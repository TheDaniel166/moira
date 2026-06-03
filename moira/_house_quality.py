"""
Private helper functions for house-cycle quality checks.

This module keeps two validation layers distinct:

1. Geometric ordering:
   The cusp cycle must move strictly forward from the Ascendant.
2. Practical distortion:
   Even an ordered cycle may be too crushed or ballooned to be useful.

The distortion metric is computed over all twelve house widths so it does not
presuppose opposition symmetry.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class HouseDistortionProfile:
    """Measured width/distortion profile for a 12-cusp house figure."""

    widths: tuple[float, ...]
    min_width: float
    max_width: float
    distortion_ratio: float
    narrow_house: int
    wide_house: int


def strictly_ordered_cusp_cycle(
    cusps: tuple[float, ...] | list[float],
    asc: float,
    *,
    ordering_tolerance: float = 1e-7,
) -> bool:
    """
    Return True only when the cusp cycle moves strictly forward from Ascendant.

    ``cusps`` must be in house order with House 1 / Ascendant first.
    """
    if len(cusps) != 12:
        raise ValueError("cusps must contain exactly 12 house longitudes")

    unwrapped = [0.0] + [((cusp - asc) % 360.0) for cusp in cusps[1:]]
    return all(
        unwrapped[i + 1] - unwrapped[i] > ordering_tolerance
        for i in range(11)
    )


def house_distortion_profile(cusps: tuple[float, ...] | list[float]) -> HouseDistortionProfile:
    """
    Measure 12-house width distortion without presupposing symmetry.

    Widths are computed in house order:
        w_i = (lambda_{i+1} - lambda_i) mod 360
    with the final width wrapping from House 12 back to House 1.
    """
    if len(cusps) != 12:
        raise ValueError("cusps must contain exactly 12 house longitudes")

    widths = tuple(
        (cusps[(i + 1) % 12] - cusps[i]) % 360.0
        for i in range(12)
    )
    min_width = min(widths)
    max_width = max(widths)
    narrow_house = widths.index(min_width) + 1
    wide_house = widths.index(max_width) + 1
    distortion_ratio = float("inf") if min_width == 0.0 else max_width / min_width
    return HouseDistortionProfile(
        widths=widths,
        min_width=min_width,
        max_width=max_width,
        distortion_ratio=distortion_ratio,
        narrow_house=narrow_house,
        wide_house=wide_house,
    )


def practically_admissible_cusp_cycle(
    cusps: tuple[float, ...] | list[float],
    *,
    rho_max: float,
) -> tuple[bool, HouseDistortionProfile]:
    """Return practical admissibility under a distortion-ratio ceiling."""
    if rho_max < 1.0:
        raise ValueError("rho_max must be >= 1.0")

    profile = house_distortion_profile(cusps)
    return profile.distortion_ratio <= rho_max, profile
