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
def test_transit_search_route_preserves_selected_event_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    direct = moira_engine.transits("Sun", 300.0, 2451545.0, 2451545.0 + 365.25)

    response = client_with_engine.post(
        "/v1/transits/search",
        json={
            "body": "Sun",
            "target_lon": 300.0,
            "jd_start": 2451545.0,
            "jd_end": 2451545.0 + 365.25,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["events"]) == len(direct)
    assert body["events"][0]["jd_ut"] == pytest.approx(direct[0].jd_ut)
    assert body["events"][0]["direction"] == direct[0].direction
    assert body["events"][0]["relation"]["relation_kind"] == direct[0].relation.relation_kind.value
    assert body["events"][0]["classification"]["search"]["wrapper_kind"] == direct[0].classification.search.wrapper_kind.value
    assert body["events"][0]["computation_truth"]["target_truth"]["resolved_name"] == direct[0].computation_truth.target_truth.resolved_name


@pytest.mark.requires_ephemeris
def test_ingress_search_route_preserves_sign_and_boundary_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    direct = moira_engine.ingresses("Sun", 2451545.0, 2451545.0 + 40.0)

    response = client_with_engine.post(
        "/v1/transits/ingresses",
        json={
            "body": "Sun",
            "jd_start": 2451545.0,
            "jd_end": 2451545.0 + 40.0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["events"]) == len(direct)
    assert body["events"][0]["sign"] == direct[0].sign
    assert body["events"][0]["sign_longitude"] == pytest.approx(direct[0].sign_longitude)
    assert body["events"][0]["relation"]["basis"] == direct[0].relation.basis.value


@pytest.mark.requires_ephemeris
def test_next_ingress_route_matches_engine_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    direct = moira_engine.next_ingress("Sun", 2451545.0)

    response = client_with_engine.post(
        "/v1/transits/next-ingress",
        json={
            "body": "Sun",
            "jd_start": 2451545.0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["sign"] == direct.sign
    assert body["jd_ut"] == pytest.approx(direct.jd_ut)
    assert body["direction"] == direct.direction


@pytest.mark.requires_ephemeris
def test_return_routes_match_engine_selected_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    natal = moira_engine.chart(dt, bodies=["Sun", "Moon", "Venus"], include_nodes=False)

    solar_direct = moira_engine.solar_return(natal.planets["Sun"].longitude, 2001)
    lunar_direct = moira_engine.lunar_return(natal.planets["Moon"].longitude, natal.jd_ut + 1.0)
    planet_direct = moira_engine.planet_return("Venus", natal.planets["Venus"].longitude, natal.jd_ut + 1.0)

    solar_response = client_with_engine.post(
        "/v1/returns/solar",
        json={"natal_sun_lon": natal.planets["Sun"].longitude, "year": 2001},
    )
    lunar_response = client_with_engine.post(
        "/v1/returns/lunar",
        json={"natal_moon_lon": natal.planets["Moon"].longitude, "jd_start": natal.jd_ut + 1.0},
    )
    planet_response = client_with_engine.post(
        "/v1/returns/planet",
        json={
            "body": "Venus",
            "natal_lon": natal.planets["Venus"].longitude,
            "jd_start": natal.jd_ut + 1.0,
        },
    )

    assert solar_response.status_code == 200
    assert solar_response.json()["return_type"] == "solar_return"
    assert solar_response.json()["jd_ut"] == pytest.approx(solar_direct)

    assert lunar_response.status_code == 200
    assert lunar_response.json()["return_type"] == "lunar_return"
    assert lunar_response.json()["jd_ut"] == pytest.approx(lunar_direct)

    assert planet_response.status_code == 200
    assert planet_response.json()["body"] == "Venus"
    assert planet_response.json()["jd_ut"] == pytest.approx(planet_direct)


@pytest.mark.requires_ephemeris
def test_lunar_phases_route_matches_engine_phase_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    direct = moira_engine.moon_phases(2451545.0, 2451545.0 + 40.0)

    response = client_with_engine.post(
        "/v1/lunar-phases",
        json={
            "jd_start": 2451545.0,
            "jd_end": 2451545.0 + 40.0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["events"]) == len(direct)
    assert body["events"][0]["phase_type"] == direct[0].phenomenon
    assert body["events"][0]["jd_ut"] == pytest.approx(direct[0].jd_ut)
    assert body["events"][0]["phase_angle"] == pytest.approx(direct[0].value)


def test_phase_three_routes_reject_reversed_windows_and_invalid_bodies(
    client_with_engine: TestClient,
) -> None:
    reversed_window = client_with_engine.post(
        "/v1/lunar-phases",
        json={"jd_start": 2451545.0 + 10.0, "jd_end": 2451545.0},
    )
    invalid_body = client_with_engine.post(
        "/v1/returns/planet",
        json={"body": "NotAPlanet", "natal_lon": 123.0, "jd_start": 2451545.0},
    )

    assert reversed_window.status_code == 422
    assert reversed_window.json()["error_code"] == "validation_error"
    assert "jd_end" in reversed_window.json()["message"]

    assert invalid_body.status_code == 422
    assert invalid_body.json()["error_code"] == "validation_error"
    assert "NotAPlanet" in invalid_body.json()["message"]
