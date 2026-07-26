"""Phase-9 decans/decanates routes (P9-12)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine

from ..models.decans import (
    DecanateChartBodyRequest,
    DecanateChartPositionResponse,
    DecanateChartSetResponse,
    DecanateLongitudeRequest,
    DecanatePositionResponse,
    DecanateSetRequest,
    DecanateSetResponse,
    VedicDrekkanaRequest,
)
from ..serializers.decans import (
    serialize_decanate_chart_position,
    serialize_decanate_chart_set,
    serialize_decanate_position,
    serialize_decanate_set,
)
from ..services.decans import (
    compute_chaldean_face,
    compute_decanate_set,
    compute_decanate_set_chart,
    compute_triplicity_decan,
    compute_vedic_drekkana,
    compute_vedic_drekkana_chart,
)


decanates_router = APIRouter(prefix="/v1/decanates", tags=["decanates"])


@decanates_router.post("/chaldean-face", response_model=DecanatePositionResponse)
def chaldean_face_route(
    request: DecanateLongitudeRequest,
) -> DecanatePositionResponse:
    return serialize_decanate_position(compute_chaldean_face(request))


@decanates_router.post("/triplicity", response_model=DecanatePositionResponse)
def triplicity_decan_route(
    request: DecanateLongitudeRequest,
) -> DecanatePositionResponse:
    return serialize_decanate_position(compute_triplicity_decan(request))


@decanates_router.post("/vedic-drekkana", response_model=DecanatePositionResponse)
def vedic_drekkana_route(
    request: VedicDrekkanaRequest,
) -> DecanatePositionResponse:
    return serialize_decanate_position(compute_vedic_drekkana(request))


@decanates_router.post("/set", response_model=DecanateSetResponse)
def decanate_set_route(request: DecanateSetRequest) -> DecanateSetResponse:
    return serialize_decanate_set(compute_decanate_set(request))


@decanates_router.post(
    "/chart/vedic-drekkana",
    response_model=DecanateChartPositionResponse,
)
def vedic_drekkana_chart_route(
    request: DecanateChartBodyRequest,
    engine: Moira = Depends(get_engine),
) -> DecanateChartPositionResponse:
    return serialize_decanate_chart_position(
        compute_vedic_drekkana_chart(engine, request)
    )


@decanates_router.post("/chart/set", response_model=DecanateChartSetResponse)
def decanate_set_chart_route(
    request: DecanateChartBodyRequest,
    engine: Moira = Depends(get_engine),
) -> DecanateChartSetResponse:
    return serialize_decanate_chart_set(
        compute_decanate_set_chart(engine, request)
    )
