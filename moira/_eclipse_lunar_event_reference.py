"""Joint contact and stationary-point coverage for one frozen lunar model.

All eight scalar partitions share immutable vector/jet bounds and one counted
vector budget. Mean-value enclosures tighten natural interval expressions;
they never replace a source, continuity, singularity or curvature obligation.
These are exact-polynomial reference conclusions, not serving certificates.
"""
from dataclasses import dataclass, replace

from ._eclipse_continuous_lunar import ContinuousLunarReference, enclose_continuous_lunar_reference
from ._eclipse_interval import IntervalBudgetError, RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable, RootCell, isolate_roots
from ._eclipse_lunar_acceleration import bound_lunar_reference_accelerations
from ._eclipse_lunar_extrema import bound_lunar_observable_jets
from .constants import EARTH_RADIUS_KM


@dataclass(frozen=True, slots=True)
class LunarEventScalarPartition:
    """Closed-domain contact or stationary cover for one named observable.

    ``value_unit`` labels the observable itself. For stationary partitions,
    a root cell's value is its first TT derivative, and its derivative is
    the second TT derivative. ``root_function_unit`` names that distinction.
    """

    domain: I
    objective: str
    kind: str
    value_unit: str
    cells: tuple[RootCell, ...]
    tolerance: I

    @property
    def root_function_unit(self):
        """Unit of each root cell's value, including its derivative order."""
        return self.value_unit if self.kind == 'contact' else self.value_unit+' per TT day'

    @property
    def complete(self):
        """Whether every cell excludes a root or proves exactly one."""
        return all(cell.status in ('excluded', 'unique') for cell in self.cells)

    @property
    def resolution_reached(self):
        """Whether every retained root box meets the requested width."""
        return all(cell.status == 'excluded' or cell.interval.width <= self.tolerance.hi
                   for cell in self.cells)


@dataclass(frozen=True, slots=True)
class LunarReferenceEventCoverage:
    """Eight independent partitions sharing a frozen reference and budget."""

    domain: I
    policy: str
    partitions: tuple[LunarEventScalarPartition, ...]
    vector_evaluations: int
    max_vector_evaluations: int
    serving_evaluator_enclosed: bool = False
    physical_accuracy_certified: bool = False

    @property
    def complete(self):
        """Whether all contacts and stationary points are covered completely."""
        return all(part.complete for part in self.partitions)


def _taylor_vectors(anchor, domain, acceleration):
    """Translate a point vector bound using the whole-model acceleration.

    For h=t-t0, x(t) is enclosed by x(t0)+h*x'(t0)+h**2*[-A,A]/2,
    and x'(t) by x'(t0)+h*[-A,A]. The integral Taylor remainder holds
    on both sides of t0. Clock usages in the result identify the evaluated
    anchor; whole-interval inclusion comes from the frozen acceleration
    receipt, rather than evaluating clocks at every time in the interval.
    """
    if anchor.tt_offset_days.width:
        raise ValueError('Taylor anchor must be a point enclosure')
    hull = I(min(anchor.tt_offset_days.lo, domain.lo), max(anchor.tt_offset_days.hi, domain.hi))
    if hull.lo < acceleration.domain.lo or hull.hi > acceleration.domain.hi:
        raise ValueError('Taylor translation leaves acceleration domain')
    h = domain-anchor.tt_offset_days.lo

    def translate(values, rates, bounds):
        remainder = tuple(I(-bound, bound) for bound in bounds)
        positions = tuple((x+h*v+h.square()*a/2).quantize_outward(128)
                          for x, v, a in zip(values, rates, remainder))
        velocities = tuple((v+h*a).quantize_outward(128) for v, a in zip(rates, remainder))
        return positions, velocities

    sun, sv = translate(anchor.sun_geocentric_km, anchor.sun_derivative_km_per_tt_day, acceleration.sun)
    moon, mv = translate(anchor.moon_geocentric_km, anchor.moon_derivative_km_per_tt_day, acceleration.moon)
    return replace(anchor, tt_offset_days=domain, sun_geocentric_km=sun, moon_geocentric_km=moon,
                   sun_derivative_km_per_tt_day=sv, moon_derivative_km_per_tt_day=mv)


def isolate_lunar_reference_event(model: ContinuousLunarReference, domain: I, *,
                                  policy: str, tolerance,
                                  earth_radius_km=EARTH_RADIUS_KM,
                                  max_vector_evaluations: int = 5000,
                                  max_depth: int = 80) -> LunarReferenceEventCoverage:
    """Cover every contact and each distinct stationary objective on a domain.

    The frozen source must support a continuous twice differentiable reference
    on each resolved cell. Unsupported wide boxes subdivide; source seams,
    singularities, exact degeneracies and exhausted budgets retain their full
    affected domains. Midpoint Taylor bounds use whole-cell derivative and
    curvature bounds with the mean-value theorem. A midpoint sample alone
    never excludes time. Neither event identity nor an external catalog type
    is inferred from a seed. Radii and the model policy remain explicit.
    """
    if not isinstance(model, ContinuousLunarReference) or not isinstance(domain, I):
        raise TypeError('frozen lunar model and exact TT domain required')
    if domain.lo < model.tt_offset_days.lo or domain.hi > model.tt_offset_days.hi:
        raise ValueError('event domain outside frozen reference')
    if policy not in ('danjon_angular', 'static_finite_cone'):
        raise ValueError('unknown lunar policy')
    tol = I.point(tolerance)
    if tol.lo != tol.hi or tol.lo <= 0:
        raise ValueError('positive exact event tolerance required')
    if (type(max_vector_evaluations) is not int or max_vector_evaluations < 0
            or type(max_depth) is not int or not 0 <= max_depth <= 256):
        raise ValueError('invalid event coverage budget')
    radius = I.point(earth_radius_km)
    if radius.lo != radius.hi or radius.lo <= 0:
        raise ValueError('positive exact Earth radius required')
    names = ('axis_distance', 'angular_opposition', 'penumbral_overlap',
             'umbral_overlap', 'total_overlap')
    requests = tuple((index, 'contact') for index in (2, 3, 4)) + tuple(
        (index, 'stationary') for index in range(5))
    cache, anchors, evaluations = {}, {}, 0
    try:
        acceleration = bound_lunar_reference_accelerations(model)
    except (EnclosureUnavailable, IntervalBudgetError) as exc:
        partitions = tuple(LunarEventScalarPartition(domain, names[index], kind,
            'km' if index == 0 or policy == 'static_finite_cone' and index > 1 else 'rad',
            (RootCell(domain, 'unresolved', 'acceleration_enclosure_unavailable: '+str(exc)),), tol)
            for index, kind in requests)
        return LunarReferenceEventCoverage(domain, policy, partitions, 0, max_vector_evaluations)

    def observe(box):
        nonlocal evaluations
        key = box.lo, box.hi
        if key not in cache:
            try:
                nearest = min(anchors, key=lambda t: abs(t-box.midpoint)) if anchors else None
                if nearest is None or abs(nearest-box.midpoint) > 8*box.width:
                    if evaluations >= max_vector_evaluations:
                        raise EnclosureUnavailable('shared_vector_budget_exhausted')
                    evaluations += 1
                    nearest = box.midpoint
                    anchors[nearest] = enclose_continuous_lunar_reference(model, I.point(nearest))
                vectors = _taylor_vectors(anchors[nearest], box, acceleration)
                cache[key] = bound_lunar_observable_jets(vectors, acceleration,
                    policy=policy, earth_radius_km=radius.lo, precision_bits=model.precision_bits)
            except (EnclosureUnavailable, IntervalBudgetError) as exc:
                cache[key] = exc
        if isinstance(cache[key], Exception):
            raise cache[key]
        return cache[key]

    def scalar(box, index, kind):
        jet = observe(box)
        value = jet.values[index] if kind == 'contact' else jet.rates[index]
        derivative = jet.rates[index] if kind == 'contact' else jet.curvatures[index]
        if value.contains_zero and box.width:
            center = observe(I.point(box.midpoint))
            center_value = center.values[index] if kind == 'contact' else center.rates[index]
            mean_value = center_value + derivative*I(-box.width/2, box.width/2)
            tightened = value.intersect(mean_value)
            if tightened is None:
                raise ArithmeticError('natural and mean-value bounds disagree')
            value = tightened
        return value, derivative

    partitions = []
    for index, kind in requests:
        stack, cells = [(domain, 0)], []
        while stack:
            box, depth = stack.pop()
            reason = 'root_existence_not_established'
            try:
                value, derivative = scalar(box, index, kind)
                if not value.contains_zero:
                    cells.append(RootCell(box, 'excluded', 'whole_interval_bound_excludes_zero',
                                          value, derivative))
                    continue
                if box.width <= tol.hi or depth >= max_depth:
                    roots = isolate_roots(box, lambda part: scalar(part, index, kind)[0],
                        derivative=lambda part: scalar(part, index, kind)[1],
                        tolerance=tol, unit='TT day offset', time_scale='TT',
                        continuous=True, max_depth=0, max_evaluations=8)
                    cells.extend(roots.cells)
                    continue
            except (EnclosureUnavailable, IntervalBudgetError) as exc:
                reason = str(exc)
                if box.width <= tol.hi or depth >= max_depth or evaluations >= max_vector_evaluations:
                    cells.append(RootCell(box, 'unresolved', reason))
                    continue
            middle = box.midpoint
            stack.extend(((I(middle, box.hi), depth+1), (I(box.lo, middle), depth+1)))
        unit = 'km' if index == 0 or policy == 'static_finite_cone' and index > 1 else 'rad'
        partitions.append(LunarEventScalarPartition(domain, names[index], kind, unit,
            tuple(sorted(cells, key=lambda cell: (cell.interval.lo, cell.interval.hi))), tol))
    return LunarReferenceEventCoverage(domain, policy, tuple(partitions), evaluations,
                                       max_vector_evaluations)
