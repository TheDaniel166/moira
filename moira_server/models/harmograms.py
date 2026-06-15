"""Transport models for P-GAP-06 harmogram routes."""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


HARMOGRAMS_MAX_POSITIONS = 32
HARMOGRAMS_MAX_RELATIONAL_POSITIONS = 24
HARMOGRAMS_MAX_HARMONIC = 128
HARMOGRAMS_MAX_DOMAIN_WIDTH = 32
HARMOGRAMS_MAX_TRACE_SAMPLES = 64
HARMOGRAMS_MAX_TRACE_CELLS = 256
HARMOGRAMS_MIN_INTENSITY_SAMPLE_COUNT = 256
HARMOGRAMS_MAX_INTENSITY_SAMPLE_COUNT = 8192
HARMOGRAMS_MAX_ORB_WIDTH_DEG = 90.0
HARMOGRAMS_MAX_NAME_LENGTH = 64

HarmogramNormalizationMode = Literal["raw_sum", "mean_resultant"]
HarmogramPairConstructionMode = Literal["ordered", "unordered"]
HarmogramSelfPairMode = Literal["include", "exclude"]
HarmogramIntensityFamilyName = Literal[
    "cosine_bell_harmonic_aspects",
    "top_hat_harmonic_aspects",
    "triangular_harmonic_aspects",
    "gaussian_harmonic_aspects",
]
HarmogramGaussianWidthModeName = Literal["sigma", "fwhm"]
HarmogramTraceFamilyName = Literal[
    "dynamic_zero_aries_parts",
    "transit_to_natal_zero_aries_parts",
    "directed_to_natal_zero_aries_parts",
    "progressed_to_natal_zero_aries_parts",
]
HarmogramOutputModeName = Literal["single_harmonic", "multi_harmonic_family"]


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _finite(value: float, field_name: str) -> float:
    if not math.isfinite(value):
        raise ValueError(f"{field_name} must be finite")
    return value


def _clean_positions(
    positions: list["HarmogramPositionRequest"],
    *,
    max_count: int,
    field_name: str,
) -> list["HarmogramPositionRequest"]:
    if not positions:
        raise ValueError(f"{field_name} must contain at least one position")
    if len(positions) > max_count:
        raise ValueError(f"{field_name} may contain at most {max_count} positions")
    seen: set[str] = set()
    cleaned: list[HarmogramPositionRequest] = []
    for position in positions:
        name = position.name.strip()
        if name in seen:
            raise ValueError(f"{field_name} names must be unique after trimming")
        seen.add(name)
        cleaned.append(HarmogramPositionRequest(name=name, degree=position.degree))
    return cleaned


def _clean_harmonic_numbers(values: list[int]) -> list[int]:
    if not values:
        raise ValueError("harmonic_numbers must contain at least one harmonic")
    if len(values) > HARMOGRAMS_MAX_DOMAIN_WIDTH:
        raise ValueError(
            f"harmonic_numbers may contain at most {HARMOGRAMS_MAX_DOMAIN_WIDTH} harmonics"
        )
    if len(set(values)) != len(values):
        raise ValueError("harmonic_numbers must be unique")
    return values


class HarmogramPositionRequest(_StrictModel):
    name: str = Field(min_length=1, max_length=HARMOGRAMS_MAX_NAME_LENGTH)
    degree: float

    @field_validator("name")
    @classmethod
    def _valid_name(cls, value: str) -> str:
        name = value.strip()
        if not name:
            raise ValueError("position names must be non-empty")
        return name

    @field_validator("degree")
    @classmethod
    def _valid_degree(cls, value: float) -> float:
        return _finite(value, "degree")


class HarmogramHarmonicDomainRequest(_StrictModel):
    harmonic_start: int = Field(default=1, ge=1, le=HARMOGRAMS_MAX_HARMONIC)
    harmonic_stop: int = Field(default=12, ge=1, le=HARMOGRAMS_MAX_HARMONIC)

    @model_validator(mode="after")
    def _valid_domain(self) -> "HarmogramHarmonicDomainRequest":
        if self.harmonic_stop < self.harmonic_start:
            raise ValueError("harmonic_stop must be greater than or equal to harmonic_start")
        width = self.harmonic_stop - self.harmonic_start + 1
        if width > HARMOGRAMS_MAX_DOMAIN_WIDTH:
            raise ValueError(
                f"harmonic domains may contain at most {HARMOGRAMS_MAX_DOMAIN_WIDTH} harmonics"
            )
        return self


class HarmogramVectorPolicyRequest(_StrictModel):
    normalization_mode: HarmogramNormalizationMode = "mean_resultant"
    harmonic_domain: HarmogramHarmonicDomainRequest = Field(
        default_factory=HarmogramHarmonicDomainRequest
    )


class HarmogramPartsPolicyRequest(_StrictModel):
    pair_construction_mode: HarmogramPairConstructionMode = "ordered"
    self_pair_mode: HarmogramSelfPairMode = "include"


class HarmogramIntensityPolicyRequest(_StrictModel):
    family: HarmogramIntensityFamilyName = "cosine_bell_harmonic_aspects"
    include_conjunction: bool = True
    harmonic_domain: HarmogramHarmonicDomainRequest = Field(
        default_factory=HarmogramHarmonicDomainRequest
    )
    orb_width_deg: float = Field(default=24.0, gt=0.0, le=HARMOGRAMS_MAX_ORB_WIDTH_DEG)
    gaussian_width_parameter_mode: HarmogramGaussianWidthModeName = "fwhm"
    gaussian_width_deg: float | None = Field(default=None, gt=0.0, le=HARMOGRAMS_MAX_ORB_WIDTH_DEG)
    sample_count: int = Field(
        default=4096,
        ge=HARMOGRAMS_MIN_INTENSITY_SAMPLE_COUNT,
        le=HARMOGRAMS_MAX_INTENSITY_SAMPLE_COUNT,
    )

    @field_validator("orb_width_deg", "gaussian_width_deg")
    @classmethod
    def _valid_float(cls, value: float | None) -> float | None:
        if value is None:
            return value
        return _finite(value, "intensity policy numeric values")

    @model_validator(mode="after")
    def _valid_gaussian_policy(self) -> "HarmogramIntensityPolicyRequest":
        is_gaussian = self.family == "gaussian_harmonic_aspects"
        if is_gaussian and self.gaussian_width_deg is None:
            raise ValueError("gaussian intensity families require gaussian_width_deg")
        if not is_gaussian and self.gaussian_width_deg is not None:
            raise ValueError("gaussian_width_deg is only valid for gaussian intensity families")
        return self


class HarmogramVectorRequest(_StrictModel):
    positions: list[HarmogramPositionRequest]
    policy: HarmogramVectorPolicyRequest = Field(default_factory=HarmogramVectorPolicyRequest)

    @field_validator("positions")
    @classmethod
    def _valid_positions(
        cls,
        value: list[HarmogramPositionRequest],
    ) -> list[HarmogramPositionRequest]:
        return _clean_positions(value, max_count=HARMOGRAMS_MAX_POSITIONS, field_name="positions")


class HarmogramZeroAriesVectorRequest(_StrictModel):
    positions: list[HarmogramPositionRequest] | None = None
    source_positions: list[HarmogramPositionRequest] | None = None
    target_positions: list[HarmogramPositionRequest] | None = None
    parts_policy: HarmogramPartsPolicyRequest = Field(default_factory=HarmogramPartsPolicyRequest)
    vector_policy: HarmogramVectorPolicyRequest = Field(default_factory=HarmogramVectorPolicyRequest)

    @field_validator("positions", "source_positions", "target_positions")
    @classmethod
    def _valid_position_sets(
        cls,
        value: list[HarmogramPositionRequest] | None,
    ) -> list[HarmogramPositionRequest] | None:
        if value is None:
            return value
        return _clean_positions(
            value,
            max_count=HARMOGRAMS_MAX_RELATIONAL_POSITIONS,
            field_name="position sets",
        )

    @model_validator(mode="after")
    def _valid_position_mode(self) -> "HarmogramZeroAriesVectorRequest":
        has_single = self.positions is not None
        has_relational = self.source_positions is not None or self.target_positions is not None
        if has_single and has_relational:
            raise ValueError("pass either positions or source_positions/target_positions, not both")
        if not has_single and (self.source_positions is None or self.target_positions is None):
            raise ValueError("source_positions and target_positions are required without positions")
        return self


class HarmogramIntensitySpectrumRequest(_StrictModel):
    harmonic_number: int = Field(ge=1, le=HARMOGRAMS_MAX_HARMONIC)
    policy: HarmogramIntensityPolicyRequest = Field(default_factory=HarmogramIntensityPolicyRequest)


class HarmogramProjectionRequest(HarmogramZeroAriesVectorRequest):
    harmonic_number: int = Field(ge=1, le=HARMOGRAMS_MAX_HARMONIC)
    intensity_policy: HarmogramIntensityPolicyRequest | None = None


class HarmogramTraceSampleRequest(_StrictModel):
    time: float
    positions: list[HarmogramPositionRequest] | None = None
    transit_positions: list[HarmogramPositionRequest] | None = None
    directed_positions: list[HarmogramPositionRequest] | None = None
    progressed_positions: list[HarmogramPositionRequest] | None = None
    natal_positions: list[HarmogramPositionRequest] | None = None

    @field_validator("time")
    @classmethod
    def _valid_time(cls, value: float) -> float:
        return _finite(value, "time")

    @field_validator(
        "positions",
        "transit_positions",
        "directed_positions",
        "progressed_positions",
        "natal_positions",
    )
    @classmethod
    def _valid_positions(
        cls,
        value: list[HarmogramPositionRequest] | None,
    ) -> list[HarmogramPositionRequest] | None:
        if value is None:
            return value
        return _clean_positions(
            value,
            max_count=HARMOGRAMS_MAX_RELATIONAL_POSITIONS,
            field_name="trace position sets",
        )


class HarmogramTraceRequest(_StrictModel):
    samples: list[HarmogramTraceSampleRequest]
    harmonic_numbers: list[int] = Field(default_factory=lambda: [1])
    trace_family: HarmogramTraceFamilyName = "dynamic_zero_aries_parts"
    output_mode: HarmogramOutputModeName = "multi_harmonic_family"
    point_set_policy: HarmogramVectorPolicyRequest = Field(default_factory=HarmogramVectorPolicyRequest)
    parts_policy: HarmogramPartsPolicyRequest = Field(default_factory=HarmogramPartsPolicyRequest)
    intensity_policy: HarmogramIntensityPolicyRequest = Field(default_factory=HarmogramIntensityPolicyRequest)

    @field_validator("samples")
    @classmethod
    def _valid_samples(
        cls,
        value: list[HarmogramTraceSampleRequest],
    ) -> list[HarmogramTraceSampleRequest]:
        if not value:
            raise ValueError("samples must contain at least one sample")
        if len(value) > HARMOGRAMS_MAX_TRACE_SAMPLES:
            raise ValueError(f"samples may contain at most {HARMOGRAMS_MAX_TRACE_SAMPLES} items")
        previous_time: float | None = None
        for sample in value:
            if previous_time is not None and sample.time <= previous_time:
                raise ValueError("samples must be strictly increasing by time")
            previous_time = sample.time
        return value

    @field_validator("harmonic_numbers")
    @classmethod
    def _valid_harmonic_numbers(cls, value: list[int]) -> list[int]:
        return _clean_harmonic_numbers(value)

    @model_validator(mode="after")
    def _valid_trace_request(self) -> "HarmogramTraceRequest":
        if self.output_mode == "single_harmonic" and len(self.harmonic_numbers) != 1:
            raise ValueError("single_harmonic output requires exactly one harmonic_number")
        if len(self.samples) * len(self.harmonic_numbers) > HARMOGRAMS_MAX_TRACE_CELLS:
            raise ValueError(
                f"trace sample x harmonic count may not exceed {HARMOGRAMS_MAX_TRACE_CELLS}"
            )
        if self.point_set_policy.harmonic_domain != self.intensity_policy.harmonic_domain:
            raise ValueError("point_set_policy and intensity_policy must share the same harmonic_domain")

        for sample in self.samples:
            if self.trace_family == "dynamic_zero_aries_parts":
                if sample.positions is None:
                    raise ValueError("dynamic traces require positions on every sample")
            elif self.trace_family == "transit_to_natal_zero_aries_parts":
                if sample.transit_positions is None or sample.natal_positions is None:
                    raise ValueError("transit-to-natal traces require transit_positions and natal_positions")
            elif self.trace_family == "directed_to_natal_zero_aries_parts":
                if sample.directed_positions is None or sample.natal_positions is None:
                    raise ValueError("directed-to-natal traces require directed_positions and natal_positions")
            elif self.trace_family == "progressed_to_natal_zero_aries_parts":
                if sample.progressed_positions is None or sample.natal_positions is None:
                    raise ValueError("progressed-to-natal traces require progressed_positions and natal_positions")
        return self


class HarmogramBoundsResponse(_StrictModel):
    max_positions: int = HARMOGRAMS_MAX_POSITIONS
    max_relational_positions: int = HARMOGRAMS_MAX_RELATIONAL_POSITIONS
    max_harmonic: int = HARMOGRAMS_MAX_HARMONIC
    max_domain_width: int = HARMOGRAMS_MAX_DOMAIN_WIDTH
    max_trace_samples: int = HARMOGRAMS_MAX_TRACE_SAMPLES
    max_trace_cells: int = HARMOGRAMS_MAX_TRACE_CELLS
    min_intensity_sample_count: int = HARMOGRAMS_MIN_INTENSITY_SAMPLE_COUNT
    max_intensity_sample_count: int = HARMOGRAMS_MAX_INTENSITY_SAMPLE_COUNT
    max_orb_width_deg: float = HARMOGRAMS_MAX_ORB_WIDTH_DEG


class HarmogramProvenanceResponse(_StrictModel):
    source_module: str = "moira.harmograms"
    engine_entrypoint: str
    input_position_owner: str = "caller_supplied"
    chart_sampling_owner: str = "not_this_route"
    interpretation_owner: str = "not_returned"
    output_bound_policy: str = "bounded_transport_serialization"
    stage_sequence: list[str]
    bounds: HarmogramBoundsResponse = Field(default_factory=HarmogramBoundsResponse)


class HarmogramHarmonicDomainResponse(_StrictModel):
    harmonic_start: int
    harmonic_stop: int
    harmonics: list[int]


class HarmogramVectorPolicyResponse(_StrictModel):
    normalization_mode: str
    harmonic_domain: HarmogramHarmonicDomainResponse


class HarmogramPartsPolicyResponse(_StrictModel):
    pair_construction_mode: str
    self_pair_mode: str


class HarmogramIntensityPolicyResponse(_StrictModel):
    family: str
    include_conjunction: bool
    orb_mode: str
    orb_scaling_mode: str
    symmetry_mode: str
    normalization_mode: str
    harmonic_domain: HarmogramHarmonicDomainResponse
    orb_width_deg: float
    gaussian_width_parameter_mode: str
    gaussian_width_deg: float | None
    sample_count: int


class HarmogramComponentResponse(_StrictModel):
    harmonic: int
    amplitude: float
    phase_deg: float


class HarmogramSourceVectorResponse(_StrictModel):
    source_kind: Literal["point_set", "zero_aries_parts"]
    vector_policy: HarmogramVectorPolicyResponse
    body_names: list[str] | None = None
    point_count: int | None = None
    parts_policy: HarmogramPartsPolicyResponse | None = None
    source_body_names: list[str] | None = None
    target_body_names: list[str] | None = None
    parts_count: int | None = None
    harmonic_zero_amplitude: float
    components: list[HarmogramComponentResponse]


class HarmogramIntensitySpectrumResponse(_StrictModel):
    harmonic_number: int
    policy: HarmogramIntensityPolicyResponse
    realization_mode: str
    harmonic_zero_amplitude: float
    components: list[HarmogramComponentResponse]


class HarmogramProjectionTermResponse(_StrictModel):
    harmonic: int
    source_amplitude: float
    source_phase_deg: float
    intensity_amplitude: float
    intensity_phase_deg: float
    signed_contribution: float


class HarmogramProjectionDetailResponse(_StrictModel):
    normalization_mode: str
    realization_mode: str
    harmonic_zero_contribution: float
    total_strength: float
    terms: list[HarmogramProjectionTermResponse]


class HarmogramVectorEnvelopeResponse(_StrictModel):
    vector: HarmogramSourceVectorResponse
    provenance: HarmogramProvenanceResponse


class HarmogramIntensitySpectrumEnvelopeResponse(_StrictModel):
    spectrum: HarmogramIntensitySpectrumResponse
    provenance: HarmogramProvenanceResponse


class HarmogramProjectionEnvelopeResponse(_StrictModel):
    source_vector: HarmogramSourceVectorResponse
    intensity_spectrum: HarmogramIntensitySpectrumResponse
    projection: HarmogramProjectionDetailResponse
    provenance: HarmogramProvenanceResponse


class HarmogramTraceSampleResponse(_StrictModel):
    sample_index: int
    sample_time: float
    source_vector: HarmogramSourceVectorResponse
    projection: HarmogramProjectionDetailResponse
    total_strength: float


class HarmogramTraceSeriesResponse(_StrictModel):
    harmonic_number: int
    intensity_spectrum: HarmogramIntensitySpectrumResponse
    samples: list[HarmogramTraceSampleResponse]
    strengths: list[float]


class HarmogramTracePolicyResponse(_StrictModel):
    trace_family: str
    output_mode: str
    chart_domain: str
    point_set_policy: HarmogramVectorPolicyResponse
    parts_policy: HarmogramPartsPolicyResponse
    intensity_policy: HarmogramIntensityPolicyResponse
    sample_count: int


class HarmogramTraceEnvelopeResponse(_StrictModel):
    policy: HarmogramTracePolicyResponse
    interval_start: float
    interval_stop: float
    sample_times: list[float]
    series: list[HarmogramTraceSeriesResponse]
    series_count: int
    provenance: HarmogramProvenanceResponse
