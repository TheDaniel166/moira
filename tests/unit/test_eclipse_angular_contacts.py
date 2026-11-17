"""Independent decimal angular geometry and contact-domain controls."""
from dataclasses import replace
from decimal import Decimal, localcontext
from fractions import Fraction as F

import pytest

from moira._eclipse_angular_contacts import bound_angular_lunar_contacts
from moira._eclipse_continuous_lunar_contacts import isolate_lunar_margin_triplet
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable
from tests.unit.test_eclipse_continuous_lunar_contacts import _affine


RADII = dict(earth_radius_km=2, sun_radius_km=4, moon_radius_km=F(1, 2))


def _asin(x):
    value, power, coefficient = Decimal(0), x, Decimal(1)
    for n in range(180):
        value += coefficient*power/(2*n+1)
        coefficient *= Decimal(2*n+1)/Decimal(2*n+2)
        power *= x*x
    return value


def _atan(x):
    value, power = Decimal(0), x
    for n in range(180):
        value += power/(2*n+1) if n % 2 == 0 else -power/(2*n+1)
        power *= x*x
    return value


def _decimal_margins(time):
    distance = (time*time + Decimal(100)).sqrt()
    factor = Decimal.from_float(1.01)
    beta = factor*_asin(Decimal(2)/distance) + _asin(Decimal(2)/20)
    solar = _asin(Decimal(4)/20)
    alpha = _asin(Decimal('0.5')/distance)
    theta = _atan(abs(time)/10)
    return beta + solar + alpha - theta, beta - solar + alpha - theta, beta - solar - alpha - theta


@pytest.mark.parametrize('time', [F(-2), F(-1, 2), F(1, 2), F(2)])
def test_angular_values_and_rates_match_independent_decimal_samples(time):
    value = bound_angular_lunar_contacts(_affine(I.point(time)), **RADII)
    with localcontext() as context:
        context.prec = 100
        t = Decimal(time.numerator)/Decimal(time.denominator)
        h = Decimal('1e-24')
        exact, left, right = _decimal_margins(t), _decimal_margins(t-h), _decimal_margins(t+h)
        for bounded, rate, expected, before, after in zip(value.margins, value.derivatives, exact, left, right):
            assert bounded.contains(F(expected))
            assert rate.contains(F((after-before)/(2*h)))


def test_six_angular_contacts_share_a_cover_and_a_budget():
    def enclosure(box):
        return bound_angular_lunar_contacts(_affine(box), **RADII)

    result = isolate_lunar_margin_triplet(
        I(-8, 8), enclosure, tolerance=F(1, 1000), continuity_assumed=True,
        margin_unit='rad', model_policy='danjon_angular_reference', max_evaluations=2000,
    )
    assert result.margin_unit == 'rad' and result.model_policy == 'danjon_angular_reference'
    for partition in (result.penumbral, result.umbral, result.total):
        assert partition.complete
        assert len([cell for cell in partition.cells if cell.status == 'unique']) == 2
        assert partition.cells[0].interval.lo == -8 and partition.cells[-1].interval.hi == 8
    assert not result.eclipse_absence_certified


def test_angular_domain_and_axis_singularity_are_explicit():
    with pytest.raises(EnclosureUnavailable, match='antisolar'):
        bound_angular_lunar_contacts(_affine(I.point(0), z=-10), **RADII)
    value = bound_angular_lunar_contacts(_affine(I.point(0)), **RADII)
    assert all(rate is None for rate in value.derivatives)
    discontinuous = bound_angular_lunar_contacts(
        replace(_affine(I.point(1)), continuous_on_domain=False), **RADII)
    assert all(rate is None for rate in discontinuous.derivatives)
