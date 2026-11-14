"""
Moira — out_of_bounds.py
The Solver of Bounds: governs out-of-bounds declination excursions for any
ephemeris-backed body.

A body is *out of bounds* when the magnitude of its geocentric apparent
declination exceeds the true obliquity of the ecliptic of date. Both terms
move: the declination with the body's own motion, the obliquity with
precession and nutation in obliquity. This module owns the bound function,
the excursion object assembled from its roots, the extremal declination
inside each excursion, and the conditioning receipt that tells a caller how
much a reported instant is worth.

Boundary: owns the bound function B(t) = |delta(t)| - epsilon(t), the scan
doctrine that brackets its roots, root refinement, culmination solving, and
window-edge semantics. Delegates apparent declination to the shared
``transits_equatorial._declination`` primitive (which routes planets,
asteroids and comets through ``planets.planet_at`` and stars through
``stars.star_at``), true obliquity to ``obliquity.true_obliquity``, and
UT1 -> TT reduction to ``_ephemeris_time._ut1_to_ephemeris_tt``. Does not own
declination parallels or contra-parallels; those remain in
``transits_equatorial``.

Public surface:
    OutOfBoundsPolicy, OutOfBoundsCrossing, OutOfBoundsCulmination,
    OutOfBoundsExcursion, OutOfBoundsScanTruth, OutOfBoundsReport,
    OutOfBoundsUnavailableError, OutOfBoundsBudgetError, find_out_of_bounds

Import-time side effects: None

External dependency assumptions:
    None (stdlib only; all astronomical content is internal to Moira)

Canon: IAU 2006 P03 mean obliquity with IAU 2000A nutation in obliquity
(via obliquity.py) defines the bound. Declination is the geocentric apparent
equatorial declination of date produced by Moira's own apparent-place
pipeline. No external engine participates in the definition or the proof.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

from ._ephemeris_time import _ut1_to_ephemeris_tt
from .constants import KM_PER_AU
from .obliquity import true_obliquity
from .spk_reader import SpkReader, get_reader


__all__ = [
    "OutOfBoundsBudgetError",
    "OutOfBoundsCrossing",
    "OutOfBoundsCulmination",
    "OutOfBoundsExcursion",
    "OutOfBoundsPolicy",
    "OutOfBoundsReport",
    "OutOfBoundsScanTruth",
    "OutOfBoundsUnavailableError",
    "UNAVAILABLE_REASONS",
    "find_out_of_bounds",
]


# ---------------------------------------------------------------------------
# Declared doctrinal constants
# ---------------------------------------------------------------------------

_SECONDS_PER_DAY: float = 86400.0
_ARCSEC_PER_DEGREE: float = 3600.0


# ---------------------------------------------------------------------------
# Policy
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class OutOfBoundsPolicy:
    """Explicit scan and solver doctrine for one out-of-bounds search.

    Every field is a declared policy choice, never an ambient default
    discovered at call time. ``angular_resolution_deg`` sets the coarse scan
    cadence against the body's own measured declination rate: the base step is
    the time the bound function needs to move that many degrees. No field is a
    per-body name lookup.
    """

    #: Degrees of bound-function travel admitted per coarse scan step.
    angular_resolution_deg: float = 1.5
    #: Inflation applied to sampled secants before they are used as a local
    #: rate bound, covering the curvature a secant cannot see.
    rate_safety_factor: float = 3.0
    #: Hard floor and ceiling on the coarse scan step, in days.
    min_step_days: float = 1.0 / 48.0
    max_step_days: float = 5.0
    #: Number of evenly spaced probes used to measure the body's rate before
    #: the scan step is chosen.
    rate_probe_count: int = 25
    #: Bisection tolerance, in days, for entry/return roots and culminations.
    solver_tolerance_days: float = 1.0e-7
    #: Central-difference half-step, in days, for declination rates.
    differentiation_step_days: float = 1.0 / 480.0
    #: Maximum recursive halvings of an unresolved coarse interval.
    max_subdivision_depth: int = 12
    #: Geocentric distance, in AU, below which an interval is refined
    #: regardless of its clearance margin.
    close_approach_distance_au: float = 0.35
    #: Fractional change in geocentric distance across one interval that
    #: forces refinement even when the clearance test passes.
    distance_change_trigger: float = 0.10
    #: Recursion depth up to which the close-approach trigger may override a
    #: passing clearance test. Beyond it the measured clearance decides. The
    #: trigger exists to buy a trustworthy secant across a close approach,
    #: which a few halvings supply; left ungated it refines to the recursion
    #: floor for as long as the body stays near, which for Venus is weeks.
    close_approach_refinement_depth: int = 4
    #: Nodes per excursion used to bracket interior declination extrema.
    culmination_probe_count: int = 17
    #: Ceiling on declination evaluations for one search, or None for no
    #: ceiling. Cost is linear in the requested span — measured at roughly
    #: 3,800 evaluations per year of lunar scan — so an unbounded span is an
    #: unbounded search. Library callers may legitimately scan centuries and so
    #: default to None; a transport layer should impose its own ceiling.
    max_declination_evaluations: int | None = None

    def __post_init__(self) -> None:
        _require_positive(self.angular_resolution_deg, "angular_resolution_deg")
        _require_positive(self.rate_safety_factor, "rate_safety_factor")
        _require_positive(self.min_step_days, "min_step_days")
        _require_positive(self.max_step_days, "max_step_days")
        _require_positive(self.solver_tolerance_days, "solver_tolerance_days")
        _require_positive(self.differentiation_step_days, "differentiation_step_days")
        _require_positive(self.close_approach_distance_au, "close_approach_distance_au")
        _require_positive(self.distance_change_trigger, "distance_change_trigger")
        if self.max_step_days < self.min_step_days:
            raise ValueError(
                "Out-of-bounds policy max_step_days must be >= min_step_days"
            )
        if self.rate_safety_factor < 1.0:
            raise ValueError(
                "Out-of-bounds policy rate_safety_factor must be >= 1.0"
            )
        if self.rate_probe_count < 3:
            raise ValueError("Out-of-bounds policy rate_probe_count must be >= 3")
        if self.culmination_probe_count < 3:
            raise ValueError(
                "Out-of-bounds policy culmination_probe_count must be >= 3"
            )
        if self.max_subdivision_depth < 0:
            raise ValueError(
                "Out-of-bounds policy max_subdivision_depth must be >= 0"
            )
        if self.close_approach_refinement_depth < 0:
            raise ValueError(
                "Out-of-bounds policy close_approach_refinement_depth "
                "must be >= 0"
            )
        if self.max_declination_evaluations is not None:
            if (
                not isinstance(self.max_declination_evaluations, int)
                or isinstance(self.max_declination_evaluations, bool)
                or self.max_declination_evaluations < 1
            ):
                raise ValueError(
                    "Out-of-bounds policy max_declination_evaluations must be "
                    "a positive integer or None"
                )


# ---------------------------------------------------------------------------
# Result vessels
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class OutOfBoundsCrossing:
    """One solved root of the bound function, with its conditioning receipt.

    ``bound_rate_deg_per_day`` is the rate of the quantity actually driven to
    zero, d/dt(|delta| - epsilon). It, not the declination rate alone, governs
    how a declination error maps onto a time error:
    ``time_sensitivity_days_per_arcsec`` states that mapping directly.
    """

    kind: str
    jd_ut: float
    declination: float
    obliquity: float
    declination_rate_deg_per_day: float
    obliquity_rate_deg_per_day: float
    bound_rate_deg_per_day: float
    time_sensitivity_days_per_arcsec: float
    achieved_tolerance_days: float
    bracket_start_jd_ut: float
    bracket_end_jd_ut: float
    conditioning: str

    @property
    def time_sensitivity_seconds_per_arcsec(self) -> float:
        """Seconds of time error per arcsecond of declination error."""

        return self.time_sensitivity_days_per_arcsec * _SECONDS_PER_DAY


@dataclass(frozen=True, slots=True)
class OutOfBoundsCulmination:
    """The extremal declination magnitude reached inside one excursion.

    Solved as a root of the signed declination rate, never read off the scan
    grid. ``at_boundary`` records that the extremum sits on a window edge
    rather than at an interior critical point, which is the normal state of a
    clipped excursion and the case a hump-assuming search gets wrong.
    """

    jd_ut: float
    declination: float
    obliquity: float
    excess_deg: float
    at_boundary: bool
    boundary_edge: str | None
    interior_critical_points: int


@dataclass(frozen=True, slots=True)
class OutOfBoundsExcursion:
    """One maximal interval on which the body is out of bounds.

    The hemisphere is constant across an excursion: |delta| > epsilon > 0
    forces delta away from zero, and delta is continuous, so its sign cannot
    change while the body is out. A clipped edge means the excursion is cut by
    the requested range, not that it begins or ends there; ``duration_hours``
    is then a lower bound and ``duration_is_lower_bound`` says so.
    """

    body: str
    hemisphere: str
    jd_start_observed: float
    jd_end_observed: float
    entry: OutOfBoundsCrossing | None
    departure: OutOfBoundsCrossing | None
    entry_clipped: bool
    departure_clipped: bool
    culmination: OutOfBoundsCulmination
    duration_hours: float
    duration_is_lower_bound: bool

    @property
    def is_complete(self) -> bool:
        """True when both edges were solved inside the requested range."""

        return self.entry is not None and self.departure is not None


@dataclass(frozen=True, slots=True)
class OutOfBoundsScanTruth:
    """Inspectable record of how the scan was chosen and what it resolved.

    ``resolved_amplitude_floor_deg`` is the shallowest excursion the coarse
    grid could in principle have cleared on its own, before refinement. It is
    reported so a caller can judge the scan, not as a guarantee.
    ``unresolved_intervals`` counts intervals that hit the subdivision depth
    limit without clearing; a nonzero count is a disclosed gap in capture.
    """

    coarse_step_days: float
    measured_max_rate_deg_per_day: float
    measured_median_rate_deg_per_day: float
    rate_bound_deg_per_day: float
    resolved_amplitude_floor_deg: float
    coarse_node_count: int
    refined_interval_count: int
    unresolved_intervals: int
    declination_evaluations: int
    policy: OutOfBoundsPolicy


@dataclass(frozen=True, slots=True)
class OutOfBoundsReport:
    """Every out-of-bounds excursion of one body across one requested range."""

    body: str
    resolved_name: str
    resolved_kind: str
    jd_start: float
    jd_end: float
    excursions: tuple[OutOfBoundsExcursion, ...]
    out_of_bounds_at_start: bool
    out_of_bounds_at_end: bool
    scan_truth: OutOfBoundsScanTruth
    obliquity_at_start: float
    obliquity_at_end: float

    @property
    def excursion_count(self) -> int:
        """Number of excursions found in the requested range."""

        return len(self.excursions)


#: Stable machine reasons an out-of-bounds answer can be unavailable. They
#: exist so a transport layer can map the cause to its own status without
#: parsing prose.
UNAVAILABLE_REASONS: frozenset[str] = frozenset(
    {"ephemeris_coverage", "body_unresolved"}
)

_UNAVAILABLE_MESSAGES: dict[str, str] = {
    "ephemeris_coverage": (
        "the body's ephemeris does not cover the requested range"
    ),
    "body_unresolved": "the body specification could not be resolved",
}


class OutOfBoundsUnavailableError(ValueError):
    """Vessel: signals that no out-of-bounds answer exists for the request.

    Raised when the body cannot be resolved, or when its ephemeris does not
    cover the requested range. An uncovered range never degrades to an empty
    excursion list, because an empty list is itself an astrological claim:
    'this body went nowhere out of bounds' is not the same statement as 'this
    body cannot be computed here'.

    ``reason`` is one of :data:`UNAVAILABLE_REASONS`, so a transport layer can
    separate a bad request from an absent resource without reading prose.
    """

    def __init__(self, body: str, reason: str, detail: str = "") -> None:
        if reason not in UNAVAILABLE_REASONS:
            raise ValueError(
                f"Out-of-bounds unavailable reason must be one of "
                f"{sorted(UNAVAILABLE_REASONS)}, got {reason!r}"
            )
        self.body = body
        self.reason = reason
        self.detail = detail
        message = (
            f"Out-of-bounds search unavailable for {body!r}: "
            f"{_UNAVAILABLE_MESSAGES[reason]}"
        )
        if detail:
            message = f"{message} ({detail})"
        super().__init__(message)


class OutOfBoundsBudgetError(ValueError):
    """Vessel: signals that a search exceeded its declared evaluation budget.

    Raised rather than returning a partial excursion list, because a truncated
    search is indistinguishable from a quiet one: "no further excursions" and
    "I stopped looking" are different statements. Carries the budget, the count
    reached, and the stage, so a caller can narrow the window or raise the
    ceiling deliberately.
    """

    def __init__(self, body: str, budget: int, evaluations: int, stage: str) -> None:
        self.body = body
        self.budget = budget
        self.evaluations = evaluations
        self.stage = stage
        super().__init__(
            f"Out-of-bounds search for {body!r} exceeded its evaluation budget "
            f"of {budget} declination evaluations at stage {stage!r} "
            f"({evaluations} reached). Narrow the window or raise "
            "max_declination_evaluations."
        )


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

def _require_positive(value: float, label: str) -> None:
    """Fail clearly when a required positive scalar is invalid."""

    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"Out-of-bounds policy {label} must be a number")
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"Out-of-bounds policy {label} must be positive and finite")


def _require_non_empty_body(body: str) -> None:
    if not isinstance(body, str) or not body.strip():
        raise ValueError("Out-of-bounds input body must be a non-empty string")


def _validate_range(jd_start: float, jd_end: float) -> None:
    for value, label in ((jd_start, "jd_start"), (jd_end, "jd_end")):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(f"Out-of-bounds input {label} must be a number")
        if not math.isfinite(value):
            raise ValueError(f"Out-of-bounds input {label} must be finite")
    if jd_end <= jd_start:
        raise ValueError("Out-of-bounds input range must be strictly increasing")


def _validate_policy(policy: OutOfBoundsPolicy | None) -> OutOfBoundsPolicy:
    if policy is None:
        return OutOfBoundsPolicy()
    if not isinstance(policy, OutOfBoundsPolicy):
        raise ValueError(
            "Out-of-bounds policy must be an OutOfBoundsPolicy"
        )
    return policy


# ---------------------------------------------------------------------------
# Body resolution
# ---------------------------------------------------------------------------

def _coverage_error_types() -> tuple[type[BaseException], ...]:
    """Collect the ephemeris coverage error types to treat as unavailable."""

    from .spk_reader import OutOfRangeError as _SpkOutOfRange

    types: list[type[BaseException]] = [_SpkOutOfRange]
    try:
        from ._spk_body_kernel import OutOfRangeError as _BodyOutOfRange
    except ImportError:  # pragma: no cover - module is packaged with the engine
        pass
    else:
        types.append(_BodyOutOfRange)
    return tuple(types)


def _resolve_body_kind(body: str) -> tuple[str, str]:
    """Classify a body name into (resolved_name, resolved_kind).

    Planets and points resolve first; small bodies then resolve through the
    shared small-body identity registry, which owns the asteroid/comet
    family policy and the ``asteroid:`` / ``comet:`` qualifier rules. A name
    that resolves to neither is reported as a star specification, which the
    shared declination primitive will accept or reject.
    """

    from .constants import Body
    from .small_body_identity import resolve_small_body_identity

    name = body.strip()
    if name in Body.ALL_PLANETS:
        return name, "planet"
    identity = resolve_small_body_identity(name)
    if identity is not None:
        return identity.canonical_name, identity.family
    return name, "star"


# ---------------------------------------------------------------------------
# The bound function
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class _BoundField:
    """Evaluator for the bound function B(t) = |delta(t)| - epsilon(t).

    RITE: The Keeper of the Bound

    THEOREM: Governs the single scalar field whose sign decides whether a body
    is out of bounds, and whose roots are the entries and returns.

    RITE OF PURPOSE:
        Holds one body, one reader and one evaluation cache so that a scan,
        its refinements and its root solvers all read exactly the same field.
        Counts its own evaluations so the scan can report honest cost.

    LAW OF OPERATION:
        Responsibilities:
            - Evaluate declination, obliquity, bound value and distance at a
              requested UT1 Julian Day, memoised per instant
            - Translate ephemeris coverage failures into an explicit
              unavailable rather than a silent gap
            - Provide central-difference rates for declination and obliquity
        Non-responsibilities:
            - Choosing a scan step, bracketing roots, or assembling excursions
            - Owning apparent-place or obliquity models, which are delegated
        Dependencies:
            - transits_equatorial._declination for apparent declination
            - obliquity.true_obliquity for the bound
            - _ephemeris_time._ut1_to_ephemeris_tt for the TT reduction

    Canon: None (assembly of Moira-owned primitives; the models belong to
    obliquity.py and the apparent-place pipeline)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.out_of_bounds._BoundField",
      "risk": "medium",
      "api": {"frozen": [], "internal": ["sample", "declination_rate", "obliquity_rate", "evaluations"]},
      "state": {"mutable": true, "owners": ["_BoundField instance"]},
      "effects": {"signals_emitted": [], "io": ["reads the active SPK reader"]},
      "concurrency": {"thread": "request_local", "cross_thread_calls": "forbidden", "owner_thread_only_mutation": true},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    body: str
    reader: SpkReader
    differentiation_step_days: float
    max_evaluations: int | None = None
    stage: str = "scan"
    _cache: dict[float, tuple[float, float, float, float]] = field(default_factory=dict)
    evaluations: int = 0

    def sample(self, jd: float) -> tuple[float, float, float, float]:
        """Return (declination, obliquity, bound, distance_au) at one instant."""

        cached = self._cache.get(jd)
        if cached is not None:
            return cached
        self._charge_evaluation()
        from .transits_equatorial import _declination

        coverage_errors = _coverage_error_types()
        try:
            declination = _declination(self.body, jd, self.reader)
            distance_km = _geocentric_distance_km(self.body, jd, self.reader)
        except coverage_errors as exc:
            raise OutOfBoundsUnavailableError(
                self.body,
                "ephemeris_coverage",
                f"JD(UT1) {jd:.6f}: {exc}",
            ) from exc
        jd_tt = _ut1_to_ephemeris_tt(jd, self.reader)
        obliquity = true_obliquity(jd_tt)
        distance_au = (
            distance_km / KM_PER_AU if distance_km is not None else math.inf
        )
        result = (declination, obliquity, abs(declination) - obliquity, distance_au)
        self._cache[jd] = result
        self.evaluations += 1
        return result

    def _charge_evaluation(self) -> None:
        """Admit one uncached evaluation against the declared budget.

        Separate from ``sample`` so a substituted field evaluator shares the
        same accounting. A cached instant is free, because the budget exists to
        bound real ephemeris work, not repeated reads of one instant.
        """

        if (
            self.max_evaluations is not None
            and self.evaluations >= self.max_evaluations
        ):
            raise OutOfBoundsBudgetError(
                self.body, self.max_evaluations, self.evaluations, self.stage
            )

    def bound(self, jd: float) -> float:
        """Return B(t) = |delta(t)| - epsilon(t) at one instant."""

        return self.sample(jd)[2]

    def declination_rate(self, jd: float) -> float:
        """Central-difference d(delta)/dt in degrees per day."""

        h = self.differentiation_step_days
        return (self.sample(jd + h)[0] - self.sample(jd - h)[0]) / (2.0 * h)

    def obliquity_rate(self, jd: float) -> float:
        """Central-difference d(epsilon)/dt in degrees per day."""

        h = self.differentiation_step_days
        return (self.sample(jd + h)[1] - self.sample(jd - h)[1]) / (2.0 * h)


def _geocentric_distance_km(body: str, jd: float, reader: SpkReader) -> float | None:
    """Geocentric distance in km, or None when the spec carries no distance.

    Stars and fixed declination specifications have no usable distance; the
    close-approach refinement trigger simply does not apply to them.
    """

    from .constants import Body
    from .planets import planet_at

    name = body.strip()
    if name in Body.ALL_PLANETS:
        return float(planet_at(name, jd, reader=reader).distance)
    from .small_body_identity import resolve_small_body_identity

    if resolve_small_body_identity(name) is not None:
        return float(planet_at(name, jd, reader=reader).distance)
    return None


# ---------------------------------------------------------------------------
# Scan step derivation — measured motion, never a name
# ---------------------------------------------------------------------------

def _measure_rates(
    field_: _BoundField,
    jd_start: float,
    jd_end: float,
    policy: OutOfBoundsPolicy,
) -> tuple[float, float]:
    """Measure the bound function's secant rates across the whole range.

    Returns ``(max_rate, median_rate)`` in degrees per day. The scan step is
    derived from these measurements and from nothing else: no body name, no
    speed table, no orbital-class lookup participates.
    """

    count = max(3, int(policy.rate_probe_count))
    span = jd_end - jd_start
    nodes = [jd_start + span * index / (count - 1) for index in range(count)]
    values = [field_.bound(node) for node in nodes]
    rates = [
        abs(values[index + 1] - values[index]) / (nodes[index + 1] - nodes[index])
        for index in range(count - 1)
    ]
    rates.sort()
    max_rate = rates[-1] if rates else 0.0
    median_rate = rates[len(rates) // 2] if rates else 0.0
    return max_rate, median_rate


def _derive_coarse_step(
    max_rate: float,
    median_rate: float,
    jd_start: float,
    jd_end: float,
    policy: OutOfBoundsPolicy,
) -> float:
    """Choose the coarse scan step from measured motion.

    The step is the time the bound function needs to travel
    ``angular_resolution_deg`` at the body's own representative rate. The
    representative rate is the larger of the median secant and a damped share
    of the maximum, so one close approach cannot force a punitive cadence
    across a decade while a genuinely fast body still gets a fast scan. The
    close-approach interval is then recovered by local refinement, not by the
    base cadence.
    """

    representative = max(median_rate, max_rate / 8.0)
    if representative <= 0.0:
        step = policy.max_step_days
    else:
        step = policy.angular_resolution_deg / representative
    step = min(step, policy.max_step_days)
    step = max(step, policy.min_step_days)
    span = jd_end - jd_start
    return min(step, span)


# ---------------------------------------------------------------------------
# Scan — bracket every sign change, refine every interval that is not
# provably clear
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class _ScanOutcome:
    """Brackets and refinement bookkeeping produced by one scan."""

    brackets: list[tuple[float, float]]
    refined_intervals: int
    unresolved_intervals: int


def _interval_is_clear(
    bound_lo: float,
    bound_hi: float,
    rate_bound: float,
    width: float,
) -> bool:
    """Clearance lemma: can this interval hold no root of the bound function?

    If ``|dB/dt| <= R`` on ``[t0, t1]`` of width ``h``, then every instant in
    the interval lies within ``h/2`` of one endpoint or the other, so

        ``|B(t) - B(t_nearer)| <= R * h / 2``.

    Two consequences, and the test is symmetric in them:

    * both endpoints at or below ``-R*h/2`` means ``B <= 0`` throughout, so no
      excursion begins inside;
    * both endpoints at or above ``+R*h/2`` means ``B >= 0`` throughout, so no
      excursion ends inside.

    The second branch matters as much as the first. Without it the interior of
    every excursion — where ``B`` is comfortably positive and nothing is
    happening — fails the test and is subdivided to the recursion floor,
    which both slows the scan and reports hundreds of phantom unresolved
    intervals.

    The guarantee is exactly as good as the rate bound ``R``, which is
    measured and declared, not assumed.
    """

    margin = rate_bound * width / 2.0
    if bound_lo <= -margin and bound_hi <= -margin:
        return True
    return bound_lo >= margin and bound_hi >= margin


def _needs_close_approach_refinement(
    distance_lo: float,
    distance_hi: float,
    policy: OutOfBoundsPolicy,
) -> bool:
    """Force refinement where sampled secants cannot see the body's motion.

    A secant across an interval reports almost no motion when a close
    approach happens entirely between its endpoints. Geocentric distance is
    the cheap physical witness of that case: a near or rapidly changing
    distance refines the interval regardless of its clearance margin.
    """

    if not math.isfinite(distance_lo) or not math.isfinite(distance_hi):
        return False
    nearest = min(distance_lo, distance_hi)
    if nearest <= policy.close_approach_distance_au:
        return True
    farthest = max(distance_lo, distance_hi)
    if farthest <= 0.0:
        return False
    return (farthest - nearest) / farthest >= policy.distance_change_trigger


def _local_rate_bound(
    jd_lo: float,
    jd_hi: float,
    bound_lo: float,
    bound_hi: float,
    policy: OutOfBoundsPolicy,
) -> float:
    """Local rate bound for the clearance test.

    The secant across the interval is inflated by ``rate_safety_factor`` to
    cover the curvature a secant cannot see. As an interval is halved its
    secant converges on the true derivative, so the bound tightens with the
    refinement that uses it, and the clearance test becomes progressively
    better justified rather than progressively more hopeful.

    A universal kinematic ceiling such as ``v_max / r`` is rigorous but
    useless here: for the Moon it is some eighty times the body's real
    relative speed, so it would make almost every interval unclearable and
    turn the scan into a uniform fine grid. The motion a secant genuinely
    cannot see is a close approach, and that case is caught by its own
    distance-based trigger in ``_needs_close_approach_refinement`` instead.
    """

    width = jd_hi - jd_lo
    secant = abs(bound_hi - bound_lo) / width if width > 0.0 else 0.0
    return max(secant * policy.rate_safety_factor, 1.0e-9)


def _scan_for_brackets(
    field_: _BoundField,
    jd_start: float,
    jd_end: float,
    coarse_step: float,
    policy: OutOfBoundsPolicy,
) -> _ScanOutcome:
    """Bracket every root of the bound function in the requested range."""

    brackets: list[tuple[float, float]] = []
    refined = 0
    unresolved = 0

    def _walk(jd_lo: float, jd_hi: float, depth: int) -> None:
        nonlocal refined, unresolved
        _, _, bound_lo, distance_lo = field_.sample(jd_lo)
        _, _, bound_hi, distance_hi = field_.sample(jd_hi)
        if bound_lo == 0.0 or bound_hi == 0.0:
            # A sampled tangency is not a sign change. Refine so the solver
            # sees whichever side genuinely carries the excursion.
            pass
        elif bound_lo * bound_hi < 0.0:
            brackets.append((jd_lo, jd_hi))
            return
        width = jd_hi - jd_lo
        rate_bound = _local_rate_bound(
            jd_lo, jd_hi, bound_lo, bound_hi, policy
        )
        clear = _interval_is_clear(bound_lo, bound_hi, rate_bound, width)
        forced = depth < policy.close_approach_refinement_depth and (
            _needs_close_approach_refinement(distance_lo, distance_hi, policy)
        )
        if clear and not forced:
            return
        if depth >= policy.max_subdivision_depth or width <= policy.min_step_days:
            if not clear:
                unresolved += 1
            return
        refined += 1
        jd_mid = (jd_lo + jd_hi) / 2.0
        _walk(jd_lo, jd_mid, depth + 1)
        _walk(jd_mid, jd_hi, depth + 1)

    node = jd_start
    node_count = 0
    while node < jd_end:
        node_next = min(node + coarse_step, jd_end)
        if node_next <= node:
            break
        _walk(node, node_next, 0)
        node_count += 1
        node = node_next

    brackets.sort()
    return _ScanOutcome(
        brackets=brackets,
        refined_intervals=refined,
        unresolved_intervals=unresolved,
    )


# ---------------------------------------------------------------------------
# Root refinement
# ---------------------------------------------------------------------------

def _bisect_bound_root(
    field_: _BoundField,
    jd_lo: float,
    jd_hi: float,
    tolerance_days: float,
) -> tuple[float, float, float]:
    """Bisect one bracketed root of the bound function.

    Returns ``(jd_root, bracket_lo, bracket_hi)``; the final bracket width is
    the achieved tolerance, reported on the crossing rather than assumed from
    the requested tolerance.
    """

    low, high = jd_lo, jd_hi
    value_low = field_.bound(low)
    if value_low == 0.0:
        return low, low, low
    for _ in range(200):
        if high - low <= tolerance_days:
            break
        middle = (low + high) / 2.0
        value_middle = field_.bound(middle)
        if value_middle == 0.0:
            return middle, middle, middle
        if value_low * value_middle < 0.0:
            high = middle
        else:
            low = middle
            value_low = value_middle
    return (low + high) / 2.0, low, high


def _classify_conditioning(bound_rate_deg_per_day: float) -> str:
    """Name how well-posed a crossing instant is, from its own rate.

    The thresholds are stated in time cost per arcsecond of declination
    error, which is the quantity a caller actually needs: 'well_posed' keeps
    an arcsecond under a minute, 'sensitive' under an hour, 'ill_conditioned'
    beyond it.
    """

    rate = abs(bound_rate_deg_per_day)
    if rate <= 0.0:
        return "degenerate"
    seconds_per_arcsec = _SECONDS_PER_DAY / (rate * _ARCSEC_PER_DEGREE)
    if seconds_per_arcsec <= 60.0:
        return "well_posed"
    if seconds_per_arcsec <= 3600.0:
        return "sensitive"
    return "ill_conditioned"


def _build_crossing(
    field_: _BoundField,
    kind: str,
    jd_root: float,
    bracket_lo: float,
    bracket_hi: float,
) -> OutOfBoundsCrossing:
    """Assemble one crossing with its rates and conditioning receipt."""

    declination, obliquity, _, _ = field_.sample(jd_root)
    declination_rate = field_.declination_rate(jd_root)
    obliquity_rate = field_.obliquity_rate(jd_root)
    hemisphere_sign = 1.0 if declination >= 0.0 else -1.0
    bound_rate = hemisphere_sign * declination_rate - obliquity_rate
    arcsec_per_day = abs(bound_rate) * _ARCSEC_PER_DEGREE
    sensitivity = 1.0 / arcsec_per_day if arcsec_per_day > 0.0 else math.inf
    return OutOfBoundsCrossing(
        kind=kind,
        jd_ut=jd_root,
        declination=declination,
        obliquity=obliquity,
        declination_rate_deg_per_day=declination_rate,
        obliquity_rate_deg_per_day=obliquity_rate,
        bound_rate_deg_per_day=bound_rate,
        time_sensitivity_days_per_arcsec=sensitivity,
        achieved_tolerance_days=max(0.0, bracket_hi - bracket_lo),
        bracket_start_jd_ut=bracket_lo,
        bracket_end_jd_ut=bracket_hi,
        conditioning=_classify_conditioning(bound_rate),
    )


# ---------------------------------------------------------------------------
# Culmination — the extremum, solved as a root of the declination rate
# ---------------------------------------------------------------------------

def _solve_culmination(
    field_: _BoundField,
    jd_lo: float,
    jd_hi: float,
    hemisphere_sign: float,
    entry_clipped: bool,
    departure_clipped: bool,
    policy: OutOfBoundsPolicy,
) -> OutOfBoundsCulmination:
    """Find the extremal |delta| inside one excursion.

    The extremum is a root of d|delta|/dt = sign(delta) * d(delta)/dt, found by
    bracketing sign changes of that signed rate on a sub-grid and bisecting
    each one. Every interior critical point is evaluated, so a double-peaked
    excursion reports its true maximum rather than the first hump found.

    A hump-assuming search such as a ternary search is wrong here. When an
    excursion is clipped by the requested range the body may already be past
    its turn, the maximum then sits on the window edge, and a ternary search
    walks away from it and returns a value below the grid maximum. Both
    endpoints are therefore always candidates, and ``at_boundary`` records
    when one of them wins.
    """

    count = max(3, int(policy.culmination_probe_count))
    nodes = [
        jd_lo + (jd_hi - jd_lo) * index / (count - 1) for index in range(count)
    ]
    signed_rates = [
        hemisphere_sign * field_.declination_rate(node) for node in nodes
    ]

    candidates: list[float] = [jd_lo, jd_hi]
    interior_critical_points = 0
    for index in range(count - 1):
        if signed_rates[index] * signed_rates[index + 1] >= 0.0:
            continue
        low, high = nodes[index], nodes[index + 1]
        rate_low = signed_rates[index]
        for _ in range(100):
            if high - low <= policy.solver_tolerance_days:
                break
            middle = (low + high) / 2.0
            rate_middle = hemisphere_sign * field_.declination_rate(middle)
            if rate_low * rate_middle < 0.0:
                high = middle
            else:
                low = middle
                rate_low = rate_middle
        candidates.append((low + high) / 2.0)
        interior_critical_points += 1

    best_jd = max(candidates, key=lambda jd: abs(field_.sample(jd)[0]))
    declination, obliquity, bound_value, _ = field_.sample(best_jd)
    at_start = best_jd <= jd_lo + policy.solver_tolerance_days
    at_end = best_jd >= jd_hi - policy.solver_tolerance_days
    at_boundary = at_start or at_end
    boundary_edge: str | None = None
    if at_start:
        boundary_edge = "range_start" if entry_clipped else "excursion_entry"
    elif at_end:
        boundary_edge = "range_end" if departure_clipped else "excursion_departure"
    return OutOfBoundsCulmination(
        jd_ut=best_jd,
        declination=declination,
        obliquity=obliquity,
        excess_deg=bound_value,
        at_boundary=at_boundary,
        boundary_edge=boundary_edge,
        interior_critical_points=interior_critical_points,
    )


# ---------------------------------------------------------------------------
# Excursion assembly
# ---------------------------------------------------------------------------

def _assemble_excursions(
    field_: _BoundField,
    body: str,
    jd_start: float,
    jd_end: float,
    roots: list[OutOfBoundsCrossing],
    out_at_start: bool,
    policy: OutOfBoundsPolicy,
) -> tuple[OutOfBoundsExcursion, ...]:
    """Pair solved roots into excursions, honouring both window edges.

    Assembly doctrine: the roots partition the range into alternating in- and
    out-of-bounds intervals. The state at ``jd_start`` fixes the phase, so an
    excursion that was already under way at the range start opens with a
    clipped entry, and one still under way at the range end closes with a
    clipped departure. No root is invented for a clipped edge.
    """

    excursions: list[OutOfBoundsExcursion] = []
    pending_entry: OutOfBoundsCrossing | None = None
    pending_entry_clipped = False
    pending_start = jd_start
    inside = out_at_start

    def _close(
        departure: OutOfBoundsCrossing | None,
        jd_end_observed: float,
        departure_clipped: bool,
    ) -> None:
        declination_mid = field_.sample(
            (pending_start + jd_end_observed) / 2.0
        )[0]
        hemisphere_sign = 1.0 if declination_mid >= 0.0 else -1.0
        culmination = _solve_culmination(
            field_,
            pending_start,
            jd_end_observed,
            hemisphere_sign,
            pending_entry_clipped,
            departure_clipped,
            policy,
        )
        duration_hours = (jd_end_observed - pending_start) * 24.0
        excursions.append(
            OutOfBoundsExcursion(
                body=body,
                hemisphere="north" if hemisphere_sign > 0.0 else "south",
                jd_start_observed=pending_start,
                jd_end_observed=jd_end_observed,
                entry=pending_entry,
                departure=departure,
                entry_clipped=pending_entry_clipped,
                departure_clipped=departure_clipped,
                culmination=culmination,
                duration_hours=duration_hours,
                duration_is_lower_bound=pending_entry_clipped or departure_clipped,
            )
        )

    if inside:
        pending_entry = None
        pending_entry_clipped = True
        pending_start = jd_start

    for root in roots:
        if inside:
            _close(replace(root, kind="departure"), root.jd_ut, False)
            inside = False
            pending_entry = None
            pending_entry_clipped = False
        else:
            pending_entry = replace(root, kind="entry")
            pending_entry_clipped = False
            pending_start = root.jd_ut
            inside = True

    if inside:
        _close(None, jd_end, True)

    return tuple(excursions)


# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------

def find_out_of_bounds(
    body: str,
    jd_start: float,
    jd_end: float,
    *,
    reader: SpkReader | None = None,
    policy: OutOfBoundsPolicy | None = None,
) -> OutOfBoundsReport:
    """
    Find every out-of-bounds declination excursion of one body in a range.

    A body is out of bounds when ``|delta(t)| > epsilon(t)``, where ``delta``
    is its geocentric apparent declination of date and ``epsilon`` is the true
    obliquity of date. Both move, so entries and returns are roots of
    ``|delta(t)| - epsilon(t)`` and not of ``|delta(t)| - 23.4``. Within each
    excursion the extremal declination is solved as a root of the declination
    rate, never read off the scan grid.

    Every crossing carries the declination rate, the obliquity rate, the rate
    of the bound function itself, and the tolerance the solver actually
    achieved. A grazing crossing is genuinely ill-conditioned: the time error
    is the declination error divided by the crossing rate, and that rate spans
    more than two orders of magnitude between the Moon and Pluto. Without the
    rate, a printed instant cannot be judged.

    The scan step is derived from the body's own measured bound-function rate,
    never from its name, so an asteroid or comet is scanned at a cadence
    matched to its motion. Intervals that are not provably clear of an
    excursion are refined recursively, and intervals near or across a close
    approach are refined regardless of their clearance margin.

    Args:
        body: Planet or point name, or a small-body name resolved through the
            shared small-body identity registry, including family-qualified
            ``asteroid:Name`` and ``comet:Name`` forms.
        jd_start: Range start, Julian Day (UT1).
        jd_end: Range end, Julian Day (UT1); must exceed ``jd_start``.
        reader: Active kernel reader; the ambient reader context when omitted.
        policy: Explicit scan and solver doctrine; defaults when omitted.

    Returns:
        An ``OutOfBoundsReport`` holding every excursion, the state at both
        window edges, and the scan truth describing how the search was run.

    Raises:
        ValueError: If any input or policy field is invalid.
        OutOfBoundsBudgetError: If the search exceeds
            ``policy.max_declination_evaluations``, when one is declared. The
            search raises rather than returning a truncated excursion list.
        OutOfBoundsUnavailableError: If the body cannot be resolved, or its
            ephemeris does not cover the requested range. An uncovered range
            never degrades to an empty excursion list.

    Side effects:
        Reads the active ephemeris kernels through the supplied reader.
    """
    _require_non_empty_body(body)
    _validate_range(jd_start, jd_end)
    resolved_policy = _validate_policy(policy)
    if reader is None:
        reader = get_reader()

    resolved_name, resolved_kind = _resolve_body_kind(body)
    field_ = _BoundField(
        body=body,
        reader=reader,
        differentiation_step_days=resolved_policy.differentiation_step_days,
        max_evaluations=resolved_policy.max_declination_evaluations,
        stage="edge_probe",
    )

    try:
        _, obliquity_at_start, bound_at_start, _ = field_.sample(jd_start)
        _, obliquity_at_end, bound_at_end, _ = field_.sample(jd_end)
    except OutOfBoundsUnavailableError:
        raise
    except ValueError as exc:
        raise OutOfBoundsUnavailableError(
            body, "body_unresolved", str(exc)
        ) from exc

    field_.stage = "rate_measurement"
    max_rate, median_rate = _measure_rates(
        field_, jd_start, jd_end, resolved_policy
    )
    coarse_step = _derive_coarse_step(
        max_rate, median_rate, jd_start, jd_end, resolved_policy
    )
    field_.stage = "scan"
    outcome = _scan_for_brackets(
        field_, jd_start, jd_end, coarse_step, resolved_policy
    )

    field_.stage = "root_refinement"
    roots: list[OutOfBoundsCrossing] = []
    for bracket_lo, bracket_hi in outcome.brackets:
        jd_root, final_lo, final_hi = _bisect_bound_root(
            field_, bracket_lo, bracket_hi, resolved_policy.solver_tolerance_days
        )
        kind = "departure" if field_.bound(bracket_lo) > 0.0 else "entry"
        roots.append(_build_crossing(field_, kind, jd_root, final_lo, final_hi))
    roots.sort(key=lambda crossing: crossing.jd_ut)

    field_.stage = "excursion_assembly"
    excursions = _assemble_excursions(
        field_,
        body,
        jd_start,
        jd_end,
        roots,
        bound_at_start > 0.0,
        resolved_policy,
    )

    rate_bound = max(max_rate * resolved_policy.rate_safety_factor, 1.0e-9)
    node_count = max(1, math.ceil((jd_end - jd_start) / coarse_step))
    scan_truth = OutOfBoundsScanTruth(
        coarse_step_days=coarse_step,
        measured_max_rate_deg_per_day=max_rate,
        measured_median_rate_deg_per_day=median_rate,
        rate_bound_deg_per_day=rate_bound,
        resolved_amplitude_floor_deg=rate_bound * coarse_step / 2.0,
        coarse_node_count=node_count,
        refined_interval_count=outcome.refined_intervals,
        unresolved_intervals=outcome.unresolved_intervals,
        declination_evaluations=field_.evaluations,
        policy=resolved_policy,
    )

    return OutOfBoundsReport(
        body=body,
        resolved_name=resolved_name,
        resolved_kind=resolved_kind,
        jd_start=jd_start,
        jd_end=jd_end,
        excursions=excursions,
        out_of_bounds_at_start=bound_at_start > 0.0,
        out_of_bounds_at_end=bound_at_end > 0.0,
        scan_truth=scan_truth,
        obliquity_at_start=obliquity_at_start,
        obliquity_at_end=obliquity_at_end,
    )
