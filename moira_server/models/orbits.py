"""Transport models for orbital-elements endpoints."""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field, field_validator

from moira.constants import Body


ADMITTED_ORBIT_BODIES = (
    Body.MERCURY,
    Body.VENUS,
    Body.EARTH,
    Body.MARS,
    Body.JUPITER,
    Body.SATURN,
    Body.URANUS,
    Body.NEPTUNE,
    Body.PLUTO,
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _OrbitBaseRequest(_StrictModel):
    body: str
    jd_ut: float

    @field_validator("body")
    @classmethod
    def _valid_body(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("body must be non-empty")
        return stripped

    @field_validator("jd_ut")
    @classmethod
    def _finite_jd_ut(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("jd_ut must be finite")
        return value

    @field_validator("jd_ut", mode="before")
    @classmethod
    def _jd_ut_is_not_boolean(cls, value):
        if isinstance(value, bool):
            raise ValueError("jd_ut must be a real number, not a Boolean")
        return value


class OrbitalElementsRequest(_OrbitBaseRequest):
    pass


class DistanceExtremesRequest(_OrbitBaseRequest):
    pass


class OrbitalElementsResponse(_StrictModel):
    name: str
    epoch_jd: float
    semi_major_axis_au: float | None = None
    eccentricity: float
    inclination_deg: float
    lon_ascending_node_deg: float
    arg_perihelion_deg: float
    mean_anomaly_deg: float | None = None
    mean_motion_deg_per_day: float | None = None
    orbital_period_days: float | None = None
    perihelion_distance_au: float
    aphelion_distance_au: float | None = None


class DistanceExtremesResponse(_StrictModel):
    name: str
    perihelion_jd: float
    perihelion_distance_au: float
    aphelion_jd: float
    aphelion_distance_au: float


class OrbitRequestEchoResponse(_StrictModel):
    body: str
    jd_ut: float


class OrbitTimeConversionResponse(_StrictModel):
    """Allowlisted policy receipt for the UT1 -> TT -> TDB conversion."""

    delta_t_policy: str
    delta_t_source_product: str
    delta_t_retarget_mode: str
    delta_t_correction_seconds: float
    identity_iterations: int
    tt_tdb_policy: str
    tt_tdb_version: str
    tt_tdb_source_url: str
    tt_tdb_source_sha256: str
    tt_tdb_source_bytes: int
    tt_tdb_iterations: int


class OrbitTimeResponse(_StrictModel):
    """Truthful clock envelope for Stage 1 orbital-element responses."""

    input_time_scale: str = "UT1_JD"
    state_evaluation_scale: str = "TDB_JD"
    output_time_scale: str = "TT_JD"
    jd_ut: float
    epoch_tt: float
    epoch_tdb: float
    delta_t_seconds: float
    tdb_minus_tt_seconds: float
    conversion: OrbitTimeConversionResponse


class DistanceExtremesTimeResponse(OrbitTimeResponse):
    """Truthful Stage 2 clock envelope for the distance-extremes route."""


class OrbitalGravityResponse(_StrictModel):
    rule: str
    gm_km3_s2: float
    units: str = "km^3/s^2"
    component_naif_ids: list[int]
    component_gm_km3_s2: list[float]
    policy: str
    source_url: str
    retrieved_date: str
    source_sha256: str
    source_bytes: int
    planetary_ephemeris: str


class OrbitalFrameConstructionResponse(_StrictModel):
    frame: str
    routine: str
    router_branch: str
    precession_model: str | None
    obliquity_model: str
    nutation_model: str | None
    admitted_interval_tt: list[float] | None


class OrbitalStateLegResponse(_StrictModel):
    center_naif_id: int
    target_naif_id: int
    traversal_sign: int
    segment_type: int
    coverage_start_tdb: float
    coverage_end_tdb: float
    kernel_label: str
    kernel_sha256: str
    kernel_bytes: int
    pool_index: int
    catalog_id: str | None
    catalog_version: str | None
    manifest_sha256: str | None
    released_utc: str | None
    planetary_ephemeris: str | None
    coverage_restricted_to_observed_arc: bool | None


class OrbitalStateSourceResponse(_StrictModel):
    legs: list[OrbitalStateLegResponse]
    covered_intervals_tdb: list[list[float]]
    pool_generation: int


class ApsidalPassageOutcomeResponse(_StrictModel):
    status: str
    epoch_tdb: float | None
    epoch_tt: float | None
    jd_ut: float | None
    distance_au: float | None
    coverage_edge_tdb: float | None
    detail: str


class ApsidalRouteScheduleEntryResponse(_StrictModel):
    start_tdb: float
    end_tdb: float
    route_identity: str
    legs: list[OrbitalStateLegResponse]


class ApsidalSegmentUsageResponse(_StrictModel):
    leg: OrbitalStateLegResponse
    evaluations: int


class ApsidalSeamContinuityResponse(_StrictModel):
    epoch_tdb: float
    left_route_identity: str
    right_route_identity: str
    position_residual_km: float
    velocity_residual_km_per_day: float
    position_tolerance_km: float
    velocity_tolerance_km_per_day: float
    admitted: bool
    detail: str


class OrbitalSingularityThresholdsResponse(_StrictModel):
    circular_e_tolerance: float
    equatorial_sin_i_tolerance: float
    parabolic_e_tolerance: float
    rectilinear_normalized_h_tolerance: float
    policy: str


class OrbitalElementsProvenanceResponse(_StrictModel):
    source_module: str = "moira.orbits"
    engine_entrypoint: str = "osculating_elements"
    reader_owner: str
    center: str
    frame: str
    orientation: str = "fixed_J2000_ecliptic"
    element_type: str = "osculating"
    position_basis: str = "center_relative_state_vector"
    apparent_corrections: str = "not_applied"
    light_time_correction: str = "not_applied"
    mean_element_table: str = "not_used"
    gravity: OrbitalGravityResponse
    frame_construction: OrbitalFrameConstructionResponse
    state_source: OrbitalStateSourceResponse
    singularity_thresholds: OrbitalSingularityThresholdsResponse
    stage_sequence: list[str]


class OrbitProvenanceResponse(_StrictModel):
    source_module: str = "moira.orbits"
    engine_entrypoint: str
    reader_owner: str
    center: str = "sun"
    frame: str = "J2000_ecliptic_and_equinox"
    orientation: str = "fixed_J2000_ecliptic"
    element_type: str = "osculating"
    state_source: str = "DE_series_kernel"
    position_basis: str = "heliocentric_state_vector"
    apparent_corrections: str = "not_applied"
    light_time_correction: str = "not_applied"
    mean_element_table: str = "not_used"
    event_basis: str | None = None
    search_direction: str | None = None
    search_owner: str | None = None
    perihelion_event: str | None = None
    aphelion_event: str | None = None
    chronological_order_forced: bool | None = None
    stage_sequence: list[str]


class ApsidalPassagesProvenanceResponse(_StrictModel):
    algorithm_version: str
    gravity: OrbitalGravityResponse
    time_conversion: OrbitTimeConversionResponse
    state_source: OrbitalStateSourceResponse
    initial_period_fraction: float
    radial_timescale_fraction: float
    minimum_step_days: float
    maximum_step_days: float
    witness_root_tolerance_factor: float
    witness_minimum_step_fraction: float
    witness_motion_timescale_fraction: float
    witness_maximum_offset_days: float
    refinement_tolerance_days: float
    maximum_root_iterations: int
    evaluation_budget: int
    extremum_semantics: str
    search_window_source: str
    route_plan_identity: str
    route_schedule: list[ApsidalRouteScheduleEntryResponse]
    segment_usage: list[ApsidalSegmentUsageResponse]
    seam_continuity: list[ApsidalSeamContinuityResponse]
    searched_interval_tdb: list[float]
    total_evaluations: int


class DistanceExtremesProvenanceResponse(_StrictModel):
    source_module: str = "moira.orbits"
    engine_entrypoint: str = "apsidal_passages"
    reader_owner: str
    center: str = "SUN"
    direction: str = "NEXT"
    pericenter: ApsidalPassageOutcomeResponse
    apocenter: ApsidalPassageOutcomeResponse
    search: ApsidalPassagesProvenanceResponse
    stage_sequence: list[str]


class OrbitalElementsEnvelopeResponse(_StrictModel):
    request: OrbitRequestEchoResponse
    time: OrbitTimeResponse
    elements: OrbitalElementsResponse
    provenance: OrbitalElementsProvenanceResponse


class DistanceExtremesEnvelopeResponse(_StrictModel):
    request: OrbitRequestEchoResponse
    time: DistanceExtremesTimeResponse
    distance_extremes: DistanceExtremesResponse
    provenance: DistanceExtremesProvenanceResponse


class OrbitClassRequest(_OrbitBaseRequest):
    """Request for one small-body osculating orbit classification."""


class OrbitClassPredicateMarginResponse(_StrictModel):
    parameter: str
    operator: str
    boundary: float
    value: float
    margin: float
    satisfied: bool
    unit: str


class OrbitClassResponse(_StrictModel):
    name: str
    code: str
    title: str
    description: str
    is_near_earth_asteroid: bool
    is_potentially_hazardous_candidate: bool
    condition_summary: str
    predicates: list[OrbitClassPredicateMarginResponse]


class OrbitClassProvenanceResponse(_StrictModel):
    source_module: str = "moira.orbits"
    engine_entrypoint: str = "orbit_class"
    reader_owner: str
    center: str = "SUN"
    frame: str = "J2000_ECLIPTIC"
    classification_policy: str = "jpl_sbdb_osculating_v1"
    gravity: OrbitalGravityResponse
    state_source: OrbitalStateSourceResponse
    stage_sequence: list[str]


class OrbitClassEnvelopeResponse(_StrictModel):
    request: OrbitRequestEchoResponse
    time: OrbitTimeResponse
    orbit_class: OrbitClassResponse
    provenance: OrbitClassProvenanceResponse


MAX_ORBIT_CLASS_BATCH_BODIES = 1000


class OrbitClassBatchRequest(_StrictModel):
    bodies: list[str] = Field(min_length=1, max_length=MAX_ORBIT_CLASS_BATCH_BODIES)
    jd_ut: float

    @field_validator("bodies")
    @classmethod
    def _valid_bodies(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for body in value:
            stripped = body.strip()
            if not stripped:
                raise ValueError("bodies entries must be non-empty")
            cleaned.append(stripped)
        return cleaned

    @field_validator("jd_ut")
    @classmethod
    def _finite_jd_ut(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("jd_ut must be finite")
        return value

    @field_validator("jd_ut", mode="before")
    @classmethod
    def _jd_ut_is_not_boolean(cls, value):
        if isinstance(value, bool):
            raise ValueError("jd_ut must be a real number, not a Boolean")
        return value


class OrbitClassBatchEchoResponse(_StrictModel):
    bodies_count: int
    jd_ut: float


class OrbitClassBatchItemErrorResponse(_StrictModel):
    error_code: str
    message: str
    category: str


class OrbitClassBatchProvenanceResponse(_StrictModel):
    source_module: str = "moira.orbits"
    engine_entrypoint: str = "orbit_classes_at"
    reader_owner: str
    center: str = "SUN"
    frame: str = "J2000_ECLIPTIC"
    classification_policy: str = "jpl_sbdb_osculating_v1"
    stage_sequence: list[str]


class OrbitClassBatchEnvelopeResponse(_StrictModel):
    request: OrbitClassBatchEchoResponse
    time: OrbitTimeResponse
    results: dict[str, OrbitClassResponse]
    errors: dict[str, OrbitClassBatchItemErrorResponse]
    total_requested: int
    total_succeeded: int
    total_failed: int
    provenance: OrbitClassBatchProvenanceResponse

