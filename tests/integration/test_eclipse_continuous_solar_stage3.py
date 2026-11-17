"""Continuous clock/rotation/source composition retains the declared units."""
from fractions import Fraction as F

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_continuous_policy_clock import freeze_continuous_policy_clock,bound_continuous_policy_tt
from moira._eclipse_continuous_solar_stage3 import prepare_continuous_solar_stage3,continuous_solar_stage3_provider
from moira._eclipse_clock_provider import bound_native_ut1_to_tt
from moira.eclipse import (EclipseCalculator,_earth_fixed_solar_shadow,
    _axis_surface_point_from_shadow,_shadow_dot,_shadow_subtract)


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize('epoch,branch',[(1045155.0252075894,'historical_hpiers'),
    (2446707.2953674407,'direct_eop'),(2763363.8118256605,'future_scenario')])
def test_complete_policy_clock_interpolation_and_rate(planetary_reader,epoch,branch):
    domain = I(F(-1,6),F(1,6))
    scope = freeze_continuous_policy_clock(planetary_reader,epoch,domain)
    result,continuous = bound_continuous_policy_tt(scope,domain)
    assert scope.branch==branch and continuous
    assert F(999,1000)<result[1].lo<=result[1].hi<F(1001,1000)
    actual = bound_native_ut1_to_tt(planetary_reader,epoch,domain)
    native = I.point(actual.bounds.anchor_jd)+actual.bounds.output_offset_days-epoch
    assert result[0].lo>=native.lo and result[0].hi<=native.hi
    h = F(1,86400)
    left,_ = bound_continuous_policy_tt(scope,I.point(-h))
    right,_ = bound_continuous_policy_tt(scope,I.point(h))
    secant = (right[0]-left[0])/(2*h)
    assert result[1].intersect(secant) is not None


@pytest.mark.requires_ephemeris
def test_continuous_axis_derivative_matches_independent_serving_secant(planetary_reader):
    epoch = 1045155.0352075894
    domain = I(F(-2,86400),F(2,86400))
    scope = prepare_continuous_solar_stage3(planetary_reader,epoch,domain,panel_count=2)
    provider,stats = continuous_solar_stage3_provider(scope)
    bounds = provider(domain)
    assert bounds.real_continuous_model
    assert not provider(I.point(0)).axis_derivative.contains_zero
    assert bounds.radius_derivative is not None
    calc = EclipseCalculator(reader=planetary_reader)
    values = []
    for seconds in (-1,1):
        shadow = _earth_fixed_solar_shadow(calc,epoch+seconds/86400)
        point = _axis_surface_point_from_shadow(shadow)
        radius = shadow.central_radius_km-shadow.central_cone_slope*_shadow_dot(
            _shadow_subtract(point.xyz_itrf_km,shadow.fundamental_plane_point_xyz_km),
            shadow.axis_unit_away_from_sun)
        values.append((I.point(point.signed_half_chord_sq_km2),I.point(radius)))
        assert bounds.axis_margin.intersect(values[-1][0]) is not None
        assert bounds.signed_radius.intersect(values[-1][1]) is not None
    secant = (values[1][0]-values[0][0])*43200
    radius_secant = (values[1][1]-values[0][1])*43200
    assert bounds.axis_derivative.intersect(secant) is not None
    assert bounds.radius_derivative.intersect(radius_secant) is not None
    assert stats['calls']==2
