"""Conditional ancient native clock polynomial and HPIERS bridge bounds.

The supported source branch is before HPIERS, with no EOP handoff. This
bounds successful represented outputs under unchanged source, reader identity,
and binary64/f-sum semantics; it is not a physical Delta-T uncertainty.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from . import julian as _j
from ._eclipse_canon_clock_bounds import (
    CanonClockBoundsUnavailable, _anchor_and_input,
)
from ._eclipse_interval import IntervalBudgetError, IntervalDomainError, RationalInterval
from ._eclipse_native_clock_bounds import (
    _native_months_for_interval as _months_for_interval,
    NativeClockBoundsUnavailable, _historical_year_output, _require_sources, _rn,
    _snapshot_sources,
)
from .spk_reader import SpkReader, _EphemerisKernelIdentity

_POLYNOMIAL_NDOT = _j._TIDAL_NDOT_POLYNOMIAL


@dataclass(frozen=True, slots=True)
class AncientNativeClockBounds:
    """Conditional enclosure for the ancient forward clock model."""
    anchor_jd: float
    input_offset_days: RationalInterval
    output_offset_days: RationalInterval
    possible_years: tuple[int, ...]
    identity: _EphemerisKernelIdentity
    table_sha256: str
    eop_sha256: str
    raw_delta_t_seconds: RationalInterval | None = None
    bound_delta_t_seconds: RationalInterval | None = None
    source_and_arithmetic_attested: bool = False
    successful_outputs_only: bool = True
    inverse_enclosed: bool = False
    physical_delta_t_accuracy_certified: bool = False


def _fsum_bounds(*values):
    """Enclose finite fsum with an extra ULP for double rounding.

    The smaller-magnitude neighbor at a binary power-of-two boundary is half
    the larger-binade ulp away, so widen by two representable steps.
    """
    result = _rn(sum(values, RationalInterval.point(0)))
    lo, hi = float(result.lo), float(result.hi)
    for _ in range(2):
        lo = math.nextafter(lo, -math.inf)
        hi = math.nextafter(hi, math.inf)
    if not math.isfinite(lo) or not math.isfinite(hi):
        raise NativeClockBoundsUnavailable("ancient fsum outside finite range")
    return RationalInterval(lo, hi)


def _correction(year, source, target):
    p = RationalInterval.point
    t = _rn(_rn(year - p(_j._TIDAL_REF_EPOCH)) / p(100.0))
    factor = _rn(p(-_j._TIDAL_CONVERSION) * _rn(p(target) - p(source)))
    return _rn(_rn(factor * t) * t)


def bound_ancient_native_ut1_to_tt(
    reader, anchor_jd, offset_days, *, max_days=32, _include_hpiers_seam=False,
):
    """Enclose successful pre-HPIERS default reader-bound clock outputs."""
    _require_sources()
    if _j._TIDAL_NDOT_POLYNOMIAL != _POLYNOMIAL_NDOT:
        raise NativeClockBoundsUnavailable("ancient clock source changed")
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
        years = tuple(sorted({y for y, _ in _months_for_interval(ut, max_days=max_days)}))
        table, table_digest, eop_digest, cutoff = _snapshot_sources()
        if cutoff is not None and ut.hi >= cutoff:
            raise NativeClockBoundsUnavailable("EOP handoff and later epochs are unsupported")
        p = RationalInterval.point
        hstart = table[0][0]
        bridge_start = hstart - 100.0
        # Prove the ancient polynomial and bridge precede every earlier source
        # branch in _resolve_delta_t; source switches otherwise need new bounds.
        if hstart != -2000.0 or bridge_start != -2100.0:
            raise NativeClockBoundsUnavailable("unsupported HPIERS source boundary")
        outputs = []
        raw_values = []
        bound_values = []
        for year in years:
            start, end = _j.julian_day(year, 1, 1), _j.julian_day(year + 1, 1, 1)
            part = ut.intersect(RationalInterval(start - 1, end + 1))
            if part is None:
                continue
            y = _rn(p(year) + _rn(_rn(part - p(start)) / _rn(p(end) - p(start))))
            if y.hi >= hstart:
                if not _include_hpiers_seam or y.lo < hstart - 2 or y.hi > hstart + 2:
                    raise NativeClockBoundsUnavailable("interval reaches HPIERS table branch")
                outputs.extend(_historical_year_output(part, year, table, target, partial=True))
                # A local import avoids a module cycle: the inverse helper uses
                # this module's tidal correction, while seam receipts need its
                # separately clipped HPIERS raw/corrected seconds.
                from ._eclipse_historical_inverse_bounds import _hpiers_seconds
                raw_hpiers, bound_hpiers = _hpiers_seconds(
                    reader, anchor, part, max_days, model_only=True, partial=True
                )
                raw_values.append(raw_hpiers)
                bound_values.append(bound_hpiers)
            pre = y.intersect(RationalInterval(-1000000, bridge_start))
            if pre is not None:
                u = _rn(_rn(pre - p(1820.0)) / p(100.0))
                total = _rn(p(-20.0) + _rn(_rn(p(32.0) * u) * u))
                correction = _rn(p(1.0) * _correction(pre, _POLYNOMIAL_NDOT, target))
                seconds = _rn(total + correction)
                raw_values.append(total)
                bound_values.append(seconds)
                outputs.append(_rn(part + _rn(seconds / p(86400.0))))
            bridge = y.intersect(RationalInterval(bridge_start, hstart))
            if bridge is not None:
                u0 = _rn(_rn(p(bridge_start) - p(1820.0)) / p(100.0))
                poly = _rn(p(-20.0) + _rn(_rn(p(32.0) * u0) * u0))
                fraction = _rn(_rn(bridge - p(bridge_start)) / _rn(p(hstart) - p(bridge_start)))
                total = _rn(poly + _rn(fraction * _rn(p(table[0][1]) - poly)))
                c1 = _rn(_rn(p(1.0) - fraction) * _correction(p(bridge_start), _POLYNOMIAL_NDOT, target))
                c2 = _rn(fraction * _correction(p(hstart), _j._TIDAL_NDOT_HPIERS, target))
                seconds = _rn(total + _fsum_bounds(c1, c2))
                raw_values.append(total)
                bound_values.append(seconds)
                outputs.append(_rn(part + _rn(seconds / p(86400.0))))
        if not outputs:
            raise NativeClockBoundsUnavailable("ancient source branch unavailable")
        tt = RationalInterval(min(x.lo for x in outputs), max(x.hi for x in outputs))
        raw_hull = RationalInterval(min(x.lo for x in raw_values), max(x.hi for x in raw_values))
        bound_hull = RationalInterval(min(x.lo for x in bound_values), max(x.hi for x in bound_values))
        return AncientNativeClockBounds(anchor, offset_days, tt - p(anchor), years,
                                        identity, table_digest, eop_digest, raw_hull, bound_hull)
    except (CanonClockBoundsUnavailable, IntervalBudgetError, IntervalDomainError, OverflowError) as exc:
        raise NativeClockBoundsUnavailable("ancient clock domain or arithmetic unavailable") from exc


def bound_ancient_hpiers_seam_ut1_to_tt(reader, anchor_jd, offset_days, *, max_days=32):
    """Hull both polynomial bridge and table evaluations around their seam."""
    return bound_ancient_native_ut1_to_tt(
        reader, anchor_jd, offset_days, max_days=max_days, _include_hpiers_seam=True
    )
