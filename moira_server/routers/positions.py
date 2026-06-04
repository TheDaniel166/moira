"""Phase-2 planetary and sky-position routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.positions import (
    PlanetPositionRequest,
    PlanetPositionResponse,
    PlanetPositionReductionResponse,
    SkyPositionRequest,
    SkyPositionResponse,
    SkyPositionReductionResponse,
)
from ..serializers.positions import (
    serialize_planet,
    serialize_planet_with_reduction,
    serialize_sky_position,
    serialize_sky_position_with_reduction,
)
from ..services.positions import (
    compute_planet_position,
    compute_planet_position_with_reduction,
    compute_sky_position,
    compute_sky_position_with_reduction,
)


router = APIRouter(prefix="/v1/positions", tags=["positions"])


@router.post("/planet", response_model=PlanetPositionResponse)
def planet_position_route(
    request: PlanetPositionRequest,
    engine: Moira = Depends(get_engine),
) -> PlanetPositionResponse:
    """Serialize a canonical planetary position result for transport."""

    return serialize_planet(compute_planet_position(engine, request))


@router.post("/planet/reduction", response_model=PlanetPositionReductionResponse)
def planet_position_reduction_route(
    request: PlanetPositionRequest,
    engine: Moira = Depends(get_engine),
) -> PlanetPositionReductionResponse:
    """Serialize a planetary position together with its reduction truth."""

    planet, reduction = compute_planet_position_with_reduction(engine, request)
    return serialize_planet_with_reduction(planet, reduction)


@router.post("/sky", response_model=SkyPositionResponse)
def sky_position_route(
    request: SkyPositionRequest,
    engine: Moira = Depends(get_engine),
) -> SkyPositionResponse:
    """Serialize a canonical sky-position result for transport."""

    return serialize_sky_position(compute_sky_position(engine, request))


@router.post("/sky/reduction", response_model=SkyPositionReductionResponse)
def sky_position_reduction_route(
    request: SkyPositionRequest,
    engine: Moira = Depends(get_engine),
) -> SkyPositionReductionResponse:
    """Serialize a sky position together with its reduction truth."""

    position, reduction = compute_sky_position_with_reduction(engine, request)
    return serialize_sky_position_with_reduction(position, reduction)
