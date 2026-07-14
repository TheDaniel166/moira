"""Typed transport models for the bounded Western electional profile."""

from __future__ import annotations

import math
from typing import Any, Literal

from pydantic import Field, field_validator

from moira.constants import HOUSE_SYSTEM_NAMES

from .common import _StrictModel


RAMESEY_PROFILE_ID = "ramesey_moon_condition_v1"
RAMESEY_HOUSE_SYSTEMS = tuple(HOUSE_SYSTEM_NAMES)

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


class RameseyRemedyWitnessResponse(_StrictModel):
    remedy_id: str
    applicability: RameseyRemedyApplicabilityValue
    triggering_rule_ids: list[str]
    unavoidable_time_urgency: bool | None
    source_reference: str
    instructions: list[str]
    uncomputed_requirements: list[str]
    assessment_semantics: Literal["instruction_only_not_fulfillment_assessment"]
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
    remedy_fulfillment_assessment: Literal["not_computed"] = "not_computed"
    stage_sequence: list[str]


class RameseyMoonConditionResponse(_StrictModel):
    evaluation: RameseyMoonConditionEvaluationResponse
    transport_provenance: WesternElectionalTransportProvenanceResponse


__all__ = [
    "RAMESEY_HOUSE_SYSTEMS",
    "RAMESEY_PROFILE_ID",
    "RameseyClauseWitnessResponse",
    "RameseyMeasurementResponse",
    "RameseyMoonConditionEvaluationResponse",
    "RameseyMoonConditionRequest",
    "RameseyMoonConditionResponse",
    "RameseyRemedyApplicabilityValue",
    "RameseyRemedyWitnessResponse",
    "RameseyRuleStateValue",
    "RameseyRuleWitnessResponse",
    "RameseyStatusValue",
    "WesternElectionalTransportProvenanceResponse",
]
