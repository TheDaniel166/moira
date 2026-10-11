"""Independent MC04 actors, Boolean quantifiers and boundary fixtures."""
import json
from pathlib import Path
from dataclasses import replace
import pytest
from moira.muhurta_business import (
    BusinessElectionPolicy, BusinessElectionContext, assess_business_election, compare_business_elections, _sale_tithi,
)
from moira.muhurta_election import ElectionEvidence, ElectionPlanet
from moira.muhurta_marriage import MarriageSolarContext
from moira.panchanga_shuddhi import ShuddhiInterval,_point

F=json.loads((Path(__file__).parents[1]/'fixtures/business_election_sources.json').read_text())
ROLES={'purchase':'buyer','sale':'seller','first_opening_for_trade':'trading_operator'}


def evidence(**p):
    return ElectionEvidence(.4,tuple(ElectionPlanet(k,v) for k,v in p.items()))


def result(e,purpose):
    return assess_business_election(e,policy=BusinessElectionPolicy(purpose),context=BusinessElectionContext(
        'actor',ROLES[purpose],'first_opening_for_trade' if purpose=='first_opening_for_trade' else 'acceptance_exchange'))


def with_clock(e,lagna,weekday):
    return replace(e,lagna_sidereal_longitude=lagna,solar=MarriageSolarContext(
        ShuddhiInterval(_point('rise',0.),_point('rise',1.)),_point('set',.5),weekday))


@pytest.mark.parametrize('purpose,fixture',[('purchase','purchase_star27'),('sale','sale_star27'),('first_opening_for_trade','opening_star27')])
def test_all_stars_and_complements(purpose,fixture):
    for star in range(27):
        r=result(evidence(Moon=(star+.5)*360/27),purpose)
        assert r.astronomical_findings[0].detected == (star not in F[fixture])


def test_every_tithi_tier_and_weekday_conflict():
    for tithi in range(30):
        for day in range(7):
            r={name:passed for name,passed,_ in _sale_tithi(tithi,0,day)}
            assert r['grade'] == (tithi+1 in F['sale_best_absolute_tithi1'])
            for name in ('dagdha','visha','hutashana'):
                assert r[name] == (tithi%15+1 != F['weekday_'+name][day])


def test_same_sky_opposite_roles_and_no_averaging():
    r=compare_business_elections(evidence(Moon=5.),buyer_id='buyer',seller_id='seller')
    assert r.buyer.astronomical.status == 'passes_selected_profile'
    assert r.seller.astronomical.status == 'restricted'
    assert r.preferred_star_sets_disjoint
    assert r.buyer.context.counterparty_id == r.seller.context.actor_id
    with pytest.raises(ValueError):
        compare_business_elections(evidence(),buyer_id='same',seller_id='same')


def test_vipani_and_specific_priority_are_satisfiable():
    e=with_clock(evidence(Sun=70.,Moon=10.,Venus=15.,Mercury=40.,Jupiter=280.,Saturn=80.,Mars=130.),5.,1)
    r=result(e,'first_opening_for_trade')
    assert r.astronomical.status == 'passes_selected_profile'
    for body in ('Moon','Venus'):
        changed=replace(e,planets=tuple(replace(p,sidereal_longitude=45.) if p.planet==body else p for p in e.planets))
        row=next(f for f in result(changed,'first_opening_for_trade').astronomical_findings if f.rule_id.endswith('Moon_AND_Venus_lagna'))
        assert row.detected is True
    assert result(replace(e,solar=None),'first_opening_for_trade').astronomical.status == 'indeterminate'


def test_sale_satisfiability_and_no_implicit_purchase_requirements():
    e=with_clock(evidence(Sun=255.,Moon=20.,Mercury=260.,Venus=275.,Jupiter=95.,Mars=340.,Saturn=130.),200.,4)
    assert result(e,'sale').astronomical.status == 'passes_selected_profile'
    assert result(evidence(Moon=5.),'purchase').astronomical.coverage_complete
    assert result(evidence(),'purchase').astronomical.status == 'indeterminate'


@pytest.mark.parametrize('role,anchor',[('seller','acceptance_exchange'),('buyer','first_opening_for_trade'),('trading_operator','acceptance_exchange')])
def test_wrong_role_or_anchor_is_not_relabelled(role,anchor):
    with pytest.raises(ValueError):
        assess_business_election(evidence(),policy=BusinessElectionPolicy('purchase'),context=BusinessElectionContext('x',role,anchor))


def test_same_actor_extra_natal_and_unsupported_purposes_rejected():
    with pytest.raises(ValueError):
        BusinessElectionContext('x','buyer','acceptance_exchange','x')
    with pytest.raises(TypeError):
        BusinessElectionContext('x','buyer','acceptance_exchange',participant={})
    for purpose in ('lending','incorporation','contract','purchase_and_sale'):
        with pytest.raises(ValueError):
            BusinessElectionPolicy(purpose)
