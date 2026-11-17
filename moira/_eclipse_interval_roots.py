"""Finite exact-rational root partitions with explicit proof obligations.

The caller supplies a mathematically valid enclosure of a single function on
every requested closed interval. Existence and uniqueness additionally depend
on the caller's declared continuity and derivative-enclosure contracts. No
ephemeris, floating implementation, or physical model is certified by this
generic partitioner. Closed neighboring cells share their endpoint; reported
unique cells must not be counted as distinct roots without deduplication.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

from ._eclipse_interval import IntervalBudgetError, IntervalDomainError, RationalInterval


class EnclosureUnavailable(ValueError):
    """A provider cannot enclose the selected mathematical domain."""


@dataclass(frozen=True, slots=True)
class RootCell:
    """A covered closed interval and its model-conditional root evidence."""

    interval: RationalInterval
    status: Literal["excluded", "unique", "present", "unresolved"]
    reason: str
    value: RationalInterval | None = None
    derivative: RationalInterval | None = None


@dataclass(frozen=True, slots=True)
class RootPartition:
    """Ordered covering cells and the assumptions under which they apply.

    ``complete`` means every cell excludes a root or contains exactly one;
    adjacent unique cells may share the same root at their common endpoint.
    The cells are not deduplicated root identities or proofs about nature.
    ``resolution_reached`` reports cell widths only; narrow unresolved cells
    do not establish completeness or root existence.
    """

    domain: RationalInterval
    cells: tuple[RootCell, ...]
    tolerance: RationalInterval
    evaluations: int
    max_evaluations: int
    unit: str
    time_scale: str | None
    continuous_assumed: bool
    interval_newton_enabled: bool = False

    @property
    def complete(self) -> bool:
        return all(cell.status in ("excluded", "unique") for cell in self.cells)

    @property
    def resolution_reached(self) -> bool:
        """Whether every retained root box meets the requested resolution."""
        return all(cell.status == "excluded" or cell.interval.width <= self.tolerance.hi
                   for cell in self.cells)


class _EvaluationLimit(Exception):
    """Stop an interval search when its callback budget is exhausted."""


def isolate_roots(
    domain: RationalInterval,
    enclosure: Callable[[RationalInterval], RationalInterval],
    *,
    tolerance: int | float | RationalInterval,
    unit: str,
    time_scale: str | None = None,
    derivative: Callable[[RationalInterval], RationalInterval] | None = None,
    continuous: bool = False,
    max_evaluations: int = 10000,
    max_depth: int = 80,
    interval_newton: bool = False,
    continuously_differentiable: bool = False,
) -> RootPartition:
    """Cover a domain by excluded, unique-root, present, or unresolved cells.

    A valid inclusion enclosure is required for every callback. A strict
    endpoint sign change proves a root only under the declared continuity
    contract. An exact point enclosure ``[0, 0]`` proves a root at that point.
    A sign witness plus a derivative enclosure strictly on one side of zero
    proves uniqueness, provided the derivative is valid throughout the cell.
    The same strict derivative bound and strict, equal endpoint signs prove
    absence on the entire closed cell, even if its value enclosure is wider.
    An unavailable provider or an exhausted budget retains every affected
    cell as unresolved; unexpected exceptions propagate. Domain units and
    time scale are metadata, never a time conversion. Opt-in interval Newton
    requires an explicit continuously differentiable model and derivative.
    It may exclude a whole cell or prove it has exactly one root; no partial
    complement is labeled excluded, preserving closed shared endpoints.
    """
    if not isinstance(domain, RationalInterval):
        raise TypeError("domain must be a RationalInterval")
    tol = RationalInterval.point(tolerance)
    if tol.lo != tol.hi or tol.lo <= 0:
        raise IntervalDomainError("tolerance must be a positive exact point")
    if not isinstance(unit, str) or not unit.strip():
        raise ValueError("unit must be a nonempty string")
    if time_scale is not None and (not isinstance(time_scale, str) or not time_scale.strip()):
        raise ValueError("time_scale must be None or a nonempty string")
    if type(continuous) is not bool:
        raise TypeError("continuous must be a bool")
    if type(interval_newton) is not bool or type(continuously_differentiable) is not bool:
        raise TypeError("interval_newton and continuously_differentiable must be bool")
    if interval_newton and (not continuous or not continuously_differentiable or derivative is None):
        raise ValueError("interval Newton requires continuity, continuous differentiability, and a derivative enclosure")
    if type(max_evaluations) is not int or max_evaluations < 0:
        raise ValueError("max_evaluations must be a nonnegative integer")
    if type(max_depth) is not int or max_depth < 0:
        raise ValueError("max_depth must be a nonnegative integer")

    evaluations = 0
    cells: list[RootCell] = []
    stack = [(domain, 0)]

    def evaluate(callback, box):
        nonlocal evaluations
        if evaluations >= max_evaluations:
            raise _EvaluationLimit
        evaluations += 1
        result = callback(box)
        if not isinstance(result, RationalInterval):
            raise TypeError("enclosure callbacks must return RationalInterval")
        return result

    while stack:
        box, depth = stack.pop()
        try:
            values = evaluate(enclosure, box)
            if not values.contains_zero:
                cells.append(RootCell(box, "excluded", "value_enclosure_excludes_zero", values))
                continue
            if interval_newton:
                # Local import avoids a module cycle: the standalone contractor
                # shares this module's provider-unavailable exception.
                from ._eclipse_interval_newton import interval_newton_step

                step = interval_newton_step(
                    box, enclosure, derivative,
                    continuously_differentiable=True,
                    max_evaluations=max_evaluations - evaluations,
                )
                evaluations += step.evaluations
                if step.status == "excluded":
                    cells.append(RootCell(box, "excluded", step.reason, values, step.derivative))
                    continue
                if step.status == "unique" and (box.width <= tol.hi or depth >= max_depth):
                    cells.append(RootCell(box, "unique", step.reason, values, step.derivative))
                    continue
            if box.width > tol.hi and depth < max_depth:
                middle = box.midpoint
                # Closed halves deliberately overlap at the common endpoint.
                stack.append((RationalInterval(middle, box.hi), depth + 1))
                stack.append((RationalInterval(box.lo, middle), depth + 1))
                continue

            left = evaluate(enclosure, RationalInterval.point(box.lo))
            right = left if box.lo == box.hi else evaluate(enclosure, RationalInterval.point(box.hi))
            exact_endpoint = (left.lo == left.hi == 0 or right.lo == right.hi == 0)
            opposite = (left.hi < 0 < right.lo) or (right.hi < 0 < left.lo)
            exists = exact_endpoint or (continuous and opposite)
            rate = evaluate(derivative, box) if derivative is not None and continuous else None
            unique = exists and rate is not None and not rate.contains_zero
            same_strict_sign = (left.lo > 0 and right.lo > 0) or (left.hi < 0 and right.hi < 0)
            if rate is not None and not rate.contains_zero and same_strict_sign:
                status, reason = "excluded", "nonzero_derivative_and_same_strict_endpoint_sign"
            elif unique:
                status, reason = "unique", "witness_and_nonzero_derivative"
            elif exists:
                status, reason = "present", "root_witness_without_uniqueness"
            else:
                status, reason = "unresolved", "root_existence_not_established"
            cells.append(RootCell(box, status, reason, values, rate))
        except _EvaluationLimit:
            cells.append(RootCell(box, "unresolved", "evaluation_budget_exhausted"))
            cells.extend(RootCell(item, "unresolved", "evaluation_budget_exhausted")
                         for item, _ in stack)
            stack.clear()
        except (EnclosureUnavailable, IntervalBudgetError) as exc:
            cells.append(RootCell(box, "unresolved", f"enclosure_unavailable: {exc}"))

    return RootPartition(domain, tuple(sorted(cells, key=lambda c: (c.interval.lo, c.interval.hi))),
                         tol, evaluations, max_evaluations, unit, time_scale, continuous, interval_newton)
