"""Independent frozen-horizon construction and event-role/buffer regressions."""
from math import radians
from dataclasses import replace

import erfa
import pytest

from moira.muhurta_marriage_visibility import (marriage_time_degrees,
    MarriageVisibilitySample, MarriageVisibilityEvent, MarriageApparitionContext,
    marriage_planet_availability)
from moira.panchanga_shuddhi import ShuddhiBoundary


def test_primary_threshold_transcription_and_hand_worked_geometry():
    import json
    from pathlib import Path
    from moira.muhurta_marriage_visibility import _EVENTS,_BUFFERS
    fixture=json.loads((Path(__file__).parents[1]/'fixtures/marriage_visibility_cases.json').read_text())
    assert tuple(tuple(row) for row in fixture['events'])==_EVENTS
    assert {(p,side):(post,pre) for p,side,post,pre in fixture['buffers']}==_BUFFERS
    for row in fixture['geometry']:
        geometry=marriage_time_degrees(*(row[key] for key in ('latitude','sun_ra','sun_dec','planet_ra','planet_dec')))
        assert geometry.east_time_degrees==pytest.approx(row['east'],abs=2e-12)
        assert geometry.west_time_degrees==pytest.approx(row['west'],abs=2e-12)


def _erfa_horizon(dec, latitude, rising):
    """Independent altitude root; no reuse of the production acos formula."""
    lo, hi = (-180.,0.) if rising else (0.,180.)
    for _ in range(60):
        mid = (lo+hi)/2
        altitude = erfa.hd2ae(radians(mid),radians(dec),radians(latitude))[1]
        if (altitude < 0) == rising:
            lo = mid
        else:
            hi = mid
    return (lo+hi)/2


@pytest.mark.parametrize('latitude,sd,pd',[(0,0,0),(30,-12,7),(-35,18,-10),(52,23,-14),(-52,-23,14)])
def test_ss_diurnal_arc_matches_independent_erfa_horizon_roots(latitude,sd,pd):
    sr,pr = 80.,64.
    result = marriage_time_degrees(latitude,sr,sd,pr,pd)
    er = sr + _erfa_horizon(sd,latitude,True)
    ep = pr + _erfa_horizon(pd,latitude,True)
    wr = sr + _erfa_horizon(sd,latitude,False)
    wp = pr + _erfa_horizon(pd,latitude,False)
    assert result.east_time_degrees == pytest.approx(er-ep,abs=2e-12)
    assert result.west_time_degrees == pytest.approx(wp-wr,abs=2e-12)


def test_real_reader_brackets_satisfy_each_source_threshold_in_independent_horizon_geometry():
    import json
    from pathlib import Path
    directory=Path(__file__).parents[1]/'fixtures'
    rows=json.loads((directory/'marriage_visibility_reader_brackets.json').read_text())['rows']
    source=json.loads((directory/'marriage_visibility_cases.json').read_text())
    thresholds={(p,role,side):(threshold,direction) for p,role,side,threshold,direction in source['events']}
    covered=set()
    hemispheres=set()
    for row in rows:
        event=row['event']
        key=event['before']['planet'],event['role'],event['side']
        q,direction=thresholds[key]
        covered.add(key)
        values=[]
        for name in ('before','after'):
            point=event[name]
            latitude=point['latitude']
            hemispheres.add(1 if latitude>0 else -1)
            sr=point['sun_ra']
            pr=sr+(point['planet_ra']-sr+180)%360-180
            rising=event['side']=='east'
            sun=sr+_erfa_horizon(point['sun_declination'],latitude,rising)
            planet=pr+_erfa_horizon(point['planet_declination'],latitude,rising)
            value=sun-planet if rising else planet-sun
            actual=marriage_time_degrees(latitude,point['sun_ra'],point['sun_declination'],
                point['planet_ra'],point['planet_declination'])
            assert value==pytest.approx(getattr(actual,event['side']+'_time_degrees'),abs=2e-12)
            values.append(value)
        assert direction*(values[0]-q)<=2e-12
        assert direction*(values[1]-q)>=-2e-12
        assert event['before']['jd_ut1']<event['after']['jd_ut1']
    assert covered==set(thresholds)
    assert hemispheres=={-1,1}


def test_equator_signed_ra_separation_not_positive_modulo():
    result = marriage_time_degrees(0.,359.,0.,2.,0.)
    assert result.east_time_degrees == -3.
    assert result.west_time_degrees == 3.
    assert marriage_time_degrees(0.,0.,0.,180.,0.).east_time_degrees == 180.


def test_declination_correction_is_not_longitude_orb():
    a = marriage_time_degrees(40.,0.,0.,10.,0.)
    b = marriage_time_degrees(40.,0.,0.,10.,12.)
    assert abs(a.west_time_degrees-b.west_time_degrees)>10.


@pytest.mark.parametrize('latitude,dec',[(90,0),(-90,0),(80,30),(0,90)])
def test_polar_or_degenerate_horizon_is_unavailable(latitude,dec):
    result = marriage_time_degrees(latitude,0.,0.,10.,dec)
    assert result.east_time_degrees is None
    assert result.unavailable_reasons


def event(planet,role,side,jd):
    threshold = 11 if planet=='Jupiter' else 8 if (role,side) in (('appearance','east'),('disappearance','west')) else 10
    direction = 1 if role=='appearance' else -1
    def sample(t,value):
        ra = (100-value) if side=='east' else (100+value)
        return MarriageVisibilitySample(t,planet,0.,100.,0.,ra,0.,100.,ra,0.)
    return MarriageVisibilityEvent(role,side,ShuddhiBoundary('SS_threshold',jd,jd-.000001,jd+.000001),
        sample(jd-.000001,threshold-direction*.00001),sample(jd+.000001,threshold+direction*.00001))


@pytest.mark.parametrize('undefined_epoch,required',[(50.,False),(150.,True)])
def test_undefined_horizon_abandons_only_the_required_apparition_parent(monkeypatch,undefined_epoch,required):
    from types import SimpleNamespace
    from zoneinfo import ZoneInfo
    from moira import muhurta_marriage_dated as dated
    from moira.muhurta_marriage import MarriageElectionPolicy
    from moira._muhurta_marriage_search import MarriageSearchLimits,WorkMeter
    from moira._muhurta_marriage_certification import Isolation

    first=event('Jupiter','appearance','east',100.)
    last=event('Jupiter','disappearance','west',200.)
    samples={sample.jd_ut1:sample for e in (first,last) for sample in (e.before,e.after)}
    # An actual missing horizon, not an unevaluated or absent scalar sample.
    samples[undefined_epoch]=MarriageVisibilitySample(undefined_epoch,'Jupiter',0.,100.,0.,89.,90.,100.,89.,0.)
    context=dated._Context(object(),WorkMeter(MarriageSearchLimits()),0.,0.,ZoneInfo('UTC'),'UTC',
        MarriageElectionPolicy('vows','all_regions'))
    context.visibility_sample=lambda planet,t:samples[t]
    calls=[]
    def certify(*args):
        calls.append(args)
        return Isolation((),(),0)
    context._certifier=SimpleNamespace(records=[],scalar=certify)
    events=iter((first,last))
    def seed(evaluator,*args,**kwargs):
        evaluator(undefined_epoch)
        e=next(events)
        return SimpleNamespace(roots=(SimpleNamespace(jd_ut=e.boundary.jd_ut1,
            bracket_start_jd_ut=e.before.jd_ut1,bracket_end_jd_ut=e.after.jd_ut1),))
    monkeypatch.setattr(dated,'scan_scalar_interval',seed)
    assert context.apparition('Jupiter',150.) is None
    assert len(calls)==(0 if required else 2)
    if required:
        record=context.certifier.records[0]
        assert record[0]=='Jupiter_apparition_domain'
        assert record[-1]==((undefined_epoch,undefined_epoch,'required_apparition_history_has_undefined_horizon'),)
        assert context.apparition_events['Jupiter']==()
    else:
        assert not context.certifier.records
        assert not any('undefined_horizon' in reason for reason in context.reasons)


@pytest.mark.parametrize('planet,side,post,pre',[('Jupiter','east',15,15),('Venus','east',3,15),('Venus','west',10,5)])
def test_role_specific_hysteresis_and_mc_elapsed_buffers(planet,side,post,pre):
    a = event(planet,'appearance',side,100.)
    b = event(planet,'disappearance','west' if planet=='Jupiter' else side,200.)
    context = MarriageApparitionContext(a,b)
    assert marriage_planet_availability(planet,101.,context).state=='balya'
    assert marriage_planet_availability(planet,150.,context).state=='available'
    assert marriage_planet_availability(planet,199.,context).state=='vriddha'
    result=marriage_planet_availability(planet,100.+post,context)
    assert result.state=='uncertain'
    assert result.usable_start.lower_jd_ut1==a.boundary.lower_jd_ut1+post
    assert result.usable_end.upper_jd_ut1==b.boundary.upper_jd_ut1-pre


def test_venus_same_side_apparition_then_alternating_absence():
    a=event('Venus','disappearance','east',100.)
    b=event('Venus','appearance','west',200.)
    assert marriage_planet_availability('Venus',150.,MarriageApparitionContext(a,b)).state=='asta'
    with pytest.raises(ValueError):
        MarriageApparitionContext(a,event('Venus','appearance','east',200.))


def test_event_rejects_wrong_threshold_direction_and_epoch():
    a=event('Venus','appearance','east',100.)
    with pytest.raises(ValueError):
        replace(a,role='disappearance')
    with pytest.raises(ValueError):
        replace(a,before=replace(a.before,jd_ut1=99.))
    with pytest.raises(ValueError):
        marriage_planet_availability('Jupiter',150.,MarriageApparitionContext(a,event('Venus','disappearance','east',200.)))


@pytest.mark.parametrize('bad',[True,float('nan'),float('inf'),-float('inf')])
def test_geometry_strict_numeric_admission(bad):
    with pytest.raises(ValueError):
        marriage_time_degrees(bad,0.,0.,10.,0.)
