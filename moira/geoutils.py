"""
Moira — geoutils.py
Geographic Utilities Oracle: governs shared geographic helper functions for
path-solving modules across the Moira system.

Purpose: provides common geographic calculations, coordinate transformations,
and path-solving utilities used by multiple astrological engines that require
geographic computation (astrocartography, eclipse paths, occultation tracks).

Boundary: owns geographic coordinate utilities, distance calculations, and
path interpolation functions. Delegates specific astrological calculations
to the modules that import these utilities. Does not own any astrological
interpretation or display formatting.

Import-time side effects: None

External dependency assumptions:
    - No external geographic databases required
    - Pure computational module using standard geodetic formulas

Public surface / exports:
    geographic_distance()     — distance calculations between coordinates
    coordinate_interpolation() — path interpolation utilities
    geodetic_transforms()     — coordinate system conversions
    (Shared utilities for astrocartography, eclipse, and occultation modules)
"""

import math

from .eclipse_geometry import EARTH_RADIUS_KM

EARTH_KM_PER_DEG_LAT = 2.0 * math.pi * EARTH_RADIUS_KM / 360.0


def wrap_longitude_deg(longitude: float) -> float:
    """Wrap longitude into the established local range (-180, 180]."""

    wrapped = ((longitude + 180.0) % 360.0) - 180.0
    if wrapped == -180.0:
        return 180.0
    return wrapped


def offset_geographic_km(
    latitude: float,
    longitude: float,
    north_km: float,
    east_km: float,
) -> tuple[float, float]:
    """Offset a geographic point by north/east distances in kilometres."""

    lat = latitude + (north_km / EARTH_KM_PER_DEG_LAT)
    lat = max(-89.5, min(89.5, lat))
    cos_lat = math.cos(math.radians(lat))
    if abs(cos_lat) < 1e-9:
        lon = longitude
    else:
        lon = longitude + (east_km / (EARTH_KM_PER_DEG_LAT * cos_lat))
    return lat, wrap_longitude_deg(lon)


def sample_interval(jd_start: float, jd_end: float, sample_count: int) -> tuple[float, ...]:
    """Return evenly spaced samples across an interval, inclusive."""

    if sample_count == 1 or abs(jd_end - jd_start) < 1e-12:
        return ((jd_start + jd_end) / 2.0,)
    step = (jd_end - jd_start) / float(sample_count - 1)
    return tuple(jd_start + i * step for i in range(sample_count))
