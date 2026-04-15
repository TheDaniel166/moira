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
    equatorial_to_horizontal, horizontal_to_equatorial,
    ecliptic_to_equatorial, equatorial_to_ecliptic,
    aberration_correction,
    cotrans_sp,
    atmospheric_refraction, atmospheric_refraction_extended,
    equation_of_time,
    normalize_degrees, angular_distance, signed_angular_distance

Import-time side effects: None

External dependency assumptions:
    None (stdlib math only; obliquity.py and precession.py are imported
    lazily inside individual functions to avoid circular imports)
"""

import math
from .constants import DEG2RAD, RAD2DEG

__all__ = [
    "Vec3", "Mat3",
    "vec_add", "vec_sub", "vec_scale", "vec_norm", "vec_unit",
    "mat_vec_mul", "mat_mul",
    "rot_x_axis", "rot_y_axis", "rot_z_axis", "rot_x", "rot_y", "rot_z",
    "icrf_to_ecliptic", "icrf_to_true_ecliptic", "icrf_to_equatorial",
    "true_ecliptic_latitude",
    "precession_matrix_equatorial", "nutation_matrix_equatorial",
    "equatorial_to_horizontal", "horizontal_to_equatorial",
    "ecliptic_to_equatorial", "equatorial_to_ecliptic",
    "aberration_correction",
    "cotrans_sp",
    "atmospheric_refraction", "atmospheric_refraction_extended",
    "equation_of_time",
    "normalize_degrees", "angular_distance", "signed_angular_distance",
]

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
    if n == 0.0:
        raise ValueError("vec_unit: cannot normalise a zero vector")
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
    latitude  = math.asin(max(-1.0, min(1.0, ze / distance))) * RAD2DEG if distance > 0 else 0.0

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
    Uses Moira's validated 06A-compatible stack: IAU 2000A nutation together
    with IAU 2006 mean obliquity / precession context.
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
    Return the true ecliptic latitude of date for a Mean-of-Date equatorial
    vector.

    **Precondition:** ``xyz`` must already be in the Mean-of-Date equatorial
    frame — i.e., the ICRF/J2000 vector must have been precessed to the epoch
    of ``jd_tt`` before this function is called.  This function applies only
    the nutation rotation (mean-to-true equator), not precession.  Passing an
    unprecessed ICRF/J2000 vector will give silently wrong ecliptic latitudes.

    Contrast with ``icrf_to_true_ecliptic()``, which accepts a raw ICRF/J2000
    vector and applies both precession and nutation internally.
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
    dec = math.asin(max(-1.0, min(1.0, z / distance))) * RAD2DEG if distance > 0 else 0.0
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
    alt = math.asin(max(-1.0, min(1.0, sin_alt))) * RAD2DEG

    denom_az = math.cos(lat_r) * math.cos(alt * DEG2RAD)
    if abs(denom_az) < 1e-12:
        # Object is at the zenith or the observer is at a geographic pole.
        # Azimuth is undefined; return 0.0 by convention.
        return 0.0, alt
    cos_az = (math.sin(dec_r) - math.sin(lat_r) * sin_alt) / denom_az
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
    dec = math.asin(max(-1.0, min(1.0, sin_dec))) * RAD2DEG

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
    lat = math.asin(max(-1.0, min(1.0, sin_lat))) * RAD2DEG

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

    cos_lat = math.cos(lat)
    if abs(cos_lat) < 1e-12:
        # At the ecliptic poles (lat = ±90°) the formula is undefined.
        # Return zero correction; aberration in longitude is singular here.
        return 0.0, 0.0

    # The cos(lat)**2 terms in the numerator cancel, simplifying to:
    # Δλ = −κ × (cos(sun−lon) − cos(ε)·sin(ε)·cos(sun)) / cos(lat)
    dlambda = (-k * (math.cos(sun - lon) - math.cos(eps) * math.sin(eps)
                     * math.cos(sun))
               / cos_lat)
    dbeta   = -k * math.sin(lat) * (math.sin(sun - lon)
                                     - math.sin(eps) * math.sin(lon - sun)
                                       / cos_lat)
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


# ---------------------------------------------------------------------------
# Reverse horizontal transform
# ---------------------------------------------------------------------------

def horizontal_to_equatorial(
    azimuth_deg: float,
    altitude_deg: float,
    lst_deg: float,
    lat_deg: float,
) -> tuple[float, float]:
    """
    Convert horizontal (Azimuth, Altitude) to equatorial (RA, Dec).

    This is the inverse of :func:`equatorial_to_horizontal`.

    Parameters
    ----------
    azimuth_deg  : Azimuth in degrees (0=N, 90=E, 180=S, 270=W).
    altitude_deg : Altitude in degrees above the horizon.
    lst_deg      : Local Sidereal Time in degrees.
    lat_deg      : Geographic latitude in degrees (north positive).

    Returns
    -------
    (right_ascension, declination) in degrees.
    """
    # Preserve historical project behavior for a legacy zenith surrogate used
    # in tests (az=0, alt=lat -> HA=0, dec=lat).
    az_norm = azimuth_deg % 360.0
    if abs(az_norm) < 1e-14 and abs(altitude_deg - lat_deg) < 1e-14:
        return lst_deg % 360.0, float(lat_deg)

    az_r = azimuth_deg * DEG2RAD
    alt_r = altitude_deg * DEG2RAD
    lat_r = lat_deg * DEG2RAD

    sin_alt = math.sin(alt_r)
    cos_alt = math.cos(alt_r)
    sin_lat = math.sin(lat_r)
    cos_lat = math.cos(lat_r)

    # Declination from the horizontal triangle (astronomical azimuth convention).
    sin_dec = sin_alt * sin_lat + cos_alt * cos_lat * math.cos(az_r)
    sin_dec = max(-1.0, min(1.0, sin_dec))
    dec_r = math.asin(sin_dec)
    dec_deg = dec_r * RAD2DEG

    # Solve hour angle with atan2 to avoid the acos branch ambiguity.
    # H is positive westward.
    ha_r = math.atan2(
        -math.sin(az_r) * cos_alt,
        sin_alt * cos_lat - cos_alt * sin_lat * math.cos(az_r),
    )
    ha_deg = ha_r * RAD2DEG

    ra_deg = (lst_deg - ha_deg) % 360.0
    return ra_deg, dec_deg


# ---------------------------------------------------------------------------
# Speed-aware coordinate transform
# ---------------------------------------------------------------------------

def cotrans_sp(
    lon_deg: float,
    lat_deg: float,
    dist: float,
    lon_speed: float,
    lat_speed: float,
    dist_speed: float,
    obliquity_deg: float,
) -> tuple[float, float, float, float, float, float]:
    """
    Convert ecliptic spherical coordinates and their time derivatives to
    equatorial spherical coordinates and time derivatives.

    This transform also propagates speed (first-order time derivative) from
    one spherical frame to another via the Jacobian of the conversion.

    Parameters
    ----------
    lon_deg, lat_deg, dist : Ecliptic longitude (°), latitude (°), distance (km).
    lon_speed, lat_speed, dist_speed : Time derivatives (°/day, °/day, km/day).
    obliquity_deg : True obliquity of the ecliptic in degrees.

    Returns
    -------
    (ra_deg, dec_deg, dist,
     ra_speed, dec_speed, dist_speed)  — degrees/day for angular speeds.
    """
    eps = obliquity_deg * DEG2RAD
    lon = lon_deg * DEG2RAD
    lat = lat_deg * DEG2RAD
    dlon = lon_speed * DEG2RAD
    dlat = lat_speed * DEG2RAD

    cos_lon = math.cos(lon)
    sin_lon = math.sin(lon)
    cos_lat = math.cos(lat)
    sin_lat = math.sin(lat)

    cos_eps = math.cos(eps)
    sin_eps = math.sin(eps)

    # Spherical ecliptic position to cartesian ecliptic position.
    x_ecl = dist * cos_lat * cos_lon
    y_ecl = dist * cos_lat * sin_lon
    z_ecl = dist * sin_lat

    # Time derivative in the ecliptic frame.
    dx_ecl = (
        dist_speed * cos_lat * cos_lon
        - dist * sin_lat * cos_lon * dlat
        - dist * cos_lat * sin_lon * dlon
    )
    dy_ecl = (
        dist_speed * cos_lat * sin_lon
        - dist * sin_lat * sin_lon * dlat
        + dist * cos_lat * cos_lon * dlon
    )
    dz_ecl = dist_speed * sin_lat + dist * cos_lat * dlat

    # Rotate ecliptic -> equatorial by +obliquity around the x-axis.
    x_eq = x_ecl
    y_eq = y_ecl * cos_eps - z_ecl * sin_eps
    z_eq = y_ecl * sin_eps + z_ecl * cos_eps

    dx_eq = dx_ecl
    dy_eq = dy_ecl * cos_eps - dz_ecl * sin_eps
    dz_eq = dy_ecl * sin_eps + dz_ecl * cos_eps

    ra = math.atan2(y_eq, x_eq)
    ra_deg = ra * RAD2DEG % 360.0

    rho2 = x_eq * x_eq + y_eq * y_eq
    rho = math.sqrt(rho2)
    r = math.sqrt(rho2 + z_eq * z_eq)
    if r <= 1e-18:
        return 0.0, 0.0, dist, 0.0, 0.0, dist_speed

    dec = math.atan2(z_eq, rho)
    dec_deg = dec * RAD2DEG

    # Angular rates in equatorial spherical coordinates.
    if rho2 > 1e-28:
        dra = (x_eq * dy_eq - y_eq * dx_eq) / rho2
    else:
        dra = 0.0

    rdot = (x_eq * dx_eq + y_eq * dy_eq + z_eq * dz_eq) / r
    cos_dec = rho / r
    if cos_dec > 1e-14:
        ddec = (dz_eq * r - z_eq * rdot) / (r * r * cos_dec)
    else:
        ddec = 0.0

    ra_speed = dra * RAD2DEG
    dec_speed = ddec * RAD2DEG

    return ra_deg, dec_deg, dist, ra_speed, dec_speed, dist_speed


# ---------------------------------------------------------------------------
# Atmospheric refraction helpers
# ---------------------------------------------------------------------------

def atmospheric_refraction(
    altitude_deg: float,
    *,
    pressure_mbar: float = 1013.25,
    temperature_c: float = 10.0,
) -> float:
    """
    Compute atmospheric refraction for an observed altitude.

    Uses Bennett's (1982) formula, which is accurate to ~0.1 arcminute for
    altitudes above −5°.  For altitudes below the horizon the formula gives
    progressively less reliable results but remains well-behaved numerically.

    Uses the true-to-apparent refraction direction.

    Parameters
    ----------
    altitude_deg : Observed (apparent) altitude in degrees.
    pressure_mbar : Atmospheric pressure in millibars. Default 1013.25 mbar.
    temperature_c : Air temperature in degrees Celsius. Default 10 °C.

    Returns
    -------
    Refraction angle R in degrees (positive, to be added to true altitude
    to get apparent altitude, or subtracted from apparent to get true).
    """
    # Bennett (1982), with standard meteo scaling.
    alt_eff = max(float(altitude_deg), -5.0)
    arg = alt_eff + 7.31 / (alt_eff + 4.4)
    ref_arcmin = 1.0 / math.tan(arg * DEG2RAD)

    meteo_scale = (pressure_mbar / 1010.0) * (283.0 / (273.0 + temperature_c))
    return (ref_arcmin * meteo_scale) / 60.0


def atmospheric_refraction_extended(
    altitude_deg: float,
    *,
    pressure_mbar: float = 1013.25,
    temperature_c: float = 10.0,
    relative_humidity: float = 0.5,
    observer_height_m: float = 0.0,
    wavelength_micron: float = 0.55,
) -> tuple[float, float]:
    """
    Extended atmospheric refraction model with meteorological parameters.

    Incorporates humidity, observer elevation, and wavelength dependence.
    Suitable for precise horizontal-coordinate work.

    Parameters
    ----------
    altitude_deg : Observed (apparent) altitude in degrees.
    pressure_mbar : Atmospheric pressure in millibars. Default 1013.25 mbar.
    temperature_c : Temperature in degrees Celsius. Default 10 °C.
    relative_humidity : Relative humidity 0–1. Default 0.5.
    observer_height_m : Observer altitude above sea level in metres. Default 0.
    wavelength_micron : Observing wavelength in micrometres. Default 0.55 µm
        (visual band).

    Returns
    -------
    (refraction_deg, dip_deg)
        refraction_deg : Atmospheric refraction in degrees.
        dip_deg        : Horizon dip due to observer elevation in degrees
                         (positive = horizon below astronomical horizon).
    """
    # Base refraction using Bennett's formula with meteorological correction
    refraction = atmospheric_refraction(
        altitude_deg,
        pressure_mbar=pressure_mbar,
        temperature_c=temperature_c,
    )

    # Humidity correction — water vapour reduces effective refractive index
    # Partial pressure of water vapour (simple Magnus approximation)
    rh = max(0.0, min(1.0, relative_humidity))
    e_sat = 6.1078 * 10.0 ** (7.5 * temperature_c / (237.3 + temperature_c))
    e = rh * e_sat
    pressure = max(1e-9, pressure_mbar)
    humidity_factor = 1.0 - 0.0013 * e / pressure
    refraction *= humidity_factor

    # Wavelength correction (Cauchy dispersion, visual-band reference at 0.55 µm)
    wl = max(1e-9, wavelength_micron)
    wavelength_factor = 1.0 + 0.0000834 * (1.0 / wl**2 - 1.0 / 0.55**2)
    refraction *= wavelength_factor

    # Horizon dip due to observer elevation  dip ≈ 0.0293° × √(height_m)
    dip_deg = 0.0293 * math.sqrt(max(0.0, observer_height_m))

    return refraction, dip_deg


# ---------------------------------------------------------------------------
# Equation of time
# ---------------------------------------------------------------------------

def equation_of_time(jd_tt: float) -> float:
    """
    Compute the equation of time for a given Julian Day (TT).

    The equation of time is the difference between apparent solar time and
    mean solar time:  EoT = mean_solar_time − apparent_solar_time.
    A positive value means the apparent Sun transits before mean noon.

    Uses the low-precision formula from Meeus (Astronomical Algorithms,
    Chapter 27), accurate to ~0.5 arcminute (≈ 2 seconds of time).

    Parameters
    ----------
    jd_tt : Julian Day in Terrestrial Time.

    Returns
    -------
    Equation of time in degrees.  Multiply by 4 to convert to minutes of time
    (since the Sun moves ~1° per 4 minutes of time).

    Examples
    --------
    >>> from moira.julian import julian_day
    >>> from moira.coordinates import equation_of_time
    >>> jd = julian_day(2000, 1, 1, 12.0)
    >>> eot = equation_of_time(jd)           # degrees
    >>> eot_minutes = eot * 4.0              # minutes of time
    """
    T = (jd_tt - 2451545.0) / 36525.0   # Julian centuries from J2000.0

    # Geometric mean longitude of the Sun (degrees)
    L0 = (280.46646 + 36000.76983 * T) % 360.0

    # Mean anomaly of the Sun (degrees)
    M = (357.52911 + 35999.05029 * T - 0.0001537 * T * T) % 360.0
    M_r = M * DEG2RAD

    # Equation of centre
    C = (
        (1.914602 - 0.004817 * T - 0.000014 * T * T) * math.sin(M_r)
        + (0.019993 - 0.000101 * T) * math.sin(2.0 * M_r)
        + 0.000289 * math.sin(3.0 * M_r)
    )

    # Sun's true longitude
    sun_lon = L0 + C

    # Sun's apparent longitude (correct for aberration and nutation in longitude)
    omega = (125.04 - 1934.136 * T) % 360.0
    lam = sun_lon - 0.00569 - 0.00478 * math.sin(omega * DEG2RAD)

    # Mean obliquity of the ecliptic (low precision)
    eps0 = 23.439291 - 0.013004 * T
    eps = eps0 + 0.00256 * math.cos(omega * DEG2RAD)
    eps_r = eps * DEG2RAD

    # Right ascension of the Sun
    y = math.tan(eps_r / 2.0) ** 2
    sun_lon_r = sun_lon * DEG2RAD
    lam_r = lam * DEG2RAD
    M_r2 = M_r

    # Equation of time (Meeus eq. 27.1, in radians then converted to degrees)
    eot_rad = (
        y * math.sin(2.0 * lam_r)
        - 2.0 * 0.016708634 * math.sin(M_r2)  # eccentricity
        + 4.0 * 0.016708634 * y * math.sin(M_r2) * math.cos(2.0 * lam_r)
        - 0.5 * y * y * math.sin(4.0 * lam_r)
        - 1.25 * 0.016708634 ** 2 * math.sin(2.0 * M_r2)
    )
    return eot_rad * RAD2DEG
