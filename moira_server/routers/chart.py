"""Phase-2 chart and houses routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.chart import ChartRequest, ChartResponse, HousesRequest, HousesResponse
from ..serializers.chart import serialize_chart, serialize_houses
from ..services.chart import compute_chart, compute_houses


router = APIRouter(prefix="/v1", tags=["chart"])


@router.post("/chart", response_model=ChartResponse)
def chart_route(
    request: ChartRequest,
    engine: Moira = Depends(get_engine),
) -> ChartResponse:
    """Serialize a canonical chart result for transport."""

    return serialize_chart(compute_chart(engine, request))


@router.post("/houses", response_model=HousesResponse)
def houses_route(
    request: HousesRequest,
    engine: Moira = Depends(get_engine),
) -> HousesResponse:
    """Serialize a canonical houses result for transport."""

    return serialize_houses(compute_houses(engine, request))
