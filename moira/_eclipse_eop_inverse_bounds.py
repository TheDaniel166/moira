"""Conditional native TT-to-UT1 enclosure wholly within direct EOP coverage.

The source's EOP inverse seeds are enclosed, then each of its up to twelve
reader-bound iterations is enclosed. Any unsupported initial TT segment or
intermediate UT interval fails closed. No existence, uniqueness, or physical
uncertainty is established. Source and arithmetic premises are not attested.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import _ephemeris_time as _time
from . import julian as _j
from ._eclipse_canon_clock_bounds import CanonClockBoundsUnavailable, _anchor_and_input
from ._eclipse_eop_clock_bounds import bound_direct_eop_ut1_to_tt
from ._eclipse_interval import IntervalBudgetError, IntervalDomainError, RationalInterval
from ._eclipse_native_clock_bounds import NativeClockBoundsUnavailable, _require_sources, _rn, _snapshot_sources
from .spk_reader import SpkReader

_INVERSE = _time._ephemeris_tt_to_ut1
_GENERIC = _j.tt_to_ut
_EOP_INVERSE = _j.EOPRegistry.__dict__["_ut1_from_tt"]


@dataclass(frozen=True, slots=True)
class DirectEOPInverseBounds:
    """Conditional inverse clock enclosure within direct EOP coverage."""
    anchor_jd: float
    input_offset_days: RationalInterval
    output_offset_days: RationalInterval
    source_and_arithmetic_attested: bool = False
    successful_outputs_only: bool = True
    inverse_uniqueness_certified: bool = False
    physical_delta_t_accuracy_certified: bool = False


def _hull(a, b):
    return RationalInterval(min(a.lo, b.lo), max(a.hi, b.hi))


def bound_direct_eop_tt_to_ut1(reader, anchor_jd, offset_days, *, max_days=32):
    """Enclose successful scalar inverse outputs if all iterations stay in EOP."""
    _require_sources()
    if (_time._ephemeris_tt_to_ut1 is not _INVERSE or _time.tt_to_ut is not _GENERIC
            or _j.tt_to_ut is not _GENERIC
            or _j.EOPRegistry.__dict__["_ut1_from_tt"] is not _EOP_INVERSE):
        raise NativeClockBoundsUnavailable("native inverse source changed")
    if type(reader) is not SpkReader:
        raise NativeClockBoundsUnavailable("a direct SPK reader is required")
    try:
        anchor, tt = _anchor_and_input(anchor_jd, offset_days, max_days)
        p = RationalInterval.point
        _snapshot_sources()
        data = _j.EOPRegistry._ensure_loaded()
        first = (tt.lo - p(2400000.5).lo) // 1 - 2
        last = (tt.hi - p(2400000.5).lo) // 1 + 2
        if last - first > max_days + 5:
            raise NativeClockBoundsUnavailable("EOP inverse enumeration budget exceeded")
        covered, outputs, upper_covered = [], [], False
        for mjd in range(first, last + 1):
            seg = _j.EOPRegistry._segment_bounds(mjd, data)
            if seg is None:
                continue
            start, dt0, end, dt1 = seg
            # These are exactly the scalar code's represented TT endpoints.
            tt0 = start + dt0 / 86400.0
            tt1 = end + dt1 / 86400.0
            midnight = 2400000.5 + mjd
            if not (midnight - 0.01 < tt0 < midnight + 0.01
                    and midnight + 0.99 < tt1 < midnight + 1.01 and tt0 < tt1):
                raise NativeClockBoundsUnavailable("unsupported EOP inverse segment geometry")
            upper_covered |= tt0 <= tt.hi < tt1
            owned = tt.intersect(RationalInterval(tt0, tt1))
            if owned is None:
                continue
            fraction = _rn(_rn(owned - p(tt0)) / _rn(p(tt1) - p(tt0)))
            outputs.append(_rn(p(start) + _rn(fraction * _rn(p(end) - p(start)))))
            covered.append(owned)
        cursor = tt.lo
        for owned in sorted(covered, key=lambda x: x.lo):
            if owned.lo > cursor:
                break
            cursor = max(cursor, owned.hi)
        if not outputs or cursor < tt.hi or not upper_covered:
            raise NativeClockBoundsUnavailable("EOP inverse segments do not fully cover TT")
        current = RationalInterval(min(x.lo for x in outputs), max(x.hi for x in outputs))
        # Keep every earlier iterate: equality can terminate the loop at any
        # step, and the returned value is the current (not next) iterate.
        for _ in range(12):
            seconds = bound_direct_eop_ut1_to_tt(
                reader, anchor, current - p(anchor), max_days=max_days
            ).delta_t_seconds
            next_ut = _rn(tt - _rn(seconds / p(86400.0)))
            current = _hull(current, next_ut)
        # The source's final recovered-TT check can only reject outcomes.
        return DirectEOPInverseBounds(anchor, offset_days, current - p(anchor))
    except (CanonClockBoundsUnavailable, IntervalBudgetError, IntervalDomainError, OverflowError) as exc:
        raise NativeClockBoundsUnavailable("EOP inverse domain or arithmetic unavailable") from exc
