"""Source tables, hostile evidence and satisfiability of residential elections."""
import json
from dataclasses import replace
from fractions import Fraction
from math import inf, nextafter
from pathlib import Path

import pytest

from moira.muhurta_election import ElectionEvidence, ElectionPlanet, ElectionParticipant
from moira.muhurta_vastu import VastuElectionPolicy, VastuElectionContext, assess_vastu_election, _ordinal
from moira._muhurta_vastu_sources import FOUNDATION_FORBIDDEN_TITHIS, VAMA_RAVI, MANIFEST_SHA256
from moira.muhurta_marriage import MarriageSolarContext
from moira.panchanga_shuddhi import ShuddhiInterval, _point

F = json.loads((Path(__file__).parents[1]/'fixtures/vastu_election_sources.json').read_text())


def evidence(**positions):
    return ElectionEvidence(.4, tuple(ElectionPlanet(p, x) for p, x in positions.items()))


def assess(e, purpose='foundation', facing='east', **context):
    return assess_vastu_election(e, policy=VastuElectionPolicy(purpose), context=VastuElectionContext(facing, **context))


def rows(e, **kwargs):
    r = assess(e, **kwargs)
    return {f.rule_id: f for f in r.astronomical_findings + r.personal_findings}


def test_independent_source_tithi_partition_and_north_wrap():
    assert dict(VAMA_RAVI)['north'] == tuple(F['north_vama_ravi_houses'])
    for direction, forbidden in FOUNDATION_FORBIDDEN_TITHIS:
        assert [i+1 for i in forbidden] == F['foundation_forbidden_tithis_one_based'][direction]
        for tithi in range(30):
            f = rows(evidence(Sun=0., Moon=tithi*12.+1.), facing=direction)['vastu.foundation_facing_tithi']
            assert f.detected == (tithi in forbidden)
    assert sorted(i for _, values in FOUNDATION_FORBIDDEN_TITHIS for i in values) == list(range(30))


def test_all_cyclic_chakra_counts_use_distinct_partitions():
    # Interior representatives independently enumerate physical27 and unequal28.
    points27 = [(i+.5)*360/27 for i in range(27)]
    edges28 = sorted(set([i*360/27 for i in range(28)] + [830/3,2528/9]) - {280.})
    points28 = [(a+b)/2 for a,b in zip(edges28,edges28[1:])]
    assert len(points28) == 28
    for size, points, key, good in ((28,points28,'vastu.foundation_vrisha',F['vrisha_good']),
                                  (27,points27,'vastu.entry_kalasha',F['kalasha_good'])):
        for i, sun in enumerate(points):
            for j, moon in enumerate(points):
                expected = (j-i)%size+1
                assert _ordinal(sun,moon,size) == expected
                purpose = 'foundation' if size == 28 else 'return_entry'
                assert rows(evidence(Sun=sun,Moon=moon),purpose=purpose)[key].detected == (expected not in good)


def test_abhijit_edges_and_no_rescaling_of_27_star_calendar():
    for edge in (Fraction(830,3),Fraction(2528,9)):
        a,b = nextafter(float(edge),-inf), nextafter(float(edge),inf)
        assert _ordinal(0.,b,28) == _ordinal(0.,a,28)+1
        assert _ordinal(0.,b,27) == _ordinal(0.,a,27)


def test_foundation_is_satisfiable_and_missing_corner_stays_unknown():
    # A logical fixture, deliberately not presented as an observed real chart.
    e = evidence(Sun=31., Moon=140., Mercury=35., Venus=70., Jupiter=340., Mars=130., Saturn=280.)
    e = replace(e,lagna_sidereal_longitude=340.,solar=MarriageSolarContext(
        ShuddhiInterval(_point('rise',0.),_point('rise',1.)),_point('set',.5),1))
    result = assess(e,facing='north',excavation_corner='southwest')
    assert result.astronomical.status == 'passes_selected_profile'
    assert result.astronomical.coverage_complete
    assert result.source_manifest_sha256 == MANIFEST_SHA256
    assert assess(e,facing='north').astronomical.status == 'indeterminate'
    assert rows(e,facing='north',excavation_corner='northwest')['vastu.excavation_corner'].detected is True


def test_missing_evidence_and_personal_layer_are_distinct():
    r = assess(evidence())
    assert r.astronomical.status == 'indeterminate'
    assert r.personal_decision.status == 'not_requested'
    r = assess(evidence(),purpose='first_entry',participant=ElectionParticipant('resident'))
    assert r.personal_decision.status == 'indeterminate'


def test_old_house_relief_retains_original_asta_fact():
    old = rows(evidence(),purpose='old_house_entry')['vastu.entry_availability.Jupiter']
    ordinary = rows(evidence(),purpose='first_entry')['vastu.entry_availability.Jupiter']
    assert old.detected is ordinary.detected is None
    assert old.applicable is False and old.coverage_complete and old.exceptions[0].satisfied
    assert ordinary.applicable and not ordinary.coverage_complete


def test_purna_does_not_waive_amavasya():
    r = rows(evidence(Sun=0.,Moon=355.),purpose='return_entry',facing='east')
    assert r['vastu.entry_facing_tithi'].detected is False
    assert r['vastu.entry_panchanga.tithi'].detected is True


def test_natal_birth_sign_is_allowed_but_eighth_is_not():
    resident = ElectionParticipant('resident',40.,40.)
    e = replace(evidence(Sun=359.,Moon=57.),lagna_sidereal_longitude=40.)
    r = rows(e,purpose='return_entry',participant=resident)
    assert r['vastu.personal_entry.moon_eighth'].detected is False
    r = rows(replace(e,lagna_sidereal_longitude=250.),purpose='return_entry',participant=resident)
    assert r['vastu.personal_entry.moon_eighth'].detected is True


@pytest.mark.parametrize('purpose,context',[
    ('first_entry',{'extraordinary_reason':'fire'}),('extraordinary_entry',{}),
    ('foundation',{'participant':ElectionParticipant('resident')}),('return_entry',{'excavation_corner':'northeast'}),
])
def test_incompatible_context_rejected(purpose,context):
    with pytest.raises(ValueError):
        assess(evidence(),purpose=purpose,**context)


@pytest.mark.parametrize('value',[True,float('nan'),float('inf'),-.1,360.])
def test_hostile_natal_angles(value):
    with pytest.raises((ValueError,TypeError)):
        ElectionParticipant('resident',value)


def test_manifest_and_policy_cannot_claim_other_traditions():
    with pytest.raises(ValueError):
        VastuElectionPolicy('foundation',profile='universal_vastu')
    with pytest.raises(ValueError):
        VastuElectionContext('northeast')
