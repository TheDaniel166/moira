"""
Moira -- primary_directions/fixed_stars.py
Explicit narrow fixed-star primitives for the primary-directions subsystem.

Boundary
--------
Owns the service-supplied sovereign fixed-star target wrapper and the minimal
projection needed to turn catalog-backed star identities into explicit
primary-direction promissor points.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..stars import star_at, star_name_resolves

__all__ = [
    "PrimaryDirectionFixedStarTarget",
    "resolve_primary_direction_fixed_star_point",
]


@dataclass(frozen=True, slots=True)
class PrimaryDirectionFixedStarTarget:
    star_name: str

    def __post_init__(self) -> None:
        if not self.star_name:
            raise ValueError("PrimaryDirectionFixedStarTarget requires a star_name")
        if not star_name_resolves(self.star_name):
            raise ValueError(
                f"PrimaryDirectionFixedStarTarget requires a sovereign catalog star: {self.star_name!r}"
            )

    @property
    def name(self) -> str:
        return self.star_name


def resolve_primary_direction_fixed_star_point(
    target: PrimaryDirectionFixedStarTarget,
    *,
    jd_tt: float,
) -> tuple[str, float, float]:
    star = star_at(target.star_name, jd_tt)
    return star.name, star.longitude, star.latitude
