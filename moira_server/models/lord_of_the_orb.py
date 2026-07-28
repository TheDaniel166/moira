"""Transport models for P12-10 caller-seeded Lord of the Orb routes."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from moira._strenum import StrEnum


LORD_OF_THE_ORB_MAX_YEARS = 252
LORD_OF_THE_ORB_MAX_AGE = LORD_OF_THE_ORB_MAX_YEARS - 1
CHALDEAN_PLANETS = ("Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon")


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LordOfTheOrbCycleKindRequest(StrEnum):
    CONTINUOUS_LOOP = "continuous_loop"
    SINGLE_CYCLE = "single_cycle"


def _clean_birth_planet(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("birth_planet must be a string")
    planet = value.strip()
    if not planet:
        raise ValueError("birth_planet must be non-empty")
    if planet not in CHALDEAN_PLANETS:
        raise ValueError(f"birth_planet must be one of {list(CHALDEAN_PLANETS)!r}")
    return planet


def _strict_bool(value: bool, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a boolean")
    return value


def _strict_int(value: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")
    return value


class LordOfTheOrbBaseRequest(_StrictModel):
    birth_planet: str
    cycle_kind: LordOfTheOrbCycleKindRequest = LordOfTheOrbCycleKindRequest.CONTINUOUS_LOOP
    include_validation: bool = True

    @field_validator("birth_planet", mode="before")
    @classmethod
    def _valid_birth_planet(cls, value: str) -> str:
        return _clean_birth_planet(value)

    @field_validator("include_validation", mode="before")
    @classmethod
    def _valid_include_validation(cls, value: bool) -> bool:
        return _strict_bool(value, "include_validation")


class LordOfTheOrbSequenceRequest(LordOfTheOrbBaseRequest):
    years: int = Field(ge=1, le=LORD_OF_THE_ORB_MAX_YEARS)

    @field_validator("years", mode="before")
    @classmethod
    def _valid_years(cls, value: int) -> int:
        return _strict_int(value, "years")


class LordOfTheOrbCurrentRequest(LordOfTheOrbBaseRequest):
    age: int = Field(ge=0, le=LORD_OF_THE_ORB_MAX_AGE)

    @field_validator("age", mode="before")
    @classmethod
    def _valid_age(cls, value: int) -> int:
        return _strict_int(value, "age")


class LordOfTheOrbBoundsResponse(_StrictModel):
    max_years: int = LORD_OF_THE_ORB_MAX_YEARS
    max_age: int = LORD_OF_THE_ORB_MAX_AGE


class LordOfTheOrbPeriodResponse(_StrictModel):
    year: int
    planet: str
    house: int
    chaldean_index: int
    cycle_kind: str
    house_signification: str
    house_zero_indexed: int
    is_year_one_planet: bool
    is_house_cycle_start: bool
    years_until_next_same_planet: int


class LordOfTheOrbSequenceTruthResponse(_StrictModel):
    birth_planet: str
    cycle_kind: str
    span: int
    planets_in_sequence: list[str]
    is_full_84_year_cycle: bool


class LordOfTheOrbConditionProfileResponse(_StrictModel):
    period: LordOfTheOrbPeriodResponse
    house_signification: str
    hierarchy_rank: int
    house_cycle_number: int
    planet_cycle_number: int
    is_cycle_coincidence: bool
    is_benefic_planet: bool
    is_malefic_planet: bool


class LordOfTheOrbAggregateResponse(_StrictModel):
    benefic_years: list[int]
    malefic_years: list[int]
    planet_year_counts: dict[str, int]
    cycle_coincidence_years: list[int]


class LordOfTheOrbPolicyResponse(_StrictModel):
    cycle_kind: str


class LordOfTheOrbValidationResponse(_StrictModel):
    included: bool
    passed: bool | None
    failures: list[str] | None


class LordOfTheOrbProvenanceResponse(_StrictModel):
    source_module: str = "moira.lord_of_the_orb"
    engine_entrypoint: str
    validation_entrypoint: str = "validate_lord_of_orb_output"
    birth_planet_source: str = "caller_supplied_birth_planetary_hour_ruler"
    planetary_hour_derivation_owner: str = "not_this_route"
    cycle_kind: str
    cycle_basis: str = "Chaldean_order"
    house_cycle_basis: str = "twelve_house_modular_cycle"
    hierarchy_rank: int = 6
    distinct_from: str = "moira.lord_of_the_turn"
    interpretation_policy: str = "not_provided"
    annual_hierarchy_orchestration: str = "not_computed"
    dignity_scoring: str = "not_computed"
    bounds: LordOfTheOrbBoundsResponse = Field(default_factory=LordOfTheOrbBoundsResponse)
    stage_sequence: list[str]


class LordOfTheOrbSequenceResponse(_StrictModel):
    sequence: LordOfTheOrbSequenceTruthResponse
    periods: list[LordOfTheOrbPeriodResponse]
    condition_profiles: list[LordOfTheOrbConditionProfileResponse]
    aggregate: LordOfTheOrbAggregateResponse
    policy: LordOfTheOrbPolicyResponse
    validation: LordOfTheOrbValidationResponse
    provenance: LordOfTheOrbProvenanceResponse


class LordOfTheOrbCurrentResponse(_StrictModel):
    period: LordOfTheOrbPeriodResponse
    condition_profile: LordOfTheOrbConditionProfileResponse
    age: int
    year_of_life: int
    policy: LordOfTheOrbPolicyResponse
    validation: LordOfTheOrbValidationResponse
    provenance: LordOfTheOrbProvenanceResponse
