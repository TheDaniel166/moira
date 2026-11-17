"""Independent, explicitly selected lunar-shadow geometric observables.

These pure-vector models do not select ephemerides, time scales, atmosphere or
greatest-eclipse epochs.  Vectors point from Earth's centre to the Sun and Moon
and must share a frame, distance unit (km), and caller-selected epoch policy.
Neither model changes the legacy eclipse or NASA-compatibility calculations.

``danjon_angular_shadow`` compares angular circles using Danjon's traditional
shadow-radius approximation. ``spherical_cone_shadow`` compares the Moon's
sphere with tangent cones from static, spherical Sun and Earth models.  The
latter is a distinct sensitivity model, not NASA's Danjon prescription.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal, Sequence

from .constants import EARTH_RADIUS_KM, MOON_RADIUS_KM, SUN_RADIUS_KM


class LunarShadowDomainError(ValueError):
    """Input is invalid or outside a model's explicitly supported domain."""


@dataclass(frozen=True)
class LunarShadowGeometry:
    """Immutable phase clearances with an explicitly identified unit.

    Positive penumbral and umbral margins mean positive overlap; positive
    total margin means complete umbral containment. Zero denotes tangency.
    Angular margins are in radians; cone margins are signed distances in km.
    For the cone, they measure the infinite positive nappe. The supported
    downstream domain makes their signs equal to those of the physical
    truncated-cone phase predicates. They are not truncated-cone distances.
    Gamma is unsigned physical axis distance divided by the unscaled Earth
    radius. Angular magnitudes are provided only for the angular policy.
    """
    policy: Literal["danjon_angular", "static_finite_cone"]
    margin_unit: Literal["rad", "km"]
    axis_distance_km: float
    gamma: float
    separation_rad: float
    penumbral_margin: float
    umbral_margin: float
    total_margin: float
    penumbral_magnitude: float | None
    umbral_magnitude: float | None


def _vector(value: Sequence[float], name: str) -> tuple[float, float, float]:
    try:
        if len(value) != 3:
            raise LunarShadowDomainError(f"{name} must have three components")
        result = tuple(float(component) for component in value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise LunarShadowDomainError(f"{name} must contain three finite numbers") from exc
    if not all(math.isfinite(component) for component in result):
        raise LunarShadowDomainError(f"{name} must contain three finite numbers")
    return result  # type: ignore[return-value]


def _input(sun_km: Sequence[float], moon_km: Sequence[float],
           earth_radius_km: float, sun_radius_km: float, moon_radius_km: float
           ) -> tuple[float, float, float, float, float, float, float, float]:
    sun, moon = _vector(sun_km, "sun_km"), _vector(moon_km, "moon_km")
    try:
        re, rs, rm = (float(earth_radius_km), float(sun_radius_km),
                      float(moon_radius_km))
    except (TypeError, ValueError, OverflowError) as exc:
        raise LunarShadowDomainError("radii must be finite positive numbers") from exc
    if not all(math.isfinite(x) and x > 0 for x in (re, rs, rm)):
        raise LunarShadowDomainError("radii must be finite positive numbers")
    s, d = math.hypot(*sun), math.hypot(*moon)
    if not math.isfinite(s) or not math.isfinite(d) or s <= rs + re or d <= re + rm:
        raise LunarShadowDomainError("Sun or Moon intersects Earth or distance is invalid")
    axis = tuple(-x / s for x in sun)
    try:
        z = math.fsum(moon[i] * axis[i] for i in range(3))
    except OverflowError as exc:
        raise LunarShadowDomainError("geometry is not finite") from exc
    cross = (moon[1] * axis[2] - moon[2] * axis[1],
             moon[2] * axis[0] - moon[0] * axis[2],
             moon[0] * axis[1] - moon[1] * axis[0])
    r = math.hypot(*cross)
    theta = math.atan2(r, z)
    if not all(math.isfinite(x) for x in (z, r, theta, r / re)):
        raise LunarShadowDomainError("geometry is not finite")
    return s, d, z, r, theta, re, rs, rm


def danjon_angular_shadow(
    sun_km: Sequence[float], moon_km: Sequence[float], *,
    earth_radius_km: float = EARTH_RADIUS_KM,
    sun_radius_km: float = SUN_RADIUS_KM,
    moon_radius_km: float = MOON_RADIUS_KM,
) -> LunarShadowGeometry:
    """Angular-disc Danjon approximation, with signed radians and magnitudes.

    Its shadow-radius 1.01 multiplier is the Danjon convention, combining an
    empirical atmospheric enlargement and an Earth-oblateness correction.
    """
    s, d, z, r, theta, re, rs, rm = _input(
        sun_km, moon_km, earth_radius_km, sun_radius_km, moon_radius_km)
    if z <= 0:
        raise LunarShadowDomainError("Moon must be on the antisolar side of Earth")
    pm, ps, ss, alpha = (math.asin(re / d), math.asin(re / s),
                         math.asin(rs / s), math.asin(rm / d))
    beta_pen = 1.01 * pm + ss + ps
    beta_umb = 1.01 * pm - ss + ps
    if alpha <= 0 or beta_umb <= 0 or beta_pen + alpha >= math.pi:
        raise LunarShadowDomainError("Danjon angular circles are outside their domain")
    pen = beta_pen + alpha - theta
    umb = beta_umb + alpha - theta
    total = beta_umb - alpha - theta
    pen_magnitude, umb_magnitude = pen / (2 * alpha), umb / (2 * alpha)
    if not all(math.isfinite(x) for x in (pen, umb, total, pen_magnitude, umb_magnitude)):
        raise LunarShadowDomainError("angular geometry is not finite")
    return LunarShadowGeometry("danjon_angular", "rad", r, r / re, theta,
                               pen, umb, total, pen_magnitude, umb_magnitude)


def _cone_clearance(t: float, r: float, sine: float, cosine: float) -> float:
    """Signed Euclidean clearance to a cone's boundary, positive inside."""
    k = sine / cosine
    if t + k * r <= 0:
        return -math.hypot(t, r)
    return sine * t - cosine * r


def spherical_cone_shadow(
    sun_km: Sequence[float], moon_km: Sequence[float], *,
    earth_radius_km: float = EARTH_RADIUS_KM,
    sun_radius_km: float = SUN_RADIUS_KM,
    moon_radius_km: float = MOON_RADIUS_KM,
    earth_radius_scale: float = 1.0,
) -> LunarShadowGeometry:
    """Static finite-source spherical tangent-cone shadow sensitivity model.

    Earth radius scaling is an explicit sensitivity parameter, not the Danjon
    angular formula. This model admits only a Moon wholly downstream of the
    effective Earth's bounding sphere; then the infinite-nappe overlap and
    containment predicates agree with the Earth-truncated physical cones.
    Umbral apex crossing is supported, including a sphere touching the tip.
    """
    s, d, z, r, theta, re, rs, rm = _input(
        sun_km, moon_km, earth_radius_km, sun_radius_km, moon_radius_km)
    try:
        scale = float(earth_radius_scale)
    except (TypeError, ValueError, OverflowError) as exc:
        raise LunarShadowDomainError("Earth radius scale must be finite and positive") from exc
    if not math.isfinite(scale) or scale <= 0:
        raise LunarShadowDomainError("Earth radius scale must be finite and positive")
    effective_re = re * scale
    if (not math.isfinite(effective_re) or effective_re <= 0 or effective_re >= rs
            or s <= rs + effective_re or z - rm < effective_re):
        raise LunarShadowDomainError("geometry lies outside the downstream cone domain")
    sp = (rs + effective_re) / s
    su = (rs - effective_re) / s
    if not 0 < su < 1 or not 0 < sp < 1:
        raise LunarShadowDomainError("cone angles cannot be represented")
    cp = math.sqrt((1 - sp) * (1 + sp))
    cu = math.sqrt((1 - su) * (1 + su))
    pen_t = z + effective_re / sp
    umb_t = effective_re / su - z
    pen_clearance = _cone_clearance(pen_t, r, sp, cp)
    umb_clearance = _cone_clearance(umb_t, r, su, cu)
    if not all(math.isfinite(x) for x in (pen_clearance, umb_clearance)):
        raise LunarShadowDomainError("cone geometry is not finite")
    return LunarShadowGeometry("static_finite_cone", "km", r, r / re, theta,
                               pen_clearance + rm, umb_clearance + rm,
                               umb_clearance - rm, None, None)
