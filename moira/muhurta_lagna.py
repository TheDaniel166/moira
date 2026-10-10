"""Source-selected Lagna composition; no complete election or universal override.

MC = Daivajna Rama, Muhurta Chintamani, Avasthi commentary, 2004.
The source packet records verse loci, competing readings and operational choices.
"""
from dataclasses import dataclass, field
from .muhurta_dosha import DoshaPredicate, _choice
from .panchanga_shuddhi import _number, _longitude
from .sidereal import list_ayanamsa_systems
from .varga import navamsa, varga_sign_index, _navamsa_partition, VargaPoint
from .vedic_dignities import NATURAL_ENEMIES, NATURAL_FRIENDS, DEBILITATION_SIGN, OWN_SIGNS
from .shadbala import (ShadbalaResult, PlanetShadbala, SthanaBala, KalaBala,
                      validate_shadbala_output)
from .avasthas import _is_combust

_SEVEN = ('Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn')
_NINE = _SEVEN + ('Rahu', 'Ketu')
_LORDS = tuple(next(p for p, signs in OWN_SIGNS.items() if s in signs) for s in range(12))
_GENERAL = 'mc_nakshatra_44.v1'
_MARRIAGE = 'mc_vivaha_75_78_84_88_92.v1'
_FOUR = 'mc_avasthi_vivaha_84_four.v1'
_FIVE = 'mc_vivaha_84_optional_pisces.v1'
_PAR = 'mc_vivaha_88_natural_avasthas_orb.v1'
_WEIGHTS = dict(zip(_NINE, (3.5, 5., 1.5, 2., 3., 2., 1.5, 1.5, 1.5)))
_GOOD = {
 'Sun': (3, 6, 8, 11), 'Moon': (2, 3, 11), 'Mars': (3, 6, 11),
 'Mercury': (1, 2, 3, 4, 5, 6, 9, 10, 11),
 'Jupiter': (1, 2, 3, 4, 5, 6, 9, 10, 11),
 'Venus': (1, 2, 4, 5, 9, 10, 11), 'Saturn': (3, 6, 8, 11),
 'Rahu': (3, 6, 8, 11), 'Ketu': (3, 6, 8, 11),
}
_EXCLUDED = ('complete_purpose_election', 'continuous_time_windows',
 'kartaridosha_and_its_exceptions', 'mc_vivaha_89_91_broad_cancellation',
 'kp_rashi_tyajya_and_unspecified_strength_remedies', 'ritual_performance',
 'automatic_cancellation_of_ved009_detectors')


@dataclass(frozen=True, slots=True)
class MuhurtaLagnaPolicy:
    """Named purpose, Navamsa variant and opt-in placement exceptions.

    Aspects use MC 75 quarters, D1 positions against D1/D9 sign labels.
    Nature uses BPHS 3.11 verse-only waxing Moon and same-sign Mercury
    association, excluding Santhanam's additional commentary exceptions.
    """
    purpose_profile: str = _MARRIAGE
    navamsa_profile: str = _FOUR
    parihara_profile: str | None = None
    ayanamsa_system: str = 'Lahiri'
    house_basis: str = field(init=False, default='whole_sign_from_sidereal_lagna')
    aspect_profile: str = field(init=False, default='mc_vivaha_75_quarter_sign_d1_projection.v1')
    relationship_profile: str = field(init=False, default='bphs_natural_directional.v1')
    nature_profile: str = field(init=False, default='bphs_3_11_verse_phase_same_sign.v1')
    shadbala_role: str = field(init=False, default='context_only_no_cancellation_threshold')

    def __post_init__(self):
        _choice('purpose_profile', self.purpose_profile, (_GENERAL, _MARRIAGE))
        _choice('navamsa_profile', self.navamsa_profile, (_FOUR, _FIVE))
        if self.parihara_profile is not None:
            _choice('parihara_profile', self.parihara_profile, (_PAR,))
            if self.purpose_profile != _MARRIAGE:
                raise ValueError('Vivaha Parihara requires the marriage purpose profile')
        _choice('ayanamsa_system', self.ayanamsa_system, tuple(list_ayanamsa_systems()))


@dataclass(frozen=True, slots=True)
class LagnaPlanet:
    """One supplied position, its canonical D9 and nullable whole-sign house/nature."""
    planet: str
    sidereal_longitude: float
    sign_index: int
    navamsa: VargaPoint
    house: int | None
    benefic: bool | None


@dataclass(frozen=True, slots=True)
class LagnaRuleEvidence:
    """An independently inspectable predicate, including unknown prerequisites."""
    rule_id: str
    satisfied: bool | None
    prerequisites: tuple[DoshaPredicate, ...]
    citation: str


@dataclass(frozen=True, slots=True)
class LagnaPlacementContribution:
    """MC 87/92 source weight awarded only in the planet's listed houses."""
    planet: str
    house: int | None
    favorable_houses: tuple[int, ...]
    weight: float
    points: float | None


@dataclass(frozen=True, slots=True)
class LagnaPlacementScore:
    """MC Lagna Vimshopaka, distinct from Varga Vimshopaka and Shadbala.

    Opposite nodes limit the attainable maximum to 20. Commentary overlaps
    at 10 and 15 are returned as multiple bands, never silently resolved.
    """
    entries: tuple[LagnaPlacementContribution, ...]
    total: float | None
    known_points: float
    possible_bands: tuple[str, ...]
    maximum: float = field(init=False, default=20.)
    citation: str = field(init=False, default='MC Avasthi 2004, Vivaha 87/92, printed 146/148')


@dataclass(frozen=True, slots=True)
class LagnaRestriction:
    """Raw placement restriction survives any selected, witnessed exception."""
    rule_id: str
    planet: str
    detected: bool | None
    state: str
    predicates: tuple[DoshaPredicate, ...]
    parihara_profile: str | None
    neutralized: bool | None
    exception_predicates: tuple[DoshaPredicate, ...]
    citation: str


@dataclass(frozen=True, slots=True)
class MuhurtaLagnaAssessment:
    """Finite source components and strength context; no overall auspicious score."""
    jd_ut1: float
    policy: MuhurtaLagnaPolicy
    lagna_sidereal_longitude: float | None
    lagna_navamsa: VargaPoint | None
    natal_moon_sidereal_longitude: float | None
    natal_lagna_sidereal_longitude: float | None
    planets: tuple[LagnaPlanet, ...]
    rules: tuple[LagnaRuleEvidence, ...]
    placement_score: LagnaPlacementScore | None
    restrictions: tuple[LagnaRestriction, ...]
    shadbala: tuple[PlanetShadbala, ...]
    unavailable_reasons: tuple[str, ...]
    excluded_rules: tuple[str, ...] = field(init=False, default=_EXCLUDED)
    activity_suitability: str = field(init=False, default='not_evaluated')
    input_basis: str = 'caller_supplied_sidereal_same_epoch'
    shadbala_result: ShadbalaResult | None = None


def _and(values):
    values = tuple(values)
    return False if False in values else None if None in values else True


def _or(values):
    values = tuple(values)
    return True if True in values else None if None in values else False


def _aspect(planet, origin, target):
    if origin is None or target is None:
        return None
    distance = (target - origin) % 12 + 1
    special = {'Mars': (4, 8), 'Jupiter': (5, 9), 'Saturn': (3, 10)}
    if distance in special.get(planet, ()):
        return 1.
    return {3: .25, 10: .25, 5: .5, 9: .5, 4: .75, 8: .75, 7: 1.}.get(distance, 0.)


def _nature(positions):
    signs = {p: int(x // 30) for p, x in positions.items()}
    phase = None if not {'Moon', 'Sun'} <= positions.keys() else (positions['Moon'] - positions['Sun']) % 360
    nature = {p: False for p in ('Sun', 'Mars', 'Saturn', 'Rahu', 'Ketu')}
    nature.update(Jupiter=True, Venus=True, Moon=None if phase is None else 0 < phase <= 180)
    if 'Mercury' not in signs:
        nature['Mercury'] = None
    else:
        joined = []
        for p in _NINE:
            if p == 'Mercury':
                continue
            joined.append(False if nature[p] is True else None if p not in signs else False if signs[p] != signs['Mercury']
                          else None if nature[p] is None else not nature[p])
        bad = _or(joined)
        nature['Mercury'] = None if bad is None else not bad
    return nature


def _strength(result, jd, policy, positions):
    if result is None:
        return ()
    if not isinstance(result, ShadbalaResult):
        raise TypeError('shadbala_result must be ShadbalaResult')
    if result.jd != jd or result.ayanamsa_system != policy.ayanamsa_system:
        raise ValueError('Shadbala epoch/ayanamsa must match the Lagna inputs exactly')
    if set(result.planets) != set(_SEVEN):
        raise ValueError('Shadbala must contain exactly the seven classical planets')
    # The owner validates typed numeric components, signed Ayana/Yuddha,
    # source receipts and all sums. Keep strict epoch/body checks above.
    for p in _SEVEN:
        ps = result.planets[p]
        if not isinstance(ps, PlanetShadbala) or not isinstance(ps.sthana_bala, SthanaBala) or not isinstance(ps.kala_bala, KalaBala):
            raise TypeError('Shadbala entries and subcomponents must be typed')
    validate_shadbala_output(result)
    if result.context is not None:
        result.context.check_positions(jd, policy.ayanamsa_system,
            {p: lon for p,lon in positions.items() if p in _SEVEN})
    return tuple(result.planets[p] for p in _SEVEN)


def _score(positions, houses):
    entries = tuple(LagnaPlacementContribution(p, houses.get(p), _GOOD[p], _WEIGHTS[p],
        None if p not in positions or houses.get(p) is None else _WEIGHTS[p] if houses[p] in _GOOD[p] else 0.) for p in _NINE)
    known = sum(e.points or 0 for e in entries)
    total = known if all(e.points is not None for e in entries) else None
    bands = () if total is None else tuple(name for name, valid in (
        ('prohibited', total < 5), ('inauspicious', 5 <= total <= 10),
        ('middling', 10 <= total <= 15), ('auspicious', 15 <= total <= 20)) if valid)
    return LagnaPlacementScore(entries, total, known, bands)


def evaluate_muhurta_lagna_strength(sidereal_longitudes: dict[str, float], *, jd_ut1: float,
        lagna_sidereal_longitude: float | None = None,
        natal_moon_sidereal_longitude: float | None = None,
        natal_lagna_sidereal_longitude: float | None = None,
        shadbala_result: ShadbalaResult | None = None,
        policy: MuhurtaLagnaPolicy | None = None) -> MuhurtaLagnaAssessment:
    """Compose explicit source predicates from a possibly incomplete snapshot.

    Longitude inputs are finite [0,360); supplied nodes must be antipodal.
    Missing data yields nullable component truth, never a favorable fallback.
    Shadbala is checked and copied into immutable per-planet context; it never
    substitutes for a text's dignity, placement or aspect prerequisite.
    """
    active = MuhurtaLagnaPolicy() if policy is None else policy
    if not isinstance(active, MuhurtaLagnaPolicy):
        raise TypeError('policy must be MuhurtaLagnaPolicy')
    jd = _number('jd_ut1', jd_ut1)
    if not isinstance(sidereal_longitudes, dict) or not set(sidereal_longitudes) <= set(_NINE):
        raise ValueError('sidereal_longitudes must map only the nine Vedic planet names')
    positions = {p: _longitude(p, x) for p, x in sidereal_longitudes.items()}
    strengths = _strength(shadbala_result, jd, active, positions)
    if shadbala_result is not None and shadbala_result.context is not None:
        # Compatibility tolerance admits the supplied chart; one canonical
        # position must govern all discrete signs, Navamsas and predicates.
        # Preserve missing bodies and supplied nodes rather than filling gaps.
        canonical = dict(shadbala_result.context.sidereal_longitudes)
        positions = {p: canonical[p] if p in _SEVEN else x for p, x in positions.items()}
    if {'Rahu', 'Ketu'} <= positions.keys():
        if (abs(abs(positions['Rahu'] - positions['Ketu']) - 180) > 1e-9
                or int(positions['Ketu']//30) != (int(positions['Rahu']//30)+6)%12):
            raise ValueError('Rahu and Ketu must be antipodal')
    optional = (lagna_sidereal_longitude, natal_moon_sidereal_longitude, natal_lagna_sidereal_longitude)
    for name, value in zip(('lagna', 'natal_moon', 'natal_lagna'), optional):
        if value is not None:
            _longitude(name, value)
    lagna = None if lagna_sidereal_longitude is None else int(lagna_sidereal_longitude // 30)
    d9 = None if lagna is None else navamsa(lagna_sidereal_longitude)
    d9sign = None if d9 is None else varga_sign_index(lagna_sidereal_longitude, 9)
    signs = {p: int(x // 30) for p, x in positions.items()}
    houses = {p: None if lagna is None else (s - lagna) % 12 + 1 for p, s in signs.items()}
    nature = _nature(positions)
    planets = tuple(LagnaPlanet(p, positions[p], signs[p], navamsa(positions[p]), houses[p], nature[p])
                    for p in _NINE if p in positions)
    reasons = tuple(f'missing_position:{p}' for p in _NINE if p not in positions)
    if lagna is None:
        reasons += ('missing_lagna',)
    if not strengths:
        reasons += ('shadbala_not_supplied',)
    rules, restrictions = [], []
    def pred(name, truth, evidence):
        return DoshaPredicate(name, truth, evidence)
    def rule(key, prerequisites, citation, any_of=False):
        rules.append(LagnaRuleEvidence(key, (_or if any_of else _and)(p.satisfied for p in prerequisites),
                                       tuple(prerequisites), citation))
    def aspect(p, target, occupancy=False):
        value = _aspect(p, signs.get(p), target)
        truth = None if value is None else value > 0 or (occupancy and signs[p] == target)
        return pred(f'{p}_to_sign_{target}', truth,
                    f'D1 sign={signs.get(p)}; target={target}; aspect_quarters={None if value is None else value*4}; occupancy_allowed={occupancy}')
    if active.purpose_profile == _GENERAL:
        for h in (8, 12):
            rule(f'general_house_{h}_empty', [pred(p, None if lagna is None or p not in houses else houses[p] != h,
                 f'house={houses.get(p)}') for p in _NINE], 'MC Nakshatra 44, printed 46')
        references = [pred(name, None if lagna is None or x is None else (lagna-int(x//30))%12+1 in (3,6,10,11),
                           f'natal_longitude={x}; election_sign={lagna}') for name, x in zip(('natal_moon', 'natal_lagna'), optional[1:])]
        rule('general_natal_upachaya', references, 'MC Nakshatra 44, printed 46', True)
        if all(x is None for x in optional[1:]):
            reasons += ('missing_natal_reference',)
        support = []
        for p in _SEVEN:
            a = aspect(p, lagna, True)
            support.append(pred(p, _and((nature[p], a.satisfied)), f'benefic={nature[p]}; {a.evidence}'))
        rule('general_benefic_support', support, 'MC Nakshatra 44; BPHS 3.11; MC Vivaha 75', True)
        rule('general_moon_upachaya', [pred('Moon', None if houses.get('Moon') is None else houses['Moon'] in (3,6,10,11),
             f'house={houses.get("Moon")}')], 'MC Nakshatra 44, printed 46')
    else:
        allowed = (2, 5, 6, 8) + ((11,) if active.navamsa_profile == _FIVE else ())
        rule('navamsa_allowed_sign', [pred('allowed_sign', None if d9sign is None else d9sign in allowed,
             f'sign={d9sign}; allowed={allowed}')], 'MC Vivaha 84, printed 145')
        segment = None if lagna is None else _navamsa_partition(lagna_sidereal_longitude)[1] % 9
        rule('navamsa_last_except_vargottama', [pred('last_segment', None if segment is None else segment != 8 or d9sign == lagna,
             f'zero_based_segment={segment}; vargottama={None if lagna is None else d9sign == lagna}')], 'MC Vivaha 85, printed 145')
        forbidden = _and((None if lagna is None else lagna in (0,3,6,9),
                          None if d9sign is None else d9sign in (0,3,6,9),
                          None if 'Moon' not in signs else signs['Moon'] in (6,9)))
        rule('navamsa_movable_moon_exception', [pred('avoid_combination', None if forbidden is None else not forbidden,
             f'lagna={lagna}; navamsa={d9sign}; Moon={signs.get("Moon")}')], 'MC Vivaha 85, printed 145')
        for side, delta in (('lagna', 0), ('seventh', 6)):
            targets = tuple(None if s is None else (s+delta)%12 for s in (lagna, d9sign))
            if lagna is None:
                for verse in (76, 77, 78):
                    rule(f'{side}_support_{verse}', [pred('lagna', None, 'Lagna absent')], f'MC Vivaha {verse}')
                continue
            lord, d9lord = (_LORDS[s] for s in targets)
            rule(f'{side}_support_76', [aspect(d9lord, target, True) for target in targets], 'MC Vivaha 75-76, printed 140-142', True)
            pairs = []
            for name, pair in (('own', ((lord, targets[0]), (d9lord, targets[1]))),
                               ('cross', ((lord, targets[1]), (d9lord, targets[0])))):
                aps = [aspect(p,t) for p,t in pair]
                pairs.append(pred(name, _and(a.satisfied for a in aps), '; '.join(a.evidence for a in aps)))
            rule(f'{side}_support_77', pairs, 'MC Vivaha 75/77, printed 140-142', True)
            friends = []
            for p in _SEVEN:
                aps = [aspect(p, t) for t in targets]
                friends.append(pred(p, _and((p in NATURAL_FRIENDS[d9lord], nature[p], _or(a.satisfied for a in aps))),
                    f'friend_from={d9lord}; benefic={nature[p]}; ' + '; '.join(a.evidence for a in aps)))
            rule(f'{side}_support_78', friends, 'MC Vivaha 78, printed 142-143; BPHS natural friendship', True)
        # Every explicit placement prohibition in 86; Moon 12 added by 88.
        for p in _NINE:
            for h in range(1,13):
                causes = []
                if (p,h) in (('Saturn',12),('Mars',10),('Venus',3),('Moon',1),('Venus',6),('Moon',6),('Moon',8),('Mars',8),('Moon',12)) or h == 7:
                    causes.append(True)
                if h == 1:
                    causes.append(None if nature[p] is None else not nature[p])
                if h in (6,8):
                    causes.append(None if lagna is None else p == _LORDS[lagna])
                if h == 8:
                    causes.append(nature[p])
                if not causes or _or(causes) is False:
                    continue
                at_house = None if houses.get(p) is None else houses[p] == h
                detected = _and((at_house, _or(causes)))
                exc = []
                eligible = (p,h) in (('Venus',6),('Mars',8),('Moon',6),('Moon',8),('Moon',12))
                if eligible:
                    deb = None if p not in signs else signs[p] == DEBILITATION_SIGN[p]
                    exc.append(pred('debilitated_sign', deb, f'sign={signs.get(p)}; required={DEBILITATION_SIGN[p]}'))
                    if p == 'Moon':
                        nd = None if p not in positions else varga_sign_index(positions[p],9)
                        exc.append(pred('debilitated_navamsa', None if nd is None else nd == DEBILITATION_SIGN[p], f'navamsa={nd}'))
                    else:
                        exc.append(pred('natural_enemy_sign', None if p not in signs else _LORDS[signs[p]] in NATURAL_ENEMIES[p],
                                        f'from={p}; sign_lord={None if p not in signs else _LORDS[signs[p]]}'))
                        if p == 'Mars':
                            combust = None if not {'Sun','Mars'} <= positions.keys() else _is_combust('Mars', positions)
                            exc.append(pred('combust', combust, 'moira.avasthas fixed Mars orb: shortest elongation <17 degrees; declared numerical policy'))
                neutralized = _and((detected, _or(x.satisfied for x in exc))) if eligible and active.parihara_profile else False
                state = ('clear' if detected is False else 'unavailable' if detected is None else
                         'neutralized' if neutralized is True else 'exception_unavailable' if neutralized is None else 'detected')
                restrictions.append(LagnaRestriction(f'{p.lower()}_house_{h}', p, detected, state,
                    (pred('in_house',at_house,f'actual={houses.get(p)}; prohibited={h}'),
                     pred('prohibited_role',_or(causes),f'benefic={nature[p]}; lagna_lord={None if lagna is None else _LORDS[lagna]}')),
                    active.parihara_profile if eligible else None, neutralized, tuple(exc), 'MC Vivaha 86/88, printed 145-147'))
    return MuhurtaLagnaAssessment(jd, active, lagna_sidereal_longitude, d9,
        natal_moon_sidereal_longitude, natal_lagna_sidereal_longitude, planets, tuple(rules),
        _score(positions,houses) if active.purpose_profile == _MARRIAGE else None,
        tuple(restrictions), strengths, reasons, shadbala_result=shadbala_result)


def muhurta_lagna_catalogue() -> dict:
    """Discover the admitted profiles, source loci and explicit product boundary."""
    return {'purpose_profiles': (_GENERAL, _MARRIAGE), 'navamsa_profiles': (_FOUR, _FIVE),
            'parihara_profiles': (_PAR,), 'source': 'MC Avasthi 2004, printed 46, 140-148; BPHS Santhanam I 3.11',
            'excluded_rules': _EXCLUDED, 'score_maximum': 20., 'grade_boundary_policy': 'retain_both_at_10_and_15',
            'relationship_direction': 'Navamsa lord toward potential benefic friend',
            'nature_boundary_policy': '0 < Moon-Sun elongation <= 180 is waxing; Mercury association is same-sign',
            'strength_policy': 'canonical Shadbala context; no automatic cancellation'}


__all__ = ['MuhurtaLagnaPolicy', 'LagnaPlanet', 'LagnaRuleEvidence', 'LagnaPlacementContribution',
 'LagnaPlacementScore', 'LagnaRestriction', 'MuhurtaLagnaAssessment',
 'evaluate_muhurta_lagna_strength', 'muhurta_lagna_catalogue']
