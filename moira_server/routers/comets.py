"""Fast comet surfaces (Phase 11 small-body)."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..dependencies import get_engine
from ..models.comets import (
    CometPositionRequest,
    CometPositionResponse,
    CometsBulkRequest,
    CometsBulkResponse,
)
from ..services.comets import (
    compute_comet_position,
    compute_comets_bulk,
    list_sovereign_comets,
)

router = APIRouter(prefix="/v1/comets", tags=["comets (fast small-body)"])


@router.post("/position", response_model=CometPositionResponse)
def comet_position(
    request: CometPositionRequest,
    engine=Depends(get_engine),
) -> CometPositionResponse:
    return compute_comet_position(engine, request)


@router.post("/bulk", response_model=CometsBulkResponse)
def comets_bulk(
    request: CometsBulkRequest,
    engine=Depends(get_engine),
) -> CometsBulkResponse:
    return compute_comets_bulk(engine, request)


@router.get("/list", response_model=list[str])
def list_comets(
    q: str | None = None,
    engine=Depends(get_engine),
) -> list[str]:
    """List / search comets in the loaded sovereign catalog (?q=halley)."""
    return list_sovereign_comets(engine, name_filter=q)
