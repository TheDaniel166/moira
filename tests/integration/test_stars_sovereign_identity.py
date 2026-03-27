"""
Sovereign Identity Verification — tests/integration/test_stars_sovereign_identity.py

Verify that the Star Engine correctly resolves named stars via the 
Sovereign Registry and computes valid Gaia-derived positions.
"""

import pytest
from moira.stars import star_at, list_named_stars, FixedStar

@pytest.mark.unit
def test_registry_coverage():
    """Verify that the registry contains our primary anchor stars."""
    names = list_named_stars()
    assert "Algol" in names
    assert "Sirius" in names
    assert "Spica" in names
    assert len(names) > 1000

def test_star_at_returns_unified_result(jd_j2000, ritual, assert_longitude):
    """Summon a star and witness its Gaia-derived truth."""
    # Summon Algol (The Demon Star)
    star = star_at("Algol", jd_j2000)
    ritual.witness("algol_j2000_longitude", star.longitude)
    
    assert isinstance(star, FixedStar)
    assert star.name == "Algol"
    assert_longitude(star.longitude)
    assert star.magnitude < 3.0
    assert star.source == "gaia"

def test_star_position_invariants(jd_j2000, ritual, moira_approx):
    """Witness longitude agreement for a known star."""
    # Sirius: ~104.08 degrees in J2000 (Tropical)
    sirius = star_at("Sirius", jd_j2000)
    ritual.witness("sirius_j2000_longitude", sirius.longitude)
    
    # Gaia-proper-motion-reduced J2000 Tropical match
    assert sirius.longitude == pytest.approx(104.08, abs=0.01)

def test_lookup_is_case_insensitive(jd_j2000):
    """Verify that the engine is resilient to user input casing."""
    s1 = star_at("algol", jd_j2000)
    s2 = star_at("ALGOL", jd_j2000)
    assert s1.longitude == s2.longitude
    assert s1.name == "algol" # It preserves the casing of the query in the name field
