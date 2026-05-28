"""Transport models for visibility endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LunarCrescentDetailsResponse(_StrictModel):
    best_time_jd_ut: float
    sunset_jd_ut: float
    moonset_jd_ut: float
    lag_minutes: float
    arcl_deg: float
    arcv_deg: float
    daz_deg: float
    moon_altitude_deg: float
    sun_altitude_deg: float
    lunar_parallax_arcmin: float
    topocentric_crescent_width_arcmin: float
    q: float
    visibility_class: str


class VisibilityAssessmentRequest(_StrictModel):
    body: str
    jd_ut: float
    lat: float
    lon: float


class VisibilityAssessmentResponse(_StrictModel):
    body: str
    jd_ut: float
    criterion_family: str
    effective_limiting_magnitude: float
    apparent_magnitude: float
    true_altitude_deg: float
    apparent_altitude_deg: float
    local_horizon_altitude_deg: float
    solar_elongation_deg: float
    is_geometrically_visible: bool
    is_bright_enough: bool
    observable: bool
    lunar_crescent_details: LunarCrescentDetailsResponse | None = None
    moonlight_sky_nanolamberts: float | None = None


__all__ = [
    "LunarCrescentDetailsResponse",
    "VisibilityAssessmentRequest",
    "VisibilityAssessmentResponse",
]
