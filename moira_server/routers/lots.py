"""Phase-9 Classical Lots routes (P9-05)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.lots import (
    LotChartConditionProfileResponse,
    LotConditionNetworkProfileResponse,
    LotConditionProfileResponse,
    LotsCatalogResponse,
    LotsChartRequest,
    LotsConditionChartRequest,
    LotsConditionsResponse,
    LotsDependenciesResponse,
    LotsResultResponse,
)
from ..serializers.lots import (
    serialize_lot_chart_condition_profile,
    serialize_lot_condition_network_profile,
    serialize_lot_condition_profile,
    serialize_lots_catalog,
    serialize_lots_conditions,
    serialize_lots_dependencies,
    serialize_lots_result,
)
from ..services.lots import (
    compute_lots_chart_evaluation,
    compute_lots_chart_condition,
    compute_lots_chart_conditions,
    compute_lots_chart_dependencies,
    compute_lots_chart_network,
    compute_lots_chart_profile,
    list_lot_catalog,
)


router = APIRouter(prefix="/v1/lots", tags=["lots"])


@router.get("/catalog", response_model=LotsCatalogResponse)
def lots_catalog_route() -> LotsCatalogResponse:
    return serialize_lots_catalog(list_lot_catalog())


@router.post("/chart", response_model=LotsResultResponse)
def lots_chart_route(
    request: LotsChartRequest,
    engine: Moira = Depends(get_engine),
) -> LotsResultResponse:
    return serialize_lots_result(
        compute_lots_chart_evaluation(engine, request)
    )


@router.post("/chart/dependencies", response_model=LotsDependenciesResponse)
def lots_chart_dependencies_route(
    request: LotsChartRequest,
    engine: Moira = Depends(get_engine),
) -> LotsDependenciesResponse:
    return serialize_lots_dependencies(
        compute_lots_chart_dependencies(engine, request)
    )


@router.post("/chart/conditions", response_model=LotsConditionsResponse)
def lots_chart_conditions_route(
    request: LotsChartRequest,
    engine: Moira = Depends(get_engine),
) -> LotsConditionsResponse:
    return serialize_lots_conditions(
        compute_lots_chart_conditions(engine, request)
    )


@router.post("/chart/condition", response_model=LotConditionProfileResponse)
def lots_chart_condition_route(
    request: LotsConditionChartRequest,
    engine: Moira = Depends(get_engine),
) -> LotConditionProfileResponse:
    return serialize_lot_condition_profile(
        compute_lots_chart_condition(engine, request)
    )


@router.post("/chart/profile", response_model=LotChartConditionProfileResponse)
def lots_chart_profile_route(
    request: LotsChartRequest,
    engine: Moira = Depends(get_engine),
) -> LotChartConditionProfileResponse:
    return serialize_lot_chart_condition_profile(
        compute_lots_chart_profile(engine, request)
    )


@router.post("/chart/network", response_model=LotConditionNetworkProfileResponse)
def lots_chart_network_route(
    request: LotsChartRequest,
    engine: Moira = Depends(get_engine),
) -> LotConditionNetworkProfileResponse:
    return serialize_lot_condition_network_profile(
        compute_lots_chart_network(engine, request)
    )
