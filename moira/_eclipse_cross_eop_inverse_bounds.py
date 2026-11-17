"""Conditional inverse across outer EOP and supported internal-gap boundaries.

This bounds the source's EOP inverse seed or its alternative year-model seed,
then splits each UT iteration at EOP and internal-gap knots. A TT interval that
mixes seed ownership is explicitly unavailable; no uniqueness or physical
Delta-T accuracy is claimed. Source and binary64 premises remain unattested.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from . import julian as _j
from ._eclipse_canon_clock_bounds import CanonClockBoundsUnavailable, _anchor_and_input
from ._eclipse_eop_clock_bounds import bound_direct_eop_ut1_to_tt
from ._eclipse_eop_gap_bounds import bound_eop_gap_ut1_to_tt
from ._eclipse_future_inverse_bounds import _seconds as _future_seconds
from ._eclipse_future_clock_bounds import _require_future_sources
from ._eclipse_future_taper_bounds import bound_post_eop_future_taper_ut1_to_tt
from ._eclipse_historical_inverse_bounds import _hpiers_seconds
from ._eclipse_historical_taper_bounds import bound_pre_eop_hpiers_taper_ut1_to_tt
from ._eclipse_interval import IntervalBudgetError, IntervalDomainError, RationalInterval
from ._eclipse_native_clock_bounds import NativeClockBoundsUnavailable, _rn, _snapshot_sources
from ._eclipse_taper_inverse_bounds import _guard
from .spk_reader import SpkReader


@dataclass(frozen=True, slots=True)
class CrossEOPInverseBounds:
    """Conditional inverse clock enclosure across supported EOP boundaries."""
    anchor_jd: float
    input_offset_days: RationalInterval
    output_offset_days: RationalInterval
    seed: str
    source_and_arithmetic_attested: bool = False
    successful_outputs_only: bool = True
    inverse_uniqueness_certified: bool = False
    physical_delta_t_accuracy_certified: bool = False


def _eop_seed(tt, max_days):
    """Return a fully covered EOP seed, None for no candidate, else reject."""
    p = RationalInterval.point
    data = _j.EOPRegistry._ensure_loaded()
    first = (tt.lo - p(2400000.5).lo) // 1 - 2
    last = (tt.hi - p(2400000.5).lo) // 1 + 2
    if last - first > max_days + 5:
        raise NativeClockBoundsUnavailable("EOP seed enumeration budget exceeded")
    covered, outputs, upper_covered = [], [], False
    for mjd in range(first, last + 1):
        segment = _j.EOPRegistry._segment_bounds(mjd, data)
        if segment is None:
            continue
        start, dt0, end, dt1 = segment
        tt0, tt1 = start + dt0 / 86400.0, end + dt1 / 86400.0
        midnight = 2400000.5 + mjd
        if not (midnight - 0.01 < tt0 < midnight + 0.01
                and midnight + 0.99 < tt1 < midnight + 1.01 and tt0 < tt1):
            raise NativeClockBoundsUnavailable("unsupported EOP seed geometry")
        upper_covered |= tt0 <= tt.hi < tt1
        owned = tt.intersect(RationalInterval(tt0, tt1))
        if owned is None or owned.lo >= tt1:
            continue
        fraction = _rn(_rn(owned - p(tt0)) / _rn(p(tt1) - p(tt0)))
        outputs.append(_rn(p(start) + _rn(fraction * _rn(p(end) - p(start)))))
        covered.append(owned)
    if not outputs:
        return None
    cursor = tt.lo
    for part in sorted(covered, key=lambda x: x.lo):
        if part.lo > cursor:
            break
        cursor = max(cursor, part.hi)
    if cursor < tt.hi or not upper_covered:
        raise NativeClockBoundsUnavailable("TT interval mixes EOP and model seeds")
    return RationalInterval(min(x.lo for x in outputs), max(x.hi for x in outputs))


def _seconds(reader, anchor, ut, max_days):
    """Hull raw/corrected seconds across represented EOP branches."""
    data = _j.EOPRegistry._ensure_loaded()
    if not data:
        raise NativeClockBoundsUnavailable("EOP boundaries unavailable")
    first = _j.EOPRegistry._segment_bounds(min(data), data)[0]
    last = _j.EOPRegistry._segment_bounds(max(data), data)[2]
    p = RationalInterval.point
    cuts = {first, last}
    keys = sorted(data)
    for lkey, rkey in zip(keys, keys[1:]):
        if rkey > lkey + 1:
            for cut in (_j.EOPRegistry._segment_bounds(lkey, data)[2],
                        _j.EOPRegistry._segment_bounds(rkey, data)[0]):
                if ut.lo < p(cut).lo <= ut.hi:
                    cuts.add(cut)
    if len(cuts) > 2 * max_days + 4:
        raise NativeClockBoundsUnavailable("inverse EOP seam budget exceeded")
    parts, left = [], ut.lo
    for cut in sorted(cuts):
        point = p(cut).lo
        if left < point <= ut.hi:
            before = p(math.nextafter(cut, -math.inf)).lo
            if left <= before:
                parts.append(RationalInterval(left, before))
            left = point
    if left <= ut.hi:
        parts.append(RationalInterval(left, ut.hi))
    raw_values, bound_values = [], []
    for part in parts:
        offset = part - p(anchor)
        if part.hi < first:
            result = bound_pre_eop_hpiers_taper_ut1_to_tt(reader, anchor, offset, max_days=max_days)
            raw_values.append(result.raw_delta_t_seconds)
            bound_values.append(result.bound_delta_t_seconds)
        elif part.lo >= last:
            result = bound_post_eop_future_taper_ut1_to_tt(reader, anchor, offset, max_days=max_days)
            raw_values.append(result.delta_t_seconds)
            bound_values.append(result.delta_t_seconds)
        else:
            try:
                result = bound_direct_eop_ut1_to_tt(reader, anchor, offset, max_days=max_days)
            except NativeClockBoundsUnavailable:
                result = bound_eop_gap_ut1_to_tt(reader, anchor, offset, max_days=max_days)
                raw_values.append(result.raw_delta_t_seconds)
                bound_values.append(result.bound_delta_t_seconds)
            else:
                raw_values.append(result.delta_t_seconds)
                bound_values.append(result.delta_t_seconds)
    return (RationalInterval(min(x.lo for x in raw_values), max(x.hi for x in raw_values)),
            RationalInterval(min(x.lo for x in bound_values), max(x.hi for x in bound_values)))


def _neutral_model_seconds(tt, max_days):
    """Bound the source's year-only initial seed inside annual/future models."""
    from ._eclipse_native_clock_bounds import _native_months_for_interval

    table = tuple(_j._DELTA_T_ANNUAL)
    if (len(table) < 2 or any(not math.isfinite(x) or not math.isfinite(v) for x, v in table)
            or any(a[0] >= b[0] for a, b in zip(table, table[1:]))):
        raise NativeClockBoundsUnavailable("invalid annual model table")
    boundary = _j._delta_t_observation_boundary()
    if not table[0][0] <= boundary.year <= table[-1][0]:
        raise NativeClockBoundsUnavailable("invalid annual model boundary")
    p = RationalInterval.point
    outputs = []
    for year in sorted({y for y, _ in _native_months_for_interval(tt, max_days=max_days)}):
        start, end = _j.julian_day(year, 1, 1), _j.julian_day(year + 1, 1, 1)
        part = tt.intersect(RationalInterval(start - 1, end + 1))
        if part is None:
            continue
        y = _rn(p(year) + _rn(_rn(part - p(start)) / _rn(p(end) - p(start))))
        bridge = _j._delta_t_hpiers_annual_bridge()
        if y.lo >= bridge[0][0] and y.hi < bridge[1][0]:
            segments = bridge
        elif y.lo >= table[0][0] and y.hi <= boundary.year:
            segments = table
        else:
            segments = None
        if segments is not None:
            for (x0, v0), (x1, v1) in zip(segments, segments[1:]):
                sub = y.intersect(RationalInterval(x0, x1))
                if sub is None:
                    continue
                fraction = _rn(_rn(sub - p(x0)) / _rn(p(x1) - p(x0)))
                outputs.append(_rn(p(v0) + _rn(fraction * _rn(p(v1) - p(v0)))))
        elif y.lo > boundary.year:
            from ._eclipse_future_clock_bounds import _future_seconds as future_seconds
            outputs.append(future_seconds(y, boundary.year, boundary.total))
        else:
            raise NativeClockBoundsUnavailable("internal-gap inverse seed crosses model branch")
    if not outputs:
        raise NativeClockBoundsUnavailable("internal-gap inverse seed unavailable")
    return RationalInterval(min(x.lo for x in outputs), max(x.hi for x in outputs))


def bound_cross_eop_tt_to_ut1(reader, anchor_jd, offset_days, *, max_days=32):
    """Enclose successful mixed EOP, taper and supported-gap iterations."""
    _guard()
    _require_future_sources()
    if type(reader) is not SpkReader:
        raise NativeClockBoundsUnavailable("a direct SPK reader is required")
    try:
        anchor, tt = _anchor_and_input(anchor_jd, offset_days, max_days)
        p = RationalInterval.point
        _snapshot_sources()
        data = _j.EOPRegistry._ensure_loaded()
        if not data:
            raise NativeClockBoundsUnavailable("EOP boundary unavailable")
        first_seg = _j.EOPRegistry._segment_bounds(min(data), data)
        last_seg = _j.EOPRegistry._segment_bounds(max(data), data)
        first_tt = first_seg[0] + first_seg[1] / 86400.0
        last_tt = last_seg[2] + last_seg[3] / 86400.0
        current = _eop_seed(tt, max_days)
        if current is None:
            if tt.hi < first_tt:
                raw, _ = _hpiers_seconds(reader, anchor, tt, max_days, model_only=True)
                seed = "hpiers_model"
            elif tt.lo >= last_tt:
                raw = _future_seconds(reader, anchor, tt, max_days, model_only=True)
                seed = "future_model"
            else:
                try:
                    raw = _neutral_model_seconds(tt, max_days)
                    seed = "neutral_gap_model"
                except NativeClockBoundsUnavailable:
                    raw, _ = _hpiers_seconds(reader, anchor, tt, max_days, model_only=True)
                    seed = "hpiers_gap_model"
            current = _rn(tt - _rn(raw / p(86400.0)))
            for _ in range(8):
                raw, _ = _seconds(reader, anchor, current, max_days)
                current = _rn(tt - _rn(raw / p(86400.0)))
        else:
            seed = "direct_eop"
        for _ in range(12):
            _, corrected = _seconds(reader, anchor, current, max_days)
            next_ut = _rn(tt - _rn(corrected / p(86400.0)))
            current = RationalInterval(min(current.lo, next_ut.lo), max(current.hi, next_ut.hi))
        return CrossEOPInverseBounds(anchor, offset_days, current - p(anchor), seed)
    except (CanonClockBoundsUnavailable, IntervalBudgetError, IntervalDomainError, OverflowError) as exc:
        raise NativeClockBoundsUnavailable("cross-EOP inverse arithmetic unavailable") from exc
