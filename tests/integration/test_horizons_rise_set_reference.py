from __future__ import annotations

import json
from pathlib import Path

import pytest

from moira.rise_set import find_phenomena, get_transit

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "horizons_rise_set_reference.json"
_DEFAULT_THRESHOLD_SECONDS = 120.0
_JD_SECONDS = 86400.0


def _load_cases() -> list[dict[str, object]]:
    if not _FIXTURE.exists():
        return []
    data = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    return list(data.get("cases", []))


def _event_error_seconds(actual_jd: float, expected_jd: float) -> float:
    return abs(actual_jd - expected_jd) * _JD_SECONDS


_CASES = _load_cases()
_CASE_IDS = [str(case["id"]) for case in _CASES]


@pytest.mark.integration
@pytest.mark.requires_ephemeris
@pytest.mark.slow
@pytest.mark.skipif(
    not _FIXTURE.exists(),
    reason=(
        "horizons_rise_set_reference.json not found — "
        "run scripts/build_rise_set_horizons_fixture.py first"
    ),
)
@pytest.mark.parametrize("case", _CASES, ids=_CASE_IDS)
def test_find_phenomena_and_get_transit_match_horizons_fixture(case: dict[str, object]) -> None:
    """
    Validate rise/set/transit timing against an offline JPL Horizons fixture.

    Window semantics are explicit: each expected event is the first matching
    event in the next 24 hours from ``jd_start``.
    """
    body = str(case["body"])
    location = dict(case["location"])
    window = dict(case["window"])
    expected = dict(case["expected_events"])
    altitude = float(case["altitude_deg"])
    jd_start = float(window["jd_start"])
    lat = float(location["latitude_deg"])
    lon = float(location["longitude_deg"])

    phenomena = find_phenomena(body, jd_start, lat, lon, altitude=altitude)
    threshold = float(case.get("threshold_seconds", _DEFAULT_THRESHOLD_SECONDS))

    for event_name in ("Rise", "Set"):
        expected_jd = expected.get(event_name)
        actual_jd = phenomena.get(event_name)
        if expected_jd is None:
            assert actual_jd is None, (
                f"{case['id']} expected no {event_name} in the next 24h window, "
                f"but moira returned JD {actual_jd}"
            )
            continue
        assert actual_jd is not None, f"{case['id']} missing {event_name}"
        error_seconds = _event_error_seconds(float(actual_jd), float(expected_jd))
        assert error_seconds <= threshold, (
            f"{case['id']} {event_name} error {error_seconds:.2f}s exceeds "
            f"{threshold:.2f}s (moira={actual_jd}, ref={expected_jd})"
        )

    for event_name, upper in (("Transit", True), ("AntiTransit", False)):
        expected_jd = expected.get(event_name)
        actual_jd = get_transit(body, jd_start, lat, lon, upper=upper)
        assert jd_start <= actual_jd < jd_start + 1.0, (
            f"{case['id']} {event_name} fell outside the documented next-24h window"
        )
        assert expected_jd is not None, f"{case['id']} fixture missing {event_name}"
        error_seconds = _event_error_seconds(actual_jd, float(expected_jd))
        assert error_seconds <= threshold, (
            f"{case['id']} {event_name} error {error_seconds:.2f}s exceeds "
            f"{threshold:.2f}s (moira={actual_jd}, ref={expected_jd})"
        )
