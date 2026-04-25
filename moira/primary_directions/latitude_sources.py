"""
Moira -- primary_directions/latitude_sources.py
Standalone latitude-source doctrine owner for the primary-directions subsystem.

Boundary
--------
Owns the doctrinal identity, admission policy, and hardened interpretation of
the currently admitted sources from which primary-direction latitude is taken
or assigned.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

__all__ = [
    "PrimaryDirectionLatitudeSource",
    "PrimaryDirectionLatitudeSourceRelationKind",
    "PrimaryDirectionLatitudeSourceConditionState",
    "PrimaryDirectionLatitudeSourcePolicy",
    "PrimaryDirectionLatitudeSourceTruth",
    "PrimaryDirectionLatitudeSourceClassification",
    "PrimaryDirectionLatitudeSourceRelation",
    "PrimaryDirectionLatitudeSourceRelationProfile",
    "PrimaryDirectionLatitudeSourceConditionProfile",
    "PrimaryDirectionLatitudeSourceAggregateProfile",
    "PrimaryDirectionLatitudeSourceNetworkNode",
    "PrimaryDirectionLatitudeSourceNetworkEdge",
    "PrimaryDirectionLatitudeSourceNetworkProfile",
    "primary_direction_latitude_source_truth",
    "classify_primary_direction_latitude_source",
    "relate_primary_direction_latitude_source",
    "evaluate_primary_direction_latitude_source_relations",
    "evaluate_primary_direction_latitude_source_condition",
    "evaluate_primary_direction_latitude_source_aggregate",
    "evaluate_primary_direction_latitude_source_network",
]


class PrimaryDirectionLatitudeSource(StrEnum):
    PROMISSOR_NATIVE = "promissor_native"
    ASSIGNED_ZERO = "assigned_zero"
    ASPECT_INHERITED = "aspect_inherited"
    SIGNIFICATOR_NATIVE = "significator_native"


class PrimaryDirectionLatitudeSourceRelationKind(StrEnum):
    NATIVE_BODY_LATITUDE = "native_body_latitude"
    ZERO_ASSIGNED = "zero_assigned"
    ASPECT_LATITUDE_INHERITED = "aspect_latitude_inherited"
    SIGNIFICATOR_LATITUDE_NATIVE = "significator_latitude_native"


class PrimaryDirectionLatitudeSourceConditionState(StrEnum):
    BODY_DERIVED = "body_derived"
    ZERO_ASSIGNED = "zero_assigned"
    ASPECT_DERIVED = "aspect_derived"
    SIGNIFICATOR_DERIVED = "significator_derived"


@dataclass(frozen=True, slots=True)
class PrimaryDirectionLatitudeSourcePolicy:
    source: PrimaryDirectionLatitudeSource = PrimaryDirectionLatitudeSource.PROMISSOR_NATIVE

    def __post_init__(self) -> None:
        if not isinstance(self.source, PrimaryDirectionLatitudeSource):
            raise ValueError(f"Unsupported primary direction latitude source: {self.source}")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionLatitudeSourceTruth:
    source: PrimaryDirectionLatitudeSource
    derives_from_body: bool
    assigns_zero: bool

    def __post_init__(self) -> None:
        expected = {
            PrimaryDirectionLatitudeSource.PROMISSOR_NATIVE: (True, False),
            PrimaryDirectionLatitudeSource.ASSIGNED_ZERO: (False, True),
            PrimaryDirectionLatitudeSource.ASPECT_INHERITED: (False, False),
            PrimaryDirectionLatitudeSource.SIGNIFICATOR_NATIVE: (False, False),
        }[self.source]
        if (self.derives_from_body, self.assigns_zero) != expected:
            raise ValueError(
                "PrimaryDirectionLatitudeSourceTruth invariant failed: source traits mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionLatitudeSourceClassification:
    truth: PrimaryDirectionLatitudeSourceTruth
    body_derived: bool
    zero_assigned: bool
    aspect_inherited: bool
    significator_derived: bool

    def __post_init__(self) -> None:
        truth_flags = (
            self.truth.source is PrimaryDirectionLatitudeSource.PROMISSOR_NATIVE,
            self.truth.source is PrimaryDirectionLatitudeSource.ASSIGNED_ZERO,
            self.truth.source is PrimaryDirectionLatitudeSource.ASPECT_INHERITED,
            self.truth.source is PrimaryDirectionLatitudeSource.SIGNIFICATOR_NATIVE,
        )
        class_flags = (
            self.body_derived,
            self.zero_assigned,
            self.aspect_inherited,
            self.significator_derived,
        )
        if sum(class_flags) != 1:
            raise ValueError(
                "PrimaryDirectionLatitudeSourceClassification invariant failed: exactly one classification flag must be set"
            )
        if class_flags != truth_flags:
            raise ValueError(
                "PrimaryDirectionLatitudeSourceClassification invariant failed: classification flags mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionLatitudeSourceRelation:
    truth: PrimaryDirectionLatitudeSourceTruth
    relation_kind: PrimaryDirectionLatitudeSourceRelationKind

    def __post_init__(self) -> None:
        expected = (
            PrimaryDirectionLatitudeSourceRelationKind.NATIVE_BODY_LATITUDE
            if self.truth.source is PrimaryDirectionLatitudeSource.PROMISSOR_NATIVE
            else (
                PrimaryDirectionLatitudeSourceRelationKind.ZERO_ASSIGNED
                if self.truth.source is PrimaryDirectionLatitudeSource.ASSIGNED_ZERO
                else (
                    PrimaryDirectionLatitudeSourceRelationKind.ASPECT_LATITUDE_INHERITED
                    if self.truth.source is PrimaryDirectionLatitudeSource.ASPECT_INHERITED
                    else PrimaryDirectionLatitudeSourceRelationKind.SIGNIFICATOR_LATITUDE_NATIVE
                )
            )
        )
        if self.relation_kind is not expected:
            raise ValueError(
                "PrimaryDirectionLatitudeSourceRelation invariant failed: relation_kind mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionLatitudeSourceRelationProfile:
    truth: PrimaryDirectionLatitudeSourceTruth
    detected_relation: PrimaryDirectionLatitudeSourceRelation
    admitted_relations: tuple[PrimaryDirectionLatitudeSourceRelation, ...]
    scored_relations: tuple[PrimaryDirectionLatitudeSourceRelation, ...]

    def __post_init__(self) -> None:
        if self.detected_relation.truth != self.truth:
            raise ValueError(
                "PrimaryDirectionLatitudeSourceRelationProfile invariant failed: detected relation truth mismatch"
            )
        if self.detected_relation not in self.admitted_relations:
            raise ValueError(
                "PrimaryDirectionLatitudeSourceRelationProfile invariant failed: detected relation must be admitted"
            )
        for relation in self.scored_relations:
            if relation not in self.admitted_relations:
                raise ValueError(
                    "PrimaryDirectionLatitudeSourceRelationProfile invariant failed: scored relation must be admitted"
                )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionLatitudeSourceConditionProfile:
    truth: PrimaryDirectionLatitudeSourceTruth
    classification: PrimaryDirectionLatitudeSourceClassification
    relation_profile: PrimaryDirectionLatitudeSourceRelationProfile
    state: PrimaryDirectionLatitudeSourceConditionState

    def __post_init__(self) -> None:
        if self.classification.truth != self.truth:
            raise ValueError(
                "PrimaryDirectionLatitudeSourceConditionProfile invariant failed: classification truth mismatch"
            )
        if self.relation_profile.truth != self.truth:
            raise ValueError(
                "PrimaryDirectionLatitudeSourceConditionProfile invariant failed: relation truth mismatch"
            )
        expected = (
            PrimaryDirectionLatitudeSourceConditionState.BODY_DERIVED
            if self.truth.source is PrimaryDirectionLatitudeSource.PROMISSOR_NATIVE
            else (
                PrimaryDirectionLatitudeSourceConditionState.ZERO_ASSIGNED
                if self.truth.source is PrimaryDirectionLatitudeSource.ASSIGNED_ZERO
                else (
                    PrimaryDirectionLatitudeSourceConditionState.ASPECT_DERIVED
                    if self.truth.source is PrimaryDirectionLatitudeSource.ASPECT_INHERITED
                    else PrimaryDirectionLatitudeSourceConditionState.SIGNIFICATOR_DERIVED
                )
            )
        )
        if self.state is not expected:
            raise ValueError(
                "PrimaryDirectionLatitudeSourceConditionProfile invariant failed: state mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionLatitudeSourceAggregateProfile:
    profiles: tuple[PrimaryDirectionLatitudeSourceConditionProfile, ...]
    total_profiles: int
    body_derived_count: int
    zero_assigned_count: int

    def __post_init__(self) -> None:
        if not self.profiles:
            raise ValueError("PrimaryDirectionLatitudeSourceAggregateProfile requires at least one profile")
        if self.total_profiles != len(self.profiles):
            raise ValueError(
                "PrimaryDirectionLatitudeSourceAggregateProfile invariant failed: total_profiles mismatch"
            )
        if self.body_derived_count != sum(1 for profile in self.profiles if profile.truth.derives_from_body):
            raise ValueError(
                "PrimaryDirectionLatitudeSourceAggregateProfile invariant failed: body_derived_count mismatch"
            )
        if self.zero_assigned_count != sum(1 for profile in self.profiles if profile.truth.assigns_zero):
            raise ValueError(
                "PrimaryDirectionLatitudeSourceAggregateProfile invariant failed: zero_assigned_count mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionLatitudeSourceNetworkNode:
    source: PrimaryDirectionLatitudeSource
    count: int

    def __post_init__(self) -> None:
        if self.count <= 0:
            raise ValueError("PrimaryDirectionLatitudeSourceNetworkNode invariant failed: count must be positive")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionLatitudeSourceNetworkEdge:
    from_source: PrimaryDirectionLatitudeSource
    to_source: PrimaryDirectionLatitudeSource
    count: int

    def __post_init__(self) -> None:
        if self.from_source == self.to_source:
            raise ValueError(
                "PrimaryDirectionLatitudeSourceNetworkEdge invariant failed: self-edges are not admitted"
            )
        if self.count <= 0:
            raise ValueError("PrimaryDirectionLatitudeSourceNetworkEdge invariant failed: count must be positive")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionLatitudeSourceNetworkProfile:
    nodes: tuple[PrimaryDirectionLatitudeSourceNetworkNode, ...]
    edges: tuple[PrimaryDirectionLatitudeSourceNetworkEdge, ...]
    dominant_source: PrimaryDirectionLatitudeSource
    isolated_sources: tuple[PrimaryDirectionLatitudeSource, ...]

    def __post_init__(self) -> None:
        if not self.nodes:
            raise ValueError("PrimaryDirectionLatitudeSourceNetworkProfile requires at least one node")
        sources = [node.source for node in self.nodes]
        if len(set(sources)) != len(sources):
            raise ValueError(
                "PrimaryDirectionLatitudeSourceNetworkProfile invariant failed: duplicate nodes"
            )
        node_set = set(sources)
        for edge in self.edges:
            if edge.from_source not in node_set or edge.to_source not in node_set:
                raise ValueError(
                    "PrimaryDirectionLatitudeSourceNetworkProfile invariant failed: dangling edge"
                )
        dominant = max(self.nodes, key=lambda node: (node.count, node.source.value)).source
        if self.dominant_source is not dominant:
            raise ValueError(
                "PrimaryDirectionLatitudeSourceNetworkProfile invariant failed: dominant_source mismatch"
            )
        if set(self.isolated_sources) - node_set:
            raise ValueError(
                "PrimaryDirectionLatitudeSourceNetworkProfile invariant failed: isolated_sources contains unknown node"
            )


def primary_direction_latitude_source_truth(
    source: PrimaryDirectionLatitudeSource = PrimaryDirectionLatitudeSource.PROMISSOR_NATIVE,
    *,
    policy: PrimaryDirectionLatitudeSourcePolicy | None = None,
) -> PrimaryDirectionLatitudeSourceTruth:
    resolved_policy = policy if policy is not None else PrimaryDirectionLatitudeSourcePolicy(source)
    return PrimaryDirectionLatitudeSourceTruth(
        source=resolved_policy.source,
        derives_from_body=resolved_policy.source is PrimaryDirectionLatitudeSource.PROMISSOR_NATIVE,
        assigns_zero=resolved_policy.source is PrimaryDirectionLatitudeSource.ASSIGNED_ZERO,
    )


def classify_primary_direction_latitude_source(
    truth: PrimaryDirectionLatitudeSourceTruth,
) -> PrimaryDirectionLatitudeSourceClassification:
    return PrimaryDirectionLatitudeSourceClassification(
        truth=truth,
        body_derived=truth.derives_from_body,
        zero_assigned=truth.assigns_zero,
        aspect_inherited=truth.source is PrimaryDirectionLatitudeSource.ASPECT_INHERITED,
        significator_derived=truth.source is PrimaryDirectionLatitudeSource.SIGNIFICATOR_NATIVE,
    )


def relate_primary_direction_latitude_source(
    truth: PrimaryDirectionLatitudeSourceTruth,
) -> PrimaryDirectionLatitudeSourceRelation:
    return PrimaryDirectionLatitudeSourceRelation(
        truth=truth,
        relation_kind=(
            PrimaryDirectionLatitudeSourceRelationKind.NATIVE_BODY_LATITUDE
            if truth.source is PrimaryDirectionLatitudeSource.PROMISSOR_NATIVE
            else (
                PrimaryDirectionLatitudeSourceRelationKind.ZERO_ASSIGNED
                if truth.source is PrimaryDirectionLatitudeSource.ASSIGNED_ZERO
                else (
                    PrimaryDirectionLatitudeSourceRelationKind.ASPECT_LATITUDE_INHERITED
                    if truth.source is PrimaryDirectionLatitudeSource.ASPECT_INHERITED
                    else PrimaryDirectionLatitudeSourceRelationKind.SIGNIFICATOR_LATITUDE_NATIVE
                )
            )
        ),
    )


def evaluate_primary_direction_latitude_source_relations(
    truth: PrimaryDirectionLatitudeSourceTruth,
) -> PrimaryDirectionLatitudeSourceRelationProfile:
    relation = relate_primary_direction_latitude_source(truth)
    admitted = (relation,)
    return PrimaryDirectionLatitudeSourceRelationProfile(
        truth=truth,
        detected_relation=relation,
        admitted_relations=admitted,
        scored_relations=admitted,
    )


def evaluate_primary_direction_latitude_source_condition(
    truth: PrimaryDirectionLatitudeSourceTruth,
) -> PrimaryDirectionLatitudeSourceConditionProfile:
    return PrimaryDirectionLatitudeSourceConditionProfile(
        truth=truth,
        classification=classify_primary_direction_latitude_source(truth),
        relation_profile=evaluate_primary_direction_latitude_source_relations(truth),
        state=(
            PrimaryDirectionLatitudeSourceConditionState.BODY_DERIVED
            if truth.source is PrimaryDirectionLatitudeSource.PROMISSOR_NATIVE
            else (
                PrimaryDirectionLatitudeSourceConditionState.ZERO_ASSIGNED
                if truth.source is PrimaryDirectionLatitudeSource.ASSIGNED_ZERO
                else (
                    PrimaryDirectionLatitudeSourceConditionState.ASPECT_DERIVED
                    if truth.source is PrimaryDirectionLatitudeSource.ASPECT_INHERITED
                    else PrimaryDirectionLatitudeSourceConditionState.SIGNIFICATOR_DERIVED
                )
            )
        ),
    )


def evaluate_primary_direction_latitude_source_aggregate(
    truths: Iterable[PrimaryDirectionLatitudeSourceTruth],
) -> PrimaryDirectionLatitudeSourceAggregateProfile:
    profiles = tuple(evaluate_primary_direction_latitude_source_condition(truth) for truth in truths)
    if not profiles:
        raise ValueError("evaluate_primary_direction_latitude_source_aggregate requires at least one truth")
    return PrimaryDirectionLatitudeSourceAggregateProfile(
        profiles=profiles,
        total_profiles=len(profiles),
        body_derived_count=sum(1 for profile in profiles if profile.truth.derives_from_body),
        zero_assigned_count=sum(1 for profile in profiles if profile.truth.assigns_zero),
    )


def evaluate_primary_direction_latitude_source_network(
    truths: Iterable[PrimaryDirectionLatitudeSourceTruth],
) -> PrimaryDirectionLatitudeSourceNetworkProfile:
    truth_tuple = tuple(truths)
    if not truth_tuple:
        raise ValueError("evaluate_primary_direction_latitude_source_network requires at least one truth")

    counts: dict[PrimaryDirectionLatitudeSource, int] = {}
    for truth in truth_tuple:
        counts[truth.source] = counts.get(truth.source, 0) + 1

    nodes = tuple(
        sorted(
            (
                PrimaryDirectionLatitudeSourceNetworkNode(source=source, count=count)
                for source, count in counts.items()
            ),
            key=lambda node: node.source.value,
        )
    )

    edge_counts: dict[tuple[PrimaryDirectionLatitudeSource, PrimaryDirectionLatitudeSource], int] = {}
    for left, right in zip(truth_tuple, truth_tuple[1:]):
        if left.source == right.source:
            continue
        key = (left.source, right.source)
        edge_counts[key] = edge_counts.get(key, 0) + 1

    edges = tuple(
        sorted(
            (
                PrimaryDirectionLatitudeSourceNetworkEdge(
                    from_source=from_source,
                    to_source=to_source,
                    count=count,
                )
                for (from_source, to_source), count in edge_counts.items()
            ),
            key=lambda edge: (edge.from_source.value, edge.to_source.value),
        )
    )

    dominant = max(nodes, key=lambda node: (node.count, node.source.value)).source
    participating = {edge.from_source for edge in edges} | {edge.to_source for edge in edges}
    isolated = tuple(
        sorted(
            (node.source for node in nodes if node.source not in participating),
            key=lambda source: source.value,
        )
    )
    return PrimaryDirectionLatitudeSourceNetworkProfile(
        nodes=nodes,
        edges=edges,
        dominant_source=dominant,
        isolated_sources=isolated,
    )
