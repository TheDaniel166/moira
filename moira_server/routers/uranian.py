"""Uranian / Hamburg School hypothetical-body routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.uranian import (
    UranianBulkRequest,
    UranianBulkResponse,
    UranianCatalogResponse,
    UranianPositionRequest,
    UranianSingleResponse,
)
from ..services.uranian import (
    compute_uranian_bulk,
    compute_uranian_position,
    list_uranian_catalog,
)


router = APIRouter(prefix="/v1/uranian", tags=["uranian"])


@router.get("/catalog", response_model=UranianCatalogResponse)
def uranian_catalog_route() -> UranianCatalogResponse:
    """Return the admitted Uranian/Hamburg School hypothetical-body names."""
    return list_uranian_catalog()


@router.post("/position", response_model=UranianSingleResponse)
def uranian_position_route(
    request: UranianPositionRequest,
    engine: Moira = Depends(get_engine),
) -> UranianSingleResponse:
    """Compute one apparent geocentric hypothetical-body position."""
    return compute_uranian_position(engine, request)


@router.post("/bulk", response_model=UranianBulkResponse)
def uranian_bulk_route(
    request: UranianBulkRequest,
    engine: Moira = Depends(get_engine),
) -> UranianBulkResponse:
    """Compute bounded apparent geocentric hypothetical-body positions."""
    return compute_uranian_bulk(engine, request)
