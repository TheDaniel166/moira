"""Adapt request-local planetary moon contexts to the REST contract."""

from __future__ import annotations

import logging

from moira._kernel_paths import find_kernel
from moira.planetary_moon_events import find_planetary_moon_events
from moira.planetary_moons import PlanetaryMoons
from moira.spk_reader import MissingKernelError, OutOfRangeError

from ..config import ServerConfig, ServerConfigurationError
from ..models.planetary_moons import (
    PlanetaryMoonEventsRequest,
    PlanetaryMoonEventsResponse,
    PlanetaryMoonsCoverageInterval,
    PlanetaryMoonsCoverageResponse,
    PlanetaryMoonsSnapshotRequest,
    PlanetaryMoonsSnapshotResponse,
    PlanetaryMoonsSystemCoverage,
)


logger = logging.getLogger(__name__)


class PlanetaryMoonsCoverageError(ValueError):
    """The requested reception or a required retarded epoch is unavailable."""


def _open_moons(config: ServerConfig) -> PlanetaryMoons:
    manifest = config.planetary_moons_manifest
    if manifest is None:
        raise ServerConfigurationError(
            "Planetary moon data is not configured. Set MOIRA_SERVER_PLANETARY_MOONS_MANIFEST."
        )
    try:
        return PlanetaryMoons.open(
            de441_path=config.kernel_path or find_kernel("de441.bsp"),
            manifest_path=manifest,
        )
    except (OSError, ValueError, RuntimeError) as exc:
        logger.warning("Planetary moon data could not be opened: %s", exc)
        raise MissingKernelError("The required planetary moon data could not be loaded.") from exc


def compute_planetary_moons_snapshot(
    config: ServerConfig, request: PlanetaryMoonsSnapshotRequest,
) -> PlanetaryMoonsSnapshotResponse:
    """Compute and serialize a snapshot on the worker that owns its context."""

    with _open_moons(config) as moons:
        try:
            snapshot = moons.at(request.jd_tt, planet=request.planet)
        except FileNotFoundError as exc:
            selection = request.planet or "Jupiter and Saturn"
            raise MissingKernelError(f"Planetary moon data for {selection} is required.") from exc
        except OutOfRangeError as exc:
            raise PlanetaryMoonsCoverageError(
                "The requested epoch or a required light-time evaluation is "
                "outside the installed planetary moon coverage."
            ) from exc
    return PlanetaryMoonsSnapshotResponse.model_validate(snapshot)


def compute_planetary_moons_coverage(config: ServerConfig) -> PlanetaryMoonsCoverageResponse:
    """Report the geometric state intervals admitted by the installed data."""

    with _open_moons(config) as moons:
        coverage = moons.coverage_tdb()
    return PlanetaryMoonsCoverageResponse(
        systems=tuple(
            PlanetaryMoonsSystemCoverage(
                planet=planet,
                intervals_tdb=tuple(
                    PlanetaryMoonsCoverageInterval(start_jd_tdb=start, end_jd_tdb=end)
                    for start, end in intervals
                ),
            )
            for planet, intervals in coverage.items()
        )
    )


def compute_planetary_moon_events(
    config: ServerConfig, request: PlanetaryMoonEventsRequest,
) -> PlanetaryMoonEventsResponse:
    """Run the finite-disk solver on the thread that owns its kernels."""

    with _open_moons(config) as context:
        try:
            result = find_planetary_moon_events(
                context, request.jd_start_tt, request.jd_end_tt,
                planet=request.planet, moon_ids=request.moon_ids, kinds=request.kinds,
                mode=request.mode, max_evaluations=request.max_evaluations,
                max_results=request.max_results,
            )
        except FileNotFoundError as exc:
            raise MissingKernelError("Planetary moon data for a requested system is unavailable.") from exc
        except OutOfRangeError as exc:
            raise PlanetaryMoonsCoverageError(
                "The requested interval or a required light-time evaluation is outside installed coverage."
            ) from exc
    return PlanetaryMoonEventsResponse(request=request, result=result)
