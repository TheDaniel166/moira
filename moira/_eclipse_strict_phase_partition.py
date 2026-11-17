"""Conditional represented-input partitions of the strict mean-phase route.

The underlying enclosures constrain successful outputs only, and require
their documented source, kernel, arithmetic and native-build premises. These
partitions do not establish that all inputs evaluate or that real-time phase
is continuous; they are neither event counts nor physical eclipse searches.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import math
from typing import Literal

from ._eclipse_float_sign_partition import RepresentableSignPartition, partition_representable_signs
from ._eclipse_interval import RationalInterval
from ._eclipse_strict_phase_bounds import bound_strict_mean_phase_interval
from ._eclipse_strict_phase_ut import bound_strict_ut_phase_interval


@dataclass(frozen=True)
class ConditionalStrictPhasePartition:
    """Strict phase signs for successful evaluations, conditional on premises.

    Sign cells cover the requested represented inputs, not an attested set of
    successful outputs. Receipts from the underlying bound are not retained;
    this object alone does not attest the source, kernel or loaded binary.
    """

    phase: Literal["new", "full"]
    time_scale: Literal["TT", "UT1"]
    partition: RepresentableSignPartition
    successful_outputs_only: bool = True
    source_and_loaded_native_image_attested: bool = False
    legacy_phase_evaluator_attested: bool = False
    continuous_root_proved: bool = False
    complete_search_certified: bool = False
    physical_accuracy_certified: bool = False


def partition_strict_phase_signs(
    reader,
    first_jd: float,
    last_jd: float,
    *,
    phase: Literal["new", "full"],
    time_scale: Literal["TT", "UT1"],
    max_evaluations: int,
    max_depth: int = 64,
    max_unresolved_width_days: float = 0.0,
    max_ut_days: int = 32,
) -> ConditionalStrictPhasePartition:
    """Conditionally partition represented positive Julian dates by phase sign.

    TT uses the strict mean-ecliptic phase route. UT1 composes it with the
    conditional native reader clock; that does not validate physical Delta T.
    ``None`` signs and unsupported domains remain unresolved and may split.
    The represented-input coverage does not prove evaluation totality.
    """
    if phase not in ("new", "full"):
        raise ValueError("phase must be 'new' or 'full'")
    if time_scale not in ("TT", "UT1"):
        raise ValueError("time_scale must be 'TT' or 'UT1'")
    if any(isinstance(x, bool) or not isinstance(x, float) or not math.isfinite(x) or x <= 0
           for x in (first_jd, last_jd)):
        raise ValueError("positive finite binary64 Julian-date endpoints required")

    def enclosure(first: float, last: float):
        offset = RationalInterval(Fraction(0), Fraction.from_float(last) - Fraction.from_float(first))
        if time_scale == "TT":
            domain = bound_strict_mean_phase_interval(reader, first, offset)
        else:
            domain = bound_strict_ut_phase_interval(reader, first, offset, max_days=max_ut_days).phase
        sign = domain.new_direction_sign if phase == "new" else domain.full_direction_sign
        if sign is None:
            return None
        if type(sign) is not int or sign not in (-1, 1):
            raise ValueError("strict phase provider returned an invalid direction sign")
        return "positive" if sign == 1 else "negative"

    partition = partition_representable_signs(
        first_jd, last_jd, enclosure,
        max_evaluations=max_evaluations,
        max_depth=max_depth,
        max_unresolved_width_days=max_unresolved_width_days,
        all_inputs_defined_assumed=False,
        time_scale=time_scale,
    )
    return ConditionalStrictPhasePartition(phase, time_scale, partition)
