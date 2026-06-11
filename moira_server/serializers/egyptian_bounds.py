"""Serializers for Phase-9 Egyptian Bounds vessels (P9-07)."""

from __future__ import annotations

from moira.egyptian_bounds import (
    EgyptianBoundClassification,
    EgyptianBoundConditionProfile,
    EgyptianBoundRelation,
    EgyptianBoundRelationProfile,
    EgyptianBoundSegment,
    EgyptianBoundTruth,
    EgyptianBoundsAggregateProfile,
    EgyptianBoundsNetworkEdge,
    EgyptianBoundsNetworkNode,
    EgyptianBoundsNetworkProfile,
)

from ..models.egyptian_bounds import (
    EgyptianBoundClassificationResponse,
    EgyptianBoundConditionProfileResponse,
    EgyptianBoundRelationProfileResponse,
    EgyptianBoundRelationResponse,
    EgyptianBoundSegmentResponse,
    EgyptianBoundTableSignResponse,
    EgyptianBoundTruthResponse,
    EgyptianBoundsAggregateProfileResponse,
    EgyptianBoundsNetworkEdgeResponse,
    EgyptianBoundsNetworkNodeResponse,
    EgyptianBoundsNetworkProfileResponse,
    EgyptianBoundsTableResponse,
)


def serialize_egyptian_bound_segment(
    segment: EgyptianBoundSegment,
) -> EgyptianBoundSegmentResponse:
    return EgyptianBoundSegmentResponse(
        sign=segment.sign,
        ruler=segment.ruler,
        start_degree=segment.start_degree,
        end_degree=segment.end_degree,
        width=segment.width,
    )


def serialize_egyptian_bounds_table(
    *,
    doctrine: str,
    signs: list[tuple[str, list[EgyptianBoundSegment]]],
) -> EgyptianBoundsTableResponse:
    return EgyptianBoundsTableResponse(
        doctrine=doctrine,
        signs=tuple(
            EgyptianBoundTableSignResponse(
                sign=sign,
                segments=tuple(
                    serialize_egyptian_bound_segment(segment)
                    for segment in segments
                ),
            )
            for sign, segments in signs
        ),
    )


def serialize_egyptian_bound_truth(
    truth: EgyptianBoundTruth,
) -> EgyptianBoundTruthResponse:
    return EgyptianBoundTruthResponse(
        longitude=truth.longitude,
        doctrine=truth.doctrine.value,
        sign=truth.sign,
        sign_index=truth.sign_index,
        degree_in_sign=truth.degree_in_sign,
        segment=serialize_egyptian_bound_segment(truth.segment),
        ruler=truth.ruler,
        segment_start_degree=truth.segment_start_degree,
        segment_end_degree=truth.segment_end_degree,
        segment_width=truth.segment_width,
        segment_range=truth.segment_range,
    )


def serialize_egyptian_bound_classification(
    classification: EgyptianBoundClassification,
) -> EgyptianBoundClassificationResponse:
    return EgyptianBoundClassificationResponse(
        planet=classification.planet,
        truth=serialize_egyptian_bound_truth(classification.truth),
        own_bound=classification.own_bound,
        host_nature=classification.host_nature.value,
        host_in_sect=classification.host_in_sect,
        hosted_by_benefic=classification.hosted_by_benefic,
        hosted_by_malefic=classification.hosted_by_malefic,
    )


def serialize_egyptian_bound_relation(
    relation: EgyptianBoundRelation,
) -> EgyptianBoundRelationResponse:
    return EgyptianBoundRelationResponse(
        guest_planet=relation.guest_planet,
        host_ruler=relation.host_ruler,
        truth=serialize_egyptian_bound_truth(relation.truth),
        relation_kind=relation.relation_kind.value,
        host_nature=relation.host_nature.value,
        host_in_sect=relation.host_in_sect,
        own_bound=relation.own_bound,
        hosted_by_benefic=relation.hosted_by_benefic,
        hosted_by_malefic=relation.hosted_by_malefic,
        hosted_by_neutral=relation.hosted_by_neutral,
    )


def serialize_egyptian_bound_relation_profile(
    profile: EgyptianBoundRelationProfile,
) -> EgyptianBoundRelationProfileResponse:
    return EgyptianBoundRelationProfileResponse(
        planet=profile.planet,
        truth=serialize_egyptian_bound_truth(profile.truth),
        detected_relation=serialize_egyptian_bound_relation(profile.detected_relation),
        admitted_relations=tuple(
            serialize_egyptian_bound_relation(relation)
            for relation in profile.admitted_relations
        ),
        scored_relations=tuple(
            serialize_egyptian_bound_relation(relation)
            for relation in profile.scored_relations
        ),
        detected_relation_kind=profile.detected_relation_kind.value,
        admitted_relation_kinds=tuple(
            kind.value for kind in profile.admitted_relation_kinds
        ),
        scored_relation_kinds=tuple(
            kind.value for kind in profile.scored_relation_kinds
        ),
        has_detected_relation=profile.has_detected_relation,
        has_admitted_relation=profile.has_admitted_relation,
        has_scored_relation=profile.has_scored_relation,
    )


def serialize_egyptian_bound_condition_profile(
    profile: EgyptianBoundConditionProfile,
) -> EgyptianBoundConditionProfileResponse:
    return EgyptianBoundConditionProfileResponse(
        planet=profile.planet,
        truth=serialize_egyptian_bound_truth(profile.truth),
        classification=serialize_egyptian_bound_classification(profile.classification),
        relation_profile=serialize_egyptian_bound_relation_profile(
            profile.relation_profile
        ),
        strengthening_count=profile.strengthening_count,
        weakening_count=profile.weakening_count,
        neutral_count=profile.neutral_count,
        state=profile.state.value,
        is_self_governed=profile.is_self_governed,
        is_supported=profile.is_supported,
        is_mediated=profile.is_mediated,
        is_constrained=profile.is_constrained,
    )


def serialize_egyptian_bounds_aggregate_profile(
    profile: EgyptianBoundsAggregateProfile,
) -> EgyptianBoundsAggregateProfileResponse:
    return EgyptianBoundsAggregateProfileResponse(
        profiles=tuple(
            serialize_egyptian_bound_condition_profile(condition)
            for condition in profile.profiles
        ),
        self_governed_count=profile.self_governed_count,
        supported_count=profile.supported_count,
        mediated_count=profile.mediated_count,
        constrained_count=profile.constrained_count,
        strengthening_total=profile.strengthening_total,
        weakening_total=profile.weakening_total,
        neutral_total=profile.neutral_total,
        strongest_planets=profile.strongest_planets,
        weakest_planets=profile.weakest_planets,
        strongest_count=profile.strongest_count,
        weakest_count=profile.weakest_count,
    )


def serialize_egyptian_bounds_network_node(
    node: EgyptianBoundsNetworkNode,
) -> EgyptianBoundsNetworkNodeResponse:
    return EgyptianBoundsNetworkNodeResponse(
        planet=node.planet,
        profile=serialize_egyptian_bound_condition_profile(node.profile),
        incoming_count=node.incoming_count,
        outgoing_count=node.outgoing_count,
        mutual_count=node.mutual_count,
        total_degree=node.total_degree,
        is_isolated=node.is_isolated,
    )


def serialize_egyptian_bounds_network_edge(
    edge: EgyptianBoundsNetworkEdge,
) -> EgyptianBoundsNetworkEdgeResponse:
    return EgyptianBoundsNetworkEdgeResponse(
        source_planet=edge.source_planet,
        target_planet=edge.target_planet,
        relation_kind=edge.relation_kind.value,
        mode=edge.mode.value,
        is_mutual=edge.is_mutual,
    )


def serialize_egyptian_bounds_network_profile(
    profile: EgyptianBoundsNetworkProfile,
) -> EgyptianBoundsNetworkProfileResponse:
    return EgyptianBoundsNetworkProfileResponse(
        nodes=tuple(
            serialize_egyptian_bounds_network_node(node)
            for node in profile.nodes
        ),
        edges=tuple(
            serialize_egyptian_bounds_network_edge(edge)
            for edge in profile.edges
        ),
        isolated_planets=profile.isolated_planets,
        most_connected_planets=profile.most_connected_planets,
        mutual_edge_count=profile.mutual_edge_count,
        unilateral_edge_count=profile.unilateral_edge_count,
        node_count=profile.node_count,
        edge_count=profile.edge_count,
    )


__all__ = [
    "serialize_egyptian_bound_classification",
    "serialize_egyptian_bound_condition_profile",
    "serialize_egyptian_bound_relation",
    "serialize_egyptian_bound_relation_profile",
    "serialize_egyptian_bound_segment",
    "serialize_egyptian_bound_truth",
    "serialize_egyptian_bounds_aggregate_profile",
    "serialize_egyptian_bounds_network_edge",
    "serialize_egyptian_bounds_network_node",
    "serialize_egyptian_bounds_network_profile",
    "serialize_egyptian_bounds_table",
]
