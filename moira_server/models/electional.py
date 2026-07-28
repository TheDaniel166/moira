"""Transport models for P13-01 bounded electional-window routes."""

from __future__ import annotations

from math import floor, isfinite
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from moira._strenum import StrEnum
from moira.constants import HOUSE_SYSTEM_NAMES, HouseSystem
from moira.sidereal import Ayanamsa


ELECTIONAL_MAX_SPAN_DAYS = 31.0
ELECTIONAL_MIN_STEP_DAYS = 1.0 / 96.0
ELECTIONAL_MAX_STEP_DAYS = 1.0
ELECTIONAL_MAX_SCAN_POINTS = 1000
ELECTIONAL_MAX_WINDOWS = 64
ELECTIONAL_MAX_BOUNDARY_REFINE_STEPS = 8
ELECTIONAL_MAX_BODIES = 12
ELECTIONAL_DEFAULT_STEP_DAYS = 1.0 / 24.0
ELECTIONAL_SCORE_MIN = 0.0
ELECTIONAL_SCORE_MAX = 1.0

ELECTIONAL_SUBJECTS = (
    "Sun",
    "Moon",
    "Mercury",
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Pluto",
)
ELECTIONAL_SUBJECT_SET = frozenset(ELECTIONAL_SUBJECTS)
ELECTIONAL_HOUSE_SYSTEMS = tuple(HOUSE_SYSTEM_NAMES.keys())
ELECTIONAL_AYANAMSA_SYSTEMS = tuple(Ayanamsa.ALL)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ElectionalPredicateProfileId(StrEnum):
    BODY_LONGITUDE_RANGE = "body_longitude_range_v1"
    BODY_HOUSE_MEMBERSHIP = "body_house_membership_v1"
    BODY_ANGULAR_SEPARATION_RANGE = "body_angular_separation_range_v1"


class ElectionalScorerProfileId(StrEnum):
    BODY_LONGITUDE_TARGET_CLOSENESS = "body_longitude_target_closeness_v1"
    BODY_ANGULAR_SEPARATION_TARGET_CLOSENESS = (
        "body_angular_separation_target_closeness_v1"
    )


class ElectionalZodiacFrame(StrEnum):
    TROPICAL = "tropical"
    SIDEREAL = "sidereal"


class ElectionalAyanamsaMode(StrEnum):
    TRUE = "true"
    MEAN = "mean"


def finite_float(value: Any, field_name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a finite number")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a finite number") from exc
    if not isfinite(parsed):
        raise ValueError(f"{field_name} must be finite")
    return parsed


def strict_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer")
    return value


def strict_bool(value: Any, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a boolean")
    return value


def clean_subject(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a subject name string")
    subject = value.strip()
    if not subject:
        raise ValueError(f"{field_name} must be non-empty")
    if subject not in ELECTIONAL_SUBJECT_SET:
        raise ValueError(f"{field_name} must be one of {list(ELECTIONAL_SUBJECTS)!r}")
    return subject


def clean_bodies(value: Any) -> list[str] | None:
    if value is None:
        return None
    if not isinstance(value, list):
        raise ValueError("bodies must be a list")
    if len(value) > ELECTIONAL_MAX_BODIES:
        raise ValueError(f"bodies may contain at most {ELECTIONAL_MAX_BODIES} entries")
    cleaned: list[str] = []
    seen: set[str] = set()
    for index, raw in enumerate(value):
        subject = clean_subject(raw, f"bodies[{index}]")
        if subject in seen:
            raise ValueError(f"bodies contains duplicate subject {subject!r}")
        cleaned.append(subject)
        seen.add(subject)
    return cleaned


def scan_point_count(jd_start: float, jd_end: float, step_days: float) -> int:
    return int(floor((jd_end - jd_start) / step_days)) + 1


class ElectionalSearchPolicyRequest(_StrictModel):
    step_days: float = ELECTIONAL_DEFAULT_STEP_DAYS
    merge_gap_days: float | None = None
    house_system: str = HouseSystem.PLACIDUS
    bodies: list[str] | None = None
    zodiac_frame: ElectionalZodiacFrame = ElectionalZodiacFrame.TROPICAL
    ayanamsa_system: str = Ayanamsa.LAHIRI
    ayanamsa_mode: ElectionalAyanamsaMode = ElectionalAyanamsaMode.TRUE
    boundary_refine_steps: int = Field(default=0, ge=0, le=ELECTIONAL_MAX_BOUNDARY_REFINE_STEPS)
    max_windows: int = Field(default=ELECTIONAL_MAX_WINDOWS, ge=1, le=ELECTIONAL_MAX_WINDOWS)

    @field_validator("step_days", mode="before")
    @classmethod
    def _valid_step_days(cls, value: Any) -> float:
        parsed = finite_float(value, "step_days")
        if parsed < ELECTIONAL_MIN_STEP_DAYS:
            raise ValueError(
                f"step_days must be at least {ELECTIONAL_MIN_STEP_DAYS:g}"
            )
        if parsed > ELECTIONAL_MAX_STEP_DAYS:
            raise ValueError(f"step_days may not exceed {ELECTIONAL_MAX_STEP_DAYS:g}")
        return parsed

    @field_validator("merge_gap_days", mode="before")
    @classmethod
    def _valid_merge_gap_days(cls, value: Any) -> float | None:
        if value is None:
            return None
        parsed = finite_float(value, "merge_gap_days")
        if parsed < 0:
            raise ValueError("merge_gap_days must be non-negative")
        return parsed

    @field_validator("house_system", mode="before")
    @classmethod
    def _valid_house_system(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("house_system must be a string")
        code = value.strip()
        if code not in ELECTIONAL_HOUSE_SYSTEMS:
            raise ValueError(f"house_system must be one of {list(ELECTIONAL_HOUSE_SYSTEMS)!r}")
        return code

    @field_validator("bodies", mode="before")
    @classmethod
    def _valid_bodies(cls, value: Any) -> list[str] | None:
        return clean_bodies(value)

    @field_validator("ayanamsa_system", mode="before")
    @classmethod
    def _valid_ayanamsa_system(cls, value: Any) -> str:
        if not isinstance(value, str):
            raise ValueError("ayanamsa_system must be a string")
        system = value.strip()
        if not system:
            raise ValueError("ayanamsa_system must be non-empty")
        if system not in ELECTIONAL_AYANAMSA_SYSTEMS:
            raise ValueError(f"ayanamsa_system must be one of {list(ELECTIONAL_AYANAMSA_SYSTEMS)!r}")
        return system

    @field_validator("boundary_refine_steps", "max_windows", mode="before")
    @classmethod
    def _valid_policy_ints(cls, value: Any, info) -> int:
        return strict_int(value, info.field_name)


class ElectionalWindowsRequest(_StrictModel):
    jd_start: float
    jd_end: float
    latitude: float
    longitude: float
    predicate_profile: ElectionalPredicateProfileId
    predicate_parameters: dict[str, Any]
    policy: ElectionalSearchPolicyRequest = Field(default_factory=ElectionalSearchPolicyRequest)
    include_qualifying_jds: bool = True
    include_boundary_brackets: bool = True

    @field_validator("jd_start", "jd_end", "latitude", "longitude", mode="before")
    @classmethod
    def _valid_finite_fields(cls, value: Any, info) -> float:
        return finite_float(value, info.field_name)

    @field_validator("predicate_parameters", mode="before")
    @classmethod
    def _valid_predicate_parameters(cls, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("predicate_parameters must be an object")
        return dict(value)

    @field_validator("include_qualifying_jds", "include_boundary_brackets", mode="before")
    @classmethod
    def _valid_bools(cls, value: Any, info) -> bool:
        return strict_bool(value, info.field_name)

    @model_validator(mode="after")
    def _valid_search_bounds(self) -> "ElectionalWindowsRequest":
        if self.jd_end <= self.jd_start:
            raise ValueError("jd_end must be greater than jd_start")
        span = self.jd_end - self.jd_start
        if span > ELECTIONAL_MAX_SPAN_DAYS:
            raise ValueError(f"search span may not exceed {ELECTIONAL_MAX_SPAN_DAYS:g} days")
        if self.latitude < -90.0 or self.latitude > 90.0:
            raise ValueError("latitude must be in [-90, 90]")
        if self.longitude < -180.0 or self.longitude > 180.0:
            raise ValueError("longitude must be in [-180, 180]")
        count = scan_point_count(self.jd_start, self.jd_end, self.policy.step_days)
        if count > ELECTIONAL_MAX_SCAN_POINTS:
            raise ValueError(
                f"scan point count {count} exceeds maximum {ELECTIONAL_MAX_SCAN_POINTS}"
            )
        if self.policy.boundary_refine_steps > 0 and not self.include_boundary_brackets:
            raise ValueError(
                "boundary_refine_steps requires include_boundary_brackets=true"
            )
        return self


class ElectionalMomentsRequest(_StrictModel):
    jd_start: float
    jd_end: float
    latitude: float
    longitude: float
    predicate_profile: ElectionalPredicateProfileId
    predicate_parameters: dict[str, Any]
    policy: ElectionalSearchPolicyRequest = Field(default_factory=ElectionalSearchPolicyRequest)
    include_moments: bool = True

    @field_validator("jd_start", "jd_end", "latitude", "longitude", mode="before")
    @classmethod
    def _valid_finite_fields(cls, value: Any, info) -> float:
        return finite_float(value, info.field_name)

    @field_validator("predicate_parameters", mode="before")
    @classmethod
    def _valid_predicate_parameters(cls, value: Any) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("predicate_parameters must be an object")
        return dict(value)

    @field_validator("include_moments", mode="before")
    @classmethod
    def _valid_include_moments(cls, value: Any) -> bool:
        return strict_bool(value, "include_moments")

    @model_validator(mode="after")
    def _valid_search_bounds(self) -> "ElectionalMomentsRequest":
        if self.jd_end <= self.jd_start:
            raise ValueError("jd_end must be greater than jd_start")
        span = self.jd_end - self.jd_start
        if span > ELECTIONAL_MAX_SPAN_DAYS:
            raise ValueError(f"search span may not exceed {ELECTIONAL_MAX_SPAN_DAYS:g} days")
        if self.latitude < -90.0 or self.latitude > 90.0:
            raise ValueError("latitude must be in [-90, 90]")
        if self.longitude < -180.0 or self.longitude > 180.0:
            raise ValueError("longitude must be in [-180, 180]")
        count = scan_point_count(self.jd_start, self.jd_end, self.policy.step_days)
        if count > ELECTIONAL_MAX_SCAN_POINTS:
            raise ValueError(
                f"scan point count {count} exceeds maximum {ELECTIONAL_MAX_SCAN_POINTS}"
            )
        if self.policy.boundary_refine_steps != 0:
            raise ValueError("boundary_refine_steps must be 0 for electional moments")
        return self


class ElectionalScoredRequest(_StrictModel):
    jd_start: float
    jd_end: float
    latitude: float
    longitude: float
    predicate_profile: ElectionalPredicateProfileId
    predicate_parameters: dict[str, Any]
    scorer_profile: ElectionalScorerProfileId
    scorer_parameters: dict[str, Any]
    policy: ElectionalSearchPolicyRequest = Field(default_factory=ElectionalSearchPolicyRequest)
    include_qualifying_jds: bool = True
    include_boundary_brackets: bool = True
    include_score_rank: bool = True

    @field_validator("jd_start", "jd_end", "latitude", "longitude", mode="before")
    @classmethod
    def _valid_finite_fields(cls, value: Any, info) -> float:
        return finite_float(value, info.field_name)

    @field_validator("predicate_parameters", "scorer_parameters", mode="before")
    @classmethod
    def _valid_parameter_objects(cls, value: Any, info) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError(f"{info.field_name} must be an object")
        return dict(value)

    @field_validator(
        "include_qualifying_jds",
        "include_boundary_brackets",
        "include_score_rank",
        mode="before",
    )
    @classmethod
    def _valid_bools(cls, value: Any, info) -> bool:
        return strict_bool(value, info.field_name)

    @model_validator(mode="after")
    def _valid_search_bounds(self) -> "ElectionalScoredRequest":
        if self.jd_end <= self.jd_start:
            raise ValueError("jd_end must be greater than jd_start")
        span = self.jd_end - self.jd_start
        if span > ELECTIONAL_MAX_SPAN_DAYS:
            raise ValueError(f"search span may not exceed {ELECTIONAL_MAX_SPAN_DAYS:g} days")
        if self.latitude < -90.0 or self.latitude > 90.0:
            raise ValueError("latitude must be in [-90, 90]")
        if self.longitude < -180.0 or self.longitude > 180.0:
            raise ValueError("longitude must be in [-180, 180]")
        count = scan_point_count(self.jd_start, self.jd_end, self.policy.step_days)
        if count > ELECTIONAL_MAX_SCAN_POINTS:
            raise ValueError(
                f"scan point count {count} exceeds maximum {ELECTIONAL_MAX_SCAN_POINTS}"
            )
        if self.policy.boundary_refine_steps > 0 and not self.include_boundary_brackets:
            raise ValueError(
                "boundary_refine_steps requires include_boundary_brackets=true"
            )
        return self


class ElectionalBoundsResponse(_StrictModel):
    max_span_days: float = ELECTIONAL_MAX_SPAN_DAYS
    min_step_days: float = ELECTIONAL_MIN_STEP_DAYS
    max_step_days: float = ELECTIONAL_MAX_STEP_DAYS
    max_scan_points: int = ELECTIONAL_MAX_SCAN_POINTS
    max_windows: int = ELECTIONAL_MAX_WINDOWS
    max_boundary_refine_steps: int = ELECTIONAL_MAX_BOUNDARY_REFINE_STEPS
    max_bodies: int = ELECTIONAL_MAX_BODIES
    admitted_subjects: list[str] = Field(default_factory=lambda: list(ELECTIONAL_SUBJECTS))


class ElectionalPredicateProfileResponse(_StrictModel):
    profile_id: str
    version: str
    description: str
    required_parameters: list[str]
    required_chart_fields: list[str]
    supported_frames: list[str]
    doctrine_status: str
    non_goals: list[str]


class ElectionalPredicateCatalogResponse(_StrictModel):
    profiles: list[ElectionalPredicateProfileResponse]
    bounds: ElectionalBoundsResponse
    provenance: dict[str, Any]


class ElectionalScorerProfileResponse(_StrictModel):
    profile_id: str
    version: str
    description: str
    required_parameters: list[str]
    required_chart_fields: list[str]
    supported_frames: list[str]
    score_scale: list[float]
    score_direction: str
    doctrine_status: str
    non_goals: list[str]


class ElectionalScorerCatalogResponse(_StrictModel):
    profiles: list[ElectionalScorerProfileResponse]
    bounds: ElectionalBoundsResponse
    provenance: dict[str, Any]


class ElectionalPredicateResponse(_StrictModel):
    profile_id: str
    profile_version: str
    parameters: dict[str, Any]
    owner: str = "server_defined"
    doctrine_status: str = "scan_predicate_not_electional_judgement"


class ElectionalScorerResponse(_StrictModel):
    profile_id: str
    profile_version: str
    parameters: dict[str, Any]
    owner: str = "server_defined"
    score_scale: list[float] = Field(
        default_factory=lambda: [ELECTIONAL_SCORE_MIN, ELECTIONAL_SCORE_MAX]
    )
    score_direction: str = "higher_is_closer_numeric_fit"
    doctrine_status: str = "numeric_fit_not_electional_judgement"


class ElectionalPolicyResponse(_StrictModel):
    requested_step_days: float
    effective_step_days: float
    requested_merge_gap_days: float | None
    effective_merge_gap_days: float
    requested_house_system: str
    effective_house_system: str
    requested_bodies: list[str] | None
    effective_bodies: list[str] | None
    requested_zodiac_frame: str
    effective_zodiac_frame: str
    requested_ayanamsa_system: str
    effective_ayanamsa_system: str
    requested_ayanamsa_mode: str
    effective_ayanamsa_mode: str
    requested_boundary_refine_steps: int
    effective_boundary_refine_steps: int
    requested_max_windows: int
    effective_max_windows: int


class ElectionalScoredPolicyResponse(ElectionalPolicyResponse):
    max_windows_semantics: str = "chronological_early_exit"


class ElectionalMomentPolicyResponse(_StrictModel):
    requested_step_days: float
    effective_step_days: float
    requested_merge_gap_days: float | None
    effective_merge_gap_days: float
    merge_gap_days_applicable: bool = False
    requested_house_system: str
    effective_house_system: str
    requested_bodies: list[str] | None
    effective_bodies: list[str] | None
    requested_zodiac_frame: str
    effective_zodiac_frame: str
    requested_ayanamsa_system: str
    effective_ayanamsa_system: str
    requested_ayanamsa_mode: str
    effective_ayanamsa_mode: str
    requested_boundary_refine_steps: int
    effective_boundary_refine_steps: int
    boundary_refinement_applicable: bool = False
    requested_max_windows: int
    effective_max_windows: int | None
    max_windows_applicable: bool = False


class ElectionalScanResponse(_StrictModel):
    jd_start: float
    jd_end: float
    span_days: float
    scan_point_count: int
    discrete_scan: bool = True
    continuous_truth_claimed: bool = False
    exact_boundary_claimed: bool = False


class ElectionalScoredScanResponse(ElectionalScanResponse):
    exact_peak_claimed: bool = False


class ElectionalWindowResponse(_StrictModel):
    jd_start: float
    jd_end: float
    duration_hours: float
    qualifying_count: int
    qualifying_jds: list[float] | None
    entry_bracket: list[float] | None
    exit_bracket: list[float] | None
    window_kind: str = "merged_scan_witness"


class ElectionalScoredWindowResponse(ElectionalWindowResponse):
    score: float
    peak_jd: float
    score_rank: int | None
    peak_kind: str = "highest_scored_qualifying_scan_point"


class ElectionalScoreSummaryResponse(_StrictModel):
    count: int
    highest_score: float | None
    lowest_score: float | None
    score_rank_basis: str = "score_desc_peak_jd_asc_window_start_asc"
    rank_scope: str = "returned_windows_only"
    global_best_claimed: bool = False


class ElectionalMomentsListResponse(_StrictModel):
    count: int
    jds: list[float] | None
    first_jd: float | None
    last_jd: float | None
    moment_kind: str = "qualifying_scan_point"
    sorted_temporally: bool = True


class ElectionalValidationResponse(_StrictModel):
    included: bool = True
    passed: bool
    failures: list[str]


class ElectionalProvenanceResponse(_StrictModel):
    source_module: str = "moira.electional"
    engine_entrypoint: str = "find_electional_windows"
    predicate_owner: str = "server_defined"
    predicate_profile: str
    predicate_profile_version: str
    chart_construction_owner: str = "moira.chart.create_chart"
    reader_owner: str
    scan_semantics: str = "discrete_sampled_chart_states"
    window_semantics: str = "merged_qualifying_scan_points"
    boundary_semantics: str = "optional_true_false_brackets_not_exact_roots"
    western_electional_doctrine: str = "not_admitted"
    advice_language: str = "not_provided"
    scoring: str = "not_admitted"
    moments_route: str = "admitted_separately_in_p13_02"
    stage_sequence: list[str]


class ElectionalMomentsProvenanceResponse(_StrictModel):
    source_module: str = "moira.electional"
    engine_entrypoint: str = "find_electional_moments"
    predicate_owner: str = "server_defined"
    predicate_profile: str
    predicate_profile_version: str
    chart_construction_owner: str = "moira.chart.create_chart"
    reader_owner: str
    scan_semantics: str = "discrete_sampled_chart_states"
    moment_semantics: str = "raw_qualifying_scan_points"
    window_merge: str = "not_applied"
    boundary_semantics: str = "not_applicable_to_raw_moments"
    western_electional_doctrine: str = "not_admitted"
    advice_language: str = "not_provided"
    scoring: str = "not_admitted"
    stage_sequence: list[str]


class ElectionalScoredProvenanceResponse(_StrictModel):
    source_module: str = "moira.electional"
    engine_entrypoint: str = "find_scored_windows"
    predicate_owner: str = "server_defined"
    predicate_profile: str
    predicate_profile_version: str
    scorer_owner: str = "server_defined"
    scorer_profile: str
    scorer_profile_version: str
    chart_construction_owner: str = "moira.chart.create_chart"
    reader_owner: str
    scan_semantics: str = "discrete_sampled_chart_states"
    window_semantics: str = "merged_qualifying_scan_points"
    boundary_semantics: str = "optional_true_false_brackets_not_exact_roots"
    score_semantics: str = "numeric_fit_to_declared_scorer_profile"
    score_scale: list[float] = Field(
        default_factory=lambda: [ELECTIONAL_SCORE_MIN, ELECTIONAL_SCORE_MAX]
    )
    score_direction: str = "higher_is_closer_numeric_fit"
    score_rank_semantics: str = "returned_windows_only"
    peak_semantics: str = "highest_scored_qualifying_scan_point"
    exact_peak_claimed: bool = False
    score_peak_refinement: str = "not_applied"
    max_windows_semantics: str = "chronological_early_exit"
    western_electional_doctrine: str = "not_admitted"
    advice_language: str = "not_provided"
    recommendation_language: str = "not_provided"
    scoring_doctrine: str = "transport_numeric_fit_not_western_judgement"
    stage_sequence: list[str]


class ElectionalWindowsResponse(_StrictModel):
    predicate: ElectionalPredicateResponse
    policy: ElectionalPolicyResponse
    scan: ElectionalScanResponse
    windows: list[ElectionalWindowResponse]
    bounds: ElectionalBoundsResponse
    validation: ElectionalValidationResponse
    provenance: ElectionalProvenanceResponse


class ElectionalMomentsResponse(_StrictModel):
    predicate: ElectionalPredicateResponse
    policy: ElectionalMomentPolicyResponse
    scan: ElectionalScanResponse
    moments: ElectionalMomentsListResponse
    bounds: ElectionalBoundsResponse
    validation: ElectionalValidationResponse
    provenance: ElectionalMomentsProvenanceResponse


class ElectionalScoredResponse(_StrictModel):
    predicate: ElectionalPredicateResponse
    scorer: ElectionalScorerResponse
    policy: ElectionalScoredPolicyResponse
    scan: ElectionalScoredScanResponse
    scored_windows: list[ElectionalScoredWindowResponse]
    score_summary: ElectionalScoreSummaryResponse
    bounds: ElectionalBoundsResponse
    validation: ElectionalValidationResponse
    provenance: ElectionalScoredProvenanceResponse
