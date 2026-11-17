"""Conditional native UT1 clock plus strict mean-phase interval policy.

The native clock's own source and floating-point premises remain unverified.
The phase policy uses copied SPK snapshots and mathematical strict trig; it
does not attest the legacy apparent evaluator or physical eclipse search.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import math

from ._eclipse_clock_provider import NativeClockProviderReceipt, bound_native_ut1_to_tt
from ._eclipse_interval import RationalInterval as I
from ._eclipse_strict_phase import StrictMeanPhaseSample
from ._eclipse_strict_phase_bounds import (
    ConditionalStrictMeanDomain, bound_strict_mean_phase_interval, evaluate_bounded_strict_mean_phase,
)
from ._ephemeris_time import _ut1_to_ephemeris_tt


@dataclass(frozen=True, slots=True)
class ConditionalStrictUtDomain:
    """A native clock receipt and strict TT phase box for the same reader."""

    ut_anchor_jd: float
    ut_offset_days: I
    clock: NativeClockProviderReceipt
    phase: ConditionalStrictMeanDomain
    reader: object = field(repr=False, compare=False)
    unchanged_clock_source_data_and_reader_required: bool = True
    source_and_arithmetic_attested: bool = False
    successful_outputs_only: bool = True
    continuous_root_proved: bool = False
    complete_search_certified: bool = False
    physical_accuracy_certified: bool = False


def bound_strict_ut_phase_interval(
    reader, ut_anchor_jd: float, ut_offset_days: I, *, max_days: int = 32,
) -> ConditionalStrictUtDomain:
    """Compose successful native UT→TT outputs with the strict TT domain."""
    clock = bound_native_ut1_to_tt(reader, ut_anchor_jd, ut_offset_days, max_days=max_days)
    phase = bound_strict_mean_phase_interval(reader, float(ut_anchor_jd), clock.bounds.output_offset_days)
    return ConditionalStrictUtDomain(float(ut_anchor_jd), ut_offset_days, clock, phase, reader)


def evaluate_bounded_strict_ut_phase(bounds: ConditionalStrictUtDomain, ut_jd: float) -> StrictMeanPhaseSample:
    """Evaluate one actual reader-clock TT and check the strict phase box."""
    if not isinstance(bounds, ConditionalStrictUtDomain):
        raise TypeError("conditional strict UT phase domain required")
    if isinstance(ut_jd, bool) or not isinstance(ut_jd, (int, float)) or not math.isfinite(ut_jd):
        raise ValueError("finite UT sample required")
    ut = float(ut_jd)
    if not bounds.ut_offset_days.contains(Fraction.from_float(ut) - Fraction.from_float(bounds.ut_anchor_jd)):
        raise ValueError("UT sample lies outside the bounded input interval")
    tt = _ut1_to_ephemeris_tt(ut, bounds.reader)
    relative_tt = Fraction.from_float(tt) - Fraction.from_float(bounds.ut_anchor_jd)
    if not bounds.clock.bounds.output_offset_days.contains(relative_tt):
        raise ArithmeticError("reader clock sample escaped its conditional TT box")
    return evaluate_bounded_strict_mean_phase(bounds.phase, tt)
