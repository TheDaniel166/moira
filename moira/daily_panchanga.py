"""Sunrise-owned daily Panchanga, composed over Moira's astronomical substrate.

The governing object is [local sunrise, next local sunrise). IMD's Rashtriya
Panchang explanation defines the four angular limbs and their ending moments;
B. V. Raman, A Manual of Hindu Astrology, section 65, defines the sunrise day.
See wiki/02_standards/DAILY_PANCHANGA_STANDARD.md for source and policy receipts.

Owns civil-date selection, daily limb coverage and boundary search. Delegates
positions to planets, solar crossings to rise_set, clocks to julian and limb
names/arithmetic to panchanga. No external ephemeris or runtime dependency.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, replace
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from enum import Enum
from functools import lru_cache
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .julian import _ut1_to_utc, datetime_from_jd, jd_from_datetime, utc_to_ut1
from .panchanga import (
    PanchangaElement, PanchangaResult, VARA_LORDS, VARA_NAMES,
    _normalize_ayanamsa_system_name, panchanga_at,
)
from .planets import planet_at
from .rise_set import find_phenomena
from .sidereal import list_ayanamsa_systems, tropical_to_sidereal
from .spk_reader import get_reader, use_reader_override

__all__ = [
    "PanchangaSunriseDefinition", "DailyPanchangaPolicy", "PanchangaMoment",
    "PanchangaSolarDate", "PanchangaLimbInterval", "PanchangaLimbDay",
    "DailyPanchangaProvenance", "DailyPanchangaResult", "daily_panchanga",
]


class PanchangaSunriseDefinition(str, Enum):
    """Named geometric center thresholds; no terrain or elevation model."""

    RASHTRIYA_UPPER_LIMB = "rashtriya_upper_limb"
    USNO_UPPER_LIMB = "usno_upper_limb"
    GEOMETRIC_CENTER = "geometric_center"

    @property
    def altitude_degrees(self) -> float:
        return {
            self.RASHTRIYA_UPPER_LIMB: -47.0 / 60.0,
            self.USNO_UPPER_LIMB: -50.0 / 60.0,
            self.GEOMETRIC_CENTER: 0.0,
        }[self]


def _finite_number(name: str, value: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a real number")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


@dataclass(frozen=True, slots=True)
class DailyPanchangaPolicy:
    """Explicit sunrise convention and numerical stopping tolerance.

    The tolerance bounds a root bracket, not observational sunrise accuracy.
    Hourly bracketing and a 72-hour search cap are fixed product bounds.
    """

    ayanamsa_system: str = "Lahiri"
    sunrise_definition: PanchangaSunriseDefinition = PanchangaSunriseDefinition.RASHTRIYA_UPPER_LIMB
    solver_tolerance_seconds: float = 0.1

    def __post_init__(self) -> None:
        if not isinstance(self.ayanamsa_system, str):
            raise TypeError("ayanamsa_system must be a named system")
        system = _normalize_ayanamsa_system_name(self.ayanamsa_system)
        if system not in list_ayanamsa_systems():
            raise ValueError(f"Unknown ayanamsa system {self.ayanamsa_system!r}")
        object.__setattr__(self, "ayanamsa_system", system)
        if not isinstance(self.sunrise_definition, PanchangaSunriseDefinition):
            raise TypeError("sunrise_definition must be PanchangaSunriseDefinition")
        _finite_number("solver_tolerance_seconds", self.solver_tolerance_seconds)
        if not 0.01 <= self.solver_tolerance_seconds <= 1.0:
            raise ValueError("solver_tolerance_seconds must be within [0.01, 1]")


@dataclass(frozen=True, slots=True)
class PanchangaMoment:
    """One astronomical instant, with explicitly converted civil displays."""

    jd_ut1: float
    utc: datetime
    local: datetime


@dataclass(frozen=True, slots=True)
class PanchangaSolarDate:
    """All admitted solar crossings in one half-open local civil date."""

    local_date: date
    civil_start: PanchangaMoment
    civil_end: PanchangaMoment
    sunrises: tuple[PanchangaMoment, ...]
    sunsets: tuple[PanchangaMoment, ...]


@dataclass(frozen=True, slots=True)
class PanchangaLimbInterval:
    """A limb's coverage within the day and its actual astronomical ending.

    coverage_start can be sunrise inside an already-running limb. coverage_end
    is clipped to next sunrise; ending is never clipped and may be on a later
    date. Intervals use the entered limb at a boundary (half-open ownership).
    """

    index: int
    number: int
    name: str
    coverage_start: PanchangaMoment
    coverage_end: PanchangaMoment
    ending: PanchangaMoment

    def __post_init__(self) -> None:
        if type(self.index) is not int or self.index < 0 or self.number != self.index + 1:
            raise ValueError("limb interval index/number must be consistent")
        if not self.name or not (self.coverage_start.jd_ut1 < self.coverage_end.jd_ut1
                                 <= self.ending.jd_ut1):
            raise ValueError("limb coverage must be nonempty and end no later than its ending")


@dataclass(frozen=True, slots=True)
class PanchangaLimbDay:
    """Complete ordered coverage and comparison of successive sunrise limbs."""

    limb: str
    intervals: tuple[PanchangaLimbInterval, ...]
    index_at_sunrise: int
    index_at_next_sunrise: int
    repeated_at_next_sunrise: bool
    skipped_at_sunrise_indices: tuple[int, ...]

    def __post_init__(self) -> None:
        counts = {"tithi": 30, "nakshatra": 27, "yoga": 27, "karana": 60}
        count = counts.get(self.limb)
        if count is None or not self.intervals:
            raise ValueError("limb day must name an admitted limb with nonempty coverage")
        indices = (self.index_at_sunrise, self.index_at_next_sunrise,
                   *(part.index for part in self.intervals))
        if any(type(index) is not int or not 0 <= index < count for index in indices):
            raise ValueError("limb indices must be in their cycle")
        if self.intervals[0].index != self.index_at_sunrise:
            raise ValueError("first interval must belong to the sunrise limb")
        for a, b in zip(self.intervals, self.intervals[1:]):
            if a.coverage_end != b.coverage_start or b.index != (a.index + 1) % count:
                raise ValueError("limb coverage must be contiguous and sequential")
        advance = (self.index_at_next_sunrise - self.index_at_sunrise) % count
        expected_skipped = tuple((self.index_at_sunrise + i) % count for i in range(1, advance))
        if (self.repeated_at_next_sunrise != (advance == 0)
                or self.skipped_at_sunrise_indices != expected_skipped):
            raise ValueError("repeated/skipped evidence must match successive sunrise indices")


@dataclass(frozen=True, slots=True)
class DailyPanchangaProvenance:
    """Reader, coordinate, clock, and solar-event conventions for a daily Panchanga."""

    reader_binding: str
    longitude_origin: str = "geocentric"
    longitude_frame: str = "apparent_ecliptic_of_date"
    sidereal_mode: str = "true"
    event_timescale: str = "UT1"
    civil_clock: str = "moira.julian UTC/UT1 conversion"
    vara_basis: str = "requested_local_civil_weekday_owned_by_sunrise"
    day_boundary: str = "[sunrise, next_sunrise)"
    sunrise_altitude_degrees: float = -47.0 / 60.0
    bracket_step_seconds: int = 3600
    maximum_search_hours: int = 72
    horizon_model: str = "level_horizon_zero_elevation_no_terrain"


@dataclass(frozen=True, slots=True)
class DailyPanchangaResult:
    """A local sunrise day with its Panchanga limbs and explicit availability."""

    local_date: date
    timezone: str
    latitude: float
    longitude: float
    policy: DailyPanchangaPolicy
    provenance: DailyPanchangaProvenance
    status: str
    unavailable_reasons: tuple[str, ...]
    solar_date: PanchangaSolarDate
    next_solar_date: PanchangaSolarDate
    at_sunrise: PanchangaResult | None
    limbs: tuple[PanchangaLimbDay, ...]

    def __post_init__(self) -> None:
        if (self.solar_date.local_date != self.local_date
                or self.next_solar_date.local_date != self.local_date + timedelta(days=1)):
            raise ValueError("solar dates must belong to the requested and next civil dates")
        if self.status == "unavailable":
            if not self.unavailable_reasons or self.at_sunrise is not None or self.limbs:
                raise ValueError("unavailable daily Panchanga must not fabricate limb truth")
        elif self.status == "available":
            if (self.unavailable_reasons or self.at_sunrise is None
                    or self.sunrise is None or self.next_sunrise is None
                    or tuple(limb.limb for limb in self.limbs) != ("tithi", "nakshatra", "yoga", "karana")):
                raise ValueError("available daily Panchanga requires two sunrises and all four angular limbs")
            for limb in self.limbs:
                if (limb.intervals[0].coverage_start != self.sunrise
                        or limb.intervals[-1].coverage_end != self.next_sunrise):
                    raise ValueError("limbs must cover the entire sunrise day")
        else:
            raise ValueError("daily Panchanga status must be available or unavailable")

    @property
    def sunrise(self) -> PanchangaMoment | None:
        events = self.solar_date.sunrises
        return events[0] if len(events) == 1 else None

    @property
    def next_sunrise(self) -> PanchangaMoment | None:
        events = self.next_solar_date.sunrises
        return events[0] if len(events) == 1 else None


def _resolve_timezone(key: str) -> tzinfo:
    if not isinstance(key, str) or not key or len(key) > 128:
        raise ValueError("timezone must be an IANA key, UTC, or UTC+/-HH:MM")
    if key == "UTC":
        return timezone.utc
    match = re.fullmatch(r"UTC([+-])(\d{2}):(\d{2})", key)
    if match:
        hours, minutes = int(match[2]), int(match[3])
        if hours > 23 or minutes > 59:
            raise ValueError("invalid fixed UTC offset")
        offset = timedelta(hours=hours, minutes=minutes)
        return timezone(offset if match[1] == "+" else -offset)
    try:
        return ZoneInfo(key)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise ValueError(f"Unknown or unavailable IANA timezone {key!r}") from exc


def _civil_datetimes(local_date: date, zone: tzinfo) -> tuple[datetime, datetime]:
    """Fold 0 owns a repeated midnight; a midnight gap starts after the gap.

    A wholly skipped date has no interval and is rejected. Conversion back to
    the zone witnesses that the selected boundary really belongs to the date.
    """
    next_date = local_date + timedelta(days=1)
    start = datetime.combine(local_date, time(), zone)
    end = datetime.combine(next_date, time(), zone)
    for boundary, expected in ((start, local_date), (end, next_date)):
        if boundary.astimezone(timezone.utc).astimezone(zone).date() != expected:
            raise ValueError("requested date or adjacent date is skipped in timezone")
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


def _civil_bounds(local_date: date, zone: tzinfo) -> tuple[float, float]:
    start, end = _civil_datetimes(local_date, zone)
    return utc_to_ut1(jd_from_datetime(start)), utc_to_ut1(jd_from_datetime(end))


def _moment(jd: float, zone: tzinfo) -> PanchangaMoment:
    utc = datetime_from_jd(_ut1_to_utc(jd))
    return PanchangaMoment(jd, utc, utc.astimezone(zone))


def _solar_date(local_date: date, zone: tzinfo, latitude: float,
                longitude: float, altitude: float) -> PanchangaSolarDate:
    start, end = _civil_bounds(local_date, zone)
    civil_start, civil_end = _civil_datetimes(local_date, zone)
    found: dict[str, list[float]] = {"Rise": [], "Set": []}
    # find_phenomena owns 24h searches and returns one event per kind. Half-day
    # overlapping searches also recover the earlier crossing if a 24h search
    # contains two. Keep only this civil date and merge repeated root witnesses.
    cursor = start - 0.5
    while cursor < end:
        events = find_phenomena("Sun", cursor, latitude, longitude, altitude=altitude)
        for kind in found:
            jd = events.get(kind)
            if (jd is not None and start <= jd < end
                    and all(abs(jd - existing) * 86400.0 > 1.0 for existing in found[kind])):
                found[kind].append(jd)
        cursor += 0.5
    return PanchangaSolarDate(
        # Preserve the exact civil anchors. Converting their JD float back to
        # datetime can land one ulp before midnight (or a DST transition).
        local_date,
        PanchangaMoment(start, civil_start, civil_start.astimezone(zone)),
        PanchangaMoment(end, civil_end, civil_end.astimezone(zone)),
        tuple(_moment(jd, zone) for jd in sorted(found["Rise"])),
        tuple(_moment(jd, zone) for jd in sorted(found["Set"])),
    )


_LIMBS = (("tithi", 12.0, 30), ("nakshatra", 360.0 / 27, 27),
          ("yoga", 360.0 / 27, 27), ("karana", 6.0, 60))


def _limb_identity(snapshot: PanchangaResult, limb: str) -> tuple[int, str]:
    value = getattr(snapshot, limb)
    if limb == "nakshatra":
        return value.nakshatra_index, value.nakshatra
    return value.index, value.name


def _solve_limb_day(limb: str, span: float, count: int, start: float,
                    end: float, snapshot_at, phases_at, zone: tzinfo,
                    tolerance_seconds: float) -> PanchangaLimbDay:
    """Find every entered span by following the continuous forward phase.

    A one-hour step must advance by less than half a span. Violation is a
    search failure, never silently repaired by modulo/index guessing. Roots
    are bracketed on the actual moving phase, not a mean speed interpolation.
    """
    position = dict((name, i) for i, (name, _, _) in enumerate(_LIMBS))[limb]
    index, name = _limb_identity(snapshot_at(start), limb)
    first_index = index
    interval_start = start
    left = start
    left_phase = phases_at(left)[position]
    remaining = span - (left_phase - index * span)
    # Fractional spans can round differently at their exact boundary. The
    # canonical instant's index owns that boundary; only ulp noise is tolerated.
    if not 0.0 < remaining <= span + 1e-12:
        raise RuntimeError("daily Panchanga phase and canonical limb disagree")
    intervals: list[PanchangaLimbInterval] = []
    transitions = 0
    cap = start + 3.0
    while left < cap:
        right = min(left + 1.0 / 24.0, cap)
        right_phase = phases_at(right)[position]
        advance = (right_phase - left_phase) % 360.0
        if not 0.0 < advance < span / 2.0:
            raise RuntimeError("daily Panchanga forward phase bound violated")
        if advance < remaining:
            remaining -= advance
            left, left_phase = right, right_phase
            continue
        low, high = left, right
        while (high - low) * 86400.0 > tolerance_seconds:
            mid = (low + high) / 2.0
            progress = (phases_at(mid)[position] - left_phase) % 360.0
            if progress < remaining:
                low = mid
            else:
                high = mid
        # Return the entered side of the root bracket: the ending belongs to
        # the new limb. Numerical error is <= the declared bracket tolerance.
        root = high
        intervals.append(PanchangaLimbInterval(
            index, index + 1, name, _moment(interval_start, zone),
            _moment(min(root, end), zone), _moment(root, zone),
        ))
        if root >= end:
            next_index, _ = _limb_identity(snapshot_at(end), limb)
            expected = (first_index + transitions) % count
            if root == end:
                expected = (expected + 1) % count
            if next_index != expected:
                # Sunrise inside the final root bracket is owned by the
                # actual phase at sunrise, not the rounded root time.
                if not (low <= end <= high and next_index == (index + 1) % count):
                    raise RuntimeError("daily Panchanga sunrise/transition ownership mismatch")
            skipped = tuple((first_index + i) % count for i in range(1, transitions + 1)
                            if (first_index + i) % count != next_index)
            return PanchangaLimbDay(limb, tuple(intervals), first_index,
                                    next_index, first_index == next_index, skipped)
        transitions += 1
        interval_start = root
        index = (index + 1) % count
        entered_index, name = _limb_identity(snapshot_at(root), limb)
        if entered_index != index:
            raise RuntimeError("daily Panchanga root disagrees with canonical entered limb")
        left, left_phase = root, phases_at(root)[position]
        remaining = span - (left_phase - index * span)
    raise RuntimeError("daily Panchanga limb ending exceeds 72-hour search cap")


def daily_panchanga(local_date: date, latitude: float, longitude: float, *,
                    timezone: str, policy: DailyPanchangaPolicy | None = None,
                    reader=None) -> DailyPanchangaResult:
    """Compute the daily almanac for a local Gregorian date and location.

    Requires two consecutive extant civil dates with exactly one sunrise each.
    Solar absence/ambiguity is returned as unavailable; resource and numerical
    errors propagate. The reader is caller-owned, bound once and never closed.
    IANA zones require installed zoneinfo data; fixed UTC offsets do not.
    """
    if type(local_date) is not date:
        raise TypeError("local_date must be a date, not a datetime or string")
    if not date(1, 1, 2) <= local_date <= date(9999, 12, 27):
        raise ValueError("local_date must allow adjacent dates and 72-hour lookahead")
    for key, value in (("latitude", latitude), ("longitude", longitude)):
        _finite_number(key, value)
    if not -90.0 <= latitude <= 90.0 or not -180.0 <= longitude <= 180.0:
        raise ValueError("latitude/longitude must be within [-90,90]/[-180,180]")
    if policy is not None and not isinstance(policy, DailyPanchangaPolicy):
        raise TypeError("policy must be DailyPanchangaPolicy")
    selected = policy or DailyPanchangaPolicy()
    zone = _resolve_timezone(timezone)
    # Validate civil-date ownership before acquiring an ephemeris resource.
    _civil_bounds(local_date, zone)
    _civil_bounds(local_date + timedelta(days=1), zone)
    binding = "caller_owned_reader" if reader is not None else "active_or_default_reader"
    if reader is None:
        reader = get_reader()
    provenance = DailyPanchangaProvenance(
        reader_binding=binding,
        sunrise_altitude_degrees=selected.sunrise_definition.altitude_degrees,
    )
    with use_reader_override(reader):
        solar = _solar_date(local_date, zone, latitude, longitude,
                            provenance.sunrise_altitude_degrees)
        following = _solar_date(local_date + timedelta(days=1), zone, latitude,
                                longitude, provenance.sunrise_altitude_degrees)
        reasons = tuple(
            f"{label}_{'absent' if not day.sunrises else 'ambiguous'}"
            for label, day in (("sunrise", solar), ("next_sunrise", following))
            if len(day.sunrises) != 1
        )
        if reasons:
            return DailyPanchangaResult(local_date, timezone, latitude, longitude,
                selected, provenance, "unavailable", reasons, solar, following, None, ())
        start, end = solar.sunrises[0].jd_ut1, following.sunrises[0].jd_ut1
        if not start < end or end - start > 2.0:
            raise RuntimeError("daily Panchanga sunrise bounds invalid")

        @lru_cache(maxsize=4096)
        def longitudes_at(jd):
            return tuple(planet_at(body, jd, reader=reader).longitude for body in ("Sun", "Moon"))

        @lru_cache(maxsize=4096)
        def snapshot_at(jd):
            sun, moon = longitudes_at(jd)
            return panchanga_at(sun, moon, jd, ayanamsa_system=selected.ayanamsa_system)

        @lru_cache(maxsize=4096)
        def phases_at(jd):
            sun, moon = longitudes_at(jd)
            sun_sid = tropical_to_sidereal(sun, jd, selected.ayanamsa_system)
            moon_sid = tropical_to_sidereal(moon, jd, selected.ayanamsa_system)
            elongation = (moon - sun) % 360.0
            return elongation, moon_sid, (sun_sid + moon_sid) % 360.0, elongation

        weekday = (local_date.weekday() + 1) % 7
        snapshot = replace(snapshot_at(start),
            vara=PanchangaElement(VARA_NAMES[weekday], weekday, weekday + 1, 0.0, 0.0),
            vara_lord=VARA_LORDS[weekday])
        limbs = tuple(_solve_limb_day(name, span, count, start, end, snapshot_at,
                                      phases_at, zone, selected.solver_tolerance_seconds)
                      for name, span, count in _LIMBS)
        return DailyPanchangaResult(local_date, timezone, latitude, longitude,
            selected, provenance, "available", (), solar, following, snapshot, limbs)
