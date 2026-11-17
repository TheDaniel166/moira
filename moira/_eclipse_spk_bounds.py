"""Exact stored-polynomial bounds for bounded SPK type-2 eclipse research.

Input epochs are a split TDB Julian day and a closed interval of TDB day
offsets.  All coordinates and polynomial coefficients are treated as the
exact rational values represented by their stored binary64 words.  The
adapter borrows an already-open ``SpkReader`` and reads only bounded records
from its native evaluator; it never reopens or eagerly loads an SPK segment.

These enclosures do not bound the rounded native evaluator, its floating-point
descriptor routing, a time-scale conversion, or iterative light-time.  They
are not, by themselves, an eclipse certificate or a physical error bound.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import math
import struct

from ._eclipse_interval import RationalInterval
from ._eclipse_interval_roots import EnclosureUnavailable
from .spk_reader import SpkReader


class EclipseSpkBoundsUnavailable(EnclosureUnavailable):
    """The requested source, route, records, or resource budget is unsupported."""


@dataclass(frozen=True, slots=True)
class Type2PolynomialBounds:
    """Exact bounds on selected stored polynomials, not on native execution.

    ``position_km`` is a box containing the exact uniform-INIT/INTLEN position polynomial on the
    requested TDB interval. ``velocity_component_abs_km_per_second`` bounds
    each component's absolute derivative; ``speed_upper_km_per_second`` is
    the upper endpoint of an exact rational square-root enclosure.  Priority
    is interpreted from raw binary64 descriptor seconds as exact rationals;
    the native floating-point descriptor routing and evaluation are not
    enclosed by this product. The source hash is the reader's open-time
    identity, not a live-file-integrity check. The record hash identifies the
    copied coefficient and metadata words and the exact selected descriptor;
    raw per-record MID/RADIUS words are not read or verified by this adapter.
    """

    center: int
    target: int
    frame_id: int
    source_sha256_at_reader_open: str
    copied_records_sha256: str
    descriptor_start_second: Fraction
    descriptor_end_second: Fraction
    interval_seconds_tdb: RationalInterval
    record_indices: tuple[int, ...]
    position_km: tuple[RationalInterval, RationalInterval, RationalInterval]
    velocity_component_abs_km_per_second: tuple[Fraction, Fraction, Fraction]
    speed_upper_km_per_second: Fraction
    native_routing_enclosed: bool = False
    native_evaluation_enclosed: bool = False
    time_conversion_enclosed: bool = False
    light_time_enclosed: bool = False


def _raw_seconds(jd_tdb: float, offset_days: RationalInterval) -> RationalInterval:
    """Convert represented split TDB values without summing Julian day parts."""
    if isinstance(jd_tdb, bool) or not isinstance(jd_tdb, (int, float)):
        raise ValueError("TDB Julian-day anchor must be a finite real number")
    if not math.isfinite(jd_tdb):
        raise ValueError("TDB Julian-day anchor must be a finite real number")
    return (RationalInterval.point(jd_tdb) - 2451545 + offset_days) * 86400


def _descriptor_interval(segment) -> RationalInterval:
    try:
        start, end = float(segment.start_second), float(segment.end_second)
    except (AttributeError, TypeError, ValueError, OverflowError) as exc:
        raise EclipseSpkBoundsUnavailable("raw descriptor seconds unavailable") from exc
    if not math.isfinite(start) or not math.isfinite(end) or start > end:
        raise EclipseSpkBoundsUnavailable("invalid raw descriptor seconds")
    return RationalInterval(start, end)


def _select_descriptor(segments, seconds: RationalInterval):
    """Select exact raw descriptor priority or demand a domain split.

    Segments are supplied in descending priority. A higher-priority segment
    touching only part of this closed interval forces subdivision, including
    when it touches a single endpoint. Lower-priority overlap after the
    selected full-interval descriptor cannot preempt it.
    """
    for segment in segments:
        span = _descriptor_interval(segment)
        if span.hi < seconds.lo or span.lo > seconds.hi:
            continue
        if span.lo <= seconds.lo and seconds.hi <= span.hi:
            return segment
        raise EclipseSpkBoundsUnavailable("descriptor priority or coverage transition requires split")
    raise EclipseSpkBoundsUnavailable("no descriptor covers the requested interval")


def _chebyshev(coefficients, x: RationalInterval) -> RationalInterval:
    """Enclose an ascending-degree Chebyshev series by exact Clenshaw algebra."""
    if not coefficients or x.lo < -1 or x.hi > 1:
        raise EclipseSpkBoundsUnavailable("invalid Chebyshev coefficients or normalized domain")
    first = second = RationalInterval.point(0)
    for coefficient in reversed(coefficients[1:]):
        first, second = 2 * x * first - second + coefficient, first
    return x * first - second + coefficients[0]


def _derivative_upper(coefficients, record_length: Fraction) -> Fraction:
    """Use |T'_n(x)| <= n² on [-1, 1], with time measured in seconds."""
    return sum((n * n * abs(Fraction.from_float(float(c)))
                for n, c in enumerate(coefficients)), Fraction(0)) * 2 / record_length


def bound_serving_type2_polynomial(
    reader: SpkReader,
    center: int,
    target: int,
    jd_tdb: float,
    offset_days: RationalInterval,
    *,
    max_records: int = 256,
) -> Type2PolynomialBounds:
    """Bound stored type-2 polynomials on an exact split-TDB interval.

    Only a direct pair from a concrete ``SpkReader`` is currently supported;
    pooled, synthetic, arbitrary-reader and indirect body routes fail closed.
    A selected descriptor or priority transition is returned as unavailable
    instead of being silently crossed. The caller retains and owns the reader.
    This function does not certify native output or physical eclipse geometry.
    """
    if type(reader) is not SpkReader:
        raise EclipseSpkBoundsUnavailable("exact SpkReader required; other backends are unsupported")
    if isinstance(center, bool) or not isinstance(center, int) or isinstance(target, bool) or not isinstance(target, int):
        raise ValueError("center and target must be integer NAIF identifiers")
    if type(max_records) is not int or not 1 <= max_records <= 256:
        raise ValueError("max_records must be an integer from 1 to 256")
    if not isinstance(offset_days, RationalInterval):
        raise TypeError("offset_days must be a RationalInterval in TDB days")
    seconds = _raw_seconds(jd_tdb, offset_days)
    try:
        segments = reader._segments_for_pair(center, target)
    except KeyError as exc:
        raise EclipseSpkBoundsUnavailable("direct SPK pair unavailable") from exc
    segment = _select_descriptor(segments, seconds)
    if segment.data_type != 2:
        raise EclipseSpkBoundsUnavailable("selected descriptor is not SPK type 2")
    try:
        frame_id, start_word, end_word = int(segment.frame), int(segment.start_i), int(segment.end_i)
    except (AttributeError, TypeError, ValueError, OverflowError) as exc:
        raise EclipseSpkBoundsUnavailable("descriptor frame or address provenance unavailable") from exc
    loader = getattr(segment, "_load_native_evaluator", None)
    if not callable(loader):
        raise EclipseSpkBoundsUnavailable("native bounded-record accessor unavailable")
    evaluator = loader()
    if evaluator is None or not callable(getattr(evaluator, "chebyshev_metadata", None)) or not callable(getattr(evaluator, "chebyshev_records", None)):
        raise EclipseSpkBoundsUnavailable("native bounded-record accessor unavailable")
    init_float, length_float, count, components, coefficient_count = evaluator.chebyshev_metadata()
    if (not math.isfinite(init_float) or not math.isfinite(length_float) or length_float <= 0
            or type(count) is not int or count < 1 or components != 3
            or type(coefficient_count) is not int or not 1 <= coefficient_count <= 256):
        raise EclipseSpkBoundsUnavailable("unsupported type-2 record layout")
    init, length = Fraction.from_float(init_float), Fraction.from_float(length_float)
    end = init + count * length
    if seconds.lo < init or seconds.hi > end:
        raise EclipseSpkBoundsUnavailable("requested interval lies outside type-2 records")
    first = (seconds.lo - init) // length
    if first > 0 and seconds.lo == init + first * length:
        first -= 1  # Conservatively retain both records at exact joins.
    last = min(count - 1, (seconds.hi - init) // length)
    if first < 0 or first > last or last - first + 1 > max_records:
        raise EclipseSpkBoundsUnavailable("record interval exceeds budget; subdivide")

    position_boxes: list[tuple[RationalInterval, ...]] = []
    max_derivative = [Fraction(0), Fraction(0), Fraction(0)]
    descriptor = _descriptor_interval(segment)
    digest = hashlib.sha256()
    digest.update(b"moira-eclipse-type2-copied-records-v1\0")
    digest.update(f"{center} {target} {frame_id} {start_word} {end_word} {count} {components} {coefficient_count}\n".encode("ascii"))
    digest.update(struct.pack("<4d", float(segment.start_second), float(segment.end_second), init_float, length_float))
    for index in range(first, last + 1):
        record = evaluator.chebyshev_records(index, 1)[0]
        if len(record) != 3 or any(len(component) != coefficient_count for component in record):
            raise EclipseSpkBoundsUnavailable("inconsistent type-2 record layout")
        if not all(math.isfinite(value) for component in record for value in component):
            raise EclipseSpkBoundsUnavailable("non-finite type-2 coefficient")
        digest.update(f"{index}\n".encode("ascii"))
        for component in record:
            for coefficient in component:
                digest.update(struct.pack("<d", coefficient))
        start = init + index * length
        overlap = seconds.intersect(RationalInterval(start, start + length))
        if overlap is None:
            raise EclipseSpkBoundsUnavailable("record selection did not overlap requested interval")
        normalized = 2 * (overlap - start) / length - 1
        position_boxes.append(tuple(_chebyshev(component, normalized) for component in record))
        for component in range(3):
            max_derivative[component] = max(max_derivative[component], _derivative_upper(record[component], length))

    positions = tuple(RationalInterval(min(row[i].lo for row in position_boxes),
                                       max(row[i].hi for row in position_boxes)) for i in range(3))
    speed_squared = sum((value * value for value in max_derivative), Fraction(0))
    speed_upper = RationalInterval.point(speed_squared).sqrt().hi
    identity = getattr(reader, "_source_identity", None)
    source_hash = getattr(identity, "sha256", None)
    if not isinstance(source_hash, str) or not source_hash:
        raise EclipseSpkBoundsUnavailable("source hash unavailable")
    return Type2PolynomialBounds(
        center, target, frame_id, source_hash, digest.hexdigest(), descriptor.lo, descriptor.hi, seconds,
        tuple(range(first, last + 1)), positions, tuple(max_derivative), speed_upper,
    )
