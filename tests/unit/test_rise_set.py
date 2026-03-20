from __future__ import annotations

import math
import pytest

from moira.rise_set import find_phenomena, twilight_times


def _unwrap_monotonic(values: list[float]) -> list[float]:
    unwrapped: list[float] = []
    for value in values:
        adjusted = value
        while unwrapped and adjusted <= unwrapped[-1]:
            adjusted += 1.0
        unwrapped.append(adjusted)
    return unwrapped


@pytest.mark.slow
def test_twilight_times_are_chronologically_ordered_for_mid_latitude_day() -> None:
    jd_day = 2460409.5  # 2024-04-08 00:00 UT
    twilight = twilight_times(jd_day, 40.7128, -74.0060)

    assert twilight.astronomical_dawn is not None
    assert twilight.nautical_dawn is not None
    assert twilight.civil_dawn is not None
    assert twilight.sunrise is not None
    assert twilight.sunset is not None
    assert twilight.civil_dusk is not None
    assert twilight.nautical_dusk is not None
    assert twilight.astronomical_dusk is not None

    ordered = _unwrap_monotonic(
        [
            twilight.astronomical_dawn,
            twilight.nautical_dawn,
            twilight.civil_dawn,
            twilight.sunrise,
            twilight.sunset,
            twilight.civil_dusk,
            twilight.nautical_dusk,
            twilight.astronomical_dusk,
        ]
    )
    assert ordered == sorted(ordered)


@pytest.mark.slow
def test_twilight_sunrise_and_sunset_match_find_phenomena() -> None:
    jd_day = 2460409.5
    lat = 40.7128
    lon = -74.0060

    twilight = twilight_times(jd_day, lat, lon)
    phenomena = find_phenomena("Sun", jd_day, lat, lon, altitude=-0.8333)

    assert twilight.sunrise is not None
    assert twilight.sunset is not None
    assert abs(twilight.sunrise - phenomena["Rise"]) * 86400.0 < 0.5
    assert abs(twilight.sunset - phenomena["Set"]) * 86400.0 < 0.5


@pytest.mark.slow
def test_twilight_handles_polar_day_or_night_without_raising() -> None:
    jd_day = 2460481.5  # near northern summer solstice
    twilight = twilight_times(jd_day, 69.6492, 18.9553)

    values = [
        twilight.astronomical_dawn,
        twilight.nautical_dawn,
        twilight.civil_dawn,
        twilight.sunrise,
        twilight.sunset,
        twilight.civil_dusk,
        twilight.nautical_dusk,
        twilight.astronomical_dusk,
    ]
    assert all(value is None or math.isfinite(value) for value in values)
