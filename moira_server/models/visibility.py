"""Transport models for the explicit observational-visibility surface."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from moira.heliacal import (
    LightPollutionClass,
    LightPollutionDerivationMode,
    MoonlightPolicy,
    ObserverAid,
    PhysicalBackgroundComponentKind,
    PhysicalBackgroundScope,
    PhysicalEventTimeSemantics,
    PhysicalVisibilityBoundarySource,
    PhysicalVisibilityCrossingDirection,
    PhysicalVisibilityEvidenceState,
    PhysicalVisibilityPhase,
    PhysicalVisibilityStatus,
    VisibilityCriterionFamily,
    VisibilityExtinctionModel,
    VisibilityTwilightModel,
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class _StrictResponseModel(_StrictModel):
    model_config = ConfigDict(
        extra="forbid",
        allow_inf_nan=False,
        from_attributes=True,
    )


_SHA256_PATTERN = r"^[0-9a-f]{64}$"


class LunarCrescentDetailsResponse(_StrictModel):
    best_time_jd_ut: float
    sunset_jd_ut: float
    moonset_jd_ut: float
    lag_minutes: float
    arcl_deg: float
    arcv_deg: float
    daz_deg: float
    moon_altitude_deg: float
    sun_altitude_deg: float
    lunar_parallax_arcmin: float
    topocentric_crescent_width_arcmin: float
    q: float
    visibility_class: str


class ObserverVisibilityEnvironmentRequest(_StrictModel):
    light_pollution_class: LightPollutionClass | None = LightPollutionClass.BORTLE_3
    limiting_magnitude: float | None = None
    sky_surface_brightness_mag_arcsec2: float | None = Field(default=None, gt=0.0)
    local_horizon_altitude_deg: float = Field(default=0.0, ge=-90.0, le=90.0)
    temperature_c: float = 10.0
    pressure_mbar: float = Field(default=1013.25, ge=0.0)
    relative_humidity: float = Field(default=0.5, ge=0.0, le=1.0)
    observer_altitude_m: float = Field(default=0.0, ge=-1000.0)
    observing_aid: ObserverAid = ObserverAid.NAKED_EYE


class VisibilityPolicyRequest(_StrictModel):
    criterion_family: VisibilityCriterionFamily = (
        VisibilityCriterionFamily.LIMITING_MAGNITUDE_THRESHOLD
    )
    environment: ObserverVisibilityEnvironmentRequest | None = None
    light_pollution_derivation_mode: LightPollutionDerivationMode = (
        LightPollutionDerivationMode.BORTLE_LINEAR
    )
    extinction_model: VisibilityExtinctionModel = (
        VisibilityExtinctionModel.LEGACY_ARCUS_VISIONIS
    )
    twilight_model: VisibilityTwilightModel = (
        VisibilityTwilightModel.ARCUS_VISIONIS_SOLAR_DEPRESSION
    )
    use_refraction: bool = True
    moonlight_policy: MoonlightPolicy = MoonlightPolicy.IGNORE
    extinction_coefficient_k: float = Field(default=0.20, ge=0.0)
    crumey_field_factor: float = Field(default=2.0, gt=0.0)
    crumey_field_factor_includes_atmosphere: bool = True


class VisibilityAssessmentRequest(_StrictModel):
    body: str
    jd_ut: float
    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)
    policy: VisibilityPolicyRequest | None = None


class PhysicalAtmosphereInputRequest(_StrictModel):
    atmosphere_profile: str = "us_standard"
    aerosol_profile: str = "rural_summer"
    observer_altitude_m: float = 0.0
    surface_pressure_hpa: float = 1013.25
    aod550: float = 0.1
    angstrom_exponent: float = 1.3
    ozone_du: float = 300.0
    ground_albedo: float = 0.2


class PhysicalDirectionalBackgroundRequest(_StrictModel):
    kind: Literal["directional"]
    photopic_luminance_cd_m2: float
    scotopic_luminance_cd_m2: float
    scope: PhysicalBackgroundScope
    component_ids: tuple[str, ...]
    source_id: str
    source_receipt_sha256: str = Field(pattern=_SHA256_PATTERN)
    method_id: str
    component_inventory_complete: bool = False


class PhysicalSqmBackgroundRequest(_StrictModel):
    kind: Literal["sqm"]
    sqm_mag_arcsec2: float
    scotopic_to_photopic_ratio: float
    scope: PhysicalBackgroundScope
    component_ids: tuple[str, ...]
    measurement_source_id: str
    measurement_receipt_sha256: str = Field(pattern=_SHA256_PATTERN)
    device_bandpass_id: str
    pointing_receipt_id: str
    temporal_applicability_id: str
    spectral_ratio_source_id: str
    component_inventory_complete: bool = False


class PhysicalBortleBackgroundRequest(_StrictModel):
    kind: Literal["bortle"]
    light_pollution_class: LightPollutionClass
    scotopic_to_photopic_ratio: float = Field(gt=0.0)
    spectral_ratio_source_id: str
    source_receipt_sha256: str = Field(pattern=_SHA256_PATTERN)


PhysicalBackgroundRequest = Annotated[
    PhysicalDirectionalBackgroundRequest
    | PhysicalSqmBackgroundRequest
    | PhysicalBortleBackgroundRequest,
    Field(discriminator="kind"),
]


class PhysicalModeledBackgroundComponentRequest(_StrictModel):
    component_kind: PhysicalBackgroundComponentKind
    photopic_luminance_cd_m2: float
    scotopic_luminance_cd_m2: float
    model_id: str
    source_ids: tuple[str, ...]
    source_receipt_sha256: str = Field(pattern=_SHA256_PATTERN)
    spatial_applicability_id: str
    temporal_applicability_id: str
    direction_receipt_id: str
    validity_domain_id: str
    uncertainty_authority_id: str


class PhysicalHorizonSampleRequest(_StrictModel):
    azimuth_deg: float
    apparent_altitude_deg: float


class PhysicalHorizonProfileRequest(_StrictModel):
    samples: tuple[PhysicalHorizonSampleRequest, ...]
    profile_id: str
    source_id: str
    source_receipt_sha256: str = Field(pattern=_SHA256_PATTERN)


class PhysicalVisibilityPolicyRequest(_StrictModel):
    background: PhysicalBackgroundRequest | None = None
    atmosphere: PhysicalAtmosphereInputRequest = Field(
        default_factory=PhysicalAtmosphereInputRequest
    )
    composite_model_id: Literal[
        "clear_sky_naked_eye_point_source_v1"
    ] = "clear_sky_naked_eye_point_source_v1"
    expected_data_pack_id: Literal[
        "moira-physical-heliacal-visibility"
    ] = "moira-physical-heliacal-visibility"
    expected_manifest_sha256: str | None = Field(
        default=None,
        pattern=_SHA256_PATTERN,
    )
    observer_protocol_id: Literal[
        "known_location_directed_averted_observation_v1"
    ] = "known_location_directed_averted_observation_v1"
    local_horizon_altitude_deg: float = Field(
        default=0.0,
        ge=-5.0,
        le=90.0,
    )
    refraction_model_id: Literal[
        "bennett_extended_v1"
    ] = "bennett_extended_v1"
    refraction_pressure_hpa: float = Field(default=1013.25, gt=0.0)
    refraction_temperature_c: float = 15.0
    refraction_relative_humidity: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
    )
    directional_horizon: PhysicalHorizonProfileRequest | None = None
    modeled_background_components: tuple[
        PhysicalModeledBackgroundComponentRequest,
        ...,
    ] = ()


class PhysicalVisibilitySearchPolicyRequest(_StrictModel):
    search_window_days: int = Field(default=400, gt=0)
    scan_step_days: float = Field(default=5.0 / 1440.0, gt=0.0)
    adaptive_minimum_step_days: float = Field(
        default=30.0 / 86400.0,
        gt=0.0,
    )
    root_time_tolerance_days: float = Field(
        default=0.25 / 86400.0,
        gt=0.0,
    )
    root_margin_tolerance_magnitude: float = Field(
        default=1.0e-5,
        gt=0.0,
    )
    near_zero_tolerance_magnitude: float = Field(
        default=2.5e-3,
        gt=0.0,
    )
    curvature_tolerance_magnitude: float = Field(
        default=5.0e-3,
        gt=0.0,
    )
    maximum_adaptive_depth: int = Field(default=12, gt=0)
    maximum_root_iterations: int = Field(default=96, gt=0)


class PhysicalVisibilityAssessmentRequest(_StrictModel):
    body: str = Field(min_length=1)
    jd_ut: float
    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)
    policy: PhysicalVisibilityPolicyRequest | None = None


class PhysicalVisibilityEventRequest(_StrictModel):
    body: str = Field(min_length=1)
    phase: PhysicalVisibilityPhase
    jd_start: float
    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)
    policy: PhysicalVisibilityPolicyRequest | None = None
    search_policy: PhysicalVisibilitySearchPolicyRequest | None = None


class AtmosphericExtinctionRequest(_StrictModel):
    apparent_altitude_deg: float = Field(ge=0.0, le=90.0)
    model: Literal[
        VisibilityExtinctionModel.KASTEN_YOUNG_1989_BROADBAND,
        VisibilityExtinctionModel.SCHAEFER_1993_COMPONENTS,
    ]
    extinction_coefficient_k: float = Field(default=0.20, ge=0.0)
    observer_altitude_m: float = Field(default=0.0, ge=-1000.0)
    relative_humidity: float = Field(default=0.5, ge=0.0, le=1.0)
    observer_latitude_deg: float = Field(default=0.0, ge=-90.0, le=90.0)
    sun_right_ascension_deg: float = 0.0


class TwilightSkyBrightnessRequest(_StrictModel):
    target_altitude_deg: float = Field(ge=0.0, le=90.0)
    sun_altitude_deg: float
    sun_target_separation_deg: float = Field(ge=0.0, le=180.0)
    extinction_coefficient_k: float = Field(default=0.20, ge=0.0)


class PointSourceVisibilityThresholdRequest(_StrictModel):
    background_nanolamberts: float = Field(gt=0.0)
    field_factor: float = Field(default=2.0, gt=0.0)


class AtmosphericExtinctionResponse(_StrictModel):
    model: str
    apparent_altitude_deg: float
    zenith_distance_deg: float
    broadband_airmass: float | None
    rayleigh_airmass: float | None
    aerosol_airmass: float | None
    ozone_airmass: float | None
    rayleigh_coefficient_mag_per_airmass: float | None
    aerosol_coefficient_mag_per_airmass: float | None
    ozone_coefficient_mag_per_airmass: float | None
    total_zenith_extinction_coefficient: float
    sky_brightness_extinction_coefficient: float
    extinction_magnitude: float
    transmission_fraction: float


class TwilightSkyBrightnessResponse(_StrictModel):
    model: str
    target_altitude_deg: float
    sun_altitude_deg: float
    sun_target_separation_deg: float
    sky_airmass: float
    extinction_coefficient: float
    formula_applied: bool
    valid: bool
    reason: str | None
    sky_nanolamberts: float | None


class PointSourceVisibilityThresholdResponse(_StrictModel):
    criterion_family: str
    background_nanolamberts: float
    background_luminance_cd_m2: float
    field_factor: float
    valid_background_min_cd_m2: float
    valid_background_max_cd_m2: float
    valid: bool
    reason: str | None
    limiting_magnitude: float | None


class VisibilityAssessmentResponse(_StrictModel):
    body: str
    jd_ut: float
    criterion_family: str
    effective_limiting_magnitude: float | None
    apparent_magnitude: float
    true_altitude_deg: float
    apparent_altitude_deg: float
    local_horizon_altitude_deg: float
    solar_elongation_deg: float
    is_geometrically_visible: bool
    is_bright_enough: bool
    observable: bool
    lunar_crescent_details: LunarCrescentDetailsResponse | None = None
    moonlight_sky_nanolamberts: float | None = None
    extinction_adjusted_magnitude: float | None = None
    visibility_margin_magnitude: float | None = None
    criterion_target_magnitude: float | None = None
    target_extinction_applied_separately: bool = False
    criterion_applicable: bool = True
    criterion_reason: str | None = None
    atmospheric_extinction: AtmosphericExtinctionResponse | None = None
    twilight_sky_brightness: TwilightSkyBrightnessResponse | None = None
    point_source_threshold: PointSourceVisibilityThresholdResponse | None = None
    dark_sky_nanolamberts: float | None = None
    total_sky_nanolamberts: float | None = None


class VisibilityDataPackReceiptResponse(_StrictResponseModel):
    pack_id: str
    version: str
    compatibility_id: str
    composite_model_id: str
    table_format_id: str
    engine_contract_id: str
    engine_contract_version: int
    manifest_sha256: str
    generation_fingerprint: str
    payload_sha256: tuple[tuple[str, str], ...]
    source_artifact_spec_id: str
    source_artifact_manifest_sha256: str
    source_dataset_ids: tuple[str, ...]
    license: str
    notice_sha256: str


class VisibilityComponentReceiptResponse(_StrictResponseModel):
    role: str
    component_id: str
    source_ids: tuple[str, ...]
    details: tuple[tuple[str, str], ...] = ()


class PhysicalAtmosphereReceiptResponse(_StrictResponseModel):
    complete: bool
    within_data_pack_domain: bool | None
    atmosphere_profile: str
    aerosol_profile: str
    observer_altitude_m: float
    surface_pressure_hpa: float
    aod550: float
    angstrom_exponent: float
    ozone_du: float
    ground_albedo: float


class PhysicalValidityDomainReceiptResponse(_StrictResponseModel):
    no_extrapolation: bool
    solar_center_altitude_domain_deg: tuple[float, float]
    target_true_altitude_domain_deg: tuple[float, float]
    relative_solar_azimuth_domain_deg: tuple[float, float]
    queried_solar_center_altitude_deg: float | None
    queried_target_true_altitude_deg: float | None
    queried_relative_solar_azimuth_deg: float | None
    within_domain: bool | None


class PhysicalObserverProtocolReceiptResponse(_StrictResponseModel):
    protocol_id: str
    task: str
    optical_aid: str
    adaptation_field: str
    local_horizon_altitude_deg: float
    refraction_model_id: str
    refraction_pressure_hpa: float
    refraction_temperature_c: float
    refraction_relative_humidity: float
    horizon_model_id: str
    directional_profile_applied: bool
    directional_profile_id: str | None
    directional_profile_source_id: str | None
    directional_profile_source_receipt_sha256: str | None
    detection_field_factor_model_id: str
    detection_field_factor_value: float
    detection_field_factor_mutable: bool
    detection_field_factor_source_ids: tuple[str, ...]
    probabilistic_detection_claimed: bool


class PhysicalBackgroundReceiptResponse(_StrictResponseModel):
    authority_id: str
    component_ids: tuple[str, ...]
    source_ids: tuple[str, ...]
    photopic_luminance_cd_m2: float
    scotopic_luminance_cd_m2: float
    mesopic_luminance_cd_m2: float
    scotopic_to_photopic_ratio: float
    adaptation_coefficient: float
    weighting_state: str
    adaptation_solver_method: str
    photopic_solver_relative_standard_error_bound: float | None
    scotopic_solver_relative_standard_error_bound: float | None
    solver_uncertainty_bound_method: str | None
    photopic_interpolation_maximum_error_mag: float | None
    photopic_interpolation_p95_error_mag: float | None
    scotopic_interpolation_maximum_error_mag: float | None
    scotopic_interpolation_p95_error_mag: float | None
    storage_maximum_error_mag: float | None
    component_inventory_complete: bool
    modeled_component_count: int


class PhysicalTargetReceiptResponse(_StrictResponseModel):
    target_id: str
    photometry_model_id: str
    photometry_source_ids: tuple[str, ...]
    spectral_profile_id: str
    spectral_source_ids: tuple[str, ...]
    spectral_source_receipt_sha256: str
    spectral_model_details: tuple[tuple[str, str], ...]
    top_of_atmosphere_visual_magnitude: float
    scotopic_to_photopic_ratio: float
    photopic_transmission: float
    scotopic_transmission: float
    conditioned_target_magnitude: float
    direct_interpolation_maximum_error_mag: float
    direct_interpolation_p95_error_mag: float
    storage_maximum_error_mag: float


class PhysicalThresholdReceiptResponse(_StrictResponseModel):
    model_id: str
    background_luminance_cd_m2: float
    field_factor: float
    threshold_illuminance_lux: float
    limiting_magnitude: float
    valid_background_min_cd_m2: float
    valid_background_max_cd_m2: float
    equation_receipt: str


class PhysicalVisibilityErrorBudgetReceiptResponse(_StrictResponseModel):
    method_id: str
    background_error_authority: str
    solver_relative_standard_error_multiplier: float | None
    background_mesopic_luminance_envelope_lower_cd_m2: float
    background_mesopic_luminance_envelope_upper_cd_m2: float
    limiting_magnitude_envelope_lower: float
    limiting_magnitude_envelope_upper: float
    conditioned_target_magnitude_maximum_pack_error: float
    visibility_margin_envelope_lower_magnitude: float
    visibility_margin_envelope_upper_magnitude: float
    visibility_margin_envelope_maximum_deviation_magnitude: float
    visibility_classification_within_data_pack_envelope: str
    included_error_sources: tuple[str, ...]
    unquantified_error_sources: tuple[str, ...]


class PhysicalHorizonReceiptResponse(_StrictResponseModel):
    horizon_model_id: str
    apparent_horizon_altitude_deg: float | None
    directional_profile_applied: bool
    refraction_model_id: str
    refraction_pressure_hpa: float
    refraction_temperature_c: float
    refraction_relative_humidity: float
    applied_to: tuple[str, ...]
    target_apparent_boundary_altitude_deg: float | None = None
    solar_apparent_horizon_altitude_deg: float | None = None
    data_pack_target_true_altitude_floor_deg: float | None = None
    target_boundary_narrowing_applied: bool = False
    directional_profile_id: str | None = None
    directional_profile_source_id: str | None = None
    directional_profile_source_receipt_sha256: str | None = None
    interpolation_method_id: str | None = None
    profile_sample_count: int | None = None
    admitted_maximum_gap_deg: float | None = None
    actual_maximum_gap_deg: float | None = None
    maximum_absolute_slope_deg_per_deg: float | None = None
    cone_signal_lipschitz_factor: float | None = None
    queried_target_azimuth_deg: float | None = None
    queried_solar_azimuth_deg: float | None = None
    target_local_horizon_altitude_deg: float | None = None
    solar_local_horizon_altitude_deg: float | None = None
    event_certificate_id: str | None = None
    event_certificate_source_sha256: str | None = None
    event_certificate_maximum_absolute_rate_per_day: float | None = None


class PhysicalVisibilityAssessmentResponse(_StrictResponseModel):
    body: str
    jd_ut: float
    latitude_deg: float
    longitude_deg: float
    status: PhysicalVisibilityStatus
    evidence_state: PhysicalVisibilityEvidenceState
    reason: str | None
    true_target_altitude_deg: float | None
    apparent_target_altitude_deg: float | None
    true_solar_center_altitude_deg: float | None
    relative_solar_azimuth_deg: float | None
    geometrically_visible: bool | None
    visible: bool | None
    observable: bool | None
    visibility_margin_magnitude: float | None
    data_pack_receipt: VisibilityDataPackReceiptResponse | None
    atmosphere_receipt: PhysicalAtmosphereReceiptResponse
    validity_domain_receipt: PhysicalValidityDomainReceiptResponse | None
    observer_protocol_receipt: PhysicalObserverProtocolReceiptResponse
    background_receipt: PhysicalBackgroundReceiptResponse | None
    target_receipt: PhysicalTargetReceiptResponse | None
    threshold_receipt: PhysicalThresholdReceiptResponse | None
    error_budget_receipt: PhysicalVisibilityErrorBudgetReceiptResponse | None
    components: tuple[VisibilityComponentReceiptResponse, ...]
    horizon_receipt: PhysicalHorizonReceiptResponse | None = None


class PhysicalObservationWindowReceiptResponse(_StrictResponseModel):
    observation_day_key: int
    start_jd_ut: float
    end_jd_ut: float
    target_boundary_jd_ut: float
    target_boundary_role: str
    solar_side: str


class PhysicalEventSolverReceiptResponse(_StrictResponseModel):
    search_window_days: int
    scan_step_days: float
    bracket_tolerance_days: float
    adaptive_minimum_step_days: float
    root_time_tolerance_days: float
    root_margin_tolerance_magnitude: float
    near_zero_tolerance_magnitude: float
    curvature_tolerance_magnitude: float
    candidate_day_count: int
    guard_day_count: int
    classified_day_count: int
    evaluable_day_count: int
    observation_window_count: int
    scalar_evaluation_count: int
    sign_changing_root_count: int
    tangent_root_count: int
    near_zero_interval_count: int
    non_evaluable_gap_count: int
    maximum_sample_gap_days: float | None
    classified_day_states: tuple[
        tuple[int, str, str | None, str | None],
        ...,
    ]
    non_evaluable_day_states: tuple[tuple[int, str, str | None], ...]
    crossing_completeness_state: str
    crossing_completeness_reason: str | None
    crossing_certificate_ids: tuple[str, ...] = ()
    crossing_certificate_source_sha256: str | None = None
    root_enclosure_count: int = 0
    unresolved_certificate_interval_count: int = 0


class PhysicalEventSensitivityReceiptResponse(_StrictResponseModel):
    data_pack_numerical_event_interval_jd_ut: tuple[float, float] | None
    data_pack_numerical_reason: str | None
    atmospheric_scenario_event_interval_jd_ut: tuple[float, float] | None
    atmospheric_scenario_reason: str | None
    probabilistic_confidence_claimed: bool


class PhysicalEphemerisReceiptResponse(_StrictResponseModel):
    provider_id: str
    input_timescale: str
    ephemeris_timescale: str
    direction_frame: str
    horizontal_frame: str
    refraction_applied_separately: bool


class PhysicalVisibilityEventResponse(_StrictResponseModel):
    body: str
    phase: PhysicalVisibilityPhase
    latitude_deg: float
    longitude_deg: float
    status: PhysicalVisibilityStatus
    evidence_state: PhysicalVisibilityEvidenceState
    reason: str | None
    observation_day_key: int | None
    comparison_observation_day_key: int | None
    comparison_day_status: str | None
    event_jd_ut: float | None
    event_time_semantics: PhysicalEventTimeSemantics | None
    target_horizon_jd_ut: float | None
    peak_margin_jd_ut: float | None
    peak_margin_magnitude: float | None
    boundary_role: str | None
    crossing_direction: PhysicalVisibilityCrossingDirection | None
    boundary_source: PhysicalVisibilityBoundarySource | None
    visibility_margin_residual_magnitude: float | None
    visibility_margin_bracket_jd_ut: tuple[float, float] | None
    root_iterations: int | None
    derived_arcus_deg: float | None
    assessment_jd_ut: float | None
    observation_window: PhysicalObservationWindowReceiptResponse | None
    event_assessment: PhysicalVisibilityAssessmentResponse | None
    data_pack_receipt: VisibilityDataPackReceiptResponse | None
    atmosphere_receipt: PhysicalAtmosphereReceiptResponse
    observer_protocol_receipt: PhysicalObserverProtocolReceiptResponse
    horizon_receipt: PhysicalHorizonReceiptResponse
    ephemeris_receipt: PhysicalEphemerisReceiptResponse | None
    solver_receipt: PhysicalEventSolverReceiptResponse
    sensitivity_receipt: PhysicalEventSensitivityReceiptResponse
    components: tuple[VisibilityComponentReceiptResponse, ...]


__all__ = [
    "LunarCrescentDetailsResponse",
    "ObserverVisibilityEnvironmentRequest",
    "VisibilityPolicyRequest",
    "VisibilityAssessmentRequest",
    "PhysicalAtmosphereInputRequest",
    "PhysicalDirectionalBackgroundRequest",
    "PhysicalSqmBackgroundRequest",
    "PhysicalBortleBackgroundRequest",
    "PhysicalBackgroundRequest",
    "PhysicalModeledBackgroundComponentRequest",
    "PhysicalHorizonSampleRequest",
    "PhysicalHorizonProfileRequest",
    "PhysicalVisibilityPolicyRequest",
    "PhysicalVisibilitySearchPolicyRequest",
    "PhysicalVisibilityAssessmentRequest",
    "PhysicalVisibilityEventRequest",
    "AtmosphericExtinctionRequest",
    "TwilightSkyBrightnessRequest",
    "PointSourceVisibilityThresholdRequest",
    "AtmosphericExtinctionResponse",
    "TwilightSkyBrightnessResponse",
    "PointSourceVisibilityThresholdResponse",
    "VisibilityAssessmentResponse",
    "VisibilityDataPackReceiptResponse",
    "VisibilityComponentReceiptResponse",
    "PhysicalAtmosphereReceiptResponse",
    "PhysicalValidityDomainReceiptResponse",
    "PhysicalObserverProtocolReceiptResponse",
    "PhysicalBackgroundReceiptResponse",
    "PhysicalTargetReceiptResponse",
    "PhysicalThresholdReceiptResponse",
    "PhysicalVisibilityErrorBudgetReceiptResponse",
    "PhysicalHorizonReceiptResponse",
    "PhysicalVisibilityAssessmentResponse",
    "PhysicalObservationWindowReceiptResponse",
    "PhysicalEventSolverReceiptResponse",
    "PhysicalEventSensitivityReceiptResponse",
    "PhysicalEphemerisReceiptResponse",
    "PhysicalVisibilityEventResponse",
]
