"""Serializers for visibility vessels."""

from __future__ import annotations

from moira.heliacal import LunarCrescentDetails, VisibilityAssessment

from ..models.visibility import (
    LunarCrescentDetailsResponse,
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
    )


__all__ = [
    "serialize_lunar_crescent_details",
    "serialize_visibility_assessment",
]
