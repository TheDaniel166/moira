"""
Moira -- primary_direction_targets.py
Standalone primary-direction target-doctrine subsystem.

Boundary
--------
Owns the doctrinal identity, classification, and admission policy for the kinds
of entities currently admitted as primary-direction promissors and significators.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Iterable

from .constants import Body

__all__ = [
    "PrimaryDirectionTargetClass",
    "PrimaryDirectionTargetRelationKind",
    "PrimaryDirectionTargetConditionState",
    "PrimaryDirectionTargetPolicy",
    "PrimaryDirectionTargetTruth",
    "PrimaryDirectionTargetClassification",
    "PrimaryDirectionTargetRelation",
    "PrimaryDirectionTargetRelationProfile",
    "PrimaryDirectionTargetConditionProfile",
    "PrimaryDirectionTargetsAggregateProfile",
    "PrimaryDirectionTargetsNetworkNode",
    "PrimaryDirectionTargetsNetworkEdge",
    "PrimaryDirectionTargetsNetworkProfile",
    "primary_direction_target_truth",
    "classify_primary_direction_target",
    "relate_primary_direction_target",
    "evaluate_primary_direction_target_relations",
    "evaluate_primary_direction_target_condition",
    "evaluate_primary_direction_targets_aggregate",
    "evaluate_primary_direction_targets_network",
]


_ANGLE_NAMES = frozenset({"ASC", "MC", "DSC", "IC"})
_NODE_NAMES = frozenset(
    {
        Body.TRUE_NODE,
        Body.MEAN_NODE,
        Body.LILITH,
        Body.TRUE_LILITH,
        "North Node",
        "South Node",
        "Mean Node",
        "True Node",
    }
)
_PLANET_NAMES = frozenset(Body.ALL_PLANETS)


class PrimaryDirectionTargetClass(StrEnum):
    PLANET = "planet"
    NODE = "node"
    ANGLE = "angle"


class PrimaryDirectionTargetRelationKind(StrEnum):
    ADMITTED_AS_BOTH = "admitted_as_both"
    ADMITTED_AS_SIGNIFICATOR_ONLY = "admitted_as_significator_only"
    ADMITTED_AS_PROMISSOR_ONLY = "admitted_as_promissor_only"
    REJECTED = "rejected"


class PrimaryDirectionTargetConditionState(StrEnum):
    UNIVERSALLY_ADMITTED = "universally_admitted"
    SIGNIFICATOR_ONLY = "significator_only"
    PROMISSOR_ONLY = "promissor_only"
    NOT_ADMITTED = "not_admitted"


@dataclass(frozen=True, slots=True)
class PrimaryDirectionTargetPolicy:
    admitted_significator_classes: frozenset[PrimaryDirectionTargetClass] = field(
        default_factory=lambda: frozenset(
            {
                PrimaryDirectionTargetClass.PLANET,
                PrimaryDirectionTargetClass.NODE,
                PrimaryDirectionTargetClass.ANGLE,
            }
        )
    )
    admitted_promissor_classes: frozenset[PrimaryDirectionTargetClass] = field(
        default_factory=lambda: frozenset(
            {
                PrimaryDirectionTargetClass.PLANET,
                PrimaryDirectionTargetClass.NODE,
                PrimaryDirectionTargetClass.ANGLE,
            }
        )
    )

    def __post_init__(self) -> None:
        valid = set(PrimaryDirectionTargetClass)
        if not self.admitted_significator_classes or not self.admitted_promissor_classes:
            raise ValueError(
                "PrimaryDirectionTargetPolicy invariant failed: admitted target classes may not be empty"
            )
        if not set(self.admitted_significator_classes) <= valid:
            raise ValueError("Unsupported significator target classes")
        if not set(self.admitted_promissor_classes) <= valid:
            raise ValueError("Unsupported promissor target classes")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionTargetTruth:
    name: str
    target_class: PrimaryDirectionTargetClass

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("PrimaryDirectionTargetTruth requires a non-empty target name")
        if not isinstance(self.target_class, PrimaryDirectionTargetClass):
            raise ValueError(f"Unsupported primary-direction target class: {self.target_class}")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionTargetClassification:
    truth: PrimaryDirectionTargetTruth
    admitted_as_significator: bool
    admitted_as_promissor: bool

    def __post_init__(self) -> None:
        if not isinstance(self.truth.target_class, PrimaryDirectionTargetClass):
            raise ValueError(
                "PrimaryDirectionTargetClassification invariant failed: invalid truth target class"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionTargetRelation:
    truth: PrimaryDirectionTargetTruth
    relation_kind: PrimaryDirectionTargetRelationKind


@dataclass(frozen=True, slots=True)
class PrimaryDirectionTargetRelationProfile:
    truth: PrimaryDirectionTargetTruth
    detected_relation: PrimaryDirectionTargetRelation
    admitted_relations: tuple[PrimaryDirectionTargetRelation, ...]
    scored_relations: tuple[PrimaryDirectionTargetRelation, ...]

    def __post_init__(self) -> None:
        if self.detected_relation.truth != self.truth:
            raise ValueError(
                "PrimaryDirectionTargetRelationProfile invariant failed: detected relation truth mismatch"
            )
        if self.detected_relation not in self.admitted_relations:
            raise ValueError(
                "PrimaryDirectionTargetRelationProfile invariant failed: detected relation must be admitted"
            )
        for relation in self.scored_relations:
            if relation not in self.admitted_relations:
                raise ValueError(
                    "PrimaryDirectionTargetRelationProfile invariant failed: scored relation must be admitted"
                )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionTargetConditionProfile:
    truth: PrimaryDirectionTargetTruth
    classification: PrimaryDirectionTargetClassification
    relation_profile: PrimaryDirectionTargetRelationProfile
    state: PrimaryDirectionTargetConditionState

    def __post_init__(self) -> None:
        if self.classification.truth != self.truth:
            raise ValueError(
                "PrimaryDirectionTargetConditionProfile invariant failed: classification truth mismatch"
            )
        if self.relation_profile.truth != self.truth:
            raise ValueError(
                "PrimaryDirectionTargetConditionProfile invariant failed: relation truth mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionTargetsAggregateProfile:
    profiles: tuple[PrimaryDirectionTargetConditionProfile, ...]
    total_profiles: int
    planet_count: int
    node_count: int
    angle_count: int
    universally_admitted_count: int

    def __post_init__(self) -> None:
        if not self.profiles:
            raise ValueError("PrimaryDirectionTargetsAggregateProfile requires at least one profile")
        if self.total_profiles != len(self.profiles):
            raise ValueError(
                "PrimaryDirectionTargetsAggregateProfile invariant failed: total_profiles mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionTargetsNetworkNode:
    target_class: PrimaryDirectionTargetClass
    count: int

    def __post_init__(self) -> None:
        if self.count <= 0:
            raise ValueError("PrimaryDirectionTargetsNetworkNode invariant failed: count must be positive")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionTargetsNetworkEdge:
    from_class: PrimaryDirectionTargetClass
    to_class: PrimaryDirectionTargetClass
    count: int

    def __post_init__(self) -> None:
        if self.from_class == self.to_class:
            raise ValueError(
                "PrimaryDirectionTargetsNetworkEdge invariant failed: self-edges are not admitted"
            )
        if self.count <= 0:
            raise ValueError("PrimaryDirectionTargetsNetworkEdge invariant failed: count must be positive")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionTargetsNetworkProfile:
    nodes: tuple[PrimaryDirectionTargetsNetworkNode, ...]
    edges: tuple[PrimaryDirectionTargetsNetworkEdge, ...]
    dominant_class: PrimaryDirectionTargetClass
    isolated_classes: tuple[PrimaryDirectionTargetClass, ...]

    def __post_init__(self) -> None:
        if not self.nodes:
            raise ValueError("PrimaryDirectionTargetsNetworkProfile requires at least one node")
        classes = [node.target_class for node in self.nodes]
        if len(set(classes)) != len(classes):
            raise ValueError(
                "PrimaryDirectionTargetsNetworkProfile invariant failed: duplicate nodes"
            )


def _target_class_for_name(name: str) -> PrimaryDirectionTargetClass:
    if name in _ANGLE_NAMES:
        return PrimaryDirectionTargetClass.ANGLE
    if name in _PLANET_NAMES:
        return PrimaryDirectionTargetClass.PLANET
    if name in _NODE_NAMES or name.endswith("Node") or "Lilith" in name:
        return PrimaryDirectionTargetClass.NODE
    raise ValueError(f"Unsupported primary-direction target identity: {name}")


def _relation_kind(
    admitted_as_significator: bool,
    admitted_as_promissor: bool,
) -> PrimaryDirectionTargetRelationKind:
    if admitted_as_significator and admitted_as_promissor:
        return PrimaryDirectionTargetRelationKind.ADMITTED_AS_BOTH
    if admitted_as_significator:
        return PrimaryDirectionTargetRelationKind.ADMITTED_AS_SIGNIFICATOR_ONLY
    if admitted_as_promissor:
        return PrimaryDirectionTargetRelationKind.ADMITTED_AS_PROMISSOR_ONLY
    return PrimaryDirectionTargetRelationKind.REJECTED


def _condition_state(relation_kind: PrimaryDirectionTargetRelationKind) -> PrimaryDirectionTargetConditionState:
    return {
        PrimaryDirectionTargetRelationKind.ADMITTED_AS_BOTH: PrimaryDirectionTargetConditionState.UNIVERSALLY_ADMITTED,
        PrimaryDirectionTargetRelationKind.ADMITTED_AS_SIGNIFICATOR_ONLY: PrimaryDirectionTargetConditionState.SIGNIFICATOR_ONLY,
        PrimaryDirectionTargetRelationKind.ADMITTED_AS_PROMISSOR_ONLY: PrimaryDirectionTargetConditionState.PROMISSOR_ONLY,
        PrimaryDirectionTargetRelationKind.REJECTED: PrimaryDirectionTargetConditionState.NOT_ADMITTED,
    }[relation_kind]


def primary_direction_target_truth(name: str) -> PrimaryDirectionTargetTruth:
    return PrimaryDirectionTargetTruth(name=name, target_class=_target_class_for_name(name))


def classify_primary_direction_target(
    truth: PrimaryDirectionTargetTruth,
    *,
    policy: PrimaryDirectionTargetPolicy | None = None,
) -> PrimaryDirectionTargetClassification:
    resolved_policy = policy if policy is not None else PrimaryDirectionTargetPolicy()
    return PrimaryDirectionTargetClassification(
        truth=truth,
        admitted_as_significator=truth.target_class in resolved_policy.admitted_significator_classes,
        admitted_as_promissor=truth.target_class in resolved_policy.admitted_promissor_classes,
    )


def relate_primary_direction_target(
    truth: PrimaryDirectionTargetTruth,
    *,
    policy: PrimaryDirectionTargetPolicy | None = None,
) -> PrimaryDirectionTargetRelation:
    classification = classify_primary_direction_target(truth, policy=policy)
    return PrimaryDirectionTargetRelation(
        truth=truth,
        relation_kind=_relation_kind(
            classification.admitted_as_significator,
            classification.admitted_as_promissor,
        ),
    )


def evaluate_primary_direction_target_relations(
    truth: PrimaryDirectionTargetTruth,
    *,
    policy: PrimaryDirectionTargetPolicy | None = None,
) -> PrimaryDirectionTargetRelationProfile:
    relation = relate_primary_direction_target(truth, policy=policy)
    admitted = (relation,)
    scored = admitted if relation.relation_kind is not PrimaryDirectionTargetRelationKind.REJECTED else ()
    return PrimaryDirectionTargetRelationProfile(
        truth=truth,
        detected_relation=relation,
        admitted_relations=admitted,
        scored_relations=scored,
    )


def evaluate_primary_direction_target_condition(
    truth: PrimaryDirectionTargetTruth,
    *,
    policy: PrimaryDirectionTargetPolicy | None = None,
) -> PrimaryDirectionTargetConditionProfile:
    classification = classify_primary_direction_target(truth, policy=policy)
    relation_profile = evaluate_primary_direction_target_relations(truth, policy=policy)
    return PrimaryDirectionTargetConditionProfile(
        truth=truth,
        classification=classification,
        relation_profile=relation_profile,
        state=_condition_state(relation_profile.detected_relation.relation_kind),
    )


def evaluate_primary_direction_targets_aggregate(
    truths: Iterable[PrimaryDirectionTargetTruth],
    *,
    policy: PrimaryDirectionTargetPolicy | None = None,
) -> PrimaryDirectionTargetsAggregateProfile:
    profiles = tuple(evaluate_primary_direction_target_condition(truth, policy=policy) for truth in truths)
    if not profiles:
        raise ValueError("evaluate_primary_direction_targets_aggregate requires at least one truth")
    return PrimaryDirectionTargetsAggregateProfile(
        profiles=profiles,
        total_profiles=len(profiles),
        planet_count=sum(1 for p in profiles if p.truth.target_class is PrimaryDirectionTargetClass.PLANET),
        node_count=sum(1 for p in profiles if p.truth.target_class is PrimaryDirectionTargetClass.NODE),
        angle_count=sum(1 for p in profiles if p.truth.target_class is PrimaryDirectionTargetClass.ANGLE),
        universally_admitted_count=sum(
            1 for p in profiles if p.state is PrimaryDirectionTargetConditionState.UNIVERSALLY_ADMITTED
        ),
    )


def evaluate_primary_direction_targets_network(
    truths: Iterable[PrimaryDirectionTargetTruth],
    *,
    policy: PrimaryDirectionTargetPolicy | None = None,
) -> PrimaryDirectionTargetsNetworkProfile:
    truth_tuple = tuple(truths)
    if not truth_tuple:
        raise ValueError("evaluate_primary_direction_targets_network requires at least one truth")
    counts: dict[PrimaryDirectionTargetClass, int] = {}
    for truth in truth_tuple:
        counts[truth.target_class] = counts.get(truth.target_class, 0) + 1
    nodes = tuple(
        sorted(
            (
                PrimaryDirectionTargetsNetworkNode(target_class=target_class, count=count)
                for target_class, count in counts.items()
            ),
            key=lambda node: node.target_class.value,
        )
    )
    edge_counts: dict[tuple[PrimaryDirectionTargetClass, PrimaryDirectionTargetClass], int] = {}
    for left, right in zip(truth_tuple, truth_tuple[1:]):
        if left.target_class == right.target_class:
            continue
        key = (left.target_class, right.target_class)
        edge_counts[key] = edge_counts.get(key, 0) + 1
    edges = tuple(
        sorted(
            (
                PrimaryDirectionTargetsNetworkEdge(from_class=from_class, to_class=to_class, count=count)
                for (from_class, to_class), count in edge_counts.items()
            ),
            key=lambda edge: (edge.from_class.value, edge.to_class.value),
        )
    )
    dominant = max(nodes, key=lambda node: (node.count, node.target_class.value)).target_class
    participating = {edge.from_class for edge in edges} | {edge.to_class for edge in edges}
    isolated = tuple(sorted((node.target_class for node in nodes if node.target_class not in participating), key=lambda c: c.value))
    return PrimaryDirectionTargetsNetworkProfile(
        nodes=nodes,
        edges=edges,
        dominant_class=dominant,
        isolated_classes=isolated,
    )
