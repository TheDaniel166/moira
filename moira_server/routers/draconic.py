"""Draconic chart-frame routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..dependencies import get_engine
from ..models.draconic import (
    DraconicChartRequest,
    DraconicChartResponse,
    DraconicLongitudeRequest,
    DraconicLongitudeResponse,
    DraconicPositionsRequest,
)
from ..services.draconic import (
    compute_draconic_chart,
    compute_draconic_longitude,
    compute_draconic_positions,
)


router = APIRouter(prefix="/v1/draconic", tags=["draconic"])


@router.post("/longitude", response_model=DraconicLongitudeResponse)
def draconic_longitude_route(
    request: DraconicLongitudeRequest,
) -> DraconicLongitudeResponse:
    """Rotate one caller-supplied longitude into a node-anchored draconic frame."""
    return compute_draconic_longitude(request)


@router.post("/positions", response_model=DraconicChartResponse)
def draconic_positions_route(request: DraconicPositionsRequest) -> DraconicChartResponse:
    """Materialize a draconic chart from caller-supplied longitudes and anchor."""
    return compute_draconic_positions(request)


@router.post("/chart", response_model=DraconicChartResponse)
def draconic_chart_route(
    request: DraconicChartRequest,
    engine=Depends(get_engine),
) -> DraconicChartResponse:
    """Materialize a draconic chart from an engine-computed tropical chart."""
    return compute_draconic_chart(engine, request)
