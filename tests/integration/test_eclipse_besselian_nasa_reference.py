from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from moira._ephemeris_time import _ephemeris_tt_to_ut1


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "nasa_solar_besselian_reference.json"
)

_POLYNOMIAL_FIELDS = ("x", "y", "d", "mu", "l1", "l2")
_CONSTANT_FIELDS = ("tan_f1", "tan_f2")
_FIELD_SEMANTICS = {
    "x": "+east shadow-axis coordinate on the geocentric fundamental plane",
    "y": "+north shadow-axis coordinate on the geocentric fundamental plane",
    "d": "declination of the shadow axis",
    "mu": "ephemeris Greenwich hour angle of the shadow axis, modulo 360 degrees",
    "l1": "penumbral cone radius on the fundamental plane",
    "l2": "signed umbral or antumbral cone radius on the fundamental plane",
    "tan_f1": "tangent of the penumbral cone half-angle",
    "tan_f2": "tangent of the umbral or antumbral cone half-angle",
}
_ADMITTED_TOLERANCES = {
    "x": {"absolute": 0.0001, "unit": "Earth equatorial radii"},
    "y": {"absolute": 0.0001, "unit": "Earth equatorial radii"},
    "d": {"absolute": 0.003, "unit": "degrees"},
    "mu": {"absolute": 0.007, "unit": "degrees circular"},
    "l1": {"absolute": 0.0001, "unit": "Earth equatorial radii"},
    "l2": {"absolute": 0.0001, "unit": "Earth equatorial radii"},
    "tan_f1": {"absolute": 0.000003, "unit": "dimensionless"},
    "tan_f2": {"absolute": 0.000003, "unit": "dimensionless"},
}


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _evaluate_polynomial(coefficients: list[float], hours_from_t0: float) -> float:
    return math.fsum(
        coefficient * hours_from_t0**degree
        for degree, coefficient in enumerate(coefficients)
    )


def _circular_residual_deg(actual: float, expected: float) -> float:
    return abs((actual - expected + 180.0) % 360.0 - 180.0)


def test_nasa_besselian_fixture_preserves_authority_and_product_semantics() -> None:
    fixture = _load_fixture()
    source = fixture["source"]

    assert source["authority"] == "NASA Goddard Space Flight Center Eclipse Web Site"
    assert source["definitions_url"].startswith("https://eclipse.gsfc.nasa.gov/")
    assert source["computation_url"].startswith("https://eclipse.gsfc.nasa.gov/")
    assert source["radius_convention_url"].startswith(
        "https://eclipse.gsfc.nasa.gov/"
    )
    assert source["reference_ephemerides"] == "VSOP87/ELP2000-82"
    assert source["reference_lunar_radius_constants"] == {
        "k1_penumbral": 0.272488,
        "k2_umbral": 0.272281,
    }
    assert source["acknowledgment"] == (
        "Eclipse Predictions by Fred Espenak, NASA's GSFC"
    )
    assert "TDT/TT hours" in source["polynomial_semantics"]
    assert "+x east" in source["coordinate_semantics"]
    assert "+y north" in source["coordinate_semantics"]
    assert "cross-model reference" in source["reference_model_note"]
    assert fixture["tolerances"] == _ADMITTED_TOLERANCES

    assert fixture["sample_offsets_hours"] == [-3.0, -1.5, 0.0, 1.5, 3.0]
    assert {row["kind"] for row in fixture["events"]} == {
        "partial",
        "total",
        "hybrid",
        "annular",
    }
    assert len(fixture["events"]) == 4

    for row in fixture["events"]:
        assert row["source_url"].startswith(
            "https://eclipse.gsfc.nasa.gov/SEsearch/SEdata.php?Ecl="
        )
        assert set(row["coefficients"]) == set(_POLYNOMIAL_FIELDS)
        assert all(
            len(row["coefficients"][field]) == 4
            for field in _POLYNOMIAL_FIELDS
        )


def test_de441_native_besselian_fields_track_nasa_published_polynomials(
    eclipse_calculator,
) -> None:
    """Compare every admitted runtime field at NASA's five fit epochs.

    This is primary-authority, per-field external validation under a named
    cross-model envelope.  NASA's published coefficient model is not used as
    Moira's runtime substrate; the runtime values remain independently derived
    from the reader-bound DE441 Earth-reception shadow geometry.
    """

    fixture = _load_fixture()
    tolerances = _ADMITTED_TOLERANCES
    failures: list[str] = []

    for row in fixture["events"]:
        t0_tt = float(row["t0_tt_jd"])
        for hours_from_t0 in fixture["sample_offsets_hours"]:
            offset_hours = float(hours_from_t0)
            jd_tt = t0_tt + offset_hours / 24.0
            jd_ut1 = _ephemeris_tt_to_ut1(
                jd_tt,
                eclipse_calculator._reader,
            )
            actual = eclipse_calculator.solar_besselian_elements(jd_ut1)

            assert actual.ephemeris == "DE-0441LE-0441"
            assert actual.axis_model == "earth_reception_light_time_center_of_mass"
            assert actual.frame == "true_equator_and_equinox_of_date"
            assert actual.hour_angle_model == "tt_ephemeris_hour_angle"
            assert actual.radius_model == "moira_spherical_mean_limb"

            # The public method accepts UT1, but each NASA polynomial sample is
            # defined at an exact TT/TDT offset.  Guard the clock inversion so
            # a per-field agreement cannot conceal sampling the wrong epoch.
            tt_residual_days = abs(actual.jd_tt - jd_tt)
            tt_tolerance_days = 4.0 * math.ulp(max(1.0, abs(jd_tt)))
            if tt_residual_days > tt_tolerance_days:
                failures.append(
                    f"event={row['id']} t={offset_hours:+.1f}h field=jd_tt "
                    f"actual={actual.jd_tt:.12f} expected={jd_tt:.12f} "
                    f"residual={tt_residual_days * 86400.0:.9f}s "
                    f"tolerance={tt_tolerance_days * 86400.0:.9f}s "
                    "semantics=reader-bound UT1-to-TT recovery"
                )

            expected_values = {
                field: _evaluate_polynomial(
                    [float(value) for value in row["coefficients"][field]],
                    offset_hours,
                )
                for field in _POLYNOMIAL_FIELDS
            }
            expected_values.update(
                {field: float(row[field]) for field in _CONSTANT_FIELDS}
            )

            for field in (*_POLYNOMIAL_FIELDS, *_CONSTANT_FIELDS):
                actual_value = float(getattr(actual, field))
                expected_value = expected_values[field]
                if field == "mu":
                    residual = _circular_residual_deg(actual_value, expected_value)
                else:
                    residual = abs(actual_value - expected_value)
                tolerance = float(tolerances[field]["absolute"])
                if residual > tolerance:
                    failures.append(
                        f"event={row['id']} kind={row['kind']} "
                        f"t={offset_hours:+.1f}h field={field} "
                        f"actual={actual_value:.10f} expected={expected_value:.10f} "
                        f"residual={residual:.10g} tolerance={tolerance:.10g} "
                        f"unit={tolerances[field]['unit']} "
                        f"semantics={_FIELD_SEMANTICS[field]}"
                    )

    assert not failures, (
        "NASA/GSFC Besselian per-field mismatches "
        f"({len(failures)} failures across four event classes):\n"
        + "\n".join(failures)
    )
