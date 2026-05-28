from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest

from moira.batch import (
    BatchFailure,
    EventBatchRequest,
    EventBatchResult,
)
from moira.stations import StationEvent
from moira.transits_aspects import AspectTransitEvent
from moira.transits_equatorial import EquatorialTransitEvent
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
def test_batch_charts_route_preserves_item_level_failure_isolation(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/batch/charts",
        json={
            "requests": [
                {"dt": "2000-01-01T12:00:00+00:00", "bodies": ["Sun"]},
                {"dt": "2000-01-01T12:00:00+00:00", "bodies": ["NotAPlanet"]},
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 2
    assert body["results"][0]["ok"] is True
    assert body["results"][0]["chart"]["planets"]["Sun"]["name"] == "Sun"
    assert body["results"][1]["ok"] is False
    assert body["results"][1]["failure"]["error_type"] in {"KeyError", "ValueError"}
    assert "NotAPlanet" in body["results"][1]["failure"]["message"]


@pytest.mark.requires_ephemeris
def test_batch_transits_route_preserves_item_level_failure_isolation(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/batch/transits",
        json={
            "requests": [
                {
                    "body": "Sun",
                    "target_lon": 300.0,
                    "jd_start": 2451545.0,
                    "jd_end": 2451545.0 + 365.25,
                },
                {
                    "body": "NotAPlanet",
                    "target_lon": 300.0,
                    "jd_start": 2451545.0,
                    "jd_end": 2451545.0 + 365.25,
                },
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 2
    assert body["results"][0]["ok"] is True
    assert body["results"][0]["count"] >= 1
    assert body["results"][0]["events"][0]["body"] == "Sun"
    assert body["results"][1]["ok"] is False
    assert "NotAPlanet" in body["results"][1]["failure"]["message"]


@pytest.mark.requires_ephemeris
def test_batch_returns_and_progressions_routes_preserve_success_and_failure_items(
    client_with_engine: TestClient,
) -> None:
    returns_response = client_with_engine.post(
        "/v1/batch/returns",
        json={
            "requests": [
                {"kind": "solar_return", "natal_lon": 280.0, "year": 2001},
                {"kind": "not_real", "natal_lon": 280.0},
            ]
        },
    )
    progressions_response = client_with_engine.post(
        "/v1/batch/progressions",
        json={
            "requests": [
                {
                    "technique": "secondary",
                    "natal_dt": "2000-01-01T12:00:00+00:00",
                    "target_date": "2001-01-01T00:00:00+00:00",
                    "bodies": ["Sun", "Moon"],
                },
                {
                    "technique": "not_real",
                    "natal_dt": "2000-01-01T12:00:00+00:00",
                    "target_date": "2001-01-01T00:00:00+00:00",
                },
            ]
        },
    )

    assert returns_response.status_code == 200
    returns_body = returns_response.json()
    assert returns_body["results"][0]["ok"] is True
    assert returns_body["results"][0]["result"]["return_type"] == "solar_return"
    assert returns_body["results"][1]["ok"] is False
    assert "not_real" in returns_body["results"][1]["failure"]["message"]

    assert progressions_response.status_code == 200
    progressions_body = progressions_response.json()
    assert progressions_body["results"][0]["ok"] is True
    assert progressions_body["results"][0]["result"]["result_type"] in {
        "progressed_chart",
        "progressed_declination_chart",
        "progressed_house_frame",
    }
    assert progressions_body["results"][1]["ok"] is False
    assert "batch_progressions: technique" in progressions_body["results"][1]["failure"]["message"]


def test_batch_events_route_serializes_heterogeneous_event_payloads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _FakeEngine:
        def batch_events(self, requests):
            assert len(requests) == 3
            return (
                EventBatchResult(
                    request=requests[0],
                    events=(StationEvent("Mercury", "retrograde", 2451545.5, 271.2),),
                ),
                EventBatchResult(
                    request=requests[1],
                    events=(
                        AspectTransitEvent(
                            "Mars",
                            "Venus",
                            90.0,
                            1.0,
                            2451546.5,
                            2451546.25,
                            2451546.75,
                            False,
                            "forward",
                        ),
                    ),
                ),
                EventBatchResult(
                    request=requests[2],
                    events=(
                        EquatorialTransitEvent(
                            "Moon",
                            "Sun",
                            True,
                            2451547.5,
                            -12.3,
                            "forward",
                        ),
                    ),
                ),
            )

    monkeypatch.setattr("moira_server.app.create_engine", lambda config: _FakeEngine())
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        response = client.post(
            "/v1/batch/events",
            json={
                "requests": [
                    {"kind": "station", "body": "Mercury", "jd_start": 1.0, "jd_end": 2.0},
                    {
                        "kind": "aspect_transit",
                        "body": "Mars",
                        "jd_start": 1.0,
                        "jd_end": 2.0,
                        "target": "Venus",
                        "angle": 90.0,
                        "orb": 1.0,
                    },
                    {
                        "kind": "declination_transit",
                        "body": "Moon",
                        "jd_start": 1.0,
                        "jd_end": 2.0,
                        "target": "Sun",
                        "is_contra_parallel": True,
                    },
                ]
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["results"][0]["events"][0]["event_type"] == "station"
    assert body["results"][1]["events"][0]["event_type"] == "aspect_transit"
    assert body["results"][2]["events"][0]["event_type"] == "declination_transit"
    assert body["results"][2]["events"][0]["is_contra_parallel"] is True


@pytest.mark.requires_ephemeris
def test_batch_progressions_route_serializes_all_result_families(
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
                    "bodies": ["Sun", "Moon"],
                },
                {
                    "technique": "secondary_declination",
                    "natal_dt": "2000-01-01T12:00:00+00:00",
                    "target_date": "2001-01-01T00:00:00+00:00",
                    "bodies": ["Sun", "Moon"],
                },
                {
                    "technique": "daily_house_frame",
                    "natal_dt": "2000-01-01T12:00:00+00:00",
                    "target_date": "2001-01-01T00:00:00+00:00",
                    "latitude": 51.5,
                    "longitude": -0.1,
                    "system": "P",
                },
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert [item["ok"] for item in body["results"]] == [True, True, True]
    assert body["results"][0]["result"]["result_type"] == "progressed_chart"
    assert "positions" in body["results"][0]["result"]
    assert body["results"][1]["result"]["result_type"] == "progressed_declination_chart"
    assert "positions" in body["results"][1]["result"]
    assert body["results"][2]["result"]["result_type"] == "progressed_house_frame"
    assert "houses" in body["results"][2]["result"]


@pytest.mark.requires_ephemeris
def test_batch_progressions_route_preserves_item_local_adversarial_failures(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/batch/progressions",
        json={
            "requests": [
                {
                    "technique": "planetary_arc",
                    "natal_dt": "2000-01-01T12:00:00+00:00",
                    "target_date": "2001-01-01T00:00:00+00:00",
                },
                {
                    "technique": "secondary",
                    "natal_dt": "2000-01-01T12:00:00+00:00",
                    "target_date": "2001-01-01T00:00:00+00:00",
                    "bodies": ["Sun"],
                },
                {
                    "technique": "secondary",
                    "target_date": "2001-01-01T00:00:00+00:00",
                    "bodies": ["Sun"],
                },
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["results"]) == 3
    assert body["results"][0]["ok"] is False
    assert "requires arc_body" in body["results"][0]["failure"]["message"]
    assert body["results"][1]["ok"] is True
    assert body["results"][1]["result"]["result_type"] == "progressed_chart"
    assert body["results"][2]["ok"] is False
    assert "requires natal_jd_ut or natal_dt" in body["results"][2]["failure"]["message"]
