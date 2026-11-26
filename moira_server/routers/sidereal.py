"""Sidereal and Nakshatra utility routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine, with_engine_reader

from ..models.sidereal import (
    AyanamsaSystemsEnvelopeResponse,
    GalacticAyanamsaPresetsResponse,
    SiderealAyanamsaRequest,
    SiderealAyanamsaResponse,
    SiderealChartRequest,
    SiderealChartResponse,
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
    compute_sidereal_chart,
    convert_sidereal_longitude,
    list_galactic_ayanamsa_presets,
    list_sidereal_ayanamsa_systems,
)


router = APIRouter(prefix="/v1", tags=["sidereal"])


@router.post("/chart/sidereal", response_model=SiderealChartResponse)
@with_engine_reader
def sidereal_chart_route(
    request: SiderealChartRequest,
    engine: Moira = Depends(get_engine),
) -> SiderealChartResponse:
    """Return one chart reduced with a request-local ayanamsa."""

    return compute_sidereal_chart(engine, request)


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


@router.get("/sidereal/galactic-ayanamsa-presets", response_model=GalacticAyanamsaPresetsResponse)
def galactic_ayanamsa_presets_route() -> GalacticAyanamsaPresetsResponse:
    """List Galactic ayanamsa selections, anchors, and sources."""

    return list_galactic_ayanamsa_presets()


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
