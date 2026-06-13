"""P13-01 bounded electional-window routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.electional import (
    ElectionalMomentsRequest,
    ElectionalMomentsResponse,
    ElectionalPredicateCatalogResponse,
    ElectionalScoredRequest,
    ElectionalScoredResponse,
    ElectionalScorerCatalogResponse,
    ElectionalWindowsRequest,
    ElectionalWindowsResponse,
)
from ..services.electional import (
    compute_electional_moments,
    compute_electional_scored,
    compute_electional_windows,
    electional_predicate_catalog,
    electional_scorer_catalog,
)


router = APIRouter(prefix="/v1/electional", tags=["electional"])


@router.get("/predicate-profiles", response_model=ElectionalPredicateCatalogResponse)
def electional_predicate_profiles_route() -> ElectionalPredicateCatalogResponse:
    """Return the admitted Stage 1 electional predicate catalogue."""
    return electional_predicate_catalog()


@router.get("/scorer-profiles", response_model=ElectionalScorerCatalogResponse)
def electional_scorer_profiles_route() -> ElectionalScorerCatalogResponse:
    """Return the admitted Stage 1 electional scorer catalogue."""
    return electional_scorer_catalog()


@router.post("/windows", response_model=ElectionalWindowsResponse)
def electional_windows_route(
    request: ElectionalWindowsRequest,
    engine: Annotated[Moira, Depends(get_engine)],
) -> ElectionalWindowsResponse:
    """Return bounded scan-derived electional windows for a server-defined predicate."""
    return compute_electional_windows(request, engine)


@router.post("/scored", response_model=ElectionalScoredResponse)
def electional_scored_route(
    request: ElectionalScoredRequest,
    engine: Annotated[Moira, Depends(get_engine)],
) -> ElectionalScoredResponse:
    """Return bounded scored electional windows for server-defined profiles."""
    return compute_electional_scored(request, engine)


@router.post("/moments", response_model=ElectionalMomentsResponse)
def electional_moments_route(
    request: ElectionalMomentsRequest,
    engine: Annotated[Moira, Depends(get_engine)],
) -> ElectionalMomentsResponse:
    """Return bounded raw electional scan points for a server-defined predicate."""
    return compute_electional_moments(request, engine)
