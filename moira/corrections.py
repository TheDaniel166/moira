"""
Moira — Astrometric Corrections Engine
Archetype: Engine

Purpose:
    Governs the application of astrometric corrections that transform geometric
    positions into apparent positions as seen by a real observer. Provides the
    four canonical correction stages: light-time, annual aberration, gravitational
    deflection, frame bias, and topocentric parallax.

Boundary:
    Owns: light-time iteration, relativistic aberration, gravitational deflection
          (multi-body: Sun + Jupiter + Saturn + Earth via IAU SOFA LDBODY),
          IAU 2006 frame bias rotation, and WGS-84 topocentric parallax shift.
    Delegates: SPK kernel reads (via caller-supplied barycentric_fn and SpkReader),
               coordinate type definitions (moira.coordinates), and physical
               constants (moira.constants).

Import-time side effects: None

External dependency assumptions:
    - Caller supplies a SpkReader instance and a barycentric position function;
      this Engine imposes no direct I/O.
    - Physical constants (speed of light, Earth radius) are sourced from
      moira.constants and moira.coordinates.
    - All vectors are ICRF rectangular (km) unless otherwise stated.

Public surface / exports:
    apply_light_time(body, jd_tt, reader, earth_ssb, barycentric_fn)
        -> tuple[Vec3, float]
    apply_aberration(xyz, earth_velocity_xyz) -> Vec3
    SCHWARZSCHILD_RADII         — dict of body name → R_s = 2GM/c² (km)
    apply_deflection(xyz_body, deflectors) -> Vec3
    apply_frame_bias(xyz) -> Vec3
    topocentric_correction(xyz_geocentric, latitude_deg, longitude_deg,
                           lst_deg, elevation_m) -> Vec3
    apply_refraction(altitude_deg, *, pressure_mbar, temperature_c) -> float
"""

import math
from .constants import DEG2RAD, RAD2DEG, ARCSEC2RAD

try:
    import numpy as _np
    _HAS_NUMPY = True
except ImportError:
    _np = None
    _HAS_NUMPY = False
from .coordinates import (
    Vec3, vec_sub, vec_norm, vec_scale, vec_add,
    atmospheric_refraction as _atmospheric_refraction,
    atmospheric_refraction_extended as _atmospheric_refraction_extended,
)

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------

C_KM_PER_DAY = 299_792.458 * 86_400.0   # speed of light in km/day
EARTH_RADIUS_KM = 6_378.137              # equatorial Earth radius, km

# Schwarzschild radii R_s = 2GM/c² (km) for gravitational deflection.
# Sun: ~1.75" at the limb; Jupiter: ~16 µas peak; Saturn: ~6 µas; Earth: negligible.
# Source: IERS TN 36 / IAU SOFA LDBODY constants.
SCHWARZSCHILD_RADII: dict[str, float] = {
    "Sun":     2.95325008,  # km
    "Jupiter": 0.00282,     # km  (2 × 1.26687e8 km³/s² / c²)
    "Saturn":  0.000838,    # km  (2 × 3.79312e7 km³/s² / c²)
    "Earth":   8.87e-6,     # km  (2 × 3.98600e5 km³/s² / c²)
}

# ---------------------------------------------------------------------------
# Frame bias constants (IAU 2006, Capitaine et al.)
# Bias from ICRF to dynamical mean ecliptic and equinox of J2000.0
# These are tiny rotations — applied once, fixed.
# ---------------------------------------------------------------------------

# Frame bias parameters (milliarcseconds - mas)
# Values from IAU 2006 / IERS Conventions 2010
_dA_mas  = -14.6
_xi0_mas = -16.6170
_de0_mas =  -6.8192

# Convert mas to radians (1 mas = 1/3,600,000 degrees)
_dA_r  = (_dA_mas  / 1000.0) * ARCSEC2RAD
_xi0_r = (_xi0_mas / 1000.0) * ARCSEC2RAD
_de0_r = (_de0_mas / 1000.0) * ARCSEC2RAD

# Pre-built rotation matrix for apply_frame_bias — constructed once at import.
# Only materialised when NumPy is available; pure-Python path uses scalars above.
if _HAS_NUMPY:
    _FRAME_BIAS_MATRIX = _np.array([
        [ 1.0,    -_de0_r,  _xi0_r],
        [ _de0_r,  1.0,    -_dA_r ],
        [-_xi0_r,  _dA_r,   1.0   ],
    ], dtype=_np.float64)
else:
    _FRAME_BIAS_MATRIX = None


# ---------------------------------------------------------------------------
# 1. Light-time correction
# ---------------------------------------------------------------------------

def apply_light_time(
    body: str,
    jd_tt: float,
    reader,   # SpkReader
    earth_ssb: Vec3,
    barycentric_fn, # callable(body, jd_tt, reader) -> Vec3
) -> tuple[Vec3, float]:
    """
    Correct a geocentric position vector for light travel time.

    Calculates: Barycentric Body(t - lt) - Barycentric Earth(t).
    One iteration is sufficient for all planets.

    Parameters
    ----------
    body           : Body.* constant
    jd_tt          : current Julian Day (TT) at observer
    reader         : SpkReader instance
    earth_ssb      : Barycentric position of Earth at jd_tt (km)
    barycentric_fn : function returning SSB position of body

    Returns
    -------
    (corrected_xyz, light_time_days)
    """
    # Initial estimate: light-time from body position at t
    pos_body = barycentric_fn(body, jd_tt, reader)
    lt = vec_norm(vec_sub(pos_body, earth_ssb)) / C_KM_PER_DAY

    # Iterate to convergence: planet position at t − lt feeds back into lt.
    # Converges in ≤3 steps for all solar-system bodies; cap at 10 for safety.
    # Tolerance is 1 ns in light-time (1e-14 days ≈ 0.3 mm positional error).
    _LT_TOL = 1e-14  # days
    xyz_geocentric_lt = vec_sub(pos_body, earth_ssb)
    for _ in range(10):
        pos_body_lt       = barycentric_fn(body, jd_tt - lt, reader)
        xyz_geocentric_lt = vec_sub(pos_body_lt, earth_ssb)
        lt_new            = vec_norm(xyz_geocentric_lt) / C_KM_PER_DAY
        if abs(lt_new - lt) < _LT_TOL:
            lt = lt_new
            break
        lt = lt_new

    return xyz_geocentric_lt, lt


# ---------------------------------------------------------------------------
# 2. Annual aberration
# ---------------------------------------------------------------------------

def apply_aberration(
    xyz: Vec3,
    earth_velocity_xyz: Vec3,   # Earth velocity in km/day (ICRF)
) -> Vec3:
    """
    Apply annual aberration correction to a geocentric ICRF position vector.

    Uses the relativistic formula (IAU SOFA / IERS Conventions).

    Parameters
    ----------
    xyz                : geocentric ICRF position of body (km)
    earth_velocity_xyz : Earth's velocity vector (km/day, ICRF)

    Returns
    -------
    Aberration-corrected position vector (same unit as input)
    """
    dist = vec_norm(xyz)
    if dist < 1e-10:
        return xyz

    if _HAS_NUMPY:
        u   = _np.asarray(xyz,               dtype=_np.float64)
        vel = _np.asarray(earth_velocity_xyz, dtype=_np.float64)
        u   = u / dist
        b   = vel / C_KM_PER_DAY
        beta2 = _np.dot(b, b)
        gamma = 1.0 / math.sqrt(1.0 - float(beta2))
        dot   = float(_np.dot(u, b))
        f1 = 1.0 + dot / (1.0 + gamma)
        f2 = gamma * (1.0 + dot)
        a  = (u + f1 * b) / f2
        scale = dist / float(_np.linalg.norm(a))
        r = a * scale
        return (float(r[0]), float(r[1]), float(r[2]))

    # Unit direction to body (u)
    ux, uy, uz = xyz[0] / dist, xyz[1] / dist, xyz[2] / dist

    # Velocity as fraction of c (beta)
    bx = earth_velocity_xyz[0] / C_KM_PER_DAY
    by = earth_velocity_xyz[1] / C_KM_PER_DAY
    bz = earth_velocity_xyz[2] / C_KM_PER_DAY

    # Lorentz factor: gamma = 1 / sqrt(1 - beta^2)
    beta2 = bx*bx + by*by + bz*bz
    gamma = 1.0 / math.sqrt(1.0 - beta2)

    # Dot product u·beta
    dot = ux*bx + uy*by + uz*bz

    # Relativistic aberration formula (IAU SOFA - AB)
    # u' = [u + (1 + (u·beta)/(1+gamma))·beta] / [gamma(1 + u·beta)]
    factor1 = 1.0 + dot / (1.0 + gamma)
    factor2 = gamma * (1.0 + dot)

    ax = (ux + factor1 * bx) / factor2
    ay = (uy + factor1 * by) / factor2
    az = (uz + factor1 * bz) / factor2

    # Rescale to original distance
    scale = dist / math.sqrt(ax*ax + ay*ay + az*az)
    return (ax * scale, ay * scale, az * scale)


# ---------------------------------------------------------------------------
# 3. Gravitational deflection
# ---------------------------------------------------------------------------

def apply_deflection(
    xyz_body: Vec3,
    deflectors: list,   # list[tuple[Vec3, float]] — (geocentric_pos_km, R_s_km)
) -> Vec3:
    """
    Apply gravitational light deflection from multiple point masses.

    Follows the IAU SOFA LDBODY pattern: deflections from each body are
    applied sequentially to the running unit direction vector, accumulating
    the full relativistic bending from all contributing masses.

    The standard set of deflectors for sub-microarcsecond work is:
        Sun     (~1.75" at limb, ~0.004" at 90°)
        Jupiter (~16 µas peak)
        Saturn  (~6 µas peak)
        Earth   (~6 µas, relevant only for nearby objects)

    Use SCHWARZSCHILD_RADII to look up R_s = 2GM/c² for each body.

    Parameters
    ----------
    xyz_body   : geocentric ICRF position of the target body (km)
    deflectors : list of (geocentric_position_km, schwarzschild_radius_km)
                 tuples — one entry per deflecting mass, in order of
                 decreasing importance (Sun first).

    Returns
    -------
    Gravitationally deflected geocentric position vector (same unit as xyz_body).

    Notes
    -----
    The singularity guard (cos_psi < -0.9999999) catches the anti-solar-point
    geometry where the formula's denominator (1 + cos_psi) approaches zero.
    At that geometry the physical deflection is zero, so skipping the
    deflector is exact.
    """
    dist_body = vec_norm(xyz_body)
    if dist_body < 1e-10:
        return xyz_body

    # Work with the running unit direction vector u.
    # Each deflector nudges u; we re-normalise after every step.
    ux, uy, uz = xyz_body[0] / dist_body, xyz_body[1] / dist_body, xyz_body[2] / dist_body

    for xyz_defl, rs in deflectors:
        dist_defl = vec_norm(xyz_defl)
        if dist_defl < 1e-10:
            continue  # deflector at observer — skip

        ex = xyz_defl[0] / dist_defl
        ey = xyz_defl[1] / dist_defl
        ez = xyz_defl[2] / dist_defl

        cos_psi = ux*ex + uy*ey + uz*ez

        # Anti-deflector-point singularity guard (see docstring).
        if cos_psi < -0.9999999:
            continue

        g1 = rs / dist_defl
        f2 = cos_psi / (1.0 + cos_psi)

        # du = g1 * (e − (cos_psi / (1 + cos_psi)) · u)
        # Equivalent to IAU SOFA LDBODY vector form.
        dx = g1 * (ex - f2 * ux)
        dy = g1 * (ey - f2 * uy)
        dz = g1 * (ez - f2 * uz)

        nx, ny, nz = ux + dx, uy + dy, uz + dz
        mag = math.sqrt(nx*nx + ny*ny + nz*nz)
        ux, uy, uz = nx / mag, ny / mag, nz / mag

    return (ux * dist_body, uy * dist_body, uz * dist_body)


# ---------------------------------------------------------------------------
# 4. Frame bias
# ---------------------------------------------------------------------------

def apply_frame_bias(xyz: Vec3) -> Vec3:
    """
    Rotate an ICRF position vector to the dynamical mean equator and equinox
    of J2000.0 using the IAU 2006 frame bias (Capitaine et al.).

    Frame bias is a small, fixed, time-independent rotation between the
    ICRF pole/origin and the dynamical mean equatorial pole/equinox of J2000.0.
    It is distinct from nutation/precession and from the ecliptic frame —
    no obliquity rotation is applied here.

    The correction is ~17–18 arcseconds in total angular displacement.

    Parameters
    ----------
    xyz : position in ICRF (any unit)

    Returns
    -------
    Position in dynamical mean equator/equinox J2000.0 frame (same unit)
    """
    if _HAS_NUMPY:
        r = _np.dot(_FRAME_BIAS_MATRIX, _np.asarray(xyz, dtype=_np.float64))
        return (float(r[0]), float(r[1]), float(r[2]))

    x, y, z = xyz

    # Small-angle rotation matrix (IAU 2006 frame bias)
    # R = I + antisymmetric part only (second-order terms negligible)
    xb =  x       - _de0_r * y + _xi0_r * z
    yb =  _de0_r  * x + y      - _dA_r  * z
    zb = -_xi0_r  * x + _dA_r  * y + z

    return (xb, yb, zb)


# ---------------------------------------------------------------------------
# 5. Topocentric parallax
# ---------------------------------------------------------------------------

def topocentric_correction(
    xyz_geocentric: Vec3,
    latitude_deg: float,
    longitude_deg: float,
    lst_deg: float,
    elevation_m: float = 0.0,
) -> Vec3:
    """
    Shift a geocentric position vector to a topocentric (surface) observer.

    The effect is largest for the Moon (~1°) and negligible for planets
    beyond a few AU (< 0.01″ for Jupiter and beyond).

    Parameters
    ----------
    xyz_geocentric : geocentric ICRF position (km)
    latitude_deg   : geographic (geodetic) latitude, degrees
    longitude_deg  : geographic east longitude, degrees
    lst_deg        : Local Sidereal Time, degrees
    elevation_m    : observer elevation above sea level, metres

    Returns
    -------
    Topocentric ICRF position (km)
    """
    lat = latitude_deg * DEG2RAD
    lst = lst_deg      * DEG2RAD

    # WGS-84 geodetic → geocentric rectangular (Meeus §11, USNO Circular 179)
    f   = 1.0 / 298.257223563   # WGS-84 flattening
    a   = EARTH_RADIUS_KM       # equatorial radius (km)
    h   = elevation_m / 1000.0  # elevation in km

    C = 1.0 / math.sqrt(math.cos(lat)**2 + (1.0 - f)**2 * math.sin(lat)**2)
    S = (1.0 - f)**2 * C

    # Elevation is added directly to the scaled equatorial radius, not as a
    # simple spherical increment — this is the correct WGS-84 separation.
    obs_x = (a * C + h) * math.cos(lat) * math.cos(lst)
    obs_y = (a * C + h) * math.cos(lat) * math.sin(lst)
    obs_z = (a * S + h) * math.sin(lat)

    # Topocentric = geocentric − observer position
    return vec_sub(xyz_geocentric, (obs_x, obs_y, obs_z))


# ---------------------------------------------------------------------------
# 6. Atmospheric refraction
# ---------------------------------------------------------------------------

def apply_refraction(
    altitude_deg: float,
    *,
    pressure_mbar: float = 1013.25,
    temperature_c: float = 10.0,
    relative_humidity: float = 0.0,
) -> float:
    """
    Apply atmospheric refraction to a geometric altitude, returning the
    apparent (observed) altitude.

    Refraction lifts objects above the geometric horizon — the effect is
    largest near the horizon (~0.57° at 0°) and negligible above ~45°.
    This is the final stage of the apparent-position pipeline and must be
    applied *after* the topocentric correction and the horizontal-coordinate
    projection, not to any intermediate ICRF vector.

    When ``relative_humidity`` is non-zero, uses the extended Bennett model
    from ``atmospheric_refraction_extended()`` which incorporates the partial
    pressure of water vapour (Magnus approximation) into the refractivity
    correction.  At ``relative_humidity=0.0`` (the default) the result is
    identical to the plain Bennett formula.

    Parameters
    ----------
    altitude_deg       : geometric (true) altitude in degrees
    pressure_mbar      : atmospheric pressure in millibars (default 1013.25)
    temperature_c      : air temperature in degrees Celsius (default 10.0)
    relative_humidity  : relative humidity 0–1 (default 0.0 = dry air).
                         When non-zero, water-vapour partial pressure is
                         computed via the Magnus formula and applied as a
                         multiplicative refractivity correction.

    Returns
    -------
    Apparent altitude in degrees (geometric altitude + refraction angle).
    """
    if relative_humidity:
        refraction, _ = _atmospheric_refraction_extended(
            altitude_deg,
            pressure_mbar=pressure_mbar,
            temperature_c=temperature_c,
            relative_humidity=relative_humidity,
        )
        return altitude_deg + refraction
    return altitude_deg + _atmospheric_refraction(
        altitude_deg,
        pressure_mbar=pressure_mbar,
        temperature_c=temperature_c,
    )
