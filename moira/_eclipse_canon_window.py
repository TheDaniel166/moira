"""Bounds for the existing month-stepped lunar canon search convention.

This module bounds the *implemented* 0.2-day TT optimizer neighborhood. It
does not certify physical eclipse discovery, a phase-search gate, or an
ephemeris model. The NASA month-midpoint policy and its finite representable
year domain determine the bound, independent of reader coverage metadata.
"""
from __future__ import annotations

from functools import lru_cache
import math

from .julian import _MAX_ABS_DELTA_T_YEAR, calendar_from_jd, delta_t_nasa_canon


_CANON_TT_HALF_WINDOW_DAYS = 0.2
_MAX_CALENDAR_SPAN_YEARS = 200_000
_SHORTEST_SUPPORTED_MONTH_DAYS = 20.0


class CanonPhaseOrderingUnsupported(NotImplementedError):
    """The admitted canon time policy cannot establish a phase-ordering bound."""


@lru_cache(maxsize=8)
def _month_delta_envelope(first_year: int, last_year: int) -> tuple[float, float, float]:
    """Return min, max, and maximum neighboring-month change, in seconds."""
    if last_year < first_year or last_year - first_year > _MAX_CALENDAR_SPAN_YEARS:
        raise CanonPhaseOrderingUnsupported("lunar canon search cannot bound the reader calendar coverage")
    low = math.inf
    high = -math.inf
    jump = 0.0
    previous = None
    for year in range(first_year, last_year + 1):
        for month in range(1, 13):
            delta = delta_t_nasa_canon(year + (month - 0.5) / 12.0)
            if not math.isfinite(delta):
                raise CanonPhaseOrderingUnsupported("lunar canon Delta-T bound is not finite")
            low = min(low, delta)
            high = max(high, delta)
            if previous is not None:
                jump = max(jump, abs(delta - previous))
            previous = delta
    return low, high, jump


def _canon_ut_half_window(reader, reference_jd_ut: float) -> float:
    """Bound UT separation for a canon phase and its 0.2-day TT maximum.

    For UT separation ``d``, at most ``d / 20 + 1`` month boundaries can be
    crossed, since 20 days is shorter than every calendar month in the policy.
    If the maximum adjacent-month Delta-T change over the entire representable
    year domain is ``J`` seconds, then
    ``d <= 0.2 + J * (d / 20 + 1) / 86400``. Solving this inequality gives
    the returned bound, provided its denominator is positive. All admitted
    month-midpoint values are enumerated once and cached; no reader coverage
    capability or one-month assumption is required.

    The bound concerns the finite binary64 convention in the implemented
    canon solver; it is not a model-wide proof of an eclipse maximum or phase.
    """
    if not math.isfinite(reference_jd_ut):
        raise ValueError("lunar canon phase-ordering reference must be finite")
    year = calendar_from_jd(reference_jd_ut)[0]
    limit = int(_MAX_ABS_DELTA_T_YEAR)
    if not -limit <= year < limit:
        raise CanonPhaseOrderingUnsupported("lunar canon reference is outside the Delta-T year domain")
    low, high, jump = _month_delta_envelope(-limit, limit - 1)
    # The policy values are binary64 computations. Add a guard for rounding
    # at both Delta-T endpoints rather than assuming exact subtraction.
    jump = math.nextafter(jump + 8 * max(math.ulp(low), math.ulp(high)), math.inf)
    denominator = 1.0 - jump / (_SHORTEST_SUPPORTED_MONTH_DAYS * 86400.0)
    if denominator <= 0.0:
        raise CanonPhaseOrderingUnsupported("lunar canon month jumps do not yield a finite UT bound")
    radius = (_CANON_TT_HALF_WINDOW_DAYS + jump / 86400.0) / denominator
    return math.nextafter(radius + 8 * math.ulp(reference_jd_ut), math.inf)
