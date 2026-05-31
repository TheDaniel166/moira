"""Fast asteroid surfaces for websites (small-body Phase 11 integration).

These endpoints are designed to be high-performance when the server is started
with a sovereign small-body manifest (MOIRA_SERVER_SMALL_BODY_MANIFEST).
They automatically use the native Type 13 evaluator for speed.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..dependencies import get_engine
from ..models.asteroids import (
    AsteroidPositionRequest,
    AsteroidPositionResponse,
    AsteroidsBulkRequest,
    AsteroidsBulkResponse,
)
from ..services.asteroids import (
    compute_asteroid_position,
    compute_asteroids_bulk,
    list_sovereign_asteroids,
)

router = APIRouter(prefix="/v1/asteroids", tags=["asteroids (fast small-body)"])


@router.post("/position", response_model=AsteroidPositionResponse)
def asteroid_position(
    request: AsteroidPositionRequest,
    engine=Depends(get_engine),
) -> AsteroidPositionResponse:
    """Single asteroid geocentric ecliptic position.

    Uses the fast native Type 13 sovereign path when the server was started
    with a small body manifest.
    """
    return compute_asteroid_position(engine, request)


@router.post("/bulk", response_model=AsteroidsBulkResponse)
def asteroids_bulk(
    request: AsteroidsBulkRequest,
    engine=Depends(get_engine),
) -> AsteroidsBulkResponse:
    """Bulk asteroid positions at a single time — the fast path for websites.

    Ideal for rendering many asteroids on a chart or list.
    """
    return compute_asteroids_bulk(engine, request)


@router.get("/list", response_model=list[str])
def list_asteroids(
    q: str | None = None,  # name/NAIF contains filter for search
    engine=Depends(get_engine),
) -> list[str]:
    """List / search bodies in the loaded sovereign small-body catalog.

    Use ?q=ceres for filtering. Fast (no heavy computation).
    """
    return list_sovereign_asteroids(engine, name_filter=q)

