"""Generic phenomena and solar-condition routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..dependencies import get_engine
from ..models.generic_phenomena import (
    OrbitalPhenomenaEventsEnvelopeResponse,
    OrbitalPhenomenaEventsRequest,
    PlanetPhenomenaEnvelopeResponse,
    PlanetPhenomenaRequest,
    ProximityEventsEnvelopeResponse,
    ProximityEventsRequest,
    SolarConditionEventsEnvelopeResponse,
    SolarConditionEventsRequest,
    SolarConditionInstantEnvelopeResponse,
    SolarConditionInstantRequest,
)
from ..services.generic_phenomena import (
    compute_orbital_phenomena_events,
    compute_planet_phenomena,
    compute_proximity_events,
    compute_solar_condition_events,
    compute_solar_condition_instant,
)


router = APIRouter(prefix="/v1", tags=["generic-phenomena"])


@router.post("/phenomena/planet", response_model=PlanetPhenomenaEnvelopeResponse)
def planet_phenomena_route(
    request: PlanetPhenomenaRequest,
    engine=Depends(get_engine),
) -> PlanetPhenomenaEnvelopeResponse:
    """Return one instant's physical/photometric phenomena snapshot."""
    return compute_planet_phenomena(engine, request)


@router.post(
    "/phenomena/orbital-events",
    response_model=OrbitalPhenomenaEventsEnvelopeResponse,
)
def orbital_phenomena_events_route(
    request: OrbitalPhenomenaEventsRequest,
    engine=Depends(get_engine),
) -> OrbitalPhenomenaEventsEnvelopeResponse:
    """Search bounded admitted elongation and apside events."""
    return compute_orbital_phenomena_events(engine, request)


@router.post("/phenomena/proximity", response_model=ProximityEventsEnvelopeResponse)
def proximity_events_route(
    request: ProximityEventsRequest,
    engine=Depends(get_engine),
) -> ProximityEventsEnvelopeResponse:
    """Search angular proximity threshold ingress and egress events."""
    return compute_proximity_events(engine, request)


@router.post(
    "/solar-condition/instant",
    response_model=SolarConditionInstantEnvelopeResponse,
)
def solar_condition_instant_route(
    request: SolarConditionInstantRequest,
    engine=Depends(get_engine),
) -> SolarConditionInstantEnvelopeResponse:
    """Return classical solar-condition truth at one instant."""
    return compute_solar_condition_instant(engine, request)


@router.post(
    "/solar-condition/events",
    response_model=SolarConditionEventsEnvelopeResponse,
)
def solar_condition_events_route(
    request: SolarConditionEventsRequest,
    engine=Depends(get_engine),
) -> SolarConditionEventsEnvelopeResponse:
    """Search classical solar-condition threshold crossings."""
    return compute_solar_condition_events(engine, request)
