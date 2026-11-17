"""Independent rational inverse-series and forward-function controls."""
from decimal import Decimal
from fractions import Fraction as F

import pytest

from moira._eclipse_interval import IntervalBudgetError, IntervalDomainError, RationalInterval as I
from moira._eclipse_interval_elementary import sin_cos_enclosure
from moira._eclipse_inverse_trig import asin_enclosure, atan_enclosure


PI = F(Decimal('3.141592653589793238462643383279502884197169399375105820974944592307816406286208998628034825342117068'))


@pytest.mark.parametrize('x,expected', [(0, F(0)), (1, PI/4), (-1, -PI/4)])
def test_atan_known_values(x, expected):
    assert atan_enclosure(I.point(x)).contains(expected)


@pytest.mark.parametrize('x', [F(-10**20), -3, F(-1, 3), F(1, 1000), F(1, 2), 2, 10**20])
def test_atan_endpoint_signs_with_independent_forward_taylor_bounds(x):
    result = atan_enclosure(I.point(x))
    left = sin_cos_enclosure(I.point(result.lo), precision_bits=192)
    right = sin_cos_enclosure(I.point(result.hi), precision_bits=192)
    assert (left.sine - x*left.cosine).hi <= 0
    assert (right.sine - x*right.cosine).lo >= 0
    assert result.width < F(1, 1 << 116)


@pytest.mark.parametrize('x', [F(-3, 4), F(-1, 10), F(1, 10), F(1, 2), F(3, 4)])
def test_asin_against_independent_positive_coefficient_series(x):
    sign, y = (-1 if x < 0 else 1), abs(x)
    # c_n=(2n choose n)/4**n, c_(n+1)=c_n*(2n+1)/(2n+2).
    # Since 0<c_n<=1, the remaining positive terms are bounded by the
    # geometric tail y**(2n+1)/(1-y*y), independently of atan reduction.
    value, coefficient, power, n = F(0), F(1), y, 0
    while True:
        value += coefficient*power/(2*n+1)
        coefficient *= F(2*n+1, 2*n+2)
        power *= y*y
        n += 1
        tail = power/(1-y*y)
        if tail < F(1, 1 << 256):
            break
    oracle = I(value, value + tail)
    if sign < 0:
        oracle = -oracle
    result = asin_enclosure(I.point(x))
    assert result.lo <= oracle.lo <= oracle.hi <= result.hi


@pytest.mark.parametrize('x,expected', [(-1, -PI/2), (0, F(0)), (1, PI/2), (F(1, 2), PI/6)])
def test_asin_endpoint_and_elementary_values(x, expected):
    assert asin_enclosure(I.point(x)).contains(expected)


def test_whole_interval_monotonicity_and_explicit_work_failures():
    box = atan_enclosure(I(-2, 3))
    assert box.lo == atan_enclosure(I.point(-2)).lo
    assert box.hi == atan_enclosure(I.point(3)).hi
    assert asin_enclosure(I(-1, 1)).lo < 0 < asin_enclosure(I(-1, 1)).hi
    with pytest.raises(IntervalDomainError):
        asin_enclosure(I(-2, 0))
    with pytest.raises(IntervalBudgetError):
        atan_enclosure(I.point(1), max_halvings=0)
    with pytest.raises(IntervalBudgetError):
        atan_enclosure(I.point(F(1, 2)), max_terms=1)


@pytest.mark.parametrize('kwargs', [dict(precision_bits=True), dict(precision_bits=16),
                                  dict(max_terms=0), dict(max_halvings=-1)])
def test_invalid_budgets_even_at_zero(kwargs):
    with pytest.raises(IntervalBudgetError):
        asin_enclosure(I.point(0), **kwargs)
