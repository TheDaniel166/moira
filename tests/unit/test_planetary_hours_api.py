from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

import moira._local_solar_day as local_solar_day_module
from moira.constants import Body
import moira.planetary_hours as planetary_hours_module


def test_planetary_hours_explicit_reader_bypasses_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    explicit_reader = object()

    monkeypatch.setattr(
        local_solar_day_module,
        "_sunrise_sunset",
        lambda jd_noon, latitude, longitude, reader: (jd_noon - 0.75, jd_noon - 0.25),
    )
    monkeypatch.setattr(
        local_solar_day_module,
        "_refine_sunrise",
        lambda jd_guess, latitude, longitude, reader, is_rise: jd_guess,
    )
    monkeypatch.setattr(
        local_solar_day_module,
        "get_reader",
        lambda: pytest.fail("get_reader should not run when an explicit reader is supplied"),
    )

    result = planetary_hours_module.planetary_hours(2451545.5, 0.0, 0.0, reader=explicit_reader)

    assert len(result.hours) == 24


def test_planetary_hours_day_and_hours_are_immutable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        local_solar_day_module,
        "_sunrise_sunset",
        lambda jd_noon, latitude, longitude, reader: (jd_noon - 0.75, jd_noon - 0.25),
    )
    monkeypatch.setattr(
        local_solar_day_module,
        "_refine_sunrise",
        lambda jd_guess, latitude, longitude, reader, is_rise: jd_guess,
    )
    monkeypatch.setattr(local_solar_day_module, "get_reader", lambda: object())

    result = planetary_hours_module.planetary_hours(2451545.5, 0.0, 0.0)

    assert isinstance(result.hours, tuple)
    with pytest.raises(FrozenInstanceError):
        result.sunrise_jd = 0.0  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        result.hours[0].ruler = "Venus"  # type: ignore[misc]


def test_planetary_hours_uses_previous_sunrise_window_before_today_sunrise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sunrise_sunset_by_noon = {
        2451545.0: (2451544.20, 2451544.70),
        2451546.0: (2451545.20, 2451545.70),
    }

    monkeypatch.setattr(
        local_solar_day_module,
        "_sunrise_sunset",
        lambda jd_noon, latitude, longitude, reader: sunrise_sunset_by_noon[jd_noon],
    )
    monkeypatch.setattr(
        local_solar_day_module,
        "_refine_sunrise",
        lambda jd_guess, latitude, longitude, reader, is_rise: jd_guess,
    )
    monkeypatch.setattr(local_solar_day_module, "get_reader", lambda: object())

    result = planetary_hours_module.planetary_hours(2451545.10, 0.0, 0.0)

    assert result.sunrise_jd == pytest.approx(2451544.20)
    assert result.sunset_jd == pytest.approx(2451544.70)
    assert result.hours[0].jd_start == pytest.approx(2451544.20)
    assert result.hours[-1].jd_end == pytest.approx(2451545.20)
    assert result.hour_at(2451545.10) is not None


def test_planetary_hours_uses_current_window_after_today_sunrise(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sunrise_sunset_by_noon = {
        2451546.0: (2451545.20, 2451545.70),
        2451547.0: (2451546.20, 2451546.70),
    }

    monkeypatch.setattr(
        local_solar_day_module,
        "_sunrise_sunset",
        lambda jd_noon, latitude, longitude, reader: sunrise_sunset_by_noon[jd_noon],
    )
    monkeypatch.setattr(
        local_solar_day_module,
        "_refine_sunrise",
        lambda jd_guess, latitude, longitude, reader, is_rise: jd_guess,
    )
    monkeypatch.setattr(local_solar_day_module, "get_reader", lambda: object())

    result = planetary_hours_module.planetary_hours(2451546.10, 0.0, 0.0)

    assert result.sunrise_jd == pytest.approx(2451545.20)
    assert result.sunset_jd == pytest.approx(2451545.70)
    assert result.hours[0].jd_start == pytest.approx(2451545.20)
    assert result.hours[-1].jd_end == pytest.approx(2451546.20)
    assert result.hour_at(2451546.10) is not None


def test_planetary_hours_rejects_refinement_outside_local_day(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sunrise_sunset_by_noon = {
        2460477.0: (2460476.20, 2460476.80),
        2460478.0: (2460477.20, 2460477.80),
    }

    monkeypatch.setattr(
        local_solar_day_module,
        "_sunrise_sunset",
        lambda jd_noon, latitude, longitude, reader: sunrise_sunset_by_noon[jd_noon],
    )
    monkeypatch.setattr(
        local_solar_day_module,
        "_refine_sunrise",
        lambda jd_guess, latitude, longitude, reader, is_rise: (
            jd_guess if is_rise else jd_guess + 5.0
        ),
    )
    monkeypatch.setattr(local_solar_day_module, "get_reader", lambda: object())

    with pytest.raises(ValueError, match="escaped its local day"):
        planetary_hours_module.planetary_hours(2460476.50, 40.7128, -74.0060)


def test_planetary_hours_real_solar_window_invariants_common_locations() -> None:
    from moira._kernel_paths import find_planetary_kernel
    from moira.planets import sky_position_at
    from moira.spk_reader import SpkReader

    kernel_path = find_planetary_kernel()
    if kernel_path is None:
        pytest.skip("no planetary kernel found")

    cases = [
        (2451545.5, 0.0, 0.0),
        (2460476.5, 40.7128, -74.0060),
        (2460390.5, 51.5074, -0.1278),
        (2460310.5, -33.8688, 151.2093),
    ]

    with SpkReader(kernel_path) as reader:
        for jd, latitude, longitude in cases:
            result = planetary_hours_module.planetary_hours(
                jd,
                latitude,
                longitude,
                reader=reader,
            )
            next_sunrise = result.hours[-1].jd_end

            assert result.sunrise_jd < result.sunset_jd < next_sunrise
            assert 0.0 < result.sunset_jd - result.sunrise_jd < 1.0
            assert 0.0 < next_sunrise - result.sunset_jd < 1.0
            assert len(result.hours) == 24
            assert result.hour_at(jd) is not None
            assert result.hours[0].jd_start == pytest.approx(result.sunrise_jd)
            assert result.hours[11].jd_end == pytest.approx(result.sunset_jd)
            assert result.hours[12].jd_start == pytest.approx(result.sunset_jd)
            assert result.hours[-1].jd_end == pytest.approx(next_sunrise)
            sunrise_altitude = sky_position_at(
                Body.SUN,
                result.sunrise_jd,
                latitude,
                longitude,
                reader=reader,
                refraction=False,
            ).altitude
            sunset_altitude = sky_position_at(
                Body.SUN,
                result.sunset_jd,
                latitude,
                longitude,
                reader=reader,
                refraction=False,
            ).altitude
            assert sunrise_altitude == pytest.approx(-0.833, abs=5e-4)
            assert sunset_altitude == pytest.approx(-0.833, abs=5e-4)
            for current, next_hour in zip(result.hours, result.hours[1:], strict=False):
                assert current.jd_end == pytest.approx(next_hour.jd_start)
                assert current.jd_end > current.jd_start


@pytest.mark.parametrize(
    ("jd", "latitude", "longitude", "message"),
    [
        (float("nan"), 0.0, 0.0, "jd must be finite"),
        (2451545.5, 90.1, 0.0, "latitude must be within"),
        (2451545.5, -90.1, 0.0, "latitude must be within"),
        (2451545.5, 0.0, 180.1, "longitude must be within"),
        (2451545.5, 0.0, -180.1, "longitude must be within"),
    ],
)
def test_planetary_hours_engine_rejects_invalid_inputs(
    jd: float,
    latitude: float,
    longitude: float,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        planetary_hours_module.planetary_hours(
            jd, latitude, longitude, reader=object(),
        )


def test_local_weekday_uses_longitude_and_floor_for_bce() -> None:
    # 2023-12-31 UTC is already local Monday at a Sydney sunrise.
    assert local_solar_day_module._local_weekday_at_sunrise(
        2460310.28, 151.2093,
    ) == 1
    # Negative JDs must floor rather than truncate toward zero.
    sunrise_bce = -1000.2523388558844
    assert local_solar_day_module._local_weekday_at_sunrise(sunrise_bce, 0.0) == 2


def test_real_sydney_monday_begins_with_moon_and_polar_day_fails() -> None:
    from moira._kernel_paths import find_planetary_kernel
    from moira.spk_reader import SpkReader

    kernel_path = find_planetary_kernel()
    if kernel_path is None:
        pytest.skip("no planetary kernel found")

    with SpkReader(kernel_path) as reader:
        sydney = planetary_hours_module.planetary_hours(
            2460310.5416666665,
            -33.8688,
            151.2093,
            reader=reader,
        )
        assert sydney.hours[0].ruler == Body.MOON

        with pytest.raises(ValueError, match="no (sunrise|sunset) altitude crossing"):
            planetary_hours_module.planetary_hours(
                2460482.5,
                89.0,
                0.0,
                reader=reader,
            )
