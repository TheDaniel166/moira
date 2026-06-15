"""Transport models for P-GAP-05 sidereal and Nakshatra utility routes."""

from __future__ import annotations

import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from moira.sidereal import Ayanamsa


SIDEREAL_NAKSHATRA_MAX_BULK_POSITIONS = 64
SIDEREAL_AYANAMSA_MODES = ("true", "mean")
SIDEREAL_CONVERSION_DIRECTIONS = ("tropical_to_sidereal", "sidereal_to_tropical")


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _validate_finite(value: float, field_name: str) -> float:
    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite")
    return value


def _validate_ayanamsa_system(value: str) -> str:
    system = value.strip()
    if not system:
        raise ValueError("ayanamsa_system must be non-empty")
    if system not in Ayanamsa.ALL:
        raise ValueError(f"ayanamsa_system must be one of {list(Ayanamsa.ALL)!r}")
    return system


def _validate_mode(value: str) -> str:
    mode = value.strip().lower()
    if mode not in SIDEREAL_AYANAMSA_MODES:
        raise ValueError("mode must be 'true' or 'mean'")
    return mode


class SiderealAyanamsaRequest(_StrictModel):
    jd_ut: float
    ayanamsa_system: str = Ayanamsa.LAHIRI
    mode: Literal["true", "mean"] = "true"

    @field_validator("jd_ut")
    @classmethod
    def _finite_jd_ut(cls, value: float) -> float:
        return _validate_finite(value, "jd_ut")

    @field_validator("ayanamsa_system")
    @classmethod
    def _valid_ayanamsa_system(cls, value: str) -> str:
        return _validate_ayanamsa_system(value)

    @field_validator("mode", mode="before")
    @classmethod
    def _valid_mode(cls, value: str) -> str:
        return _validate_mode(value)


class SiderealConversionRequest(SiderealAyanamsaRequest):
    longitude_deg: float
    direction: Literal["tropical_to_sidereal", "sidereal_to_tropical"]

    @field_validator("longitude_deg")
    @classmethod
    def _finite_longitude(cls, value: float) -> float:
        return _validate_finite(value, "longitude_deg")

    @field_validator("direction", mode="before")
    @classmethod
    def _valid_direction(cls, value: str) -> str:
        direction = value.strip()
        if direction not in SIDEREAL_CONVERSION_DIRECTIONS:
            raise ValueError(
                "direction must be 'tropical_to_sidereal' or 'sidereal_to_tropical'"
            )
        return direction


class SiderealNakshatraPositionRequest(_StrictModel):
    tropical_longitude_deg: float
    jd_ut: float
    ayanamsa_system: str = Ayanamsa.LAHIRI

    @field_validator("tropical_longitude_deg")
    @classmethod
    def _finite_longitude(cls, value: float) -> float:
        return _validate_finite(value, "tropical_longitude_deg")

    @field_validator("jd_ut")
    @classmethod
    def _finite_jd_ut(cls, value: float) -> float:
        return _validate_finite(value, "jd_ut")

    @field_validator("ayanamsa_system")
    @classmethod
    def _valid_ayanamsa_system(cls, value: str) -> str:
        return _validate_ayanamsa_system(value)


class SiderealNakshatraBulkRequest(_StrictModel):
    positions: dict[str, float] = Field(
        min_length=1,
        max_length=SIDEREAL_NAKSHATRA_MAX_BULK_POSITIONS,
    )
    jd_ut: float
    ayanamsa_system: str = Ayanamsa.LAHIRI

    @field_validator("positions", mode="before")
    @classmethod
    def _valid_positions(cls, value: Any) -> dict[str, float]:
        if not isinstance(value, dict):
            raise ValueError("positions must be a mapping")
        if not value:
            raise ValueError("positions must be non-empty")
        if len(value) > SIDEREAL_NAKSHATRA_MAX_BULK_POSITIONS:
            raise ValueError(
                f"positions may not contain more than {SIDEREAL_NAKSHATRA_MAX_BULK_POSITIONS} entries"
            )

        cleaned: dict[str, float] = {}
        for raw_name, raw_longitude in value.items():
            if not isinstance(raw_name, str):
                raise ValueError("position names must be strings")
            name = raw_name.strip()
            if not name:
                raise ValueError("position names must be non-empty")
            if name in cleaned:
                raise ValueError("position names must be unique after trimming")
            try:
                longitude = float(raw_longitude)
            except (TypeError, ValueError) as exc:
                raise ValueError("position longitude values must be finite") from exc
            _validate_finite(longitude, "position longitude values")
            cleaned[name] = longitude
        return cleaned

    @field_validator("jd_ut")
    @classmethod
    def _finite_jd_ut(cls, value: float) -> float:
        return _validate_finite(value, "jd_ut")

    @field_validator("ayanamsa_system")
    @classmethod
    def _valid_ayanamsa_system(cls, value: str) -> str:
        return _validate_ayanamsa_system(value)


class SiderealUtilityProvenanceResponse(_StrictModel):
    source_module: str = "moira.sidereal"
    engine_entrypoint: str
    time_scale: str = "UT_JD"
    product_kind: str
    ayanamsa_system: str | None = None
    ayanamsa_mode: str | None = None
    registry_owner: str | None = None
    reference_epoch: str | None = None
    user_defined_ayanamsa: str | None = None
    jd_policy: str | None = None
    mode_policy: str | None = None
    star_anchor_policy: str | None = None
    longitude_input_policy: str | None = None
    conversion_direction: str | None = None
    taxonomy: str | None = None
    span_deg: float | None = None
    pada_span_deg: float | None = None
    interpretation: str | None = None
    panchanga_judgement: str | None = None
    stage_sequence: list[str]


class AyanamsaSystemResponse(_StrictModel):
    system: str
    reference_value_j2000_deg: float
    is_star_anchored: bool
    default_mode: str = "true"
    supported_modes: list[str]


class AyanamsaSystemsEnvelopeResponse(_StrictModel):
    systems: list[AyanamsaSystemResponse]
    total: int
    provenance: SiderealUtilityProvenanceResponse


class SiderealAyanamsaResponse(_StrictModel):
    jd_ut: float
    ayanamsa_system: str
    mode: str
    ayanamsa_deg: float
    value_range: list[float | str]
    provenance: SiderealUtilityProvenanceResponse


class SiderealConversionResponse(_StrictModel):
    direction: str
    jd_ut: float
    ayanamsa_system: str
    mode: str
    input_longitude_deg: float
    output_longitude_deg: float
    ayanamsa_deg: float
    longitude_range: list[float | str]
    provenance: SiderealUtilityProvenanceResponse


class SiderealNakshatraPositionResponse(_StrictModel):
    name: str | None = None
    tropical_longitude_deg: float
    jd_ut: float
    ayanamsa_system: str
    nakshatra: str
    nakshatra_index: int
    nakshatra_number: int
    nakshatra_lord: str
    pada: int
    degrees_in: float
    degrees_remaining: float
    sidereal_longitude_deg: float


class SiderealNakshatraPositionEnvelopeResponse(_StrictModel):
    request: SiderealNakshatraPositionRequest
    position: SiderealNakshatraPositionResponse
    provenance: SiderealUtilityProvenanceResponse


class SiderealNakshatraBulkEnvelopeResponse(_StrictModel):
    request: SiderealNakshatraBulkRequest
    positions: list[SiderealNakshatraPositionResponse]
    total: int
    provenance: SiderealUtilityProvenanceResponse
