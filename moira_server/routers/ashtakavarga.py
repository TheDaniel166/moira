"""Phase-9 Ashtakavarga routes (P9-09)."""

from __future__ import annotations

from fastapi import APIRouter

from ..models.ashtakavarga import (
    AshtakavargaChartProfileResponse,
    AshtakavargaDirectRequest,
    AshtakavargaResultResponse,
    AshtakavargaSignProfileRequest,
    AshtakavargaTransitStrengthRequest,
    AshtakavargaTransitStrengthResponse,
    SignStrengthProfileResponse,
)
from ..serializers.ashtakavarga import (
    serialize_ashtakavarga_chart_profile,
    serialize_ashtakavarga_result,
    serialize_ashtakavarga_transit_strength,
    serialize_sign_strength_profile,
)
from ..services.ashtakavarga import (
    compute_ashtakavarga_chart_profile,
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
