"""Whole-interval strict phase schedule and fail-closed domains."""
from dataclasses import replace
from fractions import Fraction
import math
from types import SimpleNamespace

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable
from moira import _eclipse_strict_phase_bounds as strict_bounds
from moira._eclipse_strict_phase_bounds import (
    bound_strict_mean_phase_interval,
    evaluate_bounded_strict_mean_phase,
)


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("tt", [2451545.25 - 100 * 36525, 1026289.7107341307,
                                2459895.9582497696, 2688460.25, 2451545.25 + 100 * 36525])
def test_strict_schedule_interval_contains_each_sample_without_libm(planetary_reader, monkeypatch, tt):
    monkeypatch.setattr(math, "sin", lambda *args: (_ for _ in ()).throw(AssertionError("platform sin used")))
    monkeypatch.setattr(math, "cos", lambda *args: (_ for _ in ()).throw(AssertionError("platform cos used")))
    monkeypatch.setattr(math, "atan2", lambda *args: (_ for _ in ()).throw(AssertionError("platform atan2 used")))
    bounds = bound_strict_mean_phase_interval(planetary_reader, tt, I(Fraction(-5, 86400), Fraction(5, 86400)))
    assert not bounds.platform_sin_cos_or_atan2_required
    assert not bounds.source_and_loaded_native_image_attested
    assert not bounds.legacy_phase_evaluator_attested
    assert not bounds.continuous_root_proved
    assert not bounds.complete_search_certified
    for seconds in (-4.99, -4, -2, 0, 2, 4, 4.99):
        sample = evaluate_bounded_strict_mean_phase(bounds, tt + seconds / 86400)
        assert bounds.cross_km2.contains(sample.cross_km2)
        assert bounds.dot_km2.contains(sample.dot_km2)
        if bounds.new_direction_sign is not None:
            assert sample.cross_km2 * bounds.new_direction_sign > 0
        if bounds.full_direction_sign is not None:
            assert sample.cross_km2 * bounds.full_direction_sign < 0
    assert bounds.new_direction_sign is not None or bounds.full_direction_sign is not None


@pytest.mark.requires_ephemeris
def test_strict_schedule_rejects_outside_and_tampered_intervals(planetary_reader):
    tt = 2459895.9582497696
    bounds = bound_strict_mean_phase_interval(planetary_reader, tt, I.point(0))
    with pytest.raises(ValueError, match="outside"):
        evaluate_bounded_strict_mean_phase(bounds, tt + 1)
    altered = replace(bounds, cross_km2=I.point(0))
    with pytest.raises(ArithmeticError, match="escaped"):
        evaluate_bounded_strict_mean_phase(altered, tt)


@pytest.mark.requires_ephemeris
def test_strict_schedule_declines_fw_vondrak_boundary(planetary_reader):
    boundary = 2451545.0 + 50 * 36525.0
    with pytest.raises(EnclosureUnavailable):
        bound_strict_mean_phase_interval(planetary_reader, boundary, I(-1, 1))


def test_zero_delay_split_layout_remains_unavailable(monkeypatch):
    monkeypatch.setattr(strict_bounds, "bound_phase_planetary_vectors",
                        lambda *args: SimpleNamespace(spk_usages=(None,) * 64))
    with pytest.raises(EnclosureUnavailable, match="positive-delay"):
        bound_strict_mean_phase_interval(None, 2451545.0, I.point(0))
