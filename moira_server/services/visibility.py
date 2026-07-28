"""Phase-5 visibility service helpers."""

from __future__ import annotations

from moira import Moira
from moira.sky.visibility import (
    ObserverVisibilityEnvironment,
    VisibilityPolicy,
    atmospheric_extinction,
    directional_twilight_sky_brightness,
    point_source_visibility_threshold,
    visibility_assessment,
)
from moira.spk_reader import use_reader_override

from ..models.visibility import (
    AtmosphericExtinctionRequest,
    PointSourceVisibilityThresholdRequest,
    TwilightSkyBrightnessRequest,
    VisibilityAssessmentRequest,
    VisibilityPolicyRequest,
)


def visibility_policy_from_request(
    request: VisibilityPolicyRequest | None,
) -> VisibilityPolicy | None:
    if request is None:
        return None
    environment = (
        ObserverVisibilityEnvironment(**request.environment.model_dump())
        if request.environment is not None
        else None
    )
    values = request.model_dump(exclude={"environment"})
    return VisibilityPolicy(environment=environment, **values)


def compute_visibility_assessment(engine: Moira, request: VisibilityAssessmentRequest):
    policy = visibility_policy_from_request(request.policy)
    reader = getattr(engine, "_reader", None)
    with use_reader_override(reader):
        return visibility_assessment(
            request.body,
            request.jd_ut,
            request.lat,
            request.lon,
            policy=policy,
        )


def compute_visibility_tonight(engine: Moira, request: VisibilityAssessmentRequest):
    return engine.visibility_tonight(
        request.body,
        request.jd_ut,
        request.lat,
        request.lon,
        policy=visibility_policy_from_request(request.policy),
    )


def compute_atmospheric_extinction(request: AtmosphericExtinctionRequest):
    return atmospheric_extinction(
        request.apparent_altitude_deg,
        model=request.model,
        extinction_coefficient_k=request.extinction_coefficient_k,
        observer_altitude_m=request.observer_altitude_m,
        relative_humidity=request.relative_humidity,
        observer_latitude_deg=request.observer_latitude_deg,
        sun_right_ascension_deg=request.sun_right_ascension_deg,
    )


def compute_twilight_sky_brightness(request: TwilightSkyBrightnessRequest):
    return directional_twilight_sky_brightness(
        request.target_altitude_deg,
        request.sun_altitude_deg,
        request.sun_target_separation_deg,
        extinction_coefficient_k=request.extinction_coefficient_k,
    )


def compute_point_source_visibility_threshold(
    request: PointSourceVisibilityThresholdRequest,
):
    return point_source_visibility_threshold(
        request.background_nanolamberts,
        field_factor=request.field_factor,
    )


__all__ = [
    "compute_visibility_assessment",
    "compute_visibility_tonight",
    "visibility_policy_from_request",
    "compute_atmospheric_extinction",
    "compute_twilight_sky_brightness",
    "compute_point_source_visibility_threshold",
]
