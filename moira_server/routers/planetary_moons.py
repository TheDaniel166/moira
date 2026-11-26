"""REST routes for Jupiter and Saturn moon snapshots and source coverage."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..config import ServerConfig
from ..dependencies import get_config
from ..models.planetary_moons import (
    PlanetaryMoonEventsRequest,
    PlanetaryMoonEventsResponse,
    PlanetaryMoonsCoverageResponse,
    PlanetaryMoonsSnapshotRequest,
    PlanetaryMoonsSnapshotResponse,
)
from ..services.planetary_moons import (
    compute_planetary_moon_events,
    compute_planetary_moons_coverage,
    compute_planetary_moons_snapshot,
)


router = APIRouter(prefix="/v1/planetary-moons", tags=["planetary-moons"])


@router.post(
    "/events",
    response_model=PlanetaryMoonEventsResponse,
    responses={
        422: {"description": "Invalid input or interval outside installed coverage."},
        503: {"description": "Required planetary moon data is unavailable."},
    },
)
def planetary_moon_events_route(
    request: PlanetaryMoonEventsRequest, config: ServerConfig = Depends(get_config),
) -> PlanetaryMoonEventsResponse:
    """Search Jupiter and Saturn finite-disk contacts over a bounded TT interval."""

    return compute_planetary_moon_events(config, request)


@router.post(
    "/snapshot",
    response_model=PlanetaryMoonsSnapshotResponse,
    responses={
        422: {"description": "Invalid input or epoch outside installed coverage."},
        503: {"description": "Required planetary moon data is unavailable."},
    },
)
def planetary_moons_snapshot_route(
    request: PlanetaryMoonsSnapshotRequest,
    config: ServerConfig = Depends(get_config),
) -> PlanetaryMoonsSnapshotResponse:
    """Return parent-relative states, Earth-view events, phases, and eclipses at a TT epoch."""

    return compute_planetary_moons_snapshot(config, request)


@router.get(
    "/coverage",
    response_model=PlanetaryMoonsCoverageResponse,
    responses={503: {"description": "Planetary moon data is unavailable."}},
)
def planetary_moons_coverage_route(
    config: ServerConfig = Depends(get_config),
) -> PlanetaryMoonsCoverageResponse:
    """Return closed TDB state intervals. Reception snapshots also require light-time coverage."""

    return compute_planetary_moons_coverage(config)
