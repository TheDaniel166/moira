"""
Moira -- primary_directions/antiscia.py
Explicit narrow antiscia primitives for the primary-directions subsystem.
"""

from dataclasses import dataclass
from enum import StrEnum

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
    ANTISCION = "antiscion"
    CONTRA_ANTISCION = "contra_antiscion"


@dataclass(frozen=True, slots=True)
class PrimaryDirectionAntisciaTarget:
    source_name: str
    kind: PrimaryDirectionAntisciaKind = PrimaryDirectionAntisciaKind.ANTISCION

    def __post_init__(self) -> None:
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
    if kind is PrimaryDirectionAntisciaKind.ANTISCION:
        return antiscion(source_longitude)
    return contra_antiscion(source_longitude)
