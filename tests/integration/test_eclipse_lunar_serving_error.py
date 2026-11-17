"""Derived uniform tubes contain literal native/reference discrepancies."""
from fractions import Fraction as F

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_frozen_native_vectors import freeze_native_vector_scope
from moira._eclipse_lunar_serving_error import derive_lunar_serving_error_tube
from moira._eclipse_piecewise_vectors import enclose_piecewise_eclipse_vectors
from moira._eclipse_lunar_piecewise_extrema import bound_piecewise_lunar_observables
from moira.eclipse import _eclipse_body_pair
from moira.lunar_shadow_models import danjon_angular_shadow,spherical_cone_shadow
from moira.constants import EARTH_RADIUS_KM


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize('anchor',[1124726.318610764,2001312.523536443,2459891.96,2740492.6247106483])
def test_whole_domain_error_not_fitted_to_native_samples(planetary_reader,anchor):
    domain = I(F(-3,10),F(3,10))
    scope = freeze_native_vector_scope(planetary_reader,anchor,domain)
    tube = derive_lunar_serving_error_tube(scope)
    assert tube.finite_split_route_under_premises and tube.geometry_guards_under_premises
    assert max(tube.danjon_margin_errors_rad)<F(1,10**7)
    assert max(tube.cone_margin_errors_km)<F(1,100)
    for seconds in (-10,0,10):
        tt = anchor+seconds/86400
        offset = F.from_float(tt)-F.from_float(anchor)
        reference = enclose_piecewise_eclipse_vectors(scope.model,I.point(offset))
        sun,moon = _eclipse_body_pair(tt,planetary_reader,sun_retarded=True,moon_retarded=False)
        for vector,actual,error in ((reference.sun,sun,tube.sun_vector_l2_error_km),
                                   (reference.moon,moon,tube.moon_vector_l2_error_km)):
            assert sum(((I.point(value)-component[0]).magnitude for value,component in zip(actual,vector)),F(0))<=error
        for policy,scale,errors,geometry in (
            ('danjon_angular',1.,tube.danjon_margin_errors_rad,danjon_angular_shadow(sun,moon)),
            ('static_finite_cone',1.01,tube.cone_margin_errors_km,spherical_cone_shadow(sun,moon,earth_radius_scale=1.01))):
            real = bound_piecewise_lunar_observables(reference,policy=policy,earth_radius_km=EARTH_RADIUS_KM*scale)
            actual = geometry.penumbral_margin,geometry.umbral_margin,geometry.total_margin
            assert all((value+I(-error,error)).contains(native)
                       for value,error,native in zip(real.values[2:],errors,actual))
