"""
Moira — transits_houses.py
The Predictive Geographic Engine: governs topocentric house ingresses.
"""

import math
from dataclasses import dataclass
from typing import Literal

from .spk_reader import SpkReader, get_reader
from .transits import _auto_step, _require_non_empty_body, _validate_transit_range, _require_positive, TransitComputationPolicy, _validate_policy, _resolve_longitude
from .houses import calculate_houses, classify_house_system
from .constants import Body
from .julian import ut_to_tt

__all__ = ["HouseIngressEvent", "find_house_ingresses"]

@dataclass(slots=True)
class HouseIngressEvent:
    """An exact topocentric house ingress."""
    body: str
    house_index: int  # 1 through 12
    jd_exact: float
    longitude: float

def _signed_diff(a: float, b: float) -> float:
    return (a - b + 180.0) % 360.0 - 180.0

def _find_house_crossing(
    body: str,
    house_idx: int,
    jd_lo: float,
    jd_hi: float,
    lat: float,
    lon: float,
    system: str,
    reader: SpkReader,
    tol_days: float = 1e-5, # Houses move fast (~1 degree per 4 minutes)
) -> float:
    """Bisect to find when body crosses the specific house cusp."""
    def _diff(jd_val: float) -> float:
        b_lon = _resolve_longitude(body, jd_val, reader)
        cusps = calculate_houses(jd_val, lat, lon, system)
        h_lon = cusps.cusps[house_idx - 1] # 0-indexed internally
        return _signed_diff(b_lon, h_lon)

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

def find_house_ingresses(
    body: str,
    lat: float,
    lon: float,
    jd_start: float,
    jd_end: float,
    system: str = "placidus",
    step_days: float | None = None,
    reader: SpkReader | None = None,
    policy: TransitComputationPolicy | None = None,
) -> list[HouseIngressEvent]:
    """
    Find all house ingresses of `body` for a specific geographic location.
    
    Warning: Because house cusps rotate 360 degrees per day, finding a planetary 
    crossing of a house cusp requires very fine step sizes. If `step_days` is None, 
    we default to ~1 hour (0.04 days) to ensure no crossings are skipped.
    """
    _require_non_empty_body(body)
    _validate_transit_range(jd_start, jd_end)
    if step_days is not None:
        _require_positive(step_days, "step_days")
    if reader is None:
        reader = get_reader()
    policy = _validate_policy(policy)
    
    # House cusps move incredibly fast compared to planets.
    # To catch a planet crossing a moving cusp reliably, we need a small step size.
    if step_days is None:
        step_days = 0.04 # roughly 1 hour

    events: list[HouseIngressEvent] = []
    jd = jd_start
    
    def _diffs(jd_val: float) -> list[float]:
        b_lon = _resolve_longitude(body, jd_val, reader)
        cusps = calculate_houses(jd_val, lat, lon, system)
        return [_signed_diff(b_lon, c) for c in cusps.cusps]

    diffs_prev = _diffs(jd)

    while jd < jd_end:
        jd_next = min(jd + step_days, jd_end)
        diffs_next = _diffs(jd_next)

        for i in range(12):
            # A crossing happens when the diff changes sign AND the jump is not a wrap-around artifact.
            # However, because both planet and cusp move, the relative speed is very high.
            # We must be careful to only count valid crossings where the planet crosses the cusp,
            # not just the cusp flying past the planet. Astrologically, a house ingress is when
            # the planet moves forward *into* the house relative to the cusp.
            # Actually, since cusps move ~360 deg/day and planets move 1 deg/day,
            # the cusp crosses the planet every day. 
            # In predictive astrology, geographic house transits typically refer to 
            # exactly this daily phenomenon!
            if diffs_prev[i] * diffs_next[i] < 0 and abs(diffs_prev[i]) < 90.0 and abs(diffs_next[i]) < 90.0:
                jd_exact = _find_house_crossing(body, i + 1, jd, jd_next, lat, lon, system, reader, tol_days=1e-5)
                exact_lon = _resolve_longitude(body, jd_exact, reader)
                events.append(HouseIngressEvent(
                    body=body,
                    house_index=i + 1,
                    jd_exact=jd_exact,
                    longitude=exact_lon
                ))

        jd = jd_next
        diffs_prev = diffs_next

    return events
