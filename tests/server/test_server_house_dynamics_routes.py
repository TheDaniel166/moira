"""Tests for /v1/houses/dynamics route."""
from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback


@pytest.fixture
def client_with_engine(
    moira_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client


def test_house_dynamics_route_placidus(client_with_engine: TestClient):
    """Test standard house dynamics computation via REST."""
    payload = {
        "dt": "2026-09-21T12:00:00Z",
        "latitude": 51.5074,
        "longitude": -0.1278,
        "system": "Placidus",
        "dt_minutes": 1.0,
    }
    response = client_with_engine.post("/v1/houses/dynamics", json=payload)
    assert response.status_code == 200, response.text
    
    data = response.json()
    assert "house_cusps" in data
    assert "cusp_speeds" in data
    assert len(data["cusp_speeds"]) == 12
    
    # Check cusp speed entries
    for i, cs in enumerate(data["cusp_speeds"], start=1):
        assert cs["house"] == i
        assert 0.0 <= cs["cusp_longitude"] < 360.0
        assert isinstance(cs["speed_deg_per_day"], float)
    
    assert data["asc_speed_deg_per_day"] > 0.0
    assert data["mc_speed_deg_per_day"] > 300.0
    assert abs(data["cusp_speeds"][0]["speed_deg_per_day"] - data["asc_speed_deg_per_day"]) < 1e-9


def test_house_dynamics_route_regiomontanus_and_campanus(client_with_engine: TestClient):
    """Test house dynamics across alternative quadrant systems."""
    expected_codes = {"Regiomontanus": "R", "Campanus": "C", "Koch": "K"}
    for sys_name, expected_code in expected_codes.items():
        payload = {
            "dt": "2026-09-21T12:00:00Z",
            "latitude": 51.5074,
            "longitude": -0.1278,
            "system": sys_name,
        }
        response = client_with_engine.post("/v1/houses/dynamics", json=payload)
        assert response.status_code == 200, f"Failed for {sys_name}: {response.text}"
        data = response.json()
        assert len(data["cusp_speeds"]) == 12
        assert data["house_cusps"]["effective_system"] == expected_code


def test_house_dynamics_route_custom_step(client_with_engine: TestClient):
    """Test house dynamics with custom finite-difference step."""
    payload = {
        "dt": "2026-09-21T12:00:00Z",
        "latitude": 51.5074,
        "longitude": -0.1278,
        "system": "Placidus",
        "dt_minutes": 0.5,
    }
    response = client_with_engine.post("/v1/houses/dynamics", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["mc_speed_deg_per_day"] > 300.0


def test_house_dynamics_rejects_timezone_naive_dt(client_with_engine: TestClient):
    """Test that timezone-naive datetime inputs are rejected."""
    payload = {
        "dt": "2026-09-21T12:00:00",  # No Z or offset
        "latitude": 51.5,
        "longitude": -0.1,
    }
    response = client_with_engine.post("/v1/houses/dynamics", json=payload)
    assert response.status_code in (400, 422)
