"""One-ULP fsum allowance across binary64 binade boundaries."""

import math
from fractions import Fraction

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_native_spk_bounds import _fsum
from moira._eclipse_ancient_clock_bounds import _fsum_bounds


@pytest.mark.parametrize("exponent", [-1022, -10, 0, 10, 1023])
@pytest.mark.parametrize("sign", [-1, 1])
@pytest.mark.parametrize("summation", [lambda x: _fsum((x,)), _fsum_bounds])
def test_fsum_one_ulp_enclosure_covers_both_sides_of_power_of_two(exponent, sign, summation):
    boundary = math.ldexp(float(sign), exponent)
    ulp = math.ulp(boundary)
    result = summation(I.point(boundary))
    exact = Fraction.from_float(boundary)
    allowance = Fraction.from_float(ulp)
    assert result.contains(exact - allowance)
    assert result.contains(exact + allowance)


def test_fsum_boundary_cancellation_encloses_small_represented_residual():
    boundary = float(2**52)
    result = _fsum((I.point(boundary), I.point(-boundary), I.point(0.5)))
    assert result.contains(0.5)
