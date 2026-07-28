"""
Moira -- primary_directions/perfections.py
Standalone perfection-doctrine owner for the primary-directions subsystem.

Boundary
--------
Owns the doctrinal identity, classification, and hardened interpretation of
currently admitted perfection kinds in the primary-directions family.
"""

from __future__ import annotations

from dataclasses import dataclass
from .._strenum import StrEnum
from typing import Iterable

from ._ordered_network import validate_ordered_transition_counts

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
    """Vessel: Registry of architectural perfection kinds."""
    MUNDANE_POSITION_PERFECTION = "mundane_position_perfection"
    ZODIACAL_LONGITUDE_PERFECTION = "zodiacal_longitude_perfection"
    ZODIACAL_PROJECTED_PERFECTION = "zodiacal_projected_perfection"


class PrimaryDirectionPerfectionMode(StrEnum):
    """Vessel: Registry of perfection modes."""
    POSITIONAL = "positional"


class PrimaryDirectionPerfectionConditionState(StrEnum):
    """Vessel: Registry of condition states for perfection."""
    MUNDANE_POSITIONAL = "mundane_positional"
    ZODIACAL_POSITIONAL = "zodiacal_positional"
    ZODIACAL_PROJECTED = "zodiacal_projected"


@dataclass(frozen=True, slots=True)
class PrimaryDirectionPerfectionPolicy:
    """Vessel: Policy definition for perfection kind selection."""
    kind: PrimaryDirectionPerfectionKind = PrimaryDirectionPerfectionKind.MUNDANE_POSITION_PERFECTION

    def __post_init__(self) -> None:
        if not isinstance(self.kind, PrimaryDirectionPerfectionKind):
            raise ValueError(f"Unsupported primary direction perfection kind: {self.kind}")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionPerfectionTruth:
    """Vessel: Immutable architectural truth for a perfection kind."""
    kind: PrimaryDirectionPerfectionKind
    mode: PrimaryDirectionPerfectionMode
    uses_significator_mundane_fraction: bool
    world_frame_based: bool

    def __post_init__(self) -> None:
        if not isinstance(self.kind, PrimaryDirectionPerfectionKind):
            raise ValueError(f"Unsupported primary direction perfection kind on truth: {self.kind}")
        if not isinstance(self.mode, PrimaryDirectionPerfectionMode):
            raise ValueError(f"Unsupported primary direction perfection mode: {self.mode}")
        if (
            type(self.uses_significator_mundane_fraction) is not bool
            or type(self.world_frame_based) is not bool
        ):
            raise ValueError(
                "PrimaryDirectionPerfectionTruth invariant failed: trait flags must be bool"
            )
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
    """Vessel: Result of classifying a perfection kind based on its traits."""
    truth: PrimaryDirectionPerfectionTruth
    positional: bool
    aspectual: bool

    def __post_init__(self) -> None:
        if not isinstance(self.truth, PrimaryDirectionPerfectionTruth):
            raise ValueError(
                "PrimaryDirectionPerfectionClassification invariant failed: invalid truth"
            )
        if type(self.positional) is not bool or type(self.aspectual) is not bool:
            raise ValueError(
                "PrimaryDirectionPerfectionClassification invariant failed: flags must be bool"
            )
        if self.positional is not True or self.aspectual is not False:
            raise ValueError(
                "PrimaryDirectionPerfectionClassification invariant failed: current admitted perfection classification mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionPerfectionRelation:
    """Vessel: Established relation between a perfection kind and the system."""
    truth: PrimaryDirectionPerfectionTruth
    relation_kind: PrimaryDirectionPerfectionKind

    def __post_init__(self) -> None:
        if not isinstance(self.truth, PrimaryDirectionPerfectionTruth):
            raise ValueError("PrimaryDirectionPerfectionRelation invariant failed: invalid truth")
        if not isinstance(self.relation_kind, PrimaryDirectionPerfectionKind):
            raise ValueError(
                "PrimaryDirectionPerfectionRelation invariant failed: relation_kind must be an enum member"
            )
        if self.relation_kind is not self.truth.kind:
            raise ValueError(
                "PrimaryDirectionPerfectionRelation invariant failed: relation_kind must match truth.kind"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionPerfectionRelationProfile:
    """Vessel: Comprehensive profile of relations for a perfection kind."""
    truth: PrimaryDirectionPerfectionTruth
    detected_relation: PrimaryDirectionPerfectionRelation
    admitted_relations: tuple[PrimaryDirectionPerfectionRelation, ...]
    scored_relations: tuple[PrimaryDirectionPerfectionRelation, ...]

    def __post_init__(self) -> None:
        try:
            admitted_relations = tuple(self.admitted_relations)
            scored_relations = tuple(self.scored_relations)
        except TypeError as exc:
            raise ValueError(
                "PrimaryDirectionPerfectionRelationProfile invariant failed: relation collections must be iterable"
            ) from exc
        object.__setattr__(self, "admitted_relations", admitted_relations)
        object.__setattr__(self, "scored_relations", scored_relations)
        if not isinstance(self.truth, PrimaryDirectionPerfectionTruth):
            raise ValueError("PrimaryDirectionPerfectionRelationProfile invariant failed: invalid truth")
        if not isinstance(self.detected_relation, PrimaryDirectionPerfectionRelation):
            raise ValueError(
                "PrimaryDirectionPerfectionRelationProfile invariant failed: invalid detected relation"
            )
        if self.detected_relation.truth != self.truth:
            raise ValueError(
                "PrimaryDirectionPerfectionRelationProfile invariant failed: detected relation truth mismatch"
            )
        if self.admitted_relations != (self.detected_relation,):
            raise ValueError(
                "PrimaryDirectionPerfectionRelationProfile invariant failed: current doctrine admits exactly the detected relation"
            )
        if self.scored_relations != self.admitted_relations:
            raise ValueError(
                "PrimaryDirectionPerfectionRelationProfile invariant failed: admitted relation must be scored"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionPerfectionConditionProfile:
    """Vessel: Final condition profile for a primary direction perfection."""
    truth: PrimaryDirectionPerfectionTruth
    classification: PrimaryDirectionPerfectionClassification
    relation_profile: PrimaryDirectionPerfectionRelationProfile
    state: PrimaryDirectionPerfectionConditionState

    def __post_init__(self) -> None:
        if not isinstance(self.truth, PrimaryDirectionPerfectionTruth):
            raise ValueError("PrimaryDirectionPerfectionConditionProfile invariant failed: invalid truth")
        if not isinstance(self.classification, PrimaryDirectionPerfectionClassification):
            raise ValueError(
                "PrimaryDirectionPerfectionConditionProfile invariant failed: invalid classification"
            )
        if not isinstance(self.relation_profile, PrimaryDirectionPerfectionRelationProfile):
            raise ValueError(
                "PrimaryDirectionPerfectionConditionProfile invariant failed: invalid relation profile"
            )
        if not isinstance(self.state, PrimaryDirectionPerfectionConditionState):
            raise ValueError(
                "PrimaryDirectionPerfectionConditionProfile invariant failed: state must be an enum member"
            )
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
    """Vessel: Aggregated profile of multiple perfection conditions."""
    profiles: tuple[PrimaryDirectionPerfectionConditionProfile, ...]
    total_profiles: int
    positional_count: int
    world_frame_count: int

    def __post_init__(self) -> None:
        try:
            profiles = tuple(self.profiles)
        except TypeError as exc:
            raise ValueError(
                "PrimaryDirectionPerfectionsAggregateProfile invariant failed: profiles must be iterable"
            ) from exc
        object.__setattr__(self, "profiles", profiles)
        if not self.profiles:
            raise ValueError("PrimaryDirectionPerfectionsAggregateProfile requires at least one profile")
        if any(not isinstance(profile, PrimaryDirectionPerfectionConditionProfile) for profile in self.profiles):
            raise ValueError(
                "PrimaryDirectionPerfectionsAggregateProfile invariant failed: invalid profile type"
            )
        if any(
            type(count) is not int or count < 0
            for count in (self.total_profiles, self.positional_count, self.world_frame_count)
        ):
            raise ValueError(
                "PrimaryDirectionPerfectionsAggregateProfile invariant failed: counts must be non-negative integers"
            )
        if self.total_profiles != len(self.profiles):
            raise ValueError(
                "PrimaryDirectionPerfectionsAggregateProfile invariant failed: total_profiles mismatch"
            )
        if self.positional_count != sum(
            1 for profile in self.profiles if profile.classification.positional
        ):
            raise ValueError(
                "PrimaryDirectionPerfectionsAggregateProfile invariant failed: positional_count mismatch"
            )
        if self.world_frame_count != sum(1 for profile in self.profiles if profile.truth.world_frame_based):
            raise ValueError(
                "PrimaryDirectionPerfectionsAggregateProfile invariant failed: world_frame_count mismatch"
            )

    @property
    def mundane_position_count(self) -> int:
        return sum(
            1
            for profile in self.profiles
            if profile.truth.kind
            is PrimaryDirectionPerfectionKind.MUNDANE_POSITION_PERFECTION
        )

    @property
    def zodiacal_longitude_count(self) -> int:
        return sum(
            1
            for profile in self.profiles
            if profile.truth.kind
            is PrimaryDirectionPerfectionKind.ZODIACAL_LONGITUDE_PERFECTION
        )

    @property
    def zodiacal_projected_count(self) -> int:
        return sum(
            1
            for profile in self.profiles
            if profile.truth.kind
            is PrimaryDirectionPerfectionKind.ZODIACAL_PROJECTED_PERFECTION
        )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionPerfectionsNetworkNode:
    """Vessel: Node in a primary direction perfections network."""
    kind: PrimaryDirectionPerfectionKind
    count: int

    def __post_init__(self) -> None:
        if not isinstance(self.kind, PrimaryDirectionPerfectionKind):
            raise ValueError("PrimaryDirectionPerfectionsNetworkNode invariant failed: invalid kind")
        if type(self.count) is not int or self.count <= 0:
            raise ValueError("PrimaryDirectionPerfectionsNetworkNode invariant failed: count must be positive")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionPerfectionsNetworkEdge:
    """Vessel: Directed edge in a primary direction perfections network."""
    from_kind: PrimaryDirectionPerfectionKind
    to_kind: PrimaryDirectionPerfectionKind
    count: int

    def __post_init__(self) -> None:
        if not isinstance(self.from_kind, PrimaryDirectionPerfectionKind) or not isinstance(
            self.to_kind, PrimaryDirectionPerfectionKind
        ):
            raise ValueError("PrimaryDirectionPerfectionsNetworkEdge invariant failed: invalid kind")
        if self.from_kind == self.to_kind:
            raise ValueError(
                "PrimaryDirectionPerfectionsNetworkEdge invariant failed: self-edges are not admitted"
            )
        if type(self.count) is not int or self.count <= 0:
            raise ValueError("PrimaryDirectionPerfectionsNetworkEdge invariant failed: count must be positive")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionPerfectionsNetworkProfile:
    """Vessel: Structural profile of an ordered perfection-transition network."""
    nodes: tuple[PrimaryDirectionPerfectionsNetworkNode, ...]
    edges: tuple[PrimaryDirectionPerfectionsNetworkEdge, ...]
    dominant_kind: PrimaryDirectionPerfectionKind
    isolated_kinds: tuple[PrimaryDirectionPerfectionKind, ...]

    def __post_init__(self) -> None:
        try:
            nodes = tuple(self.nodes)
            edges = tuple(self.edges)
            isolated_kinds = tuple(self.isolated_kinds)
        except TypeError as exc:
            raise ValueError(
                "PrimaryDirectionPerfectionsNetworkProfile invariant failed: network collections must be iterable"
            ) from exc
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "edges", edges)
        object.__setattr__(self, "isolated_kinds", isolated_kinds)
        if not self.nodes:
            raise ValueError("PrimaryDirectionPerfectionsNetworkProfile requires at least one node")
        if any(not isinstance(node, PrimaryDirectionPerfectionsNetworkNode) for node in self.nodes):
            raise ValueError("PrimaryDirectionPerfectionsNetworkProfile invariant failed: invalid node type")
        if any(not isinstance(edge, PrimaryDirectionPerfectionsNetworkEdge) for edge in self.edges):
            raise ValueError("PrimaryDirectionPerfectionsNetworkProfile invariant failed: invalid edge type")
        if not isinstance(self.dominant_kind, PrimaryDirectionPerfectionKind):
            raise ValueError("PrimaryDirectionPerfectionsNetworkProfile invariant failed: invalid dominant_kind")
        if any(not isinstance(kind, PrimaryDirectionPerfectionKind) for kind in self.isolated_kinds):
            raise ValueError("PrimaryDirectionPerfectionsNetworkProfile invariant failed: invalid isolated kind")
        kinds = [node.kind for node in self.nodes]
        if len(set(kinds)) != len(kinds):
            raise ValueError(
                "PrimaryDirectionPerfectionsNetworkProfile invariant failed: duplicate nodes"
            )
        if len(set(self.isolated_kinds)) != len(self.isolated_kinds):
            raise ValueError(
                "PrimaryDirectionPerfectionsNetworkProfile invariant failed: duplicate isolated kinds"
            )
        edge_keys = [(edge.from_kind, edge.to_kind) for edge in self.edges]
        if len(set(edge_keys)) != len(edge_keys):
            raise ValueError(
                "PrimaryDirectionPerfectionsNetworkProfile invariant failed: duplicate edges"
            )
        node_by_kind = {node.kind: node for node in self.nodes}
        if any(
            edge.from_kind not in node_by_kind or edge.to_kind not in node_by_kind
            for edge in self.edges
        ):
            raise ValueError(
                "PrimaryDirectionPerfectionsNetworkProfile invariant failed: edge endpoint missing from nodes"
            )
        if any(
            edge.count > min(node_by_kind[edge.from_kind].count, node_by_kind[edge.to_kind].count)
            for edge in self.edges
        ):
            raise ValueError(
                "PrimaryDirectionPerfectionsNetworkProfile invariant failed: edge count exceeds endpoint occurrence count"
            )
        if sum(edge.count for edge in self.edges) > sum(node.count for node in self.nodes) - 1:
            raise ValueError(
                "PrimaryDirectionPerfectionsNetworkProfile invariant failed: edge count exceeds possible transitions"
            )
        validate_ordered_transition_counts(
            {node.kind: node.count for node in self.nodes},
            {(edge.from_kind, edge.to_kind): edge.count for edge in self.edges},
            object_name="PrimaryDirectionPerfectionsNetworkProfile",
        )
        expected_dominant = max(self.nodes, key=lambda node: (node.count, node.kind.value)).kind
        if self.dominant_kind is not expected_dominant:
            raise ValueError(
                "PrimaryDirectionPerfectionsNetworkProfile invariant failed: dominant_kind mismatch"
            )
        participating = {edge.from_kind for edge in self.edges} | {edge.to_kind for edge in self.edges}
        expected_isolated = tuple(
            sorted((kind for kind in kinds if kind not in participating), key=lambda kind: kind.value)
        )
        if self.isolated_kinds != expected_isolated:
            raise ValueError(
                "PrimaryDirectionPerfectionsNetworkProfile invariant failed: isolated_kinds mismatch"
            )


def primary_direction_perfection_truth(
    kind: PrimaryDirectionPerfectionKind = PrimaryDirectionPerfectionKind.MUNDANE_POSITION_PERFECTION,
    *,
    policy: PrimaryDirectionPerfectionPolicy | None = None,
) -> PrimaryDirectionPerfectionTruth:
    if not isinstance(kind, PrimaryDirectionPerfectionKind):
        raise ValueError(f"Unsupported primary direction perfection kind: {kind}")
    if policy is not None and not isinstance(policy, PrimaryDirectionPerfectionPolicy):
        raise ValueError("policy must be a PrimaryDirectionPerfectionPolicy")
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
    if not isinstance(truth, PrimaryDirectionPerfectionTruth):
        raise ValueError("truth must be a PrimaryDirectionPerfectionTruth")
    return PrimaryDirectionPerfectionClassification(
        truth=truth,
        positional=True,
        aspectual=False,
    )


def relate_primary_direction_perfection(
    truth: PrimaryDirectionPerfectionTruth,
) -> PrimaryDirectionPerfectionRelation:
    if not isinstance(truth, PrimaryDirectionPerfectionTruth):
        raise ValueError("truth must be a PrimaryDirectionPerfectionTruth")
    return PrimaryDirectionPerfectionRelation(
        truth=truth,
        relation_kind=truth.kind,
    )


def evaluate_primary_direction_perfection_relations(
    truth: PrimaryDirectionPerfectionTruth,
) -> PrimaryDirectionPerfectionRelationProfile:
    if not isinstance(truth, PrimaryDirectionPerfectionTruth):
        raise ValueError("truth must be a PrimaryDirectionPerfectionTruth")
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
    if not isinstance(truth, PrimaryDirectionPerfectionTruth):
        raise ValueError("truth must be a PrimaryDirectionPerfectionTruth")
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
    try:
        truth_tuple = tuple(truths)
    except TypeError as exc:
        raise ValueError("truths must be an iterable of PrimaryDirectionPerfectionTruth") from exc
    profiles = tuple(evaluate_primary_direction_perfection_condition(truth) for truth in truth_tuple)
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
    """Build transitions between consecutive truths in caller-supplied order."""
    try:
        truth_tuple = tuple(truths)
    except TypeError as exc:
        raise ValueError("truths must be an iterable of PrimaryDirectionPerfectionTruth") from exc
    if not truth_tuple:
        raise ValueError("evaluate_primary_direction_perfections_network requires at least one truth")
    if any(not isinstance(truth, PrimaryDirectionPerfectionTruth) for truth in truth_tuple):
        raise ValueError("truths must contain only PrimaryDirectionPerfectionTruth values")
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
