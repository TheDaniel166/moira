"""Bounded nominal finite-disk event searches for the admitted planetary moons."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from functools import lru_cache
from math import ceil, isfinite
from typing import Literal

from ._planetary_moon_data import PCK_SHA256, SYSTEMS, MoonIdentity, MoonSystem, Planet
from ._planetary_moon_geometry import _CONTACT_TOL
from .julian import tdb_to_tt, tt_to_tdb
from .planetary_moons import PlanetaryMoonSource, PlanetaryMoons, _MoonContactSample, _moon_contact_sample, _received
from .spk_reader import OutOfRangeError

PlanetaryMoonEventKind = Literal["transit", "occultation", "eclipse"]
PlanetaryMoonSearchMode = Literal["window", "next"]
PlanetaryMoonContactKind = Literal[
    "ingress", "egress", "graze", "internal_ingress", "internal_egress", "internal_graze",
]
_Transition = Literal["enter", "exit", "touch"]
_Signal = Callable[[float], float]

PLANETARY_MOON_EVENT_KINDS: tuple[PlanetaryMoonEventKind, ...] = ("transit", "occultation", "eclipse")
PLANETARY_MOON_MAX_WINDOW_DAYS = 90.0
PLANETARY_MOON_MAX_EVALUATIONS = 50_000
PLANETARY_MOON_DEFAULT_EVALUATIONS = 20_000
PLANETARY_MOON_MAX_RESULTS = 1000

_SCAN_STEP_DAYS = 1.0 / 48.0
_EPOCH_TOL_DAYS = 2e-9
_BOUNDARY_PROBE_DAYS = 1.0 / 1440.0
# The moon-local limb can move several tangent-plane units per day. Allow
# that motion across the timing tolerance when checking for a bracket jump.
_MAX_BRACKET_MARGIN_CHANGE = 32.0 * _EPOCH_TOL_DAYS
_GOLDEN_SECTION = (5.0**0.5 - 1.0) / 2.0

__all__ = [
    "PlanetaryMoonContact",
    "PlanetaryMoonEventWindow",
    "PlanetaryMoonEventSearch",
    "UnresolvedPlanetaryMoonInterval",
    "find_planetary_moon_events",
]


@dataclass(frozen=True, slots=True)
class PlanetaryMoonContact:
    """A finite-disk contact, with all offsets relative to Earth reception."""

    kind: PlanetaryMoonContactKind
    jd_tt: float
    jd_tdb: float
    observer_offset_days: float
    moon_emission_offset_days: float
    planet_emission_offset_days: float
    sun_emission_offset_days: float | None


@dataclass(frozen=True, slots=True)
class PlanetaryMoonEventWindow:
    """One interval of disk overlap or one isolated external tangency."""

    planet: Planet
    moon: str
    naif_id: int
    kind: PlanetaryMoonEventKind
    start_jd_tt: float
    end_jd_tt: float
    start_clipped: bool
    end_clipped: bool
    contacts: tuple[PlanetaryMoonContact, ...]


@dataclass(frozen=True, slots=True)
class UnresolvedPlanetaryMoonInterval:
    """An Earth-reception interval for which the search has no verdict."""

    naif_id: int
    start_jd_tt: float
    end_jd_tt: float
    reason: Literal["evaluation_budget", "unresolved_contact"]


@dataclass(frozen=True, slots=True)
class PlanetaryMoonEventSearch:
    """Bounded search results, numerical resolution, and source receipts."""

    jd_start_tt: float
    jd_end_tt: float
    mode: PlanetaryMoonSearchMode
    events: tuple[PlanetaryMoonEventWindow, ...]
    status: Literal["complete", "evaluation_budget", "unresolved", "result_limit"]
    unresolved_intervals: tuple[UnresolvedPlanetaryMoonInterval, ...]
    evaluations: int
    max_evaluations: int
    scan_step_days: float
    contact_tolerance_days: float
    sources: tuple[PlanetaryMoonSource, ...]
    de441_sha256: str
    figure_pck_sha256: str = PCK_SHA256
    resolution: Literal["sampled_with_extremum_refinement"] = "sampled_with_extremum_refinement"


class _EvaluationBudgetReached(RuntimeError):
    """The next geometry evaluation would exceed the search budget."""


class _UnresolvedContact(ArithmeticError):
    """A contact bracket cannot be resolved at the admitted numerical scale."""


def _sign(margin: float) -> int:
    if abs(margin) <= _CONTACT_TOL:
        return 0
    return 1 if margin > 0.0 else -1


def _boundary_sign(signal: _Signal, jd: float, direction: int) -> int:
    """Resolve the side immediately outside a search boundary contact."""
    offset_days = 8 * _EPOCH_TOL_DAYS
    while True:
        sign = _sign(signal(jd + direction * offset_days))
        if sign:
            return sign
        if offset_days == _BOUNDARY_PROBE_DAYS:
            raise _UnresolvedContact("A boundary contact has no resolved exterior side.")
        offset_days = min(4 * offset_days, _BOUNDARY_PROBE_DAYS)


def _extremum(signal: _Signal, left: float, right: float, sense: int) -> float:
    """Refine one sampled local extremum and return its best epoch."""

    a = right - _GOLDEN_SECTION * (right - left)
    b = left + _GOLDEN_SECTION * (right - left)
    fa, fb = sense * signal(a), sense * signal(b)
    while right - left > _EPOCH_TOL_DAYS:
        if fa < fb:
            right, b, fb = b, a, fa
            a = right - _GOLDEN_SECTION * (right - left)
            fa = sense * signal(a)
        else:
            left, a, fa = a, b, fb
            b = left + _GOLDEN_SECTION * (right - left)
            fb = sense * signal(b)
    return a if fa < fb else b


def _root(signal: _Signal, left: float, right: float, before: float, after: float) -> float:
    """Isolate a continuous sign reversal and reject a discontinuous jump."""

    while right - left > _EPOCH_TOL_DAYS:
        middle = left + (right - left) / 2.0
        margin = signal(middle)
        if _sign(margin) == 0:
            return middle
        if (before < 0.0) == (margin < 0.0):
            left, before = middle, margin
        else:
            right, after = middle, margin
    if abs(before - after) > _MAX_BRACKET_MARGIN_CHANGE:
        raise _UnresolvedContact("The contact bracket ended at a discontinuity.")
    return left if abs(before) < abs(after) else right


def _scan_contacts(signal: _Signal, epochs: tuple[float, ...]) -> list[tuple[float, _Transition]]:
    """Refine sampled crossings and same-sign minima or maxima."""

    knots = {epoch: signal(epoch) for epoch in epochs}
    # Endpoint cells have only one neighbor. Refine toward the opposite
    # sign there so a short overlap can still be found close to the boundary.
    for left, right in dict.fromkeys(((epochs[0], epochs[1]), (epochs[-2], epochs[-1]))):
        flank = _sign(knots[left])
        if flank != 0 and flank == _sign(knots[right]):
            peak = _extremum(signal, left, right, flank)
            knots[peak] = signal(peak)
    for left, middle, right in zip(epochs, epochs[1:], epochs[2:]):
        a, b, c = knots[left], knots[middle], knots[right]
        if min(a, c) >= b and max(a, c) > b:
            peak = _extremum(signal, left, right, 1)
        elif max(a, c) <= b and min(a, c) < b:
            peak = _extremum(signal, left, right, -1)
        else:
            continue
        knots[peak] = signal(peak)

    ordered = sorted(knots)
    contacts: list[tuple[float, _Transition]] = []
    index = 0
    while index < len(ordered):
        jd = ordered[index]
        margin = knots[jd]
        if _sign(margin) == 0:
            last = index
            while last + 1 < len(ordered) and _sign(knots[ordered[last + 1]]) == 0:
                last += 1
            if ordered[last] - jd > 4 * _EPOCH_TOL_DAYS:
                raise _UnresolvedContact("A contact lies in an unresolved near-zero interval.")
            if index == 0 and last + 1 == len(ordered):
                raise _UnresolvedContact("The whole contact interval is near zero.")
            previous = _sign(knots[ordered[index - 1]]) if index else _boundary_sign(signal, epochs[0], -1)
            following = (
                _sign(knots[ordered[last + 1]]) if last + 1 < len(ordered)
                else _boundary_sign(signal, epochs[-1], 1)
            )
            transition = "touch" if previous == following else ("enter" if following < 0 else "exit")
            contacts.append((min(ordered[index:last + 1], key=lambda t: abs(knots[t])), transition))
            index = last + 1
            continue

        if index + 1 < len(ordered):
            right = ordered[index + 1]
            if _sign(margin) * _sign(knots[right]) < 0:
                epoch = _root(signal, jd, right, margin, knots[right])
                contacts.append((epoch, "enter" if margin > 0.0 else "exit"))
        index += 1
    return contacts


def _windows(
    start: float, end: float, initially_active: bool, contacts: list[tuple[float, _Transition]],
) -> list[tuple[float, float, bool, bool]]:
    """Assemble event windows with a start-inclusive and end-exclusive search."""

    found: list[tuple[float, float, bool, bool]] = []
    beginning = start if initially_active else None
    clipped = initially_active
    for epoch, direction in contacts:
        if direction == "enter" and beginning is None and epoch < end:
            beginning, clipped = epoch, False
        elif direction == "exit" and beginning is not None:
            if epoch > beginning:
                found.append((beginning, epoch, clipped, False))
            beginning = None
        elif direction == "touch" and beginning is None and epoch < end:
            found.append((epoch, epoch, False, False))
    if beginning is not None:
        found.append((beginning, end, clipped, True))
    return found


def _contact(
    kind: PlanetaryMoonContactKind, jd: float, sample: _MoonContactSample, eclipse: bool,
) -> PlanetaryMoonContact:
    if eclipse:
        assert sample.shadow_planet_emission is not None
        observer = sample.moon_emission
        planet = sample.shadow_planet_emission
        sun = sample.shadow_sun_emission
    else:
        observer, planet, sun = 0.0, sample.planet_emission, None
    return PlanetaryMoonContact(kind, tdb_to_tt(jd), jd, observer, sample.moon_emission, planet, sun)


def _events_for_channel(
    system: MoonSystem, moon: MoonIdentity, epochs: tuple[float, ...],
    sample: Callable[[float], _MoonContactSample], kinds: frozenset[PlanetaryMoonEventKind],
    *, eclipse: bool,
) -> list[PlanetaryMoonEventWindow]:
    def margins(jd: float) -> tuple[float, float]:
        value = sample(jd)
        result = value.eclipse_margins if eclipse else value.earth_margins
        assert result is not None
        return result

    def outer_margin(jd: float) -> float:
        return margins(jd)[0]

    outer = _scan_contacts(outer_margin, epochs)
    start = epochs[0]
    start_sign = _sign(outer_margin(start))
    if start_sign == 0:
        start_sign = _boundary_sign(outer_margin, start, -1)
    intervals = _windows(start, epochs[-1], start_sign < 0, outer)
    if not intervals:
        return []
    inner = _scan_contacts(lambda jd: margins(jd)[1], epochs)
    outer_names = {"enter": "ingress", "exit": "egress", "touch": "graze"}
    inner_names = {"enter": "internal_ingress", "exit": "internal_egress", "touch": "internal_graze"}

    result = []
    for start, end, clipped_start, clipped_end in intervals:
        if eclipse:
            kind = "eclipse"
        else:
            start_depth, end_depth = sample(start).depth_km, sample(end).depth_km
            if start_depth * end_depth <= 0.0:
                raise _UnresolvedContact("The Earth-view range ordering changes during overlap.")
            kind = "transit" if start_depth < 0.0 else "occultation"
        if kind not in kinds:
            continue
        times = [(jd, outer_names[direction]) for jd, direction in outer if start <= jd <= end]
        times += [(jd, inner_names[direction]) for jd, direction in inner if start <= jd <= end]
        contacts = tuple(_contact(name, jd, sample(jd), eclipse) for jd, name in sorted(times))
        result.append(PlanetaryMoonEventWindow(
            system.name, moon.name, moon.naif_id, kind,
            tdb_to_tt(start), tdb_to_tt(end), clipped_start, clipped_end, contacts,
        ))
    return result


def find_planetary_moon_events(
    context: PlanetaryMoons, jd_start_tt: float, jd_end_tt: float, *,
    planet: Planet | None = None, moon_ids: tuple[int, ...] = (),
    kinds: tuple[PlanetaryMoonEventKind, ...] = PLANETARY_MOON_EVENT_KINDS,
    mode: PlanetaryMoonSearchMode = "window",
    max_evaluations: int = PLANETARY_MOON_DEFAULT_EVALUATIONS,
    max_results: int = 256,
) -> PlanetaryMoonEventSearch:
    """Search finite-disk events on the owning thread of an open context.

    Numerical completion covers the declared sample and extremum search.
    Budget and unresolved results carry no definitive next-event answer.
    """
    if (
        isinstance(jd_start_tt, bool) or isinstance(jd_end_tt, bool)
        or not isfinite(jd_start_tt) or not isfinite(jd_end_tt)
        or not 0 < jd_end_tt - jd_start_tt <= PLANETARY_MOON_MAX_WINDOW_DAYS
    ):
        raise ValueError("Planetary moon search needs an ordered TT window of at most 90 days.")
    if type(max_evaluations) is not int or not 1 <= max_evaluations <= PLANETARY_MOON_MAX_EVALUATIONS:
        raise ValueError("Planetary moon evaluation budget is outside the admitted bounds.")
    if type(max_results) is not int or not 1 <= max_results <= PLANETARY_MOON_MAX_RESULTS:
        raise ValueError("Planetary moon result limit is outside the admitted bounds.")
    filters = frozenset(kinds)
    if mode not in ("window", "next") or not filters or filters.difference(PLANETARY_MOON_EVENT_KINDS):
        raise ValueError("Unsupported planetary moon event mode or kind.")
    ids = frozenset(moon_ids)
    selected = [
        (system, moon) for system in SYSTEMS if planet is None or system.name == planet
        for moon in system.moons if not ids or moon.naif_id in ids
    ]
    if not selected or ids.difference(moon.naif_id for _, moon in selected):
        raise ValueError("Selected moon IDs must belong to the requested planetary systems.")
    if any(type(naif_id) is not int for naif_id in moon_ids):
        raise ValueError("Selected moon IDs must be integers.")
    start, end = tt_to_tdb(jd_start_tt), tt_to_tdb(jd_end_tt)
    if end <= start:
        raise ValueError("Planetary moon search window collapses at TDB precision.")
    count = ceil((end - start) / _SCAN_STEP_DAYS)
    epochs = tuple(start + index * (end - start) / count for index in range(count)) + (end,)
    selected_planets = tuple(dict.fromkeys(system.name for system, _ in selected))
    coverage = context.coverage_tdb()
    for name in selected_planets:
        if name not in coverage:
            raise FileNotFoundError(f"Install the satellite extract for {name}")
        if not any(lo <= start <= end <= hi for lo, hi in coverage[name]):
            raise OutOfRangeError("The request crosses a planetary moon coverage boundary.", out_of_range_times=True)

    evaluations = 0
    events: list[PlanetaryMoonEventWindow] = []
    unresolved: list[UnresolvedPlanetaryMoonInterval] = []
    with context._pool._read_lease() as lease:
        for system, moon in selected:
            @lru_cache(maxsize=None)
            def sample(jd: float) -> _MoonContactSample:
                nonlocal evaluations
                if evaluations == max_evaluations:
                    raise _EvaluationBudgetReached
                evaluations += 1

                def position(body: int, offset: float = 0.0):
                    return context._pool._position_tdb_offset(0, body, jd, offset, snapshot=lease)

                earth = position(399)
                parent, emission = _received(system.center, earth, 0.0, position)
                return _moon_contact_sample(
                    system, moon, jd, earth, parent, emission, position, include_eclipse="eclipse" in filters,
                )

            try:
                if filters.intersection(("transit", "occultation")):
                    events.extend(_events_for_channel(system, moon, epochs, sample, filters, eclipse=False))
                if "eclipse" in filters:
                    events.extend(_events_for_channel(system, moon, epochs, sample, filters, eclipse=True))
            except _EvaluationBudgetReached:
                unresolved.append(UnresolvedPlanetaryMoonInterval(
                    moon.naif_id, jd_start_tt, jd_end_tt, "evaluation_budget",
                ))
            except _UnresolvedContact:
                unresolved.append(UnresolvedPlanetaryMoonInterval(
                    moon.naif_id, jd_start_tt, jd_end_tt, "unresolved_contact",
                ))

    events.sort(key=lambda event: (event.start_jd_tt, event.naif_id, event.kind))
    if unresolved:
        status = "evaluation_budget" if any(row.reason == "evaluation_budget" for row in unresolved) else "unresolved"
    else:
        status = "result_limit" if mode == "window" and len(events) > max_results else "complete"
    if mode == "next":
        events = [] if unresolved else [event for event in events if not event.start_clipped][:1]
    return PlanetaryMoonEventSearch(
        jd_start_tt, jd_end_tt, mode, tuple(events[:max_results]), status, tuple(unresolved),
        evaluations, max_evaluations, _SCAN_STEP_DAYS, _EPOCH_TOL_DAYS,
        tuple(context._sources[name] for name in selected_planets), context._base_hash,
    )
