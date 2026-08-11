"""Serializers for bounded relationship and locational forecasting receipts."""

from __future__ import annotations

from moira.astrocartography import FixedStarAstrocartographyResult
from moira.chart import ChartContext
from moira.locational_forecasting import (
    DynamicAstrocartographySeries,
    RelocatedReturnChart,
)
from moira.relationship_forecasting import (
    RelationshipChartIdentity,
    RelationshipChartTargetSet,
    RelationshipTransitEvent,
    RelationshipTransitSearchResult,
    RelationshipTransitTarget,
)

from ..models.forecasting import (
    AstrocartographyCurvePointShiftResponse,
    ChartContextResponse,
    DynamicAstrocartographyLineTransitionResponse,
    DynamicAstrocartographyPositionResponse,
    DynamicAstrocartographyResponse,
    DynamicAstrocartographySeriesTruthResponse,
    DynamicAstrocartographySnapshotResponse,
    DynamicAstrocartographySnapshotTruthResponse,
    FixedStarAstrocartographyResponse,
    FixedStarAstrocartographySubjectResponse,
    FixedStarAstrocartographyTruthResponse,
    RelocatedReturnResponse,
    RelationshipChartIdentityResponse,
    RelationshipChartTargetSetResponse,
    RelationshipTransitEventResponse,
    RelationshipTransitSearchResponse,
    RelationshipTransitSearchTruthResponse,
    RelationshipTransitTargetResponse,
    ReturnMomentTruthResponse,
    ReturnSearchPolicyTruthResponse,
    ReturnRelocationTruthResponse,
)
from .astrocartography import (
    serialize_astrocartography_line,
    serialize_subplanetary_point,
)
from .chart import serialize_houses, serialize_node
from .positions import serialize_planet
from .relationship import serialize_composite_truth, serialize_davison_truth
from .transits import serialize_transit_event


def serialize_relationship_chart_identity(
    identity: RelationshipChartIdentity,
) -> RelationshipChartIdentityResponse:
    construction_truth = identity.construction_truth
    serialized_construction = (
        serialize_composite_truth(construction_truth)
        if identity.chart_kind.value == "composite"
        else serialize_davison_truth(construction_truth)
    )
    return RelationshipChartIdentityResponse(
        chart_id=identity.chart_id,
        chart_kind=identity.chart_kind.value,
        method=identity.method,
        epoch_jd_ut=identity.epoch_jd_ut,
        includes_house_frame=identity.includes_house_frame,
        relation_basis=identity.relation_basis,
        geometry_sha256=identity.geometry_sha256,
        construction_truth=serialized_construction,
        reference_latitude=identity.reference_latitude,
        reference_longitude=identity.reference_longitude,
        correction_mode=identity.correction_mode,
        reference_frame=identity.reference_frame,
        timescale=identity.timescale,
    )


def serialize_relationship_transit_target(
    target: RelationshipTransitTarget,
) -> RelationshipTransitTargetResponse:
    return RelationshipTransitTargetResponse(
        chart_id=target.chart_id,
        name=target.name,
        target_kind=target.target_kind.value,
        longitude=target.longitude,
        source_path=target.source_path,
    )


def serialize_relationship_target_set(
    target_set: RelationshipChartTargetSet,
) -> RelationshipChartTargetSetResponse:
    return RelationshipChartTargetSetResponse(
        identity=serialize_relationship_chart_identity(target_set.identity),
        targets=[
            serialize_relationship_transit_target(target)
            for target in target_set.targets
        ],
        target_count=target_set.target_count,
    )


def serialize_relationship_transit_event(
    event: RelationshipTransitEvent,
) -> RelationshipTransitEventResponse:
    return RelationshipTransitEventResponse(
        chart_id=event.chart_id,
        target=serialize_relationship_transit_target(event.target),
        moving_body=event.moving_body,
        aspect_name=event.aspect_name,
        aspect_symbol=event.aspect_symbol,
        aspect_angle_deg=event.aspect_angle_deg,
        directional_offset_deg=event.directional_offset_deg,
        jd_exact=event.jd_exact,
        direction=event.direction,
        perfection_longitude=event.perfection_longitude,
        transit=serialize_transit_event(event.transit),
        event_source=event.event_source,
        orb_boundaries_computed=event.orb_boundaries_computed,
        interpretation=event.interpretation,
    )


def serialize_relationship_transit_search(
    result: RelationshipTransitSearchResult,
) -> RelationshipTransitSearchResponse:
    truth = result.computation_truth
    return RelationshipTransitSearchResponse(
        target_set=serialize_relationship_target_set(result.target_set),
        events=[serialize_relationship_transit_event(event) for event in result.events],
        computation_truth=RelationshipTransitSearchTruthResponse(
            chart_id=truth.chart_id,
            moving_bodies=list(truth.moving_bodies),
            target_names=list(truth.target_names),
            tier=truth.tier,
            aspect_names=list(truth.aspect_names),
            jd_start=truth.jd_start,
            jd_end=truth.jd_end,
            step_days=truth.step_days,
            policy_step_days_override=truth.policy_step_days_override,
            solver_tolerance_days=truth.solver_tolerance_days,
            step_policy=truth.step_policy,
            transit_policy_source=truth.transit_policy_source,
            direction=truth.direction,
            search_motion=truth.search_motion,
            search_call_count=truth.search_call_count,
            event_count=truth.event_count,
            event_source=truth.event_source,
            target_motion=truth.target_motion,
            event_kind=truth.event_kind,
            orb_window_policy=truth.orb_window_policy,
            interpretation=truth.interpretation,
        ),
        event_count=result.event_count,
    )


def serialize_fixed_star_astrocartography(
    result: FixedStarAstrocartographyResult,
) -> FixedStarAstrocartographyResponse:
    truth = result.computation_truth
    return FixedStarAstrocartographyResponse(
        subjects=[
            FixedStarAstrocartographySubjectResponse(
                requested_name=subject.requested_name,
                canonical_name=subject.canonical_name,
                nomenclature=subject.nomenclature,
                constellation=subject.constellation,
                source_kind=subject.source_kind,
                lookup_kind=subject.lookup_kind,
                hipparcos_name=subject.hipparcos_name,
                source_mode=subject.source_mode,
                gaia_match_status=subject.gaia_match_status,
                gaia_source_index=subject.gaia_source_index,
                merge_state=subject.merge_state,
                observer_mode=subject.observer_mode,
                relation_kind=subject.relation_kind,
                relation_basis=subject.relation_basis,
                true_position=subject.true_position,
                dedup_applied=subject.dedup_applied,
                is_topocentric=subject.is_topocentric,
                longitude=subject.longitude,
                latitude=subject.latitude,
                right_ascension=subject.right_ascension,
                declination=subject.declination,
                magnitude=subject.magnitude,
                position_source=subject.position_source,
            )
            for subject in result.subjects
        ],
        lines=[serialize_astrocartography_line(line) for line in result.lines],
        subplanetary_points=[
            serialize_subplanetary_point(point)
            for point in result.subplanetary_points
        ],
        computation_truth=FixedStarAstrocartographyTruthResponse(
            requested_names=list(truth.requested_names),
            canonical_names=list(truth.canonical_names),
            jd_ut=truth.jd_ut,
            jd_tt=truth.jd_tt,
            apparent_sidereal_time_deg=truth.apparent_sidereal_time_deg,
            true_obliquity_deg=truth.true_obliquity_deg,
            nutation_longitude_deg=truth.nutation_longitude_deg,
            lat_step=truth.lat_step,
            refraction=truth.refraction,
            coordinate_frame=truth.coordinate_frame,
            star_position_source=truth.star_position_source,
            equatorial_conversion_source=truth.equatorial_conversion_source,
            line_geometry_source=truth.line_geometry_source,
            point_geometry_source=truth.point_geometry_source,
            interpretation=truth.interpretation,
        ),
    )


def serialize_dynamic_astrocartography(
    result: DynamicAstrocartographySeries,
) -> DynamicAstrocartographyResponse:
    snapshots = []
    for snapshot in result.snapshots:
        truth = snapshot.computation_truth
        snapshots.append(
            DynamicAstrocartographySnapshotResponse(
                positions=[
                    DynamicAstrocartographyPositionResponse(
                        body=position.body,
                        right_ascension=position.right_ascension,
                        declination=position.declination,
                        position_source=position.position_source,
                    )
                    for position in snapshot.positions
                ],
                lines=[
                    serialize_astrocartography_line(line)
                    for line in snapshot.lines
                ],
                computation_truth=DynamicAstrocartographySnapshotTruthResponse(
                    jd_ut=truth.jd_ut,
                    jd_tt=truth.jd_tt,
                    bodies=list(truth.bodies),
                    observer_latitude=truth.observer_latitude,
                    observer_longitude=truth.observer_longitude,
                    observer_elevation_m=truth.observer_elevation_m,
                    apparent_sidereal_time_deg=truth.apparent_sidereal_time_deg,
                    true_obliquity_deg=truth.true_obliquity_deg,
                    nutation_longitude_deg=truth.nutation_longitude_deg,
                    lat_step=truth.lat_step,
                    refraction=truth.refraction,
                    mode=truth.mode.value,
                    coordinate_frame=truth.coordinate_frame,
                    timescale=truth.timescale,
                    line_geometry_source=truth.line_geometry_source,
                    interpretation=truth.interpretation,
                ),
                jd_ut=snapshot.jd_ut,
            )
        )

    transitions = [
        DynamicAstrocartographyLineTransitionResponse(
            body=transition.body,
            line_type=transition.line_type,
            source_jd_ut=transition.source_jd_ut,
            target_jd_ut=transition.target_jd_ut,
            source_meridian_longitude=transition.source_meridian_longitude,
            target_meridian_longitude=transition.target_meridian_longitude,
            meridian_signed_delta_deg=transition.meridian_signed_delta_deg,
            curve_point_shifts=[
                AstrocartographyCurvePointShiftResponse(
                    latitude=shift.latitude,
                    source_longitude=shift.source_longitude,
                    target_longitude=shift.target_longitude,
                    signed_delta_deg=shift.signed_delta_deg,
                )
                for shift in transition.curve_point_shifts
            ],
            source_only_latitudes=list(transition.source_only_latitudes),
            target_only_latitudes=list(transition.target_only_latitudes),
        )
        for transition in result.transitions
    ]
    truth = result.computation_truth
    return DynamicAstrocartographyResponse(
        snapshots=snapshots,
        transitions=transitions,
        computation_truth=DynamicAstrocartographySeriesTruthResponse(
            mode=truth.mode.value,
            epochs_jd_ut=list(truth.epochs_jd_ut),
            bodies=list(truth.bodies),
            snapshot_count=truth.snapshot_count,
            transition_count=truth.transition_count,
            epoch_policy=truth.epoch_policy,
            comparison_policy=truth.comparison_policy,
            progressed_mode=truth.progressed_mode,
            directed_mode=truth.directed_mode,
            interpretation=truth.interpretation,
        ),
    )


def serialize_chart_context(chart: ChartContext) -> ChartContextResponse:
    if chart.houses is None:
        raise ValueError("relocated return chart is missing its local house frame")
    return ChartContextResponse(
        jd_ut=chart.jd_ut,
        jd_tt=chart.jd_tt,
        latitude=chart.latitude,
        longitude=chart.longitude,
        planets={
            name: serialize_planet(planet)
            for name, planet in chart.planets.items()
        },
        nodes={name: serialize_node(node) for name, node in chart.nodes.items()},
        houses=serialize_houses(chart.houses),
        is_day=chart.is_day,
    )


def serialize_relocated_return(
    result: RelocatedReturnChart,
) -> RelocatedReturnResponse:
    moment = result.return_truth
    relocation = result.relocation_truth
    return RelocatedReturnResponse(
        source_chart=serialize_chart_context(result.source_chart),
        relocated_chart=serialize_chart_context(result.relocated_chart),
        return_truth=ReturnMomentTruthResponse(
            return_kind=moment.return_kind.value,
            body=moment.body,
            natal_longitude=moment.natal_longitude,
            jd_return_ut=moment.jd_return_ut,
            direction=moment.direction,
            timing_source=moment.timing_source,
            search_policy=ReturnSearchPolicyTruthResponse(
                step_days_override=moment.search_policy.step_days_override,
                default_max_days=moment.search_policy.default_max_days,
                per_body_max_days=list(moment.search_policy.per_body_max_days),
                solver_tolerance_days=moment.search_policy.solver_tolerance_days,
                policy_source=moment.search_policy.policy_source,
            ),
            year=moment.year,
            search_start_jd_ut=moment.search_start_jd_ut,
            reference_frame=moment.reference_frame,
            timescale=moment.timescale,
        ),
        relocation_truth=ReturnRelocationTruthResponse(
            source_latitude=relocation.source_latitude,
            source_longitude=relocation.source_longitude,
            relocated_latitude=relocation.relocated_latitude,
            relocated_longitude=relocation.relocated_longitude,
            source_requested_house_system=relocation.source_requested_house_system,
            source_effective_house_system=relocation.source_effective_house_system,
            source_house_fallback=relocation.source_house_fallback,
            relocated_requested_house_system=relocation.relocated_requested_house_system,
            relocated_effective_house_system=relocation.relocated_effective_house_system,
            relocated_house_fallback=relocation.relocated_house_fallback,
            same_epoch=relocation.same_epoch,
            same_celestial_snapshot=relocation.same_celestial_snapshot,
            chart_source=relocation.chart_source,
            relocation_source=relocation.relocation_source,
            interpretation=relocation.interpretation,
        ),
    )


__all__ = [
    "serialize_chart_context",
    "serialize_dynamic_astrocartography",
    "serialize_fixed_star_astrocartography",
    "serialize_relationship_chart_identity",
    "serialize_relationship_target_set",
    "serialize_relationship_transit_event",
    "serialize_relationship_transit_search",
    "serialize_relationship_transit_target",
    "serialize_relocated_return",
]
