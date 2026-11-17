"""Conditional native inverse of the ancient polynomial/HPIERS bridge."""
from __future__ import annotations

from dataclasses import dataclass

from . import julian as _j
from ._eclipse_ancient_clock_bounds import bound_ancient_native_ut1_to_tt
from ._eclipse_canon_clock_bounds import CanonClockBoundsUnavailable, _anchor_and_input
from ._eclipse_interval import IntervalBudgetError, IntervalDomainError, RationalInterval
from ._eclipse_native_clock_bounds import NativeClockBoundsUnavailable, _rn
from ._eclipse_taper_inverse_bounds import _guard
from .spk_reader import SpkReader


@dataclass(frozen=True, slots=True)
class AncientNativeInverseBounds:
    """Conditional enclosure for ancient inverse clock evaluations."""
    anchor_jd: float
    input_offset_days: RationalInterval
    output_offset_days: RationalInterval
    source_and_arithmetic_attested: bool = False
    successful_outputs_only: bool = True
    inverse_uniqueness_certified: bool = False
    physical_delta_t_accuracy_certified: bool = False


def bound_ancient_native_tt_to_ut1(reader, anchor_jd, offset_days, *, max_days=32):
    """Enclose generic and reader-bound ancient inverse passes, conditionally."""
    _guard()
    if type(reader) is not SpkReader:
        raise NativeClockBoundsUnavailable("a direct SPK reader is required")
    try:
        anchor, tt = _anchor_and_input(anchor_jd, offset_days, max_days)
        p = RationalInterval.point
        data = _j.EOPRegistry._ensure_loaded()
        if data and tt.hi >= p(2400000.5).lo + min(data) - 4:
            raise NativeClockBoundsUnavailable("initial inverse might use EOP")
        receipt = bound_ancient_native_ut1_to_tt(reader, anchor, tt - p(anchor), max_days=max_days,
                                                     _include_hpiers_seam=True)
        current = _rn(tt - _rn(receipt.raw_delta_t_seconds / p(86400.0)))
        for _ in range(8):
            receipt = bound_ancient_native_ut1_to_tt(reader, anchor, current - p(anchor),
                                                      max_days=max_days, _include_hpiers_seam=True)
            current = _rn(tt - _rn(receipt.raw_delta_t_seconds / p(86400.0)))
        for _ in range(12):
            receipt = bound_ancient_native_ut1_to_tt(reader, anchor, current - p(anchor),
                                                      max_days=max_days, _include_hpiers_seam=True)
            next_ut = _rn(tt - _rn(receipt.bound_delta_t_seconds / p(86400.0)))
            current = RationalInterval(min(current.lo, next_ut.lo), max(current.hi, next_ut.hi))
        return AncientNativeInverseBounds(anchor, offset_days, current - p(anchor))
    except (CanonClockBoundsUnavailable, IntervalBudgetError, IntervalDomainError, OverflowError) as exc:
        raise NativeClockBoundsUnavailable("ancient inverse domain or arithmetic unavailable") from exc
