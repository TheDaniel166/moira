from __future__ import annotations

import math

import pytest

from moira.constants import Body
from moira.planets import planet_at
from moira.transits_aspects import (
    _find_candidate_windows_native,
    find_aspect_transits,
)


@pytest.mark.requires_ephemeris
def test_native_candidate_windows_accept_frozen_longitude(planetary_reader, jd_j2000) -> None:
    saturn = planet_at(Body.SATURN, jd_j2000, reader=planetary_reader).longitude
    target = (saturn + 5.0) % 360.0
    windows = _find_candidate_windows_native(
        Body.SATURN,
        target,
        0.0,
        jd_j2000,
        jd_j2000 + 400.0,
        1.0,
        planetary_reader,
    )
    assert windows is not None
    assert isinstance(windows, list)
    assert windows, "Saturn should conjunct a longitude 5° ahead within 400 days"


@pytest.mark.requires_ephemeris
def test_find_aspect_transits_numeric_target_matches_python_fallback(
    planetary_reader,
    jd_j2000,
    monkeypatch,
) -> None:
    jd_start = jd_j2000
    jd_end = jd_start + 400.0
    mars = planet_at(Body.MARS, jd_start, reader=planetary_reader).longitude
    target = (mars + 8.0) % 360.0
    native_events = find_aspect_transits(
        Body.MARS,
        target,
        90.0,
        1.0,
        jd_start,
        jd_end,
        reader=planetary_reader,
    )
    assert native_events

    monkeypatch.setattr(
        "moira.transits_aspects._find_candidate_windows_native",
        lambda *args, **kwargs: None,
    )
    fallback_events = find_aspect_transits(
        Body.MARS,
        target,
        90.0,
        1.0,
        jd_start,
        jd_end,
        reader=planetary_reader,
    )
    assert [round(event.jd_exact, 5) for event in native_events] == [
        round(event.jd_exact, 5) for event in fallback_events
    ]


@pytest.mark.requires_ephemeris
def test_find_aspect_transits_to_longitudes_matches_single_searches(
    planetary_reader,
    jd_j2000,
) -> None:
    jd_start = jd_j2000
    jd_end = jd_start + 400.0
    jupiter = planet_at(Body.JUPITER, jd_start, reader=planetary_reader).longitude
    specs = (
        ((jupiter + 4.0) % 360.0, 0.0, 1.0),
        ((jupiter + 6.0) % 360.0, 0.0, 1.0),
    )
    from moira.transits_aspects import find_aspect_transits_to_longitudes

    grid = find_aspect_transits_to_longitudes(
        Body.JUPITER,
        specs,
        jd_start,
        jd_end,
        reader=planetary_reader,
    )
    singles = []
    for longitude, angle, orb in specs:
        singles.extend(
            find_aspect_transits(
                Body.JUPITER,
                longitude,
                angle,
                orb,
                jd_start,
                jd_end,
                reader=planetary_reader,
            )
        )
    grid_keys = sorted((round(event.jd_exact, 5), float(event.target), event.angle) for event in grid)
    single_keys = sorted((round(event.jd_exact, 5), float(event.target), event.angle) for event in singles)
    assert grid_keys == single_keys
    assert grid_keys, "Jupiter should hit at least one frozen longitude in 400 days"
    for event in grid:
        assert math.isfinite(event.jd_exact)
        assert event.body == Body.JUPITER


# ---------------------------------------------------------------------------
# Series provider (spec 2026-09-02 natal grid series provider)
# ---------------------------------------------------------------------------

from moira.transits_aspects import (  # noqa: E402
    LongitudeSeries,
    _longitude_series,
    _sample_resolver_series,
    _series_max_circular_step,
)


def test_sample_resolver_series_uses_the_transit_resolver(planetary_reader, jd_j2000, monkeypatch) -> None:
    calls: list[float] = []

    def fake_resolve(spec, jd, reader):
        calls.append(jd)
        return (jd - jd_j2000) * 10.0 % 360.0

    monkeypatch.setattr("moira.transits_aspects._resolve_longitude", fake_resolve)
    series = _sample_resolver_series("True Node", jd_j2000, jd_j2000 + 3.0, 1.0, planetary_reader)
    assert isinstance(series, LongitudeSeries)
    assert series.tier == "resolver"
    assert series.jd_start == jd_j2000
    assert series.step_days == 1.0
    assert series.values == (0.0, 10.0, 20.0, 30.0)
    assert calls == [jd_j2000, jd_j2000 + 1.0, jd_j2000 + 2.0, jd_j2000 + 3.0]


def test_series_max_circular_step_wraps_at_360() -> None:
    assert _series_max_circular_step((350.0, 5.0, 20.0)) == pytest.approx(15.0)
    assert _series_max_circular_step((10.0,)) == 0.0


def test_longitude_series_halves_the_step_when_a_sample_jumps_a_quarter_turn(
    planetary_reader, jd_j2000, monkeypatch
) -> None:
    # 100°/day at a 1-day step trips the guard; at 0.5 day it is 50°/step and passes.
    monkeypatch.setattr(
        "moira.transits_aspects._resolve_longitude",
        lambda spec, jd, reader: ((jd - jd_j2000) * 100.0) % 360.0,
    )
    series = _longitude_series("Mean Node", jd_j2000, jd_j2000 + 4.0, 1.0, planetary_reader)
    assert series is not None
    assert series.tier == "resolver"
    assert series.step_days == 0.5
    assert _series_max_circular_step(series.values) <= 90.0


def test_longitude_series_gives_up_after_four_halvings(planetary_reader, jd_j2000, monkeypatch) -> None:
    # A resolver that always reports a 100° jump between consecutive samples,
    # whatever the step, can never satisfy the guard.
    counter = {"n": 0}

    def hostile(spec, jd, reader):
        counter["n"] += 1
        return (counter["n"] * 100.0) % 360.0

    monkeypatch.setattr("moira.transits_aspects._resolve_longitude", hostile)
    assert _longitude_series("Mean Node", jd_j2000, jd_j2000 + 4.0, 1.0, planetary_reader) is None
