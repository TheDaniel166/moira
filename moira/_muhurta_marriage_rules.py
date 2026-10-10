"""Pure MC marriage predicates; source ownership and three-valued logic.

No ephemeris calls, resource discovery, HTTP models or aggregate score live here.
All restrictions survive in the result even when a named remedy is applied.
"""
from dataclasses import replace
from fractions import Fraction

from . import _muhurta_marriage_sources as S
from .muhurta_marriage import MarriageFinding, MarriageMeasure, MarriageException
from .panchanga_shuddhi import (_sector, _affine, ShuddhiInterval,
                               panchanga_shuddhi_from_longitudes, PanchangaShuddhiPolicy)
from .muhurta_lagna import (_and, _or, _nature, _aspect, _LORDS,
                            MuhurtaLagnaPolicy, evaluate_muhurta_lagna_strength)
from .muhurta_dosha import detect_muhurta_doshas, MuhurtaDoshaPolicy
from .muhurta_marriage_visibility import marriage_planet_availability
from .vedic_dignities import DEBILITATION_SIGN, EXALTATION_SIGN, OWN_SIGNS, NATURAL_ENEMIES
from .avasthas import _is_combust
from .varga import varga_sign_index
from ._muhurta_marriage_manifest import TARGETS68,TARGETS89,TARGETS_BROAD

_DEFINITIONS = {r.rule_id: r for r in S.RULES}
_ABHIJIT_START = Fraction(830, 3)
_ABHIJIT_END = Fraction(2528, 9)


def star28(longitude):
    """Unequal Abhijit insertion; ordinary physical padas elsewhere remain intact."""
    if longitude is None:
        return None, None
    x = Fraction.from_float(float(longitude))
    if _ABHIJIT_START <= x < _ABHIJIT_END:
        return 21, int((x - _ABHIJIT_START) * 4 // (_ABHIJIT_END - _ABHIJIT_START)) + 1
    ordinary = _sector(longitude, 27)
    return ordinary + (ordinary >= 21), _sector(longitude, 108) % 4 + 1


def measure(name, value, unit='predicate'):
    return MarriageMeasure(name, value, unit)


def finding(family, detected, *, suffix='', applicable=True, values=(), reasons=(), exceptions=(), advisory=False):
    row = _DEFINITIONS[family]
    rid = family + ('.' + suffix if suffix else '')
    if applicable is not False and not advisory and detected is None and not reasons:
        reasons = ('required_evidence_missing_or_boundary_uncertain',)
    return MarriageFinding(rid, family, row.locus, applicable, detected,
                           tuple(values), tuple(exceptions), tuple(reasons), advisory)


def exception(name, rid, satisfied, *values, source=None):
    return MarriageException(name, (rid,), satisfied, tuple(values),
                             source or 'MC Avasthi 2004, ' + name)


def _nnot(value):
    return None if value is None else not value


def _in(value, values):
    return None if value is None else value in values


def _eq(a, b):
    return None if a is None or b is None else a == b


def _sign(x):
    return None if x is None else _sector(x, 12)


def _house(x, reference):
    return None if x is None or reference is None else (_sign(x) - _sign(reference)) % 12 + 1


def _aspect_to(p, positions, target):
    return _aspect(p, _sign(positions.get(p)), _sign(target))


def _daytime(e):
    if e.solar is None:
        return None
    return ShuddhiInterval(e.solar.day.start, e.solar.sunset).contains(e.jd_ut1)


def _discrete(e, policy, positions, nature):
    sun, moon = positions.get('Sun'), positions.get('Moon')
    nak = None if moon is None else _sector(moon, 27)
    moon_pada = None if moon is None else _sector(moon, 108) % 4 + 1
    sun_nak = None if sun is None else _sector(sun, 27)
    sun_pada = None if sun is None else _sector(sun, 108) % 4 + 1
    phase = None if sun is None or moon is None else (moon-sun) % 360
    tithi = None if phase is None else _sector(phase, 30)
    karana = None if phase is None else _sector(phase, 60)
    yoga = None if sun is None or moon is None else _sector((sun+moon) % 360, 27)
    weekday = None if e.solar is None else e.solar.weekday
    yield finding('wedding_star', _nnot(_in(nak, S.WEDDING_STARS)), values=(measure('star_index', nak, 'zero_based_27'),))
    yield finding('wedding_tithi', _nnot(_in(tithi, S.ALLOWED_TITHI_INDICES)), values=(measure('tithi_index', tithi, 'zero_based_absolute_30'),))
    yield finding('wedding_weekday', _nnot(_in(weekday, S.WEEKDAYS)), values=(measure('weekday', weekday, 'Sunday=0_sunrise_owned'),))
    yield finding('wedding_karana', _in(karana, (7,14,21,28,35,42,49,56)), values=(measure('half_tithi_index', karana, 'zero_based_60'),))
    target, target_pada = star28(moon)
    for family, pairs in (('five_line_vedha', S.FIVE_LINE_PAIRS), ('seven_line_vedha', S.SEVEN_LINE_PAIRS)):
        pair = dict(pairs + tuple((b, a) for a, b in pairs))
        for p in S.NINE:
            if p == 'Moon':
                continue
            cause, cause_pada = star28(positions.get(p))
            star_hit = None if target is None or cause is None else pair.get(cause) == target
            pada_hit = None if target_pada is None or cause_pada is None else target_pada == 5 - cause_pada
            qualification = pada_hit if family == 'five_line_vedha' else _or((_nnot(nature[p]), pada_hit))
            yield finding(family, _and((star_hit, qualification)), suffix=p.lower(), values=(
                measure('causal_star', cause, 'zero_based_28'), measure('target_star', target, 'zero_based_28'),
                measure('causal_pada', cause_pada, 'one_based_4'), measure('target_pada', target_pada, 'one_based_4'),
                measure('causal_benefic', nature[p])))
    for p, count, direction in S.LATTA:
        cause = None if p not in positions else _sector(positions[p], 27)
        pada = None if p not in positions else _sector(positions[p], 108) % 4 + 1
        hit = None if cause is None or nak is None else (cause + direction * (count-1)) % 27 == nak
        full = nature['Moon'] if p == 'Moon' else True
        yield finding('latta', _and((hit, _eq(pada, moon_pada), full)), suffix=p.lower(),
            applicable=policy.regional_tradition == 'saurashtra_shalva', values=(
                measure('causal_star', cause, 'zero_based_27'), measure('inclusive_count', count, 'stars'),
                measure('zodiac_direction', direction, 'sign'), measure('same_pada', _eq(pada, moon_pada)),
                measure('full_or_benefic_moon', full)))
    relation = None if sun is None or moon is None else any({_sign(sun), _sign(moon)} == {a,b} for a,b in S.KRANTISAMYA)
    yield finding('krantisamya', relation, values=(measure('sun_sign', _sign(sun), 'zero_based_12'), measure('moon_sign', _sign(moon), 'zero_based_12')))
    sun28, _ = star28(sun)
    count28 = None if sun28 is None or target is None else (target-sun28) % 28 + 1
    yield finding('ekargala', _and((_in(yoga, S.EKARGALA_YOGAS), None if count28 is None else count28 % 2 == 1)), values=(
        measure('yoga_index', yoga, 'zero_based_27'), measure('sun_to_moon_count', count28, 'inclusive_28')))
    count27 = None if sun_nak is None or nak is None else (nak-sun_nak) % 27 + 1
    yield finding('upagraha', _and((_in(count27, S.UPAGRAHA_COUNTS), _eq(sun_pada, moon_pada))),
        applicable=policy.regional_tradition == 'kuru_bahlika', values=(
            measure('sun_to_moon_count', count27, 'inclusive_27'), measure('same_pada', _eq(sun_pada, moon_pada))))
    dagdha = None if sun is None or tithi is None else tithi % 15 + 1 == S.DAGDHA[_sign(sun)]
    yield finding('dagdha', dagdha, values=(measure('paksha_tithi', None if tithi is None else tithi % 15 + 1, 'one_based_15'),))
    residue = None if sun_nak is None or nak is None else (sun_nak + nak + 2) % 27
    bad = _in(residue, S.DASHAYOGA_REMAINDERS)
    empty = support = opposite = None
    if residue is not None and bad and target is not None:
        start27 = 14 + (residue+1)//2 - 1
        start28 = start27 + (start27 >= 21)
        opposite = (2 * start28 + 1 - target) % 28
        empty = _nnot(_or(None if p not in positions else star28(positions[p])[0] == opposite for p in S.NINE))
    if e.lagna_sidereal_longitude is not None:
        support = _or(_or((_eq(_sign(positions.get(p)), _sign(e.lagna_sidereal_longitude)),
                          None if (a := _aspect_to(p, positions, e.lagna_sidereal_longitude)) is None else a > 0)) for p in ('Jupiter', 'Venus'))
    exc = exception('mc71_empty_opposition_or_benefic_lagna', 'dashayoga', _or((empty, support)),
                    measure('opposite_star_empty', empty), measure('Venus_or_Jupiter_support', support), source='MC Vivaha 71 and attributed Vyasa remedy')
    yield finding('dashayoga', bad, values=(measure('remainder', residue, 'modulo_27'), measure('opposite_star', opposite, 'zero_based_28')),
                  exceptions=(exc,) if bad is not False else ())
    # Elapsed tithis = zero-based absolute tithi, Lagna count = one-based sign.
    lagna_sign = _sign(e.lagna_sidereal_longitude)
    remainder = None if tithi is None or lagna_sign is None else (tithi + lagna_sign + 1) % 9
    yield finding('southern_bana', None if remainder is None else remainder in dict(S.SOUTHERN_BANA),
        applicable=policy.regional_tradition == 'dakshinatya', values=(measure('remainder', remainder, 'modulo_9'),
            measure('category', None if remainder is None else dict(S.SOUTHERN_BANA).get(remainder, 'none'), 'name')))
    degree = None if sun is None else int(Fraction.from_float(float(sun)) % 30)
    daytime = _daytime(e)
    for offset, category in S.SOLAR_BANA:
        r = None if degree is None else (degree + offset) % 9
        time_scope = True if category in ('fire', 'death') else daytime if category == 'royal' else _nnot(daytime)
        week_scope = None if weekday is None else weekday in {'royal': (6,), 'death': (3,), 'fire': (2,), 'theft': (2,), 'illness': (0,)}[category]
        yield finding('solar_bana', _eq(r, 5), suffix=category, applicable=_or((time_scope, week_scope)), values=(
            measure('sun_completed_sign_degrees', degree, 'degrees'), measure('remainder', r, 'modulo_9'),
            measure('time_or_marriage_scope', time_scope), measure('weekday_scope', week_scope)))


def _solar(e):
    if e.solar is None:
        yield finding('day_eighth', None)
        yield finding('kulika', None)
        yield finding('durmuhurta', None)
        return
    solar, jd = e.solar, e.jd_ut1
    daylight = ShuddhiInterval(solar.day.start, solar.sunset)
    night = ShuddhiInterval(solar.sunset, solar.day.end)
    for side, parent, table in (('day', daylight, S.DURMUHURTA_DAY), ('night', night, S.DURMUHURTA_NIGHT)):
        windows = tuple(ShuddhiInterval(_affine(parent, Fraction(n-1,15), 'durmuhurta_start'),
                                       _affine(parent, Fraction(n,15), 'durmuhurta_end')) for n in table[solar.weekday])
        yield finding('durmuhurta', _or(w.contains(jd) for w in windows), suffix=side,
            values=tuple(measure(f'window_{i}_{name}_{edge}', getattr(bound,edge+'_jd_ut1'),'JD_UT1')
                         for i,w in enumerate(windows) for name,bound in (('start',w.start),('end',w.end))
                         for edge in ('lower','upper')))
    for family, parent, ordinal, divisions, suffix in (
        ('day_eighth', daylight, S.DAY_EIGHTHS[solar.weekday], 8, ''),
        ('kulika', daylight, S.KULIKA_DAY[solar.weekday], 15, 'day'),
        ('kulika', night, S.KULIKA_NIGHT[solar.weekday], 15, 'night'),
        ('kulika', night, 15, 15, 'saturday_last'),
    ):
        window = ShuddhiInterval(_affine(parent, Fraction(ordinal-1, divisions), family+'_start'),
                                 _affine(parent, Fraction(ordinal, divisions), family+'_end'))
        yield finding(family, window.contains(jd), suffix=suffix,
            applicable=solar.weekday == 6 if suffix == 'saturday_last' else True,
            values=(measure('ordinal', ordinal, 'one_based_parent_division'),
                    measure('window_start_lower', window.start.lower_jd_ut1, 'JD_UT1'),
                    measure('window_start_upper', window.start.upper_jd_ut1, 'JD_UT1'),
                    measure('window_end_lower', window.end.lower_jd_ut1, 'JD_UT1'),
                    measure('window_end_upper', window.end.upper_jd_ut1, 'JD_UT1')))


def _foundations(e, policy, positions):
    if not {'Sun', 'Moon'} <= positions.keys():
        for family in ('nitya_yoga','vishanadi','yamaghanta_yoga','yamaghanta_kala',
                       'nakshatra_gandanta','tithi_gandanta','lagna_gandanta'):
            yield finding(family, None)
        return
    weekday = None if e.solar is None else e.solar.weekday
    tithi_span = next((s.interval for s in e.phase_spans if s.kind == 'tithi' and s.interval.contains(e.jd_ut1) is not False), None)
    shuddhi = panchanga_shuddhi_from_longitudes(positions['Sun'], positions['Moon'],
        jd_ut1=e.jd_ut1, weekday=weekday, lagna_sidereal_longitude=e.lagna_sidereal_longitude,
        is_daytime=_daytime(e), yoga_span=e.yoga_span, tithi_span=tithi_span, karana_span=e.karana_span,
        policy=PanchangaShuddhiPolicy(tara_profile='mc_gochara_13_quarters.v1',
            ayanamsa_system=policy.ayanamsa_system,solver_tolerance_seconds=policy.solver_tolerance_seconds))
    yoga = next(f for f in shuddhi.findings if f.rule_id == 'nitya_yoga')
    yield finding('nitya_yoga', yoga.detected,
        reasons=yoga.reasons if yoga.detected is None else (),
        values=(measure('component_profile', yoga.profile, 'source_profile'),
                measure('yoga_index', shuddhi.values.yoga_index, 'zero_based_27'))+
            tuple(measure(f'window_{i}_{side}_{edge}',getattr(bound,edge+'_jd_ut1'),'JD_UT1')
                  for i,w in enumerate(yoga.windows) for side,bound in (('start',w.start),('end',w.end))
                  for edge in ('lower','upper')))
    doshas = detect_muhurta_doshas(positions['Sun'], positions['Moon'], jd_ut1=e.jd_ut1,
        weekday=weekday, lagna_sidereal_longitude=e.lagna_sidereal_longitude,
        phase_spans=e.phase_spans, sunrise_day=None if e.solar is None else e.solar.day,
        sunset=None if e.solar is None else e.solar.sunset,
        policy=MuhurtaDoshaPolicy(vishanadi_profile='mc_vivaha_49_51.v1',
                                 vishanadi_clock='mc_avasthi_scaled_start_fixed_width.v1',
                                 gandanta_profile='mc_vivaha_43_fixed_ghati.v1',parihara_profiles=(),
                                 ayanamsa_system=policy.ayanamsa_system,
                                 solver_tolerance_seconds=policy.solver_tolerance_seconds))
    for f in doshas.findings:
        values = [measure('component_profile', f.profile, 'source_profile')]
        for i, w in enumerate(f.witnesses):
            values.append(measure(f'witness_{i}_detected', w.detected))
            window = w.unclipped_window or w.window
            if window is not None:
                for label, bound in (('start', window.start), ('end', window.end)):
                    values.extend((measure(f'witness_{i}_{label}_lower', bound.lower_jd_ut1, 'JD_UT1'),
                                   measure(f'witness_{i}_{label}_upper', bound.upper_jd_ut1, 'JD_UT1')))
        yield finding(f.rule_id, f.detected, values=values, reasons=f.unavailable_reasons)


def _lagna(e, policy, positions, nature):
    lagna, moon = e.lagna_sidereal_longitude, positions.get('Moon')
    active = MuhurtaLagnaPolicy(navamsa_profile=policy.navamsa_profile,
        parihara_profile='mc_vivaha_88_natural_avasthas_orb.v1' if 'mc88_weak_afflictors' in policy.remedies else None,
        ayanamsa_system=policy.ayanamsa_system)
    component = evaluate_muhurta_lagna_strength(positions, jd_ut1=e.jd_ut1,
        lagna_sidereal_longitude=lagna, policy=active)
    for r in component.rules:
        if '_support_' in r.rule_id:
            continue
        yield finding('lagna_components', _nnot(r.satisfied), suffix=r.rule_id,
            values=tuple(measure(p.name, p.satisfied) for p in r.prerequisites))
    for side in ('lagna', 'seventh'):
        alternatives = [r for r in component.rules if r.rule_id.startswith(side+'_support_')]
        support = _or(r.satisfied for r in alternatives)
        yield finding('lagna_components', _nnot(support), suffix=side+'_support',
            values=tuple(measure(r.rule_id, r.satisfied) for r in alternatives))
    for r in component.restrictions:
        rid = 'lagna_components.' + r.rule_id
        exc = ()
        if r.parihara_profile and r.detected is not False:
            exc = (exception('mc88_weak_afflictors', rid, _or(p.satisfied for p in r.exception_predicates),
                *(measure(p.name, p.satisfied) for p in r.exception_predicates), source=r.citation),)
        yield finding('lagna_components', r.detected, suffix=r.rule_id,
            values=tuple(measure(p.name, p.satisfied) for p in r.predicates), exceptions=exc)
    total=None if component.placement_score is None else component.placement_score.total
    yield finding('lagna_components', None if total is None else total<5, suffix='placement_score_below_five',
        values=(measure('score',total,'MC87_92_vimshopaka'),measure('exclusive_prohibition_cutoff',5,'source_points')))
    yield finding('lagna_components', False, suffix='placement_score_context', advisory=True,
        values=(measure('score',total,'MC87_92_vimshopaka'),)+tuple(
            measure('quality_band_'+str(i),band,'source_inclusive_band') for i,band in enumerate(
                () if component.placement_score is None else component.placement_score.possible_bands)))
    for reference, value in (('lagna', lagna), ('moon', moon)):
        for p in S.NINE:
            house = _house(positions.get(p), value)
            delta = None if value is None or p not in positions else (_sector(positions[p],108)-_sector(value,108)) % 108
            yield finding('jamitra', _or((_eq(house,7), _eq(delta,54))), suffix=reference+'.'+p.lower(),
                values=(measure('relative_house', house, 'inclusive_12'), measure('navamsa_delta', delta, 'zero_based_108')))
    daytime = _daytime(e)
    for defect in ('blind','deaf','lame'):
        indices = None if daytime is None else dict(S.DAY_DEFECTS if daytime else S.NIGHT_DEFECTS)[defect]
        bad = None if indices is None or lagna is None else _sign(lagna) in indices
        exc = ()
        if 'mc83_lagna_aspect' in policy.remedies and bad is not False:
            lord = None if lagna is None else _LORDS[_sign(lagna)]
            aspects = [(p, None if p is None else _aspect_to(p, positions, lagna)) for p in (lord,'Jupiter')]
            satisfied = _or(None if a is None else a > 0 for _,a in aspects)
            exc = (exception('mc83_lagna_aspect', 'lagna_day_night.'+defect, satisfied,
                             *(measure(str(p)+'_aspect',a,'quarter_sign_strength') for p,a in aspects), source='MC Vivaha 83'),)
        yield finding('lagna_day_night', bad, suffix=defect,
            values=(measure('is_daytime',daytime), measure('lagna_sign',_sign(lagna),'zero_based_12')), exceptions=exc)
    speeds = {p.planet:p.longitude_speed for p in e.planets}
    for reference, value in (('lagna',lagna),('moon',moon)):
        candidates = []
        for left in S.NINE:
            for right in S.NINE:
                if left == right:
                    continue
                lhouse, rhouse = _house(positions.get(left),value), _house(positions.get(right),value)
                direct = None if speeds.get(left) is None else speeds[left] > 0
                retrograde = None if speeds.get(right) is None else speeds[right] < 0
                hit = _and((_eq(lhouse,12),_eq(rhouse,2),_nnot(nature[left]),_nnot(nature[right]),direct,retrograde))
                if hit is False:
                    continue
                candidates.append(hit)
                exc = ()
                if 'mc88_weak_afflictors' in policy.remedies:
                    weakness = []
                    for p in (left,right):
                        sign = _sign(positions.get(p))
                        deb = None if sign is None else sign == DEBILITATION_SIGN.get(p)
                        enemy = None if sign is None else _LORDS[sign] in NATURAL_ENEMIES.get(p, ())
                        combust = None if p not in positions or 'Sun' not in positions else _is_combust(p,positions) if p in S.SEVEN and p != 'Sun' else False
                        weakness.append(_or((deb,enemy,combust)))
                    rid = f'kartari.{reference}.{left.lower()}.{right.lower()}'
                    exc = (exception('mc88_weak_afflictors',rid,_and(weakness),measure('left_weak',weakness[0]),measure('right_weak',weakness[1]),source='MC Vivaha 44/88'),)
                yield finding('kartari',hit,suffix=f'{reference}.{left.lower()}.{right.lower()}',
                    values=(measure('left_house',lhouse,'inclusive_12'),measure('right_house',rhouse,'inclusive_12'),
                            measure('left_direct',direct),measure('right_retrograde',retrograde)),exceptions=exc)
        if not candidates:
            yield finding('kartari',False,suffix=reference+'.clear')


def _remedies(findings, e, policy, positions):
    """Finite target sets; broad source rhetoric does not change this manifest."""
    lagna, moon = e.lagna_sidereal_longitude, positions.get('Moon')
    own_luminaries = _and(None if p not in positions else _sign(positions[p]) in (*OWN_SIGNS[p], EXALTATION_SIGN[p]) for p in ('Sun','Moon'))
    def central(p):
        return _in(_house(positions.get(p), lagna), (1,4,5,9,10))
    benefic = _or(central(p) for p in ('Mercury','Jupiter','Venus'))
    def vargottama(x):
        return None if x is None else _sign(x) == varga_sign_index(x,9)
    broad90 = _or((central('Jupiter'), _eq(_house(positions.get('Sun'),lagna),11), vargottama(lagna), vargottama(moon)))
    lords = () if lagna is None else (_LORDS[_sign(lagna)],_LORDS[varga_sign_index(lagna,9)])
    broad91 = None if not lords else _or(_in(_house(positions.get(p),lagna),(1,4,10,11)) for p in lords)
    witnesses = {
        'mc68_own_or_exalted_luminaries': tuple(measure(p+'_own_or_exalted', None if p not in positions else _sign(positions[p]) in (*OWN_SIGNS[p], EXALTATION_SIGN[p])) for p in ('Sun','Moon')),
        'mc89_benefic_kendra_trikona': tuple(measure(p+'_house', _house(positions.get(p),lagna), 'inclusive_12') for p in ('Mercury','Jupiter','Venus')),
        'mc90_anvaya_disjunction': (measure('Jupiter_kendra_trikona', central('Jupiter')), measure('Sun_eleventh', _eq(_house(positions.get('Sun'),lagna),11)), measure('lagna_vargottama', vargottama(lagna)), measure('Moon_vargottama', vargottama(moon))),
        'mc91_lagna_lords_placement': tuple(measure(side+'_lord', p, 'planet') for side,p in zip(('lagna','navamsa'),lords)) + tuple(measure(side+'_lord_house', _house(positions.get(p),lagna), 'inclusive_12') for side,p in zip(('lagna','navamsa'),lords)),
        'mc90_moon_eleventh': (measure('Moon_house', _house(moon,lagna), 'inclusive_12'),
            measure('lagna_navamsa_lord',None if lagna is None else _LORDS[varga_sign_index(lagna,9)],'planet'),
            measure('interpretation','mc90_avasthi_malefic_owned_lagna_navamsa','source_composition')),
    }
    # Scope of source 'all' is frozen to the astronomical restrictions in this
    # MC marriage composition. Never personal eligibility or SS availability.
    for f in findings:
        exc = list(f.exceptions)
        if f.detected is not False and f.applicable is not False and not f.advisory:
            rows = (
                ('mc68_own_or_exalted_luminaries',own_luminaries,f.family_id in TARGETS68 or f.rule_id in ('lagna_components.lagna_support','lagna_components.seventh_support'),'MC Vivaha 68; finite own/exaltation subset'),
                ('mc89_benefic_kendra_trikona',benefic,f.family_id in TARGETS89,'MC Vivaha 89; finite astronomical groups'),
                ('mc90_anvaya_disjunction',broad90,f.family_id in TARGETS_BROAD,'MC Vivaha 90; printed anvaya disjunction'),
                ('mc91_lagna_lords_placement',broad91,f.family_id in TARGETS_BROAD,'MC Vivaha 91; no numeric dosha subtraction'),
                ('mc90_moon_eleventh',_eq(_house(moon,lagna),11),f.family_id == 'durmuhurta' or
                    (f.rule_id=='lagna_components.navamsa_allowed_sign' and lagna is not None and
                     _LORDS[varga_sign_index(lagna,9)] in ('Sun','Mars','Saturn')),
                    'MC Vivaha 90, Avasthi commentary: Durmuhurta and malefic-owned Lagna Navamsa'),
            )
            for name,satisfied,eligible,source in rows:
                if name in policy.remedies and eligible:
                    exc.append(exception(name,f.rule_id,satisfied,*witnesses[name],measure('qualified',satisfied),source=source))
        yield replace(f, exceptions=tuple(exc))


def evaluate(e, policy, personal):
    positions = {p.planet:p.sidereal_longitude for p in e.planets}
    nature = _nature(positions)
    from ._muhurta_marriage_context import context_findings, personal_findings, compose_godhuli
    rows = list(_discrete(e,policy,positions,nature))
    rows.extend(_solar(e))
    rows.extend(_foundations(e,policy,positions))
    rows.extend(_lagna(e,policy,positions,nature))
    for planet,capacity in (('Mercury',100),('Venus',200),('Jupiter',100000)):
        rows.append(finding('broad_remedies',False,suffix='mc91_capacity_'+planet.lower(),advisory=True,
            values=(measure('planet',planet,'planet'),measure('source_capacity',capacity,'textual_dosha_count'),
                measure('qualifying_placement',_in(_house(positions.get(planet),e.lagna_sidereal_longitude),(1,4,5,9,10))),
                measure('numeric_subtraction_admitted',False))))
    rows.extend(context_findings(e,policy,positions,nature,rows))
    for p in ('Jupiter','Venus'):
        availability = marriage_planet_availability(p,e.jd_ut1,getattr(e,p.lower()+'_apparition'))
        rows.append(finding(p.lower()+'_availability',availability.restricted,
            values=(measure('state',availability.state,'availability_state'),
                    measure('post_appearance',availability.post_appearance_days,'elapsed_UT1_days'),
                    measure('pre_disappearance',availability.pre_disappearance_days,'elapsed_UT1_days')),
            reasons=availability.unavailable_reasons))
    rows = tuple(_remedies(rows,e,policy,positions))
    personal_rows = tuple(personal_findings(e,policy,positions,personal)) if personal is not None else ()
    composition = compose_godhuli(e,policy,positions,rows) if policy.godhuli else rows
    return rows, personal_rows, tuple(composition)
