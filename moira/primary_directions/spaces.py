"""
Moira -- primary_directions/spaces.py
Standalone direction-space doctrine owner for the primary-directions subsystem.

Boundary
--------
Owns the doctrinal identity, truth surface, and hardened interpretation of
currently admitted primary-direction spaces. This module is intentionally
orthogonal to geometry method and time-key conversion.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Iterable

__all__ = [
    "PrimaryDirectionSpace",
    "PrimaryDirectionSpaceKind",
    "PrimaryDirectionLatitudeMode",
    "PrimaryDirectionSpaceRelationKind",
    "PrimaryDirectionSpaceConditionState",
    "PrimaryDirectionSpacePolicy",
    "PrimaryDirectionSpaceTruth",
    "PrimaryDirectionSpaceClassification",
    "PrimaryDirectionSpaceRelation",
    "PrimaryDirectionSpaceRelationProfile",
    "PrimaryDirectionSpaceConditionProfile",
    "PrimaryDirectionSpacesAggregateProfile",
    "PrimaryDirectionSpacesNetworkNode",
    "PrimaryDirectionSpacesNetworkEdge",
    "PrimaryDirectionSpacesNetworkProfile",
    "primary_direction_space_truth",
    "classify_primary_direction_space",
    "relate_primary_direction_space",
    "evaluate_primary_direction_space_relations",
    "evaluate_primary_direction_space_condition",
    "evaluate_primary_direction_spaces_aggregate",
    "evaluate_primary_direction_spaces_network",
]


class PrimaryDirectionSpace(StrEnum):
    IN_MUNDO = "in_mundo"
    IN_ZODIACO = "in_zodiaco"


class PrimaryDirectionSpaceKind(StrEnum):
    WORLD_FRAME = "world_frame"
    ZODIACAL = "zodiacal"


class PrimaryDirectionLatitudeMode(StrEnum):
    PRESERVED = "preserved"
    SUPPRESSED = "suppressed"


class PrimaryDirectionSpaceRelationKind(StrEnum):
    WORLD_FRAME_PERFECTION = "world_frame_perfection"
    ZODIACAL_LONGITUDE_PERFECTION = "zodiacal_longitude_perfection"
    ZODIACAL_PROJECTED_PERFECTION = "zodiacal_projected_perfection"


class PrimaryDirectionSpaceConditionState(StrEnum):
    WORLD_FRAMED = "world_framed"
    ZODIACALLY_FRAMED = "zodiacally_framed"
    ZODIACALLY_PROJECTED = "zodiacally_projected"


@dataclass(frozen=True, slots=True)
class PrimaryDirectionSpacePolicy:
    space: PrimaryDirectionSpace = PrimaryDirectionSpace.IN_MUNDO
    latitude_mode: PrimaryDirectionLatitudeMode | None = None

    def __post_init__(self) -> None:
        if self.space not in (PrimaryDirectionSpace.IN_MUNDO, PrimaryDirectionSpace.IN_ZODIACO):
            raise ValueError(f"Unsupported primary direction space: {self.space}")
        if self.space is PrimaryDirectionSpace.IN_MUNDO:
            if self.latitude_mode not in (None, PrimaryDirectionLatitudeMode.PRESERVED):
                raise ValueError("in_mundo currently admits only preserved latitude mode")
        else:
            if self.latitude_mode not in (
                None,
                PrimaryDirectionLatitudeMode.SUPPRESSED,
                PrimaryDirectionLatitudeMode.PRESERVED,
            ):
                raise ValueError("in_zodiaco currently admits suppressed or preserved latitude mode")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionSpaceTruth:
    space: PrimaryDirectionSpace
    kind: PrimaryDirectionSpaceKind
    latitude_mode: PrimaryDirectionLatitudeMode
    relation_domain: str
    aspectual_points_native: bool

    def __post_init__(self) -> None:
        expected = {
            (PrimaryDirectionSpace.IN_MUNDO, PrimaryDirectionLatitudeMode.PRESERVED): (
                PrimaryDirectionSpaceKind.WORLD_FRAME,
                "world_frame",
                False,
            ),
            (PrimaryDirectionSpace.IN_ZODIACO, PrimaryDirectionLatitudeMode.SUPPRESSED): (
                PrimaryDirectionSpaceKind.ZODIACAL,
                "zodiacal_longitude",
                False,
            ),
            (PrimaryDirectionSpace.IN_ZODIACO, PrimaryDirectionLatitudeMode.PRESERVED): (
                PrimaryDirectionSpaceKind.ZODIACAL,
                "zodiacal_projected",
                False,
            ),
        }.get((self.space, self.latitude_mode))
        if expected is None:
            raise ValueError(
                f"Unsupported primary direction space on truth: {(self.space, self.latitude_mode)}"
            )
        if (
            self.kind,
            self.relation_domain,
            self.aspectual_points_native,
        ) != expected:
            raise ValueError("PrimaryDirectionSpaceTruth invariant failed: truth mismatch")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionSpaceClassification:
    truth: PrimaryDirectionSpaceTruth
    bodily: bool
    zodiacal: bool
    hybrid: bool

    def __post_init__(self) -> None:
        if self.truth.kind is PrimaryDirectionSpaceKind.WORLD_FRAME:
            if not self.bodily or self.zodiacal or self.hybrid:
                raise ValueError(
                    "PrimaryDirectionSpaceClassification invariant failed: in_mundo classification mismatch"
                )
        elif self.truth.kind is PrimaryDirectionSpaceKind.ZODIACAL:
            if self.bodily or not self.zodiacal or self.hybrid:
                raise ValueError(
                    "PrimaryDirectionSpaceClassification invariant failed: in_zodiaco classification mismatch"
                )
        else:
            raise ValueError("PrimaryDirectionSpaceClassification invariant failed: unknown truth kind")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionSpaceRelation:
    truth: PrimaryDirectionSpaceTruth
    relation_kind: PrimaryDirectionSpaceRelationKind
    latitude_mode: PrimaryDirectionLatitudeMode

    def __post_init__(self) -> None:
        expected_kind = (
            PrimaryDirectionSpaceRelationKind.WORLD_FRAME_PERFECTION
            if self.truth.space is PrimaryDirectionSpace.IN_MUNDO
            else (
                PrimaryDirectionSpaceRelationKind.ZODIACAL_LONGITUDE_PERFECTION
                if self.truth.latitude_mode is PrimaryDirectionLatitudeMode.SUPPRESSED
                else PrimaryDirectionSpaceRelationKind.ZODIACAL_PROJECTED_PERFECTION
            )
        )
        if self.relation_kind is not expected_kind:
            raise ValueError(f"Unsupported primary direction space relation kind: {self.relation_kind}")
        if self.latitude_mode is not self.truth.latitude_mode:
            raise ValueError(
                "PrimaryDirectionSpaceRelation invariant failed: latitude_mode does not match truth"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionSpaceRelationProfile:
    truth: PrimaryDirectionSpaceTruth
    detected_relation: PrimaryDirectionSpaceRelation
    admitted_relations: tuple[PrimaryDirectionSpaceRelation, ...]
    scored_relations: tuple[PrimaryDirectionSpaceRelation, ...]

    def __post_init__(self) -> None:
        if self.detected_relation.truth != self.truth:
            raise ValueError(
                "PrimaryDirectionSpaceRelationProfile invariant failed: detected relation must belong to truth"
            )
        if self.detected_relation not in self.admitted_relations:
            raise ValueError(
                "PrimaryDirectionSpaceRelationProfile invariant failed: detected relation must be admitted"
            )
        for relation in self.scored_relations:
            if relation not in self.admitted_relations:
                raise ValueError(
                    "PrimaryDirectionSpaceRelationProfile invariant failed: scored relations must be admitted"
                )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionSpaceConditionProfile:
    truth: PrimaryDirectionSpaceTruth
    classification: PrimaryDirectionSpaceClassification
    relation_profile: PrimaryDirectionSpaceRelationProfile
    state: PrimaryDirectionSpaceConditionState

    def __post_init__(self) -> None:
        if self.classification.truth != self.truth:
            raise ValueError(
                "PrimaryDirectionSpaceConditionProfile invariant failed: classification truth mismatch"
            )
        if self.relation_profile.truth != self.truth:
            raise ValueError(
                "PrimaryDirectionSpaceConditionProfile invariant failed: relation truth mismatch"
            )
        expected_state = (
            PrimaryDirectionSpaceConditionState.WORLD_FRAMED
            if self.truth.space is PrimaryDirectionSpace.IN_MUNDO
            else (
                PrimaryDirectionSpaceConditionState.ZODIACALLY_FRAMED
                if self.truth.latitude_mode is PrimaryDirectionLatitudeMode.SUPPRESSED
                else PrimaryDirectionSpaceConditionState.ZODIACALLY_PROJECTED
            )
        )
        if self.state is not expected_state:
            raise ValueError("PrimaryDirectionSpaceConditionProfile invariant failed: state mismatch")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionSpacesAggregateProfile:
    profiles: tuple[PrimaryDirectionSpaceConditionProfile, ...]
    total_profiles: int
    world_frame_count: int
    preserves_latitude_count: int

    def __post_init__(self) -> None:
        if not self.profiles:
            raise ValueError("PrimaryDirectionSpacesAggregateProfile requires at least one profile")
        if self.total_profiles != len(self.profiles):
            raise ValueError(
                "PrimaryDirectionSpacesAggregateProfile invariant failed: total_profiles mismatch"
            )
        if self.world_frame_count != sum(
            1 for profile in self.profiles if profile.truth.kind is PrimaryDirectionSpaceKind.WORLD_FRAME
        ):
            raise ValueError(
                "PrimaryDirectionSpacesAggregateProfile invariant failed: world_frame_count mismatch"
            )
        if self.preserves_latitude_count != sum(
            1
            for profile in self.profiles
            if profile.truth.latitude_mode is PrimaryDirectionLatitudeMode.PRESERVED
        ):
            raise ValueError(
                "PrimaryDirectionSpacesAggregateProfile invariant failed: preserves_latitude_count mismatch"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionSpacesNetworkNode:
    space: PrimaryDirectionSpace
    count: int

    def __post_init__(self) -> None:
        if self.count <= 0:
            raise ValueError("PrimaryDirectionSpacesNetworkNode invariant failed: count must be positive")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionSpacesNetworkEdge:
    from_space: PrimaryDirectionSpace
    to_space: PrimaryDirectionSpace
    count: int

    def __post_init__(self) -> None:
        if self.from_space == self.to_space:
            raise ValueError(
                "PrimaryDirectionSpacesNetworkEdge invariant failed: self-edges are not admitted"
            )
        if self.count <= 0:
            raise ValueError("PrimaryDirectionSpacesNetworkEdge invariant failed: count must be positive")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionSpacesNetworkProfile:
    nodes: tuple[PrimaryDirectionSpacesNetworkNode, ...]
    edges: tuple[PrimaryDirectionSpacesNetworkEdge, ...]
    dominant_space: PrimaryDirectionSpace
    isolated_spaces: tuple[PrimaryDirectionSpace, ...]

    def __post_init__(self) -> None:
        if not self.nodes:
            raise ValueError("PrimaryDirectionSpacesNetworkProfile requires at least one node")
        spaces = [node.space for node in self.nodes]
        if len(set(spaces)) != len(spaces):
            raise ValueError(
                "PrimaryDirectionSpacesNetworkProfile invariant failed: duplicate nodes"
            )
        node_set = set(spaces)
        for edge in self.edges:
            if edge.from_space not in node_set or edge.to_space not in node_set:
                raise ValueError(
                    "PrimaryDirectionSpacesNetworkProfile invariant failed: dangling edge"
                )
        dominant = max(self.nodes, key=lambda node: (node.count, node.space.value)).space
        if self.dominant_space is not dominant:
            raise ValueError(
                "PrimaryDirectionSpacesNetworkProfile invariant failed: dominant_space mismatch"
            )
        if set(self.isolated_spaces) - node_set:
            raise ValueError(
                "PrimaryDirectionSpacesNetworkProfile invariant failed: isolated_spaces contains unknown node"
            )


def primary_direction_space_truth(
    space: PrimaryDirectionSpace = PrimaryDirectionSpace.IN_MUNDO,
    *,
    policy: PrimaryDirectionSpacePolicy | None = None,
) -> PrimaryDirectionSpaceTruth:
    resolved_policy = policy if policy is not None else PrimaryDirectionSpacePolicy(space)
    if resolved_policy.space not in (PrimaryDirectionSpace.IN_MUNDO, PrimaryDirectionSpace.IN_ZODIACO):
        raise ValueError(f"Unsupported primary direction space: {resolved_policy.space}")
    latitude_mode = (
        resolved_policy.latitude_mode
        if resolved_policy.latitude_mode is not None
        else (
            PrimaryDirectionLatitudeMode.PRESERVED
            if resolved_policy.space is PrimaryDirectionSpace.IN_MUNDO
            else PrimaryDirectionLatitudeMode.SUPPRESSED
        )
    )
    return PrimaryDirectionSpaceTruth(
        space=resolved_policy.space,
        kind=(
            PrimaryDirectionSpaceKind.WORLD_FRAME
            if resolved_policy.space is PrimaryDirectionSpace.IN_MUNDO
            else PrimaryDirectionSpaceKind.ZODIACAL
        ),
        latitude_mode=latitude_mode,
        relation_domain=(
            "world_frame"
            if resolved_policy.space is PrimaryDirectionSpace.IN_MUNDO
            else (
                "zodiacal_longitude"
                if latitude_mode is PrimaryDirectionLatitudeMode.SUPPRESSED
                else "zodiacal_projected"
            )
        ),
        aspectual_points_native=False,
    )


def classify_primary_direction_space(
    truth: PrimaryDirectionSpaceTruth,
) -> PrimaryDirectionSpaceClassification:
    return PrimaryDirectionSpaceClassification(
        truth=truth,
        bodily=truth.space is PrimaryDirectionSpace.IN_MUNDO,
        zodiacal=truth.space is PrimaryDirectionSpace.IN_ZODIACO,
        hybrid=False,
    )


def relate_primary_direction_space(
    truth: PrimaryDirectionSpaceTruth,
) -> PrimaryDirectionSpaceRelation:
    return PrimaryDirectionSpaceRelation(
        truth=truth,
        relation_kind=(
            PrimaryDirectionSpaceRelationKind.WORLD_FRAME_PERFECTION
            if truth.space is PrimaryDirectionSpace.IN_MUNDO
            else (
                PrimaryDirectionSpaceRelationKind.ZODIACAL_LONGITUDE_PERFECTION
                if truth.latitude_mode is PrimaryDirectionLatitudeMode.SUPPRESSED
                else PrimaryDirectionSpaceRelationKind.ZODIACAL_PROJECTED_PERFECTION
            )
        ),
        latitude_mode=truth.latitude_mode,
    )


def evaluate_primary_direction_space_relations(
    truth: PrimaryDirectionSpaceTruth,
) -> PrimaryDirectionSpaceRelationProfile:
    relation = relate_primary_direction_space(truth)
    admitted = (relation,)
    return PrimaryDirectionSpaceRelationProfile(
        truth=truth,
        detected_relation=relation,
        admitted_relations=admitted,
        scored_relations=admitted,
    )


def evaluate_primary_direction_space_condition(
    truth: PrimaryDirectionSpaceTruth,
) -> PrimaryDirectionSpaceConditionProfile:
    return PrimaryDirectionSpaceConditionProfile(
        truth=truth,
        classification=classify_primary_direction_space(truth),
        relation_profile=evaluate_primary_direction_space_relations(truth),
        state=(
            PrimaryDirectionSpaceConditionState.WORLD_FRAMED
            if truth.space is PrimaryDirectionSpace.IN_MUNDO
            else (
                PrimaryDirectionSpaceConditionState.ZODIACALLY_FRAMED
                if truth.latitude_mode is PrimaryDirectionLatitudeMode.SUPPRESSED
                else PrimaryDirectionSpaceConditionState.ZODIACALLY_PROJECTED
            )
        ),
    )


def evaluate_primary_direction_spaces_aggregate(
    truths: Iterable[PrimaryDirectionSpaceTruth],
) -> PrimaryDirectionSpacesAggregateProfile:
    profiles = tuple(evaluate_primary_direction_space_condition(truth) for truth in truths)
    if not profiles:
        raise ValueError("evaluate_primary_direction_spaces_aggregate requires at least one truth")
    return PrimaryDirectionSpacesAggregateProfile(
        profiles=profiles,
        total_profiles=len(profiles),
        world_frame_count=sum(
            1 for profile in profiles if profile.truth.kind is PrimaryDirectionSpaceKind.WORLD_FRAME
        ),
        preserves_latitude_count=sum(
            1
            for profile in profiles
            if profile.truth.latitude_mode is PrimaryDirectionLatitudeMode.PRESERVED
        ),
    )


def evaluate_primary_direction_spaces_network(
    truths: Iterable[PrimaryDirectionSpaceTruth],
) -> PrimaryDirectionSpacesNetworkProfile:
    truth_tuple = tuple(truths)
    if not truth_tuple:
        raise ValueError("evaluate_primary_direction_spaces_network requires at least one truth")

    counts: dict[PrimaryDirectionSpace, int] = {}
    for truth in truth_tuple:
        counts[truth.space] = counts.get(truth.space, 0) + 1

    nodes = tuple(
        sorted(
            (PrimaryDirectionSpacesNetworkNode(space=space, count=count) for space, count in counts.items()),
            key=lambda node: node.space.value,
        )
    )

    edge_counts: dict[tuple[PrimaryDirectionSpace, PrimaryDirectionSpace], int] = {}
    for left, right in zip(truth_tuple, truth_tuple[1:]):
        if left.space == right.space:
            continue
        key = (left.space, right.space)
        edge_counts[key] = edge_counts.get(key, 0) + 1

    edges = tuple(
        sorted(
            (
                PrimaryDirectionSpacesNetworkEdge(from_space=from_space, to_space=to_space, count=count)
                for (from_space, to_space), count in edge_counts.items()
            ),
            key=lambda edge: (edge.from_space.value, edge.to_space.value),
        )
    )

    dominant_space = max(nodes, key=lambda node: (node.count, node.space.value)).space
    participating = {edge.from_space for edge in edges} | {edge.to_space for edge in edges}
    isolated = tuple(sorted((node.space for node in nodes if node.space not in participating), key=lambda s: s.value))
    return PrimaryDirectionSpacesNetworkProfile(
        nodes=nodes,
        edges=edges,
        dominant_space=dominant_space,
        isolated_spaces=isolated,
    )
