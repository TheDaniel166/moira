"""Strict transport contracts for source-scoped Pancha Pakshi products."""

from __future__ import annotations

from datetime import datetime, timezone
from math import gcd
from typing import Literal

from pydantic import Field, field_validator, model_validator

from moira.pancha_pakshi import (
    PanchaPakshiActivity,
    PanchaPakshiAdmissionStatus,
    PanchaPakshiAstronomicalPaksha,
    PanchaPakshiBird,
    PanchaPakshiCapability,
    PanchaPakshiCurrentCellSelectionStatus,
    PanchaPakshiHalf,
    PanchaPakshiMaterializedCellRelation,
    PanchaPakshiPaksha,
    PanchaPakshiRelation,
    PanchaPakshiSolarBoundaryRelation,
    PanchaPakshiWeekday,
)

from .common import _StrictModel


class PanchaPakshiProfileRequest(_StrictModel):
    """Base request: selection is always explicit and never ambient."""

    profile_id: str = Field(min_length=1)

    @field_validator("profile_id")
    @classmethod
    def _non_blank_profile_id(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("profile_id must be non-empty; there is no default canon")
        return value


class PanchaPakshiAksaraIdentityRequest(PanchaPakshiProfileRequest):
    initial_vowel: str = Field(min_length=1)

    @field_validator("initial_vowel")
    @classmethod
    def _one_explicit_symbol(cls, value: str) -> str:
        value = value.strip()
        if len(value) != 1:
            raise ValueError("initial_vowel must be one explicitly listed vowel symbol")
        return value


class PanchaPakshiNominalScheduleRequest(PanchaPakshiProfileRequest):
    paksha: PanchaPakshiPaksha
    half: PanchaPakshiHalf
    weekday: PanchaPakshiWeekday


class PanchaPakshiFirstEatBirdMappingRequest(PanchaPakshiProfileRequest):
    """Select one source-attested first-samam Eat bird without scheduling."""

    profile_paksha: PanchaPakshiPaksha
    half: PanchaPakshiHalf
    weekday: PanchaPakshiWeekday


class PanchaPakshiPaduBirdMappingRequest(PanchaPakshiProfileRequest):
    """Select one source-attested Padu bird without temporal routing."""

    profile_paksha: PanchaPakshiPaksha
    weekday: PanchaPakshiWeekday


class PanchaPakshiFractionRequest(_StrictModel):
    """One exact, reduced rational input; floating point is not admitted."""

    numerator: int
    denominator: int = Field(gt=0)

    @model_validator(mode="after")
    def _reduced_form(self) -> "PanchaPakshiFractionRequest":
        if gcd(abs(self.numerator), self.denominator) != 1:
            raise ValueError("fraction input must be in reduced form")
        return self


class PanchaPakshiSookshmaSelectionRequest(PanchaPakshiProfileRequest):
    """Select within one samam under one explicitly named source policy."""

    policy_id: Literal[
        "bogamuni_2024_weighted_sookshma_samam_v1",
        "bogamuni_2024_eka_sookshma_equal_fifths_v1",
    ]
    parent_activity: PanchaPakshiActivity
    elapsed_nazhigai: PanchaPakshiFractionRequest


class PanchaPakshiLocalSolarContextRequest(PanchaPakshiProfileRequest):
    """Route one aware civil instant through the admitted local-solar policy."""

    dt: datetime
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    paksha: PanchaPakshiPaksha
    policy_id: Literal["local_solar_day_explicit_paksha_v1"]

    @field_validator("dt")
    @classmethod
    def _aware_datetime_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value.astimezone(timezone.utc)


class PanchaPakshiAstronomicalPakshaRequest(PanchaPakshiProfileRequest):
    """Infer the source-mapped paksha from one aware civil instant."""

    dt: datetime
    policy_id: Literal[
        "apparent_geocentric_moon_sun_longitude_paksha_half_open_v1"
    ]

    @field_validator("dt", mode="before")
    @classmethod
    def _require_iso_datetime_input(cls, value: object) -> object:
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str):
            raise ValueError("dt must be an ISO 8601 date-time")
        candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            datetime.fromisoformat(candidate)
        except ValueError as exc:
            raise ValueError("dt must be an ISO 8601 date-time") from exc
        return value

    @field_validator("dt")
    @classmethod
    def _aware_datetime_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value.astimezone(timezone.utc)


class PanchaPakshiNatalMoonIdentityRequest(PanchaPakshiProfileRequest):
    """Apply the one admitted natal-Moon composition at an aware instant."""

    dt: datetime
    policy_id: Literal[
        "bogamuni_2024_apparent_lahiri_natal_moon_identity_v1"
    ]

    @field_validator("dt", mode="before")
    @classmethod
    def _require_iso_datetime_input(cls, value: object) -> object:
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str):
            raise ValueError("dt must be an ISO 8601 date-time")
        candidate = value[:-1] + "+00:00" if value.endswith("Z") else value
        try:
            datetime.fromisoformat(candidate)
        except ValueError as exc:
            raise ValueError("dt must be an ISO 8601 date-time") from exc
        return value

    @field_validator("dt")
    @classmethod
    def _aware_datetime_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value.astimezone(timezone.utc)


class PanchaPakshiFixedClockMaterializationRequest(PanchaPakshiProfileRequest):
    """Materialize one fixed-clock schedule from an aware civil instant."""

    dt: datetime
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    paksha: PanchaPakshiPaksha
    policy_id: Literal[
        "fixed_24_minute_nazhigai_from_local_solar_half_start_v1"
    ]

    @field_validator("dt")
    @classmethod
    def _aware_datetime_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value.astimezone(timezone.utc)


class PanchaPakshiFixedClockCurrentCellRequest(PanchaPakshiProfileRequest):
    """Select one fixed-clock cell for an explicit aware civil instant."""

    dt: datetime
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    paksha: PanchaPakshiPaksha
    policy_id: Literal[
        "fixed_clock_current_cell_half_open_solar_precedence_v1"
    ]

    @field_validator("dt")
    @classmethod
    def _aware_datetime_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value.astimezone(timezone.utc)


class PanchaPakshiSolarProportionalMaterializationRequest(
    PanchaPakshiProfileRequest
):
    """Scale exact nominal offsets over one governing local-solar half."""

    dt: datetime
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    paksha: PanchaPakshiPaksha
    policy_id: Literal[
        "solar_proportional_nominal_offsets_over_governing_half_tt_v1"
    ]

    @field_validator("dt")
    @classmethod
    def _aware_datetime_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value.astimezone(timezone.utc)


class PanchaPakshiSolarProportionalCurrentCellRequest(
    PanchaPakshiProfileRequest
):
    """Select one proportional cell for an explicit aware civil instant."""

    dt: datetime
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    paksha: PanchaPakshiPaksha
    policy_id: Literal[
        "solar_proportional_current_cell_half_open_solar_precedence_v1"
    ]

    @field_validator("dt")
    @classmethod
    def _aware_datetime_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value.astimezone(timezone.utc)


class PanchaPakshiDirectedRelationshipRequest(PanchaPakshiProfileRequest):
    subject: PanchaPakshiBird
    target: PanchaPakshiBird


class PanchaPakshiFractionResponse(_StrictModel):
    numerator: int
    denominator: int = Field(gt=0)


class PanchaPakshiSourceLocatorResponse(_StrictModel):
    locator_id: str
    witness_id: str
    label: str
    url: str
    evidence_role: str


class PanchaPakshiSourceResponse(_StrictModel):
    witness_id: str
    title: str
    traditional_attribution: str
    authorship_status: str
    publication_place: str
    publisher: str
    publication_year: int
    language: str
    archive_item_url: str
    archive_original_image_zip_name: str
    archive_original_image_zip_source_status: str
    archive_original_image_zip_md5: str
    archive_original_image_zip_sha1: str
    archive_pdf_name: str
    archive_pdf_source_status: str
    archive_pdf_md5: str
    archive_pdf_sha1: str
    locally_verified_pdf_sha256: str
    catalogued_contributor_note: str
    artifact_distribution_status: str
    redistribution_policy: str
    license_scope: str
    artifact_distribution_note: str


class PanchaPakshiOmissionResponse(_StrictModel):
    feature: str
    status: str
    reason: str


class PanchaPakshiConflictWitnessResponse(_StrictModel):
    witness_id: str
    bibliographic_label: str
    record_url: str
    record_identity: str
    conflict_locators: list[str]
    evidence_status: str
    runtime_status: str


class PanchaPakshiProfileDescriptorResponse(_StrictModel):
    profile_id: str
    admission_status: PanchaPakshiAdmissionStatus
    product_kind: str
    default_selection_allowed: bool
    capabilities: list[PanchaPakshiCapability]
    admission_decision_id: str


class PanchaPakshiProvenanceResponse(_StrictModel):
    profile_id: str
    admission_status: PanchaPakshiAdmissionStatus
    product_kind: str
    default_selection_allowed: bool
    capabilities: list[PanchaPakshiCapability]
    admission_decision_id: str
    derivation_status: str
    assembly_policy: str
    astronomical_routing_status: str
    source: PanchaPakshiSourceResponse
    declared_omissions: list[PanchaPakshiOmissionResponse]


class PanchaPakshiProfileInfoResponse(_StrictModel):
    title: str
    provenance: PanchaPakshiProvenanceResponse
    source_locators: list[PanchaPakshiSourceLocatorResponse]
    known_conflict_witnesses: list[PanchaPakshiConflictWitnessResponse]


class PanchaPakshiProfilesResponse(_StrictModel):
    profiles: list[PanchaPakshiProfileDescriptorResponse]
    total: int
    default_profile_selected: bool = False


class PanchaPakshiAksaraIdentityResponse(_StrictModel):
    profile_id: str
    identity_kind: str
    input_symbol: str
    normalized_symbol: str
    bird: PanchaPakshiBird
    is_natal_moon_identity: bool
    source_locators: list[PanchaPakshiSourceLocatorResponse]
    provenance: PanchaPakshiProvenanceResponse


class PanchaPakshiDirectedRelationshipResponse(_StrictModel):
    profile_id: str
    model_kind: str
    subject: PanchaPakshiBird
    target: PanchaPakshiBird
    relation: PanchaPakshiRelation
    is_reciprocal_inference: bool
    source_locators: list[PanchaPakshiSourceLocatorResponse]
    provenance: PanchaPakshiProvenanceResponse


class PanchaPakshiScheduleCellResponse(_StrictModel):
    samam_index: int
    sequence_index: int
    bird: PanchaPakshiBird
    activity: PanchaPakshiActivity
    start_nazhigai: PanchaPakshiFractionResponse
    end_nazhigai: PanchaPakshiFractionResponse
    duration_nazhigai: PanchaPakshiFractionResponse
    derivation_status: str
    assembly_policy: str
    source_locators: list[PanchaPakshiSourceLocatorResponse]


class PanchaPakshiNominalScheduleResponse(_StrictModel):
    profile_id: str
    admission_status: PanchaPakshiAdmissionStatus
    product_kind: str
    generator_id: str
    paksha: PanchaPakshiPaksha
    half: PanchaPakshiHalf
    weekday: PanchaPakshiWeekday
    first_eat_bird: PanchaPakshiBird
    temporal_model_kind: str
    span_nazhigai: PanchaPakshiFractionResponse
    samam_span_nazhigai: PanchaPakshiFractionResponse
    cells: list[PanchaPakshiScheduleCellResponse]
    provenance: PanchaPakshiProvenanceResponse


class PanchaPakshiAstronomicalPakshaInferencePolicyResponse(_StrictModel):
    policy_id: Literal[
        "apparent_geocentric_moon_sun_longitude_paksha_half_open_v1"
    ]
    input_time_scale: Literal["ut1"]
    ephemeris_time_scale: Literal["reader_bound_tt"]
    position_origin: Literal["geocentric"]
    position_frame: Literal["true_ecliptic_of_date"]
    apparent: Literal[True]
    aberration: Literal[True]
    grav_deflection: Literal[True]
    nutation: Literal[True]
    elongation_definition: Literal[
        "normalized_moon_longitude_minus_sun_longitude"
    ]
    elongation_domain: Literal["degrees_half_open_0_360"]
    shukla_interval: Literal["0_inclusive_180_exclusive"]
    krishna_interval: Literal["180_inclusive_360_exclusive"]
    boundary_tolerance_degrees: Literal[0.0]
    ayanamsa_status: Literal[
        "not_applied_common_longitude_offset_cancels"
    ]
    profile_mapping_basis: Literal[
        "direct_source_attested_waxing_waning"
    ]
    purva_source_locator_id: Literal["ia_n16"]
    amara_source_locator_id: Literal["ia_n26"]
    schedule_selection_status: Literal["not_performed"]
    materialization_status: Literal["not_performed"]
    natal_identity_status: Literal["not_performed"]


class PanchaPakshiAstronomicalPakshaResponse(_StrictModel):
    profile_id: str
    requested_jd_ut1: float = Field(allow_inf_nan=False)
    requested_jd_tt: float = Field(allow_inf_nan=False)
    policy: PanchaPakshiAstronomicalPakshaInferencePolicyResponse
    sun_longitude_deg: float = Field(ge=0.0, lt=360.0)
    moon_longitude_deg: float = Field(ge=0.0, lt=360.0)
    moon_minus_sun_elongation_deg: float = Field(ge=0.0, lt=360.0)
    astronomical_paksha: PanchaPakshiAstronomicalPaksha
    profile_paksha: PanchaPakshiPaksha
    mapping_status: Literal["direct_source_attested"]
    mapping_source_locators: list[PanchaPakshiSourceLocatorResponse] = Field(
        min_length=1,
        max_length=1,
    )
    provenance: PanchaPakshiProvenanceResponse


class PanchaPakshiNakshatraBirdMappingResponse(_StrictModel):
    """One source-table cell, explicitly distinct from the natal composition."""

    profile_id: str
    profile_paksha: PanchaPakshiPaksha
    nakshatra_index: int = Field(ge=0, le=26)
    nakshatra: str
    bird: PanchaPakshiBird
    mapping_status: Literal["direct_source_attested"]
    source_table_semantics: Literal[
        "nakshatra_bird_table_not_explicitly_natal_moon"
    ]
    assembly_policy: Literal[
        "verse_precedence_for_nakshatra_partition"
    ]
    source_locators: list[PanchaPakshiSourceLocatorResponse] = Field(
        min_length=1,
        max_length=1,
    )
    provenance: PanchaPakshiProvenanceResponse


class PanchaPakshiPaduBirdMappingResponse(_StrictModel):
    """One source table cell; not a schedule activity or current-time role."""

    profile_id: str
    profile_paksha: PanchaPakshiPaksha
    weekday: PanchaPakshiWeekday
    bird: PanchaPakshiBird
    mapping_status: Literal["direct_source_attested"]
    source_table_semantics: Literal[
        "profile_paksha_weekday_death_or_inoperative_bird_not_schedule_"
        "rule_activity"
    ]
    assembly_policy: Literal[
        "paksha_stanzas_govern_repeated_combined_table_confirms"
    ]
    source_locators: list[PanchaPakshiSourceLocatorResponse] = Field(
        min_length=3,
        max_length=3,
    )
    provenance: PanchaPakshiProvenanceResponse


class PanchaPakshiSookshmaActivityDurationResponse(_StrictModel):
    activity: PanchaPakshiActivity
    duration_nazhigai: PanchaPakshiFractionResponse


class PanchaPakshiSookshmaSelectorPolicyResponse(_StrictModel):
    policy_id: Literal[
        "bogamuni_2024_weighted_sookshma_samam_v1",
        "bogamuni_2024_eka_sookshma_equal_fifths_v1",
    ]
    source_layer: str
    partition_kind: Literal["weighted_activity_durations", "five_equal_parts"]
    container_span_nazhigai: PanchaPakshiFractionResponse
    interval_count: Literal[5]
    interval_ownership: Literal["half_open"]
    sequence_policy: str
    activity_assignment_status: Literal[
        "source_attested_cyclic_activity_rows",
        "not_attested",
    ]
    activity_durations_nazhigai: list[
        PanchaPakshiSookshmaActivityDurationResponse
    ] = Field(max_length=5)
    automatic_policy_selection: Literal["forbidden"]
    uromarisi_composition_status: Literal[
        "not_performed_requires_separate_explicit_cross_witness_decision"
    ]
    outcome_interpretation_status: Literal["not_performed"]
    source_locator_ids: list[str] = Field(min_length=2, max_length=2)


class PanchaPakshiSookshmaIntervalResponse(_StrictModel):
    ordinal: int = Field(ge=1, le=5)
    activity: PanchaPakshiActivity | None
    start_nazhigai: PanchaPakshiFractionResponse
    end_nazhigai: PanchaPakshiFractionResponse
    duration_nazhigai: PanchaPakshiFractionResponse


class PanchaPakshiSookshmaSelectionResponse(_StrictModel):
    profile_id: str
    parent_activity: PanchaPakshiActivity
    elapsed_nazhigai: PanchaPakshiFractionResponse
    policy: PanchaPakshiSookshmaSelectorPolicyResponse
    intervals: list[PanchaPakshiSookshmaIntervalResponse] = Field(
        min_length=5,
        max_length=5,
    )
    selected_ordinal: int = Field(ge=1, le=5)
    selected_interval: PanchaPakshiSookshmaIntervalResponse
    source_locators: list[PanchaPakshiSourceLocatorResponse] = Field(
        min_length=2,
        max_length=2,
    )
    provenance: PanchaPakshiProvenanceResponse


class PanchaPakshiFirstEatBirdMappingResponse(_StrictModel):
    """One first-samam Eat seed; not Padu, authority, condition, or score."""

    profile_id: str
    generator_id: str
    profile_paksha: PanchaPakshiPaksha
    half: PanchaPakshiHalf
    weekday: PanchaPakshiWeekday
    first_eat_bird: PanchaPakshiBird
    mapping_status: Literal["direct_source_attested"]
    source_table_semantics: Literal[
        "profile_paksha_half_weekday_first_samam_eat_seed_not_padu_"
        "authority_condition_or_score"
    ]
    source_locators: list[PanchaPakshiSourceLocatorResponse] = Field(
        min_length=3,
        max_length=4,
    )
    provenance: PanchaPakshiProvenanceResponse

    @model_validator(mode="after")
    def _canonical_locator_count(
        self,
    ) -> "PanchaPakshiFirstEatBirdMappingResponse":
        expected = 3 if self.half is PanchaPakshiHalf.DAY else 4
        if len(self.source_locators) != expected:
            raise ValueError(
                f"{self.half.value} mapping must contain exactly "
                f"{expected} canonical source locators"
            )
        return self


class PanchaPakshiNatalMoonIdentityPolicyResponse(_StrictModel):
    policy_id: Literal[
        "bogamuni_2024_apparent_lahiri_natal_moon_identity_v1"
    ]
    composition_status: Literal["modern_moira_policy_not_source_claim"]
    source_table_semantics: Literal[
        "nakshatra_bird_table_not_explicitly_natal_moon"
    ]
    input_time_scale: Literal["ut1"]
    ephemeris_time_scale: Literal["reader_bound_tt"]
    position_origin: Literal["geocentric"]
    position_frame: Literal["true_ecliptic_of_date"]
    apparent: Literal[True]
    aberration: Literal[True]
    grav_deflection: Literal[True]
    nutation: Literal[True]
    elongation_definition: Literal[
        "normalized_moon_longitude_minus_sun_longitude"
    ]
    shukla_interval: Literal["0_inclusive_180_exclusive"]
    krishna_interval: Literal["180_inclusive_360_exclusive"]
    phase_boundary_tolerance_degrees: Literal[0.0]
    phase_to_profile_mapping: Literal[
        "direct_source_attested_new_moon_purva_full_moon_amara"
    ]
    phase_mapping_source_locator_id: Literal["bogar_n167_phase"]
    ayanamsa_system: Literal["Lahiri"]
    ayanamsa_mode: Literal["true"]
    ayanamsa_status: Literal[
        "fixed_modern_moira_policy_not_source_attested"
    ]
    nakshatra_partition: Literal[
        "27_equal_half_open_40_over_3_degree_sectors"
    ]
    exact_internal_boundary_ownership: Literal["following_nakshatra"]
    binary_boundary_recovery: Literal[
        "maximum_one_ulp_below_internal_boundary"
    ]
    mapping_assembly_policy: Literal[
        "verse_precedence_for_nakshatra_partition"
    ]
    schedule_selection_status: Literal["not_performed"]
    materialization_status: Literal["not_performed"]
    current_cell_status: Literal["not_performed"]
    scoring_status: Literal["not_performed"]
    forecast_status: Literal["not_performed"]


class PanchaPakshiNatalMoonIdentityResponse(_StrictModel):
    """Transparent result for the modern natal-Moon/source-table composition."""

    profile_id: str
    requested_jd_ut1: float = Field(allow_inf_nan=False)
    requested_jd_tt: float = Field(allow_inf_nan=False)
    policy: PanchaPakshiNatalMoonIdentityPolicyResponse
    sun_longitude_deg: float = Field(ge=0.0, lt=360.0)
    moon_tropical_longitude_deg: float = Field(ge=0.0, lt=360.0)
    moon_minus_sun_elongation_deg: float = Field(ge=0.0, lt=360.0)
    astronomical_paksha: PanchaPakshiAstronomicalPaksha
    profile_paksha: PanchaPakshiPaksha
    phase_mapping_source_locators: list[
        PanchaPakshiSourceLocatorResponse
    ] = Field(min_length=1, max_length=1)
    ayanamsa_deg: float = Field(allow_inf_nan=False)
    moon_sidereal_longitude_deg: float = Field(ge=0.0, lt=360.0)
    nakshatra_index: int = Field(ge=0, le=26)
    nakshatra: str
    degrees_in_nakshatra: float = Field(ge=0.0, lt=40.0 / 3.0)
    bird: PanchaPakshiBird
    bird_mapping: PanchaPakshiNakshatraBirdMappingResponse
    provenance: PanchaPakshiProvenanceResponse


class PanchaPakshiLocalSolarContextPolicyResponse(_StrictModel):
    policy_id: Literal["local_solar_day_explicit_paksha_v1"]
    paksha_basis: Literal["caller_supplied_source_label"]
    solar_day_basis: Literal["topocentric_sunrise_to_next_sunrise"]
    solar_event_altitude_deg: float
    observer_elevation_m: float
    solar_altitude_refraction_mode: Literal[
        "unrefracted_signal_standard_refraction_and_semidiameter_in_threshold"
    ]
    half_basis: Literal["topocentric_sunrise_sunset"]
    weekday_basis: Literal["local_mean_solar_time_at_governing_sunrise"]
    offset_materialization_status: Literal["not_performed"]


class PanchaPakshiLocalSolarContextResponse(_StrictModel):
    profile_id: str
    requested_jd_ut1: float
    latitude: float
    longitude: float
    sunrise_jd_ut1: float
    sunset_jd_ut1: float
    next_sunrise_jd_ut1: float
    paksha: PanchaPakshiPaksha
    half: PanchaPakshiHalf
    weekday: PanchaPakshiWeekday
    policy: PanchaPakshiLocalSolarContextPolicyResponse
    nominal_schedule: PanchaPakshiNominalScheduleResponse
    provenance: PanchaPakshiProvenanceResponse


class PanchaPakshiFixedClockMaterializationPolicyResponse(_StrictModel):
    policy_id: Literal[
        "fixed_24_minute_nazhigai_from_local_solar_half_start_v1"
    ]
    paksha_basis: Literal["caller_supplied_source_label"]
    solar_context_basis: Literal["topocentric_sunrise_to_next_sunrise"]
    day_anchor: Literal["governing_topocentric_sunrise"]
    night_anchor: Literal["governing_topocentric_sunset"]
    nazhigai_seconds: Literal[1440]
    half_span_nazhigai: Literal[30]
    half_span_seconds: Literal[43200]
    offset_arithmetic_time_scale: Literal["reader_bound_tt"]
    published_endpoint_time_scale: Literal["ut1"]
    interval_ownership: Literal["half_open"]
    solar_end_clipping: Literal["none"]
    topology_metric: Literal["fixed_end_jd_tt_minus_solar_end_jd_tt"]
    topology_coalescence_seconds: float = Field(ge=0.0)
    current_cell_status: Literal["not_performed"]
    solar_proportional_scaling_status: Literal["not_performed"]


class PanchaPakshiFixedClockCellResponse(_StrictModel):
    schedule_cell_index: int = Field(ge=0)
    nominal_cell: PanchaPakshiScheduleCellResponse
    start_jd_tt: float
    end_jd_tt: float
    start_jd_ut1: float
    end_jd_ut1: float
    duration_seconds: PanchaPakshiFractionResponse
    solar_half_relation: PanchaPakshiMaterializedCellRelation


class PanchaPakshiFixedClockMaterializationResponse(_StrictModel):
    local_solar_context: PanchaPakshiLocalSolarContextResponse
    policy: PanchaPakshiFixedClockMaterializationPolicyResponse
    anchor_jd_tt: float
    anchor_jd_ut1: float
    governing_solar_half_end_jd_tt: float
    governing_solar_half_end_jd_ut1: float
    fixed_end_jd_tt: float
    fixed_end_jd_ut1: float
    signed_fixed_end_minus_solar_end_seconds_tt: float
    solar_boundary_relation: PanchaPakshiSolarBoundaryRelation
    cells: list[PanchaPakshiFixedClockCellResponse]
    provenance: PanchaPakshiProvenanceResponse


class PanchaPakshiFixedClockCurrentCellSelectionPolicyResponse(_StrictModel):
    policy_id: Literal[
        "fixed_clock_current_cell_half_open_solar_precedence_v1"
    ]
    materialization_policy_id: Literal[
        "fixed_24_minute_nazhigai_from_local_solar_half_start_v1"
    ]
    paksha_basis: Literal["caller_supplied_source_label"]
    selection_time_scale: Literal["reader_bound_tt"]
    interval_ownership: Literal["half_open"]
    solar_half_precedence: Literal[
        "resolve_governing_solar_half_before_selection"
    ]
    membership_tolerance_seconds: Literal[0.0]
    unmaterialized_solar_half_tail: Literal["explicit_no_current_cell"]
    solar_end_clipping: Literal["none"]
    fixed_span_wrap: Literal["none"]
    fixed_span_repeat: Literal["none"]
    solar_proportional_scaling_status: Literal["not_performed"]
    astronomical_paksha_inference_status: Literal["not_performed"]


class PanchaPakshiFixedClockCurrentCellResponse(_StrictModel):
    """Bounded current-cell result without the full materialized schedule."""

    profile_id: str
    requested_jd_ut1: float
    requested_jd_tt: float
    latitude: float
    longitude: float
    paksha: PanchaPakshiPaksha
    half: PanchaPakshiHalf
    weekday: PanchaPakshiWeekday
    policy: PanchaPakshiFixedClockCurrentCellSelectionPolicyResponse
    anchor_jd_tt: float
    anchor_jd_ut1: float
    governing_solar_half_end_jd_tt: float
    governing_solar_half_end_jd_ut1: float
    fixed_end_jd_tt: float
    fixed_end_jd_ut1: float
    signed_fixed_end_minus_solar_end_seconds_tt: float
    solar_boundary_relation: PanchaPakshiSolarBoundaryRelation
    selection_status: PanchaPakshiCurrentCellSelectionStatus
    current_cell: PanchaPakshiFixedClockCellResponse | None
    provenance: PanchaPakshiProvenanceResponse


class PanchaPakshiSolarProportionalMaterializationPolicyResponse(_StrictModel):
    policy_id: Literal[
        "solar_proportional_nominal_offsets_over_governing_half_tt_v1"
    ]
    paksha_basis: Literal["caller_supplied_source_label"]
    solar_context_basis: Literal["topocentric_sunrise_to_next_sunrise"]
    day_anchor: Literal["governing_topocentric_sunrise"]
    night_anchor: Literal["governing_topocentric_sunset"]
    nominal_offset_basis: Literal["exact_fraction_of_nominal_schedule_span"]
    mapping_time_scale: Literal["reader_bound_tt"]
    published_endpoint_time_scale: Literal["ut1"]
    endpoint_mapping: Literal[
        "independent_anchor_plus_fraction_of_governing_solar_half"
    ]
    endpoint_closure: Literal["exact_anchor_and_governing_solar_half_end"]
    interval_ownership: Literal["half_open"]
    solar_end_clipping: Literal["none"]
    solar_half_wrap: Literal["none"]
    solar_half_repeat: Literal["none"]
    fixed_nazhigai_seconds_status: Literal["not_used"]
    current_cell_status: Literal["not_performed"]
    astronomical_paksha_inference_status: Literal["not_performed"]


class PanchaPakshiSolarProportionalCellResponse(_StrictModel):
    """One cell whose exact fractions refer to the governing solar half."""

    schedule_cell_index: int = Field(ge=0)
    nominal_cell: PanchaPakshiScheduleCellResponse
    start_offset_fraction: PanchaPakshiFractionResponse
    end_offset_fraction: PanchaPakshiFractionResponse
    span_fraction: PanchaPakshiFractionResponse
    start_jd_tt: float
    end_jd_tt: float
    start_jd_ut1: float
    end_jd_ut1: float
    duration_seconds_tt: float = Field(gt=0.0)


class PanchaPakshiSolarProportionalMaterializationResponse(_StrictModel):
    """Full proportional materialization with no current-cell judgment."""

    local_solar_context: PanchaPakshiLocalSolarContextResponse
    policy: PanchaPakshiSolarProportionalMaterializationPolicyResponse
    anchor_jd_tt: float
    anchor_jd_ut1: float
    governing_solar_half_end_jd_tt: float
    governing_solar_half_end_jd_ut1: float
    solar_half_duration_seconds_tt: float = Field(gt=0.0)
    cells: list[PanchaPakshiSolarProportionalCellResponse]
    provenance: PanchaPakshiProvenanceResponse


class PanchaPakshiSolarProportionalCurrentCellSelectionPolicyResponse(
    _StrictModel
):
    policy_id: Literal[
        "solar_proportional_current_cell_half_open_solar_precedence_v1"
    ]
    materialization_policy_id: Literal[
        "solar_proportional_nominal_offsets_over_governing_half_tt_v1"
    ]
    paksha_basis: Literal["caller_supplied_source_label"]
    selection_time_scale: Literal["reader_bound_tt"]
    interval_ownership: Literal["half_open"]
    solar_half_precedence: Literal[
        "resolve_governing_solar_half_before_selection"
    ]
    membership_tolerance_seconds: Literal[0.0]
    coverage_requirement: Literal["complete_governing_solar_half"]
    required_match_count: Literal[1]
    unmaterialized_solar_half_tail_status: Literal["not_applicable"]
    invalid_match_policy: Literal["fail_closed"]
    fixed_clock_mixing_status: Literal["not_performed"]
    astronomical_paksha_inference_status: Literal["not_performed"]


class PanchaPakshiSolarProportionalCurrentCellResponse(_StrictModel):
    """One selected proportional cell without the full materialization."""

    profile_id: str
    requested_jd_ut1: float
    requested_jd_tt: float
    latitude: float
    longitude: float
    paksha: PanchaPakshiPaksha
    half: PanchaPakshiHalf
    weekday: PanchaPakshiWeekday
    policy: PanchaPakshiSolarProportionalCurrentCellSelectionPolicyResponse
    anchor_jd_tt: float
    anchor_jd_ut1: float
    governing_solar_half_end_jd_tt: float
    governing_solar_half_end_jd_ut1: float
    solar_half_duration_seconds_tt: float = Field(gt=0.0)
    selection_status: Literal["selected"]
    current_cell: PanchaPakshiSolarProportionalCellResponse
    provenance: PanchaPakshiProvenanceResponse
