"""Serializers for Phase-10 Gauquelin Sectors transport vessels."""

from __future__ import annotations

from moira.gauquelin import GauquelinPosition

from ..models.gauquelin import (
    GauquelinPositionResponse,
    GauquelinProvenanceResponse,
    GauquelinSectorResponse,
    GauquelinSectorsResponse,
)
from ..services.gauquelin import (
    GauquelinPositionResult,
    GauquelinProvenance,
    GauquelinSectorResult,
    GauquelinSectorsResult,
)


def serialize_gauquelin_position(
    position: GauquelinPosition,
    *,
    right_ascension: float | None = None,
    declination: float | None = None,
) -> GauquelinPositionResponse:
    return GauquelinPositionResponse(
        body=position.body,
        sector=position.sector,
        zone=position.zone,
        diurnal_position=position.diurnal_position,
        sectors=position.sectors,
        degree_in_sector=position.degree_in_sector,
        is_plus_zone=position.is_plus_zone,
        horizon_status=position.horizon_status.value,
        right_ascension=right_ascension,
        declination=declination,
    )


def serialize_gauquelin_position_result(
    result: GauquelinPositionResult,
) -> GauquelinPositionResponse:
    source = result.source_coordinate
    return serialize_gauquelin_position(
        result.position,
        right_ascension=source.right_ascension if source is not None else None,
        declination=source.declination if source is not None else None,
    )


def serialize_gauquelin_provenance(
    provenance: GauquelinProvenance,
) -> GauquelinProvenanceResponse:
    return GauquelinProvenanceResponse(
        requested_datetime=provenance.requested_datetime,
        normalized_datetime_utc=provenance.normalized_datetime_utc,
        jd_ut=provenance.jd_ut,
        jd_tt=provenance.jd_tt,
        latitude=provenance.latitude,
        longitude=provenance.longitude,
        local_sidereal_time=provenance.local_sidereal_time,
        horizon_altitude=provenance.horizon_altitude,
        sectors=provenance.sectors,
        requested_bodies=(
            list(provenance.requested_bodies)
            if provenance.requested_bodies is not None
            else None
        ),
        returned_bodies=list(provenance.returned_bodies),
        coordinate_source=provenance.coordinate_source,
        stage_sequence=list(provenance.stage_sequence),
    )


def serialize_gauquelin_sector(
    result: GauquelinSectorResult,
) -> GauquelinSectorResponse:
    return GauquelinSectorResponse(
        position=serialize_gauquelin_position_result(result.position),
        provenance=serialize_gauquelin_provenance(result.provenance),
    )


def serialize_gauquelin_sectors(
    result: GauquelinSectorsResult,
) -> GauquelinSectorsResponse:
    return GauquelinSectorsResponse(
        positions=[
            serialize_gauquelin_position_result(position)
            for position in result.positions
        ],
        provenance=serialize_gauquelin_provenance(result.provenance),
    )


__all__ = [
    "serialize_gauquelin_position",
    "serialize_gauquelin_position_result",
    "serialize_gauquelin_provenance",
    "serialize_gauquelin_sector",
    "serialize_gauquelin_sectors",
]
