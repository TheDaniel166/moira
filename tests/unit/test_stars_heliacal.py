from __future__ import annotations

from dataclasses import dataclass

import pytest

import moira.stars as stars
from moira.star_types import HeliacalEvent


@dataclass
class _FakeBody:
    longitude: float
    latitude: float = 0.0
    magnitude: float = 1.0


def test_heliacal_rising_event_returns_found_event(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("moira.julian.ut_to_tt", lambda jd: jd)
    monkeypatch.setattr(stars, "star_at", lambda name, jd_tt, **_: _FakeBody(100.0, magnitude=1.2))
    monkeypatch.setattr("moira.planets.planet_at", lambda body, jd_tt: _FakeBody(114.5))
    monkeypatch.setattr("moira.heliacal._find_sun_at_alt", lambda *args, **kwargs: 2451545.25)
    monkeypatch.setattr("moira.rise_set._altitude", lambda *args, **kwargs: 7.5)

    event = stars.heliacal_rising_event("Sirius", 2451545.0, 31.2, 29.9, arcus_visionis=10.0, search_days=30)

    assert isinstance(event, HeliacalEvent)
    assert event.is_found is True
    assert event.jd_ut == pytest.approx(2451545.25)
    assert event.event_kind == "heliacal_rising"
    assert event.computation_truth is not None
    assert event.computation_truth.search_days == 30
    assert event.computation_truth.arcus_visionis == pytest.approx(10.0)
    assert event.classification is not None
    assert event.classification.visibility_state == "found"


def test_heliacal_setting_event_returns_last_visible_morning(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("moira.julian.ut_to_tt", lambda jd: jd)

    def _fake_star_at(name: str, jd_tt: float, **_: object) -> _FakeBody:
        return _FakeBody(100.0, magnitude=1.2)

    def _fake_planet_at(body: str, jd_tt: float) -> _FakeBody:
        if jd_tt < 2451546.0:
            return _FakeBody(114.5)
        return _FakeBody(104.0)

    monkeypatch.setattr(stars, "star_at", _fake_star_at)
    monkeypatch.setattr("moira.planets.planet_at", _fake_planet_at)
    monkeypatch.setattr("moira.heliacal._find_sun_at_alt", lambda jd_midnight, *args, **kwargs: jd_midnight + 0.25)
    monkeypatch.setattr("moira.rise_set._altitude", lambda *args, **kwargs: 6.0)

    event = stars.heliacal_setting_event("Sirius", 2451545.0, 31.2, 29.9, arcus_visionis=10.0, search_days=30)

    assert event.is_found is True
    assert event.jd_ut == pytest.approx(2451545.25)
    assert event.event_kind == "heliacal_setting"
    assert event.computation_truth is not None
    assert event.computation_truth.qualifying_day_offset == 0


def test_heliacal_rising_returns_none_when_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("moira.julian.ut_to_tt", lambda jd: jd)
    monkeypatch.setattr(stars, "star_at", lambda name, jd_tt, **_: _FakeBody(100.0, magnitude=2.0))
    monkeypatch.setattr("moira.planets.planet_at", lambda body, jd_tt: _FakeBody(100.5))

    assert stars.heliacal_rising("Sirius", 2451545.0, 31.2, 29.9, arcus_visionis=10.0, search_days=5) is None


def test_heliacal_event_rejects_invalid_arcus() -> None:
    with pytest.raises(ValueError, match="arcus_visionis must be a positive finite value"):
        stars.heliacal_rising_event("Sirius", 2451545.0, 31.2, 29.9, arcus_visionis=0.0)
