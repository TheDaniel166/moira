"""KP source arithmetic, strict release edges and component isolation."""
from dataclasses import replace
from math import nextafter,inf
import pytest
from moira.muhurta_travel import TravelElectionPolicy,TravelElectionContext,assess_travel_election
from moira.muhurta_election import ElectionEvidence,ElectionPlanet
from moira.muhurta_marriage import MarriageSolarContext
from moira.panchanga_shuddhi import ShuddhiBoundary,ShuddhiInterval,_point

WEEK='kp_1917_weekday_direction_release.v1'
MOD='kp_1917_travel_modular_tests.v1'


def evidence(jd=.2,weekday=5,sun=43.,moon=94.,lagna=5.,rise=None):
    return ElectionEvidence(jd,(ElectionPlanet('Sun',sun),ElectionPlanet('Moon',moon)),lagna,
        MarriageSolarContext(ShuddhiInterval(_point('rise',0.) if rise is None else rise,_point('rise',1.)),_point('set',.5),weekday))


def assess(e,profile=MOD,direction=None,**kwargs):
    return assess_travel_election(e,policy=TravelElectionPolicy(profile,**kwargs),
        context=TravelElectionContext('traveller','leave_residence',direction))


def test_printed_friday_pushya_panchami_remainders():
    r=assess(evidence())
    rows=[f for f in r.astronomical_findings if f.family_id=='travel.kp_three_moduli']
    assert [next(m.value for m in f.measures if m.name=='remainder') for f in rows]==[4,2,2]
    assert all(f.detected is False for f in rows)
    assert r.policy.scope=='named_component'


def test_all_direction_weekday_pairs_and_strict_release_edges():
    # Independent transcription KP1917 printed148/PDF185.
    cases={'east':((1,6),8),'south':((4,),22),'west':((0,5),15),'north':((2,3),12)}
    for direction,(days,ghatis) in cases.items():
        edge=ghatis/60
        for day in range(7):
            for jd,after in ((nextafter(edge,-inf),False),(edge,False),(nextafter(edge,inf),True)):
                row=assess(evidence(jd=jd,weekday=day),WEEK,direction).astronomical_findings[0]
                assert row.detected == (day in days)
                assert row.exceptions[0].satisfied is after
                assert row.effective_restriction == (day in days and not after)


def test_uncertain_or_absent_sunrise_does_not_release():
    rise=ShuddhiBoundary('rise',0.,-.001,.001)
    r=assess(evidence(jd=8/60,weekday=1,rise=rise),WEEK,'east')
    row=r.astronomical_findings[0]
    assert row.detected is True and row.exceptions[0].satisfied is None
    assert row.effective_restriction is True and not row.coverage_complete
    assert assess(replace(evidence(),solar=None),WEEK,'east').astronomical.status=='indeterminate'


def test_shifted_panchakam_every_residue_and_explicit_tithi_convention():
    for tithi in range(1,31):
        for lagna in range(12):
            e=evidence(sun=0.,moon=(tithi-1)*12.+1.,lagna=lagna*30.+1.)
            for ordinal in ('month_1_to_30','paksha_1_to_15'):
                r=assess(e,tithi_ordinal=ordinal)
                star=int(e.planets[1].sidereal_longitude*27/360)+1
                n=tithi if ordinal=='month_1_to_30' else (tithi-1)%15+1
                total=n+6+star+lagna+1
                rows=[f for f in r.astronomical_findings if f.family_id=='travel.kp_shifted_panchakam']
                assert [f.detected for f in rows]==[(total+s)%9==5 for s in (15,12,10,8,4)]


def test_component_profiles_do_not_imply_other_rules_or_allow_injection():
    assert len(assess(evidence(),WEEK,'east').astronomical_findings)==1
    assert len(assess(evidence(),MOD).astronomical_findings)==9
    with pytest.raises(ValueError):
        assess(evidence(),WEEK,'northeast')
    with pytest.raises(ValueError):
        TravelElectionPolicy('complete_kp_travel')
    with pytest.raises(TypeError):
        TravelElectionPolicy(WEEK,remedies=('cancel_all',))
