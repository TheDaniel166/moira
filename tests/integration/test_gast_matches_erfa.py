"""Greenwich apparent sidereal time against SOFA/ERFA ``gst06a`` (authority validation).

Python ``apparent_sidereal_time`` and its native counterpart must use the IAU 2006 mean
obliquity in the equation of the equinoxes (SOFA ``iauEe00``) whatever obliquity the caller
passes, so the result no longer depends on the true obliquity used for horizon geometry.
Time scales follow SOFA: Earth rotation at UT1, GMST precession polynomial, mean obliquity and
complementary terms at TT.  Compared at 12 epochs from 1900 to 2100 against ``gst06a``, and
over -2000..2500 against ``gmst06 + ee00`` (isolating the time-scale arithmetic from the
nutation model); angles in arcseconds of rotation.
"""
import math

import pytest

from moira.julian import (
    apparent_sidereal_time, apparent_sidereal_time_at, earth_rotation_angle,
    greenwich_mean_sidereal_time, ut_to_tt,
)
from moira.obliquity import nutation, true_obliquity

erfa = pytest.importorskip("erfa")

_EPOCHS = (
    2415020.5, 2430000.5, 2442413.5, 2447892.5, 2451545.0, 2455197.5,
    2458849.5, 2460676.5, 2461343.5, 2462502.5, 2469807.5, 2488069.5,
)
# 0.05 mas.  Measured maximum over these epochs is 2.7e-5": Moira's IAU 2000A nutation versus
# ERFA's nut06a (P03-adjusted, ~0.03 mas at 1900) and the 8-term complementary series.  The
# TT-only terms are evaluated at TT, so no ΔT-sized offset (1.0e-4" in 2026) remains.
_TOL_ARCSEC = 5e-5
# 5 µas.  Same nutation fed to both sides, so only the time-scale arithmetic and the truncated
# complementary series differ; measured maximum 2.6e-6" over -2000..2500.
_TOL_LONG_BASELINE_ARCSEC = 5e-6
_LONG_BASELINE = (
    990575.5, 1538719.5, 1721059.5, 2086302.5, 2305447.5,
    2415020.5, 2451545.0, 2488069.5, 2634166.5,
)


def _wrapped_arcsec(a_deg: float, b_deg: float) -> float:
    return abs((a_deg - b_deg + 180.0) % 360.0 - 180.0) * 3600.0


@pytest.mark.parametrize("jd_ut", _EPOCHS)
def test_apparent_sidereal_time_at_matches_gst06a(jd_ut: float) -> None:
    jd_tt = ut_to_tt(jd_ut)
    ref = math.degrees(erfa.gst06a(jd_ut, 0.0, jd_tt, 0.0)) % 360.0
    assert _wrapped_arcsec(apparent_sidereal_time_at(jd_ut), ref) < _TOL_ARCSEC


@pytest.mark.parametrize("jd_ut", _EPOCHS)
def test_supplied_obliquity_does_not_change_gast(jd_ut: float) -> None:
    dpsi, _ = nutation(ut_to_tt(jd_ut))
    base = apparent_sidereal_time(jd_ut, dpsi, true_obliquity(ut_to_tt(jd_ut)))
    for eps in (0.0, 20.0, 23.4392911, 25.0):
        assert apparent_sidereal_time(jd_ut, dpsi, eps) == base


@pytest.mark.parametrize("jd_ut", _LONG_BASELINE)
def test_apparent_sidereal_time_matches_gmst06_plus_ee00_over_long_baseline(jd_ut: float) -> None:
    jd_tt = ut_to_tt(jd_ut)
    dpsi, _ = nutation(jd_tt)
    epsa = erfa.obl06(jd_tt, 0.0)
    ref = math.degrees(erfa.anp(erfa.gmst06(jd_ut, 0.0, jd_tt, 0.0)
                                + erfa.ee00(jd_tt, 0.0, epsa, math.radians(dpsi))))
    assert _wrapped_arcsec(apparent_sidereal_time(jd_ut, dpsi, 0.0), ref) < _TOL_LONG_BASELINE_ARCSEC


@pytest.mark.parametrize("jd_ut", _LONG_BASELINE)
def test_gmst_matches_gmst06_at_tt_over_long_baseline(jd_ut: float) -> None:
    jd_tt = ut_to_tt(jd_ut)
    ref = math.degrees(erfa.gmst06(jd_ut, 0.0, jd_tt, 0.0)) % 360.0
    assert _wrapped_arcsec(greenwich_mean_sidereal_time(jd_ut), ref) < 1e-6
    assert _wrapped_arcsec(greenwich_mean_sidereal_time(jd_ut, jd_tt), ref) < 1e-6


@pytest.mark.parametrize("jd_ut", _LONG_BASELINE)
def test_earth_rotation_angle_matches_era00_over_long_baseline(jd_ut: float) -> None:
    ref = math.degrees(erfa.era00(jd_ut, 0.0)) % 360.0
    # 1 µas.  Both sides sum ~4e3 turns of 0.0027378*D at -2000 before reducing mod one, so
    # binary64 rounding there is ~4.5e-13 turn ≈ 0.6 µas; measured maximum 0.34 µas.  The
    # previous 1.0027378*D form was off by 0.3 mas (300 µas) at the same epoch.
    assert _wrapped_arcsec(earth_rotation_angle(jd_ut), ref) < 1e-6


def test_explicit_jd_tt_is_used_verbatim_and_default_derives_ut_to_tt() -> None:
    jd_ut = 2461041.5
    jd_tt = ut_to_tt(jd_ut)
    dpsi, _ = nutation(jd_tt)
    assert apparent_sidereal_time(jd_ut, dpsi, 0.0) == apparent_sidereal_time(jd_ut, dpsi, 0.0, jd_tt)
    assert greenwich_mean_sidereal_time(jd_ut) == greenwich_mean_sidereal_time(jd_ut, jd_tt)
    # One second of TT moves GMST by dGMST/dT * 1 s = 4612"/cy / 3.15576e9 s/cy = 1.46e-6".
    shifted = greenwich_mean_sidereal_time(jd_ut, jd_tt + 1.0 / 86400.0)
    base = greenwich_mean_sidereal_time(jd_ut, jd_tt)
    assert _wrapped_arcsec(shifted, base) == pytest.approx(1.4615e-6, rel=1e-3)

