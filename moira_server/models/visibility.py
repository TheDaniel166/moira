"""Transport models for the explicit observational-visibility surface."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from moira.heliacal import (
    LightPollutionClass,
    LightPollutionDerivationMode,
    MoonlightPolicy,
    ObserverAid,
    VisibilityCriterionFamily,
    VisibilityExtinctionModel,
    VisibilityTwilightModel,
)


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


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


class ObserverVisibilityEnvironmentRequest(_StrictModel):
    light_pollution_class: LightPollutionClass | None = LightPollutionClass.BORTLE_3
    limiting_magnitude: float | None = None
    sky_surface_brightness_mag_arcsec2: float | None = Field(default=None, gt=0.0)
    local_horizon_altitude_deg: float = Field(default=0.0, ge=-90.0, le=90.0)
    temperature_c: float = 10.0
    pressure_mbar: float = Field(default=1013.25, ge=0.0)
    relative_humidity: float = Field(default=0.5, ge=0.0, le=1.0)
    observer_altitude_m: float = Field(default=0.0, ge=-1000.0)
    observing_aid: ObserverAid = ObserverAid.NAKED_EYE


class VisibilityPolicyRequest(_StrictModel):
    criterion_family: VisibilityCriterionFamily = (
        VisibilityCriterionFamily.LIMITING_MAGNITUDE_THRESHOLD
    )
    environment: ObserverVisibilityEnvironmentRequest | None = None
    light_pollution_derivation_mode: LightPollutionDerivationMode = (
        LightPollutionDerivationMode.BORTLE_LINEAR
    )
    extinction_model: VisibilityExtinctionModel = (
        VisibilityExtinctionModel.LEGACY_ARCUS_VISIONIS
    )
    twilight_model: VisibilityTwilightModel = (
        VisibilityTwilightModel.ARCUS_VISIONIS_SOLAR_DEPRESSION
    )
    use_refraction: bool = True
    moonlight_policy: MoonlightPolicy = MoonlightPolicy.IGNORE
    extinction_coefficient_k: float = Field(default=0.20, ge=0.0)
    crumey_field_factor: float = Field(default=2.0, gt=0.0)
    crumey_field_factor_includes_atmosphere: bool = True


class VisibilityAssessmentRequest(_StrictModel):
    body: str
    jd_ut: float
    lat: float = Field(ge=-90.0, le=90.0)
    lon: float = Field(ge=-180.0, le=180.0)
    policy: VisibilityPolicyRequest | None = None


class AtmosphericExtinctionRequest(_StrictModel):
    apparent_altitude_deg: float = Field(ge=0.0, le=90.0)
    model: Literal[
        VisibilityExtinctionModel.KASTEN_YOUNG_1989_BROADBAND,
        VisibilityExtinctionModel.SCHAEFER_1993_COMPONENTS,
    ]
    extinction_coefficient_k: float = Field(default=0.20, ge=0.0)
    observer_altitude_m: float = Field(default=0.0, ge=-1000.0)
    relative_humidity: float = Field(default=0.5, ge=0.0, le=1.0)
    observer_latitude_deg: float = Field(default=0.0, ge=-90.0, le=90.0)
    sun_right_ascension_deg: float = 0.0


class TwilightSkyBrightnessRequest(_StrictModel):
    target_altitude_deg: float = Field(ge=0.0, le=90.0)
    sun_altitude_deg: float
    sun_target_separation_deg: float = Field(ge=0.0, le=180.0)
    extinction_coefficient_k: float = Field(default=0.20, ge=0.0)


class PointSourceVisibilityThresholdRequest(_StrictModel):
    background_nanolamberts: float = Field(gt=0.0)
    field_factor: float = Field(default=2.0, gt=0.0)


class AtmosphericExtinctionResponse(_StrictModel):
    model: str
    apparent_altitude_deg: float
    zenith_distance_deg: float
    broadband_airmass: float | None
    rayleigh_airmass: float | None
    aerosol_airmass: float | None
    ozone_airmass: float | None
    rayleigh_coefficient_mag_per_airmass: float | None
    aerosol_coefficient_mag_per_airmass: float | None
    ozone_coefficient_mag_per_airmass: float | None
    total_zenith_extinction_coefficient: float
    sky_brightness_extinction_coefficient: float
    extinction_magnitude: float
    transmission_fraction: float


class TwilightSkyBrightnessResponse(_StrictModel):
    model: str
    target_altitude_deg: float
    sun_altitude_deg: float
    sun_target_separation_deg: float
    sky_airmass: float
    extinction_coefficient: float
    formula_applied: bool
    valid: bool
    reason: str | None
    sky_nanolamberts: float | None


class PointSourceVisibilityThresholdResponse(_StrictModel):
    criterion_family: str
    background_nanolamberts: float
    background_luminance_cd_m2: float
    field_factor: float
    valid_background_min_cd_m2: float
    valid_background_max_cd_m2: float
    valid: bool
    reason: str | None
    limiting_magnitude: float | None


class VisibilityAssessmentResponse(_StrictModel):
    body: str
    jd_ut: float
    criterion_family: str
    effective_limiting_magnitude: float | None
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
    extinction_adjusted_magnitude: float | None = None
    visibility_margin_magnitude: float | None = None
    criterion_target_magnitude: float | None = None
    target_extinction_applied_separately: bool = False
    criterion_applicable: bool = True
    criterion_reason: str | None = None
    atmospheric_extinction: AtmosphericExtinctionResponse | None = None
    twilight_sky_brightness: TwilightSkyBrightnessResponse | None = None
    point_source_threshold: PointSourceVisibilityThresholdResponse | None = None
    dark_sky_nanolamberts: float | None = None
    total_sky_nanolamberts: float | None = None


__all__ = [
    "LunarCrescentDetailsResponse",
    "ObserverVisibilityEnvironmentRequest",
    "VisibilityPolicyRequest",
    "VisibilityAssessmentRequest",
    "AtmosphericExtinctionRequest",
    "TwilightSkyBrightnessRequest",
    "PointSourceVisibilityThresholdRequest",
    "AtmosphericExtinctionResponse",
    "TwilightSkyBrightnessResponse",
    "PointSourceVisibilityThresholdResponse",
    "VisibilityAssessmentResponse",
]
