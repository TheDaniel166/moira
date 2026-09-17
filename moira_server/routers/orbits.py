"""Orbital element, distance-extrema, and orbit-classification routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..dependencies import get_engine
from ..models.orbits import (
    DistanceExtremesEnvelopeResponse,
    DistanceExtremesRequest,
    OrbitalElementsEnvelopeResponse,
    OrbitalElementsRequest,
    OrbitClassBatchEnvelopeResponse,
    OrbitClassBatchRequest,
    OrbitClassEnvelopeResponse,
    OrbitClassRequest,
)
from ..services.orbits import (
    compute_distance_extremes,
    compute_orbit_class,
    compute_orbit_class_batch,
    compute_orbital_elements,
)


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


@router.post("/class", response_model=OrbitClassEnvelopeResponse)
def orbit_class_route(
    request: OrbitClassRequest,
    engine=Depends(get_engine),
) -> OrbitClassEnvelopeResponse:
    """Compute SBDB-style osculating asteroid orbit classification."""
    return compute_orbit_class(engine, request)


@router.post("/class/batch", response_model=OrbitClassBatchEnvelopeResponse)
def orbit_class_batch_route(
    request: OrbitClassBatchRequest,
    engine=Depends(get_engine),
) -> OrbitClassBatchEnvelopeResponse:
    """Compute batch SBDB-style osculating asteroid orbit classifications."""
    return compute_orbit_class_batch(engine, request)

