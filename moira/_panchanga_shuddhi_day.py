"""Bounded sunrise-day composition for the source-selected Shuddhi profiles.

Hourly celestial discovery and adaptive three-minute Lagna discovery bracket
every admitted sector crossing. Labels belong to the open space between root
bands; the bands themselves make no categorical claim.
"""
from bisect import bisect_right
from dataclasses import replace
from datetime import date, timedelta
from functools import lru_cache
import math

from .daily_panchanga import _resolve_timezone, _civil_bounds
from .houses import _local_angles_at
from .named_muhurta import NamedMuhurtaPolicy, named_muhurta_for_date, _refine
from .muhurta_search import MuhurtaCoverageError, MuhurtaResourceError
from .planets import planet_at
from .sidereal import tropical_to_sidereal
from .spk_reader import get_reader, use_reader_override, MissingKernelError, OutOfRangeError
from ._ephemeris_time import _EphemerisTimeBasisError
from .panchanga_shuddhi import (
    PanchangaShuddhiDay, ShuddhiBoundary, ShuddhiInterval, ShuddhiCell,
    _integer, _number, _policy, panchanga_shuddhi_from_longitudes,
)


def _crossings(phase, divisions, start, end, step, tolerance, kind):
    """Forward circular phase; bounded adaptive discovery, then bisection.

    Monotonicity is an admission condition. An unresolved crossing fails the
    product rather than publishing an interpolated or sampled boundary.
    """
    span = 360 / divisions
    roots = []
    calls = 0

    def value(t):
        nonlocal calls
        calls += 1
        if calls > 16384:
            raise ValueError(f"{kind}: transition discovery budget exceeded")
        result = phase(t)
        if not math.isfinite(result) or not 0 <= result < 360:
            raise ValueError(f"{kind}: invalid circular phase")
        return result

    def segment(a, b, va, vb, depth=0):
        advance = (vb-va) % 360
        if advance > span/2:
            if depth >= 24 or (b-a)*86400 <= tolerance:
                raise ValueError(f"{kind}: nonmonotonic or unresolved phase")
            mid = (a+b)/2
            vm = value(mid)
            segment(a, mid, va, vm, depth+1)
            segment(mid, b, vm, vb, depth+1)
            return
        # Scale as a ratio instead of dividing by a rounded subdivision width.
        sector = math.floor(va*divisions/360)
        target = (sector+1)*360/divisions
        if va+advance < target:
            return
        target %= 360
        low, high = a, b
        for _ in range(64):
            if (high-low)*86400 <= tolerance:
                break
            mid = (low+high)/2
            if mid in (low, high):
                raise ValueError(f"{kind}: floating-point root resolution exhausted")
            residual = (value(mid)-target+180) % 360-180
            if residual < 0:
                low = mid
            else:
                high = mid
        if (high-low)*86400 > tolerance:
            raise ValueError(f"{kind}: root tolerance unmet")
        roots.append(ShuddhiBoundary(kind, (low+high)/2, low, high))

    a, va = start, value(start)
    while a < end:
        b = min(a+step, end)
        vb = value(b)
        segment(a, b, va, vb)
        a, va = b, vb
    return tuple(roots)


def _span(roots, jd):
    index = bisect_right([x.jd_ut1 for x in roots], jd)
    if not 0 < index < len(roots):
        raise ValueError("full event unavailable inside bounded three-day search margin")
    return ShuddhiInterval(roots[index-1], roots[index])


def _bands(boundaries):
    """Merge overlapping numerical uncertainty; keep distinct exact points."""
    result = []
    for item in sorted(boundaries, key=lambda b: b.lower_jd_ut1):
        if result and item.lower_jd_ut1 <= result[-1].upper_jd_ut1:
            previous = result.pop()
            lo, hi = previous.lower_jd_ut1, max(previous.upper_jd_ut1, item.upper_jd_ut1)
            kinds = tuple(dict.fromkeys((*previous.kind.split("+"), *item.kind.split("+"))))
            result.append(ShuddhiBoundary("+".join(kinds), (lo+hi)/2, lo, hi))
        else:
            result.append(item)
    if len(result) > 512:
        raise ValueError("Shuddhi day exceeds 512 transition bands")
    return tuple(result)


def _convert(anchor, kind=None):
    return None if anchor is None else ShuddhiBoundary(kind or anchor.kind,
        anchor.jd_ut1, anchor.lower_jd_ut1, anchor.upper_jd_ut1)


def _compose_day(local_date, latitude, longitude, timezone, natal, active, bound, binding):
    solar_policy = NamedMuhurtaPolicy(sunrise_definition=active.sunrise_definition,
                                    solver_tolerance_seconds=active.solver_tolerance_seconds)
    named = named_muhurta_for_date(local_date, latitude, longitude, timezone=timezone,
                                  policy=solar_policy, reader=bound)
    rise = _convert(named.result.sunrise)
    setting = _convert(named.result.sunset)
    next_rises = named.solar_dates[2].sunrises
    next_rise = None
    if len(next_rises) == 1:
        zone = _resolve_timezone(timezone)
        next_rise = _convert(_refine(next_rises[0], "sunrise", latitude, longitude,
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
        return PanchangaShuddhiDay(local_date, timezone, latitude, longitude, active,
            "unavailable" if not cells else "partial" if reasons else "available", tuple(reasons),
            rise, next_rise, setting, cells, bands, named.kernel_label, binding)

    if rise is None or next_rise is None:
        return product()
    if not 0 < next_rise.jd_ut1-rise.jd_ut1 <= 2:
        raise ValueError("sunrise-owned day must have positive extent at most two days")
    if setting is None or not rise.upper_jd_ut1 < setting.lower_jd_ut1 <= setting.upper_jd_ut1 < next_rise.lower_jd_ut1:
        setting = None
        reasons.append("sunset_between_sunrises_absent_or_unresolved")
    if natal is None:
        reasons.append("natal_nakshatra_not_supplied")

    @lru_cache(maxsize=8192)
    def longitudes(jd):
        return tuple(tropical_to_sidereal(planet_at(name, jd, reader=bound).longitude, jd, active.ayanamsa_system)
                     for name in ("Sun", "Moon"))

    def elongation(jd):
        sun, moon = longitudes(jd)
        return (moon-sun) % 360

    def yoga(jd):
        return sum(longitudes(jd)) % 360

    @lru_cache(maxsize=2048)
    def lagna(jd):
        asc = _local_angles_at(jd, latitude, longitude).asc
        return tropical_to_sidereal(asc, jd, active.ayanamsa_system)

    lo, hi = rise.jd_ut1, next_rise.jd_ut1
    tol = active.solver_tolerance_seconds
    # The full containing events may begin before sunrise or end after next sunrise.
    tithis = _crossings(elongation, 30, lo-3, hi+3, 1/24, tol, "tithi")
    karanas = _crossings(elongation, 60, lo-3, hi+3, 1/24, tol, "karana")
    yogas = _crossings(yoga, 27, lo-3, hi+3, 1/24, tol, "nitya_yoga")
    padas = _crossings(lambda jd: longitudes(jd)[1], 108, lo, hi, 1/24, tol, "moon_pada")
    # A continuous rising-ecliptic branch is admitted below the polar circle.
    # Discontinuous polar branches require a separately admitted solver.
    critical_lat = 90-max(_local_angles_at(jd, latitude, longitude).obliquity for jd in (lo, hi))
    lagna_available = abs(latitude) < critical_lat
    if lagna_available:
        lagnas = _crossings(lagna, 12, lo, hi, 3/1440, tol, "lagna_sign")
    else:
        lagnas = ()
        reasons.append("lagna_timing_at_or_above_ecliptic_polar_circle")
    boundaries = [rise, next_rise]
    boundaries.extend(b for b in (*tithis, *karanas, *yogas, *padas, *lagnas)
                      if rise.lower_jd_ut1 <= b.jd_ut1 <= next_rise.upper_jd_ut1)
    if setting is not None:
        boundaries.append(setting)

    def assessment(jd):
        sun, moon = longitudes(jd)
        result = panchanga_shuddhi_from_longitudes(sun, moon, jd_ut1=jd,
            weekday=(local_date.weekday()+1) % 7,
            lagna_sidereal_longitude=lagna(jd) if lagna_available else None,
            natal_nakshatra_index=natal,
            is_daytime=None if setting is None else jd < setting.jd_ut1,
            yoga_span=_span(yogas, jd), tithi_span=_span(tithis, jd),
            karana_span=_span(karanas, jd), policy=active)
        return replace(result, input_basis="reader_bound_true_sidereal; solved_full_event_ut1_spans")

    # First split at every astronomical transition; derive temporal subwindows
    # from their full parent events, then split again at all their endpoints.
    initial = _bands(boundaries)
    for a, b in zip(initial, initial[1:]):
        if a.upper_jd_ut1 >= b.lower_jd_ut1:
            continue
        result = assessment((a.upper_jd_ut1+b.lower_jd_ut1)/2)
        for finding in result.findings:
            for window in finding.windows:
                boundaries.extend(x for x in (window.start, window.end) if lo < x.jd_ut1 < hi)
    bands = _bands(boundaries)
    cells = tuple(ShuddhiCell(ShuddhiInterval(a, b),
                            assessment((a.upper_jd_ut1+b.lower_jd_ut1)/2))
                  for a, b in zip(bands, bands[1:]) if a.upper_jd_ut1 < b.lower_jd_ut1)
    return product(cells, bands)


def calculate_day(local_date, latitude, longitude, *, timezone, natal_nakshatra_index=None,
                  policy=None, reader=None):
    active = _policy(policy)
    if natal_nakshatra_index is not None:
        _integer("natal_nakshatra_index", natal_nakshatra_index, 0, 26)
    # Reuse strict civil/coordinate admission before reader discovery.
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
            return _compose_day(local_date, lat, lon, timezone, natal_nakshatra_index, active,
                                bound, "active_context_reader" if reader is None else "caller_owned_reader")
    except OutOfRangeError as exc:
        raise MuhurtaCoverageError("Shuddhi date or three-day event margins exceed kernel coverage") from exc
    except (MissingKernelError, _EphemerisTimeBasisError, LookupError, FileNotFoundError) as exc:
        raise MuhurtaResourceError("required Shuddhi reader or clock resource is unavailable") from exc
