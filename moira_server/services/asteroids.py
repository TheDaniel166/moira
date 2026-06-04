"""Services for asteroid (and later comet) surfaces.

Designed for "fast API" use on websites:
- Automatically uses sovereign small-body Type 13 + native evaluator when loaded at startup.
- Falls back gracefully.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from moira import Moira
from moira.asteroids import ASTEROID_NAIF, AsteroidData, asteroid_at
from moira.julian import jd_from_datetime

from ..models.asteroids import (
    AsteroidListItem,
    AsteroidListResponse,
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
    jd_ut = jd_from_datetime(request.dt) if isinstance(request.dt, datetime) else float(request.dt)
    data: AsteroidData = asteroid_at(
        request.body,
        jd_ut,
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
        sign=data.sign,
        sign_symbol=data.sign_symbol,
        sign_degree=data.sign_degree,
        is_sovereign=is_sovereign,
    )


def compute_asteroids_bulk(
    engine: Moira, request: AsteroidsBulkRequest
) -> AsteroidsBulkResponse:
    """Bulk asteroid positions — the fast path for websites loading many bodies at once."""
    reader = _get_small_body_reader(engine)

    results: dict[str, AsteroidPositionResponse] = {}
    missing: list[str] = []

    jd_ut = jd_from_datetime(request.dt) if isinstance(request.dt, datetime) else float(request.dt)
    for body in request.bodies:
        try:
            data = asteroid_at(body, jd_ut, reader=reader)
            is_sovereign = reader is not None
            results[str(body)] = AsteroidPositionResponse(
                name=data.name,
                naif_id=data.naif_id,
                longitude=data.longitude,
                latitude=data.latitude,
                distance=data.distance,
                speed=data.speed,
                retrograde=data.retrograde,
                sign=data.sign,
                sign_symbol=data.sign_symbol,
                sign_degree=data.sign_degree,
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


def list_sovereign_asteroids(engine: Moira, name_filter: str | None = None) -> AsteroidListResponse:
    """
    Return bodies available in the loaded sovereign small-body kernels.
    Supports basic name/NAIF filtering for website search.
    """
    reader = _get_small_body_reader(engine)
    if reader is None:
        return AsteroidListResponse(bodies=[], total=0)

    covered_ids = reader.covered_bodies() if hasattr(reader, "covered_bodies") else frozenset()
    result = [
        AsteroidListItem(name=name, naif_id=naif_id)
        for name, naif_id in ASTEROID_NAIF.items()
        if naif_id in covered_ids
    ]
    if name_filter:
        nf = name_filter.lower()
        result = [
            body for body in result
            if nf in body.name.lower() or nf in str(body.naif_id)
        ]
    result.sort(key=lambda body: body.name)
    return AsteroidListResponse(bodies=result, total=len(result))
