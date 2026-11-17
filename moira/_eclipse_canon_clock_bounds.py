"""Bound Moira's stepwise NASA catalog clock on a finite calendar domain.

This private layer concerns the *implemented month-midpoint convention* in
``eclipse_canon``, not the continuous-year NASA clock or the default native
reader-bound clock. It encloses only successfully returned binary64 values and
does not prove that an inverse exists or is unique at a monthly jump.

The conditional contract requires unchanged clock/calendar source and binary,
including the references imported by ``eclipse_canon`` and the selected
Python/native calendar implementation; deterministic same-environment month
evaluations; and binary64 round-to-nearest. Floating-point settings must remain
stable from construction of the cached global month hull through every later
use of that hull, not merely within individual calls. The identity checks in
this module cannot attest all of these premises. No runtime attestation or
physical Delta-T accuracy is implied.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import math

from . import eclipse_canon as _canon
from . import julian as _julian
from ._eclipse_interval import RationalInterval
from ._eclipse_interval_roots import EnclosureUnavailable


class CanonClockBoundsUnavailable(EnclosureUnavailable):
    """The requested clock domain or computational budget is unsupported."""


_SOURCE_FIRST_YEAR = -3000
_SOURCE_LAST_YEAR = 4000
_MAX_INTERVAL_DAYS = 400
_JULIAN_DAY_FN = _julian.julian_day
_CALENDAR_FN = _julian.calendar_from_jd
_DECIMAL_YEAR_FN = _julian.decimal_year
_DECIMAL_YEAR_FROM_JD_FN = _julian.decimal_year_from_jd
_CANON_DELTA_FN = _julian.delta_t_nasa_canon
_CANON_FORWARD_FN = _julian.ut_to_tt_nasa_canon
_CANON_INVERSE_FN = _julian.tt_to_ut_nasa_canon
_CATALOG_FORWARD_FN = _canon._ut_to_tt_nasa_catalog
_CATALOG_INVERSE_FN = _canon._tt_to_ut_nasa_catalog
_FORWARD_GUARDS = {
    name: getattr(_julian, name)
    for name in ("_require_representable_time_jd", "_require_representable_delta_t_year", "_require_finite")
}
_FORWARD_LIMITS = (_julian._MAX_ABS_TIME_JD, _julian._MAX_ABS_DELTA_T_YEAR)
_SOURCE_FIRST_JD = _JULIAN_DAY_FN(_SOURCE_FIRST_YEAR, 1, 1)
_SOURCE_END_JD = _JULIAN_DAY_FN(_SOURCE_LAST_YEAR + 1, 1, 1)


@dataclass(frozen=True, slots=True)
class CanonClockBounds:
    """Conditional enclosure relative to one represented Julian-day anchor.

    The finite month list includes all calendar months that *might* be
    selected; conservative adjacent days can add unused months. The interval
    enclosure describes successful outputs. If the separate forward-totality
    flag is true, every represented forward input returns under the stated
    unchanged-source and arithmetic premises. Neither the inverse nor the
    physical Delta-T, source, or floating-point environment is attested.
    """

    direction: str
    anchor_jd: float
    input_offset_days: RationalInterval
    output_offset_days: RationalInterval
    possible_months: tuple[tuple[int, int], ...]
    policy: str = "NASA lunar catalog, proleptic-Gregorian month midpoint"
    source_and_arithmetic_attested: bool = False
    inverse_uniqueness_certified: bool = False
    successful_outputs_only: bool = True
    native_reader_clock_enclosed: bool = False
    physical_delta_t_accuracy_certified: bool = False
    forward_totality_conditionally_proved: bool = False
    unchanged_calendar_canon_source_and_arithmetic_required: bool = True


def _require_source_contract() -> None:
    """Refuse obvious source replacement; deeper source integrity is assumed."""
    if (_julian.julian_day is not _JULIAN_DAY_FN
            or _julian.calendar_from_jd is not _CALENDAR_FN
            or _julian.decimal_year is not _DECIMAL_YEAR_FN
            or _julian.decimal_year_from_jd is not _DECIMAL_YEAR_FROM_JD_FN
            or _julian.delta_t_nasa_canon is not _CANON_DELTA_FN
            or _julian.ut_to_tt_nasa_canon is not _CANON_FORWARD_FN
            or _julian.tt_to_ut_nasa_canon is not _CANON_INVERSE_FN
            or _canon._ut_to_tt_nasa_catalog is not _CATALOG_FORWARD_FN
            or _canon._tt_to_ut_nasa_catalog is not _CATALOG_INVERSE_FN
            or _canon.calendar_from_jd is not _CALENDAR_FN
            or _canon.decimal_year_from_jd is not _DECIMAL_YEAR_FROM_JD_FN
            or _canon.delta_t_nasa_canon is not _CANON_DELTA_FN
            or _canon.ut_to_tt_nasa_canon is not _CANON_FORWARD_FN
            or _canon.tt_to_ut_nasa_canon is not _CANON_INVERSE_FN):
        raise CanonClockBoundsUnavailable("canon clock source changed after bounds initialization")


def _require_forward_totality_sources() -> None:
    """Reject changed guards needed to establish the forward source domain."""
    if (any(getattr(_julian, name) is not fn for name, fn in _FORWARD_GUARDS.items())
            or (_julian._MAX_ABS_TIME_JD, _julian._MAX_ABS_DELTA_T_YEAR) != _FORWARD_LIMITS
            or _FORWARD_LIMITS != (40_000_000.0, 100_000.0)):
        raise CanonClockBoundsUnavailable("canon forward totality source changed")


def _anchor_and_input(anchor_jd, offset_days, max_days):
    if isinstance(anchor_jd, bool) or not isinstance(anchor_jd, (int, float)):
        raise ValueError("anchor_jd must be a finite numeric Julian day")
    try:
        anchor = float(anchor_jd)
    except OverflowError as exc:
        raise ValueError("anchor_jd must be a finite numeric Julian day") from exc
    if not math.isfinite(anchor):
        raise ValueError("anchor_jd must be a finite numeric Julian day")
    if not isinstance(offset_days, RationalInterval):
        raise TypeError("offset_days must be a RationalInterval")
    if type(max_days) is not int or not 1 <= max_days <= _MAX_INTERVAL_DAYS:
        raise ValueError("max_days must be an integer from 1 to 400")
    interval = RationalInterval.point(anchor) + offset_days
    if interval.width > max_days:
        raise CanonClockBoundsUnavailable("requested clock interval exceeds day budget")
    return anchor, interval


def _months_for_interval(interval: RationalInterval, *, max_days: int):
    """Enumerate a conservative calendar-day hull, including seam neighbors.

    In the admitted multi-millennium domain, calendar arithmetic first obtains
    ``floor(jd + 0.5)``. The extra integer day on each side covers rounding at
    representable midnight boundaries; year/month then depend only on that
    integer day in the unchanged Python and native calendar implementations.
    """
    # The extra days also keep every calendar probe inside the declared range.
    # Check before converting arbitrary rational endpoints to C/native dates.
    if interval.lo < _SOURCE_FIRST_JD + 2 or interval.hi > _SOURCE_END_JD - 2:
        raise CanonClockBoundsUnavailable("clock interval outside supported calendar domain")
    half = RationalInterval.point(0.5).lo
    first = (interval.lo + half) // 1 - 1
    last = (interval.hi + half) // 1 + 1
    if last - first > max_days + 3:
        raise CanonClockBoundsUnavailable("calendar enumeration exceeds day budget")
    months = set()
    for day_number in range(first, last + 1):
        year, month, _, _ = _CALENDAR_FN(float(day_number))
        if not _SOURCE_FIRST_YEAR <= year <= _SOURCE_LAST_YEAR:
            raise CanonClockBoundsUnavailable("clock interval outside supported calendar domain")
        if not 1 <= month <= 12:
            raise CanonClockBoundsUnavailable("calendar returned an invalid month")
        months.add((year, month))
    return tuple(sorted(months))


def _month_offsets(months):
    """Evaluate the exact represented per-month source values in day units."""
    values = []
    for year, month in months:
        year_coordinate = _DECIMAL_YEAR_FN(year, month)
        seconds = _CANON_DELTA_FN(year_coordinate)
        value = seconds / 86400.0
        if not math.isfinite(value):
            raise CanonClockBoundsUnavailable("canon Delta-T offset is non-finite")
        values.append(RationalInterval.point(value).lo)
    if not values:
        raise CanonClockBoundsUnavailable("no calendar month selected")
    return RationalInterval(min(values), max(values))


@lru_cache(maxsize=1)
def _global_offsets():
    """Enumerate every represented month in the admitted finite source range."""
    _require_source_contract()
    low = high = None
    for year in range(_SOURCE_FIRST_YEAR, _SOURCE_LAST_YEAR + 1):
        for month in range(1, 13):
            value = _CANON_DELTA_FN(_DECIMAL_YEAR_FN(year, month)) / 86400.0
            if not math.isfinite(value):
                raise CanonClockBoundsUnavailable("canon Delta-T source is non-finite")
            if low is None:
                low = high = value
            else:
                low, high = min(low, value), max(high, value)
    result = RationalInterval(low, high)
    # The inverse implementation searches adjacent calendar months around the
    # TT month. A <20-day global Delta-T makes its computed search span at most
    # three months; a one-year interior guard therefore contains those months.
    if result.magnitude >= 20:
        raise CanonClockBoundsUnavailable("canon Delta-T exceeds proved inverse search bound")
    return result


def _rounded_binary64_hull(interval: RationalInterval) -> RationalInterval:
    """Enclose binary64 nearest-rounded results by adjacent floats."""
    lo, hi = interval.to_float_bounds()
    return RationalInterval(lo, hi)


def bound_canon_catalog_ut1_to_tt(
    anchor_jd: float,
    offset_days: RationalInterval,
    *,
    max_days: int = 32,
    require_totality: bool = False,
) -> CanonClockBounds:
    """Enclose successful month-stepped canon UT1→TT evaluations.

    Both sides of all possible month boundaries are included in a single
    output hull. With ``require_totality=True``, the bounded calendar domain,
    actual enumerated month values and guarded forward source establish that
    every represented input returns a finite TT value, conditional on stable
    source/calendar/backend and binary64 arithmetic throughout. This proof is
    distinct from inverse existence or uniqueness, physical Earth rotation,
    an arbitrary explicit-year clock, and the native reader clock.
    """
    if type(require_totality) is not bool:
        raise ValueError("require_totality must be a bool")
    _require_source_contract()
    if require_totality:
        _require_forward_totality_sources()
    anchor, ut1 = _anchor_and_input(anchor_jd, offset_days, max_days)
    months = _months_for_interval(ut1, max_days=max_days)
    if require_totality and (ut1.lo < -_FORWARD_LIMITS[0] or ut1.hi > _FORWARD_LIMITS[0]):
        raise CanonClockBoundsUnavailable("canon forward input outside source domain")
    offsets = _month_offsets(months)
    tt = _rounded_binary64_hull(ut1 + offsets)
    return CanonClockBounds("UT1_TO_TT", anchor, offset_days,
                            tt - RationalInterval.point(anchor), months,
                            forward_totality_conditionally_proved=require_totality)


def bound_canon_catalog_tt_to_ut1(
    anchor_jd: float,
    offset_days: RationalInterval,
    *,
    max_days: int = 32,
) -> CanonClockBounds:
    """Enclose every successfully returned month-stepped canon TT→UT1 value.

    The implemented inverse can raise on monthly gaps and overlaps. This
    function does not decide whether the inverse succeeds, which branch is
    unique, or whether every real point has an inverse. Its conditional result
    bounds successful represented outputs only.
    """
    _require_source_contract()
    anchor, tt = _anchor_and_input(anchor_jd, offset_days, max_days)
    initial_months = _months_for_interval(tt, max_days=max_days)
    if any(year in (_SOURCE_FIRST_YEAR, _SOURCE_LAST_YEAR) for year, _ in initial_months):
        raise CanonClockBoundsUnavailable("inverse needs a full adjacent-year source guard")
    all_offsets = _global_offsets()
    broad_ut1 = _rounded_binary64_hull(tt - all_offsets)
    months = _months_for_interval(broad_ut1, max_days=max_days + 2)
    offsets = _month_offsets(months)
    ut1 = _rounded_binary64_hull(tt - offsets)
    return CanonClockBounds("TT_TO_UT1", anchor, offset_days,
                            ut1 - RationalInterval.point(anchor), months)
