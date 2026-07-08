from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: object())
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as test_client:
        yield test_client


def test_openapi_schema_has_ordered_tag_metadata_and_redoc_groups() -> None:
    app = create_app(ServerConfig(docs_enabled=True))

    schema = app.openapi()
    tags = schema["tags"]
    tag_by_name = {tag["name"]: tag for tag in tags}

    assert [tag["name"] for tag in tags[:3]] == [
        "meta",
        "chart",
        "positions",
    ]
    assert tag_by_name["western-profile"]["x-family"] == "profile-bundles"
    assert tag_by_name["vedic-profile"]["x-displayName"] == "Vedic Profile Bundles"
    assert tag_by_name["muhurta"]["x-displayName"] == "Muhurta"
    assert tag_by_name["muhurta"]["x-family"] == "classical-vedic"
    assert "Vedic Muhurta" in tag_by_name["muhurta"]["description"]
    assert tag_by_name["website-chart-wheel"]["x-familyLabel"] == "Website and Batch Support"

    tag_groups = {group["name"]: group["tags"] for group in schema["x-tagGroups"]}
    assert tag_groups["Profile Bundles"] == ["western-profile", "vedic-profile"]
    assert "muhurta" in tag_groups["Classical and Vedic Doctrine"]
    assert "planetary-hours" in tag_groups["Phenomena and Visibility"]
    assert "website-chart-wheel" in tag_groups["Website and Batch Support"]


def test_route_catalog_lists_live_schema_routes(client: TestClient) -> None:
    response = client.get("/v1/meta/routes")

    assert response.status_code == 200
    body = response.json()
    paths = {route["path"] for route in body["routes"]}

    assert body["count"] == body["total_count"]
    assert body["count"] == len(body["routes"])
    assert "/v1/meta/routes" in paths
    assert "/v1/muhurta/direct/score" in paths
    assert "/openapi.json" not in paths
    assert "muhurta" in body["available_tags"]
    assert {
        family["family"]
        for family in body["available_families"]
    } >= {"operational", "profile-bundles", "classical-vedic", "phenomena", "website"}


def test_route_catalog_filters_by_tag_family_method_and_path(client: TestClient) -> None:
    response = client.get(
        "/v1/meta/routes",
        params={
            "family": "classical-vedic",
            "tag": "muhurta",
            "method": "post",
            "path_contains": "score",
        },
    )

    assert response.status_code == 200
    body = response.json()
    paths = {route["path"] for route in body["routes"]}

    assert body["filters"] == {
        "family": "classical-vedic",
        "tag": "muhurta",
        "method": "POST",
        "path_contains": "score",
        "include_hidden": False,
    }
    assert paths == {
        "/v1/muhurta/chart/score",
        "/v1/muhurta/direct/score",
        "/v1/muhurta/personal/score",
    }
    assert all(route["family"] == "classical-vedic" for route in body["routes"])
    assert all(route["methods"] == ["POST"] for route in body["routes"])
    assert all(route["tags"] == ["muhurta"] for route in body["routes"])
