"""Finite VV/KP ordinary doctrine, with independent source precedence.

Raw astronomy is shared; calendar, house testimony, Navamsa, history and
remedies are selected here. No whole-profile score or numeric dosha subtraction.
"""
from dataclasses import replace
from fractions import Fraction

from . import _muhurta_marriage_tradition_sources as S
from ._muhurta_marriage_sources import NINE, SEVEN
from .muhurta_marriage import MarriageFinding, MarriageException, MarriageTimeSpan
from ._muhurta_marriage_rules import (measure,star28,_sign,_house,_in,_eq,_nnot,_and,_or)
from .muhurta_lagna import _nature,_LORDS,_aspect
from .panchanga_shuddhi import _sector,ShuddhiInterval
from .muhurta_dosha import _shift
from .varga import varga_sign_index
from .vedic_dignities import OWN_SIGNS,EXALTATION_SIGN,DEBILITATION_SIGN,NATURAL_ENEMIES
from .avasthas import _is_combust


def row(profile,key,detected,locus,*,suffix='',values=(),exceptions=(),advisory=False,reasons=(),applicable=True):
    prefix='vv' if profile==S.VV else 'kp'
    family=prefix+'.'+key
    rid=family+('.'+suffix if suffix else '')
    if applicable is not False and detected is None and not advisory and not reasons:
        reasons=('required_evidence_missing_or_boundary_uncertain',)
    return MarriageFinding(rid,family,locus,applicable,detected,tuple(values),tuple(exceptions),tuple(reasons),advisory)


def _indices(positions):
    sun,moon=positions.get('Sun'),positions.get('Moon')
    phase=None if sun is None or moon is None else (moon-sun)%360
    return (None if phase is None else _sector(phase,30),
            None if moon is None else _sector(moon,27),
            None if phase is None else _sector(phase,60),
            None if phase is None else _sector((sun+moon)%360,27))


def _calendar(e,policy,p):
    profile=policy.profile
    month=e.lunar_month
    index=None if month is None or month.label is None else month.label.index
    solar=_sign(p.get('Sun'))
    if profile==S.VV:
        # Source1.3/5 ordinary Uttarayana, qualified by10.1-4 lunar priority.
        allowed=_or((_in(solar,(9,10,0,1,2)),_and((_eq(index,11),_eq(solar,11)))))
        allowed=_and((allowed,_nnot(_in(index,(0,9)))))
        yield row(profile,'calendar',_nnot(allowed),'VV1.3-5;10.1-4/PDF15-17,86-88',
            values=(measure('month_index',index,'Chaitra=0'),measure('solar_sign',solar,'zero_based_12'),
                    measure('calendar_adapter','physical_amanta_with_source_specific_lunar_precedence','composition')))
    else:
        yield row(profile,'calendar',_in(index,S.KP_BAD_MONTHS),'KP XIV/PDF121-122',
            values=(measure('month_index',index,'Chaitra=0'),))
        quality=None if index is None else 'prohibited' if index in S.KP_BAD_MONTHS else 'middling' if index in S.KP_MIDDLE_MONTHS else 'good'
        yield row(profile,'calendar_grade',False,'KP XIV/PDF116,121-122',advisory=True,
            values=(measure('month_quality',quality,'source_grade'),
                    measure('ayana_quality',None if solar is None else 'excellent' if solar in (9,10,11,0,1,2) else 'middling','source_grade')))
    yield row(profile,'intercalation',None if month is None or month.label is None else month.label.qualifier!='ordinary',
        'VV17.6/PDF128-129' if profile==S.VV else 'KP XXXIII general calendar exclusions',
        values=(measure('month_qualifier',None if month is None or month.label is None else month.label.qualifier,'calendar_status'),))


def _availability(e,policy,planet):
    profile=policy.profile
    ctx=getattr(e,planet.lower()+'_apparition')
    if ctx is None:
        yield row(profile,'availability',None,'VV5.8-9/PDF54-55' if profile==S.VV else 'KP XIV/PDF117;XXXIII/PDF219;glossary/PDF281',suffix=planet.lower())
        return
    previous,following=ctx.previous_event,ctx.next_event
    invisible=previous.role=='disappearance'
    post,_=S.buffers(profile,planet,previous.side)
    _,pre=S.buffers(profile,planet,following.side)
    start=_shift(previous.boundary,post if not invisible else 0.,'appearance_wait_end')
    end=_shift(following.boundary,-pre if not invisible else 0.,'disappearance_wait_start')
    # If both waiting periods overlap there is no available interval.
    if start.lower_jd_ut1>=end.upper_jd_ut1:
        restricted=True
    elif start.upper_jd_ut1>=end.lower_jd_ut1:
        restricted=True if e.jd_ut1<start.lower_jd_ut1 or e.jd_ut1>=end.upper_jd_ut1 else None
    else:
        available=MarriageTimeSpan(start,end).contains(e.jd_ut1)
        restricted=True if invisible else _nnot(available)
    yield row(profile,'availability',restricted,'VV5.9 specific over5.8; SS IX geometry adapter' if profile==S.VV else
        'KP XIV/PDF117 specific Venus7d;XXXIII/PDF219 Venus10d pre;angular orbs/PDF281',suffix=planet.lower(),
        values=(measure('post_appearance_days',post,'elapsed_UT1_days'),measure('pre_disappearance_days',pre,'elapsed_UT1_days'),
            measure('event_geometry','SS_IX_modern_diurnal_arc' if profile==S.VV else 'KP_angular_11_10_8_degrees','composition'),
            measure('invisible_interval',invisible),
            measure('appearance_wait_end_lower',start.lower_jd_ut1,'JD_UT1'),measure('appearance_wait_end_upper',start.upper_jd_ut1,'JD_UT1'),
            measure('disappearance_wait_start_lower',end.lower_jd_ut1,'JD_UT1'),measure('disappearance_wait_start_upper',end.upper_jd_ut1,'JD_UT1')))


def _ingress(e,profile):
    history=e.ingress_history
    radius=16/60 if profile==S.VV else 3.
    complete=history is not None and 'Sun' in history.planets and history.extent.start_jd_ut1<=e.jd_ut1-radius and history.extent.end_jd_ut1>=e.jd_ut1+radius
    hits=[]
    values=[]
    for i,event in enumerate(() if history is None else history.events):
        if event.planet!='Sun':
            continue
        pad=16/60 if profile==S.VV else 3. if event.entered_sign in (0,3,9) else 1. if event.entered_sign==6 else .5
        a,b=_shift(event.boundary,-pad,'source_ingress_start'),_shift(event.boundary,pad,'source_ingress_end')
        hits.append(MarriageTimeSpan(a,b).contains(e.jd_ut1))
        for side,edge in (('start',a),('end',b)):
            values.extend((measure(f'event_{i}_{side}_lower',edge.lower_jd_ut1,'JD_UT1'),measure(f'event_{i}_{side}_upper',edge.upper_jd_ut1,'JD_UT1')))
    yield row(profile,'solar_ingress',_or((*hits,False if complete else None)),
        'VV8.12 Vasantalakshmi/PDF76 defines16 ghatis each side;17.6 recap' if profile==S.VV else 'KP printed175/PDF212:30/60/180 fixed ghatis each side',values=values)


def _vv_stars(e,p):
    profile=S.VV
    tithi,star,karana,yoga=_indices(p)
    target,pada=star28(p.get('Moon'))
    mapping=dict(S.VV_FIVE_PAIRS+tuple((b,a) for a,b in S.VV_FIVE_PAIRS))
    for planet in NINE:
        if planet=='Moon':
            continue
        cause,cpada=star28(p.get(planet))
        yield row(profile,'five_line',None if cause is None or target is None else mapping.get(cause)==target,
            'VV1.6-9/PDF17-19;17.3/PDF127: ordinary whole-star vedha',suffix=planet.lower(),
            values=(measure('causal_star',cause,'zero_based_28'),measure('target_star',target,'zero_based_28'),
                measure('opposed_padas',_eq(pada,None if cpada is None else 5-cpada)),measure('necessity_pada_relief_selected',False)))
    for planet,count in S.VV_LATTA:
        cause=None if planet not in p else _sector(p[planet],27)
        hit=None if cause is None or star is None else (cause+count-1)%27==star
        # 'Full Moon' is a declared Purnima-tithi interpretation, not MC's
        # every-waxing-Moon substitution. The chosen phase edge is certified.
        if planet=='Moon':
            hit=_and((hit,_eq(tithi,14)))
        yield row(profile,'latta',hit,'VV1.11-13/PDF20-21: forward inclusive counts; full Moon=Purnima tithi adapter',
            suffix=planet.lower(),values=(measure('count',count,'inclusive_27'),measure('causal_star',cause,'zero_based_27')))
    sun28,sun_pada=star28(p.get('Sun'))
    count=None if sun28 is None or target is None else (target-sun28)%28+1
    # Detailed ch1 commentary and its Revati/Chitra example take precedence
    # over contradictory parity in17.4. The whole-star restriction preserves
    # 1.18-19's rejection of a malefic-pada-only release; opposed padas grade it.
    hit=_and((_in(yoga,S.EKARGALA_YOGAS),None if count is None else count%2==1))
    yield row(profile,'ekargala',hit,'VV1.14-19/PDF21-24; detailed chapter precedence over17.4 parity',
        values=(measure('sun_to_moon',count,'inclusive_28'),measure('opposed_padas',_eq(pada,None if sun_pada is None else 5-sun_pada))))
    sun27=None if 'Sun' not in p else _sector(p['Sun'],27)
    count27=None if star is None or sun27 is None else (star-sun27)%27+1
    yield row(profile,'solar_fourteenth',_eq(count27,14),'VV1.10;17.4',values=(measure('inclusive_count',count27,'stars27'),))
    parent=next((x.interval for x in e.phase_spans if x.kind=='nakshatra' and x.interval.contains(e.jd_ut1) is not False),None)
    hits=[]
    for event in e.yoga_endings:
        if event.yoga_index not in S.PATA_YOGAS:
            continue
        inside=None if parent is None else (False if event.boundary.upper_jd_ut1<parent.start.lower_jd_ut1 or event.boundary.lower_jd_ut1>parent.end.upper_jd_ut1 else
            True if parent.start.upper_jd_ut1<event.boundary.lower_jd_ut1 and event.boundary.upper_jd_ut1<parent.end.lower_jd_ut1 else None)
        hits.append(_and((_eq(_sector(event.moon_sidereal_longitude,27),star),inside)))
    complete=bool(parent is not None and e.yoga_endings and e.yoga_endings[0].boundary.upper_jd_ut1<=parent.start.lower_jd_ut1 and e.yoga_endings[-1].boundary.lower_jd_ut1>=parent.end.upper_jd_ut1)
    yield row(profile,'pata',_or((*hits,False if complete else None)),'VV1.20;17.3: six yoga endings, whole owning star')


def _vv_navamsa(e,p,nature):
    profile=S.VV
    lagna=e.lagna_sidereal_longitude
    sign=_sign(lagna)
    nav=None if lagna is None else varga_sign_index(lagna,9)
    degrees=None if lagna is None else float(Fraction.from_float(float(lagna))*9%30)
    allowed=_or((_in(nav,(2,5,6)),_and((_eq(nav,8),None if degrees is None else degrees<15))))
    yield row(profile,'navamsa',_nnot(allowed),'VV4.8/PDF46: human signs including only first half Sagittarius',
        values=(measure('sign',nav,'zero_based_D9'),measure('degree',degrees,'D9_degrees')))
    seventh=None if sign is None else (sign+6)%12
    lord=None if nav is None else _LORDS[nav]
    seventh_lord=None if seventh is None else _LORDS[seventh]
    friendly=None if lord is None or seventh_lord is None else lord==seventh_lord or lord in dict(S.VV_FRIENDS)[seventh_lord]
    yield row(profile,'navamsa_friendship',_nnot(friendly),'VV4.8 with author-selected Yavana3.17-21; directed seventh-lord friendship',
        values=(measure('navamsa_lord',lord,'planet'),measure('seventh_lord',seventh_lord,'planet')))
    for side,owner,reference1,reference2 in (
        ('lagna',lord,sign,nav),
        ('seventh',None if nav is None else _LORDS[(nav+6)%12],seventh,None if nav is None else (nav+6)%12)):
        actual=None if owner is None else _sign(p.get(owner))
        for frame,reference in (('D1',reference1),('D9',reference2)):
            h=None if actual is None or reference is None else (actual-reference)%12+1
            yield row(profile,'navamsa_lord_house',_in(h,(2,3,8,12)),'VV4.9;17.6: D1 planet sign against each named D1/D9 reference',
                suffix=side+'.'+frame,values=(measure('house',h,'inclusive12'),measure('lord',owner,'planet')))
    lord_sign=None if lord is None else _sign(p.get(lord))
    support=_or((_eq(lord_sign,nav),None if lord is None else _eq(_aspect(lord,lord_sign,nav),1.)))
    yield row(profile,'navamsa_own_lord_support',_nnot(support),'VV6.3/PDF56-57: own lord conjunction or full graha aspect',
        values=(measure('owner',lord,'planet'),measure('qualified',support)))
    weak=None if lord is None or lord_sign is None else lord_sign==DEBILITATION_SIGN[lord]
    yield row(profile,'navamsa_lord_debility',weak,'VV4.8 weak lord; explicit sign-debility subset of qualitative weakness')
    yield row(profile,'movable_combination',_and((_in(sign,(0,3,6,9)),_in(nav,(0,3,6,9)),_in(_sign(p.get('Moon')),(6,9)))),
        'VV4.17: movable Lagna and D9 with Moon Libra/Capricorn')


def _vv_placements(e,p,nature):
    from ._muhurta_marriage_vv_geometry import bhava_house
    profile=S.VV
    asc=e.lagna_sidereal_longitude
    mc=getattr(e,'midheaven_sidereal_longitude',None)
    # VV5/13/17 explicit ordinary placement prohibitions; predictions and
    # character descriptions are not separate timing vetoes.
    forbidden={'Sun':(1,2,4,5,7,9,10,12),'Moon':(1,5,6,7,8,9,10,12),'Mars':(1,2,4,5,7,8,9,10,12),
        'Mercury':(7,8,12),'Jupiter':(7,8,12),'Venus':(3,6,7,8),
        'Saturn':(1,2,4,5,7,9,10,12),'Rahu':(1,2,4,5,7,9,10,12),'Ketu':(1,2,4,5,7,9,10,12)}
    # Specific ch5 permissions take precedence over the compressed ch13
    # recap: Moon4, Ketu8 and Venus12 remain visible source choices.
    tithi,_,_,_=_indices(p)
    moon_sign=_sign(p.get('Moon'))
    moon_owner=None if moon_sign is None else _LORDS[moon_sign]
    friend_or_benefic=None if moon_owner is None else _or((moon_owner=='Moon' or moon_owner in dict(S.VV_FRIENDS)['Moon'],nature[moon_owner]))
    moon_support=_or(_and((nature[body],body in dict(S.VV_FRIENDS)['Moon'],_eq(_aspect(body,_sign(p.get(body)),moon_sign),1.))) for body in SEVEN if body!='Moon')
    moon_qualified=_and((_eq(tithi,14),friend_or_benefic,moon_support))
    for planet in NINE:
        signhouse=_house(p.get(planet),asc)
        bhava=bhava_house(p.get(planet),asc,mc)
        bad=_or((_in(signhouse,forbidden[planet]),_in(bhava,forbidden[planet])))
        exceptions=[]
        rid='vv.placement.'+planet.lower()
        if planet=='Mars':
            qualified=_and((_eq(_aspect('Jupiter',_sign(p.get('Jupiter')),_sign(p.get('Mars'))),1.),
                _in(signhouse,(3,6,10,11)),_in(bhava,(3,6,10,11))))
            exceptions.append(MarriageException('vv5_3_jupiter_aspects_tenth_mars',(rid,),qualified,
                (measure('full_jupiter_aspect_and_no_other_house_restriction',qualified),),'VV5.3 specific exception;13.10 rejects unqualified folk waiver'))
        if planet=='Moon':
            qualified=_and((moon_qualified,_in(signhouse,(2,3,4,7,10,11)),_in(bhava,(2,3,4,7,10,11))))
            exceptions.append(MarriageException('vv13_2_qualified_full_moon',(rid,),qualified,
                (measure('Purnima_friend_benefic_full_aspect',qualified),),'VV13.2: explicit Purnima/D1-varga/full-friend-benefic-aspect adapter for7/10'))
        yield row(profile,'placement',bad,'VV5.1-7 specific permissions;13.1/10;17.5;8.4-5: adverse D1 OR bhava',suffix=planet.lower(),
            values=(measure('sign_house',signhouse,'one_based12'),measure('bhava_house',bhava,'one_based12')),
            exceptions=exceptions)
    for reference,longitude in (('lagna',asc),('moon',p.get('Moon'))):
        sides=[]
        for house in (2,12):
            sides.append(_or(_and((_eq(_house(p.get(body),longitude),house),_nnot(nature[body]))) for body in NINE))
        yield row(profile,'kartari',_and(sides),'VV5.7: malefics on both sides, no MC direct/retro qualification',suffix=reference)
        for body in NINE:
            if reference=='moon' and body=='Moon':
                continue
            exceptions=()
            if reference=='lagna' and body=='Moon':
                rid='vv.seventh_occupancy.lagna.moon'
                exceptions=(MarriageException('vv13_2_qualified_full_moon',(rid,),moon_qualified,
                    (measure('Purnima_friend_benefic_full_aspect',moon_qualified),),'VV13.2 specific Moon7 qualification'),)
            yield row(profile,'seventh_occupancy',_eq(_house(p.get(body),longitude),7),'VV6.3: any planet seventh from Lagna or Moon',suffix=reference+'.'+body.lower(),exceptions=exceptions)
    moon108=None if 'Moon' not in p else _sector(p['Moon'],108)
    for body in NINE:
        if body=='Moon':
            continue
        segment=None if body not in p else _sector(p[body],108)
        full=_and((_nnot(nature[body]),None if segment is None or moon108 is None else (segment-moon108)%108==54))
        yield row(profile,'protected_full_jamitra',full,'VV13.12-13/PDF106-107:55th inclusive =54 elapsed navamsas; no cancellation',suffix=body.lower(),
            values=(measure('moon_navamsa',moon108,'zero_based108'),measure('planet_navamsa',segment,'zero_based108'),measure('cancellable',False)))
    yield row(profile,'jupiter_sign',_in(_sign(p.get('Jupiter')),(4,9)),'VV5.5: Jupiter Leo or debility Capricorn')
    yield row(profile,'moon_association',_or(_and((_eq(_sign(p.get(body)),_sign(p.get('Moon'))),
        True if body=='Venus' else _nnot(nature[body]))) for body in NINE if body!='Moon'),
        'VV5.2;13.1: Moon with malefic or Venus; explicit whole-sign association adapter')
    for division in (1,3,9):
        lord=None if asc is None else _LORDS[varga_sign_index(asc,division)]
        house=None if lord is None else _house(p.get(lord),asc)
        yield row(profile,'division_lord_sixth',_eq(house,6),'VV13.1: Lagna, Drekkana and Navamsa lords in sixth',suffix=str(division),values=(measure('lord',lord,'planet'),))
    for label,body in (('moon','Moon'),('navamsa_lord',None if asc is None else _LORDS[varga_sign_index(asc,9)])):
        combust=None if body is None or body not in p or 'Sun' not in p else _is_combust(body,p)
        yield row(profile,'combustion',combust,'VV5.2;13.1: explicit ordinary angular combustion adapter',suffix=label,
            values=(measure('body',body,'planet'),measure('orb_profile','moira_avasthas_fixed_planetary_orbs','composition')))


def _kp_discrete(e,p,nature):
    profile=S.KP
    tithi,star,karana,yoga=_indices(p)
    ordinal=None if tithi is None else tithi%15+1
    quality=None if tithi is None else 'prohibited' if tithi>=23 or tithi==0 else (
        'best' if ordinal in S.KP_BEST_TITHIS else 'middling' if ordinal in S.KP_MIDDLE_TITHIS or tithi==15 else 'prohibited')
    yield row(profile,'tithi',None if quality is None else quality=='prohibited','KP XIV/PDF116;XXXIII/PDF219: dark after8 prohibited',
        values=(measure('absolute_tithi',None if tithi is None else tithi+1,'one_based30'),measure('quality',quality,'source_grade')))
    yield row(profile,'weekday',_nnot(_in(None if e.solar is None else e.solar.weekday,(1,3,4,5))),'KP XIV/PDF117')
    sign=_sign(e.lagna_sidereal_longitude)
    grade=None if sign is None else 'best' if sign in (2,5,6) else 'prohibited' if sign in (0,9,7,11) else 'middling'
    yield row(profile,'lagna',None if grade is None else grade=='prohibited','KP XIV/PDF117',values=(measure('quality',grade,'source_grade'),))
    yield row(profile,'prishtodaya',_in(sign,S.PRISHTODAYA),'KP XIV/PDF123;Brihat Jataka1.10 classification')
    nav=None if e.lagna_sidereal_longitude is None else varga_sign_index(e.lagna_sidereal_longitude,9)
    owner=None if nav is None else _LORDS[nav]
    yield row(profile,'navamsa',_in(owner,('Sun','Mars','Saturn')),'KP XIV/PDF117: fixed benefic ownership',values=(measure('lord',owner,'planet'),))
    for planet,bad_houses in S.KP_BAD_HOUSES:
        house=_house(p.get(planet),e.lagna_sidereal_longitude)
        bad=_in(house,bad_houses)
        grade=None if house is None else 'adverse' if bad else 'favorable' if house in dict(S.KP_GOOD_HOUSES)[planet] else 'unassigned'
        yield row(profile,'placement',bad,'KP XIV/PDF117-119: specific testimony takes precedence over general21-dosha list',suffix=planet.lower(),
            values=(measure('house',house,'one_based12'),measure('testimony',grade,'source_grade'),measure('global_waiver',False)))
    motions={x.planet:x.longitude_speed for x in e.planets}
    for planet in ('Jupiter','Venus'):
        sign=_sign(p.get(planet))
        enemy=None if sign is None else _LORDS[sign] in NATURAL_ENEMIES[planet]
        bad=_or((_eq(sign,DEBILITATION_SIGN[planet]),enemy,None if motions.get(planet) is None else motions[planet]<0))
        yield row(profile,'planet_strength',bad,'KP XXXIII/PDF219: debility, enemy sign or retrograde; natural-enemy adapter',suffix=planet.lower())
    yield row(profile,'jupiter_venus_opposition',_eq(_house(p.get('Jupiter'),p.get('Venus')),7),
        'KP XXXIII/PDF219: whole-sign opposed placement adapter')
    yield row(profile,'moon_association',_or(_eq(_sign(p.get(body)),_sign(p.get('Moon'))) for body in NINE if body!='Moon'),
        'KP XIV/PDF124: whole-sign association adapter; glossary exact-longitude variant retained separately')
    # KP's actual27-star diagram has one head and13 pairs. No Abhijit,
    # no VV/MC parity shortcut, and the source explicitly restricts it to day.
    heads={0:0,16:8,8:4,18:9,9:18,5:16,14:7,12:6,26:13}
    head=heads.get(yoga)
    sunstar=None if 'Sun' not in p else _sector(p['Sun'],27)
    paired=None if star is None or sunstar is None else False if head is None else (
        star!=head and sunstar!=head and (sunstar+star-2*head)%27==0)
    day=None if e.solar is None else ShuddhiInterval(e.solar.day.start,e.solar.sunset).contains(e.jd_ut1)
    yield row(profile,'ekargala',_and((paired,day)), 'KP XXXIII/PDF206-207:27-star paired diagram, daytime only',
        values=(measure('head',head,'zero_based27'),measure('paired',paired),measure('daytime',day)))
    sides=[]
    for house in (2,12):
        sides.append(_or(_and((_eq(_house(p.get(body),e.lagna_sidereal_longitude),house),_nnot(nature[body]),
            None if motions.get(body) is None else motions[body]<0)) for body in NINE))
    yield row(profile,'kartari',_and(sides),'KP XXXIII/PDF208: both flanking malefics retrograde')
    from ._muhurta_marriage_vv_hora import varga_lords
    lords=None if e.lagna_sidereal_longitude is None else varga_lords(e.lagna_sidereal_longitude)
    for i,division in enumerate((1,2,3,9,12,30)):
        owner=None if lords is None else lords[i]
        yield row(profile,'shadvarga',None if owner is None else _nnot(nature[owner]),
            'KP XXXIII/PDF216-219: malefic-owned Shadvargas; BJ1.7/9 standard division adapter',suffix=str(division),
            values=(measure('lord',owner,'planet'),))


def _personal(e,policy,p,personal):
    if personal is None:
        return
    profile=policy.profile
    tithi,star,_,_=_indices(p)
    month=None if e.lunar_month is None or e.lunar_month.label is None else e.lunar_month.label.index
    for person in personal.participants:
        natal=person.natal_moon_sidereal_longitude
        natalstar=None if natal is None else _sector(natal,27)
        count=None if star is None or natalstar is None else (star-natalstar)%27+1
        if profile==S.KP:
            bad=None if count is None else count in (10,19) or (count-1)%9+1 in (3,5,7)
            if count==1:
                bad=person.first_born if person.role=='groom' else False
            yield row(profile,'personal_tara',bad,'KP XIV/PDF123-124: first-born groom specificity for Janma',suffix=person.participant_id,
                values=(measure('inclusive_count',count,'stars27'),measure('role',person.role,'source_role')))
            if person.role=='bride':
                yield row(profile,'personal_jupiter',_nnot(_in(_house(p.get('Jupiter'),natal),(2,5,7,9,11))),
                    'KP XIV/PDF116: Jupiter from bride natal Moon',suffix=person.participant_id)
            for name,current,birth in (('month',month,person.birth_lunar_month_index),('tithi',tithi,person.birth_tithi_index)):
                yield row(profile,'birth_period',_and((person.role=='groom',person.first_born,_eq(current,birth))),
                    'KP XIV/PDF124: first-born groom only',suffix=person.participant_id+'.'+name)
        else:
            # Source6 requires both partners; these are named ordinary transit
            # adapters, not compatibility, Ashtakavarga or a birth-chart score.
            yield row(profile,'personal_moon',_nnot(_in(_house(p.get('Moon'),natal),(1,3,6,7,10,11))),
                'VV6.1-6 requires both Moons; ordinary six-house Chandra-bala adapter',suffix=person.participant_id,
                values=(measure('natal_moon',natal,'sidereal_degrees'),))
            for planet,allowed in (('Sun',(3,6,10,11)),('Jupiter',(2,5,7,9,11))):
                yield row(profile,'personal_transit',_nnot(_in(_house(p.get(planet),natal),allowed)),
                    'VV6.5;10.5-7;17.7: named ordinary transit-house adapter',suffix=person.participant_id+'.'+planet.lower())
            for reference,birth in (('moon',natal),('lagna',person.natal_lagna_sidereal_longitude)):
                house=_house(e.lagna_sidereal_longitude,birth)
                birthsign=_sign(birth)
                shared_lord=None if birthsign is None or e.lagna_sidereal_longitude is None else _LORDS[_sign(e.lagna_sidereal_longitude)]==_LORDS[birthsign]
                eighth=_and((_eq(house,8),_nnot(shared_lord)))
                yield row(profile,'personal_lagna',_or((eighth,_eq(house,12))),
                    'VV4.16 shared Venus/Mars-lord eighth exception;17.7 eighth/twelfth',suffix=person.participant_id+'.'+reference,
                    values=(measure('house',house,'inclusive12'),measure('shared_lord_eighth_exception',_and((_eq(house,8),shared_lord)))))


def _remedies(rows,e,policy,p):
    profile=policy.profile
    for f in rows:
        exceptions=list(f.exceptions)
        if profile==S.VV and S.VV_REMEDIES[0] in policy.remedies and f.family_id=='vv.seventh_occupancy' and '.moon.' in f.rule_id:
            moon=_sign(p.get('Moon'))
            candidates=[]
            for body in ('Mercury','Venus','Jupiter'):
                sign=_sign(p.get(body))
                friend=None if sign is None else _LORDS[sign]==body or _LORDS[sign] in dict(S.VV_FRIENDS)[body]
                candidates.append(_and((_in(_house(p.get(body),e.lagna_sidereal_longitude),(1,4,5,9,10)),friend,_eq(_aspect(body,sign,moon),1.))))
            causal_body=f.rule_id.rsplit('.',1)[-1].capitalize()
            qualified=_and((_or(candidates),_nnot(_nature(p).get(causal_body))))
            # Full Jamitra has its OWN non-cancellable row and is never targeted.
            exceptions.append(MarriageException(S.VV_REMEDIES[0],(f.rule_id,),qualified,
                (measure('qualified_benefic',qualified),),'VV13.11;13.12-13 protection remains independently effective'))
        if profile==S.KP and S.KP_REMEDIES[0] in policy.remedies and f.family_id in ('kp.tithi','kp.weekday','kp.prishtodaya'):
            candidates=[]
            for body in ('Mercury','Venus','Jupiter'):
                sign=_sign(p.get(body))
                dignified=None if sign is None else sign in OWN_SIGNS[body] or sign==EXALTATION_SIGN[body]
                motion=next((x.longitude_speed for x in e.planets if x.planet==body),None)
                combust=None if body not in p or 'Sun' not in p else _is_combust(body,p)
                candidates.append(_and((_eq(_house(p.get(body),e.lagna_sidereal_longitude),1),dignified,
                    None if motion is None else motion>=0,_nnot(combust))))
            qualified=_or(candidates)
            exceptions.append(MarriageException(S.KP_REMEDIES[0],(f.rule_id,),qualified,
                (measure('own_or_exalted_direct_noncombust_benefic_lagna',qualified),),
                'KP XIV/PDF123-124; explicit finite timing subset of broad strength language; no numeric subtraction'))
        yield replace(f,exceptions=tuple(exceptions))


def evaluate(e,policy,personal):
    p={x.planet:x.sidereal_longitude for x in e.planets}
    profile=policy.profile
    nature=_nature(p)
    _,star,_,_=_indices(p)
    rows=[row(profile,'wedding_star',_nnot(_in(star,S.STARS)),'VV1.3/PDF15 or KP XIV/PDF116',values=(measure('star',star,'zero_based27'),))]
    rows.extend(_calendar(e,policy,p))
    rows.extend(_ingress(e,profile))
    for planet in ('Jupiter','Venus'):
        rows.extend(_availability(e,policy,planet))
    if profile==S.VV:
        rows.extend(_vv_stars(e,p))
        rows.extend(_vv_navamsa(e,p,nature))
        rows.extend(_vv_placements(e,p,nature))
        from ._muhurta_marriage_vv_hora import findings as hora_findings
        rows.extend(hora_findings(e,p,nature))
        from ._muhurta_marriage_vv_history import findings
        rows.extend(findings(e,p))
    else:
        rows.extend(_kp_discrete(e,p,nature))
        from ._muhurta_marriage_kp_history import findings
        rows.extend(findings(e,p))
    from ._muhurta_marriage_tradition_time import findings
    rows.extend(findings(e,policy,p))
    from ._muhurta_marriage_tradition_event_rules import findings
    rows.extend(findings(e,policy,p))
    rows=tuple(_remedies(rows,e,policy,p))
    return rows,tuple(_personal(e,policy,p,personal)),rows
