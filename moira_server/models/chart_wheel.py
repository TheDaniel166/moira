"""Website-only chart-wheel primitive transport models."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .chart import ChartRequest, ChartResponse, HousesResponse


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ChartWheelHousesRequest(_StrictModel):
    latitude: float
    longitude: float
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
    label_position: ChartWheelCoordinateResponse
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


__all__ = [
    "ChartWheelAspectPrimitiveResponse",
    "ChartWheelCollisionGroupResponse",
    "ChartWheelConfig",
    "ChartWheelConfigValidationRequest",
    "ChartWheelConfigValidationResponse",
    "ChartWheelConfigWarningResponse",
    "ChartWheelCoordinateResponse",
    "ChartWheelHousesRequest",
    "ChartWheelHouseCuspPrimitiveResponse",
    "ChartWheelHouseSectorPrimitiveResponse",
    "ChartWheelPacketRequest",
    "ChartWheelPacketResponse",
    "ChartWheelPointPrimitiveResponse",
    "ChartWheelStylePresetResponse",
    "ChartWheelZodiacSegmentResponse",
]
