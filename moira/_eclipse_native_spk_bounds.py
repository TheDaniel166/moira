"""Conditional bounds for one native type-2 SPK evaluator operation.

This private research adapter follows the Python descriptor selector, native
descriptor guard, split-time record-index calculation, and both scalar and
AVX Chebyshev recurrences. It uses exact rational interval arithmetic to
enclose each possible binary64 round-to-nearest operation, including possible
FMA contraction. Ambiguous descriptor/record/floor branches fail closed.

The bound is conditional on IEEE-754 binary64 round-to-nearest, gradual
underflow, correctly rounded ``std::fma``, faithful Python ``math.fsum`` within one additional ulp, and a
native build that does not arbitrarily reassociate or apply unsafe fast-math.
The currently loaded native binary does not attest these premises. This is
therefore not an unconditional serving-state or eclipse certificate.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
import hashlib
import math
import struct

from ._eclipse_interval import IntervalBudgetError, IntervalDomainError, RationalInterval as I
from ._eclipse_spk_bounds import (
    EclipseSpkBoundsUnavailable,
    Type2PolynomialBounds,
    _descriptor_interval,
    bound_serving_type2_polynomial,
)
from .spk_reader import SpkReader


_MODEL = "conditional_binary64_RN_gradual_ieee_fma_fsum_1ulp_no_unsafe_reassociation"
_MAX_EXACT_INT = 2**53


@dataclass(frozen=True, slots=True)
class ConditionalNativeType2Bounds:
    """Native position/velocity bounds conditioned on the declared model.

    Coordinates are km and derivatives are km per TDB day. ``source`` is a
    stored-polynomial receipt and does not attest the runtime environment.
    The operation and its record/descriptor branch are bounded only under
    ``arithmetic_model``; loaded-binary build flags and calling-thread mode
    are not verified by this Python implementation.
    """

    position_km: tuple[I, I, I]
    velocity_km_per_day: tuple[I, I, I]
    record_index: int
    normalized_time: I
    source: Type2PolynomialBounds
    jd_tdb: float
    offset_days: I
    record_snapshot: tuple[tuple[float, ...], tuple[float, ...], tuple[float, ...]] = field(repr=False)
    record_snapshot_sha256: str
    record_init: float
    record_length: float
    record_count: int
    descriptor_start: float
    descriptor_end: float
    arithmetic_model: str = _MODEL
    arithmetic_environment_attested: bool = False
    time_conversion_enclosed: bool = False
    light_time_enclosed: bool = False


@dataclass(frozen=True, slots=True)
class GuardedScalarSnapshotEvaluation:
    """One strict scalar result, checked against its immutable input bounds.

    A same-thread native guard checks its FP environment for this call. The
    binary's self-reported build contract is not independent provenance, and
    this result does not attest the legacy mapped reader or physical model.
    """

    position_km: tuple[float, float, float]
    velocity_km_per_day: tuple[float, float, float]
    normalized_time: float
    record_index: int
    record_snapshot_sha256: str
    build_contract_self_reported: str
    independent_build_receipt_verified: bool = False
    legacy_mapped_evaluator_certified: bool = False


def _rounded(x: I) -> I:
    """Bound a binary64 round-to-nearest operation by adjacent floats."""
    try:
        lo, hi = x.to_float_bounds()
    except (IntervalDomainError, OverflowError) as exc:
        raise EclipseSpkBoundsUnavailable("binary64 rounding overflow") from exc
    return I(lo, hi)


def _fsum(values: tuple[I, ...]) -> I:
    """Enclose an fsum error of up to one binary64 ulp beyond RN.

    At an exact power of two, the adjacent floats on the smaller-magnitude
    side are only half an ulp apart when the ulp is taken from the larger
    binade. Two outward steps therefore cover the stated one-ulp allowance
    even where one representable neighbor would be insufficient. The initial
    outward conversion already encloses the correctly rounded result.
    """
    result = _rounded(sum(values, I.point(0)))
    lo, hi = float(result.lo), float(result.hi)
    for _ in range(2):
        lo = math.nextafter(lo, -math.inf)
        hi = math.nextafter(hi, math.inf)
    if not math.isfinite(lo) or not math.isfinite(hi):
        raise EclipseSpkBoundsUnavailable("fsum rounding overflow")
    return I(lo, hi)


def _hull(*values: I) -> I:
    return I(min(value.lo for value in values), max(value.hi for value in values))


def _floor_unique(value: I, label: str) -> int:
    lo, hi = value.lo // 1, value.hi // 1
    if lo != hi or not -_MAX_EXACT_INT <= lo <= _MAX_EXACT_INT:
        raise EclipseSpkBoundsUnavailable(f"{label} floor branch requires subdivision")
    return int(lo)


def _difference_product(a: I, b: I, c: I) -> I:
    """Enclose subtract-after-multiply and contracted multiply-subtract."""
    return _hull(_rounded(a - _rounded(b*c)), _rounded(a - b*c))


def _recurrence(a: I, b: I, c: I, d: I) -> I:
    """Enclose scalar, SIMD and fused forms of ``a + b*c - d``."""
    product = _rounded(b*c)
    return _hull(
        _rounded(_rounded(a + product) - d),
        _rounded(a + _rounded(product - d)),
        _rounded(_rounded(a + b*c) - d),
        _rounded(a + _rounded(b*c - d)),
        _rounded(a + b*c - d),
    )


def _coverage_signs(start: float, end: float, jd: float | I, offset: I) -> tuple[I, I, I, I]:
    """Enclose Python fsum and C++ FMA descriptor comparisons separately."""
    anchor = jd if isinstance(jd, I) else I.point(jd)
    whole1 = _floor_unique(anchor, "anchor day")
    whole2 = _floor_unique(offset, "split day")
    whole = whole1 + whole2 - 2451545
    if abs(whole1) > _MAX_EXACT_INT or abs(whole2) > _MAX_EXACT_INT or abs(whole) > _MAX_EXACT_INT:
        raise EclipseSpkBoundsUnavailable("split day is outside exact integer model")
    # Python's selector calculates an integer anchor and uses math.fsum.
    py_anchor = _rounded(I.point(whole) * 86400)
    part1 = _rounded(anchor - whole1)
    part2 = _rounded(offset - whole2)
    fractional_seconds = _rounded(_fsum((part1, part2)) * 86400)
    py_start = _fsum((py_anchor, fractional_seconds, I.point(-start)))
    py_end = _fsum((py_anchor, fractional_seconds, I.point(-end)))

    # Native validator uses floating-point day parts and std::fma.
    native_days = _rounded(_rounded(I.point(whole1) + whole2) - 2451545)
    native_anchor = _rounded(native_days * 86400)
    fraction = _rounded(part1 + part2)
    native_start = _rounded(fraction * 86400 + _rounded(native_anchor - start))
    native_end = _rounded(fraction * 86400 + _rounded(native_anchor - end))
    return py_start, py_end, native_start, native_end


def _coverage_class(start: I, end: I) -> str:
    if start.lo >= 0 and end.hi <= 0:
        return "inside"
    if start.hi < 0 or end.lo > 0:
        return "outside"
    return "unknown"


def _require_matching_native_descriptor(reader: SpkReader, segment) -> None:
    """Reject ambiguous payload keys before using a native coverage guard.

    The native evaluator identifies a descriptor by its payload addresses and
    type, selecting the first catalog match.  Consequently the Python-selected
    descriptor's times alone do not establish the native guard's times if a
    payload key is reused.  All matches must have the same represented bounds.
    The catalog and reader are still required to stay unchanged throughout use.
    """
    try:
        kernel = reader._kernel
        handle = segment._handle
        if handle is not kernel._handle:
            raise EclipseSpkBoundsUnavailable("native descriptor handle does not match reader")
        catalog = handle.catalog() if handle is not None else kernel.catalog
        summaries = catalog["summaries"]
        if not isinstance(summaries, (list, tuple)) or len(summaries) > 100000:
            raise EclipseSpkBoundsUnavailable("unsupported native descriptor catalog")
        key = (int(segment.start_i), int(segment.end_i), int(segment.data_type))
        expected = (float(segment.start_second), float(segment.end_second))
        if not all(math.isfinite(x) for x in expected) or expected[0] > expected[1]:
            raise EclipseSpkBoundsUnavailable("invalid selected descriptor coverage")
        matches = 0
        for item in summaries:
            descriptor = item["descriptor"]
            if len(descriptor) != 8:
                raise EclipseSpkBoundsUnavailable("unsupported native descriptor catalog")
            if (int(descriptor[6]), int(descriptor[7]), int(descriptor[5])) != key:
                continue
            matches += 1
            coverage = (float(descriptor[0]), float(descriptor[1]))
            if coverage != expected:
                raise EclipseSpkBoundsUnavailable("native descriptor payload has conflicting coverage")
        if not matches:
            raise EclipseSpkBoundsUnavailable("native descriptor payload not present in catalog")
    except EclipseSpkBoundsUnavailable:
        raise
    except (AttributeError, KeyError, TypeError, ValueError, OverflowError, OSError, RuntimeError) as exc:
        raise EclipseSpkBoundsUnavailable("native descriptor catalog unavailable") from exc


def _selected_descriptor(reader: SpkReader, center: int, target: int, jd: float | I, offset: I):
    try:
        segments = reader._segments_for_pair(center, target)
    except KeyError as exc:
        raise EclipseSpkBoundsUnavailable("direct SPK pair unavailable") from exc
    for segment in segments:
        _descriptor_interval(segment)
        py_start, py_end, native_start, native_end = _coverage_signs(
            float(segment.start_second), float(segment.end_second), jd, offset
        )
        selection = _coverage_class(py_start, py_end)
        if selection == "unknown":
            raise EclipseSpkBoundsUnavailable("Python descriptor routing requires subdivision")
        if selection == "inside":
            if _coverage_class(native_start, native_end) != "inside":
                raise EclipseSpkBoundsUnavailable("native descriptor guard requires subdivision")
            _require_matching_native_descriptor(reader, segment)
            return segment
    raise EclipseSpkBoundsUnavailable("no descriptor covers the requested interval")


def _native_record_argument(jd: float | I, offset_days: I, init: float, length: float, count: int) -> tuple[int, I]:
    """Enclose the three native floor stages, refusing ambiguous branches."""
    length_i = I.point(length)
    anchor = jd if isinstance(jd, I) else I.point(jd)
    epoch = _rounded(_rounded(anchor - 2451545) * 86400)
    offset = _rounded(epoch - init)
    virtual_init = _rounded(epoch - offset)
    roundoff = _rounded(_rounded(epoch - _rounded(offset + virtual_init)) + _rounded(virtual_init - init))
    first = _floor_unique(_rounded(offset / length_i), "first record index")
    offset1 = _difference_product(offset, I.point(first), length_i)
    split_seconds = _rounded(offset_days * 86400)
    second = _floor_unique(_rounded(split_seconds / length_i), "split record index")
    offset2 = _difference_product(split_seconds, I.point(second), length_i)
    combined = _rounded(_rounded(offset1 + offset2) + roundoff)
    third = _floor_unique(_rounded(combined / length_i), "record carry")
    local = _difference_product(combined, I.point(third), length_i)
    if abs(first + second) > _MAX_EXACT_INT or abs(first + second + third) > _MAX_EXACT_INT:
        raise EclipseSpkBoundsUnavailable("record index sum exceeds exact binary64 integer range")
    index = first + second + third
    if index == count:
        index -= 1
        local = _rounded(local + length_i)
    if not 0 <= index < count:
        raise EclipseSpkBoundsUnavailable("native record index lies outside segment payload")
    radius = _rounded(length_i * Fraction(1, 2))
    if radius.contains_zero:
        raise EclipseSpkBoundsUnavailable("record radius contains zero")
    return index, _rounded(_rounded(local - radius) / radius)


def _record_component(coefficients, normalized: I, length: float) -> tuple[I, I]:
    """Enclose native position and derivative recurrences for one component."""
    if not coefficients or not all(math.isfinite(value) for value in coefficients):
        raise EclipseSpkBoundsUnavailable("type-2 coefficient values are invalid")
    s2 = _rounded(2 * normalized)
    first = second = I.point(0)
    rate_first = rate_second = I.point(0)
    for coefficient in reversed(coefficients[1:]):
        # Include both a rounded multiply-by-two and an unrounded operand to
        # cover an allowed FMA contraction into the surrounding addition.
        two_first = _hull(_rounded(2 * first), 2 * first)
        new_rate = _recurrence(two_first, s2, rate_first, rate_second)
        new_first = _recurrence(I.point(coefficient), s2, first, second)
        rate_first, rate_second = new_rate, rate_first
        first, second = new_first, first
    position = _recurrence(I.point(coefficients[0]), normalized, first, second)
    derivative_s = _recurrence(first, normalized, rate_first, rate_second)
    scale = _rounded(_rounded(I.point(2) * 86400) / length)
    return position, _rounded(derivative_s * scale)


def _snapshot_hash(source, record, jd, offsets, init, length, count, index, start, end) -> str:
    """Bind the immutable coefficient snapshot and descriptor metadata."""
    digest = hashlib.sha256()
    digest.update(b"moira-eclipse-strict-scalar-snapshot-v1\0")
    digest.update(f"{source.center} {source.target} {source.frame_id} {count} {index} {len(record[0])}\n".encode("ascii"))
    digest.update(source.source_sha256_at_reader_open.encode("ascii") + b"\0")
    digest.update(source.copied_records_sha256.encode("ascii") + b"\0")
    digest.update(f"{offsets.lo.numerator}/{offsets.lo.denominator} {offsets.hi.numerator}/{offsets.hi.denominator}\n".encode("ascii"))
    digest.update(struct.pack("<5d", start, end, init, length, jd))
    for axis in record:
        for coefficient in axis:
            digest.update(struct.pack("<d", coefficient))
    return digest.hexdigest()


def conditional_native_type2_bounds(
    reader: SpkReader, center: int, target: int, jd_tdb: float, offset_days: I,
    *, max_records: int = 256,
) -> ConditionalNativeType2Bounds:
    """Enclose one selected native type-2 route under explicit FP assumptions.

    No runtime/compiler attestation is performed. Unknown descriptor, split
    day, record-index, overflow or unsupported reader states raise the named
    enclosure-unavailable error. Time conversion and light-time are outside
    this operation's scope. ``offset_days`` is interpreted as possible input
    binary64 day offsets, not as a proof about a caller's epoch conversion.
    """
    if type(reader) is not SpkReader or not isinstance(offset_days, I):
        raise EclipseSpkBoundsUnavailable("concrete SpkReader and rational offset interval required")
    if isinstance(jd_tdb, bool) or not isinstance(jd_tdb, (float, int)) or not math.isfinite(jd_tdb):
        raise ValueError("finite TDB anchor required")
    if isinstance(center, bool) or not isinstance(center, int) or isinstance(target, bool) or not isinstance(target, int):
        raise ValueError("center and target must be integer NAIF identifiers")
    offset = _rounded(offset_days)
    try:
        segment = _selected_descriptor(reader, center, target, float(jd_tdb), offset)
        if segment.data_type != 2:
            raise EclipseSpkBoundsUnavailable("selected descriptor is not SPK type 2")
        source = bound_serving_type2_polynomial(reader, center, target, float(jd_tdb), offset, max_records=max_records)
        descriptor = _descriptor_interval(segment)
        if descriptor.lo != source.descriptor_start_second or descriptor.hi != source.descriptor_end_second:
            raise EclipseSpkBoundsUnavailable("mathematical and native descriptor routes differ")
        evaluator = segment._load_native_evaluator()
        init, length, count, components, coefficient_count = evaluator.chebyshev_metadata()
        index, normalized = _native_record_argument(float(jd_tdb), offset, init, length, count)
        if index not in source.record_indices:
            raise EclipseSpkBoundsUnavailable("native and exact-model record selection differ")
        copied_record = evaluator.chebyshev_records(index, 1)[0]
        record = tuple(tuple(float(value) for value in axis) for axis in copied_record)
        if components != 3 or len(record) != 3 or any(len(axis) != coefficient_count for axis in record):
            raise EclipseSpkBoundsUnavailable("unsupported native type-2 record layout")
        digest = _snapshot_hash(source, record, float(jd_tdb), offset, init, length, count, index,
                                float(segment.start_second), float(segment.end_second))
        states = tuple(_record_component(axis, normalized, length) for axis in record)
        return ConditionalNativeType2Bounds(
            tuple(value[0] for value in states), tuple(value[1] for value in states),
            index, normalized, source, float(jd_tdb), offset, record, digest,
            init, length, count, float(segment.start_second), float(segment.end_second),
        )
    except (IntervalBudgetError, IntervalDomainError) as exc:
        raise EclipseSpkBoundsUnavailable("native arithmetic enclosure exceeded its domain or budget") from exc


def guarded_scalar_snapshot_evaluate(
    bounds: ConditionalNativeType2Bounds, offset_days: float,
) -> GuardedScalarSnapshotEvaluation:
    """Evaluate the exact bounded snapshot under the guarded native policy.

    The copied coefficient tuple is the same immutable object from which the
    conditional interval was constructed. No live SPK file read or Python
    callback is used in the native call. Build marker is self-reported and is
    not a substitute for a separately verified binary/build receipt.
    """
    if not isinstance(bounds, ConditionalNativeType2Bounds):
        raise TypeError("bounds must be a ConditionalNativeType2Bounds")
    if isinstance(offset_days, bool) or not isinstance(offset_days, (float, int)) or not math.isfinite(offset_days):
        raise ValueError("finite TDB offset in days required")
    offset = float(offset_days)
    if not bounds.offset_days.contains(offset):
        raise ValueError("TDB offset is outside the bounded snapshot interval")
    expected = _snapshot_hash(
        bounds.source, bounds.record_snapshot, bounds.jd_tdb, bounds.offset_days, bounds.record_init,
        bounds.record_length, bounds.record_count, bounds.record_index,
        bounds.descriptor_start, bounds.descriptor_end,
    )
    if expected != bounds.record_snapshot_sha256:
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
            bounds.record_snapshot, bounds.jd_tdb, offset,
            bounds.record_init, bounds.record_length, bounds.record_count, bounds.record_index,
            bounds.descriptor_start, bounds.descriptor_end,
        )
    except ValueError as exc:
        if str(exc).startswith("eclipse_snapshot_"):
            raise EclipseSpkBoundsUnavailable(str(exc)) from exc
        raise
    if (index != bounds.record_index or not bounds.normalized_time.contains(normalized)
            or any(not enclosure.contains(value) for enclosure, value in zip(bounds.position_km, position))
            or any(not enclosure.contains(value) for enclosure, value in zip(bounds.velocity_km_per_day, velocity))):
        raise ArithmeticError("guarded snapshot escaped its conditional native enclosure")
    return GuardedScalarSnapshotEvaluation(
        tuple(position), tuple(velocity), normalized, index, bounds.record_snapshot_sha256, contract,
    )
