"""MC scan/arithmetic fixtures and adversarial kernel-free composition tests."""
import json
from dataclasses import replace
from fractions import Fraction
from math import nextafter, inf
from pathlib import Path

import pytest

from moira import _muhurta_marriage_sources as S
from moira.muhurta_marriage import (MarriageElectionPolicy, MarriageElectionEvidence,
    MarriagePlanet, MarriageParticipant, MarriagePersonalContext, MarriageSolarContext,
    MarriageFinding, MarriageException, assess_marriage_election)
from moira._muhurta_marriage_rules import star28
from moira.panchanga_shuddhi import _point, ShuddhiInterval
from moira.muhurta_lagna import _nature

FIXTURE = json.loads((Path(__file__).parents[1]/'fixtures/marriage_election_sources.json').read_text())
POLICY = MarriageElectionPolicy('exchange of vows','all_regions',remedies=())


def evidence(**positions):
    return MarriageElectionEvidence(2460000.,tuple(MarriagePlanet(p,x) for p,x in positions.items()))


def rows(e, policy=POLICY, personal=None):
    return {f.rule_id:f for f in assess_marriage_election(e,policy=policy,personal=personal).astronomical_findings}


def test_primary_transcription_tables():
    assert [S.STARS[i] for i in S.WEDDING_STARS] == FIXTURE['wedding_star_names']
    for table,name in ((S.SEVEN_LINE_PAIRS,'seven_line_pairs'),(S.FIVE_LINE_PAIRS,'five_line_pairs')):
        assert [[S.STARS28[a],S.STARS28[b]] for a,b in table] == FIXTURE[name]
    assert dict(S.INGRESS_TOTAL_GHATIS) == FIXTURE['ingress_total_ghatis']
    assert list(S.FORBIDDEN_PAKSHA_TITHIS) == FIXTURE['forbidden_paksha_tithis']
    for planet,count,direction in S.LATTA:
        assert S.STARS[(direction*(count-1))%27] == FIXTURE['latta_from_ashwini'][planet]


def test_mc72_southern_bana_categories_follow_primary_commentary():
    # MC Avasthi printed139, PDF148: eight illness, two fire, four royal,
    # six theft, one death. This is independent of the runtime ordering.
    assert dict(S.SOUTHERN_BANA)=={8:'illness',2:'fire',4:'royal',6:'theft',1:'death'}


def test_exact_unequal_abhijit_boundaries_and_original_padas():
    for rational,before,after in ((Fraction(830,3),20,21),(Fraction(2528,9),21,22)):
        approximate = float(rational)
        low,high = nextafter(approximate,-inf),nextafter(approximate,inf)
        assert star28(low)[0] == before
        assert star28(high)[0] == after
    assert star28(277.) == (21,1)
    assert star28(280.9) == (22,1)  # Shravana original first pada survives clipping.
    assert star28(276.) == (20,3)   # Do not rescale clipped Uttara Ashadha.


def test_missing_evidence_never_passes_and_no_resource_access(monkeypatch):
    import moira.spk_reader
    monkeypatch.setattr(moira.spk_reader,'get_reader',lambda: pytest.fail('pure path opened a reader'))
    result = assess_marriage_election(evidence(),policy=POLICY)
    assert result.astronomical.status == 'indeterminate'
    assert not result.astronomical.coverage_complete
    assert result.personal_decision.status == 'not_requested'
    assert result.requested_composition.status == 'indeterminate'
    assert result.input_basis == 'caller_supplied_conditional_on_evidence'


def test_restriction_survives_missing_other_inputs():
    result = assess_marriage_election(evidence(Sun=0.,Moon=20.),policy=POLICY)
    assert result.astronomical.status == 'restricted'
    assert not result.astronomical.coverage_complete
    assert 'wedding_star' in result.astronomical.effective_restriction_ids


def test_missing_exception_cannot_cancel():
    f = MarriageFinding('rule','family','source',True,True,(),(
        MarriageException('remedy',('rule',),None,(),'source'),),())
    assert f.effective_restriction is True
    assert f.coverage_complete is False


def test_regions_change_applicability_not_arithmetic():
    e = evidence(Sun=0.,Moon=107.,Rahu=0.)
    a = rows(e)
    b = rows(e,replace(POLICY,regional_tradition='saurashtra_shalva'))
    assert a['latta.rahu'].applicable is False
    assert b['latta.rahu'].applicable is True
    assert a['latta.rahu'].detected == b['latta.rahu'].detected is True


def test_karana_does_not_import_unsourced_kinstughna_ban():
    assert rows(evidence(Sun=0.,Moon=1.))['wedding_karana'].detected is False
    assert rows(evidence(Sun=0.,Moon=43.))['wedding_karana'].detected is True


def test_both_pakshas_apply_wider_tithi_restrictions():
    for half in (0,15):
        for tithi in FIXTURE['forbidden_paksha_tithis']:
            r = rows(evidence(Sun=0.,Moon=(half+tithi-1)*12.+1.))
            assert r['wedding_tithi'].detected is True
    assert rows(evidence(Sun=0.,Moon=349.))['wedding_tithi'].detected is True


def test_solar_bana_uses_whole_degrees_and_marriage_death_scope():
    for x,want in ((.999999,False),(1.,True),(nextafter(1.,inf),True)):
        e = evidence(Sun=x,Moon=100.)
        r = rows(e)['solar_bana.death']
        assert r.detected is want
        assert r.applicable is True


def test_saturday_extra_kulika_is_last_night_fifteenth():
    solar = MarriageSolarContext(ShuddhiInterval(_point('rise',0.),_point('next_rise',1.)),_point('set',.5),6)
    e = replace(evidence(Sun=0.,Moon=100.),jd_ut1=.99,solar=solar)
    r = rows(e)['kulika.saturday_last']
    assert r.detected is True
    assert rows(replace(e,jd_ut1=.49))['kulika.saturday_last'].detected is False


def test_kartari_requires_specific_motion_pair():
    e = MarriageElectionEvidence(2460000.,(
        MarriagePlanet('Sun',330.,1.),MarriagePlanet('Moon',100.,13.),MarriagePlanet('Mars',40.,-1.)),5.)
    assert rows(e)['kartari.lagna.sun.mars'].detected is True
    changed = replace(e,planets=tuple(replace(p,longitude_speed=1.) if p.planet=='Mars' else p for p in e.planets))
    assert 'kartari.lagna.sun.mars' not in rows(changed)


def test_personal_moon_does_not_reuse_generic_first_house_permission():
    personal = MarriagePersonalContext((MarriageParticipant('a','bride',100.,first_born=False),
                                        MarriageParticipant('b','groom',100.,first_born=False)))
    result = assess_marriage_election(evidence(Sun=0.,Moon=100.,Jupiter=160.),policy=POLICY,personal=personal)
    found = {f.rule_id:f for f in result.personal_findings}
    assert found['personal_shuddhi.a.moon'].detected is True
    assert found['personal_tara.a'].detected is False
    assert result.personal_decision.status == 'restricted'


@pytest.mark.parametrize('kwargs',[
    {'jd_ut1':True},{'jd_ut1':float('nan')},{'planets':[MarriagePlanet('Sun',0.)]},
    {'planets':(MarriagePlanet('Sun',0.),MarriagePlanet('Sun',1.))},
    {'planets':(MarriagePlanet('Rahu',10.),MarriagePlanet('Ketu',200.))},
])
def test_direct_rejects_malformed_evidence(kwargs):
    with pytest.raises((ValueError,TypeError)):
        MarriageElectionEvidence(**({'jd_ut1':2460000.}|kwargs))


def test_unsupported_research_policy_is_not_admitted():
    with pytest.raises(ValueError):
        replace(POLICY,profile='raman_marriage')
    with pytest.raises(ValueError):
        MarriagePersonalContext((MarriageParticipant('same','bride'),MarriageParticipant('same','groom')))


@pytest.mark.parametrize('weekday,day,night',[
    (0,(14,),()),(1,(9,12),(8,)),(2,(4,),(7,)),(3,(8,),()),
    (4,(6,12),()),(5,(4,9),(8,)),(6,(1,2),(1,)),
])
def test_durmuhurta_preserves_both_primary_deity_tables(weekday,day,night):
    from moira._muhurta_marriage_rules import _solar
    solar=MarriageSolarContext(ShuddhiInterval(_point('rise',0.),_point('next_rise',1.)),_point('set',.5),weekday)
    for start,expected in ((0.,day),(.5,night)):
        for ordinal in range(1,16):
            e=MarriageElectionEvidence(start+(ordinal-.5)/30,solar=solar)
            detected=[f for f in _solar(e) if f.family_id=='durmuhurta' and f.detected]
            assert bool(detected)==(ordinal in expected)


@pytest.mark.parametrize('d9sign',range(12))
def test_mc90_moon11_only_cancels_malefic_owned_lagna_navamsa(d9sign):
    from moira._muhurta_marriage_rules import _remedies
    # Aries D9 traverses the full zodiac in its first twelve physical padas.
    lagna=(d9sign+.5)*10/3
    p={'Moon':(floor_sign(lagna)+10)%12*30+1.}
    raw=tuple(MarriageFinding('lagna_components.'+suffix,'lagna_components','fixture',True,True,(),(),())
              for suffix in ('navamsa_allowed_sign','navamsa_last','navamsa_movable'))
    e=MarriageElectionEvidence(2460000.,(MarriagePlanet('Moon',p['Moon']),),lagna)
    found=tuple(_remedies(raw,e,replace(POLICY,remedies=('mc90_moon_eleventh',)),p))
    assert found[0].effective_restriction is (d9sign not in (0,4,7,9,10))
    assert all(f.effective_restriction and not f.exceptions for f in found[1:])


def floor_sign(longitude):
    return int(longitude//30)


@pytest.mark.parametrize('cleared,pada,expected',[(False,4,True),(True,4,False),(False,3,False)])
def test_mc58_piercing_persists_after_planet_moves_until_full_lunar_clearance(cleared,pada,expected):
    from moira.muhurta_marriage import (MarriageHistoricalSkySpan,MarriageMoon28Passage,
        MarriageExtent,MarriageStarHistory)
    from moira._muhurta_marriage_context import _historical_vedha
    def sky(sun):
        return tuple(MarriagePlanet(p,x) for p,x in {'Sun':sun,'Moon':90.,'Mercury':0.,
            'Venus':0.,'Jupiter':0.,'Mars':0.,'Saturn':0.,'Rahu':0.,'Ketu':180.}.items())
    boundaries=tuple(_point('fixture',float(x)) for x in range(-70,11))
    spans=tuple(MarriageHistoricalSkySpan(ShuddhiInterval(a,b),(a.jd_ut1+b.jd_ut1)/2,
        sky(14. if -40<=a.jd_ut1<-30 else 35.)) for a,b in zip(boundaries,boundaries[1:]))
    entry,exit=(-20.,-19.) if cleared else (-60.,-59.)
    passage=MarriageMoon28Passage(16,_point('Moon_enter',entry),_point('Moon_exit',exit))
    history=MarriageStarHistory(MarriageExtent(-70.,10.),S.NINE,(),spans,(passage,))
    positions={p.planet:p.sidereal_longitude for p in sky(35.)}
    positions['Moon']=16*40/3+(pada-.5)*10/3
    history=replace(history,vedha_spans=tuple(replace(s,planets=tuple(MarriagePlanet(p,x) for p,x in positions.items()))
        if s.interval.contains(0.) is True else s for s in spans))
    e=MarriageElectionEvidence(0.,tuple(MarriagePlanet(p,x) for p,x in positions.items()),star_history=history)
    found={f.rule_id:f for f in _historical_vedha(e,positions)}
    assert found['star_history.historical_five_line'].detected is expected
    assert not rows(e)['five_line_vedha.sun'].detected


def test_mc92_source_cutoff_is_a_restriction_and_capacities_are_not_row_subtraction():
    # All classical planets in Aries against Aries Lagna: Sun/Moon/Mars/Saturn
    # contribute zero under MC87/92; select a known independently inspected
    # low-score arrangement and verify the source cutoff through its receipt.
    positions={'Sun':180.,'Moon':180.,'Mars':180.,'Mercury':180.,'Jupiter':180.,
               'Venus':180.,'Saturn':180.,'Rahu':180.,'Ketu':0.}
    e=MarriageElectionEvidence(0.,tuple(MarriagePlanet(p,x) for p,x in positions.items()),0.)
    result=rows(e)
    f=result['lagna_components.placement_score_below_five']
    measures={m.name:m.value for m in f.measures}
    assert measures['score']==0
    assert f.detected is True and f.advisory is False
    for p,capacity in (('mercury',100),('venus',200),('jupiter',100000)):
        item=result['broad_remedies.mc91_capacity_'+p]
        assert item.advisory and not item.effective_restriction
        assert {m.name:m.value for m in item.measures}['source_capacity']==capacity


@pytest.mark.parametrize('pada,cleared,expected',[(1,False,None),(3,False,False),(1,True,False)])
def test_historical_coincident_band_does_not_infer_clearance_from_clear_endpoints(pada,cleared,expected):
    from moira.muhurta_marriage import (MarriageHistoricalSkySpan,MarriageMoon28Passage,
        MarriageExtent,MarriageStarHistory,MarriageHistoricalSkyBand,MarriageHistoricalLongitude)
    from moira.panchanga_shuddhi import ShuddhiBoundary
    from moira._muhurta_marriage_context import _historical_vedha
    band=ShuddhiBoundary('Mercury_ingress+Sun_ingress',-2.,-2.001,-1.999)
    edges=tuple(band if x==-2 else _point('fixture',float(x)) for x in range(-7,2))
    def sky(after):
        return {'Sun':120.001 if after else 119.999,'Mercury':90.001 if after else 89.999,
                'Moon':150.,'Venus':0.,'Jupiter':0.,'Mars':0.,'Saturn':0.,'Rahu':0.,'Ketu':180.}
    spans=tuple(MarriageHistoricalSkySpan(ShuddhiInterval(a,b),(a.upper_jd_ut1+b.lower_jd_ut1)/2,
        tuple(MarriagePlanet(p,x) for p,x in sky(a.jd_ut1>=-2).items())) for a,b in zip(edges,edges[1:]))
    a,b=sky(False),sky(True)
    raw=MarriageHistoricalSkyBand(band,tuple(MarriageHistoricalLongitude(p,min(a[p],b[p]),max(a[p],b[p]))
        for p in S.NINE),(29.999,30.001))
    entry,exit=(-1.,-.5) if cleared else (-6.,-5.)
    passage=MarriageMoon28Passage(18,_point('entry',entry),_point('exit',exit))
    history=MarriageStarHistory(MarriageExtent(-7.,1.),S.NINE,(),spans,(passage,),(raw,))
    positions=sky(True)|{'Moon':240+(pada-.5)*10/3}
    history=replace(history,vedha_spans=tuple(replace(s,planets=tuple(MarriagePlanet(p,x) for p,x in positions.items()))
        if s.interval.contains(0.) is True else s for s in spans))
    e=MarriageElectionEvidence(0.,tuple(MarriagePlanet(p,x) for p,x in positions.items()),star_history=history)
    assert _nature(sky(False))['Mercury'] is _nature(sky(True))['Mercury'] is True
    f=next(f for f in _historical_vedha(e,positions) if f.rule_id=='star_history.historical_five_line')
    assert f.detected is expected


def test_historical_mercury_association_survives_later_benefic_nature():
    from moira.muhurta_marriage import (MarriageHistoricalSkySpan,MarriageStarPassage,
        MarriageExtent,MarriageStarHistory)
    from moira._muhurta_marriage_context import _mercury_occupancy
    def sky(sun):
        return tuple(MarriagePlanet(p,x) for p,x in {'Sun':sun,'Mercury':91.,'Moon':150.,
            'Venus':0.,'Jupiter':0.,'Mars':0.,'Saturn':0.,'Rahu':0.,'Ketu':180.}.items())
    edges=tuple(_point('fixture',float(x)) for x in range(-7,2))
    spans=tuple(MarriageHistoricalSkySpan(ShuddhiInterval(a,b),(a.jd_ut1+b.jd_ut1)/2,
        sky(100. if a.jd_ut1<-2 else 121.)) for a,b in zip(edges,edges[1:]))
    mercury=MarriageStarPassage('Mercury',6,_point('entry',-4.),_point('exit',1.))
    moon=MarriageStarPassage('Moon',6,_point('entry',-6.),_point('exit',-5.))
    history=MarriageStarHistory(MarriageExtent(-7.,1.),S.NINE,(moon,mercury),spans)
    assert _mercury_occupancy(history,mercury,0.) is True
    assert _nature({p.planet:p.sidereal_longitude for p in sky(121.)})['Mercury'] is True


def test_manifest_covers_all_inventory_rows_and_every_executable_family():
    from moira.muhurta_marriage import marriage_election_catalogue
    catalogue=marriage_election_catalogue()
    contracts=catalogue['rule_contracts']
    assert {c.family_id for c in contracts}=={r.rule_id for r in S.RULES}
    ids={c.inventory_id for c in contracts}|{i for i,_ in catalogue['supporting_contracts']}
    assert ids=={f'M{i:02}' for i in range(1,31)}|{f'F{i:02}' for i in range(1,10)}
    root=Path(__file__).parents[2]
    for c in contracts:
        assert c.formula and c.authority and c.transition_dependencies and c.transport_fields
        assert all((root/path).is_file() for path in c.fixture_references)


@pytest.mark.parametrize('month,sun,paksha,tithi,bad',[
    (3,61.,'Shukla',10,False),(3,61.,'Shukla',11,True),
    (3,61.,'Krishna',10,True),(3,31.,'Shukla',10,True),
    (7,211.,'Shukla',5,False),(9,271.,'Shukla',5,False),
    (4,91.,'Shukla',5,True),(0,1.,'Shukla',5,False),
])
def test_vivaha13_lunar_qualifications_and_ashadha_boundary(month,sun,paksha,tithi,bad):
    from types import SimpleNamespace
    from moira._muhurta_marriage_context import _calendar
    # Independently stated verse/composition cases; aggregate tithi vetoes
    # remain separate from this calendar qualification.
    e=SimpleNamespace(lunar_month=SimpleNamespace(label=SimpleNamespace(index=month,qualifier='ordinary'),
        paksha=paksha,tithi_number=tithi))
    found={f.rule_id:f for f in _calendar(e,POLICY,{'Sun':sun})}
    assert found['calendar.lunar_month'].detected is bad


@pytest.mark.parametrize('is_day,expected',[(True,{'blind':(0,1,4),'deaf':(6,7),'lame':(10,)}),
                                         (False,{'blind':(2,3,5),'deaf':(8,9),'lame':(11,)})])
def test_mc81_all_signs_in_both_halves(is_day,expected):
    from moira._muhurta_marriage_rules import _lagna
    solar=MarriageSolarContext(ShuddhiInterval(_point('rise',0.),_point('next',1.)),_point('set',.5),1)
    for sign in range(12):
        e=MarriageElectionEvidence(.25 if is_day else .75,lagna_sidereal_longitude=sign*30+1,solar=solar)
        found={f.rule_id:f for f in _lagna(e,POLICY,{},_nature({}))}
        for name,signs in expected.items():
            assert found['lagna_day_night.'+name].detected is (sign in signs)


@pytest.mark.parametrize('moon_house,mercury_house,total,bad',[(7,7,0.,True),(7,1,2.,True),(2,7,5.,False),(2,1,7.,False)])
def test_mc92_exact_five_point_cutoff(moon_house,mercury_house,total,bad):
    p={name:180. for name in S.NINE}
    p['Ketu']=0.
    p['Moon']=(moon_house-1)*30+1.
    p['Mercury']=(mercury_house-1)*30+1.
    e=MarriageElectionEvidence(0.,tuple(MarriagePlanet(name,x) for name,x in p.items()),1.)
    f=rows(e)['lagna_components.placement_score_below_five']
    assert next(m.value for m in f.measures if m.name=='score')==total
    assert f.detected is bad


@pytest.mark.parametrize('event_time,expected',[(10.4,True),(9.4,False),(10.,None)])
def test_pata_requires_the_same_complete_star_occurrence(event_time,expected):
    from types import SimpleNamespace as NS
    from moira._muhurta_marriage_context import _pata
    from moira.panchanga_shuddhi import ShuddhiBoundary
    parent=NS(kind='nakshatra',interval=ShuddhiInterval(_point('start',10.),_point('end',11.)))
    def ending(i,t):
        return NS(yoga_index=i,boundary=ShuddhiBoundary('yoga',t,t-.000001,t+.000001),moon_sidereal_longitude=61.)
    e=NS(jd_ut1=10.5,phase_spans=(parent,),yoga_endings=(ending(0,9.),ending(13,event_time),ending(0,12.)))
    f=next(_pata(e,replace(POLICY,regional_tradition='kalinga_vanga'),{'Moon':61.,'Sun':21.}))
    assert f.detected is expected
    assert next(_pata(e,POLICY,{'Moon':61.,'Sun':21.})).applicable is False


@pytest.mark.parametrize('mars,jupiter,satisfied',[(0.,180.,True),(180.,0.,True),(0.,0.,False),(None,0.,None)])
def test_mc83_lagna_lord_or_jupiter_aspect_is_a_disjunction(mars,jupiter,satisfied):
    from moira._muhurta_marriage_rules import _lagna
    solar=MarriageSolarContext(ShuddhiInterval(_point('rise',0.),_point('next',1.)),_point('set',.5),1)
    positions={p:x for p,x in (('Mars',mars),('Jupiter',jupiter)) if x is not None}
    e=MarriageElectionEvidence(.25,tuple(MarriagePlanet(p,x) for p,x in positions.items()),1.,solar=solar)
    f=next(f for f in _lagna(e,replace(POLICY,remedies=('mc83_lagna_aspect',)),positions,_nature(positions))
           if f.rule_id=='lagna_day_night.blind')
    assert f.detected is True
    assert f.exceptions[0].satisfied is satisfied
    assert f.effective_restriction is (satisfied is not True)


def test_remedy_targets_are_finite_and_do_not_absorb_personal_or_visibility_rules():
    from moira._muhurta_marriage_manifest import REMEDY_CONTRACTS
    contracts={c.remedy_id:c for c in REMEDY_CONTRACTS}
    assert set(contracts['mc68_own_or_exalted_luminaries'].family_targets)=={
        'ekargala','upagraha','pata','latta','jamitra','kartari'}
    assert set(contracts['mc89_benefic_kendra_trikona'].family_targets)=={
        'wedding_tithi','calendar','dagdha','lagna_day_night','tithi_sunrise_count','star_history'}
    for contract in contracts.values():
        assert not set(contract.family_targets)&{'personal_tara','personal_shuddhi','birth_period',
            'jupiter_availability','venus_availability'}
    assert not set(contracts[S.GODHULI].family_targets)&{'calendar','solar_ingress','planetary_ingress'}
    from moira.muhurta_marriage import REMEDIES
    assert {c.remedy_id for c in contracts.values() if c.selection=='policy_remedies'}==set(REMEDIES)
    assert contracts['mc71_empty_opposition_or_benefic_lagna'].selection=='intrinsic_rule'


def test_legacy_guidance_migration_preserves_shape_and_corrects_mula_and_tithi_basis():
    from moira.muhurta import ACTIVITY_MUHURTA_GUIDANCE,get_muhurta_guidance_for_activity
    with pytest.warns(DeprecationWarning,match='assess_marriage_election'):
        value=get_muhurta_guidance_for_activity('MARRIAGE')
    assert value is ACTIVITY_MUHURTA_GUIDANCE['marriage']
    assert value['tithi_basis']=='zero_based_absolute_0_to_29'
    assert 'Mula' in value['good_nakshatras'] and 'Mula' not in value['avoid_nakshatras']
    assert len(value['good_nakshatras'])==11
    assert set(value['good_tithis'])|set(value['avoid_tithis'])==set(range(30))
    assert not set(value['good_tithis'])&set(value['avoid_tithis'])
    assert get_muhurta_guidance_for_activity('missing') is None
def test_every_owned_marriage_export_has_identical_public_surface_identity():
    import moira
    import moira.facade
    import moira.vedic
    from moira import muhurta_marriage, muhurta_marriage_dated, muhurta_marriage_visibility
    from moira import _muhurta_marriage_windows

    owned = [(owner, owner.__all__) for owner in
             (muhurta_marriage, muhurta_marriage_dated, muhurta_marriage_visibility)]
    owned.append((_muhurta_marriage_windows, ('MarriageEvidencePart', 'MarriageWindowWitness',
                  'MarriageElectionCell', 'MarriageElectionWindows', 'marriage_election_windows')))
    for owner, names in owned:
        for name in names:
            expected = getattr(owner, name)
            for surface in (moira, moira.facade, moira.vedic):
                assert name in surface.__all__, (surface.__name__, name)
                assert getattr(surface, name) is expected, (surface.__name__, name)
