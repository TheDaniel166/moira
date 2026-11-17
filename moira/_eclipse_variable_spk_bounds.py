"""Conditional native SPK bounds for two independently varying TDB parts.

The first Julian-date part and the second day offset remain separate in every
modeled native and Python routing operation. The stored-polynomial receipt may
use a mathematical re-expression solely to cover the same exact epoch set;
that re-expression is never substituted for the native operation ordering.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from fractions import Fraction
import hashlib
import math
import struct

from ._eclipse_interval import IntervalBudgetError, IntervalDomainError, RationalInterval as I
from ._eclipse_native_spk_bounds import (
    GuardedScalarSnapshotEvaluation, _native_record_argument, _record_component, _rounded,
    _selected_descriptor, _snapshot_hash,
)
from ._eclipse_spk_bounds import (
    EclipseSpkBoundsUnavailable, Type2PolynomialBounds, _descriptor_interval, bound_serving_type2_polynomial,
)
from .spk_reader import SpkReader


@dataclass(frozen=True, slots=True)
class ConditionalVariableAnchorBounds:
    """One record's bounds for independent binary64 anchor and offset parts."""

    position_km: tuple[I, I, I]
    velocity_km_per_day: tuple[I, I, I]
    normalized_time: I
    anchor_days: I
    offset_days: I
    record_index: int
    record_snapshot: tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]] = field(repr=False)
    record_snapshot_sha256: str
    source: Type2PolynomialBounds
    record_init: float
    record_length: float
    record_count: int
    descriptor_start: float
    descriptor_end: float
    native_environment_attested: bool = False
    loaded_image_verified: bool = False
    legacy_mapped_evaluator_certified: bool = False
    record_routing_model: str = "conditional_scalar_simd_fma_hull"
    source_record_matches_native: bool = True


@dataclass(frozen=True, slots=True)
class StrictScalarVariableAnchorBounds:
    """Explicit strict-only seam result; not a legacy serving-vector bound.

    The wrapper deliberately has no position or velocity fields. Accessing
    its enclosed data requires choosing the strict snapshot policy explicitly.
    """

    strict_bounds: ConditionalVariableAnchorBounds

    @property
    def record_snapshot_sha256(self) -> str:
        """Identify the strict-only copied record and routing policy."""
        return self.strict_bounds.record_snapshot_sha256


def _round_nearest_even(value: Fraction) -> Fraction:
    """Round an exact rational to finite binary64, ties to even, without fenv."""
    try:
        lo, hi = I.point(value).to_float_bounds()
    except (IntervalDomainError, OverflowError) as exc:
        raise EclipseSpkBoundsUnavailable("strict scalar replay rounding overflow") from exc
    if not math.isfinite(lo) or not math.isfinite(hi):
        raise EclipseSpkBoundsUnavailable("strict scalar replay rounding overflow")
    lower, upper = Fraction.from_float(lo), Fraction.from_float(hi)
    if lower == upper:
        return lower
    if math.nextafter(lo, math.inf) != hi:
        raise EclipseSpkBoundsUnavailable("strict scalar replay rounding neighbors are not adjacent")
    left, right = value - lower, upper - value
    if left == right:
        low_bits = struct.unpack("<Q", struct.pack("<d", lo))[0]
        return lower if low_bits % 2 == 0 else upper
    return lower if left < right else upper


def _strict_point_record_argument(jd: I, offset: I, init: float, length: float, count: int) -> tuple[int, I]:
    """Replay the opt-in strict scalar record path for one binary64 pair."""
    if jd.lo != jd.hi or offset.lo != offset.hi:
        raise EclipseSpkBoundsUnavailable("strict scalar replay requires singleton inputs")
    f = Fraction.from_float
    if f(float(jd.lo)) != jd.lo or f(float(offset.lo)) != offset.lo:
        raise EclipseSpkBoundsUnavailable("strict scalar replay requires binary64 inputs")
    r = _round_nearest_even
    initial, interval = f(init), f(length)
    if interval <= 0:
        raise EclipseSpkBoundsUnavailable("strict scalar replay requires positive record length")
    epoch = r(r(jd.lo - 2451545) * 86400)
    shifted = r(epoch - initial)
    virtual = r(epoch - shifted)
    residual = r(r(epoch - r(shifted + virtual)) + r(virtual - initial))
    first = r(shifted / interval) // 1
    local1 = r(shifted - r(first * interval))
    seconds2 = r(offset.lo * 86400)
    second = r(seconds2 / interval) // 1
    local2 = r(seconds2 - r(second * interval))
    combined = r(r(local1 + local2) + residual)
    third = r(combined / interval) // 1
    if any(abs(value) > 2**53 for value in (first, second, third, first + second, first + second + third)):
        raise EclipseSpkBoundsUnavailable("strict scalar replay index exceeds exact integer domain")
    index = first + second + third
    local = r(combined - r(third * interval))
    if index == count:
        index -= 1
        local = r(local + interval)
    if not 0 <= index < count:
        raise EclipseSpkBoundsUnavailable("strict scalar replay record outside payload")
    radius = r(interval / 2)
    if radius == 0:
        raise EclipseSpkBoundsUnavailable("strict scalar replay radius is zero")
    normalized = r(r(local - radius) / radius)
    return int(index), I.point(normalized)


def variable_snapshot_hash(bounds: ConditionalVariableAnchorBounds | StrictScalarVariableAnchorBounds) -> str:
    """Recompute the digest for the separately bounded inputs and record."""
    if isinstance(bounds, StrictScalarVariableAnchorBounds):
        bounds = bounds.strict_bounds
    representative = float(bounds.anchor_days.midpoint)
    equivalent = bounds.anchor_days - I.point(representative) + bounds.offset_days
    base = _snapshot_hash(
        bounds.source, bounds.record_snapshot, representative, equivalent, bounds.record_init,
        bounds.record_length, bounds.record_count, bounds.record_index,
        bounds.descriptor_start, bounds.descriptor_end,
    )
    split = f"{bounds.anchor_days.lo} {bounds.anchor_days.hi} {bounds.offset_days.lo} {bounds.offset_days.hi}".encode("ascii")
    policy = f"{bounds.record_routing_model} {int(bounds.source_record_matches_native)}".encode("ascii")
    return hashlib.sha256(
        b"moira-eclipse-two-variable-parts-v1\0" + base.encode("ascii") + b"\0" + split + b"\0" + policy
    ).hexdigest()


def _variable_anchor_type2_bounds(
    reader: SpkReader, center: int, target: int, anchor_days: I, offset_days: I,
    *, max_records: int = 256, allow_strict_singleton: bool = False,
) -> ConditionalVariableAnchorBounds | StrictScalarVariableAnchorBounds:
    """Enclose original native operations for independently varying inputs.

    The model assumes binary64 round-to-nearest, gradual underflow, correctly
    rounded FMA, faithful fsum within one extra ulp, and no unsafe compiler
    reassociation. Descriptor, anchor-day, record and carry ambiguities fail
    closed. A point offset of zero also covers single-part reader calls.
    """
    if type(reader) is not SpkReader or not isinstance(anchor_days, I) or not isinstance(offset_days, I):
        raise EclipseSpkBoundsUnavailable("concrete reader and two rational TDB intervals required")
    if isinstance(center, bool) or not isinstance(center, int) or isinstance(target, bool) or not isinstance(target, int):
        raise ValueError("center and target must be integer NAIF identifiers")
    try:
        anchor, offset = _rounded(anchor_days), _rounded(offset_days)
        representative = float(anchor.midpoint)
        if not math.isfinite(representative):
            raise EclipseSpkBoundsUnavailable("non-finite TDB anchor")
        segment = _selected_descriptor(reader, center, target, anchor, offset)
        if segment.data_type != 2:
            raise EclipseSpkBoundsUnavailable("selected descriptor is not SPK type 2")
        # Exact set identity is used only for the mathematical metadata and
        # polynomial receipt, not for the modeled native floating operations.
        equivalent_offset = anchor - I.point(representative) + offset
        source = bound_serving_type2_polynomial(reader, center, target, representative, equivalent_offset,
                                                max_records=max_records)
        descriptor = _descriptor_interval(segment)
        if descriptor.lo != source.descriptor_start_second or descriptor.hi != source.descriptor_end_second:
            raise EclipseSpkBoundsUnavailable("mathematical and native descriptor routes differ")
        evaluator = segment._load_native_evaluator()
        init, length, count, components, coefficient_count = evaluator.chebyshev_metadata()
        routing_model = "conditional_scalar_simd_fma_hull"
        try:
            index, normalized = _native_record_argument(anchor, offset, init, length, count)
        except EclipseSpkBoundsUnavailable as exc:
            if (not allow_strict_singleton or anchor.lo != anchor.hi or offset.lo != offset.hi
                    or "floor branch requires subdivision" not in str(exc)):
                raise
            index, normalized = _strict_point_record_argument(anchor, offset, init, length, count)
            routing_model = "strict_snapshot_scalar_binary64_rn"
        source_matches = index in source.record_indices
        if not source_matches and routing_model != "strict_snapshot_scalar_binary64_rn":
            raise EclipseSpkBoundsUnavailable("native and exact-model record selection differ")
        record = tuple(tuple(float(value) for value in axis) for axis in evaluator.chebyshev_records(index, 1)[0])
        if components != 3 or len(record) != 3 or any(len(axis) != coefficient_count for axis in record):
            raise EclipseSpkBoundsUnavailable("unsupported native type-2 record layout")
        states = tuple(_record_component(axis, normalized, length) for axis in record)
        provisional = ConditionalVariableAnchorBounds(
            tuple(value[0] for value in states), tuple(value[1] for value in states), normalized,
            anchor, offset, index, record, "", source, init, length, count,
            float(segment.start_second), float(segment.end_second),
            record_routing_model=routing_model, source_record_matches_native=source_matches,
        )
        result = replace(provisional, record_snapshot_sha256=variable_snapshot_hash(provisional))
        if routing_model == "strict_snapshot_scalar_binary64_rn":
            return StrictScalarVariableAnchorBounds(result)
        return result
    except (IntervalBudgetError, IntervalDomainError, OverflowError) as exc:
        raise EclipseSpkBoundsUnavailable("variable-anchor enclosure exceeded its domain or budget") from exc


def conditional_variable_anchor_type2_bounds(
    reader: SpkReader, center: int, target: int, anchor_days: I, offset_days: I,
    *, max_records: int = 256,
) -> ConditionalVariableAnchorBounds:
    """Bound the general native scalar/SIMD/FMA routing model or fail closed."""
    result = _variable_anchor_type2_bounds(reader, center, target, anchor_days, offset_days, max_records=max_records)
    if not isinstance(result, ConditionalVariableAnchorBounds):
        raise ArithmeticError("strict-only result escaped the general native policy")
    return result


def strict_variable_anchor_type2_bounds(
    reader: SpkReader, center: int, target: int, anchor_days: I, offset_days: I,
    *, max_records: int = 256,
) -> ConditionalVariableAnchorBounds | StrictScalarVariableAnchorBounds:
    """Admit a distinct strict-only singleton when the general hull is ambiguous."""
    return _variable_anchor_type2_bounds(
        reader, center, target, anchor_days, offset_days, max_records=max_records, allow_strict_singleton=True,
    )


def guarded_variable_scalar_snapshot_evaluate(
    bounds: ConditionalVariableAnchorBounds | StrictScalarVariableAnchorBounds, anchor_days: float, offset_days: float,
) -> GuardedScalarSnapshotEvaluation:
    """Evaluate one admitted original split against its identical copied record."""
    if isinstance(bounds, StrictScalarVariableAnchorBounds):
        bounds = bounds.strict_bounds
    if not isinstance(bounds, ConditionalVariableAnchorBounds):
        raise TypeError("variable-anchor bounds required")
    if (isinstance(anchor_days, bool) or not isinstance(anchor_days, (int, float)) or not math.isfinite(anchor_days)
            or isinstance(offset_days, bool) or not isinstance(offset_days, (int, float)) or not math.isfinite(offset_days)):
        raise ValueError("finite TDB split inputs required")
    anchor, offset = float(anchor_days), float(offset_days)
    if not bounds.anchor_days.contains(anchor) or not bounds.offset_days.contains(offset):
        raise ValueError("TDB split inputs are outside bounded intervals")
    if variable_snapshot_hash(bounds) != bounds.record_snapshot_sha256:
        raise ValueError("bounded coefficient snapshot identity does not match its receipt")
    from . import _moira_native
    capability = getattr(_moira_native, "_eclipse_strict_snapshot_build_contract", None)
    evaluate = getattr(_moira_native, "_eclipse_strict_snapshot_evaluate", None)
    if not callable(capability) or not callable(evaluate):
        raise EclipseSpkBoundsUnavailable("loaded native binary lacks guarded snapshot capability")
    contract = capability()
    if contract != "moira_eclipse_scalar_snapshot_binary64_rn_gradual_v1":
        raise EclipseSpkBoundsUnavailable("native guarded snapshot build is unsupported or unattested")
    try:
        position, velocity, normalized, index = evaluate(
            bounds.record_snapshot, anchor, offset, bounds.record_init, bounds.record_length,
            bounds.record_count, bounds.record_index, bounds.descriptor_start, bounds.descriptor_end,
        )
    except ValueError as exc:
        if str(exc).startswith("eclipse_snapshot_"):
            raise EclipseSpkBoundsUnavailable(str(exc)) from exc
        raise
    if (index != bounds.record_index or not bounds.normalized_time.contains(normalized)
            or any(not box.contains(value) for box, value in zip(bounds.position_km, position))
            or any(not box.contains(value) for box, value in zip(bounds.velocity_km_per_day, velocity))):
        raise ArithmeticError("guarded snapshot escaped its conditional native enclosure")
    return GuardedScalarSnapshotEvaluation(
        tuple(position), tuple(velocity), normalized, index, bounds.record_snapshot_sha256, contract,
    )
