"""Strict transport models for the neutral Mundane event-chart profile."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Annotated, Literal

from pydantic import Field, RootModel, field_validator, model_validator

from moira.mundane import (
    CardinalIngress,
    CardinalIngressSelectionPolicy,
    EclipseAnchorEpoch,
    EclipseContactKind,
    EclipseKind,
    JupiterSaturnConjunctionDefinition,
    MundaneEvaluationStatus,
    MundaneLocationRole,
    MundaneLongitudeDefinition,
    MundaneMotionState,
    MundaneNotEvaluableReason,
    MundaneProfileComponent,
    MundaneProfileExclusion,
    MundaneProvenanceMode,
    MundaneTimescale,
    MundaneUtcRealizationStatus,
    MundaneZodiacModality,
    PrimarySyzygyPhase,
)

from .chart import HousePolicyResponse, HousesResponse
from .common import _StrictModel


MundaneHouseSystemCode = Literal[
    "P", "K", "E", "W", "C", "R", "O", "X", "B", "M", "T", "V",
    "N", "S", "H", "CT", "U", "Y", "Z", "EM", "PSD", "PSR",
]


class MundaneLocationRequest(_StrictModel):
    """Caller-owned location identity; it is never engine provenance."""

    label: str = Field(min_length=1, max_length=255)
    role: MundaneLocationRole
    source_id: str = Field(min_length=1, max_length=1_000)
    valid_from_utc: datetime | None
    valid_until_utc: datetime | None
    latitude_deg: float = Field(strict=True, ge=-90.0, le=90.0)
    longitude_deg_east: float = Field(strict=True, ge=-180.0, le=180.0)

    @field_validator("label", "source_id")
    @classmethod
    def _trimmed_text(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("Mundane location text must be trimmed")
        return value

    @field_validator("valid_from_utc", "valid_until_utc")
    @classmethod
    def _aware_validity(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("Mundane location validity instants must be timezone-aware")
        return value

    @field_validator("latitude_deg", "longitude_deg_east")
    @classmethod
    def _finite_coordinate(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("Mundane location coordinates must be finite")
        return value

    @model_validator(mode="after")
    def _validity_interval(self) -> "MundaneLocationRequest":
        institutional = {
            MundaneLocationRole.SEAT_OF_GOVERNMENT,
            MundaneLocationRole.CONSTITUTIONAL_CAPITAL,
            MundaneLocationRole.ADMINISTRATIVE_CAPITAL,
            MundaneLocationRole.REGIONAL_CENTER,
        }
        if self.role in institutional and self.valid_from_utc is None:
            raise ValueError("Institutional location roles require valid_from_utc")
        if self.valid_from_utc is None and self.valid_until_utc is not None:
            raise ValueError("valid_until_utc requires valid_from_utc")
        if (
            self.valid_from_utc is not None
            and self.valid_until_utc is not None
            and self.valid_until_utc <= self.valid_from_utc
        ):
            raise ValueError("Mundane location validity interval must be non-empty")
        return self


class _MundaneEventRequest(_StrictModel):
    search_start_utc: datetime
    search_end_utc: datetime
    location: MundaneLocationRequest
    house_system: MundaneHouseSystemCode

    @field_validator("search_start_utc", "search_end_utc")
    @classmethod
    def _aware_search_instant(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Mundane search instants must be timezone-aware")
        return value

    @model_validator(mode="after")
    def _ordered_search(self) -> "_MundaneEventRequest":
        if self.search_end_utc <= self.search_start_utc:
            raise ValueError("Mundane search interval must be non-empty")
        return self

    def _require_maximum_span(self, days: float, label: str) -> None:
        span_days = (self.search_end_utc - self.search_start_utc).total_seconds() / 86400.0
        if span_days > days:
            raise ValueError(f"{label} search interval is limited to {days:g} days")


class CardinalIngressProfileRequest(_MundaneEventRequest):
    event_type: Literal["cardinal_ingress"]
    selected_ingress: CardinalIngress
    selection_policy: CardinalIngressSelectionPolicy

    @model_validator(mode="after")
    def _one_cycle(self) -> "CardinalIngressProfileRequest":
        self._require_maximum_span(370.0, "Cardinal ingress")
        return self


class PrimarySyzygyProfileRequest(_MundaneEventRequest):
    event_type: Literal["primary_syzygy"]
    anchor_ingress: CardinalIngress

    @model_validator(mode="after")
    def _one_cycle(self) -> "PrimarySyzygyProfileRequest":
        self._require_maximum_span(370.0, "Primary syzygy anchor")
        return self


class EclipseProfileRequest(_MundaneEventRequest):
    event_type: Literal["eclipse"]
    eclipse_id: str = Field(min_length=1, max_length=255)
    eclipse_kind: EclipseKind
    chart_epoch_kind: EclipseAnchorEpoch

    @field_validator("eclipse_id")
    @classmethod
    def _trimmed_eclipse_id(cls, value: str) -> str:
        if value != value.strip():
            raise ValueError("eclipse_id must be trimmed")
        return value

    @model_validator(mode="after")
    def _bounded_eclipse_search(self) -> "EclipseProfileRequest":
        self._require_maximum_span(400.0, "Eclipse")
        return self


class JupiterSaturnProfileRequest(_MundaneEventRequest):
    event_type: Literal["jupiter_saturn_ecliptic_longitude_conjunction"]
    selected_root_index: int = Field(strict=True, ge=0)

    @model_validator(mode="after")
    def _bounded_conjunction_search(self) -> "JupiterSaturnProfileRequest":
        self._require_maximum_span(36_525.0, "Jupiter-Saturn")
        return self


MundaneEventProfileRequest = Annotated[
    CardinalIngressProfileRequest
    | PrimarySyzygyProfileRequest
    | EclipseProfileRequest
    | JupiterSaturnProfileRequest,
    Field(discriminator="event_type"),
]


class MundaneEventChartProfileRequest(RootModel[MundaneEventProfileRequest]):
    """Named discriminated request root for one admitted event family."""


class VerifiedReaderIdentityResponse(_StrictModel):
    summary_label: str
    planetary_ephemeris: str | None
    lunar_ephemeris: str | None
    verification_basis: Literal["spk_summary_label_content"]


class MundaneEpochResponse(_StrictModel):
    jd: float
    timescale: MundaneTimescale


class MundaneSearchIntervalResponse(_StrictModel):
    start: MundaneEpochResponse
    end: MundaneEpochResponse


class MundaneRootSearchResponse(_StrictModel):
    search_interval: MundaneSearchIntervalResponse
    bracket_start: MundaneEpochResponse
    bracket_end: MundaneEpochResponse
    root_epoch: MundaneEpochResponse
    step_days: float
    solver_tolerance_days: float
    target_angle_deg: float
    root_residual_deg: float
    bracket_start_residual_deg: float
    bracket_end_residual_deg: float
    search_kind: str
    solver_method_id: str
    verified_reader_identity: VerifiedReaderIdentityResponse


class MundaneEventClockResponse(_StrictModel):
    ut1: MundaneEpochResponse
    tt: MundaneEpochResponse
    delta_t_seconds: float
    delta_t_source_product: str
    delta_t_retarget_mode: str
    delta_t_correction_seconds: float
    delta_t_tidal_source_products: tuple[str, ...]
    delta_t_target_reader_identity: str | None
    utc: MundaneEpochResponse | None
    utc_realization_status: MundaneUtcRealizationStatus
    utc_realization_detail: str
    verified_reader_identity: VerifiedReaderIdentityResponse


class MundaneAngularRootToleranceResponse(_StrictModel):
    maximum_abs_residual_deg: float
    basis: str


class MundaneEventProvenanceResponse(_StrictModel):
    mode: MundaneProvenanceMode
    source_id: str
    method_id: str
    provenance_family_id: str
    longitude_product_id: str
    reference_frame: str
    correction_regime: str
    solver_semantics: str
    source_refs: tuple[str, ...]
    verified_reader_identity: VerifiedReaderIdentityResponse | None
    caller_asserted_artifact_id: str | None
    caller_asserted_artifact_sha256: str | None


class MundaneNotEvaluableResponse(_StrictModel):
    component: MundaneProfileComponent
    reason: MundaneNotEvaluableReason
    missing_inputs: tuple[str, ...]
    detail: str


class CardinalIngressReceiptResponse(_StrictModel):
    event_type: Literal["cardinal_ingress"]
    ingress: CardinalIngress
    epoch: MundaneEpochResponse
    sun_longitude_deg: float
    root_residual_deg: float
    solver_tolerance_days: float
    angular_root_tolerance: MundaneAngularRootToleranceResponse
    provenance: MundaneEventProvenanceResponse
    clock: MundaneEventClockResponse | None
    search_truth: MundaneRootSearchResponse | None
    longitude_definition: MundaneLongitudeDefinition
    root_direction: Literal["increasing"]


class PrimarySyzygyReceiptResponse(_StrictModel):
    event_type: Literal["primary_syzygy"]
    phase: PrimarySyzygyPhase
    epoch: MundaneEpochResponse
    sun_longitude_deg: float
    moon_longitude_deg: float
    root_residual_deg: float
    solver_tolerance_days: float
    angular_root_tolerance: MundaneAngularRootToleranceResponse
    provenance: MundaneEventProvenanceResponse
    clock: MundaneEventClockResponse | None
    search_truth: MundaneRootSearchResponse | None
    longitude_definition: MundaneLongitudeDefinition


class EclipseNamedEpochResponse(_StrictModel):
    eclipse_id: str
    eclipse_kind: EclipseKind
    epoch_kind: EclipseAnchorEpoch
    epoch: MundaneEpochResponse
    provenance: MundaneEventProvenanceResponse


class EclipseContactEpochResponse(_StrictModel):
    eclipse_id: str
    eclipse_kind: EclipseKind
    contact: EclipseContactKind
    epoch: MundaneEpochResponse
    provenance: MundaneEventProvenanceResponse


class EclipseEventReceiptResponse(_StrictModel):
    event_type: Literal["eclipse"]
    eclipse_id: str
    eclipse_kind: EclipseKind
    anchor_epoch_kind: EclipseAnchorEpoch
    provenance: MundaneEventProvenanceResponse
    named_epochs: tuple[EclipseNamedEpochResponse, ...]
    global_contacts: tuple[EclipseContactEpochResponse, ...]
    clock: MundaneEventClockResponse | None


class JupiterSaturnConjunctionReceiptResponse(_StrictModel):
    event_type: Literal["jupiter_saturn_ecliptic_longitude_conjunction"]
    event_id: str
    epoch: MundaneEpochResponse
    jupiter_longitude_deg: float
    saturn_longitude_deg: float
    root_residual_deg: float
    jupiter_motion: MundaneMotionState
    saturn_motion: MundaneMotionState
    solver_tolerance_days: float
    angular_root_tolerance: MundaneAngularRootToleranceResponse
    provenance: MundaneEventProvenanceResponse
    clock: MundaneEventClockResponse | None
    definition: JupiterSaturnConjunctionDefinition
    longitude_definition: MundaneLongitudeDefinition


MundaneEventReceiptResponse = Annotated[
    CardinalIngressReceiptResponse
    | PrimarySyzygyReceiptResponse
    | EclipseEventReceiptResponse
    | JupiterSaturnConjunctionReceiptResponse,
    Field(discriminator="event_type"),
]


class MundaneAscendantResponse(_StrictModel):
    aries_ingress: CardinalIngressReceiptResponse
    location: "MundaneLocationResponse"
    clock: MundaneEventClockResponse
    ascendant_longitude_deg: float
    ascendant_sign: str
    ascendant_modality: MundaneZodiacModality
    local_angle_method_id: str


class RameseyIngressCadenceResponse(_StrictModel):
    aries_ingress: CardinalIngressReceiptResponse
    ascendant: MundaneAscendantResponse
    selected_ingresses: tuple[CardinalIngress, ...]
    chart_count: int
    policy: CardinalIngressSelectionPolicy
    source_reference: str


class CardinalIngressSelectionReceiptResponse(_StrictModel):
    policy: CardinalIngressSelectionPolicy
    search_interval: MundaneSearchIntervalResponse
    all_events: tuple[CardinalIngressReceiptResponse, ...]
    selected_events: tuple[CardinalIngressReceiptResponse, ...]
    source_reference: str
    ramesey_cadence: RameseyIngressCadenceResponse | None


class CardinalIngressSelectionEvidenceResponse(_StrictModel):
    status: MundaneEvaluationStatus
    selection: CardinalIngressSelectionReceiptResponse | None
    issue: MundaneNotEvaluableResponse | None


class PrecedingSyzygySelectionReceiptResponse(_StrictModel):
    anchor_event: CardinalIngressReceiptResponse
    candidates: tuple[PrimarySyzygyReceiptResponse, ...]
    selected: PrimarySyzygyReceiptResponse
    comparison_timescale: MundaneTimescale
    policy_id: str


class PrecedingSyzygyEvidenceResponse(_StrictModel):
    status: MundaneEvaluationStatus
    selection: PrecedingSyzygySelectionReceiptResponse | None
    issue: MundaneNotEvaluableResponse | None


class JupiterSaturnSequenceResponse(_StrictModel):
    search_interval: MundaneSearchIntervalResponse
    roots: tuple[JupiterSaturnConjunctionReceiptResponse, ...]


class MundaneLocationResponse(_StrictModel):
    label: str
    latitude_deg: float
    longitude_deg_east: float
    role: MundaneLocationRole
    source_id: str
    valid_from: MundaneEpochResponse | None
    valid_until: MundaneEpochResponse | None


class MundaneHouseComputationResponse(_StrictModel):
    event_epoch: MundaneEpochResponse
    location: MundaneLocationResponse
    requested_house_system: MundaneHouseSystemCode
    policy: HousePolicyResponse
    houses: HousesResponse
    calculator_id: str


class MundaneLocalProjectionReceiptResponse(_StrictModel):
    anchor_event: MundaneEventReceiptResponse
    house_computation: MundaneHouseComputationResponse
    chart_epoch_kind: EclipseAnchorEpoch | None


class MundaneEventEvidenceResponse(_StrictModel):
    status: MundaneEvaluationStatus
    receipt: MundaneEventReceiptResponse | None
    issue: MundaneNotEvaluableResponse | None


class MundaneLocalProjectionEvidenceResponse(_StrictModel):
    status: MundaneEvaluationStatus
    receipt: MundaneLocalProjectionReceiptResponse | None
    issue: MundaneNotEvaluableResponse | None


class MundaneProfileProvenanceResponse(_StrictModel):
    source_refs: tuple[str, ...]
    engine_version: str | None
    method_id: str
    derivation: str


class MundaneProfileResponse(_StrictModel):
    status: MundaneEvaluationStatus
    anchor_event: MundaneEventEvidenceResponse
    cardinal_ingress_selection: CardinalIngressSelectionEvidenceResponse
    preceding_syzygy: PrecedingSyzygyEvidenceResponse
    local_projection: MundaneLocalProjectionEvidenceResponse
    provenance: MundaneProfileProvenanceResponse
    not_evaluable: tuple[MundaneNotEvaluableResponse, ...]
    included_components: tuple[MundaneProfileComponent, ...]
    excluded_components: tuple[MundaneProfileExclusion, ...]


class CardinalIngressSelectionContextResponse(_StrictModel):
    event_type: Literal["cardinal_ingress"]
    explicit_selected_ingress: CardinalIngress
    selection: CardinalIngressSelectionReceiptResponse


class PrimarySyzygySelectionContextResponse(_StrictModel):
    event_type: Literal["primary_syzygy"]
    anchor_ingress: CardinalIngress
    selection: PrecedingSyzygySelectionReceiptResponse


class EclipseSelectionContextResponse(_StrictModel):
    event_type: Literal["eclipse"]
    eclipse_kind: EclipseKind
    chart_epoch_kind: EclipseAnchorEpoch
    event: EclipseEventReceiptResponse


class JupiterSaturnSelectionContextResponse(_StrictModel):
    event_type: Literal["jupiter_saturn_ecliptic_longitude_conjunction"]
    selected_root_index: int = Field(ge=0)
    sequence: JupiterSaturnSequenceResponse


MundaneSelectionContextResponse = Annotated[
    CardinalIngressSelectionContextResponse
    | PrimarySyzygySelectionContextResponse
    | EclipseSelectionContextResponse
    | JupiterSaturnSelectionContextResponse,
    Field(discriminator="event_type"),
]


class MundaneEventChartProfileResponse(_StrictModel):
    selection: MundaneSelectionContextResponse
    profile: MundaneProfileResponse


__all__ = [
    "CardinalIngressProfileRequest",
    "EclipseProfileRequest",
    "JupiterSaturnProfileRequest",
    "MundaneEventChartProfileRequest",
    "MundaneEventChartProfileResponse",
    "PrimarySyzygyProfileRequest",
]
