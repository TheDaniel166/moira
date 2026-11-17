"""Exact rational enclosures for bounded eclipse computations.

Endpoints denote finite rational numbers; binary64 inputs are converted to
their exact represented values.  Arithmetic contains no platform ``libm``
assumption.  These primitives alone do not enclose an ephemeris, time scale,
light-time solver, or the physical uncertainty of an eclipse model.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
import math


MAX_ENDPOINT_BITS = 16384
MAX_SQRT_PRECISION_BITS = 4096


class IntervalDomainError(ValueError):
    """An interval operation has an invalid or non-finite domain."""


class IntervalBudgetError(ArithmeticError):
    """An exact enclosure exceeds its declared resource limit."""


def _fraction(value: int | float | Fraction | Decimal) -> Fraction:
    if isinstance(value, bool):
        raise IntervalDomainError("boolean is not an interval endpoint")
    if isinstance(value, Fraction):
        result = value
    elif isinstance(value, int):
        if value.bit_length() > MAX_ENDPOINT_BITS:
            raise IntervalBudgetError("integer endpoint exceeds bit budget")
        result = Fraction(value)
    elif isinstance(value, float):
        if not math.isfinite(value):
            raise IntervalDomainError("finite interval endpoint required")
        result = Fraction.from_float(value)
    elif isinstance(value, Decimal):
        if not value.is_finite():
            raise IntervalDomainError("finite interval endpoint required")
        # Avoid allocating arbitrary powers of ten for hostile exponents.
        parts = value.as_tuple()
        if (abs(parts.exponent) > MAX_ENDPOINT_BITS // 3
                or len(parts.digits) > MAX_ENDPOINT_BITS // 3):
            raise IntervalBudgetError("decimal input exceeds bit budget")
        result = Fraction(value)
    else:
        raise TypeError("endpoint must be an int, float, Fraction or Decimal")
    if max(result.numerator.bit_length(), result.denominator.bit_length()) > MAX_ENDPOINT_BITS:
        raise IntervalBudgetError("rational endpoint exceeds bit budget")
    return result


@dataclass(frozen=True, slots=True)
class RationalInterval:
    """Closed interval over exact rationals, including exact point intervals."""

    lo: Fraction
    hi: Fraction

    def __post_init__(self) -> None:
        lo, hi = _fraction(self.lo), _fraction(self.hi)
        if lo > hi:
            raise IntervalDomainError("interval endpoints must be ordered")
        object.__setattr__(self, "lo", lo)
        object.__setattr__(self, "hi", hi)

    @classmethod
    def point(cls, value: int | float | Fraction | Decimal | RationalInterval) -> RationalInterval:
        """Enclose an exact rational or the exact represented binary64 value."""
        if isinstance(value, cls):
            return value
        return cls(value, value)

    @property
    def width(self) -> Fraction:
        return self.hi - self.lo

    @property
    def midpoint(self) -> Fraction:
        return (self.lo + self.hi) / 2

    @property
    def magnitude(self) -> Fraction:
        return max(abs(self.lo), abs(self.hi))

    @property
    def contains_zero(self) -> bool:
        return self.lo <= 0 <= self.hi

    def contains(self, value: int | float | Fraction | Decimal) -> bool:
        """Return whether the exact represented value belongs to the interval."""
        point = _fraction(value)
        return self.lo <= point <= self.hi

    def intersect(self, other: RationalInterval) -> RationalInterval | None:
        """Return the closed intersection, or ``None`` when disjoint."""
        other = self.point(other)
        lo, hi = max(self.lo, other.lo), min(self.hi, other.hi)
        return None if lo > hi else RationalInterval(lo, hi)

    def __neg__(self) -> RationalInterval:
        return RationalInterval(-self.hi, -self.lo)

    def __add__(self, other) -> RationalInterval:
        other = self.point(other)
        return RationalInterval(self.lo + other.lo, self.hi + other.hi)

    __radd__ = __add__

    def __sub__(self, other) -> RationalInterval:
        return self + -self.point(other)

    def __rsub__(self, other) -> RationalInterval:
        return self.point(other) - self

    def __mul__(self, other) -> RationalInterval:
        other = self.point(other)
        values = (self.lo * other.lo, self.lo * other.hi,
                  self.hi * other.lo, self.hi * other.hi)
        return RationalInterval(min(values), max(values))

    __rmul__ = __mul__

    def __truediv__(self, other) -> RationalInterval:
        other = self.point(other)
        if other.contains_zero:
            raise IntervalDomainError("interval denominator contains zero")
        return self * RationalInterval(1 / other.hi, 1 / other.lo)

    def __rtruediv__(self, other) -> RationalInterval:
        return self.point(other) / self

    def square(self) -> RationalInterval:
        """Return the exact range of the square function on the interval."""
        return RationalInterval(0 if self.contains_zero else min(self.lo**2, self.hi**2),
                                max(self.lo**2, self.hi**2))

    def __pow__(self, exponent: int) -> RationalInterval:
        if type(exponent) is not int or exponent < 0:
            raise IntervalDomainError("nonnegative integer exponent required")
        if exponent > MAX_ENDPOINT_BITS:
            raise IntervalBudgetError("interval exponent exceeds bit budget")
        if exponent == 0:
            return self.point(1)
        # Fractions are reduced; preflight before constructing a huge power.
        for value in (self.lo, self.hi):
            if value not in (0, 1, -1):
                bits = max(value.numerator.bit_length(), value.denominator.bit_length())
                if bits * exponent > MAX_ENDPOINT_BITS:
                    raise IntervalBudgetError("interval power exceeds bit budget")
        if exponent % 2 == 0:
            base = self.square()
            power = exponent // 2
            return RationalInterval(base.lo**power, base.hi**power)
        return RationalInterval(self.lo**exponent, self.hi**exponent)

    def __abs__(self) -> RationalInterval:
        if self.contains_zero:
            return RationalInterval(0, self.magnitude)
        return RationalInterval(min(abs(self.lo), abs(self.hi)), self.magnitude)

    def sqrt(self, precision_bits: int = 128) -> RationalInterval:
        """Enclose the square root by dyadics using exact integer comparisons."""
        if self.lo < 0:
            raise IntervalDomainError("square-root interval contains negative values")
        if type(precision_bits) is not int or not 1 <= precision_bits <= MAX_SQRT_PRECISION_BITS:
            raise IntervalBudgetError("square-root precision exceeds supported budget")
        scale = 1 << precision_bits

        def bounds(x: Fraction) -> tuple[Fraction, Fraction]:
            shifted = x.numerator << (2 * precision_bits)
            lower = math.isqrt(shifted // x.denominator)
            exact = lower * lower * x.denominator == shifted
            return Fraction(lower, scale), Fraction(lower if exact else lower + 1, scale)

        return RationalInterval(bounds(self.lo)[0], bounds(self.hi)[1])

    def quantize_outward(self, precision_bits: int = 128) -> RationalInterval:
        """Enclose endpoints by dyadics with an exact floor/ceiling operation.

        This is an absolute grid of 2**(-precision_bits), not a relative-error
        model. It can prevent denominator growth when composing enclosures.
        """
        if type(precision_bits) is not int or not 1 <= precision_bits <= MAX_SQRT_PRECISION_BITS:
            raise IntervalBudgetError("dyadic precision exceeds supported budget")
        scale = 1 << precision_bits
        lo = (self.lo.numerator * scale) // self.lo.denominator
        hi = -((-self.hi.numerator * scale) // self.hi.denominator)
        return RationalInterval(Fraction(lo, scale), Fraction(hi, scale))

    def to_float_bounds(self) -> tuple[float, float]:
        """Round each endpoint outwards to a finite binary64 representation."""
        try:
            lo, hi = float(self.lo), float(self.hi)
        except OverflowError as exc:
            raise IntervalDomainError("interval is outside finite binary64 range") from exc
        if not math.isfinite(lo) or not math.isfinite(hi):
            raise IntervalDomainError("interval is outside finite binary64 range")
        if Fraction.from_float(lo) > self.lo:
            lo = math.nextafter(lo, -math.inf)
        if Fraction.from_float(hi) < self.hi:
            hi = math.nextafter(hi, math.inf)
        if not math.isfinite(lo) or not math.isfinite(hi):
            raise IntervalDomainError("interval is outside finite binary64 range")
        if Fraction.from_float(lo) > self.lo or Fraction.from_float(hi) < self.hi:
            raise IntervalDomainError("binary64 conversion could not enclose interval")
        return lo, hi
