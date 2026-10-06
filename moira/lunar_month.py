"""Source-declared lunar-month context, separate from the sunrise day.

Object: geocentric conjunction-to-conjunction lunations and the sidereal
solar sign containing their opening conjunction.  Solar signs name months
Vaisakha through Chaitra.  Zero/one/two ingresses preserve adhika/ordinary/
omitted-month evidence, without applying a hidden historical remapping.

Ordinary Purnimanta months use the amanta lunation beginning a fortnight
later.  Intercalary neighbourhoods require a distinct regional rule set:
the official 1948 SE table itself interrupts a simple full-moon sequence.
Such mappings are explicitly unavailable here, with all lunation evidence
retained.  See wiki/02_standards/LUNAR_MONTH_AND_FESTIVAL_POLICY.md.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from typing import Literal

from .daily_panchanga import DailyPanchangaPolicy, _finite_number
from .planets import planet_at
from .sidereal import tropical_to_sidereal
from .spk_reader import get_reader, use_reader_override

__all__ = [
    "LunarMonthSystem", "LunarMonthPolicy", "CalendarBoundary",
    "LunarMonthLabel", "LunarLunation", "LunarMonthProvenance",
    "LunarMonthResult", "lunar_month_at",
]

_MONTHS = ("Chaitra", "Vaisakha", "Jyaishtha", "Ashadha", "Sravana",
           "Bhadrapada", "Asvina", "Kartika", "Margasirsha", "Pausha",
           "Magha", "Phalguna")
_SOURCE = ("PAC Rashtriya Panchang 1948 SE, printed vi-vii and xii-xiii; "
           "S.K. Chatterjee, Indian Calendars, printed 93-94")


class LunarMonthSystem(str, Enum):
    AMANTA = "amanta"
    PURNIMANTA = "purnimanta"


@dataclass(frozen=True, slots=True)
class LunarMonthPolicy:
    system: LunarMonthSystem = LunarMonthSystem.AMANTA
    ayanamsa_system: str = "Lahiri"
    solver_tolerance_seconds: float = 0.1

    def __post_init__(self) -> None:
        if not isinstance(self.system, LunarMonthSystem):
            raise TypeError("system must be LunarMonthSystem")
        checked = DailyPanchangaPolicy(
            ayanamsa_system=self.ayanamsa_system,
            solver_tolerance_seconds=self.solver_tolerance_seconds,
        )
        object.__setattr__(self, "ayanamsa_system", checked.ayanamsa_system)


@dataclass(frozen=True, slots=True)
class CalendarBoundary:
    """Entered side of a root and its complete numerical uncertainty bracket."""

    kind: Literal["new_moon", "full_moon", "solar_ingress"]
    target_degrees: float
    lower_jd_ut1: float
    upper_jd_ut1: float

    def __post_init__(self) -> None:
        if self.kind not in ("new_moon", "full_moon", "solar_ingress"):
            raise ValueError("unknown calendar boundary")
        for name in ("target_degrees", "lower_jd_ut1", "upper_jd_ut1"):
            _finite_number(name, getattr(self, name))
        if not 0 <= self.target_degrees < 360 or self.lower_jd_ut1 > self.upper_jd_ut1:
            raise ValueError("invalid calendar boundary target or bracket")
        if (self.upper_jd_ut1 - self.lower_jd_ut1) * 86400 > 1.0001:
            raise ValueError("calendar boundary exceeds the maximum one-second bracket")
        if ((self.kind == "new_moon" and self.target_degrees != 0)
                or (self.kind == "full_moon" and self.target_degrees != 180)
                or (self.kind == "solar_ingress" and self.target_degrees % 30 != 0)):
            raise ValueError("calendar boundary kind must match its angular target")

    @property
    def jd_ut1(self) -> float:
        return self.upper_jd_ut1


@dataclass(frozen=True, slots=True)
class LunarMonthLabel:
    index: int
    name: str
    qualifier: Literal["ordinary", "adhika", "ksaya_context"]

    def __post_init__(self) -> None:
        if type(self.index) is not int or not 0 <= self.index < 12:
            raise ValueError("month index must be an integer in [0,11]")
        if self.name != _MONTHS[self.index] or self.qualifier not in (
                "ordinary", "adhika", "ksaya_context"):
            raise ValueError("month label must match its canonical identity")


@dataclass(frozen=True, slots=True)
class LunarLunation:
    start: CalendarBoundary
    end: CalendarBoundary
    solar_rashi_at_start: int
    ingresses: tuple[CalendarBoundary, ...]
    uncertain_ingresses: tuple[CalendarBoundary, ...]
    label: LunarMonthLabel | None
    omitted_months: tuple[str, ...]

    def __post_init__(self) -> None:
        if (self.start.kind != "new_moon" or self.end.kind != "new_moon"
                or not self.start.jd_ut1 < self.end.lower_jd_ut1
                or type(self.solar_rashi_at_start) is not int
                or not 0 <= self.solar_rashi_at_start < 12):
            raise ValueError("lunation requires ordered conjunctions and a solar sign")
        if len(self.ingresses) > 2:
            raise ValueError("lunation cannot contain more than two admitted ingresses")
        for event in self.ingresses:
            if (event.kind != "solar_ingress" or not
                    self.start.jd_ut1 < event.lower_jd_ut1 <= event.jd_ut1 < self.end.lower_jd_ut1):
                raise ValueError("certain ingresses must lie inside the lunation")
        for a, b in zip(self.ingresses, self.ingresses[1:]):
            if a.jd_ut1 >= b.lower_jd_ut1:
                raise ValueError("ingresses must be ordered and disjoint")
        for event in self.uncertain_ingresses:
            if event.kind != "solar_ingress" or not any(
                event.lower_jd_ut1 <= edge.jd_ut1 and event.jd_ut1 >= edge.lower_jd_ut1
                for edge in (self.start, self.end)
            ):
                raise ValueError("uncertain ingress must overlap a conjunction bracket")
        if self.uncertain_ingresses:
            if self.label is not None or self.omitted_months:
                raise ValueError("uncertain ingress ordering cannot assert a month label")
        else:
            month_index = (self.solar_rashi_at_start + 1) % 12
            count = len(self.ingresses)
            qualifier = ("adhika", "ordinary", "ksaya_context")[count]
            if self.label != LunarMonthLabel(month_index, _MONTHS[month_index], qualifier):
                raise ValueError("month label must follow opening sign and ingress count")
            expected = (_MONTHS[(month_index + 1) % 12],) if count == 2 else ()
            if self.omitted_months != expected:
                raise ValueError("omitted month must follow the opening month")
            if tuple(int(event.target_degrees / 30) for event in self.ingresses) != tuple(
                (self.solar_rashi_at_start + i + 1) % 12 for i in range(count)
            ):
                raise ValueError("ingress targets must advance from the opening sign")


@dataclass(frozen=True, slots=True)
class LunarMonthProvenance:
    reader_binding: str
    source: str = _SOURCE
    longitude_origin: str = "geocentric"
    longitude_frame: str = "apparent_ecliptic_of_date"
    sidereal_mode: str = "true"
    event_timescale: str = "UT1"
    naming_rule: str = "nirayana_solar_sign_at_initial_conjunction"
    boundary_ownership: str = "[entered_conjunction, next_entered_conjunction)"
    intercalation_rule: str = "zero_one_two_solar_ingresses_per_amanta_lunation"
    purnimanta_scope: str = "ordinary_neighbourhood_only"
    ksaya_scope: str = "omitted_name_evidence_without_regional_remapping"
    scan_step_days: float = 1.0
    search_radius_days: int = 65


@dataclass(frozen=True, slots=True)
class LunarMonthResult:
    jd_ut1: float
    policy: LunarMonthPolicy
    provenance: LunarMonthProvenance
    status: Literal["available", "boundary_ambiguous", "unsupported_intercalation"]
    unavailable_reasons: tuple[str, ...]
    paksha: Literal["Shukla", "Krishna"]
    tithi_number: int
    uncertain_phase_boundaries: tuple[CalendarBoundary, ...]
    previous_lunation: LunarLunation
    amanta_lunation: LunarLunation
    next_lunation: LunarLunation
    month_start: CalendarBoundary | None
    month_end: CalendarBoundary | None
    label: LunarMonthLabel | None

    def __post_init__(self) -> None:
        _finite_number("jd_ut1", self.jd_ut1)
        if not isinstance(self.policy, LunarMonthPolicy):
            raise TypeError("month result policy must be LunarMonthPolicy")
        a, b, c = self.previous_lunation, self.amanta_lunation, self.next_lunation
        if a.end != b.start or b.end != c.start or not b.start.jd_ut1 <= self.jd_ut1 < b.end.jd_ut1:
            raise ValueError("month context requires contiguous surrounding lunations")
        events = (a.start, a.end, b.end, c.end,
                  *self.uncertain_phase_boundaries,
                  *(e for x in (a, b, c) for e in (*x.ingresses, *x.uncertain_ingresses)))
        if any((e.jd_ut1 - e.lower_jd_ut1)*86400 > self.policy.solver_tolerance_seconds + 0.0001
               for e in events):
            raise ValueError("month boundary bracket exceeds the selected solver tolerance")
        if self.paksha not in ("Shukla", "Krishna") or type(self.tithi_number) is not int or not 1 <= self.tithi_number <= 15:
            raise ValueError("invalid paksha/tithi identity")
        if any(e.kind not in ("new_moon", "full_moon") or not e.lower_jd_ut1 <= self.jd_ut1 < e.jd_ut1
               for e in self.uncertain_phase_boundaries):
            raise ValueError("uncertain phase boundary must bracket the requested instant")
        needed = (b,) if self.policy.system is LunarMonthSystem.AMANTA else (a, b, c)
        ambiguous = bool(self.uncertain_phase_boundaries or any(x.uncertain_ingresses for x in needed))
        if self.status == "available":
            if (ambiguous or self.unavailable_reasons or self.label is None or self.month_start is None
                    or self.month_end is None or not self.month_start.jd_ut1 <= self.jd_ut1 < self.month_end.jd_ut1):
                raise ValueError("available month requires an owned period and label")
            if self.policy.system is LunarMonthSystem.AMANTA:
                if self.label != b.label or self.month_start != b.start or self.month_end != b.end:
                    raise ValueError("amanta month must preserve its lunation")
            else:
                owner = b if self.paksha == "Shukla" else c
                if (any(x.label is None or x.label.qualifier != "ordinary" for x in (a, b, c))
                        or self.label != owner.label
                        or self.month_start.kind != "full_moon" or self.month_end.kind != "full_moon"):
                    raise ValueError("purnimanta admission requires an ordinary neighbourhood")
        elif self.status in ("boundary_ambiguous", "unsupported_intercalation"):
            if not self.unavailable_reasons or any(x is not None for x in (self.month_start, self.month_end, self.label)):
                raise ValueError("unavailable month must retain evidence without a selected label")
            if self.status == "boundary_ambiguous" and not ambiguous:
                raise ValueError("ambiguous month requires retained overlapping brackets")
            if self.status == "unsupported_intercalation" and (
                    ambiguous or self.policy.system is not LunarMonthSystem.PURNIMANTA
                    or all(x.label is not None and x.label.qualifier == "ordinary" for x in (a, b, c))):
                raise ValueError("unsupported intercalation must identify an exceptional purnimanta context")
        else:
            raise ValueError("unknown lunar month availability")


def _angular_boundaries(start: float, end: float, phase_at, span: float,
                        tolerance_seconds: float, lunar: bool) -> tuple[CalendarBoundary, ...]:
    """Follow a forward continuous angle and bracket each multiple of span.

    One-day advances must be positive and less than half a span; an invalid
    trajectory fails. No mean synodic period determines an event or label.
    """
    left, wrapped = start, phase_at(start)
    continuous = wrapped
    events: list[CalendarBoundary] = []
    while left < end:
        right = min(left + 1.0, end)
        right_wrapped = phase_at(right)
        advance = (right_wrapped - wrapped) % 360.0
        if not 0 < advance < span / 2:
            raise RuntimeError("lunar calendar forward angular bound violated")
        target = (math.floor(continuous / span) + 1) * span
        if target <= continuous + advance:
            low, high = left, right
            while (high - low) * 86400 > tolerance_seconds:
                mid = (low + high) / 2
                progress = (phase_at(mid) - wrapped) % 360.0
                if continuous + progress < target:
                    low = mid
                else:
                    high = mid
            angle = target % 360.0
            kind = ("new_moon" if angle == 0 else "full_moon") if lunar else "solar_ingress"
            events.append(CalendarBoundary(kind, angle, low, high))
        continuous += advance
        left, wrapped = right, right_wrapped
    return tuple(events)


def _lunation(start: CalendarBoundary, end: CalendarBoundary,
               solar_events: tuple[CalendarBoundary, ...], solar_at) -> LunarLunation:
    sign = int(solar_at(start.jd_ut1) // 30)
    inside = tuple(e for e in solar_events if start.jd_ut1 < e.lower_jd_ut1 and e.jd_ut1 < end.lower_jd_ut1)
    uncertain = tuple(e for e in solar_events if any(
        e.lower_jd_ut1 <= edge.jd_ut1 and e.jd_ut1 >= edge.lower_jd_ut1
        for edge in (start, end)
    ))
    label, omitted = None, ()
    if not uncertain:
        count = len(inside)
        if count > 2:
            raise RuntimeError("lunar calendar ingress count exceeds physical admission")
        index = (sign + 1) % 12
        label = LunarMonthLabel(index, _MONTHS[index], ("adhika", "ordinary", "ksaya_context")[count])
        if count == 2:
            omitted = (_MONTHS[(index + 1) % 12],)
    return LunarLunation(start, end, sign, inside, uncertain, label, omitted)


def lunar_month_at(jd_ut1: float, *, policy: LunarMonthPolicy | None = None,
                   reader=None) -> LunarMonthResult:
    """Return bounded astronomical month evidence at an instant in UT1.

    This is an astronomical period, not an era year, regional civil date or
    festival calendar. Selected ayanamsa changes solar naming/intercalation;
    the conjunction and opposition phases are ayanamsa-independent.
    """
    _finite_number("jd_ut1", jd_ut1)
    if not -10_000_000 <= jd_ut1 <= 10_000_000:
        raise ValueError("jd_ut1 must be within [-10000000,10000000]")
    if policy is not None and not isinstance(policy, LunarMonthPolicy):
        raise TypeError("policy must be LunarMonthPolicy")
    selected = policy or LunarMonthPolicy()
    binding = "caller_owned_reader" if reader is not None else "active_or_default_reader"
    if reader is None:
        reader = get_reader()
    with use_reader_override(reader):
        @lru_cache(maxsize=4096)
        def longitudes(jd):
            return tuple(planet_at(body, jd, reader=reader).longitude for body in ("Sun", "Moon"))

        def phase(jd):
            sun, moon = longitudes(jd)
            return (moon - sun) % 360

        def solar(jd):
            sun, _ = longitudes(jd)
            return tropical_to_sidereal(sun, jd, selected.ayanamsa_system)

        phases = _angular_boundaries(jd_ut1 - 65, jd_ut1 + 65, phase, 180,
                                     selected.solver_tolerance_seconds, True)
        new = tuple(e for e in phases if e.kind == "new_moon")
        current = next((i for i in range(len(new) - 1) if new[i].jd_ut1 <= jd_ut1 < new[i+1].jd_ut1), None)
        if current is None or current == 0 or current + 2 >= len(new):
            raise RuntimeError("lunar calendar surrounding conjunctions exceed 65-day search radius")
        if any(not 20 < b.jd_ut1 - a.jd_ut1 < 40 for a, b in zip(new, new[1:])):
            raise RuntimeError("lunar calendar lunation duration bound violated")
        first, last = new[current - 1], new[current + 2]
        ingresses = _angular_boundaries(first.lower_jd_ut1 - 1, last.jd_ut1 + 1,
                                        solar, 30, selected.solver_tolerance_seconds, False)
        context = tuple(_lunation(new[i], new[i+1], ingresses, solar)
                        for i in range(current - 1, current + 2))
        previous, amanta, following = context
        angle = phase(jd_ut1)
        paksha = "Shukla" if angle < 180 else "Krishna"
        tithi = int(angle // 12) % 15 + 1
        status, reasons = "available", ()
        start, end, label = amanta.start, amanta.end, amanta.label
        uncertain_phases = tuple(e for e in phases if e.lower_jd_ut1 <= jd_ut1 < e.jd_ut1)
        needed = (amanta,) if selected.system is LunarMonthSystem.AMANTA else context
        if uncertain_phases or any(lunation.uncertain_ingresses for lunation in needed):
            status, reasons = "boundary_ambiguous", ("phase_or_ingress_brackets_overlap",)
        elif selected.system is LunarMonthSystem.PURNIMANTA:
            if any(lunation.label.qualifier != "ordinary" for lunation in context):
                status, reasons = "unsupported_intercalation", ("purnimanta_intercalary_or_ksaya_neighbourhood_requires_regional_rules",)
            else:
                full = tuple(e for e in phases if e.kind == "full_moon")
                start = max((e for e in full if e.jd_ut1 <= jd_ut1), key=lambda e: e.jd_ut1)
                end = min((e for e in full if e.jd_ut1 > jd_ut1), key=lambda e: e.jd_ut1)
                label = amanta.label if paksha == "Shukla" else following.label
        if status != "available":
            start, end, label = None, None, None
        return LunarMonthResult(jd_ut1, selected, LunarMonthProvenance(binding), status,
            reasons, paksha, tithi, uncertain_phases, previous, amanta, following, start, end, label)
