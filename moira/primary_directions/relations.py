"""
Moira -- primary_directions/relations.py
Standalone relation-doctrine owner for the primary-directions subsystem.

Boundary
--------
Owns the doctrinal identity, classification, and admission policy for the
relation classes that may count as primary-direction perfections.
"""

from __future__ import annotations

from dataclasses import dataclass
from .._strenum import StrEnum
from typing import Iterable

from ._ordered_network import validate_ordered_transition_counts

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
    """Vessel: Registry of architectural relation kinds for primary directions."""
    CONJUNCTION = "conjunction"
    OPPOSITION = "opposition"
    ZODIACAL_ASPECT = "zodiacal_aspect"
    ANTISCION = "antiscion"
    CONTRA_ANTISCION = "contra_antiscion"
    PARALLEL = "parallel"
    CONTRA_PARALLEL = "contra_parallel"
    RAPT_PARALLEL = "rapt_parallel"


class PrimaryDirectionRelationalMode(StrEnum):
    """Vessel: Registry of relational modes."""
    POSITIONAL = "positional"
    DECLINATIONAL = "declinational"


class PrimaryDirectionRelationalConditionState(StrEnum):
    """Vessel: Registry of condition states for relations."""
    POSITIONAL_ADMITTED = "positional_admitted"
    POSITIONAL_REJECTED = "positional_rejected"
    DECLINATIONAL_ADMITTED = "declinational_admitted"
    DECLINATIONAL_REJECTED = "declinational_rejected"


@dataclass(frozen=True, slots=True)
class PrimaryDirectionRelationPolicy:
    """Vessel: Policy definition for admitted relation kinds."""
    admitted_kinds: frozenset[PrimaryDirectionRelationalKind] = frozenset(
        {
            PrimaryDirectionRelationalKind.CONJUNCTION,
            PrimaryDirectionRelationalKind.OPPOSITION,
            PrimaryDirectionRelationalKind.ZODIACAL_ASPECT,
        }
    )

    def __post_init__(self) -> None:
        try:
            admitted_kinds = frozenset(self.admitted_kinds)
        except TypeError as exc:
            raise ValueError(
                "PrimaryDirectionRelationPolicy invariant failed: admitted_kinds must be iterable"
            ) from exc
        object.__setattr__(self, "admitted_kinds", admitted_kinds)
        if not self.admitted_kinds:
            raise ValueError("PrimaryDirectionRelationPolicy invariant failed: admitted_kinds may not be empty")
        if not all(isinstance(kind, PrimaryDirectionRelationalKind) for kind in self.admitted_kinds):
            raise ValueError("Unsupported primary direction relation kinds")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionRelationalTruth:
    """Vessel: Immutable architectural truth for a relational kind."""
    kind: PrimaryDirectionRelationalKind
    mode: PrimaryDirectionRelationalMode
    derived_point_realizable: bool

    def __post_init__(self) -> None:
        if not isinstance(self.kind, PrimaryDirectionRelationalKind):
            raise ValueError(f"Unsupported primary direction relational kind: {self.kind}")
        if not isinstance(self.mode, PrimaryDirectionRelationalMode):
            raise ValueError(f"Unsupported primary direction relational mode: {self.mode}")
        if type(self.derived_point_realizable) is not bool:
            raise ValueError(
                "PrimaryDirectionRelationalTruth invariant failed: derived_point_realizable must be bool"
            )
        expected = {
            PrimaryDirectionRelationalKind.CONJUNCTION: (
                PrimaryDirectionRelationalMode.POSITIONAL,
                False,
            ),
            PrimaryDirectionRelationalKind.OPPOSITION: (
                PrimaryDirectionRelationalMode.POSITIONAL,
                True,
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
    """Vessel: Result of classifying a relational kind based on its traits."""
    truth: PrimaryDirectionRelationalTruth
    positional: bool
    declinational: bool

    def __post_init__(self) -> None:
        if not isinstance(self.truth, PrimaryDirectionRelationalTruth):
            raise ValueError(
                "PrimaryDirectionRelationalClassification invariant failed: truth must be relational truth"
            )
        if type(self.positional) is not bool or type(self.declinational) is not bool:
            raise ValueError(
                "PrimaryDirectionRelationalClassification invariant failed: flags must be bool"
            )
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
    """Vessel: Established relation between a relational kind and the system."""
    truth: PrimaryDirectionRelationalTruth
    relation_kind: PrimaryDirectionRelationalKind

    def __post_init__(self) -> None:
        if not isinstance(self.truth, PrimaryDirectionRelationalTruth):
            raise ValueError(
                "PrimaryDirectionRelationalRelation invariant failed: truth must be relational truth"
            )
        if not isinstance(self.relation_kind, PrimaryDirectionRelationalKind):
            raise ValueError(
                "PrimaryDirectionRelationalRelation invariant failed: relation_kind must be an enum member"
            )
        if self.relation_kind is not self.truth.kind:
            raise ValueError(
                "PrimaryDirectionRelationalRelation invariant failed: relation_kind must match truth.kind"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionRelationalRelationProfile:
    """Vessel: Comprehensive profile of relations for a relational kind."""
    truth: PrimaryDirectionRelationalTruth
    detected_relation: PrimaryDirectionRelationalRelation
    admitted_relations: tuple[PrimaryDirectionRelationalRelation, ...]
    scored_relations: tuple[PrimaryDirectionRelationalRelation, ...]

    def __post_init__(self) -> None:
        try:
            admitted_relations = tuple(self.admitted_relations)
            scored_relations = tuple(self.scored_relations)
        except TypeError as exc:
            raise ValueError(
                "PrimaryDirectionRelationalRelationProfile invariant failed: relation collections must be iterable"
            ) from exc
        object.__setattr__(self, "admitted_relations", admitted_relations)
        object.__setattr__(self, "scored_relations", scored_relations)
        if not isinstance(self.truth, PrimaryDirectionRelationalTruth):
            raise ValueError(
                "PrimaryDirectionRelationalRelationProfile invariant failed: truth must be relational truth"
            )
        if not isinstance(self.detected_relation, PrimaryDirectionRelationalRelation):
            raise ValueError(
                "PrimaryDirectionRelationalRelationProfile invariant failed: detected_relation has invalid type"
            )
        if self.detected_relation.truth != self.truth:
            raise ValueError(
                "PrimaryDirectionRelationalRelationProfile invariant failed: detected relation truth mismatch"
            )
        for label, relations in (
            ("admitted", self.admitted_relations),
            ("scored", self.scored_relations),
        ):
            if any(
                not isinstance(relation, PrimaryDirectionRelationalRelation)
                or relation.truth != self.truth
                for relation in relations
            ):
                raise ValueError(
                    f"PrimaryDirectionRelationalRelationProfile invariant failed: {label} relation truth mismatch"
                )
            if len(set(relations)) != len(relations):
                raise ValueError(
                    f"PrimaryDirectionRelationalRelationProfile invariant failed: duplicate {label} relations"
                )
        if any(relation not in self.admitted_relations for relation in self.scored_relations):
            raise ValueError(
                "PrimaryDirectionRelationalRelationProfile invariant failed: scored relation must be admitted"
            )
        if self.admitted_relations not in ((), (self.detected_relation,)):
            raise ValueError(
                "PrimaryDirectionRelationalRelationProfile invariant failed: current doctrine admits only the detected relation"
            )
        if self.scored_relations != self.admitted_relations:
            raise ValueError(
                "PrimaryDirectionRelationalRelationProfile invariant failed: admitted relation must be scored"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionRelationalConditionProfile:
    """Vessel: Final condition profile for a primary direction relation."""
    truth: PrimaryDirectionRelationalTruth
    classification: PrimaryDirectionRelationalClassification
    relation_profile: PrimaryDirectionRelationalRelationProfile
    state: PrimaryDirectionRelationalConditionState

    def __post_init__(self) -> None:
        if not isinstance(self.truth, PrimaryDirectionRelationalTruth):
            raise ValueError(
                "PrimaryDirectionRelationalConditionProfile invariant failed: truth must be relational truth"
            )
        if not isinstance(self.classification, PrimaryDirectionRelationalClassification):
            raise ValueError(
                "PrimaryDirectionRelationalConditionProfile invariant failed: invalid classification"
            )
        if not isinstance(self.relation_profile, PrimaryDirectionRelationalRelationProfile):
            raise ValueError(
                "PrimaryDirectionRelationalConditionProfile invariant failed: invalid relation profile"
            )
        if not isinstance(self.state, PrimaryDirectionRelationalConditionState):
            raise ValueError(
                "PrimaryDirectionRelationalConditionProfile invariant failed: state must be an enum member"
            )
        if self.classification.truth != self.truth:
            raise ValueError(
                "PrimaryDirectionRelationalConditionProfile invariant failed: classification truth mismatch"
            )
        if self.relation_profile.truth != self.truth:
            raise ValueError(
                "PrimaryDirectionRelationalConditionProfile invariant failed: relation truth mismatch"
            )
        admitted = self.relation_profile.detected_relation in self.relation_profile.admitted_relations
        expected_state = {
            (PrimaryDirectionRelationalMode.POSITIONAL, True): (
                PrimaryDirectionRelationalConditionState.POSITIONAL_ADMITTED
            ),
            (PrimaryDirectionRelationalMode.POSITIONAL, False): (
                PrimaryDirectionRelationalConditionState.POSITIONAL_REJECTED
            ),
            (PrimaryDirectionRelationalMode.DECLINATIONAL, True): (
                PrimaryDirectionRelationalConditionState.DECLINATIONAL_ADMITTED
            ),
            (PrimaryDirectionRelationalMode.DECLINATIONAL, False): (
                PrimaryDirectionRelationalConditionState.DECLINATIONAL_REJECTED
            ),
        }[(self.truth.mode, admitted)]
        if self.state is not expected_state:
            raise ValueError(
                "PrimaryDirectionRelationalConditionProfile invariant failed: state does not match admission"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionRelationsAggregateProfile:
    """Vessel: Aggregated profile of multiple relation conditions."""
    profiles: tuple[PrimaryDirectionRelationalConditionProfile, ...]
    total_profiles: int
    positional_count: int
    declinational_count: int

    def __post_init__(self) -> None:
        try:
            profiles = tuple(self.profiles)
        except TypeError as exc:
            raise ValueError(
                "PrimaryDirectionRelationsAggregateProfile invariant failed: profiles must be iterable"
            ) from exc
        object.__setattr__(self, "profiles", profiles)
        if not self.profiles:
            raise ValueError("PrimaryDirectionRelationsAggregateProfile requires at least one profile")
        if any(not isinstance(profile, PrimaryDirectionRelationalConditionProfile) for profile in self.profiles):
            raise ValueError(
                "PrimaryDirectionRelationsAggregateProfile invariant failed: invalid profile type"
            )
        if any(
            type(count) is not int or count < 0
            for count in (self.total_profiles, self.positional_count, self.declinational_count)
        ):
            raise ValueError(
                "PrimaryDirectionRelationsAggregateProfile invariant failed: counts must be non-negative integers"
            )
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
        if self.positional_count + self.declinational_count != self.total_profiles:
            raise ValueError(
                "PrimaryDirectionRelationsAggregateProfile invariant failed: mode counts must partition profiles"
            )

    @property
    def admitted_count(self) -> int:
        """Number of relation truths admitted by the evaluated policy."""
        return sum(
            1
            for profile in self.profiles
            if profile.relation_profile.detected_relation
            in profile.relation_profile.admitted_relations
        )

    @property
    def rejected_count(self) -> int:
        """Number of relation truths rejected by the evaluated policy."""
        return self.total_profiles - self.admitted_count


@dataclass(frozen=True, slots=True)
class PrimaryDirectionRelationsNetworkNode:
    """Vessel: Node in a primary direction relations network."""
    kind: PrimaryDirectionRelationalKind
    count: int

    def __post_init__(self) -> None:
        if not isinstance(self.kind, PrimaryDirectionRelationalKind):
            raise ValueError("PrimaryDirectionRelationsNetworkNode invariant failed: invalid kind")
        if type(self.count) is not int or self.count <= 0:
            raise ValueError("PrimaryDirectionRelationsNetworkNode invariant failed: count must be positive")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionRelationsNetworkEdge:
    """Vessel: Directed edge in a primary direction relations network."""
    from_kind: PrimaryDirectionRelationalKind
    to_kind: PrimaryDirectionRelationalKind
    count: int

    def __post_init__(self) -> None:
        if not isinstance(self.from_kind, PrimaryDirectionRelationalKind) or not isinstance(
            self.to_kind, PrimaryDirectionRelationalKind
        ):
            raise ValueError("PrimaryDirectionRelationsNetworkEdge invariant failed: invalid kind")
        if self.from_kind == self.to_kind:
            raise ValueError(
                "PrimaryDirectionRelationsNetworkEdge invariant failed: self-edges are not admitted"
            )
        if type(self.count) is not int or self.count <= 0:
            raise ValueError("PrimaryDirectionRelationsNetworkEdge invariant failed: count must be positive")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionRelationsNetworkProfile:
    """Vessel: Structural profile of an ordered relation-transition network."""
    nodes: tuple[PrimaryDirectionRelationsNetworkNode, ...]
    edges: tuple[PrimaryDirectionRelationsNetworkEdge, ...]
    dominant_kind: PrimaryDirectionRelationalKind
    isolated_kinds: tuple[PrimaryDirectionRelationalKind, ...]

    def __post_init__(self) -> None:
        try:
            nodes = tuple(self.nodes)
            edges = tuple(self.edges)
            isolated_kinds = tuple(self.isolated_kinds)
        except TypeError as exc:
            raise ValueError(
                "PrimaryDirectionRelationsNetworkProfile invariant failed: network collections must be iterable"
            ) from exc
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "edges", edges)
        object.__setattr__(self, "isolated_kinds", isolated_kinds)
        if not self.nodes:
            raise ValueError("PrimaryDirectionRelationsNetworkProfile requires at least one node")
        if any(not isinstance(node, PrimaryDirectionRelationsNetworkNode) for node in self.nodes):
            raise ValueError("PrimaryDirectionRelationsNetworkProfile invariant failed: invalid node type")
        if any(not isinstance(edge, PrimaryDirectionRelationsNetworkEdge) for edge in self.edges):
            raise ValueError("PrimaryDirectionRelationsNetworkProfile invariant failed: invalid edge type")
        if not isinstance(self.dominant_kind, PrimaryDirectionRelationalKind):
            raise ValueError("PrimaryDirectionRelationsNetworkProfile invariant failed: invalid dominant_kind")
        if any(not isinstance(kind, PrimaryDirectionRelationalKind) for kind in self.isolated_kinds):
            raise ValueError("PrimaryDirectionRelationsNetworkProfile invariant failed: invalid isolated kind")
        kinds = [node.kind for node in self.nodes]
        if len(set(kinds)) != len(kinds):
            raise ValueError(
                "PrimaryDirectionRelationsNetworkProfile invariant failed: duplicate nodes"
            )
        if len(set(self.isolated_kinds)) != len(self.isolated_kinds):
            raise ValueError(
                "PrimaryDirectionRelationsNetworkProfile invariant failed: duplicate isolated kinds"
            )
        edge_keys = [(edge.from_kind, edge.to_kind) for edge in self.edges]
        if len(set(edge_keys)) != len(edge_keys):
            raise ValueError(
                "PrimaryDirectionRelationsNetworkProfile invariant failed: duplicate edges"
            )
        node_by_kind = {node.kind: node for node in self.nodes}
        if any(
            edge.from_kind not in node_by_kind or edge.to_kind not in node_by_kind
            for edge in self.edges
        ):
            raise ValueError(
                "PrimaryDirectionRelationsNetworkProfile invariant failed: edge endpoint missing from nodes"
            )
        if any(
            edge.count > min(node_by_kind[edge.from_kind].count, node_by_kind[edge.to_kind].count)
            for edge in self.edges
        ):
            raise ValueError(
                "PrimaryDirectionRelationsNetworkProfile invariant failed: edge count exceeds endpoint occurrence count"
            )
        if sum(edge.count for edge in self.edges) > sum(node.count for node in self.nodes) - 1:
            raise ValueError(
                "PrimaryDirectionRelationsNetworkProfile invariant failed: edge count exceeds possible transitions"
            )
        validate_ordered_transition_counts(
            {node.kind: node.count for node in self.nodes},
            {(edge.from_kind, edge.to_kind): edge.count for edge in self.edges},
            object_name="PrimaryDirectionRelationsNetworkProfile",
        )
        expected_dominant = max(self.nodes, key=lambda node: (node.count, node.kind.value)).kind
        if self.dominant_kind is not expected_dominant:
            raise ValueError(
                "PrimaryDirectionRelationsNetworkProfile invariant failed: dominant_kind mismatch"
            )
        participating = {edge.from_kind for edge in self.edges} | {edge.to_kind for edge in self.edges}
        expected_isolated = tuple(
            sorted((kind for kind in kinds if kind not in participating), key=lambda kind: kind.value)
        )
        if self.isolated_kinds != expected_isolated:
            raise ValueError(
                "PrimaryDirectionRelationsNetworkProfile invariant failed: isolated_kinds mismatch"
            )


def primary_direction_relational_truth(
    kind: PrimaryDirectionRelationalKind = PrimaryDirectionRelationalKind.CONJUNCTION,
    *,
    policy: PrimaryDirectionRelationPolicy | None = None,
) -> PrimaryDirectionRelationalTruth:
    if not isinstance(kind, PrimaryDirectionRelationalKind):
        raise ValueError(f"Unsupported primary direction relational kind: {kind}")
    if policy is not None and not isinstance(policy, PrimaryDirectionRelationPolicy):
        raise ValueError("policy must be a PrimaryDirectionRelationPolicy")
    resolved_kind = kind
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
                PrimaryDirectionRelationalKind.OPPOSITION,
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
    if not isinstance(truth, PrimaryDirectionRelationalTruth):
        raise ValueError("truth must be a PrimaryDirectionRelationalTruth")
    return PrimaryDirectionRelationalClassification(
        truth=truth,
        positional=truth.mode is PrimaryDirectionRelationalMode.POSITIONAL,
        declinational=truth.mode is PrimaryDirectionRelationalMode.DECLINATIONAL,
    )


def relate_primary_direction_relation(
    truth: PrimaryDirectionRelationalTruth,
) -> PrimaryDirectionRelationalRelation:
    if not isinstance(truth, PrimaryDirectionRelationalTruth):
        raise ValueError("truth must be a PrimaryDirectionRelationalTruth")
    return PrimaryDirectionRelationalRelation(
        truth=truth,
        relation_kind=truth.kind,
    )


def evaluate_primary_direction_relation_relations(
    truth: PrimaryDirectionRelationalTruth,
    *,
    policy: PrimaryDirectionRelationPolicy | None = None,
) -> PrimaryDirectionRelationalRelationProfile:
    if not isinstance(truth, PrimaryDirectionRelationalTruth):
        raise ValueError("truth must be a PrimaryDirectionRelationalTruth")
    if policy is not None and not isinstance(policy, PrimaryDirectionRelationPolicy):
        raise ValueError("policy must be a PrimaryDirectionRelationPolicy")
    resolved_policy = policy if policy is not None else PrimaryDirectionRelationPolicy()
    relation = relate_primary_direction_relation(truth)
    admitted = (
        (relation,)
        if relation.relation_kind in resolved_policy.admitted_kinds
        else ()
    )
    scored = admitted
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
    if not isinstance(truth, PrimaryDirectionRelationalTruth):
        raise ValueError("truth must be a PrimaryDirectionRelationalTruth")
    if policy is not None and not isinstance(policy, PrimaryDirectionRelationPolicy):
        raise ValueError("policy must be a PrimaryDirectionRelationPolicy")
    relation_profile = evaluate_primary_direction_relation_relations(truth, policy=policy)
    admitted = relation_profile.detected_relation in relation_profile.admitted_relations
    return PrimaryDirectionRelationalConditionProfile(
        truth=truth,
        classification=classify_primary_direction_relation(truth),
        relation_profile=relation_profile,
        state=(
            (
                PrimaryDirectionRelationalConditionState.DECLINATIONAL_ADMITTED
                if admitted
                else PrimaryDirectionRelationalConditionState.DECLINATIONAL_REJECTED
            )
            if truth.mode is PrimaryDirectionRelationalMode.DECLINATIONAL
            else (
                PrimaryDirectionRelationalConditionState.POSITIONAL_ADMITTED
                if admitted
                else PrimaryDirectionRelationalConditionState.POSITIONAL_REJECTED
            )
        ),
    )


def evaluate_primary_direction_relations_aggregate(
    truths: Iterable[PrimaryDirectionRelationalTruth],
    *,
    policy: PrimaryDirectionRelationPolicy | None = None,
) -> PrimaryDirectionRelationsAggregateProfile:
    if policy is not None and not isinstance(policy, PrimaryDirectionRelationPolicy):
        raise ValueError("policy must be a PrimaryDirectionRelationPolicy")
    try:
        truth_tuple = tuple(truths)
    except TypeError as exc:
        raise ValueError("truths must be an iterable of PrimaryDirectionRelationalTruth") from exc
    profiles = tuple(
        evaluate_primary_direction_relation_condition(truth, policy=policy)
        for truth in truth_tuple
    )
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
    """Build transitions between consecutive truths in caller-supplied order."""
    try:
        truth_tuple = tuple(truths)
    except TypeError as exc:
        raise ValueError("truths must be an iterable of PrimaryDirectionRelationalTruth") from exc
    if not truth_tuple:
        raise ValueError("evaluate_primary_direction_relations_network requires at least one truth")
    if any(not isinstance(truth, PrimaryDirectionRelationalTruth) for truth in truth_tuple):
        raise ValueError("truths must contain only PrimaryDirectionRelationalTruth values")
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
