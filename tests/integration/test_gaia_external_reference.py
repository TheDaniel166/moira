from __future__ import annotations

import math

import pytest

erfa = pytest.importorskip("erfa")

import moira.gaia as gaia
from moira.coordinates import equatorial_to_ecliptic


_ARCSEC_TO_RAD = math.pi / 648000.0


def _record(
    ra: float,
    dec: float,
    pmra: float,
    pmdec: float,
    parallax: float,
    rv: float,
    gmag: float = 5.0,
    bp_rp: float = math.nan,
    teff: float = math.nan,
) -> tuple[float, ...]:
    return (ra, dec, pmra, pmdec, parallax, 0.1, rv, gmag, bp_rp, teff)


def _pm_to_erfa(ra_deg: float, dec_deg: float, pmra_masyr: float, pmdec_masyr: float) -> tuple[float, float]:
    dec_r = math.radians(dec_deg)
    cos_dec = max(abs(math.cos(dec_r)), 1e-16)
    pmr = pmra_masyr * 1e-3 * _ARCSEC_TO_RAD / cos_dec
    pmd = pmdec_masyr * 1e-3 * _ARCSEC_TO_RAD
    return pmr, pmd


def _oracle_propagated_ra_dec(
    rec: tuple[float, ...],
    jd_tt: float,
    *,
    true_position: bool,
) -> tuple[float, float]:
    ra = float(rec[gaia._F_RA])
    dec = float(rec[gaia._F_DEC])
    pmra = float(rec[gaia._F_PMRA])
    pmdec = float(rec[gaia._F_PMDEC])
    plx = float(rec[gaia._F_PLX])
    rv = float(rec[gaia._F_RV])

    effective_jd = jd_tt
    if not true_position and plx > 0.0:
        effective_jd -= (plx * 3.26156 / 1000.0) * 365.25

    pmr, pmd = _pm_to_erfa(ra, dec, pmra, pmdec)
    ra2, dec2, *_ = erfa.pmsafe(
        math.radians(ra),
        math.radians(dec),
        pmr,
        pmd,
        plx * 1e-3,
        0.0 if math.isnan(rv) else rv,
        gaia._J2016,
        0.0,
        effective_jd,
        0.0,
    )
    return math.degrees(ra2) % 360.0, math.degrees(dec2)


def _exact_annual_parallax(
    lon_deg: float,
    lat_deg: float,
    parallax_mas: float,
    sun_longitude_deg: float,
) -> tuple[float, float]:
    if parallax_mas <= 0.0:
        return lon_deg, lat_deg

    dist_au = 1.0e3 / parallax_mas * (1.0 / 4.84813681e-6)
    lon_r = math.radians(lon_deg)
    lat_r = math.radians(lat_deg)
    sun_r = math.radians(sun_longitude_deg)

    sx = dist_au * math.cos(lat_r) * math.cos(lon_r)
    sy = dist_au * math.cos(lat_r) * math.sin(lon_r)
    sz = dist_au * math.sin(lat_r)

    ex = math.cos(sun_r)
    ey = math.sin(sun_r)
    ez = 0.0

    x = sx - ex
    y = sy - ey
    z = sz - ez
    lon = math.degrees(math.atan2(y, x)) % 360.0
    lat = math.degrees(math.atan2(z, math.hypot(x, y)))
    return lon, lat


def _exact_topocentric_ra_dec(
    ra_deg: float,
    dec_deg: float,
    parallax_mas: float,
    observer_lat: float,
    observer_elev_m: float,
    lst_deg: float,
) -> tuple[float, float]:
    if parallax_mas <= 0.0:
        return ra_deg, dec_deg

    f = 1.0 / 298.257223563
    a_km = 6378.137
    h_km = observer_elev_m / 1000.0
    lat_r = math.radians(observer_lat)

    c = 1.0 / math.sqrt(math.cos(lat_r) ** 2 + (1.0 - f) ** 2 * math.sin(lat_r) ** 2)
    s = (1.0 - f) ** 2 * c

    rho_cos = (a_km * c + h_km) * math.cos(lat_r) / gaia._AU_TO_KM
    rho_sin = (a_km * s + h_km) * math.sin(lat_r) / gaia._AU_TO_KM

    lst_r = math.radians(lst_deg)
    ox = rho_cos * math.cos(lst_r)
    oy = rho_cos * math.sin(lst_r)
    oz = rho_sin

    dist_au = 1.0e3 / parallax_mas * (1.0 / 4.84813681e-6)
    ra_r = math.radians(ra_deg)
    dec_r = math.radians(dec_deg)
    sx = dist_au * math.cos(dec_r) * math.cos(ra_r)
    sy = dist_au * math.cos(dec_r) * math.sin(ra_r)
    sz = dist_au * math.sin(dec_r)

    x = sx - ox
    y = sy - oy
    z = sz - oz
    ra = math.degrees(math.atan2(y, x)) % 360.0
    dec = math.degrees(math.atan2(z, math.hypot(x, y)))
    return ra, dec


def _oracle_record_position(
    rec: tuple[float, ...],
    jd_tt: float,
    *,
    observer_lat: float | None = None,
    observer_lon: float | None = None,
    observer_elev_m: float = 0.0,
    lst_deg: float | None = None,
    true_position: bool = False,
    dpsi_deg: float = 0.0,
    obl_mean: float = 23.43927944,
    prec_deg: float = 0.0,
    sun_longitude: float = 0.0,
) -> tuple[float, float]:
    ra, dec = _oracle_propagated_ra_dec(rec, jd_tt, true_position=true_position)
    plx = float(rec[gaia._F_PLX])

    if observer_lat is not None and observer_lon is not None and lst_deg is not None:
        ra, dec = _exact_topocentric_ra_dec(
            ra,
            dec,
            plx,
            observer_lat,
            observer_elev_m,
            lst_deg,
        )

    lon, lat = equatorial_to_ecliptic(ra, dec, obl_mean)
    lon = (lon + prec_deg + dpsi_deg) % 360.0
    lon, lat = _exact_annual_parallax(lon, lat, plx, sun_longitude)
    return lon, lat


@pytest.mark.parametrize(
    ("rec", "jd_tt"),
    [
        (_record(100.0, 20.0, 500.0, -300.0, 100.0, 20.0), 2460400.0),
        (_record(219.9, -60.8, -3775.0, 770.0, 747.0, -22.0), 2463000.0),
        (_record(10.0, 45.0, 0.0, 0.0, 0.0, math.nan), 2451545.0),
    ],
)
@pytest.mark.parametrize("true_position", [False, True])
def test_apply_proper_motion_gaia_matches_erfa_pmsafe(
    rec: tuple[float, ...],
    jd_tt: float,
    true_position: bool,
) -> None:
    dt_yr = (jd_tt - gaia._J2016) / 365.25
    lt_yr = (float(rec[gaia._F_PLX]) * 3.26156 / 1000.0) if (not true_position and float(rec[gaia._F_PLX]) > 0.0) else 0.0
    actual_ra, actual_dec = gaia._apply_proper_motion_gaia(
        float(rec[gaia._F_RA]),
        float(rec[gaia._F_DEC]),
        float(rec[gaia._F_PMRA]),
        float(rec[gaia._F_PMDEC]),
        float(rec[gaia._F_RV]),
        float(rec[gaia._F_PLX]),
        dt_yr - lt_yr,
    )
    expected_ra, expected_dec = _oracle_propagated_ra_dec(rec, jd_tt, true_position=true_position)

    ra_diff_arcsec = ((actual_ra - expected_ra + 180.0) % 360.0 - 180.0) * 3600.0
    dec_diff_arcsec = (actual_dec - expected_dec) * 3600.0
    assert abs(ra_diff_arcsec) < 0.02
    assert abs(dec_diff_arcsec) < 0.02


@pytest.mark.parametrize(
    ("lon", "lat", "parallax_mas", "sun_lon"),
    [
        (100.0, 10.0, 100.0, 45.0),
        (250.0, -30.0, 750.0, 300.0),
        (5.0, 70.0, 500.0, 120.0),
        (150.0, -5.0, 0.0, 220.0),
    ],
)
def test_annual_parallax_matches_exact_vector_geometry(
    lon: float,
    lat: float,
    parallax_mas: float,
    sun_lon: float,
) -> None:
    actual = gaia._annual_parallax(lon, lat, parallax_mas, sun_lon)
    expected = _exact_annual_parallax(lon, lat, parallax_mas, sun_lon)

    lon_diff_arcsec = ((actual[0] - expected[0] + 180.0) % 360.0 - 180.0) * 3600.0
    lat_diff_arcsec = (actual[1] - expected[1]) * 3600.0
    assert abs(lon_diff_arcsec) < 0.05
    assert abs(lat_diff_arcsec) < 0.05


@pytest.mark.parametrize(
    ("ra", "dec", "parallax_mas", "observer_lat", "observer_lon", "observer_elev_m", "lst_deg"),
    [
        (100.0, 20.0, 100.0, 40.0, -74.0, 20.0, 150.0),
        (10.0, -30.0, 750.0, -33.0, 151.0, 50.0, 220.0),
        (250.0, 60.0, 500.0, 52.0, 0.0, 100.0, 30.0),
        (90.0, 0.0, 0.0, 52.0, 0.0, 100.0, 30.0),
    ],
)
def test_topocentric_stellar_parallax_matches_exact_vector_geometry(
    ra: float,
    dec: float,
    parallax_mas: float,
    observer_lat: float,
    observer_lon: float,
    observer_elev_m: float,
    lst_deg: float,
) -> None:
    delta_ra, delta_dec = gaia._topocentric_stellar_parallax(
        ra,
        dec,
        parallax_mas,
        observer_lat,
        observer_lon,
        observer_elev_m,
        lst_deg,
    )
    actual = ((ra + delta_ra) % 360.0, dec + delta_dec)
    expected = _exact_topocentric_ra_dec(
        ra,
        dec,
        parallax_mas,
        observer_lat,
        observer_elev_m,
        lst_deg,
    )
    ra_diff_arcsec = ((actual[0] - expected[0] + 180.0) % 360.0 - 180.0) * 3600.0
    dec_diff_arcsec = (actual[1] - expected[1]) * 3600.0
    assert abs(ra_diff_arcsec) < 1e-6
    assert abs(dec_diff_arcsec) < 1e-6


@pytest.mark.parametrize(
    ("rec", "jd_tt", "observer_lat", "observer_lon", "observer_elev_m", "lst_deg", "true_position"),
    [
        (_record(100.0, 20.0, 500.0, -300.0, 100.0, 20.0, bp_rp=1.1, teff=5800.0), 2460400.0, None, None, 0.0, None, False),
        (_record(219.9, -60.8, -3775.0, 770.0, 747.0, -22.0, bp_rp=1.8, teff=3200.0), 2463000.0, -33.0, 151.0, 50.0, 220.0, True),
        (_record(10.0, 45.0, 0.0, 0.0, 0.0, math.nan, bp_rp=0.8, teff=7000.0), 2451545.0, 52.0, 0.0, 100.0, 30.0, True),
    ],
)
def test_record_to_position_matches_external_oracle_for_gaia_specific_stack(
    rec: tuple[float, ...],
    jd_tt: float,
    observer_lat: float | None,
    observer_lon: float | None,
    observer_elev_m: float,
    lst_deg: float | None,
    true_position: bool,
) -> None:
    dpsi_deg = 0.2
    obl_mean = 23.4
    prec_deg = 0.5
    sun_longitude = 123.0

    pos = gaia._record_to_position(
        7,
        rec,
        jd_tt,
        observer_lat=observer_lat,
        observer_lon=observer_lon,
        observer_elev_m=observer_elev_m,
        lst_deg=lst_deg,
        true_position=true_position,
        _dpsi=dpsi_deg,
        _obl_mean=obl_mean,
        _prec=prec_deg,
        _sun_lon=sun_longitude,
    )
    expected_lon, expected_lat = _oracle_record_position(
        rec,
        jd_tt,
        observer_lat=observer_lat,
        observer_lon=observer_lon,
        observer_elev_m=observer_elev_m,
        lst_deg=lst_deg,
        true_position=true_position,
        dpsi_deg=dpsi_deg,
        obl_mean=obl_mean,
        prec_deg=prec_deg,
        sun_longitude=sun_longitude,
    )

    lon_diff_arcsec = ((pos.longitude - expected_lon + 180.0) % 360.0 - 180.0) * 3600.0
    lat_diff_arcsec = (pos.latitude - expected_lat) * 3600.0
    assert abs(lon_diff_arcsec) < 3.0
    assert abs(lat_diff_arcsec) < 1.0
