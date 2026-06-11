"""Serializers for Phase-9 Classical Lots vessels (P9-05)."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any

from moira.lots import (
    ArabicPart,
    LotChartConditionProfile,
    LotConditionNetworkEdge,
    LotConditionNetworkNode,
    LotConditionNetworkProfile,
    LotConditionProfile,
    LotDependency,
    PartDefinition,
)

from ..models.lots import (
    ArabicPartResponse,
    LotChartConditionProfileResponse,
    LotConditionNetworkEdgeResponse,
    LotConditionNetworkNodeResponse,
    LotConditionNetworkProfileResponse,
    LotConditionProfileResponse,
    LotDependencyResponse,
    LotsCatalogResponse,
    LotsConditionsResponse,
    LotsDependenciesResponse,
    LotsResultResponse,
    PartDefinitionResponse,
)


def _transport_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {
            field.name: _transport_value(getattr(value, field.name))
            for field in fields(value)
            if field.init
        }
    if isinstance(value, dict):
        return {
            _transport_value(key): _transport_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_transport_value(item) for item in value]
    return value


def serialize_part_definition(part: PartDefinition) -> PartDefinitionResponse:
    return PartDefinitionResponse(
        name=part.name,
        day_add=part.day_add,
        day_sub=part.day_sub,
        reverse_at_night=part.reverse_at_night,
        category=part.category,
        description=part.description,
    )


def serialize_lots_catalog(parts: list[PartDefinition]) -> LotsCatalogResponse:
    return LotsCatalogResponse(
        parts=tuple(serialize_part_definition(part) for part in parts)
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
    return ArabicPartResponse(
        name=part.name,
        longitude=part.longitude,
        formula=part.formula,
        category=part.category,
        description=part.description,
        computation_truth=_transport_value(part.computation_truth),
        classification=_transport_value(part.classification),
        all_dependencies=tuple(
            serialize_lot_dependency(dependency)
            for dependency in part.all_dependencies
        ),
        dependencies=tuple(
            serialize_lot_dependency(dependency)
            for dependency in part.dependencies
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


def serialize_lots_result(parts: list[ArabicPart]) -> LotsResultResponse:
    return LotsResultResponse(
        parts=tuple(serialize_arabic_part(part) for part in parts)
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
    "serialize_arabic_part",
    "serialize_lot_chart_condition_profile",
    "serialize_lot_condition_network_profile",
    "serialize_lot_condition_profile",
    "serialize_lot_dependency",
    "serialize_lot_network_edge",
    "serialize_lot_network_node",
    "serialize_lots_catalog",
    "serialize_lots_conditions",
    "serialize_lots_dependencies",
    "serialize_lots_result",
    "serialize_part_definition",
]
