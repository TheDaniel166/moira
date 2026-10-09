"""Independent source cases, adversarial contracts and exact D9 boundaries."""
from dataclasses import asdict, replace, FrozenInstanceError
from fractions import Fraction
from math import nextafter, inf
from pathlib import Path
import json
import pytest
from moira import (MuhurtaLagnaPolicy, evaluate_muhurta_lagna_strength, navamsa,
                   varga_sign_index, muhurta_lagna_catalogue)
from moira.constants import SIGNS
from moira.muhurta_lagna import _aspect, _GENERAL, _FIVE, _PAR
from moira.shadbala import ShadbalaResult, SthanaBala, KalaBala, PlanetShadbala, REQUIRED_RUPAS

SOURCE=json.loads((Path(__file__).parents[1]/'fixtures/muhurta_lagna_sources.json').read_text(encoding='utf-8-sig'))
POSITIONS={'Sun':65.,'Moon':35.,'Mars':65.,'Mercury':5.,'Jupiter':5.,'Venus':5.,'Saturn':65.,'Rahu':65.,'Ketu':245.}


def assess(positions=None, lagna=5., **kw):
    return evaluate_muhurta_lagna_strength(POSITIONS if positions is None else positions, jd_ut1=2451545.,
                                          lagna_sidereal_longitude=lagna, **kw)


def by_rule(result, key):
    return next(r for r in result.rules if r.rule_id==key)


def restriction(result,key):
    return next(r for r in result.restrictions if r.rule_id==key)


def strength():
    entries={}
    for p,req in REQUIRED_RUPAS.items():
        s=SthanaBala(60.,20.,15.,60.,15.,170.)
        k=KalaBala(60.,30.,0.,45.,30.,0.,165.)
        total=170+165+60+30+30-5
        entries[p]=PlanetShadbala(p,s,60.,k,30.,30.,-5.,total,total/60,req,total/60>=req)
    return ShadbalaResult(2451545.,'Lahiri',entries)


@pytest.mark.parametrize('planet',list(SOURCE['favorable_houses_and_weights']))
@pytest.mark.parametrize('house',range(1,13))
def test_all_source_house_weights(planet,house):
    good,weight=SOURCE['favorable_houses_and_weights'][planet]
    r=assess({planet:(house-1)*30+1})
    entry=next(x for x in r.placement_score.entries if x.planet==planet)
    assert entry.points==(weight if house in good else 0)
    assert entry.weight==weight and entry.favorable_houses==tuple(good)
    assert r.placement_score.total is None


@pytest.mark.parametrize('example',SOURCE['aspect_examples'])
def test_printed_fractional_aspect_examples(example):
    r=assess({example['planet']:example['longitude']},lagna=8.)
    q=by_rule(r,example['rule'])
    assert q.satisfied is True
    assert any(f"target={example['target']}" in p.evidence and f"aspect_quarters={float(example['quarter_count'])}" in p.evidence for p in q.prerequisites)


@pytest.mark.parametrize('example',SOURCE['last_segment_examples'])
def test_printed_last_navamsa_examples(example):
    r=assess(lagna=example['lagna'])
    assert SIGNS.index(r.lagna_navamsa.sign)==example['d9_sign']
    assert by_rule(r,'navamsa_last_except_vargottama').satisfied==example['satisfied']


@pytest.mark.parametrize('index',range(109))
def test_every_d9_boundary_and_adjacent_float(index):
    # Oracle uses exact rational arithmetic, not the implementation's quotient.
    boundary=float(Fraction(index*10,3))
    for lon in (nextafter(boundary,-inf),boundary,nextafter(boundary,inf)):
        normalized=lon%360
        if normalized==360: normalized=nextafter(360.,0.)
        exact=Fraction.from_float(normalized)*9
        sign=int(exact//30)%12
        result=navamsa(lon)
        assert SIGNS.index(result.sign)==varga_sign_index(lon,9)==sign
        assert 0<=result.sign_degree<30 and sign*30<=result.varga_longitude<(sign+1)*30
        assert result.sign_degree==pytest.approx(float(exact%30),abs=1e-12)


def test_source_score_twenty_and_nodes_do_not_double_count():
    r=assess()
    assert r.placement_score.total==20 and r.placement_score.possible_bands==('auspicious',)
    for s in range(12):
        r=assess(POSITIONS|{'Rahu':s*30+1,'Ketu':((s+6)%12)*30+1})
        nodes=[p.points for p in r.placement_score.entries if p.planet in ('Rahu','Ketu')]
        assert sum(nodes)<=1.5 and r.placement_score.total<=20
    with pytest.raises(ValueError,match='antipodal'):assess(POSITIONS|{'Ketu':65.})


@pytest.mark.parametrize('total,bands',[(10,('inauspicious','middling')),(15,('middling','auspicious')),(5,('inauspicious',)),(0,('prohibited',))])
def test_overlapping_commentary_bands(total,bands):
    # Choose subsets by fixture weights, with each rejected planet in house7.
    import itertools
    planets=list(POSITIONS)
    for subset in itertools.product((False,True),repeat=7):
        selected=dict(zip(planets[:7],subset))
        candidate={p:POSITIONS[p] if selected.get(p) else 185. for p in planets[:7]}
        candidate.update(Rahu=5.,Ketu=185.)
        expected=sum(SOURCE['favorable_houses_and_weights'][p][1] for p,v in selected.items() if v)
        if expected==total:
            assert assess(candidate).placement_score.possible_bands==bands
            return
    pytest.fail('fixture cannot make requested total')


def test_optional_pisces_and_movable_constraint_are_separate():
    four=assess(lagna=39.) # Pisces D9
    five=assess(lagna=39.,policy=MuhurtaLagnaPolicy(navamsa_profile=_FIVE))
    assert by_rule(four,'navamsa_allowed_sign').satisfied is False
    assert by_rule(five,'navamsa_allowed_sign').satisfied is True
    assert by_rule(assess({'Moon':185.},lagna=1.),'navamsa_movable_moon_exception').satisfied is False
    assert by_rule(assess({},lagna=1.),'navamsa_movable_moon_exception').satisfied is None


def test_general_and_marriage_do_not_share_moon_sixth_rule():
    pos=POSITIONS|{'Moon':155.}
    gen=assess(pos,policy=MuhurtaLagnaPolicy(purpose_profile=_GENERAL),natal_moon_sidereal_longitude=305.)
    assert by_rule(gen,'general_moon_upachaya').satisfied is True
    assert by_rule(gen,'general_natal_upachaya').satisfied is True
    assert gen.placement_score is None and not gen.restrictions
    assert restriction(assess(pos),'moon_house_6').detected is True


@pytest.mark.parametrize('planet,lon,lagna,key',[
 ('Venus',155.,5.,'venus_house_6'), # debilitated Virgo
 ('Venus',125.,335.,'venus_house_6'), # enemy Sun sign Leo
 ('Mars',95.,245.,'mars_house_8'), # debilitated Cancer
 ('Moon',215.,65.,'moon_house_6'), # Scorpio
 ('Moon',24.,235.,'moon_house_6'), # Aries / Scorpio D9
])
def test_88_exceptions_keep_raw_detection(planet,lon,lagna,key):
    pos=POSITIONS|{planet:lon}
    raw=restriction(assess(pos,lagna=lagna),key)
    active=restriction(assess(pos,lagna=lagna,policy=MuhurtaLagnaPolicy(parihara_profile=_PAR)),key)
    assert raw.detected is active.detected is True
    assert raw.state=='detected' and active.state=='neutralized' and active.neutralized is True
    assert raw.predicates==active.predicates


def test_combustion_has_strict_declared_orb_and_unknown_sun():
    def r(sun):
        pos={'Mars':5.} if sun is None else {'Mars':5.,'Sun':sun}
        return restriction(assess(pos,lagna=155.,policy=MuhurtaLagnaPolicy(parihara_profile=_PAR)),'mars_house_8')
    assert r(21.999).neutralized is True
    assert r(22.).neutralized is False
    assert r(None).neutralized is None and r(None).state=='exception_unavailable'


def test_partial_missing_values_never_become_clear():
    r=assess({},lagna=None)
    assert r.placement_score.total is None and not r.placement_score.possible_bands
    assert all(x.satisfied is None for x in r.rules)
    assert all(x.detected is None for x in r.restrictions)
    assert 'missing_lagna' in r.unavailable_reasons and 'shadbala_not_supplied' in r.unavailable_reasons


def test_shadbala_remains_inspectable_and_cannot_cancel():
    s=strength()
    r=assess(shadbala_result=s)
    without=assess()
    assert r.rules==without.rules and r.restrictions==without.restrictions and r.placement_score==without.placement_score
    assert r.shadbala[0].sthana_bala==s.planets['Sun'].sthana_bala
    s.planets.clear()
    assert len(r.shadbala)==7
    with pytest.raises(FrozenInstanceError):r.shadbala[0].total_rupas=10


@pytest.mark.parametrize('mutation',['epoch','ayanamsa','missing','threshold','nan','total','sub','sufficiency','key'])
def test_invalid_strength_receipts_rejected(mutation):
    s=strength();p=s.planets['Sun']
    if mutation=='epoch':s=replace(s,jd=s.jd+1)
    elif mutation=='ayanamsa':s=replace(s,ayanamsa_system='Raman')
    elif mutation=='missing':s.planets.pop('Moon')
    elif mutation=='key':s.planets['Moon']=p
    else:
        updates={'threshold':{'required_rupas':1.},'nan':{'dig_bala':float('nan')},
                 'total':{'total_shashtiamsas':500.},'sub':{'sthana_bala':replace(p.sthana_bala,total=0)},
                 'sufficiency':{'is_sufficient':not p.is_sufficient}}[mutation]
        s.planets['Sun']=replace(p,**updates)
    with pytest.raises(ValueError):assess(shadbala_result=s)


@pytest.mark.parametrize('value',[True,'12',-1,360,float('nan'),float('inf')])
def test_invalid_longitudes_rejected(value):
    with pytest.raises((ValueError,TypeError)):assess({'Moon':value})
    with pytest.raises((ValueError,TypeError)):assess(lagna=value)


def test_78_friendship_is_directional_and_nature_explicit():
    r=assess(POSITIONS|{'Moon':185.,'Mercury':65.,'Sun':5.},lagna=8.)
    # Gemini Navamsa lord Mercury has Moon as enemy, though Moon likes Mercury.
    moon=next(x for x in by_rule(r,'lagna_support_78').prerequisites if x.name=='Moon')
    assert moon.satisfied is False and 'friend_from=Mercury' in moon.evidence
    assert next(p for p in r.planets if p.planet=='Mercury').benefic is False # joined Mars
    assert 'strength_policy' in muhurta_lagna_catalogue()


def test_d9_consumers_agree_at_exact_angle():
    from moira.avasthas import _navamsa_sign
    from moira.shadbala import sthana_bala
    assert navamsa(10.).sign=='Cancer' and _navamsa_sign(10.)==3
    # Sun: odd Aries D1 + even Cancer D9 -> only the D1 15-shashtiamsa share.
    from tests.unit.test_shadbala import _MockHouses
    assert sthana_bala('Sun',10.,_MockHouses(),2451545.).ojayugma==15

def test_near_antipodal_nodes_cannot_claim_two_favorable_houses():
    with pytest.raises(ValueError,match='antipodal'):
        assess(POSITIONS|{'Rahu':60.,'Ketu':nextafter(240.,0.)})

@pytest.mark.parametrize('planet',list(SOURCE['relationships']))
def test_bphs_complete_directional_friendship_table(planet):
    from moira.vedic_dignities import NATURAL_FRIENDS, NATURAL_ENEMIES, NATURAL_NEUTRALS
    for actual,expected in zip((NATURAL_FRIENDS,NATURAL_ENEMIES,NATURAL_NEUTRALS),SOURCE['relationships'][planet]):
        assert actual[planet]==set(expected)


def test_venus_moon_source_correction_flows_into_dignity_and_exception():
    from moira.vedic_dignities import vedic_dignity, planetary_relationships
    assert vedic_dignity('Venus',95.).dignity_rank=='enemy_sign'
    relations=planetary_relationships(POSITIONS)
    forward=next(r for r in relations if r.from_planet=='Venus' and r.to_planet=='Moon')
    reverse=next(r for r in relations if r.from_planet=='Moon' and r.to_planet=='Venus')
    assert forward.natural=='enemy' and reverse.natural=='neutral'
    r=assess(POSITIONS|{'Venus':95.},lagna=305.,policy=MuhurtaLagnaPolicy(parihara_profile=_PAR))
    assert restriction(r,'venus_house_6').neutralized is True

def test_mercury_missing_known_benefics_cannot_create_malefic_association():
    pos={'Sun':5.,'Moon':65.,'Mars':95.,'Mercury':125.,'Saturn':185.,'Rahu':245.,'Ketu':65.}
    r=assess(pos)
    assert next(p for p in r.planets if p.planet=='Mercury').benefic is True


@pytest.mark.parametrize('moon,benefic',[(0.,False),(1e-12,True),(180.,True),(nextafter(180.,inf),False),(359.,False)])
def test_nature_phase_endpoints(moon,benefic):
    r=assess({'Sun':0.,'Moon':moon})
    assert next(p for p in r.planets if p.planet=='Moon').benefic is benefic


def test_source_aspect_quarters_all_planets_and_distances():
    from moira.muhurta_lagna import _SEVEN
    for p in _SEVEN:
        for distance in range(1,13):
            expected={3:1,10:1,5:2,9:2,4:3,8:3,7:4}.get(distance,0)
            if (p=='Saturn' and distance in (3,10)) or (p=='Jupiter' and distance in (5,9)) or (p=='Mars' and distance in (4,8)):
                expected=4
            assert _aspect(p,0,distance-1)*4==expected


def test_support_77_requires_both_own_or_both_cross_aspects():
    # Aries D1, Gemini D9: Mars and Mercury are respective lords.
    yes=assess({'Mars':185.,'Mercury':245.},lagna=8.)
    no=assess({'Mars':35.,'Mercury':245.},lagna=8.)
    assert by_rule(yes,'lagna_support_77').satisfied is True
    assert by_rule(no,'lagna_support_77').satisfied is False
    # 76 occupancy can pass while 77, which only mentions aspect, does not.
    occupied=assess({'Mars':5.,'Mercury':65.},lagna=8.)
    assert by_rule(occupied,'lagna_support_76').satisfied is True
    assert by_rule(occupied,'lagna_support_77').satisfied is False

@pytest.mark.parametrize('planet,house',[
 ('Saturn',12),('Mars',10),('Venus',3),('Moon',1),('Sun',1),('Mars',1),('Saturn',1),('Rahu',1),('Ketu',1),
 ('Mars',6),('Venus',6),('Moon',6),('Moon',8),('Mars',8),('Venus',8),('Jupiter',8),
 *[(p,7) for p in POSITIONS],('Moon',12),
])
def test_86_and_88_fixed_role_prohibitions(planet,house):
    pos=POSITIONS|{planet:(house-1)*30+5.}
    if planet=='Rahu':pos['Ketu']=(pos['Rahu']+180)%360
    if planet=='Ketu':pos['Rahu']=(pos['Ketu']+180)%360
    r=restriction(assess(pos),f'{planet.lower()}_house_{house}')
    assert r.detected is True and r.state=='detected' and r.neutralized is False


def test_consistent_but_negative_strength_components_rejected():
    s=strength();p=s.planets['Sun'];k=replace(p.kala_bala,nathonnatha=-1.,paksha=91.)
    s.planets['Sun']=replace(p,kala_bala=k)
    with pytest.raises(ValueError,match='nonnegative'):assess(shadbala_result=s)

@pytest.mark.parametrize('sign',range(12))
def test_derived_opposite_node_preserves_opposite_sign_at_float_edges(sign):
    from moira.muhurta_lagna_dated import _opposite_node
    for x in (nextafter(sign*30.,-inf),sign*30.,nextafter(sign*30.,inf)):
        if not 0<=x<360:continue
        opposite=_opposite_node(x)
        assert int(opposite//30)==(int(x//30)+6)%12
        assert abs(x-opposite)==pytest.approx(180.,abs=1e-12)
        assess({'Rahu':x,'Ketu':opposite})

@pytest.mark.parametrize('kind',['missing','coverage','identity'])
def test_dated_composer_maps_resource_errors_and_restores_context(monkeypatch,kind):
    from datetime import datetime, timezone
    import moira.muhurta_lagna_dated as dated
    from moira.spk_reader import MissingKernelError, OutOfRangeError, get_active_reader
    from moira.gochara_dated import GocharaResourceError
    from moira.muhurta_search import MuhurtaResourceError, MuhurtaCoverageError
    error={'missing':MissingKernelError('missing'), 'coverage':OutOfRangeError('outside', (2451545.,)),
           'identity':GocharaResourceError('identity')}[kind]
    def fail(*args,**kwargs):raise error
    monkeypatch.setattr(dated,'_epoch',fail)
    before=get_active_reader()
    expected=MuhurtaCoverageError if kind=='coverage' else MuhurtaResourceError
    with pytest.raises(expected):dated.muhurta_lagna_for_datetime(datetime(2026,1,1,tzinfo=timezone.utc),0.,0.,reader=object())
    assert get_active_reader() is before
