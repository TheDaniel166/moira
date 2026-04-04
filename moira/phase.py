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
    synodic_phase_angle()  — ecliptic phase angle for any body pair (0..360)
    synodic_phase_state()  — coarse synodic state label for a phase angle
    angular_diameter()     — apparent angular diameter (arcseconds)
    apparent_magnitude()   — apparent visual magnitude (V band, simplified model)
"""

import math
from .constants import Body, J2000, KM_PER_AU, SUN_RADIUS_KM, MOON_RADIUS_KM
from .planets import planet_at, _barycentric, _earth_barycentric
from .spk_reader import get_reader

__all__ = [
    "phase_angle",
    "illuminated_fraction",
    "elongation",
    "synodic_phase_angle",
    "synodic_phase_state",
    "angular_diameter",
    "apparent_magnitude",
]


def phase_angle(body_name: str, jd_ut: float) -> float:
    """
    Calculate the phase angle (Sun-Planet-Earth angle) in degrees.

    The phase angle β is the angle at the planet between the Sun and Earth.
    β = 0° → full phase (fully illuminated disk facing Earth).
    β = 180° → new phase (dark side facing Earth).

    Parameters
    ----------
    body_name : str
        The celestial body name (e.g., "Venus", Body.VENUS).
    jd_ut : float
        Julian Day in UT.

    Returns
    -------
    float
        Phase angle in degrees [0, 180].
    """
    reader = get_reader()
    p_bary = _barycentric(body_name, jd_ut, reader)
    s_bary = reader.position(0, 10, jd_ut)
    e_bary = _earth_barycentric(jd_ut, reader)

    # Heliocentric planet vector (Sun → Planet)
    r_ps = (p_bary[0] - s_bary[0], p_bary[1] - s_bary[1], p_bary[2] - s_bary[2])
    # Geocentric planet vector (Earth → Planet)
    r_pe = (p_bary[0] - e_bary[0], p_bary[1] - e_bary[1], p_bary[2] - e_bary[2])

    # Phase angle: cos(β) = (r_ps · r_pe) / (|r_ps| |r_pe|)
    dot = r_ps[0]*r_pe[0] + r_ps[1]*r_pe[1] + r_ps[2]*r_pe[2]
    m_ps = math.sqrt(r_ps[0]**2 + r_ps[1]**2 + r_ps[2]**2)
    m_pe = math.sqrt(r_pe[0]**2 + r_pe[1]**2 + r_pe[2]**2)

    if m_ps == 0 or m_pe == 0:
        return 0.0

    cos_beta = max(-1.0, min(1.0, dot / (m_ps * m_pe)))
    return math.degrees(math.acos(cos_beta))


def illuminated_fraction(phase_ang: float) -> float:
    """
    Compute the fraction of the illuminated disk visible from Earth.

    k = (1 + cos(β)) / 2

    Parameters
    ----------
    phase_ang : float
        Phase angle in degrees.

    Returns
    -------
    float
        Illuminated fraction in [0.0, 1.0].
    """
    return (1.0 + math.cos(math.radians(phase_ang))) / 2.0


def elongation(body_name: str, jd_ut: float) -> float:
    """
    Angular separation from the Sun as seen from Earth (degrees).

    This is a spherical-law-of-cosines great-circle distance computed from the
    apparent ecliptic longitudes and latitudes returned by ``planet_at()``.
    It is a two-dimensional approximation on the ecliptic sphere; the true
    three-dimensional Sun--Earth--Body angle may differ, typically by a small
    amount for major planets.

    Parameters
    ----------
    body_name : str
        The celestial body name.
    jd_ut : float
        Julian Day in UT.

    Returns
    -------
    float
        Angular separation in degrees [0, 180].
    """
    p = planet_at(body_name, jd_ut)
    s = planet_at(Body.SUN, jd_ut)

    # Spherical law of cosines
    phi1, lam1 = math.radians(p.latitude), math.radians(p.longitude)
    phi2, lam2 = math.radians(s.latitude), math.radians(s.longitude)

    cos_d = (math.sin(phi1)*math.sin(phi2) +
             math.cos(phi1)*math.cos(phi2)*math.cos(lam1 - lam2))
    return math.degrees(math.acos(max(-1.0, min(1.0, cos_d))))


def synodic_phase_angle(body1: str, body2: str, jd_ut: float) -> float:
    """
    Return the synodic phase angle from ``body1`` to ``body2`` in ecliptic longitude.

    The result is normalized to [0, 360), where 0 means conjunction,
    180 means opposition, and values in (0, 180) are waxing relative to body1.
    """
    p1 = planet_at(body1, jd_ut)
    p2 = planet_at(body2, jd_ut)
    return (p2.longitude - p1.longitude) % 360.0


def synodic_phase_state(angle_deg: float) -> str:
    """
    Classify a synodic phase angle into a coarse conventional label.

    The four quadrants are split at 45° boundaries around the cardinal
    points (0 = conjunction, 180 = opposition). These labels are a
    traditional astrological convention, not a physically fundamental
    partition.
    """
    a = angle_deg % 360.0
    if a < 45.0 or a >= 315.0:
        return "conjunction"
    if a < 135.0:
        return "waxing"
    if a < 225.0:
        return "opposition"
    return "waning"


# ---------------------------------------------------------------------------
# Angular diameter
# ---------------------------------------------------------------------------

# Physical radii (km) for angular diameter calculation.
# Sun and Moon values sourced from moira.constants for consistency with eclipse geometry.
_PHYSICAL_RADII_KM: dict[str, float] = {
    "Sun":     SUN_RADIUS_KM,
    "Moon":    MOON_RADIUS_KM,
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
    body_name : str
        The celestial body name.
    jd_ut : float
        Julian Day (UT).

    Returns
    -------
    float
        Angular diameter in arcseconds.

    Raises
    ------
    ValueError
        If the body has no radius entry in the engine's radius table.
    """
    if body_name not in _PHYSICAL_RADII_KM:
        raise ValueError(
            f"angular_diameter: no radius data for body {body_name!r}"
        )
    r_km = _PHYSICAL_RADII_KM[body_name]
    pos = planet_at(body_name, jd_ut)
    delta_km = pos.distance  # geocentric distance in km
    # Non-positive distance is physically degenerate; return 0.0 rather than
    # fail, so callers in batch pipelines can skip silently.
    if delta_km <= 0:
        return 0.0
    return math.degrees(2.0 * math.atan(r_km / delta_km)) * 3600.0


# ---------------------------------------------------------------------------
# Apparent magnitude
# ---------------------------------------------------------------------------

# Body-specific magnitude models following Mallama & Hilton (2018)
# "Computing Apparent Planetary Magnitudes for The Astronomical Almanac"
# and the associated Astronomical Almanac treatments.
#
# The Moon is admitted separately using the approximate apparent-magnitude
# phase law published by B.E. Schaefer (1993), with explicit distance terms.
#
# Limitations explicitly documented:
#   - Moon:    no opposition surge or eclipse darkening correction.
#   - Saturn:  globe-only model; ring tilt/brightness not included.
#   - Pluto:   intentionally unsupported in the current photometric
#              engine; adding Pluto would imply a broader admission
#              policy for dwarf planets and related minor bodies.

_SUPPORTED_BODIES = frozenset(
    [Body.MOON, Body.MERCURY, Body.VENUS, Body.MARS, Body.JUPITER,
     Body.SATURN, Body.URANUS, Body.NEPTUNE])

_SATURN_RING_PHASE_LIMIT_DEG = 6.5
_SATURN_RING_INCLINATION_LIMIT_DEG = 27.0
_SATURN_POLE_RA0_DEG = 40.589
_SATURN_POLE_RA_RATE_DEG_PER_CY = -0.036
_SATURN_POLE_DEC0_DEG = 83.537
_SATURN_POLE_DEC_RATE_DEG_PER_CY = -0.004
_NEPTUNE_GEOCENTRIC_PHASE_LIMIT_DEG = 1.9
_URANUS_GEOCENTRIC_PHASE_LIMIT_DEG = 3.1
_URANUS_POLE_RA_DEG = 257.311
_URANUS_POLE_DEC_DEG = -15.175
_URANUS_EQUATORIAL_RADIUS_KM = 25559.0
_URANUS_POLAR_RADIUS_KM = 24973.0
_MARS_PHASE_LIMIT_DEG = 50.0
_MARS_LS_OFFSET_DEG = -85.0
_MARS_POLE_RA0_DEG = 317.269202
_MARS_POLE_RA_RATE_DEG_PER_CY = -0.10927547
_MARS_POLE_DEC0_DEG = 54.432516
_MARS_POLE_DEC_RATE_DEG_PER_CY = -0.05827105
_MARS_PM0_DEG = 176.049863
_MARS_PM_RATE_DEG_PER_DAY = 350.891982443297
_MARS_NUT_PREC_RA = (
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    6.8e-05, 2.38e-04, 5.2e-05, 9.0e-06, 0.419057,
)
_MARS_NUT_PREC_DEC = (
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0, 0.0, 5.1e-05, 1.41e-04, 3.1e-05, 5.0e-06, 1.591274,
)
_MARS_NUT_PREC_PM = (
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
    1.45e-04, 1.57e-04, 4.0e-05, 1.0e-06, 1.0e-06, 0.584542,
)
_MARS_NUT_PREC_ANGLES = (
    (190.72646643, 15917.10818695, 0.0),
    (21.46892470, 31834.27934054, 0.0),
    (332.86082793, 19139.89694742, 0.0),
    (394.93256437, 38280.79631835, 0.0),
    (189.63271560, 41215158.18420050, 12.711923222),
    (121.46893664, 660.22803474, 0.0),
    (231.05028581, 660.99123540, 0.0),
    (251.37314025, 1320.50145245, 0.0),
    (217.98635955, 38279.96125550, 0.0),
    (196.19729402, 19139.83628608, 0.0),
    (198.99122600, 19139.48199850, 0.0),
    (226.29267900, 38280.85112810, 0.0),
    (249.66339100, 57420.72515930, 0.0),
    (266.18351000, 76560.63679500, 0.0),
    (79.39879700, 0.50426150, 0.0),
    (122.43357600, 19139.94074760, 0.0),
    (43.05840100, 38280.87532720, 0.0),
    (57.66337900, 57420.75172050, 0.0),
    (79.47640100, 76560.64950040, 0.0),
    (166.32572200, 0.50426150, 0.0),
    (129.07177300, 19140.03282440, 0.0),
    (36.35216700, 38281.04735910, 0.0),
    (56.66864600, 57420.92953600, 0.0),
    (67.36400300, 76560.25522150, 0.0),
    (104.79268000, 95700.43875780, 0.0),
    (95.39165400, 0.50426150, 0.0),
)
_MARS_ROTATION_MAG_CORR = (
    0.024, 0.034, 0.036, 0.045, 0.038, 0.023, 0.015, 0.011,
    0.000, -0.012, -0.018, -0.036, -0.044, -0.059, -0.060, -0.055,
    -0.043, -0.041, -0.041, -0.036, -0.036, -0.018, -0.038, -0.011,
    0.002, 0.004, 0.018, 0.019, 0.035, 0.050, 0.035, 0.027,
    0.037, 0.048, 0.025, 0.022, 0.024, 0.034, 0.036, 0.045,
)
_MARS_ORBIT_MAG_CORR = (
    -0.030, -0.017, -0.029, -0.017, -0.014, -0.006, -0.018, -0.020,
    -0.014, -0.030, -0.008, -0.040, -0.024, -0.037, -0.036, -0.032,
    0.010, 0.010, -0.001, 0.044, 0.025, -0.004, -0.016, -0.008,
    0.029, -0.054, -0.033, 0.055, 0.017, 0.052, 0.006, 0.087,
    0.006, 0.064, 0.030, 0.019, -0.030, -0.017, -0.029, -0.017,
)


def _saturn_pole_unit(jd_ut: float) -> tuple[float, float, float]:
    centuries = (jd_ut - J2000) / 36525.0
    ra = math.radians(_SATURN_POLE_RA0_DEG + _SATURN_POLE_RA_RATE_DEG_PER_CY * centuries)
    dec = math.radians(_SATURN_POLE_DEC0_DEG + _SATURN_POLE_DEC_RATE_DEG_PER_CY * centuries)
    cos_dec = math.cos(dec)
    return (
        cos_dec * math.cos(ra),
        cos_dec * math.sin(ra),
        math.sin(dec),
    )


def _saturn_effective_sub_lat_geoc(
    p_bary: tuple[float, float, float],
    s_bary: tuple[float, float, float],
    e_bary: tuple[float, float, float],
    jd_ut: float,
) -> float:
    pole = _saturn_pole_unit(jd_ut)

    sx = s_bary[0] - p_bary[0]
    sy = s_bary[1] - p_bary[1]
    sz = s_bary[2] - p_bary[2]
    ex = e_bary[0] - p_bary[0]
    ey = e_bary[1] - p_bary[1]
    ez = e_bary[2] - p_bary[2]

    sm = math.sqrt(sx*sx + sy*sy + sz*sz)
    em = math.sqrt(ex*ex + ey*ey + ez*ez)
    if sm == 0.0 or em == 0.0:
        return 0.0

    sun_lat = math.degrees(math.asin(max(-1.0, min(1.0, (pole[0]*sx + pole[1]*sy + pole[2]*sz) / sm))))
    earth_lat = math.degrees(math.asin(max(-1.0, min(1.0, (pole[0]*ex + pole[1]*ey + pole[2]*ez) / em))))

    lat_product = sun_lat * earth_lat
    if lat_product <= 0.0:
        return 0.0
    return math.sqrt(lat_product)


def _uranus_pole_unit() -> tuple[float, float, float]:
    ra = math.radians(_URANUS_POLE_RA_DEG)
    dec = math.radians(_URANUS_POLE_DEC_DEG)
    cos_dec = math.cos(dec)
    return (
        cos_dec * math.cos(ra),
        cos_dec * math.sin(ra),
        math.sin(dec),
    )


def _uranus_planetographic_latitude(direction: tuple[float, float, float]) -> float:
    pole = _uranus_pole_unit()
    magnitude = math.sqrt(direction[0] * direction[0] + direction[1] * direction[1] + direction[2] * direction[2])
    if magnitude == 0.0:
        return 0.0

    planetocentric_lat = math.asin(
        max(-1.0, min(1.0, (pole[0] * direction[0] + pole[1] * direction[1] + pole[2] * direction[2]) / magnitude))
    )
    axis_ratio_sq = (_URANUS_POLAR_RADIUS_KM / _URANUS_EQUATORIAL_RADIUS_KM) ** 2
    return math.degrees(math.atan(math.tan(planetocentric_lat) / axis_ratio_sq))


def _uranus_effective_sub_lat_planetog(
    p_bary: tuple[float, float, float],
    s_bary: tuple[float, float, float],
    e_bary: tuple[float, float, float],
) -> float:
    sun_lat = _uranus_planetographic_latitude((s_bary[0] - p_bary[0], s_bary[1] - p_bary[1], s_bary[2] - p_bary[2]))
    earth_lat = _uranus_planetographic_latitude((e_bary[0] - p_bary[0], e_bary[1] - p_bary[1], e_bary[2] - p_bary[2]))
    return (abs(sun_lat) + abs(earth_lat)) / 2.0


def _mars_stirling_correction(table: tuple[float, ...], angle_deg: float) -> float:
    angle = angle_deg % 360.0
    zero_point = int(angle / 10.0)
    p1 = angle / 10.0 - zero_point

    delta = [table[zero_point + i + 1] - table[zero_point + i] for i in range(4)]
    delta_2 = [delta[i + 1] - delta[i] for i in range(3)]
    delta_3 = [delta_2[i + 1] - delta_2[i] for i in range(2)]
    delta_4 = delta_3[1] - delta_3[0]

    a0 = table[zero_point + 2]
    a4 = delta_4 / 24.0
    a3 = (delta_3[0] + delta_3[1]) / 12.0
    a2 = delta_2[1] / 2.0 - a4
    a1 = (delta[1] + delta[2]) / 2.0 - a3

    return a0 + a1 * p1 + a2 * p1**2 + a3 * p1**3 + a4 * p1**4


def _mars_rotation_r1(angle_rad: float) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    cos_angle = math.cos(angle_rad)
    sin_angle = math.sin(angle_rad)
    return (
        (1.0, 0.0, 0.0),
        (0.0, cos_angle, sin_angle),
        (0.0, -sin_angle, cos_angle),
    )


def _mars_rotation_r3(angle_rad: float) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    cos_angle = math.cos(angle_rad)
    sin_angle = math.sin(angle_rad)
    return (
        (cos_angle, sin_angle, 0.0),
        (-sin_angle, cos_angle, 0.0),
        (0.0, 0.0, 1.0),
    )


def _mars_matmul(
    left: tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]],
    right: tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]],
) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    return (
        (
            left[0][0] * right[0][0] + left[0][1] * right[1][0] + left[0][2] * right[2][0],
            left[0][0] * right[0][1] + left[0][1] * right[1][1] + left[0][2] * right[2][1],
            left[0][0] * right[0][2] + left[0][1] * right[1][2] + left[0][2] * right[2][2],
        ),
        (
            left[1][0] * right[0][0] + left[1][1] * right[1][0] + left[1][2] * right[2][0],
            left[1][0] * right[0][1] + left[1][1] * right[1][1] + left[1][2] * right[2][1],
            left[1][0] * right[0][2] + left[1][1] * right[1][2] + left[1][2] * right[2][2],
        ),
        (
            left[2][0] * right[0][0] + left[2][1] * right[1][0] + left[2][2] * right[2][0],
            left[2][0] * right[0][1] + left[2][1] * right[1][1] + left[2][2] * right[2][1],
            left[2][0] * right[0][2] + left[2][1] * right[1][2] + left[2][2] * right[2][2],
        ),
    )


def _mars_matvec(
    matrix: tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]],
    vector: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (
        matrix[0][0] * vector[0] + matrix[0][1] * vector[1] + matrix[0][2] * vector[2],
        matrix[1][0] * vector[0] + matrix[1][1] * vector[1] + matrix[1][2] * vector[2],
        matrix[2][0] * vector[0] + matrix[2][1] * vector[1] + matrix[2][2] * vector[2],
    )


def _mars_nutation_precession_angles(centuries: float) -> tuple[float, ...]:
    return tuple(
        (constant + linear * centuries + quadratic * centuries * centuries) % 360.0
        for constant, linear, quadratic in _MARS_NUT_PREC_ANGLES
    )


def _mars_trig_sum(coefficients: tuple[float, ...], angles_deg: tuple[float, ...], *, use_cosine: bool) -> float:
    trig = math.cos if use_cosine else math.sin
    return sum(
        coefficient * trig(math.radians(angle_deg))
        for coefficient, angle_deg in zip(coefficients, angles_deg)
    )


def _mars_orientation_angles(jd_tt: float) -> tuple[float, float, float]:
    centuries = (jd_tt - J2000) / 36525.0
    days = jd_tt - J2000
    nut_prec_angles = _mars_nutation_precession_angles(centuries)

    ra = (
        _MARS_POLE_RA0_DEG
        + _MARS_POLE_RA_RATE_DEG_PER_CY * centuries
        + _mars_trig_sum(_MARS_NUT_PREC_RA, nut_prec_angles, use_cosine=False)
    )
    dec = (
        _MARS_POLE_DEC0_DEG
        + _MARS_POLE_DEC_RATE_DEG_PER_CY * centuries
        + _mars_trig_sum(_MARS_NUT_PREC_DEC, nut_prec_angles, use_cosine=True)
    )
    w = (
        _MARS_PM0_DEG
        + _MARS_PM_RATE_DEG_PER_DAY * days
        + _mars_trig_sum(_MARS_NUT_PREC_PM, nut_prec_angles, use_cosine=False)
    ) % 360.0
    return ra, dec, w


def _mars_body_axes(jd_tt: float) -> tuple[tuple[float, float, float], tuple[float, float, float], tuple[float, float, float]]:
    ra_deg, dec_deg, w_deg = _mars_orientation_angles(jd_tt)
    frame = _mars_matmul(
        _mars_rotation_r3(math.radians(w_deg)),
        _mars_matmul(
            _mars_rotation_r1(math.radians(90.0 - dec_deg)),
            _mars_rotation_r3(math.radians(ra_deg + 90.0)),
        ),
    )
    return (
        (frame[0][0], frame[1][0], frame[2][0]),
        (frame[0][1], frame[1][1], frame[2][1]),
        (frame[0][2], frame[1][2], frame[2][2]),
    )


def _mars_sub_longitude(
    body_to_target: tuple[float, float, float],
    jd_tt: float,
) -> float:
    ra_deg, dec_deg, w_deg = _mars_orientation_angles(jd_tt)
    frame = _mars_matmul(
        _mars_rotation_r3(math.radians(w_deg)),
        _mars_matmul(
            _mars_rotation_r1(math.radians(90.0 - dec_deg)),
            _mars_rotation_r3(math.radians(ra_deg + 90.0)),
        ),
    )
    tm = math.sqrt(
        body_to_target[0] * body_to_target[0]
        + body_to_target[1] * body_to_target[1]
        + body_to_target[2] * body_to_target[2]
    )
    if tm == 0.0:
        return 0.0
    body_fixed = _mars_matvec(
        frame,
        (body_to_target[0] / tm, body_to_target[1] / tm, body_to_target[2] / tm),
    )
    return math.degrees(math.atan2(-body_fixed[1], body_fixed[0])) % 360.0


def _mars_magnitude_context(
    h_vec: tuple[float, float, float],
    earth_vec: tuple[float, float, float],
    sun_vec: tuple[float, float, float],
    jd_ut: float,
) -> tuple[float, float]:
    from .coordinates import icrf_to_true_ecliptic
    from .julian import decimal_year_from_jd, tt_to_tdb, ut_to_tt

    jd_tt = ut_to_tt(jd_ut, decimal_year_from_jd(jd_ut))
    jd_tdb = tt_to_tdb(jd_tt)
    sub_earth_long = _mars_sub_longitude((-earth_vec[0], -earth_vec[1], -earth_vec[2]), jd_tdb)
    sub_sun_long = _mars_sub_longitude(sun_vec, jd_tdb)
    eff_cm = (sub_earth_long + sub_sun_long) / 2.0
    if abs(sub_earth_long - sub_sun_long) > 180.0:
        eff_cm += 180.0
    if eff_cm > 360.0:
        eff_cm -= 360.0

    h_ecl_long, _lat, _dist = icrf_to_true_ecliptic(jd_tt, h_vec)
    mars_ls = (h_ecl_long + _MARS_LS_OFFSET_DEG) % 360.0
    return eff_cm, mars_ls

# -----------------------------------------------------------------------
# Mercury: geocentric modern phase polynomial from Hilton (2005) as adopted
# by Mallama & Hilton (2018).
# -----------------------------------------------------------------------
def _mag_mercury(
    r: float,
    delta: float,
    beta: float,
    _jd_ut: float | None = None,
    _saturn_sub_lat_geoc: float | None = None,
) -> float:
    mag = 5.0 * math.log10(r * delta)
    mag += (-0.613
            + 6.3280e-02 * beta
            - 1.6336e-03 * beta**2
            + 3.3644e-05 * beta**3
            - 3.4265e-07 * beta**4
            + 1.6893e-09 * beta**5
            - 3.0334e-12 * beta**6)
    return mag

# -----------------------------------------------------------------------
# Venus: piecewise modern geocentric treatment.
# The large-crescent branch begins at β >= 163.7 degrees.
# -----------------------------------------------------------------------
def _mag_venus(
    r: float,
    delta: float,
    beta: float,
    _jd_ut: float | None = None,
    _saturn_sub_lat_geoc: float | None = None,
) -> float:
    mag = 5.0 * math.log10(r * delta)
    if beta < 163.7:
        mag += (-4.384
                - 1.044e-03 * beta
                + 3.687e-04 * beta**2
                - 2.814e-06 * beta**3
                + 8.938e-09 * beta**4)
    else:
        mag += (236.05828
                - 2.81914 * beta
                + 8.39034e-03 * beta**2)
    return mag

# -----------------------------------------------------------------------
# Mars: geocentric modern treatment with rotational and orbital brightness
# corrections using the published periodic Mars orientation series.
# -----------------------------------------------------------------------
def _mag_mars(
    r: float,
    delta: float,
    beta: float,
    _jd_ut: float | None = None,
    _saturn_sub_lat_geoc: float | None = None,
    mars_eff_cm: float | None = None,
    mars_ls: float | None = None,
) -> float:
    mag = 5.0 * math.log10(r * delta)
    if beta <= _MARS_PHASE_LIMIT_DEG:
        mag += (-1.601
                + 2.267e-02 * beta
                - 1.302e-04 * beta**2)
    else:
        mag += (-0.367
                - 0.02573 * beta
                + 0.0003445 * beta**2)
    if mars_eff_cm is not None:
        mag += _mars_stirling_correction(_MARS_ROTATION_MAG_CORR, mars_eff_cm)
    if mars_ls is not None:
        mag += _mars_stirling_correction(_MARS_ORBIT_MAG_CORR, mars_ls)
    return mag

# -----------------------------------------------------------------------
# Jupiter: geocentric small-phase-angle treatment.
# Earth-based phase angles remain within the modern low-phase polynomial regime.
# -----------------------------------------------------------------------
def _mag_jupiter(
    r: float,
    delta: float,
    beta: float,
    _jd_ut: float | None = None,
    _saturn_sub_lat_geoc: float | None = None,
) -> float:
    mag = 5.0 * math.log10(r * delta)
    mag += (-9.395
            - 3.7e-04 * beta
            + 6.16e-04 * beta**2)
    return mag

# -----------------------------------------------------------------------
# Saturn: geocentric globe+rings treatment when the effective ring sub-latitude
# is available and within the published validity range; otherwise globe-only.
# -----------------------------------------------------------------------
def _mag_saturn(
    r: float,
    delta: float,
    beta: float,
    _jd_ut: float | None = None,
    saturn_sub_lat_geoc: float | None = None,
) -> float:
    mag = 5.0 * math.log10(r * delta)
    if (saturn_sub_lat_geoc is not None
            and beta <= _SATURN_RING_PHASE_LIMIT_DEG
            and saturn_sub_lat_geoc <= _SATURN_RING_INCLINATION_LIMIT_DEG):
        sin_sub_lat = math.sin(math.radians(saturn_sub_lat_geoc))
        mag += (-8.914
                - 1.825 * sin_sub_lat
                + 0.026 * beta
                - 0.378 * sin_sub_lat * math.exp(-2.25 * beta))
    elif beta <= _SATURN_RING_PHASE_LIMIT_DEG:
        mag += (-8.95
                - 3.7e-04 * beta
                + 6.16e-04 * beta**2)
    else:
        mag += (-8.94
                + 2.446e-04 * beta
                + 2.672e-04 * beta**2
                - 1.506e-06 * beta**3
                + 4.767e-09 * beta**4)
    return mag

# -----------------------------------------------------------------------
# Uranus: geocentric modern treatment with the effective planetographic
# sub-latitude term, plus the supplementary beyond-geocentric phase branch.
# -----------------------------------------------------------------------
def _mag_uranus(
    r: float,
    delta: float,
    beta: float,
    _jd_ut: float | None = None,
    _saturn_sub_lat_geoc: float | None = None,
    uranus_sub_lat_planetog: float | None = None,
) -> float:
    mag = 5.0 * math.log10(r * delta)
    sub_lat_factor = 0.0
    if uranus_sub_lat_planetog is not None:
        sub_lat_factor = -8.4e-04 * uranus_sub_lat_planetog
    mag += -7.110 + sub_lat_factor
    if beta > _URANUS_GEOCENTRIC_PHASE_LIMIT_DEG:
        mag += 6.587e-03 * beta + 1.045e-04 * beta**2
    return mag

# -----------------------------------------------------------------------
# Neptune: geocentric modern V(1,0) with the published secular term plus the
# supplementary large-phase branch for post-2000 epochs.
# -----------------------------------------------------------------------
def _mag_neptune(
    r: float,
    delta: float,
    beta: float,
    jd_ut: float | None = None,
    _saturn_sub_lat_geoc: float | None = None,
) -> float:
    mag = 5.0 * math.log10(r * delta)
    if jd_ut is None:
        mag += -7.00
        return mag
    from .julian import decimal_year_from_jd
    year = decimal_year_from_jd(jd_ut)
    if year > 2000.0:
        mag += -7.00
    elif year < 1980.0:
        mag += -6.89
    else:
        mag += -6.89 - 0.0054 * (year - 1980.0)
    if year > 2000.0 and beta > _NEPTUNE_GEOCENTRIC_PHASE_LIMIT_DEG:
        mag += 7.944e-03 * beta + 9.617e-05 * beta**2
    return mag


def _mag_moon(
    r: float,
    delta: float,
    beta: float,
    _jd_ut: float | None = None,
    _saturn_sub_lat_geoc: float | None = None,
) -> float:
    """
    Approximate apparent V magnitude of the Moon.

    Source lineage:
        B.E. Schaefer, "Astronomy and the Limits of Vision",
        Vistas in Astronomy 36 (1993), 311-361.
    """
    delta_km = delta * KM_PER_AU
    if delta_km <= 0.0 or r <= 0.0:
        return 0.0
    return (
        -12.73
        + 0.026 * beta
        + 4.0e-9 * beta**4
        + 5.0 * math.log10((delta_km / 384400.0) * r)
    )

# Dispatch table: body name → body-specific magnitude function.
_BODY_MAG: dict[str, callable] = {
    Body.MOON:    _mag_moon,
    Body.MERCURY: _mag_mercury,
    Body.VENUS:   _mag_venus,
    Body.MARS:    _mag_mars,
    Body.JUPITER: _mag_jupiter,
    Body.SATURN:  _mag_saturn,
    Body.URANUS:  _mag_uranus,
    Body.NEPTUNE: _mag_neptune,
}


def apparent_magnitude(body_name: str, jd_ut: float) -> float:
    """
    Calculate apparent visual magnitude (V band).

    For the planets, this uses the admitted modern planetary magnitude models
    following Mallama & Hilton (2018) and the associated Astronomical Almanac
    treatments. For the Moon, this uses the admitted Schaefer (1993)
    approximate phase law.

    Parameters
    ----------
    body_name : str
        The celestial body (Body.* constant or string name).
    jd_ut : float
        Julian Day in UT.

    Returns
    -------
    float
        Apparent visual magnitude.

    Raises
    ------
    ValueError
        If the body is unsupported (unknown body, or photometric model
        not yet implemented to modern standard).

    Notes
    -----
        - Moon: Schaefer (1993) approximate law; opposition surge and eclipse
            darkening are not modeled.
        - Saturn: ring model is used for geocentric conditions within the
            published validity range; otherwise a globe-only fallback is used.
    - Mars: rotational/orbital terms use the published periodic IAU/NAIF orientation model.
    - Uranus: effective planetographic sub-latitude term is included.
    - Neptune: time-dependent geocentric V(1,0) plus the published post-2000 supplementary phase branch.
        - Pluto: intentionally unsupported in the current photometric
            engine; adding Pluto would imply a broader admission policy for
            dwarf planets and related minor bodies.
    """
    if body_name not in _BODY_MAG:
        raise ValueError(
            f"apparent_magnitude: no modern magnitude model for body {body_name!r}"
        )

    reader = get_reader()
    p_bary = _barycentric(body_name, jd_ut, reader)
    s_bary = reader.position(0, 10, jd_ut)
    e_bary = _earth_barycentric(jd_ut, reader)

    # Heliocentric distance vector (Sun → Planet)
    hx = p_bary[0] - s_bary[0]
    hy = p_bary[1] - s_bary[1]
    hz = p_bary[2] - s_bary[2]
    r = math.sqrt(hx*hx + hy*hy + hz*hz) / KM_PER_AU

    # Geocentric distance vector (Earth → Planet)
    gx = p_bary[0] - e_bary[0]
    gy = p_bary[1] - e_bary[1]
    gz = p_bary[2] - e_bary[2]
    delta = math.sqrt(gx*gx + gy*gy + gz*gz) / KM_PER_AU

    # Non-positive distances are physically degenerate; skip silently.
    if r <= 0 or delta <= 0:
        return 0.0

    # Phase angle from already-fetched vectors to avoid a second SPK lookup.
    # cos(β) = (heliocentric · geocentric) / (|h| |g|)
    dot = hx*gx + hy*gy + hz*gz
    hm = r * KM_PER_AU
    gm = delta * KM_PER_AU
    cos_beta = max(-1.0, min(1.0, dot / (hm * gm)))
    beta = math.degrees(math.acos(cos_beta))

    saturn_sub_lat_geoc = None
    if body_name == Body.SATURN:
        saturn_sub_lat_geoc = _saturn_effective_sub_lat_geoc(p_bary, s_bary, e_bary, jd_ut)
        return _BODY_MAG[body_name](r, delta, beta, jd_ut, saturn_sub_lat_geoc)

    if body_name == Body.MARS:
        mars_eff_cm, mars_ls = _mars_magnitude_context(
            (hx, hy, hz),
            (gx, gy, gz),
            (s_bary[0] - p_bary[0], s_bary[1] - p_bary[1], s_bary[2] - p_bary[2]),
            jd_ut,
        )
        return _mag_mars(r, delta, beta, jd_ut, None, mars_eff_cm, mars_ls)

    if body_name == Body.URANUS:
        uranus_sub_lat_planetog = _uranus_effective_sub_lat_planetog(p_bary, s_bary, e_bary)
        return _mag_uranus(r, delta, beta, jd_ut, None, uranus_sub_lat_planetog)

    return _BODY_MAG[body_name](r, delta, beta, jd_ut)
