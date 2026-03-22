"""
Moira — progressions.py
The Progression Engine: governs secondary progressions, solar arc directions,
Naibod directions, tertiary progressions, converse progressions, minor
progressions, and progressed house-frame techniques.

Boundary: owns all symbolic time-advancement techniques (one-day-one-year and
variants). Delegates body position computation to planets. Delegates Julian Day
arithmetic to julian. Does NOT own ephemeris state or natal chart construction.

Public surface:
    ProgressedPosition, ProgressedChart,
    secondary_progression, solar_arc, solar_arc_right_ascension,
    naibod_longitude, naibod_right_ascension,
    tertiary_progression, tertiary_ii_progression,
    converse_secondary_progression, converse_solar_arc,
    converse_solar_arc_right_ascension,
    converse_naibod_longitude, converse_naibod_right_ascension,
    converse_tertiary_progression, converse_tertiary_ii_progression,
    ascendant_arc, minor_progression, converse_minor_progression,
    daily_houses

Import-time side effects: None

External dependency assumptions:
    - No third-party packages; stdlib only plus internal moira modules.
    - SpkReader must be initialised before any public function is called.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .constants import Body, HouseSystem, HOUSE_SYSTEM_NAMES, sign_of
from .coordinates import ecliptic_to_equatorial, equatorial_to_ecliptic
from .houses import HouseCusps, calculate_houses
from .julian import CalendarDateTime, calendar_datetime_from_jd, datetime_from_jd, jd_from_datetime, delta_t, ut_to_tt
from .planets import planet_at, all_planets_at
from .obliquity import true_obliquity
from .spk_reader import get_reader, SpkReader


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ProgressionDoctrineTruth:
    """
    Preserve the doctrinal key embodied by one progression technique.

    The progression subsystem currently embodies three technique families:
    ``time_key``, ``uniform_arc``, and ``house_frame``. This is preserved here
    as backend truth so later policy and standards work does not have to infer
    the family doctrine from arithmetic alone.
    """

    technique_name: str
    doctrine_family: str
    life_unit: str
    ephemeris_unit: str
    rate_mode: str
    application_mode: str
    coordinate_system: str
    converse: bool = False


@dataclass(slots=True)
class ProgressionComputationTruth:
    """Preserve the concrete computational path used to build a progression."""

    doctrine: ProgressionDoctrineTruth
    target_jd_ut: float
    age_years: float
    progressed_jd_ut: float
    directed_arc_deg: float | None = None
    reference_body: str | None = None
    reference_start_value: float | None = None
    reference_end_value: float | None = None
    stepped_years: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    house_system: str | None = None


@dataclass(slots=True)
class ProgressionDoctrineClassification:
    """Typed descriptive classification derived from preserved doctrine truth."""

    technique_name: str
    doctrine_family: str
    rate_mode: str
    application_mode: str
    coordinate_system: str
    converse: bool


@dataclass(slots=True)
class ProgressionComputationClassification:
    """Typed descriptive classification derived from preserved computation truth."""

    doctrine: ProgressionDoctrineClassification
    uses_directed_arc: bool
    uses_reference_body: bool
    uses_stepped_key: bool
    uses_house_frame: bool


@dataclass(slots=True)
class ProgressionRelation:
    """
    Formalize the directing relation embodied by a progression technique.

    This is the small Phase 5 relation layer for progressions: it makes explicit
    whether a result was produced by a time key, a directing arc, or a house-frame
    projection, and what concrete doctrinal basis supplied that relation.
    """

    technique_name: str
    relation_kind: str
    basis: str
    reference_name: str | None
    converse: bool
    coordinate_system: str


@dataclass(slots=True)
class ProgressionConditionProfile:
    """
    Integrated per-result progression condition profile.

    This is a structural synthesis layer only. It consumes preserved doctrine,
    classification, and relation truth without introducing interpretation.
    """

    technique_name: str
    doctrine_family: str
    relation_kind: str
    relation_basis: str
    coordinate_system: str
    rate_mode: str
    application_mode: str
    converse: bool
    uses_directed_arc: bool
    uses_reference_body: bool
    uses_stepped_key: bool
    uses_house_frame: bool
    structural_state: str


@dataclass(slots=True)
class ProgressionChartConditionProfile:
    """
    Deterministic aggregate over per-result progression condition profiles.

    This is a pure chart-wide/backend aggregation layer. It consumes existing
    ``ProgressionConditionProfile`` truth and does not recompute doctrine.
    """

    profiles: tuple[ProgressionConditionProfile, ...]
    uniform_count: int
    differential_count: int
    hybrid_count: int
    directing_arc_count: int
    time_key_count: int
    house_frame_count: int
    strongest_techniques: tuple[str, ...]
    weakest_techniques: tuple[str, ...]

    def __post_init__(self) -> None:
        ordered = tuple(
            sorted(
                self.profiles,
                key=lambda profile: (
                    profile.technique_name,
                    profile.converse,
                    profile.relation_kind,
                    profile.coordinate_system,
                ),
            )
        )
        if self.profiles != ordered:
            raise ValueError("chart condition profiles must be deterministically ordered")
        if self.uniform_count != sum(profile.structural_state == "uniform" for profile in self.profiles):
            raise ValueError("uniform_count must match profiles")
        if self.differential_count != sum(profile.structural_state == "differential" for profile in self.profiles):
            raise ValueError("differential_count must match profiles")
        if self.hybrid_count != sum(profile.structural_state == "hybrid" for profile in self.profiles):
            raise ValueError("hybrid_count must match profiles")
        if self.directing_arc_count != sum(profile.relation_kind == "directing_arc" for profile in self.profiles):
            raise ValueError("directing_arc_count must match profiles")
        if self.time_key_count != sum(profile.relation_kind == "time_key" for profile in self.profiles):
            raise ValueError("time_key_count must match profiles")
        if self.house_frame_count != sum(profile.relation_kind == "house_frame_projection" for profile in self.profiles):
            raise ValueError("house_frame_count must match profiles")
        if self.strongest_techniques != _condition_extreme_names(self.profiles, strongest=True):
            raise ValueError("strongest_techniques must match profiles")
        if self.weakest_techniques != _condition_extreme_names(self.profiles, strongest=False):
            raise ValueError("weakest_techniques must match profiles")

    @property
    def profile_count(self) -> int:
        return len(self.profiles)

    @property
    def strongest_count(self) -> int:
        return len(self.strongest_techniques)

    @property
    def weakest_count(self) -> int:
        return len(self.weakest_techniques)


@dataclass(slots=True)
class ProgressionConditionNetworkNode:
    """Node in the structural progression condition network."""

    node_id: str
    node_kind: str
    label: str
    incoming_count: int
    outgoing_count: int
    total_degree: int
    is_isolated: bool

    def __post_init__(self) -> None:
        if not self.node_id:
            raise ValueError("network node_id must be non-empty")
        if self.node_kind not in {"technique", "reference", "basis"}:
            raise ValueError("network node_kind must be a supported kind")
        if not self.label:
            raise ValueError("network node label must be non-empty")
        if self.incoming_count < 0 or self.outgoing_count < 0 or self.total_degree < 0:
            raise ValueError("network node degree counts must be non-negative")
        if self.total_degree != self.incoming_count + self.outgoing_count:
            raise ValueError("network node total_degree must equal incoming_count + outgoing_count")
        if self.is_isolated != (self.total_degree == 0):
            raise ValueError("network node is_isolated must match total_degree")


@dataclass(slots=True)
class ProgressionConditionNetworkEdge:
    """Directed edge in the structural progression condition network."""

    source_id: str
    target_id: str
    relation_kind: str
    relation_basis: str

    def __post_init__(self) -> None:
        if not self.source_id or not self.target_id:
            raise ValueError("network edge endpoints must be non-empty")
        if self.source_id == self.target_id:
            raise ValueError("network edges may not self-loop")
        if self.relation_kind not in {"time_key", "directing_arc", "house_frame_projection"}:
            raise ValueError("network edge relation_kind must be supported")
        if self.relation_basis not in {
            "continuous_time_key",
            "stepped_time_key",
            "solar_arc_reference",
            "ascendant_arc_reference",
            "naibod_rate",
            "progressed_house_frame",
        }:
            raise ValueError("network edge relation_basis must be supported")


@dataclass(slots=True)
class ProgressionConditionNetworkProfile:
    """Deterministic network projection over progression condition profiles."""

    nodes: tuple[ProgressionConditionNetworkNode, ...]
    edges: tuple[ProgressionConditionNetworkEdge, ...]
    technique_node_count: int
    target_node_count: int
    most_connected_nodes: tuple[str, ...]
    isolated_nodes: tuple[str, ...]

    def __post_init__(self) -> None:
        ordered_nodes = tuple(sorted(self.nodes, key=lambda node: (node.node_kind, node.label, node.node_id)))
        ordered_edges = tuple(sorted(self.edges, key=lambda edge: (edge.source_id, edge.target_id, edge.relation_kind, edge.relation_basis)))
        if self.nodes != ordered_nodes:
            raise ValueError("network nodes must be deterministically ordered")
        if self.edges != ordered_edges:
            raise ValueError("network edges must be deterministically ordered")
        node_ids = {node.node_id for node in self.nodes}
        if len(node_ids) != len(self.nodes):
            raise ValueError("network node ids must be unique")
        for edge in self.edges:
            if edge.source_id not in node_ids or edge.target_id not in node_ids:
                raise ValueError("network edges must reference existing nodes")
        incoming = {node.node_id: 0 for node in self.nodes}
        outgoing = {node.node_id: 0 for node in self.nodes}
        for edge in self.edges:
            outgoing[edge.source_id] += 1
            incoming[edge.target_id] += 1
        if self.technique_node_count != sum(node.node_kind == "technique" for node in self.nodes):
            raise ValueError("technique_node_count must match nodes")
        if self.target_node_count != sum(node.node_kind != "technique" for node in self.nodes):
            raise ValueError("target_node_count must match nodes")
        for node in self.nodes:
            if node.incoming_count != incoming[node.node_id]:
                raise ValueError("network node incoming_count must match edges")
            if node.outgoing_count != outgoing[node.node_id]:
                raise ValueError("network node outgoing_count must match edges")
            if node.total_degree != incoming[node.node_id] + outgoing[node.node_id]:
                raise ValueError("network node total_degree must match edges")
            if node.is_isolated != (incoming[node.node_id] + outgoing[node.node_id] == 0):
                raise ValueError("network node is_isolated must match edges")
            if node.node_kind == "technique" and node.incoming_count != 0:
                raise ValueError("technique nodes may not have incoming edges")
            if node.node_kind != "technique" and node.outgoing_count != 0:
                raise ValueError("target nodes may not have outgoing edges")
        if self.isolated_nodes != tuple(node.label for node in self.nodes if node.is_isolated):
            raise ValueError("isolated_nodes must match nodes")
        expected_most_connected = _network_extreme_node_labels(self.nodes)
        if self.most_connected_nodes != expected_most_connected:
            raise ValueError("most_connected_nodes must match nodes")

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)


def _validate_progression_truth_and_classification(
    *,
    chart_type: str,
    progressed_jd_ut: float,
    solar_arc_deg: float | None,
    truth: ProgressionComputationTruth | None,
    classification: ProgressionComputationClassification | None,
    requires_house_frame: bool = False,
) -> None:
    if (truth is None) != (classification is None):
        raise ValueError("computation_truth and classification must be provided together")
    if truth is None or classification is None:
        return
    if truth.doctrine.technique_name != chart_type:
        raise ValueError("computation_truth doctrine must match chart_type")
    if truth.progressed_jd_ut != progressed_jd_ut:
        raise ValueError("computation_truth progressed_jd_ut must match vessel progressed_jd_ut")
    if solar_arc_deg is not None and truth.directed_arc_deg is not None and truth.directed_arc_deg != solar_arc_deg:
        raise ValueError("directed_arc_deg must match solar_arc_deg")
    if classification.doctrine.technique_name != truth.doctrine.technique_name:
        raise ValueError("classification technique_name must match computation truth")
    if classification.doctrine.doctrine_family != truth.doctrine.doctrine_family:
        raise ValueError("classification doctrine_family must match computation truth")
    if classification.doctrine.rate_mode != truth.doctrine.rate_mode:
        raise ValueError("classification rate_mode must match computation truth")
    if classification.doctrine.application_mode != truth.doctrine.application_mode:
        raise ValueError("classification application_mode must match computation truth")
    if classification.doctrine.coordinate_system != truth.doctrine.coordinate_system:
        raise ValueError("classification coordinate_system must match computation truth")
    if classification.doctrine.converse != truth.doctrine.converse:
        raise ValueError("classification converse must match computation truth")
    if classification.uses_directed_arc != (truth.directed_arc_deg is not None):
        raise ValueError("classification uses_directed_arc must match computation truth")
    if classification.uses_reference_body != (truth.reference_body is not None):
        raise ValueError("classification uses_reference_body must match computation truth")
    if classification.uses_stepped_key != (truth.stepped_years is not None):
        raise ValueError("classification uses_stepped_key must match computation truth")
    if classification.uses_house_frame != (truth.doctrine.doctrine_family == "house_frame"):
        raise ValueError("classification uses_house_frame must match computation truth")
    if requires_house_frame and truth.doctrine.doctrine_family != "house_frame":
        raise ValueError("house-frame vessels require house_frame doctrine truth")
    if requires_house_frame and not classification.uses_house_frame:
        raise ValueError("house-frame vessels require house-frame classification")


def _build_progression_relation(
    truth: ProgressionComputationTruth,
    classification: ProgressionComputationClassification,
) -> ProgressionRelation:
    if classification.doctrine.doctrine_family == "house_frame":
        relation_kind = "house_frame_projection"
    elif classification.uses_directed_arc:
        relation_kind = "directing_arc"
    else:
        relation_kind = "time_key"

    if truth.reference_body == "Sun":
        basis = "solar_arc_reference"
    elif truth.reference_body == "Ascendant":
        basis = "ascendant_arc_reference"
    elif truth.doctrine.technique_name.startswith("Naibod"):
        basis = "naibod_rate"
    elif "Naibod" in truth.doctrine.technique_name:
        basis = "naibod_rate"
    elif truth.stepped_years is not None:
        basis = "stepped_time_key"
    elif classification.doctrine.doctrine_family == "house_frame":
        basis = "progressed_house_frame"
    else:
        basis = "continuous_time_key"

    return ProgressionRelation(
        technique_name=truth.doctrine.technique_name,
        relation_kind=relation_kind,
        basis=basis,
        reference_name=truth.reference_body,
        converse=classification.doctrine.converse,
        coordinate_system=classification.doctrine.coordinate_system,
    )


def _validate_progression_relation(
    relation: ProgressionRelation,
    truth: ProgressionComputationTruth,
    classification: ProgressionComputationClassification,
) -> None:
    if relation.technique_name != truth.doctrine.technique_name:
        raise ValueError("relation technique_name must match computation truth")
    if relation.converse != classification.doctrine.converse:
        raise ValueError("relation converse must match classification")
    if relation.coordinate_system != classification.doctrine.coordinate_system:
        raise ValueError("relation coordinate_system must match classification")
    if relation.reference_name != truth.reference_body:
        raise ValueError("relation reference_name must match computation truth")
    expected_kind = (
        "house_frame_projection"
        if classification.doctrine.doctrine_family == "house_frame"
        else "directing_arc"
        if classification.uses_directed_arc
        else "time_key"
    )
    if relation.relation_kind != expected_kind:
        raise ValueError("relation_kind must match computation truth")
    expected_basis = (
        "solar_arc_reference"
        if truth.reference_body == "Sun"
        else "ascendant_arc_reference"
        if truth.reference_body == "Ascendant"
        else "naibod_rate"
        if truth.doctrine.technique_name.startswith("Naibod") or "Naibod" in truth.doctrine.technique_name
        else "stepped_time_key"
        if truth.stepped_years is not None
        else "progressed_house_frame"
        if classification.doctrine.doctrine_family == "house_frame"
        else "continuous_time_key"
    )
    if relation.basis != expected_basis:
        raise ValueError("relation basis must match computation truth")
    if relation.relation_kind == "time_key" and relation.reference_name is not None:
        raise ValueError("time-key relations may not carry a reference_name")
    if relation.relation_kind == "house_frame_projection" and relation.reference_name is not None:
        raise ValueError("house-frame relations may not carry a reference_name")
    if relation.relation_kind == "directing_arc" and truth.reference_body is None and relation.basis != "naibod_rate":
        raise ValueError("non-Naibod directing arcs require a reference_name")


def _build_progression_condition_profile(
    classification: ProgressionComputationClassification,
    relation: ProgressionRelation,
) -> ProgressionConditionProfile:
    if classification.uses_house_frame:
        structural_state = "hybrid"
    elif classification.uses_directed_arc and classification.doctrine.application_mode == "uniform":
        structural_state = "uniform"
    else:
        structural_state = "differential"

    return ProgressionConditionProfile(
        technique_name=classification.doctrine.technique_name,
        doctrine_family=classification.doctrine.doctrine_family,
        relation_kind=relation.relation_kind,
        relation_basis=relation.basis,
        coordinate_system=classification.doctrine.coordinate_system,
        rate_mode=classification.doctrine.rate_mode,
        application_mode=classification.doctrine.application_mode,
        converse=classification.doctrine.converse,
        uses_directed_arc=classification.uses_directed_arc,
        uses_reference_body=classification.uses_reference_body,
        uses_stepped_key=classification.uses_stepped_key,
        uses_house_frame=classification.uses_house_frame,
        structural_state=structural_state,
    )


def _validate_progression_condition_profile(
    profile: ProgressionConditionProfile,
    classification: ProgressionComputationClassification,
    relation: ProgressionRelation,
) -> None:
    if profile.technique_name != classification.doctrine.technique_name:
        raise ValueError("condition profile technique_name must match classification")
    if profile.doctrine_family != classification.doctrine.doctrine_family:
        raise ValueError("condition profile doctrine_family must match classification")
    if profile.relation_kind != relation.relation_kind:
        raise ValueError("condition profile relation_kind must match relation")
    if profile.relation_basis != relation.basis:
        raise ValueError("condition profile relation_basis must match relation")
    if profile.coordinate_system != classification.doctrine.coordinate_system:
        raise ValueError("condition profile coordinate_system must match classification")
    if profile.rate_mode != classification.doctrine.rate_mode:
        raise ValueError("condition profile rate_mode must match classification")
    if profile.application_mode != classification.doctrine.application_mode:
        raise ValueError("condition profile application_mode must match classification")
    if profile.converse != classification.doctrine.converse:
        raise ValueError("condition profile converse must match classification")
    if profile.uses_directed_arc != classification.uses_directed_arc:
        raise ValueError("condition profile uses_directed_arc must match classification")
    if profile.uses_reference_body != classification.uses_reference_body:
        raise ValueError("condition profile uses_reference_body must match classification")
    if profile.uses_stepped_key != classification.uses_stepped_key:
        raise ValueError("condition profile uses_stepped_key must match classification")
    if profile.uses_house_frame != classification.uses_house_frame:
        raise ValueError("condition profile uses_house_frame must match classification")
    expected_state = (
        "hybrid"
        if classification.uses_house_frame
        else "uniform"
        if classification.uses_directed_arc and classification.doctrine.application_mode == "uniform"
        else "differential"
    )
    if profile.structural_state != expected_state:
        raise ValueError("condition profile structural_state must match classification")


def _condition_rank(profile: ProgressionConditionProfile) -> int:
    return {
        "differential": 0,
        "uniform": 1,
        "hybrid": 2,
    }[profile.structural_state]


def _condition_extreme_names(
    profiles: tuple[ProgressionConditionProfile, ...],
    *,
    strongest: bool,
) -> tuple[str, ...]:
    if not profiles:
        return ()
    ranked = [_condition_rank(profile) for profile in profiles]
    extreme = max(ranked) if strongest else min(ranked)
    return tuple(
        profile.technique_name
        for profile in profiles
        if _condition_rank(profile) == extreme
    )


def _network_extreme_node_labels(
    nodes: tuple[ProgressionConditionNetworkNode, ...],
) -> tuple[str, ...]:
    if not nodes:
        return ()
    max_degree = max(node.total_degree for node in nodes)
    return tuple(node.label for node in nodes if node.total_degree == max_degree)

@dataclass(slots=True)
class ProgressedPosition:
    """
    RITE: The Progressed Position Vessel

    THEOREM: Governs the storage of a single body's position in a progressed or
    directed chart.

    RITE OF PURPOSE:
        ProgressedPosition is the authoritative data vessel for a single body's
        ecliptic longitude in any progressed or directed chart produced by the
        Progression Engine. It captures the body name, longitude, speed, retrograde
        flag, and derived sign fields. Without it, callers would receive unstructured
        tuples with no field-level guarantees. It exists to give every higher-level
        consumer a single, named, mutable record of each progressed body position.

    LAW OF OPERATION:
        Responsibilities:
            - Store a single progressed body position as named, typed fields
            - Derive sign, sign_symbol, and sign_degree via __post_init__
            - Serve as a value inside ProgressedChart.positions
        Non-responsibilities:
            - Computing progressed positions (delegates to secondary_progression etc.)
            - Resolving body positions from ephemeris (delegates to planets)
        Dependencies:
            - sign, sign_symbol, sign_degree derived from sign_of(longitude) at init
        Structural invariants:
            - longitude is in [0, 360)
            - sign is a valid zodiac sign name
        Behavioral invariants:
            - sign fields are always consistent with longitude

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.progressions.ProgressedPosition",
      "risk": "high",
      "api": {
        "frozen": ["name", "longitude", "speed", "retrograde"],
        "internal": ["sign", "sign_symbol", "sign_degree"]
      },
      "state": {"mutable": true, "owners": ["secondary_progression", "solar_arc", "tertiary_progression", "converse_secondary_progression", "converse_solar_arc", "converse_tertiary_progression", "minor_progression", "converse_minor_progression"]},
      "effects": {
        "signals_emitted": [],
        "io": []
      },
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    name:        str
    longitude:   float
    speed:       float  = 0.0
    retrograde:  bool   = False
    sign:        str    = field(init=False)
    sign_symbol: str    = field(init=False)
    sign_degree: float  = field(init=False)

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("progressed position name must be a non-empty string")
        if not math.isfinite(self.longitude):
            raise ValueError("progressed position longitude must be finite")
        if not math.isfinite(self.speed):
            raise ValueError("progressed position speed must be finite")
        if not isinstance(self.retrograde, bool):
            raise ValueError("progressed position retrograde must be bool")
        self.sign, self.sign_symbol, self.sign_degree = sign_of(self.longitude)

    def __repr__(self) -> str:
        r = "R" if self.retrograde else " "
        return (f"{self.name:<10}{r} {self.longitude:>9.4f}  "
                f"{self.sign} {self.sign_degree:.2f}")


@dataclass(slots=True)
class ProgressedChart:
    """
    RITE: The Progressed Chart Vessel

    THEOREM: Governs the storage of a complete progressed or directed chart for a
    given real-world target date.

    RITE OF PURPOSE:
        ProgressedChart is the authoritative data vessel for a complete progressed
        or directed chart produced by the Progression Engine. It captures the chart
        type label, natal and progressed Julian Days, the real-world target date,
        the solar arc applied, and the full dictionary of progressed body positions.
        Without it, callers would receive unstructured collections with no
        field-level guarantees. It exists to give every higher-level consumer a
        single, named, mutable record of each complete progressed chart.

    LAW OF OPERATION:
        Responsibilities:
            - Store a complete progressed chart as named, typed fields
            - Expose UTC datetime and CalendarDateTime views via read-only properties
            - Serve as the return type of all progression functions
        Non-responsibilities:
            - Computing progressed positions (delegates to progression functions)
            - Resolving body positions from ephemeris (delegates to planets)
        Dependencies:
            - positions dict populated by the owning progression function
            - datetime_utc delegates to datetime_from_jd()
            - calendar_utc delegates to calendar_datetime_from_jd()
        Structural invariants:
            - chart_type is one of the recognised progression type labels
            - solar_arc_deg is 0.0 for non-solar-arc techniques
        Behavioral invariants:
            - All consumers treat ProgressedChart fields as read-only after construction

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.progressions.ProgressedChart",
      "risk": "high",
      "api": {
        "frozen": ["chart_type", "natal_jd_ut", "progressed_jd_ut", "target_date", "solar_arc_deg", "positions"],
        "internal": ["datetime_utc", "calendar_utc"]
      },
      "state": {"mutable": true, "owners": ["secondary_progression", "solar_arc", "tertiary_progression", "converse_secondary_progression", "converse_solar_arc", "converse_tertiary_progression", "minor_progression", "converse_minor_progression"]},
      "effects": {
        "signals_emitted": [],
        "io": []
      },
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    chart_type:       str          # "Secondary Progression" | "Solar Arc Direction"
    natal_jd_ut:      float
    progressed_jd_ut: float        # JD used to cast the chart (SP) or natal JD (SA)
    target_date:      datetime     # The real-world date for which we progressed
    solar_arc_deg:    float        # Arc applied (0 for SP, actual arc for SA)
    positions:        dict[str, ProgressedPosition]
    computation_truth: ProgressionComputationTruth | None = None
    classification: ProgressionComputationClassification | None = None
    relation: ProgressionRelation | None = None
    condition_profile: ProgressionConditionProfile | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.chart_type, str) or not self.chart_type.strip():
            raise ValueError("chart_type must be a non-empty string")
        _validate_natal_jd_ut(self.natal_jd_ut)
        if not math.isfinite(self.progressed_jd_ut):
            raise ValueError("progressed_jd_ut must be finite")
        if not math.isfinite(self.solar_arc_deg):
            raise ValueError("solar_arc_deg must be finite")
        _validate_target_date(self.target_date)
        for name, position in self.positions.items():
            if name != position.name:
                raise ValueError("positions keys must match progressed position names")
        _validate_progression_truth_and_classification(
            chart_type=self.chart_type,
            progressed_jd_ut=self.progressed_jd_ut,
            solar_arc_deg=self.solar_arc_deg,
            truth=self.computation_truth,
            classification=self.classification,
        )
        if self.relation is not None:
            if self.computation_truth is None or self.classification is None:
                raise ValueError("relation requires computation_truth and classification")
            _validate_progression_relation(self.relation, self.computation_truth, self.classification)
        if self.condition_profile is not None:
            if self.classification is None or self.relation is None:
                raise ValueError("condition_profile requires classification and relation")
            _validate_progression_condition_profile(self.condition_profile, self.classification, self.relation)

    @property
    def datetime_utc(self) -> datetime:
        return datetime_from_jd(self.progressed_jd_ut)

    @property
    def calendar_utc(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(self.progressed_jd_ut)

    @property
    def doctrine_family(self) -> str | None:
        return None if self.classification is None else self.classification.doctrine.doctrine_family

    @property
    def rate_mode(self) -> str | None:
        return None if self.classification is None else self.classification.doctrine.rate_mode

    @property
    def application_mode(self) -> str | None:
        return None if self.classification is None else self.classification.doctrine.application_mode

    @property
    def coordinate_system(self) -> str | None:
        return None if self.classification is None else self.classification.doctrine.coordinate_system

    @property
    def is_converse(self) -> bool:
        return False if self.classification is None else self.classification.doctrine.converse

    @property
    def uses_directed_arc(self) -> bool:
        return False if self.classification is None else self.classification.uses_directed_arc

    @property
    def uses_reference_body(self) -> bool:
        return False if self.classification is None else self.classification.uses_reference_body

    @property
    def uses_stepped_key(self) -> bool:
        return False if self.classification is None else self.classification.uses_stepped_key

    @property
    def relation_kind(self) -> str | None:
        return None if self.relation is None else self.relation.relation_kind

    @property
    def relation_basis(self) -> str | None:
        return None if self.relation is None else self.relation.basis

    @property
    def is_time_key_relation(self) -> bool:
        return self.relation_kind == "time_key"

    @property
    def is_directing_arc_relation(self) -> bool:
        return self.relation_kind == "directing_arc"

    @property
    def is_house_frame_relation(self) -> bool:
        return self.relation_kind == "house_frame_projection"

    @property
    def relation_reference_name(self) -> str | None:
        return None if self.relation is None else self.relation.reference_name

    @property
    def condition_state(self) -> str | None:
        return None if self.condition_profile is None else self.condition_profile.structural_state


@dataclass(slots=True)
class ProgressedHouseFrame:
    """
    Preserve a progressed local house frame with the same truth standards used
    for planetary progression charts.
    """

    chart_type: str
    natal_jd_ut: float
    progressed_jd_ut: float
    target_date: datetime
    houses: HouseCusps
    computation_truth: ProgressionComputationTruth
    classification: ProgressionComputationClassification | None = None
    relation: ProgressionRelation | None = None
    condition_profile: ProgressionConditionProfile | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.chart_type, str) or not self.chart_type.strip():
            raise ValueError("chart_type must be a non-empty string")
        _validate_natal_jd_ut(self.natal_jd_ut)
        if not math.isfinite(self.progressed_jd_ut):
            raise ValueError("progressed_jd_ut must be finite")
        _validate_target_date(self.target_date)
        _validate_progression_truth_and_classification(
            chart_type=self.chart_type,
            progressed_jd_ut=self.progressed_jd_ut,
            solar_arc_deg=None,
            truth=self.computation_truth,
            classification=self.classification,
            requires_house_frame=True,
        )
        if self.relation is None:
            raise ValueError("house-frame vessels require a progression relation")
        _validate_progression_relation(self.relation, self.computation_truth, self.classification)
        if self.condition_profile is None:
            raise ValueError("house-frame vessels require a condition_profile")
        _validate_progression_condition_profile(self.condition_profile, self.classification, self.relation)
        _validate_house_frame_inputs(
            latitude=self.computation_truth.latitude,
            longitude=self.computation_truth.longitude,
            system=self.computation_truth.house_system,
        )

    @property
    def datetime_utc(self) -> datetime:
        return datetime_from_jd(self.progressed_jd_ut)

    @property
    def calendar_utc(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(self.progressed_jd_ut)

    @property
    def doctrine_family(self) -> str:
        return self.classification.doctrine.doctrine_family

    @property
    def rate_mode(self) -> str:
        return self.classification.doctrine.rate_mode

    @property
    def application_mode(self) -> str:
        return self.classification.doctrine.application_mode

    @property
    def coordinate_system(self) -> str:
        return self.classification.doctrine.coordinate_system

    @property
    def uses_house_frame(self) -> bool:
        return self.classification.uses_house_frame

    @property
    def relation_kind(self) -> str:
        return self.relation.relation_kind

    @property
    def relation_basis(self) -> str:
        return self.relation.basis

    @property
    def is_house_frame_relation(self) -> bool:
        return self.relation_kind == "house_frame_projection"

    @property
    def relation_reference_name(self) -> str | None:
        return self.relation.reference_name

    @property
    def condition_state(self) -> str:
        return self.condition_profile.structural_state


_TROPICAL_YEAR = 365.24219
_SYNODIC_MONTH = 29.53058868
_NAIBOD_RATE_DEG_PER_YEAR = 0.98564733


@dataclass(frozen=True, slots=True)
class ProgressionTimeKeyPolicy:
    """Doctrine surface for time-key progression constants."""

    tropical_year_days: float = _TROPICAL_YEAR
    synodic_month_days: float = _SYNODIC_MONTH


@dataclass(frozen=True, slots=True)
class ProgressionDirectionPolicy:
    """Doctrine surface for arc-based progression constants."""

    naibod_rate_deg_per_year: float = _NAIBOD_RATE_DEG_PER_YEAR


@dataclass(frozen=True, slots=True)
class ProgressionHouseFramePolicy:
    """Doctrine surface for progressed house-frame techniques."""

    default_house_system: str = HouseSystem.PLACIDUS


@dataclass(frozen=True, slots=True)
class ProgressionComputationPolicy:
    """
    Lean doctrine surface for the progression subsystem.

    This governs only doctrine already embodied by the engine: time-key
    constants, Naibod rate, and default house-frame system.
    """

    time_key: ProgressionTimeKeyPolicy = ProgressionTimeKeyPolicy()
    directions: ProgressionDirectionPolicy = ProgressionDirectionPolicy()
    house_frame: ProgressionHouseFramePolicy = ProgressionHouseFramePolicy()


DEFAULT_PROGRESSION_POLICY = ProgressionComputationPolicy()


def _validate_policy(policy: ProgressionComputationPolicy) -> ProgressionComputationPolicy:
    if not isinstance(policy.time_key, ProgressionTimeKeyPolicy):
        raise TypeError("policy.time_key must be ProgressionTimeKeyPolicy")
    if not isinstance(policy.directions, ProgressionDirectionPolicy):
        raise TypeError("policy.directions must be ProgressionDirectionPolicy")
    if not isinstance(policy.house_frame, ProgressionHouseFramePolicy):
        raise TypeError("policy.house_frame must be ProgressionHouseFramePolicy")
    if policy.time_key.tropical_year_days <= 0:
        raise ValueError("policy.time_key.tropical_year_days must be positive")
    if policy.time_key.synodic_month_days <= 0:
        raise ValueError("policy.time_key.synodic_month_days must be positive")
    if policy.directions.naibod_rate_deg_per_year <= 0:
        raise ValueError("policy.directions.naibod_rate_deg_per_year must be positive")
    if not policy.house_frame.default_house_system:
        raise ValueError("policy.house_frame.default_house_system must be non-empty")
    if policy.house_frame.default_house_system not in HOUSE_SYSTEM_NAMES:
        raise ValueError("policy.house_frame.default_house_system must be a supported house system code")
    return policy


def _resolve_policy(policy: ProgressionComputationPolicy | None) -> ProgressionComputationPolicy:
    return _validate_policy(DEFAULT_PROGRESSION_POLICY if policy is None else policy)


def _validate_target_date(target_date: datetime) -> None:
    if not isinstance(target_date, datetime):
        raise TypeError("target_date must be a datetime")


def _validate_natal_jd_ut(natal_jd_ut: float) -> None:
    if not math.isfinite(natal_jd_ut):
        raise ValueError("natal_jd_ut must be finite")


def _validate_bodies(bodies: list[str] | None) -> None:
    if bodies is None:
        return
    seen: set[str] = set()
    for body in bodies:
        if not isinstance(body, str) or not body.strip():
            raise ValueError("bodies must contain non-empty strings")
        if body in seen:
            raise ValueError("bodies may not contain duplicates")
        seen.add(body)


def _validate_house_frame_inputs(latitude: float, longitude: float, system: str | None) -> None:
    if not isinstance(latitude, (int, float)) or not math.isfinite(latitude) or latitude < -90.0 or latitude > 90.0:
        raise ValueError("latitude must be finite and within [-90, 90]")
    if not isinstance(longitude, (int, float)) or not math.isfinite(longitude) or longitude < -180.0 or longitude > 180.0:
        raise ValueError("longitude must be finite and within [-180, 180]")
    if system is not None and system not in HOUSE_SYSTEM_NAMES:
        raise ValueError("system must be a supported house system code")


def _age_years(
    natal_jd_ut: float,
    target_date: datetime,
    tropical_year_days: float = _TROPICAL_YEAR,
) -> float:
    """Return tropical age in years for the target date."""

    _validate_natal_jd_ut(natal_jd_ut)
    _validate_target_date(target_date)
    return (jd_from_datetime(target_date) - natal_jd_ut) / tropical_year_days


def _default_bodies(bodies: list[str] | None) -> list[str]:
    """Normalize the body list used by progression techniques."""

    _validate_bodies(bodies)
    return list(Body.ALL_PLANETS) if bodies is None else list(bodies)


def _doctrine_truth(
    *,
    technique_name: str,
    doctrine_family: str,
    life_unit: str,
    ephemeris_unit: str,
    rate_mode: str,
    application_mode: str,
    coordinate_system: str,
    converse: bool = False,
) -> ProgressionDoctrineTruth:
    return ProgressionDoctrineTruth(
        technique_name=technique_name,
        doctrine_family=doctrine_family,
        life_unit=life_unit,
        ephemeris_unit=ephemeris_unit,
        rate_mode=rate_mode,
        application_mode=application_mode,
        coordinate_system=coordinate_system,
        converse=converse,
    )


def _classify_computation_truth(
    truth: ProgressionComputationTruth,
) -> ProgressionComputationClassification:
    doctrine = ProgressionDoctrineClassification(
        technique_name=truth.doctrine.technique_name,
        doctrine_family=truth.doctrine.doctrine_family,
        rate_mode=truth.doctrine.rate_mode,
        application_mode=truth.doctrine.application_mode,
        coordinate_system=truth.doctrine.coordinate_system,
        converse=truth.doctrine.converse,
    )
    return ProgressionComputationClassification(
        doctrine=doctrine,
        uses_directed_arc=truth.directed_arc_deg is not None,
        uses_reference_body=truth.reference_body is not None,
        uses_stepped_key=truth.stepped_years is not None,
        uses_house_frame=truth.doctrine.doctrine_family == "house_frame",
    )


def _uniform_longitude_direction(
    *,
    chart_type: str,
    natal_jd_ut: float,
    target_date: datetime,
    arc_deg: float,
    age_years: float,
    bodies: list[str] | None,
    reader: SpkReader,
    progressed_jd_ut: float,
) -> ProgressedChart:
    """
    Apply one uniform ecliptic-longitude arc to all natal bodies.

    SYMBOLIC KEY:
        - unit of life: tropical year
        - rate type: fixed or variable, supplied by caller as ``arc_deg``
        - application: uniform to all bodies
        - coordinate system: ecliptic longitude
    """

    _validate_natal_jd_ut(natal_jd_ut)
    _validate_target_date(target_date)
    if not math.isfinite(arc_deg):
        raise ValueError("arc_deg must be finite")
    if not math.isfinite(age_years):
        raise ValueError("age_years must be finite")
    if not math.isfinite(progressed_jd_ut):
        raise ValueError("progressed_jd_ut must be finite")
    resolved_bodies = _default_bodies(bodies)
    natal_raw = all_planets_at(natal_jd_ut, bodies=resolved_bodies, reader=reader)
    positions = {
        name: ProgressedPosition(
            name=name,
            longitude=(p.longitude + arc_deg) % 360.0,
            speed=p.speed,
            retrograde=p.retrograde,
        )
        for name, p in natal_raw.items()
    }
    truth = ProgressionComputationTruth(
        doctrine=_doctrine_truth(
            technique_name=chart_type,
            doctrine_family="uniform_arc",
            life_unit="tropical_year",
            ephemeris_unit="directing_arc_degree",
            rate_mode="variable" if "Solar Arc" in chart_type or "Ascendant Arc" in chart_type else "fixed",
            application_mode="uniform",
            coordinate_system="ecliptic_longitude",
            converse=chart_type.startswith("Converse "),
        ),
        target_jd_ut=jd_from_datetime(target_date),
        age_years=age_years,
        progressed_jd_ut=progressed_jd_ut,
        directed_arc_deg=arc_deg,
        reference_body="Sun" if "Solar Arc" in chart_type else ("Ascendant" if "Ascendant Arc" in chart_type else None),
    )
    classification = _classify_computation_truth(truth)
    relation = _build_progression_relation(truth, classification)
    return ProgressedChart(
        chart_type=chart_type,
        natal_jd_ut=natal_jd_ut,
        progressed_jd_ut=progressed_jd_ut,
        target_date=target_date,
        solar_arc_deg=arc_deg,
        positions=positions,
        computation_truth=truth,
        classification=classification,
        relation=relation,
        condition_profile=_build_progression_condition_profile(classification, relation),
    )


def _uniform_ra_direction(
    *,
    chart_type: str,
    natal_jd_ut: float,
    target_date: datetime,
    arc_deg: float,
    age_years: float,
    bodies: list[str] | None,
    reader: SpkReader,
    progressed_jd_ut: float,
) -> ProgressedChart:
    """
    Apply one uniform equatorial right-ascension arc to all natal bodies.

    SYMBOLIC KEY:
        - unit of life: tropical year
        - rate type: fixed or variable, supplied by caller as ``arc_deg``
        - application: uniform to all bodies
        - coordinate system: equatorial right ascension

    OPERATION:
        Each natal body's ecliptic longitude/latitude is converted to RA/Dec at
        the natal obliquity, the arc is added to RA while keeping declination
        fixed, and the result is projected back to ecliptic longitude.
    """

    _validate_natal_jd_ut(natal_jd_ut)
    _validate_target_date(target_date)
    if not math.isfinite(arc_deg):
        raise ValueError("arc_deg must be finite")
    if not math.isfinite(age_years):
        raise ValueError("age_years must be finite")
    if not math.isfinite(progressed_jd_ut):
        raise ValueError("progressed_jd_ut must be finite")
    eps = true_obliquity(ut_to_tt(natal_jd_ut))
    resolved_bodies = _default_bodies(bodies)
    natal_raw = all_planets_at(natal_jd_ut, bodies=resolved_bodies, reader=reader)
    positions: dict[str, ProgressedPosition] = {}
    for name, p in natal_raw.items():
        ra, dec = ecliptic_to_equatorial(p.longitude, p.latitude, eps)
        lon, _lat = equatorial_to_ecliptic((ra + arc_deg) % 360.0, dec, eps)
        positions[name] = ProgressedPosition(
            name=name,
            longitude=lon % 360.0,
            speed=p.speed,
            retrograde=p.retrograde,
        )
    truth = ProgressionComputationTruth(
        doctrine=_doctrine_truth(
            technique_name=chart_type,
            doctrine_family="uniform_arc",
            life_unit="tropical_year",
            ephemeris_unit="directing_arc_degree",
            rate_mode="variable" if "Solar Arc" in chart_type else "fixed",
            application_mode="uniform",
            coordinate_system="right_ascension",
            converse=chart_type.startswith("Converse "),
        ),
        target_jd_ut=jd_from_datetime(target_date),
        age_years=age_years,
        progressed_jd_ut=progressed_jd_ut,
        directed_arc_deg=arc_deg,
        reference_body="Sun" if "Solar Arc" in chart_type else None,
    )
    classification = _classify_computation_truth(truth)
    relation = _build_progression_relation(truth, classification)
    return ProgressedChart(
        chart_type=chart_type,
        natal_jd_ut=natal_jd_ut,
        progressed_jd_ut=progressed_jd_ut,
        target_date=target_date,
        solar_arc_deg=arc_deg,
        positions=positions,
        computation_truth=truth,
        classification=classification,
        relation=relation,
        condition_profile=_build_progression_condition_profile(classification, relation),
    )


def _time_key_chart(
    *,
    chart_type: str,
    natal_jd_ut: float,
    target_date: datetime,
    progressed_jd_ut: float,
    age_years: float,
    bodies: list[str] | None,
    reader: SpkReader,
    life_unit: str,
    ephemeris_unit: str,
    rate_mode: str,
    converse: bool = False,
    stepped_years: int | None = None,
) -> ProgressedChart:
    _validate_natal_jd_ut(natal_jd_ut)
    _validate_target_date(target_date)
    if not math.isfinite(progressed_jd_ut):
        raise ValueError("progressed_jd_ut must be finite")
    if not math.isfinite(age_years):
        raise ValueError("age_years must be finite")
    raw = all_planets_at(progressed_jd_ut, bodies=_default_bodies(bodies), reader=reader)
    positions = {
        name: ProgressedPosition(
            name=name,
            longitude=p.longitude,
            speed=p.speed,
            retrograde=p.retrograde,
        )
        for name, p in raw.items()
    }
    truth = ProgressionComputationTruth(
        doctrine=_doctrine_truth(
            technique_name=chart_type,
            doctrine_family="time_key",
            life_unit=life_unit,
            ephemeris_unit=ephemeris_unit,
            rate_mode=rate_mode,
            application_mode="differential",
            coordinate_system="ecliptic_longitude",
            converse=converse,
        ),
        target_jd_ut=jd_from_datetime(target_date),
        age_years=age_years,
        progressed_jd_ut=progressed_jd_ut,
        stepped_years=stepped_years,
    )
    classification = _classify_computation_truth(truth)
    relation = _build_progression_relation(truth, classification)
    return ProgressedChart(
        chart_type=chart_type,
        natal_jd_ut=natal_jd_ut,
        progressed_jd_ut=progressed_jd_ut,
        target_date=target_date,
        solar_arc_deg=0.0,
        positions=positions,
        computation_truth=truth,
        classification=classification,
        relation=relation,
        condition_profile=_build_progression_condition_profile(classification, relation),
    )


def daily_house_frame(
    natal_jd_ut: float,
    target_date: datetime,
    latitude: float,
    longitude: float,
    system: str | None = None,
    policy: ProgressionComputationPolicy | None = None,
) -> ProgressedHouseFrame:
    """
    Preserve the progressed house frame with its symbolic key and progressed date.
    """

    resolved_policy = _resolve_policy(policy)
    _validate_natal_jd_ut(natal_jd_ut)
    _validate_target_date(target_date)
    _validate_house_frame_inputs(latitude, longitude, system)
    resolved_system = resolved_policy.house_frame.default_house_system if system is None else system
    age_years = _age_years(natal_jd_ut, target_date, resolved_policy.time_key.tropical_year_days)
    progressed_jd_ut = natal_jd_ut + age_years
    houses = calculate_houses(progressed_jd_ut, latitude, longitude, system=resolved_system)
    truth = ProgressionComputationTruth(
        doctrine=_doctrine_truth(
            technique_name="Daily Houses",
            doctrine_family="house_frame",
            life_unit="tropical_year",
            ephemeris_unit="day_after_birth",
            rate_mode="variable",
            application_mode="differential",
            coordinate_system="local_house_frame",
        ),
        target_jd_ut=jd_from_datetime(target_date),
        age_years=age_years,
        progressed_jd_ut=progressed_jd_ut,
        latitude=latitude,
        longitude=longitude,
        house_system=resolved_system,
    )
    classification = _classify_computation_truth(truth)
    relation = _build_progression_relation(truth, classification)
    return ProgressedHouseFrame(
        chart_type="Daily Houses",
        natal_jd_ut=natal_jd_ut,
        progressed_jd_ut=progressed_jd_ut,
        target_date=target_date,
        houses=houses,
        computation_truth=truth,
        classification=classification,
        relation=relation,
        condition_profile=_build_progression_condition_profile(classification, relation),
    )


# ---------------------------------------------------------------------------
# Secondary Progressions
# ---------------------------------------------------------------------------

def secondary_progression(
    natal_jd_ut: float,
    target_date: datetime,
    bodies: list[str] | None = None,
    reader: SpkReader | None = None,
    policy: ProgressionComputationPolicy | None = None,
) -> ProgressedChart:
    """
    Calculate Secondary Progressed chart.

    One solar year of life = one day after birth.

    Parameters
    ----------
    natal_jd_ut : Julian Day (UT) of birth
    target_date : real-world date for which to calculate progressions
    bodies      : list of Body.* constants (defaults to all planets)
    reader      : SpkReader instance

    Returns
    -------
    ProgressedChart with chart_type="Secondary Progression"
    """
    if reader is None:
        reader = get_reader()
    resolved_policy = _resolve_policy(policy)

    # Age in tropical years at target_date
    age_years = _age_years(natal_jd_ut, target_date, resolved_policy.time_key.tropical_year_days)

    # Progressed JD = natal + age as days
    prog_jd = natal_jd_ut + age_years

    if bodies is None:
        bodies = list(Body.ALL_PLANETS)

    return _time_key_chart(
        chart_type="Secondary Progression",
        natal_jd_ut=natal_jd_ut,
        target_date=target_date,
        progressed_jd_ut=prog_jd,
        age_years=age_years,
        bodies=bodies,
        reader=reader,
        life_unit="tropical_year",
        ephemeris_unit="day_after_birth",
        rate_mode="variable",
    )


# ---------------------------------------------------------------------------
# Solar Arc Directions
# ---------------------------------------------------------------------------

def solar_arc(
    natal_jd_ut: float,
    target_date: datetime,
    bodies: list[str] | None = None,
    reader: SpkReader | None = None,
    policy: ProgressionComputationPolicy | None = None,
) -> ProgressedChart:
    """
    Calculate Solar Arc Direction chart.

    Arc = Progressed Sun − Natal Sun.
    Every natal point is advanced by that arc.

    Parameters
    ----------
    natal_jd_ut : Julian Day (UT) of birth
    target_date : real-world date for which to calculate directions
    bodies      : list of Body.* constants (defaults to all planets)
    reader      : SpkReader instance

    Returns
    -------
    ProgressedChart with chart_type="Solar Arc Direction"
    """
    if reader is None:
        reader = get_reader()
    resolved_policy = _resolve_policy(policy)

    if bodies is None:
        bodies = list(Body.ALL_PLANETS)

    # Natal Sun
    natal_sun  = planet_at(Body.SUN, natal_jd_ut, reader=reader).longitude

    # Progressed Sun (secondary progression date)
    age_years = _age_years(natal_jd_ut, target_date, resolved_policy.time_key.tropical_year_days)
    prog_jd    = natal_jd_ut + age_years
    prog_sun   = planet_at(Body.SUN, prog_jd, reader=reader).longitude

    # Solar arc (forward direction, 0–360)
    arc = (prog_sun - natal_sun) % 360.0

    return _uniform_longitude_direction(
        chart_type="Solar Arc Direction",
        natal_jd_ut=natal_jd_ut,
        target_date=target_date,
        arc_deg=arc,
        age_years=age_years,
        bodies=bodies,
        reader=reader,
        progressed_jd_ut=prog_jd,
    )


def naibod_longitude(
    natal_jd_ut: float,
    target_date: datetime,
    bodies: list[str] | None = None,
    reader: SpkReader | None = None,
    policy: ProgressionComputationPolicy | None = None,
) -> ProgressedChart:
    """
    Naibod in longitude: fixed mean solar motion applied uniformly in longitude.

    SYMBOLIC KEY:
        - unit of ephemeris time per unit of life: fixed 0.98564733° per year
        - rate type: fixed
        - application: uniform to all bodies
        - coordinate system: ecliptic longitude
    """
    if reader is None:
        reader = get_reader()
    resolved_policy = _resolve_policy(policy)

    age_years = _age_years(natal_jd_ut, target_date, resolved_policy.time_key.tropical_year_days)
    arc = (age_years * resolved_policy.directions.naibod_rate_deg_per_year) % 360.0
    return _uniform_longitude_direction(
        chart_type="Naibod in Longitude",
        natal_jd_ut=natal_jd_ut,
        target_date=target_date,
        arc_deg=arc,
        age_years=age_years,
        bodies=bodies,
        reader=reader,
        progressed_jd_ut=natal_jd_ut,
    )


def converse_naibod_longitude(
    natal_jd_ut: float,
    target_date: datetime,
    bodies: list[str] | None = None,
    reader: SpkReader | None = None,
    policy: ProgressionComputationPolicy | None = None,
) -> ProgressedChart:
    """
    Converse Naibod in longitude: fixed mean solar motion applied in reverse.

    SYMBOLIC KEY:
        - unit of ephemeris time per unit of life: fixed 0.98564733° per year
        - rate type: fixed
        - application: uniform to all bodies
        - coordinate system: ecliptic longitude
    """
    if reader is None:
        reader = get_reader()
    resolved_policy = _resolve_policy(policy)

    age_years = _age_years(natal_jd_ut, target_date, resolved_policy.time_key.tropical_year_days)
    arc = (-(age_years * resolved_policy.directions.naibod_rate_deg_per_year)) % 360.0
    return _uniform_longitude_direction(
        chart_type="Converse Naibod in Longitude",
        natal_jd_ut=natal_jd_ut,
        target_date=target_date,
        arc_deg=arc,
        age_years=age_years,
        bodies=bodies,
        reader=reader,
        progressed_jd_ut=natal_jd_ut,
    )


def naibod_right_ascension(
    natal_jd_ut: float,
    target_date: datetime,
    bodies: list[str] | None = None,
    reader: SpkReader | None = None,
    policy: ProgressionComputationPolicy | None = None,
) -> ProgressedChart:
    """
    Naibod in right ascension: fixed mean solar motion measured on the equator.

    SYMBOLIC KEY:
        - unit of ephemeris time per unit of life: fixed 0.98564733° per year
        - rate type: fixed
        - application: uniform to all bodies
        - coordinate system: equatorial right ascension
    """
    if reader is None:
        reader = get_reader()
    resolved_policy = _resolve_policy(policy)

    age_years = _age_years(natal_jd_ut, target_date, resolved_policy.time_key.tropical_year_days)
    arc = (age_years * resolved_policy.directions.naibod_rate_deg_per_year) % 360.0
    return _uniform_ra_direction(
        chart_type="Naibod in Right Ascension",
        natal_jd_ut=natal_jd_ut,
        target_date=target_date,
        arc_deg=arc,
        age_years=age_years,
        bodies=bodies,
        reader=reader,
        progressed_jd_ut=natal_jd_ut,
    )


def converse_naibod_right_ascension(
    natal_jd_ut: float,
    target_date: datetime,
    bodies: list[str] | None = None,
    reader: SpkReader | None = None,
    policy: ProgressionComputationPolicy | None = None,
) -> ProgressedChart:
    """
    Converse Naibod in right ascension: fixed equatorial rate applied in reverse.

    SYMBOLIC KEY:
        - unit of ephemeris time per unit of life: fixed 0.98564733° per year
        - rate type: fixed
        - application: uniform to all bodies
        - coordinate system: equatorial right ascension
    """
    if reader is None:
        reader = get_reader()
    resolved_policy = _resolve_policy(policy)

    age_years = _age_years(natal_jd_ut, target_date, resolved_policy.time_key.tropical_year_days)
    arc = (-(age_years * resolved_policy.directions.naibod_rate_deg_per_year)) % 360.0
    return _uniform_ra_direction(
        chart_type="Converse Naibod in Right Ascension",
        natal_jd_ut=natal_jd_ut,
        target_date=target_date,
        arc_deg=arc,
        age_years=age_years,
        bodies=bodies,
        reader=reader,
        progressed_jd_ut=natal_jd_ut,
    )


def solar_arc_right_ascension(
    natal_jd_ut: float,
    target_date: datetime,
    bodies: list[str] | None = None,
    reader: SpkReader | None = None,
    policy: ProgressionComputationPolicy | None = None,
) -> ProgressedChart:
    """
    Solar arc in right ascension: actual Sun arc measured on the equator.

    SYMBOLIC KEY:
        - unit of ephemeris time per unit of life: one tropical year = one day
          after birth for the progressed Sun reference date
        - rate type: variable, measured from natal Sun RA to progressed Sun RA
        - application: uniform to all bodies
        - coordinate system: equatorial right ascension
    """
    if reader is None:
        reader = get_reader()
    resolved_policy = _resolve_policy(policy)

    age_years = _age_years(natal_jd_ut, target_date, resolved_policy.time_key.tropical_year_days)
    prog_jd = natal_jd_ut + age_years
    eps_natal = true_obliquity(ut_to_tt(natal_jd_ut))
    eps_prog = true_obliquity(ut_to_tt(prog_jd))
    natal_sun = planet_at(Body.SUN, natal_jd_ut, reader=reader)
    prog_sun = planet_at(Body.SUN, prog_jd, reader=reader)
    natal_ra, _ = ecliptic_to_equatorial(natal_sun.longitude, natal_sun.latitude, eps_natal)
    prog_ra, _ = ecliptic_to_equatorial(prog_sun.longitude, prog_sun.latitude, eps_prog)
    arc = (prog_ra - natal_ra) % 360.0
    return _uniform_ra_direction(
        chart_type="Solar Arc in Right Ascension",
        natal_jd_ut=natal_jd_ut,
        target_date=target_date,
        arc_deg=arc,
        age_years=age_years,
        bodies=bodies,
        reader=reader,
        progressed_jd_ut=prog_jd,
    )


def converse_solar_arc_right_ascension(
    natal_jd_ut: float,
    target_date: datetime,
    bodies: list[str] | None = None,
    reader: SpkReader | None = None,
    policy: ProgressionComputationPolicy | None = None,
) -> ProgressedChart:
    """
    Converse solar arc in right ascension: actual Sun RA arc applied in reverse.

    SYMBOLIC KEY:
        - unit of ephemeris time per unit of life: one tropical year = one day
          after birth for the progressed Sun reference date
        - rate type: variable, measured from natal Sun RA to progressed Sun RA
        - application: uniform to all bodies
        - coordinate system: equatorial right ascension
    """
    if reader is None:
        reader = get_reader()
    resolved_policy = _resolve_policy(policy)

    forward = solar_arc_right_ascension(
        natal_jd_ut,
        target_date,
        bodies=bodies,
        reader=reader,
        policy=resolved_policy,
    )
    return _uniform_ra_direction(
        chart_type="Converse Solar Arc in Right Ascension",
        natal_jd_ut=natal_jd_ut,
        target_date=target_date,
        arc_deg=(-forward.solar_arc_deg) % 360.0,
        age_years=forward.computation_truth.age_years if forward.computation_truth is not None else _age_years(
            natal_jd_ut,
            target_date,
            resolved_policy.time_key.tropical_year_days,
        ),
        bodies=bodies,
        reader=reader,
        progressed_jd_ut=forward.progressed_jd_ut,
    )


# ---------------------------------------------------------------------------
# Tertiary Progressions (1 day = 1 lunar month)
# ---------------------------------------------------------------------------

def tertiary_progression(
    natal_jd_ut: float,
    target_date: datetime,
    bodies: list[str] | None = None,
    reader: SpkReader | None = None,
    policy: ProgressionComputationPolicy | None = None,
) -> ProgressedChart:
    """
    Tertiary progressions: one synodic month (~29.53 days) = one year of life.

    Parameters
    ----------
    natal_jd_ut : Julian Day (UT) of birth
    target_date : real-world date for which to calculate progressions
    """
    if reader is None:
        reader = get_reader()
    resolved_policy = _resolve_policy(policy)

    age_years = _age_years(natal_jd_ut, target_date, resolved_policy.time_key.tropical_year_days)
    prog_jd = natal_jd_ut + age_years * (
        resolved_policy.time_key.synodic_month_days / resolved_policy.time_key.tropical_year_days
    )

    if bodies is None:
        bodies = list(Body.ALL_PLANETS)

    return _time_key_chart(
        chart_type="Tertiary Progression",
        natal_jd_ut=natal_jd_ut,
        target_date=target_date,
        progressed_jd_ut=prog_jd,
        age_years=age_years,
        bodies=bodies,
        reader=reader,
        life_unit="tropical_year",
        ephemeris_unit="synodic_month_fraction",
        rate_mode="variable",
    )


# ---------------------------------------------------------------------------
# Converse Tertiary Progression
# ---------------------------------------------------------------------------

def converse_tertiary_progression(
    natal_jd_ut: float,
    target_date: datetime,
    bodies: list[str] | None = None,
    reader: SpkReader | None = None,
    policy: ProgressionComputationPolicy | None = None,
) -> ProgressedChart:
    """
    Converse tertiary progressions: reverse the current tertiary mapping rule.

    Under the current embodied doctrine, tertiary progression advances the
    ephemeris date by ``age_years * synodic_month / tropical_year`` days.
    Converse tertiary progression applies that same mapping in reverse.
    """
    if reader is None:
        reader = get_reader()
    resolved_policy = _resolve_policy(policy)

    age_years = _age_years(natal_jd_ut, target_date, resolved_policy.time_key.tropical_year_days)
    prog_jd = natal_jd_ut - age_years * (
        resolved_policy.time_key.synodic_month_days / resolved_policy.time_key.tropical_year_days
    )

    if bodies is None:
        bodies = list(Body.ALL_PLANETS)

    return _time_key_chart(
        chart_type="Converse Tertiary Progression",
        natal_jd_ut=natal_jd_ut,
        target_date=target_date,
        progressed_jd_ut=prog_jd,
        age_years=age_years,
        bodies=bodies,
        reader=reader,
        life_unit="tropical_year",
        ephemeris_unit="synodic_month_fraction",
        rate_mode="variable",
        converse=True,
    )


def tertiary_ii_progression(
    natal_jd_ut: float,
    target_date: datetime,
    bodies: list[str] | None = None,
    reader: SpkReader | None = None,
    policy: ProgressionComputationPolicy | None = None,
) -> ProgressedChart:
    """
    Tertiary II / Klaus Wessel: one synodic month of ephemeris time per life year,
    stepped by completed years rather than continuously.

    SYMBOLIC KEY:
        - unit of ephemeris time per unit of life: one synodic month = one year
        - rate type: fixed stepped time key
        - application: differential, because bodies are read from the ephemeris
          at the stepped progressed date rather than moved by one common arc
        - coordinate system: native ecliptic longitude of the ephemeris result
    """
    if reader is None:
        reader = get_reader()
    resolved_policy = _resolve_policy(policy)

    age_years = _age_years(natal_jd_ut, target_date, resolved_policy.time_key.tropical_year_days)
    completed_years = int(age_years)
    prog_jd = natal_jd_ut + completed_years * resolved_policy.time_key.synodic_month_days

    return _time_key_chart(
        chart_type="Tertiary II Progression",
        natal_jd_ut=natal_jd_ut,
        target_date=target_date,
        progressed_jd_ut=prog_jd,
        age_years=age_years,
        bodies=bodies,
        reader=reader,
        life_unit="completed_life_year",
        ephemeris_unit="synodic_month",
        rate_mode="stepped",
        stepped_years=completed_years,
    )


def converse_tertiary_ii_progression(
    natal_jd_ut: float,
    target_date: datetime,
    bodies: list[str] | None = None,
    reader: SpkReader | None = None,
    policy: ProgressionComputationPolicy | None = None,
) -> ProgressedChart:
    """
    Converse Tertiary II / Klaus Wessel: reverse-stepped synodic-month key.

    SYMBOLIC KEY:
        - unit of ephemeris time per unit of life: one synodic month = one year
        - rate type: fixed stepped time key
        - application: differential, because bodies are read from the ephemeris
          at the stepped progressed date rather than moved by one common arc
        - coordinate system: native ecliptic longitude of the ephemeris result
    """
    if reader is None:
        reader = get_reader()
    resolved_policy = _resolve_policy(policy)

    age_years = _age_years(natal_jd_ut, target_date, resolved_policy.time_key.tropical_year_days)
    completed_years = int(age_years)
    prog_jd = natal_jd_ut - completed_years * resolved_policy.time_key.synodic_month_days

    return _time_key_chart(
        chart_type="Converse Tertiary II Progression",
        natal_jd_ut=natal_jd_ut,
        target_date=target_date,
        progressed_jd_ut=prog_jd,
        age_years=age_years,
        bodies=bodies,
        reader=reader,
        life_unit="completed_life_year",
        ephemeris_unit="synodic_month",
        rate_mode="stepped",
        converse=True,
        stepped_years=completed_years,
    )


# ---------------------------------------------------------------------------
# Converse Secondary Progression
# ---------------------------------------------------------------------------

def converse_secondary_progression(
    natal_jd_ut: float,
    target_date: datetime,
    bodies: list[str] | None = None,
    reader: SpkReader | None = None,
    policy: ProgressionComputationPolicy | None = None,
) -> ProgressedChart:
    """
    Converse secondary progression: go BACKWARD from birth.

    Instead of advancing the chart forward (natal_JD + age_days),
    the converse chart goes backward: natal_JD − age_years.

    Used to find when progressed planets conjunct natal positions from
    the other direction, and in rectification work.

    Parameters
    ----------
    natal_jd_ut : Julian Day (UT) of birth
    target_date : real-world date for which to calculate
    bodies      : list of Body.* constants (defaults to all planets)
    reader      : SpkReader instance
    """
    if reader is None:
        reader = get_reader()
    resolved_policy = _resolve_policy(policy)

    age_years = _age_years(natal_jd_ut, target_date, resolved_policy.time_key.tropical_year_days)

    # Converse: go BACKWARD from natal by age_years (as days)
    prog_jd = natal_jd_ut - age_years

    if bodies is None:
        bodies = list(Body.ALL_PLANETS)

    return _time_key_chart(
        chart_type="Converse Secondary Progression",
        natal_jd_ut=natal_jd_ut,
        target_date=target_date,
        progressed_jd_ut=prog_jd,
        age_years=age_years,
        bodies=bodies,
        reader=reader,
        life_unit="tropical_year",
        ephemeris_unit="day_after_birth",
        rate_mode="variable",
        converse=True,
    )


# ---------------------------------------------------------------------------
# Converse Solar Arc
# ---------------------------------------------------------------------------

def converse_solar_arc(
    natal_jd_ut: float,
    target_date: datetime,
    bodies: list[str] | None = None,
    reader: SpkReader | None = None,
    policy: ProgressionComputationPolicy | None = None,
) -> ProgressedChart:
    """
    Converse solar arc: apply the solar arc in REVERSE (subtract from natal).

    Arc = progressed Sun − natal Sun (same as forward solar arc).
    Converse: each natal point is SUBTRACTED by that arc.

    Used alongside standard solar arc to find additional direction hits.

    Parameters
    ----------
    natal_jd_ut : Julian Day (UT) of birth
    target_date : real-world date for which to calculate
    bodies      : list of Body.* constants (defaults to all planets)
    reader      : SpkReader instance
    """
    if reader is None:
        reader = get_reader()
    resolved_policy = _resolve_policy(policy)

    if bodies is None:
        bodies = list(Body.ALL_PLANETS)

    # Natal Sun
    natal_sun = planet_at(Body.SUN, natal_jd_ut, reader=reader).longitude

    # Progressed Sun (secondary progression date)
    age_years = _age_years(natal_jd_ut, target_date, resolved_policy.time_key.tropical_year_days)
    prog_jd    = natal_jd_ut + age_years
    prog_sun   = planet_at(Body.SUN, prog_jd, reader=reader).longitude

    # Solar arc (same magnitude as forward, but applied in reverse)
    arc = (prog_sun - natal_sun) % 360.0

    return _uniform_longitude_direction(
        chart_type="Converse Solar Arc",
        natal_jd_ut=natal_jd_ut,
        target_date=target_date,
        arc_deg=-arc,
        age_years=age_years,
        bodies=bodies,
        reader=reader,
        progressed_jd_ut=prog_jd,
    )


def ascendant_arc(
    natal_jd_ut: float,
    target_date: datetime,
    latitude: float,
    longitude: float,
    system: str | None = None,
    bodies: list[str] | None = None,
    reader: SpkReader | None = None,
    policy: ProgressionComputationPolicy | None = None,
) -> ProgressedChart:
    """
    Ascendant arc: variable directing rate measured from the progressed Ascendant.

    SYMBOLIC KEY:
        - unit of ephemeris time per unit of life: one tropical year = one day
          after birth for the progressed Ascendant reference date
        - rate type: variable, measured from natal Ascendant to progressed Ascendant
        - application: uniform to all bodies
        - coordinate system: ecliptic longitude
    """
    if reader is None:
        reader = get_reader()
    resolved_policy = _resolve_policy(policy)
    _validate_house_frame_inputs(latitude, longitude, system)

    age_years = _age_years(natal_jd_ut, target_date, resolved_policy.time_key.tropical_year_days)
    prog_jd = natal_jd_ut + age_years
    resolved_system = resolved_policy.house_frame.default_house_system if system is None else system
    natal_houses = calculate_houses(natal_jd_ut, latitude, longitude, system=resolved_system)
    progressed_houses = calculate_houses(prog_jd, latitude, longitude, system=resolved_system)
    arc = (progressed_houses.asc - natal_houses.asc) % 360.0
    return _uniform_longitude_direction(
        chart_type="Ascendant Arc Direction",
        natal_jd_ut=natal_jd_ut,
        target_date=target_date,
        arc_deg=arc,
        age_years=age_years,
        bodies=bodies,
        reader=reader,
        progressed_jd_ut=prog_jd,
    )


# ---------------------------------------------------------------------------
# Minor Progressions
# ---------------------------------------------------------------------------

def minor_progression(
    natal_jd_ut: float,
    target_date: datetime,
    bodies: list[str] | None = None,
    reader: SpkReader | None = None,
    policy: ProgressionComputationPolicy | None = None,
) -> ProgressedChart:
    """
    Minor progressions: one lunar month = one year of life.

    The progressed JD advances by (age_years × synodic_month / year).
    Slower than secondary progressions (29.53 days instead of 365.25),
    giving a different rhythm to the progressed planets.

    Progressed JD = natal_JD + (age_years × 29.53058868 / 365.24219)

    Parameters
    ----------
    natal_jd_ut : Julian Day (UT) of birth
    target_date : real-world date for which to calculate progressions
    bodies      : list of Body.* constants (defaults to all planets)
    reader      : SpkReader instance
    """
    if reader is None:
        reader = get_reader()
    resolved_policy = _resolve_policy(policy)

    age_years = _age_years(natal_jd_ut, target_date, resolved_policy.time_key.tropical_year_days)
    prog_jd = natal_jd_ut + age_years * (
        resolved_policy.time_key.synodic_month_days / resolved_policy.time_key.tropical_year_days
    )

    if bodies is None:
        bodies = list(Body.ALL_PLANETS)

    return _time_key_chart(
        chart_type="Minor Progression",
        natal_jd_ut=natal_jd_ut,
        target_date=target_date,
        progressed_jd_ut=prog_jd,
        age_years=age_years,
        bodies=bodies,
        reader=reader,
        life_unit="tropical_year",
        ephemeris_unit="synodic_month_fraction",
        rate_mode="variable",
    )


def converse_minor_progression(
    natal_jd_ut: float,
    target_date: datetime,
    bodies: list[str] | None = None,
    reader: SpkReader | None = None,
    policy: ProgressionComputationPolicy | None = None,
) -> ProgressedChart:
    """
    Converse minor progressions: reverse the current minor mapping rule.

    Under the current embodied doctrine, minor progression shares the same
    synodic-month mapping rule as tertiary progression. The converse form
    applies that same embodied rule backward from the natal date.
    """
    if reader is None:
        reader = get_reader()
    resolved_policy = _resolve_policy(policy)

    age_years = _age_years(natal_jd_ut, target_date, resolved_policy.time_key.tropical_year_days)
    prog_jd = natal_jd_ut - age_years * (
        resolved_policy.time_key.synodic_month_days / resolved_policy.time_key.tropical_year_days
    )

    if bodies is None:
        bodies = list(Body.ALL_PLANETS)

    return _time_key_chart(
        chart_type="Converse Minor Progression",
        natal_jd_ut=natal_jd_ut,
        target_date=target_date,
        progressed_jd_ut=prog_jd,
        age_years=age_years,
        bodies=bodies,
        reader=reader,
        life_unit="tropical_year",
        ephemeris_unit="synodic_month_fraction",
        rate_mode="variable",
        converse=True,
    )


def daily_houses(
    natal_jd_ut: float,
    target_date: datetime,
    latitude: float,
    longitude: float,
    system: str | None = None,
    policy: ProgressionComputationPolicy | None = None,
) -> HouseCusps:
    """
    Daily Houses: apply the one-day-one-year key to the local house frame.

    SYMBOLIC KEY:
        - unit of ephemeris time per unit of life: one tropical year = one day
          after birth for the progressed house frame
        - rate type: variable through Earth rotation at the progressed date/time
        - application: differential to the local angles and cusps, not uniform
          to planetary positions
        - coordinate system: local house frame derived from ARMC and ecliptic cusps
    """
    return daily_house_frame(
        natal_jd_ut,
        target_date,
        latitude,
        longitude,
        system=system,
        policy=policy,
    ).houses


def progression_relation(chart: ProgressedChart) -> ProgressionRelation:
    """Return the formal directing relation preserved on a progressed chart."""

    if chart.relation is None:
        raise ValueError("progressed chart does not carry a progression relation")
    return chart.relation


def house_frame_relation(frame: ProgressedHouseFrame) -> ProgressionRelation:
    """Return the formal directing relation preserved on a progressed house frame."""

    return frame.relation


def progression_condition_profile(chart: ProgressedChart) -> ProgressionConditionProfile:
    """Return the integrated condition profile preserved on a progressed chart."""

    if chart.condition_profile is None:
        raise ValueError("progressed chart does not carry a condition profile")
    return chart.condition_profile


def house_frame_condition_profile(frame: ProgressedHouseFrame) -> ProgressionConditionProfile:
    """Return the integrated condition profile preserved on a progressed house frame."""

    return frame.condition_profile


def progression_chart_condition_profile(
    charts: list[ProgressedChart] | None = None,
    house_frames: list[ProgressedHouseFrame] | None = None,
) -> ProgressionChartConditionProfile:
    """
    Aggregate progression condition profiles into a deterministic chart-wide profile.

    The current structural ranking used for strongest/weakest summaries is:
    ``hybrid`` > ``uniform`` > ``differential``.
    """

    chart_profiles = [] if charts is None else [progression_condition_profile(chart) for chart in charts]
    house_profiles = [] if house_frames is None else [house_frame_condition_profile(frame) for frame in house_frames]
    profiles = tuple(
        sorted(
            [*chart_profiles, *house_profiles],
            key=lambda profile: (
                profile.technique_name,
                profile.converse,
                profile.relation_kind,
                profile.coordinate_system,
            ),
        )
    )
    return ProgressionChartConditionProfile(
        profiles=profiles,
        uniform_count=sum(profile.structural_state == "uniform" for profile in profiles),
        differential_count=sum(profile.structural_state == "differential" for profile in profiles),
        hybrid_count=sum(profile.structural_state == "hybrid" for profile in profiles),
        directing_arc_count=sum(profile.relation_kind == "directing_arc" for profile in profiles),
        time_key_count=sum(profile.relation_kind == "time_key" for profile in profiles),
        house_frame_count=sum(profile.relation_kind == "house_frame_projection" for profile in profiles),
        strongest_techniques=_condition_extreme_names(profiles, strongest=True),
        weakest_techniques=_condition_extreme_names(profiles, strongest=False),
    )


def progression_condition_network_profile(
    charts: list[ProgressedChart] | None = None,
    house_frames: list[ProgressedHouseFrame] | None = None,
) -> ProgressionConditionNetworkProfile:
    """Project progression condition profiles into a deterministic technique-to-basis network."""

    profiles = progression_chart_condition_profile(charts=charts, house_frames=house_frames).profiles
    edges: list[ProgressionConditionNetworkEdge] = []
    node_labels: dict[str, tuple[str, str]] = {}

    for profile in profiles:
        technique_id = f"technique:{profile.technique_name}"
        if technique_id in node_labels:
            raise ValueError("progression condition network requires unique technique names")
        node_labels[technique_id] = ("technique", profile.technique_name)

    for profile in profiles:
        technique_id = f"technique:{profile.technique_name}"
        if profile.relation_kind == "directing_arc" and profile.uses_reference_body:
            target_label = "Sun" if profile.relation_basis == "solar_arc_reference" else "Ascendant"
            target_id = f"reference:{target_label}"
            target_kind = "reference"
        else:
            target_label = profile.relation_basis
            target_id = f"basis:{target_label}"
            target_kind = "basis"
        node_labels[target_id] = (target_kind, target_label)
        edges.append(
            ProgressionConditionNetworkEdge(
                source_id=technique_id,
                target_id=target_id,
                relation_kind=profile.relation_kind,
                relation_basis=profile.relation_basis,
            )
        )

    incoming: dict[str, int] = {node_id: 0 for node_id in node_labels}
    outgoing: dict[str, int] = {node_id: 0 for node_id in node_labels}
    for edge in edges:
        outgoing[edge.source_id] += 1
        incoming[edge.target_id] += 1

    nodes = tuple(
        sorted(
            (
                ProgressionConditionNetworkNode(
                    node_id=node_id,
                    node_kind=node_kind,
                    label=label,
                    incoming_count=incoming[node_id],
                    outgoing_count=outgoing[node_id],
                    total_degree=incoming[node_id] + outgoing[node_id],
                    is_isolated=(incoming[node_id] + outgoing[node_id]) == 0,
                )
                for node_id, (node_kind, label) in node_labels.items()
            ),
            key=lambda node: (node.node_kind, node.label, node.node_id),
        )
    )
    ordered_edges = tuple(sorted(edges, key=lambda edge: (edge.source_id, edge.target_id, edge.relation_kind, edge.relation_basis)))
    return ProgressionConditionNetworkProfile(
        nodes=nodes,
        edges=ordered_edges,
        technique_node_count=sum(node.node_kind == "technique" for node in nodes),
        target_node_count=sum(node.node_kind != "technique" for node in nodes),
        most_connected_nodes=_network_extreme_node_labels(nodes),
        isolated_nodes=tuple(node.label for node in nodes if node.is_isolated),
    )
