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
from typing import Literal


_EXTREME_HOUSE_TOLERANCE = 1e-9


HouseCycleVerdict = Literal[
    "unordered",
    "ordered_but_impractical",
    "practically_admissible",
]


@dataclass(frozen=True, slots=True)
class HouseDistortionProfile:
    """Measured width/distortion profile for a 12-cusp house figure."""

    widths: tuple[float, ...]
    min_width: float
    max_width: float
    distortion_ratio: float
    narrow_houses: tuple[int, ...]
    wide_houses: tuple[int, ...]


def strictly_ordered_cusp_cycle(
    cusps: tuple[float, ...] | list[float],
    *,
    ordering_tolerance: float = 1e-7,
) -> bool:
    """
    Return True only when the cusp cycle moves strictly forward from Ascendant.

    ``cusps`` must be in house order with House 1 / Ascendant first.
    """
    if len(cusps) != 12:
        raise ValueError("cusps must contain exactly 12 house longitudes")

    unwrapped = [0.0] + [((cusp - cusps[0]) % 360.0) for cusp in cusps[1:]]
    gaps = [unwrapped[i + 1] - unwrapped[i] for i in range(11)]
    gaps.append(360.0 - unwrapped[11])
    return all(gap > ordering_tolerance for gap in gaps)


def house_distortion_profile(cusps: tuple[float, ...] | list[float]) -> HouseDistortionProfile:
    """
    Measure 12-house width distortion without presupposing symmetry.

    Widths are computed in house order:
        w_i = (lambda_{i+1} - lambda_i) mod 360
    with the final width wrapping from House 12 back to House 1.

    Precondition:
        ``cusps`` should already be known to form a strictly ordered cycle.
        This function intentionally stays pure and does not impose that gate.
    """
    if len(cusps) != 12:
        raise ValueError("cusps must contain exactly 12 house longitudes")

    widths = tuple(
        (cusps[(i + 1) % 12] - cusps[i]) % 360.0
        for i in range(12)
    )
    min_width = min(widths)
    max_width = max(widths)
    narrow_houses = tuple(
        index + 1
        for index, width in enumerate(widths)
        if width - min_width <= _EXTREME_HOUSE_TOLERANCE
    )
    wide_houses = tuple(
        index + 1
        for index, width in enumerate(widths)
        if max_width - width <= _EXTREME_HOUSE_TOLERANCE
    )
    distortion_ratio = float("inf") if min_width == 0.0 else max_width / min_width
    return HouseDistortionProfile(
        widths=widths,
        min_width=min_width,
        max_width=max_width,
        distortion_ratio=distortion_ratio,
        narrow_houses=narrow_houses,
        wide_houses=wide_houses,
    )


def practically_admissible_cusp_cycle(
    cusps: tuple[float, ...] | list[float],
    *,
    rho_max: float,
) -> tuple[bool, HouseDistortionProfile]:
    """
    Return practical admissibility under a distortion-ratio ceiling.

    Precondition:
        ``cusps`` should already be known to form a strictly ordered cycle.
    """
    if rho_max < 1.0:
        raise ValueError("rho_max must be >= 1.0")

    profile = house_distortion_profile(cusps)
    return profile.distortion_ratio <= rho_max, profile


def house_cycle_verdict(
    cusps: tuple[float, ...] | list[float],
    *,
    rho_max: float,
    ordering_tolerance: float = 1e-7,
) -> tuple[HouseCycleVerdict, HouseDistortionProfile | None]:
    """
    Compose ordering and practical screening into one safe verdict surface.
    """
    if not strictly_ordered_cusp_cycle(
        cusps,
        ordering_tolerance=ordering_tolerance,
    ):
        return "unordered", None

    admissible, profile = practically_admissible_cusp_cycle(
        cusps,
        rho_max=rho_max,
    )
    if admissible:
        return "practically_admissible", profile
    return "ordered_but_impractical", profile
