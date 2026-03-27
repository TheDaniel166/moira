"""
Sovereign Identity Verification — tests/integration/test_stars_sovereign_identity.py

Verify that the Star Engine correctly resolves named stars via the 
Sovereign Registry and computes valid native positions.
"""

import pytest
import importlib.util
import sys
import types
from pathlib import Path


def _load_stars_module():
    root = Path(__file__).resolve().parents[2]
    package = types.ModuleType("moira")
    package.__path__ = [str(root / "moira")]
    sys.modules["moira"] = package

    spec = importlib.util.spec_from_file_location("moira.stars", root / "moira" / "stars.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["moira.stars"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


stars = _load_stars_module()
star_at = stars.star_at
list_named_stars = stars.list_named_stars
FixedStar = stars.FixedStar

@pytest.mark.unit
def test_registry_coverage():
    """Verify that the registry contains our primary anchor stars."""
    names = list_named_stars()
    assert "Algol" in names
    assert "Sirius" in names
    assert "Spica" in names
    assert len(names) > 1000

def test_star_at_returns_unified_result(jd_j2000, assert_longitude):
    """Summon a star and witness its sovereign truth."""
    star = star_at("Algol", jd_j2000)

    assert isinstance(star, FixedStar)
    assert star.name == "Algol"
    assert_longitude(star.longitude)
    assert star.magnitude < 3.0
    assert star.source == "sovereign"

def test_star_position_invariants(jd_j2000):
    """Witness longitude agreement for a known star."""
    sirius = star_at("Sirius", jd_j2000)

    assert sirius.longitude == pytest.approx(104.08, abs=0.01)

def test_lookup_is_case_insensitive(jd_j2000):
    """Verify that the engine is resilient to user input casing."""
    s1 = star_at("algol", jd_j2000)
    s2 = star_at("ALGOL", jd_j2000)
    assert s1.longitude == s2.longitude
    assert s1.name == "Algol"
