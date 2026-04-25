"""
Moira -- egyptian_bounds.py
Standalone Egyptian-bounds doctrine subsystem.

Boundary
--------
Owns the Egyptian bound table, bound lookup, and small typed classifications
derived directly from that table. This module is intentionally table-first:
it preserves the doctrinal truth of the bounds before any higher interpretive
layer consumes it.

Doctrinal notes
---------------
- Uses the traditional Egyptian bounds/terms in the tropical zodiac.
- Bound rulers are the five non-luminaries only: Mercury, Venus, Mars,
  Jupiter, and Saturn.
- A planet in its own bound receives minor essential dignity under the
  traditional scoring model used elsewhere in Moira.
"""

from dataclasses import dataclass
from enum import StrEnum

from .constants import SIGNS

__all__ = [
    "BOUND_RULERS",
    "BoundHostNature",
    "EgyptianBoundsDoctrine",
    "EgyptianBoundsPolicy",
    "EgyptianBoundRelationKind",
    "EgyptianBoundConditionState",
    "EgyptianBoundNetworkMode",
    "EgyptianBoundSegment",
    "EgyptianBoundTruth",
    "EgyptianBoundClassification",
    "EgyptianBoundRelation",
    "EgyptianBoundRelationProfile",
    "EgyptianBoundConditionProfile",
    "EgyptianBoundsAggregateProfile",
    "EgyptianBoundsNetworkNode",
    "EgyptianBoundsNetworkEdge",
    "EgyptianBoundsNetworkProfile",
    "EGYPTIAN_BOUNDS",
    "PTOLEMAIC_BOUNDS",
    "CHALDEAN_BOUNDS",
    "egyptian_bound_of",
    "bound_ruler",
    "classify_egyptian_bound",
    "is_in_own_egyptian_bound",
    "relate_planet_to_egyptian_bound",
    "evaluate_egyptian_bound_relations",
    "evaluate_egyptian_bound_condition",
    "evaluate_egyptian_bounds_aggregate",
    "evaluate_egyptian_bounds_network",
]


BOUND_RULERS: frozenset[str] = frozenset({"Mercury", "Venus", "Mars", "Jupiter", "Saturn"})
_BENEFICS: frozenset[str] = frozenset({"Venus", "Jupiter"})
_MALEFICS: frozenset[str] = frozenset({"Mars", "Saturn"})
_DIURNAL: frozenset[str] = frozenset({"Sun", "Jupiter", "Saturn"})
_NOCTURNAL: frozenset[str] = frozenset({"Moon", "Venus", "Mars"})
_PLANET_ORDER: tuple[str, ...] = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")


class BoundHostNature(StrEnum):
    BENEFIC = "benefic"
    MALEFIC = "malefic"
    NEUTRAL = "neutral"


class EgyptianBoundRelationKind(StrEnum):
    SELF_HOSTED = "self_hosted"
    HOSTED_BY_BENEFIC = "hosted_by_benefic"
    HOSTED_BY_MALEFIC = "hosted_by_malefic"
    HOSTED_BY_NEUTRAL = "hosted_by_neutral"


class EgyptianBoundConditionState(StrEnum):
    SELF_GOVERNED = "self_governed"
    SUPPORTED = "supported"
    MEDIATED = "mediated"
    CONSTRAINED = "constrained"


class EgyptianBoundNetworkMode(StrEnum):
    UNILATERAL = "unilateral"
    MUTUAL = "mutual"


class EgyptianBoundsDoctrine(StrEnum):
    EGYPTIAN = "egyptian"
    PTOLEMAIC = "ptolemaic"
    CHALDEAN = "chaldean"


@dataclass(frozen=True)
class EgyptianBoundsPolicy:
    doctrine: EgyptianBoundsDoctrine = EgyptianBoundsDoctrine.EGYPTIAN

    def __post_init__(self) -> None:
        if not isinstance(self.doctrine, EgyptianBoundsDoctrine):
            raise ValueError(
                f"doctrine must be an EgyptianBoundsDoctrine member, got {self.doctrine!r}"
            )


# Traditional Egyptian bounds: (ruler, start_degree, end_degree) per sign.
EGYPTIAN_BOUNDS: dict[str, list[tuple[str, float, float]]] = {
    "Aries":       [("Jupiter", 0,  6), ("Venus",   6, 12), ("Mercury", 12, 20), ("Mars",    20, 25), ("Saturn", 25, 30)],
    "Taurus":      [("Venus",   0,  8), ("Mercury", 8, 14), ("Jupiter", 14, 22), ("Saturn",  22, 27), ("Mars",   27, 30)],
    "Gemini":      [("Mercury", 0,  6), ("Jupiter", 6, 12), ("Venus",   12, 17), ("Mars",    17, 24), ("Saturn", 24, 30)],
    "Cancer":      [("Mars",    0,  7), ("Venus",   7, 13), ("Mercury", 13, 19), ("Jupiter", 19, 26), ("Saturn", 26, 30)],
    "Leo":         [("Jupiter", 0,  6), ("Venus",   6, 11), ("Saturn",  11, 18), ("Mercury", 18, 24), ("Mars",   24, 30)],
    "Virgo":       [("Mercury", 0,  7), ("Venus",   7, 17), ("Jupiter", 17, 21), ("Mars",    21, 28), ("Saturn", 28, 30)],
    "Libra":       [("Saturn",  0,  6), ("Mercury", 6, 14), ("Jupiter", 14, 21), ("Venus",   21, 28), ("Mars",   28, 30)],
    "Scorpio":     [("Mars",    0,  7), ("Venus",   7, 11), ("Mercury", 11, 19), ("Jupiter", 19, 24), ("Saturn", 24, 30)],
    "Sagittarius": [("Jupiter", 0, 12), ("Venus",  12, 17), ("Mercury", 17, 21), ("Saturn",  21, 26), ("Mars",   26, 30)],
    "Capricorn":   [("Mercury", 0,  7), ("Jupiter", 7, 14), ("Venus",   14, 22), ("Saturn",  22, 26), ("Mars",   26, 30)],
    "Aquarius":    [("Mercury", 0,  7), ("Venus",   7, 13), ("Jupiter", 13, 20), ("Mars",    20, 25), ("Saturn", 25, 30)],
    "Pisces":      [("Venus",   0, 12), ("Jupiter", 12, 16), ("Mercury", 16, 19), ("Mars",   19, 28), ("Saturn", 28, 30)],
}


# Ptolemaic bounds/terms — Ptolemy, Tetrabiblos I.21 (Robbins translation).
# Note: Ptolemy's own term tables differ from the Egyptian bounds above.
# Canon: Ptolemy, Tetrabiblos I.21; Hephaistion reconstruction.
PTOLEMAIC_BOUNDS: dict[str, list[tuple[str, float, float]]] = {
    "Aries":       [("Jupiter", 0,  6), ("Venus",   6, 12), ("Mercury", 12, 20), ("Mars",    20, 25), ("Saturn", 25, 30)],
    "Taurus":      [("Venus",   0,  8), ("Mercury", 8, 14), ("Jupiter", 14, 22), ("Saturn",  22, 27), ("Mars",   27, 30)],
    "Gemini":      [("Mercury", 0,  6), ("Jupiter", 6, 12), ("Venus",   12, 17), ("Mars",    17, 24), ("Saturn", 24, 30)],
    "Cancer":      [("Mars",    0,  7), ("Venus",   7, 13), ("Mercury", 13, 19), ("Jupiter", 19, 26), ("Saturn", 26, 30)],
    "Leo":         [("Jupiter", 0,  6), ("Venus",   6, 11), ("Saturn",  11, 18), ("Mercury", 18, 24), ("Mars",   24, 30)],
    "Virgo":       [("Mercury", 0,  7), ("Venus",   7, 17), ("Jupiter", 17, 21), ("Mars",    21, 28), ("Saturn", 28, 30)],
    "Libra":       [("Saturn",  0,  6), ("Mercury", 6, 14), ("Jupiter", 14, 21), ("Venus",   21, 28), ("Mars",   28, 30)],
    "Scorpio":     [("Mars",    0,  7), ("Venus",   7, 11), ("Mercury", 11, 19), ("Jupiter", 19, 24), ("Saturn", 24, 30)],
    "Sagittarius": [("Jupiter", 0, 12), ("Venus",  12, 17), ("Mercury", 17, 21), ("Saturn",  21, 26), ("Mars",   26, 30)],
    "Capricorn":   [("Mercury", 0,  7), ("Jupiter", 7, 14), ("Venus",   14, 22), ("Saturn",  22, 26), ("Mars",   26, 30)],
    "Aquarius":    [("Mercury", 0,  7), ("Venus",   7, 13), ("Jupiter", 13, 20), ("Mars",    20, 25), ("Saturn", 25, 30)],
    "Pisces":      [("Venus",   0, 12), ("Jupiter", 12, 16), ("Mercury", 16, 19), ("Mars",   19, 28), ("Saturn", 28, 30)],
}


# Chaldean bounds/terms — pre-Ptolemaic tradition via the Yavanajataka.
# Canon: D. Pingree, The Yavanajataka of Sphujidhvaja (Harvard, 1978).
CHALDEAN_BOUNDS: dict[str, list[tuple[str, float, float]]] = {
    "Aries":       [("Mars",    0,  6), ("Jupiter", 6, 12), ("Venus",   12, 20), ("Saturn",  20, 25), ("Mercury", 25, 30)],
    "Taurus":      [("Venus",   0,  8), ("Mercury", 8, 14), ("Jupiter", 14, 22), ("Saturn",  22, 27), ("Mars",    27, 30)],
    "Gemini":      [("Mercury", 0,  6), ("Jupiter", 6, 12), ("Venus",   12, 17), ("Saturn",  17, 24), ("Mars",    24, 30)],
    "Cancer":      [("Mars",    0,  7), ("Jupiter", 7, 13), ("Mercury", 13, 19), ("Venus",   19, 26), ("Saturn",  26, 30)],
    "Leo":         [("Saturn",  0,  6), ("Mercury", 6, 11), ("Venus",   11, 18), ("Jupiter", 18, 24), ("Mars",    24, 30)],
    "Virgo":       [("Mercury", 0,  7), ("Venus",   7, 17), ("Jupiter", 17, 21), ("Saturn",  21, 28), ("Mars",    28, 30)],
    "Libra":       [("Saturn",  0,  6), ("Venus",   6, 14), ("Jupiter", 14, 21), ("Mercury", 21, 28), ("Mars",    28, 30)],
    "Scorpio":     [("Mars",    0,  7), ("Jupiter", 7, 11), ("Venus",   11, 19), ("Mercury", 19, 24), ("Saturn",  24, 30)],
    "Sagittarius": [("Jupiter", 0, 12), ("Venus",  12, 17), ("Mercury", 17, 21), ("Mars",    21, 26), ("Saturn",  26, 30)],
    "Capricorn":   [("Mercury", 0,  7), ("Jupiter", 7, 14), ("Venus",   14, 22), ("Mars",    22, 26), ("Saturn",  26, 30)],
    "Aquarius":    [("Saturn",  0,  7), ("Mercury", 7, 13), ("Venus",   13, 20), ("Jupiter", 20, 25), ("Mars",    25, 30)],
    "Pisces":      [("Venus",   0, 12), ("Jupiter", 12, 16), ("Mercury", 16, 19), ("Saturn",  19, 28), ("Mars",   28, 30)],
}


@dataclass(frozen=True)
class EgyptianBoundSegment:
    sign: str
    ruler: str
    start_degree: float
    end_degree: float

    def __post_init__(self) -> None:
        if self.sign not in SIGNS:
            raise ValueError(f"Unknown Egyptian bound sign: {self.sign}")
        if self.ruler not in BOUND_RULERS:
            raise ValueError(f"Invalid Egyptian bound ruler: {self.ruler}")
        if not (0.0 <= self.start_degree < self.end_degree <= 30.0):
            raise ValueError(
                f"Invalid Egyptian bound segment range for {self.sign}: "
                f"{self.start_degree}..{self.end_degree}"
            )

    @property
    def width(self) -> float:
        return self.end_degree - self.start_degree

    def contains(self, degree_in_sign: float) -> bool:
        return self.start_degree <= degree_in_sign < self.end_degree


@dataclass(frozen=True)
class EgyptianBoundTruth:
    longitude: float
    doctrine: EgyptianBoundsDoctrine
    sign: str
    sign_index: int
    degree_in_sign: float
    segment: EgyptianBoundSegment

    def __post_init__(self) -> None:
        if not (0.0 <= self.longitude < 360.0):
            raise ValueError(f"Egyptian bound longitude must be normalized: {self.longitude}")
        if self.doctrine not in (
            EgyptianBoundsDoctrine.EGYPTIAN,
            EgyptianBoundsDoctrine.PTOLEMAIC,
            EgyptianBoundsDoctrine.CHALDEAN,
        ):
            raise ValueError(f"Unsupported bounds doctrine on truth: {self.doctrine}")
        if self.sign not in SIGNS:
            raise ValueError(f"Unknown Egyptian bound sign: {self.sign}")
        if not (0 <= self.sign_index < 12):
            raise ValueError(f"Egyptian bound sign_index out of range: {self.sign_index}")
        if SIGNS[self.sign_index] != self.sign:
            raise ValueError(
                "Egyptian bound truth invariant failed: sign_index does not match sign"
            )
        if not (0.0 <= self.degree_in_sign < 30.0):
            raise ValueError(
                f"Egyptian bound degree_in_sign out of range: {self.degree_in_sign}"
            )
        if self.segment.sign != self.sign:
            raise ValueError(
                "Egyptian bound truth invariant failed: segment sign does not match truth sign"
            )
        if not self.segment.contains(self.degree_in_sign):
            raise ValueError(
                "Egyptian bound truth invariant failed: segment does not contain degree_in_sign"
            )

    @property
    def ruler(self) -> str:
        return self.segment.ruler

    @property
    def segment_start_degree(self) -> float:
        return self.segment.start_degree

    @property
    def segment_end_degree(self) -> float:
        return self.segment.end_degree

    @property
    def segment_width(self) -> float:
        return self.segment.width

    @property
    def segment_range(self) -> tuple[float, float]:
        return (self.segment.start_degree, self.segment.end_degree)


@dataclass(frozen=True)
class EgyptianBoundClassification:
    planet: str
    truth: EgyptianBoundTruth
    own_bound: bool
    host_nature: BoundHostNature
    host_in_sect: bool | None

    def __post_init__(self) -> None:
        if not self.planet:
            raise ValueError("Egyptian bound classification requires a planet name")
        if self.own_bound != (self.truth.ruler == self.planet):
            raise ValueError(
                "Egyptian bound classification invariant failed: own_bound mismatch"
            )
        expected_nature = _host_nature(self.truth.ruler)
        if self.host_nature is not expected_nature:
            raise ValueError(
                "Egyptian bound classification invariant failed: host_nature mismatch"
            )

    @property
    def hosted_by_benefic(self) -> bool:
        return self.host_nature is BoundHostNature.BENEFIC

    @property
    def hosted_by_malefic(self) -> bool:
        return self.host_nature is BoundHostNature.MALEFIC


@dataclass(frozen=True)
class EgyptianBoundRelation:
    guest_planet: str
    host_ruler: str
    truth: EgyptianBoundTruth
    relation_kind: EgyptianBoundRelationKind
    host_nature: BoundHostNature
    host_in_sect: bool | None

    def __post_init__(self) -> None:
        if not self.guest_planet:
            raise ValueError("Egyptian bound relation requires a guest planet name")
        if self.host_ruler != self.truth.ruler:
            raise ValueError(
                "Egyptian bound relation invariant failed: host_ruler does not match truth.ruler"
            )
        expected_nature = _host_nature(self.host_ruler)
        if self.host_nature is not expected_nature:
            raise ValueError(
                "Egyptian bound relation invariant failed: host_nature mismatch"
            )
        expected_kind = _relation_kind(self.guest_planet, self.host_ruler, self.host_nature)
        if self.relation_kind is not expected_kind:
            raise ValueError(
                "Egyptian bound relation invariant failed: relation_kind mismatch"
            )

    @property
    def own_bound(self) -> bool:
        return self.relation_kind is EgyptianBoundRelationKind.SELF_HOSTED

    @property
    def hosted_by_benefic(self) -> bool:
        return self.relation_kind is EgyptianBoundRelationKind.HOSTED_BY_BENEFIC

    @property
    def hosted_by_malefic(self) -> bool:
        return self.relation_kind is EgyptianBoundRelationKind.HOSTED_BY_MALEFIC

    @property
    def hosted_by_neutral(self) -> bool:
        return self.relation_kind is EgyptianBoundRelationKind.HOSTED_BY_NEUTRAL


@dataclass(frozen=True)
class EgyptianBoundRelationProfile:
    planet: str
    truth: EgyptianBoundTruth
    detected_relation: EgyptianBoundRelation
    admitted_relations: tuple[EgyptianBoundRelation, ...]
    scored_relations: tuple[EgyptianBoundRelation, ...]

    def __post_init__(self) -> None:
        if not self.planet:
            raise ValueError("Egyptian bound relation profile requires a planet name")
        if self.detected_relation.guest_planet != self.planet:
            raise ValueError(
                "Egyptian bound relation profile invariant failed: detected relation guest mismatch"
            )
        if self.detected_relation.truth != self.truth:
            raise ValueError(
                "Egyptian bound relation profile invariant failed: detected relation truth mismatch"
            )
        for relation in self.admitted_relations:
            if relation != self.detected_relation:
                raise ValueError(
                    "Egyptian bound relation profile invariant failed: admitted relations must be the detected relation"
                )
        expected_scored = (
            self.detected_relation,
        ) if self.detected_relation.own_bound else ()
        if self.scored_relations != expected_scored:
            raise ValueError(
                "Egyptian bound relation profile invariant failed: scored_relations must match own-bound scoring"
            )
        for relation in self.scored_relations:
            if relation not in self.admitted_relations:
                raise ValueError(
                    "Egyptian bound relation profile invariant failed: scored relations must be admitted"
                )

    @property
    def detected_relation_kind(self) -> EgyptianBoundRelationKind:
        return self.detected_relation.relation_kind

    @property
    def admitted_relation_kinds(self) -> tuple[EgyptianBoundRelationKind, ...]:
        return tuple(relation.relation_kind for relation in self.admitted_relations)

    @property
    def scored_relation_kinds(self) -> tuple[EgyptianBoundRelationKind, ...]:
        return tuple(relation.relation_kind for relation in self.scored_relations)

    @property
    def has_detected_relation(self) -> bool:
        return True

    @property
    def has_admitted_relation(self) -> bool:
        return bool(self.admitted_relations)

    @property
    def has_scored_relation(self) -> bool:
        return bool(self.scored_relations)


@dataclass(frozen=True)
class EgyptianBoundConditionProfile:
    planet: str
    truth: EgyptianBoundTruth
    classification: EgyptianBoundClassification
    relation_profile: EgyptianBoundRelationProfile
    strengthening_count: int
    weakening_count: int
    neutral_count: int
    state: EgyptianBoundConditionState

    def __post_init__(self) -> None:
        if not self.planet:
            raise ValueError("Egyptian bound condition profile requires a planet name")
        if self.classification.planet != self.planet:
            raise ValueError(
                "Egyptian bound condition profile invariant failed: classification planet mismatch"
            )
        if self.relation_profile.planet != self.planet:
            raise ValueError(
                "Egyptian bound condition profile invariant failed: relation profile planet mismatch"
            )
        if self.classification.truth != self.truth:
            raise ValueError(
                "Egyptian bound condition profile invariant failed: classification truth mismatch"
            )
        if self.relation_profile.truth != self.truth:
            raise ValueError(
                "Egyptian bound condition profile invariant failed: relation profile truth mismatch"
            )
        derived_state = _derive_condition_state(self.classification, self.relation_profile)
        if self.state is not derived_state:
            raise ValueError(
                "Egyptian bound condition profile invariant failed: state must match derived condition"
            )
        derived_counts = _derive_condition_counts(self.relation_profile)
        if (
            self.strengthening_count,
            self.weakening_count,
            self.neutral_count,
        ) != derived_counts:
            raise ValueError(
                "Egyptian bound condition profile invariant failed: polarity counts mismatch"
            )

    @property
    def is_self_governed(self) -> bool:
        return self.state is EgyptianBoundConditionState.SELF_GOVERNED

    @property
    def is_supported(self) -> bool:
        return self.state is EgyptianBoundConditionState.SUPPORTED

    @property
    def is_mediated(self) -> bool:
        return self.state is EgyptianBoundConditionState.MEDIATED

    @property
    def is_constrained(self) -> bool:
        return self.state is EgyptianBoundConditionState.CONSTRAINED


@dataclass(frozen=True)
class EgyptianBoundsAggregateProfile:
    profiles: tuple[EgyptianBoundConditionProfile, ...]
    self_governed_count: int
    supported_count: int
    mediated_count: int
    constrained_count: int
    strengthening_total: int
    weakening_total: int
    neutral_total: int
    strongest_planets: tuple[str, ...]
    weakest_planets: tuple[str, ...]

    def __post_init__(self) -> None:
        expected_counts = (
            sum(1 for profile in self.profiles if profile.state is EgyptianBoundConditionState.SELF_GOVERNED),
            sum(1 for profile in self.profiles if profile.state is EgyptianBoundConditionState.SUPPORTED),
            sum(1 for profile in self.profiles if profile.state is EgyptianBoundConditionState.MEDIATED),
            sum(1 for profile in self.profiles if profile.state is EgyptianBoundConditionState.CONSTRAINED),
        )
        if (
            self.self_governed_count,
            self.supported_count,
            self.mediated_count,
            self.constrained_count,
        ) != expected_counts:
            raise ValueError(
                "Egyptian bounds aggregate invariant failed: state counts must match profile states"
            )

        expected_totals = (
            sum(profile.strengthening_count for profile in self.profiles),
            sum(profile.weakening_count for profile in self.profiles),
            sum(profile.neutral_count for profile in self.profiles),
        )
        if (
            self.strengthening_total,
            self.weakening_total,
            self.neutral_total,
        ) != expected_totals:
            raise ValueError(
                "Egyptian bounds aggregate invariant failed: polarity totals must match profile totals"
            )

        ordered_names = [
            profile.planet
            for profile in sorted(
                self.profiles,
                key=lambda profile: _PLANET_ORDER.index(profile.planet)
                if profile.planet in _PLANET_ORDER
                else len(_PLANET_ORDER),
            )
        ]
        if [profile.planet for profile in self.profiles] != ordered_names:
            raise ValueError(
                "Egyptian bounds aggregate invariant failed: profiles must be in deterministic planet order"
            )
        if len({profile.planet for profile in self.profiles}) != len(self.profiles):
            raise ValueError(
                "Egyptian bounds aggregate invariant failed: profiles must be unique by planet"
            )

        if self.profiles:
            strongest_score = max(_profile_rank(profile) for profile in self.profiles)
            weakest_score = min(_profile_rank(profile) for profile in self.profiles)
            expected_strongest = tuple(
                profile.planet for profile in self.profiles if _profile_rank(profile) == strongest_score
            )
            expected_weakest = tuple(
                profile.planet for profile in self.profiles if _profile_rank(profile) == weakest_score
            )
        else:
            expected_strongest = ()
            expected_weakest = ()
        if self.strongest_planets != expected_strongest:
            raise ValueError(
                "Egyptian bounds aggregate invariant failed: strongest_planets must match profile ranks"
            )
        if self.weakest_planets != expected_weakest:
            raise ValueError(
                "Egyptian bounds aggregate invariant failed: weakest_planets must match profile ranks"
            )

    @property
    def strongest_count(self) -> int:
        return len(self.strongest_planets)

    @property
    def weakest_count(self) -> int:
        return len(self.weakest_planets)


@dataclass(frozen=True)
class EgyptianBoundsNetworkNode:
    planet: str
    profile: EgyptianBoundConditionProfile
    incoming_count: int = 0
    outgoing_count: int = 0
    mutual_count: int = 0
    total_degree: int = 0

    def __post_init__(self) -> None:
        if self.planet != self.profile.planet:
            raise ValueError(
                "Egyptian bounds network node invariant failed: node planet must match profile planet"
            )
        if self.total_degree != self.incoming_count + self.outgoing_count:
            raise ValueError(
                "Egyptian bounds network node invariant failed: total_degree must equal incoming_count + outgoing_count"
            )
        if self.mutual_count > self.outgoing_count:
            raise ValueError(
                "Egyptian bounds network node invariant failed: mutual_count cannot exceed outgoing_count"
            )

    @property
    def is_isolated(self) -> bool:
        return self.total_degree == 0


@dataclass(frozen=True)
class EgyptianBoundsNetworkEdge:
    source_planet: str
    target_planet: str
    relation_kind: EgyptianBoundRelationKind
    mode: EgyptianBoundNetworkMode

    def __post_init__(self) -> None:
        if self.source_planet == self.target_planet:
            raise ValueError(
                "Egyptian bounds network edge invariant failed: source_planet must differ from target_planet"
            )

    @property
    def is_mutual(self) -> bool:
        return self.mode is EgyptianBoundNetworkMode.MUTUAL


@dataclass(frozen=True)
class EgyptianBoundsNetworkProfile:
    nodes: tuple[EgyptianBoundsNetworkNode, ...]
    edges: tuple[EgyptianBoundsNetworkEdge, ...]
    isolated_planets: tuple[str, ...]
    most_connected_planets: tuple[str, ...]
    mutual_edge_count: int
    unilateral_edge_count: int

    def __post_init__(self) -> None:
        isolated = tuple(node.planet for node in self.nodes if node.is_isolated)
        if self.isolated_planets != isolated:
            raise ValueError(
                "Egyptian bounds network invariant failed: isolated_planets must match node isolation state"
            )
        if self.mutual_edge_count != sum(1 for edge in self.edges if edge.is_mutual):
            raise ValueError(
                "Egyptian bounds network invariant failed: mutual_edge_count must match mutual edges"
            )
        if self.unilateral_edge_count != sum(1 for edge in self.edges if not edge.is_mutual):
            raise ValueError(
                "Egyptian bounds network invariant failed: unilateral_edge_count must match unilateral edges"
            )
        expected_node_order = tuple(
            node.planet
            for node in sorted(
                self.nodes,
                key=lambda node: _PLANET_ORDER.index(node.planet)
                if node.planet in _PLANET_ORDER
                else len(_PLANET_ORDER),
            )
        )
        if tuple(node.planet for node in self.nodes) != expected_node_order:
            raise ValueError(
                "Egyptian bounds network invariant failed: nodes must be in deterministic planet order"
            )
        node_names = tuple(node.planet for node in self.nodes)
        if len(set(node_names)) != len(node_names):
            raise ValueError(
                "Egyptian bounds network invariant failed: nodes must be unique by planet"
            )
        for edge in self.edges:
            if edge.source_planet not in node_names or edge.target_planet not in node_names:
                raise ValueError(
                    "Egyptian bounds network invariant failed: edges must refer only to declared nodes"
                )
        max_degree = max((node.total_degree for node in self.nodes), default=0)
        expected_most_connected = tuple(
            node.planet for node in self.nodes if node.total_degree == max_degree and max_degree > 0
        )
        if self.most_connected_planets != expected_most_connected:
            raise ValueError(
                "Egyptian bounds network invariant failed: most_connected_planets must match node degrees"
            )

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)


def _sign_and_degree(longitude: float) -> tuple[str, int, float]:
    lon = longitude % 360.0
    sign_index = int(lon // 30.0)
    return SIGNS[sign_index], sign_index, lon - sign_index * 30.0


def _host_nature(ruler: str) -> BoundHostNature:
    if ruler in _BENEFICS:
        return BoundHostNature.BENEFIC
    if ruler in _MALEFICS:
        return BoundHostNature.MALEFIC
    return BoundHostNature.NEUTRAL


def _host_in_sect(ruler: str, is_day_chart: bool, mercury_rises_before_sun: bool) -> bool | None:
    if ruler == "Mercury":
        mercury_sect = "diurnal" if mercury_rises_before_sun else "nocturnal"
        return mercury_sect == ("diurnal" if is_day_chart else "nocturnal")
    if ruler in _DIURNAL:
        return is_day_chart
    if ruler in _NOCTURNAL:
        return not is_day_chart
    return None


def _relation_kind(
    guest_planet: str,
    host_ruler: str,
    host_nature: BoundHostNature,
) -> EgyptianBoundRelationKind:
    if guest_planet == host_ruler:
        return EgyptianBoundRelationKind.SELF_HOSTED
    if host_nature is BoundHostNature.BENEFIC:
        return EgyptianBoundRelationKind.HOSTED_BY_BENEFIC
    if host_nature is BoundHostNature.MALEFIC:
        return EgyptianBoundRelationKind.HOSTED_BY_MALEFIC
    return EgyptianBoundRelationKind.HOSTED_BY_NEUTRAL


def _derive_condition_counts(
    relation_profile: EgyptianBoundRelationProfile,
) -> tuple[int, int, int]:
    if relation_profile.detected_relation.relation_kind is EgyptianBoundRelationKind.SELF_HOSTED:
        return (1, 0, 0)
    if relation_profile.detected_relation.relation_kind is EgyptianBoundRelationKind.HOSTED_BY_BENEFIC:
        return (1, 0, 0)
    if relation_profile.detected_relation.relation_kind is EgyptianBoundRelationKind.HOSTED_BY_MALEFIC:
        return (0, 1, 0)
    return (0, 0, 1)


def _derive_condition_state(
    classification: EgyptianBoundClassification,
    relation_profile: EgyptianBoundRelationProfile,
) -> EgyptianBoundConditionState:
    if classification.own_bound:
        return EgyptianBoundConditionState.SELF_GOVERNED
    if relation_profile.detected_relation.relation_kind is EgyptianBoundRelationKind.HOSTED_BY_BENEFIC:
        return EgyptianBoundConditionState.SUPPORTED
    if relation_profile.detected_relation.relation_kind is EgyptianBoundRelationKind.HOSTED_BY_MALEFIC:
        return EgyptianBoundConditionState.CONSTRAINED
    return EgyptianBoundConditionState.MEDIATED


def _profile_rank(profile: EgyptianBoundConditionProfile) -> tuple[int, int, int, int]:
    state_weight = {
        EgyptianBoundConditionState.SELF_GOVERNED: 3,
        EgyptianBoundConditionState.SUPPORTED: 2,
        EgyptianBoundConditionState.MEDIATED: 1,
        EgyptianBoundConditionState.CONSTRAINED: 0,
    }[profile.state]
    planet_rank = (
        -_PLANET_ORDER.index(profile.planet)
        if profile.planet in _PLANET_ORDER
        else -len(_PLANET_ORDER)
    )
    return (
        profile.strengthening_count - profile.weakening_count,
        state_weight,
        -profile.neutral_count,
        planet_rank,
    )


def _resolve_policy(policy: EgyptianBoundsPolicy | None) -> EgyptianBoundsPolicy:
    return EgyptianBoundsPolicy() if policy is None else policy


def _table_for_policy(policy: EgyptianBoundsPolicy) -> dict[str, list[tuple[str, float, float]]]:
    if policy.doctrine is EgyptianBoundsDoctrine.PTOLEMAIC:
        return PTOLEMAIC_BOUNDS
    if policy.doctrine is EgyptianBoundsDoctrine.CHALDEAN:
        return CHALDEAN_BOUNDS
    return EGYPTIAN_BOUNDS


def _validate_bounds_table(table: dict[str, list[tuple[str, float, float]]]) -> None:
    if set(table.keys()) != set(SIGNS):
        raise ValueError("Egyptian bounds table invariant failed: table must define exactly the 12 zodiac signs")
    for sign in SIGNS:
        bounds = table[sign]
        if len(bounds) != 5:
            raise ValueError(
                f"Egyptian bounds table invariant failed: {sign} must have exactly 5 segments"
            )
        position = 0.0
        for ruler, start_degree, end_degree in bounds:
            if ruler not in BOUND_RULERS:
                raise ValueError(
                    f"Egyptian bounds table invariant failed: {sign} contains invalid ruler {ruler}"
                )
            if start_degree != position:
                raise ValueError(
                    f"Egyptian bounds table invariant failed: {sign} segment starts at {start_degree}, expected {position}"
                )
            if not (start_degree < end_degree <= 30.0):
                raise ValueError(
                    f"Egyptian bounds table invariant failed: {sign} has invalid segment {start_degree}..{end_degree}"
                )
            position = end_degree
        if position != 30.0:
            raise ValueError(
                f"Egyptian bounds table invariant failed: {sign} must cover exactly 30 degrees"
            )


def egyptian_bound_of(
    longitude: float,
    *,
    policy: EgyptianBoundsPolicy | None = None,
) -> EgyptianBoundTruth:
    """
    Return the Egyptian-bound truth for an ecliptic longitude.

    Longitudes are normalized mod 360. Bound intervals are closed on the left
    and open on the right: [start, end), matching the rest of Moira's
    sign-degree segmentation.
    """
    resolved_policy = _resolve_policy(policy)
    table = _table_for_policy(resolved_policy)
    sign, sign_index, degree_in_sign = _sign_and_degree(longitude)
    for ruler, start_degree, end_degree in table[sign]:
        if start_degree <= degree_in_sign < end_degree:
            segment = EgyptianBoundSegment(
                sign=sign,
                ruler=ruler,
                start_degree=start_degree,
                end_degree=end_degree,
            )
            return EgyptianBoundTruth(
                longitude=longitude % 360.0,
                doctrine=resolved_policy.doctrine,
                sign=sign,
                sign_index=sign_index,
                degree_in_sign=degree_in_sign,
                segment=segment,
            )
    raise ValueError(f"No Egyptian bound segment covers {degree_in_sign} degrees in {sign}")


def bound_ruler(
    longitude: float,
    *,
    policy: EgyptianBoundsPolicy | None = None,
) -> str:
    """Return the ruler of the Egyptian bound at the given longitude."""
    return egyptian_bound_of(longitude, policy=policy).ruler


def is_in_own_egyptian_bound(
    planet: str,
    longitude: float,
    *,
    policy: EgyptianBoundsPolicy | None = None,
) -> bool:
    """True when the planet matches the Egyptian bound ruler at the longitude."""
    return bound_ruler(longitude, policy=policy) == planet


def classify_egyptian_bound(
    planet: str,
    longitude: float,
    *,
    policy: EgyptianBoundsPolicy | None = None,
    is_day_chart: bool | None = None,
    mercury_rises_before_sun: bool = False,
) -> EgyptianBoundClassification:
    """
    Classify a planet's relation to the Egyptian bound it occupies.

    `host_in_sect` is only computed when chart sect is supplied.
    """
    truth = egyptian_bound_of(longitude, policy=policy)
    return EgyptianBoundClassification(
        planet=planet,
        truth=truth,
        own_bound=(truth.ruler == planet),
        host_nature=_host_nature(truth.ruler),
        host_in_sect=(
            None
            if is_day_chart is None
            else _host_in_sect(truth.ruler, is_day_chart, mercury_rises_before_sun)
        ),
    )


def relate_planet_to_egyptian_bound(
    planet: str,
    longitude: float,
    *,
    policy: EgyptianBoundsPolicy | None = None,
    is_day_chart: bool | None = None,
    mercury_rises_before_sun: bool = False,
) -> EgyptianBoundRelation:
    """
    Formal guest/host relation for a planet occupying an Egyptian bound.
    """
    classification = classify_egyptian_bound(
        planet,
        longitude,
        policy=policy,
        is_day_chart=is_day_chart,
        mercury_rises_before_sun=mercury_rises_before_sun,
    )
    return EgyptianBoundRelation(
        guest_planet=planet,
        host_ruler=classification.truth.ruler,
        truth=classification.truth,
        relation_kind=_relation_kind(planet, classification.truth.ruler, classification.host_nature),
        host_nature=classification.host_nature,
        host_in_sect=classification.host_in_sect,
    )


def evaluate_egyptian_bound_relations(
    planet: str,
    longitude: float,
    *,
    policy: EgyptianBoundsPolicy | None = None,
    is_day_chart: bool | None = None,
    mercury_rises_before_sun: bool = False,
) -> EgyptianBoundRelationProfile:
    """
    Harden the local bound relation into detected, admitted, and scored subsets.

    Current doctrine/policy admits every detected local bound relation.
    Current scoring is narrower: only self-hosted relations contribute to the
    minor essential dignity represented by own-bound status.
    """
    detected_relation = relate_planet_to_egyptian_bound(
        planet,
        longitude,
        policy=policy,
        is_day_chart=is_day_chart,
        mercury_rises_before_sun=mercury_rises_before_sun,
    )
    admitted_relations = (detected_relation,)
    scored_relations = (detected_relation,) if detected_relation.own_bound else ()
    return EgyptianBoundRelationProfile(
        planet=planet,
        truth=detected_relation.truth,
        detected_relation=detected_relation,
        admitted_relations=admitted_relations,
        scored_relations=scored_relations,
    )


def evaluate_egyptian_bound_condition(
    planet: str,
    longitude: float,
    *,
    policy: EgyptianBoundsPolicy | None = None,
    is_day_chart: bool | None = None,
    mercury_rises_before_sun: bool = False,
) -> EgyptianBoundConditionProfile:
    """
    Integrated local Egyptian-bound condition profile for one planet.
    """
    classification = classify_egyptian_bound(
        planet,
        longitude,
        policy=policy,
        is_day_chart=is_day_chart,
        mercury_rises_before_sun=mercury_rises_before_sun,
    )
    relation_profile = evaluate_egyptian_bound_relations(
        planet,
        longitude,
        policy=policy,
        is_day_chart=is_day_chart,
        mercury_rises_before_sun=mercury_rises_before_sun,
    )
    strengthening_count, weakening_count, neutral_count = _derive_condition_counts(relation_profile)
    return EgyptianBoundConditionProfile(
        planet=planet,
        truth=classification.truth,
        classification=classification,
        relation_profile=relation_profile,
        strengthening_count=strengthening_count,
        weakening_count=weakening_count,
        neutral_count=neutral_count,
        state=_derive_condition_state(classification, relation_profile),
    )


def evaluate_egyptian_bounds_aggregate(
    profiles: list[EgyptianBoundConditionProfile] | tuple[EgyptianBoundConditionProfile, ...],
) -> EgyptianBoundsAggregateProfile:
    """
    Aggregate intelligence layer for a set of local Egyptian-bound profiles.
    """
    ordered_profiles = tuple(
        sorted(
            profiles,
            key=lambda profile: _PLANET_ORDER.index(profile.planet)
            if profile.planet in _PLANET_ORDER
            else len(_PLANET_ORDER),
        )
    )
    if not ordered_profiles:
        strongest_planets: tuple[str, ...] = ()
        weakest_planets: tuple[str, ...] = ()
    else:
        strongest_score = max(_profile_rank(profile) for profile in ordered_profiles)
        weakest_score = min(_profile_rank(profile) for profile in ordered_profiles)
        strongest_planets = tuple(
            profile.planet for profile in ordered_profiles if _profile_rank(profile) == strongest_score
        )
        weakest_planets = tuple(
            profile.planet for profile in ordered_profiles if _profile_rank(profile) == weakest_score
        )
    return EgyptianBoundsAggregateProfile(
        profiles=ordered_profiles,
        self_governed_count=sum(
            1 for profile in ordered_profiles if profile.state is EgyptianBoundConditionState.SELF_GOVERNED
        ),
        supported_count=sum(
            1 for profile in ordered_profiles if profile.state is EgyptianBoundConditionState.SUPPORTED
        ),
        mediated_count=sum(
            1 for profile in ordered_profiles if profile.state is EgyptianBoundConditionState.MEDIATED
        ),
        constrained_count=sum(
            1 for profile in ordered_profiles if profile.state is EgyptianBoundConditionState.CONSTRAINED
        ),
        strengthening_total=sum(profile.strengthening_count for profile in ordered_profiles),
        weakening_total=sum(profile.weakening_count for profile in ordered_profiles),
        neutral_total=sum(profile.neutral_count for profile in ordered_profiles),
        strongest_planets=strongest_planets,
        weakest_planets=weakest_planets,
    )


def evaluate_egyptian_bounds_network(
    aggregate_profile: EgyptianBoundsAggregateProfile,
) -> EgyptianBoundsNetworkProfile:
    """
    Project local Egyptian-bound relation truth into a directed guest/host network.

    Self-hosted relations remain local-condition truth and do not become self-loop
    edges in the network.
    """
    ordered_profiles = aggregate_profile.profiles
    relation_by_planet = {
        profile.planet: profile.relation_profile.detected_relation
        for profile in ordered_profiles
    }

    raw_edges: list[EgyptianBoundsNetworkEdge] = []
    for profile in ordered_profiles:
        relation = profile.relation_profile.detected_relation
        if relation.host_ruler == relation.guest_planet:
            continue
        reciprocal = relation_by_planet.get(relation.host_ruler)
        mode = EgyptianBoundNetworkMode.UNILATERAL
        if reciprocal is not None and reciprocal.host_ruler == relation.guest_planet:
            mode = EgyptianBoundNetworkMode.MUTUAL
        raw_edges.append(
            EgyptianBoundsNetworkEdge(
                source_planet=relation.guest_planet,
                target_planet=relation.host_ruler,
                relation_kind=relation.relation_kind,
                mode=mode,
            )
        )

    edges = tuple(
        sorted(
            raw_edges,
            key=lambda edge: (
                _PLANET_ORDER.index(edge.source_planet)
                if edge.source_planet in _PLANET_ORDER
                else len(_PLANET_ORDER),
                _PLANET_ORDER.index(edge.target_planet)
                if edge.target_planet in _PLANET_ORDER
                else len(_PLANET_ORDER),
                0 if edge.mode is EgyptianBoundNetworkMode.MUTUAL else 1,
            ),
        )
    )

    node_map: dict[str, EgyptianBoundsNetworkNode] = {
        profile.planet: EgyptianBoundsNetworkNode(planet=profile.planet, profile=profile)
        for profile in ordered_profiles
    }

    for edge in edges:
        source = node_map[edge.source_planet]
        target = node_map[edge.target_planet]
        node_map[edge.source_planet] = EgyptianBoundsNetworkNode(
            planet=source.planet,
            profile=source.profile,
            incoming_count=source.incoming_count,
            outgoing_count=source.outgoing_count + 1,
            mutual_count=source.mutual_count + (1 if edge.is_mutual else 0),
            total_degree=source.total_degree + 1,
        )
        node_map[edge.target_planet] = EgyptianBoundsNetworkNode(
            planet=target.planet,
            profile=target.profile,
            incoming_count=target.incoming_count + 1,
            outgoing_count=target.outgoing_count,
            mutual_count=target.mutual_count,
            total_degree=target.total_degree + 1,
        )

    nodes = tuple(
        node_map[planet]
        for planet in _PLANET_ORDER
        if planet in node_map
    )
    isolated_planets = tuple(node.planet for node in nodes if node.is_isolated)
    max_degree = max((node.total_degree for node in nodes), default=0)
    most_connected_planets = tuple(
        node.planet for node in nodes if node.total_degree == max_degree and max_degree > 0
    )

    return EgyptianBoundsNetworkProfile(
        nodes=nodes,
        edges=edges,
        isolated_planets=isolated_planets,
        most_connected_planets=most_connected_planets,
        mutual_edge_count=sum(1 for edge in edges if edge.is_mutual),
        unilateral_edge_count=sum(1 for edge in edges if not edge.is_mutual),
    )


_validate_bounds_table(EGYPTIAN_BOUNDS)
