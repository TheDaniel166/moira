"""REST admission tests for circumambulations, transmissions, and offices."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira.circumambulations import circumambulate
from moira.hellenistic_offices import OFFICE_NOT_ADMITTED_REASON
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback


class _FakeEngine:
    pass


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: _FakeEngine())
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as test_client:
        yield test_client


def test_circumambulations_route_preserves_bound_walk(client: TestClient) -> None:
    direct = circumambulate(10.0, 2451545.0, significator_name="Ascendant")
    response = client.post(
        "/v1/hellenistic/circumambulations",
        json={
            "significator_name": "Ascendant",
            "significator_longitude": 10.0,
            "start_jd": 2451545.0,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "evaluated"
    assert body["periods"][0]["lord"] == direct.periods[0].lord
    assert body["periods"][0]["years"] == pytest.approx(direct.periods[0].years or 0.0)
    assert body["provenance"]["engine_entrypoint"] == "circumambulate"


def test_transmissions_route_has_no_effect_fields(client: TestClient) -> None:
    response = client.post(
        "/v1/hellenistic/transmissions",
        json={
            "positions": {"Sun": 10.0, "Moon": 45.0},
            "asc_longitude": 15.0,
            "decennial_l1": "Sun",
            "decennial_l2": "Moon",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "evaluated"
    assert body["edges"]
    assert "effect" not in body
    assert all("effect" not in edge for edge in body["edges"])


def test_offices_route_fails_closed_without_hyleg(client: TestClient) -> None:
    response = client.post(
        "/v1/hellenistic/offices",
        json={
            "positions": {
                "Sun": 10.0,
                "Moon": 45.0,
                "Mercury": 80.0,
                "Venus": 120.0,
                "Mars": 160.0,
                "Jupiter": 220.0,
                "Saturn": 300.0,
            },
            "is_day_chart": True,
            "asc_longitude": 15.0,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_evaluable"
    assert body["predominator"] is None
    assert body["house_master"] is None
    assert body["reason"] == OFFICE_NOT_ADMITTED_REASON
    assert body["candidates"]


def test_hellenistic_system_routes_are_registered(client: TestClient) -> None:
    paths = {route.path for route in client.app.routes}
    assert {
        "/v1/hellenistic/circumambulations",
        "/v1/hellenistic/transmissions",
        "/v1/hellenistic/offices",
    } <= paths


def test_system_routes_reject_extra_keys(client: TestClient) -> None:
    response = client.post(
        "/v1/hellenistic/offices",
        json={
            "positions": {"Sun": 10.0},
            "is_day_chart": True,
            "hyleg": "Sun",
        },
    )
    assert response.status_code == 422
    assert "Extra inputs are not permitted" in response.json()["message"]
