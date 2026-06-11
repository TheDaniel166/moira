"""Transport models for Phase-9 Ashtakavarga route family (P9-09)."""

from __future__ import annotations

import math

from pydantic import Field, field_validator, model_validator

from .common import _StrictModel


_REQUIRED_REFERENCES = frozenset(
    ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Lagna")
)


class AshtakavargaPolicyRequest(_StrictModel):
    ayanamsa_system: str = "Lahiri"
    strong_threshold: int = Field(default=4, ge=1, le=8)
    apply_trikona_shodhana: bool = False
    apply_ekadhipatya_shodhana: bool = False

    @field_validator("ayanamsa_system")
    @classmethod
    def _non_empty_ayanamsa_system(cls, value: str) -> str:
        if not value:
            raise ValueError("ayanamsa_system must be non-empty")
        return value

    @model_validator(mode="after")
    def _valid_shodhana_policy(self) -> "AshtakavargaPolicyRequest":
        if self.apply_ekadhipatya_shodhana and not self.apply_trikona_shodhana:
            raise ValueError(
                "apply_ekadhipatya_shodhana requires apply_trikona_shodhana"
            )
        return self


class AshtakavargaDirectRequest(_StrictModel):
    sidereal_longitudes: dict[str, float] | None = None
    sign_indices: dict[str, int] | None = None
    policy: AshtakavargaPolicyRequest | None = None

    @field_validator("sidereal_longitudes")
    @classmethod
    def _finite_sidereal_longitudes(
        cls,
        value: dict[str, float] | None,
    ) -> dict[str, float] | None:
        if value is None:
            return value
        _validate_required_keys(value, "sidereal_longitudes")
        for body, longitude in value.items():
            if not body:
                raise ValueError("sidereal_longitudes keys must be non-empty")
            if not math.isfinite(longitude):
                raise ValueError("sidereal_longitudes values must be finite")
        return value

    @field_validator("sign_indices")
    @classmethod
    def _valid_sign_indices(
        cls,
        value: dict[str, int] | None,
    ) -> dict[str, int] | None:
        if value is None:
            return value
        _validate_required_keys(value, "sign_indices")
        for body, sign_index in value.items():
            if not body:
                raise ValueError("sign_indices keys must be non-empty")
            if not 0 <= sign_index <= 11:
                raise ValueError("sign_indices values must be in [0, 11]")
        return value

    @model_validator(mode="after")
    def _one_input_form(self) -> "AshtakavargaDirectRequest":
        if (self.sidereal_longitudes is None) == (self.sign_indices is None):
            raise ValueError(
                "provide exactly one of sidereal_longitudes or sign_indices"
            )
        return self


class AshtakavargaSignProfileRequest(AshtakavargaDirectRequest):
    planet: str
    sign_index: int = Field(ge=0, le=11)

    @field_validator("planet")
    @classmethod
    def _non_empty_planet(cls, value: str) -> str:
        if not value:
            raise ValueError("planet must be non-empty")
        return value


class AshtakavargaTransitStrengthRequest(AshtakavargaDirectRequest):
    planet: str
    transit_sign_index: int = Field(ge=0, le=11)

    @field_validator("planet")
    @classmethod
    def _non_empty_planet(cls, value: str) -> str:
        if not value:
            raise ValueError("planet must be non-empty")
        return value


class BhinnashtakavargaResultResponse(_StrictModel):
    planet: str
    rekhas: tuple[int, ...]
    total_rekhas: int


class AshtakavargaResultResponse(_StrictModel):
    ayanamsa_system: str
    bhinnashtakavarga: dict[str, BhinnashtakavargaResultResponse]
    sarvashtakavarga: tuple[int, ...]
    shodhana_bhinnashtakavarga: dict[str, BhinnashtakavargaResultResponse] | None
    shodhana_sarvashtakavarga: tuple[int, ...] | None


class SignStrengthProfileResponse(_StrictModel):
    ayanamsa_system: str
    planet: str
    sign_idx: int
    rekha_count: int
    tier: str


class AshtakavargaChartProfileResponse(_StrictModel):
    ayanamsa_system: str
    result: AshtakavargaResultResponse
    sarva_total: int
    sarva_max: int
    sarva_max_sign_idx: int
    sarva_min: int
    sarva_min_sign_idx: int
    strong_planet_sign_counts: dict[str, int]


class AshtakavargaTransitStrengthResponse(_StrictModel):
    ayanamsa_system: str
    planet: str
    transit_sign_index: int
    rekha_count: int
    tier: str


def _validate_required_keys(value: dict[str, object], field_name: str) -> None:
    missing = sorted(_REQUIRED_REFERENCES - set(value))
    if missing:
        raise ValueError(f"{field_name} missing required references: {missing}")


__all__ = [
    "AshtakavargaChartProfileResponse",
    "AshtakavargaDirectRequest",
    "AshtakavargaPolicyRequest",
    "AshtakavargaResultResponse",
    "AshtakavargaSignProfileRequest",
    "AshtakavargaTransitStrengthRequest",
    "AshtakavargaTransitStrengthResponse",
    "BhinnashtakavargaResultResponse",
    "SignStrengthProfileResponse",
]
