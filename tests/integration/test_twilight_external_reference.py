from __future__ import annotations

from datetime import datetime, timezone

import pytest

from moira.julian import datetime_from_jd, jd_from_datetime
from moira.rise_set import twilight_times


_MAX_TIMING_ERROR_SECONDS = 120.0


# U.S. Naval Observatory annual twilight tables, 2024.
# Times in the published tables are given for Zone 5h West of Greenwich
# (local standard time). UTC below is therefore table time + 5 hours.
#
# Sources:
# - Boston, MA Civil Twilight for 2024
# - Hartford, CT Nautical Twilight for 2024
# - Hartford, CT Astronomical Twilight for 2024
_USNO_TWILIGHT_CASES = [
    {
        "label": "Boston civil dawn",
        "lat": 42.32,
        "lon": -71.09,
        "jd_day": jd_from_datetime(datetime(2024, 6, 21, 0, 0, tzinfo=timezone.utc)),
        "attr": "civil_dawn",
        "expected": datetime(2024, 6, 21, 8, 33, tzinfo=timezone.utc),
    },
    {
        "label": "Boston civil dusk",
        "lat": 42.32,
        "lon": -71.09,
        "jd_day": jd_from_datetime(datetime(2024, 6, 21, 0, 0, tzinfo=timezone.utc)),
        "attr": "civil_dusk",
        "expected": datetime(2024, 6, 22, 0, 59, tzinfo=timezone.utc),
    },
    {
        "label": "Hartford nautical dawn",
        "lat": 41.76,
        "lon": -72.69,
        "jd_day": jd_from_datetime(datetime(2024, 6, 21, 0, 0, tzinfo=timezone.utc)),
        "attr": "nautical_dawn",
        "expected": datetime(2024, 6, 21, 7, 58, tzinfo=timezone.utc),
    },
    {
        "label": "Hartford nautical dusk",
        "lat": 41.76,
        "lon": -72.69,
        "jd_day": jd_from_datetime(datetime(2024, 6, 21, 0, 0, tzinfo=timezone.utc)),
        "attr": "nautical_dusk",
        "expected": datetime(2024, 6, 22, 1, 48, tzinfo=timezone.utc),
    },
    {
        "label": "Hartford astronomical dawn",
        "lat": 41.76,
        "lon": -72.69,
        "jd_day": jd_from_datetime(datetime(2024, 6, 21, 0, 0, tzinfo=timezone.utc)),
        "attr": "astronomical_dawn",
        "expected": datetime(2024, 6, 21, 7, 5, tzinfo=timezone.utc),
    },
    {
        "label": "Hartford astronomical dusk",
        "lat": 41.76,
        "lon": -72.69,
        "jd_day": jd_from_datetime(datetime(2024, 6, 21, 0, 0, tzinfo=timezone.utc)),
        "attr": "astronomical_dusk",
        "expected": datetime(2024, 6, 22, 2, 41, tzinfo=timezone.utc),
    },
]


@pytest.mark.requires_ephemeris
@pytest.mark.slow
@pytest.mark.parametrize("case", _USNO_TWILIGHT_CASES, ids=[c["label"] for c in _USNO_TWILIGHT_CASES])
def test_twilight_boundaries_match_usno_reference_tables(case: dict[str, object]) -> None:
    twilight = twilight_times(float(case["jd_day"]), float(case["lat"]), float(case["lon"]))
    actual_jd = getattr(twilight, str(case["attr"]))

    assert actual_jd is not None

    expected_jd = jd_from_datetime(case["expected"])
    error_seconds = abs(actual_jd - expected_jd) * 86400.0

    assert error_seconds <= _MAX_TIMING_ERROR_SECONDS


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_twilight_ordering_matches_published_boundary_sequence() -> None:
    jd_day = jd_from_datetime(datetime(2024, 6, 21, 0, 0, tzinfo=timezone.utc))
    twilight = twilight_times(jd_day, 41.76, -72.69)

    sequence = [
        twilight.astronomical_dawn,
        twilight.nautical_dawn,
        twilight.civil_dawn,
        twilight.sunrise,
        twilight.sunset,
        twilight.civil_dusk,
        twilight.nautical_dusk,
        twilight.astronomical_dusk,
    ]

    assert all(value is not None for value in sequence)
    assert sequence == sorted(sequence)

    # Published-table granularity is whole minutes; this check ensures the
    # returned UTC times correspond to the same day ordering the USNO tables use.
    rendered = [datetime_from_jd(value).strftime("%Y-%m-%d %H:%M") for value in sequence]
    assert rendered[0].startswith("2024-06-21")
    assert rendered[-1].startswith("2024-06-22")
