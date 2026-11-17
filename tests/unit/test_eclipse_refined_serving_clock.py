"""Refined conversion inclusions, whole-day carries and source guards."""
from fractions import Fraction as F
import math

import pytest

from moira import julian
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable
from moira._eclipse_refined_serving_clock import (bound_refined_serving_split_tdb,
    prove_reduced_split_clock_convergence,refined_split_clock_error)
from tests.unit.test_tt_tdb_split_precision import _reference_tdb, DAY
from decimal import Decimal as D, localcontext


@pytest.mark.parametrize('anchor', [-39_000_000.,-1_000_000.,1045155.4,2451545.,2763363.8,39_000_000.])
@pytest.mark.parametrize('first', [I.point(0),I(F(-1,6),F(1,6))])
def test_reduced_clock_convergence_and_value_bounds(anchor,first):
    offsets = I(F(-1,100),F(1,100))
    proof = prove_reduced_split_clock_convergence(anchor,offsets,first_part_offsets=first)
    assert proof.status=='proved' and proof.max_iterations<=4
    assert proof.final_difference_bound_seconds<=F.from_float(julian._TT_TDB_FIXED_POINT_RESIDUAL_SECONDS)
    bounds = bound_refined_serving_split_tdb(anchor,first+offsets)
    assert refined_split_clock_error(anchor,first+offsets).total_error_seconds<F(1,10**6)
    for delta in (first.lo,first.hi):
        part1 = float(F.from_float(anchor)+delta)
        for offset in (offsets.lo,offsets.hi):
            whole,fraction = julian._tt_to_tdb_split(part1,float(offset))
            actual = F.from_float(whole)+F.from_float(fraction)-F.from_float(anchor)
            # Rounding the chosen first input may shift it by one JD ulp.
            if first.contains(F.from_float(part1)-F.from_float(anchor)):
                assert bounds.tdb_offset_days.contains(actual)


@pytest.mark.parametrize('anchor', [1045155.4,2451545.,2763363.8])
def test_compensated_time_matches_independent_decimal(anchor):
    with localcontext() as context:
        context.prec = 70
        whole,fraction = julian._tt_to_tdb_split(anchor,-.005)
        actual = D.from_float(whole)+D.from_float(fraction)
        assert abs(actual-_reference_tdb(anchor,-.005))*DAY<D('2e-11')


def test_pre_fma_python_fallback_preserves_product_residual(monkeypatch):
    before = julian._tt_to_tdb_split(1045155.4,-.005)
    monkeypatch.delattr(math,'fma',raising=False)
    after = julian._tt_to_tdb_split(1045155.4,-.005)
    assert after==before


def test_changed_source_cannot_inherit_convergence_proof(monkeypatch):
    monkeypatch.setattr(julian,'_naif_tdb_minus_tt_seconds_at_tdb_split',lambda *args:0.)
    with pytest.raises(EnclosureUnavailable,match='source'):
        prove_reduced_split_clock_convergence(2451545.,I.point(0))
