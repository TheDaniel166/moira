from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from moira._ephemeris_time import _ephemeris_tt_to_ut1
from moira.constants import EARTH_RADIUS_KM
from moira.eclipse import (
    _SearchLimitReached,
    _central_shadow_clearance_km,
    _earth_fixed_solar_shadow,
    _solar_axis_surface_point,
    _solve_local_solar_central_duration_s,
    _solve_solar_umbral_width_km,
    _wgs84_surface_xyz_km,
)


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "nasa_solar_polar_path_reference.json"
)

_ADMITTED_TOLERANCES = {
    "searched_timing_s": 1.0,
    "surface_position_km": 3.0,
    "path_width_km": 3.0,
    "central_duration_s": 3.0,
    "magnitude": 0.005,
    "published_limit_clearance_km": 3.0,
    "besselian": {
        "x": 0.0001,
        "y": 0.0001,
        "d": 0.003,
        "mu": 0.007,
        "l1": 0.0001,
        "l2": 0.0001,
        "tan_f1": 0.000003,
        "tan_f2": 0.000003,
    },
}


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _surface_distance_km(
    actual: tuple[float, float],
    expected: tuple[float, float] | list[float],
) -> float:
    actual_latitude, actual_longitude = map(math.radians, actual)
    expected_latitude, expected_longitude = map(math.radians, expected)
    actual_unit = (
        math.cos(actual_latitude) * math.cos(actual_longitude),
        math.cos(actual_latitude) * math.sin(actual_longitude),
        math.sin(actual_latitude),
    )
    expected_unit = (
        math.cos(expected_latitude) * math.cos(expected_longitude),
        math.cos(expected_latitude) * math.sin(expected_longitude),
        math.sin(expected_latitude),
    )
    cross = (
        actual_unit[1] * expected_unit[2] - actual_unit[2] * expected_unit[1],
        actual_unit[2] * expected_unit[0] - actual_unit[0] * expected_unit[2],
        actual_unit[0] * expected_unit[1] - actual_unit[1] * expected_unit[0],
    )
    cross_norm = math.sqrt(sum(component * component for component in cross))
    dot = sum(left * right for left, right in zip(actual_unit, expected_unit))
    return EARTH_RADIUS_KM * math.atan2(cross_norm, dot)


def _evaluate_polynomial(coefficients: list[float], hours_from_t0: float) -> float:
    return math.fsum(
        coefficient * hours_from_t0**degree
        for degree, coefficient in enumerate(coefficients)
    )


def _circular_residual_deg(actual: float, expected: float) -> float:
    return abs((actual - expected + 180.0) % 360.0 - 180.0)


def test_polar_fixture_preserves_one_coherent_nasa_product_lineage() -> None:
    fixture = _load_fixture()
    source = fixture["source"]
    event = fixture["event"]

    assert fixture["schema_version"] == 1
    assert fixture["tolerances"] == _ADMITTED_TOLERANCES
    assert source["authority"] == "NASA Goddard Space Flight Center Eclipse Web Site"
    assert source["path_url"] == (
        "https://eclipse.gsfc.nasa.gov/SEpath/SEpath2001/SE2015Mar20Tpath.html"
    )
    assert source["besselian_url"] == (
        "https://eclipse.gsfc.nasa.gov/SEbeselm/SEbeselm2001/"
        "SE2015Mar20Tbeselm.html"
    )
    assert source["reference_ephemeris"] == "JPL DE405"
    assert source["delta_t_s"] == 67.6
    assert source["sampling_interval_s"] == 120
    assert source["lunar_radius_constants"] == {
        "k1_penumbral": 0.272508,
        "k2_umbral": 0.272281,
    }
    assert source["acknowledgment"] == (
        "Eclipse Predictions by Fred Espenak, NASA's GSFC"
    )
    assert "WGS 84 geodetic" in source["coordinate_system"]
    assert "mean-limb" in source["mean_limb_policy"]
    assert "cross-model" in source["comparison_note"]

    assert event["id"] == "2015-03-20-total-polar-central"
    assert event["kind"] == "total"
    assert len(event["path_samples"]) == 5
    assert [row["ut"] for row in event["path_samples"]] == [
        "10:10:00",
        "10:12:00",
        "10:14:00",
        "10:16:00",
        "10:18:00",
    ]
    sample_jds = [float(row["jd_ut1"]) for row in event["path_samples"]]
    assert sample_jds == pytest.approx(
        [
            2457101.923611111,
            2457101.925,
            2457101.926388889,
            2457101.927777778,
            2457101.9291666667,
        ],
        abs=1.0e-12,
    )
    for earlier, later in zip(event["path_samples"], event["path_samples"][1:]):
        cadence_s = (
            float(later["jd_ut1"]) - float(earlier["jd_ut1"])
        ) * 86400.0
        assert cadence_s == pytest.approx(120.0, abs=1.0e-3)
    assert event["initial_product"]["time_label"] == "Limits"
    assert event["terminal_product"]["time_label"] == "Limits"
    published_delta_t_s = (
        float(event["greatest"]["tt_jd"])
        - float(event["greatest"]["ut1_jd"])
    ) * 86400.0
    assert published_delta_t_s == pytest.approx(source["delta_t_s"], abs=0.05)
    assert event["path_samples"][-2]["north_limit"] is None
    assert event["path_samples"][-1]["north_limit"] is None
    assert event["terminal_product"]["central_line"][0] > 89.0
    assert event["besselian"]["valid_hours_from_t0"] == [-3.0, 3.0]
    assert event["besselian"]["fit_sample_count"] == 5
    assert event["besselian"]["sample_offsets_hours"] == [
        -3.0,
        -1.5,
        0.0,
        1.5,
        3.0,
    ]

    for product in (
        event["initial_product"],
        *event["path_samples"],
        event["terminal_product"],
    ):
        for field in ("north_limit", "south_limit", "central_line"):
            coordinates = product[field]
            if coordinates is None:
                continue
            assert -90.0 <= float(coordinates[0]) <= 90.0
            assert -180.0 <= float(coordinates[1]) <= 180.0


@pytest.mark.slow
def test_de441_polar_besselian_fields_track_the_paired_de405_product(
    eclipse_calculator,
) -> None:
    fixture = _load_fixture()
    besselian = fixture["event"]["besselian"]
    tolerances = _ADMITTED_TOLERANCES["besselian"]
    polynomial_fields = ("x", "y", "d", "mu", "l1", "l2")

    for offset in besselian["sample_offsets_hours"]:
        hours_from_t0 = float(offset)
        jd_tt = float(besselian["t0_tt_jd"]) + hours_from_t0 / 24.0
        jd_ut1 = _ephemeris_tt_to_ut1(jd_tt, eclipse_calculator._reader)
        actual = eclipse_calculator.solar_besselian_elements(jd_ut1)

        assert actual.ephemeris == "DE-0441LE-0441"
        assert actual.jd_tt == pytest.approx(jd_tt, abs=4.0 * math.ulp(jd_tt))
        for field in polynomial_fields:
            expected = _evaluate_polynomial(
                [float(value) for value in besselian["coefficients"][field]],
                hours_from_t0,
            )
            if field == "mu":
                residual = _circular_residual_deg(float(actual.mu), expected)
                assert residual <= float(tolerances[field])
            else:
                assert float(getattr(actual, field)) == pytest.approx(
                    expected,
                    abs=float(tolerances[field]),
                )
        for field in ("tan_f1", "tan_f2"):
            assert float(getattr(actual, field)) == pytest.approx(
                float(besselian[field]),
                abs=float(tolerances[field]),
            )


@pytest.mark.slow
def test_public_de441_path_reaches_the_authoritative_polar_central_limits(
    eclipse_calculator,
) -> None:
    fixture = _load_fixture()
    event_row = fixture["event"]
    greatest = event_row["greatest"]
    tolerances = _ADMITTED_TOLERANCES
    seed_jd = float(event_row["seed_jd"])

    event = eclipse_calculator.next_solar_eclipse(seed_jd, kind="total")
    path = eclipse_calculator.solar_eclipse_path(
        seed_jd,
        kind="total",
        sample_count=2,
    )

    assert abs(event.jd_ut - float(greatest["ut1_jd"])) * 86400.0 <= float(
        tolerances["searched_timing_s"]
    )
    assert path.eclipse_data.eclipse_type.is_total
    assert _surface_distance_km(
        (path.max_eclipse_lat, path.max_eclipse_lon),
        (float(greatest["latitude_deg"]), float(greatest["longitude_deg"])),
    ) <= float(tolerances["surface_position_km"])
    assert path.umbral_width_km == pytest.approx(
        float(greatest["path_width_km"]),
        abs=float(tolerances["path_width_km"]),
    )
    assert path.duration_at_max_s == pytest.approx(
        float(greatest["central_duration_s"]),
        abs=float(tolerances["central_duration_s"]),
    )
    assert path.eclipse_data.eclipse_magnitude == pytest.approx(
        float(greatest["magnitude"]),
        abs=float(tolerances["magnitude"]),
    )

    assert len(path.central_line_lats) == len(path.central_line_lons) == 2
    initial_actual = (path.central_line_lats[0], path.central_line_lons[0])
    terminal_actual = (path.central_line_lats[-1], path.central_line_lons[-1])
    assert _surface_distance_km(
        initial_actual,
        event_row["initial_product"]["central_line"],
    ) <= float(tolerances["surface_position_km"])
    assert _surface_distance_km(
        terminal_actual,
        event_row["terminal_product"]["central_line"],
    ) <= float(tolerances["surface_position_km"])
    assert terminal_actual[0] > 89.0


@pytest.mark.slow
def test_named_polar_rows_bind_axis_limits_and_duration_to_one_epoch(
    eclipse_calculator,
) -> None:
    fixture = _load_fixture()
    tolerances = _ADMITTED_TOLERANCES

    for row in fixture["event"]["path_samples"]:
        jd_ut1 = float(row["jd_ut1"])
        point = _solar_axis_surface_point(eclipse_calculator, jd_ut1)
        shadow = _earth_fixed_solar_shadow(eclipse_calculator, jd_ut1)
        assert point is not None
        assert shadow is not None
        assert _surface_distance_km(
            (point.latitude_deg, point.longitude_deg),
            row["central_line"],
        ) <= float(tolerances["surface_position_km"])
        assert _central_shadow_clearance_km(
            shadow,
            point.xyz_itrf_km,
        ) > 0.0

        duration_s = _solve_local_solar_central_duration_s(
            eclipse_calculator,
            jd_ut1,
            point.latitude_deg,
            point.longitude_deg,
        )
        assert duration_s == pytest.approx(
            float(row["central_duration_s"]),
            abs=float(tolerances["central_duration_s"]),
        )

        for field in ("north_limit", "south_limit"):
            coordinates = row[field]
            if coordinates is None:
                continue
            clearance_km = _central_shadow_clearance_km(
                shadow,
                _wgs84_surface_xyz_km(
                    float(coordinates[0]),
                    float(coordinates[1]),
                ),
            )
            assert abs(clearance_km) <= float(
                tolerances["published_limit_clearance_km"]
            )


@pytest.mark.slow
def test_pole_enclosing_one_limit_rows_fail_closed_as_a_distinct_width_product(
    eclipse_calculator,
) -> None:
    fixture = _load_fixture()
    one_limit_rows = fixture["event"]["path_samples"][-2:]

    for row in one_limit_rows:
        assert row["north_limit"] is None
        assert row["south_limit"] is not None
        point = _solar_axis_surface_point(eclipse_calculator, float(row["jd_ut1"]))
        shadow = _earth_fixed_solar_shadow(
            eclipse_calculator,
            float(row["jd_ut1"]),
        )
        assert point is not None
        assert shadow is not None
        assert _central_shadow_clearance_km(shadow, point.xyz_itrf_km) > 0.0
        with pytest.raises(
            _SearchLimitReached,
            match="not a closed two-limit product",
        ):
            _solve_solar_umbral_width_km(
                eclipse_calculator,
                float(row["jd_ut1"]),
            )
