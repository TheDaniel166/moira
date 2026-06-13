"""Transport models for P12-11 caller-supplied Lord of the Turn profile route."""

from __future__ import annotations

from enum import StrEnum
from math import isfinite
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


CLASSICAL_PLANETS = ("Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon")
CLASSICAL_PLANET_SET = frozenset(CLASSICAL_PLANETS)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LordOfTheTurnMethodRequest(StrEnum):
    AL_QABISI = "al_qabisi"
    EGYPTIAN_AL_SIJZI = "egyptian_al_sijzi"


def _strict_bool(value: bool, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a boolean")
    return value


def _strict_int(value: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")
    return value


def _finite_float(value: Any, field_name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a finite number")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a finite number") from exc
    if not isfinite(parsed):
        raise ValueError(f"{field_name} must be finite")
    return parsed


def _clean_planet_name(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a planet name string")
    planet = value.strip()
    if not planet:
        raise ValueError(f"{field_name} must be non-empty")
    if planet not in CLASSICAL_PLANET_SET:
        raise ValueError(f"{field_name} must be one of {list(CLASSICAL_PLANETS)!r}")
    return planet


def _clean_longitude_map(value: Any, field_name: str) -> dict[str, float]:
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object")
    cleaned: dict[str, float] = {}
    for raw_planet, raw_longitude in value.items():
        planet = _clean_planet_name(raw_planet, f"{field_name} key")
        if planet in cleaned:
            raise ValueError(f"{field_name} contains duplicate planet {planet!r}")
        cleaned[planet] = _finite_float(raw_longitude, f"{field_name}[{planet!r}]")
    return cleaned


def _clean_house_map(value: Any, field_name: str) -> dict[str, int]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object")
    cleaned: dict[str, int] = {}
    for raw_planet, raw_house in value.items():
        planet = _clean_planet_name(raw_planet, f"{field_name} key")
        if planet in cleaned:
            raise ValueError(f"{field_name} contains duplicate planet {planet!r}")
        house = _strict_int(raw_house, f"{field_name}[{planet!r}]")
        if house < 1 or house > 12:
            raise ValueError(f"{field_name}[{planet!r}] must be in the range 1..12")
        cleaned[planet] = house
    return cleaned


def _clean_planet_list(value: Any, field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list")
    cleaned: list[str] = []
    seen: set[str] = set()
    for index, raw_planet in enumerate(value):
        planet = _clean_planet_name(raw_planet, f"{field_name}[{index}]")
        if planet in seen:
            raise ValueError(f"{field_name} contains duplicate planet {planet!r}")
        cleaned.append(planet)
        seen.add(planet)
    return cleaned


class LordOfTheTurnSRChartRequest(_StrictModel):
    sr_asc: float
    planets: dict[str, float]
    house_placements: dict[str, int] = Field(default_factory=dict)
    is_night: bool = False
    retrograde_planets: list[str] = Field(default_factory=list)
    sr_lot_fortune: float | None = None

    @field_validator("sr_asc", mode="before")
    @classmethod
    def _valid_sr_asc(cls, value: Any) -> float:
        return _finite_float(value, "sr_asc")

    @field_validator("planets", mode="before")
    @classmethod
    def _valid_planets(cls, value: Any) -> dict[str, float]:
        cleaned = _clean_longitude_map(value, "planets")
        if not cleaned:
            raise ValueError("planets must contain at least one classical planet")
        return cleaned

    @field_validator("house_placements", mode="before")
    @classmethod
    def _valid_house_placements(cls, value: Any) -> dict[str, int]:
        return _clean_house_map(value, "house_placements")

    @field_validator("is_night", mode="before")
    @classmethod
    def _valid_is_night(cls, value: bool) -> bool:
        return _strict_bool(value, "is_night")

    @field_validator("retrograde_planets", mode="before")
    @classmethod
    def _valid_retrograde_planets(cls, value: Any) -> list[str]:
        return _clean_planet_list(value, "retrograde_planets")

    @field_validator("sr_lot_fortune", mode="before")
    @classmethod
    def _valid_sr_lot_fortune(cls, value: Any) -> float | None:
        if value is None:
            return None
        return _finite_float(value, "sr_lot_fortune")

    @model_validator(mode="after")
    def _valid_chart_consistency(self) -> "LordOfTheTurnSRChartRequest":
        planets = set(self.planets)
        missing_houses = sorted(set(self.house_placements) - planets)
        if missing_houses:
            raise ValueError(
                "house_placements keys must also be present in planets: "
                + ", ".join(missing_houses)
            )
        missing_retrogrades = sorted(set(self.retrograde_planets) - planets)
        if missing_retrogrades:
            raise ValueError(
                "retrograde_planets must also be present in planets: "
                + ", ".join(missing_retrogrades)
            )
        return self


class LordOfTheTurnProfileRequest(_StrictModel):
    natal_asc: float
    age: int = Field(ge=0)
    sr_chart: LordOfTheTurnSRChartRequest
    method: LordOfTheTurnMethodRequest = LordOfTheTurnMethodRequest.AL_QABISI
    combust_orb: float = Field(default=8.5, gt=0)
    include_validation: bool = True

    @field_validator("natal_asc", mode="before")
    @classmethod
    def _valid_natal_asc(cls, value: Any) -> float:
        return _finite_float(value, "natal_asc")

    @field_validator("age", mode="before")
    @classmethod
    def _valid_age(cls, value: int) -> int:
        return _strict_int(value, "age")

    @field_validator("combust_orb", mode="before")
    @classmethod
    def _valid_combust_orb(cls, value: Any) -> float:
        parsed = _finite_float(value, "combust_orb")
        if parsed <= 0:
            raise ValueError("combust_orb must be positive")
        return parsed

    @field_validator("include_validation", mode="before")
    @classmethod
    def _valid_include_validation(cls, value: bool) -> bool:
        return _strict_bool(value, "include_validation")


class LordOfTheTurnProfectionResponse(_StrictModel):
    natal_asc: float
    age: int
    profected_longitude: float
    profected_sign: str
    profected_degree_in_sign: float
    profected_sign_index: int


class LordOfTheTurnCandidateResponse(_StrictModel):
    planet: str
    role: str
    sr_house: int | None
    is_combust: bool
    is_retrograde: bool
    is_well_placed: bool
    blocker_reasons: list[str]
    witnesses_target: bool
    testimony_count: int


class LordOfTheTurnResultResponse(_StrictModel):
    lord: str
    method: str
    selection_reason: str
    sign_of_year: str
    age: int
    is_fallback: bool
    winning_candidate: LordOfTheTurnCandidateResponse | None
    blocked_candidates: list[LordOfTheTurnCandidateResponse]


class LordOfTheTurnConditionProfileResponse(_StrictModel):
    lord: str
    sign_of_year: str
    sr_is_night: bool
    sect_light: str
    lord_witnesses_sr_asc: bool
    lord_sr_house: int | None
    is_fallback: bool
    condition_mode: str


class LordOfTheTurnPolicyResponse(_StrictModel):
    method: str
    combust_orb: float


class LordOfTheTurnValidationResponse(_StrictModel):
    included: bool
    passed: bool | None
    failures: list[str] | None


class LordOfTheTurnProvenanceResponse(_StrictModel):
    source_module: str = "moira.lord_of_the_turn"
    engine_entrypoint: str = "lord_of_turn"
    validation_entrypoint: str = "validate_lord_of_turn_output"
    method: str
    combust_orb: float
    sr_chart_owner: str = "caller_supplied"
    solar_return_construction_owner: str = "not_this_route"
    house_calculation_owner: str = "not_this_route"
    ephemeris_derivation_owner: str = "not_this_route"
    sect_owner: str = "caller_supplied_sr_is_night"
    witnessing_target: str = "sr_asc_or_sect_light"
    testimony_count_policy: str = "binary_dignity_type_count_not_weighted_almuten"
    al_qabisi_selection_policy: str = "sequential_succession_no_simultaneous_tiebreak"
    annual_hierarchy_orchestration: str = "not_computed"
    interpretation_policy: str = "not_provided"
    domicile_only_mode: bool
    stage_sequence: list[str]


class LordOfTheTurnProfileResponse(_StrictModel):
    profile: LordOfTheTurnConditionProfileResponse
    result: LordOfTheTurnResultResponse
    profection: LordOfTheTurnProfectionResponse
    candidates: list[LordOfTheTurnCandidateResponse]
    policy: LordOfTheTurnPolicyResponse
    validation: LordOfTheTurnValidationResponse
    provenance: LordOfTheTurnProvenanceResponse
