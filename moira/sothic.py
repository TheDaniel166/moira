"""
Sothic Cycle Engine — moira/sothic.py

Archetype: Engine
Purpose: Computes the heliacal rising of Sirius year by year, tracks its
         drift through the ancient Egyptian civil calendar, detects Sothic
         epochs (years of calendar realignment), and converts Julian Days
         to Egyptian civil calendar dates — all anchored to the historically
         confirmed 139 AD Sothic epoch of Censorinus.

Boundary declaration:
    Owns: Egyptian civil calendar arithmetic, Sothic drift computation,
          epoch detection, drift-rate regression, and the EgyptianDate,
          SothicEntry, and SothicEpoch result types.
    Delegates: heliacal rising computation to
               moira.fixed_stars.heliacal_rising; Julian Day arithmetic to
               moira.julian (julian_day, calendar_from_jd,
               calendar_datetime_from_jd, safe_datetime_from_jd).

Import-time side effects: None

External dependency assumptions:
    - moira.fixed_stars.heliacal_rising("Sirius", jd_start, lat, lon,
      arcus_visionis, search_days) returns a float JD or None.
    - moira.julian.julian_day(year, month, day, hour) returns a JD float.
    - moira.julian.safe_datetime_from_jd returns None for out-of-range JDs
      rather than raising.

Public surface / exports:
    EgyptianDate              — civil calendar date in the Egyptian year
    SothicEntry               — heliacal rising record for one year
    SothicEpoch               — a year of Sothic calendar realignment
    EGYPTIAN_MONTHS           — ordered list of 13 month names
    EGYPTIAN_SEASONS          — season → month-name mapping
    EPAGOMENAL_BIRTHS         — deities born on the 5 intercalary days
    HISTORICAL_SOTHIC_EPOCHS  — known/inferred epoch records
    egyptian_civil_date()     — convert JD to EgyptianDate
    days_from_1_thoth()       — fractional days elapsed since 1 Thoth
    sothic_rising()           — year-by-year heliacal rising table
    sothic_epochs()           — years of Sothic calendar realignment
    sothic_drift_rate()       — observed drift rate in days/year
    predicted_sothic_epoch_year() — forward/backward epoch prediction
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .julian import (
    julian_day,
    calendar_from_jd,
    calendar_datetime_from_jd,
    safe_datetime_from_jd,
)
from .stars import heliacal_rising as _heliacal_rising


__all__ = [
    # Policy
    "SothicCalendarPolicy", "SothicHeliacalPolicy", "SothicEpochPolicy",
    "SothicPredictionPolicy", "SothicComputationPolicy",
    # Truth / Classification
    "EgyptianCalendarTruth", "SothicComputationTruth",
    "EgyptianCalendarClassification", "SothicComputationClassification",
    # Condition vessels
    "SothicRelation", "SothicConditionState", "SothicConditionProfile",
    "SothicChartConditionProfile",
    "SothicConditionNetworkNode", "SothicConditionNetworkEdge",
    "SothicConditionNetworkProfile",
    # Data types
    "EgyptianDate", "SothicEntry", "SothicEpoch",
    # Constants
    "EGYPTIAN_MONTHS", "EGYPTIAN_SEASONS", "EPAGOMENAL_BIRTHS",
    "HISTORICAL_SOTHIC_EPOCHS",
    # Functions
    "sothic_rising", "sothic_epochs", "sothic_drift_rate",
    "egyptian_civil_date", "days_from_1_thoth", "predicted_sothic_epoch_year",
    "sothic_chart_condition_profile", "sothic_condition_network_profile",
]


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Censorinus epoch: heliacal rising = 1 Thoth, July 20, 139 AD.
# In Moira's JD/calendar conventions, midnight at the start of 139-07-20
# corresponds to JD 1772027.5.
_SOTHIC_EPOCH_139_JD: float = 1772027.5

# Length of the Egyptian civil year (exactly 365 days, no leap)
_EGYPTIAN_YEAR_DAYS: int = 365

# Sothic cycle: 1460 Julian years = 1461 Egyptian civil years = 533265 Julian days
# Identity: 1460 × 365.25 = 533265 = 1461 × 365  (exact)
_SOTHIC_CYCLE_YEARS: float = 1460.0
_SOTHIC_CYCLE_DAYS:  float = 533_265.0

# Egyptian month names in order (12 × 30 days + 5 epagomenal)
EGYPTIAN_MONTHS: list[str] = [
    "Thoth", "Phaophi", "Athyr", "Choiak",      # Akhet (Inundation)
    "Tybi", "Mechir", "Phamenoth", "Pharmuthi",  # Peret (Emergence)
    "Pachon", "Payni", "Epiphi", "Mesore",       # Shemu (Harvest)
    "Epagomenal",                                 # 5 intercalary days
]

EGYPTIAN_SEASONS: dict[str, list[str]] = {
    "Akhet":      ["Thoth", "Phaophi", "Athyr", "Choiak"],
    "Peret":      ["Tybi", "Mechir", "Phamenoth", "Pharmuthi"],
    "Shemu":      ["Pachon", "Payni", "Epiphi", "Mesore"],
    "Epagomenal": ["Epagomenal"],
}

# Births associated with the 5 epagomenal days (Plutarch, De Iside)
EPAGOMENAL_BIRTHS: list[str] = [
    "Osiris", "Arueris (Elder Horus)", "Set", "Isis", "Nephthys"
]


# ---------------------------------------------------------------------------
# Explicit doctrine / policy
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SothicCalendarPolicy:
    """Policy surface for the current Egyptian civil calendar anchor doctrine."""

    epoch_jd: float = _SOTHIC_EPOCH_139_JD


@dataclass(frozen=True, slots=True)
class SothicHeliacalPolicy:
    """Policy surface for the currently embodied Sirius heliacal search doctrine."""

    arcus_visionis: float = 10.0
    search_days: int = 400


@dataclass(frozen=True, slots=True)
class SothicEpochPolicy:
    """Policy surface for epoch-detection tolerance doctrine."""

    tolerance_days: float = 1.0


@dataclass(frozen=True, slots=True)
class SothicPredictionPolicy:
    """Policy surface for the current Sothic cycle-length assumption."""

    cycle_length_years: float = _SOTHIC_CYCLE_YEARS


@dataclass(frozen=True, slots=True)
class SothicComputationPolicy:
    """Lean doctrine vessel for the current Sothic backend."""

    calendar: SothicCalendarPolicy = field(default_factory=SothicCalendarPolicy)
    heliacal: SothicHeliacalPolicy = field(default_factory=SothicHeliacalPolicy)
    epoch: SothicEpochPolicy = field(default_factory=SothicEpochPolicy)
    prediction: SothicPredictionPolicy = field(default_factory=SothicPredictionPolicy)


DEFAULT_SOTHIC_POLICY = SothicComputationPolicy()


def _resolve_sothic_policy(policy: SothicComputationPolicy | None) -> SothicComputationPolicy:
    return DEFAULT_SOTHIC_POLICY if policy is None else policy


def _validate_sothic_policy(policy: SothicComputationPolicy) -> None:
    if not isinstance(policy, SothicComputationPolicy):
        raise ValueError("sothic policy must be a SothicComputationPolicy")
    if not isinstance(policy.calendar, SothicCalendarPolicy):
        raise ValueError("sothic calendar policy must be a SothicCalendarPolicy")
    if not isinstance(policy.heliacal, SothicHeliacalPolicy):
        raise ValueError("sothic heliacal policy must be a SothicHeliacalPolicy")
    if not isinstance(policy.epoch, SothicEpochPolicy):
        raise ValueError("sothic epoch policy must be a SothicEpochPolicy")
    if not isinstance(policy.prediction, SothicPredictionPolicy):
        raise ValueError("sothic prediction policy must be a SothicPredictionPolicy")
    if not math.isfinite(policy.calendar.epoch_jd):
        raise ValueError("sothic calendar policy epoch_jd must be finite")
    if not math.isfinite(policy.heliacal.arcus_visionis) or policy.heliacal.arcus_visionis <= 0:
        raise ValueError("sothic heliacal policy arcus_visionis must be positive")
    if not isinstance(policy.heliacal.search_days, int) or policy.heliacal.search_days <= 0:
        raise ValueError("sothic heliacal policy search_days must be a positive integer")
    if not math.isfinite(policy.epoch.tolerance_days) or policy.epoch.tolerance_days < 0:
        raise ValueError("sothic epoch policy tolerance_days must be non-negative")
    if not math.isfinite(policy.prediction.cycle_length_years) or policy.prediction.cycle_length_years <= 0:
        raise ValueError("sothic prediction policy cycle_length_years must be positive")


# ---------------------------------------------------------------------------
# Truth preservation
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class EgyptianCalendarTruth:
    """Preserve the modular civil-calendar path used to derive an EgyptianDate."""

    jd: float
    epoch_jd: float
    elapsed_days: float
    wrapped_day_index: int

    def __post_init__(self) -> None:
        if not math.isfinite(self.jd):
            raise ValueError("egyptian calendar truth jd must be finite")
        if not math.isfinite(self.epoch_jd):
            raise ValueError("egyptian calendar truth epoch_jd must be finite")
        if not math.isfinite(self.elapsed_days):
            raise ValueError("egyptian calendar truth elapsed_days must be finite")
        if not 0 <= self.wrapped_day_index < _EGYPTIAN_YEAR_DAYS:
            raise ValueError("egyptian calendar truth wrapped_day_index must be within the civil year")


@dataclass(slots=True)
class SothicComputationTruth:
    """Preserve the doctrinal and delegated computation path for one Sothic result."""

    star_name: str
    latitude: float
    longitude: float
    epoch_jd: float
    arcus_visionis: float
    search_days: int
    jd_start: float
    jd_rising: float
    drift_days: float
    cycle_position: float | None = None
    tolerance_days: float | None = None

    def __post_init__(self) -> None:
        if self.star_name != "Sirius":
            raise ValueError("sothic computation truth star_name must be Sirius")
        for field_name, value in (
            ("latitude", self.latitude),
            ("longitude", self.longitude),
            ("epoch_jd", self.epoch_jd),
            ("arcus_visionis", self.arcus_visionis),
            ("jd_start", self.jd_start),
            ("jd_rising", self.jd_rising),
            ("drift_days", self.drift_days),
        ):
            if not math.isfinite(value):
                raise ValueError(f"sothic computation truth {field_name} must be finite")
        if not -90.0 <= self.latitude <= 90.0:
            raise ValueError("sothic computation truth latitude must be between -90 and 90 degrees")
        if not -180.0 <= self.longitude <= 180.0:
            raise ValueError("sothic computation truth longitude must be between -180 and 180 degrees")
        if self.arcus_visionis <= 0:
            raise ValueError("sothic computation truth arcus_visionis must be positive")
        if self.search_days <= 0:
            raise ValueError("sothic computation truth search_days must be positive")
        if self.cycle_position is not None:
            if not math.isfinite(self.cycle_position):
                raise ValueError("sothic computation truth cycle_position must be finite")
            if not 0.0 <= self.cycle_position < _SOTHIC_CYCLE_YEARS:
                raise ValueError("sothic computation truth cycle_position must be within the Sothic cycle")
        if self.tolerance_days is not None:
            if not math.isfinite(self.tolerance_days):
                raise ValueError("sothic computation truth tolerance_days must be finite")
            if self.tolerance_days < 0:
                raise ValueError("sothic computation truth tolerance_days must be non-negative")


@dataclass(slots=True)
class EgyptianCalendarClassification:
    """Typed descriptive classification derived from Egyptian calendar truth."""

    calendar_kind: str
    wrap_kind: str

    def __post_init__(self) -> None:
        if self.calendar_kind != "egyptian_civil":
            raise ValueError("egyptian calendar classification calendar_kind must be egyptian_civil")
        if self.wrap_kind != "mod_365":
            raise ValueError("egyptian calendar classification wrap_kind must be mod_365")


@dataclass(slots=True)
class SothicComputationClassification:
    """Typed descriptive classification derived from Sothic computation truth."""

    result_kind: str
    star_kind: str
    detection_kind: str
    tolerance_mode: str

    def __post_init__(self) -> None:
        if self.result_kind not in {"sothic_rising", "sothic_epoch"}:
            raise ValueError("sothic computation classification result_kind must be supported")
        if self.star_kind != "sirius_heliacal":
            raise ValueError("sothic computation classification star_kind must be sirius_heliacal")
        if self.detection_kind != "delegated_heliacal_rising":
            raise ValueError("sothic computation classification detection_kind must be delegated_heliacal_rising")
        if self.tolerance_mode not in {"none", "epoch_tolerance"}:
            raise ValueError("sothic computation classification tolerance_mode must be supported")


def _classify_egyptian_calendar_truth(truth: EgyptianCalendarTruth) -> EgyptianCalendarClassification:
    return EgyptianCalendarClassification(
        calendar_kind="egyptian_civil",
        wrap_kind="mod_365",
    )


def _classify_sothic_computation_truth(truth: SothicComputationTruth) -> SothicComputationClassification:
    return SothicComputationClassification(
        result_kind="sothic_epoch" if truth.tolerance_days is not None else "sothic_rising",
        star_kind="sirius_heliacal",
        detection_kind="delegated_heliacal_rising",
        tolerance_mode="epoch_tolerance" if truth.tolerance_days is not None else "none",
    )


@dataclass(slots=True)
class SothicRelation:
    """Explicit relation truth derived from the current Sothic backend."""

    kind: str
    basis: str
    anchor: str
    star_name: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in {"egyptian_calendar", "sothic_rising", "sothic_epoch"}:
            raise ValueError("sothic relation kind must be supported")
        if self.anchor != "censorinus_139_epoch":
            raise ValueError("sothic relation anchor must be censorinus_139_epoch")
        if self.kind == "egyptian_calendar":
            if self.basis != "civil_calendar_anchor":
                raise ValueError("egyptian calendar relation basis must be civil_calendar_anchor")
            if self.star_name is not None:
                raise ValueError("egyptian calendar relation must not preserve star_name")
        else:
            if self.basis != "sirius_heliacal_rising":
                raise ValueError("sothic star relation basis must be sirius_heliacal_rising")
            if self.star_name != "Sirius":
                raise ValueError("sothic star relation must preserve Sirius")

    @property
    def is_calendar_relation(self) -> bool:
        return self.kind == "egyptian_calendar"

    @property
    def is_sothic_rising_relation(self) -> bool:
        return self.kind == "sothic_rising"

    @property
    def is_sothic_epoch_relation(self) -> bool:
        return self.kind == "sothic_epoch"


def _build_egyptian_date_relation(_: "EgyptianDate") -> SothicRelation:
    return SothicRelation(
        kind="egyptian_calendar",
        basis="civil_calendar_anchor",
        anchor="censorinus_139_epoch",
    )


def _build_sothic_entry_relation(_: "SothicEntry") -> SothicRelation:
    return SothicRelation(
        kind="sothic_rising",
        basis="sirius_heliacal_rising",
        anchor="censorinus_139_epoch",
        star_name="Sirius",
    )


def _build_sothic_epoch_relation(_: "SothicEpoch") -> SothicRelation:
    return SothicRelation(
        kind="sothic_epoch",
        basis="sirius_heliacal_rising",
        anchor="censorinus_139_epoch",
        star_name="Sirius",
    )


@dataclass(slots=True)
class SothicConditionState:
    """Structural condition state for one Sothic result vessel."""

    name: str

    def __post_init__(self) -> None:
        if self.name not in {"calendar_anchor", "annual_rising", "epoch_alignment"}:
            raise ValueError("sothic condition state must be supported")


@dataclass(slots=True)
class SothicConditionProfile:
    """Integrated per-result Sothic condition profile derived from existing truth."""

    result_kind: str
    condition_state: SothicConditionState
    relation_kind: str
    relation_basis: str
    star_kind: str | None = None
    tolerance_mode: str | None = None

    def __post_init__(self) -> None:
        if self.result_kind not in {"egyptian_date", "sothic_entry", "sothic_epoch"}:
            raise ValueError("sothic condition profile result_kind must be supported")
        if self.condition_state.name == "calendar_anchor" and self.relation_kind != "egyptian_calendar":
            raise ValueError("calendar-anchor profile must use egyptian_calendar relation")
        if self.condition_state.name == "annual_rising" and self.relation_kind != "sothic_rising":
            raise ValueError("annual-rising profile must use sothic_rising relation")
        if self.condition_state.name == "epoch_alignment" and self.relation_kind != "sothic_epoch":
            raise ValueError("epoch-alignment profile must use sothic_epoch relation")
        if self.result_kind in {"sothic_entry", "sothic_epoch"} and self.star_kind != "sirius_heliacal":
            raise ValueError("sothic star profiles must preserve sirius_heliacal star_kind")
        if self.result_kind == "egyptian_date" and self.star_kind is not None:
            raise ValueError("egyptian date condition profile must not preserve star_kind")


def _build_egyptian_date_condition_profile(_: "EgyptianDate") -> SothicConditionProfile:
    return SothicConditionProfile(
        result_kind="egyptian_date",
        condition_state=SothicConditionState("calendar_anchor"),
        relation_kind="egyptian_calendar",
        relation_basis="civil_calendar_anchor",
    )


def _build_sothic_entry_condition_profile(entry: "SothicEntry") -> SothicConditionProfile:
    return SothicConditionProfile(
        result_kind="sothic_entry",
        condition_state=SothicConditionState("annual_rising"),
        relation_kind="sothic_rising",
        relation_basis="sirius_heliacal_rising",
        star_kind=entry.star_kind,
        tolerance_mode=entry.tolerance_mode,
    )


def _build_sothic_epoch_condition_profile(epoch: "SothicEpoch") -> SothicConditionProfile:
    return SothicConditionProfile(
        result_kind="sothic_epoch",
        condition_state=SothicConditionState("epoch_alignment"),
        relation_kind="sothic_epoch",
        relation_basis="sirius_heliacal_rising",
        star_kind=epoch.star_kind,
        tolerance_mode=epoch.tolerance_mode,
    )


def _sothic_condition_strength(profile: SothicConditionProfile) -> int:
    ranks = {
        "calendar_anchor": 0,
        "annual_rising": 1,
        "epoch_alignment": 2,
    }
    return ranks[profile.condition_state.name]


def _sothic_condition_sort_key(profile: SothicConditionProfile) -> tuple[object, ...]:
    return (
        profile.condition_state.name,
        profile.result_kind,
        profile.relation_kind,
        profile.relation_basis,
        profile.star_kind or "",
        profile.tolerance_mode or "",
    )


@dataclass(slots=True)
class SothicChartConditionProfile:
    """Chart-wide Sothic condition aggregate built from per-result profiles."""

    profiles: tuple[SothicConditionProfile, ...]
    calendar_anchor_count: int
    annual_rising_count: int
    epoch_alignment_count: int
    strongest_profiles: tuple[SothicConditionProfile, ...]
    weakest_profiles: tuple[SothicConditionProfile, ...]

    def __post_init__(self) -> None:
        expected_profiles = tuple(sorted(self.profiles, key=_sothic_condition_sort_key))
        if self.profiles != expected_profiles:
            raise ValueError("sothic chart condition profiles must be deterministically ordered")
        if self.calendar_anchor_count != sum(1 for p in self.profiles if p.condition_state.name == "calendar_anchor"):
            raise ValueError("sothic chart calendar_anchor_count must match profiles")
        if self.annual_rising_count != sum(1 for p in self.profiles if p.condition_state.name == "annual_rising"):
            raise ValueError("sothic chart annual_rising_count must match profiles")
        if self.epoch_alignment_count != sum(1 for p in self.profiles if p.condition_state.name == "epoch_alignment"):
            raise ValueError("sothic chart epoch_alignment_count must match profiles")
        if len(self.profiles) != self.calendar_anchor_count + self.annual_rising_count + self.epoch_alignment_count:
            raise ValueError("sothic chart profile counts must sum to profile total")
        if self.profiles:
            strongest_rank = max(_sothic_condition_strength(p) for p in self.profiles)
            weakest_rank = min(_sothic_condition_strength(p) for p in self.profiles)
            expected_strongest = tuple(p for p in self.profiles if _sothic_condition_strength(p) == strongest_rank)
            expected_weakest = tuple(p for p in self.profiles if _sothic_condition_strength(p) == weakest_rank)
        else:
            expected_strongest = ()
            expected_weakest = ()
        if self.strongest_profiles != expected_strongest:
            raise ValueError("sothic chart strongest_profiles must match derived ranking")
        if self.weakest_profiles != expected_weakest:
            raise ValueError("sothic chart weakest_profiles must match derived ranking")

    @property
    def profile_count(self) -> int:
        return len(self.profiles)


def _sothic_network_node_sort_key(node: "SothicConditionNetworkNode") -> tuple[str, str]:
    return (node.kind, node.node_id)


def _sothic_network_edge_sort_key(edge: "SothicConditionNetworkEdge") -> tuple[str, str, str, str, str]:
    return (
        edge.source_id,
        edge.target_id,
        edge.relation_kind,
        edge.relation_basis,
        edge.condition_state,
    )


@dataclass(slots=True)
class SothicConditionNetworkNode:
    """Deterministic node in the derived Sothic condition network."""

    node_id: str
    kind: str
    incoming_count: int
    outgoing_count: int

    def __post_init__(self) -> None:
        if self.kind not in {"anchor", "star", "date", "entry", "epoch"}:
            raise ValueError("sothic network node kind must be supported")
        expected_prefix = f"{self.kind}:"
        if not self.node_id.startswith(expected_prefix):
            raise ValueError("sothic network node_id must use the kind prefix")
        if self.incoming_count < 0 or self.outgoing_count < 0:
            raise ValueError("sothic network node counts must be non-negative")

    @property
    def total_degree(self) -> int:
        return self.incoming_count + self.outgoing_count


@dataclass(frozen=True, slots=True)
class SothicConditionNetworkEdge:
    """Directed edge derived from existing Sothic relation and condition truth."""

    source_id: str
    target_id: str
    relation_kind: str
    relation_basis: str
    condition_state: str

    def __post_init__(self) -> None:
        if self.relation_kind not in {"egyptian_calendar", "sothic_rising", "sothic_epoch"}:
            raise ValueError("sothic network edge relation_kind must be supported")
        if self.relation_basis not in {"civil_calendar_anchor", "sirius_heliacal_rising"}:
            raise ValueError("sothic network edge relation_basis must be supported")
        if self.condition_state not in {"calendar_anchor", "annual_rising", "epoch_alignment"}:
            raise ValueError("sothic network edge condition_state must be supported")
        if self.relation_kind == "egyptian_calendar":
            if not self.source_id.startswith("anchor:") or not self.target_id.startswith("date:"):
                raise ValueError("egyptian calendar edges must run from anchor nodes to date nodes")
            if self.relation_basis != "civil_calendar_anchor" or self.condition_state != "calendar_anchor":
                raise ValueError("egyptian calendar edges must preserve calendar-anchor doctrine")
        elif self.relation_kind == "sothic_rising":
            if not self.source_id.startswith("star:") or not self.target_id.startswith("entry:"):
                raise ValueError("sothic rising edges must run from star nodes to entry nodes")
            if self.relation_basis != "sirius_heliacal_rising" or self.condition_state != "annual_rising":
                raise ValueError("sothic rising edges must preserve annual-rising doctrine")
        else:
            if not self.source_id.startswith("star:") or not self.target_id.startswith("epoch:"):
                raise ValueError("sothic epoch edges must run from star nodes to epoch nodes")
            if self.relation_basis != "sirius_heliacal_rising" or self.condition_state != "epoch_alignment":
                raise ValueError("sothic epoch edges must preserve epoch-alignment doctrine")


@dataclass(slots=True)
class SothicConditionNetworkProfile:
    """Network projection over current Sothic relation and condition truth."""

    nodes: tuple[SothicConditionNetworkNode, ...]
    edges: tuple[SothicConditionNetworkEdge, ...]
    isolated_nodes: tuple[SothicConditionNetworkNode, ...]
    most_connected_nodes: tuple[SothicConditionNetworkNode, ...]

    def __post_init__(self) -> None:
        expected_nodes = tuple(sorted(self.nodes, key=_sothic_network_node_sort_key))
        if self.nodes != expected_nodes:
            raise ValueError("sothic network nodes must be deterministically ordered")
        expected_edges = tuple(sorted(self.edges, key=_sothic_network_edge_sort_key))
        if self.edges != expected_edges:
            raise ValueError("sothic network edges must be deterministically ordered")
        node_ids = [node.node_id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("sothic network node ids must be unique")
        edge_keys = [(
            edge.source_id,
            edge.target_id,
            edge.relation_kind,
            edge.relation_basis,
            edge.condition_state,
        ) for edge in self.edges]
        if len(edge_keys) != len(set(edge_keys)):
            raise ValueError("sothic network edges must be unique")
        node_map = {node.node_id: node for node in self.nodes}
        incoming_counts = {node.node_id: 0 for node in self.nodes}
        outgoing_counts = {node.node_id: 0 for node in self.nodes}
        for edge in self.edges:
            if edge.source_id not in node_map or edge.target_id not in node_map:
                raise ValueError("sothic network edges must reference known nodes")
            outgoing_counts[edge.source_id] += 1
            incoming_counts[edge.target_id] += 1
        for node in self.nodes:
            if node.incoming_count != incoming_counts[node.node_id]:
                raise ValueError("sothic network node incoming_count must match edges")
            if node.outgoing_count != outgoing_counts[node.node_id]:
                raise ValueError("sothic network node outgoing_count must match edges")
        expected_isolated = tuple(
            node for node in self.nodes
            if node.total_degree == 0
        )
        if self.isolated_nodes != expected_isolated:
            raise ValueError("sothic network isolated_nodes must match derived isolation")
        if self.nodes:
            max_degree = max(node.total_degree for node in self.nodes)
            expected_most_connected = tuple(
                node for node in self.nodes
                if node.total_degree == max_degree
            )
        else:
            expected_most_connected = ()
        if self.most_connected_nodes != expected_most_connected:
            raise ValueError("sothic network most_connected_nodes must match derived degree ranking")

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class EgyptianDate:
    """
    RITE: The Wandering Day — a position in the ancient Egyptian civil
          calendar that drifts freely through the seasons, untethered to
          any astronomical anchor except the Sothic epoch.

    THEOREM: Immutable record of a date in the 365-day Egyptian civil
             calendar, carrying month name, month number, day, season,
             day-of-year, and the birth deity for epagomenal days.

    RITE OF PURPOSE:
        EgyptianDate is the result vessel of egyptian_civil_date().  It
        translates a Julian Day into the symbolic language of the ancient
        Egyptian year — month, season, and the mythic births of the
        epagomenal days — so that callers can express astronomical events
        in the sacred calendar without performing the modular arithmetic
        themselves.  Without this vessel, callers would receive raw
        day-of-year integers with no semantic context.

    LAW OF OPERATION:
        Responsibilities:
            - Store month_name, month_number (1–13), day (1–30 or 1–5
              for Epagomenal), season, day_of_year (1–365), and
              epagomenal_birth (str or None).
            - Render a human-readable string (e.g. "14 Thoth (Akhet)"
              or "Epagomenal day 3 (Set)").
        Non-responsibilities:
            - Does not perform calendar conversion; that is
              egyptian_civil_date()'s role.
            - Does not validate that day is within the month's range.
            - Does not perform any I/O or kernel access.
        Dependencies:
            - None beyond Python builtins.
        Structural invariants:
            - month_number is in [1, 13].
            - day is in [1, 30] for months 1–12, [1, 5] for month 13.
            - day_of_year is in [1, 365].
            - epagomenal_birth is non-None only when month_number == 13.

    Canon: Plutarch, De Iside et Osiride (epagomenal births)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.sothic.EgyptianDate",
        "risk": "low",
        "api": {"frozen": ["month_name", "month_number", "day", "season", "day_of_year", "epagomenal_birth"], "internal": []},
        "state": {"mutable": false, "owners": []},
        "effects": {
            "signals_emitted": [],
            "io": [],
            "mutation": "none"
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {"policy": "none"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    month_name:    str    # e.g. "Thoth", "Mesore", "Epagomenal"
    month_number:  int    # 1–13 (13 = Epagomenal)
    day:           int    # 1–30 (1–5 for Epagomenal)
    season:        str    # "Akhet", "Peret", "Shemu", or "Epagomenal"
    day_of_year:   int    # 1–365 in the Egyptian civil year
    epagomenal_birth: str | None  # birth deity if Epagomenal day, else None
    computation_truth: EgyptianCalendarTruth | None = None
    classification: EgyptianCalendarClassification | None = None
    relation: SothicRelation | None = None
    condition_profile: SothicConditionProfile | None = None

    def __post_init__(self) -> None:
        if self.month_number < 1 or self.month_number > 13:
            raise ValueError("egyptian date month_number must be between 1 and 13")
        if self.day_of_year < 1 or self.day_of_year > _EGYPTIAN_YEAR_DAYS:
            raise ValueError("egyptian date day_of_year must be within the civil year")
        if self.month_number == 13:
            if self.month_name != "Epagomenal":
                raise ValueError("egyptian date month 13 must be Epagomenal")
            if self.day < 1 or self.day > 5:
                raise ValueError("egyptian epagomenal day must be between 1 and 5")
            if self.season != "Epagomenal":
                raise ValueError("egyptian epagomenal date season must be Epagomenal")
        else:
            if self.day < 1 or self.day > 30:
                raise ValueError("egyptian civil month day must be between 1 and 30")
            if self.epagomenal_birth is not None:
                raise ValueError("egyptian non-epagomenal date must not preserve epagomenal_birth")
        if self.classification is not None:
            if self.computation_truth is None:
                raise ValueError("egyptian date classification requires computation_truth")
            expected = _classify_egyptian_calendar_truth(self.computation_truth)
            if self.classification != expected:
                raise ValueError("egyptian date classification must match computation_truth")
        if self.relation is not None:
            expected = _build_egyptian_date_relation(self)
            if self.relation != expected:
                raise ValueError("egyptian date relation must match computation truth")
        if self.condition_profile is not None:
            expected = _build_egyptian_date_condition_profile(self)
            if self.condition_profile != expected:
                raise ValueError("egyptian date condition profile must match computation truth")

    def __str__(self) -> str:
        if self.month_name == "Epagomenal":
            birth = f" ({self.epagomenal_birth})" if self.epagomenal_birth else ""
            return f"Epagomenal day {self.day}{birth}"
        return f"{self.day} {self.month_name} ({self.season})"

    @property
    def calendar_kind(self) -> str | None:
        return None if self.classification is None else self.classification.calendar_kind

    @property
    def wrap_kind(self) -> str | None:
        return None if self.classification is None else self.classification.wrap_kind

    @property
    def relation_kind(self) -> str | None:
        return None if self.relation is None else self.relation.kind

    @property
    def relation_basis(self) -> str | None:
        return None if self.relation is None else self.relation.basis

    @property
    def relation_anchor(self) -> str | None:
        return None if self.relation is None else self.relation.anchor

    @property
    def has_relation(self) -> bool:
        return self.relation is not None

    @property
    def condition_state(self) -> str | None:
        return None if self.condition_profile is None else self.condition_profile.condition_state.name


@dataclass(slots=True)
class SothicEntry:
    """
    RITE: The Annual Witness — the record of Sirius's heliacal rising for
          a single year, marking where the sacred star stood in the
          Egyptian civil calendar and how far it had drifted from the
          New Year anchor.

    THEOREM: Immutable record of the heliacal rising of Sirius for one
             astronomical year at a given observer location, carrying the
             JD of the rising, its Gregorian and Egyptian calendar dates,
             the drift from 1 Thoth, and the position within the Sothic
             cycle.

    RITE OF PURPOSE:
        SothicEntry is the per-year result vessel of sothic_rising().  It
        gives callers a complete picture of each year's heliacal rising —
        not just when it occurred, but where it fell in the sacred calendar
        and how far the cycle has progressed.  Without this vessel, the
        year-by-year table would be a list of unstructured tuples requiring
        callers to reconstruct all derived quantities.

    LAW OF OPERATION:
        Responsibilities:
            - Store year, jd_rising, date_utc (or None for out-of-range
              years), calendar_year/month/day, day_of_year, drift_days,
              cycle_position, and egyptian_date.
            - Render a compact repr showing year (BC/AD), JD, Gregorian
              date, Egyptian date, and drift.
        Non-responsibilities:
            - Does not compute heliacal rising times; that is
              sothic_rising()'s role.
            - Does not validate that drift_days is within [0, 365).
            - Does not perform any I/O or kernel access.
        Dependencies:
            - EgyptianDate for the egyptian_date field.
        Structural invariants:
            - jd_rising is a finite float.
            - drift_days is in [0, 365).
            - cycle_position is in [0, 1460).

    Canon: Censorinus, De Die Natali 21.10 (reference epoch)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.sothic.SothicEntry",
        "risk": "low",
        "api": {"frozen": ["year", "jd_rising", "date_utc", "calendar_year", "calendar_month", "calendar_day", "day_of_year", "drift_days", "cycle_position", "egyptian_date"], "internal": []},
        "state": {"mutable": false, "owners": []},
        "effects": {
            "signals_emitted": [],
            "io": [],
            "mutation": "none"
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {"policy": "none"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    year:              int      # astronomical year (0 = 1 BC, negative = BC)
    jd_rising:         float    # JD UT of heliacal rising
    date_utc:          datetime | None # Gregorian UTC date when representable
    calendar_year:     int
    calendar_month:    int
    calendar_day:      int
    day_of_year:       int      # Gregorian day-of-year (1–366) of the rising

    # How far the rising has drifted from the reference (1 Thoth at Memphis)
    # Positive = rising is later in the civil calendar than the anchor
    # Negative = rising is earlier
    drift_days:        float

    # Position in the Sothic cycle (0–~1460), measured in days from the
    # most recent Sothic epoch at the reference location
    cycle_position:    float

    # Egyptian civil calendar date at the reference epoch's calendar
    egyptian_date:     EgyptianDate
    computation_truth: SothicComputationTruth | None = None
    classification: SothicComputationClassification | None = None
    relation: SothicRelation | None = None
    condition_profile: SothicConditionProfile | None = None

    def __post_init__(self) -> None:
        if not math.isfinite(self.jd_rising):
            raise ValueError("sothic entry jd_rising must be finite")
        if not math.isfinite(self.drift_days):
            raise ValueError("sothic entry drift_days must be finite")
        if not 0.0 <= self.drift_days < _EGYPTIAN_YEAR_DAYS:
            raise ValueError("sothic entry drift_days must be within the Egyptian civil year")
        if not math.isfinite(self.cycle_position):
            raise ValueError("sothic entry cycle_position must be finite")
        if not 0.0 <= self.cycle_position < _SOTHIC_CYCLE_YEARS:
            raise ValueError("sothic entry cycle_position must be within the Sothic cycle")
        if self.classification is not None:
            if self.computation_truth is None:
                raise ValueError("sothic entry classification requires computation_truth")
            expected = _classify_sothic_computation_truth(self.computation_truth)
            if self.classification != expected:
                raise ValueError("sothic entry classification must match computation_truth")
        if self.computation_truth is not None:
            if self.computation_truth.jd_rising != self.jd_rising:
                raise ValueError("sothic entry computation truth jd_rising must match result")
            if self.computation_truth.drift_days != self.drift_days:
                raise ValueError("sothic entry computation truth drift_days must match result")
            if self.computation_truth.cycle_position != self.cycle_position:
                raise ValueError("sothic entry computation truth cycle_position must match result")
        if self.relation is not None:
            expected = _build_sothic_entry_relation(self)
            if self.relation != expected:
                raise ValueError("sothic entry relation must match computation truth")
        if self.condition_profile is not None:
            expected = _build_sothic_entry_condition_profile(self)
            if self.condition_profile != expected:
                raise ValueError("sothic entry condition profile must match computation truth")

    def __repr__(self) -> str:
        year_str = f"{abs(self.year)} BC" if self.year < 0 else f"{self.year} AD"
        date_str = (
            self.date_utc.strftime('%b %d')
            if self.date_utc is not None
            else f"{self.calendar_year:04d}-{self.calendar_month:02d}-{self.calendar_day:02d}"
        )
        return (
            f"SothicEntry({year_str}: JD {self.jd_rising:.1f}, "
            f"{date_str}, "
            f"Egyptian {self.egyptian_date}, "
            f"drift {self.drift_days:+.1f} d)"
        )

    @property
    def result_kind(self) -> str | None:
        return None if self.classification is None else self.classification.result_kind

    @property
    def star_kind(self) -> str | None:
        return None if self.classification is None else self.classification.star_kind

    @property
    def detection_kind(self) -> str | None:
        return None if self.classification is None else self.classification.detection_kind

    @property
    def tolerance_mode(self) -> str | None:
        return None if self.classification is None else self.classification.tolerance_mode

    @property
    def relation_kind(self) -> str | None:
        return None if self.relation is None else self.relation.kind

    @property
    def relation_basis(self) -> str | None:
        return None if self.relation is None else self.relation.basis

    @property
    def relation_anchor(self) -> str | None:
        return None if self.relation is None else self.relation.anchor

    @property
    def has_relation(self) -> bool:
        return self.relation is not None

    @property
    def condition_state(self) -> str | None:
        return None if self.condition_profile is None else self.condition_profile.condition_state.name


@dataclass(slots=True)
class SothicEpoch:
    """
    RITE: The Great Return — the rare year when the wandering star and the
          wandering calendar meet again at the threshold of the New Year,
          closing one Sothic cycle and opening the next.

    THEOREM: Immutable record of a Sothic epoch year — a year in which the
             heliacal rising of Sirius falls within the configured tolerance
             of 1 Thoth in the Egyptian civil calendar — carrying the year,
             JD of the rising, Gregorian date, and residual drift.

    RITE OF PURPOSE:
        SothicEpoch is the result vessel of sothic_epochs().  It marks the
        historically and astronomically significant moments when the Egyptian
        civil calendar and the heliacal rising of Sirius realign, completing
        the ~1460-year Sothic cycle.  Without this vessel, callers would need
        to filter SothicEntry records themselves and recompute the residual
        drift from the alignment threshold.

    LAW OF OPERATION:
        Responsibilities:
            - Store year, jd_rising, date_utc (or None), calendar_year/
              month/day, and drift_days (residual from exact alignment,
              normalised to [-182.5, 182.5]).
            - Render a compact repr showing year (BC/AD), JD, Gregorian
              date, and residual drift.
        Non-responsibilities:
            - Does not detect epochs; that is sothic_epochs()'s role.
            - Does not validate that drift_days is within tolerance.
            - Does not perform any I/O or kernel access.
        Dependencies:
            - None beyond Python builtins.
        Structural invariants:
            - jd_rising is a finite float.
            - drift_days is in [-182.5, 182.5] (normalised signed drift).

    Canon: Censorinus, De Die Natali 21.10 (confirmed 139 AD epoch)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.sothic.SothicEpoch",
        "risk": "low",
        "api": {"frozen": ["year", "jd_rising", "date_utc", "calendar_year", "calendar_month", "calendar_day", "drift_days"], "internal": []},
        "state": {"mutable": false, "owners": []},
        "effects": {
            "signals_emitted": [],
            "io": [],
            "mutation": "none"
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {"policy": "none"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    year:          int      # astronomical year
    jd_rising:     float    # JD UT of the heliacal rising
    date_utc:      datetime | None
    calendar_year: int
    calendar_month:int
    calendar_day:  int
    drift_days:    float    # residual drift from exact alignment (days)
    computation_truth: SothicComputationTruth | None = None
    classification: SothicComputationClassification | None = None
    relation: SothicRelation | None = None
    condition_profile: SothicConditionProfile | None = None

    def __post_init__(self) -> None:
        if not math.isfinite(self.jd_rising):
            raise ValueError("sothic epoch jd_rising must be finite")
        if not math.isfinite(self.drift_days):
            raise ValueError("sothic epoch drift_days must be finite")
        if not -(_EGYPTIAN_YEAR_DAYS / 2) <= self.drift_days <= (_EGYPTIAN_YEAR_DAYS / 2):
            raise ValueError("sothic epoch drift_days must be normalized around exact alignment")
        if self.classification is not None:
            if self.computation_truth is None:
                raise ValueError("sothic epoch classification requires computation_truth")
            expected = _classify_sothic_computation_truth(self.computation_truth)
            if self.classification != expected:
                raise ValueError("sothic epoch classification must match computation_truth")
        if self.computation_truth is not None:
            if self.computation_truth.jd_rising != self.jd_rising:
                raise ValueError("sothic epoch computation truth jd_rising must match result")
            if self.computation_truth.drift_days != self.drift_days:
                raise ValueError("sothic epoch computation truth drift_days must match result")
            if self.computation_truth.tolerance_days is None:
                raise ValueError("sothic epoch computation truth must preserve tolerance_days")
        if self.relation is not None:
            expected = _build_sothic_epoch_relation(self)
            if self.relation != expected:
                raise ValueError("sothic epoch relation must match computation truth")
        if self.condition_profile is not None:
            expected = _build_sothic_epoch_condition_profile(self)
            if self.condition_profile != expected:
                raise ValueError("sothic epoch condition profile must match computation truth")

    def __repr__(self) -> str:
        year_str = f"{abs(self.year)} BC" if self.year < 0 else f"{self.year} AD"
        date_str = (
            self.date_utc.strftime('%b %d')
            if self.date_utc is not None
            else f"{self.calendar_year:04d}-{self.calendar_month:02d}-{self.calendar_day:02d}"
        )
        return (f"SothicEpoch({year_str}: JD {self.jd_rising:.1f}, "
                f"{date_str}, "
                f"residual {self.drift_days:+.2f} d)")

    @property
    def result_kind(self) -> str | None:
        return None if self.classification is None else self.classification.result_kind

    @property
    def star_kind(self) -> str | None:
        return None if self.classification is None else self.classification.star_kind

    @property
    def detection_kind(self) -> str | None:
        return None if self.classification is None else self.classification.detection_kind

    @property
    def tolerance_mode(self) -> str | None:
        return None if self.classification is None else self.classification.tolerance_mode

    @property
    def relation_kind(self) -> str | None:
        return None if self.relation is None else self.relation.kind

    @property
    def relation_basis(self) -> str | None:
        return None if self.relation is None else self.relation.basis

    @property
    def relation_anchor(self) -> str | None:
        return None if self.relation is None else self.relation.anchor

    @property
    def has_relation(self) -> bool:
        return self.relation is not None

    @property
    def condition_state(self) -> str | None:
        return None if self.condition_profile is None else self.condition_profile.condition_state.name


# ---------------------------------------------------------------------------
# Egyptian civil calendar
# ---------------------------------------------------------------------------

def egyptian_civil_date(
    jd: float,
    epoch_jd: float = _SOTHIC_EPOCH_139_JD,
    policy: SothicComputationPolicy | None = None,
) -> EgyptianDate:
    """
    Convert a Julian Day to an Egyptian civil calendar date.

    The Egyptian civil calendar is a wandering calendar of exactly 365 days
    per year.  It is anchored to the given *epoch_jd* as 1 Thoth of year 0.

    Parameters
    ----------
    jd       : Julian Day to convert
    epoch_jd : JD of 1 Thoth in the reference year (default: 139 AD Sothic epoch)

    Returns
    -------
    EgyptianDate giving the month, day, and season.

    Notes
    -----
    Because the Egyptian year does not drift with the seasons (no leap year),
    the returned date tells you *where in the Egyptian civil calendar* a given
    astronomical event falls, relative to the anchor epoch.
    """
    policy = _resolve_sothic_policy(policy)
    _validate_sothic_policy(policy)
    epoch_jd = policy.calendar.epoch_jd if epoch_jd == _SOTHIC_EPOCH_139_JD else epoch_jd
    if not math.isfinite(jd):
        raise ValueError("egyptian civil jd must be finite")
    _validate_sothic_epoch_jd(epoch_jd)

    # Days elapsed since the epoch (mod 365)
    elapsed = jd - epoch_jd
    day_of_year = int(elapsed % _EGYPTIAN_YEAR_DAYS)
    if day_of_year < 0:
        day_of_year += _EGYPTIAN_YEAR_DAYS
    truth = EgyptianCalendarTruth(
        jd=jd,
        epoch_jd=epoch_jd,
        elapsed_days=elapsed,
        wrapped_day_index=day_of_year,
    )
    classification = _classify_egyptian_calendar_truth(truth)

    # 1-indexed
    doy = day_of_year + 1    # 1–365

    if doy <= 360:
        month_idx = (doy - 1) // 30      # 0–11
        day       = (doy - 1) % 30 + 1   # 1–30
        month_name = EGYPTIAN_MONTHS[month_idx]
        month_number = month_idx + 1
        # Season
        if month_idx < 4:
            season = "Akhet"
        elif month_idx < 8:
            season = "Peret"
        else:
            season = "Shemu"
        return EgyptianDate(
            month_name=month_name,
            month_number=month_number,
            day=day,
            season=season,
            day_of_year=doy,
            epagomenal_birth=None,
            computation_truth=truth,
            classification=classification,
            relation=_build_egyptian_date_relation(None),
            condition_profile=_build_egyptian_date_condition_profile(None),
        )
    else:
        # Epagomenal days: doy 361–365
        epag_day = doy - 360    # 1–5
        birth = EPAGOMENAL_BIRTHS[epag_day - 1] if epag_day <= 5 else None
        return EgyptianDate(
            month_name="Epagomenal",
            month_number=13,
            day=epag_day,
            season="Epagomenal",
            day_of_year=doy,
            epagomenal_birth=birth,
            computation_truth=truth,
            classification=classification,
            relation=_build_egyptian_date_relation(None),
            condition_profile=_build_egyptian_date_condition_profile(None),
        )


def days_from_1_thoth(jd: float, epoch_jd: float = _SOTHIC_EPOCH_139_JD) -> float:
    """
    Return how many civil calendar days have elapsed since 1 Thoth of the
    current Egyptian year relative to the epoch.

    Equivalent to (day_of_year - 1) with a fractional day component.
    """
    elapsed = jd - epoch_jd
    return elapsed % _EGYPTIAN_YEAR_DAYS


# ---------------------------------------------------------------------------
# Core: Sothic rising computation
# ---------------------------------------------------------------------------

def sothic_rising(
    latitude: float,
    longitude: float,
    year_start: int,
    year_end: int,
    epoch_jd: float = _SOTHIC_EPOCH_139_JD,
    arcus_visionis: float = 10.0,
    policy: SothicComputationPolicy | None = None,
) -> list[SothicEntry]:
    """
    Compute the heliacal rising of Sirius for each year in the given range.

    This is the central function of the Sothic cycle — a year-by-year record
    of when Sirius first appeared on the eastern horizon before sunrise,
    and where that moment fell in the Egyptian civil calendar.

    Parameters
    ----------
    latitude        : observer geographic latitude (degrees, signed)
    longitude       : observer geographic east longitude (degrees)
    year_start      : first astronomical year to compute (negative = BC)
    year_end        : last astronomical year to compute (inclusive)
    epoch_jd        : reference Sothic epoch JD (default: 139 AD at Alexandria)
    arcus_visionis  : solar depression required for Sirius visibility (degrees).
                      Default 10° is appropriate for Sirius (magnitude −1.46)
                      in a clear ancient Mediterranean sky.  Increase to 11–12°
                      for modern polluted skies.

    Returns
    -------
    list[SothicEntry], one per year where a heliacal rising was found.
    Years where Sirius is circumpolar or never rises are omitted.

    Notes
    -----
    At latitudes above ~73°N, Sirius never rises; this function returns an
    empty list for such latitudes.

    The search for each year begins on January 1 (proleptic Gregorian) and
    looks forward up to 400 days.  The heliacal rising of Sirius occurs in
    boreal summer at most latitudes; if a year is skipped, it typically means
    the rising occurred very close to year-end and was captured in the
    adjacent year.
    """
    policy = _resolve_sothic_policy(policy)
    _validate_sothic_policy(policy)
    epoch_jd = policy.calendar.epoch_jd if epoch_jd == _SOTHIC_EPOCH_139_JD else epoch_jd
    arcus_visionis = policy.heliacal.arcus_visionis if arcus_visionis == 10.0 else arcus_visionis
    _validate_sothic_coordinates(latitude, longitude)
    _validate_sothic_year_range(year_start, year_end)
    _validate_sothic_epoch_jd(epoch_jd)
    _validate_sothic_arcus_visionis(arcus_visionis)

    results: list[SothicEntry] = []

    for year in range(year_start, year_end + 1):
        # Start search from January 1 of this year
        jd_start = julian_day(year, 1, 1, 0.0)

        try:
            jd_rise = _heliacal_rising(
                "Sirius", jd_start, latitude, longitude,
                arcus_visionis=arcus_visionis,
                search_days=policy.heliacal.search_days,
            )
        except Exception:
            continue   # catalog not loaded or other error

        if jd_rise is None:
            continue   # Sirius does not rise heliacally at this latitude/year

        # Calendar date
        cal_year, cal_month, cal_day, _ = calendar_from_jd(jd_rise)
        dt = safe_datetime_from_jd(jd_rise)
        doy = _day_of_year(dt) if dt is not None else int(jd_rise - julian_day(cal_year, 1, 1, 0.0)) + 1

        # Drift: how many Egyptian civil calendar days from 1 Thoth?
        # At the reference epoch, the rising fell on day 1 of the Egyptian year.
        # Each ~4 years the rising drifts one day further through the calendar.
        drift = days_from_1_thoth(jd_rise, epoch_jd)

        # Year within the 1460-year Sothic cycle (0.0 → 1460.0)
        cycle_pos = ((jd_rise - epoch_jd) / 365.25) % _SOTHIC_CYCLE_YEARS

        # Egyptian date at the reference epoch's calendar
        egypt_date = egyptian_civil_date(jd_rise, epoch_jd)
        truth = SothicComputationTruth(
            star_name="Sirius",
            latitude=latitude,
            longitude=longitude,
            epoch_jd=epoch_jd,
            arcus_visionis=arcus_visionis,
            search_days=policy.heliacal.search_days,
            jd_start=jd_start,
            jd_rising=jd_rise,
            drift_days=drift,
            cycle_position=cycle_pos,
        )
        classification = _classify_sothic_computation_truth(truth)

        results.append(SothicEntry(
            year=year,
            jd_rising=jd_rise,
            date_utc=dt,
            calendar_year=cal_year,
            calendar_month=cal_month,
            calendar_day=cal_day,
            day_of_year=doy,
            drift_days=drift,
            cycle_position=cycle_pos,
            egyptian_date=egypt_date,
            computation_truth=truth,
            classification=classification,
            relation=_build_sothic_entry_relation(None),
            condition_profile=SothicConditionProfile(
                result_kind="sothic_entry",
                condition_state=SothicConditionState("annual_rising"),
                relation_kind="sothic_rising",
                relation_basis="sirius_heliacal_rising",
                star_kind=classification.star_kind,
                tolerance_mode=classification.tolerance_mode,
            ),
        ))

    return results


# ---------------------------------------------------------------------------
# Sothic epoch finder
# ---------------------------------------------------------------------------

def sothic_epochs(
    latitude: float,
    longitude: float,
    year_start: int,
    year_end: int,
    epoch_jd: float = _SOTHIC_EPOCH_139_JD,
    tolerance_days: float = 1.0,
    arcus_visionis: float = 10.0,
    policy: SothicComputationPolicy | None = None,
) -> list[SothicEpoch]:
    """
    Find years within the range where the heliacal rising of Sirius returns
    to within *tolerance_days* of the original civil New Year anchor.

    These are the "Sothic epochs" — the sacred moments when the sacred star
    and the sacred calendar realign.

    Parameters
    ----------
    latitude / longitude : observer location
    year_start / year_end : search range (astronomical years)
    epoch_jd       : reference anchor JD (default: 139 AD)
    tolerance_days : how close to 1 Thoth counts as an epoch (default ±1 day)
    arcus_visionis : solar depression required (default 10° for Sirius)

    Returns
    -------
    list[SothicEpoch], one per epoch found in the range.

    Notes
    -----
    The Sothic cycle length (~1460 Julian years or ~1507 tropical years) means
    a range of 2000 years will typically contain 1–2 epochs.  Use a range of
    10,000+ years for the full historical picture.
    """
    policy = _resolve_sothic_policy(policy)
    _validate_sothic_policy(policy)
    epoch_jd = policy.calendar.epoch_jd if epoch_jd == _SOTHIC_EPOCH_139_JD else epoch_jd
    tolerance_days = policy.epoch.tolerance_days if tolerance_days == 1.0 else tolerance_days
    arcus_visionis = policy.heliacal.arcus_visionis if arcus_visionis == 10.0 else arcus_visionis
    _validate_sothic_coordinates(latitude, longitude)
    _validate_sothic_year_range(year_start, year_end)
    _validate_sothic_epoch_jd(epoch_jd)
    _validate_sothic_tolerance_days(tolerance_days)
    _validate_sothic_arcus_visionis(arcus_visionis)

    entries = sothic_rising(
        latitude,
        longitude,
        year_start,
        year_end,
        epoch_jd=epoch_jd,
        arcus_visionis=arcus_visionis,
        policy=policy,
    )
    epochs: list[SothicEpoch] = []

    for e in entries:
        # Drift relative to 1 Thoth: we want drift close to 0 (or 365)
        drift = e.drift_days
        # Normalise to [-182.5, 182.5] so we can measure closeness to both
        # 0 and 365 (which are the same point in the cycle)
        if drift > _EGYPTIAN_YEAR_DAYS / 2:
            drift -= _EGYPTIAN_YEAR_DAYS

        if abs(drift) <= tolerance_days:
            truth = SothicComputationTruth(
                star_name="Sirius",
                latitude=latitude,
                longitude=longitude,
                epoch_jd=epoch_jd,
                arcus_visionis=arcus_visionis,
                search_days=policy.heliacal.search_days,
                jd_start=julian_day(e.year, 1, 1, 0.0),
                jd_rising=e.jd_rising,
                drift_days=drift,
                tolerance_days=tolerance_days,
            )
            epochs.append(SothicEpoch(
                year=e.year,
                jd_rising=e.jd_rising,
                date_utc=e.date_utc,
                calendar_year=e.calendar_year,
                calendar_month=e.calendar_month,
                calendar_day=e.calendar_day,
                drift_days=drift,
                computation_truth=truth,
                classification=_classify_sothic_computation_truth(truth),
                relation=_build_sothic_epoch_relation(None),
                condition_profile=SothicConditionProfile(
                    result_kind="sothic_epoch",
                    condition_state=SothicConditionState("epoch_alignment"),
                    relation_kind="sothic_epoch",
                    relation_basis="sirius_heliacal_rising",
                    star_kind="sirius_heliacal",
                    tolerance_mode="epoch_tolerance",
                ),
            ))

    return epochs


# ---------------------------------------------------------------------------
# Drift analysis
# ---------------------------------------------------------------------------

def sothic_drift_rate(entries: list[SothicEntry]) -> float:
    """
    Estimate the observed drift rate of the heliacal rising through the
    Egyptian civil calendar in days per year, computed from a list of
    SothicEntry records.

    For the standard Egyptian civil calendar this should be ~0.242 days/year
    (approximately 1 day per 4.13 years).

    Parameters
    ----------
    entries : list from sothic_rising() — must span at least 5 years

    Returns
    -------
    Drift rate in days per year (positive = rising moves later in calendar)
    """
    if len(entries) < 5:
        raise ValueError("Need at least 5 entries to estimate drift rate")
    for entry in entries:
        if not hasattr(entry, "year") or not hasattr(entry, "drift_days"):
            raise ValueError("sothic drift rate entries must preserve year and drift_days")
        if not isinstance(entry.year, int):
            raise ValueError("sothic drift rate entry year must be an integer")
        if not math.isfinite(entry.drift_days):
            raise ValueError("sothic drift rate entry drift_days must be finite")

    # Linear regression on drift_days vs year
    n = len(entries)
    xs = [e.year for e in entries]
    ys = [e.drift_days for e in entries]

    # Unwrap: remove the 365-day jumps when drift wraps around
    for i in range(1, n):
        diff = ys[i] - ys[i - 1]
        if diff > 182.5:
            for j in range(i, n):
                ys[j] -= _EGYPTIAN_YEAR_DAYS
        elif diff < -182.5:
            for j in range(i, n):
                ys[j] += _EGYPTIAN_YEAR_DAYS

    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    den = sum((x - mean_x) ** 2 for x in xs)
    if abs(den) < 1e-10:
        return 0.0
    return num / den


def predicted_sothic_epoch_year(
    known_epoch_year: int,
    n_cycles: int,
    cycle_length_years: float = 1460.0,
    policy: SothicComputationPolicy | None = None,
) -> float:
    """
    Predict the year of a Sothic epoch *n_cycles* after a known epoch.

    Parameters
    ----------
    known_epoch_year  : astronomical year of a known Sothic epoch
    n_cycles          : number of cycles forward (positive) or backward (negative)
    cycle_length_years: assumed Sothic cycle length (default 1460.0 Julian years)

    Returns
    -------
    Predicted astronomical year (float)
    """
    policy = _resolve_sothic_policy(policy)
    _validate_sothic_policy(policy)
    cycle_length_years = (
        policy.prediction.cycle_length_years
        if cycle_length_years == 1460.0
        else cycle_length_years
    )
    if not isinstance(known_epoch_year, int):
        raise ValueError("known_epoch_year must be an integer")
    if not isinstance(n_cycles, int):
        raise ValueError("n_cycles must be an integer")
    if not math.isfinite(cycle_length_years) or cycle_length_years <= 0:
        raise ValueError("cycle_length_years must be positive")
    return known_epoch_year + n_cycles * cycle_length_years


def sothic_chart_condition_profile(
    *,
    egyptian_dates: list[EgyptianDate] | None = None,
    entries: list[SothicEntry] | None = None,
    epochs: list[SothicEpoch] | None = None,
) -> SothicChartConditionProfile:
    """Aggregate current Sothic condition profiles into one chart-wide vessel."""

    profiles: list[SothicConditionProfile] = []
    if egyptian_dates is not None:
        profiles.extend(
            date.condition_profile
            for date in egyptian_dates
            if date.condition_profile is not None
        )
    if entries is not None:
        profiles.extend(
            entry.condition_profile
            for entry in entries
            if entry.condition_profile is not None
        )
    if epochs is not None:
        profiles.extend(
            epoch.condition_profile
            for epoch in epochs
            if epoch.condition_profile is not None
        )

    ordered_profiles = tuple(sorted(profiles, key=_sothic_condition_sort_key))
    if ordered_profiles:
        strongest_rank = max(_sothic_condition_strength(p) for p in ordered_profiles)
        weakest_rank = min(_sothic_condition_strength(p) for p in ordered_profiles)
        strongest_profiles = tuple(
            p for p in ordered_profiles
            if _sothic_condition_strength(p) == strongest_rank
        )
        weakest_profiles = tuple(
            p for p in ordered_profiles
            if _sothic_condition_strength(p) == weakest_rank
        )
    else:
        strongest_profiles = ()
        weakest_profiles = ()

    return SothicChartConditionProfile(
        profiles=ordered_profiles,
        calendar_anchor_count=sum(1 for p in ordered_profiles if p.condition_state.name == "calendar_anchor"),
        annual_rising_count=sum(1 for p in ordered_profiles if p.condition_state.name == "annual_rising"),
        epoch_alignment_count=sum(1 for p in ordered_profiles if p.condition_state.name == "epoch_alignment"),
        strongest_profiles=strongest_profiles,
        weakest_profiles=weakest_profiles,
    )


def _egyptian_date_network_node_id(date: EgyptianDate) -> str:
    return f"date:{date.day_of_year:03d}:{date.month_number:02d}:{date.day:02d}"


def _sothic_entry_network_node_id(entry: SothicEntry) -> str:
    return f"entry:{entry.year}"


def _sothic_epoch_network_node_id(epoch: SothicEpoch) -> str:
    return f"epoch:{epoch.year}"


def sothic_condition_network_profile(
    *,
    egyptian_dates: list[EgyptianDate] | None = None,
    entries: list[SothicEntry] | None = None,
    epochs: list[SothicEpoch] | None = None,
) -> SothicConditionNetworkProfile:
    """Build a deterministic network from current Sothic relation and condition truth."""

    node_kinds: dict[str, str] = {}
    edges: list[SothicConditionNetworkEdge] = []

    def ensure_node(node_id: str, kind: str) -> None:
        existing = node_kinds.get(node_id)
        if existing is None:
            node_kinds[node_id] = kind
        elif existing != kind:
            raise ValueError("sothic network node ids must not change kind")

    if egyptian_dates is not None:
        for date in egyptian_dates:
            if date.relation is None or date.condition_profile is None:
                continue
            source_id = f"anchor:{date.relation.anchor}"
            target_id = _egyptian_date_network_node_id(date)
            ensure_node(source_id, "anchor")
            ensure_node(target_id, "date")
            edges.append(SothicConditionNetworkEdge(
                source_id=source_id,
                target_id=target_id,
                relation_kind=date.relation.kind,
                relation_basis=date.relation.basis,
                condition_state=date.condition_profile.condition_state.name,
            ))

    if entries is not None:
        for entry in entries:
            if entry.relation is None or entry.condition_profile is None:
                continue
            source_id = f"star:{entry.relation.star_name}"
            target_id = _sothic_entry_network_node_id(entry)
            ensure_node(source_id, "star")
            ensure_node(target_id, "entry")
            edges.append(SothicConditionNetworkEdge(
                source_id=source_id,
                target_id=target_id,
                relation_kind=entry.relation.kind,
                relation_basis=entry.relation.basis,
                condition_state=entry.condition_profile.condition_state.name,
            ))

    if epochs is not None:
        for epoch in epochs:
            if epoch.relation is None or epoch.condition_profile is None:
                continue
            source_id = f"star:{epoch.relation.star_name}"
            target_id = _sothic_epoch_network_node_id(epoch)
            ensure_node(source_id, "star")
            ensure_node(target_id, "epoch")
            edges.append(SothicConditionNetworkEdge(
                source_id=source_id,
                target_id=target_id,
                relation_kind=epoch.relation.kind,
                relation_basis=epoch.relation.basis,
                condition_state=epoch.condition_profile.condition_state.name,
            ))

    ordered_edges = tuple(sorted(edges, key=_sothic_network_edge_sort_key))
    incoming_counts = {node_id: 0 for node_id in node_kinds}
    outgoing_counts = {node_id: 0 for node_id in node_kinds}
    for edge in ordered_edges:
        outgoing_counts[edge.source_id] += 1
        incoming_counts[edge.target_id] += 1

    ordered_nodes = tuple(sorted(
        (
            SothicConditionNetworkNode(
                node_id=node_id,
                kind=kind,
                incoming_count=incoming_counts[node_id],
                outgoing_count=outgoing_counts[node_id],
            )
            for node_id, kind in node_kinds.items()
        ),
        key=_sothic_network_node_sort_key,
    ))
    isolated_nodes = tuple(node for node in ordered_nodes if node.total_degree == 0)
    if ordered_nodes:
        max_degree = max(node.total_degree for node in ordered_nodes)
        most_connected_nodes = tuple(
            node for node in ordered_nodes
            if node.total_degree == max_degree
        )
    else:
        most_connected_nodes = ()

    return SothicConditionNetworkProfile(
        nodes=ordered_nodes,
        edges=ordered_edges,
        isolated_nodes=isolated_nodes,
        most_connected_nodes=most_connected_nodes,
    )


# ---------------------------------------------------------------------------
# Convenience: historical epochs
# ---------------------------------------------------------------------------

# Known / inferred Sothic epochs at Memphis (lat 29.8°N, lon 31.3°E)
HISTORICAL_SOTHIC_EPOCHS: list[dict] = [
    {"year": -2780, "note": "First Sothic Period — beginning of the Egyptian calendar (inferred)"},
    {"year": -1320, "note": "Second Sothic Period — Ebers Papyrus (9th year of Amenhotep I, inferred)"},
    {"year":   139, "note": "Third Sothic Period — Censorinus (confirmed, 139 AD)"},
    {"year":  1599, "note": "Fourth Sothic Period — computed from the 139 AD epoch"},
]


# ---------------------------------------------------------------------------
# Internal utilities
# ---------------------------------------------------------------------------

def _day_of_year(dt: datetime) -> int:
    """Return the day-of-year (1–366) for a datetime."""
    return dt.timetuple().tm_yday


def _safe_datetime_from_jd(jd: float) -> datetime | None:
    """Backward-compatible local alias; use moira.julian.safe_datetime_from_jd."""
    return safe_datetime_from_jd(jd)


def _validate_sothic_coordinates(latitude: float, longitude: float) -> None:
    if not math.isfinite(latitude):
        raise ValueError("sothic latitude must be finite")
    if not math.isfinite(longitude):
        raise ValueError("sothic longitude must be finite")
    if not -90.0 <= latitude <= 90.0:
        raise ValueError("sothic latitude must be between -90 and 90 degrees")
    if not -180.0 <= longitude <= 180.0:
        raise ValueError("sothic longitude must be between -180 and 180 degrees")


def _validate_sothic_year_range(year_start: int, year_end: int) -> None:
    if not isinstance(year_start, int) or not isinstance(year_end, int):
        raise ValueError("sothic year range bounds must be integers")
    if year_end < year_start:
        raise ValueError("sothic year_end must be greater than or equal to year_start")


def _validate_sothic_epoch_jd(epoch_jd: float) -> None:
    if not math.isfinite(epoch_jd):
        raise ValueError("sothic epoch_jd must be finite")


def _validate_sothic_arcus_visionis(arcus_visionis: float) -> None:
    if not math.isfinite(arcus_visionis) or arcus_visionis <= 0:
        raise ValueError("sothic arcus_visionis must be positive")


def _validate_sothic_tolerance_days(tolerance_days: float) -> None:
    if not math.isfinite(tolerance_days) or tolerance_days < 0:
        raise ValueError("sothic tolerance_days must be non-negative")
