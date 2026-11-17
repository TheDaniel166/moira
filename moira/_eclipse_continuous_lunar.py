"""Continuous exact-polynomial lunar reference vectors and derivatives.

The model is distinct from the legacy evaluator: exact represented type-2
coefficients normalized by uniform INIT/INTLEN, the unique exact reference TT/TDB fixed point, geometric Moon,
and exactly ten real-arithmetic retarded-Sun iterations. A model freezes one
strictly interior record for each direct route; it refuses descriptor and
record seams rather than assuming the stored polynomials join continuously.
Each subinterval reuses the same immutable coefficient tuples. Norms must be
strictly positive and every emission must remain within the declared horizon.
By default the record's raw MID/RADIUS words are not read or verified; an
opt-in record-word verifier can check them for the frozen request. This is
an explicitly defined uniform-metadata model, not proof of an arbitrary SPK
type-2 record's prescribed normalization. Neither live kernel integrity nor
physical/legacy eclipse accuracy is attested.
"""
from __future__ import annotations

from dataclasses import dataclass, field, replace
from fractions import Fraction
import hashlib
import math
import struct

from ._eclipse_interval import IntervalBudgetError, IntervalDomainError, RationalInterval as I
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_reference_clock import ContinuousReferenceTdb, bound_continuous_reference_tdb
from ._eclipse_spk_bounds import (
    Type2PolynomialBounds, _chebyshev, _raw_seconds, _select_descriptor, bound_serving_type2_polynomial,
)
from .constants import C_KM_PER_DAY
from .spk_reader import SpkReader


class EclipseContinuousLunarUnavailable(EnclosureUnavailable):
    """The exact lunar model cannot be proved on this closed domain."""


@dataclass(frozen=True, slots=True)
class ContinuousType2Record:
    """One immutable single-record exact-polynomial model and its receipt."""

    center: int
    target: int
    record_index: int
    record_start_seconds: Fraction
    record_length_seconds: Fraction
    coefficients: tuple[tuple[Fraction, ...], tuple[Fraction, ...], tuple[Fraction, ...]] = field(repr=False)
    source: Type2PolynomialBounds


@dataclass(frozen=True, slots=True)
class ContinuousLunarReference:
    """A fixed exact-coefficient reference model on one closed TT domain."""

    tt_anchor_jd: float
    tt_offset_days: I
    max_light_delay_days: Fraction
    precision_bits: int
    records: tuple[ContinuousType2Record, ...]
    exact_reference_model_only: bool = True
    uniform_init_intlen_reference_only: bool = True
    raw_record_mid_radius_verified: bool = False
    unchanged_reference_source_and_constants_required: bool = True
    source_and_kernel_attested: bool = False
    legacy_evaluator_enclosed: bool = False
    ut1_enclosed: bool = False
    physical_accuracy_certified: bool = False
    raw_record_word_sha256: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ContinuousLunarVectorBounds:
    """Real vector and signed TT derivative enclosures on one closed cell."""

    tt_offset_days: I
    sun_geocentric_km: tuple[I, I, I]
    moon_geocentric_km: tuple[I, I, I]
    sun_derivative_km_per_tt_day: tuple[I, I, I]
    moon_derivative_km_per_tt_day: tuple[I, I, I]
    clock_usages: tuple[ContinuousReferenceTdb, ...]
    fixed_sun_iterations: int = 10
    continuous_on_domain: bool = True
    differentiable_on_domain: bool = True
    uniform_init_intlen_reference_only: bool = True
    raw_record_mid_radius_verified: bool = False
    unchanged_reference_source_and_constants_required: bool = True
    source_and_kernel_attested: bool = False
    legacy_evaluator_enclosed: bool = False
    physical_accuracy_certified: bool = False


@dataclass(frozen=True, slots=True)
class ContinuousSunLightTimeCertificate:
    """Conditional contraction bounds for the uniform-metadata Sun model.

    Error and residual bounds apply to ideal real arithmetic, not the rounded
    serving iteration. The Sun vector returned by ``vectors`` uses the tenth
    emission-time update; ``last_next_delay_error_days`` instead applies to
    the delay computed from that vector for a hypothetical eleventh update.
    """

    vectors: ContinuousLunarVectorBounds
    delay_map_image_days: I
    contraction_factor: Fraction
    sun_emission_delay_residual_days: Fraction
    sun_emission_delay_error_days: Fraction
    last_next_delay_error_days: Fraction
    sun_position_component_error_km: Fraction
    continuous_fixed_point_unique: bool = True
    uniform_init_intlen_reference_only: bool = True
    raw_record_mid_radius_verified: bool = False
    source_and_kernel_attested: bool = False
    legacy_evaluator_enclosed: bool = False
    physical_accuracy_certified: bool = False


def _copy_single_record(reader, center, target, anchor, tdb_offsets):
    source = bound_serving_type2_polynomial(reader, center, target, anchor, tdb_offsets, max_records=1)
    if source.frame_id != 1 or len(source.record_indices) != 1:
        raise EclipseContinuousLunarUnavailable("reference route needs one J2000 type-2 record")
    seconds = _raw_seconds(anchor, tdb_offsets)
    segment = _select_descriptor(reader._segments_for_pair(center, target), seconds)
    if seconds.lo <= source.descriptor_start_second or seconds.hi >= source.descriptor_end_second:
        raise EclipseContinuousLunarUnavailable("reference descriptor boundary requires subdivision")
    evaluator = segment._load_native_evaluator()
    init, length, count, components, coefficient_count = evaluator.chebyshev_metadata()
    index = source.record_indices[0]
    start = Fraction.from_float(init) + index * Fraction.from_float(length)
    stop = start + Fraction.from_float(length)
    if seconds.lo <= start or seconds.hi >= stop:
        raise EclipseContinuousLunarUnavailable("reference record seam requires subdivision")
    raw = tuple(tuple(float(x) for x in axis) for axis in evaluator.chebyshev_records(index, 1)[0])
    if components != 3 or len(raw) != 3 or any(len(axis) != coefficient_count for axis in raw):
        raise EclipseContinuousLunarUnavailable("reference record layout changed")
    if any(not math.isfinite(value) for axis in raw for value in axis):
        raise EclipseContinuousLunarUnavailable("reference record contains nonfinite coefficients")
    # Reconstruct the exact adapter's digest, ensuring this frozen tuple really
    # matches the record words and metadata whose interval route was selected.
    digest = hashlib.sha256()
    digest.update(b"moira-eclipse-type2-copied-records-v1\0")
    digest.update(f"{center} {target} {int(segment.frame)} {int(segment.start_i)} {int(segment.end_i)} "
                  f"{count} {components} {coefficient_count}\n".encode("ascii"))
    digest.update(struct.pack("<4d", float(segment.start_second), float(segment.end_second), init, length))
    digest.update(f"{index}\n".encode("ascii"))
    for axis in raw:
        for coefficient in axis:
            digest.update(struct.pack("<d", coefficient))
    if digest.hexdigest() != source.copied_records_sha256:
        raise EclipseContinuousLunarUnavailable("reference source record changed during copying")
    coefficients = tuple(tuple(Fraction.from_float(x) for x in axis) for axis in raw)
    return ContinuousType2Record(center, target, index, start, Fraction.from_float(length), coefficients, source)


def build_continuous_lunar_reference(
    reader, tt_anchor_jd: float, tt_offset_days: I, *,
    max_light_delay_days: Fraction = Fraction(1, 100), precision_bits: int = 128,
) -> ContinuousLunarReference:
    """Freeze four source records covering reception and every allowed emission."""
    if type(reader) is not SpkReader:
        raise EclipseContinuousLunarUnavailable("exact direct SpkReader required")
    if not isinstance(tt_offset_days, I):
        raise TypeError("TT offsets must be a RationalInterval")
    if not isinstance(max_light_delay_days, Fraction) or not 0 < max_light_delay_days <= 1:
        raise ValueError("max_light_delay_days must be a positive Fraction <=1 day")
    if type(precision_bits) is not int or not 64 <= precision_bits <= 256:
        raise ValueError("precision_bits must be an integer from 64 to 256")
    if not math.isfinite(C_KM_PER_DAY) or C_KM_PER_DAY <= 0:
        raise EclipseContinuousLunarUnavailable("reference light speed must be positive and finite")
    clock_domain = I(tt_offset_days.lo - max_light_delay_days, tt_offset_days.hi)
    clock = bound_continuous_reference_tdb(tt_anchor_jd, clock_domain, precision_bits=precision_bits)
    reception = bound_continuous_reference_tdb(tt_anchor_jd, tt_offset_days, precision_bits=precision_bits)
    anchor = clock.tt_anchor_jd
    try:
        records = tuple(_copy_single_record(reader, center, target, anchor,
                            clock.tdb_offset_days if (center, target) == (0, 10)
                            else reception.tdb_offset_days)
                        for center, target in ((0, 3), (3, 399), (3, 301), (0, 10)))
    except (IntervalBudgetError, IntervalDomainError, OverflowError) as exc:
        raise EclipseContinuousLunarUnavailable("reference record construction budget exhausted") from exc
    hashes = {record.source.source_sha256_at_reader_open for record in records}
    if len(hashes) != 1:
        raise EclipseContinuousLunarUnavailable("reference route source identity changed")
    return ContinuousLunarReference(anchor, tt_offset_days, max_light_delay_days, precision_bits, records)


def verify_continuous_lunar_record_words(reader, model: ContinuousLunarReference) -> ContinuousLunarReference:
    """Verify MID/RADIUS and every coefficient word of the frozen records.

    The NAIF type-2 normalizer is the record's MID/RADIUS. Admission here
    requires those exact binary64 words to equal the model's uniform
    INIT/INTLEN normalization, and every coefficient to match the frozen
    tuple. This is a request-specific on-disk record witness, not a live
    mapped-kernel, source/build or reader-lifetime attestation. A replacement
    receipt is returned; the caller's original model is left unchanged.
    """
    if type(reader) is not SpkReader or reader._closed or not isinstance(model, ContinuousLunarReference):
        raise EclipseContinuousLunarUnavailable("open direct reader and frozen model required")
    if (len(model.records) != 4 or {(record.center, record.target) for record in model.records}
            != {(0, 3), (3, 399), (3, 301), (0, 10)}):
        raise EclipseContinuousLunarUnavailable("all four distinct reference routes required")
    hashes = []
    with open(reader.path, "rb") as source:
        for record in model.records:
            if record.source.source_sha256_at_reader_open != reader._source_identity.sha256:
                raise EclipseContinuousLunarUnavailable("frozen and supplied reader identities differ")
            segment = _select_descriptor(reader._segments_for_pair(record.center, record.target),
                                         record.source.interval_seconds_tdb)
            if len(record.coefficients) != 3 or not record.coefficients[0]:
                raise EclipseContinuousLunarUnavailable("invalid frozen record dimensions")
            count = len(record.coefficients[0])
            if any(len(axis) != count for axis in record.coefficients):
                raise EclipseContinuousLunarUnavailable("invalid frozen record dimensions")
            words = 2+3*count
            source.seek((segment.start_i-1+record.record_index*words)*8)
            raw = source.read(words*8)
            if len(raw) != words*8:
                raise EclipseContinuousLunarUnavailable("selected raw type-2 record truncated")
            values = struct.unpack(("<" if segment._little_endian else ">")+"d"*words, raw)
            if not all(math.isfinite(value) for value in values):
                raise EclipseContinuousLunarUnavailable("selected raw record is nonfinite")
            midpoint, radius = map(Fraction.from_float, values[:2])
            if (radius <= 0 or midpoint != record.record_start_seconds+record.record_length_seconds/2
                    or radius != record.record_length_seconds/2):
                raise EclipseContinuousLunarUnavailable("raw MID/RADIUS differs from reference normalization")
            if tuple(map(Fraction.from_float, values[2:])) != tuple(
                    coefficient for axis in record.coefficients for coefficient in axis):
                raise EclipseContinuousLunarUnavailable("raw coefficient words differ from frozen reference")
            hashes.append(hashlib.sha256(raw).hexdigest())
    return replace(model, raw_record_mid_radius_verified=True, raw_record_word_sha256=tuple(hashes))


def enclose_continuous_lunar_reference(model: ContinuousLunarReference, subinterval: I) -> ContinuousLunarVectorBounds:
    """Enclose exact vectors and derivatives on a closed model subinterval."""
    if not isinstance(model, ContinuousLunarReference):
        raise TypeError("continuous lunar reference model required")
    if not isinstance(subinterval, I):
        raise TypeError("TT subinterval must be a RationalInterval")
    if subinterval.lo < model.tt_offset_days.lo or subinterval.hi > model.tt_offset_days.hi:
        raise ValueError("TT subinterval lies outside the frozen model domain")
    def q(value):
        return value.quantize_outward(model.precision_bits)
    zero, one = I.point(0), I.point(1)
    clocks: list[ContinuousReferenceTdb] = []
    records = {(record.center, record.target): record for record in model.records}

    def clock(offsets):
        result = bound_continuous_reference_tdb(model.tt_anchor_jd, offsets, precision_bits=model.precision_bits)
        clocks.append(result)
        return result

    def route(pair, conversion):
        record = records[pair]
        seconds = q((I.point(model.tt_anchor_jd) - 2451545 + conversion.tdb_offset_days) * 86400)
        end = record.record_start_seconds + record.record_length_seconds
        if seconds.lo <= record.record_start_seconds or seconds.hi >= end:
            raise EclipseContinuousLunarUnavailable("reference evaluation left its frozen record")
        x = q(2 * (seconds - record.record_start_seconds) / record.record_length_seconds - 1)

        def axis(coefficients):
            # Simultaneously propagate T_n and dT_n/dx with exact interval
            # recurrence; all dyadic quantization is outward.
            p0, p1, d0, d1 = one, x, zero, one
            position = I.point(coefficients[0])
            deriv = zero
            if len(coefficients) > 1:
                position = q(position + coefficients[1] * p1)
                deriv = q(deriv + coefficients[1] * d1)
            for coefficient in coefficients[2:]:
                p2 = q(2 * x * p1 - p0)
                d2 = q(2 * p1 + 2 * x * d1 - d0)
                position = q(position + coefficient * p2)
                deriv = q(deriv + coefficient * d2)
                p0, p1, d0, d1 = p1, p2, d1, d2
            rate = q(deriv * (2 * 86400 / record.record_length_seconds) * conversion.derivative_tdb_per_tt)
            return position, rate

        axes = tuple(axis(component) for component in record.coefficients)
        return tuple(a[0] for a in axes), tuple(a[1] for a in axes)

    def add(left, right):
        return tuple(q(a + b) for a, b in zip(left, right))

    def sub(left, right):
        return tuple(q(a - b) for a, b in zip(left, right))

    def scale(vector, factor):
        return tuple(q(component * factor) for component in vector)

    def delay(vector, derivative):
        distance = sum((component.square() for component in vector), zero).sqrt(model.precision_bits)
        if distance.lo <= 0:
            raise EclipseContinuousLunarUnavailable("reference light-time norm may vanish")
        speed = Fraction.from_float(C_KM_PER_DAY)
        value = q(distance / speed)
        rate = q(sum((x * y for x, y in zip(vector, derivative)), zero) / (distance * speed))
        if value.lo < 0 or value.hi > model.max_light_delay_days:
            raise EclipseContinuousLunarUnavailable("reference light-time exceeds the frozen emission horizon")
        return value, rate

    try:
        reception = clock(subinterval)
        emb, emb_rate = route((0, 3), reception)
        earth_leg, earth_leg_rate = route((3, 399), reception)
        moon_leg, moon_leg_rate = route((3, 301), reception)
        earth, earth_rate = add(emb, earth_leg), add(emb_rate, earth_leg_rate)
        moon, moon_rate = sub(moon_leg, earth_leg), sub(moon_leg_rate, earth_leg_rate)
        initial, initial_rate = route((0, 10), reception)
        sun, sun_rate = sub(initial, earth), sub(initial_rate, earth_rate)
        current, current_rate = delay(sun, sun_rate)
        for _ in range(10):
            emission = q(subinterval - current)
            emitted, emitted_rate = route((0, 10), clock(emission))
            sun = sub(emitted, earth)
            sun_rate = sub(scale(emitted_rate, one - current_rate), earth_rate)
            current, current_rate = delay(sun, sun_rate)
        return ContinuousLunarVectorBounds(subinterval, sun, moon, sun_rate, moon_rate, tuple(clocks),
                                           raw_record_mid_radius_verified=model.raw_record_mid_radius_verified)
    except (IntervalBudgetError, IntervalDomainError, OverflowError, ZeroDivisionError) as exc:
        raise EclipseContinuousLunarUnavailable("continuous lunar interval budget or domain exhausted") from exc


def certify_continuous_sun_light_time(
    model: ContinuousLunarReference, subinterval: I,
) -> ContinuousSunLightTimeCertificate:
    """Certify a fixed point and finite-iteration error for this model only.

    For each reception epoch, map a delay ``d`` in ``[0, horizon]`` to
    ``|Sun(TT-d)-Earth(TT)|/c``. The copied polynomial and clock enclosures
    cover the entire frozen reception/emission horizon. The distance norm is
    1-Lipschitz even at zero; a Sun speed and clock derivative bound therefore
    give ``q`` for this delay map. Its image must fit in the same horizon and
    ``q`` must be strictly below one. Banach's theorem then guarantees a
    unique fixed point. With x0=0 and x(k+1)=F(xk), the returned tenth-emission
    vector uses x10, so its residual is at most q**10*horizon and its delay
    error at most residual/(1-q). The Sun position error is at most c*q times
    that delay error in each component. These bounds do not establish source
    identity, legacy equivalence, or physical accuracy.
    """
    vectors = enclose_continuous_lunar_reference(model, subinterval)
    records = {(record.center, record.target): record for record in model.records}
    try:
        clock_domain = I(model.tt_offset_days.lo - model.max_light_delay_days,
                         model.tt_offset_days.hi)
        clock = bound_continuous_reference_tdb(
            model.tt_anchor_jd, clock_domain, precision_bits=model.precision_bits,
        )
        reception = bound_continuous_reference_tdb(
            model.tt_anchor_jd, model.tt_offset_days, precision_bits=model.precision_bits,
        )
        speed = Fraction.from_float(C_KM_PER_DAY)

        def frozen_horizon(pair):
            # Derive these enclosures directly from the exact same immutable
            # coefficient tuples evaluated by ``route``. Receipt metadata is
            # informational and cannot override the model's actual values.
            record = records[pair]
            conversion = clock if pair == (0, 10) else reception
            seconds = _raw_seconds(model.tt_anchor_jd, conversion.tdb_offset_days)
            length = record.record_length_seconds
            start = record.record_start_seconds
            if length <= 0 or seconds.lo <= start or seconds.hi >= start + length:
                raise EclipseContinuousLunarUnavailable("reference horizon leaves its frozen record")
            if (len(record.coefficients) != 3 or any(not axis for axis in record.coefficients)
                    or any(not isinstance(c, Fraction) for axis in record.coefficients for c in axis)):
                raise EclipseContinuousLunarUnavailable("reference coefficient tuple is invalid")
            x = 2 * (seconds - start) / length - 1
            positions = tuple(_chebyshev(axis, x) for axis in record.coefficients)
            derivatives = tuple(sum((n * n * abs(c) for n, c in enumerate(axis)), Fraction(0))
                                * 2 / length for axis in record.coefficients)
            speed_squared = sum((value * value for value in derivatives), Fraction(0))
            speed_km_per_second = I.point(speed_squared).sqrt(model.precision_bits).hi
            return positions, speed_km_per_second

        sun, sun_speed = frozen_horizon((0, 10))
        emb, _ = frozen_horizon((0, 3))
        earth_leg, _ = frozen_horizon((3, 399))
        q = sun_speed * 86400 * clock.derivative_tdb_per_tt.hi / speed
        if not 0 <= q < 1:
            raise EclipseContinuousLunarUnavailable("reference light-time contraction is not proved")
        relative = tuple(s - e - leg for s, e, leg in zip(sun, emb, earth_leg))
        squared = sum((component.square() for component in relative), I.point(0))
        image = (squared.sqrt(model.precision_bits) / speed).quantize_outward(model.precision_bits)
        if image.lo < 0 or image.hi > model.max_light_delay_days:
            raise EclipseContinuousLunarUnavailable("reference light-time map is not closed on its horizon")
        residual = q ** 10 * model.max_light_delay_days
        emission_error = residual / (1 - q)
        return ContinuousSunLightTimeCertificate(
            vectors, image, q, residual, emission_error, q * emission_error,
            speed * q * emission_error,
        )
    except (IntervalBudgetError, IntervalDomainError, OverflowError, ZeroDivisionError, KeyError) as exc:
        raise EclipseContinuousLunarUnavailable("reference contraction budget or route unavailable") from exc
