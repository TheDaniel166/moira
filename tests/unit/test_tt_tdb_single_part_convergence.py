"""Real adjacent-JD cycles must not prevent the contractive LSK solve."""
from fractions import Fraction as F
import math

import pytest

from moira import julian
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_reference_clock import bound_continuous_reference_tdb
from moira._eclipse_refined_serving_clock import prove_reduced_split_clock_convergence


@pytest.mark.parametrize('epoch',[1045155.3616574521,1045155.0252075894,2451545.,2763363.8118256605])
def test_fractional_iteration_returns_and_agrees_with_the_split_contract(epoch):
    receipt = julian._tt_to_tdb_with_receipt(epoch)
    proof = prove_reduced_split_clock_convergence(epoch,I.point(0))
    assert proof.status=='proved'
    assert receipt.iterations<=julian._TT_TDB_FIXED_POINT_MAX_ITERATIONS+proof.max_iterations
    if epoch==1045155.3616574521:
        assert receipt.iterations>julian._TT_TDB_FIXED_POINT_MAX_ITERATIONS
        assert receipt.epoch_tdb==math.fsum(julian._tt_to_tdb_split(epoch))
    reference = bound_continuous_reference_tdb(epoch,I.point(0))
    exact = I.point(epoch)+reference.tdb_offset_days
    assert (exact-I.point(receipt.epoch_tdb)).magnitude<F.from_float(math.ulp(epoch))


def test_the_old_rounded_iteration_has_the_documented_two_cycle():
    epoch = 1045155.3616574521
    current,values = epoch,[]
    for _ in range(8):
        offset = julian._naif_tdb_minus_tt_seconds_at_tdb(current)
        current = math.fsum((epoch,offset/86400))
        values.append((current,offset))
    assert values[-1][0]==values[-3][0] and values[-1][0]!=values[-2][0]
    assert abs(values[-1][1]-values[-2][1])>julian._TT_TDB_FIXED_POINT_RESIDUAL_SECONDS


@pytest.mark.parametrize('epoch',[1045155.3616574521,1045155.0252075894,2451545.,2763363.8118256605])
def test_native_tt_facing_adapter_has_the_same_bounded_recovery(epoch):
    from moira import moira_native

    assert moira_native.TtToTdbEvaluator.convert(epoch)==julian.tt_to_tdb(epoch)
