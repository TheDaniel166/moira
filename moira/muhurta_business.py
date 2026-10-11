"""MC04 buyer, seller and first-opening election profiles."""
from dataclasses import dataclass, field, asdict
from . import _muhurta_business_sources as S
from .muhurta_election import (
    ElectionAssessment, _admit_evidence, _assessment, _finding, _measure,
    _member, _not, _house, _sign, _and, _classical_nature,
)
from .muhurta_marriage import _choice
from .panchanga_shuddhi import _number, _sector
from ._muhurta_marriage_sources import SEVEN
from .lunar_month import LunarMonthSystem

_RULES = {r.rule_id.removeprefix('business.'):r for r in S.RULES}


@dataclass(frozen=True, slots=True)
class BusinessElectionPolicy:
    """Selected commercial action, source edition and explicit interpretations."""
    purpose: str
    profile: str = S.PROFILE
    ayanamsa_system: str = 'Lahiri'
    solver_tolerance_seconds: float = .1
    family: str = field(init=False,default='business')
    good_tithi_profile: str = field(init=False,default='mc04_1_4_best_with_enumerated_conflicts.v1')
    placement_profile: str = field(init=False,default='seven_classical_specific_precedes_general.v1')
    nature_profile: str = field(init=False,default='bphs_phase_same_sign_seven_classical_composition.v1')
    month_system: LunarMonthSystem = field(init=False,default=LunarMonthSystem.AMANTA)
    godhuli: bool = field(init=False,default=False)

    def __post_init__(self):
        _choice('purpose',self.purpose,S.PURPOSES)
        _choice('profile',self.profile,(S.PROFILE,))
        _choice('ayanamsa_system',self.ayanamsa_system,('Lahiri',))
        if not .01 <= _number('solver_tolerance_seconds',self.solver_tolerance_seconds) <= 1:
            raise ValueError('solver_tolerance_seconds must lie in [.01,1]')


@dataclass(frozen=True, slots=True)
class BusinessElectionContext:
    """Named actor, distinct counterparty and the act whose instant is elected."""
    actor_id: str
    actor_role: str
    anchor: str
    counterparty_id: str | None = None
    family: str = field(init=False,default='business')
    participant: None = field(init=False,default=None)

    def __post_init__(self):
        for name in ('actor_id','counterparty_id'):
            value = getattr(self,name)
            if value is None and name == 'counterparty_id':
                continue
            if type(value) is not str or not value.strip() or len(value)>120:
                raise ValueError('actor identities must be nonempty strings of at most120 characters')
        if self.actor_id == self.counterparty_id:
            raise ValueError('counterparty must be a distinct actor')
        _choice('actor_role',self.actor_role,('buyer','seller','trading_operator'))
        _choice('anchor',self.anchor,('acceptance_exchange','first_opening_for_trade'))


def _admit_context(policy,context):
    if not isinstance(policy,BusinessElectionPolicy) or not isinstance(context,BusinessElectionContext):
        raise ValueError('typed business policy/context required')
    policy.__post_init__()
    context.__post_init__()
    if context.actor_role != S.ROLE[policy.purpose]:
        raise ValueError('actor role must match the elected purpose')
    expected = 'first_opening_for_trade' if policy.purpose == 'first_opening_for_trade' else 'acceptance_exchange'
    if context.anchor != expected:
        raise ValueError('anchor does not match this source-defined action')
    if policy.purpose == 'first_opening_for_trade' and context.counterparty_id is not None:
        raise ValueError('first trade opening has an operator, not an inferred transaction counterparty')


def _sale_tithi(tithi,star,weekday):
    """Named interpretation of sat-tithi; grades remain visible separately."""
    n = None if tithi is None else tithi%15+1
    tier = None if tithi is None else ('inferior','middling','best')[tithi//5] if tithi<15 else ('best','middling','inferior')[(tithi-15)//5]
    yield 'grade', None if tier is None else tier=='best', (_measure('tier',tier,'source_grade'),)
    # Finite no-cancellation reading; the source's Siddha praise is advisory.
    for name,table in (('weekday_class',S.DEAD_CLASSES),('krakacha',S.KRAKACHA),('dagdha',S.DAGDHA),('visha',S.VISHA),('hutashana',S.HUTASHANA)):
        value = None if n is None or weekday is None else ((n-1)%5+1 != table[weekday] if name=='weekday_class' else n != table[weekday])
        yield name,value,(_measure('paksha_tithi',n,'one_based_tithi'),_measure('weekday',weekday,'Sunday0'))
    value = None if n is None or weekday is None else (weekday,n) not in ((3,1),(0,7))
    yield 'samvartaka',value,()
    value = None if n is None or star is None else star not in dict(S.TITHI_STARS).get(n,())
    yield 'tithi_star',value,(_measure('star',star,'zero_based_star27'),)
    value = None if n is None or star is None or weekday is None else (weekday,star,n) not in ((0,12,5),(2,0,7),(1,4,6))
    yield 'triple_conflict',value,()


def assess_business_election(evidence,*,policy,context):
    """Keep source actors and selection criteria separate, without averaging."""
    _admit_context(policy,context)
    _admit_evidence(evidence,policy,context)
    positions = {p.planet:p.sidereal_longitude for p in evidence.planets}
    sun,moon = positions.get('Sun'),positions.get('Moon')
    star = None if moon is None else _sector(moon,27)
    tithi = None if sun is None or moon is None else _sector((moon-sun)%360,30)
    weekday = None if evidence.solar is None else evidence.solar.weekday
    lagna = evidence.lagna_sidereal_longitude
    findings = [_finding(_RULES['selected_star'],_member(star,dict(S.STARS)[policy.purpose]),measures=(
        _measure('star',star,'zero_based_star27'),_measure('actor_role',context.actor_role,'role'),
        _measure('meaning','positive_selection_requirement_not_universal_prohibition','interpretation')))]
    if policy.purpose == 'sale':
        findings.extend(_finding(_RULES['sale_tithi'],passed,suffix=name,measures=values)
                        for name,passed,values in _sale_tithi(tithi,star,weekday))
        n = None if tithi is None else tithi%15+1
        siddha = None if weekday is None or n is None else weekday == (5,3,2,6,4)[(n-1)%5]
        findings.append(_finding(_RULES['sale_tithi'],siddha,suffix='siddha_testimony',advisory=True))
        contract = _RULES['sale_lagna']
        findings.append(_finding(contract,_not(_member(_sign(lagna),(10,))),suffix='Aquarius'))
        nature = _classical_nature(positions)
        for planet in SEVEN:
            house,benefic = _house(positions.get(planet),lagna),nature[planet]
            allowed = None if benefic is None else (1,2,4,5,7,9,10) if benefic else (3,6,11)
            findings.append(_finding(contract,None if allowed is None else _member(house,allowed),suffix=planet,
                measures=(_measure('house',house,'one_based_house'),_measure('benefic',benefic))))
    elif policy.purpose == 'first_opening_for_trade':
        contract = _RULES['vipani_panchanga']
        findings.extend((_finding(contract,None if tithi is None else tithi%15+1 not in (4,9,14),suffix='Rikta'),
            _finding(contract,_not(_member(weekday,(2,))),suffix='Tuesday'),
            _finding(contract,_not(_member(_sign(lagna),(10,))),suffix='Aquarius')))
        contract = _RULES['vipani_placements']
        houses = {p:_house(positions.get(p),lagna) for p in SEVEN}
        findings.append(_finding(contract,_and((_member(houses['Moon'],(1,)),_member(houses['Venus'],(1,)))),
            suffix='Moon_AND_Venus_lagna',measures=(_measure('Moon_house',houses['Moon'],'one_based_house'),
                                                  _measure('Venus_house',houses['Venus'],'one_based_house'))))
        nature = _classical_nature(positions)
        for planet in SEVEN:
            house,benefic = houses[planet],nature[planet]
            # Specific Lagna placement owns Moon/Venus; the no-malefic8/12
            # constraint still applies to a waning Moon without contradiction.
            passed = None if benefic is None else _not(_member(house,(8,12))) if not benefic else (
                True if planet in ('Moon','Venus') else _member(house,(2,10,11)))
            findings.append(_finding(contract,passed,suffix=planet,
                measures=(_measure('house',house,'one_based_house'),_measure('benefic',benefic))))
    return _assessment('business',policy,context,evidence,findings,(),S.MANIFEST_SHA256,S.EXCLUSIONS)


@dataclass(frozen=True, slots=True)
class BusinessElectionComparison:
    """Two unaveraged role assessments from exactly the same conditional sky."""
    buyer: ElectionAssessment
    seller: ElectionAssessment
    preferred_star_sets_disjoint: bool = field(init=False,default=True)

    def __post_init__(self):
        if not isinstance(self.buyer,ElectionAssessment) or not isinstance(self.seller,ElectionAssessment):
            raise ValueError('comparison requires canonical assessments')
        if self.buyer.policy != BusinessElectionPolicy('purchase') or self.seller.policy != BusinessElectionPolicy('sale'):
            raise ValueError('comparison requires the declared purchase/sale profiles')
        if self.buyer.evidence != self.seller.evidence or self.buyer.context.actor_id == self.seller.context.actor_id:
            raise ValueError('comparison requires one sky and distinct actors')


def compare_business_elections(evidence,*,buyer_id,seller_id):
    """One conditional sky, two named roles and both unmodified decisions."""
    return BusinessElectionComparison(
        assess_business_election(evidence,policy=BusinessElectionPolicy('purchase'),
            context=BusinessElectionContext(buyer_id,'buyer','acceptance_exchange',seller_id)),
        assess_business_election(evidence,policy=BusinessElectionPolicy('sale'),
            context=BusinessElectionContext(seller_id,'seller','acceptance_exchange',buyer_id)))


def business_election_catalogue():
    from ._muhurta_marriage_search import MarriageSearchLimits, SEARCH_HARD_MAXIMA
    return dict(family='business',profiles=(S.PROFILE,),purposes=S.PURPOSES,source_url=S.SOURCE_URL,
        source_pdf_sha256=S.SOURCE_SHA256,source_manifest_sha256=S.MANIFEST_SHA256,rules=S.RULES,exclusions=S.EXCLUSIONS,
        roles=tuple(S.ROLE.items()),anchors=('acceptance_exchange','first_opening_for_trade'),
        default_limits=asdict(MarriageSearchLimits()),hard_maxima=dict(SEARCH_HARD_MAXIMA),
        input_basis='direct evidence is conditional; dated/windows require serving-reader numerical admission')


def business_election_for_datetime(dt,latitude,longitude,*,timezone,policy,context,limits=None,reader=None):
    from ._muhurta_election_dated import election_for_datetime
    return election_for_datetime('business',dt,latitude,longitude,timezone=timezone,policy=policy,context=context,limits=limits,reader=reader)


def business_election_windows(start,end,latitude,longitude,*,timezone,policy,context,limits=None,reader=None):
    from ._muhurta_election_dated import election_windows
    return election_windows('business',start,end,latitude,longitude,timezone=timezone,policy=policy,context=context,limits=limits,reader=reader)


__all__ = ['BusinessElectionPolicy','BusinessElectionContext','BusinessElectionComparison','assess_business_election',
           'compare_business_elections','business_election_catalogue','business_election_for_datetime','business_election_windows']
