"""Exact-enclosure binary64 trig for an opt-in mathematical policy."""
from decimal import Decimal, localcontext
from fractions import Fraction
import math
from types import SimpleNamespace

import pytest

from moira import _eclipse_strict_trig as strict
from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_interval_roots import EnclosureUnavailable


def _decimal_sin_cos(value):
    # Independent high-precision decimal Taylor computation for these small
    # arguments; this is numerical validation, not the enclosure proof.
    with localcontext() as context:
        context.prec = 115
        x = Decimal.from_float(value)
        sine, cosine = x, Decimal(1)
        sin_term, cos_term = x, Decimal(1)
        for n in range(1, 180):
            sin_term *= -(x * x) / Decimal((2 * n) * (2 * n + 1))
            cos_term *= -(x * x) / Decimal((2 * n - 1) * (2 * n))
            sine += sin_term
            cosine += cos_term
        return float(sine), float(cosine)


@pytest.mark.parametrize("x", [-10.0, -3.141592653589793, -1.0, -0.1, 0.1, 1.0, 3.141592653589793, 10.0])
def test_rounding_matches_independent_decimal_computation(x):
    result = strict.strict_scalar_sin_cos(x)
    expected = _decimal_sin_cos(x)
    assert (result.sine, result.cosine) == expected
    assert not result.platform_sin_cos_required
    assert not result.legacy_phase_evaluator_attested
    assert not result.complete_search_certified


@pytest.mark.parametrize("x", [0.0, -0.0, math.ulp(0.0), -math.ulp(0.0), 1e-200, -1e-200, 1e-12, -1e-12])
def test_tiny_arguments_and_signed_zero(x):
    result = strict.strict_scalar_sin_cos(x)
    assert result.sine == x
    assert math.copysign(1.0, result.sine) == math.copysign(1.0, x)
    assert result.cosine == 1.0


def test_exact_midpoints_use_ties_to_even():
    assert strict._checked_round(Fraction(1) + Fraction(1, 2**53)) == 1.0
    assert strict._checked_round(Fraction(1) + Fraction(3, 2**53)) == math.nextafter(math.nextafter(1.0, math.inf), math.inf)
    assert math.copysign(1.0, strict._checked_round(-Fraction(1, 2**1076))) == -1.0
    assert math.copysign(1.0, strict._checked_round(Fraction(0))) == 1.0


def test_no_platform_trig_and_unresolved_midpoint_fails_closed(monkeypatch):
    monkeypatch.setattr(math, "sin", lambda *args: (_ for _ in ()).throw(AssertionError("platform sin used")))
    monkeypatch.setattr(math, "cos", lambda *args: (_ for _ in ()).throw(AssertionError("platform cos used")))
    assert strict.strict_scalar_sin_cos(0.5).cosine > 0
    monkeypatch.setattr(strict, "sin_cos_enclosure", lambda *args, **kwargs: SimpleNamespace(
        sine=I(0, 1), cosine=I(0, 1),
    ))
    with pytest.raises(EnclosureUnavailable, match="midpoint"):
        strict.strict_scalar_sin_cos(0.5, max_precision_bits=64)


def test_budget_and_invalid_arguments_fail_closed():
    with pytest.raises(EnclosureUnavailable, match="budget"):
        strict.strict_scalar_sin_cos(2.0**70)
    with pytest.raises(EnclosureUnavailable, match="rounding"):
        strict._checked_round(Fraction(2**2048))
    for value in (float("nan"), float("inf"), True):
        with pytest.raises(ValueError):
            strict.strict_scalar_sin_cos(value)
