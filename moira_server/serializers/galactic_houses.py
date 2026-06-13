"""Serializers for Phase-10 Galactic Houses transport vessels."""

from __future__ import annotations

from moira.galactic_houses import (
    GalacticAngles,
    GalacticHouseBoundaryProfile,
    GalacticHouseCusps,
    GalacticHousePlacement,
)

from ..models.galactic_houses import (
    GalacticAnglesResponse,
    GalacticHouseBodyPlacementResponse,
    GalacticHouseBoundaryResponse,
    GalacticHouseChartPlacementsResponse,
    GalacticHouseCuspsEnvelopeResponse,
    GalacticHouseCuspsResponse,
    GalacticHousePlacementEnvelopeResponse,
    GalacticHousePlacementResponse,
    GalacticHousesProvenanceResponse,
)
from ..services.galactic_houses import (
    GalacticHouseBodyPlacementResult,
    GalacticHouseChartPlacementsResult,
    GalacticHouseCuspsResult,
    GalacticHouseDirectPlacementResult,
    GalacticHousePlacementResult,
    GalacticHousesProvenance,
)


def serialize_galactic_house_angles(
    angles: GalacticAngles,
) -> GalacticAnglesResponse:
    return GalacticAnglesResponse(
        ga_lon=angles.ga_lon,
        gmc_lon=angles.gmc_lon,
        gd_lon=angles.gd_lon,
        gic_lon=angles.gic_lon,
        ga_ecl=angles.ga_ecl,
        gmc_ecl=angles.gmc_ecl,
        gd_ecl=angles.gd_ecl,
        gic_ecl=angles.gic_ecl,
    )


def serialize_galactic_house_cusps(
    cusps: GalacticHouseCusps,
) -> GalacticHouseCuspsResponse:
    return GalacticHouseCuspsResponse(
        cusps_gal=list(cusps.cusps_gal),
        cusps_ecl=list(cusps.cusps_ecl),
        angles=serialize_galactic_house_angles(cusps.angles),
        forward=cusps.forward,
    )


def serialize_galactic_house_placement(
    placement: GalacticHousePlacement,
) -> GalacticHousePlacementResponse:
    return GalacticHousePlacementResponse(
        house=placement.house,
        galactic_longitude=placement.galactic_longitude,
        exact_on_cusp=placement.exact_on_cusp,
        cusp_longitude=placement.cusp_longitude,
    )


def serialize_galactic_house_boundary(
    boundary: GalacticHouseBoundaryProfile,
) -> GalacticHouseBoundaryResponse:
    return GalacticHouseBoundaryResponse(
        opening_cusp=boundary.opening_cusp,
        closing_cusp=boundary.closing_cusp,
        dist_to_opening=boundary.dist_to_opening,
        dist_to_closing=boundary.dist_to_closing,
        house_span=boundary.house_span,
        nearest_cusp=boundary.nearest_cusp,
        nearest_cusp_distance=boundary.nearest_cusp_distance,
        near_cusp_threshold=boundary.near_cusp_threshold,
        is_near_cusp=boundary.is_near_cusp,
    )


def serialize_galactic_houses_provenance(
    provenance: GalacticHousesProvenance,
) -> GalacticHousesProvenanceResponse:
    return GalacticHousesProvenanceResponse(
        requested_datetime=provenance.requested_datetime,
        normalized_datetime_utc=provenance.normalized_datetime_utc,
        jd_ut=provenance.jd_ut,
        jd_tt=provenance.jd_tt,
        latitude=provenance.latitude,
        longitude=provenance.longitude,
        obliquity_deg=provenance.obliquity_deg,
        armc_deg=provenance.armc_deg,
        requested_bodies=(
            list(provenance.requested_bodies)
            if provenance.requested_bodies is not None
            else None
        ),
        returned_bodies=list(provenance.returned_bodies),
        coordinate_source=provenance.coordinate_source,
        stage_sequence=list(provenance.stage_sequence),
    )


def serialize_galactic_house_cusps_result(
    result: GalacticHouseCuspsResult,
) -> GalacticHouseCuspsEnvelopeResponse:
    return GalacticHouseCuspsEnvelopeResponse(
        cusps=serialize_galactic_house_cusps(result.cusps),
        provenance=serialize_galactic_houses_provenance(result.provenance),
    )


def serialize_galactic_house_placement_result(
    result: GalacticHousePlacementResult,
) -> tuple[GalacticHousePlacementResponse, float, GalacticHouseBoundaryResponse]:
    return (
        serialize_galactic_house_placement(result.placement),
        result.fractional_position,
        serialize_galactic_house_boundary(result.boundary),
    )


def serialize_galactic_house_direct_placement(
    result: GalacticHouseDirectPlacementResult,
) -> GalacticHousePlacementEnvelopeResponse:
    placement, fractional_position, boundary = serialize_galactic_house_placement_result(
        result.placement_result
    )
    return GalacticHousePlacementEnvelopeResponse(
        placement=placement,
        fractional_position=fractional_position,
        boundary=boundary,
        provenance=serialize_galactic_houses_provenance(result.provenance),
    )


def serialize_galactic_house_body_placement(
    result: GalacticHouseBodyPlacementResult,
) -> GalacticHouseBodyPlacementResponse:
    placement, fractional_position, boundary = serialize_galactic_house_placement_result(
        result.placement_result
    )
    return GalacticHouseBodyPlacementResponse(
        body=result.body,
        ecliptic_longitude=result.ecliptic_longitude,
        ecliptic_latitude=result.ecliptic_latitude,
        galactic_longitude=result.galactic_longitude,
        galactic_latitude=result.galactic_latitude,
        placement=placement,
        fractional_position=fractional_position,
        boundary=boundary,
    )


def serialize_galactic_house_chart_placements(
    result: GalacticHouseChartPlacementsResult,
) -> GalacticHouseChartPlacementsResponse:
    return GalacticHouseChartPlacementsResponse(
        cusps=serialize_galactic_house_cusps(result.cusps),
        placements=[
            serialize_galactic_house_body_placement(placement)
            for placement in result.placements
        ],
        provenance=serialize_galactic_houses_provenance(result.provenance),
    )


__all__ = [
    "serialize_galactic_house_angles",
    "serialize_galactic_house_body_placement",
    "serialize_galactic_house_boundary",
    "serialize_galactic_house_chart_placements",
    "serialize_galactic_house_cusps",
    "serialize_galactic_house_cusps_result",
    "serialize_galactic_house_direct_placement",
    "serialize_galactic_house_placement",
    "serialize_galactic_house_placement_result",
    "serialize_galactic_houses_provenance",
]
