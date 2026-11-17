"""Conditional strict phase sign partitions over represented times."""

from fractions import Fraction
import math
from types import SimpleNamespace

import pytest

from moira._eclipse_interval_roots import EnclosureUnavailable
from moira import _eclipse_strict_phase_partition as subject


def test_tt_partition_uses_new_branch_and_exact_closed_offsets(monkeypatch):
    first = 2459895.0
    last = math.nextafter(first, math.inf)
    calls = []

    def provider(reader, anchor, offset):
        calls.append((reader, anchor, offset))
        return SimpleNamespace(new_direction_sign=-1, full_direction_sign=1)

    monkeypatch.setattr(subject, "bound_strict_mean_phase_interval", provider)
    reader = object()
    result = subject.partition_strict_phase_signs(
        reader, first, last, phase="new", time_scale="TT", max_evaluations=1,
    )
    assert calls[0][0] is reader
    assert calls[0][1] == first
    assert calls[0][2].lo == 0
    assert calls[0][2].hi == Fraction.from_float(last) - Fraction.from_float(first)
    assert result.partition.cells[0].sign == "negative"
    assert result.partition.represented_coverage_complete
    assert not result.partition.all_signs_classified
    assert not result.partition.adjacent_sign_witnesses
    assert result.successful_outputs_only
    assert not result.complete_search_certified
    assert not result.continuous_root_proved


def test_ut_partition_uses_full_branch_and_retains_unresolved(monkeypatch):
    first = 2459895.0
    last = math.nextafter(first, math.inf)
    calls = []

    def provider(reader, anchor, offset, *, max_days):
        calls.append((anchor, offset, max_days))
        return SimpleNamespace(phase=SimpleNamespace(new_direction_sign=1, full_direction_sign=None))

    monkeypatch.setattr(subject, "bound_strict_ut_phase_interval", provider)
    result = subject.partition_strict_phase_signs(
        object(), first, last, phase="full", time_scale="UT1", max_evaluations=1, max_ut_days=7,
    )
    assert calls[0][2] == 7
    assert result.partition.represented_coverage_complete
    assert all(cell.sign == "unresolved" for cell in result.partition.cells)
    assert result.partition.evaluations == 1


def test_unsupported_and_invalid_provider_values_are_not_proofs(monkeypatch):
    def unavailable(*args):
        raise EnclosureUnavailable("unsupported")

    monkeypatch.setattr(subject, "bound_strict_mean_phase_interval", unavailable)
    result = subject.partition_strict_phase_signs(
        object(), 2459895.0, 2459895.0, phase="new", time_scale="TT", max_evaluations=1,
    )
    assert result.partition.cells[0].sign == "unresolved"
    assert not result.partition.all_signs_classified

    monkeypatch.setattr(subject, "bound_strict_mean_phase_interval", lambda *args:
                        SimpleNamespace(new_direction_sign=True, full_direction_sign=None))
    with pytest.raises(ValueError, match="invalid direction"):
        subject.partition_strict_phase_signs(
            object(), 2459895.0, 2459895.0, phase="new", time_scale="TT", max_evaluations=1,
        )


@pytest.mark.parametrize("first,last,phase,scale", [
    (0.0, 1.0, "new", "TT"),
    (1.0, float("inf"), "new", "TT"),
    (1.0, 1.0, "other", "TT"),
    (1.0, 1.0, "new", "UTC"),
])
def test_invalid_domains_are_rejected(first, last, phase, scale):
    with pytest.raises(ValueError):
        subject.partition_strict_phase_signs(
            object(), first, last, phase=phase, time_scale=scale, max_evaluations=1,
        )


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("scale", ["TT", "UT1"])
def test_de441_phase_bounds_remain_conditional(planetary_reader, scale):
    from moira._eclipse_interval import RationalInterval
    from moira._eclipse_strict_phase_bounds import (
        bound_strict_mean_phase_interval,
        evaluate_bounded_strict_mean_phase,
    )
    from moira._eclipse_strict_phase_ut import (
        bound_strict_ut_phase_interval,
        evaluate_bounded_strict_ut_phase,
    )

    anchor = 2459895.9582497696
    first, last = anchor - 5 / 86400, anchor + 5 / 86400
    result = subject.partition_strict_phase_signs(
        planetary_reader, first, last,
        phase="full", time_scale=scale, max_evaluations=1,
    )
    assert result.partition.represented_coverage_complete
    assert result.partition.cells[0].sign in ("positive", "negative")
    assert not result.partition.all_signs_classified
    assert not result.legacy_phase_evaluator_attested
    assert not result.physical_accuracy_certified
    offset = RationalInterval(Fraction(0), Fraction.from_float(last) - Fraction.from_float(first))
    if scale == "TT":
        domain = bound_strict_mean_phase_interval(planetary_reader, first, offset)
        evaluate = evaluate_bounded_strict_mean_phase
    else:
        domain = bound_strict_ut_phase_interval(planetary_reader, first, offset)
        evaluate = evaluate_bounded_strict_ut_phase
    expected = 1 if result.partition.cells[0].sign == "positive" else -1
    for jd in (first, anchor, last):
        sample = evaluate(domain, jd)
        assert sample.cross_km2 * expected < 0


@pytest.mark.requires_ephemeris
def test_sign_box_does_not_attest_native_snapshot_availability(planetary_reader, monkeypatch):
    """The bounding path can succeed even when the execution guard cannot."""
    from moira import _moira_native
    from moira._eclipse_interval import RationalInterval
    from moira._eclipse_strict_phase_bounds import (
        bound_strict_mean_phase_interval,
        evaluate_bounded_strict_mean_phase,
    )

    tt = 2459895.9582497696
    domain = bound_strict_mean_phase_interval(planetary_reader, tt, RationalInterval.point(0))
    result = subject.partition_strict_phase_signs(
        planetary_reader, tt, tt, phase="full", time_scale="TT", max_evaluations=1,
    )
    assert result.partition.cells[0].sign in ("positive", "negative")
    monkeypatch.setattr(_moira_native, "_eclipse_strict_snapshot_build_contract", None)
    with pytest.raises(EnclosureUnavailable, match="lacks guarded snapshot"):
        evaluate_bounded_strict_mean_phase(domain, tt)
    assert not result.partition.all_signs_classified
    assert not result.partition.adjacent_sign_witnesses


@pytest.mark.requires_ephemeris
def test_sign_box_does_not_prove_trigonometric_work_finishes(planetary_reader, monkeypatch):
    """A strict operation's unavailable path cannot become a sign witness."""
    from moira import _eclipse_strict_phase as strict_phase
    from moira._eclipse_interval import RationalInterval
    from moira._eclipse_strict_phase_bounds import (
        bound_strict_mean_phase_interval,
        evaluate_bounded_strict_mean_phase,
    )
    from moira._eclipse_strict_trig import EclipseStrictTrigUnavailable

    tt = 2459895.9582497696
    domain = bound_strict_mean_phase_interval(planetary_reader, tt, RationalInterval.point(0))
    result = subject.partition_strict_phase_signs(
        planetary_reader, tt, tt, phase="full", time_scale="TT", max_evaluations=1,
    )

    def unavailable(*args, **kwargs):
        raise EclipseStrictTrigUnavailable("injected unresolved trigonometric rounding")

    monkeypatch.setattr(strict_phase, "strict_scalar_sin_cos", unavailable)
    with pytest.raises(EclipseStrictTrigUnavailable, match="injected unresolved"):
        evaluate_bounded_strict_mean_phase(domain, tt)
    assert not result.partition.all_signs_classified
    assert not result.partition.adjacent_sign_witnesses
