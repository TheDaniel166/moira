"""Derived source/geometry capsules cover literal native discrepancies."""
from fractions import Fraction as F

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_solar_radius_error import sharp_native_record_error,derive_solar_radius_error_scope,bound_solar_radius_serving_error
from moira._eclipse_native_spk_bounds import conditional_native_type2_bounds
from moira._eclipse_continuous_solar_stage3 import prepare_continuous_solar_stage3
from moira._eclipse_frozen_native_vectors import freeze_native_vector_scope
from moira._eclipse_solar_scalar_taylor import scalar_taylor_solar_provider
from moira._eclipse_clock_provider import bound_native_ut1_to_tt
from moira._eclipse_refined_native_solar import inspect_refined_native_solar
from moira.eclipse import EclipseCalculator,_earth_fixed_solar_shadow,_axis_surface_point_from_shadow,_shadow_dot,_shadow_subtract
from tests.integration.test_eclipse_correlated_emb import _exact_record


PIN = 'b5a215bc9f1f749bd08ce2fe4d7bc449f564122f410ba1fb8e25569a56f207ba'


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize('epoch',[1045155.,2451545.,2763363.])
@pytest.mark.parametrize('offset',[.125,.5,.875])
def test_weighted_clenshaw_error_contains_independent_exact_polynomial(planetary_reader,epoch,offset):
    state = conditional_native_type2_bounds(planetary_reader,0,3,epoch,I.point(offset))
    error = sharp_native_record_error(state)
    actual = planetary_reader._position_tdb_offset(0,3,epoch,offset)
    exact = _exact_record(state,offset)
    assert all(abs(F.from_float(native)-real)<=limit for native,real,limit in zip(actual,exact,error))


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize('epoch',[1421936.2171787173,1685704.3261082352,2379997.9696220569])
def test_uniform_capsule_covers_native_radius_without_residual_calibration(planetary_reader,epoch):
    domain = I(F(-1,6),F(1,6))
    reference = prepare_continuous_solar_stage3(planetary_reader,epoch,domain)
    mapped = bound_native_ut1_to_tt(planetary_reader,epoch,domain)
    native_tt = I.point(mapped.bounds.anchor_jd)+mapped.bounds.output_offset_days-epoch
    full = I(min(native_tt.lo,reference.tt_domain.lo)-F(1,10**7),
             max(native_tt.hi,reference.tt_domain.hi)+F(1,10**7))
    native_scope = freeze_native_vector_scope(planetary_reader,epoch,full)
    capsule = derive_solar_radius_error_scope(reference,native_scope)
    provider,_ = scalar_taylor_solar_provider(reference)
    calc = EclipseCalculator(reader=planetary_reader)
    for seconds in (-60,0,60):
        jd = epoch+seconds/86400
        box = I.point(F.from_float(jd)-F.from_float(epoch))
        halo = capsule.comparison_ut1_halo_days
        real = provider(I(box.lo-halo,box.hi+halo))
        error = bound_solar_radius_serving_error(capsule,real)
        shadow = _earth_fixed_solar_shadow(calc,jd)
        point = _axis_surface_point_from_shadow(shadow)
        radius = shadow.central_radius_km-shadow.central_cone_slope*_shadow_dot(
            _shadow_subtract(point.xyz_itrf_km,shadow.fundamental_plane_point_xyz_km),shadow.axis_unit_away_from_sun)
        assert (real.signed_radius+I(-error,error)).contains(F.from_float(radius))


@pytest.mark.requires_ephemeris
def test_shallow_native_radius_case_closes_with_capsule(planetary_reader):
    result = inspect_refined_native_solar(EclipseCalculator(reader=planetary_reader),
        1421936.2171787173,I(F(-1,6),F(1,6)),trusted_native_binary_sha256=PIN)
    assert result.coverage.all_represented_inputs_covered
    assert result.coverage.event_interval_enclosed
    assert result.radius_contractions>0
