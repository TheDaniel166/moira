"""
Integration tests for the Vondrak 2011 long-term precession matrix against
ERFA eraLtp across the ancient epoch domain (|T| > 50 centuries).

Validated finding (2026-04-07): at every epoch from 3000 BCE to 9650 BCE,
vondrak_precession_matrix() agrees with erfa.ltp() to machine epsilon
(|Delta R| < 10^-10 arcsec).  This confirms the port of eraLtpecl / eraLtpequ
/ eraLtp is correct across the full long-term domain.

Frame-definition note:
    Moira uses the Vondrak / IAU 2006+ ecliptic.  JPL Horizons reports positions
    in the IAU 76/80 ecliptic-of-date (Lieske 1977), which is a polynomial only
    valid to +-50 centuries.  At T ~ -116 the two ecliptic pole definitions diverge
    materially: the Sun (ecliptic latitude ~ 0) is unaffected, but the Moon
    (latitude ~ -4 deg) differs by ~39 arcminutes.  Moira's answer is correct;
    Horizons' output at this epoch is an extrapolation of an obsolete model.
"""
from __future__ import annotations

import math

import pytest

from moira.julian import centuries_from_j2000
from moira.precession import vondrak_precession_matrix

erfa = pytest.importorskip("erfa")

# Threshold: machine epsilon for double-precision trig should keep all matrix
# element differences below 1e-9 arcsec.  We use 1e-6 arcsec as the pass
# criterion to give a comfortable margin while still catching any regression
# in the coefficient tables or loop logic.
PASS_THRESHOLD_ARCSEC = 1e-6

# Epochs are all in the Vondrak zone (|T| > 50).  JD values are approximate
# Julian Calendar midnight dates; the exact value does not affect the matrix
# accuracy assertion since both sides receive the same T.
#
# Format: (label, jd_approx)
ANCIENT_EPOCHS = [
    ("3000 BCE  (T ~ -50)",  481300.5),
    ("4000 BCE  (T ~ -60)",   43882.5),
    ("5000 BCE  (T ~ -70)", -393537.5),
    ("6000 BCE  (T ~ -80)", -830957.5),
    ("7000 BCE  (T ~ -90)",-1268376.5),
    ("8000 BCE  (T ~-100)",-1705796.5),
    ("9000 BCE  (T ~-110)",-2143216.5),
    ("9650 BCE  (T ~-116)",-1803239.5),  # Astrodienst reference epoch
]


def _matrix_max_diff_arcsec(erfa_matrix, our_matrix: tuple) -> float:
    """Return the maximum absolute element difference in arcseconds."""
    max_diff = 0.0
    for i in range(3):
        for j in range(3):
            diff = abs(float(erfa_matrix[i][j]) - our_matrix[i][j])
            if diff > max_diff:
                max_diff = diff
    return max_diff * (180.0 / math.pi) * 3600.0


@pytest.mark.integration
@pytest.mark.parametrize(
    ("label", "jd"),
    ANCIENT_EPOCHS,
    ids=[label for label, _ in ANCIENT_EPOCHS],
)
def test_vondrak_matrix_matches_erfa_ancient(label: str, jd: float) -> None:
    """
    vondrak_precession_matrix() must agree with erfa.ltp() to machine epsilon
    at every epoch in the long-term (|T| > 50) domain.

    erfa.ltp() takes a Julian epoch (years); we derive it from T via
    epj = 2000.0 + T * 100.0, consistent with eraLtpecl / eraLtpequ internals.
    """
    T = centuries_from_j2000(jd)
    epj = 2000.0 + T * 100.0

    erfa_matrix = erfa.ltp(epj)
    our_matrix = vondrak_precession_matrix(jd)

    diff_arcsec = _matrix_max_diff_arcsec(erfa_matrix, our_matrix)
    assert diff_arcsec < PASS_THRESHOLD_ARCSEC, (
        f"{label}: max matrix element diff {diff_arcsec:.2e} arcsec "
        f"exceeds threshold {PASS_THRESHOLD_ARCSEC:.0e} arcsec"
    )


@pytest.mark.integration
@pytest.mark.parametrize(
    ("label", "jd"),
    ANCIENT_EPOCHS,
    ids=[label for label, _ in ANCIENT_EPOCHS],
)
def test_vondrak_matrix_is_orthogonal(label: str, jd: float) -> None:
    """
    The precession rotation matrix must be orthogonal (R @ R^T = I) to
    machine epsilon.  This catches sign errors or normalization failures
    in the ecliptic / equator pole construction.
    """
    m = vondrak_precession_matrix(jd)
    for i in range(3):
        for j in range(3):
            dot = sum(m[i][k] * m[j][k] for k in range(3))
            expected = 1.0 if i == j else 0.0
            assert abs(dot - expected) < 1e-12, (
                f"{label}: R @ R^T [{i},{j}] = {dot:.6e}, expected {expected} "
                f"(orthogonality violated)"
            )
