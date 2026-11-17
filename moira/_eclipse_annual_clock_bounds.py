"""Conditional HPIERS-to-annual bridge and annual clock without EOP data.

Source data, reader identity, calendar and binary64 operations must remain
stable. This does not attest data or physical Delta-T accuracy. Nonempty EOP
requires separate direct or handoff providers and is rejected here.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from . import julian as _j
from ._eclipse_ancient_clock_bounds import _correction
from ._eclipse_canon_clock_bounds import (
    CanonClockBoundsUnavailable, _anchor_and_input,
)
from ._eclipse_interval import IntervalBudgetError, IntervalDomainError, RationalInterval
from ._eclipse_native_clock_bounds import (
    _native_months_for_interval as _months_for_interval,
    NativeClockBoundsUnavailable, _require_sources, _rn, _snapshot_sources,
)
from .spk_reader import SpkReader, _EphemerisKernelIdentity


@dataclass(frozen=True, slots=True)
class AnnualClockBounds:
    """Conditional enclosure for annual-table clock evaluations."""
    anchor_jd: float
    input_offset_days: RationalInterval
    output_offset_days: RationalInterval
    source_and_arithmetic_attested: bool = False
    successful_outputs_only: bool = True
    physical_delta_t_accuracy_certified: bool = False


def bound_annual_no_eop_ut1_to_tt(reader, anchor_jd, offset_days, *, max_days=32):
    """Bound annual and HPIERS bridge branches if no EOP rows are present."""
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
        _snapshot_sources()
        if _j.EOPRegistry._ensure_loaded():
            raise NativeClockBoundsUnavailable("annual provider requires empty EOP data")
        table = tuple(_j._DELTA_T_ANNUAL)
        if (len(table) < 2 or any(not math.isfinite(x) or not math.isfinite(v) for x, v in table)
                or any(a[0] >= b[0] for a, b in zip(table, table[1:]))):
            raise NativeClockBoundsUnavailable("invalid annual table")
        bridge = _j._delta_t_hpiers_annual_bridge()
        if len(bridge) != 2 or bridge[1] != table[0] or bridge[0][0] >= bridge[1][0]:
            raise NativeClockBoundsUnavailable("invalid annual bridge")
        boundary = _j._delta_t_observation_boundary()
        if not table[0][0] <= boundary.year <= table[-1][0]:
            raise NativeClockBoundsUnavailable("invalid annual observation boundary")
        p = RationalInterval.point
        outputs = []
        for year in sorted({y for y, _ in _months_for_interval(ut, max_days=max_days)}):
            start, end = _j.julian_day(year, 1, 1), _j.julian_day(year + 1, 1, 1)
            part = ut.intersect(RationalInterval(start - 1, end + 1))
            if part is None:
                continue
            y = _rn(p(year) + _rn(_rn(part - p(start)) / _rn(p(end) - p(start))))
            if y.lo < bridge[0][0] or y.hi > boundary.year:
                raise NativeClockBoundsUnavailable("interval leaves annual and bridge branches")
            for (x0, v0), (x1, v1), is_bridge in [(*bridge, True), *(
                (a, b, False) for a, b in zip(table, table[1:])
            )]:
                sub = y.intersect(RationalInterval(x0, x1))
                if sub is None:
                    continue
                fraction = _rn(_rn(sub - p(x0)) / _rn(p(x1) - p(x0)))
                base = _rn(p(v0) + _rn(fraction * _rn(p(v1) - p(v0))))
                if is_bridge:
                    coefficient = _rn(p(1.0) - fraction)
                    correction = _rn(coefficient * _correction(p(x0), _j._TIDAL_NDOT_HPIERS, target))
                    seconds = _rn(base + correction)
                else:
                    seconds = base
                outputs.append(_rn(part + _rn(seconds / p(86400.0))))
        if not outputs:
            raise NativeClockBoundsUnavailable("annual source branch unavailable")
        tt = RationalInterval(min(x.lo for x in outputs), max(x.hi for x in outputs))
        return AnnualClockBounds(anchor, offset_days, tt - p(anchor))
    except (CanonClockBoundsUnavailable, IntervalBudgetError, IntervalDomainError, OverflowError) as exc:
        raise NativeClockBoundsUnavailable("annual clock domain or arithmetic unavailable") from exc
