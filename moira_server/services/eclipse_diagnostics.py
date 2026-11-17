"""Opt-in, bounded eclipse diagnostics using the request's engine reader."""
from __future__ import annotations

from moira._ephemeris_time import _ut1_to_ephemeris_tt
from moira.eclipse import EclipseCalculator, _reader_identity_at
from moira.lunar_shadow_events import inspect_lunar_shadow_candidate
from moira.solar_eclipse_clipped import inspect_instantaneous_clipped_central_boundary
from moira.solar_eclipse_hybrid import classify_solar_central_path
from moira.solar_swept_witness import inspect_swept_central_interior
from moira.solar_visibility_witness import refine_solar_visibility_candidate, solar_visibility_at_site


def _calculator(engine):
    return EclipseCalculator(reader=getattr(engine, "_reader", None))


def _select_solar_event(calc, jd_start_ut1: float, *, backward: bool):
    """Use the core's strict maximum-time selector for either direction."""
    search = calc.previous_solar_eclipse if backward else calc.next_solar_eclipse
    return search(jd_start_ut1, kind="any")


def compute_hybrid_diagnostic(engine, request):
    calc = _calculator(engine)
    event = _select_solar_event(calc, request.jd_start_ut1, backward=request.backward)
    result = classify_solar_central_path(calc, event, max_evaluations=request.max_evaluations)
    jd_tt = _ut1_to_ephemeris_tt(event.jd_ut, calc._reader)
    identity = _reader_identity_at(calc._reader, jd_tt)
    return event, result, identity.summary_label if identity else "unidentified"


def compute_lunar_shadow_candidate(engine, request):
    calc = _calculator(engine)
    result = inspect_lunar_shadow_candidate(
        calc, request.center_jd_ut1, policy=request.policy,
        earth_radius_scale=request.earth_radius_scale,
        window_days=request.window_days, coarse_step_seconds=request.coarse_step_seconds,
    )
    reference_jd = result.event.greatest_jd_ut if result.event else request.center_jd_ut1
    identity = _reader_identity_at(calc._reader, _ut1_to_ephemeris_tt(reference_jd, calc._reader))
    return result, reference_jd, identity.summary_label if identity else "unidentified"


def compute_solar_visibility_site(engine, request):
    return solar_visibility_at_site(
        _calculator(engine), request.jd_ut1, request.latitude_deg, request.longitude_deg,
        lunation=request.lunation, tolerance_rad=request.tolerance_rad,
    )


def compute_solar_visibility_refinement(engine, request):
    return refine_solar_visibility_candidate(
        _calculator(engine), (request.seed.jd_ut1, request.seed.latitude_deg, request.seed.longitude_deg),
        time_bounds_ut1=request.time_bounds_ut1,
        latitude_bounds_deg=request.latitude_bounds_deg,
        longitude_bounds_deg=request.longitude_bounds_deg,
        max_iterations=request.max_iterations,
        time_tolerance_seconds=request.time_tolerance_seconds,
        angular_tolerance_deg=request.angular_tolerance_deg,
        lunation=request.lunation, tolerance_rad=request.tolerance_rad,
    )


def compute_clipped_central_boundary(engine, request):
    return inspect_instantaneous_clipped_central_boundary(
        _calculator(engine), request.jd_ut1, arc_samples=request.arc_samples,
    )


def compute_swept_central_interior(engine, request):
    return inspect_swept_central_interior(
        _calculator(engine), request.latitude_deg, request.longitude_deg,
        request.times_ut1, interval_ut1=request.interval_ut1,
        lunation=request.lunation, tolerance_rad=request.tolerance_rad,
    )
