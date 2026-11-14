"""Observer-dependent comet light time and topocentric RA/Dec parity."""

from __future__ import annotations

from datetime import datetime
import math

import pytest

from moira import comets, planets
from moira._ephemeris_time import _ut1_to_ephemeris_tt
from moira.julian import jd_from_datetime, tt_to_tdb, utc_to_ut1
from moira.polar_motion import PolarMotionRegistry


_J2000 = 2451545.0
_C_KM_S = 299792.458
_COMET = "1P/Halley"
_RECEPTION_X_KM = 400_000.0
_RECEPTION_Y_KM = 3_000.0
_COMET_SPEED_KM_S = 30.0
_STATION_X_KM = 6_378.0


@pytest.fixture
def linear_comet_sky(monkeypatch):
    """Bind a linear comet and two known station offsets to the public sky path."""
    zero = (0.0, 0.0, 0.0)
    identity = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))

    class Reader:
        def position(self, center, target, jd_tt):
            return zero

        def position_and_velocity(self, center, target, jd_tt):
            return zero, zero

    class LinearComet:
        def __init__(self, first_tdb):
            self.first_tdb = first_tdb

        def position_tdb(self, center, target, tdb):
            assert (center, target) == (10, 1000001)
            if tdb < self.first_tdb:
                raise KeyError("No segment covers the retarded comet epoch")
            elapsed_seconds = (tdb - _J2000) * 86400.0
            return (_RECEPTION_X_KM, _RECEPTION_Y_KM + _COMET_SPEED_KM_S * elapsed_seconds, 0.0)

    reader = Reader()
    monkeypatch.setattr(planets, "_ut1_to_ephemeris_tt", lambda jd_ut, *_args, **_kwargs: jd_ut)
    monkeypatch.setattr(planets, "tt_to_tdb", lambda jd_tt: jd_tt)
    monkeypatch.setattr(planets, "_compose_rotation_matrix", lambda *_args, **_kwargs: identity)
    monkeypatch.setattr(
        planets, "_observer_position_icrf",
        lambda latitude, longitude, *_args, **_kwargs: (math.copysign(_STATION_X_KM, longitude), 0.0, 0.0),
    )
    monkeypatch.setattr(planets, "_observer_velocity_icrf", lambda *_args, **_kwargs: zero)

    def calculate(longitude, first_tdb=-math.inf):
        kernel = LinearComet(first_tdb)
        monkeypatch.setattr(comets, "_comet_kernel", lambda *_args: kernel)
        return planets.sky_position_at(
            _COMET, _J2000, 0.0, longitude, reader=reader,
            aberration=False, grav_deflection=False, refraction=False,
        )

    return calculate


@pytest.mark.parametrize("longitude", (-90.0, 90.0))
def test_comet_station_sets_light_time_against_the_analytic_solution(linear_comet_sky, longitude):
    sky = linear_comet_sky(longitude)
    x = _RECEPTION_X_KM - math.copysign(_STATION_X_KM, longitude)
    distance_sq = x * x + _RECEPTION_Y_KM**2
    dot = _RECEPTION_Y_KM * _COMET_SPEED_KM_S
    delay = distance_sq / (math.sqrt(dot**2 + (_C_KM_S**2 - _COMET_SPEED_KM_S**2) * distance_sq) + dot)
    y = _RECEPTION_Y_KM - _COMET_SPEED_KM_S * delay
    expected_ra = math.degrees(math.atan2(y, x))

    # The Type 13 reader's absolute TDB JD has a roughly 40 microsecond tick here.
    assert sky.right_ascension == pytest.approx(expected_ra, abs=2e-7, rel=0)
    assert sky.declination == 0.0
    assert sky.distance == pytest.approx(math.hypot(x, y), abs=1e-5, rel=0)


def test_comet_emission_coverage_depends_on_the_reception_station(linear_comet_sky):
    cutoff_tdb = _J2000 - _RECEPTION_X_KM / _C_KM_S / 86400.0
    assert math.isfinite(linear_comet_sky(90.0, cutoff_tdb).right_ascension)
    with pytest.raises(KeyError, match="retarded comet epoch"):
        linear_comet_sky(-90.0, cutoff_tdb)


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize(
    ("name", "epoch", "latitude", "longitude", "height_m"),
    [
        ("1P/Halley", "2000-01-01T12:00:00+00:00", 40.7128, -74.0060, 31.0),
        ("67P/Churyumov-Gerasimenko", "2021-11-12T00:00:00+00:00", -31.27, 149.06, 1165.0),
        ("2P/Encke", "2023-10-23T12:00:00+00:00", 51.477, 0.0, 46.0),
    ],
)
def test_comet_topocentric_apparent_place_matches_independent_erfa_reduction(
    small_body_reader_pool, name, epoch, latitude, longitude, height_m,
):
    erfa = pytest.importorskip("erfa")
    np = pytest.importorskip("numpy")
    reader = small_body_reader_pool
    body_id = comets.COMET_NAIF[name]
    jd_ut = utc_to_ut1(jd_from_datetime(datetime.fromisoformat(epoch)))
    jd_tt = _ut1_to_ephemeris_tt(jd_ut, reader)
    jd_tdb = tt_to_tdb(jd_tt)
    c_km_day = _C_KM_S * 86400.0

    # Share the kernel vectors, clock inputs and EOP data. ERFA independently
    # supplies the station state, apparent direction and equator/equinox.
    tt_part = jd_tt - erfa.DJ00
    gast = erfa.gst06a(erfa.DJ00, jd_ut - erfa.DJ00, erfa.DJ00, tt_part)
    rotation = erfa.pnm06a(erfa.DJ00, tt_part)
    xp, yp = np.asarray(PolarMotionRegistry.polar_motion_at(jd_ut)) * erfa.DAS2R
    station = erfa.pvtob(math.radians(longitude), math.radians(latitude), height_m, xp, yp, 0.0, gast)
    emb_p, emb_v = map(np.asarray, reader.position_and_velocity_tdb(0, 3, jd_tdb))
    earth_p, earth_v = map(np.asarray, reader.position_and_velocity_tdb(3, 399, jd_tdb))
    observer = emb_p + earth_p + rotation.T @ station["p"] / 1000.0
    velocity = (emb_v + earth_v + rotation.T @ station["v"] * 86.4) / c_km_day

    def ray(delay):
        epoch_tdb = jd_tdb - delay
        return (
            np.asarray(reader.position_tdb(0, 10, epoch_tdb))
            + np.asarray(reader.position_tdb(10, body_id, epoch_tdb))
            - observer
        )

    # Bracket and bisect the one-way light cone independently of Moira's iteration.
    low, high = 0.0, 2.0 * np.linalg.norm(ray(0.0)) / c_km_day
    for _ in range(56):
        mid = (low + high) / 2.0
        if np.linalg.norm(ray(mid)) > mid * c_km_day:
            low = mid
        else:
            high = mid
    astrometric = ray((low + high) / 2.0)
    distance = np.linalg.norm(astrometric)
    sun_to_observer = observer - np.asarray(reader.position_tdb(0, 10, jd_tdb))
    sun_to_comet = astrometric + sun_to_observer
    sun_distance = np.linalg.norm(sun_to_observer)
    natural = erfa.ld(
        1.0, astrometric / distance, sun_to_comet / np.linalg.norm(sun_to_comet),
        sun_to_observer / sun_distance, sun_distance / (erfa.DAU / 1000.0), 1e-8,
    )
    # Use a large solar distance in ERFA ab to isolate the same Lorentz boost.
    proper = erfa.ab(natural / np.linalg.norm(natural), velocity, 1e12, math.sqrt(1 - velocity @ velocity))
    expected = rotation @ proper

    sky = planets.sky_position_at(
        name, jd_ut, latitude, longitude, height_m, reader=reader, refraction=False,
    )
    actual = erfa.s2c(math.radians(sky.right_ascension), math.radians(sky.declination))
    separation_arcsec = float(erfa.sepp(actual, expected)) / erfa.DAS2R

    assert separation_arcsec < 2e-5, f"{name} separation {separation_arcsec:.8g} arcsec"
    assert sky.distance == pytest.approx(distance, abs=5e-6, rel=0)
