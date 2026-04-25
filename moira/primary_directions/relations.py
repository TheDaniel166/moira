"""
Moira -- primary_directions/relations.py
Standalone relation-doctrine owner for the primary-directions subsystem.

Boundary
--------
Owns the doctrinal identity, classification, and admission policy for the
relation classes that may count as primary-direction perfections.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

__all__ = [
    "PrimaryDirectionRelationalKind",
    "PrimaryDirectionRelationalMode",
    "PrimaryDirectionRelationalConditionState",
    "PrimaryDirectionRelationPolicy",
    "PrimaryDirectionRelationalTruth",
    "PrimaryDirectionRelationalClassification",
    "PrimaryDirectionRelationalRelation",
    "PrimaryDirectionRelationalRelationProfile",
    "PrimaryDirectionRelationalConditionProfile",
    "PrimaryDirectionRelationsAggregateProfile",
    "PrimaryDirectionRelationsNetworkNode",
    "PrimaryDirectionRelationsNetworkEdge",
    "PrimaryDirectionRelationsNetworkProfile",
    "default_positional_relation_policy",
    "zodiacal_aspect_relation_policy",
    "antiscia_relation_policy",
    "ptolemaic_parallel_relation_policy",
    "placidian_rapt_parallel_relation_policy",
    "primary_direction_relational_truth",
    "classify_primary_direction_relation",
    "relate_primary_direction_relation",
    "evaluate_primary_direction_relation_relations",
    "evaluate_primary_direction_relation_condition",
    "evaluate_primary_direction_relations_aggregate",
    "evaluate_primary_direction_relations_network",
]


class PrimaryDirectionRelationalKind(StrEnum):
    CONJUNCTION = "conjunction"
    OPPOSITION = "opposition"
    ZODIACAL_ASPECT = "zodiacal_aspect"
    ANTISCION = "antiscion"
    CONTRA_ANTISCION = "contra_antiscion"
    PARALLEL = "parallel"
    CONTRA_PARALLEL = "contra_parallel"
    RAPT_PARALLEL = "rapt_parallel"


class PrimaryDirectionRelationalMode(StrEnum):
    POSITIONAL = "positional"
    DECLINATIONAL = "declinational"


class PrimaryDirectionRelationalConditionState(StrEnum):
    POSITIONAL_ADMITTED = "positional_admitted"
    DECLINATIONAL_ADMITTED = "declinational_admitted"


@dataclass(frozen=True, slots=True)
class PrimaryDirectionRelationPolicy:
    admitted_kinds: frozenset[PrimaryDirectionRelationalKind] = frozenset(
        {
            PrimaryDirectionRelationalKind.CONJUNCTION,
            PrimaryDirectionRelationalKind.OPPOSITION,
            PrimaryDirectionRelationalKind.ZODIACAL_ASPECT,
        }
    )

    def __post_init__(self) -> None:
        if not self.admitted_kinds:
            raise ValueError("PrimaryDirectionRelationPolicy invariant failed: admitted_kinds may not be empty")
        if not set(self.admitted_kinds) <= set(PrimaryDirectionRelationalKind):
            raise ValueError("Unsupported primary direction relation kinds")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionRelationalTruth:
    kind: PrimaryDirectionRelationalKind
    mode: PrimaryDirectionRelationalMode
    derived_point_realizable: bool

    def __post_init__(self) -> None:
        expected = {
            PrimaryDirectionRelationalKind.CONJUNCTION: (
                PrimaryDirectionRelationalMode.POSITIONAL,
                False,
            ),
            PrimaryDirectionRelationalKind.OPPOSITION: (
                PrimaryDirectionRelationalMode.POSITIONAL,
                False,
            ),
            PrimaryDirectionRelationalKind.ZODIACAL_ASPECT: (
                PrimaryDirectionRelationalMode.POSITIONAL,
                True,
            ),
            PrimaryDirectionRelationalKind.ANTISCION: (
                PrimaryDirectionRelationalMode.POSITIONAL,
                True,
            ),
            PrimaryDirectionRelationalKind.CONTRA_ANTISCION: (
                PrimaryDirectionRelationalMode.POSITIONAL,
                True,
            ),
            PrimaryDirectionRelationalKind.PARALLEL: (
                PrimaryDirectionRelationalMode.DECLINATIONAL,
                True,
            ),
            PrimaryDirectionRelationalKind.CONTRA_PARALLEL: (
                PrimaryDirectionRelationalMode.DECLINATIONAL,
                True,
            ),
            PrimaryDirectionRelationalKind.RAPT_PARALLEL: (
                PrimaryDirectionRelationalMode.DECLINATIONAL,
                False,
            ),
        }.get(self.kind)
        if expected is None or (self.mode, self.derived_point_realizable) != expected:
            raise ValueError(
                "PrimaryDirectionRelationalTruth invariant failed: current admitted relation traits mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionRelationalClassification:
    truth: PrimaryDirectionRelationalTruth
    positional: bool
    declinational: bool

    def __post_init__(self) -> None:
        expected = (
            self.truth.mode is PrimaryDirectionRelationalMode.POSITIONAL,
            self.truth.mode is PrimaryDirectionRelationalMode.DECLINATIONAL,
        )
        if (self.positional, self.declinational) != expected:
            raise ValueError(
                "PrimaryDirectionRelationalClassification invariant failed: classification mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionRelationalRelation:
    truth: PrimaryDirectionRelationalTruth
    relation_kind: PrimaryDirectionRelationalKind

    def __post_init__(self) -> None:
        if self.relation_kind is not self.truth.kind:
            raise ValueError(
                "PrimaryDirectionRelationalRelation invariant failed: relation_kind must match truth.kind"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionRelationalRelationProfile:
    truth: PrimaryDirectionRelationalTruth
    detected_relation: PrimaryDirectionRelationalRelation
    admitted_relations: tuple[PrimaryDirectionRelationalRelation, ...]
    scored_relations: tuple[PrimaryDirectionRelationalRelation, ...]

    def __post_init__(self) -> None:
        if self.detected_relation.truth != self.truth:
            raise ValueError(
                "PrimaryDirectionRelationalRelationProfile invariant failed: detected relation truth mismatch"
            )
        if self.detected_relation not in self.admitted_relations:
            raise ValueError(
                "PrimaryDirectionRelationalRelationProfile invariant failed: detected relation must be admitted"
            )
        for relation in self.scored_relations:
            if relation not in self.admitted_relations:
                raise ValueError(
                    "PrimaryDirectionRelationalRelationProfile invariant failed: scored relation must be admitted"
                )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionRelationalConditionProfile:
    truth: PrimaryDirectionRelationalTruth
    classification: PrimaryDirectionRelationalClassification
    relation_profile: PrimaryDirectionRelationalRelationProfile
    state: PrimaryDirectionRelationalConditionState

    def __post_init__(self) -> None:
        if self.classification.truth != self.truth:
            raise ValueError(
                "PrimaryDirectionRelationalConditionProfile invariant failed: classification truth mismatch"
            )
        if self.relation_profile.truth != self.truth:
            raise ValueError(
                "PrimaryDirectionRelationalConditionProfile invariant failed: relation truth mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionRelationsAggregateProfile:
    profiles: tuple[PrimaryDirectionRelationalConditionProfile, ...]
    total_profiles: int
    positional_count: int
    declinational_count: int

    def __post_init__(self) -> None:
        if not self.profiles:
            raise ValueError("PrimaryDirectionRelationsAggregateProfile requires at least one profile")
        if self.total_profiles != len(self.profiles):
            raise ValueError(
                "PrimaryDirectionRelationsAggregateProfile invariant failed: total_profiles mismatch"
            )
        if self.positional_count != sum(1 for profile in self.profiles if profile.classification.positional):
            raise ValueError(
                "PrimaryDirectionRelationsAggregateProfile invariant failed: positional_count mismatch"
            )
        if self.declinational_count != sum(
            1 for profile in self.profiles if profile.classification.declinational
        ):
            raise ValueError(
                "PrimaryDirectionRelationsAggregateProfile invariant failed: declinational_count mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionRelationsNetworkNode:
    kind: PrimaryDirectionRelationalKind
    count: int

    def __post_init__(self) -> None:
        if self.count <= 0:
            raise ValueError("PrimaryDirectionRelationsNetworkNode invariant failed: count must be positive")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionRelationsNetworkEdge:
    from_kind: PrimaryDirectionRelationalKind
    to_kind: PrimaryDirectionRelationalKind
    count: int

    def __post_init__(self) -> None:
        if self.from_kind == self.to_kind:
            raise ValueError(
                "PrimaryDirectionRelationsNetworkEdge invariant failed: self-edges are not admitted"
            )
        if self.count <= 0:
            raise ValueError("PrimaryDirectionRelationsNetworkEdge invariant failed: count must be positive")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionRelationsNetworkProfile:
    nodes: tuple[PrimaryDirectionRelationsNetworkNode, ...]
    edges: tuple[PrimaryDirectionRelationsNetworkEdge, ...]
    dominant_kind: PrimaryDirectionRelationalKind
    isolated_kinds: tuple[PrimaryDirectionRelationalKind, ...]

    def __post_init__(self) -> None:
        if not self.nodes:
            raise ValueError("PrimaryDirectionRelationsNetworkProfile requires at least one node")
        kinds = [node.kind for node in self.nodes]
        if len(set(kinds)) != len(kinds):
            raise ValueError(
                "PrimaryDirectionRelationsNetworkProfile invariant failed: duplicate nodes"
            )


def primary_direction_relational_truth(
    kind: PrimaryDirectionRelationalKind = PrimaryDirectionRelationalKind.CONJUNCTION,
    *,
    policy: PrimaryDirectionRelationPolicy | None = None,
) -> PrimaryDirectionRelationalTruth:
    resolved_kind = kind if policy is None else kind
    return PrimaryDirectionRelationalTruth(
        kind=resolved_kind,
        mode=(
            PrimaryDirectionRelationalMode.DECLINATIONAL
            if resolved_kind in (
                PrimaryDirectionRelationalKind.PARALLEL,
                PrimaryDirectionRelationalKind.CONTRA_PARALLEL,
                PrimaryDirectionRelationalKind.RAPT_PARALLEL,
            )
            else PrimaryDirectionRelationalMode.POSITIONAL
        ),
        derived_point_realizable=(
            resolved_kind
            in (
                PrimaryDirectionRelationalKind.ZODIACAL_ASPECT,
                PrimaryDirectionRelationalKind.ANTISCION,
                PrimaryDirectionRelationalKind.CONTRA_ANTISCION,
                PrimaryDirectionRelationalKind.PARALLEL,
                PrimaryDirectionRelationalKind.CONTRA_PARALLEL,
            )
        ),
    )


def default_positional_relation_policy() -> PrimaryDirectionRelationPolicy:
    return PrimaryDirectionRelationPolicy(
        frozenset(
            {
                PrimaryDirectionRelationalKind.CONJUNCTION,
                PrimaryDirectionRelationalKind.OPPOSITION,
            }
        )
    )


def zodiacal_aspect_relation_policy() -> PrimaryDirectionRelationPolicy:
    return PrimaryDirectionRelationPolicy(
        frozenset(
            {
                PrimaryDirectionRelationalKind.CONJUNCTION,
                PrimaryDirectionRelationalKind.OPPOSITION,
                PrimaryDirectionRelationalKind.ZODIACAL_ASPECT,
            }
        )
    )


def antiscia_relation_policy() -> PrimaryDirectionRelationPolicy:
    return PrimaryDirectionRelationPolicy(
        frozenset(
            {
                PrimaryDirectionRelationalKind.CONJUNCTION,
                PrimaryDirectionRelationalKind.OPPOSITION,
                PrimaryDirectionRelationalKind.ANTISCION,
                PrimaryDirectionRelationalKind.CONTRA_ANTISCION,
            }
        )
    )


def ptolemaic_parallel_relation_policy() -> PrimaryDirectionRelationPolicy:
    return PrimaryDirectionRelationPolicy(
        frozenset(
            {
                PrimaryDirectionRelationalKind.CONJUNCTION,
                PrimaryDirectionRelationalKind.OPPOSITION,
                PrimaryDirectionRelationalKind.ZODIACAL_ASPECT,
                PrimaryDirectionRelationalKind.PARALLEL,
                PrimaryDirectionRelationalKind.CONTRA_PARALLEL,
            }
        )
    )


def placidian_rapt_parallel_relation_policy() -> PrimaryDirectionRelationPolicy:
    return PrimaryDirectionRelationPolicy(
        frozenset(
            {
                PrimaryDirectionRelationalKind.RAPT_PARALLEL,
            }
        )
    )


def classify_primary_direction_relation(
    truth: PrimaryDirectionRelationalTruth,
) -> PrimaryDirectionRelationalClassification:
    return PrimaryDirectionRelationalClassification(
        truth=truth,
        positional=truth.mode is PrimaryDirectionRelationalMode.POSITIONAL,
        declinational=truth.mode is PrimaryDirectionRelationalMode.DECLINATIONAL,
    )


def relate_primary_direction_relation(
    truth: PrimaryDirectionRelationalTruth,
) -> PrimaryDirectionRelationalRelation:
    return PrimaryDirectionRelationalRelation(
        truth=truth,
        relation_kind=truth.kind,
    )


def evaluate_primary_direction_relation_relations(
    truth: PrimaryDirectionRelationalTruth,
    *,
    policy: PrimaryDirectionRelationPolicy | None = None,
) -> PrimaryDirectionRelationalRelationProfile:
    resolved_policy = policy if policy is not None else PrimaryDirectionRelationPolicy()
    relation = relate_primary_direction_relation(truth)
    admitted = (relation,)
    scored = admitted if relation.relation_kind in resolved_policy.admitted_kinds else ()
    return PrimaryDirectionRelationalRelationProfile(
        truth=truth,
        detected_relation=relation,
        admitted_relations=admitted,
        scored_relations=scored,
    )


def evaluate_primary_direction_relation_condition(
    truth: PrimaryDirectionRelationalTruth,
    *,
    policy: PrimaryDirectionRelationPolicy | None = None,
) -> PrimaryDirectionRelationalConditionProfile:
    return PrimaryDirectionRelationalConditionProfile(
        truth=truth,
        classification=classify_primary_direction_relation(truth),
        relation_profile=evaluate_primary_direction_relation_relations(truth, policy=policy),
        state=(
            PrimaryDirectionRelationalConditionState.DECLINATIONAL_ADMITTED
            if truth.mode is PrimaryDirectionRelationalMode.DECLINATIONAL
            else PrimaryDirectionRelationalConditionState.POSITIONAL_ADMITTED
        ),
    )


def evaluate_primary_direction_relations_aggregate(
    truths: Iterable[PrimaryDirectionRelationalTruth],
    *,
    policy: PrimaryDirectionRelationPolicy | None = None,
) -> PrimaryDirectionRelationsAggregateProfile:
    profiles = tuple(evaluate_primary_direction_relation_condition(truth, policy=policy) for truth in truths)
    if not profiles:
        raise ValueError("evaluate_primary_direction_relations_aggregate requires at least one truth")
    return PrimaryDirectionRelationsAggregateProfile(
        profiles=profiles,
        total_profiles=len(profiles),
        positional_count=sum(1 for profile in profiles if profile.classification.positional),
        declinational_count=sum(1 for profile in profiles if profile.classification.declinational),
    )


def evaluate_primary_direction_relations_network(
    truths: Iterable[PrimaryDirectionRelationalTruth],
) -> PrimaryDirectionRelationsNetworkProfile:
    truth_tuple = tuple(truths)
    if not truth_tuple:
        raise ValueError("evaluate_primary_direction_relations_network requires at least one truth")
    counts: dict[PrimaryDirectionRelationalKind, int] = {}
    for truth in truth_tuple:
        counts[truth.kind] = counts.get(truth.kind, 0) + 1
    nodes = tuple(
        sorted(
            (
                PrimaryDirectionRelationsNetworkNode(kind=kind, count=count)
                for kind, count in counts.items()
            ),
            key=lambda node: node.kind.value,
        )
    )
    edge_counts: dict[tuple[PrimaryDirectionRelationalKind, PrimaryDirectionRelationalKind], int] = {}
    for left, right in zip(truth_tuple, truth_tuple[1:]):
        if left.kind == right.kind:
            continue
        key = (left.kind, right.kind)
        edge_counts[key] = edge_counts.get(key, 0) + 1
    edges = tuple(
        sorted(
            (
                PrimaryDirectionRelationsNetworkEdge(from_kind=from_kind, to_kind=to_kind, count=count)
                for (from_kind, to_kind), count in edge_counts.items()
            ),
            key=lambda edge: (edge.from_kind.value, edge.to_kind.value),
        )
    )
    dominant = max(nodes, key=lambda node: (node.count, node.kind.value)).kind
    participating = {edge.from_kind for edge in edges} | {edge.to_kind for edge in edges}
    isolated = tuple(sorted((node.kind for node in nodes if node.kind not in participating), key=lambda k: k.value))
    return PrimaryDirectionRelationsNetworkProfile(
        nodes=nodes,
        edges=edges,
        dominant_kind=dominant,
        isolated_kinds=isolated,
    )
