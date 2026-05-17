"""
Moira — transits_aspects.py
The Predictive Aspect Engine: governs transit-to-transit and transit-to-natal
aspect orb boundaries (applying, exact, separating) and aspect geometry sweeps.

Boundary: Owns the geometric relation (angle and orb) between two moving or static
bodies. Delegates position resolution to the core transit engine.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

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
from .julian import ut_to_tt
try:
    from . import moira_native as mn
except ImportError:
    mn = None

__all__ = ["AspectTransitEvent", "find_aspect_transits"]

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
    elif len(evals) == 2:
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
    from .planets import _NPE_BODY_ROUTE_PAIRS
    
    # 1. Identify SpkReader for DE441
    de441 = None
    if hasattr(reader, "_readers"): # KernelPool
        for r in reader._readers:
            if "de441" in str(r.path).lower():
                de441 = r
                break
    elif "de441" in str(reader.path).lower():
        de441 = reader
    
    if de441 is None:
        return []

    # 2. Get segment specs
    jd_tt_start = ut_to_tt(jd_start)
    specs = _npe_body_route_segment_specs(de441, jd_tt_start)
    if not specs:
        return []
    
    # 3. Build Evaluators
    path = str(de441.path)
    e_target1 = _get_native_evaluator(body, specs, path)
    
    # Target may be a body or a fixed longitude
    if isinstance(target, str) and target in specs:
        e_target2 = _get_native_evaluator(target, specs, path)
    else:
        # For numeric target, we can't use native batching easily yet, fallback to Python
        return None
        
    e_earth = _get_native_evaluator('Earth', specs, path)
    if not e_target1 or not e_target2 or not e_earth:
        return None
    
    # 4. Batch Evaluate
    jds = []
    curr = jd_start
    while curr <= jd_end:
        jds.append(ut_to_tt(curr))
        curr += step_days
    if not jds: return []
    
    # Geometric longitude difference
    diffs = mn.longitude_difference_batch(e_target1, e_target2, e_earth, jds)
    
    # 5. Identify Sign Changes
    windows = []
    for i in range(len(jds) - 1):
        d1 = _signed_diff(diffs[i], angle)
        d2 = _signed_diff(diffs[i+1], angle)
        if d1 * d2 <= 0 and abs(d1) < 90.0:
            windows.append((jd_start + i * step_days, jd_start + (i+1) * step_days))
            
    return windows

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
    # If both bodies are planets and we have native support, pre-filter windows.
    if isinstance(target, str) and body in Body.ALL_PLANETS and target in Body.ALL_PLANETS:
        # Use 1-day coarse grid to isolate hits
        windows = _find_candidate_windows_native(body, target, angle, jd_start, jd_end, 1.0, reader)
        if windows:
            events = []
            ordered_windows = windows if search_motion == "forward" else list(reversed(windows))
            for jd_lo, jd_hi in ordered_windows:
                # Pad window slightly to ensure bisection doesn't miss if crossing is near boundary
                events.append(_process_aspect_hit(
                    body, target, angle, orb, 
                    max(jd_start, jd_lo - 0.1), min(jd_end, jd_hi + 0.1),
                    jd_start, jd_end, reader, policy, search_motion
                ))
            return events
        # If native scanner found zero windows, we are done (planetary aspects are well-behaved)
        return []

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
