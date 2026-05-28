"""Phase-2 planetary and sky-position routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.positions import (
    PlanetPositionRequest,
    PlanetPositionResponse,
    SkyPositionRequest,
    SkyPositionResponse,
)
from ..serializers.positions import serialize_planet, serialize_sky_position
from ..services.positions import compute_planet_position, compute_sky_position


router = APIRouter(prefix="/v1/positions", tags=["positions"])


@router.post("/planet", response_model=PlanetPositionResponse)
def planet_position_route(
    request: PlanetPositionRequest,
    engine: Moira = Depends(get_engine),
) -> PlanetPositionResponse:
    """Serialize a canonical planetary position result for transport."""

    return serialize_planet(compute_planet_position(engine, request))


@router.post("/sky", response_model=SkyPositionResponse)
def sky_position_route(
    request: SkyPositionRequest,
    engine: Moira = Depends(get_engine),
) -> SkyPositionResponse:
    """Serialize a canonical sky-position result for transport."""

    return serialize_sky_position(compute_sky_position(engine, request))
