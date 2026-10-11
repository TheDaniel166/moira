"""Source-specific travel assessments with explicit component scope."""
from dataclasses import dataclass,field,asdict
from . import _muhurta_travel_sources as S
from . import _muhurta_travel_mc_sources as MC
from .muhurta_election import (
    ElectionParticipant,ElectionException,_admit_evidence,_assessment,_finding,_measure,_member,_sign,
)
from .muhurta_marriage import _choice
from .panchanga_shuddhi import _number,_integer,_sector,_shift
from .lunar_month import LunarMonthSystem

_RULES={r.rule_id:r for r in S.RULES}


@dataclass(frozen=True, slots=True)
class TravelElectionPolicy:
    """A named component never claims to be a complete travel tradition."""
    profile: str
    tithi_ordinal: str = 'month_1_to_30'
    ayanamsa_system: str = 'Lahiri'
    solver_tolerance_seconds: float = .1
    purpose: str = field(init=False,default='departure')
    family: str = field(init=False,default='travel')
    scope: str = field(init=False,default='named_component')
    ghati_clock: str = field(init=False,default='fixed_1440_elapsed_UT1_seconds')
    month_system: LunarMonthSystem = field(init=False,default=LunarMonthSystem.AMANTA)
    godhuli: bool = field(init=False,default=False)

    def __post_init__(self):
        _choice('profile',self.profile,(MC.PROFILE,*S.PROFILES))
        object.__setattr__(self,'scope','ordinary_land_departure' if self.profile==MC.PROFILE else 'named_component')
        _choice('tithi_ordinal',self.tithi_ordinal,('month_1_to_30','paksha_1_to_15'))
        _choice('ayanamsa_system',self.ayanamsa_system,('Lahiri',))
        if not .01 <= _number('solver_tolerance_seconds',self.solver_tolerance_seconds) <= 1:
            raise ValueError('solver_tolerance_seconds must lie in [.01,1]')
        if self.profile == S.KP_WEEKDAY and self.tithi_ordinal != 'month_1_to_30':
            raise ValueError('weekday-only component has no selectable tithi count')
        if self.profile == MC.PROFILE and self.tithi_ordinal != 'month_1_to_30':
            raise ValueError('MC selected composition requires its declared month1..30 count')


@dataclass(frozen=True, slots=True)
class TravelElectionContext:
    """The traveller, actual departure act, leg and declared compass direction."""
    traveller_id: str
    anchor: str
    direction: str | None = None
    leg: str = 'outbound'
    participant: ElectionParticipant | None = None
    prior_departure_jd_ut1: float | None = None
    completed_stop_nights: int | None = None
    family: str = field(init=False,default='travel')
    direction_basis: str = field(init=False,default='declared_true_cardinal_or_intercardinal')

    def __post_init__(self):
        if type(self.traveller_id) is not str or not self.traveller_id.strip() or len(self.traveller_id)>120:
            raise ValueError('traveller_id must be a nonempty label of at most120 characters')
        _choice('anchor',self.anchor,('leave_residence','cross_settlement_boundary','leave_room'))
        _choice('leg',self.leg,('outbound','return'))
        if self.direction is not None:
            _choice('direction',self.direction,S.DIRECTIONS)
        if self.participant is not None:
            if not isinstance(self.participant,ElectionParticipant) or self.participant.participant_id != self.traveller_id:
                raise ValueError('natal participant must identify this traveller')
        if self.prior_departure_jd_ut1 is not None:
            _number('prior_departure_jd_ut1',self.prior_departure_jd_ut1)
        if self.completed_stop_nights is not None:
            _integer('completed_stop_nights',self.completed_stop_nights,0,10000)
            if self.prior_departure_jd_ut1 is None:
                raise ValueError('stop context requires an earlier actual departure')


def _admit_context(policy,context):
    if not isinstance(policy,TravelElectionPolicy) or not isinstance(context,TravelElectionContext):
        raise ValueError('typed travel policy/context required')
    policy.__post_init__()
    context.__post_init__()
    if policy.profile==MC.PROFILE:
        if context.direction is None:
            raise ValueError('ordinary travel requires an explicit compass direction')
        return
    if context.prior_departure_jd_ut1 is not None or context.completed_stop_nights is not None:
        raise ValueError('KP components have no prior-departure rule')
    if context.participant is not None:
        raise ValueError('selected KP components have no natal layer')
    if policy.profile == S.KP_WEEKDAY and context.direction not in S.CARDINAL:
        raise ValueError('KP weekday component requires one of its four stated cardinal directions')


def _beyond(jd,boundary):
    if boundary.lower_jd_ut1 == boundary.upper_jd_ut1:
        return jd > boundary.jd_ut1
    return False if jd < boundary.lower_jd_ut1 else True if jd > boundary.upper_jd_ut1 else None


def _kp_findings(evidence,policy,context):
    solar=evidence.solar
    weekday=None if solar is None else solar.weekday
    if policy.profile == S.KP_WEEKDAY:
        contract=_RULES['travel.kp_weekday_direction']
        forbidden=_member(weekday,dict(S.WEEKDAYS)[context.direction])
        boundary=None if solar is None else _shift(solar.day.start,dict(S.RELEASE_GHATIS)[context.direction]*1440,'kp_weekday_release')
        released=None if boundary is None else _beyond(evidence.jd_ut1,boundary)
        values=(_measure('weekday',weekday,'Sunday0'),_measure('direction',context.direction,'direction'),
            _measure('release_ghatis',dict(S.RELEASE_GHATIS)[context.direction],'fixed_24_minute_ghatis'),
            _measure('release_lower',None if boundary is None else boundary.lower_jd_ut1,'JD_UT1'),
            _measure('release_upper',None if boundary is None else boundary.upper_jd_ut1,'JD_UT1'))
        exception=ElectionException('kp_weekday_strictly_after_sunrise_offset',(contract.rule_id,),released,
                                    (_measure('strictly_beyond',released),),contract.source)
        yield _finding(contract,None if forbidden is None else not forbidden,measures=values,exceptions=(exception,))
        return
    positions={p.planet:p.sidereal_longitude for p in evidence.planets}
    sun,moon=positions.get('Sun'),positions.get('Moon')
    star=None if moon is None else _sector(moon,27)+1
    sun_star=None if sun is None else _sector(sun,27)+1
    tithi=None if sun is None or moon is None else _sector((moon-sun)%360,30)+1
    if tithi is not None and policy.tithi_ordinal == 'paksha_1_to_15':
        tithi=(tithi-1)%15+1
    day=None if weekday is None else weekday+1
    lagna=None if evidence.lagna_sidereal_longitude is None else _sign(evidence.lagna_sidereal_longitude)+1
    contract=_RULES['travel.kp_three_moduli']
    for name,value,multiplier,divisor in (('tithi',tithi,2,6),('weekday',day,3,8),('star',star,4,6)):
        remainder=None if value is None else value*multiplier%divisor
        yield _finding(contract,None if remainder is None else remainder!=0,suffix=name,
            measures=(_measure('ordinal',value,'one_based'),_measure('multiplier',multiplier,'integer'),
                      _measure('divisor',divisor,'integer'),_measure('remainder',remainder,'integer')))
    count=None if sun_star is None or star is None else (star-sun_star)%27+1
    remainder=None if count is None else count%7
    yield _finding(_RULES['travel.kp_sun_moon_count'],_member(remainder,(1,4,5)),
        measures=(_measure('inclusive_count',count,'one_based_27_star_count'),_measure('remainder',remainder,'integer')))
    total=None if any(x is None for x in (tithi,day,star,lagna)) else tithi+day+star+lagna
    for label,shift in S.SHIFTS:
        remainder=None if total is None else (total+shift)%9
        yield _finding(_RULES['travel.kp_shifted_panchakam'],None if remainder is None else remainder!=5,suffix=label,
            measures=(_measure('sum',total,'integer'),_measure('shift',shift,'integer'),_measure('remainder',remainder,'integer'),
                      _measure('tithi_ordinal',policy.tithi_ordinal,'composition')))


def assess_travel_election(evidence,*,policy,context):
    """Retain selected source conditions; never infer physical travel safety."""
    _admit_context(policy,context)
    _admit_evidence(evidence,policy,context)
    if policy.profile==MC.PROFILE:
        from ._muhurta_travel_mc import evaluate
        findings,personal=evaluate(evidence,policy,context)
        return _assessment('travel',policy,context,evidence,findings,personal,MC.MANIFEST_SHA256,MC.EXCLUSIONS)
    findings=tuple(_kp_findings(evidence,policy,context))
    return _assessment('travel',policy,context,evidence,findings,(),S.MANIFEST_SHA256,S.EXCLUSIONS)


def travel_election_catalogue():
    from ._muhurta_marriage_search import MarriageSearchLimits,SEARCH_HARD_MAXIMA
    return dict(family='travel',profiles=(MC.PROFILE,*S.PROFILES),purposes=('departure',),source_url=MC.URL,
        source_pdf_sha256=MC.SHA256,source_manifest_sha256=MC.MANIFEST_SHA256,rules=MC.RULES+S.RULES,exclusions=MC.EXCLUSIONS+S.EXCLUSIONS,
        profile_scopes=((MC.PROFILE,'ordinary_land_departure'),)+tuple((p,'named_component') for p in S.PROFILES),directions=S.DIRECTIONS,
        profile_sources=((MC.PROFILE,MC.URL,MC.SHA256,MC.MANIFEST_SHA256),)+tuple((p,S.KP_URL,S.KP_SHA256,S.MANIFEST_SHA256) for p in S.PROFILES),
        imported_families=MC.IMPORT_FAMILIES,
        anchors=('leave_residence','cross_settlement_boundary','leave_room'),
        default_limits=asdict(MarriageSearchLimits()),hard_maxima=dict(SEARCH_HARD_MAXIMA),
        input_basis='direct evidence is conditional; dated/windows require serving-reader numerical admission')


def travel_election_for_datetime(dt,latitude,longitude,*,timezone,policy,context,limits=None,reader=None):
    from ._muhurta_election_dated import election_for_datetime
    return election_for_datetime('travel',dt,latitude,longitude,timezone=timezone,policy=policy,context=context,limits=limits,reader=reader)


def travel_election_windows(start,end,latitude,longitude,*,timezone,policy,context,limits=None,reader=None):
    from ._muhurta_election_dated import election_windows
    return election_windows('travel',start,end,latitude,longitude,timezone=timezone,policy=policy,context=context,limits=limits,reader=reader)


__all__=['TravelElectionPolicy','TravelElectionContext','assess_travel_election','travel_election_catalogue',
         'travel_election_for_datetime','travel_election_windows']
