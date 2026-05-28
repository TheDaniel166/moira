"""Serializers for relationship and inter-chart vessels."""

from __future__ import annotations

from moira.aspects import AspectClassification, AspectData
from moira.chart_shape import ChartShape
from moira.houses import HousePlacement
from moira.midpoints import Midpoint, MidpointCluster, MidpointWeight, PlanetaryPicture
from moira.patterns import (
    AspectPattern,
    PatternAspectContribution,
    PatternBodyRoleClassification,
    PatternBodyRoleTruth,
    PatternChartConditionProfile,
    PatternClassification,
    PatternConditionNetworkEdge,
    PatternConditionNetworkNode,
    PatternConditionNetworkProfile,
    PatternConditionProfile,
    PatternDetectionTruth,
)
from moira.synastry import (
    CompositeChart,
    CompositeClassification,
    CompositeComputationTruth,
    DavisonChart,
    DavisonClassification,
    DavisonComputationTruth,
    DavisonInfo,
    MutualHouseOverlay,
    SynastryAspectClassification,
    SynastryAspectContact,
    SynastryAspectTruth,
    SynastryChartConditionProfile,
    SynastryConditionNetworkEdge,
    SynastryConditionNetworkNode,
    SynastryConditionNetworkProfile,
    SynastryConditionProfile,
    SynastryHouseOverlay,
    SynastryOverlayClassification,
    SynastryOverlayTruth,
    SynastryRelation,
)

from ..models.relationship import (
    AspectClassificationResponse,
    AspectDataResponse,
    AspectPatternResponse,
    ChartShapeResponse,
    CompositeChartResponse,
    CompositeClassificationResponse,
    CompositeComputationTruthResponse,
    DavisonChartResponse,
    DavisonClassificationResponse,
    DavisonComputationTruthResponse,
    DavisonInfoResponse,
    HousePlacementResponse,
    MidpointClusterResponse,
    MidpointHitResponse,
    MidpointResponse,
    MidpointWeightResponse,
    MutualHouseOverlayResponse,
    PatternAspectContributionResponse,
    PatternBodyRoleClassificationResponse,
    PatternBodyRoleTruthResponse,
    PatternChartConditionProfileResponse,
    PatternClassificationResponse,
    PatternConditionNetworkEdgeResponse,
    PatternConditionNetworkNodeResponse,
    PatternConditionNetworkProfileResponse,
    PatternConditionProfileResponse,
    PatternDetectionTruthResponse,
    PlanetaryPictureResponse,
    SynastryAspectClassificationResponse,
    SynastryAspectTruthResponse,
    SynastryChartConditionProfileResponse,
    SynastryConditionNetworkEdgeResponse,
    SynastryConditionNetworkNodeResponse,
    SynastryConditionNetworkProfileResponse,
    SynastryConditionProfileResponse,
    SynastryContactResponse,
    SynastryHouseOverlayResponse,
    SynastryOverlayClassificationResponse,
    SynastryOverlayTruthResponse,
    SynastryRelationResponse,
)
from .chart import serialize_chart, serialize_houses


def serialize_aspect_classification(classification: AspectClassification) -> AspectClassificationResponse:
    return AspectClassificationResponse(
        domain=classification.domain.value,
        tier=classification.tier.value,
        family=classification.family.value,
    )


def serialize_aspect(aspect: AspectData) -> AspectDataResponse:
    return AspectDataResponse(
        body1=aspect.body1,
        body2=aspect.body2,
        aspect=aspect.aspect,
        symbol=aspect.symbol,
        angle=aspect.angle,
        separation=aspect.separation,
        orb=aspect.orb,
        allowed_orb=aspect.allowed_orb,
        applying=aspect.applying,
        stationary=aspect.stationary,
        classification=(
            serialize_aspect_classification(aspect.classification)
            if aspect.classification is not None
            else None
        ),
        direction=aspect.direction,
        sign_degree1=aspect.sign_degree1,
        sign_degree2=aspect.sign_degree2,
    )


def serialize_synastry_aspect_truth(truth: SynastryAspectTruth) -> SynastryAspectTruthResponse:
    return SynastryAspectTruthResponse(
        source_label=truth.source_label,
        target_label=truth.target_label,
        source_body=truth.source_body,
        target_body=truth.target_body,
        tier=truth.tier,
        include_nodes=truth.include_nodes,
        orb_factor=truth.orb_factor,
        custom_orbs=truth.custom_orbs,
        source_speed=truth.source_speed,
        target_speed=truth.target_speed,
    )


def serialize_synastry_aspect_classification(
    classification: SynastryAspectClassification,
) -> SynastryAspectClassificationResponse:
    return SynastryAspectClassificationResponse(
        contact_mode=classification.contact_mode,
        pair_mode=classification.pair_mode,
        includes_nodes=classification.includes_nodes,
        uses_custom_orbs=classification.uses_custom_orbs,
    )


def serialize_synastry_relation(relation: SynastryRelation) -> SynastryRelationResponse:
    return SynastryRelationResponse(
        kind=relation.kind,
        basis=relation.basis,
        source_label=relation.source_label,
        target_label=relation.target_label,
        source_ref=relation.source_ref,
        target_ref=relation.target_ref,
        method=relation.method,
    )


def serialize_synastry_condition_profile(
    profile: SynastryConditionProfile,
) -> SynastryConditionProfileResponse:
    return SynastryConditionProfileResponse(
        result_kind=profile.result_kind,
        condition_state=profile.condition_state.name,
        pair_mode=profile.pair_mode,
        relation_kind=profile.relation_kind,
        relation_basis=profile.relation_basis,
        method=profile.method,
        includes_nodes=profile.includes_nodes,
        includes_house_frame=profile.includes_house_frame,
        has_house_fallback=profile.has_house_fallback,
    )


def serialize_synastry_contact(contact: SynastryAspectContact) -> SynastryContactResponse:
    return SynastryContactResponse(
        aspect=serialize_aspect(contact.aspect),
        truth=serialize_synastry_aspect_truth(contact.truth),
        classification=(
            serialize_synastry_aspect_classification(contact.classification)
            if contact.classification is not None
            else None
        ),
        relation=serialize_synastry_relation(contact.relation) if contact.relation is not None else None,
        condition_profile=(
            serialize_synastry_condition_profile(contact.condition_profile)
            if contact.condition_profile is not None
            else None
        ),
    )


def serialize_house_placement(placement: HousePlacement) -> HousePlacementResponse:
    return HousePlacementResponse(
        house=placement.house,
        longitude=placement.longitude,
        exact_on_cusp=placement.exact_on_cusp,
        cusp_longitude=placement.cusp_longitude,
    )


def serialize_synastry_overlay_truth(truth: SynastryOverlayTruth) -> SynastryOverlayTruthResponse:
    return SynastryOverlayTruthResponse(
        source_label=truth.source_label,
        target_label=truth.target_label,
        include_nodes=truth.include_nodes,
        point_count=truth.point_count,
        target_house_system=truth.target_house_system,
        target_effective_house_system=truth.target_effective_house_system,
        target_has_fallback=truth.target_has_fallback,
    )


def serialize_synastry_overlay_classification(
    classification: SynastryOverlayClassification,
) -> SynastryOverlayClassificationResponse:
    return SynastryOverlayClassificationResponse(
        overlay_mode=classification.overlay_mode,
        pair_mode=classification.pair_mode,
        includes_nodes=classification.includes_nodes,
        has_house_fallback=classification.has_house_fallback,
    )


def serialize_synastry_overlay(overlay: SynastryHouseOverlay) -> SynastryHouseOverlayResponse:
    return SynastryHouseOverlayResponse(
        source_label=overlay.source_label,
        target_label=overlay.target_label,
        placements={name: serialize_house_placement(p) for name, p in overlay.placements.items()},
        include_nodes=overlay.include_nodes,
        computation_truth=(
            serialize_synastry_overlay_truth(overlay.computation_truth)
            if overlay.computation_truth is not None
            else None
        ),
        classification=(
            serialize_synastry_overlay_classification(overlay.classification)
            if overlay.classification is not None
            else None
        ),
        relation=serialize_synastry_relation(overlay.relation) if overlay.relation is not None else None,
        condition_profile=(
            serialize_synastry_condition_profile(overlay.condition_profile)
            if overlay.condition_profile is not None
            else None
        ),
    )


def serialize_mutual_overlay(overlays: MutualHouseOverlay) -> MutualHouseOverlayResponse:
    return MutualHouseOverlayResponse(
        first_in_second=serialize_synastry_overlay(overlays.first_in_second),
        second_in_first=serialize_synastry_overlay(overlays.second_in_first),
    )


def serialize_composite_truth(truth: CompositeComputationTruth) -> CompositeComputationTruthResponse:
    return CompositeComputationTruthResponse(
        method=truth.method,
        jd_mean=truth.jd_mean,
        includes_house_frame=truth.includes_house_frame,
        reference_latitude=truth.reference_latitude,
        house_system=truth.house_system,
        composite_mc=truth.composite_mc,
        composite_armc=truth.composite_armc,
        source_house_system=truth.source_house_system,
        source_effective_house_system=truth.source_effective_house_system,
    )


def serialize_composite_classification(
    classification: CompositeClassification,
) -> CompositeClassificationResponse:
    return CompositeClassificationResponse(
        chart_mode=classification.chart_mode,
        method=classification.method,
        includes_house_frame=classification.includes_house_frame,
    )


def serialize_composite_chart(chart: CompositeChart) -> CompositeChartResponse:
    return CompositeChartResponse(
        planets=dict(chart.planets),
        nodes=dict(chart.nodes),
        cusps=list(chart.cusps),
        asc=chart.asc,
        mc=chart.mc,
        jd_mean=chart.jd_mean,
        computation_truth=serialize_composite_truth(chart.computation_truth) if chart.computation_truth else None,
        classification=(
            serialize_composite_classification(chart.classification)
            if chart.classification is not None
            else None
        ),
        relation=serialize_synastry_relation(chart.relation) if chart.relation is not None else None,
        condition_profile=(
            serialize_synastry_condition_profile(chart.condition_profile)
            if chart.condition_profile is not None
            else None
        ),
    )


def serialize_davison_truth(truth: DavisonComputationTruth) -> DavisonComputationTruthResponse:
    return DavisonComputationTruthResponse(
        method=truth.method,
        raw_midpoint_jd=truth.raw_midpoint_jd,
        used_jd=truth.used_jd,
        latitude_mode=truth.latitude_mode,
        longitude_mode=truth.longitude_mode,
        latitude_midpoint=truth.latitude_midpoint,
        longitude_midpoint=truth.longitude_midpoint,
        house_system=truth.house_system,
        corrected_target_mc=truth.corrected_target_mc,
        correction_applied=truth.correction_applied,
    )


def serialize_davison_classification(
    classification: DavisonClassification,
) -> DavisonClassificationResponse:
    return DavisonClassificationResponse(
        chart_mode=classification.chart_mode,
        method=classification.method,
        latitude_mode=classification.latitude_mode,
        longitude_mode=classification.longitude_mode,
        correction_mode=classification.correction_mode,
    )


def serialize_davison_info(info: DavisonInfo) -> DavisonInfoResponse:
    return DavisonInfoResponse(
        jd_midpoint=info.jd_midpoint,
        datetime_utc=info.datetime_utc.isoformat(),
        latitude_midpoint=info.latitude_midpoint,
        longitude_midpoint=info.longitude_midpoint,
        computation_truth=serialize_davison_truth(info.computation_truth) if info.computation_truth else None,
        classification=(
            serialize_davison_classification(info.classification)
            if info.classification is not None
            else None
        ),
        relation=serialize_synastry_relation(info.relation) if info.relation is not None else None,
        condition_profile=(
            serialize_synastry_condition_profile(info.condition_profile)
            if info.condition_profile is not None
            else None
        ),
    )


def serialize_davison_chart(chart: DavisonChart) -> DavisonChartResponse:
    return DavisonChartResponse(
        chart=serialize_chart(chart.chart),
        houses=serialize_houses(chart.houses) if chart.houses is not None else None,
        info=serialize_davison_info(chart.info),
    )


def serialize_synastry_chart_condition_profile(
    profile: SynastryChartConditionProfile,
) -> SynastryChartConditionProfileResponse:
    return SynastryChartConditionProfileResponse(
        profiles=[serialize_synastry_condition_profile(item) for item in profile.profiles],
        contact_count=profile.contact_count,
        overlay_count=profile.overlay_count,
        relationship_chart_count=profile.relationship_chart_count,
        strongest_profiles=[serialize_synastry_condition_profile(item) for item in profile.strongest_profiles],
        weakest_profiles=[serialize_synastry_condition_profile(item) for item in profile.weakest_profiles],
    )


def serialize_synastry_network_node(
    node: SynastryConditionNetworkNode,
) -> SynastryConditionNetworkNodeResponse:
    return SynastryConditionNetworkNodeResponse(
        node_id=node.node_id,
        kind=node.kind,
        incoming_count=node.incoming_count,
        outgoing_count=node.outgoing_count,
        total_degree=node.total_degree,
    )


def serialize_synastry_network_edge(
    edge: SynastryConditionNetworkEdge,
) -> SynastryConditionNetworkEdgeResponse:
    return SynastryConditionNetworkEdgeResponse(
        source_id=edge.source_id,
        target_id=edge.target_id,
        relation_kind=edge.relation_kind,
        relation_basis=edge.relation_basis,
        condition_state=edge.condition_state,
    )


def serialize_synastry_network(
    profile: SynastryConditionNetworkProfile,
) -> SynastryConditionNetworkProfileResponse:
    return SynastryConditionNetworkProfileResponse(
        nodes=[serialize_synastry_network_node(node) for node in profile.nodes],
        edges=[serialize_synastry_network_edge(edge) for edge in profile.edges],
        isolated_nodes=[serialize_synastry_network_node(node) for node in profile.isolated_nodes],
        most_connected_nodes=[serialize_synastry_network_node(node) for node in profile.most_connected_nodes],
    )


def serialize_chart_shape(shape: ChartShape) -> ChartShapeResponse:
    return ChartShapeResponse(
        shape=shape.shape.value,
        occupied_arc=shape.occupied_arc,
        largest_gap=shape.largest_gap,
        leading_planet=shape.leading_planet,
        handle_planet=shape.handle_planet,
        clusters=[sorted(cluster) for cluster in shape.clusters],
    )


def serialize_pattern_body_role_truth(role: PatternBodyRoleTruth) -> PatternBodyRoleTruthResponse:
    return PatternBodyRoleTruthResponse(body=role.body, role=role.role)


def serialize_pattern_detection_truth(
    truth: PatternDetectionTruth,
) -> PatternDetectionTruthResponse:
    return PatternDetectionTruthResponse(
        pattern_name=truth.pattern_name,
        detector=truth.detector,
        source_kind=truth.source_kind,
        orb_factor=truth.orb_factor,
        body_roles=[serialize_pattern_body_role_truth(role) for role in truth.body_roles],
        centroid_longitude=truth.centroid_longitude,
        max_body_distance=truth.max_body_distance,
        orb_limit=truth.orb_limit,
    )


def serialize_pattern_body_role_classification(
    role: PatternBodyRoleClassification,
) -> PatternBodyRoleClassificationResponse:
    return PatternBodyRoleClassificationResponse(body=role.body, role=role.role.value)


def serialize_pattern_classification(
    classification: PatternClassification,
) -> PatternClassificationResponse:
    return PatternClassificationResponse(
        pattern_name=classification.pattern_name,
        detector=classification.detector,
        source_kind=classification.source_kind.value,
        symmetry=classification.symmetry.value,
        body_count=classification.body_count,
        has_apex=classification.has_apex,
        body_roles=[
            serialize_pattern_body_role_classification(role)
            for role in classification.body_roles
        ],
    )


def serialize_pattern_contribution(
    contribution: PatternAspectContribution,
) -> PatternAspectContributionResponse:
    return PatternAspectContributionResponse(
        pattern_name=contribution.pattern_name,
        role=contribution.role.value,
        body1=contribution.body1,
        body2=contribution.body2,
        aspect_name=contribution.aspect_name,
        aspect_angle=contribution.aspect_angle,
        aspect=serialize_aspect(contribution.aspect),
    )


def serialize_pattern_condition_profile(
    profile: PatternConditionProfile,
) -> PatternConditionProfileResponse:
    return PatternConditionProfileResponse(
        pattern_name=profile.pattern_name,
        detector=profile.detector,
        source_kind=profile.source_kind.value,
        symmetry=profile.symmetry.value,
        body_count=profile.body_count,
        has_apex=profile.has_apex,
        contribution_count=profile.contribution_count,
        all_contribution_count=profile.all_contribution_count,
        structured_contribution_count=profile.structured_contribution_count,
        generic_contribution_count=profile.generic_contribution_count,
        state=profile.state.value,
    )


def serialize_aspect_pattern(pattern: AspectPattern) -> AspectPatternResponse:
    return AspectPatternResponse(
        name=pattern.name,
        bodies=list(pattern.bodies),
        aspects=[serialize_aspect(aspect) for aspect in pattern.aspects],
        apex=pattern.apex,
        detection_truth=(
            serialize_pattern_detection_truth(pattern.detection_truth)
            if pattern.detection_truth is not None
            else None
        ),
        classification=(
            serialize_pattern_classification(pattern.classification)
            if pattern.classification is not None
            else None
        ),
        all_contributions=[
            serialize_pattern_contribution(item) for item in pattern.all_contributions
        ],
        contributions=[
            serialize_pattern_contribution(item) for item in pattern.contributions
        ],
        condition_profile=(
            serialize_pattern_condition_profile(pattern.condition_profile)
            if pattern.condition_profile is not None
            else None
        ),
    )


def serialize_pattern_chart_condition_profile(
    profile: PatternChartConditionProfile,
) -> PatternChartConditionProfileResponse:
    return PatternChartConditionProfileResponse(
        profiles=[serialize_pattern_condition_profile(item) for item in profile.profiles],
        reinforced_count=profile.reinforced_count,
        mixed_count=profile.mixed_count,
        weakened_count=profile.weakened_count,
        structured_contribution_total=profile.structured_contribution_total,
        generic_contribution_total=profile.generic_contribution_total,
        strongest_patterns=list(profile.strongest_patterns),
        weakest_patterns=list(profile.weakest_patterns),
    )


def serialize_pattern_network_node(
    node: PatternConditionNetworkNode,
) -> PatternConditionNetworkNodeResponse:
    return PatternConditionNetworkNodeResponse(
        node_id=node.node_id,
        kind=node.kind,
        label=node.label,
        incoming_count=node.incoming_count,
        outgoing_count=node.outgoing_count,
        total_degree=node.total_degree,
    )


def serialize_pattern_network_edge(
    edge: PatternConditionNetworkEdge,
) -> PatternConditionNetworkEdgeResponse:
    return PatternConditionNetworkEdgeResponse(
        source_id=edge.source_id,
        target_id=edge.target_id,
        pattern_name=edge.pattern_name,
        role=edge.role.value,
    )


def serialize_pattern_network(
    profile: PatternConditionNetworkProfile,
) -> PatternConditionNetworkProfileResponse:
    return PatternConditionNetworkProfileResponse(
        nodes=[serialize_pattern_network_node(node) for node in profile.nodes],
        edges=[serialize_pattern_network_edge(edge) for edge in profile.edges],
        isolated_bodies=list(profile.isolated_bodies),
        most_connected_nodes=list(profile.most_connected_nodes),
    )


def serialize_midpoint(midpoint: Midpoint) -> MidpointResponse:
    return MidpointResponse(
        planet_a=midpoint.planet_a,
        planet_b=midpoint.planet_b,
        longitude=midpoint.longitude,
        sign=midpoint.sign,
        sign_symbol=midpoint.sign_symbol,
        sign_degree=midpoint.sign_degree,
    )


def serialize_midpoint_hit(item: tuple[Midpoint, float]) -> MidpointHitResponse:
    midpoint, orb = item
    return MidpointHitResponse(midpoint=serialize_midpoint(midpoint), orb=orb)


def serialize_planetary_picture(picture: PlanetaryPicture) -> PlanetaryPictureResponse:
    return PlanetaryPictureResponse(
        focus=picture.focus,
        pair_a=picture.pair_a,
        pair_b=picture.pair_b,
        midpoint_longitude=picture.midpoint_longitude,
        orb=picture.orb,
        dial=picture.dial,
    )


def serialize_midpoint_weight(weight: MidpointWeight) -> MidpointWeightResponse:
    return MidpointWeightResponse(
        planet=weight.planet,
        score=weight.score,
        pictures=[serialize_planetary_picture(item) for item in weight.pictures],
    )


def serialize_midpoint_cluster(cluster: MidpointCluster) -> MidpointClusterResponse:
    return MidpointClusterResponse(
        dial_position=cluster.dial_position,
        midpoints=[serialize_midpoint(item) for item in cluster.midpoints],
        spread=cluster.spread,
        dial=cluster.dial,
    )


__all__ = [
    "serialize_aspect",
    "serialize_aspect_pattern",
    "serialize_chart_shape",
    "serialize_composite_chart",
    "serialize_davison_chart",
    "serialize_midpoint",
    "serialize_midpoint_cluster",
    "serialize_midpoint_hit",
    "serialize_midpoint_weight",
    "serialize_mutual_overlay",
    "serialize_pattern_chart_condition_profile",
    "serialize_pattern_network",
    "serialize_synastry_chart_condition_profile",
    "serialize_synastry_contact",
    "serialize_synastry_network",
]
