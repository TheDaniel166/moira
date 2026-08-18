"""Transport models for supporting Hellenistic atoms."""

from __future__ import annotations

import math

from pydantic import Field, field_validator

from moira.aspects import HellenisticAspectEvaluationStatus

from .common import _StrictModel
from .dignities import BesiegingTruthResponse
from .hellenistic_aspects import (
    HELLENISTIC_ASPECT_MAX_NAME_LENGTH,
    HELLENISTIC_ASPECT_MAX_POSITIONS,
    HellenisticAspectProvenanceResponse,
    HellenisticSuperiorityTruthResponse,
)


def _clean_named_floats(
    value: dict[str, float],
    *,
    quantity: str,
    minimum: int = 1,
) -> dict[str, float]:
    if len(value) < minimum:
        raise ValueError(f"{quantity} must contain at least {minimum} entries")
    if len(value) > HELLENISTIC_ASPECT_MAX_POSITIONS:
        raise ValueError(
            f"{quantity} may contain at most {HELLENISTIC_ASPECT_MAX_POSITIONS} entries"
        )
    cleaned: dict[str, float] = {}
    for raw_name, number in value.items():
        name = str(raw_name).strip()
        if not name:
            raise ValueError(f"{quantity} names must be non-empty")
        if len(name) > HELLENISTIC_ASPECT_MAX_NAME_LENGTH:
            raise ValueError(
                f"{quantity} names may contain at most "
                f"{HELLENISTIC_ASPECT_MAX_NAME_LENGTH} characters"
            )
        if name in cleaned:
            raise ValueError(f"{quantity} names must be unique after trimming")
        if not math.isfinite(number):
            raise ValueError(f"{quantity} values must be finite")
        cleaned[name] = number
    return cleaned


class TwelfthPartsRequest(_StrictModel):
    positions: dict[str, float]

    @field_validator("positions")
    @classmethod
    def _valid_positions(cls, value: dict[str, float]) -> dict[str, float]:
        return _clean_named_floats(value, quantity="positions")


class HellenisticConditionRequest(_StrictModel):
    subject: str = Field(min_length=1, max_length=HELLENISTIC_ASPECT_MAX_NAME_LENGTH)
    positions: dict[str, float]
    speeds: dict[str, float] | None = None
    adherence_orb_deg: float = 3.0
    enclosure_orb_deg: float = 12.0

    @field_validator("subject")
    @classmethod
    def _valid_subject(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("subject must be non-empty")
        return name

    @field_validator("positions")
    @classmethod
    def _valid_positions(cls, value: dict[str, float]) -> dict[str, float]:
        return _clean_named_floats(value, quantity="positions")

    @field_validator("speeds")
    @classmethod
    def _valid_speeds(
        cls,
        value: dict[str, float] | None,
    ) -> dict[str, float] | None:
        if value is None:
            return None
        return _clean_named_floats(value, quantity="speeds")

    @field_validator("adherence_orb_deg", "enclosure_orb_deg")
    @classmethod
    def _valid_orb(cls, value: float) -> float:
        if not math.isfinite(value) or not (0.0 < value <= 180.0):
            raise ValueError("orbs must be finite and in (0, 180]")
        return value


class TwelfthPartResponse(_StrictModel):
    body: str
    occupied_sign: str
    occupied_sign_degree: float
    slice_index: int
    twelfth_part_sign: str
    projected_longitude: float
    source_longitude: float


class TwelfthPartsResponse(_StrictModel):
    parts: list[TwelfthPartResponse]
    count: int
    provenance: HellenisticAspectProvenanceResponse


class HellenisticTestimonyWitnessResponse(_StrictModel):
    body: str
    aspect: str
    angle_deg: float
    superiority: HellenisticSuperiorityTruthResponse


class HellenisticTestimonyTruthResponse(_StrictModel):
    status: HellenisticAspectEvaluationStatus
    subject: str
    witnesses: tuple[HellenisticTestimonyWitnessResponse, ...]
    averse_bodies: tuple[str, ...]
    reason: str | None = None


class HellenisticPlanetOvercomingTruthResponse(_StrictModel):
    status: HellenisticAspectEvaluationStatus
    subject: str
    overcame_by: tuple[str, ...]
    overcomes: tuple[str, ...]
    receipts: tuple[HellenisticSuperiorityTruthResponse, ...]
    reason: str | None = None


class HellenisticAdherenceTruthResponse(_StrictModel):
    status: HellenisticAspectEvaluationStatus
    subject: str
    orb_deg: float
    adhered: bool | None
    partner: str | None
    distance_deg: float | None
    motion_state: str | None
    reason: str | None = None


class HellenisticRayTruthResponse(_StrictModel):
    status: HellenisticAspectEvaluationStatus
    subject: str
    reason: str


class HellenisticAssembleConditionResponse(_StrictModel):
    subject: str
    testimony: HellenisticTestimonyTruthResponse
    overcoming: HellenisticPlanetOvercomingTruthResponse
    enclosure: BesiegingTruthResponse
    adherence: HellenisticAdherenceTruthResponse
    ray: HellenisticRayTruthResponse
    provenance: HellenisticAspectProvenanceResponse


__all__ = [
    "HellenisticAdherenceTruthResponse",
    "HellenisticAssembleConditionResponse",
    "HellenisticConditionRequest",
    "HellenisticPlanetOvercomingTruthResponse",
    "HellenisticRayTruthResponse",
    "HellenisticTestimonyTruthResponse",
    "HellenisticTestimonyWitnessResponse",
    "TwelfthPartResponse",
    "TwelfthPartsRequest",
    "TwelfthPartsResponse",
]
