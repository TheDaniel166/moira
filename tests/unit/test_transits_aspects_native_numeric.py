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
