"""Serializers for phase-8 progression vessels (P8-01–P8-05)."""

from __future__ import annotations

from moira.progressions import (
    ProgressedChart,
    ProgressedDeclinationChart,
    ProgressedHouseFrame,
    ProgressionChartConditionProfile,
    ProgressionConditionNetworkProfile,
    ProgressionConditionProfile,
    ProgressionRelation,
)

from ..models.progressions import (
    DailyHousesResponse,
    ProgressedChartResponse,
    ProgressedChartReductionResponse,
    ProgressedChartReductionTruthResponse,
    ProgressedDeclinationChartResponse,
    ProgressedDeclinationChartReductionResponse,
    ProgressedDeclinationPositionResponse,
    ProgressedHouseFrameArcReductionResponse,
    ProgressedHouseFrameArcReductionTruthResponse,
    ProgressedHouseFrameResponse,
    ProgressedHouseFrameReductionResponse,
    ProgressedHouseFrameReductionTruthResponse,
    ProgressedPositionResponse,
    ProgressionAggregateReductionTruthResponse,
    ProgressionChartConditionProfileResponse,
    ProgressionChartConditionProfileReductionResponse,
    ProgressionConditionNetworkProfileReductionResponse,
    ProgressionConditionNetworkProfileResponse,
    ProgressionConditionProfileResponse,
    ProgressionComputationClassificationResponse,
    ProgressionComputationTruthResponse,
    ProgressionDoctrineClassificationResponse,
    ProgressionDoctrineTruthResponse,
    ProgressionNetworkEdgeResponse,
    ProgressionNetworkNodeResponse,
    ProgressionRelationResponse,
)
from ..services.progressions import (
    HouseFrameArcReductionContext,
    HouseFrameReductionContext,
    ProgressionAggregateReductionContext,
    ProgressionReductionContext,
)


def _serialize_relation(relation: ProgressionRelation) -> ProgressionRelationResponse:
    return ProgressionRelationResponse(
        technique_name=relation.technique_name,
        relation_kind=relation.relation_kind,
        basis=relation.basis,
        reference_name=relation.reference_name,
        converse=relation.converse,
        coordinate_system=relation.coordinate_system,
    )


def _serialize_condition_profile(profile: ProgressionConditionProfile) -> ProgressionConditionProfileResponse:
    return ProgressionConditionProfileResponse(
        technique_name=profile.technique_name,
        doctrine_family=profile.doctrine_family,
        relation_kind=profile.relation_kind,
        relation_basis=profile.relation_basis,
        coordinate_system=profile.coordinate_system,
        rate_mode=profile.rate_mode,
        application_mode=profile.application_mode,
        converse=profile.converse,
        uses_directed_arc=profile.uses_directed_arc,
        uses_reference_body=profile.uses_reference_body,
        uses_stepped_key=profile.uses_stepped_key,
        uses_house_frame=profile.uses_house_frame,
        structural_state=profile.structural_state,
    )


def serialize_progressed_chart(chart: ProgressedChart) -> ProgressedChartResponse:
    positions = {
        name: ProgressedPositionResponse(
            name=pos.name,
            longitude=pos.longitude,
            speed=pos.speed,
            retrograde=pos.retrograde,
            sign=pos.sign,
            sign_symbol=pos.sign_symbol,
            sign_degree=pos.sign_degree,
        )
        for name, pos in chart.positions.items()
    }
    return ProgressedChartResponse(
        chart_type=chart.chart_type,
        natal_jd_ut=chart.natal_jd_ut,
        progressed_jd_ut=chart.progressed_jd_ut,
        target_date=chart.target_date.isoformat(),
        solar_arc_deg=chart.solar_arc_deg,
        positions=positions,
        doctrine_family=chart.doctrine_family,
        coordinate_system=chart.coordinate_system,
        is_converse=chart.is_converse,
        condition_state=chart.condition_state,
        relation=_serialize_relation(chart.relation) if chart.relation is not None else None,
        condition_profile=(
            _serialize_condition_profile(chart.condition_profile)
            if chart.condition_profile is not None
            else None
        ),
    )


def serialize_progressed_declination_chart(chart: ProgressedDeclinationChart) -> ProgressedDeclinationChartResponse:
    positions = {
        name: ProgressedDeclinationPositionResponse(name=pos.name, declination=pos.declination)
        for name, pos in chart.positions.items()
    }
    return ProgressedDeclinationChartResponse(
        chart_type=chart.chart_type,
        natal_jd_ut=chart.natal_jd_ut,
        progressed_jd_ut=chart.progressed_jd_ut,
        target_date=chart.target_date.isoformat(),
        positions=positions,
        doctrine_family=chart.doctrine_family,
        coordinate_system=chart.coordinate_system,
        is_converse=chart.is_converse,
        condition_state=chart.condition_profile.structural_state,
        relation=_serialize_relation(chart.relation),
        condition_profile=_serialize_condition_profile(chart.condition_profile),
    )


def _serialize_doctrine_truth(truth) -> ProgressionDoctrineTruthResponse:
    return ProgressionDoctrineTruthResponse(
        technique_name=truth.technique_name,
        doctrine_family=truth.doctrine_family,
        life_unit=truth.life_unit,
        ephemeris_unit=truth.ephemeris_unit,
        rate_mode=truth.rate_mode,
        application_mode=truth.application_mode,
        coordinate_system=truth.coordinate_system,
        converse=truth.converse,
    )


def _serialize_computation_truth(truth) -> ProgressionComputationTruthResponse:
    return ProgressionComputationTruthResponse(
        doctrine=_serialize_doctrine_truth(truth.doctrine),
        target_jd_ut=truth.target_jd_ut,
        age_years=truth.age_years,
        progressed_jd_ut=truth.progressed_jd_ut,
        directed_arc_deg=truth.directed_arc_deg,
        reference_body=truth.reference_body,
        reference_start_value=truth.reference_start_value,
        reference_end_value=truth.reference_end_value,
        stepped_years=truth.stepped_years,
        latitude=truth.latitude,
        longitude=truth.longitude,
        house_system=truth.house_system,
    )


def _serialize_doctrine_classification(classification) -> ProgressionDoctrineClassificationResponse:
    return ProgressionDoctrineClassificationResponse(
        technique_name=classification.technique_name,
        doctrine_family=classification.doctrine_family,
        rate_mode=classification.rate_mode,
        application_mode=classification.application_mode,
        coordinate_system=classification.coordinate_system,
        converse=classification.converse,
    )


def _serialize_computation_classification(classification) -> ProgressionComputationClassificationResponse:
    return ProgressionComputationClassificationResponse(
        doctrine=_serialize_doctrine_classification(classification.doctrine),
        uses_directed_arc=classification.uses_directed_arc,
        uses_reference_body=classification.uses_reference_body,
        uses_stepped_key=classification.uses_stepped_key,
        uses_house_frame=classification.uses_house_frame,
    )


def _serialize_progression_reduction_truth(
    reduction: ProgressionReductionContext,
    *,
    engine_surface: str,
) -> ProgressedChartReductionTruthResponse:
    return ProgressedChartReductionTruthResponse(
        engine_surface=engine_surface,
        requested_natal_datetime=reduction.requested_natal_datetime,
        requested_target_datetime=reduction.requested_target_datetime,
        requested_bodies=reduction.requested_bodies,
        computation_truth=_serialize_computation_truth(reduction.computation_truth),
        classification=(
            _serialize_computation_classification(reduction.classification)
            if reduction.classification is not None
            else None
        ),
        stage_sequence=reduction.stage_sequence,
    )


def serialize_progressed_chart_with_reduction(
    chart: ProgressedChart,
    reduction: ProgressionReductionContext,
) -> ProgressedChartReductionResponse:
    return ProgressedChartReductionResponse(
        result=serialize_progressed_chart(chart),
        reduction=_serialize_progression_reduction_truth(
            reduction,
            engine_surface=chart.chart_type,
        ),
    )


def serialize_progressed_house_frame_arc_with_reduction(
    chart: ProgressedChart,
    reduction: HouseFrameArcReductionContext,
) -> ProgressedHouseFrameArcReductionResponse:
    return ProgressedHouseFrameArcReductionResponse(
        result=serialize_progressed_chart(chart),
        reduction=ProgressedHouseFrameArcReductionTruthResponse(
            engine_surface=chart.chart_type,
            requested_natal_datetime=reduction.requested_natal_datetime,
            requested_target_datetime=reduction.requested_target_datetime,
            requested_latitude=reduction.requested_latitude,
            requested_longitude=reduction.requested_longitude,
            requested_house_system=reduction.requested_house_system,
            requested_method=reduction.requested_method,
            requested_converse=reduction.requested_converse,
            requested_bodies=reduction.requested_bodies,
            computation_truth=_serialize_computation_truth(reduction.computation_truth),
            classification=(
                _serialize_computation_classification(reduction.classification)
                if reduction.classification is not None
                else None
            ),
            stage_sequence=reduction.stage_sequence,
        ),
    )


def serialize_progressed_declination_chart_with_reduction(
    chart: ProgressedDeclinationChart,
    reduction: ProgressionReductionContext,
) -> ProgressedDeclinationChartReductionResponse:
    return ProgressedDeclinationChartReductionResponse(
        result=serialize_progressed_declination_chart(chart),
        reduction=_serialize_progression_reduction_truth(
            reduction,
            engine_surface=chart.chart_type,
        ),
    )


def serialize_progressed_house_frame_with_reduction(
    frame: ProgressedHouseFrame,
    reduction: HouseFrameReductionContext,
) -> ProgressedHouseFrameReductionResponse:
    return ProgressedHouseFrameReductionResponse(
        result=serialize_progressed_house_frame(frame),
        reduction=ProgressedHouseFrameReductionTruthResponse(
            engine_surface=frame.chart_type,
            requested_natal_datetime=reduction.requested_natal_datetime,
            requested_target_datetime=reduction.requested_target_datetime,
            requested_latitude=reduction.requested_latitude,
            requested_longitude=reduction.requested_longitude,
            requested_house_system=reduction.requested_house_system,
            requested_bodies=reduction.requested_bodies,
            computation_truth=_serialize_computation_truth(reduction.computation_truth),
            classification=(
                _serialize_computation_classification(reduction.classification)
                if reduction.classification is not None
                else None
            ),
            stage_sequence=reduction.stage_sequence,
        ),
    )


def _serialize_progression_aggregate_reduction_truth(
    reduction: ProgressionAggregateReductionContext,
    *,
    engine_surface: str,
) -> ProgressionAggregateReductionTruthResponse:
    return ProgressionAggregateReductionTruthResponse(
        engine_surface=engine_surface,
        chart_item_count=reduction.chart_item_count,
        house_frame_item_count=reduction.house_frame_item_count,
        item_profiles=[_serialize_condition_profile(profile) for profile in reduction.item_profiles],
        stage_sequence=reduction.stage_sequence,
    )


def serialize_progression_chart_condition_profile_with_reduction(
    agg: ProgressionChartConditionProfile,
    reduction: ProgressionAggregateReductionContext,
) -> ProgressionChartConditionProfileReductionResponse:
    return ProgressionChartConditionProfileReductionResponse(
        result=serialize_progression_chart_condition_profile(agg),
        reduction=_serialize_progression_aggregate_reduction_truth(
            reduction,
            engine_surface="progression_chart_condition_profile",
        ),
    )


def serialize_progression_condition_network_profile_with_reduction(
    net: ProgressionConditionNetworkProfile,
    reduction: ProgressionAggregateReductionContext,
) -> ProgressionConditionNetworkProfileReductionResponse:
    return ProgressionConditionNetworkProfileReductionResponse(
        result=serialize_progression_condition_network_profile(net),
        reduction=_serialize_progression_aggregate_reduction_truth(
            reduction,
            engine_surface="progression_condition_network_profile",
        ),
    )


def serialize_progression_chart_condition_profile(
    agg: ProgressionChartConditionProfile,
) -> ProgressionChartConditionProfileResponse:
    return ProgressionChartConditionProfileResponse(
        profiles=[_serialize_condition_profile(p) for p in agg.profiles],
        profile_count=agg.profile_count,
        uniform_count=agg.uniform_count,
        differential_count=agg.differential_count,
        hybrid_count=agg.hybrid_count,
        directing_arc_count=agg.directing_arc_count,
        time_key_count=agg.time_key_count,
        house_frame_count=agg.house_frame_count,
        strongest_techniques=list(agg.strongest_techniques),
        weakest_techniques=list(agg.weakest_techniques),
    )


def serialize_progression_condition_network_profile(
    net: ProgressionConditionNetworkProfile,
) -> ProgressionConditionNetworkProfileResponse:
    nodes = [
        ProgressionNetworkNodeResponse(
            node_id=n.node_id,
            node_kind=n.node_kind,
            label=n.label,
            incoming_count=n.incoming_count,
            outgoing_count=n.outgoing_count,
            total_degree=n.total_degree,
            is_isolated=n.is_isolated,
        )
        for n in net.nodes
    ]
    edges = [
        ProgressionNetworkEdgeResponse(
            source_id=e.source_id,
            target_id=e.target_id,
            relation_kind=e.relation_kind,
            relation_basis=e.relation_basis,
        )
        for e in net.edges
    ]
    return ProgressionConditionNetworkProfileResponse(
        nodes=nodes,
        edges=edges,
        technique_node_count=net.technique_node_count,
        target_node_count=net.target_node_count,
        most_connected_nodes=list(net.most_connected_nodes),
        isolated_nodes=list(net.isolated_nodes),
    )


def serialize_progressed_house_frame(frame: ProgressedHouseFrame) -> ProgressedHouseFrameResponse:
    houses = frame.houses
    return ProgressedHouseFrameResponse(
        chart_type=frame.chart_type,
        natal_jd_ut=frame.natal_jd_ut,
        progressed_jd_ut=frame.progressed_jd_ut,
        target_date=frame.target_date.isoformat(),
        house_system=houses.system,
        cusps=list(houses.cusps),
        asc=houses.asc,
        mc=houses.mc,
        vertex=houses.vertex,
        doctrine_family=frame.doctrine_family,
        coordinate_system=frame.coordinate_system,
        rate_mode=frame.rate_mode,
        application_mode=frame.application_mode,
        relation_kind=frame.relation_kind,
        relation_basis=frame.relation_basis,
        condition_state=frame.condition_state,
        relation=_serialize_relation(frame.relation),
        condition_profile=_serialize_condition_profile(frame.condition_profile),
    )


def serialize_daily_houses(frame: ProgressedHouseFrame) -> DailyHousesResponse:
    houses = frame.houses
    return DailyHousesResponse(
        natal_jd_ut=frame.natal_jd_ut,
        progressed_jd_ut=frame.progressed_jd_ut,
        target_date=frame.target_date.isoformat(),
        house_system=houses.system,
        cusps=list(houses.cusps),
        asc=houses.asc,
        mc=houses.mc,
        vertex=houses.vertex,
    )


__all__ = [
    "serialize_daily_houses",
    "serialize_progressed_chart",
    "serialize_progressed_chart_with_reduction",
    "serialize_progressed_house_frame_arc_with_reduction",
    "serialize_progressed_declination_chart",
    "serialize_progressed_declination_chart_with_reduction",
    "serialize_progressed_house_frame",
    "serialize_progressed_house_frame_with_reduction",
    "serialize_progression_chart_condition_profile",
    "serialize_progression_chart_condition_profile_with_reduction",
    "serialize_progression_condition_network_profile_with_reduction",
    "serialize_progression_condition_network_profile",
]
