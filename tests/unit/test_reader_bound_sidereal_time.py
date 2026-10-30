"""Development-oracle checks of the new private two-scale clock reduction."""
import math
import pytest

from moira.julian import (
    _greenwich_mean_sidereal_time_at_tt, _local_sidereal_time_at_tt,
    greenwich_mean_sidereal_time, julian_day, ut_to_tt,
)
from moira.obliquity import nutation, mean_obliquity


@pytest.mark.parametrize("year", [1600, 1900, 2000, 2026, 2100])
def test_reader_bound_gmst_uses_tt_and_defaults_to_ut_to_tt(year):
    erfa = pytest.importorskip("erfa")
    ut1 = julian_day(year, 1, 1)
    tt = ut1 + 1  # Deliberately distinct scales, exposes using UT1 for both.
    expected = math.degrees(erfa.gmst06(ut1, 0, tt, 0))
    actual = _greenwich_mean_sidereal_time_at_tt(ut1, tt)
    assert abs((actual-expected+180) % 360-180) < 2e-7
    assert abs((actual-greenwich_mean_sidereal_time(ut1)+180) % 360-180) > 1e-5
    # An explicit equal pair is the caller's own choice and is honoured verbatim.
    assert greenwich_mean_sidereal_time(ut1, ut1) == _greenwich_mean_sidereal_time_at_tt(ut1, ut1)
    # Omitting jd_tt derives it with the default Delta-T policy, never reusing UT1 as TT.
    assert greenwich_mean_sidereal_time(ut1) == _greenwich_mean_sidereal_time_at_tt(ut1, ut_to_tt(ut1))


@pytest.mark.parametrize("year", [1600, 1900, 2000, 2026, 2100])
def test_reader_bound_last_matches_full_erfa_gast_within_existing_ct_approximation(year):
    erfa = pytest.importorskip("erfa")
    ut1 = julian_day(year, 1, 1)
    tt = ut1 + 1
    dpsi, _ = nutation(tt)
    actual = _local_sidereal_time_at_tt(ut1, tt, 77.209, dpsi, mean_obliquity(tt))
    expected = (math.degrees(erfa.gst06a(ut1, 0, tt, 0))+77.209) % 360
    assert abs((actual-expected+180) % 360-180) < 1e-6
