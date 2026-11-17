"""Conditional enclosures for the existing month-stepped NASA lunar clock."""
from __future__ import annotations

from fractions import Fraction
import math
import sys

import pytest

from moira import julian
from moira.dispatch import MoiraBackend, settings
from moira._eclipse_canon_clock_bounds import (
    CanonClockBoundsUnavailable,
    _global_offsets,
    bound_canon_catalog_tt_to_ut1,
    bound_canon_catalog_ut1_to_tt,
)
from moira._eclipse_interval import RationalInterval
from moira.eclipse_canon import _tt_to_ut_nasa_catalog, _ut_to_tt_nasa_catalog


def _absolute(result):
    return RationalInterval.point(result.anchor_jd) + result.output_offset_days


@pytest.mark.parametrize("year", [-1999, -500, 0, 500, 1600, 1800, 1900, 1955, 2005, 2022, 3000])
@pytest.mark.parametrize("month", [1, 2, 12])
def test_forward_contains_actual_month_transition_and_neighbor_floats(year, month):
    anchor = julian.julian_day(year, month, 1)
    bounds = bound_canon_catalog_ut1_to_tt(anchor, RationalInterval(-2, 2))
    output = _absolute(bounds)
    assert bounds.direction == "UT1_TO_TT"
    assert not bounds.source_and_arithmetic_attested
    assert not bounds.native_reader_clock_enclosed
    for value in (anchor - 2, math.nextafter(anchor, -math.inf), anchor,
                  math.nextafter(anchor, math.inf), anchor + 2):
        assert output.contains(_ut_to_tt_nasa_catalog(value))


@pytest.mark.parametrize("year,month", [(-1999, 1), (-500, 1), (0, 3), (500, 1),
                                        (1600, 1), (1955, 1), (2005, 1), (2024, 3), (3000, 12)])
def test_forward_totality_retains_both_sides_of_calendar_and_polynomial_seams(year, month):
    boundary = julian.julian_day(year, month, 1)
    offsets = RationalInterval(-0.125, 0.125)
    bounds = bound_canon_catalog_ut1_to_tt(boundary, offsets, require_totality=True)
    assert bounds.forward_totality_conditionally_proved
    assert bounds.successful_outputs_only
    assert bounds.unchanged_calendar_canon_source_and_arithmetic_required
    assert not bounds.source_and_arithmetic_attested
    assert not bounds.physical_delta_t_accuracy_certified
    assert not bounds.inverse_uniqueness_certified
    output = _absolute(bounds)
    for value in (boundary - 0.125, math.nextafter(boundary, -math.inf), boundary,
                  math.nextafter(boundary, math.inf), boundary + 0.125):
        assert offsets.contains(value - boundary)
        assert output.contains(_ut_to_tt_nasa_catalog(value))
    assert not bound_canon_catalog_ut1_to_tt(boundary, offsets).forward_totality_conditionally_proved


@pytest.mark.parametrize("name", ["_require_representable_time_jd", "_require_representable_delta_t_year",
                                  "_require_finite", "_MAX_ABS_TIME_JD", "_MAX_ABS_DELTA_T_YEAR"])
def test_forward_totality_rejects_changed_domain_guards(monkeypatch, name):
    anchor = julian.julian_day(2024, 4, 8)
    original = getattr(julian, name)
    replacement = (lambda *args: original(*args)) if callable(original) else original - 1
    monkeypatch.setattr(julian, name, replacement)
    with pytest.raises(CanonClockBoundsUnavailable, match="forward totality source changed"):
        bound_canon_catalog_ut1_to_tt(anchor, RationalInterval.point(0), require_totality=True)


@pytest.mark.parametrize("backend", [MoiraBackend.PYTHON, MoiraBackend.NATIVE])
def test_forward_totality_under_each_stable_calendar_backend(monkeypatch, backend):
    monkeypatch.setattr(settings, "_default_backend", backend)
    boundary = julian.julian_day(-1999, 2, 1)
    bounds = bound_canon_catalog_ut1_to_tt(boundary, RationalInterval(-0.125, 0.125),
                                           require_totality=True)
    assert bounds.forward_totality_conditionally_proved
    for value in (boundary - 0.125, math.nextafter(boundary, -math.inf), boundary,
                  math.nextafter(boundary, math.inf), boundary + 0.125):
        assert _absolute(bounds).contains(_ut_to_tt_nasa_catalog(value))


def test_forward_totality_input_and_calendar_budget_fail_closed():
    with pytest.raises(ValueError, match="require_totality"):
        bound_canon_catalog_ut1_to_tt(2451545.0, RationalInterval.point(0), require_totality=1)
    with pytest.raises(CanonClockBoundsUnavailable, match="supported calendar"):
        bound_canon_catalog_ut1_to_tt(2451545.0, RationalInterval.point(10**100),
                                      require_totality=True)
    with pytest.raises(CanonClockBoundsUnavailable, match="day budget"):
        bound_canon_catalog_ut1_to_tt(2451545.0, RationalInterval(0, 33), require_totality=True)


@pytest.mark.parametrize("year,month,day", [
    (-1999, 1, 2), (-500, 1, 1), (0, 3, 1), (500, 1, 1),
    (1582, 10, 15), (1800, 1, 1), (1900, 1, 1),
    (1955, 1, 1), (2005, 1, 1), (2022, 11, 8), (3000, 12, 31),
])
def test_inverse_contains_successful_catalog_outputs_near_branch_edges(year, month, day):
    ut1 = julian.julian_day(year, month, day, 12)
    tt = _ut_to_tt_nasa_catalog(ut1)
    bounds = bound_canon_catalog_tt_to_ut1(tt, RationalInterval(-0.01, 0.01))
    output = _absolute(bounds)
    assert bounds.direction == "TT_TO_UT1"
    assert bounds.successful_outputs_only
    assert not bounds.inverse_uniqueness_certified
    for value in (tt - 0.01, math.nextafter(tt, -math.inf), tt,
                  math.nextafter(tt, math.inf), tt + 0.01):
        try:
            result = _tt_to_ut_nasa_catalog(value)
        except ValueError as exc:
            assert "month-midpoint Delta-T" in str(exc)
        else:
            assert output.contains(result)


def test_crossing_a_month_hulls_both_unequal_month_offsets():
    anchor = julian.julian_day(-1999, 2, 1)
    result = bound_canon_catalog_ut1_to_tt(anchor, RationalInterval(-0.001, 0.001))
    assert (-1999, 1) in result.possible_months
    assert (-1999, 2) in result.possible_months
    a = _ut_to_tt_nasa_catalog(math.nextafter(anchor, -math.inf))
    b = _ut_to_tt_nasa_catalog(anchor)
    assert _absolute(result).contains(a)
    assert _absolute(result).contains(b)


@pytest.mark.parametrize("year,month,reason", [
    (-1999, 1, "multiple self-consistent"),
    (1900, 1, "no self-consistent"),
])
def test_inverse_gap_and_overlap_remain_unproved(year, month, reason):
    # Both cases are actual month-step discontinuities; neither can be
    # replaced by a claim that the entire TT domain has a unique inverse.
    boundary = julian.julian_day(year, month, 1)
    left = _ut_to_tt_nasa_catalog(math.nextafter(boundary, -math.inf))
    right = _ut_to_tt_nasa_catalog(boundary)
    midpoint = (left + right) / 2
    bounds = bound_canon_catalog_tt_to_ut1(midpoint, RationalInterval.point(0))
    assert not bounds.inverse_uniqueness_certified
    with pytest.raises(ValueError, match=reason):
        _tt_to_ut_nasa_catalog(midpoint)


def test_nonbinary_input_endpoints_enclose_neighbor_float_conversions():
    anchor = julian.julian_day(2020, 1, 1, 12)
    eps = Fraction(1, 3_000_000)
    result = bound_canon_catalog_ut1_to_tt(anchor, RationalInterval(-eps, eps))
    output = _absolute(result)
    for value in (math.nextafter(anchor, -math.inf), anchor, math.nextafter(anchor, math.inf)):
        assert output.contains(_ut_to_tt_nasa_catalog(value))


def test_finite_domain_and_work_budget_fail_closed():
    for anchor in (1e300, sys.float_info.max, -sys.float_info.max):
        with pytest.raises(CanonClockBoundsUnavailable, match="supported calendar"):
            bound_canon_catalog_ut1_to_tt(anchor, RationalInterval.point(0))
    with pytest.raises(CanonClockBoundsUnavailable, match="supported calendar"):
        bound_canon_catalog_ut1_to_tt(2451545.0, RationalInterval.point(10**100))
    with pytest.raises(CanonClockBoundsUnavailable, match="day budget"):
        bound_canon_catalog_ut1_to_tt(2451545.0, RationalInterval(0, 33))
    with pytest.raises(ValueError, match="anchor_jd"):
        bound_canon_catalog_ut1_to_tt(float("nan"), RationalInterval.point(0))
    with pytest.raises(TypeError, match="RationalInterval"):
        bound_canon_catalog_ut1_to_tt(2451545.0, 0)
    with pytest.raises(ValueError, match="max_days"):
        bound_canon_catalog_ut1_to_tt(2451545.0, RationalInterval.point(0), max_days=True)


@pytest.mark.parametrize("year", [-2998, 3998])
def test_every_month_boundary_near_supported_domain_edges(year):
    for month in range(1, 13):
        anchor = julian.julian_day(year, month, 1)
        forward = bound_canon_catalog_ut1_to_tt(anchor, RationalInterval(-1, 1))
        for ut1 in (math.nextafter(anchor, -math.inf), anchor, math.nextafter(anchor, math.inf)):
            tt = _ut_to_tt_nasa_catalog(ut1)
            assert _absolute(forward).contains(tt)
            inverse = bound_canon_catalog_tt_to_ut1(tt, RationalInterval.point(0))
            try:
                returned = _tt_to_ut_nasa_catalog(tt)
            except ValueError as exc:
                assert "month-midpoint Delta-T" in str(exc)
            else:
                assert _absolute(inverse).contains(returned)


def test_inverse_requires_adjacent_year_guard_at_outer_calendar_boundary():
    anchor = julian.julian_day(-2999, 1, 1)
    with pytest.raises(CanonClockBoundsUnavailable, match="adjacent-year"):
        bound_canon_catalog_tt_to_ut1(anchor, RationalInterval.point(0))


def test_changed_clock_source_fails_closed_even_after_global_hull_cached(monkeypatch):
    _global_offsets()
    monkeypatch.setattr(julian, "delta_t_nasa_canon", lambda year: 0)
    with pytest.raises(CanonClockBoundsUnavailable, match="source changed"):
        bound_canon_catalog_tt_to_ut1(2451545.0, RationalInterval.point(0))
