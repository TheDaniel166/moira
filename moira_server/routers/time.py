"""Time-scale conversion, Delta-T diagnostics, and sidereal time."""

from __future__ import annotations

from fastapi import APIRouter

from ..models.time import (
    DeltaTRequest,
    DeltaTResponse,
    SiderealTimeRequest,
    SiderealTimeResponse,
    TimeConversionInput,
    TimeConversionResponse,
)
from ..services.time import compute_delta_t, compute_sidereal_time, convert_time


router = APIRouter(prefix="/v1/time", tags=["time"])


@router.post("/convert", response_model=TimeConversionResponse)
def time_conversion_route(request: TimeConversionInput) -> TimeConversionResponse:
    """Convert a labelled epoch using an admitted Moira time model."""

    return convert_time(request)


@router.post("/delta-t", response_model=DeltaTResponse)
def delta_t_route(request: DeltaTRequest) -> DeltaTResponse:
    """Return a Delta-T estimate, component breakdown, or policy distribution."""

    return compute_delta_t(request)


@router.post("/sidereal", response_model=SiderealTimeResponse)
def sidereal_time_route(request: SiderealTimeRequest) -> SiderealTimeResponse:
    """Return mean or apparent sidereal time at explicit UT1 and TT."""

    return compute_sidereal_time(request)
