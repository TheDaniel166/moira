"""Serializers for visibility vessels."""

from __future__ import annotations

from moira.heliacal import (
    AtmosphericExtinctionAssessment,
    LunarCrescentDetails,
    PhysicalVisibilityAssessment,
    PhysicalVisibilityEventResult,
    PointSourceVisibilityThreshold,
    TwilightSkyBrightnessAssessment,
    VisibilityAssessment,
)

from ..models.visibility import (
    AtmosphericExtinctionResponse,
    LunarCrescentDetailsResponse,
    PhysicalVisibilityAssessmentResponse,
    PhysicalVisibilityEventResponse,
    PointSourceVisibilityThresholdResponse,
    TwilightSkyBrightnessResponse,
    VisibilityAssessmentResponse,
)


def serialize_lunar_crescent_details(
    details: LunarCrescentDetails,
) -> LunarCrescentDetailsResponse:
    return LunarCrescentDetailsResponse(
        best_time_jd_ut=details.best_time_jd_ut,
        sunset_jd_ut=details.sunset_jd_ut,
        moonset_jd_ut=details.moonset_jd_ut,
        lag_minutes=details.lag_minutes,
        arcl_deg=details.arcl_deg,
        arcv_deg=details.arcv_deg,
        daz_deg=details.daz_deg,
        moon_altitude_deg=details.moon_altitude_deg,
        sun_altitude_deg=details.sun_altitude_deg,
        lunar_parallax_arcmin=details.lunar_parallax_arcmin,
        topocentric_crescent_width_arcmin=details.topocentric_crescent_width_arcmin,
        q=details.q,
        visibility_class=details.visibility_class.value,
    )


def serialize_atmospheric_extinction(
    assessment: AtmosphericExtinctionAssessment,
) -> AtmosphericExtinctionResponse:
    return AtmosphericExtinctionResponse(
        model=assessment.model.value,
        apparent_altitude_deg=assessment.apparent_altitude_deg,
        zenith_distance_deg=assessment.zenith_distance_deg,
        broadband_airmass=assessment.broadband_airmass,
        rayleigh_airmass=assessment.rayleigh_airmass,
        aerosol_airmass=assessment.aerosol_airmass,
        ozone_airmass=assessment.ozone_airmass,
        rayleigh_coefficient_mag_per_airmass=(
            assessment.rayleigh_coefficient_mag_per_airmass
        ),
        aerosol_coefficient_mag_per_airmass=(
            assessment.aerosol_coefficient_mag_per_airmass
        ),
        ozone_coefficient_mag_per_airmass=(
            assessment.ozone_coefficient_mag_per_airmass
        ),
        total_zenith_extinction_coefficient=(
            assessment.total_zenith_extinction_coefficient
        ),
        sky_brightness_extinction_coefficient=(
            assessment.sky_brightness_extinction_coefficient
        ),
        extinction_magnitude=assessment.extinction_magnitude,
        transmission_fraction=assessment.transmission_fraction,
    )


def serialize_twilight_sky_brightness(
    assessment: TwilightSkyBrightnessAssessment,
) -> TwilightSkyBrightnessResponse:
    return TwilightSkyBrightnessResponse(
        model=assessment.model.value,
        target_altitude_deg=assessment.target_altitude_deg,
        sun_altitude_deg=assessment.sun_altitude_deg,
        sun_target_separation_deg=assessment.sun_target_separation_deg,
        sky_airmass=assessment.sky_airmass,
        extinction_coefficient=assessment.extinction_coefficient,
        formula_applied=assessment.formula_applied,
        valid=assessment.valid,
        reason=assessment.reason,
        sky_nanolamberts=assessment.sky_nanolamberts,
    )


def serialize_point_source_visibility_threshold(
    threshold: PointSourceVisibilityThreshold,
) -> PointSourceVisibilityThresholdResponse:
    return PointSourceVisibilityThresholdResponse(
        criterion_family=threshold.criterion_family.value,
        background_nanolamberts=threshold.background_nanolamberts,
        background_luminance_cd_m2=threshold.background_luminance_cd_m2,
        field_factor=threshold.field_factor,
        valid_background_min_cd_m2=threshold.valid_background_min_cd_m2,
        valid_background_max_cd_m2=threshold.valid_background_max_cd_m2,
        valid=threshold.valid,
        reason=threshold.reason,
        limiting_magnitude=threshold.limiting_magnitude,
    )


def serialize_visibility_assessment(
    assessment: VisibilityAssessment,
) -> VisibilityAssessmentResponse:
    return VisibilityAssessmentResponse(
        body=assessment.body,
        jd_ut=assessment.jd_ut,
        criterion_family=assessment.criterion_family.value,
        effective_limiting_magnitude=assessment.effective_limiting_magnitude,
        apparent_magnitude=assessment.apparent_magnitude,
        true_altitude_deg=assessment.true_altitude_deg,
        apparent_altitude_deg=assessment.apparent_altitude_deg,
        local_horizon_altitude_deg=assessment.local_horizon_altitude_deg,
        solar_elongation_deg=assessment.solar_elongation_deg,
        is_geometrically_visible=assessment.is_geometrically_visible,
        is_bright_enough=assessment.is_bright_enough,
        observable=assessment.observable,
        lunar_crescent_details=(
            serialize_lunar_crescent_details(assessment.lunar_crescent_details)
            if assessment.lunar_crescent_details is not None
            else None
        ),
        moonlight_sky_nanolamberts=assessment.moonlight_sky_nanolamberts,
        extinction_adjusted_magnitude=assessment.extinction_adjusted_magnitude,
        visibility_margin_magnitude=assessment.visibility_margin_magnitude,
        criterion_target_magnitude=assessment.criterion_target_magnitude,
        target_extinction_applied_separately=(
            assessment.target_extinction_applied_separately
        ),
        criterion_applicable=assessment.criterion_applicable,
        criterion_reason=assessment.criterion_reason,
        atmospheric_extinction=(
            serialize_atmospheric_extinction(assessment.atmospheric_extinction)
            if assessment.atmospheric_extinction is not None
            else None
        ),
        twilight_sky_brightness=(
            serialize_twilight_sky_brightness(
                assessment.twilight_sky_brightness
            )
            if assessment.twilight_sky_brightness is not None
            else None
        ),
        point_source_threshold=(
            serialize_point_source_visibility_threshold(
                assessment.point_source_threshold
            )
            if assessment.point_source_threshold is not None
            else None
        ),
        dark_sky_nanolamberts=assessment.dark_sky_nanolamberts,
        total_sky_nanolamberts=assessment.total_sky_nanolamberts,
    )


def serialize_physical_visibility_assessment(
    assessment: PhysicalVisibilityAssessment,
) -> PhysicalVisibilityAssessmentResponse:
    return PhysicalVisibilityAssessmentResponse.model_validate(assessment)


def serialize_physical_visibility_event(
    event: PhysicalVisibilityEventResult,
) -> PhysicalVisibilityEventResponse:
    return PhysicalVisibilityEventResponse.model_validate(event)


__all__ = [
    "serialize_lunar_crescent_details",
    "serialize_atmospheric_extinction",
    "serialize_twilight_sky_brightness",
    "serialize_point_source_visibility_threshold",
    "serialize_visibility_assessment",
    "serialize_physical_visibility_assessment",
    "serialize_physical_visibility_event",
]
