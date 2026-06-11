"""Phase-9 Vedic Dignities routes (P9-08)."""

from __future__ import annotations

from fastapi import APIRouter

from ..models.vedic_dignities import (
    VedicChartDignityProfileResponse,
    VedicDignityChartRequest,
    VedicDignityConditionResponse,
    VedicDignityRelationshipsResponse,
    VedicDignityRequest,
    VedicDignityResultResponse,
)
from ..serializers.vedic_dignities import (
    serialize_vedic_chart_dignity_profile,
    serialize_vedic_dignity_condition,
    serialize_vedic_dignity_relationships,
    serialize_vedic_dignity_result,
)
from ..services.vedic_dignities import (
    compute_vedic_chart_dignity_profile,
    compute_vedic_dignity,
    compute_vedic_dignity_condition,
    compute_vedic_dignity_relationships,
)


router = APIRouter(prefix="/v1/vedic-dignities", tags=["vedic-dignities"])


@router.post("/dignity", response_model=VedicDignityResultResponse)
def vedic_dignity_route(
    request: VedicDignityRequest,
) -> VedicDignityResultResponse:
    policy, result = compute_vedic_dignity(request)
    return serialize_vedic_dignity_result(
        result,
        ayanamsa_system=policy.ayanamsa_system,
    )


@router.post("/relationships", response_model=VedicDignityRelationshipsResponse)
def vedic_dignity_relationships_route(
    request: VedicDignityChartRequest,
) -> VedicDignityRelationshipsResponse:
    policy, relationships = compute_vedic_dignity_relationships(request)
    return serialize_vedic_dignity_relationships(
        relationships,
        ayanamsa_system=policy.ayanamsa_system,
    )


@router.post("/condition", response_model=VedicDignityConditionResponse)
def vedic_dignity_condition_route(
    request: VedicDignityRequest,
) -> VedicDignityConditionResponse:
    result = compute_vedic_dignity_condition(request)
    return serialize_vedic_dignity_condition(
        result.profile,
        result=result.result,
        ayanamsa_system=result.ayanamsa_system,
    )


@router.post("/chart-profile", response_model=VedicChartDignityProfileResponse)
def vedic_dignity_chart_profile_route(
    request: VedicDignityChartRequest,
) -> VedicChartDignityProfileResponse:
    result = compute_vedic_chart_dignity_profile(request)
    return serialize_vedic_chart_dignity_profile(
        result.profile,
        results=result.results,
        ayanamsa_system=result.ayanamsa_system,
    )
