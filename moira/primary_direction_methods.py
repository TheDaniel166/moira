"""
Moira -- primary_direction_methods.py
Standalone primary-direction method doctrine subsystem.

Boundary
--------
Owns the doctrinal identity, classification, and hardened interpretation of
currently admitted primary-direction method families.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

__all__ = [
    "PrimaryDirectionMethod",
    "PrimaryDirectionMethodKind",
    "PrimaryDirectionMethodRelationKind",
    "PrimaryDirectionMethodConditionState",
    "PrimaryDirectionMethodPolicy",
    "PrimaryDirectionMethodTruth",
    "PrimaryDirectionMethodClassification",
    "PrimaryDirectionMethodRelation",
    "PrimaryDirectionMethodRelationProfile",
    "PrimaryDirectionMethodConditionProfile",
    "PrimaryDirectionMethodsAggregateProfile",
    "PrimaryDirectionMethodsNetworkNode",
    "PrimaryDirectionMethodsNetworkEdge",
    "PrimaryDirectionMethodsNetworkProfile",
    "primary_direction_method_truth",
    "classify_primary_direction_method",
    "relate_primary_direction_method",
    "evaluate_primary_direction_method_relations",
    "evaluate_primary_direction_method_condition",
    "evaluate_primary_direction_methods_aggregate",
    "evaluate_primary_direction_methods_network",
]


class PrimaryDirectionMethod(StrEnum):
    PLACIDUS_MUNDANE = "placidus_mundane"
    PLACIDIAN_CLASSIC_SEMI_ARC = "placidian_classic_semi_arc"


class PrimaryDirectionMethodKind(StrEnum):
    PLACIDUS_MUNDANE = "placidus_mundane"
    PLACIDIAN_CLASSIC_SEMI_ARC = "placidian_classic_semi_arc"


class PrimaryDirectionMethodRelationKind(StrEnum):
    PLACIDIAN_MUNDANE_PERFECTION = "placidian_mundane_perfection"
    PLACIDIAN_CLASSIC_SEMI_ARC_PERFECTION = "placidian_classic_semi_arc_perfection"


class PrimaryDirectionMethodConditionState(StrEnum):
    MUNDANE_SEMI_ARC_GROUNDED = "mundane_semi_arc_grounded"
    CLASSIC_SEMI_ARC_GROUNDED = "classic_semi_arc_grounded"


@dataclass(frozen=True, slots=True)
class PrimaryDirectionMethodPolicy:
    method: PrimaryDirectionMethod = PrimaryDirectionMethod.PLACIDUS_MUNDANE

    def __post_init__(self) -> None:
        if self.method not in (
            PrimaryDirectionMethod.PLACIDUS_MUNDANE,
            PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC,
        ):
            raise ValueError(f"Unsupported primary direction method: {self.method}")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionMethodTruth:
    method: PrimaryDirectionMethod
    kind: PrimaryDirectionMethodKind
    uses_semi_arcs: bool
    uses_world_frame_geometry: bool
    latitude_sensitive: bool

    def __post_init__(self) -> None:
        expected_kind = {
            PrimaryDirectionMethod.PLACIDUS_MUNDANE: PrimaryDirectionMethodKind.PLACIDUS_MUNDANE,
            PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC: PrimaryDirectionMethodKind.PLACIDIAN_CLASSIC_SEMI_ARC,
        }.get(self.method)
        if expected_kind is None:
            raise ValueError(f"Unsupported primary direction method on truth: {self.method}")
        if self.kind is not expected_kind:
            raise ValueError("PrimaryDirectionMethodTruth invariant failed: kind mismatch")
        if not self.uses_semi_arcs or not self.uses_world_frame_geometry or not self.latitude_sensitive:
            raise ValueError(
                "PrimaryDirectionMethodTruth invariant failed: current admitted method traits mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionMethodClassification:
    truth: PrimaryDirectionMethodTruth
    mundane: bool
    zodiacal: bool
    semi_arc_based: bool

    def __post_init__(self) -> None:
        if not self.mundane or self.zodiacal or not self.semi_arc_based:
            raise ValueError(
                "PrimaryDirectionMethodClassification invariant failed: current admitted method classification mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionMethodRelation:
    truth: PrimaryDirectionMethodTruth
    relation_kind: PrimaryDirectionMethodRelationKind

    def __post_init__(self) -> None:
        expected_kind = {
            PrimaryDirectionMethod.PLACIDUS_MUNDANE: PrimaryDirectionMethodRelationKind.PLACIDIAN_MUNDANE_PERFECTION,
            PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC: PrimaryDirectionMethodRelationKind.PLACIDIAN_CLASSIC_SEMI_ARC_PERFECTION,
        }[self.truth.method]
        if self.relation_kind is not expected_kind:
            raise ValueError("PrimaryDirectionMethodRelation invariant failed: relation_kind mismatch")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionMethodRelationProfile:
    truth: PrimaryDirectionMethodTruth
    detected_relation: PrimaryDirectionMethodRelation
    admitted_relations: tuple[PrimaryDirectionMethodRelation, ...]
    scored_relations: tuple[PrimaryDirectionMethodRelation, ...]

    def __post_init__(self) -> None:
        if self.detected_relation.truth != self.truth:
            raise ValueError(
                "PrimaryDirectionMethodRelationProfile invariant failed: detected relation truth mismatch"
            )
        if self.detected_relation not in self.admitted_relations:
            raise ValueError(
                "PrimaryDirectionMethodRelationProfile invariant failed: detected relation must be admitted"
            )
        for relation in self.scored_relations:
            if relation not in self.admitted_relations:
                raise ValueError(
                    "PrimaryDirectionMethodRelationProfile invariant failed: scored relation must be admitted"
                )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionMethodConditionProfile:
    truth: PrimaryDirectionMethodTruth
    classification: PrimaryDirectionMethodClassification
    relation_profile: PrimaryDirectionMethodRelationProfile
    state: PrimaryDirectionMethodConditionState

    def __post_init__(self) -> None:
        if self.classification.truth != self.truth:
            raise ValueError(
                "PrimaryDirectionMethodConditionProfile invariant failed: classification truth mismatch"
            )
        if self.relation_profile.truth != self.truth:
            raise ValueError(
                "PrimaryDirectionMethodConditionProfile invariant failed: relation truth mismatch"
            )
        expected_state = {
            PrimaryDirectionMethod.PLACIDUS_MUNDANE: PrimaryDirectionMethodConditionState.MUNDANE_SEMI_ARC_GROUNDED,
            PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC: PrimaryDirectionMethodConditionState.CLASSIC_SEMI_ARC_GROUNDED,
        }[self.truth.method]
        if self.state is not expected_state:
            raise ValueError("PrimaryDirectionMethodConditionProfile invariant failed: state mismatch")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionMethodsAggregateProfile:
    profiles: tuple[PrimaryDirectionMethodConditionProfile, ...]
    total_profiles: int
    mundane_count: int
    semi_arc_count: int

    def __post_init__(self) -> None:
        if not self.profiles:
            raise ValueError("PrimaryDirectionMethodsAggregateProfile requires at least one profile")
        if self.total_profiles != len(self.profiles):
            raise ValueError(
                "PrimaryDirectionMethodsAggregateProfile invariant failed: total_profiles mismatch"
            )
        if self.mundane_count != len(self.profiles):
            raise ValueError(
                "PrimaryDirectionMethodsAggregateProfile invariant failed: mundane_count mismatch"
            )
        if self.semi_arc_count != len(self.profiles):
            raise ValueError(
                "PrimaryDirectionMethodsAggregateProfile invariant failed: semi_arc_count mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionMethodsNetworkNode:
    method: PrimaryDirectionMethod
    count: int

    def __post_init__(self) -> None:
        if self.count <= 0:
            raise ValueError("PrimaryDirectionMethodsNetworkNode invariant failed: count must be positive")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionMethodsNetworkEdge:
    from_method: PrimaryDirectionMethod
    to_method: PrimaryDirectionMethod
    count: int

    def __post_init__(self) -> None:
        if self.from_method == self.to_method:
            raise ValueError(
                "PrimaryDirectionMethodsNetworkEdge invariant failed: self-edges are not admitted"
            )
        if self.count <= 0:
            raise ValueError("PrimaryDirectionMethodsNetworkEdge invariant failed: count must be positive")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionMethodsNetworkProfile:
    nodes: tuple[PrimaryDirectionMethodsNetworkNode, ...]
    edges: tuple[PrimaryDirectionMethodsNetworkEdge, ...]
    dominant_method: PrimaryDirectionMethod
    isolated_methods: tuple[PrimaryDirectionMethod, ...]

    def __post_init__(self) -> None:
        if not self.nodes:
            raise ValueError("PrimaryDirectionMethodsNetworkProfile requires at least one node")
        methods = [node.method for node in self.nodes]
        if len(set(methods)) != len(methods):
            raise ValueError(
                "PrimaryDirectionMethodsNetworkProfile invariant failed: duplicate nodes"
            )


def primary_direction_method_truth(
    method: PrimaryDirectionMethod = PrimaryDirectionMethod.PLACIDUS_MUNDANE,
    *,
    policy: PrimaryDirectionMethodPolicy | None = None,
) -> PrimaryDirectionMethodTruth:
    resolved_policy = policy if policy is not None else PrimaryDirectionMethodPolicy(method)
    return PrimaryDirectionMethodTruth(
        method=resolved_policy.method,
        kind={
            PrimaryDirectionMethod.PLACIDUS_MUNDANE: PrimaryDirectionMethodKind.PLACIDUS_MUNDANE,
            PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC: PrimaryDirectionMethodKind.PLACIDIAN_CLASSIC_SEMI_ARC,
        }[resolved_policy.method],
        uses_semi_arcs=True,
        uses_world_frame_geometry=True,
        latitude_sensitive=True,
    )


def classify_primary_direction_method(
    truth: PrimaryDirectionMethodTruth,
) -> PrimaryDirectionMethodClassification:
    return PrimaryDirectionMethodClassification(
        truth=truth,
        mundane=True,
        zodiacal=False,
        semi_arc_based=True,
    )


def relate_primary_direction_method(
    truth: PrimaryDirectionMethodTruth,
) -> PrimaryDirectionMethodRelation:
    return PrimaryDirectionMethodRelation(
        truth=truth,
        relation_kind={
            PrimaryDirectionMethod.PLACIDUS_MUNDANE: PrimaryDirectionMethodRelationKind.PLACIDIAN_MUNDANE_PERFECTION,
            PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC: PrimaryDirectionMethodRelationKind.PLACIDIAN_CLASSIC_SEMI_ARC_PERFECTION,
        }[truth.method],
    )


def evaluate_primary_direction_method_relations(
    truth: PrimaryDirectionMethodTruth,
) -> PrimaryDirectionMethodRelationProfile:
    relation = relate_primary_direction_method(truth)
    admitted = (relation,)
    return PrimaryDirectionMethodRelationProfile(
        truth=truth,
        detected_relation=relation,
        admitted_relations=admitted,
        scored_relations=admitted,
    )


def evaluate_primary_direction_method_condition(
    truth: PrimaryDirectionMethodTruth,
) -> PrimaryDirectionMethodConditionProfile:
    return PrimaryDirectionMethodConditionProfile(
        truth=truth,
        classification=classify_primary_direction_method(truth),
        relation_profile=evaluate_primary_direction_method_relations(truth),
        state={
            PrimaryDirectionMethod.PLACIDUS_MUNDANE: PrimaryDirectionMethodConditionState.MUNDANE_SEMI_ARC_GROUNDED,
            PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC: PrimaryDirectionMethodConditionState.CLASSIC_SEMI_ARC_GROUNDED,
        }[truth.method],
    )


def evaluate_primary_direction_methods_aggregate(
    truths: Iterable[PrimaryDirectionMethodTruth],
) -> PrimaryDirectionMethodsAggregateProfile:
    profiles = tuple(evaluate_primary_direction_method_condition(truth) for truth in truths)
    if not profiles:
        raise ValueError("evaluate_primary_direction_methods_aggregate requires at least one truth")
    return PrimaryDirectionMethodsAggregateProfile(
        profiles=profiles,
        total_profiles=len(profiles),
        mundane_count=len(profiles),
        semi_arc_count=len(profiles),
    )


def evaluate_primary_direction_methods_network(
    truths: Iterable[PrimaryDirectionMethodTruth],
) -> PrimaryDirectionMethodsNetworkProfile:
    truth_tuple = tuple(truths)
    if not truth_tuple:
        raise ValueError("evaluate_primary_direction_methods_network requires at least one truth")
    counts: dict[PrimaryDirectionMethod, int] = {}
    for truth in truth_tuple:
        counts[truth.method] = counts.get(truth.method, 0) + 1
    nodes = tuple(
        sorted(
            (
                PrimaryDirectionMethodsNetworkNode(method=method, count=count)
                for method, count in counts.items()
            ),
            key=lambda node: node.method.value,
        )
    )
    edge_counts: dict[tuple[PrimaryDirectionMethod, PrimaryDirectionMethod], int] = {}
    for left, right in zip(truth_tuple, truth_tuple[1:]):
        if left.method == right.method:
            continue
        key = (left.method, right.method)
        edge_counts[key] = edge_counts.get(key, 0) + 1
    edges = tuple(
        sorted(
            (
                PrimaryDirectionMethodsNetworkEdge(from_method=from_method, to_method=to_method, count=count)
                for (from_method, to_method), count in edge_counts.items()
            ),
            key=lambda edge: (edge.from_method.value, edge.to_method.value),
        )
    )
    dominant = max(nodes, key=lambda node: (node.count, node.method.value)).method
    participating = {edge.from_method for edge in edges} | {edge.to_method for edge in edges}
    isolated = tuple(sorted((node.method for node in nodes if node.method not in participating), key=lambda m: m.value))
    return PrimaryDirectionMethodsNetworkProfile(
        nodes=nodes,
        edges=edges,
        dominant_method=dominant,
        isolated_methods=isolated,
    )
