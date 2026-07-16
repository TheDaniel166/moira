"""Regression proofs for bounded and geometrically honest phenomena searches."""

from dataclasses import FrozenInstanceError
import math
from types import SimpleNamespace

import pytest

from moira.constants import Body
import moira.phenomena as phenomena


def _position(body: str, jd_ut: float, **_kwargs) -> SimpleNamespace:
    return SimpleNamespace(
        longitude=jd_ut % 360.0,
        latitude=0.0,
        retrograde=False,
    )


def test_phenomenon_event_is_immutable() -> None:
    event = phenomena.PhenomenonEvent("Mercury", "Perihelion", 1.0, 0.3)

    with pytest.raises(FrozenInstanceError):
        event.value = 99.0


def test_angular_elongation_includes_ecliptic_latitude(monkeypatch) -> None:
    def fake_planet_at(body: str, _jd_ut: float, **_kwargs) -> SimpleNamespace:
        if body == Body.SUN:
            return SimpleNamespace(longitude=0.0, latitude=0.0)
        return SimpleNamespace(longitude=30.0, latitude=10.0)

    monkeypatch.setattr(phenomena, "planet_at", fake_planet_at)

    expected = math.degrees(
        math.acos(math.cos(math.radians(10.0)) * math.cos(math.radians(30.0)))
    )
    assert phenomena._angular_elongation(Body.MERCURY, 0.0, object()) == pytest.approx(expected)
    assert phenomena._angular_elongation(Body.MERCURY, 0.0, object()) > 30.0


def test_greatest_elongation_optimizes_angular_separation(monkeypatch) -> None:
    monkeypatch.setattr(phenomena, "_elongation", lambda *_args: 20.0)
    monkeypatch.setattr(
        phenomena,
        "_angular_elongation",
        lambda _body, jd_ut, _reader: 30.0 - (jd_ut - 5.25) ** 2,
    )

    event = phenomena.greatest_elongation(
        Body.MERCURY, 0.0, direction="east", reader=object(), max_days=10.0,
    )

    assert event is not None
    assert event.jd_ut == pytest.approx(5.25, abs=1e-5)
    assert event.value == pytest.approx(30.0, abs=1e-9)


def test_de441_greatest_elongation_is_a_spherical_local_maximum(reader) -> None:
    event = phenomena.greatest_elongation(
        Body.MERCURY,
        2451545.0,
        direction="east",
        reader=reader,
        max_days=200.0,
    )

    assert event is not None
    center = phenomena._angular_elongation(Body.MERCURY, event.jd_ut, reader)
    assert event.value == pytest.approx(center, abs=1e-10)
    assert center > phenomena._angular_elongation(Body.MERCURY, event.jd_ut - 0.01, reader)
    assert center > phenomena._angular_elongation(Body.MERCURY, event.jd_ut + 0.01, reader)


@pytest.mark.parametrize("direction", ["banana", "EAST", ""])
def test_greatest_elongation_rejects_unknown_direction(direction: str) -> None:
    with pytest.raises(ValueError, match="direction"):
        phenomena.greatest_elongation(
            Body.MERCURY, 2451545.0, direction=direction, reader=object(),
        )


@pytest.mark.parametrize("body", [Body.MARS, Body.SUN, Body.MOON, "Unknown"])
def test_greatest_elongation_rejects_unsupported_body(body: str) -> None:
    with pytest.raises(ValueError, match="Mercury and Venus"):
        phenomena.greatest_elongation(body, 2451545.0, reader=object())


@pytest.mark.parametrize("search", [phenomena.perihelion, phenomena.aphelion])
@pytest.mark.parametrize("body", [Body.SUN, Body.MOON, "Unknown"])
def test_apsides_reject_non_planets(search, body: str) -> None:
    with pytest.raises(ValueError, match="major planet"):
        search(body, 2451545.0, reader=object())


def test_bounded_resonance_is_the_closest_allowed_fraction() -> None:
    assert phenomena.find_closest_resonance(math.pi, max_denominator=5) == (16, 5)
    assert phenomena.find_closest_resonance(0.0843044, max_denominator=50) == (4, 47)


def test_resonance_rejects_identical_bodies() -> None:
    with pytest.raises(ValueError, match="distinct orbital periods"):
        phenomena.resonance(Body.MERCURY, Body.MERCURY)


@pytest.mark.parametrize(
    ("function_name", "replacement_name"),
    [
        ("conjunctions_in_range", "next_conjunction"),
        ("heliocentric_conjunctions_in_range", "next_heliocentric_conjunction"),
    ],
)
def test_conjunction_range_rejects_solver_result_beyond_end(
    monkeypatch, function_name: str, replacement_name: str,
) -> None:
    outside = phenomena.PhenomenonEvent("Sun-Moon", "Conjunction", 10.1, 0.0)
    monkeypatch.setattr(phenomena, replacement_name, lambda *_args, **_kwargs: outside)

    search = getattr(phenomena, function_name)
    assert search(Body.SUN, Body.MOON, 0.0, 10.0, reader=object()) == []


def test_proximity_scan_rejects_opposition_wrap(monkeypatch) -> None:
    def wrapped_separation(_body1, _body2, jd_ut, _reader, apparent=False):
        raw = 170.0 + 20.0 * jd_ut
        return (raw + 180.0) % 360.0 - 180.0

    monkeypatch.setattr(phenomena, "_conjunction_separation", wrapped_separation)
    monkeypatch.setattr(phenomena, "planet_at", _position)

    assert phenomena.proximity_events_in_range(
        Body.SUN, Body.MOON, 0.0, 1.0, threshold_deg=8.0, reader=object(),
    ) == []


def test_proximity_scan_finds_slow_body_threshold_crossing(monkeypatch) -> None:
    monkeypatch.setattr(
        phenomena,
        "_conjunction_separation",
        lambda _b1, _b2, jd_ut, _reader, apparent=False: 10.0 - 0.01 * jd_ut,
    )
    monkeypatch.setattr(phenomena, "planet_at", _position)

    events = phenomena.proximity_events_in_range(
        Body.JUPITER,
        Body.SATURN,
        0.0,
        400.0,
        threshold_deg=8.0,
        reader=object(),
    )

    assert len(events) == 1
    assert events[0].jd_ut == pytest.approx(200.0, abs=1e-7)
    assert events[0].threshold_deg == 8.0
    assert events[0].is_ingress is True


def test_proximity_scan_returns_only_crossings_inside_exact_range(monkeypatch) -> None:
    monkeypatch.setattr(
        phenomena,
        "_conjunction_separation",
        lambda _b1, _b2, jd_ut, _reader, apparent=False: 4.0 * (jd_ut - 5.0),
    )
    monkeypatch.setattr(phenomena, "planet_at", _position)

    assert phenomena.proximity_events_in_range(
        Body.SUN, Body.MERCURY, 4.75, 5.25, threshold_deg=2.0, reader=object(),
    ) == []

    events = phenomena.proximity_events_in_range(
        Body.SUN, Body.MERCURY, 4.0, 6.0, threshold_deg=2.0, reader=object(),
    )
    assert [event.jd_ut for event in events] == pytest.approx([4.5, 5.5], abs=1e-7)
    assert [event.is_ingress for event in events] == [True, False]


def test_cazimi_event_search_uses_exact_shared_threshold(monkeypatch) -> None:
    captured: list[float] = []

    def fake_proximity(_body1, _body2, _start, _end, threshold, _reader):
        captured.append(threshold)
        return []

    monkeypatch.setattr(phenomena, "proximity_events_in_range", fake_proximity)

    assert phenomena.solar_condition_events_in_range(
        Body.MERCURY, 0.0, 1.0, condition="cazimi", reader=object(),
    ) == []
    assert captured == [17.0 / 60.0]
