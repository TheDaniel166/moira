"""Transport models for P12-05 Abu Ma'shar Nine Parts routes."""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


NINE_PARTS_REQUIRED_PLANETS = frozenset(
    {"Sun", "Moon", "Mars", "Jupiter", "Saturn", "North Node"}
)
NinePartsReversalRuleValue = Literal["full_reversal"]
NinePartsHistoricalScopeValue = Literal["evidenced_core_plus_admitted_extension"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _clean_planets(value: dict[str, float]) -> dict[str, float]:
    if not value:
        raise ValueError("planets must contain required body longitudes")

    cleaned: dict[str, float] = {}
    for raw_name, longitude in value.items():
        name = str(raw_name).strip()
        if not name:
            raise ValueError("planet keys must be non-empty")
        if name in cleaned:
            raise ValueError("planet keys must be unique after trimming")
        if not math.isfinite(longitude):
            raise ValueError("planet longitudes must be finite")
        cleaned[name] = longitude

    missing = sorted(NINE_PARTS_REQUIRED_PLANETS - cleaned.keys())
    if missing:
        raise ValueError(f"planets missing required keys: {', '.join(missing)}")
    return cleaned


class NinePartsPolicyRequest(_StrictModel):
    reversal_rule: NinePartsReversalRuleValue = "full_reversal"
    historical_scope: NinePartsHistoricalScopeValue = "evidenced_core_plus_admitted_extension"


class NinePartsAbuMasharRequest(_StrictModel):
    asc: float
    planets: dict[str, float]
    is_night_chart: bool
    policy: NinePartsPolicyRequest | None = None
    include_validation: bool = True

    @field_validator("asc")
    @classmethod
    def _finite_asc(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("asc must be finite")
        return value

    @field_validator("planets")
    @classmethod
    def _valid_planets(cls, value: dict[str, float]) -> dict[str, float]:
        return _clean_planets(value)

    @field_validator("is_night_chart", "include_validation", mode="before")
    @classmethod
    def _strict_boolean(cls, value: bool, info) -> bool:
        if not isinstance(value, bool):
            raise ValueError(f"{info.field_name} must be a boolean")
        return value


class NinePartsPolicyResponse(_StrictModel):
    reversal_rule: str
    historical_scope: str


class NinePartComputationResponse(_StrictModel):
    asc_longitude: float
    add_key: str
    sub_key: str
    add_longitude: float
    sub_longitude: float
    is_night_chart: bool
    formula_reversed: bool
    formula_variant: str
    formula: str


class NinePartResponse(_StrictModel):
    name: str
    planet_association: str | None
    historical_status: str
    meaning: str
    longitude: float
    sign: str
    sign_degree: float
    sign_symbol: str
    dependency_kind: str
    computation: NinePartComputationResponse


class NinePartsDependencyResponse(_StrictModel):
    part: str
    lot_dependencies: list[str]
    is_direct: bool
    dependency_count: int


class NinePartConditionProfileResponse(_StrictModel):
    part: str
    lord: str
    lord_is_part_planet: bool
    is_in_own_sign: bool
    is_derived: bool
    dependency_kind: str
    historical_status: str


class NinePartsAggregateSummaryResponse(_StrictModel):
    is_night_chart: bool
    part_count: int
    direct_part_count: int
    derived_part_count: int
    planetary_part_count: int
    admitted_extension_part_count: int
    nocturnal_formula_count: int
    parts_in_own_sign: list[str]
    unique_lords: list[str]
    dominant_lord: str | None


class NinePartsValidationResponse(_StrictModel):
    passed: bool
    failures: list[str]
    entrypoint: str = "validate_nine_parts_output"


class NinePartsProvenanceResponse(_StrictModel):
    source_module: str = "moira.nine_parts"
    engine_entrypoint: str = "nine_parts_abu_mashar"
    validation_entrypoint: str = "validate_nine_parts_output"
    doctrine: str = "Abu_Mashar_Nine_Parts"
    reversal_rule: str
    historical_scope: str
    night_determination_owner: str = "caller_supplied"
    ascendant_derivation_owner: str = "caller_supplied"
    formula_basis: str = "Asc + Add - Sub mod 360"
    chart_construction: str = "not_computed"
    house_placement: str = "not_computed"
    sect_determination: str = "not_computed"
    stage_sequence: list[str]


class NinePartsAbuMasharResponse(_StrictModel):
    parts: list[NinePartResponse]
    dependency_relations: list[NinePartsDependencyResponse]
    condition_profiles: list[NinePartConditionProfileResponse]
    aggregate: NinePartsAggregateSummaryResponse
    policy: NinePartsPolicyResponse
    validation: NinePartsValidationResponse | None = None
    provenance: NinePartsProvenanceResponse
