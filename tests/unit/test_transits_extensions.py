import time
import pytest
from moira.transits_aspects import find_aspect_transits
from moira.transits_equatorial import find_declination_transits
from moira.transits_houses import find_house_ingresses
from moira.constants import Body

def test_aspect_transits_comprehensive_and_audit(moira_engine, jd_j2000, ritual):
    """Verify aspect transit searches and audit their performance."""
    jd_start = jd_j2000
    jd_end = jd_start + 365.25 * 5  # 5 years
    
    # SUMMON
    start_time = time.perf_counter()
    # Find Jupiter square Saturn over 5 years (a very common predictive query)
    events = find_aspect_transits(Body.JUPITER, Body.SATURN, 90.0, 1.0, jd_start, jd_end)
    elapsed = time.perf_counter() - start_time
    
    print(f"\n[Audit] Aspect Transits (Jupiter Square Saturn, 1 degree orb, 5 years scan): {elapsed:.4f} seconds")
    
    # WITNESS
    ritual.witness("aspect_transits_count", len(events))
    if events:
        first = events[0]
        ritual.witness("first_aspect_hit_jd", round(first.jd_exact, 4))
        ritual.witness("first_aspect_retrograde", first.is_retrograde_hit)
    
    # COVENANT
    assert isinstance(events, list)
    for ev in events:
        assert ev.jd_exact >= jd_start
        assert ev.jd_exact <= jd_end
        assert ev.angle == 90.0
        assert ev.orb == 1.0
        # If orb > 0, entering and leaving boundaries MUST exist and enclose the exact hit
        assert ev.jd_entering is not None
        assert ev.jd_leaving is not None
        assert ev.jd_entering <= ev.jd_exact <= ev.jd_leaving

def test_equatorial_transits_comprehensive_and_audit(moira_engine, jd_j2000, ritual):
    """Verify equatorial (declination parallel) transits and audit performance."""
    jd_start = jd_j2000
    jd_end = jd_start + 365.25  # 1 year scan
    
    # SUMMON
    start_time = time.perf_counter()
    # Mars parallel Venus
    events = find_declination_transits(Body.MARS, Body.VENUS, jd_start, jd_end, is_contra_parallel=False)
    elapsed = time.perf_counter() - start_time
    
    print(f"\n[Audit] Equatorial Parallels (Mars // Venus, 1 year scan): {elapsed:.4f} seconds")
    
    # WITNESS
    ritual.witness("equatorial_transits_count", len(events))
    if events:
        ritual.witness("first_equatorial_hit_jd", round(events[0].jd_exact, 4))
        ritual.witness("first_equatorial_dec", round(events[0].declination, 4))
        
    # COVENANT
    assert isinstance(events, list)
    for ev in events:
        assert ev.jd_exact >= jd_start
        assert ev.jd_exact <= jd_end
        assert ev.is_contra_parallel is False

def test_house_ingresses_comprehensive_and_audit(moira_engine, jd_j2000, ritual):
    """Verify topocentric house ingresses and audit performance."""
    jd_start = jd_j2000
    jd_end = jd_start + 30.0  # 1 month scan
    
    lat, lon = 40.7128, -74.0060  # New York
    
    # SUMMON
    start_time = time.perf_counter()
    # Moon crossing house cusps for a month
    events = find_house_ingresses(Body.MOON, lat, lon, jd_start, jd_end, system="placidus")
    elapsed = time.perf_counter() - start_time
    
    print(f"\n[Audit] House Ingresses (Moon in NY, Placidus, 1 month scan): {elapsed:.4f} seconds")
    
    # WITNESS
    ritual.witness("house_ingress_count", len(events))
    if events:
        ritual.witness("first_house_ingress_jd", round(events[0].jd_exact, 4))
        ritual.witness("first_house_entered", events[0].house_index)
        
    # COVENANT
    assert isinstance(events, list)
    # The moon should cross a house roughly every 2-3 hours, so over 30 days we expect > 100 crossings.
    assert len(events) > 100
    for ev in events:
        assert ev.jd_exact >= jd_start
        assert ev.jd_exact <= jd_end
        assert 1 <= ev.house_index <= 12
