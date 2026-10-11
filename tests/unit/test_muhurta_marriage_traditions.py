"""Independent source disagreement and boundary witnesses for VV/KP."""
from dataclasses import replace
from math import nextafter,inf
import json
from pathlib import Path

import pytest

from moira.muhurta_marriage import (MarriageElectionPolicy,MarriageElectionEvidence,
    VivahaVrindavanaEvidence,MarriagePlanet,MarriageParticipant,MarriagePersonalContext,
    MarriageSolarContext,assess_marriage_election)
from moira._muhurta_marriage_tradition_sources import VV,KP,VV_PERSONAL,KP_PERSONAL
from moira._muhurta_marriage_vv_geometry import bhava_centers,bhava_sandhis,bhava_house
from moira._muhurta_marriage_longitude_visibility import (LongitudeVisibilitySample,
    LongitudeVisibilityEvent,LongitudeApparitionContext)
from moira.panchanga_shuddhi import _point,ShuddhiBoundary,ShuddhiInterval


def policy(profile,**kw):
    return MarriageElectionPolicy('declared vows','all_regions',profile=profile,**kw)


def evidence(*,lagna=None,mc=None,**positions):
    cls=MarriageElectionEvidence if mc is None else VivahaVrindavanaEvidence
    extra={} if mc is None else {'midheaven_sidereal_longitude':mc}
    return cls(100.,tuple(MarriagePlanet(p,x,1.) for p,x in positions.items()),lagna,**extra)


def rows(e,profile=VV,**kw):
    return {r.rule_id:r for r in assess_marriage_election(e,policy=policy(profile,**kw)).astronomical_findings}


def test_profile_defaults_and_cross_injections_fail_closed():
    mc=MarriageElectionPolicy('vows','all_regions')
    assert mc.remedies==('mc68_own_or_exalted_luminaries','mc83_lagna_aspect','mc88_weak_afflictors')
    assert mc.navamsa_profile=='mc_avasthi_vivaha_84_four.v1'
    for selected in (VV,KP):
        assert policy(selected).remedies==()
        with pytest.raises(ValueError,match='selected profile'):
            policy(selected,remedies=mc.remedies)
        with pytest.raises(ValueError,match='navamsa'):
            policy(selected,navamsa_profile=mc.navamsa_profile)
        with pytest.raises(ValueError,match='Godhuli'):
            policy(selected,godhuli=True)
        with pytest.raises(ValueError,match='personal profile'):
            assess_marriage_election(evidence(),policy=policy(selected),personal=MarriagePersonalContext((MarriageParticipant('b','bride'),MarriageParticipant('g','groom'))))


def test_vv_five_line_whole_star_does_not_release_other_padas():
    # Diagram PDF17 +17.3 independently: Hasta ↔ Uttara Bhadra;
    # Revati ↔ Uttara Phalguni. Same pairs; VV ordinary differs in scope.
    for cause,target in ((160.1,335.),(350.,147.)):
        hit=rows(evidence(Moon=target,Jupiter=cause))['vv.five_line.jupiter']
        assert hit.detected is True
        assert hit.exceptions==()
    assert rows(evidence(Moon=350.,Jupiter=160.1))['vv.five_line.jupiter'].detected is False


def test_vv_first_half_sagittarius_navamsa_exact_edge():
    # 28°20' Aries maps to Sagittarius15 in standard continuous D9.
    edge=85/3
    assert rows(evidence(lagna=nextafter(edge,-inf)))['vv.navamsa'].detected is False
    assert rows(evidence(lagna=nextafter(edge,inf)))['vv.navamsa'].detected is True
    for degree in (7.,18.,22.):
        assert rows(evidence(lagna=degree))['vv.navamsa'].detected is False


def test_vv_bhava_quadrants_and_sign_testimony_both_survive():
    # Asc0/MC300 gives IC120; thirds40° and20°. Centers are NOT
    # whole-sign houses, and sandhis are midpoints between centers.
    assert bhava_centers(0.,300.)==(0.,40.,80.,120.,140.,160.,180.,220.,260.,300.,320.,340.)
    assert bhava_sandhis(0.,300.)==(20.,60.,100.,130.,150.,170.,200.,240.,280.,310.,330.,350.)
    assert bhava_house(149.,0.,300.)==5
    assert bhava_house(151.,0.,300.)==6
    assert bhava_house(150.,0.,300.) is None
    # Venus at151 is sixth in BOTH; Venus at140 is fifth in both.
    assert rows(evidence(lagna=0.,mc=300.,Venus=151.))['vv.placement.venus'].detected is True
    # Asymmetric opposite geometry makes Venus145 fifth D1 but sixth bhava.
    hit=rows(evidence(lagna=0.,mc=240.,Venus=145.))['vv.placement.venus']
    assert hit.detected is True
    assert {x.name:x.value for x in hit.measures}=={'sign_house':5,'bhava_house':6}


def test_vv_full_jamitra_is_55th_inclusive_and_cannot_be_remedied():
    r=rows(evidence(lagna=90.,mc=0.,Moon=10.,Sun=190.,Jupiter=95.),
        remedies=('vv13_11_qualified_benefic_moon_aspect',))
    f=r['vv.protected_full_jamitra.sun']
    assert f.detected is True and f.effective_restriction is True and not f.exceptions
    assert rows(evidence(Moon=10.,Sun=nextafter(190.,-inf)))['vv.protected_full_jamitra.sun'].detected is False


def test_kp_tithi_specific_permissions_override_generic_waning_language():
    # Printed79/PDF116: dark1,6,8 middle; dark9 onward prohibited.
    for absolute,expected,grade in ((1,True,'prohibited'),(6,False,'middling'),(8,False,'middling'),
        (15,False,'middling'),(16,False,'middling'),(21,False,'middling'),(23,False,'middling'),(24,True,'prohibited'),(26,True,'prohibited')):
        f=rows(evidence(Sun=0.,Moon=(absolute-1)*12+1),KP)['kp.tithi']
        assert f.detected is expected
        assert next(m.value for m in f.measures if m.name=='quality')==grade


def test_kp_eighth_mars_favorable_is_not_a_complete_profile_waiver():
    r=assess_marriage_election(evidence(lagna=60.,Mars=280.,Moon=80.),policy=policy(KP))
    f=next(x for x in r.astronomical_findings if x.rule_id=='kp.placement.mars')
    assert f.detected is False
    assert next(m.value for m in f.measures if m.name=='testimony')=='favorable'
    assert r.astronomical.status=='restricted'  # Moon in Lagna remains adverse.


def test_both_participants_are_evaluated_and_missing_moon_stays_unknown():
    personal=MarriagePersonalContext((MarriageParticipant('bride','bride',0.),MarriageParticipant('groom','groom')),profile=VV_PERSONAL)
    r=assess_marriage_election(evidence(Moon=0.,Sun=90.),policy=policy(VV),personal=personal)
    by={x.rule_id:x for x in r.personal_findings}
    assert by['vv.personal_moon.bride'].detected is False
    assert by['vv.personal_moon.groom'].detected is None
    assert not r.personal_decision.coverage_complete


def angular_event(role,jd,planet='Jupiter',retro=False):
    orb=11 if planet=='Jupiter' else 8 if retro else 10
    before,after=(orb-.1,orb+.1) if role=='appearance' else (orb+.1,orb-.1)
    edge=ShuddhiBoundary('raw_orb',jd,jd-.001,jd+.001)
    return LongitudeVisibilityEvent(role,'west',edge,
        LongitudeVisibilitySample(jd-.001,planet,0.,before,-1. if retro else 1.),
        LongitudeVisibilitySample(jd+.001,planet,0.,after,-1. if retro else 1.))


def test_kp_orbs_and_waiting_periods_use_own_event_definition():
    assert LongitudeVisibilitySample(100.,'Jupiter',359.,9.,1.).combust
    assert not LongitudeVisibilitySample(100.,'Venus',0.,9.,-1.).combust
    assert LongitudeVisibilitySample(100.,'Venus',0.,9.,1.).combust
    for planet,post,pre in (('Jupiter',8,15),('Venus',7,10)):
        ctx=LongitudeApparitionContext(angular_event('appearance',80,planet),angular_event('disappearance',150,planet))
        e=replace(evidence(),**{planet.lower()+'_apparition':ctx})
        f=rows(e,KP)['kp.availability.'+planet.lower()]
        assert f.detected is False
        v={m.name:m.value for m in f.measures}
        assert (v['post_appearance_days'],v['pre_disappearance_days'])==(post,pre)
        assert rows(replace(e,jd_ut1=80+post),KP)['kp.availability.'+planet.lower()].detected is None
        assert rows(replace(e,jd_ut1=80+post+.01),KP)['kp.availability.'+planet.lower()].detected is False
        assert rows(replace(e,jd_ut1=150-pre+.01),KP)['kp.availability.'+planet.lower()].detected is True
        with pytest.raises(ValueError,match='geometry'):
            rows(e,VV)


def test_forged_angular_context_rejected():
    event=angular_event('appearance',80.)
    with pytest.raises(ValueError,match='role'):
        replace(event,role='disappearance')
    with pytest.raises(ValueError,match='state change'):
        replace(event,after=replace(event.after,planet_sidereal_longitude=10.))
    with pytest.raises(ValueError,match='alternate'):
        LongitudeApparitionContext(event,angular_event('appearance',150.))


def test_kp_firstborn_groom_exception_does_not_erase_other_tara_cycles():
    personal=MarriagePersonalContext((MarriageParticipant('b','bride',0.,first_born=True),MarriageParticipant('g','groom',0.,first_born=False)),profile=KP_PERSONAL)
    r=assess_marriage_election(evidence(Moon=1.,Sun=270.),policy=policy(KP),personal=personal)
    assert all(not f.detected for f in r.personal_findings if f.family_id=='kp.personal_tara')
    r=assess_marriage_election(evidence(Moon=121.,Sun=270.),policy=policy(KP),personal=personal)
    assert all(f.detected for f in r.personal_findings if f.family_id=='kp.personal_tara')


def test_missing_sunrise_and_malformed_bhava_never_pass():
    for selected in (VV,KP):
        r=assess_marriage_election(evidence(),policy=policy(selected))
        assert r.astronomical.status=='indeterminate'
    with pytest.raises(ValueError,match='ordered'):
        VivahaVrindavanaEvidence(100.,lagna_sidereal_longitude=0.,midheaven_sidereal_longitude=10.)


def test_primary_scan_fixture_tables_and_waits():
    from moira import _muhurta_marriage_tradition_sources as S
    from moira._muhurta_marriage_sources import STARS28
    f=json.loads((Path(__file__).parents[1]/'fixtures/marriage_additional_tradition_sources.json').read_text(encoding='utf-8'))
    assert [[STARS28[a],STARS28[b]] for a,b in S.VV_FIVE_PAIRS]==f['vv']['five_line_pairs']
    assert dict(S.VV_LATTA)==f['vv']['forward_inclusive_latta']
    for planet,side,post,pre in S.VV_BUFFERS:
        assert [post,pre]==f['vv']['visibility_waits'][planet+'_'+side]
    for planet,side,post,pre in S.KP_BUFFERS:
        assert [post,pre]==f['kp']['appearance_disappearance_waits'][planet]
    assert set(f['kp']['eighth_house_favorable'])=={'Sun','Saturn','Mars'}


def solar(jd=100.,weekday=1):
    return MarriageSolarContext(ShuddhiInterval(_point('rise',jd-.25),_point('next_rise',jd+.75)),
        _point('set',jd+.25),weekday)


def test_kp_ekargala_uses_27_star_diagram_and_daytime_only():
    from moira._muhurta_marriage_traditions import _kp_discrete
    from moira.muhurta_lagna import _nature
    # Printed diagram's Aswini/Mula opposite under Parigha. Positions are
    # chosen within those stars so the sum is Parigha as well (240..253 1/3).
    e=replace(evidence(Sun=4.,Moon=245.),solar=solar())
    p={x.planet:x.sidereal_longitude for x in e.planets}
    f=next(x for x in _kp_discrete(e,p,_nature(p)) if x.rule_id=='kp.ekargala')
    assert f.detected is True
    night=replace(e,solar=MarriageSolarContext(ShuddhiInterval(_point('rise',99.),_point('next',100.25)),_point('set',99.5),1))
    assert rows(night,KP)['kp.ekargala'].detected is False


def test_kp_yoga_is_whole_while_vv_initial_ghatis_release():
    # Ganda spans [99,101), selected epoch100 is past VV six fixed ghatis.
    e=replace(evidence(Sun=30.,Moon=100.),yoga_span=ShuddhiInterval(_point('start',99.),_point('end',101.)))
    assert rows(e,VV)['vv.nitya_yoga'].detected is False
    assert rows(e,KP)['kp.nitya_yoga'].detected is True


def test_kp_moon_fourth_is_adverse_despite_other_benefics_good():
    r=rows(evidence(lagna=60.,Moon=151.,Jupiter=152.),KP)
    assert r['kp.placement.moon'].detected is True
    assert r['kp.placement.jupiter'].detected is False


def extra_history(profile,**kw):
    from moira import MarriageTraditionHistory,MarriageExtent
    return MarriageTraditionHistory(MarriageExtent(10.,110.),(),(),tradition_profile=profile,
        additional_extent=MarriageExtent(20.,105.),declination_extent=MarriageExtent(97.,103.) if profile==VV else None,**kw)


def test_catalogue_covers_every_emitted_family_and_protects_jamitra():
    from moira.muhurta_marriage import marriage_election_catalogue
    catalogue=marriage_election_catalogue()
    assert ('kp_marriage','research_only') not in catalogue['research_variants']
    for profile in catalogue['additional_profiles']:
        personal=MarriagePersonalContext((MarriageParticipant('b','bride',0.,0.),MarriageParticipant('g','groom',10.,20.)),profile=profile.personal_profile)
        result=assess_marriage_election(evidence(),policy=policy(profile.profile),personal=personal)
        admitted={c.family_id for c in profile.rule_contracts}
        assert {r.family_id for r in result.astronomical_findings+result.personal_findings}<=admitted
        assert len(admitted)==len(profile.rule_contracts)
        assert all(c.transition_dependencies and c.fixture_references and c.missing_input_behavior for c in profile.rule_contracts)
        assert len(profile.source_fingerprint)==64
        for remedy in profile.remedy_contracts:
            assert 'vv.protected_full_jamitra' not in remedy.family_targets


@pytest.mark.parametrize('sign',range(12))
def test_shadvarga_uses_unequal_d30_and_self_counted_d12(sign):
    from moira._muhurta_marriage_vv_hora import varga_lords
    # Primary BJ1.7:5,5,8,7,5; reversed in even zodiac signs.
    ends,owners=((5,10,18,25,30),('Mars','Saturn','Jupiter','Mercury','Venus')) if sign%2==0 else (
        (5,12,20,25,30),('Venus','Mercury','Jupiter','Saturn','Mars'))
    for end,owner in zip(ends,owners):
        assert varga_lords(nextafter(sign*30.+end,-inf))[-1]==owner
    assert varga_lords(sign*30.)[0]==varga_lords(sign*30.)[4]


@pytest.mark.parametrize('sign',range(12))
def test_kp_solar_navamsa_wait_keeps_exact_uncertainty_and_one_day_edge(sign):
    from moira import MarriageAngularHistoryEvent
    from moira._muhurta_marriage_tradition_event_rules import findings
    part=(4,6,8)[sign%3]
    target=sign*30.+part*10/3
    event=MarriageAngularHistoryEvent('solar_navamsa',ShuddhiBoundary('entry',99.,98.999,99.001),
        'Sun',None,target,target-.01,target+.01)
    history=extra_history(KP,solar_navamsa_entries=(event,))
    for jd,want in ((99.999,None),(100.,None),(100.001,None),(100.002,False),(99.5,True),(98.,False)):
        e=replace(evidence(Sun=target+.2,Moon=50.),jd_ut1=jd,star_history=history)
        result=next(x for x in findings(e,policy(KP),{'Sun':target+.2,'Moon':50.}) if x.family_id=='kp.shadaseethimukha')
        assert result.detected is want


def test_vv_event_contamination_needs_two_actual_complete_traversals():
    from moira import MarriageAngularHistoryEvent,MarriageStarPassage
    from moira._muhurta_marriage_tradition_event_rules import findings
    event=MarriageAngularHistoryEvent('planetary_conjunction',ShuddhiBoundary('bheda',40.,39.99,40.01),
        'Mars','Jupiter',0.,25.,25.,24.99,25.01)
    past=tuple(MarriageStarPassage('Moon',1,_point('entry',a),_point('exit',a+1)) for a in (50.,78.))
    history=replace(extra_history(VV,conjunction_events=(event,)),planets=('Moon',),passages=past)
    for jd,want in ((78.5,True),(79.,False),(100.,False)):
        e=replace(evidence(lagna=20.,Moon=20.),jd_ut1=jd,star_history=history)
        result=tuple(f for f in findings(e,policy(VV),{'Moon':20.}) if f.family_id=='vv.event_star_contamination')
        assert len(result)==2 and all(f.detected is want for f in result)


def eclipse_fixture():
    from moira import MarriageShadowSample,MarriageShadowContact,MarriageEclipseInterval
    def sample(jd,y):
        return MarriageShadowSample(jd,'solar',(150000000.,0.,0.),(384400.,y,0.),20.)
    start=MarriageShadowContact(ShuddhiBoundary('start',90.005,90.,90.01),sample(90.,12000.),sample(90.01,8000.),'start')
    end=MarriageShadowContact(ShuddhiBoundary('end',90.995,90.99,91.),sample(90.99,8000.),sample(91.,12000.),'end')
    return MarriageEclipseInterval(start,end)


def test_eclipse_contact_raw_vectors_and_seven_day_clock_are_retained():
    from moira._muhurta_marriage_tradition_event_rules import findings
    event=eclipse_fixture()
    history=extra_history(VV,eclipse_intervals=(event,))
    for jd,want in ((97.98,True),(97.995,None),(98.,None),(98.001,False)):
        e=replace(evidence(),jd_ut1=jd,star_history=history)
        f=next(x for x in findings(e,policy(VV),{}) if x.family_id=='vv.eclipse_seven_days')
        assert f.detected is want
    with pytest.raises(ValueError,match='state change'):
        replace(event.start,after=replace(event.start.after,moon_xyz_km=(384400.,13000.,0.)))


def test_additional_history_cannot_cross_profile_or_forge_scalar_verdicts():
    from dataclasses import asdict
    from moira_server.models.muhurta_marriage import MarriageTraditionHistoryModel
    history=extra_history(VV)
    with pytest.raises(ValueError,match='selected profile'):
        assess_marriage_election(replace(evidence(),star_history=history),policy=policy(KP))
    payload=asdict(history)
    payload['complete']=True
    with pytest.raises(ValueError):
        MarriageTraditionHistoryModel(**payload)
