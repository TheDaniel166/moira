"""Serializers for Phase-10 Local Space transport vessels."""

from __future__ import annotations

from moira.local_space import LocalSpacePosition

from ..models.local_space import (
    LocalSpaceObserverResponse,
    LocalSpacePositionResponse,
    LocalSpacePositionsResponse,
    LocalSpaceProvenanceResponse,
)
from ..services.local_space import (
    LocalSpaceObserverContext,
    LocalSpacePositionsResult,
    LocalSpaceProvenance,
)


def serialize_local_space_position(
    position: LocalSpacePosition,
) -> LocalSpacePositionResponse:
    return LocalSpacePositionResponse(
        body=position.body,
        azimuth=position.azimuth,
        altitude=position.altitude,
        is_above=position.is_above,
        compass_direction=position.compass_direction(),
    )


def serialize_local_space_observer(
    observer: LocalSpaceObserverContext,
) -> LocalSpaceObserverResponse:
    return LocalSpaceObserverResponse(
        latitude=observer.latitude,
        longitude=observer.longitude,
        elevation_m=observer.elevation_m,
        source=observer.source,
    )


def serialize_local_space_provenance(
    provenance: LocalSpaceProvenance,
) -> LocalSpaceProvenanceResponse:
    return LocalSpaceProvenanceResponse(
        requested_datetime=provenance.requested_datetime,
        normalized_datetime_utc=provenance.normalized_datetime_utc,
        jd_ut=provenance.jd_ut,
        jd_tt=provenance.jd_tt,
        lst_deg=provenance.lst_deg,
        observer=serialize_local_space_observer(provenance.observer),
        requested_bodies=(
            list(provenance.requested_bodies)
            if provenance.requested_bodies is not None
            else None
        ),
        returned_bodies=list(provenance.returned_bodies),
        coordinate_source=provenance.coordinate_source,
        stage_sequence=list(provenance.stage_sequence),
    )


def serialize_local_space_positions(
    result: LocalSpacePositionsResult,
) -> LocalSpacePositionsResponse:
    return LocalSpacePositionsResponse(
        positions=[
            serialize_local_space_position(position)
            for position in result.positions
        ],
        provenance=serialize_local_space_provenance(result.provenance),
    )


__all__ = [
    "serialize_local_space_observer",
    "serialize_local_space_position",
    "serialize_local_space_positions",
    "serialize_local_space_provenance",
]
