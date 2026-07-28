"""Transport models for Arabic lunar mansion (Manazil) routes."""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field, field_validator

from moira._strenum import StrEnum


MANAZIL_BULK_MAX_ITEMS = 500


class MansionComputationMode(StrEnum):
    tropical = "tropical"
    sidereal = "sidereal"


class MansionTraditionName(StrEnum):
    al_biruni = "al_biruni"
    abenragel = "abenragel"
    ibn_alarabi = "ibn_alarabi"
    agrippa = "agrippa"
    picatrix = "picatrix"


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MansionInfoResponse(_StrictModel):
    index: int
    arabic_name: str
    latin_name: str
    ruling_star: str
    nature: str
    signification: str


class MansionPositionResponse(_StrictModel):
    mansion: MansionInfoResponse
    degrees_in: float
    longitude: float
    computation_longitude: float


class MansionProvenanceResponse(_StrictModel):
    mansion_system: str = "Arabic_Manazil_28_equal_mansions"
    computational_basis: str = "equal_division_360_by_28"
    default_authority: str = "al_biruni_book_of_instruction"
    mode: MansionComputationMode
    tradition: MansionTraditionName
    requested_longitude: float
    normalized_longitude: float
    jd_ut: float | None = None
    ayanamsa_system: str | None = None
    ayanamsa_mode: str | None = None
    stage_sequence: list[str]


class MansionCatalogResponse(_StrictModel):
    mansions: list[MansionInfoResponse]
    total: int
    span_degrees: float
    traditions: list[MansionTraditionName]
    provenance: MansionProvenanceResponse


class MansionPositionRequest(_StrictModel):
    longitude: float
    mode: MansionComputationMode = MansionComputationMode.tropical
    jd_ut: float | None = None
    ayanamsa_system: str = "Lahiri"
    ayanamsa_mode: str = "true"
    tradition: MansionTraditionName = MansionTraditionName.al_biruni

    @field_validator("longitude", "jd_ut")
    @classmethod
    def _finite_number(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("numeric fields must be finite")
        return value

    @field_validator("ayanamsa_system", "ayanamsa_mode")
    @classmethod
    def _non_empty_string(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("string fields must be non-empty")
        return stripped


class MansionPositionEnvelopeResponse(_StrictModel):
    result: MansionPositionResponse
    provenance: MansionProvenanceResponse


class MansionBulkRequest(_StrictModel):
    positions: dict[str, float] = Field(min_length=1, max_length=MANAZIL_BULK_MAX_ITEMS)
    mode: MansionComputationMode = MansionComputationMode.tropical
    jd_ut: float | None = None
    ayanamsa_system: str = "Lahiri"
    ayanamsa_mode: str = "true"
    tradition: MansionTraditionName = MansionTraditionName.al_biruni

    @field_validator("positions")
    @classmethod
    def _valid_positions(cls, value: dict[str, float]) -> dict[str, float]:
        cleaned: dict[str, float] = {}
        for name, longitude in value.items():
            stripped = name.strip()
            if not stripped:
                raise ValueError("position keys must be non-empty")
            if not math.isfinite(longitude):
                raise ValueError("position longitudes must be finite")
            cleaned[stripped] = longitude
        return cleaned

    @field_validator("jd_ut")
    @classmethod
    def _finite_jd(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("jd_ut must be finite")
        return value

    @field_validator("ayanamsa_system", "ayanamsa_mode")
    @classmethod
    def _non_empty_string(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("string fields must be non-empty")
        return stripped


class MansionBulkResponse(_StrictModel):
    results: dict[str, MansionPositionResponse]
    total: int
    provenance: MansionProvenanceResponse


class MansionTraditionLookupResponse(_StrictModel):
    mansion_index: int
    tradition: MansionTraditionName
    nature: str
    signification: str
    provenance: MansionProvenanceResponse
