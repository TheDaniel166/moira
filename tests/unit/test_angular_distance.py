"""Exact-rational witnesses for unsigned circular separation, in degrees."""

from fractions import Fraction
import math
from random import Random

import pytest

from moira.coordinates import angular_distance


@pytest.mark.parametrize("angle", [720/11, 1080/11, 1440/11, 1800/11, 360/14, 1080/14, 1800/14])
def test_nonbinary_aspect_orb_boundary_is_exact_and_symmetric(angle):
    point = angle + 1.0
    assert Fraction(point) - Fraction(angle) == 1
    assert angular_distance(0.0, point) == angular_distance(point, 0.0) == point
    assert angular_distance(0.0, point) - angle == 1.0


def test_unsigned_separation_matches_an_independent_exact_rational_oracle():
    rng = Random(20261025)
    pairs = [(0, 0), (0, 180), (355, 5), (-355, -5), (720, -720)]
    pairs += [(rng.uniform(-720, 720), rng.uniform(-720, 720)) for _ in range(500)]
    # Inputs differ by at most 1440 degrees. Four ULPs at that bound cover
    # the floating subtraction and fold; the oracle uses exact input floats.
    tolerance = 4 * math.ulp(1440.0)
    for a, b in pairs:
        exact = abs(Fraction(a) - Fraction(b)) % 360
        expected = float(min(exact, 360-exact))
        actual = angular_distance(a, b)
        assert 0 <= actual <= 180
        assert actual == angular_distance(b, a)
        assert actual == pytest.approx(expected, abs=tolerance, rel=0)
