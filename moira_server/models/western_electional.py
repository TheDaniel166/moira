"""Typed transport models for the bounded Western electional profile."""

from __future__ import annotations

import math
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from moira.constants import HOUSE_SYSTEM_NAMES

from .common import _StrictModel
from .relationship import MoonConnectionFlowResponse


RAMESEY_PROFILE_ID = "ramesey_moon_condition_v1"
SAHL_PROFILE_ID = "sahl_moon_condition_v1"
SAHL_MATTER_PROFILE_IDS = (
    "sahl_lending_v1",
    "sahl_investment_v1",
    "sahl_purchase_v1",
    "sahl_sale_v1",
    "sahl_building_v1",
    "sahl_demolition_v1",
    "sahl_land_v1",
    "sahl_wells_and_rivers_v1",
    "sahl_planting_v1",
    "sahl_sowing_v1",
)
DOROTHEUS_PROFILE_ID = "dorotheus_moon_condition_v1"
DOROTHEUS_ROOTED_CONTEXT_PROFILE_ID = "dorotheus_rooted_context_v1"
DOROTHEUS_CONSTRUCTION_PROFILE_ID = "dorotheus_construction_v1"
DOROTHEUS_MATTER_PROFILE_IDS = (
    "dorotheus_demolition_v1",
    "dorotheus_leasing_v1",
    "dorotheus_buying_and_selling_v1",
    "dorotheus_lunar_price_timing_v1",
    "dorotheus_land_purchase_v1",
)
WESTERN_PROFILE_SCAN_MAX_SPAN_DAYS = 31.0
WESTERN_PROFILE_SCAN_MAX_POINTS = 256
WESTERN_PROFILE_SCAN_MAX_WINDOWS = 64
WESTERN_PROFILE_SCAN_MIN_STEP_DAYS = 1.0 / 24.0
RAMESEY_HOUSE_SYSTEMS = tuple(HOUSE_SYSTEM_NAMES)
SAHL_HOUSE_SYSTEMS = tuple(HOUSE_SYSTEM_NAMES)
DOROTHEUS_HOUSE_SYSTEMS = tuple(HOUSE_SYSTEM_NAMES)
LILLY_PERFECTION_PROFILE_ID = "lilly_1647_perfection_v1"
LILLY_PERFECTION_MAX_SPAN_DAYS = 31.0
WESTERN_ELECTIONAL_JUDGEMENT_PROFILE_ID = "western_electional_judgement_v1"
WESTERN_ELECTIONAL_RANKING_PROFILE_ID = "western_electional_ranking_v1"
WESTERN_ELECTIONAL_JUDGEMENT_WINDOWS_PROFILE_ID = (
    "western_electional_judgement_windows_v1"
)

TraditionalPlanetValue = Literal[
    "Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"
]
ZodiacSignValue = Literal[
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]
LillyPerfectionKindValue = Literal[
    "direct_perfection", "translation_of_light", "collection_of_light",
    "prohibition", "refranation", "frustration",
]
WesternElectionalRankingContributionIdValue = Literal[
    "direct_perfection_present",
    "translation_of_light_present",
    "collection_of_light_present",
]

RameseyRuleStateValue = Literal["clear", "triggered", "not_evaluable"]
RameseyStatusValue = Literal[
    "clear_of_profile_impediments",
    "one_or_more_profile_impediments",
    "indeterminate",
]
RameseyRemedyApplicabilityValue = Literal[
    "not_applicable",
    "applicable",
    "indeterminate",
]
RameseyRemedyClauseStateValue = Literal[
    "fulfilled", "not_fulfilled", "indeterminate"
]
RameseyRemedyFulfillmentValue = Literal[
    "fulfilled", "not_fulfilled", "indeterminate"
]
WesternProfileIdValue = Literal[
    "ramesey_moon_condition_v1",
    "sahl_moon_condition_v1",
    "dorotheus_moon_condition_v1",
]
WesternQualificationStatusValue = Literal[
    "clear_of_profile_impediments",
    "one_or_more_profile_impediments",
    "indeterminate",
]
DorotheusMatterProfileIdValue = Literal[
    "dorotheus_demolition_v1",
    "dorotheus_leasing_v1",
    "dorotheus_buying_and_selling_v1",
    "dorotheus_lunar_price_timing_v1",
    "dorotheus_land_purchase_v1",
]
DorotheusMatterProfileStatusValue = Literal[
    "clear_of_explicit_profile_impediments",
    "one_or_more_explicit_profile_impediments",
    "descriptive_witnesses_only",
    "indeterminate",
]
SahlMatterProfileIdValue = Literal[
    "sahl_lending_v1",
    "sahl_investment_v1",
    "sahl_purchase_v1",
    "sahl_sale_v1",
    "sahl_building_v1",
    "sahl_demolition_v1",
    "sahl_land_v1",
    "sahl_wells_and_rivers_v1",
    "sahl_planting_v1",
    "sahl_sowing_v1",
]
SahlMatterProfileStatusValue = Literal[
    "clear_of_explicit_profile_gates",
    "one_or_more_explicit_profile_gates",
    "indeterminate",
]
LunarEclipticHemisphereValue = Literal[
    "north", "south", "on_ecliptic_numerical_root"
]
LunarLatitudeMotionValue = Literal[
    "northward", "southward", "stationary_within_numerical_tolerance"
]
LunarNodeCrossingDirectionValue = Literal[
    "ascending_south_to_north", "descending_north_to_south"
]
LunarNodeCrossingRelationValue = Literal[
    "previous", "current_within_numerical_tolerance", "next"
]


def _finite_number(value: Any, field_name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a finite number")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a finite number") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{field_name} must be finite")
    return parsed


class LunarEclipticDirectionRequest(_StrictModel):
    jd_ut: float

    @field_validator("jd_ut", mode="before")
    @classmethod
    def _finite_jd(cls, value: Any) -> float:
        return _finite_number(value, "jd_ut")


class LunarNodeCrossingResponse(_StrictModel):
    jd_ut: float
    direction: LunarNodeCrossingDirectionValue
    longitude_deg: float
    latitude_residual_deg: float
    latitude_rate_deg_per_day: float
    hours_from_query: float


class LunarEclipticDirectionPolicyResponse(_StrictModel):
    policy_id: Literal["lunar_ecliptic_direction_v1"]
    search_span_days: float
    scan_step_days: float
    latitude_rate_sample_days: float
    latitude_zero_tolerance_deg: float
    latitude_rate_zero_tolerance_deg_per_day: float
    bisection_iterations: int


class LunarEclipticDirectionResponse(_StrictModel):
    jd_ut: float
    latitude_deg: float
    latitude_rate_deg_per_day: float
    hemisphere: LunarEclipticHemisphereValue
    motion: LunarLatitudeMotionValue
    previous_crossing: LunarNodeCrossingResponse
    next_crossing: LunarNodeCrossingResponse
    nearest_crossing: LunarNodeCrossingResponse
    nearest_crossing_relation: LunarNodeCrossingRelationValue
    policy: LunarEclipticDirectionPolicyResponse
    reference_frame: str
    timescale: str
    provenance: str
    interpretation_scope: Literal["astronomical_witness_only_no_doctrinal_region"]


class RameseyMoonConditionRequest(_StrictModel):
    profile_id: Literal["ramesey_moon_condition_v1"] = RAMESEY_PROFILE_ID
    jd_ut: float
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    house_system: str
    unavoidable_time_urgency: bool | None = None

    @field_validator("jd_ut", "latitude", "longitude", mode="before")
    @classmethod
    def _finite_coordinates(cls, value: Any, info) -> float:
        return _finite_number(value, info.field_name)

    @field_validator("house_system", mode="before")
    @classmethod
    def _known_house_system(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("house_system must be a string")
        code = value.strip()
        if code not in RAMESEY_HOUSE_SYSTEMS:
            raise ValueError(
                f"house_system must be one of {list(RAMESEY_HOUSE_SYSTEMS)!r}"
            )
        return code

    @field_validator("unavoidable_time_urgency", mode="before")
    @classmethod
    def _strict_urgency(cls, value: Any) -> bool | None:
        if value is None or isinstance(value, bool):
            return value
        raise ValueError("unavoidable_time_urgency must be a boolean or null")


SahlBurntPathVariantValue = Literal[
    "sahl_text_indeterminate_no_numeric_endpoints",
    "dykes_glossary_fall_degrees_19_libra_to_3_scorpio",
    "later_fifteen_degrees_15_libra_to_15_scorpio",
]
SahlEighthRuleVariantValue = Literal[
    "arabic_al_rijal_twelfth_part",
    "latin_twelfth_sign",
]


class SahlMoonConditionRequest(_StrictModel):
    profile_id: Literal["sahl_moon_condition_v1"] = SAHL_PROFILE_ID
    jd_ut: float
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    house_system: str
    burnt_path_variant: SahlBurntPathVariantValue
    eighth_rule_variant: SahlEighthRuleVariantValue = "arabic_al_rijal_twelfth_part"

    @field_validator("jd_ut", "latitude", "longitude", mode="before")
    @classmethod
    def _finite_coordinates(cls, value: Any, info) -> float:
        return _finite_number(value, info.field_name)

    @field_validator("house_system", mode="before")
    @classmethod
    def _known_house_system(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("house_system must be a string")
        code = value.strip()
        if code not in SAHL_HOUSE_SYSTEMS:
            raise ValueError(
                f"house_system must be one of {list(SAHL_HOUSE_SYSTEMS)!r}"
            )
        return code


class SahlMatterProfileRequest(_StrictModel):
    profile_id: SahlMatterProfileIdValue
    jd_ut: float
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    house_system: str
    burnt_path_variant: SahlBurntPathVariantValue
    eighth_rule_variant: SahlEighthRuleVariantValue = "arabic_al_rijal_twelfth_part"

    @field_validator("jd_ut", "latitude", "longitude", mode="before")
    @classmethod
    def _finite_coordinates(cls, value: Any, info) -> float:
        return _finite_number(value, info.field_name)

    @field_validator("house_system", mode="before")
    @classmethod
    def _known_house_system(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("house_system must be a string")
        code = value.strip()
        if code not in SAHL_HOUSE_SYSTEMS:
            raise ValueError(
                f"house_system must be one of {list(SAHL_HOUSE_SYSTEMS)!r}"
            )
        return code


class DorotheusMoonConditionRequest(_StrictModel):
    profile_id: Literal["dorotheus_moon_condition_v1"] = DOROTHEUS_PROFILE_ID
    jd_ut: float
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    house_system: str
    unavoidable_time_urgency: bool | None = None

    @field_validator("jd_ut", "latitude", "longitude", mode="before")
    @classmethod
    def _finite_coordinates(cls, value: Any, info) -> float:
        return _finite_number(value, info.field_name)

    @field_validator("house_system", mode="before")
    @classmethod
    def _known_house_system(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("house_system must be a string")
        code = value.strip()
        if code not in DOROTHEUS_HOUSE_SYSTEMS:
            raise ValueError(
                f"house_system must be one of {list(DOROTHEUS_HOUSE_SYSTEMS)!r}"
            )
        return code

    @field_validator("unavoidable_time_urgency", mode="before")
    @classmethod
    def _strict_urgency(cls, value: Any) -> bool | None:
        if value is None or isinstance(value, bool):
            return value
        raise ValueError("unavoidable_time_urgency must be a boolean or null")


class RameseyMeasurementResponse(_StrictModel):
    name: str
    value: float | str | bool | None
    units: str | None = None
    comparison: str | None = None
    threshold: float | str | bool | None = None


class RameseyClauseWitnessResponse(_StrictModel):
    clause_id: str
    state: RameseyRuleStateValue
    policy_id: str
    policy_reference: str
    measurements: list[RameseyMeasurementResponse]
    explanation: str


class RameseyRuleWitnessResponse(_StrictModel):
    rule_id: str
    source_order: int = Field(ge=1, le=10)
    state: RameseyRuleStateValue
    clauses: list[RameseyClauseWitnessResponse]
    source_reference: str
    modifiers: list[str]


class RameseyRemedyClauseWitnessResponse(_StrictModel):
    clause_id: str
    state: RameseyRemedyClauseStateValue
    policy_id: str
    policy_reference: str
    measurements: list[RameseyMeasurementResponse]
    explanation: str


class RameseyRemedyWitnessResponse(_StrictModel):
    remedy_id: str
    applicability: RameseyRemedyApplicabilityValue
    triggering_rule_ids: list[str]
    unavoidable_time_urgency: bool | None
    source_reference: str
    instructions: list[str]
    fulfillment: RameseyRemedyFulfillmentValue
    clauses: list[RameseyRemedyClauseWitnessResponse]
    uncomputed_requirements: list[str]
    assessment_semantics: Literal["tri_state_non_erasing_fulfillment_assessment"]
    erases_triggered_rules: Literal[False]


class RameseyMoonConditionEvaluationResponse(_StrictModel):
    jd_ut: float
    profile_id: Literal["ramesey_moon_condition_v1"]
    profile_version: str
    status: RameseyStatusValue
    triggered_rule_ids: list[str]
    not_evaluable_rule_ids: list[str]
    rules: list[RameseyRuleWitnessResponse]
    remedies: list[RameseyRemedyWitnessResponse]
    position_product: str
    reader_provenance: str
    latitude: float
    longitude: float
    requested_house_system: str | None
    effective_house_system: str | None
    house_fallback: bool | None
    election_class: Literal["ephemeral"]
    matter_scope: str
    complete_electional_judgement: Literal[False]
    advice_language: Literal["not_provided"]
    recommendation_language: Literal["not_provided"]


class WesternElectionalTransportProvenanceResponse(_StrictModel):
    source_module: Literal["moira.western_electional"] = "moira.western_electional"
    engine_entrypoint: Literal["ramesey_moon_condition_at"] = (
        "ramesey_moon_condition_at"
    )
    facade_entrypoint: Literal["Moira.ramesey_moon_condition_at"] = (
        "Moira.ramesey_moon_condition_at"
    )
    route_semantics: Literal["single_moment_bounded_profile_evaluation"] = (
        "single_moment_bounded_profile_evaluation"
    )
    western_electional_doctrine: Literal["ramesey_v1_admitted"] = (
        "ramesey_v1_admitted"
    )
    authority: str
    scoring: Literal["not_provided"] = "not_provided"
    recommendation_language: Literal["not_provided"] = "not_provided"
    generic_search_integration: Literal["not_admitted"] = "not_admitted"
    remedy_fulfillment_assessment: Literal["tri_state_non_erasing"] = "tri_state_non_erasing"
    stage_sequence: list[str]


class RameseyMoonConditionResponse(_StrictModel):
    evaluation: RameseyMoonConditionEvaluationResponse
    transport_provenance: WesternElectionalTransportProvenanceResponse


class SahlMeasurementResponse(_StrictModel):
    name: str
    value: float | str | bool | None
    units: str | None = None
    comparison: str | None = None
    threshold: float | str | bool | None = None


class SahlClauseWitnessResponse(_StrictModel):
    clause_id: str
    state: RameseyRuleStateValue
    policy_id: str
    policy_reference: str
    measurements: list[SahlMeasurementResponse]
    explanation: str


class SahlRuleWitnessResponse(_StrictModel):
    rule_id: str
    source_order: int = Field(ge=1, le=10)
    state: RameseyRuleStateValue
    clauses: list[SahlClauseWitnessResponse]
    source_reference: str
    modifiers: list[str]


class SahlMoonConditionEvaluationResponse(_StrictModel):
    jd_ut: float
    profile_id: Literal["sahl_moon_condition_v1"]
    profile_version: str
    status: RameseyStatusValue
    triggered_rule_ids: list[str]
    not_evaluable_rule_ids: list[str]
    rules: list[SahlRuleWitnessResponse]
    position_product: str
    reader_provenance: str
    latitude: float
    longitude: float
    requested_house_system: str | None
    effective_house_system: str | None
    house_fallback: bool | None
    burnt_path_variant: SahlBurntPathVariantValue
    eighth_rule_variant: SahlEighthRuleVariantValue
    election_class: Literal["ephemeral"]
    matter_scope: str
    complete_electional_judgement: Literal[False]
    advice_language: Literal["not_provided"]
    recommendation_language: Literal["not_provided"]


class SahlWesternElectionalTransportProvenanceResponse(_StrictModel):
    source_module: Literal["moira.western_electional"] = "moira.western_electional"
    engine_entrypoint: Literal["sahl_moon_condition_at"] = "sahl_moon_condition_at"
    facade_entrypoint: Literal["Moira.sahl_moon_condition_at"] = (
        "Moira.sahl_moon_condition_at"
    )
    route_semantics: Literal["single_moment_bounded_profile_evaluation"] = (
        "single_moment_bounded_profile_evaluation"
    )
    western_electional_doctrine: Literal["sahl_v1_admitted"] = "sahl_v1_admitted"
    authority: str
    scoring: Literal["not_provided"] = "not_provided"
    recommendation_language: Literal["not_provided"] = "not_provided"
    generic_search_integration: Literal["not_admitted"] = "not_admitted"
    stage_sequence: list[str]


class SahlMoonConditionResponse(_StrictModel):
    evaluation: SahlMoonConditionEvaluationResponse
    transport_provenance: SahlWesternElectionalTransportProvenanceResponse


class SahlMatterClauseWitnessResponse(_StrictModel):
    clause_id: str
    source_order: int = Field(ge=1)
    role: Literal["fortifier", "gate", "outcome", "witness"]
    state: Literal["satisfied", "clear", "triggered", "observed", "not_evaluable"]
    measurements: list[SahlMeasurementResponse]
    explanation: str
    source_reference: str
    policy_id: str


class SahlMatterProfileEvaluationResponse(_StrictModel):
    jd_ut: float
    profile_id: SahlMatterProfileIdValue
    profile_version: Literal["1.0.0"]
    matter: Literal[
        "borrowing_and_lending",
        "investing_money_for_profit",
        "purchasing_goods",
        "selling_goods",
        "building_a_house",
        "destroying_a_house",
        "buying_and_occupying_land",
        "digging_wells_and_diverting_rivers",
        "planting_trees",
        "sowing_seed",
    ]
    status: SahlMatterProfileStatusValue
    moon_condition: SahlMoonConditionEvaluationResponse
    clauses: list[SahlMatterClauseWitnessResponse]
    triggered_clause_ids: list[str]
    not_evaluable_clause_ids: list[str]
    reader_provenance: str
    authorities: list[str]
    source_complete: Literal[True]
    complete_matter_profile: Literal[True]
    numerically_complete: bool
    complete_electional_judgement: Literal[False]
    advice_language: Literal["not_provided"]
    recommendation_language: Literal["not_provided"]
    scoring: Literal["not_provided"]


class SahlMatterProfileTransportProvenanceResponse(_StrictModel):
    source_module: Literal["moira.western_electional"] = "moira.western_electional"
    engine_entrypoint: Literal["sahl_matter_profile_at"] = "sahl_matter_profile_at"
    facade_entrypoint: Literal["Moira.sahl_matter_profile_at"] = "Moira.sahl_matter_profile_at"
    route_semantics: Literal["single_moment_named_matter_profile"] = "single_moment_named_matter_profile"
    western_electional_doctrine: Literal["sahl_named_matter_profiles_admitted"] = (
        "sahl_named_matter_profiles_admitted"
    )
    authority: str
    scoring: Literal["not_provided"] = "not_provided"
    recommendation_language: Literal["not_provided"] = "not_provided"
    stage_sequence: list[str]


class SahlMatterProfileResponse(_StrictModel):
    evaluation: SahlMatterProfileEvaluationResponse
    transport_provenance: SahlMatterProfileTransportProvenanceResponse


class DorotheusMeasurementResponse(_StrictModel):
    name: str
    value: float | str | bool | None
    units: str | None = None
    comparison: str | None = None
    threshold: float | str | bool | None = None


class DorotheusClauseWitnessResponse(_StrictModel):
    clause_id: str
    state: RameseyRuleStateValue
    policy_id: str
    policy_reference: str
    measurements: list[DorotheusMeasurementResponse]
    explanation: str


class DorotheusRuleWitnessResponse(_StrictModel):
    rule_id: str
    source_order: int = Field(ge=1, le=11)
    state: RameseyRuleStateValue
    clauses: list[DorotheusClauseWitnessResponse]
    source_reference: str
    modifiers: list[str]


class DorotheusRemedyWitnessResponse(_StrictModel):
    remedy_id: str
    applicability: RameseyRemedyApplicabilityValue
    triggering_rule_ids: list[str]
    unavoidable_time_urgency: bool | None
    source_reference: str
    instructions: list[str]
    uncomputed_requirements: list[str]
    assessment_semantics: Literal["instruction_only_not_fulfillment_assessment"]
    erases_triggered_rules: Literal[False]


class DorotheusMoonConditionEvaluationResponse(_StrictModel):
    jd_ut: float
    profile_id: Literal["dorotheus_moon_condition_v1"]
    profile_version: str
    status: RameseyStatusValue
    triggered_rule_ids: list[str]
    not_evaluable_rule_ids: list[str]
    rules: list[DorotheusRuleWitnessResponse]
    remedies: list[DorotheusRemedyWitnessResponse]
    position_product: str
    reader_provenance: str
    latitude: float
    longitude: float
    requested_house_system: str | None
    effective_house_system: str | None
    house_fallback: bool | None
    election_class: Literal["ephemeral"]
    matter_scope: str
    complete_electional_judgement: Literal[False]
    advice_language: Literal["not_provided"]
    recommendation_language: Literal["not_provided"]


class DorotheusWesternElectionalTransportProvenanceResponse(_StrictModel):
    source_module: Literal["moira.western_electional"] = "moira.western_electional"
    engine_entrypoint: Literal["dorotheus_moon_condition_at"] = (
        "dorotheus_moon_condition_at"
    )
    facade_entrypoint: Literal["Moira.dorotheus_moon_condition_at"] = (
        "Moira.dorotheus_moon_condition_at"
    )
    route_semantics: Literal["single_moment_bounded_profile_evaluation"] = (
        "single_moment_bounded_profile_evaluation"
    )
    western_electional_doctrine: Literal["dorotheus_v1_admitted"] = (
        "dorotheus_v1_admitted"
    )
    authority: str
    scoring: Literal["not_provided"] = "not_provided"
    recommendation_language: Literal["not_provided"] = "not_provided"
    generic_search_integration: Literal["not_admitted"] = "not_admitted"
    remedy_fulfillment_assessment: Literal["not_computed"] = "not_computed"
    stage_sequence: list[str]


class DorotheusMoonConditionResponse(_StrictModel):
    evaluation: DorotheusMoonConditionEvaluationResponse
    transport_provenance: DorotheusWesternElectionalTransportProvenanceResponse


DorotheusMatterValue = Literal[
    "land_and_management",
    "mercurial_affairs",
    "marriage_sex_and_pleasure",
    "war_and_arms",
    "rulers_and_petitions",
    "manifest_and_prominent",
]
DorotheusElectionClassValue = Literal["ephemeral", "radical"]
DorotheusStrengthValue = Literal["angular", "succedent", "cadent", "not_evaluable"]
DorotheusRootOutcomePatternValue = Literal[
    "good_root_bad_outcome",
    "difficult_root_suitable_outcome",
    "good_root_and_outcome",
    "bad_root_worse_outcome",
    "unclassified",
    "not_evaluable",
]
DorotheusSignificatorConditionValue = Literal[
    "clear_of_computed_impediments",
    "one_or_more_computed_impediments",
    "indeterminate",
]
DorotheusFortificationTestimonyStateValue = Literal[
    "clear", "triggered", "not_evaluable"
]
DorotheusSupplementaryIndicatorStateValue = Literal[
    "evaluated", "not_evaluable"
]


class DorotheusRootedContextRequest(_StrictModel):
    profile_id: Literal["dorotheus_rooted_context_v1"] = DOROTHEUS_ROOTED_CONTEXT_PROFILE_ID
    jd_ut: float
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    house_system: str
    matter: DorotheusMatterValue
    election_class: DorotheusElectionClassValue = "ephemeral"
    natal_jd_ut: float | None = None
    natal_latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    natal_longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    natal_house_system: str | None = None

    @field_validator(
        "jd_ut",
        "latitude",
        "longitude",
        "natal_jd_ut",
        "natal_latitude",
        "natal_longitude",
        mode="before",
    )
    @classmethod
    def _finite_values(cls, value: Any, info) -> float | None:
        if value is None and info.field_name.startswith("natal_"):
            return None
        return _finite_number(value, info.field_name)

    @field_validator("house_system", "natal_house_system", mode="before")
    @classmethod
    def _known_house_system(cls, value: Any, info) -> str | None:
        if value is None and info.field_name == "natal_house_system":
            return None
        if not isinstance(value, str):
            raise ValueError(f"{info.field_name} must be a string")
        code = value.strip()
        if code not in DOROTHEUS_HOUSE_SYSTEMS:
            raise ValueError(
                f"{info.field_name} must be one of {list(DOROTHEUS_HOUSE_SYSTEMS)!r}"
            )
        return code

    @model_validator(mode="after")
    def _natal_contract(self) -> "DorotheusRootedContextRequest":
        natal_values = (
            self.natal_jd_ut,
            self.natal_latitude,
            self.natal_longitude,
            self.natal_house_system,
        )
        if self.election_class == "ephemeral" and any(
            value is not None for value in natal_values
        ):
            raise ValueError("ephemeral election_class rejects natal fields")
        if self.election_class == "radical" and any(
            value is None for value in natal_values
        ):
            raise ValueError("radical election_class requires all natal fields")
        return self


class DorotheusPlacementWitnessResponse(_StrictModel):
    body: str
    role: str
    longitude: float
    sign: str
    house: int | None
    strength: DorotheusStrengthValue
    house_system_is_quadrant: bool
    explanation: str


class DorotheusRootOutcomeWitnessResponse(_StrictModel):
    moon: DorotheusPlacementWitnessResponse
    moon_sign_lord: DorotheusPlacementWitnessResponse
    pattern: DorotheusRootOutcomePatternValue
    outcome_delayed: bool | None
    source_reference: str
    interpretation_scope: Literal["source_named_pattern_not_complete_judgement"]


class DorotheusFortificationTestimonyResponse(_StrictModel):
    testimony_id: str
    state: DorotheusFortificationTestimonyStateValue
    policy_id: str
    observed_value: bool | float | str | list[str] | None
    explanation: str
    source_reference: str


class DorotheusMatterSignificatorWitnessResponse(_StrictModel):
    body: str
    placement: DorotheusPlacementWitnessResponse
    under_rays: bool
    solar_distance_degrees: float | None
    configured_malefics: list[str]
    looks_at_ascendant: bool
    bad_place_evaluated: Literal[True]
    bad_place: bool
    condition: DorotheusSignificatorConditionValue
    fortification_testimonies: list[DorotheusFortificationTestimonyResponse]
    source_reference: str
    combination_law: Literal[
        "triggered_if_any_testimony_triggered_else_indeterminate_if_any_not_evaluable"
    ]


class DorotheusSupplementaryIndicatorResponse(_StrictModel):
    indicator_id: str
    role: str
    state: DorotheusSupplementaryIndicatorStateValue
    body: str | None
    longitude: float | None
    sign: str | None
    ruler: str | None
    placement: DorotheusPlacementWitnessResponse | None
    source_reference: str
    explanation: str


class MoonConnectionResponse(_StrictModel):
    body: str
    aspect_name: str
    angle: float
    jd_query: float
    jd_exact: float
    jd_sign_exit: float
    moon_sign: str
    hours_until_exact: float


class DorotheusRadicalityWitnessResponse(_StrictModel):
    election_class: DorotheusElectionClassValue
    natal_required: bool
    natal_provided: bool
    election_ascendant_sign: str
    election_ascendant_lord: str
    natal_ascendant_sign: str | None
    natal_ascendant_lord: str | None
    assessment_semantics: Literal["evidence_only_not_success_gate"]


class DorotheusRootedContextEvaluationResponse(_StrictModel):
    jd_ut: float
    profile_id: Literal["dorotheus_rooted_context_v1"]
    profile_version: str
    matter: DorotheusMatterValue
    election_class: DorotheusElectionClassValue
    root_outcome: DorotheusRootOutcomeWitnessResponse
    matter_significators: list[DorotheusMatterSignificatorWitnessResponse]
    next_connection: MoonConnectionResponse | None
    next_connection_placement: DorotheusPlacementWitnessResponse | None
    supplementary_indicators: list[DorotheusSupplementaryIndicatorResponse]
    radicality: DorotheusRadicalityWitnessResponse
    reader_provenance: str
    latitude: float
    longitude: float
    requested_house_system: str
    effective_house_system: str
    house_fallback: bool
    authorities: list[str]
    uncomputed_requirements: list[str]
    complete_electional_judgement: Literal[False]
    advice_language: Literal["not_provided"]
    recommendation_language: Literal["not_provided"]


class DorotheusRootedContextTransportProvenanceResponse(_StrictModel):
    source_module: Literal["moira.western_electional"] = "moira.western_electional"
    engine_entrypoint: Literal["dorotheus_rooted_context_at"] = "dorotheus_rooted_context_at"
    facade_entrypoint: Literal["Moira.dorotheus_rooted_context_at"] = "Moira.dorotheus_rooted_context_at"
    route_semantics: Literal["single_moment_rooted_context_evaluation"] = "single_moment_rooted_context_evaluation"
    western_electional_doctrine: Literal["dorotheus_rooted_context_v1_admitted"] = "dorotheus_rooted_context_v1_admitted"
    authority: str
    scoring: Literal["not_provided"] = "not_provided"
    recommendation_language: Literal["not_provided"] = "not_provided"
    generic_search_integration: Literal["not_yet_admitted"] = "not_yet_admitted"
    stage_sequence: list[str]


class DorotheusRootedContextResponse(_StrictModel):
    evaluation: DorotheusRootedContextEvaluationResponse
    transport_provenance: DorotheusRootedContextTransportProvenanceResponse


class DorotheusConstructionRequest(_StrictModel):
    profile_id: Literal["dorotheus_construction_v1"] = DOROTHEUS_CONSTRUCTION_PROFILE_ID
    jd_ut: float
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    house_system: str
    election_class: DorotheusElectionClassValue = "ephemeral"
    natal_jd_ut: float | None = None
    natal_latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    natal_longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    natal_house_system: str | None = None
    unavoidable_time_urgency: bool | None = None

    @field_validator(
        "jd_ut", "latitude", "longitude", "natal_jd_ut", "natal_latitude", "natal_longitude",
        mode="before",
    )
    @classmethod
    def _finite_values(cls, value: Any, info) -> float | None:
        if value is None and info.field_name.startswith("natal_"):
            return None
        return _finite_number(value, info.field_name)

    @field_validator("house_system", "natal_house_system", mode="before")
    @classmethod
    def _known_house_system(cls, value: Any, info) -> str | None:
        if value is None and info.field_name == "natal_house_system":
            return None
        if not isinstance(value, str):
            raise ValueError(f"{info.field_name} must be a string")
        code = value.strip()
        if code not in DOROTHEUS_HOUSE_SYSTEMS:
            raise ValueError(
                f"{info.field_name} must be one of {list(DOROTHEUS_HOUSE_SYSTEMS)!r}"
            )
        return code

    @field_validator("unavoidable_time_urgency", mode="before")
    @classmethod
    def _strict_urgency(cls, value: Any) -> bool | None:
        if value is None or isinstance(value, bool):
            return value
        raise ValueError("unavoidable_time_urgency must be a boolean or null")

    @model_validator(mode="after")
    def _natal_contract(self) -> "DorotheusConstructionRequest":
        natal_values = (
            self.natal_jd_ut,
            self.natal_latitude,
            self.natal_longitude,
            self.natal_house_system,
        )
        if self.election_class == "ephemeral" and any(value is not None for value in natal_values):
            raise ValueError("ephemeral election_class rejects natal fields")
        if self.election_class == "radical" and any(value is None for value in natal_values):
            raise ValueError("radical election_class requires all natal fields")
        return self


class DorotheusSignNatureWitnessResponse(_StrictModel):
    ascendant_longitude: float
    ascendant_sign: str
    geographic_latitude: float
    true_obliquity_degrees: float
    ascensional_arc_degrees: float | None
    ascensional_class: Literal["straight", "crooked", "not_evaluable"]
    base_tempo: str
    configured_fortunes: list[str]
    configured_infortunes: list[str]
    modifier: str
    convertible: bool
    convertible_effect: str
    twin: bool
    twin_effect: str
    chart_sect: Literal["diurnal", "nocturnal"]
    ascendant_sect: Literal["diurnal", "nocturnal"]
    moon_sect: Literal["diurnal", "nocturnal"]
    sect_fit: bool
    source_reference: str


class DorotheusConstructionClauseWitnessResponse(_StrictModel):
    clause_id: str
    source_order: int = Field(ge=1, le=6)
    role: Literal["fortifier", "gate"]
    state: Literal["satisfied", "clear", "triggered", "not_evaluable"]
    measurements: list[DorotheusMeasurementResponse]
    explanation: str
    source_reference: str


class DorotheusConstructionEvaluationResponse(_StrictModel):
    jd_ut: float
    profile_id: Literal["dorotheus_construction_v1"]
    profile_version: str
    status: RameseyStatusValue
    sign_nature: DorotheusSignNatureWitnessResponse
    moon_condition: DorotheusMoonConditionEvaluationResponse
    rooted_context: DorotheusRootedContextEvaluationResponse
    construction_clauses: list[DorotheusConstructionClauseWitnessResponse]
    triggered_clause_ids: list[str]
    not_evaluable_clause_ids: list[str]
    reader_provenance: str
    authorities: list[str]
    matter: Literal["building_construction"]
    election_class: DorotheusElectionClassValue
    source_complete: Literal[True]
    complete_matter_profile: Literal[True]
    numerically_complete: Literal[False]
    complete_electional_judgement: Literal[False]
    advice_language: Literal["not_provided"]
    recommendation_language: Literal["not_provided"]
    scoring: Literal["not_provided"]


class DorotheusConstructionTransportProvenanceResponse(_StrictModel):
    source_module: Literal["moira.western_electional"] = "moira.western_electional"
    engine_entrypoint: Literal["dorotheus_construction_at"] = "dorotheus_construction_at"
    facade_entrypoint: Literal["Moira.dorotheus_construction_at"] = "Moira.dorotheus_construction_at"
    route_semantics: Literal["single_moment_complete_matter_profile"] = "single_moment_complete_matter_profile"
    western_electional_doctrine: Literal["dorotheus_construction_v1_admitted"] = "dorotheus_construction_v1_admitted"
    authority: str
    scoring: Literal["not_provided"] = "not_provided"
    recommendation_language: Literal["not_provided"] = "not_provided"
    generic_search_integration: Literal["not_yet_admitted"] = "not_yet_admitted"
    stage_sequence: list[str]


class DorotheusConstructionResponse(_StrictModel):
    evaluation: DorotheusConstructionEvaluationResponse
    transport_provenance: DorotheusConstructionTransportProvenanceResponse


class DorotheusMoonFlowPolicyRequest(_StrictModel):
    previous_window: Literal["current_sign", "fixed_lookback"]
    previous_lookback_days: float | None = Field(default=None, gt=0.0, le=30.0)
    modern: bool = False

    @field_validator("previous_lookback_days", mode="before")
    @classmethod
    def _finite_lookback(cls, value: Any) -> float | None:
        if value is None:
            return None
        return _finite_number(value, "previous_lookback_days")

    @field_validator("modern", mode="before")
    @classmethod
    def _strict_modern(cls, value: Any) -> bool:
        if not isinstance(value, bool):
            raise ValueError("modern must be a boolean")
        return value

    @model_validator(mode="after")
    def _coherent_window(self) -> "DorotheusMoonFlowPolicyRequest":
        if self.previous_window == "current_sign":
            if self.previous_lookback_days is not None:
                raise ValueError(
                    "current_sign previous window rejects previous_lookback_days"
                )
        elif self.previous_lookback_days is None:
            raise ValueError(
                "fixed_lookback previous window requires previous_lookback_days"
            )
        return self


class DorotheusMatterProfileRequest(DorotheusConstructionRequest):
    profile_id: DorotheusMatterProfileIdValue
    moon_flow_policy: DorotheusMoonFlowPolicyRequest | None = None

    @model_validator(mode="after")
    def _flow_policy(self) -> "DorotheusMatterProfileRequest":
        if self.profile_id in {
            "dorotheus_leasing_v1",
            "dorotheus_buying_and_selling_v1",
        }:
            if self.moon_flow_policy is None:
                raise ValueError(
                    "flow-based profile requires moon_flow_policy because the "
                    "previous-event window is not source-settled"
                )
        elif self.moon_flow_policy is not None:
            raise ValueError("moon_flow_policy is accepted only for flow-based profiles")
        return self


class DorotheusAngularPlaceWitnessResponse(_StrictModel):
    whole_sign_place: Literal[1, 4, 7, 10]
    topic: str
    sign: str
    occupying_fortunes: list[str]
    configured_fortunes: list[str]
    occupying_infortunes: list[str]
    configured_infortunes: list[str]
    source_meaning: str


class DorotheusMatterClauseWitnessResponse(_StrictModel):
    clause_id: str
    source_order: int = Field(ge=1)
    role: Literal["fortifier", "gate", "witness"]
    state: Literal["satisfied", "clear", "triggered", "observed", "not_evaluable"]
    measurements: list[DorotheusMeasurementResponse]
    explanation: str
    source_reference: str


class DorotheusMatterProfileEvaluationResponse(_StrictModel):
    jd_ut: float
    profile_id: DorotheusMatterProfileIdValue
    profile_version: Literal["1.0.0"]
    matter: Literal[
        "building_demolition",
        "leasing",
        "buying_and_selling",
        "lunar_price_timing",
        "land_purchase",
    ]
    status: DorotheusMatterProfileStatusValue
    moon_condition: DorotheusMoonConditionEvaluationResponse
    rooted_context: DorotheusRootedContextEvaluationResponse
    moon_connection_flow: MoonConnectionFlowResponse | None
    clauses: list[DorotheusMatterClauseWitnessResponse]
    angular_places: list[DorotheusAngularPlaceWitnessResponse]
    planetary_strengths: list[DorotheusPlacementWitnessResponse]
    triggered_clause_ids: list[str]
    not_evaluable_clause_ids: list[str]
    reader_provenance: str
    authorities: list[str]
    source_complete: Literal[True]
    complete_matter_profile: Literal[True]
    numerically_complete: bool
    complete_electional_judgement: Literal[False]
    advice_language: Literal["not_provided"]
    recommendation_language: Literal["not_provided"]
    scoring: Literal["not_provided"]


class DorotheusMatterProfileTransportProvenanceResponse(_StrictModel):
    source_module: Literal["moira.western_electional"] = "moira.western_electional"
    engine_entrypoint: Literal["dorotheus_matter_profile_at"] = "dorotheus_matter_profile_at"
    facade_entrypoint: Literal["Moira.dorotheus_matter_profile_at"] = "Moira.dorotheus_matter_profile_at"
    route_semantics: Literal["single_moment_named_matter_profile"] = "single_moment_named_matter_profile"
    western_electional_doctrine: Literal["dorotheus_V8_V9_V11_admitted"] = "dorotheus_V8_V9_V11_admitted"
    authority: str
    scoring: Literal["not_provided"] = "not_provided"
    recommendation_language: Literal["not_provided"] = "not_provided"
    stage_sequence: list[str]


class DorotheusMatterProfileResponse(_StrictModel):
    evaluation: DorotheusMatterProfileEvaluationResponse
    transport_provenance: DorotheusMatterProfileTransportProvenanceResponse


class WesternProfileScanPolicyRequest(_StrictModel):
    step_days: float = 1.0 / 24.0
    merge_gap_days: float | None = None
    max_scan_points: int = Field(default=WESTERN_PROFILE_SCAN_MAX_POINTS, ge=2, le=WESTERN_PROFILE_SCAN_MAX_POINTS)
    max_windows: int = Field(default=WESTERN_PROFILE_SCAN_MAX_WINDOWS, ge=1, le=WESTERN_PROFILE_SCAN_MAX_WINDOWS)

    @field_validator("step_days", "merge_gap_days", mode="before")
    @classmethod
    def _finite_policy_values(cls, value: Any, info) -> float | None:
        if value is None and info.field_name == "merge_gap_days":
            return None
        parsed = _finite_number(value, info.field_name)
        if info.field_name == "step_days" and not WESTERN_PROFILE_SCAN_MIN_STEP_DAYS <= parsed <= 1.0:
            raise ValueError(
                f"step_days must be in [{WESTERN_PROFILE_SCAN_MIN_STEP_DAYS:g}, 1]"
            )
        if info.field_name == "merge_gap_days" and parsed < 0.0:
            raise ValueError("merge_gap_days must be non-negative")
        return parsed


class WesternProfileWindowsRequest(_StrictModel):
    profile_id: WesternProfileIdValue
    jd_start: float
    jd_end: float
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    house_system: str
    qualification_statuses: list[WesternQualificationStatusValue] = Field(
        min_length=1, max_length=3
    )
    policy: WesternProfileScanPolicyRequest = Field(default_factory=WesternProfileScanPolicyRequest)
    unavoidable_time_urgency: bool | None = None
    sahl_burnt_path_variant: SahlBurntPathVariantValue | None = None
    sahl_eighth_rule_variant: SahlEighthRuleVariantValue | None = None
    include_qualifying_jds: bool = True

    @field_validator("jd_start", "jd_end", "latitude", "longitude", mode="before")
    @classmethod
    def _finite_scan_values(cls, value: Any, info) -> float:
        return _finite_number(value, info.field_name)

    @field_validator("house_system", mode="before")
    @classmethod
    def _known_scan_house_system(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("house_system must be a string")
        code = value.strip()
        if code not in RAMESEY_HOUSE_SYSTEMS:
            raise ValueError(
                f"house_system must be one of {list(RAMESEY_HOUSE_SYSTEMS)!r}"
            )
        return code

    @field_validator("qualification_statuses")
    @classmethod
    def _unique_statuses(cls, value: list[str]) -> list[str]:
        if len(set(value)) != len(value):
            raise ValueError("qualification_statuses must not contain duplicates")
        return value

    @field_validator("unavoidable_time_urgency", "include_qualifying_jds", mode="before")
    @classmethod
    def _strict_scan_bools(cls, value: Any, info):
        if info.field_name == "unavoidable_time_urgency" and value is None:
            return None
        if not isinstance(value, bool):
            raise ValueError(f"{info.field_name} must be a boolean")
        return value

    @model_validator(mode="after")
    def _bounded_profile_scan(self) -> "WesternProfileWindowsRequest":
        if self.jd_end <= self.jd_start:
            raise ValueError("jd_end must be greater than jd_start")
        span = self.jd_end - self.jd_start
        if span > WESTERN_PROFILE_SCAN_MAX_SPAN_DAYS:
            raise ValueError(
                f"search span may not exceed {WESTERN_PROFILE_SCAN_MAX_SPAN_DAYS:g} days"
            )
        quotient = span / self.policy.step_days
        nearest = round(quotient)
        ratio_tolerance = max(
            1e-12,
            4.0 * math.ulp(max(abs(self.jd_start), abs(self.jd_end))) / self.policy.step_days,
        )
        if abs(quotient - nearest) <= ratio_tolerance:
            quotient = float(nearest)
        count = int(math.floor(quotient)) + 1
        if count > self.policy.max_scan_points:
            raise ValueError(
                f"scan point count {count} exceeds maximum {self.policy.max_scan_points}"
            )
        if self.profile_id == SAHL_PROFILE_ID:
            if self.unavoidable_time_urgency is not None:
                raise ValueError("Sahl profile does not accept unavoidable_time_urgency")
            if self.sahl_burnt_path_variant is None:
                raise ValueError(
                    "Sahl profile requires an explicit sahl_burnt_path_variant"
                )
        elif self.sahl_burnt_path_variant is not None or self.sahl_eighth_rule_variant is not None:
            raise ValueError("Sahl variants are valid only for the Sahl profile")
        return self


class WesternProfileParameterResponse(_StrictModel):
    name: str
    value: str | bool | None


class WesternProfileStatusCountResponse(_StrictModel):
    status: WesternQualificationStatusValue
    count: int = Field(ge=0)


class WesternProfileSampleWitnessResponse(_StrictModel):
    jd_ut: float
    status: WesternQualificationStatusValue
    qualifies: bool
    triggered_rule_ids: list[str]
    not_evaluable_rule_ids: list[str]


class WesternProfileWindowResponse(_StrictModel):
    jd_start: float
    jd_end: float
    duration_hours: float
    qualifying_count: int = Field(ge=1)
    qualifying_jds: list[float] | None


class WesternProfileScanPolicyResponse(_StrictModel):
    step_days: float
    requested_merge_gap_days: float | None
    effective_merge_gap_days: float
    max_scan_points: int
    max_windows: int
    qualification_statuses: list[WesternQualificationStatusValue]


class WesternProfileScanBoundsResponse(_StrictModel):
    max_span_days: float = WESTERN_PROFILE_SCAN_MAX_SPAN_DAYS
    min_step_days: float = WESTERN_PROFILE_SCAN_MIN_STEP_DAYS
    max_scan_points: int = WESTERN_PROFILE_SCAN_MAX_POINTS
    max_windows: int = WESTERN_PROFILE_SCAN_MAX_WINDOWS


class WesternProfileScanProvenanceResponse(_StrictModel):
    source_module: Literal["moira._western_electional_scan"] = "moira._western_electional_scan"
    engine_entrypoint: Literal["scan_western_electional_profile"] = "scan_western_electional_profile"
    facade_entrypoint: Literal["Moira.western_electional_profile_windows"] = "Moira.western_electional_profile_windows"
    route_semantics: Literal["bounded_discrete_profile_status_windows"] = "bounded_discrete_profile_status_windows"
    stage_sequence: list[str]


class WesternProfileWindowsResponse(_StrictModel):
    profile_id: WesternProfileIdValue
    profile_version: str
    jd_start: float
    jd_end: float
    latitude: float
    longitude: float
    house_system: str
    policy: WesternProfileScanPolicyResponse
    scan_point_count: int
    status_counts: list[WesternProfileStatusCountResponse]
    samples: list[WesternProfileSampleWitnessResponse]
    windows: list[WesternProfileWindowResponse]
    windows_truncated: bool
    profile_parameters: list[WesternProfileParameterResponse]
    predicate_semantics: Literal["profile_status_exact_match_at_discrete_sample"]
    continuous_boundary_claim: Literal["not_provided"]
    scoring: Literal["not_provided"]
    ranking: Literal["not_provided"]
    advice: Literal["not_provided"]
    recommendation: Literal["not_provided"]
    bounds: WesternProfileScanBoundsResponse
    provenance: WesternProfileScanProvenanceResponse


class LillyPerfectionRequest(_StrictModel):
    profile_id: Literal["lilly_1647_perfection_v1"] = LILLY_PERFECTION_PROFILE_ID
    jd_start: float
    jd_end: float
    significator_a: TraditionalPlanetValue
    significator_b: TraditionalPlanetValue
    is_day_chart: bool

    @field_validator("jd_start", "jd_end")
    @classmethod
    def finite_jd(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("Julian days must be finite")
        return value

    @model_validator(mode="after")
    def valid_interval(self):
        if self.significator_a == self.significator_b:
            raise ValueError("significators must be distinct")
        span = self.jd_end - self.jd_start
        if span <= 0.0 or span > LILLY_PERFECTION_MAX_SPAN_DAYS:
            raise ValueError("analysis interval must be positive and at most 31 days")
        return self


class ClassicalBodyStateResponse(_StrictModel):
    body: TraditionalPlanetValue
    longitude: float
    speed: float
    sign: ZodiacSignValue


class ClassicalPerfectionEventResponse(_StrictModel):
    event_id: str
    jd_ut: float
    kind: Literal["aspect_exact", "station_retrograde", "station_direct", "sign_ingress"]
    actor: TraditionalPlanetValue
    target: TraditionalPlanetValue | None = None
    aspect: Literal["conjunction", "sextile", "square", "trine", "opposition"] | None = None
    directional_angle_deg: float | None = None
    longitude_deg: float | None = None
    sign_before: ZodiacSignValue | None = None
    sign_after: ZodiacSignValue | None = None


class LillyPerfectionWitnessResponse(_StrictModel):
    kind: LillyPerfectionKindValue
    state: Literal["present", "absent", "indeterminate"]
    actors: list[TraditionalPlanetValue]
    event_ids: list[str]
    explanation: str
    source_reference: str
    reception_bases: list[str]


class LillyPerfectionPolicyResponse(_StrictModel):
    profile_id: Literal["lilly_1647_perfection_v1"]
    profile_version: Literal["1.0.0"]
    aspect_scope: Literal["tropical_zodiacal_ptolemaic_exact"]
    contact_scope: Literal["summed_planetary_moieties"]
    ingress_policy: Literal["prior_ingress_makes_application_indeterminate"]
    tie_policy: Literal["events_within_one_second_are_indeterminate"]
    translation_reception: Literal["house_triplicity_or_term"]
    collection_reception: Literal["any_lilly_essential_dignity"]
    bounds_doctrine: Literal["egyptian"]
    triplicity_doctrine: Literal["dorothean_sect_active"]
    planetary_moiety_table: Literal["lilly_1647_traditional_moieties"]
    longitude_product: Literal["apparent_geocentric_true_ecliptic_of_date"]
    motion_product: Literal["astrometric_geocentric_longitude_rate"]
    input_timescale: Literal["ut1_with_internal_tt_ephemeris_conversion"]
    max_span_days: Literal[31.0]


class ClassicalPerfectionEvaluationResponse(_StrictModel):
    jd_start: float
    jd_end: float
    significator_a: TraditionalPlanetValue
    significator_b: TraditionalPlanetValue
    is_day_chart: bool
    profile_id: Literal["lilly_1647_perfection_v1"]
    profile_version: Literal["1.0.0"]
    policy: LillyPerfectionPolicyResponse
    initial_states: list[ClassicalBodyStateResponse]
    events: list[ClassicalPerfectionEventResponse]
    witnesses: list[LillyPerfectionWitnessResponse]
    present_kinds: list[LillyPerfectionKindValue]
    indeterminate_kinds: list[LillyPerfectionKindValue]
    reader_provenance: str
    authorities: list[str]
    complete_electional_judgement: Literal[False]
    scoring: Literal["not_provided"]
    advice_language: Literal["not_provided"]


class LillyPerfectionTransportProvenanceResponse(_StrictModel):
    source_module: Literal["moira.classical_perfection"] = "moira.classical_perfection"
    engine_entrypoint: Literal["lilly_perfection_at"] = "lilly_perfection_at"
    facade_entrypoint: Literal["Moira.lilly_perfection_at"] = "Moira.lilly_perfection_at"
    route_semantics: Literal["bounded_named_perfection_event_trace"] = "bounded_named_perfection_event_trace"
    doctrine: Literal["lilly_1647_only"] = "lilly_1647_only"
    excluded_profiles: list[str] = Field(default_factory=lambda: ["sahl", "bonatti", "reflection_of_light"])
    stage_sequence: list[str]


class LillyPerfectionResponse(_StrictModel):
    evaluation: ClassicalPerfectionEvaluationResponse
    transport_provenance: LillyPerfectionTransportProvenanceResponse


class WesternElectionalJudgementRequest(DorotheusConstructionRequest):
    profile_id: Literal["western_electional_judgement_v1"] = (
        WESTERN_ELECTIONAL_JUDGEMENT_PROFILE_ID
    )
    matter_profile_id: DorotheusMatterProfileIdValue | SahlMatterProfileIdValue
    perfection_significator_a: TraditionalPlanetValue
    perfection_significator_b: TraditionalPlanetValue
    perfection_interval_days: float = Field(gt=0.0, le=LILLY_PERFECTION_MAX_SPAN_DAYS)
    moon_flow_policy: DorotheusMoonFlowPolicyRequest | None = None
    sahl_burnt_path_variant: SahlBurntPathVariantValue | None = None
    sahl_eighth_rule_variant: SahlEighthRuleVariantValue | None = None

    @field_validator("perfection_interval_days", mode="before")
    @classmethod
    def _finite_perfection_interval(cls, value: Any) -> float:
        return _finite_number(value, "perfection_interval_days")

    @model_validator(mode="after")
    def _judgement_selection_contract(self) -> "WesternElectionalJudgementRequest":
        if self.perfection_significator_a == self.perfection_significator_b:
            raise ValueError("perfection significators must be distinct")
        is_sahl = self.matter_profile_id.startswith("sahl_")
        is_flow = self.matter_profile_id in {
            "dorotheus_leasing_v1",
            "dorotheus_buying_and_selling_v1",
        }
        if is_sahl:
            if self.election_class != "ephemeral":
                raise ValueError("Sahl judgement admits only ephemeral elections")
            if any(value is not None for value in (
                self.natal_jd_ut,
                self.natal_latitude,
                self.natal_longitude,
                self.natal_house_system,
                self.unavoidable_time_urgency,
                self.moon_flow_policy,
            )):
                raise ValueError(
                    "Sahl judgement rejects Dorothean natal, urgency, and flow inputs"
                )
            if self.sahl_burnt_path_variant is None:
                raise ValueError("Sahl judgement requires sahl_burnt_path_variant")
            if self.sahl_eighth_rule_variant is None:
                raise ValueError("Sahl judgement requires sahl_eighth_rule_variant")
        else:
            if self.sahl_burnt_path_variant is not None or self.sahl_eighth_rule_variant is not None:
                raise ValueError("Dorotheus judgement rejects Sahl variant inputs")
            if is_flow and self.moon_flow_policy is None:
                raise ValueError(
                    "flow-based Dorotheus judgement requires moon_flow_policy"
                )
            if not is_flow and self.moon_flow_policy is not None:
                raise ValueError(
                    "moon_flow_policy is accepted only for flow-based Dorotheus profiles"
                )
        return self


class WesternElectionalJudgementPolicyResponse(_StrictModel):
    profile_id: Literal["western_electional_judgement_v1"]
    profile_version: Literal["1.0.0"]
    composition_authority: Literal["moira_owned_explicit_cross_source_composition"]
    matter_policy: Literal["one_admitted_named_matter_profile_required"]
    perfection_policy: Literal["lilly_1647_caller_declared_significators_required"]
    rooted_context_policy: Literal["dorotheus_embedded_sahl_not_applicable"]
    natal_policy: Literal["selected_matter_profile_owns_radicality_requirement"]
    precedence_policy: Literal["impediment_then_indeterminacy"]
    completion_policy: Literal["all_required_components_complete_with_constructive_perfection"]
    unresolved_policy: Literal["blocking_unresolved_requirements_propagate_indeterminacy"]
    scoring: Literal["not_provided"]
    advice_language: Literal["not_provided"]
    recommendation_language: Literal["not_provided"]


class WesternElectionalJudgementSelectionResponse(_StrictModel):
    doctrine: Literal[
        "dorotheus_matter_with_lilly_perfection",
        "sahl_matter_with_lilly_perfection",
    ]
    matter_profile_id: DorotheusMatterProfileIdValue | SahlMatterProfileIdValue
    perfection_profile_id: Literal["lilly_1647_perfection_v1"]
    perfection_significator_a: TraditionalPlanetValue
    perfection_significator_b: TraditionalPlanetValue
    perfection_interval_days: float
    election_class: DorotheusElectionClassValue
    natal_input_provided: bool
    natal_jd_ut: float | None
    natal_latitude: float | None
    natal_longitude: float | None
    natal_house_system: str | None
    unavoidable_time_urgency: bool | None
    moon_flow_previous_window: Literal["current_sign", "fixed_lookback"] | None
    moon_flow_previous_lookback_days: float | None
    moon_flow_modern: bool | None
    sahl_burnt_path_variant: SahlBurntPathVariantValue | None
    sahl_eighth_rule_variant: SahlEighthRuleVariantValue | None


class WesternElectionalComponentSummaryResponse(_StrictModel):
    component_id: Literal[
        "general_moon_condition",
        "rooted_context",
        "matter_profile",
        "perfection_path",
        "natal_or_radical_context",
        "fortification_and_remedy",
    ]
    profile_id: str | None
    state: Literal[
        "complete", "impeded", "indeterminate", "not_applicable"
    ]
    explanation: str


class WesternElectionalRequirementWitnessResponse(_StrictModel):
    requirement_id: str
    component_id: str
    state: Literal["unresolved", "excluded"]
    blocking: bool
    explanation: str
    source_reference: str


class WesternElectionalJudgementEvaluationResponse(_StrictModel):
    jd_ut: float
    latitude: float
    longitude: float
    requested_house_system: str
    profile_id: Literal["western_electional_judgement_v1"]
    profile_version: Literal["1.0.0"]
    state: Literal[
        "complete_under_profile", "impeded", "indeterminate"
    ]
    policy: WesternElectionalJudgementPolicyResponse
    selection: WesternElectionalJudgementSelectionResponse
    general_moon_condition: DorotheusMoonConditionEvaluationResponse | SahlMoonConditionEvaluationResponse
    rooted_context: DorotheusRootedContextEvaluationResponse | None
    matter_profile: DorotheusMatterProfileEvaluationResponse | SahlMatterProfileEvaluationResponse
    perfection_path: ClassicalPerfectionEvaluationResponse
    components: list[WesternElectionalComponentSummaryResponse]
    unresolved_requirements: list[WesternElectionalRequirementWitnessResponse]
    excluded_requirements: list[WesternElectionalRequirementWitnessResponse]
    reader_provenance: str
    authorities: list[str]
    complete_electional_judgement: Literal[True]
    scoring: Literal["not_provided"]
    advice_language: Literal["not_provided"]
    recommendation_language: Literal["not_provided"]


class WesternElectionalJudgementTransportProvenanceResponse(_StrictModel):
    source_module: Literal["moira.western_electional"] = "moira.western_electional"
    engine_entrypoint: Literal["western_electional_judgement_at"] = "western_electional_judgement_at"
    facade_entrypoint: Literal["Moira.western_electional_judgement_at"] = "Moira.western_electional_judgement_at"
    route_semantics: Literal["single_moment_complete_profile_composition"] = "single_moment_complete_profile_composition"
    composition_authority: Literal["moira_owned_not_historical_synthesis"] = "moira_owned_not_historical_synthesis"
    scoring: Literal["not_provided"] = "not_provided"
    advice_language: Literal["not_provided"] = "not_provided"
    stage_sequence: list[str]


class WesternElectionalJudgementResponse(_StrictModel):
    evaluation: WesternElectionalJudgementEvaluationResponse
    transport_provenance: WesternElectionalJudgementTransportProvenanceResponse


class WesternElectionalRankingWeightRequest(_StrictModel):
    contribution_id: WesternElectionalRankingContributionIdValue
    weight: float

    @field_validator("weight", mode="before")
    @classmethod
    def _finite_nonzero_weight(cls, value: Any) -> float:
        parsed = _finite_number(value, "weight")
        if parsed == 0.0:
            raise ValueError("weight must be nonzero")
        return parsed


class WesternElectionalRankingRequest(_StrictModel):
    profile_id: Literal["western_electional_ranking_v1"] = (
        WESTERN_ELECTIONAL_RANKING_PROFILE_ID
    )
    candidate_jds: list[float] = Field(min_length=2, max_length=64)
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    house_system: str
    matter_profile_id: DorotheusMatterProfileIdValue | SahlMatterProfileIdValue
    perfection_significator_a: TraditionalPlanetValue
    perfection_significator_b: TraditionalPlanetValue
    perfection_interval_days: float = Field(gt=0.0, le=LILLY_PERFECTION_MAX_SPAN_DAYS)
    weights: list[WesternElectionalRankingWeightRequest] = Field(
        min_length=1,
        max_length=3,
    )
    election_class: DorotheusElectionClassValue = "ephemeral"
    natal_jd_ut: float | None = None
    natal_latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    natal_longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    natal_house_system: str | None = None
    unavoidable_time_urgency: bool | None = None
    moon_flow_policy: DorotheusMoonFlowPolicyRequest | None = None
    sahl_burnt_path_variant: SahlBurntPathVariantValue | None = None
    sahl_eighth_rule_variant: SahlEighthRuleVariantValue | None = None

    @field_validator("candidate_jds", mode="before")
    @classmethod
    def _finite_distinct_candidates(cls, value: Any) -> list[float]:
        if not isinstance(value, (list, tuple)):
            raise ValueError("candidate_jds must be a list")
        parsed = [_finite_number(item, "candidate_jds") for item in value]
        if len(set(parsed)) != len(parsed):
            raise ValueError("candidate_jds must contain distinct instants")
        return parsed

    @field_validator(
        "latitude",
        "longitude",
        "perfection_interval_days",
        "natal_jd_ut",
        "natal_latitude",
        "natal_longitude",
        mode="before",
    )
    @classmethod
    def _finite_values(cls, value: Any, info) -> float | None:
        if value is None and info.field_name.startswith("natal_"):
            return None
        return _finite_number(value, info.field_name)

    @field_validator("house_system", "natal_house_system", mode="before")
    @classmethod
    def _known_house_system(cls, value: Any, info) -> str | None:
        if value is None and info.field_name == "natal_house_system":
            return None
        if not isinstance(value, str):
            raise ValueError(f"{info.field_name} must be a string")
        code = value.strip()
        if code not in DOROTHEUS_HOUSE_SYSTEMS:
            raise ValueError(
                f"{info.field_name} must be one of {list(DOROTHEUS_HOUSE_SYSTEMS)!r}"
            )
        return code

    @field_validator("unavoidable_time_urgency", mode="before")
    @classmethod
    def _strict_urgency(cls, value: Any) -> bool | None:
        if value is None or isinstance(value, bool):
            return value
        raise ValueError("unavoidable_time_urgency must be a boolean or null")

    @model_validator(mode="after")
    def _ranking_contract(self) -> "WesternElectionalRankingRequest":
        if len({item.contribution_id for item in self.weights}) != len(self.weights):
            raise ValueError("ranking contribution weights must be unique")
        if self.perfection_significator_a == self.perfection_significator_b:
            raise ValueError("perfection significators must be distinct")
        natal_values = (
            self.natal_jd_ut,
            self.natal_latitude,
            self.natal_longitude,
            self.natal_house_system,
        )
        if self.election_class == "ephemeral" and any(
            value is not None for value in natal_values
        ):
            raise ValueError("ephemeral election_class rejects natal fields")
        if self.election_class == "radical" and any(
            value is None for value in natal_values
        ):
            raise ValueError("radical election_class requires all natal fields")
        is_sahl = self.matter_profile_id.startswith("sahl_")
        is_flow = self.matter_profile_id in {
            "dorotheus_leasing_v1",
            "dorotheus_buying_and_selling_v1",
        }
        if is_sahl:
            if self.election_class != "ephemeral":
                raise ValueError("Sahl ranking admits only ephemeral elections")
            if any(value is not None for value in (
                self.natal_jd_ut,
                self.natal_latitude,
                self.natal_longitude,
                self.natal_house_system,
                self.unavoidable_time_urgency,
                self.moon_flow_policy,
            )):
                raise ValueError(
                    "Sahl ranking rejects Dorothean natal, urgency, and flow inputs"
                )
            if self.sahl_burnt_path_variant is None:
                raise ValueError("Sahl ranking requires sahl_burnt_path_variant")
            if self.sahl_eighth_rule_variant is None:
                raise ValueError("Sahl ranking requires sahl_eighth_rule_variant")
        else:
            if self.sahl_burnt_path_variant is not None or self.sahl_eighth_rule_variant is not None:
                raise ValueError("Dorotheus ranking rejects Sahl variant inputs")
            if is_flow and self.moon_flow_policy is None:
                raise ValueError("flow-based Dorotheus ranking requires moon_flow_policy")
            if not is_flow and self.moon_flow_policy is not None:
                raise ValueError(
                    "moon_flow_policy is accepted only for flow-based Dorotheus profiles"
                )
        return self


class WesternElectionalRankingPolicyResponse(_StrictModel):
    profile_id: Literal["western_electional_ranking_v1"]
    profile_version: Literal["1.0.0"]
    ranking_authority: Literal["moira_owned_caller_weighted_numeric_decision_support"]
    candidate_scope: Literal["explicit_distinct_instants_same_phase8_selection"]
    contribution_scope: Literal["constructive_lilly_perfection_presence_only"]
    weight_policy: Literal["caller_supplied_unique_finite_nonzero_no_default"]
    normalization_policy: Literal["weighted_sum_divided_by_sum_absolute_weights"]
    eligibility_policy: Literal["complete_under_profile_only"]
    incomplete_candidate_policy: Literal["partition_with_complete_judgement_evidence"]
    tie_break_policy: Literal["score_descending_jd_ascending_input_index_ascending"]
    min_candidates: Literal[2]
    max_candidates: Literal[64]
    score_minimum: Literal[-1.0]
    score_maximum: Literal[1.0]
    advice_language: Literal["not_admitted"]
    recommendation_language: Literal["not_admitted"]
    empirical_claim: Literal["not_provided"]


class WesternElectionalRankingWeightResponse(_StrictModel):
    contribution_id: WesternElectionalRankingContributionIdValue
    weight: float


class WesternElectionalRankingContributionResponse(_StrictModel):
    contribution_id: WesternElectionalRankingContributionIdValue
    raw_value: Literal[0.0, 1.0]
    normalization: Literal["binary_presence_identity"]
    normalized_value: Literal[0.0, 1.0]
    weight: float
    weighted_value: float


class WesternElectionalRankedCandidateResponse(_StrictModel):
    input_index: int = Field(ge=0)
    jd_ut: float
    state: Literal["ranked_complete_under_profile"]
    rank: int = Field(ge=1)
    score: float = Field(ge=-1.0, le=1.0)
    normalization_divisor: float = Field(gt=0.0)
    contributions: list[WesternElectionalRankingContributionResponse]
    judgement: WesternElectionalJudgementEvaluationResponse


class WesternElectionalExcludedCandidateResponse(_StrictModel):
    input_index: int = Field(ge=0)
    jd_ut: float
    state: Literal["excluded_impeded", "excluded_indeterminate"]
    reason: str
    judgement: WesternElectionalJudgementEvaluationResponse


class WesternElectionalRankingEvaluationResponse(_StrictModel):
    profile_id: Literal["western_electional_ranking_v1"]
    profile_version: Literal["1.0.0"]
    policy: WesternElectionalRankingPolicyResponse
    weights: list[WesternElectionalRankingWeightResponse]
    candidate_jds: list[float]
    ranked_candidates: list[WesternElectionalRankedCandidateResponse]
    excluded_candidates: list[WesternElectionalExcludedCandidateResponse]
    reader_provenance: str
    authorities: list[str]
    ranking_is_decision_support: Literal[True]
    advice_language: Literal["not_admitted"]
    recommendation_language: Literal["not_admitted"]
    empirical_claim: Literal["not_provided"]


class WesternElectionalRankingTransportProvenanceResponse(_StrictModel):
    source_module: Literal["moira.western_electional"] = "moira.western_electional"
    engine_entrypoint: Literal["western_electional_ranking_at"] = "western_electional_ranking_at"
    facade_entrypoint: Literal["Moira.western_electional_ranking_at"] = "Moira.western_electional_ranking_at"
    route_semantics: Literal["explicit_candidate_caller_weighted_decision_support"] = "explicit_candidate_caller_weighted_decision_support"
    historical_score_claim: Literal["not_claimed"] = "not_claimed"
    advice_product: Literal["not_admitted"] = "not_admitted"
    stage_sequence: list[str]


class WesternElectionalRankingResponse(_StrictModel):
    evaluation: WesternElectionalRankingEvaluationResponse
    transport_provenance: WesternElectionalRankingTransportProvenanceResponse


class WesternElectionalJudgementWindowPolicyRequest(_StrictModel):
    mode: Literal["sampled", "partially_event_refined"] = "sampled"
    step_days: float = Field(default=0.25, ge=1.0 / 24.0, le=31.0)
    transition_tolerance_seconds: float = Field(default=60.0, ge=0.1, le=3600.0)
    max_refinement_iterations: int = Field(default=0, ge=0, le=24)
    max_initial_samples: int = Field(default=64, ge=2, le=64)
    max_evaluations: int = Field(default=256, ge=2, le=256)
    max_windows: int = Field(default=64, ge=1, le=64)
    max_transitions: int = Field(default=63, ge=0, le=63)
    max_event_seeds: int = Field(default=128, ge=0, le=128)
    max_span_days: float = Field(default=31.0, gt=0.0, le=31.0)

    @field_validator(
        "step_days",
        "transition_tolerance_seconds",
        "max_span_days",
        mode="before",
    )
    @classmethod
    def _finite_policy_values(cls, value: Any, info) -> float:
        return _finite_number(value, info.field_name)

    @model_validator(mode="after")
    def _coherent_resources(self) -> "WesternElectionalJudgementWindowPolicyRequest":
        if self.max_evaluations < self.max_initial_samples:
            raise ValueError("max_evaluations cannot be less than max_initial_samples")
        if self.mode == "sampled" and self.max_refinement_iterations != 0:
            raise ValueError("sampled mode requires max_refinement_iterations=0")
        if self.mode == "partially_event_refined" and self.max_refinement_iterations < 1:
            raise ValueError(
                "partially_event_refined mode requires max_refinement_iterations >= 1"
            )
        return self


class WesternElectionalJudgementWindowsRequest(_StrictModel):
    profile_id: Literal["western_electional_judgement_windows_v1"] = (
        WESTERN_ELECTIONAL_JUDGEMENT_WINDOWS_PROFILE_ID
    )
    jd_start: float
    jd_end: float
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    house_system: str
    matter_profile_id: DorotheusMatterProfileIdValue | SahlMatterProfileIdValue
    perfection_significator_a: TraditionalPlanetValue
    perfection_significator_b: TraditionalPlanetValue
    perfection_interval_days: float = Field(gt=0.0, le=LILLY_PERFECTION_MAX_SPAN_DAYS)
    election_class: DorotheusElectionClassValue = "ephemeral"
    natal_jd_ut: float | None = None
    natal_latitude: float | None = Field(default=None, ge=-90.0, le=90.0)
    natal_longitude: float | None = Field(default=None, ge=-180.0, le=180.0)
    natal_house_system: str | None = None
    unavoidable_time_urgency: bool | None = None
    moon_flow_policy: DorotheusMoonFlowPolicyRequest | None = None
    sahl_burnt_path_variant: SahlBurntPathVariantValue | None = None
    sahl_eighth_rule_variant: SahlEighthRuleVariantValue | None = None
    policy: WesternElectionalJudgementWindowPolicyRequest = Field(
        default_factory=WesternElectionalJudgementWindowPolicyRequest
    )

    @field_validator(
        "jd_start",
        "jd_end",
        "latitude",
        "longitude",
        "perfection_interval_days",
        "natal_jd_ut",
        "natal_latitude",
        "natal_longitude",
        mode="before",
    )
    @classmethod
    def _finite_values(cls, value: Any, info) -> float | None:
        if value is None and info.field_name.startswith("natal_"):
            return None
        return _finite_number(value, info.field_name)

    @field_validator("house_system", "natal_house_system", mode="before")
    @classmethod
    def _known_house_system(cls, value: Any, info) -> str | None:
        if value is None and info.field_name == "natal_house_system":
            return None
        if not isinstance(value, str):
            raise ValueError(f"{info.field_name} must be a string")
        code = value.strip()
        if code not in DOROTHEUS_HOUSE_SYSTEMS:
            raise ValueError(
                f"{info.field_name} must be one of {list(DOROTHEUS_HOUSE_SYSTEMS)!r}"
            )
        return code

    @field_validator("unavoidable_time_urgency", mode="before")
    @classmethod
    def _strict_urgency(cls, value: Any) -> bool | None:
        if value is None or isinstance(value, bool):
            return value
        raise ValueError("unavoidable_time_urgency must be a boolean or null")

    @model_validator(mode="after")
    def _window_contract(self) -> "WesternElectionalJudgementWindowsRequest":
        if self.jd_end <= self.jd_start:
            raise ValueError("jd_start must be less than jd_end")
        if self.jd_end - self.jd_start > self.policy.max_span_days:
            raise ValueError("scan span exceeds policy.max_span_days")
        sample_count = 2
        current = self.jd_start + self.policy.step_days
        while current < self.jd_end:
            sample_count += 1
            current += self.policy.step_days
        if sample_count > self.policy.max_initial_samples:
            raise ValueError("initial sample count exceeds policy.max_initial_samples")
        if self.perfection_significator_a == self.perfection_significator_b:
            raise ValueError("perfection significators must be distinct")
        natal_values = (
            self.natal_jd_ut,
            self.natal_latitude,
            self.natal_longitude,
            self.natal_house_system,
        )
        if self.election_class == "ephemeral" and any(
            value is not None for value in natal_values
        ):
            raise ValueError("ephemeral election_class rejects natal fields")
        if self.election_class == "radical" and any(
            value is None for value in natal_values
        ):
            raise ValueError("radical election_class requires all natal fields")
        is_sahl = self.matter_profile_id.startswith("sahl_")
        is_flow = self.matter_profile_id in {
            "dorotheus_leasing_v1",
            "dorotheus_buying_and_selling_v1",
        }
        if is_sahl:
            if self.election_class != "ephemeral":
                raise ValueError("Sahl judgement windows admit only ephemeral elections")
            if any(value is not None for value in (
                self.natal_jd_ut,
                self.natal_latitude,
                self.natal_longitude,
                self.natal_house_system,
                self.unavoidable_time_urgency,
                self.moon_flow_policy,
            )):
                raise ValueError(
                    "Sahl judgement windows reject Dorothean natal, urgency, and flow inputs"
                )
            if self.sahl_burnt_path_variant is None:
                raise ValueError("Sahl judgement windows require sahl_burnt_path_variant")
            if self.sahl_eighth_rule_variant is None:
                raise ValueError("Sahl judgement windows require sahl_eighth_rule_variant")
        else:
            if self.sahl_burnt_path_variant is not None or self.sahl_eighth_rule_variant is not None:
                raise ValueError("Dorotheus judgement windows reject Sahl variant inputs")
            if is_flow and self.moon_flow_policy is None:
                raise ValueError(
                    "flow-based Dorotheus judgement windows require moon_flow_policy"
                )
            if not is_flow and self.moon_flow_policy is not None:
                raise ValueError(
                    "moon_flow_policy is accepted only for flow-based Dorotheus profiles"
                )
        return self


class WesternElectionalJudgementWindowPolicyResponse(_StrictModel):
    profile_id: Literal["western_electional_judgement_windows_v1"]
    profile_version: Literal["1.0.0"]
    mode: Literal["sampled", "partially_event_refined"]
    step_days: float
    transition_tolerance_seconds: float
    max_refinement_iterations: int
    max_initial_samples: int
    max_evaluations: int
    max_windows: int
    max_transitions: int
    max_event_seeds: int
    max_span_days: float
    boundary_inventory: Literal["incomplete_profile_transition_inventory"]
    transition_detector: Literal["complete_phase8_signature_change"]
    exact_boundary_claimed: Literal[False]
    continuous_truth_claimed: Literal[False]
    ranking_integration: Literal["separate_phase9_endpoint_not_applied"]
    advice_language: Literal["not_admitted"]
    recommendation_language: Literal["not_admitted"]


class WesternElectionalStatePairResponse(_StrictModel):
    item_id: str
    state: str


class WesternElectionalJudgementSignatureResponse(_StrictModel):
    judgement_state: Literal["complete_under_profile", "impeded", "indeterminate"]
    moon_status: str
    matter_status: str
    component_states: list[WesternElectionalStatePairResponse]
    moon_rule_states: list[WesternElectionalStatePairResponse]
    matter_clause_states: list[WesternElectionalStatePairResponse]
    rooted_significator_conditions: list[WesternElectionalStatePairResponse]
    rooted_supplementary_states: list[WesternElectionalStatePairResponse]
    perfection_present_kinds: list[LillyPerfectionKindValue]
    perfection_indeterminate_kinds: list[LillyPerfectionKindValue]
    unresolved_requirement_ids: list[str]
    contains_unresolved: bool


class WesternElectionalTransitionCauseResponse(_StrictModel):
    cause_id: str
    before_value: str
    after_value: str
    semantics: Literal[
        "observed_phase8_output_change_not_complete_astronomical_cause"
    ]


class WesternElectionalCandidateEventResponse(_StrictModel):
    event_id: str
    jd_ut: float
    source_component: str
    event_kind: str
    causal_status: Literal["candidate_boundary_seed_not_asserted_cause"]


class WesternElectionalWindowBoundaryResponse(_StrictModel):
    resolution: Literal[
        "request_bound", "sampled_bracket", "adaptively_refined_bracket"
    ]
    estimate_jd_ut: float
    bracket_start_jd_ut: float
    bracket_end_jd_ut: float
    bracket_width_seconds: float
    causes: list[WesternElectionalTransitionCauseResponse]
    candidate_events: list[WesternElectionalCandidateEventResponse]
    doctrine_boundary_exact: Literal[False]


class WesternElectionalJudgementWindowResponse(_StrictModel):
    window_index: int = Field(ge=0)
    exactness: Literal["sampled", "partially_event_refined"]
    jd_start_estimate: float
    jd_end_estimate: float
    start_boundary: WesternElectionalWindowBoundaryResponse
    end_boundary: WesternElectionalWindowBoundaryResponse
    observed_jds: list[float]
    signature: WesternElectionalJudgementSignatureResponse
    representative_judgement: WesternElectionalJudgementEvaluationResponse
    contains_unresolved: bool


class WesternElectionalJudgementWindowScanResponse(_StrictModel):
    jd_start: float
    jd_end: float
    latitude: float
    longitude: float
    requested_house_system: str
    profile_id: Literal["western_electional_judgement_windows_v1"]
    profile_version: Literal["1.0.0"]
    policy: WesternElectionalJudgementWindowPolicyResponse
    windows: list[WesternElectionalJudgementWindowResponse]
    initial_sample_count: int
    total_evaluation_count: int
    transition_count: int
    candidate_events: list[WesternElectionalCandidateEventResponse]
    event_seed_count: int
    reader_provenance: str
    authorities: list[str]
    boundary_inventory_complete: Literal[False]
    exact_boundary_claimed: Literal[False]
    continuous_truth_claimed: Literal[False]
    ranking_integration: Literal["separate_phase9_endpoint_not_applied"]
    advice_language: Literal["not_admitted"]
    recommendation_language: Literal["not_admitted"]


class WesternElectionalJudgementWindowsTransportProvenanceResponse(_StrictModel):
    source_module: Literal["moira.western_electional"] = "moira.western_electional"
    engine_entrypoint: Literal["scan_western_electional_judgement_windows"] = "scan_western_electional_judgement_windows"
    facade_entrypoint: Literal["Moira.western_electional_judgement_windows"] = "Moira.western_electional_judgement_windows"
    route_semantics: Literal["bounded_observed_complete_judgement_windows"] = "bounded_observed_complete_judgement_windows"
    boundary_truth: Literal["sampled_or_partially_refined_never_exact"] = "sampled_or_partially_refined_never_exact"
    ranking_endpoint: Literal["separate"] = "separate"
    advice_product: Literal["not_admitted"] = "not_admitted"
    stage_sequence: list[str]


class WesternElectionalJudgementWindowsResponse(_StrictModel):
    evaluation: WesternElectionalJudgementWindowScanResponse
    transport_provenance: WesternElectionalJudgementWindowsTransportProvenanceResponse


__all__ = [
    "LunarEclipticDirectionRequest",
    "LunarNodeCrossingResponse",
    "LunarEclipticDirectionPolicyResponse",
    "LunarEclipticDirectionResponse",
    "DOROTHEUS_HOUSE_SYSTEMS",
    "DOROTHEUS_PROFILE_ID",
    "DOROTHEUS_ROOTED_CONTEXT_PROFILE_ID",
    "DOROTHEUS_CONSTRUCTION_PROFILE_ID",
    "DOROTHEUS_MATTER_PROFILE_IDS",
    "RAMESEY_HOUSE_SYSTEMS",
    "RAMESEY_PROFILE_ID",
    "SAHL_HOUSE_SYSTEMS",
    "SAHL_MATTER_PROFILE_IDS",
    "SAHL_PROFILE_ID",
    "RameseyClauseWitnessResponse",
    "RameseyMeasurementResponse",
    "RameseyMoonConditionEvaluationResponse",
    "RameseyMoonConditionRequest",
    "RameseyMoonConditionResponse",
    "RameseyRemedyApplicabilityValue",
    "RameseyRemedyClauseStateValue",
    "RameseyRemedyFulfillmentValue",
    "RameseyRemedyClauseWitnessResponse",
    "RameseyRemedyWitnessResponse",
    "RameseyRuleStateValue",
    "RameseyRuleWitnessResponse",
    "RameseyStatusValue",
    "WesternElectionalTransportProvenanceResponse",
    "SahlBurntPathVariantValue",
    "SahlClauseWitnessResponse",
    "SahlEighthRuleVariantValue",
    "SahlMeasurementResponse",
    "SahlMoonConditionEvaluationResponse",
    "SahlMoonConditionRequest",
    "SahlMoonConditionResponse",
    "SahlMatterProfileIdValue",
    "SahlMatterProfileStatusValue",
    "SahlMatterProfileRequest",
    "SahlMatterClauseWitnessResponse",
    "SahlMatterProfileEvaluationResponse",
    "SahlMatterProfileTransportProvenanceResponse",
    "SahlMatterProfileResponse",
    "SahlRuleWitnessResponse",
    "SahlWesternElectionalTransportProvenanceResponse",
    "DorotheusClauseWitnessResponse",
    "DorotheusMeasurementResponse",
    "DorotheusMoonConditionEvaluationResponse",
    "DorotheusMoonConditionRequest",
    "DorotheusMoonConditionResponse",
    "DorotheusRemedyWitnessResponse",
    "DorotheusRuleWitnessResponse",
    "DorotheusWesternElectionalTransportProvenanceResponse",
    "DorotheusRootedContextRequest",
    "DorotheusRootedContextResponse",
    "DorotheusRootedContextEvaluationResponse",
    "DorotheusRootedContextTransportProvenanceResponse",
    "DorotheusPlacementWitnessResponse",
    "DorotheusRootOutcomeWitnessResponse",
    "DorotheusMatterSignificatorWitnessResponse",
    "DorotheusFortificationTestimonyResponse",
    "DorotheusSupplementaryIndicatorResponse",
    "DorotheusRadicalityWitnessResponse",
    "MoonConnectionResponse",
    "DorotheusConstructionRequest",
    "DorotheusConstructionResponse",
    "DorotheusConstructionEvaluationResponse",
    "DorotheusConstructionTransportProvenanceResponse",
    "DorotheusConstructionClauseWitnessResponse",
    "DorotheusSignNatureWitnessResponse",
    "DorotheusMatterProfileIdValue",
    "DorotheusMatterProfileStatusValue",
    "DorotheusMatterProfileRequest",
    "DorotheusMoonFlowPolicyRequest",
    "DorotheusAngularPlaceWitnessResponse",
    "DorotheusMatterClauseWitnessResponse",
    "DorotheusMatterProfileEvaluationResponse",
    "DorotheusMatterProfileTransportProvenanceResponse",
    "DorotheusMatterProfileResponse",
    "WesternProfileScanPolicyRequest",
    "WesternProfileWindowsRequest",
    "WesternProfileParameterResponse",
    "WesternProfileStatusCountResponse",
    "WesternProfileSampleWitnessResponse",
    "WesternProfileWindowResponse",
    "WesternProfileScanPolicyResponse",
    "WesternProfileScanBoundsResponse",
    "WesternProfileScanProvenanceResponse",
    "WesternProfileWindowsResponse",
    "LILLY_PERFECTION_PROFILE_ID",
    "LILLY_PERFECTION_MAX_SPAN_DAYS",
    "TraditionalPlanetValue",
    "ZodiacSignValue",
    "LillyPerfectionKindValue",
    "LillyPerfectionRequest",
    "ClassicalBodyStateResponse",
    "ClassicalPerfectionEventResponse",
    "LillyPerfectionWitnessResponse",
    "LillyPerfectionPolicyResponse",
    "ClassicalPerfectionEvaluationResponse",
    "LillyPerfectionTransportProvenanceResponse",
    "LillyPerfectionResponse",
    "WESTERN_ELECTIONAL_JUDGEMENT_PROFILE_ID",
    "WesternElectionalJudgementRequest",
    "WesternElectionalJudgementPolicyResponse",
    "WesternElectionalJudgementSelectionResponse",
    "WesternElectionalComponentSummaryResponse",
    "WesternElectionalRequirementWitnessResponse",
    "WesternElectionalJudgementEvaluationResponse",
    "WesternElectionalJudgementTransportProvenanceResponse",
    "WesternElectionalJudgementResponse",
    "WESTERN_ELECTIONAL_RANKING_PROFILE_ID",
    "WesternElectionalRankingContributionIdValue",
    "WesternElectionalRankingWeightRequest",
    "WesternElectionalRankingRequest",
    "WesternElectionalRankingPolicyResponse",
    "WesternElectionalRankingWeightResponse",
    "WesternElectionalRankingContributionResponse",
    "WesternElectionalRankedCandidateResponse",
    "WesternElectionalExcludedCandidateResponse",
    "WesternElectionalRankingEvaluationResponse",
    "WesternElectionalRankingTransportProvenanceResponse",
    "WesternElectionalRankingResponse",
    "WESTERN_ELECTIONAL_JUDGEMENT_WINDOWS_PROFILE_ID",
    "WesternElectionalJudgementWindowPolicyRequest",
    "WesternElectionalJudgementWindowsRequest",
    "WesternElectionalJudgementWindowPolicyResponse",
    "WesternElectionalStatePairResponse",
    "WesternElectionalJudgementSignatureResponse",
    "WesternElectionalTransitionCauseResponse",
    "WesternElectionalCandidateEventResponse",
    "WesternElectionalWindowBoundaryResponse",
    "WesternElectionalJudgementWindowResponse",
    "WesternElectionalJudgementWindowScanResponse",
    "WesternElectionalJudgementWindowsTransportProvenanceResponse",
    "WesternElectionalJudgementWindowsResponse",
]
