"""Conditional first-EOP taper for an HPIERS-owned boundary and base.

Code, binary64 environment, EOP and HPIERS data, endpoint dependencies
including leap-second/TAI data, and reader identity must stay stable. These
premises are not attested; no physical Delta-T accuracy is claimed.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from . import julian as _j
from ._eclipse_ancient_clock_bounds import _correction, _fsum_bounds
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
class HistoricalTaperBounds:
    """Conditional enclosure for the pre-EOP forward clock taper."""
    anchor_jd: float
    input_offset_days: RationalInterval
    output_offset_days: RationalInterval
    eop_sha256: str
    raw_delta_t_seconds: RationalInterval
    bound_delta_t_seconds: RationalInterval
    source_and_arithmetic_attested: bool = False
    successful_outputs_only: bool = True
    physical_delta_t_accuracy_certified: bool = False


def bound_pre_eop_hpiers_taper_ut1_to_tt(reader, anchor_jd, offset_days, *, max_days=32):
    """Bound the first EOP taper when both source products are HPIERS."""
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
        table, _, digest, _ = _snapshot_sources()
        data = _j.EOPRegistry._ensure_loaded()
        if not data:
            raise NativeClockBoundsUnavailable("EOP boundary unavailable")
        mjd = min(data)
        segment = _j.EOPRegistry._segment_bounds(mjd, data)
        if segment is None:
            raise NativeClockBoundsUnavailable("first EOP segment unavailable")
        first, first_dt, _, _ = segment
        midnight = 2400000.5 + mjd
        if not midnight - 0.01 < first < midnight + 0.01:
            raise NativeClockBoundsUnavailable("unsupported first EOP geometry")
        window = _j._EOP_HANDOFF_WINDOW_DAYS
        p = RationalInterval.point
        if window <= 0 or ut.hi > p(first).lo:
            raise NativeClockBoundsUnavailable("interval leaves pre-EOP taper")
        boundary_y = _j._continuous_decimal_year_from_jd(first)
        model = _j._resolve_delta_t(boundary_y)
        if (model.source_product != "hpiers_de430_le430" or len(model.tidal_terms) != 1
                or model.tidal_terms[0].coefficient != 1.0
                or model.tidal_terms[0].source_ndot != _j._TIDAL_NDOT_HPIERS):
            raise NativeClockBoundsUnavailable("first EOP boundary is not HPIERS-owned")
        distance = _rn(p(first) - ut)
        if distance.lo >= window:
            weight = p(0.0)
        else:
            active = distance.intersect(RationalInterval(0, window))
            if active is None:
                raise NativeClockBoundsUnavailable("invalid taper distance")
            proximity = _rn(p(1.0) - _rn(active / p(window)))
            weight = _rn(_rn(proximity * proximity) * _rn(p(3.0) - _rn(p(2.0) * proximity)))
            if distance.hi >= window:
                weight = RationalInterval(min(weight.lo, 0), max(weight.hi, 0))
        correction = _rn(p(first_dt) - p(model.seconds))
        endpoint_corr = _correction(p(boundary_y), _j._TIDAL_NDOT_HPIERS, target)
        years = sorted({y for y, _ in _months_for_interval(ut, max_days=max_days)})
        outputs = []
        raw_values = []
        bound_values = []
        for year in years:
            start, end = _j.julian_day(year, 1, 1), _j.julian_day(year + 1, 1, 1)
            part = ut.intersect(RationalInterval(start - 1, end + 1))
            if part is None:
                continue
            y = _rn(p(year) + _rn(_rn(part - p(start)) / _rn(p(end) - p(start))))
            if y.lo < table[0][0] or y.hi >= min(_j._delta_t_hpiers_annual_bridge()[0][0],
                                                 _j._DELTA_T_ANNUAL[0][0]):
                raise NativeClockBoundsUnavailable("taper base is not HPIERS-owned")
            for (x0, v0), (x1, v1) in zip(table, table[1:]):
                sub = y.intersect(RationalInterval(x0, x1))
                if sub is None:
                    continue
                fraction = _rn(_rn(sub - p(x0)) / _rn(p(x1) - p(x0)))
                base = _rn(p(v0) + _rn(fraction * _rn(p(v1) - p(v0))))
                raw = _rn(base + _rn(correction * weight))
                base_corr = _rn(p(1.0) * _correction(sub, _j._TIDAL_NDOT_HPIERS, target))
                boundary_corr = _rn(_rn(p(1.0) * -weight) * endpoint_corr)
                seconds = _rn(raw + _fsum_bounds(base_corr, boundary_corr))
                raw_values.append(raw)
                bound_values.append(seconds)
                outputs.append(_rn(part + _rn(seconds / p(86400.0))))
        # The first UT1 knot is owned by the direct EOP branch, not the taper.
        if ut.contains(first):
            raw_values.append(p(first_dt))
            bound_values.append(p(first_dt))
            outputs.append(_rn(p(first) + _rn(p(first_dt) / p(86400.0))))
        if not outputs:
            raise NativeClockBoundsUnavailable("historical taper source unavailable")
        result = RationalInterval(min(x.lo for x in outputs), max(x.hi for x in outputs))
        raw_hull = RationalInterval(min(x.lo for x in raw_values), max(x.hi for x in raw_values))
        bound_hull = RationalInterval(min(x.lo for x in bound_values), max(x.hi for x in bound_values))
        return HistoricalTaperBounds(anchor, offset_days, result - p(anchor), digest,
                                     raw_hull, bound_hull)
    except (CanonClockBoundsUnavailable, IntervalBudgetError, IntervalDomainError, OverflowError) as exc:
        raise NativeClockBoundsUnavailable("historical taper domain or arithmetic unavailable") from exc
