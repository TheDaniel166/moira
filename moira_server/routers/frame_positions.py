"""Frame-specific position routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from moira import Moira

from ..dependencies import get_engine
from ..models.frame_positions import (
    FrameHeliocentricRequest,
    FrameHeliocentricResponse,
    FramePlanetocentricRequest,
    FramePlanetocentricResponse,
    FrameReceivedLightRequest,
    FrameReceivedLightResponse,
    FrameSSBRequest,
    FrameSSBResponse,
)
from ..services.frame_positions import (
    compute_frame_heliocentric,
    compute_frame_planetocentric,
    compute_frame_received_light,
    compute_frame_ssb,
)


router = APIRouter(prefix="/v1/positions/frame", tags=["positions-frame"])


@router.post("/heliocentric", response_model=FrameHeliocentricResponse)
def frame_heliocentric_route(
    request: FrameHeliocentricRequest,
    engine: Moira = Depends(get_engine),
) -> FrameHeliocentricResponse:
    """Return Sun-centered true-of-date ecliptic positions."""

    return compute_frame_heliocentric(engine, request)


@router.post("/planetocentric", response_model=FramePlanetocentricResponse)
def frame_planetocentric_route(
    request: FramePlanetocentricRequest,
    engine: Moira = Depends(get_engine),
) -> FramePlanetocentricResponse:
    """Return true-of-date ecliptic positions from a named body center."""

    return compute_frame_planetocentric(engine, request)


@router.post("/ssb", response_model=FrameSSBResponse)
def frame_ssb_route(
    request: FrameSSBRequest,
    engine: Moira = Depends(get_engine),
) -> FrameSSBResponse:
    """Return Solar System Barycenter true-of-date ecliptic positions."""

    return compute_frame_ssb(engine, request)


@router.post("/received-light", response_model=FrameReceivedLightResponse)
def frame_received_light_route(
    request: FrameReceivedLightRequest,
    engine: Moira = Depends(get_engine),
) -> FrameReceivedLightResponse:
    """Return received-light positions with same-time geometric comparison."""

    return compute_frame_received_light(engine, request)


__all__ = ["router"]
