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

from __future__ import annotations

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
    """Apply a local north/east tangent vector on Moira's Earth sphere.

    The vector magnitude is the great-circle arc length and its direction is
    the initial bearing measured clockwise from geographic north.  This is the
    spherical exponential map: it remains defined when a step crosses a pole,
    unlike independent latitude/longitude increments.

    Longitude has no geometric meaning at an exact pole, so pole results use
    the deterministic canonical longitude ``0.0``.
    """

    values = {
        "latitude": latitude,
        "longitude": longitude,
        "north_km": north_km,
        "east_km": east_km,
    }
    for name, value in values.items():
        if not math.isfinite(value):
            raise ValueError(f"{name} must be finite")
    if not -90.0 <= latitude <= 90.0:
        raise ValueError("latitude must be in [-90, 90]")

    distance_km = math.hypot(north_km, east_km)
    if distance_km == 0.0:
        if abs(latitude) == 90.0:
            return latitude, 0.0
        return latitude, wrap_longitude_deg(longitude)

    angular_distance = distance_km / EARTH_RADIUS_KM
    latitude_rad = math.radians(latitude)
    canonical_longitude = 0.0 if abs(latitude) == 90.0 else wrap_longitude_deg(longitude)
    longitude_rad = math.radians(canonical_longitude)

    sin_latitude = math.sin(latitude_rad)
    cos_latitude = math.cos(latitude_rad)
    sin_longitude = math.sin(longitude_rad)
    cos_longitude = math.cos(longitude_rad)
    sin_distance = math.sin(angular_distance)
    cos_distance = math.cos(angular_distance)

    north_fraction = north_km / distance_km
    east_fraction = east_km / distance_km
    position_x = cos_latitude * cos_longitude
    position_y = cos_latitude * sin_longitude
    position_z = sin_latitude
    tangent_x = (
        -north_fraction * sin_latitude * cos_longitude
        - east_fraction * sin_longitude
    )
    tangent_y = (
        -north_fraction * sin_latitude * sin_longitude
        + east_fraction * cos_longitude
    )
    tangent_z = north_fraction * cos_latitude

    destination_x = cos_distance * position_x + sin_distance * tangent_x
    destination_y = cos_distance * position_y + sin_distance * tangent_y
    destination_z = cos_distance * position_z + sin_distance * tangent_z
    horizontal = math.hypot(destination_x, destination_y)

    pole_tolerance = 8.0 * math.ulp(1.0)
    if horizontal <= pole_tolerance * max(1.0, abs(destination_z)):
        return math.copysign(90.0, destination_z), 0.0

    destination_latitude = math.degrees(math.atan2(destination_z, horizontal))
    destination_longitude = wrap_longitude_deg(
        math.degrees(math.atan2(destination_y, destination_x))
    )
    return destination_latitude, destination_longitude


def sample_interval(jd_start: float, jd_end: float, sample_count: int) -> tuple[float, ...]:
    """Return evenly spaced samples across an interval, inclusive."""

    if sample_count == 1 or abs(jd_end - jd_start) < 1e-12:
        return ((jd_start + jd_end) / 2.0,)
    step = (jd_end - jd_start) / float(sample_count - 1)
    return tuple(jd_start + i * step for i in range(sample_count))
