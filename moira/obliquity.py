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
    None (stdlib only; nutation_2000a and precession are internal modules)
"""

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


def nutation(jd: float) -> tuple[float, float]:
    """
    Governs computation of nutation in longitude (Δψ) and obliquity (Δε).

    Delegates to the full IAU 2000A series evaluator implemented in
    nutation_2000a.py. Within Moira's validated standards stack this nutation
    surface is paired with IAU 2006 precession and checked against ERFA/SOFA
    ``nut06a``.

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
