"""
Moira -- primary_directions/targets.py
Standalone target-doctrine owner for the primary-directions subsystem.

Boundary
--------
Owns the doctrinal identity, classification, and admission policy for the kinds
of entities currently admitted as primary-direction promissors and significators.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from .._strenum import StrEnum
import math
from numbers import Real
from typing import Iterable

from ._ordered_network import validate_ordered_transition_counts

from ..constants import Body, SIGNS
from ..egyptian_bounds import (
    EgyptianBoundsDoctrine,
    EGYPTIAN_BOUNDS,
    PTOLEMAIC_BOUNDS,
    CHALDEAN_DAY_BOUNDS,
    CHALDEAN_NIGHT_BOUNDS,
)

__all__ = [
    "PrimaryDirectionTargetClass",
    "PrimaryDirectionBoundTarget",
    "PrimaryDirectionMundaneAspectTarget",
    "PLACIDIAN_MUNDANE_ASPECT_OFFSETS",
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
    "resolve_primary_direction_bound_targets",
    "resolve_primary_direction_mundane_aspect_targets",
    "PrimaryDirectionMundaneParallelKind",
    "PrimaryDirectionMundaneParallelTarget",
    "PrimaryDirectionMidpointTarget",
    "resolve_primary_direction_mundane_parallel_targets",
    "resolve_primary_direction_midpoint_targets",
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
_PLANET_NAMES = frozenset(name for name in Body.ALL_PLANETS if name not in _NODE_NAMES)


class PrimaryDirectionTargetClass(StrEnum):
    """Vessel: Registry of architectural classes for primary direction targets."""
    PLANET = "planet"
    NODE = "node"
    ANGLE = "angle"
    HOUSE_CUSP = "house_cusp"
    ASPECTUAL_POINT = "aspectual_point"
    BOUND_BOUNDARY = "bound_boundary"
    MUNDANE_ASPECT = "mundane_aspect"
    MUNDANE_PARALLEL = "mundane_parallel"
    MIDPOINT = "midpoint"


PLACIDIAN_MUNDANE_ASPECT_OFFSETS: tuple[tuple[str, float], ...] = (
    ("Opposition", 2.0),
    ("Dexter Semi-Sextile", 1.0 / 3.0),
    ("Sinister Semi-Sextile", -1.0 / 3.0),
    ("Dexter Sextile", 2.0 / 3.0),
    ("Sinister Sextile", -2.0 / 3.0),
    ("Dexter Square", 1.0),
    ("Sinister Square", -1.0),
    ("Dexter Trine", 4.0 / 3.0),
    ("Sinister Trine", -4.0 / 3.0),
    ("Dexter Quincunx", 5.0 / 3.0),
    ("Sinister Quincunx", -5.0 / 3.0),
)


@dataclass(frozen=True, slots=True)
class PrimaryDirectionMundaneAspectTarget:
    """Immutable astronomical representation of a Placidian mundane aspect target."""
    source_name: str
    aspect_name: str
    fraction_offset: float

    def __post_init__(self) -> None:
        if not isinstance(self.source_name, str) or not self.source_name.strip():
            raise ValueError("PrimaryDirectionMundaneAspectTarget requires a non-empty source_name")
        if not isinstance(self.aspect_name, str) or not self.aspect_name.strip():
            raise ValueError("PrimaryDirectionMundaneAspectTarget requires a non-empty aspect_name")
        if (
            isinstance(self.fraction_offset, bool)
            or not isinstance(self.fraction_offset, Real)
            or not math.isfinite(float(self.fraction_offset))
        ):
            raise ValueError("PrimaryDirectionMundaneAspectTarget requires a finite fraction_offset")

    @property
    def name(self) -> str:
        return f"{self.source_name} Mundane {self.aspect_name}"


class PrimaryDirectionMundaneParallelKind(StrEnum):
    """Vessel: Registry of Placidian mundane parallel relation varieties."""
    PARALLEL = "parallel"
    CONTRA_PARALLEL = "contra_parallel"


@dataclass(frozen=True, slots=True)
class PrimaryDirectionMundaneParallelTarget:
    """Immutable astronomical representation of a Placidian mundane parallel target."""
    source_name: str
    relation: PrimaryDirectionMundaneParallelKind = PrimaryDirectionMundaneParallelKind.PARALLEL

    def __init__(
        self,
        source_name: str,
        relation: PrimaryDirectionMundaneParallelKind | None = None,
        *,
        kind: PrimaryDirectionMundaneParallelKind | None = None,
    ) -> None:
        rel = (
            kind
            if kind is not None
            else (
                relation
                if relation is not None
                else PrimaryDirectionMundaneParallelKind.PARALLEL
            )
        )
        object.__setattr__(self, "source_name", source_name)
        object.__setattr__(self, "relation", rel)
        self.__post_init__()

    def __post_init__(self) -> None:
        if not isinstance(self.source_name, str) or not self.source_name.strip():
            raise ValueError("PrimaryDirectionMundaneParallelTarget requires a non-empty source_name")
        if not isinstance(self.relation, PrimaryDirectionMundaneParallelKind):
            raise ValueError(
                f"PrimaryDirectionMundaneParallelTarget requires a valid PrimaryDirectionMundaneParallelKind, got {self.relation!r}"
            )

    @property
    def kind(self) -> PrimaryDirectionMundaneParallelKind:
        return self.relation

    @property
    def name(self) -> str:
        suffix = "Parallel" if self.relation is PrimaryDirectionMundaneParallelKind.PARALLEL else "Contra-Parallel"
        return f"{self.source_name} Mundane {suffix}"


@dataclass(frozen=True, slots=True)
class PrimaryDirectionMidpointTarget:
    """Immutable astronomical representation of a zodiacal shortest-arc midpoint target."""
    source_a: str
    source_b: str

    def __init__(
        self,
        source_a: str | None = None,
        source_b: str | None = None,
        *,
        source_a_name: str | None = None,
        source_b_name: str | None = None,
    ) -> None:
        a = source_a_name if source_a_name is not None else source_a
        b = source_b_name if source_b_name is not None else source_b
        if a is None or b is None:
            raise ValueError("PrimaryDirectionMidpointTarget requires two source names")
        object.__setattr__(self, "source_a", a)
        object.__setattr__(self, "source_b", b)
        self.__post_init__()

    def __post_init__(self) -> None:
        if not isinstance(self.source_a, str) or not self.source_a.strip():
            raise ValueError("PrimaryDirectionMidpointTarget requires a non-empty source_a")
        if not isinstance(self.source_b, str) or not self.source_b.strip():
            raise ValueError("PrimaryDirectionMidpointTarget requires a non-empty source_b")
        if self.source_a.strip() == self.source_b.strip():
            raise ValueError("PrimaryDirectionMidpointTarget sources must be distinct")

    @property
    def source_a_name(self) -> str:
        return self.source_a.strip()

    @property
    def source_b_name(self) -> str:
        return self.source_b.strip()

    @property
    def name(self) -> str:
        return f"{self.source_a.strip()}/{self.source_b.strip()} Midpoint"


@dataclass(frozen=True, slots=True)
class PrimaryDirectionBoundTarget:
    """Immutable astronomical representation of a zodiacal term/bound boundary."""
    name: str
    sign: str
    degree_in_sign: float
    absolute_longitude: float
    ruler: str
    doctrine: EgyptianBoundsDoctrine

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("PrimaryDirectionBoundTarget requires a non-empty name")
        if self.sign not in SIGNS:
            raise ValueError(f"Unknown zodiac sign: {self.sign}")
        if not (0.0 <= self.degree_in_sign <= 30.0):
            raise ValueError(f"degree_in_sign must be in [0, 30], got {self.degree_in_sign}")
        if not (0.0 <= self.absolute_longitude <= 360.0):
            raise ValueError(f"absolute_longitude must be in [0, 360], got {self.absolute_longitude}")
        if not isinstance(self.ruler, str) or not self.ruler.strip():
            raise ValueError("PrimaryDirectionBoundTarget requires a non-empty ruler")
        if not isinstance(self.doctrine, EgyptianBoundsDoctrine):
            raise ValueError("PrimaryDirectionBoundTarget requires a valid EgyptianBoundsDoctrine")


class PrimaryDirectionTargetRelationKind(StrEnum):
    """Vessel: Registry of admission relation types for targets."""
    ADMITTED_AS_BOTH = "admitted_as_both"
    ADMITTED_AS_SIGNIFICATOR_ONLY = "admitted_as_significator_only"
    ADMITTED_AS_PROMISSOR_ONLY = "admitted_as_promissor_only"
    REJECTED = "rejected"


class PrimaryDirectionTargetConditionState(StrEnum):
    """Vessel: Registry of condition states for primary direction targets."""
    UNIVERSALLY_ADMITTED = "universally_admitted"
    SIGNIFICATOR_ONLY = "significator_only"
    PROMISSOR_ONLY = "promissor_only"
    NOT_ADMITTED = "not_admitted"


@dataclass(frozen=True, slots=True)
class PrimaryDirectionTargetPolicy:
    """Vessel: Policy definition for target admission in primary directions."""
    admitted_significator_classes: frozenset[PrimaryDirectionTargetClass] = field(
        default_factory=lambda: frozenset(
            {
                PrimaryDirectionTargetClass.PLANET,
                PrimaryDirectionTargetClass.NODE,
                PrimaryDirectionTargetClass.ANGLE,
                PrimaryDirectionTargetClass.HOUSE_CUSP,
            }
        )
    )
    admitted_promissor_classes: frozenset[PrimaryDirectionTargetClass] = field(
        default_factory=lambda: frozenset(
            {
                PrimaryDirectionTargetClass.PLANET,
                PrimaryDirectionTargetClass.NODE,
                PrimaryDirectionTargetClass.ANGLE,
                PrimaryDirectionTargetClass.HOUSE_CUSP,
                PrimaryDirectionTargetClass.BOUND_BOUNDARY,
            }
        )
    )

    def __post_init__(self) -> None:
        try:
            significator_classes = frozenset(self.admitted_significator_classes)
            promissor_classes = frozenset(self.admitted_promissor_classes)
        except TypeError as exc:
            raise ValueError(
                "PrimaryDirectionTargetPolicy invariant failed: admitted classes must be iterable"
            ) from exc
        object.__setattr__(self, "admitted_significator_classes", significator_classes)
        object.__setattr__(self, "admitted_promissor_classes", promissor_classes)
        if not self.admitted_significator_classes or not self.admitted_promissor_classes:
            raise ValueError(
                "PrimaryDirectionTargetPolicy invariant failed: admitted target classes may not be empty"
            )
        if not all(
            isinstance(target_class, PrimaryDirectionTargetClass)
            for target_class in self.admitted_significator_classes
        ):
            raise ValueError("Unsupported significator target classes")
        if not all(
            isinstance(target_class, PrimaryDirectionTargetClass)
            for target_class in self.admitted_promissor_classes
        ):
            raise ValueError("Unsupported promissor target classes")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionTargetTruth:
    """Vessel: Immutable astronomical truth for a primary direction target."""
    name: str
    target_class: PrimaryDirectionTargetClass
    source_name: str | None = None
    aspect_name: str | None = None
    aspect_angle: float | None = None
    fraction_offset: float | None = None
    source_b_name: str | None = None
    parallel_kind: PrimaryDirectionMundaneParallelKind | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("PrimaryDirectionTargetTruth requires a non-empty target name")
        if not isinstance(self.target_class, PrimaryDirectionTargetClass):
            raise ValueError(f"Unsupported primary-direction target class: {self.target_class}")
        if self.target_class is PrimaryDirectionTargetClass.ASPECTUAL_POINT:
            if (
                not isinstance(self.source_name, str)
                or not self.source_name.strip()
                or not isinstance(self.aspect_name, str)
                or not self.aspect_name.strip()
                or isinstance(self.aspect_angle, bool)
                or not isinstance(self.aspect_angle, Real)
                or not math.isfinite(float(self.aspect_angle))
            ):
                raise ValueError(
                    "PrimaryDirectionTargetTruth invariant failed: aspectual points require source_name, aspect_name, and aspect_angle"
                )
            _target_class_for_name(self.source_name)
            expected_angles = {
                aspect_name: angle for aspect_name, angle in _MAJOR_ASPECT_ANGLES
            }
            expected_angle = expected_angles.get(self.aspect_name)
            if expected_angle is None or float(self.aspect_angle) != expected_angle:
                raise ValueError(
                    "PrimaryDirectionTargetTruth invariant failed: aspect metadata is not an admitted major aspect"
                )
            if self.name != f"{self.source_name} {self.aspect_name}":
                raise ValueError(
                    "PrimaryDirectionTargetTruth invariant failed: aspect target name does not match its metadata"
                )
        elif self.target_class is PrimaryDirectionTargetClass.MUNDANE_ASPECT:
            if (
                not isinstance(self.source_name, str)
                or not self.source_name.strip()
                or not isinstance(self.aspect_name, str)
                or not self.aspect_name.strip()
                or isinstance(self.fraction_offset, bool)
                or not isinstance(self.fraction_offset, Real)
                or not math.isfinite(float(self.fraction_offset))
            ):
                raise ValueError(
                    "PrimaryDirectionTargetTruth invariant failed: mundane aspects require source_name, aspect_name, and fraction_offset"
                )
            _target_class_for_name(self.source_name)
            expected_offsets = {
                aspect_name: offset for aspect_name, offset in PLACIDIAN_MUNDANE_ASPECT_OFFSETS
            }
            expected_offset = expected_offsets.get(self.aspect_name)
            if expected_offset is None or not math.isclose(float(self.fraction_offset), expected_offset, abs_tol=1e-9):
                raise ValueError(
                    "PrimaryDirectionTargetTruth invariant failed: aspect metadata is not an admitted mundane aspect"
                )
            if self.name != f"{self.source_name} Mundane {self.aspect_name}":
                raise ValueError(
                    "PrimaryDirectionTargetTruth invariant failed: mundane aspect target name does not match its metadata"
                )
        elif self.target_class is PrimaryDirectionTargetClass.MUNDANE_PARALLEL:
            if (
                not isinstance(self.source_name, str)
                or not self.source_name.strip()
                or not isinstance(self.parallel_kind, PrimaryDirectionMundaneParallelKind)
            ):
                raise ValueError(
                    "PrimaryDirectionTargetTruth invariant failed: mundane parallels require source_name and parallel_kind"
                )
            _target_class_for_name(self.source_name)
            suffix = "Parallel" if self.parallel_kind is PrimaryDirectionMundaneParallelKind.PARALLEL else "Contra-Parallel"
            if self.name != f"{self.source_name} Mundane {suffix}":
                raise ValueError(
                    "PrimaryDirectionTargetTruth invariant failed: mundane parallel target name does not match its metadata"
                )
        elif self.target_class is PrimaryDirectionTargetClass.MIDPOINT:
            if (
                not isinstance(self.source_name, str)
                or not self.source_name.strip()
                or not isinstance(self.source_b_name, str)
                or not self.source_b_name.strip()
            ):
                raise ValueError(
                    "PrimaryDirectionTargetTruth invariant failed: midpoints require source_name and source_b_name"
                )
            if self.source_name.strip() == self.source_b_name.strip():
                raise ValueError("PrimaryDirectionTargetTruth invariant failed: midpoint sources must be distinct")
            _target_class_for_name(self.source_name)
            _target_class_for_name(self.source_b_name)
            if self.name != f"{self.source_name.strip()}/{self.source_b_name.strip()} Midpoint":
                raise ValueError(
                    "PrimaryDirectionTargetTruth invariant failed: midpoint target name does not match its metadata"
                )
        elif any(
            value is not None
            for value in (
                self.source_name,
                self.aspect_name,
                self.aspect_angle,
                self.fraction_offset,
                self.source_b_name,
                self.parallel_kind,
            )
        ):
            raise ValueError(
                "PrimaryDirectionTargetTruth invariant failed: non-derived targets may not carry derived metadata"
            )
        elif _target_class_for_name(self.name) is not self.target_class:
            raise ValueError(
                "PrimaryDirectionTargetTruth invariant failed: target class does not match declared identity"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionTargetClassification:
    """Vessel: Result of classifying a target based on policy."""
    truth: PrimaryDirectionTargetTruth
    admitted_as_significator: bool
    admitted_as_promissor: bool

    def __post_init__(self) -> None:
        if not isinstance(self.truth, PrimaryDirectionTargetTruth):
            raise ValueError(
                "PrimaryDirectionTargetClassification invariant failed: invalid truth"
            )
        if type(self.admitted_as_significator) is not bool or type(self.admitted_as_promissor) is not bool:
            raise ValueError(
                "PrimaryDirectionTargetClassification invariant failed: admission flags must be bool"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionTargetRelation:
    """Vessel: Established relation between a target and the system."""
    truth: PrimaryDirectionTargetTruth
    relation_kind: PrimaryDirectionTargetRelationKind

    def __post_init__(self) -> None:
        if not isinstance(self.truth, PrimaryDirectionTargetTruth):
            raise ValueError("PrimaryDirectionTargetRelation invariant failed: invalid truth")
        if not isinstance(self.relation_kind, PrimaryDirectionTargetRelationKind):
            raise ValueError(
                "PrimaryDirectionTargetRelation invariant failed: relation_kind must be an enum member"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionTargetRelationProfile:
    """Vessel: Comprehensive profile of relations for a target."""
    truth: PrimaryDirectionTargetTruth
    detected_relation: PrimaryDirectionTargetRelation
    admitted_relations: tuple[PrimaryDirectionTargetRelation, ...]
    scored_relations: tuple[PrimaryDirectionTargetRelation, ...]

    def __post_init__(self) -> None:
        try:
            admitted_relations = tuple(self.admitted_relations)
            scored_relations = tuple(self.scored_relations)
        except TypeError as exc:
            raise ValueError(
                "PrimaryDirectionTargetRelationProfile invariant failed: relation collections must be iterable"
            ) from exc
        object.__setattr__(self, "admitted_relations", admitted_relations)
        object.__setattr__(self, "scored_relations", scored_relations)
        if not isinstance(self.truth, PrimaryDirectionTargetTruth):
            raise ValueError("PrimaryDirectionTargetRelationProfile invariant failed: invalid truth")
        if not isinstance(self.detected_relation, PrimaryDirectionTargetRelation):
            raise ValueError(
                "PrimaryDirectionTargetRelationProfile invariant failed: invalid detected relation"
            )
        if self.detected_relation.truth != self.truth:
            raise ValueError(
                "PrimaryDirectionTargetRelationProfile invariant failed: detected relation truth mismatch"
            )
        for label, relations in (
            ("admitted", self.admitted_relations),
            ("scored", self.scored_relations),
        ):
            if any(
                not isinstance(relation, PrimaryDirectionTargetRelation)
                or relation.truth != self.truth
                for relation in relations
            ):
                raise ValueError(
                    f"PrimaryDirectionTargetRelationProfile invariant failed: {label} relation truth mismatch"
                )
            if len(set(relations)) != len(relations):
                raise ValueError(
                    f"PrimaryDirectionTargetRelationProfile invariant failed: duplicate {label} relations"
                )
        if any(relation not in self.admitted_relations for relation in self.scored_relations):
                raise ValueError(
                    "PrimaryDirectionTargetRelationProfile invariant failed: scored relation must be admitted"
                )
        expected_relations = (
            ()
            if self.detected_relation.relation_kind is PrimaryDirectionTargetRelationKind.REJECTED
            else (self.detected_relation,)
        )
        if self.admitted_relations != expected_relations or self.scored_relations != expected_relations:
            raise ValueError(
                "PrimaryDirectionTargetRelationProfile invariant failed: relation admission does not match detected relation"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionTargetConditionProfile:
    """Vessel: Final condition profile for a primary direction target."""
    truth: PrimaryDirectionTargetTruth
    classification: PrimaryDirectionTargetClassification
    relation_profile: PrimaryDirectionTargetRelationProfile
    state: PrimaryDirectionTargetConditionState

    def __post_init__(self) -> None:
        if not isinstance(self.truth, PrimaryDirectionTargetTruth):
            raise ValueError("PrimaryDirectionTargetConditionProfile invariant failed: invalid truth")
        if not isinstance(self.classification, PrimaryDirectionTargetClassification):
            raise ValueError(
                "PrimaryDirectionTargetConditionProfile invariant failed: invalid classification"
            )
        if not isinstance(self.relation_profile, PrimaryDirectionTargetRelationProfile):
            raise ValueError(
                "PrimaryDirectionTargetConditionProfile invariant failed: invalid relation profile"
            )
        if not isinstance(self.state, PrimaryDirectionTargetConditionState):
            raise ValueError(
                "PrimaryDirectionTargetConditionProfile invariant failed: state must be an enum member"
            )
        if self.classification.truth != self.truth:
            raise ValueError(
                "PrimaryDirectionTargetConditionProfile invariant failed: classification truth mismatch"
            )
        if self.relation_profile.truth != self.truth:
            raise ValueError(
                "PrimaryDirectionTargetConditionProfile invariant failed: relation truth mismatch"
            )
        expected_relation_kind = _relation_kind(
            self.classification.admitted_as_significator,
            self.classification.admitted_as_promissor,
        )
        if self.relation_profile.detected_relation.relation_kind is not expected_relation_kind:
            raise ValueError(
                "PrimaryDirectionTargetConditionProfile invariant failed: relation does not match classification"
            )
        if self.state is not _condition_state(expected_relation_kind):
            raise ValueError(
                "PrimaryDirectionTargetConditionProfile invariant failed: state does not match admission"
            )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionTargetsAggregateProfile:
    """Vessel: Aggregated profile of multiple target conditions."""
    profiles: tuple[PrimaryDirectionTargetConditionProfile, ...]
    total_profiles: int
    planet_count: int
    node_count: int
    angle_count: int
    house_cusp_count: int
    aspect_count: int
    universally_admitted_count: int
    bound_boundary_count: int = 0
    mundane_aspect_count: int = 0
    mundane_parallel_count: int = 0
    midpoint_count: int = 0

    def __post_init__(self) -> None:
        try:
            profiles = tuple(self.profiles)
        except TypeError as exc:
            raise ValueError(
                "PrimaryDirectionTargetsAggregateProfile invariant failed: profiles must be iterable"
            ) from exc
        object.__setattr__(self, "profiles", profiles)
        if not self.profiles:
            raise ValueError("PrimaryDirectionTargetsAggregateProfile requires at least one profile")
        if any(not isinstance(profile, PrimaryDirectionTargetConditionProfile) for profile in self.profiles):
            raise ValueError("PrimaryDirectionTargetsAggregateProfile invariant failed: invalid profile type")
        counts = (
            self.total_profiles,
            self.planet_count,
            self.node_count,
            self.angle_count,
            self.house_cusp_count,
            self.aspect_count,
            self.bound_boundary_count,
            self.mundane_aspect_count,
            self.mundane_parallel_count,
            self.midpoint_count,
            self.universally_admitted_count,
        )
        if any(type(count) is not int or count < 0 for count in counts):
            raise ValueError(
                "PrimaryDirectionTargetsAggregateProfile invariant failed: counts must be non-negative integers"
            )
        if self.total_profiles != len(self.profiles):
            raise ValueError(
                "PrimaryDirectionTargetsAggregateProfile invariant failed: total_profiles mismatch"
            )
        if self.planet_count != sum(
            1 for profile in self.profiles if profile.truth.target_class is PrimaryDirectionTargetClass.PLANET
        ):
            raise ValueError(
                "PrimaryDirectionTargetsAggregateProfile invariant failed: planet_count mismatch"
            )
        if self.node_count != sum(
            1 for profile in self.profiles if profile.truth.target_class is PrimaryDirectionTargetClass.NODE
        ):
            raise ValueError(
                "PrimaryDirectionTargetsAggregateProfile invariant failed: node_count mismatch"
            )
        if self.angle_count != sum(
            1 for profile in self.profiles if profile.truth.target_class is PrimaryDirectionTargetClass.ANGLE
        ):
            raise ValueError(
                "PrimaryDirectionTargetsAggregateProfile invariant failed: angle_count mismatch"
            )
        if self.house_cusp_count != sum(
            1
            for profile in self.profiles
            if profile.truth.target_class is PrimaryDirectionTargetClass.HOUSE_CUSP
        ):
            raise ValueError(
                "PrimaryDirectionTargetsAggregateProfile invariant failed: house_cusp_count mismatch"
            )
        if self.aspect_count != sum(
            1
            for profile in self.profiles
            if profile.truth.target_class is PrimaryDirectionTargetClass.ASPECTUAL_POINT
        ):
            raise ValueError(
                "PrimaryDirectionTargetsAggregateProfile invariant failed: aspect_count mismatch"
            )
        if self.bound_boundary_count != sum(
            1
            for profile in self.profiles
            if profile.truth.target_class is PrimaryDirectionTargetClass.BOUND_BOUNDARY
        ):
            raise ValueError(
                "PrimaryDirectionTargetsAggregateProfile invariant failed: bound_boundary_count mismatch"
            )
        if self.mundane_aspect_count != sum(
            1
            for profile in self.profiles
            if profile.truth.target_class is PrimaryDirectionTargetClass.MUNDANE_ASPECT
        ):
            raise ValueError(
                "PrimaryDirectionTargetsAggregateProfile invariant failed: mundane_aspect_count mismatch"
            )
        if self.mundane_parallel_count != sum(
            1
            for profile in self.profiles
            if profile.truth.target_class is PrimaryDirectionTargetClass.MUNDANE_PARALLEL
        ):
            raise ValueError(
                "PrimaryDirectionTargetsAggregateProfile invariant failed: mundane_parallel_count mismatch"
            )
        if self.midpoint_count != sum(
            1
            for profile in self.profiles
            if profile.truth.target_class is PrimaryDirectionTargetClass.MIDPOINT
        ):
            raise ValueError(
                "PrimaryDirectionTargetsAggregateProfile invariant failed: midpoint_count mismatch"
            )
        if (
            self.planet_count
            + self.node_count
            + self.angle_count
            + self.house_cusp_count
            + self.aspect_count
            + self.bound_boundary_count
            + self.mundane_aspect_count
            + self.mundane_parallel_count
            + self.midpoint_count
            != self.total_profiles
        ):
            raise ValueError(
                "PrimaryDirectionTargetsAggregateProfile invariant failed: class counts must partition profiles"
            )
        expected_universal = sum(
            1
            for profile in self.profiles
            if profile.state is PrimaryDirectionTargetConditionState.UNIVERSALLY_ADMITTED
        )
        if self.universally_admitted_count != expected_universal:
            raise ValueError(
                "PrimaryDirectionTargetsAggregateProfile invariant failed: universally_admitted_count mismatch"
            )

    @property
    def significator_only_count(self) -> int:
        return sum(
            1
            for profile in self.profiles
            if profile.state is PrimaryDirectionTargetConditionState.SIGNIFICATOR_ONLY
        )

    @property
    def promissor_only_count(self) -> int:
        return sum(
            1
            for profile in self.profiles
            if profile.state is PrimaryDirectionTargetConditionState.PROMISSOR_ONLY
        )

    @property
    def not_admitted_count(self) -> int:
        return sum(
            1
            for profile in self.profiles
            if profile.state is PrimaryDirectionTargetConditionState.NOT_ADMITTED
        )


@dataclass(frozen=True, slots=True)
class PrimaryDirectionTargetsNetworkNode:
    """Vessel: Node in a primary direction targets network."""
    target_class: PrimaryDirectionTargetClass
    count: int

    def __post_init__(self) -> None:
        if not isinstance(self.target_class, PrimaryDirectionTargetClass):
            raise ValueError("PrimaryDirectionTargetsNetworkNode invariant failed: invalid target_class")
        if type(self.count) is not int or self.count <= 0:
            raise ValueError("PrimaryDirectionTargetsNetworkNode invariant failed: count must be positive")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionTargetsNetworkEdge:
    """Vessel: Directed edge in a primary direction targets network."""
    from_class: PrimaryDirectionTargetClass
    to_class: PrimaryDirectionTargetClass
    count: int

    def __post_init__(self) -> None:
        if not isinstance(self.from_class, PrimaryDirectionTargetClass) or not isinstance(
            self.to_class, PrimaryDirectionTargetClass
        ):
            raise ValueError("PrimaryDirectionTargetsNetworkEdge invariant failed: invalid target class")
        if self.from_class == self.to_class:
            raise ValueError(
                "PrimaryDirectionTargetsNetworkEdge invariant failed: self-edges are not admitted"
            )
        if type(self.count) is not int or self.count <= 0:
            raise ValueError("PrimaryDirectionTargetsNetworkEdge invariant failed: count must be positive")


@dataclass(frozen=True, slots=True)
class PrimaryDirectionTargetsNetworkProfile:
    """Vessel: Structural profile of an ordered target-class transition network."""
    nodes: tuple[PrimaryDirectionTargetsNetworkNode, ...]
    edges: tuple[PrimaryDirectionTargetsNetworkEdge, ...]
    dominant_class: PrimaryDirectionTargetClass
    isolated_classes: tuple[PrimaryDirectionTargetClass, ...]

    def __post_init__(self) -> None:
        try:
            nodes = tuple(self.nodes)
            edges = tuple(self.edges)
            isolated_classes = tuple(self.isolated_classes)
        except TypeError as exc:
            raise ValueError(
                "PrimaryDirectionTargetsNetworkProfile invariant failed: network collections must be iterable"
            ) from exc
        object.__setattr__(self, "nodes", nodes)
        object.__setattr__(self, "edges", edges)
        object.__setattr__(self, "isolated_classes", isolated_classes)
        if not self.nodes:
            raise ValueError("PrimaryDirectionTargetsNetworkProfile requires at least one node")
        if any(not isinstance(node, PrimaryDirectionTargetsNetworkNode) for node in self.nodes):
            raise ValueError("PrimaryDirectionTargetsNetworkProfile invariant failed: invalid node type")
        if any(not isinstance(edge, PrimaryDirectionTargetsNetworkEdge) for edge in self.edges):
            raise ValueError("PrimaryDirectionTargetsNetworkProfile invariant failed: invalid edge type")
        if not isinstance(self.dominant_class, PrimaryDirectionTargetClass):
            raise ValueError("PrimaryDirectionTargetsNetworkProfile invariant failed: invalid dominant_class")
        if any(not isinstance(item, PrimaryDirectionTargetClass) for item in self.isolated_classes):
            raise ValueError("PrimaryDirectionTargetsNetworkProfile invariant failed: invalid isolated class")
        classes = [node.target_class for node in self.nodes]
        if len(set(classes)) != len(classes):
            raise ValueError(
                "PrimaryDirectionTargetsNetworkProfile invariant failed: duplicate nodes"
            )
        if len(set(self.isolated_classes)) != len(self.isolated_classes):
            raise ValueError(
                "PrimaryDirectionTargetsNetworkProfile invariant failed: duplicate isolated classes"
            )
        edge_keys = [(edge.from_class, edge.to_class) for edge in self.edges]
        if len(set(edge_keys)) != len(edge_keys):
            raise ValueError("PrimaryDirectionTargetsNetworkProfile invariant failed: duplicate edges")
        node_by_class = {node.target_class: node for node in self.nodes}
        if any(
            edge.from_class not in node_by_class or edge.to_class not in node_by_class
            for edge in self.edges
        ):
            raise ValueError(
                "PrimaryDirectionTargetsNetworkProfile invariant failed: edge endpoint missing from nodes"
            )
        if any(
            edge.count
            > min(node_by_class[edge.from_class].count, node_by_class[edge.to_class].count)
            for edge in self.edges
        ):
            raise ValueError(
                "PrimaryDirectionTargetsNetworkProfile invariant failed: edge count exceeds endpoint occurrence count"
            )
        if sum(edge.count for edge in self.edges) > sum(node.count for node in self.nodes) - 1:
            raise ValueError(
                "PrimaryDirectionTargetsNetworkProfile invariant failed: edge count exceeds possible transitions"
            )
        validate_ordered_transition_counts(
            {node.target_class: node.count for node in self.nodes},
            {(edge.from_class, edge.to_class): edge.count for edge in self.edges},
            object_name="PrimaryDirectionTargetsNetworkProfile",
        )
        expected_dominant = max(
            self.nodes,
            key=lambda node: (node.count, node.target_class.value),
        ).target_class
        if self.dominant_class is not expected_dominant:
            raise ValueError(
                "PrimaryDirectionTargetsNetworkProfile invariant failed: dominant_class mismatch"
            )
        participating = {edge.from_class for edge in self.edges} | {
            edge.to_class for edge in self.edges
        }
        expected_isolated = tuple(
            sorted(
                (target_class for target_class in classes if target_class not in participating),
                key=lambda target_class: target_class.value,
            )
        )
        if self.isolated_classes != expected_isolated:
            raise ValueError(
                "PrimaryDirectionTargetsNetworkProfile invariant failed: isolated_classes mismatch"
            )


def _target_class_for_name(name: str) -> PrimaryDirectionTargetClass:
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Primary-direction target identity must be a non-empty string")
    if name.startswith("Term of ") or name.startswith("Bound: "):
        return PrimaryDirectionTargetClass.BOUND_BOUNDARY
    if _mundane_aspect_target_components(name) is not None:
        return PrimaryDirectionTargetClass.MUNDANE_ASPECT
    if _mundane_parallel_target_components(name) is not None:
        return PrimaryDirectionTargetClass.MUNDANE_PARALLEL
    if _midpoint_target_components(name) is not None:
        return PrimaryDirectionTargetClass.MIDPOINT
    if _aspect_target_components(name) is not None:
        return PrimaryDirectionTargetClass.ASPECTUAL_POINT
    if name in _ANGLE_NAMES:
        return PrimaryDirectionTargetClass.ANGLE
    if len(name) == 2 and name.startswith("H") and name[1].isdigit() and 1 <= int(name[1]) <= 9:
        return PrimaryDirectionTargetClass.HOUSE_CUSP
    if len(name) == 3 and name.startswith("H") and name[1:].isdigit() and 10 <= int(name[1:]) <= 12:
        return PrimaryDirectionTargetClass.HOUSE_CUSP
    if name in _NODE_NAMES:
        return PrimaryDirectionTargetClass.NODE
    if name in _PLANET_NAMES:
        return PrimaryDirectionTargetClass.PLANET
    raise ValueError(f"Unsupported primary-direction target identity: {name}")


_MAJOR_ASPECT_ANGLES: tuple[tuple[str, float], ...] = (
    ("Opposition", 180.0),
    ("Sinister Sextile", 60.0),
    ("Dexter Sextile", -60.0),
    ("Sextile", 60.0),
    ("Sinister Square", 90.0),
    ("Dexter Square", -90.0),
    ("Square", 90.0),
    ("Sinister Trine", 120.0),
    ("Dexter Trine", -120.0),
    ("Trine", 120.0),
)


def _aspect_target_components(name: str) -> tuple[str, str, float] | None:
    for aspect_name, angle in _MAJOR_ASPECT_ANGLES:
        suffix = f" {aspect_name}"
        if name.endswith(suffix):
            source_name = name[: -len(suffix)].strip()
            if not source_name:
                break
            _target_class_for_name(source_name)
            return source_name, aspect_name, angle
    return None


def _mundane_aspect_target_components(name: str) -> tuple[str, str, float] | None:
    for aspect_name, offset in PLACIDIAN_MUNDANE_ASPECT_OFFSETS:
        suffix = f" Mundane {aspect_name}"
        if name.endswith(suffix):
            source_name = name[: -len(suffix)].strip()
            if not source_name:
                break
            _target_class_for_name(source_name)
            return source_name, aspect_name, offset
    return None


def _mundane_parallel_target_components(
    name: str,
) -> tuple[str, PrimaryDirectionMundaneParallelKind] | None:
    for suffix, kind in (
        (" Mundane Parallel", PrimaryDirectionMundaneParallelKind.PARALLEL),
        (" Mundane Contra-Parallel", PrimaryDirectionMundaneParallelKind.CONTRA_PARALLEL),
    ):
        if name.endswith(suffix):
            source_name = name[: -len(suffix)].strip()
            if not source_name:
                break
            _target_class_for_name(source_name)
            return source_name, kind
    return None


def _midpoint_target_components(name: str) -> tuple[str, str] | None:
    suffix = " Midpoint"
    if name.endswith(suffix):
        body = name[: -len(suffix)].strip()
        if "/" in body:
            parts = body.split("/")
            if len(parts) == 2:
                a, b = parts[0].strip(), parts[1].strip()
                if a and b and a != b:
                    _target_class_for_name(a)
                    _target_class_for_name(b)
                    return a, b
    return None


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
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Primary-direction target identity must be a non-empty string")
    mundane_parallel_components = _mundane_parallel_target_components(name)
    if mundane_parallel_components is not None:
        source_name, parallel_kind = mundane_parallel_components
        return PrimaryDirectionTargetTruth(
            name=name,
            target_class=PrimaryDirectionTargetClass.MUNDANE_PARALLEL,
            source_name=source_name,
            parallel_kind=parallel_kind,
        )
    midpoint_components = _midpoint_target_components(name)
    if midpoint_components is not None:
        source_a, source_b = midpoint_components
        return PrimaryDirectionTargetTruth(
            name=name,
            target_class=PrimaryDirectionTargetClass.MIDPOINT,
            source_name=source_a,
            source_b_name=source_b,
        )
    mundane_components = _mundane_aspect_target_components(name)
    if mundane_components is not None:
        source_name, aspect_name, offset = mundane_components
        return PrimaryDirectionTargetTruth(
            name=name,
            target_class=PrimaryDirectionTargetClass.MUNDANE_ASPECT,
            source_name=source_name,
            aspect_name=aspect_name,
            fraction_offset=offset,
        )
    aspect_components = _aspect_target_components(name)
    if aspect_components is not None:
        source_name, aspect_name, angle = aspect_components
        return PrimaryDirectionTargetTruth(
            name=name,
            target_class=PrimaryDirectionTargetClass.ASPECTUAL_POINT,
            source_name=source_name,
            aspect_name=aspect_name,
            aspect_angle=angle,
        )
    return PrimaryDirectionTargetTruth(name=name, target_class=_target_class_for_name(name))


def classify_primary_direction_target(
    truth: PrimaryDirectionTargetTruth,
    *,
    policy: PrimaryDirectionTargetPolicy | None = None,
) -> PrimaryDirectionTargetClassification:
    if not isinstance(truth, PrimaryDirectionTargetTruth):
        raise ValueError("truth must be a PrimaryDirectionTargetTruth")
    if policy is not None and not isinstance(policy, PrimaryDirectionTargetPolicy):
        raise ValueError("policy must be a PrimaryDirectionTargetPolicy")
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
    if not isinstance(truth, PrimaryDirectionTargetTruth):
        raise ValueError("truth must be a PrimaryDirectionTargetTruth")
    if policy is not None and not isinstance(policy, PrimaryDirectionTargetPolicy):
        raise ValueError("policy must be a PrimaryDirectionTargetPolicy")
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
    if not isinstance(truth, PrimaryDirectionTargetTruth):
        raise ValueError("truth must be a PrimaryDirectionTargetTruth")
    if policy is not None and not isinstance(policy, PrimaryDirectionTargetPolicy):
        raise ValueError("policy must be a PrimaryDirectionTargetPolicy")
    relation = relate_primary_direction_target(truth, policy=policy)
    admitted = (
        ()
        if relation.relation_kind is PrimaryDirectionTargetRelationKind.REJECTED
        else (relation,)
    )
    scored = admitted
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
    if not isinstance(truth, PrimaryDirectionTargetTruth):
        raise ValueError("truth must be a PrimaryDirectionTargetTruth")
    if policy is not None and not isinstance(policy, PrimaryDirectionTargetPolicy):
        raise ValueError("policy must be a PrimaryDirectionTargetPolicy")
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
    if policy is not None and not isinstance(policy, PrimaryDirectionTargetPolicy):
        raise ValueError("policy must be a PrimaryDirectionTargetPolicy")
    try:
        truth_tuple = tuple(truths)
    except TypeError as exc:
        raise ValueError("truths must be an iterable of PrimaryDirectionTargetTruth") from exc
    profiles = tuple(
        evaluate_primary_direction_target_condition(truth, policy=policy)
        for truth in truth_tuple
    )
    if not profiles:
        raise ValueError("evaluate_primary_direction_targets_aggregate requires at least one truth")
    return PrimaryDirectionTargetsAggregateProfile(
        profiles=profiles,
        total_profiles=len(profiles),
        planet_count=sum(1 for p in profiles if p.truth.target_class is PrimaryDirectionTargetClass.PLANET),
        node_count=sum(1 for p in profiles if p.truth.target_class is PrimaryDirectionTargetClass.NODE),
        angle_count=sum(1 for p in profiles if p.truth.target_class is PrimaryDirectionTargetClass.ANGLE),
        house_cusp_count=sum(
            1 for p in profiles if p.truth.target_class is PrimaryDirectionTargetClass.HOUSE_CUSP
        ),
        aspect_count=sum(
            1 for p in profiles if p.truth.target_class is PrimaryDirectionTargetClass.ASPECTUAL_POINT
        ),
        bound_boundary_count=sum(
            1 for p in profiles if p.truth.target_class is PrimaryDirectionTargetClass.BOUND_BOUNDARY
        ),
        mundane_aspect_count=sum(
            1 for p in profiles if p.truth.target_class is PrimaryDirectionTargetClass.MUNDANE_ASPECT
        ),
        mundane_parallel_count=sum(
            1 for p in profiles if p.truth.target_class is PrimaryDirectionTargetClass.MUNDANE_PARALLEL
        ),
        midpoint_count=sum(
            1 for p in profiles if p.truth.target_class is PrimaryDirectionTargetClass.MIDPOINT
        ),
        universally_admitted_count=sum(
            1 for p in profiles if p.state is PrimaryDirectionTargetConditionState.UNIVERSALLY_ADMITTED
        ),
    )


def evaluate_primary_direction_targets_network(
    truths: Iterable[PrimaryDirectionTargetTruth],
    *,
    policy: PrimaryDirectionTargetPolicy | None = None,
) -> PrimaryDirectionTargetsNetworkProfile:
    """Build class transitions in input order, optionally gating target admission."""
    if policy is not None and not isinstance(policy, PrimaryDirectionTargetPolicy):
        raise ValueError("policy must be a PrimaryDirectionTargetPolicy")
    try:
        truth_tuple = tuple(truths)
    except TypeError as exc:
        raise ValueError("truths must be an iterable of PrimaryDirectionTargetTruth") from exc
    if not truth_tuple:
        raise ValueError("evaluate_primary_direction_targets_network requires at least one truth")
    if any(not isinstance(truth, PrimaryDirectionTargetTruth) for truth in truth_tuple):
        raise ValueError("truths must contain only PrimaryDirectionTargetTruth values")
    if policy is not None and any(
        evaluate_primary_direction_target_condition(truth, policy=policy).state
        is PrimaryDirectionTargetConditionState.NOT_ADMITTED
        for truth in truth_tuple
    ):
        raise ValueError(
            "evaluate_primary_direction_targets_network cannot represent a policy-rejected target"
        )
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


def resolve_primary_direction_bound_targets(
    doctrine: EgyptianBoundsDoctrine = EgyptianBoundsDoctrine.EGYPTIAN,
) -> tuple[PrimaryDirectionBoundTarget, ...]:
    """
    Generate the 60 canonical term/bound boundary targets across the zodiac.
    """
    if not isinstance(doctrine, EgyptianBoundsDoctrine):
        raise ValueError(f"doctrine must be an EgyptianBoundsDoctrine member, got {doctrine!r}")
    if doctrine is EgyptianBoundsDoctrine.PTOLEMAIC:
        table = PTOLEMAIC_BOUNDS
    elif doctrine is EgyptianBoundsDoctrine.CHALDEAN_DAY:
        table = CHALDEAN_DAY_BOUNDS
    elif doctrine is EgyptianBoundsDoctrine.CHALDEAN_NIGHT:
        table = CHALDEAN_NIGHT_BOUNDS
    else:
        table = EGYPTIAN_BOUNDS

    targets: list[PrimaryDirectionBoundTarget] = []
    for sign_idx, sign in enumerate(SIGNS):
        bounds = table[sign]
        for ruler, start_deg, _ in bounds:
            abs_lon = (sign_idx * 30.0 + start_deg) % 360.0
            name = f"Term of {ruler} ({int(start_deg):02d}°00' {sign[:3]})"
            targets.append(
                PrimaryDirectionBoundTarget(
                    name=name,
                    sign=sign,
                    degree_in_sign=float(start_deg),
                    absolute_longitude=float(abs_lon),
                    ruler=ruler,
                    doctrine=doctrine,
                )
            )
    return tuple(targets)


def resolve_primary_direction_mundane_aspect_targets(
    source_names: Iterable[str],
    aspect_filter: Iterable[str] | None = None,
) -> tuple[PrimaryDirectionMundaneAspectTarget, ...]:
    """Generate Placidian mundane aspect targets for the provided source bodies."""
    allowed_aspects = (
        set(aspect_filter) if aspect_filter is not None else None
    )
    targets: list[PrimaryDirectionMundaneAspectTarget] = []
    for source in source_names:
        for aspect_name, offset in PLACIDIAN_MUNDANE_ASPECT_OFFSETS:
            if allowed_aspects is not None and aspect_name not in allowed_aspects:
                continue
            targets.append(
                PrimaryDirectionMundaneAspectTarget(
                    source_name=source,
                    aspect_name=aspect_name,
                    fraction_offset=offset,
                )
            )
    return tuple(targets)


def resolve_primary_direction_mundane_parallel_targets(
    source_names: Iterable[str],
    *,
    include_contra_parallel: bool = True,
    kinds: Iterable[PrimaryDirectionMundaneParallelKind] | None = None,
) -> tuple[PrimaryDirectionMundaneParallelTarget, ...]:
    """Generate Placidian mundane parallel and contra-parallel targets."""
    targets: list[PrimaryDirectionMundaneParallelTarget] = []
    allowed_kinds = set(kinds) if kinds is not None else None
    for source in source_names:
        clean = source.strip()
        if not clean:
            continue
        if allowed_kinds is None or PrimaryDirectionMundaneParallelKind.PARALLEL in allowed_kinds:
            targets.append(
                PrimaryDirectionMundaneParallelTarget(
                    source_name=clean,
                    relation=PrimaryDirectionMundaneParallelKind.PARALLEL,
                )
            )
        if (allowed_kinds is None and include_contra_parallel) or (
            allowed_kinds is not None
            and PrimaryDirectionMundaneParallelKind.CONTRA_PARALLEL in allowed_kinds
        ):
            targets.append(
                PrimaryDirectionMundaneParallelTarget(
                    source_name=clean,
                    relation=PrimaryDirectionMundaneParallelKind.CONTRA_PARALLEL,
                )
            )
    return tuple(targets)


def resolve_primary_direction_midpoint_targets(
    pairs: Iterable[tuple[str, str]],
) -> tuple[PrimaryDirectionMidpointTarget, ...]:
    """Generate zodiacal shortest-arc midpoint targets for pairs of bodies."""
    targets: list[PrimaryDirectionMidpointTarget] = []
    for a, b in pairs:
        clean_a, clean_b = a.strip(), b.strip()
        if not clean_a or not clean_b or clean_a == clean_b:
            continue
        targets.append(
            PrimaryDirectionMidpointTarget(
                source_a=clean_a,
                source_b=clean_b,
            )
        )
    return tuple(targets)


