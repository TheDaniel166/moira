"""Source-bounded isolation for apparent geocentric longitude conjunctions."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import math
from types import SimpleNamespace

from ._ephemeris_time import _bind_ephemeris_time
from ._event_search.astronomy import AstronomyEnclosures, longitude_differential
from ._event_search.budgets import SearchBudgetError, WorkMeter
from ._event_search.intervals import EnclosureUnavailable, Interval
from ._event_search.isolation import Signal, isolate
from ._event_search.resources import borrow_reader
from .constants import Body
from .julian import julian_day
from .spk_reader import OutOfRangeError, get_reader


COARSE_STEP_DAYS = 3.0
MAX_SPAN_DAYS = 366.0
ISOLATION_SECONDS = 0.25
_WITNESS_PADDING_DAYS = 2.0 / 86400.0


class GeocentricConjunctionBudgetError(SearchBudgetError):
    """Bounded geocentric conjunction isolation exhausted its declared work."""

    label = "geocentric conjunction"


@dataclass(frozen=True, slots=True)
class _Limits:
    """Fixed work limits for a synchronous search."""

    max_evaluations: int = 12000
    max_reader_calls: int = 100000
    max_root_iterations: int = 12000
    max_subdivisions: int = 6000
    max_candidates: int = 512


@dataclass(frozen=True, slots=True)
class GeocentricConjunctionWitness:
    """One bracket with strict endpoint signs and a one-sign relative rate."""

    lower_jd_ut1: float
    upper_jd_ut1: float
    direction: int
    lower_offset_deg: tuple[float, float]
    upper_offset_deg: tuple[float, float]
    relative_rate_deg_per_day: tuple[float, float]


@dataclass(frozen=True, slots=True)
class GeocentricConjunctionUnresolved:
    """A retained interval whose existence or completeness is unresolved."""

    lower_jd_ut1: float
    upper_jd_ut1: float
    reason: str


@dataclass(frozen=True, slots=True)
class GeocentricConjunctionResolution:
    """Search coverage, matched witnesses, and path-free serving evidence."""

    witnesses: tuple[GeocentricConjunctionWitness, ...]
    unresolved: tuple[GeocentricConjunctionUnresolved, ...]
    excluded_intervals: int
    evaluations: int
    subdivisions: int
    reader_calls: int
    planetary_ephemeris: str
    source_sha256: tuple[str, ...]


def _enclosed_longitude(vector):
    """Choose a local angular lift from the center enclosure."""
    x, y = vector[:2]
    reference = math.degrees(math.atan2(y.center.lo + y.center.hi, x.center.lo + x.center.hi))
    return longitude_differential(vector, reference)


def _pair_signal(astronomy, body1, body2, lower, upper, coarse):
    """Enclose the lifted longitude difference and convert its rate to UT1."""
    tt = astronomy.tt(lower, upper)
    first = _enclosed_longitude(astronomy.coordinates_tt(body1, tt.lo, tt.hi, coarse)[1])
    second = _enclosed_longitude(astronomy.coordinates_tt(body2, tt.lo, tt.hi, coarse)[1])
    difference = first - second
    clock = astronomy.clock.jet(lower, upper)
    center = None
    if difference.centered and clock.centered:
        center = difference.center + difference.rate * (clock.center - (tt.lo + tt.hi) / 2)
    return Signal(difference.value, difference.rate * clock.rate, center)


def _crossing_witness(signal, lower, upper):
    """Prove a unique crossing on every retained continuous rounding branch."""
    try:
        whole = signal(lower, upper, False)
    except EnclosureUnavailable:
        return None
    if whole.center is None or whole.rate is None:
        return None
    ray = 360.0 * round((whole.value.lo + whole.value.hi) / 720.0)
    if not ray - 180.0 < whole.value.lo <= whole.value.hi < ray + 180.0:
        return None
    midpoint = (lower + upper) / 2
    left = whole.center - ray + whole.rate * (Interval.point(lower) - midpoint)
    right = whole.center - ray + whole.rate * (Interval.point(upper) - midpoint)
    if whole.rate.lo > 0.0 and left.hi < 0.0 < right.lo:
        direction = 1
    elif whole.rate.hi < 0.0 and right.hi < 0.0 < left.lo:
        direction = -1
    else:
        return None
    return GeocentricConjunctionWitness(
        lower, upper, direction, (left.lo, left.hi), (right.lo, right.hi),
        (whole.rate.lo, whole.rate.hi),
    )


def _resolve_crossings(signal, start, end, meter, refine):
    """Return ordered crossings and retain every interval lacking a proof."""
    lower = start - _WITNESS_PADDING_DAYS
    upper = end + _WITNESS_PADDING_DAYS
    isolation = isolate(
        signal, lower, upper, period=360.0, step=COARSE_STEP_DAYS,
        tolerance=ISOLATION_SECONDS, meter=meter,
        on_retain=lambda kind, a, b: meter.tick("candidates"),
    )
    unresolved = [
        GeocentricConjunctionUnresolved(max(a, start), min(b, end), reason)
        for a, b, reason in isolation.unresolved if a <= end and b >= start
    ]
    events = []
    roots = isolation.roots
    for index, root in enumerate(roots):
        if root.upper < start or root.lower > end:
            continue
        # Keep the proof bracket away from the adjacent candidate, even
        # when both roots are closer than the ordinary witness padding.
        padding = _WITNESS_PADDING_DAYS
        if index:
            padding = min(padding, (root.lower - roots[index - 1].upper) / 4)
        if index + 1 < len(roots):
            padding = min(padding, (roots[index + 1].lower - root.upper) / 4)
        a = max(lower, root.lower - padding)
        b = min(upper, root.upper + padding)
        witness = _crossing_witness(signal, a, b)
        event = refine(witness) if witness is not None else None
        if event is None:
            unresolved.append(GeocentricConjunctionUnresolved(
                max(a, start), min(b, end),
                "crossing_existence_or_multiplicity_unresolved" if witness is None
                else "point_reducer_disagrees_with_crossing_witness",
            ))
        elif start <= event.jd_ut <= end:
            events.append((event, witness))
        else:
            unresolved.append(GeocentricConjunctionUnresolved(
                max(root.lower, start), min(root.upper, end), "boundary_ownership_unresolved",
            ))
    unresolved.sort(key=lambda gap: (gap.lower_jd_ut1, gap.upper_jd_ut1))
    return tuple(events), tuple(unresolved), isolation.excluded_intervals


def search(body1, body2, start, end, reader):
    """Bind the serving reader, isolate roots, then refine canonical epochs."""
    from .phenomena import (
        PhenomenonEvent, _bisect_conjunction, _conjunction_separation,
        _polish_conjunction_root, planet_at,
    )

    if body1 == body2 or body1 not in Body.ALL_PLANETS or body2 not in Body.ALL_PLANETS:
        raise ValueError("Verified conjunctions require two distinct admitted geocentric bodies.")
    minimum = julian_day(1900, 1, 1)
    maximum = julian_day(2101, 1, 1)
    lo, hi = start - _WITNESS_PADDING_DAYS, end + _WITNESS_PADDING_DAYS
    if not 0 < end - start <= MAX_SPAN_DAYS:
        raise ValueError(f"The conjunction interval must be positive and at most {MAX_SPAN_DAYS:g} days.")
    if not minimum <= lo <= hi < maximum:
        raise ValueError("The conjunction interval and its boundary witnesses require the 1900–2100 clock domain.")

    meter = WorkMeter(
        _Limits(), budget_error=GeocentricConjunctionBudgetError,
        kinds=("evaluations", "reader_calls", "root_iterations", "subdivisions", "candidates"),
    )
    with borrow_reader(get_reader() if reader is None else reader, meter) as bound:
        epoch = lru_cache(maxsize=4096)(lambda jd: _bind_ephemeris_time(jd, bound))
        astronomy = AstronomyEnclosures(SimpleNamespace(reader=bound, meter=meter, epoch=epoch))
        identity = epoch(start).identity
        if identity.planetary_ephemeris is None:
            raise EnclosureUnavailable("serving_planetary_identity_unavailable")
        # Validate the actual clock/frame endpoints before scanning. A
        # source seam inside the window is tracked by the interval solver.
        for endpoint in (lo, hi):
            tt = astronomy.tt(endpoint, endpoint)
            if not minimum <= tt.lo <= tt.hi < maximum:
                raise ValueError("The conjunction boundary witness is outside the supported TT frame domain.")
            for body in (body1, body2):
                astronomy.coordinates_tt(body, tt.lo, tt.hi, True)

        @lru_cache(maxsize=4096)
        def signal(a, b, coarse):
            return _pair_signal(astronomy, body1, body2, a, b, coarse)

        def refine(witness):
            a, b = witness.lower_jd_ut1, witness.upper_jd_ut1
            left = _conjunction_separation(body1, body2, a, bound, apparent=True)
            right = _conjunction_separation(body1, body2, b, bound, apparent=True)
            if not (-90 < left < 90 and -90 < right < 90
                    and left * witness.direction < 0 < right * witness.direction):
                return None
            jd = _bisect_conjunction(body1, body2, a, b, bound, apparent=True)
            jd = _polish_conjunction_root(body1, body2, jd, bound, apparent=True, bracket=(a, b))
            if not abs(_conjunction_separation(body1, body2, jd, bound, apparent=True)) <= 1e-6:
                return None
            position = planet_at(body1, jd, reader=bound, apparent=True)
            return PhenomenonEvent(f"{body1}-{body2}", "Conjunction", jd, position.longitude)

        meter.stage = "apparent_conjunction_search"
        try:
            paired, unresolved, excluded = _resolve_crossings(signal, start, end, meter, refine)
        except OutOfRangeError as exc:
            # Missing serving states are distinct from a zero-free interval.
            raise OutOfRangeError(
                "The serving ephemeris does not cover the conjunction interval and boundary witnesses.",
                exc.out_of_range_times,
            ) from exc
        resolution = GeocentricConjunctionResolution(
            tuple(witness for _, witness in paired), unresolved, excluded,
            meter.counts["evaluations"], meter.counts["subdivisions"], meter.counts["reader_calls"],
            identity.planetary_ephemeris, tuple(sorted(astronomy.records.sources)),
        )
    return tuple(event for event, _ in paired), resolution
