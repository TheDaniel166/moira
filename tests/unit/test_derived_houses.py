"""
Tests for moira.houses.derived_houses — turned/derived house wheel.

Phase 1  Public surface ................................ import + __all__
Phase 2  Input validation .............................. bad from_house values
Phase 3  Result structure invariants ................... type, length, pivot alignment
Phase 4  Rotation correctness .......................... H1 pivot, H7 pivot, H12 pivot
Phase 5  Round-trip identity ........................... from_house=1 returns original cusps
Phase 6  sign_of_cusp delegation ....................... delegates to sign_of correctly
Phase 7  Ephemeris integration ......................... real HouseCusps from calculate_houses
"""
from __future__ import annotations

import pytest

import moira
from moira.houses import (
    HouseCusps,
    DerivedHouseCusps,
    derived_houses,
    HousePolicy,
    HouseSystemClassification,
    HouseSystemFamily,
    HouseSystemCuspBasis,
)

# ---------------------------------------------------------------------------
# Minimal synthetic HouseCusps for pure-logic tests (no ephemeris required)
# ---------------------------------------------------------------------------

_SYNTHETIC_CUSPS = (0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0, 270.0, 300.0, 330.0)


def _synthetic_house_cusps() -> HouseCusps:
    """Build a minimal Whole-Sign HouseCusps for testing (no kernel required)."""
    cls = HouseSystemClassification(
        family=HouseSystemFamily.WHOLE_SIGN,
        cusp_basis=HouseSystemCuspBasis.ECLIPTIC,
        latitude_sensitive=False,
        polar_capable=True,
    )
    return HouseCusps(
        system="W",
        cusps=_SYNTHETIC_CUSPS,
        asc=0.0,
        mc=270.0,
        armc=270.0,
        effective_system="W",
        fallback=False,
        fallback_reason=None,
        classification=cls,
        policy=HousePolicy.default(),
    )


# ============================================================================
# Phase 1 — Public surface
# ============================================================================

def test_derived_houses_in_module_all():
    assert "derived_houses" in moira.__all__


def test_derived_house_cusps_in_module_all():
    assert "DerivedHouseCusps" in moira.__all__


def test_derived_houses_importable_from_moira():
    from moira import derived_houses as f, DerivedHouseCusps as cls
    assert callable(f)
    assert isinstance(cls, type)


# ============================================================================
# Phase 2 — Input validation
# ============================================================================

def test_derived_houses_rejects_zero():
    hc = _synthetic_house_cusps()
    with pytest.raises(ValueError, match="1–12"):
        derived_houses(hc, 0)


def test_derived_houses_rejects_thirteen():
    hc = _synthetic_house_cusps()
    with pytest.raises(ValueError, match="1–12"):
        derived_houses(hc, 13)


def test_derived_houses_rejects_negative():
    hc = _synthetic_house_cusps()
    with pytest.raises(ValueError, match="1–12"):
        derived_houses(hc, -1)


# ============================================================================
# Phase 3 — Result structure invariants
# ============================================================================

def test_derived_houses_returns_derived_house_cusps():
    hc = _synthetic_house_cusps()
    result = derived_houses(hc, 7)
    assert isinstance(result, DerivedHouseCusps)


def test_derived_house_cusps_has_twelve_cusps():
    hc = _synthetic_house_cusps()
    result = derived_houses(hc, 4)
    assert len(result.cusps) == 12


def test_derived_house_cusps_pivot_house_recorded():
    hc = _synthetic_house_cusps()
    result = derived_houses(hc, 5)
    assert result.pivot_house == 5


def test_derived_house_cusps_source_reference():
    hc = _synthetic_house_cusps()
    result = derived_houses(hc, 3)
    assert result.source is hc


def test_derived_house_cusps_is_frozen():
    hc = _synthetic_house_cusps()
    result = derived_houses(hc, 7)
    with pytest.raises((AttributeError, TypeError)):
        result.pivot_house = 1  # type: ignore[misc]


# ============================================================================
# Phase 4 — Rotation correctness
# ============================================================================

def test_derived_houses_h7_pivot_aligns_cusps():
    """Derived H1 from house 7 must equal the original H7 cusp (180°)."""
    hc = _synthetic_house_cusps()
    result = derived_houses(hc, 7)
    assert result.cusps[0] == pytest.approx(180.0)   # original H7


def test_derived_houses_h7_full_rotation():
    """Full rotation from house 7: derived H1..H12 = original H7..H6."""
    hc = _synthetic_house_cusps()
    result = derived_houses(hc, 7)
    expected = (180.0, 210.0, 240.0, 270.0, 300.0, 330.0, 0.0, 30.0, 60.0, 90.0, 120.0, 150.0)
    for i, (got, exp) in enumerate(zip(result.cusps, expected)):
        assert got == pytest.approx(exp), f"derived cusp {i+1}: got {got}, expected {exp}"


def test_derived_houses_h12_pivot():
    """Derived H1 from house 12 must equal the original H12 cusp (330°)."""
    hc = _synthetic_house_cusps()
    result = derived_houses(hc, 12)
    assert result.cusps[0] == pytest.approx(330.0)
    assert result.cusps[1] == pytest.approx(0.0)    # wraps back to H1


def test_derived_houses_h2_pivot():
    hc = _synthetic_house_cusps()
    result = derived_houses(hc, 2)
    assert result.cusps[0] == pytest.approx(30.0)
    assert result.cusps[11] == pytest.approx(0.0)   # original H1 is now derived H12


# ============================================================================
# Phase 5 — Round-trip identity (from_house=1 returns original cusps)
# ============================================================================

def test_derived_houses_h1_pivot_is_identity():
    hc = _synthetic_house_cusps()
    result = derived_houses(hc, 1)
    assert result.cusps == pytest.approx(hc.cusps)
    assert result.pivot_house == 1


def test_all_pivots_cover_all_cusps():
    """Rotating through all 12 pivots covers every original cusp as the new H1."""
    hc = _synthetic_house_cusps()
    firsts = {derived_houses(hc, h).cusps[0] for h in range(1, 13)}
    assert firsts == set(_SYNTHETIC_CUSPS)


# ============================================================================
# Phase 6 — sign_of_cusp delegation
# ============================================================================

def test_derived_house_cusps_sign_of_cusp_h1():
    hc = _synthetic_house_cusps()
    result = derived_houses(hc, 7)
    sign, symbol, deg = result.sign_of_cusp(1)
    assert sign == "Libra"     # 180° = 0° Libra
    assert deg == pytest.approx(0.0)


def test_derived_house_cusps_sign_of_cusp_h7():
    hc = _synthetic_house_cusps()
    result = derived_houses(hc, 7)
    sign, symbol, deg = result.sign_of_cusp(7)
    assert sign == "Aries"     # 0° wraps back to 0° Aries


# ============================================================================
# Phase 7 — Ephemeris integration (real HouseCusps from calculate_houses)
# ============================================================================

@pytest.mark.requires_ephemeris
def test_derived_houses_from_real_chart(moira_engine):
    """derived_houses works on a real calculate_houses result."""
    from moira.houses import calculate_houses
    jd = 2451545.0   # J2000
    hc = calculate_houses(jd, 51.5, 0.0, system="P")
    result = derived_houses(hc, 7)
    assert isinstance(result, DerivedHouseCusps)
    assert len(result.cusps) == 12
    assert result.cusps[0] == pytest.approx(hc.cusps[6], abs=1e-9)


@pytest.mark.requires_ephemeris
def test_derived_houses_wrapping_at_aries(moira_engine):
    """Cusps that cross 0° Aries must wrap correctly into [0, 360)."""
    from moira.houses import calculate_houses
    jd = 2451545.0
    hc = calculate_houses(jd, 51.5, 0.0, system="W")   # Whole Sign
    for h in range(1, 13):
        result = derived_houses(hc, h)
        for lon in result.cusps:
            assert 0.0 <= lon < 360.0, f"cusp out of range: {lon}"
