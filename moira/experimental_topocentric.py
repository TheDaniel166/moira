"""
Experimental high-latitude solver for Topocentric houses.

This module is intentionally separate from moira.houses (following the established
pattern from experimental_placidus.py) so that research-grade or experimental
high-latitude pole-height / polar-projection resolution logic for Topocentric
can be developed and opted into explicitly via PolarFallbackPolicy.EXPERIMENTAL_SEARCH
without altering the main house doctrine or computation paths for normal latitudes.

The main houses engine will delegate to this only under explicit experimental
policy for this system when |lat| >= critical and the system is still guarded.

See HOUSES_SOVEREIGNTY_REMEDIATION_ROADMAP.md for the required geometric
object-first remediation for Topocentric (similar pole-height issues to Regio).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


__all__ = [
    "ExperimentalTopocentricStatus",
    "ExperimentalTopocentricResult",
    "search_experimental_topocentric",
]


class ExperimentalTopocentricStatus(str, Enum):
    """Structured outcome for a high-latitude Topocentric experimental computation."""

    NOT_IMPLEMENTED = "not_implemented"


@dataclass(frozen=True, slots=True)
class ExperimentalTopocentricResult:
    """Result of an explicit high-latitude Topocentric experimental computation."""

    armc: float
    obliquity: float
    latitude: float
    asc: float
    mc: float
    status: ExperimentalTopocentricStatus
    cusps: tuple[float, ...] | None = None
    diagnostic_summary: str = ""

    @property
    def has_solution(self) -> bool:
        return self.cusps is not None


def search_experimental_topocentric(
    armc: float,
    obliquity: float,
    latitude: float,
    asc: float,
    mc: float,
    **kwargs,
) -> ExperimentalTopocentricResult:
    """
    Placeholder for high-latitude experimental computation for Topocentric houses.

    Currently raises NotImplementedError.
    """
    raise NotImplementedError(
        "High-latitude experimental support for Topocentric (T) not yet implemented. "
        "Develop from first principles per the houses sovereignty roadmap "
        "(explicit objects for the (k/3) pole height formula issues, branch doctrine, "
        "no repair). Reference experimental_placidus.py and the roadmap."
    )
