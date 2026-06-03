"""
Experimental high-latitude solver for Campanus houses.

This module is intentionally separate from moira.houses (following the established
pattern from experimental_placidus.py) so that research-grade or experimental
high-latitude prime-vertical / local-horizon resolution logic for Campanus
can be developed and opted into explicitly via PolarFallbackPolicy.EXPERIMENTAL_SEARCH
without altering the main house doctrine or computation paths for normal latitudes.

The main houses engine will delegate to this only under explicit experimental
policy for this system when |lat| >= critical and the system is still guarded.

See HOUSES_SOVEREIGNTY_REMEDIATION_ROADMAP.md for the required geometric
object-first remediation for Campanus (local vector mini-engine removal,
branch doctrine, prime vertical objects).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


__all__ = [
    "ExperimentalCampanusStatus",
    "ExperimentalCampanusResult",
    "search_experimental_campanus",
]


class ExperimentalCampanusStatus(str, Enum):
    """Structured outcome for a high-latitude Campanus experimental computation."""

    NOT_IMPLEMENTED = "not_implemented"


@dataclass(frozen=True, slots=True)
class ExperimentalCampanusResult:
    """Result of an explicit high-latitude Campanus experimental computation."""

    armc: float
    obliquity: float
    latitude: float
    asc: float
    mc: float
    status: ExperimentalCampanusStatus
    cusps: tuple[float, ...] | None = None
    diagnostic_summary: str = ""

    @property
    def has_solution(self) -> bool:
        return self.cusps is not None


def search_experimental_campanus(
    armc: float,
    obliquity: float,
    latitude: float,
    asc: float,
    mc: float,
    **kwargs,
) -> ExperimentalCampanusResult:
    """
    Placeholder for high-latitude experimental computation for Campanus houses.

    Currently raises NotImplementedError.
    """
    raise NotImplementedError(
        "High-latitude experimental support for Campanus (C) not yet implemented. "
        "Develop from first principles per the houses sovereignty roadmap "
        "(prime vertical sectors as explicit objects, no duplicated local vectors, "
        "branch doctrine before assembly). Reference experimental_placidus.py and roadmap."
    )
