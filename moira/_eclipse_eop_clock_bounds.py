"""Conditional forward enclosure for completely covered direct EOP segments.

This encloses the existing reader-bound default clock only where the entire
input is covered by eligible EOP rows. Segment snapshots, code and arithmetic
must stay stable, including leap-second/TAI tables and all segment
dependencies; these premises are not attested. No handoff, source gap,
physical accuracy, inverse, or general future model is certified.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import julian as _j
from . import _ephemeris_time as _time
from ._eclipse_canon_clock_bounds import CanonClockBoundsUnavailable, _anchor_and_input
from ._eclipse_interval import IntervalBudgetError, IntervalDomainError, RationalInterval
from ._eclipse_native_clock_bounds import (
    NativeClockBoundsUnavailable, _require_sources, _rn, _snapshot_sources,
)
from .spk_reader import SpkReader


# Import-time guards detect later replacement; they are not provenance or
# execution-environment attestations. Table content and all called source
# dependencies must also stay unchanged throughout any conditional proof.
_DIRECT_FUNCTIONS = {
    name: getattr(_j, name)
    for name in ("_require_representable_time_jd", "_require_finite", "tai_minus_utc")
}
_UTC_MIDNIGHT = _j.EOPRegistry.__dict__["_utc_midnight"]
_RESOLVED_POST_INIT = _j._ResolvedDeltaT.__post_init__
_BOUND_POST_INIT = _time._BoundEphemerisDeltaT.__post_init__
_DIRECT_TIME_LIMIT = _j._MAX_ABS_TIME_JD


def _require_direct_totality_sources():
    """Reject changed source guards required for direct-EOP totality."""
    if (any(getattr(_j, name) is not fn for name, fn in _DIRECT_FUNCTIONS.items())
            or _j.EOPRegistry.__dict__["_utc_midnight"] is not _UTC_MIDNIGHT
            or _j._ResolvedDeltaT.__post_init__ is not _RESOLVED_POST_INIT
            or _time._BoundEphemerisDeltaT.__post_init__ is not _BOUND_POST_INIT
            or _j._MAX_ABS_TIME_JD != _DIRECT_TIME_LIMIT
            or _DIRECT_TIME_LIMIT != 40_000_000.0):
        raise NativeClockBoundsUnavailable("direct EOP totality source changed")


@dataclass(frozen=True, slots=True)
class DirectEOPClockBounds:
    """Conditional direct-EOP enclosure and optional totality evidence.

    The numerical enclosure is still stated over successful outputs. When
    ``forward_totality_conditionally_proved`` is true, a separate argument
    establishes that every represented input takes the direct-EOP branch and
    returns a finite TT value, provided the listed source and arithmetic
    premises hold unchanged. None of those premises is attested by this data.
    """
    anchor_jd: float
    input_offset_days: RationalInterval
    output_offset_days: RationalInterval
    possible_mjds: tuple[int, ...]
    delta_t_seconds: RationalInterval
    eop_sha256: str
    source_and_arithmetic_attested: bool = False
    successful_outputs_only: bool = True
    forward_totality_conditionally_proved: bool = False
    unchanged_eop_leap_and_source_dependencies_required: bool = True
    normal_binary64_arithmetic_required: bool = True
    inverse_enclosed: bool = False
    physical_delta_t_accuracy_certified: bool = False


def bound_direct_eop_ut1_to_tt(reader, anchor_jd, offset_days, *, max_days=32,
                               require_totality=False):
    """Enclose direct-EOP values and optionally prove conditional totality.

    Totality requires all represented UT1 inputs to be inside the source
    domain, a full cover by finite positive-span EOP segments searchable by
    the production lookup, and unchanged direct-EOP and clock dependencies.
    The EOP product has no tidal terms, so the production binding returns
    directly without ephemeris-identity lookup. This is not a physical clock,
    live-source, reader-image, or floating-point-environment attestation.
    """
    if type(require_totality) is not bool:
        raise ValueError("require_totality must be a bool")
    _require_sources()
    if require_totality:
        _require_direct_totality_sources()
    if type(reader) is not SpkReader:
        raise NativeClockBoundsUnavailable("a direct SPK reader is required")
    try:
        anchor, ut = _anchor_and_input(anchor_jd, offset_days, max_days)
        if require_totality and (ut.lo < -_j._MAX_ABS_TIME_JD or ut.hi > _j._MAX_ABS_TIME_JD):
            raise NativeClockBoundsUnavailable("UT1 interval outside source domain")
        _, _, digest, _ = _snapshot_sources()
        data = _j.EOPRegistry._ensure_loaded()
        # Approximate UTC-MJD and its neighboring-day search are binary64.
        # Two extra candidate days cover rounding near midnight.
        first = (ut.lo - RationalInterval.point(2400000.5).lo) // 1 - 2
        last = (ut.hi - RationalInterval.point(2400000.5).lo) // 1 + 2
        if last - first > max_days + 5:
            raise NativeClockBoundsUnavailable("EOP enumeration budget exceeded")
        intervals = []
        outputs = []
        second_ranges = []
        mjds = []
        upper_covered = False
        p = RationalInterval.point
        for mjd in range(first, last + 1):
            segment = _j.EOPRegistry._segment_bounds(mjd, data)
            if segment is None:
                continue
            start, dt0, end, dt1 = segment
            # This proves each overlapping epoch's lookup candidate includes
            # this row, even with day-boundary rounding in approximate_mjd.
            midnight = 2400000.5 + mjd
            if not (midnight - 0.01 < start < midnight + 0.01
                    and midnight + 0.99 < end < midnight + 1.01 and start < end):
                raise NativeClockBoundsUnavailable("unsupported EOP segment geometry")
            upper_covered |= start <= ut.hi < end
            owned = ut.intersect(RationalInterval(start, end))
            if owned is None:
                continue
            fraction = _rn(_rn(owned - p(start)) / _rn(p(end) - p(start)))
            seconds = _rn(p(dt0) + _rn(fraction * _rn(p(dt1) - p(dt0))))
            second_ranges.append(seconds)
            outputs.append(_rn(owned + _rn(seconds / p(86400.0))))
            intervals.append(owned)
            mjds.append(mjd)
        # Segment membership is half-open in the source. Requiring coverage
        # past the upper endpoint, including a following row at a join, avoids
        # treating an excluded terminal endpoint as observed EOP.
        cursor = ut.lo
        for owned in sorted(intervals, key=lambda x: x.lo):
            if owned.lo > cursor:
                break
            cursor = max(cursor, owned.hi)
        if not outputs or cursor < ut.hi or not upper_covered:
            raise NativeClockBoundsUnavailable("EOP segments do not fully cover interval")
        tt = RationalInterval(min(x.lo for x in outputs), max(x.hi for x in outputs))
        seconds_hull = RationalInterval(min(x.lo for x in second_ranges),
                                        max(x.hi for x in second_ranges))
        return DirectEOPClockBounds(anchor, offset_days, tt - p(anchor), tuple(mjds),
                                    seconds_hull, digest,
                                    forward_totality_conditionally_proved=require_totality)
    except (CanonClockBoundsUnavailable, IntervalBudgetError, IntervalDomainError, OverflowError) as exc:
        raise NativeClockBoundsUnavailable("EOP clock domain or arithmetic unavailable") from exc
