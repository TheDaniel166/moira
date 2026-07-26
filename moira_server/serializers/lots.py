"""Serializers for Phase-9 Classical Lots vessels (P9-05)."""

from __future__ import annotations

from moira.lots import (
    ArabicPart,
    ArabicPartClassification,
    ArabicPartComputationTruth,
    LotChartConditionProfile,
    LotAstrologicalConditionTruth,
    LotConditionNetworkEdge,
    LotConditionNetworkNode,
    LotConditionNetworkProfile,
    LotConditionProfile,
    LotDependency,
    LotDependencyCompletenessTruth,
    LotNotEvaluable,
    LotReferenceClassification,
    LotReferenceTruth,
    LotsEvaluation,
    PartDefinition,
)

from ..models.lots import (
    ArabicPartClassificationResponse,
    ArabicPartComputationTruthResponse,
    ArabicPartResponse,
    LotAstrologicalConditionTruthResponse,
    LotChartConditionProfileResponse,
    LotConditionNetworkEdgeResponse,
    LotConditionNetworkNodeResponse,
    LotConditionNetworkProfileResponse,
    LotConditionProfileResponse,
    LotDependencyCompletenessTruthResponse,
    LotDependencyResponse,
    LotNotEvaluableResponse,
    LotReferenceClassificationResponse,
    LotReferenceTruthResponse,
    LotsCatalogResponse,
    LotsConditionsResponse,
    LotsDependenciesResponse,
    LotsResultResponse,
    PartDefinitionResponse,
)


def serialize_part_definition(part: PartDefinition) -> PartDefinitionResponse:
    return PartDefinitionResponse(
        name=part.name,
        day_add=part.day_add,
        day_sub=part.day_sub,
        reverse_at_night=part.reverse_at_night,
        category=part.category,
        description=part.description,
        projector=part.projector,
        arc_policy=part.arc_policy,
    )


def serialize_lots_catalog(parts: list[PartDefinition]) -> LotsCatalogResponse:
    return LotsCatalogResponse(
        parts=tuple(serialize_part_definition(part) for part in parts)
    )


def serialize_lot_reference_truth(
    truth: LotReferenceTruth,
) -> LotReferenceTruthResponse:
    return LotReferenceTruthResponse(
        key=truth.key,
        longitude=truth.longitude,
        source_kind=truth.source_kind,
        detail=truth.detail,
    )


def serialize_arabic_part_computation_truth(
    truth: ArabicPartComputationTruth,
) -> ArabicPartComputationTruthResponse:
    return ArabicPartComputationTruthResponse(
        asc_longitude=truth.asc_longitude,
        projector_key=truth.projector_key,
        projector_reference=serialize_lot_reference_truth(
            truth.projector_reference
        ),
        arc_policy=truth.arc_policy,
        requested_add_key=truth.requested_add_key,
        requested_sub_key=truth.requested_sub_key,
        effective_add_key=truth.effective_add_key,
        effective_sub_key=truth.effective_sub_key,
        reversed_at_night=truth.reversed_at_night,
        reversed_for_chart=truth.reversed_for_chart,
        add_reference=serialize_lot_reference_truth(truth.add_reference),
        sub_reference=serialize_lot_reference_truth(truth.sub_reference),
        formula=truth.formula,
    )


def serialize_lot_reference_classification(
    classification: LotReferenceClassification,
) -> LotReferenceClassificationResponse:
    return LotReferenceClassificationResponse(
        kind=classification.kind,
        key=classification.key,
        detail=classification.detail,
    )


def serialize_arabic_part_classification(
    classification: ArabicPartClassification,
) -> ArabicPartClassificationResponse:
    return ArabicPartClassificationResponse(
        primary_category=classification.primary_category,
        category_tags=classification.category_tags,
        reversal=classification.reversal,
        projector_reference=serialize_lot_reference_classification(
            classification.projector_reference
        ),
        add_reference=serialize_lot_reference_classification(
            classification.add_reference
        ),
        sub_reference=serialize_lot_reference_classification(
            classification.sub_reference
        ),
    )


def serialize_lot_dependency(dependency: LotDependency) -> LotDependencyResponse:
    return LotDependencyResponse(
        part_name=dependency.part_name,
        role=dependency.role.value,
        requested_key=dependency.requested_key,
        effective_key=dependency.effective_key,
        reference_kind=dependency.reference_kind.value,
        reference_longitude=dependency.reference_longitude,
        detail=dependency.detail,
        is_inter_lot=dependency.is_inter_lot,
        is_external=dependency.is_external,
        is_indirect=dependency.is_indirect,
    )


def serialize_lot_dependency_completeness(
    truth: LotDependencyCompletenessTruth,
) -> LotDependencyCompletenessTruthResponse:
    return LotDependencyCompletenessTruthResponse(
        status=truth.status,
        expected_roles=truth.expected_roles,
        resolved_roles=truth.resolved_roles,
        missing_references=truth.missing_references,
        reason=truth.reason,
    )


def serialize_lot_astrological_condition_truth(
    truth: LotAstrologicalConditionTruth,
) -> LotAstrologicalConditionTruthResponse:
    return LotAstrologicalConditionTruthResponse(
        status=truth.status,
        condition=truth.condition,
        reason=truth.reason,
    )


def serialize_lot_condition_profile(
    profile: LotConditionProfile,
) -> LotConditionProfileResponse:
    return LotConditionProfileResponse(
        part_name=profile.part_name,
        category_tags=tuple(profile.category_tags),
        primary_category=profile.primary_category,
        reversal=profile.reversal.value,
        all_dependencies=tuple(
            serialize_lot_dependency(dependency)
            for dependency in profile.all_dependencies
        ),
        dependencies=tuple(
            serialize_lot_dependency(dependency)
            for dependency in profile.dependencies
        ),
        direct_dependency_count=profile.direct_dependency_count,
        indirect_dependency_count=profile.indirect_dependency_count,
        inter_lot_dependency_count=profile.inter_lot_dependency_count,
        external_dependency_count=profile.external_dependency_count,
        state=profile.state.value,
        has_inter_lot_dependency=profile.has_inter_lot_dependency,
        has_external_dependency=profile.has_external_dependency,
    )


def serialize_arabic_part(part: ArabicPart) -> ArabicPartResponse:
    if part.computation_truth is None:
        raise ValueError("ArabicPart must preserve computation_truth")
    if part.classification is None:
        raise ValueError("ArabicPart must preserve classification")
    if part.dependency_completeness is None:
        raise ValueError("ArabicPart must preserve dependency_completeness")
    return ArabicPartResponse(
        name=part.name,
        longitude=part.longitude,
        formula=part.formula,
        category=part.category,
        description=part.description,
        computation_truth=serialize_arabic_part_computation_truth(
            part.computation_truth
        ),
        classification=serialize_arabic_part_classification(
            part.classification
        ),
        all_dependencies=tuple(
            serialize_lot_dependency(dependency)
            for dependency in part.all_dependencies
        ),
        dependencies=tuple(
            serialize_lot_dependency(dependency)
            for dependency in part.dependencies
        ),
        dependency_completeness=serialize_lot_dependency_completeness(
            part.dependency_completeness
        ),
        astrological_condition_truth=serialize_lot_astrological_condition_truth(
            part.astrological_condition_truth
        ),
        condition_profile=None
        if part.condition_profile is None
        else serialize_lot_condition_profile(part.condition_profile),
        sign=part.sign,
        sign_symbol=part.sign_symbol,
        sign_degree=part.sign_degree,
        longitude_dms=part.longitude_dms,
        category_tags=tuple(part.category_tags),
        primary_category=part.primary_category,
        reversal_kind=part.reversal_kind.value,
        is_reversed=part.is_reversed,
        add_reference_kind=None
        if part.add_reference_kind is None
        else part.add_reference_kind.value,
        sub_reference_kind=None
        if part.sub_reference_kind is None
        else part.sub_reference_kind.value,
        dependency_count=part.dependency_count,
        all_dependency_count=part.all_dependency_count,
        inter_lot_dependencies=tuple(
            serialize_lot_dependency(dependency)
            for dependency in part.inter_lot_dependencies
        ),
        external_dependencies=tuple(
            serialize_lot_dependency(dependency)
            for dependency in part.external_dependencies
        ),
        condition_state=part.condition_state.value,
    )


def serialize_lot_not_evaluable(
    result: LotNotEvaluable,
) -> LotNotEvaluableResponse:
    return LotNotEvaluableResponse(
        name=result.name,
        category=result.category,
        projector_key=result.projector_key,
        requested_add_key=result.requested_add_key,
        requested_sub_key=result.requested_sub_key,
        effective_add_key=result.effective_add_key,
        effective_sub_key=result.effective_sub_key,
        missing_references=result.missing_references,
        status=result.status,
        reason=result.reason,
    )


def serialize_lots_result(evaluation: LotsEvaluation) -> LotsResultResponse:
    return LotsResultResponse(
        parts=tuple(
            serialize_arabic_part(part)
            for part in evaluation.parts
        ),
        not_evaluable=tuple(
            serialize_lot_not_evaluable(result)
            for result in evaluation.not_evaluable
        ),
        status=evaluation.status,
        evaluated_count=evaluation.evaluated_count,
        not_evaluable_count=evaluation.not_evaluable_count,
    )


def serialize_lots_dependencies(
    dependencies: list[LotDependency],
) -> LotsDependenciesResponse:
    return LotsDependenciesResponse(
        dependencies=tuple(
            serialize_lot_dependency(dependency)
            for dependency in dependencies
        )
    )


def serialize_lots_conditions(
    profiles: list[LotConditionProfile],
) -> LotsConditionsResponse:
    return LotsConditionsResponse(
        profiles=tuple(
            serialize_lot_condition_profile(profile)
            for profile in profiles
        )
    )


def serialize_lot_chart_condition_profile(
    profile: LotChartConditionProfile,
) -> LotChartConditionProfileResponse:
    return LotChartConditionProfileResponse(
        profiles=tuple(
            serialize_lot_condition_profile(item)
            for item in profile.profiles
        ),
        direct_count=profile.direct_count,
        mixed_count=profile.mixed_count,
        indirect_count=profile.indirect_count,
        direct_dependency_total=profile.direct_dependency_total,
        indirect_dependency_total=profile.indirect_dependency_total,
        inter_lot_dependency_total=profile.inter_lot_dependency_total,
        external_dependency_total=profile.external_dependency_total,
        strongest_parts=tuple(profile.strongest_parts),
        weakest_parts=tuple(profile.weakest_parts),
        profile_count=profile.profile_count,
        strongest_count=profile.strongest_count,
        weakest_count=profile.weakest_count,
    )


def serialize_lot_network_node(
    node: LotConditionNetworkNode,
) -> LotConditionNetworkNodeResponse:
    return LotConditionNetworkNodeResponse(
        part_name=node.part_name,
        condition_state=node.condition_state.value,
        outgoing_count=node.outgoing_count,
        incoming_count=node.incoming_count,
        reciprocal_count=node.reciprocal_count,
        degree_count=node.degree_count,
        is_isolated=node.is_isolated,
    )


def serialize_lot_network_edge(
    edge: LotConditionNetworkEdge,
) -> LotConditionNetworkEdgeResponse:
    return LotConditionNetworkEdgeResponse(
        source_part=edge.source_part,
        target_part=edge.target_part,
        role=edge.role.value,
        mode=edge.mode.value,
    )


def serialize_lot_condition_network_profile(
    profile: LotConditionNetworkProfile,
) -> LotConditionNetworkProfileResponse:
    return LotConditionNetworkProfileResponse(
        nodes=tuple(serialize_lot_network_node(node) for node in profile.nodes),
        edges=tuple(serialize_lot_network_edge(edge) for edge in profile.edges),
        isolated_parts=tuple(profile.isolated_parts),
        most_connected_parts=tuple(profile.most_connected_parts),
        reciprocal_edge_count=profile.reciprocal_edge_count,
        unilateral_edge_count=profile.unilateral_edge_count,
        node_count=profile.node_count,
        edge_count=profile.edge_count,
    )


__all__ = [
    "serialize_arabic_part_classification",
    "serialize_arabic_part_computation_truth",
    "serialize_arabic_part",
    "serialize_lot_chart_condition_profile",
    "serialize_lot_condition_network_profile",
    "serialize_lot_condition_profile",
    "serialize_lot_dependency",
    "serialize_lot_dependency_completeness",
    "serialize_lot_astrological_condition_truth",
    "serialize_lot_not_evaluable",
    "serialize_lot_reference_classification",
    "serialize_lot_reference_truth",
    "serialize_lot_network_edge",
    "serialize_lot_network_node",
    "serialize_lots_catalog",
    "serialize_lots_conditions",
    "serialize_lots_dependencies",
    "serialize_lots_result",
    "serialize_part_definition",
]
