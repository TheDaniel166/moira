"""Transport models for fixed stars (Phase 11 catalog surfaces).

Designed for high-performance website use with the sovereign star registry.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class StarPositionRequest(_StrictModel):
    dt: datetime
    star: str  # name, designation, or common name


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


class StarsBulkRequest(_StrictModel):
    dt: datetime
    stars: list[str]
    skip_missing: bool = True


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


class VariableStarStateRequest(_StrictModel):
    dt: datetime
    star: str
    eclipse_threshold: float | None = None


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


class VariableStarRangeRequest(_StrictModel):
    star: str
    jd_start: float
    jd_end: float


class VariableStarRangeResponse(_StrictModel):
    star: str
    minima_jd: list[float]
    maxima_jd: list[float]


class VariableStarCatalogProfileRequest(_StrictModel):
    dt: datetime
    eclipse_threshold: float | None = None


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


class VariableStarPairRequest(_StrictModel):
    dt: datetime
    primary: str
    secondary: str
    eclipse_threshold: float | None = None


class VariableStarPairResponse(_StrictModel):
    primary: VariableStarConditionResponse
    secondary: VariableStarConditionResponse
    is_same_type_class: bool
    is_same_quality: bool
    both_malefic: bool
    both_in_eclipse: bool
    quality_conflict: bool


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


class MultipleStarStateRequest(_StrictModel):
    dt: datetime
    system: str
    aperture_mm: float = 100.0


class MultipleStarStateResponse(_StrictModel):
    system: MultipleStarSystemResponse
    separation_arcsec: float
    position_angle_deg: float
    is_resolvable: bool
    is_resolvable_100mm: bool
    is_resolvable_200mm: bool
    dominant_component: str
    components: dict[str, MultipleStarComponentResponse]


class MultipleStarListResponse(_StrictModel):
    systems: list[str]
    total: int
