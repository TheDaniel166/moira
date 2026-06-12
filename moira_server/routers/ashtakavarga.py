"""Phase-9 Ashtakavarga routes (P9-09)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine

from ..models.ashtakavarga import (
    AshtakavargaChartBaseRequest,
    AshtakavargaChartProfileBackedResponse,
    AshtakavargaChartProfileResponse,
    AshtakavargaChartResultResponse,
    AshtakavargaChartSignProfileRequest,
    AshtakavargaChartSignProfileResponse,
    AshtakavargaChartTransitStrengthRequest,
    AshtakavargaChartTransitStrengthResponse,
    AshtakavargaDirectRequest,
    AshtakavargaResultResponse,
    AshtakavargaSignProfileRequest,
    AshtakavargaTransitStrengthRequest,
    AshtakavargaTransitStrengthResponse,
    SignStrengthProfileResponse,
)
from ..serializers.ashtakavarga import (
    serialize_ashtakavarga_chart_profile_backed,
    serialize_ashtakavarga_chart_profile,
    serialize_ashtakavarga_chart_result_backed,
    serialize_ashtakavarga_chart_sign_profile,
    serialize_ashtakavarga_chart_transit_strength,
    serialize_ashtakavarga_result,
    serialize_ashtakavarga_transit_strength,
    serialize_sign_strength_profile,
)
from ..services.ashtakavarga import (
    compute_ashtakavarga_chart_profile_backed,
    compute_ashtakavarga_chart_profile,
    compute_ashtakavarga_chart_result,
    compute_ashtakavarga_chart_sign_profile,
    compute_ashtakavarga_chart_transit_strength,
    compute_ashtakavarga_result,
    compute_ashtakavarga_sign_profile,
    compute_ashtakavarga_transit_strength,
)


router = APIRouter(prefix="/v1/ashtakavarga", tags=["ashtakavarga"])


@router.post("/result", response_model=AshtakavargaResultResponse)
def ashtakavarga_result_route(
    request: AshtakavargaDirectRequest,
) -> AshtakavargaResultResponse:
    _, result = compute_ashtakavarga_result(request)
    return serialize_ashtakavarga_result(result)


@router.post("/profile", response_model=AshtakavargaChartProfileResponse)
def ashtakavarga_profile_route(
    request: AshtakavargaDirectRequest,
) -> AshtakavargaChartProfileResponse:
    result = compute_ashtakavarga_chart_profile(request)
    return serialize_ashtakavarga_chart_profile(
        result.profile,
        result=result.result,
    )


@router.post("/sign-profile", response_model=SignStrengthProfileResponse)
def ashtakavarga_sign_profile_route(
    request: AshtakavargaSignProfileRequest,
) -> SignStrengthProfileResponse:
    result = compute_ashtakavarga_sign_profile(request)
    return serialize_sign_strength_profile(
        result.profile,
        ayanamsa_system=result.ayanamsa_system,
    )


@router.post("/transit-strength", response_model=AshtakavargaTransitStrengthResponse)
def ashtakavarga_transit_strength_route(
    request: AshtakavargaTransitStrengthRequest,
) -> AshtakavargaTransitStrengthResponse:
    return serialize_ashtakavarga_transit_strength(
        compute_ashtakavarga_transit_strength(request)
    )


@router.post("/chart/result", response_model=AshtakavargaChartResultResponse)
def ashtakavarga_chart_result_route(
    request: AshtakavargaChartBaseRequest,
    engine: Moira = Depends(get_engine),
) -> AshtakavargaChartResultResponse:
    return serialize_ashtakavarga_chart_result_backed(
        compute_ashtakavarga_chart_result(engine, request)
    )


@router.post("/chart/profile", response_model=AshtakavargaChartProfileBackedResponse)
def ashtakavarga_chart_profile_route(
    request: AshtakavargaChartBaseRequest,
    engine: Moira = Depends(get_engine),
) -> AshtakavargaChartProfileBackedResponse:
    return serialize_ashtakavarga_chart_profile_backed(
        compute_ashtakavarga_chart_profile_backed(engine, request)
    )


@router.post("/chart/sign-profile", response_model=AshtakavargaChartSignProfileResponse)
def ashtakavarga_chart_sign_profile_route(
    request: AshtakavargaChartSignProfileRequest,
    engine: Moira = Depends(get_engine),
) -> AshtakavargaChartSignProfileResponse:
    return serialize_ashtakavarga_chart_sign_profile(
        compute_ashtakavarga_chart_sign_profile(engine, request)
    )


@router.post(
    "/chart/transit-strength",
    response_model=AshtakavargaChartTransitStrengthResponse,
)
def ashtakavarga_chart_transit_strength_route(
    request: AshtakavargaChartTransitStrengthRequest,
    engine: Moira = Depends(get_engine),
) -> AshtakavargaChartTransitStrengthResponse:
    return serialize_ashtakavarga_chart_transit_strength(
        compute_ashtakavarga_chart_transit_strength(engine, request)
    )
