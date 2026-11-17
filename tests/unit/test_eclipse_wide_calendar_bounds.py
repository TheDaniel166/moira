"""Calendar source agreement and wide DE441 native clock controls."""
import math
import pytest

from moira import julian
from moira._eclipse_clock_provider import bound_native_ut1_to_tt
from moira._eclipse_interval import RationalInterval
from moira._eclipse_native_clock_bounds import _native_months_for_interval
from moira._ephemeris_time import _ut1_to_ephemeris_tt


@pytest.mark.parametrize("year", [-14999, -12000, -8001, -4801, -4713, -4712,
                                  -1, 0, 1, 12000, 14999])
@pytest.mark.parametrize("month", [1, 2, 3, 12])
def test_wide_calendar_year_month_seams(year, month):
    from moira import moira_native
    jd = julian.julian_day(year, month, 1)
    for value in (jd - 1, math.nextafter(jd, -math.inf), jd,
                  math.nextafter(jd, math.inf), jd + 1):
        py = julian.calendar_from_jd.__wrapped__(value)
        assert moira_native.calendar_from_jd(value) == py
        assert (py[0], py[1]) in _native_months_for_interval(RationalInterval.point(value), max_days=1)


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("jd", [-1200954.75, 6104045.25])
def test_wide_de441_clock_controls(planetary_reader, jd):
    receipt = bound_native_ut1_to_tt(planetary_reader, jd, RationalInterval.point(0))
    assert (RationalInterval.point(jd) + receipt.bounds.output_offset_days).contains(
        _ut1_to_ephemeris_tt(jd, planetary_reader)
    )
