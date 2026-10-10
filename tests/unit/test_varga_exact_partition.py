"""VA-07/08: rational boundary oracle independent of engine partitioning."""

from fractions import Fraction
from math import nextafter, inf

import pytest

from moira.constants import SIGNS
from moira.varga import (
    calculate_varga,
    hora,
    saptavimshamsha,
    akshavedamsha,
    shashtiamsha,
)


@pytest.mark.parametrize("n", [*range(1, 61), 81, 108, 144])
def test_rational_edges_and_neighbors(n):
    for k in range(12 * n + 1):
        edge = float(Fraction(30 * k, n))
        for lon in (nextafter(edge, -inf), edge, nextafter(edge, inf)):
            if not 0 <= lon < 360:
                continue
            exact = Fraction(lon) * n
            sign = int(exact // 30) % 12
            point = calculate_varga(lon, n)
            assert SIGNS.index(point.sign) == sign, (n, lon)
            assert int(point.varga_longitude // 30) == sign, (n, lon)
            assert 0 <= point.sign_degree < 30
            assert point.sign_degree == min(float(exact % 30), nextafter(30.0, 0.0))


def test_tiny_negative_shodashvarga_remains_inside_circle():
    for function in (hora, saptavimshamsha, akshavedamsha, shashtiamsha):
        point = function(-1e-300)
        assert 0 <= point.longitude < 360
        assert 0 <= point.sign_degree < 30
        assert SIGNS[int(point.varga_longitude // 30)] == point.sign
