"""Phase-2 chart and houses routes."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from moira import Moira

from ..cache import ChartLRUCache
from ..dependencies import get_engine
from ..models.chart import (
    ChartReductionResponse,
    ChartRequest,
    ChartResponse,
    HousesReductionResponse,
    HousesRequest,
    HousesResponse,
)
from ..serializers.chart import (
    serialize_chart,
    serialize_chart_with_reduction,
    serialize_houses,
    serialize_houses_with_reduction,
)
from ..services.chart import (
    compute_chart,
    compute_chart_with_reduction,
    compute_houses,
    compute_houses_with_reduction,
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
