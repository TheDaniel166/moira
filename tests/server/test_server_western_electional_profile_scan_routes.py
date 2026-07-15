"""REST and OpenAPI evidence for named Western profile scanning."""

from __future__ import annotations

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


def _payload() -> dict:
    return {
        "profile_id": "ramesey_moon_condition_v1",
        "jd_start": 2451545.0,
        "jd_end": 2451545.0 + 1.0 / 24.0,
        "latitude": 51.5074,
        "longitude": -0.1278,
        "house_system": HouseSystem.REGIOMONTANUS,
        "qualification_statuses": [
            "clear_of_profile_impediments",
            "one_or_more_profile_impediments",
            "indeterminate",
        ],
        "policy": {
            "step_days": 1.0 / 24.0,
            "max_scan_points": 2,
            "max_windows": 4,
        },
        "include_qualifying_jds": True,
    }


def test_profile_windows_route_scans_real_de441_profile(client_and_app) -> None:
    client, _ = client_and_app
    response = client.post("/v1/electional/western/profile-windows", json=_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["profile_id"] == "ramesey_moon_condition_v1"
    assert body["scan_point_count"] == 2
    assert sum(item["count"] for item in body["status_counts"]) == 2
    assert len(body["samples"]) == 2
    assert all("triggered_rule_ids" in sample for sample in body["samples"])
    assert all("not_evaluable_rule_ids" in sample for sample in body["samples"])
    assert all(sample["qualifies"] is True for sample in body["samples"])
    assert body["windows"][0]["qualifying_count"] == 2
    assert body["scoring"] == "not_provided"
    assert body["ranking"] == "not_provided"
    assert body["continuous_boundary_claim"] == "not_provided"
    assert body["provenance"]["facade_entrypoint"] == "Moira.western_electional_profile_windows"


def test_profile_windows_route_rejects_cross_profile_parameters(client_and_app) -> None:
    client, _ = client_and_app
    payload = _payload()
    payload["sahl_burnt_path_variant"] = "dykes_glossary_fall_degrees_19_libra_to_3_scorpio"
    response = client.post("/v1/electional/western/profile-windows", json=payload)
    assert response.status_code == 422


def test_profile_windows_route_requires_explicit_qualification_statuses(
    client_and_app,
) -> None:
    client, _ = client_and_app
    payload = _payload()
    payload.pop("qualification_statuses")
    response = client.post("/v1/electional/western/profile-windows", json=payload)
    assert response.status_code == 422


def test_profile_windows_openapi_is_typed(client_and_app) -> None:
    _, app = client_and_app
    schema = app.openapi()
    operation = schema["paths"]["/v1/electional/western/profile-windows"]["post"]
    assert operation["responses"]["200"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/WesternProfileWindowsResponse"
    }
    assert "WesternProfileWindowsRequest" in schema["components"]["schemas"]
    assert "WesternProfileWindowResponse" in schema["components"]["schemas"]
    assert "WesternProfileSampleWitnessResponse" in schema["components"]["schemas"]
