"""Polar star ayanamsa against an independent ERFA composition.

ERFA gives each anchor star's true equator of date (pmsafe, pnm06a); the
polar longitude is then the ecliptic point with the star's right ascension,
``λp = atan2(sin α, cos α cos ε)`` with ε = obl06 + Δε. Moira derives the same
point from the star's true ecliptic coordinates (AYANAMSA_DOCTRINE_STANDARD.md,
Section 2.3), so the two paths share only the catalog inputs.
"""

from __future__ import annotations

import math

import pytest

from moira.ayanamsa_doctrine import POLAR_STAR_CATALOGUE, _YOGATARA
from moira.sidereal import PolarStarAyanamsa, _ayanamsa_truth_at_tt
from tests.integration.test_stars_erfa_reference import _registry_by_name, _split_jd

erfa = pytest.importorskip("erfa")

EPOCHS_TT = [2378496.5, 2451545.0, 2461000.5, 2488069.5]
# Measured 2026-10-30 over these stars and epochs: at most 0.00001″. The
# polar construction adds only floating-point error to the shared star term.
TOLERANCE_ARCSEC = 0.001


def _erfa_polar_longitude(name: str, jd_tt: float) -> float:
    row = _registry_by_name()[name]
    cos_dec = math.cos(math.radians(float(row["dec_deg"])))
    pmr = (float(row["pmra_mas_yr"]) / 1000.0) / 3600.0 / cos_dec
    pmd = (float(row["pmdec_mas_yr"]) / 1000.0) / 3600.0
    jd1a, jd1b = _split_jd(float(row["ref_epoch_jd"]))
    jd2a, jd2b = _split_jd(jd_tt)
    ra, dec, *_ = erfa.pmsafe(
        math.radians(float(row["ra_deg"])), math.radians(float(row["dec_deg"])),
        math.radians(pmr), math.radians(pmd),
        max(0.0, float(row["parallax_mas"]) / 1000.0), float(row["radial_velocity_km_s"]),
        jd1a, jd1b, jd2a, jd2b,
    )
    p_true_equ = erfa.rxp(erfa.pnm06a(jd2a, jd2b), erfa.s2c(ra, dec))
    alpha, _ = erfa.c2s(p_true_equ)
    eps = erfa.obl06(jd2a, jd2b) + erfa.nut06a(jd2a, jd2b)[1]
    return math.degrees(math.atan2(math.sin(alpha), math.cos(alpha) * math.cos(eps))) % 360.0


@pytest.mark.integration
@pytest.mark.parametrize("nakshatra", sorted(POLAR_STAR_CATALOGUE["surya_siddhanta"]))
@pytest.mark.parametrize("jd_tt", EPOCHS_TT)
def test_polar_longitude_matches_erfa(nakshatra: str, jd_tt: float) -> None:
    truth = _ayanamsa_truth_at_tt(jd_tt, PolarStarAyanamsa("surya_siddhanta", nakshatra), "true")
    moira_polar = dict(truth.doctrine_terms)["star_polar_longitude_deg"]
    expected = _erfa_polar_longitude(_YOGATARA[nakshatra][0], jd_tt)
    diff = (((moira_polar - expected) + 180.0) % 360.0 - 180.0) * 3600.0
    assert abs(diff) <= TOLERANCE_ARCSEC, (nakshatra, jd_tt, diff)
