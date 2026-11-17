"""Conditional native inverse in the post-handoff future scenario."""
from __future__ import annotations

from dataclasses import dataclass

from . import julian as _j
from ._eclipse_canon_clock_bounds import (
    CanonClockBoundsUnavailable, _anchor_and_input,
)
from ._eclipse_future_clock_bounds import (
    _future_seconds, _require_future_sources, bound_future_native_ut1_to_tt,
)
from ._eclipse_historical_inverse_bounds import (
    _DELTA, _EOP_INVERSE, _FROM_JD, _GENERIC, _INVERSE, _YEAR,
)
from . import _ephemeris_time as _time
from ._eclipse_native_clock_bounds import _native_months_for_interval as _months_for_interval
from ._eclipse_interval import IntervalBudgetError, IntervalDomainError, RationalInterval
from ._eclipse_native_clock_bounds import NativeClockBoundsUnavailable, _require_sources, _rn
from .spk_reader import SpkReader


@dataclass(frozen=True, slots=True)
class FutureNativeInverseBounds:
    """Conditional inverse clock enclosure for the future scenario."""
    anchor_jd: float
    input_offset_days: RationalInterval
    output_offset_days: RationalInterval
    source_and_arithmetic_attested: bool = False
    successful_outputs_only: bool = True
    inverse_uniqueness_certified: bool = False
    physical_delta_t_accuracy_certified: bool = False


def _seconds(reader, anchor, interval, max_days, *, model_only=False):
    p = RationalInterval.point
    if not model_only:
        bound_future_native_ut1_to_tt(reader, anchor, interval - p(anchor), max_days=max_days)
    boundary = _j._delta_t_observation_boundary()
    outputs = []
    for year in sorted({y for y, _ in _months_for_interval(interval, max_days=max_days)}):
        start, end = _j.julian_day(year, 1, 1), _j.julian_day(year + 1, 1, 1)
        part = interval.intersect(RationalInterval(start - 1, end + 1))
        if part is None:
            continue
        y = _rn(p(year) + _rn(_rn(part - p(start)) / _rn(p(end) - p(start))))
        outputs.append(_future_seconds(y, boundary.year, boundary.total))
    if not outputs:
        raise NativeClockBoundsUnavailable("future inverse source unavailable")
    return RationalInterval(min(x.lo for x in outputs), max(x.hi for x in outputs))


def bound_future_native_tt_to_ut1(reader, anchor_jd, offset_days, *, max_days=32):
    """Enclose successful future inverse iterations, never physical uncertainty."""
    _require_sources()
    _require_future_sources()
    if (_time._ephemeris_tt_to_ut1 is not _INVERSE or _time.tt_to_ut is not _GENERIC
            or _j.tt_to_ut is not _GENERIC or _j._policy_year_from_jd is not _YEAR
            or _j.delta_t is not _DELTA or _j.delta_t_from_jd is not _FROM_JD
            or _j.EOPRegistry.__dict__["_ut1_from_tt"] is not _EOP_INVERSE):
        raise NativeClockBoundsUnavailable("native inverse source changed")
    if type(reader) is not SpkReader:
        raise NativeClockBoundsUnavailable("a direct SPK reader is required")
    try:
        anchor, tt = _anchor_and_input(anchor_jd, offset_days, max_days)
        p = RationalInterval.point
        data = _j.EOPRegistry._ensure_loaded()
        if data and tt.lo <= p(2400000.5).lo + max(data) + 4:
            raise NativeClockBoundsUnavailable("initial inverse might use EOP")
        seconds = _seconds(reader, anchor, tt, max_days)
        current = _rn(tt - _rn(seconds / p(86400.0)))
        for _ in range(8):
            seconds = _seconds(reader, anchor, current, max_days)
            current = _rn(tt - _rn(seconds / p(86400.0)))
        for _ in range(12):
            seconds = _seconds(reader, anchor, current, max_days)
            next_ut = _rn(tt - _rn(seconds / p(86400.0)))
            current = RationalInterval(min(current.lo, next_ut.lo), max(current.hi, next_ut.hi))
        return FutureNativeInverseBounds(anchor, offset_days, current - p(anchor))
    except (CanonClockBoundsUnavailable, IntervalBudgetError, IntervalDomainError, OverflowError) as exc:
        raise NativeClockBoundsUnavailable("future inverse domain or arithmetic unavailable") from exc
