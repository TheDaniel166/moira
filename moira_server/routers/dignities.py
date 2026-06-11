"""Phase-9 Classical Dignities routes (P9-04)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.dignities import (
    ChartConditionProfileResponse,
    ConditionNetworkProfileResponse,
    DignitiesChartRequest,
    DignitiesConditionChartRequest,
    DignitiesConditionsResponse,
    DignitiesReceptionsResponse,
    DignitiesResultResponse,
    PlanetaryConditionProfileResponse,
)
from ..serializers.dignities import (
    serialize_chart_condition_profile,
    serialize_condition_network_profile,
    serialize_dignities_conditions,
    serialize_dignities_receptions,
    serialize_dignities_result,
    serialize_planetary_condition_profile,
)
from ..services.dignities import (
    compute_dignities_chart,
    compute_dignities_chart_condition,
    compute_dignities_chart_conditions,
    compute_dignities_chart_network,
    compute_dignities_chart_profile,
    compute_dignities_chart_receptions,
)


router = APIRouter(prefix="/v1/dignities", tags=["dignities"])


@router.post("/chart", response_model=DignitiesResultResponse)
def dignities_chart_route(
    request: DignitiesChartRequest,
    engine: Moira = Depends(get_engine),
) -> DignitiesResultResponse:
    return serialize_dignities_result(compute_dignities_chart(engine, request))


@router.post("/chart/receptions", response_model=DignitiesReceptionsResponse)
def dignities_chart_receptions_route(
    request: DignitiesChartRequest,
    engine: Moira = Depends(get_engine),
) -> DignitiesReceptionsResponse:
    return serialize_dignities_receptions(
        compute_dignities_chart_receptions(engine, request)
    )


@router.post("/chart/conditions", response_model=DignitiesConditionsResponse)
def dignities_chart_conditions_route(
    request: DignitiesChartRequest,
    engine: Moira = Depends(get_engine),
) -> DignitiesConditionsResponse:
    return serialize_dignities_conditions(
        compute_dignities_chart_conditions(engine, request)
    )


@router.post("/chart/condition", response_model=PlanetaryConditionProfileResponse)
def dignities_chart_condition_route(
    request: DignitiesConditionChartRequest,
    engine: Moira = Depends(get_engine),
) -> PlanetaryConditionProfileResponse:
    return serialize_planetary_condition_profile(
        compute_dignities_chart_condition(engine, request)
    )


@router.post("/chart/profile", response_model=ChartConditionProfileResponse)
def dignities_chart_profile_route(
    request: DignitiesChartRequest,
    engine: Moira = Depends(get_engine),
) -> ChartConditionProfileResponse:
    return serialize_chart_condition_profile(
        compute_dignities_chart_profile(engine, request)
    )


@router.post("/chart/network", response_model=ConditionNetworkProfileResponse)
def dignities_chart_network_route(
    request: DignitiesChartRequest,
    engine: Moira = Depends(get_engine),
) -> ConditionNetworkProfileResponse:
    return serialize_condition_network_profile(
        compute_dignities_chart_network(engine, request)
    )
