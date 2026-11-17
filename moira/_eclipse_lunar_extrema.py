"""Separate continuous-reference lunar extrema with curvature enclosures.

Axis distance, angular opposition and each overlap margin are independent
objectives. Exact interval chain rules propagate the frozen model's first
derivatives and conservative second-derivative bounds. Only a nonzero
curvature enclosure and a stationary-root witness prove uniqueness.
"""
from dataclasses import dataclass
from fractions import Fraction as F

from ._eclipse_continuous_lunar import ContinuousLunarVectorBounds, enclose_continuous_lunar_reference
from ._eclipse_continuous_lunar_contacts import _radii
from ._eclipse_interval import IntervalBudgetError, RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable, RootCell, isolate_roots
from ._eclipse_inverse_trig import asin_enclosure, atan_enclosure
from ._eclipse_lunar_acceleration import bound_lunar_reference_accelerations
from .constants import EARTH_RADIUS_KM, MOON_RADIUS_KM, SUN_RADIUS_KM


@dataclass(frozen=True, slots=True)
class LunarObservableJets:
    """Five separately named value, first-rate and curvature enclosures."""

    domain: I
    names: tuple[str, ...]
    values: tuple[I, ...]
    rates: tuple[I, ...]
    curvatures: tuple[I, ...]


@dataclass(frozen=True, slots=True)
class LunarStationaryPartition:
    """Cover every potential stationary point for one declared objective."""

    domain: I
    objective: str
    cells: tuple[RootCell, ...]
    tolerance: I

    @property
    def complete(self):
        """Whether every cell excludes a stationary point or proves uniqueness."""
        return all(cell.status in ('excluded', 'unique') for cell in self.cells)

    @property
    def resolution_reached(self):
        """Whether every retained stationary box meets the requested width."""
        return all(cell.status == 'excluded' or cell.interval.width <= self.tolerance.hi
                   for cell in self.cells)


@dataclass(frozen=True, slots=True)
class LunarExtremaCoverage:
    """Independent stationary covers, never an interchangeable greatest epoch."""

    domain: I
    policy: str
    partitions: tuple[LunarStationaryPartition, ...]
    evaluations: int
    max_evaluations: int
    serving_evaluator_enclosed: bool = False
    physical_accuracy_certified: bool = False


def bound_lunar_observable_jets(vectors: ContinuousLunarVectorBounds, accelerations, *,
                                policy: str, earth_radius_km=EARTH_RADIUS_KM,
                                sun_radius_km=SUN_RADIUS_KM, moon_radius_km=MOON_RADIUS_KM,
                                precision_bits=128):
    """Enclose five exact-real objectives and their first two TT derivatives.

    Product/quotient, norm, asin and atan derivatives are applied to the same
    mathematical vectors, not finite differences of sampled results. The
    acceleration receipt must cover the requested domain. Axis singularities,
    ambiguous cone nappes and unsupported angular domains remain unavailable.
    """
    if not isinstance(vectors, ContinuousLunarVectorBounds):
        raise TypeError('continuous lunar vectors required')
    if not vectors.continuous_on_domain or not vectors.differentiable_on_domain:
        raise EnclosureUnavailable('continuous differentiable vector model not established')
    if vectors.tt_offset_days.lo < accelerations.domain.lo or vectors.tt_offset_days.hi > accelerations.domain.hi:
        raise ValueError('curvature domain outside frozen acceleration bound')
    if type(precision_bits) is not int or not 64 <= precision_bits <= 256:
        raise ValueError('invalid curvature precision')
    re, rs, rm = _radii(earth_radius_km, sun_radius_km, moon_radius_km)

    def q(value):
        return value.quantize_outward(precision_bits)

    def scalar(value):
        return I.point(value), I.point(0), I.point(0)

    def add(a, b):
        return tuple(q(x+y) for x, y in zip(a, b))

    def neg(a):
        return tuple(-x for x in a)

    def sub(a, b):
        return add(a, neg(b))

    def mul(a, b):
        return q(a[0]*b[0]), q(a[1]*b[0]+a[0]*b[1]), q(a[2]*b[0]+2*a[1]*b[1]+a[0]*b[2])

    def square(a):
        return q(a[0].square()), q(2*a[0]*a[1]), q(2*a[1].square()+2*a[0]*a[2])

    def inv(a):
        if a[0].contains_zero:
            raise EnclosureUnavailable('reference curvature denominator may vanish')
        return q(1/a[0]), q(-a[1]/a[0].square()), q(2*a[1].square()/(a[0]**3)-a[2]/a[0].square())

    def div(a, b):
        return mul(a, inv(b))

    def sqrt(a):
        if a[0].lo <= 0:
            raise EnclosureUnavailable('reference norm curvature not proved away from zero')
        value = a[0].sqrt(precision_bits)
        return value, q(a[1]/(2*value)), q(a[2]/(2*value)-a[1].square()/(4*(value**3)))

    def asin(a):
        if a[0].lo <= -1 or a[0].hi >= 1:
            raise EnclosureUnavailable('angular curvature domain not proved')
        c = (1-a[0].square()).sqrt(precision_bits)
        return (asin_enclosure(a[0], precision_bits=precision_bits), q(a[1]/c),
                q(a[2]/c+a[0]*a[1].square()/(c**3)))

    def atan(a):
        d = 1+a[0].square()
        return (atan_enclosure(a[0], precision_bits=precision_bits), q(a[1]/d),
                q(a[2]/d-2*a[0]*a[1].square()/d.square()))

    def dot(a, b):
        result = scalar(0)
        for x, y in zip(a, b):
            result = add(result, mul(x, y))
        return result

    def norm(a):
        result = scalar(0)
        for x in a:
            result = add(result, square(x))
        return sqrt(result)

    def vector(values, rates, absolute):
        if len(values) != 3 or len(rates) != 3 or len(absolute) != 3 or any(a < 0 for a in absolute):
            raise ValueError('invalid vector acceleration components')
        return tuple((x, v, I(-a, a)) for x, v, a in zip(values, rates, absolute))

    sun = vector(vectors.sun_geocentric_km, vectors.sun_derivative_km_per_tt_day, accelerations.sun)
    moon = vector(vectors.moon_geocentric_km, vectors.moon_derivative_km_per_tt_day, accelerations.moon)
    ds, dm = norm(sun), norm(moon)
    if ds[0].lo <= rs+re or dm[0].lo <= re+rm:
        raise EnclosureUnavailable('curvature source domains not proved')
    z = neg(div(dot(sun, moon), ds))
    if z[0].lo <= 0:
        raise EnclosureUnavailable('antisolar curvature domain not proved')
    cross = (sub(mul(moon[1], sun[2]), mul(moon[2], sun[1])),
             sub(mul(moon[2], sun[0]), mul(moon[0], sun[2])),
             sub(mul(moon[0], sun[1]), mul(moon[1], sun[0])))
    radial = div(norm(cross), ds)
    theta = atan(div(radial, z))
    if policy == 'danjon_angular':
        pm, alpha = asin(div(scalar(re), dm)), asin(div(scalar(rm), dm))
        ss, ps = asin(div(scalar(rs), ds)), asin(div(scalar(re), ds))
        base = add(mul(scalar(F.from_float(1.01)), pm), ps)
        bp, bu = add(base, ss), sub(base, ss)
        if bu[0].lo <= 0 or (bp[0]+alpha[0]).hi >= 3:
            raise EnclosureUnavailable('angular-circle curvature domain not proved')
        margins = sub(add(bp, alpha), theta), sub(add(bu, alpha), theta), sub(sub(bu, alpha), theta)
    elif policy == 'static_finite_cone':
        if z[0].lo-rm < re:
            raise EnclosureUnavailable('downstream curvature domain not proved')
        p, u = div(scalar(rs+re), ds), div(scalar(rs-re), ds)
        cp, cu = sqrt(sub(scalar(1), square(p))), sqrt(sub(scalar(1), square(u)))
        pen = add(sub(add(scalar(re), mul(p, z)), mul(cp, radial)), scalar(rm))
        t = sub(div(scalar(re), u), z)
        branch = add(t, mul(div(u, cu), radial))[0]
        if branch.lo > 0:
            clearance = sub(sub(scalar(re), mul(u, z)), mul(cu, radial))
        elif branch.hi < 0:
            clearance = neg(norm((t, radial)))
        else:
            raise EnclosureUnavailable('umbral curvature nappe branch not proved')
        margins = pen, add(clearance, scalar(rm)), sub(clearance, scalar(rm))
    else:
        raise ValueError('unknown lunar policy')
    objectives = (radial, theta, *margins)
    return LunarObservableJets(vectors.tt_offset_days,
        ('axis_distance', 'angular_opposition', 'penumbral_overlap', 'umbral_overlap', 'total_overlap'),
        tuple(x[0] for x in objectives), tuple(x[1] for x in objectives), tuple(x[2] for x in objectives))


def isolate_lunar_reference_extrema(model, domain: I, *, policy: str, tolerance,
                                   earth_radius_km=EARTH_RADIUS_KM, max_evaluations=5000,
                                   max_depth=80):
    """Cover and isolate each objective's stationary points independently.

    One frozen-record acceleration calculation precedes a shared budget of
    vector/observable callback evaluations. Unknown norm or curvature regions
    are subdivided and retained. A unique root's curvature sign identifies a
    local minimum/maximum; a narrow unresolved cell does not establish either.
    """
    if not isinstance(domain, I) or domain.lo < model.tt_offset_days.lo or domain.hi > model.tt_offset_days.hi:
        raise ValueError('extrema domain outside frozen reference')
    tol = I.point(tolerance)
    if tol.lo != tol.hi or tol.lo <= 0:
        raise ValueError('positive exact extrema tolerance required')
    if (type(max_evaluations) is not int or max_evaluations < 0
            or type(max_depth) is not int or not 0 <= max_depth <= 256):
        raise ValueError('invalid extrema budget')
    if policy not in ('danjon_angular', 'static_finite_cone'):
        raise ValueError('unknown lunar policy')
    acceleration = bound_lunar_reference_accelerations(model)
    cache, count = {}, 0

    def observe(box):
        nonlocal count
        key = box.lo, box.hi
        if key not in cache:
            if count >= max_evaluations:
                raise EnclosureUnavailable('extrema evaluation budget exhausted')
            count += 1
            cache[key] = bound_lunar_observable_jets(
                enclose_continuous_lunar_reference(model, box), acceleration, policy=policy,
                earth_radius_km=earth_radius_km, precision_bits=model.precision_bits,
            )
        return cache[key]

    partitions = []
    names = ('axis_distance', 'angular_opposition', 'penumbral_overlap', 'umbral_overlap', 'total_overlap')
    for index, name in enumerate(names):
        stack, cells = [(domain, 0)], []
        while stack:
            box, depth = stack.pop()
            reason = 'stationary root not proved'
            try:
                jet = observe(box)
                if not jet.rates[index].contains_zero:
                    cells.append(RootCell(box, 'excluded', 'first_derivative_excludes_zero',
                                          jet.rates[index], jet.curvatures[index]))
                    continue
                if box.width <= tol.hi or depth >= max_depth:
                    result = isolate_roots(
                        box, lambda part: observe(part).rates[index], tolerance=tol,
                        unit='TT day offset', time_scale='TT', continuous=True,
                        derivative=lambda part: observe(part).curvatures[index],
                        max_evaluations=8, max_depth=0,
                    )
                    cells.extend(result.cells)
                    continue
            except (EnclosureUnavailable, IntervalBudgetError) as exc:
                reason = str(exc)
                if box.width <= tol.hi or depth >= max_depth or count >= max_evaluations:
                    cells.append(RootCell(box, 'unresolved', reason))
                    continue
            middle = box.midpoint
            stack.extend(((I(middle, box.hi), depth+1), (I(box.lo, middle), depth+1)))
        partitions.append(LunarStationaryPartition(domain, name,
            tuple(sorted(cells, key=lambda cell: (cell.interval.lo, cell.interval.hi))), tol))
    return LunarExtremaCoverage(domain, policy, tuple(partitions), count, max_evaluations)
