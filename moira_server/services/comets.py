"""Services for comets (symmetric to asteroids, Phase 11 fast small-body)."""

from __future__ import annotations

from typing import Any

from moira import Moira
from moira.comets import COMET_NAIF, CometData, comet_at

from ..models.comets import (
    CometListItem,
    CometListResponse,
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


def list_sovereign_comets(engine: Moira, name_filter: str | None = None) -> CometListResponse:
    reader = _get_small_body_reader(engine)
    if reader is None:
        return CometListResponse(bodies=[], total=0)

    covered_ids = reader.covered_bodies() if hasattr(reader, "covered_bodies") else frozenset()
    result = [
        CometListItem(name=name, naif_id=naif_id)
        for name, naif_id in COMET_NAIF.items()
        if naif_id in covered_ids
    ]
    if name_filter:
        nf = name_filter.lower()
        result = [
            body for body in result
            if nf in body.name.lower() or nf in str(body.naif_id)
        ]
    result.sort(key=lambda body: body.name)
    return CometListResponse(bodies=result, total=len(result))
