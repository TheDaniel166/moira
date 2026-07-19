"""Transport models for relationship and inter-chart endpoints."""

from __future__ import annotations

from datetime import datetime
import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .chart import ChartResponse, HousesResponse


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RelationshipPartyRequest(_StrictModel):
    dt: datetime
    latitude: float
    longitude: float
    bodies: list[str] | None = None
    include_nodes: bool = True
    observer_lat: float | None = None
    observer_lon: float | None = None
    observer_elev_m: float = 0.0
    house_system: str | None = None


class SynastryPairRequest(_StrictModel):
    first: RelationshipPartyRequest
    second: RelationshipPartyRequest
    first_label: str = "A"
    second_label: str = "B"
    tier: int | None = None
    orb_factor: float | None = None
    include_nodes: bool | None = None


class SynastryDirectionalOverlayRequest(SynastryPairRequest):
    direction: str = "first_in_second"


class AspectClassificationResponse(_StrictModel):
    domain: str
    tier: str
    family: str


class AspectDataResponse(_StrictModel):
    body1: str
    body2: str
    aspect: str
    symbol: str
    angle: float
    separation: float
    orb: float
    allowed_orb: float
    applying: bool | None = None
    stationary: bool
    classification: AspectClassificationResponse | None = None
    direction: str | None = None
    sign_degree1: float | None = None
    sign_degree2: float | None = None


class AspectsFromLongitudesRequest(_StrictModel):
    longitudes: dict[str, float] = Field(min_length=2, max_length=64)
    tier: Literal[0, 1, 2] = 1
    orb_factor: float = Field(default=1.0, gt=0.0, le=10.0)
    include_nodes: bool = True

    @field_validator("longitudes", mode="before")
    @classmethod
    def _valid_longitudes(cls, value: Any) -> dict[str, float]:
        if not isinstance(value, dict):
            raise ValueError("longitudes must be an object mapping point names to degrees")
        normalized: dict[str, float] = {}
        for name, longitude in value.items():
            if not isinstance(name, str) or not name or name != name.strip():
                raise ValueError("longitude point names must be non-empty trimmed strings")
            if isinstance(longitude, bool):
                raise ValueError(f"longitude for {name!r} must be finite")
            try:
                parsed = float(longitude)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"longitude for {name!r} must be finite") from exc
            if not math.isfinite(parsed):
                raise ValueError(f"longitude for {name!r} must be finite")
            normalized[name] = parsed
        return normalized

    @field_validator("tier", mode="before")
    @classmethod
    def _strict_tier(cls, value: Any) -> Any:
        if isinstance(value, bool):
            raise ValueError("tier must be 0, 1, or 2")
        return value

    @field_validator("orb_factor", mode="before")
    @classmethod
    def _strict_orb_factor(cls, value: Any) -> Any:
        if isinstance(value, bool):
            raise ValueError("orb_factor must be a finite number")
        return value

    @field_validator("include_nodes", mode="before")
    @classmethod
    def _strict_include_nodes(cls, value: Any) -> bool:
        if not isinstance(value, bool):
            raise ValueError("include_nodes must be a boolean")
        return value


class LongitudeAspectComputationTruthResponse(_StrictModel):
    source_module: Literal["moira.aspects"] = "moira.aspects"
    engine_entrypoint: Literal["aspects_from_longitudes"] = "aspects_from_longitudes"
    facade_entrypoint: Literal["Moira.aspects_from_longitudes"] = "Moira.aspects_from_longitudes"
    position_semantics: Literal["caller_supplied_ecliptic_longitudes"] = (
        "caller_supplied_ecliptic_longitudes"
    )
    motion_semantics: Literal["not_computed_without_speeds"]
    ordering: Literal["orb_ascending_stable_over_point_name_order"] = (
        "orb_ascending_stable_over_point_name_order"
    )
    aspect_policy_authority: Literal["moira.constants.Aspect"] = "moira.constants.Aspect"
    normalized_longitudes: dict[str, float]
    tier: Literal[0, 1, 2]
    orb_factor: float
    include_nodes: bool
    excluded_node_names: list[str]
    point_count: int
    aspect_count: int


class AspectsFromLongitudesResponse(_StrictModel):
    events: list[AspectDataResponse]
    computation_truth: LongitudeAspectComputationTruthResponse


class DeclinationAspectResponse(_StrictModel):
    body1: str
    body2: str
    aspect: Literal["Parallel", "Contra-Parallel"]
    dec1: float
    dec2: float
    orb: float
    allowed_orb: float
    classification: AspectClassificationResponse


class DeclinationAspectsFromDeclinationsRequest(_StrictModel):
    declinations: dict[str, float] = Field(min_length=2, max_length=64)
    reference_frame: str = Field(min_length=1, max_length=128)
    timescale: str = Field(min_length=1, max_length=32)
    orb: float = Field(default=1.0, ge=0.0, le=10.0)

    @field_validator("declinations", mode="before")
    @classmethod
    def _valid_declinations(cls, value: Any) -> dict[str, float]:
        if not isinstance(value, dict):
            raise ValueError(
                "declinations must be an object mapping point names to degrees"
            )
        normalized: dict[str, float] = {}
        for name, declination in value.items():
            if not isinstance(name, str) or not name or name != name.strip():
                raise ValueError(
                    "declination point names must be non-empty trimmed strings"
                )
            if isinstance(declination, bool):
                raise ValueError(f"declination for {name!r} must be finite")
            try:
                parsed = float(declination)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"declination for {name!r} must be finite"
                ) from exc
            if not math.isfinite(parsed):
                raise ValueError(f"declination for {name!r} must be finite")
            if not -90.0 <= parsed <= 90.0:
                raise ValueError(
                    f"declination for {name!r} must lie in [-90, 90]"
                )
            normalized[name] = parsed
        return normalized

    @field_validator("orb", mode="before")
    @classmethod
    def _strict_orb(cls, value: Any) -> Any:
        if isinstance(value, bool):
            raise ValueError("orb must be a finite number")
        return value

    @field_validator("reference_frame", "timescale")
    @classmethod
    def _trimmed_provenance(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("frame and timescale provenance must be trimmed")
        return value


class DeclinationAspectComputationTruthResponse(_StrictModel):
    source_module: Literal["moira.aspects"] = "moira.aspects"
    governing_module: Literal["moira.declination_aspects"] = (
        "moira.declination_aspects"
    )
    engine_entrypoint: Literal["declination_aspects_from_declinations"] = (
        "declination_aspects_from_declinations"
    )
    facade_entrypoint: Literal[
        "Moira.declination_aspects_from_declinations"
    ] = "Moira.declination_aspects_from_declinations"
    coordinate_semantics: Literal["caller_supplied_equatorial_declinations"] = (
        "caller_supplied_equatorial_declinations"
    )
    hemisphere_policy: Literal[
        "parallel_same_nonzero_hemisphere_contra_opposite_nonzero_hemispheres"
    ] = "parallel_same_nonzero_hemisphere_contra_opposite_nonzero_hemispheres"
    equator_policy: Literal[
        "two_equatorial_points_parallel_one_equatorial_point_unclassified"
    ] = "two_equatorial_points_parallel_one_equatorial_point_unclassified"
    ordering: Literal["orb_ascending_stable_over_point_name_order"] = (
        "orb_ascending_stable_over_point_name_order"
    )
    normalized_declinations: dict[str, float]
    orb: float
    reference_frame: str
    timescale: str
    provenance: Literal["caller_supplied_declinations"] = (
        "caller_supplied_declinations"
    )
    point_count: int
    aspect_count: int


class DeclinationAspectsFromDeclinationsResponse(_StrictModel):
    events: list[DeclinationAspectResponse]
    computation_truth: DeclinationAspectComputationTruthResponse


class DeclinationAspectMotionWitnessRequest(_StrictModel):
    body1: str = Field(min_length=1, max_length=128)
    declination1_deg: float = Field(ge=-90.0, le=90.0)
    body2: str = Field(min_length=1, max_length=128)
    declination2_deg: float = Field(ge=-90.0, le=90.0)
    aspect: Literal["Parallel", "Contra-Parallel"]
    speed1_deg_per_day: float | None = None
    speed2_deg_per_day: float | None = None
    orb: float = Field(default=1.0, ge=0.0, le=10.0)
    exact_tolerance_deg: float = Field(default=1e-9, ge=0.0, le=1.0)
    rate_tolerance_deg_per_day: float = Field(default=1e-12, ge=0.0, le=1.0)
    reference_frame: str = Field(min_length=1, max_length=128)
    timescale: str = Field(min_length=1, max_length=32)

    @field_validator("body1", "body2", "reference_frame", "timescale")
    @classmethod
    def _trimmed_text(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("text provenance and body fields must be trimmed")
        return value

    @field_validator(
        "declination1_deg",
        "declination2_deg",
        "speed1_deg_per_day",
        "speed2_deg_per_day",
        "orb",
        "exact_tolerance_deg",
        "rate_tolerance_deg_per_day",
        mode="before",
    )
    @classmethod
    def _finite_values(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, bool):
            raise ValueError("declination motion values must be finite numbers")
        try:
            parsed = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "declination motion values must be finite numbers"
            ) from exc
        if not math.isfinite(parsed):
            raise ValueError("declination motion values must be finite numbers")
        return parsed

    @model_validator(mode="after")
    def _distinct_points(self) -> "DeclinationAspectMotionWitnessRequest":
        if self.body1 == self.body2:
            raise ValueError("body1 and body2 must identify distinct points")
        return self


class DeclinationAspectMotionWitnessResponse(_StrictModel):
    body1: str
    body2: str
    aspect: Literal["Parallel", "Contra-Parallel"]
    declination1_deg: float
    declination2_deg: float
    speed1_deg_per_day: float | None
    speed2_deg_per_day: float | None
    signed_error_deg: float
    relative_speed_deg_per_day: float | None
    orb_deg: float
    orb_rate_deg_per_day: float | None
    allowed_orb_deg: float
    within_orb: bool
    state: Literal["applying", "exact", "separating", "stationary", "indeterminate"]
    relative_motion_stalled: bool | None
    exact_tolerance_deg: float
    rate_tolerance_deg_per_day: float
    hemisphere_policy: Literal[
        "parallel_same_nonzero_hemisphere_contra_opposite_nonzero_hemispheres"
    ]
    equator_policy: Literal[
        "two_equatorial_points_parallel_one_equatorial_point_unclassified"
    ]
    classification: AspectClassificationResponse
    reference_frame: str
    timescale: str
    provenance: Literal["caller_supplied_declinations_and_optional_rates"]
    evaluation_scope: Literal["instantaneous_no_event_search"]


class DeclinationAspectMotionComputationTruthResponse(_StrictModel):
    governing_module: Literal["moira.declination_aspects"] = (
        "moira.declination_aspects"
    )
    engine_entrypoint: Literal["declination_aspect_motion_witness"] = (
        "declination_aspect_motion_witness"
    )
    facade_entrypoint: Literal["Moira.declination_aspect_motion_witness"] = (
        "Moira.declination_aspect_motion_witness"
    )
    parallel_error_formula: Literal["declination1_minus_declination2"] = (
        "declination1_minus_declination2"
    )
    contra_parallel_error_formula: Literal[
        "declination1_plus_declination2"
    ] = "declination1_plus_declination2"
    motion_classification: Literal["instantaneous_signed_error_rate"] = (
        "instantaneous_signed_error_rate"
    )
    stationary_policy: Literal["relative_declination_rate_within_tolerance"] = (
        "relative_declination_rate_within_tolerance"
    )
    provenance_semantics: Literal["caller_declared_frame_and_timescale"] = (
        "caller_declared_frame_and_timescale"
    )


class DeclinationAspectMotionAnalysisResponse(_StrictModel):
    witness: DeclinationAspectMotionWitnessResponse
    computation_truth: DeclinationAspectMotionComputationTruthResponse


AspectMotionNameValue = Literal[
    "Conjunction",
    "Semisextile",
    "Semisquare",
    "Sextile",
    "Square",
    "Trine",
    "Sesquiquadrate",
    "Quincunx",
    "Opposition",
    "Quintile",
    "Biquintile",
    "Tredecile",
    "Septile",
    "Biseptile",
    "Triseptile",
    "Novile",
    "Binovile",
    "Quadnovile",
    "Decile",
    "Undecile",
    "Quindecile",
    "Vigintile",
]

AspectMotionStationaryReasonValue = Literal[
    "body1_below_stationary_threshold",
    "body2_below_stationary_threshold",
    "relative_rate_within_tolerance",
]


class AspectMotionWitnessRequest(_StrictModel):
    body1: str = Field(min_length=1, max_length=128)
    longitude1_deg: float
    body2: str = Field(min_length=1, max_length=128)
    longitude2_deg: float
    aspect: AspectMotionNameValue
    speed1_deg_per_day: float | None = None
    speed2_deg_per_day: float | None = None
    orb_factor: float = Field(default=1.0, gt=0.0, le=10.0)
    exact_tolerance_deg: float = Field(default=1e-9, ge=0.0, le=1.0)
    rate_tolerance_deg_per_day: float = Field(default=1e-12, ge=0.0, le=1.0)
    reference_frame: str = Field(min_length=1, max_length=128)
    timescale: str = Field(min_length=1, max_length=32)

    @field_validator("body1", "body2", "reference_frame", "timescale")
    @classmethod
    def _trimmed_text(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("text provenance and body fields must be trimmed")
        return value

    @field_validator(
        "longitude1_deg",
        "longitude2_deg",
        "speed1_deg_per_day",
        "speed2_deg_per_day",
        "orb_factor",
        "exact_tolerance_deg",
        "rate_tolerance_deg_per_day",
        mode="before",
    )
    @classmethod
    def _finite_values(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, bool):
            raise ValueError("aspect motion values must be finite numbers")
        try:
            parsed = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("aspect motion values must be finite numbers") from exc
        if not math.isfinite(parsed):
            raise ValueError("aspect motion values must be finite numbers")
        return parsed

    @model_validator(mode="after")
    def _distinct_points(self) -> "AspectMotionWitnessRequest":
        if self.body1 == self.body2:
            raise ValueError("body1 and body2 must identify distinct points")
        return self


class AspectMotionWitnessResponse(_StrictModel):
    body1: str
    body2: str
    longitude1_deg: float
    longitude2_deg: float
    speed1_deg_per_day: float | None
    speed2_deg_per_day: float | None
    aspect: AspectMotionNameValue
    symbol: str
    angle_deg: float
    branch_selection: Literal[
        "undirected_conjunction",
        "positive",
        "negative",
        "ambiguous_at_zero_separation",
    ]
    target_directed_separation_deg: float | None
    directed_separation_deg: float
    directed_error_deg: float | None
    separation_deg: float
    orb_deg: float
    allowed_orb_deg: float
    within_orb: bool
    orb_policy: Literal["canonical_default_scaled"]
    orb_factor: float
    relative_speed_deg_per_day: float | None
    orb_rate_deg_per_day: float | None
    state: Literal["applying", "exact", "separating", "stationary", "indeterminate"]
    exact_tolerance_deg: float
    rate_tolerance_deg_per_day: float
    body1_stationary_threshold_deg_per_day: float
    body2_stationary_threshold_deg_per_day: float
    body1_stationary: bool | None
    body2_stationary: bool | None
    relative_motion_stalled: bool | None
    stationary_reasons: list[AspectMotionStationaryReasonValue]
    reference_frame: str
    timescale: str
    provenance: Literal["caller_supplied_longitudes_and_speeds"]
    evaluation_scope: Literal["instantaneous_no_event_search"]


class AspectMotionComputationTruthResponse(_StrictModel):
    source_module: Literal["moira.aspects"] = "moira.aspects"
    engine_entrypoint: Literal["aspect_motion_witness"] = "aspect_motion_witness"
    facade_entrypoint: Literal["Moira.aspect_motion_witness"] = (
        "Moira.aspect_motion_witness"
    )
    branch_error_formula: Literal[
        "shortest_directed_separation_minus_same_sign_exact_target"
    ] = "shortest_directed_separation_minus_same_sign_exact_target"
    relative_speed_formula: Literal["speed2_minus_speed1"] = "speed2_minus_speed1"
    motion_classification: Literal["instantaneous_signed_error_rate"] = (
        "instantaneous_signed_error_rate"
    )
    stationary_policy: Literal[
        "body_specific_threshold_or_relative_rate_tolerance"
    ] = "body_specific_threshold_or_relative_rate_tolerance"
    orb_policy_authority: Literal["moira.constants.Aspect"] = "moira.constants.Aspect"
    provenance_semantics: Literal["caller_declared_frame_and_timescale"] = (
        "caller_declared_frame_and_timescale"
    )


class AspectMotionAnalysisResponse(_StrictModel):
    witness: AspectMotionWitnessResponse
    computation_truth: AspectMotionComputationTruthResponse


class MoonConnectionFlowRequest(_StrictModel):
    jd_ut: float
    previous_window_policy: Literal["current_sign", "fixed_lookback"]
    previous_lookback_days: float | None = Field(default=None, gt=0.0, le=30.0)
    modern: bool = False
    motion_orb_factor: float = Field(default=1.0, gt=0.0, le=10.0)
    motion_exact_tolerance_deg: float = Field(default=1e-9, ge=0.0, le=1.0)
    motion_rate_tolerance_deg_per_day: float = Field(
        default=1e-12, ge=0.0, le=1.0
    )

    @field_validator(
        "jd_ut",
        "previous_lookback_days",
        "motion_orb_factor",
        "motion_exact_tolerance_deg",
        "motion_rate_tolerance_deg_per_day",
        mode="before",
    )
    @classmethod
    def _finite_flow_values(cls, value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, bool):
            raise ValueError("Moon flow numeric values must be finite")
        try:
            parsed = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("Moon flow numeric values must be finite") from exc
        if not math.isfinite(parsed):
            raise ValueError("Moon flow numeric values must be finite")
        return parsed

    @field_validator("modern", mode="before")
    @classmethod
    def _strict_modern(cls, value: Any) -> bool:
        if not isinstance(value, bool):
            raise ValueError("modern must be a boolean")
        return value

    @model_validator(mode="after")
    def _coherent_previous_window(self) -> "MoonConnectionFlowRequest":
        if self.previous_window_policy == "current_sign":
            if self.previous_lookback_days is not None:
                raise ValueError(
                    "current_sign previous window rejects previous_lookback_days"
                )
        elif self.previous_lookback_days is None:
            raise ValueError(
                "fixed_lookback previous window requires previous_lookback_days"
            )
        return self


class MoonConnectionFlowPolicyResponse(_StrictModel):
    previous_window: Literal["current_sign", "fixed_lookback"]
    previous_lookback_days: float | None
    modern: bool
    motion_orb_factor: float
    motion_exact_tolerance_deg: float
    motion_rate_tolerance_deg_per_day: float


class MoonAspectEventResponse(_StrictModel):
    role: Literal["previous_separation", "next_connection"]
    body: str
    aspect_name: Literal["Conjunction", "Sextile", "Square", "Trine", "Opposition"]
    directional_angle_deg: float
    signed_target_deg: float
    jd_exact: float
    hours_from_query: float
    moon_longitude_at_exact_deg: float
    body_longitude_at_exact_deg: float
    signed_error_at_exact_deg: float
    signed_error_at_query_deg: float


class MoonConnectionFlowResponse(_StrictModel):
    jd_query: float
    moon_sign: str
    jd_sign_ingress: float
    jd_sign_egress: float
    previous_search_start: float
    previous_search_end: float
    next_search_start: float
    next_search_end: float
    policy: MoonConnectionFlowPolicyResponse
    considered_bodies: list[str]
    previous_separation: MoonAspectEventResponse | None
    previous_motion: AspectMotionWitnessResponse | None
    next_connection: MoonAspectEventResponse | None
    previous_no_event_reason: str | None
    next_no_event_reason: str | None
    reference_frame: Literal["apparent_geocentric_true_ecliptic_of_date"]
    timescale: Literal["UT1_input_with_internal_TT_ephemeris"]
    motion_speed_product: Literal[
        "planet_at_geocentric_astrometric_longitude_rate"
    ]
    event_search: Literal["exact_directional_major_aspect_perfection"]
    interpretation: Literal["none_geometry_only"]


class MoonConnectionFlowComputationTruthResponse(_StrictModel):
    source_module: Literal["moira.aspect_events"] = "moira.aspect_events"
    engine_entrypoint: Literal["moon_connection_flow_at"] = "moon_connection_flow_at"
    facade_entrypoint: Literal["Moira.moon_connection_flow_at"] = (
        "Moira.moon_connection_flow_at"
    )
    previous_window_semantics: Literal["caller_declared"] = "caller_declared"
    next_window_semantics: Literal["current_tropical_sign"] = (
        "current_tropical_sign"
    )
    doctrine_semantics: Literal["none_geometry_only"] = "none_geometry_only"
    motion_speed_semantics: Literal[
        "planet_at_geocentric_astrometric_longitude_rate"
    ] = "planet_at_geocentric_astrometric_longitude_rate"


class MoonConnectionFlowAnalysisResponse(_StrictModel):
    flow: MoonConnectionFlowResponse
    computation_truth: MoonConnectionFlowComputationTruthResponse


class SynastryAspectTruthResponse(_StrictModel):
    source_label: str
    target_label: str
    source_body: str
    target_body: str
    tier: int
    include_nodes: bool
    orb_factor: float
    custom_orbs: bool
    source_speed: float | None = None
    target_speed: float | None = None


class SynastryAspectClassificationResponse(_StrictModel):
    contact_mode: str
    pair_mode: str
    includes_nodes: bool
    uses_custom_orbs: bool


class SynastryRelationResponse(_StrictModel):
    kind: str
    basis: str
    source_label: str
    target_label: str
    source_ref: str | None = None
    target_ref: str | None = None
    method: str | None = None


class SynastryConditionProfileResponse(_StrictModel):
    result_kind: str
    condition_state: str
    pair_mode: str
    relation_kind: str
    relation_basis: str
    method: str | None = None
    includes_nodes: bool | None = None
    includes_house_frame: bool | None = None
    has_house_fallback: bool | None = None


class SynastryContactResponse(_StrictModel):
    aspect: AspectDataResponse
    truth: SynastryAspectTruthResponse
    classification: SynastryAspectClassificationResponse | None = None
    relation: SynastryRelationResponse | None = None
    condition_profile: SynastryConditionProfileResponse | None = None


class SynastryAspectSearchResponse(_StrictModel):
    events: list[AspectDataResponse]


class SynastryContactSearchResponse(_StrictModel):
    events: list[SynastryContactResponse]


class SynastryRelationListResponse(_StrictModel):
    relations: list[SynastryRelationResponse]


class SynastryConditionProfileListResponse(_StrictModel):
    profiles: list[SynastryConditionProfileResponse]


class HousePlacementResponse(_StrictModel):
    house: int
    longitude: float
    exact_on_cusp: bool
    cusp_longitude: float


class SynastryOverlayTruthResponse(_StrictModel):
    source_label: str
    target_label: str
    include_nodes: bool
    point_count: int
    target_house_system: str
    target_effective_house_system: str
    target_has_fallback: bool


class SynastryOverlayClassificationResponse(_StrictModel):
    overlay_mode: str
    pair_mode: str
    includes_nodes: bool
    has_house_fallback: bool


class SynastryHouseOverlayResponse(_StrictModel):
    source_label: str
    target_label: str
    placements: dict[str, HousePlacementResponse]
    include_nodes: bool
    computation_truth: SynastryOverlayTruthResponse | None = None
    classification: SynastryOverlayClassificationResponse | None = None
    relation: SynastryRelationResponse | None = None
    condition_profile: SynastryConditionProfileResponse | None = None


class MutualHouseOverlayResponse(_StrictModel):
    first_in_second: SynastryHouseOverlayResponse
    second_in_first: SynastryHouseOverlayResponse


class CompositeComputationTruthResponse(_StrictModel):
    method: str
    jd_mean: float
    includes_house_frame: bool
    reference_latitude: float | None = None
    house_system: str | None = None
    composite_mc: float | None = None
    composite_armc: float | None = None
    source_house_system: str | None = None
    source_effective_house_system: str | None = None


class CompositeClassificationResponse(_StrictModel):
    chart_mode: str
    method: str
    includes_house_frame: bool


class CompositeChartResponse(_StrictModel):
    planets: dict[str, float]
    nodes: dict[str, float]
    aspects: AspectsFromLongitudesResponse
    cusps: list[float]
    asc: float | None = None
    mc: float | None = None
    jd_mean: float
    computation_truth: CompositeComputationTruthResponse | None = None
    classification: CompositeClassificationResponse | None = None
    relation: SynastryRelationResponse | None = None
    condition_profile: SynastryConditionProfileResponse | None = None


class _DerivedChartRequest(SynastryPairRequest):
    tier: Literal[0, 1, 2] | None = None
    orb_factor: float | None = Field(default=None, gt=0.0, le=10.0)
    include_nodes: bool | None = None

    @field_validator("tier", mode="before")
    @classmethod
    def _strict_derived_tier(cls, value: Any) -> Any:
        if isinstance(value, bool):
            raise ValueError("tier must be 0, 1, or 2")
        return value

    @field_validator("orb_factor", mode="before")
    @classmethod
    def _strict_derived_orb_factor(cls, value: Any) -> Any:
        if isinstance(value, bool):
            raise ValueError("orb_factor must be a finite number")
        return value

    @field_validator("include_nodes", mode="before")
    @classmethod
    def _strict_derived_include_nodes(cls, value: Any) -> Any:
        if value is not None and not isinstance(value, bool):
            raise ValueError("include_nodes must be a boolean")
        return value


class CompositeChartRequest(_DerivedChartRequest):
    method: str = "midpoint"
    reference_latitude: float | None = None
    house_system: str | None = None


class DavisonComputationTruthResponse(_StrictModel):
    method: str
    raw_midpoint_jd: float
    used_jd: float
    latitude_mode: str
    longitude_mode: str
    latitude_midpoint: float
    longitude_midpoint: float
    house_system: str
    corrected_target_mc: float | None = None
    correction_applied: bool


class DavisonClassificationResponse(_StrictModel):
    chart_mode: str
    method: str
    latitude_mode: str
    longitude_mode: str
    correction_mode: str


class DavisonInfoResponse(_StrictModel):
    jd_midpoint: float
    datetime_utc: str
    latitude_midpoint: float
    longitude_midpoint: float
    computation_truth: DavisonComputationTruthResponse | None = None
    classification: DavisonClassificationResponse | None = None
    relation: SynastryRelationResponse | None = None
    condition_profile: SynastryConditionProfileResponse | None = None


class DavisonChartResponse(_StrictModel):
    chart: ChartResponse
    aspects: AspectsFromLongitudesResponse
    houses: HousesResponse | None = None
    info: DavisonInfoResponse


class DavisonChartRequest(_DerivedChartRequest):
    method: str = "midpoint_location"
    reference_latitude: float | None = None
    reference_longitude: float | None = None
    house_system: str | None = None


class SynastryChartConditionProfileResponse(_StrictModel):
    profiles: list[SynastryConditionProfileResponse]
    contact_count: int
    overlay_count: int
    relationship_chart_count: int
    strongest_profiles: list[SynastryConditionProfileResponse]
    weakest_profiles: list[SynastryConditionProfileResponse]


class SynastryConditionNetworkNodeResponse(_StrictModel):
    node_id: str
    kind: str
    incoming_count: int
    outgoing_count: int
    total_degree: int


class SynastryConditionNetworkEdgeResponse(_StrictModel):
    source_id: str
    target_id: str
    relation_kind: str
    relation_basis: str
    condition_state: str


class SynastryConditionNetworkProfileResponse(_StrictModel):
    nodes: list[SynastryConditionNetworkNodeResponse]
    edges: list[SynastryConditionNetworkEdgeResponse]
    isolated_nodes: list[SynastryConditionNetworkNodeResponse]
    most_connected_nodes: list[SynastryConditionNetworkNodeResponse]


class SingleChartAnalysisRequest(_StrictModel):
    chart: RelationshipPartyRequest
    include_nodes: bool = False


class ChartShapeResponse(_StrictModel):
    shape: str
    occupied_arc: float
    largest_gap: float
    leading_planet: str | None = None
    handle_planet: str | None = None
    handle_bodies: list[str] = Field(default_factory=list)
    clusters: list[list[str]]


class PatternRequest(_StrictModel):
    chart: RelationshipPartyRequest
    include_nodes: bool = False
    orb_factor: float = Field(default=1.0, gt=0.0, le=10.0)
    include: list[str] | None = None
    dominant_only: bool = False

    @field_validator("orb_factor", mode="before")
    @classmethod
    def _strict_orb_factor(cls, value: Any) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("orb_factor must be a number")
        return value

    @field_validator("dominant_only", mode="before")
    @classmethod
    def _strict_dominant_only(cls, value: Any) -> bool:
        if not isinstance(value, bool):
            raise ValueError("dominant_only must be a boolean")
        return value


class PatternBodyRoleTruthResponse(_StrictModel):
    body: str
    role: str


class PatternDetectionTruthResponse(_StrictModel):
    pattern_name: str
    detector: str
    source_kind: str
    orb_factor: float
    body_roles: list[PatternBodyRoleTruthResponse]
    centroid_longitude: float | None = None
    max_body_distance: float | None = None
    orb_limit: float | None = None


class PatternBodyRoleClassificationResponse(_StrictModel):
    body: str
    role: str


class PatternClassificationResponse(_StrictModel):
    pattern_name: str
    detector: str
    source_kind: str
    symmetry: str
    body_count: int
    has_apex: bool
    body_roles: list[PatternBodyRoleClassificationResponse]


class PatternAspectContributionResponse(_StrictModel):
    pattern_name: str
    role: str
    body1: str
    body2: str
    aspect_name: str
    aspect_angle: float
    aspect: AspectDataResponse


class PatternConditionProfileResponse(_StrictModel):
    pattern_name: str
    detector: str
    source_kind: str
    symmetry: str
    body_count: int
    has_apex: bool
    contribution_count: int
    all_contribution_count: int
    structured_contribution_count: int
    generic_contribution_count: int
    state: str


class AspectPatternResponse(_StrictModel):
    name: str
    bodies: list[str]
    aspects: list[AspectDataResponse]
    apex: str | None = None
    detection_truth: PatternDetectionTruthResponse | None = None
    classification: PatternClassificationResponse | None = None
    all_contributions: list[PatternAspectContributionResponse]
    contributions: list[PatternAspectContributionResponse]
    condition_profile: PatternConditionProfileResponse | None = None


class PatternSearchResponse(_StrictModel):
    events: list[AspectPatternResponse]


class PatternChartConditionProfileResponse(_StrictModel):
    profiles: list[PatternConditionProfileResponse]
    reinforced_count: int
    mixed_count: int
    weakened_count: int
    structured_contribution_total: int
    generic_contribution_total: int
    strongest_patterns: list[str]
    weakest_patterns: list[str]


class PatternConditionNetworkNodeResponse(_StrictModel):
    node_id: str
    kind: str
    label: str
    incoming_count: int
    outgoing_count: int
    total_degree: int


class PatternConditionNetworkEdgeResponse(_StrictModel):
    source_id: str
    target_id: str
    pattern_name: str
    role: str


class PatternConditionNetworkProfileResponse(_StrictModel):
    nodes: list[PatternConditionNetworkNodeResponse]
    edges: list[PatternConditionNetworkEdgeResponse]
    isolated_bodies: list[str]
    most_connected_nodes: list[str]


class MidpointRequest(_StrictModel):
    chart: RelationshipPartyRequest
    planet_set: str = "classic"
    include_nodes: bool = False


class MidpointResponse(_StrictModel):
    planet_a: str
    planet_b: str
    longitude: float
    sign: str
    sign_symbol: str
    sign_degree: float


class MidpointSearchResponse(_StrictModel):
    events: list[MidpointResponse]


class MidpointToPointRequest(MidpointRequest):
    target: float
    orb: float = 1.5


class MidpointHitResponse(_StrictModel):
    midpoint: MidpointResponse
    orb: float


class MidpointHitSearchResponse(_StrictModel):
    events: list[MidpointHitResponse]


class PlanetaryPictureResponse(_StrictModel):
    focus: str
    pair_a: str
    pair_b: str
    midpoint_longitude: float
    orb: float
    dial: float


class PlanetaryPictureSearchResponse(_StrictModel):
    events: list[PlanetaryPictureResponse]


class MidpointWeightResponse(_StrictModel):
    planet: str
    score: int
    pictures: list[PlanetaryPictureResponse]


class MidpointWeightSearchResponse(_StrictModel):
    events: list[MidpointWeightResponse]


class MidpointClusterResponse(_StrictModel):
    dial_position: float
    midpoints: list[MidpointResponse]
    spread: float
    dial: float


class MidpointClusterSearchResponse(_StrictModel):
    events: list[MidpointClusterResponse]


class PlanetaryPictureRequest(MidpointRequest):
    orb: float = 1.5
    dial: float = 360.0


class MidpointWeightRequest(MidpointRequest):
    orb: float = 1.5
    dial: float = 360.0


class MidpointClusterRequest(MidpointRequest):
    cluster_orb: float = 1.0
    min_size: int = 3
    dial: float = 90.0


__all__ = [
    "AspectDataResponse",
    "AspectMotionAnalysisResponse",
    "AspectMotionComputationTruthResponse",
    "AspectMotionNameValue",
    "AspectMotionStationaryReasonValue",
    "AspectMotionWitnessRequest",
    "AspectMotionWitnessResponse",
    "AspectsFromLongitudesRequest",
    "AspectsFromLongitudesResponse",
    "DeclinationAspectComputationTruthResponse",
    "DeclinationAspectMotionAnalysisResponse",
    "DeclinationAspectMotionComputationTruthResponse",
    "DeclinationAspectMotionWitnessRequest",
    "DeclinationAspectMotionWitnessResponse",
    "DeclinationAspectResponse",
    "DeclinationAspectsFromDeclinationsRequest",
    "DeclinationAspectsFromDeclinationsResponse",
    "AspectPatternResponse",
    "ChartShapeResponse",
    "CompositeChartRequest",
    "CompositeChartResponse",
    "DavisonChartRequest",
    "DavisonChartResponse",
    "MidpointClusterRequest",
    "MidpointClusterResponse",
    "MidpointClusterSearchResponse",
    "MidpointHitResponse",
    "MidpointHitSearchResponse",
    "MidpointRequest",
    "MidpointResponse",
    "MidpointSearchResponse",
    "MidpointToPointRequest",
    "MidpointWeightRequest",
    "MidpointWeightResponse",
    "MidpointWeightSearchResponse",
    "LongitudeAspectComputationTruthResponse",
    "MoonAspectEventResponse",
    "MoonConnectionFlowAnalysisResponse",
    "MoonConnectionFlowComputationTruthResponse",
    "MoonConnectionFlowPolicyResponse",
    "MoonConnectionFlowRequest",
    "MoonConnectionFlowResponse",
    "MutualHouseOverlayResponse",
    "PatternChartConditionProfileResponse",
    "PatternConditionNetworkProfileResponse",
    "PatternRequest",
    "PatternSearchResponse",
    "PlanetaryPictureRequest",
    "PlanetaryPictureResponse",
    "PlanetaryPictureSearchResponse",
    "RelationshipPartyRequest",
    "SingleChartAnalysisRequest",
    "SynastryAspectSearchResponse",
    "SynastryChartConditionProfileResponse",
    "SynastryConditionNetworkProfileResponse",
    "SynastryConditionProfileListResponse",
    "SynastryContactSearchResponse",
    "SynastryDirectionalOverlayRequest",
    "SynastryPairRequest",
    "SynastryRelationListResponse",
]
