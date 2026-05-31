"""Transport models for comet endpoints (Phase 11 small-body fast API)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CometPositionRequest(_StrictModel):
    dt: datetime
    body: str | int


class CometPositionResponse(_StrictModel):
    name: str
    naif_id: int
    longitude: float
    latitude: float
    distance: float
    speed: float
    retrograde: bool
    sign: str
    sign_symbol: str
    sign_degree: float
    is_sovereign: bool = False

    # Velocity for proper motion approximation
    velocity_x: float | None = None
    velocity_y: float | None = None
    velocity_z: float | None = None
    # Magnitude not available in basic comet position calls.


class CometsBulkRequest(_StrictModel):
    dt: datetime
    bodies: list[str | int]
    skip_missing: bool = True


class CometsBulkResponse(_StrictModel):
    dt: datetime
    results: dict[str, CometPositionResponse]
    missing: list[str] = []
    sovereign_used: bool = False
