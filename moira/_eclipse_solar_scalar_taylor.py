"""Scalar solar-radius Taylor bounds retain time correlation at flat maxima.

The point jet and whole-box curvature come from the same explicit continuous
solar model. The contractor is used only inside one smooth clock/polar/source
branch and strictly inside an intersecting component. All other boxes retain
the original conservative enclosure. This does not modify the model or make
rounded serving evaluation continuous.
"""
from dataclasses import replace
from fractions import Fraction as F
import bisect

from ._eclipse_interval import RationalInterval as I
from ._eclipse_continuous_solar_stage3 import continuous_solar_stage3_provider
from . import julian


def _smooth_clock_and_polar(scope,domain):
    absolute = I.point(scope.ut1_anchor_jd)+domain
    clock = scope.clock
    if clock.branch=='direct_eop':
        if not any(F.from_float(start)<absolute.lo<=absolute.hi<F.from_float(end)
                   for start,_,end,_ in clock.eop_segments):
            return False
    else:
        lower,upper = absolute.to_float_bounds()
        first,last = julian.calendar_from_jd(lower)[0],julian.calendar_from_jd(upper)[0]
        if first!=last:
            return False
        if clock.branch=='historical_hpiers':
            start,end = map(lambda y:F.from_float(julian.julian_day(y,1,1)),(first,first+1))
            years = first+(absolute-start)/(end-start)
            if not any(F.from_float(a)<years.lo<=years.hi<F.from_float(b)
                       for (a,_),(b,_) in zip(clock.hpiers_rows,clock.hpiers_rows[1:])):
                return False
    rows = scope.polar_rows
    if not rows:
        return True
    mjd = absolute-F(4800001,2)
    if mjd.hi<F.from_float(rows[0][0]) or mjd.lo>F.from_float(rows[-1][0]):
        return True
    values = tuple(row[0] for row in rows)
    index = bisect.bisect_right(values,mjd.lo)-1
    return (0<=index<len(rows)-1 and F.from_float(rows[index][0])<mjd.lo<=mjd.hi
            <F.from_float(rows[index+1][0]))


def scalar_taylor_solar_provider(scope, *, progress=None):
    """Return an equivalent tightened provider with request-local point jets."""
    jets,points = {},{}

    def retain(domain,discriminant,radius):
        jets[domain] = discriminant,radius

    base,stats = continuous_solar_stage3_provider(scope,progress=progress,jet_observer=retain)
    stats['scalar_taylor_contractions'] = 0

    def enclosure(domain):
        value = base(domain)
        jet = jets.pop(domain)[1]
        if (jet is None or not value.real_continuous_model or value.signed_radius is None
                or not value.signed_radius.contains_zero or not _smooth_clock_and_polar(scope,domain)):
            return value
        near = min(points,key=lambda p:abs(p-domain.midpoint)) if points else None
        # A point jet must lie inside this smooth box; otherwise its Taylor
        # remainder would cross an unproved source or policy branch.
        if near is None or not domain.contains(near):
            near = domain.midpoint
            point_domain = I.point(near)
            point = base(point_domain)
            point_jet = jets.pop(point_domain)[1]
            if point_jet is None or not point.real_continuous_model:
                return value
            points[near] = point_jet
        point_jet = points[near]
        h = domain-near
        taylor = (point_jet[0]+point_jet[1]*h+jet[2]*h.square()/2).quantize_outward(128)
        rate = (point_jet[1]+jet[2]*h).quantize_outward(128)
        bounded = value.signed_radius.intersect(taylor)
        derivative = value.radius_derivative.intersect(rate)
        if bounded is None or derivative is None:
            raise ArithmeticError('scalar solar Taylor inclusion disagrees with the original jet')
        stats['scalar_taylor_contractions'] += 1
        return replace(value,signed_radius=bounded,radius_derivative=derivative)
    return enclosure,stats
