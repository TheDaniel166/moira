"""
Moira — Aspect Pattern Engine
==============================

Archetype: Engine

Purpose
-------
Governs detection of classical and modern multi-body aspect configurations
within a natal chart, including T-Squares, Grand Trines, Yods, Kites,
Stelliums, and seventeen additional pattern types.

Boundary declaration
--------------------
Owns: pattern detection logic, orb arithmetic, deduplication of matched
      configurations, and the ``AspectPattern`` result vessel.
Delegates: aspect computation to ``moira.aspects``,
           angular distance arithmetic to ``moira.coordinates``.

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required. No database access. Pure computation over
pre-computed aspect lists and position dicts.

Orb doctrine
------------
All base orbs derive from ``moira.constants.DEFAULT_ORBS``, the same table
used by the aspect engine.  Pattern-specific orbs are listed in each detector
docstring and are scaled by the caller-supplied ``orb_factor``.

    Conjunction / Opposition : 8.0°
    Trine                    : 7.0°
    Square                   : 7.0°
    Sextile                  : 5.0°
    Quincunx (150°)          : 3.0°
    Semisquare (45°)         : 2.0°
    Sesquiquadrate (135°)    : 2.0°
    Quintile (72°)           : 2.0°
    Biquintile (144°)        : 2.0°
    Septile (51.43°)         : 1.5°
    Biseptile (102.86°)      : 1.5°
    Triseptile (154.29°)     : 1.5°

Public surface
--------------
``AspectPattern``           — vessel for a detected multi-body configuration.
``find_t_squares``          — detect T-Square configurations.
``find_grand_trines``       — detect Grand Trine configurations.
``find_grand_crosses``      — detect Grand Cross configurations.
``find_yods``               — detect Yod (Finger of God) configurations.
``find_mystic_rectangles``  — detect Mystic Rectangle configurations.
``find_kites``              — detect Kite configurations.
``find_stelliums``          — detect Stellium clusters.
``find_minor_grand_trines`` — detect Minor Grand Trine configurations.
``find_grand_sextiles``     — detect Grand Sextile (Star of David) configurations.
``find_thors_hammers``      — detect Thor's Hammer configurations.
``find_boomerang_yods``     — detect Boomerang Yod configurations.
``find_wedges``             — detect Wedge (Arrowhead) configurations.
``find_cradles``            — detect Cradle configurations.
``find_trapezes``           — detect Trapeze configurations.
``find_eyes``               — detect Eye (Cosmic Eye) configurations.
``find_irritation_triangles`` — detect Irritation Triangle configurations.
``find_hard_wedges``        — detect Hard Wedge configurations.
``find_dominant_triangles`` — detect Dominant Triangle configurations.
``find_grand_quintiles``    — detect Grand Quintile configurations.
``find_quintile_triangles`` — detect Quintile Triangle configurations.
``find_septile_triangles``  — detect Septile Triangle configurations.
``find_all_patterns``       — detect all registered patterns in one call.
"""

import math
from dataclasses import dataclass, field
from enum import StrEnum
from itertools import combinations

from .aspects import AspectData, find_aspects
from .coordinates import angular_distance


__all__ = [
    "AspectPattern",
    "PatternBodyRoleTruth",
    "PatternDetectionTruth",
    "PatternSourceKind",
    "PatternSymmetryKind",
    "PatternBodyRoleKind",
    "PatternBodyRoleClassification",
    "PatternClassification",
    "PatternAspectRoleKind",
    "PatternAspectContribution",
    "PatternConditionState",
    "PatternConditionProfile",
    "PatternChartConditionProfile",
    "PatternConditionNetworkNode",
    "PatternConditionNetworkEdge",
    "PatternConditionNetworkProfile",
    "all_pattern_contributions",
    "pattern_chart_condition_profile",
    "pattern_condition_network_profile",
    "pattern_condition_profiles",
    "pattern_contributions",
    "PatternSelectionPolicy",
    "StelliumPolicy",
    "PatternComputationPolicy",
    "find_t_squares",
    "find_grand_trines",
    "find_grand_crosses",
    "find_yods",
    "find_mystic_rectangles",
    "find_kites",
    "find_stelliums",
    "find_minor_grand_trines",
    "find_grand_sextiles",
    "find_thors_hammers",
    "find_boomerang_yods",
    "find_wedges",
    "find_cradles",
    "find_trapezes",
    "find_eyes",
    "find_irritation_triangles",
    "find_hard_wedges",
    "find_dominant_triangles",
    "find_grand_quintiles",
    "find_quintile_triangles",
    "find_septile_triangles",
    "find_all_patterns",
]


# ---------------------------------------------------------------------------
# Result vessel
# ---------------------------------------------------------------------------


class PatternSourceKind(StrEnum):
    """Typed source classification for a detected pattern."""

    ASPECT = "aspect"
    POSITION = "position"


class PatternSymmetryKind(StrEnum):
    """Typed symmetry classification for a detected pattern."""

    SYMMETRIC = "symmetric"
    APEX_BEARING = "apex_bearing"


class PatternBodyRoleKind(StrEnum):
    """Typed body-role classification for a detected pattern."""

    MEMBER = "member"
    APEX = "apex"
    BASE = "base"
    SUPPORT = "support"
    TAIL = "tail"
    AXIS = "axis"
    CLUSTER_MEMBER = "cluster_member"
    BOOMERANG = "boomerang"


class PatternAspectRoleKind(StrEnum):
    """Typed relational role for one contributing aspect inside a pattern."""

    MEMBER_LINK = "member_link"
    BASE_LINK = "base_link"
    APEX_LINK = "apex_link"
    AXIS_LINK = "axis_link"
    SUPPORT_LINK = "support_link"


class PatternConditionState(StrEnum):
    """Structural integrated condition state for one detected pattern."""

    REINFORCED = "reinforced"
    MIXED = "mixed"
    WEAKENED = "weakened"


@dataclass(frozen=True, slots=True)
class PatternSelectionPolicy:
    """Policy governing which named pattern detectors are admitted."""

    include: tuple[str, ...] | None = None


@dataclass(frozen=True, slots=True)
class StelliumPolicy:
    """Policy governing the currently supported Stellium doctrine inputs."""

    min_bodies: int = 3
    orb: float = 8.0


@dataclass(frozen=True, slots=True)
class PatternComputationPolicy:
    """
    Lean backend policy surface for the pattern engine.

    The default policy is intentionally identical to the current engine
    behavior.
    """

    orb_factor: float = 1.0
    selection: PatternSelectionPolicy = field(default_factory=PatternSelectionPolicy)
    stellium: StelliumPolicy = field(default_factory=StelliumPolicy)

    @property
    def is_default(self) -> bool:
        """Return True when this policy matches current default behavior."""

        return self == PatternComputationPolicy()

@dataclass(frozen=True, slots=True)
class PatternBodyRoleTruth:
    """Structured role truth for one body inside a detected pattern."""

    body: str
    role: str

    def __post_init__(self) -> None:
        PatternBodyRoleKind(self.role)


@dataclass(frozen=True, slots=True)
class PatternDetectionTruth:
    """
    Structured doctrinal/computational path for one detected pattern.

    This is Phase 1 truth preservation only. It records which detector matched,
    whether the match was aspect- or position-driven, and what body-role
    structure the detector assigned so later layers do not need to reconstruct
    hidden logic from the flattened `AspectPattern` vessel.
    """

    pattern_name: str
    detector: str
    source_kind: str
    orb_factor: float
    body_roles: tuple[PatternBodyRoleTruth, ...]
    centroid_longitude: float | None = None
    max_body_distance: float | None = None
    orb_limit: float | None = None

    def __post_init__(self) -> None:
        if self.source_kind not in {"aspect", "position"}:
            raise ValueError("PatternDetectionTruth invariant failed: source_kind must be 'aspect' or 'position'")
        if not self.body_roles:
            raise ValueError("PatternDetectionTruth invariant failed: body_roles must not be empty")
        if len({role.body for role in self.body_roles}) != len(self.body_roles):
            raise ValueError("PatternDetectionTruth invariant failed: body_roles must not repeat bodies")
        if self.source_kind == "position":
            if self.centroid_longitude is None or self.max_body_distance is None or self.orb_limit is None:
                raise ValueError("PatternDetectionTruth invariant failed: position-based truth must preserve centroid and spread")


@dataclass(frozen=True, slots=True)
class PatternBodyRoleClassification:
    """Typed classification for one pattern body role."""

    body: str
    role: PatternBodyRoleKind


@dataclass(frozen=True, slots=True)
class PatternClassification:
    """
    Lean typed classification of an already-detected pattern.

    This classifies preserved detector truth. It does not alter pattern
    detection semantics or admission logic.
    """

    pattern_name: str
    detector: str
    source_kind: PatternSourceKind
    symmetry: PatternSymmetryKind
    body_count: int
    has_apex: bool
    body_roles: tuple[PatternBodyRoleClassification, ...]

    def __post_init__(self) -> None:
        if self.body_count != len(self.body_roles):
            raise ValueError("PatternClassification invariant failed: body_count must match body_roles")
        if len({role.body for role in self.body_roles}) != len(self.body_roles):
            raise ValueError("PatternClassification invariant failed: body_roles must not repeat bodies")
        if self.has_apex != any(role.role is PatternBodyRoleKind.APEX for role in self.body_roles):
            raise ValueError("PatternClassification invariant failed: has_apex must match body roles")


@dataclass(frozen=True, slots=True)
class PatternAspectContribution:
    """
    Formal relational contribution for one aspect inside a detected pattern.

    This is a backend-only relational layer derived from the existing pattern
    truth and classification. It does not recompute pattern doctrine.
    """

    pattern_name: str
    role: PatternAspectRoleKind
    body1: str
    body2: str
    aspect_name: str
    aspect_angle: float
    aspect: AspectData

    def __post_init__(self) -> None:
        if self.body1 == self.body2:
            raise ValueError("PatternAspectContribution invariant failed: body1 and body2 must differ")
        if {self.body1, self.body2} != {self.aspect.body1, self.aspect.body2}:
            raise ValueError("PatternAspectContribution invariant failed: bodies must match aspect endpoints")
        if self.aspect_name != self.aspect.aspect:
            raise ValueError("PatternAspectContribution invariant failed: aspect_name must match aspect.aspect")
        if self.aspect_angle != self.aspect.angle:
            raise ValueError("PatternAspectContribution invariant failed: aspect_angle must match aspect.angle")


@dataclass(frozen=True, slots=True)
class PatternConditionProfile:
    """
    Integrated structural condition profile for one detected pattern.

    This is a derived backend-only summary over preserved pattern truth,
    classification, and contribution structure. It does not recompute pattern
    doctrine or alter detection semantics.
    """

    pattern_name: str
    detector: str
    source_kind: PatternSourceKind
    symmetry: PatternSymmetryKind
    body_count: int
    has_apex: bool
    contribution_count: int
    all_contribution_count: int
    structured_contribution_count: int
    generic_contribution_count: int
    state: PatternConditionState

    def __post_init__(self) -> None:
        if self.body_count <= 0:
            raise ValueError("PatternConditionProfile invariant failed: body_count must be positive")
        if self.contribution_count < 0 or self.all_contribution_count < 0:
            raise ValueError("PatternConditionProfile invariant failed: contribution counts must be non-negative")
        if self.contribution_count > self.all_contribution_count:
            raise ValueError("PatternConditionProfile invariant failed: contribution_count must not exceed all_contribution_count")
        if self.structured_contribution_count < 0 or self.generic_contribution_count < 0:
            raise ValueError("PatternConditionProfile invariant failed: contribution role counts must be non-negative")
        if self.structured_contribution_count + self.generic_contribution_count != self.all_contribution_count:
            raise ValueError("PatternConditionProfile invariant failed: contribution role counts must cover all_contributions")
        if self.has_apex != (self.symmetry is PatternSymmetryKind.APEX_BEARING):
            raise ValueError("PatternConditionProfile invariant failed: has_apex must match symmetry")


@dataclass(frozen=True, slots=True)
class PatternChartConditionProfile:
    """
    Chart-wide structural condition profile aggregated from pattern profiles.

    This is a pure aggregation layer over ``PatternConditionProfile``. It does
    not perform fresh pattern detection or redefine local doctrine.
    """

    profiles: tuple[PatternConditionProfile, ...]
    reinforced_count: int
    mixed_count: int
    weakened_count: int
    structured_contribution_total: int
    generic_contribution_total: int
    strongest_patterns: tuple[str, ...]
    weakest_patterns: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.reinforced_count < 0 or self.mixed_count < 0 or self.weakened_count < 0:
            raise ValueError("PatternChartConditionProfile invariant failed: state counts must be non-negative")
        if self.reinforced_count + self.mixed_count + self.weakened_count != len(self.profiles):
            raise ValueError("PatternChartConditionProfile invariant failed: state counts must cover profiles")
        if self.structured_contribution_total < 0 or self.generic_contribution_total < 0:
            raise ValueError("PatternChartConditionProfile invariant failed: contribution totals must be non-negative")
        if tuple(sorted(self.profiles, key=lambda profile: (profile.pattern_name, profile.detector, profile.body_count))) != self.profiles:
            raise ValueError("PatternChartConditionProfile invariant failed: profiles must be deterministically ordered")
        if tuple(sorted(self.strongest_patterns)) != self.strongest_patterns:
            raise ValueError("PatternChartConditionProfile invariant failed: strongest_patterns must be deterministically ordered")
        if tuple(sorted(self.weakest_patterns)) != self.weakest_patterns:
            raise ValueError("PatternChartConditionProfile invariant failed: weakest_patterns must be deterministically ordered")
        if self.structured_contribution_total != sum(profile.structured_contribution_count for profile in self.profiles):
            raise ValueError("PatternChartConditionProfile invariant failed: structured_contribution_total must match profiles")
        if self.generic_contribution_total != sum(profile.generic_contribution_count for profile in self.profiles):
            raise ValueError("PatternChartConditionProfile invariant failed: generic_contribution_total must match profiles")
        if self.profiles:
            strongest_rank = max(_pattern_profile_rank(profile) for profile in self.profiles)
            weakest_rank = min(_pattern_profile_rank(profile) for profile in self.profiles)
            expected_strongest = tuple(sorted(
                profile.pattern_name
                for profile in self.profiles
                if _pattern_profile_rank(profile) == strongest_rank
            ))
            expected_weakest = tuple(sorted(
                profile.pattern_name
                for profile in self.profiles
                if _pattern_profile_rank(profile) == weakest_rank
            ))
            if self.strongest_patterns != expected_strongest:
                raise ValueError("PatternChartConditionProfile invariant failed: strongest_patterns must match profiles")
            if self.weakest_patterns != expected_weakest:
                raise ValueError("PatternChartConditionProfile invariant failed: weakest_patterns must match profiles")

    @property
    def profile_count(self) -> int:
        """Return the number of aggregated pattern condition profiles."""

        return len(self.profiles)

    @property
    def strongest_count(self) -> int:
        """Return the number of strongest patterns."""

        return len(self.strongest_patterns)

    @property
    def weakest_count(self) -> int:
        """Return the number of weakest patterns."""

        return len(self.weakest_patterns)


@dataclass(frozen=True, slots=True)
class PatternConditionNetworkNode:
    """One node in the pattern-condition network."""

    node_id: str
    kind: str
    label: str
    incoming_count: int
    outgoing_count: int
    total_degree: int

    def __post_init__(self) -> None:
        if self.kind not in {"pattern", "body"}:
            raise ValueError("PatternConditionNetworkNode invariant failed: kind must be 'pattern' or 'body'")
        if self.incoming_count < 0 or self.outgoing_count < 0 or self.total_degree < 0:
            raise ValueError("PatternConditionNetworkNode invariant failed: degree counts must be non-negative")
        if self.total_degree != self.incoming_count + self.outgoing_count:
            raise ValueError("PatternConditionNetworkNode invariant failed: total_degree must match incoming plus outgoing")


@dataclass(frozen=True, slots=True)
class PatternConditionNetworkEdge:
    """One directed structural link in the pattern-condition network."""

    source_id: str
    target_id: str
    pattern_name: str
    role: PatternAspectRoleKind | PatternBodyRoleKind

    def __post_init__(self) -> None:
        if self.source_id == self.target_id:
            raise ValueError("PatternConditionNetworkEdge invariant failed: source_id and target_id must differ")


@dataclass(frozen=True, slots=True)
class PatternConditionNetworkProfile:
    """Deterministic network projection over pattern condition truth."""

    nodes: tuple[PatternConditionNetworkNode, ...]
    edges: tuple[PatternConditionNetworkEdge, ...]
    isolated_bodies: tuple[str, ...]
    most_connected_nodes: tuple[str, ...]

    def __post_init__(self) -> None:
        if tuple(sorted(self.nodes, key=lambda node: (node.kind, node.label, node.node_id))) != self.nodes:
            raise ValueError("PatternConditionNetworkProfile invariant failed: nodes must be deterministically ordered")
        if tuple(sorted(
            self.edges,
            key=lambda edge: (edge.pattern_name, edge.source_id, edge.target_id, edge.role.value),
        )) != self.edges:
            raise ValueError("PatternConditionNetworkProfile invariant failed: edges must be deterministically ordered")
        if tuple(sorted(self.isolated_bodies)) != self.isolated_bodies:
            raise ValueError("PatternConditionNetworkProfile invariant failed: isolated_bodies must be deterministically ordered")
        if tuple(sorted(self.most_connected_nodes)) != self.most_connected_nodes:
            raise ValueError("PatternConditionNetworkProfile invariant failed: most_connected_nodes must be deterministically ordered")
        if len({node.node_id for node in self.nodes}) != len(self.nodes):
            raise ValueError("PatternConditionNetworkProfile invariant failed: node ids must be unique")
        node_ids = {node.node_id for node in self.nodes}
        for edge in self.edges:
            if edge.source_id not in node_ids or edge.target_id not in node_ids:
                raise ValueError("PatternConditionNetworkProfile invariant failed: edges must reference existing nodes")
        incoming_counts = {node.node_id: 0 for node in self.nodes}
        outgoing_counts = {node.node_id: 0 for node in self.nodes}
        for edge in self.edges:
            outgoing_counts[edge.source_id] += 1
            incoming_counts[edge.target_id] += 1
        for node in self.nodes:
            if node.incoming_count != incoming_counts[node.node_id]:
                raise ValueError("PatternConditionNetworkProfile invariant failed: node incoming_count must match edges")
            if node.outgoing_count != outgoing_counts[node.node_id]:
                raise ValueError("PatternConditionNetworkProfile invariant failed: node outgoing_count must match edges")
        expected_isolated = tuple(sorted(
            node.label
            for node in self.nodes
            if node.kind == "body" and node.total_degree == 0
        ))
        if self.isolated_bodies != expected_isolated:
            raise ValueError("PatternConditionNetworkProfile invariant failed: isolated_bodies must match nodes")
        max_degree = max((node.total_degree for node in self.nodes), default=0)
        expected_most_connected = tuple(sorted(
            node.label
            for node in self.nodes
            if node.total_degree == max_degree and max_degree > 0
        ))
        if self.most_connected_nodes != expected_most_connected:
            raise ValueError("PatternConditionNetworkProfile invariant failed: most_connected_nodes must match nodes")

    @property
    def node_count(self) -> int:
        """Return the number of network nodes."""

        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        """Return the number of network edges."""

        return len(self.edges)


@dataclass(frozen=True, slots=True)
class AspectPattern:
    """
    A detected multi-body aspect configuration.

    Fields
    ------
    name    : pattern name (e.g. "T-Square", "Grand Trine").
    bodies  : tuple of body names involved; apex planet is last for
              apex-bearing patterns (T-Square, Yod, Kite, etc.).
    aspects : tuple of the contributing AspectData instances.
    apex    : focal/apex planet name, or None for symmetric patterns.

    Structural invariants
    ---------------------
    - ``bodies`` is always non-empty.
    - ``aspects`` may be empty for Stelliums (position-based, not aspect-based).
    - ``apex`` is None for symmetric patterns (Grand Trine, Grand Cross, etc.).
    - The vessel is immutable.
    """
    name:    str
    bodies:  tuple[str, ...]
    aspects: tuple[AspectData, ...]
    apex:    str | None = None
    detection_truth: PatternDetectionTruth | None = None
    classification: PatternClassification | None = None
    all_contributions: tuple[PatternAspectContribution, ...] = ()
    contributions: tuple[PatternAspectContribution, ...] = ()
    condition_profile: PatternConditionProfile | None = None

    def __post_init__(self) -> None:
        if not self.bodies:
            raise ValueError("AspectPattern invariant failed: bodies must not be empty")
        if self.apex is not None and self.apex not in self.bodies:
            raise ValueError("AspectPattern invariant failed: apex must be one of bodies")
        if self.detection_truth is not None:
            if self.detection_truth.pattern_name != self.name:
                raise ValueError("AspectPattern invariant failed: detection_truth pattern_name must match name")
            truth_bodies = tuple(role.body for role in self.detection_truth.body_roles)
            if frozenset(truth_bodies) != frozenset(self.bodies):
                raise ValueError("AspectPattern invariant failed: detection_truth body roles must match pattern bodies")
            if self.apex is not None and not any(
                role.body == self.apex and role.role == "apex"
                for role in self.detection_truth.body_roles
            ):
                raise ValueError("AspectPattern invariant failed: apex-bearing patterns must preserve an apex body role")
        if self.classification is not None:
            if self.classification.pattern_name != self.name:
                raise ValueError("AspectPattern invariant failed: classification pattern_name must match name")
            if self.classification.body_count != len(self.bodies):
                raise ValueError("AspectPattern invariant failed: classification body_count must match bodies")
            if self.classification.has_apex != (self.apex is not None):
                raise ValueError("AspectPattern invariant failed: classification has_apex must match apex presence")
        if self.detection_truth is not None and self.classification is not None:
            if self.classification.detector != self.detection_truth.detector:
                raise ValueError("AspectPattern invariant failed: classification detector must match detection truth")
            if self.classification.source_kind.value != self.detection_truth.source_kind:
                raise ValueError("AspectPattern invariant failed: classification source_kind must match detection truth")
            expected_roles = tuple(
                PatternBodyRoleClassification(body=role.body, role=PatternBodyRoleKind(role.role))
                for role in self.detection_truth.body_roles
            )
            if self.classification.body_roles != expected_roles:
                raise ValueError("AspectPattern invariant failed: classification body_roles must match detection truth")
        aspect_signatures = {
            _aspect_signature(aspect)
            for aspect in self.aspects
        }
        if self.all_contributions:
            all_contribution_signatures = {
                _aspect_signature(contribution.aspect)
                for contribution in self.all_contributions
            }
            if len(all_contribution_signatures) != len(self.all_contributions):
                raise ValueError("AspectPattern invariant failed: all_contributions must not repeat aspects")
            if all_contribution_signatures != aspect_signatures:
                raise ValueError("AspectPattern invariant failed: all_contributions must match pattern aspects")
            if any(contribution.pattern_name != self.name for contribution in self.all_contributions):
                raise ValueError("AspectPattern invariant failed: all_contributions must match pattern name")
            expected_bodies = frozenset(self.bodies)
            if any({contribution.body1, contribution.body2} - expected_bodies for contribution in self.all_contributions):
                raise ValueError("AspectPattern invariant failed: all_contributions must only reference pattern bodies")
        if self.contributions:
            contribution_signatures = {
                _contribution_signature(contribution)
                for contribution in self.contributions
            }
            if len(contribution_signatures) != len(self.contributions):
                raise ValueError("AspectPattern invariant failed: contributions must not repeat aspect relations")
            if self.all_contributions:
                all_contribution_signatures = {
                    _contribution_signature(contribution)
                    for contribution in self.all_contributions
                }
                if not contribution_signatures <= all_contribution_signatures:
                    raise ValueError("AspectPattern invariant failed: contributions must be a subset of all_contributions")
                if contribution_signatures != all_contribution_signatures:
                    raise ValueError("AspectPattern invariant failed: contributions must match all_contributions under current doctrine")
            elif {
                _aspect_signature(contribution.aspect)
                for contribution in self.contributions
            } != aspect_signatures:
                raise ValueError("AspectPattern invariant failed: contributions must match pattern aspects")
            if any(contribution.pattern_name != self.name for contribution in self.contributions):
                raise ValueError("AspectPattern invariant failed: contributions must match pattern name")
            expected_bodies = frozenset(self.bodies)
            if any({contribution.body1, contribution.body2} - expected_bodies for contribution in self.contributions):
                raise ValueError("AspectPattern invariant failed: contributions must only reference pattern bodies")
        if self.condition_profile is not None:
            if self.classification is None:
                raise ValueError("AspectPattern invariant failed: condition_profile requires classification")
            if self.condition_profile.pattern_name != self.name:
                raise ValueError("AspectPattern invariant failed: condition_profile pattern_name must match name")
            if self.condition_profile.detector != self.classification.detector:
                raise ValueError("AspectPattern invariant failed: condition_profile detector must match classification")
            if self.condition_profile.source_kind is not self.classification.source_kind:
                raise ValueError("AspectPattern invariant failed: condition_profile source_kind must match classification")
            if self.condition_profile.symmetry is not self.classification.symmetry:
                raise ValueError("AspectPattern invariant failed: condition_profile symmetry must match classification")
            if self.condition_profile.body_count != len(self.bodies):
                raise ValueError("AspectPattern invariant failed: condition_profile body_count must match bodies")
            if self.condition_profile.has_apex != (self.apex is not None):
                raise ValueError("AspectPattern invariant failed: condition_profile has_apex must match apex presence")
            if self.condition_profile.contribution_count != len(self.contributions):
                raise ValueError("AspectPattern invariant failed: condition_profile contribution_count must match contributions")
            if self.condition_profile.all_contribution_count != len(self.all_contributions):
                raise ValueError("AspectPattern invariant failed: condition_profile all_contribution_count must match all_contributions")
            expected_structured_count = sum(
                contribution.role is not PatternAspectRoleKind.MEMBER_LINK
                for contribution in self.all_contributions
            )
            if self.condition_profile.structured_contribution_count != expected_structured_count:
                raise ValueError("AspectPattern invariant failed: condition_profile structured_contribution_count must match contributions")
            if self.condition_profile.generic_contribution_count != len(self.all_contributions) - expected_structured_count:
                raise ValueError("AspectPattern invariant failed: condition_profile generic_contribution_count must match contributions")

    def __repr__(self) -> str:
        parts = " - ".join(self.bodies)
        apex_str = f" [apex: {self.apex}]" if self.apex else ""
        return f"{self.name}: {parts}{apex_str}"

    @property
    def detector(self) -> str | None:
        """Return the detector name when preserved truth is available."""

        if self.classification is not None:
            return self.classification.detector
        if self.detection_truth is not None:
            return self.detection_truth.detector
        return None

    @property
    def source_kind(self) -> PatternSourceKind | None:
        """Return the typed source kind when classification is available."""

        if self.classification is not None:
            return self.classification.source_kind
        if self.detection_truth is not None:
            return PatternSourceKind(self.detection_truth.source_kind)
        return None

    @property
    def symmetry_kind(self) -> PatternSymmetryKind | None:
        """Return the typed symmetry classification when available."""

        if self.classification is not None:
            return self.classification.symmetry
        if self.apex is not None:
            return PatternSymmetryKind.APEX_BEARING
        if self.detection_truth is not None:
            return PatternSymmetryKind.SYMMETRIC
        return None

    @property
    def body_role_kinds(self) -> tuple[PatternBodyRoleKind, ...]:
        """Return the typed body-role kinds for this pattern when available."""

        if self.classification is not None:
            return tuple(role.role for role in self.classification.body_roles)
        if self.detection_truth is not None:
            return tuple(PatternBodyRoleKind(role.role) for role in self.detection_truth.body_roles)
        return ()

    @property
    def is_position_based(self) -> bool:
        """Return True when this pattern was detected from positions rather than aspects."""

        return self.source_kind is PatternSourceKind.POSITION

    @property
    def is_apex_bearing(self) -> bool:
        """Return True when this pattern has an explicit apex-bearing structure."""

        return self.symmetry_kind is PatternSymmetryKind.APEX_BEARING

    @property
    def contribution_roles(self) -> tuple[PatternAspectRoleKind, ...]:
        """Return the typed contribution roles for this pattern."""

        return tuple(contribution.role for contribution in self.contributions)

    @property
    def admitted_contributions(self) -> tuple[PatternAspectContribution, ...]:
        """Return the admitted contributing aspect relations for this pattern."""

        return self.contributions

    @property
    def all_contribution_roles(self) -> tuple[PatternAspectRoleKind, ...]:
        """Return the roles for the full preserved contribution surface."""

        return tuple(contribution.role for contribution in self.all_contributions)

    @property
    def contribution_count(self) -> int:
        """Return the admitted contribution count."""

        return len(self.contributions)

    @property
    def all_contribution_count(self) -> int:
        """Return the full preserved contribution count."""

        return len(self.all_contributions)

    @property
    def has_contributions(self) -> bool:
        """Return True when the pattern has admitted aspect contributions."""

        return bool(self.contributions)

    @property
    def condition_state(self) -> PatternConditionState | None:
        """Return the integrated structural condition state when available."""

        if self.condition_profile is None:
            return None
        return self.condition_profile.state


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_aspect_map(
    aspects: list[AspectData],
) -> dict[tuple[str, str], AspectData]:
    """Build a bidirectional lookup: (b1, b2) and (b2, b1) -> AspectData."""
    mapping: dict[tuple[str, str], AspectData] = {}
    for asp in aspects:
        mapping[(asp.body1, asp.body2)] = asp
        mapping[(asp.body2, asp.body1)] = asp
    return mapping


def _get_aspect(
    aspect_map: dict[tuple[str, str], AspectData],
    b1: str,
    b2: str,
    target_angle: float,
    orb: float,
) -> AspectData | None:
    """
    Return the aspect between b1 and b2 if it was admitted within ``orb``
    degrees of ``target_angle``, else None.

    Admission test: asp.orb <= orb.
    The asp.orb field already encodes the angular deviation from the target
    angle as recorded at admission time by find_aspects; no secondary
    angle check is applied here.
    """
    asp = aspect_map.get((b1, b2))
    if asp is not None and asp.orb <= orb:
        return asp
    return None


def _dedup_patterns(patterns: list[AspectPattern]) -> list[AspectPattern]:
    """
    Remove duplicate patterns.  Two patterns are duplicates when they share
    the same name and the same body set.  The first occurrence is kept.
    """
    seen: set[tuple[str, frozenset[str]]] = set()
    unique: list[AspectPattern] = []
    for p in patterns:
        key = (p.name, frozenset(p.bodies))
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def _validate_positions(positions: dict[str, float]) -> dict[str, float]:
    """Validate chart positions for pattern computation."""

    normalized: dict[str, float] = {}
    for body, longitude in positions.items():
        if not isinstance(body, str) or not body.strip():
            raise ValueError("Pattern positions must use non-empty body names")
        if not isinstance(longitude, (int, float)) or not math.isfinite(longitude):
            raise ValueError("Pattern positions must use finite longitudes")
        normalized_name = body.strip()
        if normalized_name in normalized:
            raise ValueError("Pattern positions must not repeat body names")
        normalized[normalized_name] = float(longitude)
    return normalized


def _validate_aspects(aspects: list[AspectData]) -> list[AspectData]:
    """Validate pre-computed aspects for pattern computation."""

    validated: list[AspectData] = []
    for aspect in aspects:
        if not aspect.body1 or not aspect.body2:
            raise ValueError("Pattern aspects must use non-empty body names")
        if aspect.body1 == aspect.body2:
            raise ValueError("Pattern aspects must connect two distinct bodies")
        if not math.isfinite(aspect.angle) or not math.isfinite(aspect.orb) or not math.isfinite(aspect.allowed_orb):
            raise ValueError("Pattern aspects must use finite angles and orbs")
        if aspect.orb < 0 or aspect.allowed_orb < 0:
            raise ValueError("Pattern aspects must use non-negative orbs")
        validated.append(aspect)
    return validated


def _bodies_from(aspects: list[AspectData]) -> list[str]:
    """Sorted unique body list from an aspect list."""
    return sorted({asp.body1 for asp in aspects} | {asp.body2 for asp in aspects})


def _aspect_signature(aspect: AspectData) -> tuple[str, str, str, float, float, float]:
    """Return a deterministic signature for one admitted aspect relation."""

    bodies = tuple(sorted((aspect.body1, aspect.body2)))
    return (
        bodies[0],
        bodies[1],
        aspect.aspect,
        aspect.angle,
        aspect.orb,
        aspect.allowed_orb,
    )


def _contribution_signature(
    contribution: PatternAspectContribution,
) -> tuple[str, str, str, str, str, float, float, float]:
    """Return a deterministic signature for one formal pattern contribution."""

    return (
        contribution.pattern_name,
        contribution.role.value,
        contribution.body1,
        contribution.body2,
        contribution.aspect_name,
        contribution.aspect_angle,
        contribution.aspect.orb,
        contribution.aspect.allowed_orb,
    )


def _derive_pattern_condition_state(
    *,
    all_contributions: tuple[PatternAspectContribution, ...],
) -> PatternConditionState:
    """Derive a structural condition state from preserved contribution truth."""

    if not all_contributions:
        return PatternConditionState.WEAKENED
    structured_count = sum(
        contribution.role is not PatternAspectRoleKind.MEMBER_LINK
        for contribution in all_contributions
    )
    if structured_count == len(all_contributions):
        return PatternConditionState.REINFORCED
    return PatternConditionState.MIXED


def _build_pattern_condition_profile(
    *,
    name: str,
    classification: PatternClassification,
    contributions: tuple[PatternAspectContribution, ...],
    all_contributions: tuple[PatternAspectContribution, ...],
) -> PatternConditionProfile:
    """Build the integrated per-pattern condition profile."""

    structured_count = sum(
        contribution.role is not PatternAspectRoleKind.MEMBER_LINK
        for contribution in all_contributions
    )
    return PatternConditionProfile(
        pattern_name=name,
        detector=classification.detector,
        source_kind=classification.source_kind,
        symmetry=classification.symmetry,
        body_count=classification.body_count,
        has_apex=classification.has_apex,
        contribution_count=len(contributions),
        all_contribution_count=len(all_contributions),
        structured_contribution_count=structured_count,
        generic_contribution_count=len(all_contributions) - structured_count,
        state=_derive_pattern_condition_state(all_contributions=all_contributions),
    )


def _pattern_profile_rank(
    profile: PatternConditionProfile,
) -> tuple[int, int, int, str, str]:
    """Return a deterministic structural ranking key for one pattern profile."""

    state_rank = {
        PatternConditionState.REINFORCED: 2,
        PatternConditionState.MIXED: 1,
        PatternConditionState.WEAKENED: 0,
    }[profile.state]
    return (
        state_rank,
        profile.structured_contribution_count,
        profile.body_count,
        profile.pattern_name,
        profile.detector,
    )


def _pattern_node_id(pattern_name: str) -> str:
    """Return the stable node id for a pattern node."""

    return f"pattern:{pattern_name}"


def _body_node_id(body: str) -> str:
    """Return the stable node id for a body node."""

    return f"body:{body}"


def _build_body_roles(
    bodies: tuple[str, ...],
    *,
    apex: str | None = None,
    role_overrides: dict[str, str] | None = None,
) -> tuple[PatternBodyRoleTruth, ...]:
    """Build deterministic body-role truth for one detected pattern."""

    role_overrides = role_overrides or {}
    roles: list[PatternBodyRoleTruth] = []
    for body in bodies:
        if body in role_overrides:
            role = role_overrides[body]
        elif apex is not None and body == apex:
            role = "apex"
        else:
            role = "member"
        roles.append(PatternBodyRoleTruth(body=body, role=role))
    return tuple(roles)


def _make_pattern(
    *,
    name: str,
    bodies: tuple[str, ...],
    aspects: tuple[AspectData, ...],
    detector: str,
    orb_factor: float,
    apex: str | None = None,
    source_kind: str = "aspect",
    role_overrides: dict[str, str] | None = None,
    centroid_longitude: float | None = None,
    max_body_distance: float | None = None,
    orb_limit: float | None = None,
) -> AspectPattern:
    """Construct an AspectPattern with preserved detector-path truth."""

    detection_truth = PatternDetectionTruth(
        pattern_name=name,
        detector=detector,
        source_kind=source_kind,
        orb_factor=orb_factor,
        body_roles=_build_body_roles(bodies, apex=apex, role_overrides=role_overrides),
        centroid_longitude=centroid_longitude,
        max_body_distance=max_body_distance,
        orb_limit=orb_limit,
    )
    classification = _classify_pattern_truth(name=name, bodies=bodies, apex=apex, detection_truth=detection_truth)
    contributions = _build_pattern_contributions(name=name, aspects=aspects, classification=classification)
    condition_profile = _build_pattern_condition_profile(
        name=name,
        classification=classification,
        contributions=contributions,
        all_contributions=contributions,
    )
    return AspectPattern(
        name=name,
        bodies=bodies,
        aspects=aspects,
        apex=apex,
        detection_truth=detection_truth,
        classification=classification,
        all_contributions=contributions,
        contributions=contributions,
        condition_profile=condition_profile,
    )


def _classify_pattern_truth(
    *,
    name: str,
    bodies: tuple[str, ...],
    apex: str | None,
    detection_truth: PatternDetectionTruth,
) -> PatternClassification:
    """Classify preserved pattern truth without changing its meaning."""

    return PatternClassification(
        pattern_name=name,
        detector=detection_truth.detector,
        source_kind=PatternSourceKind(detection_truth.source_kind),
        symmetry=(
            PatternSymmetryKind.APEX_BEARING
            if apex is not None
            else PatternSymmetryKind.SYMMETRIC
        ),
        body_count=len(bodies),
        has_apex=apex is not None,
        body_roles=tuple(
            PatternBodyRoleClassification(body=role.body, role=PatternBodyRoleKind(role.role))
            for role in detection_truth.body_roles
        ),
    )


def _classify_contribution_role(
    aspect: AspectData,
    *,
    classification: PatternClassification,
) -> PatternAspectRoleKind:
    """Classify one contributing aspect from already-preserved body-role truth."""

    roles_by_body = {role.body: role.role for role in classification.body_roles}
    endpoint_roles = {roles_by_body[aspect.body1], roles_by_body[aspect.body2]}
    if PatternBodyRoleKind.APEX in endpoint_roles:
        return PatternAspectRoleKind.APEX_LINK
    if endpoint_roles == {PatternBodyRoleKind.BASE}:
        return PatternAspectRoleKind.BASE_LINK
    if endpoint_roles == {PatternBodyRoleKind.AXIS}:
        return PatternAspectRoleKind.AXIS_LINK
    if endpoint_roles & {PatternBodyRoleKind.SUPPORT, PatternBodyRoleKind.TAIL, PatternBodyRoleKind.BOOMERANG}:
        return PatternAspectRoleKind.SUPPORT_LINK
    return PatternAspectRoleKind.MEMBER_LINK


def _build_pattern_contributions(
    *,
    name: str,
    aspects: tuple[AspectData, ...],
    classification: PatternClassification,
) -> tuple[PatternAspectContribution, ...]:
    """Build the formal contributing aspect relations for one detected pattern."""

    return tuple(
        PatternAspectContribution(
            pattern_name=name,
            role=_classify_contribution_role(aspect, classification=classification),
            body1=aspect.body1,
            body2=aspect.body2,
            aspect_name=aspect.aspect,
            aspect_angle=aspect.angle,
            aspect=aspect,
        )
        for aspect in aspects
    )


# ---------------------------------------------------------------------------
# Pattern detectors — classical
# ---------------------------------------------------------------------------

def find_t_squares(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    T-Square: body_A opposition body_B, both square body_C (apex).

    Orbs: opposition 8° * orb_factor, square 7° * orb_factor.
    """
    opp_orb = 8.0 * orb_factor
    sq_orb  = 7.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c in combinations(bodies, 3):
        for apex, p1, p2 in [(c, a, b), (a, b, c), (b, a, c)]:
            opp_asp = _get_aspect(aspect_map, p1, p2, 180.0, opp_orb)
            sq1_asp = _get_aspect(aspect_map, p1, apex, 90.0, sq_orb)
            sq2_asp = _get_aspect(aspect_map, p2, apex, 90.0, sq_orb)
            if opp_asp and sq1_asp and sq2_asp:
                results.append(_make_pattern(
                    name="T-Square",
                    bodies=(*sorted([p1, p2]), apex),
                    aspects=(opp_asp, sq1_asp, sq2_asp),
                    apex=apex,
                    detector="find_t_squares",
                    orb_factor=orb_factor,
                    role_overrides={p1: "base", p2: "base"},
                ))
                break

    return _dedup_patterns(results)


def find_grand_trines(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Grand Trine: three bodies all trine (120°) each other.

    Orb: 7° * orb_factor.
    """
    trine_orb = 7.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c in combinations(bodies, 3):
        t_ab = _get_aspect(aspect_map, a, b, 120.0, trine_orb)
        t_bc = _get_aspect(aspect_map, b, c, 120.0, trine_orb)
        t_ac = _get_aspect(aspect_map, a, c, 120.0, trine_orb)
        if t_ab and t_bc and t_ac:
            results.append(_make_pattern(
                name="Grand Trine",
                bodies=tuple(sorted([a, b, c])),
                aspects=(t_ab, t_bc, t_ac),
                detector="find_grand_trines",
                orb_factor=orb_factor,
            ))

    return _dedup_patterns(results)


def find_grand_crosses(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Grand Cross: two oppositions and four squares forming a closed cross.

    Orbs: opposition 8° * orb_factor, square 7° * orb_factor.
    """
    opp_orb = 8.0 * orb_factor
    sq_orb  = 7.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c, d in combinations(bodies, 4):
        pairs = [((a, b), (c, d)), ((a, c), (b, d)), ((a, d), (b, c))]
        for (p, q), (r, s) in pairs:
            opp1 = _get_aspect(aspect_map, p, q, 180.0, opp_orb)
            opp2 = _get_aspect(aspect_map, r, s, 180.0, opp_orb)
            if not (opp1 and opp2):
                continue
            sq_pr = _get_aspect(aspect_map, p, r, 90.0, sq_orb)
            sq_rq = _get_aspect(aspect_map, r, q, 90.0, sq_orb)
            sq_qs = _get_aspect(aspect_map, q, s, 90.0, sq_orb)
            sq_sp = _get_aspect(aspect_map, s, p, 90.0, sq_orb)
            if sq_pr and sq_rq and sq_qs and sq_sp:
                results.append(_make_pattern(
                    name="Grand Cross",
                    bodies=tuple(sorted([a, b, c, d])),
                    aspects=(opp1, opp2, sq_pr, sq_rq, sq_qs, sq_sp),
                    detector="find_grand_crosses",
                    orb_factor=orb_factor,
                ))
                break

    return _dedup_patterns(results)


def find_yods(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Yod (Finger of God): A sextile B, both quincunx (150°) C (apex).

    Orbs: sextile 3° * orb_factor, quincunx 3° * orb_factor.
    """
    sext_orb = 3.0 * orb_factor
    qncx_orb = 3.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c in combinations(bodies, 3):
        for apex, p1, p2 in [(c, a, b), (a, b, c), (b, a, c)]:
            sext = _get_aspect(aspect_map, p1, p2, 60.0, sext_orb)
            q1   = _get_aspect(aspect_map, p1, apex, 150.0, qncx_orb)
            q2   = _get_aspect(aspect_map, p2, apex, 150.0, qncx_orb)
            if sext and q1 and q2:
                results.append(_make_pattern(
                    name="Yod",
                    bodies=(*sorted([p1, p2]), apex),
                    aspects=(sext, q1, q2),
                    apex=apex,
                    detector="find_yods",
                    orb_factor=orb_factor,
                    role_overrides={p1: "base", p2: "base"},
                ))
                break

    return _dedup_patterns(results)


def find_mystic_rectangles(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Mystic Rectangle: two trines + two sextiles + two oppositions.
    Adjacent sides alternate trine/sextile; diagonals are oppositions.

    Orbs: trine 7°, sextile 5°, opposition 8° — all * orb_factor.
    """
    trine_orb = 7.0 * orb_factor
    sext_orb  = 5.0 * orb_factor
    opp_orb   = 8.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c, d in combinations(bodies, 4):
        for ordering in [(a, b, c, d), (a, b, d, c), (a, c, b, d)]:
            p, q, r, s = ordering
            t_pq = _get_aspect(aspect_map, p, q, 120.0, trine_orb)
            t_rs = _get_aspect(aspect_map, r, s, 120.0, trine_orb)
            s_qr = _get_aspect(aspect_map, q, r,  60.0, sext_orb)
            s_sp = _get_aspect(aspect_map, s, p,  60.0, sext_orb)
            o_pr = _get_aspect(aspect_map, p, r, 180.0, opp_orb)
            o_qs = _get_aspect(aspect_map, q, s, 180.0, opp_orb)
            if t_pq and t_rs and s_qr and s_sp and o_pr and o_qs:
                results.append(_make_pattern(
                    name="Mystic Rectangle",
                    bodies=tuple(sorted([a, b, c, d])),
                    aspects=(t_pq, t_rs, s_qr, s_sp, o_pr, o_qs),
                    detector="find_mystic_rectangles",
                    orb_factor=orb_factor,
                ))
                break

    return _dedup_patterns(results)


def find_kites(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Kite: Grand Trine (A, B, C) with a fourth planet D opposing one vertex
    (apex) and sextile the other two.

    Orbs: trine 7°, sextile 5°, opposition 8° — all * orb_factor.
    """
    trine_orb = 7.0 * orb_factor
    sext_orb  = 5.0 * orb_factor
    opp_orb   = 8.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c, d in combinations(bodies, 4):
        for tail, x, y, apex in [
            (d, a, b, c), (d, a, c, b), (d, b, c, a),
            (c, a, b, d), (c, a, d, b), (c, b, d, a),
            (b, a, c, d), (b, a, d, c), (b, c, d, a),
            (a, b, c, d), (a, b, d, c), (a, c, d, b),
        ]:
            t_xy    = _get_aspect(aspect_map, x,    y,    120.0, trine_orb)
            t_xa    = _get_aspect(aspect_map, x,    apex, 120.0, trine_orb)
            t_ya    = _get_aspect(aspect_map, y,    apex, 120.0, trine_orb)
            opp     = _get_aspect(aspect_map, tail, apex, 180.0, opp_orb)
            sext_tx = _get_aspect(aspect_map, tail, x,    60.0,  sext_orb)
            sext_ty = _get_aspect(aspect_map, tail, y,    60.0,  sext_orb)
            if t_xy and t_xa and t_ya and opp and sext_tx and sext_ty:
                results.append(_make_pattern(
                    name="Kite",
                    bodies=tuple(sorted([a, b, c, d])),
                    aspects=(t_xy, t_xa, t_ya, opp, sext_tx, sext_ty),
                    apex=apex,
                    detector="find_kites",
                    orb_factor=orb_factor,
                    role_overrides={tail: "tail", x: "support", y: "support"},
                ))
                break

    return _dedup_patterns(results)


def find_stelliums(
    positions: dict[str, float],
    min_bodies: int = 3,
    orb: float = 8.0,
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Stellium: 3+ bodies within ``orb * orb_factor`` degrees of the group
    circular centroid.  Only maximal groups are returned (no sub-group of
    a reported Stellium is reported separately).

    Parameters
    ----------
    positions  : dict of body name -> tropical longitude
    min_bodies : minimum number of bodies required (default 3)
    orb        : base spread in degrees (default 8.0)
    orb_factor : multiplier applied to orb (default 1.0)
    """
    positions = _validate_positions(positions)
    if min_bodies < 3:
        raise ValueError("Pattern stellium min_bodies must be at least 3")
    if orb < 0:
        raise ValueError("Pattern stellium orb must be non-negative")
    if orb_factor <= 0:
        raise ValueError("Pattern orb_factor must be positive")
    effective_orb = orb * orb_factor
    body_list = sorted(positions.keys())
    results: list[AspectPattern] = []

    for size in range(min_bodies, len(body_list) + 1):
        for group in combinations(body_list, size):
            lons = [positions[b] for b in group]
            sin_sum = sum(math.sin(math.radians(lon)) for lon in lons)
            cos_sum = sum(math.cos(math.radians(lon)) for lon in lons)
            centroid = math.degrees(math.atan2(sin_sum, cos_sum)) % 360.0
            if all(angular_distance(lon, centroid) <= effective_orb for lon in lons):
                max_body_distance = max(angular_distance(lon, centroid) for lon in lons)
                results.append(_make_pattern(
                    name="Stellium",
                    bodies=tuple(sorted(group)),
                    aspects=(),
                    detector="find_stelliums",
                    orb_factor=orb_factor,
                    source_kind="position",
                    role_overrides={body: "cluster_member" for body in group},
                    centroid_longitude=centroid,
                    max_body_distance=max_body_distance,
                    orb_limit=effective_orb,
                ))

    unique = _dedup_patterns(results)
    body_sets = [frozenset(p.bodies) for p in unique]
    return [
        p for i, p in enumerate(unique)
        if not any(body_sets[i] < other for other in body_sets)
    ]


def find_minor_grand_trines(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Minor Grand Trine: A trine B, both sextile C.

    Orbs: trine 7° * orb_factor, sextile 3° * orb_factor.
    """
    trine_orb = 7.0 * orb_factor
    sext_orb  = 3.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c in combinations(bodies, 3):
        for apex, p1, p2 in [(c, a, b), (a, b, c), (b, a, c)]:
            trine = _get_aspect(aspect_map, p1, p2,   120.0, trine_orb)
            sext1 = _get_aspect(aspect_map, p1, apex,  60.0, sext_orb)
            sext2 = _get_aspect(aspect_map, p2, apex,  60.0, sext_orb)
            if trine and sext1 and sext2:
                results.append(_make_pattern(
                    name="Minor Grand Trine",
                    bodies=tuple(sorted([p1, p2, apex])),
                    aspects=(trine, sext1, sext2),
                    detector="find_minor_grand_trines",
                    orb_factor=orb_factor,
                ))
                break

    return _dedup_patterns(results)


def find_grand_sextiles(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Grand Sextile (Star of David): six planets all in mutual sextile (60°),
    forming two interlocking Grand Trines.

    Orb: 3° * orb_factor.
    """
    sext_orb = 3.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for group in combinations(bodies, 6):
        group_aspects: list[AspectData] = []
        valid = True
        for b1, b2 in combinations(group, 2):
            asp = _get_aspect(aspect_map, b1, b2, 60.0, sext_orb)
            if asp is None:
                valid = False
                break
            group_aspects.append(asp)
        if valid:
            results.append(_make_pattern(
                name="Grand Sextile",
                bodies=tuple(sorted(group)),
                aspects=tuple(group_aspects),
                detector="find_grand_sextiles",
                orb_factor=orb_factor,
            ))

    return _dedup_patterns(results)


def find_thors_hammers(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Thor's Hammer (God's Fist): two planets in square (90°), both
    sesquiquadrate (135°) an apex planet.

    Orbs: square 5° * orb_factor, sesquiquadrate 2° * orb_factor.
    """
    sq_orb   = 5.0 * orb_factor
    sesq_orb = 2.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c in combinations(bodies, 3):
        for apex, p1, p2 in [(c, a, b), (a, b, c), (b, a, c)]:
            sq = _get_aspect(aspect_map, p1, p2,    90.0, sq_orb)
            s1 = _get_aspect(aspect_map, p1, apex, 135.0, sesq_orb)
            s2 = _get_aspect(aspect_map, p2, apex, 135.0, sesq_orb)
            if sq and s1 and s2:
                results.append(_make_pattern(
                    name="Thor's Hammer",
                    bodies=(*sorted([p1, p2]), apex),
                    aspects=(sq, s1, s2),
                    apex=apex,
                    detector="find_thors_hammers",
                    orb_factor=orb_factor,
                    role_overrides={p1: "base", p2: "base"},
                ))
                break

    return _dedup_patterns(results)


def find_boomerang_yods(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Boomerang Yod: standard Yod (A sextile B, both quincunx C apex) plus a
    fourth planet D opposing the apex C.

    Orbs: sextile 3°, quincunx 3°, opposition 5° — all * orb_factor.
    """
    sext_orb = 3.0 * orb_factor
    qncx_orb = 3.0 * orb_factor
    opp_orb  = 5.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c, d in combinations(bodies, 4):
        for apex, p1, p2, boom in [
            (c, a, b, d), (d, a, b, c),
            (b, a, c, d), (d, a, c, b),
            (a, b, c, d), (d, b, c, a),
        ]:
            sext = _get_aspect(aspect_map, p1,   p2,    60.0, sext_orb)
            q1   = _get_aspect(aspect_map, p1,   apex, 150.0, qncx_orb)
            q2   = _get_aspect(aspect_map, p2,   apex, 150.0, qncx_orb)
            opp  = _get_aspect(aspect_map, boom, apex, 180.0, opp_orb)
            if sext and q1 and q2 and opp:
                results.append(_make_pattern(
                    name="Boomerang Yod",
                    bodies=tuple(sorted([p1, p2, apex, boom])),
                    aspects=(sext, q1, q2, opp),
                    apex=apex,
                    detector="find_boomerang_yods",
                    orb_factor=orb_factor,
                    role_overrides={p1: "base", p2: "base", boom: "boomerang"},
                ))
                break

    return _dedup_patterns(results)


def find_wedges(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Wedge (Arrowhead): planet A opposing planet B; a third planet C trine
    one and sextile the other.

    Orbs: opposition 8°, trine/sextile 5° — all * orb_factor.
    """
    opp_orb  = 8.0 * orb_factor
    trsx_orb = 5.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c in combinations(bodies, 3):
        for p1, p2, apex in [(a, b, c), (a, c, b), (b, c, a)]:
            opp = _get_aspect(aspect_map, p1,   p2,   180.0, opp_orb)
            tr  = _get_aspect(aspect_map, apex, p1,   120.0, trsx_orb)
            sx  = _get_aspect(aspect_map, apex, p2,    60.0, trsx_orb)
            if opp and tr and sx:
                results.append(_make_pattern(
                    name="Wedge",
                    bodies=(*sorted([p1, p2]), apex),
                    aspects=(opp, tr, sx),
                    apex=apex,
                    detector="find_wedges",
                    orb_factor=orb_factor,
                    role_overrides={p1: "axis", p2: "axis"},
                ))
                break

    return _dedup_patterns(results)


# ---------------------------------------------------------------------------
# Pattern detectors — extended classical / Huber-recognized
# ---------------------------------------------------------------------------

def find_cradles(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Cradle: two Minor Grand Trines sharing a common opposition as their base.
    Structure: A opp D, A trine B, B sext C, C trine D, A sext C, B sext D.
    Equivalently: four planets in sequence A-B-C-D where A opp D, the two
    outer planets each trine their adjacent inner planet, and the two inner
    planets sextile the opposite outer planet.

    Orbs: opposition 8°, trine 7°, sextile 5° — all * orb_factor.
    """
    opp_orb   = 8.0 * orb_factor
    trine_orb = 7.0 * orb_factor
    sext_orb  = 5.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c, d in combinations(bodies, 4):
        for p, q, r, s in [
            (a, b, c, d), (a, b, d, c), (a, c, b, d),
            (a, c, d, b), (a, d, b, c), (a, d, c, b),
        ]:
            opp   = _get_aspect(aspect_map, p, s,   180.0, opp_orb)
            tr_pq = _get_aspect(aspect_map, p, q,   120.0, trine_orb)
            tr_rs = _get_aspect(aspect_map, r, s,   120.0, trine_orb)
            sx_qr = _get_aspect(aspect_map, q, r,    60.0, sext_orb)
            sx_pr = _get_aspect(aspect_map, p, r,    60.0, sext_orb)
            sx_qs = _get_aspect(aspect_map, q, s,    60.0, sext_orb)
            if opp and tr_pq and tr_rs and sx_qr and sx_pr and sx_qs:
                results.append(_make_pattern(
                    name="Cradle",
                    bodies=tuple(sorted([a, b, c, d])),
                    aspects=(opp, tr_pq, tr_rs, sx_qr, sx_pr, sx_qs),
                    detector="find_cradles",
                    orb_factor=orb_factor,
                ))
                break

    return _dedup_patterns(results)


def find_trapezes(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Trapeze (Trapezoid): four planets in sequence where the two end planets
    are in opposition and the four outer edges are sextiles, with one
    diagonal also a sextile.
    Structure: A sext B sext C sext D, A opp C or B opp D (one diagonal
    opposition), and A sext D closing the shape.

    Orbs: opposition 8°, sextile 5° — all * orb_factor.
    """
    opp_orb  = 8.0 * orb_factor
    sext_orb = 5.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c, d in combinations(bodies, 4):
        for p, q, r, s in [
            (a, b, c, d), (a, b, d, c), (a, c, b, d),
            (a, c, d, b), (a, d, b, c), (a, d, c, b),
        ]:
            sx_pq = _get_aspect(aspect_map, p, q,  60.0, sext_orb)
            sx_qr = _get_aspect(aspect_map, q, r,  60.0, sext_orb)
            sx_rs = _get_aspect(aspect_map, r, s,  60.0, sext_orb)
            opp   = _get_aspect(aspect_map, p, s, 180.0, opp_orb)
            if sx_pq and sx_qr and sx_rs and opp:
                results.append(_make_pattern(
                    name="Trapeze",
                    bodies=tuple(sorted([a, b, c, d])),
                    aspects=(sx_pq, sx_qr, sx_rs, opp),
                    detector="find_trapezes",
                    orb_factor=orb_factor,
                ))
                break

    return _dedup_patterns(results)


def find_eyes(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Eye (Cosmic Eye): two quincunxes (150°) meeting at an apex, with the
    base planets in trine (120°).  The soft analog of the Yod.

    Orbs: quincunx 3°, trine 7° — all * orb_factor.
    """
    qncx_orb  = 3.0 * orb_factor
    trine_orb = 7.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c in combinations(bodies, 3):
        for apex, p1, p2 in [(c, a, b), (a, b, c), (b, a, c)]:
            q1    = _get_aspect(aspect_map, p1, apex, 150.0, qncx_orb)
            q2    = _get_aspect(aspect_map, p2, apex, 150.0, qncx_orb)
            trine = _get_aspect(aspect_map, p1, p2,  120.0, trine_orb)
            if q1 and q2 and trine:
                results.append(_make_pattern(
                    name="Eye",
                    bodies=(*sorted([p1, p2]), apex),
                    aspects=(q1, q2, trine),
                    apex=apex,
                    detector="find_eyes",
                    orb_factor=orb_factor,
                    role_overrides={p1: "base", p2: "base"},
                ))
                break

    return _dedup_patterns(results)


def find_irritation_triangles(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Irritation Triangle (Ambivalence Triangle): one opposition with both
    planets quincunx (150°) a third.  The all-tension analog of the Eye.

    Orbs: opposition 8°, quincunx 3° — all * orb_factor.
    """
    opp_orb  = 8.0 * orb_factor
    qncx_orb = 3.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c in combinations(bodies, 3):
        for apex, p1, p2 in [(c, a, b), (a, b, c), (b, a, c)]:
            opp = _get_aspect(aspect_map, p1, p2,   180.0, opp_orb)
            q1  = _get_aspect(aspect_map, p1, apex, 150.0, qncx_orb)
            q2  = _get_aspect(aspect_map, p2, apex, 150.0, qncx_orb)
            if opp and q1 and q2:
                results.append(_make_pattern(
                    name="Irritation Triangle",
                    bodies=(*sorted([p1, p2]), apex),
                    aspects=(opp, q1, q2),
                    apex=apex,
                    detector="find_irritation_triangles",
                    orb_factor=orb_factor,
                    role_overrides={p1: "base", p2: "base"},
                ))
                break

    return _dedup_patterns(results)


def find_hard_wedges(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Hard Wedge: planet A opposing planet B; a third planet C is semisquare
    (45°) one and sesquiquadrate (135°) the other.  The tense analog of the
    Wedge using 8th-harmonic aspects.

    Orbs: opposition 8°, semisquare 2°, sesquiquadrate 2° — all * orb_factor.
    """
    opp_orb  = 8.0 * orb_factor
    semi_orb = 2.0 * orb_factor
    sesq_orb = 2.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c in combinations(bodies, 3):
        for p1, p2, apex in [(a, b, c), (a, c, b), (b, c, a)]:
            opp  = _get_aspect(aspect_map, p1,   p2,    180.0, opp_orb)
            semi = _get_aspect(aspect_map, apex, p1,     45.0, semi_orb)
            sesq = _get_aspect(aspect_map, apex, p2,    135.0, sesq_orb)
            if opp and semi and sesq:
                results.append(_make_pattern(
                    name="Hard Wedge",
                    bodies=(*sorted([p1, p2]), apex),
                    aspects=(opp, semi, sesq),
                    apex=apex,
                    detector="find_hard_wedges",
                    orb_factor=orb_factor,
                    role_overrides={p1: "axis", p2: "axis"},
                ))
                break

    return _dedup_patterns(results)


def find_dominant_triangles(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Dominant Triangle (Huber): one opposition + one square + one quincunx
    (150°), forming a mixed-tension three-planet figure.

    Orbs: opposition 8°, square 7°, quincunx 3° — all * orb_factor.
    """
    opp_orb  = 8.0 * orb_factor
    sq_orb   = 7.0 * orb_factor
    qncx_orb = 3.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c in combinations(bodies, 3):
        for p1, p2, p3 in [(a, b, c), (a, c, b), (b, c, a)]:
            opp  = _get_aspect(aspect_map, p1, p2,  180.0, opp_orb)
            sq   = _get_aspect(aspect_map, p1, p3,   90.0, sq_orb)
            qncx = _get_aspect(aspect_map, p2, p3,  150.0, qncx_orb)
            if opp and sq and qncx:
                results.append(_make_pattern(
                    name="Dominant Triangle",
                    bodies=tuple(sorted([a, b, c])),
                    aspects=(opp, sq, qncx),
                    detector="find_dominant_triangles",
                    orb_factor=orb_factor,
                ))
                break

    return _dedup_patterns(results)


# ---------------------------------------------------------------------------
# Pattern detectors — harmonic (5th and 7th harmonic)
# ---------------------------------------------------------------------------

def find_grand_quintiles(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Grand Quintile: five planets all in mutual quintile (72°), forming a
    regular pentagon.  A pure 5th-harmonic figure.

    Orb: 2° * orb_factor.
    """
    q_orb = 2.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for group in combinations(bodies, 5):
        group_aspects: list[AspectData] = []
        valid = True
        for b1, b2 in combinations(group, 2):
            asp = _get_aspect(aspect_map, b1, b2, 72.0, q_orb)
            if asp is None:
                valid = False
                break
            group_aspects.append(asp)
        if valid:
            results.append(_make_pattern(
                name="Grand Quintile",
                bodies=tuple(sorted(group)),
                aspects=tuple(group_aspects),
                detector="find_grand_quintiles",
                orb_factor=orb_factor,
            ))

    return _dedup_patterns(results)


def find_quintile_triangles(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Quintile Triangle: A quintile (72°) B, both biquintile (144°) C (apex).
    The 5th-harmonic analog of the Yod.

    Orbs: quintile 2°, biquintile 2° — all * orb_factor.
    """
    q_orb  = 2.0 * orb_factor
    bq_orb = 2.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c in combinations(bodies, 3):
        for apex, p1, p2 in [(c, a, b), (a, b, c), (b, a, c)]:
            q   = _get_aspect(aspect_map, p1, p2,    72.0, q_orb)
            bq1 = _get_aspect(aspect_map, p1, apex, 144.0, bq_orb)
            bq2 = _get_aspect(aspect_map, p2, apex, 144.0, bq_orb)
            if q and bq1 and bq2:
                results.append(_make_pattern(
                    name="Quintile Triangle",
                    bodies=(*sorted([p1, p2]), apex),
                    aspects=(q, bq1, bq2),
                    apex=apex,
                    detector="find_quintile_triangles",
                    orb_factor=orb_factor,
                    role_overrides={p1: "base", p2: "base"},
                ))
                break

    return _dedup_patterns(results)


def find_septile_triangles(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Septile Triangle: three planets connected by one each of septile (51.43°),
    biseptile (102.86°), and triseptile (154.29°).  A closed 7th-harmonic
    triangle.

    Orb: 1.5° * orb_factor for all three aspects.
    """
    s_orb = 1.5 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    sept  = 360.0 / 7          # 51.428...
    bisept  = 2 * 360.0 / 7    # 102.857...
    trisept = 3 * 360.0 / 7    # 154.285...

    for a, b, c in combinations(bodies, 3):
        for p1, p2, p3 in [(a, b, c), (a, c, b), (b, c, a)]:
            s1 = _get_aspect(aspect_map, p1, p2, sept,   s_orb)
            s2 = _get_aspect(aspect_map, p2, p3, bisept, s_orb)
            s3 = _get_aspect(aspect_map, p1, p3, trisept, s_orb)
            if s1 and s2 and s3:
                results.append(_make_pattern(
                    name="Septile Triangle",
                    bodies=tuple(sorted([a, b, c])),
                    aspects=(s1, s2, s3),
                    detector="find_septile_triangles",
                    orb_factor=orb_factor,
                ))
                break

    return _dedup_patterns(results)


# ---------------------------------------------------------------------------
# Pattern registry and master function
# ---------------------------------------------------------------------------

_PATTERN_REGISTRY: dict[str, str] = {
    "T-Square":             "find_t_squares",
    "Grand Trine":          "find_grand_trines",
    "Grand Cross":          "find_grand_crosses",
    "Yod":                  "find_yods",
    "Mystic Rectangle":     "find_mystic_rectangles",
    "Kite":                 "find_kites",
    "Stellium":             "find_stelliums",
    "Minor Grand Trine":    "find_minor_grand_trines",
    "Grand Sextile":        "find_grand_sextiles",
    "Thor's Hammer":        "find_thors_hammers",
    "Boomerang Yod":        "find_boomerang_yods",
    "Wedge":                "find_wedges",
    "Cradle":               "find_cradles",
    "Trapeze":              "find_trapezes",
    "Eye":                  "find_eyes",
    "Irritation Triangle":  "find_irritation_triangles",
    "Hard Wedge":           "find_hard_wedges",
    "Dominant Triangle":    "find_dominant_triangles",
    "Grand Quintile":       "find_grand_quintiles",
    "Quintile Triangle":    "find_quintile_triangles",
    "Septile Triangle":     "find_septile_triangles",
}


def find_all_patterns(
    positions: dict[str, float],
    aspects: list[AspectData] | None = None,
    orb_factor: float = 1.0,
    include: list[str] | None = None,
    policy: PatternComputationPolicy | None = None,
) -> list[AspectPattern]:
    """
    Detect all aspect patterns in a chart.

    Parameters
    ----------
    positions   : dict of body name -> longitude
    aspects     : pre-computed aspects (computed via find_aspects if None)
    orb_factor  : multiplier applied to all orbs
    include     : list of pattern names to detect (all patterns if None).
                  Valid names: see _PATTERN_REGISTRY keys.
    policy      : optional explicit backend policy. When supplied it takes
                  precedence over `orb_factor` and `include`.

    Returns
    -------
    list[AspectPattern] sorted by pattern name then body names.
    """
    policy = _validate_policy(policy)
    positions = _validate_positions(positions)
    if policy is not None:
        orb_factor = policy.orb_factor
        include = list(policy.selection.include) if policy.selection.include is not None else None

    if aspects is None:
        aspects = find_aspects(positions, orb_factor=orb_factor)
    else:
        aspects = _validate_aspects(aspects)

    wanted: set[str] = set(include) if include is not None else set(_PATTERN_REGISTRY)

    all_found: list[AspectPattern] = []

    if "T-Square" in wanted:
        all_found.extend(find_t_squares(aspects, orb_factor=orb_factor))
    if "Grand Trine" in wanted:
        all_found.extend(find_grand_trines(aspects, orb_factor=orb_factor))
    if "Grand Cross" in wanted:
        all_found.extend(find_grand_crosses(aspects, orb_factor=orb_factor))
    if "Yod" in wanted:
        all_found.extend(find_yods(aspects, orb_factor=orb_factor))
    if "Mystic Rectangle" in wanted:
        all_found.extend(find_mystic_rectangles(aspects, orb_factor=orb_factor))
    if "Kite" in wanted:
        all_found.extend(find_kites(aspects, orb_factor=orb_factor))
    if "Stellium" in wanted:
        all_found.extend(
            find_stelliums(
                positions,
                min_bodies=policy.stellium.min_bodies,
                orb=policy.stellium.orb,
                orb_factor=orb_factor,
            )
        )
    if "Minor Grand Trine" in wanted:
        all_found.extend(find_minor_grand_trines(aspects, orb_factor=orb_factor))
    if "Grand Sextile" in wanted:
        all_found.extend(find_grand_sextiles(aspects, orb_factor=orb_factor))
    if "Thor's Hammer" in wanted:
        all_found.extend(find_thors_hammers(aspects, orb_factor=orb_factor))
    if "Boomerang Yod" in wanted:
        all_found.extend(find_boomerang_yods(aspects, orb_factor=orb_factor))
    if "Wedge" in wanted:
        all_found.extend(find_wedges(aspects, orb_factor=orb_factor))
    if "Cradle" in wanted:
        all_found.extend(find_cradles(aspects, orb_factor=orb_factor))
    if "Trapeze" in wanted:
        all_found.extend(find_trapezes(aspects, orb_factor=orb_factor))
    if "Eye" in wanted:
        all_found.extend(find_eyes(aspects, orb_factor=orb_factor))
    if "Irritation Triangle" in wanted:
        all_found.extend(find_irritation_triangles(aspects, orb_factor=orb_factor))
    if "Hard Wedge" in wanted:
        all_found.extend(find_hard_wedges(aspects, orb_factor=orb_factor))
    if "Dominant Triangle" in wanted:
        all_found.extend(find_dominant_triangles(aspects, orb_factor=orb_factor))
    if "Grand Quintile" in wanted:
        all_found.extend(find_grand_quintiles(aspects, orb_factor=orb_factor))
    if "Quintile Triangle" in wanted:
        all_found.extend(find_quintile_triangles(aspects, orb_factor=orb_factor))
    if "Septile Triangle" in wanted:
        all_found.extend(find_septile_triangles(aspects, orb_factor=orb_factor))

    all_found.sort(key=lambda p: (p.name, p.bodies))
    return all_found


def pattern_contributions(patterns: list[AspectPattern]) -> list[PatternAspectContribution]:
    """Flatten formal contributing aspect relations from a pattern list."""

    contributions = [
        contribution
        for pattern in patterns
        for contribution in pattern.contributions
    ]
    contributions.sort(key=lambda contribution: (
        contribution.pattern_name,
        contribution.role.value,
        contribution.body1,
        contribution.body2,
        contribution.aspect_name,
    ))
    return contributions


def all_pattern_contributions(patterns: list[AspectPattern]) -> list[PatternAspectContribution]:
    """Flatten the full preserved contributing aspect relations from a pattern list."""

    contributions = [
        contribution
        for pattern in patterns
        for contribution in pattern.all_contributions
    ]
    contributions.sort(key=lambda contribution: (
        contribution.pattern_name,
        contribution.role.value,
        contribution.body1,
        contribution.body2,
        contribution.aspect_name,
    ))
    return contributions


def pattern_condition_profiles(patterns: list[AspectPattern]) -> list[PatternConditionProfile]:
    """Flatten integrated per-pattern condition profiles from a pattern list."""

    profiles = [
        pattern.condition_profile
        for pattern in patterns
        if pattern.condition_profile is not None
    ]
    profiles.sort(key=lambda profile: (profile.pattern_name, profile.detector, profile.body_count))
    return profiles


def pattern_chart_condition_profile(patterns: list[AspectPattern]) -> PatternChartConditionProfile:
    """Aggregate a chart-wide structural condition profile from detected patterns."""

    profiles = tuple(pattern_condition_profiles(patterns))
    reinforced = tuple(
        profile for profile in profiles
        if profile.state is PatternConditionState.REINFORCED
    )
    mixed = tuple(
        profile for profile in profiles
        if profile.state is PatternConditionState.MIXED
    )
    weakened = tuple(
        profile for profile in profiles
        if profile.state is PatternConditionState.WEAKENED
    )
    structured_total = sum(profile.structured_contribution_count for profile in profiles)
    generic_total = sum(profile.generic_contribution_count for profile in profiles)

    strongest_patterns: tuple[str, ...] = ()
    weakest_patterns: tuple[str, ...] = ()
    if profiles:
        strongest_rank = max(_pattern_profile_rank(profile) for profile in profiles)
        weakest_rank = min(_pattern_profile_rank(profile) for profile in profiles)
        strongest_patterns = tuple(sorted(
            profile.pattern_name
            for profile in profiles
            if _pattern_profile_rank(profile) == strongest_rank
        ))
        weakest_patterns = tuple(sorted(
            profile.pattern_name
            for profile in profiles
            if _pattern_profile_rank(profile) == weakest_rank
        ))

    return PatternChartConditionProfile(
        profiles=profiles,
        reinforced_count=len(reinforced),
        mixed_count=len(mixed),
        weakened_count=len(weakened),
        structured_contribution_total=structured_total,
        generic_contribution_total=generic_total,
        strongest_patterns=strongest_patterns,
        weakest_patterns=weakest_patterns,
    )


def pattern_condition_network_profile(patterns: list[AspectPattern]) -> PatternConditionNetworkProfile:
    """Project detected patterns into a deterministic body-pattern condition network."""

    ordered_patterns = sorted(patterns, key=lambda pattern: (pattern.name, pattern.bodies, pattern.apex or ""))
    edges: list[PatternConditionNetworkEdge] = []
    all_bodies: set[str] = set()

    for index, pattern in enumerate(ordered_patterns):
        pattern_node_id = f"{_pattern_node_id(pattern.name)}:{index}"
        role_map: dict[str, PatternBodyRoleKind] = {}
        if pattern.classification is not None:
            role_map = {role.body: role.role for role in pattern.classification.body_roles}
        for body in pattern.bodies:
            all_bodies.add(body)
            edges.append(
                PatternConditionNetworkEdge(
                    source_id=pattern_node_id,
                    target_id=_body_node_id(body),
                    pattern_name=pattern.name,
                    role=role_map.get(body, PatternBodyRoleKind.MEMBER),
                )
            )

    incoming_counts: dict[str, int] = {}
    outgoing_counts: dict[str, int] = {}
    for edge in edges:
        outgoing_counts[edge.source_id] = outgoing_counts.get(edge.source_id, 0) + 1
        incoming_counts[edge.target_id] = incoming_counts.get(edge.target_id, 0) + 1

    pattern_nodes = [
        PatternConditionNetworkNode(
            node_id=f"{_pattern_node_id(pattern.name)}:{index}",
            kind="pattern",
            label=pattern.name,
            incoming_count=incoming_counts.get(f"{_pattern_node_id(pattern.name)}:{index}", 0),
            outgoing_count=outgoing_counts.get(f"{_pattern_node_id(pattern.name)}:{index}", 0),
            total_degree=incoming_counts.get(f"{_pattern_node_id(pattern.name)}:{index}", 0) + outgoing_counts.get(f"{_pattern_node_id(pattern.name)}:{index}", 0),
        )
        for index, pattern in enumerate(ordered_patterns)
    ]
    body_nodes = [
        PatternConditionNetworkNode(
            node_id=_body_node_id(body),
            kind="body",
            label=body,
            incoming_count=incoming_counts.get(_body_node_id(body), 0),
            outgoing_count=outgoing_counts.get(_body_node_id(body), 0),
            total_degree=incoming_counts.get(_body_node_id(body), 0) + outgoing_counts.get(_body_node_id(body), 0),
        )
        for body in sorted(all_bodies)
    ]
    nodes = tuple(sorted(pattern_nodes + body_nodes, key=lambda node: (node.kind, node.label, node.node_id)))
    edges_tuple = tuple(sorted(
        edges,
        key=lambda edge: (edge.pattern_name, edge.source_id, edge.target_id, edge.role.value),
    ))
    isolated_bodies = tuple(sorted(
        node.label
        for node in body_nodes
        if node.total_degree == 0
    ))
    most_connected_nodes: tuple[str, ...] = ()
    if nodes:
        max_degree = max(node.total_degree for node in nodes)
        most_connected_nodes = tuple(sorted(
            node.label
            for node in nodes
            if node.total_degree == max_degree and max_degree > 0
        ))

    return PatternConditionNetworkProfile(
        nodes=nodes,
        edges=edges_tuple,
        isolated_bodies=isolated_bodies,
        most_connected_nodes=most_connected_nodes,
    )


def _validate_policy(policy: PatternComputationPolicy | None) -> PatternComputationPolicy:
    """Return a valid pattern policy or raise clearly on unsupported values."""

    if policy is None:
        policy = PatternComputationPolicy()
    if not isinstance(policy.selection, PatternSelectionPolicy):
        raise ValueError("Unsupported pattern selection policy")
    if not isinstance(policy.stellium, StelliumPolicy):
        raise ValueError("Unsupported stellium policy")
    if policy.orb_factor <= 0:
        raise ValueError("Pattern orb_factor must be positive")
    if policy.stellium.min_bodies < 3:
        raise ValueError("Pattern stellium min_bodies must be at least 3")
    if policy.stellium.orb < 0:
        raise ValueError("Pattern stellium orb must be non-negative")
    if policy.selection.include is not None and not isinstance(policy.selection.include, tuple):
        raise ValueError("Pattern selection include must be a tuple or None")
    if policy.selection.include is not None:
        if len(set(policy.selection.include)) != len(policy.selection.include):
            raise ValueError("Pattern selection include must not repeat names")
        unknown = [name for name in policy.selection.include if name not in _PATTERN_REGISTRY]
        if unknown:
            raise ValueError("Unsupported pattern names in selection include")
    return policy
