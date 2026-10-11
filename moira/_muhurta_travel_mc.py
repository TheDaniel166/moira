"""Pure ordinary-land predicates with explicit MC48/MC04 composition."""
from dataclasses import replace
from fractions import Fraction

from . import _muhurta_travel_mc_sources as S
from ._muhurta_travel_sources import DIRECTIONS
from .muhurta_election import (_finding, _measure, _member, _not, _and, _or, _house, _sign,
                              ElectionException)
from .panchanga_shuddhi import _sector, _affine, ShuddhiInterval
from .muhurta_lagna import _nature, _LORDS
from .varga import varga_sign_index
from ._muhurta_marriage_rules import star28, _daytime

_RULES = {r.rule_id.removeprefix('travel.mc_'): r for r in S.RULES}


def _row(name, passes, **kwargs):
    return _finding(_RULES[name], passes, **kwargs)


def _edges(window, prefix='window'):
    return tuple(_measure(prefix+'_'+name+'_'+edge, getattr(b,edge+'_jd_ut1'),'JD_UT1')
                 for name,b in (('start',window.start),('end',window.end)) for edge in ('lower','upper'))


def _time_star(e, star):
    # Each family occupies a different third of its own daylight/night parent.
    groups = ((3,11,20,25,2,15),(5,8,17,18),(0,7,12),
              (4,13,16,26),(1,9,10,19,24),(6,14,21,22,23))
    if star is None or e.solar is None:
        yield _row('time_star',None)
        return
    if star in (21,12,7,4):
        yield _row('time_star',True,measures=(_measure('all_time_star',star,'zero_based_27'),))
        return
    for i, group in enumerate(groups):
        if star not in group:
            continue
        parent = ShuddhiInterval(e.solar.day.start,e.solar.sunset) if i<3 else ShuddhiInterval(e.solar.sunset,e.solar.day.end)
        j=i%3
        window=ShuddhiInterval(_affine(parent,Fraction(j,3),'time_star_start'),
                              _affine(parent,Fraction(j+1,3),'time_star_end'))
        yield _row('time_star',_not(window.contains(e.jd_ut1)),measures=_edges(window))


def _imported(e, policy, positions, nature):
    """Only enumerated defects; no wedding preferences or remedy graph."""
    from .muhurta_marriage import MarriageElectionPolicy
    from ._muhurta_marriage_rules import _discrete, _solar, _foundations, _lagna
    from ._muhurta_marriage_context import _ingresses, _history, _tithi_sunrises
    auxiliary=MarriageElectionPolicy('travel11.112_import','all_regions',remedies=(),
        ayanamsa_system=policy.ayanamsa_system,solver_tolerance_seconds=policy.solver_tolerance_seconds)
    rows=list(_discrete(e,auxiliary,positions,nature))
    rows.extend(_solar(e))
    rows.extend(_foundations(e,auxiliary,positions,vishanadi_clock='normalized_nakshatra_sixtieths.v1'))
    rows.extend(_lagna(e,auxiliary,positions,nature))
    rows.extend(_ingresses(e))
    rows.extend(_history(e,positions,nature,rows))
    rows.extend(_tithi_sunrises(e))
    for f in rows:
        if f.family_id not in S.IMPORT_FAMILIES:
            continue
        if f.family_id=='lagna_components' and '_house_' not in f.rule_id:
            continue
        source='MC48 Yatra11.112, named MC04 detector import: '+f.source
        if f.family_id=='vishanadi':
            source='MC48 Vivaha49-51/PDF218-219: BOTH offset and four-ghati width proportional to actual star duration'
        yield replace(f,rule_id='travel.mc_import.'+f.rule_id,family_id='travel.mc_import.'+f.family_id,
                      source=source,exceptions=())


def evaluate(e, policy, context):
    p={x.planet:x.sidereal_longitude for x in e.planets}
    speed={x.planet:x.longitude_speed for x in e.planets}
    sun,moon,lagna=p.get('Sun'),p.get('Moon'),e.lagna_sidereal_longitude
    star=None if moon is None else _sector(moon,27)
    absolute=None if sun is None or moon is None else _sector((moon-sun)%360,30)+1
    tithi=None if absolute is None else (absolute-1)%15+1
    weekday=None if e.solar is None else e.solar.weekday
    direction=DIRECTIONS.index(context.direction)
    cardinal=direction//2
    nature=_nature(p)
    rows=[]
    rows.append(_row('star',_member(star,S.BEST_STARS+S.MIDDLE_STARS),measures=(
        _measure('star',star,'zero_based_27'),_measure('quality',None if star is None else 'best' if star in S.BEST_STARS else 'middling' if star in S.MIDDLE_STARS else 'adverse','source_grade'))))
    solar_grade=None if sun is None else 'best' if _sign(sun) in (8,0,4) else 'lengthy' if _sign(sun) in (3,11,7) else 'middling'
    rows.append(_row('solar_grade',True,advisory=True,measures=(_measure('quality',solar_grade,'source_grade'),)))
    bad=None if absolute is None else tithi in (4,6,8,9,12,14,15) or absolute==1
    siddha=None if tithi is None or weekday is None else weekday==(5,3,2,6,4)[(tithi-1)%5]
    rows.append(_row('tithi',_not(bad),measures=(_measure('absolute_tithi',absolute,'one_based_30'),),
        exceptions=(ElectionException('mc9_siddha_only',('travel.mc_tithi',),siddha,(_measure('siddha',siddha),),'MC48 Yatra9 commentary; Shubhashubha1.4'),)))
    rows.append(_row('weekday',_not(_member(weekday,(0,2,6))),measures=(_measure('weekday',weekday,'Sunday0'),)))
    for name,bad in (('star',None if star is None else star==S.STAR_SHULA[cardinal]),
                     ('weekday',_member(weekday,S.DAY_SHULA[cardinal]))):
        rows.append(_row('direction_shula',_not(bad),suffix=name,
                         measures=(_measure('cardinal_index',cardinal,'east_south_west_north'),)))
    rows.extend(_time_star(e,star))
    rahu=None if 'Rahu' not in p else _sector(p['Rahu'],27)
    count=None if rahu is None or star is None else (star-rahu)%27+1
    rows.append(_row('rahu_half',None if count is None else 2<=count<=14,
                     measures=(_measure('inclusive_Rahu_to_Moon',count,'one_based_27'),)))
    total=None if any(x is None for x in (absolute,star,weekday)) else absolute+star+weekday+2
    for modulus in (7,8,3):
        residue=None if total is None else total%modulus
        rows.append(_row('three_moduli',None if residue is None else residue!=0,suffix=str(modulus),
                         measures=(_measure('sum',total,'integer'),_measure('remainder',residue,'integer'))))
    yogini_tithi=30 if absolute==30 else tithi
    yogini=None if yogini_tithi is None else next(i for i,values in enumerate(S.YOGINI) if yogini_tithi in values)
    rows.append(_row('yogini',None if yogini is None else yogini not in (direction,(direction-2)%8),
                     measures=(_measure('direction_index',yogini,'east0_clockwise8'),)))
    daytime=_daytime(e)
    kala=None if weekday is None or daytime is None else (6-weekday+(0 if daytime else 4))%8
    for name,offset in (('kala',0),('pasha',4)):
        value=None if kala is None else (kala+offset)%8
        rows.append(_row('kala_pasha',None if value is None else value!=direction,suffix=name,
                         measures=(_measure('direction_index',value,'east0_clockwise8'),)))
    ordinal=star28(moon)[0]
    group=None if ordinal is None else (ordinal-2)%28//7
    relief=_member(star,S.PARIGHA_RELIEF)
    rows.append(_row('parigha',None if group is None else group==cardinal,
        measures=(_measure('star_group',group,'east_south_west_north'),),
        exceptions=(ElectionException('mc38_four_stars',('travel.mc_parigha',),relief,
            (_measure('universal_star',relief),),'MC48 Yatra38/PDF299-300'),)))
    uttara=tuple(None if x is None else _sign(x) in (9,10,11,0,1,2) for x in (sun,moon))
    governing=uttara[0] if uttara[0]==uttara[1] else None if daytime is None else uttara[0 if daytime else 1]
    rows.append(_row('ayana',None if governing is None else cardinal in ((0,3) if governing else (1,2)),
        measures=(_measure('Sun_uttara',uttara[0]),_measure('Moon_uttara',uttara[1]),_measure('daytime',daytime))))
    venus=p.get('Venus')
    elongation=None if sun is None or venus is None else (venus-sun)%360
    facing=None if elongation in (None,0.,180.) else 2 if elongation<180 else 0
    blind=None if moon is None else moon>=1040/3 or moon<30
    rows.append(_row('venus_facing',None if facing is None else cardinal!=facing,
        measures=(_measure('facing_cardinal',facing,'east0_south1_west2_north3'),),
        exceptions=(ElectionException('mc42_blind_venus_first_pada',('travel.mc_venus_facing',),blind,
            (_measure('Moon_Revati_through_Krittika_first_pada',blind),),'MC48 Yatra42/PDF302; first reading only'),)))
    from .muhurta_vastu import _asta_available
    for name,passes in (('direct',None if speed.get('Venus') is None else speed['Venus']>=0),
                        ('dignity',_not(_member(_sign(venus),(5,)))),('asta',_asta_available('Venus',e))):
        rows.append(_row('venus_state',passes,suffix=name))
    for name,value in (('rashi',_sign(lagna)),('navamsa',None if lagna is None else varga_sign_index(lagna,9))):
        exceptions=()
        if value==11 and context.participant is not None:
            birth=(context.participant.natal_moon_sidereal_longitude,context.participant.natal_lagna_sidereal_longitude)
            qualified=_and((*(None if x is None else nature[_LORDS[_sign(x)]] for x in birth),
                            _or(None if x is None else _sign(x)==value for x in birth)))
            exceptions=(ElectionException('mc44_benefic_natal_lords',('travel.mc_lagna.'+name,),qualified,
                (_measure('both_birth_lords_benefic_and_birth_sign',qualified),),'MC48 Yatra44/PDF303; Pisces qualification'),)
        rows.append(_row('lagna',_not(_member(value,(10,11))),suffix=name,
                         measures=(_measure('sign',value,'zero_based_12'),),exceptions=exceptions))
    rows.append(_row('lagna',_not(_member(_sign(lagna),(0,1,3,8,9))),suffix='back_rising',
        measures=(_measure('dictionary','Brihat Jataka1.10: night signs exceptGemini','classical_sign_class'),)))
    lagna_direction=None if lagna is None else _sign(lagna)%4
    rows.append(_row('lagna',None if lagna_direction is None else lagna_direction!=(cardinal+2)%4,suffix='opposite_direction'))
    for planet in ('Mars','Mercury','Jupiter','Venus','Saturn'):
        retro=None if speed.get(planet) is None else speed[planet]<0
        lords=None if lagna is None else (_LORDS[_sign(lagna)],_LORDS[varga_sign_index(lagna,9)])
        for name,hit in (('kendra',_member(_house(p.get(planet),lagna),(1,4,7,10))),
                         ('varga',None if lords is None else planet in lords),
                         ('weekday',None if weekday is None else weekday=={'Mars':2,'Mercury':3,'Jupiter':4,'Venus':5,'Saturn':6}[planet])):
            rows.append(_row('retrograde',_not(_and((retro,hit))),suffix=planet.lower()+'.'+name))
    for planet,house in (('Saturn',10),('Venus',7)):
        rows.append(_row('placements',_not(_member(_house(p.get(planet),lagna),(house,))),suffix=planet.lower()))
    moon_direction=None if moon is None else _sign(moon)%4
    rows.append(_row('placements',None if moon_direction is None else moon_direction not in ((cardinal-1)%4,(cardinal+2)%4),suffix='moon_left_back'))
    lord=S.DIRECTION_LORDS[direction]
    rows.append(_row('placements',True,suffix='direction_lord',advisory=True,
        measures=(_measure('lord',lord,'planet'),_measure('in_kendra',_member(_house(p.get(lord),lagna),(1,4,7,10))))))
    rows.append(_row('southern',_not(_member(star,(22,23,24,25,26))),suffix='stars',applicable=cardinal==1))
    if e.solar is None:
        rows.append(_row('southern',None,suffix='abhijit_muhurta',applicable=cardinal==1))
    else:
        day=ShuddhiInterval(e.solar.day.start,e.solar.sunset)
        abhijit=ShuddhiInterval(_affine(day,Fraction(7,15),'abhijit_start'),_affine(day,Fraction(8,15),'abhijit_end'))
        rows.append(_row('southern',_not(abhijit.contains(e.jd_ut1)),suffix='abhijit_muhurta',
                         applicable=cardinal==1,measures=_edges(abhijit)))
    prior=context.prior_departure_jd_ut1
    if prior is not None and prior>=e.jd_ut1:
        raise ValueError('prior departure must precede the current departure')
    rows.append(_row('prior_departure',True,advisory=True,measures=(
        _measure('prior_departure',prior,'JD_UT1'),_measure('completed_stop_nights',context.completed_stop_nights,'declared_count'),
        _measure('fresh_election_required',None if context.completed_stop_nights is None else context.completed_stop_nights>=5),
        _measure('current_act_assessed',True),_measure('earlier_election_inherited',False))))
    rows.extend(_imported(e,policy,p,nature))
    personal=[]
    if context.participant is not None:
        actor=context.participant
        natal=actor.natal_moon_sidereal_longitude
        tara=None if natal is None or star is None else (star-_sector(natal,27))%27%9+1
        personal.append(_row('personal',_not(_member(tara,(3,5,7))),suffix='tara',measures=(_measure('tara',tara,'one_based9'),)))
        for name,longitude in (('moon',natal),('lagna',actor.natal_lagna_sidereal_longitude)):
            eighth=None if longitude is None else (_sign(longitude)+7)%12
            lord=None if eighth is None else _LORDS[eighth]
            bad=_or((None if eighth is None or lagna is None else _sign(lagna)==eighth,
                     None if lord is None else _member(_house(p.get(lord),lagna),(1,))))
            personal.append(_row('personal',_not(bad),suffix=name+'_eighth',
                measures=(_measure('eighth_sign',eighth,'zero_based12'),_measure('eighth_lord',lord,'planet'))))
    return tuple(rows),tuple(personal)
