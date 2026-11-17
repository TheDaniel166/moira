"""Native solar coverage with a derived radius capsule at shallow extrema.

The existing literal-operation adapter retains all source/axis/root/daylight
guards. Only its signed-radius interval is intersected with the independent
continuous scalar enclosure plus a derived native error. Every accepted
box is corroborated at both represented endpoints; remaining cells are
exhaustively evaluated or explicitly unresolved. No native IVT is asserted.
"""
from dataclasses import dataclass,replace
from fractions import Fraction as F
import hashlib
from pathlib import Path

from . import _eclipse_interval_jets as j
from . import _moira_native
from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_clock_provider import bound_native_ut1_to_tt
from ._eclipse_frozen_native_vectors import freeze_native_vector_scope
from ._eclipse_orientation_reference import (freeze_orientation_series,bound_nutation_reference,
    taylor_nutation_bounds,serving_nutation_error_radians)
from ._eclipse_earth_fixed_bounds import bound_conditional_earth_fixed_solar_vectors
from ._eclipse_solar_native_predicates import bound_native_solar_predicates
from ._eclipse_solar_float_coverage import cover_native_solar_float_path
from ._eclipse_continuous_solar_stage3 import prepare_continuous_solar_stage3
from ._eclipse_solar_scalar_taylor import scalar_taylor_solar_provider
from ._eclipse_solar_radius_error import derive_solar_radius_error_scope,bound_solar_radius_serving_error
from ._eclipse_stage3_route_obligations import prove_stage3_clock_route_obligations
from ._eclipse_native_solar_stage3 import _fp_guard,_source_pins
from ._eclipse_native_clock_bounds import _snapshot_sources
from ._eclipse_polar_motion_bounds import _table_snapshot
from .eclipse import (_earth_fixed_solar_shadow,_axis_surface_point_from_shadow,
    _shadow_dot,_shadow_subtract,_wgs84_surface_normal_unit)
from .spk_reader import SpkReader


@dataclass(frozen=True, slots=True)
class RefinedNativeSolarEvidence:
    """Complete or bounded-unknown native coverage and independent resources."""

    coverage: object
    clock_obligations: object
    radius_error_scope: object
    kernel_sha256_at_reader_open: str
    native_binary_sha256: str
    source_file_sha256: tuple
    frozen_record_word_sha256: tuple
    radius_contractions: int
    nutation_points: int
    reference_statistics: dict
    same_thread_rn_gradual_guard_passed: bool
    source_tables_reader_and_record_stability_checked: bool
    compiler_and_libm_contract_required: bool = True
    physical_accuracy_certified: bool = False


def inspect_refined_native_solar(calc,anchor: float,domain: I, *,trusted_native_binary_sha256,
                                  max_interval_evaluations=8192,max_point_evaluations=32768,
                                  progress=None):
    """Close native shallow-radius boxes with an independently derived tube."""
    import math
    reader = calc._reader
    if type(reader) is not SpkReader or reader._closed:
        raise EnclosureUnavailable('open direct reader required for refined native solar coverage')
    native_path = Path(_moira_native.__file__)
    binary = hashlib.sha256(native_path.read_bytes()).hexdigest()
    if binary!=trusted_native_binary_sha256:
        raise EnclosureUnavailable('native binary differs from independently accepted build pin')
    _fp_guard()
    stat = Path(reader.path).stat()
    handle = reader._kernel._handle
    mapped = bound_native_ut1_to_tt(reader,anchor,domain)
    tt_domain = I.point(mapped.bounds.anchor_jd)+mapped.bounds.output_offset_days-anchor
    reference = prepare_continuous_solar_stage3(reader,anchor,domain)
    full_tt = I(min(tt_domain.lo,reference.tt_domain.lo)-F(1,10**7),
                max(tt_domain.hi,reference.tt_domain.hi)+F(1,10**7))
    frozen = freeze_native_vector_scope(reader,anchor,full_tt)
    capsule = derive_solar_radius_error_scope(reference,frozen)
    clock = prove_stage3_clock_route_obligations(reader,anchor,domain)
    series = freeze_orientation_series()
    all_t = j.scale(j.add(j.variable(full_tt),j.constant(F.from_float(anchor)-2451545)),F(1,36525))
    whole = bound_nutation_reference(series,all_t)
    errors = serving_nutation_error_radians(series,anchor,full_tt)
    ref_provider,ref_stats = scalar_taylor_solar_provider(reference)
    points,calls,contractions = {},0,0

    def enclosure(box):
        nonlocal calls,contractions
        calls += 1
        if progress is not None and calls%32==0:
            progress(dict(interval_evaluations=calls,radius_contractions=contractions,
                width_seconds=float(box.width*86400)))
        converted = bound_native_ut1_to_tt(reader,anchor,box)
        tt = I.point(converted.bounds.anchor_jd)+converted.bounds.output_offset_days-anchor
        near = min(points,key=lambda p:abs(p-tt.midpoint)) if points else None
        if near is None or tt.width<F(1,86400) and abs(near-tt.midpoint)>F(30,86400):
            near = tt.midpoint
            t = j.scale(j.add(j.variable(I.point(near)),j.constant(F.from_float(anchor)-2451545)),F(1,36525))
            points[near] = bound_nutation_reference(series,t)
        nutation = taylor_nutation_bounds(series,anchor,tt,near,points[near],whole,error_radians=errors)
        source = bound_conditional_earth_fixed_solar_vectors(reader,anchor,box,anchor,tt,
            assume_ieee_arithmetic=True,assume_correctly_rounded_integer_powers=True,
            assume_finite_unit_trig_within_one_ulp=True,assume_registered_nutation_tables_match=True,
            assume_builtin_sum_error=True,assume_correctly_rounded_sqrt=True,
            nutation_enclosure=nutation,tight_light_time_norm=True,refined_split_clock=True,
            correlated_moon=True,frozen_native_scope=frozen,tight_sidereal=True)
        result = bound_native_solar_predicates(box,source)
        if result.signed_radius is not None and result.signed_radius.contains_zero:
            halo = capsule.comparison_ut1_halo_days
            comparison = I(box.lo-halo,box.hi+halo)
            if comparison.lo<domain.lo or comparison.hi>domain.hi:
                return result
            nominal = ref_provider(comparison)
            if nominal.signed_radius is not None:
                error = bound_solar_radius_serving_error(capsule,nominal)
                tightened = result.signed_radius.intersect(nominal.signed_radius+I(-error,error))
                if tightened is None:
                    raise ArithmeticError('derived native solar-radius capsule disagrees with literal bounds')
                if tightened.width<result.signed_radius.width:
                    contractions += 1
                    result = replace(result,signed_radius=tightened)
        return result

    def evaluate(jd):
        shadow = _earth_fixed_solar_shadow(calc,jd)
        if shadow is None:
            return 'none'
        point = _axis_surface_point_from_shadow(shadow)
        if point is None:
            return 'none'
        xyz = point.xyz_itrf_km
        sunward = _shadow_subtract(shadow.sun_xyz_from_earth_itrf_km,xyz)
        daylight = _shadow_dot(_wgs84_surface_normal_unit(xyz),sunward)/math.sqrt(_shadow_dot(sunward,sunward))
        if daylight<=0:
            return 'none'
        radius = shadow.central_radius_km-shadow.central_cone_slope*_shadow_dot(
            _shadow_subtract(xyz,shadow.fundamental_plane_point_xyz_km),shadow.axis_unit_away_from_sun)
        return 'total' if radius>0 else 'annular' if radius<0 else 'zero_radius'

    evaluate(float(anchor))
    enclosure(I.point(domain.midpoint))
    pins = _source_pins()
    tables,polar = _snapshot_sources(),_table_snapshot()
    coverage = cover_native_solar_float_path(anchor,domain,enclosure,evaluate,
        tolerance=F(1,86400000),max_interval_evaluations=max_interval_evaluations,
        max_point_evaluations=max_point_evaluations)
    _fp_guard()
    after = Path(reader.path).stat()
    if reader._closed or reader._kernel._handle is not handle:
        raise EnclosureUnavailable('native reader handle changed during refined coverage')
    if (stat.st_size,stat.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
        raise EnclosureUnavailable('native kernel file metadata changed during refined coverage')
    if (_source_pins()!=pins or _snapshot_sources()!=tables or _table_snapshot()!=polar
            or freeze_native_vector_scope(reader,anchor,full_tt)!=frozen):
        raise EnclosureUnavailable('source/table/frozen-record stability check failed')
    if hashlib.sha256(native_path.read_bytes()).hexdigest()!=binary:
        raise EnclosureUnavailable('native binary changed during refined coverage')
    return RefinedNativeSolarEvidence(coverage,clock,capsule,frozen.model.kernel_sha256_at_reader_open,
        binary,pins,tuple(record.sha256 for record in frozen.model.records),contractions,len(points),
        ref_stats,True,True)
