"""Transport contracts for bounded relationship and locational forecasting.

These vessels expose geometry and computation receipts only.  They do not
carry interpretation, location ranking, travel advice, or progressed/directed
relationship-chart policy.
"""

from __future__ import annotations

import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from moira.constants import HouseSystem

from .astrocartography import (
    AstrocartographyLineResponse,
    AstrocartographySubplanetaryPointResponse,
)
from .chart import HousePolicyRequest, HousesResponse, NodePositionResponse
from .positions import PlanetPositionResponse
from .relationship import (
    CompositeChartRequest,
    CompositeComputationTruthResponse,
    DavisonChartRequest,
    DavisonComputationTruthResponse,
)
from .transits import TransitEventResponse


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _RelationshipTransitRequest(_StrictModel):
    moving_bodies: list[str] = Field(min_length=1, max_length=4)
    jd_start: float
    jd_end: float
    tier: Literal[0, 1, 2] = 0
    aspect_names: list[str] | None = Field(default=None, min_length=1, max_length=16)
    include_nodes: bool = True
    include_angles: bool = False
    include_cusps: bool = False
    target_names: list[str] | None = Field(default=None, min_length=1, max_length=16)
    direction: Literal["direct", "retrograde", "either"] = "either"
    search_motion: Literal["forward", "backward"] = "forward"
    step_days: float | None = Field(default=None, ge=0.01)
    solver_tolerance_days: float | None = Field(default=None, gt=0.0)

    @field_validator(
        "jd_start",
        "jd_end",
        "step_days",
        "solver_tolerance_days",
        mode="before",
    )
    @classmethod
    def _finite_numbers(cls, value: Any) -> Any:
        if value is None:
            return value
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("forecast search values must be finite numbers")
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError("forecast search values must be finite numbers")
        return parsed

    @field_validator("tier", mode="before")
    @classmethod
    def _strict_tier(cls, value: Any) -> Any:
        if isinstance(value, bool):
            raise ValueError("tier must be 0, 1, or 2")
        return value

    @field_validator(
        "include_nodes",
        "include_angles",
        "include_cusps",
        mode="before",
    )
    @classmethod
    def _strict_relationship_flags(cls, value: Any) -> bool:
        if not isinstance(value, bool):
            raise ValueError("relationship target inclusion flags must be booleans")
        return value

    @field_validator("moving_bodies", "target_names", "aspect_names")
    @classmethod
    def _unique_names(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        if any(not isinstance(item, str) or not item.strip() or item != item.strip() for item in value):
            raise ValueError("forecast names must be non-empty trimmed strings")
        if len(set(value)) != len(value):
            raise ValueError("forecast names must be unique")
        return value

    @model_validator(mode="after")
    def _bounded_window(self) -> "_RelationshipTransitRequest":
        if self.jd_end <= self.jd_start:
            raise ValueError("jd_end must be greater than jd_start")
        if self.jd_end - self.jd_start > 36_525.0:
            raise ValueError("relationship transit windows may not exceed 36525 days")
        return self


class CompositeTransitRequest(_RelationshipTransitRequest):
    chart: CompositeChartRequest


class DavisonTransitRequest(_RelationshipTransitRequest):
    chart: DavisonChartRequest


class RelationshipChartIdentityResponse(_StrictModel):
    chart_id: str
    chart_kind: str
    method: str
    epoch_jd_ut: float
    includes_house_frame: bool
    relation_basis: str
    geometry_sha256: str
    construction_truth: (
        CompositeComputationTruthResponse | DavisonComputationTruthResponse
    )
    reference_latitude: float | None = None
    reference_longitude: float | None = None
    correction_mode: str | None = None
    reference_frame: str
    timescale: str


class RelationshipTransitTargetResponse(_StrictModel):
    chart_id: str
    name: str
    target_kind: str
    longitude: float
    source_path: str


class RelationshipChartTargetSetResponse(_StrictModel):
    identity: RelationshipChartIdentityResponse
    targets: list[RelationshipTransitTargetResponse]
    target_count: int


class RelationshipTransitEventResponse(_StrictModel):
    chart_id: str
    target: RelationshipTransitTargetResponse
    moving_body: str
    aspect_name: str
    aspect_symbol: str
    aspect_angle_deg: float
    directional_offset_deg: float
    jd_exact: float
    direction: str
    perfection_longitude: float
    transit: TransitEventResponse
    event_source: str
    orb_boundaries_computed: bool
    interpretation: str


class RelationshipTransitSearchTruthResponse(_StrictModel):
    chart_id: str
    moving_bodies: list[str]
    target_names: list[str]
    tier: int
    aspect_names: list[str]
    jd_start: float
    jd_end: float
    step_days: float | None = None
    policy_step_days_override: float | None = None
    solver_tolerance_days: float
    step_policy: str
    transit_policy_source: str
    direction: str
    search_motion: str
    search_call_count: int
    event_count: int
    event_source: str
    target_motion: str
    event_kind: str
    orb_window_policy: str
    interpretation: str


class RelationshipTransitSearchResponse(_StrictModel):
    target_set: RelationshipChartTargetSetResponse
    events: list[RelationshipTransitEventResponse]
    computation_truth: RelationshipTransitSearchTruthResponse
    event_count: int


class FixedStarAstrocartographyRequest(_StrictModel):
    star_names: list[str] = Field(min_length=1, max_length=16)
    jd_ut: float
    jd_tt: float
    lat_step: float = Field(default=2.0, ge=0.5, le=178.0)
    refraction: bool = False

    @field_validator("star_names")
    @classmethod
    def _unique_star_names(cls, value: list[str]) -> list[str]:
        if any(not name.strip() or name != name.strip() for name in value):
            raise ValueError("star names must be non-empty trimmed strings")
        if len(set(value)) != len(value):
            raise ValueError("star names must be unique")
        return value

    @field_validator("jd_ut", "jd_tt", "lat_step", mode="before")
    @classmethod
    def _finite_values(cls, value: Any) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("fixed-star ACG values must be finite numbers")
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError("fixed-star ACG values must be finite numbers")
        return parsed

    @field_validator("refraction", mode="before")
    @classmethod
    def _strict_fixed_star_refraction(cls, value: Any) -> bool:
        if not isinstance(value, bool):
            raise ValueError("refraction must be a boolean")
        return value


class FixedStarAstrocartographySubjectResponse(_StrictModel):
    requested_name: str
    canonical_name: str
    nomenclature: str
    constellation: str | None = None
    source_kind: str
    lookup_kind: str
    hipparcos_name: str | None = None
    source_mode: str
    gaia_match_status: str
    gaia_source_index: int | None = None
    merge_state: str
    observer_mode: str
    relation_kind: str
    relation_basis: str
    true_position: bool
    dedup_applied: bool
    is_topocentric: bool
    longitude: float
    latitude: float
    right_ascension: float
    declination: float
    magnitude: float
    position_source: str


class FixedStarAstrocartographyTruthResponse(_StrictModel):
    requested_names: list[str]
    canonical_names: list[str]
    jd_ut: float
    jd_tt: float
    apparent_sidereal_time_deg: float
    true_obliquity_deg: float
    nutation_longitude_deg: float
    lat_step: float
    refraction: bool
    coordinate_frame: str
    star_position_source: str
    equatorial_conversion_source: str
    line_geometry_source: str
    point_geometry_source: str
    interpretation: str


class FixedStarAstrocartographyResponse(_StrictModel):
    subjects: list[FixedStarAstrocartographySubjectResponse]
    lines: list[AstrocartographyLineResponse]
    subplanetary_points: list[AstrocartographySubplanetaryPointResponse]
    computation_truth: FixedStarAstrocartographyTruthResponse


class DynamicAstrocartographyRequest(_StrictModel):
    epochs_jd_ut: list[float] = Field(min_length=1, max_length=32)
    bodies: list[str] = Field(min_length=1, max_length=4)
    observer_latitude: float = Field(ge=-90.0, le=90.0)
    observer_longitude: float = Field(ge=-180.0, le=180.0)
    observer_elevation_m: float = 0.0
    lat_step: float = Field(default=2.0, ge=0.5, le=178.0)
    refraction: bool = False

    @field_validator(
        "epochs_jd_ut",
        "observer_latitude",
        "observer_longitude",
        "observer_elevation_m",
        "lat_step",
        mode="before",
    )
    @classmethod
    def _finite_dynamic_values(cls, value: Any) -> Any:
        values = value if isinstance(value, list) else [value]
        if any(
            isinstance(item, bool)
            or not isinstance(item, (int, float))
            or not math.isfinite(float(item))
            for item in values
        ):
            raise ValueError("dynamic ACG values must be finite numbers")
        parsed = [float(item) for item in values]
        return parsed if isinstance(value, list) else parsed[0]

    @field_validator("bodies")
    @classmethod
    def _unique_bodies(cls, value: list[str]) -> list[str]:
        if any(not body.strip() or body != body.strip() for body in value):
            raise ValueError("dynamic ACG bodies must be non-empty trimmed strings")
        if len(set(value)) != len(value):
            raise ValueError("dynamic ACG bodies must be unique")
        return value

    @field_validator("refraction", mode="before")
    @classmethod
    def _strict_dynamic_refraction(cls, value: Any) -> bool:
        if not isinstance(value, bool):
            raise ValueError("refraction must be a boolean")
        return value

    @model_validator(mode="after")
    def _increasing_epochs(self) -> "DynamicAstrocartographyRequest":
        if any(
            later <= earlier
            for earlier, later in zip(self.epochs_jd_ut, self.epochs_jd_ut[1:])
        ):
            raise ValueError("dynamic ACG epochs must be strictly increasing")
        return self


class DynamicAstrocartographyPositionResponse(_StrictModel):
    body: str
    right_ascension: float
    declination: float
    position_source: str


class DynamicAstrocartographySnapshotTruthResponse(_StrictModel):
    jd_ut: float
    jd_tt: float
    bodies: list[str]
    observer_latitude: float
    observer_longitude: float
    observer_elevation_m: float
    apparent_sidereal_time_deg: float
    true_obliquity_deg: float
    nutation_longitude_deg: float
    lat_step: float
    refraction: bool
    mode: str
    coordinate_frame: str
    timescale: str
    line_geometry_source: str
    interpretation: str


class DynamicAstrocartographySnapshotResponse(_StrictModel):
    positions: list[DynamicAstrocartographyPositionResponse]
    lines: list[AstrocartographyLineResponse]
    computation_truth: DynamicAstrocartographySnapshotTruthResponse
    jd_ut: float


class AstrocartographyCurvePointShiftResponse(_StrictModel):
    latitude: float
    source_longitude: float
    target_longitude: float
    signed_delta_deg: float


class DynamicAstrocartographyLineTransitionResponse(_StrictModel):
    body: str
    line_type: str
    source_jd_ut: float
    target_jd_ut: float
    source_meridian_longitude: float | None = None
    target_meridian_longitude: float | None = None
    meridian_signed_delta_deg: float | None = None
    curve_point_shifts: list[AstrocartographyCurvePointShiftResponse]
    source_only_latitudes: list[float]
    target_only_latitudes: list[float]


class DynamicAstrocartographySeriesTruthResponse(_StrictModel):
    mode: str
    epochs_jd_ut: list[float]
    bodies: list[str]
    snapshot_count: int
    transition_count: int
    epoch_policy: str
    comparison_policy: str
    progressed_mode: str
    directed_mode: str
    interpretation: str


class DynamicAstrocartographyResponse(_StrictModel):
    snapshots: list[DynamicAstrocartographySnapshotResponse]
    transitions: list[DynamicAstrocartographyLineTransitionResponse]
    computation_truth: DynamicAstrocartographySeriesTruthResponse


class RelocatedReturnRequest(_StrictModel):
    return_kind: Literal["solar_return", "lunar_return", "planetary_return"]
    natal_longitude: float
    body: str | None = None
    year: int | None = None
    jd_start: float | None = None
    direction: Literal["direct", "retrograde", "either"] = "direct"
    source_latitude: float = Field(ge=-90.0, le=90.0)
    source_longitude: float = Field(ge=-180.0, le=180.0)
    relocated_latitude: float = Field(ge=-90.0, le=90.0)
    relocated_longitude: float = Field(ge=-180.0, le=180.0)
    source_house_system: str = HouseSystem.PLACIDUS
    relocated_house_system: str | None = None
    bodies: list[str] | None = Field(default=None, min_length=1, max_length=16)
    step_days: float | None = Field(default=None, ge=0.01)
    solver_tolerance_days: float | None = Field(default=None, gt=0.0)
    house_policy: HousePolicyRequest | None = None

    @field_validator(
        "natal_longitude",
        "jd_start",
        "source_latitude",
        "source_longitude",
        "relocated_latitude",
        "relocated_longitude",
        "step_days",
        "solver_tolerance_days",
        mode="before",
    )
    @classmethod
    def _finite_return_values(cls, value: Any) -> Any:
        if value is None:
            return value
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("relocated-return values must be finite numbers")
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError("relocated-return values must be finite numbers")
        return parsed

    @field_validator("year", mode="before")
    @classmethod
    def _strict_year(cls, value: Any) -> Any:
        if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
            raise ValueError("year must be an integer")
        return value

    @field_validator("body")
    @classmethod
    def _trimmed_body(cls, value: str | None) -> str | None:
        if value is not None and (not value.strip() or value != value.strip()):
            raise ValueError("body must be a non-empty trimmed string")
        return value

    @field_validator("source_house_system", "relocated_house_system")
    @classmethod
    def _trimmed_house_system(cls, value: str | None) -> str | None:
        if value is not None and (not value.strip() or value != value.strip()):
            raise ValueError("house systems must be non-empty trimmed strings")
        return value

    @field_validator("bodies")
    @classmethod
    def _unique_chart_bodies(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        if any(not body.strip() or body != body.strip() for body in value):
            raise ValueError("chart bodies must be non-empty trimmed strings")
        if len(set(value)) != len(value):
            raise ValueError("chart bodies must be unique")
        return value

    @model_validator(mode="after")
    def _return_selector(self) -> "RelocatedReturnRequest":
        if self.return_kind == "solar_return":
            if self.year is None or self.jd_start is not None:
                raise ValueError("solar_return requires year and forbids jd_start")
            if self.body not in (None, "Sun") or self.direction != "direct":
                raise ValueError("solar_return is a direct Sun return")
        elif self.return_kind == "lunar_return":
            if self.jd_start is None or self.year is not None:
                raise ValueError("lunar_return requires jd_start and forbids year")
            if self.body not in (None, "Moon") or self.direction != "direct":
                raise ValueError("lunar_return is a direct Moon return")
        else:
            if self.body is None or self.jd_start is None or self.year is not None:
                raise ValueError("planetary_return requires body and jd_start and forbids year")
        return self


class ChartContextResponse(_StrictModel):
    jd_ut: float
    jd_tt: float
    latitude: float
    longitude: float
    planets: dict[str, PlanetPositionResponse]
    nodes: dict[str, NodePositionResponse]
    houses: HousesResponse
    is_day: bool


class ReturnMomentTruthResponse(_StrictModel):
    return_kind: str
    body: str
    natal_longitude: float
    jd_return_ut: float
    direction: str
    timing_source: str
    search_policy: "ReturnSearchPolicyTruthResponse"
    year: int | None = None
    search_start_jd_ut: float | None = None
    reference_frame: str
    timescale: str


class ReturnSearchPolicyTruthResponse(_StrictModel):
    step_days_override: float | None = None
    default_max_days: float | None = None
    per_body_max_days: list[tuple[str, float]]
    solver_tolerance_days: float
    policy_source: str


class ReturnRelocationTruthResponse(_StrictModel):
    source_latitude: float
    source_longitude: float
    relocated_latitude: float
    relocated_longitude: float
    source_requested_house_system: str
    source_effective_house_system: str
    source_house_fallback: bool
    relocated_requested_house_system: str
    relocated_effective_house_system: str
    relocated_house_fallback: bool
    same_epoch: bool
    same_celestial_snapshot: bool
    chart_source: str
    relocation_source: str
    interpretation: str


class RelocatedReturnResponse(_StrictModel):
    source_chart: ChartContextResponse
    relocated_chart: ChartContextResponse
    return_truth: ReturnMomentTruthResponse
    relocation_truth: ReturnRelocationTruthResponse


__all__ = [
    "AstrocartographyCurvePointShiftResponse",
    "ChartContextResponse",
    "CompositeTransitRequest",
    "DavisonTransitRequest",
    "DynamicAstrocartographyLineTransitionResponse",
    "DynamicAstrocartographyPositionResponse",
    "DynamicAstrocartographyRequest",
    "DynamicAstrocartographyResponse",
    "DynamicAstrocartographySeriesTruthResponse",
    "DynamicAstrocartographySnapshotResponse",
    "DynamicAstrocartographySnapshotTruthResponse",
    "FixedStarAstrocartographyRequest",
    "FixedStarAstrocartographyResponse",
    "FixedStarAstrocartographySubjectResponse",
    "FixedStarAstrocartographyTruthResponse",
    "RelocatedReturnRequest",
    "RelocatedReturnResponse",
    "RelationshipChartIdentityResponse",
    "RelationshipChartTargetSetResponse",
    "RelationshipTransitEventResponse",
    "RelationshipTransitSearchResponse",
    "RelationshipTransitSearchTruthResponse",
    "RelationshipTransitTargetResponse",
    "ReturnMomentTruthResponse",
    "ReturnSearchPolicyTruthResponse",
    "ReturnRelocationTruthResponse",
]


ReturnMomentTruthResponse.model_rebuild()
