from __future__ import annotations

import csv
import math
import warnings
from pathlib import Path
from types import SimpleNamespace

import pytest

import moira.stars as stars
from moira._stellar_space_motion import astrometric_direction
from moira.coordinates import icrf_to_true_ecliptic
from moira.stars import star_at


erfa = pytest.importorskip("erfa")

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "moira" / "data" / "star_registry.csv"
J2000 = 2451545.0
ERFA_ANCHOR_THRESHOLD_DEG = 4e-4
ERFA_CATALOG_PASS_THRESHOLD_DEG = 0.01
ANCHOR_CASES = [
    ("Sirius", J2000 - 36525.0 * 10),
    ("Sirius", J2000 - 36525.0 * 5),
    ("Sirius", J2000 - 36525.0),
    ("Sirius", J2000),
    ("Sirius", J2000 + 36525.0),
    ("Sirius", J2000 + 36525.0 * 5),
    ("Sirius", J2000 + 36525.0 * 10),
    ("Algol", J2000 - 36525.0 * 10),
    ("Algol", J2000 - 36525.0 * 5),
    ("Algol", J2000 - 36525.0),
    ("Algol", J2000),
    ("Algol", J2000 + 36525.0),
    ("Algol", J2000 + 36525.0 * 5),
    ("Algol", J2000 + 36525.0 * 10),
    ("Spica", J2000 - 36525.0 * 10),
    ("Spica", J2000 - 36525.0 * 5),
    ("Spica", J2000 - 36525.0),
    ("Spica", J2000),
    ("Spica", J2000 + 36525.0),
    ("Spica", J2000 + 36525.0 * 5),
    ("Spica", J2000 + 36525.0 * 10),
    ("Aldebaran", J2000 - 36525.0 * 10),
    ("Aldebaran", J2000 - 36525.0 * 5),
    ("Aldebaran", J2000 - 36525.0),
    ("Aldebaran", J2000),
    ("Aldebaran", J2000 + 36525.0),
    ("Aldebaran", J2000 + 36525.0 * 5),
    ("Aldebaran", J2000 + 36525.0 * 10),
]


def _moira_position(name: str, jd_tt: float) -> SimpleNamespace:
    """Moira's position for the registry row that ERFA propagates here.

    ``star_at`` places a binary component (Sirius, alpha Centauri A and B) on
    its orbit about the system barycentre; ERFA ``pmsafe`` moves the catalog
    row in a straight line.  For those rows the comparison therefore uses
    Moira's straight-line stage-1 path; the orbit model is validated in
    test_stars_binary_orbits.py.
    """
    if name not in stars._binary_components():
        return star_at(name, jd_tt)
    record = {r.name: r for r in stars._load_registry_records()}[name]
    direction, _ = astrometric_direction(
        record.ra_deg, record.dec_deg, record.pmra_mas_yr, record.pmdec_mas_yr,
        record.parallax_mas, record.radial_velocity_km_s, record.ref_epoch_jd, jd_tt,
    )
    lon, lat, _ = icrf_to_true_ecliptic(jd_tt, direction)
    return SimpleNamespace(longitude=lon, latitude=lat)


def _split_jd(jd: float) -> tuple[float, float]:
    return float(int(jd)), float(jd - int(jd))


def _angular_diff(a_deg: float, b_deg: float) -> float:
    diff = abs(a_deg - b_deg) % 360.0
    return diff if diff <= 180.0 else 360.0 - diff


def _rot_x_passive(vec: tuple[float, float, float], angle_rad: float) -> tuple[float, float, float]:
    x, y, z = vec
    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    return (x, y * c + z * s, -y * s + z * c)


def _registry_rows() -> list[dict[str, str]]:
    with REGISTRY_PATH.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _registry_by_name() -> dict[str, dict[str, str]]:
    return {row["name"].strip(): row for row in _registry_rows() if row["name"].strip()}


def _erfa_fixed_star_position(row: dict[str, str], jd_tt: float) -> tuple[float, float]:
    ra_deg = float(row["ra_deg"])
    dec_deg = float(row["dec_deg"])
    pmra_mas_yr = float(row["pmra_mas_yr"])
    pmdec_mas_yr = float(row["pmdec_mas_yr"])
    parallax_mas = float(row["parallax_mas"])
    # The same catalog inputs Moira propagates: radial velocity and epoch.
    radial_velocity_km_s = float(row["radial_velocity_km_s"])
    ref_epoch_jd = float(row["ref_epoch_jd"])

    cos_dec = math.cos(math.radians(dec_deg))
    pmr_deg_per_year = 0.0
    if abs(cos_dec) > 1e-12:
        pmr_deg_per_year = (pmra_mas_yr / 1000.0) / 3600.0 / cos_dec
    pmd_deg_per_year = (pmdec_mas_yr / 1000.0) / 3600.0

    jd1a, jd1b = _split_jd(ref_epoch_jd)
    jd2a, jd2b = _split_jd(jd_tt)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        ra_date, dec_date, _, _, _, _ = erfa.pmsafe(
            math.radians(ra_deg),
            math.radians(dec_deg),
            math.radians(pmr_deg_per_year),
            math.radians(pmd_deg_per_year),
            max(0.0, parallax_mas / 1000.0),
            radial_velocity_km_s,
            jd1a,
            jd1b,
            jd2a,
            jd2b,
        )

    p_icrs = tuple(float(value) for value in erfa.s2c(ra_date, dec_date))
    p_true_equ = tuple(float(value) for value in erfa.rxp(erfa.pnm06a(jd2a, jd2b), p_icrs))
    eps_true = erfa.obl06(jd2a, jd2b) + erfa.nut06a(jd2a, jd2b)[1]
    p_true_ecl = _rot_x_passive(p_true_equ, eps_true)
    lon_rad, lat_rad = erfa.c2s(p_true_ecl)
    return math.degrees(lon_rad) % 360.0, math.degrees(lat_rad)


@pytest.mark.integration
@pytest.mark.parametrize(("name", "jd_tt"), ANCHOR_CASES, ids=[f"{name}@{jd_tt:.1f}" for name, jd_tt in ANCHOR_CASES])
def test_anchor_stars_match_erfa_oracle(name: str, jd_tt: float) -> None:
    row = _registry_by_name()[name]
    erfa_lon, erfa_lat = _erfa_fixed_star_position(row, jd_tt)
    moira = _moira_position(name, jd_tt)

    lon_err = _angular_diff(moira.longitude, erfa_lon)
    lat_err = abs(moira.latitude - erfa_lat)

    assert lon_err <= ERFA_ANCHOR_THRESHOLD_DEG, (
        f"{name} jd_tt={jd_tt:.6f}: longitude delta {lon_err:.9f} deg exceeds "
        f"{ERFA_ANCHOR_THRESHOLD_DEG:.9f} deg"
    )
    assert lat_err <= ERFA_ANCHOR_THRESHOLD_DEG, (
        f"{name} jd_tt={jd_tt:.6f}: latitude delta {lat_err:.9f} deg exceeds "
        f"{ERFA_ANCHOR_THRESHOLD_DEG:.9f} deg"
    )


@pytest.mark.integration
def test_full_catalog_j2000_erfa_sweep_has_no_large_outliers() -> None:
    outliers: list[tuple[str, float, float]] = []

    for name, row in _registry_by_name().items():
        erfa_lon, erfa_lat = _erfa_fixed_star_position(row, J2000)
        moira = _moira_position(name, J2000)
        lon_err = _angular_diff(moira.longitude, erfa_lon)
        lat_err = abs(moira.latitude - erfa_lat)
        if max(lon_err, lat_err) > ERFA_CATALOG_PASS_THRESHOLD_DEG:
            outliers.append((name, lon_err, lat_err))

    assert outliers == []


# Straight-line space motion with the catalog radial velocity omits only the
# second-order Romer (light-time) term that pmsafe includes. Over the whole
# registry it measured at most 0.0048 arcsec at 1800 and 2200 (Barnard's
# Star) on 2026-10-29; the gate leaves room for catalog refreshes.
ERFA_CATALOG_SPACE_MOTION_THRESHOLD_ARCSEC = 0.01


@pytest.mark.integration
@pytest.mark.parametrize("jd_tt", [J2000 - 73050.0, J2000 + 73050.0], ids=["1800", "2200"])
def test_full_catalog_space_motion_with_radial_velocity_matches_erfa(jd_tt: float) -> None:
    outliers: list[tuple[str, float]] = []

    for name, row in _registry_by_name().items():
        erfa_lon, erfa_lat = _erfa_fixed_star_position(row, jd_tt)
        moira = _moira_position(name, jd_tt)
        lon_err = _angular_diff(moira.longitude, erfa_lon) * math.cos(math.radians(erfa_lat))
        lat_err = abs(moira.latitude - erfa_lat)
        error_arcsec = math.hypot(lon_err, lat_err) * 3600.0
        if error_arcsec > ERFA_CATALOG_SPACE_MOTION_THRESHOLD_ARCSEC:
            outliers.append((name, error_arcsec))

    assert outliers == []
