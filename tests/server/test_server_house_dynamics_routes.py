"""Tests for /v1/houses/dynamics route."""
from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from moira import analytical_asc_speed, analytical_mc_speed
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.chart import (
    HOUSE_DYNAMICS_MAX_DT_MINUTES,
    HOUSE_DYNAMICS_MIN_DT_MINUTES,
)


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
    assert data["computation"] == {
        "engine_surface": "Moira.house_dynamics",
        "source_vessel": "HouseDynamics",
        "method": "centered_finite_difference",
        "independent_variable": "time",
        "half_step": 1.0,
        "half_step_unit": "minutes",
        "speed_unit": "degrees_per_day",
        "obliquity_held_fixed": False,
    }


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


@pytest.mark.parametrize(
    "dt_minutes",
    [
        HOUSE_DYNAMICS_MIN_DT_MINUTES / 2.0,
        HOUSE_DYNAMICS_MAX_DT_MINUTES + 0.001,
        True,
        "1.0",
    ],
)
def test_house_dynamics_rejects_unreliable_or_coercive_steps(
    client_with_engine: TestClient,
    dt_minutes,
) -> None:
    response = client_with_engine.post(
        "/v1/houses/dynamics",
        json={
            "dt": "2026-09-21T12:00:00Z",
            "latitude": 51.5074,
            "longitude": -0.1278,
            "dt_minutes": dt_minutes,
        },
    )
    assert response.status_code == 422
    assert response.json()["error_code"] == "validation_error"


@pytest.mark.parametrize("system", ["Whole Sign", "Solar Sign"])
def test_time_house_dynamics_rejects_discontinuous_cusp_systems(
    client_with_engine: TestClient,
    system: str,
) -> None:
    response = client_with_engine.post(
        "/v1/houses/dynamics",
        json={
            "dt": "2026-09-21T12:00:00Z",
            "latitude": 51.5074,
            "longitude": -0.1278,
            "system": system,
        },
    )

    assert response.status_code == 422
    assert "do not define" in response.json()["message"]


def test_armc_house_dynamics_rejects_whole_sign_discontinuity(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/houses/dynamics/armc",
        json={
            "armc": 90.0,
            "obliquity": 23.4392911,
            "latitude": 51.5074,
            "system": "Whole Sign",
            "darmc_deg": 0.001,
        },
    )

    assert response.status_code == 422
    assert "discontinuous" in response.json()["message"]


def test_armc_house_dynamics_rejects_effective_whole_sign_fallback(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/houses/dynamics/armc",
        json={
            "armc": 90.0,
            "obliquity": 23.4392911,
            "latitude": 80.0,
            "system": "Koch",
            "policy": {"polar_fallback": "fallback_to_whole_sign"},
        },
    )

    assert response.status_code == 422
    assert "Whole Sign cusps are discontinuous" in response.json()["message"]


def test_armc_solar_sign_preserves_fixed_anchor_partial_derivative(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/houses/dynamics/armc",
        json={
            "armc": 90.0,
            "obliquity": 23.4392911,
            "latitude": 51.5074,
            "system": "Solar Sign",
            "sun_longitude": 100.0,
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["house_cusps"]["effective_system"] == "S"
    assert all(
        cusp["speed_deg_per_day"] == pytest.approx(0.0, abs=1.0e-12)
        for cusp in response.json()["cusp_speeds"]
    )


def test_house_dynamics_openapi_exposes_all_public_surfaces() -> None:
    schema = create_app(ServerConfig(docs_enabled=False)).openapi()
    assert "/v1/houses/dynamics" in schema["paths"]
    assert "/v1/houses/dynamics/armc" in schema["paths"]
    assert "/v1/houses/dynamics/analytical" in schema["paths"]
    assert "HouseDynamicsFromArmcRequest" in schema["components"]["schemas"]
    assert "AnalyticalHouseDynamicsResponse" in schema["components"]["schemas"]


def test_house_dynamics_package_aggregators_export_transport_surface() -> None:
    from moira_server import models, serializers, services

    expected_models = {
        "AnalyticalHouseDynamicsRequest",
        "AnalyticalHouseDynamicsResponse",
        "CuspSpeedResponse",
        "HouseDynamicsComputationResponse",
        "HouseDynamicsFromArmcRequest",
        "HouseDynamicsRequest",
        "HouseDynamicsResponse",
        "PolarAdmissibilityRequest",
        "PolarAdmissibilityResponse",
        "PolarHouseWindowResponse",
    }
    assert expected_models <= set(models.__all__)
    assert {
        "compute_analytical_house_dynamics",
        "compute_house_dynamics",
        "compute_house_dynamics_from_armc",
        "compute_polar_admissibility",
    } <= set(services.__all__)
    assert {
        "serialize_analytical_house_dynamics",
        "serialize_house_dynamics",
        "serialize_polar_admissibility",
    } <= set(serializers.__all__)


def test_house_dynamics_from_armc_route(client_with_engine: TestClient) -> None:
    payload = {
        "armc": 135.0,
        "obliquity": 23.4392911,
        "latitude": 51.5074,
        "system": "placidus",
        "darmc_deg": 0.001,
    }
    response = client_with_engine.post("/v1/houses/dynamics/armc", json=payload)
    assert response.status_code == 200, response.text
    data = response.json()
    assert len(data["cusp_speeds"]) == 12
    assert data["house_cusps"]["effective_system"] == "P"
    assert data["computation"]["engine_surface"] == (
        "moira.houses.house_dynamics_from_armc"
    )
    assert data["computation"]["independent_variable"] == "armc"
    assert data["computation"]["obliquity_held_fixed"] is True
    assert abs(
        data["mc_speed_deg_per_day"]
        - analytical_mc_speed(payload["armc"], payload["obliquity"])
    ) < 0.001


def test_analytical_house_dynamics_route(client_with_engine: TestClient) -> None:
    payload = {
        "armc": 135.0,
        "obliquity": 23.4392911,
        "latitude": 51.5074,
    }
    response = client_with_engine.post(
        "/v1/houses/dynamics/analytical",
        json=payload,
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["mc_speed_deg_per_day"] == pytest.approx(
        analytical_mc_speed(payload["armc"], payload["obliquity"])
    )
    assert data["asc_speed_deg_per_day"] == pytest.approx(
        analytical_asc_speed(
            payload["armc"],
            payload["obliquity"],
            payload["latitude"],
        )
    )
    assert data["asc_available"] is True
    assert data["vertex_available"] is True
    assert data["computation"]["method"] == "analytical_derivative"


def test_analytical_house_dynamics_serializes_vertex_singularity_as_null(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/houses/dynamics/analytical",
        json={"armc": 135.0, "obliquity": 23.4392911, "latitude": 0.0},
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["vertex_available"] is False
    assert data["vertex_speed_deg_per_day"] is None
    assert data["anti_vertex_speed_deg_per_day"] is None
    assert data["vertex_unavailable_reason"]
