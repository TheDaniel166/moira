"""Serializers for asteroid surfaces (Phase 11 small-body fast API)."""

from __future__ import annotations

from moira.asteroids import AsteroidData
from moira.constants import sign_of

from ..models.asteroids import AsteroidPositionResponse, AsteroidsBulkResponse


def serialize_asteroid(data: AsteroidData, is_sovereign: bool = False) -> AsteroidPositionResponse:
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
    )


def serialize_asteroids_bulk(
    results: dict[str, AsteroidData],
    missing: list[str],
    sovereign_used: bool,
    dt,
) -> AsteroidsBulkResponse:
    """Serialize bulk results."""
    serialized = {
        key: serialize_asteroid(data, is_sovereign=sovereign_used)
        for key, data in results.items()
    }
    return AsteroidsBulkResponse(
        dt=dt,
        results=serialized,
        missing=missing,
        sovereign_used=sovereign_used,
    )
