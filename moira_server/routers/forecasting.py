"""Bounded predictive relationship and locational composition routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.forecasting import (
    CompositeTransitRequest,
    DavisonTransitRequest,
    DynamicAstrocartographyRequest,
    DynamicAstrocartographyResponse,
    FixedStarAstrocartographyRequest,
    FixedStarAstrocartographyResponse,
    RelocatedReturnRequest,
    RelocatedReturnResponse,
    RelationshipTransitSearchResponse,
)
from ..serializers.forecasting import (
    serialize_dynamic_astrocartography,
    serialize_fixed_star_astrocartography,
    serialize_relationship_transit_search,
    serialize_relocated_return,
)
from ..services.forecasting import (
    compute_composite_transits,
    compute_davison_transits,
    compute_dynamic_astrocartography,
    compute_fixed_star_astrocartography,
    compute_relocated_return,
)


router = APIRouter(prefix="/v1")


@router.post(
    "/composite/transits",
    response_model=RelationshipTransitSearchResponse,
    tags=["relationship"],
)
def composite_transits_route(
    request: CompositeTransitRequest,
    engine: Moira = Depends(get_engine),
) -> RelationshipTransitSearchResponse:
    """Find exact canonical transits to a static composite-chart target set."""

    return serialize_relationship_transit_search(
        compute_composite_transits(engine, request)
    )


@router.post(
    "/davison/transits",
    response_model=RelationshipTransitSearchResponse,
    tags=["relationship"],
)
def davison_transits_route(
    request: DavisonTransitRequest,
    engine: Moira = Depends(get_engine),
) -> RelationshipTransitSearchResponse:
    """Find exact canonical transits to a static Davison-chart target set."""

    return serialize_relationship_transit_search(
        compute_davison_transits(engine, request)
    )


@router.post(
    "/astrocartography/fixed-stars",
    response_model=FixedStarAstrocartographyResponse,
    tags=["astrocartography"],
)
def fixed_star_astrocartography_route(
    request: FixedStarAstrocartographyRequest,
) -> FixedStarAstrocartographyResponse:
    """Resolve star identity/provenance and compute equatorial ACG geometry."""

    return serialize_fixed_star_astrocartography(
        compute_fixed_star_astrocartography(request)
    )


@router.post(
    "/astrocartography/dynamic/transits",
    response_model=DynamicAstrocartographyResponse,
    tags=["astrocartography"],
)
def dynamic_astrocartography_route(
    request: DynamicAstrocartographyRequest,
    engine: Moira = Depends(get_engine),
) -> DynamicAstrocartographyResponse:
    """Compute geometry-only ACG snapshots at explicit transiting epochs."""

    return serialize_dynamic_astrocartography(
        compute_dynamic_astrocartography(engine, request)
    )


@router.post(
    "/returns/relocated",
    response_model=RelocatedReturnResponse,
    tags=["predictive", "astrocartography"],
)
def relocated_return_route(
    request: RelocatedReturnRequest,
    engine: Moira = Depends(get_engine),
) -> RelocatedReturnResponse:
    """Time one canonical return and recast its unchanged sky at two locations."""

    return serialize_relocated_return(compute_relocated_return(engine, request))


__all__ = ["router"]
