from __future__ import annotations

from datetime import datetime, timezone

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
def test_chart_route_matches_engine_selected_truth(client_with_engine: TestClient, moira_engine) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    direct = moira_engine.chart(dt, bodies=["Sun", "Moon"], include_nodes=True)

    response = client_with_engine.post(
        "/v1/chart",
        json={
            "dt": dt.isoformat(),
            "bodies": ["Sun", "Moon"],
            "include_nodes": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["jd_ut"] == pytest.approx(direct.jd_ut)
    assert body["obliquity"] == pytest.approx(direct.obliquity)
    assert body["delta_t"] == pytest.approx(direct.delta_t)
    assert body["planets"]["Sun"]["longitude"] == pytest.approx(direct.planets["Sun"].longitude)
    assert body["planets"]["Moon"]["speed"] == pytest.approx(direct.planets["Moon"].speed)
    assert body["nodes"]["True Node"]["longitude"] == pytest.approx(direct.nodes["True Node"].longitude)


@pytest.mark.requires_ephemeris
def test_planet_position_route_matches_engine_selected_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    direct = moira_engine.chart(dt, bodies=["Mars"], include_nodes=False).planets["Mars"]

    response = client_with_engine.post(
        "/v1/positions/planet",
        json={
            "dt": dt.isoformat(),
            "body": "Mars",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Mars"
    assert body["longitude"] == pytest.approx(direct.longitude)
    assert body["latitude"] == pytest.approx(direct.latitude)
    assert body["speed"] == pytest.approx(direct.speed)
    assert body["retrograde"] is direct.retrograde


@pytest.mark.requires_ephemeris
def test_planet_position_route_preserves_topocentric_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    direct = moira_engine.chart(
        dt,
        bodies=["Moon"],
        include_nodes=False,
        observer_lat=40.7128,
        observer_lon=-74.0060,
        observer_elev_m=10.0,
    ).planets["Moon"]

    response = client_with_engine.post(
        "/v1/positions/planet",
        json={
            "dt": dt.isoformat(),
            "body": "Moon",
            "observer_lat": 40.7128,
            "observer_lon": -74.0060,
            "observer_elev_m": 10.0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Moon"
    assert body["is_topocentric"] is True
    assert body["longitude"] == pytest.approx(direct.longitude)
    assert body["latitude"] == pytest.approx(direct.latitude)
    assert body["distance_au"] == pytest.approx(direct.distance_au)


@pytest.mark.requires_ephemeris
def test_sky_position_route_matches_engine_selected_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    direct = moira_engine.sky_position(dt, "Venus", 51.5, -0.1)

    response = client_with_engine.post(
        "/v1/positions/sky",
        json={
            "dt": dt.isoformat(),
            "body": "Venus",
            "latitude": 51.5,
            "longitude": -0.1,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Venus"
    assert body["right_ascension"] == pytest.approx(direct.right_ascension)
    assert body["declination"] == pytest.approx(direct.declination)
    assert body["azimuth"] == pytest.approx(direct.azimuth)
    assert body["altitude"] == pytest.approx(direct.altitude)


@pytest.mark.requires_ephemeris
def test_houses_route_matches_engine_selected_truth(client_with_engine: TestClient, moira_engine) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    direct = moira_engine.houses(dt, latitude=51.5, longitude=-0.1)

    response = client_with_engine.post(
        "/v1/houses",
        json={
            "dt": dt.isoformat(),
            "latitude": 51.5,
            "longitude": -0.1,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["system"] == direct.system
    assert body["effective_system"] == direct.effective_system
    assert body["asc"] == pytest.approx(direct.asc)
    assert body["mc"] == pytest.approx(direct.mc)
    assert body["cusps"][0] == pytest.approx(direct.cusps[0])


def test_phase_two_routes_reject_naive_datetimes_as_validation_failures(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/chart",
        json={"dt": "2000-01-01T12:00:00", "bodies": ["Sun"]},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert "timezone-aware" in body["message"]


@pytest.mark.requires_ephemeris
def test_planet_position_route_rejects_invalid_body_with_validation_envelope(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/positions/planet",
        json={
            "dt": "2000-01-01T12:00:00+00:00",
            "body": "NotAPlanet",
        },
    )

    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert "NotAPlanet" in body["message"]
