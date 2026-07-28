"""
Moira -- primary_directions/ptolemy.py
Explicit Ptolemaic declination-equivalence primitives for the primary-directions subsystem.

Boundary
--------
Owns the narrow, source-backed Ptolemaic handling of zodiacal parallels and
contra-parallels by projecting a declination-equivalent ecliptic point on the
branch nearest the source body's own longitude.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from .._strenum import StrEnum
from numbers import Real

from .targets import PrimaryDirectionTargetClass, primary_direction_target_truth

__all__ = [
    "PtolemaicParallelRelation",
    "PtolemaicParallelTarget",
    "project_ptolemaic_declination_point",
]


class PtolemaicParallelRelation(StrEnum):
    """Vessel: Enumeration of Ptolemaic declination-equivalence types."""
    PARALLEL = "parallel"
    CONTRA_PARALLEL = "contra_parallel"


@dataclass(frozen=True, slots=True)
class PtolemaicParallelTarget:
    """Vessel: Definition of a specific body to be used for Ptolemaic zodiacal parallels."""
    source_name: str
    relation: PtolemaicParallelRelation = PtolemaicParallelRelation.PARALLEL

    def __post_init__(self) -> None:
        if not isinstance(self.source_name, str) or not self.source_name.strip():
            raise ValueError("PtolemaicParallelTarget requires a source_name")
        if not isinstance(self.relation, PtolemaicParallelRelation):
            raise ValueError("PtolemaicParallelTarget requires a PtolemaicParallelRelation")
        truth = primary_direction_target_truth(self.source_name)
        if truth.target_class not in (
            PrimaryDirectionTargetClass.PLANET,
            PrimaryDirectionTargetClass.NODE,
            PrimaryDirectionTargetClass.ANGLE,
        ):
            raise ValueError(
                "PtolemaicParallelTarget currently requires a planet, node, or angle source"
            )

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
    inputs = {
        "source_longitude": source_longitude,
        "source_declination": source_declination,
        "obliquity": obliquity,
    }
    if any(
        not isinstance(value, Real)
        or isinstance(value, bool)
        or not math.isfinite(value)
        for value in inputs.values()
    ):
        raise ValueError("Ptolemaic declination projection requires finite real coordinates")
    if not isinstance(relation, PtolemaicParallelRelation):
        raise ValueError("Ptolemaic declination projection requires an explicit relation")
    if not 0.0 <= source_longitude < 360.0:
        raise ValueError("Ptolemaic source longitude must be normalized to [0, 360)")
    if not -90.0 <= source_declination <= 90.0:
        raise ValueError("Ptolemaic source declination must be in [-90, 90]")
    if not 0.0 < obliquity < 90.0:
        raise ValueError("Ptolemaic obliquity must be in (0, 90)")

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
    if ratio < -1.0 - 1e-12 or ratio > 1.0 + 1e-12:
        raise ValueError(
            "Ptolemaic declination projection has no real ecliptic equivalent"
        )
    ratio = max(-1.0, min(1.0, ratio))
    principal = math.degrees(math.asin(ratio))
    candidates = (principal % 360.0, (180.0 - principal) % 360.0)
    return min(candidates, key=lambda candidate: (_angular_separation(candidate, source_longitude), candidate))
