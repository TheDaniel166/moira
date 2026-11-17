"""Serialize bounded eclipse evidence without civil-time conversion."""
from __future__ import annotations

from dataclasses import asdict

from ..models.eclipse_diagnostics import (
    ClippedCentralBoundaryResponse,
    HybridDiagnosticResponse,
    LunarShadowCandidateResponse,
    SolarVisibilityRefinementResponse,
    SolarVisibilitySiteResponse,
    SweptCentralInteriorResponse,
)


def serialize_hybrid_diagnostic(value):
    event, result, ephemeris = value

    def witness(point):
        if point is None:
            return None
        data = asdict(point)
        data["jd_ut1"] = data.pop("jd_ut")
        return data

    transitions = [
        {
            "start_jd_ut1": t.start_jd_ut,
            "end_jd_ut1": t.end_jd_ut,
            "direction": t.direction,
            "width_seconds": t.width_seconds,
        }
        for t in result.transitions
    ]
    return HybridDiagnosticResponse(
        status=result.status, subtype=result.subtype, reason=result.reason,
        event_jd_ut1=event.jd_ut, instantaneous_type=str(event.data.eclipse_type),
        ephemeris_at_epoch=ephemeris, ephemeris_reference_jd_ut1=event.jd_ut,
        axis_interval_ut1=result.axis_interval, annular_witness=witness(result.annular_witness),
        total_witness=witness(result.total_witness), transitions=transitions,
        evaluation_count=result.evaluation_count, budget_exhausted=result.budget_exhausted,
    )


def serialize_lunar_shadow_candidate(value):
    candidate, reference_jd, ephemeris = value
    event = asdict(candidate.event) if candidate.event is not None else None
    if event is not None:
        for name in ("greatest", "axis_distance_minimum", "angular_opposition_minimum", "umbral_maximum", "total_maximum"):
            event[name + "_jd_ut1"] = event.pop(name + "_jd_ut")
        contacts = event["contacts"]
        event["contacts"] = {name + "_jd_ut1": value for name, value in contacts.items()}
    return LunarShadowCandidateResponse(
        status=candidate.status, event=event, reason=candidate.reason,
        complete=candidate.complete, ephemeris_at_epoch=ephemeris,
        ephemeris_reference_jd_ut1=reference_jd,
        vector_policy="Earth-reception retarded Sun; simultaneous geocentric Moon; no annual aberration",
        maximum_policy="maximum penumbral overlap, not NASA greatest eclipse",
    )


def serialize_solar_visibility_site(value):
    return SolarVisibilitySiteResponse.model_validate(asdict(value))


def serialize_solar_visibility_refinement(value):
    return SolarVisibilityRefinementResponse.model_validate(asdict(value))


def serialize_clipped_central_boundary(value):
    data = asdict(value)
    boundary = data["boundary"]
    if boundary is not None:
        boundary["jd_ut1"] = boundary.pop("jd_ut")
        boundary["cone_arc"] = list(boundary["cone_arc"])
        boundary["horizon_arc"] = list(boundary["horizon_arc"])
    return ClippedCentralBoundaryResponse.model_validate(data)


def serialize_swept_central_interior(value):
    data = asdict(value)
    data["samples"] = list(data["samples"])
    return SweptCentralInteriorResponse.model_validate(data)
