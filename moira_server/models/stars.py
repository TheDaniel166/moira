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
