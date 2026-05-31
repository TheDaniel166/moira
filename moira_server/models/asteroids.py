"""Transport models for asteroid/comet endpoints (Phase 11 small-body surfaces).

These are designed for high-performance website use:
- Leverage native Type 13 + sovereign small-body kernels for speed when available.
- Support single and bulk queries.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AsteroidPositionRequest(_StrictModel):
    """Request for a single asteroid geocentric ecliptic position."""
    dt: datetime
    body: str | int  # name or NAIF ID
    # Future: observer for topocentric, but start simple for website


class AsteroidPositionResponse(_StrictModel):
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
    is_sovereign: bool = False   # True if served from fast native Type 13 sovereign path

    # Additional fields for website (proper motion approximation from velocity)
    velocity_x: float | None = None  # km/s (ecliptic)
    velocity_y: float | None = None
    velocity_z: float | None = None
    # Note: Magnitude (V) requires additional catalog data (H/G params) and is not
    #       currently computed by the basic position functions.


class AsteroidsBulkRequest(_StrictModel):
    """Fast bulk request for many asteroids at the same time (website-friendly)."""
    dt: datetime
    bodies: list[str | int]
    skip_missing: bool = True


class AsteroidsBulkResponse(_StrictModel):
    dt: datetime
    results: dict[str, AsteroidPositionResponse]  # keyed by requested name/naif
    missing: list[str] = []
    sovereign_used: bool = False
