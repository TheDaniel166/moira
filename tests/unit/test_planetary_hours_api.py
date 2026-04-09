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
