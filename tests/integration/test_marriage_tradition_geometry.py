"""Serving-resource validation of newly admitted MC/bhava enclosures."""
from datetime import datetime,timezone
from zoneinfo import ZoneInfo

import pytest

from moira.muhurta_marriage import MarriageElectionPolicy
from moira._muhurta_marriage_tradition_sources import VV
from moira.muhurta_marriage_dated import _Context
from moira._muhurta_marriage_search import WorkMeter,MarriageSearchLimits,borrow_marriage_reader
from moira._muhurta_marriage_vv_geometry import _signal,bhava_sandhis,boundaries
from moira.julian import utc_to_ut1,jd_from_datetime

pytestmark=[pytest.mark.integration,pytest.mark.requires_ephemeris]


def test_serving_midheaven_and_bhava_signals_enclose_native_values(moira_engine):
    policy=MarriageElectionPolicy('vows','all_regions',profile=VV)
    meter=WorkMeter(MarriageSearchLimits())
    with borrow_marriage_reader(moira_engine._reader,meter) as reader:
        context=_Context(reader,meter,28.6,77.2,ZoneInfo('Asia/Kolkata'),'Asia/Kolkata',policy)
        jd=utc_to_ut1(jd_from_datetime(datetime(2026,10,10,12,tzinfo=timezone.utc)))
        for delta in (0.,.08,.23,.51,.74):
            epoch=jd+delta
            for width in (0.,1/86400):
                sig=context.certifier.angular_signal((('Midheaven',1),),epoch-width,epoch+width,False)
                for t in (epoch-width,epoch,epoch+width):
                    value=context.midheaven(t)
                    value+=360*round(((sig.value.lo+sig.value.hi)/2-value)/360)
                    assert sig.value.lo<=value<=sig.value.hi
            for body in ('Moon','Jupiter'):
                for index in (0,2,5,8,11):
                    sig=_signal(context,body,index,epoch-1/86400,epoch+1/86400,False)
                    for t in (epoch-1/86400,epoch,epoch+1/86400):
                        edge=bhava_sandhis(context.lagna(t),context.midheaven(t))[index]
                        value=(context.longitude_at(body,t)-edge+180)%360-180
                        assert sig.value.lo<=value<=sig.value.hi
        result=boundaries(context,jd,jd+1/48)
        assert result
        assert not context.reasons
        assert all(b.lower_jd_ut1<b.upper_jd_ut1 for b in result)


def test_signed_declination_enclosure_contains_apparent_native_directions(moira_engine):
    from math import sin, radians
    from moira._muhurta_marriage_tradition_geometry import declination_signal
    from moira._muhurta_marriage_tradition_history_dated import declinations
    policy=MarriageElectionPolicy('vows','all_regions',profile=VV)
    meter=WorkMeter(MarriageSearchLimits())
    with borrow_marriage_reader(moira_engine._reader,meter) as reader:
        context=_Context(reader,meter,28.6,77.2,ZoneInfo('Asia/Kolkata'),'Asia/Kolkata',policy)
        for jd in (2451545.,2460409.,2460748.,2461324.,2461327.):
            for width in (0.,1/86400):
                bound=declination_signal(context,jd-width,jd+width).value
                for epoch in (jd-width,jd,jd+width):
                    sun,moon=declinations(context,epoch)
                    value=sin(radians(sun))-sin(radians(moon))
                    assert bound.lo<=value<=bound.hi,(jd,width,bound,value)


@pytest.mark.parametrize('kind,date',[('solar',(2024,4,8,18)),('lunar_umbral',(2025,3,14,7))])
def test_shadow_signal_contains_native_reference_and_resolves_known_event(moira_engine,kind,date):
    from moira._muhurta_marriage_tradition_geometry import eclipse_signal
    from moira._muhurta_marriage_tradition_history_dated import shadow_sample,_scalar_edges
    from moira._muhurta_marriage_tradition_history import MarriageShadowContact,MarriageEclipseInterval
    policy=MarriageElectionPolicy('vows','all_regions',profile=VV)
    meter=WorkMeter(MarriageSearchLimits())
    with borrow_marriage_reader(moira_engine._reader,meter) as reader:
        context=_Context(reader,meter,28.6,77.2,ZoneInfo('Asia/Kolkata'),'Asia/Kolkata',policy)
        jd=utc_to_ut1(jd_from_datetime(datetime(*date,tzinfo=timezone.utc)))
        for delta in (-.25,-.1,0.,.1,.25):
            t=jd+delta
            for width in (0.,1/86400):
                value=eclipse_signal(context,kind,t-width,t+width).value
                for epoch in (t-width,t,t+width):
                    sample=shadow_sample(context,kind,epoch)
                    assert value.lo<=sample.signal<=value.hi,(kind,delta,value,sample.signal)
        assert shadow_sample(context,kind,jd).signal<0
        assert shadow_sample(context,kind,jd-.25).signal>0
        edges=_scalar_edges(context,lambda a,b,c:eclipse_signal(context,kind,a,b,c),jd-.5,jd+.5,'shadow_test',.25)
        assert len(edges)==2 and not context.reasons
        contacts=[MarriageShadowContact(edge,shadow_sample(context,kind,edge.lower_jd_ut1),
            shadow_sample(context,kind,edge.upper_jd_ut1),role) for edge,role in zip(edges,('start','end'))]
        event=MarriageEclipseInterval(*contacts)
        assert event.interval.contains(jd) is True


@pytest.mark.parametrize('profile',[VV,'kp_1917_marriage_ordinary.v1'])
def test_complete_extra_history_is_bounded_and_serializes(moira_engine,profile):
    from dataclasses import asdict
    from moira.muhurta_marriage import MarriageStarHistory,MarriageExtent
    from moira._muhurta_marriage_tradition_history_dated import enrich
    from moira_server.models.muhurta_marriage import MarriageTraditionHistoryModel
    policy=MarriageElectionPolicy('vows','all_regions',profile=profile)
    meter=WorkMeter(MarriageSearchLimits())
    with borrow_marriage_reader(moira_engine._reader,meter) as reader:
        context=_Context(reader,meter,28.6,77.2,ZoneInfo('Asia/Kolkata'),'Asia/Kolkata',policy)
        jd=utc_to_ut1(jd_from_datetime(datetime(2026,10,10,12,tzinfo=timezone.utc)))
        base=MarriageStarHistory(MarriageExtent(jd-100,jd+100),(),())
        result=enrich(context,base,jd)
        assert not context.reasons,context.reasons
        assert result.additional_extent.start_jd_ut1<jd<result.additional_extent.end_jd_ut1
        assert MarriageTraditionHistoryModel(**asdict(result)).to_engine()==result
        assert enrich(context,base,jd+.01) is result
        if profile==VV:
            assert result.eclipse_intervals and result.declination_events
        else:
            assert result.solar_navamsa_entries


@pytest.mark.parametrize('date,month,solar_sign,prohibited',[
    ((2026,3,16),11,11,False), # Phalguna/Pisces explicit permission.
    ((2026,3,25),0,11,True),  # Chaitra rejected despite same Pisces Sun.
    ((2026,4,12),0,11,True),
    ((2026,4,25),1,0,False),  # Vaisakha/Aries explicit permission.
])
def test_real_calendar_pairs_follow_vv_lunar_precedence(moira_engine,date,month,solar_sign,prohibited):
    from moira.muhurta_marriage import MarriageElectionEvidence,MarriagePlanet,assess_marriage_election
    from moira.panchanga_shuddhi import _sector
    policy=MarriageElectionPolicy('vows','all_regions',profile=VV)
    meter=WorkMeter(MarriageSearchLimits())
    with borrow_marriage_reader(moira_engine._reader,meter) as reader:
        context=_Context(reader,meter,28.6,77.2,ZoneInfo('Asia/Kolkata'),'Asia/Kolkata',policy)
        jd=utc_to_ut1(jd_from_datetime(datetime(*date,12,tzinfo=timezone.utc)))
        label=context.lunar_month(jd)
        positions=tuple(MarriagePlanet(body,context.longitude_at(body,jd)) for body in ('Sun','Moon'))
        assert label.label.index==month
        assert _sector(positions[0].sidereal_longitude,12)==solar_sign
        evidence=MarriageElectionEvidence(jd,positions,lunar_month=label)
        result=assess_marriage_election(evidence,policy=policy)
        assert next(x for x in result.astronomical_findings if x.rule_id=='vv.calendar').detected is prohibited
        assert not context.reasons
