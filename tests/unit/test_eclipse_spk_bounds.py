"""Exact type-2 stored-polynomial bounds; not native output certificates."""
from fractions import Fraction
import math
import struct
from types import SimpleNamespace

import pytest

from moira._eclipse_interval import RationalInterval
from moira._eclipse_spk_bounds import (
    EclipseSpkBoundsUnavailable,
    _chebyshev,
    _derivative_upper,
    _raw_seconds,
    _select_descriptor,
    bound_serving_type2_polynomial,
)


def _independent_series(coefficients, x):
    """Forward Chebyshev recurrence, independent of production Clenshaw."""
    terms = [Fraction(1)]
    if len(coefficients) > 1:
        terms.append(x)
    for _ in range(2, len(coefficients)):
        terms.append(2 * x * terms[-1] - terms[-2])
    return sum((Fraction.from_float(c) * t for c, t in zip(coefficients, terms)), Fraction(0))


def _independent_derivative(coefficients, x, record_length):
    """Forward recurrence for dT_n/dx; units km per TDB second."""
    terms, derivatives = [Fraction(1)], [Fraction(0)]
    if len(coefficients) > 1:
        terms.append(x)
        derivatives.append(Fraction(1))
    for _ in range(2, len(coefficients)):
        terms.append(2*x*terms[-1] - terms[-2])
        derivatives.append(2*terms[-2] + 2*x*derivatives[-1] - derivatives[-2])
    return (sum((Fraction.from_float(c) * t for c, t in zip(coefficients, derivatives)), Fraction(0))
            * 2 / record_length)


def test_split_jd_keeps_offset_below_single_jd_ulp():
    offset = Fraction.from_float(1e-15)
    result = _raw_seconds(2451545.0, RationalInterval.point(offset))
    assert 2451545.0 + 1e-15 == 2451545.0
    assert result.lo == result.hi == offset * 86400
    assert result.lo > 0


def test_polynomial_and_n_squared_derivative_bound_independent_recurrence():
    coefficients = (2.0, -0.5, 3.0, 1.25)
    box = RationalInterval(Fraction(-1, 3), Fraction(1, 2))
    bound = _chebyshev(coefficients, box)
    velocity = _derivative_upper(coefficients, Fraction(8))
    for numerator in range(-100, 101):
        x = box.lo + box.width * Fraction(numerator + 100, 200)
        assert bound.contains(_independent_series(coefficients, x))
        assert abs(_independent_derivative(coefficients, x, Fraction(8))) <= velocity


def test_raw_descriptor_priority_and_internal_preemption():
    high = SimpleNamespace(start_second=1.0, end_second=2.0)
    low = SimpleNamespace(start_second=0.0, end_second=3.0)
    assert _select_descriptor((high, low), RationalInterval(Fraction(3, 2), Fraction(7, 4))) is high
    assert _select_descriptor((high, low), RationalInterval(Fraction(0), Fraction(1, 2))) is low
    with pytest.raises(EclipseSpkBoundsUnavailable, match="transition"):
        _select_descriptor((high, low), RationalInterval(Fraction(0), Fraction(3)))
    with pytest.raises(EclipseSpkBoundsUnavailable, match="transition"):
        _select_descriptor((high, low), RationalInterval(Fraction(0), Fraction(1)))
    with pytest.raises(EclipseSpkBoundsUnavailable, match="covers"):
        _select_descriptor((high, low), RationalInterval(Fraction(4), Fraction(5)))


def test_priority_uses_exact_binary64_descriptor_not_rounded_jd():
    boundary = 1.0
    low = SimpleNamespace(start_second=0.0, end_second=3.0)
    high = SimpleNamespace(start_second=boundary, end_second=2.0)
    just_before = Fraction.from_float(math.nextafter(boundary, -math.inf))
    assert _select_descriptor((high, low), RationalInterval.point(just_before)) is low
    assert _select_descriptor((high, low), RationalInterval.point(boundary)) is high


def test_unsupported_backend_never_returns_polynomial_bounds():
    with pytest.raises(EclipseSpkBoundsUnavailable, match="other backends"):
        bound_serving_type2_polynomial(object(), 0, 3, 2451545.0, RationalInterval.point(0))


@pytest.mark.requires_ephemeris
def test_de441_exact_polynomial_and_velocity_enclosed(planetary_reader):
    reader = planetary_reader
    interval = RationalInterval(Fraction(-1, 86400), Fraction(1, 86400))
    result = bound_serving_type2_polynomial(reader, 0, 3, 2451545.0, interval)
    assert result.frame_id == 1
    assert result.source_sha256_at_reader_open == reader._source_identity.sha256
    assert len(result.copied_records_sha256) == 64
    repeated = bound_serving_type2_polynomial(reader, 0, 3, 2451545.0, interval)
    assert repeated.copied_records_sha256 == result.copied_records_sha256
    assert not result.native_routing_enclosed and not result.native_evaluation_enclosed
    assert not result.time_conversion_enclosed and not result.light_time_enclosed
    segment = reader._segment_for_tdb(0, 3, 2451545.0)
    evaluator = segment._load_native_evaluator()
    init, duration, _count, _, _ = evaluator.chebyshev_metadata()
    start = Fraction.from_float(init)
    length = Fraction.from_float(duration)
    for seconds in (Fraction(-1), Fraction(0), Fraction(1)):
        index = (seconds - start) // length
        record = evaluator.chebyshev_records(index, 1)[0]
        x = 2 * (seconds - start - index * length) / length - 1
        for component in range(3):
            assert result.position_km[component].contains(_independent_series(record[component], x))
            derivative = _independent_derivative(record[component], x, length)
            assert abs(derivative) <= result.velocity_component_abs_km_per_second[component]
    assert result.speed_upper_km_per_second**2 >= sum(
        v**2 for v in result.velocity_component_abs_km_per_second
    )


@pytest.mark.requires_ephemeris
def test_de441_exact_internal_record_join_retains_both_records(planetary_reader):
    segment = planetary_reader._segment_for_tdb(0, 3, 2451545.0)
    init, duration, count, _, _ = segment._load_native_evaluator().chebyshev_metadata()
    start, length = Fraction.from_float(init), Fraction.from_float(duration)
    index = (-start) // length
    assert 0 < index < count
    seam = start + index * length
    result = bound_serving_type2_polynomial(
        planetary_reader, 0, 3, 2451545.0, RationalInterval.point(seam / 86400)
    )
    assert result.record_indices == (index - 1, index)


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("jd_tdb", [1026285.7107341307, 2451545.0])
@pytest.mark.parametrize("center,target", [(0, 3), (0, 10), (3, 301), (3, 399)])
def test_de441_raw_daf_record_enclosed_independently(
    planetary_reader, planetary_kernel_path, jd_tdb, center, target,
):
    """Raw same-DE441 forward recurrence is numerical, not physical, evidence."""
    interval = RationalInterval(Fraction(-1, 86400), Fraction(1, 86400))
    result = bound_serving_type2_polynomial(planetary_reader, center, target, jd_tdb, interval)
    segment = planetary_reader._segment_for_tdb(center, target, jd_tdb)
    endian = "<" if segment._little_endian else ">"
    epoch_seconds = (Fraction.from_float(jd_tdb) - 2451545) * 86400
    with open(planetary_kernel_path, "rb") as stream:
        stream.seek((int(segment.end_i) - 4) * 8)
        init, duration, raw_size, raw_count = struct.unpack(endian + "4d", stream.read(32))
        record_size, count = int(raw_size), int(raw_count)
        index = (epoch_seconds - Fraction.from_float(init)) // Fraction.from_float(duration)
        assert 0 <= index < count
        stream.seek((int(segment.start_i) - 1 + index * record_size) * 8)
        record = struct.unpack(endian + str(record_size) + "d", stream.read(record_size * 8))
    assert record[0] == init + (index + 0.5) * duration
    assert record[1] == duration / 2
    coefficients_per_component = (record_size - 2) // 3
    raw_x = (epoch_seconds - Fraction.from_float(record[0])) / Fraction.from_float(record[1])
    assert -1 <= raw_x <= 1
    for component in range(3):
        start = 2 + component * coefficients_per_component
        coefficients = record[start:start + coefficients_per_component]
        assert result.position_km[component].contains(_independent_series(coefficients, raw_x))
        assert abs(_independent_derivative(coefficients, raw_x, Fraction.from_float(duration))) <= result.velocity_component_abs_km_per_second[component]


@pytest.mark.requires_ephemeris
def test_record_budget_and_missing_pair_fail_closed(planetary_reader):
    with pytest.raises(EclipseSpkBoundsUnavailable, match="budget"):
        bound_serving_type2_polynomial(
            planetary_reader, 0, 3, 2451545.0, RationalInterval(-30, 30), max_records=1
        )
    with pytest.raises(EclipseSpkBoundsUnavailable, match="pair unavailable"):
        bound_serving_type2_polynomial(planetary_reader, 123456, 654321, 2451545.0, RationalInterval.point(0))


@pytest.mark.requires_ephemeris
def test_type3_descriptor_and_missing_record_accessor_fail_closed(planetary_reader, monkeypatch):
    candidate = SimpleNamespace(start_second=-100.0, end_second=100.0, data_type=3,
                                frame=1, start_i=1, end_i=2)
    monkeypatch.setattr(planetary_reader, "_segments_for_pair", lambda center, target: (candidate,))
    with pytest.raises(EclipseSpkBoundsUnavailable, match="not SPK type 2"):
        bound_serving_type2_polynomial(planetary_reader, 0, 3, 2451545.0, RationalInterval.point(0))
    candidate.data_type = 2
    with pytest.raises(EclipseSpkBoundsUnavailable, match="accessor unavailable"):
        bound_serving_type2_polynomial(planetary_reader, 0, 3, 2451545.0, RationalInterval.point(0))
