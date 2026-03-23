from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from moira.julian import jd_from_datetime
from moira.rise_set import find_phenomena

_JD_SECONDS = 86400.0
_USNO_MINUTE_THRESHOLD_SECONDS = 120.0

_USNO_CASES: list[dict[str, object]] = [
    {
        "id": "usno-sirius-new-york-2025-11-04",
        "body": "Sirius",
        "source_url": (
            "https://aa.usno.navy.mil/calculated/mrst"
            "?body=-20&date=2025-11-04&height=0&label=New+York%2C+NY"
            "&lat=40.73&lon=-73.92&reps=5&submit=Get+Data&tz=5&tz_sign=-1"
        ),
        "location": {
            "label": "New York, NY",
            "latitude_deg": 40.73,
            "longitude_deg": -73.92,
        },
        "jd_start": jd_from_datetime(
            datetime(2025, 11, 4, 0, 0, tzinfo=timezone(timedelta(hours=-5)))
        ),
        "altitude_deg": -0.5667,
        "expected_events": {
            "Rise": jd_from_datetime(
                datetime(2025, 11, 4, 22, 40, tzinfo=timezone(timedelta(hours=-5)))
            ),
            "Transit": jd_from_datetime(
                datetime(2025, 11, 4, 3, 47, tzinfo=timezone(timedelta(hours=-5)))
            ),
            "Set": jd_from_datetime(
                datetime(2025, 11, 4, 8, 49, tzinfo=timezone(timedelta(hours=-5)))
            ),
        },
        "notes": (
            "USNO published rise/set/transit table for Sirius, New York, NY, "
            "row dated 2025 Nov 04 (EST, 5h west of Greenwich)."
        ),
    },
]


def _error_seconds(actual_jd: float, expected_jd: float) -> float:
    return abs(actual_jd - expected_jd) * _JD_SECONDS


@pytest.mark.integration
@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("case", _USNO_CASES, ids=[str(case["id"]) for case in _USNO_CASES])
def test_rise_set_against_usno_published_table(case: dict[str, object]) -> None:
    """
    Supplemental published-table spot check for fixed-star rise/set/transit.

    USNO tables are minute-resolution and therefore use a 2-minute threshold.
    This test is intentionally small; the primary oracle suite for rise/set is
    the offline Horizons fixture.
    """
    body = str(case["body"])
    location = dict(case["location"])
    expected = dict(case["expected_events"])
    jd_start = float(case["jd_start"])

    phenomena = find_phenomena(
        body,
        jd_start,
        float(location["latitude_deg"]),
        float(location["longitude_deg"]),
        altitude=float(case["altitude_deg"]),
    )

    for event_name, expected_jd in expected.items():
        actual_jd = phenomena.get(event_name)
        assert actual_jd is not None, f"{case['id']} missing {event_name}"
        error_seconds = _error_seconds(float(actual_jd), float(expected_jd))
        assert error_seconds <= _USNO_MINUTE_THRESHOLD_SECONDS, (
            f"{case['id']} {event_name} error {error_seconds:.2f}s exceeds "
            f"{_USNO_MINUTE_THRESHOLD_SECONDS:.2f}s "
            f"(source: {case['source_url']})"
        )
