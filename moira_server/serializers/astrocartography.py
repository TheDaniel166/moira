"""Serializers for Phase-10 Astrocartography transport vessels."""

from __future__ import annotations

from moira.astrocartography import ACGLine, SubPlanetaryPoint

from ..models.astrocartography import (
    AstrocartographyGeoPointResponse,
    AstrocartographyLineResponse,
    AstrocartographyLinesResponse,
    AstrocartographyObserverResponse,
    AstrocartographyProvenanceResponse,
    AstrocartographySubjectProvenanceResponse,
    AstrocartographySubplanetaryPointResponse,
    AstrocartographySubplanetaryResponse,
)
from ..services.astrocartography import (
    AstrocartographyLinesResult,
    AstrocartographyObserverContext,
    AstrocartographyProvenance,
    AstrocartographySubplanetaryResult,
)


def serialize_astrocartography_line(line: ACGLine) -> AstrocartographyLineResponse:
    return AstrocartographyLineResponse(
        planet=line.planet,
        line_type=line.line_type,
        longitude=line.longitude,
        points=[
            AstrocartographyGeoPointResponse(latitude=latitude, longitude=longitude)
            for latitude, longitude in line.points
        ],
    )


def serialize_subplanetary_point(
    point: SubPlanetaryPoint,
) -> AstrocartographySubplanetaryPointResponse:
    return AstrocartographySubplanetaryPointResponse(
        planet=point.planet,
        point_type=point.point_type,
        latitude=point.latitude,
        longitude=point.longitude,
    )


def serialize_astrocartography_observer(
    observer: AstrocartographyObserverContext,
) -> AstrocartographyObserverResponse:
    return AstrocartographyObserverResponse(
        latitude=observer.latitude,
        longitude=observer.longitude,
        elevation_m=observer.elevation_m,
        source=observer.source,
    )


def serialize_astrocartography_provenance(
    provenance: AstrocartographyProvenance,
) -> AstrocartographyProvenanceResponse:
    return AstrocartographyProvenanceResponse(
        requested_datetime=provenance.requested_datetime,
        normalized_datetime_utc=provenance.normalized_datetime_utc,
        jd_ut=provenance.jd_ut,
        jd_tt=provenance.jd_tt,
        gmst_deg=provenance.gmst_deg,
        obliquity_deg=provenance.obliquity_deg,
        nutation_longitude_deg=provenance.nutation_longitude_deg,
        requested_bodies=(
            list(provenance.requested_bodies)
            if provenance.requested_bodies is not None
            else None
        ),
        returned_bodies=list(provenance.returned_bodies),
        observer=serialize_astrocartography_observer(provenance.observer),
        coordinate_source=provenance.coordinate_source,
        subjects=[
            AstrocartographySubjectProvenanceResponse(
                requested_label=subject.requested_label,
                returned_label=subject.returned_label,
                subject_class=subject.subject_class,
                canonical_name=subject.canonical_name,
                naif_id=subject.naif_id,
                position_source=subject.position_source,
            )
            for subject in provenance.subjects
        ],
        lat_step=provenance.lat_step,
        refraction=provenance.refraction,
        stage_sequence=list(provenance.stage_sequence),
    )


def serialize_astrocartography_lines(
    result: AstrocartographyLinesResult,
) -> AstrocartographyLinesResponse:
    return AstrocartographyLinesResponse(
        lines=[serialize_astrocartography_line(line) for line in result.lines],
        provenance=serialize_astrocartography_provenance(result.provenance),
    )


def serialize_astrocartography_subplanetary(
    result: AstrocartographySubplanetaryResult,
) -> AstrocartographySubplanetaryResponse:
    return AstrocartographySubplanetaryResponse(
        points=[
            serialize_subplanetary_point(point)
            for point in result.points
        ],
        provenance=serialize_astrocartography_provenance(result.provenance),
    )


__all__ = [
    "serialize_astrocartography_line",
    "serialize_astrocartography_lines",
    "serialize_astrocartography_observer",
    "serialize_astrocartography_provenance",
    "serialize_astrocartography_subplanetary",
    "serialize_subplanetary_point",
]
