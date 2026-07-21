"""Transport models for whole-sign Hellenistic aspect relations."""

from __future__ import annotations

import math

from pydantic import Field, field_validator

from .common import _StrictModel


HELLENISTIC_ASPECT_MAX_POSITIONS = 64
HELLENISTIC_ASPECT_MAX_NAME_LENGTH = 64


def _clean_positions(value: dict[str, float]) -> dict[str, float]:
    if len(value) < 2:
        raise ValueError("positions must contain at least two bodies")
    if len(value) > HELLENISTIC_ASPECT_MAX_POSITIONS:
        raise ValueError(
            f"positions may contain at most {HELLENISTIC_ASPECT_MAX_POSITIONS} bodies"
        )

    cleaned: dict[str, float] = {}
    for raw_name, longitude in value.items():
        name = str(raw_name).strip()
        if not name:
            raise ValueError("position body names must be non-empty")
        if len(name) > HELLENISTIC_ASPECT_MAX_NAME_LENGTH:
            raise ValueError(
                f"position body names may contain at most "
                f"{HELLENISTIC_ASPECT_MAX_NAME_LENGTH} characters"
            )
        if name in cleaned:
            raise ValueError("position body names must be unique after trimming")
        if not math.isfinite(longitude):
            raise ValueError("position longitudes must be finite")
        cleaned[name] = longitude
    return cleaned


class WholeSignAspectsRequest(_StrictModel):
    positions: dict[str, float]

    @field_validator("positions")
    @classmethod
    def _valid_positions(cls, value: dict[str, float]) -> dict[str, float]:
        return _clean_positions(value)


class OvercomingRequest(_StrictModel):
    body1: str = Field(min_length=1, max_length=HELLENISTIC_ASPECT_MAX_NAME_LENGTH)
    longitude1: float
    body2: str = Field(min_length=1, max_length=HELLENISTIC_ASPECT_MAX_NAME_LENGTH)
    longitude2: float

    @field_validator("body1", "body2")
    @classmethod
    def _valid_body_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("body names must be non-empty")
        return name

    @field_validator("longitude1", "longitude2")
    @classmethod
    def _finite_longitude(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("longitudes must be finite")
        return value


class HellenisticAspectClassificationResponse(_StrictModel):
    domain: str
    tier: str
    family: str


class WholeSignAspectResponse(_StrictModel):
    body1: str
    body2: str
    aspect: str
    symbol: str
    angle: float
    separation: float
    direction: str | None
    sign_degree1: int
    sign_degree2: int
    body1_overcomes_body2: bool
    body2_overcomes_body1: bool
    classification: HellenisticAspectClassificationResponse


class HellenisticAspectProvenanceResponse(_StrictModel):
    source_module: str = "moira.aspects"
    engine_entrypoint: str
    doctrine: str
    ephemeris: str = "not_used"
    chart_motion: str = "not_computed"
    position_semantics: str = "caller_supplied_tropical_ecliptic_longitudes_degrees"
    source_refs: list[str]
    stage_sequence: list[str]


class WholeSignAspectsResponse(_StrictModel):
    aspects: list[WholeSignAspectResponse]
    count: int
    provenance: HellenisticAspectProvenanceResponse


class OvercomingResponse(_StrictModel):
    body1: str
    longitude1: float
    body2: str
    longitude2: float
    body1_overcomes_body2: bool
    body2_overcomes_body1: bool
    overcoming_body: str | None
    provenance: HellenisticAspectProvenanceResponse
