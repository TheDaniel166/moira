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


from moira.transits import _auto_step, _resolve_longitude  # noqa: E402
from moira.transits_aspects import find_aspect_transits_to_longitudes  # noqa: E402


_JD_TOLERANCE_DAYS = 2e-6  # two solver tolerances: brackets differ, midpoints may not agree exactly


def _event_key(event):
    return (float(event.target), event.angle, event.is_retrograde_hit, event.jd_exact)


def _grid_and_singles(body, jd_start, jd_end, reader, specs):
    """Return (grid, singles) as sorted keys with jd_exact snapped to the shared tolerance.

    Equality of the two lists means: same hits, same target/angle/direction,
    exact times within ``_JD_TOLERANCE_DAYS`` of each other.
    """
    grid = find_aspect_transits_to_longitudes(body, specs, jd_start, jd_end, reader=reader)
    singles = []
    for longitude, angle, orb in specs:
        singles.extend(find_aspect_transits(body, longitude, angle, orb, jd_start, jd_end, reader=reader))
    grid_keys = sorted(_event_key(e) for e in grid)
    single_keys = sorted(_event_key(e) for e in singles)
    assert len(grid_keys) == len(single_keys), (grid_keys, single_keys)
    for g, s_ in zip(grid_keys, single_keys, strict=True):
        assert g[:3] == s_[:3], (g, s_)
        assert abs(g[3] - s_[3]) <= _JD_TOLERANCE_DAYS, (g, s_)
    snapped = [k[:3] for k in grid_keys]
    return snapped, [k[:3] for k in single_keys]


_GRID_ANGLES = ((0.0, 8.0), (60.0, 5.0), (90.0, 7.0), (120.0, 7.0), (180.0, 8.0))


def _grid_specs(anchor_longitude: float):
    longitudes = [(anchor_longitude + offset) % 360.0 for offset in (-12.0, -5.0, 4.0, 37.0, 91.0, 150.0, 212.0, 301.0)]
    return [(lon, angle, orb) for lon in longitudes for angle, orb in _GRID_ANGLES]


@pytest.mark.requires_ephemeris
def test_planet_grid_uses_native_tier_and_matches_singles(planetary_reader, jd_j2000) -> None:
    series = _longitude_series(Body.SATURN, jd_j2000, jd_j2000 + 365.0, _auto_step(Body.SATURN), planetary_reader)
    assert series is not None and series.tier == "native_planet"
    saturn = planet_at(Body.SATURN, jd_j2000, reader=planetary_reader).longitude
    grid, singles = _grid_and_singles(Body.SATURN, jd_j2000, jd_j2000 + 365.0, planetary_reader, _grid_specs(saturn))
    assert grid, 'expected at least one hit in the window'
    assert grid == singles


@pytest.mark.requires_ephemeris
def test_true_node_grid_uses_resolver_tier_and_matches_singles(planetary_reader, jd_j2000) -> None:
    series = _longitude_series(Body.TRUE_NODE, jd_j2000, jd_j2000 + 365.0, _auto_step(Body.TRUE_NODE), planetary_reader)
    assert series is not None and series.tier == "resolver"
    node = _resolve_longitude(Body.TRUE_NODE, jd_j2000, planetary_reader)
    grid, singles = _grid_and_singles(Body.TRUE_NODE, jd_j2000, jd_j2000 + 365.0, planetary_reader, _grid_specs(node))
    assert grid, 'expected at least one hit in the window'
    assert grid == singles


@pytest.mark.requires_ephemeris
def test_true_lilith_grid_matches_singles(planetary_reader, jd_j2000) -> None:
    lilith = _resolve_longitude(Body.TRUE_LILITH, jd_j2000, planetary_reader)
    grid, singles = _grid_and_singles(Body.TRUE_LILITH, jd_j2000, jd_j2000 + 365.0, planetary_reader, _grid_specs(lilith))
    assert grid, 'expected at least one hit in the window'
    assert grid == singles


def test_auto_step_tightens_osculating_points() -> None:
    assert _auto_step(Body.TRUE_NODE) == 0.25
    assert _auto_step(Body.TRUE_LILITH) == 0.25
    assert _auto_step(Body.MEAN_NODE) == 1.0
    assert _auto_step(Body.LILITH) == 1.0


@pytest.mark.requires_ephemeris
def test_grid_falls_back_to_singles_when_no_series(planetary_reader, jd_j2000, monkeypatch) -> None:
    monkeypatch.setattr("moira.transits_aspects._longitude_series", lambda *a, **k: None)
    saturn = planet_at(Body.SATURN, jd_j2000, reader=planetary_reader).longitude
    grid, singles = _grid_and_singles(Body.SATURN, jd_j2000, jd_j2000 + 365.0, planetary_reader, _grid_specs(saturn))
    assert grid, 'expected at least one hit in the window'
    assert grid == singles


from moira.transits_aspects import _native_small_body_series, _signed_diff  # noqa: E402


@pytest.mark.requires_ephemeris
def test_ceres_grid_uses_native_small_body_tier_and_matches_singles(small_body_reader_context, jd_j2000) -> None:
    pool = small_body_reader_context
    series = _longitude_series("Ceres", jd_j2000, jd_j2000 + 365.0, _auto_step("Ceres"), pool)
    assert series is not None and series.tier == "native_small_body"
    ceres = _resolve_longitude("Ceres", jd_j2000, pool)
    grid, singles = _grid_and_singles("Ceres", jd_j2000, jd_j2000 + 365.0, pool, _grid_specs(ceres))
    assert grid, "expected at least one hit in the window"
    assert grid == singles


@pytest.mark.requires_ephemeris
def test_ceres_native_series_agrees_with_resolver_sampling(small_body_reader_context, jd_j2000) -> None:
    pool = small_body_reader_context
    native = _native_small_body_series("Ceres", jd_j2000, jd_j2000 + 30.0, 1.0, pool)
    assert native is not None
    sampled = _sample_resolver_series("Ceres", jd_j2000, jd_j2000 + 30.0, 1.0, pool)
    # geometric native vs apparent resolver: light time on Ceres is minutes, so
    # agreement is a small fraction of a degree, far inside the window guard.
    for a, b in zip(native, sampled.values, strict=True):
        assert abs(_signed_diff(a, b)) < 0.05


@pytest.mark.requires_ephemeris
def test_ceres_grid_falls_to_resolver_when_native_small_body_is_off(
    small_body_reader_context, jd_j2000, monkeypatch
) -> None:
    pool = small_body_reader_context
    monkeypatch.setattr("moira.transits_aspects._native_small_body_series", lambda *a, **k: None)
    series = _longitude_series("Ceres", jd_j2000, jd_j2000 + 365.0, 1.0, pool)
    assert series is not None and series.tier == "resolver"


def test_native_small_body_series_is_none_for_non_asteroids(planetary_reader, jd_j2000) -> None:
    assert _native_small_body_series(Body.SATURN, jd_j2000, jd_j2000 + 10.0, 1.0, planetary_reader) is None
    assert _native_small_body_series(Body.TRUE_NODE, jd_j2000, jd_j2000 + 10.0, 1.0, planetary_reader) is None


@pytest.mark.requires_ephemeris
def test_asteroid_movers_resolve_in_longitude_and_declination_searches(small_body_reader_context, jd_j2000) -> None:
    # Regression: both resolvers passed a keyword asteroid_at() no longer accepts.
    from moira.transits_equatorial import find_declination_transits

    pool = small_body_reader_context
    assert 0.0 <= _resolve_longitude("Ceres", jd_j2000, pool) < 360.0
    events = find_declination_transits("Ceres", "Sun", jd_j2000, jd_j2000 + 60.0, reader=pool)
    assert isinstance(events, list)
