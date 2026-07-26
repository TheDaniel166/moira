"""Serializers for Phase-9 Classical Dignities vessels (P9-04)."""

from __future__ import annotations

from dataclasses import fields, is_dataclass
from enum import Enum
from typing import Any

from moira.dignities_types import (
    ChartConditionProfile,
    ConditionNetworkEdge,
    ConditionNetworkNode,
    ConditionNetworkProfile,
    PlanetaryConditionProfile,
    PlanetaryDignity,
    PlanetaryReception,
)

from ..models.dignities import (
    AccidentalDignityTruthResponse,
    ChartConditionProfileResponse,
    ConditionNetworkEdgeResponse,
    ConditionNetworkNodeResponse,
    ConditionNetworkProfileResponse,
    DignitiesConditionsResponse,
    DignitiesReceptionsResponse,
    DignitiesResultResponse,
    EssentialDignityTruthResponse,
    PlanetaryConditionProfileResponse,
    PlanetaryDignityResponse,
    PlanetaryReceptionResponse,
    SectTruthResponse,
    SolarConditionTruthResponse,
    MutualReceptionTruthResponse,
)


def _transport_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {
            field.name: _transport_value(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, dict):
        return {
            _transport_value(key): _transport_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_transport_value(item) for item in value]
    return value


def _typed_truth(value: Any, response_type):
    if value is None:
        return None
    return response_type.model_validate(_transport_value(value))


def serialize_planetary_reception(
    reception: PlanetaryReception,
) -> PlanetaryReceptionResponse:
    return PlanetaryReceptionResponse(
        receiving_planet=reception.receiving_planet,
        host_planet=reception.host_planet,
        basis=reception.basis.value,
        mode=reception.mode.value,
        receiving_sign=reception.receiving_sign,
        host_sign=reception.host_sign,
        host_matching_signs=tuple(reception.host_matching_signs),
        is_mutual=reception.is_mutual,
    )


def serialize_planetary_condition_profile(
    profile: PlanetaryConditionProfile,
) -> PlanetaryConditionProfileResponse:
    return PlanetaryConditionProfileResponse(
        planet=profile.planet,
        essential_truth=_typed_truth(
            profile.essential_truth,
            EssentialDignityTruthResponse,
        ),
        essential_classification=_transport_value(profile.essential_classification),
        accidental_truth=_typed_truth(
            profile.accidental_truth,
            AccidentalDignityTruthResponse,
        ),
        accidental_classification=_transport_value(profile.accidental_classification),
        sect_truth=_typed_truth(profile.sect_truth, SectTruthResponse),
        sect_classification=_transport_value(profile.sect_classification),
        solar_truth=_typed_truth(
            profile.solar_truth,
            SolarConditionTruthResponse,
        ),
        solar_classification=_transport_value(profile.solar_classification),
        all_receptions=tuple(
            serialize_planetary_reception(reception)
            for reception in profile.all_receptions
        ),
        admitted_receptions=tuple(
            serialize_planetary_reception(reception)
            for reception in profile.admitted_receptions
        ),
        scored_receptions=tuple(
            serialize_planetary_reception(reception)
            for reception in profile.scored_receptions
        ),
        mutual_reception_truth=tuple(
            _typed_truth(truth, MutualReceptionTruthResponse)
            for truth in profile.mutual_reception_truth
        ),
        reception_classification=tuple(
            _transport_value(classification)
            for classification in profile.reception_classification
        ),
        strengthening_count=profile.strengthening_count,
        weakening_count=profile.weakening_count,
        neutral_count=profile.neutral_count,
        state=profile.state.value,
    )


def serialize_planetary_dignity(
    dignity: PlanetaryDignity,
) -> PlanetaryDignityResponse:
    return PlanetaryDignityResponse(
        planet=dignity.planet,
        sign=dignity.sign,
        degree=dignity.degree,
        house=dignity.house,
        essential_dignity=dignity.essential_dignity,
        essential_score=dignity.essential_score,
        accidental_dignities=tuple(dignity.accidental_dignities),
        accidental_score=dignity.accidental_score,
        total_score=dignity.total_score,
        is_retrograde=dignity.is_retrograde,
        essential_truth=_typed_truth(
            dignity.essential_truth,
            EssentialDignityTruthResponse,
        ),
        accidental_truth=_typed_truth(
            dignity.accidental_truth,
            AccidentalDignityTruthResponse,
        ),
        sect_truth=_typed_truth(dignity.sect_truth, SectTruthResponse),
        solar_truth=_typed_truth(
            dignity.solar_truth,
            SolarConditionTruthResponse,
        ),
        all_receptions=tuple(
            serialize_planetary_reception(reception)
            for reception in dignity.all_receptions
        ),
        admitted_receptions=tuple(
            serialize_planetary_reception(reception)
            for reception in dignity.admitted_receptions
        ),
        scored_receptions=tuple(
            serialize_planetary_reception(reception)
            for reception in dignity.scored_receptions
        ),
        mutual_reception_truth=tuple(
            _typed_truth(truth, MutualReceptionTruthResponse)
            for truth in dignity.mutual_reception_truth
        ),
        essential_classification=_transport_value(dignity.essential_classification),
        accidental_classification=_transport_value(dignity.accidental_classification),
        sect_classification=_transport_value(dignity.sect_classification),
        solar_classification=_transport_value(dignity.solar_classification),
        reception_classification=tuple(
            _transport_value(classification)
            for classification in dignity.reception_classification
        ),
        condition_profile=None
        if dignity.condition_profile is None
        else serialize_planetary_condition_profile(dignity.condition_profile),
    )


def serialize_dignities_result(
    dignities: list[PlanetaryDignity],
) -> DignitiesResultResponse:
    return DignitiesResultResponse(
        dignities=tuple(serialize_planetary_dignity(dignity) for dignity in dignities)
    )


def serialize_dignities_receptions(
    receptions: list[PlanetaryReception],
) -> DignitiesReceptionsResponse:
    return DignitiesReceptionsResponse(
        receptions=tuple(
            serialize_planetary_reception(reception)
            for reception in receptions
        )
    )


def serialize_dignities_conditions(
    profiles: list[PlanetaryConditionProfile],
) -> DignitiesConditionsResponse:
    return DignitiesConditionsResponse(
        profiles=tuple(
            serialize_planetary_condition_profile(profile)
            for profile in profiles
        )
    )


def serialize_chart_condition_profile(
    profile: ChartConditionProfile,
) -> ChartConditionProfileResponse:
    return ChartConditionProfileResponse(
        profiles=tuple(
            serialize_planetary_condition_profile(planet_profile)
            for planet_profile in profile.profiles
        ),
        reinforced_count=profile.reinforced_count,
        mixed_count=profile.mixed_count,
        weakened_count=profile.weakened_count,
        strengthening_total=profile.strengthening_total,
        weakening_total=profile.weakening_total,
        neutral_total=profile.neutral_total,
        strongest_planets=tuple(profile.strongest_planets),
        weakest_planets=tuple(profile.weakest_planets),
        essential_strengthening_total=profile.essential_strengthening_total,
        essential_weakening_total=profile.essential_weakening_total,
        accidental_strengthening_total=profile.accidental_strengthening_total,
        accidental_weakening_total=profile.accidental_weakening_total,
        reception_participation_total=profile.reception_participation_total,
        strongest_count=profile.strongest_count,
        weakest_count=profile.weakest_count,
    )


def serialize_condition_network_node(
    node: ConditionNetworkNode,
) -> ConditionNetworkNodeResponse:
    return ConditionNetworkNodeResponse(
        planet=node.planet,
        profile=serialize_planetary_condition_profile(node.profile),
        incoming_count=node.incoming_count,
        outgoing_count=node.outgoing_count,
        mutual_count=node.mutual_count,
        total_degree=node.total_degree,
        is_isolated=node.is_isolated,
    )


def serialize_condition_network_edge(
    edge: ConditionNetworkEdge,
) -> ConditionNetworkEdgeResponse:
    return ConditionNetworkEdgeResponse(
        source_planet=edge.source_planet,
        target_planet=edge.target_planet,
        basis=edge.basis.value,
        mode=edge.mode.value,
        is_mutual=edge.is_mutual,
    )


def serialize_condition_network_profile(
    profile: ConditionNetworkProfile,
) -> ConditionNetworkProfileResponse:
    return ConditionNetworkProfileResponse(
        nodes=tuple(serialize_condition_network_node(node) for node in profile.nodes),
        edges=tuple(serialize_condition_network_edge(edge) for edge in profile.edges),
        isolated_planets=tuple(profile.isolated_planets),
        most_connected_planets=tuple(profile.most_connected_planets),
        mutual_edge_count=profile.mutual_edge_count,
        unilateral_edge_count=profile.unilateral_edge_count,
        node_count=profile.node_count,
        edge_count=profile.edge_count,
    )


__all__ = [
    "serialize_chart_condition_profile",
    "serialize_condition_network_edge",
    "serialize_condition_network_node",
    "serialize_condition_network_profile",
    "serialize_dignities_conditions",
    "serialize_dignities_receptions",
    "serialize_dignities_result",
    "serialize_planetary_condition_profile",
    "serialize_planetary_dignity",
    "serialize_planetary_reception",
]
