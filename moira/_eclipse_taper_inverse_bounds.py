"""Conditional native inverse for first/last EOP taper model branches."""
from __future__ import annotations

from dataclasses import dataclass

from . import _ephemeris_time as _time
from . import julian as _j
from ._eclipse_canon_clock_bounds import CanonClockBoundsUnavailable, _anchor_and_input
from ._eclipse_future_inverse_bounds import _seconds as _future_seconds
from ._eclipse_future_taper_bounds import bound_post_eop_future_taper_ut1_to_tt
from ._eclipse_historical_inverse_bounds import (
    _DELTA, _EOP_INVERSE, _FROM_JD, _GENERIC, _INVERSE, _YEAR, _hpiers_seconds,
)
from ._eclipse_historical_taper_bounds import bound_pre_eop_hpiers_taper_ut1_to_tt
from ._eclipse_interval import IntervalBudgetError, IntervalDomainError, RationalInterval
from ._eclipse_native_clock_bounds import NativeClockBoundsUnavailable, _require_sources, _rn
from .spk_reader import SpkReader


@dataclass(frozen=True, slots=True)
class TaperNativeInverseBounds:
    """Conditional inverse clock enclosure for an EOP taper."""
    anchor_jd: float
    input_offset_days: RationalInterval
    output_offset_days: RationalInterval
    source_and_arithmetic_attested: bool = False
    successful_outputs_only: bool = True
    inverse_uniqueness_certified: bool = False
    physical_delta_t_accuracy_certified: bool = False


def _guard():
    _require_sources()
    if (_time._ephemeris_tt_to_ut1 is not _INVERSE or _time.tt_to_ut is not _GENERIC
            or _j.tt_to_ut is not _GENERIC or _j._policy_year_from_jd is not _YEAR
            or _j.delta_t is not _DELTA or _j.delta_t_from_jd is not _FROM_JD
            or _j.EOPRegistry.__dict__["_ut1_from_tt"] is not _EOP_INVERSE):
        raise NativeClockBoundsUnavailable("native inverse source changed")


def _bound(reader, anchor_jd, offset_days, *, max_days, historical):
    _guard()
    if type(reader) is not SpkReader:
        raise NativeClockBoundsUnavailable("a direct SPK reader is required")
    try:
        anchor, tt = _anchor_and_input(anchor_jd, offset_days, max_days)
        p = RationalInterval.point
        data = _j.EOPRegistry._ensure_loaded()
        if not data:
            raise NativeClockBoundsUnavailable("taper requires EOP boundaries")
        if historical:
            if tt.hi >= p(2400000.5).lo + min(data) - 4:
                raise NativeClockBoundsUnavailable("initial inverse might use EOP")
            bound_pre_eop_hpiers_taper_ut1_to_tt(reader, anchor, tt - p(anchor), max_days=max_days)
            raw, _ = _hpiers_seconds(reader, anchor, tt, max_days, model_only=True)
        else:
            if tt.lo <= p(2400000.5).lo + max(data) + 4:
                raise NativeClockBoundsUnavailable("initial inverse might use EOP")
            bound_post_eop_future_taper_ut1_to_tt(reader, anchor, tt - p(anchor), max_days=max_days)
            raw = _future_seconds(reader, anchor, tt, max_days, model_only=True)
        current = _rn(tt - _rn(raw / p(86400.0)))
        for _ in range(8):
            if historical:
                receipt = bound_pre_eop_hpiers_taper_ut1_to_tt(
                    reader, anchor, current - p(anchor), max_days=max_days)
                seconds = receipt.raw_delta_t_seconds
            else:
                receipt = bound_post_eop_future_taper_ut1_to_tt(
                    reader, anchor, current - p(anchor), max_days=max_days)
                seconds = receipt.delta_t_seconds
            current = _rn(tt - _rn(seconds / p(86400.0)))
        for _ in range(12):
            if historical:
                receipt = bound_pre_eop_hpiers_taper_ut1_to_tt(
                    reader, anchor, current - p(anchor), max_days=max_days)
                seconds = receipt.bound_delta_t_seconds
            else:
                receipt = bound_post_eop_future_taper_ut1_to_tt(
                    reader, anchor, current - p(anchor), max_days=max_days)
                seconds = receipt.delta_t_seconds
            next_ut = _rn(tt - _rn(seconds / p(86400.0)))
            current = RationalInterval(min(current.lo, next_ut.lo), max(current.hi, next_ut.hi))
        return TaperNativeInverseBounds(anchor, offset_days, current - p(anchor))
    except (CanonClockBoundsUnavailable, IntervalBudgetError, IntervalDomainError, OverflowError) as exc:
        raise NativeClockBoundsUnavailable("taper inverse domain or arithmetic unavailable") from exc


def bound_pre_eop_taper_tt_to_ut1(reader, anchor_jd, offset_days, *, max_days=32):
    """Bound HPIERS taper inverse if the initial seed cannot use direct EOP."""
    return _bound(reader, anchor_jd, offset_days, max_days=max_days, historical=True)


def bound_post_eop_taper_tt_to_ut1(reader, anchor_jd, offset_days, *, max_days=32):
    """Bound neutral future taper inverse away from the EOP seed seam."""
    return _bound(reader, anchor_jd, offset_days, max_days=max_days, historical=False)
