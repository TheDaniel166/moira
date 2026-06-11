"""Transport models for Phase-9 Vedic Dignities route family (P9-08)."""

from __future__ import annotations

import math

from pydantic import Field, field_validator

from .common import _StrictModel


class VedicDignityPolicyRequest(_StrictModel):
    ayanamsa_system: str = "Lahiri"

    @field_validator("ayanamsa_system")
    @classmethod
    def _non_empty_ayanamsa_system(cls, value: str) -> str:
        if not value:
            raise ValueError("ayanamsa_system must be non-empty")
        return value


class VedicDignityRequest(_StrictModel):
    planet: str
    sidereal_longitude: float
    policy: VedicDignityPolicyRequest | None = None

    @field_validator("planet")
    @classmethod
    def _non_empty_planet(cls, value: str) -> str:
        if not value:
            raise ValueError("planet must be non-empty")
        return value

    @field_validator("sidereal_longitude")
    @classmethod
    def _finite_sidereal_longitude(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("sidereal_longitude must be finite")
        return value


class VedicDignityChartRequest(_StrictModel):
    sidereal_longitudes: dict[str, float] = Field(min_length=1)
    policy: VedicDignityPolicyRequest | None = None

    @field_validator("sidereal_longitudes")
    @classmethod
    def _finite_sidereal_longitudes(cls, value: dict[str, float]) -> dict[str, float]:
        if not value:
            raise ValueError("sidereal_longitudes must be non-empty")
        for planet, longitude in value.items():
            if not planet:
                raise ValueError("sidereal_longitudes keys must be non-empty")
            if not math.isfinite(longitude):
                raise ValueError("sidereal_longitudes values must be finite")
        return value


class VedicDignityResultResponse(_StrictModel):
    planet: str
    sidereal_longitude: float
    sign_index: int
    sign: str
    dignity_rank: str
    is_exalted: bool
    is_debilitated: bool
    is_mulatrikona: bool
    is_own_sign: bool
    is_strong: bool
    is_weak: bool
    exaltation_score: float
    ayanamsa_system: str


class VedicPlanetaryRelationshipResponse(_StrictModel):
    from_planet: str
    to_planet: str
    natural: str
    temporary: str
    compound: str
    is_friendly: bool
    is_hostile: bool


class VedicDignityRelationshipsResponse(_StrictModel):
    ayanamsa_system: str
    relationships: tuple[VedicPlanetaryRelationshipResponse, ...]


class VedicDignityConditionResponse(_StrictModel):
    ayanamsa_system: str
    result: VedicDignityResultResponse
    planet: str
    dignity_rank: str
    tier: str
    exaltation_score: float
    sign_index: int
    sign: str


class VedicChartDignityProfileResponse(_StrictModel):
    ayanamsa_system: str
    results: dict[str, VedicDignityResultResponse]
    strong_count: int
    neutral_count: int
    weak_count: int
    strongest_planet: str
    weakest_planet: str
    planet_tiers: dict[str, str]
    exaltation_scores: dict[str, float]


__all__ = [
    "VedicChartDignityProfileResponse",
    "VedicDignityChartRequest",
    "VedicDignityConditionResponse",
    "VedicDignityPolicyRequest",
    "VedicDignityRelationshipsResponse",
    "VedicDignityRequest",
    "VedicDignityResultResponse",
    "VedicPlanetaryRelationshipResponse",
]
