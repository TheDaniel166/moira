"""Common-ray local visibility of two spherical discs above a horizon.

This static geometric calculation accepts caller-supplied *topocentric* unit
directions and apparent angular radii. It does not compute positions,
refraction, terrain, observer altitude, or event-wide visibility.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal, Sequence


Vector = tuple[float, float, float]


@dataclass(frozen=True)
class SolarDiscVisibility:
    """Local spherical-cap result, with all angles in radians.

    ``maximum_direction`` is the highest point of the common lens and may be
    on a limb. A ``visible`` result additionally carries a distinct strictly
    interior ``witness_direction`` above the horizon. Near floating-point
    degeneracy is reported as indeterminate rather than rounded to contact.
    """
    status: Literal["visible", "hidden", "disjoint", "tangent", "indeterminate"]
    maximum_altitude_rad: float | None
    maximum_direction: Vector | None
    witness_direction: Vector | None
    separation_margin_rad: float
    tolerance_rad: float
    margin_unit: Literal["rad"] = "rad"


def _dot(a: Vector, b: Vector) -> float:
    return math.fsum(x*y for x, y in zip(a, b))


def _cross(a: Vector, b: Vector) -> Vector:
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def _scale(a: Vector, k: float) -> Vector:
    return a[0]*k, a[1]*k, a[2]*k


def _add(a: Vector, b: Vector) -> Vector:
    return a[0]+b[0], a[1]+b[1], a[2]+b[2]


def _unit(value: Sequence[float], name: str) -> Vector:
    try:
        if len(value) != 3:
            raise ValueError
        xyz = tuple(float(x) for x in value)
        norm = math.hypot(*xyz)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite, nonzero 3-vector") from exc
    if not math.isfinite(norm) or norm == 0:
        raise ValueError(f"{name} must be a finite, nonzero 3-vector")
    return tuple(x / norm for x in xyz)  # type: ignore[return-value]


def _angle(a: Vector, b: Vector) -> float:
    return math.atan2(math.hypot(*_cross(a, b)), _dot(a, b))


def _normal(a: Vector) -> Vector:
    """Deterministic unit vector perpendicular to a."""
    axis = min(((1., 0., 0.), (0., 1., 0.), (0., 0., 1.)),
               key=lambda u: abs(_dot(a, u)))
    return _unit(_cross(a, axis), "perpendicular")


def solar_disc_visibility(
    sun_direction: Sequence[float], moon_direction: Sequence[float],
    zenith_direction: Sequence[float], sun_radius_rad: float, moon_radius_rad: float,
    *, tolerance_rad: float = 1e-12,
) -> SolarDiscVisibility:
    """Find the highest common solar/lunar ray relative to a geometric horizon.

    The closed caps use exact spherical angular geometry. A point or horizon
    tangency only counts as ``tangent`` when certified by a represented exact
    antipodal-hemisphere degeneracy; cases within ``tolerance_rad`` of other
    boundaries return ``indeterminate``. The binary64 numerical guard cannot
    be smaller than 1e-12 rad; it is not atmospheric refraction or a claim of
    physical observational accuracy.
    """
    sun = _unit(sun_direction, "sun_direction")
    moon = _unit(moon_direction, "moon_direction")
    zenith = _unit(zenith_direction, "zenith_direction")
    try:
        sr, mr, tol = float(sun_radius_rad), float(moon_radius_rad), float(tolerance_rad)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError("radii and tolerance must be finite angles") from exc
    if (not all(math.isfinite(x) for x in (sr, mr, tol)) or not 0 < sr <= math.pi/2
            or not 0 < mr <= math.pi/2 or not 1e-12 <= tol < 0.1):
        raise ValueError("radii must be in (0, pi/2], tolerance in [1e-12, 0.1)")
    sep = _angle(sun, moon)
    overlap = sr + mr - sep

    def result(status, alt=None, maximum=None, witness=None):
        return SolarDiscVisibility(status, alt, maximum, witness, overlap, tol)

    if overlap < -tol:
        return result("disjoint")
    # Opposite exact hemispheres intersect in a great circle; handle this
    # degenerate lens before generic near-external-tangency rejection.
    cross = _cross(sun, moon)
    sin_sep = math.hypot(*cross)
    if sin_sep == 0 and _dot(sun, moon) < 0 and sr == mr == math.pi/2:
        tangent = _add(zenith, _scale(sun, -_dot(zenith, sun)))
        if math.hypot(*tangent) == 0:
            return result("tangent", 0.0, _normal(sun))
        maximum = _unit(tangent, "great-circle maximum")
        altitude = math.asin(max(-1.0, min(1.0, _dot(zenith, maximum))))
        return result("tangent", altitude, maximum)
    if abs(overlap) <= tol:
        return result("indeterminate")
    internal = abs(sr - mr)
    # Near an internal tangency the candidate topology itself is uncertain.
    if sep != 0 and abs(sep - internal) <= tol:
        return result("indeterminate")
    if sin_sep != 0 and sin_sep < 16 * math.ulp(1.0):
        return result("indeterminate")

    candidates: list[Vector] = []
    uncertain = False

    def add_if_inside(p: Vector, a: Vector, ar: float) -> None:
        nonlocal uncertain
        margin = ar - _angle(a, p)
        if margin > tol:
            candidates.append(p)
        elif margin >= -tol:
            uncertain = True

    # Unconstrained zenith and cap centers give interior candidates.
    sun_zenith, moon_zenith = sr-_angle(sun, zenith), mr-_angle(moon, zenith)
    if min(sun_zenith, moon_zenith) > tol:
        candidates.append(zenith)
    elif min(sun_zenith, moon_zenith) >= -tol:
        uncertain = True
    add_if_inside(sun, moon, mr)
    add_if_inside(moon, sun, sr)

    # Stationary maxima on either cap boundary. Cross products avoid loss
    # when a zenith is close to the cap center.
    for n, radius, other, other_radius in ((sun, sr, moon, mr), (moon, mr, sun, sr)):
        axis = _cross(n, zenith)
        if math.hypot(*axis) == 0:
            tangent = _normal(n)
        else:
            tangent = _unit(_cross(axis, n), "boundary tangent")
        boundary = _unit(_add(_scale(n, math.cos(radius)),
                              _scale(tangent, math.sin(radius))), "boundary point")
        if sep == 0 and radius == other_radius:
            candidates.append(boundary)
        else:
            add_if_inside(boundary, other, other_radius)

    # Intersections of the two boundary circles, when neither contains the
    # other. Difference-of-cosines identity avoids cancellation for small caps.
    if sep > internal + tol and sep < sr + mr - tol:
        w = _scale(cross, 1 / sin_sep)
        v = _cross(w, sun)
        numerator = (2 * math.sin((sr + mr)/2) * math.sin((sr - mr)/2)
                     + math.cos(sr) * 2 * math.sin(sep/2)**2)
        b = numerator / sin_sep
        h2 = (math.sin(sr)-abs(b)) * (math.sin(sr)+abs(b))
        if h2 <= 0 or not math.isfinite(h2):
            return result("indeterminate")
        base = _add(_scale(sun, math.cos(sr)), _scale(v, b))
        height = math.sqrt(h2)
        for sign in (-1, 1):
            candidates.append(_unit(_add(base, _scale(w, sign*height)), "circle intersection"))
    if not candidates or uncertain:
        return result("indeterminate")
    maximum = max(candidates, key=lambda p: _dot(zenith, p))
    altitude = math.asin(max(-1.0, min(1.0, _dot(zenith, maximum))))
    if abs(altitude) <= tol:
        return result("indeterminate", altitude, maximum)
    if altitude < 0:
        return result("hidden", altitude, maximum)

    # Construct a strict lens-interior direction on the center-to-center arc.
    # A positive combination of that direction with the maximum stays in both
    # convex hemispherical cones. Verify strict angular and horizon clearances.
    if sep == 0:
        interior = sun
    else:
        along = _unit(_cross(_scale(cross, 1 / sin_sep), sun), "center arc")
        lo, hi = max(0.0, sep-mr), min(sr, sep)
        arc = (lo+hi)/2
        interior = _unit(_add(_scale(sun, math.cos(arc)),
                              _scale(along, math.sin(arc))), "interior")
    for k in range(1, 54):
        weight = 2.0**-k
        witness = _unit(_add(_scale(maximum, 1-weight), _scale(interior, weight)), "witness")
        horizon = math.asin(max(-1.0, min(1.0, _dot(zenith, witness))))
        if (sr-_angle(sun, witness) > tol and mr-_angle(moon, witness) > tol
                and horizon > tol):
            return result("visible", altitude, maximum, witness)
    return result("indeterminate", altitude, maximum)
