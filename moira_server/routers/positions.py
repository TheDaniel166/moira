"""Phase-2 planetary and sky-position routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.positions import (
    PlanetPositionRequest,
    PlanetPositionReductionResponse,
    PlanetPositionWithComputationTruthResponse,
    SkyPositionRequest,
    SkyPositionReductionResponse,
    SkyPositionWithComputationTruthResponse,
)
from ..serializers.positions import (
    serialize_planet_with_computation_truth,
    serialize_planet_with_reduction,
    serialize_sky_position_with_computation_truth,
    serialize_sky_position_with_reduction,
)
from ..services.positions import (
    compute_planet_position_with_reduction,
    compute_sky_position_with_reduction,
)


router = APIRouter(prefix="/v1/positions", tags=["positions"])


@router.post("/planet", response_model=PlanetPositionWithComputationTruthResponse)
def planet_position_route(
    request: PlanetPositionRequest,
    engine: Moira = Depends(get_engine),
) -> PlanetPositionWithComputationTruthResponse:
    """Serialize a planetary result with additive computation truth."""

    planet, reduction = compute_planet_position_with_reduction(engine, request)
    return serialize_planet_with_computation_truth(planet, reduction)


@router.post("/planet/reduction", response_model=PlanetPositionReductionResponse)
def planet_position_reduction_route(
    request: PlanetPositionRequest,
    engine: Moira = Depends(get_engine),
) -> PlanetPositionReductionResponse:
    """Serialize a planetary position together with its reduction truth."""

    planet, reduction = compute_planet_position_with_reduction(engine, request)
    return serialize_planet_with_reduction(planet, reduction)


@router.post("/sky", response_model=SkyPositionWithComputationTruthResponse)
def sky_position_route(
    request: SkyPositionRequest,
    engine: Moira = Depends(get_engine),
) -> SkyPositionWithComputationTruthResponse:
    """Serialize a sky-position result with additive computation truth."""

    position, reduction = compute_sky_position_with_reduction(engine, request)
    return serialize_sky_position_with_computation_truth(position, reduction)


@router.post("/sky/reduction", response_model=SkyPositionReductionResponse)
def sky_position_reduction_route(
    request: SkyPositionRequest,
    engine: Moira = Depends(get_engine),
) -> SkyPositionReductionResponse:
    """Serialize a sky position together with its reduction truth."""

    position, reduction = compute_sky_position_with_reduction(engine, request)
    return serialize_sky_position_with_reduction(position, reduction)
