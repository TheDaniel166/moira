"""Perspective sphere–spheroid disk geometry for planetary moon snapshots.

A ray is tangent to the spheroid when its line misses the origin by one unit
in coordinates scaled by the spheroid axes. On a tangent sky plane the
resulting quadratic is the projected limb. A spherical target centered on
that plane projects to a circle of radius tan(apparent angular radius).
"""

from math import asin, atan2, cos, degrees, hypot, inf, nextafter, radians, sin, sqrt, tan, ulp
from typing import Literal

from .constants import J2000, JULIAN_CENTURY
from .coordinates import Vec3, vec_norm, vec_unit
from ._planetary_moon_data import MoonSystem

DiskOverlap = Literal["clear", "contact", "partial", "contained"]

# Roundoff allowance in the dimensionless tangent-plane coordinates.
_CONTACT_TOL = 64.0 * ulp(1.0)


def _dot(a: Vec3, b: Vec3) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a: Vec3, b: Vec3) -> Vec3:
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _sky_axes(direction: Vec3) -> tuple[Vec3, Vec3]:
    xy = hypot(direction[0], direction[1])
    east = (-direction[1] / xy, direction[0] / xy, 0.0) if xy else (0.0, 1.0, 0.0)
    return east, _cross(direction, east)


def sky_offsets_arcsec(planet: Vec3, moon: Vec3) -> tuple[float, float]:
    """Project the moon onto the planet-centered ICRF east and north axes."""
    sight = vec_unit(planet)
    east, north = _sky_axes(sight)
    depth = _dot(sight, moon)
    return degrees(atan2(_dot(east, moon), depth)) * 3600.0, degrees(atan2(_dot(north, moon), depth)) * 3600.0


def angle_between(a: Vec3, b: Vec3) -> float:
    """Return the unsigned angle in radians, including near alignment."""
    a, b = vec_unit(a), vec_unit(b)
    return atan2(vec_norm(_cross(a, b)), _dot(a, b))


def planet_pole(system: MoonSystem, epoch_tdb: float, offset_days: float) -> Vec3:
    """Evaluate the IAU spin axis in ICRF using the pinned NAIF text PCK."""
    centuries = ((epoch_tdb - J2000) + offset_days) / JULIAN_CENTURY
    ra = system.pole_ra_deg[0] + centuries * system.pole_ra_deg[1]
    dec = system.pole_dec_deg[0] + centuries * system.pole_dec_deg[1]
    for origin, rate, ra_amp, dec_amp in system.pole_periodic:
        phase = radians(origin + rate * centuries)
        ra += ra_amp * sin(phase)
        dec += dec_amp * cos(phase)
    ra, dec = radians(ra), radians(dec)
    return cos(dec) * cos(ra), cos(dec) * sin(ra), sin(dec)


def _limb_distance(x: float, y: float, a: float, b: float) -> float:
    """Signed distance from a point to a centered ellipse with a >= b."""
    x, y, b = abs(x) / a, abs(y) / a, b / a
    inside = hypot(x, y / b) < 1.0
    difference = (1.0 - b) * (1.0 + b)
    if difference == 0.0:
        return (hypot(x, y) - 1.0) * a
    if x == 0.0:
        distance = abs(y - b)
    elif y == 0.0:
        nearest_x = min(1.0, x / difference)
        distance = hypot(nearest_x - x, b * sqrt(1.0 - nearest_x**2))
    else:
        # Shift the Lagrange multiplier by the minor axis squared so it
        # remains positive. The ellipse equation decreases on this bracket.
        low, high = b * y, hypot(x, b * y)
        for _ in range(64):
            middle = (low + high) / 2.0
            if middle == low or middle == high:
                break
            if hypot(x / (difference + middle), b * y / middle) > 1.0:
                low = middle
            else:
                high = middle
        root = (low + high) / 2.0
        distance = hypot(x / (difference + root) - x, b * (b * y / root) - y)
    return (-distance if inside else distance) * a


def disk_contact_margins(
    planet: Vec3,
    pole: Vec3,
    planet_radii: tuple[float, float],
    target: Vec3,
    target_radius: float,
) -> tuple[float, float]:
    """Return signed external and internal contact margins on the tangent plane."""
    equatorial, polar = planet_radii
    target_angle = asin(target_radius / vec_norm(target))
    planet_bound = asin(equatorial / vec_norm(planet))
    separation = angle_between(planet, target)
    radius = tan(target_angle)
    if separation > planet_bound + target_angle + _CONTACT_TOL:
        # Outside the bounding sphere, this positive lower bound avoids
        # projecting a spheroid that may be behind the tangent plane.
        margin = max(separation - planet_bound - target_angle, nextafter(_CONTACT_TOL, inf))
        return margin, margin + 2.0 * radius

    sight = vec_unit(target)
    east, north = _sky_axes(sight)

    def scale_for_spheroid(vector: Vec3) -> Vec3:
        # Isotropic equatorial scaling followed by a stretch along the pole.
        stretch = _dot(vector, pole) * (equatorial / polar - 1.0)
        return tuple((axis + stretch * component) / equatorial
                     for axis, component in zip(vector, pole))

    scaled_planet = scale_for_spheroid(planet)
    ray, x_axis, y_axis = map(scale_for_spheroid, (sight, east, north))
    ray_cross, x_cross, y_cross = (_cross(scaled_planet, axis) for axis in (ray, x_axis, y_axis))
    xx = _dot(x_cross, x_cross) - _dot(x_axis, x_axis)
    xy = _dot(x_cross, y_cross) - _dot(x_axis, y_axis)
    yy = _dot(y_cross, y_cross) - _dot(y_axis, y_axis)
    x = _dot(x_cross, ray_cross) - _dot(x_axis, ray)
    y = _dot(y_cross, ray_cross) - _dot(y_axis, ray)
    constant = _dot(ray_cross, ray_cross) - _dot(ray, ray)

    determinant = xx * yy - xy * xy
    center_x = (xy * y - yy * x) / determinant
    center_y = (xy * x - xx * y) / determinant
    level = -(constant + x * center_x + y * center_y)
    large = (xx + yy + hypot(xx - yy, 2.0 * xy)) / 2.0
    major, minor = sqrt(level * large / determinant), sqrt(level / large)
    rotation = atan2(2.0 * xy, xx - yy) / 2.0
    cr, sr = cos(rotation), sin(rotation)
    limb = _limb_distance(center_x * sr - center_y * cr,
                          center_x * cr + center_y * sr, major, minor)
    return limb - radius, limb + radius


def classify_disk_margins(margins: tuple[float, float]) -> DiskOverlap:
    """Apply the nominal finite-disk classification to signed contact margins."""

    outer, inner = margins
    if min(abs(outer), abs(inner)) <= _CONTACT_TOL:
        return "contact"
    if outer > 0.0:
        return "clear"
    return "contained" if inner < 0.0 else "partial"


def disk_overlap(
    planet: Vec3,
    pole: Vec3,
    planet_radii: tuple[float, float],
    target: Vec3,
    target_radius: float,
) -> DiskOverlap:
    """Classify a target sphere against an oblate planet in the same sky."""

    return classify_disk_margins(disk_contact_margins(planet, pole, planet_radii, target, target_radius))
