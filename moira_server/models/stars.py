"""Transport models for fixed stars (Phase 11 catalog surfaces).

Designed for high-performance website use with the sovereign star registry.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


STARS_BULK_MAX_ITEMS = 500
VARIABLE_STAR_RANGE_MAX_DAYS = 366.0
VARIABLE_STAR_ECLIPSE_THRESHOLD_MAX = 5.0
MULTIPLE_STAR_APERTURE_MAX_MM = 10000.0


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StarPositionRequest(_StrictModel):
    dt: datetime
    star: str = Field(min_length=1)  # name, designation, or common name

    @field_validator("dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value

    @field_validator("star")
    @classmethod
    def _non_empty_star(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("star must be non-empty")
        return stripped


class StarPositionProvenanceResponse(_StrictModel):
    requested_datetime: str | None = None
    normalized_datetime_utc: str | None = None
    jd_tt: float | None = None
    coordinate_source: str = "sovereign_star_registry"
    source: str | None = None
    source_mode: str | None = None
    lookup_kind: str | None = None
    hipparcos_name: str | None = None
    constellation: str | None = None
    gaia_match_status: str | None = None
    gaia_source_index: int | None = None
    source_kind: str | None = None
    merge_state: str | None = None
    observer_mode: str | None = None
    is_topocentric: bool | None = None
    true_position: bool | None = None
    dedup_applied: bool | None = None
    relation_kind: str | None = None
    relation_basis: str | None = None
    relation_star_name: str | None = None
    condition_result_kind: str | None = None
    condition_state: str | None = None
    stage_sequence: list[str]


class StarPositionResponse(_StrictModel):
    name: str
    designation: str | None = None
    longitude: float
    latitude: float
    distance: float | None = None
    magnitude: float | None = None
    sign: str
    sign_symbol: str
    sign_degree: float
    is_variable: bool = False
    provenance: StarPositionProvenanceResponse


class StarsBulkRequest(_StrictModel):
    dt: datetime
    stars: list[str] = Field(min_length=1, max_length=STARS_BULK_MAX_ITEMS)
    skip_missing: bool = True

    @field_validator("dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value

    @field_validator("stars")
    @classmethod
    def _valid_stars(cls, value: list[str]) -> list[str]:
        stripped = [item.strip() for item in value]
        if any(not item for item in stripped):
            raise ValueError("stars entries must be non-empty")
        return stripped


class StarsBulkResponse(_StrictModel):
    dt: datetime
    results: dict[str, StarPositionResponse]
    missing: list[str] = []


class StarListResponse(_StrictModel):
    stars: list[str]  # names or designations
    total: int


class VariableStarCatalogResponse(_StrictModel):
    name: str
    designation: str
    var_type: str
    epoch_jd: float
    epoch_is_minimum: bool
    period_days: float
    mag_max: float
    mag_min: float
    mag_min2: float
    eclipse_width: float
    classical_quality: str
    amplitude: float
    type_class: str
    is_eclipsing: bool
    is_pulsating: bool
    is_long_period: bool
    is_irregular: bool
    note: str
    provenance: "VariableStarCatalogProvenanceResponse"


class VariableStarCatalogProvenanceResponse(_StrictModel):
    catalog_source: list[str]
    catalog_scope: str = "curated_astrological_variable_star_catalog"
    phase_convention: str
    var_type: str
    epoch_jd: float
    epoch_is_minimum: bool
    period_days: float
    stage_sequence: list[str]


class VariableStarComputationProvenanceResponse(_StrictModel):
    requested_datetime: str | None = None
    normalized_datetime_utc: str | None = None
    jd: float | None = None
    computation_source: str = "variable_star_oracle"
    catalog_source: list[str]
    requested_stars: list[str]
    returned_stars: list[str]
    eclipse_threshold: float
    phase_convention: str
    stage_sequence: list[str]


class VariableStarStateRequest(_StrictModel):
    dt: datetime
    star: str = Field(min_length=1)
    eclipse_threshold: float | None = Field(default=None, ge=0.0, le=VARIABLE_STAR_ECLIPSE_THRESHOLD_MAX)

    @field_validator("dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value

    @field_validator("star")
    @classmethod
    def _non_empty_star(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("star must be non-empty")
        return stripped


class VariableStarConditionResponse(_StrictModel):
    name: str
    designation: str
    var_type: str
    type_class: str
    classical_quality: str
    is_malefic: bool
    is_benefic: bool
    amplitude: float
    period_days: float
    is_irregular: bool
    phase: float
    magnitude: float
    malefic_score: float
    benefic_score: float
    in_eclipse: bool


class VariableStarStateResponse(_StrictModel):
    star: VariableStarCatalogResponse
    condition: VariableStarConditionResponse
    next_minimum_jd: float | None
    next_maximum_jd: float | None
    provenance: VariableStarComputationProvenanceResponse


class VariableStarRangeRequest(_StrictModel):
    star: str = Field(min_length=1)
    jd_start: float
    jd_end: float

    @field_validator("star")
    @classmethod
    def _non_empty_star(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("star must be non-empty")
        return stripped

    @field_validator("jd_start", "jd_end")
    @classmethod
    def _finite_jd(cls, value: float) -> float:
        import math

        if not math.isfinite(value):
            raise ValueError("jd_start and jd_end must be finite")
        return value


class VariableStarRangeResponse(_StrictModel):
    star: str
    minima_jd: list[float]
    maxima_jd: list[float]
    provenance: VariableStarComputationProvenanceResponse


class VariableStarCatalogProfileRequest(_StrictModel):
    dt: datetime
    eclipse_threshold: float | None = Field(default=None, ge=0.0, le=VARIABLE_STAR_ECLIPSE_THRESHOLD_MAX)

    @field_validator("dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value


class VariableStarCatalogProfileResponse(_StrictModel):
    profiles: list[VariableStarConditionResponse]
    star_count: int
    eclipsing_count: int
    pulsating_count: int
    long_period_count: int
    malefic_count: int
    benefic_count: int
    neutral_count: int
    mixed_count: int
    eclipse_active_count: int
    has_active_eclipses: bool
    provenance: VariableStarComputationProvenanceResponse


class VariableStarPairRequest(_StrictModel):
    dt: datetime
    primary: str = Field(min_length=1)
    secondary: str = Field(min_length=1)
    eclipse_threshold: float | None = Field(default=None, ge=0.0, le=VARIABLE_STAR_ECLIPSE_THRESHOLD_MAX)

    @field_validator("dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value

    @field_validator("primary", "secondary")
    @classmethod
    def _non_empty_star(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("variable star names must be non-empty")
        return stripped


class VariableStarPairResponse(_StrictModel):
    primary: VariableStarConditionResponse
    secondary: VariableStarConditionResponse
    is_same_type_class: bool
    is_same_quality: bool
    both_malefic: bool
    both_in_eclipse: bool
    quality_conflict: bool
    provenance: VariableStarComputationProvenanceResponse


class MultipleStarComponentResponse(_StrictModel):
    label: str
    spectral_type: str
    magnitude: float
    mass_solar: float
    note: str


class MultipleStarOrbitResponse(_StrictModel):
    label: str
    period_yr: float
    epoch_jd: float
    ecc: float
    semi_major_arcsec: float
    incl_deg: float
    node_deg: float
    arg_peri_deg: float
    ref_pa_deg: float
    period_uncertain: bool


class MultipleStarCatalogProvenanceResponse(_StrictModel):
    catalog_source: list[str]
    catalog_scope: str = "curated_astrological_multiple_star_catalog"
    system_type: str
    orbit_model: str
    orbital_doctrine: str
    resolvability_doctrine: str = "Dawes limit: 116 / aperture_mm arcseconds"
    combined_magnitude_doctrine: str = "flux_sum_to_combined_v_magnitude"
    primary_orbit_label: str | None = None
    primary_orbit_period_uncertain: bool | None = None
    stage_sequence: list[str]


class MultipleStarStateProvenanceResponse(_StrictModel):
    requested_datetime: str
    normalized_datetime_utc: str
    jd: float
    computation_source: str = "multiple_star_oracle"
    catalog_source: list[str]
    requested_system: str
    returned_system: str
    system_type: str
    orbit_model: str
    aperture_mm: float
    dawes_limit_arcsec: float
    primary_orbit_label: str | None = None
    primary_orbit_period_uncertain: bool | None = None
    stage_sequence: list[str]


class MultipleStarListProvenanceResponse(_StrictModel):
    catalog_source: list[str]
    catalog_scope: str = "curated_astrological_multiple_star_catalog"
    requested_query: str | None = None
    requested_system_type: str | None = None
    limit: int
    returned_count: int
    stage_sequence: list[str]


class MultipleStarSystemResponse(_StrictModel):
    name: str
    designation: str
    also_known_as: list[str]
    system_type: str
    components: list[MultipleStarComponentResponse]
    orbits: list[MultipleStarOrbitResponse]
    combined_mag: float
    computed_combined_magnitude: float
    classical_quality: str
    note: str
    provenance: MultipleStarCatalogProvenanceResponse


class MultipleStarStateRequest(_StrictModel):
    dt: datetime
    system: str = Field(min_length=1)
    aperture_mm: float = Field(default=100.0, gt=0.0, le=MULTIPLE_STAR_APERTURE_MAX_MM)

    @field_validator("dt")
    @classmethod
    def _aware_datetime(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("dt must be timezone-aware")
        return value

    @field_validator("system")
    @classmethod
    def _non_empty_system(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("system must be non-empty")
        return stripped

    @field_validator("aperture_mm")
    @classmethod
    def _finite_aperture(cls, value: float) -> float:
        import math

        if not math.isfinite(value):
            raise ValueError("aperture_mm must be finite")
        return value


class MultipleStarStateResponse(_StrictModel):
    system: MultipleStarSystemResponse
    separation_arcsec: float
    position_angle_deg: float
    is_resolvable: bool
    is_resolvable_100mm: bool
    is_resolvable_200mm: bool
    dominant_component: str
    components: dict[str, MultipleStarComponentResponse]
    provenance: MultipleStarStateProvenanceResponse


class MultipleStarListResponse(_StrictModel):
    systems: list[str]
    total: int
    provenance: MultipleStarListProvenanceResponse
