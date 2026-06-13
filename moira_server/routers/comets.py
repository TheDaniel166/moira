"""Fast comet surfaces (Phase 11 small-body)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..dependencies import get_engine
from ..models.comets import (
    CometListResponse,
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


@router.get("/list", response_model=CometListResponse)
def list_comets(
    q: str | None = Query(None, description="Name or NAIF contains filter for search"),
    limit: int = Query(500, ge=1, le=500),
    engine=Depends(get_engine),
) -> CometListResponse:
    """List / search comets in the loaded sovereign catalog (?q=halley or ?q=1000001)."""
    return list_sovereign_comets(engine, name_filter=q, limit=limit)
