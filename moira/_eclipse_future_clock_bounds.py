"""Conditional enclosure of the post-EOP deterministic future clock scenario.

The supported branch begins after the EOP taper and observation boundary.
Source definitions, EOP/aggregate data, and binary64 arithmetic are assumed
stable, not attested. This is not an accuracy bound on future Earth rotation.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from . import delta_t_physical as _physical
from . import julian as _j
from ._eclipse_canon_clock_bounds import (
    CanonClockBoundsUnavailable, _anchor_and_input,
)
from ._eclipse_interval import IntervalBudgetError, IntervalDomainError, RationalInterval
from ._eclipse_native_clock_bounds import (
    _native_months_for_interval as _months_for_interval,
    NativeClockBoundsUnavailable, _require_sources, _rn, _snapshot_sources,
)
from .spk_reader import SpkReader

_FUNCTIONS = {name: getattr(_physical, name) for name in (
    "delta_t_hybrid", "delta_t_breakdown", "secular_trend", "_reference_year",
    "_reference_total", "_future_bridge_delta_t", "_coerce_model_year",
)}
_OBSERVATION = _j._delta_t_observation_boundary
_CONSTANTS = (_physical.REFERENCE_LOD, _physical.TIDAL_COEFF, _physical.GIA_COEFF)


@dataclass(frozen=True, slots=True)
class FutureNativeClockBounds:
    """Conditional forward clock enclosure for the future scenario."""
    anchor_jd: float
    input_offset_days: RationalInterval
    output_offset_days: RationalInterval
    possible_years: tuple[int, ...]
    eop_sha256: str
    reference_year: float
    reference_total_seconds: float
    source_and_arithmetic_attested: bool = False
    successful_outputs_only: bool = True
    inverse_enclosed: bool = False
    physical_delta_t_accuracy_certified: bool = False


def _require_future_sources():
    if (any(getattr(_physical, name) is not fn for name, fn in _FUNCTIONS.items())
            or _j._delta_t_observation_boundary is not _OBSERVATION
            or _physical._delta_t_observation_boundary is not _OBSERVATION
            or (_physical.REFERENCE_LOD, _physical.TIDAL_COEFF,
                _physical.GIA_COEFF) != _CONSTANTS):
        raise NativeClockBoundsUnavailable("future clock source changed")


def _future_seconds(y, reference, total):
    p = RationalInterval.point
    if (y.lo <= reference or y.lo < 2005 or y.lo < _j._DELTA_T_ANNUAL[0][0]
            or y.lo < _j._delta_t_hpiers_annual_bridge()[-1][0]):
        raise NativeClockBoundsUnavailable("future-model source branch not established")
    centuries = _rn(_rn(y - p(reference)) / p(100.0))
    coefficient = _rn(p(_physical.TIDAL_COEFF) + p(_physical.GIA_COEFF))
    secular = _rn(p(_physical.REFERENCE_LOD) + _rn(_rn(coefficient * centuries) * centuries))
    bridge = _rn(p(total) - p(_physical.REFERENCE_LOD))
    return _rn(secular + bridge)


def bound_future_native_ut1_to_tt(reader, anchor_jd, offset_days, *, max_days=32):
    """Enclose the post-handoff future scenario, conditional on its sources."""
    _require_sources()
    _require_future_sources()
    if type(reader) is not SpkReader:
        raise NativeClockBoundsUnavailable("a direct SPK reader is required")
    try:
        anchor, ut = _anchor_and_input(anchor_jd, offset_days, max_days)
        years = tuple(sorted({y for y, _ in _months_for_interval(ut, max_days=max_days)}))
        _, _, digest, _ = _snapshot_sources()
        data = _j.EOPRegistry._ensure_loaded()
        window = _j._EOP_HANDOFF_WINDOW_DAYS
        if data:
            last_mjd = max(data)
            last_segment = _j.EOPRegistry._segment_bounds(last_mjd, data)
            if last_segment is None or not math.isfinite(last_segment[2]):
                raise NativeClockBoundsUnavailable("last EOP segment unavailable")
            label_guard = RationalInterval.point(2400000.5).lo + last_mjd + 2
            last_end = RationalInterval.point(last_segment[2]).lo
            cutoff = max(label_guard, last_end) + RationalInterval.point(window).lo + 1
            if ut.lo <= cutoff:
                raise NativeClockBoundsUnavailable("EOP handoff or earlier epoch unsupported")
        boundary = _OBSERVATION()
        reference, total = boundary.year, boundary.total
        if not math.isfinite(reference) or not math.isfinite(total):
            raise NativeClockBoundsUnavailable("invalid observation boundary")
        p = RationalInterval.point
        outputs = []
        for year in years:
            start, end = _j.julian_day(year, 1, 1), _j.julian_day(year + 1, 1, 1)
            part = ut.intersect(RationalInterval(start - 1, end + 1))
            if part is None:
                continue
            y = _rn(p(year) + _rn(_rn(part - p(start)) / _rn(p(end) - p(start))))
            seconds = _future_seconds(y, reference, total)
            outputs.append(_rn(part + _rn(seconds / p(86400.0))))
        if not outputs:
            raise NativeClockBoundsUnavailable("future year unavailable")
        tt = RationalInterval(min(x.lo for x in outputs), max(x.hi for x in outputs))
        return FutureNativeClockBounds(anchor, offset_days, tt - p(anchor), years,
                                       digest, reference, total)
    except (CanonClockBoundsUnavailable, IntervalBudgetError, IntervalDomainError, OverflowError) as exc:
        raise NativeClockBoundsUnavailable("future clock domain or arithmetic unavailable") from exc
