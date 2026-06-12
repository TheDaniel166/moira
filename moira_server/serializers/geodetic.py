"""Serializers for Phase-10 Geodetic transport vessels."""

from __future__ import annotations

from moira.geodetic import GeodeticChart

from ..models.geodetic import (
    GeodeticChartEnvelopeResponse,
    GeodeticChartResponse,
    GeodeticEquivalentResponse,
    GeodeticEquivalentsResponse,
    GeodeticProvenanceResponse,
)
from ..services.geodetic import (
    GeodeticChartResult,
    GeodeticEquivalentsResult,
    GeodeticProvenance,
)


def serialize_geodetic_chart(chart: GeodeticChart) -> GeodeticChartResponse:
    return GeodeticChartResponse(
        geo_latitude=chart.geo_latitude,
        geo_longitude=chart.geo_longitude,
        mc=chart.mc,
        asc=chart.asc,
        obliquity=chart.obliquity,
        zodiac=chart.zodiac,
        ayanamsa_deg=chart.ayanamsa_deg,
    )


def serialize_geodetic_equivalent(
    body: str,
    geographic_longitude: float,
) -> GeodeticEquivalentResponse:
    return GeodeticEquivalentResponse(
        body=body,
        geographic_longitude=geographic_longitude,
    )


def serialize_geodetic_provenance(
    provenance: GeodeticProvenance,
) -> GeodeticProvenanceResponse:
    return GeodeticProvenanceResponse(
        requested_datetime=provenance.requested_datetime,
        normalized_datetime_utc=provenance.normalized_datetime_utc,
        jd_ut=provenance.jd_ut,
        jd_tt=provenance.jd_tt,
        obliquity_deg=provenance.obliquity_deg,
        zodiac=provenance.zodiac,
        ayanamsa_system=provenance.ayanamsa_system,
        ayanamsa_deg=provenance.ayanamsa_deg,
        requested_bodies=(
            list(provenance.requested_bodies)
            if provenance.requested_bodies is not None
            else None
        ),
        returned_bodies=list(provenance.returned_bodies),
        coordinate_source=provenance.coordinate_source,
        stage_sequence=list(provenance.stage_sequence),
    )


def serialize_geodetic_chart_result(
    result: GeodeticChartResult,
) -> GeodeticChartEnvelopeResponse:
    return GeodeticChartEnvelopeResponse(
        chart=serialize_geodetic_chart(result.chart),
        provenance=serialize_geodetic_provenance(result.provenance),
    )


def serialize_geodetic_equivalents_result(
    result: GeodeticEquivalentsResult,
) -> GeodeticEquivalentsResponse:
    return GeodeticEquivalentsResponse(
        equivalents=[
            serialize_geodetic_equivalent(body, longitude)
            for body, longitude in result.equivalents.items()
        ],
        provenance=serialize_geodetic_provenance(result.provenance),
    )


__all__ = [
    "serialize_geodetic_chart",
    "serialize_geodetic_chart_result",
    "serialize_geodetic_equivalent",
    "serialize_geodetic_equivalents_result",
    "serialize_geodetic_provenance",
]
