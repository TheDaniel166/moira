"""Actual shadow-operation inclusion with the refined source options."""
from fractions import Fraction as F
import math

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_earth_fixed_bounds import bound_conditional_earth_fixed_solar_vectors
from moira._eclipse_solar_native_predicates import bound_native_solar_predicates
from moira.eclipse import (_earth_fixed_solar_shadow,_wgs84_line_intersection_parameters,
    _axis_surface_point_from_shadow,_WGS84_AXIS_TANGENCY_TOLERANCE_KM2,
    _shadow_dot,_shadow_subtract,_wgs84_surface_normal_unit)


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize('ut', [1045155.0252075894,2457987.2685,2460054.68])
def test_refined_bounds_include_serving_discriminant_radius_and_daylight(planetary_reader,eclipse_calculator,ut):
    tt = ut+.001
    bounds = bound_conditional_earth_fixed_solar_vectors(planetary_reader,ut,I.point(0),tt,I.point(0),
        assume_ieee_arithmetic=True,assume_correctly_rounded_integer_powers=True,
        assume_finite_unit_trig_within_one_ulp=True,assume_registered_nutation_tables_match=True,
        assume_builtin_sum_error=True,assume_correctly_rounded_sqrt=True,
        tight_light_time_norm=True,refined_split_clock=True)
    result = bound_native_solar_predicates(I.point(0),bounds)
    shadow = _earth_fixed_solar_shadow(eclipse_calculator,ut,jd_tt=tt)
    half,_ = _wgs84_line_intersection_parameters(shadow.fundamental_plane_point_xyz_km,
                                                 shadow.axis_unit_away_from_sun)
    assert result.axis_margin.contains(F.from_float(half)+F.from_float(_WGS84_AXIS_TANGENCY_TOLERANCE_KM2))
    axis = _axis_surface_point_from_shadow(shadow)
    if axis is not None:
        xyz = axis.xyz_itrf_km
        radius = shadow.central_radius_km-shadow.central_cone_slope*_shadow_dot(
            _shadow_subtract(xyz,shadow.fundamental_plane_point_xyz_km),shadow.axis_unit_away_from_sun)
        sun = _shadow_subtract(shadow.sun_xyz_from_earth_itrf_km,xyz)
        altitude = _shadow_dot(_wgs84_surface_normal_unit(xyz),sun)/math.sqrt(_shadow_dot(sun,sun))
        assert result.signed_radius.contains(F.from_float(radius))
        assert result.daylight_margin.contains(F.from_float(altitude))
    assert not result.real_continuous_model
