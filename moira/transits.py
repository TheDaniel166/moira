"""
Moira — transits.py
The Transit Engine: governs transit and ingress search, planet returns,
and prenatal syzygy computation.

Boundary: owns longitude-crossing detection, sign ingress search, solar/lunar/
planet return computation, and prenatal syzygy resolution. Delegates body
position resolution to planets, nodes, asteroids, and fixed_stars. Delegates
Julian Day arithmetic to julian. Does NOT own ephemeris state.

Public surface:
    TransitEvent, IngressEvent,
    next_transit, find_transits, find_ingresses,
    planet_return, solar_return, lunar_return,
    last_new_moon, last_full_moon, prenatal_syzygy

Import-time side effects: None

External dependency assumptions:
    - No third-party packages; stdlib only plus internal moira modules.
    - SpkReader must be initialised before any public function is called.
"""

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum

from .constants import Body, SIGNS
from .julian import (
    CalendarDateTime,
    calendar_datetime_from_jd,
    datetime_from_jd,
    format_jd_utc,
    jd_from_datetime,
    julian_day,
    ut_to_tt,
)
from .planets import planet_at
from .spk_reader import get_reader, SpkReader
from .asteroids import asteroid_at, ASTEROID_NAIF
from .fixed_stars import fixed_star_at
from .nodes import mean_lilith, mean_node, true_lilith, true_node


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


class TransitTargetKind(StrEnum):
    """Typed classification of how a transit target longitude was resolved."""

    NUMERIC_LONGITUDE = "numeric_longitude"
    PLANET = "planet"
    NODE = "node"
    LILITH = "lilith"
    ASTEROID = "asteroid"
    FIXED_STAR = "fixed_star"


class TransitSearchKind(StrEnum):
    """Typed classification of the current transit search mode."""

    LONGITUDE_CROSSING = "longitude_crossing"
    SIGN_INGRESS = "sign_ingress"
    PHASE_CROSSING = "phase_crossing"


class TransitWrapperKind(StrEnum):
    """Typed classification of higher-level transit wrappers."""

    DIRECT_TRANSIT = "direct_transit"
    TRANSIT_RANGE = "transit_range"
    INGRESS = "ingress"
    PLANET_RETURN = "planet_return"
    SOLAR_RETURN = "solar_return"
    LUNAR_RETURN = "lunar_return"
    LAST_NEW_MOON = "last_new_moon"
    LAST_FULL_MOON = "last_full_moon"
    PRENATAL_SYZYGY = "prenatal_syzygy"


class TransitRelationKind(StrEnum):
    """Typed relational surface for the current transit subsystem."""

    TARGET_CROSSING = "target_crossing"
    SIGN_INGRESS = "sign_ingress"


class TransitRelationBasis(StrEnum):
    """Explicit doctrinal basis for a transit relation."""

    NUMERIC_LONGITUDE = "numeric_longitude"
    PLANET = "planet"
    NODE = "node"
    LILITH = "lilith"
    ASTEROID = "asteroid"
    FIXED_STAR = "fixed_star"
    SIGN_BOUNDARY = "sign_boundary"


@dataclass(slots=True)
class TransitRelation:
    """
    First-class relational truth for one transit or ingress event.

    This formalizes the already-computed relation between a moving body and the
    target or sign boundary it reached. It does not introduce new doctrine or
    recompute longitude state independently of the transit engine.
    """

    source_body: str
    relation_kind: TransitRelationKind
    basis: TransitRelationBasis
    target_name: str
    target_longitude: float
    is_dynamic_target: bool

    def __post_init__(self) -> None:
        if not self.source_body:
            raise ValueError("TransitRelation invariant failed: source_body must not be empty")
        if not self.target_name:
            raise ValueError("TransitRelation invariant failed: target_name must not be empty")
        if not math.isfinite(self.target_longitude):
            raise ValueError("TransitRelation invariant failed: target_longitude must be finite")
        if self.relation_kind is TransitRelationKind.SIGN_INGRESS:
            if self.basis is not TransitRelationBasis.SIGN_BOUNDARY:
                raise ValueError("TransitRelation invariant failed: sign ingress must use sign_boundary basis")
            if self.is_dynamic_target:
                raise ValueError("TransitRelation invariant failed: sign ingress must not be dynamic")
        elif self.basis is TransitRelationBasis.SIGN_BOUNDARY:
            raise ValueError("TransitRelation invariant failed: sign_boundary basis is reserved for sign ingress")


@dataclass(slots=True, frozen=True)
class TransitSearchPolicy:
    """
    Explicit doctrine for longitude-crossing and ingress search cadence.

    This governs local search cadence and solver tolerance only. It does not
    imply stronger astronomical accuracy than the delegated longitude engines.
    """

    step_days_override: float | None = None
    solver_tolerance_days: float = 1e-6


@dataclass(slots=True, frozen=True)
class ReturnSearchPolicy:
    """
    Explicit doctrine for planet-return search windows and cadence.

    Per-body overrides are expressed as ordered ``(body, max_days)`` pairs so
    policy remains deterministic and inspectable.
    """

    step_days_override: float | None = None
    default_max_days: float | None = None
    per_body_max_days: tuple[tuple[str, float], ...] = ()


@dataclass(slots=True, frozen=True)
class SyzygySearchPolicy:
    """Explicit doctrine for New Moon / Full Moon / prenatal syzygy search."""

    scan_step_days: float = 1.0
    solver_tolerance_days: float = 1e-6
    max_synodic_multiple: float = 1.1


@dataclass(slots=True, frozen=True)
class TransitComputationPolicy:
    """
    Lean backend policy surface for the transit subsystem.

    The default policy preserves current behavior exactly. Policy governs search
    doctrine and wrapper search envelopes, not the delegated longitude engines.
    """

    transit: TransitSearchPolicy = field(default_factory=TransitSearchPolicy)
    ingress: TransitSearchPolicy = field(default_factory=TransitSearchPolicy)
    returns: ReturnSearchPolicy = field(default_factory=ReturnSearchPolicy)
    syzygy: SyzygySearchPolicy = field(default_factory=SyzygySearchPolicy)


@dataclass(slots=True)
class LongitudeResolutionClassification:
    """Typed classification for preserved transit target-resolution truth."""

    target_kind: TransitTargetKind
    resolved_name: str

    def __post_init__(self) -> None:
        if not self.resolved_name:
            raise ValueError("LongitudeResolutionClassification invariant failed: resolved_name must not be empty")


@dataclass(slots=True)
class CrossingSearchClassification:
    """Typed classification for preserved transit search truth."""

    search_kind: TransitSearchKind
    wrapper_kind: TransitWrapperKind
    uses_bisection: bool
    uses_dynamic_target: bool

    def __post_init__(self) -> None:
        if not isinstance(self.uses_bisection, bool) or not isinstance(self.uses_dynamic_target, bool):
            raise ValueError("CrossingSearchClassification invariant failed: boolean flags must be bool")


@dataclass(slots=True)
class TransitComputationClassification:
    """Lean typed classification over preserved transit computation truth."""

    body: str
    target: LongitudeResolutionClassification
    search: CrossingSearchClassification

    def __post_init__(self) -> None:
        if not self.body:
            raise ValueError("TransitComputationClassification invariant failed: body must not be empty")


@dataclass(slots=True)
class IngressComputationClassification:
    """Lean typed classification over preserved ingress computation truth."""

    body: str
    sign: str
    search: CrossingSearchClassification

    def __post_init__(self) -> None:
        if not self.body:
            raise ValueError("IngressComputationClassification invariant failed: body must not be empty")
        if self.search.search_kind is not TransitSearchKind.SIGN_INGRESS:
            raise ValueError("IngressComputationClassification invariant failed: search_kind must be sign_ingress")


@dataclass(slots=True)
class LongitudeResolutionTruth:
    """
    Preserved target-resolution truth for one transit computation.

    This preserves how a target longitude was resolved at a specific Julian Day.
    It records delegated source kind and resolved longitude, but does not claim
    independent astronomical accuracy beyond the delegated longitude engines.
    """

    requested_spec: str | float
    resolved_kind: str
    resolved_name: str
    jd_ut: float
    longitude: float

    def __post_init__(self) -> None:
        if self.resolved_kind not in {kind.value for kind in TransitTargetKind}:
            raise ValueError("LongitudeResolutionTruth invariant failed: resolved_kind must be supported")
        if not self.resolved_name:
            raise ValueError("LongitudeResolutionTruth invariant failed: resolved_name must not be empty")
        if not math.isfinite(self.jd_ut):
            raise ValueError("LongitudeResolutionTruth invariant failed: jd_ut must be finite")
        if not math.isfinite(self.longitude):
            raise ValueError("LongitudeResolutionTruth invariant failed: longitude must be finite")


@dataclass(slots=True)
class CrossingSearchTruth:
    """
    Preserved search/bracketing truth for one detected longitude crossing.

    This preserves local solver state such as scan step, bracketing interval,
    and bisection tolerance. It describes search precision only. It does not
    state a stronger end-to-end model accuracy than the delegated longitude
    sources justify.
    """

    search_start_jd_ut: float
    search_end_jd_ut: float
    step_days: float
    bracket_start_jd_ut: float
    bracket_end_jd_ut: float
    crossing_jd_ut: float
    solver_tolerance_days: float

    def __post_init__(self) -> None:
        values = (
            self.search_start_jd_ut,
            self.search_end_jd_ut,
            self.step_days,
            self.bracket_start_jd_ut,
            self.bracket_end_jd_ut,
            self.crossing_jd_ut,
            self.solver_tolerance_days,
        )
        if not all(math.isfinite(value) for value in values):
            raise ValueError("CrossingSearchTruth invariant failed: all values must be finite")
        if self.step_days <= 0:
            raise ValueError("CrossingSearchTruth invariant failed: step_days must be positive")
        if self.solver_tolerance_days <= 0:
            raise ValueError("CrossingSearchTruth invariant failed: solver_tolerance_days must be positive")
        if self.search_start_jd_ut > self.search_end_jd_ut:
            raise ValueError("CrossingSearchTruth invariant failed: search interval must be ordered")
        if self.bracket_start_jd_ut > self.bracket_end_jd_ut:
            raise ValueError("CrossingSearchTruth invariant failed: bracket interval must be ordered")
        if not (self.bracket_start_jd_ut <= self.crossing_jd_ut <= self.bracket_end_jd_ut):
            raise ValueError("CrossingSearchTruth invariant failed: crossing_jd_ut must lie inside bracket")


@dataclass(slots=True)
class TransitComputationTruth:
    """
    Preserved doctrinal/computational truth for one transit crossing.

    This is Phase 1 truth preservation only. It records how the target was
    resolved and how the crossing was bracketed, without altering transit
    semantics or overclaiming numerical accuracy beyond delegated engines.
    """

    body: str
    requested_target: str | float
    direction_filter: str
    target_truth: LongitudeResolutionTruth
    search_truth: CrossingSearchTruth

    def __post_init__(self) -> None:
        if not self.body:
            raise ValueError("TransitComputationTruth invariant failed: body must not be empty")
        if self.direction_filter not in {"direct", "retrograde", "either"}:
            raise ValueError("TransitComputationTruth invariant failed: direction_filter must be supported")


@dataclass(slots=True)
class IngressComputationTruth:
    """
    Preserved doctrinal/computational truth for one ingress event.

    This records the boundary sign and longitude plus the search bracket that
    produced the ingress, while preserving current ingress semantics intact.
    """

    body: str
    sign: str
    boundary_longitude: float
    search_truth: CrossingSearchTruth

    def __post_init__(self) -> None:
        if not self.body:
            raise ValueError("IngressComputationTruth invariant failed: body must not be empty")
        if self.sign not in SIGNS:
            raise ValueError("IngressComputationTruth invariant failed: sign must be valid")
        if not math.isfinite(self.boundary_longitude):
            raise ValueError("IngressComputationTruth invariant failed: boundary_longitude must be finite")


def _classify_resolution_truth(
    truth: LongitudeResolutionTruth,
) -> LongitudeResolutionClassification:
    """Classify preserved target-resolution truth without changing meaning."""

    return LongitudeResolutionClassification(
        target_kind=TransitTargetKind(truth.resolved_kind),
        resolved_name=truth.resolved_name,
    )


def _classify_transit_computation_truth(
    truth: TransitComputationTruth,
    *,
    wrapper_kind: TransitWrapperKind,
) -> TransitComputationClassification:
    """Classify preserved transit computation truth without changing semantics."""

    return TransitComputationClassification(
        body=truth.body,
        target=_classify_resolution_truth(truth.target_truth),
        search=CrossingSearchClassification(
            search_kind=TransitSearchKind.LONGITUDE_CROSSING,
            wrapper_kind=wrapper_kind,
            uses_bisection=True,
            uses_dynamic_target=truth.target_truth.resolved_kind != "numeric_longitude",
        ),
    )


def _classify_ingress_computation_truth(
    truth: IngressComputationTruth,
) -> IngressComputationClassification:
    """Classify preserved ingress computation truth without changing semantics."""

    return IngressComputationClassification(
        body=truth.body,
        sign=truth.sign,
        search=CrossingSearchClassification(
            search_kind=TransitSearchKind.SIGN_INGRESS,
            wrapper_kind=TransitWrapperKind.INGRESS,
            uses_bisection=True,
            uses_dynamic_target=False,
        ),
    )


def _build_transit_relation(truth: TransitComputationTruth) -> TransitRelation:
    """Formalize the already-computed body-to-target transit relation."""

    target_kind = TransitTargetKind(truth.target_truth.resolved_kind)
    return TransitRelation(
        source_body=truth.body,
        relation_kind=TransitRelationKind.TARGET_CROSSING,
        basis=TransitRelationBasis(target_kind.value),
        target_name=truth.target_truth.resolved_name,
        target_longitude=truth.target_truth.longitude,
        is_dynamic_target=target_kind is not TransitTargetKind.NUMERIC_LONGITUDE,
    )


def _build_ingress_relation(truth: IngressComputationTruth) -> TransitRelation:
    """Formalize the already-computed body-to-sign-boundary ingress relation."""

    return TransitRelation(
        source_body=truth.body,
        relation_kind=TransitRelationKind.SIGN_INGRESS,
        basis=TransitRelationBasis.SIGN_BOUNDARY,
        target_name=truth.sign,
        target_longitude=truth.boundary_longitude,
        is_dynamic_target=False,
    )

@dataclass(slots=True)
class TransitEvent:
    """
    RITE: The Transit Event Vessel

    THEOREM: Governs the storage of a single moment when a body crosses an exact
    ecliptic longitude.

    RITE OF PURPOSE:
        TransitEvent is the authoritative data vessel for a single longitude-crossing
        event produced by the Transit Engine. It captures the body name, the target
        longitude crossed, the Julian Day of crossing, and the direction of motion.
        Without it, callers would receive unstructured tuples with no field-level
        guarantees. It exists to give every higher-level consumer a single, named,
        mutable record of each transit crossing.

    LAW OF OPERATION:
        Responsibilities:
            - Store a single transit crossing as named, typed fields
            - Expose UTC datetime and CalendarDateTime views via read-only properties
            - Serve as the return type of next_transit() and find_transits()
        Non-responsibilities:
            - Computing transit times (delegates to next_transit / find_transits)
            - Resolving body positions (delegates to planets / nodes / asteroids)
            - Converting Julian Days to display strings (delegates to julian)
        Dependencies:
            - Populated by next_transit() and find_transits()
            - datetime_utc delegates to datetime_from_jd()
            - calendar_utc delegates to calendar_datetime_from_jd()
        Structural invariants:
            - longitude is in [0, 360)
            - direction is 'direct' or 'retrograde'
        Behavioral invariants:
            - All consumers treat TransitEvent fields as read-only after construction

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.transits.TransitEvent",
      "risk": "high",
      "api": {
        "frozen": ["body", "longitude", "jd_ut", "direction"],
        "internal": ["datetime_utc", "calendar_utc"]
      },
      "state": {"mutable": true, "owners": ["next_transit", "find_transits"]},
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
    body:        str
    longitude:   float        # the target longitude that was crossed
    jd_ut:       float        # Julian Day of crossing
    direction:   str          # 'direct' or 'retrograde'
    computation_truth: TransitComputationTruth | None = None
    classification: TransitComputationClassification | None = None
    relation: TransitRelation | None = None

    def __post_init__(self) -> None:
        if not self.body:
            raise ValueError("TransitEvent invariant failed: body must not be empty")
        if not math.isfinite(self.longitude):
            raise ValueError("TransitEvent invariant failed: longitude must be finite")
        if not math.isfinite(self.jd_ut):
            raise ValueError("TransitEvent invariant failed: jd_ut must be finite")
        if self.direction not in {"direct", "retrograde"}:
            raise ValueError("TransitEvent invariant failed: direction must be supported")
        if self.computation_truth is not None:
            if self.computation_truth.body != self.body:
                raise ValueError("TransitEvent invariant failed: computation_truth body must match body")
            if self.computation_truth.target_truth.longitude != self.longitude:
                raise ValueError("TransitEvent invariant failed: computation_truth target longitude must match longitude")
            if self.computation_truth.search_truth.crossing_jd_ut != self.jd_ut:
                raise ValueError("TransitEvent invariant failed: computation_truth crossing_jd_ut must match jd_ut")
        if self.classification is not None:
            if self.classification.body != self.body:
                raise ValueError("TransitEvent invariant failed: classification body must match body")
        if self.relation is not None:
            if self.relation.source_body != self.body:
                raise ValueError("TransitEvent invariant failed: relation source_body must match body")
            if self.relation.relation_kind is not TransitRelationKind.TARGET_CROSSING:
                raise ValueError("TransitEvent invariant failed: relation_kind must be target_crossing")
            if self.relation.target_longitude != self.longitude:
                raise ValueError("TransitEvent invariant failed: relation target_longitude must match longitude")
        if self.computation_truth is not None and self.classification is not None:
            if self.classification.target.target_kind.value != self.computation_truth.target_truth.resolved_kind:
                raise ValueError("TransitEvent invariant failed: classification target kind must match computation truth")
        if self.computation_truth is not None and self.relation is not None:
            if self.relation.target_name != self.computation_truth.target_truth.resolved_name:
                raise ValueError("TransitEvent invariant failed: relation target_name must match computation truth")
            if self.relation.basis.value != self.computation_truth.target_truth.resolved_kind:
                raise ValueError("TransitEvent invariant failed: relation basis must match computation truth")
        if self.classification is not None and self.relation is not None:
            if self.relation.basis.value != self.classification.target.target_kind.value:
                raise ValueError("TransitEvent invariant failed: relation basis must match classification target kind")

    @property
    def datetime_utc(self) -> datetime:
        return datetime_from_jd(self.jd_ut)

    @property
    def calendar_utc(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(self.jd_ut)

    def __repr__(self) -> str:
        return (f"{self.body} at {self.longitude:.4f}°  "
                f"{format_jd_utc(self.jd_ut)}  "
                f"({self.direction})")

    @property
    def target_kind(self) -> TransitTargetKind | None:
        """Return the typed target kind when classification is available."""

        if self.classification is not None:
            return self.classification.target.target_kind
        if self.computation_truth is not None:
            return TransitTargetKind(self.computation_truth.target_truth.resolved_kind)
        return None

    @property
    def search_kind(self) -> TransitSearchKind | None:
        """Return the typed search kind when classification is available."""

        if self.classification is not None:
            return self.classification.search.search_kind
        return None

    @property
    def wrapper_kind(self) -> TransitWrapperKind | None:
        """Return the typed wrapper kind when classification is available."""

        if self.classification is not None:
            return self.classification.search.wrapper_kind
        return None

    @property
    def uses_dynamic_target(self) -> bool | None:
        """Return whether the preserved target was dynamically resolved."""

        if self.classification is not None:
            return self.classification.search.uses_dynamic_target
        return None


@dataclass(slots=True)
class IngressEvent:
    """
    RITE: The Ingress Event Vessel

    THEOREM: Governs the storage of a single moment when a body enters a new
    zodiac sign.

    RITE OF PURPOSE:
        IngressEvent is the authoritative data vessel for a single sign-ingress
        event produced by the Transit Engine. It captures the body name, the sign
        entered, the Julian Day of ingress, and the direction of motion. Without it,
        callers would receive unstructured tuples with no field-level guarantees. It
        exists to give every higher-level consumer a single, named, mutable record
        of each sign ingress.

    LAW OF OPERATION:
        Responsibilities:
            - Store a single sign ingress as named, typed fields
            - Expose the sign's boundary longitude via sign_longitude property
            - Expose UTC datetime and CalendarDateTime views via read-only properties
            - Serve as the return type of find_ingresses()
        Non-responsibilities:
            - Computing ingress times (delegates to find_ingresses)
            - Resolving body positions (delegates to planets)
            - Converting Julian Days to display strings (delegates to julian)
        Dependencies:
            - Populated by find_ingresses()
            - sign_longitude derives from SIGNS index
        Structural invariants:
            - sign is a valid member of SIGNS
            - direction is 'direct' or 'retrograde'
        Behavioral invariants:
            - All consumers treat IngressEvent fields as read-only after construction

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.transits.IngressEvent",
      "risk": "high",
      "api": {
        "frozen": ["body", "sign", "jd_ut", "direction"],
        "internal": ["sign_longitude", "datetime_utc", "calendar_utc"]
      },
      "state": {"mutable": true, "owners": ["find_ingresses"]},
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
    body:        str
    sign:        str          # sign being entered
    jd_ut:       float
    direction:   str          # 'direct' or 'retrograde'
    computation_truth: IngressComputationTruth | None = None
    classification: IngressComputationClassification | None = None
    relation: TransitRelation | None = None

    def __post_init__(self) -> None:
        if not self.body:
            raise ValueError("IngressEvent invariant failed: body must not be empty")
        if self.sign not in SIGNS:
            raise ValueError("IngressEvent invariant failed: sign must be valid")
        if not math.isfinite(self.jd_ut):
            raise ValueError("IngressEvent invariant failed: jd_ut must be finite")
        if self.direction not in {"direct", "retrograde"}:
            raise ValueError("IngressEvent invariant failed: direction must be supported")
        if self.computation_truth is not None:
            if self.computation_truth.body != self.body:
                raise ValueError("IngressEvent invariant failed: computation_truth body must match body")
            if self.computation_truth.sign != self.sign:
                raise ValueError("IngressEvent invariant failed: computation_truth sign must match sign")
            if self.computation_truth.search_truth.crossing_jd_ut != self.jd_ut:
                raise ValueError("IngressEvent invariant failed: computation_truth crossing_jd_ut must match jd_ut")
        if self.classification is not None:
            if self.classification.body != self.body:
                raise ValueError("IngressEvent invariant failed: classification body must match body")
            if self.classification.sign != self.sign:
                raise ValueError("IngressEvent invariant failed: classification sign must match sign")
        if self.relation is not None:
            if self.relation.source_body != self.body:
                raise ValueError("IngressEvent invariant failed: relation source_body must match body")
            if self.relation.relation_kind is not TransitRelationKind.SIGN_INGRESS:
                raise ValueError("IngressEvent invariant failed: relation_kind must be sign_ingress")
            if self.relation.target_name != self.sign:
                raise ValueError("IngressEvent invariant failed: relation target_name must match sign")
            if self.relation.target_longitude != self.sign_longitude:
                raise ValueError("IngressEvent invariant failed: relation target_longitude must match sign_longitude")
        if self.computation_truth is not None and self.classification is not None:
            if self.classification.search.search_kind is not TransitSearchKind.SIGN_INGRESS:
                raise ValueError("IngressEvent invariant failed: classification search_kind must be sign_ingress")
        if self.computation_truth is not None and self.relation is not None:
            if self.relation.target_longitude != self.computation_truth.boundary_longitude:
                raise ValueError("IngressEvent invariant failed: relation target_longitude must match computation truth")
        if self.classification is not None and self.relation is not None:
            if self.relation.basis is not TransitRelationBasis.SIGN_BOUNDARY:
                raise ValueError("IngressEvent invariant failed: relation basis must be sign_boundary")

    @property
    def sign_longitude(self) -> float:
        idx = SIGNS.index(self.sign)
        return float(idx * 30)

    @property
    def datetime_utc(self) -> datetime:
        return datetime_from_jd(self.jd_ut)

    @property
    def calendar_utc(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(self.jd_ut)

    def __repr__(self) -> str:
        arrow = "→" if self.direction == "direct" else "←"
        return (f"{self.body} {arrow} {self.sign}  "
                f"{format_jd_utc(self.jd_ut)}")

    @property
    def search_kind(self) -> TransitSearchKind | None:
        """Return the typed search kind when classification is available."""

        if self.classification is not None:
            return self.classification.search.search_kind
        return None

    @property
    def wrapper_kind(self) -> TransitWrapperKind | None:
        """Return the typed wrapper kind when classification is available."""

        if self.classification is not None:
            return self.classification.search.wrapper_kind
        return None


# ---------------------------------------------------------------------------
# Low-level longitude sampler
# ---------------------------------------------------------------------------

def _resolve_longitude(spec: str | float, jd: float, reader: SpkReader) -> float:
    """
    Resolve a transit source/target specification to a tropical longitude.

    Supports:
    - numeric longitudes
    - planetary body names
    - named asteroids in ASTEROID_NAIF
    - True Node / Mean Node / Lilith / True Lilith
    - named fixed stars resolvable by fixed_star_at()
    """
    return _resolve_longitude_truth(spec, jd, reader).longitude


def _resolve_longitude_truth(
    spec: str | float,
    jd: float,
    reader: SpkReader,
) -> LongitudeResolutionTruth:
    """Resolve a target specification and preserve how it was obtained."""

    if isinstance(spec, (int, float)):
        return LongitudeResolutionTruth(
            requested_spec=spec,
            resolved_kind="numeric_longitude",
            resolved_name=f"{float(spec) % 360.0:.12f}",
            jd_ut=jd,
            longitude=float(spec) % 360.0,
        )

    name = str(spec).strip()

    try:
        return LongitudeResolutionTruth(
            requested_spec=spec,
            resolved_kind="planet",
            resolved_name=name,
            jd_ut=jd,
            longitude=planet_at(name, jd, reader=reader).longitude,
        )
    except Exception:
        pass

    if name == Body.TRUE_NODE:
        return LongitudeResolutionTruth(spec, "node", name, jd, true_node(jd, reader=reader).longitude)
    if name == Body.MEAN_NODE:
        return LongitudeResolutionTruth(spec, "node", name, jd, mean_node(jd).longitude)
    if name == Body.LILITH:
        return LongitudeResolutionTruth(spec, "lilith", name, jd, mean_lilith(jd).longitude)
    if name == Body.TRUE_LILITH:
        return LongitudeResolutionTruth(spec, "lilith", name, jd, true_lilith(jd, reader=reader).longitude)

    if name in ASTEROID_NAIF or any(key.lower() == name.lower() for key in ASTEROID_NAIF):
        return LongitudeResolutionTruth(
            requested_spec=spec,
            resolved_kind="asteroid",
            resolved_name=name,
            jd_ut=jd,
            longitude=asteroid_at(name, jd, de441_reader=reader).longitude,
        )

    return LongitudeResolutionTruth(
        requested_spec=spec,
        resolved_kind="fixed_star",
        resolved_name=name,
        jd_ut=jd,
        longitude=fixed_star_at(name, ut_to_tt(jd)).longitude,
    )


def _lon(body: str | float, jd: float, reader: SpkReader) -> float:
    return _resolve_longitude(body, jd, reader)


def _signed_diff(a: float, b: float) -> float:
    """Signed angular difference a − b, normalised to (−180, +180]."""
    return (a - b + 180.0) % 360.0 - 180.0


def _validate_policy(policy: TransitComputationPolicy | None) -> TransitComputationPolicy:
    """Validate and normalize transit computation policy."""

    if policy is None:
        return TransitComputationPolicy()
    if not isinstance(policy, TransitComputationPolicy):
        raise ValueError("Transit computation policy must be a TransitComputationPolicy")

    if policy.transit.step_days_override is not None and policy.transit.step_days_override <= 0:
        raise ValueError("Transit search policy step_days_override must be positive")
    if policy.transit.solver_tolerance_days <= 0:
        raise ValueError("Transit search policy solver_tolerance_days must be positive")

    if policy.ingress.step_days_override is not None and policy.ingress.step_days_override <= 0:
        raise ValueError("Ingress search policy step_days_override must be positive")
    if policy.ingress.solver_tolerance_days <= 0:
        raise ValueError("Ingress search policy solver_tolerance_days must be positive")

    if policy.returns.step_days_override is not None and policy.returns.step_days_override <= 0:
        raise ValueError("Return search policy step_days_override must be positive")
    if policy.returns.default_max_days is not None and policy.returns.default_max_days <= 0:
        raise ValueError("Return search policy default_max_days must be positive")
    seen_return_bodies: set[str] = set()
    for body, max_days in policy.returns.per_body_max_days:
        if not body:
            raise ValueError("Return search policy per_body_max_days body must not be empty")
        if body in seen_return_bodies:
            raise ValueError("Return search policy per_body_max_days must not contain duplicate bodies")
        if max_days <= 0:
            raise ValueError("Return search policy per_body_max_days values must be positive")
        seen_return_bodies.add(body)

    if policy.syzygy.scan_step_days <= 0:
        raise ValueError("Syzygy search policy scan_step_days must be positive")
    if policy.syzygy.solver_tolerance_days <= 0:
        raise ValueError("Syzygy search policy solver_tolerance_days must be positive")
    if policy.syzygy.max_synodic_multiple <= 0:
        raise ValueError("Syzygy search policy max_synodic_multiple must be positive")

    return policy


def _return_window_days(body: str, policy: TransitComputationPolicy) -> float:
    """Resolve the doctrinal return-search window for one body."""

    per_body = dict(policy.returns.per_body_max_days)
    if body in per_body:
        return per_body[body]
    if policy.returns.default_max_days is not None:
        return policy.returns.default_max_days
    return _RETURN_SEARCH_DAYS.get(body, 400.0)


# ---------------------------------------------------------------------------
# Binary search: find exact crossing of a target longitude
# ---------------------------------------------------------------------------

def _find_crossing(
    body: str,
    target: str | float,
    jd_lo: float,
    jd_hi: float,
    reader: SpkReader,
    tol_days: float = 1e-6,   # ~0.086 seconds
) -> tuple[float, CrossingSearchTruth]:
    """
    Bisect to find when body crosses `target` longitude in [jd_lo, jd_hi].
    Assumes there is exactly one crossing in the interval.
    Returns jd of crossing plus preserved search truth.
    """
    search_start = jd_lo
    search_end = jd_hi
    sign_lo = _signed_diff(_lon(body, jd_lo, reader), _lon(target, jd_lo, reader))
    for _ in range(60):
        jd_mid = (jd_lo + jd_hi) / 2
        if jd_hi - jd_lo < tol_days:
            break
        sign_mid = _signed_diff(_lon(body, jd_mid, reader), _lon(target, jd_mid, reader))
        if sign_lo * sign_mid <= 0:
            jd_hi = jd_mid
        else:
            jd_lo = jd_mid
            sign_lo = sign_mid
    crossing_jd = (jd_lo + jd_hi) / 2
    return crossing_jd, CrossingSearchTruth(
        search_start_jd_ut=search_start,
        search_end_jd_ut=search_end,
        step_days=search_end - search_start,
        bracket_start_jd_ut=jd_lo,
        bracket_end_jd_ut=jd_hi,
        crossing_jd_ut=crossing_jd,
        solver_tolerance_days=tol_days,
    )


# ---------------------------------------------------------------------------
# Public: find next/previous transit of a body to a longitude
# ---------------------------------------------------------------------------

def next_transit(
    body: str,
    target_lon: str | float,
    jd_start: float,
    direction: str = "either",
    max_days: float = 400.0,
    step_days: float | None = None,
    reader: SpkReader | None = None,
    policy: TransitComputationPolicy | None = None,
) -> TransitEvent | None:
    """
    Find the next time *body* passes through *target_lon*.

    Parameters
    ----------
    body        : Body.* constant
    target_lon  : target ecliptic longitude (0–360°)
    jd_start    : search start Julian Day (UT)
    direction   : 'direct', 'retrograde', or 'either'
    max_days    : maximum search window in days
    step_days   : step size for scanning (auto-selected if None)
    reader      : SpkReader instance

    Returns
    -------
    TransitEvent, or None if not found within max_days
    """
    if reader is None:
        reader = get_reader()
    policy = _validate_policy(policy)

    # Auto step: fast movers need a small step; slow movers can use larger
    if step_days is None:
        step_days = policy.transit.step_days_override or _auto_step(body)

    jd = jd_start
    lon_prev = _lon(body, jd, reader)

    while jd < jd_start + max_days:
        jd_next = jd + step_days
        lon_next = _lon(body, jd_next, reader)

        # Check for crossing: signed difference changes sign
        target_prev = _lon(target_lon, jd, reader)
        target_next = _lon(target_lon, jd_next, reader)
        diff_prev = _signed_diff(lon_prev, target_prev)
        diff_next = _signed_diff(lon_next, target_next)

        if (diff_prev * diff_next < 0
                and abs(diff_prev) < 90.0 and abs(diff_next) < 90.0):
            jd_cross, search_truth = _find_crossing(
                body,
                target_lon,
                jd,
                jd_next,
                reader,
                tol_days=policy.transit.solver_tolerance_days,
            )
            # Determine direction from speed at crossing
            lon_before = _lon(body, jd_cross - 0.25, reader)
            lon_after  = _lon(body, jd_cross + 0.25, reader)
            speed = _signed_diff(lon_after, lon_before) / 0.5
            mov = "direct" if speed >= 0 else "retrograde"

            if direction == "either" or direction == mov:
                target_truth = _resolve_longitude_truth(target_lon, jd_cross, reader)
                computation_truth = TransitComputationTruth(
                    body=body,
                    requested_target=target_lon,
                    direction_filter=direction,
                    target_truth=target_truth,
                    search_truth=CrossingSearchTruth(
                        search_start_jd_ut=jd_start,
                        search_end_jd_ut=jd_start + max_days,
                        step_days=step_days,
                        bracket_start_jd_ut=search_truth.bracket_start_jd_ut,
                        bracket_end_jd_ut=search_truth.bracket_end_jd_ut,
                        crossing_jd_ut=search_truth.crossing_jd_ut,
                        solver_tolerance_days=search_truth.solver_tolerance_days,
                    ),
                )
                return TransitEvent(
                    body=body,
                    longitude=target_truth.longitude,
                    jd_ut=jd_cross,
                    direction=mov,
                    computation_truth=computation_truth,
                    classification=_classify_transit_computation_truth(
                        computation_truth,
                        wrapper_kind=TransitWrapperKind.DIRECT_TRANSIT,
                    ),
                    relation=_build_transit_relation(computation_truth),
                )

        jd = jd_next
        lon_prev = lon_next

    return None


def find_transits(
    body: str,
    target_lon: str | float,
    jd_start: float,
    jd_end: float,
    step_days: float | None = None,
    reader: SpkReader | None = None,
    policy: TransitComputationPolicy | None = None,
) -> list[TransitEvent]:
    """
    Find all transits of *body* to *target_lon* within a date range.

    Parameters
    ----------
    body        : Body.* constant
    target_lon  : target longitude (degrees)
    jd_start    : range start (JD UT)
    jd_end      : range end (JD UT)
    step_days   : scan step (auto if None)
    reader      : SpkReader instance

    Returns
    -------
    List of TransitEvent (chronological)
    """
    if reader is None:
        reader = get_reader()
    policy = _validate_policy(policy)
    if step_days is None:
        step_days = policy.transit.step_days_override or _auto_step(body)

    events: list[TransitEvent] = []
    jd = jd_start
    lon_prev = _lon(body, jd, reader)

    while jd < jd_end:
        jd_next = min(jd + step_days, jd_end)
        lon_next = _lon(body, jd_next, reader)

        target_prev = _lon(target_lon, jd, reader)
        target_next = _lon(target_lon, jd_next, reader)
        diff_prev = _signed_diff(lon_prev, target_prev)
        diff_next = _signed_diff(lon_next, target_next)

        if (diff_prev * diff_next < 0
                and abs(diff_prev) < 90.0 and abs(diff_next) < 90.0):
            jd_cross, search_truth = _find_crossing(
                body,
                target_lon,
                jd,
                jd_next,
                reader,
                tol_days=policy.transit.solver_tolerance_days,
            )
            lon_before = _lon(body, jd_cross - 0.25, reader)
            lon_after  = _lon(body, jd_cross + 0.25, reader)
            speed = _signed_diff(lon_after, lon_before) / 0.5
            mov = "direct" if speed >= 0 else "retrograde"
            target_truth = _resolve_longitude_truth(target_lon, jd_cross, reader)
            computation_truth = TransitComputationTruth(
                body=body,
                requested_target=target_lon,
                direction_filter="either",
                target_truth=target_truth,
                search_truth=CrossingSearchTruth(
                    search_start_jd_ut=jd_start,
                    search_end_jd_ut=jd_end,
                    step_days=step_days,
                    bracket_start_jd_ut=search_truth.bracket_start_jd_ut,
                    bracket_end_jd_ut=search_truth.bracket_end_jd_ut,
                    crossing_jd_ut=search_truth.crossing_jd_ut,
                    solver_tolerance_days=search_truth.solver_tolerance_days,
                ),
            )
            events.append(TransitEvent(
                body=body,
                longitude=target_truth.longitude,
                jd_ut=jd_cross,
                direction=mov,
                computation_truth=computation_truth,
                classification=_classify_transit_computation_truth(
                    computation_truth,
                    wrapper_kind=TransitWrapperKind.TRANSIT_RANGE,
                ),
                relation=_build_transit_relation(computation_truth),
            ))

        jd = jd_next
        lon_prev = lon_next

    return events


# ---------------------------------------------------------------------------
# Public: sign ingresses
# ---------------------------------------------------------------------------

def find_ingresses(
    body: str,
    jd_start: float,
    jd_end: float,
    step_days: float | None = None,
    reader: SpkReader | None = None,
    policy: TransitComputationPolicy | None = None,
) -> list[IngressEvent]:
    """
    Find all sign ingresses of *body* within a date range.

    Returns
    -------
    List of IngressEvent (chronological)
    """
    if reader is None:
        reader = get_reader()
    policy = _validate_policy(policy)
    if step_days is None:
        step_days = policy.ingress.step_days_override or _auto_step(body)

    events: list[IngressEvent] = []
    jd = jd_start

    # Find all 30° boundary crossings (0, 30, 60, ..., 330)
    sign_boundaries = [i * 30.0 for i in range(12)]
    lon_prev = _lon(body, jd, reader)

    while jd < jd_end:
        jd_next = min(jd + step_days, jd_end)
        lon_next = _lon(body, jd_next, reader)

        for boundary in sign_boundaries:
            diff_prev = _signed_diff(lon_prev, boundary)
            diff_next = _signed_diff(lon_next, boundary)
            if (diff_prev * diff_next < 0
                and abs(diff_prev) < 90.0 and abs(diff_next) < 90.0):
                jd_cross, search_truth = _find_crossing(
                    body,
                    boundary,
                    jd,
                    jd_next,
                    reader,
                    tol_days=policy.ingress.solver_tolerance_days,
                )
                lon_before = _lon(body, jd_cross - 0.25, reader)
                lon_after  = _lon(body, jd_cross + 0.25, reader)
                speed = _signed_diff(lon_after, lon_before) / 0.5
                mov = "direct" if speed >= 0 else "retrograde"
                # Which sign is being entered?
                sign_idx = int(boundary / 30) % 12
                computation_truth = IngressComputationTruth(
                    body=body,
                    sign=SIGNS[sign_idx],
                    boundary_longitude=boundary,
                    search_truth=CrossingSearchTruth(
                        search_start_jd_ut=jd_start,
                        search_end_jd_ut=jd_end,
                        step_days=step_days,
                        bracket_start_jd_ut=search_truth.bracket_start_jd_ut,
                        bracket_end_jd_ut=search_truth.bracket_end_jd_ut,
                        crossing_jd_ut=search_truth.crossing_jd_ut,
                        solver_tolerance_days=search_truth.solver_tolerance_days,
                    ),
                )
                events.append(IngressEvent(
                    body=body,
                    sign=SIGNS[sign_idx],
                    jd_ut=jd_cross,
                    direction=mov,
                    computation_truth=computation_truth,
                    classification=_classify_ingress_computation_truth(computation_truth),
                    relation=_build_ingress_relation(computation_truth),
                ))

        jd = jd_next
        lon_prev = lon_next

    events.sort(key=lambda e: e.jd_ut)
    return events


# ---------------------------------------------------------------------------
# Public: solar / lunar / generic planet returns
# ---------------------------------------------------------------------------

# Practical geocentric return-search envelopes in days.
# These are intentionally wider than orbital or synodic periods because
# geocentric longitude returns can be delayed by retrograde loops and by the
# Earth's own yearly motion.
_RETURN_SEARCH_DAYS: dict[str, float] = {
    Body.SUN:     370.0,
    Body.MOON:    35.0,
    Body.MERCURY: 400.0,
    Body.VENUS:   650.0,
    Body.MARS:    850.0,
    Body.JUPITER: 500.0,
    Body.SATURN:  450.0,
    Body.URANUS:  430.0,
    Body.NEPTUNE: 430.0,
    Body.PLUTO:   430.0,
}


def planet_return(
    body: str,
    natal_lon: float,
    jd_start: float,
    direction: str = "direct",
    reader: SpkReader | None = None,
    policy: TransitComputationPolicy | None = None,
) -> float:
    """
    Find the Julian Day (UT) when *body* next returns to *natal_lon*.

    Works for any body recognised by the ephemeris engine.  The search window
    is set automatically from the body's approximate orbital period so that
    both fast bodies (Moon) and slow bodies (Saturn, Pluto) are handled
    without manual tuning.

    Parameters
    ----------
    body       : body name constant (e.g. Body.SUN, Body.VENUS, "Jupiter")
    natal_lon  : natal ecliptic longitude to return to (degrees, 0–360)
    jd_start   : start the search from this Julian Day (UT)
    direction  : 'direct' (default — next direct-motion return) or 'either'
                 to allow a retrograde return
    reader     : optional SpkReader (uses default ephemeris if None)

    Returns
    -------
    Julian Day (UT) of the next return

    Raises
    ------
    RuntimeError if no return is found within 1.5 × the orbital period
    """
    if reader is None:
        reader = get_reader()
    policy = _validate_policy(policy)

    max_days = _return_window_days(body, policy)
    step = policy.returns.step_days_override or _auto_step(body)

    event = next_transit(
        body, natal_lon, jd_start,
        direction=direction,
        max_days=max_days,
        step_days=step,
        reader=reader,
        policy=policy,
    )
    if event is None:
        raise RuntimeError(
            f"Return of {body} to {natal_lon:.4f}° not found within "
            f"{max_days:.0f} days of JD {jd_start:.2f}"
        )
    return event.jd_ut


def solar_return(
    natal_sun_lon: float,
    year: int,
    reader: SpkReader | None = None,
    policy: TransitComputationPolicy | None = None,
) -> float:
    """
    Find the Julian Day of the solar return for a given year.

    Parameters
    ----------
    natal_sun_lon : natal Sun longitude (degrees)
    year          : calendar year of the return
    reader        : SpkReader instance

    Returns
    -------
    Julian Day (UT) of the exact solar return
    """
    if reader is None:
        reader = get_reader()

    # Start searching ~10 days before the expected date derived from the
    # vernal equinox offset, then delegate to planet_return().
    jd_approx  = julian_day(year, 3, 10, 0.0)
    days_offset = (natal_sun_lon / 360.0) * 365.25
    jd_start   = jd_approx + days_offset - 10.0

    return planet_return(
        Body.SUN,
        natal_sun_lon,
        jd_start,
        direction="direct",
        reader=reader,
        policy=policy,
    )


def lunar_return(
    natal_moon_lon: float,
    jd_start: float,
    reader: SpkReader | None = None,
    policy: TransitComputationPolicy | None = None,
) -> float:
    """
    Find the next lunar return after jd_start.

    Parameters
    ----------
    natal_moon_lon : natal Moon longitude (degrees)
    jd_start       : search from this Julian Day (UT)

    Returns
    -------
    Julian Day (UT) of the next exact lunar return
    """
    if reader is None:
        reader = get_reader()

    return planet_return(
        Body.MOON,
        natal_moon_lon,
        jd_start,
        direction="direct",
        reader=reader,
        policy=policy,
    )


# ---------------------------------------------------------------------------
# Internal: auto-select scan step per body
# ---------------------------------------------------------------------------

def _auto_step(body: str) -> float:
    """Return a suitable scan step in days for the given body."""
    # Average daily motion (degrees/day) × safety factor
    # Step = max_motion_per_step = ~5–10°
    _STEPS = {
        Body.MOON:    0.25,    # 13°/day → step covers ~3°
        Body.SUN:     0.5,
        Body.MERCURY: 0.5,
        Body.VENUS:   0.5,
        Body.MARS:    1.0,
        Body.JUPITER: 5.0,
        Body.SATURN:  5.0,
        Body.URANUS:  10.0,
        Body.NEPTUNE: 10.0,
        Body.PLUTO:   15.0,
    }
    return _STEPS.get(body, 1.0)


# ---------------------------------------------------------------------------
# Syzygy: last New Moon / Full Moon before a date
# ---------------------------------------------------------------------------

def _sun_moon_elongation(jd: float, reader: SpkReader) -> float:
    """Signed elongation Moon − Sun, normalised to (−180, +180]."""
    sun  = _lon(Body.SUN,  jd, reader)
    moon = _lon(Body.MOON, jd, reader)
    return _signed_diff(moon, sun)


def _find_phase_crossing(
    target_elongation: float,
    jd_lo: float,
    jd_hi: float,
    reader: SpkReader,
    tol_days: float = 1e-6,
) -> float:
    """Bisect to find when Moon-Sun elongation equals target (0°=NM, 180°=FM)."""
    def diff(jd: float) -> float:
        return _signed_diff(_sun_moon_elongation(jd, reader), target_elongation)

    d_lo = diff(jd_lo)
    for _ in range(60):
        if jd_hi - jd_lo < tol_days:
            break
        jd_mid = (jd_lo + jd_hi) / 2
        d_mid  = diff(jd_mid)
        if d_lo * d_mid <= 0:
            jd_hi = jd_mid
        else:
            jd_lo = jd_mid
            d_lo  = d_mid
    return (jd_lo + jd_hi) / 2


def last_new_moon(
    jd: float,
    reader: SpkReader | None = None,
    policy: TransitComputationPolicy | None = None,
) -> float:
    """
    Find the most recent New Moon (Sun-Moon conjunction) before *jd*.

    Returns
    -------
    Julian Day (UT) of the New Moon.
    """
    if reader is None:
        reader = get_reader()
    policy = _validate_policy(policy)

    _SYNODIC = 29.53058868

    # Scan backwards in ~1-day steps; New Moon = elongation crosses 0
    jd_cur  = jd
    elong   = _sun_moon_elongation(jd_cur, reader)

    # Walk back through the current lunation to find the bracket
    for _ in range(60):
        jd_prev = jd_cur - policy.syzygy.scan_step_days
        elong_prev = _sun_moon_elongation(jd_prev, reader)

        # New Moon: elongation crosses from negative to positive (or near 0)
        if elong_prev * elong < 0 and abs(elong_prev) < 90.0 and abs(elong) < 90.0:
            # The crossing might be a New Moon (0°) or Full Moon (±180°)
            # New Moon: both values are near 0 (not near ±180)
            return _find_phase_crossing(
                0.0,
                jd_prev,
                jd_cur,
                reader,
                tol_days=policy.syzygy.solver_tolerance_days,
            )

        jd_cur = jd_prev
        elong  = elong_prev

        if jd - jd_cur > _SYNODIC * policy.syzygy.max_synodic_multiple:
            break

    raise RuntimeError("last_new_moon: no New Moon found in past synodic month")


def last_full_moon(
    jd: float,
    reader: SpkReader | None = None,
    policy: TransitComputationPolicy | None = None,
) -> float:
    """
    Find the most recent Full Moon (Sun-Moon opposition) before *jd*.

    Returns
    -------
    Julian Day (UT) of the Full Moon.
    """
    if reader is None:
        reader = get_reader()
    policy = _validate_policy(policy)

    _SYNODIC = 29.53058868

    jd_cur = jd
    elong  = _sun_moon_elongation(jd_cur, reader)

    for _ in range(60):
        jd_prev = jd_cur - policy.syzygy.scan_step_days
        elong_prev = _sun_moon_elongation(jd_prev, reader)

        # Full Moon: elongation crosses ±180 boundary
        # Rephrase: (elong - 180) changes sign while both values within 90° of ±180
        diff_cur  = _signed_diff(elong,      180.0)
        diff_prev = _signed_diff(elong_prev, 180.0)
        if diff_prev * diff_cur < 0 and abs(diff_prev) < 90.0 and abs(diff_cur) < 90.0:
            return _find_phase_crossing(
                180.0,
                jd_prev,
                jd_cur,
                reader,
                tol_days=policy.syzygy.solver_tolerance_days,
            )

        jd_cur = jd_prev
        elong  = elong_prev

        if jd - jd_cur > _SYNODIC * policy.syzygy.max_synodic_multiple:
            break

    raise RuntimeError("last_full_moon: no Full Moon found in past synodic month")


def prenatal_syzygy(
    jd: float,
    reader: SpkReader | None = None,
    policy: TransitComputationPolicy | None = None,
) -> tuple[float, str]:
    """
    Find the pre-natal syzygy: whichever of New Moon or Full Moon
    most recently preceded *jd*.

    Returns
    -------
    (jd_syzygy, phase) where phase is 'New Moon' or 'Full Moon'.
    """
    if reader is None:
        reader = get_reader()
    policy = _validate_policy(policy)

    jd_nm = last_new_moon(jd, reader, policy=policy)
    jd_fm = last_full_moon(jd, reader, policy=policy)
    if jd_nm >= jd_fm:
        return jd_nm, "New Moon"
    return jd_fm, "Full Moon"


def transit_relations(events: list[TransitEvent]) -> list[TransitRelation]:
    """Flatten explicit transit relations from detected transit events."""

    return [event.relation for event in events if event.relation is not None]


def ingress_relations(events: list[IngressEvent]) -> list[TransitRelation]:
    """Flatten explicit ingress relations from detected ingress events."""

    return [event.relation for event in events if event.relation is not None]
