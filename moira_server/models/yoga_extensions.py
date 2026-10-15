"""Strict bounded transport for the source-defined yoga catalogue/evaluator."""

from typing import Annotated, Literal

from pydantic import ConfigDict, Field, StrictBool, model_validator

from moira._yoga_inputs import longitudes, number
from moira.yoga_extension_policy import YogaExtensionPolicy
from .common import _StrictModel
from ._vedic_inputs import ClassicalPlanet

ProfileId = Literal[
    "jp_sastri_7_14_v1",
    "raman_300_252_all_debilitated_v1",
    "bphs_santhanam_41_2_15_v1",
    "bphs_santhanam_39_selected_v1",
]
Sign = Annotated[int, Field(strict=True, ge=0, le=11)]
House = Annotated[int, Field(strict=True, ge=1, le=12)]
Count = Annotated[int, Field(strict=True, ge=0)]
Angle = Annotated[float, Field(strict=True, ge=0, lt=360, allow_inf_nan=False)]


class YogaExtensionEvaluateRequest(_StrictModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "sidereal_longitudes": {
                        "Sun": 201,
                        "Moon": 171,
                        "Mars": 111,
                        "Mercury": 181,
                        "Jupiter": 328,
                        "Venus": 214,
                        "Saturn": 84,
                    },
                    "lagna_sidereal_lon": 271,
                    "profile_ids": ["raman_300_252_all_debilitated_v1"],
                    "include_absent": True,
                }
            ]
        },
    )
    sidereal_longitudes: dict[ClassicalPlanet, Angle]
    lagna_sidereal_lon: Angle
    profile_ids: Annotated[tuple[ProfileId, ...], Field(min_length=1, max_length=4)]
    include_absent: StrictBool = True

    @model_validator(mode="after")
    def _admit(self):
        longitudes(self.sidereal_longitudes, canonical=True)
        number(self.lagna_sidereal_lon, "lagna_sidereal_lon", canonical=True)
        YogaExtensionPolicy(self.profile_ids)
        return self


class YogaExtensionSourceResponse(_StrictModel):
    source_id: str
    work: str
    translator_or_author: str
    publisher: str
    witness_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    local_corpus_path: str
    printing: str


class YogaExtensionRuleResponse(_StrictModel):
    rule_id: str
    profile_id: ProfileId
    name: str
    family: Literal["navamsa", "dhana", "raja"]
    effect_kind: Literal[
        "debilitation_relief", "wealth_combination", "royal_combination"
    ]
    source: YogaExtensionSourceResponse
    passage: str
    printed_pages: tuple[int, ...]
    pdf_pages: tuple[int, ...]
    interpretation: str
    admission: Literal["admitted", "research_required"]
    limitation: str
    overlaps: tuple[str, ...]


class YogaExtensionProfileResponse(_StrictModel):
    profile_id: ProfileId
    rule_ids: tuple[str, ...]
    requires_navamsa: StrictBool


class YogaExtensionCatalogueResponse(_StrictModel):
    catalogue_version: Literal["ved012.1"]
    profiles: tuple[YogaExtensionProfileResponse, ...]
    rules: tuple[YogaExtensionRuleResponse, ...]
    house_frame: Literal["sidereal_whole_sign_lagna"]
    aspect_model: Literal["full_graha_drishti"]
    conjunction_model: Literal["same_sign_distinct_bodies"]
    navamsa_model: Literal["moira.varga.navamsa_exact_partition"]
    required_inputs: tuple[str, ...]
    longitude_range: str
    outcome_scope: str


class YogaExtensionPolicyResponse(_StrictModel):
    profile_ids: tuple[ProfileId, ...]
    catalogue_version: Literal["ved012.1"]
    house_frame: Literal["sidereal_whole_sign_lagna"]
    aspect_model: Literal["full_graha_drishti"]
    conjunction_model: Literal["same_sign_distinct_bodies"]
    navamsa_model: Literal["moira.varga.navamsa_exact_partition"]


class YogaExtensionPositionResponse(_StrictModel):
    planet: ClassicalPlanet
    sidereal_longitude: Angle
    d1_sign_index: Sign
    d1_house: House
    d9_sign_index: Sign | None


class YogaExtensionClauseResponse(_StrictModel):
    clause_id: str
    predicate: Literal[
        "in_signs", "in_houses", "conjunction", "aspect", "opposition", "navamsa_lord"
    ]
    state: Literal["satisfied", "not_satisfied"]
    planet: Literal[
        "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Lagna"
    ]
    role: str
    frame: Literal["D1", "D9"]
    sign_index: Sign
    house: House | None
    reference: Literal["D1_Lagna"] | None
    related_planet: ClassicalPlanet | None
    related_role: str | None
    related_frame: Literal["D1", "D9"] | None
    related_sign_index: Sign | None
    expected_signs: tuple[Sign, ...]
    expected_houses: tuple[House, ...]


class YogaExtensionBranchResponse(_StrictModel):
    branch_id: str
    aggregation: Literal["all"]
    state: Literal["satisfied", "not_satisfied"]
    clauses: tuple[YogaExtensionClauseResponse, ...]


class YogaExtensionQualificationResponse(_StrictModel):
    source_id: str
    passage: str
    context: str
    assessment: Literal["not_evaluated"]


class YogaExtensionResultResponse(_StrictModel):
    rule: YogaExtensionRuleResponse
    aggregation: Literal["any"]
    formation_state: Literal["formed", "not_formed", "not_applicable"]
    branches: tuple[YogaExtensionBranchResponse, ...]
    cancellation_assessment: Literal["not_specified_by_selected_passage"]
    qualifications: tuple[YogaExtensionQualificationResponse, ...]


class YogaExtensionChartResponse(_StrictModel):
    policy: YogaExtensionPolicyResponse
    lagna_sidereal_longitude: Angle
    lagna_sign_index: Sign
    positions: tuple[YogaExtensionPositionResponse, ...]
    results: tuple[YogaExtensionResultResponse, ...]
    evaluated_count: Count
    returned_count: Count
    formed_count: Count
    not_formed_count: Count
    not_applicable_count: Count


__all__ = [
    "YogaExtensionEvaluateRequest",
    "YogaExtensionSourceResponse",
    "YogaExtensionRuleResponse",
    "YogaExtensionProfileResponse",
    "YogaExtensionCatalogueResponse",
    "YogaExtensionPolicyResponse",
    "YogaExtensionPositionResponse",
    "YogaExtensionClauseResponse",
    "YogaExtensionBranchResponse",
    "YogaExtensionQualificationResponse",
    "YogaExtensionResultResponse",
    "YogaExtensionChartResponse",
]
