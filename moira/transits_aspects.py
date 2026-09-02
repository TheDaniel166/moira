"""
Moira — transits_aspects.py
The Predictive Aspect Engine: governs transit-to-transit and transit-to-natal
aspect orb boundaries (applying, exact, separating) and aspect geometry sweeps.

Boundary: Owns the geometric relation (angle and orb) between two moving or static
bodies. Delegates position resolution to the core transit engine.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from .spk_reader import SpkReader, get_reader
from .transits import (
    _resolve_longitude,
    _auto_step,
    _require_non_empty_body,
    _validate_transit_range,
    _validate_search_motion,
    _require_positive,
    TransitComputationPolicy,
    _validate_policy,
)
from .planets import Body, _npe_body_route_segment_specs
from .asteroids import ASTEROID_NAIF
from ._ephemeris_time import _ut1_to_ephemeris_tt
try:
    from . import moira_native as mn
except ImportError:
    mn = None

__all__ = [
    "AspectTransitEvent",
    "find_aspect_transits",
    "find_aspect_transits_to_longitudes",
]

@dataclass(slots=True)
class AspectTransitEvent:
    """An exact aspect hit, optionally with its applying/separating orb boundaries."""
    body: str
    target: str | float
    angle: float
    orb: float
    jd_exact: float
    jd_entering: float | None
    jd_leaving: float | None
    is_retrograde_hit: bool
    search_motion: str = "forward"

def _signed_diff(a: float, b: float) -> float:
    """Signed angular difference a − b, normalised to (−180, +180]."""
    return (a - b + 180.0) % 360.0 - 180.0

def _find_aspect_crossing(
    body: str,
    target: str | float,
    target_angle: float,
    jd_lo: float,
    jd_hi: float,
    reader: SpkReader,
    tol_days: float = 1e-6,
) -> float:
    """Bisect to find when (body - target) == target_angle."""
    sign_lo = _signed_diff(_resolve_longitude(body, jd_lo, reader), 
                           _resolve_longitude(target, jd_lo, reader) + target_angle)
    for _ in range(60):
        jd_mid = (jd_lo + jd_hi) / 2.0
        if jd_hi - jd_lo < tol_days:
            break
        sign_mid = _signed_diff(_resolve_longitude(body, jd_mid, reader), 
                                _resolve_longitude(target, jd_mid, reader) + target_angle)
        if sign_lo * sign_mid <= 0:
            jd_hi = jd_mid
        else:
            jd_lo = jd_mid
            sign_lo = sign_mid
    return (jd_lo + jd_hi) / 2.0

_EARTH_ROUTE_PAIRS = ((0, 3), (3, 399))


def _get_native_evaluator(body: str, specs: dict, path: str) -> object | None:
    """Construct a native evaluator chain for a body's barycentric route."""
    if mn is None or body not in specs:
        return None

    route = specs[body]
    evals = []
    for start_i, end_i, data_type in route:
        evals.append(mn.load_spk_segment_evaluator(path, start_i, end_i, True, data_type))

    if len(evals) == 1:
        return evals[0]
    if len(evals) == 2:
        return mn.SumEvaluator(evals[0], evals[1])
    return None


def _earth_native_evaluator(reader: SpkReader, path: str, jd_tt: float) -> object | None:
    """SSB → EMB → Earth, matching the admitted planetary Earth route."""
    if mn is None:
        return None
    evals = []
    try:
        for center, target in _EARTH_ROUTE_PAIRS:
            segment = reader._segment_for(center, target, jd_tt)
            if segment is None:
                return None
            evals.append(
                mn.load_spk_segment_evaluator(
                    path,
                    int(segment.start_i),
                    int(segment.end_i),
                    True,
                    int(segment.data_type),
                )
            )
    except Exception:
        return None
    if len(evals) == 2:
        return mn.SumEvaluator(evals[0], evals[1])
    return None

def _find_candidate_windows_native(
    body: str,
    target: str,
    angle: float,
    jd_start: float,
    jd_end: float,
    step_days: float,
    reader: SpkReader,
) -> list[tuple[float, float]]:
    """Use native batch processing to find windows where an aspect might occur."""
    
    # 1. Resolve the content-identified planetary reader without trusting a
    # filename. Supplemental small-body shards do not own this evaluator path.
    if isinstance(reader, SpkReader):
        planetary_reader = reader
    else:
        resolver = getattr(reader, "_primary_planetary_reader", None)
        planetary_reader = resolver() if callable(resolver) else None
    if not isinstance(planetary_reader, SpkReader):
        return []

    # 2. Get segment specs
    jd_tt_start = _ut1_to_ephemeris_tt(jd_start, reader)
    specs = _npe_body_route_segment_specs(planetary_reader, jd_tt_start)
    if not specs:
        return []
    
    # 3. Build Evaluators
    path = str(planetary_reader.path)
    e_target1 = _get_native_evaluator(body, specs, path)
    e_earth = _earth_native_evaluator(planetary_reader, path, jd_tt_start)
    if not e_target1 or not e_earth:
        return None

    jds_tt: list[float] = []
    curr = jd_start
    while curr <= jd_end:
        jds_tt.append(_ut1_to_ephemeris_tt(curr, reader))
        curr += step_days
    if len(jds_tt) < 2:
        return []

    if isinstance(target, str) and target in specs:
        e_target2 = _get_native_evaluator(target, specs, path)
        if not e_target2:
            return None
        diffs = mn.longitude_difference_batch(e_target1, e_target2, e_earth, jds_tt)
        series = None
    elif isinstance(target, (int, float)) and math.isfinite(float(target)):
        from .nutation_2000a import _ensure_tables_loaded

        _ensure_tables_loaded()
        try:
            series = mn.ecliptic_longitude_batch(e_target1, e_earth, jds_tt)
        except Exception:
            return None
        diffs = None
    else:
        return None

    if diffs is not None:
        return _windows_from_difference_series(diffs, jd_start, step_days, angle)
    return _windows_from_longitude_series(series, jd_start, step_days, float(target), angle)


def _windows_from_difference_series(
    diffs: Sequence[float],
    jd_start: float,
    step_days: float,
    angle: float,
) -> list[tuple[float, float]]:
    windows: list[tuple[float, float]] = []
    for i in range(len(diffs) - 1):
        d1 = _signed_diff(diffs[i], angle)
        d2 = _signed_diff(diffs[i + 1], angle)
        if d1 * d2 <= 0 and abs(d1) < 90.0:
            windows.append((jd_start + i * step_days, jd_start + (i + 1) * step_days))
    return windows


def _windows_from_longitude_series(
    series: Sequence[float],
    jd_start: float,
    step_days: float,
    frozen_longitude: float,
    angle: float,
) -> list[tuple[float, float]]:
    frozen = frozen_longitude % 360.0
    windows: list[tuple[float, float]] = []
    for i in range(len(series) - 1):
        d1 = _signed_diff(series[i], frozen + angle)
        d2 = _signed_diff(series[i + 1], frozen + angle)
        if d1 * d2 <= 0 and abs(d1) < 90.0:
            windows.append((jd_start + i * step_days, jd_start + (i + 1) * step_days))
    return windows


_QUARTER_TURN_DEG = 90.0
_MAX_STEP_HALVINGS = 4


@dataclass(frozen=True, slots=True)
class LongitudeSeries:
    """One mover's ecliptic longitude sampled at a fixed step over a window.

    ``tier`` names the provider that produced it (``native_planet``,
    ``native_small_body``, ``resolver``). Search code never branches on it;
    it exists for tests and receipts.
    """

    jd_start: float
    step_days: float
    values: tuple[float, ...]
    tier: str


def _sample_jds(jd_start: float, jd_end: float, step_days: float) -> list[float]:
    jds: list[float] = []
    curr = jd_start
    while curr <= jd_end:
        jds.append(curr)
        curr += step_days
    return jds


def _sample_resolver_series(
    body: str,
    jd_start: float,
    jd_end: float,
    step_days: float,
    reader: SpkReader,
) -> LongitudeSeries:
    """Tier 3: sample the transit resolver itself. Admits every body it admits."""
    values = tuple(
        _resolve_longitude(body, jd, reader) % 360.0 for jd in _sample_jds(jd_start, jd_end, step_days)
    )
    return LongitudeSeries(jd_start=jd_start, step_days=step_days, values=values, tier="resolver")


def _series_max_circular_step(values: Sequence[float]) -> float:
    """Largest absolute circular difference between consecutive samples, degrees."""
    worst = 0.0
    for i in range(len(values) - 1):
        worst = max(worst, abs(_signed_diff(values[i + 1], values[i])))
    return worst


def _longitude_series(
    body: str,
    jd_start: float,
    jd_end: float,
    step_days: float,
    reader: SpkReader,
) -> LongitudeSeries | None:
    """Return the mover's longitude series for candidate-window detection.

    Tries native providers first, then the resolver. Whatever produced the
    series, the quarter-turn guard halves the step and resamples while any
    consecutive pair differs by more than 90 degrees, up to
    ``_MAX_STEP_HALVINGS`` times. Returns ``None`` when no provider can
    satisfy the guard; the caller then falls back to per-target searches.
    """
    step = float(step_days)
    for _ in range(_MAX_STEP_HALVINGS + 1):
        series: LongitudeSeries | None = None
        native = _native_ecliptic_longitude_series(body, jd_start, jd_end, step, reader)
        if native is not None:
            series = LongitudeSeries(
                jd_start=jd_start,
                step_days=step,
                values=tuple(float(v) % 360.0 for v in native),
                tier="native_planet",
            )
        if series is None:
            native_sb = _native_small_body_series(body, jd_start, jd_end, step, reader)
            if native_sb is not None:
                series = LongitudeSeries(
                    jd_start=jd_start,
                    step_days=step,
                    values=tuple(float(v) % 360.0 for v in native_sb),
                    tier="native_small_body",
                )
        if series is None:
            series = _sample_resolver_series(body, jd_start, jd_end, step, reader)
        if len(series.values) < 2:
            return None
        if _series_max_circular_step(series.values) <= _QUARTER_TURN_DEG:
            return series
        step /= 2.0
    return None


def _native_ecliptic_longitude_series(
    body: str,
    jd_start: float,
    jd_end: float,
    step_days: float,
    reader: SpkReader,
) -> list[float] | None:
    if mn is None or body not in Body.ALL_PLANETS:
        return None
    if isinstance(reader, SpkReader):
        planetary_reader = reader
    else:
        resolver = getattr(reader, "_primary_planetary_reader", None)
        planetary_reader = resolver() if callable(resolver) else None
    if not isinstance(planetary_reader, SpkReader):
        return None
    jd_tt_start = _ut1_to_ephemeris_tt(jd_start, reader)
    specs = _npe_body_route_segment_specs(planetary_reader, jd_tt_start)
    if not specs:
        return None
    path = str(planetary_reader.path)
    e_body = _get_native_evaluator(body, specs, path)
    e_earth = _earth_native_evaluator(planetary_reader, path, jd_tt_start)
    if not e_body or not e_earth:
        return None
    jds_tt: list[float] = []
    curr = jd_start
    while curr <= jd_end:
        jds_tt.append(_ut1_to_ephemeris_tt(curr, reader))
        curr += step_days
    if len(jds_tt) < 2:
        return None
    from .nutation_2000a import _ensure_tables_loaded

    _ensure_tables_loaded()
    try:
        return mn.ecliptic_longitude_batch(e_body, e_earth, jds_tt)
    except Exception:
        return None

_SSB = 0
_SUN = 10


def _small_body_segment(reader, naif_id: int, jd_tt_start: float, jd_tt_end: float):
    """Return the Type 13 segment covering the whole window for *naif_id*, or None."""
    readers = getattr(reader, "_readers", None)
    if readers is None:
        return None
    for candidate in readers:
        has_body = getattr(candidate, "has_body", None)
        kernel = getattr(candidate, "_kernel", None)
        if not callable(has_body) or kernel is None or not has_body(naif_id):
            continue
        for seg in kernel.segments:
            if seg.target == naif_id and seg.start_jd <= jd_tt_start and jd_tt_end <= seg.end_jd:
                return seg
    return None


def _native_small_body_series(
    body: str,
    jd_start: float,
    jd_end: float,
    step_days: float,
    reader: SpkReader,
) -> list[float] | None:
    """Tier 2: geometric ecliptic longitude of a named asteroid from its Type 13 evaluator.

    The small-body segment is heliocentric in the wheel catalog, so the
    target chain is SSB->Sun (planetary kernel) plus Sun->asteroid (Type 13),
    against the admitted Earth route. Any missing piece steps down to the
    resolver tier.
    """
    if mn is None:
        return None
    naif_id = ASTEROID_NAIF.get(body)
    if naif_id is None:
        return None
    resolver = getattr(reader, "_primary_planetary_reader", None)
    planetary_reader = resolver() if callable(resolver) else None
    if not isinstance(planetary_reader, SpkReader):
        return None
    jd_tt_start = _ut1_to_ephemeris_tt(jd_start, reader)
    jd_tt_end = _ut1_to_ephemeris_tt(jd_end, reader)
    seg = _small_body_segment(reader, int(naif_id), jd_tt_start, jd_tt_end)
    if seg is None:
        return None
    try:
        e_body = seg._load_native_evaluator()
    except Exception:
        return None
    if e_body is None:
        return None
    path = str(planetary_reader.path)
    if seg.center == _SUN:
        sun = planetary_reader._segment_for(_SSB, _SUN, jd_tt_start)
        if sun is None:
            return None
        e_sun = mn.load_spk_segment_evaluator(path, int(sun.start_i), int(sun.end_i), True, int(sun.data_type))
        e_target = mn.SumEvaluator(e_sun, e_body)
    elif seg.center == _SSB:
        e_target = e_body
    else:
        return None
    e_earth = _earth_native_evaluator(planetary_reader, path, jd_tt_start)
    if e_earth is None:
        return None
    jds_tt = [_ut1_to_ephemeris_tt(jd, reader) for jd in _sample_jds(jd_start, jd_end, step_days)]
    if len(jds_tt) < 2:
        return None
    from .nutation_2000a import _ensure_tables_loaded

    _ensure_tables_loaded()
    try:
        return list(mn.ecliptic_longitude_batch(e_target, e_earth, jds_tt))
    except Exception:
        return None


def _process_aspect_hit(
    body: str,
    target: str | float,
    angle: float,
    orb: float,
    jd_lo: float,
    jd_hi: float,
    jd_start: float,
    jd_end: float,
    reader: SpkReader,
    policy: TransitComputationPolicy,
    search_motion: str,
) -> AspectTransitEvent:
    """Refine a candidate window into a high-precision AspectTransitEvent."""
    # Exact hit
    jd_exact = _find_aspect_crossing(body, target, angle, jd_lo, jd_hi, reader, policy.transit.solver_tolerance_days)
    
    # Entering/Leaving
    jd_ent, jd_lea = None, None
    if orb > 0:
        scan_horizon = 2.0 # 2 days is plenty for planets
        
        diff_before = _signed_diff(_resolve_longitude(body, max(jd_start, jd_exact - scan_horizon), reader), 
                                   _resolve_longitude(target, max(jd_start, jd_exact - scan_horizon), reader) + angle)
        diff_after = _signed_diff(_resolve_longitude(body, min(jd_end, jd_exact + scan_horizon), reader), 
                                  _resolve_longitude(target, min(jd_end, jd_exact + scan_horizon), reader) + angle)
        
        if diff_before < 0 < diff_after:
            if diff_before <= -orb:
                jd_ent = _find_aspect_crossing(body, target, angle - orb, max(jd_start, jd_exact - scan_horizon), jd_exact, reader, policy.transit.solver_tolerance_days)
            if diff_after >= orb:
                jd_lea = _find_aspect_crossing(body, target, angle + orb, jd_exact, min(jd_end, jd_exact + scan_horizon), reader, policy.transit.solver_tolerance_days)
            is_retrograde = False
        else:
            if diff_before >= orb:
                jd_ent = _find_aspect_crossing(body, target, angle + orb, max(jd_start, jd_exact - scan_horizon), jd_exact, reader, policy.transit.solver_tolerance_days)
            if diff_after <= -orb:
                jd_lea = _find_aspect_crossing(body, target, angle - orb, jd_exact, min(jd_end, jd_exact + scan_horizon), reader, policy.transit.solver_tolerance_days)
            is_retrograde = True
    else:
        l1_b = _resolve_longitude(body, jd_exact - 0.01, reader)
        l2_b = _resolve_longitude(target, jd_exact - 0.01, reader)
        l1_a = _resolve_longitude(body, jd_exact + 0.01, reader)
        l2_a = _resolve_longitude(target, jd_exact + 0.01, reader)
        speed = _signed_diff(l1_a - l2_a, l1_b - l2_b)
        is_retrograde = speed < 0

    return AspectTransitEvent(
        body=body,
        target=target,
        angle=angle,
        orb=orb,
        jd_exact=jd_exact,
        jd_entering=jd_ent,
        jd_leaving=jd_lea,
        is_retrograde_hit=is_retrograde,
        search_motion=search_motion,
    )

def find_aspect_transits(
    body: str,
    target: str | float,
    angle: float,
    orb: float,
    jd_start: float,
    jd_end: float,
    step_days: float | None = None,
    reader: SpkReader | None = None,
    policy: TransitComputationPolicy | None = None,
    search_motion: str = "forward",
) -> list[AspectTransitEvent]:
    """
    Find all aspect transits of `body` to `target` at `angle` within a date range.
    If `orb` > 0, also computes the applying and separating boundaries.
    """
    _require_non_empty_body(body)
    _validate_transit_range(jd_start, jd_end)
    _validate_search_motion(search_motion)
    if orb < 0:
        raise ValueError("Orb must be non-negative")
    if step_days is not None:
        _require_positive(step_days, "step_days")
    if reader is None:
        reader = get_reader()
    policy = _validate_policy(policy)
    if step_days is None:
        step_days = policy.transit.step_days_override or _auto_step(body)

    # --- HYBRID NATIVE SCAN ---
    # Planet-to-planet names, or a moving planet against a frozen ecliptic longitude.
    target_is_planet = isinstance(target, str) and target in Body.ALL_PLANETS
    target_is_frozen = isinstance(target, (int, float)) and math.isfinite(float(target))
    if body in Body.ALL_PLANETS and (target_is_planet or target_is_frozen):
        windows = _find_candidate_windows_native(body, target, angle, jd_start, jd_end, 1.0, reader)
        if windows is None:
            pass
        else:
            events = []
            ordered_windows = windows if search_motion == "forward" else list(reversed(windows))
            for jd_lo, jd_hi in ordered_windows:
                events.append(_process_aspect_hit(
                    body, target, angle, orb,
                    max(jd_start, jd_lo - 0.1), min(jd_end, jd_hi + 0.1),
                    jd_start, jd_end, reader, policy, search_motion
                ))
            return events

    # --- FALLBACK / REFINEMENT LOOP ---
    events: list[AspectTransitEvent] = []
    jd = jd_start if search_motion == "forward" else jd_end
    l1_prev = _resolve_longitude(body, jd, reader)
    l2_prev = _resolve_longitude(target, jd, reader)
    diff_prev = _signed_diff(l1_prev, l2_prev + angle)

    while (jd < jd_end) if search_motion == "forward" else (jd > jd_start):
        jd_next = (
            min(jd + step_days, jd_end)
            if search_motion == "forward"
            else max(jd - step_days, jd_start)
        )
        l1_next = _resolve_longitude(body, jd_next, reader)
        l2_next = _resolve_longitude(target, jd_next, reader)
        diff_next = _signed_diff(l1_next, l2_next + angle)

        if (diff_prev * diff_next < 0 and abs(diff_prev) < 90.0 and abs(diff_next) < 90.0):
            events.append(
                _process_aspect_hit(
                    body,
                    target,
                    angle,
                    orb,
                    min(jd, jd_next),
                    max(jd, jd_next),
                    jd_start,
                    jd_end,
                    reader,
                    policy,
                    search_motion,
                )
            )

        jd = jd_next
        diff_prev = diff_next

    return events


def find_aspect_transits_to_longitudes(
    body: str,
    targets: Sequence[tuple[float, float, float]],
    jd_start: float,
    jd_end: float,
    step_days: float | None = None,
    reader: SpkReader | None = None,
    policy: TransitComputationPolicy | None = None,
    search_motion: str = "forward",
) -> list[AspectTransitEvent]:
    """Find aspect hits of *body* against many frozen ecliptic longitudes.

    ``targets`` is ``(longitude_deg, aspect_angle_deg, orb_deg)``. One native
    longitude series of *body* is scanned when available; otherwise each
    target is searched independently.
    """

    _require_non_empty_body(body)
    _validate_transit_range(jd_start, jd_end)
    _validate_search_motion(search_motion)
    if reader is None:
        reader = get_reader()
    policy = _validate_policy(policy)
    if step_days is not None:
        scan_step = float(step_days)
    else:
        scan_step = policy.transit.step_days_override or _auto_step(body)
    series = _longitude_series(body, jd_start, jd_end, scan_step, reader)
    events: list[AspectTransitEvent] = []
    if series is None:
        for longitude, angle, orb in targets:
            events.extend(
                find_aspect_transits(
                    body,
                    float(longitude),
                    float(angle),
                    float(orb),
                    jd_start,
                    jd_end,
                    step_days=step_days,
                    reader=reader,
                    policy=policy,
                    search_motion=search_motion,
                )
            )
        events.sort(key=lambda event: event.jd_exact)
        return events

    for longitude, angle, orb in targets:
        if not math.isfinite(float(longitude)) or not math.isfinite(float(angle)):
            raise ValueError("natal aspect target longitude and angle must be finite")
        if float(orb) < 0:
            raise ValueError("Orb must be non-negative")
        windows = _windows_from_longitude_series(
            series.values, series.jd_start, series.step_days, float(longitude), float(angle)
        )
        ordered = windows if search_motion == "forward" else list(reversed(windows))
        pad = series.step_days
        for jd_lo, jd_hi in ordered:
            events.append(
                _process_aspect_hit(
                    body,
                    float(longitude),
                    float(angle),
                    float(orb),
                    max(jd_start, jd_lo - pad),
                    min(jd_end, jd_hi + pad),
                    jd_start,
                    jd_end,
                    reader,
                    policy,
                    search_motion,
                )
            )
    events.sort(key=lambda event: event.jd_exact)
    return events
