"""Conditional Fukushima–Williams mean-ecliptic pole and direction bounds.

These private bounds model the Python FW/P03 precession and a mathematical
mean-ecliptic reduction. They do not enclose the actual nutation, apparent
frame, atan2, modulo, UT clock or phase-search result. Vondrak dates and FW
branch boundaries that cannot be resolved are unavailable.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import math

from ._eclipse_interval import IntervalBudgetError, IntervalDomainError, RationalInterval as I
from ._eclipse_interval_elementary import sin_cos_enclosure
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_native_spk_bounds import _rounded
from .constants import ARCSEC2RAD, DEG2RAD


class EclipsePhasePoleUnavailable(EnclosureUnavailable):
    """The mean-ecliptic pole cannot be enclosed on this model domain."""


@dataclass(frozen=True, slots=True)
class ConditionalMeanEclipticPole:
    """FW pole enclosure; not an enclosure of the serving phase result."""

    tt_anchor_jd: float
    tt_offset_days: I
    centuries: I
    pole: tuple[I, I, I]
    precession_matrix: tuple[tuple[I, I, I], tuple[I, I, I], tuple[I, I, I]]
    mean_matrix: tuple[tuple[I, I, I], tuple[I, I, I], tuple[I, I, I]]
    arithmetic_model: str = (
        "binary64 RN; gradual underflow; correctly rounded integer powers; "
        "Python sin/cos absolute error <= 2**-52"
    )
    source_and_constants_attested: bool = False
    arithmetic_environment_attested: bool = False
    actual_nutation_enclosed: bool = False
    actual_phase_enclosed: bool = False
    ut1_enclosed: bool = False
    physical_accuracy_certified: bool = False


def bound_fw_mean_ecliptic_pole(tt_anchor_jd: float, tt_offset_days: I) -> ConditionalMeanEclipticPole:
    """Bound the FW/P03 pole for represented TT samples on its proven branch.

    The numerical path follows the represented Python polynomial coefficients,
    source evaluation order, and passive rotation matrices. Conditional libm
    sin/cos accuracy is widened by 2**-52 per call; unlike exact rational
    trigonometry this is not a platform attestation. The FW branch is valid
    only when all represented computed centuries lie within [-50, 50].
    """
    if isinstance(tt_anchor_jd, bool) or not isinstance(tt_anchor_jd, (int, float)):
        raise ValueError("TT anchor must be a finite numeric Julian day")
    anchor = float(tt_anchor_jd)
    if not math.isfinite(anchor):
        raise ValueError("TT anchor must be a finite numeric Julian day")
    if not isinstance(tt_offset_days, I):
        raise TypeError("TT offsets must be a RationalInterval")

    try:
        def add(a, b):
            return _rounded(a + b)

        def mul(a, b):
            return _rounded(a * b)

        def centuries(jd):
            return _rounded(add(jd, -I.point(2451545.0)) / I.point(36525.0))

        def poly(t, coefficients):
            result = I.point(coefficients[0])
            for power, coefficient in enumerate(coefficients[1:], 1):
                # Python's T**n is assumed correctly rounded for these powers.
                term = mul(I.point(coefficient), _rounded(t ** power))
                result = add(result, term)
            return result

        def mean_eps(jd):
            result = poly(centuries(jd), (84381.406, -46.836769, -0.0001831,
                                         0.00200340, -0.000000576, -0.0000000434))
            return _rounded(result / I.point(3600.0))

        def trig(angle):
            exact = sin_cos_enclosure(angle)
            error = I(-Fraction(1, 2**52), Fraction(1, 2**52))
            return _rounded(exact.sine + error), _rounded(exact.cosine + error)

        zero, one = I.point(0), I.point(1)

        def rx(angle):
            s, c = trig(angle)
            return ((one, zero, zero), (zero, c, s), (zero, -s, c))

        def rz(angle):
            s, c = trig(angle)
            return ((c, s, zero), (-s, c, zero), (zero, zero, one))

        def matmul(a, b):
            return tuple(tuple(add(add(mul(a[i][0], b[0][j]), mul(a[i][1], b[1][j])),
                                   mul(a[i][2], b[2][j])) for j in range(3)) for i in range(3))

        jd = _rounded(I.point(anchor) + tt_offset_days)
        t = centuries(jd)
        if t.lo < -50 or t.hi > 50:
            raise EclipsePhasePoleUnavailable("FW/Vondrak branch is outside or crosses the proved domain")
        gamb = mul(poly(t, (-0.052928, 10.556378, 0.4932044, -0.00031238,
                            -0.000002788, 0.0000000260)), I.point(ARCSEC2RAD))
        phib = mul(poly(t, (84381.412819, -46.811016, 0.0511268, 0.00053289,
                            -0.000000440, -0.0000000176)), I.point(ARCSEC2RAD))
        psib = mul(poly(t, (-0.041775, 5038.481484, 1.5584175, -0.00018522,
                            -0.000026452, -0.0000000148)), I.point(ARCSEC2RAD))
        rebuilt_jd = add(I.point(2451545.0), mul(t, I.point(36525.0)))
        epsa = mul(mean_eps(rebuilt_jd), _rounded(I.point(math.pi) / I.point(180.0)))
        precession = matmul(rx(-epsa), matmul(rz(-psib), matmul(rx(phib), rz(gamb))))
        mean_angle = mul(mean_eps(jd), I.point(DEG2RAD))
        mean_matrix = matmul(rx(mean_angle), precession)
        return ConditionalMeanEclipticPole(anchor, tt_offset_days, t, mean_matrix[2], precession, mean_matrix)
    except (IntervalBudgetError, IntervalDomainError, OverflowError) as exc:
        raise EclipsePhasePoleUnavailable("FW pole arithmetic exceeded its domain or budget") from exc


def bound_mean_ecliptic_cross(
    pole: ConditionalMeanEclipticPole,
    sun: tuple[I, I, I],
    moon: tuple[I, I, I],
) -> I:
    """Bound the exact pole dot (Sun cross Moon), in squared kilometres.

    This is a mathematical direction diagnostic, not a proof that the
    rounded apparent serving longitudes or their phase residual exclude zero.
    """
    if not isinstance(pole, ConditionalMeanEclipticPole):
        raise TypeError("conditional mean-ecliptic pole required")
    if (not isinstance(sun, tuple) or not isinstance(moon, tuple) or len(sun) != 3 or len(moon) != 3
            or not all(isinstance(value, I) for value in (*sun, *moon))):
        raise TypeError("Sun and Moon must be three RationalInterval components")
    cross = (sun[1] * moon[2] - sun[2] * moon[1],
             sun[2] * moon[0] - sun[0] * moon[2],
             sun[0] * moon[1] - sun[1] * moon[0])
    return sum((p * c for p, c in zip(pole.pole, cross)), I.point(0)).quantize_outward(128)


def bound_mean_ecliptic_projection(
    pole: ConditionalMeanEclipticPole, vector: tuple[I, I, I],
) -> tuple[I, I, I]:
    """Bound exact products of the reference mean matrix and vector.

    This reference projection helps detect degenerate directions. It is not
    the nutated, rounded projection used by actual apparent longitudes.
    """
    if not isinstance(pole, ConditionalMeanEclipticPole):
        raise TypeError("conditional mean-ecliptic pole required")
    if not isinstance(vector, tuple) or len(vector) != 3 or not all(isinstance(x, I) for x in vector):
        raise TypeError("vector must have three RationalInterval components")
    return tuple(
        sum((element * component for element, component in zip(row, vector)), I.point(0)).quantize_outward(128)
        for row in pole.mean_matrix
    )
