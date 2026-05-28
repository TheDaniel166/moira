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


def _assert_validation_envelope(response, *, message_fragment: str | None = None) -> None:
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert body["request_id"]
    assert response.headers["X-Request-ID"] == body["request_id"]
    if message_fragment is not None:
        assert message_fragment in body["message"]


def test_chart_route_rejects_missing_required_field_with_server_envelope(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/chart",
        json={"bodies": ["Sun"]},
    )

    _assert_validation_envelope(response, message_fragment="Field required")
    assert "body.dt" in response.json()["details"]


def test_positions_sky_route_rejects_schema_type_errors_with_server_envelope(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/positions/sky",
        json={
            "dt": "2000-01-01T12:00:00+00:00",
            "body": "Venus",
            "latitude": "north",
            "longitude": -0.1,
        },
    )

    _assert_validation_envelope(response)
    assert "body.latitude" in response.json()["details"]


@pytest.mark.requires_ephemeris
def test_route_level_value_errors_keep_request_ids_across_predictive_surfaces(
    client_with_engine: TestClient,
) -> None:
    transit_response = client_with_engine.post(
        "/v1/transits/search",
        json={
            "body": "Sun",
            "target_lon": 300.0,
            "jd_start": 2451545.0 + 10.0,
            "jd_end": 2451545.0,
        },
    )
    return_response = client_with_engine.post(
        "/v1/returns/planet",
        json={
            "body": "Venus",
            "natal_lon": 123.0,
            "jd_start": 2451545.0,
            "direction": "sideways",
        },
    )

    _assert_validation_envelope(transit_response, message_fragment="strictly increasing")
    _assert_validation_envelope(return_response, message_fragment="direction")


@pytest.mark.requires_ephemeris
def test_batch_progressions_route_keeps_mixed_hostile_items_item_local(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/batch/progressions",
        json={
            "requests": [
                {
                    "technique": "secondary",
                    "natal_dt": "2000-01-01T12:00:00+00:00",
                    "target_date": "2001-01-01T00:00:00+00:00",
                    "bodies": ["Sun"],
                },
                {
                    "technique": "secondary",
                    "natal_dt": "2000-01-01T12:00:00+00:00",
                    "natal_jd_ut": 2451545.0,
                    "target_date": "2001-01-01T00:00:00+00:00",
                },
                {
                    "technique": "daily_house_frame",
                    "natal_dt": "2000-01-01T12:00:00+00:00",
                    "target_date": "2001-01-01T00:00:00+00:00",
                },
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["results"][0]["ok"] is True
    assert body["results"][1]["ok"] is False
    assert "provide natal_jd_ut or natal_dt, not both" in body["results"][1]["failure"]["message"]
    assert body["results"][2]["ok"] is False
    assert "requires latitude" in body["results"][2]["failure"]["message"]


def test_batch_events_route_rejects_request_schema_failures_before_engine_dispatch(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/batch/events",
        json={
            "requests": [
                {
                    "kind": "station",
                    "body": "Mercury",
                    "jd_start": 1.0,
                }
            ]
        },
    )

    _assert_validation_envelope(response, message_fragment="Field required")
    assert "body.requests.0.jd_end" in response.json()["details"]
