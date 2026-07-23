from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from moira._ephemeris_time import _ephemeris_tt_to_ut1
from moira.julian import julian_day


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "solar_eclipse_global_reference.json"
)
NASA_BESSELIAN_FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "nasa_solar_besselian_reference.json"
)


def _calendar_jd(value: str) -> float:
    date_text, time_text = value.split("T")
    year, month, day = (int(part) for part in date_text.split("-"))
    hour, minute, second = time_text.split(":")
    decimal_hour = int(hour) + int(minute) / 60.0 + float(second) / 3600.0
    return julian_day(year, month, day, decimal_hour)


def _time_error_seconds(jd_ut1: float, expected: str) -> float:
    return abs(jd_ut1 - _calendar_jd(expected)) * 86400.0


def _longitude_error_degrees(left: float, right: float) -> float:
    return abs((left - right + 180.0) % 360.0 - 180.0)


def _evaluate_polynomial(coefficients: list[float], hours_from_t0: float) -> float:
    return math.fsum(
        float(coefficient) * hours_from_t0**degree
        for degree, coefficient in enumerate(coefficients)
    )


def test_fixture_declares_cross_model_solar_semantics() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    source = payload["source"]
    assert source["evidence_class"] == "cross_model_corroboration"
    assert source["ephemerides"] == "JPL DE405"
    assert source["lunar_origin"] == "Moon center of mass"
    assert source["archived_sha256"] is None
    assert float(source["delta_t_seconds"]) == 72.8


@pytest.mark.slow
def test_solar_global_products_correlate_with_declared_eclipsewise_row(
    eclipse_calculator,
) -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    row = payload["events"][0]
    tolerance = payload["source"]["cross_model_tolerances"]
    result = eclipse_calculator.solar_global_circumstances(
        julian_day(2027, 7, 20),
        kind=str(row["kind"]),
    )

    assert result.ephemeris == "DE-0441LE-0441"
    for kind in ("equatorial", "ecliptic"):
        actual = getattr(result, f"{kind}_conjunction")
        assert actual.kind.value == kind
        assert _time_error_seconds(
            actual.epoch.jd_ut1,
            row["conjunctions"][f"{kind}_ut1"],
        ) <= float(tolerance["greatest_eclipse_time_seconds"])
    contacts = result.umbral_contacts
    assert contacts is not None
    for kind in ("u1", "u2", "u3", "u4"):
        actual = getattr(contacts, kind)
        expected = row["umbral_contacts"][kind]
        assert _time_error_seconds(actual.epoch.jd_ut1, expected["ut1"]) <= float(
            tolerance["contact_time_seconds"]
        )
        assert actual.latitude_deg == pytest.approx(
            float(expected["latitude_deg"]),
            abs=float(tolerance["contact_position_degrees"]),
        )
        assert _longitude_error_degrees(
            actual.longitude_deg,
            float(expected["longitude_deg"]),
        ) <= float(tolerance["contact_position_degrees"])

    for actual, expected, time_tolerance in (
        (
            result.greatest,
            row["greatest_eclipse"],
            tolerance["greatest_eclipse_time_seconds"],
        ),
        (
            result.greatest_duration,
            row["greatest_duration"],
            tolerance["greatest_duration_time_seconds"],
        ),
    ):
        assert actual is not None
        assert _time_error_seconds(actual.epoch.jd_ut1, expected["ut1"]) <= float(
            time_tolerance
        )
        assert actual.latitude_deg == pytest.approx(
            float(expected["latitude_deg"]),
            abs=float(tolerance["greatest_site_position_degrees"]),
        )
        assert _longitude_error_degrees(
            actual.longitude_deg,
            float(expected["longitude_deg"]),
        ) <= float(tolerance["greatest_site_position_degrees"])
        assert actual.central_duration_seconds == pytest.approx(
            float(expected["duration_seconds"]),
            abs=float(tolerance["duration_seconds"]),
        )
        assert actual.path_width_km == pytest.approx(
            float(expected["path_width_km"]),
            abs=float(tolerance["path_width_km"]),
        )


@pytest.mark.slow
@pytest.mark.parametrize(
    "row",
    json.loads(
        NASA_BESSELIAN_FIXTURE_PATH.read_text(encoding="utf-8")
    )["events"],
    ids=lambda row: f"{row['id']} global vessel",
)
def test_solar_global_vessel_tracks_nasa_besselian_corpus_across_event_classes(
    eclipse_calculator,
    row: dict[str, object],
) -> None:
    """Bind the first-class global result to the existing NASA field corpus."""

    fixture = json.loads(
        NASA_BESSELIAN_FIXTURE_PATH.read_text(encoding="utf-8")
    )
    t0_tt = float(row["t0_tt_jd"])
    t0_ut1 = _ephemeris_tt_to_ut1(t0_tt, eclipse_calculator._reader)
    kind = str(row["kind"])
    result = eclipse_calculator.solar_global_circumstances(
        t0_ut1 - 1.0,
        kind=kind,
    )

    eclipse_type = result.event.data.eclipse_type
    assert getattr(eclipse_type, f"is_{kind}") is True
    assert result.ephemeris == "DE-0441LE-0441"
    if kind == "partial":
        assert result.umbral_contacts is None
        assert result.greatest_duration is None
    else:
        assert result.umbral_contacts is not None
        assert result.greatest_duration is not None

    actual = result.besselian
    hours_from_t0 = (actual.jd_tt - t0_tt) * 24.0
    assert -3.0 <= hours_from_t0 <= 3.0
    coefficients = row["coefficients"]
    failures: list[str] = []
    for field in ("x", "y", "d", "mu", "l1", "l2"):
        expected = _evaluate_polynomial(
            [float(value) for value in coefficients[field]],
            hours_from_t0,
        )
        value = float(getattr(actual, field))
        residual = (
            _longitude_error_degrees(value, expected)
            if field == "mu"
            else abs(value - expected)
        )
        tolerance = float(fixture["tolerances"][field]["absolute"])
        if residual > tolerance:
            failures.append(
                f"{row['id']} {field}: residual={residual:.10g} "
                f"tolerance={tolerance:.10g}"
            )
    for field in ("tan_f1", "tan_f2"):
        residual = abs(float(getattr(actual, field)) - float(row[field]))
        tolerance = float(fixture["tolerances"][field]["absolute"])
        if residual > tolerance:
            failures.append(
                f"{row['id']} {field}: residual={residual:.10g} "
                f"tolerance={tolerance:.10g}"
            )
    assert not failures, "\n".join(failures)
