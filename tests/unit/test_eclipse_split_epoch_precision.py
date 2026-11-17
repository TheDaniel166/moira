"""Raw-record checks of reception light time at represented TT epochs.

The oracle uses 70-digit arithmetic and a forward Chebyshev recurrence on
the same DE441 coefficients, not a second physical ephemeris. TT is already
binary64 and the pinned TT/TDB periodic phase is evaluated in binary64.
"""
from decimal import Decimal, ROUND_FLOOR, localcontext
import math
import struct

import pytest

from moira.eclipse import EclipseCalculator, _eclipse_body_pair
from moira.eclipse_canon import _lunar_canon_vectors_tt
from moira.corrections import apply_aberration
from moira.julian import _naif_tdb_minus_tt_seconds_at_tdb, tt_to_tdb
from moira.planets import _earth_barycentric_state_at_tt_offset
from moira.spk_reader import KernelPool, _SplitEpochUnsupported


D = Decimal.from_float
DAY = Decimal(86400)


def _raw_position(stream, segment, first, second):
    """Evaluate a type-2 DAF record without the production evaluator."""
    endian = "<" if segment._little_endian else ">"
    stream.seek((int(segment.end_i) - 4) * 8)
    init, interval, size, count = struct.unpack(endian + "4d", stream.read(32))
    size, count = int(size), int(count)
    assert segment.data_type == 2 and (size - 2) % 3 == 0
    et = ((Decimal(first) - Decimal(2451545)) + second) * DAY
    index = int(((et - D(init)) / D(interval)).to_integral_value(rounding=ROUND_FLOOR))
    if index == count and et == D(init) + D(interval) * count:
        index -= 1
    assert 0 <= index < count
    stream.seek((int(segment.start_i) - 1 + index * size) * 8)
    record = struct.unpack(endian + str(size) + "d", stream.read(size * 8))
    x = (et - D(record[0])) / D(record[1])
    assert abs(x) <= Decimal("1.00000000000000000001")
    n = (size - 2) // 3
    output = []
    for axis in range(3):
        coefficients = record[2 + axis * n:2 + (axis + 1) * n]
        previous, current = Decimal(1), x
        value = D(coefficients[0])
        if n > 1:
            value += D(coefficients[1]) * current
        for coefficient in coefficients[2:]:
            previous, current = current, 2 * x * current - previous
            value += D(coefficient) * current
        output.append(value)
    return output


def _state(reader, stream, pair, tt):
    # Same pinned time-scale model; its slow phase is rounded only once.
    rounded = float(tt)
    correction = _naif_tdb_minus_tt_seconds_at_tdb(tt_to_tdb(rounded))
    tdb = tt + D(correction) / DAY
    first = int(tdb.to_integral_value(rounding=ROUND_FLOOR))
    second = tdb - Decimal(first)
    segment = reader._segment_for_tdb(*pair, float(first), offset_days=float(second))
    return _raw_position(stream, segment, first, second)


def _add(a, b):
    return [x + y for x, y in zip(a, b)]


def _sub(a, b):
    return [x - y for x, y in zip(a, b)]


def _norm(a):
    return sum(x * x for x in a).sqrt()


def _reference(reader, stream, tt):
    earth = _add(_state(reader, stream, (0, 3), tt), _state(reader, stream, (3, 399), tt))
    result = []
    for pair in ((0, 10), (3, 301)):
        def body(epoch):
            value = _state(reader, stream, pair, epoch)
            return _add(_state(reader, stream, (0, 3), epoch), value) if pair == (3, 301) else value

        delay = _norm(_sub(body(tt), earth)) / Decimal("299792.458")
        for _ in range(12):
            xyz = _sub(body(tt - delay / DAY), earth)
            next_delay = _norm(xyz) / Decimal("299792.458")
            if abs(next_delay - delay) < Decimal("1e-12"):
                break
            delay = next_delay
        else:
            raise AssertionError("reference light time did not converge")
        result.append(xyz)
    return result


def _nearby_python_records(segment, path, tt):
    """Load only the records needed by this test, in Python evaluator order."""
    endian = "<" if segment._little_endian else ">"
    with open(path, "rb") as stream:
        stream.seek((int(segment.end_i) - 4) * 8)
        init, interval, size, count = struct.unpack(endian + "4d", stream.read(32))
        size, count = int(size), int(count)
        seconds = (tt - 2451545.0) * 86400.0
        first = max(0, math.floor((seconds - 1000.0 - init) / interval))
        last = min(count - 1, math.floor((seconds + 1000.0 - init) / interval))
        n = (size - 2) // 3
        records = []
        for index in range(first, last + 1):
            stream.seek((int(segment.start_i) - 1 + index * size) * 8)
            record = struct.unpack(endian + str(size) + "d", stream.read(size * 8))
            records.append(tuple(tuple(reversed(record[2 + axis * n:2 + (axis + 1) * n]))
                                 for axis in range(3)))
    return init + first * interval, interval, records


@pytest.mark.parametrize("tt", [1026285.7107341307, 2460409.262])
@pytest.mark.parametrize("backend", ["native", "python"])
def test_retarded_solar_shadow_vectors_match_raw_decimal(
    planetary_reader, planetary_kernel_path, tt, backend, monkeypatch
):
    calculator = EclipseCalculator(reader=planetary_reader)
    if backend == "python":
        for pair in ((0, 3), (3, 399), (0, 10), (3, 301)):
            segment = planetary_reader._segment_for_tdb(*pair, tt)
            records = _nearby_python_records(segment, planetary_kernel_path, tt)
            monkeypatch.setattr(segment, "_handle", None)
            monkeypatch.setattr(segment, "_load_native_evaluator", lambda: None)
            monkeypatch.setattr(segment, "_data", records)
    with localcontext() as context, open(planetary_kernel_path, "rb") as stream:
        context.prec = 70
        for offset in (-2.0, 0.0, 2.0):
            sample = tt + offset / 86400.0
            expected_sun, expected_moon = _reference(planetary_reader, stream, D(sample))
            actual = calculator._native_solar_shadow_axis_state_tt(sample)
            for value, expected in ((actual.sun_xyz_km, expected_sun), (actual.moon_xyz_km, expected_moon)):
                error_km = math.sqrt(sum(float(D(a) - e) ** 2 for a, e in zip(value, expected)))
                assert error_km < 1e-6  # 1 mm, including binary64 position summation


@pytest.mark.parametrize("tt", [1026285.7107341307, 2460409.262])
def test_lunar_canon_policies_keep_geometry_and_precision(
    planetary_reader, planetary_kernel_path, tt
):
    calculator = EclipseCalculator(reader=planetary_reader)
    with localcontext() as context, open(planetary_kernel_path, "rb") as stream:
        context.prec = 70
        epoch = D(tt)
        sun_retarded, moon_retarded = _reference(planetary_reader, stream, epoch)
        earth = _add(_state(planetary_reader, stream, (0, 3), epoch),
                     _state(planetary_reader, stream, (3, 399), epoch))
        sun_geometric = _sub(_state(planetary_reader, stream, (0, 10), epoch), earth)
        moon_geometric = _sub(_state(planetary_reader, stream, (3, 301), epoch),
                              _state(planetary_reader, stream, (3, 399), epoch))
        _, velocity = _earth_barycentric_state_at_tt_offset(tt, 0.0, planetary_reader)
        apparent_sun = apply_aberration(tuple(map(float, sun_retarded)), velocity)
        apparent_moon = apply_aberration(tuple(map(float, moon_retarded)), velocity)
        policies = (
            ("nasa_shadow_axis_geometric_moon", sun_geometric, moon_geometric),
            ("nasa_shadow_axis_retarded_moon", sun_geometric, moon_retarded),
            ("nasa_shadow_axis_apparent_sun_moon", apparent_sun, apparent_moon),
        )
        for method, expected_sun, expected_moon in policies:
            actual = _lunar_canon_vectors_tt(calculator, tt, method=method)
            for value, expected in zip(actual, (expected_sun, expected_moon)):
                error_km = math.sqrt(sum((a - float(e)) ** 2 for a, e in zip(value, expected)))
                assert error_km < 1e-6


def test_ancient_shadow_objective_tracks_raw_decimal_samples(planetary_reader, planetary_kernel_path):
    """Exercise the previously noisy -48264 window, including its local minimum."""
    calculator = EclipseCalculator(reader=planetary_reader)
    actual_values, expected_values = [], []
    with localcontext() as context, open(planetary_kernel_path, "rb") as stream:
        context.prec = 70
        for index in range(-100, 101):
            tt = 1026285.7107341307 + (index / 10.0) / 86400.0
            sun, moon = _reference(planetary_reader, stream, D(tt))
            axis = _sub(moon, sun)
            projection = sum(x * y for x, y in zip(moon, axis)) / _norm(axis)
            expected = (sum(x * x for x in moon) - projection * projection).sqrt()
            actual = calculator._native_solar_shadow_axis_state_tt(tt).axis_distance_km
            assert abs(actual - float(expected)) < 1e-6
            actual_values.append(actual)
            expected_values.append(float(expected))
    for values in (actual_values, expected_values):
        minima = sum(values[i] < values[i - 1] and values[i] < values[i + 1]
                     for i in range(1, len(values) - 1))
        assert minima == 1


@pytest.mark.parametrize("lunation,tt", [
    (-48840, 1009276.276767078),
    (-48582, 1016895.7618307451),
    (-48264, 1026285.7107341307),
    (-30916, 1538582.439889415),
    (42, 2452790.6731771156),
    (300, 2460409.2628400046),
    (546, 2467674.3504569237),
])
def test_solar_shadow_minimum_is_repeatable_from_overlapping_brackets(planetary_reader, lunation, tt):
    """Repeat the prior seven-event, three-seed local-minimum experiment."""
    calculator = EclipseCalculator(reader=planetary_reader)
    with localcontext() as context:
        context.prec = 70
        anchor = D(tt)
        ratio = (Decimal(5).sqrt() - 1) / 2

        def objective(seconds):
            represented_tt = float(anchor + seconds / DAY)
            return calculator._native_solar_shadow_axis_state_tt(represented_tt).axis_distance_km

        def minimize(seed):
            left, right = Decimal(seed) - 180, Decimal(seed) + 180
            x1, x2 = right - ratio * (right - left), left + ratio * (right - left)
            f1, f2 = objective(x1), objective(x2)
            while right - left > Decimal("0.01"):
                if f1 <= f2:
                    right, x2, f2 = x2, x1, f1
                    x1 = right - ratio * (right - left)
                    f1 = objective(x1)
                else:
                    left, x1, f1 = x1, x2, f2
                    x2 = left + ratio * (right - left)
                    f2 = objective(x2)
            return float((left + right) / 2)

        minima = [minimize(seed) for seed in (-120, 0, 120)]
        spread = max(minima) - min(minima)
        print(f"lunation={lunation} seed_minima_s={minima} spread_s={spread:.9f}")
        assert spread < 0.1


def test_legacy_reader_inside_pool_retains_eclipse_and_canon_support(planetary_reader):
    """Pool capability must not turn the established reader protocol into an error."""
    class LegacyReader:
        def position(self, *args):
            return planetary_reader.position(*args)

        def position_and_velocity(self, *args):
            return planetary_reader.position_and_velocity(*args)

        def has_segment(self, *args):
            return planetary_reader.has_segment(*args)

        def has_segment_at(self, *args):
            return planetary_reader.has_segment_at(*args)

        def coverage(self):
            return planetary_reader.coverage()

        def covered_bodies(self):
            return planetary_reader.covered_bodies()

        def close(self):
            pass  # The shared fixture owns the underlying handle.

    legacy = LegacyReader()
    direct = EclipseCalculator(reader=legacy)
    pooled = EclipseCalculator(reader=KernelPool([legacy]))
    tt = 1026285.7107341307
    a = direct._native_solar_shadow_axis_state_tt(tt)
    b = pooled._native_solar_shadow_axis_state_tt(tt)
    assert b.sun_xyz_km == pytest.approx(a.sun_xyz_km, rel=0.0, abs=1e-7)
    assert b.moon_xyz_km == pytest.approx(a.moon_xyz_km, rel=0.0, abs=1e-7)
    for method in ("nasa_shadow_axis_geometric_moon", "nasa_shadow_axis_retarded_moon",
                   "nasa_shadow_axis_apparent_sun_moon"):
        expected = _lunar_canon_vectors_tt(direct, tt, method=method)
        actual = _lunar_canon_vectors_tt(pooled, tt, method=method)
        for got, want in zip(actual, expected):
            assert got == pytest.approx(want, rel=0.0, abs=1e-7)

    class EarthOnly(LegacyReader):
        pairs = {(0, 3), (3, 399)}

        def coverage(self):
            return {pair: interval for pair, interval in super().coverage().items() if pair in self.pairs}

        def has_segment(self, center, target):
            return (center, target) in self.pairs and super().has_segment(center, target)

        def has_segment_at(self, center, target, epoch):
            return (center, target) in self.pairs and super().has_segment_at(center, target, epoch)

        def covered_bodies(self):
            return frozenset((3, 399))

    # The first reader has Earth legs only; the native second reader supplies
    # the Sun and Moon. A split Sun must not be mixed with a rounded Earth.
    mixed = EclipseCalculator(reader=KernelPool([EarthOnly(), planetary_reader]))
    mixed_state = mixed._native_solar_shadow_axis_state_tt(tt)
    assert mixed_state.sun_xyz_km == pytest.approx(a.sun_xyz_km, rel=0.0, abs=1e-7)
    assert mixed_state.moon_xyz_km == pytest.approx(a.moon_xyz_km, rel=0.0, abs=1e-7)

    class EarthWithTdbCoverage(EarthOnly):
        def coverage_intervals_tdb(self, center, target):
            if (center, target) not in self.pairs:
                return ()
            return planetary_reader.coverage_intervals_tdb(center, target)

        def has_segment_at_tdb(self, center, target, epoch):
            return (center, target) in self.pairs and planetary_reader.has_segment_at_tdb(center, target, epoch)

        def position(self, center, target, epoch):
            value = super().position(center, target, epoch)
            return (value[0] + 1.0, value[1], value[2])

    prioritized = KernelPool([EarthWithTdbCoverage(), planetary_reader])
    class LegacyPoolView:
        def __getattr__(self, name):
            if name.startswith("_"):
                raise AttributeError(name)
            return getattr(prioritized, name)

    expected = _eclipse_body_pair(tt, LegacyPoolView(), sun_retarded=True, moon_retarded=True)
    actual = _eclipse_body_pair(tt, prioritized, sun_retarded=True, moon_retarded=True)
    for got, want in zip(actual, expected):
        assert got == pytest.approx(want, rel=0.0, abs=1e-10)
    assert abs(actual[0][0] - a.sun_xyz_km[0]) > 0.5


@pytest.mark.parametrize("unsupported", [(0, 3), (0, 10), (3, 301)])
def test_partial_split_capability_falls_back_for_whole_observable(planetary_reader, unsupported):
    class LegacyReader:
        def __getattr__(self, name):
            if name.startswith("_"):
                raise AttributeError(name)
            return getattr(planetary_reader, name)

    class PartialReader(LegacyReader):
        def _position_tdb_offset(self, center, target, first, second):
            if (center, target) == unsupported:
                raise _SplitEpochUnsupported("test reader cannot split this leg")
            return planetary_reader._position_tdb_offset(center, target, first, second)

    legacy = LegacyReader()
    partial = PartialReader()
    tt = 1026285.7107341307
    for sun_retarded, moon_retarded in ((True, True), (True, False), (False, True), (False, False)):
        expected = _eclipse_body_pair(tt, legacy, sun_retarded=sun_retarded, moon_retarded=moon_retarded)
        actual = _eclipse_body_pair(tt, partial, sun_retarded=sun_retarded, moon_retarded=moon_retarded)
        for got, want in zip(actual, expected):
            assert got == pytest.approx(want, rel=0.0, abs=1e-10)
    for method in ("nasa_shadow_axis_geometric_moon", "nasa_shadow_axis_retarded_moon"):
        expected = _lunar_canon_vectors_tt(EclipseCalculator(reader=legacy), tt, method=method)
        actual = _lunar_canon_vectors_tt(EclipseCalculator(reader=partial), tt, method=method)
        for got, want in zip(actual, expected):
            assert got == pytest.approx(want, rel=0.0, abs=1e-10)


def test_unrelated_not_implemented_error_is_not_hidden(planetary_reader):
    class BrokenReader:
        def _position_tdb_offset(self, *args):
            raise NotImplementedError("reader failed internally")

        def _position_and_velocity_tdb_offset(self, *args):
            raise NotImplementedError("reader failed internally")

        def __getattr__(self, name):
            return getattr(planetary_reader, name)

    reader = BrokenReader()
    tt = 1026285.7107341307
    with pytest.raises(NotImplementedError, match="reader failed internally"):
        _eclipse_body_pair(tt, reader, sun_retarded=True, moon_retarded=True)
    for method in ("nasa_shadow_axis_geometric_moon", "nasa_shadow_axis_retarded_moon",
                   "nasa_shadow_axis_apparent_sun_moon"):
        with pytest.raises(NotImplementedError, match="reader failed internally"):
            _lunar_canon_vectors_tt(EclipseCalculator(reader=reader), tt, method=method)
