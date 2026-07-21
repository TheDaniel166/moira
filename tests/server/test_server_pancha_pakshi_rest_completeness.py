"""REST-completeness gates for every admitted Pancha Pakshi public product."""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from moira.pancha_pakshi import (
    PanchaPakshiCapability,
    PanchaPakshiPaksha,
    available_pancha_pakshi_profiles,
    pancha_pakshi_nakshatra_bird_mapping,
    pancha_pakshi_uromarisi_constitution_status,
)
from moira._facade_vedic import VedicFacadeMixin
import moira_server.models as public_models
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.pancha_pakshi import (
    PanchaPakshiNakshatraBirdMappingRequest,
    PanchaPakshiNakshatraBirdMappingResponse,
    PanchaPakshiUromarisiConstitutionStatusResponse,
)
from moira_server.serializers.pancha_pakshi import (
    serialize_nakshatra_bird_mapping,
    serialize_uromarisi_constitution_status,
)
from moira_server.services.pancha_pakshi import (
    compute_nakshatra_bird_mapping,
    uromarisi_constitution_status,
)


_PROFILE_ID = "bogamuni_chennai_2024_nakshatra_natal_identity"
_MAPPING_ROUTE = "/v1/pancha-pakshi/mappings/nakshatra-bird"
_STATUS_ROUTE = "/v1/pancha-pakshi/constitution/uromarisi"

_CAPABILITY_ROUTES = {
    PanchaPakshiCapability.AKSARA_IDENTITY: "/v1/pancha-pakshi/identity/aksara",
    PanchaPakshiCapability.NOMINAL_SCHEDULE: "/v1/pancha-pakshi/schedule/nominal",
    PanchaPakshiCapability.DIRECTED_RELATIONSHIPS: "/v1/pancha-pakshi/relationships/directed",
    PanchaPakshiCapability.ASTRONOMICAL_CONTEXT: "/v1/pancha-pakshi/context/local-solar",
    PanchaPakshiCapability.ASTRONOMICAL_PAKSHA_INFERENCE: (
        "/v1/pancha-pakshi/context/astronomical-paksha"
    ),
    PanchaPakshiCapability.NAKSHATRA_BIRD_MAPPING: _MAPPING_ROUTE,
    PanchaPakshiCapability.NATAL_IDENTITY: "/v1/pancha-pakshi/identity/natal-moon",
    PanchaPakshiCapability.PADU_BIRD_MAPPING: "/v1/pancha-pakshi/roles/padu",
    PanchaPakshiCapability.FIRST_EAT_BIRD_MAPPING: "/v1/pancha-pakshi/schedule/first-eat-bird",
    PanchaPakshiCapability.SOOKSHMA_TEMPORAL_SELECTION: "/v1/pancha-pakshi/sookshma/select",
    PanchaPakshiCapability.FIXED_CLOCK_MATERIALIZATION: "/v1/pancha-pakshi/schedule/fixed-clock",
    PanchaPakshiCapability.FIXED_CLOCK_CURRENT_CELL_SELECTION: (
        "/v1/pancha-pakshi/schedule/fixed-clock/current-cell"
    ),
    PanchaPakshiCapability.SOLAR_PROPORTIONAL_MATERIALIZATION: (
        "/v1/pancha-pakshi/schedule/solar-proportional"
    ),
    PanchaPakshiCapability.SOLAR_PROPORTIONAL_CURRENT_CELL_SELECTION: (
        "/v1/pancha-pakshi/schedule/solar-proportional/current-cell"
    ),
}

_PUBLIC_FACADE_METHOD_ROUTES = {
    "pancha_pakshi_profiles": "/v1/pancha-pakshi/profiles",
    "pancha_pakshi_uromarisi_constitution_status": _STATUS_ROUTE,
    "pancha_pakshi_profile_info": "/v1/pancha-pakshi/profiles/{profile_id}",
    "pancha_pakshi_astronomical_paksha": "/v1/pancha-pakshi/context/astronomical-paksha",
    "pancha_pakshi_natal_moon_identity": "/v1/pancha-pakshi/identity/natal-moon",
    "pancha_pakshi_nakshatra_bird_mapping": _MAPPING_ROUTE,
    "pancha_pakshi_padu_bird_mapping": "/v1/pancha-pakshi/roles/padu",
    "pancha_pakshi_sookshma_temporal_selection": "/v1/pancha-pakshi/sookshma/select",
    "pancha_pakshi_schedule_sookshma_temporal_selection": (
        "/v1/pancha-pakshi/sookshma/schedule-select"
    ),
    "pancha_pakshi_civil_time_sookshma_selection": "/v1/pancha-pakshi/sookshma/civil-time-select",
    "pancha_pakshi_first_eat_bird_mapping": "/v1/pancha-pakshi/schedule/first-eat-bird",
    "pancha_pakshi_identity_from_initial_vowel": "/v1/pancha-pakshi/identity/aksara",
    "pancha_pakshi_directed_relationship": "/v1/pancha-pakshi/relationships/directed",
    "pancha_pakshi_schedule": "/v1/pancha-pakshi/schedule/nominal",
    "pancha_pakshi_local_solar_context": "/v1/pancha-pakshi/context/local-solar",
    "pancha_pakshi_fixed_clock_materialization": "/v1/pancha-pakshi/schedule/fixed-clock",
    "pancha_pakshi_fixed_clock_current_cell": (
        "/v1/pancha-pakshi/schedule/fixed-clock/current-cell"
    ),
    "pancha_pakshi_solar_proportional_materialization": (
        "/v1/pancha-pakshi/schedule/solar-proportional"
    ),
    "pancha_pakshi_solar_proportional_current_cell": (
        "/v1/pancha-pakshi/schedule/solar-proportional/current-cell"
    ),
}


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: object())
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as test_client:
        yield test_client


def test_nakshatra_service_and_serializer_preserve_pure_table_semantics() -> None:
    request = PanchaPakshiNakshatraBirdMappingRequest(
        profile_id=_PROFILE_ID,
        profile_paksha=PanchaPakshiPaksha.PURVA,
        nakshatra_index=0,
    )

    result = compute_nakshatra_bird_mapping(request)
    expected = pancha_pakshi_nakshatra_bird_mapping(
        _PROFILE_ID,
        profile_paksha=PanchaPakshiPaksha.PURVA,
        nakshatra_index=0,
    )
    response = serialize_nakshatra_bird_mapping(result)

    assert result == expected
    assert response.nakshatra == "Ashwini"
    assert response.bird.value == "vulture"
    assert response.source_table_semantics == (
        "nakshatra_bird_table_not_explicitly_natal_moon"
    )
    assert response.provenance.capabilities == [
        PanchaPakshiCapability.NAKSHATRA_BIRD_MAPPING,
        PanchaPakshiCapability.NATAL_IDENTITY,
    ]


def test_constitution_service_and_serializer_return_only_public_status() -> None:
    result = uromarisi_constitution_status()
    response = serialize_uromarisi_constitution_status(result)

    assert result == pancha_pakshi_uromarisi_constitution_status()
    assert response.completed_phases == list(range(1, 13))
    assert response.rest_route_status == "admitted_governance_status_only"
    assert response.historical_data_status == "private_not_exposed"
    assert response.medical_use_status == "forbidden"


@pytest.mark.network
def test_missing_nakshatra_mapping_route_is_now_strictly_admitted(
    client: TestClient,
) -> None:
    response = client.post(
        _MAPPING_ROUTE,
        json={
            "profile_id": _PROFILE_ID,
            "profile_paksha": "purva",
            "nakshatra_index": 0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["nakshatra"] == "Ashwini"
    assert body["bird"] == "vulture"
    assert body["mapping_status"] == "direct_source_attested"
    assert body["source_table_semantics"] == (
        "nakshatra_bird_table_not_explicitly_natal_moon"
    )

    forbidden = client.post(
        _MAPPING_ROUTE,
        json={
            "profile_id": _PROFILE_ID,
            "profile_paksha": "purva",
            "nakshatra_index": 0,
            "dt": "2026-07-21T12:00:00Z",
            "ayanamsa": "lahiri",
            "condition": True,
            "score": True,
        },
    )
    assert forbidden.status_code == 422
    assert forbidden.json()["error_code"] == "validation_error"


@pytest.mark.network
def test_constitution_route_exposes_status_but_no_private_research(
    client: TestClient,
) -> None:
    response = client.get(_STATUS_ROUTE)

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "process": "SCP",
        "completed_phases": list(range(1, 13)),
        "admission_status": "research_only",
        "public_product": "constitutional_status_only",
        "historical_data_status": "private_not_exposed",
        "network_status": "private_structural_no_admitted_edges",
        "relation_semantics_status": "not_admitted",
        "graph_metric_status": "not_evaluable_no_admitted_relation_edges",
        "condition_evaluation_status": (
            "not_evaluable_no_admitted_condition_doctrine"
        ),
        "prognosis_status": "not_performed",
        "medical_use_status": "forbidden",
        "manifest_profile_status": "not_admitted",
        "rest_route_status": "admitted_governance_status_only",
    }
    assert set(body).isdisjoint(
        {
            "historical_source_atoms",
            "historical_classifications",
            "historical_relation_records",
            "local_condition_profiles",
            "aggregate_intelligence",
            "network_nodes",
            "relation_candidates",
            "condition_scores",
            "prognosis",
            "medical_interpretation",
        }
    )


@pytest.mark.network
def test_all_advertised_profile_capabilities_have_registered_routes(
    client: TestClient,
) -> None:
    advertised = {
        capability
        for profile in available_pancha_pakshi_profiles()
        for capability in profile.capabilities
    }
    registered = set(client.app.openapi()["paths"])

    assert advertised == set(_CAPABILITY_ROUTES)
    assert set(_CAPABILITY_ROUTES.values()) <= registered
    assert _STATUS_ROUTE in registered
    assert {
        PanchaPakshiCapability.AUTHORITY_BIRDS,
        PanchaPakshiCapability.SUBDIVISIONS,
        PanchaPakshiCapability.CONDITION,
        PanchaPakshiCapability.SCORING,
        PanchaPakshiCapability.WINDOW_SEARCH,
    }.isdisjoint(advertised)


@pytest.mark.network
def test_every_public_facade_operation_has_one_registered_route(
    client: TestClient,
) -> None:
    facade_methods = {
        name
        for name in dir(VedicFacadeMixin)
        if name.startswith("pancha_pakshi_")
    }
    registered = {
        path
        for path in client.app.openapi()["paths"]
        if path.startswith("/v1/pancha-pakshi/")
    }

    assert facade_methods == set(_PUBLIC_FACADE_METHOD_ROUTES)
    assert len(set(_PUBLIC_FACADE_METHOD_ROUTES.values())) == len(
        _PUBLIC_FACADE_METHOD_ROUTES
    )
    assert set(_PUBLIC_FACADE_METHOD_ROUTES.values()) == registered


@pytest.mark.network
def test_new_openapi_contracts_are_exact_and_publicly_exported(
    client: TestClient,
) -> None:
    schema = client.app.openapi()
    components = schema["components"]["schemas"]
    mapping_request = components["PanchaPakshiNakshatraBirdMappingRequest"]
    status_response = components[
        "PanchaPakshiUromarisiConstitutionStatusResponse"
    ]

    assert schema["paths"][_MAPPING_ROUTE]["post"]["tags"] == ["pancha-pakshi"]
    assert schema["paths"][_STATUS_ROUTE]["get"]["tags"] == ["pancha-pakshi"]
    assert mapping_request["additionalProperties"] is False
    assert set(mapping_request["required"]) == {
        "profile_id",
        "profile_paksha",
        "nakshatra_index",
    }
    assert set(mapping_request["properties"]) == set(mapping_request["required"])
    assert status_response["additionalProperties"] is False
    assert status_response["properties"]["public_product"]["const"] == (
        "constitutional_status_only"
    )
    assert status_response["properties"]["rest_route_status"]["const"] == (
        "admitted_governance_status_only"
    )
    assert public_models.PanchaPakshiNakshatraBirdMappingRequest is (
        PanchaPakshiNakshatraBirdMappingRequest
    )
    assert public_models.PanchaPakshiNakshatraBirdMappingResponse is (
        PanchaPakshiNakshatraBirdMappingResponse
    )
    assert public_models.PanchaPakshiUromarisiConstitutionStatusResponse is (
        PanchaPakshiUromarisiConstitutionStatusResponse
    )
