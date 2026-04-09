from __future__ import annotations

import math
import pytest

import moira.rise_set as rise_set
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


def test_rise_set_preserves_planetary_substrate_failures_in_altitude_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(*args, **kwargs):
        raise RuntimeError("planet substrate failure")

    monkeypatch.setattr("moira.planets.sky_position_at", _boom)
    monkeypatch.setattr("moira.stars.star_at", lambda *args, **kwargs: pytest.fail("star fallback should not run"))

    with pytest.raises(RuntimeError, match="planet substrate failure"):
        rise_set._altitude(2451545.0, 0.0, 0.0, "Mars")


def test_rise_set_preserves_planetary_substrate_failures_in_ra_dec_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _boom(*args, **kwargs):
        raise RuntimeError("planet substrate failure")

    monkeypatch.setattr(rise_set, "planet_at", _boom)
    monkeypatch.setattr("moira.stars.star_at", lambda *args, **kwargs: pytest.fail("star fallback should not run"))

    with pytest.raises(RuntimeError, match="planet substrate failure"):
        rise_set._body_ra_dec(2451545.0, "Mars")


def test_rise_set_planetary_ra_dec_passes_tt_explicitly_without_double_conversion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, float] = {}

    monkeypatch.setattr(rise_set, "ut_to_tt", lambda jd: jd + 0.123)
    monkeypatch.setattr(rise_set, "true_obliquity", lambda jd_tt: 23.4)
    monkeypatch.setattr(rise_set, "ecliptic_to_equatorial", lambda lon, lat, eps: (lon, lat))

    def _fake_planet_at(body: str, jd_ut: float, **kwargs):
        captured["jd_ut"] = jd_ut
        captured["jd_tt"] = kwargs["jd_tt"]
        return type("Planet", (), {"longitude": 10.0, "latitude": 5.0})()

    monkeypatch.setattr(rise_set, "planet_at", _fake_planet_at)

    ra, dec = rise_set._body_ra_dec(2451545.0, "Mars")

    assert (ra, dec) == (10.0, 5.0)
    assert captured["jd_ut"] == pytest.approx(2451545.0)
    assert captured["jd_tt"] == pytest.approx(2451545.123)
