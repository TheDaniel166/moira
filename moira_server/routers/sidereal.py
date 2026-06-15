"""Sidereal and Nakshatra utility routes."""

from __future__ import annotations

from fastapi import APIRouter

from ..models.sidereal import (
    AyanamsaSystemsEnvelopeResponse,
    SiderealAyanamsaRequest,
    SiderealAyanamsaResponse,
    SiderealConversionRequest,
    SiderealConversionResponse,
    SiderealNakshatraBulkEnvelopeResponse,
    SiderealNakshatraBulkRequest,
    SiderealNakshatraPositionEnvelopeResponse,
    SiderealNakshatraPositionRequest,
)
from ..services.sidereal import (
    compute_nakshatra_bulk,
    compute_nakshatra_position,
    compute_sidereal_ayanamsa,
    convert_sidereal_longitude,
    list_sidereal_ayanamsa_systems,
)


router = APIRouter(prefix="/v1", tags=["sidereal"])


@router.get("/sidereal/ayanamsa-systems", response_model=AyanamsaSystemsEnvelopeResponse)
def sidereal_ayanamsa_systems_route() -> AyanamsaSystemsEnvelopeResponse:
    """Return the admitted built-in ayanamsa registry."""
    return list_sidereal_ayanamsa_systems()


@router.post("/sidereal/ayanamsa", response_model=SiderealAyanamsaResponse)
def sidereal_ayanamsa_route(
    request: SiderealAyanamsaRequest,
) -> SiderealAyanamsaResponse:
    """Compute one date-specific ayanamsa value."""
    return compute_sidereal_ayanamsa(request)


@router.post("/sidereal/convert", response_model=SiderealConversionResponse)
def sidereal_convert_route(
    request: SiderealConversionRequest,
) -> SiderealConversionResponse:
    """Convert one longitude between tropical and sidereal frames."""
    return convert_sidereal_longitude(request)


@router.post(
    "/nakshatra/position",
    response_model=SiderealNakshatraPositionEnvelopeResponse,
)
def nakshatra_position_route(
    request: SiderealNakshatraPositionRequest,
) -> SiderealNakshatraPositionEnvelopeResponse:
    """Return mechanical Nakshatra placement for one tropical longitude."""
    return compute_nakshatra_position(request)


@router.post("/nakshatra/bulk", response_model=SiderealNakshatraBulkEnvelopeResponse)
def nakshatra_bulk_route(
    request: SiderealNakshatraBulkRequest,
) -> SiderealNakshatraBulkEnvelopeResponse:
    """Return mechanical Nakshatra placements for a bounded longitude map."""
    return compute_nakshatra_bulk(request)
