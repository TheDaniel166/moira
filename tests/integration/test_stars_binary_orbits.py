"""Binary-star component positions (Phase 4 of the fixed-star standard).

Governing record: wiki/02_standards/FIXED_STARS_BACKEND_STANDARD.md, Section 6.
A component of a binary with an admitted orbit is placed at its share of the
relative orbit about the system barycentre, which moves in a straight line in
space.  Evidence, all from tests/fixtures/binary_star_orbit_references_2026_10_29.json:

- relative orbit: the Sixth Orbit Catalog ephemerides (2025-2029), Bond et
  al. 2017 HST measures of Sirius B (17 epochs, 1997-2016), and the Akeson et
  al. 2021 alpha Centauri ephemeris (41 epochs, 2010-2050);
- absolute positions: ALMA (2018-2019) and Hipparcos (1991.25) positions of
  alpha Centauri A and B, through a barycentre refit that the catalog stores
  and this module re-derives;
- barycentre space motion: ERFA ``pmsafe``;
- invariants: offsets balance about the barycentre and stay inside the orbit.

Measured on 2026-10-29 (tolerances below leave room only for rounding of the
published values):
- ORB6: position angle within 0.04 deg, separation within 0.0004 arcsec;
- Bond HST: worst 0.016 arcsec (2006.99), median 0.006 arcsec;
- Akeson relative ephemeris: worst 0.0014 arcsec;
- ALMA: 18 positions, RMS 7.1 mas, worst 14.6 mas; Hipparcos A 1.4 mas,
  Hipparcos B 57 mas (2.7 sigma in right ascension; Hipparcos B is the
  fainter component of a 14-arcsec pair).
"""

from __future__ import annotations

import math
import statistics
from dataclasses import replace

import pytest

import moira.stars as stars
from moira._stellar_space_motion import astrometric_direction
from moira.multiple_stars import (
    _julian_epoch_jd,
    _visual_binary_offset,
    component_offset_arcsec,
    multiple_star,
)
from tests.support import binary_star_barycentre as bsb

erfa = pytest.importorskip("erfa")

FIXTURE = bsb.load_fixture()
SYSTEMS = {"Sirius": multiple_star("Sirius"), "Alpha Centauri": multiple_star("Alpha Centauri")}

ORB6_THETA_TOLERANCE_DEG = 0.06       # published to 0.1 deg
ORB6_RHO_TOLERANCE_ARCSEC = 0.0008    # published to 0.001 arcsec
HST_TOLERANCE_ARCSEC = 0.025          # HST errors 0.003-0.005 arcsec; worst measured 0.016
AKESON_RELATIVE_TOLERANCE_ARCSEC = 0.003  # published to 0.001 arcsec
ALMA_RMS_LIMIT_MAS = 10.0
ALMA_WORST_LIMIT_MAS = 20.0
HIPPARCOS_SIGMA_LIMIT = 3.0
BARYCENTRE_ERFA_TOLERANCE_ARCSEC = 0.01


def _besselian_jd(year: float) -> float:
    return 2415020.31352 + (year - 1900.0) * 365.242198781


def _relative(system, jd: float) -> tuple[float, float]:
    """Offset of B from A (east, north) in arcsec, J2000."""
    return _visual_binary_offset(system.orbits[0], jd)


def _radec_unit(ra_deg: float, dec_deg: float):
    ra, dec = math.radians(ra_deg), math.radians(dec_deg)
    return (math.cos(dec) * math.cos(ra), math.cos(dec) * math.sin(ra), math.sin(dec))


def _position_angle_of_date(system, jd: float) -> tuple[float, float]:
    """Separation and position angle of B from A in the mean equator of date.

    The J2000 offset is laid at the barycentre, both directions are precessed
    with ERFA ``pmat06``, and the angle is measured from the north of date.
    """
    bary = system.barycentre
    a = _radec_unit(bary.ra_deg, bary.dec_deg)
    ra, dec = math.radians(bary.ra_deg), math.radians(bary.dec_deg)
    east = (-math.sin(ra), math.cos(ra), 0.0)
    north = (-math.sin(dec) * math.cos(ra), -math.sin(dec) * math.sin(ra), math.cos(dec))
    x, y = _relative(system, jd)
    arcsec = math.pi / 648000.0
    b = [ai + arcsec * (x * e + y * n) for ai, e, n in zip(a, east, north)]
    matrix = erfa.pmat06(jd, 0.0)
    a_d = matrix @ a
    b_d = matrix @ b
    ra_a, dec_a = erfa.c2s(a_d)
    ra_b, dec_b = erfa.c2s(b_d)
    x_d = math.cos(dec_b) * math.sin(ra_b - ra_a)
    y_d = math.cos(dec_a) * math.sin(dec_b) - math.sin(dec_a) * math.cos(dec_b) * math.cos(ra_b - ra_a)
    rho = math.degrees(erfa.seps(ra_a, dec_a, ra_b, dec_b)) * 3600.0
    return rho, math.degrees(math.atan2(x_d, y_d)) % 360.0


@pytest.mark.integration
@pytest.mark.parametrize("name", ["Sirius", "Alpha Centauri"])
def test_relative_orbit_reproduces_sixth_orbit_catalog_ephemerides(name: str) -> None:
    system = SYSTEMS[name]
    for row in FIXTURE["orb6_ephemerides"][name]["rows"]:
        rho, theta = _position_angle_of_date(system, _julian_epoch_jd(row["year"]))
        d_theta = (theta - row["theta_deg"] + 180.0) % 360.0 - 180.0
        assert abs(d_theta) <= ORB6_THETA_TOLERANCE_DEG, (row, theta)
        assert abs(rho - row["rho_arcsec"]) <= ORB6_RHO_TOLERANCE_ARCSEC, (row, rho)


@pytest.mark.integration
def test_sirius_relative_orbit_reproduces_bond_hst_measurements() -> None:
    system = SYSTEMS["Sirius"]
    misses = []
    for row in FIXTURE["bond2017_hst_relative"]:
        x, y = _relative(system, _besselian_jd(row["besselian_year"]))
        theta = math.radians(row["theta_j2000_deg"])
        dx = x - row["rho_arcsec"] * math.sin(theta)
        dy = y - row["rho_arcsec"] * math.cos(theta)
        misses.append(math.hypot(dx, dy))
    assert len(misses) == 17
    assert max(misses) <= HST_TOLERANCE_ARCSEC, misses
    assert statistics.median(misses) <= 0.01


@pytest.mark.integration
def test_alpha_cen_relative_orbit_reproduces_akeson_ephemeris() -> None:
    system = SYSTEMS["Alpha Centauri"]
    rows = FIXTURE["akeson2021_relative_ephemeris"]["rows"]
    misses = []
    for row in rows:
        x, y = _relative(system, _julian_epoch_jd(row["year"]))
        misses.append(math.hypot(x - row["dra_arcsec"], y - row["ddec_arcsec"]))
    assert len(misses) == 41
    assert max(misses) <= AKESON_RELATIVE_TOLERANCE_ARCSEC, max(misses)


@pytest.mark.integration
@pytest.mark.requires_ephemeris
def test_alpha_cen_barycentre_refit_reproduces_catalog_and_measurements(planetary_reader) -> None:
    system = SYSTEMS["Alpha Centauri"]
    published = FIXTURE["akeson2021_published_barycentre"]
    start = replace(
        system.barycentre,
        ra_deg=published["ra_deg"], dec_deg=published["dec_deg"],
        pmra_mas_yr=published["pmra_mas_yr"], pmdec_mas_yr=published["pmdec_mas_yr"],
    )
    assert system.barycentre.parallax_mas == published["parallax_mas"]
    assert system.barycentre.radial_velocity_km_s == published["radial_velocity_km_s"]
    assert 1.0 - system.barycentre.secondary_mass_fraction == pytest.approx(published["mass_fraction_a"], abs=1e-12)

    rows = bsb.measurements(FIXTURE)
    fitted = bsb.refit_barycentre(replace(system, barycentre=start), rows, planetary_reader)
    stored = system.barycentre
    cos_dec = math.cos(math.radians(stored.dec_deg))
    assert abs(fitted.ra_deg - stored.ra_deg) * 3.6e6 * cos_dec <= 0.1
    assert abs(fitted.dec_deg - stored.dec_deg) * 3.6e6 <= 0.1
    assert abs(fitted.pmra_mas_yr - stored.pmra_mas_yr) <= 0.01
    assert abs(fitted.pmdec_mas_yr - stored.pmdec_mas_yr) <= 0.01

    residuals = bsb.residuals_mas(system, rows, planetary_reader)
    alma = [math.hypot(*r) for r, row in zip(residuals, rows) if row["geocentric"]]
    assert len(alma) == 18
    assert math.sqrt(sum(a * a for a in alma) / len(alma)) <= ALMA_RMS_LIMIT_MAS
    assert max(alma) <= ALMA_WORST_LIMIT_MAS
    for (east, north), row in zip(residuals, rows):
        if not row["geocentric"]:
            assert abs(east) <= HIPPARCOS_SIGMA_LIMIT * row["sigma_east_mas"], (row["label"], east)
            assert abs(north) <= HIPPARCOS_SIGMA_LIMIT * row["sigma_north_mas"], (row["label"], north)


@pytest.mark.integration
def test_sirius_barycentre_is_the_hipparcos_orbital_solution() -> None:
    hip = FIXTURE["hipparcos_1997_sirius"]
    assert hip["multiplicity_flag"] == "O"
    assert hip["astrometric_reference_flag"] == "+"
    bary = SYSTEMS["Sirius"].barycentre
    assert bary.ra_deg == hip["ra_deg"]
    assert bary.dec_deg == hip["dec_deg"]
    assert bary.pmra_mas_yr == hip["pmra_mas_yr"]
    assert bary.pmdec_mas_yr == hip["pmdec_mas_yr"]
    assert bary.ref_epoch_jd == _julian_epoch_jd(1991.25)


def _component_record(name: str):
    return {record.name: record for record in stars._load_registry_records()}[name]


def _barycentre_from_components(system, jd: float):
    """Mass-weighted combination of the two component positions."""
    q = system.barycentre.secondary_mass_fraction
    names = {c.label: c.registry_name for c in system.components}
    vectors = []
    for label in ("A", "B"):
        if names.get(label):
            unit, distance = stars._binary_component_state(system, label, jd)
            vectors.append([u * distance for u in unit])
        else:
            vectors.append(None)
    if vectors[1] is None:
        # Sirius B has no registry row; recover the barycentre from A alone.
        east, north = component_offset_arcsec(system, "A", jd)
        unit, distance = stars._binary_component_state(system, "A", jd)
        bary = system.barycentre
        ra, dec = math.radians(bary.ra_deg), math.radians(bary.dec_deg)
        e = (-math.sin(ra), math.cos(ra), 0.0)
        n = (-math.sin(dec) * math.cos(ra), -math.sin(dec) * math.sin(ra), math.cos(dec))
        scale = math.pi / 648000.0 * 1000.0 / bary.parallax_mas
        return [u * distance - scale * (east * ei + north * ni) for u, ei, ni in zip(unit, e, n)]
    return [(1.0 - q) * a + q * b for a, b in zip(*vectors)]


@pytest.mark.integration
@pytest.mark.parametrize("name", ["Sirius", "Alpha Centauri"])
@pytest.mark.parametrize("year", [1000.0, 1800.0, 2200.0, 3000.0])
def test_barycentre_space_motion_matches_erfa(name: str, year: float) -> None:
    system = SYSTEMS[name]
    bary = system.barycentre
    jd = _julian_epoch_jd(year)
    vector = _barycentre_from_components(system, jd)
    dec0 = math.radians(bary.dec_deg)
    ra, dec, *_ = erfa.pmsafe(
        math.radians(bary.ra_deg), dec0,
        math.radians(bary.pmra_mas_yr / 3.6e6) / math.cos(dec0), math.radians(bary.pmdec_mas_yr / 3.6e6),
        bary.parallax_mas / 1000.0, bary.radial_velocity_km_s,
        bary.ref_epoch_jd, 0.0, jd, 0.0,
    )
    erfa_unit = _radec_unit(math.degrees(ra), math.degrees(dec))
    norm = math.sqrt(sum(c * c for c in vector))
    cos_angle = sum(a * b / norm for a, b in zip(vector, erfa_unit))
    sep_arcsec = math.degrees(math.acos(min(1.0, cos_angle))) * 3600.0
    assert sep_arcsec <= BARYCENTRE_ERFA_TOLERANCE_ARCSEC, sep_arcsec


@pytest.mark.integration
@pytest.mark.parametrize("name", ["Sirius", "Rigil Kentaurus", "Toliman"])
def test_component_never_leaves_its_orbit_about_the_barycentre(name: str) -> None:
    system, label = stars._binary_components()[name]
    bary = system.barycentre
    orbit = system.orbits[0]
    q = bary.secondary_mass_fraction
    share = q if label == "A" else 1.0 - q
    apastron = share * orbit.semi_major_arcsec * (1.0 + orbit.ecc)
    reference_distance = 1000.0 / bary.parallax_mas
    for year in range(-1000, 3001, 50):
        jd = _julian_epoch_jd(float(year))
        unit, distance = stars._binary_component_state(system, label, jd)
        centre = _barycentre_from_components(system, jd)
        norm = math.sqrt(sum(c * c for c in centre))
        cos_angle = sum(u * c / norm for u, c in zip(unit, centre))
        separation = math.degrees(math.acos(min(1.0, cos_angle))) * 3600.0
        assert separation <= apastron * reference_distance / distance * (1.0 + 1e-9), (year, separation)


@pytest.mark.integration
def test_alpha_cen_components_stay_with_their_barycentre_unlike_straight_line_rows() -> None:
    """The catalog rows carry instantaneous Hipparcos proper motions.

    Straight-line propagation of those rows strays from the orbit model by
    50 arcsec (A) and 28 arcsec (B) at 1800 and by 234 and 114 arcsec at
    1000 CE; near 2000-2100 the two agree within a few arcseconds.
    """
    system = SYSTEMS["Alpha Centauri"]
    for name, label in (("Rigil Kentaurus", "A"), ("Toliman", "B")):
        record = _component_record(name)
        for year in (1000.0, 1800.0, 3000.0):
            jd = _julian_epoch_jd(year)
            orbit_unit, _ = stars._binary_component_state(system, label, jd)
            line_unit, _ = astrometric_direction(
                record.ra_deg, record.dec_deg, record.pmra_mas_yr, record.pmdec_mas_yr,
                record.parallax_mas, record.radial_velocity_km_s, record.ref_epoch_jd, jd,
            )
            centre = _barycentre_from_components(system, jd)
            norm = math.sqrt(sum(c * c for c in centre))

            def separation(u):
                return math.degrees(math.acos(min(1.0, sum(a * c / norm for a, c in zip(u, centre))))) * 3600.0

            assert separation(orbit_unit) <= 11.0
            assert separation(line_unit) > separation(orbit_unit) + 5.0


@pytest.mark.integration
def test_results_name_their_motion_model() -> None:
    assert stars.star_at("Sirius", 2451545.0, product="astrometric").computation_truth.motion_model == "binary_orbit"
    assert stars.star_at("Toliman", 2451545.0, product="astrometric").computation_truth.motion_model == "binary_orbit"
    assert stars.star_at("Aldebaran", 2451545.0, product="astrometric").computation_truth.motion_model == "straight_line"
    assert stars.star_at("Proxima Centauri", 2451545.0, product="astrometric").computation_truth.motion_model == "straight_line"


@pytest.mark.integration
@pytest.mark.parametrize("name", ["Sirius", "Rigil Kentaurus"])
def test_native_chord_follows_the_component_over_a_heliacal_window(name: str) -> None:
    record = _component_record(name)
    system, label = stars._binary_components()[name]
    start, end = 2460310.5, 2460710.5
    inputs = stars._native_star_inputs(record, start, end)
    for jd in (start, 0.5 * (start + end), end):
        chord, _ = astrometric_direction(*inputs[:6], inputs[6], jd)
        track, _ = stars._binary_component_state(system, label, jd)
        sep = math.degrees(math.acos(min(1.0, sum(a * b for a, b in zip(chord, track))))) * 3600.0
        assert sep <= 0.1, (jd, sep)
    plain = _component_record("Aldebaran")
    assert stars._native_star_inputs(plain, start, end) == (
        plain.ra_deg, plain.dec_deg, plain.pmra_mas_yr, plain.pmdec_mas_yr,
        plain.parallax_mas, plain.radial_velocity_km_s, plain.ref_epoch_jd,
    )


@pytest.mark.integration
def test_gochara_refuses_a_binary_component_as_live_anchor() -> None:
    from moira._gochara_window_astronomy import _propagate
    from moira.gochara_dated import GocharaResourceError

    with pytest.raises(GocharaResourceError, match="binary component"):
        _propagate(_component_record("Sirius"), None)
