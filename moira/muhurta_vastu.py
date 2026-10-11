"""MC Maniprabha residential commencement and entry elections.

Object: the declared foundation/entry anchor, not a building design or a
booking's whole duration. Source-specific conditions are retained separately;
explicit contextual exceptions never erase their original astronomical facts.
"""
from dataclasses import dataclass, field, asdict

from . import _muhurta_vastu_sources as S
from .muhurta_election import (
    ElectionParticipant, ElectionException,
    _admit_evidence, _assessment, _finding, _measure, _member, _not, _house,
    _sign, _and, _or, _classical_nature,
)
from .muhurta_marriage import _choice
from .panchanga_shuddhi import _number, _sector
from ._muhurta_marriage_rules import star28
from ._muhurta_marriage_sources import SEVEN
from .lunar_month import LunarMonthSystem

_RULES = {r.rule_id.removeprefix('vastu.'): r for r in S.RULES}


@dataclass(frozen=True, slots=True)
class VastuElectionPolicy:
    """Selected edition, finite residential action and disclosed compositions."""
    purpose: str
    profile: str = S.PROFILE
    ayanamsa_system: str = 'Lahiri'
    month_system: LunarMonthSystem = LunarMonthSystem.PURNIMANTA
    solver_tolerance_seconds: float = .1
    family: str = field(init=False, default='vastu')
    foundation_calendar: str = field(init=False, default='mc48_12_15_solar_facing')
    entry_calendar: str = field(init=False, default='mc48_purnimanta_entry_composition.v1')
    star28_profile: str = field(init=False, default='unequal_abhijit_276d40m_to280d53m20s.v1')
    nature_profile: str = field(init=False, default='bphs_phase_same_sign_seven_classical_composition.v1')
    house_profile: str = field(init=False, default='whole_sign_sidereal')
    availability_profile: str = field(init=False, default='ss_ix_apparent_diurnal_arc_no_marriage_buffers.v1')
    facing_star_profile: str = field(init=False, default='mc48_13_1_conjunctive_11_36_door_stars.v1')
    godhuli: bool = field(init=False, default=False)

    def __post_init__(self):
        _choice('purpose', self.purpose, S.PURPOSES)
        _choice('profile', self.profile, (S.PROFILE,))
        _choice('ayanamsa_system', self.ayanamsa_system, ('Lahiri',))
        if self.month_system is not LunarMonthSystem.PURNIMANTA:
            raise ValueError('MC48 entry composition requires the declared Purnimanta month convention')
        if not .01 <= _number('solver_tolerance_seconds', self.solver_tolerance_seconds) <= 1:
            raise ValueError('solver_tolerance_seconds must lie in [.01,1]')


@dataclass(frozen=True, slots=True)
class VastuElectionContext:
    """Declared dwelling direction/action facts and optional named resident."""
    facing: str
    excavation_corner: str | None = None
    extraordinary_reason: str | None = None
    participant: ElectionParticipant | None = None
    family: str = field(init=False, default='vastu')
    facing_basis: str = field(init=False, default='declared_true_cardinal_front_door_direction')

    def __post_init__(self):
        _choice('facing', self.facing, S.DIRECTIONS)
        if self.excavation_corner is not None:
            _choice('excavation_corner', self.excavation_corner, S.CORNERS)
        if self.extraordinary_reason is not None:
            _choice('extraordinary_reason', self.extraordinary_reason,
                    ('fire', 'flood', 'illness', 'authority_displacement'))
        if self.participant is not None and not isinstance(self.participant, ElectionParticipant):
            raise ValueError('participant must be ElectionParticipant')


def _admit_context(policy, context):
    if not isinstance(policy, VastuElectionPolicy) or not isinstance(context, VastuElectionContext):
        raise ValueError('typed Vastu policy and context are required')
    if (policy.purpose == 'extraordinary_entry') != (context.extraordinary_reason is not None):
        raise ValueError('extraordinary_entry requires its explicit reason, which is forbidden for other purposes')
    if policy.purpose != 'foundation' and context.excavation_corner is not None:
        raise ValueError('excavation_corner belongs only to foundation commencement')
    if policy.purpose == 'foundation' and context.participant is not None:
        raise ValueError('resident natal assessment belongs to the selected entry profiles, not foundation')


def _ordinal(sun, moon, size):
    if sun is None or moon is None:
        return None
    a, b = (star28(x)[0] for x in (sun, moon)) if size == 28 else (_sector(x, 27) for x in (sun, moon))
    return (b - a) % size + 1


def _asta_available(planet, evidence):
    """SS adjacent-role geometry with no wedding-only waiting periods."""
    context = getattr(evidence, planet.lower() + '_apparition')
    if context is None:
        return None
    a, b = context.previous_event, context.next_event
    if any(x.boundary.lower_jd_ut1 <= evidence.jd_ut1 <= x.boundary.upper_jd_ut1 for x in (a, b)):
        return None
    return a.role == 'appearance'


def _entry_exception(key, rule, satisfied, context, *values):
    return ElectionException(key, (rule.rule_id,), satisfied,
        (_measure('declared_reason', context.extraordinary_reason, 'context'), *values),
        'MC48 13.2 and Maniprabha return/old-house commentary, PDF359-360')


def _placement_findings(contract, positions, lagna, *, entry):
    nature = _classical_nature(positions)
    for planet in SEVEN:
        house, benefic = _house(positions.get(planet), lagna), nature[planet]
        permitted = None if benefic is None else (
            ((1, 2, 3, 4, 5, 7, 9, 10, 11) if entry else tuple(i for i in range(1, 13) if i not in (8, 12)))
            if benefic else (3, 6, 11))
        passes = None if house is None or permitted is None else house in permitted
        yield _finding(contract, passes, suffix=planet, measures=(
            _measure('planet', planet, 'body'), _measure('house', house, 'one_based_house'),
            _measure('benefic', benefic)))
        if entry:
            yield _finding(contract, None if house is None else house not in (4, 8),
                suffix=planet + '_fourth_eighth_empty', measures=(_measure('house', house, 'one_based_house'),))


def assess_vastu_election(evidence, *, policy, context):
    """Assess exactly the selected residential anchor from conditional evidence."""
    _admit_context(policy, context)
    _admit_evidence(evidence, policy, context)
    p = {x.planet: x.sidereal_longitude for x in evidence.planets}
    sun, moon, lagna = p.get('Sun'), p.get('Moon'), evidence.lagna_sidereal_longitude
    sun_sign, lagna_sign = _sign(sun), _sign(lagna)
    tithi = None if sun is None or moon is None else _sector((moon - sun) % 360, 30)
    fortnight_tithi = None if tithi is None else tithi % 15 + 1
    star = None if moon is None else _sector(moon, 27)
    weekday = None if evidence.solar is None else evidence.solar.weekday
    findings, personal = [], []

    if policy.purpose == 'foundation':
        ordinal = _ordinal(sun, moon, 28)
        findings.append(_finding(_RULES['foundation_vrisha'], _member(ordinal, range(8, 19)),
            measures=(_measure('inclusive_count', ordinal, 'one_based_28_star_count'),)))
        findings.append(_finding(_RULES['foundation_sun_facing'],
            _member(sun_sign, dict(S.FOUNDATION_SUN)[context.facing]),
            measures=(_measure('sun_sign', sun_sign, 'zero_based_sign'), _measure('facing', context.facing, 'direction'))))
        findings.append(_finding(_RULES['foundation_facing_tithi'],
            _not(_member(tithi, dict(S.FOUNDATION_FORBIDDEN_TITHIS)[context.facing])),
            measures=(_measure('tithi', tithi, 'zero_based_absolute_tithi'),)))
        for suffix, passes, value, unit in (
            ('weekday', _not(_member(weekday, (0, 2))), weekday, 'sunrise_weekday_Sunday0'),
            ('tithi', _and((_not(_member(fortnight_tithi, (1, 4, 8, 9, 14))), _not(_member(tithi, (29,))))), tithi, 'zero_based_absolute_tithi'),
            ('star', _not(_member(star, range(22, 27))), star, 'zero_based_star27'),
            ('lagna', _not(_member(lagna_sign, (0, 3, 6, 9))), lagna_sign, 'zero_based_sign'),
        ):
            findings.append(_finding(_RULES['foundation_panchanga'], passes, suffix=suffix,
                measures=(_measure(suffix, value, unit),)))
        findings.extend(_placement_findings(_RULES['foundation_placements'], p, lagna, entry=False))
        corner = None if sun_sign is None else S.EXCAVATION_CORNERS[sun_sign]
        matches = None if corner is None or context.excavation_corner is None else corner == context.excavation_corner
        findings.append(_finding(_RULES['excavation_corner'], matches,
            measures=(_measure('recommended_corner', corner, 'symbolic_excavation_direction'),
                      _measure('declared_corner', context.excavation_corner, 'actual_action_direction'))))
    else:
        addition = policy.purpose in ('old_house_entry', 'extraordinary_entry')
        returning = policy.purpose == 'return_entry'
        relaxed = addition or returning
        month = evidence.lunar_month
        month_index = None if (month is None or month.status != 'available' or month.label is None
                               or month.label.qualifier != 'ordinary') else month.label.index
        ordinary_month = _member(month_index, S.ENTRY_MONTHS)
        northward = _member(sun_sign, (9, 10, 11, 0, 1, 2))
        calendar_pass = _and((ordinary_month, northward))
        calendar_rule = _RULES['entry_calendar']
        calendar_exception = _entry_exception('mc48_13_2_entry_calendar', calendar_rule,
            returning or (addition and month_index in S.EXTRA_ENTRY_MONTHS), context,
            _measure('month', month_index, 'zero_based_month'), _measure('purpose', policy.purpose, 'action'))
        findings.append(_finding(calendar_rule, calendar_pass,
            applicable=not returning, exceptions=(calendar_exception,) if relaxed else (),
            measures=(_measure('month', month_index, 'zero_based_month'), _measure('sidereal_uttarayana', northward))))

        moon28 = None if moon is None else star28(moon)[0]
        # MC11.36: four consecutive groups of seven, beginning Krittika in E.
        door = None if moon28 is None else S.DIRECTIONS[((moon28 - 2) % 28) // 7]
        facing_ok = None if door is None else door == context.facing
        star_pass = _and((_member(star, S.ENTRY_STARS27), facing_ok))
        star_rule = _RULES['entry_star']
        extra_star = _and((_member(star, S.EXTRA_ENTRY_STARS27), facing_ok)) if addition else False
        exceptions = (_entry_exception('mc48_13_2_entry_stars', star_rule, extra_star, context,
                         _measure('extra_star_and_facing', extra_star)),) if addition else ()
        findings.append(_finding(star_rule, star_pass, exceptions=exceptions,
            measures=(_measure('star27', star, 'zero_based_star27'), _measure('star28', moon28, 'zero_based_star28'),
                      _measure('star_direction', door, 'direction'), _measure('facing_matches', facing_ok))))

        native = context.participant
        upachaya = None if native is None else _or((
            _member(_house(lagna, native.natal_moon_sidereal_longitude), (3, 6, 10, 11)),
            _member(_house(lagna, native.natal_lagna_sidereal_longitude), (3, 6, 10, 11))))
        lagna_ok = _and((_not(_member(lagna_sign, (0, 3, 6, 9))),
                         _or((_member(lagna_sign, (1, 4, 7, 10)), upachaya))))
        findings.append(_finding(_RULES['entry_lagna'], lagna_ok,
            measures=(_measure('lagna_sign', lagna_sign, 'zero_based_sign'), _measure('natal_upachaya', upachaya))))
        for suffix, passes, value, unit in (
            ('weekday', _not(_member(weekday, (0, 2))), weekday, 'sunrise_weekday_Sunday0'),
            ('tithi', _and((_not(_member(fortnight_tithi, (4, 9, 14))), _not(_member(tithi, (29,))))), tithi, 'zero_based_absolute_tithi'),
        ):
            findings.append(_finding(_RULES['entry_panchanga'], passes, suffix=suffix,
                measures=(_measure(suffix, value, unit),)))
        findings.extend(_placement_findings(_RULES['entry_placements'], p, lagna, entry=True))
        sun_house = _house(sun, lagna)
        findings.append(_finding(_RULES['entry_vama_ravi'], _member(sun_house, dict(S.VAMA_RAVI)[context.facing]),
            measures=(_measure('sun_house', sun_house, 'one_based_house'),)))
        findings.append(_finding(_RULES['entry_facing_tithi'],
            _member(fortnight_tithi, dict(S.ENTRY_FACING_TITHIS)[context.facing]),
            measures=(_measure('fortnight_tithi', fortnight_tithi, 'one_based_paksha_tithi'),)))
        ordinal = _ordinal(sun, moon, 27)
        findings.append(_finding(_RULES['entry_kalasha'], _member(ordinal, (*range(6, 14), *range(22, 28))),
            measures=(_measure('inclusive_count', ordinal, 'one_based_27_star_count'),)))
        for planet in ('Jupiter', 'Venus'):
            available = _asta_available(planet, evidence)
            contract = _RULES['entry_availability']
            rid = contract.rule_id + '.' + planet
            exceptions = (ElectionException('mc48_13_2_no_asta_requirement', (rid,), True,
                (_measure('purpose', policy.purpose, 'action'), _measure('declared_reason', context.extraordinary_reason, 'context')),
                'MC48 13.2 and Maniprabha commentary'),) if relaxed else ()
            findings.append(_finding(contract, available, suffix=planet, applicable=not relaxed,
                exceptions=exceptions, measures=(_measure('planet', planet, 'body'), _measure('available_without_wedding_buffers', available))))
        if native is not None:
            contract = _RULES['personal_entry']
            for name, origin in (('moon', native.natal_moon_sidereal_longitude), ('lagna', native.natal_lagna_sidereal_longitude)):
                house = _house(lagna, origin)
                personal.append(_finding(contract, _not(_member(house, (8,))), suffix=name + '_eighth',
                    measures=(_measure('election_lagna_from_natal_' + name, house, 'one_based_house'),)))
            count = _house(moon, native.natal_moon_sidereal_longitude)
            personal.append(_finding(contract, _not(_member(count, (2, 5, 6, 8, 9, 12))), suffix='bhakuta',
                measures=(_measure('election_moon_from_natal_moon', count, 'one_based_house'),
                          _measure('interpretation', 'resident_Moon_relative_2_12_5_9_6_8_without_compatibility_remedies.v1', 'profile'))))
    return _assessment('vastu', policy, context, evidence, findings, personal, S.MANIFEST_SHA256, S.EXCLUSIONS)


def vastu_election_catalogue():
    """Discover the selected finite profile and its exact source/coverage contract."""
    from ._muhurta_marriage_search import MarriageSearchLimits, SEARCH_HARD_MAXIMA
    return dict(family='vastu', profiles=(S.PROFILE,), purposes=S.PURPOSES,
        source_url=S.MC48_URL, source_pdf_sha256=S.MC48_SHA256,
        source_manifest_sha256=S.MANIFEST_SHA256, rules=S.RULES, exclusions=S.EXCLUSIONS,
        directions=S.DIRECTIONS, excavation_corners=S.CORNERS,
        default_limits=asdict(MarriageSearchLimits()), hard_maxima=dict(SEARCH_HARD_MAXIMA),
        input_basis='direct evidence is conditional; dated/windows require serving-reader numerical admission')


def vastu_election_for_datetime(dt, latitude, longitude, *, timezone, policy, context, limits=None, reader=None):
    """Build source-required evidence for a declared residential anchor."""
    from ._muhurta_election_dated import election_for_datetime
    return election_for_datetime('vastu', dt, latitude, longitude, timezone=timezone,
        policy=policy, context=context, limits=limits, reader=reader)


def vastu_election_windows(start, end, latitude, longitude, *, timezone, policy, context, limits=None, reader=None):
    """Bounded cells separated at every admitted residential-rule transition."""
    from ._muhurta_election_dated import election_windows
    return election_windows('vastu', start, end, latitude, longitude, timezone=timezone,
        policy=policy, context=context, limits=limits, reader=reader)


__all__ = ['VastuElectionPolicy', 'VastuElectionContext', 'assess_vastu_election',
           'vastu_election_catalogue', 'vastu_election_for_datetime', 'vastu_election_windows']
