"""
Moira -- primary_directions/converse.py
Standalone converse-doctrine owner for the primary-directions subsystem.

Boundary
--------
Owns the doctrinal identity, admission policy, and hardened interpretation of
currently admitted primary-direction converse modes. This module is intentionally
orthogonal to geometry method and time-key conversion.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

__all__ = [
    "PrimaryDirectionConverseDoctrine",
    "PrimaryDirectionConverseRelationKind",
    "PrimaryDirectionConverseConditionState",
    "PrimaryDirectionConversePolicy",
    "PrimaryDirectionConverseTruth",
    "PrimaryDirectionConverseClassification",
    "PrimaryDirectionConverseRelation",
    "PrimaryDirectionConverseRelationProfile",
    "PrimaryDirectionConverseConditionProfile",
    "PrimaryDirectionConverseAggregateProfile",
    "PrimaryDirectionConverseNetworkNode",
    "PrimaryDirectionConverseNetworkEdge",
    "PrimaryDirectionConverseNetworkProfile",
    "primary_direction_converse_truth",
    "classify_primary_direction_converse",
    "relate_primary_direction_converse",
    "evaluate_primary_direction_converse_relations",
    "evaluate_primary_direction_converse_condition",
    "evaluate_primary_direction_converse_aggregate",
    "evaluate_primary_direction_converse_network",
]


class PrimaryDirectionConverseDoctrine(StrEnum):
    DIRECT_ONLY = "direct_only"
    TRADITIONAL_CONVERSE = "traditional_converse"


class PrimaryDirectionConverseRelationKind(StrEnum):
    FORWARD_ONLY = "forward_only"
    DIRECT_AND_TRADITIONAL_CONVERSE = "direct_and_traditional_converse"


class PrimaryDirectionConverseConditionState(StrEnum):
    DIRECT_ONLY = "direct_only"
    DIRECT_AND_CONVERSE = "direct_and_converse"


@dataclass(frozen=True, slots=True)
class PrimaryDirectionConversePolicy:
    doctrine: PrimaryDirectionConverseDoctrine = PrimaryDirectionConverseDoctrine.TRADITIONAL_CONVERSE

    def __post_init__(self) -> None:
        if not isinstance(self.doctrine, PrimaryDirectionConverseDoctrine):
            raise ValueError(f"Unsupported primary direction converse doctrine: {self.doctrine}")

    @property
    def include_converse(self) -> bool:
        return self.doctrine is PrimaryDirectionConverseDoctrine.TRADITIONAL_CONVERSE


@dataclass(frozen=True, slots=True)
class PrimaryDirectionConverseTruth:
    doctrine: PrimaryDirectionConverseDoctrine
    includes_direct: bool
    includes_converse: bool
    motion_count: int

    def __post_init__(self) -> None:
        if not self.includes_direct:
            raise ValueError(
                "PrimaryDirectionConverseTruth invariant failed: direct motion must always be admitted"
            )
        expected_include_converse = (
            self.doctrine is PrimaryDirectionConverseDoctrine.TRADITIONAL_CONVERSE
        )
        if self.includes_converse is not expected_include_converse:
            raise ValueError(
                "PrimaryDirectionConverseTruth invariant failed: converse admission mismatch"
            )
        expected_count = 2 if self.includes_converse else 1
        if self.motion_count != expected_count:
            raise ValueError(
                "PrimaryDirectionConverseTruth invariant failed: motion_count mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionConverseClassification:
    truth: PrimaryDirectionConverseTruth
    direct_only: bool
    admits_converse: bool

    def __post_init__(self) -> None:
        if self.direct_only == self.admits_converse:
            raise ValueError(
                "PrimaryDirectionConverseClassification invariant failed: direct_only/admit_converse mismatch"
            )
        if self.direct_only != (self.truth.doctrine is PrimaryDirectionConverseDoctrine.DIRECT_ONLY):
            raise ValueError(
                "PrimaryDirectionConverseClassification invariant failed: direct_only mismatch"
            )
        if self.admits_converse != self.truth.includes_converse:
            raise ValueError(
                "PrimaryDirectionConverseClassification invariant failed: admits_converse mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionConverseRelation:
    truth: PrimaryDirectionConverseTruth
    relation_kind: PrimaryDirectionConverseRelationKind
    admitted_motions: tuple[str, ...]

    def __post_init__(self) -> None:
        expected_kind = (
            PrimaryDirectionConverseRelationKind.DIRECT_AND_TRADITIONAL_CONVERSE
            if self.truth.includes_converse
            else PrimaryDirectionConverseRelationKind.FORWARD_ONLY
        )
        if self.relation_kind is not expected_kind:
            raise ValueError(
                "PrimaryDirectionConverseRelation invariant failed: relation_kind mismatch"
            )
        expected_motions = (
            ("direct", "converse")
            if self.truth.includes_converse
            else ("direct",)
        )
        if self.admitted_motions != expected_motions:
            raise ValueError(
                "PrimaryDirectionConverseRelation invariant failed: admitted_motions mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionConverseRelationProfile:
    truth: PrimaryDirectionConverseTruth
    detected_relation: PrimaryDirectionConverseRelation
    admitted_relations: tuple[PrimaryDirectionConverseRelation, ...]
    scored_relations: tuple[PrimaryDirectionConverseRelation, ...]

    def __post_init__(self) -> None:
        if self.detected_relation.truth != self.truth:
            raise ValueError(
                "PrimaryDirectionConverseRelationProfile invariant failed: detected relation truth mismatch"
            )
        if self.detected_relation not in self.admitted_relations:
            raise ValueError(
                "PrimaryDirectionConverseRelationProfile invariant failed: detected relation must be admitted"
            )
        for relation in self.scored_relations:
            if relation not in self.admitted_relations:
                raise ValueError(
                    "PrimaryDirectionConverseRelationProfile invariant failed: scored relations must be admitted"
                )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionConverseConditionProfile:
    truth: PrimaryDirectionConverseTruth
    classification: PrimaryDirectionConverseClassification
    relation_profile: PrimaryDirectionConverseRelationProfile
    state: PrimaryDirectionConverseConditionState

    def __post_init__(self) -> None:
        if self.classification.truth != self.truth:
            raise ValueError(
                "PrimaryDirectionConverseConditionProfile invariant failed: classification truth mismatch"
            )
        if self.relation_profile.truth != self.truth:
            raise ValueError(
                "PrimaryDirectionConverseConditionProfile invariant failed: relation truth mismatch"
            )
        expected_state = (
            PrimaryDirectionConverseConditionState.DIRECT_AND_CONVERSE
            if self.truth.includes_converse
            else PrimaryDirectionConverseConditionState.DIRECT_ONLY
        )
        if self.state is not expected_state:
            raise ValueError(
                "PrimaryDirectionConverseConditionProfile invariant failed: state mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionConverseAggregateProfile:
    profiles: tuple[PrimaryDirectionConverseConditionProfile, ...]
    total_profiles: int
    converse_enabled_count: int
    direct_only_count: int

    def __post_init__(self) -> None:
        if not self.profiles:
            raise ValueError("PrimaryDirectionConverseAggregateProfile requires at least one profile")
        if self.total_profiles != len(self.profiles):
            raise ValueError(
                "PrimaryDirectionConverseAggregateProfile invariant failed: total_profiles mismatch"
            )
        if self.converse_enabled_count != sum(1 for p in self.profiles if p.truth.includes_converse):
            raise ValueError(
                "PrimaryDirectionConverseAggregateProfile invariant failed: converse_enabled_count mismatch"
            )
        if self.direct_only_count != sum(1 for p in self.profiles if not p.truth.includes_converse):
            raise ValueError(
                "PrimaryDirectionConverseAggregateProfile invariant failed: direct_only_count mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionConverseNetworkNode:
    doctrine: PrimaryDirectionConverseDoctrine
    count: int

    def __post_init__(self) -> None:
        if self.count <= 0:
            raise ValueError("PrimaryDirectionConverseNetworkNode invariant failed: count must be positive")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionConverseNetworkEdge:
    from_doctrine: PrimaryDirectionConverseDoctrine
    to_doctrine: PrimaryDirectionConverseDoctrine
    count: int

    def __post_init__(self) -> None:
        if self.from_doctrine == self.to_doctrine:
            raise ValueError(
                "PrimaryDirectionConverseNetworkEdge invariant failed: self-edges are not admitted"
            )
        if self.count <= 0:
            raise ValueError("PrimaryDirectionConverseNetworkEdge invariant failed: count must be positive")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionConverseNetworkProfile:
    nodes: tuple[PrimaryDirectionConverseNetworkNode, ...]
    edges: tuple[PrimaryDirectionConverseNetworkEdge, ...]
    dominant_doctrine: PrimaryDirectionConverseDoctrine
    isolated_doctrines: tuple[PrimaryDirectionConverseDoctrine, ...]

    def __post_init__(self) -> None:
        if not self.nodes:
            raise ValueError("PrimaryDirectionConverseNetworkProfile requires at least one node")
        doctrines = [node.doctrine for node in self.nodes]
        if len(set(doctrines)) != len(doctrines):
            raise ValueError(
                "PrimaryDirectionConverseNetworkProfile invariant failed: duplicate nodes"
            )
        node_set = set(doctrines)
        for edge in self.edges:
            if edge.from_doctrine not in node_set or edge.to_doctrine not in node_set:
                raise ValueError(
                    "PrimaryDirectionConverseNetworkProfile invariant failed: dangling edge"
                )
        dominant = max(self.nodes, key=lambda node: (node.count, node.doctrine.value)).doctrine
        if self.dominant_doctrine is not dominant:
            raise ValueError(
                "PrimaryDirectionConverseNetworkProfile invariant failed: dominant_doctrine mismatch"
            )
        if set(self.isolated_doctrines) - node_set:
            raise ValueError(
                "PrimaryDirectionConverseNetworkProfile invariant failed: isolated_doctrines contains unknown node"
            )


def primary_direction_converse_truth(
    doctrine: PrimaryDirectionConverseDoctrine = PrimaryDirectionConverseDoctrine.TRADITIONAL_CONVERSE,
    *,
    policy: PrimaryDirectionConversePolicy | None = None,
) -> PrimaryDirectionConverseTruth:
    resolved_policy = policy if policy is not None else PrimaryDirectionConversePolicy(doctrine)
    includes_converse = resolved_policy.include_converse
    return PrimaryDirectionConverseTruth(
        doctrine=resolved_policy.doctrine,
        includes_direct=True,
        includes_converse=includes_converse,
        motion_count=2 if includes_converse else 1,
    )


def classify_primary_direction_converse(
    truth: PrimaryDirectionConverseTruth,
) -> PrimaryDirectionConverseClassification:
    return PrimaryDirectionConverseClassification(
        truth=truth,
        direct_only=not truth.includes_converse,
        admits_converse=truth.includes_converse,
    )


def relate_primary_direction_converse(
    truth: PrimaryDirectionConverseTruth,
) -> PrimaryDirectionConverseRelation:
    return PrimaryDirectionConverseRelation(
        truth=truth,
        relation_kind=(
            PrimaryDirectionConverseRelationKind.DIRECT_AND_TRADITIONAL_CONVERSE
            if truth.includes_converse
            else PrimaryDirectionConverseRelationKind.FORWARD_ONLY
        ),
        admitted_motions=(
            ("direct", "converse")
            if truth.includes_converse
            else ("direct",)
        ),
    )


def evaluate_primary_direction_converse_relations(
    truth: PrimaryDirectionConverseTruth,
) -> PrimaryDirectionConverseRelationProfile:
    relation = relate_primary_direction_converse(truth)
    admitted = (relation,)
    return PrimaryDirectionConverseRelationProfile(
        truth=truth,
        detected_relation=relation,
        admitted_relations=admitted,
        scored_relations=admitted,
    )


def evaluate_primary_direction_converse_condition(
    truth: PrimaryDirectionConverseTruth,
) -> PrimaryDirectionConverseConditionProfile:
    return PrimaryDirectionConverseConditionProfile(
        truth=truth,
        classification=classify_primary_direction_converse(truth),
        relation_profile=evaluate_primary_direction_converse_relations(truth),
        state=(
            PrimaryDirectionConverseConditionState.DIRECT_AND_CONVERSE
            if truth.includes_converse
            else PrimaryDirectionConverseConditionState.DIRECT_ONLY
        ),
    )


def evaluate_primary_direction_converse_aggregate(
    truths: Iterable[PrimaryDirectionConverseTruth],
) -> PrimaryDirectionConverseAggregateProfile:
    profiles = tuple(evaluate_primary_direction_converse_condition(truth) for truth in truths)
    if not profiles:
        raise ValueError("evaluate_primary_direction_converse_aggregate requires at least one truth")
    return PrimaryDirectionConverseAggregateProfile(
        profiles=profiles,
        total_profiles=len(profiles),
        converse_enabled_count=sum(1 for p in profiles if p.truth.includes_converse),
        direct_only_count=sum(1 for p in profiles if not p.truth.includes_converse),
    )


def evaluate_primary_direction_converse_network(
    truths: Iterable[PrimaryDirectionConverseTruth],
) -> PrimaryDirectionConverseNetworkProfile:
    truth_tuple = tuple(truths)
    if not truth_tuple:
        raise ValueError("evaluate_primary_direction_converse_network requires at least one truth")

    counts: dict[PrimaryDirectionConverseDoctrine, int] = {}
    for truth in truth_tuple:
        counts[truth.doctrine] = counts.get(truth.doctrine, 0) + 1

    nodes = tuple(
        sorted(
            (
                PrimaryDirectionConverseNetworkNode(doctrine=doctrine, count=count)
                for doctrine, count in counts.items()
            ),
            key=lambda node: node.doctrine.value,
        )
    )

    edge_counts: dict[tuple[PrimaryDirectionConverseDoctrine, PrimaryDirectionConverseDoctrine], int] = {}
    for left, right in zip(truth_tuple, truth_tuple[1:]):
        if left.doctrine == right.doctrine:
            continue
        key = (left.doctrine, right.doctrine)
        edge_counts[key] = edge_counts.get(key, 0) + 1

    edges = tuple(
        sorted(
            (
                PrimaryDirectionConverseNetworkEdge(
                    from_doctrine=from_doctrine,
                    to_doctrine=to_doctrine,
                    count=count,
                )
                for (from_doctrine, to_doctrine), count in edge_counts.items()
            ),
            key=lambda edge: (edge.from_doctrine.value, edge.to_doctrine.value),
        )
    )

    dominant = max(nodes, key=lambda node: (node.count, node.doctrine.value)).doctrine
    participating = {edge.from_doctrine for edge in edges} | {edge.to_doctrine for edge in edges}
    isolated = tuple(
        sorted((node.doctrine for node in nodes if node.doctrine not in participating), key=lambda d: d.value)
    )
    return PrimaryDirectionConverseNetworkProfile(
        nodes=nodes,
        edges=edges,
        dominant_doctrine=dominant,
        isolated_doctrines=isolated,
    )
