"""Exact finite-state split-clock checks; not continuous-time certificates."""

from fractions import Fraction
import math
import sys
from types import SimpleNamespace

import pytest

from moira import julian
from moira import _eclipse_float_sign_partition as signs
from moira import _eclipse_native_spk_bounds as bounds
from moira import _eclipse_spk_partition as partition
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_time_convergence import prove_split_time_convergence_exhaustively


_HISTORICAL_TT = 1248813.457560655


def test_default_is_unchanged_and_explicit_budget_covers_all_float_states():
    """Every representable normalized state in the conservative hull is run."""
    zero = I.point(0)
    assert prove_split_time_convergence_exhaustively(_HISTORICAL_TT, zero).status == "unresolved"
    rejected = prove_split_time_convergence_exhaustively(_HISTORICAL_TT, zero, max_states=1)
    assert rejected.status == "unresolved"
    assert "budget" in rejected.reason
    assert rejected.exhaustive_state_count > 1
    assert rejected.exhaustive_states_checked == 0

    normalized = julian._normalize_split_time_jd(_HISTORICAL_TT, 0.0)
    called = []
    actual_converter_code = julian._tt_to_tdb_split.__code__
    prior_profile = sys.getprofile()

    def observed(frame, event, arg):
        if event == "call" and frame.f_code is actual_converter_code:
            called.append((frame.f_locals["jd_tt"], frame.f_locals["jd_tt2"]))

    try:
        sys.setprofile(observed)
        result = prove_split_time_convergence_exhaustively(_HISTORICAL_TT, zero, max_states=16)
    finally:
        sys.setprofile(prior_profile)
    assert result.status == "proved"
    assert result.exhaustive_states_checked == result.exhaustive_state_count == len(called)
    assert normalized in called
    assert len(set(called)) == len(called)
    assert result.exhaustive_runtime_stability_required and result.exhaustive_same_thread_fenv_required
    assert not result.arithmetic_environment_attested and not result.source_and_constants_attested
    assert not result.physical_accuracy_certified


def test_changed_state_decoder_cannot_fabricate_coverage(monkeypatch):
    value = julian._normalize_split_time_jd(_HISTORICAL_TT, 0.0)[1]
    monkeypatch.setattr(signs, "_key_float", lambda _: value)
    result = prove_split_time_convergence_exhaustively(_HISTORICAL_TT, I.point(0), max_states=16)
    assert result.status == "unresolved"
    assert "source" in result.reason
    assert result.exhaustive_states_checked == 0


@pytest.mark.parametrize("module,name", [
    (signs, "_float_key"), (bounds, "_fsum"), (bounds, "_rounded"),
    (partition, "_binary64_domain"),
])
def test_changed_enclosure_or_key_helper_is_rejected(monkeypatch, module, name):
    monkeypatch.setattr(module, name, lambda *_args: 0)
    result = prove_split_time_convergence_exhaustively(_HISTORICAL_TT, I.point(0), max_states=16)
    assert result.status == "unresolved"
    assert "source" in result.reason
    assert result.exhaustive_states_checked == 0


def test_mismatched_normalizer_never_becomes_proof(monkeypatch):
    monkeypatch.setattr(julian, "_normalize_split_time_jd", lambda whole, frac: (whole, frac + 0.1))
    result = prove_split_time_convergence_exhaustively(_HISTORICAL_TT, I.point(0), max_states=16)
    assert result.status == "unresolved"
    assert "source" in result.reason


def test_raw_input_only_normalizer_change_is_detected(monkeypatch):
    """A patched raw-input branch must not hide behind canonical identities."""
    original = julian._normalize_split_time_jd

    def changed(first, second):
        if first == _HISTORICAL_TT and second == 0:
            return 40000001.0, 0.75
        return original(first, second)

    monkeypatch.setattr(julian, "_normalize_split_time_jd", changed)
    result = prove_split_time_convergence_exhaustively(_HISTORICAL_TT, I.point(0), max_states=16)
    assert result.status == "unresolved"
    assert "source" in result.reason
    assert result.exhaustive_states_checked == 0
    with pytest.raises(ValueError):
        julian._tt_to_tdb_split(_HISTORICAL_TT, 0)


def test_raw_input_only_converter_change_is_detected(monkeypatch):
    original = julian._tt_to_tdb_split

    def changed(first, second):
        if first == _HISTORICAL_TT and second == 0:
            raise ArithmeticError("raw-only failure")
        return original(first, second)

    monkeypatch.setattr(julian, "_tt_to_tdb_split", changed)
    result = prove_split_time_convergence_exhaustively(_HISTORICAL_TT, I.point(0), max_states=16)
    assert result.status == "unresolved"
    assert "source" in result.reason
    assert result.exhaustive_states_checked == 0


@pytest.mark.parametrize("name", ["_require_tt_tdb_jd", "_require_representable_time_jd", "_require_finite"])
def test_changed_input_guards_are_detected(monkeypatch, name):
    monkeypatch.setattr(julian, name, lambda *args: None)
    result = prove_split_time_convergence_exhaustively(_HISTORICAL_TT, I.point(0), max_states=16)
    assert result.status == "unresolved"
    assert "source" in result.reason
    assert result.exhaustive_states_checked == 0


def test_raw_only_finite_validation_change_is_detected(monkeypatch):
    """Exhaustive replay must not bypass validation of the original input."""
    original = julian._require_finite

    def changed(name, value):
        if name == "jd_tt" and value == _HISTORICAL_TT:
            raise ValueError("raw input rejected")
        return original(name, value)

    monkeypatch.setattr(julian, "_require_finite", changed)
    with pytest.raises(ValueError, match="raw input rejected"):
        julian._tt_to_tdb_split(_HISTORICAL_TT, 0.0)
    result = prove_split_time_convergence_exhaustively(_HISTORICAL_TT, I.point(0), max_states=16)
    assert result.status == "unresolved"
    assert "source" in result.reason
    assert result.exhaustive_states_checked == 0


def test_source_guard_applies_before_analytic_proved_shortcut(monkeypatch):
    """Opt-in proof must reject a changed source even when no enumeration is needed."""
    anchor = 2451545.0
    original = julian._require_finite

    def changed(name, value):
        if name == "jd_tt" and value == anchor:
            raise ValueError("raw input rejected")
        return original(name, value)

    monkeypatch.setattr(julian, "_require_finite", changed)
    with pytest.raises(ValueError, match="raw input rejected"):
        julian._tt_to_tdb_split(anchor, 0.0)
    result = prove_split_time_convergence_exhaustively(anchor, I.point(0), max_states=16)
    assert result.status == "unresolved"
    assert "source" in result.reason
    assert result.exhaustive_states_checked == 0


def test_changed_clock_math_module_is_detected(monkeypatch):
    # The bounds rely on the math functions used by the real normalizer, not
    # merely the separate `math` module imported by the checker.
    proxy = SimpleNamespace(**vars(math))
    proxy.fsum = lambda values: 0.0
    monkeypatch.setattr(julian, "math", proxy)
    result = prove_split_time_convergence_exhaustively(_HISTORICAL_TT, I.point(0), max_states=16)
    assert result.status == "unresolved"
    assert "source" in result.reason
    assert result.exhaustive_states_checked == 0


@pytest.mark.parametrize("name", ["nextafter", "ulp"])
def test_changed_float_enclosure_math_helpers_are_detected(monkeypatch, name):
    """The endpoint and ULP helpers are part of the exhaustive bound."""
    original = getattr(math, name)
    monkeypatch.setattr(math, name, lambda *args: original(*args))
    result = prove_split_time_convergence_exhaustively(_HISTORICAL_TT, I.point(0), max_states=16)
    assert result.status == "unresolved"
    assert "source" in result.reason
    assert result.exhaustive_states_checked == 0


@pytest.mark.parametrize("value", [True, -1, 1.5, None])
def test_invalid_budget_is_rejected(value):
    with pytest.raises(ValueError, match="nonnegative"):
        prove_split_time_convergence_exhaustively(_HISTORICAL_TT, I.point(0), max_states=value)


def test_signed_zero_and_subnormal_second_part_day_crossing_is_unresolved():
    tiny = math.ulp(0.0)
    result = prove_split_time_convergence_exhaustively(
        _HISTORICAL_TT, I(-tiny, tiny), max_states=100,
    )
    assert result.status == "unresolved"
    assert "day branch" in result.reason
    assert result.exhaustive_states_checked == 0


def test_large_fractional_float_hull_is_rejected_without_iteration():
    tiny_day = Fraction(1, 1_000_000)
    first = I(-tiny_day, tiny_day)
    result = prove_split_time_convergence_exhaustively(
        _HISTORICAL_TT, I.point(0), first_part_offsets=first, max_states=100,
    )
    assert result.status == "unresolved"
    assert "budget" in result.reason
    assert result.exhaustive_states_checked == 0
