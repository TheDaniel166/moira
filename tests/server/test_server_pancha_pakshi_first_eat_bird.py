"""Strict REST contract for the source-scoped first-samam Eat-bird lookup."""

from __future__ import annotations

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from moira.pancha_pakshi import (
    PanchaPakshiBird,
    PanchaPakshiHalf,
    PanchaPakshiPaksha,
    PanchaPakshiWeekday,
    pancha_pakshi_first_eat_bird_mapping,
)
from moira_server.app import create_app
from moira_server.config import ServerConfig
import moira_server.models as public_models
from moira_server.models.pancha_pakshi import (
    PanchaPakshiFirstEatBirdMappingRequest,
    PanchaPakshiFirstEatBirdMappingResponse,
)
import moira_server.serializers as public_serializers
from moira_server.serializers.pancha_pakshi import (
    serialize_first_eat_bird_mapping,
)
from moira_server.services.pancha_pakshi import (
    compute_first_eat_bird_mapping,
)


_PROFILE_ID = "agastya_madras_1879_akshara_fixed_clock"
_ROUTE = "/v1/pancha-pakshi/schedule/first-eat-bird"
_SOURCE_TABLE_SEMANTICS = (
    "profile_paksha_half_weekday_first_samam_eat_seed_not_padu_"
    "authority_condition_or_score"
)


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: object())
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as test_client:
        yield test_client


def test_service_and_serializer_preserve_the_first_eat_source_vessel() -> None:
    request = PanchaPakshiFirstEatBirdMappingRequest(
        profile_id=_PROFILE_ID,
        profile_paksha=PanchaPakshiPaksha.PURVA,
        half=PanchaPakshiHalf.DAY,
        weekday=PanchaPakshiWeekday.SUNDAY,
    )

    result = compute_first_eat_bird_mapping(request)
    expected = pancha_pakshi_first_eat_bird_mapping(
        _PROFILE_ID,
        profile_paksha=PanchaPakshiPaksha.PURVA,
        half=PanchaPakshiHalf.DAY,
        weekday=PanchaPakshiWeekday.SUNDAY,
    )
    response = serialize_first_eat_bird_mapping(result)

    assert result == expected
    assert response.profile_id == _PROFILE_ID
    assert response.generator_id == "purva_day"
    assert response.profile_paksha is PanchaPakshiPaksha.PURVA
    assert response.half is PanchaPakshiHalf.DAY
    assert response.weekday is PanchaPakshiWeekday.SUNDAY
    assert response.first_eat_bird is PanchaPakshiBird.VULTURE
    assert response.mapping_status == "direct_source_attested"
    assert response.source_table_semantics == _SOURCE_TABLE_SEMANTICS
    assert [locator.locator_id for locator in response.source_locators] == [
        "ia_n10",
        "ia_n16",
        "ia_n19_n20",
    ]
    assert response.provenance.astronomical_routing_status == "not_performed"


@pytest.mark.network
def test_first_eat_route_is_strict_and_routes_no_temporal_inference(
    client: TestClient,
) -> None:
    response = client.post(
        _ROUTE,
        json={
            "profile_id": _PROFILE_ID,
            "profile_paksha": "purva",
            "half": "day",
            "weekday": "sunday",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["profile_id"] == _PROFILE_ID
    assert body["generator_id"] == "purva_day"
    assert body["profile_paksha"] == "purva"
    assert body["half"] == "day"
    assert body["weekday"] == "sunday"
    assert body["first_eat_bird"] == "vulture"
    assert body["mapping_status"] == "direct_source_attested"
    assert body["source_table_semantics"] == _SOURCE_TABLE_SEMANTICS
    assert body["provenance"]["astronomical_routing_status"] == "not_performed"

    forbidden = client.post(
        _ROUTE,
        json={
            "profile_id": _PROFILE_ID,
            "profile_paksha": "purva",
            "half": "day",
            "weekday": "sunday",
            "dt": "2026-07-20T12:00:00Z",
            "latitude": 13.08,
            "longitude": 80.27,
            "policy_id": "caller_selected_policy",
            "paksha": "purva",
        },
    )
    assert forbidden.status_code == 422
    assert forbidden.json()["error_code"] == "validation_error"


@pytest.mark.network
def test_first_eat_openapi_contract_is_exact_and_publicly_exported(
    client: TestClient,
) -> None:
    schema = client.app.openapi()
    operation = schema["paths"][_ROUTE]["post"]
    components = schema["components"]["schemas"]
    request = components["PanchaPakshiFirstEatBirdMappingRequest"]
    response = components["PanchaPakshiFirstEatBirdMappingResponse"]

    assert operation["tags"] == ["pancha-pakshi"]
    assert request["additionalProperties"] is False
    assert set(request["required"]) == {
        "profile_id",
        "profile_paksha",
        "half",
        "weekday",
    }
    assert set(request["properties"]) == {
        "profile_id",
        "profile_paksha",
        "half",
        "weekday",
    }
    assert response["additionalProperties"] is False
    assert set(response["required"]) == {
        "profile_id",
        "generator_id",
        "profile_paksha",
        "half",
        "weekday",
        "first_eat_bird",
        "mapping_status",
        "source_table_semantics",
        "source_locators",
        "provenance",
    }
    assert response["properties"]["mapping_status"]["const"] == (
        "direct_source_attested"
    )
    assert response["properties"]["source_table_semantics"]["const"] == (
        _SOURCE_TABLE_SEMANTICS
    )
    assert response["properties"]["source_locators"]["minItems"] == 3
    assert response["properties"]["source_locators"]["maxItems"] == 4
    assert public_models.PanchaPakshiFirstEatBirdMappingRequest is (
        PanchaPakshiFirstEatBirdMappingRequest
    )
    assert public_models.PanchaPakshiFirstEatBirdMappingResponse is (
        PanchaPakshiFirstEatBirdMappingResponse
    )
    assert public_serializers.serialize_first_eat_bird_mapping is (
        serialize_first_eat_bird_mapping
    )


@pytest.mark.parametrize(
    ("half", "expected_count", "mutate"),
    (
        (PanchaPakshiHalf.DAY, 3, "append"),
        (PanchaPakshiHalf.NIGHT, 4, "remove"),
    ),
)
def test_first_eat_response_rejects_half_inconsistent_locator_count(
    half: PanchaPakshiHalf,
    expected_count: int,
    mutate: str,
) -> None:
    response = serialize_first_eat_bird_mapping(
        pancha_pakshi_first_eat_bird_mapping(
            _PROFILE_ID,
            profile_paksha=PanchaPakshiPaksha.PURVA,
            half=half,
            weekday=PanchaPakshiWeekday.SUNDAY,
        )
    )
    payload = response.model_dump(mode="json")
    if mutate == "append":
        payload["source_locators"].append(payload["source_locators"][0])
    else:
        payload["source_locators"].pop()

    with pytest.raises(
        ValidationError,
        match=(
            f"{half.value} mapping must contain exactly {expected_count} "
            "canonical source locators"
        ),
    ):
        PanchaPakshiFirstEatBirdMappingResponse.model_validate(payload)
