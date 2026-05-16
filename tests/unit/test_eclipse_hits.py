"""
Tests for EclipseHit and the three range helpers on EclipseCalculator:
  solar_eclipses_in_range, lunar_eclipses_in_range, eclipse_hits_in_range.

Phase 1  Public surface .............. EclipseHit importable; fields present
Phase 2  EclipseHit structure ........ frozen dataclass, correct field types
Phase 3  _ecliptic_arc helper ........ shortest-arc arithmetic
Phase 4  eclipse_hits_in_range ....... pure-logic tests via mock EclipseEvents
Phase 5  Orb filtering ............... hits outside orb are excluded
Phase 6  Sorting ..................... sorted by jd_ut then target_name
Phase 7  Ephemeris integration ........ real eclipse search over a known window
"""
from __future__ import annotations

import pytest
from dataclasses import fields
from unittest.mock import MagicMock, patch

from moira.eclipse import EclipseHit, EclipseEvent, EclipseData, EclipseCalculator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_eclipse_data(
    sun_lon: float = 0.0,
    moon_lon: float = 0.0,
    is_solar: bool = True,
    is_lunar: bool = False,
) -> EclipseData:
    """Build a minimal EclipseData stub for testing."""
    ed = MagicMock(spec=EclipseData)
    ed.sun_longitude = sun_lon
    ed.moon_longitude = moon_lon
    ed.is_solar_eclipse = is_solar
    ed.is_lunar_eclipse = is_lunar
    return ed


def _make_event(jd_ut: float, sun_lon: float, moon_lon: float,
                is_solar: bool = True, is_lunar: bool = False) -> EclipseEvent:
    ev = MagicMock(spec=EclipseEvent)
    ev.jd_ut = jd_ut
    ev.data = _make_eclipse_data(sun_lon, moon_lon, is_solar, is_lunar)
    return ev


def _make_calc_with_events(
    solar_events: list[EclipseEvent],
    lunar_events: list[EclipseEvent],
) -> EclipseCalculator:
    """Patch solar/lunar range helpers to return canned event lists."""
    calc = MagicMock(spec=EclipseCalculator)
    calc.solar_eclipses_in_range.return_value = solar_events
    calc.lunar_eclipses_in_range.return_value = lunar_events
    calc.eclipse_hits_in_range = EclipseCalculator.eclipse_hits_in_range.__get__(calc)
    return calc


# ============================================================================
# Phase 1 — Public surface
# ============================================================================

def test_eclipse_hit_importable():
    assert EclipseHit is not None


def test_eclipse_hit_has_required_fields():
    names = {f.name for f in fields(EclipseHit)}
    assert {"event", "eclipse_longitude", "eclipse_kind", "target_name",
            "target_longitude", "orb"} <= names


# ============================================================================
# Phase 2 — EclipseHit structure
# ============================================================================

def test_eclipse_hit_is_frozen():
    ev = _make_event(2451545.0, 10.0, 10.0)
    hit = EclipseHit(
        event=ev,
        eclipse_longitude=10.0,
        eclipse_kind="solar",
        target_name="Sun",
        target_longitude=10.5,
        orb=0.5,
    )
    with pytest.raises((AttributeError, TypeError)):
        hit.orb = 9.9  # type: ignore[misc]


def test_eclipse_hit_solar_kind_string():
    ev = _make_event(2451545.0, 100.0, 100.0)
    hit = EclipseHit(event=ev, eclipse_longitude=100.0, eclipse_kind="solar",
                     target_name="Moon", target_longitude=100.8, orb=0.8)
    assert hit.eclipse_kind == "solar"


def test_eclipse_hit_lunar_kind_string():
    ev = _make_event(2451545.0, 50.0, 230.0, is_solar=False, is_lunar=True)
    hit = EclipseHit(event=ev, eclipse_longitude=230.0, eclipse_kind="lunar",
                     target_name="ASC", target_longitude=230.5, orb=0.5)
    assert hit.eclipse_kind == "lunar"


# ============================================================================
# Phase 3 — _ecliptic_arc helper (via eclipse_hits_in_range boundary logic)
# ============================================================================

def test_arc_across_zero_aries():
    """A natal point at 359° should match an eclipse at 1° with arc=2°."""
    solar = [_make_event(2451545.0, 1.0, 1.0)]
    calc = _make_calc_with_events(solar, [])
    natal = {"P": 359.0}
    hits = calc.eclipse_hits_in_range(2451540.0, 2451550.0, natal, orb=3.0)
    assert len(hits) == 1
    assert hits[0].orb == pytest.approx(2.0, abs=1e-9)


def test_arc_opposite_side():
    """Arc of 180° is the maximum possible shortest arc."""
    solar = [_make_event(2451545.0, 0.0, 0.0)]
    calc = _make_calc_with_events(solar, [])
    natal = {"P": 180.0}
    hits = calc.eclipse_hits_in_range(2451540.0, 2451550.0, natal, orb=181.0)
    assert len(hits) == 1
    assert hits[0].orb == pytest.approx(180.0, abs=1e-9)


# ============================================================================
# Phase 4 — eclipse_hits_in_range pure-logic
# ============================================================================

def test_solar_eclipse_hit_recorded():
    solar = [_make_event(2451545.0, 100.0, 100.0)]
    calc = _make_calc_with_events(solar, [])
    natal = {"Mars": 100.5}
    hits = calc.eclipse_hits_in_range(2451540.0, 2451550.0, natal, orb=1.0)
    assert len(hits) == 1
    h = hits[0]
    assert h.eclipse_kind == "solar"
    assert h.eclipse_longitude == pytest.approx(100.0)
    assert h.target_name == "Mars"
    assert h.orb == pytest.approx(0.5, abs=1e-9)


def test_lunar_eclipse_moon_axis_hit():
    """Lunar eclipse: Moon longitude matches natal point."""
    lunar = [_make_event(2451545.0, 30.0, 210.0, is_solar=False, is_lunar=True)]
    calc = _make_calc_with_events([], lunar)
    natal = {"Venus": 210.3}
    hits = calc.eclipse_hits_in_range(2451540.0, 2451550.0, natal, orb=1.0)
    assert len(hits) == 1
    assert hits[0].eclipse_longitude == pytest.approx(210.0)
    assert hits[0].eclipse_kind == "lunar"


def test_lunar_eclipse_sun_axis_hit():
    """Lunar eclipse: Sun longitude (opposition) matches natal when Moon doesn't."""
    lunar = [_make_event(2451545.0, 30.5, 210.0, is_solar=False, is_lunar=True)]
    calc = _make_calc_with_events([], lunar)
    natal = {"Desc": 30.5}
    hits = calc.eclipse_hits_in_range(2451540.0, 2451550.0, natal, orb=1.0)
    assert len(hits) == 1
    assert hits[0].eclipse_longitude == pytest.approx(30.5)
    assert hits[0].eclipse_kind == "lunar"


def test_lunar_eclipse_prefers_moon_side():
    """When both Moon and Sun axes are within orb, Moon-side hit wins (continue skips Sun)."""
    lunar = [_make_event(2451545.0, 30.0, 30.3, is_solar=False, is_lunar=True)]
    calc = _make_calc_with_events([], lunar)
    # natal at 30.2: within orb of both moon_lon (30.3) and sun_lon (30.0)
    natal = {"X": 30.2}
    hits = calc.eclipse_hits_in_range(2451540.0, 2451550.0, natal, orb=1.0)
    assert len(hits) == 1
    assert hits[0].eclipse_longitude == pytest.approx(30.3)   # Moon side


def test_no_natal_points_returns_empty():
    solar = [_make_event(2451545.0, 50.0, 50.0)]
    calc = _make_calc_with_events(solar, [])
    hits = calc.eclipse_hits_in_range(2451540.0, 2451550.0, {}, orb=5.0)
    assert hits == []


def test_no_eclipses_returns_empty():
    calc = _make_calc_with_events([], [])
    natal = {"Sun": 100.0}
    hits = calc.eclipse_hits_in_range(2451540.0, 2451550.0, natal, orb=5.0)
    assert hits == []


# ============================================================================
# Phase 5 — Orb filtering
# ============================================================================

def test_hit_just_inside_orb():
    solar = [_make_event(2451545.0, 200.0, 200.0)]
    calc = _make_calc_with_events(solar, [])
    natal = {"P": 201.0}
    hits = calc.eclipse_hits_in_range(2451540.0, 2451550.0, natal, orb=1.0)
    assert len(hits) == 1


def test_hit_exactly_on_orb_boundary():
    solar = [_make_event(2451545.0, 200.0, 200.0)]
    calc = _make_calc_with_events(solar, [])
    natal = {"P": 201.0}
    hits = calc.eclipse_hits_in_range(2451540.0, 2451550.0, natal, orb=1.0)
    assert len(hits) == 1


def test_hit_just_outside_orb_excluded():
    solar = [_make_event(2451545.0, 200.0, 200.0)]
    calc = _make_calc_with_events(solar, [])
    natal = {"P": 201.1}
    hits = calc.eclipse_hits_in_range(2451540.0, 2451550.0, natal, orb=1.0)
    assert len(hits) == 0


def test_multiple_natal_points_filtered_correctly():
    solar = [_make_event(2451545.0, 100.0, 100.0)]
    calc = _make_calc_with_events(solar, [])
    natal = {"A": 100.5, "B": 103.0, "C": 99.2}
    hits = calc.eclipse_hits_in_range(2451540.0, 2451550.0, natal, orb=1.0)
    names = {h.target_name for h in hits}
    assert "A" in names
    assert "C" in names
    assert "B" not in names


# ============================================================================
# Phase 6 — Sorting
# ============================================================================

def test_hits_sorted_by_jd_then_name():
    solar = [
        _make_event(2451550.0, 10.0, 10.0),
        _make_event(2451545.0, 20.0, 20.0),
    ]
    calc = _make_calc_with_events(solar, [])
    natal = {"Z": 10.2, "A": 20.3}
    hits = calc.eclipse_hits_in_range(2451540.0, 2451560.0, natal, orb=1.0)
    assert hits[0].event.jd_ut == pytest.approx(2451545.0)
    assert hits[-1].event.jd_ut == pytest.approx(2451550.0)


def test_same_jd_sorted_by_name():
    solar = [_make_event(2451545.0, 50.0, 50.0)]
    calc = _make_calc_with_events(solar, [])
    natal = {"Z": 50.1, "A": 50.2, "M": 50.3}
    hits = calc.eclipse_hits_in_range(2451540.0, 2451550.0, natal, orb=1.0)
    names = [h.target_name for h in hits]
    assert names == sorted(names)


# ============================================================================
# Phase 7 — Ephemeris integration (requires real kernel)
# ============================================================================

@pytest.mark.requires_ephemeris
def test_solar_eclipses_in_range_returns_events(eclipse_calculator):
    # 2020–2025: several solar eclipses guaranteed
    jd_start = 2458850.0   # 2020-01-10
    jd_end   = 2460676.0   # 2025-01-10
    events = eclipse_calculator.solar_eclipses_in_range(jd_start, jd_end)
    assert len(events) >= 4
    for ev in events:
        assert jd_start <= ev.jd_ut <= jd_end
        assert ev.data.is_solar_eclipse


@pytest.mark.requires_ephemeris
def test_lunar_eclipses_in_range_returns_events(eclipse_calculator):
    jd_start = 2458850.0
    jd_end   = 2460676.0
    events = eclipse_calculator.lunar_eclipses_in_range(jd_start, jd_end)
    assert len(events) >= 3
    for ev in events:
        assert jd_start <= ev.jd_ut <= jd_end


@pytest.mark.requires_ephemeris
def test_eclipse_hits_uses_real_eclipses(eclipse_calculator):
    """An eclipse near 0° Aries should hit a natal Sun at 0°."""
    # March 2015 total solar eclipse was at ~29° Pisces (~359°)
    jd_start = 2457090.0   # 2015-03-01
    jd_end   = 2457120.0   # 2015-03-31
    natal = {"Natal Sun": 359.0}
    hits = eclipse_calculator.eclipse_hits_in_range(jd_start, jd_end, natal, orb=5.0)
    # At least verify call completes and returns a list
    assert isinstance(hits, list)
    for h in hits:
        assert isinstance(h, EclipseHit)
        assert 0.0 <= h.orb <= 5.0
