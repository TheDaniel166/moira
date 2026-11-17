"""Fail-closed native inverse clock dispatch and branch ledger."""
from __future__ import annotations

from dataclasses import dataclass
import math

from . import julian as _j
from ._eclipse_canon_clock_bounds import _anchor_and_input
from ._eclipse_interval import RationalInterval

from ._eclipse_ancient_inverse_bounds import bound_ancient_native_tt_to_ut1
from ._eclipse_cross_eop_inverse_bounds import bound_cross_eop_tt_to_ut1
from ._eclipse_eop_inverse_bounds import bound_direct_eop_tt_to_ut1
from ._eclipse_future_inverse_bounds import bound_future_native_tt_to_ut1
from ._eclipse_historical_inverse_bounds import bound_historical_native_tt_to_ut1
from ._eclipse_native_clock_bounds import NativeClockBoundsUnavailable
from ._eclipse_taper_inverse_bounds import (
    bound_post_eop_taper_tt_to_ut1, bound_pre_eop_taper_tt_to_ut1,
)


@dataclass(frozen=True, slots=True)
class NativeInverseClockReceipt:
    """Record a candidate inverse clock route and its outcome."""
    branch: str
    bounds: object
    rejected_branches: tuple[tuple[str, str], ...]
    source_and_arithmetic_attested: bool = False
    physical_delta_t_accuracy_certified: bool = False


def _one_branch(reader, anchor_jd, offset_days, max_days):
    attempts = (
        ("direct_eop", bound_direct_eop_tt_to_ut1),
        ("historical_hpiers", bound_historical_native_tt_to_ut1),
        ("ancient_polynomial_or_bridge", bound_ancient_native_tt_to_ut1),
        ("future_scenario", bound_future_native_tt_to_ut1),
        ("pre_eop_taper", bound_pre_eop_taper_tt_to_ut1),
        ("post_eop_taper", bound_post_eop_taper_tt_to_ut1),
        ("cross_eop", bound_cross_eop_tt_to_ut1),
    )
    rejected = []
    for name, provider in attempts:
        try:
            result = provider(reader, anchor_jd, offset_days, max_days=max_days)
        except NativeClockBoundsUnavailable as exc:
            rejected.append((name, str(exc)))
        else:
            return NativeInverseClockReceipt(name, result, tuple(rejected))
    detail = "; ".join(f"{name}: {reason}" for name, reason in rejected)
    raise NativeClockBoundsUnavailable(f"no complete native inverse enclosure: {detail}")


@dataclass(frozen=True, slots=True)
class CompositeNativeInverseBounds:
    """Collect conditional inverse clock bounds and routing receipts."""
    anchor_jd: float
    input_offset_days: RationalInterval
    output_offset_days: RationalInterval
    segments: tuple[NativeInverseClockReceipt, ...]
    source_and_arithmetic_attested: bool = False
    successful_outputs_only: bool = True
    inverse_uniqueness_certified: bool = False
    physical_delta_t_accuracy_certified: bool = False


def bound_native_tt_to_ut1(reader, anchor_jd, offset_days, *, max_days=32):
    """Bound successful inverse outputs, splitting at EOP TT seed knots."""
    try:
        return _one_branch(reader, anchor_jd, offset_days, max_days)
    except NativeClockBoundsUnavailable as first_error:
        anchor, tt = _anchor_and_input(anchor_jd, offset_days, max_days)
        p = RationalInterval.point
        anchor_point = p(anchor)
        data = _j.EOPRegistry._ensure_loaded()
        if not data:
            raise first_error
        first = _j.EOPRegistry._segment_bounds(min(data), data)
        last = _j.EOPRegistry._segment_bounds(max(data), data)
        if first is None or last is None:
            raise first_error
        cuts = {first[0] + first[1] / 86400.0, last[2] + last[3] / 86400.0}
        keys = sorted(data)
        for lkey, rkey in zip(keys, keys[1:]):
            if rkey <= lkey + 1:
                continue
            ls = _j.EOPRegistry._segment_bounds(lkey, data)
            rs = _j.EOPRegistry._segment_bounds(rkey, data)
            for cut in (ls[2] + ls[3] / 86400.0, rs[0] + rs[1] / 86400.0):
                if tt.lo < p(cut).lo <= tt.hi:
                    cuts.add(cut)
        if len(cuts) > 2 * max_days + 4:
            raise NativeClockBoundsUnavailable("inverse TT seed seam budget exceeded")
        cuts = sorted(cuts)
        parts, left = [], tt.lo
        for cut in cuts:
            point = p(cut).lo
            if not left < point <= tt.hi:
                continue
            before = p(math.nextafter(cut, -math.inf)).lo
            if left <= before:
                parts.append(RationalInterval(left, before))
            left = point
        if left <= tt.hi:
            parts.append(RationalInterval(left, tt.hi))
        if len(parts) < 2:
            raise first_error
        receipts = tuple(_one_branch(reader, anchor, part - anchor_point, max_days) for part in parts)
        result = RationalInterval(min(r.bounds.output_offset_days.lo for r in receipts),
                                  max(r.bounds.output_offset_days.hi for r in receipts))
        bounds = CompositeNativeInverseBounds(anchor, offset_days, result, receipts)
        return NativeInverseClockReceipt("composite_eop", bounds,
                                         (("whole_interval", str(first_error)),))
