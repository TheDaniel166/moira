"""Transport models for chart and houses endpoints."""

from __future__ import annotations

from datetime import datetime
import math
from numbers import Real
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from moira.constants import HouseSystem
from moira.houses import PolarFallbackPolicy, UnknownSystemPolicy

from .positions import PlanetPositionResponse, PositionObserverContextResponse


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


HOUSE_DYNAMICS_MIN_DT_MINUTES = 1.0e-6 * 1440.0
HOUSE_DYNAMICS_MAX_DT_MINUTES = 1.0
HOUSE_DYNAMICS_DEFAULT_DARMC_DEG = 360.98564736629 / 1440.0
HOUSE_DYNAMICS_MIN_DARMC_DEG = 0.001
HOUSE_DYNAMICS_MAX_DARMC_DEG = 1.0
POLAR_ADMISSIBILITY_MAX_SAMPLES = 3601
POLAR_ADMISSIBILITY_PLACIDUS_MAX_SAMPLES = 73


def _require_real_number(value, *, field_name: str, optional: bool = False):
    if value is None and optional:
        return None
    if isinstance(value, bool) or not isinstance(value, Real):
        raise ValueError(f"{field_name} must be a real number")
    return value


class NodePositionResponse(_StrictModel):
    name: str
    longitude: float
    speed: float
    sign: str
    sign_symbol: str
    sign_degree: float


class ChartRequest(_StrictModel):
    dt: datetime
    bodies: list[str] | None = None
    include_nodes: bool = True
    observer_lat: float | None = None
    observer_lon: float | None = None
    observer_elev_m: float = 0.0


class CalendarDateTimeResponse(_StrictModel):
    """BCE-safe structured calendar representation (astronomical year numbering)."""
    year: int
    month: int
    day: int
    hour: int
    minute: int
    second: int
    microsecond: int = 0
    tzname: str = "UTC"


class ChartResponse(_StrictModel):
    jd_ut: float
    datetime_utc: str
    calendar_utc: CalendarDateTimeResponse | None = None
    obliquity: float
    delta_t: float
    planets: dict[str, PlanetPositionResponse]
    nodes: dict[str, NodePositionResponse]


class ChartPlanetReductionSummaryResponse(_StrictModel):
    source_vessel: str
    selection_surface: str
    apparent: bool
    aberration: bool
    grav_deflection: bool
    nutation: bool
    frame: str
    center: str
    topocentric_applied: bool
    stage_sequence: list[str]


class ChartNodeReductionSummaryResponse(_StrictModel):
    source_vessel: str
    source_surface: str
    nutation: bool
    frame: str
    stage_sequence: list[str]


class ChartReductionTruthResponse(_StrictModel):
    engine_surface: str
    source_vessel: str
    requested_datetime: str
    normalized_datetime_utc: str
    jd_ut: float
    jd_ut1: float
    jd_tt: float
    delta_t_seconds: float
    obliquity_deg: float
    requested_bodies: list[str] | None = None
    returned_bodies: list[str]
    include_nodes_requested: bool
    include_nodes_returned: bool
    topocentric_requested: bool
    observer: PositionObserverContextResponse
    stage_sequence: list[str]
    planet_reductions: dict[str, ChartPlanetReductionSummaryResponse]
    node_reductions: dict[str, ChartNodeReductionSummaryResponse]


class ChartReductionResponse(_StrictModel):
    result: ChartResponse
    reduction: ChartReductionTruthResponse


class HousePolicyRequest(_StrictModel):
    """Input doctrine for unknown-system and polar fallback.
    Uses Moira's full rich enums so that all options (including EXPERIMENTAL_SEARCH,
    FALLBACK_TO_EQUAL, FALLBACK_TO_WHOLE_SIGN, RAISE, etc.) are first-class and validated.
    Defaults match HousePolicy.default().
    """
    unknown_system: UnknownSystemPolicy = UnknownSystemPolicy.FALLBACK_TO_PLACIDUS
    polar_fallback: PolarFallbackPolicy = PolarFallbackPolicy.FALLBACK_TO_PORPHYRY


class HousesRequest(_StrictModel):
    dt: datetime
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)
    system: str | None = None
    policy: HousePolicyRequest | None = None
    include_boundary_geometry: bool = False


class HousePolicyResponse(_StrictModel):
    """Governing doctrine for unknown-system and polar-latitude fallback resolution.
    Uses the full Moira enums (no artificial limits on polar fallback options).
    """
    unknown_system: UnknownSystemPolicy
    polar_fallback: PolarFallbackPolicy


class HouseBoundaryCurvePointResponse(_StrictModel):
    direction: list[float]
    right_ascension_deg: float
    declination_deg: float


class HouseBoundaryGeometryResponse(_StrictModel):
    house: int = Field(ge=1, le=12)
    kind: str
    cusp_longitude: float
    anchor_direction: list[float]
    plane_normal: list[float] | None = None
    curve_points: list[HouseBoundaryCurvePointResponse] = Field(default_factory=list)
    event_phase: str | None = None
    event_fraction: float | None = None


class HouseBoundaryGeometrySetResponse(_StrictModel):
    effective_system: str
    availability: str
    frame: str
    obliquity_deg: float
    observer_latitude_deg: float
    zodiac_offset_deg: float
    boundaries: list[HouseBoundaryGeometryResponse] = Field(default_factory=list)
    reason: str | None = None


class HousesResponse(_StrictModel):
    system: str
    effective_system: str
    fallback: bool
    fallback_reason: str | None = None
    classification_family: str | None = None
    classification_cusp_basis: str | None = None
    classification_latitude_sensitive: bool | None = None
    classification_polar_capable: bool | None = None
    policy: HousePolicyResponse
    asc: float
    mc: float
    armc: float
    dsc: float
    ic: float
    east_point: float | None = None
    vertex: float | None = None
    anti_vertex: float | None = None
    cusps: list[float]
    boundary_geometry: HouseBoundaryGeometrySetResponse | None = None


class CuspSpeedResponse(_StrictModel):
    """Instantaneous speed of a single house cusp."""
    house: int = Field(ge=1, le=12)
    cusp_longitude: float
    speed_deg_per_day: float


class HouseDynamicsRequest(_StrictModel):
    """Request payload for computing instantaneous house cusp and angle speeds."""
    dt: datetime
    latitude: float = Field(ge=-90.0, le=90.0, allow_inf_nan=False)
    longitude: float = Field(ge=-180.0, le=180.0, allow_inf_nan=False)
    system: str | None = None
    policy: HousePolicyRequest | None = None
    dt_minutes: float = Field(
        default=1.0,
        ge=HOUSE_DYNAMICS_MIN_DT_MINUTES,
        le=HOUSE_DYNAMICS_MAX_DT_MINUTES,
        allow_inf_nan=False,
        description=(
            "Centered finite-difference half-step in minutes. The admitted interval "
            "starts at the engine's numerical-noise floor and ends at its canonical "
            "one-minute half-step."
        ),
    )

    @field_validator("latitude", "longitude", "dt_minutes", mode="before")
    @classmethod
    def _strict_numbers(cls, value, info):
        return _require_real_number(value, field_name=info.field_name)


class HouseDynamicsFromArmcRequest(_StrictModel):
    """ARMC-native house dynamics with true obliquity held fixed."""

    armc: float = Field(ge=0.0, lt=360.0, allow_inf_nan=False)
    obliquity: float = Field(gt=0.0, lt=90.0, allow_inf_nan=False)
    latitude: float = Field(gt=-90.0, lt=90.0, allow_inf_nan=False)
    system: str | None = None
    policy: HousePolicyRequest | None = None
    sun_longitude: float | None = Field(
        default=None,
        ge=0.0,
        lt=360.0,
        allow_inf_nan=False,
    )
    darmc_deg: float = Field(
        default=HOUSE_DYNAMICS_DEFAULT_DARMC_DEG,
        ge=HOUSE_DYNAMICS_MIN_DARMC_DEG,
        le=HOUSE_DYNAMICS_MAX_DARMC_DEG,
        allow_inf_nan=False,
        description="Centered finite-difference half-step in degrees of ARMC.",
    )

    @field_validator(
        "armc",
        "obliquity",
        "latitude",
        "sun_longitude",
        "darmc_deg",
        mode="before",
    )
    @classmethod
    def _strict_numbers(cls, value, info):
        return _require_real_number(
            value,
            field_name=info.field_name,
            optional=info.field_name == "sun_longitude",
        )


class AnalyticalHouseDynamicsRequest(_StrictModel):
    """Inputs for exact analytical MC, ASC, and Vertex velocities."""

    armc: float = Field(ge=0.0, lt=360.0, allow_inf_nan=False)
    obliquity: float = Field(gt=0.0, lt=90.0, allow_inf_nan=False)
    latitude: float = Field(gt=-90.0, lt=90.0, allow_inf_nan=False)

    @field_validator("armc", "obliquity", "latitude", mode="before")
    @classmethod
    def _strict_numbers(cls, value, info):
        return _require_real_number(value, field_name=info.field_name)


class HouseDynamicsComputationResponse(_StrictModel):
    """Explicit method and independent-variable truth for a dynamics result."""

    engine_surface: str
    source_vessel: str
    method: Literal["centered_finite_difference", "analytical_derivative"]
    independent_variable: Literal["time", "armc"]
    half_step: float | None = None
    half_step_unit: Literal["minutes", "degrees_armc"] | None = None
    speed_unit: Literal["degrees_per_day"] = "degrees_per_day"
    obliquity_held_fixed: bool


class HouseDynamicsResponse(_StrictModel):
    """Response payload carrying parent house cusps and instantaneous cusp and angle velocities."""
    house_cusps: HousesResponse
    cusp_speeds: list[CuspSpeedResponse]
    asc_speed_deg_per_day: float
    mc_speed_deg_per_day: float
    vertex_speed_deg_per_day: float
    anti_vertex_speed_deg_per_day: float
    computation: HouseDynamicsComputationResponse


class AnalyticalHouseDynamicsResponse(_StrictModel):
    """Exact analytical angle velocities; unavailable singular values are null."""

    armc: float
    obliquity: float
    latitude: float
    mc_speed_deg_per_day: float
    asc_speed_deg_per_day: float | None
    vertex_speed_deg_per_day: float | None
    anti_vertex_speed_deg_per_day: float | None
    asc_available: bool
    vertex_available: bool
    asc_unavailable_reason: str | None = None
    vertex_unavailable_reason: str | None = None
    computation: HouseDynamicsComputationResponse


class HouseSystemClassificationResponse(_StrictModel):
    """Doctrinal classification of the (effective) house system.
    Mirrors the engine's HouseSystemClassification for nested schema exposure in reduction truth.
    """
    family: str
    cusp_basis: str
    latitude_sensitive: bool
    polar_capable: bool


class HousesReductionTruthResponse(_StrictModel):
    """Reduction truth for houses: the doctrine and computation path that produced the result.

    This now exposes the *full* HousePolicy object shape as a proper nested schema
    (using the canonical Moira enums for unknown_system and the rich polar_fallback options
    including EXPERIMENTAL_SEARCH, FALLBACK_TO_EQUAL, FALLBACK_TO_WHOLE_SIGN, etc.).

    Additional fields beyond the compact HousesResponse capture the complete governance:
    - requested vs applied policy
    - full classification as nested object
    - explicit fallback provenance
    """
    engine_surface: str
    source_vessel: str
    requested_datetime: str
    normalized_jd_ut: float
    requested_system: str | None
    effective_system: str
    requested_policy: HousePolicyResponse | None = None
    applied_policy: HousePolicyResponse
    fallback: bool
    fallback_reason: str | None = None
    classification: HouseSystemClassificationResponse | None = None


class HousesReductionResponse(_StrictModel):
    result: HousesResponse
    reduction: HousesReductionTruthResponse


class PolarHouseWindowResponse(_StrictModel):
    start_armc: float
    end_armc: float
    sample_count: int


class PolarAdmissibilityRequest(_StrictModel):
    latitude: float = Field(ge=-90.0, le=90.0, allow_inf_nan=False)
    system: str = HouseSystem.CAMPANUS
    dt: datetime | None = None
    obliquity: float | None = Field(default=None, gt=0.0, lt=90.0, allow_inf_nan=False)
    armc_start: float = Field(default=0.0, ge=0.0, le=360.0, allow_inf_nan=False)
    armc_end: float = Field(default=355.0, ge=0.0, le=360.0, allow_inf_nan=False)
    armc_step: float = Field(default=5.0, gt=0.0, le=360.0, allow_inf_nan=False)
    rho_max: float | None = Field(default=None, ge=1.0, allow_inf_nan=False)
    stability_radius: int = Field(default=0, ge=0)

    @field_validator(
        "latitude",
        "obliquity",
        "armc_start",
        "armc_end",
        "armc_step",
        "rho_max",
        mode="before",
    )
    @classmethod
    def _strict_numbers(cls, value, info):
        return _require_real_number(
            value,
            field_name=info.field_name,
            optional=info.field_name in {"obliquity", "rho_max"},
        )

    @field_validator("stability_radius", mode="before")
    @classmethod
    def _strict_stability_radius(cls, value):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("stability_radius must be an integer")
        return value

    @field_validator("system", mode="before")
    @classmethod
    def _nonempty_system(cls, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("system must be a non-empty string")
        return value.strip()

    @field_validator("dt")
    @classmethod
    def _aware_datetime(cls, value):
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("dt must be timezone-aware")
        return value

    @model_validator(mode="after")
    def _bounded_grid(self):
        if self.armc_end < self.armc_start:
            raise ValueError("armc_end must be greater than or equal to armc_start")
        span = self.armc_end - self.armc_start
        if span > 0.0 and self.armc_start + self.armc_step <= self.armc_start:
            raise ValueError("armc_step is too small to advance the ARMC grid")
        interval_ratio = span / self.armc_step
        if not math.isfinite(interval_ratio):
            raise ValueError(
                "polar admissibility scan exceeds the maximum of "
                f"{POLAR_ADMISSIBILITY_MAX_SAMPLES} samples"
            )
        intervals = math.floor(interval_ratio + 1.0e-12)
        sample_count = intervals + 1
        if sample_count > POLAR_ADMISSIBILITY_MAX_SAMPLES:
            raise ValueError(
                "polar admissibility scan exceeds the maximum of "
                f"{POLAR_ADMISSIBILITY_MAX_SAMPLES} samples"
            )
        if 2 * self.stability_radius + 1 > sample_count:
            raise ValueError(
                "stability_radius is too large for the requested ARMC sample grid"
            )
        return self

    @property
    def sample_count(self) -> int:
        """Number of samples in the inclusive-start, bounded-end ARMC grid."""

        span = self.armc_end - self.armc_start
        return math.floor(span / self.armc_step + 1.0e-12) + 1

    @property
    def last_sampled_armc(self) -> float:
        """Final ARMC actually sampled at or below the requested upper bound."""

        return self.armc_start + (self.sample_count - 1) * self.armc_step


class PolarAdmissibilityResponse(_StrictModel):
    latitude: float
    obliquity: float
    system: str
    armc_start: float
    armc_end: float
    armc_step: float
    last_sampled_armc: float
    rho_max: float | None = None
    stability_radius: int
    maximum_allowed_samples: int
    total_samples: int
    valid_fraction: float
    has_any_window: bool
    windows: list[PolarHouseWindowResponse]
    practical_windows: list[PolarHouseWindowResponse] = Field(default_factory=list)
    stable_practical_windows: list[PolarHouseWindowResponse] = Field(default_factory=list)


__all__ = [
    "AnalyticalHouseDynamicsRequest",
    "AnalyticalHouseDynamicsResponse",
    "CalendarDateTimeResponse",
    "ChartPlanetReductionSummaryResponse",
    "ChartReductionResponse",
    "ChartReductionTruthResponse",
    "ChartRequest",
    "ChartResponse",
    "ChartNodeReductionSummaryResponse",
    "HousePolicyRequest",
    "HousePolicyResponse",
    "HouseBoundaryCurvePointResponse",
    "HouseBoundaryGeometryResponse",
    "HouseBoundaryGeometrySetResponse",
    "HouseDynamicsComputationResponse",
    "HouseDynamicsFromArmcRequest",
    "HouseDynamicsRequest",
    "HouseDynamicsResponse",
    "CuspSpeedResponse",
    "HouseSystemClassificationResponse",
    "HousesReductionResponse",
    "HousesReductionTruthResponse",
    "HousesRequest",
    "HousesResponse",
    "NodePositionResponse",
    "PolarHouseWindowResponse",
    "PolarAdmissibilityRequest",
    "PolarAdmissibilityResponse",
    "POLAR_ADMISSIBILITY_MAX_SAMPLES",
    "POLAR_ADMISSIBILITY_PLACIDUS_MAX_SAMPLES",
]

# Rebuild for forward references (Pydantic v2 + string annotations in unions/optionals)
HousesRequest.model_rebuild()
HousesResponse.model_rebuild()
HousesReductionResponse.model_rebuild()
PolarAdmissibilityRequest.model_rebuild()
PolarAdmissibilityResponse.model_rebuild()
