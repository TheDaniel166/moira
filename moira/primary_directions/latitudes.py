"""
Moira -- primary_directions/latitudes.py
Standalone latitude-doctrine owner for the primary-directions subsystem.

Boundary
--------
Owns the doctrinal identity, admission policy, and hardened interpretation of
currently admitted latitude treatments in the primary-directions family.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

__all__ = [
    "PrimaryDirectionLatitudeDoctrine",
    "PrimaryDirectionLatitudeRelationKind",
    "PrimaryDirectionLatitudeConditionState",
    "PrimaryDirectionLatitudePolicy",
    "PrimaryDirectionLatitudeTruth",
    "PrimaryDirectionLatitudeClassification",
    "PrimaryDirectionLatitudeRelation",
    "PrimaryDirectionLatitudeRelationProfile",
    "PrimaryDirectionLatitudeConditionProfile",
    "PrimaryDirectionLatitudeAggregateProfile",
    "PrimaryDirectionLatitudeNetworkNode",
    "PrimaryDirectionLatitudeNetworkEdge",
    "PrimaryDirectionLatitudeNetworkProfile",
    "primary_direction_latitude_truth",
    "classify_primary_direction_latitude",
    "relate_primary_direction_latitude",
    "evaluate_primary_direction_latitude_relations",
    "evaluate_primary_direction_latitude_condition",
    "evaluate_primary_direction_latitude_aggregate",
    "evaluate_primary_direction_latitude_network",
]


class PrimaryDirectionLatitudeDoctrine(StrEnum):
    MUNDANE_PRESERVED = "mundane_preserved"
    ZODIACAL_SUPPRESSED = "zodiacal_suppressed"
    ZODIACAL_PROMISSOR_RETAINED = "zodiacal_promissor_retained"
    ZODIACAL_SIGNIFICATOR_CONDITIONED = "zodiacal_significator_conditioned"


class PrimaryDirectionLatitudeRelationKind(StrEnum):
    BODY_LATITUDE_PRESERVED = "body_latitude_preserved"
    ZODIACAL_LATITUDE_SUPPRESSED = "zodiacal_latitude_suppressed"
    PROMISSOR_LATITUDE_RETAINED = "promissor_latitude_retained"
    SIGNIFICATOR_LATITUDE_CONDITIONED = "significator_latitude_conditioned"


class PrimaryDirectionLatitudeConditionState(StrEnum):
    PRESERVING = "preserving"
    SUPPRESSING = "suppressing"
    RETAINING_PROMISSOR_LATITUDE = "retaining_promissor_latitude"
    CONDITIONING_ON_SIGNIFICATOR = "conditioning_on_significator"


@dataclass(frozen=True, slots=True)
class PrimaryDirectionLatitudePolicy:
    doctrine: PrimaryDirectionLatitudeDoctrine = PrimaryDirectionLatitudeDoctrine.MUNDANE_PRESERVED

    def __post_init__(self) -> None:
        if not isinstance(self.doctrine, PrimaryDirectionLatitudeDoctrine):
            raise ValueError(f"Unsupported primary direction latitude doctrine: {self.doctrine}")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionLatitudeTruth:
    doctrine: PrimaryDirectionLatitudeDoctrine
    preserves_latitude: bool
    zodiacal: bool

    def __post_init__(self) -> None:
        expected = {
            PrimaryDirectionLatitudeDoctrine.MUNDANE_PRESERVED: (True, False),
            PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED: (False, True),
            PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED: (True, True),
            PrimaryDirectionLatitudeDoctrine.ZODIACAL_SIGNIFICATOR_CONDITIONED: (True, True),
        }[self.doctrine]
        if (self.preserves_latitude, self.zodiacal) != expected:
            raise ValueError(
                "PrimaryDirectionLatitudeTruth invariant failed: doctrine traits mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionLatitudeClassification:
    truth: PrimaryDirectionLatitudeTruth
    preserving: bool
    suppressing: bool

    def __post_init__(self) -> None:
        if self.preserving == self.suppressing:
            raise ValueError(
                "PrimaryDirectionLatitudeClassification invariant failed: preserving/suppressing mismatch"
            )
        if self.preserving != self.truth.preserves_latitude:
            raise ValueError(
                "PrimaryDirectionLatitudeClassification invariant failed: preserving mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionLatitudeRelation:
    truth: PrimaryDirectionLatitudeTruth
    relation_kind: PrimaryDirectionLatitudeRelationKind

    def __post_init__(self) -> None:
        expected = (
            PrimaryDirectionLatitudeRelationKind.BODY_LATITUDE_PRESERVED
            if self.truth.doctrine is PrimaryDirectionLatitudeDoctrine.MUNDANE_PRESERVED
            else (
                PrimaryDirectionLatitudeRelationKind.ZODIACAL_LATITUDE_SUPPRESSED
                if self.truth.doctrine is PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED
                else (
                    PrimaryDirectionLatitudeRelationKind.PROMISSOR_LATITUDE_RETAINED
                    if self.truth.doctrine is PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED
                    else PrimaryDirectionLatitudeRelationKind.SIGNIFICATOR_LATITUDE_CONDITIONED
                )
            )
        )
        if self.relation_kind is not expected:
            raise ValueError(
                "PrimaryDirectionLatitudeRelation invariant failed: relation_kind mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionLatitudeRelationProfile:
    truth: PrimaryDirectionLatitudeTruth
    detected_relation: PrimaryDirectionLatitudeRelation
    admitted_relations: tuple[PrimaryDirectionLatitudeRelation, ...]
    scored_relations: tuple[PrimaryDirectionLatitudeRelation, ...]

    def __post_init__(self) -> None:
        if self.detected_relation.truth != self.truth:
            raise ValueError(
                "PrimaryDirectionLatitudeRelationProfile invariant failed: detected relation truth mismatch"
            )
        if self.detected_relation not in self.admitted_relations:
            raise ValueError(
                "PrimaryDirectionLatitudeRelationProfile invariant failed: detected relation must be admitted"
            )
        for relation in self.scored_relations:
            if relation not in self.admitted_relations:
                raise ValueError(
                    "PrimaryDirectionLatitudeRelationProfile invariant failed: scored relation must be admitted"
                )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionLatitudeConditionProfile:
    truth: PrimaryDirectionLatitudeTruth
    classification: PrimaryDirectionLatitudeClassification
    relation_profile: PrimaryDirectionLatitudeRelationProfile
    state: PrimaryDirectionLatitudeConditionState

    def __post_init__(self) -> None:
        if self.classification.truth != self.truth:
            raise ValueError(
                "PrimaryDirectionLatitudeConditionProfile invariant failed: classification truth mismatch"
            )
        if self.relation_profile.truth != self.truth:
            raise ValueError(
                "PrimaryDirectionLatitudeConditionProfile invariant failed: relation truth mismatch"
            )
        expected = (
            PrimaryDirectionLatitudeConditionState.PRESERVING
            if self.truth.doctrine is PrimaryDirectionLatitudeDoctrine.MUNDANE_PRESERVED
            else (
                PrimaryDirectionLatitudeConditionState.SUPPRESSING
                if self.truth.doctrine is PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED
                else (
                    PrimaryDirectionLatitudeConditionState.RETAINING_PROMISSOR_LATITUDE
                    if self.truth.doctrine is PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED
                    else PrimaryDirectionLatitudeConditionState.CONDITIONING_ON_SIGNIFICATOR
                )
            )
        )
        if self.state is not expected:
            raise ValueError(
                "PrimaryDirectionLatitudeConditionProfile invariant failed: state mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionLatitudeAggregateProfile:
    profiles: tuple[PrimaryDirectionLatitudeConditionProfile, ...]
    total_profiles: int
    preserving_count: int
    suppressing_count: int

    def __post_init__(self) -> None:
        if not self.profiles:
            raise ValueError("PrimaryDirectionLatitudeAggregateProfile requires at least one profile")
        if self.total_profiles != len(self.profiles):
            raise ValueError(
                "PrimaryDirectionLatitudeAggregateProfile invariant failed: total_profiles mismatch"
            )
        if self.preserving_count != sum(1 for profile in self.profiles if profile.truth.preserves_latitude):
            raise ValueError(
                "PrimaryDirectionLatitudeAggregateProfile invariant failed: preserving_count mismatch"
            )
        if self.suppressing_count != sum(1 for profile in self.profiles if not profile.truth.preserves_latitude):
            raise ValueError(
                "PrimaryDirectionLatitudeAggregateProfile invariant failed: suppressing_count mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionLatitudeNetworkNode:
    doctrine: PrimaryDirectionLatitudeDoctrine
    count: int

    def __post_init__(self) -> None:
        if self.count <= 0:
            raise ValueError("PrimaryDirectionLatitudeNetworkNode invariant failed: count must be positive")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionLatitudeNetworkEdge:
    from_doctrine: PrimaryDirectionLatitudeDoctrine
    to_doctrine: PrimaryDirectionLatitudeDoctrine
    count: int

    def __post_init__(self) -> None:
        if self.from_doctrine == self.to_doctrine:
            raise ValueError(
                "PrimaryDirectionLatitudeNetworkEdge invariant failed: self-edges are not admitted"
            )
        if self.count <= 0:
            raise ValueError("PrimaryDirectionLatitudeNetworkEdge invariant failed: count must be positive")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionLatitudeNetworkProfile:
    nodes: tuple[PrimaryDirectionLatitudeNetworkNode, ...]
    edges: tuple[PrimaryDirectionLatitudeNetworkEdge, ...]
    dominant_doctrine: PrimaryDirectionLatitudeDoctrine
    isolated_doctrines: tuple[PrimaryDirectionLatitudeDoctrine, ...]

    def __post_init__(self) -> None:
        if not self.nodes:
            raise ValueError("PrimaryDirectionLatitudeNetworkProfile requires at least one node")
        doctrines = [node.doctrine for node in self.nodes]
        if len(set(doctrines)) != len(doctrines):
            raise ValueError(
                "PrimaryDirectionLatitudeNetworkProfile invariant failed: duplicate nodes"
            )
        node_set = set(doctrines)
        for edge in self.edges:
            if edge.from_doctrine not in node_set or edge.to_doctrine not in node_set:
                raise ValueError(
                    "PrimaryDirectionLatitudeNetworkProfile invariant failed: dangling edge"
                )
        dominant = max(self.nodes, key=lambda node: (node.count, node.doctrine.value)).doctrine
        if self.dominant_doctrine is not dominant:
            raise ValueError(
                "PrimaryDirectionLatitudeNetworkProfile invariant failed: dominant_doctrine mismatch"
            )
        if set(self.isolated_doctrines) - node_set:
            raise ValueError(
                "PrimaryDirectionLatitudeNetworkProfile invariant failed: isolated_doctrines contains unknown node"
            )


def primary_direction_latitude_truth(
    doctrine: PrimaryDirectionLatitudeDoctrine = PrimaryDirectionLatitudeDoctrine.MUNDANE_PRESERVED,
    *,
    policy: PrimaryDirectionLatitudePolicy | None = None,
) -> PrimaryDirectionLatitudeTruth:
    resolved_policy = policy if policy is not None else PrimaryDirectionLatitudePolicy(doctrine)
    return PrimaryDirectionLatitudeTruth(
        doctrine=resolved_policy.doctrine,
        preserves_latitude=resolved_policy.doctrine is not PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED,
        zodiacal=resolved_policy.doctrine is not PrimaryDirectionLatitudeDoctrine.MUNDANE_PRESERVED,
    )


def classify_primary_direction_latitude(
    truth: PrimaryDirectionLatitudeTruth,
) -> PrimaryDirectionLatitudeClassification:
    return PrimaryDirectionLatitudeClassification(
        truth=truth,
        preserving=truth.preserves_latitude,
        suppressing=not truth.preserves_latitude,
    )


def relate_primary_direction_latitude(
    truth: PrimaryDirectionLatitudeTruth,
) -> PrimaryDirectionLatitudeRelation:
    return PrimaryDirectionLatitudeRelation(
        truth=truth,
        relation_kind=(
            PrimaryDirectionLatitudeRelationKind.BODY_LATITUDE_PRESERVED
            if truth.doctrine is PrimaryDirectionLatitudeDoctrine.MUNDANE_PRESERVED
            else (
                PrimaryDirectionLatitudeRelationKind.ZODIACAL_LATITUDE_SUPPRESSED
                if truth.doctrine is PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED
                else (
                    PrimaryDirectionLatitudeRelationKind.PROMISSOR_LATITUDE_RETAINED
                    if truth.doctrine is PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED
                    else PrimaryDirectionLatitudeRelationKind.SIGNIFICATOR_LATITUDE_CONDITIONED
                )
            )
        ),
    )


def evaluate_primary_direction_latitude_relations(
    truth: PrimaryDirectionLatitudeTruth,
) -> PrimaryDirectionLatitudeRelationProfile:
    relation = relate_primary_direction_latitude(truth)
    admitted = (relation,)
    return PrimaryDirectionLatitudeRelationProfile(
        truth=truth,
        detected_relation=relation,
        admitted_relations=admitted,
        scored_relations=admitted,
    )


def evaluate_primary_direction_latitude_condition(
    truth: PrimaryDirectionLatitudeTruth,
) -> PrimaryDirectionLatitudeConditionProfile:
    return PrimaryDirectionLatitudeConditionProfile(
        truth=truth,
        classification=classify_primary_direction_latitude(truth),
        relation_profile=evaluate_primary_direction_latitude_relations(truth),
        state=(
            PrimaryDirectionLatitudeConditionState.PRESERVING
            if truth.doctrine is PrimaryDirectionLatitudeDoctrine.MUNDANE_PRESERVED
            else (
                PrimaryDirectionLatitudeConditionState.SUPPRESSING
                if truth.doctrine is PrimaryDirectionLatitudeDoctrine.ZODIACAL_SUPPRESSED
                else (
                    PrimaryDirectionLatitudeConditionState.RETAINING_PROMISSOR_LATITUDE
                    if truth.doctrine is PrimaryDirectionLatitudeDoctrine.ZODIACAL_PROMISSOR_RETAINED
                    else PrimaryDirectionLatitudeConditionState.CONDITIONING_ON_SIGNIFICATOR
                )
            )
        ),
    )


def evaluate_primary_direction_latitude_aggregate(
    truths: Iterable[PrimaryDirectionLatitudeTruth],
) -> PrimaryDirectionLatitudeAggregateProfile:
    profiles = tuple(evaluate_primary_direction_latitude_condition(truth) for truth in truths)
    if not profiles:
        raise ValueError("evaluate_primary_direction_latitude_aggregate requires at least one truth")
    return PrimaryDirectionLatitudeAggregateProfile(
        profiles=profiles,
        total_profiles=len(profiles),
        preserving_count=sum(1 for profile in profiles if profile.truth.preserves_latitude),
        suppressing_count=sum(1 for profile in profiles if not profile.truth.preserves_latitude),
    )


def evaluate_primary_direction_latitude_network(
    truths: Iterable[PrimaryDirectionLatitudeTruth],
) -> PrimaryDirectionLatitudeNetworkProfile:
    truth_tuple = tuple(truths)
    if not truth_tuple:
        raise ValueError("evaluate_primary_direction_latitude_network requires at least one truth")

    counts: dict[PrimaryDirectionLatitudeDoctrine, int] = {}
    for truth in truth_tuple:
        counts[truth.doctrine] = counts.get(truth.doctrine, 0) + 1

    nodes = tuple(
        sorted(
            (
                PrimaryDirectionLatitudeNetworkNode(doctrine=doctrine, count=count)
                for doctrine, count in counts.items()
            ),
            key=lambda node: node.doctrine.value,
        )
    )

    edge_counts: dict[tuple[PrimaryDirectionLatitudeDoctrine, PrimaryDirectionLatitudeDoctrine], int] = {}
    for left, right in zip(truth_tuple, truth_tuple[1:]):
        if left.doctrine == right.doctrine:
            continue
        key = (left.doctrine, right.doctrine)
        edge_counts[key] = edge_counts.get(key, 0) + 1

    edges = tuple(
        sorted(
            (
                PrimaryDirectionLatitudeNetworkEdge(
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
        sorted(
            (node.doctrine for node in nodes if node.doctrine not in participating),
            key=lambda doctrine: doctrine.value,
        )
    )
    return PrimaryDirectionLatitudeNetworkProfile(
        nodes=nodes,
        edges=edges,
        dominant_doctrine=dominant,
        isolated_doctrines=isolated,
    )
