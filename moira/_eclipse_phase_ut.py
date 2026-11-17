"""Conditional UT1 composition of the private FW phase-sign enclosure.

Clock, kernel, source, arithmetic, libm and context premises remain unverified.
This does not establish a continuous root, a complete search, or a physical
eclipse, and is not used by the public eclipse selector.
"""
from __future__ import annotations

from dataclasses import dataclass

from ._eclipse_clock_provider import NativeClockProviderReceipt, bound_native_ut1_to_tt
from ._eclipse_interval import RationalInterval as I
from ._eclipse_phase_exclusion import ConditionalPhaseExclusion, bound_fw_phase_zero_exclusion


@dataclass(frozen=True, slots=True)
class ConditionalUtPhaseSigns:
    """Clock and phase receipts for all successful represented UT1 samples."""

    ut_anchor_jd: float
    ut_offset_days: I
    clock: NativeClockProviderReceipt
    phase: ConditionalPhaseExclusion
    same_reader_clock_data_and_context_required: bool = True
    source_and_arithmetic_attested: bool = False
    successful_outputs_only: bool = True
    coverage_success_guaranteed: bool = False
    continuous_root_proved: bool = False
    complete_search_certified: bool = False
    physical_accuracy_certified: bool = False


def bound_conditional_ut_phase_signs(
    reader, ut_anchor_jd: float, ut_offset_days: I, *, max_days: int = 32,
) -> ConditionalUtPhaseSigns:
    """Compose full-interval native clock and FW phase residual bounds.

    For successfully returned phase samples, the per-branch sign in the
    nested phase receipt applies throughout the UT input box if all premises
    in both receipts remain true. This bounds the default reader-bound clock;
    it does not substitute the NASA canon maximum's distinct clock policy.
    Unsupported handoffs, source branches and Vondrak dates fail closed.
    """
    clock = bound_native_ut1_to_tt(reader, ut_anchor_jd, ut_offset_days, max_days=max_days)
    phase = bound_fw_phase_zero_exclusion(reader, float(ut_anchor_jd), clock.bounds.output_offset_days)
    return ConditionalUtPhaseSigns(float(ut_anchor_jd), ut_offset_days, clock, phase)
