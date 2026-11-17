"""Conditional native inverse within the pre-EOP HPIERS clock branch.

It encloses the generic year-model seed, all eight generic fixed-point passes,
and all twelve possible reader-bound passes. Reader/source/EOP data and
binary64 arithmetic must stay stable; no premises or physical accuracy are
attested. Inputs and every intermediate must remain inside HPIERS coverage.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from . import _ephemeris_time as _time
from . import julian as _j
from ._eclipse_ancient_clock_bounds import _correction
from ._eclipse_canon_clock_bounds import (
    CanonClockBoundsUnavailable, _anchor_and_input,
)
from ._eclipse_interval import IntervalBudgetError, IntervalDomainError, RationalInterval
from ._eclipse_native_clock_bounds import (
    _native_months_for_interval as _months_for_interval,
    NativeClockBoundsUnavailable, _require_sources, _rn, _snapshot_sources,
    bound_historical_native_ut1_to_tt,
)
from .spk_reader import SpkReader, _EphemerisKernelIdentity

_INVERSE = _time._ephemeris_tt_to_ut1
_GENERIC = _j.tt_to_ut
_YEAR = _j._policy_year_from_jd
_DELTA = _j.delta_t
_FROM_JD = _j.delta_t_from_jd
_EOP_INVERSE = _j.EOPRegistry.__dict__["_ut1_from_tt"]


@dataclass(frozen=True, slots=True)
class HistoricalNativeInverseBounds:
    """Conditional inverse clock enclosure for the historical model."""
    anchor_jd: float
    input_offset_days: RationalInterval
    output_offset_days: RationalInterval
    source_and_arithmetic_attested: bool = False
    successful_outputs_only: bool = True
    inverse_uniqueness_certified: bool = False
    physical_delta_t_accuracy_certified: bool = False


def _hpiers_seconds(reader, anchor, interval, max_days, *, model_only=False, partial=False):
    """Enclose raw and reader-corrected seconds, with the forward guards."""
    p = RationalInterval.point
    if model_only:
        identity = reader._kernel_identity
        if not isinstance(identity, _EphemerisKernelIdentity):
            raise NativeClockBoundsUnavailable("reader identity unavailable")
        target = identity.lunar_tidal_acceleration_arcsec_per_cy2
        if not isinstance(target, (int, float)) or isinstance(target, bool) or not math.isfinite(target):
            raise NativeClockBoundsUnavailable("reader tidal basis unavailable")
    else:
        receipt = bound_historical_native_ut1_to_tt(reader, anchor, interval - p(anchor),
                                                     max_days=max_days)
        target = receipt.target_tidal_acceleration
    table, _, _, _ = _snapshot_sources()
    raw, corrected = [], []
    for year in sorted({y for y, _ in _months_for_interval(interval, max_days=max_days)}):
        start, end = _j.julian_day(year, 1, 1), _j.julian_day(year + 1, 1, 1)
        part = interval.intersect(RationalInterval(start - 1, end + 1))
        if part is None:
            continue
        y = _rn(p(year) + _rn(_rn(part - p(start)) / _rn(p(end) - p(start))))
        upper = min(_j._delta_t_hpiers_annual_bridge()[0][0], _j._DELTA_T_ANNUAL[0][0])
        if y.hi >= upper:
            raise NativeClockBoundsUnavailable("inverse leaves HPIERS model")
        if partial:
            y = y.intersect(RationalInterval(table[0][0], upper))
            if y is None:
                continue
        elif y.lo < table[0][0]:
            raise NativeClockBoundsUnavailable("inverse leaves HPIERS model")
        for (x0, v0), (x1, v1) in zip(table, table[1:]):
            sub = y.intersect(RationalInterval(x0, x1))
            if sub is None:
                continue
            f = _rn(_rn(sub - p(x0)) / _rn(p(x1) - p(x0)))
            base = _rn(p(v0) + _rn(f * _rn(p(v1) - p(v0))))
            corr = _rn(p(1.0) * _correction(sub, _j._TIDAL_NDOT_HPIERS, target))
            raw.append(base)
            corrected.append(_rn(base + corr))
    if not raw:
        raise NativeClockBoundsUnavailable("inverse HPIERS source unavailable")
    return (RationalInterval(min(x.lo for x in raw), max(x.hi for x in raw)),
            RationalInterval(min(x.lo for x in corrected), max(x.hi for x in corrected)))


def bound_historical_native_tt_to_ut1(reader, anchor_jd, offset_days, *, max_days=32):
    """Enclose successful scalar HPIERS inverse outputs under the stated premises."""
    _require_sources()
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
        # The initial EOP inverse searches approximate MJD -2 through +1.
        # Four days before the first row precludes any candidate even after
        # calendar subtraction rounding. Empty EOP also takes the model path.
        if data and tt.hi >= p(2400000.5).lo + min(data) - 4:
            raise NativeClockBoundsUnavailable("initial inverse might use EOP")
        raw, _ = _hpiers_seconds(reader, anchor, tt, max_days)
        current = _rn(tt - _rn(raw / p(86400.0)))
        for _ in range(8):
            raw, _ = _hpiers_seconds(reader, anchor, current, max_days)
            current = _rn(tt - _rn(raw / p(86400.0)))
        for _ in range(12):
            _, corrected = _hpiers_seconds(reader, anchor, current, max_days)
            next_ut = _rn(tt - _rn(corrected / p(86400.0)))
            current = RationalInterval(min(current.lo, next_ut.lo), max(current.hi, next_ut.hi))
        return HistoricalNativeInverseBounds(anchor, offset_days, current - p(anchor))
    except (CanonClockBoundsUnavailable, IntervalBudgetError, IntervalDomainError, OverflowError) as exc:
        raise NativeClockBoundsUnavailable("historical inverse domain or arithmetic unavailable") from exc
