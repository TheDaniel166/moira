from __future__ import annotations

import json
from pathlib import Path

import pytest

from moira.parans import find_parans


FIXTURE_PATH = Path(__file__).resolve().parents[1] / "fixtures" / "parans_horizons_reference.json"
FIXTURE = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
DEFAULT_THRESHOLD_SECONDS = FIXTURE["_default_threshold_seconds"]


def _seconds_from_jd_delta(delta_jd: float) -> float:
    return abs(delta_jd) * 86400.0


@pytest.mark.integration
@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("case", FIXTURE["cases"], ids=[case["id"] for case in FIXTURE["cases"]])
def test_parans_match_offline_horizons_reference(case: dict) -> None:
    lat = case["location"]["latitude_deg"]
    lon = case["location"]["longitude_deg"]
    jd_start = case["window"]["jd_start"]
    orb_minutes = case["orb_minutes"]
    threshold_seconds = case.get("threshold_seconds", DEFAULT_THRESHOLD_SECONDS)
    bodies = [row["body"] for row in case["bodies"]]

    actual = find_parans(bodies, jd_start, lat, lon, orb_minutes=orb_minutes)
    expected = case["expected_parans"]

    assert len(actual) == len(expected)

    for actual_paran, expected_paran in zip(actual, expected):
        assert actual_paran.body1 == expected_paran["body1"]
        assert actual_paran.body2 == expected_paran["body2"]
        assert actual_paran.circle1 == expected_paran["circle1"]
        assert actual_paran.circle2 == expected_paran["circle2"]
        assert _seconds_from_jd_delta(actual_paran.jd1 - expected_paran["jd1_ut"]) <= threshold_seconds
        assert _seconds_from_jd_delta(actual_paran.jd2 - expected_paran["jd2_ut"]) <= threshold_seconds
        assert _seconds_from_jd_delta(actual_paran.jd - expected_paran["jd_mid_ut"]) <= threshold_seconds
        assert abs(actual_paran.orb_min - expected_paran["orb_minutes"]) <= (2.0 * threshold_seconds / 60.0)
