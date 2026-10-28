"""Serializers for Phase-10 Geodetic transport vessels."""

from __future__ import annotations

from moira.geodetic import (
    GeodeticAngleDerivatives,
    GeodeticChart,
    GeodeticGeometryWitness,
    GeodeticInputUncertainty,
    GeodeticSensitivityResult,
)
from moira.geodetic_uncertainty import GeodeticNonlinearityResult

from ..models.geodetic import (
    GeodeticAngleDerivativesResponse,
    GeodeticAngleTargetsResponse,
    GeodeticChartEnvelopeResponse,
    GeodeticChartResponse,
    GeodeticCircularArcResponse,
    GeodeticDiagnosticPolicyModel,
    GeodeticEquivalentResponse,
    GeodeticEquivalentsResponse,
    GeodeticGeometryResponse,
    GeodeticHousesResponse,
    GeodeticInputUncertaintyModel,
    GeodeticProvenanceResponse,
    GeodeticSensitivityResponse,
    GeodeticUncertaintyResponse,
)
from ..services.geodetic import (
    GeodeticChartResult,
    GeodeticEquivalentsResult,
    GeodeticHousesResult,
    GeodeticProvenance,
)
from .chart import serialize_houses


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


def serialize_geodetic_houses_result(result: GeodeticHousesResult) -> GeodeticHousesResponse:
    figure = result.house_chart
    return GeodeticHousesResponse(
        chart=serialize_geodetic_chart(figure.angles),
        targets=GeodeticAngleTargetsResponse(**figure.targets),
        houses=serialize_houses(figure.houses),
        source_frame=figure.source_frame,
        provenance=serialize_geodetic_provenance(result.provenance),
    )


def serialize_geodetic_geometry(witness: GeodeticGeometryWitness) -> GeodeticGeometryResponse:
    return GeodeticGeometryResponse(
        tropical_mc_deg=witness.tropical_mc_deg,
        armc_deg=witness.armc_deg,
        intersection_norm=witness.intersection_norm,
        meridian_altitude_sine=witness.meridian_altitude_sine,
        rising_rate=witness.rising_rate,
        asc_deg=witness.asc_deg,
        status=witness.status,
        policy=witness.policy,
        roundoff_guard=witness.roundoff_guard,
    )


def _serialize_uncertainty(value: GeodeticInputUncertainty) -> GeodeticInputUncertaintyModel:
    return GeodeticInputUncertaintyModel(
        longitude_deg=value.longitude_deg,
        latitude_deg=value.latitude_deg,
        obliquity_deg=value.obliquity_deg,
    )


def _serialize_derivatives(value: GeodeticAngleDerivatives) -> GeodeticAngleDerivativesResponse:
    return GeodeticAngleDerivativesResponse(
        geo_longitude_deg=value.geo_longitude_deg,
        geo_latitude_deg=value.geo_latitude_deg,
        obliquity_deg=value.obliquity_deg,
    )


def serialize_geodetic_sensitivity(result: GeodeticSensitivityResult) -> GeodeticSensitivityResponse:
    return GeodeticSensitivityResponse(
        chart=serialize_geodetic_chart(result.base_chart),
        uncertainty=_serialize_uncertainty(result.uncertainty),
        mc_derivatives=_serialize_derivatives(result.mc_derivatives),
        asc_derivatives=_serialize_derivatives(result.asc_derivatives),
        mc_linearized_radius_deg=result.mc_linearized_radius_deg,
        asc_linearized_radius_deg=result.asc_linearized_radius_deg,
        latitude_margin_to_pole_deg=result.latitude_margin_to_pole_deg,
        interpretation=result.interpretation,
    )


def serialize_geodetic_uncertainty(result: GeodeticNonlinearityResult) -> GeodeticUncertaintyResponse:
    arc = result.sampled_arc
    return GeodeticUncertaintyResponse(
        chart=serialize_geodetic_chart(result.base_chart),
        uncertainty=_serialize_uncertainty(result.uncertainty),
        policy=GeodeticDiagnosticPolicyModel(
            residual_tolerance_deg=result.policy.residual_tolerance_deg,
            max_evaluations=result.policy.max_evaluations,
            max_depth=result.policy.max_depth,
        ),
        base_geometry=serialize_geodetic_geometry(result.base_geometry),
        status=result.status,
        reasons=list(result.reasons),
        linear_estimate=(
            None if result.linear_estimate is None
            else serialize_geodetic_sensitivity(result.linear_estimate)
        ),
        sampled_max_deviation_deg=result.sampled_max_deviation_deg,
        sampled_max_residual_deg=result.sampled_max_residual_deg,
        sampled_arc=(
            None if arc is None
            else GeodeticCircularArcResponse(start_deg=arc.start_deg, sweep_deg=arc.sweep_deg)
        ),
        evaluations=result.evaluations,
        sampling_complete=result.sampling_complete,
        interpretation=result.interpretation,
        sampling_scheme=result.sampling_scheme,
    )


__all__ = [
    "serialize_geodetic_chart",
    "serialize_geodetic_chart_result",
    "serialize_geodetic_equivalent",
    "serialize_geodetic_equivalents_result",
    "serialize_geodetic_geometry",
    "serialize_geodetic_houses_result",
    "serialize_geodetic_provenance",
    "serialize_geodetic_sensitivity",
    "serialize_geodetic_uncertainty",
]
