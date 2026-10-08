"""Phase-9 Shadbala routes (P9-02)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.shadbala import (
    BhavaBalaResultResponse,
    ShadbalaChartProfileResponse,
    ShadbalaChartRequest,
    ShadbalaConditionChartRequest,
    ShadbalaConditionProfileResponse,
    ShadbalaFullResponse,
    ShadbalaNetworkProfileResponse,
    ShadbalaResultResponse,
)
from ..services.shadbala import (
    build_shadbala_bhava_response,
    build_shadbala_chart_response,
    build_shadbala_condition_response,
    build_shadbala_network_response,
    build_shadbala_profile_response,
    build_shadbala_full_response,
)


router = APIRouter(prefix="/v1/shadbala", tags=["shadbala"])


@router.post("/chart", response_model=ShadbalaResultResponse)
def shadbala_chart_route(
    request: ShadbalaChartRequest,
    engine: Moira = Depends(get_engine),
) -> ShadbalaResultResponse:
    return build_shadbala_chart_response(engine, request)


@router.post("/chart/profile", response_model=ShadbalaChartProfileResponse)
def shadbala_chart_profile_route(
    request: ShadbalaChartRequest,
    engine: Moira = Depends(get_engine),
) -> ShadbalaChartProfileResponse:
    return build_shadbala_profile_response(engine, request)


@router.post("/chart/network", response_model=ShadbalaNetworkProfileResponse)
def shadbala_chart_network_route(
    request: ShadbalaChartRequest,
    engine: Moira = Depends(get_engine),
) -> ShadbalaNetworkProfileResponse:
    return build_shadbala_network_response(engine, request)


@router.post("/chart/condition", response_model=ShadbalaConditionProfileResponse)
def shadbala_chart_condition_route(
    request: ShadbalaConditionChartRequest,
    engine: Moira = Depends(get_engine),
) -> ShadbalaConditionProfileResponse:
    return build_shadbala_condition_response(engine, request)


@router.post("/chart/bhava", response_model=BhavaBalaResultResponse)
def bhava_bala_chart_route(
    request: ShadbalaChartRequest,
    engine: Moira = Depends(get_engine),
) -> BhavaBalaResultResponse:
    """Bhava Bala (house strength, Raman Part II) for all twelve houses."""
    return build_shadbala_bhava_response(engine, request)


@router.post("/chart/full", response_model=ShadbalaFullResponse)
def shadbala_full_route(
    request: ShadbalaChartRequest,
    engine: Moira = Depends(get_engine),
) -> ShadbalaFullResponse:
    """Chart + profile + network + bhava in one response, from one
    support-truth derivation, so all four surfaces agree exactly."""
    return build_shadbala_full_response(engine, request)
