"""
Moira — Shared Local-Angle Branch Doctrine
==========================================

Archetype: Engine helper

Purpose
-------
Single canonical implementation of the angle helpers whose result depends on a
branch choice rather than on arithmetic alone.  A circular result is not
settled by its formula: it also needs a declared normalization and a declared
tie rule.  Those two decisions are the content of this module.

Boundary declaration
--------------------
Owns:  circular normalization post-conditions and branch-selection doctrine for
       the Ascendant-from-ARMC computation.
Delegates: trigonometric constants to ``moira.constants``; the epoch, nutation
       and obliquity reductions that produce an ARMC stay with the callers.

Import-time side effects: None

Public surface (module-private by name; re-exported by consumers)
----------------------------------------------------------------
``_asc_from_armc`` — eastern ecliptic horizon intersection.
"""

from __future__ import annotations

import math

from .constants import DEG2RAD, RAD2DEG


_RISING_RATE_TIE_TOLERANCE = 64.0 * math.ulp(1.0)


def _sin_hour_angle(longitude: float, armc_r: float, eps_r: float) -> float:
    """Sine of local hour angle for an ecliptic point at latitude zero."""
    lam_r = longitude * DEG2RAD
    right_ascension = math.atan2(
        math.sin(lam_r) * math.cos(eps_r),
        math.cos(lam_r),
    )
    return math.sin(armc_r - right_ascension)


def _asc_from_armc(armc: float, obliquity: float, lat: float) -> float:
    """Ascendant from ARMC, obliquity, and geographic latitude.

    The governing object is the eastern intersection of the ecliptic with the
    local horizon: the ecliptic longitude whose altitude is zero while rising.
    ``tan(ASC) = -cos(ARMC) / (sin(eps)*tan(phi) + cos(eps)*sin(ARMC))``
    (Meeus, "Astronomical Algorithms" Ch. 24) is satisfied by two longitudes
    180 degrees apart — the rising and the setting intersection — so the
    formula alone does not determine a result. For numerical evaluation away
    from the poles, both sides are multiplied by ``cos(phi)`` so the helper
    avoids explicitly evaluating ``tan(phi)``.

    Branch doctrine
        ``atan2`` yields ``raw``; ``alt = raw + 180`` is the other root.  For
        an ecliptic point, local hour angle is ``H = ARMC - RA``.  Its altitude
        changes at rate ``-cos(phi) * cos(dec) * sin(H)`` as local sidereal time
        advances.  At every non-polar latitude exactly one root has positive
        vertical rate (``sin(H) < 0``); that rising root is the Ascendant.
        This tests the actual celestial-coordinate branch instead of comparing
        ecliptic longitude with right ascension.

    Polar degeneracy
        At exactly either geographic pole, altitude has no rising/setting
        derivative under rotation, so the branch is not astronomically
        distinguishable. The deterministic tie is ``raw``, the principal root
        of the limiting tangent formula. Callers that must not publish an undefined
        polar Ascendant must refuse the latitude rather than rely on this tie.

    Normalization post-condition
        The result is a circular longitude in the half-open range [0, 360).
        The final clamp is required, not redundant: ``(-delta) % 360.0`` returns
        exactly ``360.0`` once ``delta`` is below half a unit in the last place
        at 360, which the ``atan2`` branch does reach at a degenerate horizon.

    Raises:
        None under normal operation.

    Side effects:
        None
    """
    armc_r = armc * DEG2RAD
    eps_r  = obliquity * DEG2RAD
    lat_r  = lat * DEG2RAD

    cos_lat = math.cos(lat_r)
    y = -math.cos(armc_r) * cos_lat
    x = (
        math.sin(armc_r) * math.cos(eps_r) * cos_lat
        + math.sin(eps_r) * math.sin(lat_r)
    )
    raw = math.atan2(y, x) * RAD2DEG % 360.0

    alt      = (raw + 180.0) % 360.0

    if abs(lat) == 90.0:
        chosen = raw
    else:
        raw_is_rising = _sin_hour_angle(raw, armc_r, eps_r) < -_RISING_RATE_TIE_TOLERANCE
        alt_is_rising = _sin_hour_angle(alt, armc_r, eps_r) < -_RISING_RATE_TIE_TOLERANCE
        if raw_is_rising != alt_is_rising:
            chosen = raw if raw_is_rising else alt
        else:
            # A floating-point tie at a meridional/polar degeneracy keeps the
            # principal algebraic root.  It is not claimed to be rising.
            chosen = raw
    return 0.0 if chosen >= 360.0 else chosen


__all__ = ["_asc_from_armc"]
