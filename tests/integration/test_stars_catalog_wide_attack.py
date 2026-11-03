"""Catalog-wide fixed-star attack (2026-11-03, after 6.12.0).

The existing apparent-place test checks 12 stars.  This attacks every row of
the sovereign registry (1,809 stars; binary components excluded from the ERFA
comparison because their stage 1 is an orbit, covered by
test_stars_binary_orbits.py).

Evidence classes:
- Authority validation: apparent product against ERFA ``apcg`` + ``atciq`` built
  from Moira's own DE441 Earth state, geocentric ICRS direction, at 1850, 2000
  and 2100 (TT).  Threshold 0.001 arcsec; measured worst 0.00014 arcsec
  (Barnard's Star, the declared second-order light-time term).
- Physical invariants: every product finite with longitude in [0, 360) and
  latitude in [-90, 90] at five epochs from year 0 to year 3000; apparent minus
  astrometric bounded by aberration (20.6 arcsec) + parallax + 2 arcsec of
  deflection.
"""

from __future__ import annotations

import math
import warnings

import pytest

import moira.stars as stars

erfa = pytest.importorskip("erfa")
np = pytest.importorskip("numpy")

pytestmark = [pytest.mark.requires_ephemeris, pytest.mark.integration]

AU_KM = 149597870.7
ERFA_THRESHOLD_ARCSEC = 0.001
ERFA_EPOCHS = [2378496.5, 2451545.0, 2488069.5]
SANITY_EPOCHS = ERFA_EPOCHS + [1721057.5, 2816787.5]


def _angle_arcsec(u, v):
    cr = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    dot = sum(a * b for a, b in zip(u, v))
    return math.degrees(math.atan2(math.sqrt(sum(c * c for c in cr)), dot)) * 3600.0


def _ecliptic_unit(star):
    lon, lat = math.radians(star.longitude), math.radians(star.latitude)
    return (math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat))


def _erfa_apparent_ecliptic(record, jd_tt, reader):
    from moira.constants import Body
    from moira.coordinates import icrf_to_true_ecliptic
    from moira.planets import _earth_barycentric_state, _geocentric

    position, velocity = _earth_barycentric_state(jd_tt, reader)
    sun = _geocentric(Body.SUN, jd_tt, reader)
    earth_pv = np.zeros((), dtype=erfa.dt_pv)
    earth_pv["p"] = np.array(position) / AU_KM
    earth_pv["v"] = np.array(velocity) / AU_KM
    dec = math.radians(record.dec_deg)
    parallax = record.parallax_mas / 1000.0 if record.parallax_mas > 0 else 0.0
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        astrom = erfa.apcg(jd_tt, 0.0, earth_pv, -np.array(sun) / AU_KM)
        ra_i, dec_i = erfa.atciq(
            math.radians(record.ra_deg), dec,
            math.radians(record.pmra_mas_yr / 3.6e6) / math.cos(dec),
            math.radians(record.pmdec_mas_yr / 3.6e6),
            parallax, record.radial_velocity_km_s, astrom,
        )
    icrs = (math.cos(dec_i) * math.cos(ra_i), math.cos(dec_i) * math.sin(ra_i), math.sin(dec_i))
    lon, lat, _ = icrf_to_true_ecliptic(jd_tt, icrs)
    lon_r, lat_r = math.radians(lon), math.radians(lat)
    return (math.cos(lat_r) * math.cos(lon_r), math.cos(lat_r) * math.sin(lon_r), math.sin(lat_r))


def test_every_catalog_star_apparent_matches_erfa(planetary_reader):
    binaries = stars._binary_components()
    worst = []
    for record in stars._load_registry_records():
        if record.name in binaries:
            continue
        for jd in ERFA_EPOCHS:
            ref = _erfa_apparent_ecliptic(record, jd, planetary_reader)
            got = stars.star_at(record.name, jd, product="apparent", reader=planetary_reader)
            worst.append((_angle_arcsec(ref, _ecliptic_unit(got)), record.name, jd))
    worst.sort(reverse=True)
    assert worst[0][0] < ERFA_THRESHOLD_ARCSEC, worst[:5]


def test_every_catalog_star_products_are_finite_and_physically_bounded(planetary_reader):
    problems = []
    for record in stars._load_registry_records():
        for jd in SANITY_EPOCHS:
            astrometric = stars.star_at(record.name, jd, product="astrometric")
            apparent = stars.star_at(record.name, jd, product="apparent", reader=planetary_reader)
            geometric = stars.star_at(record.name, jd, product="geometric")
            for label, star in (("astrometric", astrometric), ("apparent", apparent), ("geometric", geometric)):
                if not (math.isfinite(star.longitude) and math.isfinite(star.latitude)
                        and 0.0 <= star.longitude < 360.0 and -90.0 <= star.latitude <= 90.0):
                    problems.append((record.name, jd, label, star.longitude, star.latitude))
            bound = 20.6 + max(record.parallax_mas, 0.0) / 1000.0 + 2.0
            separation = _angle_arcsec(_ecliptic_unit(astrometric), _ecliptic_unit(apparent))
            if separation > bound:
                problems.append((record.name, jd, "apparent-astrometric", separation, bound))
    assert not problems, problems[:10]
