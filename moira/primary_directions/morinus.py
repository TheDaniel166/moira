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

__all__ = [
    "MorinusAspectContext",
    "project_morinus_aspect_point",
]


@dataclass(frozen=True, slots=True)
class MorinusAspectContext:
    source_name: str
    maximum_latitude: float
    moving_toward_maximum: bool

    def __post_init__(self) -> None:
        if not self.source_name:
            raise ValueError("MorinusAspectContext requires a source_name")
        if abs(self.maximum_latitude) <= 1e-9:
            raise ValueError("MorinusAspectContext requires a non-zero maximum_latitude")


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
    lam_p = math.radians(longitude % 360.0)
    delta_p = math.radians(latitude)
    delta_max = math.radians(maximum_latitude)
    if abs(math.sin(delta_max)) <= 1e-12 or abs(math.tan(delta_max)) <= 1e-12:
        raise ValueError("Morinus aspect projection requires a usable maximum_latitude")

    k = 1.0 if moving_toward_maximum else -1.0
    aspect = math.radians(aspect_angle)
    lam_prime = math.asin(max(-1.0, min(1.0, math.sin(delta_p) / math.sin(delta_max)))) + k * aspect
    ae = math.asin(max(-1.0, min(1.0, math.tan(delta_p) / math.tan(delta_max))))
    ag = math.atan(math.cos(delta_max) * math.tan(lam_prime))
    delta = math.asin(max(-1.0, min(1.0, math.sin(lam_prime) * math.sin(delta_max))))
    lam = (lam_p + k * (ag - ae)) % (2.0 * math.pi)
    return math.degrees(lam), math.degrees(delta)
