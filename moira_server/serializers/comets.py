"""Serializers for comet surfaces."""

from __future__ import annotations

from moira.comets import CometData
from moira.constants import sign_of

from ..models.comets import CometPositionResponse, CometsBulkResponse


def serialize_comet(data: CometData, is_sovereign: bool = False) -> CometPositionResponse:
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
    )


def serialize_comets_bulk(
    results: dict[str, CometData],
    missing: list[str],
    sovereign_used: bool,
    dt,
) -> CometsBulkResponse:
    serialized = {
        key: serialize_comet(data, is_sovereign=sovereign_used)
        for key, data in results.items()
    }
    return CometsBulkResponse(
        dt=dt,
        results=serialized,
        missing=missing,
        sovereign_used=sovereign_used,
    )
