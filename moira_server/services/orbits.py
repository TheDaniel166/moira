"""Service layer for admitted orbital-elements routes."""

from __future__ import annotations

from typing import Any

from moira import Moira
from moira.orbits import (
    ApsidalDirection,
    ApsidalPassageOutcome,
    ApsidalPassageStatus,
    ApsidalPassages,
    DistanceExtremes,
    OrbitalCenter,
    OrbitalFrame,
    OsculatingElements,
    OrbitalPassageUnavailableError,
    apsidal_passages,
    osculating_elements,
)

from ..models.orbits import (
    ApsidalPassageOutcomeResponse,
    ApsidalPassagesProvenanceResponse,
    ApsidalRouteScheduleEntryResponse,
    ApsidalSeamContinuityResponse,
    ApsidalSegmentUsageResponse,
    DistanceExtremesEnvelopeResponse,
    DistanceExtremesProvenanceResponse,
    DistanceExtremesRequest,
    DistanceExtremesResponse,
    DistanceExtremesTimeResponse,
    OrbitalElementsEnvelopeResponse,
    OrbitalElementsProvenanceResponse,
    OrbitalElementsRequest,
    OrbitalElementsResponse,
    OrbitalFrameConstructionResponse,
    OrbitalGravityResponse,
    OrbitalSingularityThresholdsResponse,
    OrbitalStateLegResponse,
    OrbitalStateSourceResponse,
    OrbitRequestEchoResponse,
    OrbitTimeConversionResponse,
    OrbitTimeResponse,
)


def _get_reader(engine: Moira) -> Any | None:
    try:
        return engine._reader
    except Exception:
        return None


def _reader_owner(reader: Any | None) -> str:
    return "Moira engine instance" if reader is not None else "module_default_reader"


def _serialize_elements(elements: OsculatingElements) -> OrbitalElementsResponse:
    return OrbitalElementsResponse(
        name=elements.body.name,
        epoch_jd=elements.epoch_tt,
        semi_major_axis_au=elements.semi_major_axis_au,
        eccentricity=elements.eccentricity,
        inclination_deg=elements.inclination_deg,
        lon_ascending_node_deg=elements.lon_ascending_node_deg,
        arg_perihelion_deg=elements.arg_pericenter_deg,
        mean_anomaly_deg=elements.mean_anomaly_deg,
        mean_motion_deg_per_day=elements.mean_motion_deg_per_day,
        orbital_period_days=elements.orbital_period_days,
        perihelion_distance_au=elements.pericenter_distance_au,
        aphelion_distance_au=elements.apocenter_distance_au,
    )


def _serialize_elements_time(elements: OsculatingElements) -> OrbitTimeResponse:
    conversion = elements.provenance.time_conversion
    return OrbitTimeResponse(
        jd_ut=elements.jd_ut,
        epoch_tt=elements.epoch_tt,
        epoch_tdb=elements.epoch_tdb,
        delta_t_seconds=elements.delta_t_seconds,
        tdb_minus_tt_seconds=elements.tdb_minus_tt_seconds,
        conversion=OrbitTimeConversionResponse(
            delta_t_policy=conversion.delta_t_policy,
            delta_t_source_product=conversion.delta_t_source_product,
            delta_t_retarget_mode=conversion.delta_t_retarget_mode,
            delta_t_correction_seconds=conversion.delta_t_correction_seconds,
            identity_iterations=conversion.identity_iterations,
            tt_tdb_policy=conversion.tt_tdb_policy,
            tt_tdb_version=conversion.tt_tdb_version,
            tt_tdb_source_url=conversion.tt_tdb_source_url,
            tt_tdb_source_sha256=conversion.tt_tdb_source_sha256,
            tt_tdb_source_bytes=conversion.tt_tdb_source_bytes,
            tt_tdb_iterations=conversion.tt_tdb_iterations,
        ),
    )


def _serialize_time_conversion(conversion) -> OrbitTimeConversionResponse:
    return OrbitTimeConversionResponse(
        delta_t_policy=conversion.delta_t_policy,
        delta_t_source_product=conversion.delta_t_source_product,
        delta_t_retarget_mode=conversion.delta_t_retarget_mode,
        delta_t_correction_seconds=conversion.delta_t_correction_seconds,
        identity_iterations=conversion.identity_iterations,
        tt_tdb_policy=conversion.tt_tdb_policy,
        tt_tdb_version=conversion.tt_tdb_version,
        tt_tdb_source_url=conversion.tt_tdb_source_url,
        tt_tdb_source_sha256=conversion.tt_tdb_source_sha256,
        tt_tdb_source_bytes=conversion.tt_tdb_source_bytes,
        tt_tdb_iterations=conversion.tt_tdb_iterations,
    )


def _serialize_state_leg(leg) -> OrbitalStateLegResponse:
    return OrbitalStateLegResponse(
        center_naif_id=leg.center_naif_id,
        target_naif_id=leg.target_naif_id,
        traversal_sign=leg.traversal_sign,
        segment_type=leg.segment_type,
        coverage_start_tdb=leg.coverage_start_tdb,
        coverage_end_tdb=leg.coverage_end_tdb,
        kernel_label=leg.kernel_label,
        kernel_sha256=leg.kernel_sha256,
        kernel_bytes=leg.kernel_bytes,
        pool_index=leg.pool_index,
        catalog_id=leg.catalog_id,
        catalog_version=leg.catalog_version,
        manifest_sha256=leg.manifest_sha256,
        released_utc=leg.released_utc,
        planetary_ephemeris=leg.planetary_ephemeris,
        coverage_restricted_to_observed_arc=(
            leg.coverage_restricted_to_observed_arc
        ),
    )


def _serialize_state_source(source) -> OrbitalStateSourceResponse:
    return OrbitalStateSourceResponse(
        legs=[_serialize_state_leg(leg) for leg in source.legs],
        covered_intervals_tdb=[
            [start, end] for start, end in source.covered_intervals_tdb
        ],
        pool_generation=source.pool_generation,
    )


def _serialize_gravity(gravity) -> OrbitalGravityResponse:
    return OrbitalGravityResponse(
        rule=gravity.rule,
        gm_km3_s2=gravity.gm_km3_s2,
        component_naif_ids=list(gravity.component_naif_ids),
        component_gm_km3_s2=list(gravity.component_gm_km3_s2),
        policy=gravity.policy,
        source_url=gravity.source_url,
        retrieved_date=gravity.retrieved_date,
        source_sha256=gravity.source_sha256,
        source_bytes=gravity.source_bytes,
        planetary_ephemeris=gravity.planetary_ephemeris,
    )


def _serialize_elements_provenance(
    elements: OsculatingElements,
    *,
    reader_owner: str,
) -> OrbitalElementsProvenanceResponse:
    provenance = elements.provenance
    gravity = provenance.gravity
    frame = provenance.frame_construction
    state_source = provenance.state_source
    thresholds = provenance.singularity_thresholds
    return OrbitalElementsProvenanceResponse(
        reader_owner=reader_owner,
        center=elements.center.value,
        frame=elements.frame.value,
        gravity=OrbitalGravityResponse(
            rule=gravity.rule,
            gm_km3_s2=gravity.gm_km3_s2,
            component_naif_ids=list(gravity.component_naif_ids),
            component_gm_km3_s2=list(gravity.component_gm_km3_s2),
            policy=gravity.policy,
            source_url=gravity.source_url,
            retrieved_date=gravity.retrieved_date,
            source_sha256=gravity.source_sha256,
            source_bytes=gravity.source_bytes,
            planetary_ephemeris=gravity.planetary_ephemeris,
        ),
        frame_construction=OrbitalFrameConstructionResponse(
            frame=frame.frame.value,
            routine=frame.routine,
            router_branch=frame.router_branch,
            precession_model=frame.precession_model,
            obliquity_model=frame.obliquity_model,
            nutation_model=frame.nutation_model,
            admitted_interval_tt=(
                None
                if provenance.frame_model_interval_tt is None
                else list(provenance.frame_model_interval_tt)
            ),
        ),
        state_source=OrbitalStateSourceResponse(
            legs=[
                OrbitalStateLegResponse(
                    center_naif_id=leg.center_naif_id,
                    target_naif_id=leg.target_naif_id,
                    traversal_sign=leg.traversal_sign,
                    segment_type=leg.segment_type,
                    coverage_start_tdb=leg.coverage_start_tdb,
                    coverage_end_tdb=leg.coverage_end_tdb,
                    kernel_label=leg.kernel_label,
                    kernel_sha256=leg.kernel_sha256,
                    kernel_bytes=leg.kernel_bytes,
                    pool_index=leg.pool_index,
                    catalog_id=leg.catalog_id,
                    catalog_version=leg.catalog_version,
                    manifest_sha256=leg.manifest_sha256,
                    released_utc=leg.released_utc,
                    planetary_ephemeris=leg.planetary_ephemeris,
                    coverage_restricted_to_observed_arc=(
                        leg.coverage_restricted_to_observed_arc
                    ),
                )
                for leg in state_source.legs
            ],
            covered_intervals_tdb=[
                [start, end] for start, end in state_source.covered_intervals_tdb
            ],
            pool_generation=state_source.pool_generation,
        ),
        singularity_thresholds=OrbitalSingularityThresholdsResponse(
            circular_e_tolerance=thresholds.circular_e_tolerance,
            equatorial_sin_i_tolerance=thresholds.equatorial_sin_i_tolerance,
            parabolic_e_tolerance=thresholds.parabolic_e_tolerance,
            rectilinear_normalized_h_tolerance=(
                thresholds.rectilinear_normalized_h_tolerance
            ),
            policy=thresholds.policy,
        ),
        stage_sequence=[
            "input_validation",
            "reader_binding",
            "ut1_tt_tdb_binding",
            "source_and_gravity_binding",
            "state_evaluation",
            "frame_rotation",
            "element_extraction",
            "transport_serialization",
        ],
    )


def _serialize_distance_extremes(extremes: DistanceExtremes) -> DistanceExtremesResponse:
    return DistanceExtremesResponse(
        name=extremes.name,
        perihelion_jd=extremes.perihelion_jd,
        perihelion_distance_au=extremes.perihelion_distance_au,
        aphelion_jd=extremes.aphelion_jd,
        aphelion_distance_au=extremes.aphelion_distance_au,
    )


def compute_orbital_elements(
    engine: Moira,
    request: OrbitalElementsRequest,
) -> OrbitalElementsEnvelopeResponse:
    reader = _get_reader(engine)
    elements = osculating_elements(
        request.body,
        request.jd_ut,
        center=OrbitalCenter.SUN,
        frame=OrbitalFrame.J2000_ECLIPTIC,
        reader=reader,
    )
    return OrbitalElementsEnvelopeResponse(
        request=OrbitRequestEchoResponse(body=request.body, jd_ut=request.jd_ut),
        time=_serialize_elements_time(elements),
        elements=_serialize_elements(elements),
        provenance=_serialize_elements_provenance(
            elements,
            reader_owner=_reader_owner(reader),
        ),
    )


def _serialize_passage_outcome(
    outcome: ApsidalPassageOutcome,
) -> ApsidalPassageOutcomeResponse:
    return ApsidalPassageOutcomeResponse(
        status=outcome.status.value,
        epoch_tdb=outcome.epoch_tdb,
        epoch_tt=outcome.epoch_tt,
        jd_ut=outcome.jd_ut,
        distance_au=outcome.distance_au,
        coverage_edge_tdb=outcome.coverage_edge_tdb,
        detail=outcome.detail,
    )


def _serialize_passage_provenance(
    passages: ApsidalPassages,
) -> ApsidalPassagesProvenanceResponse:
    receipt = passages.provenance
    return ApsidalPassagesProvenanceResponse(
        algorithm_version=receipt.algorithm_version,
        gravity=_serialize_gravity(receipt.gravity),
        time_conversion=_serialize_time_conversion(receipt.time_conversion),
        state_source=_serialize_state_source(receipt.state_source),
        initial_period_fraction=receipt.initial_period_fraction,
        radial_timescale_fraction=receipt.radial_timescale_fraction,
        minimum_step_days=receipt.minimum_step_days,
        maximum_step_days=receipt.maximum_step_days,
        witness_root_tolerance_factor=(
            receipt.witness_root_tolerance_factor
        ),
        witness_minimum_step_fraction=(
            receipt.witness_minimum_step_fraction
        ),
        witness_motion_timescale_fraction=(
            receipt.witness_motion_timescale_fraction
        ),
        witness_maximum_offset_days=receipt.witness_maximum_offset_days,
        refinement_tolerance_days=receipt.refinement_tolerance_days,
        maximum_root_iterations=receipt.maximum_root_iterations,
        evaluation_budget=receipt.evaluation_budget,
        extremum_semantics=receipt.extremum_semantics,
        search_window_source=receipt.search_window_source,
        route_plan_identity=receipt.route_plan_identity,
        route_schedule=[
            ApsidalRouteScheduleEntryResponse(
                start_tdb=entry.start_tdb,
                end_tdb=entry.end_tdb,
                route_identity=entry.route_identity,
                legs=[_serialize_state_leg(leg) for leg in entry.legs],
            )
            for entry in receipt.route_schedule
        ],
        segment_usage=[
            ApsidalSegmentUsageResponse(
                leg=_serialize_state_leg(usage.leg),
                evaluations=usage.evaluations,
            )
            for usage in receipt.segment_usage
        ],
        seam_continuity=[
            ApsidalSeamContinuityResponse(
                epoch_tdb=seam.epoch_tdb,
                left_route_identity=seam.left_route_identity,
                right_route_identity=seam.right_route_identity,
                position_residual_km=seam.position_residual_km,
                velocity_residual_km_per_day=(
                    seam.velocity_residual_km_per_day
                ),
                position_tolerance_km=seam.position_tolerance_km,
                velocity_tolerance_km_per_day=(
                    seam.velocity_tolerance_km_per_day
                ),
                admitted=seam.admitted,
                detail=seam.detail,
            )
            for seam in receipt.seam_continuity
        ],
        searched_interval_tdb=list(receipt.searched_interval_tdb),
        total_evaluations=receipt.total_evaluations,
    )


def compute_distance_extremes(
    engine: Moira,
    request: DistanceExtremesRequest,
) -> DistanceExtremesEnvelopeResponse:
    reader = _get_reader(engine)
    passages = apsidal_passages(
        request.body,
        request.jd_ut,
        center=OrbitalCenter.SUN,
        direction=ApsidalDirection.NEXT,
        reader=reader,
    )
    missing = tuple(
        kind
        for kind, outcome in (
            ("PERICENTER", passages.pericenter),
            ("APOCENTER", passages.apocenter),
        )
        if outcome.status is not ApsidalPassageStatus.FOUND
    )
    if missing:
        raise OrbitalPassageUnavailableError(passages, missing)
    assert passages.pericenter.epoch_tt is not None
    assert passages.pericenter.distance_au is not None
    assert passages.apocenter.epoch_tt is not None
    assert passages.apocenter.distance_au is not None
    extremes = DistanceExtremes(
        name=passages.body.name,
        perihelion_jd=passages.pericenter.epoch_tt,
        perihelion_distance_au=passages.pericenter.distance_au,
        aphelion_jd=passages.apocenter.epoch_tt,
        aphelion_distance_au=passages.apocenter.distance_au,
    )
    conversion = passages.provenance.time_conversion
    return DistanceExtremesEnvelopeResponse(
        request=OrbitRequestEchoResponse(body=request.body, jd_ut=request.jd_ut),
        time=DistanceExtremesTimeResponse(
            jd_ut=passages.jd_ut,
            epoch_tt=passages.start_epoch_tt,
            epoch_tdb=passages.start_epoch_tdb,
            delta_t_seconds=(passages.start_epoch_tt - passages.jd_ut) * 86400.0,
            tdb_minus_tt_seconds=(
                passages.start_epoch_tdb - passages.start_epoch_tt
            )
            * 86400.0,
            conversion=_serialize_time_conversion(conversion),
        ),
        distance_extremes=_serialize_distance_extremes(extremes),
        provenance=DistanceExtremesProvenanceResponse(
            reader_owner=_reader_owner(reader),
            pericenter=_serialize_passage_outcome(passages.pericenter),
            apocenter=_serialize_passage_outcome(passages.apocenter),
            search=_serialize_passage_provenance(passages),
            stage_sequence=[
                "input_validation",
                "reader_binding",
                "ut1_tt_tdb_binding",
                "frozen_route_plan",
                "radial_velocity_search",
                "two_sided_extremum_witness",
                "tdb_tt_ut1_event_inversion",
                "distance_extrema_serialization",
                "provenance_serialization",
            ],
        ),
    )
