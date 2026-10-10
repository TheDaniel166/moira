"""Finite raw historical sky cells supporting MC58 lunar clearance.

A preceding full lunar revolution establishes a finite reset witness for
every unequal28-star target. This supplements (and does not redefine) the
separately named nearest previous/current/next occupied-star convention.
"""
from ._muhurta_marriage_sources import NINE
from ._muhurta_marriage_rules import star28
from .muhurta_marriage import (MarriageHistoricalSkySpan,MarriageMoon28Passage,MarriagePlanet,
    MarriageHistoricalLongitude,MarriageHistoricalSkyBand)
from ._muhurta_marriage_enclosure import EnclosureUnavailable
from .panchanga_shuddhi import ShuddhiInterval,_point


PADA_TARGETS=tuple(sorted(set([i*360/108 for i in range(108)]+[830/3+i*(2528/9-830/3)/4 for i in range(5)])))
STAR28_TARGETS=tuple(sorted([i*360/27 for i in range(27) if i!=21]+[830/3,2528/9]))


def vedha_history(context,anchor,future_end=None):
    from ._muhurta_marriage_windows import _clipped_bands
    radius=context.range_radius
    days=min(40,context.meter.limits.max_history_days)
    lo,hi=anchor-radius-days,max(anchor+radius+1/86400,future_end or anchor)
    meter=context.meter
    meter.stage='historical_piercing_and_lunar_clearance'
    context.history_extents.append(('historical_vedha',lo,hi))
    moon_roots=context.angular((('Moon',1),),lo,hi,STAR28_TARGETS,1.,'Moon28_clearance')
    passages=tuple(MarriageMoon28Passage(star28(context.longitude_at('Moon',(a.boundary.upper_jd_ut1+b.boundary.lower_jd_ut1)/2))[0],a.boundary,b.boundary)
        for a,b in zip(moon_roots,moon_roots[1:]) if a.boundary.upper_jd_ut1<b.boundary.lower_jd_ut1)
    boundaries=[_point('vedha_history_start',lo),_point('vedha_history_end',hi)]
    for body in NINE:
        roots=context.angular(((body,1),),lo,hi,PADA_TARGETS,1.,body+'_historical_pada')
        boundaries.extend(r.boundary for r in roots)
    phase=context.angular((('Moon',1),('Sun',-1)),lo,hi,(0.,180.),1.,'historical_nature_phase')
    boundaries.extend(r.boundary for r in phase)
    bands=_clipped_bands(boundaries,lo,hi)
    context.certifier.maximum_boundary_width_seconds=max(context.certifier.maximum_boundary_width_seconds,
        max((b.upper_jd_ut1-b.lower_jd_ut1)*86400 for b in bands))
    spans=[]
    for a,b in zip(bands,bands[1:]):
        if a.upper_jd_ut1>=b.lower_jd_ut1:
            continue
        if len(spans)>=4096:
            from ._muhurta_marriage_search import MarriageSearchBudgetError
            raise MarriageSearchBudgetError('historical_cells',4096,len(spans)+1,meter.stage)
        jd=(a.upper_jd_ut1+b.lower_jd_ut1)/2
        meter.tick('historical_cells')
        planets=tuple(MarriagePlanet(p,context.longitude_at(p,jd)) for p in NINE)
        spans.append(MarriageHistoricalSkySpan(ShuddhiInterval(a,b),jd,planets))
    uncertain=[]
    for band in bands[1:-1]:
        if band.lower_jd_ut1==band.upper_jd_ut1:
            continue
        bounds=[]
        reasons=[]
        phase_bounds=None
        for body in NINE:
            try:
                box=context.certifier.angular_signal(((body,1),),band.lower_jd_ut1,band.upper_jd_ut1,False).value
                bounds.append(MarriageHistoricalLongitude(body,box.lo,box.hi))
            except EnclosureUnavailable as exc:
                reasons.append(body+':'+str(exc))
        try:
            box=context.certifier.angular_signal((('Moon',1),('Sun',-1)),band.lower_jd_ut1,band.upper_jd_ut1,False).value
            phase_bounds=(box.lo,box.hi)
        except EnclosureUnavailable as exc:
            reasons.append('phase:'+str(exc))
        uncertain.append(MarriageHistoricalSkyBand(band,tuple(bounds),phase_bounds,tuple(reasons)))
    return lo,hi,tuple(spans),passages,tuple(uncertain)
