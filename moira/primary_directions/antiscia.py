"""
Moira -- primary_directions/antiscia.py
Explicit narrow antiscia primitives for the primary-directions subsystem.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from .._strenum import StrEnum
from numbers import Real

from ..antiscia import antiscion, contra_antiscion
from .targets import (
    PrimaryDirectionTargetClass,
    primary_direction_target_truth,
)

__all__ = [
    "PrimaryDirectionAntisciaKind",
    "PrimaryDirectionAntisciaTarget",
    "project_primary_direction_antiscia_longitude",
]


class PrimaryDirectionAntisciaKind(StrEnum):
    """Vessel: Enumeration of antiscia reflection types."""
    ANTISCION = "antiscion"
    CONTRA_ANTISCION = "contra_antiscion"


@dataclass(frozen=True, slots=True)
class PrimaryDirectionAntisciaTarget:
    """Vessel: Definition of a specific antiscia point to be used as a direction target."""
    source_name: str
    kind: PrimaryDirectionAntisciaKind = PrimaryDirectionAntisciaKind.ANTISCION

    def __post_init__(self) -> None:
        if not isinstance(self.source_name, str) or not self.source_name.strip():
            raise ValueError("PrimaryDirectionAntisciaTarget requires a source_name")
        if not isinstance(self.kind, PrimaryDirectionAntisciaKind):
            raise ValueError(
                "PrimaryDirectionAntisciaTarget requires a PrimaryDirectionAntisciaKind"
            )
        truth = primary_direction_target_truth(self.source_name)
        if truth.target_class not in (
            PrimaryDirectionTargetClass.PLANET,
            PrimaryDirectionTargetClass.NODE,
            PrimaryDirectionTargetClass.ANGLE,
        ):
            raise ValueError(
                "PrimaryDirectionAntisciaTarget currently requires a planet, node, or angle source"
            )

    @property
    def name(self) -> str:
        if self.kind is PrimaryDirectionAntisciaKind.ANTISCION:
            return f"{self.source_name} Antiscion"
        return f"{self.source_name} Contra-Antiscion"


def project_primary_direction_antiscia_longitude(
    source_longitude: float,
    kind: PrimaryDirectionAntisciaKind,
) -> float:
    if (
        not isinstance(source_longitude, Real)
        or isinstance(source_longitude, bool)
        or not math.isfinite(source_longitude)
        or not 0.0 <= source_longitude < 360.0
    ):
        raise ValueError("Antiscia source longitude must be a finite value in [0, 360)")
    if not isinstance(kind, PrimaryDirectionAntisciaKind):
        raise ValueError("Antiscia projection requires a PrimaryDirectionAntisciaKind")
    if kind is PrimaryDirectionAntisciaKind.ANTISCION:
        return antiscion(source_longitude)
    return contra_antiscion(source_longitude)
