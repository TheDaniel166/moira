"""
Moira — precession.py
The Precession Engine: governs IAU 2006 luni-solar precession computation using
the Fukushima-Williams four-angle parameterization (P03).

Boundary: owns the full precession pipeline from Julian centuries to the final
B×P rotation matrix. Delegates time conversion to julian, coordinate rotation
primitives to coordinates, and physical constants to constants. Does not own
nutation, aberration, or any display formatting.

Public surface:
    general_precession_in_longitude, mean_obliquity_p03, precession_matrix

Import-time side effects: None

External dependency assumptions:
    - moira.julian must be importable (centuries_from_j2000).
    - moira.constants must be importable (ARCSEC2RAD).
    - moira.coordinates must be importable (rot_x_axis, rot_z_axis, mat_mul);
      accessed lazily inside _fw2m to avoid circular imports.
"""

import math
from .julian import centuries_from_j2000
from .constants import ARCSEC2RAD

# ---------------------------------------------------------------------------
# Frame-bias constants (SOFA iauBp06 / Chapront et al. 2002, mas → arcsec)
# Applied to FW angles so the matrix equals B×P (erfa.pmat06 compatible).
# ---------------------------------------------------------------------------
_DPBIAS  = -0.041775   # correction added to ψ̄  (arcsec)  [≈ −14.6 mas offset via psib constant]
_DEBIAS  =  0.0        # correction added to εA  (none needed; absorbed into phib)
# The standard SOFA bias offsets enter via the constant terms of gamb and psib:
#   gamb₀ = −0.052928″  (frame-bias in RA)
#   psib₀ = −0.041775″  (frame-bias in longitude)
# These are already present in the polynomial constant terms below.

def general_precession_in_longitude(jd_tt: float) -> float:
    """
    Return the general precession in longitude ψ_A (IAU 2006) in degrees.

    Computes the accumulated luni-solar precession in ecliptic longitude from
    J2000.0 to the given epoch using the truncated polynomial from Capitaine
    et al. 2003 (Table 1, column ψ_A). This is a simplified scalar quantity
    used for approximate precession corrections; for the full rotation matrix
    use precession_matrix().

    Args:
        jd_tt: Julian Date in Terrestrial Time (TT).

    Returns:
        ψ_A in decimal degrees, measured from the J2000.0 ecliptic.
    """
    T = centuries_from_j2000(jd_tt)
    psi_a = (5029.0966 * T + 1.1111 * T**2 + 0.000006 * T**3) / 3600.0
    return psi_a

def mean_obliquity_p03(jd_tt: float) -> float:
    """
    Return the mean obliquity of the ecliptic ε_A (IAU 2006) in degrees.

    Evaluates the fifth-degree polynomial from Capitaine et al. 2003 (A&A 412,
    567–586), identical to SOFA iauObl06. Valid from approximately 500 BCE to
    2100 CE; accuracy degrades beyond that range.

    Args:
        jd_tt: Julian Date in Terrestrial Time (TT).

    Returns:
        ε_A in decimal degrees.
    """
    T = centuries_from_j2000(jd_tt)
    eps_a = (84381.406
             - 46.836769     * T
             -  0.0001831    * T**2
             +  0.00200340   * T**3
             -  0.000000576  * T**4
             -  0.0000000434 * T**5) / 3600.0
    return eps_a

# ---------------------------------------------------------------------------
# Fukushima-Williams four-angle precession (SOFA iauPfw06)
# Capitaine et al. 2003, A&A 412, 567–586, Table 1.
# Coefficients in arcseconds.
# ---------------------------------------------------------------------------

def _fw_angles(T: float) -> tuple[float, float, float, float]:
    """
    Return (gamb, phib, psib, epsa) in radians for Julian centuries T from J2000.
    These are the Fukushima-Williams precession angles including the J2000 frame-bias
    constant terms (SOFA iauPfw06).
    """
    gamb = (  -0.052928
              + 10.556403  * T
              +  0.4932044 * T**2
              -  0.00031238* T**3
              -  0.000002788*T**4
              +  0.0000000260*T**5) * ARCSEC2RAD

    phib = (84381.412819
              - 46.811016  * T
              +  0.0511268 * T**2
              +  0.00053289* T**3
              -  0.000000440*T**4
              -  0.0000000176*T**5) * ARCSEC2RAD

    psib = (  -0.041775
              + 5038.481484* T
              +  1.5584175 * T**2
              -  0.00018522* T**3
              -  0.000026452*T**4
              -  0.0000000148*T**5) * ARCSEC2RAD

    epsa = mean_obliquity_p03(2451545.0 + T * 36525.0) * (math.pi / 180.0)

    return gamb, phib, psib, epsa


def _fw2m(gamb: float, phib: float, psib: float, epsa: float) -> tuple[tuple[float, ...], ...]:
    """
    Build the precession rotation matrix from the four Fukushima-Williams angles.
    Equivalent to SOFA eraFw2m.

    SOFA applies rotations as sequential LEFT-multiplications with passive matrices
    (same convention as Moira's rot_z_axis / rot_x_axis):

        r  = I
        r  = Rz(gamb)  · r
        r  = Rx(+phib) · r
        r  = Rz(-psi)  · r
        r  = Rx(-eps)  · r

    Final matrix: R1(−eps) · R3(−psi) · R1(+phib) · R3(gamb)
    (ERFA header formula: NxPxB = R_1(-eps) . R_3(-psi) . R_1(phib) . R_3(gamb))
    """
    from .coordinates import rot_x_axis, rot_z_axis, mat_mul
    return mat_mul(rot_x_axis(-epsa),
           mat_mul(rot_z_axis(-psib),
           mat_mul(rot_x_axis(phib),
                   rot_z_axis(gamb))))


def precession_matrix(jd_tt: float) -> tuple[tuple[float, ...], ...]:
    """
    IAU 2006 precession + frame-bias matrix (J2000.0 → Mean-of-Date).

    Uses the Fukushima-Williams parameterization (Capitaine et al. 2003).
    Equivalent to erfa.pmat06: includes the J2000.0 frame-bias (B×P),
    accurate to < 0.001″ from 500 BCE to 2100 CE.
    """
    T = centuries_from_j2000(jd_tt)
    gamb, phib, psib, epsa = _fw_angles(T)
    return _fw2m(gamb, phib, psib, epsa)
