"""Numerical behavior of the central-path candidate root isolator.

These synthetic functions test bisection of an already witnessed sign change.
They do not assert completeness for a sampled interval or physical accuracy.
"""
from __future__ import annotations

import math

import pytest

from moira.solar_eclipse_hybrid import _bisect_sign_change


@pytest.mark.parametrize("direction", (-1.0, 1.0))
def test_isolates_ingress_switch_below_a_tenth_of_a_second(direction):
    ingress = 1582760.4850160365
    root = ingress + 0.08 / 86400.0
    left = ingress + 0.04 / 86400.0
    right = ingress + 0.15 / 86400.0

    def objective(jd):
        return direction * (jd - root)

    bracket = _bisect_sign_change(objective, left, right)
    assert bracket is not None
    lower, upper = bracket
    assert left <= lower < upper <= right
    assert objective(lower) * objective(upper) < 0.0
    assert lower <= root <= upper
    assert (upper - lower) * 86400 < 0.001


@pytest.mark.parametrize("objective", (
    lambda x: (x - 0.2) * (x - 0.3),  # two roots with same-sign endpoints
    lambda x: (x - 0.5) ** 2,          # tangent root without sign change
    lambda _x: 1.0,
))
def test_same_sign_endpoints_do_not_certify_absence(objective):
    assert _bisect_sign_change(objective, 0.0, 1.0) is None


@pytest.mark.parametrize("bad", (math.nan, math.inf, -math.inf, None))
def test_invalid_midpoint_never_produces_a_root_bracket(bad):
    def objective(x):
        return bad if x == 0.5 else x - 0.4

    assert _bisect_sign_change(objective, 0.0, 1.0) is None


def test_invalid_or_collapsed_search_domain_is_unresolved():
    assert _bisect_sign_change(lambda x: x, 1.0, 1.0) is None
    assert _bisect_sign_change(lambda x: x, 1.0, 0.0) is None


def test_exact_midpoint_zero_keeps_strict_opposite_sign_bracket():
    bracket = _bisect_sign_change(lambda x: x - 0.5, 0.0, 1.0)
    assert bracket is not None
    left, right = bracket
    assert left < 0.5 < right
    assert right - left < 1.0e-12
