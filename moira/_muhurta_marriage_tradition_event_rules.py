"""Source event rules consume retained raw histories, never opaque verdicts."""
from ._muhurta_marriage_tradition_sources import VV,KP
from ._muhurta_marriage_tradition_history import MarriageTraditionHistory
from ._muhurta_marriage_traditions import row
from ._muhurta_marriage_rules import measure,_and,_or
from ._muhurta_marriage_vv_history import _clearances
from ._muhurta_marriage_tradition_time import _witness
from .panchanga_shuddhi import ShuddhiInterval,_sector
from .muhurta_dosha import _shift
from .muhurta_marriage import MarriageTimeSpan
from math import floor


def _stars(a,b):
    end=a+(b-a+180)%360-180
    return tuple(x%27 for x in range(floor(min(a,end)*27/360),floor(max(a,end)*27/360)+1))


def findings(e,policy,p):
    history=e.star_history
    profile=policy.profile
    if not isinstance(history,MarriageTraditionHistory) or history.tradition_profile!=profile:
        for key in (('eclipse_seven_days','event_star_contamination','krantisamya') if profile==VV else ('shadaseethimukha','eclipse_ketu_star')):
            yield row(profile,key,None,'VV1.21-23/17.3 or KP XIV/XXXIII; raw additional history required')
        return
    extent=history.additional_extent
    covers=extent.start_jd_ut1<=e.jd_ut1<extent.end_jd_ut1
    if profile==KP:
        hits=[]
        values=[]
        for i,event in enumerate(history.solar_navamsa_entries):
            segment=round(event.target_degrees*3/10)%108
            sign,part=divmod(segment,9)
            target=(4,6,8)[sign%3]
            if part!=target:
                continue
            window=ShuddhiInterval(event.boundary,_shift(event.boundary,1.,'KP_shadaseethimukha_end'))
            hits.append(window.contains(e.jd_ut1))
            values.extend(_witness(window,'entry'+str(i)))
        complete=covers and extent.start_jd_ut1<=e.jd_ut1-1
        yield row(KP,'shadaseethimukha',_or((*hits,False if complete else None)),
            'KP XXXIII/PDF207: first60 fixed ghatis after movable5/fixed7/dual9 physical solar Navamsa entry',values=values)
        star=None if 'Moon' not in p else _sector(p['Moon'],27)
        hits=[]
        for event in history.eclipse_intervals:
            hits.append(_and((event.interval.contains(e.jd_ut1),None if star is None else star in (0,9,18))))
        yield row(KP,'eclipse_ketu_star',_or((*hits,False if covers else None)),
            'KP XIV/PDF124: during eclipse and Ketu-ruled Ashwini/Magha/Mula; global shadow adapter',
            values=tuple(x for i,event in enumerate(history.eclipse_intervals) for x in _witness(event.interval,'eclipse'+str(i))))
        return
    hits=[]
    values=[]
    for i,event in enumerate(history.eclipse_intervals):
        window=MarriageTimeSpan(event.start.boundary,_shift(event.end.boundary,7.,'VV_post_eclipse_seven_days'))
        hits.append(window.contains(e.jd_ut1))
        values.extend(_witness(window,'eclipse'+str(i)))
    complete=covers and extent.start_jd_ut1<=e.jd_ut1-9
    yield row(VV,'eclipse_seven_days',_or((*hits,False if complete else None)),
        'VV1.21/PDF24-25: eclipse and7 elapsed UT1 days after global last contact; umbral lunar and penumbral solar adapter',values=values)
    for label,longitude in (('moon',p.get('Moon')),('lagna',e.lagna_sidereal_longitude)):
        target=None if longitude is None else _sector(longitude,27)
        # Six months is an outer ceiling. Two complete subsequent traversals
        # prove every earlier event has cleared, so no six-month epoch estimate
        # or six-month-wide scan is necessary. Insufficient proof stays unknown.
        older_cleared=target is not None and sum(x.planet=='Moon' and x.star_index==target and
            extent.start_jd_ut1<=x.entry.lower_jd_ut1 and x.exit.upper_jd_ut1<=e.jd_ut1 for x in history.passages)>=2
        hits=[]
        values=[]
        events=[(x.boundary,_stars(x.before_first,x.after_first),'conjunction') for x in history.conjunction_events]
        events.extend((x.end.boundary,x.star_indices,'eclipse') for x in history.eclipse_intervals)
        for i,(edge,stars,kind) in enumerate(events):
            if edge.lower_jd_ut1>e.jd_ut1:
                continue
            if target is not None and target not in stars:
                continue
            clears=0 if target is None else _clearances(history,target,edge,e.jd_ut1)
            possible=0 if target is None else _clearances(history,target,edge,e.jd_ut1,possible=True)
            active=False if clears>=2 else None if possible>=2 or edge.upper_jd_ut1>e.jd_ut1 or target is None else True
            hits.append(active)
            values.extend((measure('event'+str(i)+'_kind',kind,'event_family'),measure('event'+str(i)+'_clearances',clears,'complete_moon_passages')))
        yield row(VV,'event_star_contamination',_or((*hits,False if covers and older_cleared else None)),
            'VV1.22-23/PDF25: Moon/Lagna eclipse or five-planet bheda star; two subsequent Moon traversals clear within six months; bheda=longitude conjunction adapter',
            suffix=label,values=values,reasons=() if older_cleared else ('older_events_require_two_complete_Moon_traversals',))
    parent=next((x.interval for x in e.phase_spans if x.kind=='nakshatra' and x.interval.contains(e.jd_ut1) is not False),None)
    hits=[]
    for event in history.declination_events:
        edge=event.boundary
        owns=None if parent is None else (False if edge.upper_jd_ut1<parent.start.lower_jd_ut1 or edge.lower_jd_ut1>parent.end.upper_jd_ut1 else
            True if parent.start.upper_jd_ut1<edge.lower_jd_ut1 and edge.upper_jd_ut1<parent.end.lower_jd_ut1 else None)
        hits.append(owns)
    dec_extent=history.declination_extent
    complete=covers and parent is not None and dec_extent is not None and dec_extent.start_jd_ut1<=parent.start.lower_jd_ut1 and dec_extent.end_jd_ut1>=parent.end.upper_jd_ut1
    yield row(VV,'krantisamya',_or((*hits,False if complete else None)),
        'VV1.23/17.3: actual apparent equal signed declination contaminates owning Moon-star occurrence; no six-sign proxy',
        values=() if parent is None else _witness(parent,'owning_star'))
