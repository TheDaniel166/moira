"""Adversarial cases from the VED-011 engine/REST review, 2026-10-11."""
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from math import inf, nextafter
from types import SimpleNamespace

import pytest

from moira.muhurta_marriage import (
    MarriageElectionEvidence, MarriageElectionPolicy, MarriagePlanet,
    MarriageShadowSample, assess_marriage_election,
)
from moira.muhurta_dosha import DoshaPhaseSpan
from moira.panchanga_shuddhi import ShuddhiBoundary, ShuddhiInterval, _point
from moira._muhurta_marriage_tradition_sources import KP, VV
from moira._muhurta_marriage_tradition_time import kp_phase_spans
from moira._muhurta_marriage_windows import _derived_boundaries, _clipped_bands, admit_window
from moira.muhurta_marriage_dated import _admit, _Context, marriage_election_for_datetime
from moira._muhurta_marriage_search import MarriageSearchLimits, MarriageSearchBudgetError


def span(kind, index, start, end):
    return DoshaPhaseSpan(kind, index, ShuddhiInterval(start, end))


def carryover_evidence(kind, jd, *, uncertain=False):
    # KP III tithi:55+4 ghatis; Ashwini:50+4. Each previous parent
    # ends early enough that its fixed-clock exclusion reaches the next.
    start = ShuddhiBoundary('start',99.05,99.049,99.051) if uncertain else _point('start',99.05)
    boundary = _point('next',99.8 if kind=='tithi' else 99.925)
    indices = (1,2,3) if kind=='tithi' else (26,0,1)
    spans = (span(kind,indices[0],_point('older',98.),start),
             span(kind,indices[1],start,boundary),
             span(kind,indices[2],boundary,_point('end',100.75)))
    sun,moon = (0.,36.5) if kind=='tithi' else (10.,14.)
    return MarriageElectionEvidence(jd,(MarriagePlanet('Sun',sun),MarriagePlanet('Moon',moon)),phase_spans=spans)


def finding(evidence, kind):
    result = assess_marriage_election(evidence,policy=MarriageElectionPolicy('vows','all_regions',profile=KP))
    return next(f for f in result.astronomical_findings if f.rule_id=='kp.'+kind+'_thyajyam')


@pytest.mark.parametrize('kind,offset',[('tithi',55),('nakshatra',50)])
def test_fixed_clock_carryover_and_half_open_end(kind,offset):
    start,end = 99.05+offset/60,99.05+(offset+4)/60
    # The nakshatra exclusion starts before the new parent; its tail must
    # survive the physical star change. The tithi example begins after it.
    left = max(start,99.925 if kind=='nakshatra' else 99.8)
    for jd,want in ((left,True),((left+end)/2,True),(nextafter(end,-inf),True),
                    (end,False),(nextafter(end,inf),False)):
        f = finding(carryover_evidence(kind,jd),kind)
        assert f.detected is want
        assert f.coverage_complete
    e = carryover_evidence(kind,(left+end)/2)
    result = assess_marriage_election(e,policy=MarriageElectionPolicy('vows','all_regions',profile=KP))
    edges = tuple(_derived_boundaries(result))
    assert any(b.jd_ut1==end and b.kind.startswith('kp.'+kind+'_thyajyam') for b in edges)


@pytest.mark.parametrize('kind,offset',[('tithi',55),('nakshatra',50)])
def test_carryover_keeps_nonzero_end_bracket_unknown(kind,offset):
    end=99.05+(offset+4)/60
    f=finding(carryover_evidence(kind,end,uncertain=True),kind)
    assert f.detected is None
    assert not f.coverage_complete


@pytest.mark.parametrize('kind',["tithi","nakshatra"])
def test_missing_preceding_parent_cannot_claim_clear(kind):
    e=carryover_evidence(kind,99.96 if kind=='tithi' else 99.94)
    incomplete=replace(e,phase_spans=e.phase_spans[-1:])
    f=finding(incomplete,kind)
    assert f.detected is None and not f.coverage_complete
    assert 'preceding_phase_history_required_for_fixed_clock_carryover' in f.unavailable_reasons


def test_dated_kp_retains_parents_for_entire_current_cell():
    e=carryover_evidence('tithi',100.2)
    parents={'tithi':e.phase_spans}
    # Both samples are in the same physical parent. The later midpoint must
    # still expose a carryover ending near the start of this parent.
    early=kp_phase_spans(parents,99.975)
    late=kp_phase_spans(parents,100.2)
    assert early==late==e.phase_spans
    roots={'yoga':(_point('a',99.),_point('b',101.)),
           'karana':(_point('a',99.),_point('b',101.))}
    ctx=SimpleNamespace(policy=MarriageElectionPolicy('vows','all_regions',profile=KP),
                        phase_roots=lambda day:(roots,parents,()))
    assert _Context.phase_context(ctx,100.2)[0]==e.phase_spans
    result=assess_marriage_election(replace(e,phase_spans=late),policy=ctx.policy)
    bands=_clipped_bands([_point('range_start',99.95),*_derived_boundaries(result),
                          _point('range_end',100.10)],99.95,100.10)
    end=99.05+59/60
    assert any(b.jd_ut1==end for b in bands)
    for a,b in zip(bands,bands[1:]):
        if a.upper_jd_ut1>=b.lower_jd_ut1:
            continue
        states=[finding(carryover_evidence('tithi',a.upper_jd_ut1+(b.lower_jd_ut1-a.upper_jd_ut1)*fraction),'tithi').detected
                for fraction in (.1,.5,.9)]
        assert len(set(states))==1


def test_bright_tithi_owns_carryover_into_dark_fortnight():
    e=MarriageElectionEvidence(100.65,(MarriagePlanet('Sun',0.),MarriagePlanet('Moon',181.)),
        phase_spans=(span('tithi',13,_point('old',99.),_point('full',100.)),
                     span('tithi',14,_point('full',100.),_point('dark',100.6)),
                     span('tithi',15,_point('dark',100.6),_point('end',101.6))))
    f=finding(e,'tithi')
    # Purnima offset35, width4 ends at100.65: this exact point releases.
    assert f.detected is False and f.applicable is False and f.coverage_complete
    active=finding(replace(e,jd_ut1=100.625),'tithi')
    assert active.detected is True and active.applicable is True


@pytest.mark.parametrize('kind',['solar','lunar_umbral'])
@pytest.mark.parametrize('sun,moon',[
    ((150000000.,0.,0.),(150000000.,0.,0.)),
    ((150000000.,0.,0.),(150000001.,0.,0.)),
    ((1e308,0.,0.),(384400.,0.,0.)),
    ((150000000.,0.,0.),(1e308,0.,0.)),
])
def test_shadow_geometry_rejects_degeneracy_and_overflow(kind,sun,moon):
    with pytest.raises(ValueError,match='shadow'):
        MarriageShadowSample(100.,kind,sun,moon,20.)


def test_finite_norms_do_not_admit_overflowed_shadow_signal():
    from moira._muhurta_marriage_tradition_history import norm
    sun,moon=(700000.,0.,0.),(-1.3e154,0.,0.)
    assert norm(sun)>0 and norm(moon)>0
    assert norm(tuple(m-s for m,s in zip(moon,sun)))>0
    with pytest.raises(ValueError,match='shadow signal'):
        MarriageShadowSample(100.,'lunar_umbral',sun,moon,20.)


@pytest.mark.parametrize('kind,moon',[('solar',(384400.,9000.,0.)),('lunar_umbral',(-384400.,9000.,0.))])
def test_physical_shadow_samples_remain_admitted(kind,moon):
    value=MarriageShadowSample(100.,kind,(150000000.,0.,0.),moon,20.)
    assert isinstance(value.signal,float)


@pytest.mark.parametrize('budget',[65,72])
def test_vv_instant_budget_rejected_before_borrowing_reader(monkeypatch,budget):
    def forbidden(*args,**kwargs):
        pytest.fail('invalid VV budget reached reader acquisition')
    monkeypatch.setattr('moira.muhurta_marriage_dated.get_reader',forbidden)
    with pytest.raises(MarriageSearchBudgetError) as caught:
        marriage_election_for_datetime(datetime(2026,10,10,tzinfo=timezone.utc),28.6,77.2,
            timezone='Asia/Kolkata',policy=MarriageElectionPolicy('vows','all_regions',profile=VV),
            limits=MarriageSearchLimits(max_history_days=budget))
    assert caught.value.stage=='additional_tradition_preflight'
    assert caught.value.limit_kind=='history_days' and caught.value.count==73


@pytest.mark.parametrize('profile,budget',[(VV,73),(KP,65),('mc_avasthi_2004_marriage_ordinary.v1',65)])
def test_profile_minimum_budget_is_admitted(profile,budget):
    _admit(datetime(2026,10,10,tzinfo=timezone.utc),28.6,77.2,'Asia/Kolkata',
           MarriageElectionPolicy('vows','all_regions',profile=profile),None,
           MarriageSearchLimits(max_history_days=budget))


@pytest.mark.parametrize('days,budget,kind',[(2,73,'history_days'),(18,90,'range_days')])
def test_vv_window_preflight_includes_range_radius_and_history_vessel(days,budget,kind):
    start=datetime(2026,10,10,tzinfo=timezone.utc)
    with pytest.raises(MarriageSearchBudgetError) as caught:
        admit_window(start,start+timedelta(days=days),28.6,77.2,'Asia/Kolkata',
            MarriageElectionPolicy('vows','all_regions',profile=VV),None,
            MarriageSearchLimits(max_history_days=budget,max_range_days=31))
    assert caught.value.stage=='additional_tradition_preflight'
    assert caught.value.limit_kind==kind
