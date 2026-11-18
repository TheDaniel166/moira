"""Common real rotation and celestial jets retained without box decorrelation."""
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SolarFrameBounds:
    """Celestial Sun/Moon jets and the same celestial-to-ITRF rotation jets.

    Rotation is a product of orthogonal real matrices. These are bounds on
    that shared rotation, not independent transforms for each source body.
    Derivatives use the request's UT1 offset in days. Source joins are named
    by the continuity flag and cannot silently supply a track derivative.
    """

    domain: object
    sun: tuple
    moon: tuple
    rotation: tuple
    continuous: bool
