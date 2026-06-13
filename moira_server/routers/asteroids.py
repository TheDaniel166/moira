"""Fast asteroid surfaces for websites (small-body Phase 11 integration).

These endpoints are designed to be high-performance when the server is started
with a sovereign small-body manifest (MOIRA_SERVER_SMALL_BODY_MANIFEST).
They automatically use the native Type 13 evaluator for speed.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query

from ..dependencies import get_engine
from ..models.asteroids import (
    AsteroidListResponse,
    AsteroidFamiliesInChartRequest,
    AsteroidFamiliesInChartResponse,
    AsteroidFamilyLookupResponse,
    AsteroidFamilyMembersResponse,
    AsteroidPositionRequest,
    AsteroidPositionResponse,
    AsteroidSubsetListResponse,
    AsteroidSubsetPositionsRequest,
    AsteroidSubsetPositionsResponse,
    AsteroidSubsetSlug,
    AsteroidSubsetsResponse,
    AsteroidsBulkRequest,
    AsteroidsBulkResponse,
)
from ..services.asteroids import (
    compute_asteroid_position,
    compute_asteroid_subset_positions,
    compute_asteroids_bulk,
    group_asteroid_families_in_chart,
    list_asteroid_family_members,
    list_asteroid_subset,
    list_asteroid_subsets,
    list_sovereign_asteroids,
    lookup_asteroid_family,
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


@router.get("/list", response_model=AsteroidListResponse)
def list_asteroids(
    q: str | None = Query(None, description="Name or NAIF contains filter for search"),
    limit: int = Query(500, ge=1, le=500),
    engine=Depends(get_engine),
) -> AsteroidListResponse:
    """List / search bodies in the loaded sovereign small-body catalog.

    Use ?q=ceres or ?q=2000001 for filtering. Fast (no heavy computation).
    """
    return list_sovereign_asteroids(engine, name_filter=q, limit=limit)


@router.get("/subsets", response_model=AsteroidSubsetsResponse)
def asteroid_subsets() -> AsteroidSubsetsResponse:
    """List admitted named asteroid subset registries."""
    return list_asteroid_subsets()


@router.get("/subsets/{subset}/list", response_model=AsteroidSubsetListResponse)
def asteroid_subset_list(
    subset: AsteroidSubsetSlug,
    q: str | None = Query(None, description="Name or NAIF contains filter for search"),
    limit: int = Query(500, ge=1, le=500),
    engine=Depends(get_engine),
) -> AsteroidSubsetListResponse:
    """List / search an admitted named asteroid subset."""
    return list_asteroid_subset(engine, subset, name_filter=q, limit=limit)


@router.post("/subsets/{subset}/positions", response_model=AsteroidSubsetPositionsResponse)
def asteroid_subset_positions(
    subset: AsteroidSubsetSlug,
    request: AsteroidSubsetPositionsRequest,
    engine=Depends(get_engine),
) -> AsteroidSubsetPositionsResponse:
    """Return positions for all or selected members of an admitted asteroid subset."""
    return compute_asteroid_subset_positions(engine, subset, request)


@router.get("/families/by-number/{number}", response_model=AsteroidFamilyLookupResponse)
def asteroid_family_by_number(
    number: int = Path(..., ge=1),
) -> AsteroidFamilyLookupResponse:
    """Lookup the Nesvorny dynamical family for an MPC asteroid number."""
    return lookup_asteroid_family(number)


@router.get("/families/{family_name}/members", response_model=AsteroidFamilyMembersResponse)
def asteroid_family_members(
    family_name: str = Path(..., min_length=1),
    offset: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=500),
) -> AsteroidFamilyMembersResponse:
    """Return bounded MPC-number membership for a Nesvorny asteroid family."""
    return list_asteroid_family_members(family_name, offset=offset, limit=limit)


@router.post("/families/chart", response_model=AsteroidFamiliesInChartResponse)
def asteroid_families_in_chart(
    request: AsteroidFamiliesInChartRequest,
) -> AsteroidFamiliesInChartResponse:
    """Group supplied MPC asteroid numbers by shared Nesvorny family."""
    return group_asteroid_families_in_chart(request)
