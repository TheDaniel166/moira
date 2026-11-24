"""Independent ERFA frame and geometry checks for Galactic ayanamsas.

Geometric ICRS anchors, mean and true equinoxes of date, eight Julian epochs
and two P03 bounds in TT. The 0.001 arcsecond circular tolerance measures the
numerical frame and projection, with the catalogue direction held fixed. It
does not measure the observational accuracy of a published Galactic plane.
"""

import math

import pytest

from moira.constants import J2000
from moira.cosmic_references import cosmic_reference_definition
from moira.galactic_ayanamsa import GalacticAyanamsa
from moira.sidereal import _ayanamsa_truth_at_tt

erfa = pytest.importorskip("erfa")

TOLERANCE_ARCSEC = 0.001
EPOCHS = (1600, 1900, 2000, 2015, 2026, 2100, 2225, 2400, -3000, 7000)
ECLIPTIC_NORTH = (0.0, 0.0, 1.0)
# Liu et al. (2024), Eqs. (30) and (35).
ALLWISE_POLE = (282.936 - 90.0, 90.0 - 63.398)
# Liu, Zhu & Zhang (2011), section 4, proposed ICRS pole.
LIU_POLE = (
    15.0 * (12.0 + 51.0 / 60.0 + 36.7151981 / 3600.0),
    27.0 + 6.0 / 60.0 + 11.193172 / 3600.0,
)
# ICRS realization of the historical IAU pole in the same 2011 paper.
HISTORICAL_POLE = (
    15.0 * (12.0 + 51.0 / 60.0 + 26.27469 / 3600.0),
    27.0 + 7.0 / 60.0 + 41.7087 / 3600.0,
)
MID_MULA = 240.0 + 6.0 + 40.0 / 60.0
CASES = (
    ("centre_sagittarius", "direct", 240.0, None),
    ("centre_gil_brand", "direct", 244.3769410125, None),
    ("centre_cochrane", "direct", 270.0, None),
    ("centre_wilhelm", "polar", MID_MULA, None),
    ("centre_mid_mula", "direct", MID_MULA, None),
    ("equator_allwise_2024", "node", 240.0, ALLWISE_POLE),
    ("equator_liu_2011", "node", 240.0, LIU_POLE),
    ("equator_liu_2011_mid_mula", "node", MID_MULA, LIU_POLE),
)


def _frames(jd_tt, mode):
    delta_days = jd_tt - J2000
    obliquity = erfa.obl06(J2000, delta_days)
    if mode == "mean":
        return erfa.ecm06(J2000, delta_days), erfa.pmat06(J2000, delta_days), obliquity

    _, delta_obliquity = erfa.nut06a(J2000, delta_days)
    obliquity += delta_obliquity
    equatorial = erfa.pnm06a(J2000, delta_days)
    return erfa.rx(obliquity, equatorial.copy()), equatorial, obliquity


def _longitude(vector):
    longitude, _ = erfa.c2s(vector)
    return math.degrees(longitude) % 360.0


def _reference_anchor(jd_tt, mode, projection, pole):
    ecliptic, equatorial, obliquity = _frames(jd_tt, mode)
    if projection == "node":
        pole_in_ecliptic = erfa.rxp(ecliptic, erfa.s2c(*map(math.radians, pole)))
        node = erfa.pxp(ECLIPTIC_NORTH, pole_in_ecliptic)
        return _longitude(node), pole_in_ecliptic

    source = cosmic_reference_definition("sagittarius_a_star")
    direction = erfa.s2c(math.radians(source.icrs_ra_deg), math.radians(source.icrs_dec_deg))
    if projection == "polar":
        # The point on the ecliptic has the same RA as Sgr A*. Equate the
        # RAs in the equatorial frame rather than starting from ecliptic latitude.
        right_ascension, _ = erfa.c2s(erfa.rxp(equatorial, direction))
        projected = math.atan2(math.sin(right_ascension), math.cos(right_ascension) * math.cos(obliquity))
        return math.degrees(projected) % 360.0, None

    return _longitude(erfa.rxp(ecliptic, direction)), None


def _circular_residual_arcsec(actual, expected):
    return ((actual - expected + 180.0) % 360.0 - 180.0) * 3600.0


@pytest.mark.integration
@pytest.mark.parametrize("mode", ["mean", "true"])
@pytest.mark.parametrize("epoch", EPOCHS)
@pytest.mark.parametrize(("preset", "projection", "target_deg", "pole"), CASES)
def test_galactic_ayanamsa_against_erfa(preset, projection, target_deg, pole, epoch, mode):
    jd_tt = sum(erfa.epj2jd(float(epoch)))
    expected, pole_in_ecliptic = _reference_anchor(jd_tt, mode, projection, pole)
    truth = _ayanamsa_truth_at_tt(jd_tt, GalacticAyanamsa(preset), mode)
    actual = truth.anchor_tropical_longitude_deg
    assert actual is not None
    residual = _circular_residual_arcsec(actual, expected)
    assert abs(residual) <= TOLERANCE_ARCSEC, (preset, epoch, mode, residual)
    assert truth.ayanamsa_unwrapped_deg == pytest.approx(expected - target_deg, abs=TOLERANCE_ARCSEC / 3600, rel=0)

    if pole_in_ecliptic is not None:
        actual_node = erfa.s2c(math.radians(actual), 0.0)
        assert abs(erfa.pdp(ECLIPTIC_NORTH, actual_node)) < 1e-14
        assert abs(erfa.pdp(pole_in_ecliptic, actual_node)) < math.radians(TOLERANCE_ARCSEC / 3600.0)
        if epoch == 2000:
            source_longitude, _ = _reference_anchor(jd_tt, mode, "direct", None)
            assert abs(_circular_residual_arcsec(actual, source_longitude)) < 90.0 * 3600.0


@pytest.mark.integration
def test_allwise_2024_shift_from_transformed_1958_plane_at_j2000():
    old_node, _ = _reference_anchor(J2000, "mean", "node", HISTORICAL_POLE)
    allwise = _ayanamsa_truth_at_tt(J2000, GalacticAyanamsa("equator_allwise_2024"), "mean")
    assert old_node - 240.0 == pytest.approx(30.0232213, abs=TOLERANCE_ARCSEC / 3600.0, rel=0)
    assert (allwise.ayanamsa_deg - (old_node - 240.0)) * 60.0 == pytest.approx(20.40725, abs=0.00002, rel=0)
