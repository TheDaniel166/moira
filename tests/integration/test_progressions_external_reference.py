from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from moira.julian import jd_from_datetime
from moira.progressions import secondary_progression, solar_arc


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "progressions_swetest_reference.json"
PASS_THRESHOLD_ARCSEC = 1.0


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _angular_diff_arcsec(a: float, b: float) -> float:
    diff = abs(a - b) % 360.0
    diff = diff if diff <= 180.0 else 360.0 - diff
    return diff * 3600.0


def _dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


@pytest.mark.integration
@pytest.mark.requires_ephemeris
@pytest.mark.skipif(
    not FIXTURE_PATH.exists(),
    reason="progressions_swetest_reference.json not found - run scripts/build_progressions_swetest_fixture.py first",
)
@pytest.mark.parametrize("case", _load_fixture()["secondary_cases"], ids=lambda case: case["id"])
def test_secondary_progression_matches_offline_swetest_reference(case: dict) -> None:
    natal_dt = _dt(case["natal_dt_utc"])
    target_dt = _dt(case["target_dt_utc"])
    chart = secondary_progression(jd_from_datetime(natal_dt), target_dt)

    for body, expected_lon in case["positions_deg"].items():
        actual_lon = chart.positions[body].longitude
        diff_arcsec = _angular_diff_arcsec(actual_lon, expected_lon)
        assert diff_arcsec <= PASS_THRESHOLD_ARCSEC, (
            f"{case['id']} {body}: expected {expected_lon:.10f}, got {actual_lon:.10f}, "
            f"delta={diff_arcsec:.6f}\""
        )


@pytest.mark.integration
@pytest.mark.requires_ephemeris
@pytest.mark.skipif(
    not FIXTURE_PATH.exists(),
    reason="progressions_swetest_reference.json not found - run scripts/build_progressions_swetest_fixture.py first",
)
@pytest.mark.parametrize("case", _load_fixture()["solar_arc_cases"], ids=lambda case: case["id"])
def test_solar_arc_matches_offline_swetest_reference(case: dict) -> None:
    natal_dt = _dt(case["natal_dt_utc"])
    target_dt = _dt(case["target_dt_utc"])
    chart = solar_arc(jd_from_datetime(natal_dt), target_dt)

    arc_diff = _angular_diff_arcsec(chart.solar_arc_deg, case["arc_deg"])
    assert arc_diff <= PASS_THRESHOLD_ARCSEC, (
        f"{case['id']} solar arc: expected {case['arc_deg']:.10f}, got {chart.solar_arc_deg:.10f}, "
        f"delta={arc_diff:.6f}\""
    )

    for body, expected_lon in case["positions_deg"].items():
        actual_lon = chart.positions[body].longitude
        diff_arcsec = _angular_diff_arcsec(actual_lon, expected_lon)
        assert diff_arcsec <= PASS_THRESHOLD_ARCSEC, (
            f"{case['id']} {body}: expected {expected_lon:.10f}, got {actual_lon:.10f}, "
            f"delta={diff_arcsec:.6f}\""
        )
