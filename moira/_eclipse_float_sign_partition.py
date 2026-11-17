"""Bounded sign partitions over representable binary64 eclipse epochs.

This module partitions *floating-point inputs*, not the real time continuum.
A caller-supplied oracle must enclose the sign of every successful evaluation
on a closed float interval.  An unproved interval is subdivided or retained
as unresolved; provider errors and exhausted work budgets are never mapped to
absence.  The caller must separately establish totality over the domain and
all mathematical, source, clock, native and floating-environment premises.

An adjacent sign change is evidence about two representable samples only. It
does not prove a continuous zero, the uniqueness of an event, a physical
phase, or an exhaustive search of times between representable inputs.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import struct
from typing import Callable, Literal

from ._eclipse_interval import IntervalBudgetError
from ._eclipse_interval_roots import EnclosureUnavailable

Sign = Literal["negative", "zero", "positive", "unresolved"]
_MASK64 = (1 << 64) - 1
_SIGN64 = 1 << 63


def _float_key(value: float) -> int:
    """Map finite IEEE binary64 encodings into monotonically ordered keys.

    Negative and positive zero have adjacent but distinct keys.  This matters
    to providers that observe the sign bit; both are retained in the domain.
    """
    bits = struct.unpack(">Q", struct.pack(">d", value))[0]
    return (~bits & _MASK64) if bits & _SIGN64 else bits | _SIGN64


def _key_float(key: int) -> float:
    """Invert :func:`_float_key` for a finite-representable-domain key."""
    bits = (key & ~_SIGN64) if key & _SIGN64 else (~key & _MASK64)
    return struct.unpack(">d", struct.pack(">Q", bits))[0]


@dataclass(frozen=True, slots=True)
class RepresentableSignCell:
    """Inclusive, non-overlapping binary64 input cells and conditional sign."""

    first: float
    last: float
    sign: Sign
    reason: str
    first_key: int
    last_key: int

    @property
    def represented_count(self) -> int:
        """Count all encoded binary64 values, including both signed zeros."""
        return self.last_key - self.first_key + 1


@dataclass(frozen=True, slots=True)
class AdjacentSignWitness:
    """Opposite conditional signs on two adjacent represented input values."""

    first: float
    last: float
    first_sign: Literal["negative", "positive"]
    last_sign: Literal["negative", "positive"]


@dataclass(frozen=True, slots=True)
class RepresentableSignPartition:
    """A gap-free float-domain cover under caller-supplied oracle premises.

    ``all_inputs_defined_assumed`` is the caller's statement, not a proof made
    here. A provider that bounds *successful evaluations only* must leave it
    false until successful evaluation of the entire domain is independently
    established. Even a fully classified partition says nothing about real
    values between floats or about physical event completeness.
    """

    first: float
    last: float
    cells: tuple[RepresentableSignCell, ...]
    evaluations: int
    max_evaluations: int
    max_depth: int
    all_inputs_defined_assumed: bool
    unit: str
    time_scale: str | None

    @property
    def represented_coverage_complete(self) -> bool:
        """Check exact ownership of every encoded input in the requested range."""
        if not self.cells or self.cells[0].first_key != _float_key(self.first):
            return False
        return (all(left.last_key + 1 == right.first_key
                    for left, right in zip(self.cells, self.cells[1:]))
                and self.cells[-1].last_key == _float_key(self.last))

    @property
    def all_signs_classified(self) -> bool:
        """Whether all inputs have signs, conditional on provider totality."""
        return (self.all_inputs_defined_assumed and self.represented_coverage_complete
                and all(cell.sign != "unresolved" for cell in self.cells))

    @property
    def adjacent_sign_witnesses(self) -> tuple[AdjacentSignWitness, ...]:
        """Return opposite signs conditional on caller-declared totality.

        A successful-output-only oracle cannot establish either endpoint
        exists, so no witness is returned until totality is separately assumed.
        These witnesses still do not certify continuous roots.
        """
        if not self.all_inputs_defined_assumed:
            return ()
        result = []
        for left, right in zip(self.cells, self.cells[1:]):
            if (left.last_key + 1 == right.first_key
                    and left.sign in ("negative", "positive")
                    and right.sign in ("negative", "positive")
                    and left.sign != right.sign):
                result.append(AdjacentSignWitness(left.last, right.first, left.sign, right.sign))
        return tuple(result)


def partition_representable_signs(
    first: float,
    last: float,
    enclosure: Callable[[float, float], Sign | None],
    *,
    max_evaluations: int,
    max_depth: int = 64,
    max_unresolved_width_days: float = 0.0,
    all_inputs_defined_assumed: bool = False,
    unit: str = "Julian day",
    time_scale: str | None = None,
) -> RepresentableSignPartition:
    """Partition a closed interval of finite represented epochs by sign.

    The oracle receives first/last represented floats and returns ``positive``
    or ``negative`` only if every successful evaluation in the cell has that
    strict sign, ``zero`` only if every successful evaluation is exactly zero,
    or ``None``/``unresolved`` if not established. When zero encodings occur,
    the oracle must honor both +0 and -0 input cases. It is responsible for all
    rounding, routing, environmental and availability assumptions.

    Partial results remain a full cover of the original *float encodings*.
    No interpolation or continuity is inferred. ``max_unresolved_width_days``
    bounds the numeric width of unresolved leaves and is not an error bound.
    """
    if (isinstance(first, bool) or isinstance(last, bool)
            or not isinstance(first, float) or not isinstance(last, float)
            or not math.isfinite(first) or not math.isfinite(last)):
        raise ValueError("finite binary64 endpoints required")
    lo, hi = _float_key(first), _float_key(last)
    if lo > hi:
        raise ValueError("float-domain endpoints must be ordered")
    if not callable(enclosure):
        raise TypeError("enclosure must be callable")
    if type(max_evaluations) is not int or max_evaluations < 0:
        raise ValueError("max_evaluations must be a nonnegative integer")
    if type(max_depth) is not int or not 0 <= max_depth <= 64:
        raise ValueError("max_depth must be an integer from 0 to 64")
    if (isinstance(max_unresolved_width_days, bool)
            or not isinstance(max_unresolved_width_days, (int, float))
            or not math.isfinite(max_unresolved_width_days)
            or max_unresolved_width_days < 0):
        raise ValueError("max_unresolved_width_days must be finite and nonnegative")
    if type(all_inputs_defined_assumed) is not bool:
        raise TypeError("all_inputs_defined_assumed must be a bool")
    if not isinstance(unit, str) or not unit.strip():
        raise ValueError("unit must be a nonempty string")
    if time_scale is not None and (not isinstance(time_scale, str) or not time_scale.strip()):
        raise ValueError("time_scale must be None or a nonempty string")

    pending = [(lo, hi, 0)]
    cells: list[RepresentableSignCell] = []
    evaluations = 0

    def append(a: int, b: int, status: Sign, reason: str) -> None:
        cells.append(RepresentableSignCell(_key_float(a), _key_float(b), status, reason, a, b))

    while pending:
        a, b, depth = pending.pop()
        if evaluations >= max_evaluations:
            append(a, b, "unresolved", "evaluation_budget_exhausted")
            for remaining_a, remaining_b, _ in pending:
                append(remaining_a, remaining_b, "unresolved", "evaluation_budget_exhausted")
            pending.clear()
            break
        evaluations += 1
        try:
            value = enclosure(_key_float(a), _key_float(b))
        except (EnclosureUnavailable, IntervalBudgetError) as exc:
            value = None
            reason = f"enclosure_unavailable: {exc}"
        else:
            if value not in (None, "positive", "negative", "zero", "unresolved"):
                raise TypeError("enclosure must return a sign, unresolved, or None")
            reason = "sign_not_established"
        if value in ("positive", "negative", "zero"):
            append(a, b, value, "provider_enclosed_sign")
            continue
        width = _key_float(b) - _key_float(a)
        if (a == b or depth >= max_depth
                or (max_unresolved_width_days > 0 and width <= max_unresolved_width_days)):
            append(a, b, "unresolved", reason if depth < max_depth else "depth_limit_reached")
            continue
        middle = (a + b) // 2
        # Closed, non-overlapping index domains: no representable epoch lost.
        pending.append((middle + 1, b, depth + 1))
        pending.append((a, middle, depth + 1))

    return RepresentableSignPartition(
        first, last, tuple(sorted(cells, key=lambda c: c.first_key)),
        evaluations, max_evaluations, max_depth, all_inputs_defined_assumed, unit, time_scale,
    )
