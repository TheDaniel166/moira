"""Request-owned extra histories; only admitted profile dependencies are searched."""
from dataclasses import fields
from itertools import combinations
from math import inf,nextafter

from ._muhurta_marriage_tradition_history import (MarriageTraditionHistory,MarriageAngularHistoryEvent,
    MarriageDeclinationEvent,MarriageShadowSample,MarriageShadowContact,MarriageEclipseInterval)
from ._muhurta_marriage_tradition_geometry import eclipse_signal,declination_signal
from ._muhurta_marriage_tradition_sources import VV,KP
from .muhurta_marriage import MarriageExtent
from .panchanga_shuddhi import ShuddhiBoundary


def shadow_sample(ctx,kind,jd):
    from .eclipse import _earth_barycentric,_barycentric,_geocentric,apply_light_time
    from .constants import Body
    tt=ctx.epoch(jd).epoch_tt
    earth=_earth_barycentric(tt,ctx.reader)
    sun,_=apply_light_time(Body.SUN,tt,ctx.reader,earth,_barycentric)
    moon=(apply_light_time(Body.MOON,tt,ctx.reader,earth,_barycentric)[0] if kind=='solar' else _geocentric(Body.MOON,tt,ctx.reader))
    return MarriageShadowSample(jd,kind,tuple(sun),tuple(moon),ctx.longitude_at('Moon',jd))


def declinations(ctx,jd):
    from .coordinates import ecliptic_to_equatorial
    from .obliquity import mean_obliquity,nutation
    tt=ctx.epoch(jd).epoch_tt
    eps=mean_obliquity(tt)+nutation(tt)[1]
    return tuple(ecliptic_to_equatorial(ctx.body(body,jd).longitude,ctx.body(body,jd).latitude,eps)[1] for body in ('Sun','Moon'))


def _scalar_edges(ctx,signal,lo,hi,kind,step):
    scan=ctx.certifier.scalar(signal,lo,hi,step,kind)
    ctx.reasons.extend(kind+':'+why for _,_,why in scan.unresolved)
    edges=[]
    for root in scan.roots:
        a,b=nextafter(root.lower,-inf),nextafter(root.upper,inf)
        ctx.meter.tick('transitions')
        edges.append(ShuddhiBoundary(kind,(a+b)/2,a,b))
    return edges


def _angular_event(ctx,kind,root,first,second=None):
    edge=root.boundary
    a,b=edge.lower_jd_ut1,edge.upper_jd_ut1
    return MarriageAngularHistoryEvent(kind,edge,first,second,root.target_degrees,
        ctx.longitude_at(first,a),ctx.longitude_at(first,b),
        None if second is None else ctx.longitude_at(second,a),None if second is None else ctx.longitude_at(second,b))


def admit_history_budget(profile, limits, radius=0.):
    """Admit the exact supplemental span before any serving-reader work."""
    if profile not in (VV,KP):
        return None
    from ._muhurta_marriage_search import MarriageSearchBudgetError
    days = 70 if profile==VV else 5
    required = days+radius+3
    if required > limits.max_history_days:
        raise MarriageSearchBudgetError('history_days',limits.max_history_days,required,'additional_tradition_preflight')
    # The public history vessel admits at most90 days. Include both halves
    # of a requested range so an impossible span fails before its searches.
    if days+2*radius+3 > 90:
        raise MarriageSearchBudgetError('range_days',90-days-3,2*radius,'additional_tradition_preflight')
    return days


def enrich(ctx,base,jd):
    cached=getattr(ctx,'additional_tradition_history',None)
    if cached is not None:
        return cached
    anchor=jd if ctx.range_anchor is None else ctx.range_anchor
    radius=ctx.range_radius
    vv=ctx.policy.profile==VV
    days=admit_history_budget(ctx.policy.profile,ctx.meter.limits,radius)
    lo,hi=anchor-days-radius,anchor+3+radius
    ctx.history_extents.append(('VV_additional_history' if vv else 'KP_additional_history',lo,hi))
    navamsas=[]
    conjunctions=[]
    declination_events=[]
    eclipses=[]
    if vv:
        for first,second in combinations(('Mars','Mercury','Jupiter','Venus','Saturn'),2):
            roots=ctx.angular(((first,1),(second,-1)),lo,hi,(0.,),1.,'VV_bheda_'+first+'_'+second)
            conjunctions.extend(_angular_event(ctx,'planetary_conjunction',r,first,second) for r in roots)
        for edge in _scalar_edges(ctx,lambda a,b,c:declination_signal(ctx,a,b,c),anchor-radius-3,hi,'VV_krantisamya',.5):
            a,b=edge.lower_jd_ut1,edge.upper_jd_ut1
            left,right=declinations(ctx,a),declinations(ctx,b)
            try:
                declination_events.append(MarriageDeclinationEvent(edge,*left,*right,ctx.longitude_at('Moon',a),ctx.longitude_at('Moon',b)))
            except ValueError:
                ctx.reasons.append('VV_krantisamya:raw_crossing_not_resolved')
    else:
        roots=ctx.angular((('Sun',1),),lo,hi,tuple(i*360/108 for i in range(108)),1.,'KP_solar_navamsa')
        navamsas.extend(_angular_event(ctx,'solar_navamsa',r,'Sun') for r in roots)
    coverage_lo,coverage_hi=lo,hi
    for kind in ('solar','lunar_umbral'):
        edges=_scalar_edges(ctx,lambda a,b,c,k=kind:eclipse_signal(ctx,k,a,b,c),lo,hi,kind+'_global_contact',.5)
        contacts=[]
        for edge in edges:
            a,b=shadow_sample(ctx,kind,edge.lower_jd_ut1),shadow_sample(ctx,kind,edge.upper_jd_ut1)
            try:
                contacts.append(MarriageShadowContact(edge,a,b,'start' if b.signal<a.signal else 'end'))
            except ValueError:
                ctx.reasons.append(kind+':raw_shadow_crossing_not_resolved')
        if contacts and contacts[0].role=='end':
            coverage_lo=max(coverage_lo,contacts.pop(0).boundary.upper_jd_ut1)
        if contacts and contacts[-1].role=='start':
            coverage_hi=min(coverage_hi,contacts.pop().boundary.lower_jd_ut1)
        for a,b in zip(contacts[::2],contacts[1::2]):
            try:
                eclipses.append(MarriageEclipseInterval(a,b))
            except ValueError:
                ctx.reasons.append(kind+':shadow_contacts_do_not_alternate')
    extent=MarriageExtent(coverage_lo,coverage_hi)
    def inside(event):
        a,b=(event.start.boundary,event.end.boundary) if isinstance(event,MarriageEclipseInterval) else (event.boundary,event.boundary)
        return extent.start_jd_ut1<=a.lower_jd_ut1<=b.upper_jd_ut1<=extent.end_jd_ut1
    extra=dict(tradition_profile=ctx.policy.profile,additional_extent=extent,
        declination_extent=MarriageExtent(max(coverage_lo,anchor-radius-3),coverage_hi) if vv else None,
        solar_navamsa_entries=tuple(x for x in navamsas if inside(x)),
        conjunction_events=tuple(sorted((x for x in conjunctions if inside(x)),key=lambda x:x.boundary.jd_ut1)),
        declination_events=tuple(x for x in declination_events if inside(x)),
        eclipse_intervals=tuple(sorted((x for x in eclipses if inside(x)),key=lambda x:x.start.boundary.jd_ut1)))
    result=MarriageTraditionHistory(**{f.name:getattr(base,f.name) for f in fields(base) if f.init},**extra)
    ctx.additional_tradition_history=result
    return result
