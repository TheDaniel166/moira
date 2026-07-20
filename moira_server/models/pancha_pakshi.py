"""Strict transport contracts for source-scoped Pancha Pakshi products."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import Field, field_validator

from moira.pancha_pakshi import (
    PanchaPakshiActivity,
    PanchaPakshiAdmissionStatus,
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
