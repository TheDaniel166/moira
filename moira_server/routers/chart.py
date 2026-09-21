"""Phase-2 chart and houses routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from moira import Moira

from ..cache import ChartLRUCache
from ..dependencies import get_engine
from ..models.chart import (
    AnalyticalHouseDynamicsRequest,
    AnalyticalHouseDynamicsResponse,
    ChartReductionResponse,
    ChartRequest,
    ChartResponse,
    HouseDynamicsFromArmcRequest,
    HouseDynamicsRequest,
    HouseDynamicsResponse,
    HousesReductionResponse,
    HousesRequest,
    HousesResponse,
    PolarAdmissibilityRequest,
    PolarAdmissibilityResponse,
)
from ..serializers.chart import (
    serialize_analytical_house_dynamics,
    serialize_chart,
    serialize_chart_with_reduction,
    serialize_house_dynamics,
    serialize_houses,
    serialize_houses_with_reduction,
    serialize_polar_admissibility,
)
from ..services.chart import (
    UnsupportedPolarHouseSystemError,
    compute_analytical_house_dynamics,
    compute_chart,
    compute_chart_with_reduction,
    compute_house_dynamics,
    compute_house_dynamics_from_armc,
    compute_houses,
    compute_houses_with_reduction,
    compute_polar_admissibility,
)


router = APIRouter(prefix="/v1", tags=["chart"])


def _get_cache(request: Request) -> ChartLRUCache | None:
    """Return the per-process chart cache, or None if not initialised."""
    return getattr(request.app.state, "chart_cache", None)


@router.post("/chart", response_model=ChartResponse)
def chart_route(
    request: ChartRequest,
    http_request: Request,
    engine: Moira = Depends(get_engine),
) -> ChartResponse:
    """Serialize a canonical chart result for transport."""

    cache = _get_cache(http_request)
    if cache is not None:
        key = ChartLRUCache.make_chart_key(
            request.dt.isoformat(),
            request.bodies,
            request.include_nodes,
            request.observer_lat,
            request.observer_lon,
            request.observer_elev_m,
        )
        cached = cache.get(key + "|chart")
        if cached is not None:
            return cached
        result = serialize_chart(compute_chart(engine, request))
        cache.set(key + "|chart", result)
        return result

    return serialize_chart(compute_chart(engine, request))


@router.post("/chart/reduction", response_model=ChartReductionResponse)
def chart_reduction_route(
    request: ChartRequest,
    http_request: Request,
    engine: Moira = Depends(get_engine),
) -> ChartReductionResponse:
    """Serialize a chart together with its reduction truth."""

    cache = _get_cache(http_request)
    if cache is not None:
        key = ChartLRUCache.make_chart_key(
            request.dt.isoformat(),
            request.bodies,
            request.include_nodes,
            request.observer_lat,
            request.observer_lon,
            request.observer_elev_m,
        )
        cached = cache.get(key + "|reduction")
        if cached is not None:
            return cached
        chart, reduction = compute_chart_with_reduction(engine, request)
        result = serialize_chart_with_reduction(chart, reduction)
        cache.set(key + "|reduction", result)
        return result

    chart, reduction = compute_chart_with_reduction(engine, request)
    return serialize_chart_with_reduction(chart, reduction)


@router.post("/houses", response_model=HousesResponse)
def houses_route(
    request: HousesRequest,
    engine: Moira = Depends(get_engine),
) -> HousesResponse:
    """Serialize a canonical houses result for transport."""

    return serialize_houses(compute_houses(engine, request))


@router.post("/houses/reduction", response_model=HousesReductionResponse)
def houses_reduction_route(
    request: HousesRequest,
    engine: Moira = Depends(get_engine),
) -> HousesReductionResponse:
    """Serialize houses result together with the governing doctrine and computation path (reduction truth)."""
    houses, reduction = compute_houses_with_reduction(engine, request)
    return serialize_houses_with_reduction(houses, reduction)


@router.post("/houses/dynamics", response_model=HouseDynamicsResponse)
def house_dynamics_route(
    request: HouseDynamicsRequest,
    engine: Moira = Depends(get_engine),
) -> HouseDynamicsResponse:
    """Compute instantaneous house cusp and angle speeds."""
    dynamics = compute_house_dynamics(engine, request)
    return serialize_house_dynamics(dynamics)


@router.post("/houses/dynamics/armc", response_model=HouseDynamicsResponse)
def house_dynamics_from_armc_route(
    request: HouseDynamicsFromArmcRequest,
) -> HouseDynamicsResponse:
    """Compute ARMC-native house dynamics with obliquity held fixed."""

    return serialize_house_dynamics(compute_house_dynamics_from_armc(request))


@router.post(
    "/houses/dynamics/analytical",
    response_model=AnalyticalHouseDynamicsResponse,
)
def analytical_house_dynamics_route(
    request: AnalyticalHouseDynamicsRequest,
) -> AnalyticalHouseDynamicsResponse:
    """Compute exact analytical MC, ASC, and Vertex angle velocities."""

    return serialize_analytical_house_dynamics(
        compute_analytical_house_dynamics(request)
    )


@router.post("/houses/polar-admissibility", response_model=PolarAdmissibilityResponse)
def houses_polar_admissibility_route(
    request: PolarAdmissibilityRequest,
) -> PolarAdmissibilityResponse:
    """Scan and return the polar ARMC admissibility windows and quality metrics for a house system."""
    try:
        result = compute_polar_admissibility(request)
    except UnsupportedPolarHouseSystemError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_polar_admissibility(result)
