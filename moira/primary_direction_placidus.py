"""
Moira -- primary_direction_placidus.py
Explicit narrow Placidian parallel primitives.

Boundary
--------
Owns the recoverable direct Placidian mundane rapt-parallel arithmetic.
This is not a generic parallel family. It is one explicit method-bound branch.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .primary_directions import SpeculumEntry

__all__ = [
    "PlacidianRaptParallelTarget",
    "compute_placidian_rapt_parallel_arc",
]


@dataclass(frozen=True, slots=True)
class PlacidianRaptParallelTarget:
    source_name: str

    def __post_init__(self) -> None:
        if not self.source_name:
            raise ValueError("PlacidianRaptParallelTarget requires a source_name")

    @property
    def name(self) -> str:
        return f"{self.source_name} Rapt Parallel"


def _placidian_meridian_distance(entry: SpeculumEntry) -> float:
    if entry.upper:
        return abs(entry.ha)
    return 180.0 - abs(entry.ha)


def _primary_semi_arc(entry: SpeculumEntry) -> float:
    return entry.dsa if entry.upper else entry.nsa


def _smallest_ra_difference(left: float, right: float) -> float:
    return abs((left - right + 180.0) % 360.0 - 180.0)


def compute_placidian_rapt_parallel_arc(
    promissor: SpeculumEntry,
    significator: SpeculumEntry,
) -> float:
    """
    Compute the narrow direct Placidian mundane rapt-parallel arc.

    Recoverable law:
    - use the promissor's active semi-arc and the significator's active semi-arc
    - form the semi-arc sum
    - compare it to the relevant right-ascension difference
    - derive the promissor's secondary distance by proportionality
    - subtract it from the promissor's primary meridian distance

    When the bodies lie in opposite hemispheres, the significator is taken by
    opposition in right ascension before the difference is formed.
    """
    promissor_semi_arc = _primary_semi_arc(promissor)
    significator_semi_arc = _primary_semi_arc(significator)
    semi_arc_sum = promissor_semi_arc + significator_semi_arc
    if semi_arc_sum <= 1e-9:
        raise ValueError("Placidian rapt parallel requires non-zero combined semi-arc")

    significator_ra = significator.ra
    if promissor.upper != significator.upper:
        significator_ra = (significator_ra + 180.0) % 360.0

    ra_difference = _smallest_ra_difference(promissor.ra, significator_ra)
    secondary_distance = (ra_difference * promissor_semi_arc) / semi_arc_sum
    primary_distance = _placidian_meridian_distance(promissor)
    return abs(primary_distance - secondary_distance)
