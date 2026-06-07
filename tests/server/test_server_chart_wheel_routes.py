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


def test_chart_wheel_route_is_registered(
    moira_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)

    app = create_app(ServerConfig(docs_enabled=True))
    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/v1/website/chart-wheel/packet" in paths
    assert "/v1/website/chart-wheel/presets" in paths
    assert "/v1/website/chart-wheel/validate" in paths


def test_chart_wheel_presets_return_designer_contracts(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.get("/v1/website/chart-wheel/presets")

    assert response.status_code == 200
    body = response.json()
    names = {preset["name"] for preset in body}
    assert {"classic", "dense", "minimal", "print", "dark"} <= names
    assert all("config" in preset for preset in body)


def test_chart_wheel_validate_reports_errors_and_warnings(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/website/chart-wheel/validate",
        json={
            "config": {
                "orientation": "north_by_guess",
                "preset": "classic",
                "aspect_radius": 0.95,
                "point_radius": 0.72,
                "label_radius": 0.70,
            }
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is False
    codes = {warning["code"] for warning in body["warnings"]}
    assert "unknown_orientation" in codes
    assert "aspect_radius_not_inside_points" in codes
    assert "label_radius_inside_points" in codes


@pytest.mark.requires_ephemeris
def test_chart_wheel_packet_preserves_chart_truth_and_emits_primitives(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    direct = moira_engine.chart(dt, bodies=["Sun", "Moon"], include_nodes=False)

    response = client_with_engine.post(
        "/v1/website/chart-wheel/packet",
        json={
            "chart": {
                "dt": dt.isoformat(),
                "bodies": ["Sun", "Moon"],
                "include_nodes": False,
            },
            "config": {
                "include_nodes": False,
                "include_aspects": False,
                "orientation": "aries_left",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["chart"]["planets"]["Sun"]["longitude"] == pytest.approx(direct.planets["Sun"].longitude)
    assert body["chart"]["planets"]["Moon"]["longitude"] == pytest.approx(direct.planets["Moon"].longitude)
    assert body["houses"] is None
    assert body["orientation_offset_deg"] == pytest.approx(180.0)
    assert len(body["zodiac"]) == 12
    assert len(body["points"]) == 2
    assert body["aspects"] == []
    assert body["house_sectors"] == []
    assert body["warnings"] == []
    assert {point["key"] for point in body["points"]} == {"Sun", "Moon"}
    assert all(point["glyph"] for point in body["points"])
    assert all("label_position" in point for point in body["points"])


@pytest.mark.requires_ephemeris
def test_chart_wheel_packet_with_houses_places_points_and_cusps(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    houses = moira_engine.houses(dt, latitude=51.5, longitude=-0.1)

    response = client_with_engine.post(
        "/v1/website/chart-wheel/packet",
        json={
            "chart": {
                "dt": dt.isoformat(),
                "bodies": ["Sun", "Moon"],
                "include_nodes": True,
            },
            "houses": {
                "latitude": 51.5,
                "longitude": -0.1,
            },
            "config": {
                "include_nodes": True,
                "include_aspects": True,
                "orientation": "ascendant_left",
                "aspect_tier": 0,
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["houses"]["asc"] == pytest.approx(houses.asc)
    assert body["orientation_offset_deg"] == pytest.approx((180.0 + houses.asc) % 360.0)
    assert len(body["house_cusps"]) == 12
    assert len(body["house_sectors"]) == 12
    assert all(point["house"] is not None for point in body["points"])
    assert all("position" in point for point in body["points"])
    assert all("start" in aspect and "end" in aspect for aspect in body["aspects"])
    assert all("stroke_key" in aspect for aspect in body["aspects"])


def test_chart_wheel_packet_rejects_house_dependent_orientation_without_houses(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/website/chart-wheel/packet",
        json={
            "chart": {
                "dt": "2000-01-01T12:00:00+00:00",
                "bodies": ["Sun"],
            },
            "config": {
                "orientation": "ascendant_left",
            },
        },
    )

    assert response.status_code == 422
    assert "requires houses" in response.json()["message"]


def test_chart_wheel_packet_rejects_invalid_config_errors(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/website/chart-wheel/packet",
        json={
            "chart": {
                "dt": "2000-01-01T12:00:00+00:00",
                "bodies": ["Sun"],
            },
            "config": {
                "orientation": "north_by_guess",
            },
        },
    )

    assert response.status_code == 422
    assert "unknown_orientation" in response.json()["message"]
