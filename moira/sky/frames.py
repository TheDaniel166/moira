"""
moira.sky.frames — Coordinate Frame Transforms
===============================================
Strict astronomy API for reference frame transformations, rotation
matrices, and the equatorial-to-horizontal projection.

Reference frames
----------------
ICRF        International Celestial Reference Frame. Equatorial, J2000.
            Right ascension and declination, or Cartesian (x, y, z).

Ecliptic    Mean or true ecliptic longitude and latitude.
            Mean: ecliptic of date without nutation.
            True: full precession + nutation applied via rotation matrix.

Equatorial  Right ascension / declination in the frame of date.

Horizontal  Azimuth and altitude as seen from the observer.
            Azimuth convention: 0° = North, 90° = East (navigational).

Type aliases
------------
Vec3  tuple[float, float, float]   Cartesian triple or angular triple
Mat3  tuple of three Vec3 rows     3×3 rotation matrix

Direct frame transforms
-----------------------
icrf_to_ecliptic          ICRF xyz → ecliptic lon/lat using supplied obliquity
icrf_to_true_ecliptic     ICRF xyz → true ecliptic lon/lat (precession+nutation)
true_ecliptic_latitude    ecliptic latitude only from ICRF xyz (with P+N)
icrf_to_equatorial        ICRF xyz → RA/Dec (radians)
ecliptic_to_equatorial    ecliptic lon/lat → RA/Dec
equatorial_to_ecliptic    RA/Dec → ecliptic lon/lat
equatorial_to_horizontal  RA/Dec → azimuth/altitude
horizontal_to_equatorial  azimuth/altitude → RA/Dec

Rotation matrices
-----------------
precession_matrix_equatorial  IAU 2006 precession matrix at jd_tt
nutation_matrix_equatorial    IAU 2000A nutation matrix at jd_tt
rot_x / rot_y / rot_z         single-axis rotation matrices (astronomical sign)

General transform
-----------------
cotrans_sp       general spherical coordinate transform via rotation matrix
aberration_correction  annual aberration (coordinates module, geometric)

Utility
-------
normalize_degrees      fold angle into [0, 360)
angular_distance       unsigned shortest arc between two angles (degrees)
signed_angular_distance  signed angular difference

Solar time
----------
equation_of_time  solar time correction in minutes (jd_tt)

Horizon frame — batch
---------------------
LocalSpacePosition   azimuth, altitude, is_above, compass_direction()
local_space_positions  batch equatorial → horizon for a set of bodies

Notes
-----
``local_space_from_chart`` is explicitly excluded from moira.sky.  It is
an application-layer function that couples to the chart object; it does
not belong in a strict astronomy surface.
"""

from moira.coordinates import (
    Mat3,
    Vec3,
    aberration_correction,
    angular_distance,
    cotrans_sp,
    ecliptic_to_equatorial,
    equation_of_time,
    equatorial_to_ecliptic,
    equatorial_to_horizontal,
    horizontal_to_equatorial,
    icrf_to_ecliptic,
    icrf_to_equatorial,
    icrf_to_true_ecliptic,
    normalize_degrees,
    nutation_matrix_equatorial,
    precession_matrix_equatorial,
    rot_x,
    rot_y,
    rot_z,
    signed_angular_distance,
    true_ecliptic_latitude,
)
from moira.local_space import (
    LocalSpacePosition,
    local_space_positions,
)

__all__ = [
    # Type aliases
    "Vec3",
    "Mat3",
    # ICRF → other frames
    "icrf_to_ecliptic",
    "icrf_to_true_ecliptic",
    "true_ecliptic_latitude",
    "icrf_to_equatorial",
    # Frame-to-frame
    "ecliptic_to_equatorial",
    "equatorial_to_ecliptic",
    # Horizontal projection
    "equatorial_to_horizontal",
    "horizontal_to_equatorial",
    # Rotation matrices
    "precession_matrix_equatorial",
    "nutation_matrix_equatorial",
    "rot_x",
    "rot_y",
    "rot_z",
    # General transform
    "cotrans_sp",
    "aberration_correction",
    # Utility
    "normalize_degrees",
    "angular_distance",
    "signed_angular_distance",
    # Solar time
    "equation_of_time",
    # Horizon frame — batch
    "LocalSpacePosition",
    "local_space_positions",
]
