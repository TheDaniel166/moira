"""Phase-3 transit, ingress, and lunar-phase routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.transits import (
    IngressEventResponse,
    IngressSearchRequest,
    IngressSearchResponse,
    LunarPhaseSearchRequest,
    LunarPhaseSearchResponse,
    NatalAspectSearchRequest,
    NatalAspectSearchResponse,
    NextIngressRequest,
    TransitSearchRequest,
    TransitSearchResponse,
)
from ..serializers.batch import serialize_aspect_transit_event
from ..serializers.transits import (
    serialize_ingress_event,
    serialize_lunar_phase_event,
    serialize_transit_event,
)
from ..services.transits import (
    compute_ingresses,
    compute_lunar_phases,
    compute_natal_aspect_transits,
    compute_next_ingress,
    compute_transits,
)


router = APIRouter(prefix="/v1", tags=["predictive"])


@router.post("/transits/search", response_model=TransitSearchResponse)
def transit_search_route(
    request: TransitSearchRequest,
    engine: Moira = Depends(get_engine),
) -> TransitSearchResponse:
    events = [serialize_transit_event(event) for event in compute_transits(engine, request)]
    # Transport-layer echo of the caller's requested controls into the
    # computation_truth (per the B decision on the "requested vs applied" item).
    # This augments the engine-provided applied values without mutating engine vessels.
    for ev in events:
        if ev.computation_truth is not None:
            ev.computation_truth.requested_step_days = request.step_days
            ev.computation_truth.requested_tolerance_days = request.solver_tolerance_days
            ev.computation_truth.requested_direction = request.direction
    return TransitSearchResponse(events=events)


@router.post("/transits/natal-aspects", response_model=NatalAspectSearchResponse)
def natal_aspect_search_route(
    request: NatalAspectSearchRequest,
    engine: Moira = Depends(get_engine),
) -> NatalAspectSearchResponse:
    """Aspect hits of one moving body against frozen natal longitudes.

    The natal longitudes never move. One longitude series of the body is
    scanned for the whole window and every (longitude, angle) pair is refined
    from it, so a full natal grid costs one scan instead of one search per
    pair. Events are ordered by exact time and share the aspect_transit event
    shape used by /v1/batch/events.
    """
    return NatalAspectSearchResponse(
        events=[serialize_aspect_transit_event(event) for event in compute_natal_aspect_transits(engine, request)]
    )


@router.post("/transits/ingresses", response_model=IngressSearchResponse)
def ingress_search_route(
    request: IngressSearchRequest,
    engine: Moira = Depends(get_engine),
) -> IngressSearchResponse:
    events = [serialize_ingress_event(event) for event in compute_ingresses(engine, request)]
    for ev in events:
        if ev.computation_truth is not None:
            ev.computation_truth.requested_step_days = request.step_days
            ev.computation_truth.requested_tolerance_days = request.solver_tolerance_days
            ev.computation_truth.requested_direction = request.direction
    return IngressSearchResponse(events=events)


@router.post("/transits/next-ingress", response_model=IngressEventResponse | None)
def next_ingress_route(
    request: NextIngressRequest,
    engine: Moira = Depends(get_engine),
) -> IngressEventResponse | None:
    event = compute_next_ingress(engine, request)
    if event is None:
        return None
    ev = serialize_ingress_event(event)
    if ev.computation_truth is not None:
        ev.computation_truth.requested_step_days = request.step_days
        ev.computation_truth.requested_tolerance_days = request.solver_tolerance_days
        ev.computation_truth.requested_direction = request.direction
    return ev


@router.post("/lunar-phases", response_model=LunarPhaseSearchResponse)
def lunar_phase_route(
    request: LunarPhaseSearchRequest,
    engine: Moira = Depends(get_engine),
) -> LunarPhaseSearchResponse:
    return LunarPhaseSearchResponse(
        events=[serialize_lunar_phase_event(event) for event in compute_lunar_phases(engine, request)]
    )

