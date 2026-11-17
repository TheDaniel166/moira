"""Whole-domain central-axis and hybrid sequence coverage.

The object is one explicitly supplied axis/ellipsoid function and its legal
near-side signed cone radius. Interval signs exclude complete cells; unique
root proofs and one-sided boundary phases establish a sequence. Unknown
seams, tangencies, horizon/forward order and budgets stay in the cover.
This machinery does not turn successful-output serving bounds into a
continuous physical model or a native route-totality attestation.
"""
from dataclasses import dataclass
from typing import Callable

from ._eclipse_interval import IntervalBudgetError, RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable, isolate_roots


@dataclass(frozen=True, slots=True)
class SolarAxisFunctionBounds:
    """Enclosures on one domain; phase/legality may be conditional on an axis.

    ``axis_margin`` is positive inside the ellipsoid intersection interval.
    ``signed_radius`` is positive for total and negative for annular.
    Positive forward/daylight margins establish a legal near-side axis.
    An exact-axis geometry provider may separately prove daylight on every
    strictly interior intersecting input even when its endpoint is horizon.
    Derivatives use the same time variable and the same continuous model.
    """

    domain: I
    axis_margin: I
    signed_radius: I | None
    forward_margin: I | None
    daylight_margin: I | None
    axis_derivative: I | None = None
    radius_derivative: I | None = None
    daylight_interior_proved: bool = False
    real_continuous_model: bool = False


@dataclass(frozen=True, slots=True)
class SolarPathCell:
    """One excluded, phase-resolved, root-proved or unresolved time cell."""

    domain: I
    kind: str
    reason: str
    phase: str | None = None


@dataclass(frozen=True, slots=True)
class SolarPathRoot:
    """A unique model root and its derivative-defined chronological direction."""

    function: str
    domain: I
    direction: str
    derivative: I
    boundary_phase: str | None = None


@dataclass(frozen=True, slots=True)
class SolarPathCoverage:
    """Model-specific window coverage and an optional complete path sequence.

    H1/H2/H3 require one fully enclosed legal central component, unique
    transitions, one-sided endpoint phases and complementary exclusions.
    Multiple components and clipped domains retain their separate intervals
    and do not inherit an invented NASA subtype. Physical/native attestation
    is never supplied by this result, including for analytic controls.
    """

    domain: I
    cells: tuple[SolarPathCell, ...]
    roots: tuple[SolarPathRoot, ...]
    status: str
    sequence: tuple[str, ...]
    subtype: str | None
    central_intervals: tuple[tuple[I, I], ...]
    coverage_complete: bool
    event_interval_enclosed: bool
    evaluations: int
    max_evaluations: int
    reason: str
    serving_route_totality_proved: bool = False
    physical_accuracy_certified: bool = False


def cover_solar_central_path(
    domain: I, enclosure: Callable[[I], SolarAxisFunctionBounds], *,
    tolerance, continuity_assumed: bool, max_evaluations: int = 4096,
    max_depth: int = 80,
) -> SolarPathCoverage:
    """Cover all legal-axis components, independently of greatest eclipse.

    A provider call is counted once even if its immutable result is reused
    by the root solver. No negative sample is an exclusion. Unique endpoint
    and transition roots require explicit continuous-model and derivative
    obligations. Exact tangencies can remain unresolved at any tolerance.
    Broad hybrid evidence can survive unresolved regions, while complete
    sequence/subtype admission cannot. Time scale/units belong to the caller.
    """
    if not isinstance(domain, I):
        raise TypeError('rational time domain required')
    tol = I.point(tolerance)
    if tol.lo != tol.hi or tol.lo <= 0:
        raise ValueError('positive exact time tolerance required')
    if type(continuity_assumed) is not bool:
        raise TypeError('continuity_assumed must be bool')
    if (type(max_evaluations) is not int or max_evaluations < 0
            or type(max_depth) is not int or not 0 <= max_depth <= 256):
        raise ValueError('invalid solar coverage budget')
    cache, count = {}, 0

    def observe(box):
        nonlocal count
        key = box.lo, box.hi
        if key not in cache:
            if count >= max_evaluations:
                raise EnclosureUnavailable('evaluation_budget_exhausted')
            count += 1
            value = enclosure(box)
            if not isinstance(value, SolarAxisFunctionBounds) or value.domain != box:
                raise TypeError('provider must retain the exact requested solar domain')
            if type(value.daylight_interior_proved) is not bool or type(value.real_continuous_model) is not bool:
                raise TypeError('solar proof declarations must be bool')
            for field in ('axis_margin', 'signed_radius', 'forward_margin', 'daylight_margin',
                          'axis_derivative', 'radius_derivative'):
                item = getattr(value, field)
                if not isinstance(item, I) and not (item is None and field != 'axis_margin'):
                    raise TypeError('solar function values must be rational intervals or explicit None')
            cache[key] = value
        return cache[key]

    def root_proof(box, function):
        field = 'axis_margin' if function == 'axis' else 'signed_radius'
        rate_field = 'axis_derivative' if function == 'axis' else 'radius_derivative'

        def value(part):
            result = observe(part)
            if not result.real_continuous_model:
                raise EnclosureUnavailable('continuous solar model not established')
            bounded = getattr(result, field)
            if bounded is None:
                raise EnclosureUnavailable('solar root value unavailable')
            return bounded

        def derivative(part):
            rate = getattr(observe(part), rate_field)
            if rate is None:
                raise EnclosureUnavailable('solar derivative unavailable')
            return rate

        roots = isolate_roots(
            box, value, tolerance=tol, unit='caller time coordinate',
            continuous=continuity_assumed, derivative=derivative,
            max_evaluations=8, max_depth=0,
        )
        if roots.complete and roots.resolution_reached and len(roots.cells) == 1:
            return roots.cells[0]
        return None

    stack, cells, roots = [(domain, 0)], [], []
    while stack:
        box, depth = stack.pop()
        reason = 'axis_phase_or_legality_not_proved'
        try:
            bounded = observe(box)
            d, k = bounded.axis_margin, bounded.signed_radius
            if d.hi < 0:
                cells.append(SolarPathCell(box, 'excluded', 'whole_interval_axis_misses'))
                continue
            forward, daylight = bounded.forward_margin, bounded.daylight_margin
            if ((forward is not None and forward.hi <= 0)
                    or (daylight is not None and daylight.hi <= 0 and not bounded.daylight_interior_proved)):
                cells.append(SolarPathCell(box, 'excluded', 'whole_interval_axis_not_legal'))
                continue
            legal = (forward is not None and forward.lo > 0
                     and ((daylight is not None and daylight.lo > 0) or bounded.daylight_interior_proved))
            phase = ('total' if k is not None and k.lo > 0 else
                     'annular' if k is not None and k.hi < 0 else None)
            if d.lo > 0 and legal and phase is not None:
                cells.append(SolarPathCell(box, 'phase', 'whole_interval_phase_sign', phase))
                continue
            if box.width <= tol.hi or depth >= max_depth:
                if legal and continuity_assumed:
                    if d.contains_zero and phase is not None:
                        proof = root_proof(box, 'axis')
                        if proof is not None and proof.status == 'excluded':
                            point = observe(I.point(box.lo)).axis_margin
                            if point.hi < 0:
                                cells.append(SolarPathCell(box, 'excluded', 'monotone_axis_exclusion'))
                                continue
                            if point.lo > 0:
                                cells.append(SolarPathCell(box, 'phase', 'monotone_axis_interior', phase))
                                continue
                        if proof is not None and proof.status == 'unique':
                            rate = proof.derivative
                            direction = 'entry' if rate.lo > 0 else 'exit'
                            roots.append(SolarPathRoot('axis', box, direction, rate, phase))
                            cells.append(SolarPathCell(box, 'endpoint', 'unique_axis_root_with_one_sided_phase', phase))
                            continue
                    elif d.lo > 0 and k is not None and k.contains_zero:
                        proof = root_proof(box, 'radius')
                        if proof is not None and proof.status == 'excluded':
                            point = observe(I.point(box.lo)).signed_radius
                            strict = ('total' if point is not None and point.lo > 0 else
                                      'annular' if point is not None and point.hi < 0 else None)
                            if strict is not None:
                                cells.append(SolarPathCell(box, 'phase', 'monotone_radius_exclusion', strict))
                                continue
                        if proof is not None and proof.status == 'unique':
                            rate = proof.derivative
                            direction = 'annular_to_total' if rate.lo > 0 else 'total_to_annular'
                            roots.append(SolarPathRoot('radius', box, direction, rate))
                            cells.append(SolarPathCell(box, 'transition', 'unique_signed_radius_root'))
                            continue
                cells.append(SolarPathCell(box, 'unresolved', reason))
                continue
        except (EnclosureUnavailable, IntervalBudgetError) as exc:
            reason = str(exc)
            if (box.width <= tol.hi or depth >= max_depth
                    or count >= max_evaluations or reason == 'evaluation_budget_exhausted'):
                cells.append(SolarPathCell(box, 'unresolved', reason))
                continue
        middle = box.midpoint
        stack.append((I(middle, box.hi), depth+1))
        stack.append((I(box.lo, middle), depth+1))

    cells = tuple(sorted(cells, key=lambda cell: (cell.domain.lo, cell.domain.hi)))
    # Closed neighbouring cells can prove the same shared root. Same-sign
    # derivative enclosures on their union imply strict monotonicity there;
    # two witnessed roots must therefore be the one common endpoint root.
    distinct = []
    for root in sorted(roots, key=lambda item: (item.domain.lo, item.domain.hi, item.function)):
        if (distinct and distinct[-1].function == root.function
                and distinct[-1].direction == root.direction
                and distinct[-1].boundary_phase == root.boundary_phase
                and distinct[-1].domain.hi == root.domain.lo):
            previous = distinct.pop()
            distinct.append(SolarPathRoot(
                root.function, I.point(root.domain.lo), root.direction,
                I(min(previous.derivative.lo, root.derivative.lo),
                  max(previous.derivative.hi, root.derivative.hi)), root.boundary_phase,
            ))
        else:
            distinct.append(root)
    complete = all(cell.kind != 'unresolved' for cell in cells)
    if any(left.domain.hi >= right.domain.lo for left, right in zip(distinct, distinct[1:])):
        complete = False
    enclosed = (complete and cells[0].kind == cells[-1].kind == 'excluded'
                and not any(cell.reason == 'whole_interval_axis_not_legal' for cell in cells))
    components, active, sequence = [], None, []
    for root in distinct:
        if root.function == 'axis':
            if root.direction == 'entry' and active is None:
                active = root.domain
            elif root.direction == 'exit' and active is not None:
                components.append((active, root.domain))
                active = None
            else:
                enclosed = False
        if root.function == 'axis':
            phases = (root.boundary_phase,)
        else:
            phases = ('annular', 'total') if root.direction == 'annular_to_total' else ('total', 'annular')
        for phase in phases:
            if phase is not None and (not sequence or sequence[-1] != phase):
                sequence.append(phase)
    if active is not None:
        enclosed = False
    seen = {cell.phase for cell in cells if cell.kind == 'phase' and cell.phase is not None}
    if seen == {'annular', 'total'}:
        status = 'hybrid'
    elif complete and seen == {'total'}:
        status = 'total_on_domain'
    elif complete and seen == {'annular'}:
        status = 'annular_on_domain'
    elif complete and not seen:
        status = 'no_legal_axis_on_domain'
    else:
        status = 'unresolved'
    subtype = None
    if enclosed and len(components) == 1:
        subtype = {('annular', 'total', 'annular'): 'H1',
                   ('total', 'annular'): 'H2', ('annular', 'total'): 'H3'}.get(tuple(sequence))
    reason = ('complete_model_domain_and_endpoint_coverage' if enclosed else
              'domain_clipped_or_unresolved_or_component_order_unproved')
    return SolarPathCoverage(domain, cells, tuple(distinct), status, tuple(sequence), subtype,
                             tuple(components), complete, enclosed, count, max_evaluations, reason)
