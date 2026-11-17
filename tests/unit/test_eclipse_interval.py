"""Exact endpoint and rational square-root enclosure regressions."""
from decimal import Decimal, localcontext
from fractions import Fraction
import math
import random

import pytest

from moira._eclipse_interval import (
    MAX_ENDPOINT_BITS, IntervalBudgetError, IntervalDomainError, RationalInterval,
)


def test_exact_float_decimal_and_context_independence():
    with localcontext() as ctx:
        ctx.prec = 2
        box = RationalInterval(Decimal("-1.234"), Decimal("0.1"))
        assert box.lo == Fraction(-617, 500)
        assert box.hi == Fraction(1, 10)
    assert RationalInterval.point(0.1).lo == Fraction(*0.1.as_integer_ratio())
    assert RationalInterval.point(-0.0) == RationalInterval.point(0)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), Decimal("NaN"), True])
def test_nonfinite_and_boolean_endpoints_are_rejected(value):
    with pytest.raises(IntervalDomainError):
        RationalInterval.point(value)


def test_domain_and_resource_limits_are_explicit():
    with pytest.raises(IntervalDomainError):
        RationalInterval(2, 1)
    with pytest.raises(IntervalDomainError):
        RationalInterval(1, 2) / RationalInterval(-1, 1)
    with pytest.raises(IntervalDomainError):
        RationalInterval(-1, 4).sqrt()
    with pytest.raises(IntervalBudgetError):
        RationalInterval.point(Decimal("1e-6000"))
    with pytest.raises(IntervalBudgetError):
        RationalInterval.point(Decimal("1" * 6000))
    with pytest.raises(IntervalBudgetError):
        RationalInterval.point(Fraction(1 << MAX_ENDPOINT_BITS, 3))
    with pytest.raises(IntervalBudgetError):
        RationalInterval.point(3) ** MAX_ENDPOINT_BITS
    with pytest.raises(IntervalBudgetError):
        RationalInterval.point(2).sqrt(precision_bits=4097)


def test_sqrt_bounds_hold_by_exact_squaring():
    for value in (Fraction(0), Fraction(1, 3), Fraction(2), Fraction(49, 25), Fraction(10**80, 13)):
        for bits in (1, 12, 64, 256):
            result = RationalInterval.point(value).sqrt(bits)
            assert result.lo >= 0
            assert result.lo**2 <= value <= result.hi**2
    assert RationalInterval.point(Fraction(49, 25)).sqrt(64).contains(Fraction(7, 5))
    assert RationalInterval.point(4).sqrt() == RationalInterval.point(2)


def test_outward_binary64_including_subnormal_values():
    for value in (Fraction(1, 10), Fraction(-1, 10), Fraction(1, 2**1075),
                  Fraction(-1, 2**1075), Fraction(1), Fraction(0)):
        lo, hi = RationalInterval.point(value).to_float_bounds()
        assert Fraction.from_float(lo) <= value <= Fraction.from_float(hi)
    assert RationalInterval.point(Fraction(1, 2**1075)).to_float_bounds()[1] == math.ulp(0.0)
    with pytest.raises(IntervalDomainError):
        RationalInterval.point(1 << 1100).to_float_bounds()


def test_outward_dyadic_quantization_handles_both_signs():
    for a in (Fraction(-10, 7), Fraction(-1, 10), Fraction(0), Fraction(1, 10), Fraction(10, 7)):
        for bits in (1, 8, 64, 128):
            rounded = RationalInterval.point(a).quantize_outward(bits)
            assert rounded.lo <= a <= rounded.hi
            assert rounded.width <= Fraction(1, 2**bits)


def test_randomized_rational_enclosures_against_exact_samples():
    rng = random.Random(5317)
    for _ in range(300):
        xs = sorted(Fraction(rng.randint(-100, 100), rng.randint(1, 30)) for _ in range(2))
        ys = sorted(Fraction(rng.randint(-100, 100), rng.randint(1, 30)) for _ in range(2))
        x, y = RationalInterval(*xs), RationalInterval(*ys)
        for a in (x.lo, x.midpoint, x.hi):
            for b in (y.lo, y.midpoint, y.hi):
                assert (x + y).contains(a + b)
                assert (x - y).contains(a - b)
                assert (x * y).contains(a * b)
                assert x.square().contains(a * a)
                if not y.contains_zero:
                    assert (x / y).contains(a / b)
