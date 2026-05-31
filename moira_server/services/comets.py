"""Services for comets (symmetric to asteroids, Phase 11 fast small-body)."""

from __future__ import annotations

from moira import Moira
from moira.comets import comet_at, CometData
from moira.spk_reader import KernelPool

from ..models.comets import (
    CometPositionRequest,
    CometPositionResponse,
    CometsBulkRequest,
    CometsBulkResponse,
)


def _get_small_body_reader(engine: Moira) -> Any | None:
    """
    Return the active reader (includes sovereign small-body kernels
    loaded via the proper Moira.load_small_body_manifest API).
    """
    try:
        return engine._reader
    except Exception:
        return None


def compute_comet_position(
    engine: Moira, request: CometPositionRequest
) -> CometPositionResponse:
    reader = _get_small_body_reader(engine)
    data: CometData = comet_at(request.body, request.dt, reader=reader)
    is_sovereign = reader is not None

    return CometPositionResponse(
        name=data.name,
        naif_id=data.naif_id,
        longitude=data.longitude,
        latitude=data.latitude,
        distance=data.distance,
        speed=data.speed,
        retrograde=data.retrograde,
        is_sovereign=is_sovereign,
    )


def compute_comets_bulk(
    engine: Moira, request: CometsBulkRequest
) -> CometsBulkResponse:
    reader = _get_small_body_reader(engine)
    results: dict[str, CometData] = {}
    missing: list[str] = []

    for body in request.bodies:
        try:
            data = comet_at(body, request.dt, reader=reader)
            results[str(body)] = data
        except Exception:
            if not request.skip_missing:
                raise
            missing.append(str(body))

    return CometsBulkResponse(
        dt=request.dt,
        results={
            key: CometPositionResponse(
                name=d.name,
                naif_id=d.naif_id,
                longitude=d.longitude,
                latitude=d.latitude,
                distance=d.distance,
                speed=d.speed,
                retrograde=d.retrograde,
                is_sovereign=(reader is not None),
            )
            for key, d in results.items()
        },
        missing=missing,
        sovereign_used=(reader is not None),
    )


def list_sovereign_comets(engine: Moira, name_filter: str | None = None) -> list[str]:
    reader = _get_small_body_reader(engine)
    if reader is None:
        return []
    bodies: set[str] = set()
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
