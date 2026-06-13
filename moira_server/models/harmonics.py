"""Transport models for P12-02 harmonic projection routes."""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


HARMONICS_MAX_BODIES = 64
HARMONICS_MAX_COMPOSITE_BODIES = 32
HARMONICS_MAX_HARMONIC = 128
HARMONICS_DEFAULT_MAX_HARMONIC = 32
HARMONICS_MAX_ORB = 30.0
HARMONICS_MAX_LABEL_LENGTH = 64


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


class HarmonicChartRequest(_StrictModel):
    longitudes: dict[str, float]
    harmonic: int = Field(ge=1, le=HARMONICS_MAX_HARMONIC)

    @field_validator("longitudes")
    @classmethod
    def _valid_longitudes(cls, value: dict[str, float]) -> dict[str, float]:
        return _clean_longitudes(value)


class HarmonicAgeChartRequest(_StrictModel):
    longitudes: dict[str, float]
    jd_birth: float
    jd_now: float

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

    @field_validator("orb")
    @classmethod
    def _finite_orb(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("orb must be finite")
        return value


class HarmonicAspectsRequest(_StrictModel):
    longitudes: dict[str, float]
    orb: float = Field(default=1.0, ge=0.0, le=HARMONICS_MAX_ORB)
    max_harmonic: int = Field(
        default=HARMONICS_DEFAULT_MAX_HARMONIC,
        ge=1,
        le=HARMONICS_MAX_HARMONIC,
    )

    @field_validator("longitudes")
    @classmethod
    def _valid_longitudes(cls, value: dict[str, float]) -> dict[str, float]:
        return _clean_longitudes(value)

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
    harmonic: int = Field(ge=1, le=HARMONICS_MAX_HARMONIC)
    orb: float = Field(default=1.0, ge=0.0, le=HARMONICS_MAX_ORB)
    label_a: str = Field(default="A", min_length=1, max_length=HARMONICS_MAX_LABEL_LENGTH)
    label_b: str = Field(default="B", min_length=1, max_length=HARMONICS_MAX_LABEL_LENGTH)

    @field_validator("longitudes_a")
    @classmethod
    def _valid_longitudes_a(cls, value: dict[str, float]) -> dict[str, float]:
        return _clean_composite_longitudes(value, "longitudes_a")

    @field_validator("longitudes_b")
    @classmethod
    def _valid_longitudes_b(cls, value: dict[str, float]) -> dict[str, float]:
        return _clean_composite_longitudes(value, "longitudes_b")

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


class HarmonicProvenanceResponse(_StrictModel):
    source_module: str = "moira.harmonics"
    engine_entrypoint: str
    input_longitude_owner: str = "caller_supplied"
    chart_construction_owner: str = "not_this_route"
    formula_basis: str = "(longitude * harmonic) mod 360"
    harmonic_kind: str
    preset_name: str | None = None
    preset_description: str | None = None
    bounds: HarmonicsBoundsResponse = Field(default_factory=HarmonicsBoundsResponse)
    stage_sequence: list[str]
    jd_birth: float | None = None
    jd_now: float | None = None
    age_harmonic_basis: str | None = None
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
