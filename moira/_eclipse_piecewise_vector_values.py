"""Value-only raw-record bounds with correlated Earth/EMB cancellation.

    |T_n'(x)| <= n*n for -1<=x<=1

bounds each represented Chebyshev polynomial by its centre and a whole-record
derivative bound. The EMB difference uses its finite source jumps plus a
mean-value bound on the actual reception/emission separation. Ten finite
light-time updates remain ten updates; they are not replaced by convergence.
"""
from fractions import Fraction as F

from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_reference_clock import bound_continuous_reference_tdb
from ._eclipse_spk_bounds import _raw_seconds
from .constants import C_KM_PER_DAY


def _value(coefficients, x):
    a,b = F(0),F(0)
    for c in reversed(coefficients[1:]):
        a,b = 2*x*a-b+c,a
    return x*a-b+coefficients[0]


def bound_piecewise_vector_values(model, domain, *, retarded_moon=True):
    """Return Sun/Moon boxes including every owned record and finite update."""
    if domain.lo < model.domain.lo or domain.hi > model.domain.hi:
        raise ValueError('request outside frozen TT domain')
    records = {pair:tuple(r for r in model.records if r.pair==pair)
               for pair in ((0,3),(3,399),(3,301),(0,10))}

    def clock(tt):
        if tt.lo < model.domain.lo-model.horizon_days or tt.hi > model.domain.hi:
            raise EnclosureUnavailable('emission outside frozen horizon')
        return bound_continuous_reference_tdb(model.tt_anchor_jd,tt)

    def route(pair,tt):
        seconds = _raw_seconds(model.tt_anchor_jd,clock(tt).tdb_offset_days)
        options = [r for r in records[pair] if
                   seconds.hi >= r.midpoint_seconds-r.radius_seconds and
                   seconds.lo <= r.midpoint_seconds+r.radius_seconds]
        if (not options or seconds.lo < options[0].midpoint_seconds-options[0].radius_seconds or
                seconds.hi > options[-1].midpoint_seconds+options[-1].radius_seconds):
            raise EnclosureUnavailable('records do not cover source evaluation')
        if any(a.midpoint_seconds+a.radius_seconds != b.midpoint_seconds-b.radius_seconds
               for a,b in zip(options,options[1:])):
            raise EnclosureUnavailable('gap in copied source records')
        axes = []
        for axis in range(3):
            boxes = []
            for r in options:
                owned = seconds.intersect(I(r.midpoint_seconds-r.radius_seconds,
                                             r.midpoint_seconds+r.radius_seconds))
                x = (owned-r.midpoint_seconds)/r.radius_seconds
                coefficients = r.coefficients[axis]
                value = _value(coefficients,x.midpoint)
                derivative = sum(n*n*abs(c) for n,c in enumerate(coefficients))
                error = derivative*x.width/2
                boxes.append(I(value-error,value+error).quantize_outward(128))
            axes.append(I(min(b.lo for b in boxes),max(b.hi for b in boxes)))
        return tuple(axes)

    emb, earth_leg = route((0,3),domain),route((3,399),domain)
    moon_initial = tuple(m-e for m,e in zip(route((3,301),domain),earth_leg))
    earth = tuple(e+leg for e,leg in zip(emb,earth_leg))
    # All records and jumps on the frozen horizon are sufficient. Bounds are
    # deliberately allowed to overcount jumps outside an individual delay.
    emb_rates, jumps = [],[]
    for axis in range(3):
        emb_rates.append(max(sum(n*n*abs(c) for n,c in enumerate(r.coefficients[axis]))*
                             86400/r.radius_seconds for r in records[(0,3)]))
        jumps.append(sum(abs(_value(a.coefficients[axis],1)-_value(b.coefficients[axis],-1))
                         for a,b in zip(records[(0,3)],records[(0,3)][1:])))
    clock_rate = clock(domain).derivative_tdb_per_tt.hi
    speed = F.from_float(C_KM_PER_DAY)

    def delayed(body):
        vector = (tuple(s-e for s,e in zip(route((0,10),domain),earth))
                  if body=='sun' else moon_initial)
        for _ in range(10):
            delay = sum((v.square() for v in vector),I.point(0)).sqrt(160)/speed
            if delay.hi > model.horizon_days:
                raise EnclosureUnavailable('finite light delay outside horizon')
            emitted = domain-delay
            if body=='sun':
                vector = tuple(s-e for s,e in zip(route((0,10),emitted),earth))
            else:
                new_emb, leg = route((0,3),emitted),route((3,301),emitted)
                values = []
                for k in range(3):
                    error = emb_rates[k]*clock_rate*delay.hi+jumps[k]
                    difference = (new_emb[k]-emb[k]).intersect(I(-error,error))
                    if difference is None:
                        raise ArithmeticError('independent EMB bounds disagree')
                    values.append((difference+leg[k]-earth_leg[k]).quantize_outward(128))
                vector = tuple(values)
        return vector

    return delayed('sun'),delayed('moon') if retarded_moon else moon_initial
