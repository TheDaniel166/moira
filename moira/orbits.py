"""
Moira - orbits.py
Orbital Elements Public Layer

Purpose
-------
Provides typed public vessels and computation for center-relative osculating
orbital elements and next/previous apsidal passages.

Implemented doctrine
--------------------
1. Coordinate frame
   Heliocentric, J2000.0 ecliptic and equinox.

2. Element type
   Osculating elements recovered from the instantaneous heliocentric state
   vector at the requested epoch.

3. Public shape
    Raw float arrays are rejected. Public results are always
   returned as ``KeplerianElements`` or ``DistanceExtremes``.

4. Event search basis
   Apsidal passages are isolated, two-sided local extrema of the live
   center-relative distance curve.  TDB radial-velocity roots locate them;
   osculating elements supply only search scale and automatic bounds.

Validation basis
----------------
- ``orbital_elements_at(...)`` is validated against live JPL HORIZONS
  osculating elements across Mercury through Pluto.
- ``distance_extremes_at(...)`` is validated against JPL HORIZONS
  vector-derived heliocentric distance extrema across all validated planets.
- Focused synthetic tests cover singular cases such as circular/equatorial
  states and degenerate input vectors.

Public surface
--------------
    KeplerianElements    - typed vessel for Keplerian orbital elements
    ApsidalPassages      - typed, outcome-complete passage result and receipt
    DistanceExtremes     - legacy planet-only perihelion/aphelion vessel
    orbital_elements_at  - compute heliocentric Keplerian elements for a body at a JD
    apsidal_passages     - find next/previous center-relative local extrema
    distance_extremes_at - find nearest perihelion and aphelion from a given JD

Import-time side effects: None
"""

from __future__ import annotations

import hashlib
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from typing import Any, Sequence

from .constants import Body, KM_PER_AU
from ._ephemeris_gm import _OrbitalGravity
from ._ephemeris_time import _resolve_delta_t_for_ut1
from .julian import _tt_to_tdb_with_receipt
from ._orbital_errors import (
    OrbitalAmbiguousBodyError,
    OrbitalBodyNotFoundError,
    OrbitalBodyNotLoadedError,
    OrbitalBodyNotSupportedError,
    OrbitalCenterNotAllowedError,
    OrbitalCoverageError,
    OrbitalError,
    OrbitalFrameUnavailableError,
    OrbitalGravityModelError,
    OrbitalInputError,
    OrbitalKernelMissingError,
    OrbitalLegacyBodyNotAllowedError,
    OrbitalPassageUnavailableError,
    OrbitalSearchError,
    OrbitalSourceReceiptError,
    OrbitalStateDegenerateError,
    OrbitalTimeBasisError,
)
from ._orbital_frames import orbital_frame_transform, rotate_orbital_state
from ._orbital_state import (
    OrbitalBodyIdentity,
    OrbitalBodyKind,
    OrbitalStateLeg,
    OrbitalStateSource,
    _state_source,
    bind_orbital_state,
    lease_orbital_context,
    resolve_orbital_body,
)
from .spk_reader import (
    KernelReader,
    OutOfRangeError,
    SpkReader,
    _RouteEdge,
    _RoutedState,
)


__all__ = [
    "OrbitalCenter",
    "ApsidalDirection",
    "ApsidalPassageStatus",
    "OrbitalFrame",
    "OrbitShape",
    "OrbitalBodyKind",
    "UndefinedElementReason",
    "OrbitalBodyIdentity",
    "OrbitalStateSource",
    "UndefinedElement",
    "OrbitalGravity",
    "OrbitalFrameConstruction",
    "OrbitalTimeConversion",
    "OrbitalSingularityThresholds",
    "OsculatingElementsProvenance",
    "OsculatingElements",
    "ApsidalPassageOutcome",
    "ApsidalRouteScheduleEntry",
    "ApsidalSegmentUsage",
    "ApsidalSeamContinuity",
    "ApsidalPassagesProvenance",
    "ApsidalPassages",
    "KeplerianElements",
    "DistanceExtremes",
    "osculating_elements",
    "apsidal_passages",
    "orbital_elements_at",
    "distance_extremes_at",
    "OrbitalError",
    "OrbitalInputError",
    "OrbitalBodyNotFoundError",
    "OrbitalAmbiguousBodyError",
    "OrbitalBodyNotSupportedError",
    "OrbitalCenterNotAllowedError",
    "OrbitalFrameUnavailableError",
    "OrbitalLegacyBodyNotAllowedError",
    "OrbitalPassageUnavailableError",
    "OrbitalSearchError",
    "OrbitalBodyNotLoadedError",
    "OrbitalCoverageError",
    "OrbitalKernelMissingError",
    "OrbitalGravityModelError",
    "OrbitalTimeBasisError",
    "OrbitalSourceReceiptError",
    "OrbitalStateDegenerateError",
    "OrbitClassCode",
    "OrbitClassBoundaryMargin",
    "OrbitClassPredicate",
    "OrbitClassResult",
    "OrbitalErrorReceipt",
    "OrbitClassBatchItem",
    "OrbitClassBatchResult",
    "orbit_class",
    "orbit_classes_at",
]


class OrbitalCenter(str, Enum):
    """Admitted dynamical centers for Stage 1 osculating elements."""

    SUN = "SUN"
    EARTH = "EARTH"


class ApsidalDirection(str, Enum):
    """Direction in TDB from the inclusive passage-search start."""

    NEXT = "NEXT"
    PREVIOUS = "PREVIOUS"


class ApsidalPassageStatus(str, Enum):
    """Mutually exclusive outcome of one requested extremum kind."""

    FOUND = "FOUND"
    BEYOND_COVERAGE = "BEYOND_COVERAGE"
    NOT_IN_WINDOW = "NOT_IN_WINDOW"


class OrbitalFrame(str, Enum):
    """Admitted axes in which one inertial osculating state is expressed."""

    J2000_ECLIPTIC = "J2000_ECLIPTIC"
    MEAN_ECLIPTIC_OF_DATE = "MEAN_ECLIPTIC_OF_DATE"
    TRUE_ECLIPTIC_OF_DATE = "TRUE_ECLIPTIC_OF_DATE"


class OrbitShape(str, Enum):
    """Finite-precision conic branch selected from measured eccentricity."""

    ELLIPTIC = "ELLIPTIC"
    PARABOLIC = "PARABOLIC"
    HYPERBOLIC = "HYPERBOLIC"


class OrbitClassCode(str, Enum):
    """JPL SBDB small-body orbit classification code."""

    IEO = "IEO"
    ATE = "ATE"
    APO = "APO"
    AMO = "AMO"
    MCA = "MCA"
    IMB = "IMB"
    MBA = "MBA"
    OMB = "OMB"
    TJN = "TJN"
    AST = "AST"
    CEN = "CEN"
    TNO = "TNO"
    PAA = "PAA"
    HYA = "HYA"


class UndefinedElementReason(str, Enum):
    """Reason an osculating element has no defined numerical value."""

    EQUATORIAL = "EQUATORIAL"
    CIRCULAR = "CIRCULAR"
    PARABOLIC = "PARABOLIC"
    HYPERBOLIC = "HYPERBOLIC"


@dataclass(frozen=True, slots=True)
class UndefinedElement:
    """One absent element and every simultaneous geometric reason."""

    field: str
    reasons: tuple[UndefinedElementReason, ...]


@dataclass(frozen=True, slots=True)
class OrbitalGravity:
    """Public receipt for the two-body gravitational parameter."""

    rule: str
    gm_km3_s2: float
    component_naif_ids: tuple[int, ...]
    component_gm_km3_s2: tuple[float, ...]
    policy: str
    source_url: str
    retrieved_date: str
    source_sha256: str
    source_bytes: int
    planetary_ephemeris: str


@dataclass(frozen=True, slots=True)
class OrbitalFrameConstruction:
    """Exact frame matrix and router-branch receipt."""

    frame: OrbitalFrame
    routine: str
    router_branch: str
    precession_model: str | None
    obliquity_model: str
    nutation_model: str | None


@dataclass(frozen=True, slots=True)
class OrbitalTimeConversion:
    """UT1-to-TT-to-TDB policy and source receipt."""

    delta_t_policy: str
    delta_t_source_product: str
    delta_t_retarget_mode: str
    delta_t_correction_seconds: float
    identity_iterations: int
    tt_tdb_policy: str
    tt_tdb_version: str
    tt_tdb_source_url: str
    tt_tdb_source_sha256: str
    tt_tdb_source_bytes: int
    tt_tdb_iterations: int


@dataclass(frozen=True, slots=True)
class OrbitalSingularityThresholds:
    """Dimensionless branch and degeneracy thresholds used by extraction."""

    circular_e_tolerance: float
    equatorial_sin_i_tolerance: float
    parabolic_e_tolerance: float
    rectilinear_normalized_h_tolerance: float
    policy: str


@dataclass(frozen=True, slots=True)
class OsculatingElementsProvenance:
    """Complete source, gravity, frame, time, and singularity receipt."""

    state_source: OrbitalStateSource
    gravity: OrbitalGravity
    frame_construction: OrbitalFrameConstruction
    frame_model_interval_tt: tuple[float, float] | None
    time_conversion: OrbitalTimeConversion
    singularity_thresholds: OrbitalSingularityThresholds


@dataclass(frozen=True, slots=True)
class OsculatingElements:
    """Explicit shape-safe osculating elements for one resolved body state."""

    body: OrbitalBodyIdentity
    center: OrbitalCenter
    frame: OrbitalFrame
    jd_ut: float
    epoch_tt: float
    epoch_tdb: float
    delta_t_seconds: float
    tdb_minus_tt_seconds: float
    shape: OrbitShape
    semi_major_axis_au: float | None
    eccentricity: float
    pericenter_distance_au: float
    apocenter_distance_au: float | None
    inclination_deg: float
    lon_ascending_node_deg: float | None
    arg_pericenter_deg: float | None
    true_anomaly_deg: float | None
    mean_anomaly_deg: float | None
    mean_motion_deg_per_day: float | None
    orbital_period_days: float | None
    time_of_pericenter_tdb: float | None
    time_of_pericenter_tt: float | None
    lon_pericenter_deg: float | None
    arg_latitude_deg: float | None
    true_longitude_deg: float
    mean_longitude_deg: float | None
    pericenter_ecliptic_lon_deg: float | None
    pericenter_ecliptic_lat_deg: float | None
    undefined: tuple[UndefinedElement, ...]
    provenance: OsculatingElementsProvenance


@dataclass(frozen=True, slots=True)
class ApsidalPassageOutcome:
    """One pericenter or apocenter result with scale-explicit coordinates."""

    status: ApsidalPassageStatus
    epoch_tdb: float | None
    epoch_tt: float | None
    jd_ut: float | None
    distance_au: float | None
    coverage_edge_tdb: float | None
    detail: str


@dataclass(frozen=True, slots=True)
class ApsidalRouteScheduleEntry:
    """One frozen route valid on one exact closed TDB interval."""

    start_tdb: float
    end_tdb: float
    route_identity: str
    legs: tuple[OrbitalStateLeg, ...]


@dataclass(frozen=True, slots=True)
class ApsidalSegmentUsage:
    """One exact source segment and its state-evaluation count."""

    leg: OrbitalStateLeg
    evaluations: int


@dataclass(frozen=True, slots=True)
class ApsidalSeamContinuity:
    """Numerical witness used to admit or reject one touching route seam."""

    epoch_tdb: float
    left_route_identity: str
    right_route_identity: str
    position_residual_km: float
    velocity_residual_km_per_day: float
    position_tolerance_km: float
    velocity_tolerance_km_per_day: float
    admitted: bool
    detail: str


@dataclass(frozen=True, slots=True)
class ApsidalPassagesProvenance:
    """Complete algorithm, route, seam and evaluation receipt."""

    algorithm_version: str
    gravity: OrbitalGravity
    time_conversion: OrbitalTimeConversion
    state_source: OrbitalStateSource
    initial_period_fraction: float
    radial_timescale_fraction: float
    minimum_step_days: float
    maximum_step_days: float
    witness_root_tolerance_factor: float
    witness_minimum_step_fraction: float
    witness_motion_timescale_fraction: float
    witness_maximum_offset_days: float
    refinement_tolerance_days: float
    maximum_root_iterations: int
    evaluation_budget: int
    extremum_semantics: str
    search_window_source: str
    route_plan_identity: str
    route_schedule: tuple[ApsidalRouteScheduleEntry, ...]
    segment_usage: tuple[ApsidalSegmentUsage, ...]
    seam_continuity: tuple[ApsidalSeamContinuity, ...]
    searched_interval_tdb: tuple[float, float]
    total_evaluations: int


@dataclass(frozen=True, slots=True)
class ApsidalPassages:
    """Next or previous center-relative apsidal passages from one epoch."""

    body: OrbitalBodyIdentity
    center: OrbitalCenter
    direction: ApsidalDirection
    jd_ut: float
    start_epoch_tt: float
    start_epoch_tdb: float
    pericenter: ApsidalPassageOutcome
    apocenter: ApsidalPassageOutcome
    provenance: ApsidalPassagesProvenance


@dataclass(frozen=True, slots=True)
class OrbitClassBoundaryMargin:
    """Evaluated inequality margin for one orbital boundary condition."""

    parameter: str
    value: float
    operator: str
    boundary: float
    signed_difference: float
    unit: str


@dataclass(frozen=True, slots=True)
class OrbitClassPredicate:
    """Evaluated boundary conditions for one candidate orbit class."""

    code: OrbitClassCode
    conditions: tuple[OrbitClassBoundaryMargin, ...]
    matched: bool


@dataclass(frozen=True, slots=True)
class OrbitClassResult:
    """Deterministic SBDB-style osculating asteroid classification at an epoch."""

    body: OrbitalBodyIdentity
    epoch_tdb: float
    elements: OsculatingElements
    code: OrbitClassCode
    title: str
    classification_policy: str
    predicates: tuple[OrbitClassPredicate, ...]
    boundary_margins: tuple[OrbitClassBoundaryMargin, ...]


@dataclass(frozen=True, slots=True)
class OrbitalErrorReceipt:
    """Sanitized, allowlisted failure receipt for one batch item."""

    error_code: str
    message: str
    details: tuple[tuple[str, Any], ...]


@dataclass(frozen=True, slots=True)
class OrbitClassBatchItem:
    """One classified item or isolated error within a batch evaluation."""

    input_index: int
    input_body: str | int
    result: OrbitClassResult | None
    error: OrbitalErrorReceipt | None


@dataclass(frozen=True, slots=True)
class OrbitClassBatchResult:
    """Ordered collection of classified asteroid results and error receipts."""

    epoch_tdb: float
    items: tuple[OrbitClassBatchItem, ...]


# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------

# GM_sun from JPL: 1.32712440018e20 m³/s², converted to km³/day²
_GM_SUN_KM3_DAY2: float = 1.32712440018e11 * 86400.0 ** 2
_BODY_SYSTEM_GM_KM3_S2: dict[str, float] = {
    Body.MARS: 4.2828372299345596e4,
    Body.JUPITER: 1.2669488293600228e8,
    Body.SATURN: 3.7940577410058454e7,
    Body.URANUS: 5.7943061113633998e6,
    Body.NEPTUNE: 6.8322470499278503e6,
    Body.PLUTO: 6.9049510564781247e2,
}

# KM_PER_AU imported from moira.constants — IAU 2012 exact definition.

# IAU J2000.0 ecliptic obliquity (Seidelmann 1992 value used in DE441 frame)
_J2000_OBLIQUITY_RAD: float = math.radians(23.439291111)

# Stage 1 finite-precision classification policy.  Each threshold is
# dimensionless and deliberately independent from dimensional state scales.
PARABOLIC_E_TOL = 1.0e-10
CIRCULAR_E_TOL = 1.0e-10
EQUATORIAL_SIN_I_TOL = 1.0e-10
RECTILINEAR_NORMALIZED_H_TOL = 1.0e-10
_SINGULARITY_POLICY = "MOIRA_OSCULATING_ELEMENTS_STAGE1_V1"

# Stage 2 search policy.  These values are frozen together under one algorithm
# identity so a future numerical-policy change cannot masquerade as the same
# passage product.
APSIDAL_ALGORITHM_VERSION = "MOIRA_APSIDAL_PASSAGES_V1"
APSIDAL_ROOT_TOLERANCE_DAYS = 1.0e-8
APSIDAL_MAX_ROOT_ITERATIONS = 96
APSIDAL_EVALUATION_BUDGET = 20_000
APSIDAL_INITIAL_PERIOD_FRACTION = 1.0 / 256.0
APSIDAL_RADIAL_TIMESCALE_FRACTION = 1.0 / 20.0
APSIDAL_MINIMUM_STEP_DAYS = 0.05
APSIDAL_MAXIMUM_STEP_DAYS = 32.0
APSIDAL_WITNESS_ROOT_TOLERANCE_FACTOR = 8.0
APSIDAL_WITNESS_MINIMUM_STEP_FRACTION = 0.1
APSIDAL_WITNESS_MOTION_TIMESCALE_FRACTION = 1.0e-4
APSIDAL_WITNESS_MAXIMUM_OFFSET_DAYS = 1.0
APSIDAL_SEAM_POSITION_TOLERANCE_KM = 1.0e-3
APSIDAL_SEAM_VELOCITY_TOLERANCE_KM_PER_DAY = 1.0e-6
_APSIDAL_FLAT_RADIAL_TOLERANCE_KM_PER_DAY = 1.0e-12
_APSIDAL_MAX_ROUTE_ENTRIES = 256


@dataclass(frozen=True, slots=True)
class _ApsidalRouteEntry:
    """Route entry segment mapped to a JD(TDB) interval."""

    start_tdb: float
    end_tdb: float
    route: tuple[_RouteEdge, ...]
    public: ApsidalRouteScheduleEntry


@dataclass(frozen=True, slots=True)
class _ApsidalRoutePlan:
    """Apsidal route schedule across a continuity plan."""

    entries: tuple[_ApsidalRouteEntry, ...]
    seams: tuple[ApsidalSeamContinuity, ...]
    identity: str
    lower_boundary_detail: str
    upper_boundary_detail: str

    @property
    def start_tdb(self) -> float:
        return self.entries[0].start_tdb

    @property
    def end_tdb(self) -> float:
        return self.entries[-1].end_tdb

    def entry_at(self, epoch_tdb: float) -> _ApsidalRouteEntry:
        for entry in self.entries:
            if entry.start_tdb <= epoch_tdb <= entry.end_tdb:
                return entry
        raise OutOfRangeError(
            f"frozen apsidal route plan does not cover JD(TDB) {epoch_tdb}",
            out_of_range_times=True,
        )


@dataclass(frozen=True, slots=True)
class _ApsidalSample:
    """Discrete radial sample along an apsidal route."""

    epoch_tdb: float
    distance_km: float
    radial_velocity_km_per_day: float
    speed_km_per_day: float
    route_identity: str


def _vector_norm(vector: tuple[float, float, float]) -> float:
    return math.sqrt(math.fsum(component * component for component in vector))


def _closed_interval_intersection(
    left: tuple[tuple[float, float], ...],
    right: tuple[tuple[float, float], ...],
) -> tuple[tuple[float, float], ...]:
    intersections: list[tuple[float, float]] = []
    for left_start, left_end in left:
        for right_start, right_end in right:
            start = max(left_start, right_start)
            end = min(left_end, right_end)
            if start <= end:
                intersections.append((start, end))
    intersections.sort()
    merged: list[tuple[float, float]] = []
    for start, end in intersections:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((float(start), float(end)))
    return tuple(merged)


def _route_intervals_tdb(
    route: tuple[_RouteEdge, ...],
) -> tuple[tuple[float, float], ...]:
    common: tuple[tuple[float, float], ...] | None = None
    for edge in route:
        getter = getattr(edge.reader, "coverage_intervals_tdb", None)
        if not callable(getter):
            return ()
        intervals = tuple(
            (float(start), float(end))
            for start, end in getter(edge.source_center, edge.source_target)
        )
        common = (
            intervals
            if common is None
            else _closed_interval_intersection(common, intervals)
        )
    return () if common is None else common


def _interval_containing(
    intervals: tuple[tuple[float, float], ...],
    epoch_tdb: float,
) -> tuple[float, float] | None:
    return next(
        (
            (start, end)
            for start, end in intervals
            if start <= epoch_tdb <= end
        ),
        None,
    )


def _route_identity(route: tuple[_RouteEdge, ...]) -> str:
    material: list[dict[str, object]] = []
    for edge in route:
        source = getattr(edge.reader, "_source_identity", None)
        material.append(
            {
                "start": edge.start,
                "end": edge.end,
                "source_center": edge.source_center,
                "source_target": edge.source_target,
                "sign": edge.sign,
                "pool_index": edge.pool_index,
                "source_label": getattr(source, "label", None),
                "source_sha256": getattr(source, "sha256", None),
                "source_bytes": getattr(source, "byte_length", None),
            }
        )
    encoded = json.dumps(
        material, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _route_entry(
    route: tuple[_RouteEdge, ...],
    interval: tuple[float, float],
    state: _RoutedState,
) -> _ApsidalRouteEntry:
    identity = _route_identity(route)
    source = _state_source(state)
    return _ApsidalRouteEntry(
        start_tdb=float(interval[0]),
        end_tdb=float(interval[1]),
        route=route,
        public=ApsidalRouteScheduleEntry(
            start_tdb=float(interval[0]),
            end_tdb=float(interval[1]),
            route_identity=identity,
            legs=source.legs,
        ),
    )


class _ApsidalEvaluationLedger:
    """
    RITE: The Apsidal Evaluation Ledger.

    THEOREM: Tracks evaluation counts and segment utilization receipts
    during numerical apsidal extrema searches under strict budget bounds.

    RITE OF PURPOSE:
        _ApsidalEvaluationLedger bounds ephemeris evaluation budgets and
        records exact orbital state segment utilization across route evaluations
        and discrete samples, preventing runaway root-finding loops.

    LAW OF OPERATION:
        Responsibilities:
            - Bound total orbital evaluations against APSIDAL_EVALUATION_BUDGET.
            - Record segment-use and epoch boundaries for evaluated routed states.
            - Provide deterministic state sampling for apsidal plans.
        Non-responsibilities:
            - Does not construct route graphs or resolve body ephemerides directly.
            - Does not formulate root-finding brackets.
        Dependencies:
            - Routing pool context and routed states.
        Structural invariants:
            - total <= APSIDAL_EVALUATION_BUDGET.
        Failure behavior:
            - Raises OrbitalSearchError when budget is exhausted.

    Canon: None (ephemeris evaluation accounting helper).

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.orbits._ApsidalEvaluationLedger",
      "risk": "medium",
      "api": {
        "frozen": ["observe", "evaluate_route", "sample", "sample_entry"],
        "internal": ["context", "total", "minimum_epoch_tdb", "maximum_epoch_tdb", "search_minimum_epoch_tdb", "search_maximum_epoch_tdb", "_usage", "radial_samples"]
      },
      "state": {
        "mutable": true,
        "owners": ["_ApsidalEvaluationLedger"]
      },
      "effects": {
        "signals_emitted": [],
        "io": []
      },
      "concurrency": {
        "thread": "pure_computation",
        "cross_thread_calls": "safe_read_only"
      },
      "failures": {
        "policy": "raise"
      },
      "succession": {
        "stance": "terminal"
      },
      "agent": {
        "autofix": "allowed",
        "requires_human_for": ["api_change"]
      }
    }
    [/MACHINE_CONTRACT]
    """

    def __init__(self, context) -> None:
        self.context = context
        self.total = 0
        self.minimum_epoch_tdb = math.inf
        self.maximum_epoch_tdb = -math.inf
        self.search_minimum_epoch_tdb = math.inf
        self.search_maximum_epoch_tdb = -math.inf
        self._usage: dict[OrbitalStateLeg, int] = defaultdict(int)
        self.radial_samples: list[float] = []

    def observe(self, state: _RoutedState) -> None:
        self.total += 1
        self.minimum_epoch_tdb = min(self.minimum_epoch_tdb, state.epoch_tdb)
        self.maximum_epoch_tdb = max(self.maximum_epoch_tdb, state.epoch_tdb)
        for leg in _state_source(state).legs:
            self._usage[leg] += 1

    def evaluate_route(
        self,
        route: tuple[_RouteEdge, ...],
        epoch_tdb: float,
    ) -> _RoutedState:
        if self.total >= APSIDAL_EVALUATION_BUDGET:
            raise OrbitalSearchError(
                None,
                0,
                self.total,
                APSIDAL_ROOT_TOLERANCE_DAYS,
                None,
                APSIDAL_ALGORITHM_VERSION,
            )
        state = self.context.pool._evaluate_route_tdb(
            route,
            epoch_tdb,
            snapshot=self.context.snapshot,
        )
        self.observe(state)
        return state

    def sample(
        self,
        plan: _ApsidalRoutePlan,
        epoch_tdb: float,
    ) -> _ApsidalSample:
        entry = plan.entry_at(epoch_tdb)
        return self.sample_entry(entry, epoch_tdb)

    def sample_entry(
        self,
        entry: _ApsidalRouteEntry,
        epoch_tdb: float,
    ) -> _ApsidalSample:
        state = self.evaluate_route(entry.route, epoch_tdb)
        self.search_minimum_epoch_tdb = min(
            self.search_minimum_epoch_tdb, epoch_tdb
        )
        self.search_maximum_epoch_tdb = max(
            self.search_maximum_epoch_tdb, epoch_tdb
        )
        distance = _vector_norm(state.position_km)
        speed = _vector_norm(state.velocity_km_per_day)
        if distance == 0.0:
            raise OrbitalStateDegenerateError(
                "ZERO_POSITION",
                self.context.body.name,
                epoch_tdb,
                distance,
                speed,
                0.0,
                RECTILINEAR_NORMALIZED_H_TOL,
            )
        radial = _dot3(state.position_km, state.velocity_km_per_day) / distance
        self.radial_samples.append(radial)
        return _ApsidalSample(
            epoch_tdb=float(epoch_tdb),
            distance_km=distance,
            radial_velocity_km_per_day=radial,
            speed_km_per_day=speed,
            route_identity=entry.public.route_identity,
        )

    def usages(self) -> tuple[ApsidalSegmentUsage, ...]:
        ordered = sorted(
            self._usage.items(),
            key=lambda item: (
                item[0].pool_index,
                item[0].kernel_sha256,
                item[0].center_naif_id,
                item[0].target_naif_id,
                item[0].coverage_start_tdb,
                item[0].coverage_end_tdb,
                item[0].traversal_sign,
            ),
        )
        return tuple(
            ApsidalSegmentUsage(leg=leg, evaluations=count)
            for leg, count in ordered
        )


def _state_residuals(
    left: _RoutedState,
    right: _RoutedState,
) -> tuple[float, float]:
    position = _vector_norm(
        tuple(a - b for a, b in zip(left.position_km, right.position_km))
    )
    velocity = _vector_norm(
        tuple(
            a - b
            for a, b in zip(
                left.velocity_km_per_day, right.velocity_km_per_day
            )
        )
    )
    return position, velocity


def _has_route_beyond(
    context,
    boundary_tdb: float,
    sign: int,
) -> bool:
    """Return whether the frozen snapshot resumes after a coverage gap."""

    candidates: set[float] = set()
    for reader in context.snapshot.readers:
        pairs = getattr(reader, "_coverage_pairs_tdb", None)
        getter = getattr(reader, "coverage_intervals_tdb", None)
        if not callable(pairs) or not callable(getter):
            continue
        for center, target in pairs():
            for start, end in getter(center, target):
                if sign > 0 and end > boundary_tdb:
                    candidates.add(max(float(start), math.nextafter(boundary_tdb, math.inf)))
                elif sign < 0 and start < boundary_tdb:
                    candidates.add(min(float(end), math.nextafter(boundary_tdb, -math.inf)))
    ordered = sorted(candidates, reverse=sign < 0)
    for candidate in ordered:
        if sign * (candidate - boundary_tdb) <= 0.0:
            continue
        route = context.pool._find_route_tdb(
            context.snapshot,
            context.center_naif_id,
            context.body.naif_id,
            candidate,
        )
        if route is not None:
            return True
    return False


def _build_apsidal_route_plan(context) -> tuple[
    _ApsidalRoutePlan, _ApsidalEvaluationLedger
]:
    """Freeze the exact contiguous route schedule containing the start."""

    ledger = _ApsidalEvaluationLedger(context)
    ledger.observe(context.initial_state)
    interval = _interval_containing(
        _route_intervals_tdb(context.initial_route),
        context.time.epoch_tdb,
    )
    if interval is None:
        raise OrbitalCoverageError(
            context.body.name,
            context.body.naif_id,
            context.time.epoch_tdb,
            (),
        )

    entries: list[_ApsidalRouteEntry] = [
        _route_entry(context.initial_route, interval, context.initial_state)
    ]
    seams: list[ApsidalSeamContinuity] = []
    lower_detail = "EPHEMERIS_EDGE"
    upper_detail = "EPHEMERIS_EDGE"

    def extend(sign: int) -> str:
        nonlocal entries
        for _ in range(_APSIDAL_MAX_ROUTE_ENTRIES):
            current = entries[-1] if sign > 0 else entries[0]
            boundary = current.end_tdb if sign > 0 else current.start_tdb
            if not math.isfinite(boundary):
                return "EPHEMERIS_EDGE"
            probe = math.nextafter(
                boundary, math.inf if sign > 0 else -math.inf
            )
            next_route = context.pool._find_route_tdb(
                context.snapshot,
                context.center_naif_id,
                context.body.naif_id,
                probe,
            )
            if next_route is None:
                return (
                    "UNADMITTED_SOURCE_SEAM"
                    if _has_route_beyond(context, boundary, sign)
                    else "EPHEMERIS_EDGE"
                )
            next_interval = _interval_containing(
                _route_intervals_tdb(next_route), probe
            )
            if next_interval is None:
                return "UNADMITTED_SOURCE_SEAM"
            touches = (
                next_interval[0] <= boundary
                if sign > 0
                else boundary <= next_interval[1]
            )
            if not touches:
                return "UNADMITTED_SOURCE_SEAM"
            try:
                current_state = ledger.evaluate_route(current.route, boundary)
                next_state = ledger.evaluate_route(next_route, boundary)
            except (KeyError, OutOfRangeError, ValueError):
                return "UNADMITTED_SOURCE_SEAM"
            position_residual, velocity_residual = _state_residuals(
                current_state, next_state
            )
            admitted = (
                position_residual <= APSIDAL_SEAM_POSITION_TOLERANCE_KM
                and velocity_residual
                <= APSIDAL_SEAM_VELOCITY_TOLERANCE_KM_PER_DAY
            )
            left_identity = (
                current.public.route_identity
                if sign > 0
                else _route_identity(next_route)
            )
            right_identity = (
                _route_identity(next_route)
                if sign > 0
                else current.public.route_identity
            )
            seams.append(
                ApsidalSeamContinuity(
                    epoch_tdb=boundary,
                    left_route_identity=left_identity,
                    right_route_identity=right_identity,
                    position_residual_km=position_residual,
                    velocity_residual_km_per_day=velocity_residual,
                    position_tolerance_km=APSIDAL_SEAM_POSITION_TOLERANCE_KM,
                    velocity_tolerance_km_per_day=(
                        APSIDAL_SEAM_VELOCITY_TOLERANCE_KM_PER_DAY
                    ),
                    admitted=admitted,
                    detail=(
                        "CONTINUOUS_SOURCE_SEAM"
                        if admitted
                        else "DISCONTINUOUS_SOURCE_SEAM"
                    ),
                )
            )
            if not admitted:
                return "UNADMITTED_SOURCE_SEAM"
            next_entry = _route_entry(next_route, next_interval, next_state)
            if sign > 0:
                if next_entry.end_tdb <= current.end_tdb:
                    return "UNADMITTED_SOURCE_SEAM"
                entries.append(next_entry)
            else:
                if next_entry.start_tdb >= current.start_tdb:
                    return "UNADMITTED_SOURCE_SEAM"
                entries.insert(0, next_entry)
        return "ROUTE_PLAN_ENTRY_LIMIT"

    upper_detail = extend(1)
    lower_detail = extend(-1)
    public_schedule = tuple(entry.public for entry in entries)
    identity_material = {
        "algorithm": APSIDAL_ALGORITHM_VERSION,
        "center": context.center_naif_id,
        "target": context.body.naif_id,
        "pool_generation": context.snapshot.generation,
        "schedule": [
            {
                "start": entry.start_tdb,
                "end": entry.end_tdb,
                "route": entry.route_identity,
                "legs": [
                    {
                        "center": leg.center_naif_id,
                        "target": leg.target_naif_id,
                        "sign": leg.traversal_sign,
                        "type": leg.segment_type,
                        "source": leg.kernel_sha256,
                        "coverage_start": leg.coverage_start_tdb,
                        "coverage_end": leg.coverage_end_tdb,
                    }
                    for leg in entry.legs
                ],
            }
            for entry in public_schedule
        ],
    }
    plan_identity = hashlib.sha256(
        json.dumps(
            identity_material,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()
    return (
        _ApsidalRoutePlan(
            entries=tuple(entries),
            seams=tuple(sorted(seams, key=lambda seam: seam.epoch_tdb)),
            identity=plan_identity,
            lower_boundary_detail=lower_detail,
            upper_boundary_detail=upper_detail,
        ),
        ledger,
    )


@dataclass(frozen=True, slots=True)
class _ExtractedConic:
    """Keplerian conic orbital elements extracted from a Cartesian state."""

    shape: OrbitShape
    semi_major_axis_au: float | None
    eccentricity: float
    pericenter_distance_au: float
    apocenter_distance_au: float | None
    inclination_deg: float
    lon_ascending_node_deg: float | None
    arg_pericenter_deg: float | None
    true_anomaly_deg: float | None
    mean_anomaly_deg: float | None
    mean_motion_deg_per_day: float | None
    orbital_period_days: float | None
    time_of_pericenter_tdb: float | None
    time_of_pericenter_tt: float | None
    lon_pericenter_deg: float | None
    arg_latitude_deg: float | None
    true_longitude_deg: float
    mean_longitude_deg: float | None
    pericenter_ecliptic_lon_deg: float | None
    pericenter_ecliptic_lat_deg: float | None
    undefined: tuple[UndefinedElement, ...]


_UNDEFINED_FIELD_ORDER = (
    "semi_major_axis_au",
    "apocenter_distance_au",
    "lon_ascending_node_deg",
    "arg_pericenter_deg",
    "true_anomaly_deg",
    "mean_anomaly_deg",
    "mean_motion_deg_per_day",
    "orbital_period_days",
    "time_of_pericenter_tdb",
    "time_of_pericenter_tt",
    "lon_pericenter_deg",
    "arg_latitude_deg",
    "mean_longitude_deg",
    "pericenter_ecliptic_lon_deg",
    "pericenter_ecliptic_lat_deg",
)
_UNDEFINED_REASON_ORDER = (
    UndefinedElementReason.CIRCULAR,
    UndefinedElementReason.EQUATORIAL,
    UndefinedElementReason.PARABOLIC,
    UndefinedElementReason.HYPERBOLIC,
)


def _directed_angle(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
    normal: tuple[float, float, float],
) -> float:
    """Return the directed in-plane angle from ``first`` to ``second``."""

    first_norm = _mag3(first)
    second_norm = _mag3(second)
    normal_norm = _mag3(normal)
    cosine = _dot3(first, second) / (first_norm * second_norm)
    sine = _dot3(_cross3(first, second), normal) / (
        first_norm * second_norm * normal_norm
    )
    return math.atan2(sine, max(-1.0, min(1.0, cosine)))


def _undefined_elements(
    reasons: dict[str, set[UndefinedElementReason]],
) -> tuple[UndefinedElement, ...]:
    return tuple(
        UndefinedElement(
            field=field,
            reasons=tuple(reason for reason in _UNDEFINED_REASON_ORDER if reason in reasons[field]),
        )
        for field in _UNDEFINED_FIELD_ORDER
        if field in reasons
    )


def _extract_osculating_conic(
    position_km: tuple[float, float, float],
    velocity_km_per_day: tuple[float, float, float],
    gm_km3_s2: float,
    *,
    body_name: str,
    epoch_tdb: float,
) -> _ExtractedConic:
    """Extract one explicit conic from an inertial state.

    The state boundary is kilometres and kilometres/day.  Velocity is converted
    exactly once here; all conic equations thereafter use km, km/s, and
    km^3/s^2.  The vector invariants define the result, while angle branches
    merely express that geometric object in conventional orbital coordinates.
    """

    if not all(math.isfinite(value) for value in (*position_km, *velocity_km_per_day)):
        raise OrbitalStateDegenerateError(
            "NON_FINITE_STATE",
            body_name,
            epoch_tdb,
            math.nan,
            math.nan,
            math.nan,
            RECTILINEAR_NORMALIZED_H_TOL,
        )
    r_norm = _mag3(position_km)
    v_day_norm = _mag3(velocity_km_per_day)
    if r_norm == 0.0:
        raise OrbitalStateDegenerateError(
            "ZERO_POSITION",
            body_name,
            epoch_tdb,
            r_norm,
            v_day_norm,
            0.0,
            RECTILINEAR_NORMALIZED_H_TOL,
        )
    if v_day_norm == 0.0:
        raise OrbitalStateDegenerateError(
            "ZERO_VELOCITY",
            body_name,
            epoch_tdb,
            r_norm,
            v_day_norm,
            0.0,
            RECTILINEAR_NORMALIZED_H_TOL,
        )
    h_day = _cross3(position_km, velocity_km_per_day)
    normalized_h = _mag3(h_day) / (r_norm * v_day_norm)
    if normalized_h <= RECTILINEAR_NORMALIZED_H_TOL:
        raise OrbitalStateDegenerateError(
            "RECTILINEAR_STATE",
            body_name,
            epoch_tdb,
            r_norm,
            v_day_norm,
            normalized_h,
            RECTILINEAR_NORMALIZED_H_TOL,
        )

    velocity = tuple(component / 86400.0 for component in velocity_km_per_day)
    v_norm = _mag3(velocity)
    h = _cross3(position_km, velocity)
    h_norm = _mag3(h)
    radial_dot = _dot3(position_km, velocity)
    speed_squared = v_norm * v_norm
    eccentricity_vector = tuple(
        ((speed_squared - gm_km3_s2 / r_norm) * position_km[index]
         - radial_dot * velocity[index])
        / gm_km3_s2
        for index in range(3)
    )
    eccentricity = _mag3(eccentricity_vector)
    semilatus_rectum_km = h_norm * h_norm / gm_km3_s2
    pericenter_km = semilatus_rectum_km / (1.0 + eccentricity)

    if eccentricity < 1.0 - PARABOLIC_E_TOL:
        shape = OrbitShape.ELLIPTIC
    elif abs(eccentricity - 1.0) <= PARABOLIC_E_TOL:
        shape = OrbitShape.PARABOLIC
    else:
        shape = OrbitShape.HYPERBOLIC

    inclination = math.atan2(math.hypot(h[0], h[1]), h[2])
    sin_inclination = math.hypot(h[0], h[1]) / h_norm
    equatorial = abs(sin_inclination) < EQUATORIAL_SIN_I_TOL
    circular = shape is OrbitShape.ELLIPTIC and eccentricity < CIRCULAR_E_TOL
    node = (-h[1], h[0], 0.0)

    undefined: dict[str, set[UndefinedElementReason]] = {}

    def mark(field: str, reason: UndefinedElementReason) -> None:
        undefined.setdefault(field, set()).add(reason)

    if equatorial:
        for field in (
            "lon_ascending_node_deg",
            "arg_pericenter_deg",
            "arg_latitude_deg",
        ):
            mark(field, UndefinedElementReason.EQUATORIAL)
    if circular:
        for field in (
            "arg_pericenter_deg",
            "true_anomaly_deg",
            "mean_anomaly_deg",
            "time_of_pericenter_tdb",
            "time_of_pericenter_tt",
            "lon_pericenter_deg",
            "pericenter_ecliptic_lon_deg",
            "pericenter_ecliptic_lat_deg",
        ):
            mark(field, UndefinedElementReason.CIRCULAR)

    lon_node = None
    if not equatorial:
        lon_node = _wrap_degrees(math.degrees(math.atan2(node[1], node[0])))

    arg_pericenter = None
    true_anomaly = None
    lon_pericenter = None
    pericenter_lon = None
    pericenter_lat = None
    if not circular:
        true_anomaly = _wrap_degrees(
            math.degrees(_directed_angle(eccentricity_vector, position_km, h))
        )
        pericenter_lon = _wrap_degrees(
            math.degrees(math.atan2(eccentricity_vector[1], eccentricity_vector[0]))
        )
        pericenter_lat = math.degrees(
            math.atan2(
                eccentricity_vector[2],
                math.hypot(eccentricity_vector[0], eccentricity_vector[1]),
            )
        )
        if equatorial:
            lon_pericenter = pericenter_lon
        else:
            arg_pericenter = _wrap_degrees(
                math.degrees(_directed_angle(node, eccentricity_vector, h))
            )
            lon_pericenter = _wrap_degrees(lon_node + arg_pericenter)

    arg_latitude = None
    if not equatorial:
        arg_latitude = _wrap_degrees(
            math.degrees(_directed_angle(node, position_km, h))
        )
        true_longitude = _wrap_degrees(lon_node + arg_latitude)
    else:
        true_longitude = _wrap_degrees(
            math.degrees(math.atan2(position_km[1], position_km[0]))
        )

    semi_major_axis_km: float | None
    mean_motion_rad_s: float | None
    mean_motion_deg_day: float | None
    period_days: float | None
    apocenter_au: float | None
    mean_anomaly_deg: float | None = None
    mean_longitude_deg: float | None = None
    time_pericenter_tdb: float | None = None
    time_pericenter_tt: float | None = None

    if shape is OrbitShape.PARABOLIC:
        semi_major_axis_km = None
        mean_motion_rad_s = None
        mean_motion_deg_day = None
        period_days = None
        apocenter_au = None
        for field in (
            "semi_major_axis_au",
            "mean_motion_deg_per_day",
            "mean_anomaly_deg",
            "orbital_period_days",
            "apocenter_distance_au",
            "mean_longitude_deg",
        ):
            mark(field, UndefinedElementReason.PARABOLIC)
        barker_variable = radial_dot / math.sqrt(
            2.0 * gm_km3_s2 * pericenter_km
        )
        elapsed_seconds = math.sqrt(
            2.0 * pericenter_km**3 / gm_km3_s2
        ) * (barker_variable + barker_variable**3 / 3.0)
        time_pericenter_tdb = epoch_tdb - elapsed_seconds / 86400.0
    else:
        semi_major_axis_km = pericenter_km / (1.0 - eccentricity)
        mean_motion_rad_s = math.sqrt(
            gm_km3_s2 / abs(semi_major_axis_km) ** 3
        )
        mean_motion_deg_day = math.degrees(mean_motion_rad_s) * 86400.0
        if shape is OrbitShape.ELLIPTIC:
            period_days = math.tau / mean_motion_rad_s / 86400.0
            apocenter_au = (
                semi_major_axis_km * (1.0 + eccentricity) / KM_PER_AU
            )
            if circular:
                mean_longitude_deg = true_longitude
                for field in ("mean_anomaly_deg", "time_of_pericenter_tdb", "time_of_pericenter_tt"):
                    mark(field, UndefinedElementReason.CIRCULAR)
            else:
                sin_eccentric_anomaly = radial_dot / (
                    eccentricity
                    * math.sqrt(gm_km3_s2 * semi_major_axis_km)
                )
                cos_eccentric_anomaly = (
                    1.0 - r_norm / semi_major_axis_km
                ) / eccentricity
                eccentric_anomaly = math.atan2(
                    sin_eccentric_anomaly, cos_eccentric_anomaly
                )
                signed_mean_anomaly = (
                    eccentric_anomaly
                    - eccentricity * math.sin(eccentric_anomaly)
                )
                if math.isclose(
                    signed_mean_anomaly,
                    -math.pi,
                    rel_tol=0.0,
                    abs_tol=8.0 * math.ulp(math.pi),
                ):
                    signed_mean_anomaly = math.pi
                mean_anomaly_deg = _wrap_degrees(
                    math.degrees(signed_mean_anomaly)
                )
                time_pericenter_tdb = epoch_tdb - (
                    signed_mean_anomaly / mean_motion_rad_s / 86400.0
                )
                mean_longitude_deg = _wrap_degrees(
                    lon_pericenter + mean_anomaly_deg
                )
        else:
            period_days = None
            apocenter_au = None
            mark("orbital_period_days", UndefinedElementReason.HYPERBOLIC)
            mark("apocenter_distance_au", UndefinedElementReason.HYPERBOLIC)
            mark("mean_longitude_deg", UndefinedElementReason.HYPERBOLIC)
            sinh_hyperbolic_anomaly = radial_dot / (
                eccentricity
                * math.sqrt(-gm_km3_s2 * semi_major_axis_km)
            )
            hyperbolic_anomaly = math.asinh(sinh_hyperbolic_anomaly)
            signed_mean_anomaly = (
                eccentricity * math.sinh(hyperbolic_anomaly)
                - hyperbolic_anomaly
            )
            mean_anomaly_deg = math.degrees(signed_mean_anomaly)
            time_pericenter_tdb = epoch_tdb - (
                signed_mean_anomaly / mean_motion_rad_s / 86400.0
            )

    if time_pericenter_tdb is not None:
        from .julian import tdb_to_tt

        time_pericenter_tt = tdb_to_tt(time_pericenter_tdb)

    return _ExtractedConic(
        shape=shape,
        semi_major_axis_au=(
            None if semi_major_axis_km is None else semi_major_axis_km / KM_PER_AU
        ),
        eccentricity=eccentricity,
        pericenter_distance_au=pericenter_km / KM_PER_AU,
        apocenter_distance_au=apocenter_au,
        inclination_deg=math.degrees(inclination),
        lon_ascending_node_deg=lon_node,
        arg_pericenter_deg=arg_pericenter,
        true_anomaly_deg=true_anomaly,
        mean_anomaly_deg=mean_anomaly_deg,
        mean_motion_deg_per_day=mean_motion_deg_day,
        orbital_period_days=period_days,
        time_of_pericenter_tdb=time_pericenter_tdb,
        time_of_pericenter_tt=time_pericenter_tt,
        lon_pericenter_deg=lon_pericenter,
        arg_latitude_deg=arg_latitude,
        true_longitude_deg=true_longitude,
        mean_longitude_deg=mean_longitude_deg,
        pericenter_ecliptic_lon_deg=pericenter_lon,
        pericenter_ecliptic_lat_deg=pericenter_lat,
        undefined=_undefined_elements(undefined),
    )


# ---------------------------------------------------------------------------
# KeplerianElements
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class KeplerianElements:
    """
    Keplerian osculating orbital elements for a solar system body.

    Expressed as a typed, named vessel rather than a raw float array.

    Coordinate frame: heliocentric, J2000.0 ecliptic and equinox.
    Element type: osculating (instantaneous, valid at ``epoch_jd``).

    Fields
    ------
    name : str
        Body name (one of the ``Body.*`` constants).
    epoch_jd : float
        Julian Day (TT) at which the elements were computed.
    semi_major_axis_au : float
        Semi-major axis in Astronomical Units (AU).
    eccentricity : float
        Orbital eccentricity [0, 1) for elliptical orbits.
    inclination_deg : float
        Orbital inclination to the J2000.0 ecliptic (degrees).
    lon_ascending_node_deg : float
        Longitude of the ascending node, measured from the J2000.0
        vernal equinox (degrees, [0, 360)).
    arg_perihelion_deg : float
        Argument of perihelion, measured from the ascending node
        in the orbital plane (degrees, [0, 360)).
    mean_anomaly_deg : float
        Mean anomaly at epoch (degrees, [0, 360)).
    mean_motion_deg_per_day : float
        Mean daily motion in longitude (degrees/day).
    orbital_period_days : float
        Sidereal orbital period in days.
    """
    name:                   str
    epoch_jd:               float
    semi_major_axis_au:     float
    eccentricity:           float
    inclination_deg:        float
    lon_ascending_node_deg: float
    arg_perihelion_deg:     float
    mean_anomaly_deg:       float
    mean_motion_deg_per_day: float
    orbital_period_days:    float

    @property
    def perihelion_distance_au(self) -> float:
        """Perihelion distance: a(1 − e)."""
        return self.semi_major_axis_au * (1.0 - self.eccentricity)

    @property
    def aphelion_distance_au(self) -> float:
        """Aphelion distance: a(1 + e)."""
        return self.semi_major_axis_au * (1.0 + self.eccentricity)


# ---------------------------------------------------------------------------
# DistanceExtremes
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class DistanceExtremes:
    """
    Perihelion and aphelion distances and dates for a solar system body.

    Expressed as a typed vessel.

    This legacy vessel records the body's next perihelion and next aphelion
    passage, together with the heliocentric distance at each.  Both Julian Day
    fields are TT.  The richer :class:`ApsidalPassages` surface carries next
    versus previous policy, all three clock coordinates and non-found outcomes.

    Fields
    ------
    name : str
        Body name (one of the ``Body.*`` constants).
    perihelion_jd : float
        Julian Day (TT) of the perihelion passage.
    perihelion_distance_au : float
        Heliocentric distance at perihelion (AU).
    aphelion_jd : float
        Julian Day (TT) of the aphelion passage.
    aphelion_distance_au : float
        Heliocentric distance at aphelion (AU).

    Doctrine note: both passages are recorded for the same orbit (one
    perihelion and one aphelion per vessel).  For inner planets the
    aphelion often precedes the perihelion in the search window; the
    vessel records them as observed, with no forced temporal ordering.
    """
    name:                    str
    perihelion_jd:           float
    perihelion_distance_au:  float
    aphelion_jd:             float
    aphelion_distance_au:    float


# ===========================================================================
# Private helpers — coordinate transforms and element extraction
# ===========================================================================

def _rot_eq_to_ecl(
    x: float, y: float, z: float, eps: float
) -> tuple[float, float, float]:
    """Rotate an ICRF equatorial vector to the J2000 ecliptic frame.

    The rotation is about the x-axis by the obliquity angle ε:
        x_ecl =  x
        y_ecl =  y cos ε + z sin ε
        z_ecl = −y sin ε + z cos ε
    """
    cos_e = math.cos(eps)
    sin_e = math.sin(eps)
    return x, y * cos_e + z * sin_e, -y * sin_e + z * cos_e


def _cross3(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> tuple[float, float, float]:
    ax, ay, az = a
    bx, by, bz = b
    return (ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx)


def _dot3(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _mag3(a: tuple[float, float, float]) -> float:
    return math.sqrt(_dot3(a, a))


def _wrap_degrees(angle_deg: float) -> float:
    """Normalize an angle into the half-open interval [0, 360)."""
    return angle_deg % 360.0


def _orbital_mu_km3_day2(body: str) -> float:
    """Return the effective two-body gravitational parameter for ``body``."""
    gm_body_km3_s2 = _BODY_SYSTEM_GM_KM3_S2.get(body)
    if gm_body_km3_s2 is None:
        return _GM_SUN_KM3_DAY2
    return _GM_SUN_KM3_DAY2 + gm_body_km3_s2 * 86400.0 ** 2


def _keplerian_from_state(
    r: tuple[float, float, float],
    v: tuple[float, float, float],
    gm: float,
    name: str,
    epoch_jd: float,
) -> KeplerianElements:
    """Extract Keplerian osculating elements from a heliocentric state vector.

    Parameters
    ----------
    r : heliocentric position (km, J2000 ecliptic)
    v : heliocentric velocity (km/day, J2000 ecliptic)
    gm : gravitational parameter of the central body (km³/day²)
    name : body name (stored verbatim in the result)
    epoch_jd : Julian Day at which the state was evaluated

    Returns
    -------
    KeplerianElements with all angular fields in degrees [0, 360).
    """
    tol = 1e-10

    rx, ry, rz = r
    r_mag = _mag3(r)
    v_mag = _mag3(v)

    # Angular momentum h = r × v
    h = _cross3(r, v)
    h_mag = _mag3(h)
    if h_mag < tol:
        raise ValueError(
            f"Body {name!r} has a degenerate state vector; "
            "orbital plane is undefined"
        )

    # Inclination i = arccos(h_z / |h|)
    incl_rad = math.acos(max(-1.0, min(1.0, h[2] / h_mag)))

    # Ascending-node vector N = k̂ × h = (−h_y, h_x, 0)
    nx, ny = -h[1], h[0]
    n_mag = math.sqrt(nx * nx + ny * ny)

    # Longitude of ascending node Ω
    if n_mag < tol:
        omega = 0.0                            # equatorial orbit: node undefined
    else:
        omega = _wrap_degrees(math.degrees(math.atan2(ny, nx)))

    # Eccentricity vector e = (v × h) / GM − r̂
    vxh = _cross3(v, h)
    ex = vxh[0] / gm - rx / r_mag
    ey = vxh[1] / gm - ry / r_mag
    ez = vxh[2] / gm - rz / r_mag
    ecc = math.sqrt(ex * ex + ey * ey + ez * ez)
    has_defined_periapsis = ecc >= tol
    has_defined_node = n_mag >= tol

    # Argument of perihelion ω
    if has_defined_node and has_defined_periapsis:
        cos_arg_peri = max(-1.0, min(1.0, (ex * nx + ey * ny) / (ecc * n_mag)))
        sin_arg_peri = _dot3(_cross3((nx, ny, 0.0), (ex, ey, ez)), h) / (n_mag * ecc * h_mag)
        arg_peri = _wrap_degrees(math.degrees(math.atan2(sin_arg_peri, cos_arg_peri)))
    elif has_defined_periapsis:
        # Equatorial eccentric orbit: use longitude of perihelion with Ω := 0.
        arg_peri = _wrap_degrees(math.degrees(math.atan2(ey, ex)))
    else:
        arg_peri = 0.0

    # True anomaly ν, or its circular-orbit replacements when perihelion is undefined.
    if has_defined_periapsis:
        cos_true_anom = max(-1.0, min(1.0, (ex * rx + ey * ry + ez * rz) / (ecc * r_mag)))
        sin_true_anom = _dot3(_cross3((ex, ey, ez), r), h) / (ecc * r_mag * h_mag)
        true_anom = _wrap_degrees(math.degrees(math.atan2(sin_true_anom, cos_true_anom)))
    elif has_defined_node:
        # Circular inclined orbit: use argument of latitude u.
        cos_true_anom = max(-1.0, min(1.0, (nx * rx + ny * ry) / (n_mag * r_mag)))
        sin_true_anom = _dot3(_cross3((nx, ny, 0.0), r), h) / (n_mag * r_mag * h_mag)
        true_anom = _wrap_degrees(math.degrees(math.atan2(sin_true_anom, cos_true_anom)))
    else:
        # Circular equatorial orbit: use true longitude l.
        true_anom = _wrap_degrees(math.degrees(math.atan2(ry, rx)))

    # Semi-major axis from vis-viva: a = −GM / (2 · ε_orb)
    energy = 0.5 * v_mag ** 2 - gm / r_mag
    if abs(energy) < 1e-30:
        raise ValueError(
            f"Body {name!r} is on a parabolic trajectory; "
            "semi-major axis is undefined"
        )
    sma_km = -gm / (2.0 * energy)

    # Mean anomaly M from eccentric anomaly E (elliptical only)
    if ecc < 1.0:
        half_nu = math.radians(true_anom) / 2.0
        if has_defined_periapsis:
            ea = 2.0 * math.atan2(
                math.sqrt(max(0.0, 1.0 - ecc)) * math.sin(half_nu),
                math.sqrt(max(0.0, 1.0 + ecc)) * math.cos(half_nu),
            )
            mean_anom = _wrap_degrees(math.degrees(ea - ecc * math.sin(ea)))
        else:
            # Circular ellipse: mean anomaly is equal to the available phase angle.
            mean_anom = true_anom
    else:
        mean_anom = 0.0                        # hyperbolic: M not defined

    # Mean motion n = √(GM / a³) and period T = 2π / n
    if sma_km > 0.0:
        mean_motion = math.degrees(math.sqrt(gm / sma_km ** 3))   # deg/day
        period      = 360.0 / mean_motion                          # days
    else:
        mean_motion = 0.0
        period      = float("inf")

    return KeplerianElements(
        name=name,
        epoch_jd=epoch_jd,
        semi_major_axis_au=sma_km / KM_PER_AU,
        eccentricity=ecc,
        inclination_deg=math.degrees(incl_rad),
        lon_ascending_node_deg=_wrap_degrees(omega),
        arg_perihelion_deg=_wrap_degrees(arg_peri),
        mean_anomaly_deg=_wrap_degrees(mean_anom),
        mean_motion_deg_per_day=mean_motion,
        orbital_period_days=period,
    )


# ===========================================================================
# Public entry point
# ===========================================================================

def _coerce_enum(value: object, enum_type: type[Enum], parameter: str):
    if isinstance(value, enum_type):
        return value
    if isinstance(value, str):
        try:
            return enum_type(value)
        except ValueError:
            pass
    raise OrbitalInputError(
        parameter,
        value,
        tuple(member.value for member in enum_type),
    )


def _public_gravity(gravity: _OrbitalGravity) -> OrbitalGravity:
    if gravity.planetary_ephemeris is None:
        raise OrbitalGravityModelError(None, None)
    return OrbitalGravity(
        rule=gravity.rule,
        gm_km3_s2=gravity.gm_km3_s2,
        component_naif_ids=gravity.component_naif_ids,
        component_gm_km3_s2=gravity.component_gm_km3_s2,
        policy=gravity.policy,
        source_url=gravity.source_url,
        retrieved_date=gravity.retrieved_date,
        source_sha256=gravity.source_sha256,
        source_bytes=gravity.source_bytes,
        planetary_ephemeris=gravity.planetary_ephemeris,
    )


def _public_time_conversion(time) -> OrbitalTimeConversion:
    from .julian import (
        NAIF_LSK_TT_TDB_POLICY,
        NAIF_LSK_TT_TDB_SOURCE_BYTES,
        NAIF_LSK_TT_TDB_SOURCE_SHA256,
        NAIF_LSK_TT_TDB_SOURCE_URL,
        NAIF_LSK_TT_TDB_VERSION,
    )

    return OrbitalTimeConversion(
        delta_t_policy="MOIRA_SOURCE_OWNED_DELTA_T_V1",
        delta_t_source_product=time.raw_delta_t.source_product,
        delta_t_retarget_mode=time.raw_delta_t.retarget_mode,
        delta_t_correction_seconds=time.delta_t_correction_seconds,
        identity_iterations=time.identity_iterations,
        tt_tdb_policy=NAIF_LSK_TT_TDB_POLICY,
        tt_tdb_version=NAIF_LSK_TT_TDB_VERSION,
        tt_tdb_source_url=NAIF_LSK_TT_TDB_SOURCE_URL,
        tt_tdb_source_sha256=NAIF_LSK_TT_TDB_SOURCE_SHA256,
        tt_tdb_source_bytes=NAIF_LSK_TT_TDB_SOURCE_BYTES,
        tt_tdb_iterations=time.tt_tdb_iterations,
    )


def osculating_elements(
    body: str | int,
    jd_ut: float,
    *,
    center: OrbitalCenter,
    frame: OrbitalFrame,
    reader: KernelReader | None = None,
) -> OsculatingElements:
    """Return strict, source-receipted osculating elements.

    ``jd_ut`` is UT1.  State evaluation is performed at the corresponding TDB
    epoch, while frame models consume TT.  ``center`` and ``frame`` are required
    policy choices and accept their enum members or exact string values.
    """

    selected_center = _coerce_enum(center, OrbitalCenter, "center")
    selected_frame = _coerce_enum(frame, OrbitalFrame, "frame")
    state = bind_orbital_state(
        body,
        jd_ut,
        center_key=selected_center.value,
        reader=reader,
    )
    frame_transform = orbital_frame_transform(
        selected_frame.value,
        state.time.epoch_tt,
    )
    position, velocity = rotate_orbital_state(
        frame_transform,
        state.position_icrf_km,
        state.velocity_icrf_km_per_day,
    )
    conic = _extract_osculating_conic(
        position,
        velocity,
        state.gravity.gm_km3_s2,
        body_name=state.body.name,
        epoch_tdb=state.time.epoch_tdb,
    )

    provenance = OsculatingElementsProvenance(
        state_source=state.source,
        gravity=_public_gravity(state.gravity),
        frame_construction=OrbitalFrameConstruction(
            frame=selected_frame,
            routine=frame_transform.routine,
            router_branch=frame_transform.router_branch,
            precession_model=frame_transform.precession_model,
            obliquity_model=frame_transform.obliquity_model,
            nutation_model=frame_transform.nutation_model,
        ),
        frame_model_interval_tt=frame_transform.admitted_interval_tt,
        time_conversion=_public_time_conversion(state.time),
        singularity_thresholds=OrbitalSingularityThresholds(
            circular_e_tolerance=CIRCULAR_E_TOL,
            equatorial_sin_i_tolerance=EQUATORIAL_SIN_I_TOL,
            parabolic_e_tolerance=PARABOLIC_E_TOL,
            rectilinear_normalized_h_tolerance=RECTILINEAR_NORMALIZED_H_TOL,
            policy=_SINGULARITY_POLICY,
        ),
    )
    return OsculatingElements(
        body=state.body,
        center=selected_center,
        frame=selected_frame,
        jd_ut=state.time.jd_ut1,
        epoch_tt=state.time.epoch_tt,
        epoch_tdb=state.time.epoch_tdb,
        delta_t_seconds=state.time.delta_t_seconds,
        tdb_minus_tt_seconds=state.time.tdb_minus_tt_seconds,
        shape=conic.shape,
        semi_major_axis_au=conic.semi_major_axis_au,
        eccentricity=conic.eccentricity,
        pericenter_distance_au=conic.pericenter_distance_au,
        apocenter_distance_au=conic.apocenter_distance_au,
        inclination_deg=conic.inclination_deg,
        lon_ascending_node_deg=conic.lon_ascending_node_deg,
        arg_pericenter_deg=conic.arg_pericenter_deg,
        true_anomaly_deg=conic.true_anomaly_deg,
        mean_anomaly_deg=conic.mean_anomaly_deg,
        mean_motion_deg_per_day=conic.mean_motion_deg_per_day,
        orbital_period_days=conic.orbital_period_days,
        time_of_pericenter_tdb=conic.time_of_pericenter_tdb,
        time_of_pericenter_tt=conic.time_of_pericenter_tt,
        lon_pericenter_deg=conic.lon_pericenter_deg,
        arg_latitude_deg=conic.arg_latitude_deg,
        true_longitude_deg=conic.true_longitude_deg,
        mean_longitude_deg=conic.mean_longitude_deg,
        pericenter_ecliptic_lon_deg=conic.pericenter_ecliptic_lon_deg,
        pericenter_ecliptic_lat_deg=conic.pericenter_ecliptic_lat_deg,
        undefined=conic.undefined,
        provenance=provenance,
    )


def _apsidal_crossing_kind(
    first: _ApsidalSample,
    second: _ApsidalSample,
) -> str | None:
    left, right = sorted((first, second), key=lambda sample: sample.epoch_tdb)
    left_g = left.radial_velocity_km_per_day
    right_g = right.radial_velocity_km_per_day
    if (
        abs(left_g) <= _APSIDAL_FLAT_RADIAL_TOLERANCE_KM_PER_DAY
        and abs(right_g) <= _APSIDAL_FLAT_RADIAL_TOLERANCE_KM_PER_DAY
    ):
        return None
    if left_g <= 0.0 <= right_g:
        return "PERICENTER"
    if left_g >= 0.0 >= right_g:
        return "APOCENTER"
    return None


def _refine_apsidal_root(
    ledger: _ApsidalEvaluationLedger,
    entry: _ApsidalRouteEntry,
    first: _ApsidalSample,
    second: _ApsidalSample,
) -> tuple[_ApsidalSample, int]:
    left, right = sorted((first, second), key=lambda sample: sample.epoch_tdb)
    left_g = left.radial_velocity_km_per_day
    right_g = right.radial_velocity_km_per_day
    if left_g == 0.0:
        return left, 0
    if right_g == 0.0:
        return right, 0
    if left_g * right_g > 0.0:
        raise OrbitalSearchError(
            (left.epoch_tdb, right.epoch_tdb),
            0,
            ledger.total,
            APSIDAL_ROOT_TOLERANCE_DAYS,
            min(abs(left_g), abs(right_g)),
            APSIDAL_ALGORITHM_VERSION,
        )

    midpoint = left
    for iteration in range(1, APSIDAL_MAX_ROOT_ITERATIONS + 1):
        if right.epoch_tdb - left.epoch_tdb <= APSIDAL_ROOT_TOLERANCE_DAYS:
            candidate_epoch = (left.epoch_tdb + right.epoch_tdb) / 2.0
            midpoint = ledger.sample_entry(entry, candidate_epoch)
            return midpoint, iteration
        candidate_epoch = (left.epoch_tdb + right.epoch_tdb) / 2.0
        if candidate_epoch in {left.epoch_tdb, right.epoch_tdb}:
            midpoint = min(
                (left, right),
                key=lambda sample: abs(sample.radial_velocity_km_per_day),
            )
            return midpoint, iteration
        midpoint = ledger.sample_entry(entry, candidate_epoch)
        middle_g = midpoint.radial_velocity_km_per_day
        if middle_g == 0.0:
            return midpoint, iteration
        if left_g * middle_g <= 0.0:
            right = midpoint
            right_g = middle_g
        else:
            left = midpoint
            left_g = middle_g

    raise OrbitalSearchError(
        (left.epoch_tdb, right.epoch_tdb),
        APSIDAL_MAX_ROOT_ITERATIONS,
        ledger.total,
        APSIDAL_ROOT_TOLERANCE_DAYS,
        abs(midpoint.radial_velocity_km_per_day),
        APSIDAL_ALGORITHM_VERSION,
    )


def _passage_event_outcome(
    kind: str,
    root: _ApsidalSample,
    *,
    plan: _ApsidalRoutePlan,
    ledger: _ApsidalEvaluationLedger,
    context,
    request_start_tdb: float,
    request_end_tdb: float,
) -> ApsidalPassageOutcome | None:
    low = min(request_start_tdb, request_end_tdb)
    high = max(request_start_tdb, request_end_tdb)
    if not (
        low - APSIDAL_ROOT_TOLERANCE_DAYS
        <= root.epoch_tdb
        <= high + APSIDAL_ROOT_TOLERANCE_DAYS
    ):
        return None

    local_motion_timescale = (
        APSIDAL_MAXIMUM_STEP_DAYS
        if root.speed_km_per_day == 0.0
        else root.distance_km / root.speed_km_per_day
    )
    guard_days = min(
        APSIDAL_WITNESS_MAXIMUM_OFFSET_DAYS,
        max(
            APSIDAL_WITNESS_ROOT_TOLERANCE_FACTOR
            * APSIDAL_ROOT_TOLERANCE_DAYS,
            APSIDAL_MINIMUM_STEP_DAYS
            * APSIDAL_WITNESS_MINIMUM_STEP_FRACTION,
            local_motion_timescale
            * APSIDAL_WITNESS_MOTION_TIMESCALE_FRACTION,
        ),
    )
    left_epoch = root.epoch_tdb - guard_days
    right_epoch = root.epoch_tdb + guard_days
    if left_epoch < plan.start_tdb or right_epoch > plan.end_tdb:
        return None
    left = ledger.sample(plan, left_epoch)
    exact = ledger.sample(plan, root.epoch_tdb)
    right = ledger.sample(plan, right_epoch)
    chronological_kind = _apsidal_crossing_kind(left, right)
    if chronological_kind != kind:
        return None
    distance_floor = max(1.0e-6, exact.distance_km * 1.0e-14)
    if kind == "PERICENTER":
        confirmed = (
            exact.distance_km <= left.distance_km
            and exact.distance_km <= right.distance_km
            and max(
                left.distance_km - exact.distance_km,
                right.distance_km - exact.distance_km,
            )
            > distance_floor
        )
    else:
        confirmed = (
            exact.distance_km >= left.distance_km
            and exact.distance_km >= right.distance_km
            and max(
                exact.distance_km - left.distance_km,
                exact.distance_km - right.distance_km,
            )
            > distance_floor
        )
    if not confirmed:
        return None

    from ._ephemeris_time import _ephemeris_tt_to_ut1
    from .julian import tdb_to_tt

    epoch_tt = tdb_to_tt(exact.epoch_tdb)
    try:
        jd_ut = _ephemeris_tt_to_ut1(
            epoch_tt,
            context.pool,
            snapshot=context.snapshot,
        )
    except (ArithmeticError, RuntimeError, ValueError) as exc:
        raise OrbitalTimeBasisError(
            "TDB_TO_TT_TO_UT1",
            context.time.identity.summary_label,
            context.time.identity.summary_label,
            12,
            context.time.raw_delta_t.source_product,
        ) from exc
    return ApsidalPassageOutcome(
        status=ApsidalPassageStatus.FOUND,
        epoch_tdb=exact.epoch_tdb,
        epoch_tt=epoch_tt,
        jd_ut=jd_ut,
        distance_au=exact.distance_km / KM_PER_AU,
        coverage_edge_tdb=None,
        detail="TWO_SIDED_RADIAL_VELOCITY_ROOT",
    )


def _apsidal_sampling_step(
    sample: _ApsidalSample,
    orbital_period_days: float | None,
) -> float:
    period_scale = (
        APSIDAL_MAXIMUM_STEP_DAYS
        if orbital_period_days is None
        else orbital_period_days * APSIDAL_INITIAL_PERIOD_FRACTION
    )
    radial_scale = (
        APSIDAL_MAXIMUM_STEP_DAYS
        if sample.speed_km_per_day == 0.0
        else (
            sample.distance_km / sample.speed_km_per_day
        )
        * APSIDAL_RADIAL_TIMESCALE_FRACTION
    )
    return max(
        APSIDAL_MINIMUM_STEP_DAYS,
        min(period_scale, radial_scale, APSIDAL_MAXIMUM_STEP_DAYS),
    )


def _terminal_passage_outcome(
    *,
    coverage_limited: bool,
    coverage_edge_tdb: float,
    boundary_detail: str,
    window_source: str,
    flat: bool,
) -> ApsidalPassageOutcome:
    if flat:
        return ApsidalPassageOutcome(
            status=ApsidalPassageStatus.NOT_IN_WINDOW,
            epoch_tdb=None,
            epoch_tt=None,
            jd_ut=None,
            distance_au=None,
            coverage_edge_tdb=None,
            detail="NO_ISOLATED_EXTREMUM",
        )
    if coverage_limited:
        return ApsidalPassageOutcome(
            status=ApsidalPassageStatus.BEYOND_COVERAGE,
            epoch_tdb=None,
            epoch_tt=None,
            jd_ut=None,
            distance_au=None,
            coverage_edge_tdb=coverage_edge_tdb,
            detail=boundary_detail,
        )
    return ApsidalPassageOutcome(
        status=ApsidalPassageStatus.NOT_IN_WINDOW,
        epoch_tdb=None,
        epoch_tt=None,
        jd_ut=None,
        distance_au=None,
        coverage_edge_tdb=None,
        detail=window_source,
    )


def _apsidal_start_candidate(
    *,
    plan: _ApsidalRoutePlan,
    ledger: _ApsidalEvaluationLedger,
    context,
    request_end_tdb: float,
) -> tuple[str, ApsidalPassageOutcome] | None:
    """Resolve an extremum numerically coincident with the inclusive start."""

    start_tdb = context.time.epoch_tdb
    probe_days = max(
        APSIDAL_WITNESS_ROOT_TOLERANCE_FACTOR
        * APSIDAL_ROOT_TOLERANCE_DAYS,
        APSIDAL_MINIMUM_STEP_DAYS
        * APSIDAL_WITNESS_MINIMUM_STEP_FRACTION,
    )
    left_tdb = start_tdb - probe_days
    right_tdb = start_tdb + probe_days
    if left_tdb < plan.start_tdb or right_tdb > plan.end_tdb:
        return None
    left_entry = plan.entry_at(left_tdb)
    right_entry = plan.entry_at(right_tdb)
    if left_entry.public.route_identity != right_entry.public.route_identity:
        return None
    left = ledger.sample_entry(left_entry, left_tdb)
    right = ledger.sample_entry(right_entry, right_tdb)
    kind = _apsidal_crossing_kind(left, right)
    if kind is None:
        return None
    root, _iterations = _refine_apsidal_root(
        ledger,
        left_entry,
        left,
        right,
    )
    if abs(root.epoch_tdb - start_tdb) > APSIDAL_ROOT_TOLERANCE_DAYS:
        return None
    outcome = _passage_event_outcome(
        kind,
        root,
        plan=plan,
        ledger=ledger,
        context=context,
        request_start_tdb=start_tdb,
        request_end_tdb=request_end_tdb,
    )
    if outcome is None:
        return None
    return kind, outcome


def apsidal_passages(
    body: str | int,
    jd_ut: float,
    *,
    center: OrbitalCenter,
    direction: ApsidalDirection,
    max_days: float | None = None,
    reader: KernelReader | None = None,
) -> ApsidalPassages:
    """Return next or previous two-sided local distance extrema.

    The request epoch is UT1; every state and root is evaluated in TDB.  The
    event outcomes expose TDB, TT and a verified inverse UT1 coordinate rather
    than relabelling one timescale as another.  ``center`` and ``direction``
    are required policy choices.
    """

    selected_center = _coerce_enum(center, OrbitalCenter, "center")
    selected_direction = _coerce_enum(
        direction, ApsidalDirection, "direction"
    )
    if max_days is not None:
        if (
            isinstance(max_days, bool)
            or not isinstance(max_days, (int, float))
            or not math.isfinite(float(max_days))
            or float(max_days) <= 0.0
        ):
            raise OrbitalInputError(
                "max_days", max_days, ("positive finite real days", None)
            )
        requested_max_days = float(max_days)
    else:
        requested_max_days = None

    with lease_orbital_context(
        body,
        jd_ut,
        center_key=selected_center.value,
        reader=reader,
    ) as context:
        plan, ledger = _build_apsidal_route_plan(context)
        conic = _extract_osculating_conic(
            context.initial_state.position_km,
            context.initial_state.velocity_km_per_day,
            context.gravity.gm_km3_s2,
            body_name=context.body.name,
            epoch_tdb=context.time.epoch_tdb,
        )
        sign = 1.0 if selected_direction is ApsidalDirection.NEXT else -1.0
        route_edge = plan.end_tdb if sign > 0.0 else plan.start_tdb

        if requested_max_days is not None:
            window_source = "EXPLICIT_MAX_DAYS"
            window_edge = context.time.epoch_tdb + sign * requested_max_days
        elif (
            conic.shape is OrbitShape.ELLIPTIC
            and conic.orbital_period_days is not None
        ):
            window_source = "AUTO_PERIOD"
            window_edge = (
                context.time.epoch_tdb
                + sign * 1.5 * conic.orbital_period_days
            )
        else:
            window_source = "ROUTE_COVERAGE"
            window_edge = route_edge

        directional_route_distance = sign * (
            route_edge - context.time.epoch_tdb
        )
        directional_window_distance = sign * (
            window_edge - context.time.epoch_tdb
        )
        coverage_limited = (
            directional_route_distance
            <= directional_window_distance + APSIDAL_ROOT_TOLERANCE_DAYS
        )
        search_edge = (
            route_edge
            if coverage_limited
            else window_edge
        )
        boundary_detail = (
            plan.upper_boundary_detail
            if sign > 0.0
            else plan.lower_boundary_detail
        )

        found: dict[str, ApsidalPassageOutcome] = {}
        start_candidate = _apsidal_start_candidate(
            plan=plan,
            ledger=ledger,
            context=context,
            request_end_tdb=search_edge,
        )
        if start_candidate is not None:
            found[start_candidate[0]] = start_candidate[1]
        entries = plan.entries if sign > 0.0 else tuple(reversed(plan.entries))
        for entry in entries:
            if len(found) == 2:
                break
            if sign > 0.0:
                local_start = max(context.time.epoch_tdb, entry.start_tdb)
                local_end = min(search_edge, entry.end_tdb)
                if local_start > local_end:
                    continue
            else:
                local_start = min(context.time.epoch_tdb, entry.end_tdb)
                local_end = max(search_edge, entry.start_tdb)
                if local_start < local_end:
                    continue

            previous = ledger.sample_entry(entry, local_start)
            while sign * (local_end - previous.epoch_tdb) > 0.0:
                step = _apsidal_sampling_step(
                    previous, conic.orbital_period_days
                )
                next_epoch = previous.epoch_tdb + sign * step
                if sign > 0.0:
                    next_epoch = min(next_epoch, local_end)
                else:
                    next_epoch = max(next_epoch, local_end)
                if next_epoch == previous.epoch_tdb:
                    break
                current = ledger.sample_entry(entry, next_epoch)
                kind = _apsidal_crossing_kind(previous, current)
                if kind is not None and kind not in found:
                    root, _iterations = _refine_apsidal_root(
                        ledger, entry, previous, current
                    )
                    outcome = _passage_event_outcome(
                        kind,
                        root,
                        plan=plan,
                        ledger=ledger,
                        context=context,
                        request_start_tdb=context.time.epoch_tdb,
                        request_end_tdb=search_edge,
                    )
                    if outcome is not None:
                        found[kind] = outcome
                previous = current

        flat = bool(ledger.radial_samples) and max(
            abs(value) for value in ledger.radial_samples
        ) <= _APSIDAL_FLAT_RADIAL_TOLERANCE_KM_PER_DAY
        terminal = _terminal_passage_outcome(
            coverage_limited=coverage_limited,
            coverage_edge_tdb=route_edge,
            boundary_detail=boundary_detail,
            window_source=window_source,
            flat=flat,
        )
        pericenter = found.get("PERICENTER", terminal)
        apocenter = found.get("APOCENTER", terminal)
        searched_min = (
            context.time.epoch_tdb
            if not math.isfinite(ledger.search_minimum_epoch_tdb)
            else ledger.search_minimum_epoch_tdb
        )
        searched_max = (
            context.time.epoch_tdb
            if not math.isfinite(ledger.search_maximum_epoch_tdb)
            else ledger.search_maximum_epoch_tdb
        )
        provenance = ApsidalPassagesProvenance(
            algorithm_version=APSIDAL_ALGORITHM_VERSION,
            gravity=_public_gravity(context.gravity),
            time_conversion=_public_time_conversion(context.time),
            state_source=_state_source(context.initial_state),
            initial_period_fraction=APSIDAL_INITIAL_PERIOD_FRACTION,
            radial_timescale_fraction=APSIDAL_RADIAL_TIMESCALE_FRACTION,
            minimum_step_days=APSIDAL_MINIMUM_STEP_DAYS,
            maximum_step_days=APSIDAL_MAXIMUM_STEP_DAYS,
            witness_root_tolerance_factor=(
                APSIDAL_WITNESS_ROOT_TOLERANCE_FACTOR
            ),
            witness_minimum_step_fraction=(
                APSIDAL_WITNESS_MINIMUM_STEP_FRACTION
            ),
            witness_motion_timescale_fraction=(
                APSIDAL_WITNESS_MOTION_TIMESCALE_FRACTION
            ),
            witness_maximum_offset_days=(
                APSIDAL_WITNESS_MAXIMUM_OFFSET_DAYS
            ),
            refinement_tolerance_days=APSIDAL_ROOT_TOLERANCE_DAYS,
            maximum_root_iterations=APSIDAL_MAX_ROOT_ITERATIONS,
            evaluation_budget=APSIDAL_EVALUATION_BUDGET,
            extremum_semantics=(
                "isolated two-sided local extremum of center-relative distance "
                "from a chronological radial-velocity sign crossing"
            ),
            search_window_source=window_source,
            route_plan_identity=plan.identity,
            route_schedule=tuple(entry.public for entry in plan.entries),
            segment_usage=ledger.usages(),
            seam_continuity=plan.seams,
            searched_interval_tdb=(searched_min, searched_max),
            total_evaluations=ledger.total,
        )
        return ApsidalPassages(
            body=context.body,
            center=selected_center,
            direction=selected_direction,
            jd_ut=context.time.jd_ut1,
            start_epoch_tt=context.time.epoch_tt,
            start_epoch_tdb=context.time.epoch_tdb,
            pericenter=pericenter,
            apocenter=apocenter,
            provenance=provenance,
        )


_LEGACY_ORBIT_BODIES = (
    Body.MERCURY,
    Body.VENUS,
    Body.EARTH,
    Body.MARS,
    Body.JUPITER,
    Body.SATURN,
    Body.URANUS,
    Body.NEPTUNE,
    Body.PLUTO,
)


def _legacy_result_from_strict(elements: OsculatingElements) -> KeplerianElements:
    required = (
        elements.semi_major_axis_au,
        elements.lon_ascending_node_deg,
        elements.arg_pericenter_deg,
        elements.mean_anomaly_deg,
        elements.mean_motion_deg_per_day,
        elements.orbital_period_days,
    )
    if any(value is None for value in required):
        raise OrbitalStateDegenerateError(
            "LEGACY_FIELDS_UNDEFINED",
            elements.body.name,
            elements.epoch_tdb,
            math.nan,
            math.nan,
            math.nan,
            RECTILINEAR_NORMALIZED_H_TOL,
        )
    return KeplerianElements(
        name=elements.body.name,
        epoch_jd=elements.epoch_tt,
        semi_major_axis_au=elements.semi_major_axis_au,
        eccentricity=elements.eccentricity,
        inclination_deg=elements.inclination_deg,
        lon_ascending_node_deg=elements.lon_ascending_node_deg,
        arg_perihelion_deg=elements.arg_pericenter_deg,
        mean_anomaly_deg=elements.mean_anomaly_deg,
        mean_motion_deg_per_day=elements.mean_motion_deg_per_day,
        orbital_period_days=elements.orbital_period_days,
    )


def orbital_elements_at(
    body: str,
    jd_ut: float,
    reader: SpkReader | None,
) -> KeplerianElements:
    """Compatibility wrapper for planet-only Sun/J2000 elements.

    The positional signature is preserved.  The returned ``epoch_jd`` is now
    correctly TT.  Built-in DE440/DE441 readers use the strict core; a
    historical third-party protocol reader retains the frozen
    ``LEGACY_ORBITS_V1`` extraction policy without claiming Horizons parity.
    """

    resolved = resolve_orbital_body(body)
    if resolved.name == Body.SUN:
        raise OrbitalBodyNotSupportedError(
            Body.SUN, "center", "the Sun is the heliocentric reference center"
        )
    if resolved.name not in _LEGACY_ORBIT_BODIES:
        raise OrbitalLegacyBodyNotAllowedError(
            resolved.name,
            "orbital_elements_at",
            _LEGACY_ORBIT_BODIES,
            "osculating_elements",
        )
    try:
        strict = osculating_elements(
            resolved.name,
            jd_ut,
            center=OrbitalCenter.SUN,
            frame=OrbitalFrame.J2000_ECLIPTIC,
            reader=reader,
        )
    except (OrbitalGravityModelError, OrbitalSourceReceiptError, OrbitalTimeBasisError):
        return _legacy_orbital_elements_at_unidentified(resolved.name, jd_ut, reader)
    return _legacy_result_from_strict(strict)


def _legacy_orbital_elements_at_unidentified(
    body: str,
    jd_ut: float,
    reader: SpkReader | None,
) -> KeplerianElements:
    """
    Compute heliocentric osculating Keplerian orbital elements for a body.

    The elements are instantaneous (osculating) at ``jd_ut``, expressed in the
    heliocentric J2000.0 ecliptic frame.

    Parameters
    ----------
    body : str
        Body name — one of the ``Body.*`` constants (e.g. ``Body.EARTH``).
        ``Body.SUN`` and ``Body.MOON`` raise ``ValueError``.
    jd_ut : float
        Julian Date in Universal Time (UT1).
    reader : SpkReader
        An open DE441 kernel reader (e.g. from ``moira.spk_reader.get_reader()``).

    Returns
    -------
    KeplerianElements
        Heliocentric J2000.0 osculating elements at ``jd_ut``.

    Raises
    ------
    ValueError
        If ``body`` is ``Body.SUN`` (the reference center) or ``Body.MOON``
        (whose heliocentric elements are not physically meaningful in the
        osculating Keplerian sense).

    Notes
    -----
    Method
        1. Evaluate the body's and the Sun's Solar-System Barycentric (SSB)
           position and velocity from DE441 at ``jd_tt = jd_ut + ΔT/86400``.
        2. Subtract to form the heliocentric state in ICRF (equatorial J2000).
        3. Rotate to the J2000.0 ecliptic frame via the fixed obliquity
           ε₀ = 23.439291111° (IAU J2000.0 value).
        4. Apply classical Keplerian element extraction (Bate, Mueller & White
           §2.4 algorithm) using GM_sun = 1.32712440018×10²⁰ m³/s².

    Validation
        Compare against Meeus *Astronomical Algorithms* Table 31.a (J2000.0
        elements) for the eight major planets.  Tolerance: ≤ 0.01° for angular
        elements, ≤ 0.001 AU for semi-major axis.
    """
    from ._ephemeris_time import _ut1_to_ephemeris_tt
    from .planets import _barycentric_state, _earth_barycentric_state
    from .spk_reader import get_active_reader

    if reader is None:
        reader = get_active_reader()
    if reader is None:
        raise OrbitalKernelMissingError("no active or explicit reader")

    jd_tt = _ut1_to_ephemeris_tt(jd_ut, reader)

    # Body barycentric state (km, km/day, ICRF)
    if body == Body.EARTH:
        body_pos, body_vel = _earth_barycentric_state(jd_tt, reader)
    else:
        body_pos, body_vel = _barycentric_state(body, jd_tt, reader)

    # Sun barycentric state (km, km/day, ICRF): SSB → Sun (NAIF 10)
    sun_pos, sun_vel = reader.position_and_velocity(0, 10, jd_tt)

    # Heliocentric state in ICRF
    r_icrf = (
        body_pos[0] - sun_pos[0],
        body_pos[1] - sun_pos[1],
        body_pos[2] - sun_pos[2],
    )
    v_icrf = (
        body_vel[0] - sun_vel[0],
        body_vel[1] - sun_vel[1],
        body_vel[2] - sun_vel[2],
    )

    # Rotate to J2000.0 ecliptic frame
    eps = _J2000_OBLIQUITY_RAD
    r_ecl = _rot_eq_to_ecl(*r_icrf, eps)
    v_ecl = _rot_eq_to_ecl(*v_icrf, eps)

    return _keplerian_from_state(
        r_ecl,
        v_ecl,
        _orbital_mu_km3_day2(body),
        body,
        jd_tt,
    )


def distance_extremes_at(
    body: str,
    jd_ut: float,
    reader: SpkReader | None,
) -> DistanceExtremes:
    """
    Find the next heliocentric perihelion and aphelion for a legacy planet.

    This is the frozen planet-only compatibility adapter over
    :func:`apsidal_passages`.  Search states and roots are evaluated in TDB;
    both returned ``*_jd`` fields are TT, as declared by
    :class:`DistanceExtremes`.

    Parameters
    ----------
    body : str
        Body name — one of the ``Body.*`` constants.  ``Body.SUN`` raises
        ``ValueError``; ``Body.MOON`` is not meaningful for this surface
        and also raises.
    jd_ut : float
        Search start in Julian Date (UT1).  The function finds the *next*
        perihelion and *next* aphelion after this date.
    reader : SpkReader or None
        An explicit strict reader, or the active reader when ``None``.

    Returns
    -------
    DistanceExtremes
        Perihelion and aphelion JDs (TT) and heliocentric distances (AU).
        The two passages are the nearest ones forward from ``jd_ut``;
        they may come in either order (inner planets often reach aphelion
        before perihelion within the same half-orbit).

    Raises
    ------
    OrbitalPassageUnavailableError
        If either passage cannot be established before the automatic period
        or exact route-coverage boundary.  The complete typed passage result
        is attached to the error.

    Notes
    -----
    No chronological ordering is imposed between the two events.
    """
    resolved = resolve_orbital_body(body)
    if resolved.name not in _LEGACY_ORBIT_BODIES:
        raise OrbitalLegacyBodyNotAllowedError(
            resolved.name,
            "distance_extremes_at",
            _LEGACY_ORBIT_BODIES,
            "apsidal_passages",
        )
    passages = apsidal_passages(
        resolved.name,
        jd_ut,
        center=OrbitalCenter.SUN,
        direction=ApsidalDirection.NEXT,
        reader=reader,
    )
    missing = tuple(
        kind
        for kind, outcome in (
            ("PERICENTER", passages.pericenter),
            ("APOCENTER", passages.apocenter),
        )
        if outcome.status is not ApsidalPassageStatus.FOUND
    )
    if missing:
        raise OrbitalPassageUnavailableError(passages, missing)

    assert passages.pericenter.epoch_tt is not None
    assert passages.pericenter.distance_au is not None
    assert passages.apocenter.epoch_tt is not None
    assert passages.apocenter.distance_au is not None

    return DistanceExtremes(
        name=resolved.name,
        perihelion_jd=passages.pericenter.epoch_tt,
        perihelion_distance_au=passages.pericenter.distance_au,
        aphelion_jd=passages.apocenter.epoch_tt,
        aphelion_distance_au=passages.apocenter.distance_au,
    )


# ---------------------------------------------------------------------------
# Stage 5: SBDB Orbit Classification
# ---------------------------------------------------------------------------

JPL_ORBIT_CLASS_TITLES: dict[OrbitClassCode, str] = {
    OrbitClassCode.IEO: "Atira",
    OrbitClassCode.ATE: "Aten",
    OrbitClassCode.APO: "Apollo",
    OrbitClassCode.AMO: "Amor",
    OrbitClassCode.MCA: "Mars-crossing Asteroid",
    OrbitClassCode.IMB: "Inner Main-belt Asteroid",
    OrbitClassCode.MBA: "Main-belt Asteroid",
    OrbitClassCode.OMB: "Outer Main-belt Asteroid",
    OrbitClassCode.TJN: "Jupiter Trojan",
    OrbitClassCode.AST: "Asteroid",
    OrbitClassCode.CEN: "Centaur",
    OrbitClassCode.TNO: "TransNeptunian Object",
    OrbitClassCode.PAA: "Parabolic Asteroid",
    OrbitClassCode.HYA: "Hyperbolic Asteroid",
}

ORBIT_CLASS_POLICY = "jpl_sbdb_osculating_v1"

_ORBITAL_ERROR_CODES: dict[type[Exception], str] = {
    OrbitalInputError: "ORBITAL_INPUT_ERROR",
    OrbitalBodyNotFoundError: "ORBITAL_BODY_NOT_FOUND",
    OrbitalAmbiguousBodyError: "ORBITAL_AMBIGUOUS_BODY",
    OrbitalBodyNotSupportedError: "ORBITAL_BODY_NOT_SUPPORTED",
    OrbitalCenterNotAllowedError: "ORBITAL_CENTER_NOT_ALLOWED",
    OrbitalFrameUnavailableError: "ORBITAL_FRAME_UNAVAILABLE",
    OrbitalLegacyBodyNotAllowedError: "ORBITAL_LEGACY_BODY_NOT_ALLOWED",
    OrbitalBodyNotLoadedError: "ORBITAL_BODY_NOT_LOADED",
    OrbitalCoverageError: "ORBITAL_COVERAGE_ERROR",
    OrbitalKernelMissingError: "ORBITAL_KERNEL_MISSING",
    OrbitalGravityModelError: "ORBITAL_GRAVITY_MODEL_ERROR",
    OrbitalTimeBasisError: "ORBITAL_TIME_BASIS_ERROR",
    OrbitalSourceReceiptError: "ORBITAL_SOURCE_RECEIPT_ERROR",
    OrbitalStateDegenerateError: "ORBITAL_STATE_DEGENERATE",
    OrbitalSearchError: "ORBITAL_SEARCH_ERROR",
    OrbitalPassageUnavailableError: "ORBITAL_PASSAGE_UNAVAILABLE",
}


def _sanitize_json_value(value: Any) -> Any:
    """Recursively coerce attributes to JSON-safe primitives or type names."""
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, (int, float)):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Infinity" if value > 0 else "-Infinity"
        return value
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, (list, tuple)):
        return tuple(_sanitize_json_value(item) for item in value)
    if isinstance(value, dict):
        return tuple(sorted((str(k), _sanitize_json_value(v)) for k, v in value.items()))
    return f"{type(value).__module__}.{type(value).__qualname__}"


def _sanitize_orbital_error(exc: Exception) -> OrbitalErrorReceipt:
    """Build a sanitized failure receipt with allowlisted attributes."""
    error_code = _ORBITAL_ERROR_CODES.get(type(exc), type(exc).__name__.upper())
    msg = str(exc)
    raw_details: dict[str, Any] = {}
    for attr in dir(exc):
        if attr.startswith("_") or attr in {"args", "with_traceback"}:
            continue
        val = getattr(exc, attr, None)
        if callable(val):
            continue
        if "path" in attr.lower() or "trace" in attr.lower():
            continue
        raw_details[attr] = _sanitize_json_value(val)
    sorted_details = tuple(sorted(raw_details.items(), key=lambda kv: kv[0]))
    return OrbitalErrorReceipt(
        error_code=error_code,
        message=msg,
        details=sorted_details,
    )


def _classify_osculating_elements(
    elements: OsculatingElements,
) -> tuple[
    OrbitClassCode,
    str,
    tuple[OrbitClassPredicate, ...],
    tuple[OrbitClassBoundaryMargin, ...],
]:
    """Classify small-body osculating elements against JPL SBDB boundary criteria."""
    if elements.shape == OrbitShape.PARABOLIC:
        margin = OrbitClassBoundaryMargin(
            parameter="e",
            value=elements.eccentricity,
            operator="==",
            boundary=1.0,
            signed_difference=PARABOLIC_E_TOL - abs(elements.eccentricity - 1.0),
            unit="dimensionless",
        )
        pred = OrbitClassPredicate(
            code=OrbitClassCode.PAA,
            conditions=(margin,),
            matched=True,
        )
        return (
            OrbitClassCode.PAA,
            JPL_ORBIT_CLASS_TITLES[OrbitClassCode.PAA],
            (pred,),
            (margin,),
        )

    if elements.shape == OrbitShape.HYPERBOLIC:
        margin = OrbitClassBoundaryMargin(
            parameter="e",
            value=elements.eccentricity,
            operator=">",
            boundary=1.0 + PARABOLIC_E_TOL,
            signed_difference=elements.eccentricity - (1.0 + PARABOLIC_E_TOL),
            unit="dimensionless",
        )
        pred = OrbitClassPredicate(
            code=OrbitClassCode.HYA,
            conditions=(margin,),
            matched=True,
        )
        return (
            OrbitClassCode.HYA,
            JPL_ORBIT_CLASS_TITLES[OrbitClassCode.HYA],
            (pred,),
            (margin,),
        )

    a = elements.semi_major_axis_au
    e = elements.eccentricity
    q = elements.pericenter_distance_au
    Q = elements.apocenter_distance_au

    assert a is not None
    assert Q is not None

    evaluated_predicates: list[OrbitClassPredicate] = []

    # 1. IEO: Q < 0.983 au
    ieo_cond = (
        OrbitClassBoundaryMargin(
            parameter="Q",
            value=Q,
            operator="<",
            boundary=0.983,
            signed_difference=0.983 - Q,
            unit="au",
        ),
    )
    ieo_match = Q < 0.983
    evaluated_predicates.append(
        OrbitClassPredicate(code=OrbitClassCode.IEO, conditions=ieo_cond, matched=ieo_match)
    )
    if ieo_match:
        return OrbitClassCode.IEO, JPL_ORBIT_CLASS_TITLES[OrbitClassCode.IEO], tuple(evaluated_predicates), ieo_cond

    # 2. ATE: a < 1.0 au and Q > 0.983 au
    ate_cond = (
        OrbitClassBoundaryMargin(
            parameter="a",
            value=a,
            operator="<",
            boundary=1.0,
            signed_difference=1.0 - a,
            unit="au",
        ),
        OrbitClassBoundaryMargin(
            parameter="Q",
            value=Q,
            operator=">",
            boundary=0.983,
            signed_difference=Q - 0.983,
            unit="au",
        ),
    )
    ate_match = (a < 1.0) and (Q > 0.983)
    evaluated_predicates.append(
        OrbitClassPredicate(code=OrbitClassCode.ATE, conditions=ate_cond, matched=ate_match)
    )
    if ate_match:
        return OrbitClassCode.ATE, JPL_ORBIT_CLASS_TITLES[OrbitClassCode.ATE], tuple(evaluated_predicates), ate_cond

    # 3. APO: a > 1.0 au and q < 1.017 au
    apo_cond = (
        OrbitClassBoundaryMargin(
            parameter="a",
            value=a,
            operator=">",
            boundary=1.0,
            signed_difference=a - 1.0,
            unit="au",
        ),
        OrbitClassBoundaryMargin(
            parameter="q",
            value=q,
            operator="<",
            boundary=1.017,
            signed_difference=1.017 - q,
            unit="au",
        ),
    )
    apo_match = (a > 1.0) and (q < 1.017)
    evaluated_predicates.append(
        OrbitClassPredicate(code=OrbitClassCode.APO, conditions=apo_cond, matched=apo_match)
    )
    if apo_match:
        return OrbitClassCode.APO, JPL_ORBIT_CLASS_TITLES[OrbitClassCode.APO], tuple(evaluated_predicates), apo_cond

    # 4. AMO: 1.017 au < q < 1.3 au
    amo_cond = (
        OrbitClassBoundaryMargin(
            parameter="q",
            value=q,
            operator=">",
            boundary=1.017,
            signed_difference=q - 1.017,
            unit="au",
        ),
        OrbitClassBoundaryMargin(
            parameter="q",
            value=q,
            operator="<",
            boundary=1.3,
            signed_difference=1.3 - q,
            unit="au",
        ),
    )
    amo_match = (q > 1.017) and (q < 1.3)
    evaluated_predicates.append(
        OrbitClassPredicate(code=OrbitClassCode.AMO, conditions=amo_cond, matched=amo_match)
    )
    if amo_match:
        return OrbitClassCode.AMO, JPL_ORBIT_CLASS_TITLES[OrbitClassCode.AMO], tuple(evaluated_predicates), amo_cond

    # 5. MCA: 1.3 au < q < 1.666 au and a < 3.2 au
    mca_cond = (
        OrbitClassBoundaryMargin(
            parameter="q",
            value=q,
            operator=">",
            boundary=1.3,
            signed_difference=q - 1.3,
            unit="au",
        ),
        OrbitClassBoundaryMargin(
            parameter="q",
            value=q,
            operator="<",
            boundary=1.666,
            signed_difference=1.666 - q,
            unit="au",
        ),
        OrbitClassBoundaryMargin(
            parameter="a",
            value=a,
            operator="<",
            boundary=3.2,
            signed_difference=3.2 - a,
            unit="au",
        ),
    )
    mca_match = (q > 1.3) and (q < 1.666) and (a < 3.2)
    evaluated_predicates.append(
        OrbitClassPredicate(code=OrbitClassCode.MCA, conditions=mca_cond, matched=mca_match)
    )
    if mca_match:
        return OrbitClassCode.MCA, JPL_ORBIT_CLASS_TITLES[OrbitClassCode.MCA], tuple(evaluated_predicates), mca_cond

    # 6. IMB: a < 2.0 au and q > 1.666 au
    imb_cond = (
        OrbitClassBoundaryMargin(
            parameter="a",
            value=a,
            operator="<",
            boundary=2.0,
            signed_difference=2.0 - a,
            unit="au",
        ),
        OrbitClassBoundaryMargin(
            parameter="q",
            value=q,
            operator=">",
            boundary=1.666,
            signed_difference=q - 1.666,
            unit="au",
        ),
    )
    imb_match = (a < 2.0) and (q > 1.666)
    evaluated_predicates.append(
        OrbitClassPredicate(code=OrbitClassCode.IMB, conditions=imb_cond, matched=imb_match)
    )
    if imb_match:
        return OrbitClassCode.IMB, JPL_ORBIT_CLASS_TITLES[OrbitClassCode.IMB], tuple(evaluated_predicates), imb_cond

    # 7. MBA: 2.0 au < a < 3.2 au and q > 1.666 au
    mba_cond = (
        OrbitClassBoundaryMargin(
            parameter="a",
            value=a,
            operator=">",
            boundary=2.0,
            signed_difference=a - 2.0,
            unit="au",
        ),
        OrbitClassBoundaryMargin(
            parameter="a",
            value=a,
            operator="<",
            boundary=3.2,
            signed_difference=3.2 - a,
            unit="au",
        ),
        OrbitClassBoundaryMargin(
            parameter="q",
            value=q,
            operator=">",
            boundary=1.666,
            signed_difference=q - 1.666,
            unit="au",
        ),
    )
    mba_match = (a > 2.0) and (a < 3.2) and (q > 1.666)
    evaluated_predicates.append(
        OrbitClassPredicate(code=OrbitClassCode.MBA, conditions=mba_cond, matched=mba_match)
    )
    if mba_match:
        return OrbitClassCode.MBA, JPL_ORBIT_CLASS_TITLES[OrbitClassCode.MBA], tuple(evaluated_predicates), mba_cond

    # 8. OMB: 3.2 au < a < 4.6 au
    omb_cond = (
        OrbitClassBoundaryMargin(
            parameter="a",
            value=a,
            operator=">",
            boundary=3.2,
            signed_difference=a - 3.2,
            unit="au",
        ),
        OrbitClassBoundaryMargin(
            parameter="a",
            value=a,
            operator="<",
            boundary=4.6,
            signed_difference=4.6 - a,
            unit="au",
        ),
    )
    omb_match = (a > 3.2) and (a < 4.6)
    evaluated_predicates.append(
        OrbitClassPredicate(code=OrbitClassCode.OMB, conditions=omb_cond, matched=omb_match)
    )
    if omb_match:
        return OrbitClassCode.OMB, JPL_ORBIT_CLASS_TITLES[OrbitClassCode.OMB], tuple(evaluated_predicates), omb_cond

    # 9. TJN: 4.6 au < a < 5.5 au and e < 0.3
    tjn_cond = (
        OrbitClassBoundaryMargin(
            parameter="a",
            value=a,
            operator=">",
            boundary=4.6,
            signed_difference=a - 4.6,
            unit="au",
        ),
        OrbitClassBoundaryMargin(
            parameter="a",
            value=a,
            operator="<",
            boundary=5.5,
            signed_difference=5.5 - a,
            unit="au",
        ),
        OrbitClassBoundaryMargin(
            parameter="e",
            value=e,
            operator="<",
            boundary=0.3,
            signed_difference=0.3 - e,
            unit="dimensionless",
        ),
    )
    tjn_match = (a > 4.6) and (a < 5.5) and (e < 0.3)
    evaluated_predicates.append(
        OrbitClassPredicate(code=OrbitClassCode.TJN, conditions=tjn_cond, matched=tjn_match)
    )
    if tjn_match:
        return OrbitClassCode.TJN, JPL_ORBIT_CLASS_TITLES[OrbitClassCode.TJN], tuple(evaluated_predicates), tjn_cond

    # 10. CEN: 5.5 au < a < 30.1 au
    cen_cond = (
        OrbitClassBoundaryMargin(
            parameter="a",
            value=a,
            operator=">",
            boundary=5.5,
            signed_difference=a - 5.5,
            unit="au",
        ),
        OrbitClassBoundaryMargin(
            parameter="a",
            value=a,
            operator="<",
            boundary=30.1,
            signed_difference=30.1 - a,
            unit="au",
        ),
    )
    cen_match = (a > 5.5) and (a < 30.1)
    evaluated_predicates.append(
        OrbitClassPredicate(code=OrbitClassCode.CEN, conditions=cen_cond, matched=cen_match)
    )
    if cen_match:
        return OrbitClassCode.CEN, JPL_ORBIT_CLASS_TITLES[OrbitClassCode.CEN], tuple(evaluated_predicates), cen_cond

    # 11. TNO: a > 30.1 au
    tno_cond = (
        OrbitClassBoundaryMargin(
            parameter="a",
            value=a,
            operator=">",
            boundary=30.1,
            signed_difference=a - 30.1,
            unit="au",
        ),
    )
    tno_match = a > 30.1
    evaluated_predicates.append(
        OrbitClassPredicate(code=OrbitClassCode.TNO, conditions=tno_cond, matched=tno_match)
    )
    if tno_match:
        return OrbitClassCode.TNO, JPL_ORBIT_CLASS_TITLES[OrbitClassCode.TNO], tuple(evaluated_predicates), tno_cond

    # 12. AST: Fallback
    ast_pred = OrbitClassPredicate(
        code=OrbitClassCode.AST, conditions=(), matched=True
    )
    evaluated_predicates.append(ast_pred)
    return (
        OrbitClassCode.AST,
        JPL_ORBIT_CLASS_TITLES[OrbitClassCode.AST],
        tuple(evaluated_predicates),
        (),
    )


def orbit_class(
    body: str | int,
    jd_ut: float,
    *,
    reader: KernelReader | None = None,
) -> OrbitClassResult:
    """Return the strict SBDB-style osculating asteroid orbit classification.

    Parameters
    ----------
    body : str or int
        Catalogued small body name or NAIF ID. Non-asteroids (planets, barycenters,
        the Moon, and comets) raise ``OrbitalBodyNotSupportedError``.
    jd_ut : float
        Evaluation epoch in Julian Date (UT1).
    reader : KernelReader or None
        Explicit reader instance, or active default reader if ``None``.

    Returns
    -------
    OrbitClassResult
        The matched orbit class code, JPL title, source osculating elements,
        and structured boundary margins for all evaluated predicates.
    """
    resolved = resolve_orbital_body(body)
    if resolved.kind != OrbitalBodyKind.ASTEROID:
        raise OrbitalBodyNotSupportedError(
            body=resolved.name,
            kind=resolved.kind.value,
            reason=(
                "orbit_class admits only catalogued small bodies/asteroids; "
                "comets require Tisserand parameter and period doctrine"
            ),
        )

    elements = osculating_elements(
        resolved.naif_id,
        jd_ut,
        center=OrbitalCenter.SUN,
        frame=OrbitalFrame.J2000_ECLIPTIC,
        reader=reader,
    )
    code, title, predicates, margins = _classify_osculating_elements(elements)
    return OrbitClassResult(
        body=resolved,
        epoch_tdb=elements.epoch_tdb,
        elements=elements,
        code=code,
        title=title,
        classification_policy=ORBIT_CLASS_POLICY,
        predicates=predicates,
        boundary_margins=margins,
    )


def orbit_classes_at(
    bodies: Sequence[str | int],
    jd_ut: float,
    *,
    reader: KernelReader | None = None,
) -> OrbitClassBatchResult:
    """Return SBDB osculating classifications for an ordered batch of bodies.

    Request-level validation failures (such as a non-numeric or non-finite ``jd_ut``)
    raise immediately. Individual body failures (such as an unknown body or unsupported
    body kind) are isolated into sanitized ``OrbitalErrorReceipt`` records without
    aborting the remaining batch.

    Parameters
    ----------
    bodies : Sequence[str or int]
        Ordered sequence of small body names or NAIF IDs.
    jd_ut : float
        Evaluation epoch in Julian Date (UT1).
    reader : KernelReader or None
        Explicit reader instance, or active default reader if ``None``.

    Returns
    -------
    OrbitClassBatchResult
        Container holding the verified evaluation epoch and an ordered tuple of
        ``OrbitClassBatchItem`` records matching the input sequence.
    """
    try:
        jd_ut_f = float(jd_ut)
    except (TypeError, ValueError) as exc:
        raise OrbitalInputError("jd_ut", jd_ut) from exc

    if not math.isfinite(jd_ut_f):
        raise OrbitalInputError("jd_ut", jd_ut)

    dt = _resolve_delta_t_for_ut1(jd_ut_f)
    tt = math.fsum((jd_ut_f, dt.seconds / 86400.0))
    epoch_tdb = _tt_to_tdb_with_receipt(tt).epoch_tdb
    items: list[OrbitClassBatchItem] = []

    for index, raw_body in enumerate(bodies):
        if isinstance(raw_body, str):
            input_body: str | int = raw_body
        elif isinstance(raw_body, int) and not isinstance(raw_body, bool):
            input_body = raw_body
        elif isinstance(raw_body, bool):
            input_body = bool(raw_body)
        else:
            input_body = f"{type(raw_body).__module__}.{type(raw_body).__qualname__}"

        try:
            res = orbit_class(raw_body, jd_ut_f, reader=reader)
            epoch_tdb = res.epoch_tdb
            items.append(
                OrbitClassBatchItem(
                    input_index=index,
                    input_body=input_body,
                    result=res,
                    error=None,
                )
            )
        except OrbitalError as exc:
            receipt = _sanitize_orbital_error(exc)
            items.append(
                OrbitClassBatchItem(
                    input_index=index,
                    input_body=input_body,
                    result=None,
                    error=receipt,
                )
            )
        except Exception as exc:
            receipt = _sanitize_orbital_error(exc)
            items.append(
                OrbitClassBatchItem(
                    input_index=index,
                    input_body=input_body,
                    result=None,
                    error=receipt,
                )
            )

    return OrbitClassBatchResult(
        epoch_tdb=epoch_tdb,
        items=tuple(items),
    )
