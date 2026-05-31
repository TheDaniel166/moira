"""Services for asteroid (and later comet) surfaces.

Designed for "fast API" use on websites:
- Automatically uses sovereign small-body Type 13 + native evaluator when loaded at startup.
- Falls back gracefully.
"""

from __future__ import annotations

from datetime import datetime

from moira import Moira
from moira.asteroids import asteroid_at, AsteroidData
from moira.spk_reader import KernelPool

from ..models.asteroids import (
    AsteroidPositionRequest,
    AsteroidPositionResponse,
    AsteroidsBulkRequest,
    AsteroidsBulkResponse,
)


def _get_small_body_reader(engine: Moira) -> Any | None:
    """
    Return the active reader (which now includes sovereign small-body kernels
    loaded via the proper Moira engine API).
    """
    try:
        return engine._reader  # The facade maintains the full pool (planetary + small bodies)
    except Exception:
        return None


def compute_asteroid_position(
    engine: Moira, request: AsteroidPositionRequest
) -> AsteroidPositionResponse:
    """High-performance asteroid position using native Type 13 path when available."""
    reader = _get_small_body_reader(engine)
    data: AsteroidData = asteroid_at(
        request.body,
        request.dt,
        reader=reader,   # This is the key: passes sovereign fast kernels if present
    )

    # Heuristic: if we have small body kernels loaded, assume we used the fast path.
    is_sovereign = reader is not None

    return AsteroidPositionResponse(
        name=data.name,
        naif_id=data.naif_id,
        longitude=data.longitude,
        latitude=data.latitude,
        distance=data.distance,
        speed=data.speed,
        retrograde=data.retrograde,
        is_sovereign=is_sovereign,
    )


def compute_asteroids_bulk(
    engine: Moira, request: AsteroidsBulkRequest
) -> AsteroidsBulkResponse:
    """Bulk asteroid positions — the fast path for websites loading many bodies at once."""
    reader = _get_small_body_reader(engine)

    results: dict[str, AsteroidPositionResponse] = {}
    missing: list[str] = []

    for body in request.bodies:
        try:
            data = asteroid_at(body, request.dt, reader=reader)
            is_sovereign = reader is not None
            results[str(body)] = AsteroidPositionResponse(
                name=data.name,
                naif_id=data.naif_id,
                longitude=data.longitude,
                latitude=data.latitude,
                distance=data.distance,
                speed=data.speed,
                retrograde=data.retrograde,
                is_sovereign=is_sovereign,
            )
        except Exception:
            if not request.skip_missing:
                raise
            missing.append(str(body))

    return AsteroidsBulkResponse(
        dt=request.dt,
        results=results,
        missing=missing,
        sovereign_used=(reader is not None),
    )


def list_sovereign_asteroids(engine: Moira, name_filter: str | None = None) -> list[str]:
    """
    Return bodies available in the loaded sovereign small-body kernels.
    Supports basic name/NAIF filtering for website search.
    """
    reader = _get_small_body_reader(engine)
    if reader is None:
        return []

    bodies: set[str] = set()
    # The reader may be a pool or single kernel
    segments = []
    if hasattr(reader, "segments"):
        segments = reader.segments
    elif hasattr(reader, "_kernel"):
        segments = reader._kernel.segments

    for seg in segments:
        if getattr(seg, "data_type", None) == 13:
            naif = getattr(seg, "target", None)
            if naif:
                bodies.add(str(naif))

    result = sorted(bodies)
    if name_filter:
        nf = name_filter.lower()
        result = [b for b in result if nf in b.lower()]
    return result
