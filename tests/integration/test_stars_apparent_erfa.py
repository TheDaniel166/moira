"""Fixed-star position products against ERFA (Phase 3 of the fixed-star standard).

Governing record: wiki/02_standards/FIXED_STARS_BACKEND_STANDARD.md, Sections
1-2 and 7. Authority for the apparent product: ERFA ``apcg`` built from
Moira's own DE441 Earth state, then ``atciq`` (space motion with parallax,
solar light deflection, annual aberration). The comparison is made on the
geocentric ICRS-oriented direction, before the shared frame rotation.

Measured on 2026-10-29 for the 12 stars and 6 epochs below: median 0.000003
arcsec, worst 0.00014 arcsec (Barnard's Star, 2100; the declared second-order
light-time term). Moira also deflects by Jupiter and Saturn, which ERFA's
``atciq`` omits; those are micro-arcsecond effects away from the planets.
"""

from __future__ import annotations

import math
import warnings

import pytest

import moira.stars as stars

erfa = pytest.importorskip("erfa")
np = pytest.importorskip("numpy")

AU_KM = 149597870.7
APPARENT_ERFA_THRESHOLD_ARCSEC = 0.001
STARS = ["Sirius", "Aldebaran", "Regulus", "Spica", "Antares", "Polaris", "Vega",
         "Rigil Kentaurus", "Barnard's Star", "Fomalhaut", "Arcturus", "Algol"]
EPOCHS = [2378496.5, 2415020.5, 2451545.0, 2460311.0, 2469807.5, 2488069.5]

pytestmark = pytest.mark.requires_ephemeris


def _angle_arcsec(u, v):
    cross = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    dot = sum(a * b for a, b in zip(u, v))
    return math.degrees(math.atan2(math.sqrt(sum(c * c for c in cross)), dot)) * 3600.0


def _record(name):
    return {record.name: record for record in stars._load_registry_records()}[name]


def _erfa_apparent(record, jd_tt, reader):
    from moira.constants import Body
    from moira.planets import _earth_barycentric_state, _geocentric

    position, velocity = _earth_barycentric_state(jd_tt, reader)
    sun = _geocentric(Body.SUN, jd_tt, reader)
    earth_pv = np.zeros((), dtype=erfa.dt_pv)
    earth_pv["p"] = np.array(position) / AU_KM
    earth_pv["v"] = np.array(velocity) / AU_KM
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        astrom = erfa.apcg(jd_tt, 0.0, earth_pv, -np.array(sun) / AU_KM)
        binary = stars._binary_components().get(record.name)
        if binary is None:
            dec = math.radians(record.dec_deg)
            parallax = record.parallax_mas / 1000.0 if record.parallax_mas > 0 else 0.0
            ra_i, dec_i = erfa.atciq(
                math.radians(record.ra_deg), dec,
                math.radians(record.pmra_mas_yr / 3.6e6) / math.cos(dec),
                math.radians(record.pmdec_mas_yr / 3.6e6),
                parallax, record.radial_velocity_km_s, astrom,
            )
        else:
            # A binary component's stage-1 position comes from its orbit
            # (test_stars_binary_orbits.py); ERFA checks stage 2 from there,
            # with the component's parallax at the date and no further motion.
            unit, distance_pc = stars._binary_component_state(binary[0], binary[1], jd_tt)
            ra_c, dec_c = erfa.c2s(np.array(unit))
            ra_i, dec_i = erfa.atciq(ra_c, dec_c, 0.0, 0.0, 1.0 / distance_pc, 0.0, astrom)
    return (math.cos(dec_i) * math.cos(ra_i), math.cos(dec_i) * math.sin(ra_i), math.sin(dec_i))


@pytest.mark.integration
@pytest.mark.parametrize("name", STARS)
def test_apparent_product_matches_erfa_geocentric_place(name, planetary_reader):
    record = _record(name)
    assert record.ref_epoch_jd == 2451545.0  # atciq takes catalog values at J2000.0
    for jd_tt in EPOCHS:
        moira = stars._icrs_position(record, jd_tt, "apparent", planetary_reader)
        norm = math.sqrt(sum(c * c for c in moira))
        moira = tuple(c / norm for c in moira)
        assert _angle_arcsec(moira, _erfa_apparent(record, jd_tt, planetary_reader)) < APPARENT_ERFA_THRESHOLD_ARCSEC


@pytest.mark.integration
@pytest.mark.parametrize("name", STARS)
def test_apparent_minus_astrometric_stays_within_physical_bounds(name, planetary_reader):
    record = _record(name)
    # Annual aberration is at most v/c (about 20.5 arcsec); parallax is at
    # most the catalog parallax; solar light deflection at these stars'
    # elongations stays well under one arcsecond.
    bound = 20.6 + max(record.parallax_mas, 0.0) / 1000.0 + 1.0
    for jd_tt in EPOCHS:
        apparent = stars.star_at(name, jd_tt, product="apparent", reader=planetary_reader)
        astrometric = stars.star_at(name, jd_tt)
        shift = math.hypot(
            ((apparent.longitude - astrometric.longitude + 180.0) % 360.0 - 180.0)
            * math.cos(math.radians(astrometric.latitude)),
            apparent.latitude - astrometric.latitude,
        ) * 3600.0
        assert 0.0 < shift < bound


@pytest.mark.integration
def test_products_are_named_on_every_result(planetary_reader):
    astrometric = stars.star_at("Spica", 2460311.0)
    apparent = stars.star_at("Spica", 2460311.0, product="apparent", reader=planetary_reader)
    geometric = stars.star_at("Spica", 2460311.0, product="geometric")
    for star, product, observer in (
        (astrometric, "astrometric", "barycentric"),
        (apparent, "apparent", "geocentric"),
        (geometric, "geometric", "barycentric"),
    ):
        assert star.computation_truth.position_product == product
        assert star.computation_truth.true_position is (product == "geometric")
        assert star.classification.observer_mode == observer


def test_geometric_is_the_observed_direction_one_light_time_later():
    record = _record("Arcturus")
    jd_tt = 2460311.0
    light_days = 3261.56 / record.parallax_mas * 365.25
    observed, geometric = stars.star_light_time_split("Arcturus", jd_tt)
    later = stars.star_at("Arcturus", jd_tt + light_days)
    assert observed.longitude == stars.star_at("Arcturus", jd_tt).longitude
    assert observed.computation_truth.position_product == "astrometric"
    assert geometric.computation_truth.position_product == "geometric"
    # Same space motion, evaluated one light time later; only the frame of
    # date differs between the two.
    record_later = stars._icrs_position(record, jd_tt + light_days, "astrometric", None)
    record_geometric = stars._icrs_position(record, jd_tt, "geometric", None)
    assert _angle_arcsec(record_later, record_geometric) == pytest.approx(0.0, abs=1e-9)
    # Arcturus moves about 2.3 arcsec/yr and lies about 37 light years away.
    separation = math.hypot(
        (geometric.longitude - observed.longitude) * math.cos(math.radians(observed.latitude)),
        geometric.latitude - observed.latitude,
    ) * 3600.0
    assert 80.0 < separation < 95.0
    assert later.longitude != observed.longitude


def test_unknown_product_is_refused():
    with pytest.raises(ValueError, match="unknown star position product"):
        stars.star_at("Sirius", 2451545.0, product="true")


def test_apparent_without_a_reader_fails_closed(monkeypatch):
    import moira.spk_reader as spk_reader

    monkeypatch.setattr(spk_reader, "get_active_reader", lambda: None)
    with pytest.raises(spk_reader.MissingKernelError):
        stars.star_at("Sirius", 2451545.0, product="apparent")
