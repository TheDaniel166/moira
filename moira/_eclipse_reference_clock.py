"""Exact continuous implicit NAIF-style TT/TDB reference clock.

This private mathematical model interprets pinned binary64 constants as exact
rationals and defines TDB by the unique real fixed point. It does not claim to
equal the legacy finite-iteration Python converter or physical time. Rational
Taylor trigonometric enclosures do not assume platform sin/cos accuracy.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import math

from ._eclipse_interval import IntervalBudgetError, IntervalDomainError, RationalInterval as I
from ._eclipse_interval_elementary import sin_cos_enclosure
from ._eclipse_interval_roots import EnclosureUnavailable
from .julian import (
    _MAX_ABS_TIME_JD, _NAIF_DELTET_EB, _NAIF_DELTET_K_SECONDS,
    _NAIF_DELTET_M0_RADIANS, _NAIF_DELTET_M1_RADIANS_PER_SECOND,
)


class EclipseReferenceClockUnavailable(EnclosureUnavailable):
    """The exact continuous reference clock exceeds its domain or budget."""


@dataclass(frozen=True, slots=True)
class ContinuousReferenceTdb:
    """Bound the unique exact fixed point and its derivative on a TT box."""

    tt_anchor_jd: float
    tt_offset_days: I
    tdb_offset_days: I
    correction_days: I
    derivative_tdb_per_tt: I
    contraction_ratio: Fraction
    fixed_point_steps: int
    exact_reference_model_only: bool = True
    continuous_on_domain: bool = True
    legacy_converter_enclosed: bool = False
    ut1_enclosed: bool = False
    physical_accuracy_certified: bool = False


def bound_continuous_reference_tdb(
    tt_anchor_jd: float, tt_offset_days: I, *, steps: int = 4, precision_bits: int = 128,
    local_rate: bool = False,
) -> ContinuousReferenceTdb:
    """Enclose the real implicit fixed point and d(TDB)/d(TT).

    In days let F(t,x) = K/86400*sin(M0 + M1*86400*(t+x-J2000)
    + EB*sin(M0 + M1*86400*(t+x-J2000))). ``x`` is TDB minus TT.
    A global Lipschitz upper bound in x and t is
    q=|K*M1|*(1+|EB|)<1, so F maps [-|K|/86400, |K|/86400] into
    itself and has one fixed point x(t), continuously differentiable with
    d(TDB)/d(TT) in [1/(1+q), 1/(1-q)]. This is a real-function proof, not
    an assertion about finite binary64 fixed-point iteration.

    The optional local rate uses 1/(1-F') where F' differentiates the
    correction as a function of TDB. The final iteration's input encloses
    every fixed point and supplies both cosine bounds without extra trig.
    """
    if isinstance(tt_anchor_jd, bool) or not isinstance(tt_anchor_jd, (int, float)):
        raise ValueError("TT anchor must be finite")
    try:
        anchor = float(tt_anchor_jd)
    except OverflowError as exc:
        raise ValueError("TT anchor must be finite") from exc
    if not math.isfinite(anchor):
        raise ValueError("TT anchor must be finite")
    if not isinstance(tt_offset_days, I):
        raise TypeError("TT offset must be a RationalInterval")
    if type(steps) is not int or not 1 <= steps <= 32:
        raise ValueError("steps must be an integer from 1 to 32")
    if type(precision_bits) is not int or not 64 <= precision_bits <= 512:
        raise ValueError("precision_bits must be an integer from 64 to 512")
    constants = (_NAIF_DELTET_K_SECONDS, _NAIF_DELTET_M1_RADIANS_PER_SECOND,
                 _NAIF_DELTET_EB, _NAIF_DELTET_M0_RADIANS)
    if not all(math.isfinite(value) for value in constants):
        raise EclipseReferenceClockUnavailable("reference clock constants must be finite")
    k, m1, eb, m0 = map(Fraction.from_float, constants)
    q = abs(k * m1) * (1 + abs(eb))
    if q >= 1:
        raise EclipseReferenceClockUnavailable("reference TT/TDB relation is not a contraction")
    absolute = I.point(anchor) + tt_offset_days
    if absolute.lo < -_MAX_ABS_TIME_JD or absolute.hi > _MAX_ABS_TIME_JD:
        raise EclipseReferenceClockUnavailable("TT interval outside reference clock domain")
    radius = abs(k) / 86400
    correction = I(-radius, radius)
    try:
        for _ in range(steps):
            mean = (I.point(m0) + (absolute + correction - 2451545) * (m1 * 86400)).quantize_outward(precision_bits)
            inner = sin_cos_enclosure(mean, precision_bits=precision_bits)
            anomaly = (mean + eb * inner.sine).quantize_outward(precision_bits)
            outer = sin_cos_enclosure(anomaly, precision_bits=precision_bits)
            result = (outer.sine * (k / 86400)).quantize_outward(precision_bits)
            narrowed = correction.intersect(result)
            if narrowed is None:
                raise ArithmeticError("reference fixed-point enclosures are inconsistent")
            correction = narrowed
        tdb = (tt_offset_days + correction).quantize_outward(precision_bits)
        derivative = I(Fraction(1, 1) / (1 + q), Fraction(1, 1) / (1 - q))
        if local_rate:
            slope = (k * m1 * outer.cosine * (1 + eb * inner.cosine)).intersect(I(-q, q))
            if slope is None:
                raise ArithmeticError("reference clock rate enclosures are inconsistent")
            derivative = 1 / (1 - slope)
        return ContinuousReferenceTdb(anchor, tt_offset_days, tdb, correction, derivative, q, steps)
    except (IntervalBudgetError, IntervalDomainError, OverflowError) as exc:
        raise EclipseReferenceClockUnavailable("reference clock interval budget exhausted") from exc
