"""Contract tests for polar house admissibility REST API endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from moira.constants import HouseSystem
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = [pytest.mark.loopback, pytest.mark.requires_ephemeris]


@pytest.fixture
def client_with_engine(moira_engine, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client


def test_polar_admissibility_campanus_at_80n(client_with_engine: TestClient) -> None:
    payload = {
        "latitude": 80.0,
        "system": "CAMPANUS",
        "armc_start": 0.0,
        "armc_end": 355.0,
        "armc_step": 5.0,
    }
    response = client_with_engine.post("/v1/houses/polar-admissibility", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["system"] == HouseSystem.CAMPANUS
    assert data["latitude"] == 80.0
    assert data["total_samples"] == 72
    assert data["valid_fraction"] > 0.0
    assert data["has_any_window"] is True
    assert len(data["windows"]) > 0


def test_polar_admissibility_regiomontanus_at_77n(client_with_engine: TestClient) -> None:
    payload = {
        "latitude": 77.0,
        "system": "REGIOMONTANUS",
        "armc_start": 0.0,
        "armc_end": 355.0,
        "armc_step": 5.0,
    }
    response = client_with_engine.post("/v1/houses/polar-admissibility", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["system"] == HouseSystem.REGIOMONTANUS
    assert data["valid_fraction"] > 0.5
    assert data["has_any_window"] is True


def test_polar_admissibility_topocentric_at_77n(client_with_engine: TestClient) -> None:
    payload = {
        "latitude": 77.0,
        "system": "TOPOCENTRIC",
        "armc_start": 0.0,
        "armc_end": 355.0,
        "armc_step": 5.0,
    }
    response = client_with_engine.post("/v1/houses/polar-admissibility", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["system"] == HouseSystem.TOPOCENTRIC
    assert data["valid_fraction"] > 0.0


def test_polar_admissibility_unsupported_system_raises_400(client_with_engine: TestClient) -> None:
    payload = {
        "latitude": 80.0,
        "system": "WHOLE_SIGN",
    }
    response = client_with_engine.post("/v1/houses/polar-admissibility", json=payload)
    assert response.status_code == 400
    assert "No polar admissibility scanner available" in response.json()["detail"]


def test_polar_admissibility_invalid_latitude_raises_422(client_with_engine: TestClient) -> None:
    payload = {
        "latitude": 95.0,
        "system": "CAMPANUS",
    }
    response = client_with_engine.post("/v1/houses/polar-admissibility", json=payload)
    assert response.status_code == 422
