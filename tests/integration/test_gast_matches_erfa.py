"""Greenwich apparent sidereal time against SOFA/ERFA ``gst06a`` (authority validation).

Python ``apparent_sidereal_time`` and its native counterpart must use the IAU 2006 mean
obliquity in the equation of the equinoxes (SOFA ``iauEe00``) whatever obliquity the caller
passes, so the result no longer depends on the true obliquity used for horizon geometry.
Compared at 12 epochs from 1900 to 2100; angles in arcseconds of rotation.
"""
import math

import pytest

from moira.julian import apparent_sidereal_time, apparent_sidereal_time_at, ut_to_tt
from moira.obliquity import nutation, true_obliquity

erfa = pytest.importorskip("erfa")

_EPOCHS = (
    2415020.5, 2430000.5, 2442413.5, 2447892.5, 2451545.0, 2455197.5,
    2458849.5, 2460676.5, 2461343.5, 2462502.5, 2469807.5, 2488069.5,
)
# 0.15 mas.  GMST here is evaluated from a UT1 argument, so the TT-only precession
# polynomial term is off by ΔT * 4612"/cy ≈ 1.0e-4" (the TT-aware route has no such offset).
# The equation-of-the-equinoxes obliquity convention, previously 2.6e-4", is now exact.
_TOL_ARCSEC = 1.5e-4


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
