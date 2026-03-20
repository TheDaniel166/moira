"""
Test of the Arctic Circle: Rituals of Polar House Fallback.

This suite verifies the mathematical 'Safety Valve' at extreme latitudes,
ensuring that quadrant systems (Placidus, Koch, Pullen) gracefully transition
to Porphyry before numerical instability occurs.
"""

from datetime import datetime, timezone
import pytest
from moira import Moira
from moira.constants import HouseSystem

@pytest.fixture(scope="session")
def engine():
    return Moira()

def test_north_pole_fallback_triggers_porphyry(engine):
    """
    RITE: The Arctic Transition.
    
    Verifies that at the North Pole (90°N), Placidus houses fallback to 
    Porphyry. We confirm this by comparing the Placidus output at 90°N 
    to the Porphyry output at the same location.
    """
    dt = datetime(2000, 3, 20, 7, 35, tzinfo=timezone.utc)
    
    # 1. Request Placidus at North Pole (should fallback)
    polar_placidus = engine.houses(
        dt,
        latitude=90.0,
        longitude=0.0,
        system=HouseSystem.PLACIDUS
    )
    
    # 2. Request Porphyry at North Pole
    polar_porphyry = engine.houses(
        dt,
        latitude=90.0,
        longitude=0.0,
        system=HouseSystem.PORPHYRY
    )
    
    # Verify the results are identical (to within ε)
    # The vessel 'system' field should still report the REQUESTED system
    assert polar_placidus.system == HouseSystem.PLACIDUS
    
    # But the cusps must match the Porphyry calculation
    for i in range(12):
        assert polar_placidus.cusps[i] == pytest.approx(polar_porphyry.cusps[i], abs=1e-8)
    
    assert polar_placidus.asc == pytest.approx(polar_porphyry.asc, abs=1e-8)
    assert polar_placidus.mc == pytest.approx(polar_porphyry.mc, abs=1e-8)

def test_arctic_threshold_boundary_behavior(engine):
    """
    RITE: The Threshold Guard.
    
    The fallback threshold is defined as |lat| >= 75.0.
    We test 74.9° (No fallback) and 75.1° (Fallback) to verify the limit.
    """
    dt = datetime(2000, 3, 20, 7, 35, tzinfo=timezone.utc)
    
    # 74.9°N: Placidus should remain Placidus
    sub_polar = engine.houses(dt, latitude=74.9, longitude=0.0, system=HouseSystem.PLACIDUS)
    porphyry  = engine.houses(dt, latitude=74.9, longitude=0.0, system=HouseSystem.PORPHYRY)
    
    # Placidus and Porphyry are mathematically distinct systems; 
    # at 74.9° they should NOT match (except by coincidence in very rare conditions).
    assert sub_polar.cusps[1] != pytest.approx(porphyry.cusps[1], abs=0.1)

    # 75.1°N: Placidus should fallback and match Porphyry
    supra_polar = engine.houses(dt, latitude=75.1, longitude=0.0, system=HouseSystem.PLACIDUS)
    supra_porph = engine.houses(dt, latitude=75.1, longitude=0.0, system=HouseSystem.PORPHYRY)
    
    for i in range(12):
        assert supra_polar.cusps[i] == pytest.approx(supra_porph.cusps[i], abs=1e-8)

def test_south_pole_fallback_triggers_porphyry(engine):
    """Verifies symmetry: South Pole (-90°S) must also fallback."""
    dt = datetime(2000, 3, 20, 7, 35, tzinfo=timezone.utc)
    
    polar_placidus = engine.houses(dt, latitude=-90.0, longitude=0.0, system=HouseSystem.PLACIDUS)
    polar_porphyry = engine.houses(dt, latitude=-90.0, longitude=0.0, system=HouseSystem.PORPHYRY)
    
    for i in range(12):
        assert polar_placidus.cusps[i] == pytest.approx(polar_porphyry.cusps[i], abs=1e-8)
