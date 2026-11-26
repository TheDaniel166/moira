"""Fast asteroid surfaces for websites (small-body Phase 11 integration).

These endpoints are designed to be high-performance when the server is started
with a sovereign small-body manifest (MOIRA_SERVER_SMALL_BODY_MANIFEST).
They automatically use the native Type 13 evaluator for speed.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from moira.orbits import OrbitClassCode
from moira.small_body_identity import SmallBodyFamily

from ..dependencies import get_engine
from ..models.asteroids import (
    ASTEROID_CLASS_PAGE_MAX_ITEMS,
    AsteroidClassPageResponse,
    AsteroidListResponse,
    AsteroidFamiliesInChartRequest,
    AsteroidFamiliesInChartResponse,
    AsteroidFamilyLookupResponse,
    AsteroidFamilyMembersResponse,
    AsteroidFamilyResonanceNetworkRequest,
    AsteroidFamilyResonanceNetworkResponse,
    AsteroidIdentityResponse,
    AsteroidPositionRequest,
    AsteroidPositionResponse,
    AsteroidSubsetListResponse,
    AsteroidSubsetPositionsRequest,
    AsteroidSubsetPositionsResponse,
    AsteroidSubsetSlug,
    AsteroidSubsetsResponse,
    AsteroidsBulkRequest,
    AsteroidsBulkResponse,
    SmallBodyIdentityAmbiguity,
    SmallBodyIdentityConflictResponse,
    SmallBodyIdentityResponse,
)
from ..services.asteroids import (
    compute_asteroid_family_resonance_network,
    compute_asteroid_position,
    compute_asteroid_subset_positions,
    compute_asteroids_bulk,
    group_asteroid_families_in_chart,
    list_asteroid_family_members,
    list_asteroid_subset,
    list_asteroid_subsets,
    list_published_asteroid_classes,
    list_sovereign_asteroids,
    lookup_asteroid_family,
    lookup_asteroid_identity,
    lookup_small_body,
)

router = APIRouter(prefix="/v1/asteroids", tags=["asteroids (fast small-body)"])
identity_router = APIRouter(prefix="/v1/small-bodies", tags=["small-body-identity"])


@identity_router.get(
    "/identity",
    response_model=SmallBodyIdentityResponse,
    responses={
        404: {"description": "The name is absent from the selected catalogs."},
        409: {"model": SmallBodyIdentityConflictResponse, "description": "Multiple catalog matches."},
    },
)
def small_body_identity_route(
    body: str = Query(..., min_length=1, max_length=128),
    family: SmallBodyFamily | None = None,
    engine=Depends(get_engine),
) -> SmallBodyIdentityResponse:
    """Resolve a name or family-qualified designation across the two catalogs."""

    identity = lookup_small_body(engine, body, family)
    if identity is None:
        raise HTTPException(status_code=404, detail="Small-body identity is absent from the catalog.")
    if isinstance(identity, SmallBodyIdentityAmbiguity):
        raise HTTPException(status_code=409, detail=identity.model_dump(mode="json"))
    return identity


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


@router.get(
    "/classes",
    response_model=AsteroidClassPageResponse,
    responses={503: {"description": "The bundled asteroid class registry is unavailable."}},
)
def asteroid_classes_route(
    class_code: OrbitClassCode | None = Query(None, description="Published JPL SBDB class code"),
    offset: int = Query(0, ge=0, description="Zero-based offset within the filtered catalog"),
    limit: int = Query(100, ge=1, le=ASTEROID_CLASS_PAGE_MAX_ITEMS),
    engine=Depends(get_engine),
) -> AsteroidClassPageResponse:
    """Page published asteroid orbit classes by ascending NAIF ID."""
    page = list_published_asteroid_classes(engine, class_code=class_code, offset=offset, limit=limit)
    if page is None:
        raise HTTPException(status_code=503, detail="The bundled asteroid class registry is unavailable.")
    return page


@router.get(
    "/identity",
    response_model=AsteroidIdentityResponse,
    responses={404: {"description": "Asteroid identity is absent from the catalog."}},
)
def asteroid_identity_route(
    body: str = Query(..., min_length=1, max_length=128, description="Exact name, designation, or NAIF ID"),
    engine=Depends(get_engine),
) -> AsteroidIdentityResponse:
    """Resolve a catalog identity and report whether a loaded kernel contains it."""

    identity = lookup_asteroid_identity(engine, body)
    if identity is None:
        raise HTTPException(status_code=404, detail="Asteroid identity is absent from the catalog.")
    return identity


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
    """Lookup display-primary and complete families for an MPC asteroid number."""
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
    """Group MPC asteroid numbers across all admitted family memberships."""
    return group_asteroid_families_in_chart(request)


@router.post(
    "/families/chart/resonance-network",
    response_model=AsteroidFamilyResonanceNetworkResponse,
)
def asteroid_family_resonance_network(
    request: AsteroidFamilyResonanceNetworkRequest,
    engine=Depends(get_engine),
) -> AsteroidFamilyResonanceNetworkResponse:
    """Build a chart-level family-resonance aspect network for supplied asteroids."""
    return compute_asteroid_family_resonance_network(engine, request)
