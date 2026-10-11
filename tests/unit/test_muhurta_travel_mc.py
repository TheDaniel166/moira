"""Independent source tables, finite boundary witnesses and remedy isolation."""
import json
from pathlib import Path
from dataclasses import replace
from math import nextafter, inf
import pytest

from moira.muhurta_travel import TravelElectionPolicy,TravelElectionContext,assess_travel_election
from moira.muhurta_election import ElectionEvidence,ElectionPlanet,ElectionParticipant
from moira.muhurta_marriage import MarriageSolarContext
from moira.muhurta_dosha import DoshaPhaseSpan
from moira.panchanga_shuddhi import _point,ShuddhiInterval

FIX=json.loads((Path(__file__).parents[1]/'fixtures/travel_election_sources.json').read_text())
PROFILE='mc_maniprabha_1948_ordinary_land.v1'
DIRECTIONS=('east','southeast','south','southwest','west','northwest','north','northeast')


def evidence(jd=.2,day=5,sun=5.,moon=65.,lagna=65.,**positions):
    p=dict(Sun=sun,Moon=moon,Mercury=75.,Venus=95.,Mars=125.,Jupiter=185.,Saturn=225.,Rahu=255.,Ketu=75.)
    p.update(positions)
    return ElectionEvidence(jd,tuple(ElectionPlanet(k,v,1.) for k,v in p.items()),lagna,
        MarriageSolarContext(ShuddhiInterval(_point('rise',0.),_point('rise',1.)),_point('set',.5),day))


def assess(e=None,direction='east',**context):
    return assess_travel_election(e or evidence(),policy=TravelElectionPolicy(PROFILE),
        context=TravelElectionContext('a','leave_residence',direction,**context))


def row(result,rid):
    return next(f for f in result.astronomical_findings+result.personal_findings if f.rule_id==rid)


def test_source_grade_and_all_direction_star_weekday_pairs():
    for star in range(27):
        e=evidence(moon=(star+.5)*360/27)
        r=assess(e)
        f=row(r,'travel.mc_star')
        assert f.detected==(star not in FIX['best_stars_zero_based']+FIX['middling_stars_zero_based'])
        for i,direction in enumerate(DIRECTIONS):
            r=assess(e,direction)
            assert row(r,'travel.mc_direction_shula.star').detected==(star==FIX['direction_star_shula'][i//2])
    for day in range(7):
        for i,direction in enumerate(DIRECTIONS):
            assert row(assess(evidence(day=day),direction),'travel.mc_direction_shula.weekday').detected==(day in FIX['direction_weekdays'][i//2])


def test_mc_printed_example_is_not_kp_arithmetic():
    # Sun110 Moon162 gives Panchami, Hasta; Sunday one-based1.
    r=assess(evidence(day=0,sun=110.,moon=162.))
    values=[row(r,'travel.mc_three_moduli.'+str(n)) for n in (7,8,3)]
    assert [[m.value for m in f.measures] for f in values]==[[19,5],[19,3],[19,1]]
    assert all(not f.detected for f in values)


def test_siddha_cancels_only_tithi_not_weekday_or_direction():
    r=assess(evidence(day=6,sun=0.,moon=37.))  # Saturday Rikta4
    f=row(r,'travel.mc_tithi')
    assert f.detected and f.exceptions[0].satisfied and not f.effective_restriction
    assert row(r,'travel.mc_weekday').effective_restriction
    assert row(r,'travel.mc_direction_shula.weekday').effective_restriction
    assert not row(r,'travel.mc_import.dagdha').exceptions


def test_parigha28_and_four_star_relief_are_targeted():
    for star in range(27):
        r=assess(evidence(moon=(star+.5)*360/27),'north')
        f=row(r,'travel.mc_parigha')
        assert f.exceptions[0].satisfied==(star in FIX['parigha_relief_stars'])
        assert f.exceptions[0].targets==('travel.mc_parigha',)
    # Unequal inserted Abhijit belongs to west group, not a 27-position chakra.
    assert not row(assess(evidence(moon=278.),'west'),'travel.mc_parigha').detected


def test_yogini_new_moon_is_not_full_moon_and_left_is_relative():
    for absolute in range(1,31):
        number=30 if absolute==30 else (absolute-1)%15+1
        owner=next(i for i,v in enumerate(FIX['yogini_paksha_tithis_with_new_moon_30']) if number in v)
        for i,direction in enumerate(DIRECTIONS):
            f=row(assess(evidence(sun=0.,moon=(absolute-1)*12+1),direction),'travel.mc_yogini')
            assert f.detected==(owner in (i,(i-2)%8))


def test_time_thirds_and_southern_abhijit_are_parent_derived():
    e=evidence(moon=45.)  # Rohini: first daylight third
    for jd,bad in ((nextafter(1/6,-inf),True),(1/6,False),(nextafter(1/6,inf),False)):
        assert row(assess(replace(e,jd_ut1=jd)),'travel.mc_time_star').detected is bad
    e=evidence(jd=.25,moon=60.)
    f=row(assess(e,'south'),'travel.mc_southern.abhijit_muhurta')
    assert f.detected and any(m.unit=='JD_UT1' for m in f.measures)
    assert not row(assess(e,'north'),'travel.mc_southern.abhijit_muhurta').applicable


def test_mc48_vishanadi_width_scales_with_actual_parent():
    # Rohini lasts54ghatis: exclusion starts36, ends39.6, not40.
    span=DoshaPhaseSpan('nakshatra',3,ShuddhiInterval(_point('star',0.),_point('star',.9)))
    e=evidence(jd=39.8/60,moon=45.)
    e=replace(e,phase_spans=(span,))
    f=row(assess(e),'travel.mc_import.vishanadi')
    assert f.detected is False
    assert 'BOTH' in f.source


def test_venus_relief_has_exact_first_pada_boundary_and_no_asta_relief():
    for moon,relief in ((nextafter(30.,-inf),True),(30.,False),(1040/3,True),(346.,False)):
        r=assess(evidence(moon=moon),'west')
        f=row(r,'travel.mc_venus_facing')
        assert f.detected and f.exceptions[0].satisfied is relief
        assert row(r,'travel.mc_venus_state.asta').detected is None
        assert not row(r,'travel.mc_venus_state.asta').exceptions


def test_prior_actual_departure_does_not_expire_entire_journey_or_cancel_rules():
    for nights in (0,4,5,50):
        r=assess(prior_departure_jd_ut1=-30.,completed_stop_nights=nights,leg='return')
        values={m.name:m.value for m in row(r,'travel.mc_prior_departure').measures}
        assert values['fresh_election_required']==(nights>=5)
        assert values['earlier_election_inherited'] is False
    with pytest.raises(ValueError):
        assess(prior_departure_jd_ut1=.3)
    with pytest.raises(ValueError):
        assess(completed_stop_nights=5)
    with pytest.raises(ValueError):
        assess(prior_departure_jd_ut1=-1.,completed_stop_nights=True)


def test_natal_layer_missing_values_and_pisces_targeted_exception():
    missing=assess(participant=ElectionParticipant('a'))
    assert not missing.personal_decision.coverage_complete
    p=ElectionParticipant('a',331.,331.)
    r=assess(evidence(lagna=331.),participant=p)
    f=row(r,'travel.mc_lagna.rashi')
    assert f.detected and f.exceptions[0].satisfied and not f.effective_restriction
    assert row(assess(evidence(lagna=301.),participant=p),'travel.mc_lagna.rashi').effective_restriction


def test_imports_are_explicit_and_do_not_smuggle_preferences_or_remedies():
    r=assess()
    families={f.family_id for f in r.astronomical_findings}
    assert 'travel.mc_import.star_history' in families
    assert 'travel.mc_import.calendar' not in families
    assert not any(f.rule_id.endswith('navamsa_allowed_sign') for f in r.astronomical_findings)
    assert not any(f.family_id.startswith('travel.kp') for f in r.astronomical_findings)
    assert all(not f.exceptions for f in r.astronomical_findings if f.family_id.startswith('travel.mc_import.'))
    assert r.astronomical.status!='passes_selected_profile'  # missing histories stay unknown
