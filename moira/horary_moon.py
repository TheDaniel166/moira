"""Lilly P3 lunar evidence and explicitly selected VOC candidates.

Authority: Christian Astrology (1647), pp.107-112,122,124 and the collated
P3 decisions M01-M07. Python owns doctrine and typed evidence. Existing
planetary reduction and the private bounded contact scanner own their admitted
numerical work. This additive module does not alter horary/perfection v1 or
the generic VOC surface. Finite scan completion is not interval certification
of every possible unsampled oscillation.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
import math

from ._strenum import StrEnum
from ._fixed_aspect_search import _FixedScanPolicy, _scan_fixed_aspects, _bisect_scalar
from .horary_reception import LillySnapshotContext, lilly_orb_evidence


__all__ = [
    "LillyP3State", "LillyVOCDefinition", "LillyCoverageState", "LillyTimeInterval",
    "LillyMoonCoverage", "LillyMoonProvenance", "LillyMoonContact", "LillyMoonIngress",
    "LillyApplicationEpisode", "LillyMoonTrace", "LillyVOCResult", "LillyMoonContactGroup",
    "LillyMoonSequence", "LillyMoonSearchPolicy", "LillyMoonScanReceipt", "lilly_void_of_course",
    "lilly_moon_sequence", "trace_lilly_moon", "lilly_moon_at",
]

_PARTNERS = ("Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")
_TARGETS = (0., 60., 90., 120., 180., 240., 270., 300.)
_PROFILE = "lilly_1647_moon_considerations_v1"


class LillyP3State(StrEnum):
    """A bounded proposition, including an explicitly unmet applicability premise."""
    PRESENT = "present"
    ABSENT = "absent"
    NOT_EVALUABLE = "not_evaluable"
    NOT_APPLICABLE = "not_applicable"


class LillyVOCDefinition(StrEnum):
    """Two operational readings; neither is a default or unique historical claim."""
    EXACT_BEFORE_INGRESS = "exact_before_ingress_candidate"
    APPLICATION_IN_REMAINING_SIGN = "application_in_remaining_sign_candidate"


class LillyCoverageState(StrEnum):
    """Completion of a declared finite interval, separately for each evidence class."""
    COMPLETE = "complete"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


def _finite(value, name):
    if type(value) not in (int, float):
        raise TypeError(f"{name} must be a finite number, not a boolean")
    try:
        value = float(value)
    except OverflowError as exc:
        raise ValueError(f"{name} must be finite") from exc
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    return value


def _text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a nonempty string")


def _strings(value, name):
    if not isinstance(value, tuple):
        raise TypeError(f"{name} must be an immutable tuple")
    for item in value:
        _text(item, name)
    if len(set(value)) != len(value):
        raise ValueError(f"{name} must be distinct")


def _angle(value):
    value = _finite(value, "longitude/angle")
    if not 0 <= value < 360:
        raise ValueError("longitude/angle must be in [0,360)")
    return value


def _context(value, *, dated=False):
    if not isinstance(value, LillySnapshotContext):
        raise TypeError("an explicit Lilly snapshot context is required")
    if dated and value.jd_ut is None:
        raise ValueError("lunar trace needs an explicit query jd_ut (UT1)")


@dataclass(frozen=True, slots=True)
class LillyTimeInterval:
    """Declared time envelope; numerical envelopes are not statistical errors."""
    low: float
    high: float

    def __post_init__(self):
        object.__setattr__(self, "low", _finite(self.low, "interval low"))
        object.__setattr__(self, "high", _finite(self.high, "interval high"))
        if self.high < self.low:
            raise ValueError("time interval must be ordered")

    @property
    def midpoint(self):
        """Return a display representative without choosing event precedence."""
        return self.low / 2 + self.high / 2


@dataclass(frozen=True, slots=True)
class LillyMoonCoverage:
    """A supplied or completed finite scan; unknown frontiers remain visible."""
    interval: LillyTimeInterval
    state: LillyCoverageState
    source_id: str
    reasons: tuple[str, ...] = ()
    assurance: str = "supplied_evidence"

    def __post_init__(self):
        if not isinstance(self.interval, LillyTimeInterval) or not isinstance(self.state, LillyCoverageState):
            raise TypeError("typed coverage interval and state required")
        _text(self.source_id, "coverage source")
        _text(self.assurance, "coverage assurance")
        _strings(self.reasons, "coverage reasons")
        if (self.state is LillyCoverageState.COMPLETE) == bool(self.reasons):
            raise ValueError("complete coverage has no reasons; incomplete coverage requires reasons")


@dataclass(frozen=True, slots=True)
class LillyMoonProvenance:
    """Caller-declared physical model or explicitly synthetic input identity."""
    source_id: str
    frame: str
    corrections: str
    time_model: str
    source_identity: tuple[tuple[str, str], ...] = ()

    def __post_init__(self):
        for name in ("source_id", "frame", "corrections", "time_model"):
            _text(getattr(self, name), name)
        if not isinstance(self.source_identity, tuple):
            raise TypeError("source identity must be an immutable tuple")
        for row in self.source_identity:
            if not isinstance(row, tuple) or len(row) != 2:
                raise TypeError("source identity entries must be string pairs")
            for item in row:
                _text(item, "source identity entry")
        if len({k for k, _ in self.source_identity}) != len(self.source_identity):
            raise ValueError("source identity keys must be distinct")


@dataclass(frozen=True, slots=True)
class LillyMoonContact:
    """One supplied exact contact, including excluded bodies/aspects as evidence."""
    event_id: str
    partner: str
    directed_angle_deg: float
    time: LillyTimeInterval

    def __post_init__(self):
        _text(self.event_id, "contact ID")
        _text(self.partner, "contact partner")
        object.__setattr__(self, "directed_angle_deg", _angle(self.directed_angle_deg))
        if not isinstance(self.time, LillyTimeInterval):
            raise TypeError("contact time must be a Lilly time interval")

    @property
    def eligible(self):
        """Return admission to this candidate's fixed lunar contact universe."""
        return self.partner in _PARTNERS and self.directed_angle_deg in _TARGETS


@dataclass(frozen=True, slots=True)
class LillyApplicationEpisode:
    """Open interval of approach, strict moiety interior and sign eligibility.

Supplied episodes assert those premises under their source_id. The numerical
builder derives them from canonical longitude, relative rate and sign cuts.
Endpoint envelopes retain possible and definite interiors separately.
"""
    event_id: str
    partner: str
    directed_angle_deg: float
    start: LillyTimeInterval
    end: LillyTimeInterval
    source_id: str
    verification: LillyP3State = LillyP3State.PRESENT
    orb_policy: str = field(default="lilly_1647_p107_second_strict_interior", init=False)

    def __post_init__(self):
        _text(self.event_id, "episode ID")
        _text(self.partner, "episode partner")
        _text(self.source_id, "episode source")
        if self.verification not in (LillyP3State.PRESENT, LillyP3State.NOT_EVALUABLE) or not isinstance(self.verification, LillyP3State):
            raise ValueError("application premise must be verified or explicitly unresolved")
        object.__setattr__(self, "directed_angle_deg", _angle(self.directed_angle_deg))
        if not isinstance(self.start, LillyTimeInterval) or not isinstance(self.end, LillyTimeInterval):
            raise TypeError("episode boundaries must be time intervals")
        if self.start.midpoint >= self.end.midpoint:
            raise ValueError("an application episode must have an open interior")

    @property
    def eligible(self):
        """Return admission to the same explicit body/aspect universe."""
        return self.partner in _PARTNERS and self.directed_angle_deg in _TARGETS


@dataclass(frozen=True, slots=True)
class LillyMoonIngress:
    """A verified sign crossing, not a tangent touch of a sign boundary."""
    event_id: str
    body: str
    time: LillyTimeInterval
    sign_before: int
    sign_after: int

    def __post_init__(self):
        _text(self.event_id, "ingress ID")
        if self.body not in ("Moon", *_PARTNERS) or not isinstance(self.time, LillyTimeInterval):
            raise ValueError("ingress needs a classical body and typed time")
        if any(type(s) is not int or not 0 <= s < 12 for s in (self.sign_before, self.sign_after)):
            raise ValueError("ingress signs must be zero-based zodiac signs")
        if (self.sign_after - self.sign_before) % 12 not in (1, 11):
            raise ValueError("ingress must cross to an adjacent sign")


@dataclass(frozen=True, slots=True)
class LillyMoonScanReceipt:
    """Actual per-scan work, completed subintervals and unresolved reasons."""
    label: str
    complete: bool
    evaluations: int
    subdivisions: int
    scanned_intervals: tuple[LillyTimeInterval, ...]
    reasons: tuple[str, ...]

    def __post_init__(self):
        _text(self.label, "scan label")
        if type(self.complete) is not bool or any(type(x) is not int or x < 0 for x in (self.evaluations, self.subdivisions)):
            raise ValueError("scan receipt needs boolean completion and nonnegative work counts")
        if not isinstance(self.scanned_intervals, tuple) or any(not isinstance(x, LillyTimeInterval) for x in self.scanned_intervals):
            raise TypeError("scanned intervals must be immutable typed intervals")
        _strings(self.reasons, "scan reasons")
        if self.complete == bool(self.reasons):
            raise ValueError("scan completion and reasons disagree")


@dataclass(frozen=True, slots=True)
class LillyMoonTrace:
    """Immutable co-model lunar evidence and independent coverage receipts."""
    context: LillySnapshotContext
    provenance: LillyMoonProvenance
    study: LillyTimeInterval
    sign_exit: LillyTimeInterval | None
    contacts: tuple[LillyMoonContact, ...]
    applications: tuple[LillyApplicationEpisode, ...]
    ingresses: tuple[LillyMoonIngress, ...]
    past_coverage: LillyMoonCoverage
    exact_coverage: LillyMoonCoverage
    application_coverage: LillyMoonCoverage
    prior_separation: LillyP3State = LillyP3State.NOT_EVALUABLE
    separation_evidence_ids: tuple[str, ...] = ()
    moon_longitude_at_query: float | None = None
    scan_receipts: tuple[LillyMoonScanReceipt, ...] = ()
    position_evaluations: int = 0
    search_policy: LillyMoonSearchPolicy | None = None
    profile_id: str = field(default=_PROFILE, init=False)

    def __post_init__(self):
        _context(self.context, dated=True)
        if not isinstance(self.provenance, LillyMoonProvenance) or not isinstance(self.study, LillyTimeInterval):
            raise TypeError("typed lunar provenance and study interval required")
        q = self.context.jd_ut
        if not self.study.low <= q < self.study.high:
            raise ValueError("study must contain query and a remaining future interval")
        if self.sign_exit is not None:
            if not isinstance(self.sign_exit, LillyTimeInterval) or self.sign_exit.low <= q:
                raise ValueError("sign exit must be wholly after the query")
            if self.sign_exit.high > self.study.high:
                raise ValueError("sign exit must lie inside the declared study")
        ids = []
        for name, cls in (("contacts", LillyMoonContact), ("applications", LillyApplicationEpisode), ("ingresses", LillyMoonIngress)):
            rows = getattr(self, name)
            if not isinstance(rows, tuple) or any(not isinstance(r, cls) for r in rows):
                raise TypeError(f"{name} must be an immutable tuple of typed records")
            ids.extend(r.event_id for r in rows)
            for row in rows:
                lo, hi = (row.start.low, row.end.high) if cls is LillyApplicationEpisode else (row.time.low, row.time.high)
                if lo < self.study.low or hi > self.study.high:
                    raise ValueError("event envelope lies outside the declared study")
        if len(ids) != len(set(ids)):
            raise ValueError("lunar event IDs must be globally distinct")
        for coverage in (self.past_coverage, self.exact_coverage, self.application_coverage):
            if not isinstance(coverage, LillyMoonCoverage):
                raise TypeError("typed lunar coverage required")
            if coverage.interval.low < self.study.low or coverage.interval.high > self.study.high:
                raise ValueError("coverage lies outside the study")
        if not isinstance(self.prior_separation, LillyP3State) or self.prior_separation is LillyP3State.NOT_APPLICABLE:
            raise ValueError("separation premise must be present, absent or unknown")
        _strings(self.separation_evidence_ids, "separation evidence IDs")
        if self.prior_separation is not LillyP3State.NOT_EVALUABLE and not self.separation_evidence_ids:
            raise ValueError("known separation premise needs explicit evidence IDs")
        if self.moon_longitude_at_query is not None:
            object.__setattr__(self, "moon_longitude_at_query", _angle(self.moon_longitude_at_query))
        if not isinstance(self.scan_receipts, tuple) or any(not isinstance(x, LillyMoonScanReceipt) for x in self.scan_receipts):
            raise TypeError("scan receipts must be an immutable typed tuple")
        if type(self.position_evaluations) is not int or self.position_evaluations < 0:
            raise ValueError("position evaluation count must be nonnegative")
        if self.search_policy is not None and not isinstance(self.search_policy, LillyMoonSearchPolicy):
            raise TypeError("numerical traces must retain a typed search policy")
        object.__setattr__(self, "contacts", tuple(sorted(self.contacts, key=lambda x: (x.time.low, x.event_id))))
        object.__setattr__(self, "applications", tuple(sorted(self.applications, key=lambda x: (x.start.low, x.event_id))))
        object.__setattr__(self, "ingresses", tuple(sorted(self.ingresses, key=lambda x: (x.time.low, x.event_id))))


@dataclass(frozen=True, slots=True)
class LillyVOCResult:
    """One explicitly selected definition, with all supports and boundaries."""
    trace: LillyMoonTrace
    definition: LillyVOCDefinition
    state: LillyP3State = field(init=False)
    connection_ids: tuple[str, ...] = field(init=False)
    boundary_ids: tuple[str, ...] = field(init=False)
    excluded_ids: tuple[str, ...] = field(init=False)
    reasons: tuple[str, ...] = field(init=False)
    source_reference: str = field(default="Lilly 1647 pp.107-112,122; P3 M01-M06", init=False)

    def __post_init__(self):
        if not isinstance(self.trace, LillyMoonTrace) or not isinstance(self.definition, LillyVOCDefinition):
            raise TypeError("typed lunar trace and explicit VOC definition required")
        trace, q = self.trace, self.trace.context.jd_ut
        exit_ = trace.sign_exit
        connections, boundaries, excluded, reasons = [], [], [], []
        if self.definition is LillyVOCDefinition.EXACT_BEFORE_INGRESS:
            rows, coverage = trace.contacts, trace.exact_coverage
            for event in rows:
                if not event.eligible:
                    excluded.append(event.event_id)
                elif exit_ is not None:
                    if q < event.time.low and event.time.high < exit_.low:
                        connections.append(event.event_id)
                    elif not (event.time.high < q or event.time.low > exit_.high):
                        boundaries.append(event.event_id)
        else:
            rows, coverage = trace.applications, trace.application_coverage
            for event in rows:
                if not event.eligible:
                    excluded.append(event.event_id)
                elif exit_ is not None:
                    if event.verification is LillyP3State.PRESENT and max(q, event.start.high) < min(exit_.low, event.end.low):
                        connections.append(event.event_id)
                    elif max(q, event.start.low) < min(exit_.high, event.end.high):
                        boundaries.append(event.event_id)
        query_ingresses = tuple(e.event_id for e in trace.ingresses if e.body == "Moon" and e.time.low <= q <= e.time.high)
        boundaries.extend(query_ingresses)
        coverage_complete = (exit_ is not None and coverage.state is LillyCoverageState.COMPLETE
                             and coverage.interval.low <= q and coverage.interval.high >= exit_.high)
        if trace.prior_separation is LillyP3State.ABSENT:
            state = LillyP3State.NOT_APPLICABLE
            reasons.append("separation_premise_explicitly_unmet")
        elif exit_ is None or query_ingresses:
            state = LillyP3State.NOT_EVALUABLE
            reasons.append("sign_exit_unresolved" if exit_ is None else "query_ingress_order_unresolved")
        elif connections:
            state = LillyP3State.ABSENT
        elif boundaries or not coverage_complete or trace.prior_separation is LillyP3State.NOT_EVALUABLE:
            state = LillyP3State.NOT_EVALUABLE
            if boundaries:
                reasons.append("event_boundary_order_unresolved")
            if not coverage_complete:
                reasons.append("remaining_interval_coverage_incomplete")
            if trace.prior_separation is LillyP3State.NOT_EVALUABLE:
                reasons.append("prior_separation_unknown")
        else:
            state = LillyP3State.PRESENT
        for name, value in (("state", state), ("connection_ids", tuple(connections)),
                            ("boundary_ids", tuple(boundaries)), ("excluded_ids", tuple(excluded)),
                            ("reasons", tuple(reasons))):
            object.__setattr__(self, name, value)


def lilly_void_of_course(trace: LillyMoonTrace, *, definition: LillyVOCDefinition) -> LillyVOCResult:
    """Evaluate a named candidate; there is deliberately no definition default."""
    return LillyVOCResult(trace, definition)


@dataclass(frozen=True, slots=True)
class LillyMoonContactGroup:
    """A component of overlapping envelopes; members need not all be simultaneous."""
    contacts: tuple[LillyMoonContact, ...]
    ordering: str = field(init=False)

    def __post_init__(self):
        if not isinstance(self.contacts, tuple) or not self.contacts or any(not isinstance(c, LillyMoonContact) for c in self.contacts):
            raise TypeError("nonempty immutable lunar contact group required")
        times = {(c.time.low, c.time.high) for c in self.contacts}
        point = len(times) == 1 and self.contacts[0].time.low == self.contacts[0].time.high
        object.__setattr__(self, "ordering", "single" if len(self.contacts) == 1 else "simultaneous" if point else "unresolved_order")


def _groups(contacts):
    groups, rows, end = [], [], -math.inf
    for c in sorted(contacts, key=lambda x: (x.time.low, x.event_id)):
        if rows and c.time.low > end:
            groups.append(LillyMoonContactGroup(tuple(rows)))
            rows = []
        rows.append(c)
        end = max(end, c.time.high)
    if rows:
        groups.append(LillyMoonContactGroup(tuple(rows)))
    return tuple(groups)


@dataclass(frozen=True, slots=True)
class LillyMoonSequence:
    """All supplied contacts, tied/order-uncertain groups and bounded last evidence."""
    trace: LillyMoonTrace
    groups: tuple[LillyMoonContactGroup, ...] = field(init=False)
    past_groups: tuple[LillyMoonContactGroup, ...] = field(init=False)
    future_groups: tuple[LillyMoonContactGroup, ...] = field(init=False)
    last_separation_candidates: tuple[str, ...] = field(init=False)
    last_separation_order_known: bool = field(init=False)
    automatic_role_assignment: bool = field(default=False, init=False)

    def __post_init__(self):
        if not isinstance(self.trace, LillyMoonTrace):
            raise TypeError("typed lunar trace required")
        trace, q = self.trace, self.trace.context.jd_ut
        groups = _groups(c for c in trace.contacts if c.eligible)
        past = tuple(g for g in groups if max(c.time.high for c in g.contacts) < q)
        future = tuple(g for g in groups if min(c.time.low for c in g.contacts) > q)
        cov = trace.past_coverage
        known = (bool(past) and past[-1].ordering != "unresolved_order" and cov.state is LillyCoverageState.COMPLETE
                 and cov.interval.high >= q and cov.interval.low <= min(c.time.low for c in past[-1].contacts)
                 and not any(c.time.low <= q <= c.time.high for c in trace.contacts if c.eligible))
        for name, value in (("groups", groups), ("past_groups", past), ("future_groups", future),
                            ("last_separation_candidates", tuple(c.event_id for c in past[-1].contacts) if past else ()),
                            ("last_separation_order_known", known)):
            object.__setattr__(self, name, value)


def lilly_moon_sequence(trace: LillyMoonTrace) -> LillyMoonSequence:
    """Preserve the sequence without assigning last/next planets as new roles."""
    return LillyMoonSequence(trace)


@dataclass(frozen=True, slots=True)
class LillyMoonSearchPolicy:
    """Numerical work and resolution policy, never an astrological duration rule."""
    past_days: float = 4.
    future_days: float = 4.
    step_days: float = .125
    time_tolerance_seconds: float = .05
    angular_tolerance_deg: float = 1e-7
    rate_tolerance_deg_per_day: float = 1e-6
    longitude_curvature_tolerance_deg: float = .1
    rate_curvature_tolerance_deg_per_day: float = .01
    velocity_step_days: float = .001
    max_position_evaluations: int = 50000
    max_subdivisions: int = 10000
    max_depth: int = 14
    policy_id: str = field(default="moira_lilly_p3_bounded_lunar_scan_v1", init=False)
    assurance: str = field(default="bounded_adaptive_scan_not_interval_certification", init=False)

    def __post_init__(self):
        for name in ("past_days", "future_days", "step_days", "time_tolerance_seconds", "angular_tolerance_deg", "rate_tolerance_deg_per_day",
                     "longitude_curvature_tolerance_deg", "rate_curvature_tolerance_deg_per_day", "velocity_step_days"):
            value = _finite(getattr(self, name), name)
            if value <= 0:
                raise ValueError(f"{name} must be positive")
            object.__setattr__(self, name, value)
        if self.past_days + self.future_days > 16 or self.step_days > 1:
            raise ValueError("lunar study is bounded to 16 days and step to one day")
        if self.time_tolerance_seconds / 86400 >= min(self.past_days, self.future_days, self.step_days) / 8:
            raise ValueError("time resolution must be smaller than scan/study intervals")
        for name in ("max_position_evaluations", "max_subdivisions", "max_depth"):
            if type(getattr(self, name)) is not int or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be a positive integer")


class _PositionBudget(RuntimeError):
    """Request-local exhaustion signal; never interpreted as absent evidence."""


def _difference(a, b):
    return (a - b + 180.) % 360. - 180.


def trace_lilly_moon(context: LillySnapshotContext, *, longitude_at,
                     provenance: LillyMoonProvenance,
                     policy: LillyMoonSearchPolicy = LillyMoonSearchPolicy()) -> LillyMoonTrace:
    """Derive a finite trace from one explicitly identified longitude product.

The callable takes ``(body, jd_ut1)`` and returns normalized longitude. Its
exceptions propagate. Numerical resource exhaustion instead retains earlier
evidence and marks coverage partial. No shared mutable cache is retained.
"""
    _context(context, dated=True)
    if not isinstance(provenance, LillyMoonProvenance) or not isinstance(policy, LillyMoonSearchPolicy):
        raise TypeError("typed lunar provenance and search policy required")
    if not callable(longitude_at):
        raise TypeError("longitude_at must be callable")
    q = context.jd_ut
    low, high = q - policy.past_days, q + policy.future_days
    if low == q or high == q:
        raise ValueError("study is below time representation")
    study = LillyTimeInterval(low, high)
    tol = policy.time_tolerance_seconds / 86400
    pad = max(4 * tol, 4 * math.ulp(q), 4 * math.ulp(low), 4 * math.ulp(high))
    cache, exact_reasons, application_reasons = {}, set(), set()
    contacts, episodes, ingresses, scan_receipts = [], [], [], []
    lunar_exit = None

    def position(body, jd):
        key = body, jd
        if key not in cache:
            if len(cache) >= policy.max_position_evaluations:
                raise _PositionBudget
            cache[key] = _angle(longitude_at(body, jd))
        return cache[key]

    def envelope(t):
        return LillyTimeInterval(max(low, t - pad), min(high, t + pad))

    scanner = _FixedScanPolicy(policy.step_days, tol, policy.angular_tolerance_deg,
        policy.longitude_curvature_tolerance_deg, policy.max_position_evaluations, policy.max_subdivisions, policy.max_depth,
        min(policy.velocity_step_days, policy.step_days / 8), policy.rate_tolerance_deg_per_day)

    def scan(function, targets, label):
        result = _scan_fixed_aspects(function, targets, ((low, high, "study_start", "study_end"),), scanner)
        scan_receipts.append(LillyMoonScanReceipt(label, result.complete, result.evaluations, result.subdivisions,
            tuple(LillyTimeInterval(a, b) for a, b in result.scanned_intervals), result.reasons))
        if not result.complete:
            exact_reasons.update(f"{label}:{r}" for r in result.reasons)
            application_reasons.update(f"{label}:{r}" for r in result.reasons)
        return result

    def rate(function, t):
        h = min(policy.velocity_step_days, policy.step_days / 8, (high - low) / 8)
        if t - h < low:
            return (4 * _difference(function(t + h), function(t)) - _difference(function(t + 2 * h), function(t))) / (2 * h)
        if t + h > high:
            return (-4 * _difference(function(t - h), function(t)) + _difference(function(t - 2 * h), function(t))) / (2 * h)
        return _difference(function(t + h), function(t - h)) / (2 * h)

    def crossings(body):
        def f(t):
            return position(body, t)
        result = scan(f, tuple((0., float(a), 0.) for a in range(0, 360, 30)), body + ":ingress")
        rows = []
        for hit in result.passes:
            t, angle = hit.jd_ut1, hit.directed_angle_deg
            h = min(.001, (t - low) / 2, (high - t) / 2)
            if h <= 0:
                application_reasons.add(body + ":ingress_at_study_edge")
                continue
            left, right = _difference(f(t - h), angle), _difference(f(t + h), angle)
            if left * right >= 0:
                continue
            boundary = int(angle / 30)
            before, after = ((boundary - 1) % 12, boundary) if right > left else (boundary, (boundary - 1) % 12)
            row = LillyMoonIngress(f"ingress:{body}:{angle:g}:{t.hex()}", body, envelope(t), before, after)
            rows.append(row)
        ingresses.extend(rows)
        return rows, result.complete

    def motion_cuts(relative, body):
        """Bounded scalar-rate partition; scalar rates never masquerade as angles."""
        count = math.ceil((high - low) / (policy.step_days / 2))
        if count > policy.max_position_evaluations:
            raise _PositionBudget
        pending = [(low + (high - low) * i / count, low + (high - low) * (i + 1) / count, 0) for i in range(count)]
        roots, subdivisions = [], 0
        while pending:
            a, b, depth = pending.pop()
            m = a / 2 + b / 2
            ra, rm, rb = (rate(relative, t) for t in (a, m, b))
            if abs(ra - 2 * rm + rb) > policy.rate_curvature_tolerance_deg_per_day:
                if depth >= policy.max_depth or subdivisions >= policy.max_subdivisions or m in (a, b):
                    application_reasons.add(body + ":motion_partition_incomplete")
                else:
                    subdivisions += 1
                    pending.extend(((a, m, depth + 1), (m, b, depth + 1)))
                    continue
            for u, v, ru, rv in ((a, m, ra, rm), (m, b, rm, rb)):
                if abs(ru) <= policy.rate_tolerance_deg_per_day:
                    roots.append(u)
                    application_reasons.add(body + ":motion_at_numerical_stationary_limit")
                if ru * rv < 0:
                    try:
                        roots.append(_bisect_scalar(lambda t: rate(relative, t), u, v, tol, policy.rate_tolerance_deg_per_day))
                    except ValueError:
                        application_reasons.add(body + ":motion_root_unresolved")
        return roots

    moon_q = position("Moon", q)
    try:
        moon_ingresses, moon_ingresses_complete = crossings("Moon")
        future = [e for e in moon_ingresses if e.time.low > q]
        if future and moon_ingresses_complete:
            lunar_exit = min(future, key=lambda e: e.time.low).time
        else:
            reason = "moon_exit_coverage_incomplete" if not moon_ingresses_complete else "moon_exit_not_found_within_horizon"
            exact_reasons.add(reason)
            application_reasons.add(reason)
        for body in _PARTNERS:
            prior_application_reasons = set(application_reasons)
            body_episodes = []
            partner_ingresses, partner_ingresses_complete = crossings(body)
            def relative(t, body=body):
                return position("Moon", t) - position(body, t)
            orb = lilly_orb_evidence("Moon", body, 0., context=context).combined_moiety_deg
            result = scan(relative, tuple((0., angle, orb) for angle in _TARGETS), body + ":aspect")
            for hit in result.passes:
                t, angle = hit.jd_ut1, hit.directed_angle_deg
                contacts.append(LillyMoonContact(f"contact:{body}:{angle:g}:{t.hex()}", body, angle, envelope(t)))
            turn_times = motion_cuts(relative, body)
            sign_times = [e.time.midpoint for e in (*moon_ingresses, *partner_ingresses)]
            for window in result.windows:
                if window.end <= window.start:
                    continue
                angle = _TARGETS[window.target_index]
                cuts = {window.start, window.end}
                cuts.update(t for t in (*turn_times, *sign_times,
                    *(h.jd_ut1 for h in result.passes if h.target_index == window.target_index))
                    if window.start < t < window.end)
                ordered = sorted(cuts)
                for a, b in zip(ordered, ordered[1:]):
                    if b - a <= 2 * tol:
                        application_reasons.add(body + ":unresolved_close_application_boundaries")
                        continue
                    middle = a / 2 + b / 2
                    residual = _difference(relative(middle), angle)
                    velocity = rate(relative, middle)
                    sign_relation = (int(position("Moon", middle) // 30) - int(position(body, middle) // 30)) % 12
                    if abs(residual) < orb and residual * velocity < 0 and sign_relation == int(angle / 30):
                        if abs(velocity) <= policy.rate_tolerance_deg_per_day:
                            application_reasons.add(body + ":application_rate_unresolved")
                        else:
                            body_episodes.append(LillyApplicationEpisode(
                                f"application:{body}:{angle:g}:{a.hex()}:{b.hex()}", body, angle,
                                envelope(a), envelope(b), provenance.source_id))
            verified = (moon_ingresses_complete and partner_ingresses_complete and result.complete
                        and not (application_reasons - prior_application_reasons))
            episodes.extend(body_episodes if verified else
                (replace(e, verification=LillyP3State.NOT_EVALUABLE) for e in body_episodes))
    except _PositionBudget:
        exact_reasons.add("position_budget_exhausted")
        application_reasons.add("position_budget_exhausted")
    exact_reason_tuple = tuple(sorted(exact_reasons))
    app_reason_tuple = tuple(sorted(application_reasons | exact_reasons))
    def coverage(reasons):
        return LillyMoonCoverage(study, LillyCoverageState.PARTIAL if reasons else LillyCoverageState.COMPLETE,
                                 provenance.source_id, reasons, policy.assurance)
    separation_ids = tuple(c.event_id for c in contacts if c.eligible and c.time.high < q)
    return LillyMoonTrace(context, provenance, study, lunar_exit, tuple(contacts), tuple(episodes),
        tuple(ingresses), coverage(exact_reason_tuple), coverage(exact_reason_tuple), coverage(app_reason_tuple),
        LillyP3State.PRESENT if separation_ids else LillyP3State.NOT_EVALUABLE,
        separation_ids, moon_q, tuple(scan_receipts), len(cache), policy)


def lilly_moon_at(context: LillySnapshotContext, *, reader,
                  policy: LillyMoonSearchPolicy = LillyMoonSearchPolicy()) -> LillyMoonTrace:
    """Trace the explicit reader's apparent geocentric tropical longitude product.

Canonical UT1-to-TT and TT-to-TDB conversion, light time, aberration,
deflection, precession and nutation remain owned by planet_at/SpkReader.
The reader is mandatory: this surface never acquires a kernel implicitly.
"""
    from .planets import planet_at
    from .spk_reader import SpkReader
    from .julian import ut_to_tt

    _context(context, dated=True)
    if not isinstance(reader, SpkReader):
        raise TypeError("an explicit open SpkReader is required")
    identity = reader._ephemeris_kernel_identity_at(ut_to_tt(context.jd_ut))
    if identity is None:
        raise ValueError("reader cannot identify a planetary/lunar product at the query")
    provenance = LillyMoonProvenance(
        str(reader.path), "geocentric_true_ecliptic_and_equinox_of_date",
        "planet_at:apparent_light_time_aberration_deflection_precession_nutation",
        "UT1_to_TT:moira.julian_canonical;TT_to_TDB:SPK_boundary",
        (("planetary_ephemeris", str(identity.planetary_ephemeris)),
         ("lunar_ephemeris", str(identity.lunar_ephemeris)),
         ("kernel_sha256", reader._source_identity.sha256),
         ("query_jd_ut1", repr(context.jd_ut)),
         ("query_jd_tt", repr(ut_to_tt(context.jd_ut))),
         ("delta_t_policy", "moira.julian_canonical_default")))
    return trace_lilly_moon(context, longitude_at=lambda body, jd: planet_at(body, jd, reader=reader).longitude,
                            provenance=provenance, policy=policy)
