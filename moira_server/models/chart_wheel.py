"""Website-only chart-wheel primitive transport models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .chart import ChartRequest, ChartResponse, HousePolicyResponse, HousesResponse


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ChartWheelHousesRequest(_StrictModel):
    latitude: float = Field(ge=-90.0, le=90.0, allow_inf_nan=False)
    longitude: float = Field(ge=-180.0, le=180.0, allow_inf_nan=False)
    system: str | None = None


class ChartWheelConfig(_StrictModel):
    orientation: str = "aries_left"
    preset: str = "classic"
    include_aspects: bool = True
    aspect_tier: int | None = 0
    orb_factor: float = 1.0
    include_nodes: bool = True
    glyph_set: str = "unicode"
    label_mode: str = "standard"
    collision_orb_deg: float = Field(default=3.0, ge=0.0, le=30.0)
    zodiac_radius: float = Field(default=1.0, gt=0.0)
    house_radius: float = Field(default=0.86, gt=0.0)
    point_radius: float = Field(default=0.72, gt=0.0)
    label_radius: float = Field(default=0.82, gt=0.0)
    aspect_radius: float = Field(default=0.52, gt=0.0)
    min_label_separation_deg: float = Field(default=4.0, ge=0.0, le=45.0)


class ChartWheelPacketRequest(_StrictModel):
    chart: ChartRequest
    houses: ChartWheelHousesRequest | None = None
    config: ChartWheelConfig = Field(default_factory=ChartWheelConfig)


class ChartWheelCoordinateResponse(_StrictModel):
    x: float
    y: float


class ChartWheelZodiacSegmentResponse(_StrictModel):
    sign: str
    sign_symbol: str
    start_longitude: float
    end_longitude: float
    start_angle_deg: float
    end_angle_deg: float
    radius: float


class ChartWheelHouseCuspPrimitiveResponse(_StrictModel):
    house: int
    longitude: float
    angle_deg: float
    radius: float
    endpoint: ChartWheelCoordinateResponse


class ChartWheelHouseSectorPrimitiveResponse(_StrictModel):
    house: int
    start_longitude: float
    end_longitude: float
    start_angle_deg: float
    end_angle_deg: float
    radius: float


class ChartWheelPointPrimitiveResponse(_StrictModel):
    key: str
    kind: str
    longitude: float
    angle_deg: float
    radius: float
    position: ChartWheelCoordinateResponse
    label_angle_deg: float
    label_position: ChartWheelCoordinateResponse
    label_displacement_deg: float
    label: str
    glyph: str
    sign: str
    sign_symbol: str
    sign_degree: float
    retrograde: bool | None = None
    house: int | None = None
    collision_group: int | None = None
    label_priority: int
    hidden_label: bool = False


class ChartWheelAspectPrimitiveResponse(_StrictModel):
    body1: str
    body2: str
    aspect: str
    symbol: str
    angle: float
    orb: float
    allowed_orb: float
    classification_tier: str | None = None
    family: str | None = None
    stroke_key: str
    applying: bool | None = None
    start: ChartWheelCoordinateResponse
    end: ChartWheelCoordinateResponse


class ChartWheelCollisionGroupResponse(_StrictModel):
    group_id: int
    members: list[str]
    center_longitude: float
    label_lane: int


class ChartWheelStylePresetResponse(_StrictModel):
    name: str
    description: str
    config: ChartWheelConfig


class ChartWheelConfigValidationRequest(_StrictModel):
    config: ChartWheelConfig


class ChartWheelConfigWarningResponse(_StrictModel):
    code: str
    message: str
    severity: str


class ChartWheelConfigValidationResponse(_StrictModel):
    valid: bool
    normalized_config: ChartWheelConfig
    warnings: list[ChartWheelConfigWarningResponse]


class ChartWheelNodeSelectionTruthResponse(_StrictModel):
    chart_requested_include_nodes: bool
    config_requested_include_nodes: bool
    effective_include_nodes: bool
    config_override_applied: bool


class ChartWheelHousePolicyTruthResponse(_StrictModel):
    houses_requested: bool
    requested_system: str | None = None
    effective_system: str | None = None
    fallback_applied: bool | None = None
    fallback_reason: str | None = None
    applied_policy: HousePolicyResponse | None = None


class ChartWheelOrientationTruthResponse(_StrictModel):
    requested_orientation: str
    source: Literal["fixed_aries", "house_ascendant"]
    anchor_longitude_deg: float
    offset_deg: float


class ChartWheelAspectPolicyTruthResponse(_StrictModel):
    include_aspects_requested: bool
    included: bool
    tier: int | None = None
    orb_factor: float
    positions_include_nodes: bool
    returned_count: int


class ChartWheelLabelPlacementTruthResponse(_StrictModel):
    mode: str
    algorithm: Literal["hidden", "identity", "cyclic_weighted_forward_pack_v1"]
    requested_minimum_separation_deg: float
    effective_minimum_separation_deg: float
    achieved_minimum_separation_deg: float | None = None
    requested_constraint_satisfied: bool
    collision_threshold_deg: float
    labels_considered: int
    labels_displaced: int
    max_absolute_displacement_deg: float
    point_coordinates_preserved: bool = True


class ChartWheelComputationTruthResponse(_StrictModel):
    source_module: Literal["moira_server.services.chart_wheel"] = (
        "moira_server.services.chart_wheel"
    )
    assembly_entrypoint: Literal["compute_chart_wheel_packet"] = (
        "compute_chart_wheel_packet"
    )
    chart_engine_entrypoint: Literal["Moira.chart"] = "Moira.chart"
    house_engine_entrypoint: Literal["Moira.houses"] | None = None
    source_vessel: Literal["ChartWheelPacketResponse"] = "ChartWheelPacketResponse"
    node_selection: ChartWheelNodeSelectionTruthResponse
    houses: ChartWheelHousePolicyTruthResponse
    orientation: ChartWheelOrientationTruthResponse
    aspects: ChartWheelAspectPolicyTruthResponse
    label_placement: ChartWheelLabelPlacementTruthResponse


class ChartWheelPacketResponse(_StrictModel):
    chart: ChartResponse
    houses: HousesResponse | None = None
    config: ChartWheelConfig
    orientation_offset_deg: float
    warnings: list[ChartWheelConfigWarningResponse]
    zodiac: list[ChartWheelZodiacSegmentResponse]
    house_cusps: list[ChartWheelHouseCuspPrimitiveResponse]
    house_sectors: list[ChartWheelHouseSectorPrimitiveResponse]
    points: list[ChartWheelPointPrimitiveResponse]
    aspects: list[ChartWheelAspectPrimitiveResponse]
    collision_groups: list[ChartWheelCollisionGroupResponse]
    computation_truth: ChartWheelComputationTruthResponse


__all__ = [
    "ChartWheelAspectPrimitiveResponse",
    "ChartWheelCollisionGroupResponse",
    "ChartWheelComputationTruthResponse",
    "ChartWheelConfig",
    "ChartWheelConfigValidationRequest",
    "ChartWheelConfigValidationResponse",
    "ChartWheelConfigWarningResponse",
    "ChartWheelCoordinateResponse",
    "ChartWheelHousesRequest",
    "ChartWheelHouseCuspPrimitiveResponse",
    "ChartWheelHouseSectorPrimitiveResponse",
    "ChartWheelHousePolicyTruthResponse",
    "ChartWheelLabelPlacementTruthResponse",
    "ChartWheelNodeSelectionTruthResponse",
    "ChartWheelOrientationTruthResponse",
    "ChartWheelAspectPolicyTruthResponse",
    "ChartWheelPacketRequest",
    "ChartWheelPacketResponse",
    "ChartWheelPointPrimitiveResponse",
    "ChartWheelStylePresetResponse",
    "ChartWheelZodiacSegmentResponse",
]
