"""Barycentre refit for binary-star component positions.

Akeson et al. (2021) fitted the alpha Centauri barycentre position and proper
motion to the absolute Hipparcos and ALMA positions of A and B.  Their
published ephemeris (Table 12) is reproduced to 0.3 mas by moving the
barycentre at constant rates in right ascension and declination, a path that
departs from straight-line motion in space by about 0.1 mas/yr^2 at this
declination; the published proper motion carries that departure.

This module repeats the fit with Moira's stage-1 model (straight-line space
motion plus the orbital offset), holding the published orbit, parallax,
radial velocity and mass fraction fixed and fitting only the barycentre
position and proper motion at J2019.5.  The catalog values in
``moira.multiple_stars`` are the result; the test re-derives them.
"""

from __future__ import annotations

import datetime as _dt
import json
import math
from dataclasses import replace
from pathlib import Path

from moira import stars
from moira.multiple_stars import MultipleStarSystem, SystemBarycentre, _julian_epoch_jd
from moira.planets import _earth_barycentric_state

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = REPOSITORY_ROOT / "tests" / "fixtures" / "binary_star_orbit_references_2026_10_29.json"

PARSEC_KM = 206264.806247096355 * 149597870.7
# TT - UTC in 2018-2019 (TAI - UTC = 37 s since 2017 January 1).
TT_MINUS_UTC_2018_2019_S = 69.184
# Akeson et al. 2021 Section 3: systematic uncertainty assigned to each
# absolute ALMA position, larger for the lower-resolution October 2018 run.
ALMA_SIGMA_MAS = 3.0
ALMA_SIGMA_OCT_2018_MAS = 6.0
HIPPARCOS_EPOCH_JD = _julian_epoch_jd(1991.25)


def load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _utc_jd(date: str, time: str) -> float:
    moment = _dt.datetime.strptime(f"{date} {time}", "%d-%b-%Y %H:%M:%S.%f")
    epoch = _dt.datetime(2000, 1, 1, 12)
    return 2451545.0 + (moment - epoch).total_seconds() / 86400.0


def tangent_offset_mas(ra0: float, dec0: float, ra1: float, dec1: float) -> tuple[float, float]:
    """Gnomonic offset (east, north) of (ra1, dec1) from (ra0, dec0), in mas."""
    ra0, dec0, ra1, dec1 = map(math.radians, (ra0, dec0, ra1, dec1))
    cos_c = math.sin(dec0) * math.sin(dec1) + math.cos(dec0) * math.cos(dec1) * math.cos(ra1 - ra0)
    x = math.cos(dec1) * math.sin(ra1 - ra0) / cos_c
    y = (math.cos(dec0) * math.sin(dec1) - math.sin(dec0) * math.cos(dec1) * math.cos(ra1 - ra0)) / cos_c
    return math.degrees(x) * 3.6e6, math.degrees(y) * 3.6e6


def _ra_dec(vector) -> tuple[float, float]:
    norm = math.sqrt(sum(c * c for c in vector))
    return math.degrees(math.atan2(vector[1], vector[0])) % 360.0, math.degrees(math.asin(vector[2] / norm))


def measurements(fixture: dict) -> list[dict]:
    """The absolute positions of alpha Cen A and B used by the fit."""
    rows = []
    for row in fixture["akeson2021_alma_absolute"]["rows"]:
        jd_tt = _utc_jd(row["date"], row["start_time_ut"]) + TT_MINUS_UTC_2018_2019_S / 86400.0
        sigma = ALMA_SIGMA_OCT_2018_MAS if row["date"] == "14-Oct-2018" else ALMA_SIGMA_MAS
        rows.append({"label": row["star"], "jd_tt": jd_tt, "geocentric": True,
                     "ra_deg": row["ra_deg"], "dec_deg": row["dec_deg"],
                     "sigma_east_mas": sigma, "sigma_north_mas": sigma, "source": "ALMA " + row["date"]})
    for key, label in (("alpha_cen_a", "A"), ("alpha_cen_b", "B")):
        row = fixture["hipparcos_2007"][key]
        rows.append({"label": label, "jd_tt": HIPPARCOS_EPOCH_JD, "geocentric": False,
                     "ra_deg": row["ra_deg"], "dec_deg": row["dec_deg"],
                     "sigma_east_mas": row["sigma_ra_cosdec_mas"], "sigma_north_mas": row["sigma_dec_mas"],
                     "source": "Hipparcos 2007"})
    return rows


def residuals_mas(system: MultipleStarSystem, rows: list[dict], reader) -> list[tuple[float, float]]:
    """Model minus measurement, (east, north) in mas, for each row."""
    out = []
    for row in rows:
        unit, distance_pc = stars._binary_component_state(system, row["label"], row["jd_tt"])
        if row["geocentric"]:
            earth, _ = _earth_barycentric_state(row["jd_tt"], reader)
            vector = [u * distance_pc * PARSEC_KM - e for u, e in zip(unit, earth)]
        else:
            vector = list(unit)
        ra, dec = _ra_dec(vector)
        out.append(tangent_offset_mas(row["ra_deg"], row["dec_deg"], ra, dec))
    return out


def refit_barycentre(system: MultipleStarSystem, rows: list[dict], reader, iterations: int = 4) -> SystemBarycentre:
    """Weighted least-squares fit of the barycentre position and proper motion.

    Parameters: right ascension and declination at the barycentre epoch (in
    mas on the sky) and the two proper-motion components.  Everything else in
    ``system`` is held fixed.
    """
    bary = system.barycentre
    weights = []
    for row in rows:
        weights += [1.0 / row["sigma_east_mas"], 1.0 / row["sigma_north_mas"]]

    def vector(b: SystemBarycentre) -> list[float]:
        flat = []
        for east, north in residuals_mas(replace(system, barycentre=b), rows, reader):
            flat += [east, north]
        return [w * r for w, r in zip(weights, flat)]

    def shifted(b: SystemBarycentre, p: list[float]) -> SystemBarycentre:
        cos_dec = math.cos(math.radians(b.dec_deg))
        return replace(
            b,
            ra_deg=b.ra_deg + p[0] / 3.6e6 / cos_dec,
            dec_deg=b.dec_deg + p[1] / 3.6e6,
            pmra_mas_yr=b.pmra_mas_yr + p[2],
            pmdec_mas_yr=b.pmdec_mas_yr + p[3],
        )

    for _ in range(iterations):
        r0 = vector(bary)
        columns = []
        for k in range(4):
            step = [0.0] * 4
            step[k] = 1.0
            r1 = vector(shifted(bary, step))
            columns.append([a - b for a, b in zip(r1, r0)])
        # Normal equations J^T J p = -J^T r for the four parameters.
        normal = [[sum(ci * cj for ci, cj in zip(columns[i], columns[j])) for j in range(4)] for i in range(4)]
        rhs = [-sum(ci * r for ci, r in zip(columns[i], r0)) for i in range(4)]
        bary = shifted(bary, _solve(normal, rhs))
    return bary


def _solve(matrix: list[list[float]], rhs: list[float]) -> list[float]:
    n = len(rhs)
    a = [row[:] + [rhs[i]] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(a[r][col]))
        a[col], a[pivot] = a[pivot], a[col]
        for r in range(n):
            if r != col:
                factor = a[r][col] / a[col][col]
                a[r] = [x - factor * y for x, y in zip(a[r], a[col])]
    return [a[i][n] / a[i][i] for i in range(n)]
