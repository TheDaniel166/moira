"""Selected tradition time predicates with explicit parent and clock ownership."""
from fractions import Fraction
from ._muhurta_marriage_tradition_sources import VV,KP
from ._muhurta_marriage_traditions import row,_indices
from ._muhurta_marriage_rules import measure,_in,_or
from .panchanga_shuddhi import ShuddhiInterval,_affine,_sector
from .muhurta_dosha import _shift


def _witness(window,prefix='window'):
    return tuple(measure(prefix+'_'+side+'_'+edge,getattr(bound,edge+'_jd_ut1'),'JD_UT1')
        for side,bound in (('start',window.start),('end',window.end)) for edge in ('lower','upper'))


def findings(e,policy,p):
    profile=policy.profile
    tithi,star,karana,yoga=_indices(p)
    bhadra=None if karana is None else 1<=karana<=56 and (karana-1)%7==6
    if profile==KP and karana in (0,57,58,59):
        bhadra=True
    yield row(profile,'karana',bhadra,'VV17.6 Vishti; KP XXXIII/PDF220 Vishti plus four fixed karanas')
    # VV1.21 expressly states these fixed ghatis and first half of Parigha.
    # KP's general yoga chapter is independently collated in the standard.
    widths={9:6,8:5,0:3,14:3,12:9,5:6}
    whole=yoga in (16,26) if yoga is not None else None
    if yoga in widths:
        window=None if e.yoga_span is None else ShuddhiInterval(e.yoga_span.start,_shift(e.yoga_span.start,widths[yoga]/60,'yoga_initial_end'))
    elif yoga==18:
        window=None if e.yoga_span is None else ShuddhiInterval(e.yoga_span.start,_affine(e.yoga_span,Fraction(1,2),'parigha_half'))
    else:
        window=None
    bad=whole if yoga not in (*widths,18) else None if window is None else window.contains(e.jd_ut1)
    if profile==KP:
        bad=_in(yoga,(0,5,8,9,12,14,16,18,26))
        window=None
    yield row(profile,'nitya_yoga',bad,'VV1.21 fixed-ghati exclusions;17.6 or KP XXXIII/PDF205 whole nine yogas',values=() if window is None else _witness(window))
    from ._muhurta_marriage_context import _tithi_sunrises
    for finding in _tithi_sunrises(e):
        yield row(profile,'tithi_sunrise_count',finding.detected,'VV17.6 tithi loss/repetition; KP XXXIII exceptional sunrise-day counts',
            values=finding.measures,reasons=finding.unavailable_reasons)
    if e.solar is None:
        for key in (('day_eighth','kulika_day','kulika_night') if profile==VV else ('day_eighth',)):
            yield row(profile,key,None,'VV8.12/17.6 or KP XXXIII/PDF212')
    else:
        solar=e.solar
        daylight=ShuddhiInterval(solar.day.start,solar.sunset)
        night=ShuddhiInterval(solar.sunset,solar.day.end)
        # Yama-ardha (VV) and Yamaganda (KP) are distinct tables.
        eighth=((4,7,2,5,8,3,6) if profile==VV else (5,4,3,2,1,7,6))[solar.weekday]
        clocks=(
            ('day_eighth',daylight,eighth,8),
            ('kulika_day',daylight,(14,12,10,8,6,4,2)[solar.weekday],15),
            ('kulika_night',night,(13,11,9,7,5,3,1)[solar.weekday],15)) if profile==VV else ()
        for key,parent,ordinal,denom in clocks:
            window=ShuddhiInterval(_affine(parent,Fraction(ordinal-1,denom),key+'_start'),_affine(parent,Fraction(ordinal,denom),key+'_end'))
            yield row(profile,key,window.contains(e.jd_ut1),'VV8.12/17.6 yama-ardha/kulika; day/night proportional-muhurta adapter',values=_witness(window))
        if profile==KP:
            window=ShuddhiInterval(_shift(solar.day.start,(eighth-1)/16,'KP_Yamaganda_start'),_shift(solar.day.start,eighth/16,'KP_Yamaganda_end'))
            yield row(profile,'day_eighth',window.contains(e.jd_ut1),'KP XXXIII/PDF212 explicitly90-minute divisions from sunrise',values=_witness(window))
    if profile==KP:
        parent=next((x.interval for x in e.phase_spans if x.kind=='nakshatra' and x.interval.contains(e.jd_ut1) is not False),None)
        window=None if parent is None else ShuddhiInterval(_shift(parent.end,-2/60,'KP_star_last_two_start'),parent.end)
        yield row(profile,'star_end',None if window is None else window.contains(e.jd_ut1),'KP XXXIII/PDF219: last two fixed ghatis',values=() if window is None else _witness(window))
        month=e.lunar_month
        # Physical Amanta parent is the declared modern month clock. No
        # hard-coded30-day approximation is used for the final three days.
        lunation=None if month is None else month.amanta_lunation
        if lunation is None:
            yield row(profile,'month_end',None,'KP XXXIII/PDF219: final three elapsed days of physical Amanta lunation')
        else:
            from .panchanga_shuddhi import ShuddhiBoundary
            end=lunation.end
            edge=ShuddhiBoundary('amanta_end',(end.lower_jd_ut1+end.upper_jd_ut1)/2,end.lower_jd_ut1,end.upper_jd_ut1)
            window=ShuddhiInterval(_shift(edge,-3,'KP_month_last_three_start'),edge)
            yield row(profile,'month_end',window.contains(e.jd_ut1),'KP XXXIII/PDF219: final three elapsed days of physical Amanta lunation',values=_witness(window))
        index=None if month is None or month.label is None else month.label.index
        yield row(profile,'year_end',None if index is None or tithi is None else index==11 and tithi>=15,
            'KP XXXIII/PDF219: final fortnight; explicit Chaitra-year/Amanta adapter')
        # End-of-season uses the already quantified last3 days of its second
        # lunar month. Ayana end uses KP's own Capricorn/Cancer ingress wait.
        # These cannot create a new implicit clock or contradict XIV's explicit
        # permission of Purnima and Krishna1..8.
        end=None if lunation is None else window.contains(e.jd_ut1)
        yield row(profile,'ruthu_end',None if index is None or end is None else index%2==1 and end,
            'KP XIV/PDF122 paired lunar seasons; XXXIII/PDF219 final3-day end adapter')
        from .muhurta_marriage import MarriageException
        paksha_end=_in(tithi,(14,29))
        exemption=MarriageException('kp_xiv_specific_purnima_permission',('kp.paksha_end',),tithi==14 if tithi is not None else None,
            (), 'KP XIV/PDF116 explicitly middling Full Moon takes precedence over generic end-Paksha wording')
        yield row(profile,'paksha_end',paksha_end,'KP XIV/PDF122-123: final-tithi boundary adapter, specific permission retained',exceptions=(exemption,))
        yield from _kp_gandanta(e,tithi,star)
        yield from _kp_thyajyam(e,tithi,star)
    else:
        # VV names Gandanta without the numeric subdivision here. This
        # separately attributed MC43 fixed-ghati adapter is an explicit
        # composition, not a claim that VV supplied the numbers.
        from ._muhurta_marriage_rules import _foundations
        for f in _foundations(e,policy,p):
            if f.family_id in ('nakshatra_gandanta','tithi_gandanta','lagna_gandanta'):
                yield row(profile,f.family_id,f.detected,'VV8.12/17.6 + explicit MC Vivaha43 fixed-ghati quantitative adapter',values=f.measures,reasons=f.unavailable_reasons)


def _kp_gandanta(e,tithi,star):
    for kind,index,first,last in (('nakshatra',star,(0,9,18),(8,17,26)),
        ('tithi',tithi,(),(4,9,14,19,24,29))):
        parent=next((x.interval for x in e.phase_spans if x.kind==kind and x.interval.contains(e.jd_ut1) is not False),None)
        selected=None if index is None else index in first or index in last
        window=None
        if selected and parent is not None:
            window=(ShuddhiInterval(parent.start,_shift(parent.start,2/60,'KP_gandanta_end')) if index in first else
                    ShuddhiInterval(_shift(parent.end,-2/60,'KP_gandanta_start'),parent.end))
        detected=False if selected is False else None if window is None else window.contains(e.jd_ut1)
        yield row(KP,kind+'_gandanta',detected,'KP II/PDF49 definition imported by XXXIII21-dosha list:2 fixed ghatis',values=() if window is None else _witness(window))
    lagna=e.lagna_sidereal_longitude
    segment=None if lagna is None else _sector(lagna,108)
    bad=None if segment is None else (segment//9 in (3,7,11) and segment%9==8) or (segment//9 in (0,4,8) and segment%9==0)
    yield row(KP,'rasi_gandanta',bad,'KP II/PDF49: last water-sign D9 segment, first fire-sign D9 segment')


_KP_THYAJYAM_OFFSETS = {
    'nakshatra': (50,24,30,40,14,21,30,20,32,30,20,18,21,20,14,14,10,14,20,24,20,10,10,18,6,24,30),
    'tithi': (24,12,55,5,54,5,34,10,21,7,29,6,13,21,35),
}


def kp_phase_spans(parents,jd):
    """Keep the fixed-clock history needed anywhere in the current parent.

    An older exclusion ends no later than its start plus max(offset)+4
    ghatis. Retaining through that horizon also lets a window midpoint
    enumerate exclusions that finish before the midpoint itself.
    """
    from ._muhurta_dosha_day import _context_spans
    ordinary = _context_spans(parents,jd)
    selected = []
    for kind,spans in parents.items():
        if kind not in _KP_THYAJYAM_OFFSETS:
            selected.extend(s for s in ordinary if s.kind==kind)
            continue
        current = [i for i,s in enumerate(spans) if s.interval.contains(jd) is not False]
        lookback = (max(_KP_THYAJYAM_OFFSETS[kind])+4)/60
        cutoff = _shift(spans[current[0]].interval.start,-lookback,'KP_carryover_horizon').lower_jd_ut1
        first = current[0]
        while first>0 and spans[first].interval.start.upper_jd_ut1>cutoff:
            first -= 1
        selected.extend(spans[first:current[-1]+1])
    return tuple(selected)


def _kp_thyajyam(e,tithi,star):
    # Literal fixed ghatis are selected. The alternate second Mula interval
    # is not folded into this edition's ordinary first prescription.
    for kind,table in _KP_THYAJYAM_OFFSETS.items():
        spans = tuple(s for s in e.phase_spans if s.kind==kind)
        lookback = (max(table)+4)/60
        complete = bool(spans and _shift(spans[0].interval.start,lookback,'KP_carryover_covered').upper_jd_ut1<=e.jd_ut1)
        hits,values = [],[]
        for i,span in enumerate(spans):
            # Bright-fortnight applicability belongs to the parent, including
            # any part of its exclusion that reaches into a later tithi.
            if kind=='tithi' and span.index>=15:
                continue
            offset = table[span.index]
            window = ShuddhiInterval(_shift(span.interval.start,offset/60,'KP_thyajyam_start'),
                                    _shift(span.interval.start,(offset+4)/60,'KP_thyajyam_end'))
            hits.append(window.contains(e.jd_ut1))
            values.extend((measure('parent'+str(i)+'_index',span.index,'zero_based_parent'),
                           *_witness(window,'parent'+str(i))))
        detected = _or((*hits,False if complete else None))
        applicable = (True if kind=='nakshatra' or (tithi is not None and tithi<15) or any(x is not False for x in hits)
                      else False if complete and tithi is not None else None)
        yield row(KP,kind+'_thyajyam',detected,
            'KP XXXIII/PDF222-223: literal fixed ghatis,4-ghati width; tithi table explicitly bright fortnight',
            applicable=applicable,values=(*values,measure('carryover_history_complete',complete)),
            reasons=() if complete else ('preceding_phase_history_required_for_fixed_clock_carryover',))
    solar=e.solar
    offset=None if solar is None else (30,42,41,31,2,22,20)[solar.weekday]
    window=None if solar is None else ShuddhiInterval(_shift(solar.day.start,offset/60,'KP_weekday_thyajyam_start'),
        _shift(solar.day.start,(offset+4)/60,'KP_weekday_thyajyam_end'))
    yield row(KP,'weekday_thyajyam',None if window is None else window.contains(e.jd_ut1),'KP XXXIII/PDF223: fixed clock after sunrise',values=() if window is None else _witness(window))
    segment=None if e.lagna_sidereal_longitude is None else _sector(e.lagna_sidereal_longitude,108)
    if segment is None or solar is None:
        bad=None
    else:
        sign,part=divmod(segment,9)
        target=0 if sign in (0,1,5,8) else 4 if sign in (2,4,6,10) else 8
        weekdays=(3,6) if target==0 else (1,5) if target==4 else (0,2,4)
        bad=part==target and solar.weekday in weekdays
    yield row(KP,'rasi_thyajyam',bad,'KP XXXIII/PDF223: sign-specific1/5/9 navamsa with its own weekday qualification')
