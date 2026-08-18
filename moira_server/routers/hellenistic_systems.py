"""Hellenistic circumambulation, transmission, and office routes."""

from __future__ import annotations

from fastapi import APIRouter

from ..models.hellenistic_systems import (
    CircumambulationsRequest,
    CircumambulationsResponse,
    OfficesRequest,
    OfficesResponse,
    TransmissionsRequest,
    TransmissionsResponse,
)
from ..services.hellenistic_systems import (
    compute_circumambulations,
    compute_offices,
    compute_transmissions,
)


router = APIRouter(
    prefix="/v1/hellenistic",
    tags=["hellenistic-systems"],
)


@router.post("/circumambulations", response_model=CircumambulationsResponse)
def circumambulations_route(
    request: CircumambulationsRequest,
) -> CircumambulationsResponse:
    """Release a caller-named significator through Egyptian bounds."""
    return compute_circumambulations(request)


@router.post("/transmissions", response_model=TransmissionsResponse)
def transmissions_route(request: TransmissionsRequest) -> TransmissionsResponse:
    """Assemble a score-free from→to transmission graph."""
    return compute_transmissions(request)


@router.post("/offices", response_model=OfficesResponse)
def offices_route(request: OfficesRequest) -> OfficesResponse:
    """Preserve office candidates without selecting a predominator."""
    return compute_offices(request)


__all__ = ["router"]
