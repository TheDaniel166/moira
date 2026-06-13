"""Transport models for P12-07 Huber direct house-frame routes."""

from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from moira.constants import HouseSystem


HUBER_MAX_POINTS = 64
HUBER_MAX_CONTACT_SPAN_YEARS = 144.0
HUBER_MIN_CONTACT_STEP_YEARS = 1.0 / 52.0
HUBER_MAX_ORB = 15.0
HUBER_MAX_POINT_NAME_LENGTH = 64
HUBER_KOCH_SYSTEM = HouseSystem.KOCH


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def _finite(value: float, field_name: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"{field_name} must be finite")
    return parsed


def _clean_points(value: dict[str, float]) -> dict[str, float]:
    if not value:
        raise ValueError("points must contain at least one entry")
    if len(value) > HUBER_MAX_POINTS:
        raise ValueError(f"points may contain at most {HUBER_MAX_POINTS} entries")

    cleaned: dict[str, float] = {}
    for raw_name, longitude in value.items():
        name = str(raw_name).strip()
        if not name:
            raise ValueError("point names must be non-empty")
        if len(name) > HUBER_MAX_POINT_NAME_LENGTH:
            raise ValueError(
                f"point names may contain at most {HUBER_MAX_POINT_NAME_LENGTH} characters"
            )
        if name in cleaned:
            raise ValueError("point names must be unique after trimming")
        if not math.isfinite(longitude):
            raise ValueError("point longitudes must be finite")
        cleaned[name] = longitude
    return cleaned


class HuberDirectHouseFrameRequest(_StrictModel):
    cusps: list[float] = Field(min_length=12, max_length=12)
    asc: float
    mc: float
    armc: float
    system: str = Field(default=HUBER_KOCH_SYSTEM, min_length=1, max_length=8)
    effective_system: str | None = Field(default=None, min_length=1, max_length=8)
    fallback: bool = False
    fallback_reason: str | None = None

    @field_validator("cusps")
    @classmethod
    def _valid_cusps(cls, value: list[float]) -> list[float]:
        if len(value) != 12:
            raise ValueError("house_frame.cusps must contain exactly 12 longitudes")
        for longitude in value:
            if not math.isfinite(longitude):
                raise ValueError("house_frame.cusps must be finite")
        return value

    @field_validator("asc", "mc", "armc")
    @classmethod
    def _valid_anchor(cls, value: float, info) -> float:
        return _finite(value, f"house_frame.{info.field_name}")

    @field_validator("system", "effective_system")
    @classmethod
    def _valid_system(cls, value: str | None, info) -> str | None:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError(f"house_frame.{info.field_name} must be non-empty")
        return stripped

    @field_validator("fallback", mode="before")
    @classmethod
    def _strict_fallback_boolean(cls, value: bool) -> bool:
        if not isinstance(value, bool):
            raise ValueError("house_frame.fallback must be a boolean")
        return value

    @model_validator(mode="after")
    def _valid_fallback_truth(self) -> "HuberDirectHouseFrameRequest":
        if self.fallback and not self.fallback_reason:
            raise ValueError("house_frame.fallback_reason is required when fallback is true")
        if not self.fallback and self.fallback_reason is not None:
            raise ValueError("house_frame.fallback_reason must be null when fallback is false")
        return self


class HuberHouseFrameRequest(_StrictModel):
    source: str = Field(default="direct_cusps")
    direct: HuberDirectHouseFrameRequest

    @field_validator("source")
    @classmethod
    def _direct_only(cls, value: str) -> str:
        if value != "direct_cusps":
            raise ValueError("only source='direct_cusps' is admitted for P12-07")
        return value


class HuberDynamicIntensityRequest(_StrictModel):
    house: int = Field(ge=1, le=12)
    fraction: float = Field(ge=0.0, le=1.0)

    @field_validator("fraction", mode="before")
    @classmethod
    def _finite_fraction(cls, value: float) -> float:
        return _finite(value, "fraction")


class HuberHouseZonesRequest(_StrictModel):
    house_frame: HuberHouseFrameRequest


class HuberAgePointRequest(_StrictModel):
    age_years: float = Field(ge=0.0)
    house_frame: HuberHouseFrameRequest

    @field_validator("age_years", mode="before")
    @classmethod
    def _finite_age(cls, value: float) -> float:
        return _finite(value, "age_years")


class HuberIntensityAtRequest(HuberHouseZonesRequest):
    longitude: float

    @field_validator("longitude")
    @classmethod
    def _finite_longitude(cls, value: float) -> float:
        return _finite(value, "longitude")


class HuberChartIntensityProfileRequest(HuberHouseZonesRequest):
    points: dict[str, float]

    @field_validator("points")
    @classmethod
    def _valid_points(cls, value: dict[str, float]) -> dict[str, float]:
        return _clean_points(value)


class HuberAgePointContactsRequest(HuberChartIntensityProfileRequest):
    orb: float = Field(default=2.0, ge=0.0, le=HUBER_MAX_ORB)
    start_age: float = Field(default=0.0, ge=0.0)
    end_age: float = Field(default=72.0, ge=0.0)
    step_years: float = Field(default=1.0 / 12.0, ge=HUBER_MIN_CONTACT_STEP_YEARS)

    @field_validator("orb", "start_age", "end_age", "step_years")
    @classmethod
    def _finite_scan_value(cls, value: float, info) -> float:
        return _finite(value, info.field_name)

    @model_validator(mode="after")
    def _valid_scan_window(self) -> "HuberAgePointContactsRequest":
        if self.end_age < self.start_age:
            raise ValueError("end_age must be greater than or equal to start_age")
        if self.end_age - self.start_age > HUBER_MAX_CONTACT_SPAN_YEARS:
            raise ValueError(
                f"contact scan span may not exceed {HUBER_MAX_CONTACT_SPAN_YEARS:g} years"
            )
        return self


class HuberBoundsResponse(_StrictModel):
    max_points: int = HUBER_MAX_POINTS
    max_contact_span_years: float = HUBER_MAX_CONTACT_SPAN_YEARS
    min_contact_step_years: float = HUBER_MIN_CONTACT_STEP_YEARS
    max_orb: float = HUBER_MAX_ORB
    max_point_name_length: int = HUBER_MAX_POINT_NAME_LENGTH


class HuberHouseFrameProvenanceResponse(_StrictModel):
    house_frame_source: str
    cusp_derivation_owner: str
    system: str
    requested_system: str
    effective_system: str
    fallback: bool
    fallback_reason: str | None
    is_koch_effective: bool
    koch_doctrine_preferred: bool = True
    chart_backed_derivation: str = "not_admitted_for_p12_07"
    note: str


class HuberHouseFrameResponse(_StrictModel):
    source: str
    cusps: list[float]
    asc: float
    mc: float
    armc: float
    system: str
    effective_system: str
    fallback: bool
    fallback_reason: str | None


class HuberProvenanceResponse(_StrictModel):
    source_module: str = "moira.huber"
    engine_entrypoint: str
    house_frame_source: str = "caller_supplied"
    curve_basis: str = "piecewise_half_cosine_reconstruction"
    curve_verification_note: str = "primary-text exact formula not independently verified"
    bounds: HuberBoundsResponse = Field(default_factory=HuberBoundsResponse)
    psychological_interpretation: str = "not_provided"
    chart_construction: str = "not_computed"
    house_derivation: str = "not_computed_by_huber_transport"
    stage_sequence: list[str]


class HuberDynamicIntensityResponse(_StrictModel):
    house: int
    requested_fraction: float
    effective_fraction: float
    intensity: float
    zone: str
    curve_basis: str
    provenance: HuberProvenanceResponse


class HuberHouseZoneResponse(_StrictModel):
    house: int
    cusp_longitude: float
    next_cusp_longitude: float
    house_size: float
    balance_point_longitude: float
    low_point_longitude: float
    balance_point_fraction: float
    low_point_fraction: float


class HuberHouseZonesResponse(_StrictModel):
    zones: list[HuberHouseZoneResponse]
    house_frame: HuberHouseFrameResponse
    house_frame_provenance: HuberHouseFrameProvenanceResponse
    huber_doctrine: str
    provenance: HuberProvenanceResponse


class HuberAgePointResponse(_StrictModel):
    age_years: float
    cycle: int
    house: int
    fraction_through_house: float
    longitude: float
    zone: str
    years_into_house: float
    intensity: float
    house_frame_provenance: HuberHouseFrameProvenanceResponse
    provenance: HuberProvenanceResponse


class HuberIntensityAtResponse(_StrictModel):
    longitude: float
    house: int
    fraction: float
    intensity: float
    zone: str
    house_frame_provenance: HuberHouseFrameProvenanceResponse
    provenance: HuberProvenanceResponse


class HuberPlanetIntensityScoreResponse(_StrictModel):
    name: str
    longitude: float
    house: int
    fraction: float
    intensity: float
    zone: str
    near_cusp: bool
    near_low_point: bool


class HuberChartIntensityProfileResponse(_StrictModel):
    scores: list[HuberPlanetIntensityScoreResponse]
    high_intensity: list[HuberPlanetIntensityScoreResponse]
    low_intensity: list[HuberPlanetIntensityScoreResponse]
    mean_intensity: float
    point_count: int
    house_frame_provenance: HuberHouseFrameProvenanceResponse
    provenance: HuberProvenanceResponse


class HuberAgePointContactResponse(_StrictModel):
    age_years: float
    point_name: str
    separation_degrees: float


class HuberScanBoundsResponse(_StrictModel):
    max_contact_span_years: float = HUBER_MAX_CONTACT_SPAN_YEARS
    min_contact_step_years: float = HUBER_MIN_CONTACT_STEP_YEARS
    max_orb: float = HUBER_MAX_ORB
    point_count: int


class HuberAgePointContactsResponse(_StrictModel):
    contacts: list[HuberAgePointContactResponse]
    orb: float
    start_age: float
    end_age: float
    step_years: float
    scan_bounds: HuberScanBoundsResponse
    house_frame_provenance: HuberHouseFrameProvenanceResponse
    provenance: HuberProvenanceResponse
