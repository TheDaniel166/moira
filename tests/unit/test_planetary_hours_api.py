from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

import moira.planetary_hours as planetary_hours_module


def test_planetary_hours_explicit_reader_bypasses_singleton(monkeypatch: pytest.MonkeyPatch) -> None:
    explicit_reader = object()

    monkeypatch.setattr(
        planetary_hours_module,
        "_sunrise_sunset",
        lambda jd_noon, latitude, longitude, reader: (2451545.25, 2451545.75),
    )
    monkeypatch.setattr(
        planetary_hours_module,
        "_refine_sunrise",
        lambda jd_guess, latitude, longitude, reader, is_rise: jd_guess,
    )
    monkeypatch.setattr(
        planetary_hours_module,
        "get_reader",
        lambda: pytest.fail("get_reader should not run when an explicit reader is supplied"),
    )

    result = planetary_hours_module.planetary_hours(2451545.5, 0.0, 0.0, reader=explicit_reader)

    assert len(result.hours) == 24


def test_planetary_hours_day_and_hours_are_immutable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        planetary_hours_module,
        "_sunrise_sunset",
        lambda jd_noon, latitude, longitude, reader: (2451545.25, 2451545.75),
    )
    monkeypatch.setattr(
        planetary_hours_module,
        "_refine_sunrise",
        lambda jd_guess, latitude, longitude, reader, is_rise: jd_guess,
    )
    monkeypatch.setattr(planetary_hours_module, "get_reader", lambda: object())

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
        planetary_hours_module,
        "_sunrise_sunset",
        lambda jd_noon, latitude, longitude, reader: sunrise_sunset_by_noon[jd_noon],
    )
    monkeypatch.setattr(
        planetary_hours_module,
        "_refine_sunrise",
        lambda jd_guess, latitude, longitude, reader, is_rise: jd_guess,
    )
    monkeypatch.setattr(planetary_hours_module, "get_reader", lambda: object())

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
        planetary_hours_module,
        "_sunrise_sunset",
        lambda jd_noon, latitude, longitude, reader: sunrise_sunset_by_noon[jd_noon],
    )
    monkeypatch.setattr(
        planetary_hours_module,
        "_refine_sunrise",
        lambda jd_guess, latitude, longitude, reader, is_rise: jd_guess,
    )
    monkeypatch.setattr(planetary_hours_module, "get_reader", lambda: object())

    result = planetary_hours_module.planetary_hours(2451546.30, 0.0, 0.0)

    assert result.sunrise_jd == pytest.approx(2451545.20)
    assert result.sunset_jd == pytest.approx(2451545.70)
    assert result.hours[0].jd_start == pytest.approx(2451545.20)
    assert result.hours[-1].jd_end == pytest.approx(2451546.20)
    assert result.hour_at(2451545.30) is not None


def test_planetary_hours_preserves_refined_solar_event_locality(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sunrise_sunset_by_noon = {
        2460477.0: (2460476.20, 2460476.80),
        2460478.0: (2460477.20, 2460477.80),
    }

    monkeypatch.setattr(
        planetary_hours_module,
        "_sunrise_sunset",
        lambda jd_noon, latitude, longitude, reader: sunrise_sunset_by_noon[jd_noon],
    )
    monkeypatch.setattr(
        planetary_hours_module,
        "_refine_sunrise",
        lambda jd_guess, latitude, longitude, reader, is_rise: (
            jd_guess if is_rise else jd_guess + 5.0
        ),
    )
    monkeypatch.setattr(planetary_hours_module, "get_reader", lambda: object())

    result = planetary_hours_module.planetary_hours(2460476.50, 40.7128, -74.0060)

    assert result.sunrise_jd == pytest.approx(2460476.20)
    assert result.sunset_jd == pytest.approx(2460476.80)
    assert result.hours[-1].jd_end == pytest.approx(2460477.20)
    assert result.sunrise_jd < result.sunset_jd < result.hours[-1].jd_end
    assert result.hour_at(2460476.50) is not None


def test_planetary_hours_real_solar_window_invariants_common_locations() -> None:
    from moira._kernel_paths import find_planetary_kernel
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
            for current, next_hour in zip(result.hours, result.hours[1:], strict=False):
                assert current.jd_end == pytest.approx(next_hour.jd_start)
                assert current.jd_end > current.jd_start
