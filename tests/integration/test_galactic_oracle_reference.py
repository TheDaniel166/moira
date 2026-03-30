from __future__ import annotations

import math

import pytest

from moira.galactic import (
    ecliptic_to_galactic,
    equatorial_to_galactic,
    galactic_to_ecliptic,
    galactic_to_equatorial,
)

astropy = pytest.importorskip("astropy")
erfa = pytest.importorskip("erfa")

from astropy import units as u
from astropy.coordinates import Galactic, ICRS, SkyCoord

PASS_THRESHOLD_ARCSEC = 0.1
ICRS_CASES = [
    ("galactic_center", 266.405100, -28.936175),
    ("north_galactic_pole", 192.859508, 27.128336),
    ("generic_northern", 120.0, 45.0),
    ("vernal_origin", 0.0, 0.0),
    ("southern_polar", 359.999, -89.5),
]
GALACTIC_CASES = [
    ("center", 0.0, 0.0),
    ("quadrant_i", 90.0, 45.0),
    ("anticenter", 180.0, 0.0),
    ("near_ngp", 107.22929029933128, 89.99989428365237),
]
EPOCH_CASES = [
    ("-500 (500 BCE)", 1903682.5),
    ("-200 (200 BCE)", 1794303.5),
    ("J0000 (1 CE)", 1721045.5),
    ("J1000.0", 2086308.0),
    ("J1500.0", 2268923.5),
    ("J1800.0", 2378496.5),
    ("J1900.0", 2415020.5),
    ("J2000.0", 2451545.0),
    ("J2010.0", 2455196.5),
    ("J2024.0", 2460310.5),
    ("2026-03-20 TT", 2461497.5),
    ("J2050.0", 2469807.5),
    ("J2100.0", 2488069.5),
]
ECLIPTIC_CASES = [
    ("zero_point", 0.0, 0.0),
    ("generic", 120.0, 5.0),
    ("galactic_region", 265.0, 1.5),
    ("wraparound", 359.9, -1.2),
    ("southern_mid", 210.0, -35.0),
    ("northern_high", 45.0, 66.0),
]


def _split(jd: float) -> tuple[float, float]:
    return float(int(jd)), float(jd - int(jd))


def _true_obliquity_erfa(jd_tt: float) -> float:
    d1, d2 = _split(jd_tt)
    _dpsi, deps = erfa.nut06a(d1, d2)
    return math.degrees(erfa.obl06(d1, d2) + deps)


def _ecliptic_to_true_equatorial(lon_deg: float, lat_deg: float, obliquity_deg: float) -> tuple[float, float]:
    lon_r = math.radians(lon_deg)
    lat_r = math.radians(lat_deg)
    eps_r = math.radians(obliquity_deg)

    x_ecl = math.cos(lat_r) * math.cos(lon_r)
    y_ecl = math.cos(lat_r) * math.sin(lon_r)
    z_ecl = math.sin(lat_r)

    x_eq = x_ecl
    y_eq = y_ecl * math.cos(eps_r) - z_ecl * math.sin(eps_r)
    z_eq = y_ecl * math.sin(eps_r) + z_ecl * math.cos(eps_r)

    ra_deg = math.degrees(math.atan2(y_eq, x_eq)) % 360.0
    dec_deg = math.degrees(math.asin(max(-1.0, min(1.0, z_eq))))
    return ra_deg, dec_deg


def _true_equatorial_to_ecliptic(ra_deg: float, dec_deg: float, obliquity_deg: float) -> tuple[float, float]:
    ra_r = math.radians(ra_deg)
    dec_r = math.radians(dec_deg)
    eps_r = math.radians(obliquity_deg)

    x_eq = math.cos(dec_r) * math.cos(ra_r)
    y_eq = math.cos(dec_r) * math.sin(ra_r)
    z_eq = math.sin(dec_r)

    x_ecl = x_eq
    y_ecl = y_eq * math.cos(eps_r) + z_eq * math.sin(eps_r)
    z_ecl = -y_eq * math.sin(eps_r) + z_eq * math.cos(eps_r)

    lon_deg = math.degrees(math.atan2(y_ecl, x_ecl)) % 360.0
    lat_deg = math.degrees(math.asin(max(-1.0, min(1.0, z_ecl))))
    return lon_deg, lat_deg


def _galactic_sep_arcsec(l1_deg: float, b1_deg: float, l2_deg: float, b2_deg: float) -> float:
    left = SkyCoord(l=l1_deg * u.deg, b=b1_deg * u.deg, frame=Galactic())
    right = SkyCoord(l=l2_deg * u.deg, b=b2_deg * u.deg, frame=Galactic())
    return left.separation(right).arcsecond


def _ecliptic_sep_arcsec(lon1_deg: float, lat1_deg: float, lon2_deg: float, lat2_deg: float) -> float:
    lon1_r = math.radians(lon1_deg)
    lat1_r = math.radians(lat1_deg)
    lon2_r = math.radians(lon2_deg)
    lat2_r = math.radians(lat2_deg)
    cos_sep = (
        math.sin(lat1_r) * math.sin(lat2_r)
        + math.cos(lat1_r) * math.cos(lat2_r) * math.cos(lon1_r - lon2_r)
    )
    return math.degrees(math.acos(max(-1.0, min(1.0, cos_sep)))) * 3600.0


@pytest.mark.integration
@pytest.mark.parametrize(("case_id", "ra_deg", "dec_deg"), ICRS_CASES, ids=[case_id for case_id, _, _ in ICRS_CASES])
def test_equatorial_to_galactic_matches_astropy_oracle(case_id: str, ra_deg: float, dec_deg: float) -> None:
    oracle = SkyCoord(ra=ra_deg * u.deg, dec=dec_deg * u.deg, frame=ICRS()).transform_to(Galactic())
    moira_l, moira_b = equatorial_to_galactic(ra_deg, dec_deg)
    error_arcsec = _galactic_sep_arcsec(moira_l, moira_b, oracle.l.deg, oracle.b.deg)
    assert error_arcsec < PASS_THRESHOLD_ARCSEC, f"{case_id}: {error_arcsec:.6f}\""


@pytest.mark.integration
@pytest.mark.parametrize(("case_id", "l_deg", "b_deg"), GALACTIC_CASES, ids=[case_id for case_id, _, _ in GALACTIC_CASES])
def test_galactic_to_equatorial_matches_astropy_oracle(case_id: str, l_deg: float, b_deg: float) -> None:
    oracle = SkyCoord(l=l_deg * u.deg, b=b_deg * u.deg, frame=Galactic()).transform_to(ICRS())
    moira_ra, moira_dec = galactic_to_equatorial(l_deg, b_deg)
    moira_icrs = SkyCoord(ra=moira_ra * u.deg, dec=moira_dec * u.deg, frame=ICRS())
    error_arcsec = moira_icrs.separation(oracle).arcsecond
    assert error_arcsec < PASS_THRESHOLD_ARCSEC, f"{case_id}: {error_arcsec:.6f}\""


@pytest.mark.integration
@pytest.mark.parametrize(("epoch_id", "jd_tt"), EPOCH_CASES, ids=[epoch_id for epoch_id, _ in EPOCH_CASES])
@pytest.mark.parametrize(("case_id", "lon_deg", "lat_deg"), ECLIPTIC_CASES, ids=[case_id for case_id, _, _ in ECLIPTIC_CASES])
def test_ecliptic_to_galactic_matches_erfa_astropy_oracle(
    epoch_id: str,
    jd_tt: float,
    case_id: str,
    lon_deg: float,
    lat_deg: float,
) -> None:
    obliquity_deg = _true_obliquity_erfa(jd_tt)
    true_ra_deg, true_dec_deg = _ecliptic_to_true_equatorial(lon_deg, lat_deg, obliquity_deg)
    pnm = erfa.pnm06a(*_split(jd_tt))
    icrs_vector = erfa.trxp(pnm, erfa.s2c(math.radians(true_ra_deg), math.radians(true_dec_deg)))
    icrs_ra_rad, icrs_dec_rad = erfa.c2s(icrs_vector)
    oracle = SkyCoord(ra=icrs_ra_rad * u.rad, dec=icrs_dec_rad * u.rad, frame=ICRS()).transform_to(Galactic())

    moira_l_deg, moira_b_deg = ecliptic_to_galactic(lon_deg, lat_deg, obliquity_deg, jd_tt)
    error_arcsec = _galactic_sep_arcsec(moira_l_deg, moira_b_deg, oracle.l.deg, oracle.b.deg)
    assert error_arcsec < PASS_THRESHOLD_ARCSEC, f"{epoch_id} {case_id}: {error_arcsec:.6f}\""


@pytest.mark.integration
@pytest.mark.parametrize(("epoch_id", "jd_tt"), EPOCH_CASES, ids=[epoch_id for epoch_id, _ in EPOCH_CASES])
@pytest.mark.parametrize(("case_id", "l_deg", "b_deg"), GALACTIC_CASES, ids=[case_id for case_id, _, _ in GALACTIC_CASES])
def test_galactic_to_ecliptic_matches_erfa_astropy_oracle(
    epoch_id: str,
    jd_tt: float,
    case_id: str,
    l_deg: float,
    b_deg: float,
) -> None:
    obliquity_deg = _true_obliquity_erfa(jd_tt)
    pnm = erfa.pnm06a(*_split(jd_tt))
    oracle_icrs = SkyCoord(l=l_deg * u.deg, b=b_deg * u.deg, frame=Galactic()).transform_to(ICRS())
    true_vector = erfa.rxp(pnm, erfa.s2c(oracle_icrs.ra.radian, oracle_icrs.dec.radian))
    true_ra_rad, true_dec_rad = erfa.c2s(true_vector)
    oracle_lon_deg, oracle_lat_deg = _true_equatorial_to_ecliptic(
        math.degrees(true_ra_rad) % 360.0,
        math.degrees(true_dec_rad),
        obliquity_deg,
    )

    moira_lon_deg, moira_lat_deg = galactic_to_ecliptic(l_deg, b_deg, obliquity_deg, jd_tt)
    error_arcsec = _ecliptic_sep_arcsec(moira_lon_deg, moira_lat_deg, oracle_lon_deg, oracle_lat_deg)
    assert error_arcsec < PASS_THRESHOLD_ARCSEC, f"{epoch_id} {case_id}: {error_arcsec:.6f}\""
