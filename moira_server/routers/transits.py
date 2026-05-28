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
    NextIngressRequest,
    TransitSearchRequest,
    TransitSearchResponse,
)
from ..serializers.transits import (
    serialize_ingress_event,
    serialize_lunar_phase_event,
    serialize_transit_event,
)
from ..services.transits import (
    compute_ingresses,
    compute_lunar_phases,
    compute_next_ingress,
    compute_transits,
)


router = APIRouter(prefix="/v1", tags=["predictive"])


@router.post("/transits/search", response_model=TransitSearchResponse)
def transit_search_route(
    request: TransitSearchRequest,
    engine: Moira = Depends(get_engine),
) -> TransitSearchResponse:
    return TransitSearchResponse(
        events=[serialize_transit_event(event) for event in compute_transits(engine, request)]
    )


@router.post("/transits/ingresses", response_model=IngressSearchResponse)
def ingress_search_route(
    request: IngressSearchRequest,
    engine: Moira = Depends(get_engine),
) -> IngressSearchResponse:
    return IngressSearchResponse(
        events=[serialize_ingress_event(event) for event in compute_ingresses(engine, request)]
    )


@router.post("/transits/next-ingress", response_model=IngressEventResponse | None)
def next_ingress_route(
    request: NextIngressRequest,
    engine: Moira = Depends(get_engine),
) -> IngressEventResponse | None:
    event = compute_next_ingress(engine, request)
    return serialize_ingress_event(event) if event is not None else None


@router.post("/lunar-phases", response_model=LunarPhaseSearchResponse)
def lunar_phase_route(
    request: LunarPhaseSearchRequest,
    engine: Moira = Depends(get_engine),
) -> LunarPhaseSearchResponse:
    return LunarPhaseSearchResponse(
        events=[serialize_lunar_phase_event(event) for event in compute_lunar_phases(engine, request)]
    )

