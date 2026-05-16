"""
Moira — transits_equatorial.py
The Predictive Equatorial Engine: governs declination parallels, contra-parallels,
and out-of-bounds (OOB) crossings.
"""

import math
from dataclasses import dataclass
from typing import Literal

from .spk_reader import SpkReader, get_reader
from .transits import _auto_step, _require_non_empty_body, _validate_transit_range, _validate_search_motion, _require_positive, TransitComputationPolicy, _validate_policy
from .planets import planet_at
from .asteroids import asteroid_at, ASTEROID_NAIF
from .stars import star_at
from .julian import ut_to_tt
from .constants import Body
from .coordinates import equatorial_to_horizontal, true_ecliptic_latitude, icrf_to_equatorial
from .planets import _npe_body_route_segment_specs
import moira.moira_native as mn

__all__ = ["EquatorialTransitEvent", "find_declination_transits"]

@dataclass(slots=True)
class EquatorialTransitEvent:
    """An exact declination parallel or contra-parallel hit."""
    body: str
    target: str | float
    is_contra_parallel: bool
    jd_exact: float
    declination: float
    search_motion: str = "forward"

def _declination(spec: str | float, jd: float, reader: SpkReader) -> float:
    """Resolves the equatorial declination of a body or a static float."""
    if isinstance(spec, (int, float)):
        return float(spec)
        
    name = str(spec).strip()
    lon = lat = 0.0
    if name in Body.ALL_PLANETS:
        p = planet_at(name, jd, reader=reader)
        lon, lat = p.longitude, p.latitude
    elif name in ASTEROID_NAIF or any(key.lower() == name.lower() for key in ASTEROID_NAIF):
        a = asteroid_at(name, jd, de441_reader=reader)
        lon, lat = a.longitude, a.latitude
    else:
        try:
            s = star_at(name, ut_to_tt(jd))
            lon, lat = s.longitude, s.latitude
        except Exception as exc:
            raise ValueError(f"Equatorial target specification could not be resolved: {name}") from exc

    from .coordinates import ecliptic_to_equatorial
    from .obliquity import true_obliquity
    eps = true_obliquity(ut_to_tt(jd))
    ra, dec = ecliptic_to_equatorial(lon, lat, eps)
    return dec

def _find_declination_crossing(
    body: str,
    target: str | float,
    is_contra: bool,
    jd_lo: float,
    jd_hi: float,
    reader: SpkReader,
    tol_days: float = 1e-6,
) -> float:
    """Bisect to find when body declination equals target declination (or -target for contra)."""
    def _diff(jd_val: float) -> float:
        b_dec = _declination(body, jd_val, reader)
        t_dec = _declination(target, jd_val, reader)
        return b_dec - (-t_dec if is_contra else t_dec)

    sign_lo = _diff(jd_lo)
    for _ in range(60):
        jd_mid = (jd_lo + jd_hi) / 2.0
        if jd_hi - jd_lo < tol_days:
            break
        sign_mid = _diff(jd_mid)
        if sign_lo * sign_mid <= 0:
            jd_hi = jd_mid
        else:
            jd_lo = jd_mid
            sign_lo = sign_mid
    return (jd_lo + jd_hi) / 2.0

def _get_native_evaluator(body: str, specs: dict, path: str) -> mn.IEvaluator | None:
    """Construct a native evaluator chain for a body's barycentric route."""
    if body not in specs:
        return None
    route = specs[body]
    evals = [mn.load_spk_segment_evaluator(path, s[0], s[1], True, s[2]) for s in route]
    if len(evals) == 1: return evals[0]
    if len(evals) == 2: return mn.SumEvaluator(evals[0], evals[1])
    return None

def _find_candidate_declination_windows_native(
    body: str,
    target: str,
    is_contra: bool,
    jd_start: float,
    jd_end: float,
    step_days: float,
    reader: SpkReader,
) -> list[tuple[float, float]]:
    """Use native batch processing to find windows where a declination hit might occur."""
    de441 = None
    if hasattr(reader, "_readers"):
        for r in reader._readers:
            if "de441" in str(r.path).lower():
                de441 = r; break
    elif "de441" in str(reader.path).lower():
        de441 = reader
    if not de441: return None
    
    jd_tt_start = ut_to_tt(jd_start)
    specs = _npe_body_route_segment_specs(de441, jd_tt_start)
    if not specs: return None
    
    path = str(de441.path)
    e_body = _get_native_evaluator(body, specs, path)
    e_target = _get_native_evaluator(target, specs, path) if isinstance(target, str) and target in specs else None
    e_earth = _get_native_evaluator('Earth', specs, path)
    if not e_body or not e_earth: return None
    
    jds = []
    curr = jd_start
    while curr <= jd_end:
        jds.append(ut_to_tt(curr)); curr += step_days
    if not jds: return []
    
    b_decs = mn.declination_batch(e_body, e_earth, jds)
    if e_target:
        t_decs = mn.declination_batch(e_target, e_earth, jds)
    else:
        # Static target declination
        t_dec_static = float(target)
        t_decs = [t_dec_static] * len(jds)
        
    windows = []
    for i in range(len(jds) - 1):
        d1 = b_decs[i] - (-t_decs[i] if is_contra else t_decs[i])
        d2 = b_decs[i+1] - (-t_decs[i+1] if is_contra else t_decs[i+1])
        if d1 * d2 <= 0:
            windows.append((jd_start + i * step_days, jd_start + (i+1) * step_days))
    return windows

def find_declination_transits(
    body: str,
    target: str | float,
    jd_start: float,
    jd_end: float,
    is_contra_parallel: bool = False,
    step_days: float | None = None,
    reader: SpkReader | None = None,
    policy: TransitComputationPolicy | None = None,
    search_motion: str = "forward",
) -> list[EquatorialTransitEvent]:
    """Find all declination parallel (or contra-parallel) transits."""
    _require_non_empty_body(body)
    _validate_transit_range(jd_start, jd_end)
    _validate_search_motion(search_motion)
    if step_days is not None:
        _require_positive(step_days, "step_days")
    if reader is None:
        reader = get_reader()
    policy = _validate_policy(policy)
    if step_days is None:
        step_days = policy.transit.step_days_override or _auto_step(body)

    # --- HYBRID NATIVE SCAN ---
    if body in Body.ALL_PLANETS and (isinstance(target, (int, float)) or target in Body.ALL_PLANETS):
        windows = _find_candidate_declination_windows_native(body, target, is_contra_parallel, jd_start, jd_end, 1.0, reader)
        if windows:
            events = []
            ordered_windows = windows if search_motion == "forward" else list(reversed(windows))
            for jd_lo, jd_hi in ordered_windows:
                jd_exact = _find_declination_crossing(body, target, is_contra_parallel, max(jd_start, jd_lo-0.1), min(jd_end, jd_hi+0.1), reader, policy.transit.solver_tolerance_days)
                exact_dec = _declination(body, jd_exact, reader)
                events.append(EquatorialTransitEvent(body, target, is_contra_parallel, jd_exact, exact_dec, search_motion))
            return events
        return []

    # --- FALLBACK LOOP ---
    events: list[EquatorialTransitEvent] = []
    jd = jd_start if search_motion == "forward" else jd_end
    
    def _diff(jd_val: float) -> float:
        b_dec = _declination(body, jd_val, reader)
        t_dec = _declination(target, jd_val, reader)
        return b_dec - (-t_dec if is_contra_parallel else t_dec)

    diff_prev = _diff(jd)

    while (jd < jd_end) if search_motion == "forward" else (jd > jd_start):
        jd_next = (
            min(jd + step_days, jd_end)
            if search_motion == "forward"
            else max(jd - step_days, jd_start)
        )
        diff_next = _diff(jd_next)

        if diff_prev * diff_next < 0:
            jd_exact = _find_declination_crossing(body, target, is_contra_parallel, jd, jd_next, reader, policy.transit.solver_tolerance_days)
            exact_dec = _declination(body, jd_exact, reader)
            events.append(EquatorialTransitEvent(
                body=body,
                target=target,
                is_contra_parallel=is_contra_parallel,
                jd_exact=jd_exact,
                declination=exact_dec,
                search_motion=search_motion,
            ))

        jd = jd_next
        diff_prev = diff_next

    return events
