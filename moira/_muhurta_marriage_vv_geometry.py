"""VV8.1-5 quadrant-trisector centers, sandhis and interval crossings.

The historical rising-time approximation is replaced by the admitted exact
Ascendant/MC owners. This explicit adapter preserves the chapter's rule that
either chart's adverse testimony survives the other chart's favorable one.
"""
from fractions import Fraction
from math import floor, inf, nextafter

from .panchanga_shuddhi import ShuddhiBoundary
from ._muhurta_marriage_enclosure import EnclosureUnavailable


def bhava_centers(asc,mc):
    arc=(mc+180-asc)%360
    if not 0<arc<180:
        raise ValueError('VV bhava quadrants require ordered subpolar Ascendant/MC')
    return tuple((asc+_offset(i,arc))%360 for i in range(12))


def _offset(i,arc):
    quadrant,part=divmod(i,3)
    if quadrant==0:
        return arc*part/3
    if quadrant==1:
        return arc+(180-arc)*part/3
    if quadrant==2:
        return 180+arc*part/3
    return 180+arc+(180-arc)*part/3


def bhava_sandhis(asc,mc):
    arc=(mc+180-asc)%360
    bhava_centers(asc,mc)
    return tuple((asc+(_offset(i,arc)+(_offset(i+1,arc) if i<11 else 360))/2)%360 for i in range(12))


def bhava_house(longitude,asc,mc):
    if None in (longitude,asc,mc):
        return None
    edges=bhava_sandhis(asc,mc)
    for i,end in enumerate(edges):
        start=edges[(i-1)%12]
        if longitude==start or longitude==end:
            return None  # Source8.3 assigns no house fruit exactly on sandhi.
        if (longitude-start)%360<(end-start)%360:
            return i+1
    raise ValueError('VV sandhis do not cover the zodiac')


def _coefficients(index):
    # Exact affine offset from Ascendant: c*IC_arc + d degrees.
    def pair(i):
        if i==12:
            return Fraction(0),Fraction(360)
        q,r=divmod(i,3)
        return ((Fraction(r,3),Fraction(180*(q//2))) if q%2==0 else
                (1-Fraction(r,3),Fraction(180*(q//2)+60*r)))
    c,d=pair(index)
    x,y=pair(index+1)
    return (c+x)/2,(d+y)/2


def _signal(ctx,planet,index,a,b,coarse):
    from ._muhurta_marriage_certification import Signal
    from ._muhurta_marriage_enclosure import Interval as I
    cert=ctx.certifier
    asc=cert.angular_signal((('Lagna',1),),a,b,coarse)
    mc=cert.angular_signal((('Midheaven',1),),a,b,coarse)
    body=cert.angular_signal(((planet,1),),a,b,coarse)
    mid=(a+b)/2
    raw=ctx.midheaven(mid)+180-ctx.lagna(mid)
    turns=floor(raw/360)
    arc=mc.value+180-asc.value-360*turns
    if arc.lo<=0 or arc.hi>=180:
        raise EnclosureUnavailable('vv_bhava_quadrant_branch_requires_subdivision')
    c,d=_coefficients(index)
    ci=I.point(c.numerator)/c.denominator
    di=I.point(d.numerator)/d.denominator
    edge=asc.value+ci*arc+di
    reference=ctx.lagna(mid)+float(c)*(raw-360*turns)+float(d)
    shift=360*floor((ctx.longitude_at(planet,mid)-reference+180)/360)
    value=body.value-edge-shift
    rate=body.rate-asc.rate-ci*(mc.rate-asc.rate)
    center=None if any(x.center is None for x in (asc,mc,body)) else (
        body.center-asc.center-ci*(mc.center+180-asc.center-360*turns)-di-shift)
    return Signal(value,rate,center)


def boundaries(ctx,lo,hi):
    """Every planet/sandhi crossing receives a serving polynomial certificate."""
    from ._muhurta_marriage_sources import NINE
    if ctx.lagna((lo+hi)/2) is None:
        ctx.reasons.append('vv_bhava_subpolar_geometry_unavailable')
        return ()
    result=[]
    for planet in NINE:
        for index in range(12):
            kind=f'vv_bhava_{planet}_{index+1}'
            scan=ctx.certifier.scalar(lambda a,b,c,p=planet,i=index:_signal(ctx,p,i,a,b,c),
                                     lo,hi,min(1/96,hi-lo),kind)
            ctx.reasons.extend(kind+':'+reason for _,_,reason in scan.unresolved)
            for root in scan.roots:
                a,b=nextafter(root.lower,-inf),nextafter(root.upper,inf)
                def residual(t):
                    edge=bhava_sandhis(ctx.lagna(t),ctx.midheaven(t))[index]
                    return (ctx.longitude_at(planet,t)-edge+180)%360-180
                va,vb=residual(a),residual(b)
                if va*vb>0 or va==vb:
                    ctx.reasons.append(kind+':raw_crossing_witness_unresolved')
                    continue
                ctx.meter.tick('transitions')
                result.append(ShuddhiBoundary(kind,(a+b)/2,a,b))
    return tuple(result)
