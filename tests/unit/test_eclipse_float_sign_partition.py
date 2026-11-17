"""Exact float-domain ownership and conditional sign evidence tests."""
from __future__ import annotations

import math
import struct
from fractions import Fraction

import pytest

from moira._eclipse_float_sign_partition import (
    _float_key,
    _key_float,
    partition_representable_signs,
)
from moira._eclipse_interval import IntervalBudgetError
from moira._eclipse_interval_roots import EnclosureUnavailable


def test_represented_float_keys_round_trip_and_include_signed_zero():
    tiniest = math.ulp(0.0)
    values = [-1.0, -tiniest, -0.0, 0.0, tiniest, 1.0]
    keys = [_float_key(x) for x in values]
    assert keys == sorted(set(keys))
    assert all(struct.pack(">d", _key_float(k)) == struct.pack(">d", x)
               for x, k in zip(values, keys))
    assert keys[2] + 1 == keys[3]


def test_adjacent_float_crossing_is_a_discrete_witness_not_a_root_claim():
    left, right = 2460409.0, math.nextafter(2460409.0, math.inf)

    def enclosure(a, b):
        if b <= left:
            return "negative"
        if a >= right:
            return "positive"
        return None

    result = partition_representable_signs(
        left, right, enclosure, max_evaluations=3,
        all_inputs_defined_assumed=True, time_scale="TT",
    )
    assert result.represented_coverage_complete
    assert result.all_signs_classified
    assert [(c.first, c.last, c.sign) for c in result.cells] == [
        (left, left, "negative"), (right, right, "positive")
    ]
    assert len(result.adjacent_sign_witnesses) == 1
    assert result.adjacent_sign_witnesses[0].first == left
    assert result.adjacent_sign_witnesses[0].last == right
    assert not hasattr(result, "continuous_root_proved")


def test_successful_only_oracle_cannot_imply_complete_domain():
    result = partition_representable_signs(
        1.0, 2.0, lambda a, b: "positive", max_evaluations=1
    )
    assert result.represented_coverage_complete
    assert not result.all_inputs_defined_assumed
    assert not result.all_signs_classified
    assert result.cells[0].sign == "positive"

    # Each sign may describe only a successful output: without a totality
    # premise neither endpoint of an apparent crossing is a true witness.
    adjacent = math.nextafter(1.0, math.inf)
    def successful_only(a, b):
        if b == 1.0:
            return "negative"
        if a == adjacent:
            return "positive"
        return None
    result = partition_representable_signs(1.0, adjacent, successful_only, max_evaluations=3)
    assert [c.sign for c in result.cells] == ["negative", "positive"]
    assert result.adjacent_sign_witnesses == ()


def test_zero_plateau_and_wrap_are_retained_without_false_brackets():
    first = math.nextafter(1.0, -math.inf)
    last = math.nextafter(1.0, math.inf)
    def plateau(a, b):
        if b < 1.0:
            return "negative"
        if a > 1.0:
            return "positive"
        if a == b == 1.0:
            return "zero"
        return None
    result = partition_representable_signs(first, last, plateau, max_evaluations=15,
                                           all_inputs_defined_assumed=True)
    assert [c.sign for c in result.cells] == ["negative", "zero", "positive"]
    assert result.represented_coverage_complete and result.all_signs_classified
    assert result.adjacent_sign_witnesses == ()

    # A wrapped principal angle must not be mislabeled as a physical root by
    # this sign-only layer; the discontinuity is owned by its calling policy.
    wrap = partition_representable_signs(first, last, plateau, max_evaluations=1)
    assert not wrap.all_signs_classified
    assert wrap.adjacent_sign_witnesses == ()


def test_budget_and_unsupported_domains_preserve_every_float():
    def unavailable(a, b):
        raise EnclosureUnavailable("ambiguous record seam")
    for budget in (0, 1, 7, 20):
        result = partition_representable_signs(
            2451545.0, 2451545.01, unavailable,
            max_evaluations=budget, max_depth=64, time_scale="UT1",
        )
        assert result.represented_coverage_complete
        assert not result.all_signs_classified
        assert all(c.sign == "unresolved" for c in result.cells)
        assert result.evaluations == budget
    def arithmetic_budget(a, b):
        raise IntervalBudgetError("precision")
    result = partition_representable_signs(1.0, 1.0, arithmetic_budget, max_evaluations=1)
    assert result.cells[0].sign == "unresolved"
    assert "precision" in result.cells[0].reason


def test_unexpected_provider_errors_and_invalid_oracle_values_propagate():
    def broken(a, b):
        raise RuntimeError("damaged kernel")
    with pytest.raises(RuntimeError, match="damaged kernel"):
        partition_representable_signs(1.0, 2.0, broken, max_evaluations=1)
    with pytest.raises(TypeError, match="enclosure"):
        partition_representable_signs(1.0, 2.0, lambda a, b: 1, max_evaluations=1)


def test_numeric_width_is_not_a_proof_and_signed_zero_is_preserved():
    result = partition_representable_signs(
        -0.0, 0.0, lambda a, b: None, max_evaluations=1,
        max_unresolved_width_days=1e-9, all_inputs_defined_assumed=True,
    )
    assert result.represented_coverage_complete
    assert result.cells[0].represented_count == 2
    assert not result.all_signs_classified
    assert math.copysign(1.0, result.cells[0].first) == -1.0
    assert math.copysign(1.0, result.cells[0].last) == 1.0


@pytest.mark.parametrize("first,last", [
    (float("nan"), 1.0), (1.0, float("inf")), (2.0, 1.0), (True, 1.0), (1, 2.0)
])
def test_invalid_input_fails_before_provider(first, last):
    with pytest.raises(ValueError):
        partition_representable_signs(first, last, lambda a, b: "positive", max_evaluations=1)


@pytest.mark.requires_ephemeris
def test_conditional_de441_strict_phase_box_remains_successful_outputs_only(planetary_reader):
    from moira._eclipse_interval import RationalInterval as I
    from moira._eclipse_strict_phase_bounds import (
        bound_strict_mean_phase_interval,
        evaluate_bounded_strict_mean_phase,
    )

    # This near-full-moon TT window is away from a root and lies inside the
    # opt-in FW policy's validated domain. The bounds do not attest live
    # source, totality, the legacy phase, continuity or physical accuracy.
    anchor = 2459895.9582497696
    first, last = anchor - 5 / 86400, anchor + 5 / 86400
    saved = []

    def enclosure(a, b):
        offset = I(Fraction.from_float(a) - Fraction.from_float(anchor),
                   Fraction.from_float(b) - Fraction.from_float(anchor))
        bounds = bound_strict_mean_phase_interval(planetary_reader, anchor, offset)
        saved.append(bounds)
        sign = bounds.full_direction_sign
        return "positive" if sign == 1 else "negative" if sign == -1 else None

    result = partition_representable_signs(
        first, last, enclosure, max_evaluations=1, time_scale="TT",
    )
    assert result.represented_coverage_complete
    assert result.cells[0].sign in ("positive", "negative")
    assert not result.all_signs_classified
    assert not saved[0].complete_search_certified
    for t in (first, anchor, last):
        sample = evaluate_bounded_strict_mean_phase(saved[0], t)
        expected = 1 if result.cells[0].sign == "positive" else -1
        assert sample.cross_km2 * expected < 0  # full-moon branch sign convention
