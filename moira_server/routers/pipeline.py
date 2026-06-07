"""Website-facing reduction-pipeline routes.

The routes in this module are explicit transport aliases over existing
reduction-truth services. They expose visible computation stages for the
website without moving astronomical reduction logic into HTTP handlers.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.chart import ChartReductionResponse, ChartRequest
from ..models.positions import (
    PlanetPositionReductionResponse,
    PlanetPositionRequest,
    SkyPositionReductionResponse,
    SkyPositionRequest,
)
from ..serializers.chart import serialize_chart_with_reduction
from ..serializers.positions import serialize_planet_with_reduction, serialize_sky_position_with_reduction
from ..services.chart import compute_chart_with_reduction
from ..services.positions import compute_planet_position_with_reduction, compute_sky_position_with_reduction


router = APIRouter(prefix="/v1/pipeline", tags=["website-pipeline"])


@router.post("/chart", response_model=ChartReductionResponse)
def pipeline_chart_route(
    request: ChartRequest,
    engine: Moira = Depends(get_engine),
) -> ChartReductionResponse:
    """Expose chart assembly and reduction truth for website inspection."""

    chart, reduction = compute_chart_with_reduction(engine, request)
    return serialize_chart_with_reduction(chart, reduction)


@router.post("/positions/planet", response_model=PlanetPositionReductionResponse)
def pipeline_planet_position_route(
    request: PlanetPositionRequest,
    engine: Moira = Depends(get_engine),
) -> PlanetPositionReductionResponse:
    """Expose planet-position reduction truth for website inspection."""

    planet, reduction = compute_planet_position_with_reduction(engine, request)
    return serialize_planet_with_reduction(planet, reduction)


@router.post("/positions/sky", response_model=SkyPositionReductionResponse)
def pipeline_sky_position_route(
    request: SkyPositionRequest,
    engine: Moira = Depends(get_engine),
) -> SkyPositionReductionResponse:
    """Expose sky-position reduction truth for website inspection."""

    position, reduction = compute_sky_position_with_reduction(engine, request)
    return serialize_sky_position_with_reduction(position, reduction)


__all__ = ["router"]
