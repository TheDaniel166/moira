"""Phase-9 Shadbala routes (P9-02)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.shadbala import (
    ShadbalaChartProfileResponse,
    ShadbalaChartRequest,
    ShadbalaConditionChartRequest,
    ShadbalaConditionProfileResponse,
    ShadbalaNetworkProfileResponse,
    ShadbalaResultResponse,
)
from ..serializers.shadbala import (
    serialize_shadbala_chart_profile,
    serialize_shadbala_condition_profile,
    serialize_shadbala_network_profile,
    serialize_shadbala_result,
)
from ..services.shadbala import (
    compute_shadbala_chart,
    compute_shadbala_chart_condition,
    compute_shadbala_chart_network,
    compute_shadbala_chart_profile,
)


router = APIRouter(prefix="/v1/shadbala", tags=["shadbala"])


@router.post("/chart", response_model=ShadbalaResultResponse)
def shadbala_chart_route(
    request: ShadbalaChartRequest,
    engine: Moira = Depends(get_engine),
) -> ShadbalaResultResponse:
    return serialize_shadbala_result(compute_shadbala_chart(engine, request))


@router.post("/chart/profile", response_model=ShadbalaChartProfileResponse)
def shadbala_chart_profile_route(
    request: ShadbalaChartRequest,
    engine: Moira = Depends(get_engine),
) -> ShadbalaChartProfileResponse:
    return serialize_shadbala_chart_profile(compute_shadbala_chart_profile(engine, request))


@router.post("/chart/network", response_model=ShadbalaNetworkProfileResponse)
def shadbala_chart_network_route(
    request: ShadbalaChartRequest,
    engine: Moira = Depends(get_engine),
) -> ShadbalaNetworkProfileResponse:
    return serialize_shadbala_network_profile(compute_shadbala_chart_network(engine, request))


@router.post("/chart/condition", response_model=ShadbalaConditionProfileResponse)
def shadbala_chart_condition_route(
    request: ShadbalaConditionChartRequest,
    engine: Moira = Depends(get_engine),
) -> ShadbalaConditionProfileResponse:
    return serialize_shadbala_condition_profile(
        compute_shadbala_chart_condition(engine, request)
    )
