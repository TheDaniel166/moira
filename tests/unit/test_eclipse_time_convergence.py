"""Conditional proof of the serving split-clock iteration limit."""

import math
from fractions import Fraction

import pytest

from moira import julian
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_time_convergence import prove_conditional_split_time_convergence


@pytest.mark.parametrize("anchor", [2451545.0, 2459891.9582497696])
def test_proved_modern_interval_covers_sampled_serving_iteration_counts(monkeypatch, anchor):
    result = prove_conditional_split_time_convergence(anchor, I(-0.01, 0.01))
    assert result.status == "proved"
    assert result.tt_anchor_jd == anchor and result.tt_offset_days == I(-0.01, 0.01)
    assert result.max_iterations <= julian._TT_TDB_FIXED_POINT_MAX_ITERATIONS
    assert result.final_difference_bound_seconds <= julian._TT_TDB_FIXED_POINT_RESIDUAL_SECONDS
    assert result.assumed_sine_ulp_bound == 1
    assert not result.arithmetic_environment_attested and not result.source_and_constants_attested
    original = julian._naif_tdb_minus_tt_seconds_at_tdb_split
    counts = []
    offsets_by_call = []
    def witness(*args):
        counts[-1] += 1
        value = original(*args)
        offsets_by_call[-1].append(value)
        return value
    monkeypatch.setattr(julian, "_naif_tdb_minus_tt_seconds_at_tdb_split", witness)
    for step in range(-10, 11):
        counts.append(0)
        offsets_by_call.append([])
        julian._tt_to_tdb_split(anchor, step / 1000)
    assert max(counts) <= result.max_iterations
    assert all(abs(Fraction.from_float(values[-1]) - Fraction.from_float(values[-2]))
               <= result.final_difference_bound_seconds for values in offsets_by_call
               if len(values) == result.max_iterations)


@pytest.mark.parametrize("direction", [-math.inf, math.inf])
def test_convergence_under_one_neighbor_sine_perturbation(monkeypatch, direction):
    anchor = 2459891.9582497696
    result = prove_conditional_split_time_convergence(anchor, I(-0.01, 0.01))
    assert result.status == "proved"
    original = math.sin
    def perturbed(value):
        return min(1.0, max(-1.0, math.nextafter(original(value), direction)))
    monkeypatch.setattr(julian.math, "sin", perturbed)
    # Actual libm results are sampled witnesses, not an attestation of the
    # declared one-ulp premise for the whole machine or interval.
    for offset in [-0.01, math.nextafter(-0.01, 0.0), 0.0,
                   math.nextafter(0.01, 0.0), 0.01]:
        assert result.tt_offset_days.contains(offset)
        julian._tt_to_tdb_split(anchor, offset)
    assert not result.tt_offset_days.contains(math.nextafter(-0.01, -math.inf))
    assert not result.tt_offset_days.contains(math.nextafter(0.01, math.inf))


def test_large_roundoff_budget_remains_unresolved():
    result = prove_conditional_split_time_convergence(1026285.7107341307, I(-0.01, 0.01))
    assert result.status == "unresolved"
    assert "error" in result.reason


def test_remainder_boundary_remains_unresolved():
    seconds = (1.5 * math.tau - julian._NAIF_DELTET_M0_RADIANS) / julian._NAIF_DELTET_M1_RADIANS_PER_SECOND
    anchor = 2451545.0 + seconds / 86400
    result = prove_conditional_split_time_convergence(anchor, I(-1, 1))
    assert result.status == "unresolved"
    assert "remainder" in result.reason


def test_tighter_serving_threshold_cannot_be_claimed_without_evidence(monkeypatch):
    monkeypatch.setattr(julian, "_TT_TDB_FIXED_POINT_RESIDUAL_SECONDS", 1e-22)
    result = prove_conditional_split_time_convergence(2459891.9582497696, I(-0.01, 0.01))
    assert result.status == "unresolved"


@pytest.mark.parametrize("amplitude", [float("nan"), float("inf"), 0.01])
def test_invalid_periodic_amplitude_fails_closed(monkeypatch, amplitude):
    monkeypatch.setattr(julian, "_NAIF_DELTET_K_SECONDS", amplitude)
    result = prove_conditional_split_time_convergence(2451545.0, I.point(0))
    assert result.status == "unresolved"


@pytest.mark.parametrize("anchor", [2451545.0, 2459891.9582497696])
def test_two_part_box_covers_independent_represented_inputs(monkeypatch, anchor):
    first = [math.nextafter(anchor, -math.inf), anchor, math.nextafter(anchor, math.inf)]
    origin = Fraction.from_float(anchor)
    first_offsets = I(Fraction.from_float(first[0]) - origin,
                      Fraction.from_float(first[-1]) - origin)
    second = [-0.01, math.nextafter(-0.01, 0.0), 0.0,
              math.nextafter(0.01, 0.0), 0.01]
    offsets = I(second[0], second[-1])
    result = prove_conditional_split_time_convergence(
        anchor, offsets, first_part_offsets=first_offsets,
    )
    assert result.status == "proved"
    assert result.tt_first_part_offsets == first_offsets
    assert result.tt_combined_offset_days == first_offsets + offsets
    original = julian._naif_tdb_minus_tt_seconds_at_tdb_split
    observed = []
    def witness(*args):
        observed[-1].append(original(*args))
        return observed[-1][-1]
    monkeypatch.setattr(julian, "_naif_tdb_minus_tt_seconds_at_tdb_split", witness)
    for part1 in first:
        assert first_offsets.contains(Fraction.from_float(part1) - origin)
        for part2 in second:
            assert offsets.contains(part2)
            observed.append([])
            julian._tt_to_tdb_split(part1, part2)
    assert all(2 <= len(values) <= result.max_iterations for values in observed)
    assert all(abs(Fraction.from_float(values[-1]) - Fraction.from_float(values[-2]))
               <= result.final_difference_bound_seconds for values in observed
               if len(values) == result.max_iterations)


@pytest.mark.parametrize("direction", [-1, 1])
def test_two_part_combined_boundary_requires_normalization_margin(direction):
    limit = direction * julian._MAX_ABS_TIME_JD
    near = math.nextafter(limit, 0.0)
    boundary = prove_conditional_split_time_convergence(
        limit, I.point(0), first_part_offsets=I.point(0),
    )
    assert boundary.status == "unresolved"
    assert "boundary" in boundary.reason
    # A first-part box touching the boundary must remain unresolved even if
    # its other endpoint is in range. This cannot be hidden by decomposition.
    delta = Fraction.from_float(near) - Fraction.from_float(limit)
    box = I(min(delta, 0), max(delta, 0))
    assert prove_conditional_split_time_convergence(
        limit, I.point(0), first_part_offsets=box,
    ).status == "unresolved"


def test_each_split_input_is_checked_before_combining():
    limit = julian._MAX_ABS_TIME_JD
    result = prove_conditional_split_time_convergence(
        limit, I(-limit, -limit), first_part_offsets=I(0, 1),
    )
    assert result.status == "unresolved"
    assert "input part" in result.reason


def test_generalized_checker_does_not_use_successful_output_envelope(monkeypatch):
    from moira import _eclipse_time_bounds
    def forbidden(*args, **kwargs):
        raise AssertionError("a successful-output envelope cannot establish totality")
    monkeypatch.setattr(_eclipse_time_bounds, "bound_serving_split_tdb", forbidden)
    result = prove_conditional_split_time_convergence(
        2451545.0, I(-0.001, 0.001), first_part_offsets=I(-0.001, 0.001),
    )
    assert result.status == "proved"
