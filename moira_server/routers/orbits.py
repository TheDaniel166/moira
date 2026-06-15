"""Orbital element and heliocentric distance-extrema routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..dependencies import get_engine
from ..models.orbits import (
    DistanceExtremesEnvelopeResponse,
    DistanceExtremesRequest,
    OrbitalElementsEnvelopeResponse,
    OrbitalElementsRequest,
)
from ..services.orbits import compute_distance_extremes, compute_orbital_elements


router = APIRouter(prefix="/v1/orbits", tags=["orbits"])


@router.post("/elements", response_model=OrbitalElementsEnvelopeResponse)
def orbital_elements_route(
    request: OrbitalElementsRequest,
    engine=Depends(get_engine),
) -> OrbitalElementsEnvelopeResponse:
    """Compute heliocentric J2000 osculating Keplerian elements."""
    return compute_orbital_elements(engine, request)


@router.post("/distance-extremes", response_model=DistanceExtremesEnvelopeResponse)
def distance_extremes_route(
    request: DistanceExtremesRequest,
    engine=Depends(get_engine),
) -> DistanceExtremesEnvelopeResponse:
    """Compute next heliocentric perihelion and aphelion events."""
    return compute_distance_extremes(engine, request)
