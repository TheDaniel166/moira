"""Dependency isolation and pre-resource admission for reusable elections."""
from datetime import datetime, timezone
from types import SimpleNamespace
from zoneinfo import ZoneInfo
import pytest

from moira._muhurta_election_dated import _profile, _admit, admit_window, ElectionSearchLimits
from moira._muhurta_election_evidence import build_evidence, ElectionDependencies
from moira.muhurta_business import BusinessElectionPolicy,BusinessElectionContext
from moira.muhurta_vastu import VastuElectionPolicy,VastuElectionContext
from moira.muhurta_marriage_dated import MarriageSearchBudgetError


def test_result_rejects_mutable_policy_impostor():
    from dataclasses import replace
    from moira.muhurta_election import ElectionEvidence
    from moira.muhurta_business import assess_business_election
    result=assess_business_election(ElectionEvidence(100.),policy=BusinessElectionPolicy('purchase'),
        context=BusinessElectionContext('a','buyer','acceptance_exchange'))
    with pytest.raises(ValueError,match='canonical family'):
        replace(result,policy=SimpleNamespace(family='business'))


def test_family_dependencies_avoid_unrelated_histories():
    _,purchase=_profile('business',BusinessElectionPolicy('purchase'),BusinessElectionContext('a','buyer','acceptance_exchange'))
    assert purchase.planets==('Moon',)
    assert not any((purchase.solar,purchase.lagna,purchase.month,purchase.phases,purchase.ingresses,purchase.stars,purchase.apparitions))
    _,foundation=_profile('vastu',VastuElectionPolicy('foundation'),VastuElectionContext('east'))
    assert foundation.solar and foundation.lagna
    assert not any((foundation.month,foundation.phases,foundation.ingresses,foundation.stars,foundation.apparitions))
    _,first=_profile('vastu',VastuElectionPolicy('first_entry'),VastuElectionContext('east'))
    assert first.month and first.apparitions
    _,old=_profile('vastu',VastuElectionPolicy('old_house_entry'),VastuElectionContext('east'))
    assert old.month and not old.apparitions


def test_dependency_builder_never_calls_unselected_operations():
    calls=[]
    class Context:
        meter=SimpleNamespace(stage='')
        policy=SimpleNamespace(ayanamsa_system='Lahiri')
        certifier=SimpleNamespace(astro=SimpleNamespace(tt=lambda a,b:SimpleNamespace(lo=1.,hi=2.)))
        reasons=[]
        def epoch(self,jd):
            return SimpleNamespace(epoch_tt=1.5)
        def longitude_at(self,body,jd):
            calls.append(('longitude',body,jd))
            return 5.
        def body(self,body,jd):
            calls.append(('body',body,jd))
            return SimpleNamespace(speed=13.)
        def __getattr__(self,name):
            pytest.fail('unexpected calculation: '+name)
    result=build_evidence(Context(),2460000.,ElectionDependencies(planets=('Moon',),lagna=False,solar=False))
    assert calls==[('longitude','Moon',2460000.),('body','Moon',2460000.)]
    assert result.solar is result.lunar_month is result.jupiter_apparition is None


def test_history_limit_is_dependency_owned():
    dt=datetime(2026,10,10,tzinfo=timezone.utc)
    limits=ElectionSearchLimits(max_history_days=4)
    _admit('vastu',dt,28.6,77.2,'Asia/Kolkata',VastuElectionPolicy('foundation'),VastuElectionContext('east'),limits)
    with pytest.raises(MarriageSearchBudgetError,match='history_days'):
        _admit('vastu',dt,28.6,77.2,'Asia/Kolkata',VastuElectionPolicy('first_entry'),VastuElectionContext('east'),limits)


def test_dst_gaps_and_fold_order_are_not_python_wall_time_comparisons():
    zone=ZoneInfo('America/New_York')
    policy=BusinessElectionPolicy('purchase')
    context=BusinessElectionContext('a','buyer','acceptance_exchange')
    with pytest.raises(ValueError,match='nonexistent'):
        _admit('business',datetime(2026,3,8,2,30,tzinfo=zone),40.,-74.,'America/New_York',policy,context,None)
    start=datetime(2026,11,1,1,45,tzinfo=zone,fold=0)
    end=datetime(2026,11,1,1,15,tzinfo=zone,fold=1)
    *_,lo,hi=admit_window('business',start,end,40.,-74.,'America/New_York',policy,context,None)
    assert 1799 < (hi-lo)*86400 < 1801
