"""Transport models for P12-02 harmonic projection routes."""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


HARMONICS_MAX_BODIES = 64
HARMONICS_MAX_COMPOSITE_BODIES = 32
HARMONICS_MAX_HARMONIC = 128
HARMONICS_DEFAULT_MAX_HARMONIC = 32
HARMONICS_MAX_ORB = 30.0
HARMONICS_MAX_LABEL_LENGTH = 64
HARMONICS_MAX_FORECAST_BODIES_PER_ORIGIN = 12
HARMONICS_MAX_FORECAST_SAMPLES = 512
HARMONICS_MAX_FORECAST_HARMONICS = 16
HARMONICS_MAX_FORECAST_WORK_UNITS = 25_000


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _clean_longitudes(value: dict[str, float]) -> dict[str, float]:
    if not value:
        raise ValueError("longitudes must contain at least one body")
    if len(value) > HARMONICS_MAX_BODIES:
        raise ValueError(f"longitudes may contain at most {HARMONICS_MAX_BODIES} bodies")

    cleaned: dict[str, float] = {}
    for raw_name, longitude in value.items():
        name = str(raw_name).strip()
        if not name:
            raise ValueError("longitude body names must be non-empty")
        if name in cleaned:
            raise ValueError("longitude body names must be unique after trimming")
        if not math.isfinite(longitude):
            raise ValueError("longitudes must be finite")
        cleaned[name] = longitude
    return cleaned


def _require_real_number(value: object, *, field_name: str) -> object:
    """Reject coercive JSON scalars before Pydantic converts them to floats."""

    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field_name} must be a real number")
    return value


def _require_raw_longitude_mapping(
    value: object,
    *,
    field_name: str,
) -> object:
    """Reject coercive forecast-longitude scalars before Pydantic conversion."""

    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be an object of real-number longitudes")
    for body, longitude in value.items():
        if not isinstance(body, str):
            raise ValueError(f"{field_name} body names must be strings")
        if isinstance(longitude, bool) or not isinstance(longitude, (int, float)):
            raise ValueError(f"{field_name} values must be real numbers")
        try:
            finite = math.isfinite(longitude)
        except OverflowError:
            finite = False
        if not finite:
            raise ValueError(f"{field_name} values must be finite")
    return value


class HarmonicOrbPolicyRequest(_StrictModel):
    """Explicitly select the admitted source-circle orb scaling doctrine."""

    scaling_mode: Literal["addey_inverse_harmonic"] = "addey_inverse_harmonic"


class HarmonicChartRequest(_StrictModel):
    longitudes: dict[str, float]
    harmonic: float = Field(ge=1.0, le=float(HARMONICS_MAX_HARMONIC))

    @field_validator("longitudes", mode="before")
    @classmethod
    def _numeric_longitudes(cls, value: object) -> object:
        return _require_raw_longitude_mapping(value, field_name="longitudes")

    @field_validator("longitudes")
    @classmethod
    def _valid_longitudes(cls, value: dict[str, float]) -> dict[str, float]:
        return _clean_longitudes(value)

    @field_validator("harmonic", mode="before")
    @classmethod
    def _numeric_harmonic(cls, value: object) -> object:
        return _require_real_number(value, field_name="harmonic")

    @field_validator("harmonic")
    @classmethod
    def _finite_harmonic(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("harmonic must be finite")
        return value


class HarmonicAgeChartRequest(_StrictModel):
    longitudes: dict[str, float]
    jd_birth: float
    jd_now: float

    @field_validator("longitudes", mode="before")
    @classmethod
    def _numeric_longitudes(cls, value: object) -> object:
        return _require_raw_longitude_mapping(value, field_name="longitudes")

    @field_validator("longitudes")
    @classmethod
    def _valid_longitudes(cls, value: dict[str, float]) -> dict[str, float]:
        return _clean_longitudes(value)

    @field_validator("jd_birth", "jd_now")
    @classmethod
    def _finite_jd(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("Julian Day values must be finite")
        return value

    @model_validator(mode="after")
    def _valid_age_window(self) -> "HarmonicAgeChartRequest":
        if self.jd_now < self.jd_birth:
            raise ValueError("jd_now must be greater than or equal to jd_birth")
        return self


class HarmonicConjunctionRequest(HarmonicChartRequest):
    orb: float = Field(default=1.0, ge=0.0, le=HARMONICS_MAX_ORB)
    orb_policy: HarmonicOrbPolicyRequest | None = None

    @field_validator("orb", mode="before")
    @classmethod
    def _numeric_orb(cls, value: object) -> object:
        return _require_real_number(value, field_name="orb")

    @field_validator("orb")
    @classmethod
    def _finite_orb(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("orb must be finite")
        return value


class HarmonicAspectsRequest(_StrictModel):
    longitudes: dict[str, float]
    orb: float = Field(default=1.0, ge=0.0, le=HARMONICS_MAX_ORB)
    orb_policy: HarmonicOrbPolicyRequest | None = None
    max_harmonic: int = Field(
        default=HARMONICS_DEFAULT_MAX_HARMONIC,
        ge=1,
        le=HARMONICS_MAX_HARMONIC,
    )

    @field_validator("longitudes", mode="before")
    @classmethod
    def _numeric_longitudes(cls, value: object) -> object:
        return _require_raw_longitude_mapping(value, field_name="longitudes")

    @field_validator("longitudes")
    @classmethod
    def _valid_longitudes(cls, value: dict[str, float]) -> dict[str, float]:
        return _clean_longitudes(value)

    @field_validator("orb", mode="before")
    @classmethod
    def _numeric_orb(cls, value: object) -> object:
        return _require_real_number(value, field_name="orb")

    @field_validator("orb")
    @classmethod
    def _finite_orb(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("orb must be finite")
        return value


class HarmonicSweepRequest(HarmonicAspectsRequest):
    pass


def _clean_composite_longitudes(value: dict[str, float], field_name: str) -> dict[str, float]:
    cleaned = _clean_longitudes(value)
    if len(cleaned) > HARMONICS_MAX_COMPOSITE_BODIES:
        raise ValueError(
            f"{field_name} may contain at most {HARMONICS_MAX_COMPOSITE_BODIES} bodies"
        )
    return cleaned


class HarmonicCompositeRequest(_StrictModel):
    longitudes_a: dict[str, float]
    longitudes_b: dict[str, float]
    harmonic: float = Field(ge=1.0, le=float(HARMONICS_MAX_HARMONIC))
    orb: float = Field(default=1.0, ge=0.0, le=HARMONICS_MAX_ORB)
    orb_policy: HarmonicOrbPolicyRequest | None = None
    label_a: str = Field(default="A", min_length=1, max_length=HARMONICS_MAX_LABEL_LENGTH)
    label_b: str = Field(default="B", min_length=1, max_length=HARMONICS_MAX_LABEL_LENGTH)

    @field_validator("longitudes_a", mode="before")
    @classmethod
    def _numeric_longitudes_a(cls, value: object) -> object:
        return _require_raw_longitude_mapping(value, field_name="longitudes_a")

    @field_validator("longitudes_a")
    @classmethod
    def _valid_longitudes_a(cls, value: dict[str, float]) -> dict[str, float]:
        return _clean_composite_longitudes(value, "longitudes_a")

    @field_validator("longitudes_b", mode="before")
    @classmethod
    def _numeric_longitudes_b(cls, value: object) -> object:
        return _require_raw_longitude_mapping(value, field_name="longitudes_b")

    @field_validator("longitudes_b")
    @classmethod
    def _valid_longitudes_b(cls, value: dict[str, float]) -> dict[str, float]:
        return _clean_composite_longitudes(value, "longitudes_b")

    @field_validator("harmonic", mode="before")
    @classmethod
    def _numeric_harmonic(cls, value: object) -> object:
        return _require_real_number(value, field_name="harmonic")

    @field_validator("harmonic")
    @classmethod
    def _finite_harmonic(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("harmonic must be finite")
        return value

    @field_validator("orb", mode="before")
    @classmethod
    def _numeric_orb(cls, value: object) -> object:
        return _require_real_number(value, field_name="orb")

    @field_validator("orb")
    @classmethod
    def _finite_orb(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("orb must be finite")
        return value

    @field_validator("label_a", "label_b")
    @classmethod
    def _valid_label(cls, value: str) -> str:
        label = value.strip()
        if not label:
            raise ValueError("composite labels must be non-empty")
        if ":" in label:
            raise ValueError("composite labels must not contain ':'")
        return label


class HarmonicsBoundsResponse(_StrictModel):
    max_body_count: int = HARMONICS_MAX_BODIES
    max_composite_body_count: int = HARMONICS_MAX_COMPOSITE_BODIES
    max_harmonic: int = HARMONICS_MAX_HARMONIC
    default_max_harmonic: int = HARMONICS_DEFAULT_MAX_HARMONIC
    max_orb: float = HARMONICS_MAX_ORB
    max_label_length: int = HARMONICS_MAX_LABEL_LENGTH


class HarmonicPresetResponse(_StrictModel):
    harmonic: int
    name: str
    description: str


class HarmonicOrbPolicyResponse(_StrictModel):
    """Resolved source-space and projected-chart orb truth."""

    scaling_mode: str
    reference_harmonic: float
    reference_orb_deg: float
    projected_orb_limit_deg: float | None = None
    source_orb_limit_deg: float | None = None
    resolved_harmonic: float | None = None
    authority: str
    source_locator: str
    formula: str
    continuous_extension: bool = False
    request_mode: str


class HarmonicProvenanceResponse(_StrictModel):
    source_module: str = "moira.harmonics"
    engine_entrypoint: str
    input_longitude_owner: str = "caller_supplied"
    chart_construction_owner: str = "not_this_route"
    formula_basis: str = "(normalized_longitude * harmonic) mod 360"
    harmonic_kind: str
    longitude_origin: str = "zero_aries"
    input_branch: str = "[0,360)"
    preset_name: str | None = None
    preset_description: str | None = None
    bounds: HarmonicsBoundsResponse = Field(default_factory=HarmonicsBoundsResponse)
    stage_sequence: list[str]
    jd_birth: float | None = None
    jd_now: float | None = None
    age_harmonic_basis: str | None = None
    orb_policy: HarmonicOrbPolicyResponse | None = None
    note: str | None = None


class HarmonicCatalogResponse(_StrictModel):
    presets: list[HarmonicPresetResponse]
    count: int
    bounds: HarmonicsBoundsResponse = Field(default_factory=HarmonicsBoundsResponse)
    provenance: HarmonicProvenanceResponse


class HarmonicPositionResponse(_StrictModel):
    body: str
    natal_longitude: float
    harmonic_longitude: float
    harmonic: float
    sign: str
    sign_symbol: str
    sign_degree: float


class HarmonicChartResponse(_StrictModel):
    positions: list[HarmonicPositionResponse]
    requested_harmonic: float
    effective_harmonic: float
    harmonic_kind: str
    input_count: int
    provenance: HarmonicProvenanceResponse


class HarmonicConjunctionResponse(_StrictModel):
    planet_a: str
    planet_b: str
    harmonic: float
    orb: float
    longitude: float


class HarmonicConjunctionsResponse(_StrictModel):
    conjunctions: list[HarmonicConjunctionResponse]
    requested_harmonic: float
    effective_harmonic: float
    orb: float
    input_count: int
    provenance: HarmonicProvenanceResponse


class HarmonicPatternScoreResponse(_StrictModel):
    pattern_score: float
    conjunctions: list[HarmonicConjunctionResponse]
    cluster_sizes: list[int]
    score: float
    requested_harmonic: float
    effective_harmonic: float
    orb: float
    input_count: int
    provenance: HarmonicProvenanceResponse


class HarmonicAspectResponse(_StrictModel):
    planet_a: str
    planet_b: str
    harmonic: int
    orb: float
    separation: float


class HarmonicAspectsResponse(_StrictModel):
    aspects: list[HarmonicAspectResponse]
    max_harmonic: int
    orb: float
    input_count: int
    provenance: HarmonicProvenanceResponse


class HarmonicSweepEntryResponse(_StrictModel):
    harmonic: int
    score: float
    n_conjunctions: int
    largest_cluster: int


class HarmonicSweepResponse(_StrictModel):
    entries: list[HarmonicSweepEntryResponse]
    max_harmonic: int
    orb: float
    input_count: int
    bounds: HarmonicsBoundsResponse = Field(default_factory=HarmonicsBoundsResponse)
    provenance: HarmonicProvenanceResponse


class HarmonicFingerprintResponse(_StrictModel):
    sweep: list[HarmonicSweepEntryResponse]
    dominant: list[int]
    total_score: float
    peak_harmonic: int
    peak_score: float
    max_harmonic: int
    orb: float
    bounds: HarmonicsBoundsResponse = Field(default_factory=HarmonicsBoundsResponse)
    provenance: HarmonicProvenanceResponse


class HarmonicCompositeResponse(_StrictModel):
    conjunctions: list[HarmonicConjunctionResponse]
    requested_harmonic: float
    effective_harmonic: float
    orb: float
    label_a: str
    label_b: str
    input_count_a: int
    input_count_b: int
    provenance: HarmonicProvenanceResponse


class HarmonicTransitSampleRequest(_StrictModel):
    jd_ut: float
    longitudes: dict[str, float]

    @field_validator("jd_ut", mode="before")
    @classmethod
    def _numeric_jd(cls, value: object) -> object:
        return _require_real_number(value, field_name="jd_ut")

    @field_validator("jd_ut")
    @classmethod
    def _finite_jd(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("jd_ut must be finite")
        return value

    @field_validator("longitudes", mode="before")
    @classmethod
    def _numeric_longitudes(cls, value: object) -> object:
        return _require_raw_longitude_mapping(
            value,
            field_name="transit longitudes",
        )

    @field_validator("longitudes")
    @classmethod
    def _valid_longitudes(cls, value: dict[str, float]) -> dict[str, float]:
        cleaned = _clean_longitudes(value)
        if len(cleaned) > HARMONICS_MAX_FORECAST_BODIES_PER_ORIGIN:
            raise ValueError(
                "transit longitudes may contain at most "
                f"{HARMONICS_MAX_FORECAST_BODIES_PER_ORIGIN} bodies"
            )
        return cleaned


class HarmonicTransitForecastRequest(_StrictModel):
    natal_longitudes: dict[str, float]
    transit_samples: list[HarmonicTransitSampleRequest] = Field(
        min_length=1,
        max_length=HARMONICS_MAX_FORECAST_SAMPLES,
    )
    harmonics: list[int] = Field(
        min_length=1,
        max_length=HARMONICS_MAX_FORECAST_HARMONICS,
    )
    modes: list[
        Literal["one_transit_two_natal", "two_transits_one_natal"]
    ] = Field(
        default_factory=lambda: [
            "one_transit_two_natal",
            "two_transits_one_natal",
        ]
    )
    orb: float = Field(default=1.0, ge=0.0, le=HARMONICS_MAX_ORB)
    orb_policy: HarmonicOrbPolicyRequest | None = None
    minimum_observed_duration_days: float = Field(default=0.0, ge=0.0)
    maximum_sample_gap_days: float = Field(default=1.0, gt=0.0)

    @field_validator("natal_longitudes", mode="before")
    @classmethod
    def _numeric_natal_longitudes(cls, value: object) -> object:
        return _require_raw_longitude_mapping(
            value,
            field_name="natal_longitudes",
        )

    @field_validator("natal_longitudes")
    @classmethod
    def _valid_natal_longitudes(cls, value: dict[str, float]) -> dict[str, float]:
        cleaned = _clean_longitudes(value)
        if len(cleaned) > HARMONICS_MAX_FORECAST_BODIES_PER_ORIGIN:
            raise ValueError(
                "natal_longitudes may contain at most "
                f"{HARMONICS_MAX_FORECAST_BODIES_PER_ORIGIN} bodies"
            )
        return cleaned

    @field_validator("harmonics", mode="before")
    @classmethod
    def _strict_harmonics(cls, value: object) -> object:
        if not isinstance(value, list):
            raise ValueError("harmonics must be a list of positive integers")
        if any(type(item) is not int for item in value):
            raise ValueError("harmonics must contain positive integers")
        return value

    @field_validator("harmonics")
    @classmethod
    def _valid_harmonics(cls, value: list[int]) -> list[int]:
        if any(harmonic < 1 or harmonic > HARMONICS_MAX_HARMONIC for harmonic in value):
            raise ValueError(
                f"harmonics must be between 1 and {HARMONICS_MAX_HARMONIC}"
            )
        if len(set(value)) != len(value):
            raise ValueError("harmonics must be unique")
        return value

    @field_validator("modes")
    @classmethod
    def _valid_modes(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("modes must contain at least one mode")
        if len(set(value)) != len(value):
            raise ValueError("modes must be unique")
        return value

    @field_validator(
        "orb",
        "minimum_observed_duration_days",
        "maximum_sample_gap_days",
        mode="before",
    )
    @classmethod
    def _numeric_policy_number(cls, value: object, info) -> object:
        return _require_real_number(value, field_name=info.field_name)

    @field_validator(
        "orb",
        "minimum_observed_duration_days",
        "maximum_sample_gap_days",
    )
    @classmethod
    def _finite_policy_number(cls, value: float, info) -> float:
        if not math.isfinite(value):
            raise ValueError(f"{info.field_name} must be finite")
        return value

    @model_validator(mode="after")
    def _bounded_forecast(self) -> "HarmonicTransitForecastRequest":
        first_bodies = tuple(self.transit_samples[0].longitudes)
        previous_jd: float | None = None
        for sample in self.transit_samples:
            if set(sample.longitudes) != set(first_bodies):
                raise ValueError(
                    "transit body identity must be consistent across samples"
                )
            if previous_jd is not None:
                if sample.jd_ut <= previous_jd:
                    raise ValueError(
                        "transit sample jd_ut values must be strictly increasing"
                    )
                if not math.isfinite(sample.jd_ut - previous_jd):
                    raise ValueError("transit sample timestamp gaps must be finite")
            previous_jd = sample.jd_ut
        if not math.isfinite(
            self.transit_samples[-1].jd_ut - self.transit_samples[0].jd_ut
        ):
            raise ValueError("transit sample timestamp span must be finite")

        natal_count = len(self.natal_longitudes)
        transit_count = len(first_bodies)
        candidates = 0
        if "one_transit_two_natal" in self.modes:
            candidates += transit_count * natal_count * (natal_count - 1) // 2
        if "two_transits_one_natal" in self.modes:
            candidates += natal_count * transit_count * (transit_count - 1) // 2
        work_units = candidates * len(self.harmonics) * len(self.transit_samples)
        if work_units > HARMONICS_MAX_FORECAST_WORK_UNITS:
            raise ValueError(
                "forecast request exceeds the bounded mixed-origin work limit "
                f"of {HARMONICS_MAX_FORECAST_WORK_UNITS} candidate evaluations"
            )
        return self


class HarmonicTransitMemberResponse(_StrictModel):
    body: str
    origin: str
    source_longitude_deg: float
    projected_longitude_deg: float


class HarmonicTransitPatternSampleResponse(_StrictModel):
    sample_index: int
    jd_ut: float
    harmonic: int
    mode: str
    members: list[HarmonicTransitMemberResponse]
    projected_spread_deg: float
    source_residual_spread_deg: float
    projected_orb_limit_deg: float
    source_orb_limit_deg: float


class HarmonicTransitMemberIdentityResponse(_StrictModel):
    origin: str
    body: str


class HarmonicTransitWindowResponse(_StrictModel):
    harmonic: int
    mode: str
    member_identities: list[HarmonicTransitMemberIdentityResponse]
    first_sampled_jd_ut: float
    peak_sampled_jd_ut: float
    last_sampled_jd_ut: float
    observed_duration_days: float
    sample_count: int
    samples: list[HarmonicTransitPatternSampleResponse]


class HarmonicTransitForecastPolicyResponse(_StrictModel):
    harmonics: list[int]
    modes: list[str]
    orb_policy: HarmonicOrbPolicyResponse
    minimum_observed_duration_days: float
    maximum_sample_gap_days: float


class HarmonicTransitForecastProvenanceResponse(_StrictModel):
    source_module: str = "moira.harmonic_transits"
    engine_entrypoint: str = "mixed_origin_harmonic_transit_forecast"
    forecast_family: str = "va_informed_mixed_origin_complete_triples"
    input_longitude_owner: str = "caller_supplied"
    chart_construction_owner: str = "not_this_route"
    time_basis: str = "caller_supplied_jd_ut"
    geometry: str = "minimum_circular_covering_arc_complete_triple"
    evaluation_scope: str
    claim_boundary: str
    source_locators: list[str]
    bounds: dict[str, int]


class HarmonicTransitForecastResponse(_StrictModel):
    windows: list[HarmonicTransitWindowResponse]
    window_count: int
    natal_bodies: list[str]
    transit_bodies: list[str]
    transit_sample_count: int
    policy: HarmonicTransitForecastPolicyResponse
    provenance: HarmonicTransitForecastProvenanceResponse
