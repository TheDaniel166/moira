"""Conditional interval model of the phase route's native aberration step.

This bounds the specific scalar native expression on successful normal-domain
inputs under binary64 RN, gradual underflow, correctly rounded sqrt and
Python float power-by-two matching rounded multiplication. The unchanged
wrapper, binding TU and constants and a binding build without unsafe
reassociation are also required. These are unattested premises. It does not
bound rotation, longitude, UT1 or phase.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from ._eclipse_interval import IntervalBudgetError, IntervalDomainError, RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_native_spk_bounds import _rounded
from .constants import C_KM_PER_DAY


class EclipsePhaseAberrationUnavailable(EnclosureUnavailable):
    """The native aberration expression is outside its proven domain."""


@dataclass(frozen=True, slots=True)
class ConditionalPhaseAberrationBounds:
    """One conditional pre-rotation apparent vector enclosure."""

    position_km: tuple[I, I, I]
    arithmetic_model: str = (
        "binary64 RN; gradual underflow; correctly rounded sqrt and Python square; "
        "binding build without unsafe reassociation"
    )
    source_and_constants_attested: bool = False
    native_build_attested: bool = False
    arithmetic_environment_attested: bool = False
    frame_enclosed: bool = False
    phase_enclosed: bool = False
    physical_accuracy_certified: bool = False


def bound_phase_aberration(
    position_km: tuple[I, I, I], velocity_km_per_day: tuple[I, I, I],
) -> ConditionalPhaseAberrationBounds:
    """Bound the native aberration formula, declining ambiguous branches.

    The distance bound also covers the Python wrapper's early-return test,
    conditional on its float power-by-two implementation matching rounded
    multiplication. Underflow-scale distance, nonphysical velocity boxes,
    uncertain zero denominators, and overflow/precision budgets are unavailable.
    Every rounded intermediate uses directed endpoints, retaining the exact
    real intermediate as well as its rounded value; this also encloses an FMA
    contraction without assuming the binding's choice of contraction.
    """
    if (not isinstance(position_km, tuple) or len(position_km) != 3
            or not isinstance(velocity_km_per_day, tuple) or len(velocity_km_per_day) != 3
            or not all(isinstance(value, I) for value in (*position_km, *velocity_km_per_day))):
        raise TypeError("position and velocity must be three RationalInterval components")
    try:
        def add(a, b):
            return _rounded(a + b)

        def mul(a, b):
            return _rounded(a * b)

        def div(a, b):
            if b.contains_zero:
                raise EclipsePhaseAberrationUnavailable("aberration denominator may be zero")
            return _rounded(a / b)

        def root(value):
            if value.lo < 0:
                raise EclipsePhaseAberrationUnavailable("aberration sqrt domain is ambiguous")
            return _rounded(value.sqrt(128))

        def sum3(a, b, c):
            return add(add(a, b), c)

        def norm(v):
            return root(sum3(*(_rounded(x.square()) for x in v)))

        one = I.point(1)
        dist = norm(position_km)
        if dist.lo < Fraction.from_float(1e-10):
            raise EclipsePhaseAberrationUnavailable("aberration distance branch requires subdivision")
        direction = tuple(div(x, dist) for x in position_km)
        velocity = tuple(div(v, I.point(C_KM_PER_DAY)) for v in velocity_km_per_day)
        beta2 = sum3(*(_rounded(v.square()) for v in velocity))
        remaining = add(one, -beta2)
        if remaining.lo <= 0:
            raise EclipsePhaseAberrationUnavailable("aberration speed is not proved below light speed")
        gamma = div(one, root(remaining))
        dot = sum3(*(mul(u, v) for u, v in zip(direction, velocity)))
        factor1 = add(one, div(dot, add(one, gamma)))
        factor2 = mul(gamma, add(one, dot))
        apparent = tuple(div(add(u, mul(factor1, v)), factor2) for u, v in zip(direction, velocity))
        scale = div(dist, norm(apparent))
        result = tuple(mul(component, scale) for component in apparent)
        return ConditionalPhaseAberrationBounds(result)
    except (IntervalBudgetError, IntervalDomainError, OverflowError, ZeroDivisionError) as exc:
        raise EclipsePhaseAberrationUnavailable("aberration arithmetic exceeded its domain or budget") from exc
