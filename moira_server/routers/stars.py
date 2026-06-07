"""Fixed stars surfaces (Phase 11) — ready for website + Manus AI consumption.

Fast, sovereign catalog-backed endpoints for stars.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..dependencies import get_engine
from ..models.stars import (
    MultipleStarListResponse,
    MultipleStarStateRequest,
    MultipleStarStateResponse,
    MultipleStarSystemResponse,
    StarPositionRequest,
    StarPositionResponse,
    StarsBulkRequest,
    StarsBulkResponse,
    StarListResponse,
    VariableStarCatalogProfileRequest,
    VariableStarCatalogProfileResponse,
    VariableStarCatalogResponse,
    VariableStarPairRequest,
    VariableStarPairResponse,
    VariableStarRangeRequest,
    VariableStarRangeResponse,
    VariableStarStateRequest,
    VariableStarStateResponse,
)
from ..services.stars import (
    compute_star_position,
    compute_stars_bulk,
    compute_multiple_star_state,
    compute_variable_catalog_profile,
    compute_variable_pair,
    compute_variable_star_range,
    compute_variable_star_state,
    get_multiple_star_system,
    get_variable_star,
    list_multiple_star_catalog,
    list_or_search_stars,
    list_variable_star_catalog,
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


@router.get("/variable/list", response_model=StarListResponse)
def list_variable_stars_route(
    q: str | None = Query(None, description="Search term"),
    var_type: str | None = Query(None, description="GCVS variability type, e.g. EA, DCEP, M"),
    limit: int = Query(100, le=500),
) -> StarListResponse:
    """List variable stars from the variable-star catalog."""

    return list_variable_star_catalog(q=q, var_type=var_type, limit=limit)


@router.get("/variable/{name}", response_model=VariableStarCatalogResponse)
def variable_star_catalog_route(name: str) -> VariableStarCatalogResponse:
    """Return one variable-star catalog record."""

    return get_variable_star(name)


@router.post("/variable/state", response_model=VariableStarStateResponse)
def variable_star_state_route(request: VariableStarStateRequest) -> VariableStarStateResponse:
    """Return one variable star's instantaneous photometric condition."""

    return compute_variable_star_state(request)


@router.post("/variable/range", response_model=VariableStarRangeResponse)
def variable_star_range_route(request: VariableStarRangeRequest) -> VariableStarRangeResponse:
    """Return minima and maxima for one variable star over a bounded JD range."""

    return compute_variable_star_range(request)


@router.post("/variable/catalog-profile", response_model=VariableStarCatalogProfileResponse)
def variable_star_catalog_profile_route(
    request: VariableStarCatalogProfileRequest,
) -> VariableStarCatalogProfileResponse:
    """Return aggregate variable-star catalog condition at one moment."""

    return compute_variable_catalog_profile(request)


@router.post("/variable/pair", response_model=VariableStarPairResponse)
def variable_star_pair_route(request: VariableStarPairRequest) -> VariableStarPairResponse:
    """Return the structural condition relation between two variable stars."""

    return compute_variable_pair(request)


@router.get("/multiple/list", response_model=MultipleStarListResponse)
def list_multiple_stars_route(
    q: str | None = Query(None, description="Search term"),
    system_type: str | None = Query(None, description="System type: visual, wide, spectroscopic, optical"),
    limit: int = Query(100, le=500),
) -> MultipleStarListResponse:
    """List multiple-star systems from the local orbital catalog."""

    return list_multiple_star_catalog(q=q, system_type=system_type, limit=limit)


@router.get("/multiple/{name}", response_model=MultipleStarSystemResponse)
def multiple_star_catalog_route(name: str) -> MultipleStarSystemResponse:
    """Return one multiple-star system catalog record."""

    return get_multiple_star_system(name)


@router.post("/multiple/state", response_model=MultipleStarStateResponse)
def multiple_star_state_route(request: MultipleStarStateRequest) -> MultipleStarStateResponse:
    """Return separation, position angle, and telescope resolvability."""

    return compute_multiple_star_state(request)
