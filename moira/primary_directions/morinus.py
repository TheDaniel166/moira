"""
Moira -- primary_directions/morinus.py
Explicit Morinus aspect-plane primitives for the primary-directions subsystem.

Boundary
--------
Owns the formula-grade Morinus circle-of-aspects projection for explicit
aspectual promissors when the service layer supplies the path context that the
engine cannot derive from the natal chart alone.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real

__all__ = [
    "MorinusAspectContext",
    "project_morinus_aspect_point",
]


_DOMAIN_TOLERANCE = 1e-12


def _finite_real(value: object, *, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
        raise ValueError(f"Morinus aspect projection requires finite real {name}")
    return float(value)


def _checked_unit_argument(value: float, *, name: str) -> float:
    if value < -1.0 - _DOMAIN_TOLERANCE or value > 1.0 + _DOMAIN_TOLERANCE:
        raise ValueError(f"Morinus aspect projection has no real {name}")
    return max(-1.0, min(1.0, value))


@dataclass(frozen=True, slots=True)
class MorinusAspectContext:
    """Vessel: Contextual state for calculating Morinus aspectual projections."""
    source_name: str
    maximum_latitude: float
    moving_toward_maximum: bool

    def __post_init__(self) -> None:
        if not isinstance(self.source_name, str) or not self.source_name.strip():
            raise ValueError("MorinusAspectContext requires a non-empty string source_name")
        object.__setattr__(self, "source_name", self.source_name.strip())
        maximum_latitude = _finite_real(self.maximum_latitude, name="maximum_latitude")
        if abs(maximum_latitude) <= 1e-9 or abs(maximum_latitude) >= 90.0:
            raise ValueError("MorinusAspectContext requires maximum_latitude in (-90, 0) or (0, 90)")
        if not isinstance(self.moving_toward_maximum, bool):
            raise ValueError("MorinusAspectContext requires a boolean moving_toward_maximum")


def project_morinus_aspect_point(
    *,
    longitude: float,
    latitude: float,
    maximum_latitude: float,
    moving_toward_maximum: bool,
    aspect_angle: float,
) -> tuple[float, float]:
    """
    Morinus circle-of-aspects projection in ecliptical coordinates.

    Inputs:
    - longitude, latitude: current ecliptical coordinates of the source body
    - maximum_latitude: delta_max on the current node-to-node path segment
    - moving_toward_maximum: Morinus coefficient k = +1 when approaching
      maximum latitude, -1 when departing it
    - aspect_angle: signed aspect angle in degrees
    """
    longitude = _finite_real(longitude, name="longitude")
    latitude = _finite_real(latitude, name="latitude")
    maximum_latitude = _finite_real(maximum_latitude, name="maximum_latitude")
    aspect_angle = _finite_real(aspect_angle, name="aspect_angle")
    if not isinstance(moving_toward_maximum, bool):
        raise ValueError("Morinus aspect projection requires boolean moving_toward_maximum")
    if abs(latitude) > 90.0:
        raise ValueError("Morinus aspect projection requires latitude in [-90, 90]")
    if abs(maximum_latitude) <= 1e-9 or abs(maximum_latitude) >= 90.0:
        raise ValueError(
            "Morinus aspect projection requires maximum_latitude in (-90, 0) or (0, 90)"
        )
    if abs(latitude) > abs(maximum_latitude) + _DOMAIN_TOLERANCE:
        raise ValueError("Morinus aspect projection latitude exceeds its path maximum")
    if latitude * maximum_latitude < -_DOMAIN_TOLERANCE:
        raise ValueError("Morinus aspect projection latitude and path maximum have opposite signs")

    lam_p = math.radians(longitude % 360.0)
    delta_p = math.radians(latitude)
    delta_max = math.radians(maximum_latitude)
    if abs(math.sin(delta_max)) <= 1e-12 or abs(math.tan(delta_max)) <= 1e-12:
        raise ValueError("Morinus aspect projection requires a usable maximum_latitude")

    k = 1.0 if moving_toward_maximum else -1.0
    aspect = math.radians(aspect_angle)
    path_phase = math.asin(
        _checked_unit_argument(
            math.sin(delta_p) / math.sin(delta_max),
            name="path-phase solution",
        )
    )
    lam_prime = path_phase + k * aspect
    ae = math.asin(
        _checked_unit_argument(
            math.tan(delta_p) / math.tan(delta_max),
            name="equatorial-path solution",
        )
    )
    # atan(cos(delta_max) * tan(lambda')) is only the principal-branch
    # reduction of this ellipse-to-ecliptic angle.  atan2 retains the phase
    # quadrant across squares, trines, and opposition.
    ag = math.atan2(
        math.cos(delta_max) * math.sin(lam_prime),
        math.cos(lam_prime),
    )
    delta = math.asin(
        _checked_unit_argument(
            math.sin(lam_prime) * math.sin(delta_max),
            name="projected-latitude solution",
        )
    )
    lam = (lam_p + k * (ag - ae)) % (2.0 * math.pi)
    longitude_result = math.degrees(lam) % 360.0
    if math.isclose(longitude_result, 360.0, rel_tol=0.0, abs_tol=1e-12):
        longitude_result = 0.0
    return longitude_result, math.degrees(delta)
