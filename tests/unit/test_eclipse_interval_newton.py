"""Conditional root exclusion, inclusion and contraction by interval Newton."""

from fractions import Fraction as F

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_newton import interval_newton_step
from moira._eclipse_interval_roots import EnclosureUnavailable


def _newton(box, function, derivative, **kwargs):
    return interval_newton_step(box, function, derivative,
                                continuously_differentiable=True, **kwargs)


def test_inclusion_proves_one_root_and_contains_independent_rational_bracket():
    result = _newton(I(1, 2), lambda x: x.square() - 2, lambda x: 2*x)
    assert result.status == "unique"
    assert result.reason == "newton_image_strictly_inside"
    assert result.root_enclosure.contains(F(1414, 1000))
    assert result.root_enclosure.contains(F(1415, 1000))
    assert F(1414, 1000)**2 < 2 < F(1415, 1000)**2
    assert result.evaluations == 3


def test_newton_image_disjoint_excludes_a_root_even_with_coarse_value_bound():
    def loose(x):
        return x + 1 if x.lo == x.hi else I(-1, 3)
    result = _newton(I(0, 1), loose, lambda x: I.point(1))
    assert result.status == "excluded"
    assert result.reason == "newton_image_disjoint"
    assert result.root_enclosure is None


def test_shared_endpoint_contraction_does_not_invent_existence():
    result = _newton(I(0, 1), lambda x: x, lambda x: I.point(1))
    assert result.status == "contracted"
    assert result.root_enclosure == I.point(0)


def test_noncontracting_image_and_negative_derivative():
    def value(x):
        return I(-1, 1) if x.lo != x.hi else I(F(-1, 2), F(1, 2))
    result = _newton(I(0, 1), value, lambda x: I(-2, -1))
    assert result.status == "unresolved"
    assert result.reason == "newton_image_does_not_contract"


def test_strict_partial_contraction_does_not_prove_a_root():
    # The actual function is x + 1/10, which is positive on [0, 1]. These
    # deliberately loose enclosures still satisfy the inclusion contract.
    def loose(x):
        return I(F(1, 10), F(9, 10)) if x.lo == x.hi else I(-1, 2)
    result = _newton(I(0, 1), loose, lambda x: I.point(1))
    assert result.status == "contracted"
    assert result.root_enclosure == I(0, F(2, 5))


def test_negative_derivative_can_prove_unique_interior_root():
    result = _newton(I(1, 2), lambda x: 2-x.square(), lambda x: -2*x)
    assert result.status == "unique"
    assert result.root_enclosure.contains(F(1414, 1000))
    assert result.root_enclosure.contains(F(1415, 1000))


def test_tangent_and_missing_differentiability_remain_unresolved():
    tangent = _newton(I(-1, 1), lambda x: x.square(), lambda x: 2*x)
    assert tangent.status == "unresolved"
    assert tangent.reason == "derivative_may_vanish"
    no_contract = interval_newton_step(I(-1, 1), lambda x: x, lambda x: I.point(1),
                                       continuously_differentiable=False)
    assert no_contract.status == "unresolved"
    assert no_contract.evaluations == 1


def test_singleton_zero_and_numerical_unknown_are_distinct():
    assert _newton(I.point(1), lambda x: I.point(0), lambda x: I.point(1)).status == "unique"
    assert _newton(I.point(1), lambda x: I(-1, 1), lambda x: I.point(1)).status == "unresolved"
    assert _newton(I.point(1), lambda x: I(1, 2), lambda x: I.point(1)).status == "excluded"


def test_budget_and_provider_fail_closed_and_unexpected_failures_propagate():
    for limit in range(3):
        result = _newton(I(-1, 1), lambda x: x, lambda x: I.point(1), max_evaluations=limit)
        assert result.status == "unresolved"
        assert result.reason == "evaluation_budget_exhausted"
        assert result.evaluations == limit
    def unavailable(_):
        raise EnclosureUnavailable("unsupported")
    result = _newton(I(-1, 1), lambda x: x, unavailable)
    assert result.status == "unresolved"
    assert "unsupported" in result.reason
    with pytest.raises(TypeError, match="RationalInterval"):
        _newton(I(-1, 1), lambda x: 42, lambda x: I.point(1))
    with pytest.raises(RuntimeError, match="unexpected"):
        _newton(I(-1, 1), lambda x: x,
                lambda _: (_ for _ in ()).throw(RuntimeError("unexpected")))
