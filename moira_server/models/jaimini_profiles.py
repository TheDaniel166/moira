"""Strict transport for VED-013 discovery, source arithmetic and bounded assessments."""

from typing import Annotated, Literal

from pydantic import ConfigDict, Field, StrictBool, model_validator

from moira._jaimini_profile_inputs import (
    CLASSICAL,
    NINE,
    ArgalaReference,
    CharaProjection,
    JaiminiChart,
    admit_chart,
    admit_references,
)
from moira.jaimini_profile_policy import (
    JaiminiSource,
    JaiminiRule,
    JaiminiConflict,
    JaiminiProfile,
)
from .common import _StrictModel
from ._vedic_inputs import ClassicalPlanet, FiniteNumber, SignIndex

Body = Literal[
    "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"
]
CharaId = Literal[
    "rangacharya_2007_method1_classical7_v1",
    "rangacharya_2007_method2_male_classical7_v1",
    "rangacharya_2007_female_prose_classical7_v1",
]
ArgalaId = Literal[
    "bphs_santhanam_31_literal_assessment_v1",
    "pvr_2000_argala_count_first_v1",
    "rath_argala_article_assessment_v1",
]
Angle = Annotated[float, Field(strict=True, ge=0, lt=360, allow_inf_nan=False)]
Degree = Annotated[float, Field(strict=True, ge=0, lt=30, allow_inf_nan=False)]
House = Annotated[int, Field(strict=True, ge=1, le=12)]
Count = Annotated[int, Field(strict=True, ge=0, le=9)]
Years = Annotated[int, Field(strict=True, ge=0, le=12)]
TotalYears = Annotated[int, Field(strict=True, ge=0, le=144)]
Direction = Literal[-1, 1]
Character = Literal["none", "benefic", "malefic", "mixed", "indeterminate"]
Reason = Literal[
    "strength_comparator_not_admitted",
    "degrees_required",
    "multioccupant_quarter_composition_unestablished",
    "factor_priority_not_admitted",
]


class CharaSignChart(_StrictModel):
    basis: Literal["signs"]
    positions: Annotated[
        dict[ClassicalPlanet, SignIndex], Field(min_length=7, max_length=7)
    ]
    lagna: SignIndex


class CharaLongitudeChart(_StrictModel):
    basis: Literal["sidereal_longitudes"]
    positions: Annotated[
        dict[ClassicalPlanet, Angle], Field(min_length=7, max_length=7)
    ]
    lagna: Angle


class ArgalaSignChart(_StrictModel):
    basis: Literal["signs"]
    positions: Annotated[dict[Body, SignIndex], Field(min_length=9, max_length=9)]
    lagna: SignIndex


class ArgalaLongitudeChart(_StrictModel):
    basis: Literal["sidereal_longitudes"]
    positions: Annotated[dict[Body, Angle], Field(min_length=9, max_length=9)]
    lagna: Angle


class ProjectionRequest(_StrictModel):
    epoch_jd: FiniteNumber
    projection_id: Literal["moira_fixed_365_25_day_projection_v1"]


class LagnaReference(_StrictModel):
    kind: Literal["lagna"]
    value: None = None


class HouseReference(_StrictModel):
    kind: Literal["house"]
    value: House


class PlanetReference(_StrictModel):
    kind: Literal["planet"]
    value: Body


Reference = Annotated[
    LagnaReference | HouseReference | PlanetReference, Field(discriminator="kind")
]
CharaChart = Annotated[
    CharaSignChart | CharaLongitudeChart, Field(discriminator="basis")
]
ArgalaChart = Annotated[
    ArgalaSignChart | ArgalaLongitudeChart, Field(discriminator="basis")
]


class CharaProfileRequest(_StrictModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "profile_id": "rangacharya_2007_method2_male_classical7_v1",
                    "chart": {
                        "basis": "signs",
                        "lagna": 7,
                        "positions": {
                            "Sun": 1,
                            "Moon": 9,
                            "Mars": 2,
                            "Mercury": 1,
                            "Jupiter": 11,
                            "Venus": 2,
                            "Saturn": 7,
                        },
                    },
                }
            ]
        }
    )
    chart: CharaChart
    profile_id: CharaId
    projection: ProjectionRequest | None = None

    @model_validator(mode="after")
    def _admit(self):
        admit_chart(JaiminiChart(**self.chart.model_dump()), CLASSICAL)
        if self.projection is not None:
            CharaProjection(**self.projection.model_dump())
        return self


class ArgalaAssessmentRequest(_StrictModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "profile_id": "pvr_2000_argala_count_first_v1",
                    "chart": {
                        "basis": "signs",
                        "lagna": 7,
                        "positions": {
                            "Sun": 1,
                            "Moon": 0,
                            "Mars": 7,
                            "Mercury": 8,
                            "Jupiter": 5,
                            "Venus": 9,
                            "Saturn": 7,
                            "Rahu": 4,
                            "Ketu": 10,
                        },
                    },
                    "references": [
                        {"kind": "lagna"},
                        {"kind": "planet", "value": "Ketu"},
                    ],
                }
            ]
        }
    )
    chart: ArgalaChart
    profile_id: ArgalaId
    references: Annotated[tuple[Reference, ...], Field(min_length=1, max_length=22)]

    @model_validator(mode="after")
    def _admit(self):
        admit_chart(JaiminiChart(**self.chart.model_dump()), NINE)
        admit_references(
            tuple(ArgalaReference(**r.model_dump()) for r in self.references)
        )
        return self


class JaiminiCatalogueResponse(_StrictModel):
    catalogue_version: Literal["ved013.1"]
    sources: tuple[JaiminiSource, ...]
    rules: tuple[JaiminiRule, ...]
    conflicts: tuple[JaiminiConflict, ...]
    profiles: tuple[JaiminiProfile, ...]


class CharaRowResponse(_StrictModel):
    ordinal: SignIndex
    sign: SignIndex
    lord: ClassicalPlanet
    lord_sign: SignIndex
    count_direction: Direction
    inclusive_count: House
    base_years: Years
    exception: Literal["none", "own_sign_twelve", "opposite_sign_ten"]
    dignity_adjustment: Literal[-1, 0, 1]
    years: Years
    start_year: TotalYears
    end_year: TotalYears
    rule_id: str


class CharaIntervalResponse(_StrictModel):
    row_ordinal: SignIndex
    start_jd: FiniteNumber
    end_jd: FiniteNumber


class CharaScheduleResponse(_StrictModel):
    status: Literal["not_requested", "projected"]
    projection: ProjectionRequest | None
    intervals: Annotated[tuple[CharaIntervalResponse, ...], Field(max_length=12)]
    not_scheduled_zero_duration: Annotated[tuple[SignIndex, ...], Field(max_length=12)]


class CharaProfileResponse(_StrictModel):
    chart: CharaChart
    profile: JaiminiProfile
    seed_sign: SignIndex
    sequence_direction: Direction
    rows: Annotated[tuple[CharaRowResponse, ...], Field(min_length=12, max_length=12)]
    total_years: TotalYears
    schedule: CharaScheduleResponse
    catalogue_version: Literal["ved013.1"]
    cycle_count: Literal[1]
    subperiod_scope: Literal["not_admitted"]
    participant_pool: tuple[ClassicalPlanet, ...]


class CharacterResponse(_StrictModel):
    body: Body
    state: Literal["benefic", "malefic", "indeterminate"]
    reason: Literal[
        "natural_benefic",
        "natural_malefic",
        "bright_half",
        "dark_half",
        "malefic_association",
        "no_malefic_association",
        "requires_longitude",
        "moon_association_unresolved",
    ]


class CountGradeResponse(_StrictModel):
    status: Literal["assessed", "not_assessed"]
    grade: Literal["none", "limited", "medium", "excellent"] | None
    rule_id: Literal["bphs.31.formation"] | None


class QuarterResponse(_StrictModel):
    causer: Body
    blocker: Body
    causer_degree: Degree
    blocker_degree: Degree
    causer_quarter: Annotated[int, Field(strict=True, ge=1, le=4)]
    blocker_quarter: Annotated[int, Field(strict=True, ge=1, le=4)]
    qualifies: StrictBool


class EligibleBlockersResponse(_StrictModel):
    causer: Body
    blockers: tuple[Body, ...]


class StrengthFactorsResponse(_StrictModel):
    side: Literal["causer", "blocker"]
    sign: SignIndex
    own_sign_bodies: tuple[ClassicalPlanet, ...]
    jupiter_rasi_aspect: StrictBool


class PairAssessmentResponse(_StrictModel):
    causer_house: House
    blocker_house: House
    causer_sign: SignIndex
    blocker_sign: SignIndex
    causers: tuple[Body, ...]
    blockers: tuple[Body, ...]
    causer_count: Count
    blocker_count: Count
    formation_state: Literal["absent", "present"]
    count_grade: CountGradeResponse
    causer_character: Character
    blocker_character: Character
    effect_state: Literal["absent", "unobstructed", "obstructed", "indeterminate"]
    reason_codes: tuple[Reason, ...]
    strength_comparison: Literal["not_required", "indeterminate"]
    quarter_status: Literal["not_assessed", "unavailable", "no_pairs", "evaluated"]
    quarter_pairs: Annotated[tuple[QuarterResponse, ...], Field(max_length=81)]
    eligible_blockers: Annotated[
        tuple[EligibleBlockersResponse, ...], Field(max_length=9)
    ]
    strength_factors: Annotated[
        tuple[StrengthFactorsResponse, ...], Field(max_length=2)
    ]


class SpecialThirdResponse(_StrictModel):
    state: Literal["present", "absent", "indeterminate", "not_assessed"]
    occupants: tuple[Body, ...]
    known_malefics: tuple[Body, ...]
    unknown_bodies: tuple[Body, ...]
    minimum_malefics: Count
    maximum_malefics: Count
    reason: Literal[
        "three_malefics",
        "fewer_than_three_possible",
        "character_unresolved",
        "special_third_threshold_not_admitted",
    ]
    source_effect: Literal["favourable_special_intervention"] | None


class ReferenceAssessmentResponse(_StrictModel):
    reference: Reference
    reference_sign: SignIndex
    direction: Direction
    direction_reason: Literal[
        "ordinary_forward", "node_reference", "ketu_occupied_reference"
    ]
    pairs: Annotated[
        tuple[PairAssessmentResponse, ...], Field(min_length=4, max_length=6)
    ]
    special_third: SpecialThirdResponse


class ArgalaAssessmentResponse(_StrictModel):
    chart: ArgalaChart
    profile: JaiminiProfile
    characters: Annotated[
        tuple[CharacterResponse, ...], Field(min_length=9, max_length=9)
    ]
    references: Annotated[
        tuple[ReferenceAssessmentResponse, ...], Field(min_length=1, max_length=22)
    ]
    catalogue_version: Literal["ved013.1"]
    character_component: Literal["bphs_santhanam_3_11_root_same_sign_v1"]
    participant_pool: tuple[Body, ...]
