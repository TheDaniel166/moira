"""Correctly rounded scalar sine/cosine from exact rational enclosures.

This opt-in primitive does not call platform sin/cos. It refines rigorous
mathematical enclosures until both endpoints provably round to the same IEEE
binary64 number; otherwise it raises an explicit resource/domain failure.
It is not substituted into the legacy phase evaluator and does not attest
that evaluator, its sources, arithmetic environment, clock or search.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import math
import struct

from ._eclipse_interval import IntervalBudgetError, RationalInterval as I
from ._eclipse_interval_elementary import sin_cos_enclosure
from ._eclipse_interval_roots import EnclosureUnavailable


class EclipseStrictTrigUnavailable(EnclosureUnavailable):
    """The exact scalar trigonometric rounding could not be decided."""


@dataclass(frozen=True, slots=True)
class StrictScalarSinCos:
    """Correctly rounded mathematical values and their exact enclosures."""

    argument: float
    sine: float
    cosine: float
    sine_enclosure: I
    cosine_enclosure: I
    precision_bits: int
    platform_sin_cos_required: bool = False
    legacy_phase_evaluator_attested: bool = False
    source_attested: bool = False
    complete_search_certified: bool = False


def _bits(value: float) -> int:
    return struct.unpack(">Q", struct.pack(">d", value))[0]


def _from_bits(value: int) -> float:
    return struct.unpack(">d", struct.pack(">Q", value))[0]


def _checked_round(value: Fraction) -> float:
    """Check a proposed binary64 rounding against exact rational midpoints."""
    try:
        candidate = float(value)
    except OverflowError as exc:
        raise EclipseStrictTrigUnavailable("finite binary64 rounding is unavailable") from exc
    if not math.isfinite(candidate):
        raise EclipseStrictTrigUnavailable("finite binary64 rounding is unavailable")
    bits = _bits(candidate)
    if candidate == 0.0:
        if (bits >> 63) != int(value < 0):
            raise EclipseStrictTrigUnavailable("host zero rounding has an invalid sign")
        lower, upper = -float.fromhex("0x0.0000000000001p-1022"), float.fromhex("0x0.0000000000001p-1022")
    elif bits >> 63:
        lower, upper = _from_bits(bits + 1), _from_bits(bits - 1)
    else:
        lower, upper = _from_bits(bits - 1), _from_bits(bits + 1)
    if not math.isfinite(lower) or not math.isfinite(upper):
        raise EclipseStrictTrigUnavailable("rounding neighbor is not finite")
    exact = Fraction.from_float(candidate)
    lower_mid = (Fraction.from_float(lower) + exact) / 2
    upper_mid = (exact + Fraction.from_float(upper)) / 2
    if value < lower_mid or value > upper_mid:
        raise EclipseStrictTrigUnavailable("host float conversion is not a nearest candidate")
    if (value == lower_mid or value == upper_mid) and bits & 1:
        raise EclipseStrictTrigUnavailable("host float conversion did not use ties-to-even")
    return candidate


def strict_scalar_sin_cos(argument: float, *, max_precision_bits: int = 2048) -> StrictScalarSinCos:
    """Return correctly rounded mathematical sin/cos of represented ``argument``.

    Round-to-nearest, ties-to-even is checked against exact rational midpoints,
    independently of the accuracy of the host's transcendental library. An
    exact interval can straddle a rounding midpoint even after refinement; a
    finite work cap then returns unavailable rather than guessing.
    """
    if isinstance(argument, bool) or not isinstance(argument, (int, float)):
        raise ValueError("finite binary64 argument required")
    try:
        x = float(argument)
    except OverflowError as exc:
        raise ValueError("finite binary64 argument required") from exc
    if not math.isfinite(x):
        raise ValueError("finite binary64 argument required")
    if type(max_precision_bits) is not int or not 64 <= max_precision_bits <= 2048:
        raise ValueError("max_precision_bits must be an integer from 64 to 2048")
    if x == 0.0:
        return StrictScalarSinCos(x, x, 1.0, I.point(0), I.point(1), 0)
    value = Fraction.from_float(x)
    if abs(value) <= Fraction(1, 2**24):
        # Taylor's global |sin(x)-x| <= |x|**3/6 and
        # 1-x**2/2 <= cos(x) <= 1 preserve very small binary64 inputs.
        error = abs(value) ** 3 / 6
        sine = I(value - error, value + error)
        cosine = I(1 - value**2 / 2, 1)
        sin_lo, sin_hi = _checked_round(sine.lo), _checked_round(sine.hi)
        cos_lo, cos_hi = _checked_round(cosine.lo), _checked_round(cosine.hi)
        if _bits(sin_lo) == _bits(sin_hi) and _bits(cos_lo) == _bits(cos_hi):
            return StrictScalarSinCos(x, sin_lo, cos_lo, sine, cosine, 0)

    precision = 64
    while precision <= max_precision_bits:
        try:
            bounds = sin_cos_enclosure(I.point(value), precision_bits=precision, max_halvings=64)
        except IntervalBudgetError as exc:
            raise EclipseStrictTrigUnavailable("exact trigonometric work budget exhausted") from exc
        sin_lo, sin_hi = _checked_round(bounds.sine.lo), _checked_round(bounds.sine.hi)
        cos_lo, cos_hi = _checked_round(bounds.cosine.lo), _checked_round(bounds.cosine.hi)
        if _bits(sin_lo) == _bits(sin_hi) and _bits(cos_lo) == _bits(cos_hi):
            return StrictScalarSinCos(x, sin_lo, cos_lo, bounds.sine, bounds.cosine, precision)
        precision *= 2
    raise EclipseStrictTrigUnavailable("sine/cosine rounding midpoint remains unresolved")
