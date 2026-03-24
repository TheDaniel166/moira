"""
tests/integration/test_multiple_stars_external_reference.py

External-reference spot checks for moira.multiple_stars.

Authority:
  Published Sirius AB yearly orbit ephemeris:
  https://www.stelledoppie.it/index2.php?iddoppia=27936&menu=29&orderby=notes_DESC&righe=50

Notes:
  - The published values are yearly Jan 1 ephemerides.
  - Theta is position angle in degrees, measured north through east.
  - Rho is separation in arcseconds.
"""

import pytest

from moira.multiple_stars import angular_separation_at, multiple_star, position_angle_at


SIRIUS_PUBLISHED_EPHEMERIS = [
    # jd_ut, published_theta_deg, published_rho_arcsec
    (2451544.5, 151.2, 4.460),   # 2000-01-01
    (2458849.5, 68.1, 11.193),   # 2020-01-01
    (2462502.5, 48.9, 10.392),   # 2030-01-01
]


def test_sirius_ab_matches_published_orbit_ephemeris():
    sirius = multiple_star("Sirius")

    for jd, theta_ref, rho_ref in SIRIUS_PUBLISHED_EPHEMERIS:
        rho = angular_separation_at(sirius, jd)
        theta = position_angle_at(sirius, jd)
        assert rho == pytest.approx(rho_ref, abs=0.2)
        assert theta == pytest.approx(theta_ref, abs=1.5)
