from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


@pytest.fixture
def client_with_engine(
    moira_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client


@pytest.mark.requires_ephemeris
def test_visibility_assessment_route_matches_engine_selected_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    direct = moira_engine.visibility_tonight("Venus", 2451545.0, 0.0, 0.0)

    response = client_with_engine.post(
        "/v1/visibility/assessment",
        json={
            "body": "Venus",
            "jd_ut": 2451545.0,
            "lat": 0.0,
            "lon": 0.0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["body"] == direct.body
    assert body["criterion_family"] == direct.criterion_family.value
    assert body["effective_limiting_magnitude"] == pytest.approx(direct.effective_limiting_magnitude)
    assert body["apparent_altitude_deg"] == pytest.approx(direct.apparent_altitude_deg)
    assert body["observable"] is direct.observable


@pytest.mark.requires_ephemeris
def test_visibility_tonight_route_matches_engine_alias_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    direct = moira_engine.visibility_tonight("Venus", 2451545.0, 35.0, 35.0)

    response = client_with_engine.post(
        "/v1/visibility/tonight",
        json={
            "body": "Venus",
            "jd_ut": 2451545.0,
            "lat": 35.0,
            "lon": 35.0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["body"] == "Venus"
    assert body["true_altitude_deg"] == pytest.approx(direct.true_altitude_deg)
    assert body["solar_elongation_deg"] == pytest.approx(direct.solar_elongation_deg)
    assert body["observable"] is direct.observable


@pytest.mark.requires_ephemeris
def test_visibility_routes_reject_unsupported_target_with_validation_envelope(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/visibility/assessment",
        json={
            "body": "NotAPlanet",
            "jd_ut": 2451545.0,
            "lat": 0.0,
            "lon": 0.0,
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert "NotAPlanet" in body["message"]
