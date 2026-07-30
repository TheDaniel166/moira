"""REST/OpenAPI evidence for the complete Dorotheus V.7 profile."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from moira.constants import HouseSystem
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = [pytest.mark.loopback, pytest.mark.requires_ephemeris]


@pytest.fixture(scope="module")
def client_and_app():
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client, app


def _payload() -> dict[str, Any]:
    return {
        "profile_id": "dorotheus_construction_v1",
        "jd_ut": 2451545.0,
        "latitude": 51.5074,
        "longitude": -0.1278,
        "house_system": HouseSystem.REGIOMONTANUS,
        "election_class": "ephemeral",
    }


def test_construction_route_returns_every_source_layer(client_and_app) -> None:
    client, _ = client_and_app
    response = client.post(
        "/v1/electional/western/dorotheus-construction",
        json=_payload(),
    )
    assert response.status_code == 200
    body = response.json()
    evaluation = body["evaluation"]
    assert evaluation["profile_id"] == "dorotheus_construction_v1"
    assert evaluation["profile_version"] == "1.1.0"
    assert evaluation["matter"] == "building_construction"
    assert evaluation["source_complete"] is True
    assert evaluation["complete_matter_profile"] is True
    assert evaluation["numerically_complete"] is False
    assert evaluation["complete_electional_judgement"] is False
    assert evaluation["moon_condition"]["profile_id"] == "dorotheus_moon_condition_v1"
    assert evaluation["rooted_context"]["profile_id"] == "dorotheus_rooted_context_v1"
    assert len(evaluation["construction_clauses"]) == 6
    calculation = evaluation["construction_clauses"][0]
    assert calculation["state"] == "satisfied"
    assert [item["name"] for item in calculation["measurements"]] == [
        "moon_true_longitude_mean_ecliptic",
        "moon_mean_longitude_iers_2010",
        "lunar_equation",
        "equation_direction",
    ]
    assert calculation["measurements"][3]["value"] == "added"
    assert body["transport_provenance"]["facade_entrypoint"] == "Moira.dorotheus_construction_at"


def test_construction_radical_request_requires_complete_natal_bundle(client_and_app) -> None:
    client, _ = client_and_app
    payload = _payload()
    payload["election_class"] = "radical"
    assert client.post(
        "/v1/electional/western/dorotheus-construction",
        json=payload,
    ).status_code == 422


def test_construction_openapi_is_typed(client_and_app) -> None:
    _, app = client_and_app
    schema = app.openapi()
    operation = schema["paths"]["/v1/electional/western/dorotheus-construction"]["post"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/DorotheusConstructionResponse"
    }
    assert "DorotheusConstructionRequest" in schema["components"]["schemas"]
    assert "DorotheusConstructionEvaluationResponse" in schema["components"]["schemas"]
