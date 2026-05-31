"""Serializers for stars surfaces."""

from __future__ import annotations

from moira.stars import star_at, StarPosition
from moira.constants import sign_of

from ..models.stars import StarPositionResponse, StarsBulkResponse, StarListResponse


def serialize_star(data: StarPosition | dict, is_variable: bool = False) -> StarPositionResponse:
    """Normalize star position result."""
    if isinstance(data, dict):
        lon = data.get("longitude", data.get("ecliptic_longitude", 0.0))
        lat = data.get("latitude", data.get("ecliptic_latitude", 0.0))
        name = data.get("name", data.get("designation", "Unknown"))
        designation = data.get("designation")
        mag = data.get("magnitude")
    else:
        lon = getattr(data, "longitude", 0.0)
        lat = getattr(data, "latitude", 0.0)
        name = getattr(data, "name", "Unknown")
        designation = getattr(data, "designation", None)
        mag = getattr(data, "magnitude", None)

    sign, sign_symbol, sign_degree = sign_of(lon)

    return StarPositionResponse(
        name=name,
        designation=designation,
        longitude=lon,
        latitude=lat,
        distance=None,
        magnitude=mag,
        sign=sign,
        sign_symbol=sign_symbol,
        sign_degree=sign_degree,
        is_variable=is_variable,
    )


def serialize_stars_bulk(results: dict, missing: list[str]) -> StarsBulkResponse:
    serialized = {}
    for key, data in results.items():
        serialized[key] = serialize_star(data)

    return StarsBulkResponse(
        dt=results.get("dt") if isinstance(results, dict) else None,  # placeholder
        results=serialized,
        missing=missing,
    )
