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
          (point-mass Sun), IAU 2006 frame bias rotation, and WGS-84 topocentric
          parallax shift.
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
    apply_deflection(xyz_body, xyz_sun, earth_barycentric) -> Vec3
    apply_frame_bias(xyz) -> Vec3
    topocentric_correction(xyz_geocentric, latitude_deg, longitude_deg,
                           lst_deg, elevation_m) -> Vec3
"""

import math
from .constants import DEG2RAD, RAD2DEG, ARCSEC2RAD
from .coordinates import Vec3, vec_sub, vec_norm, vec_scale, vec_add

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------

C_KM_PER_DAY = 299_792.458 * 86_400.0   # speed of light in km/day
EARTH_RADIUS_KM = 6_378.137              # equatorial Earth radius, km

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
    # First estimate: compute planet at current time t
    pos_body = barycentric_fn(body, jd_tt, reader)
    dist0 = vec_norm(vec_sub(pos_body, earth_ssb))
    lt    = dist0 / C_KM_PER_DAY

    # Newton-Raphson step: planet at t - lt
    pos_body_lt = barycentric_fn(body, jd_tt - lt, reader)
    xyz_geocentric_lt = vec_sub(pos_body_lt, earth_ssb)
    dist1 = vec_norm(xyz_geocentric_lt)
    lt    = dist1 / C_KM_PER_DAY

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

    # Unit direction to body (u)
    ux, uy, uz = xyz[0] / dist, xyz[1] / dist, xyz[2] / dist

    # Velocity as fraction of c (beta)
    bx = earth_velocity_xyz[0] / C_KM_PER_DAY
    by = earth_velocity_xyz[1] / C_KM_PER_DAY
    bz = earth_velocity_xyz[2] / C_KM_PER_DAY

    # Lorents factor: gamma = 1 / sqrt(1 - beta^2)
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
    xyz_sun: Vec3,           # Sun position relative to Earth (km, ICRF)
    earth_barycentric: Vec3, # Earth position relative to SSB (km, ICRF)
) -> Vec3:
    """
    Apply gravitational light deflection (near the Sun) to a geocentric vector.

    Follows the IAU SOFA (LDSUN) point-mass deflection model.
    The effect is ~1.75" at the Sun's limb and ~0.004" at 90 deg.

    Parameters
    ----------
    xyz_body          : geocentric ICRF position of body (km)
    xyz_sun           : geocentric ICRF position of Sun (km)
    earth_barycentric : Solar System Barycentric position of Earth (km)

    Returns
    -------
    Gravitationally deflected geocentric position vector (same unit as xyz_body)
    """
    dist_body = vec_norm(xyz_body)
    dist_sun  = vec_norm(xyz_sun)
    dist_earth_sun = vec_norm(vec_sub(xyz_sun, (0,0,0))) # redundant, dist_sun

    # u: unit vector from Earth to body
    ux, uy, uz = xyz_body[0]/dist_body, xyz_body[1]/dist_body, xyz_body[2]/dist_body

    # e: unit vector from Earth to Sun
    ex, ey, ez = xyz_sun[0]/dist_sun, xyz_sun[1]/dist_sun, xyz_sun[2]/dist_sun

    # cos_psi = u·e
    cos_psi = ux*ex + uy*ey + uz*ez

    # Scaling factor g1 = 2 * G * M_sun / (c^2 * r_e)
    # For Sun: 2 * mu / c^2 is the Schwarzschild radius R_s ~ 2.953 km
    # g1 ~ R_s / distance_to_sun
    rs_sun = 2.95325008  # km
    g1 = rs_sun / dist_sun

    # Singularity guard: the deflection formula contains 1/(1 + cos_psi).
    # This diverges when cos_psi → -1, i.e. when the body is at the anti-solar
    # point (exactly opposite the Sun as seen from Earth). At that geometry the
    # deflection is physically zero anyway, so we return the unmodified vector.
    # cos_psi = +1 (body in the direction of the Sun) is NOT a singularity;
    # the denominator 1 + cos_psi → 2 there.
    if cos_psi < -0.9999999:
        return xyz_body

    # Vector form: du = g1 * ( (1+cos_psi)·e - (cos_psi)·u ) / (1+cos_psi)
    #              du = g1 * ( e - (cos_psi/(1+cos_psi))·u )
    # Note: SOFA uses ( (1+u·e)·e - (u·e)·u ) / (1+u·e)
    # which simplifies to e·[denom/denom] - u·[cos/denom] = e - u*(cos/(1+cos))

    f2 = cos_psi / (1.0 + cos_psi)
    dx = g1 * (ex - f2 * ux)
    dy = g1 * (ey - f2 * uy)
    dz = g1 * (ez - f2 * uz)

    # u_final = u + du (then normalise)
    nx, ny, nz = ux + dx, uy + dy, uz + dz
    mag = math.sqrt(nx*nx + ny*ny + nz*nz)

    scale = dist_body / mag
    return (nx * scale, ny * scale, nz * scale)


# ---------------------------------------------------------------------------
# 3. Frame bias
# ---------------------------------------------------------------------------

def apply_frame_bias(xyz: Vec3) -> Vec3:
    """
    Rotate an ICRF position vector to the dynamical mean ecliptic J2000.0
    frame using the IAU 2006 frame bias (Capitaine et al.).

    The correction is ~17–18 arcseconds and is a fixed, time-independent
    rotation of the coordinate frame.

    Parameters
    ----------
    xyz : position in ICRF (any unit)

    Returns
    -------
    Position in dynamical mean ecliptic J2000.0 frame (same unit)
    """
    x, y, z = xyz

    # Small-angle rotation matrix (IAU 2006 frame bias)
    # R = I + antisymmetric part only (second-order terms negligible)
    xb =  x       - _de0_r * y + _xi0_r * z
    yb =  _de0_r  * x + y      - _dA_r  * z
    zb = -_xi0_r  * x + _dA_r  * y + z

    return (xb, yb, zb)


# ---------------------------------------------------------------------------
# 4. Topocentric parallax
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
