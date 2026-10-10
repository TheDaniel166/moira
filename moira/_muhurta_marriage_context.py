"""Calendar, history, personal context and Godhuli composition for marriage."""
from dataclasses import replace
from math import floor

from . import _muhurta_marriage_sources as S
from ._muhurta_marriage_rules import (finding, measure, exception, _eq, _in, _nnot,
                                     _sign, _house, _and, _or,star28)
from .muhurta_lagna import _nature
from .muhurta_marriage import MarriageTimeSpan
from .panchanga_shuddhi import _sector, ShuddhiInterval, panchanga_shuddhi_from_longitudes,PanchangaShuddhiPolicy
from .muhurta_dosha import _shift
from ._muhurta_marriage_manifest import GODHULI_TARGETS


def _calendar(e, policy, positions):
    sun = positions.get('Sun')
    month = e.lunar_month
    allowed = _in(_sign(sun), S.SOLAR_MARRIAGE_SIGNS)
    yield finding('calendar', _nnot(allowed), suffix='solar_sign', values=(measure('solar_sign', _sign(sun), 'zero_based_12'),))
    if month is None or month.label is None:
        yield finding('calendar', None, suffix='lunar_month', reasons=('canonical_lunar_month_required',) if month is None else month.unavailable_reasons)
        return
    label = month.label
    yield finding('calendar', label.qualifier != 'ordinary', suffix='intercalation',
        values=(measure('month_qualifier',label.qualifier,'calendar_status'),))
    # Vivaha 13 lunar qualification is supplied by the edition-owned table.
    allowed_month = _in(_sign(sun), S.MARRIAGE_MONTH_SIGNS[label.index])
    if label.index == 3:  # Ashadha is the explicit Gemini/early-Shukla exception.
        allowed_month = _and((_eq(_sign(sun),2), month.paksha == 'Shukla', month.tithi_number <= 10))
    yield finding('calendar', _nnot(allowed_month), suffix='lunar_month', values=(
        measure('month_index',label.index,'Chaitra=0'), measure('paksha',month.paksha,'name'),
        measure('paksha_tithi',month.tithi_number,'one_based_15'),
        measure('month_system',policy.month_system.value,'calendar_system')))


def _ingresses(e):
    history = e.ingress_history
    jd = e.jd_ut1
    for p, width in S.INGRESS_TOTAL_GHATIS:
        pad = width / 120  # total ghatis / 2 / 60 = elapsed UT1 days per side
        complete = history is not None and p in history.planets and history.extent.start_jd_ut1 <= jd-pad and history.extent.end_jd_ut1 >= jd+pad
        hits = []
        values = [measure('total_width',width,'ghati_1440_seconds')]
        for i,event in enumerate(() if history is None else history.events):
            if event.planet != p:
                continue
            window = MarriageTimeSpan(_shift(event.boundary,-pad,'ingress_start'),_shift(event.boundary,pad,'ingress_end'))
            hits.append(window.contains(jd))
            values.extend((measure(f'ingress_{i}_jd_lower',event.boundary.lower_jd_ut1,'JD_UT1'),
                           measure(f'ingress_{i}_jd_upper',event.boundary.upper_jd_ut1,'JD_UT1'),
                           measure(f'ingress_{i}_direction',event.direction,'sign')))
        result = _or((*hits, False if complete else None))
        yield finding('planetary_ingress',result,suffix=p.lower(),values=values,
            reasons=() if complete else ('full_buffer_search_extent_required',))
    complete = history is not None and 'Sun' in history.planets and history.extent.start_jd_ut1 <= jd-3 and history.extent.end_jd_ut1 >= jd+3
    hits = []
    for event in (() if history is None else history.events):
        if event.planet != 'Sun':
            continue
        if event.entered_sign in (0,3,6,9):
            hits.append(None if event.cardinal_solar_days is None else event.cardinal_solar_days.contains(jd))
        else:
            window = MarriageTimeSpan(_shift(event.boundary,-16/60,'solar_ingress_start'),_shift(event.boundary,16/60,'solar_ingress_end'))
            hits.append(window.contains(jd))
    yield finding('solar_ingress',_or((*hits,False if complete else None)),
        reasons=() if complete else ('solar_ingress_three_date_context_required',))


def _history(e, positions, nature, prior_findings):
    history, jd = e.star_history, e.jd_ut1
    moon = positions.get('Moon')
    target = None if moon is None else _sector(moon,27)
    for planet in S.NINE:
        if planet == 'Moon':
            continue
        if planet in ('Jupiter','Venus'):
            yield finding('star_history',False,suffix=planet.lower(),applicable=False,
                          values=(measure('causal_benefic',True),))
            continue
        if history is None or planet not in history.planets or 'Moon' not in history.planets:
            yield finding('star_history',None,suffix=planet.lower(),reasons=('nearest_planet_passages_and_Moon_clearance_required',))
            continue
        passages = [p for p in history.passages if p.planet == planet]
        before = [p for p in passages if p.exit.upper_jd_ut1 <= jd]
        current = [p for p in passages if p.entry.lower_jd_ut1 <= jd <= p.exit.upper_jd_ut1]
        after = [p for p in passages if p.entry.lower_jd_ut1 > jd]
        selected = (before[-1:] + current + after[:1])
        complete = bool(before and current and after and
                        all(a.exit==b.entry for a,b in zip(selected,selected[1:])))
        hits = []
        values = []
        for i, passage in enumerate(selected):
            match = _eq(passage.star_index,target)
            trigger = passage.exit if passage.exit.upper_jd_ut1 <= jd else passage.entry
            active = passage.entry.upper_jd_ut1 <= jd < passage.exit.lower_jd_ut1
            cleared = any(p.planet == 'Moon' and p.star_index == passage.star_index
                          and p.entry.lower_jd_ut1 > trigger.upper_jd_ut1 and p.exit.upper_jd_ut1 <= jd
                          for p in history.passages)
            if planet=='Mercury':
                causal=_mercury_occupancy(history,passage,jd) if match is not False else False
                hits.append(_and((match,causal)))
            else:
                hits.append(_and((match,_nnot(nature[planet]),not cleared or active)))
            values.extend((measure(f'passage_{i}_star',passage.star_index,'zero_based_27'),
                           measure(f'passage_{i}_trigger',trigger.jd_ut1,'JD_UT1'),
                           measure(f'passage_{i}_completed_Moon_clearance',cleared)))
        yield finding('star_history',_or((*hits,False if complete else None)),suffix=planet.lower(),values=values,
            reasons=() if complete else ('nearest_previous_current_next_passage_missing',))
    yield from _historical_vedha(e,positions)


def _arc_samples(lower,upper,targets):
    """Represent every partition state in a closed unwrapped angular box."""
    edges=[lower,upper]
    for turn in range(floor(lower/360)-1,floor(upper/360)+2):
        edges.extend(t+turn*360 for t in targets if lower<t+turn*360<upper)
    edges=sorted(set(edges))
    return tuple(x%360 for x in (*edges,*((a+b)/2 for a,b in zip(edges,edges[1:]))))


def _band_possibilities(band):
    """Raw interval ranges may overestimate correlation, never understate it."""
    from ._muhurta_marriage_history import PADA_TARGETS
    if band is None:
        return {},{},True
    samples={p.planet:_arc_samples(p.lower_degrees,p.upper_degrees,PADA_TARGETS)
             for p in band.longitudes}
    signs={p:{_sign(x) for x in values} for p,values in samples.items()}
    phases=() if band.phase_bounds is None else _arc_samples(*band.phase_bounds,(0.,180.))
    moon_malefic=not phases or any(not 0<x<=180 for x in phases)
    return samples,signs,moon_malefic


def _possibly_malefic(body,signs,moon_malefic):
    if body in ('Jupiter','Venus'):
        return False
    if body=='Moon':
        return moon_malefic
    if body!='Mercury':
        return True
    mercury=signs.get('Mercury',set(range(12)))
    return any(mercury & signs.get(p,set(range(12))) for p in ('Sun','Mars','Saturn','Rahu','Ketu')) or (
        moon_malefic and bool(mercury & signs.get('Moon',set(range(12)))))


def _history_bands(history):
    by_boundary={b.boundary:b for b in history.transition_bands}
    for span in history.vedha_spans[:-1]:
        edge=span.interval.end
        if edge.lower_jd_ut1<edge.upper_jd_ut1:
            yield edge,by_boundary.get(edge)


def _mercury_occupancy(history,passage,jd):
    """Event-time association, including the explicitly selected next passage."""
    spans=history.vedha_spans
    future=passage.entry.lower_jd_ut1>jd
    end=passage.exit.upper_jd_ut1 if future else min(jd,passage.exit.upper_jd_ut1)
    moons=tuple(p for p in history.passages if p.planet=='Moon' and p.star_index==passage.star_index
                and p.exit.upper_jd_ut1<=jd)
    start=passage.entry.lower_jd_ut1
    if not future and moons:
        start=max(start,moons[-1].entry.lower_jd_ut1)
    if start>=end:
        return False
    complete=bool(spans and spans[0].interval.start.upper_jd_ut1<=start
                  and spans[-1].interval.end.lower_jd_ut1>=end)
    hits=[]
    for span in spans:
        a,b=span.interval.start,span.interval.end
        if b.upper_jd_ut1<=start or a.lower_jd_ut1>=end:
            continue
        if any(p.entry.lower_jd_ut1>b.upper_jd_ut1 for p in moons):
            continue
        sky={p.planet:p.sidereal_longitude for p in span.planets}
        bad=_and((_eq(None if 'Mercury' not in sky else _sector(sky['Mercury'],27),passage.star_index),
                  _nnot(_nature(sky)['Mercury'])))
        certain=max(a.upper_jd_ut1,start)<min(b.lower_jd_ut1,end)
        possible_clear=any(p.entry.upper_jd_ut1>b.lower_jd_ut1 for p in moons)
        hits.append(_and((bad,True if certain and not possible_clear else None)))
    for edge,band in _history_bands(history):
        if edge.upper_jd_ut1<=start or edge.lower_jd_ut1>=end:
            continue
        if any(p.entry.lower_jd_ut1>edge.upper_jd_ut1 for p in moons):
            continue
        samples,signs,moon_bad=_band_possibilities(band)
        possible='Mercury' not in samples or any(_sector(x,27)==passage.star_index for x in samples['Mercury'])
        if possible and _possibly_malefic('Mercury',signs,moon_bad):
            hits.append(None)
    return _or((*hits,False if complete else None))


def _historical_vedha(e,positions):
    """Persist event-time malefic piercing until a complete Moon28 traversal."""
    history,jd=e.star_history,e.jd_ut1
    target,pada=star28(positions.get('Moon'))
    passages=() if history is None else tuple(p for p in history.moon28_passages if p.star_index==target)
    completed=tuple(p for p in passages if p.exit.upper_jd_ut1<=jd)
    spans=() if history is None else history.vedha_spans
    complete=bool(completed and spans and spans[0].interval.start.upper_jd_ut1<=completed[-1].entry.lower_jd_ut1
                  and spans[-1].interval.end.lower_jd_ut1>=jd)
    for family,pairs in (('five_line',S.FIVE_LINE_PAIRS),('seven_line',S.SEVEN_LINE_PAIRS)):
        mapping=dict(pairs+tuple((b,a) for a,b in pairs))
        hits=[]
        values=[]
        for index,span in enumerate(spans):
            if span.interval.start.lower_jd_ut1>=jd:
                continue
            # The last completed target-star lunar traversal proves that any
            # contamination ending before its entry has already been cleared.
            end=span.interval.end
            cleared=any(p.entry.lower_jd_ut1>end.upper_jd_ut1 and p.exit.upper_jd_ut1<=jd for p in passages)
            if cleared:
                continue
            sky={p.planet:p.sidereal_longitude for p in span.planets}
            historical_nature=_nature(sky)
            for body in S.NINE:
                causal,causal_pada=star28(sky.get(body))
                match=None if causal is None or target is None else mapping.get(causal)==target
                qualification=True if family=='seven_line' else _eq(pada,None if causal_pada is None else 5-causal_pada)
                hit=_and((match,qualification,_nnot(historical_nature[body])))
                if hit is not False:
                    timing=None if span.interval.start.upper_jd_ut1>=jd else True
                    possible_clear=any(p.entry.upper_jd_ut1>end.lower_jd_ut1 and p.exit.lower_jd_ut1<=jd for p in passages)
                    hits.append(_and((hit,timing,None if possible_clear else True)))
                    values.extend((measure(f'causal_{index}_{body}_jd',span.jd_ut1,'JD_UT1'),
                        measure(f'causal_{index}_{body}_star',causal,'zero_based_28'),
                        measure(f'causal_{index}_{body}_pada',causal_pada,'one_based_4'),
                        measure(f'causal_{index}_{body}_benefic',historical_nature[body])))
        if history is not None:
            for index,(edge,band) in enumerate(_history_bands(history)):
                if edge.lower_jd_ut1>=jd or any(p.entry.lower_jd_ut1>edge.upper_jd_ut1
                        and p.exit.upper_jd_ut1<=jd for p in passages):
                    continue
                samples,signs,moon_bad=_band_possibilities(band)
                possible=False
                for body in S.NINE:
                    states=None if body not in samples else {star28(x) for x in samples[body]}
                    match=states is None or any(mapping.get(s)==target and
                        (family=='seven_line' or 5-q==pada) for s,q in states)
                    if match and _possibly_malefic(body,signs,moon_bad):
                        possible=True
                        break
                if possible:
                    hits.append(None)
                    values.extend((measure(f'uncertain_causal_{index}_lower',edge.lower_jd_ut1,'JD_UT1'),
                                   measure(f'uncertain_causal_{index}_upper',edge.upper_jd_ut1,'JD_UT1')))
        yield finding('star_history',_or((*hits,False if complete else None)),suffix='historical_'+family,
            values=values,reasons=() if complete else ('previous_complete_Moon28_traversal_and_vedha_cells_required',))


def _pata(e, policy, positions):
    moon = positions.get('Moon')
    sun = positions.get('Sun')
    applicable = policy.regional_tradition == 'kalinga_vanga'
    target = None if moon is None else _sector(moon,27)
    same = None if moon is None or sun is None else _sector(moon,108)%4 == _sector(sun,108)%4
    # MC60 selected prescription uses the star at a qualifying yoga's END.
    # The owning star occurrence is needed, so a same-day-only yoga list cannot
    # establish absence of contamination in that occurrence.
    parent = next((s.interval for s in e.phase_spans if s.kind == 'nakshatra' and s.interval.contains(e.jd_ut1) is not False),None)
    endings = [x for x in e.yoga_endings if x.yoga_index in S.PATA_YOGAS]
    def in_occurrence(x):
        if parent is None:
            return None
        if x.boundary.upper_jd_ut1<parent.start.lower_jd_ut1 or x.boundary.lower_jd_ut1>parent.end.upper_jd_ut1:
            return False
        if parent.start.upper_jd_ut1<x.boundary.lower_jd_ut1<=x.boundary.upper_jd_ut1<parent.end.lower_jd_ut1:
            return True
        return None
    hit = _or(_and((_eq(_sector(x.moon_sidereal_longitude,27),target),same,in_occurrence(x))) for x in endings)
    complete = parent is not None and bool(e.yoga_endings) and e.yoga_endings[0].boundary.upper_jd_ut1 <= parent.start.lower_jd_ut1 and e.yoga_endings[-1].boundary.lower_jd_ut1 >= parent.end.upper_jd_ut1
    yield finding('pata',_or((hit,False if complete else None)),applicable=applicable,
        values=(measure('same_solar_pada',same),),reasons=() if complete or not applicable else ('full_star_occurrence_yoga_endings_required',))


def _tithi_sunrises(e):
    parent = next((s.interval for s in e.phase_spans if s.kind == 'tithi' and s.interval.contains(e.jd_ut1) is not False),None)
    solar = e.solar
    if (parent is None or solar is None or solar.history_extent is None
            or solar.history_extent.start_jd_ut1 > parent.start.lower_jd_ut1
            or solar.history_extent.end_jd_ut1 < parent.end.upper_jd_ut1):
        yield finding('tithi_sunrise_count',None,reasons=('full_tithi_and_sunrise_history_required',))
        return
    count = 0
    uncertain = False
    for rise in solar.sunrise_history:
        if (rise.lower_jd_ut1 <= parent.start.upper_jd_ut1 and rise.upper_jd_ut1 >= parent.start.lower_jd_ut1
                or rise.lower_jd_ut1 <= parent.end.upper_jd_ut1 and rise.upper_jd_ut1 >= parent.end.lower_jd_ut1):
            uncertain = True
        if parent.start.upper_jd_ut1 < rise.lower_jd_ut1 <= rise.upper_jd_ut1 < parent.end.lower_jd_ut1:
            count += 1
    yield finding('tithi_sunrise_count',None if uncertain else count != 1,
        values=(measure('sunrise_count',count,'complete_tithi_occurrence'),),
        reasons=('sunrise_tithi_boundary_overlap',) if uncertain else ())


def context_findings(e, policy, positions, nature, prior_findings):
    yield from _calendar(e,policy,positions)
    yield from _ingresses(e)
    yield from _history(e,positions,nature,prior_findings)
    yield from _pata(e,policy,positions)
    yield from _tithi_sunrises(e)


def personal_findings(e, policy, positions, personal):
    moon, sun = positions.get('Moon'),positions.get('Sun')
    star = None if moon is None else _sector(moon,27)
    tithi = None if sun is None or moon is None else _sector((moon-sun)%360,30)
    month = None if e.lunar_month is None or e.lunar_month.label is None else e.lunar_month.label.index
    for p in personal.participants:
        natal = p.natal_moon_sidereal_longitude
        for planet, allowed in (('Moon',(2,3,5,6,7,9,10,11)),
                               ('Jupiter',(2,5,7,9,11)) if p.role == 'bride' else ('Sun',(3,6,10,11))):
            house = _house(positions.get(planet),natal)
            yield finding('personal_shuddhi',_nnot(_in(house,allowed)),suffix=p.participant_id+'.'+planet.lower(),
                values=(measure('participant_id',p.participant_id,'identity'),measure('role',p.role,'traditional_rule_role'),
                        measure('distance_from_natal_Moon',house,'inclusive_12')))
        natal_star = None if natal is None else _sector(natal,27)
        fields = (('month',month,p.birth_lunar_month_index),('star',star,natal_star),
                  ('tithi',tithi,p.birth_tithi_index),('lagna',_sign(e.lagna_sidereal_longitude),_sign(p.natal_lagna_sidereal_longitude)))
        for name,current,birth in fields:
            match = _eq(current,birth)
            yield finding('birth_period',_and((p.first_born,match)),suffix=p.participant_id+'.'+name,
                values=(measure('first_born',p.first_born),measure('election_value',current,'index'),
                        measure('birth_value',birth,'index'),measure('matches',match)))
        count = None if star is None or natal_star is None else (star-natal_star)%27+1
        if count == 1:
            bad, interpretation = p.first_born,'mc14_birth_star_firstborn_override'
        elif count in (10,19):
            bad, interpretation = True,'mc_gochara13_unremedied_trijanma_composition'
        elif count is None or sun is None or moon is None:
            bad, interpretation = None,'missing_natal_or_election_positions'
        else:
            s = panchanga_shuddhi_from_longitudes(sun,moon,natal_nakshatra_index=natal_star,
                policy=PanchangaShuddhiPolicy(tara_profile='mc_gochara_13_quarters.v1',
                    ayanamsa_system=policy.ayanamsa_system,solver_tolerance_seconds=policy.solver_tolerance_seconds))
            bad = next(f.detected for f in s.findings if f.rule_id == 'tara_cycle')
            interpretation = 'mc_gochara13_sanskrit_quarters'
        yield finding('personal_tara',bad,suffix=p.participant_id,
            values=(measure('inclusive_count',count,'stars_27'),measure('interpretation',interpretation,'source_composition')))
    firstborn = [p.first_born for p in personal.participants]
    jy = _eq(month,2)
    yield finding('birth_period',_and((jy,*firstborn)),suffix='trijyeshtha',
        values=(measure('Jyeshtha_month',jy),*(measure(p.participant_id+'_first_born',p.first_born) for p in personal.participants)))
    factors = (jy, *firstborn)
    count = None if None in factors else sum(factors)
    yield finding('birth_period',False,suffix='dvijyeshtha_advisory',advisory=True,
        values=(measure('jyeshtha_factor_count',count,'count'),
                measure('source_quality','middling' if count == 2 else None,'MC15_advisory')))
    yield finding('marriage_context',False,applicable=False,
        values=(measure('MC93','predictions_excluded','scope'),measure('MC94','social_class_variant_excluded','scope'),
                measure('MC95','special_ceremony_form_excluded','scope')))


def compose_godhuli(e, policy, positions, ordinary):
    solar = e.solar
    inside = None
    if solar is not None and solar.half_set is not None:
        window = ShuddhiInterval(_shift(solar.half_set,-.5/60,'godhuli_start'),
                                 _shift(solar.half_set,.5/60,'godhuli_end'))
        inside = window.contains(e.jd_ut1)
        if solar.weekday in (4,6):
            setting=solar.upper_limb_set
            side=None if setting is None or setting.lower_jd_ut1<setting.upper_jd_ut1 and setting.lower_jd_ut1<=e.jd_ut1<=setting.upper_jd_ut1 else e.jd_ut1>=setting.jd_ut1
            inside=_and((inside,side if solar.weekday==4 else _nnot(side)))
    lagna = e.lagna_sidereal_longitude
    moon_bad = _in(_house(positions.get('Moon'),lagna),(1,6,8))
    mars_bad = _in(_house(positions.get('Mars'),lagna),(1,7,8))
    yield finding('godhuli',_nnot(inside),suffix='selected_window',values=(measure('inside_qualified_godhuli',inside),))
    yield finding('godhuli',moon_bad,suffix='moon_qualification')
    yield finding('godhuli',mars_bad,suffix='mars_qualification')
    qualify = _and((inside,_nnot(moon_bad),_nnot(mars_bad)))
    # MC99-101 timing remedy targets are enumerated; ordinary findings remain
    # separately available. Personal context and modern visibility are retained.
    for f in ordinary:
        if f.family_id in GODHULI_TARGETS and f.detected is not False and not f.advisory:
            exc = exception(S.GODHULI,f.rule_id,qualify,measure('qualified_window',qualify),source='MC Vivaha 99-101; VV geometric half-ghati composition')
            yield replace(f,exceptions=f.exceptions+(exc,))
        else:
            yield f
