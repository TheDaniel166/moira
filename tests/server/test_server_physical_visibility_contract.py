"""Transport-parity gates for the additive physical visibility routes."""

from __future__ import annotations

from dataclasses import fields, replace
import json

from fastapi.testclient import TestClient
import pytest

import moira.heliacal as heliacal
from moira._visibility_lut import VisibilityDataPackReceipt
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models import visibility as visibility_models
from moira_server.services.visibility import (
    physical_visibility_data_pack_config_from_server,
    physical_visibility_policy_from_request,
    physical_visibility_search_policy_from_request,
)
from moira_server.serializers.visibility import (
    serialize_physical_visibility_assessment,
    serialize_physical_visibility_event,
)


pytestmark = pytest.mark.loopback

_SHA = "a" * 64
_MISSING_PACK = r"X:\moira-phase5-deliberately-missing-pack"


@pytest.fixture
def physical_client(
    moira_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(
        ServerConfig(
            docs_enabled=False,
            physical_visibility_data_pack_directory=_MISSING_PACK,
        )
    )
    with TestClient(app) as client:
        yield client


@pytest.fixture
def unconfigured_client(
    moira_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client


def _bortle_policy_payload() -> dict[str, object]:
    return {
        "background": {
            "kind": "bortle",
            "light_pollution_class": 3,
            "scotopic_to_photopic_ratio": 1.5,
            "spectral_ratio_source_id": "phase5-test-ratio",
            "source_receipt_sha256": _SHA,
        }
    }


def test_physical_assessment_route_returns_typed_fail_closed_truth(
    physical_client: TestClient,
) -> None:
    response = physical_client.post(
        "/v1/visibility/physical-assessment",
        json={
            "body": "Venus",
            "jd_ut": 2451545.0,
            "lat": 0.0,
            "lon": 0.0,
            "policy": _bortle_policy_payload(),
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_evaluable"
    assert body["evidence_state"] == "missing_dependency"
    assert body["reason"] == "visibility_data_pack_missing"
    assert body["data_pack_receipt"] is None
    assert body["atmosphere_receipt"]["atmosphere_profile"] == "us_standard"
    assert body["observer_protocol_receipt"]["protocol_id"] == (
        "known_location_directed_averted_observation_v1"
    )
    assert isinstance(body["components"], list)


def test_physical_event_route_returns_solver_and_horizon_receipts(
    physical_client: TestClient,
) -> None:
    response = physical_client.post(
        "/v1/visibility/physical-event",
        json={
            "body": "Mars",
            "phase": "morning_first_rising",
            "jd_start": 2451545.0,
            "lat": 0.0,
            "lon": 0.0,
            "policy": _bortle_policy_payload(),
            "search_policy": {"search_window_days": 2},
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_evaluable"
    assert body["reason"] == "visibility_data_pack_missing"
    assert body["phase"] == "morning_first_rising"
    assert body["solver_receipt"]["search_window_days"] == 2
    assert body["solver_receipt"]["crossing_completeness_state"] == (
        "not_evaluated"
    )
    assert body["horizon_receipt"]["horizon_model_id"] == (
        "scalar_apparent_horizon_v1"
    )
    assert body["sensitivity_receipt"]["probabilistic_confidence_claimed"] is False


def test_physical_routes_require_server_owned_pack_configuration(
    unconfigured_client: TestClient,
) -> None:
    response = unconfigured_client.post(
        "/v1/visibility/physical-assessment",
        json={
            "body": "Mars",
            "jd_ut": 2451545.0,
            "lat": 0.0,
            "lon": 0.0,
            "policy": _bortle_policy_payload(),
        },
    )

    assert response.status_code == 503
    body = response.json()
    assert body["error_code"] == "server_not_configured"
    assert body["category"] == "server_configuration"
    assert "MOIRA_SERVER_PHYSICAL_VISIBILITY_DATA_PACK_DIRECTORY" in body["message"]


def test_physical_request_cannot_supply_a_filesystem_path(
    physical_client: TestClient,
) -> None:
    response = physical_client.post(
        "/v1/visibility/physical-assessment",
        json={
            "body": "Mars",
            "jd_ut": 2451545.0,
            "lat": 0.0,
            "lon": 0.0,
            "data_pack_path": r"C:\client-controlled",
            "policy": _bortle_policy_payload(),
        },
    )

    assert response.status_code == 422
    assert response.json()["error_code"] == "validation_error"


def test_physical_policy_transport_preserves_every_nested_input() -> None:
    request = visibility_models.PhysicalVisibilityPolicyRequest.model_validate(
        {
            "background": {
                "kind": "directional",
                "photopic_luminance_cd_m2": 1.0e-4,
                "scotopic_luminance_cd_m2": 1.5e-4,
                "scope": "dark_sky_anchor",
                "component_ids": ["phase5-dark-sky"],
                "source_id": "phase5-background",
                "source_receipt_sha256": _SHA,
                "method_id": "phase5-method",
                "component_inventory_complete": False,
            },
            "atmosphere": {
                "atmosphere_profile": "phase5-atmosphere",
                "aerosol_profile": "phase5-aerosol",
                "observer_altitude_m": 1250.0,
                "surface_pressure_hpa": 870.0,
                "aod550": 0.08,
                "angstrom_exponent": 1.1,
                "ozone_du": 280.0,
                "ground_albedo": 0.15,
            },
            "expected_manifest_sha256": _SHA,
            "local_horizon_altitude_deg": 2.0,
            "refraction_pressure_hpa": 870.0,
            "refraction_temperature_c": 5.0,
            "refraction_relative_humidity": 0.25,
            "modeled_background_components": [
                {
                    "component_kind": "airglow",
                    "photopic_luminance_cd_m2": 1.0e-5,
                    "scotopic_luminance_cd_m2": 1.8e-5,
                    "model_id": "phase5-airglow-model-v1",
                    "source_ids": ["phase5-airglow-source"],
                    "source_receipt_sha256": _SHA,
                    "spatial_applicability_id": "phase5-site",
                    "temporal_applicability_id": "phase5-epoch",
                    "direction_receipt_id": "phase5-direction",
                    "validity_domain_id": "phase5-airglow-domain",
                    "uncertainty_authority_id": "phase5-uncertainty",
                }
            ],
        }
    )

    policy = physical_visibility_policy_from_request(request)

    assert policy is not None
    assert isinstance(policy.background, heliacal.PhysicalDirectionalBackground)
    assert policy.background.component_ids == ("phase5-dark-sky",)
    assert policy.atmosphere.observer_altitude_m == 1250.0
    assert policy.atmosphere.aerosol_profile == "phase5-aerosol"
    assert policy.expected_manifest_sha256 == _SHA
    assert policy.local_horizon_altitude_deg == 2.0
    assert policy.refraction_relative_humidity == 0.25
    assert len(policy.modeled_background_components) == 1
    assert policy.modeled_background_components[0].source_ids == (
        "phase5-airglow-source",
    )


def test_directional_horizon_transport_preserves_profile_identity() -> None:
    request = visibility_models.PhysicalVisibilityPolicyRequest.model_validate(
        {
            "background": _bortle_policy_payload()["background"],
            "directional_horizon": {
                "samples": [
                    {
                        "azimuth_deg": float(azimuth),
                        "apparent_altitude_deg": 1.0 + azimuth / 3600.0,
                    }
                    for azimuth in range(0, 360, 10)
                ],
                "profile_id": "phase5-horizon",
                "source_id": "phase5-horizon-source",
                "source_receipt_sha256": _SHA,
            },
        }
    )

    policy = physical_visibility_policy_from_request(request)

    assert policy is not None
    assert policy.directional_horizon is not None
    assert policy.directional_horizon.profile_id == "phase5-horizon"
    assert len(policy.directional_horizon.samples) == 36
    assert policy.directional_horizon.actual_maximum_gap_deg == 10.0


def test_search_and_server_pack_configuration_preserve_identity() -> None:
    search_request = (
        visibility_models.PhysicalVisibilitySearchPolicyRequest(
            search_window_days=17,
            scan_step_days=0.01,
            adaptive_minimum_step_days=0.001,
            root_time_tolerance_days=0.0001,
            root_margin_tolerance_magnitude=2.0e-5,
            near_zero_tolerance_magnitude=3.0e-3,
            curvature_tolerance_magnitude=4.0e-3,
            maximum_adaptive_depth=9,
            maximum_root_iterations=73,
        )
    )
    search_policy = physical_visibility_search_policy_from_request(
        search_request
    )
    pack_config = physical_visibility_data_pack_config_from_server(
        ServerConfig(
            physical_visibility_data_pack_directory=r"C:\server-owned-pack",
            physical_visibility_data_pack_manifest_sha256=_SHA,
        )
    )

    assert search_policy == heliacal.PhysicalVisibilitySearchPolicy(
        **search_request.model_dump()
    )
    assert str(pack_config.directory) == r"C:\server-owned-pack"
    assert pack_config.expected_manifest_sha256 == _SHA


def test_response_models_cover_every_engine_receipt_field() -> None:
    pairs = (
        (VisibilityDataPackReceipt, visibility_models.VisibilityDataPackReceiptResponse),
        (heliacal.VisibilityComponentReceipt, visibility_models.VisibilityComponentReceiptResponse),
        (heliacal.PhysicalAtmosphereReceipt, visibility_models.PhysicalAtmosphereReceiptResponse),
        (heliacal.PhysicalValidityDomainReceipt, visibility_models.PhysicalValidityDomainReceiptResponse),
        (heliacal.PhysicalObserverProtocolReceipt, visibility_models.PhysicalObserverProtocolReceiptResponse),
        (heliacal.PhysicalBackgroundReceipt, visibility_models.PhysicalBackgroundReceiptResponse),
        (heliacal.PhysicalTargetReceipt, visibility_models.PhysicalTargetReceiptResponse),
        (heliacal.PhysicalThresholdReceipt, visibility_models.PhysicalThresholdReceiptResponse),
        (heliacal.PhysicalVisibilityErrorBudgetReceipt, visibility_models.PhysicalVisibilityErrorBudgetReceiptResponse),
        (heliacal.PhysicalHorizonReceipt, visibility_models.PhysicalHorizonReceiptResponse),
        (heliacal.PhysicalVisibilityAssessment, visibility_models.PhysicalVisibilityAssessmentResponse),
        (heliacal.PhysicalObservationWindowReceipt, visibility_models.PhysicalObservationWindowReceiptResponse),
        (heliacal.PhysicalEventSolverReceipt, visibility_models.PhysicalEventSolverReceiptResponse),
        (heliacal.PhysicalEventSensitivityReceipt, visibility_models.PhysicalEventSensitivityReceiptResponse),
        (heliacal.PhysicalEphemerisReceipt, visibility_models.PhysicalEphemerisReceiptResponse),
        (heliacal.PhysicalVisibilityEventResult, visibility_models.PhysicalVisibilityEventResponse),
    )

    for engine_type, response_type in pairs:
        assert {field.name for field in fields(engine_type)} == set(
            response_type.model_fields
        )


def test_request_models_cover_every_engine_policy_input() -> None:
    exact_pairs = (
        (
            heliacal.PhysicalAtmosphereInput,
            visibility_models.PhysicalAtmosphereInputRequest,
        ),
        (
            heliacal.PhysicalHorizonSample,
            visibility_models.PhysicalHorizonSampleRequest,
        ),
        (
            heliacal.PhysicalVisibilityPolicy,
            visibility_models.PhysicalVisibilityPolicyRequest,
        ),
        (
            heliacal.PhysicalVisibilitySearchPolicy,
            visibility_models.PhysicalVisibilitySearchPolicyRequest,
        ),
    )
    discriminated_pairs = (
        (
            heliacal.PhysicalDirectionalBackground,
            visibility_models.PhysicalDirectionalBackgroundRequest,
        ),
        (
            heliacal.PhysicalSqmBackground,
            visibility_models.PhysicalSqmBackgroundRequest,
        ),
        (
            heliacal.PhysicalBortleBackground,
            visibility_models.PhysicalBortleBackgroundRequest,
        ),
    )

    for engine_type, request_type in exact_pairs:
        assert {field.name for field in fields(engine_type) if field.init} == set(
            request_type.model_fields
        )
    for engine_type, request_type in discriminated_pairs:
        assert {field.name for field in fields(engine_type)} == (
            set(request_type.model_fields) - {"kind"}
        )
    assert {
        field.name
        for field in fields(heliacal.PhysicalHorizonProfile)
        if field.init
    } == set(visibility_models.PhysicalHorizonProfileRequest.model_fields)
    assert set(
        visibility_models.PhysicalModeledBackgroundComponentRequest.model_fields
    ) == {
        "component_kind",
        "photopic_luminance_cd_m2",
        "scotopic_luminance_cd_m2",
        "model_id",
        "source_ids",
        "source_receipt_sha256",
        "spatial_applicability_id",
        "temporal_applicability_id",
        "direction_receipt_id",
        "validity_domain_id",
        "uncertainty_authority_id",
    }


def test_serializers_preserve_nested_pack_identity_receipts() -> None:
    policy = heliacal.PhysicalVisibilityPolicy(
        background=heliacal.PhysicalBortleBackground(
            light_pollution_class=3,
            scotopic_to_photopic_ratio=1.5,
            spectral_ratio_source_id="phase5-test-ratio",
            source_receipt_sha256=_SHA,
        )
    )
    pack_config = heliacal.VisibilityDataPackConfig(_MISSING_PACK)
    pack_receipt = VisibilityDataPackReceipt(
        pack_id="moira-physical-heliacal-visibility",
        version="1.2.0",
        compatibility_id=(
            "moira-physical-heliacal-visibility-data-pack-v1.2"
        ),
        composite_model_id="clear_sky_naked_eye_point_source_v1",
        table_format_id="phase5-format",
        engine_contract_id="moira-physical-visibility-engine-contract-v1",
        engine_contract_version=1,
        manifest_sha256=_SHA,
        generation_fingerprint="phase5-generation",
        payload_sha256=(("radiance.bin", _SHA),),
        source_artifact_spec_id="phase5-source-artifact",
        source_artifact_manifest_sha256=_SHA,
        source_dataset_ids=("phase5-source",),
        license="phase5-test-only",
        notice_sha256=_SHA,
    )
    assessment = heliacal.physical_visibility_assessment(
        "Mars",
        2451545.0,
        0.0,
        0.0,
        data_pack_config=pack_config,
        policy=policy,
    )
    event = heliacal.physical_visibility_event(
        "Mars",
        heliacal.PhysicalVisibilityPhase.MORNING_FIRST_RISING,
        2451545.0,
        0.0,
        0.0,
        data_pack_config=pack_config,
        policy=policy,
        search_policy=heliacal.PhysicalVisibilitySearchPolicy(
            search_window_days=1
        ),
    )
    assessment = replace(assessment, data_pack_receipt=pack_receipt)
    event = replace(
        event,
        data_pack_receipt=pack_receipt,
        event_assessment=assessment,
    )

    assessment_payload = serialize_physical_visibility_assessment(
        assessment
    ).model_dump(mode="json")
    event_payload = serialize_physical_visibility_event(event).model_dump(
        mode="json"
    )

    assert assessment_payload["data_pack_receipt"]["table_format_id"] == (
        "phase5-format"
    )
    assert assessment_payload["data_pack_receipt"]["payload_sha256"] == [
        ["radiance.bin", _SHA]
    ]
    assert event_payload["event_assessment"]["data_pack_receipt"][
        "generation_fingerprint"
    ] == "phase5-generation"
    assert event_payload["solver_receipt"]["search_window_days"] == 1


def test_openapi_exposes_physical_routes_without_client_paths(
    unconfigured_client: TestClient,
) -> None:
    schema = unconfigured_client.app.openapi()
    assert "/v1/visibility/physical-assessment" in schema["paths"]
    assert "/v1/visibility/physical-event" in schema["paths"]

    components = schema["components"]["schemas"]
    assert "PhysicalVisibilityPolicyRequest" in components
    assert "PhysicalVisibilityAssessmentResponse" in components
    assert "PhysicalVisibilityEventResponse" in components
    for path in (
        "/v1/visibility/physical-assessment",
        "/v1/visibility/physical-event",
    ):
        unavailable = schema["paths"][path]["post"]["responses"]["503"]
        assert unavailable["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/ErrorEnvelope"
        }
    request_schema = json.dumps(
        {
            "assessment": components["PhysicalVisibilityAssessmentRequest"],
            "event": components["PhysicalVisibilityEventRequest"],
        },
        sort_keys=True,
    )
    assert "directory" not in request_schema
    assert "data_pack_path" not in request_schema


def test_legacy_visibility_and_event_schemas_remain_exact(
    unconfigured_client: TestClient,
) -> None:
    schemas = unconfigured_client.app.openapi()["components"]["schemas"]
    expected = {
        "VisibilityAssessmentRequest": (
            "body",
            "jd_ut",
            "lat",
            "lon",
            "policy",
        ),
        "VisibilityAssessmentResponse": (
            "body",
            "jd_ut",
            "criterion_family",
            "effective_limiting_magnitude",
            "apparent_magnitude",
            "true_altitude_deg",
            "apparent_altitude_deg",
            "local_horizon_altitude_deg",
            "solar_elongation_deg",
            "is_geometrically_visible",
            "is_bright_enough",
            "observable",
            "lunar_crescent_details",
            "moonlight_sky_nanolamberts",
            "extinction_adjusted_magnitude",
            "visibility_margin_magnitude",
            "criterion_target_magnitude",
            "target_extinction_applied_separately",
            "criterion_applicable",
            "criterion_reason",
            "atmospheric_extinction",
            "twilight_sky_brightness",
            "point_source_threshold",
            "dark_sky_nanolamberts",
            "total_sky_nanolamberts",
        ),
        "GeneralVisibilityEventRequest": (
            "body",
            "kind",
            "jd_start",
            "lat",
            "lon",
            "search_window_days",
        ),
        "GeneralVisibilityEventResponse": (
            "body",
            "target_kind",
            "kind",
            "jd_ut",
            "datetime_utc",
            "elongation_deg",
            "target_altitude_deg",
            "sun_altitude_deg",
            "apparent_magnitude",
            "assessment",
        ),
    }

    for name, properties in expected.items():
        assert tuple(schemas[name]["properties"]) == properties


def test_server_config_reads_physical_pack_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "MOIRA_SERVER_PHYSICAL_VISIBILITY_DATA_PACK_DIRECTORY",
        r"C:\configured-pack",
    )
    monkeypatch.setenv(
        "MOIRA_SERVER_PHYSICAL_VISIBILITY_DATA_PACK_MANIFEST_SHA256",
        _SHA,
    )

    config = ServerConfig.from_env()

    assert config.physical_visibility_data_pack_directory == r"C:\configured-pack"
    assert config.physical_visibility_data_pack_manifest_sha256 == _SHA
