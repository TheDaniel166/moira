"""
Moira -- primary_directions/perfections.py
Standalone perfection-doctrine owner for the primary-directions subsystem.

Boundary
--------
Owns the doctrinal identity, classification, and hardened interpretation of
currently admitted perfection kinds in the primary-directions family.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

__all__ = [
    "PrimaryDirectionPerfectionKind",
    "PrimaryDirectionPerfectionMode",
    "PrimaryDirectionPerfectionConditionState",
    "PrimaryDirectionPerfectionPolicy",
    "PrimaryDirectionPerfectionTruth",
    "PrimaryDirectionPerfectionClassification",
    "PrimaryDirectionPerfectionRelation",
    "PrimaryDirectionPerfectionRelationProfile",
    "PrimaryDirectionPerfectionConditionProfile",
    "PrimaryDirectionPerfectionsAggregateProfile",
    "PrimaryDirectionPerfectionsNetworkNode",
    "PrimaryDirectionPerfectionsNetworkEdge",
    "PrimaryDirectionPerfectionsNetworkProfile",
    "primary_direction_perfection_truth",
    "classify_primary_direction_perfection",
    "relate_primary_direction_perfection",
    "evaluate_primary_direction_perfection_relations",
    "evaluate_primary_direction_perfection_condition",
    "evaluate_primary_direction_perfections_aggregate",
    "evaluate_primary_direction_perfections_network",
]


class PrimaryDirectionPerfectionKind(StrEnum):
    MUNDANE_POSITION_PERFECTION = "mundane_position_perfection"
    ZODIACAL_LONGITUDE_PERFECTION = "zodiacal_longitude_perfection"
    ZODIACAL_PROJECTED_PERFECTION = "zodiacal_projected_perfection"


class PrimaryDirectionPerfectionMode(StrEnum):
    POSITIONAL = "positional"


class PrimaryDirectionPerfectionConditionState(StrEnum):
    MUNDANE_POSITIONAL = "mundane_positional"
    ZODIACAL_POSITIONAL = "zodiacal_positional"
    ZODIACAL_PROJECTED = "zodiacal_projected"


@dataclass(frozen=True, slots=True)
class PrimaryDirectionPerfectionPolicy:
    kind: PrimaryDirectionPerfectionKind = PrimaryDirectionPerfectionKind.MUNDANE_POSITION_PERFECTION

    def __post_init__(self) -> None:
        if self.kind not in (
            PrimaryDirectionPerfectionKind.MUNDANE_POSITION_PERFECTION,
            PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION,
            PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION,
        ):
            raise ValueError(f"Unsupported primary direction perfection kind: {self.kind}")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionPerfectionTruth:
    kind: PrimaryDirectionPerfectionKind
    mode: PrimaryDirectionPerfectionMode
    uses_significator_mundane_fraction: bool
    world_frame_based: bool

    def __post_init__(self) -> None:
        expected = {
            PrimaryDirectionPerfectionKind.MUNDANE_POSITION_PERFECTION: (True, True),
            PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION: (False, False),
            PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION: (False, False),
        }.get(self.kind)
        if expected is None:
            raise ValueError(f"Unsupported primary direction perfection kind on truth: {self.kind}")
        if self.mode is not PrimaryDirectionPerfectionMode.POSITIONAL:
            raise ValueError("PrimaryDirectionPerfectionTruth invariant failed: mode mismatch")
        if (self.uses_significator_mundane_fraction, self.world_frame_based) != expected:
            raise ValueError(
                "PrimaryDirectionPerfectionTruth invariant failed: current admitted perfection traits mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionPerfectionClassification:
    truth: PrimaryDirectionPerfectionTruth
    positional: bool
    aspectual: bool

    def __post_init__(self) -> None:
        if not self.positional or self.aspectual:
            raise ValueError(
                "PrimaryDirectionPerfectionClassification invariant failed: current admitted perfection classification mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionPerfectionRelation:
    truth: PrimaryDirectionPerfectionTruth
    relation_kind: PrimaryDirectionPerfectionKind

    def __post_init__(self) -> None:
        if self.relation_kind is not self.truth.kind:
            raise ValueError(
                "PrimaryDirectionPerfectionRelation invariant failed: relation_kind must match truth.kind"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionPerfectionRelationProfile:
    truth: PrimaryDirectionPerfectionTruth
    detected_relation: PrimaryDirectionPerfectionRelation
    admitted_relations: tuple[PrimaryDirectionPerfectionRelation, ...]
    scored_relations: tuple[PrimaryDirectionPerfectionRelation, ...]

    def __post_init__(self) -> None:
        if self.detected_relation.truth != self.truth:
            raise ValueError(
                "PrimaryDirectionPerfectionRelationProfile invariant failed: detected relation truth mismatch"
            )
        if self.detected_relation not in self.admitted_relations:
            raise ValueError(
                "PrimaryDirectionPerfectionRelationProfile invariant failed: detected relation must be admitted"
            )
        for relation in self.scored_relations:
            if relation not in self.admitted_relations:
                raise ValueError(
                    "PrimaryDirectionPerfectionRelationProfile invariant failed: scored relation must be admitted"
                )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionPerfectionConditionProfile:
    truth: PrimaryDirectionPerfectionTruth
    classification: PrimaryDirectionPerfectionClassification
    relation_profile: PrimaryDirectionPerfectionRelationProfile
    state: PrimaryDirectionPerfectionConditionState

    def __post_init__(self) -> None:
        if self.classification.truth != self.truth:
            raise ValueError(
                "PrimaryDirectionPerfectionConditionProfile invariant failed: classification truth mismatch"
            )
        if self.relation_profile.truth != self.truth:
            raise ValueError(
                "PrimaryDirectionPerfectionConditionProfile invariant failed: relation truth mismatch"
            )
        expected_state = (
            PrimaryDirectionPerfectionConditionState.MUNDANE_POSITIONAL
            if self.truth.kind is PrimaryDirectionPerfectionKind.MUNDANE_POSITION_PERFECTION
            else (
                PrimaryDirectionPerfectionConditionState.ZODIACAL_POSITIONAL
                if self.truth.kind is PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION
                else PrimaryDirectionPerfectionConditionState.ZODIACAL_PROJECTED
            )
        )
        if self.state is not expected_state:
            raise ValueError("PrimaryDirectionPerfectionConditionProfile invariant failed: state mismatch")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionPerfectionsAggregateProfile:
    profiles: tuple[PrimaryDirectionPerfectionConditionProfile, ...]
    total_profiles: int
    positional_count: int
    world_frame_count: int

    def __post_init__(self) -> None:
        if not self.profiles:
            raise ValueError("PrimaryDirectionPerfectionsAggregateProfile requires at least one profile")
        if self.total_profiles != len(self.profiles):
            raise ValueError(
                "PrimaryDirectionPerfectionsAggregateProfile invariant failed: total_profiles mismatch"
            )
        if self.positional_count != len(self.profiles):
            raise ValueError(
                "PrimaryDirectionPerfectionsAggregateProfile invariant failed: positional_count mismatch"
            )
        if self.world_frame_count != sum(1 for profile in self.profiles if profile.truth.world_frame_based):
            raise ValueError(
                "PrimaryDirectionPerfectionsAggregateProfile invariant failed: world_frame_count mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionPerfectionsNetworkNode:
    kind: PrimaryDirectionPerfectionKind
    count: int

    def __post_init__(self) -> None:
        if self.count <= 0:
            raise ValueError("PrimaryDirectionPerfectionsNetworkNode invariant failed: count must be positive")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionPerfectionsNetworkEdge:
    from_kind: PrimaryDirectionPerfectionKind
    to_kind: PrimaryDirectionPerfectionKind
    count: int

    def __post_init__(self) -> None:
        if self.from_kind == self.to_kind:
            raise ValueError(
                "PrimaryDirectionPerfectionsNetworkEdge invariant failed: self-edges are not admitted"
            )
        if self.count <= 0:
            raise ValueError("PrimaryDirectionPerfectionsNetworkEdge invariant failed: count must be positive")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionPerfectionsNetworkProfile:
    nodes: tuple[PrimaryDirectionPerfectionsNetworkNode, ...]
    edges: tuple[PrimaryDirectionPerfectionsNetworkEdge, ...]
    dominant_kind: PrimaryDirectionPerfectionKind
    isolated_kinds: tuple[PrimaryDirectionPerfectionKind, ...]

    def __post_init__(self) -> None:
        if not self.nodes:
            raise ValueError("PrimaryDirectionPerfectionsNetworkProfile requires at least one node")
        kinds = [node.kind for node in self.nodes]
        if len(set(kinds)) != len(kinds):
            raise ValueError(
                "PrimaryDirectionPerfectionsNetworkProfile invariant failed: duplicate nodes"
            )


def primary_direction_perfection_truth(
    kind: PrimaryDirectionPerfectionKind = PrimaryDirectionPerfectionKind.MUNDANE_POSITION_PERFECTION,
    *,
    policy: PrimaryDirectionPerfectionPolicy | None = None,
) -> PrimaryDirectionPerfectionTruth:
    resolved_policy = policy if policy is not None else PrimaryDirectionPerfectionPolicy(kind)
    return PrimaryDirectionPerfectionTruth(
        kind=resolved_policy.kind,
        mode=PrimaryDirectionPerfectionMode.POSITIONAL,
        uses_significator_mundane_fraction=(
            resolved_policy.kind is PrimaryDirectionPerfectionKind.MUNDANE_POSITION_PERFECTION
        ),
        world_frame_based=(
            resolved_policy.kind is PrimaryDirectionPerfectionKind.MUNDANE_POSITION_PERFECTION
        ),
    )


def classify_primary_direction_perfection(
    truth: PrimaryDirectionPerfectionTruth,
) -> PrimaryDirectionPerfectionClassification:
    return PrimaryDirectionPerfectionClassification(
        truth=truth,
        positional=True,
        aspectual=False,
    )


def relate_primary_direction_perfection(
    truth: PrimaryDirectionPerfectionTruth,
) -> PrimaryDirectionPerfectionRelation:
    return PrimaryDirectionPerfectionRelation(
        truth=truth,
        relation_kind=truth.kind,
    )


def evaluate_primary_direction_perfection_relations(
    truth: PrimaryDirectionPerfectionTruth,
) -> PrimaryDirectionPerfectionRelationProfile:
    relation = relate_primary_direction_perfection(truth)
    admitted = (relation,)
    return PrimaryDirectionPerfectionRelationProfile(
        truth=truth,
        detected_relation=relation,
        admitted_relations=admitted,
        scored_relations=admitted,
    )


def evaluate_primary_direction_perfection_condition(
    truth: PrimaryDirectionPerfectionTruth,
) -> PrimaryDirectionPerfectionConditionProfile:
    return PrimaryDirectionPerfectionConditionProfile(
        truth=truth,
        classification=classify_primary_direction_perfection(truth),
        relation_profile=evaluate_primary_direction_perfection_relations(truth),
        state=(
            PrimaryDirectionPerfectionConditionState.MUNDANE_POSITIONAL
            if truth.kind is PrimaryDirectionPerfectionKind.MUNDANE_POSITION_PERFECTION
            else (
                PrimaryDirectionPerfectionConditionState.ZODIACAL_POSITIONAL
                if truth.kind is PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION
                else PrimaryDirectionPerfectionConditionState.ZODIACAL_PROJECTED
            )
        ),
    )


def evaluate_primary_direction_perfections_aggregate(
    truths: Iterable[PrimaryDirectionPerfectionTruth],
) -> PrimaryDirectionPerfectionsAggregateProfile:
    profiles = tuple(evaluate_primary_direction_perfection_condition(truth) for truth in truths)
    if not profiles:
        raise ValueError("evaluate_primary_direction_perfections_aggregate requires at least one truth")
    return PrimaryDirectionPerfectionsAggregateProfile(
        profiles=profiles,
        total_profiles=len(profiles),
        positional_count=len(profiles),
        world_frame_count=sum(1 for profile in profiles if profile.truth.world_frame_based),
    )


def evaluate_primary_direction_perfections_network(
    truths: Iterable[PrimaryDirectionPerfectionTruth],
) -> PrimaryDirectionPerfectionsNetworkProfile:
    truth_tuple = tuple(truths)
    if not truth_tuple:
        raise ValueError("evaluate_primary_direction_perfections_network requires at least one truth")
    counts: dict[PrimaryDirectionPerfectionKind, int] = {}
    for truth in truth_tuple:
        counts[truth.kind] = counts.get(truth.kind, 0) + 1
    nodes = tuple(
        sorted(
            (
                PrimaryDirectionPerfectionsNetworkNode(kind=kind, count=count)
                for kind, count in counts.items()
            ),
            key=lambda node: node.kind.value,
        )
    )
    edge_counts: dict[tuple[PrimaryDirectionPerfectionKind, PrimaryDirectionPerfectionKind], int] = {}
    for left, right in zip(truth_tuple, truth_tuple[1:]):
        if left.kind == right.kind:
            continue
        key = (left.kind, right.kind)
        edge_counts[key] = edge_counts.get(key, 0) + 1
    edges = tuple(
        sorted(
            (
                PrimaryDirectionPerfectionsNetworkEdge(from_kind=from_kind, to_kind=to_kind, count=count)
                for (from_kind, to_kind), count in edge_counts.items()
            ),
            key=lambda edge: (edge.from_kind.value, edge.to_kind.value),
        )
    )
    dominant = max(nodes, key=lambda node: (node.count, node.kind.value)).kind
    participating = {edge.from_kind for edge in edges} | {edge.to_kind for edge in edges}
    isolated = tuple(sorted((node.kind for node in nodes if node.kind not in participating), key=lambda k: k.value))
    return PrimaryDirectionPerfectionsNetworkProfile(
        nodes=nodes,
        edges=edges,
        dominant_kind=dominant,
        isolated_kinds=isolated,
    )
