"""Rational inverse-trigonometric enclosures for real reference geometry.

The arctangent power series and inverse-function identities are those of
NIST DLMF 4.24. For a reduced nonnegative argument at most 1/2, alternating
terms decrease and the first omitted term bounds the remainder. The exact
half-angle identity reduces any finite positive argument without a pi or
libm approximation. Monotonic endpoint evaluation covers whole intervals.
"""
from fractions import Fraction

from ._eclipse_interval import IntervalBudgetError, IntervalDomainError, RationalInterval as I


def atan_enclosure(argument: I, *, precision_bits: int = 128,
                   max_terms: int = 512, max_halvings: int = 4) -> I:
    """Enclose mathematical atan on a finite rational interval.

    atan(x)=2 atan(x/(1+sqrt(1+x*x))) for x>=0. Once x<=1/2,
    the alternating series has remainder bounded by x**(2n+1)/(2n+1).
    Outward quantization only enlarges intermediate intervals. Precision
    denotes a dyadic grid; width is not promised on a non-point input.
    """
    if not isinstance(argument, I):
        raise TypeError("argument must be a RationalInterval")
    if type(precision_bits) is not int or not 32 <= precision_bits <= 512:
        raise IntervalBudgetError("inverse-trig precision exceeds supported budget")
    if type(max_terms) is not int or not 1 <= max_terms <= 2048:
        raise IntervalBudgetError("invalid inverse-trig series budget")
    if type(max_halvings) is not int or not 0 <= max_halvings <= 16:
        raise IntervalBudgetError("invalid inverse-trig half-angle budget")
    bits = precision_bits + 32

    def q(value):
        return value.quantize_outward(bits)

    def positive(value):
        if value == 0:
            return I.point(0)
        x, halves = I.point(value), 0
        while x.hi > Fraction(1, 2):
            if halves >= max_halvings:
                raise IntervalBudgetError("inverse-trig half-angle budget exhausted")
            x = q(x / (1 + (1 + x.square()).sqrt(bits)))
            halves += 1
        squared = q(x.square())
        power, result = x, I.point(0)
        for index in range(max_terms):
            term = power / (2 * index + 1)
            result = q(result + (term if index % 2 == 0 else -term))
            power = q(power * squared)
            remainder = power.magnitude / (2 * index + 3)
            if remainder <= Fraction(1, 1 << (precision_bits + 16)):
                tail = I(-remainder, 0) if index % 2 == 0 else I(0, remainder)
                return ((result + tail) * (1 << halves)).quantize_outward(precision_bits)
        raise IntervalBudgetError("inverse-trig series budget exhausted")

    def endpoint(value):
        return -positive(-value) if value < 0 else positive(value)

    lower = endpoint(argument.lo)
    upper = lower if argument.lo == argument.hi else endpoint(argument.hi)
    return I(lower.lo, upper.hi)


def asin_enclosure(argument: I, *, precision_bits: int = 128,
                   max_terms: int = 512, max_halvings: int = 4) -> I:
    """Enclose asin on [-1,1] by its exact real half-angle identity.

    asin(x)=2 atan(x/(1+sqrt(1-x*x))). The denominator is positive,
    including at +/-1. Endpoint monotonicity avoids dependency inflation
    across a wide input interval. No platform inverse trig is used.
    """
    if not isinstance(argument, I):
        raise TypeError("argument must be a RationalInterval")
    if argument.lo < -1 or argument.hi > 1:
        raise IntervalDomainError("arcsine argument lies outside [-1,1]")
    # Validate work parameters even for the exact zero case.
    atan_enclosure(I.point(0), precision_bits=precision_bits,
                   max_terms=max_terms, max_halvings=max_halvings)

    def endpoint(value):
        x = I.point(value)
        ratio = (x / (1 + (1 - x.square()).sqrt(precision_bits + 32))).quantize_outward(
            precision_bits + 32)
        return 2 * atan_enclosure(ratio, precision_bits=precision_bits,
                                  max_terms=max_terms, max_halvings=max_halvings)

    lower = endpoint(argument.lo)
    upper = lower if argument.lo == argument.hi else endpoint(argument.hi)
    return I(lower.lo, upper.hi).quantize_outward(precision_bits)
