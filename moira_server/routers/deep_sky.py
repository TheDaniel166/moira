"""HTTP routes for Moira's release-bound deep-sky coordinate anchors."""

from __future__ import annotations

from fastapi import APIRouter, Query

from moira.deep_sky import DeepSkyClass

from ..models.deep_sky import (
    DeepSkyBulkRequest,
    DeepSkyBulkResponse,
    DeepSkyListResponse,
    DeepSkyPositionRequest,
    DeepSkyPositionResponse,
)
from ..services.deep_sky import (
    compute_deep_sky_bulk,
    compute_deep_sky_position,
    list_deep_sky_catalog,
)


router = APIRouter(prefix="/v1/deep-sky", tags=["deep-sky"])


@router.get("/list", response_model=DeepSkyListResponse)
def deep_sky_list(
    q: str | None = Query(None, description="Search names, designations, aliases, or SIMBAD identity"),
    object_class: DeepSkyClass | None = Query(None, description="Restrict results to one released class"),
    limit: int = Query(100, ge=1, le=100),
) -> DeepSkyListResponse:
    """List or search the offline 60-object catalog."""

    return list_deep_sky_catalog(query=q, object_class=object_class, limit=limit)


@router.post("/position", response_model=DeepSkyPositionResponse)
def deep_sky_position(request: DeepSkyPositionRequest) -> DeepSkyPositionResponse:
    """Return one true-ecliptic-of-date catalog-anchor direction."""

    return compute_deep_sky_position(request)


@router.post("/bulk", response_model=DeepSkyBulkResponse)
def deep_sky_bulk(request: DeepSkyBulkRequest) -> DeepSkyBulkResponse:
    """Return a bounded set of deep-sky directions at one instant."""

    return compute_deep_sky_bulk(request)
