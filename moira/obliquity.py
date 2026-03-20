"""
Moira — obliquity.py
The Oracle of Obliquity: governs computation of the mean and true obliquity
of the ecliptic for any Julian Day.

Boundary: owns the full pipeline from Julian centuries to mean obliquity
(IAU 2006 P03 / Capitaine, Wallace & Chapront 2003) and true obliquity
(mean + nutation-in-obliquity correction). Delegates nutation-in-obliquity
values to nutation_2000a.py and the P03 polynomial to precession.py. Does
not own coordinate transforms, house calculations, or any display formatting.

Public surface:
    mean_obliquity, nutation, true_obliquity

Import-time side effects: None

External dependency assumptions:
    None (stdlib math only; nutation_2000a and precession are internal modules)
"""

import math
from .constants import DEG2RAD, RAD2DEG, ARCSEC2RAD
from .julian import centuries_from_j2000
from .nutation_2000a import nutation_2000a as _nutation_2000a
from .precession import mean_obliquity_p03 as _mean_obliquity_p03

# ---------------------------------------------------------------------------
# Mean obliquity — IAU 2006 P03 (Capitaine, Wallace & Chapront 2003)
# ---------------------------------------------------------------------------

def mean_obliquity(jd: float) -> float:
    """
    Governs computation of the mean obliquity of the ecliptic via the IAU 2006 P03 polynomial.

    Delegates to precession.mean_obliquity_p03. The P03 formula
    (Capitaine, Wallace & Chapront 2003) supersedes the older Laskar 1986 /
    IAU 1980 polynomial and is accurate to 0.04″ for dates within ±1000 years
    of J2000.0.

    Args:
        jd: Julian Day Number in Terrestrial Time (TT).

    Returns:
        Mean obliquity of the ecliptic in degrees.

    Raises:
        No exceptions raised; delegates entirely to precession.mean_obliquity_p03.

    Side effects:
        None.
    """
    return _mean_obliquity_p03(jd)


# ---------------------------------------------------------------------------
# IAU 1980 Nutation — abridged 106-term series
# Returns (Δψ, Δε) in degrees
# ---------------------------------------------------------------------------
# Each row: (n_l, n_lp, n_F, n_D, n_Om, S0, S1, C0, C1)
# Δψ = Σ (S0 + S1·T) · sin(arg)   in arcsec
# Δε = Σ (C0 + C1·T) · cos(arg)   in arcsec
# Argument = n_l·l + n_lp·l' + n_F·F + n_D·D + n_Om·Ω
#
# Source: Seidelmann 1982, as tabulated in Meeus "Astronomical Algorithms" ch.22

_NUTATION_TERMS: list[tuple[int,int,int,int,int, float,float,float,float]] = [
    # l   l'  F   D   Om      S0       S1      C0      C1
    ( 0,  0,  0,  0,  1, -171996, -174.2, 92025,   8.9),
    (-2,  0,  0,  2,  2,  -13187,   -1.6,  5736,  -3.1),
    ( 0,  0,  0,  2,  2,   -2274,   -0.2,   977,  -0.5),
    ( 0,  0,  0,  0,  2,    2062,    0.2,  -895,   0.5),
    ( 0,  1,  0,  0,  0,    1426,   -3.4,    54,  -0.1),
    ( 0,  0,  1,  0,  0,     712,    0.1,    -7,   0.0),
    (-2,  1,  0,  2,  2,    -517,    1.2,   224,  -0.6),
    ( 0,  0,  0,  2,  1,    -386,   -0.4,   200,   0.0),
    ( 0,  0,  1,  2,  2,    -301,    0.0,   129,  -0.1),
    (-2, -1,  0,  2,  2,     217,   -0.5,   -95,   0.3),
    (-2,  0,  1,  0,  0,    -158,    0.0,     0,   0.0),
    (-2,  0,  0,  2,  1,     129,    0.1,   -70,   0.0),
    ( 0,  0, -1,  2,  2,     123,    0.0,   -53,   0.0),
    ( 2,  0,  0,  0,  0,      63,    0.0,     0,   0.0),
    ( 0,  0,  1,  0,  1,      63,    0.1,   -33,   0.0),
    ( 2,  0, -1,  2,  2,     -59,    0.0,    26,   0.0),
    ( 0,  0, -1,  0,  1,     -58,   -0.1,    32,   0.0),
    ( 0,  0,  1,  2,  1,     -51,    0.0,    27,   0.0),
    (-2,  0,  2,  0,  0,      48,    0.0,     0,   0.0),
    ( 0,  0, -2,  2,  1,      46,    0.0,   -24,   0.0),
    ( 2,  0,  0,  2,  2,     -38,    0.0,    16,   0.0),
    ( 0,  0,  2,  2,  2,     -31,    0.0,    13,   0.0),
    ( 0,  0,  2,  0,  0,      29,    0.0,     0,   0.0),
    (-2,  0,  1,  2,  2,      29,    0.0,   -12,   0.0),
    ( 0,  0,  0,  2,  0,      26,    0.0,     0,   0.0),
    (-2,  0,  0,  2,  0,     -22,    0.0,     0,   0.0),
    ( 0,  0, -1,  2,  1,      21,    0.0,   -10,   0.0),
    ( 0,  2,  0,  0,  0,      17,   -0.1,     0,   0.0),
    ( 2,  0, -1,  0,  1,      16,    0.0,    -8,   0.0),
    (-2,  2,  0,  2,  2,     -16,    0.1,     7,   0.0),
    ( 0,  1,  0,  0,  1,     -15,    0.0,     9,   0.0),
    (-2,  0,  1,  0,  1,     -13,    0.0,     7,   0.0),
    ( 0, -1,  0,  0,  1,     -12,    0.0,     6,   0.0),
    ( 0,  0,  2, -2,  0,      11,    0.0,     0,   0.0),
    ( 2,  0, -1,  2,  1,     -10,    0.0,     5,   0.0),
    ( 2,  0,  1,  2,  2,      -8,    0.0,     3,   0.0),
    ( 0,  1,  0,  2,  2,       7,    0.0,    -3,   0.0),
    (-2,  1,  1,  0,  0,      -7,    0.0,     0,   0.0),
    ( 0, -1,  0,  2,  2,      -7,    0.0,     3,   0.0),
    ( 2,  0,  0,  2,  1,      -7,    0.0,     3,   0.0),
    ( 2,  0,  1,  0,  0,       7,    0.0,     0,   0.0),
    (-2,  0,  2,  2,  2,      -6,    0.0,     3,   0.0),
    (-2,  0,  1,  2,  1,      -6,    0.0,     3,   0.0),
    ( 2,  0, -2,  0,  1,       6,    0.0,    -3,   0.0),
    ( 2,  0,  0,  0,  1,       6,    0.0,    -3,   0.0),
    ( 0, -1,  1,  0,  0,       6,    0.0,     0,   0.0),
    (-2, -1,  0,  2,  1,      -5,    0.0,     3,   0.0),
    (-2,  0,  0,  0,  1,      -5,    0.0,     3,   0.0),
    ( 0,  0,  2,  2,  1,      -5,    0.0,     3,   0.0),
    (-2,  0,  2,  0,  1,       5,    0.0,    -3,   0.0),
    (-2,  1,  0,  2,  1,      -4,    0.0,     0,   0.0),  # truncated after here
]

def _fundamental_arguments(T: float) -> tuple[float, ...]:
    """
    Serves the nutation series by computing the five fundamental Delaunay arguments in degrees.

    Args:
        T: Julian centuries from J2000.0 (TT).

    Returns:
        Tuple (l, l', F, D, Ω) — mean anomaly of the Moon, mean anomaly of the
        Sun, Moon's argument of latitude, elongation of the Moon from the Sun,
        and longitude of the ascending node of the Moon; all in degrees.

    Side effects:
        None.
    """
    # Mean anomaly of the Moon (l)
    l  = (134.96298 + 477198.867398 * T
          + 0.0086972 * T**2 + T**3 / 56250.0) % 360.0
    # Mean anomaly of the Sun (l')
    lp = (357.52772 +  35999.050340 * T
          - 0.0001603 * T**2 - T**3 / 300000.0) % 360.0
    # Moon's argument of latitude (F)
    F  = (93.27191 + 483202.017538 * T
          - 0.0036825 * T**2 + T**3 / 327270.0) % 360.0
    # Elongation of the Moon from the Sun (D)
    D  = (297.85036 + 445267.111480 * T
          - 0.0019142 * T**2 + T**3 / 189474.0) % 360.0
    # Longitude of the ascending node of the Moon (Ω)
    Om = (125.04452 -   1934.136261 * T
          + 0.0020708 * T**2 + T**3 / 450000.0) % 360.0
    return l, lp, F, D, Om


def nutation(jd: float) -> tuple[float, float]:
    """
    Governs computation of nutation in longitude (Δψ) and obliquity (Δε).

    Delegates to the full IAU 2000A model (1320 + 38 luni-solar terms,
    1037 + 19 obliquity terms) with IAU 2006 adjustments, implemented in
    nutation_2000a.py.

    Args:
        jd: Julian Day in Terrestrial Time (TT).

    Returns:
        Tuple (delta_psi, delta_eps) — nutation in longitude and nutation in
        obliquity, both in degrees.

    Raises:
        No exceptions raised; delegates entirely to nutation_2000a.

    Side effects:
        None.
    """
    return _nutation_2000a(jd)


def true_obliquity(jd: float) -> float:
    """
    Governs computation of the true obliquity of the ecliptic by combining mean
    obliquity with the nutation-in-obliquity correction (Δε).

    Args:
        jd: Julian Day in Terrestrial Time (TT).

    Returns:
        True obliquity of the ecliptic in degrees (mean obliquity + Δε).

    Raises:
        No exceptions raised; delegates to mean_obliquity and nutation.

    Side effects:
        None.
    """
    eps0 = mean_obliquity(jd)
    _, deps = nutation(jd)
    return eps0 + deps
