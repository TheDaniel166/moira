"""Independent exact endpoint controls for type-2 Chebyshev bounds.

These synthetic polynomials validate the numerical enclosure, not the
accuracy of a particular ephemeris or the completeness of an eclipse search.
"""

from fractions import Fraction
import math

import pytest

from moira._eclipse_interval import RationalInterval as I
from moira._eclipse_spk_bounds import _chebyshev, _derivative_upper


def _forward_value_and_derivative(degree, x):
    """Use the forward recurrence for T_n and dT_n/dx, not Clenshaw."""
    previous, value = Fraction(1), x
    previous_derivative, derivative = Fraction(0), Fraction(1)
    if degree == 0:
        return previous, previous_derivative
    for _ in range(2, degree + 1):
        previous, value, previous_derivative, derivative = (
            value,
            2 * x * value - previous,
            derivative,
            2 * value + 2 * x * derivative - previous_derivative,
        )
    return value, derivative


@pytest.mark.parametrize("degree", [0, 1, 2, 17, 48])
@pytest.mark.parametrize("endpoint", [-1, 1])
def test_exact_record_endpoint_identity_and_saturated_derivative_bound(degree, endpoint):
    """T_n(±1) and |T'_n(±1)| = n² test endpoint signs and scaling."""
    coefficients = (0.0,) * degree + (1.0,)
    record_length_seconds = Fraction(8)
    bound = _chebyshev(coefficients, I.point(endpoint))
    assert bound == I.point(endpoint ** degree)
    assert _derivative_upper(coefficients, record_length_seconds) == (
        Fraction(degree * degree * 2, 1) / record_length_seconds
    )


@pytest.mark.parametrize("endpoint", [-1.0, 1.0])
def test_immediately_interior_float_has_enclosed_high_order_value_and_rate(endpoint):
    """A forward exact-rational oracle checks both sides of the endpoint layer."""
    degree = 48
    x = Fraction.from_float(math.nextafter(endpoint, 0.0))
    coefficients = (0.0,) * degree + (1.0,)
    expected_value, expected_rate_x = _forward_value_and_derivative(degree, x)
    result = _chebyshev(coefficients, I.point(x))
    record_length_seconds = Fraction(8)
    assert result.contains(expected_value)
    assert _derivative_upper(coefficients, record_length_seconds) >= abs(
        expected_rate_x * 2 / record_length_seconds
    )
