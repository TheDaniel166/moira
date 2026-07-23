"""Private solar apparent-disc geometry shared by global and map products."""

from __future__ import annotations

import math
from dataclasses import dataclass

from .constants import Body
from .eclipse_geometry import (
    MOON_RADIUS_KM,
    SUN_RADIUS_KM,
    angular_separation,
    apparent_radius,
)
from .planets import sky_position_at


@dataclass(frozen=True, slots=True)
class _SolarApparentDiscGeometry:
    """Vessel: Structured solar apparent disc geometry data."""
    separation_deg: float
    sun_radius_deg: float
    moon_radius_deg: float
    sun_altitude_deg: float
    sun_azimuth_deg: float
    moon_altitude_deg: float
    moon_azimuth_deg: float
    magnitude: float
    obscuration: float
    local_class: str


def _circle_overlap_fraction(
    sun_radius: float,
    moon_radius: float,
    separation: float,
) -> float:
    """Return the fraction of the apparent solar disc covered by the Moon."""

    if not all(
        math.isfinite(value)
        for value in (sun_radius, moon_radius, separation)
    ):
        raise ValueError("disc-overlap inputs must be finite")
    if sun_radius <= 0.0 or moon_radius <= 0.0:
        raise ValueError("disc radii must be positive")
    if separation < 0.0:
        raise ValueError("disc separation must be non-negative")
    if separation >= sun_radius + moon_radius:
        return 0.0
    if separation <= abs(sun_radius - moon_radius):
        if moon_radius >= sun_radius:
            return 1.0
        return (moon_radius / sun_radius) ** 2

    cos_sun = (
        separation * separation
        + sun_radius * sun_radius
        - moon_radius * moon_radius
    ) / (2.0 * separation * sun_radius)
    cos_moon = (
        separation * separation
        + moon_radius * moon_radius
        - sun_radius * sun_radius
    ) / (2.0 * separation * moon_radius)
    alpha = math.acos(max(-1.0, min(1.0, cos_sun)))
    beta = math.acos(max(-1.0, min(1.0, cos_moon)))
    radicand = (
        (-separation + sun_radius + moon_radius)
        * (separation + sun_radius - moon_radius)
        * (separation - sun_radius + moon_radius)
        * (separation + sun_radius + moon_radius)
    )
    lens_area = (
        sun_radius * sun_radius * alpha
        + moon_radius * moon_radius * beta
        - 0.5 * math.sqrt(max(0.0, radicand))
    )
    fraction = lens_area / (math.pi * sun_radius * sun_radius)
    return max(0.0, min(1.0, fraction))


def _topocentric_solar_disc_geometry(
    calculator,
    jd_ut1: float,
    latitude_deg: float,
    longitude_deg: float,
    elevation_m: float = 0.0,
) -> _SolarApparentDiscGeometry:
    """Evaluate exact apparent Sun/Moon disc overlap at one observer."""

    sun = sky_position_at(
        Body.SUN,
        jd_ut1,
        latitude_deg,
        longitude_deg,
        elevation_m,
        reader=calculator._reader,
    )
    moon = sky_position_at(
        Body.MOON,
        jd_ut1,
        latitude_deg,
        longitude_deg,
        elevation_m,
        reader=calculator._reader,
    )
    separation = angular_separation(
        sun.right_ascension,
        sun.declination,
        moon.right_ascension,
        moon.declination,
    )
    sun_radius = apparent_radius(SUN_RADIUS_KM, sun.distance)
    moon_radius = apparent_radius(MOON_RADIUS_KM, moon.distance)
    if separation >= sun_radius + moon_radius:
        magnitude = 0.0
        local_class = "none"
    elif separation <= abs(moon_radius - sun_radius):
        magnitude = moon_radius / sun_radius
        local_class = "total" if moon_radius >= sun_radius else "annular"
    else:
        magnitude = max(
            0.0,
            (sun_radius + moon_radius - separation) / (2.0 * sun_radius),
        )
        local_class = "partial"
    return _SolarApparentDiscGeometry(
        separation_deg=separation,
        sun_radius_deg=sun_radius,
        moon_radius_deg=moon_radius,
        sun_altitude_deg=sun.altitude,
        sun_azimuth_deg=sun.azimuth,
        moon_altitude_deg=moon.altitude,
        moon_azimuth_deg=moon.azimuth,
        magnitude=magnitude,
        obscuration=_circle_overlap_fraction(
            sun_radius,
            moon_radius,
            separation,
        ),
        local_class=local_class,
    )
