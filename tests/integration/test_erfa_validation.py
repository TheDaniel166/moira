from __future__ import annotations

import math

import pytest

from moira.coordinates import mat_mul, nutation_matrix_equatorial, precession_matrix_equatorial
from moira.julian import greenwich_mean_sidereal_time
from moira.obliquity import nutation, true_obliquity
from moira.precession import mean_obliquity_p03, precession_matrix

erfa = pytest.importorskip("erfa")

ARCSEC = 3600.0
PASS_THRESHOLD_ARCSEC = 0.001
TEST_EPOCHS = [
    ("-500 (500 BCE)", 1903682.5, 1903682.5),
    ("-200 (200 BCE)", 1794303.5, 1794303.5),
    ("J0000 (1 CE)", 1721045.5, 1721045.5),
    ("J1000.0", 2086308.0, 2086308.0),
    ("J1500.0", 2268923.5, 2268923.5),
    ("J1800.0", 2378496.5, 2378496.5),
    ("J1900.0", 2415020.5, 2415020.5),
    ("J2000.0", 2451545.0, 2451545.0),
    ("J2010.0", 2455196.5, 2455196.5),
    ("J2024.0", 2460310.5, 2460310.5),
    ("J2050.0", 2469807.5, 2469807.5),
    ("J2100.0", 2488069.5, 2488069.5),
]


def _split(jd: float) -> tuple[float, float]:
    return float(int(jd)), float(jd - int(jd))


def _wrapped_arcsec(a_deg: float, b_deg: float) -> float:
    delta_arcsec = abs(a_deg - b_deg) * ARCSEC
    if delta_arcsec > 180.0 * ARCSEC:
        delta_arcsec = 360.0 * ARCSEC - delta_arcsec
    return delta_arcsec


def _matrix_max_diff_arcsec(erfa_matrix, moira_matrix) -> float:
    max_diff = 0.0
    for i in range(3):
        for j in range(3):
            max_diff = max(max_diff, abs(float(erfa_matrix[i][j]) - moira_matrix[i][j]))
    return max_diff * (180.0 / math.pi) * ARCSEC


@pytest.mark.integration
@pytest.mark.parametrize(("label", "jd_tt", "jd_ut"), TEST_EPOCHS, ids=[label for label, _, _ in TEST_EPOCHS])
def test_gmst_matches_erfa(label: str, jd_tt: float, jd_ut: float) -> None:
    d1u, d2u = _split(jd_ut)
    d1t, d2t = _split(jd_tt)
    erfa_gmst = math.degrees(erfa.gmst06(d1u, d2u, d1t, d2t)) % 360.0
    moira_gmst = greenwich_mean_sidereal_time(jd_ut) % 360.0

    assert _wrapped_arcsec(erfa_gmst, moira_gmst) < PASS_THRESHOLD_ARCSEC


@pytest.mark.integration
@pytest.mark.parametrize(("label", "jd_tt", "_jd_ut"), TEST_EPOCHS, ids=[label for label, _, _ in TEST_EPOCHS])
def test_mean_obliquity_matches_erfa(label: str, jd_tt: float, _jd_ut: float) -> None:
    d1, d2 = _split(jd_tt)
    erfa_eps = math.degrees(erfa.obl06(d1, d2))
    moira_eps = mean_obliquity_p03(jd_tt)

    assert abs(erfa_eps - moira_eps) * ARCSEC < PASS_THRESHOLD_ARCSEC


@pytest.mark.integration
@pytest.mark.parametrize(("label", "jd_tt", "_jd_ut"), TEST_EPOCHS, ids=[label for label, _, _ in TEST_EPOCHS])
def test_nutation_matches_erfa(label: str, jd_tt: float, _jd_ut: float) -> None:
    d1, d2 = _split(jd_tt)
    erfa_dpsi, erfa_deps = erfa.nut06a(d1, d2)
    moira_dpsi_deg, moira_deps_deg = nutation(jd_tt)

    dpsi_error_arcsec = abs(math.degrees(erfa_dpsi) - moira_dpsi_deg) * ARCSEC
    deps_error_arcsec = abs(math.degrees(erfa_deps) - moira_deps_deg) * ARCSEC

    assert dpsi_error_arcsec < PASS_THRESHOLD_ARCSEC
    assert deps_error_arcsec < PASS_THRESHOLD_ARCSEC


@pytest.mark.integration
@pytest.mark.parametrize(("label", "jd_tt", "_jd_ut"), TEST_EPOCHS, ids=[label for label, _, _ in TEST_EPOCHS])
def test_precession_matrix_matches_erfa(label: str, jd_tt: float, _jd_ut: float) -> None:
    d1, d2 = _split(jd_tt)
    erfa_matrix = erfa.pmat06(d1, d2)
    moira_matrix = precession_matrix(jd_tt)

    assert _matrix_max_diff_arcsec(erfa_matrix, moira_matrix) < PASS_THRESHOLD_ARCSEC


@pytest.mark.integration
@pytest.mark.parametrize(("label", "jd_tt", "_jd_ut"), TEST_EPOCHS, ids=[label for label, _, _ in TEST_EPOCHS])
def test_precession_nutation_matrix_matches_erfa(label: str, jd_tt: float, _jd_ut: float) -> None:
    d1, d2 = _split(jd_tt)
    erfa_matrix = erfa.pnm06a(d1, d2)
    moira_matrix = mat_mul(nutation_matrix_equatorial(jd_tt), precession_matrix_equatorial(jd_tt))

    assert _matrix_max_diff_arcsec(erfa_matrix, moira_matrix) < PASS_THRESHOLD_ARCSEC


@pytest.mark.integration
@pytest.mark.parametrize(("label", "jd_tt", "_jd_ut"), TEST_EPOCHS, ids=[label for label, _, _ in TEST_EPOCHS])
def test_true_obliquity_matches_erfa(label: str, jd_tt: float, _jd_ut: float) -> None:
    d1, d2 = _split(jd_tt)
    _dpsi, erfa_deps = erfa.nut06a(d1, d2)
    erfa_true = math.degrees(erfa.obl06(d1, d2) + erfa_deps)
    moira_true = true_obliquity(jd_tt)

    assert abs(erfa_true - moira_true) * ARCSEC < PASS_THRESHOLD_ARCSEC


@pytest.mark.integration
@pytest.mark.parametrize(("label", "jd_tt", "jd_ut"), TEST_EPOCHS, ids=[label for label, _, _ in TEST_EPOCHS])
def test_gast_approximation_matches_erfa(label: str, jd_tt: float, jd_ut: float) -> None:
    d1u, d2u = _split(jd_ut)
    d1t, d2t = _split(jd_tt)
    erfa_dpsi, erfa_deps = erfa.nut06a(d1t, d2t)
    erfa_eps = erfa.obl06(d1t, d2t)
    erfa_eqeq_rad = erfa_dpsi * math.cos(erfa_eps + erfa_deps)
    erfa_gast_deg = math.degrees(erfa.gmst06(d1u, d2u, d1t, d2t) + erfa_eqeq_rad) % 360.0

    moira_gmst = greenwich_mean_sidereal_time(jd_ut)
    moira_dpsi_deg, moira_deps_deg = nutation(jd_tt)
    moira_eps_rad = math.radians(mean_obliquity_p03(jd_tt) + moira_deps_deg)
    moira_gast_deg = (moira_gmst + moira_dpsi_deg * math.cos(moira_eps_rad)) % 360.0

    assert _wrapped_arcsec(erfa_gast_deg, moira_gast_deg) < PASS_THRESHOLD_ARCSEC
