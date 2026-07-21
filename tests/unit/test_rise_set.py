from __future__ import annotations

import math
import pytest

import moira.rise_set as rise_set
from moira.rise_set import (
    HorizonCrossingState,
    find_phenomena,
    horizon_crossing_availability,
    twilight_times,
)
from moira.constants import Body


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


def test_find_phenomena_omits_meridian_event_absent_from_window(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(rise_set, "_find_horizon_events", lambda *args, **kwargs: {})

    def _transit(*args, upper: bool, **kwargs) -> float:
        if upper:
            raise RuntimeError("no meridian transit bracket found in the 24-hour window")
        return 100.5

    monkeypatch.setattr(rise_set, "get_transit", _transit)

    assert find_phenomena("Moon", 100.0, 0.0, 0.0) == {
        "AntiTransit": 100.5,
    }


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


def test_lst_reuses_one_nutation_evaluation(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[float] = []
    monkeypatch.setattr(
        rise_set,
        "_jd_tt_for_active_reader",
        lambda jd: jd + 0.25,
    )

    def _nutation(jd_tt: float) -> tuple[float, float]:
        calls.append(jd_tt)
        return 0.01, 0.02

    monkeypatch.setattr(rise_set, "nutation", _nutation)
    monkeypatch.setattr(rise_set, "mean_obliquity", lambda jd_tt: 23.4)
    monkeypatch.setattr(
        rise_set,
        "local_sidereal_time",
        lambda jd_ut, longitude, dpsi, eps: jd_ut + longitude + dpsi + eps,
    )

    value = rise_set._lst(100.0, 5.0)

    assert calls == [100.25]
    assert value == pytest.approx(128.43)


def test_get_transit_uses_verified_newton_before_scan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[float] = []

    def _error(jd, body, lat, lon, target):
        calls.append(jd)
        expected = 100.25 if target == 0.0 else 100.75
        return (jd - expected) * 360.98564736629

    monkeypatch.setattr(rise_set, "_hour_angle_error", _error)
    monkeypatch.setattr(
        rise_set,
        "_scan_transit",
        lambda *args, **kwargs: pytest.fail("verified Newton solve must avoid scan"),
    )

    assert rise_set.get_transit("Regulus", 100.0, 0.0, 0.0) == pytest.approx(100.25)
    assert rise_set.get_transit(
        "Regulus", 100.0, 0.0, 0.0, upper=False
    ) == pytest.approx(100.75)
    assert len(calls) <= 6


def test_get_transit_falls_back_when_newton_does_not_verify(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        rise_set,
        "_hour_angle_error",
        lambda *args, **kwargs: 100.0,
    )
    monkeypatch.setattr(rise_set, "_scan_transit", lambda *args, **kwargs: 123.25)

    assert rise_set.get_transit("Regulus", 123.0, 0.0, 0.0) == 123.25


@pytest.mark.slow
@pytest.mark.parametrize("body", [*Body.ALL_PLANETS, "Regulus", "Acrux"])
@pytest.mark.parametrize("lat", [-66.0, -30.0, 0.0, 30.0, 66.0])
@pytest.mark.parametrize("upper", [True, False])
def test_newton_first_transit_matches_scan_truth(
    body: str,
    lat: float,
    upper: bool,
) -> None:
    jd_day = 2451544.5
    expected = rise_set._scan_transit(body, jd_day, lat, -0.1, upper=upper)
    actual = rise_set.get_transit(body, jd_day, lat, -0.1, upper=upper)

    assert abs(actual - expected) * 86400.0 < 0.5


@pytest.mark.slow
def test_horizon_crossing_availability_distinguishes_stellar_geometry() -> None:
    states = {
        star: horizon_crossing_availability(star, 2451544.5, 60.0, 0.0).state
        for star in ("Regulus", "Capella", "Acrux")
    }

    assert states == {
        "Regulus": HorizonCrossingState.CROSSES,
        "Capella": HorizonCrossingState.ALWAYS_ABOVE_HORIZON,
        "Acrux": HorizonCrossingState.ALWAYS_BELOW_HORIZON,
    }


@pytest.mark.slow
def test_fixed_star_fast_horizon_matches_scan_truth_across_latitudes() -> None:
    jd_day = 2451544.5
    altitude = -0.5667
    for star in ("Regulus", "Capella", "Acrux", "Sirius", "Polaris"):
        for lat in range(-66, 67, 2):
            fast = rise_set._stellar_horizon_events(
                star,
                jd_day,
                float(lat),
                0.0,
                altitude,
                1013.25,
                10.0,
            )
            scan = rise_set._scan_horizon_events(
                star,
                jd_day,
                float(lat),
                0.0,
                altitude,
                1013.25,
                10.0,
            )
            resolved = scan if fast is None else fast
            assert set(resolved) == set(scan), (star, lat, resolved, scan)
            for event in scan:
                assert abs(resolved[event] - scan[event]) * 86400.0 < 0.5


def test_fixed_star_availability_uses_analytic_extrema_with_same_states() -> None:
    jd_day = 2451544.5
    altitude = -0.5667
    for star in ("Regulus", "Capella", "Acrux", "Sirius", "Polaris"):
        for lat in (-66.0, -30.0, 0.0, 30.0, 66.0):
            result = horizon_crossing_availability(
                star,
                jd_day,
                lat,
                0.0,
                altitude=altitude,
            )
            sampled = tuple(
                rise_set._altitude(jd_day + index / 144, lat, 0.0, star)
                for index in range(145)
            )
            expected = (
                HorizonCrossingState.ALWAYS_ABOVE_HORIZON
                if min(sampled) > altitude
                else HorizonCrossingState.ALWAYS_BELOW_HORIZON
                if max(sampled) < altitude
                else HorizonCrossingState.CROSSES
            )
            assert result.state is expected
            assert result.method == "analytic_fixed_star_diurnal_extrema"
            assert result.sample_count == 1


def test_fixed_star_grazing_geometry_preserves_scan_event_semantics() -> None:
    jd_day = 2451544.5
    altitude = -0.5667
    _ra, dec, _minimum, _maximum, _cos_h0 = rise_set._stellar_horizon_geometry(
        "Capella", jd_day + 0.5, 0.0, altitude
    )
    grazing_latitude = 90.0 + altitude - dec
    fast = rise_set._stellar_horizon_events(
        "Capella",
        jd_day,
        grazing_latitude,
        0.0,
        altitude,
        1013.25,
        10.0,
    )
    scan = rise_set._scan_horizon_events(
        "Capella",
        jd_day,
        grazing_latitude,
        0.0,
        altitude,
        1013.25,
        10.0,
    )

    assert (scan if fast is None else fast) == scan


@pytest.mark.slow
@pytest.mark.parametrize("body", Body.ALL_PLANETS)
@pytest.mark.parametrize("lat", [-66.0, 0.0, 66.0])
def test_planet_horizon_estimates_refine_to_scan_truth(body: str, lat: float) -> None:
    jd_day = 2451544.5
    altitude = -0.5667
    fast = rise_set._planet_horizon_events(
        body,
        jd_day,
        lat,
        -0.1,
        altitude,
        1013.25,
        10.0,
    )
    scan = rise_set._scan_horizon_events(
        body,
        jd_day,
        lat,
        -0.1,
        altitude,
        1013.25,
        10.0,
    )
    resolved = scan if fast is None else fast

    assert set(resolved) == set(scan)
    for event in scan:
        assert abs(resolved[event] - scan[event]) * 86400.0 < 0.5
