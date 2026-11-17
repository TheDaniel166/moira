"""Conditional one-dimensional interval-Newton contraction.

This operates on exact rational enclosures of one caller-supplied function.
Its conclusions require the declared differentiability and inclusion
contracts; it does not validate an ephemeris, a time scale, or a physical
eclipse. A nonempty contraction alone never establishes a root.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

from ._eclipse_interval import IntervalBudgetError, RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable


@dataclass(frozen=True, slots=True)
class IntervalNewtonStep:
    """A closed domain, a conditional conclusion, and its work receipt."""

    domain: I
    status: Literal["excluded", "unique", "contracted", "unresolved"]
    reason: str
    root_enclosure: I | None
    value: I | None
    derivative: I | None
    newton_image: I | None
    evaluations: int
    max_evaluations: int
    continuously_differentiable_assumed: bool


def interval_newton_step(
    domain: I,
    enclosure: Callable[[I], I],
    derivative: Callable[[I], I],
    *,
    continuously_differentiable: bool,
    max_evaluations: int = 3,
) -> IntervalNewtonStep:
    """Contract a closed real interval using an inclusion-form Newton step.

    The callbacks must enclose the *same* function and its derivative on
    their respective closed inputs. For a continuously differentiable function,
    every root in X belongs to N = m - f(m)/F'(X) when 0 is outside F'(X).
    An empty intersection excludes roots. N strictly inside X proves exactly
    one root by the interval-Newton inclusion theorem. A partial intersection
    is only a necessary enclosure, not an existence witness. Derivative-zero,
    unavailable, and exhausted-budget cases remain explicitly unresolved.
    """
    if not isinstance(domain, I):
        raise TypeError("domain must be a RationalInterval")
    if not callable(enclosure) or not callable(derivative):
        raise TypeError("value and derivative enclosures must be callable")
    if type(continuously_differentiable) is not bool:
        raise TypeError("continuously_differentiable must be a bool")
    if type(max_evaluations) is not int or max_evaluations < 0:
        raise ValueError("max_evaluations must be a nonnegative integer")

    count = 0
    value = rate = image = None

    def receipt(status, reason, root=None):
        return IntervalNewtonStep(domain, status, reason, root, value, rate, image,
                                  count, max_evaluations, continuously_differentiable)

    def evaluate(callback, box):
        nonlocal count
        if count >= max_evaluations:
            raise _EvaluationLimit
        count += 1
        result = callback(box)
        if not isinstance(result, I):
            raise TypeError("enclosure callbacks must return RationalInterval")
        return result

    try:
        value = evaluate(enclosure, domain)
        if not value.contains_zero:
            return receipt("excluded", "value_enclosure_excludes_zero")
        if not continuously_differentiable:
            return receipt("unresolved", "differentiability_not_declared", domain)
        # A singleton is decidable only if its actual value is proved zero.
        if domain.lo == domain.hi:
            if value.lo == value.hi == 0:
                return receipt("unique", "singleton_exact_zero", domain)
            return receipt("unresolved", "singleton_value_not_decided", domain)
        rate = evaluate(derivative, domain)
        if rate.contains_zero:
            return receipt("unresolved", "derivative_may_vanish", domain)
        midpoint = I.point(domain.midpoint)
        at_midpoint = evaluate(enclosure, midpoint)
        image = midpoint - at_midpoint / rate
        intersection = domain.intersect(image)
        if intersection is None:
            return receipt("excluded", "newton_image_disjoint")
        if domain.lo < image.lo and image.hi < domain.hi:
            return receipt("unique", "newton_image_strictly_inside", intersection)
        if intersection != domain:
            return receipt("contracted", "root_must_lie_in_intersection", intersection)
        return receipt("unresolved", "newton_image_does_not_contract", domain)
    except _EvaluationLimit:
        return receipt("unresolved", "evaluation_budget_exhausted", domain)
    except (EnclosureUnavailable, IntervalBudgetError) as exc:
        return receipt("unresolved", f"enclosure_unavailable: {exc}", domain)


class _EvaluationLimit(Exception):
    """The declared callback budget has been reached."""
