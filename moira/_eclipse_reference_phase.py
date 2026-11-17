"""Continuous fixed-pole phase observables over exact vector enclosures.

This private mathematical model is independent of Moira's serving evaluator.
Its pole is an explicit constant vector; no physical frame, source, continuity,
or derivative is certified by accepting it as input. A caller must provide one
continuous vector model on the whole domain before using the intermediate
value theorem; independently selected SPK records can introduce seams.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable, RootPartition, isolate_roots


VectorBox = tuple[I, I, I]


@dataclass(frozen=True)
class ReferencePhaseVectors:
    """Enclosures of one exact reference model and optionally its derivatives.

    Derivatives are with respect to the same real input variable as the root
    domain. The provider is responsible for their validity and continuity of
    both vector functions on the entire requested interval.
    """

    sun: VectorBox
    moon: VectorBox
    sun_rate: VectorBox | None = None
    moon_rate: VectorBox | None = None


@dataclass(frozen=True)
class ReferencePhaseObservable:
    """Exact determinant, projected dot and optional determinant derivative."""

    determinant: I
    projected_dot: I
    derivative: I | None


def _dot(left: VectorBox, right: VectorBox) -> I:
    return sum((a * b for a, b in zip(left, right)), I.point(0))


def _cross(left: VectorBox, right: VectorBox) -> VectorBox:
    return (left[1] * right[2] - left[2] * right[1],
            left[2] * right[0] - left[0] * right[2],
            left[0] * right[1] - left[1] * right[0])


def _check_vector(vector) -> VectorBox:
    if not isinstance(vector, tuple) or len(vector) != 3 or not all(isinstance(x, I) for x in vector):
        raise TypeError("three-component RationalInterval vector required")
    return vector


def bound_reference_phase(vectors: ReferencePhaseVectors, pole: VectorBox) -> ReferencePhaseObservable:
    """Bound fixed-pole oriented phase and, if supplied, its derivative.

    The determinant is ``pole · (sun × moon)``. Projected dot is
    ``|pole|² (sun · moon) - (pole · sun)(pole · moon)``; its positive or
    negative sign distinguishes conjunction and opposition respectively.
    A point-valued, nonzero pole is required so that it denotes one fixed
    real vector throughout the interval. The sign of determinant is an
    oriented model convention, not the legacy wrapped-phase residual.
    """
    if not isinstance(vectors, ReferencePhaseVectors):
        raise TypeError("reference phase vector bounds required")
    sun, moon, pole = _check_vector(vectors.sun), _check_vector(vectors.moon), _check_vector(pole)
    if any(component.lo != component.hi for component in pole) or all(component.lo == 0 for component in pole):
        raise ValueError("pole must be a fixed nonzero exact vector")
    determinant = _dot(pole, _cross(sun, moon))
    projected_dot = _dot(pole, pole) * _dot(sun, moon) - _dot(pole, sun) * _dot(pole, moon)
    if (vectors.sun_rate is None) != (vectors.moon_rate is None):
        raise ValueError("both vector derivatives must be supplied together")
    derivative = None
    if vectors.sun_rate is not None:
        sun_rate, moon_rate = _check_vector(vectors.sun_rate), _check_vector(vectors.moon_rate)
        derivative = _dot(pole, _cross(sun_rate, moon)) + _dot(pole, _cross(sun, moon_rate))
    return ReferencePhaseObservable(determinant, projected_dot, derivative)


def isolate_reference_phase_roots(
    domain: I,
    vector_enclosure: Callable[[I], ReferencePhaseVectors],
    *,
    pole: VectorBox,
    phase: Literal["new", "full"],
    tolerance: int | float | I,
    continuity_assumed: bool,
    derivative_enclosed: bool = False,
    max_evaluations: int = 10000,
    max_depth: int = 80,
    time_scale: str | None = "TT",
    unit: str = "Julian day",
) -> RootPartition:
    """Isolate fixed-pole model roots with explicit continuity obligations.

    The vector provider must describe one fixed reference function on the
    complete domain, including endpoints and any native record seams. An
    unresolved branch or seam must raise ``EnclosureUnavailable``. The
    projected dot must prove the requested New/Full branch on each queried
    cell; otherwise that cell remains unresolved. A continuous sign change
    proves presence, while uniqueness additionally requires a valid derivative
    enclosure excluding zero. None of this certifies a physical eclipse.
    """
    if phase not in ("new", "full"):
        raise ValueError("phase must be 'new' or 'full'")
    if type(continuity_assumed) is not bool or type(derivative_enclosed) is not bool:
        raise TypeError("continuity and derivative declarations must be bool")
    cache: dict[tuple[object, object], ReferencePhaseObservable] = {}

    def observable(box: I) -> ReferencePhaseObservable:
        key = (box.lo, box.hi)
        if key not in cache:
            value = bound_reference_phase(vector_enclosure(box), pole)
            if (phase == "new" and value.projected_dot.lo <= 0) or (
                phase == "full" and value.projected_dot.hi >= 0
            ):
                raise EnclosureUnavailable("requested phase branch is not proved on this cell")
            cache[key] = value
        return cache[key]

    def enclosure(box: I) -> I:
        return observable(box).determinant

    def derivative(box: I) -> I:
        result = observable(box).derivative
        if result is None:
            raise EnclosureUnavailable("reference vector derivatives unavailable")
        return result

    return isolate_roots(
        domain, enclosure, tolerance=tolerance, unit=unit, time_scale=time_scale,
        continuous=continuity_assumed, derivative=derivative if derivative_enclosed else None,
        max_evaluations=max_evaluations, max_depth=max_depth,
    )
