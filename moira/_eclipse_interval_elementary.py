"""Unconditional rational sine/cosine enclosures without platform libm.

The domain and coefficients are exact rationals. We halve the entire argument
interval until it lies in [-1, 1], evaluate Taylor polynomials with explicit
Lagrange remainders, and undo every halving with double-angle identities.
All interval operations and outward quantization are rational. Bounds are for
the mathematical sine/cosine of the supplied interval, not automatically
for a particular floating-point implementation or astronomical model.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from ._eclipse_interval import IntervalBudgetError, RationalInterval


_MAX_WORK_PRECISION_BITS = 4096
_MAX_HALVINGS = 1024
_MAX_TERMS = 2048


@dataclass(frozen=True, slots=True)
class RationalSinCos:
    """Exact enclosures and work receipt for mathematical sine and cosine.

    The precision is the final dyadic grid, not an asserted bound on interval
    width. A wide argument, dependency inflation, or repeated doubling may
    legitimately yield the full range [-1, 1].
    """

    sine: RationalInterval
    cosine: RationalInterval
    halvings: int
    taylor_terms: int
    precision_bits: int
    working_precision_bits: int


def sin_cos_enclosure(
    argument: RationalInterval,
    *,
    precision_bits: int = 128,
    max_halvings: int = 256,
    max_terms: int = 512,
) -> RationalSinCos:
    """Enclose sin(x) and cos(x) for every exact rational x in ``argument``.

    For |x|<=1, the m-term sine polynomial has degree 2m-1 and absolute
    remainder at most 1/(2m)!; the m-term cosine polynomial has degree 2m-2
    and remainder at most 1/(2m-1)!. The derivative bound used in each
    Lagrange remainder is one. Halving and the subsequent double-angle
    identities are exact; every intermediate dyadic quantization widens its
    input. Exhausted work/precision limits raise ``IntervalBudgetError``.
    """
    if not isinstance(argument, RationalInterval):
        raise TypeError("argument must be a RationalInterval")
    if type(precision_bits) is not int or not 1 <= precision_bits <= _MAX_WORK_PRECISION_BITS:
        raise IntervalBudgetError("sine/cosine precision exceeds supported budget")
    if type(max_halvings) is not int or not 0 <= max_halvings <= _MAX_HALVINGS:
        raise IntervalBudgetError("sine/cosine halving budget is invalid")
    if type(max_terms) is not int or not 1 <= max_terms <= _MAX_TERMS:
        raise IntervalBudgetError("sine/cosine Taylor budget is invalid")
    full = RationalInterval(-1, 1)
    if argument.lo == argument.hi == 0:
        return RationalSinCos(RationalInterval.point(0), RationalInterval.point(1),
                              0, 0, precision_bits, precision_bits)
    # This conservative range is valid for any interval, even without a
    # separate transcendental proof that it spans an entire cycle.
    if argument.width >= 8:
        return RationalSinCos(full, full, 0, 0, precision_bits, precision_bits)

    reduced = argument
    halvings = 0
    while reduced.magnitude > 1:
        if halvings >= max_halvings:
            raise IntervalBudgetError("sine/cosine argument halving budget exhausted")
        reduced = reduced / 2
        halvings += 1

    # Extra working bits control accumulated widening. This is not presented
    # as a guaranteed final-width target, because interval dependency can be
    # large. The exact Lagrange remainder remains valid for every bit count.
    working_bits = precision_bits + 2 * halvings + 16
    if working_bits > _MAX_WORK_PRECISION_BITS:
        raise IntervalBudgetError("sine/cosine working precision exceeds budget")
    threshold = 1 << working_bits
    factorials = [1]
    terms = 0
    while True:
        terms += 1
        if terms > max_terms:
            raise IntervalBudgetError("sine/cosine Taylor term budget exhausted")
        # Both remainders need factorials through (2m)!.
        for n in range(len(factorials), 2 * terms + 1):
            factorials.append(factorials[-1] * n)
        if factorials[2 * terms - 1] >= threshold:
            break

    x = reduced.quantize_outward(working_bits)
    x_squared = x.square().quantize_outward(working_bits)

    def polynomial(odd: bool) -> RationalInterval:
        result = RationalInterval.point(0)
        for index in range(terms - 1, -1, -1):
            power = 2 * index + int(odd)
            coefficient = Fraction(-1 if index % 2 else 1, factorials[power])
            result = (result * x_squared + coefficient).quantize_outward(working_bits)
        return (result * x).quantize_outward(working_bits) if odd else result

    def widen(value: RationalInterval, remainder: Fraction) -> RationalInterval:
        return RationalInterval(value.lo - remainder, value.hi + remainder).quantize_outward(working_bits)

    def clip(value: RationalInterval) -> RationalInterval:
        clipped = value.intersect(full)
        if clipped is None:
            raise ArithmeticError("internal sine/cosine enclosure contradicts global range")
        return clipped

    sine = clip(widen(polynomial(True), Fraction(1, factorials[2 * terms])))
    cosine = clip(widen(polynomial(False), Fraction(1, factorials[2 * terms - 1])))
    for _ in range(halvings):
        old_sine, old_cosine = sine, cosine
        sine = clip((2 * old_sine * old_cosine).quantize_outward(working_bits))
        cosine = clip((1 - 2 * old_sine.square()).quantize_outward(working_bits))
    return RationalSinCos(sine.quantize_outward(precision_bits),
                          cosine.quantize_outward(precision_bits),
                          halvings, terms, precision_bits, working_bits)
