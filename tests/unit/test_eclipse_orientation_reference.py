"""Differentiated series and derived serving-error controls."""
from decimal import Decimal as D,localcontext
from fractions import Fraction as F

import pytest

from moira import _eclipse_interval_jets as j
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_orientation_reference import (FrozenOrientationSeries,
    bound_nutation_reference,freeze_orientation_series,taylor_nutation_bounds,
    serving_nutation_error_radians)
from moira.constants import DEG2RAD
from moira.nutation_2000a import _ARCSEC,nutation_2000a


@pytest.mark.parametrize('time_order',[0,1])
def test_differentiated_single_term_against_independent_decimal(time_order):
    row = (1_000_000.,0.,1,0,0,0,0,0,0,0,0,0,0,0,0,0)
    series = FrozenOrientationSeries((row,),(row,),1-time_order,1-time_order,'synthetic')
    x = F(1,3)
    t = j.scale(j.variable(I.point(x)),F(1,36525))
    result = bound_nutation_reference(series,t)[0]
    with localcontext() as context:
        context.prec = 110

        def oracle(days):
            centuries = days/36525
            coefficients = map(D.from_float,(485868.249036,1717915923.2178,31.8792,.051635,-.00024470))
            angle = sum(c*centuries**power for power,c in enumerate(coefficients))*D.from_float(_ARCSEC)
            pi = D('3.141592653589793238462643383279502884197169399375105820974944592307816406286208998628034825342117068')
            angle %= 2*pi
            if angle>pi:
                angle -= 2*pi
            value = term = angle
            for n in range(1,100):
                term *= -angle*angle/D(2*n*(2*n+1))
                value += term
            return value*D(1_000_000)*D.from_float(1e-6/3600)*D.from_float(DEG2RAD)*(centuries if time_order else 1)

        center,h = D(x.numerator)/D(x.denominator),D('1e-20')
        middle,before,after = oracle(center),oracle(center-h),oracle(center+h)
        assert result[0].contains(F(middle))
        assert result[1].contains(F((after-before)/(2*h)))
        assert result[2].contains(F((after-2*middle+before)/(h*h)))


@pytest.mark.parametrize('anchor',[1045155.5,2459891.96,2763363.])
def test_taylor_and_rounding_tube_contains_current_native_series(anchor):
    series = freeze_orientation_series()
    domain = I(F(-6,86400),F(6,86400))
    t = j.scale(j.add(j.variable(domain),j.constant(F.from_float(anchor)-2451545)),F(1,36525))
    whole = bound_nutation_reference(series,t)
    center = j.scale(j.add(j.variable(I.point(0)),j.constant(F.from_float(anchor)-2451545)),F(1,36525))
    point = bound_nutation_reference(series,center)
    errors = serving_nutation_error_radians(series,anchor,domain)
    result = taylor_nutation_bounds(series,anchor,domain,F(0),point,whole,error_radians=errors)
    for offset in (F(-5,86400),F(0),F(5,86400)):
        actual = nutation_2000a(float(F.from_float(anchor)+offset))
        assert result.longitude_degrees.contains(F.from_float(actual[0]))
        assert result.obliquity_degrees.contains(F.from_float(actual[1]))
    assert all(error>0 for error in errors)
