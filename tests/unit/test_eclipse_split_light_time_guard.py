"""Fail-closed norm guards on the split light-time iteration only."""
import math
import sys

import pytest

from moira import corrections


def _iterate(geometric, emission, *, guarded=True):
    return corrections._iterate_light_time((0.0, 0.0, 0.0), geometric, emission, guard_norm=guarded)


@pytest.mark.parametrize("bad_norm", [float("nan"), float("inf"), -1.0, 3.0])
def test_bad_norm_is_rejected_in_split_path(monkeypatch, bad_norm):
    monkeypatch.setattr(corrections, "vec_norm", lambda xyz: bad_norm)
    with pytest.raises(ArithmeticError, match="split light-time norm"):
        _iterate((1.0, 0.0, 0.0), lambda delay: (1.0, 0.0, 0.0))


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_vector_is_rejected(bad):
    with pytest.raises(ArithmeticError, match="vector must be finite"):
        _iterate((bad, 0.0, 0.0), lambda delay: (1.0, 0.0, 0.0))


@pytest.mark.parametrize("bad_c", [0.0, -1.0, float("nan"), float("inf"), True])
def test_invalid_speed_constant_is_rejected(monkeypatch, bad_c):
    monkeypatch.setattr(corrections, "C_KM_PER_DAY", bad_c)
    with pytest.raises(ArithmeticError, match="speed of light"):
        _iterate((1.0, 0.0, 0.0), lambda delay: (1.0, 0.0, 0.0))


def test_finite_but_tiny_speed_cannot_produce_an_infinite_delay(monkeypatch):
    monkeypatch.setattr(corrections, "C_KM_PER_DAY", math.ulp(0.0))
    with pytest.raises(ArithmeticError, match="delay must be finite"):
        _iterate((1.0, 0.0, 0.0), lambda delay: (1.0, 0.0, 0.0))


def test_zero_signed_zero_and_subnormal_are_admitted():
    for value in (0.0, -0.0, math.ulp(0.0), -math.ulp(0.0)):
        xyz, delay = _iterate((value, 0.0, 0.0), lambda delay: (value, 0.0, 0.0))
        assert xyz[0] == value
        assert delay == 0.0


def test_guard_accepts_finite_norm_if_twice_peak_would_overflow(monkeypatch):
    monkeypatch.setattr(corrections, "vec_norm", lambda xyz: sys.float_info.max)
    xyz, delay = _iterate((sys.float_info.max, 0.0, 0.0), lambda delay: (sys.float_info.max, 0.0, 0.0))
    assert xyz[0] == sys.float_info.max
    assert math.isfinite(delay)


def test_legacy_unsplit_path_does_not_enable_new_guard(monkeypatch):
    monkeypatch.setattr(corrections, "vec_norm", lambda xyz: 3.0)
    xyz, delay = _iterate((1.0, 0.0, 0.0), lambda delay: (1.0, 0.0, 0.0), guarded=False)
    assert xyz == (1.0, 0.0, 0.0)
    assert delay == 3.0 / corrections.C_KM_PER_DAY
    with pytest.raises(ArithmeticError, match="exceeds"):
        _iterate((1.0, 0.0, 0.0), lambda delay: (1.0, 0.0, 0.0), guarded=True)


def test_first_iteration_success_is_bit_identical():
    calls = []

    def emission(delay):
        calls.append(delay)
        return (123456.75, -300.125, 15.0)

    geometric = (123456.75, -300.125, 15.0)
    old = _iterate(geometric, emission, guarded=False)
    assert len(calls) == 1
    calls.clear()
    new = _iterate(geometric, emission, guarded=True)
    assert len(calls) == 1
    assert new == old


@pytest.mark.parametrize("stop_on_tenth", [True, False])
def test_tenth_iteration_return_and_exhaustion_are_preserved(stop_on_tenth):
    def make_emitter(calls):
        def emission(delay):
            calls.append(delay)
            number = len(calls)
            value = 100.0 + (9 if stop_on_tenth and number == 10 else number)
            return (value, 0.0, 0.0)
        return emission

    old_calls, new_calls = [], []
    old = _iterate((100.0, 0.0, 0.0), make_emitter(old_calls), guarded=False)
    new = _iterate((100.0, 0.0, 0.0), make_emitter(new_calls), guarded=True)
    assert len(old_calls) == len(new_calls) == 10
    assert new == old


def test_apply_split_enables_guard_but_legacy_apply_does_not(monkeypatch):
    monkeypatch.setattr(corrections, "vec_norm", lambda xyz: 3.0)
    earth = (0.0, 0.0, 0.0)

    def split(body, jd, offset, reader):
        return (1.0, 0.0, 0.0)

    def legacy(body, jd, reader):
        return (1.0, 0.0, 0.0)

    with pytest.raises(ArithmeticError, match="exceeds"):
        corrections._apply_light_time_split("Sun", 2451545.0, None, earth, split)
    assert corrections.apply_light_time("Sun", 2451545.0, None, earth, legacy)[0] == (1.0, 0.0, 0.0)
