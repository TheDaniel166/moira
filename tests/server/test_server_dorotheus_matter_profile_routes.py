"""REST and OpenAPI evidence for Dorotheus V.8, V.9, and V.11 profiles."""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from moira.constants import HouseSystem
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = [pytest.mark.network, pytest.mark.requires_ephemeris]


@pytest.fixture(scope="module")
def client_and_app():
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client, app


def _payload(profile_id: str) -> dict[str, Any]:
    return {
        "profile_id": profile_id,
        "jd_ut": 2451545.0,
        "latitude": 51.5074,
        "longitude": -0.1278,
        "house_system": HouseSystem.REGIOMONTANUS,
        "election_class": "ephemeral",
    }


@pytest.mark.parametrize(
    ("profile_id", "matter", "clause_count"),
    (
        ("dorotheus_demolition_v1", "building_demolition", 2),
        ("dorotheus_leasing_v1", "leasing", 5),
        ("dorotheus_land_purchase_v1", "land_purchase", 2),
    ),
)
def test_matter_route_exposes_each_named_profile(
    client_and_app,
    profile_id: str,
    matter: str,
    clause_count: int,
) -> None:
    client, _ = client_and_app
    response = client.post(
        "/v1/electional/western/dorotheus-matter-profile",
        json=_payload(profile_id),
    )
    assert response.status_code == 200
    body = response.json()
    evaluation = body["evaluation"]
    assert evaluation["profile_id"] == profile_id
    assert evaluation["profile_version"] == "1.0.0"
    assert evaluation["matter"] == matter
    assert len(evaluation["clauses"]) == clause_count
    assert evaluation["source_complete"] is True
    assert evaluation["complete_matter_profile"] is True
    assert evaluation["complete_electional_judgement"] is False
    assert evaluation["scoring"] == "not_provided"
    assert body["transport_provenance"]["facade_entrypoint"] == (
        "Moira.dorotheus_matter_profile_at"
    )


def test_matter_route_rejects_unknown_profile(client_and_app) -> None:
    client, _ = client_and_app
    response = client.post(
        "/v1/electional/western/dorotheus-matter-profile",
        json=_payload("dorotheus_unknown_v1"),
    )
    assert response.status_code == 422


def test_matter_route_openapi_is_typed(client_and_app) -> None:
    _, app = client_and_app
    schema = app.openapi()
    operation = schema["paths"][
        "/v1/electional/western/dorotheus-matter-profile"
    ]["post"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/DorotheusMatterProfileResponse"
    }
    assert "DorotheusMatterProfileRequest" in schema["components"]["schemas"]
    assert "DorotheusMatterProfileEvaluationResponse" in schema["components"]["schemas"]
