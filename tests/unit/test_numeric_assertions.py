"""Contracts for unit-aware, semantics-aware numeric test assertions."""

from __future__ import annotations

import math

import pytest

from support.numeric_assertions import (
    NumericSemantics,
    ToleranceContract,
    Unit,
    assert_au,
    assert_canonical_longitude_degrees,
    assert_circular_degrees,
    assert_days,
    assert_event_residual,
    assert_kilometres,
    assert_ratio,
    assert_scalar_degrees,
    assert_seconds,
    assert_vector_angular_separation,
    circular_residual_degrees,
    vector_angular_separation_degrees,
)


CIRCULAR_MICRODEGREE = ToleranceContract(
    name="circular_microdegree",
    semantics=NumericSemantics.CIRCULAR,
    unit=Unit.DEGREES,
    absolute=1e-6,
    basis="Contract-test boundary for wrapped longitude residuals.",
)
SCALAR_MICRODEGREE = ToleranceContract(
    name="scalar_microdegree",
    semantics=NumericSemantics.LINEAR,
    unit=Unit.DEGREES,
    absolute=1e-6,
    basis="Contract-test boundary for non-periodic degree quantities.",
)
VECTOR_NANODEGREE = ToleranceContract(
    name="vector_nanodegree",
    semantics=NumericSemantics.VECTOR_ANGLE,
    unit=Unit.DEGREES,
    absolute=1e-9,
    basis="Contract-test boundary for vector-direction agreement.",
)
AU_CONTRACT = ToleranceContract(
    name="au_contract",
    semantics=NumericSemantics.LINEAR,
    unit=Unit.AU,
    absolute=1e-12,
    basis="Contract-test boundary for astronomical-unit distances.",
)
KILOMETRE_CONTRACT = ToleranceContract(
    name="kilometre_contract",
    semantics=NumericSemantics.LINEAR,
    unit=Unit.KILOMETRES,
    absolute=1e-6,
    basis="Contract-test boundary for kilometre distances.",
)
DAY_CONTRACT = ToleranceContract(
    name="day_contract",
    semantics=NumericSemantics.LINEAR,
    unit=Unit.DAYS,
    absolute=1e-9,
    basis="Contract-test boundary for Julian-day intervals.",
)
SECOND_CONTRACT = ToleranceContract(
    name="second_contract",
    semantics=NumericSemantics.LINEAR,
    unit=Unit.SECONDS,
    absolute=1e-6,
    basis="Contract-test boundary for elapsed seconds.",
)
RATIO_CONTRACT = ToleranceContract(
    name="ratio_contract",
    semantics=NumericSemantics.LINEAR,
    unit=Unit.DIMENSIONLESS,
    absolute=1e-12,
    basis="Contract-test boundary for dimensionless ratios.",
)
EVENT_CONTRACT = ToleranceContract(
    name="event_root_residual",
    semantics=NumericSemantics.EVENT_RESIDUAL,
    unit=Unit.DEGREES,
    absolute=1e-8,
    basis="Contract-test boundary for a signed angular event function.",
)


def test_circular_degrees_wrap_across_zero() -> None:
    assert_circular_degrees(
        359.99999975,
        0.00000025,
        tolerance=CIRCULAR_MICRODEGREE,
    )


def test_circular_degrees_enforce_threshold_boundary() -> None:
    assert_circular_degrees(10.0, 10.0 + 1e-6, tolerance=CIRCULAR_MICRODEGREE)

    with pytest.raises(AssertionError, match="circular_microdegree"):
        assert_circular_degrees(
            10.0,
            10.0 + 1.01e-6,
            tolerance=CIRCULAR_MICRODEGREE,
        )


def test_circular_degrees_reduce_extreme_finite_inputs_before_subtraction() -> None:
    assert circular_residual_degrees(1.7e308, -1.7e308) == 56.0

    with pytest.raises(AssertionError, match="circular_microdegree"):
        assert_circular_degrees(
            1.7e308,
            -1.7e308,
            tolerance=CIRCULAR_MICRODEGREE,
        )


def test_scalar_degrees_do_not_wrap() -> None:
    with pytest.raises(AssertionError, match="scalar_microdegree"):
        assert_scalar_degrees(359.99999975, 0.00000025, tolerance=SCALAR_MICRODEGREE)


@pytest.mark.parametrize(
    ("assertion", "contract"),
    (
        (assert_au, AU_CONTRACT),
        (assert_kilometres, KILOMETRE_CONTRACT),
        (assert_days, DAY_CONTRACT),
        (assert_seconds, SECOND_CONTRACT),
        (assert_ratio, RATIO_CONTRACT),
    ),
)
def test_linear_product_helpers_accept_matching_contracts(
    assertion,
    contract: ToleranceContract,
) -> None:
    assertion(1.0, 1.0 + contract.absolute / 2.0, tolerance=contract)


def test_helper_rejects_contract_with_wrong_unit() -> None:
    with pytest.raises(ValueError, match="unit"):
        assert_au(1.0, 1.0, tolerance=KILOMETRE_CONTRACT)


def test_helper_rejects_contract_with_wrong_semantics() -> None:
    with pytest.raises(ValueError, match="semantics"):
        assert_circular_degrees(1.0, 1.0, tolerance=SCALAR_MICRODEGREE)


@pytest.mark.parametrize("value", (True, False))
def test_numeric_helpers_reject_booleans(value: bool) -> None:
    with pytest.raises(TypeError, match="boolean"):
        assert_scalar_degrees(value, 0.0, tolerance=SCALAR_MICRODEGREE)


@pytest.mark.parametrize("value", (math.nan, math.inf, -math.inf))
def test_numeric_helpers_reject_non_finite_values(value: float) -> None:
    with pytest.raises(ValueError, match="finite"):
        assert_ratio(value, 0.0, tolerance=RATIO_CONTRACT)


@pytest.mark.parametrize("value", (0.0, 1.0, 359.999999999))
def test_canonical_longitude_accepts_half_open_domain(value: float) -> None:
    assert_canonical_longitude_degrees(value)


@pytest.mark.parametrize("value", (-1e-15, 360.0, 720.0))
def test_canonical_longitude_rejects_values_outside_half_open_domain(
    value: float,
) -> None:
    with pytest.raises(AssertionError, match=r"\[0, 360\)"):
        assert_canonical_longitude_degrees(value)


@pytest.mark.parametrize(
    ("value", "expected_error"),
    (
        (True, TypeError),
        (math.nan, ValueError),
        (math.inf, ValueError),
    ),
)
def test_canonical_longitude_rejects_invalid_numeric_values(
    value: object,
    expected_error: type[Exception],
) -> None:
    with pytest.raises(expected_error):
        assert_canonical_longitude_degrees(value)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("first", "second", "expected"),
    (
        ((1.0, 0.0, 0.0), (1.0, 0.0, 0.0), 0.0),
        ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), 90.0),
        ((1.0, 0.0, 0.0), (-1.0, 0.0, 0.0), 180.0),
    ),
)
def test_vector_angular_separation_covers_principal_geometry(
    first: tuple[float, float, float],
    second: tuple[float, float, float],
    expected: float,
) -> None:
    assert vector_angular_separation_degrees(first, second) == pytest.approx(
        expected,
        abs=1e-14,
    )


def test_vector_angular_separation_preserves_tiny_angles() -> None:
    tiny_radians = 1e-12
    second = (math.cos(tiny_radians), math.sin(tiny_radians), 0.0)

    separation = vector_angular_separation_degrees((1.0, 0.0, 0.0), second)

    assert separation == pytest.approx(math.degrees(tiny_radians), rel=1e-12)


def test_vector_angular_separation_is_scale_invariant() -> None:
    unit_separation = vector_angular_separation_degrees(
        (1.0, 2.0, 3.0),
        (-4.0, 5.0, 6.0),
    )
    scaled_separation = vector_angular_separation_degrees(
        (1e100, 2e100, 3e100),
        (-4e-100, 5e-100, 6e-100),
    )

    assert scaled_separation == pytest.approx(unit_separation, abs=1e-14)


def test_vector_angular_separation_scales_before_norm_overflow() -> None:
    separation = vector_angular_separation_degrees(
        (1.7e308, 1.7e308, 0.0),
        (-1.7e308, 1.7e308, 0.0),
    )

    assert separation == pytest.approx(90.0, abs=1e-14)


def test_vector_length_check_consumes_at_most_four_components() -> None:
    def four_then_explode():
        yield 1.0
        yield 2.0
        yield 3.0
        yield 4.0
        raise AssertionError("vector helper consumed beyond the fourth component")

    with pytest.raises(ValueError, match="exactly three"):
        vector_angular_separation_degrees(
            four_then_explode(),
            (1.0, 0.0, 0.0),
        )


def test_vector_assertion_reports_separation_against_named_contract() -> None:
    assert_vector_angular_separation(
        (1.0, 0.0, 0.0),
        (1.0, 0.0, 0.0),
        tolerance=VECTOR_NANODEGREE,
    )

    with pytest.raises(AssertionError, match="vector_nanodegree"):
        assert_vector_angular_separation(
            (1.0, 0.0, 0.0),
            (0.0, 1.0, 0.0),
            tolerance=VECTOR_NANODEGREE,
        )


@pytest.mark.parametrize(
    ("vector", "expected_error"),
    (
        ((0.0, 0.0, 0.0), ValueError),
        ((1.0, 2.0), ValueError),
        ((1.0, 2.0, 3.0, 4.0), ValueError),
        ((1.0, math.nan, 0.0), ValueError),
        ((True, 0.0, 0.0), TypeError),
    ),
)
def test_vector_angular_separation_rejects_invalid_vectors(
    vector,
    expected_error: type[Exception],
) -> None:
    with pytest.raises(expected_error):
        vector_angular_separation_degrees(vector, (1.0, 0.0, 0.0))


def test_event_residual_is_explicitly_zero_centered() -> None:
    assert_event_residual(5e-9, tolerance=EVENT_CONTRACT)

    with pytest.raises(AssertionError, match="event_root_residual"):
        assert_event_residual(2e-8, tolerance=EVENT_CONTRACT)


@pytest.mark.parametrize(
    ("overrides", "expected_error"),
    (
        ({"name": ""}, ValueError),
        ({"basis": ""}, ValueError),
        ({"absolute": True}, TypeError),
        ({"absolute": -1.0}, ValueError),
        ({"absolute": math.nan}, ValueError),
        ({"relative": True}, TypeError),
        ({"relative": -1.0}, ValueError),
        ({"relative": math.inf}, ValueError),
        ({"semantics": "linear"}, TypeError),
        ({"unit": "deg"}, TypeError),
    ),
)
def test_tolerance_contract_rejects_ambiguous_or_invalid_policy(
    overrides: dict[str, object],
    expected_error: type[Exception],
) -> None:
    values: dict[str, object] = {
        "name": "valid_contract",
        "semantics": NumericSemantics.LINEAR,
        "unit": Unit.DEGREES,
        "absolute": 1e-6,
        "relative": None,
        "basis": "A specific and reviewable numerical basis.",
    }
    values.update(overrides)

    with pytest.raises(expected_error):
        ToleranceContract(**values)  # type: ignore[arg-type]


def test_relative_tolerance_is_for_linear_semantics_only() -> None:
    with pytest.raises(ValueError, match="relative"):
        ToleranceContract(
            name="invalid_circular_relative",
            semantics=NumericSemantics.CIRCULAR,
            unit=Unit.DEGREES,
            absolute=1e-6,
            relative=1e-9,
            basis="Relative tolerance has no declared circular meaning.",
        )
