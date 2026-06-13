"""Arabic lunar mansion (Manazil) REST routes."""

from __future__ import annotations

from fastapi import APIRouter, Path

from ..models.manazil import (
    MansionBulkRequest,
    MansionBulkResponse,
    MansionCatalogResponse,
    MansionPositionEnvelopeResponse,
    MansionPositionRequest,
    MansionTraditionLookupResponse,
    MansionTraditionName,
)
from ..services.manazil import (
    compute_mansion_bulk,
    compute_mansion_position,
    lookup_mansion_tradition,
    manazil_catalog,
)


router = APIRouter(prefix="/v1/manazil", tags=["manazil"])


@router.get("/catalog", response_model=MansionCatalogResponse)
def manazil_catalog_route() -> MansionCatalogResponse:
    """Return the admitted 28 Arabic mansion catalog."""
    return manazil_catalog()


@router.post("/position", response_model=MansionPositionEnvelopeResponse)
def manazil_position_route(
    request: MansionPositionRequest,
) -> MansionPositionEnvelopeResponse:
    """Compute one direct longitude's Arabic mansion position."""
    return compute_mansion_position(request)


@router.post("/bulk", response_model=MansionBulkResponse)
def manazil_bulk_route(
    request: MansionBulkRequest,
) -> MansionBulkResponse:
    """Compute Arabic mansion positions for a bounded set of longitudes."""
    return compute_mansion_bulk(request)


@router.get(
    "/traditions/{tradition}/mansions/{mansion_index}",
    response_model=MansionTraditionLookupResponse,
)
def manazil_tradition_lookup_route(
    tradition: MansionTraditionName,
    mansion_index: int = Path(..., ge=1, le=28),
) -> MansionTraditionLookupResponse:
    """Lookup a mansion's textual attribution in an admitted tradition."""
    return lookup_mansion_tradition(mansion_index, tradition)
