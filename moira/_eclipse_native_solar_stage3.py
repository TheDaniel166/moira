"""Scoped Stage 3 native solar coverage with frozen resources and float cells.

The trusted binary pin is supplied independently by the caller. Each run
checks the same-thread strict FP guard, freezes/compares actual type-2 words,
and checks source/table/resource stability. The interval theorem still names
its IEEE, libm, compiler and unchanged-resource premises. Represented-input
coverage is separate from the continuous reference and physical accuracy.
"""
from dataclasses import dataclass
from fractions import Fraction as F
import hashlib
from pathlib import Path
import sys

from . import _eclipse_interval_jets as j
from ._eclipse_interval import RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_clock_provider import bound_native_ut1_to_tt
from ._eclipse_orientation_reference import (freeze_orientation_series,
    bound_nutation_reference,taylor_nutation_bounds,serving_nutation_error_radians)
from ._eclipse_piecewise_vectors import freeze_eclipse_records
from ._eclipse_frozen_native_vectors import freeze_native_vector_scope
from ._eclipse_native_clock_bounds import _snapshot_sources
from ._eclipse_polar_motion_bounds import _table_snapshot
from ._eclipse_earth_fixed_bounds import bound_conditional_earth_fixed_solar_vectors
from ._eclipse_solar_native_predicates import bound_native_solar_predicates
from ._eclipse_solar_float_coverage import cover_native_solar_float_path, SolarFloatPathCoverage
from .spk_reader import SpkReader
from .eclipse import (_earth_fixed_solar_shadow,_axis_surface_point_from_shadow,
    _shadow_dot,_shadow_subtract,_wgs84_surface_normal_unit)
from . import _moira_native


@dataclass(frozen=True, slots=True)
class NativeSolarStage3Evidence:
    """Coverage plus the exact resources and distinct theorem premises used."""

    coverage: SolarFloatPathCoverage
    kernel_sha256_at_reader_open: str
    frozen_record_word_sha256: tuple[str,...]
    native_binary_sha256: str
    orientation_series_sha256: str
    source_file_sha256: tuple[tuple[str,str],...]
    nutation_point_evaluations: int
    binary_pin_matched: bool
    same_thread_rn_gradual_guard_passed: bool
    source_and_table_stability_checked: bool
    conditionally_complete_native_input_coverage: bool
    compiler_and_libm_contract_required: bool = True
    physical_accuracy_certified: bool = False


def _source_pins():
    root = Path(__file__).resolve().parent
    files = sorted({Path(module.__file__).resolve() for name,module in tuple(sys.modules.items())
                    if name.startswith('moira') and getattr(module,'__file__',None)
                    and str(module.__file__).endswith('.py') and Path(module.__file__).resolve().is_relative_to(root)})
    return tuple((str(path),hashlib.sha256(path.read_bytes()).hexdigest()) for path in files)


def _fp_guard():
    contract = _moira_native._eclipse_strict_snapshot_build_contract()
    if contract!='moira_eclipse_scalar_snapshot_binary64_rn_gradual_v1':
        raise EnclosureUnavailable('required native arithmetic guard unavailable')
    result = _moira_native._eclipse_strict_snapshot_evaluate(
        ((1.,),(2.,),(3.,)),2451545.,0.,-86400.,172800.,1,0,-86400.,86400.)
    if tuple(result[0])!=(1.,2.,3.):
        raise EnclosureUnavailable('native arithmetic guard/control failed')


def inspect_native_solar_stage3_domain(calc, anchor: float, domain: I, *,
                                       trusted_native_binary_sha256: str,
                                       tolerance=F(1,86400000),
                                       max_interval_evaluations=4096,max_point_evaluations=8192,
                                       progress=None):
    """Prove conditional native-input coverage, retaining every unclosed cell.

    This private entry point operates on direct DE type-2 routes and the FW
    orientation branch. It does not expose a new REST contract. A native pin
    must come from an independently accepted build record, rather than being
    inferred here from the inspected binary. Source/data mutation, unavailable
    bounds, exhausted work and actual serving errors cannot become absence.
    """
    reader = calc._reader
    if type(reader) is not SpkReader or reader._closed:
        raise EnclosureUnavailable('open direct SpkReader required')
    native_path = Path(_moira_native.__file__).resolve()
    binary_hash = hashlib.sha256(native_path.read_bytes()).hexdigest()
    if not isinstance(trusted_native_binary_sha256,str) or binary_hash!=trusted_native_binary_sha256:
        raise EnclosureUnavailable('native binary differs from the independent trusted pin')
    _fp_guard()
    kernel_stat = Path(reader.path).stat()
    kernel_handle = reader._kernel._handle
    # Snapshot data before pinning imported source files, so lazy imports are
    # included in the stability check and cannot create a false discrepancy.
    mapped = bound_native_ut1_to_tt(reader,anchor,domain)
    tt_domain = I.point(mapped.bounds.anchor_jd)+mapped.bounds.output_offset_days-anchor
    frozen = freeze_native_vector_scope(reader,anchor,tt_domain)
    records = frozen.model
    series = freeze_orientation_series()
    clock_tables = _snapshot_sources()
    polar_table = _table_snapshot()
    full_t = j.scale(j.add(j.variable(tt_domain),j.constant(F.from_float(anchor)-2451545)),F(1,36525))
    whole = bound_nutation_reference(series,full_t)
    nutation_errors = serving_nutation_error_radians(series,anchor,tt_domain)
    points = {}
    interval_calls = 0
    scope_modules = ('moira.julian','moira.eclipse','moira.corrections','moira.coordinates',
                     'moira._eclipse_solar_serving','moira._eclipse_earth_fixed_bounds',
                     'moira.spk_reader')
    bindings = tuple((name,key,value) for name in scope_modules
                     for key,value in vars(sys.modules[name]).items() if callable(value))

    def enclosure(box):
        nonlocal interval_calls
        interval_calls += 1
        if progress is not None and interval_calls%32==0:
            progress(dict(interval_evaluations=interval_calls,nutation_points=len(points),
                          current_width_seconds=float(box.width*86400)))
        mapped = bound_native_ut1_to_tt(reader,anchor,box)
        tt = I.point(mapped.bounds.anchor_jd)+mapped.bounds.output_offset_days-anchor
        near = min(points,key=lambda point:abs(point-tt.midpoint)) if points else None
        # One new point near a critical cell removes the broad Taylor error;
        # the whole-domain curvature still proves its complete time range.
        if near is None or tt.width<F(1,86400) and abs(near-tt.midpoint)>F(30,86400):
            near = tt.midpoint
            t = j.scale(j.add(j.variable(I.point(near)),
                j.constant(F.from_float(anchor)-2451545)),F(1,36525))
            points[near] = bound_nutation_reference(series,t)
        nutation = taylor_nutation_bounds(series,anchor,tt,near,points[near],whole,
                                         error_radians=nutation_errors)
        source = bound_conditional_earth_fixed_solar_vectors(reader,anchor,box,anchor,tt,
            assume_ieee_arithmetic=True,assume_correctly_rounded_integer_powers=True,
            assume_finite_unit_trig_within_one_ulp=True,assume_registered_nutation_tables_match=True,
            assume_builtin_sum_error=True,assume_correctly_rounded_sqrt=True,
            nutation_enclosure=nutation,tight_light_time_norm=True,refined_split_clock=True,
            correlated_moon=True,frozen_native_scope=frozen,tight_sidereal=True)
        return bound_native_solar_predicates(box,source)

    def evaluate(jd):
        shadow = _earth_fixed_solar_shadow(calc,jd)
        if shadow is None:
            return 'none'
        axis = _axis_surface_point_from_shadow(shadow)
        if axis is None:
            return 'none'
        xyz = axis.xyz_itrf_km
        sunward = _shadow_subtract(shadow.sun_xyz_from_earth_itrf_km,xyz)
        # A positive norm does not change the sign of the witness's horizon
        # predicate. Evaluate the source's actual normalized expression.
        import math
        daylight = _shadow_dot(_wgs84_surface_normal_unit(xyz),sunward)/math.sqrt(_shadow_dot(sunward,sunward))
        if daylight<=0:
            return 'none'
        radius = shadow.central_radius_km-shadow.central_cone_slope*_shadow_dot(
            _shadow_subtract(xyz,shadow.fundamental_plane_point_xyz_km),shadow.axis_unit_away_from_sun)
        return 'total' if radius>0 else 'annular' if radius<0 else 'zero_radius'

    # Warm the lazy source imports before recording their content pins.
    evaluate(float(anchor))
    enclosure(I.point(domain.midpoint))
    pins = _source_pins()
    coverage = cover_native_solar_float_path(anchor,domain,enclosure,evaluate,tolerance=tolerance,
        max_interval_evaluations=max_interval_evaluations,max_point_evaluations=max_point_evaluations)
    _fp_guard()
    if any(getattr(sys.modules[name],key,None) is not value for name,key,value in bindings):
        raise EnclosureUnavailable('serving callable binding changed during coverage')
    after = Path(reader.path).stat()
    if (after.st_size,after.st_mtime_ns)!=(kernel_stat.st_size,kernel_stat.st_mtime_ns):
        raise EnclosureUnavailable('kernel file metadata changed during coverage')
    if reader._closed or reader._kernel._handle is not kernel_handle:
        raise EnclosureUnavailable('reader/kernel handle changed during coverage')
    if (_snapshot_sources()!=clock_tables or _table_snapshot()!=polar_table
            or freeze_eclipse_records(reader,anchor,records.domain)!=records):
        raise EnclosureUnavailable('clock, polar table or copied raw records changed during coverage')
    if _source_pins()!=pins or freeze_orientation_series()!=series:
        raise EnclosureUnavailable('source or orientation tables changed during coverage')
    if hashlib.sha256(native_path.read_bytes()).hexdigest()!=binary_hash:
        raise EnclosureUnavailable('native binary changed during coverage')
    return NativeSolarStage3Evidence(coverage,records.kernel_sha256_at_reader_open,
        tuple(record.sha256 for record in records.records),binary_hash,series.sha256,pins,len(points),
        True,True,True,coverage.all_represented_inputs_covered)
