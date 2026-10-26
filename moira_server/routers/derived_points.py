"""Named symbolic and geometric points, separate from physical body routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.derived_points import (
    BakerLongitudesRequest, BakerVulcanResponse, DerivedPointCatalogResponse,
    DerivedPointEpochRequest, MeanPriapusRequest, PriapusResponse,
    SecondFocusRequest, SecondFocusResponse,
)
from ..services.derived_points import (
    compute_baker_longitudes, compute_baker_vulcan, compute_mean_priapus,
    compute_osculating_priapus, compute_second_focus, list_derived_points,
)

router = APIRouter(prefix="/v1/derived-points", tags=["derived-points"])


@router.get("/catalog", response_model=DerivedPointCatalogResponse)
def catalog_route() -> DerivedPointCatalogResponse:
    """Discover four explicitly named models without opening an ephemeris."""
    return list_derived_points()


@router.post("/baker-vulcan/from-longitudes", response_model=BakerVulcanResponse)
def baker_longitudes_route(request: BakerLongitudesRequest) -> BakerVulcanResponse:
    """Apply the symbolic rule to supplied common-frame longitudes."""
    return compute_baker_longitudes(request)


@router.post("/baker-vulcan", response_model=BakerVulcanResponse)
def baker_route(
    request: DerivedPointEpochRequest, engine: Moira = Depends(get_engine),
) -> BakerVulcanResponse:
    """Compute Baker Vulcan from apparent geocentric Sun/Mercury inputs."""
    return compute_baker_vulcan(engine, request)


@router.post("/priapus/mean", response_model=PriapusResponse)
def mean_priapus_route(request: MeanPriapusRequest) -> PriapusResponse:
    """Compute mean lunar perigee without an ephemeris kernel."""
    return compute_mean_priapus(request)


@router.post("/priapus/osculating", response_model=PriapusResponse)
def osculating_priapus_route(
    request: DerivedPointEpochRequest, engine: Moira = Depends(get_engine),
) -> PriapusResponse:
    """Compute lunar perigee with the existing osculating-apogee truth."""
    return compute_osculating_priapus(engine, request)


@router.post("/second-focus", response_model=SecondFocusResponse)
def second_focus_route(
    request: SecondFocusRequest, engine: Moira = Depends(get_engine),
) -> SecondFocusResponse:
    """Derive central-focus-relative ellipse geometry in an explicit frame."""
    return compute_second_focus(engine, request)
