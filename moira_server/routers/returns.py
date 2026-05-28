"""Phase-3 return routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Body, Moira

from ..dependencies import get_engine
from ..models.returns import (
    LunarReturnRequest,
    PlanetReturnRequest,
    ReturnEventResponse,
    SolarReturnRequest,
)
from ..serializers.returns import serialize_return_event
from ..services.returns import compute_lunar_return, compute_planet_return, compute_solar_return


router = APIRouter(prefix="/v1/returns", tags=["predictive"])


@router.post("/solar", response_model=ReturnEventResponse)
def solar_return_route(
    request: SolarReturnRequest,
    engine: Moira = Depends(get_engine),
) -> ReturnEventResponse:
    return serialize_return_event(
        return_type="solar_return",
        body=Body.SUN,
        jd_ut=compute_solar_return(engine, request),
    )


@router.post("/lunar", response_model=ReturnEventResponse)
def lunar_return_route(
    request: LunarReturnRequest,
    engine: Moira = Depends(get_engine),
) -> ReturnEventResponse:
    return serialize_return_event(
        return_type="lunar_return",
        body=Body.MOON,
        jd_ut=compute_lunar_return(engine, request),
    )


@router.post("/planet", response_model=ReturnEventResponse)
def planet_return_route(
    request: PlanetReturnRequest,
    engine: Moira = Depends(get_engine),
) -> ReturnEventResponse:
    return serialize_return_event(
        return_type="planet_return",
        body=request.body,
        jd_ut=compute_planet_return(engine, request),
    )

