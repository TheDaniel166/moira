"""Conditional serving split TT/TDB enclosure and guarded sine checks."""
from fractions import Fraction
import math
import random
import sys

import pytest

from moira import julian
from moira import _eclipse_time_bounds as time_bounds
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_time_bounds import (
    EclipseTimeBoundsUnavailable,
    bound_serving_single_tdb,
    bound_serving_split_tdb,
)


def _assert_enclosed(anchor, offsets, value):
    envelope = bound_serving_split_tdb(anchor, offsets)
    whole, fraction = julian._tt_to_tdb_split(anchor, value)
    # Compare exact represented binary64 output, not a rounded JD sum.
    relative = Fraction.from_float(whole) + Fraction.from_float(fraction) - Fraction.from_float(float(anchor))
    assert envelope.tdb_offset_days.contains(relative)
    assert envelope.conditional_on_float_model
    assert envelope.maximum_displacement_seconds == Fraction(1, 50)
    assert envelope.final_sine_guard_required
    assert not envelope.source_and_constants_attested
    assert not envelope.native_spk_routing_enclosed
    assert not envelope.native_spk_evaluation_enclosed
    assert not envelope.ut1_enclosed
    assert not envelope.physical_accuracy_certified


def test_conditional_platform_examples_are_binary64():
    # This check prevents accidental tests on a clearly incompatible runtime;
    # it does not prove fsum or the runtime floating-point rounding mode.
    assert sys.float_info.radix == 2
    assert sys.float_info.mant_dig == 53
    assert math.ulp(0.0) == float.fromhex("0x0.0000000000001p-1022")


@pytest.mark.parametrize("anchor,offset", [
    (2451545.0, 0.0),
    (1026285.7107341307, -0.005),
    (0.0, -math.ulp(0.0)),
    (-0.0, math.ulp(0.0)),
    (-1.0, math.nextafter(0.0, -math.inf)),
    (1.0, math.nextafter(-1.0, 0.0)),
    (40000000.0, -0.5),
    (-40000000.0, 0.5),
    (20000000.0, -20000000.0),
    (-20000000.0, 20000000.0),
])
def test_split_output_is_within_twenty_milliseconds_at_adversarial_values(anchor, offset):
    _assert_enclosed(anchor, I.point(offset), offset)


def test_split_output_closed_interval_and_seeded_ranges():
    offsets = I(-0.01, 0.01)
    for index in range(21):
        _assert_enclosed(2459891.9582497696, offsets, -0.01 + index / 1000.0)
    rng = random.Random(673429)
    for _ in range(200):
        anchor = rng.uniform(-39999900.0, 39999900.0)
        offset = rng.uniform(-0.4, 0.4)
        _assert_enclosed(anchor, I.point(offset), offset)


@pytest.mark.parametrize("sine", [-1.0, 1.0])
@pytest.mark.parametrize("anchor,offset", [
    (2451545.0, 0.0), (1026285.7107341307, -0.005),
    (40000000.0, -0.5), (-40000000.0, 0.5),
])
def test_split_twenty_millisecond_envelope_covers_guarded_amplitude_extremes(monkeypatch, sine, anchor, offset):
    monkeypatch.setattr(julian.math, "sin", lambda _: sine)
    _assert_enclosed(anchor, I.point(offset), offset)


def test_split_envelope_can_separate_from_whole_day_boundary():
    anchor = 2451545.0
    offset = float(Fraction(1, 25 * 86400))
    envelope = bound_serving_split_tdb(anchor, I.point(offset))
    assert envelope.tdb_offset_days.lo > 0
    assert envelope.tdb_offset_days.hi * 86400 < Fraction(1, 10)


@pytest.mark.parametrize("amplitude", [float("nan"), float("inf"), 0.01, -0.01])
def test_invalid_split_amplitude_is_unavailable(monkeypatch, amplitude):
    monkeypatch.setattr(time_bounds, "_NAIF_DELTET_K_SECONDS", amplitude)
    with pytest.raises(EclipseTimeBoundsUnavailable, match="amplitude"):
        bound_serving_split_tdb(2451545.0, I.point(0))


def test_normal_guarded_periodic_value_preserves_existing_formula():
    whole, fractional = 2451545.0, 0.2718281828
    whole_seconds = (whole - julian.J2000) * 86400.0
    fractional_seconds = fractional * 86400.0
    mean = math.remainder(math.fsum((
        julian._NAIF_DELTET_M0_RADIANS,
        julian._NAIF_DELTET_M1_RADIANS_PER_SECOND * whole_seconds,
        julian._NAIF_DELTET_M1_RADIANS_PER_SECOND * fractional_seconds,
    )), math.tau)
    eccentric = mean + julian._NAIF_DELTET_EB * math.sin(mean)
    expected = julian._NAIF_DELTET_K_SECONDS * math.sin(eccentric)
    assert julian._naif_tdb_minus_tt_seconds_at_tdb_split(whole, fractional) == expected


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), 1.0000000000000002, -1.0000000000000002])
def test_invalid_final_sine_is_an_error_not_an_enclosure(monkeypatch, invalid):
    calls = []

    def controlled_sine(value):
        calls.append(value)
        return 0.0 if len(calls) == 1 else invalid

    monkeypatch.setattr(julian.math, "sin", controlled_sine)
    with pytest.raises(ArithmeticError, match="sine is outside"):
        julian._naif_tdb_minus_tt_seconds_at_tdb_split(2451545.0, 0.0)


def test_nonconvergent_split_converter_remains_an_error(monkeypatch):
    calls = iter([0.0, 1.0] * 4)
    monkeypatch.setattr(julian, "_naif_tdb_minus_tt_seconds_at_tdb_split", lambda *args: next(calls))
    with pytest.raises(ArithmeticError, match="did not converge"):
        julian._tt_to_tdb_split(2451545.0, 0.0)


def test_replacing_guarded_converter_invalidates_the_declared_premise(monkeypatch):
    envelope = bound_serving_split_tdb(2451545.0, I.point(0))
    monkeypatch.setattr(julian, "_naif_tdb_minus_tt_seconds_at_tdb_split", lambda *args: 100.0)
    whole, fraction = julian._tt_to_tdb_split(2451545.0, 0.0)
    elapsed = Fraction.from_float(whole) + Fraction.from_float(fraction) - 2451545
    assert not envelope.tdb_offset_days.contains(elapsed)
    assert not envelope.source_and_constants_attested


@pytest.mark.parametrize("anchor,offsets", [
    (40000000.0, I.point(1)),
    (-40000000.0, I.point(-1)),
    (2451545.0, I(-40000001, 0)),
])
def test_outside_proof_domain_is_unavailable(anchor, offsets):
    with pytest.raises(EclipseTimeBoundsUnavailable):
        bound_serving_split_tdb(anchor, offsets)


@pytest.mark.parametrize("anchor,offsets", [
    (True, I.point(0)),
    (float("nan"), I.point(0)),
    (float("inf"), I.point(0)),
])
def test_invalid_input_is_an_error(anchor, offsets):
    with pytest.raises(ValueError):
        bound_serving_split_tdb(anchor, offsets)


@pytest.mark.parametrize("tt", [
    -40000000.0, -1.0, -math.ulp(0.0), 0.0, math.ulp(0.0),
    1026285.7107341307, 2459891.9582497696, 2688456.25, 40000000.0,
])
def test_single_part_tdb_encloses_edge_and_representative_epochs(tt):
    bounds = bound_serving_single_tdb(tt, I.point(0))
    actual = julian.tt_to_tdb(tt)
    assert bounds.tdb_offset_days.contains(Fraction.from_float(actual) - Fraction.from_float(tt))
    assert bounds.final_sine_guard_required
    assert not bounds.source_and_constants_attested
    assert not bounds.ut1_enclosed
    assert not bounds.physical_accuracy_certified


def test_single_part_tdb_encloses_closed_interval_and_random_samples():
    anchor = 2459891.9582497696
    bounds = bound_serving_single_tdb(anchor, I(Fraction(-10, 86400), Fraction(10, 86400)))
    for seconds in range(-10, 11):
        tt = anchor + seconds / 86400
        offset = Fraction.from_float(tt) - Fraction.from_float(anchor)
        if bounds.tt_offset_days.contains(offset):
            assert bounds.tdb_offset_days.contains(Fraction.from_float(julian.tt_to_tdb(tt)) - Fraction.from_float(anchor))
    rng = random.Random(5821)
    for _ in range(200):
        tt = rng.uniform(-40000000, 40000000)
        point = bound_serving_single_tdb(tt, I.point(0))
        assert point.tdb_offset_days.contains(Fraction.from_float(julian.tt_to_tdb(tt)) - Fraction.from_float(tt))


def test_normal_single_part_periodic_value_preserves_existing_formula():
    tdb = 2451545.2718281828
    seconds = math.fsum((tdb, -julian.J2000)) * 86400.0
    mean = math.remainder(julian._NAIF_DELTET_M0_RADIANS
                          + julian._NAIF_DELTET_M1_RADIANS_PER_SECOND * seconds, math.tau)
    eccentric = mean + julian._NAIF_DELTET_EB * math.sin(mean)
    assert julian._naif_tdb_minus_tt_seconds_at_tdb(tdb) == julian._NAIF_DELTET_K_SECONDS * math.sin(eccentric)


@pytest.mark.parametrize("invalid", [float("nan"), float("inf"), 1.0000000000000002, -1.0000000000000002])
def test_single_part_invalid_final_sine_fails_closed(monkeypatch, invalid):
    calls = []

    def controlled_sine(value):
        calls.append(value)
        return 0.0 if len(calls) == 1 else invalid

    monkeypatch.setattr(julian.math, "sin", controlled_sine)
    with pytest.raises(ArithmeticError, match="sine is outside"):
        julian._naif_tdb_minus_tt_seconds_at_tdb(2451545.0)


def test_single_part_time_domain_failure_is_unavailable():
    with pytest.raises(EclipseTimeBoundsUnavailable):
        bound_serving_single_tdb(40000000.0, I.point(1))
