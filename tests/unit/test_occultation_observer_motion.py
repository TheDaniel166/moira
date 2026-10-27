"""Independent ERFA checks of station transport and apparent stellar motion."""

import math

import pytest

from moira import occultations
from moira.constants import EARTH_ROTATION_RATE_RAD_PER_SEC
from moira.corrections import _observer_position_icrf
from moira.polar_motion import PolarMotionRegistry, polar_motion_matrix

erfa = pytest.importorskip("erfa")


@pytest.mark.parametrize("xp,yp", ((0.0, 0.0), (0.3, -0.2), (-0.4, 0.5)))
@pytest.mark.parametrize("station", (
    (0.0, 0.0, 0.0, 0.0),
    (51.5, -0.1, 123.0, 45.0),
    (-33.9, 151.2, 280.0, 250.0),
    (89.9, -170.0, 10.0, 1500.0),
    (27.79491666666667, -90.0, 250.0, 0.0),
))
def test_station_transport_matches_erfa_pvtob(monkeypatch, xp, yp, station):
    """pvtob note 3 permits GAST, giving true equinox-of-date coordinates."""
    monkeypatch.setattr(PolarMotionRegistry, "polar_motion_at",
                        classmethod(lambda cls, jd: (xp, yp)))
    lat, lon, lst, height = station
    expected = erfa.pvtob(
        math.radians(lon), math.radians(lat), height,
        xp * erfa.DAS2R, yp * erfa.DAS2R, 0.0,
        math.radians(lst - lon),
    )["p"] / 1000.0
    actual = _observer_position_icrf(
        lat, lon, lst, height, jd_ut=2460641.0,
        observer_frame="equatorial_of_date",
    )
    assert actual == pytest.approx(expected, rel=0.0, abs=1e-11)
    # Keep the public matrix direction unchanged, independently of its consumer.
    matrix = polar_motion_matrix(xp, yp)
    reference = erfa.pom00(xp * erfa.DAS2R, yp * erfa.DAS2R, 0.0)
    assert max(abs(matrix[i][j] - reference[i, j])
               for i in range(3) for j in range(3)) < 1e-14


@pytest.mark.parametrize("lat,lon,lst,height", (
    (27.79491666666667, -90.0, 250.0, 0.0),
    (-33.9, 151.2, 35.0, 250.0),
    (0.0, 0.0, 0.0, 0.0),
    (90.0, 0.0, 10.0, 0.0),
))
def test_nominal_star_diurnal_aberration_matches_erfa(
    monkeypatch, lat, lon, lst, height,
):
    """Isolate observer motion from the already-tested annual/frame stages."""
    ray = (0.6, 0.0, 0.8)
    identity = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    monkeypatch.setattr(occultations, "_ut1_to_ephemeris_tt", lambda jd, r: jd)
    monkeypatch.setattr(occultations, "_star_geometric_icrf_direction", lambda *a: ray)
    monkeypatch.setattr(occultations, "_earth_barycentric_state",
                        lambda *a: ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0)))
    monkeypatch.setattr(occultations, "_geocentric", lambda *a: (1e15, 0.0, 0.0))
    monkeypatch.setattr(occultations, "apply_deflection", lambda u, d: u)
    monkeypatch.setattr(occultations, "precession_matrix_equatorial", lambda jd: identity)
    monkeypatch.setattr(occultations, "nutation_matrix_equatorial", lambda jd: identity)
    monkeypatch.setattr(occultations, "local_sidereal_time", lambda *a: lst)
    monkeypatch.setattr(PolarMotionRegistry, "polar_motion_at",
                        classmethod(lambda cls, jd: (0.3, -0.2)))

    pv = erfa.pvtob(math.radians(lon), math.radians(lat), height,
                    0.3 * erfa.DAS2R, -0.2 * erfa.DAS2R, 0.0,
                    math.radians(lst - lon))
    # Match Moira's admitted IERS rotation rate. Position comes only from ERFA.
    x, y, _ = pv["p"]
    beta = (-y * EARTH_ROTATION_RATE_RAD_PER_SEC / 299792458.0,
            x * EARTH_ROTATION_RATE_RAD_PER_SEC / 299792458.0, 0.0)
    expected = erfa.ab(ray, beta, 1e100, math.sqrt(1.0 - sum(v*v for v in beta)))
    ra, dec, altitude = occultations._star_topocentric_equatorial(
        0.0, 0.0, 2460641.0, lat, lon, height, reader=object(),
    )
    actual = (math.cos(math.radians(dec)) * math.cos(math.radians(ra)),
              math.cos(math.radians(dec)) * math.sin(math.radians(ra)),
              math.sin(math.radians(dec)))
    assert actual == pytest.approx(expected, rel=0.0, abs=3e-16)
    expected_altitude = math.degrees(math.asin(
        math.sin(math.radians(lat)) * expected[2]
        + math.cos(math.radians(lat)) * (
            expected[0] * math.cos(math.radians(lst))
            + expected[1] * math.sin(math.radians(lst)))))
    assert altitude == pytest.approx(expected_altitude, rel=0.0, abs=1e-11)

    # The separately defined physical topographic ray must remain unboosted.
    physical_ra, physical_dec = occultations._star_physical_equatorial(
        0.0, 0.0, 2460641.0, reader=object(),
    )
    assert physical_ra == pytest.approx(0.0, abs=1e-13)
    assert physical_dec == pytest.approx(math.degrees(math.asin(0.8)), abs=1e-13)
