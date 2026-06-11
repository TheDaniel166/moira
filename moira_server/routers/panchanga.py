"""Phase-9 Panchanga routes (P9-01)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.panchanga import (
    PanchangaChartRequest,
    PanchangaDirectRequest,
    PanchangaProfileResponse,
    PanchangaResultResponse,
)
from ..serializers.panchanga import (
    serialize_panchanga_profile,
    serialize_panchanga_result,
)
from ..services.panchanga import (
    compute_panchanga_chart,
    compute_panchanga_chart_profile,
    compute_panchanga_direct,
    compute_panchanga_direct_profile,
)


router = APIRouter(prefix="/v1/panchanga", tags=["panchanga"])


@router.post("/instant", response_model=PanchangaResultResponse)
def panchanga_instant_route(request: PanchangaDirectRequest) -> PanchangaResultResponse:
    return serialize_panchanga_result(compute_panchanga_direct(request))


@router.post("/instant/profile", response_model=PanchangaProfileResponse)
def panchanga_instant_profile_route(
    request: PanchangaDirectRequest,
) -> PanchangaProfileResponse:
    return serialize_panchanga_profile(compute_panchanga_direct_profile(request))


@router.post("/chart", response_model=PanchangaResultResponse)
def panchanga_chart_route(
    request: PanchangaChartRequest,
    engine: Moira = Depends(get_engine),
) -> PanchangaResultResponse:
    return serialize_panchanga_result(compute_panchanga_chart(engine, request))


@router.post("/chart/profile", response_model=PanchangaProfileResponse)
def panchanga_chart_profile_route(
    request: PanchangaChartRequest,
    engine: Moira = Depends(get_engine),
) -> PanchangaProfileResponse:
    return serialize_panchanga_profile(compute_panchanga_chart_profile(engine, request))
