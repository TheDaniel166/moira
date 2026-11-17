"""Find a Moon-phase crossing within a bounded eclipse-search window.

This is an ordering aid for the existing eclipse search, not a proof that a
bounded window contains every phase. The caller supplies a short window in
which the same continuous phase branch is expected and determines whether it
has sufficient ephemeris coverage. Provider failures deliberately propagate.
"""
from __future__ import annotations

import math

from .phenomena import _sun_moon_phase_angle


class PhaseWindowUnresolved(ArithmeticError):
    """A window endpoint does not contain enough phase information."""


def _phase_crossing_in_window(
    phase_name: str,
    start_jd: float,
    end_jd: float,
    reader,
) -> float | None:
    """Return the represented crossing of one phase branch, if bracketed.

    The local signed phase residual is valid only within 90 degrees of the
    requested target. A short-window crossing is refined until the bracketing
    Julian days are adjacent floats. Choosing the upper end makes results
    independent of the input bracket when the evaluated residual is monotone
    and has one crossing. ``None`` means no qualifying endpoint bracket was
    found, not a proof that the interval contains no crossing. This routine
    is not an interval certificate or error bound. No evaluations occur
    outside the supplied interval.
    """
    if phase_name == "New Moon":
        target = 0.0
    elif phase_name == "Full Moon":
        target = 180.0
    else:
        raise ValueError("phase_name must be 'New Moon' or 'Full Moon'")
    if not math.isfinite(start_jd) or not math.isfinite(end_jd) or start_jd >= end_jd:
        raise ValueError("phase search window must have finite ordered bounds")

    def residual(jd: float) -> float:
        angle = _sun_moon_phase_angle(jd, reader)
        if not math.isfinite(angle):
            raise ValueError("phase calculation returned a non-finite angle")
        return (angle - target + 180.0) % 360.0 - 180.0

    left, right = start_jd, end_jd
    fl, fr = residual(left), residual(right)
    if abs(fl) >= 90.0 or abs(fr) >= 90.0:
        return None
    if fr == 0.0:
        raise PhaseWindowUnresolved(
            "phase residual is zero at the window end; the zero plateau may extend beyond it"
        )
    if fl != 0.0 and (fl > 0.0) == (fr > 0.0):
        return None

    positive_left = fl > 0.0 if fl != 0.0 else fr < 0.0
    for _ in range(128):
        midpoint = left + (right - left) / 2.0
        if midpoint == left or midpoint == right:
            break
        fm = residual(midpoint)
        # Assign a rounded zero to the lower side of the bracket. This makes
        # the upper adjacent float deterministic for a monotone zero plateau.
        if fm == 0.0 or (fm > 0.0) == positive_left:
            left = midpoint
        else:
            right = midpoint
    return right
