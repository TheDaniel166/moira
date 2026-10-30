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
from moira.aspects import AspectPolicy
from moira.geodetic_analysis import (
    GeodeticHouseChart,
    GeodeticLocationComparison,
    GeodeticLocationDifference,
    GeodeticNatalOverlay,
)
from moira.geodetic_curves import GeodeticLociResult
from moira.geodetic_inputs import GeodeticBodySnapshot
from moira.geodetic_timing import GeodeticTimingResult
from moira.julian import utc_datetime_from_ut1

from ..models.geodetic import (
    GeodeticAngleDerivativesResponse,
    GeodeticAngleTargetsResponse,
    GeodeticAspectPolicyModel,
    GeodeticBodyFailureResponse,
    GeodeticBodyPositionResponse,
    GeodeticChartBackedHousesResponse,
    GeodeticCompareResponse,
    GeodeticContactKeyResponse,
    GeodeticCurveExclusionResponse,
    GeodeticCurvePolicyModel,
    GeodeticCurveVertexResponse,
    GeodeticEphemerisClockResponse,
    GeodeticEpochResponse,
    GeodeticIntervalResponse,
    GeodeticOrbWindowResponse,
    GeodeticTimingAspectModel,
    GeodeticTimingPolicyModel,
    GeodeticTimingReferenceResponse,
    GeodeticTimingResourceResponse,
    GeodeticTransitPassResponse,
    GeodeticTransitsResponse,
    GeodeticHouseChangeResponse,
    GeodeticHouseFigureResponse,
    GeodeticLociResponse,
    GeodeticLocusResponse,
    GeodeticNamedLongitudeResponse,
    GeodeticOverlayBodyResponse,
    GeodeticOverlayResponse,
    GeodeticPlaceDifferenceResponse,
    GeodeticPlaceModel,
    GeodeticPlaceResultResponse,
    GeodeticPlacementResponse,
    GeodeticSmallBodyIdentityResponse,
    GeodeticSnapshotResponse,
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
from .relationship import serialize_aspect


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


# -- P10-03b analysis products ------------------------------------------------


def serialize_geodetic_snapshot(snapshot: GeodeticBodySnapshot) -> GeodeticSnapshotResponse:
    return GeodeticSnapshotResponse(
        positions=[
            GeodeticBodyPositionResponse(
                body_id=p.body_id,
                requested_name=p.requested_name,
                display_name=p.display_name,
                tropical_longitude_deg=p.tropical_longitude_deg,
                selected_longitude_deg=p.selected_longitude_deg,
                identity=(
                    None if p.identity is None
                    else GeodeticSmallBodyIdentityResponse(
                        family=p.identity.family,
                        canonical_name=p.identity.canonical_name,
                        naif_id=p.identity.naif_id,
                        matched_name=p.identity.matched_name,
                        is_alias=p.identity.is_alias,
                    )
                ),
                ecliptic_latitude_deg=p.ecliptic_latitude_deg,
                speed_deg_per_day=p.speed_deg_per_day,
            )
            for p in snapshot.positions
        ],
        failures=[
            GeodeticBodyFailureResponse(
                requested_name=f.requested_name,
                body_id=f.body_id,
                failure_type=f.failure_type,
                reason=f.reason,
            )
            for f in snapshot.failures
        ],
        source_kind=snapshot.source_kind,
        source_frame=snapshot.source_frame,
        correction_regime=snapshot.correction_regime,
        zodiac=snapshot.zodiac,
        ayanamsa_deg=snapshot.ayanamsa_deg,
        ayanamsa_system=snapshot.ayanamsa_system,
        jd_ut1=snapshot.jd_ut1,
        jd_tt=snapshot.jd_tt,
        resource_receipt_status=snapshot.resource_receipt_status,
        complete=snapshot.complete,
    )


def serialize_geodetic_house_figure(figure: GeodeticHouseChart) -> GeodeticHouseFigureResponse:
    return GeodeticHouseFigureResponse(
        chart=serialize_geodetic_chart(figure.angles),
        targets=GeodeticAngleTargetsResponse(**figure.targets),
        houses=serialize_houses(figure.houses),
        source_frame=figure.source_frame,
        jd_ut1=figure.jd_ut1,
        jd_tt=figure.jd_tt,
        ayanamsa_system=figure.ayanamsa_system,
    )


def serialize_geodetic_chart_houses(figure: GeodeticHouseChart) -> GeodeticChartBackedHousesResponse:
    return GeodeticChartBackedHousesResponse(figure=serialize_geodetic_house_figure(figure))


def _serialize_aspect_policy(policy: AspectPolicy) -> GeodeticAspectPolicyModel:
    return GeodeticAspectPolicyModel(
        tier=policy.tier,
        orb_factor=policy.orb_factor,
        optional_sets=list(policy.optional_sets),
    )


def serialize_geodetic_overlay_body(overlay: GeodeticNatalOverlay) -> GeodeticOverlayBodyResponse:
    return GeodeticOverlayBodyResponse(
        figure=serialize_geodetic_house_figure(overlay.house_chart),
        placements=[
            GeodeticPlacementResponse(
                body_id=placement.body_id,
                house=placement.placement.house,
                longitude=placement.placement.longitude,
                exact_on_cusp=placement.placement.exact_on_cusp,
                cusp_longitude=placement.placement.cusp_longitude,
            )
            for placement in overlay.placements
        ],
        contacts=[serialize_aspect(contact) for contact in overlay.contacts],
        aspect_policy=_serialize_aspect_policy(overlay.aspect_policy),
        target_longitudes=[
            GeodeticNamedLongitudeResponse(name=name, longitude=longitude)
            for name, longitude in overlay.target_longitudes
        ],
        coincident_targets=[list(pair) for pair in overlay.coincident_targets],
        placement_semantics=overlay.placement_semantics,
        complete=overlay.complete,
    )


def serialize_geodetic_overlay(overlay: GeodeticNatalOverlay) -> GeodeticOverlayResponse:
    return GeodeticOverlayResponse(
        snapshot=serialize_geodetic_snapshot(overlay.snapshot),
        overlay=serialize_geodetic_overlay_body(overlay),
    )


def _serialize_difference(difference: GeodeticLocationDifference) -> GeodeticPlaceDifferenceResponse:
    return GeodeticPlaceDifferenceResponse(
        baseline_id=difference.baseline_id,
        angle_deltas_deg=[
            GeodeticNamedLongitudeResponse(name=name, longitude=delta)
            for name, delta in difference.angle_deltas_deg
        ],
        house_changes=[
            GeodeticHouseChangeResponse(body_id=body, baseline_house=before, house=after)
            for body, before, after in difference.house_changes
        ],
        added_contacts=[
            GeodeticContactKeyResponse(body=body, target=target, aspect_angle_deg=angle)
            for body, target, angle in difference.added_contacts
        ],
        removed_contacts=[
            GeodeticContactKeyResponse(body=body, target=target, aspect_angle_deg=angle)
            for body, target, angle in difference.removed_contacts
        ],
    )


def serialize_geodetic_compare(comparison: GeodeticLocationComparison) -> GeodeticCompareResponse:
    return GeodeticCompareResponse(
        snapshot=serialize_geodetic_snapshot(comparison.snapshot),
        results=[
            GeodeticPlaceResultResponse(
                place=GeodeticPlaceModel(
                    location_id=result.place.location_id,
                    geo_latitude=result.place.location.latitude_deg,
                    geo_longitude=result.place.location.longitude_deg,
                    display_name=result.place.display_name,
                ),
                overlay=None if result.overlay is None else serialize_geodetic_overlay_body(result.overlay),
                difference=None if result.difference is None else _serialize_difference(result.difference),
                failure_type=result.failure_type,
                reason=result.reason,
            )
            for result in comparison.results
        ],
        order_by=comparison.order_by,
        baseline_id=comparison.baseline_id,
        complete=comparison.complete,
    )


def serialize_geodetic_loci(result: GeodeticLociResult) -> GeodeticLociResponse:
    return GeodeticLociResponse(
        snapshot=serialize_geodetic_snapshot(result.snapshot),
        obliquity_deg=result.obliquity_deg,
        curve_policy=GeodeticCurvePolicyModel(
            latitude_step_deg=result.policy.latitude_step_deg,
            max_evaluations=result.policy.max_evaluations,
            round_trip_tolerance_deg=result.policy.round_trip_tolerance_deg,
        ),
        loci=[
            GeodeticLocusResponse(
                body_id=locus.body_id,
                angle=locus.angle,
                tropical_target_deg=locus.tropical_target_deg,
                selected_target_deg=locus.selected_target_deg,
                right_ascension_deg=locus.right_ascension_deg,
                declination_deg=locus.declination_deg,
                segments=[
                    [
                        GeodeticCurveVertexResponse(
                            latitude_deg=v.latitude_deg,
                            longitude_deg=v.longitude_deg,
                            residual_deg=v.residual_deg,
                            rising_rate=v.rising_rate,
                            boundary=v.boundary,
                        )
                        for v in segment
                    ]
                    for segment in locus.segments
                ],
                exclusions=[
                    GeodeticCurveExclusionResponse(latitude_deg=e.latitude_deg, reason=e.reason)
                    for e in locus.exclusions
                ],
                analytic_definition=locus.analytic_definition,
                complete=locus.complete,
            )
            for locus in result.loci
        ],
        evaluations=result.evaluations,
        complete=result.complete,
        semantics=result.semantics,
        interpolation=result.interpolation,
    )

# -- P10-03c timing ------------------------------------------------------------


def _epoch(jd_ut1: float) -> GeodeticEpochResponse:
    # JD UT1 is authoritative; datetime_utc renders the same epoch in UTC.
    return GeodeticEpochResponse(jd_ut1=jd_ut1, datetime_utc=utc_datetime_from_ut1(jd_ut1).isoformat())


def _interval(interval) -> GeodeticIntervalResponse:
    start, end = interval
    return GeodeticIntervalResponse(start=_epoch(start), end=_epoch(end))


def _serialize_clock(clock) -> GeodeticEphemerisClockResponse:
    identity = getattr(clock, "identity", None)
    raw_delta_t = getattr(clock, "raw_delta_t", None)
    return GeodeticEphemerisClockResponse(
        jd_ut1=clock.jd_ut1,
        epoch_tt=clock.epoch_tt,
        epoch_tdb=clock.epoch_tdb,
        delta_t_seconds=clock.delta_t_seconds,
        delta_t_correction_seconds=clock.delta_t_correction_seconds,
        tdb_minus_tt_seconds=clock.tdb_minus_tt_seconds,
        ephemeris_summary_label=getattr(identity, "summary_label", None),
        planetary_ephemeris=getattr(identity, "planetary_ephemeris", None),
        lunar_ephemeris=getattr(identity, "lunar_ephemeris", None),
        delta_t_source_product=getattr(raw_delta_t, "source_product", None),
    )


def _serialize_identity(identity) -> GeodeticSmallBodyIdentityResponse | None:
    if identity is None:
        return None
    return GeodeticSmallBodyIdentityResponse(
        family=identity.family,
        canonical_name=identity.canonical_name,
        naif_id=identity.naif_id,
        matched_name=identity.matched_name,
        is_alias=identity.is_alias,
    )


def serialize_geodetic_transits(
    result: GeodeticTimingResult,
    aspects: list[GeodeticTimingAspectModel],
) -> GeodeticTransitsResponse:
    reference = result.reference
    policy = result.policy
    return GeodeticTransitsResponse(
        reference=GeodeticTimingReferenceResponse(
            chart=serialize_geodetic_chart(reference.chart),
            selected_targets=[
                GeodeticNamedLongitudeResponse(name=name, longitude=longitude)
                for name, longitude in reference.selected_targets
            ],
            tropical_targets=[
                GeodeticNamedLongitudeResponse(name=name, longitude=longitude)
                for name, longitude in reference.tropical_targets
            ],
            reference_jd_ut1=reference.reference_jd_ut1,
            reference_jd_tt=reference.reference_jd_tt,
            angles=list(reference.angles),
            target_policy=reference.target_policy,
            source_frame=reference.source_frame,
        ),
        requested_mover=result.requested_mover,
        body_id=result.body_id,
        identity=_serialize_identity(result.identity),
        policy=GeodeticTimingPolicyModel(
            step_days=policy.step_days,
            max_evaluations=policy.max_evaluations,
            max_subdivisions=policy.max_subdivisions,
            max_depth=policy.max_depth,
            maximum_light_time_days=policy.maximum_light_time_days,
            coverage_policy=policy.coverage_policy,
        ),
        aspects=list(aspects),
        requested_interval=_interval(result.requested_interval_jd_ut1),
        covered_intervals=[_interval(i) for i in result.covered_intervals_jd_ut1],
        gaps=[_interval(i) for i in result.gaps_jd_ut1],
        scanned_intervals=[_interval(i) for i in result.scanned_intervals_jd_ut1],
        resources=[
            GeodeticTimingResourceResponse(
                center=r.center,
                target=r.target,
                source_label=r.source_label,
                source_sha256=r.source_sha256,
                catalog_id=r.catalog_id,
                catalog_version=r.catalog_version,
                manifest_sha256=r.manifest_sha256,
                intervals_tdb=[list(i) for i in r.intervals_tdb],
                segment_boundaries_tdb=list(r.segment_boundaries_tdb),
            )
            for r in result.resources
        ],
        events=[
            GeodeticTransitPassResponse(
                body_id=e.body_id,
                target=e.target,
                aspect_angle_deg=e.aspect_angle_deg,
                directed_angle_deg=e.directed_angle_deg,
                epoch=_epoch(e.jd_ut1),
                motion=e.motion,
                residual_deg=e.residual_deg,
                window_index=e.window_index,
            )
            for e in result.events
        ],
        windows=[
            GeodeticOrbWindowResponse(
                body_id=w.body_id,
                target=w.target,
                aspect_angle_deg=w.aspect_angle_deg,
                orb_deg=w.orb_deg,
                covered=_interval((w.covered_start_jd_ut1, w.covered_end_jd_ut1)),
                entry=None if w.entry_jd_ut1 is None else _epoch(w.entry_jd_ut1),
                exit=None if w.exit_jd_ut1 is None else _epoch(w.exit_jd_ut1),
                entry_status=w.entry_status,
                exit_status=w.exit_status,
                pass_indices=list(w.pass_indices),
            )
            for w in result.windows
        ],
        evaluations=result.evaluations,
        subdivisions=result.subdivisions,
        complete=result.complete,
        status=result.status,
        reasons=list(result.reasons),
        ephemeris_clock=_serialize_clock(result.ephemeris_clock),
        timescale=result.timescale,
        longitude_frame=result.longitude_frame,
        correction_regime=result.correction_regime,
        completeness=result.completeness,
        resource_semantics=result.resource_semantics,
    )

__all__ = [
    "serialize_geodetic_transits",
    "serialize_geodetic_chart_houses",
    "serialize_geodetic_compare",
    "serialize_geodetic_house_figure",
    "serialize_geodetic_loci",
    "serialize_geodetic_overlay",
    "serialize_geodetic_overlay_body",
    "serialize_geodetic_snapshot",
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
