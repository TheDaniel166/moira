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
from ..serializers.shadbala import (
    serialize_bhava_bala_result,
    serialize_shadbala_chart_profile,
    serialize_shadbala_condition_profile,
    serialize_shadbala_full,
    serialize_shadbala_network_profile,
    serialize_shadbala_result,
)
from ..services.shadbala import (
    compute_bhava_bala_chart,
    compute_shadbala_chart,
    compute_shadbala_chart_condition,
    compute_shadbala_chart_network,
    compute_shadbala_chart_profile,
    compute_shadbala_full,
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


@router.post("/chart/bhava", response_model=BhavaBalaResultResponse)
def bhava_bala_chart_route(
    request: ShadbalaChartRequest,
    engine: Moira = Depends(get_engine),
) -> BhavaBalaResultResponse:
    """Bhava Bala (house strength, Raman Part II) for all twelve houses."""
    return serialize_bhava_bala_result(compute_bhava_bala_chart(engine, request))


@router.post("/chart/full", response_model=ShadbalaFullResponse)
def shadbala_full_route(
    request: ShadbalaChartRequest,
    engine: Moira = Depends(get_engine),
) -> ShadbalaFullResponse:
    """Chart + profile + network + bhava in one response, from one
    support-truth derivation, so all four surfaces agree exactly."""
    full = compute_shadbala_full(engine, request)
    return serialize_shadbala_full(full.result, full.profile, full.network, full.bhava)
