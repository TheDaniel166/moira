"""Opt-in, explicitly qualified hypothetical constructions and historical orbits."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira
from moira.hypothetical import (
    ArtaFourPoints, ArtaOsculatingSet, HypotheticalGeometry, LongitudeConvention,
    hypothetical_catalog,
    PlanetNineScenario,
)
from ..dependencies import get_engine
from ..models.derived_points import DerivedPointCatalogResponse
from ..models.hypothetical import (
    ArtaInputsRequest, ArtaOsculatingRequest, HypotheticalOrbitRequest,
    ProserpinaRequest, SelenaRequest,
    PlanetNineScenarioRequest,
)
from ..services.hypothetical import (
    compute_arta_inputs, compute_arta_osculating, compute_hypothetical_orbit,
    compute_proserpina, compute_selena,
    compute_planet_nine_scenario,
)

router = APIRouter(prefix="/v1/hypothetical", tags=["hypothetical"])


@router.get("/catalog", response_model=DerivedPointCatalogResponse)
def catalog_route() -> DerivedPointCatalogResponse:
    """List model-qualified constructions and the required realization choices."""
    points = hypothetical_catalog()
    return DerivedPointCatalogResponse(points=list(points), count=len(points))


@router.post("/arta/from-longitudes", response_model=ArtaFourPoints)
def arta_inputs_route(request: ArtaInputsRequest) -> ArtaFourPoints:
    """Return all four equivalent points for named supplied inputs."""
    return compute_arta_inputs(request)


@router.post("/arta/osculating", response_model=ArtaOsculatingSet)
def arta_osculating_route(
    request: ArtaOsculatingRequest, engine: Moira = Depends(get_engine),
) -> ArtaOsculatingSet:
    """Use strict geometric Moon/Earth inputs, retaining both complete receipts."""
    return compute_arta_osculating(engine, request)


@router.post("/selena", response_model=LongitudeConvention)
def selena_route(request: SelenaRequest) -> LongitudeConvention:
    """Apply seven-year motion to an explicitly selected anchor and year rule."""
    return compute_selena(request)


@router.post("/proserpina", response_model=LongitudeConvention)
def proserpina_route(request: ProserpinaRequest) -> LongitudeConvention:
    """Evaluate a selected realization of Abramov's rounded approximation."""
    return compute_proserpina(request)


@router.post("/planet-nine-scenario", response_model=PlanetNineScenario)
def planet_nine_scenario_route(request: PlanetNineScenarioRequest) -> PlanetNineScenario:
    """Evaluate a selected trial position, without a canonical epoch or phase."""
    return compute_planet_nine_scenario(request)


@router.post("/orbit", response_model=HypotheticalGeometry)
def orbit_route(request: HypotheticalOrbitRequest) -> HypotheticalGeometry:
    """Evaluate a named prescribed ellipse with all required reconstruction choices."""
    return compute_hypothetical_orbit(request)
