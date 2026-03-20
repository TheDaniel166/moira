"""
Moira — coordinates.py
The Coordinate Transform Engine: governs all conversions between rectangular
ICRF barycentric vectors and spherical ecliptic/equatorial/horizontal coordinates.

Boundary: owns the full pipeline from raw (x, y, z) km vectors to final
ecliptic longitude/latitude/distance results, equatorial RA/Dec, and
observer-centric azimuth/altitude.  Delegates obliquity computation to
obliquity.py and precession matrix construction to precession.py.  Does not
own house calculations, aspect detection, body-position retrieval, or any
display formatting.

Coordinate systems served:
  - ICRF      : International Celestial Reference Frame (equatorial, J2000,
                barycentric) — the native frame of DE441 state vectors.
  - Ecliptic  : geocentric ecliptic longitude / latitude / distance.
  - Equatorial: right ascension / declination (degrees).
  - Horizontal: azimuth / altitude (observer-centric, degrees).

All angles are in degrees unless a function explicitly states otherwise.
All 3-vectors are numpy-free plain Python tuples of three floats.

Public surface:
    Vec3, Mat3,
    vec_add, vec_sub, vec_scale, vec_norm, vec_unit,
    mat_vec_mul, mat_mul,
    rot_x_axis, rot_y_axis, rot_z_axis, rot_x, rot_y, rot_z,
    icrf_to_ecliptic, icrf_to_true_ecliptic, icrf_to_equatorial,
    true_ecliptic_latitude,
    precession_matrix_equatorial, nutation_matrix_equatorial,
    equatorial_to_horizontal,
    ecliptic_to_equatorial, equatorial_to_ecliptic,
    aberration_correction,
    normalize_degrees, angular_distance, signed_angular_distance

Import-time side effects: None

External dependency assumptions:
    None (stdlib math only; obliquity.py and precession.py are imported
    lazily inside individual functions to avoid circular imports)
"""

import math
from .constants import DEG2RAD, RAD2DEG


# ---------------------------------------------------------------------------
# Low-level 3-vector helpers (no numpy dependency)
# ---------------------------------------------------------------------------

Vec3 = tuple
Mat3 = tuple


def vec_add(a: Vec3, b: Vec3) -> Vec3:
    return (a[0]+b[0], a[1]+b[1], a[2]+b[2])


def vec_sub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0]-b[0], a[1]-b[1], a[2]-b[2])


def vec_scale(a: Vec3, s: float) -> Vec3:
    return (a[0]*s, a[1]*s, a[2]*s)


def vec_norm(a: Vec3) -> float:
    return math.sqrt(a[0]**2 + a[1]**2 + a[2]**2)


def vec_unit(a: Vec3) -> Vec3:
    n = vec_norm(a)
    return (a[0]/n, a[1]/n, a[2]/n)


def mat_vec_mul(m: Mat3, v: Vec3) -> Vec3:
    return (
        m[0][0] * v[0] + m[0][1] * v[1] + m[0][2] * v[2],
        m[1][0] * v[0] + m[1][1] * v[1] + m[1][2] * v[2],
        m[2][0] * v[0] + m[2][1] * v[1] + m[2][2] * v[2],
    )


def mat_mul(a: Mat3, b: Mat3) -> Mat3:
    return (
        (
            a[0][0] * b[0][0] + a[0][1] * b[1][0] + a[0][2] * b[2][0],
            a[0][0] * b[0][1] + a[0][1] * b[1][1] + a[0][2] * b[2][1],
            a[0][0] * b[0][2] + a[0][1] * b[1][2] + a[0][2] * b[2][2],
        ),
        (
            a[1][0] * b[0][0] + a[1][1] * b[1][0] + a[1][2] * b[2][0],
            a[1][0] * b[0][1] + a[1][1] * b[1][1] + a[1][2] * b[2][1],
            a[1][0] * b[0][2] + a[1][1] * b[1][2] + a[1][2] * b[2][2],
        ),
        (
            a[2][0] * b[0][0] + a[2][1] * b[1][0] + a[2][2] * b[2][0],
            a[2][0] * b[0][1] + a[2][1] * b[1][1] + a[2][2] * b[2][1],
            a[2][0] * b[0][2] + a[2][1] * b[1][2] + a[2][2] * b[2][2],
        ),
    )


def rot_x_axis(angle_rad: float) -> Mat3:
    """Passive rotation matrix around X axis (rotation of coordinate frame)."""
    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    return (
        (1.0, 0.0, 0.0),
        (0.0, c,   s),
        (0.0, -s,  c),
    )


def rot_y_axis(angle_rad: float) -> Mat3:
    """Passive rotation matrix around Y axis."""
    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    return (
        (c,   0.0, -s),
        (0.0, 1.0, 0.0),
        (s,   0.0, c),
    )


def rot_z_axis(angle_rad: float) -> Mat3:
    """Passive rotation matrix around Z axis."""
    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    return (
        (c,   s,   0.0),
        (-s,  c,   0.0),
        (0.0, 0.0, 1.0),
    )


# Alias for legacy code or active rotation needs
def rot_x(angle_rad: float) -> Mat3: return rot_x_axis(-angle_rad)
def rot_y(angle_rad: float) -> Mat3: return rot_y_axis(-angle_rad)
def rot_z(angle_rad: float) -> Mat3: return rot_z_axis(-angle_rad)


# ---------------------------------------------------------------------------
# ICRF rectangular → ecliptic longitude / latitude
# ---------------------------------------------------------------------------

def icrf_to_ecliptic(xyz: Vec3, obliquity_deg: float) -> tuple[float, float, float]:
    """
    Convert an ICRF rectangular position vector to ecliptic coordinates.

    Parameters
    ----------
    xyz          : (x, y, z) in any consistent unit (km, AU, etc.)
    obliquity_deg: true obliquity of the ecliptic in degrees

    Returns
    -------
    (longitude, latitude, distance)  — longitude and latitude in degrees,
                                        distance in same units as input
    """
    eps = obliquity_deg * DEG2RAD
    cos_eps = math.cos(eps)
    sin_eps = math.sin(eps)

    x, y, z = xyz

    # Rotate from equatorial to ecliptic frame
    xe =  x
    ye =  y * cos_eps + z * sin_eps
    ze = -y * sin_eps + z * cos_eps

    distance  = math.sqrt(xe**2 + ye**2 + ze**2)
    longitude = math.atan2(ye, xe) * RAD2DEG % 360.0
    latitude  = math.asin(ze / distance) * RAD2DEG if distance > 0 else 0.0

    return longitude, latitude, distance


def precession_matrix_equatorial(jd_tt: float) -> Mat3:
    """
    Precession matrix from mean equator/equinox J2000.0 to mean equator/equinox of date.
    Uses the IAU 2006 (P03) Fukushima-Williams model.
    """
    from .precession import precession_matrix
    return precession_matrix(jd_tt)


def nutation_matrix_equatorial(jd_tt: float) -> Mat3:
    """
    Nutation matrix from mean equator/equinox of date to true equator/equinox of date.
    Uses IAU 2000A model.
    """
    from .obliquity import mean_obliquity, nutation

    eps0_rad = mean_obliquity(jd_tt) * DEG2RAD
    dpsi_deg, deps_deg = nutation(jd_tt)
    eps_rad = eps0_rad + (deps_deg * DEG2RAD)
    dpsi_rad = dpsi_deg * DEG2RAD

    # Nutation matrix (passive rotation sequence)
    # N = R1(-eps) * R3(-dpsi) * R1(eps0)
    return mat_mul(rot_x_axis(-eps_rad),
           mat_mul(rot_z_axis(-dpsi_rad),
                   rot_x_axis(eps0_rad)))


def icrf_to_true_ecliptic(jd_tt: float, xyz: Vec3) -> tuple[float, float, float]:
    """
    Convert an ICRF/J2000 equatorial vector directly to true ecliptic-of-date coordinates.
    """
    from .obliquity import true_obliquity

    precession = precession_matrix_equatorial(jd_tt)
    nutation = nutation_matrix_equatorial(jd_tt)
    true_equatorial = mat_vec_mul(nutation, mat_vec_mul(precession, xyz))
    return icrf_to_ecliptic(true_equatorial, true_obliquity(jd_tt))


def true_ecliptic_latitude(jd_tt: float, xyz: Vec3) -> float:
    """
    Return the true ecliptic latitude of date for an ICRF/J2000 vector.

    This applies the mean-to-true equator nutation rotation before the
    equatorial-to-ecliptic conversion, which materially improves latitude
    accuracy while preserving the existing high-accuracy longitude pipeline.
    """
    from .obliquity import true_obliquity

    true_equatorial = mat_vec_mul(nutation_matrix_equatorial(jd_tt), xyz)
    _, lat, _ = icrf_to_ecliptic(true_equatorial, true_obliquity(jd_tt))
    return lat


def icrf_to_equatorial(xyz: Vec3) -> tuple[float, float, float]:
    """
    Convert an ICRF rectangular vector to equatorial RA/Dec.

    Returns
    -------
    (right_ascension, declination, distance)  — degrees
    """
    x, y, z = xyz
    distance = math.sqrt(x**2 + y**2 + z**2)
    ra  = math.atan2(y, x) * RAD2DEG % 360.0
    dec = math.asin(z / distance) * RAD2DEG if distance > 0 else 0.0
    return ra, dec, distance


# ---------------------------------------------------------------------------
# Equatorial → Horizontal (azimuth / altitude)
# ---------------------------------------------------------------------------

def equatorial_to_horizontal(
    ra_deg: float,
    dec_deg: float,
    lst_deg: float,
    lat_deg: float,
) -> tuple[float, float]:
    """
    Convert equatorial (RA, Dec) to horizontal (Azimuth, Altitude).

    Parameters
    ----------
    ra_deg  : Right Ascension in degrees
    dec_deg : Declination in degrees
    lst_deg : Local Sidereal Time in degrees
    lat_deg : Geographic latitude in degrees (north positive)

    Returns
    -------
    (azimuth, altitude) in degrees
    Azimuth is measured from North, clockwise (0=N, 90=E, 180=S, 270=W).
    """
    ha  = (lst_deg - ra_deg) % 360.0   # Hour Angle
    ha_r  = ha  * DEG2RAD
    dec_r = dec_deg * DEG2RAD
    lat_r = lat_deg * DEG2RAD

    sin_alt = (math.sin(dec_r) * math.sin(lat_r)
               + math.cos(dec_r) * math.cos(lat_r) * math.cos(ha_r))
    alt = math.asin(sin_alt) * RAD2DEG

    cos_az = ((math.sin(dec_r) - math.sin(lat_r) * sin_alt)
              / (math.cos(lat_r) * math.cos(alt * DEG2RAD)))
    # clamp for numerical safety
    cos_az = max(-1.0, min(1.0, cos_az))
    az = math.acos(cos_az) * RAD2DEG

    if math.sin(ha_r) > 0:
        az = 360.0 - az

    return az, alt


# ---------------------------------------------------------------------------
# Ecliptic ↔ equatorial conversions
# ---------------------------------------------------------------------------

def ecliptic_to_equatorial(
    lon_deg: float,
    lat_deg: float,
    obliquity_deg: float,
) -> tuple[float, float]:
    """
    Convert ecliptic longitude/latitude to equatorial RA/Dec.

    Returns
    -------
    (right_ascension, declination) in degrees
    """
    eps = obliquity_deg * DEG2RAD
    lon = lon_deg * DEG2RAD
    lat = lat_deg * DEG2RAD

    sin_dec = (math.sin(lat) * math.cos(eps)
               + math.cos(lat) * math.sin(eps) * math.sin(lon))
    dec = math.asin(sin_dec) * RAD2DEG

    y = math.sin(lon) * math.cos(eps) - math.tan(lat) * math.sin(eps)
    x = math.cos(lon)
    ra = math.atan2(y, x) * RAD2DEG % 360.0

    return ra, dec


def equatorial_to_ecliptic(
    ra_deg: float,
    dec_deg: float,
    obliquity_deg: float,
) -> tuple[float, float]:
    """
    Convert equatorial RA/Dec to ecliptic longitude/latitude.

    Returns
    -------
    (longitude, latitude) in degrees
    """
    eps = obliquity_deg * DEG2RAD
    ra  = ra_deg  * DEG2RAD
    dec = dec_deg * DEG2RAD

    sin_lat = (math.sin(dec) * math.cos(eps)
               - math.cos(dec) * math.sin(eps) * math.sin(ra))
    lat = math.asin(sin_lat) * RAD2DEG

    y = math.sin(ra) * math.cos(eps) + math.tan(dec) * math.sin(eps)
    x = math.cos(ra)
    lon = math.atan2(y, x) * RAD2DEG % 360.0

    return lon, lat


# ---------------------------------------------------------------------------
# Aberration (annual) — approximate correction
# ---------------------------------------------------------------------------

def aberration_correction(
    lon_deg: float,
    lat_deg: float,
    sun_lon_deg: float,
    obliquity_deg: float,
) -> tuple[float, float]:
    """
    Approximate correction for annual aberration (Meeus Ch.23).
    Returns (Δλ, Δβ) in degrees to add to ecliptic coordinates.

    Accuracy: ~1 arcsecond.
    """
    k  = 20.49552 / 3600.0   # constant of aberration in degrees
    lon = lon_deg     * DEG2RAD
    lat = lat_deg     * DEG2RAD
    sun = sun_lon_deg * DEG2RAD
    eps = obliquity_deg * DEG2RAD

    dlambda = (-k * (math.cos(sun - lon) - math.cos(lat)**2 * math.cos(eps)
                     * math.sin(eps) * math.cos(sun) / math.cos(lat)**2)
               / math.cos(lat))
    dbeta   = -k * math.sin(lat) * (math.sin(sun - lon)
                                     - math.sin(eps) * math.sin(lon - sun)
                                       / math.cos(lat))
    return dlambda, dbeta


# ---------------------------------------------------------------------------
# Angle utilities
# ---------------------------------------------------------------------------

def normalize_degrees(angle: float) -> float:
    """Reduce an angle to [0, 360)."""
    return angle % 360.0


def angular_distance(a: float, b: float) -> float:
    """Shortest angular distance between two longitudes (0–180°)."""
    diff = abs((a - b) % 360.0)
    return diff if diff <= 180.0 else 360.0 - diff


def signed_angular_distance(from_deg: float, to_deg: float) -> float:
    """Signed difference to_deg − from_deg in (−180, +180]."""
    diff = (to_deg - from_deg) % 360.0
    if diff > 180.0:
        diff -= 360.0
    return diff
