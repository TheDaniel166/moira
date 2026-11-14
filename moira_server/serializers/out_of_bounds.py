"""Serializers for out-of-bounds excursion vessels."""

from __future__ import annotations

import math

from moira import datetime_from_jd
from moira.out_of_bounds import (
    OutOfBoundsCrossing,
    OutOfBoundsCulmination,
    OutOfBoundsExcursion,
    OutOfBoundsPolicy,
    OutOfBoundsReport,
    OutOfBoundsScanTruth,
)

from ..models.out_of_bounds import (
    OutOfBoundsCrossingResponse,
    OutOfBoundsCulminationResponse,
    OutOfBoundsExcursionResponse,
    OutOfBoundsPolicyResponse,
    OutOfBoundsScanTruthResponse,
    OutOfBoundsSearchResponse,
)


_JSON_SENTINEL_FOR_INFINITE_SENSITIVITY = -1.0


def _finite_sensitivity(value: float) -> float:
    """Keep a degenerate crossing's sensitivity JSON-representable.

    A crossing whose bound rate is exactly zero has unbounded time
    sensitivity, which JSON cannot carry. It is reported as -1.0 alongside
    ``conditioning == "degenerate"``, so the state stays visible rather than
    being silently flattened to a large finite number.
    """

    if math.isfinite(value):
        return value
    return _JSON_SENTINEL_FOR_INFINITE_SENSITIVITY


def serialize_out_of_bounds_crossing(
    crossing: OutOfBoundsCrossing,
) -> OutOfBoundsCrossingResponse:
    return OutOfBoundsCrossingResponse(
        kind=crossing.kind,
        jd_ut=crossing.jd_ut,
        datetime_utc=datetime_from_jd(crossing.jd_ut).isoformat(),
        declination=crossing.declination,
        obliquity=crossing.obliquity,
        declination_rate_deg_per_day=crossing.declination_rate_deg_per_day,
        obliquity_rate_deg_per_day=crossing.obliquity_rate_deg_per_day,
        bound_rate_deg_per_day=crossing.bound_rate_deg_per_day,
        time_sensitivity_seconds_per_arcsec=_finite_sensitivity(
            crossing.time_sensitivity_seconds_per_arcsec
        ),
        achieved_tolerance_days=crossing.achieved_tolerance_days,
        bracket_start_jd_ut=crossing.bracket_start_jd_ut,
        bracket_end_jd_ut=crossing.bracket_end_jd_ut,
        conditioning=crossing.conditioning,
    )


def serialize_out_of_bounds_culmination(
    culmination: OutOfBoundsCulmination,
) -> OutOfBoundsCulminationResponse:
    return OutOfBoundsCulminationResponse(
        jd_ut=culmination.jd_ut,
        datetime_utc=datetime_from_jd(culmination.jd_ut).isoformat(),
        declination=culmination.declination,
        obliquity=culmination.obliquity,
        excess_deg=culmination.excess_deg,
        at_boundary=culmination.at_boundary,
        boundary_edge=culmination.boundary_edge,
        interior_critical_points=culmination.interior_critical_points,
    )


def serialize_out_of_bounds_excursion(
    excursion: OutOfBoundsExcursion,
) -> OutOfBoundsExcursionResponse:
    return OutOfBoundsExcursionResponse(
        body=excursion.body,
        hemisphere=excursion.hemisphere,
        jd_start_observed=excursion.jd_start_observed,
        jd_end_observed=excursion.jd_end_observed,
        datetime_start_utc=datetime_from_jd(excursion.jd_start_observed).isoformat(),
        datetime_end_utc=datetime_from_jd(excursion.jd_end_observed).isoformat(),
        entry=(
            serialize_out_of_bounds_crossing(excursion.entry)
            if excursion.entry is not None
            else None
        ),
        departure=(
            serialize_out_of_bounds_crossing(excursion.departure)
            if excursion.departure is not None
            else None
        ),
        entry_clipped=excursion.entry_clipped,
        departure_clipped=excursion.departure_clipped,
        culmination=serialize_out_of_bounds_culmination(excursion.culmination),
        duration_hours=excursion.duration_hours,
        duration_is_lower_bound=excursion.duration_is_lower_bound,
        is_complete=excursion.is_complete,
    )


def serialize_out_of_bounds_policy(
    policy: OutOfBoundsPolicy,
) -> OutOfBoundsPolicyResponse:
    return OutOfBoundsPolicyResponse(
        angular_resolution_deg=policy.angular_resolution_deg,
        rate_safety_factor=policy.rate_safety_factor,
        min_step_days=policy.min_step_days,
        max_step_days=policy.max_step_days,
        rate_probe_count=policy.rate_probe_count,
        solver_tolerance_days=policy.solver_tolerance_days,
        differentiation_step_days=policy.differentiation_step_days,
        max_subdivision_depth=policy.max_subdivision_depth,
        close_approach_distance_au=policy.close_approach_distance_au,
        distance_change_trigger=policy.distance_change_trigger,
        close_approach_refinement_depth=policy.close_approach_refinement_depth,
        culmination_probe_count=policy.culmination_probe_count,
        max_declination_evaluations=policy.max_declination_evaluations,
    )


def serialize_out_of_bounds_scan_truth(
    truth: OutOfBoundsScanTruth,
) -> OutOfBoundsScanTruthResponse:
    return OutOfBoundsScanTruthResponse(
        coarse_step_days=truth.coarse_step_days,
        measured_max_rate_deg_per_day=truth.measured_max_rate_deg_per_day,
        measured_median_rate_deg_per_day=truth.measured_median_rate_deg_per_day,
        rate_bound_deg_per_day=truth.rate_bound_deg_per_day,
        resolved_amplitude_floor_deg=truth.resolved_amplitude_floor_deg,
        coarse_node_count=truth.coarse_node_count,
        refined_interval_count=truth.refined_interval_count,
        unresolved_intervals=truth.unresolved_intervals,
        declination_evaluations=truth.declination_evaluations,
        policy=serialize_out_of_bounds_policy(truth.policy),
    )


def serialize_out_of_bounds_report(
    report: OutOfBoundsReport,
) -> OutOfBoundsSearchResponse:
    return OutOfBoundsSearchResponse(
        body=report.body,
        resolved_name=report.resolved_name,
        resolved_kind=report.resolved_kind,
        jd_start=report.jd_start,
        jd_end=report.jd_end,
        obliquity_at_start=report.obliquity_at_start,
        obliquity_at_end=report.obliquity_at_end,
        out_of_bounds_at_start=report.out_of_bounds_at_start,
        out_of_bounds_at_end=report.out_of_bounds_at_end,
        excursion_count=report.excursion_count,
        excursions=[
            serialize_out_of_bounds_excursion(excursion)
            for excursion in report.excursions
        ],
        scan_truth=serialize_out_of_bounds_scan_truth(report.scan_truth),
    )


__all__ = [
    "serialize_out_of_bounds_crossing",
    "serialize_out_of_bounds_culmination",
    "serialize_out_of_bounds_excursion",
    "serialize_out_of_bounds_policy",
    "serialize_out_of_bounds_report",
    "serialize_out_of_bounds_scan_truth",
]
