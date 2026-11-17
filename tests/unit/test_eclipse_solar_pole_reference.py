"""Rotated-metric jets agree with independently explicit frame geometry."""
from fractions import Fraction as F

import pytest

from moira import _eclipse_interval_jets as j
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_solar_axis_reference import bound_solar_axis_reference
from moira._eclipse_solar_pole_reference import bound_solar_pole_reference


@pytest.mark.parametrize('time',[F(-1,100),F(0),F(1,100)])
def test_equivalent_oblate_rotated_line_values_and_derivatives(time):
    t = j.variable(I.point(time))
    sun = tuple(j.constant(value) for value in (1.5e8,1e6,3e7))
    moon = (j.constant(360000),j.add(j.constant(2400),j.scale(t,100000)),j.constant(76000))
    matrix = j.matrix_product(j.rotation_x(j.constant(.31)),j.rotation_z(j.scale(t,6.3)))
    pole = matrix[2]
    transformed_sun,transformed_moon = j.matrix_vector(matrix,sun),j.matrix_vector(matrix,moon)
    explicit = bound_solar_axis_reference(I.point(time),
        tuple(a[0] for a in transformed_sun),tuple(a[0] for a in transformed_moon),
        sun_rate=tuple(a[1] for a in transformed_sun),moon_rate=tuple(a[1] for a in transformed_moon),
        continuous_model=True)
    metric = bound_solar_pole_reference(I.point(time),sun,moon,pole,continuous_model=True)
    assert metric.axis_margin.intersect(explicit.axis_margin) is not None
    assert metric.axis_derivative.intersect(explicit.axis_derivative) is not None
    if explicit.signed_radius is not None:
        assert metric.signed_radius.intersect(explicit.signed_radius) is not None
        assert metric.radius_derivative.intersect(explicit.radius_derivative) is not None
