"""Serializers for asteroid surfaces (Phase 11 small-body fast API)."""

from __future__ import annotations

from datetime import timezone

from moira.asteroids import AsteroidData
from moira.constants import sign_of

from ..models.asteroids import (
    AsteroidPositionProvenanceResponse,
    AsteroidPositionRequest,
    AsteroidPositionResponse,
    AsteroidsBulkProvenanceResponse,
    AsteroidsBulkRequest,
)


def serialize_asteroid_position_provenance(
    *,
    request: AsteroidPositionRequest,
    data: AsteroidData,
    jd_ut: float,
    kernel_source: str,
    known_catalog_entry: bool,
    loaded_kernel_available: bool,
) -> AsteroidPositionProvenanceResponse:
    return AsteroidPositionProvenanceResponse(
        requested_datetime=request.dt.isoformat(),
        normalized_datetime_utc=request.dt.astimezone(timezone.utc).isoformat(),
        jd_ut=jd_ut,
        kernel_source=kernel_source,
        known_catalog_entry=known_catalog_entry,
        loaded_kernel_available=loaded_kernel_available,
        requested_body=str(request.body),
        returned_body=data.name,
        returned_naif_id=data.naif_id,
        stage_sequence=[
            "datetime_validation",
            "julian_day_conversion",
            "asteroid_identity_resolution",
            "small_body_kernel_evaluation",
            "asteroid_response_serialization",
        ],
    )


def serialize_asteroid_bulk_provenance(
    *,
    request: AsteroidsBulkRequest,
    jd_ut: float,
    kernel_source: str,
    returned_bodies: list[str],
    missing_bodies: list[str],
    loaded_kernel_available: bool,
) -> AsteroidsBulkProvenanceResponse:
    return AsteroidsBulkProvenanceResponse(
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
            "bulk_asteroid_identity_resolution",
            "small_body_kernel_evaluation",
            "asteroid_bulk_response_serialization",
        ],
    )


def serialize_asteroid(
    data: AsteroidData,
    is_sovereign: bool = False,
    *,
    provenance: AsteroidPositionProvenanceResponse,
) -> AsteroidPositionResponse:
    """Turn internal AsteroidData into transport-friendly response.

    Includes sign info and sovereign flag for website use.
    Note: Current AsteroidData does not include proper motion or magnitude.
          Those would require extending the public asteroid API or additional kernels.
    """
    sign, sign_symbol, sign_degree = sign_of(data.longitude)
    return AsteroidPositionResponse(
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
