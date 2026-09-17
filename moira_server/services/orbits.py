"""Service layer for admitted orbital-elements routes."""

from __future__ import annotations

import math
from typing import Any

from moira import Moira
from moira.constants import Body
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
    OrbitClassBoundaryMargin,
    OrbitClassResult,
    apsidal_passages,
    orbit_class,
    orbit_classes_at,
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
    OrbitClassBatchEchoResponse,
    OrbitClassBatchEnvelopeResponse,
    OrbitClassBatchItemErrorResponse,
    OrbitClassBatchProvenanceResponse,
    OrbitClassBatchRequest,
    OrbitClassEnvelopeResponse,
    OrbitClassPredicateMarginResponse,
    OrbitClassProvenanceResponse,
    OrbitClassRequest,
    OrbitClassResponse,
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


_ORBIT_CLASS_DESCRIPTIONS: dict[str, str] = {
    "IEO": "Atira-class asteroid with orbit strictly interior to Earth's orbit (a < 1.0 AU, Q < 0.983 AU).",
    "ATE": "Aten-class near-Earth asteroid with semi-major axis less than 1.0 AU and aphelion distance greater than 0.983 AU (a < 1.0 AU, Q > 0.983 AU).",
    "APO": "Apollo-class near-Earth asteroid with semi-major axis greater than 1.0 AU and perihelion distance less than 1.017 AU (a > 1.0 AU, q < 1.017 AU).",
    "AMO": "Amor-class near-Earth asteroid with perihelion distance between 1.017 AU and 1.3 AU (1.017 AU < q < 1.3 AU).",
    "MCA": "Mars-crossing asteroid with perihelion distance between 1.3 AU and 1.666 AU, crossing or approaching Mars's orbit (1.3 AU < q < 1.666 AU).",
    "IMB": "Inner Main-belt asteroid with semi-major axis less than 2.0 AU and perihelion distance greater than 1.666 AU (a < 2.0 AU, q > 1.666 AU).",
    "MBA": "Main-belt asteroid located between Mars and Jupiter with semi-major axis between 2.0 AU and 3.2 AU and perihelion distance greater than 1.666 AU (2.0 AU < a < 3.2 AU, q > 1.666 AU).",
    "OMB": "Outer Main-belt asteroid with semi-major axis between 3.2 AU and 4.6 AU and perihelion distance greater than 1.666 AU (3.2 AU < a < 4.6 AU, q > 1.666 AU).",
    "TJN": "Jupiter Trojan asteroid co-orbiting near Jupiter's L4 or L5 Lagrange points with semi-major axis between 4.6 AU and 5.5 AU and eccentricity less than 0.3 (4.6 AU < a < 5.5 AU, e < 0.3).",
    "CEN": "Centaur small body orbiting in the giant planet region between Jupiter and Neptune with semi-major axis between 5.5 AU and 30.1 AU (5.5 AU < a < 30.1 AU).",
    "TNO": "TransNeptunian Object with semi-major axis beyond the orbit of Neptune (a > 30.1 AU).",
    "PAA": "Parabolic asteroid on an unbound or nominally parabolic trajectory with eccentricity approximately 1.0 (e ≈ 1.0).",
    "HYA": "Hyperbolic asteroid on an unbound hyperbolic trajectory with eccentricity strictly greater than 1.0 (e > 1.0).",
    "AST": "Asteroid orbit not classified into a more specific orbital category.",
}


def _is_condition_satisfied(op: str, val: float, bnd: float) -> bool:
    if op == "<":
        return val < bnd
    if op == "<=":
        return val <= bnd
    if op == ">":
        return val > bnd
    if op == ">=":
        return val >= bnd
    if op == "==":
        return math.isclose(val, bnd)
    return False


def _serialize_orbit_class_margin(
    margin: OrbitClassBoundaryMargin,
) -> OrbitClassPredicateMarginResponse:
    satisfied = _is_condition_satisfied(margin.operator, margin.value, margin.boundary)
    return OrbitClassPredicateMarginResponse(
        parameter=margin.parameter,
        operator=margin.operator,
        boundary=margin.boundary,
        value=margin.value,
        margin=margin.signed_difference,
        satisfied=satisfied,
        unit=margin.unit,
    )


def _serialize_orbit_class(result: OrbitClassResult) -> OrbitClassResponse:
    code_str = result.code.value
    desc = _ORBIT_CLASS_DESCRIPTIONS.get(code_str, result.title)
    is_nea = code_str in {"IEO", "ATE", "APO", "AMO"}
    is_pha_candidate = code_str in {"ATE", "APO"}
    predicates = [_serialize_orbit_class_margin(m) for m in result.boundary_margins]
    condition_parts = [
        f"{m.parameter} {m.operator} {m.boundary} {m.unit}".strip()
        for m in result.boundary_margins
    ]
    summary = ", ".join(condition_parts) if condition_parts else "unconditional"
    return OrbitClassResponse(
        name=result.body.name,
        code=code_str,
        title=result.title,
        description=desc,
        is_near_earth_asteroid=is_nea,
        is_potentially_hazardous_candidate=is_pha_candidate,
        condition_summary=summary,
        predicates=predicates,
    )


def _serialize_orbit_class_provenance(
    elements: OsculatingElements,
    *,
    reader_owner: str,
) -> OrbitClassProvenanceResponse:
    provenance = elements.provenance
    return OrbitClassProvenanceResponse(
        reader_owner=reader_owner,
        center=elements.center.value,
        frame=elements.frame.value,
        classification_policy="jpl_sbdb_osculating_v1",
        gravity=_serialize_gravity(provenance.gravity),
        state_source=_serialize_state_source(provenance.state_source),
        stage_sequence=[
            "input_validation",
            "reader_binding",
            "ut1_tt_tdb_binding",
            "state_evaluation",
            "osculating_conic_extraction",
            "sbdb_predicate_evaluation",
            "transport_serialization",
        ],
    )


def _serialize_orbit_class_batch_provenance(
    *,
    reader_owner: str,
) -> OrbitClassBatchProvenanceResponse:
    return OrbitClassBatchProvenanceResponse(
        reader_owner=reader_owner,
        center="SUN",
        frame="J2000_ECLIPTIC",
        classification_policy="jpl_sbdb_osculating_v1",
        stage_sequence=[
            "input_validation",
            "reader_binding",
            "ut1_tt_tdb_binding",
            "batch_orbit_classification",
            "error_isolation",
            "transport_serialization",
        ],
    )


def compute_orbit_class(
    engine: Moira,
    request: OrbitClassRequest,
) -> OrbitClassEnvelopeResponse:
    reader = _get_reader(engine)
    result = orbit_class(
        request.body,
        request.jd_ut,
        reader=reader,
    )
    elements = result.elements
    return OrbitClassEnvelopeResponse(
        request=OrbitRequestEchoResponse(body=request.body, jd_ut=request.jd_ut),
        time=_serialize_elements_time(elements),
        orbit_class=_serialize_orbit_class(result),
        provenance=_serialize_orbit_class_provenance(
            elements,
            reader_owner=_reader_owner(reader),
        ),
    )


def compute_orbit_class_batch(
    engine: Moira,
    request: OrbitClassBatchRequest,
) -> OrbitClassBatchEnvelopeResponse:
    reader = _get_reader(engine)
    batch = orbit_classes_at(
        request.bodies,
        request.jd_ut,
        reader=reader,
    )
    results: dict[str, OrbitClassResponse] = {}
    errors: dict[str, OrbitClassBatchItemErrorResponse] = {}

    first_elements: OsculatingElements | None = None
    for item in batch.items:
        key = str(item.input_body)
        if item.result is not None:
            results[key] = _serialize_orbit_class(item.result)
            if first_elements is None:
                first_elements = item.result.elements
        elif item.error is not None:
            errors[key] = OrbitClassBatchItemErrorResponse(
                error_code=item.error.error_code,
                message=item.error.message,
                category="orbital_classification_failure",
            )

    if first_elements is not None:
        time_block = _serialize_elements_time(first_elements)
    else:
        ref_elements = osculating_elements(
            Body.EARTH,
            request.jd_ut,
            center=OrbitalCenter.SUN,
            frame=OrbitalFrame.J2000_ECLIPTIC,
            reader=reader,
        )
        time_block = _serialize_elements_time(ref_elements)

    return OrbitClassBatchEnvelopeResponse(
        request=OrbitClassBatchEchoResponse(
            bodies_count=len(request.bodies),
            jd_ut=request.jd_ut,
        ),
        time=time_block,
        results=results,
        errors=errors,
        total_requested=len(request.bodies),
        total_succeeded=len(results),
        total_failed=len(errors),
        provenance=_serialize_orbit_class_batch_provenance(
            reader_owner=_reader_owner(reader),
        ),
    )

