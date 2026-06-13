"""Planetary and small-body node routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..dependencies import get_engine
from ..models.nodes import (
    GeometricNodeRequest,
    MeanPlanetaryNodeRequest,
    MeanPlanetaryNodesBulkRequest,
    MeanPlanetaryNodesBulkResponse,
    NodeCatalogResponse,
    NodeResponse,
)
from ..services.nodes import (
    compute_geometric_node,
    compute_mean_planetary_node,
    compute_mean_planetary_nodes_bulk,
    list_node_catalog,
)


router = APIRouter(prefix="/v1/nodes", tags=["nodes"])


@router.get("/catalog", response_model=NodeCatalogResponse)
def node_catalog_route() -> NodeCatalogResponse:
    """Return the admitted node methods and their transport boundaries."""
    return list_node_catalog()


@router.post("/planetary/mean", response_model=NodeResponse)
def mean_planetary_node_route(request: MeanPlanetaryNodeRequest) -> NodeResponse:
    """Compute one kernel-free mean planetary orbital node and apsides record."""
    return compute_mean_planetary_node(request)


@router.post("/planetary/mean/bulk", response_model=MeanPlanetaryNodesBulkResponse)
def mean_planetary_nodes_bulk_route(
    request: MeanPlanetaryNodesBulkRequest,
) -> MeanPlanetaryNodesBulkResponse:
    """Compute bounded kernel-free mean planetary orbital nodes."""
    return compute_mean_planetary_nodes_bulk(request)


@router.post("/geometric", response_model=NodeResponse)
def geometric_node_route(
    request: GeometricNodeRequest,
    engine=Depends(get_engine),
) -> NodeResponse:
    """Compute one osculating heliocentric node from the active reader."""
    return compute_geometric_node(engine, request)
