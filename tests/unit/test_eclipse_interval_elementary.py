"""Independent checks of exact-rational trigonometric enclosures."""
from decimal import Decimal, localcontext
from fractions import Fraction as F
import random

import pytest

from moira._eclipse_interval import IntervalBudgetError, RationalInterval as I
from moira._eclipse_interval_elementary import sin_cos_enclosure


def atan_reciprocal_bounds(q, terms):
    """Alternating-series rational bounds for arctan(1/q), q>1."""
    partial = sum((F((-1)**k, (2*k+1) * q**(2*k+1)) for k in range(terms)), F(0))
    next_term = F((-1)**terms, (2*terms+1) * q**(2*terms+1))
    return I(min(partial, partial+next_term), max(partial, partial+next_term))


def pi_bounds():
    # Machin identity and alternating remainders, independently of the
    # implementation's halving and Lagrange construction.
    return 16*atan_reciprocal_bounds(5, 80) - 4*atan_reciprocal_bounds(239, 80)


def decimal_direct_taylor(x):
    """Empirical independent reference; Decimal result is not a certificate."""
    with localcontext() as ctx:
        ctx.prec = 115
        v = Decimal(x.numerator) / Decimal(x.denominator)
        sine = term_sin = v
        cosine = term_cos = Decimal(1)
        for n in range(1, 200):
            term_sin *= -v*v / Decimal((2*n)*(2*n+1))
            term_cos *= -v*v / Decimal((2*n-1)*(2*n))
            sine += term_sin
            cosine += term_cos
            if abs(term_sin) < Decimal("1e-105") and abs(term_cos) < Decimal("1e-105"):
                break
        return F(sine), F(cosine)


def test_zero_and_small_special_values():
    result = sin_cos_enclosure(I.point(0))
    assert result.sine == I.point(0)
    assert result.cosine == I.point(1)
    assert result.halvings == 0 and result.taylor_terms == 0
    result = sin_cos_enclosure(I(-1, 1))
    assert result.sine.contains(0) and result.cosine.contains(1)
    assert I(-1, 1).intersect(result.sine) == result.sine
    assert I(-1, 1).intersect(result.cosine) == result.cosine


@pytest.mark.parametrize("multiple", [1, -1, 3, -3, 10**6, -(10**6)])
def test_exact_extrema_and_zeros_from_rigorous_pi_interval(multiple):
    pi = pi_bounds()
    # Even multiples yield sin(kπ)=0, odd half-multiples sin(kπ/2)=±1.
    zero = sin_cos_enclosure(pi * multiple, precision_bits=80)
    assert zero.sine.contains(0)
    assert zero.cosine.contains(1 if multiple % 2 == 0 else -1)
    if multiple % 2:
        peak = sin_cos_enclosure(pi * F(multiple, 2), precision_bits=80)
        assert peak.cosine.contains(0)
        assert peak.sine.contains(1 if multiple % 4 == 1 else -1)


def test_narrow_intervals_crossing_extrema():
    pi = pi_bounds()
    around_half = pi / 2 + I(F(-1, 10**10), F(1, 10**10))
    r = sin_cos_enclosure(around_half, precision_bits=90)
    assert r.sine.contains(1) and r.cosine.contains(0)
    around_pi = pi + I(F(-1, 10**10), F(1, 10**10))
    r = sin_cos_enclosure(around_pi, precision_bits=90)
    assert r.cosine.contains(-1) and r.sine.contains(0)


def test_wide_and_giant_intervals_are_conservative_or_fail_closed():
    wide = sin_cos_enclosure(I(-(1 << 1000), 1 << 1000))
    assert wide.sine == I(-1, 1) and wide.cosine == I(-1, 1)
    with pytest.raises(IntervalBudgetError, match="halving"):
        sin_cos_enclosure(I.point(1 << 1000), max_halvings=100)
    with pytest.raises(IntervalBudgetError, match="halving"):
        sin_cos_enclosure(I.point(-2), max_halvings=0)
    with pytest.raises(IntervalBudgetError, match="Taylor"):
        sin_cos_enclosure(I.point(F(1, 2)), precision_bits=128, max_terms=1)
    with pytest.raises(IntervalBudgetError, match="working precision"):
        sin_cos_enclosure(I.point(1), precision_bits=4096)
    with pytest.raises(TypeError):
        sin_cos_enclosure(1)


def test_random_points_against_independent_decimal_direct_series():
    rng = random.Random(4421)
    for _ in range(80):
        x = F(rng.randint(-1000, 1000), rng.randint(100, 500))
        s, c = decimal_direct_taylor(x)
        result = sin_cos_enclosure(I.point(x), precision_bits=64)
        assert result.sine.contains(s)
        assert result.cosine.contains(c)


def test_interval_contains_independent_interior_samples():
    intervals = [(F(-9), F(-89, 10)), (F(-1, 3), F(2, 3)),
                 (F(7), F(71, 10)), (F(-2), F(3))]
    for lo, hi in intervals:
        result = sin_cos_enclosure(I(lo, hi), precision_bits=64)
        for index in range(11):
            x = lo + (hi-lo) * F(index, 10)
            s, c = decimal_direct_taylor(x)
            assert result.sine.contains(s)
            assert result.cosine.contains(c)
