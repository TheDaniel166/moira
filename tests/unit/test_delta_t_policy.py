"""
Unit tests for DeltaTPolicy and its integration with ut_to_tt / planet_at.

All tests are pure-unit except those marked @pytest.mark.requires_ephemeris.
"""
from __future__ import annotations

import pytest

from moira.julian import DeltaTPolicy, ut_to_tt, tt_to_ut, delta_t, delta_t_nasa_canon
from moira.delta_t_physical import delta_t_hybrid

_JD_J2000 = 2451545.0
_YEAR_J2000 = 2000.0


# ---------------------------------------------------------------------------
# DeltaTPolicy construction and validation
# ---------------------------------------------------------------------------

def test_default_policy_uses_hybrid_model():
    policy = DeltaTPolicy()
    assert policy.model == 'hybrid'
    assert policy.fixed_delta_t is None


def test_policy_fixed_model_requires_value():
    with pytest.raises(ValueError, match="fixed_delta_t"):
        DeltaTPolicy(model='fixed')


def test_policy_unknown_model_raises():
    with pytest.raises(ValueError, match="model"):
        DeltaTPolicy(model='unknown_model')


def test_policy_fixed_compute_returns_exact_value():
    policy = DeltaTPolicy(model='fixed', fixed_delta_t=69.0)
    assert policy.compute(2000.0) == 69.0
    assert policy.compute(1800.0) == 69.0  # year is ignored for fixed


def test_policy_nasa_canon_compute_matches_function():
    policy = DeltaTPolicy(model='nasa_canon')
    year = 1990.0
    assert policy.compute(year) == delta_t_nasa_canon(year)


def test_policy_hybrid_compute_matches_function():
    policy = DeltaTPolicy(model='hybrid')
    year = 2000.0
    assert policy.compute(year) == delta_t(year)


def test_policy_physical_compute_matches_function():
    policy = DeltaTPolicy(model='physical')
    year = 2000.0
    assert policy.compute(year) == delta_t_hybrid(year)


def test_policy_physical_differs_from_table_at_future_epoch():
    """Physical model and table cascade must diverge for post-2026 years."""
    year = 2075.0
    physical = DeltaTPolicy(model='physical').compute(year)
    table    = DeltaTPolicy(model='hybrid').compute(year)
    assert physical != table


def test_ut_to_tt_physical_policy_applies():
    from moira.julian import decimal_year_from_jd
    policy = DeltaTPolicy(model='physical')
    jd_tt = ut_to_tt(_JD_J2000, delta_t_policy=policy)
    year = decimal_year_from_jd(_JD_J2000)
    expected = _JD_J2000 + delta_t_hybrid(year) / 86400.0
    assert abs(jd_tt - expected) < 1e-12


def test_policy_is_immutable():
    policy = DeltaTPolicy(model='fixed', fixed_delta_t=70.0)
    with pytest.raises((AttributeError, TypeError)):
        policy.model = 'hybrid'  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ut_to_tt with policy
# ---------------------------------------------------------------------------

def test_ut_to_tt_no_policy_matches_default():
    """ut_to_tt with delta_t_policy=None must equal the no-policy call."""
    jd1 = ut_to_tt(_JD_J2000)
    jd2 = ut_to_tt(_JD_J2000, delta_t_policy=None)
    assert jd1 == jd2


def test_ut_to_tt_fixed_policy_applies_exact_offset():
    dt_sec = 70.0
    policy = DeltaTPolicy(model='fixed', fixed_delta_t=dt_sec)
    jd_tt = ut_to_tt(_JD_J2000, delta_t_policy=policy)
    assert abs(jd_tt - (_JD_J2000 + dt_sec / 86400.0)) < 1e-15


def test_ut_to_tt_nasa_policy_differs_from_hybrid_at_historical_epoch():
    """For historical epochs the two models typically give different ΔT."""
    jd_1000ad = 2086308.5  # ~1000 AD
    hybrid     = ut_to_tt(jd_1000ad)
    nasa_canon = ut_to_tt(jd_1000ad, delta_t_policy=DeltaTPolicy(model='nasa_canon'))
    assert hybrid != nasa_canon


def test_ut_to_tt_hybrid_policy_matches_default():
    policy = DeltaTPolicy(model='hybrid')
    assert ut_to_tt(_JD_J2000, delta_t_policy=policy) == ut_to_tt(_JD_J2000)


# ---------------------------------------------------------------------------
# tt_to_ut with policy
# ---------------------------------------------------------------------------

def test_tt_to_ut_fixed_policy_reverses_ut_to_tt():
    """tt_to_ut(ut_to_tt(jd)) must recover jd within floating-point precision."""
    policy = DeltaTPolicy(model='fixed', fixed_delta_t=69.0)
    jd_tt = ut_to_tt(_JD_J2000, delta_t_policy=policy)
    jd_ut = tt_to_ut(jd_tt, delta_t_policy=policy)
    assert abs(jd_ut - _JD_J2000) < 1e-12


def test_tt_to_ut_no_policy_matches_default():
    jd1 = tt_to_ut(_JD_J2000)
    jd2 = tt_to_ut(_JD_J2000, delta_t_policy=None)
    assert jd1 == jd2


# ---------------------------------------------------------------------------
# Integration: planet_at accepts delta_t_policy
# ---------------------------------------------------------------------------

@pytest.mark.requires_ephemeris
def test_planet_at_fixed_delta_t_policy_changes_position():
    """A very different fixed ΔT must produce a measurably different position."""
    from moira.planets import planet_at
    from moira.constants import Body

    normal = planet_at(Body.MOON, _JD_J2000)
    # Use a wildly different ΔT (3600 s = 1 hour vs ~63.8 s default).
    # The Moon moves ~0.55°/hour, so we expect a large difference.
    policy = DeltaTPolicy(model='fixed', fixed_delta_t=3600.0)
    shifted = planet_at(Body.MOON, _JD_J2000, delta_t_policy=policy)

    diff = abs(normal.longitude - shifted.longitude)
    assert diff > 0.1, f"Expected >0.1° Moon shift from large ΔT, got {diff}"


@pytest.mark.requires_ephemeris
def test_planet_at_hybrid_policy_matches_default():
    """DeltaTPolicy(model='hybrid') must reproduce the default planet_at result."""
    from moira.planets import planet_at
    from moira.constants import Body

    default = planet_at(Body.MARS, _JD_J2000)
    policy  = DeltaTPolicy(model='hybrid')
    with_policy = planet_at(Body.MARS, _JD_J2000, delta_t_policy=policy)

    assert default.longitude == with_policy.longitude
    assert default.latitude == with_policy.latitude
