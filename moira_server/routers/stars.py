"""Fixed stars surfaces (Phase 11) — ready for website + Manus AI consumption.

Fast, sovereign catalog-backed endpoints for stars.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..dependencies import get_engine
from ..models.stars import (
    StarPositionRequest,
    StarPositionResponse,
    StarsBulkRequest,
    StarsBulkResponse,
    StarListResponse,
)
from ..services.stars import (
    compute_star_position,
    compute_stars_bulk,
    list_or_search_stars,
)

router = APIRouter(prefix="/v1/stars", tags=["stars (fixed stars)"])


@router.post("/position", response_model=StarPositionResponse)
def star_position(
    request: StarPositionRequest,
    engine=Depends(get_engine),
) -> StarPositionResponse:
    """Single fixed star position (sovereign catalog, fast)."""
    return compute_star_position(engine, request)


@router.post("/bulk", response_model=StarsBulkResponse)
def stars_bulk(
    request: StarsBulkRequest,
    engine=Depends(get_engine),
) -> StarsBulkResponse:
    """Bulk star positions — perfect for rendering full constellations on your site."""
    return compute_stars_bulk(engine, request)


@router.get("/list", response_model=StarListResponse)
def list_stars(
    q: str | None = Query(None, description="Search term (name, Bayer, etc.)"),
    limit: int = Query(100, le=500),
    engine=Depends(get_engine),
) -> StarListResponse:
    """Search or list stars from the sovereign catalog. Very fast."""
    return list_or_search_stars(engine, q=q, limit=limit)
