"""Conditional internal EOP gap enclosure for consistent source models."""
from __future__ import annotations

from dataclasses import dataclass
import math

from . import julian as _j
from ._eclipse_ancient_clock_bounds import _correction, _fsum_bounds
from ._eclipse_canon_clock_bounds import (
    CanonClockBoundsUnavailable, _anchor_and_input,
)
from ._eclipse_future_clock_bounds import _future_seconds, _require_future_sources
from ._eclipse_interval import IntervalBudgetError, IntervalDomainError, RationalInterval
from ._eclipse_native_clock_bounds import (
    _native_months_for_interval as _months_for_interval,
    NativeClockBoundsUnavailable, _require_sources, _rn, _snapshot_sources,
)
from .spk_reader import SpkReader, _EphemerisKernelIdentity


@dataclass(frozen=True, slots=True)
class EOPGapBounds:
    """Conditional forward clock enclosure within an internal EOP gap."""
    anchor_jd: float
    input_offset_days: RationalInterval
    output_offset_days: RationalInterval
    boundary_mjds: tuple[int, int]
    raw_delta_t_seconds: RationalInterval
    bound_delta_t_seconds: RationalInterval
    source_and_arithmetic_attested: bool = False
    successful_outputs_only: bool = True
    physical_delta_t_accuracy_certified: bool = False


def bound_eop_gap_ut1_to_tt(reader, anchor_jd, offset_days, *, max_days=32):
    """Bound one internal gap with supported base and source-owned boundary terms.

    Calendar, EOP/annual/future data, leap/TAI dependencies, source and
    arithmetic must be stable. These premises are not attested.
    """
    _require_sources()
    _require_future_sources()
    if type(reader) is not SpkReader:
        raise NativeClockBoundsUnavailable("a direct SPK reader is required")
    try:
        anchor, ut = _anchor_and_input(anchor_jd, offset_days, max_days)
        _snapshot_sources()
        data = _j.EOPRegistry._ensure_loaded()
        keys = sorted(data)
        if keys and 2400000.5 + keys[0] < _j._PRE_1972_UTC_START_JD:
            raise NativeClockBoundsUnavailable("EOP source predates admitted TAI-UTC coverage")
        if len(keys) < 2:
            raise NativeClockBoundsUnavailable("internal EOP gap unavailable")
        selected = None
        for left, right in zip(keys, keys[1:]):
            # Consecutive rows cannot have a source-level internal gap.
            if right <= left + 1:
                continue
            left_segment = _j.EOPRegistry._segment_bounds(left, data)
            right_segment = _j.EOPRegistry._segment_bounds(right, data)
            gap_start, left_dt = left_segment[2], left_segment[3]
            gap_end, right_dt = right_segment[0], right_segment[1]
            if gap_start <= ut.lo and ut.hi < gap_end:
                selected = left, right, gap_start, gap_end, left_dt, right_dt
                break
        if selected is None:
            raise NativeClockBoundsUnavailable("interval is not within one internal EOP gap")
        left, right, gap_start, gap_end, left_dt, right_dt = selected
        if not (2400000.5 + left + 0.99 < gap_start < 2400000.5 + left + 1.01
                and 2400000.5 + right - 0.01 < gap_end < 2400000.5 + right + 0.01):
            raise NativeClockBoundsUnavailable("unsupported internal EOP geometry")
        table = tuple(_j._DELTA_T_ANNUAL)
        if (len(table) < 2 or any(not math.isfinite(x) or not math.isfinite(v) for x, v in table)
                or any(a[0] >= b[0] for a, b in zip(table, table[1:]))):
            raise NativeClockBoundsUnavailable("invalid annual model table")
        boundary = _j._delta_t_observation_boundary()
        if not table[0][0] <= boundary.year <= table[-1][0]:
            raise NativeClockBoundsUnavailable("invalid annual model boundary")
        left_model = _j._resolve_delta_t(_j._continuous_decimal_year_from_jd(gap_start))
        right_model = _j._resolve_delta_t(_j._continuous_decimal_year_from_jd(gap_end))
        # Boundary products are fixed source snapshots. Carry every declared
        # tidal term separately with the source's interpolation coefficient.
        boundary_terms = (left_model.tidal_terms, right_model.tidal_terms)
        if any(len(terms) > 8 for terms in boundary_terms):
            raise NativeClockBoundsUnavailable("internal gap tidal term budget exceeded")
        target = None

        def require_target():
            identity = reader._kernel_identity
            if (not isinstance(identity, _EphemerisKernelIdentity)
                    or "_ephemeris_kernel_identity_at_tdb" in reader.__dict__):
                raise NativeClockBoundsUnavailable("reader tidal identity unavailable")
            value = identity.lunar_tidal_acceleration_arcsec_per_cy2
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
                raise NativeClockBoundsUnavailable("reader tidal basis unavailable")
            return value

        if any(boundary_terms):
            target = require_target()
        p = RationalInterval.point
        span = _rn(p(gap_end) - p(gap_start))
        fraction = _rn(_rn(ut - p(gap_start)) / span)
        # The source clamps this fraction, so hulling 0 and 1 is conservative
        # even if the interval extension slightly crosses an endpoint.
        fraction = RationalInterval(max(0, min(1, fraction.lo)), max(0, min(1, fraction.hi)))
        left_corr = _rn(p(left_dt) - p(left_model.seconds))
        right_corr = _rn(p(right_dt) - p(right_model.seconds))
        correction = _rn(left_corr + _rn(fraction * _rn(right_corr - left_corr)))
        outputs = []
        raw_ranges = []
        bound_ranges = []
        hpiers_table = _j._DELTA_T_HPIERS_2016
        for year in sorted({y for y, _ in _months_for_interval(ut, max_days=max_days)}):
            start, end = _j.julian_day(year, 1, 1), _j.julian_day(year + 1, 1, 1)
            part = ut.intersect(RationalInterval(start - 1, end + 1))
            if part is None:
                continue
            y = _rn(p(year) + _rn(_rn(part - p(start)) / _rn(p(end) - p(start))))
            bases = []
            historical = (y.lo >= hpiers_table[0][0]
                          and y.hi < _j._delta_t_hpiers_annual_bridge()[0][0])
            bridge = _j._delta_t_hpiers_annual_bridge()
            bridge_base = y.lo >= bridge[0][0] and y.hi < bridge[1][0]
            if historical:
                segments = hpiers_table
                if target is None:
                    target = require_target()
            elif bridge_base:
                segments = bridge
                if target is None:
                    target = require_target()
            elif y.lo >= table[0][0] and y.hi <= boundary.year:
                segments = table
            else:
                segments = None
            if segments is not None:
                for (x0, v0), (x1, v1) in zip(segments, segments[1:]):
                    sub = y.intersect(RationalInterval(x0, x1))
                    if sub is None:
                        continue
                    f = _rn(_rn(sub - p(x0)) / _rn(p(x1) - p(x0)))
                    bases.append((sub, _rn(p(v0) + _rn(f * _rn(p(v1) - p(v0)))), f))
            elif y.lo > boundary.year:
                bases.append((y, _future_seconds(y, boundary.year, boundary.total), None))
            else:
                raise NativeClockBoundsUnavailable("internal gap base crosses model boundary")
            for sub, base, base_fraction in bases:
                raw = _rn(base + correction)
                terms = []
                if historical:
                    terms.append(_rn(p(1.0) * _correction(sub, _j._TIDAL_NDOT_HPIERS, target)))
                elif bridge_base:
                    coefficient = _rn(p(1.0) - base_fraction)
                    terms.append(_rn(coefficient * _correction(
                        p(bridge[0][0]), _j._TIDAL_NDOT_HPIERS, target)))
                left_weight = -_rn(p(1.0) - fraction)
                for term in left_model.tidal_terms:
                    coefficient = _rn(p(term.coefficient) * left_weight)
                    terms.append(_rn(coefficient * _correction(
                        p(term.epoch_year), term.source_ndot, target)))
                for term in right_model.tidal_terms:
                    coefficient = _rn(p(term.coefficient) * -fraction)
                    terms.append(_rn(coefficient * _correction(
                        p(term.epoch_year), term.source_ndot, target)))
                seconds = _rn(raw + _fsum_bounds(*terms)) if terms else raw
                raw_ranges.append(raw)
                bound_ranges.append(seconds)
                outputs.append(_rn(part + _rn(seconds / p(86400.0))))
        if not outputs:
            raise NativeClockBoundsUnavailable("internal gap source unavailable")
        result = RationalInterval(min(x.lo for x in outputs), max(x.hi for x in outputs))
        raw_hull = RationalInterval(min(x.lo for x in raw_ranges), max(x.hi for x in raw_ranges))
        bound_hull = RationalInterval(min(x.lo for x in bound_ranges), max(x.hi for x in bound_ranges))
        return EOPGapBounds(anchor, offset_days, result - p(anchor), (left, right),
                                   raw_hull, bound_hull)
    except (CanonClockBoundsUnavailable, IntervalBudgetError, IntervalDomainError, OverflowError) as exc:
        raise NativeClockBoundsUnavailable("internal gap clock arithmetic unavailable") from exc
