"""Public and REST contracts for the source-scoped Stage 2H Padu table."""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

import moira
import moira.facade as facade_surface
from moira._facade_vedic import VedicFacadeMixin
from moira.pancha_pakshi import (
    PanchaPakshiCapability,
    PanchaPakshiPaduBirdMapping,
    PanchaPakshiPaksha,
    PanchaPakshiWeekday,
    pancha_pakshi_padu_bird_mapping,
)
import moira.vedic as vedic_surface
import moira_server.models as public_models
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.pancha_pakshi import (
    PanchaPakshiPaduBirdMappingRequest,
    PanchaPakshiPaduBirdMappingResponse,
)
from moira_server.serializers.pancha_pakshi import (
    serialize_padu_bird_mapping,
)
from moira_server.services.pancha_pakshi import compute_padu_bird_mapping


_PROFILE_ID = "bogamuni_chennai_2024_padu_bird_mapping"
_ROUTE = "/v1/pancha-pakshi/roles/padu"
_SOURCE_TABLE_SEMANTICS = (
    "profile_paksha_weekday_death_or_inoperative_bird_not_schedule_"
    "rule_activity"
)
_ASSEMBLY_POLICY = (
    "paksha_stanzas_govern_repeated_combined_table_confirms"
)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: object())
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as test_client:
        yield test_client


def test_stage2h_padu_symbols_are_exported_on_all_public_python_surfaces() -> None:
    for surface in (moira, facade_surface, vedic_surface):
        assert surface.PanchaPakshiPaduBirdMapping is PanchaPakshiPaduBirdMapping
        assert surface.pancha_pakshi_padu_bird_mapping is (
            pancha_pakshi_padu_bird_mapping
        )


def test_facade_padu_lookup_is_a_pure_engine_delegation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinel = object()
    seen: dict[str, object] = {}

    def fake_mapping(profile_id, *, profile_paksha, weekday):
        seen.update(
            profile_id=profile_id,
            profile_paksha=profile_paksha,
            weekday=weekday,
        )
        return sentinel

    monkeypatch.setattr(
        "moira._facade_vedic._pancha_pakshi.pancha_pakshi_padu_bird_mapping",
        fake_mapping,
    )

    result = VedicFacadeMixin.pancha_pakshi_padu_bird_mapping(
        object(),
        _PROFILE_ID,
        profile_paksha=PanchaPakshiPaksha.PURVA,
        weekday=PanchaPakshiWeekday.SUNDAY,
    )

    assert result is sentinel
    assert seen == {
        "profile_id": _PROFILE_ID,
        "profile_paksha": PanchaPakshiPaksha.PURVA,
        "weekday": PanchaPakshiWeekday.SUNDAY,
    }


def test_service_and_serializer_preserve_the_pure_source_table_vessel() -> None:
    request = PanchaPakshiPaduBirdMappingRequest(
        profile_id=_PROFILE_ID,
        profile_paksha=PanchaPakshiPaksha.PURVA,
        weekday=PanchaPakshiWeekday.SUNDAY,
    )

    result = compute_padu_bird_mapping(request)
    expected = pancha_pakshi_padu_bird_mapping(
        _PROFILE_ID,
        profile_paksha=PanchaPakshiPaksha.PURVA,
        weekday=PanchaPakshiWeekday.SUNDAY,
    )
    response = serialize_padu_bird_mapping(result)

    assert result == expected
    assert response.profile_id == _PROFILE_ID
    assert response.profile_paksha is PanchaPakshiPaksha.PURVA
    assert response.weekday is PanchaPakshiWeekday.SUNDAY
    assert response.bird.value == "owl"
    assert response.mapping_status == "direct_source_attested"
    assert response.source_table_semantics == _SOURCE_TABLE_SEMANTICS
    assert response.assembly_policy == _ASSEMBLY_POLICY
    assert len(response.source_locators) == 3
    assert response.provenance.capabilities == [
        PanchaPakshiCapability.PADU_BIRD_MAPPING
    ]
    assert response.provenance.astronomical_routing_status == "not_performed"


@pytest.mark.network
def test_padu_route_is_registered_strict_and_has_no_temporal_policy_inputs(
    client: TestClient,
) -> None:
    response = client.post(
        _ROUTE,
        json={
            "profile_id": _PROFILE_ID,
            "profile_paksha": "purva",
            "weekday": "sunday",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["profile_id"] == _PROFILE_ID
    assert body["profile_paksha"] == "purva"
    assert body["weekday"] == "sunday"
    assert body["bird"] == "owl"
    assert body["mapping_status"] == "direct_source_attested"
    assert body["source_table_semantics"] == _SOURCE_TABLE_SEMANTICS
    assert body["assembly_policy"] == _ASSEMBLY_POLICY
    assert len(body["source_locators"]) == 3
    assert body["provenance"]["capabilities"] == ["padu_bird_mapping"]
    assert body["provenance"]["astronomical_routing_status"] == "not_performed"

    forbidden = client.post(
        _ROUTE,
        json={
            "profile_id": _PROFILE_ID,
            "profile_paksha": "purva",
            "weekday": "sunday",
            "dt": "2026-07-20T12:00:00Z",
            "half": "day",
            "latitude": 13.08,
            "longitude": 80.27,
            "policy_id": "caller_selected_policy",
        },
    )
    assert forbidden.status_code == 422
    assert forbidden.json()["error_code"] == "validation_error"


@pytest.mark.network
def test_padu_profile_advertises_only_its_admitted_capability(
    client: TestClient,
) -> None:
    response = client.get("/v1/pancha-pakshi/profiles")

    assert response.status_code == 200
    descriptor = next(
        item
        for item in response.json()["profiles"]
        if item["profile_id"] == _PROFILE_ID
    )
    assert descriptor["admission_status"] == "source_scoped_public"
    assert descriptor["product_kind"] == "padu_bird_mapping"
    assert descriptor["capabilities"] == ["padu_bird_mapping"]
    assert descriptor["default_selection_allowed"] is False


@pytest.mark.network
def test_padu_openapi_contract_is_exact_and_publicly_exported(
    client: TestClient,
) -> None:
    schema = client.app.openapi()
    operation = schema["paths"][_ROUTE]["post"]
    components = schema["components"]["schemas"]
    request = components["PanchaPakshiPaduBirdMappingRequest"]
    response = components["PanchaPakshiPaduBirdMappingResponse"]

    assert operation["tags"] == ["pancha-pakshi"]
    assert request["additionalProperties"] is False
    assert set(request["required"]) == {
        "profile_id",
        "profile_paksha",
        "weekday",
    }
    assert set(request["properties"]) == {
        "profile_id",
        "profile_paksha",
        "weekday",
    }
    assert response["additionalProperties"] is False
    assert set(response["required"]) == {
        "profile_id",
        "profile_paksha",
        "weekday",
        "bird",
        "mapping_status",
        "source_table_semantics",
        "assembly_policy",
        "source_locators",
        "provenance",
    }
    assert response["properties"]["mapping_status"]["const"] == (
        "direct_source_attested"
    )
    assert response["properties"]["source_table_semantics"]["const"] == (
        _SOURCE_TABLE_SEMANTICS
    )
    assert response["properties"]["assembly_policy"]["const"] == (
        _ASSEMBLY_POLICY
    )
    assert response["properties"]["source_locators"]["minItems"] == 3
    assert response["properties"]["source_locators"]["maxItems"] == 3
    assert "padu_bird_mapping" in components["PanchaPakshiCapability"]["enum"]
    assert public_models.PanchaPakshiPaduBirdMappingRequest is (
        PanchaPakshiPaduBirdMappingRequest
    )
    assert public_models.PanchaPakshiPaduBirdMappingResponse is (
        PanchaPakshiPaduBirdMappingResponse
    )
