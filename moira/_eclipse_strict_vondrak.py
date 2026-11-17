"""Opt-in checked-RN scalar Vondrak precession for strict phase samples.

This follows the arithmetic expression order of Moira's long-term precession
using exact-rational checked rounding and strict mathematical sine and cosine.
It is a distinct scalar policy, not an attestation of the legacy precession,
native code, platform environment, source, ephemeris, or physical accuracy.
"""
from __future__ import annotations

import math

from . import precession
from ._eclipse_strict_phase import EclipseStrictPhaseUnavailable, _add, _div, _mul, _norm, _sqrt
from ._eclipse_strict_trig import strict_scalar_sin_cos
from .constants import ARCSEC2RAD


def _series(t: float, terms, polynomials) -> tuple[float, float]:
    """Evaluate the two long-term pole coordinates in serving order."""
    w = _mul(_mul(2.0, math.pi), t)
    first = second = 0.0
    for period, a_cos, b_cos, a_sin, b_sin in terms:
        angle = _div(w, period)
        trig = strict_scalar_sin_cos(angle)
        first = _add(first, _add(_mul(trig.cosine, a_cos), _mul(trig.sine, a_sin)))
        second = _add(second, _add(_mul(trig.cosine, b_cos), _mul(trig.sine, b_sin)))

    def polynomial(coefficients):
        c0, c1, c2, c3 = coefficients
        return _add(c0, _mul(t, _add(c1, _mul(t, _add(c2, _mul(t, c3))))))

    first = _mul(_add(first, polynomial(polynomials[0])), ARCSEC2RAD)
    second = _mul(_add(second, polynomial(polynomials[1])), ARCSEC2RAD)
    return first, second


def _clamped_z(first: float, second: float) -> float:
    square = _add(_add(1.0, -_mul(first, first)), -_mul(second, second))
    return 0.0 if square < 0.0 else _sqrt(square)


def _ecliptic_pole(t: float) -> tuple[float, float, float]:
    p, q = _series(t, precession._VONDRAK_PQPER, precession._VONDRAK_PQPOL)
    z = _clamped_z(p, q)
    trig = strict_scalar_sin_cos(precession._VONDRAK_EPS0)
    return (
        p,
        _add(_mul(-q, trig.cosine), -_mul(z, trig.sine)),
        _add(_mul(-q, trig.sine), _mul(z, trig.cosine)),
    )


def _equatorial_pole(t: float) -> tuple[float, float, float]:
    x, y = _series(t, precession._VONDRAK_XYPER, precession._VONDRAK_XYPOL)
    return x, y, _clamped_z(x, y)


def _cross(a, b):
    return (
        _add(_mul(a[1], b[2]), -_mul(a[2], b[1])),
        _add(_mul(a[2], b[0]), -_mul(a[0], b[2])),
        _add(_mul(a[0], b[1]), -_mul(a[1], b[0])),
    )


def strict_vondrak_precession_matrix(tt_jd: float) -> tuple[tuple[float, float, float], ...]:
    """Return the bias-inclusive Vondrak matrix under the strict scalar policy.

    Only finite TT values within the long-term model's +/-2000-century domain
    are admitted. An exactly zero rounded equinox norm is unavailable instead
    of silently returning an unnormalized singular basis. All trigonometry is
    supplied by the strict scalar helper; platform sine and cosine are unused.
    """
    if isinstance(tt_jd, bool) or not isinstance(tt_jd, (int, float)):
        raise ValueError("TT epoch must be finite")
    try:
        tt = float(tt_jd)
    except OverflowError as exc:
        raise ValueError("TT epoch must be finite") from exc
    if not math.isfinite(tt):
        raise ValueError("TT epoch must be finite")
    t = _div(_add(tt, -2451545.0), 36525.0)
    if abs(t) > 2000.0:
        raise EclipseStrictPhaseUnavailable("strict Vondrak epoch is outside its admitted domain")
    equator = _equatorial_pole(t)
    ecliptic = _ecliptic_pole(t)
    raw = _cross(equator, ecliptic)
    norm = _norm(raw)
    if norm == 0.0:
        raise EclipseStrictPhaseUnavailable("strict Vondrak equinox norm is singular")
    equinox = tuple(_div(component, norm) for component in raw)
    middle = _cross(equator, equinox)
    dx = _mul(-0.016617, ARCSEC2RAD)
    de = _mul(-0.0068192, ARCSEC2RAD)
    dr = _mul(-0.0146, ARCSEC2RAD)

    def biased(row):
        return (
            _add(_add(row[0], -_mul(row[1], dr)), _mul(row[2], dx)),
            _add(_add(_mul(row[0], dr), row[1]), _mul(row[2], de)),
            _add(_add(_mul(-row[0], dx), -_mul(row[1], de)), row[2]),
        )

    return tuple(biased(row) for row in (equinox, middle, equator))
