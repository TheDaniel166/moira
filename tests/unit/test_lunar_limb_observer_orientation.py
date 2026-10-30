"""Earth orientation of the SPICE-route lunar-limb observer (authority validation).

``moira.lunar_limb._observer_state_j2000`` places the observer in J2000 with the IERS/SOFA
chain: polar motion, Earth rotation at UT1, equinox terms and precession-nutation at TT.  It
replaced SPICE's ``IAU_EARTH`` frame, whose prime meridian turns with dynamical time and so
rotated the observer by Delta-T times the Earth's rotation rate (0.29 degrees, ~32 km, in 2026).

Authority: ERFA ``c2t06a`` (celestial-to-terrestrial matrix, IAU 2006/2000A, polar motion from
Moira's loaded EOP) applied to the WGS84 station vector from ``gd2gc``.  Measured agreement over
four epochs 2000-2090: position <= 1.0e-6 km (1 mm), velocity <= 5.6e-7 km/s.  Tolerances below
are 10x and 9x those bounds.  The velocity is the diurnal rotation velocity omega x r.
"""
import math

import pytest

from moira.julian import julian_day, utc_to_tt, utc_to_ut1
from moira.lunar_limb import _observer_state_j2000
from moira.polar_motion import PolarMotionRegistry

erfa = pytest.importorskip("erfa")

_ARCSEC_TO_RAD = math.pi / 648000.0
_OMEGA_RAD_S = 7.292115e-5
_POSITION_TOL_KM = 1.0e-5
_VELOCITY_TOL_KM_S = 5.0e-6

_EPOCHS = (
    (2000, 1, 1, 12.0),
    (2026, 10, 30, 12.0),
    (2026, 10, 30, 2.0),
    (2090, 6, 1, 12.0),
)
_STATION = (40.0, -75.0, 250.0)  # latitude, east longitude (degrees), elevation (m)


def _norm(vector) -> float:
    return math.sqrt(sum(component * component for component in vector))


def _reference_state(ut1: float, tt: float):
    lat, lon, elevation_m = _STATION
    xp, yp = PolarMotionRegistry.polar_motion_at(ut1)
    celestial_to_terrestrial = erfa.c2t06a(
        tt, 0.0, ut1, 0.0, xp * _ARCSEC_TO_RAD, yp * _ARCSEC_TO_RAD
    ).tolist()
    itrs = [value / 1000.0 for value in erfa.gd2gc(1, math.radians(lon), math.radians(lat), elevation_m).tolist()]
    rotation_of_station = (-_OMEGA_RAD_S * itrs[1], _OMEGA_RAD_S * itrs[0], 0.0)

    def to_celestial(vector):
        return tuple(
            sum(celestial_to_terrestrial[row][column] * vector[row] for row in range(3))
            for column in range(3)
        )

    return to_celestial(itrs), to_celestial(rotation_of_station)


@pytest.mark.parametrize(("year", "month", "day", "hour"), _EPOCHS)
def test_observer_state_matches_erfa_c2t06a(year, month, day, hour) -> None:
    jd_utc = julian_day(year, month, day, hour)
    ut1, tt = utc_to_ut1(jd_utc), utc_to_tt(jd_utc)
    position, velocity = _observer_state_j2000(*_STATION[:2], _STATION[2], ut1, tt)
    ref_position, ref_velocity = _reference_state(ut1, tt)
    assert _norm([a - b for a, b in zip(position, ref_position)]) < _POSITION_TOL_KM
    assert _norm([a - b for a, b in zip(velocity, ref_velocity)]) < _VELOCITY_TOL_KM_S


def test_earth_rotation_follows_ut1_not_dynamical_time() -> None:
    """Shifting UT1 by Delta-T turns the observer; shifting only TT barely moves it."""
    jd_utc = julian_day(2026, 10, 30, 12.0)
    ut1, tt = utc_to_ut1(jd_utc), utc_to_tt(jd_utc)
    delta_t_s = (tt - ut1) * 86400.0
    base, _ = _observer_state_j2000(*_STATION[:2], _STATION[2], ut1, tt)

    later_ut1, _ = _observer_state_j2000(*_STATION[:2], _STATION[2], ut1 + delta_t_s / 86400.0, tt)
    later_tt, _ = _observer_state_j2000(*_STATION[:2], _STATION[2], ut1, tt + delta_t_s / 86400.0)

    def separation_deg(a, b):
        cosine = sum(x * y for x, y in zip(a, b)) / (_norm(a) * _norm(b))
        return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))

    # Delta-T of ~69 s of Earth rotation is 0.29 degrees about the pole (about 32 km at the
    # equator); the station's own direction turns by that angle times cos(geocentric latitude).
    geocentric_latitude = math.asin(base[2] / _norm(base))
    expected_deg = math.degrees(_OMEGA_RAD_S * delta_t_s) * math.cos(geocentric_latitude)
    assert separation_deg(base, later_ut1) == pytest.approx(expected_deg, rel=2e-3)
    # The same 69 s on the TT side only changes precession/nutation by ~1e-9 degrees.
    assert separation_deg(base, later_tt) < 1.0e-6
