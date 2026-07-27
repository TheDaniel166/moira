"""P9-12 decans/decanates route tests."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from moira.decanates import chaldean_face, triplicity_decan, vedic_drekkana
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


def _client() -> TestClient:
    return TestClient(create_app(ServerConfig(docs_enabled=False)))


def _assert_validation_envelope(response, *, message_fragment: str | None = None) -> None:
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert body["request_id"]
    assert response.headers["X-Request-ID"] == body["request_id"]
    if message_fragment is not None:
        assert message_fragment in body["message"]


def _assert_decanate_position(body: dict, expected) -> None:
    assert body["system"] == expected.system
    assert body["decan_number"] == expected.decan_number
    assert body["ruling_planet"] == expected.ruling_planet
    assert body["ruling_sign"] == expected.ruling_sign
    assert body["sign"] == expected.sign
    assert body["sign_symbol"] == expected.sign_symbol
    assert body["degree_in_decan"] == expected.degree_in_decan
    assert body["longitude_used"] == expected.longitude_used


def test_chaldean_face_route_matches_engine_truth() -> None:
    expected = chaldean_face(45.5)

    with _client() as client:
        response = client.post("/v1/decanates/chaldean-face", json={"longitude": 45.5})

    assert response.status_code == 200
    _assert_decanate_position(response.json(), expected)


def test_triplicity_decan_route_matches_engine_truth() -> None:
    expected = triplicity_decan(135.25)

    with _client() as client:
        response = client.post("/v1/decanates/triplicity", json={"longitude": 135.25})

    assert response.status_code == 200
    _assert_decanate_position(response.json(), expected)


def test_vedic_drekkana_route_matches_engine_truth() -> None:
    expected = vedic_drekkana(45.0, 2451545.0, ayanamsa_system="Lahiri")

    with _client() as client:
        response = client.post(
            "/v1/decanates/vedic-drekkana",
            json={"longitude": 45.0, "jd": 2451545.0, "ayanamsa_system": "Lahiri"},
        )

    assert response.status_code == 200
    _assert_decanate_position(response.json(), expected)


def test_decanate_set_route_returns_all_three_doctrine_keys() -> None:
    with _client() as client:
        response = client.post(
            "/v1/decanates/set",
            json={"longitude": 45.0, "jd": 2451545.0},
        )

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"chaldean_face", "triplicity", "vedic_drekkana"}
    _assert_decanate_position(body["chaldean_face"], chaldean_face(45.0))
    _assert_decanate_position(body["triplicity"], triplicity_decan(45.0))
    _assert_decanate_position(body["vedic_drekkana"], vedic_drekkana(45.0, 2451545.0))


@pytest.mark.parametrize(
    ("path", "payload", "fragment"),
    [
        ("/v1/decanates/chaldean-face", {"longitude": "NaN"}, "longitude"),
        ("/v1/decanates/vedic-drekkana", {"longitude": 10.0, "jd": "NaN"}, "jd"),
        ("/v1/decanates/vedic-drekkana", {"longitude": 10.0, "jd": 2451545.0, "ayanamsa_system": ""}, "ayanamsa_system"),
    ],
)
def test_decan_routes_reject_invalid_inputs(
    path: str,
    payload: dict[str, object],
    fragment: str,
) -> None:
    with _client() as client:
        response = client.post(path, json=payload)

    _assert_validation_envelope(response, message_fragment=fragment)


def test_decan_routes_are_registered() -> None:
    import moira_server.routers.decans as decan_routes

    app = create_app(ServerConfig(docs_enabled=False))
    paths = {route.path for route in app.routes}

    assert "/v1/decanates/chaldean-face" in paths
    assert "/v1/decanates/triplicity" in paths
    assert "/v1/decanates/vedic-drekkana" in paths
    assert "/v1/decanates/set" in paths
    assert "/v1/decanates/chart/vedic-drekkana" in paths
    assert "/v1/decanates/chart/set" in paths
    assert not any(path.startswith("/v1/hermetic-decans") for path in paths)
    assert not hasattr(decan_routes, "hermetic_decans_router")


@pytest.mark.parametrize(
    ("method", "path", "payload"),
    [
        ("GET", "/v1/hermetic-decans/catalog", None),
        ("POST", "/v1/hermetic-decans/longitude", {"longitude": 10.0}),
        (
            "POST",
            "/v1/hermetic-decans/rising",
            {"jd": 2451545.0, "latitude": 0.0, "longitude": 0.0},
        ),
        (
            "POST",
            "/v1/hermetic-decans/night-hours",
            {"jd": 2451545.0, "latitude": 0.0, "longitude": 0.0},
        ),
    ],
)
def test_closed_exclusion_hermetic_decan_routes_return_not_found(
    method: str,
    path: str,
    payload: dict[str, object] | None,
) -> None:
    with _client() as client:
        response = client.request(method, path, json=payload)

    assert response.status_code == 404


@pytest.mark.requires_ephemeris
def test_vedic_drekkana_chart_route_matches_direct_route() -> None:
    payload = {
        "dt": datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc).isoformat(),
        "body": "Sun",
        "ayanamsa_system": "Lahiri",
    }

    with _client() as client:
        chart_response = client.post(
            "/v1/decanates/chart/vedic-drekkana",
            json=payload,
        )

    assert chart_response.status_code == 200
    chart_body = chart_response.json()

    with _client() as client:
        direct_response = client.post(
            "/v1/decanates/vedic-drekkana",
            json={
                "longitude": chart_body["tropical_longitude"],
                "jd": chart_body["jd"],
                "ayanamsa_system": "Lahiri",
            },
        )

    assert direct_response.status_code == 200
    assert chart_body["result"] == direct_response.json()
    assert chart_body["body"] == "Sun"
    assert chart_body["provenance"]["requested_bodies"] == ["Sun"]


@pytest.mark.requires_ephemeris
def test_decanate_set_chart_route_matches_direct_route() -> None:
    payload = {
        "dt": datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc).isoformat(),
        "body": "Moon",
        "ayanamsa_system": "Lahiri",
    }

    with _client() as client:
        chart_response = client.post("/v1/decanates/chart/set", json=payload)

    assert chart_response.status_code == 200
    chart_body = chart_response.json()

    with _client() as client:
        direct_response = client.post(
            "/v1/decanates/set",
            json={
                "longitude": chart_body["tropical_longitude"],
                "jd": chart_body["jd"],
                "ayanamsa_system": "Lahiri",
            },
        )

    assert direct_response.status_code == 200
    assert chart_body["result"] == direct_response.json()


def test_decanate_chart_route_rejects_naive_datetime() -> None:
    with _client() as client:
        response = client.post(
            "/v1/decanates/chart/vedic-drekkana",
            json={"dt": "2000-01-01T12:00:00", "body": "Sun"},
        )

    _assert_validation_envelope(response, message_fragment="timezone-aware")


def test_decanate_chart_route_rejects_invalid_body() -> None:
    with _client() as client:
        response = client.post(
            "/v1/decanates/chart/vedic-drekkana",
            json={
                "dt": datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc).isoformat(),
                "body": "NotAPlanet",
            },
        )

    _assert_validation_envelope(response, message_fragment="unsupported chart bodies")
