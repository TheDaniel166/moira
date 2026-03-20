"""
Phase Engine — moira/phase.py

Archetype: Engine
Purpose: Computes the visual appearance of solar system bodies — phase angle,
         illuminated fraction, elongation from the Sun, angular diameter, and
         apparent visual magnitude — from raw ICRF barycentric vectors.

Boundary declaration:
    Owns: phase angle geometry (Sun-Planet-Earth triangle), illuminated
          fraction formula, great-circle elongation, angular diameter from
          physical radii, and the simplified apparent magnitude model.
    Delegates: raw barycentric position vectors to moira.planets._barycentric
               and moira.planets._earth_barycentric; geocentric planetary
               positions to moira.planets.planet_at; kernel I/O to
               moira.spk_reader.get_reader().

Import-time side effects: None

External dependency assumptions:
    - moira.planets._barycentric(body, jd, reader) returns a 3-tuple of
      ICRF barycentric coordinates in km.
    - moira.planets._earth_barycentric(jd, reader) returns the same for Earth.
    - moira.spk_reader.get_reader() is callable without arguments.
    - reader.position(0, 10, jd) returns the Sun's barycentric position in km.

Public surface / exports:
    phase_angle()          — Sun-Planet-Earth angle in degrees (0 = full, 180 = new)
    illuminated_fraction() — fraction of disk illuminated (0.0–1.0)
    elongation()           — angular separation from the Sun (degrees)
    angular_diameter()     — apparent angular diameter (arcseconds)
    apparent_magnitude()   — apparent visual magnitude (V band, simplified model)
"""

import math
from .constants import Body, NAIF
from .planets import planet_at

def phase_angle(body_name: str, jd_ut: float) -> float:
    """
    Calculate the phase angle (Sun-Planet-Earth angle) in degrees.
    β = 0 at full phase, β = 180 at new phase.
    """
    # 1. Heliocentric vector Planet-Sun (r_ps)
    # Actually, we have Geocentric Planet (r_pe) and Geocentric Sun (r_se).
    # Heliocentric Planet r_p = r_pe - r_se? No, r_pe + r_es = r_ps.
    # r_ps = Geocentric Planet - Geocentric Sun (vectors)
    from .spk_reader import get_reader
    reader = get_reader()
    
    # We need raw vectors in ICRF
    from .planets import _barycentric, _earth_barycentric
    p_bary = _barycentric(body_name, jd_ut, reader)
    s_bary = reader.position(0, 10, jd_ut)
    e_bary = _earth_barycentric(jd_ut, reader)
    
    # Heliocentric Planet (r_ps)
    r_ps = (p_bary[0] - s_bary[0], p_bary[1] - s_bary[1], p_bary[2] - s_bary[2])
    # Geocentric Planet (r_pe)
    r_pe = (p_bary[0] - e_bary[0], p_bary[1] - e_bary[1], p_bary[2] - e_bary[2])
    
    # Dot product for angle
    dot = r_ps[0]*r_pe[0] + r_ps[1]*r_pe[1] + r_ps[2]*r_pe[2]
    m_ps = math.sqrt(r_ps[0]**2 + r_ps[1]**2 + r_ps[2]**2)
    m_pe = math.sqrt(r_pe[0]**2 + r_pe[1]**2 + r_pe[2]**2)
    
    return math.degrees(math.acos(max(-1.0, min(1.0, dot / (m_ps * m_pe)))))

def illuminated_fraction(phase_ang: float) -> float:
    """k = (1 + cos(β)) / 2"""
    return (1.0 + math.cos(math.radians(phase_ang))) / 2.0

def elongation(body_name: str, jd_ut: float) -> float:
    """Angular separation from the Sun as seen from Earth (degrees)."""
    p = planet_at(body_name, jd_ut)
    s = planet_at(Body.SUN, jd_ut)
    
    # Great circle distance between (lon1, lat1) and (lon2, lat2)
    phi1, lam1 = math.radians(p.latitude), math.radians(p.longitude)
    phi2, lam2 = math.radians(s.latitude), math.radians(s.longitude)
    
    d = math.acos(math.sin(phi1)*math.sin(phi2) + 
                  math.cos(phi1)*math.cos(phi2)*math.cos(lam1 - lam2))
    return math.degrees(d)

# ---------------------------------------------------------------------------
# Angular diameter
# ---------------------------------------------------------------------------

# Physical radii (km) for angular diameter calculation
_PHYSICAL_RADII_KM: dict[str, float] = {
    "Sun":     695700.0,
    "Moon":      1737.4,
    "Mercury":   2439.7,
    "Venus":     6051.8,
    "Mars":      3389.5,
    "Jupiter":  71492.0,
    "Saturn":   60268.0,   # equatorial (rings excluded)
    "Uranus":   25559.0,
    "Neptune":  24764.0,
    "Pluto":     1188.3,
}


def angular_diameter(body_name: str, jd_ut: float) -> float:
    """
    Compute the apparent angular diameter of a solar system body (arcseconds).

    Angular diameter = 2 · arctan(R / Δ)
    where R is the physical radius and Δ is the geocentric distance.

    Parameters
    ----------
    body_name : planet name
    jd_ut     : Julian Day (UT)

    Returns
    -------
    Angular diameter in arcseconds. Returns 0.0 for unknown bodies.
    """
    if body_name not in _PHYSICAL_RADII_KM:
        return 0.0
    r_km = _PHYSICAL_RADII_KM[body_name]
    pos = planet_at(body_name, jd_ut)
    delta_km = pos.distance  # geocentric distance in km (already in PlanetData)
    if delta_km <= 0:
        return 0.0
    # arctan(R/Δ) in arcseconds
    return math.degrees(2.0 * math.atan(r_km / delta_km)) * 3600.0


def apparent_magnitude(body_name: str, jd_ut: float) -> float:
    """
    Calculate apparent magnitude (V) using standard planetary models.
    Ref: Seidelmann, Explanatory Supplement to the Astronomical Almanac.
    """
    # Absolute magnitude H and phase coefficients G (simplified)
    # Values at 1 AU from Sun and Earth
    m_data = {
        Body.MERCURY: (-0.42, 0.0380, 0.000273, 0.000002), # Multiple coefficients
        Body.VENUS:   (-4.40, 0.0009, 0.000239, 0.00000065),
        Body.MARS:    (-1.52, 0.016, 0.0, 0.0),
        Body.JUPITER: (-9.40, 0.005, 0.0, 0.0),
        Body.SATURN:  (-8.88, 0.044, 0.0, 0.0), # Complexity with rings
        Body.URANUS:  (-7.19, 0.002, 0.0, 0.0),
        Body.NEPTUNE: (-6.87, 0.0, 0.0, 0.0),
        Body.PLUTO:   (-1.0,  0.041, 0.0, 0.0)
    }
    
    if body_name not in m_data: return 0.0
    
    # Distances
    from .spk_reader import get_reader
    reader = get_reader()
    from .planets import _barycentric, _earth_barycentric
    p_bary = _barycentric(body_name, jd_ut, reader)
    s_bary = reader.position(0, 10, jd_ut)
    e_bary = _earth_barycentric(jd_ut, reader)
    
    r = math.sqrt((p_bary[0]-s_bary[0])**2 + (p_bary[1]-s_bary[1])**2 + (p_bary[2]-s_bary[2])**2) / 149597870.7
    delta = math.sqrt((p_bary[0]-e_bary[0])**2 + (p_bary[1]-e_bary[1])**2 + (p_bary[2]-e_bary[2])**2) / 149597870.7
    beta = phase_angle(body_name, jd_ut)
    
    H, a1, a2, a3 = m_data[body_name]
    
    # Basic formula: V = H + 5log10(r*delta) + phase_poly(beta)
    mag = H + 5 * math.log10(r * delta)
    
    if body_name == Body.VENUS:
        # Venus specific phase coefficients (Hilton)
        mag += 0.0009 * beta + 0.000239 * beta**2 - 0.00000065 * beta**3
    elif body_name == Body.MERCURY:
        mag += 0.0380 * beta - 0.000273 * beta**2 + 0.000002 * beta**3
    else:
        mag += a1 * beta
        
    return mag
