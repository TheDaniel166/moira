"""Serializers for comet surfaces."""

from __future__ import annotations

from datetime import timezone

from moira.comets import CometData
from moira.constants import sign_of

from ..models.comets import (
    CometPositionProvenanceResponse,
    CometPositionRequest,
    CometPositionResponse,
    CometsBulkProvenanceResponse,
    CometsBulkRequest,
)


def serialize_comet_position_provenance(
    *,
    request: CometPositionRequest,
    resolved_body: str,
    data: CometData,
    jd_ut: float,
    kernel_source: str,
    known_catalog_entry: bool,
    loaded_kernel_available: bool,
) -> CometPositionProvenanceResponse:
    return CometPositionProvenanceResponse(
        requested_datetime=request.dt.isoformat(),
        normalized_datetime_utc=request.dt.astimezone(timezone.utc).isoformat(),
        jd_ut=jd_ut,
        kernel_source=kernel_source,
        known_catalog_entry=known_catalog_entry,
        loaded_kernel_available=loaded_kernel_available,
        requested_body=str(request.body),
        resolved_body=resolved_body,
        returned_body=data.name,
        returned_naif_id=data.naif_id,
        stage_sequence=[
            "datetime_validation",
            "julian_day_conversion",
            "comet_identity_resolution",
            "small_body_kernel_evaluation",
            "comet_response_serialization",
        ],
    )


def serialize_comet_bulk_provenance(
    *,
    request: CometsBulkRequest,
    jd_ut: float,
    kernel_source: str,
    returned_bodies: list[str],
    missing_bodies: list[str],
    loaded_kernel_available: bool,
) -> CometsBulkProvenanceResponse:
    return CometsBulkProvenanceResponse(
        requested_datetime=request.dt.isoformat(),
        normalized_datetime_utc=request.dt.astimezone(timezone.utc).isoformat(),
        jd_ut=jd_ut,
        kernel_source=kernel_source,
        requested_bodies=[str(body) for body in request.bodies],
        returned_bodies=list(returned_bodies),
        missing_bodies=list(missing_bodies),
        loaded_kernel_available=loaded_kernel_available,
        stage_sequence=[
            "datetime_validation",
            "julian_day_conversion",
            "bulk_comet_identity_resolution",
            "small_body_kernel_evaluation",
            "comet_bulk_response_serialization",
        ],
    )


def serialize_comet(
    data: CometData,
    is_sovereign: bool = False,
    *,
    provenance: CometPositionProvenanceResponse,
) -> CometPositionResponse:
    sign, sign_symbol, sign_degree = sign_of(data.longitude)
    return CometPositionResponse(
        name=data.name,
        naif_id=data.naif_id,
        longitude=data.longitude,
        latitude=data.latitude,
        distance=data.distance,
        speed=data.speed,
        retrograde=data.retrograde,
        sign=sign,
        sign_symbol=sign_symbol,
        sign_degree=sign_degree,
        is_sovereign=is_sovereign,
        provenance=provenance,
    )
