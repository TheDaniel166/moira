"""Opt-in strict phase samples from the same bounded SPK records."""
from fractions import Fraction
import math
from dataclasses import replace

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_phase_exclusion import bound_fw_phase_zero_exclusion
from moira import _eclipse_strict_phase as strict_phase
from moira._eclipse_strict_phase import evaluate_strict_mean_phase, evaluate_verified_strict_mean_phase


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("tt", [1026289.7107341307, 2459895.9582497696, 2688460.25])
def test_strict_phase_same_snapshot_sample_is_inside_phase_boxes(planetary_reader, monkeypatch, tt):
    bounds = bound_fw_phase_zero_exclusion(planetary_reader, tt, I(Fraction(-5, 86400), Fraction(5, 86400)))
    monkeypatch.setattr(math, "sin", lambda *args: (_ for _ in ()).throw(AssertionError("platform sin used")))
    monkeypatch.setattr(math, "cos", lambda *args: (_ for _ in ()).throw(AssertionError("platform cos used")))
    monkeypatch.setattr(math, "atan2", lambda *args: (_ for _ in ()).throw(AssertionError("platform atan2 used")))
    for seconds in (-2, 0, 2):
        epoch = tt + seconds / 86400
        evidence = evaluate_verified_strict_mean_phase(bounds, epoch)
        sample = evidence.sample
        assert evidence.sample_contained_in_error_widened_reference
        assert not evidence.entire_strict_policy_proved
        assert bounds.cross_km2.contains(sample.cross_km2)
        assert bounds.dot_km2.contains(sample.dot_km2)
        assert 1 <= sample.sun_iterations <= 10
        assert 1 <= sample.moon_iterations <= 10
        assert len(sample.snapshot_hashes) == 4 + sample.sun_iterations + 2 * sample.moon_iterations
        assert not sample.native_snapshot_build_independently_attested
        assert not sample.source_and_kernel_attested
        assert not sample.legacy_phase_evaluator_attested
        assert not sample.complete_search_certified
        if bounds.new_residual_sign is not None:
            assert sample.cross_km2 * bounds.new_residual_sign > 0
        if bounds.full_residual_sign is not None:
            assert sample.cross_km2 * bounds.full_residual_sign < 0


@pytest.mark.requires_ephemeris
def test_strict_phase_rejects_samples_outside_the_bounded_tt_box(planetary_reader):
    tt = 2459895.9582497696
    bounds = bound_fw_phase_zero_exclusion(planetary_reader, tt, I.point(0))
    with pytest.raises(ValueError, match="outside"):
        evaluate_strict_mean_phase(bounds.vector_bounds, tt + 1.0)


def test_checked_arithmetic_preserves_ieee_signed_zero():
    for result, sign in (
        (strict_phase._add(-0.0, -0.0), -1),
        (strict_phase._add(-0.0, 0.0), 1),
        (strict_phase._add(-1.0, 1.0), 1),
        (strict_phase._mul(-0.0, 1.0), -1),
        (strict_phase._mul(-0.0, -1.0), 1),
        (strict_phase._div(-0.0, 1.0), -1),
        (strict_phase._div(0.0, -1.0), -1),
        (strict_phase._sqrt(-0.0), -1),
    ):
        assert result == 0.0
        assert math.copysign(1.0, result) == sign


@pytest.mark.parametrize("x", [math.ulp(0.0), 1e-300, 1e-100, 2.0, 1e100])
def test_checked_sqrt_matches_representative_binary64_samples(x):
    assert strict_phase._sqrt(x) == math.sqrt(x)


@pytest.mark.requires_ephemeris
def test_verified_sample_rejects_modified_reference_box(planetary_reader):
    tt = 2459895.9582497696
    bounds = bound_fw_phase_zero_exclusion(planetary_reader, tt, I.point(0))
    altered = replace(bounds, cross_km2=I.point(0), error_margin_km2=Fraction(0),
                      new_residual_sign=None, full_residual_sign=None)
    with pytest.raises(ArithmeticError, match="escaped"):
        evaluate_verified_strict_mean_phase(altered, tt)


@pytest.mark.requires_ephemeris
def test_strict_phase_rejects_tampered_coefficient_snapshot(planetary_reader):
    tt = 2459895.9582497696
    bounds = bound_fw_phase_zero_exclusion(planetary_reader, tt, I.point(0))
    original = bounds.vector_bounds.spk_usages[0]
    first = original.record_snapshot[0]
    changed = ((first[0] + 1.0, *first[1:]), *original.record_snapshot[1:])
    bad_state = replace(original, record_snapshot=changed)
    bad_vector = replace(bounds.vector_bounds, spk_usages=(bad_state, *bounds.vector_bounds.spk_usages[1:]))
    bad_bounds = replace(bounds, vector_bounds=bad_vector)
    with pytest.raises(ValueError, match="snapshot identity"):
        evaluate_verified_strict_mean_phase(bad_bounds, tt)
