"""
Experimental high-latitude solver for Alcabitius houses.

This module is intentionally separate from moira.houses (following the established
pattern from experimental_placidus.py) so that research-grade or experimental
high-latitude ascendant-based semi-arc / oblique ascension resolution logic for
Alcabitius can be developed and opted into explicitly via
PolarFallbackPolicy.EXPERIMENTAL_SEARCH without altering the main house doctrine
or computation paths for normal latitudes.

The main houses engine will delegate to this only under explicit experimental
policy for this system when |lat| >= critical and the system is still guarded.

See HOUSES_SOVEREIGNTY_REMEDIATION_ROADMAP.md for the required geometric
object-first remediation for Alcabitius (semi-arc geometry, _asc_from_armc
issues at polar).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


__all__ = [
    "ExperimentalAlcabitiusStatus",
    "ExperimentalAlcabitiusResult",
    "search_experimental_alcabitius",
]


class ExperimentalAlcabitiusStatus(str, Enum):
    """Structured outcome for a high-latitude Alcabitius experimental computation."""

    NOT_IMPLEMENTED = "not_implemented"


@dataclass(frozen=True, slots=True)
class ExperimentalAlcabitiusResult:
    """Result of an explicit high-latitude Alcabitius experimental computation."""

    armc: float
    obliquity: float
    latitude: float
    asc: float
    mc: float
    status: ExperimentalAlcabitiusStatus
    cusps: tuple[float, ...] | None = None
    diagnostic_summary: str = ""

    @property
    def has_solution(self) -> bool:
        return self.cusps is not None


def search_experimental_alcabitius(
    armc: float,
    obliquity: float,
    latitude: float,
    asc: float,
    mc: float,
    **kwargs,
) -> ExperimentalAlcabitiusResult:
    """
    Placeholder for high-latitude experimental computation for Alcabitius houses.

    Currently raises NotImplementedError.
    """
    raise NotImplementedError(
        "High-latitude experimental support for Alcabitius (B) not yet implemented. "
        "Develop from first principles per the houses sovereignty roadmap "
        "(object-first semi-arc geometry, handling for _asc_from_armc overflow at polar). "
        "Reference experimental_placidus.py and the roadmap (Alcabitius entry)."
    )
