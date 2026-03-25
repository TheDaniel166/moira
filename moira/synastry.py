from __future__ import annotations

"""
Moira — Synastry Engine
=======================

Archetype: Engine

Purpose
-------
Governs relationship chart computation: synastry inter-aspects, composite
midpoint charts, and Davison relationship charts.

Boundary declaration
--------------------
Owns: inter-chart aspect comparison, composite midpoint arithmetic,
      Davison time/location midpoint resolution and chart construction.
Delegates: planetary position computation to ``moira.planets``,
           house calculation to ``moira.houses``,
           aspect detection to ``moira.aspects``,
           Julian Day arithmetic to ``moira.julian``.

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required. No database access. Pure computation over
``moira.Chart`` instances and Julian Day values.

Public surface
--------------
``synastry_aspects`` — inter-aspects between two natal charts.
``composite_chart``  — midpoint composite chart from two natal charts.
``davison_chart``    — real chart at the midpoint time and location.
``CompositeChart``   — vessel for composite chart data.
``DavisonInfo``      — vessel for Davison midpoint time/location metadata.
``DavisonChart``     — vessel for the Davison relationship chart.
"""


import math
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING

from .constants import Body, DEG2RAD, RAD2DEG
from .coordinates import ecliptic_to_equatorial
from .midpoints import _midpoint
from .aspects import AspectData, aspects_between
from .julian import jd_from_datetime, datetime_from_jd, delta_t
from .planets import all_planets_at
from .nodes import true_node, mean_node, mean_lilith
from .obliquity import true_obliquity
from .houses import (
    HouseCusps,
    HousePlacement,
    HousePolicy,
    PolarFallbackPolicy,
    UnknownSystemPolicy,
    _KNOWN_SYSTEMS,
    _POLAR_SYSTEMS,
    _alcabitius,
    _apc,
    _asc_from_armc,
    _azimuthal,
    _campanus,
    _carter,
    _equal_house,
    _koch,
    _krusinski,
    _mc_from_armc,
    _meridian,
    _morinus,
    _placidus,
    _porphyry,
    _pullen_sd,
    _pullen_sr,
    _regiomontanus,
    _sunshine,
    _topocentric,
    _vehlow,
    _whole_sign,
    assign_house,
    calculate_houses,
    classify_house_system,
)
from .constants import HouseSystem, sign_of
from .spk_reader import get_reader, SpkReader

if TYPE_CHECKING:
    from .__init__ import Chart


__all__ = [
    # Truth
    "SynastryAspectTruth", "SynastryAspectContact",
    "SynastryOverlayTruth",
    "CompositeComputationTruth", "DavisonComputationTruth",
    # Classification
    "SynastryAspectClassification", "SynastryOverlayClassification",
    "CompositeClassification", "DavisonClassification",
    # Relation / Condition
    "SynastryRelation",
    "SynastryConditionState", "SynastryConditionProfile",
    "SynastryChartConditionProfile",
    "SynastryConditionNetworkNode", "SynastryConditionNetworkEdge",
    "SynastryConditionNetworkProfile",
    # Policy
    "SynastryAspectPolicy", "SynastryOverlayPolicy",
    "SynastryCompositePolicy", "SynastryDavisonPolicy",
    "SynastryComputationPolicy",
    # Vessels
    "SynastryHouseOverlay", "MutualHouseOverlay",
    "CompositeChart", "DavisonChart", "DavisonInfo",
    # Core functions
    "synastry_aspects", "synastry_contacts",
    "house_overlay", "mutual_house_overlays",
    "composite_chart", "composite_chart_reference_place",
    "davison_chart", "davison_chart_uncorrected",
    "davison_chart_reference_place", "davison_chart_spherical_midpoint",
    "davison_chart_corrected",
    # Condition profile functions
    "synastry_contact_relations", "mutual_overlay_relations",
    "synastry_condition_profiles", "synastry_chart_condition_profile",
    "synastry_condition_network_profile",
]


# ---------------------------------------------------------------------------
# Synastry aspects (inter-aspects between two charts)
# ---------------------------------------------------------------------------


def _classify_synastry_aspect_truth(truth: SynastryAspectTruth) -> SynastryAspectClassification:
    return SynastryAspectClassification(
        contact_mode="cross_chart_aspect",
        pair_mode="pair",
        includes_nodes=truth.include_nodes,
        uses_custom_orbs=truth.custom_orbs,
    )


def _classify_overlay_truth(truth: SynastryOverlayTruth) -> SynastryOverlayClassification:
    return SynastryOverlayClassification(
        overlay_mode="directional_house_overlay",
        pair_mode="pair",
        includes_nodes=truth.include_nodes,
        has_house_fallback=truth.target_has_fallback,
    )


def _classify_composite_truth(truth: CompositeComputationTruth) -> CompositeClassification:
    return CompositeClassification(
        chart_mode="composite",
        method=truth.method,
        includes_house_frame=truth.includes_house_frame,
    )


def _classify_davison_truth(truth: DavisonComputationTruth) -> DavisonClassification:
    return DavisonClassification(
        chart_mode="davison",
        method=truth.method,
        latitude_mode=truth.latitude_mode,
        longitude_mode=truth.longitude_mode,
        correction_mode="corrected" if truth.method == "corrected" else "uncorrected",
    )


def _relation_basis_for_composite_method(method: str) -> str:
    return "reference_place_composite" if method == "reference_place" else "midpoint_composite"


def _relation_basis_for_davison_method(method: str) -> str:
    mapping = {
        "midpoint_location": "midpoint_location_davison",
        "uncorrected": "uncorrected_davison",
        "reference_place": "reference_place_davison",
        "spherical_midpoint": "spherical_midpoint_davison",
        "corrected": "corrected_davison",
    }
    return mapping[method]


@dataclass(slots=True)
class SynastryAspectTruth:
    """Preserve the doctrinal/computational path for one cross-chart aspect."""

    source_label: str
    target_label: str
    source_body: str
    target_body: str
    tier: int
    include_nodes: bool
    orb_factor: float
    custom_orbs: bool
    source_speed: float | None
    target_speed: float | None


@dataclass(slots=True)
class SynastryAspectContact:
    """Additive synastry contact vessel preserving raw aspect plus pair truth."""

    aspect: AspectData
    truth: SynastryAspectTruth
    classification: SynastryAspectClassification | None = None
    relation: SynastryRelation | None = None
    condition_profile: SynastryConditionProfile | None = None

    def __post_init__(self) -> None:
        if self.truth.source_body != self.aspect.body1:
            raise ValueError("synastry contact truth source_body must match aspect.body1")
        if self.truth.target_body != self.aspect.body2:
            raise ValueError("synastry contact truth target_body must match aspect.body2")
        if self.classification is not None:
            if self.classification.contact_mode != "cross_chart_aspect":
                raise ValueError("synastry contact classification contact_mode must be cross_chart_aspect")
            if self.classification.pair_mode != "pair":
                raise ValueError("synastry contact classification pair_mode must be pair")
            if self.classification.includes_nodes != self.truth.include_nodes:
                raise ValueError("synastry contact classification includes_nodes must match truth")
            if self.classification.uses_custom_orbs != self.truth.custom_orbs:
                raise ValueError("synastry contact classification uses_custom_orbs must match truth")
        if self.relation is not None:
            if self.relation.kind != "cross_chart_contact":
                raise ValueError("synastry contact relation kind must be cross_chart_contact")
            if self.relation.basis != "aspect":
                raise ValueError("synastry contact relation basis must be aspect")
            if self.relation.source_label != self.truth.source_label:
                raise ValueError("synastry contact relation source_label must match truth")
            if self.relation.target_label != self.truth.target_label:
                raise ValueError("synastry contact relation target_label must match truth")
            if self.relation.source_ref != self.truth.source_body:
                raise ValueError("synastry contact relation source_ref must match truth source_body")
            if self.relation.target_ref != self.truth.target_body:
                raise ValueError("synastry contact relation target_ref must match truth target_body")
        if self.condition_profile is not None:
            if self.condition_profile.result_kind != (self.contact_mode or "cross_chart_aspect"):
                raise ValueError("synastry contact condition profile result_kind must match classification")
            if self.condition_profile.relation_kind != (self.relation_kind or "cross_chart_contact"):
                raise ValueError("synastry contact condition profile relation_kind must match relation")
            if self.condition_profile.relation_basis != (self.relation_basis or "aspect"):
                raise ValueError("synastry contact condition profile relation_basis must match relation")
            if self.condition_profile.includes_nodes != self.includes_nodes:
                raise ValueError("synastry contact condition profile includes_nodes must match contact")

    @property
    def contact_mode(self) -> str | None:
        return None if self.classification is None else self.classification.contact_mode

    @property
    def pair_mode(self) -> str | None:
        return None if self.classification is None else self.classification.pair_mode

    @property
    def includes_nodes(self) -> bool:
        return self.truth.include_nodes if self.classification is None else self.classification.includes_nodes

    @property
    def uses_custom_orbs(self) -> bool:
        return self.truth.custom_orbs if self.classification is None else self.classification.uses_custom_orbs

    @property
    def has_source_speed(self) -> bool:
        return self.truth.source_speed is not None

    @property
    def has_target_speed(self) -> bool:
        return self.truth.target_speed is not None

    @property
    def relation_kind(self) -> str | None:
        return None if self.relation is None else self.relation.kind

    @property
    def relation_basis(self) -> str | None:
        return None if self.relation is None else self.relation.basis

    @property
    def has_relation(self) -> bool:
        return self.relation is not None

    @property
    def condition_state(self) -> str | None:
        return None if self.condition_profile is None else self.condition_profile.condition_state.name


@dataclass(slots=True)
class SynastryOverlayTruth:
    """Preserve the computational path for one directional house overlay."""

    source_label: str
    target_label: str
    include_nodes: bool
    point_count: int
    target_house_system: str
    target_effective_house_system: str
    target_has_fallback: bool


@dataclass(slots=True)
class CompositeComputationTruth:
    """Preserve the doctrinal/computational path for a composite chart result."""

    method: str
    jd_mean: float
    includes_house_frame: bool
    reference_latitude: float | None = None
    house_system: str | None = None
    composite_mc: float | None = None
    composite_armc: float | None = None
    source_house_system: str | None = None
    source_effective_house_system: str | None = None


@dataclass(slots=True)
class DavisonComputationTruth:
    """Preserve the doctrinal/computational path for a Davison chart result."""

    method: str
    raw_midpoint_jd: float
    used_jd: float
    latitude_mode: str
    longitude_mode: str
    latitude_midpoint: float
    longitude_midpoint: float
    house_system: str
    corrected_target_mc: float | None = None
    correction_applied: bool = False


@dataclass(slots=True)
class SynastryAspectClassification:
    """Typed descriptive classification derived from synastry aspect truth."""

    contact_mode: str
    pair_mode: str
    includes_nodes: bool
    uses_custom_orbs: bool

    def __post_init__(self) -> None:
        if self.contact_mode != "cross_chart_aspect":
            raise ValueError("synastry aspect classification contact_mode must be cross_chart_aspect")
        if self.pair_mode != "pair":
            raise ValueError("synastry aspect classification pair_mode must be pair")


@dataclass(slots=True)
class SynastryOverlayClassification:
    """Typed descriptive classification derived from overlay truth."""

    overlay_mode: str
    pair_mode: str
    includes_nodes: bool
    has_house_fallback: bool

    def __post_init__(self) -> None:
        if self.overlay_mode != "directional_house_overlay":
            raise ValueError("synastry overlay classification overlay_mode must be directional_house_overlay")
        if self.pair_mode != "pair":
            raise ValueError("synastry overlay classification pair_mode must be pair")


@dataclass(slots=True)
class CompositeClassification:
    """Typed descriptive classification derived from composite computation truth."""

    chart_mode: str
    method: str
    includes_house_frame: bool

    def __post_init__(self) -> None:
        if self.chart_mode != "composite":
            raise ValueError("composite classification chart_mode must be composite")
        if self.method not in {"midpoint", "reference_place"}:
            raise ValueError("composite classification method must be a supported composite doctrine")


@dataclass(slots=True)
class DavisonClassification:
    """Typed descriptive classification derived from Davison computation truth."""

    chart_mode: str
    method: str
    latitude_mode: str
    longitude_mode: str
    correction_mode: str

    def __post_init__(self) -> None:
        if self.chart_mode != "davison":
            raise ValueError("Davison classification chart_mode must be davison")
        if self.method not in {
            "midpoint_location",
            "uncorrected",
            "reference_place",
            "spherical_midpoint",
            "corrected",
        }:
            raise ValueError("Davison classification method must be a supported Davison doctrine")
        if self.correction_mode not in {"corrected", "uncorrected"}:
            raise ValueError("Davison classification correction_mode must be corrected or uncorrected")


@dataclass(slots=True)
class SynastryRelation:
    """Explicit relational truth derived from the current synastry backend."""

    kind: str
    basis: str
    source_label: str
    target_label: str
    source_ref: str | None = None
    target_ref: str | None = None
    method: str | None = None

    def __post_init__(self) -> None:
        valid_kinds = {"cross_chart_contact", "house_overlay", "relationship_chart"}
        if self.kind not in valid_kinds:
            raise ValueError("synastry relation kind must be a supported synastry relation kind")
        valid_bases = {
            "aspect",
            "house_membership",
            "midpoint_composite",
            "reference_place_composite",
            "midpoint_location_davison",
            "uncorrected_davison",
            "reference_place_davison",
            "spherical_midpoint_davison",
            "corrected_davison",
        }
        if self.basis not in valid_bases:
            raise ValueError("synastry relation basis must be a supported synastry relation basis")
        if not self.source_label.strip() or not self.target_label.strip():
            raise ValueError("synastry relation labels must be non-empty")
        if self.kind == "cross_chart_contact":
            if self.basis != "aspect":
                raise ValueError("cross-chart contact relation basis must be aspect")
            if self.source_ref is None or self.target_ref is None:
                raise ValueError("cross-chart contact relation requires source_ref and target_ref")
            if self.method is not None:
                raise ValueError("cross-chart contact relation must not carry a chart method")
        elif self.kind == "house_overlay":
            if self.basis != "house_membership":
                raise ValueError("house overlay relation basis must be house_membership")
            if self.source_ref is None or self.target_ref is None:
                raise ValueError("house overlay relation requires source_ref and target_ref")
            if self.method is not None:
                raise ValueError("house overlay relation must not carry a chart method")
        else:
            expected_methods = {
                "midpoint_composite": "midpoint",
                "reference_place_composite": "reference_place",
                "midpoint_location_davison": "midpoint_location",
                "uncorrected_davison": "uncorrected",
                "reference_place_davison": "reference_place",
                "spherical_midpoint_davison": "spherical_midpoint",
                "corrected_davison": "corrected",
            }
            expected_method = expected_methods[self.basis]
            if self.method != expected_method:
                raise ValueError("relationship chart relation method must match basis")

    @property
    def is_contact_relation(self) -> bool:
        return self.kind == "cross_chart_contact"

    @property
    def is_overlay_relation(self) -> bool:
        return self.kind == "house_overlay"

    @property
    def is_relationship_chart_relation(self) -> bool:
        return self.kind == "relationship_chart"

    @property
    def is_composite_relation(self) -> bool:
        return self.basis in {"midpoint_composite", "reference_place_composite"}

    @property
    def is_davison_relation(self) -> bool:
        return self.basis in {
            "midpoint_location_davison",
            "uncorrected_davison",
            "reference_place_davison",
            "spherical_midpoint_davison",
            "corrected_davison",
        }


@dataclass(slots=True)
class SynastryConditionState:
    """Structural condition state for a single synastry result vessel."""

    name: str

    def __post_init__(self) -> None:
        if self.name not in {"contact", "overlay", "relationship_chart"}:
            raise ValueError("synastry condition state must be contact, overlay, or relationship_chart")


@dataclass(slots=True)
class SynastryConditionProfile:
    """Integrated per-result synastry condition profile derived from existing truth."""

    result_kind: str
    condition_state: SynastryConditionState
    pair_mode: str
    relation_kind: str
    relation_basis: str
    method: str | None = None
    includes_nodes: bool | None = None
    includes_house_frame: bool | None = None
    has_house_fallback: bool | None = None

    def __post_init__(self) -> None:
        if self.result_kind not in {
            "cross_chart_aspect",
            "directional_house_overlay",
            "composite",
            "davison",
        }:
            raise ValueError("synastry condition profile result_kind must be a supported synastry result kind")
        if self.condition_state.name == "contact" and self.relation_kind != "cross_chart_contact":
            raise ValueError("contact condition profile must use cross_chart_contact relation kind")
        if self.condition_state.name == "overlay" and self.relation_kind != "house_overlay":
            raise ValueError("overlay condition profile must use house_overlay relation kind")
        if self.condition_state.name == "relationship_chart" and self.relation_kind != "relationship_chart":
            raise ValueError("relationship chart condition profile must use relationship_chart relation kind")


def _synastry_condition_strength(profile: SynastryConditionProfile) -> int:
    ranks = {
        "contact": 0,
        "overlay": 1,
        "relationship_chart": 2,
    }
    return ranks[profile.condition_state.name]


def _synastry_condition_sort_key(profile: SynastryConditionProfile) -> tuple[object, ...]:
    return (
        profile.condition_state.name,
        profile.result_kind,
        profile.relation_kind,
        profile.relation_basis,
        profile.method or "",
        profile.pair_mode,
        profile.includes_nodes if profile.includes_nodes is not None else False,
        profile.includes_house_frame if profile.includes_house_frame is not None else False,
        profile.has_house_fallback if profile.has_house_fallback is not None else False,
    )


@dataclass(slots=True)
class SynastryChartConditionProfile:
    """Chart-wide synastry condition aggregate built from per-result profiles."""

    profiles: tuple[SynastryConditionProfile, ...]
    contact_count: int
    overlay_count: int
    relationship_chart_count: int
    strongest_profiles: tuple[SynastryConditionProfile, ...]
    weakest_profiles: tuple[SynastryConditionProfile, ...]

    def __post_init__(self) -> None:
        expected_profiles = tuple(sorted(self.profiles, key=_synastry_condition_sort_key))
        if self.profiles != expected_profiles:
            raise ValueError("synastry chart condition profiles must be deterministically ordered")
        if self.contact_count != sum(1 for profile in self.profiles if profile.condition_state.name == "contact"):
            raise ValueError("synastry chart contact_count must match profiles")
        if self.overlay_count != sum(1 for profile in self.profiles if profile.condition_state.name == "overlay"):
            raise ValueError("synastry chart overlay_count must match profiles")
        if self.relationship_chart_count != sum(1 for profile in self.profiles if profile.condition_state.name == "relationship_chart"):
            raise ValueError("synastry chart relationship_chart_count must match profiles")
        if self.profiles:
            strongest_rank = max(_synastry_condition_strength(profile) for profile in self.profiles)
            weakest_rank = min(_synastry_condition_strength(profile) for profile in self.profiles)
            expected_strongest = tuple(profile for profile in self.profiles if _synastry_condition_strength(profile) == strongest_rank)
            expected_weakest = tuple(profile for profile in self.profiles if _synastry_condition_strength(profile) == weakest_rank)
        else:
            expected_strongest = ()
            expected_weakest = ()
        if self.strongest_profiles != expected_strongest:
            raise ValueError("synastry chart strongest_profiles must match derived ranking")
        if self.weakest_profiles != expected_weakest:
            raise ValueError("synastry chart weakest_profiles must match derived ranking")
        if tuple(sorted(self.strongest_profiles, key=_synastry_condition_sort_key)) != self.strongest_profiles:
            raise ValueError("synastry chart strongest_profiles must be deterministically ordered")
        if tuple(sorted(self.weakest_profiles, key=_synastry_condition_sort_key)) != self.weakest_profiles:
            raise ValueError("synastry chart weakest_profiles must be deterministically ordered")

    @property
    def profile_count(self) -> int:
        return len(self.profiles)

    @property
    def strongest_count(self) -> int:
        return len(self.strongest_profiles)

    @property
    def weakest_count(self) -> int:
        return len(self.weakest_profiles)


@dataclass(slots=True)
class SynastryConditionNetworkNode:
    """One node in the synastry relation/condition network."""

    node_id: str
    kind: str
    incoming_count: int
    outgoing_count: int

    def __post_init__(self) -> None:
        if not self.node_id.strip():
            raise ValueError("synastry network node_id must be non-empty")
        if self.kind not in {"pair", "body", "chart"}:
            raise ValueError("synastry network node kind must be pair, body, or chart")
        if self.incoming_count < 0 or self.outgoing_count < 0:
            raise ValueError("synastry network node counts must be non-negative")

    @property
    def total_degree(self) -> int:
        return self.incoming_count + self.outgoing_count


@dataclass(slots=True)
class SynastryConditionNetworkEdge:
    """One directed edge in the synastry relation/condition network."""

    source_id: str
    target_id: str
    relation_kind: str
    relation_basis: str
    condition_state: str

    def __post_init__(self) -> None:
        if not self.source_id.strip() or not self.target_id.strip():
            raise ValueError("synastry network edge endpoints must be non-empty")
        if self.relation_kind not in {"cross_chart_contact", "house_overlay", "relationship_chart"}:
            raise ValueError("synastry network edge relation_kind must be supported")
        if self.condition_state not in {"contact", "overlay", "relationship_chart"}:
            raise ValueError("synastry network edge condition_state must be supported")


@dataclass(slots=True)
class SynastryConditionNetworkProfile:
    """Network projection built from existing synastry relations and condition profiles."""

    nodes: tuple[SynastryConditionNetworkNode, ...]
    edges: tuple[SynastryConditionNetworkEdge, ...]
    isolated_nodes: tuple[SynastryConditionNetworkNode, ...]
    most_connected_nodes: tuple[SynastryConditionNetworkNode, ...]

    def __post_init__(self) -> None:
        expected_nodes = tuple(sorted(self.nodes, key=lambda node: (node.kind, node.node_id)))
        expected_edges = tuple(sorted(
            self.edges,
            key=lambda edge: (edge.source_id, edge.target_id, edge.relation_kind, edge.relation_basis, edge.condition_state),
        ))
        if self.nodes != expected_nodes:
            raise ValueError("synastry network nodes must be deterministically ordered")
        if self.edges != expected_edges:
            raise ValueError("synastry network edges must be deterministically ordered")
        node_ids = {node.node_id for node in self.nodes}
        if len(node_ids) != len(self.nodes):
            raise ValueError("synastry network node ids must be unique")
        for edge in self.edges:
            if edge.source_id not in node_ids or edge.target_id not in node_ids:
                raise ValueError("synastry network edges must reference known nodes")
            if edge.relation_kind == "cross_chart_contact" and edge.condition_state != "contact":
                raise ValueError("cross-chart contact edges must use contact condition_state")
            if edge.relation_kind == "house_overlay" and edge.condition_state != "overlay":
                raise ValueError("house overlay edges must use overlay condition_state")
            if edge.relation_kind == "relationship_chart" and edge.condition_state != "relationship_chart":
                raise ValueError("relationship chart edges must use relationship_chart condition_state")
        incoming = {node.node_id: 0 for node in self.nodes}
        outgoing = {node.node_id: 0 for node in self.nodes}
        for edge in self.edges:
            outgoing[edge.source_id] += 1
            incoming[edge.target_id] += 1
        for node in self.nodes:
            if node.incoming_count != incoming[node.node_id]:
                raise ValueError("synastry network node incoming_count must match edges")
            if node.outgoing_count != outgoing[node.node_id]:
                raise ValueError("synastry network node outgoing_count must match edges")
        expected_isolated = tuple(node for node in self.nodes if node.total_degree == 0)
        if self.isolated_nodes != expected_isolated:
            raise ValueError("synastry network isolated_nodes must match nodes")
        if self.nodes:
            max_degree = max(node.total_degree for node in self.nodes)
            expected_most_connected = tuple(node for node in self.nodes if node.total_degree == max_degree)
        else:
            expected_most_connected = ()
        if self.most_connected_nodes != expected_most_connected:
            raise ValueError("synastry network most_connected_nodes must match nodes")

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)


def _build_contact_condition_profile(contact: SynastryAspectContact) -> SynastryConditionProfile:
    return SynastryConditionProfile(
        result_kind=contact.contact_mode or "cross_chart_aspect",
        condition_state=SynastryConditionState("contact"),
        pair_mode=contact.pair_mode or "pair",
        relation_kind=contact.relation_kind or "cross_chart_contact",
        relation_basis=contact.relation_basis or "aspect",
        includes_nodes=contact.includes_nodes,
    )


def _build_overlay_condition_profile(overlay: SynastryHouseOverlay) -> SynastryConditionProfile:
    return SynastryConditionProfile(
        result_kind=overlay.overlay_mode or "directional_house_overlay",
        condition_state=SynastryConditionState("overlay"),
        pair_mode=overlay.pair_mode or "pair",
        relation_kind=overlay.relation_kind or "house_overlay",
        relation_basis=overlay.relation_basis or "house_membership",
        includes_nodes=overlay.includes_nodes,
        has_house_fallback=overlay.has_house_fallback,
    )


def _build_composite_condition_profile(composite: CompositeChart) -> SynastryConditionProfile:
    return SynastryConditionProfile(
        result_kind=composite.chart_mode or "composite",
        condition_state=SynastryConditionState("relationship_chart"),
        pair_mode="pair",
        relation_kind=composite.relation_kind or "relationship_chart",
        relation_basis=composite.relation_basis or "midpoint_composite",
        method=composite.method,
        includes_house_frame=composite.includes_house_frame,
    )


def _build_davison_condition_profile(davison: DavisonInfo) -> SynastryConditionProfile:
    return SynastryConditionProfile(
        result_kind=davison.chart_mode or "davison",
        condition_state=SynastryConditionState("relationship_chart"),
        pair_mode="pair",
        relation_kind=davison.relation_kind or "relationship_chart",
        relation_basis=davison.relation_basis or "midpoint_location_davison",
        method=davison.method,
        includes_house_frame=True,
    )


@dataclass(frozen=True, slots=True)
class SynastryAspectPolicy:
    """Doctrine surface for direct synastry aspect search."""

    tier: int = 2
    orbs: dict[float, float] | None = None
    orb_factor: float = 1.0
    include_nodes: bool = True

    def __post_init__(self) -> None:
        if self.tier not in {1, 2}:
            raise ValueError("synastry aspect policy tier must be 1 or 2")
        if not math.isfinite(self.orb_factor) or self.orb_factor <= 0.0:
            raise ValueError("synastry aspect policy orb_factor must be positive and finite")
        if self.orbs is not None:
            for angle, orb in self.orbs.items():
                if not math.isfinite(angle) or not math.isfinite(orb) or orb <= 0.0:
                    raise ValueError("synastry aspect policy orbs must contain finite positive values")


@dataclass(frozen=True, slots=True)
class SynastryOverlayPolicy:
    """Doctrine surface for directional synastry house overlays."""

    include_nodes: bool = True


@dataclass(frozen=True, slots=True)
class SynastryCompositePolicy:
    """Doctrine surface for composite reference-place house selection."""

    reference_place_house_system: str = HouseSystem.PLACIDUS

    def __post_init__(self) -> None:
        if not str(self.reference_place_house_system).strip():
            raise ValueError("synastry composite policy reference_place_house_system must be non-empty")


@dataclass(frozen=True, slots=True)
class SynastryDavisonPolicy:
    """Doctrine surface for Davison chart house-system defaults."""

    default_house_system: str = HouseSystem.PLACIDUS

    def __post_init__(self) -> None:
        if not str(self.default_house_system).strip():
            raise ValueError("synastry Davison policy default_house_system must be non-empty")


@dataclass(frozen=True, slots=True)
class SynastryComputationPolicy:
    """Lean backend policy surface for the current synastry doctrine."""

    aspects: SynastryAspectPolicy = field(default_factory=SynastryAspectPolicy)
    overlays: SynastryOverlayPolicy = field(default_factory=SynastryOverlayPolicy)
    composite: SynastryCompositePolicy = field(default_factory=SynastryCompositePolicy)
    davison: SynastryDavisonPolicy = field(default_factory=SynastryDavisonPolicy)


DEFAULT_SYNASTRY_POLICY = SynastryComputationPolicy()


def _resolve_synastry_policy(policy: SynastryComputationPolicy | None) -> SynastryComputationPolicy:
    return DEFAULT_SYNASTRY_POLICY if policy is None else policy


def _validate_label_pair(source_label: str, target_label: str) -> None:
    if not source_label.strip() or not target_label.strip():
        raise ValueError("synastry labels must be non-empty")


def _validate_finite_coordinate(value: float, name: str) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


def _validate_house_system_code(house_system: str | None, name: str = "house_system") -> None:
    if house_system is None or not str(house_system).strip():
        raise ValueError(f"{name} must be a non-empty house system code")


def _validate_synastry_aspect_inputs(
    *,
    tier: int,
    orb_factor: float,
    include_nodes: bool,
    orbs: dict[float, float] | None,
) -> None:
    if tier not in {1, 2}:
        raise ValueError("synastry tier must be 1 or 2")
    if not math.isfinite(orb_factor) or orb_factor <= 0.0:
        raise ValueError("synastry orb_factor must be positive and finite")
    if not isinstance(include_nodes, bool):
        raise ValueError("synastry include_nodes must be boolean")
    if orbs is not None:
        for angle, orb in orbs.items():
            if not math.isfinite(angle) or not math.isfinite(orb) or orb <= 0.0:
                raise ValueError("synastry orbs must contain finite positive values")


@dataclass(slots=True)
class SynastryHouseOverlay:
    """Directional synastry house-overlay result."""

    source_label: str
    target_label: str
    placements: dict[str, HousePlacement]
    include_nodes: bool = True
    computation_truth: SynastryOverlayTruth | None = None
    classification: SynastryOverlayClassification | None = None
    relation: SynastryRelation | None = None
    condition_profile: SynastryConditionProfile | None = None

    def __post_init__(self) -> None:
        if not self.source_label.strip():
            raise ValueError("source_label must be non-empty")
        if not self.target_label.strip():
            raise ValueError("target_label must be non-empty")
        if self.computation_truth is not None:
            if self.computation_truth.source_label != self.source_label:
                raise ValueError("overlay computation_truth source_label must match overlay")
            if self.computation_truth.target_label != self.target_label:
                raise ValueError("overlay computation_truth target_label must match overlay")
            if self.computation_truth.include_nodes != self.include_nodes:
                raise ValueError("overlay computation_truth include_nodes must match overlay")
            if self.computation_truth.point_count != len(self.placements):
                raise ValueError("overlay computation_truth point_count must match placements")
        if self.classification is not None:
            if self.classification.overlay_mode != "directional_house_overlay":
                raise ValueError("overlay classification overlay_mode must be directional_house_overlay")
            if self.classification.pair_mode != "pair":
                raise ValueError("overlay classification pair_mode must be pair")
            if self.computation_truth is None:
                raise ValueError("overlay classification requires computation_truth")
            if self.classification.includes_nodes != self.computation_truth.include_nodes:
                raise ValueError("overlay classification includes_nodes must match truth")
            if self.classification.has_house_fallback != self.computation_truth.target_has_fallback:
                raise ValueError("overlay classification has_house_fallback must match truth")
        if self.relation is not None:
            if self.relation.kind != "house_overlay":
                raise ValueError("overlay relation kind must be house_overlay")
            if self.relation.basis != "house_membership":
                raise ValueError("overlay relation basis must be house_membership")
            if self.computation_truth is None:
                raise ValueError("overlay relation requires computation_truth")
            if self.relation.source_label != self.computation_truth.source_label:
                raise ValueError("overlay relation source_label must match truth")
            if self.relation.target_label != self.computation_truth.target_label:
                raise ValueError("overlay relation target_label must match truth")
        if self.condition_profile is not None:
            if self.condition_profile.result_kind != (self.overlay_mode or "directional_house_overlay"):
                raise ValueError("overlay condition profile result_kind must match classification")
            if self.condition_profile.relation_kind != (self.relation_kind or "house_overlay"):
                raise ValueError("overlay condition profile relation_kind must match relation")
            if self.condition_profile.relation_basis != (self.relation_basis or "house_membership"):
                raise ValueError("overlay condition profile relation_basis must match relation")
            if self.condition_profile.includes_nodes != self.includes_nodes:
                raise ValueError("overlay condition profile includes_nodes must match overlay")
            if self.condition_profile.has_house_fallback != self.has_house_fallback:
                raise ValueError("overlay condition profile has_house_fallback must match overlay")

    def bodies_in_house(self, house: int) -> tuple[str, ...]:
        """Return the deterministically ordered bodies placed in one target house."""

        return tuple(sorted(
            name for name, placement in self.placements.items() if placement.house == house
        ))

    @property
    def overlay_mode(self) -> str | None:
        return None if self.classification is None else self.classification.overlay_mode

    @property
    def pair_mode(self) -> str | None:
        return None if self.classification is None else self.classification.pair_mode

    @property
    def has_house_fallback(self) -> bool:
        return False if self.classification is None else self.classification.has_house_fallback

    @property
    def includes_nodes(self) -> bool:
        return self.include_nodes

    @property
    def target_house_system(self) -> str | None:
        return None if self.computation_truth is None else self.computation_truth.target_house_system

    @property
    def target_effective_house_system(self) -> str | None:
        return None if self.computation_truth is None else self.computation_truth.target_effective_house_system

    @property
    def relation_kind(self) -> str | None:
        return None if self.relation is None else self.relation.kind

    @property
    def relation_basis(self) -> str | None:
        return None if self.relation is None else self.relation.basis

    @property
    def has_relation(self) -> bool:
        return self.relation is not None

    @property
    def condition_state(self) -> str | None:
        return None if self.condition_profile is None else self.condition_profile.condition_state.name


@dataclass(slots=True)
class MutualHouseOverlay:
    """Container for the two directional house overlays in a synastry pair."""

    first_in_second: SynastryHouseOverlay
    second_in_first: SynastryHouseOverlay

def synastry_aspects(
    chart_a: "Chart",
    chart_b: "Chart",
    tier: int | None = None,
    orbs: dict[float, float] | None = None,
    orb_factor: float | None = None,
    include_nodes: bool | None = None,
    policy: SynastryComputationPolicy | None = None,
) -> list[AspectData]:
    """
    Find all inter-aspects between two natal charts (synastry).

    Every body in chart_a is compared to every body in chart_b.
    No intra-chart aspects are included.

    Parameters
    ----------
    chart_a       : first natal Chart
    chart_b       : second natal Chart
    tier          : aspect set (1=major only, 2=all, default 2)
    orbs          : custom orb table {angle: max_orb}
    orb_factor    : multiplier for default orbs
    include_nodes : include True Node / Mean Node / Lilith

    Returns
    -------
    List of AspectData sorted by orb.
    """
    active_policy = _resolve_synastry_policy(policy).aspects
    tier = active_policy.tier if tier is None else tier
    orbs = active_policy.orbs if orbs is None else orbs
    orb_factor = active_policy.orb_factor if orb_factor is None else orb_factor
    include_nodes = active_policy.include_nodes if include_nodes is None else include_nodes
    _validate_synastry_aspect_inputs(
        tier=tier,
        orb_factor=orb_factor,
        include_nodes=include_nodes,
        orbs=orbs,
    )

    lons_a = chart_a.longitudes(include_nodes=include_nodes)
    lons_b = chart_b.longitudes(include_nodes=include_nodes)

    speeds_a = chart_a.speeds()
    speeds_b = chart_b.speeds()

    results: list[AspectData] = []
    for name_a, lon_a in lons_a.items():
        for name_b, lon_b in lons_b.items():
            found = aspects_between(
                name_a, lon_a,
                name_b, lon_b,
                tier=tier,
                orbs=orbs,
                orb_factor=orb_factor,
                speed_a=speeds_a.get(name_a),
                speed_b=speeds_b.get(name_b),
            )
            results.extend(found)

    results.sort(key=lambda a: a.orb)
    return results


def synastry_contacts(
    chart_a: "Chart",
    chart_b: "Chart",
    tier: int | None = None,
    orbs: dict[float, float] | None = None,
    orb_factor: float | None = None,
    include_nodes: bool | None = None,
    source_label: str = "A",
    target_label: str = "B",
    policy: SynastryComputationPolicy | None = None,
) -> list[SynastryAspectContact]:
    """Return additive synastry contact vessels over the current aspect engine."""

    active_policy = _resolve_synastry_policy(policy).aspects
    tier = active_policy.tier if tier is None else tier
    orbs = active_policy.orbs if orbs is None else orbs
    orb_factor = active_policy.orb_factor if orb_factor is None else orb_factor
    include_nodes = active_policy.include_nodes if include_nodes is None else include_nodes
    _validate_synastry_aspect_inputs(
        tier=tier,
        orb_factor=orb_factor,
        include_nodes=include_nodes,
        orbs=orbs,
    )
    _validate_label_pair(source_label, target_label)

    lons_a = chart_a.longitudes(include_nodes=include_nodes)
    lons_b = chart_b.longitudes(include_nodes=include_nodes)
    speeds_a = chart_a.speeds()
    speeds_b = chart_b.speeds()
    contacts: list[SynastryAspectContact] = []
    for name_a, lon_a in lons_a.items():
        for name_b, lon_b in lons_b.items():
            found = aspects_between(
                name_a, lon_a,
                name_b, lon_b,
                tier=tier,
                orbs=orbs,
                orb_factor=orb_factor,
                speed_a=speeds_a.get(name_a),
                speed_b=speeds_b.get(name_b),
            )
            for aspect in found:
                truth = SynastryAspectTruth(
                    source_label=source_label,
                    target_label=target_label,
                    source_body=name_a,
                    target_body=name_b,
                    tier=tier,
                    include_nodes=include_nodes,
                    orb_factor=orb_factor,
                    custom_orbs=orbs is not None,
                    source_speed=speeds_a.get(name_a),
                    target_speed=speeds_b.get(name_b),
                )
                classification = _classify_synastry_aspect_truth(truth)
                relation = SynastryRelation(
                    kind="cross_chart_contact",
                    basis="aspect",
                    source_label=source_label,
                    target_label=target_label,
                    source_ref=name_a,
                    target_ref=name_b,
                )
                condition_profile = _build_contact_condition_profile(
                    SynastryAspectContact(
                        aspect=aspect,
                        truth=truth,
                        classification=classification,
                        relation=relation,
                    )
                )
                contacts.append(
                    SynastryAspectContact(
                        aspect=aspect,
                        truth=truth,
                        classification=classification,
                        relation=relation,
                        condition_profile=condition_profile,
                    )
                )
    contacts.sort(key=lambda contact: contact.aspect.orb)
    return contacts


def house_overlay(
    chart_source: "Chart",
    target_houses: HouseCusps,
    *,
    include_nodes: bool | None = None,
    source_label: str = "A",
    target_label: str = "B",
    policy: SynastryComputationPolicy | None = None,
) -> SynastryHouseOverlay:
    """
    Place one chart's points into another chart's houses.

    This is the standard backend house-overlay technique used in synastry:
    each selected body or node from ``chart_source`` is assigned to a house in
    ``target_houses`` using the existing house membership doctrine.
    """

    include_nodes = _resolve_synastry_policy(policy).overlays.include_nodes if include_nodes is None else include_nodes
    if not isinstance(include_nodes, bool):
        raise ValueError("synastry overlay include_nodes must be boolean")
    _validate_label_pair(source_label, target_label)
    longitudes = chart_source.longitudes(include_nodes=include_nodes)
    placements = {
        name: assign_house(longitude, target_houses)
        for name, longitude in longitudes.items()
    }
    truth = SynastryOverlayTruth(
        source_label=source_label,
        target_label=target_label,
        include_nodes=include_nodes,
        point_count=len(placements),
        target_house_system=target_houses.system,
        target_effective_house_system=target_houses.effective_system,
        target_has_fallback=target_houses.fallback,
    )
    classification = _classify_overlay_truth(truth)
    relation = SynastryRelation(
        kind="house_overlay",
        basis="house_membership",
        source_label=source_label,
        target_label=target_label,
        source_ref=source_label,
        target_ref=target_label,
    )
    condition_profile = _build_overlay_condition_profile(
        SynastryHouseOverlay(
            source_label=source_label,
            target_label=target_label,
            placements=placements,
            include_nodes=include_nodes,
            computation_truth=truth,
            classification=classification,
            relation=relation,
        )
    )
    return SynastryHouseOverlay(
        source_label=source_label,
        target_label=target_label,
        placements=placements,
        include_nodes=include_nodes,
        computation_truth=truth,
        classification=classification,
        relation=relation,
        condition_profile=condition_profile,
    )


def mutual_house_overlays(
    chart_a: "Chart",
    houses_a: HouseCusps,
    chart_b: "Chart",
    houses_b: HouseCusps,
    *,
    include_nodes: bool | None = None,
    first_label: str = "A",
    second_label: str = "B",
    policy: SynastryComputationPolicy | None = None,
) -> MutualHouseOverlay:
    """Compute house overlays in both synastry directions."""

    _validate_label_pair(first_label, second_label)

    return MutualHouseOverlay(
        first_in_second=house_overlay(
            chart_a,
            houses_b,
            include_nodes=include_nodes,
            source_label=first_label,
            target_label=second_label,
            policy=policy,
        ),
        second_in_first=house_overlay(
            chart_b,
            houses_a,
            include_nodes=include_nodes,
            source_label=second_label,
            target_label=first_label,
            policy=policy,
        ),
    )


# ---------------------------------------------------------------------------
# Composite chart
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class CompositeChart:
    """
    RITE: The Midpoint Vessel — synthetic chart born of two lives merged.

    THEOREM: Holds the midpoint ecliptic longitudes of corresponding planetary
    positions from two natal charts, forming a synthetic composite chart.

    RITE OF PURPOSE:
        Serves the Synastry Engine as the primary data vessel for composite
        relationship charts. A composite chart does not correspond to any real
        moment in time; it represents the combined midpoint geometry of two
        natal charts. Without this vessel, composite chart data would have no
        structured home in the pillar.

    LAW OF OPERATION:
        Responsibilities:
            - Store midpoint planetary longitudes keyed by body name.
            - Store midpoint node longitudes keyed by node name.
            - Store optional midpoint house cusps and angles (ASC, MC).
            - Expose a flat ``longitudes()`` accessor for downstream aspect work.
        Non-responsibilities:
            - Does not compute midpoints (delegated to ``composite_chart``).
            - Does not cast a real chart (no ephemeris access).
            - Does not validate that midpoints are astronomically meaningful.
        Dependencies:
            - Populated exclusively by ``composite_chart()``.
        Structural invariants:
            - ``planets`` and ``nodes`` are always present (may be empty dicts).
            - ``cusps`` is an empty list when house data was not requested.
            - ``asc`` and ``mc`` are ``None`` when house data was not requested.
        Succession stance: terminal — not designed for subclassing.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.synastry.CompositeChart",
        "risk": "medium",
        "api": {
            "public_methods": ["longitudes"],
            "public_attributes": ["planets", "nodes", "cusps", "asc", "mc", "jd_mean"]
        },
        "state": {
            "mutable": false,
            "fields": ["planets", "nodes", "cusps", "asc", "mc", "jd_mean"]
        },
        "effects": {
            "io": [],
            "signals_emitted": [],
            "db_writes": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": [],
            "policy": "caller ensures valid midpoint data before construction"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]

    Attributes
    ----------
    planets   : body name → midpoint ecliptic longitude (°)
    nodes     : node name → midpoint ecliptic longitude (°)
    cusps     : 12 house cusp midpoints (°), or empty list if not computed
    asc       : midpoint ASC longitude (°), or None
    mc        : midpoint MC longitude (°), or None
    jd_mean   : arithmetic mean of the two natal Julian Days (for reference)
    """
    planets:  dict[str, float]
    nodes:    dict[str, float]
    cusps:    list[float]
    asc:      float | None
    mc:       float | None
    jd_mean:  float
    computation_truth: CompositeComputationTruth | None = None
    classification: CompositeClassification | None = None
    relation: SynastryRelation | None = None
    condition_profile: SynastryConditionProfile | None = None

    def __post_init__(self) -> None:
        if self.computation_truth is not None:
            if self.computation_truth.jd_mean != self.jd_mean:
                raise ValueError("computation_truth jd_mean must match composite chart")
            if self.computation_truth.includes_house_frame != bool(self.cusps):
                raise ValueError("computation_truth includes_house_frame must match composite house data")
            if self.computation_truth.includes_house_frame:
                if self.asc is None or self.mc is None:
                    raise ValueError("computation_truth with house frame requires composite asc and mc")
            elif self.asc is not None or self.mc is not None:
                raise ValueError("computation_truth without house frame requires composite asc and mc to be None")
        if self.classification is not None:
            if self.computation_truth is None:
                raise ValueError("composite classification requires computation_truth")
            if self.classification.chart_mode != "composite":
                raise ValueError("composite classification chart_mode must be composite")
            if self.classification.method != self.computation_truth.method:
                raise ValueError("composite classification method must match computation_truth")
            if self.classification.includes_house_frame != self.computation_truth.includes_house_frame:
                raise ValueError("composite classification includes_house_frame must match computation_truth")
        if self.relation is not None:
            if self.relation.kind != "relationship_chart":
                raise ValueError("composite relation kind must be relationship_chart")
            if self.computation_truth is None:
                raise ValueError("composite relation requires computation_truth")
            if self.relation.basis != _relation_basis_for_composite_method(self.computation_truth.method):
                raise ValueError("composite relation basis must match computation_truth method")
            if self.relation.method != self.computation_truth.method:
                raise ValueError("composite relation method must match computation_truth method")
        if self.condition_profile is not None:
            if self.condition_profile.result_kind != (self.chart_mode or "composite"):
                raise ValueError("composite condition profile result_kind must match classification")
            if self.condition_profile.relation_kind != (self.relation_kind or "relationship_chart"):
                raise ValueError("composite condition profile relation_kind must match relation")
            if self.condition_profile.relation_basis != (self.relation_basis or _relation_basis_for_composite_method(self.method or "midpoint")):
                raise ValueError("composite condition profile relation_basis must match relation")
            if self.condition_profile.method != self.method:
                raise ValueError("composite condition profile method must match composite method")
            if self.condition_profile.includes_house_frame != self.includes_house_frame:
                raise ValueError("composite condition profile includes_house_frame must match composite")

    def longitudes(self, include_nodes: bool = True) -> dict[str, float]:
        """Return flat dict body_name → composite longitude."""
        lons = dict(self.planets)
        if include_nodes:
            lons.update(self.nodes)
        return lons

    @property
    def chart_mode(self) -> str | None:
        return None if self.classification is None else self.classification.chart_mode

    @property
    def method(self) -> str | None:
        return None if self.classification is None else self.classification.method

    @property
    def includes_house_frame(self) -> bool:
        return False if self.classification is None else self.classification.includes_house_frame

    @property
    def reference_latitude(self) -> float | None:
        return None if self.computation_truth is None else self.computation_truth.reference_latitude

    @property
    def source_house_system(self) -> str | None:
        return None if self.computation_truth is None else self.computation_truth.source_house_system

    @property
    def source_effective_house_system(self) -> str | None:
        return None if self.computation_truth is None else self.computation_truth.source_effective_house_system

    @property
    def relation_kind(self) -> str | None:
        return None if self.relation is None else self.relation.kind

    @property
    def relation_basis(self) -> str | None:
        return None if self.relation is None else self.relation.basis

    @property
    def relation_method(self) -> str | None:
        return None if self.relation is None else self.relation.method

    @property
    def has_relation(self) -> bool:
        return self.relation is not None

    @property
    def condition_state(self) -> str | None:
        return None if self.condition_profile is None else self.condition_profile.condition_state.name


def composite_chart(
    chart_a: "Chart",
    chart_b: "Chart",
    houses_a: HouseCusps | None = None,
    houses_b: HouseCusps | None = None,
    policy: SynastryComputationPolicy | None = None,
) -> CompositeChart:
    """
    Build a Composite chart from two natal charts.

    Matching planets are combined via the shorter-arc midpoint.  If both
    sets of house cusps are supplied, composite house cusps are also computed.

    Parameters
    ----------
    chart_a / chart_b   : natal Chart instances
    houses_a / houses_b : optional natal HouseCusps for composite houses

    Returns
    -------
    CompositeChart instance
    """
    if (houses_a is None) != (houses_b is None):
        raise ValueError("composite chart requires both houses_a and houses_b or neither")

    # --- Planet midpoints ---
    planets: dict[str, float] = {}
    for name, pd_a in chart_a.planets.items():
        if name in chart_b.planets:
            planets[name] = _midpoint(pd_a.longitude, chart_b.planets[name].longitude)

    # --- Node midpoints ---
    nodes: dict[str, float] = {}
    for name, nd_a in chart_a.nodes.items():
        if name in chart_b.nodes:
            nodes[name] = _midpoint(nd_a.longitude, chart_b.nodes[name].longitude)

    # --- House cusp midpoints (optional) ---
    cusps: list[float] = []
    asc_mid: float | None = None
    mc_mid:  float | None = None

    if houses_a is not None and houses_b is not None:
        cusps = [
            _midpoint(houses_a.cusps[i], houses_b.cusps[i])
            for i in range(12)
        ]
        asc_mid = _midpoint(houses_a.asc, houses_b.asc)
        mc_mid  = _midpoint(houses_a.mc,  houses_b.mc)

    jd_mean = (chart_a.jd_ut + chart_b.jd_ut) / 2.0

    computation_truth = CompositeComputationTruth(
        method="midpoint",
        jd_mean=jd_mean,
        includes_house_frame=houses_a is not None and houses_b is not None,
        source_house_system=None if houses_a is None or houses_b is None else houses_a.system,
        source_effective_house_system=None if houses_a is None or houses_b is None else houses_a.effective_system,
    )
    classification = _classify_composite_truth(computation_truth)
    relation = SynastryRelation(
        kind="relationship_chart",
        basis="midpoint_composite",
        source_label="A",
        target_label="B",
        source_ref="A",
        target_ref="B",
        method="midpoint",
    )
    condition_profile = _build_composite_condition_profile(
        CompositeChart(
            planets=planets,
            nodes=nodes,
            cusps=cusps,
            asc=asc_mid,
            mc=mc_mid,
            jd_mean=jd_mean,
            computation_truth=computation_truth,
            classification=classification,
            relation=relation,
        )
    )
    return CompositeChart(
        planets=planets,
        nodes=nodes,
        cusps=cusps,
        asc=asc_mid,
        mc=mc_mid,
        jd_mean=jd_mean,
        computation_truth=computation_truth,
        classification=classification,
        relation=relation,
        condition_profile=condition_profile,
    )


def composite_chart_reference_place(
    chart_a: "Chart",
    chart_b: "Chart",
    houses_a: HouseCusps,
    houses_b: HouseCusps,
    reference_latitude: float,
    house_system: str | None = None,
    policy: SynastryComputationPolicy | None = None,
) -> CompositeChart:
    """
    Composite chart using midpoint planets and a reference-place house method.

    This follows the mainstream "reference place method" doctrine: planets and
    nodes use midpoint longitudes, while the house frame is derived from the
    composite MC/ARMC and a supplied reference latitude.
    """

    house_system = _resolve_synastry_policy(policy).composite.reference_place_house_system if house_system is None else house_system
    _validate_house_system_code(house_system)
    _validate_finite_coordinate(reference_latitude, "reference_latitude")
    composite = composite_chart(chart_a, chart_b, policy=policy)
    composite_mc = _midpoint(houses_a.mc, houses_b.mc)
    mean_obliquity = (chart_a.obliquity + chart_b.obliquity) / 2.0
    composite_armc, _ = ecliptic_to_equatorial(composite_mc, 0.0, mean_obliquity)
    composite_sun_lon = composite.planets.get(Body.SUN)
    houses = _synastry_houses_from_armc(
        armc=composite_armc,
        latitude=reference_latitude,
        obliquity=mean_obliquity,
        system=house_system,
        sun_lon=composite_sun_lon,
    )
    computation_truth = CompositeComputationTruth(
        method="reference_place",
        jd_mean=composite.jd_mean,
        includes_house_frame=True,
        reference_latitude=reference_latitude,
        house_system=house_system,
        composite_mc=composite_mc,
        composite_armc=composite_armc,
        source_house_system=houses_a.system,
        source_effective_house_system=houses_a.effective_system,
    )
    classification = _classify_composite_truth(computation_truth)
    relation = SynastryRelation(
        kind="relationship_chart",
        basis="reference_place_composite",
        source_label="A",
        target_label="B",
        source_ref="A",
        target_ref="B",
        method="reference_place",
    )
    condition_profile = _build_composite_condition_profile(
        CompositeChart(
            planets=composite.planets,
            nodes=composite.nodes,
            cusps=list(houses.cusps),
            asc=houses.asc,
            mc=houses.mc,
            jd_mean=composite.jd_mean,
            computation_truth=computation_truth,
            classification=classification,
            relation=relation,
        )
    )
    return CompositeChart(
        planets=composite.planets,
        nodes=composite.nodes,
        cusps=list(houses.cusps),
        asc=houses.asc,
        mc=houses.mc,
        jd_mean=composite.jd_mean,
        computation_truth=computation_truth,
        classification=classification,
        relation=relation,
        condition_profile=condition_profile,
    )


# ---------------------------------------------------------------------------
# Davison chart
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class DavisonInfo:
    """
    RITE: The Midpoint Witness — records the exact time and place of union.

    THEOREM: Holds the computed midpoint Julian Day, UTC datetime, and
    geographic coordinates used to cast a Davison relationship chart.

    RITE OF PURPOSE:
        Serves the Synastry Engine as a metadata vessel for the Davison chart
        construction. It preserves the midpoint time and location so callers
        can inspect or display the Davison chart's reference coordinates without
        re-deriving them from the original birth data.

    LAW OF OPERATION:
        Responsibilities:
            - Store the midpoint Julian Day (UT).
            - Store the midpoint UTC datetime.
            - Store the midpoint geographic latitude and longitude.
        Non-responsibilities:
            - Does not compute midpoints (delegated to ``davison_chart``).
            - Does not validate geographic coordinates.
        Dependencies:
            - Populated exclusively by ``davison_chart()``.
        Succession stance: terminal — not designed for subclassing.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.synastry.DavisonInfo",
        "risk": "low",
        "api": {
            "public_methods": [],
            "public_attributes": ["jd_midpoint", "datetime_utc", "latitude_midpoint", "longitude_midpoint"]
        },
        "state": {
            "mutable": false,
            "fields": ["jd_midpoint", "datetime_utc", "latitude_midpoint", "longitude_midpoint"]
        },
        "effects": {
            "io": [],
            "signals_emitted": [],
            "db_writes": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": [],
            "policy": "caller ensures valid midpoint data before construction"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]
    """
    jd_midpoint:        float
    datetime_utc:       datetime
    latitude_midpoint:  float
    longitude_midpoint: float
    computation_truth: DavisonComputationTruth | None = None
    classification: DavisonClassification | None = None
    relation: SynastryRelation | None = None
    condition_profile: SynastryConditionProfile | None = None

    def __post_init__(self) -> None:
        if self.computation_truth is not None:
            if self.computation_truth.used_jd != self.jd_midpoint:
                raise ValueError("computation_truth used_jd must match DavisonInfo.jd_midpoint")
            if self.computation_truth.latitude_midpoint != self.latitude_midpoint:
                raise ValueError("computation_truth latitude_midpoint must match DavisonInfo")
            if self.computation_truth.longitude_midpoint != self.longitude_midpoint:
                raise ValueError("computation_truth longitude_midpoint must match DavisonInfo")
        if self.classification is not None:
            if self.computation_truth is None:
                raise ValueError("Davison classification requires computation_truth")
            if self.classification.chart_mode != "davison":
                raise ValueError("Davison classification chart_mode must be davison")
            if self.classification.method != self.computation_truth.method:
                raise ValueError("Davison classification method must match computation_truth")
            if self.classification.latitude_mode != self.computation_truth.latitude_mode:
                raise ValueError("Davison classification latitude_mode must match computation_truth")
            if self.classification.longitude_mode != self.computation_truth.longitude_mode:
                raise ValueError("Davison classification longitude_mode must match computation_truth")
            expected_correction_mode = "corrected" if self.computation_truth.method == "corrected" else "uncorrected"
            if self.classification.correction_mode != expected_correction_mode:
                raise ValueError("Davison classification correction_mode must match computation_truth")
        if self.relation is not None:
            if self.relation.kind != "relationship_chart":
                raise ValueError("Davison relation kind must be relationship_chart")
            if self.computation_truth is None:
                raise ValueError("Davison relation requires computation_truth")
            if self.relation.basis != _relation_basis_for_davison_method(self.computation_truth.method):
                raise ValueError("Davison relation basis must match computation_truth method")
            if self.relation.method != self.computation_truth.method:
                raise ValueError("Davison relation method must match computation_truth method")
        if self.condition_profile is not None:
            if self.condition_profile.result_kind != (self.chart_mode or "davison"):
                raise ValueError("Davison condition profile result_kind must match classification")
            if self.condition_profile.relation_kind != (self.relation_kind or "relationship_chart"):
                raise ValueError("Davison condition profile relation_kind must match relation")
            if self.condition_profile.relation_basis != (self.relation_basis or _relation_basis_for_davison_method(self.method or "midpoint_location")):
                raise ValueError("Davison condition profile relation_basis must match relation")
            if self.condition_profile.method != self.method:
                raise ValueError("Davison condition profile method must match Davison method")

    @property
    def chart_mode(self) -> str | None:
        return None if self.classification is None else self.classification.chart_mode

    @property
    def method(self) -> str | None:
        return None if self.classification is None else self.classification.method

    @property
    def latitude_mode_name(self) -> str | None:
        return None if self.classification is None else self.classification.latitude_mode

    @property
    def longitude_mode_name(self) -> str | None:
        return None if self.classification is None else self.classification.longitude_mode

    @property
    def correction_mode(self) -> str | None:
        return None if self.classification is None else self.classification.correction_mode

    @property
    def is_corrected(self) -> bool:
        return False if self.classification is None else self.classification.correction_mode == "corrected"

    @property
    def relation_kind(self) -> str | None:
        return None if self.relation is None else self.relation.kind

    @property
    def relation_basis(self) -> str | None:
        return None if self.relation is None else self.relation.basis

    @property
    def relation_method(self) -> str | None:
        return None if self.relation is None else self.relation.method

    @property
    def has_relation(self) -> bool:
        return self.relation is not None

    @property
    def condition_state(self) -> str | None:
        return None if self.condition_profile is None else self.condition_profile.condition_state.name


@dataclass(slots=True)
class DavisonChart:
    """
    RITE: The Vessel of the Real Moment — a true chart born at the midpoint.

    THEOREM: Holds a real natal chart cast at the midpoint time and location
    between two people's birth data, together with its house cusps and
    midpoint metadata.

    RITE OF PURPOSE:
        Serves the Synastry Engine as the primary vessel for Davison relationship
        charts. Unlike the composite chart, the Davison chart corresponds to a
        real astronomical moment and can be interpreted like any natal chart.
        Without this vessel, the Davison chart's chart, houses, and metadata
        would have no unified home in the pillar.

    LAW OF OPERATION:
        Responsibilities:
            - Hold the natal ``Chart`` cast at the midpoint time.
            - Hold the ``HouseCusps`` computed at the midpoint time and location.
            - Hold the ``DavisonInfo`` metadata (midpoint JD, datetime, lat/lon).
        Non-responsibilities:
            - Does not compute the midpoint (delegated to ``davison_chart``).
            - Does not validate that the chart is astronomically consistent.
        Dependencies:
            - Populated exclusively by ``davison_chart()``.
            - ``chart`` is a ``moira.Chart`` instance from the package root.
        Succession stance: terminal — not designed for subclassing.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.synastry.DavisonChart",
        "risk": "medium",
        "api": {
            "public_methods": [],
            "public_attributes": ["chart", "houses", "info"]
        },
        "state": {
            "mutable": false,
            "fields": ["chart", "houses", "info"]
        },
        "effects": {
            "io": [],
            "signals_emitted": [],
            "db_writes": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": [],
            "policy": "caller ensures valid chart and info before construction"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]

    Attributes
    ----------
    chart  : natal Chart at the midpoint time
    houses : HouseCusps at midpoint time + location (None if no location given)
    info   : midpoint time and location details
    """
    chart:  "Chart"
    houses: HouseCusps | None
    info:   DavisonInfo

    def __post_init__(self) -> None:
        if self.info.computation_truth is not None:
            if self.chart.jd_ut != self.info.jd_midpoint:
                raise ValueError("Davison chart jd_ut must match info.jd_midpoint")
            if self.houses is not None and self.houses.system != self.info.computation_truth.house_system:
                raise ValueError("Davison houses system must match computation_truth")

    @property
    def chart_mode(self) -> str | None:
        return None if self.info.classification is None else self.info.classification.chart_mode

    @property
    def method(self) -> str | None:
        return None if self.info.classification is None else self.info.classification.method

    @property
    def correction_mode(self) -> str | None:
        return None if self.info.classification is None else self.info.classification.correction_mode

    @property
    def latitude_mode(self) -> str | None:
        return None if self.info.classification is None else self.info.classification.latitude_mode

    @property
    def longitude_mode(self) -> str | None:
        return None if self.info.classification is None else self.info.classification.longitude_mode

    @property
    def is_corrected(self) -> bool:
        return self.info.is_corrected


def _lon_midpoint(lon_a: float, lon_b: float) -> float:
    """Shorter-arc geographic longitude midpoint, handling antimeridian."""
    diff = abs(lon_a - lon_b)
    if diff > 180.0:
        # Shorter arc crosses the antimeridian — offset one side by 360° before averaging
        if lon_a < lon_b:
            lon_a += 360.0
        else:
            lon_b += 360.0
        mid = (lon_a + lon_b) / 2.0
        # Normalise to (-180, 180]
        if mid > 180.0:
            mid -= 360.0
        return mid
    return (lon_a + lon_b) / 2.0


def _lon_midpoint_uncorrected(lon_a: float, lon_b: float) -> float:
    """Arithmetic longitude midpoint used by uncorrected Davison doctrine."""

    mid = (lon_a + lon_b) / 2.0
    if mid <= -180.0:
        mid += 360.0
    elif mid > 180.0:
        mid -= 360.0
    return mid


def _spherical_geo_midpoint(
    lat_a: float,
    lon_a: float,
    lat_b: float,
    lon_b: float,
) -> tuple[float, float]:
    """Great-circle midpoint of two geographic coordinates on the unit sphere."""

    lat_a_r = lat_a * DEG2RAD
    lon_a_r = lon_a * DEG2RAD
    lat_b_r = lat_b * DEG2RAD
    lon_b_r = lon_b * DEG2RAD

    x_a = math.cos(lat_a_r) * math.cos(lon_a_r)
    y_a = math.cos(lat_a_r) * math.sin(lon_a_r)
    z_a = math.sin(lat_a_r)
    x_b = math.cos(lat_b_r) * math.cos(lon_b_r)
    y_b = math.cos(lat_b_r) * math.sin(lon_b_r)
    z_b = math.sin(lat_b_r)

    x = x_a + x_b
    y = y_a + y_b
    z = z_a + z_b
    hyp = math.hypot(x, y)
    lat_mid = math.atan2(z, hyp) * RAD2DEG
    lon_mid = math.atan2(y, x) * RAD2DEG
    if lon_mid <= -180.0:
        lon_mid += 360.0
    elif lon_mid > 180.0:
        lon_mid -= 360.0
    return lat_mid, lon_mid


def _build_relationship_chart(
    jd_ut: float,
    latitude: float,
    longitude: float,
    house_system: str,
    reader: SpkReader,
    computation_truth: DavisonComputationTruth | None = None,
) -> DavisonChart:
    """Build a real chart and house frame for one relationship-chart moment/place."""

    dt_mid = datetime_from_jd(jd_ut)
    planets = all_planets_at(jd_ut, reader=reader)
    nodes = {
        Body.TRUE_NODE: true_node(jd_ut, reader=reader),
        Body.MEAN_NODE: mean_node(jd_ut),
        Body.LILITH: mean_lilith(jd_ut),
    }
    year = dt_mid.year if dt_mid.year > -9999 else -9999
    dt_s = delta_t(float(year))
    obl = true_obliquity(jd_ut)

    from . import Chart

    chart = Chart(
        jd_ut=jd_ut,
        planets=planets,
        nodes=nodes,
        obliquity=obl,
        delta_t=dt_s,
    )
    houses = calculate_houses(jd_ut, latitude, longitude, house_system)
    classification = None if computation_truth is None else _classify_davison_truth(computation_truth)
    relation = None
    if computation_truth is not None:
        relation = SynastryRelation(
            kind="relationship_chart",
            basis=_relation_basis_for_davison_method(computation_truth.method),
            source_label="A",
            target_label="B",
            source_ref="A",
            target_ref="B",
            method=computation_truth.method,
        )
    condition_profile = None
    if computation_truth is not None:
        condition_profile = _build_davison_condition_profile(
            DavisonInfo(
                jd_midpoint=jd_ut,
                datetime_utc=dt_mid,
                latitude_midpoint=latitude,
                longitude_midpoint=longitude,
                computation_truth=computation_truth,
                classification=classification,
                relation=relation,
            )
        )
    info = DavisonInfo(
        jd_midpoint=jd_ut,
        datetime_utc=dt_mid,
        latitude_midpoint=latitude,
        longitude_midpoint=longitude,
        computation_truth=computation_truth,
        classification=classification,
        relation=relation,
        condition_profile=condition_profile,
    )
    return DavisonChart(chart=chart, houses=houses, info=info)


def _synastry_houses_from_armc(
    *,
    armc: float,
    latitude: float,
    obliquity: float,
    system: str,
    sun_lon: float | None = None,
) -> HouseCusps:
    """HouseCusps constructor for reference-place relationship-chart techniques."""

    active_policy = HousePolicy.default()
    critical_lat = 90.0 - obliquity
    polar = abs(latitude) >= critical_lat and system in _POLAR_SYSTEMS
    effective_system = system
    fallback = False
    fallback_reason: str | None = None

    if polar:
        if active_policy.polar_fallback == PolarFallbackPolicy.RAISE:
            raise ValueError("reference-place synastry houses hit polar fallback under strict policy")
        effective_system = HouseSystem.PORPHYRY
        fallback = True
        fallback_reason = "reference-place synastry houses fell back to Porphyry at critical latitude"
    elif system not in _KNOWN_SYSTEMS:
        if active_policy.unknown_system == UnknownSystemPolicy.RAISE:
            raise ValueError("reference-place synastry houses received unknown system under strict policy")
        effective_system = HouseSystem.PLACIDUS
        fallback = True
        fallback_reason = f"unknown system code {system!r}; fell back to Placidus"

    mc = _mc_from_armc(armc, obliquity, latitude)
    asc = _asc_from_armc(armc, obliquity, latitude)
    vertex = _asc_from_armc((armc + 90.0) % 360.0, obliquity, -latitude)
    anti_vertex = (vertex + 180.0) % 360.0

    if effective_system == HouseSystem.WHOLE_SIGN:
        cusps = _whole_sign(asc)
    elif effective_system == HouseSystem.EQUAL:
        cusps = _equal_house(asc)
    elif effective_system == HouseSystem.PORPHYRY:
        cusps = _porphyry(asc, mc)
    elif effective_system == HouseSystem.PLACIDUS:
        cusps = _placidus(armc, obliquity, latitude)
    elif effective_system == HouseSystem.KOCH:
        cusps = _koch(armc, obliquity, latitude)
    elif effective_system == HouseSystem.CAMPANUS:
        cusps = _campanus(armc, obliquity, latitude)
    elif effective_system == HouseSystem.REGIOMONTANUS:
        cusps = _regiomontanus(armc, obliquity, latitude)
    elif effective_system == HouseSystem.ALCABITIUS:
        cusps = _alcabitius(armc, obliquity, latitude)
    elif effective_system == HouseSystem.MORINUS:
        cusps = _morinus(armc, obliquity)
    elif effective_system == HouseSystem.TOPOCENTRIC:
        cusps = _topocentric(armc, obliquity, latitude)
    elif effective_system == HouseSystem.MERIDIAN:
        cusps = _meridian(armc, obliquity)
    elif effective_system == HouseSystem.VEHLOW:
        cusps = _vehlow(asc)
    elif effective_system == HouseSystem.SUNSHINE:
        if sun_lon is None:
            raise ValueError("Sunshine reference-place synastry houses require sun_lon")
        cusps = _sunshine(sun_lon, latitude, obliquity)
    elif effective_system == HouseSystem.AZIMUTHAL:
        cusps = _azimuthal(armc, obliquity, latitude)
    elif effective_system == HouseSystem.CARTER:
        cusps = _carter(armc, obliquity, latitude)
    elif effective_system == HouseSystem.PULLEN_SD:
        cusps = _pullen_sd(armc, obliquity, latitude)
    elif effective_system == HouseSystem.PULLEN_SR:
        cusps = _pullen_sr(armc, obliquity, latitude)
    elif effective_system == HouseSystem.KRUSINSKI:
        cusps = _krusinski(armc, obliquity, latitude)
    elif effective_system == HouseSystem.APC:
        cusps = _apc(armc, obliquity, latitude)
    else:
        cusps = _placidus(armc, obliquity, latitude)

    return HouseCusps(
        system=system,
        cusps=[c % 360.0 for c in cusps],
        asc=asc % 360.0,
        mc=mc % 360.0,
        armc=armc % 360.0,
        vertex=vertex % 360.0,
        anti_vertex=anti_vertex % 360.0,
        effective_system=effective_system,
        fallback=fallback,
        fallback_reason=fallback_reason,
        classification=classify_house_system(effective_system),
        policy=active_policy,
    )


def davison_chart(
    dt_a: datetime,
    lat_a: float,
    lon_a: float,
    dt_b: datetime,
    lat_b: float,
    lon_b: float,
    house_system: str | None = None,
    reader: SpkReader | None = None,
    policy: SynastryComputationPolicy | None = None,
) -> DavisonChart:
    """
    Calculate a Davison Relationship Chart.

    The chart is cast for the exact midpoint in both time and space.

    Parameters
    ----------
    dt_a / dt_b         : birth datetimes (timezone-aware; naïve = UTC)
    lat_a / lat_b       : geographic latitudes (°, north positive)
    lon_a / lon_b       : geographic longitudes (°, east positive)
    house_system        : house system for the Davison chart
    reader              : SpkReader instance (uses module singleton if None)

    Returns
    -------
    DavisonChart with chart, houses, and midpoint info.
    """
    if reader is None:
        reader = get_reader()
    house_system = _resolve_synastry_policy(policy).davison.default_house_system if house_system is None else house_system
    _validate_house_system_code(house_system)
    for value, name in ((lat_a, "lat_a"), (lon_a, "lon_a"), (lat_b, "lat_b"), (lon_b, "lon_b")):
        _validate_finite_coordinate(value, name)

    # Ensure UTC
    if dt_a.tzinfo is None:
        dt_a = dt_a.replace(tzinfo=timezone.utc)
    if dt_b.tzinfo is None:
        dt_b = dt_b.replace(tzinfo=timezone.utc)

    jd_a = jd_from_datetime(dt_a)
    jd_b = jd_from_datetime(dt_b)

    # Time midpoint
    jd_mid = (jd_a + jd_b) / 2.0
    dt_mid = datetime_from_jd(jd_mid)

    # Location midpoint
    lat_mid = (lat_a + lat_b) / 2.0
    lon_mid = _lon_midpoint(lon_a, lon_b)

    # Build chart at the midpoint using the same public chart-state logic
    # as the main engine: geocentric UT chart positions with Moira's standard
    # obliquity and Delta T fields.
    planets = all_planets_at(jd_mid, reader=reader)

    nodes = {
        Body.TRUE_NODE: true_node(jd_mid, reader=reader),
        Body.MEAN_NODE: mean_node(jd_mid),
        Body.LILITH:    mean_lilith(jd_mid),
    }

    year = dt_mid.year if dt_mid.year > -9999 else -9999
    dt_s = delta_t(float(year))
    obl = true_obliquity(jd_mid)

    # Import Chart here to avoid circular dependency at module level
    from . import Chart

    chart = Chart(
        jd_ut=jd_mid,
        planets=planets,
        nodes=nodes,
        obliquity=obl,
        delta_t=dt_s,
    )

    houses = calculate_houses(jd_mid, lat_mid, lon_mid, house_system)

    computation_truth = DavisonComputationTruth(
        method="midpoint_location",
        raw_midpoint_jd=jd_mid,
        used_jd=jd_mid,
        latitude_mode="arithmetic_midpoint",
        longitude_mode="shorter_arc_midpoint",
        latitude_midpoint=lat_mid,
        longitude_midpoint=lon_mid,
        house_system=house_system,
    )
    relation = SynastryRelation(
        kind="relationship_chart",
        basis="midpoint_location_davison",
        source_label="A",
        target_label="B",
        source_ref="A",
        target_ref="B",
        method="midpoint_location",
    )
    classification = _classify_davison_truth(computation_truth)
    condition_profile = _build_davison_condition_profile(
        DavisonInfo(
            jd_midpoint=jd_mid,
            datetime_utc=dt_mid,
            latitude_midpoint=lat_mid,
            longitude_midpoint=lon_mid,
            computation_truth=computation_truth,
            classification=classification,
            relation=relation,
        )
    )
    info = DavisonInfo(
        jd_midpoint=jd_mid,
        datetime_utc=dt_mid,
        latitude_midpoint=lat_mid,
        longitude_midpoint=lon_mid,
        computation_truth=computation_truth,
        classification=classification,
        relation=relation,
        condition_profile=condition_profile,
    )

    return DavisonChart(chart=chart, houses=houses, info=info)


def davison_chart_uncorrected(
    dt_a: datetime,
    lat_a: float,
    lon_a: float,
    dt_b: datetime,
    lat_b: float,
    lon_b: float,
    house_system: str | None = None,
    reader: SpkReader | None = None,
    policy: SynastryComputationPolicy | None = None,
) -> DavisonChart:
    """Davison chart using arithmetic midpoint time and arithmetic location."""

    if reader is None:
        reader = get_reader()
    house_system = _resolve_synastry_policy(policy).davison.default_house_system if house_system is None else house_system
    _validate_house_system_code(house_system)
    for value, name in ((lat_a, "lat_a"), (lon_a, "lon_a"), (lat_b, "lat_b"), (lon_b, "lon_b")):
        _validate_finite_coordinate(value, name)
    if dt_a.tzinfo is None:
        dt_a = dt_a.replace(tzinfo=timezone.utc)
    if dt_b.tzinfo is None:
        dt_b = dt_b.replace(tzinfo=timezone.utc)

    jd_mid = (jd_from_datetime(dt_a) + jd_from_datetime(dt_b)) / 2.0
    lat_mid = (lat_a + lat_b) / 2.0
    lon_mid = _lon_midpoint_uncorrected(lon_a, lon_b)
    return _build_relationship_chart(
        jd_mid,
        lat_mid,
        lon_mid,
        house_system,
        reader,
        computation_truth=DavisonComputationTruth(
            method="uncorrected",
            raw_midpoint_jd=jd_mid,
            used_jd=jd_mid,
            latitude_mode="arithmetic_midpoint",
            longitude_mode="arithmetic_midpoint",
            latitude_midpoint=lat_mid,
            longitude_midpoint=lon_mid,
            house_system=house_system,
        ),
    )


def davison_chart_reference_place(
    dt_a: datetime,
    dt_b: datetime,
    reference_latitude: float,
    reference_longitude: float,
    house_system: str | None = None,
    reader: SpkReader | None = None,
    policy: SynastryComputationPolicy | None = None,
) -> DavisonChart:
    """Davison chart using midpoint time and an explicit reference place."""

    if reader is None:
        reader = get_reader()
    house_system = _resolve_synastry_policy(policy).davison.default_house_system if house_system is None else house_system
    _validate_house_system_code(house_system)
    for value, name in ((reference_latitude, "reference_latitude"), (reference_longitude, "reference_longitude")):
        _validate_finite_coordinate(value, name)
    if dt_a.tzinfo is None:
        dt_a = dt_a.replace(tzinfo=timezone.utc)
    if dt_b.tzinfo is None:
        dt_b = dt_b.replace(tzinfo=timezone.utc)

    jd_mid = (jd_from_datetime(dt_a) + jd_from_datetime(dt_b)) / 2.0
    return _build_relationship_chart(
        jd_mid,
        reference_latitude,
        reference_longitude,
        house_system,
        reader,
        computation_truth=DavisonComputationTruth(
            method="reference_place",
            raw_midpoint_jd=jd_mid,
            used_jd=jd_mid,
            latitude_mode="reference_place",
            longitude_mode="reference_place",
            latitude_midpoint=reference_latitude,
            longitude_midpoint=reference_longitude,
            house_system=house_system,
        ),
    )


def davison_chart_spherical_midpoint(
    dt_a: datetime,
    lat_a: float,
    lon_a: float,
    dt_b: datetime,
    lat_b: float,
    lon_b: float,
    house_system: str | None = None,
    reader: SpkReader | None = None,
    policy: SynastryComputationPolicy | None = None,
) -> DavisonChart:
    """Davison chart using midpoint time and great-circle midpoint location."""

    if reader is None:
        reader = get_reader()
    house_system = _resolve_synastry_policy(policy).davison.default_house_system if house_system is None else house_system
    _validate_house_system_code(house_system)
    for value, name in ((lat_a, "lat_a"), (lon_a, "lon_a"), (lat_b, "lat_b"), (lon_b, "lon_b")):
        _validate_finite_coordinate(value, name)
    if dt_a.tzinfo is None:
        dt_a = dt_a.replace(tzinfo=timezone.utc)
    if dt_b.tzinfo is None:
        dt_b = dt_b.replace(tzinfo=timezone.utc)

    jd_mid = (jd_from_datetime(dt_a) + jd_from_datetime(dt_b)) / 2.0
    lat_mid, lon_mid = _spherical_geo_midpoint(lat_a, lon_a, lat_b, lon_b)
    return _build_relationship_chart(
        jd_mid,
        lat_mid,
        lon_mid,
        house_system,
        reader,
        computation_truth=DavisonComputationTruth(
            method="spherical_midpoint",
            raw_midpoint_jd=jd_mid,
            used_jd=jd_mid,
            latitude_mode="spherical_midpoint",
            longitude_mode="spherical_midpoint",
            latitude_midpoint=lat_mid,
            longitude_midpoint=lon_mid,
            house_system=house_system,
        ),
    )


def davison_chart_corrected(
    dt_a: datetime,
    lat_a: float,
    lon_a: float,
    dt_b: datetime,
    lat_b: float,
    lon_b: float,
    house_system: str | None = None,
    reader: SpkReader | None = None,
    policy: SynastryComputationPolicy | None = None,
) -> DavisonChart:
    """
    Davison chart with midpoint location and corrected time to preserve midpoint MC.

    The current embodied correction doctrine searches around the midpoint time
    until the cast chart's MC matches the midpoint of the two natal MCs.
    """

    if reader is None:
        reader = get_reader()
    house_system = _resolve_synastry_policy(policy).davison.default_house_system if house_system is None else house_system
    _validate_house_system_code(house_system)
    for value, name in ((lat_a, "lat_a"), (lon_a, "lon_a"), (lat_b, "lat_b"), (lon_b, "lon_b")):
        _validate_finite_coordinate(value, name)
    if dt_a.tzinfo is None:
        dt_a = dt_a.replace(tzinfo=timezone.utc)
    if dt_b.tzinfo is None:
        dt_b = dt_b.replace(tzinfo=timezone.utc)

    jd_a = jd_from_datetime(dt_a)
    jd_b = jd_from_datetime(dt_b)
    jd_mid = (jd_a + jd_b) / 2.0
    lat_mid = (lat_a + lat_b) / 2.0
    lon_mid = _lon_midpoint_uncorrected(lon_a, lon_b)
    houses_a = calculate_houses(jd_a, lat_a, lon_a, house_system)
    houses_b = calculate_houses(jd_b, lat_b, lon_b, house_system)
    target_mc = _midpoint(houses_a.mc, houses_b.mc)

    def _signed_diff(jd_value: float) -> float:
        mc = calculate_houses(jd_value, lat_mid, lon_mid, house_system).mc
        return ((mc - target_mc + 540.0) % 360.0) - 180.0

    bracket_left = jd_mid - 0.5
    left_diff = _signed_diff(bracket_left)
    right_jd = bracket_left
    right_diff = left_diff
    found_bracket = False
    for step in range(1, 145):
        probe = jd_mid - 0.5 + (step / 144.0)
        probe_diff = _signed_diff(probe)
        if left_diff == 0.0:
            right_jd = bracket_left
            right_diff = left_diff
            found_bracket = True
            break
        if left_diff * probe_diff <= 0.0:
            right_jd = probe
            right_diff = probe_diff
            found_bracket = True
            break
        bracket_left = probe
        left_diff = probe_diff

    corrected_jd = jd_mid
    if found_bracket:
        left_jd = bracket_left
        for _ in range(80):
            mid_probe = (left_jd + right_jd) / 2.0
            mid_diff = _signed_diff(mid_probe)
            if abs(mid_diff) < 1e-10:
                corrected_jd = mid_probe
                break
            if left_diff * mid_diff <= 0.0:
                right_jd = mid_probe
                right_diff = mid_diff
            else:
                left_jd = mid_probe
                left_diff = mid_diff
            corrected_jd = mid_probe

    return _build_relationship_chart(
        corrected_jd,
        lat_mid,
        lon_mid,
        house_system,
        reader,
        computation_truth=DavisonComputationTruth(
            method="corrected",
            raw_midpoint_jd=jd_mid,
            used_jd=corrected_jd,
            latitude_mode="arithmetic_midpoint",
            longitude_mode="arithmetic_midpoint",
            latitude_midpoint=lat_mid,
            longitude_midpoint=lon_mid,
            house_system=house_system,
            corrected_target_mc=target_mc,
            correction_applied=abs(corrected_jd - jd_mid) > 1e-12,
        ),
    )


def synastry_contact_relations(
    contacts: list[SynastryAspectContact],
) -> tuple[SynastryRelation, ...]:
    """Flatten the explicit relation layer from synastry contact vessels."""

    return tuple(contact.relation for contact in contacts if contact.relation is not None)


def mutual_overlay_relations(
    overlays: MutualHouseOverlay,
) -> tuple[SynastryRelation, ...]:
    """Flatten the explicit relation layer from a mutual overlay pair."""

    relations: list[SynastryRelation] = []
    if overlays.first_in_second.relation is not None:
        relations.append(overlays.first_in_second.relation)
    if overlays.second_in_first.relation is not None:
        relations.append(overlays.second_in_first.relation)
    return tuple(relations)


def synastry_condition_profiles(
    contacts: list[SynastryAspectContact],
) -> tuple[SynastryConditionProfile, ...]:
    """Flatten per-contact condition profiles from synastry contacts."""

    return tuple(contact.condition_profile for contact in contacts if contact.condition_profile is not None)


def synastry_chart_condition_profile(
    *,
    contacts: list[SynastryAspectContact] | None = None,
    overlays: MutualHouseOverlay | None = None,
    composite: CompositeChart | None = None,
    davison: DavisonChart | None = None,
) -> SynastryChartConditionProfile:
    """Aggregate current synastry condition profiles into one chart-wide vessel."""

    profiles: list[SynastryConditionProfile] = []
    if contacts is not None:
        profiles.extend(
            contact.condition_profile
            for contact in contacts
            if contact.condition_profile is not None
        )
    if overlays is not None:
        if overlays.first_in_second.condition_profile is not None:
            profiles.append(overlays.first_in_second.condition_profile)
        if overlays.second_in_first.condition_profile is not None:
            profiles.append(overlays.second_in_first.condition_profile)
    if composite is not None and composite.condition_profile is not None:
        profiles.append(composite.condition_profile)
    if davison is not None and davison.info.condition_profile is not None:
        profiles.append(davison.info.condition_profile)

    ordered_profiles = tuple(sorted(profiles, key=_synastry_condition_sort_key))
    if ordered_profiles:
        strongest_rank = max(_synastry_condition_strength(profile) for profile in ordered_profiles)
        weakest_rank = min(_synastry_condition_strength(profile) for profile in ordered_profiles)
        strongest_profiles = tuple(
            profile for profile in ordered_profiles
            if _synastry_condition_strength(profile) == strongest_rank
        )
        weakest_profiles = tuple(
            profile for profile in ordered_profiles
            if _synastry_condition_strength(profile) == weakest_rank
        )
    else:
        strongest_profiles = ()
        weakest_profiles = ()

    return SynastryChartConditionProfile(
        profiles=ordered_profiles,
        contact_count=sum(1 for profile in ordered_profiles if profile.condition_state.name == "contact"),
        overlay_count=sum(1 for profile in ordered_profiles if profile.condition_state.name == "overlay"),
        relationship_chart_count=sum(1 for profile in ordered_profiles if profile.condition_state.name == "relationship_chart"),
        strongest_profiles=strongest_profiles,
        weakest_profiles=weakest_profiles,
    )


def synastry_condition_network_profile(
    *,
    contacts: list[SynastryAspectContact] | None = None,
    overlays: MutualHouseOverlay | None = None,
    composite: CompositeChart | None = None,
    davison: DavisonChart | None = None,
) -> SynastryConditionNetworkProfile:
    """Project current synastry relations into a small directed condition network."""

    pair_ids = {"pair:A", "pair:B"}
    body_ids: set[str] = set()
    chart_ids: set[str] = set()
    edges: list[SynastryConditionNetworkEdge] = []

    if contacts is not None:
        for contact in contacts:
            if contact.relation is None or contact.condition_profile is None:
                continue
            source_id = f"body:{contact.relation.source_ref}"
            target_id = f"body:{contact.relation.target_ref}"
            body_ids.update((source_id, target_id))
            edges.append(SynastryConditionNetworkEdge(
                source_id=source_id,
                target_id=target_id,
                relation_kind=contact.relation.kind,
                relation_basis=contact.relation.basis,
                condition_state=contact.condition_profile.condition_state.name,
            ))

    if overlays is not None:
        for overlay in (overlays.first_in_second, overlays.second_in_first):
            if overlay.relation is None or overlay.condition_profile is None:
                continue
            source_id = f"pair:{overlay.source_label}"
            target_id = f"pair:{overlay.target_label}"
            pair_ids.update((source_id, target_id))
            edges.append(SynastryConditionNetworkEdge(
                source_id=source_id,
                target_id=target_id,
                relation_kind=overlay.relation.kind,
                relation_basis=overlay.relation.basis,
                condition_state=overlay.condition_profile.condition_state.name,
            ))

    if composite is not None and composite.relation is not None and composite.condition_profile is not None:
        chart_id = f"chart:composite:{composite.relation.method or 'midpoint'}"
        chart_ids.add(chart_id)
        edges.append(SynastryConditionNetworkEdge(
            source_id="pair:A",
            target_id=chart_id,
            relation_kind=composite.relation.kind,
            relation_basis=composite.relation.basis,
            condition_state=composite.condition_profile.condition_state.name,
        ))
        edges.append(SynastryConditionNetworkEdge(
            source_id="pair:B",
            target_id=chart_id,
            relation_kind=composite.relation.kind,
            relation_basis=composite.relation.basis,
            condition_state=composite.condition_profile.condition_state.name,
        ))

    if davison is not None and davison.info.relation is not None and davison.info.condition_profile is not None:
        chart_id = f"chart:davison:{davison.info.relation.method or 'midpoint_location'}"
        chart_ids.add(chart_id)
        edges.append(SynastryConditionNetworkEdge(
            source_id="pair:A",
            target_id=chart_id,
            relation_kind=davison.info.relation.kind,
            relation_basis=davison.info.relation.basis,
            condition_state=davison.info.condition_profile.condition_state.name,
        ))
        edges.append(SynastryConditionNetworkEdge(
            source_id="pair:B",
            target_id=chart_id,
            relation_kind=davison.info.relation.kind,
            relation_basis=davison.info.relation.basis,
            condition_state=davison.info.condition_profile.condition_state.name,
        ))

    ordered_edges = tuple(sorted(
        edges,
        key=lambda edge: (edge.source_id, edge.target_id, edge.relation_kind, edge.relation_basis, edge.condition_state),
    ))
    all_node_ids = sorted(pair_ids | body_ids | chart_ids)
    incoming = {node_id: 0 for node_id in all_node_ids}
    outgoing = {node_id: 0 for node_id in all_node_ids}
    for edge in ordered_edges:
        outgoing[edge.source_id] += 1
        incoming[edge.target_id] += 1

    def _kind_for_node(node_id: str) -> str:
        if node_id.startswith("pair:"):
            return "pair"
        if node_id.startswith("body:"):
            return "body"
        return "chart"

    ordered_nodes = tuple(
        sorted(
            (
                SynastryConditionNetworkNode(
                    node_id=node_id,
                    kind=_kind_for_node(node_id),
                    incoming_count=incoming[node_id],
                    outgoing_count=outgoing[node_id],
                )
                for node_id in all_node_ids
            ),
            key=lambda node: (node.kind, node.node_id),
        )
    )

    if ordered_nodes:
        max_degree = max(node.total_degree for node in ordered_nodes)
        most_connected_nodes = tuple(node for node in ordered_nodes if node.total_degree == max_degree)
    else:
        most_connected_nodes = ()

    return SynastryConditionNetworkProfile(
        nodes=ordered_nodes,
        edges=ordered_edges,
        isolated_nodes=tuple(node for node in ordered_nodes if node.total_degree == 0),
        most_connected_nodes=most_connected_nodes,
    )
