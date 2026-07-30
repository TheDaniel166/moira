"""P10-02 Local Space route tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira.local_space import local_space_positions
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.local_space import LocalSpaceChartPositionsRequest
from moira_server.serializers.local_space import serialize_local_space_positions
from moira_server.services.local_space import compute_local_space_chart_positions


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


_DT_ISO = "2000-01-01T12:00:00Z"
_DIRECT_POSITIONS = {
    "Meridian": {"right_ascension": 0.0, "declination": 0.0},
    "East": {"right_ascension": 90.0, "declination": 0.0},
}
_DIRECT_RA_DEC = {
    "Meridian": (0.0, 0.0),
    "East": (90.0, 0.0),
}


def _assert_validation_envelope(response, *, message_fragment: str | None = None) -> None:
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert body["request_id"]
    assert response.headers["X-Request-ID"] == body["request_id"]
    if message_fragment is not None:
        assert message_fragment in body["message"]


def _position_map(positions: list[dict]) -> dict[str, dict]:
    return {position["body"]: position for position in positions}


def test_local_space_direct_positions_route_matches_engine_truth(
    client_with_engine: TestClient,
) -> None:
    expected = {
        position.body: position
        for position in local_space_positions(_DIRECT_RA_DEC, latitude=0.0, lst_deg=0.0)
    }

    response = client_with_engine.post(
        "/v1/local-space/positions",
        json={
            "positions": _DIRECT_POSITIONS,
            "latitude": 0.0,
            "lst_deg": 0.0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    positions = _position_map(body["positions"])
    assert set(positions) == set(expected)
    assert positions["Meridian"]["azimuth"] == pytest.approx(expected["Meridian"].azimuth)
    assert positions["Meridian"]["altitude"] == pytest.approx(expected["Meridian"].altitude)
    assert positions["Meridian"]["is_above"] is expected["Meridian"].is_above
    assert positions["Meridian"]["compass_direction"] == expected["Meridian"].compass_direction()
    assert [position["azimuth"] for position in body["positions"]] == sorted(
        position["azimuth"] for position in body["positions"]
    )
    provenance = body["provenance"]
    assert provenance["coordinate_source"] == "direct_ra_dec"
    assert provenance["observer"]["source"] == "direct_request"
    assert provenance["observer"]["latitude"] == 0.0
    assert provenance["lst_deg"] == 0.0
    assert provenance["stage_sequence"][0] == "direct_ra_dec_validation"


@pytest.mark.requires_ephemeris
def test_local_space_chart_positions_route_matches_service_truth(
    client_with_engine: TestClient,
    moira_engine,
) -> None:
    payload = {
        "dt": _DT_ISO,
        "bodies": ["Sun"],
        "observer_lat": 40.7128,
        "observer_lon": -74.0060,
    }
    expected = serialize_local_space_positions(
        compute_local_space_chart_positions(
            moira_engine,
            LocalSpaceChartPositionsRequest.model_validate(payload),
        )
    ).model_dump(mode="json")

    response = client_with_engine.post("/v1/local-space/chart/positions", json=payload)

    assert response.status_code == 200
    assert response.json() == expected
    provenance = response.json()["provenance"]
    assert provenance["coordinate_source"] == "chart_apparent_topocentric_ra_dec"
    assert provenance["observer"]["source"] == "chart_request"
    assert provenance["returned_bodies"] == ["Sun"]
    assert provenance["stage_sequence"][0] == "datetime_validation"


def test_local_space_routes_are_registered(client_with_engine: TestClient) -> None:
    paths = {
        route.path
        for route in client_with_engine.app.routes
        if route.path.startswith("/v1/local-space")
    }

    assert paths == {
        "/v1/local-space/positions",
        "/v1/local-space/chart/positions",
    }


def test_local_space_direct_route_rejects_empty_positions(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/local-space/positions",
        json={"positions": {}, "latitude": 0.0, "lst_deg": 0.0},
    )

    _assert_validation_envelope(response, message_fragment="positions must be non-empty")


def test_local_space_direct_route_rejects_non_finite_ra_dec(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/local-space/positions",
        json={
            "positions": {"Sun": {"right_ascension": "NaN", "declination": 0.0}},
            "latitude": 0.0,
            "lst_deg": 0.0,
        },
    )

    _assert_validation_envelope(response, message_fragment="RA/Dec")


def test_local_space_direct_route_rejects_invalid_declination(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/local-space/positions",
        json={
            "positions": {"Sun": {"right_ascension": 0.0, "declination": 91.0}},
            "latitude": 0.0,
            "lst_deg": 0.0,
        },
    )

    _assert_validation_envelope(response, message_fragment="declination")


def test_local_space_direct_route_rejects_invalid_latitude(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/local-space/positions",
        json={
            "positions": {"Sun": {"right_ascension": 0.0, "declination": 0.0}},
            "latitude": 91.0,
            "lst_deg": 0.0,
        },
    )

    _assert_validation_envelope(response, message_fragment="less than 90")


def test_local_space_direct_route_rejects_non_finite_lst(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/local-space/positions",
        json={
            "positions": {"Sun": {"right_ascension": 0.0, "declination": 0.0}},
            "latitude": 0.0,
            "lst_deg": "NaN",
        },
    )

    _assert_validation_envelope(response, message_fragment="lst_deg")


def test_local_space_chart_route_rejects_naive_datetime(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/local-space/chart/positions",
        json={
            "dt": "2000-01-01T12:00:00",
            "bodies": ["Sun"],
            "observer_lat": 40.0,
            "observer_lon": -74.0,
        },
    )

    _assert_validation_envelope(response, message_fragment="timezone-aware")


def test_local_space_chart_route_rejects_unsupported_body(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/local-space/chart/positions",
        json={
            "dt": _DT_ISO,
            "bodies": ["NotAPlanet"],
            "observer_lat": 40.0,
            "observer_lon": -74.0,
        },
    )

    _assert_validation_envelope(response, message_fragment="unsupported chart bodies")


def test_local_space_chart_route_rejects_missing_observer_longitude(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/local-space/chart/positions",
        json={"dt": _DT_ISO, "bodies": ["Sun"], "observer_lat": 40.0},
    )

    _assert_validation_envelope(response, message_fragment="Field required")


def test_local_space_chart_route_rejects_too_many_bodies(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.post(
        "/v1/local-space/chart/positions",
        json={
            "dt": _DT_ISO,
            "bodies": [f"Body{i}" for i in range(13)],
            "observer_lat": 40.0,
            "observer_lon": -74.0,
        },
    )

    _assert_validation_envelope(response, message_fragment="at most 12")
