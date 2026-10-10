"""Source-owned Abhijit/Brahma intervals, independent of Muhurta scoring.

Chintamani, Avasthi 2004, Vivaha vv.52/54: eighth daylight part and Wednesday
exclusion. Arunadatta on Ashtanga Hridaya Sutra 2.1: fixed pre-sunrise ghatis.
The old proportional-night Brahma calculation is an explicit compatibility
profile, not silently attributed to Arunadatta. See the admission standard.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime, timedelta
from fractions import Fraction
import math

from .daily_panchanga import (
    PanchangaMoment, PanchangaSolarDate, PanchangaSunriseDefinition,
    _civil_bounds, _moment, _resolve_timezone, _solar_date,
)
from .julian import _require_representable_time_jd
from .muhurta_search import MuhurtaCoverageError, MuhurtaResourceError
from .rise_set import _altitude
from .spk_reader import KernelReader, MissingKernelError, OutOfRangeError, get_reader, use_reader_override
from ._ephemeris_time import _EphemerisTimeBasisError, _bind_ephemeris_time

__all__ = [
    "NamedMuhurtaPolicy", "NamedMuhurtaAnchor", "NamedMuhurtaInterval",
    "NamedMuhurtaResult", "NamedMuhurtaDay", "named_muhurta_from_solar_times",
    "named_muhurta_for_date",
]

_CHINTAMANI = "Muhurta Chintamani, Avasthi 2004, Vivaha vv.52/54, pp.126-127"
_ARUNADATTA = "Arunadatta Sarvangasundara on Ashtanga Hridaya Sutrasthana 2.1"


def _number(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a finite number")
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError(f"{name} must be finite") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _jd(name, value):
    result = _number(name, value)
    _require_representable_time_jd(name, result)
    return result


@dataclass(frozen=True, slots=True)
class NamedMuhurtaPolicy:
    """Selected text/compatibility readings and dated solar-event policy."""

    brahma_basis: str = "arunadatta_fixed_ghati"
    abhijit_weekday_rule: str = "chintamani_wednesday_exclusion"
    sunrise_definition: PanchangaSunriseDefinition = PanchangaSunriseDefinition.RASHTRIYA_UPPER_LIMB
    solver_tolerance_seconds: float = 0.1
    abhijit_basis: str = field(init=False, default="chintamani_eighth_daylight_part")
    endpoint_convention: str = field(init=False, default="[start,end)")
    weekday_basis: str = field(init=False, default="Monday=0,Sunday=6; requested sunrise date")
    event_timescale: str = field(init=False, default="UT1")
    horizon_model: str = field(init=False, default="level_horizon_zero_elevation_no_terrain")
    maximum_civil_dates: int = field(init=False, default=3)

    def __post_init__(self):
        if self.brahma_basis not in ("arunadatta_fixed_ghati", "legacy_proportional_night_14"):
            raise ValueError("unsupported Brahma basis")
        if self.abhijit_weekday_rule not in ("chintamani_wednesday_exclusion", "geometry_only"):
            raise ValueError("unsupported Abhijit weekday rule")
        if not isinstance(self.sunrise_definition, PanchangaSunriseDefinition):
            raise TypeError("sunrise_definition must be PanchangaSunriseDefinition")
        if not 0.01 <= _number("solver_tolerance_seconds", self.solver_tolerance_seconds) <= 1:
            raise ValueError("solver tolerance must be in [0.01, 1] seconds")


@dataclass(frozen=True, slots=True)
class NamedMuhurtaAnchor:
    """One supplied or solved solar event with an explicit UT1 bracket."""

    kind: str
    jd_ut1: float
    lower_jd_ut1: float
    upper_jd_ut1: float
    basis: str
    moment: PanchangaMoment | None = None

    def __post_init__(self):
        if self.kind not in ("sunrise", "sunset", "previous_sunset"):
            raise ValueError("unknown solar anchor kind")
        low, jd, high = (_jd(name, getattr(self, name)) for name in
                         ("lower_jd_ut1", "jd_ut1", "upper_jd_ut1"))
        if not low <= jd <= high or self.basis not in ("caller_supplied_ut1", "solved_solar_crossing"):
            raise ValueError("solar anchor must agree with its bracket and basis")
        if self.moment is not None and self.moment.jd_ut1 != jd:
            raise ValueError("anchor civil moment disagrees with UT1")


@dataclass(frozen=True, slots=True)
class NamedMuhurtaInterval:
    """Half-open geometry and source-rule eligibility, retained separately."""

    name: str
    basis: str
    citations: tuple[str, ...]
    status: str
    unavailable_reasons: tuple[str, ...]
    eligibility: str
    eligibility_rule: str
    start_jd_ut1: float | None = None
    end_jd_ut1: float | None = None
    start_lower_jd_ut1: float | None = None
    start_upper_jd_ut1: float | None = None
    end_lower_jd_ut1: float | None = None
    end_upper_jd_ut1: float | None = None
    start: PanchangaMoment | None = None
    end: PanchangaMoment | None = None

    def __post_init__(self):
        if self.name not in ("Abhijit", "Brahma"):
            raise ValueError("unknown named Muhurta")
        endpoints = (self.start_jd_ut1, self.end_jd_ut1, self.start_lower_jd_ut1,
                     self.start_upper_jd_ut1, self.end_lower_jd_ut1, self.end_upper_jd_ut1)
        if self.status == "unavailable":
            if (not self.unavailable_reasons or any(x is not None for x in endpoints)
                    or self.start is not None or self.end is not None):
                raise ValueError("unavailable intervals require reasons and no endpoints")
        elif self.status == "available":
            if self.unavailable_reasons or any(x is None for x in endpoints):
                raise ValueError("available intervals require complete endpoint evidence")
            for value in endpoints:
                _jd("interval endpoint", value)
            if not (self.start_lower_jd_ut1 <= self.start_jd_ut1 <= self.start_upper_jd_ut1
                    < self.end_lower_jd_ut1 <= self.end_jd_ut1 <= self.end_upper_jd_ut1):
                raise ValueError("interval endpoints must be ordered and resolved")
            for moment, jd in ((self.start, self.start_jd_ut1), (self.end, self.end_jd_ut1)):
                if moment is not None and moment.jd_ut1 != jd:
                    raise ValueError("civil interval disagrees with UT1")
        else:
            raise ValueError("unknown interval availability")
        if self.eligibility not in ("excluded", "not_excluded_by_selected_rule", "not_evaluated"):
            raise ValueError("unknown eligibility state")

    def contains(self, jd_ut1: float) -> bool | None:
        """Geometric membership; None means unavailable or root uncertainty.

        Weekday exclusion remains separate from the geometric interval.
        """
        jd = _jd("query_jd_ut1", jd_ut1)
        if self.status == "unavailable":
            return None
        if jd < self.start_lower_jd_ut1 or jd >= self.end_upper_jd_ut1:
            return False
        if self.start_upper_jd_ut1 <= jd < self.end_lower_jd_ut1:
            return True
        return None


@dataclass(frozen=True, slots=True)
class NamedMuhurtaResult:
    """Canonical Abhijit and Brahma pair with per-window availability."""

    policy: NamedMuhurtaPolicy
    weekday: int
    sunrise: NamedMuhurtaAnchor | None
    sunset: NamedMuhurtaAnchor | None
    previous_sunset: NamedMuhurtaAnchor | None
    intervals: tuple[NamedMuhurtaInterval, ...]
    solar_policy_applied: bool

    def __post_init__(self):
        if not isinstance(self.policy, NamedMuhurtaPolicy) or type(self.weekday) is not int or not 0 <= self.weekday <= 6:
            raise ValueError("typed policy and weekday in [0, 6] are required")
        if tuple(x.name for x in self.intervals) != ("Abhijit", "Brahma"):
            raise ValueError("named intervals must contain Abhijit and Brahma in order")
        if type(self.solar_policy_applied) is not bool:
            raise TypeError("solar_policy_applied must be bool")

    @property
    def status(self) -> str:
        count = sum(x.status == "available" for x in self.intervals)
        return ("unavailable", "partial", "available")[count]


@dataclass(frozen=True, slots=True)
class NamedMuhurtaDay:
    """Civil sunrise-date composition; clock receipt is at civil midpoint."""

    local_date: date
    timezone: str
    latitude: float
    longitude: float
    result: NamedMuhurtaResult
    solar_dates: tuple[PanchangaSolarDate, ...]
    reader_binding: str
    kernel_label: str
    clock_jd_ut1: float
    clock_jd_tt: float
    clock_jd_tdb: float
    delta_t_source: str
    delta_t_seconds: float
    delta_t_correction_seconds: float
    tdb_minus_tt_seconds: float


def _point(kind, value):
    if value is None:
        return None
    jd = _jd(kind, value)
    return NamedMuhurtaAnchor(kind, jd, jd, jd, "caller_supplied_ut1")


def _fraction(a, b, numerator, denominator):
    x, y = Fraction.from_float(a), Fraction.from_float(b)
    return float(x + (y - x) * Fraction(numerator, denominator))


def _compose(sunrise, sunset, previous, weekday, policy, *, solved=False, missing=None):
    reasons = missing or {}
    windows = []
    for name in ("Abhijit", "Brahma"):
        is_day = name == "Abhijit"
        fixed = not is_day and policy.brahma_basis == "arunadatta_fixed_ghati"
        basis = policy.abhijit_basis if is_day else policy.brahma_basis
        citations = (_CHINTAMANI,) if is_day else ((_ARUNADATTA,) if fixed else ("Moira legacy is_brahma_muhurta; seasonal-night compatibility",))
        rule = policy.abhijit_weekday_rule if is_day else "not_evaluated"
        eligibility = ("excluded" if weekday == 2 else "not_excluded_by_selected_rule") if rule == "chintamani_wednesday_exclusion" else "not_evaluated"
        common = dict(name=name, basis=basis, citations=citations, eligibility=eligibility, eligibility_rule=rule)
        reason = None
        if sunrise is None:
            reason = reasons.get("sunrise", "sunrise_absent")
        elif is_day and sunset is None:
            reason = reasons.get("sunset", "following_sunset_absent")
        elif not is_day and not fixed and previous is None:
            reason = reasons.get("previous_sunset", "previous_sunset_absent")
        elif is_day and sunrise.upper_jd_ut1 >= sunset.lower_jd_ut1:
            reason = "daylight_anchor_order_uncertain"
        elif not is_day and not fixed and previous.upper_jd_ut1 >= sunrise.lower_jd_ut1:
            reason = "night_anchor_order_uncertain"
        if reason:
            windows.append(NamedMuhurtaInterval(**common, status="unavailable", unavailable_reasons=(reason,)))
            continue
        if fixed:
            values = []
            for seconds in (5760, 2880):
                values.append(tuple(float(Fraction.from_float(x) - Fraction(seconds, 86400))
                                    for x in (sunrise.jd_ut1, sunrise.lower_jd_ut1, sunrise.upper_jd_ut1)))
        else:
            left, right = (sunrise, sunset) if is_day else (previous, sunrise)
            indices = (7, 8) if is_day else (13, 14)
            values = [tuple(_fraction(a, b, i, 15) for a, b in (
                (left.jd_ut1, right.jd_ut1), (left.lower_jd_ut1, right.lower_jd_ut1),
                (left.upper_jd_ut1, right.upper_jd_ut1))) for i in indices]
        (start, slow, shigh), (end, elow, ehigh) = values
        if solved:
            slow, shigh = math.nextafter(slow, -math.inf), math.nextafter(shigh, math.inf)
            elow, ehigh = math.nextafter(elow, -math.inf), math.nextafter(ehigh, math.inf)
        if shigh >= elow:
            windows.append(NamedMuhurtaInterval(**common, status="unavailable", unavailable_reasons=("interval_endpoints_unresolved",)))
        else:
            windows.append(NamedMuhurtaInterval(**common, status="available", unavailable_reasons=(),
                start_jd_ut1=start, end_jd_ut1=end, start_lower_jd_ut1=slow,
                start_upper_jd_ut1=shigh, end_lower_jd_ut1=elow, end_upper_jd_ut1=ehigh))
    return NamedMuhurtaResult(policy, weekday, sunrise, sunset, previous, tuple(windows), solved)


def named_muhurta_from_solar_times(sunrise_jd_ut1: float, sunset_jd_ut1: float | None = None,
                                  previous_sunset_jd_ut1: float | None = None, *,
                                  weekday: int, policy: NamedMuhurtaPolicy | None = None) -> NamedMuhurtaResult:
    """Supplied UT1 anchors; weekday is Monday=0 through Sunday=6.

    Missing optional anchors yield per-window unavailability. Supplied anchors
    must be correctly ordered. Their astronomical identity is caller-owned.
    """
    active = NamedMuhurtaPolicy() if policy is None else policy
    if not isinstance(active, NamedMuhurtaPolicy):
        raise TypeError("policy must be NamedMuhurtaPolicy")
    if type(weekday) is not int or not 0 <= weekday <= 6:
        raise ValueError("weekday must be a strict integer in [0, 6], Monday=0")
    rise = _point("sunrise", _jd("sunrise_jd_ut1", sunrise_jd_ut1))
    setting, previous = _point("sunset", sunset_jd_ut1), _point("previous_sunset", previous_sunset_jd_ut1)
    if setting is not None and setting.jd_ut1 <= rise.jd_ut1:
        raise ValueError("sunset must follow sunrise")
    if previous is not None and previous.jd_ut1 >= rise.jd_ut1:
        raise ValueError("previous sunset must precede sunrise")
    return _compose(rise, setting, previous, weekday, active)


def _refine(event, kind, lat, lon, zone, policy):
    """Local root refinement over the existing rise/set geometric signal."""
    direction = 1 if kind == "sunrise" else -1
    def signal(jd):
        return direction * (_altitude(jd, lat, lon, "Sun", 1013.25, 10.0)
                            - policy.sunrise_definition.altitude_degrees)
    for width in (1, 2, 4, 8, 16, 32, 60):
        low, high = event.jd_ut1 - width / 86400, event.jd_ut1 + width / 86400
        left, right = signal(low), signal(high)
        if math.isfinite(left) and math.isfinite(right) and left <= 0 <= right:
            break
    else:
        return None
    for _ in range(64):
        if left == 0:
            high = low
            break
        if right == 0:
            low = high
            break
        if (high - low) * 86400 <= policy.solver_tolerance_seconds:
            break
        mid = (low + high) / 2
        value = signal(mid)
        if not math.isfinite(value) or mid in (low, high):
            return None
        if value == 0:
            low = high = mid
            break
        if value < 0:
            low, left = mid, value
        else:
            high, right = mid, value
    if (high - low) * 86400 > policy.solver_tolerance_seconds:
        return None
    jd = (low + high) / 2
    return NamedMuhurtaAnchor(kind, jd, low, high, "solved_solar_crossing", _moment(jd, zone))


def named_muhurta_for_date(local_date: date, latitude: float, longitude: float, *,
                           timezone: str, policy: NamedMuhurtaPolicy | None = None,
                           reader: KernelReader | None = None) -> NamedMuhurtaDay:
    """Intervals owned by the requested local sunrise date, with civil displays.

    Three local civil dates bound event discovery. No distant seasonal rise,
    fixed sunrise, civil-midnight clipping or inferred location is used.
    """
    if not isinstance(local_date, date) or isinstance(local_date, datetime) or not 2 <= local_date.year <= 9998:
        raise ValueError("local_date must be a date with year in [2, 9998]")
    active = NamedMuhurtaPolicy() if policy is None else policy
    if not isinstance(active, NamedMuhurtaPolicy):
        raise TypeError("policy must be NamedMuhurtaPolicy")
    lat, lon = _number("latitude", latitude), _number("longitude", longitude)
    if not -90 < lat < 90 or not -180 <= lon <= 180:
        raise ValueError("latitude must be in (-90,90), longitude in [-180,180]")
    zone = _resolve_timezone(timezone)
    dates = tuple(local_date + timedelta(days=i) for i in (-1, 0, 1))
    bounds = tuple(_civil_bounds(day, zone) for day in dates)  # skipped dates fail before reader access
    try:
        bound = get_reader() if reader is None else reader
        with use_reader_override(bound):
            clock = _bind_ephemeris_time((bounds[1][0] + bounds[1][1]) / 2, bound)
            solar = tuple(_solar_date(day, zone, lat, lon, active.sunrise_definition.altitude_degrees) for day in dates)
            rise = setting = previous = None
            missing = {}
            if len(solar[1].sunrises) != 1:
                missing["sunrise"] = "sunrise_absent" if not solar[1].sunrises else "multiple_sunrises_on_requested_date"
            else:
                witness = solar[1].sunrises[0]
                rise = _refine(witness, "sunrise", lat, lon, zone, active)
                if rise is None:
                    missing["sunrise"] = "sunrise_root_bracket_unresolved"
                elif not bounds[1][0] <= rise.lower_jd_ut1 <= rise.upper_jd_ut1 < bounds[1][1]:
                    rise = None
                    missing["sunrise"] = "sunrise_civil_date_ownership_uncertain"
                sunsets = sorted((x for day in solar for x in day.sunsets), key=lambda x: x.jd_ut1)
                before, after = [x for x in sunsets if x.jd_ut1 < witness.jd_ut1], [x for x in sunsets if x.jd_ut1 > witness.jd_ut1]
                if before:
                    previous = _refine(before[-1], "previous_sunset", lat, lon, zone, active)
                    if previous is None:
                        missing["previous_sunset"] = "previous_sunset_root_bracket_unresolved"
                if after:
                    setting = _refine(after[0], "sunset", lat, lon, zone, active)
                    if setting is None:
                        missing["sunset"] = "sunset_root_bracket_unresolved"
            result = _compose(rise, setting, previous, local_date.weekday(), active, solved=True, missing=missing)
            intervals = tuple(replace(x, start=_moment(x.start_jd_ut1, zone), end=_moment(x.end_jd_ut1, zone))
                              if x.status == "available" else x for x in result.intervals)
            return NamedMuhurtaDay(local_date, timezone, lat, lon, replace(result, intervals=intervals), solar,
                "active_context_reader" if reader is None else "caller_owned_reader", clock.identity.summary_label,
                clock.jd_ut1, clock.epoch_tt, clock.epoch_tdb, clock.raw_delta_t.source_product,
                clock.delta_t_seconds, clock.delta_t_correction_seconds, clock.tdb_minus_tt_seconds)
    except OutOfRangeError as exc:
        raise MuhurtaCoverageError("named Muhurta date or adjacent solar dates are outside kernel coverage") from exc
    except (MissingKernelError, _EphemerisTimeBasisError, LookupError, FileNotFoundError) as exc:
        raise MuhurtaResourceError("required named Muhurta reader or clock resource is unavailable") from exc
