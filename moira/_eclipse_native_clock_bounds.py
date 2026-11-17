"""Conditional bounds for the historical native reader-bound UT1 to TT clock.

Only direct SpkReader instances, the default clock policy, the HPIERS table
branch and dates before the first EOP handoff are enclosed. Source functions,
calendar, reader identity, table and EOP snapshot must remain unchanged while
used, and binary64 basic operations and single-term fsum must round normally.
Identity checks are guards, not attestations. The kernel identity is an
open-time observation, and table/EOP digests describe snapshots, not live-file
or physical attestations. This encloses successful scalar outputs only; it establishes neither SPK coverage nor physical Delta-T accuracy.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import struct

from . import _ephemeris_time as _time
from . import julian as _j
from ._eclipse_canon_clock_bounds import (
    CanonClockBoundsUnavailable, _anchor_and_input,
    _rounded_binary64_hull,
)
from ._eclipse_interval import IntervalBudgetError, IntervalDomainError, RationalInterval
from ._eclipse_interval_roots import EnclosureUnavailable
from .spk_reader import SpkReader, _EphemerisKernelIdentity


class NativeClockBoundsUnavailable(EnclosureUnavailable):
    """The default native clock cannot be enclosed under this contract."""


_FUNCTION_NAMES = (
    "julian_day", "calendar_from_jd", "_continuous_decimal_year_from_jd",
    "_resolve_delta_t_for_ut1", "_resolve_delta_t", "_interpolate_delta_t_table",
    "_delta_t_hpiers_annual_bridge", "_tidacc_correction", "_tidal_term",
    "_resolved_delta_t",
)
_FUNCTIONS = {name: getattr(_j, name) for name in _FUNCTION_NAMES}
_METHODS = {name: _j.EOPRegistry.__dict__[name] for name in (
    "_ensure_loaded", "_delta_t_from_ut1", "_model_delta_t_handoff_resolved",
    "_segment_bounds", "_ordered_mjds",
)}
_TIME_FUNCTIONS = {name: getattr(_time, name) for name in (
    "_ut1_to_ephemeris_tt", "_ephemeris_delta_t", "_reader_identity_at",
)}
_READER_METHOD = SpkReader._ephemeris_kernel_identity_at_tdb
_TABLE = _j._DELTA_T_HPIERS_2016
_CONSTANTS = (_j._TIDAL_CONVERSION, _j._TIDAL_REF_EPOCH,
              _j._TIDAL_NDOT_HPIERS, _j._EOP_HANDOFF_WINDOW_DAYS)


@dataclass(frozen=True, slots=True)
class HistoricalNativeClockBounds:
    """Conditional forward clock enclosure for the historical model."""
    anchor_jd: float
    input_offset_days: RationalInterval
    output_offset_days: RationalInterval
    possible_years: tuple[int, ...]
    identity: _EphemerisKernelIdentity
    target_tidal_acceleration: float
    table_sha256: str
    eop_sha256: str
    source_and_arithmetic_attested: bool = False
    successful_outputs_only: bool = True
    coverage_success_guaranteed: bool = False
    inverse_enclosed: bool = False
    physical_delta_t_accuracy_certified: bool = False


_NATIVE_FIRST_JD = _j.julian_day(-15000, 1, 1)
_NATIVE_END_JD = _j.julian_day(15001, 1, 1)


def _native_months_for_interval(interval, *, max_days):
    """Enumerate calendar ownership with seam guards in a finite wider domain.

    The unchanged Python/native calendar must depend on the rounded integer
    day in this range, and the same rounding environment must remain stable.
    """
    if interval.lo < _NATIVE_FIRST_JD + 2 or interval.hi > _NATIVE_END_JD - 2:
        raise NativeClockBoundsUnavailable("native clock calendar domain unavailable")
    half = RationalInterval.point(0.5).lo
    first = (interval.lo + half) // 1 - 1
    last = (interval.hi + half) // 1 + 1
    if last - first > max_days + 3:
        raise NativeClockBoundsUnavailable("calendar enumeration exceeds day budget")
    months = set()
    for day in range(first, last + 1):
        year, month, _, _ = _j.calendar_from_jd(float(day))
        if not -15000 <= year <= 15000 or not 1 <= month <= 12:
            raise NativeClockBoundsUnavailable("native calendar returned unsupported date")
        months.add((year, month))
    return tuple(sorted(months))


def _require_sources() -> None:
    if (any(getattr(_j, name) is not fn for name, fn in _FUNCTIONS.items())
            or any(_j.EOPRegistry.__dict__[name] is not fn for name, fn in _METHODS.items())
            or any(getattr(_time, name) is not fn for name, fn in _TIME_FUNCTIONS.items())
            or _time._resolve_delta_t_for_ut1 is not _FUNCTIONS["_resolve_delta_t_for_ut1"]
            or SpkReader._ephemeris_kernel_identity_at_tdb is not _READER_METHOD
            or _j._DELTA_T_HPIERS_2016 is not _TABLE
            or (_j._TIDAL_CONVERSION, _j._TIDAL_REF_EPOCH,
                _j._TIDAL_NDOT_HPIERS, _j._EOP_HANDOFF_WINDOW_DAYS) != _CONSTANTS):
        raise NativeClockBoundsUnavailable("native clock source changed")


def _snapshot_sources():
    table = tuple(_TABLE)
    if (len(table) < 2 or any(not math.isfinite(x) or not math.isfinite(y)
                               for x, y in table)
            or any(a[0] >= b[0] for a, b in zip(table, table[1:]))):
        raise NativeClockBoundsUnavailable("invalid HPIERS table")
    table_digest = hashlib.sha256(b"".join(struct.pack("<dd", *p) for p in table)).hexdigest()
    data = _j.EOPRegistry._ensure_loaded()
    if not isinstance(data, dict):
        raise NativeClockBoundsUnavailable("unsupported EOP source")
    items = list(data.items())
    if any(type(k) is not int or not isinstance(v, (int, float)) or isinstance(v, bool)
           or not math.isfinite(v) or abs(v) > 1 or not -(2**63) <= k < 2**63
           for k, v in items):
        raise NativeClockBoundsUnavailable("unsupported EOP source values")
    items.sort()
    window = _j._EOP_HANDOFF_WINDOW_DAYS
    if not isinstance(window, (int, float)) or not math.isfinite(window) or window < 0:
        raise NativeClockBoundsUnavailable("invalid EOP handoff window")
    digest = hashlib.sha256(b"".join(struct.pack("<qd", k, float(v)) for k, v in items)).hexdigest()
    cutoff = (None if not items else
              (RationalInterval.point(2400000.5) + items[0][0] - window - 2).lo)
    return table, table_digest, digest, cutoff


def _rn(x):
    return _rounded_binary64_hull(x)


def _historical_year_output(ut, year, table, target, *, partial=False):
    p = RationalInterval.point
    start, end = _j.julian_day(year, 1, 1), _j.julian_day(year + 1, 1, 1)
    # The adjacent-day guard encloses calendar rounding at the year boundary.
    ut = ut.intersect(RationalInterval(start - 1, end + 1))
    if ut is None:
        return []
    span = _rn(p(end) - p(start))
    y = _rn(p(year) + _rn(_rn(ut - p(start)) / span))
    bridge = _j._delta_t_hpiers_annual_bridge()[0][0]
    annual_start = _j._DELTA_T_ANNUAL[0][0]
    if partial:
        if y.hi >= min(bridge, annual_start):
            raise NativeClockBoundsUnavailable("interval leaves the HPIERS-only branch")
        y = y.intersect(RationalInterval(table[0][0], min(bridge, annual_start)))
        if y is None:
            return []
    elif y.lo < table[0][0] or y.hi >= min(bridge, annual_start):
        raise NativeClockBoundsUnavailable("interval leaves the HPIERS-only branch")
    outputs = []
    for (x0, v0), (x1, v1) in zip(table, table[1:]):
        segment = y.intersect(RationalInterval(x0, x1))
        if segment is None:
            continue
        fraction = _rn(_rn(segment - p(x0)) / _rn(p(x1) - p(x0)))
        base = _rn(p(v0) + _rn(fraction * _rn(p(v1) - p(v0))))
        t = _rn(_rn(segment - p(_j._TIDAL_REF_EPOCH)) / p(100.0))
        correction = _rn(p(-_j._TIDAL_CONVERSION)
                         * _rn(p(target) - p(_j._TIDAL_NDOT_HPIERS)))
        correction = _rn(_rn(correction * t) * t)
        correction = _rn(p(1.0) * correction)
        seconds = _rn(base + correction)
        outputs.append(_rn(ut + _rn(seconds / p(86400.0))))
    if not outputs:
        raise NativeClockBoundsUnavailable("no HPIERS segment selected")
    return outputs


def bound_historical_native_ut1_to_tt(reader, anchor_jd, offset_days, *, max_days=32):
    """Bound successful default-policy conversions, with no physical guarantee."""
    _require_sources()
    if type(reader) is not SpkReader or "_ephemeris_kernel_identity_at_tdb" in reader.__dict__:
        raise NativeClockBoundsUnavailable("a direct, unmodified SPK reader is required")
    identity = reader._kernel_identity
    if not isinstance(identity, _EphemerisKernelIdentity):
        raise NativeClockBoundsUnavailable("reader identity unavailable")
    target = identity.lunar_tidal_acceleration_arcsec_per_cy2
    if not isinstance(target, (int, float)) or isinstance(target, bool) or not math.isfinite(target):
        raise NativeClockBoundsUnavailable("reader tidal basis unavailable")
    try:
        anchor, ut = _anchor_and_input(anchor_jd, offset_days, max_days)
        years = tuple(sorted({y for y, _ in _native_months_for_interval(ut, max_days=max_days)}))
        table, table_digest, eop_digest, cutoff = _snapshot_sources()
        if cutoff is not None and ut.hi >= cutoff:
            raise NativeClockBoundsUnavailable("EOP handoff and later epochs are unsupported")
        outputs = [o for year in years for o in _historical_year_output(ut, year, table, target)]
        if not outputs:
            raise NativeClockBoundsUnavailable("no historical branch selected")
        tt = RationalInterval(min(x.lo for x in outputs), max(x.hi for x in outputs))
        return HistoricalNativeClockBounds(anchor, offset_days, tt - RationalInterval.point(anchor),
                                           years, identity, target, table_digest, eop_digest)
    except (CanonClockBoundsUnavailable, IntervalBudgetError, IntervalDomainError, OverflowError) as exc:
        raise NativeClockBoundsUnavailable("clock domain or arithmetic unavailable") from exc
