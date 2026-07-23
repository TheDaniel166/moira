"""Bounded Church of Light progressed-contact search and influence integration.

The one-degree contact band and instantaneous power curve are source doctrine.
Numerical search and variable-rate quadrature are explicitly Moira products;
they do not replace the manual's conditional constant-rate 0.75 rule.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import ceil, isfinite

from .astrodynes import ASTRODYNE_PLANETS, ASTRODYNE_POINTS, natal_astrodynes_from_geometry
from .constants import HouseSystem
from .houses import HousePolicy, calculate_houses
from .julian import jd_from_datetime
from .planets import get_reader, planet_at
from .progressed_astrodynes import (
    ProgressedAccessoryAspectRelation,
    ProgressedAstrodyneTerminal,
    ProgressedMajorAspectRelation,
    ProgressedNatalBodyValue,
    ProgressedReenforcementTruth,
    ProgressedTerminalKind,
    evaluate_accessory_progressed_relation,
    evaluate_major_progressed_relation,
    progressed_aspect_harmony,
    reenforce_major_progressed_relation,
)
from .progressed_astrodynes_chart import (
    DEFAULT_CHURCH_OF_LIGHT_PROGRESSION_POLICY,
    _limiting_date,
    _major_ephemeris_jd,
    _minor_ephemeris_jd,
    _terminal_set,
)


_BODIES = frozenset((*ASTRODYNE_PLANETS, *ASTRODYNE_POINTS))
_MAJOR_KINDS = frozenset(
    {ProgressedTerminalKind.RADICAL, ProgressedTerminalKind.MAJOR_PROGRESSED}
)
_ACCESSORY_KINDS = frozenset(
    {ProgressedTerminalKind.MINOR_PROGRESSED, ProgressedTerminalKind.TRANSIT}
)


def _aware_utc(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")
    return value.astimezone(timezone.utc)


def _positive(value: float, name: str) -> float:
    if not isfinite(value) or value <= 0.0:
        raise ValueError(f"{name} must be finite and positive")
    return float(value)


@dataclass(frozen=True, slots=True)
class ProgressedContactQuery:
    """One terminal-to-terminal contact whose chronology is to be searched."""

    body_a: str
    kind_a: ProgressedTerminalKind
    body_b: str
    kind_b: ProgressedTerminalKind
    aspect: str

    def __post_init__(self) -> None:
        if self.body_a not in _BODIES or self.body_b not in _BODIES:
            raise ValueError("contact bodies must be admitted Astrodyne bodies or angles")
        try:
            kind_a = ProgressedTerminalKind(self.kind_a)
            kind_b = ProgressedTerminalKind(self.kind_b)
        except ValueError as exc:
            raise ValueError("unsupported progressed terminal kind") from exc
        aspect = self.aspect.strip().lower().replace("_", "-")
        if not aspect:
            raise ValueError("aspect must be non-empty")
        if kind_a in _ACCESSORY_KINDS:
            if kind_b not in _MAJOR_KINDS:
                raise ValueError("an accessory contact must target a radical/major terminal")
        elif kind_a in _MAJOR_KINDS and kind_b in _MAJOR_KINDS:
            if ProgressedTerminalKind.MAJOR_PROGRESSED not in {kind_a, kind_b}:
                raise ValueError("a major contact requires a major-progressed terminal")
        else:
            raise ValueError(
                "kind_a must be an accessory mover or both terminals must form a major contact"
            )
        object.__setattr__(self, "kind_a", kind_a)
        object.__setattr__(self, "kind_b", kind_b)
        object.__setattr__(self, "aspect", aspect)

    @property
    def terminal_a_id(self) -> str:
        return _terminal_id(self.body_a, self.kind_a)

    @property
    def terminal_b_id(self) -> str:
        return _terminal_id(self.body_b, self.kind_b)


@dataclass(frozen=True, slots=True)
class ProgressedContactSearchPolicy:
    """Visible numerical policy for one bounded chronological search."""

    coarse_step_hours: float
    boundary_tolerance_seconds: float = 1.0
    perfection_tolerance_seconds: float = 1.0
    perfection_distance_tolerance_arcmin: float = 0.01
    max_samples: int = 50_000

    def __post_init__(self) -> None:
        _positive(self.coarse_step_hours, "coarse_step_hours")
        _positive(self.boundary_tolerance_seconds, "boundary_tolerance_seconds")
        _positive(self.perfection_tolerance_seconds, "perfection_tolerance_seconds")
        _positive(
            self.perfection_distance_tolerance_arcmin,
            "perfection_distance_tolerance_arcmin",
        )
        if isinstance(self.max_samples, bool) or not isinstance(self.max_samples, int):
            raise TypeError("max_samples must be an integer")
        if self.max_samples < 3:
            raise ValueError("max_samples must be an integer of at least 3")


@dataclass(frozen=True, slots=True)
class ProgressedContactMoment:
    """Vessel: Structured progressed contact moment data."""
    event: str
    dt: datetime
    jd_ut: float
    distance_arcmin: float
    power: float
    harmony: float
    discord: float
    relation_id: str
    reenforcement_power: float | None = None
    reenforced_major_power: float | None = None


@dataclass(frozen=True, slots=True)
class ProgressedContactWindow:
    """Vessel: Structured progressed contact window data."""
    entry: ProgressedContactMoment
    closest_approaches: tuple[ProgressedContactMoment, ...]
    exit: ProgressedContactMoment
    entry_clipped: bool
    exit_clipped: bool


@dataclass(frozen=True, slots=True)
class ProgressedContactSearchResult:
    """Vessel: Structured progressed contact search result data."""
    query: ProgressedContactQuery
    start_dt: datetime
    end_dt: datetime
    policy: ProgressedContactSearchPolicy
    sample_count: int
    windows: tuple[ProgressedContactWindow, ...]
    reenforces_major: ProgressedContactQuery | None
    provenance: str = "church_of_light_one_degree_band_moira_bounded_search"


@dataclass(frozen=True, slots=True)
class ProgressedVariableInfluenceTruth:
    """Vessel: Structured progressed variable influence truth data."""
    query: ProgressedContactQuery
    start_dt: datetime
    end_dt: datetime
    duration_days: float
    method: str
    max_step_hours: float
    sample_count: int
    total_power_days: float
    total_harmony_days: float
    total_discord_days: float
    average_power: float
    average_harmony: float
    average_discord: float
    coarse_total_power_days: float
    power_error_estimate_days: float
    constant_rate_comparator_power_days: float | None
    constant_rate_difference_days: float | None
    provenance: str = "source_instantaneous_curve_moira_composite_trapezoid"


@dataclass(frozen=True, slots=True)
class _Evaluation:
    """Vessel: Structured evaluation data."""
    moment: ProgressedContactMoment
    relation: ProgressedMajorAspectRelation | ProgressedAccessoryAspectRelation
    reenforcement: ProgressedReenforcementTruth | None


def _terminal_id(body: str, kind: ProgressedTerminalKind) -> str:
    suffix = {
        ProgressedTerminalKind.RADICAL: "r",
        ProgressedTerminalKind.MAJOR_PROGRESSED: "p",
        ProgressedTerminalKind.MINOR_PROGRESSED: "m",
        ProgressedTerminalKind.TRANSIT: "t",
    }[kind]
    return f"{body}:{suffix}"


def _natal_values(
    radical_terminals: tuple[ProgressedAstrodyneTerminal, ...],
    natal_cusps: tuple[float, ...],
) -> dict[str, ProgressedNatalBodyValue]:
    radical = {item.body: item for item in radical_terminals}
    natal = natal_astrodynes_from_geometry(
        {body: radical[body].longitude_deg for body in ASTRODYNE_PLANETS},
        {body: radical[body].declination_deg for body in radical},
        natal_cusps,
        radical["M.C."].longitude_deg,
        radical["Asc."].longitude_deg,
    )
    return {
        item.body: ProgressedNatalBodyValue(
            item.body, item.total_power, item.total_harmony, item.total_discord
        )
        for item in natal.profiles
    }


def _opposite_terminal(
    terminal: ProgressedAstrodyneTerminal,
    terminals: dict[str, ProgressedAstrodyneTerminal],
) -> ProgressedAstrodyneTerminal:
    opposite = (
        ProgressedTerminalKind.MAJOR_PROGRESSED
        if terminal.kind is ProgressedTerminalKind.RADICAL
        else ProgressedTerminalKind.RADICAL
    )
    return terminals[_terminal_id(terminal.body, opposite)]


def _relation(
    query: ProgressedContactQuery,
    terminals: dict[str, ProgressedAstrodyneTerminal],
    natal: dict[str, ProgressedNatalBodyValue],
) -> ProgressedMajorAspectRelation | ProgressedAccessoryAspectRelation:
    first = terminals[query.terminal_a_id]
    second = terminals[query.terminal_b_id]
    if first.kind in _ACCESSORY_KINDS:
        return evaluate_accessory_progressed_relation(
            first,
            second,
            _opposite_terminal(second, terminals),
            natal[first.body],
            natal[second.body],
            query.aspect,
        )
    same_body = first.body == second.body
    return evaluate_major_progressed_relation(
        first,
        second,
        None if same_body else _opposite_terminal(first, terminals),
        None if same_body else _opposite_terminal(second, terminals),
        natal[first.body],
        natal[second.body],
        query.aspect,
    )


def _default_step_hours(query: ProgressedContactQuery) -> float:
    if query.kind_a is ProgressedTerminalKind.TRANSIT:
        return 1.0 if query.body_a == "Moon" else 6.0
    if query.kind_a is ProgressedTerminalKind.MINOR_PROGRESSED:
        return 6.0 if query.body_a == "Moon" else 24.0
    if "Moon" in {query.body_a, query.body_b}:
        return 120.0
    return 720.0


class _Evaluator:
    """
    RITE: The Progressed Contact Evaluator

    THEOREM: Owns one search-local mapping from civil instants to progressed
    contact evaluations under an explicit house and reader policy.

    RITE OF PURPOSE:
        Centralizes the reusable natal state, terminal construction, and
        memoized evaluation needed by one progressed-contact search.

    LAW OF OPERATION:
        Responsibilities:
            - Bind the natal chart, reader, house policy, and contact query.
            - Build required progressed terminals for candidate instants.
            - Cache evaluations only within this evaluator instance.
        Non-responsibilities:
            - Select global kernels or mutate public doctrine.
            - Persist results beyond the owning search.
        Dependencies:
            - Planetary reader, progressed terminal builders, and house engine.
        Structural invariants:
            - The natal state and query remain fixed for the evaluator lifetime.
            - Cached values are keyed by the exact candidate datetime.

    Canon: Church of Light progressed-aspect timing doctrine as admitted by
    this module.

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.progressed_astrodynes_search._Evaluator",
      "risk": "high",
      "api": {"public_methods": [], "internal_methods": ["_terminal_map"]},
      "state": {"mutable": true, "owners": ["one progressed-contact search"]},
      "effects": {"signals_emitted": [], "io": ["reader-backed computation"]},
      "concurrency": {
        "thread": "pure_computation",
        "cross_thread_calls": "safe_read_only"
      },
      "failures": {"raises": ["ValueError", "OutOfRangeError"], "policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    def __init__(
        self,
        natal_dt: datetime,
        observer_lat: float,
        observer_lon: float,
        query: ProgressedContactQuery,
        *,
        house_system: str,
        allow_house_fallback: bool,
        reader,
        reenforces_major: ProgressedContactQuery | None,
    ) -> None:
        self.natal_dt = natal_dt
        self.observer_lat = observer_lat
        self.observer_lon = observer_lon
        self.query = query
        self.house_system = house_system
        self.allow_house_fallback = allow_house_fallback
        self.reader = reader
        self.reenforces_major = reenforces_major
        if self.reader is None:
            self.reader = get_reader()
        self.natal_jd = jd_from_datetime(natal_dt)
        self.house_policy = (
            HousePolicy.default() if allow_house_fallback else HousePolicy.strict()
        )
        self.natal_houses = calculate_houses(
            self.natal_jd,
            observer_lat,
            observer_lon,
            system=house_system,
            policy=self.house_policy,
        )
        self.natal_noon_jd, _, self.limiting_date = _limiting_date(natal_dt)
        self.natal_sun = planet_at("Sun", self.natal_jd, reader=self.reader).longitude
        self.natal_moon = planet_at("Moon", self.natal_jd, reader=self.reader).longitude
        self.solar_constant = (
            self.natal_sun - self.natal_moon + 180.0
        ) % 360.0 - 180.0
        radical = _terminal_set(
            self.reader,
            self.natal_jd,
            ProgressedTerminalKind.RADICAL,
            self.natal_houses,
            self.natal_sun,
            self.natal_houses.mc,
            observer_lat,
            house_system,
            self.house_policy,
        )
        self.radical = {item.terminal_id: item for item in radical}
        self.natal = _natal_values(radical, tuple(self.natal_houses.cusps))
        self.cache: dict[datetime, _Evaluation] = {}

    def _terminal_map(self, value: datetime) -> dict[str, ProgressedAstrodyneTerminal]:
        required = {self.query.kind_a, self.query.kind_b}
        if self.reenforces_major is not None:
            required.update(
                {self.reenforces_major.kind_a, self.reenforces_major.kind_b}
            )
        if any(kind in _MAJOR_KINDS for kind in required):
            required.update(_MAJOR_KINDS)
        terminals = dict(self.radical)
        target_jd = jd_from_datetime(value)
        if ProgressedTerminalKind.MAJOR_PROGRESSED in required:
            _, _, _, major_jd = _major_ephemeris_jd(
                self.natal_noon_jd,
                self.limiting_date,
                value,
            )
            major = _terminal_set(
                self.reader,
                major_jd,
                ProgressedTerminalKind.MAJOR_PROGRESSED,
                self.natal_houses,
                self.natal_sun,
                self.natal_houses.mc,
                self.observer_lat,
                self.house_system,
                self.house_policy,
            )
            terminals.update((item.terminal_id, item) for item in major)
        if ProgressedTerminalKind.MINOR_PROGRESSED in required:
            transit_sun = planet_at("Sun", target_jd, reader=self.reader).longitude
            moon_target = (transit_sun - self.solar_constant) % 360.0
            age_years = (
                (target_jd - self.natal_jd)
                / DEFAULT_CHURCH_OF_LIGHT_PROGRESSION_POLICY.life_year_days
            )
            approximate = self.natal_jd + age_years * (
                DEFAULT_CHURCH_OF_LIGHT_PROGRESSION_POLICY.minor_ephemeris_days_per_year
            )
            minor_jd = _minor_ephemeris_jd(
                self.reader,
                approximate,
                moon_target,
                DEFAULT_CHURCH_OF_LIGHT_PROGRESSION_POLICY,
            )
            minor = _terminal_set(
                self.reader,
                minor_jd,
                ProgressedTerminalKind.MINOR_PROGRESSED,
                self.natal_houses,
                self.natal_sun,
                self.natal_houses.mc,
                self.observer_lat,
                self.house_system,
                self.house_policy,
            )
            terminals.update((item.terminal_id, item) for item in minor)
        if ProgressedTerminalKind.TRANSIT in required:
            transit = _terminal_set(
                self.reader,
                target_jd,
                ProgressedTerminalKind.TRANSIT,
                self.natal_houses,
                self.natal_sun,
                self.natal_houses.mc,
                self.observer_lat,
                self.house_system,
                self.house_policy,
            )
            terminals.update((item.terminal_id, item) for item in transit)
        return terminals

    def __call__(self, value: datetime) -> _Evaluation:
        value = _aware_utc(value, "evaluation datetime")
        if value in self.cache:
            return self.cache[value]
        terminals = self._terminal_map(value)
        relation = _relation(self.query, terminals, self.natal)
        harmony = progressed_aspect_harmony(
            self.query.body_a,
            self.query.body_b,
            self.query.aspect,
            relation.moment_truth.power,
        )
        reinforcement = None
        reinforcement_power = None
        reenforced_power = None
        if self.reenforces_major is not None:
            if not isinstance(relation, ProgressedAccessoryAspectRelation) or relation.tier.value != "minor":
                raise ValueError("reenforcement search requires a minor-progressed contact")
            major = _relation(self.reenforces_major, terminals, self.natal)
            if not isinstance(major, ProgressedMajorAspectRelation):
                raise ValueError("reenforces_major must describe a major relation")
            lawful_ids = {
                item.terminal_id
                for item in (*major.direct_terminals, *major.indirect_terminals)
            }
            if relation.target_terminal.terminal_id not in lawful_ids:
                raise ValueError("minor target is not a terminal of reenforces_major")
            reinforcement = reenforce_major_progressed_relation(major, relation)
            reinforcement_power = reinforcement.moment_truth.power * reinforcement.terminal_factor
            reenforced_power = reinforcement.reenforced_power
        moment = ProgressedContactMoment(
            event="sample",
            dt=value,
            jd_ut=jd_from_datetime(value),
            distance_arcmin=relation.distance_arcmin,
            power=relation.moment_truth.power,
            harmony=harmony.total_harmony,
            discord=harmony.total_discord,
            relation_id=relation.relation_id,
            reenforcement_power=reinforcement_power,
            reenforced_major_power=reenforced_power,
        )
        result = _Evaluation(moment, relation, reinforcement)
        self.cache[value] = result
        return result


def _with_event(moment: ProgressedContactMoment, event: str) -> ProgressedContactMoment:
    return ProgressedContactMoment(
        event=event,
        dt=moment.dt,
        jd_ut=moment.jd_ut,
        distance_arcmin=moment.distance_arcmin,
        power=moment.power,
        harmony=moment.harmony,
        discord=moment.discord,
        relation_id=moment.relation_id,
        reenforcement_power=moment.reenforcement_power,
        reenforced_major_power=moment.reenforced_major_power,
    )


def _bisect_boundary(
    evaluator: _Evaluator,
    left: datetime,
    right: datetime,
    tolerance_seconds: float,
) -> ProgressedContactMoment:
    f_left = evaluator(left).moment.distance_arcmin - 60.0
    f_right = evaluator(right).moment.distance_arcmin - 60.0
    if f_left == 0.0:
        return evaluator(left).moment
    if f_right == 0.0:
        return evaluator(right).moment
    if f_left * f_right > 0.0:
        raise ValueError("boundary refinement requires a bracket")
    while (right - left).total_seconds() > tolerance_seconds:
        mid = left + (right - left) / 2
        f_mid = evaluator(mid).moment.distance_arcmin - 60.0
        if f_left * f_mid <= 0.0:
            right, f_right = mid, f_mid
        else:
            left, f_left = mid, f_mid
    return evaluator(left + (right - left) / 2).moment


def _minimize_distance(
    evaluator: _Evaluator,
    left: datetime,
    right: datetime,
    tolerance_seconds: float,
) -> ProgressedContactMoment:
    while (right - left).total_seconds() > tolerance_seconds:
        third = (right - left) / 3
        a, b = left + third, right - third
        if evaluator(a).moment.distance_arcmin <= evaluator(b).moment.distance_arcmin:
            right = b
        else:
            left = a
    return evaluator(left + (right - left) / 2).moment


def search_progressed_contacts(
    natal_dt: datetime,
    start_dt: datetime,
    end_dt: datetime,
    observer_lat: float,
    observer_lon: float,
    query: ProgressedContactQuery,
    *,
    house_system: str = HouseSystem.PLACIDUS,
    allow_house_fallback: bool = False,
    coarse_step_hours: float | None = None,
    boundary_tolerance_seconds: float = 1.0,
    perfection_tolerance_seconds: float = 1.0,
    perfection_distance_tolerance_arcmin: float = 0.01,
    max_samples: int = 50_000,
    reenforces_major: ProgressedContactQuery | None = None,
    reader=None,
) -> ProgressedContactSearchResult:
    """Find bounded one-degree contact windows and their closest approaches."""

    natal = _aware_utc(natal_dt, "natal_dt")
    start = _aware_utc(start_dt, "start_dt")
    end = _aware_utc(end_dt, "end_dt")
    if start < natal:
        raise ValueError("start_dt must not precede natal_dt")
    if end <= start:
        raise ValueError("end_dt must be later than start_dt")
    if not isinstance(query, ProgressedContactQuery):
        raise TypeError("query must be ProgressedContactQuery")
    step = _default_step_hours(query) if coarse_step_hours is None else coarse_step_hours
    policy = ProgressedContactSearchPolicy(
        step,
        boundary_tolerance_seconds,
        perfection_tolerance_seconds,
        perfection_distance_tolerance_arcmin,
        max_samples,
    )
    count = int(ceil((end - start).total_seconds() / (step * 3600.0))) + 1
    if count > policy.max_samples:
        raise ValueError(
            f"search requires {count} coarse samples, exceeding max_samples={policy.max_samples}"
        )
    evaluator = _Evaluator(
        natal,
        observer_lat,
        observer_lon,
        query,
        house_system=house_system,
        allow_house_fallback=allow_house_fallback,
        reader=reader,
        reenforces_major=reenforces_major,
    )
    times = [min(start + timedelta(hours=step * index), end) for index in range(count)]
    times[-1] = end
    distances = [evaluator(value).moment.distance_arcmin for value in times]
    windows: list[ProgressedContactWindow] = []
    index = 0
    while index < len(times):
        if distances[index] > 60.0:
            index += 1
            continue
        first = index
        while index + 1 < len(times) and distances[index + 1] <= 60.0:
            index += 1
        last = index
        if first == 0:
            entry = _with_event(evaluator(start).moment, "entry")
            entry_clipped = True
        else:
            entry = _with_event(
                _bisect_boundary(
                    evaluator,
                    times[first - 1],
                    times[first],
                    policy.boundary_tolerance_seconds,
                ),
                "entry",
            )
            entry_clipped = False
        if last == len(times) - 1:
            exit_moment = _with_event(evaluator(end).moment, "exit")
            exit_clipped = True
        else:
            exit_moment = _with_event(
                _bisect_boundary(
                    evaluator,
                    times[last],
                    times[last + 1],
                    policy.boundary_tolerance_seconds,
                ),
                "exit",
            )
            exit_clipped = False
        candidates = []
        for candidate in range(first, last + 1):
            left_distance = distances[candidate - 1] if candidate > first else float("inf")
            right_distance = distances[candidate + 1] if candidate < last else float("inf")
            if distances[candidate] <= left_distance and distances[candidate] <= right_distance:
                left = entry.dt if candidate == first else times[candidate - 1]
                right = exit_moment.dt if candidate == last else times[candidate + 1]
                minimum = _minimize_distance(
                    evaluator, left, right, policy.perfection_tolerance_seconds
                )
                event = (
                    "perfection"
                    if minimum.distance_arcmin
                    <= policy.perfection_distance_tolerance_arcmin
                    else "closest_approach"
                )
                candidates.append(_with_event(minimum, event))
        deduplicated = []
        for candidate in sorted(candidates, key=lambda item: item.dt):
            if not deduplicated or abs(
                (candidate.dt - deduplicated[-1].dt).total_seconds()
            ) > policy.perfection_tolerance_seconds * 2.0:
                deduplicated.append(candidate)
        windows.append(
            ProgressedContactWindow(
                entry,
                tuple(deduplicated),
                exit_moment,
                entry_clipped,
                exit_clipped,
            )
        )
        index += 1
    return ProgressedContactSearchResult(
        query,
        start,
        end,
        policy,
        len(times),
        tuple(windows),
        reenforces_major,
    )


def integrate_progressed_influence(
    natal_dt: datetime,
    start_dt: datetime,
    end_dt: datetime,
    observer_lat: float,
    observer_lon: float,
    query: ProgressedContactQuery,
    *,
    house_system: str = HouseSystem.PLACIDUS,
    allow_house_fallback: bool = False,
    max_step_hours: float = 6.0,
    max_samples: int = 50_000,
    reader=None,
) -> ProgressedVariableInfluenceTruth:
    """Integrate actual ephemeris-varying instantaneous power over an interval."""

    natal = _aware_utc(natal_dt, "natal_dt")
    start = _aware_utc(start_dt, "start_dt")
    end = _aware_utc(end_dt, "end_dt")
    if start < natal:
        raise ValueError("start_dt must not precede natal_dt")
    if end <= start:
        raise ValueError("end_dt must be later than start_dt")
    step = _positive(max_step_hours, "max_step_hours")
    if isinstance(max_samples, bool) or not isinstance(max_samples, int):
        raise TypeError("max_samples must be an integer")
    if max_samples < 3:
        raise ValueError("max_samples must be at least 3")
    duration_hours = (end - start).total_seconds() / 3600.0
    fine_intervals = max(2, int(ceil(duration_hours / step)))
    if fine_intervals % 2:
        fine_intervals += 1
    required_samples = fine_intervals + 1
    if required_samples > max_samples:
        raise ValueError(
            f"integration requires {required_samples} samples, exceeding max_samples={max_samples}"
        )
    evaluator = _Evaluator(
        natal,
        observer_lat,
        observer_lon,
        query,
        house_system=house_system,
        allow_house_fallback=allow_house_fallback,
        reader=reader,
        reenforces_major=None,
    )

    duration = end - start
    duration_days = duration_hours / 24.0
    fine_times = tuple(
        start + duration * (index / fine_intervals)
        for index in range(fine_intervals + 1)
    )
    coarse_times = fine_times[::2]

    def integrate(sample_times: tuple[datetime, ...]) -> tuple[float, float, float]:
        subintervals = len(sample_times) - 1
        dt_days = duration_days / subintervals
        totals = [0.0, 0.0, 0.0]
        previous = evaluator(sample_times[0]).moment
        for sample_time in sample_times[1:]:
            current = evaluator(sample_time).moment
            for slot, name in enumerate(("power", "harmony", "discord")):
                totals[slot] += (
                    getattr(previous, name) + getattr(current, name)
                ) * 0.5 * dt_days
            previous = current
        return tuple(totals)  # type: ignore[return-value]

    fine = integrate(fine_times)
    coarse = integrate(coarse_times)
    evaluated = tuple(evaluator.cache.values())
    closest = min(evaluated, key=lambda item: item.moment.distance_arcmin)
    endpoints_are_orb_limits = all(
        abs(evaluator(value).moment.distance_arcmin - 60.0) <= 0.1
        for value in (start, end)
    )
    comparator = (
        closest.relation.peak_truth.peak_power * 0.75 * duration_days
        if endpoints_are_orb_limits
        else None
    )
    return ProgressedVariableInfluenceTruth(
        query=query,
        start_dt=start,
        end_dt=end,
        duration_days=duration_days,
        method="composite_trapezoid_actual_ephemeris",
        max_step_hours=step,
        sample_count=len(evaluator.cache),
        total_power_days=fine[0],
        total_harmony_days=fine[1],
        total_discord_days=fine[2],
        average_power=fine[0] / duration_days,
        average_harmony=fine[1] / duration_days,
        average_discord=fine[2] / duration_days,
        coarse_total_power_days=coarse[0],
        # Composite trapezoid error is O(h^2).  The exact 2:1 nested mesh
        # therefore admits the Richardson divisor 2^2 - 1 = 3.
        power_error_estimate_days=abs(fine[0] - coarse[0]) / 3.0,
        constant_rate_comparator_power_days=comparator,
        constant_rate_difference_days=(
            None if comparator is None else fine[0] - comparator
        ),
    )


__all__ = [
    "ProgressedContactMoment",
    "ProgressedContactQuery",
    "ProgressedContactSearchPolicy",
    "ProgressedContactSearchResult",
    "ProgressedContactWindow",
    "ProgressedVariableInfluenceTruth",
    "integrate_progressed_influence",
    "search_progressed_contacts",
]
