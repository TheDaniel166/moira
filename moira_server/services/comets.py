"""Services for comets (symmetric to asteroids, Phase 11 fast small-body)."""

from __future__ import annotations

from typing import Any

from moira import Moira
from moira.comets import COMET_NAIF, CometData, comet_at
from moira.julian import jd_from_datetime

from ..models.comets import (
    CometListItem,
    CometListProvenanceResponse,
    CometListResponse,
    CometPositionRequest,
    CometPositionResponse,
    CometsBulkRequest,
    CometsBulkResponse,
)
from ..serializers.comets import (
    serialize_comet,
    serialize_comet_bulk_provenance,
    serialize_comet_position_provenance,
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


def _covered_bodies(reader: Any | None) -> frozenset[int]:
    if reader is None or not hasattr(reader, "covered_bodies"):
        return frozenset()
    return frozenset(reader.covered_bodies())


_KNOWN_COMET_NAMES = frozenset(name.casefold() for name in COMET_NAIF)
_KNOWN_COMET_IDS = frozenset(COMET_NAIF.values())
_COMET_NAME_BY_ID = {naif_id: name for name, naif_id in COMET_NAIF.items()}
_COMET_NAME_BY_CASEFOLD = {name.casefold(): name for name in COMET_NAIF}


def _known_comet_entry(body: str | int) -> bool:
    if isinstance(body, int):
        return body in _KNOWN_COMET_IDS
    if body.isdecimal():
        return int(body) in _KNOWN_COMET_IDS
    return body.casefold() in _KNOWN_COMET_NAMES


def _resolve_comet_body(body: str | int) -> str:
    if isinstance(body, int):
        return _COMET_NAME_BY_ID[body]
    if body.isdecimal():
        return _COMET_NAME_BY_ID[int(body)]
    return _COMET_NAME_BY_CASEFOLD[body.casefold()]


def _kernel_source(reader: Any | None) -> str:
    return "loaded_small_body_reader" if reader is not None else "active_reader_or_default_kernel_path"


def compute_comet_position(
    engine: Moira, request: CometPositionRequest
) -> CometPositionResponse:
    reader = _get_small_body_reader(engine)
    resolved_body = _resolve_comet_body(request.body)
    jd_ut = jd_from_datetime(request.dt)
    data: CometData = comet_at(resolved_body, jd_ut, reader=reader)
    covered = _covered_bodies(reader)
    loaded_kernel_available = data.naif_id in covered

    return serialize_comet(
        data,
        is_sovereign=loaded_kernel_available,
        provenance=serialize_comet_position_provenance(
            request=request,
            resolved_body=resolved_body,
            data=data,
            jd_ut=jd_ut,
            kernel_source=_kernel_source(reader),
            known_catalog_entry=_known_comet_entry(request.body),
            loaded_kernel_available=loaded_kernel_available,
        ),
    )


def compute_comets_bulk(
    engine: Moira, request: CometsBulkRequest
) -> CometsBulkResponse:
    reader = _get_small_body_reader(engine)
    covered = _covered_bodies(reader)
    results = {}
    missing: list[str] = []

    jd_ut = jd_from_datetime(request.dt)
    for body in request.bodies:
        try:
            resolved_body = _resolve_comet_body(body)
            data = comet_at(resolved_body, jd_ut, reader=reader)
            loaded_kernel_available = data.naif_id in covered
            results[str(body)] = serialize_comet(
                data,
                is_sovereign=loaded_kernel_available,
                provenance=serialize_comet_position_provenance(
                    request=CometPositionRequest(dt=request.dt, body=body),
                    resolved_body=resolved_body,
                    data=data,
                    jd_ut=jd_ut,
                    kernel_source=_kernel_source(reader),
                    known_catalog_entry=_known_comet_entry(body),
                    loaded_kernel_available=loaded_kernel_available,
                ),
            )
        except Exception:
            if not request.skip_missing:
                raise
            missing.append(str(body))

    return CometsBulkResponse(
        dt=request.dt,
        results=results,
        missing=missing,
        sovereign_used=any(result.is_sovereign for result in results.values()),
        provenance=serialize_comet_bulk_provenance(
            request=request,
            jd_ut=jd_ut,
            kernel_source=_kernel_source(reader),
            returned_bodies=[result.name for result in results.values()],
            missing_bodies=missing,
            loaded_kernel_available=bool(covered),
        ),
    )


def list_sovereign_comets(
    engine: Moira,
    name_filter: str | None = None,
    limit: int = 500,
) -> CometListResponse:
    reader = _get_small_body_reader(engine)
    if reader is None:
        return CometListResponse(
            bodies=[],
            total=0,
            provenance=CometListProvenanceResponse(
                availability_source="no_loaded_reader",
                loaded_kernel_available=False,
                requested_query=name_filter,
                limit=limit,
                returned_count=0,
                stage_sequence=["reader_availability_check", "loaded_kernel_list_serialization"],
            ),
        )

    covered_ids = _covered_bodies(reader)
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
    limited = result[:limit]
    return CometListResponse(
        bodies=limited,
        total=len(limited),
        provenance=CometListProvenanceResponse(
            availability_source="loaded_reader_covered_bodies",
            loaded_kernel_available=True,
            requested_query=name_filter,
            limit=limit,
            returned_count=len(limited),
            stage_sequence=["reader_coverage_intersection", "loaded_kernel_list_serialization"],
        ),
    )
