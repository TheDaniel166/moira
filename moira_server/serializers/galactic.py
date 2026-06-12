"""Serializers for Phase-10 Galactic Coordinates transport vessels."""

from __future__ import annotations

from moira.galactic import GalacticPosition

from ..models.galactic import (
    GalacticCoordinateResponse,
    GalacticEclipticCoordinateResponse,
    GalacticEquatorialCoordinateResponse,
    GalacticPositionResponse,
    GalacticPositionsResponse,
    GalacticProvenanceResponse,
    GalacticReferencePointResponse,
    GalacticReferencePointsResponse,
)
from ..services.galactic import (
    EclipticCoordinateResult,
    EquatorialCoordinateResult,
    GalacticCoordinateResult,
    GalacticPositionsResult,
    GalacticProvenance,
    GalacticReferencePointsResult,
)


def serialize_galactic_provenance(
    provenance: GalacticProvenance,
) -> GalacticProvenanceResponse:
    return GalacticProvenanceResponse(
        requested_datetime=provenance.requested_datetime,
        normalized_datetime_utc=provenance.normalized_datetime_utc,
        jd_ut=provenance.jd_ut,
        jd_tt=provenance.jd_tt,
        obliquity_deg=provenance.obliquity_deg,
        requested_bodies=(
            list(provenance.requested_bodies)
            if provenance.requested_bodies is not None
            else None
        ),
        returned_bodies=list(provenance.returned_bodies),
        source_frame=provenance.source_frame,
        target_frame=provenance.target_frame,
        coordinate_source=provenance.coordinate_source,
        stage_sequence=list(provenance.stage_sequence),
    )


def serialize_galactic_coordinate(
    result: GalacticCoordinateResult,
) -> GalacticCoordinateResponse:
    provenance = serialize_galactic_provenance(result.provenance)
    return GalacticCoordinateResponse(
        galactic_longitude=result.galactic_longitude,
        galactic_latitude=result.galactic_latitude,
        source_frame=result.provenance.source_frame,
        target_frame=result.provenance.target_frame,
        provenance=provenance,
    )


def serialize_equatorial_coordinate(
    result: EquatorialCoordinateResult,
) -> GalacticEquatorialCoordinateResponse:
    provenance = serialize_galactic_provenance(result.provenance)
    return GalacticEquatorialCoordinateResponse(
        right_ascension=result.right_ascension,
        declination=result.declination,
        source_frame=result.provenance.source_frame,
        target_frame=result.provenance.target_frame,
        provenance=provenance,
    )


def serialize_ecliptic_coordinate(
    result: EclipticCoordinateResult,
) -> GalacticEclipticCoordinateResponse:
    provenance = serialize_galactic_provenance(result.provenance)
    return GalacticEclipticCoordinateResponse(
        ecliptic_longitude=result.ecliptic_longitude,
        ecliptic_latitude=result.ecliptic_latitude,
        source_frame=result.provenance.source_frame,
        target_frame=result.provenance.target_frame,
        provenance=provenance,
    )


def serialize_reference_points(
    result: GalacticReferencePointsResult,
) -> GalacticReferencePointsResponse:
    return GalacticReferencePointsResponse(
        points=[
            GalacticReferencePointResponse(
                name=name,
                ecliptic_longitude=longitude,
                ecliptic_latitude=latitude,
                source_frame=result.provenance.source_frame,
                target_frame=result.provenance.target_frame,
            )
            for name, (longitude, latitude) in result.points.items()
        ],
        provenance=serialize_galactic_provenance(result.provenance),
    )


def serialize_galactic_position(
    position: GalacticPosition,
) -> GalacticPositionResponse:
    return GalacticPositionResponse(
        body=position.body,
        galactic_longitude=position.lon,
        galactic_latitude=position.lat,
        ecliptic_longitude=position.ecliptic_lon,
        ecliptic_latitude=position.ecliptic_lat,
        near_galactic_plane=position.near_galactic_plane,
        galactic_hemisphere=position.galactic_hemisphere,
        angular_distance_to_galactic_center=position.angular_distance_to_gc,
        angular_distance_to_galactic_anticenter=position.angular_distance_to_anticenter,
    )


def serialize_galactic_positions(
    result: GalacticPositionsResult,
) -> GalacticPositionsResponse:
    return GalacticPositionsResponse(
        positions=[
            serialize_galactic_position(position)
            for position in result.positions
        ],
        provenance=serialize_galactic_provenance(result.provenance),
    )


__all__ = [
    "serialize_ecliptic_coordinate",
    "serialize_equatorial_coordinate",
    "serialize_galactic_coordinate",
    "serialize_galactic_position",
    "serialize_galactic_positions",
    "serialize_galactic_provenance",
    "serialize_reference_points",
]
