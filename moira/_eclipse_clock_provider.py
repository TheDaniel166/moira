"""Fail-closed dispatch and proof ledger for native forward clock enclosures.

Each selected provider must individually cover the complete requested input.
A provider rejection does not establish absence or permit silently mixing
partially covered clock branches. See ECLIPSE_CLOCK_BOUNDS.md for premises.
"""
from __future__ import annotations

from dataclasses import dataclass
import math

from . import julian as _j
from ._eclipse_interval import RationalInterval
from ._eclipse_canon_clock_bounds import _anchor_and_input

from ._eclipse_annual_clock_bounds import bound_annual_no_eop_ut1_to_tt
from ._eclipse_ancient_clock_bounds import (
    bound_ancient_hpiers_seam_ut1_to_tt, bound_ancient_native_ut1_to_tt,
)
from ._eclipse_eop_clock_bounds import bound_direct_eop_ut1_to_tt
from ._eclipse_eop_gap_bounds import bound_eop_gap_ut1_to_tt
from ._eclipse_future_clock_bounds import bound_future_native_ut1_to_tt
from ._eclipse_future_taper_bounds import bound_post_eop_future_taper_ut1_to_tt
from ._eclipse_historical_taper_bounds import bound_pre_eop_hpiers_taper_ut1_to_tt
from ._eclipse_native_clock_bounds import (
    NativeClockBoundsUnavailable, bound_historical_native_ut1_to_tt,
)


@dataclass(frozen=True, slots=True)
class NativeClockProviderReceipt:
    """Record a candidate forward clock route and its outcome."""
    branch: str
    bounds: object
    rejected_branches: tuple[tuple[str, str], ...]
    source_and_arithmetic_attested: bool = False
    physical_delta_t_accuracy_certified: bool = False


def _one_branch(reader, anchor_jd, offset_days, max_days):
    attempts = (
        ("direct_eop", bound_direct_eop_ut1_to_tt),
        ("annual_no_eop", bound_annual_no_eop_ut1_to_tt),
        ("historical_hpiers", bound_historical_native_ut1_to_tt),
        ("ancient_polynomial_or_bridge", bound_ancient_native_ut1_to_tt),
        ("ancient_hpiers_seam", bound_ancient_hpiers_seam_ut1_to_tt),
        ("future_scenario", bound_future_native_ut1_to_tt),
        ("post_eop_future_taper", bound_post_eop_future_taper_ut1_to_tt),
        ("pre_eop_hpiers_taper", bound_pre_eop_hpiers_taper_ut1_to_tt),
        ("eop_gap", bound_eop_gap_ut1_to_tt),
    )
    rejected = []
    for name, provider in attempts:
        try:
            bounds = provider(reader, anchor_jd, offset_days, max_days=max_days)
        except NativeClockBoundsUnavailable as exc:
            rejected.append((name, str(exc)))
        else:
            return NativeClockProviderReceipt(name, bounds, tuple(rejected))
    detail = "; ".join(f"{name}: {reason}" for name, reason in rejected)
    raise NativeClockBoundsUnavailable(f"no complete native clock enclosure: {detail}")


@dataclass(frozen=True, slots=True)
class CompositeNativeClockBounds:
    """Collect conditional forward clock bounds and routing receipts."""
    anchor_jd: float
    input_offset_days: RationalInterval
    output_offset_days: RationalInterval
    segments: tuple[NativeClockProviderReceipt, ...]
    source_and_arithmetic_attested: bool = False
    successful_outputs_only: bool = True
    physical_delta_t_accuracy_certified: bool = False


def bound_native_ut1_to_tt(reader, anchor_jd, offset_days, *, max_days=32,
                           require_totality=False):
    """Enclose one branch or compose across represented EOP seams.

    Adjacent float cuts leave no represented binary64 input between pieces.
    No unsupported internal gap is silently accepted. The opt-in conditional
    totality proof currently admits only a directly covered EOP interval;
    other clock branches fail closed instead of inheriting that proof.
    """
    if type(require_totality) is not bool:
        raise ValueError("require_totality must be a bool")
    if require_totality:
        bounds = bound_direct_eop_ut1_to_tt(
            reader, anchor_jd, offset_days, max_days=max_days,
            require_totality=True,
        )
        return NativeClockProviderReceipt("direct_eop", bounds, ())
    try:
        return _one_branch(reader, anchor_jd, offset_days, max_days)
    except NativeClockBoundsUnavailable as first_error:
        if not isinstance(offset_days, RationalInterval) or not isinstance(anchor_jd, (int, float)):
            raise
        normalized_anchor, ut = _anchor_and_input(anchor_jd, offset_days, max_days)
        anchor = RationalInterval.point(normalized_anchor)
        data = _j.EOPRegistry._ensure_loaded()
        if not data:
            raise first_error
        first = _j.EOPRegistry._segment_bounds(min(data), data)
        last = _j.EOPRegistry._segment_bounds(max(data), data)
        if first is None or last is None:
            raise first_error
        cuts = {first[0], last[2]}
        keys = sorted(data)
        for left_mjd, right_mjd in zip(keys, keys[1:]):
            if right_mjd <= left_mjd + 1:
                continue
            left_segment = _j.EOPRegistry._segment_bounds(left_mjd, data)
            right_segment = _j.EOPRegistry._segment_bounds(right_mjd, data)
            if left_segment is None or right_segment is None:
                raise first_error
            for cut in (left_segment[2], right_segment[0]):
                if ut.lo < RationalInterval.point(cut).lo <= ut.hi:
                    cuts.add(cut)
        if len(cuts) > 2 * max_days + 4:
            raise NativeClockBoundsUnavailable("clock seam composition budget exceeded")
        cuts = sorted(cuts)
        parts = []
        left = ut.lo
        for cut in cuts:
            point = RationalInterval.point(cut).lo
            if not left < point <= ut.hi:
                continue
            before = RationalInterval.point(math.nextafter(cut, -math.inf)).lo
            if left <= before:
                parts.append(RationalInterval(left, before))
            left = point
        if left <= ut.hi:
            parts.append(RationalInterval(left, ut.hi))
        if len(parts) < 2:
            raise first_error
        receipts = tuple(_one_branch(reader, anchor_jd, part - anchor, max_days) for part in parts)
        result = RationalInterval(min(r.bounds.output_offset_days.lo for r in receipts),
                                  max(r.bounds.output_offset_days.hi for r in receipts))
        composite = CompositeNativeClockBounds(normalized_anchor, offset_days, result, receipts)
        return NativeClockProviderReceipt("composite_eop", composite,
                                          (("whole_interval", str(first_error)),))
