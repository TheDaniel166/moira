"""Bounded astronomical composition for the six admitted Muhurta dosha rules.

Reuse the admitted forward-phase root finder and solar-anchor refinement.
Full parent events precede derived windows; no sampled transition is promoted
to an exact boundary, and numerical root bands carry no categorical state.
"""
from dataclasses import replace
from datetime import date, timedelta
from functools import lru_cache

from ._ephemeris_time import _EphemerisTimeBasisError
from ._panchanga_shuddhi_day import _crossings, _bands, _convert
from .daily_panchanga import _resolve_timezone, _civil_bounds
from .houses import _local_angles_at
from .muhurta_dosha import (
    MuhurtaDoshaPolicy, MuhurtaDoshaDay, MuhurtaDoshaCell, DoshaPhaseSpan,
    detect_muhurta_doshas, MC_NECESSARY,
)
from .muhurta_search import MuhurtaCoverageError, MuhurtaResourceError
from .named_muhurta import NamedMuhurtaPolicy, named_muhurta_for_date, _refine
from .panchanga_shuddhi import ShuddhiInterval, _number, _sector
from .planets import planet_at
from .sidereal import tropical_to_sidereal
from .spk_reader import get_reader, use_reader_override, MissingKernelError, OutOfRangeError


def _events(roots, phase, divisions, kind):
    if any(a.upper_jd_ut1 >= b.lower_jd_ut1 for a, b in zip(roots, roots[1:])):
        raise ValueError(f"{kind}: full event endpoints are unresolved")
    return tuple(DoshaPhaseSpan(kind, _sector(phase((a.upper_jd_ut1+b.lower_jd_ut1)/2), divisions),
                                ShuddhiInterval(a, b)) for a, b in zip(roots, roots[1:]))


def _context_spans(events, jd):
    """Keep current parents and enough earlier stars for fixed-width carryover."""
    result = []
    for kind, spans in events.items():
        if kind == "nakshatra":
            current = next((i for i, s in enumerate(spans) if s.interval.contains(jd) is not False), None)
            if current is None:
                raise ValueError("complete nakshatra event unavailable inside bounded search margin")
            first = max(0, current-1)
            while first > 0 and spans[first].interval.start.upper_jd_ut1 > jd-4/60:
                first -= 1
            # Retain at least the previous full star throughout this parent.
            # A representative cell then carries usable context for all its
            # off-midpoint probes, including the first 96 minutes of a star.
            selected = spans[first:current+1]
        else:
            selected = tuple(s for s in spans if s.interval.contains(jd) is not False)
        if not selected or not any(s.interval.contains(jd) is not False for s in selected):
            raise ValueError(f"complete {kind} event unavailable inside bounded search margin")
        if kind == "nakshatra" and selected[0].interval.start.upper_jd_ut1 > jd-4/60:
            raise ValueError("preceding nakshatra unavailable inside bounded search margin")
        result.extend(selected)
    return tuple(result)


def _compose(local_date, latitude, longitude, timezone, necessary, active, bound, binding):
    solar_policy = NamedMuhurtaPolicy(sunrise_definition=active.sunrise_definition,
                                     solver_tolerance_seconds=active.solver_tolerance_seconds)
    named = named_muhurta_for_date(local_date, latitude, longitude, timezone=timezone,
                                  policy=solar_policy, reader=bound)
    rise, setting = _convert(named.result.sunrise), _convert(named.result.sunset)
    next_rise = None
    following = named.solar_dates[2]
    if len(following.sunrises) == 1:
        zone = _resolve_timezone(timezone)
        next_rise = _convert(_refine(following.sunrises[0], "sunrise", latitude, longitude,
                                    zone, solar_policy), "next_sunrise")
        bounds = _civil_bounds(local_date+timedelta(days=1), zone)
        if next_rise is not None and not bounds[0] <= next_rise.lower_jd_ut1 <= next_rise.upper_jd_ut1 < bounds[1]:
            next_rise = None
    reasons = []
    if rise is None:
        reasons.append("requested_sunrise_absent_or_unresolved")
    if next_rise is None:
        reasons.append("next_civil_date_sunrise_absent_or_unresolved")

    def product(cells=(), bands=()):
        return MuhurtaDoshaDay(local_date, timezone, latitude, longitude, active,
            "unavailable" if not cells else "partial" if reasons else "available", tuple(reasons),
            rise, next_rise, setting, cells, bands, named.kernel_label, binding)

    if rise is None or next_rise is None:
        return product()
    if not 0 < next_rise.jd_ut1-rise.jd_ut1 <= 2 or rise.upper_jd_ut1 >= next_rise.lower_jd_ut1:
        raise ValueError("sunrise-owned day must be resolved and at most two days")
    if setting is None or not rise.upper_jd_ut1 < setting.lower_jd_ut1 <= setting.upper_jd_ut1 < next_rise.lower_jd_ut1:
        setting = None
        reasons.append("sunset_between_sunrises_absent_or_unresolved")
    if MC_NECESSARY in active.parihara_profiles and necessary is None:
        reasons.append("necessary_activity_evidence_not_supplied")
    day = ShuddhiInterval(rise, next_rise)
    lo, hi, tolerance = rise.jd_ut1, next_rise.jd_ut1, active.solver_tolerance_seconds

    @lru_cache(maxsize=8192)
    def longitudes(jd):
        return tuple(tropical_to_sidereal(planet_at(name, jd, reader=bound).longitude, jd, active.ayanamsa_system)
                     for name in ("Sun", "Moon"))

    def elongation(jd):
        sun, moon = longitudes(jd)
        return (moon-sun) % 360

    def moon(jd):
        return longitudes(jd)[1]

    @lru_cache(maxsize=4096)
    def lagna(jd):
        return tropical_to_sidereal(_local_angles_at(jd, latitude, longitude).asc, jd, active.ayanamsa_system)

    roots = {
        "nakshatra": _crossings(moon, 27, lo-3, hi+3, 1/24, tolerance, "nakshatra"),
        "tithi": _crossings(elongation, 30, lo-3, hi+3, 1/24, tolerance, "tithi"),
    }
    events = {"nakshatra": _events(roots["nakshatra"], moon, 27, "nakshatra"),
              "tithi": _events(roots["tithi"], elongation, 30, "tithi")}
    critical = 90-max(_local_angles_at(jd, latitude, longitude).obliquity for jd in (lo-1, hi+1))
    lagna_available = abs(latitude) < critical
    if lagna_available:
        roots["lagna"] = _crossings(lagna, 12, lo-1, hi+1, 3/1440, tolerance, "lagna_sign")
        events["lagna"] = _events(roots["lagna"], lagna, 12, "lagna")
    else:
        reasons.append("lagna_timing_at_or_above_ecliptic_polar_circle")

    boundaries = [rise, next_rise]
    if setting is not None:
        boundaries.append(setting)
    boundaries.extend(b for family in roots.values() for b in family
                      if b.upper_jd_ut1 >= rise.lower_jd_ut1
                      and b.lower_jd_ut1 <= next_rise.upper_jd_ut1)

    def assessment(jd):
        return replace(detect_muhurta_doshas(*longitudes(jd), jd_ut1=jd,
            weekday=(local_date.weekday()+1) % 7,
            lagna_sidereal_longitude=lagna(jd) if lagna_available else None,
            phase_spans=_context_spans(events, jd), sunrise_day=day, sunset=setting,
            necessary_activity=necessary, policy=active),
            input_basis="reader_bound_true_sidereal; solved_full_parent_ut1_events")

    for a, b in zip((initial := _bands(boundaries)), initial[1:]):
        if a.upper_jd_ut1 >= b.lower_jd_ut1:
            continue
        result = assessment((a.upper_jd_ut1+b.lower_jd_ut1)/2)
        for finding in result.findings:
            windows = [w.window for w in finding.witnesses]
            windows.extend(p.window for p in finding.parihara)
            for window in windows:
                if window is not None:
                    boundaries.extend(edge for edge in (window.start, window.end)
                                      if edge.upper_jd_ut1 >= rise.lower_jd_ut1
                                      and edge.lower_jd_ut1 <= next_rise.upper_jd_ut1)
    bands = _bands(boundaries)
    cells = tuple(MuhurtaDoshaCell(ShuddhiInterval(a, b), assessment((a.upper_jd_ut1+b.lower_jd_ut1)/2))
                  for a, b in zip(bands, bands[1:]) if a.upper_jd_ut1 < b.lower_jd_ut1)
    return product(cells, bands)


def calculate_day(local_date, latitude, longitude, *, timezone, necessary_activity=None,
                  policy=None, reader=None):
    """Strict preflight before borrowing a reader for one bounded sunrise day."""
    active = MuhurtaDoshaPolicy() if policy is None else policy
    if not isinstance(active, MuhurtaDoshaPolicy):
        raise ValueError("policy must be MuhurtaDoshaPolicy")
    if necessary_activity is not None and type(necessary_activity) is not bool:
        raise ValueError("necessary_activity must be a boolean or None")
    if type(local_date) is not date or not 2 <= local_date.year <= 9998:
        raise ValueError("local_date must be a date with year in [2,9998]")
    lat, lon = _number("latitude", latitude), _number("longitude", longitude)
    if not -90 < lat < 90 or not -180 <= lon <= 180:
        raise ValueError("latitude must be in (-90,90), longitude in [-180,180]")
    zone = _resolve_timezone(timezone)
    for offset in (-1, 0, 1):
        _civil_bounds(local_date+timedelta(days=offset), zone)
    try:
        bound = get_reader() if reader is None else reader
        with use_reader_override(bound):
            return _compose(local_date, lat, lon, timezone, necessary_activity, active, bound,
                            "active_context_reader" if reader is None else "caller_owned_reader")
    except OutOfRangeError as exc:
        raise MuhurtaCoverageError("dosha date or full-event search margins exceed kernel coverage") from exc
    except (MissingKernelError, _EphemerisTimeBasisError, LookupError, FileNotFoundError) as exc:
        raise MuhurtaResourceError("required dosha reader or clock resource is unavailable") from exc
