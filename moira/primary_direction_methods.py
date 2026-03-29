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
    PTOLEMY_SEMI_ARC = "ptolemy_semi_arc"
    PLACIDIAN_CLASSIC_SEMI_ARC = "placidian_classic_semi_arc"
    MERIDIAN = "meridian"
    MORINUS = "morinus"
    REGIOMONTANUS = "regiomontanus"
    CAMPANUS = "campanus"
    TOPOCENTRIC = "topocentric"


class PrimaryDirectionMethodKind(StrEnum):
    PLACIDUS_MUNDANE = "placidus_mundane"
    PTOLEMY_SEMI_ARC = "ptolemy_semi_arc"
    PLACIDIAN_CLASSIC_SEMI_ARC = "placidian_classic_semi_arc"
    MERIDIAN = "meridian"
    MORINUS = "morinus"
    REGIOMONTANUS = "regiomontanus"
    CAMPANUS = "campanus"
    TOPOCENTRIC = "topocentric"


class PrimaryDirectionMethodRelationKind(StrEnum):
    PLACIDIAN_MUNDANE_PERFECTION = "placidian_mundane_perfection"
    PTOLEMAIC_SEMI_ARC_PERFECTION = "ptolemaic_semi_arc_perfection"
    PLACIDIAN_CLASSIC_SEMI_ARC_PERFECTION = "placidian_classic_semi_arc_perfection"
    MERIDIAN_EQUATORIAL_PERFECTION = "meridian_equatorial_perfection"
    MORINIAN_EQUATORIAL_PERFECTION = "morinian_equatorial_perfection"
    REGIOMONTANIAN_UNDER_POLE_PERFECTION = "regiomontanian_under_pole_perfection"
    CAMPANIAN_UNDER_POLE_PERFECTION = "campanian_under_pole_perfection"
    TOPOCENTRIC_UNDER_POLE_PERFECTION = "topocentric_under_pole_perfection"


class PrimaryDirectionMethodConditionState(StrEnum):
    MUNDANE_SEMI_ARC_GROUNDED = "mundane_semi_arc_grounded"
    PTOLEMAIC_SEMI_ARC_GROUNDED = "ptolemaic_semi_arc_grounded"
    CLASSIC_SEMI_ARC_GROUNDED = "classic_semi_arc_grounded"
    EQUATORIAL_GROUNDED = "equatorial_grounded"
    MORINIAN_GROUNDED = "morinian_grounded"
    UNDER_POLE_GROUNDED = "under_pole_grounded"
    PRIME_VERTICAL_UNDER_POLE_GROUNDED = "prime_vertical_under_pole_grounded"
    TOPOCENTRIC_UNDER_POLE_GROUNDED = "topocentric_under_pole_grounded"


@dataclass(frozen=True, slots=True)
class PrimaryDirectionMethodPolicy:
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
    method: PrimaryDirectionMethod
    kind: PrimaryDirectionMethodKind
    uses_semi_arcs: bool
    uses_world_frame_geometry: bool
    latitude_sensitive: bool
    under_pole_based: bool

    def __post_init__(self) -> None:
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
                False,
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
    truth: PrimaryDirectionMethodTruth
    mundane: bool
    zodiacal: bool
    semi_arc_based: bool
    under_pole_based: bool

    def __post_init__(self) -> None:
        expected = {
            PrimaryDirectionMethod.PLACIDUS_MUNDANE: (True, False, True, False),
            PrimaryDirectionMethod.PTOLEMY_SEMI_ARC: (True, False, True, False),
            PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC: (True, False, True, False),
            PrimaryDirectionMethod.MERIDIAN: (True, True, False, False),
            PrimaryDirectionMethod.MORINUS: (True, True, False, False),
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
    truth: PrimaryDirectionMethodTruth
    relation_kind: PrimaryDirectionMethodRelationKind

    def __post_init__(self) -> None:
        expected_kind = {
            PrimaryDirectionMethod.PLACIDUS_MUNDANE: PrimaryDirectionMethodRelationKind.PLACIDIAN_MUNDANE_PERFECTION,
            PrimaryDirectionMethod.PTOLEMY_SEMI_ARC: PrimaryDirectionMethodRelationKind.PTOLEMAIC_SEMI_ARC_PERFECTION,
            PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC: PrimaryDirectionMethodRelationKind.PLACIDIAN_CLASSIC_SEMI_ARC_PERFECTION,
            PrimaryDirectionMethod.MERIDIAN: PrimaryDirectionMethodRelationKind.MERIDIAN_EQUATORIAL_PERFECTION,
            PrimaryDirectionMethod.MORINUS: PrimaryDirectionMethodRelationKind.MORINIAN_EQUATORIAL_PERFECTION,
            PrimaryDirectionMethod.REGIOMONTANUS: PrimaryDirectionMethodRelationKind.REGIOMONTANIAN_UNDER_POLE_PERFECTION,
            PrimaryDirectionMethod.CAMPANUS: PrimaryDirectionMethodRelationKind.CAMPANIAN_UNDER_POLE_PERFECTION,
            PrimaryDirectionMethod.TOPOCENTRIC: PrimaryDirectionMethodRelationKind.TOPOCENTRIC_UNDER_POLE_PERFECTION,
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
            PrimaryDirectionMethod.PTOLEMY_SEMI_ARC: PrimaryDirectionMethodConditionState.PTOLEMAIC_SEMI_ARC_GROUNDED,
            PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC: PrimaryDirectionMethodConditionState.CLASSIC_SEMI_ARC_GROUNDED,
            PrimaryDirectionMethod.MERIDIAN: PrimaryDirectionMethodConditionState.EQUATORIAL_GROUNDED,
            PrimaryDirectionMethod.MORINUS: PrimaryDirectionMethodConditionState.MORINIAN_GROUNDED,
            PrimaryDirectionMethod.REGIOMONTANUS: PrimaryDirectionMethodConditionState.UNDER_POLE_GROUNDED,
            PrimaryDirectionMethod.CAMPANUS: PrimaryDirectionMethodConditionState.PRIME_VERTICAL_UNDER_POLE_GROUNDED,
            PrimaryDirectionMethod.TOPOCENTRIC: PrimaryDirectionMethodConditionState.TOPOCENTRIC_UNDER_POLE_GROUNDED,
        }[self.truth.method]
        if self.state is not expected_state:
            raise ValueError("PrimaryDirectionMethodConditionProfile invariant failed: state mismatch")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionMethodsAggregateProfile:
    profiles: tuple[PrimaryDirectionMethodConditionProfile, ...]
    total_profiles: int
    mundane_count: int
    semi_arc_count: int
    under_pole_count: int

    def __post_init__(self) -> None:
        if not self.profiles:
            raise ValueError("PrimaryDirectionMethodsAggregateProfile requires at least one profile")
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
            PrimaryDirectionMethod.REGIOMONTANUS,
            PrimaryDirectionMethod.CAMPANUS,
            PrimaryDirectionMethod.TOPOCENTRIC,
        ),
    )


def classify_primary_direction_method(
    truth: PrimaryDirectionMethodTruth,
) -> PrimaryDirectionMethodClassification:
    return PrimaryDirectionMethodClassification(
        truth=truth,
        mundane=True,
        zodiacal=truth.method in (
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
    return PrimaryDirectionMethodRelation(
        truth=truth,
        relation_kind={
            PrimaryDirectionMethod.PLACIDUS_MUNDANE: PrimaryDirectionMethodRelationKind.PLACIDIAN_MUNDANE_PERFECTION,
            PrimaryDirectionMethod.PTOLEMY_SEMI_ARC: PrimaryDirectionMethodRelationKind.PTOLEMAIC_SEMI_ARC_PERFECTION,
            PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC: PrimaryDirectionMethodRelationKind.PLACIDIAN_CLASSIC_SEMI_ARC_PERFECTION,
            PrimaryDirectionMethod.MERIDIAN: PrimaryDirectionMethodRelationKind.MERIDIAN_EQUATORIAL_PERFECTION,
            PrimaryDirectionMethod.MORINUS: PrimaryDirectionMethodRelationKind.MORINIAN_EQUATORIAL_PERFECTION,
            PrimaryDirectionMethod.REGIOMONTANUS: PrimaryDirectionMethodRelationKind.REGIOMONTANIAN_UNDER_POLE_PERFECTION,
            PrimaryDirectionMethod.CAMPANUS: PrimaryDirectionMethodRelationKind.CAMPANIAN_UNDER_POLE_PERFECTION,
            PrimaryDirectionMethod.TOPOCENTRIC: PrimaryDirectionMethodRelationKind.TOPOCENTRIC_UNDER_POLE_PERFECTION,
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
            PrimaryDirectionMethod.PTOLEMY_SEMI_ARC: PrimaryDirectionMethodConditionState.PTOLEMAIC_SEMI_ARC_GROUNDED,
            PrimaryDirectionMethod.PLACIDIAN_CLASSIC_SEMI_ARC: PrimaryDirectionMethodConditionState.CLASSIC_SEMI_ARC_GROUNDED,
            PrimaryDirectionMethod.MERIDIAN: PrimaryDirectionMethodConditionState.EQUATORIAL_GROUNDED,
            PrimaryDirectionMethod.MORINUS: PrimaryDirectionMethodConditionState.MORINIAN_GROUNDED,
            PrimaryDirectionMethod.REGIOMONTANUS: PrimaryDirectionMethodConditionState.UNDER_POLE_GROUNDED,
            PrimaryDirectionMethod.CAMPANUS: PrimaryDirectionMethodConditionState.PRIME_VERTICAL_UNDER_POLE_GROUNDED,
            PrimaryDirectionMethod.TOPOCENTRIC: PrimaryDirectionMethodConditionState.TOPOCENTRIC_UNDER_POLE_GROUNDED,
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
        mundane_count=sum(1 for profile in profiles if profile.classification.mundane),
        semi_arc_count=sum(1 for profile in profiles if profile.truth.uses_semi_arcs),
        under_pole_count=sum(1 for profile in profiles if profile.truth.under_pole_based),
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
