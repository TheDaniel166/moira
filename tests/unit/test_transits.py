from __future__ import annotations

from datetime import datetime, timezone

import pytest

from moira.constants import Body
from moira.fixed_stars import fixed_star_at
from moira.julian import jd_from_datetime, ut_to_tt
from moira.nodes import true_node
from moira.planets import planet_at
from moira.transits import (
    TransitEvent,
    find_ingresses,
    find_transits,
    last_full_moon,
    last_new_moon,
    lunar_return,
    next_transit,
    planet_return,
    prenatal_syzygy,
    solar_return,
)


def _angle_diff(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


@pytest.mark.requires_ephemeris
def test_next_transit_finds_exact_direct_crossing_for_sun() -> None:
    start = jd_from_datetime(datetime(2024, 3, 20, 0, 0, tzinfo=timezone.utc))
    target = 0.0

    event = next_transit(Body.SUN, target, start - 2.0, direction="direct", max_days=10.0)

    assert isinstance(event, TransitEvent)
    assert event is not None
    assert event.body == Body.SUN
    assert event.direction == "direct"
    assert _angle_diff(planet_at(Body.SUN, event.jd_ut).longitude, target) < 1e-3


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    ("body", "target", "start_dt", "max_days", "expected_direction"),
    [
        (Body.VENUS, 330.0, datetime(2025, 1, 1, tzinfo=timezone.utc), 120.0, "direct"),
        (Body.MARS, 120.0, datetime(2024, 5, 1, tzinfo=timezone.utc), 220.0, "direct"),
        (Body.JUPITER, 60.0, datetime(2024, 1, 1, tzinfo=timezone.utc), 600.0, "direct"),
        (Body.SATURN, 345.0, datetime(2024, 1, 1, tzinfo=timezone.utc), 365.0, "direct"),
        (Body.PLUTO, 300.0, datetime(2024, 1, 1, tzinfo=timezone.utc), 120.0, "direct"),
    ],
)
def test_next_transit_finds_exact_crossing_for_multiple_bodies(
    body: str,
    target: float,
    start_dt: datetime,
    max_days: float,
    expected_direction: str,
) -> None:
    event = next_transit(body, target, jd_from_datetime(start_dt), direction="either", max_days=max_days)

    assert event is not None
    assert event.body == body
    assert event.direction == expected_direction
    assert _angle_diff(planet_at(body, event.jd_ut).longitude, target) < 1e-3


@pytest.mark.requires_ephemeris
def test_find_transits_captures_mercury_retrograde_multi_passes() -> None:
    start = jd_from_datetime(datetime(2023, 12, 1, 0, 0, tzinfo=timezone.utc))
    end = jd_from_datetime(datetime(2024, 1, 20, 0, 0, tzinfo=timezone.utc))
    natal_point = 270.0

    events = find_transits(Body.MERCURY, natal_point, start, end)

    assert len(events) >= 3
    assert events == sorted(events, key=lambda e: e.jd_ut)
    assert {event.direction for event in events} >= {"direct", "retrograde"}
    for event in events:
        assert _angle_diff(planet_at(Body.MERCURY, event.jd_ut).longitude, natal_point) < 1e-3


@pytest.mark.requires_ephemeris
def test_find_ingresses_detects_both_directions_for_mercury_window() -> None:
    start = jd_from_datetime(datetime(2023, 12, 1, 0, 0, tzinfo=timezone.utc))
    end = jd_from_datetime(datetime(2024, 1, 20, 0, 0, tzinfo=timezone.utc))

    events = find_ingresses(Body.MERCURY, start, end)

    assert events
    assert events == sorted(events, key=lambda e: e.jd_ut)
    assert any(event.direction == "direct" for event in events)
    assert any(event.direction == "retrograde" for event in events)
    for event in events:
        target = event.sign_longitude
        assert _angle_diff(planet_at(Body.MERCURY, event.jd_ut).longitude, target) < 1e-3


@pytest.mark.requires_ephemeris
def test_next_transit_supports_fixed_star_targets() -> None:
    event = next_transit(Body.VENUS, "Sirius", jd_from_datetime(datetime(2024, 1, 1, tzinfo=timezone.utc)), max_days=365.0)

    assert event is not None
    assert event.body == Body.VENUS
    target_lon = fixed_star_at("Sirius", ut_to_tt(event.jd_ut)).longitude
    assert _angle_diff(planet_at(Body.VENUS, event.jd_ut).longitude, target_lon) < 1e-3


@pytest.mark.requires_ephemeris
def test_next_transit_supports_node_targets() -> None:
    event = next_transit(Body.MARS, Body.TRUE_NODE, jd_from_datetime(datetime(2024, 1, 1, tzinfo=timezone.utc)), max_days=800.0)

    assert event is not None
    assert event.body == Body.MARS
    target_lon = true_node(event.jd_ut).longitude
    assert _angle_diff(planet_at(Body.MARS, event.jd_ut).longitude, target_lon) < 1e-3


@pytest.mark.requires_ephemeris
def test_solar_return_matches_solar_transit_to_natal_longitude() -> None:
    natal_dt = datetime(1990, 7, 11, 12, 0, tzinfo=timezone.utc)
    natal_sun_lon = planet_at(Body.SUN, jd_from_datetime(natal_dt)).longitude

    jd_return = solar_return(natal_sun_lon, 2024)
    returned_sun_lon = planet_at(Body.SUN, jd_return).longitude

    assert _angle_diff(returned_sun_lon, natal_sun_lon) < 1e-3


@pytest.mark.requires_ephemeris
def test_lunar_and_generic_planet_return_agree_for_moon() -> None:
    natal_dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    natal_moon_lon = planet_at(Body.MOON, jd_from_datetime(natal_dt)).longitude
    start = jd_from_datetime(datetime(2000, 1, 10, 0, 0, tzinfo=timezone.utc))

    jd_lunar = lunar_return(natal_moon_lon, start)
    jd_generic = planet_return(Body.MOON, natal_moon_lon, start)

    assert jd_lunar == pytest.approx(jd_generic, abs=1e-6)
    assert _angle_diff(planet_at(Body.MOON, jd_lunar).longitude, natal_moon_lon) < 1e-3


@pytest.mark.requires_ephemeris
def test_mercury_return_uses_geocentric_search_window_not_orbital_period() -> None:
    natal_dt = datetime(1995, 3, 15, 6, 0, tzinfo=timezone.utc)
    start = jd_from_datetime(datetime(1995, 3, 16, 0, 0, tzinfo=timezone.utc))
    natal_lon = planet_at(Body.MERCURY, jd_from_datetime(natal_dt)).longitude

    jd_return = planet_return(Body.MERCURY, natal_lon, start, direction="either")

    assert jd_return > start
    assert _angle_diff(planet_at(Body.MERCURY, jd_return).longitude, natal_lon) < 1e-3


@pytest.mark.requires_ephemeris
def test_last_new_moon_and_full_moon_hit_expected_syzygies() -> None:
    ref = jd_from_datetime(datetime(2024, 4, 20, 0, 0, tzinfo=timezone.utc))

    jd_nm = last_new_moon(ref)
    jd_fm = last_full_moon(ref)

    nm_sep = _angle_diff(
        planet_at(Body.MOON, jd_nm).longitude,
        planet_at(Body.SUN, jd_nm).longitude,
    )
    fm_sep = _angle_diff(
        planet_at(Body.MOON, jd_fm).longitude,
        (planet_at(Body.SUN, jd_fm).longitude + 180.0) % 360.0,
    )

    assert jd_nm < ref
    assert jd_fm < ref
    assert nm_sep < 1e-3
    assert fm_sep < 1e-3


@pytest.mark.requires_ephemeris
def test_prenatal_syzygy_returns_latest_of_new_or_full_moon() -> None:
    ref = jd_from_datetime(datetime(2024, 4, 20, 0, 0, tzinfo=timezone.utc))

    jd_syzygy, phase = prenatal_syzygy(ref)
    jd_nm = last_new_moon(ref)
    jd_fm = last_full_moon(ref)

    assert phase in {"New Moon", "Full Moon"}
    assert jd_syzygy == max(jd_nm, jd_fm)


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_transit_stress_matrix_remains_coherent() -> None:
    transit_cases = [
        (Body.SUN, 0.0, datetime(2024, 3, 15, tzinfo=timezone.utc), datetime(2024, 3, 30, tzinfo=timezone.utc)),
        (Body.MERCURY, 270.0, datetime(2023, 12, 1, tzinfo=timezone.utc), datetime(2024, 1, 20, tzinfo=timezone.utc)),
        (Body.VENUS, 330.0, datetime(2025, 1, 1, tzinfo=timezone.utc), datetime(2025, 2, 28, tzinfo=timezone.utc)),
        (Body.MARS, 120.0, datetime(2024, 5, 1, tzinfo=timezone.utc), datetime(2024, 12, 1, tzinfo=timezone.utc)),
        (Body.JUPITER, 60.0, datetime(2024, 1, 1, tzinfo=timezone.utc), datetime(2025, 6, 1, tzinfo=timezone.utc)),
        (Body.SATURN, 345.0, datetime(2024, 1, 1, tzinfo=timezone.utc), datetime(2024, 12, 31, tzinfo=timezone.utc)),
    ]

    seen_event_fingerprints: set[tuple[str, int, str]] = set()

    for body, target, start_dt, end_dt in transit_cases:
        jd_start = jd_from_datetime(start_dt)
        jd_end = jd_from_datetime(end_dt)

        events = find_transits(body, target, jd_start, jd_end)
        assert events
        assert events == sorted(events, key=lambda e: e.jd_ut)

        if len(events) > 1:
            assert len({round(event.jd_ut, 6) for event in events}) == len(events)

        for event in events:
            assert jd_start <= event.jd_ut <= jd_end
            assert event.direction in {"direct", "retrograde"}
            assert _angle_diff(planet_at(body, event.jd_ut).longitude, target) < 1e-3
            seen_event_fingerprints.add((body, int(round(event.jd_ut)), event.direction))

        first = next_transit(body, target, jd_start, max_days=(jd_end - jd_start) + 1.0)
        assert first is not None
        assert first.jd_ut == pytest.approx(events[0].jd_ut, abs=1e-6)

    assert len(seen_event_fingerprints) >= len(transit_cases)

    ingress_cases = [
        (Body.MERCURY, datetime(2023, 12, 1, tzinfo=timezone.utc), datetime(2024, 1, 20, tzinfo=timezone.utc)),
        (Body.VENUS, datetime(2025, 2, 1, tzinfo=timezone.utc), datetime(2025, 5, 1, tzinfo=timezone.utc)),
        (Body.MARS, datetime(2024, 10, 1, tzinfo=timezone.utc), datetime(2025, 2, 1, tzinfo=timezone.utc)),
    ]

    for body, start_dt, end_dt in ingress_cases:
        jd_start = jd_from_datetime(start_dt)
        jd_end = jd_from_datetime(end_dt)
        ingresses = find_ingresses(body, jd_start, jd_end)

        assert ingresses
        assert ingresses == sorted(ingresses, key=lambda e: e.jd_ut)
        assert len({round(event.jd_ut, 6) for event in ingresses}) == len(ingresses)

        for event in ingresses:
            assert jd_start <= event.jd_ut <= jd_end
            assert _angle_diff(planet_at(body, event.jd_ut).longitude, event.sign_longitude) < 1e-3


@pytest.mark.requires_ephemeris
@pytest.mark.slow
def test_return_and_syzygy_stress_matrix_remains_exact() -> None:
    natal_cases = [
        (Body.SUN, datetime(1990, 7, 11, 12, 0, tzinfo=timezone.utc), datetime(2024, 1, 1, tzinfo=timezone.utc)),
        (Body.MOON, datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc), datetime(2000, 1, 10, tzinfo=timezone.utc)),
        (Body.MERCURY, datetime(1995, 3, 15, 6, 0, tzinfo=timezone.utc), datetime(1995, 3, 16, tzinfo=timezone.utc)),
        (Body.VENUS, datetime(1988, 11, 2, 18, 0, tzinfo=timezone.utc), datetime(1989, 1, 1, tzinfo=timezone.utc)),
        (Body.MARS, datetime(1984, 4, 8, 0, 0, tzinfo=timezone.utc), datetime(1985, 1, 1, tzinfo=timezone.utc)),
    ]

    for body, natal_dt, start_dt in natal_cases:
        natal_lon = planet_at(body, jd_from_datetime(natal_dt)).longitude
        jd_start = jd_from_datetime(start_dt)
        jd_return = planet_return(body, natal_lon, jd_start, direction="either")

        assert jd_return >= jd_start
        assert _angle_diff(planet_at(body, jd_return).longitude, natal_lon) < 1e-3

        if body == Body.SUN:
            expected = solar_return(natal_lon, 2024)
            assert jd_return == pytest.approx(expected, abs=1e-6)
        if body == Body.MOON:
            expected = lunar_return(natal_lon, jd_start)
            assert jd_return == pytest.approx(expected, abs=1e-6)

    syzygy_refs = [
        datetime(2024, 4, 20, tzinfo=timezone.utc),
        datetime(2024, 9, 20, tzinfo=timezone.utc),
        datetime(2025, 1, 20, tzinfo=timezone.utc),
    ]

    for ref_dt in syzygy_refs:
        ref = jd_from_datetime(ref_dt)
        jd_nm = last_new_moon(ref)
        jd_fm = last_full_moon(ref)
        jd_syzygy, phase = prenatal_syzygy(ref)

        assert jd_nm < ref
        assert jd_fm < ref
        assert jd_syzygy == max(jd_nm, jd_fm)
        assert phase == ("New Moon" if jd_nm >= jd_fm else "Full Moon")

        nm_sep = _angle_diff(
            planet_at(Body.MOON, jd_nm).longitude,
            planet_at(Body.SUN, jd_nm).longitude,
        )
        fm_sep = _angle_diff(
            planet_at(Body.MOON, jd_fm).longitude,
            (planet_at(Body.SUN, jd_fm).longitude + 180.0) % 360.0,
        )
        assert nm_sep < 1e-3
        assert fm_sep < 1e-3
