"""Lossless partition transport, resource ownership and deterministic limits."""
from dataclasses import replace
from datetime import datetime,timezone

import pytest

from moira.muhurta_marriage import MarriageElectionPolicy,MarriageElectionEvidence,assess_marriage_election
from moira.muhurta_marriage_dated import MarriageSearchReceipt,_retain_numerical_gap,_check_output
from moira._muhurta_marriage_search import MarriageSearchLimits,WorkMeter,MarriageSearchBudgetError,borrow_marriage_reader
from moira._muhurta_marriage_windows import (MarriageEvidencePart,MarriageWindowWitness,MarriageElectionCell,
    MarriageElectionWindows,admit_window,_clipped_bands)
from moira.panchanga_shuddhi import ShuddhiBoundary,ShuddhiInterval,_point


def window_fixture():
    lo,hi=2460000.,2460000.25
    policy=MarriageElectionPolicy('vows','all_regions')
    raw=MarriageElectionEvidence((lo+hi)/2)
    assessment=_retain_numerical_gap(assess_marriage_election(raw,policy=policy))
    findings=tuple(dict.fromkeys(assessment.astronomical_findings+assessment.composition_findings))
    def refs(rows):
        return tuple(findings.index(f) for f in rows)
    bands=(_point('start',lo),_point('end',hi))
    cell=MarriageElectionCell(ShuddhiInterval(*bands),MarriageWindowWitness(raw.jd_ut1,(),None,(None,)*10),
        refs(assessment.astronomical_findings),(),refs(assessment.composition_findings),
        assessment.astronomical,assessment.personal_decision,assessment.requested_composition,False)
    receipt=MarriageSearchReceipt(MarriageSearchLimits(),0,0,0,1,0,(),'fixture','not_certified',('fixture_gap',))
    return MarriageElectionWindows(datetime(2023,2,24,12,tzinfo=timezone.utc),datetime(2023,2,24,18,tzinfo=timezone.utc),
        lo,hi,0.,0.,'UTC',policy,None,(),findings,(cell,),bands,'fixture','fixture',receipt)


def test_window_registry_reconstructs_exact_witness_and_does_not_claim_constancy():
    result=window_fixture()
    rebuilt=result.assessment(0)
    assert rebuilt.evidence.jd_ut1==result.cells[0].witness.jd_ut1
    assert rebuilt.requested_composition==result.cells[0].requested_composition
    assert result.at(rebuilt.evidence.jd_ut1) is None
    assert result.eligible_intervals==() and result.indeterminate_cell_indices==(0,)
    for value in (True,-1,1):
        with pytest.raises(ValueError):
            result.assessment(value)
    with pytest.raises(ValueError,match='cover'):
        replace(result,cells=())
    with pytest.raises(ValueError,match='dangling'):
        replace(result,cells=(replace(result.cells[0],astronomical_finding_refs=(9999,)),))
    with pytest.raises(ValueError,match='complete numerical receipt'):
        replace(result,cells=(replace(result.cells[0],constancy_certified=True),))


@pytest.mark.parametrize('kind',('solar','phase_spans','lunar_month','yoga_span','jupiter_apparition'))
def test_registry_rejects_mutable_or_wrong_type_components(kind):
    with pytest.raises(ValueError):
        MarriageEvidencePart(kind,{'forged':'evidence'})


def test_partition_preserves_overlapping_bands_and_a_narrow_restricted_gap():
    boundaries=(_point('start',0.),ShuddhiBoundary('a',.2,.19,.21),
        ShuddhiBoundary('b',.21,.20,.22),ShuddhiBoundary('c',.23,.229,.231),_point('end',1.))
    result=_clipped_bands(boundaries,0.,1.)
    assert len(result)==4
    assert result[1].kind=='a+b'
    assert result[1].upper_jd_ut1<result[2].lower_jd_ut1
    clipped=_clipped_bands(boundaries,.205,.23)
    assert clipped[0].lower_jd_ut1==.205 and clipped[-1].upper_jd_ut1==.23


def test_limits_fail_deterministically_and_never_truncate_success():
    meter=WorkMeter(MarriageSearchLimits(max_evaluations=2,max_output_bytes=1))
    meter.tick('evaluations',2)
    with pytest.raises(MarriageSearchBudgetError) as failure:
        meter.tick('evaluations')
    assert (failure.value.limit_kind,failure.value.count)==('evaluations',3)
    with pytest.raises(MarriageSearchBudgetError) as failure:
        _check_output(window_fixture(),meter)
    assert failure.value.limit_kind=='output_bytes'
    with pytest.raises(MarriageSearchBudgetError):
        admit_window(datetime(2026,1,1,tzinfo=timezone.utc),datetime(2026,2,1,tzinfo=timezone.utc),
            0,0,'UTC',MarriageElectionPolicy('vows','all_regions'),None,None)


def test_pool_borrow_pins_generation_without_owning_or_closing_readers():
    from moira.spk_reader import KernelPool
    class Reader:
        closed=False
        def coverage(self):return {}
        def close(self):self.closed=True
    first,second=Reader(),Reader()
    pool=KernelPool((first,))
    with borrow_marriage_reader(pool,WorkMeter(MarriageSearchLimits())) as borrowed:
        pool.add(second)
        assert borrowed.source_pool_generation==0
        with borrowed._read_lease() as snapshot:
            assert snapshot.readers==(first,)
        with pytest.raises(RuntimeError,match='borrows'):
            borrowed.close()
        assert not hasattr(borrowed,'_primary_planetary_reader')
    assert not first.closed and not second.closed
    with pool._read_lease() as snapshot:
        assert snapshot.readers==(first,second)


def test_numerical_admission_requires_sources_and_gap_free_certificates():
    receipt=window_fixture().search_receipt
    with pytest.raises(ValueError,match='complete receipt'):
        replace(receipt,crossing_completeness='complete_under_declared_arithmetic_model')
    with pytest.raises(ValueError,match='counter'):
        replace(receipt,evaluations=receipt.limits.max_evaluations+1)
    good=replace(receipt,crossing_completeness='complete_under_declared_arithmetic_model',unavailable_reasons=(),
        kernel_source_sha256=('a'*64,),numerical_source_sha256='b'*64,native_backend_sha256='c'*64,
        supporting_certificates=(('analytic_fixture',0.,1.,0,1,()),))
    with pytest.raises(ValueError,match='gap-free'):
        replace(good,supporting_certificates=(('analytic_fixture',0.,1.,0,1,((.2,.3,'gap'),)),))
    raw=assess_marriage_election(MarriageElectionEvidence(.5),policy=MarriageElectionPolicy('vows','all_regions'))
    admitted=_retain_numerical_gap(raw,good)
    assert not any(f.rule_id=='numerical_search_completeness' for f in admitted.astronomical_findings)
    assert admitted.requested_composition.status=='indeterminate'  # Numeric proof does not supply missing doctrine.


def test_output_budget_checks_incremental_objects_and_final_size_without_double_counting():
    meter=WorkMeter(MarriageSearchLimits())
    _check_output({'a':'short'},meter,additional=True)
    first=meter.counts['output_bytes']
    _check_output({'b':'short'},meter,additional=True)
    assert meter.counts['output_bytes']==2*first
    _check_output({'a':'short','b':'short'},meter)
    assert meter.counts['output_bytes']==2*first


def test_overwide_calendar_boundary_returns_typed_unavailability_before_owner_construction():
    from moira.muhurta_marriage_dated import _Context
    from moira._muhurta_marriage_search import AngularCandidate
    from zoneinfo import ZoneInfo
    context=_Context(object(),WorkMeter(MarriageSearchLimits()),0.,0.,ZoneInfo('UTC'),'UTC',MarriageElectionPolicy('vows','all_regions'))
    context.angular=lambda *args:(AngularCandidate(ShuddhiBoundary('new_moon',2460000.,2460000.-1/86400,2460000.+1/86400),0.,1),)
    assert context.lunar_month(2460000.) is None
    assert context.reasons==['calendar_achieved_boundary_width_exceeds_one_second']


def test_required_calendar_parent_cannot_silently_exceed_requested_history_cap(monkeypatch):
    from moira import muhurta_marriage_dated as dated
    monkeypatch.setattr(dated,'get_reader',lambda:pytest.fail('history preflight opened a reader'))
    with pytest.raises(MarriageSearchBudgetError) as failure:
        dated.marriage_election_for_datetime(datetime(2026,10,10,tzinfo=timezone.utc),0.,0.,timezone='UTC',
            policy=MarriageElectionPolicy('vows','all_regions'),limits=MarriageSearchLimits(max_history_days=1))
    assert (failure.value.limit_kind,failure.value.count,failure.value.stage)==('history_days',65,'calendar_parent_preflight')


def test_complete_empty_and_indeterminate_empty_have_distinct_retained_evidence():
    from moira.muhurta_marriage import MarriageFinding,_decision
    result=window_fixture()
    receipt=replace(result.search_receipt,crossing_completeness='complete_under_declared_arithmetic_model',
        unavailable_reasons=(),kernel_source_sha256=('a'*64,),numerical_source_sha256='b'*64,
        native_backend_sha256='c'*64,supporting_certificates=(('analytic_fixture',result.start_jd_ut1,result.end_jd_ut1,0,1,()),))
    # Synthetic vessel/partition contract: this asserts no astronomical truth.
    for detected,eligible,indeterminate in ((True,False,False),(None,False,True),(False,True,False)):
        finding=MarriageFinding('analytic_fixture','analytic_fixture','analytic fixture',True,detected,(),(),())
        decision=_decision((finding,))
        cell=replace(result.cells[0],astronomical_finding_refs=(0,),composition_finding_refs=(0,),
            astronomical=decision,requested_composition=decision,constancy_certified=True)
        actual=replace(result,findings=(finding,),cells=(cell,),search_receipt=receipt)
        assert bool(actual.eligible_intervals) is eligible
        assert bool(actual.indeterminate_cell_indices) is indeterminate
        assert actual.at(cell.witness.jd_ut1).requested_composition==decision
        assert actual.cells[0].requested_composition.coverage_complete is (detected is not None)


def test_lagna_domain_gap_retains_uncertainty_without_sampling_through_none():
    from types import SimpleNamespace
    from zoneinfo import ZoneInfo
    from moira.muhurta_marriage_dated import _Context
    context=_Context(object(),WorkMeter(MarriageSearchLimits()),66.56,0.,ZoneInfo('UTC'),'UTC',MarriageElectionPolicy('vows','all_regions'))
    context._certifier=SimpleNamespace(angular=lambda *args:((),((1.,2.,'lagna_subpolar_geometry_not_admitted'),)))
    context.lagna=lambda t:None
    assert context.angular((('Lagna',1),),1.,2.,(0.,30.),.01,'lagna_discrete')==()
    assert context.reasons==['lagna_discrete:lagna_subpolar_geometry_not_admitted']


def test_seed_bisection_shares_the_request_root_budget():
    from moira._muhurta_marriage_search import bisect_crossing
    meter=WorkMeter(MarriageSearchLimits(max_root_iterations=1))
    with pytest.raises(MarriageSearchBudgetError) as failure:
        bisect_crossing(lambda t:t-.3,0.,1.,.1,meter,'analytic_seed')
    assert failure.value.limit_kind=='root_iterations' and failure.value.count==2
