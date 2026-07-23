from __future__ import annotations

import json
from pathlib import Path

import pytest

from moira.julian import julian_day


FIXTURE_PATH = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "solar_eclipse_global_reference.json"
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
