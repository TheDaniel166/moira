"""Bounded reader-derived whole-sign Gochar timelines and explicit uncertainty.

Phaladeepika/Sastri doctrine is evaluated by ``gochara``. Interval arithmetic
certifies the selected computational model, not physical event-time accuracy.
The window search preserves all seven potential subjects and blockers.
"""
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Literal
import json
import math
from hashlib import sha256

from ._event_search.budgets import SearchBudgetError
from .gochara import GOCHARA_PLANETS, GOCHARA_PROFILE, gochara_from_positions, gochara_local_profiles
from .gochara_policy import GocharaDoctrineOption, gochara_doctrine_options
from .gochara_dated import (
    GocharaDatePolicy, GocharaBirthLocation, GocharaEpoch, GocharaDateResult,
    DEFAULT_GOCHARA_DATE_POLICY, _birth_scope, _number, _natal_components,
)
from .sidereal import Ayanamsa
from .ashtakavarga import BhinnashtakavargaResult


class GocharaWindowBudgetError(SearchBudgetError):
    """A finite search/output cap was exceeded; no truncated success exists."""
    label = "Gochar window"


class GocharaWindowDomainError(ValueError):
    """The request exceeds the certified interval model's dependency domain."""
    def __init__(self, dependency, lower=2415020.5, upper=2488434.5):
        self.dependency, self.lower, self.upper = dependency, lower, upper
        super().__init__(f"Gochar window outside certified {dependency} domain [{lower}, {upper})")


class GocharaWindowUnresolvedError(ValueError):
    """Strict resolution was requested but retained uncertainty remains."""
    def __init__(self, reasons, count, maximum_width_seconds):
        self.reasons = tuple(sorted(set(reasons)))
        self.count = count
        self.maximum_width_seconds = maximum_width_seconds
        super().__init__("Gochar window resolution is incomplete: " + ", ".join(self.reasons))


# Finite ceilings are public admission law. Benchmarks validate the usable
# request sizes independently; a duration ceiling is not a latency promise.
GOCHARA_WINDOW_HARD_MAXIMA = (
    ("max_range_days", 366), ("max_evaluations", 2_000_000),
    ("max_reader_calls", 20_000_000), ("max_root_iterations", 500_000),
    ("max_subdivisions", 500_000), ("max_events", 8192),
    ("max_cells", 16384), ("max_samples", 16384),
    ("max_evidence", 500_000), ("max_output_bytes", 32_000_000),
)


@dataclass(frozen=True, slots=True)
class GocharaWindowSearchLimits:
    """Immutable finite per-request ceilings; callers can lower each limit."""
    max_range_days: int = 366
    max_evaluations: int = 2_000_000
    max_reader_calls: int = 20_000_000
    max_root_iterations: int = 500_000
    max_subdivisions: int = 500_000
    max_events: int = 8192
    max_cells: int = 16384
    max_samples: int = 16384
    max_evidence: int = 500_000
    max_output_bytes: int = 32_000_000

    def __post_init__(self):
        for name, maximum in GOCHARA_WINDOW_HARD_MAXIMA:
            value = getattr(self, name)
            if type(value) is not int or not 1 <= value <= maximum:
                raise ValueError(f"{name} must be an integer in [1, {maximum}]")


@dataclass(frozen=True, slots=True)
class GocharaWindowSearchPolicy:
    """Numerical isolation target is separate from astronomical uncertainty."""
    boundary_tolerance_seconds: float = 1.0
    require_resolved: bool = False
    limits: GocharaWindowSearchLimits = field(default_factory=GocharaWindowSearchLimits)

    def __post_init__(self):
        value = _number("boundary_tolerance_seconds", self.boundary_tolerance_seconds)
        if not .01 <= value <= 60:
            raise ValueError("boundary_tolerance_seconds must be in [0.01, 60]")
        if type(self.require_resolved) is not bool:
            raise TypeError("require_resolved must be boolean")
        if not isinstance(self.limits, GocharaWindowSearchLimits):
            raise TypeError("limits must be GocharaWindowSearchLimits")
        object.__setattr__(self, "boundary_tolerance_seconds", value)


@dataclass(frozen=True, slots=True)
class GocharaNatalContext:
    """One natal derivation, shared by every window and dated sample."""
    epoch: GocharaEpoch
    policy: GocharaDatePolicy
    birth_location: GocharaBirthLocation | None = None
    natal_ascendant_tropical: float | None = field(init=False)
    natal_ascendant_sidereal: float | None = field(init=False)
    natal_sign_indices: tuple[tuple[str, int], ...] = field(init=False)
    raw_bav: tuple[BhinnashtakavargaResult, ...] = field(init=False)
    bav_source: str | None = field(init=False)
    _integrity: str = field(init=False, repr=False, compare=False, metadata={"wire": False})

    def __post_init__(self):
        _birth_scope(self.policy, self.birth_location)
        if not isinstance(self.epoch, GocharaEpoch):
            raise TypeError("epoch must be GocharaEpoch")
        if self.epoch.ayanamsa_system != self.policy.ayanamsa_system:
            raise ValueError("natal epoch contradicts policy")
        from dataclasses import replace
        if replace(self.epoch) != self.epoch:
            raise ValueError("natal epoch was mutated after construction")
        asc, sidereal, indices, tables = _natal_components(self.epoch, self.birth_location)
        for name, value in (
            ("natal_ascendant_tropical", asc), ("natal_ascendant_sidereal", sidereal),
            ("natal_sign_indices", tuple(indices.items())),
            ("raw_bav", tuple(tables[p] for p in GOCHARA_PLANETS) if tables else ()),
            ("bav_source", "Moira Raman 1981 encoding; own natal seven bodies + Lagna; unreduced" if tables else None),
        ):
            object.__setattr__(self, name, value)
        object.__setattr__(self, "_integrity", self._digest())

    def _digest(self):
        return sha256(json.dumps(_wire(self), allow_nan=False, sort_keys=True).encode()).hexdigest()

    def validate(self):
        """Detect mutation of a constructed context without repeating natal work."""
        if self._integrity != self._digest():
            raise ValueError("natal context changed after its derivation")

    def snapshot(self, longitudes):
        """Evaluate existing doctrine using the request's fixed natal tables."""
        return gochara_from_positions(
            self.epoch.positions[1].position.sidereal_longitude,
            dict(zip(GOCHARA_PLANETS, longitudes)),
            bhinna={b.planet: b for b in self.raw_bav} or None,
            policy=self.policy.gochara_policy,
        )


@dataclass(frozen=True, slots=True)
class GocharaWindowWitness:
    """Discrete directed relation; no changing longitude in the state key."""
    blocker: str
    blocker_house: int
    exempt: bool
    source: str


@dataclass(frozen=True, slots=True)
class GocharaWindowPlanet:
    """Constant whole-sign testimony, with raw BAV independent of condition."""
    planet: str
    sign_index: int
    house_from_moon: int
    condition: str
    baseline_favorable: bool
    baseline_source: str
    indication: str
    indication_source: str
    vedha_house: int | None
    vedha_source: str
    vedha_status: str
    witnesses: tuple[GocharaWindowWitness, ...]
    raw_bav_rekhas: int | None
    raw_bav_source: str | None
    evaluated_layers: tuple[str, ...]


def _state_planets(snapshot):
    return tuple(GocharaWindowPlanet(
        p.planet, a.position.rashi_index, a.house_from_moon, p.condition.value,
        a.baseline_favorable, a.baseline_source, a.indication, a.indication_source,
        a.vedha_house, a.vedha_source, a.vedha_status.value,
        tuple(GocharaWindowWitness(w.blocker.planet, w.blocker_house, w.exempt, w.source)
              for w in a.vedha_witnesses),
        a.ashtakavarga_rekhas, a.ashtakavarga_source, a.evaluated_layers,
    ) for p in gochara_local_profiles(snapshot) for a in (p.assessment,))


@dataclass(frozen=True, slots=True)
class GocharaWindowState:
    """Interned discrete state derived by the existing doctrine evaluator."""
    id: int
    signs: tuple[int, ...]
    planets: tuple[GocharaWindowPlanet, ...]

    def __post_init__(self):
        if type(self.id) is not int or self.id < 0:
            raise ValueError("state id must be nonnegative integer")
        if type(self.signs) is not tuple or len(self.signs) != 7 or any(type(s) is not int or not 0 <= s < 12 for s in self.signs):
            raise ValueError("state requires seven canonical sign indices")
        if type(self.planets) is not tuple or any(not isinstance(p, GocharaWindowPlanet) for p in self.planets):
            raise TypeError("state planets must be immutable Gochar testimony")
        if tuple(p.planet for p in self.planets) != GOCHARA_PLANETS or tuple(p.sign_index for p in self.planets) != self.signs:
            raise ValueError("state testimony contradicts canonical signs")


@dataclass(frozen=True, slots=True)
class GocharaWindowSample:
    """Individually dated complete astronomy, referencing one discrete state."""
    id: int
    state_id: int
    epoch: GocharaEpoch

    def __post_init__(self):
        if any(type(v) is not int or v < 0 for v in (self.id, self.state_id)):
            raise ValueError("sample and state ids must be nonnegative integers")
        if not isinstance(self.epoch, GocharaEpoch):
            raise TypeError("sample requires a complete astronomical epoch")


@dataclass(frozen=True, slots=True)
class GocharaIngressEvent:
    """Retained boundary evidence; classification never follows width alone."""
    id: int
    planet: str
    boundary_degrees: float
    lower_jd_ut1: float
    upper_jd_ut1: float
    kind: Literal["crossing", "contact", "possible_contact", "model_seam"]
    direction: int | None
    count: int | None
    reasons: tuple[str, ...] = ()
    clipped_start: bool = False
    clipped_end: bool = False
    left_value_bounds: tuple[float, float] | None = None
    right_value_bounds: tuple[float, float] | None = None
    rate_bounds: tuple[float, float] | None = None
    continuous_branch: bool = False

    def __post_init__(self):
        if type(self.id) is not int or self.id < 0:
            raise ValueError("event id must be a nonnegative integer")
        if self.planet not in GOCHARA_PLANETS:
            raise ValueError("event planet is not a classical participant")
        ray = _number("boundary_degrees", self.boundary_degrees)
        if not 0 <= ray < 360 or ray % 30:
            raise ValueError("boundary must be a sign ray")
        a, b = (_number(n, getattr(self, n)) for n in ("lower_jd_ut1", "upper_jd_ut1"))
        if a > b:
            raise ValueError("event bounds are reversed")
        if self.kind not in ("crossing", "contact", "possible_contact", "model_seam"):
            raise ValueError("unknown event classification")
        if type(self.reasons) is not tuple or any(not isinstance(r, str) or not r for r in self.reasons):
            raise ValueError("event reasons must be immutable nonempty strings")
        if any(type(v) is not bool for v in (self.clipped_start, self.clipped_end, self.continuous_branch)):
            raise TypeError("event clipping and continuity flags must be boolean")
        if self.count is not None and (type(self.count) is not int or self.count < 1):
            raise ValueError("an established event count must be a positive integer")
        if self.kind == "possible_contact" and (self.count is not None or not self.reasons):
            raise ValueError("possible contact requires unknown count and explicit reasons")
        if self.kind == "crossing" and (type(self.direction) is not int or self.direction not in (-1, 1) or type(self.count) is not int or self.count != 1):
            raise ValueError("crossing requires proved direction and unique count")
        if self.kind != "crossing" and self.direction is not None:
            raise ValueError("direction requires a proved crossing")
        for box in (self.left_value_bounds, self.right_value_bounds, self.rate_bounds):
            if box is not None and (type(box) is not tuple or len(box) != 2 or
                    any(not math.isfinite(_number("event bound", x)) for x in box) or box[0] > box[1]):
                raise ValueError("event evidence requires finite ordered bounds")
        if self.kind == "crossing":
            if not self.continuous_branch or any(b is None for b in
                    (self.left_value_bounds, self.right_value_bounds, self.rate_bounds)):
                raise ValueError("crossing requires continuity, endpoint and derivative evidence")
            left, right, rate = self.left_value_bounds, self.right_value_bounds, self.rate_bounds
            lray = ray+360*math.floor(((left[0]+left[1])/2-ray)/360+.5)
            rray = ray+360*math.floor(((right[0]+right[1])/2-ray)/360+.5)
            if not ((self.direction == 1 and left[1] < lray and right[0] > rray and rate[0] > 0) or
                    (self.direction == -1 and left[0] > lray and right[1] < rray and rate[1] < 0)):
                raise ValueError("crossing classification contradicts retained evidence")


@dataclass(frozen=True, slots=True)
class GocharaWindowRegion:
    """One uniquely owned part of the closed requested interval."""
    id: int
    start_jd_ut1: float
    end_jd_ut1: float
    include_start: bool
    include_end: bool
    kind: Literal["certain", "boundary_band", "unresolved_band"]
    state_id: int | None
    sample_id: int | None
    event_ids: tuple[int, ...] = ()
    reasons: tuple[str, ...] = ()

    def __post_init__(self):
        if type(self.id) is not int or self.id < 0:
            raise ValueError("region id must be a nonnegative integer")
        a, b = (_number(n, getattr(self, n)) for n in ("start_jd_ut1", "end_jd_ut1"))
        if a > b or (a == b and not (self.include_start and self.include_end)):
            raise ValueError("empty or reversed region")
        if type(self.include_start) is not bool or type(self.include_end) is not bool:
            raise TypeError("endpoint inclusion must be boolean")
        if self.kind not in ("certain", "boundary_band", "unresolved_band"):
            raise ValueError("unknown region kind")
        if type(self.event_ids) is not tuple or any(type(i) is not int or i < 0 for i in self.event_ids) or len(set(self.event_ids)) != len(self.event_ids):
            raise ValueError("region event references must be unique immutable integer ids")
        if type(self.reasons) is not tuple or any(not isinstance(r, str) or not r for r in self.reasons):
            raise ValueError("region reasons must be immutable nonempty strings")
        if any(v is not None and (type(v) is not int or v < 0) for v in (self.state_id, self.sample_id)):
            raise ValueError("region state/sample references must be integer ids")
        if (self.kind == "certain") != (self.state_id is not None and self.sample_id is not None):
            raise ValueError("only certain regions carry constant state and sample")
        if self.kind != "certain" and (self.state_id is not None or self.sample_id is not None):
            raise ValueError("an uncertainty band cannot assert constant state")
        if self.kind == "certain" and (self.event_ids or self.reasons):
            raise ValueError("certain regions cannot hide unresolved evidence or events")
        if self.kind == "unresolved_band" and not self.reasons:
            raise ValueError("unresolved region requires reasons")


@dataclass(frozen=True, slots=True)
class GocharaExclusionEvidence:
    """A domain removed by value exclusion or necessary Newton enclosure."""
    planet: str
    start_jd_ut1: float
    end_jd_ut1: float
    method: str
    value_lower: float
    value_upper: float
    rate_lower: float | None = None
    rate_upper: float | None = None
    parent_start_jd_ut1: float | None = None
    parent_end_jd_ut1: float | None = None
    target_degrees: float | None = None
    center_lower: float | None = None
    center_upper: float | None = None

    def __post_init__(self):
        if self.planet not in GOCHARA_PLANETS or self.method not in ("value", "newton_empty", "newton_left_open", "newton_right_open"):
            raise ValueError("unknown exclusion participant or method")
        if self.start_jd_ut1 > self.end_jd_ut1 or self.value_lower > self.value_upper:
            raise ValueError("exclusion bounds must be ordered")
        for f in fields(self):
            v = getattr(self, f.name)
            if f.name not in ("planet", "method") and v is not None:
                _number(f.name, v)
        if self.method == "value":
            if math.ceil(self.value_lower/30) <= math.floor(self.value_upper/30):
                raise ValueError("value exclusion contains a sign ray")
        else:
            if any(v is None for v in (self.parent_start_jd_ut1, self.parent_end_jd_ut1,
                    self.target_degrees, self.center_lower, self.center_upper, self.rate_lower, self.rate_upper)):
                raise ValueError("Newton exclusion requires complete parent and center evidence")
            if self.parent_start_jd_ut1 > self.parent_end_jd_ut1 or self.center_lower > self.center_upper or self.rate_lower > self.rate_upper:
                raise ValueError("Newton evidence bounds must be ordered")
            if self.target_degrees % 30 or not self.value_lower <= self.target_degrees <= self.value_upper:
                raise ValueError("Newton target must be an enclosed sign ray")
            from ._event_search.intervals import Interval
            derivative = Interval(self.rate_lower, self.rate_upper)
            if derivative.lo <= 0 <= derivative.hi:
                raise ValueError("Newton exclusion derivative contains zero")
            root = (self.parent_start_jd_ut1+self.parent_end_jd_ut1)/2-(
                Interval(self.center_lower,self.center_upper)-self.target_degrees)/derivative
            a, b = self.start_jd_ut1, self.end_jd_ut1
            if not self.parent_start_jd_ut1 <= a <= b <= self.parent_end_jd_ut1:
                raise ValueError("Newton exclusion is outside its parent proof")
            if not (b <= root.lo or a >= root.hi):
                raise ValueError("Newton exclusion intersects its necessary root enclosure")


@dataclass(frozen=True, slots=True)
class GocharaWindowCoverage:
    """Independent coverage claims, derived from the canonical partition."""
    participants: tuple[str, ...]
    domain_accounted: bool
    exclusion_certified: bool
    events_resolved: bool
    doctrine_profile: str
    unresolved_regions: int
    maximum_band_width_seconds: float
    certain_duration_days: float
    uncertain_duration_days: float


@dataclass(frozen=True, slots=True)
class GocharaWindowSubjectView:
    """Presentation projection retaining canonical regions and blocker evidence.

    Each reference resolves the region and that state's row for ``planet``.
    Bands remain in the view, including events caused only by other bodies.
    """
    planet: str
    region_ids: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class GocharaWindowResult:
    """Engine/REST result. Structural checks do not authenticate SPK execution."""
    start_jd_ut1: float
    end_jd_ut1: float
    natal: GocharaNatalContext
    search_policy: GocharaWindowSearchPolicy
    subjects: tuple[str, ...]
    states: tuple[GocharaWindowState, ...]
    samples: tuple[GocharaWindowSample, ...]
    events: tuple[GocharaIngressEvent, ...]
    regions: tuple[GocharaWindowRegion, ...]
    exclusions: tuple[GocharaExclusionEvidence, ...]
    resources: tuple[tuple[str, str], ...]
    work: tuple[tuple[str, int], ...]
    civil_inputs: tuple[str, ...] = ()
    coverage: GocharaWindowCoverage = field(init=False)
    subject_views: tuple[GocharaWindowSubjectView, ...] = field(init=False)
    selected_options: tuple[GocharaDoctrineOption, ...] = field(init=False)
    schema: str = field(init=False, default="moira.gochara.windows.v1")

    def __post_init__(self):
        if not isinstance(self.natal, GocharaNatalContext):
            raise TypeError("natal must be GocharaNatalContext")
        self.natal.validate()
        admitted = _admit(self.natal.epoch.jd_ut1, self.start_jd_ut1, self.end_jd_ut1,
               self.natal.birth_location, self.natal.policy, self.search_policy, self.subjects)
        if type(self.subjects) is not tuple or self.subjects != admitted[3]:
            raise ValueError("result subjects must use canonical immutable order")
        if type(self.civil_inputs) is not tuple or (self.civil_inputs and (len(self.civil_inputs) != 3 or any(not isinstance(v, str) for v in self.civil_inputs))):
            raise ValueError("civil receipts require three immutable datetime strings")
        for name, cls in (("states", GocharaWindowState), ("samples", GocharaWindowSample),
                          ("events", GocharaIngressEvent), ("regions", GocharaWindowRegion)):
            values = getattr(self, name)
            if type(values) is not tuple or any(not isinstance(v, cls) for v in values):
                raise TypeError(f"{name} must contain immutable {cls.__name__} vessels")
            if tuple(v.id for v in values) != tuple(range(len(values))):
                raise ValueError(f"{name} ids must be canonical and unique")
            for value in values:
                value.__post_init__()
        if type(self.exclusions) is not tuple or any(not isinstance(x, GocharaExclusionEvidence) for x in self.exclusions):
            raise TypeError("exclusions must be immutable proof records")
        for item in self.exclusions:
            item.__post_init__()
            if not self.start_jd_ut1 <= item.start_jd_ut1 <= item.end_jd_ut1 <= self.end_jd_ut1:
                raise ValueError("exclusion exceeds the requested domain")
        for state in self.states:
            expected = _state_planets(self.natal.snapshot(tuple(s * 30 + 15 for s in state.signs)))
            if state.planets != expected:
                raise ValueError("state testimony contradicts natal doctrine")
        for sample in self.samples:
            if not isinstance(sample.epoch, GocharaEpoch) or not 0 <= sample.state_id < len(self.states):
                raise ValueError("invalid sample epoch or state reference")
            if sample.epoch.ayanamsa_system != self.natal.policy.ayanamsa_system:
                raise ValueError("sample ayanamsa contradicts policy")
            if tuple(p.position.rashi_index for p in sample.epoch.positions) != self.states[sample.state_id].signs:
                raise ValueError("sample contradicts assigned state")
            from dataclasses import replace
            if replace(sample.epoch) != sample.epoch:
                raise ValueError("sample epoch was mutated after construction")
        if not self.regions or (self.regions[0].start_jd_ut1, self.regions[-1].end_jd_ut1) != (self.start_jd_ut1, self.end_jd_ut1):
            raise ValueError("partition must account for the whole requested domain")
        if not self.regions[0].include_start or not self.regions[-1].include_end:
            raise ValueError("closed request endpoints must be owned")
        for left, right in zip(self.regions, self.regions[1:]):
            if left.end_jd_ut1 != right.start_jd_ut1 or left.include_end == right.include_start:
                raise ValueError("partition has a gap or overlapping endpoint ownership")
        for region in self.regions:
            if any(type(i) is not int or not 0 <= i < len(self.events) for i in region.event_ids):
                raise ValueError("dangling event reference")
            if region.kind == "certain":
                if not 0 <= region.sample_id < len(self.samples) or not 0 <= region.state_id < len(self.states):
                    raise ValueError("dangling sample or state reference")
                sample = self.samples[region.sample_id]
                if sample.state_id != region.state_id or not region.start_jd_ut1 <= sample.epoch.jd_ut1 <= region.end_jd_ut1:
                    raise ValueError("region sample contradicts state or time")
                if (sample.epoch.jd_ut1 == region.start_jd_ut1 and not region.include_start or
                    sample.epoch.jd_ut1 == region.end_jd_ut1 and not region.include_end):
                    raise ValueError("sample occupies an excluded region endpoint")
            else:
                if not region.include_start or not region.include_end:
                    raise ValueError("uncertainty bands must own both endpoints")
                if region.kind == "boundary_band" and (not region.event_ids or region.reasons):
                    raise ValueError("resolved boundary band requires event evidence and no unresolved reason")
        if tuple(e.lower_jd_ut1 for e in self.events) != tuple(sorted(e.lower_jd_ut1 for e in self.events)):
            raise ValueError("events must be chronologically ordered")
        for event in self.events:
            owners = [r for r in self.regions if event.id in r.event_ids]
            if len(owners) != 1:
                raise ValueError("each event must belong to one band")
            owner = owners[0]
            if not owner.start_jd_ut1 <= event.lower_jd_ut1 <= event.upper_jd_ut1 <= owner.end_jd_ut1:
                raise ValueError("event exceeds its owning band")
            if event.kind == "possible_contact" and owner.kind != "unresolved_band":
                raise ValueError("possible contact cannot become a resolved boundary")
            if event.reasons and owner.kind != "unresolved_band":
                raise ValueError("unresolved event qualification must remain visible")
            if not set(event.reasons).issubset(owner.reasons):
                raise ValueError("owning band must retain every event reason")
            if ((event.upper_jd_ut1-event.lower_jd_ut1)*86400 > self.search_policy.boundary_tolerance_seconds
                    and owner.kind != "unresolved_band"):
                raise ValueError("an oversized event band cannot claim accepted resolution")
        # Every body's domain must be covered by exclusions or retained bands.
        # This verifies accounting, not the authenticity of the SPK coefficients.
        for planet in GOCHARA_PLANETS:
            spans = [(x.start_jd_ut1,x.end_jd_ut1) for x in self.exclusions if x.planet == planet]
            spans += [(e.lower_jd_ut1,e.upper_jd_ut1) for e in self.events if e.planet == planet]
            spans += [(r.start_jd_ut1,r.end_jd_ut1) for r in self.regions if r.kind == "unresolved_band"]
            cursor = self.start_jd_ut1
            for a,b in sorted(spans):
                if a > cursor:
                    raise ValueError(f"unaccounted search interval for {planet}")
                cursor = max(cursor,b)
            if cursor < self.end_jd_ut1:
                raise ValueError(f"incomplete exclusion/boundary evidence for {planet}")
        if type(self.resources) is not tuple or any(type(p) is not tuple or len(p) != 2 or any(not isinstance(s,str) for s in p) for p in self.resources):
            raise ValueError("resource receipts must be immutable string pairs")
        if type(self.work) is not tuple or any(type(p) is not tuple or len(p) != 2 or not isinstance(p[0],str) or type(p[1]) is not int or p[1]<0 for p in self.work):
            raise ValueError("work receipts require named nonnegative integer counters")
        uncertain = tuple(r for r in self.regions if r.kind != "certain")
        gaps = tuple(r for r in uncertain if r.kind == "unresolved_band")
        object.__setattr__(self, "coverage", GocharaWindowCoverage(
            GOCHARA_PLANETS, True, True, not gaps, GOCHARA_PROFILE,
            len(gaps), max(((r.end_jd_ut1-r.start_jd_ut1)*86400 for r in uncertain), default=0.),
            sum(r.end_jd_ut1-r.start_jd_ut1 for r in self.regions if r.kind == "certain"),
            sum(r.end_jd_ut1-r.start_jd_ut1 for r in uncertain),
        ))
        object.__setattr__(self, "subject_views", tuple(GocharaWindowSubjectView(p,
            tuple(r.id for r in self.regions)) for p in self.subjects))
        forecast = next(o for o in gochara_doctrine_options() if o.id == "forecast.dated_events")
        object.__setattr__(self, "selected_options", (*self.natal.policy.selected_options, forecast))
        if self.search_policy.require_resolved and gaps:
            raise GocharaWindowUnresolvedError(tuple(reason for r in gaps for reason in r.reasons),
                len(gaps), self.coverage.maximum_band_width_seconds)

    def resolve_sample(self, sample_id: int) -> GocharaDateResult:
        """Reconstruct the existing dated snapshot on explicit caller request."""
        if type(sample_id) is not int or not 0 <= sample_id < len(self.samples):
            raise ValueError("unknown sample id")
        return GocharaDateResult(self.natal.epoch, self.samples[sample_id].epoch,
                                 self.natal.policy, self.natal.birth_location)

    def to_dict(self):
        """Canonical stdlib wire projection shared by transport and size accounting."""
        return _wire(self)


def _wire(value):
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        result = {f.name: _wire(getattr(value, f.name)) for f in fields(value) if f.metadata.get("wire", True)}
        if hasattr(value, "selected_options"):
            result["selected_options"] = _wire(value.selected_options)
        return result
    if isinstance(value, (tuple, list)):
        return [_wire(v) for v in value]
    return value


def window_json_bytes(result):
    """UTF-8 compact JSON, including receipts; no self-referential byte count."""
    return json.dumps(result.to_dict(), ensure_ascii=False, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")


def _admit(natal, start, end, location, policy, search, subjects):
    _birth_scope(policy, location)
    policy.__post_init__()
    policy.gochara_policy.__post_init__()
    if not isinstance(search, GocharaWindowSearchPolicy):
        raise TypeError("search_policy must be GocharaWindowSearchPolicy")
    search.__post_init__()
    search.limits.__post_init__()
    natal, start, end = (_number(n, v) for n, v in
                         (("natal_jd_ut1", natal), ("start_jd_ut1", start), ("end_jd_ut1", end)))
    if not -10_000_000 <= natal <= 10_000_000 or not start < end:
        raise ValueError("admitted natal epoch and positive search duration required")
    if not 2415020.5 <= start < end < 2488434.5:
        raise GocharaWindowDomainError("UT1 clock")
    if end-start > search.limits.max_range_days:
        raise GocharaWindowBudgetError("range_days", search.limits.max_range_days, end-start, "preflight")
    if search.boundary_tolerance_seconds < 32 * max(math.ulp(start), math.ulp(end)) * 86400:
        raise ValueError("boundary tolerance is below representable resolution")
    if subjects is None:
        subjects = GOCHARA_PLANETS
    if not isinstance(subjects, (tuple, list)) or not subjects or any(p not in GOCHARA_PLANETS for p in subjects) or len(set(subjects)) != len(subjects):
        raise ValueError("subjects must be unique classical planet names")
    return natal, start, end, tuple(p for p in GOCHARA_PLANETS if p in subjects)


def gochara_windows(natal_jd_ut1, start_jd_ut1, end_jd_ut1, *, birth_location=None,
                     policy=None, search_policy=None, subjects=None, reader=None):
    """Search closed UT1 bounds with explicit event-time and unresolved bands."""
    active = DEFAULT_GOCHARA_DATE_POLICY if policy is None else policy
    search = GocharaWindowSearchPolicy() if search_policy is None else search_policy
    natal, start, end, selected = _admit(natal_jd_ut1, start_jd_ut1, end_jd_ut1,
                                       birth_location, active, search, subjects)
    from ._gochara_window_search import search_windows
    return search_windows(natal, start, end, birth_location, active, search, selected, reader)


def _civil_epochs(values):
    """Shared engine/transport civil admission; each instant converts once."""
    from .julian import jd_from_datetime, utc_to_ut1
    for value in values:
        if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("three timezone-aware datetime instants required")
    return tuple(utc_to_ut1(jd_from_datetime(v)) for v in values)


def _civil_receipt(result, values):
    from dataclasses import replace
    result = replace(result, civil_inputs=tuple(v.isoformat() for v in values))
    size = len(window_json_bytes(result))
    if size > result.search_policy.limits.max_output_bytes:
        raise GocharaWindowBudgetError("output_bytes", result.search_policy.limits.max_output_bytes, size, "civil_serialization")
    return result


def gochara_windows_for_datetimes(natal_dt, start_dt, end_dt, **kwargs):
    """Convert each aware civil instant once through the canonical UTC owner."""
    values = (natal_dt, start_dt, end_dt)
    return _civil_receipt(gochara_windows(*_civil_epochs(values), **kwargs), values)


@dataclass(frozen=True, slots=True)
class GocharaWindowCapabilities:
    """Resource-free product contract; installed resources are not probed."""
    ayanamsas: tuple[str, ...] = tuple(Ayanamsa.ALL)
    participants: tuple[str, ...] = GOCHARA_PLANETS
    doctrine_profile: str = GOCHARA_PROFILE
    nominal_start_jd_ut1: float = 2415020.5
    nominal_end_exclusive_jd_ut1: float = 2488434.5
    endpoint_semantics: str = "closed_request_disjoint_regions"
    boundary_tolerance_seconds: tuple[float, float] = (.01, 60.)
    default_search: GocharaWindowSearchPolicy = field(default_factory=GocharaWindowSearchPolicy)
    installed_resources_probed: bool = False
    effective_domain: str = "intersection_of_UT1_clock_TT_frame_retarded_SPK_and_anchor_support"
    unresolved_behavior: str = "explicit_regions_or_strict_422"
    physical_timing_accuracy: str = "not_inferred_from_solver_tolerance"
    event_count_semantics: str = "per_continuous_surrogate_branch_under_declared_arithmetic_model"


def gochara_window_capabilities():
    """Discover the contract without opening ephemerides or stellar catalogs."""
    return GocharaWindowCapabilities()


__all__ = ['GocharaWindowBudgetError', 'GocharaWindowDomainError', 'GocharaWindowUnresolvedError', 'GocharaWindowSearchLimits', 'GocharaWindowSearchPolicy', 'GocharaNatalContext', 'GocharaWindowWitness', 'GocharaWindowPlanet', 'GocharaWindowState', 'GocharaWindowSample', 'GocharaIngressEvent', 'GocharaWindowRegion', 'GocharaExclusionEvidence', 'GocharaWindowCoverage', 'GocharaWindowSubjectView', 'GocharaWindowResult', 'GocharaWindowCapabilities', 'gochara_windows', 'gochara_windows_for_datetimes', 'gochara_window_capabilities']
