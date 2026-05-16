"""
Tests for moira.phenomena.solar_condition_at — standalone solar proximity query.

Phase 1  Public surface ................................................ import + __all__
Phase 2  Luminary guard ................................................ Sun / Moon → absent
Phase 3  Result structure invariants ................................... distance always set
Phase 4  Condition classification ...................................... combust, under beams
Phase 5  Facade wiring ................................................. Moira.solar_condition_at
"""
from __future__ import annotations

import pytest

import moira
from moira.phenomena import solar_condition_at
from moira.dignities_types import SolarConditionKind, SolarConditionTruth

# J2000.0 — 2000-01-01 12:00 TT ≈ 2000-01-01 12:00 UTC (≈ 64 s difference, irrelevant here)
_J2000 = 2451545.0

# 2024-04-08 12:00 UTC — Mercury was ≈3–4° from Sun (combust) during the solar eclipse period
_JD_MERCURY_COMBUST = 2460408.0


# ============================================================================
# Phase 1 — Public surface
# ============================================================================

def test_solar_condition_at_in_module_all():
    assert "solar_condition_at" in moira.__all__


def test_solar_condition_at_importable_from_moira():
    from moira import solar_condition_at as f
    assert callable(f)


# ============================================================================
# Phase 2 — Luminary guard (no ephemeris needed: returned before any kernel call)
# ============================================================================

def test_luminary_sun_returns_absent():
    result = solar_condition_at("Sun", _J2000)
    assert isinstance(result, SolarConditionTruth)
    assert result.present is False
    assert result.condition is None
    assert result.distance_from_sun is None


def test_luminary_moon_returns_absent():
    result = solar_condition_at("Moon", _J2000)
    assert isinstance(result, SolarConditionTruth)
    assert result.present is False
    assert result.condition is None


# ============================================================================
# Phase 3 — Result structure invariants (requires ephemeris)
# ============================================================================

@pytest.mark.requires_ephemeris
def test_solar_condition_at_returns_solar_condition_truth(moira_engine):
    result = solar_condition_at("Mars", _J2000)
    assert isinstance(result, SolarConditionTruth)
    assert isinstance(result.present, bool)
    assert result.distance_from_sun is not None
    assert 0.0 <= result.distance_from_sun <= 180.0


@pytest.mark.requires_ephemeris
def test_solar_condition_at_condition_consistent_with_distance(moira_engine):
    """When present, condition must match the distance band; when absent, condition is None."""
    for body in ("Mercury", "Venus", "Mars", "Jupiter", "Saturn"):
        r = solar_condition_at(body, _J2000)
        dist = r.distance_from_sun
        assert dist is not None
        if r.present:
            assert r.condition in ("cazimi", "combust", "under_sunbeams")
            assert r.label is not None
            if r.condition == "cazimi":
                assert dist <= 17.0 / 60.0 + 1e-9
            elif r.condition == "combust":
                assert dist <= 8.0 + 1e-9
            else:
                assert dist <= 17.0 + 1e-9
        else:
            assert r.condition is None
            assert r.label is None
            assert r.distance_from_sun > 17.0


@pytest.mark.requires_ephemeris
def test_solar_condition_at_score_matches_condition(moira_engine):
    """Score must be +5 for cazimi, -5 for combust, -4 for under sunbeams, 0 for absent."""
    score_map = {
        "cazimi": 5,
        "combust": -5,
        "under_sunbeams": -4,
        None: 0,
    }
    for body in ("Mercury", "Venus", "Mars", "Jupiter", "Saturn"):
        r = solar_condition_at(body, _J2000)
        assert r.score == score_map[r.condition]


# ============================================================================
# Phase 4 — Known condition classification
# ============================================================================

@pytest.mark.requires_ephemeris
def test_mercury_combust_during_eclipse_period(moira_engine):
    """Mercury was within combust orb (~3–4°) around the 2024-04-08 solar eclipse."""
    result = solar_condition_at("Mercury", _JD_MERCURY_COMBUST)
    assert result.present is True
    assert result.condition in ("cazimi", "combust")
    assert result.distance_from_sun < 8.0


@pytest.mark.requires_ephemeris
def test_jupiter_not_combust_during_eclipse_period(moira_engine):
    """Jupiter was far from the Sun in April 2024."""
    result = solar_condition_at("Jupiter", _JD_MERCURY_COMBUST)
    assert result.present is False
    assert result.condition is None
    assert result.distance_from_sun > 17.0


# ============================================================================
# Phase 5 — Facade wiring
# ============================================================================

@pytest.mark.requires_ephemeris
def test_facade_solar_condition_at_delegates_correctly(moira_engine):
    """Moira.solar_condition_at must return the same result as the module function."""
    direct = solar_condition_at("Mars", _J2000)
    via_facade = moira_engine.solar_condition_at("Mars", _J2000)
    assert via_facade.present == direct.present
    assert via_facade.condition == direct.condition
    assert via_facade.distance_from_sun == pytest.approx(direct.distance_from_sun, abs=1e-10)
