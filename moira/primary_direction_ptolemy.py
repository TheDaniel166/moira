"""
Moira -- primary_direction_ptolemy.py
Explicit Ptolemaic declination-equivalence primitives.

Boundary
--------
Owns the narrow, source-backed Ptolemaic handling of zodiacal parallels and
contra-parallels by projecting a declination-equivalent ecliptic point on the
branch nearest the source body's own longitude.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "PtolemaicParallelRelation",
    "PtolemaicParallelTarget",
    "project_ptolemaic_declination_point",
]


class PtolemaicParallelRelation(StrEnum):
    PARALLEL = "parallel"
    CONTRA_PARALLEL = "contra_parallel"


@dataclass(frozen=True, slots=True)
class PtolemaicParallelTarget:
    source_name: str
    relation: PtolemaicParallelRelation = PtolemaicParallelRelation.PARALLEL

    def __post_init__(self) -> None:
        if not self.source_name:
            raise ValueError("PtolemaicParallelTarget requires a source_name")

    @property
    def name(self) -> str:
        label = "Parallel" if self.relation is PtolemaicParallelRelation.PARALLEL else "Contra-Parallel"
        return f"{self.source_name} {label}"


def _angular_separation(left: float, right: float) -> float:
    return abs((left - right + 180.0) % 360.0 - 180.0)


def project_ptolemaic_declination_point(
    *,
    source_longitude: float,
    source_declination: float,
    obliquity: float,
    relation: PtolemaicParallelRelation,
) -> float:
    """
    Project the narrow Ptolemaic zodiacal declination equivalent.

    This branch keeps the historical reduction explicit:
    - parallel      -> preserve the source declination
    - contra-parallel -> negate the source declination
    - solve sin(delta) = sin(eps) * sin(lambda) on the ecliptic
    - choose the ecliptic branch nearest the source longitude
    """
    if abs(obliquity) <= 1e-9:
        raise ValueError("Ptolemaic declination projection requires non-zero obliquity")

    target_declination = (
        source_declination
        if relation is PtolemaicParallelRelation.PARALLEL
        else -source_declination
    )
    limit = abs(obliquity) + 1e-9
    if abs(target_declination) > limit:
        raise ValueError(
            "Ptolemaic declination projection requires a declination within ecliptic reach"
        )

    ratio = math.sin(math.radians(target_declination)) / math.sin(math.radians(obliquity))
    ratio = max(-1.0, min(1.0, ratio))
    principal = math.degrees(math.asin(ratio))
    candidates = (principal % 360.0, (180.0 - principal) % 360.0)
    return min(candidates, key=lambda candidate: (_angular_separation(candidate, source_longitude), candidate))
