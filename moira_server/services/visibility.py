"""Phase-5 visibility service helpers."""

from __future__ import annotations

from moira import Moira
from moira.sky.visibility import (
    ObserverVisibilityEnvironment,
    PhysicalAtmosphereInput,
    PhysicalBortleBackground,
    PhysicalDirectionalBackground,
    PhysicalHorizonProfile,
    PhysicalHorizonSample,
    PhysicalModeledBackgroundComponent,
    PhysicalSqmBackground,
    PhysicalVisibilityPolicy,
    PhysicalVisibilitySearchPolicy,
    VisibilityDataPackConfig,
    VisibilityPolicy,
    atmospheric_extinction,
    directional_twilight_sky_brightness,
    point_source_visibility_threshold,
    visibility_assessment,
)
from moira.spk_reader import use_reader_override

from ..config import ServerConfig, ServerConfigurationError
from ..models.visibility import (
    AtmosphericExtinctionRequest,
    PhysicalBackgroundRequest,
    PhysicalBortleBackgroundRequest,
    PhysicalDirectionalBackgroundRequest,
    PhysicalHorizonProfileRequest,
    PhysicalModeledBackgroundComponentRequest,
    PhysicalSqmBackgroundRequest,
    PhysicalVisibilityAssessmentRequest,
    PhysicalVisibilityEventRequest,
    PhysicalVisibilityPolicyRequest,
    PhysicalVisibilitySearchPolicyRequest,
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


def _physical_background_from_request(
    request: PhysicalBackgroundRequest | None,
):
    if request is None:
        return None
    values = request.model_dump(exclude={"kind"})
    if isinstance(request, PhysicalDirectionalBackgroundRequest):
        return PhysicalDirectionalBackground(**values)
    if isinstance(request, PhysicalSqmBackgroundRequest):
        return PhysicalSqmBackground(**values)
    if isinstance(request, PhysicalBortleBackgroundRequest):
        return PhysicalBortleBackground(**values)
    raise TypeError("unsupported physical background request")


def _physical_modeled_component_from_request(
    request: PhysicalModeledBackgroundComponentRequest,
) -> PhysicalModeledBackgroundComponent:
    return PhysicalModeledBackgroundComponent(**request.model_dump())


def _physical_horizon_from_request(
    request: PhysicalHorizonProfileRequest | None,
) -> PhysicalHorizonProfile | None:
    if request is None:
        return None
    return PhysicalHorizonProfile(
        samples=tuple(
            PhysicalHorizonSample(**sample.model_dump())
            for sample in request.samples
        ),
        profile_id=request.profile_id,
        source_id=request.source_id,
        source_receipt_sha256=request.source_receipt_sha256,
    )


def physical_visibility_policy_from_request(
    request: PhysicalVisibilityPolicyRequest | None,
) -> PhysicalVisibilityPolicy | None:
    if request is None:
        return None
    values = request.model_dump(
        exclude={
            "atmosphere",
            "background",
            "directional_horizon",
            "modeled_background_components",
        }
    )
    return PhysicalVisibilityPolicy(
        **values,
        atmosphere=PhysicalAtmosphereInput(**request.atmosphere.model_dump()),
        background=_physical_background_from_request(request.background),
        directional_horizon=_physical_horizon_from_request(
            request.directional_horizon
        ),
        modeled_background_components=tuple(
            _physical_modeled_component_from_request(component)
            for component in request.modeled_background_components
        ),
    )


def physical_visibility_search_policy_from_request(
    request: PhysicalVisibilitySearchPolicyRequest | None,
) -> PhysicalVisibilitySearchPolicy | None:
    if request is None:
        return None
    return PhysicalVisibilitySearchPolicy(**request.model_dump())


def physical_visibility_data_pack_config_from_server(
    config: ServerConfig,
) -> VisibilityDataPackConfig:
    directory = config.physical_visibility_data_pack_directory
    if directory is None:
        raise ServerConfigurationError(
            "physical visibility requires the server-owned "
            "MOIRA_SERVER_PHYSICAL_VISIBILITY_DATA_PACK_DIRECTORY"
        )
    try:
        return VisibilityDataPackConfig(
            directory=directory,
            expected_manifest_sha256=(
                config.physical_visibility_data_pack_manifest_sha256
            ),
        )
    except ValueError as exc:
        raise ServerConfigurationError(
            f"invalid physical visibility data-pack configuration: {exc}"
        ) from exc


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


def compute_physical_visibility_assessment(
    engine: Moira,
    request: PhysicalVisibilityAssessmentRequest,
    config: ServerConfig,
):
    return engine.physical_visibility_assessment(
        request.body,
        request.jd_ut,
        request.lat,
        request.lon,
        data_pack_config=physical_visibility_data_pack_config_from_server(
            config
        ),
        policy=physical_visibility_policy_from_request(request.policy),
    )


def compute_physical_visibility_event(
    engine: Moira,
    request: PhysicalVisibilityEventRequest,
    config: ServerConfig,
):
    return engine.physical_visibility_event(
        request.body,
        request.phase,
        request.jd_start,
        request.lat,
        request.lon,
        data_pack_config=physical_visibility_data_pack_config_from_server(
            config
        ),
        policy=physical_visibility_policy_from_request(request.policy),
        search_policy=physical_visibility_search_policy_from_request(
            request.search_policy
        ),
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
    "compute_physical_visibility_assessment",
    "compute_physical_visibility_event",
    "physical_visibility_policy_from_request",
    "physical_visibility_search_policy_from_request",
    "physical_visibility_data_pack_config_from_server",
    "compute_atmospheric_extinction",
    "compute_twilight_sky_brightness",
    "compute_point_source_visibility_threshold",
]
