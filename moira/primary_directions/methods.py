"""
Moira -- primary_directions/methods.py
Standalone method-doctrine owner for the primary-directions subsystem.

Boundary
--------
Owns the doctrinal identity, classification, and hardened interpretation of
currently admitted primary-direction method families.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

from ._ordered_network import validate_ordered_transition_counts

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
    """Vessel: Registry of architectural primary direction methods."""
    PLACIDUS_MUNDANE = "placidus_mundane"
    PTOLEMY_SEMI_ARC = "ptolemy_semi_arc"
    PLACIDIAN_CLASSIC_SEMI_ARC = "placidian_classic_semi_arc"
    MERIDIAN = "meridian"
    MORINUS = "morinus"
    REGIOMONTANUS = "regiomontanus"
    CAMPANUS = "campanus"
    TOPOCENTRIC = "topocentric"


class PrimaryDirectionMethodKind(StrEnum):
    """Vessel: Registry of primary direction method kinds."""
    PLACIDUS_MUNDANE = "placidus_mundane"
    PTOLEMY_SEMI_ARC = "ptolemy_semi_arc"
    PLACIDIAN_CLASSIC_SEMI_ARC = "placidian_classic_semi_arc"
    MERIDIAN = "meridian"
    MORINUS = "morinus"
    REGIOMONTANUS = "regiomontanus"
    CAMPANUS = "campanus"
    TOPOCENTRIC = "topocentric"


class PrimaryDirectionMethodRelationKind(StrEnum):
    """Vessel: Registry of perfection relation types for methods."""
    PLACIDIAN_MUNDANE_PERFECTION = "placidian_mundane_perfection"
    PTOLEMAIC_SEMI_ARC_PERFECTION = "ptolemaic_semi_arc_perfection"
    PLACIDIAN_CLASSIC_SEMI_ARC_PERFECTION = "placidian_classic_semi_arc_perfection"
    MERIDIAN_EQUATORIAL_PERFECTION = "meridian_equatorial_perfection"
    MORINIAN_UNDER_POLE_PERFECTION = "morinian_under_pole_perfection"
    REGIOMONTANIAN_UNDER_POLE_PERFECTION = "regiomontanian_under_pole_perfection"
    CAMPANIAN_UNDER_POLE_PERFECTION = "campanian_under_pole_perfection"
    TOPOCENTRIC_UNDER_POLE_PERFECTION = "topocentric_under_pole_perfection"


class PrimaryDirectionMethodConditionState(StrEnum):
    """Vessel: Registry of condition states for direction methods."""
    MUNDANE_SEMI_ARC_GROUNDED = "mundane_semi_arc_grounded"
    PTOLEMAIC_SEMI_ARC_GROUNDED = "ptolemaic_semi_arc_grounded"
    CLASSIC_SEMI_ARC_GROUNDED = "classic_semi_arc_grounded"
    EQUATORIAL_GROUNDED = "equatorial_grounded"
    MORINIAN_UNDER_POLE_GROUNDED = "morinian_under_pole_grounded"
    UNDER_POLE_GROUNDED = "under_pole_grounded"
    PRIME_VERTICAL_UNDER_POLE_GROUNDED = "prime_vertical_under_pole_grounded"
    TOPOCENTRIC_UNDER_POLE_GROUNDED = "topocentric_under_pole_grounded"


@dataclass(frozen=True, slots=True)
class PrimaryDirectionMethodPolicy:
    """Vessel: Policy definition for primary direction method selection."""
    method: PrimaryDirectionMethod = PrimaryDirectionMethod.PLACIDUS_MUNDANE

    def __post_init__(self) -> None:
        if not isinstance(self.method, PrimaryDirectionMethod):
            raise ValueError(f"Unsupported primary direction method: {self.method}")
        if self.method not in (
            PrimaryDirectionMethod.PLACIDUS_MUNDANE,
            PrimaryDirectionMethod.PTOLEMY_SEMI_ARC,
            PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC,
            PrimaryDirectionMethod.MERIDIAN,
            PrimaryDirectionMethod.MORINUS,
            PrimaryDirectionMethod.REGIOMONTANUS,
            PrimaryDirectionMethod.CAMPANUS,
            PrimaryDirectionMethod.TOPOCENTRIC,
        ):
            raise ValueError(f"Unsupported primary direction method: {self.method}")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionMethodTruth:
    """Vessel: Immutable architectural truth for a direction method."""
    method: PrimaryDirectionMethod
    kind: PrimaryDirectionMethodKind
    uses_semi_arcs: bool
    uses_world_frame_geometry: bool
    latitude_sensitive: bool
    under_pole_based: bool

    def __post_init__(self) -> None:
        if not isinstance(self.method, PrimaryDirectionMethod):
            raise ValueError(f"Unsupported primary direction method on truth: {self.method}")
        if not isinstance(self.kind, PrimaryDirectionMethodKind):
            raise ValueError(f"Unsupported primary direction method kind: {self.kind}")
        if any(
            type(flag) is not bool
            for flag in (
                self.uses_semi_arcs,
                self.uses_world_frame_geometry,
                self.latitude_sensitive,
                self.under_pole_based,
            )
        ):
            raise ValueError("PrimaryDirectionMethodTruth invariant failed: trait flags must be bool")
        expected = {
            PrimaryDirectionMethod.PLACIDUS_MUNDANE: (
                PrimaryDirectionMethodKind.PLACIDUS_MUNDANE,
                True,
                True,
                True,
                False,
            ),
            PrimaryDirectionMethod.PTOLEMY_SEMI_ARC: (
                PrimaryDirectionMethodKind.PTOLEMY_SEMI_ARC,
                True,
                True,
                True,
                False,
            ),
            PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC: (
                PrimaryDirectionMethodKind.PLACIDIAN_CLASSIC_SEMI_ARC,
                True,
                True,
                True,
                False,
            ),
            PrimaryDirectionMethod.MERIDIAN: (
                PrimaryDirectionMethodKind.MERIDIAN,
                False,
                True,
                True,
                False,
            ),
            PrimaryDirectionMethod.MORINUS: (
                PrimaryDirectionMethodKind.MORINUS,
                False,
                True,
                True,
                True,
            ),
            PrimaryDirectionMethod.REGIOMONTANUS: (
                PrimaryDirectionMethodKind.REGIOMONTANUS,
                False,
                True,
                True,
                True,
            ),
            PrimaryDirectionMethod.CAMPANUS: (
                PrimaryDirectionMethodKind.CAMPANUS,
                False,
                True,
                True,
                True,
            ),
            PrimaryDirectionMethod.TOPOCENTRIC: (
                PrimaryDirectionMethodKind.TOPOCENTRIC,
                False,
                True,
                True,
                True,
            ),
        }.get(self.method)
        if expected is None:
            raise ValueError(f"Unsupported primary direction method on truth: {self.method}")
        if (
            self.kind,
            self.uses_semi_arcs,
            self.uses_world_frame_geometry,
            self.latitude_sensitive,
            self.under_pole_based,
        ) != expected:
            raise ValueError(
                "PrimaryDirectionMethodTruth invariant failed: current admitted method traits mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionMethodClassification:
    """Vessel: Result of classifying a method based on its traits."""
    truth: PrimaryDirectionMethodTruth
    mundane: bool
    zodiacal: bool
    semi_arc_based: bool
    under_pole_based: bool

    def __post_init__(self) -> None:
        if not isinstance(self.truth, PrimaryDirectionMethodTruth):
            raise ValueError("PrimaryDirectionMethodClassification invariant failed: invalid truth")
        if any(
            type(flag) is not bool
            for flag in (self.mundane, self.zodiacal, self.semi_arc_based, self.under_pole_based)
        ):
            raise ValueError(
                "PrimaryDirectionMethodClassification invariant failed: flags must be bool"
            )
        expected = {
            PrimaryDirectionMethod.PLACIDUS_MUNDANE: (True, False, True, False),
            PrimaryDirectionMethod.PTOLEMY_SEMI_ARC: (True, True, True, False),
            PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC: (True, False, True, False),
            PrimaryDirectionMethod.MERIDIAN: (True, True, False, False),
            PrimaryDirectionMethod.MORINUS: (True, True, False, True),
            PrimaryDirectionMethod.REGIOMONTANUS: (True, True, False, True),
            PrimaryDirectionMethod.CAMPANUS: (True, True, False, True),
            PrimaryDirectionMethod.TOPOCENTRIC: (True, True, False, True),
        }[self.truth.method]
        actual = (self.mundane, self.zodiacal, self.semi_arc_based, self.under_pole_based)
        if actual != expected:
            raise ValueError(
                "PrimaryDirectionMethodClassification invariant failed: current admitted method classification mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionMethodRelation:
    """Vessel: Established relation between a method and the system."""
    truth: PrimaryDirectionMethodTruth
    relation_kind: PrimaryDirectionMethodRelationKind

    def __post_init__(self) -> None:
        if not isinstance(self.truth, PrimaryDirectionMethodTruth):
            raise ValueError("PrimaryDirectionMethodRelation invariant failed: invalid truth")
        if not isinstance(self.relation_kind, PrimaryDirectionMethodRelationKind):
            raise ValueError(
                "PrimaryDirectionMethodRelation invariant failed: relation_kind must be an enum member"
            )
        expected_kind = {
            PrimaryDirectionMethod.PLACIDUS_MUNDANE: PrimaryDirectionMethodRelationKind.PLACIDIAN_MUNDANE_PERFECTION,
            PrimaryDirectionMethod.PTOLEMY_SEMI_ARC: PrimaryDirectionMethodRelationKind.PTOLEMAIC_SEMI_ARC_PERFECTION,
            PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC: PrimaryDirectionMethodRelationKind.PLACIDIAN_CLASSIC_SEMI_ARC_PERFECTION,
            PrimaryDirectionMethod.MERIDIAN: PrimaryDirectionMethodRelationKind.MERIDIAN_EQUATORIAL_PERFECTION,
            PrimaryDirectionMethod.MORINUS: PrimaryDirectionMethodRelationKind.MORINIAN_UNDER_POLE_PERFECTION,
            PrimaryDirectionMethod.REGIOMONTANUS: PrimaryDirectionMethodRelationKind.REGIOMONTANIAN_UNDER_POLE_PERFECTION,
            PrimaryDirectionMethod.CAMPANUS: PrimaryDirectionMethodRelationKind.CAMPANIAN_UNDER_POLE_PERFECTION,
            PrimaryDirectionMethod.TOPOCENTRIC: PrimaryDirectionMethodRelationKind.TOPOCENTRIC_UNDER_POLE_PERFECTION,
        }[self.truth.method]
        if self.relation_kind is not expected_kind:
            raise ValueError("PrimaryDirectionMethodRelation invariant failed: relation_kind mismatch")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionMethodRelationProfile:
    """Vessel: Comprehensive profile of relations for a method."""
    truth: PrimaryDirectionMethodTruth
    detected_relation: PrimaryDirectionMethodRelation
    admitted_relations: tuple[PrimaryDirectionMethodRelation, ...]
    scored_relations: tuple[PrimaryDirectionMethodRelation, ...]

    def __post_init__(self) -> None:
        try:
            admitted_relations = tuple(self.admitted_relations)
            scored_relations = tuple(self.scored_relations)
        except TypeError as exc:
            raise ValueError(
                "PrimaryDirectionMethodRelationProfile invariant failed: relation collections must be iterable"
            ) from exc
        object.__setattr__(self, "admitted_relations", admitted_relations)
        object.__setattr__(self, "scored_relations", scored_relations)
        if not isinstance(self.truth, PrimaryDirectionMethodTruth):
            raise ValueError("PrimaryDirectionMethodRelationProfile invariant failed: invalid truth")
        if not isinstance(self.detected_relation, PrimaryDirectionMethodRelation):
            raise ValueError(
                "PrimaryDirectionMethodRelationProfile invariant failed: invalid detected relation"
            )
        if self.detected_relation.truth != self.truth:
            raise ValueError(
                "PrimaryDirectionMethodRelationProfile invariant failed: detected relation truth mismatch"
            )
        if self.admitted_relations != (self.detected_relation,):
            raise ValueError(
                "PrimaryDirectionMethodRelationProfile invariant failed: current doctrine admits exactly the detected relation"
            )
        if self.scored_relations != self.admitted_relations:
            raise ValueError(
                "PrimaryDirectionMethodRelationProfile invariant failed: admitted relation must be scored"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionMethodConditionProfile:
    """Vessel: Final condition profile for a primary direction method."""
    truth: PrimaryDirectionMethodTruth
    classification: PrimaryDirectionMethodClassification
    relation_profile: PrimaryDirectionMethodRelationProfile
    state: PrimaryDirectionMethodConditionState

    def __post_init__(self) -> None:
        if not isinstance(self.truth, PrimaryDirectionMethodTruth):
            raise ValueError("PrimaryDirectionMethodConditionProfile invariant failed: invalid truth")
        if not isinstance(self.classification, PrimaryDirectionMethodClassification):
            raise ValueError(
                "PrimaryDirectionMethodConditionProfile invariant failed: invalid classification"
            )
        if not isinstance(self.relation_profile, PrimaryDirectionMethodRelationProfile):
            raise ValueError(
                "PrimaryDirectionMethodConditionProfile invariant failed: invalid relation profile"
            )
        if not isinstance(self.state, PrimaryDirectionMethodConditionState):
            raise ValueError(
                "PrimaryDirectionMethodConditionProfile invariant failed: state must be an enum member"
            )
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
            PrimaryDirectionMethod.PTOLEMY_SEMI_ARC: PrimaryDirectionMethodConditionState.PTOLEMAIC_SEMI_ARC_GROUNDED,
            PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC: PrimaryDirectionMethodConditionState.CLASSIC_SEMI_ARC_GROUNDED,
            PrimaryDirectionMethod.MERIDIAN: PrimaryDirectionMethodConditionState.EQUATORIAL_GROUNDED,
            PrimaryDirectionMethod.MORINUS: PrimaryDirectionMethodConditionState.MORINIAN_UNDER_POLE_GROUNDED,
            PrimaryDirectionMethod.REGIOMONTANUS: PrimaryDirectionMethodConditionState.UNDER_POLE_GROUNDED,
            PrimaryDirectionMethod.CAMPANUS: PrimaryDirectionMethodConditionState.PRIME_VERTICAL_UNDER_POLE_GROUNDED,
            PrimaryDirectionMethod.TOPOCENTRIC: PrimaryDirectionMethodConditionState.TOPOCENTRIC_UNDER_POLE_GROUNDED,
        }[self.truth.method]
        if self.state is not expected_state:
            raise ValueError("PrimaryDirectionMethodConditionProfile invariant failed: state mismatch")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionMethodsAggregateProfile:
    """Vessel: Aggregated profile of multiple method conditions."""
    profiles: tuple[PrimaryDirectionMethodConditionProfile, ...]
    total_profiles: int
    mundane_count: int
    semi_arc_count: int
    under_pole_count: int

    def __post_init__(self) -> None:
        try:
            profiles = tuple(self.profiles)
        except TypeError as exc:
            raise ValueError(
                "PrimaryDirectionMethodsAggregateProfile invariant failed: profiles must be iterable"
            ) from exc
        object.__setattr__(self, "profiles", profiles)
        if not self.profiles:
            raise ValueError("PrimaryDirectionMethodsAggregateProfile requires at least one profile")
        if any(not isinstance(profile, PrimaryDirectionMethodConditionProfile) for profile in self.profiles):
            raise ValueError("PrimaryDirectionMethodsAggregateProfile invariant failed: invalid profile type")
        if any(
            type(count) is not int or count < 0
            for count in (
                self.total_profiles,
                self.mundane_count,
                self.semi_arc_count,
                self.under_pole_count,
            )
        ):
            raise ValueError(
                "PrimaryDirectionMethodsAggregateProfile invariant failed: counts must be non-negative integers"
            )
        if self.total_profiles != len(self.profiles):
            raise ValueError(
                "PrimaryDirectionMethodsAggregateProfile invariant failed: total_profiles mismatch"
            )
        if self.mundane_count != sum(1 for profile in self.profiles if profile.classification.mundane):
            raise ValueError(
                "PrimaryDirectionMethodsAggregateProfile invariant failed: mundane_count mismatch"
            )
        if self.semi_arc_count != sum(1 for profile in self.profiles if profile.truth.uses_semi_arcs):
            raise ValueError(
                "PrimaryDirectionMethodsAggregateProfile invariant failed: semi_arc_count mismatch"
            )
        if self.under_pole_count != sum(1 for profile in self.profiles if profile.truth.under_pole_based):
            raise ValueError(
                "PrimaryDirectionMethodsAggregateProfile invariant failed: under_pole_count mismatch"
            )

    @property
    def zodiacal_count(self) -> int:
        """Number of methods capable of zodiacal-space computation."""
        return sum(1 for profile in self.profiles if profile.classification.zodiacal)


@dataclass(frozen=True, slots=True)
class PrimaryDirectionMethodsNetworkNode:
    """Vessel: Node in a primary direction methods network."""
    method: PrimaryDirectionMethod
    count: int

    def __post_init__(self) -> None:
        if not isinstance(self.method, PrimaryDirectionMethod):
            raise ValueError("PrimaryDirectionMethodsNetworkNode invariant failed: invalid method")
        if type(self.count) is not int or self.count <= 0:
            raise ValueError("PrimaryDirectionMethodsNetworkNode invariant failed: count must be positive")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionMethodsNetworkEdge:
    """Vessel: Directed edge in a primary direction methods network."""
    from_method: PrimaryDirectionMethod
    to_method: PrimaryDirectionMethod
    count: int

    def __post_init__(self) -> None:
        if not isinstance(self.from_method, PrimaryDirectionMethod) or not isinstance(
            self.to_method, PrimaryDirectionMethod
        ):
            raise ValueError("PrimaryDirectionMethodsNetworkEdge invariant failed: invalid method")
        if self.from_method == self.to_method:
            raise ValueError(
                "PrimaryDirectionMethodsNetworkEdge invariant failed: self-edges are not admitted"
            )
        if type(self.count) is not int or self.count <= 0:
            raise ValueError("PrimaryDirectionMethodsNetworkEdge invariant failed: count must be positive")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionMethodsNetworkProfile:
    """Vessel: Structural profile of an ordered method-transition network."""
    nodes: tuple[PrimaryDirectionMethodsNetworkNode, ...]
    edges: tuple[PrimaryDirectionMethodsNetworkEdge, ...]
    dominant_method: PrimaryDirectionMethod
    isolated_methods: tuple[PrimaryDirectionMethod, ...]

    def __post_init__(self) -> None:
        try:
            nodes = tuple(self.nodes)
            edges = tuple(self.edges)
            isolated_methods = tuple(self.isolated_methods)
        except TypeError as exc:
            raise ValueError(
                "PrimaryDirectionMethodsNetworkProfile invariant failed: network collections must be iterable"
            ) from exc
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "edges", edges)
        object.__setattr__(self, "isolated_methods", isolated_methods)
        if not self.nodes:
            raise ValueError("PrimaryDirectionMethodsNetworkProfile requires at least one node")
        if any(not isinstance(node, PrimaryDirectionMethodsNetworkNode) for node in self.nodes):
            raise ValueError("PrimaryDirectionMethodsNetworkProfile invariant failed: invalid node type")
        if any(not isinstance(edge, PrimaryDirectionMethodsNetworkEdge) for edge in self.edges):
            raise ValueError("PrimaryDirectionMethodsNetworkProfile invariant failed: invalid edge type")
        if not isinstance(self.dominant_method, PrimaryDirectionMethod):
            raise ValueError("PrimaryDirectionMethodsNetworkProfile invariant failed: invalid dominant_method")
        if any(not isinstance(method, PrimaryDirectionMethod) for method in self.isolated_methods):
            raise ValueError("PrimaryDirectionMethodsNetworkProfile invariant failed: invalid isolated method")
        methods = [node.method for node in self.nodes]
        if len(set(methods)) != len(methods):
            raise ValueError(
                "PrimaryDirectionMethodsNetworkProfile invariant failed: duplicate nodes"
            )
        if len(set(self.isolated_methods)) != len(self.isolated_methods):
            raise ValueError(
                "PrimaryDirectionMethodsNetworkProfile invariant failed: duplicate isolated methods"
            )
        edge_keys = [(edge.from_method, edge.to_method) for edge in self.edges]
        if len(set(edge_keys)) != len(edge_keys):
            raise ValueError("PrimaryDirectionMethodsNetworkProfile invariant failed: duplicate edges")
        node_by_method = {node.method: node for node in self.nodes}
        if any(
            edge.from_method not in node_by_method or edge.to_method not in node_by_method
            for edge in self.edges
        ):
            raise ValueError(
                "PrimaryDirectionMethodsNetworkProfile invariant failed: edge endpoint missing from nodes"
            )
        if any(
            edge.count
            > min(node_by_method[edge.from_method].count, node_by_method[edge.to_method].count)
            for edge in self.edges
        ):
            raise ValueError(
                "PrimaryDirectionMethodsNetworkProfile invariant failed: edge count exceeds endpoint occurrence count"
            )
        if sum(edge.count for edge in self.edges) > sum(node.count for node in self.nodes) - 1:
            raise ValueError(
                "PrimaryDirectionMethodsNetworkProfile invariant failed: edge count exceeds possible transitions"
            )
        validate_ordered_transition_counts(
            {node.method: node.count for node in self.nodes},
            {(edge.from_method, edge.to_method): edge.count for edge in self.edges},
            object_name="PrimaryDirectionMethodsNetworkProfile",
        )
        expected_dominant = max(
            self.nodes,
            key=lambda node: (node.count, node.method.value),
        ).method
        if self.dominant_method is not expected_dominant:
            raise ValueError(
                "PrimaryDirectionMethodsNetworkProfile invariant failed: dominant_method mismatch"
            )
        participating = {edge.from_method for edge in self.edges} | {
            edge.to_method for edge in self.edges
        }
        expected_isolated = tuple(
            sorted(
                (method for method in methods if method not in participating),
                key=lambda method: method.value,
            )
        )
        if self.isolated_methods != expected_isolated:
            raise ValueError(
                "PrimaryDirectionMethodsNetworkProfile invariant failed: isolated_methods mismatch"
            )


def primary_direction_method_truth(
    method: PrimaryDirectionMethod = PrimaryDirectionMethod.PLACIDUS_MUNDANE,
    *,
    policy: PrimaryDirectionMethodPolicy | None = None,
) -> PrimaryDirectionMethodTruth:
    if not isinstance(method, PrimaryDirectionMethod):
        raise ValueError(f"Unsupported primary direction method: {method}")
    if policy is not None and not isinstance(policy, PrimaryDirectionMethodPolicy):
        raise ValueError("policy must be a PrimaryDirectionMethodPolicy")
    resolved_policy = policy if policy is not None else PrimaryDirectionMethodPolicy(method)
    return PrimaryDirectionMethodTruth(
        method=resolved_policy.method,
        kind={
            PrimaryDirectionMethod.PLACIDUS_MUNDANE: PrimaryDirectionMethodKind.PLACIDUS_MUNDANE,
            PrimaryDirectionMethod.PTOLEMY_SEMI_ARC: PrimaryDirectionMethodKind.PTOLEMY_SEMI_ARC,
            PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC: PrimaryDirectionMethodKind.PLACIDIAN_CLASSIC_SEMI_ARC,
            PrimaryDirectionMethod.MERIDIAN: PrimaryDirectionMethodKind.MERIDIAN,
            PrimaryDirectionMethod.MORINUS: PrimaryDirectionMethodKind.MORINUS,
            PrimaryDirectionMethod.REGIOMONTANUS: PrimaryDirectionMethodKind.REGIOMONTANUS,
            PrimaryDirectionMethod.CAMPANUS: PrimaryDirectionMethodKind.CAMPANUS,
            PrimaryDirectionMethod.TOPOCENTRIC: PrimaryDirectionMethodKind.TOPOCENTRIC,
        }[resolved_policy.method],
        uses_semi_arcs=resolved_policy.method in (
            PrimaryDirectionMethod.PLACIDUS_MUNDANE,
            PrimaryDirectionMethod.PTOLEMY_SEMI_ARC,
            PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC,
        ),
        uses_world_frame_geometry=True,
        latitude_sensitive=True,
        under_pole_based=resolved_policy.method in (
            PrimaryDirectionMethod.MORINUS,
            PrimaryDirectionMethod.REGIOMONTANUS,
            PrimaryDirectionMethod.CAMPANUS,
            PrimaryDirectionMethod.TOPOCENTRIC,
        ),
    )


def classify_primary_direction_method(
    truth: PrimaryDirectionMethodTruth,
) -> PrimaryDirectionMethodClassification:
    if not isinstance(truth, PrimaryDirectionMethodTruth):
        raise ValueError("truth must be a PrimaryDirectionMethodTruth")
    return PrimaryDirectionMethodClassification(
        truth=truth,
        mundane=True,
        zodiacal=truth.method in (
            PrimaryDirectionMethod.PTOLEMY_SEMI_ARC,
            PrimaryDirectionMethod.MERIDIAN,
            PrimaryDirectionMethod.MORINUS,
            PrimaryDirectionMethod.REGIOMONTANUS,
            PrimaryDirectionMethod.CAMPANUS,
            PrimaryDirectionMethod.TOPOCENTRIC,
        ),
        semi_arc_based=truth.uses_semi_arcs,
        under_pole_based=truth.under_pole_based,
    )


def relate_primary_direction_method(
    truth: PrimaryDirectionMethodTruth,
) -> PrimaryDirectionMethodRelation:
    if not isinstance(truth, PrimaryDirectionMethodTruth):
        raise ValueError("truth must be a PrimaryDirectionMethodTruth")
    return PrimaryDirectionMethodRelation(
        truth=truth,
        relation_kind={
            PrimaryDirectionMethod.PLACIDUS_MUNDANE: PrimaryDirectionMethodRelationKind.PLACIDIAN_MUNDANE_PERFECTION,
            PrimaryDirectionMethod.PTOLEMY_SEMI_ARC: PrimaryDirectionMethodRelationKind.PTOLEMAIC_SEMI_ARC_PERFECTION,
            PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC: PrimaryDirectionMethodRelationKind.PLACIDIAN_CLASSIC_SEMI_ARC_PERFECTION,
            PrimaryDirectionMethod.MERIDIAN: PrimaryDirectionMethodRelationKind.MERIDIAN_EQUATORIAL_PERFECTION,
            PrimaryDirectionMethod.MORINUS: PrimaryDirectionMethodRelationKind.MORINIAN_UNDER_POLE_PERFECTION,
            PrimaryDirectionMethod.REGIOMONTANUS: PrimaryDirectionMethodRelationKind.REGIOMONTANIAN_UNDER_POLE_PERFECTION,
            PrimaryDirectionMethod.CAMPANUS: PrimaryDirectionMethodRelationKind.CAMPANIAN_UNDER_POLE_PERFECTION,
            PrimaryDirectionMethod.TOPOCENTRIC: PrimaryDirectionMethodRelationKind.TOPOCENTRIC_UNDER_POLE_PERFECTION,
        }[truth.method],
    )


def evaluate_primary_direction_method_relations(
    truth: PrimaryDirectionMethodTruth,
) -> PrimaryDirectionMethodRelationProfile:
    if not isinstance(truth, PrimaryDirectionMethodTruth):
        raise ValueError("truth must be a PrimaryDirectionMethodTruth")
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
    if not isinstance(truth, PrimaryDirectionMethodTruth):
        raise ValueError("truth must be a PrimaryDirectionMethodTruth")
    return PrimaryDirectionMethodConditionProfile(
        truth=truth,
        classification=classify_primary_direction_method(truth),
        relation_profile=evaluate_primary_direction_method_relations(truth),
        state={
            PrimaryDirectionMethod.PLACIDUS_MUNDANE: PrimaryDirectionMethodConditionState.MUNDANE_SEMI_ARC_GROUNDED,
            PrimaryDirectionMethod.PTOLEMY_SEMI_ARC: PrimaryDirectionMethodConditionState.PTOLEMAIC_SEMI_ARC_GROUNDED,
            PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC: PrimaryDirectionMethodConditionState.CLASSIC_SEMI_ARC_GROUNDED,
            PrimaryDirectionMethod.MERIDIAN: PrimaryDirectionMethodConditionState.EQUATORIAL_GROUNDED,
            PrimaryDirectionMethod.MORINUS: PrimaryDirectionMethodConditionState.MORINIAN_UNDER_POLE_GROUNDED,
            PrimaryDirectionMethod.REGIOMONTANUS: PrimaryDirectionMethodConditionState.UNDER_POLE_GROUNDED,
            PrimaryDirectionMethod.CAMPANUS: PrimaryDirectionMethodConditionState.PRIME_VERTICAL_UNDER_POLE_GROUNDED,
            PrimaryDirectionMethod.TOPOCENTRIC: PrimaryDirectionMethodConditionState.TOPOCENTRIC_UNDER_POLE_GROUNDED,
        }[truth.method],
    )


def evaluate_primary_direction_methods_aggregate(
    truths: Iterable[PrimaryDirectionMethodTruth],
) -> PrimaryDirectionMethodsAggregateProfile:
    try:
        truth_tuple = tuple(truths)
    except TypeError as exc:
        raise ValueError("truths must be an iterable of PrimaryDirectionMethodTruth") from exc
    profiles = tuple(evaluate_primary_direction_method_condition(truth) for truth in truth_tuple)
    if not profiles:
        raise ValueError("evaluate_primary_direction_methods_aggregate requires at least one truth")
    return PrimaryDirectionMethodsAggregateProfile(
        profiles=profiles,
        total_profiles=len(profiles),
        mundane_count=sum(1 for profile in profiles if profile.classification.mundane),
        semi_arc_count=sum(1 for profile in profiles if profile.truth.uses_semi_arcs),
        under_pole_count=sum(1 for profile in profiles if profile.truth.under_pole_based),
    )


def evaluate_primary_direction_methods_network(
    truths: Iterable[PrimaryDirectionMethodTruth],
) -> PrimaryDirectionMethodsNetworkProfile:
    """Build transitions between consecutive truths in caller-supplied order."""
    try:
        truth_tuple = tuple(truths)
    except TypeError as exc:
        raise ValueError("truths must be an iterable of PrimaryDirectionMethodTruth") from exc
    if not truth_tuple:
        raise ValueError("evaluate_primary_direction_methods_network requires at least one truth")
    if any(not isinstance(truth, PrimaryDirectionMethodTruth) for truth in truth_tuple):
        raise ValueError("truths must contain only PrimaryDirectionMethodTruth values")
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
                PrimaryDirectionMethodsNetworkEdge(
                    from_method=from_method,
                    to_method=to_method,
                    count=count,
                )
                for (from_method, to_method), count in edge_counts.items()
            ),
            key=lambda edge: (edge.from_method.value, edge.to_method.value),
        )
    )
    dominant = max(nodes, key=lambda node: (node.count, node.method.value)).method
    participating = {edge.from_method for edge in edges} | {edge.to_method for edge in edges}
    isolated = tuple(
        sorted((node.method for node in nodes if node.method not in participating), key=lambda m: m.value)
    )
    return PrimaryDirectionMethodsNetworkProfile(
        nodes=nodes,
        edges=edges,
        dominant_method=dominant,
        isolated_methods=isolated,
    )
