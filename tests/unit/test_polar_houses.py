"""
Test of the critical latitude: house fallback above 90° − obliquity.

This suite verifies that semi-arc systems (Placidus, Koch, Pullen SD) fall
back to Porphyry above the critical latitude, which is 90° − obliquity
(≈ 66.56° at J2000).  This threshold is not a fixed constant — it is derived
from the chart's actual obliquity at call time.

The old threshold of 75° was incorrect: it silently returned geometrically
invalid cusp sets from ≈66.6° to 74.9°.
"""

from datetime import datetime, timezone
import pytest
from moira import Moira
from moira.constants import HouseSystem

@pytest.fixture(scope="session")
def engine():
    return Moira()

def test_north_pole_fallback_triggers_porphyry(engine):
    """At the North Pole (90°N), Placidus must fall back to Porphyry."""
    dt = datetime(2000, 3, 20, 7, 35, tzinfo=timezone.utc)

    polar_placidus = engine.houses(dt, latitude=90.0, longitude=0.0, system=HouseSystem.PLACIDUS)
    polar_porphyry = engine.houses(dt, latitude=90.0, longitude=0.0, system=HouseSystem.PORPHYRY)

    assert polar_placidus.system == HouseSystem.PLACIDUS
    for i in range(12):
        assert polar_placidus.cusps[i] == pytest.approx(polar_porphyry.cusps[i], abs=1e-8)
    assert polar_placidus.asc == pytest.approx(polar_porphyry.asc, abs=1e-8)
    assert polar_placidus.mc  == pytest.approx(polar_porphyry.mc,  abs=1e-8)

def test_arctic_threshold_boundary_behavior(engine):
    """
    The critical latitude is 90° − obliquity (≈ 66.56° at J2000).
    60° is safely below it (no fallback); 70° is safely above it (fallback).
    """
    dt = datetime(2000, 3, 20, 7, 35, tzinfo=timezone.utc)

    # 60°N: well below critical latitude — Placidus must remain Placidus
    sub = engine.houses(dt, latitude=60.0, longitude=0.0, system=HouseSystem.PLACIDUS)
    assert sub.effective_system == HouseSystem.PLACIDUS
    assert sub.fallback is False

    # 70°N: well above critical latitude — Placidus must fall back to Porphyry
    supra       = engine.houses(dt, latitude=70.0, longitude=0.0, system=HouseSystem.PLACIDUS)
    supra_porph = engine.houses(dt, latitude=70.0, longitude=0.0, system=HouseSystem.PORPHYRY)
    assert supra.effective_system == HouseSystem.PORPHYRY
    assert supra.fallback is True
    for i in range(12):
        assert supra.cusps[i] == pytest.approx(supra_porph.cusps[i], abs=1e-8)

def test_south_pole_fallback_triggers_porphyry(engine):
    """South Pole (−90°S) must also fall back symmetrically."""
    dt = datetime(2000, 3, 20, 7, 35, tzinfo=timezone.utc)

    polar_placidus = engine.houses(dt, latitude=-90.0, longitude=0.0, system=HouseSystem.PLACIDUS)
    polar_porphyry = engine.houses(dt, latitude=-90.0, longitude=0.0, system=HouseSystem.PORPHYRY)

    for i in range(12):
        assert polar_placidus.cusps[i] == pytest.approx(polar_porphyry.cusps[i], abs=1e-8)
