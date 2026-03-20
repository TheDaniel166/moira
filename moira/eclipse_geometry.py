"""
Moira — eclipse_geometry.py
The Geometry Engine of Shadow and Light: governs pure geometric computation of
eclipse shadow radii, apparent angular radii, parallax values, and umbral/
penumbral magnitudes for both solar and lunar eclipse classification.

Boundary: owns angular separation, apparent radii, shadow radii (umbra and
penumbra), parallax formulas (lunar and solar), topocentric near-Moon radius,
shadow-axis offset, and umbral/penumbral magnitude calculations. Delegates
nothing — all computation is pure math using stdlib only. Does not own eclipse
search, contact timing, canon lookup, or any state management.

Public surface:
    angular_separation, lunar_parallax, apparent_radius, solar_parallax,
    topocentric_near_moon_radius, umbra_radius, penumbra_radius,
    shadow_axis_offset_deg, lunar_umbral_magnitude, lunar_penumbral_magnitude,
    EARTH_RADIUS_KM, SUN_RADIUS_KM, MOON_RADIUS_KM

Import-time side effects: None

External dependency assumptions:
    - stdlib math only; no third-party packages required.
"""

import math


EARTH_RADIUS_KM = 6378.137
SUN_RADIUS_KM = 696_340.0
MOON_RADIUS_KM = 1_737.4


def angular_separation(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """
    Spherical angular separation between two ecliptic points (degrees).

    Applies the spherical law of cosines to ecliptic longitude/latitude pairs,
    clamping the cosine argument to [-1, 1] to guard against floating-point
    rounding outside the valid domain of acos.

    Parameters:
        lon1: Ecliptic longitude of the first point in degrees.
        lat1: Ecliptic latitude of the first point in degrees.
        lon2: Ecliptic longitude of the second point in degrees.
        lat2: Ecliptic latitude of the second point in degrees.

    Returns:
        Angular separation in degrees, in the range [0, 180].
    """
    dl = abs(lon1 - lon2)
    if dl > 180.0:
        dl = 360.0 - dl
    c = (
        math.sin(math.radians(lat1)) * math.sin(math.radians(lat2))
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.cos(math.radians(dl))
    )
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def lunar_parallax(moon_dist_km: float) -> float:
    """
    Horizontal parallax of the Moon in degrees (Meeus Eq. 40.1).

    Parameters:
        moon_dist_km: Geocentric distance to the Moon in kilometres.

    Returns:
        Equatorial horizontal parallax of the Moon in degrees.
    """
    return math.degrees(math.asin(EARTH_RADIUS_KM / moon_dist_km))


def apparent_radius(physical_radius_km: float, distance_km: float) -> float:
    """
    Apparent angular radius of a body in degrees.

    Parameters:
        physical_radius_km: Physical (equatorial) radius of the body in kilometres.
        distance_km: Geocentric distance to the body in kilometres.

    Returns:
        Apparent angular radius in degrees.
    """
    return math.degrees(math.asin(physical_radius_km / distance_km))


def solar_parallax(sun_dist_km: float) -> float:
    """
    Equatorial horizontal parallax of the Sun in degrees.

    Parameters:
        sun_dist_km: Geocentric distance to the Sun in kilometres.

    Returns:
        Equatorial horizontal parallax of the Sun in degrees.
    """
    return math.degrees(math.asin(EARTH_RADIUS_KM / sun_dist_km))


def topocentric_near_moon_radius(moon_parallax: float) -> float:
    """
    Approximate the Moon's apparent radius for an observer on Earth's near side.

    This is the minimal Earth-scale correction needed to separate ordinary
    annular eclipses from hybrid events in a global classifier.
    """
    moon_dist = EARTH_RADIUS_KM / math.sin(math.radians(moon_parallax))
    near_dist = max(moon_dist - EARTH_RADIUS_KM, MOON_RADIUS_KM + 1.0)
    return apparent_radius(MOON_RADIUS_KM, near_dist)


def umbra_radius(sun_dist_km: float, moon_dist_km: float) -> float:
    """
    Earth umbral shadow apparent radius at the Moon's distance (degrees).

    Uses the Danjon-style lunar-eclipse shadow convention adopted by NASA:
    Ru = 1.01 * Pm - Ss + Ps
    where Pm is lunar horizontal parallax, Ss is solar semidiameter,
    and Ps is solar parallax.
    """
    pm = lunar_parallax(moon_dist_km)
    ss = apparent_radius(SUN_RADIUS_KM, sun_dist_km)
    ps = solar_parallax(sun_dist_km)
    return max(0.0, 1.01 * pm - ss + ps)


def penumbra_radius(sun_dist_km: float, moon_dist_km: float) -> float:
    """
    Earth penumbral shadow apparent radius at the Moon's distance (degrees).

    Uses the Danjon-style lunar-eclipse shadow convention adopted by NASA:
    Rp = 1.01 * Pm + Ss + Ps
    where Pm is lunar horizontal parallax, Ss is solar semidiameter,
    and Ps is solar parallax.
    """
    pm = lunar_parallax(moon_dist_km)
    ss = apparent_radius(SUN_RADIUS_KM, sun_dist_km)
    ps = solar_parallax(sun_dist_km)
    return 1.01 * pm + ss + ps


def shadow_axis_offset_deg(angular_sep: float) -> float:
    """Angular offset from exact opposition for the lunar shadow-axis geometry."""
    return abs(angular_sep - 180.0)


def lunar_umbral_magnitude(
    shadow_radius_deg: float,
    moon_radius_deg: float,
    shadow_axis_offset_deg_value: float,
) -> float:
    """Umbral magnitude for a lunar eclipse."""
    return (shadow_radius_deg + moon_radius_deg - shadow_axis_offset_deg_value) / (
        2.0 * moon_radius_deg
    )


def lunar_penumbral_magnitude(
    penumbra_radius_deg: float,
    moon_radius_deg: float,
    shadow_axis_offset_deg_value: float,
) -> float:
    """Penumbral magnitude for a lunar eclipse."""
    return (penumbra_radius_deg + moon_radius_deg - shadow_axis_offset_deg_value) / (
        2.0 * moon_radius_deg
    )
