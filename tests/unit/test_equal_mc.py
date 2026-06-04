"""
Tests for HouseSystem.EQUAL_MC (Equal Houses from Midheaven).
"""
from __future__ import annotations

import pytest
from moira.houses import calculate_houses, houses_from_armc, classify_house_system
from moira.constants import HouseSystem, HOUSE_SYSTEM_NAMES
from moira.houses import HouseSystemFamily, HouseSystemCuspBasis

_JD_J2000 = 2451545.0
_LAT_NORMAL = 51.5
_LON = 0.0
_LAT_POLAR = 80.0


def test_equal_mc_metadata():
    # Verify name mapping exists
    assert HOUSE_SYSTEM_NAMES[HouseSystem.EQUAL_MC] == "Equal from MC"
    assert HouseSystem.EQUAL_MC == "EM"


def test_equal_mc_classification():
    cls = classify_house_system(HouseSystem.EQUAL_MC)
    assert cls.family == HouseSystemFamily.EQUAL
    assert cls.cusp_basis == HouseSystemCuspBasis.ECLIPTIC
    assert cls.latitude_sensitive is False
    assert cls.polar_capable is True


def test_equal_mc_calculation_invariants():
    # Verify standard calculation at normal latitude
    res = calculate_houses(_JD_J2000, _LAT_NORMAL, _LON, HouseSystem.EQUAL_MC)
    assert res.system == HouseSystem.EQUAL_MC
    assert res.effective_system == HouseSystem.EQUAL_MC
    assert res.fallback is False
    assert res.fallback_reason is None

    # Invariant: Cusps must be spaced exactly 30 degrees apart
    for i in range(11):
        diff = (res.cusps[i + 1] - res.cusps[i]) % 360.0
        assert diff == pytest.approx(30.0, abs=1e-8)

    # Invariant: Cusp 10 (index 9) must equal MC
    assert res.cusps[9] == pytest.approx(res.mc, abs=1e-8)

    # Invariant: Cusp 1 (index 0) must equal MC + 90
    assert res.cusps[0] == pytest.approx((res.mc + 90.0) % 360.0, abs=1e-8)


def test_equal_mc_polar_capability():
    # Equal MC is polar capable and latitude-insensitive, so it should not fall back
    res = calculate_houses(_JD_J2000, _LAT_POLAR, _LON, HouseSystem.EQUAL_MC)
    assert res.system == HouseSystem.EQUAL_MC
    assert res.effective_system == HouseSystem.EQUAL_MC
    assert res.fallback is False
    assert res.fallback_reason is None

    for i in range(11):
        diff = (res.cusps[i + 1] - res.cusps[i]) % 360.0
        assert diff == pytest.approx(30.0, abs=1e-8)

    assert res.cusps[9] == pytest.approx(res.mc, abs=1e-8)


def test_equal_mc_houses_from_armc_parity():
    # Verify houses_from_armc gives identical output
    obliquity = 23.4392911  # approximate J2000 obliquity
    armc = 270.0
    lat = 40.0
    res1 = houses_from_armc(armc, obliquity, lat, HouseSystem.EQUAL_MC)
    
    assert res1.system == HouseSystem.EQUAL_MC
    assert res1.fallback is False
    
    # Cusp 10 (index 9) equals mc
    assert res1.cusps[9] == pytest.approx(res1.mc, abs=1e-8)
    
    # Check 30 degree step propagation
    for i in range(11):
        diff = (res1.cusps[i + 1] - res1.cusps[i]) % 360.0
        assert diff == pytest.approx(30.0, abs=1e-8)
