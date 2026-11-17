"""Conditional Vondrak/P03 frame intervals for long-term phase policies.

This follows Moira's represented long-term precession series, clamped pole
square roots, equinox normalization and first-order bias. It assumes binary64
RN/gradual, correctly rounded sqrt/powers and absolute sin/cos error <=2**-52;
unchanged source/coefficients are required but not attested. The interval
trig itself is rational and also contains the correctly rounded strict policy.
Only one branch of 50 < |T| <= 200 centuries is admitted per box.
"""
from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import math

from . import precession
from ._eclipse_interval import IntervalBudgetError, IntervalDomainError, RationalInterval as I
from ._eclipse_interval_elementary import sin_cos_enclosure
from ._eclipse_interval_roots import EnclosureUnavailable
from ._eclipse_native_spk_bounds import _rounded
from ._eclipse_phase_pole import ConditionalMeanEclipticPole
from .constants import ARCSEC2RAD, DEG2RAD


class EclipseVondrakBoundsUnavailable(EnclosureUnavailable):
    """The long-term precession branch or normalization is unresolved."""


@dataclass(frozen=True, slots=True)
class ConditionalVondrakEclipticPole(ConditionalMeanEclipticPole):
    """Conditional long-term frame; not an apparent phase certificate."""

    arithmetic_model: str = (
        "binary64 RN/gradual; correctly rounded sqrt and integer powers; "
        "sin/cos absolute error <=2**-52; unchanged Vondrak source/coefficients"
    )


def bound_vondrak_mean_ecliptic_pole(tt_anchor_jd: float, tt_offset_days: I) -> ConditionalVondrakEclipticPole:
    """Enclose the selected long-term mean-ecliptic matrix for TT inputs."""
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

        def sub(a, b):
            return _rounded(a - b)

        def mul(a, b):
            return _rounded(a * b)

        def div(a, b):
            if b.contains_zero:
                raise EclipseVondrakBoundsUnavailable("long-term normalization denominator may vanish")
            return _rounded(a / b)

        def trig(angle):
            exact = sin_cos_enclosure(angle)
            error = I(-Fraction(1, 2**52), Fraction(1, 2**52))
            return _rounded(exact.sine + error), _rounded(exact.cosine + error)

        def sqrt_nonnegative(value):
            if value.hi < 0:
                return I.point(0)
            return _rounded(I(max(Fraction(0), value.lo), value.hi).sqrt(128))

        def cross(a, b):
            return (sub(mul(a[1], b[2]), mul(a[2], b[1])),
                    sub(mul(a[2], b[0]), mul(a[0], b[2])),
                    sub(mul(a[0], b[1]), mul(a[1], b[0])))

        def normalize(vector):
            squares = tuple(_rounded(x.square()) for x in vector)
            norm = sqrt_nonnegative(add(add(squares[0], squares[1]), squares[2]))
            if norm.contains_zero:
                raise EclipseVondrakBoundsUnavailable("long-term equinox norm may vanish")
            return tuple(div(x, norm) for x in vector)

        def mean_eps(jd):
            t = div(sub(jd, I.point(2451545.0)), I.point(36525.0))
            coeffs = (84381.406, -46.836769, -0.0001831, 0.00200340, -0.000000576, -0.0000000434)
            result = I.point(coeffs[0])
            for n, coefficient in enumerate(coeffs[1:], 1):
                result = add(result, mul(I.point(coefficient), _rounded(t ** n)))
            return div(result, I.point(3600.0))

        def matmul(a, b):
            return tuple(tuple(add(add(mul(a[i][0], b[0][j]), mul(a[i][1], b[1][j])),
                                   mul(a[i][2], b[2][j])) for j in range(3)) for i in range(3))

        jd = _rounded(I.point(anchor) + tt_offset_days)
        t = div(sub(jd, I.point(2451545.0)), I.point(36525.0))
        if not ((t.hi < -50 and t.lo >= -200) or (t.lo > 50 and t.hi <= 200)):
            raise EclipseVondrakBoundsUnavailable("FW/Vondrak branch or long-term domain requires subdivision")
        w = mul(mul(I.point(2.0), I.point(math.pi)), t)

        def longterm_series(periods, polynomials):
            first = second = I.point(0)
            for period, a_cos, b_cos, a_sin, b_sin in periods:
                sine, cosine = trig(div(w, I.point(period)))
                first = add(first, add(mul(cosine, I.point(a_cos)), mul(sine, I.point(a_sin))))
                second = add(second, add(mul(cosine, I.point(b_cos)), mul(sine, I.point(b_sin))))
            def polynomial(coeffs):
                return add(I.point(coeffs[0]), mul(t, add(I.point(coeffs[1]),
                           mul(t, add(I.point(coeffs[2]), mul(t, I.point(coeffs[3])))))))
            return (mul(add(first, polynomial(polynomials[0])), I.point(ARCSEC2RAD)),
                    mul(add(second, polynomial(polynomials[1])), I.point(ARCSEC2RAD)))

        p, q = longterm_series(precession._VONDRAK_PQPER, precession._VONDRAK_PQPOL)
        x, y = longterm_series(precession._VONDRAK_XYPER, precession._VONDRAK_XYPOL)
        w_pq = sqrt_nonnegative(sub(sub(I.point(1), _rounded(p.square())), _rounded(q.square())))
        w_xy = sqrt_nonnegative(sub(sub(I.point(1), _rounded(x.square())), _rounded(y.square())))
        s0, c0 = trig(I.point(precession._VONDRAK_EPS0))
        pecl = (p, sub(-mul(q, c0), mul(w_pq, s0)), add(-mul(q, s0), mul(w_pq, c0)))
        peqr = (x, y, w_xy)
        eqx = normalize(cross(peqr, pecl))
        mid = cross(peqr, eqx)
        raw = (eqx, mid, peqr)
        dx = mul(I.point(-0.016617), I.point(ARCSEC2RAD))
        de = mul(I.point(-0.0068192), I.point(ARCSEC2RAD))
        dr = mul(I.point(-0.0146), I.point(ARCSEC2RAD))
        matrix = tuple((add(sub(row[0], mul(row[1], dr)), mul(row[2], dx)),
                        add(add(mul(row[0], dr), row[1]), mul(row[2], de)),
                        add(sub(-mul(row[0], dx), mul(row[1], de)), row[2])) for row in raw)
        sine, cosine = trig(mul(mean_eps(jd), I.point(DEG2RAD)))
        zero, one = I.point(0), I.point(1)
        rotation = ((one, zero, zero), (zero, cosine, sine), (zero, -sine, cosine))
        mean_matrix = matmul(rotation, matrix)
        return ConditionalVondrakEclipticPole(anchor, tt_offset_days, t, mean_matrix[2], matrix, mean_matrix)
    except (IntervalBudgetError, IntervalDomainError, OverflowError) as exc:
        raise EclipseVondrakBoundsUnavailable("long-term frame arithmetic exceeded its domain or budget") from exc
