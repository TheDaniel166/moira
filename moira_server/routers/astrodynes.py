"""Church of Light natal Astrodynes REST routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.astrodynes import (
    AstrodynesCalculationResponse,
    AstrodynesChartRequest,
    AstrodynesDoctrineResponse,
    AstrodynesGeometryRequest,
)
from ..serializers.astrodynes import (
    serialize_astrodynes_calculation,
    serialize_astrodynes_doctrine,
)
from ..services.astrodynes import (
    compute_astrodynes_chart,
    compute_astrodynes_geometry,
    get_astrodynes_doctrine,
)


router = APIRouter(prefix="/v1/astrodynes", tags=["astrodynes"])


@router.get("/doctrine", response_model=AstrodynesDoctrineResponse)
def astrodynes_doctrine_route() -> AstrodynesDoctrineResponse:
    """Expose the fixed tables and policy governing every Astrodyne result."""

    return serialize_astrodynes_doctrine(get_astrodynes_doctrine())


@router.post("/geometry", response_model=AstrodynesCalculationResponse)
def astrodynes_geometry_route(
    request: AstrodynesGeometryRequest,
) -> AstrodynesCalculationResponse:
    """Compute from a complete caller-supplied tropical geometry, kernel-free."""

    return serialize_astrodynes_calculation(compute_astrodynes_geometry(request))


@router.post("/chart", response_model=AstrodynesCalculationResponse)
def astrodynes_chart_route(
    request: AstrodynesChartRequest,
    engine: Moira = Depends(get_engine),
) -> AstrodynesCalculationResponse:
    """Compute from geocentric apparent positions and an explicit house figure."""

    return serialize_astrodynes_calculation(
        compute_astrodynes_chart(engine, request)
    )


__all__ = ["router"]
