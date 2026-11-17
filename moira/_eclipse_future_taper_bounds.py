"""Conditional post-EOP taper where both models are future-scenario neutral.

Code, binary64 environment, EOP and aggregate snapshots, and all endpoint
dependencies including leap-second/TAI data must remain stable; none is
attested. The enclosure concerns successful outputs, not physical accuracy.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from . import julian as _j
from ._eclipse_canon_clock_bounds import (
    CanonClockBoundsUnavailable, _anchor_and_input,
)
from ._eclipse_future_clock_bounds import _future_seconds, _require_future_sources
from ._eclipse_interval import IntervalBudgetError, IntervalDomainError, RationalInterval
from ._eclipse_native_clock_bounds import (
    _native_months_for_interval as _months_for_interval,
    NativeClockBoundsUnavailable, _require_sources, _rn, _snapshot_sources,
)
from .spk_reader import SpkReader


@dataclass(frozen=True, slots=True)
class FutureTaperBounds:
    """Conditional enclosure for the post-EOP forward clock taper."""
    anchor_jd: float
    input_offset_days: RationalInterval
    output_offset_days: RationalInterval
    eop_sha256: str
    delta_t_seconds: RationalInterval
    source_and_arithmetic_attested: bool = False
    successful_outputs_only: bool = True
    physical_delta_t_accuracy_certified: bool = False


def bound_post_eop_future_taper_ut1_to_tt(reader, anchor_jd, offset_days, *, max_days=32):
    """Bound the outer taper after the last admitted EOP segment."""
    _require_sources()
    _require_future_sources()
    if type(reader) is not SpkReader:
        raise NativeClockBoundsUnavailable("a direct SPK reader is required")
    try:
        anchor, ut = _anchor_and_input(anchor_jd, offset_days, max_days)
        _, _, digest, _ = _snapshot_sources()
        data = _j.EOPRegistry._ensure_loaded()
        if not data:
            raise NativeClockBoundsUnavailable("EOP boundary unavailable")
        mjd = max(data)
        segment = _j.EOPRegistry._segment_bounds(mjd, data)
        if segment is None:
            raise NativeClockBoundsUnavailable("last EOP segment unavailable")
        _, _, last, last_dt = segment
        midnight = 2400000.5 + mjd
        if not (midnight + 0.99 < last < midnight + 1.01):
            raise NativeClockBoundsUnavailable("unsupported last EOP geometry")
        if ut.lo < last:
            raise NativeClockBoundsUnavailable("interval precedes last EOP segment end")
        window = _j._EOP_HANDOFF_WINDOW_DAYS
        if window <= 0:
            raise NativeClockBoundsUnavailable("interval leaves post-EOP taper")
        boundary = _j._delta_t_observation_boundary()
        last_y = _j._continuous_decimal_year_from_jd(last)
        last_model = _j._resolve_delta_t(last_y)
        if last_model.source_product != "future_scenario" or last_model.tidal_terms:
            raise NativeClockBoundsUnavailable("last EOP boundary is not future-model neutral")
        p = RationalInterval.point
        distance = _rn(ut - p(last))
        if distance.lo >= window:
            weight = p(0.0)
        else:
            active = distance.intersect(RationalInterval(0, window))
            if active is None:
                raise NativeClockBoundsUnavailable("invalid taper distance")
            proximity = _rn(p(1.0) - _rn(active / p(window)))
            weight = _rn(_rn(proximity * proximity) * _rn(p(3.0) - _rn(p(2.0) * proximity)))
            if distance.hi >= window:
                weight = RationalInterval(min(weight.lo, 0), max(weight.hi, 0))
        correction = _rn(p(last_dt) - p(last_model.seconds))
        years = sorted({y for y, _ in _months_for_interval(ut, max_days=max_days)})
        outputs = []
        second_ranges = []
        for year in years:
            start, end = _j.julian_day(year, 1, 1), _j.julian_day(year + 1, 1, 1)
            part = ut.intersect(RationalInterval(start - 1, end + 1))
            if part is None:
                continue
            y = _rn(p(year) + _rn(_rn(part - p(start)) / _rn(p(end) - p(start))))
            base = _future_seconds(y, boundary.year, boundary.total)
            seconds = _rn(base + _rn(correction * weight))
            second_ranges.append(seconds)
            outputs.append(_rn(part + _rn(seconds / p(86400.0))))
        if not outputs or not math.isfinite(last_dt):
            raise NativeClockBoundsUnavailable("future taper source unavailable")
        result = RationalInterval(min(x.lo for x in outputs), max(x.hi for x in outputs))
        seconds_hull = RationalInterval(min(x.lo for x in second_ranges),
                                        max(x.hi for x in second_ranges))
        return FutureTaperBounds(anchor, offset_days, result - p(anchor), digest, seconds_hull)
    except (CanonClockBoundsUnavailable, IntervalBudgetError, IntervalDomainError, OverflowError) as exc:
        raise NativeClockBoundsUnavailable("future taper domain or arithmetic unavailable") from exc
