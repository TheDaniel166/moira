"""
Fixed Star Oracle — moira/fixed_stars.py

Archetype: Oracle
Purpose: Provides tropical ecliptic positions for ~1,500 named fixed stars
         sourced from the Swiss Ephemeris sefstars.txt catalog.

Boundary declaration
--------------------
Owns:
    - Parsing and caching of sefstars.txt into _StarRecord instances
    - Proper-motion propagation from catalog epoch to query JD
    - ICRF/J2000 → true ecliptic of date conversion (via icrf_to_true_ecliptic)
    - Annual stellar parallax correction (first-order, ecliptic frame)
    - Heliacal rising and setting computation
    - Catalog introspection (list_stars, find_stars, star_magnitude)
Delegates:
    - Obliquity and nutation to moira.obliquity
    - Coordinate frame rotation to moira.coordinates
    - Sun position (for parallax) to moira.planets

Import-time side effects: None. Catalog is loaded lazily on first query.

External dependency assumptions:
    - sefstars.txt must be present at <project_root>/kernels/sefstars.txt before
      any position query is made; FileNotFoundError is raised otherwise.
    - No Qt, no database, no OS threads.

Public surface / exports:
    _StarRecord       — internal catalog entry (frozen dataclass)
    StarPosition      — ecliptic position result (dataclass)
    load_catalog()    — explicit catalog load / reload
    fixed_star_at()   — position of one named star at a JD
    all_stars_at()    — positions of all catalog stars at a JD
    list_stars()      — sorted list of traditional names
    find_stars()      — name-fragment search with optional magnitude filter
    star_magnitude()  — V magnitude lookup by name
    heliacal_rising() — JD of heliacal rising
    heliacal_setting()— JD of heliacal setting (last evening visibility)

Catalog format (per Swiss Ephemeris documentation):
    traditional_name, nomenclature_name, equinox,
    ra_h, ra_m, ra_s, dec_d, dec_m, dec_s,
    pm_ra  (0.001 arcsec/yr * cos dec),
    pm_dec (0.001 arcsec/yr),
    radial_velocity (km/s),
    parallax (0.001 arcsec),
    magnitude,
    dm_zone, dm_number

Equinox values: 'ICRS' or '2000' → J2000.0 (JD 2451545.0)
                '1950'           → B1950.0 (JD 2433282.4235)

Usage
-----
    from moira.fixed_stars import fixed_star_at, list_stars

    pos = fixed_star_at("Algol", jd_tt)
    print(pos.longitude, pos.latitude, pos.magnitude)

    for name in list_stars():
        print(name)

Place sefstars.txt in the kernels/ directory alongside de441.bsp.
Download from: https://raw.githubusercontent.com/astrorigin/swisseph/master/sefstars.txt
"""

import math
from dataclasses import dataclass, field
from pathlib import Path
from collections.abc import Iterator

__all__ = [
    "StarPositionTruth",
    "StarPositionClassification",
    "StarRelation",
    "StarConditionState",
    "StarConditionProfile",
    "StarChartConditionProfile",
    "StarConditionNetworkNode",
    "StarConditionNetworkEdge",
    "StarConditionNetworkProfile",
    "StarPosition",
    "HeliacalEventTruth",
    "HeliacalEventClassification",
    "HeliacalEvent",
    "FixedStarLookupPolicy",
    "HeliacalSearchPolicy",
    "FixedStarComputationPolicy",
    "DEFAULT_FIXED_STAR_POLICY",
    "load_catalog",
    "fixed_star_at",
    "all_stars_at",
    "list_stars",
    "find_stars",
    "star_magnitude",
    "heliacal_rising",
    "heliacal_setting",
    "heliacal_rising_event",
    "heliacal_setting_event",
    "star_chart_condition_profile",
    "star_condition_network_profile",
]

from .constants import DEG2RAD, RAD2DEG
from .coordinates import equatorial_to_ecliptic, icrf_to_true_ecliptic
from .obliquity import mean_obliquity

# ---------------------------------------------------------------------------
# Reference epochs
# ---------------------------------------------------------------------------

_J2000   = 2451545.0          # JD of J2000.0
_J1991_25 = 2448349.0625      # JD of J1991.25 — Hipparcos catalog mean epoch
_B1950   = 2433282.4235       # JD of B1950.0

# Arcseconds → degrees
_AS2DEG = 1.0 / 3600.0


# ---------------------------------------------------------------------------
# Explicit doctrine / policy
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class FixedStarLookupPolicy:
    """Policy surface for fixed-star name resolution doctrine."""

    allow_prefix_lookup: bool = True


@dataclass(frozen=True, slots=True)
class HeliacalSearchPolicy:
    """Policy surface for heliacal visibility doctrine already embodied here."""

    elongation_threshold: float = 12.0
    visibility_tolerance: float = 1.0
    setting_visibility_factor: float = 0.5


@dataclass(frozen=True, slots=True)
class FixedStarComputationPolicy:
    """Lean policy vessel for fixed-star lookup and heliacal doctrine."""

    lookup: FixedStarLookupPolicy = field(default_factory=FixedStarLookupPolicy)
    heliacal: HeliacalSearchPolicy = field(default_factory=HeliacalSearchPolicy)


DEFAULT_FIXED_STAR_POLICY = FixedStarComputationPolicy()


def _resolve_fixed_star_policy(policy: FixedStarComputationPolicy | None) -> FixedStarComputationPolicy:
    return DEFAULT_FIXED_STAR_POLICY if policy is None else policy


def _require_finite(value: float, name: str) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


def _validate_lat_lon(lat: float, lon: float) -> None:
    _require_finite(lat, "lat")
    _require_finite(lon, "lon")
    if not -90.0 <= lat <= 90.0:
        raise ValueError("lat must be between -90 and 90 degrees")
    if not -180.0 <= lon <= 180.0:
        raise ValueError("lon must be between -180 and 180 degrees")


def _validate_fixed_star_policy(policy: FixedStarComputationPolicy) -> None:
    if not isinstance(policy, FixedStarComputationPolicy):
        raise ValueError("fixed-star policy must be a FixedStarComputationPolicy")
    if not isinstance(policy.lookup, FixedStarLookupPolicy):
        raise ValueError("fixed-star policy lookup must be a FixedStarLookupPolicy")
    if not isinstance(policy.heliacal, HeliacalSearchPolicy):
        raise ValueError("fixed-star policy heliacal must be a HeliacalSearchPolicy")
    if not isinstance(policy.lookup.allow_prefix_lookup, bool):
        raise ValueError("fixed-star lookup policy allow_prefix_lookup must be boolean")
    if policy.heliacal.elongation_threshold <= 0:
        raise ValueError("heliacal policy elongation_threshold must be positive")
    if policy.heliacal.visibility_tolerance < 0:
        raise ValueError("heliacal policy visibility_tolerance must be non-negative")
    if policy.heliacal.setting_visibility_factor <= 0:
        raise ValueError("heliacal policy setting_visibility_factor must be positive")
    _require_finite(policy.heliacal.elongation_threshold, "heliacal policy elongation_threshold")
    _require_finite(policy.heliacal.visibility_tolerance, "heliacal policy visibility_tolerance")
    _require_finite(policy.heliacal.setting_visibility_factor, "heliacal policy setting_visibility_factor")


# ---------------------------------------------------------------------------
# Internal catalog entry
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class _StarRecord:
    """
    RITE: The Sealed Scroll — an immutable catalog entry for one fixed star.

    THEOREM: Holds the raw astrometric parameters for a single sefstars.txt
    entry as parsed from the catalog file.

    RITE OF PURPOSE:
        _StarRecord is the internal vessel that carries the catalog truth for
        one star from the moment of parsing until the process ends.  It is
        frozen and slotted so that the catalog singleton can hold thousands of
        these without memory overhead.  No computation lives here; it is pure
        data.  Without it the Oracle would have no stable substrate to query.

    LAW OF OPERATION:
        Responsibilities:
            - Store traditional name, nomenclature, reference frame, epoch JD,
              RA/Dec at epoch, proper-motion components, parallax, and magnitude.
        Non-responsibilities:
            - Does not compute positions.
            - Does not perform coordinate transformations.
            - Does not validate field ranges.
        Dependencies:
            - None (pure data container).
        Structural invariants:
            - All fields are set at construction; the instance is immutable.
        Mutation authority: None — frozen dataclass.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
        "scope": "moira.fixed_stars._StarRecord",
        "id": "moira.fixed_stars._StarRecord",
        "risk": "low",
        "api": {
            "inputs": ["traditional_name", "nomenclature", "frame", "equinox_jd",
                       "ra_deg", "dec_deg", "pm_ra", "pm_dec", "parallax_mas", "magnitude"],
            "outputs": ["frozen dataclass instance"],
            "raises": []
        },
        "state": "stateless",
        "effects": {
            "reads": [],
            "writes": [],
            "signals_emitted": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": "None — construction only fails if caller passes wrong types.",
        "succession": {
            "stance": "terminal",
            "extension_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]
    """

    traditional_name: str
    nomenclature:     str
    frame:            str     # source frame/equinox tag from sefstars.txt
    equinox_jd:       float   # reference epoch JD (J2000/J1991.25/B1950)
    ra_deg:           float   # RA at reference epoch, degrees
    dec_deg:          float   # Dec at reference epoch, degrees
    pm_ra:            float   # proper motion, 0.001 arcsec/yr * cos(dec)
    pm_dec:           float   # proper motion, 0.001 arcsec/yr
    parallax_mas:     float   # annual parallax, 0.001 arcsec (milliarcseconds)
    magnitude:        float   # V magnitude


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class StarPositionTruth:
    """Preserve the lookup and frame path used to compute one star position."""

    queried_name: str
    lookup_mode: str
    matched_name: str
    matched_nomenclature: str
    source_frame: str
    frame_path: str
    catalog_epoch_jd: float
    parallax_applied: bool

    def __post_init__(self) -> None:
        if not self.queried_name.strip():
            raise ValueError("star position truth queried_name must be non-empty")
        if not self.matched_name.strip():
            raise ValueError("star position truth matched_name must be non-empty")
        if not self.matched_nomenclature.strip():
            raise ValueError("star position truth matched_nomenclature must be non-empty")
        if not self.source_frame.strip():
            raise ValueError("star position truth source_frame must be non-empty")
        if self.lookup_mode not in {"traditional_name", "nomenclature", "prefix_unique", "prefix_shortest"}:
            raise ValueError("star position truth lookup_mode must be supported")
        if self.frame_path not in {"icrf_to_true_ecliptic", "equatorial_to_ecliptic_mean_obliquity"}:
            raise ValueError("star position truth frame_path must be supported")
        _require_finite(self.catalog_epoch_jd, "star position truth catalog_epoch_jd")


@dataclass(slots=True)
class StarPositionClassification:
    """Typed descriptive classification derived from star position truth."""

    lookup_kind: str
    frame_kind: str
    parallax_state: str

    def __post_init__(self) -> None:
        if self.lookup_kind not in {"traditional_name", "nomenclature", "prefix_unique", "prefix_shortest"}:
            raise ValueError("star position classification lookup_kind must be supported")
        if self.frame_kind not in {"icrf", "legacy_equatorial"}:
            raise ValueError("star position classification frame_kind must be supported")
        if self.parallax_state not in {"applied", "not_applied"}:
            raise ValueError("star position classification parallax_state must be applied or not_applied")


def _classify_star_position_truth(truth: StarPositionTruth) -> StarPositionClassification:
    return StarPositionClassification(
        lookup_kind=truth.lookup_mode,
        frame_kind="icrf" if truth.frame_path == "icrf_to_true_ecliptic" else "legacy_equatorial",
        parallax_state="applied" if truth.parallax_applied else "not_applied",
    )


@dataclass(slots=True)
class StarRelation:
    """Explicit relation truth derived from the current star backend."""

    kind: str
    basis: str
    star_name: str
    reference: str | None = None
    event_kind: str | None = None

    def __post_init__(self) -> None:
        if not self.star_name.strip():
            raise ValueError("star relation star_name must be non-empty")
        if self.kind not in {"catalog_lookup", "heliacal_event"}:
            raise ValueError("star relation kind must be supported")
        if self.kind == "catalog_lookup" and self.basis not in {"named_star_lookup"}:
            raise ValueError("catalog lookup relation basis must be named_star_lookup")
        if self.kind == "catalog_lookup" and self.event_kind is not None:
            raise ValueError("catalog lookup relation must not carry event_kind")
        if self.kind == "catalog_lookup" and self.reference is None:
            raise ValueError("catalog lookup relation must preserve nomenclature reference")
        if self.kind == "catalog_lookup" and self.reference is not None and not self.reference.strip():
            raise ValueError("catalog lookup relation reference must be non-empty")
        if self.kind == "heliacal_event" and self.basis not in {"heliacal_visibility"}:
            raise ValueError("heliacal event relation basis must be heliacal_visibility")
        if self.kind == "heliacal_event" and self.event_kind not in {"rising", "setting"}:
            raise ValueError("heliacal event relation must preserve supported event_kind")
        if self.kind == "heliacal_event" and self.reference is not None:
            raise ValueError("heliacal event relation must not carry lookup reference")

    @property
    def is_catalog_lookup(self) -> bool:
        return self.kind == "catalog_lookup"

    @property
    def is_heliacal_event(self) -> bool:
        return self.kind == "heliacal_event"


@dataclass(slots=True)
class StarConditionState:
    """Structural condition state for one star result vessel."""

    name: str

    def __post_init__(self) -> None:
        if self.name not in {"catalog_position", "heliacal_event", "unified_merge"}:
            raise ValueError("star condition state must be supported")


@dataclass(slots=True)
class StarConditionProfile:
    """Integrated per-result star condition profile derived from existing truth."""

    result_kind: str
    condition_state: StarConditionState
    relation_kind: str
    relation_basis: str
    lookup_kind: str | None = None
    source_kind: str | None = None
    event_kind: str | None = None

    def __post_init__(self) -> None:
        if self.result_kind not in {"fixed_star_position", "heliacal_event", "unified_star"}:
            raise ValueError("star condition profile result_kind must be supported")
        if self.condition_state.name == "catalog_position" and self.relation_kind != "catalog_lookup":
            raise ValueError("catalog-position profile must use catalog_lookup relation")
        if self.condition_state.name == "heliacal_event" and self.relation_kind != "heliacal_event":
            raise ValueError("heliacal-event profile must use heliacal_event relation")
        if self.condition_state.name == "unified_merge" and self.relation_kind != "catalog_merge":
            raise ValueError("unified-merge profile must use catalog_merge relation")
        if self.result_kind == "fixed_star_position" and not self.lookup_kind:
            raise ValueError("fixed-star-position profile must preserve lookup_kind")
        if self.result_kind == "heliacal_event" and self.event_kind not in {"rising", "setting"}:
            raise ValueError("heliacal-event profile must preserve supported event_kind")
        if self.result_kind == "unified_star" and self.source_kind not in {"hipparcos", "gaia", "both"}:
            raise ValueError("unified-star profile must preserve supported source_kind")


def _build_star_position_condition_profile(position: "StarPosition") -> StarConditionProfile:
    return StarConditionProfile(
        result_kind="fixed_star_position",
        condition_state=StarConditionState("catalog_position"),
        relation_kind="catalog_lookup",
        relation_basis="named_star_lookup",
        lookup_kind=position.lookup_kind,
    )


def _build_heliacal_event_condition_profile(event: "HeliacalEvent") -> StarConditionProfile:
    return StarConditionProfile(
        result_kind="heliacal_event",
        condition_state=StarConditionState("heliacal_event"),
        relation_kind="heliacal_event",
        relation_basis="heliacal_visibility",
        event_kind=event.event_kind,
    )


def _star_condition_strength(profile: StarConditionProfile) -> int:
    ranks = {
        "catalog_position": 0,
        "heliacal_event": 1,
        "unified_merge": 2,
    }
    return ranks[profile.condition_state.name]


def _star_condition_sort_key(profile: StarConditionProfile) -> tuple[object, ...]:
    return (
        profile.condition_state.name,
        profile.result_kind,
        profile.relation_kind,
        profile.relation_basis,
        profile.lookup_kind or "",
        profile.source_kind or "",
        profile.event_kind or "",
    )


@dataclass(slots=True)
class StarChartConditionProfile:
    """Chart-wide star condition aggregate built from per-result profiles."""

    profiles: tuple[StarConditionProfile, ...]
    catalog_position_count: int
    heliacal_event_count: int
    unified_merge_count: int
    strongest_profiles: tuple[StarConditionProfile, ...]
    weakest_profiles: tuple[StarConditionProfile, ...]

    def __post_init__(self) -> None:
        if len(self.profiles) != self.catalog_position_count + self.heliacal_event_count + self.unified_merge_count:
            raise ValueError("star chart profile counts must sum to profile total")
        expected_profiles = tuple(sorted(self.profiles, key=_star_condition_sort_key))
        if self.profiles != expected_profiles:
            raise ValueError("star chart condition profiles must be deterministically ordered")
        if self.catalog_position_count != sum(1 for profile in self.profiles if profile.condition_state.name == "catalog_position"):
            raise ValueError("star chart catalog_position_count must match profiles")
        if self.heliacal_event_count != sum(1 for profile in self.profiles if profile.condition_state.name == "heliacal_event"):
            raise ValueError("star chart heliacal_event_count must match profiles")
        if self.unified_merge_count != sum(1 for profile in self.profiles if profile.condition_state.name == "unified_merge"):
            raise ValueError("star chart unified_merge_count must match profiles")
        if self.profiles:
            strongest_rank = max(_star_condition_strength(profile) for profile in self.profiles)
            weakest_rank = min(_star_condition_strength(profile) for profile in self.profiles)
            expected_strongest = tuple(profile for profile in self.profiles if _star_condition_strength(profile) == strongest_rank)
            expected_weakest = tuple(profile for profile in self.profiles if _star_condition_strength(profile) == weakest_rank)
        else:
            expected_strongest = ()
            expected_weakest = ()
        if self.strongest_profiles != expected_strongest:
            raise ValueError("star chart strongest_profiles must match derived ranking")
        if self.weakest_profiles != expected_weakest:
            raise ValueError("star chart weakest_profiles must match derived ranking")

    @property
    def profile_count(self) -> int:
        return len(self.profiles)


@dataclass(slots=True)
class StarConditionNetworkNode:
    """One node in the star relation/condition network."""

    node_id: str
    kind: str
    incoming_count: int
    outgoing_count: int

    def __post_init__(self) -> None:
        if not self.node_id.strip():
            raise ValueError("star network node_id must be non-empty")
        if self.kind not in {"star", "event", "source"}:
            raise ValueError("star network node kind must be supported")
        if self.incoming_count < 0 or self.outgoing_count < 0:
            raise ValueError("star network node counts must be non-negative")
        expected_prefix = f"{self.kind}:"
        if not self.node_id.startswith(expected_prefix):
            raise ValueError("star network node_id must match node kind prefix")

    @property
    def total_degree(self) -> int:
        return self.incoming_count + self.outgoing_count


@dataclass(slots=True)
class StarConditionNetworkEdge:
    """One directed edge in the star relation/condition network."""

    source_id: str
    target_id: str
    relation_kind: str
    relation_basis: str
    condition_state: str

    def __post_init__(self) -> None:
        if not self.source_id.strip() or not self.target_id.strip():
            raise ValueError("star network edge endpoints must be non-empty")
        if self.relation_kind not in {"catalog_lookup", "heliacal_event", "catalog_merge"}:
            raise ValueError("star network edge relation_kind must be supported")
        if self.condition_state not in {"catalog_position", "heliacal_event", "unified_merge"}:
            raise ValueError("star network edge condition_state must be supported")
        if self.source_id == self.target_id:
            raise ValueError("star network edges must not be self-loops")


@dataclass(slots=True)
class StarConditionNetworkProfile:
    """Network projection built from existing star relations and condition profiles."""

    nodes: tuple[StarConditionNetworkNode, ...]
    edges: tuple[StarConditionNetworkEdge, ...]
    isolated_nodes: tuple[StarConditionNetworkNode, ...]
    most_connected_nodes: tuple[StarConditionNetworkNode, ...]

    def __post_init__(self) -> None:
        expected_nodes = tuple(sorted(self.nodes, key=lambda node: (node.kind, node.node_id)))
        expected_edges = tuple(sorted(
            self.edges,
            key=lambda edge: (edge.source_id, edge.target_id, edge.relation_kind, edge.relation_basis, edge.condition_state),
        ))
        if self.nodes != expected_nodes:
            raise ValueError("star network nodes must be deterministically ordered")
        if self.edges != expected_edges:
            raise ValueError("star network edges must be deterministically ordered")
        if len(set(
            (edge.source_id, edge.target_id, edge.relation_kind, edge.relation_basis, edge.condition_state)
            for edge in self.edges
        )) != len(self.edges):
            raise ValueError("star network edges must be unique")
        node_ids = {node.node_id for node in self.nodes}
        if len(node_ids) != len(self.nodes):
            raise ValueError("star network node ids must be unique")
        incoming = {node.node_id: 0 for node in self.nodes}
        outgoing = {node.node_id: 0 for node in self.nodes}
        for edge in self.edges:
            if edge.source_id not in node_ids or edge.target_id not in node_ids:
                raise ValueError("star network edges must reference known nodes")
            if edge.relation_kind == "catalog_lookup" and not edge.source_id.startswith("source:"):
                raise ValueError("catalog lookup edges must originate from source nodes")
            if edge.relation_kind == "catalog_lookup" and not edge.target_id.startswith("star:"):
                raise ValueError("catalog lookup edges must target star nodes")
            if edge.relation_kind == "catalog_lookup" and edge.condition_state != "catalog_position":
                raise ValueError("catalog lookup edges must use catalog_position condition_state")
            if edge.relation_kind == "heliacal_event" and not edge.source_id.startswith("event:"):
                raise ValueError("heliacal event edges must originate from event nodes")
            if edge.relation_kind == "heliacal_event" and not edge.target_id.startswith("star:"):
                raise ValueError("heliacal event edges must target star nodes")
            if edge.relation_kind == "heliacal_event" and edge.condition_state != "heliacal_event":
                raise ValueError("heliacal event edges must use heliacal_event condition_state")
            if edge.relation_kind == "catalog_merge" and not edge.source_id.startswith("source:"):
                raise ValueError("catalog merge edges must originate from source nodes")
            if edge.relation_kind == "catalog_merge" and not edge.target_id.startswith("star:"):
                raise ValueError("catalog merge edges must target star nodes")
            if edge.relation_kind == "catalog_merge" and edge.condition_state != "unified_merge":
                raise ValueError("catalog merge edges must use unified_merge condition_state")
            outgoing[edge.source_id] += 1
            incoming[edge.target_id] += 1
        for node in self.nodes:
            if node.incoming_count != incoming[node.node_id]:
                raise ValueError("star network incoming_count must match edges")
            if node.outgoing_count != outgoing[node.node_id]:
                raise ValueError("star network outgoing_count must match edges")
        expected_isolated = tuple(node for node in self.nodes if node.total_degree == 0)
        if self.isolated_nodes != expected_isolated:
            raise ValueError("star network isolated_nodes must match zero-degree nodes")
        if self.nodes:
            max_degree = max(node.total_degree for node in self.nodes)
            expected_most_connected = tuple(node for node in self.nodes if node.total_degree == max_degree)
        else:
            expected_most_connected = ()
        if self.most_connected_nodes != expected_most_connected:
            raise ValueError("star network most_connected_nodes must match node degrees")


def _build_star_position_relation(position: "StarPosition") -> StarRelation:
    return StarRelation(
        kind="catalog_lookup",
        basis="named_star_lookup",
        star_name=position.name,
        reference=position.nomenclature,
    )


@dataclass(slots=True)
class StarPosition:
    """
    RITE: The Star's Witness — the ecliptic position of a fixed star at a moment in time.

    THEOREM: Holds the computed tropical ecliptic longitude, latitude, and
    magnitude of a named fixed star at a specific Julian Day.

    RITE OF PURPOSE:
        StarPosition is the public result vessel returned by fixed_star_at() and
        all_stars_at().  It carries the star's apparent place in the tropical
        ecliptic frame of date, ready for astrological interpretation.  Without
        it callers would receive raw floats with no semantic context.  It serves
        the Fixed Star Oracle pillar as its sole output type.

    LAW OF OPERATION:
        Responsibilities:
            - Store name, nomenclature, tropical longitude, ecliptic latitude,
              and V magnitude.
            - Derive sign name and sign-relative degree via properties.
        Non-responsibilities:
            - Does not compute positions (that is fixed_star_at's role).
            - Does not perform topocentric corrections.
            - Does not carry equatorial coordinates.
        Dependencies:
            - moira.constants.SIGNS for sign name lookup.
        Structural invariants:
            - longitude is always in [0, 360).
        Mutation authority: Fields are mutable post-construction (not frozen).

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
        "scope": "moira.fixed_stars.StarPosition",
        "id": "moira.fixed_stars.StarPosition",
        "risk": "high",
        "api": {
            "inputs": ["name", "nomenclature", "longitude", "latitude", "magnitude"],
            "outputs": ["StarPosition instance", "sign (str)", "sign_degree (float)"],
            "raises": []
        },
        "state": "stateless",
        "effects": {
            "reads": [],
            "writes": [],
            "signals_emitted": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": "None — construction only fails if caller passes wrong types.",
        "succession": {
            "stance": "terminal",
            "extension_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]
    """

    name:       str
    nomenclature: str
    longitude:  float   # tropical ecliptic longitude, degrees [0, 360)
    latitude:   float   # ecliptic latitude, degrees
    magnitude:  float   # V magnitude
    computation_truth: StarPositionTruth | None = None
    classification: StarPositionClassification | None = None
    relation: StarRelation | None = None
    condition_profile: StarConditionProfile | None = None

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("star position name must be non-empty")
        if not self.nomenclature.strip():
            raise ValueError("star position nomenclature must be non-empty")
        _require_finite(self.longitude, "star position longitude")
        _require_finite(self.latitude, "star position latitude")
        _require_finite(self.magnitude, "star position magnitude")
        self.longitude = self.longitude % 360.0
        if self.computation_truth is not None:
            if self.computation_truth.matched_name != self.name:
                raise ValueError("star position truth matched_name must match position name")
            if self.computation_truth.matched_nomenclature != self.nomenclature:
                raise ValueError("star position truth matched_nomenclature must match position nomenclature")
        if self.classification is not None:
            if self.computation_truth is None:
                raise ValueError("star position classification requires computation_truth")
            expected = _classify_star_position_truth(self.computation_truth)
            if self.classification != expected:
                raise ValueError("star position classification must match computation_truth")
        if self.relation is not None:
            expected = _build_star_position_relation(self)
            if self.relation != expected:
                raise ValueError("star position relation must match star vessel truth")
        if self.condition_profile is not None:
            expected = _build_star_position_condition_profile(self)
            if self.condition_profile != expected:
                raise ValueError("star position condition profile must match vessel truth")

    @property
    def sign(self) -> str:
        from .constants import SIGNS
        return SIGNS[int(self.longitude // 30)]

    @property
    def sign_degree(self) -> float:
        return self.longitude % 30.0

    @property
    def lookup_kind(self) -> str | None:
        return None if self.classification is None else self.classification.lookup_kind

    @property
    def frame_kind(self) -> str | None:
        return None if self.classification is None else self.classification.frame_kind

    @property
    def parallax_state(self) -> str | None:
        return None if self.classification is None else self.classification.parallax_state

    @property
    def source_frame(self) -> str | None:
        return None if self.computation_truth is None else self.computation_truth.source_frame

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

    def __repr__(self) -> str:
        return (f"StarPosition({self.name!r}, "
                f"{self.longitude:.4f}° [{self.sign} {self.sign_degree:.2f}°], "
                f"lat={self.latitude:.4f}°, mag={self.magnitude})")


# ---------------------------------------------------------------------------
# Heliacal event result vessels
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class HeliacalEventTruth:
    """Preserve the doctrinal search path for one heliacal event computation."""

    event_kind: str
    star_name: str
    jd_start: float
    search_days: int
    arcus_visionis: float
    elongation_threshold: float
    conjunction_offset: int | None
    qualifying_day_offset: int | None
    qualifying_elongation: float | None
    qualifying_sun_altitude: float | None
    event_jd_ut: float | None

    def __post_init__(self) -> None:
        if self.event_kind not in {"rising", "setting"}:
            raise ValueError("heliacal event truth event_kind must be rising or setting")
        if not self.star_name.strip():
            raise ValueError("heliacal event truth star_name must be non-empty")
        if self.search_days <= 0:
            raise ValueError("heliacal event truth search_days must be positive")
        if self.elongation_threshold <= 0:
            raise ValueError("heliacal event truth elongation_threshold must be positive")
        _require_finite(self.jd_start, "heliacal event truth jd_start")
        _require_finite(self.arcus_visionis, "heliacal event truth arcus_visionis")
        _require_finite(self.elongation_threshold, "heliacal event truth elongation_threshold")
        if self.qualifying_day_offset is not None and not 0 <= self.qualifying_day_offset < self.search_days:
            raise ValueError("heliacal event truth qualifying_day_offset must fall within search_days")
        if self.conjunction_offset is not None and not 0 <= self.conjunction_offset < self.search_days:
            raise ValueError("heliacal event truth conjunction_offset must fall within search_days")
        if self.event_jd_ut is None:
            if self.qualifying_day_offset is not None:
                raise ValueError("heliacal event truth without event_jd_ut must not preserve qualifying_day_offset")
        else:
            _require_finite(self.event_jd_ut, "heliacal event truth event_jd_ut")


@dataclass(slots=True)
class HeliacalEventClassification:
    """Typed descriptive classification derived from heliacal event truth."""

    event_kind: str
    visibility_basis: str
    threshold_mode: str

    def __post_init__(self) -> None:
        if self.event_kind not in {"rising", "setting"}:
            raise ValueError("heliacal event classification event_kind must be supported")
        if self.visibility_basis != "heliacal_visibility":
            raise ValueError("heliacal event classification visibility_basis must be heliacal_visibility")
        if self.threshold_mode not in {"first_visible", "last_visible"}:
            raise ValueError("heliacal event classification threshold_mode must be supported")


def _classify_heliacal_event_truth(truth: HeliacalEventTruth) -> HeliacalEventClassification:
    return HeliacalEventClassification(
        event_kind=truth.event_kind,
        visibility_basis="heliacal_visibility",
        threshold_mode="first_visible" if truth.event_kind == "rising" else "last_visible",
    )


def _build_heliacal_event_relation(event: "HeliacalEvent") -> StarRelation:
    return StarRelation(
        kind="heliacal_event",
        basis="heliacal_visibility",
        star_name=event.truth.star_name,
        event_kind=event.truth.event_kind,
    )


@dataclass(slots=True)
class HeliacalEvent:
    """Explicit heliacal event vessel preserving returned JD plus search truth."""

    jd_ut: float | None
    truth: HeliacalEventTruth
    classification: HeliacalEventClassification | None = None
    relation: StarRelation | None = None
    condition_profile: StarConditionProfile | None = None

    def __post_init__(self) -> None:
        if self.jd_ut is not None:
            _require_finite(self.jd_ut, "heliacal event jd_ut")
        if self.jd_ut != self.truth.event_jd_ut:
            raise ValueError("heliacal event jd_ut must match truth event_jd_ut")
        if self.classification is not None:
            expected = _classify_heliacal_event_truth(self.truth)
            if self.classification != expected:
                raise ValueError("heliacal event classification must match truth")
        if self.relation is not None:
            expected = _build_heliacal_event_relation(self)
            if self.relation != expected:
                raise ValueError("heliacal event relation must match event truth")
        if self.condition_profile is not None:
            expected = _build_heliacal_event_condition_profile(self)
            if self.condition_profile != expected:
                raise ValueError("heliacal event condition profile must match event truth")

    @property
    def event_kind(self) -> str:
        return self.truth.event_kind if self.classification is None else self.classification.event_kind

    @property
    def visibility_basis(self) -> str | None:
        return None if self.classification is None else self.classification.visibility_basis

    @property
    def threshold_mode(self) -> str | None:
        return None if self.classification is None else self.classification.threshold_mode

    @property
    def found_event(self) -> bool:
        return self.jd_ut is not None

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


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def _parse_dec(d: str, m: str, s: str) -> float:
    """Parse degrees/minutes/seconds with sign embedded in the degree field."""
    deg = float(d)
    arc = float(m) / 60.0 + float(s) / 3600.0
    return deg - arc if deg < 0 or d.strip().startswith("-") else deg + arc


def _parse_ra(h: str, m: str, s: str) -> float:
    """Parse right ascension hours/minutes/seconds → degrees."""
    return (float(h) + float(m) / 60.0 + float(s) / 3600.0) * 15.0


def _parse_catalog(path: Path) -> dict[str, _StarRecord]:
    """
    Return an ordered dict: lower-cased traditional_name → _StarRecord.
    Duplicate traditional names are kept as the first occurrence only.
    """
    records: dict[str, _StarRecord] = {}
    alt_index: dict[str, str] = {}   # nomenclature.lower() → traditional_name.lower()

    with path.open(encoding="utf-8", errors="replace") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 14:
                continue

            trad = parts[0]
            nom  = parts[1]
            # Some sefstars.txt entries carry only a Bayer designation (no
            # traditional name).  Use the nomenclature name as the key so the
            # star remains accessible; both the primary dict and the alt_index
            # will point to it via the same key.
            if not trad:
                trad = nom
            if not trad:
                continue  # skip entries with no usable name at all
            equinox_str = parts[2].upper()

            if equinox_str == "ICRS":
                # ICRS-tagged entries in sefstars.txt are Hipparcos-sourced;
                # their positions were measured at the Hipparcos mean epoch J1991.25.
                # Using J1991.25 as the propagation start minimises accumulated
                # proper-motion error compared to starting from J2000.0.
                epoch_jd = _J1991_25
            elif equinox_str == "2000":
                epoch_jd = _J2000
            elif equinox_str == "1950":
                epoch_jd = _B1950
            else:
                continue  # unknown equinox — skip

            try:
                ra_deg  = _parse_ra(parts[3], parts[4], parts[5])
                dec_deg = _parse_dec(parts[6], parts[7], parts[8])
                pm_ra   = float(parts[9])
                pm_dec  = float(parts[10])
                # parts[11] = radial velocity (not used)
                parallax_mas = float(parts[12])   # 0.001 arcsec = 1 mas
                magnitude    = float(parts[13])
            except (ValueError, IndexError):
                continue

            key = trad.lower()
            if key not in records:
                records[key] = _StarRecord(
                    traditional_name=trad,
                    nomenclature=nom,
                    frame=equinox_str,
                    equinox_jd=epoch_jd,
                    ra_deg=ra_deg,
                    dec_deg=dec_deg,
                    pm_ra=pm_ra,
                    pm_dec=pm_dec,
                    parallax_mas=parallax_mas,
                    magnitude=magnitude,
                )
                nom_key = nom.lower()
                if nom_key not in alt_index:
                    alt_index[nom_key] = key

    # Attach alt_index as a module-level side-effect via a small wrapper
    _parse_catalog._alt_index = alt_index  # type: ignore[attr-defined]
    return records


# ---------------------------------------------------------------------------
# Catalog singleton
# ---------------------------------------------------------------------------

_catalog:   dict[str, _StarRecord] | None = None
_alt_index: dict[str, str]                = {}   # nomenclature.lower() → trad.lower()
_catalog_path: Path | None                = None


def _default_catalog_path() -> Path:
    """Return the expected location of sefstars.txt (kernels/ alongside de441.bsp)."""
    return Path(__file__).resolve().parents[1] / "kernels" / "sefstars.txt"


def load_catalog(path: Path | str | None = None) -> None:
    """
    Load (or reload) the fixed star catalog from *path*.

    If *path* is None the default location is used:
        <project_root>/kernels/sefstars.txt

    Raises FileNotFoundError if the file does not exist.
    """
    global _catalog, _alt_index, _catalog_path

    p = Path(path) if path else _default_catalog_path()
    if not p.exists():
        raise FileNotFoundError(
            f"sefstars.txt not found at {p}\n"
            "Download from: https://raw.githubusercontent.com/astrorigin/swisseph/master/sefstars.txt\n"
            "and place it in the kernels/ directory alongside de441.bsp."
        )

    _catalog = _parse_catalog(p)
    _alt_index = getattr(_parse_catalog, "_alt_index", {})
    _catalog_path = p


def _ensure_loaded() -> None:
    if _catalog is None:
        load_catalog()


# ---------------------------------------------------------------------------
# Position calculation
# ---------------------------------------------------------------------------

def _apply_proper_motion(ra: float, dec: float, pm_ra: float, pm_dec: float,
                          epoch_jd: float, target_jd: float) -> tuple[float, float]:
    """
    Propagate RA/Dec from epoch_jd to target_jd using linear proper motion.

    pm_ra  — 0.001 arcsec/yr * cos(dec)  (mu_alpha_star)
    pm_dec — 0.001 arcsec/yr
    """
    dt = (target_jd - epoch_jd) / 365.25          # years
    dec_r = dec * DEG2RAD
    cos_dec = math.cos(dec_r)

    # delta RA in arcsec → degrees; divide by cos(dec) to get angular RA change
    if abs(cos_dec) > 1e-10:
        new_ra  = ra  + (pm_ra  * 0.001 * _AS2DEG / cos_dec) * dt
    else:
        new_ra  = ra

    new_dec = dec + (pm_dec * 0.001 * _AS2DEG) * dt
    # clamp dec to ±90
    new_dec = max(-90.0, min(90.0, new_dec))
    return new_ra % 360.0, new_dec


def fixed_star_at(
    name: str,
    jd_tt: float,
    policy: FixedStarComputationPolicy | None = None,
) -> StarPosition:
    """
    Return the tropical ecliptic position of a fixed star at *jd_tt*.

    *name* is matched case-insensitively against both the traditional name
    (e.g. "Algol") and the nomenclature name (e.g. "bePer").

    Parameters
    ----------
    name   : star name (traditional or Bayer/Flamsteed nomenclature)
    jd_tt  : Julian Day in Terrestrial Time

    Returns
    -------
    StarPosition with tropical longitude, ecliptic latitude, and magnitude.

    Raises
    ------
    FileNotFoundError if sefstars.txt has not been placed in the project root.
    KeyError          if the star is not found in the catalog.
    """
    if not isinstance(name, str) or not name.strip():
        raise ValueError("fixed star name must be a non-empty string")
    _require_finite(jd_tt, "jd_tt")
    policy = _resolve_fixed_star_policy(policy)
    _validate_fixed_star_policy(policy)

    _ensure_loaded()
    assert _catalog is not None

    key = name.lower().strip()
    lookup_mode = "traditional_name"
    record = _catalog.get(key)
    if record is None:
        # Try nomenclature lookup
        trad_key = _alt_index.get(key)
        if trad_key:
            record = _catalog[trad_key]
            lookup_mode = "nomenclature"
    if record is None:
        # Fuzzy: match by prefix
        if policy.lookup.allow_prefix_lookup:
            matches = [v for k, v in _catalog.items() if k.startswith(key)]
            if len(matches) == 1:
                record = matches[0]
                lookup_mode = "prefix_unique"
            elif len(matches) > 1:
                # Return closest (shortest name)
                record = min(matches, key=lambda r: len(r.traditional_name))
                lookup_mode = "prefix_shortest"
        if record is None:
            raise KeyError(
                f"Fixed star {name!r} not found in catalog. "
                f"Use list_stars() to see available names."
            )

    # 1. Apply proper motion from catalog epoch to jd_tt
    #    ICRS entries use J1991.25 (Hipparcos mean epoch) as the start;
    #    J2000/B1950 entries use their stated epoch.
    ra, dec = _apply_proper_motion(
        record.ra_deg, record.dec_deg,
        record.pm_ra, record.pm_dec,
        record.equinox_jd, jd_tt,
    )

    # 2. Convert to tropical true ecliptic of date.
    #
    #    For ICRS/J2000 stars, use the same equatorial matrix path as the
    #    planetary engine: build the inertial unit vector, apply the
    #    bias+precession and nutation rotations, then rotate into the true
    #    ecliptic of date. This avoids the scalar precession shortcut, whose
    #    latitude errors grow noticeably away from J2000.
    #
    #    The single B1950 catalog entry keeps the legacy scalar path because
    #    Moira does not yet carry a dedicated FK4→J2000 frame conversion here.
    if record.frame in {"ICRS", "2000"}:
        frame_path = "icrf_to_true_ecliptic"
        ra_r = ra * DEG2RAD
        dec_r = dec * DEG2RAD
        xyz = (
            math.cos(dec_r) * math.cos(ra_r),
            math.cos(dec_r) * math.sin(ra_r),
            math.sin(dec_r),
        )
        lon, lat, _ = icrf_to_true_ecliptic(jd_tt, xyz)
    else:
        frame_path = "equatorial_to_ecliptic_mean_obliquity"
        obliquity_mean = mean_obliquity(jd_tt)
        lon, lat = equatorial_to_ecliptic(ra, dec, obliquity_mean)

    # 3. Annual stellar parallax
    #    Shifts the apparent position by up to p″ depending on Earth's orbital
    #    position.  Effect: ~0.77″ for α Cen, < 0.1″ for most catalog stars.
    #    Formula (ecliptic frame, first-order, Woolard & Clemence §53):
    #       Δλ = +p * sin(λ_sun − λ) / cos β
    #       Δβ = −p * cos(λ_sun − λ) * sin β
    #    where p is the annual parallax in the same angular units.
    parallax_applied = False
    if record.parallax_mas > 0.0:
        from .planets import planet_at as _planet_at
        sun = _planet_at("Sun", jd_tt)
        p_deg = (record.parallax_mas * 0.001) * _AS2DEG  # mas → degrees
        lat_r = lat * DEG2RAD
        dlam  = math.sin((sun.longitude - lon) * DEG2RAD)
        dcos  = math.cos((sun.longitude - lon) * DEG2RAD)
        cos_b = math.cos(lat_r)
        if abs(cos_b) > 1e-10:
            lon = (lon + p_deg * dlam / cos_b) % 360.0
        lat = lat - p_deg * dcos * math.sin(lat_r)
        parallax_applied = True

    return StarPosition(
        name=record.traditional_name,
        nomenclature=record.nomenclature,
        longitude=lon,
        latitude=lat,
        magnitude=record.magnitude,
        computation_truth=StarPositionTruth(
            queried_name=name,
            lookup_mode=lookup_mode,
            matched_name=record.traditional_name,
            matched_nomenclature=record.nomenclature,
            source_frame=record.frame,
            frame_path=frame_path,
            catalog_epoch_jd=record.equinox_jd,
            parallax_applied=parallax_applied,
        ),
        classification=_classify_star_position_truth(
            StarPositionTruth(
                queried_name=name,
                lookup_mode=lookup_mode,
                matched_name=record.traditional_name,
                matched_nomenclature=record.nomenclature,
                source_frame=record.frame,
                frame_path=frame_path,
                catalog_epoch_jd=record.equinox_jd,
                parallax_applied=parallax_applied,
            )
        ),
        relation=StarRelation(
            kind="catalog_lookup",
            basis="named_star_lookup",
            star_name=record.traditional_name,
            reference=record.nomenclature,
        ),
        condition_profile=StarConditionProfile(
            result_kind="fixed_star_position",
            condition_state=StarConditionState("catalog_position"),
            relation_kind="catalog_lookup",
            relation_basis="named_star_lookup",
            lookup_kind=lookup_mode,
        ),
    )


def all_stars_at(jd_tt: float) -> dict[str, StarPosition]:
    """
    Return positions for every star in the catalog at *jd_tt*.

    Returns a dict keyed by traditional name (original casing).
    """
    _ensure_loaded()
    assert _catalog is not None
    return {
        rec.traditional_name: fixed_star_at(rec.traditional_name, jd_tt)
        for rec in _catalog.values()
    }


# ---------------------------------------------------------------------------
# Catalog introspection
# ---------------------------------------------------------------------------

def list_stars() -> list[str]:
    """Return a sorted list of all traditional star names in the catalog."""
    _ensure_loaded()
    assert _catalog is not None
    return sorted(rec.traditional_name for rec in _catalog.values())


def find_stars(
    name_fragment: str,
    *,
    max_magnitude: float | None = None,
) -> list[str]:
    """
    Return traditional names that contain *name_fragment* (case-insensitive).

    Optionally filter by *max_magnitude* (lower = brighter).
    """
    _ensure_loaded()
    assert _catalog is not None
    frag = name_fragment.lower()
    results = []
    for key, rec in _catalog.items():
        if frag in key or frag in rec.nomenclature.lower():
            if max_magnitude is None or rec.magnitude <= max_magnitude:
                results.append(rec.traditional_name)
    return sorted(results)


def star_magnitude(name: str) -> float:
    """Return the V magnitude of a star by name."""
    _ensure_loaded()
    assert _catalog is not None
    key = name.lower().strip()
    rec = _catalog.get(key)
    if rec is None:
        trad_key = _alt_index.get(key)
        if trad_key:
            rec = _catalog[trad_key]
    if rec is None:
        raise KeyError(f"Star {name!r} not found.")
    return rec.magnitude


# ---------------------------------------------------------------------------
# Heliacal Rising and Setting
# ---------------------------------------------------------------------------

def _arcus_visionis(magnitude: float) -> float:
    """
    Minimum solar depression angle for a star to be visible (degrees).

    Based on standard astronomical twilight visibility thresholds.
    Brighter stars need less solar depression.

    Parameters
    ----------
    magnitude : apparent visual magnitude of the star

    Returns
    -------
    Arcus visionis in degrees (solar depression required)
    """
    if magnitude <= 1.0:
        return 10.0
    elif magnitude <= 2.0:
        return 11.0
    elif magnitude <= 3.0:
        return 12.0
    elif magnitude <= 4.0:
        return 13.0
    else:
        return 14.5


def _star_altitude(jd_ut: float, lat: float, lon: float, star_name: str) -> float:
    """
    Compute the altitude of a fixed star above the horizon for an observer.

    Parameters
    ----------
    jd_ut     : Julian Day (UT)
    lat       : observer latitude (degrees)
    lon       : observer longitude (degrees, east positive)
    star_name : fixed star name (catalog lookup)

    Returns
    -------
    Altitude in degrees (positive = above horizon)
    """
    from .julian import ut_to_tt, centuries_from_j2000

    jd_tt = ut_to_tt(jd_ut)
    # Get star equatorial coordinates (via ecliptic → equatorial)
    # fixed_star_at returns tropical ecliptic (lon, lat) — convert to equatorial
    star_pos = fixed_star_at(star_name, jd_tt)

    # Convert ecliptic → equatorial using mean obliquity at the epoch
    obliquity = mean_obliquity(jd_tt)
    eps_r = obliquity * DEG2RAD
    lon_ecl = star_pos.longitude * DEG2RAD
    lat_ecl = star_pos.latitude  * DEG2RAD

    # Standard ecliptic-to-equatorial rotation
    sin_dec = (math.sin(lat_ecl) * math.cos(eps_r)
               + math.cos(lat_ecl) * math.sin(eps_r) * math.sin(lon_ecl))
    sin_dec = max(-1.0, min(1.0, sin_dec))
    dec_r   = math.asin(sin_dec)

    cos_ra_cos_dec = math.cos(lon_ecl) * math.cos(lat_ecl)
    sin_ra_cos_dec = (math.sin(lon_ecl) * math.cos(lat_ecl) * math.cos(eps_r)
                      - math.sin(lat_ecl) * math.sin(eps_r))
    ra_r = math.atan2(sin_ra_cos_dec, cos_ra_cos_dec)
    ra_deg = math.degrees(ra_r) % 360.0

    # Local Sidereal Time (degrees)
    T = centuries_from_j2000(jd_ut)
    gmst = (280.46061837 + 360.98564736629 * (jd_ut - 2451545.0)
            + 0.000387933 * T**2 - T**3 / 38710000.0)
    lst_deg = (gmst + lon) % 360.0

    # Hour angle
    ha = (lst_deg - ra_deg) % 360.0
    if ha > 180.0:
        ha -= 360.0

    lat_r = lat * DEG2RAD
    ha_r  = ha  * DEG2RAD

    sin_alt = (math.sin(lat_r) * math.sin(dec_r)
               + math.cos(lat_r) * math.cos(dec_r) * math.cos(ha_r))
    return math.degrees(math.asin(max(-1.0, min(1.0, sin_alt))))


def _sun_altitude(jd_ut: float, lat: float, lon: float) -> float:
    """
    Compute the altitude of the Sun at the given UT Julian Day and location.

    Uses `rise_set._altitude` which in turn calls `planet_at("Sun", ...)`.

    Parameters
    ----------
    jd_ut : Julian Day (UT)
    lat   : observer latitude (degrees)
    lon   : observer longitude (degrees, east positive)

    Returns
    -------
    Solar altitude in degrees
    """
    from .rise_set import _altitude
    return _altitude(jd_ut, lat, lon, "Sun")


def _find_star_rise(
    star_name: str,
    jd_day: float,
    lat: float,
    lon: float,
    horizon_alt: float = -0.5667,
) -> float | None:
    """
    Find the star's rising time (JD) within the 24 hours starting at jd_day.

    Parameters
    ----------
    star_name   : fixed star name
    jd_day      : start of the search window (JD, UT)
    lat         : observer latitude (degrees)
    lon         : observer longitude (degrees, east positive)
    horizon_alt : altitude threshold for "rising" (degrees); default −0.5667
                  accounts for atmospheric refraction only (no disk radius)

    Returns
    -------
    JD of rising, or None if the star does not rise within the window
    """
    steps = 24
    prev_alt = _star_altitude(jd_day, lat, lon, star_name) - horizon_alt

    for i in range(1, steps + 1):
        jd = jd_day + i / steps
        curr_alt = _star_altitude(jd, lat, lon, star_name) - horizon_alt

        if prev_alt < 0.0 and curr_alt >= 0.0:
            # Rising: refine via bisection
            t0, t1 = jd - 1.0 / steps, jd
            for _ in range(10):
                tm = (t0 + t1) / 2.0
                a0 = _star_altitude(t0, lat, lon, star_name) - horizon_alt
                am = _star_altitude(tm, lat, lon, star_name) - horizon_alt
                if a0 * am < 0.0:
                    t1 = tm
                else:
                    t0 = tm
            return (t0 + t1) / 2.0

        prev_alt = curr_alt

    return None


def _find_star_set(
    star_name: str,
    jd_day: float,
    lat: float,
    lon: float,
    horizon_alt: float = -0.5667,
) -> float | None:
    """
    Find the star's setting time (JD) within the 24 hours starting at jd_day.

    Parameters
    ----------
    star_name   : fixed star name
    jd_day      : start of the search window (JD, UT)
    lat         : observer latitude (degrees)
    lon         : observer longitude (degrees, east positive)
    horizon_alt : altitude threshold for "setting" (degrees)

    Returns
    -------
    JD of setting, or None if the star does not set within the window
    """
    steps = 24
    prev_alt = _star_altitude(jd_day, lat, lon, star_name) - horizon_alt

    for i in range(1, steps + 1):
        jd = jd_day + i / steps
        curr_alt = _star_altitude(jd, lat, lon, star_name) - horizon_alt

        if prev_alt >= 0.0 and curr_alt < 0.0:
            # Setting: refine via bisection
            t0, t1 = jd - 1.0 / steps, jd
            for _ in range(10):
                tm = (t0 + t1) / 2.0
                a0 = _star_altitude(t0, lat, lon, star_name) - horizon_alt
                am = _star_altitude(tm, lat, lon, star_name) - horizon_alt
                if a0 * am < 0.0:
                    t1 = tm
                else:
                    t0 = tm
            return (t0 + t1) / 2.0

        prev_alt = curr_alt

    return None


def heliacal_rising_event(
    star_name: str,
    jd_start: float,
    lat: float,
    lon: float,
    arcus_visionis: float | None = None,
    search_days: int = 400,
    policy: FixedStarComputationPolicy | None = None,
) -> HeliacalEvent | None:
    """
    Find the Julian Day of the heliacal rising of a fixed star.

    The heliacal rising is the first morning when the star is visible
    on the eastern horizon just before sunrise, after a period of
    invisibility due to proximity to the Sun.

    Parameters
    ----------
    star_name      : fixed star name (must be in the catalog)
    jd_start       : start searching from this JD (UT)
    lat            : observer latitude (degrees)
    lon            : observer longitude (degrees, east positive)
    arcus_visionis : solar depression angle required (degrees).
                     If None, computed from star magnitude.
    search_days    : maximum days to search

    Returns
    -------
    JD of heliacal rising (UT), or None if not found within search_days

    Algorithm
    ---------
    On each day:
      1. Compute star's elongation from the Sun.
         If elongation < 12°, star is too close to Sun — skip.
      2. Find the star's rising time for the day.
      3. Compute Sun's altitude at the star's rising time.
      4. If Sun altitude ≈ −arcus_visionis (within ±1°), this is the
         heliacal rising.
    """
    from .julian import ut_to_tt
    from .planets import planet_at

    if not isinstance(star_name, str) or not star_name.strip():
        raise ValueError("star_name must be a non-empty string")
    _require_finite(jd_start, "jd_start")
    _validate_lat_lon(lat, lon)
    if not isinstance(search_days, int) or search_days <= 0:
        raise ValueError("search_days must be a positive integer")
    if arcus_visionis is not None:
        _require_finite(arcus_visionis, "arcus_visionis")
        if arcus_visionis <= 0:
            raise ValueError("arcus_visionis must be positive")
    policy = _resolve_fixed_star_policy(policy)
    _validate_fixed_star_policy(policy)

    # Determine arcus visionis from catalog magnitude if not provided
    try:
        mag = star_magnitude(star_name)
    except KeyError:
        mag = 2.0
    av = arcus_visionis if arcus_visionis is not None else _arcus_visionis(mag)

    elongations: list[float] = []
    for day_offset in range(search_days):
        jd = jd_start + day_offset
        jd_tt = ut_to_tt(jd)
        star_pos = fixed_star_at(star_name, jd_tt, policy=policy)
        sun_pos = planet_at("Sun", jd)
        elongation = abs((star_pos.longitude - sun_pos.longitude + 180.0) % 360.0 - 180.0)
        elongations.append(elongation)

    # A true heliacal rising must occur after the annual solar conjunction,
    # not just on any morning when the star happens to be visible pre-dawn.
    conjunction_offset = min(range(search_days), key=lambda idx: elongations[idx])

    for day_offset in range(conjunction_offset, search_days):
        jd = jd_start + day_offset
        elongation = elongations[day_offset]
        if elongation < policy.heliacal.elongation_threshold:
            continue  # star still hidden in Sun's rays

        # Find rising time on this day
        star_rise_jd = _find_star_rise(star_name, jd, lat, lon)
        if star_rise_jd is None:
            continue

        # Sun altitude at the moment of star's rising
        sun_alt = _sun_altitude(star_rise_jd, lat, lon)

        # Heliacal rising condition: Sun is just below horizon at −av
        if -av - policy.heliacal.visibility_tolerance <= sun_alt <= -av + policy.heliacal.visibility_tolerance:
            truth = HeliacalEventTruth(
                event_kind="rising",
                star_name=star_name,
                jd_start=jd_start,
                search_days=search_days,
                arcus_visionis=av,
                elongation_threshold=policy.heliacal.elongation_threshold,
                conjunction_offset=conjunction_offset,
                qualifying_day_offset=day_offset,
                qualifying_elongation=elongation,
                qualifying_sun_altitude=sun_alt,
                event_jd_ut=star_rise_jd,
            )
            return HeliacalEvent(
                jd_ut=star_rise_jd,
                truth=truth,
                classification=_classify_heliacal_event_truth(truth),
                relation=StarRelation(
                    kind="heliacal_event",
                    basis="heliacal_visibility",
                    star_name=star_name,
                    event_kind="rising",
                ),
                condition_profile=StarConditionProfile(
                    result_kind="heliacal_event",
                    condition_state=StarConditionState("heliacal_event"),
                    relation_kind="heliacal_event",
                    relation_basis="heliacal_visibility",
                    event_kind="rising",
                ),
            )

    return None


def heliacal_setting_event(
    star_name: str,
    jd_start: float,
    lat: float,
    lon: float,
    arcus_visionis: float | None = None,
    search_days: int = 400,
    policy: FixedStarComputationPolicy | None = None,
) -> HeliacalEvent | None:
    """
    Find the Julian Day of the heliacal setting (last evening visibility) of a star.

    The heliacal setting is the last evening when the star is visible on the
    western horizon after sunset, before it disappears into the Sun's light.

    Parameters
    ----------
    star_name      : fixed star name (must be in the catalog)
    jd_start       : start searching from this JD (UT)
    lat            : observer latitude (degrees)
    lon            : observer longitude (degrees, east positive)
    arcus_visionis : solar depression angle required (degrees).
                     If None, computed from star magnitude.
    search_days    : maximum days to search

    Returns
    -------
    JD of heliacal setting (UT), or None if not found within search_days

    Algorithm
    ---------
    On each day:
      1. Compute star's elongation from the Sun.
         If elongation < 12°, the star has already disappeared — return the
         last known visible setting JD.
      2. Find the star's setting time for the day.
      3. Compute Sun's altitude at that setting time.
      4. If Sun altitude ≤ −av/2, record this as a candidate last-visible JD.
    """
    from .julian import ut_to_tt
    from .planets import planet_at

    if not isinstance(star_name, str) or not star_name.strip():
        raise ValueError("star_name must be a non-empty string")
    _require_finite(jd_start, "jd_start")
    _validate_lat_lon(lat, lon)
    if not isinstance(search_days, int) or search_days <= 0:
        raise ValueError("search_days must be a positive integer")
    if arcus_visionis is not None:
        _require_finite(arcus_visionis, "arcus_visionis")
        if arcus_visionis <= 0:
            raise ValueError("arcus_visionis must be positive")
    policy = _resolve_fixed_star_policy(policy)
    _validate_fixed_star_policy(policy)

    # Determine arcus visionis
    try:
        mag = star_magnitude(star_name)
    except KeyError:
        mag = 2.0
    av = arcus_visionis if arcus_visionis is not None else _arcus_visionis(mag)

    last_visible_jd: float | None = None

    for day_offset in range(search_days):
        jd = jd_start + day_offset
        jd_tt = ut_to_tt(jd)

        star_pos = fixed_star_at(star_name, jd_tt, policy=policy)
        sun_pos  = planet_at("Sun", jd)

        elongation = abs((star_pos.longitude - sun_pos.longitude + 180.0) % 360.0 - 180.0)
        if elongation < policy.heliacal.elongation_threshold:
            # Star has disappeared into the Sun — return last visible JD
            if last_visible_jd is None:
                return None
            truth = HeliacalEventTruth(
                event_kind="setting",
                star_name=star_name,
                jd_start=jd_start,
                search_days=search_days,
                arcus_visionis=av,
                elongation_threshold=policy.heliacal.elongation_threshold,
                conjunction_offset=None,
                qualifying_day_offset=day_offset - 1,
                qualifying_elongation=elongation,
                qualifying_sun_altitude=None,
                event_jd_ut=last_visible_jd,
            )
            return HeliacalEvent(
                jd_ut=last_visible_jd,
                truth=truth,
                classification=_classify_heliacal_event_truth(truth),
                relation=StarRelation(
                    kind="heliacal_event",
                    basis="heliacal_visibility",
                    star_name=star_name,
                    event_kind="setting",
                ),
                condition_profile=StarConditionProfile(
                    result_kind="heliacal_event",
                    condition_state=StarConditionState("heliacal_event"),
                    relation_kind="heliacal_event",
                    relation_basis="heliacal_visibility",
                    event_kind="setting",
                ),
            )

        star_set_jd = _find_star_set(star_name, jd, lat, lon)
        if star_set_jd is None:
            continue

        sun_alt = _sun_altitude(star_set_jd, lat, lon)
        if sun_alt <= -(av * policy.heliacal.setting_visibility_factor):
            last_visible_jd = star_set_jd

    if last_visible_jd is None:
        return None
    truth = HeliacalEventTruth(
        event_kind="setting",
        star_name=star_name,
        jd_start=jd_start,
        search_days=search_days,
        arcus_visionis=av,
        elongation_threshold=policy.heliacal.elongation_threshold,
        conjunction_offset=None,
        qualifying_day_offset=search_days - 1,
        qualifying_elongation=None,
        qualifying_sun_altitude=None,
        event_jd_ut=last_visible_jd,
    )
    return HeliacalEvent(
        jd_ut=last_visible_jd,
        truth=truth,
        classification=_classify_heliacal_event_truth(truth),
        relation=StarRelation(
            kind="heliacal_event",
            basis="heliacal_visibility",
            star_name=star_name,
            event_kind="setting",
        ),
        condition_profile=StarConditionProfile(
            result_kind="heliacal_event",
            condition_state=StarConditionState("heliacal_event"),
            relation_kind="heliacal_event",
            relation_basis="heliacal_visibility",
            event_kind="setting",
        ),
    )


def heliacal_rising(
    star_name: str,
    jd_start: float,
    lat: float,
    lon: float,
    arcus_visionis: float | None = None,
    search_days: int = 400,
    policy: FixedStarComputationPolicy | None = None,
) -> float | None:
    """Backward-compatible heliacal rising JD wrapper."""

    event = heliacal_rising_event(
        star_name,
        jd_start,
        lat,
        lon,
        arcus_visionis=arcus_visionis,
        search_days=search_days,
        policy=policy,
    )
    return None if event is None else event.jd_ut


def heliacal_setting(
    star_name: str,
    jd_start: float,
    lat: float,
    lon: float,
    arcus_visionis: float | None = None,
    search_days: int = 400,
    policy: FixedStarComputationPolicy | None = None,
) -> float | None:
    """Backward-compatible heliacal setting JD wrapper."""

    event = heliacal_setting_event(
        star_name,
        jd_start,
        lat,
        lon,
        arcus_visionis=arcus_visionis,
        search_days=search_days,
        policy=policy,
    )
    return None if event is None else event.jd_ut


def star_chart_condition_profile(
    *,
    positions: list[StarPosition] | None = None,
    heliacal_events: list[HeliacalEvent] | None = None,
    unified_stars: list["FixedStar"] | None = None,
) -> StarChartConditionProfile:
    """Aggregate current star condition profiles into one chart-wide vessel."""

    profiles: list[StarConditionProfile] = []
    if positions is not None:
        profiles.extend(
            position.condition_profile
            for position in positions
            if position.condition_profile is not None
        )
    if heliacal_events is not None:
        profiles.extend(
            event.condition_profile
            for event in heliacal_events
            if event.condition_profile is not None
        )
    if unified_stars is not None:
        profiles.extend(
            star.condition_profile
            for star in unified_stars
            if star.condition_profile is not None
        )

    ordered_profiles = tuple(sorted(profiles, key=_star_condition_sort_key))
    if ordered_profiles:
        strongest_rank = max(_star_condition_strength(profile) for profile in ordered_profiles)
        weakest_rank = min(_star_condition_strength(profile) for profile in ordered_profiles)
        strongest_profiles = tuple(
            profile for profile in ordered_profiles
            if _star_condition_strength(profile) == strongest_rank
        )
        weakest_profiles = tuple(
            profile for profile in ordered_profiles
            if _star_condition_strength(profile) == weakest_rank
        )
    else:
        strongest_profiles = ()
        weakest_profiles = ()

    return StarChartConditionProfile(
        profiles=ordered_profiles,
        catalog_position_count=sum(1 for profile in ordered_profiles if profile.condition_state.name == "catalog_position"),
        heliacal_event_count=sum(1 for profile in ordered_profiles if profile.condition_state.name == "heliacal_event"),
        unified_merge_count=sum(1 for profile in ordered_profiles if profile.condition_state.name == "unified_merge"),
        strongest_profiles=strongest_profiles,
        weakest_profiles=weakest_profiles,
    )


def star_condition_network_profile(
    *,
    positions: list[StarPosition] | None = None,
    heliacal_events: list[HeliacalEvent] | None = None,
    unified_stars: list["FixedStar"] | None = None,
) -> StarConditionNetworkProfile:
    """Project current star relations into a small directed condition network."""

    star_ids: set[str] = set()
    source_ids: set[str] = set()
    event_ids: set[str] = set()
    edges: list[StarConditionNetworkEdge] = []

    if positions is not None:
        for position in positions:
            if position.relation is None or position.condition_profile is None:
                continue
            star_id = f"star:{position.name}"
            source_id = f"source:catalog_lookup"
            star_ids.add(star_id)
            source_ids.add(source_id)
            edges.append(StarConditionNetworkEdge(
                source_id=source_id,
                target_id=star_id,
                relation_kind=position.relation.kind,
                relation_basis=position.relation.basis,
                condition_state=position.condition_profile.condition_state.name,
            ))

    if heliacal_events is not None:
        for event in heliacal_events:
            if event.relation is None or event.condition_profile is None:
                continue
            star_id = f"star:{event.truth.star_name}"
            event_id = f"event:{event.event_kind}"
            star_ids.add(star_id)
            event_ids.add(event_id)
            edges.append(StarConditionNetworkEdge(
                source_id=event_id,
                target_id=star_id,
                relation_kind=event.relation.kind,
                relation_basis=event.relation.basis,
                condition_state=event.condition_profile.condition_state.name,
            ))

    if unified_stars is not None:
        for star in unified_stars:
            if star.relation is None or star.condition_profile is None:
                continue
            star_id = f"star:{star.name or 'unnamed'}"
            source_kind = star.relation.source_kind if star.relation is not None else (star.source_kind or "hipparcos")
            source_id = f"source:{source_kind}"
            star_ids.add(star_id)
            source_ids.add(source_id)
            edges.append(StarConditionNetworkEdge(
                source_id=source_id,
                target_id=star_id,
                relation_kind=star.relation.kind,
                relation_basis=star.relation.basis,
                condition_state=star.condition_profile.condition_state.name,
            ))

    node_ids = sorted(star_ids) + sorted(event_ids) + sorted(source_ids)
    incoming = {node_id: 0 for node_id in node_ids}
    outgoing = {node_id: 0 for node_id in node_ids}
    for edge in edges:
        outgoing[edge.source_id] += 1
        incoming[edge.target_id] += 1

    nodes: list[StarConditionNetworkNode] = []
    for node_id in star_ids:
        nodes.append(StarConditionNetworkNode(
            node_id=node_id,
            kind="star",
            incoming_count=incoming[node_id],
            outgoing_count=outgoing[node_id],
        ))
    for node_id in event_ids:
        nodes.append(StarConditionNetworkNode(
            node_id=node_id,
            kind="event",
            incoming_count=incoming[node_id],
            outgoing_count=outgoing[node_id],
        ))
    for node_id in source_ids:
        nodes.append(StarConditionNetworkNode(
            node_id=node_id,
            kind="source",
            incoming_count=incoming[node_id],
            outgoing_count=outgoing[node_id],
        ))

    ordered_nodes = tuple(sorted(nodes, key=lambda node: (node.kind, node.node_id)))
    ordered_edges = tuple(sorted(
        edges,
        key=lambda edge: (edge.source_id, edge.target_id, edge.relation_kind, edge.relation_basis, edge.condition_state),
    ))
    isolated_nodes = tuple(node for node in ordered_nodes if node.total_degree == 0)
    if ordered_nodes:
        max_degree = max(node.total_degree for node in ordered_nodes)
        most_connected_nodes = tuple(node for node in ordered_nodes if node.total_degree == max_degree)
    else:
        most_connected_nodes = ()

    return StarConditionNetworkProfile(
        nodes=ordered_nodes,
        edges=ordered_edges,
        isolated_nodes=isolated_nodes,
        most_connected_nodes=most_connected_nodes,
    )
