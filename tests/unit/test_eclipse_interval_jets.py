"""Exact polynomial and independent Decimal chain-rule witnesses."""
from decimal import Decimal as D, localcontext
from fractions import Fraction as F

import pytest

from moira import _eclipse_interval_jets as j
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable


def test_polynomial_jets_cover_values_and_both_derivatives():
    value = j.polynomial(j.variable(I(F(-1,3),F(2,3))), (1,2,-3,4))
    for t in (F(-1,3),F(0),F(2,3)):
        assert value[0].contains(1+2*t-3*t*t+4*t**3)
        assert value[1].contains(2-6*t+12*t*t)
        assert value[2].contains(-6+24*t)


def test_composed_norm_inverse_and_trig_derivatives():
    t = F(1,3)
    x = j.variable(I.point(t))
    result = j.div(j.sin_cos(j.mul(x,x))[0],j.sqrt(j.add(j.constant(1),j.square(x))))
    with localcontext() as context:
        context.prec = 100

        def oracle(z):
            angle = z*z
            term = total = angle
            for n in range(1,100):
                term *= -angle*angle/D(2*n*(2*n+1))
                total += term
            return total/(1+z*z).sqrt()

        center,h = D(t.numerator)/D(t.denominator),D('1e-25')
        y,prior,later = oracle(center),oracle(center-h),oracle(center+h)
        assert result[0].contains(F(y))
        assert result[1].contains(F((later-prior)/(2*h)))
        assert result[2].contains(F((later-2*y+prior)/(h*h)))


@pytest.mark.parametrize('operation', [j.inverse,j.sqrt])
def test_singular_domains_are_not_differentiated(operation):
    with pytest.raises(EnclosureUnavailable):
        operation(j.variable(I(-1,1)))
