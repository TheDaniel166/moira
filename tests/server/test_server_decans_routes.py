"""P9-12 decans/decanates route tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import moira_server.routers.decans as decans_router
from moira.decanates import chaldean_face, triplicity_decan, vedic_drekkana
from moira.hermetic_decans import (
    DECAN_RULING_STARS,
    DecanHour,
    DecanHoursNight,
    decan_at,
    decan_for_longitude,
    decan_index,
    list_decans,
)
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


def test_hermetic_decan_catalog_route_returns_ordered_catalog() -> None:
    with _client() as client:
        response = client.get("/v1/hermetic-decans/catalog")

    assert response.status_code == 200
    decans = response.json()["decans"]
    assert len(decans) == 36
    assert decans[0] == {
        "index": 0,
        "name": list_decans()[0],
        "ruling_star": DECAN_RULING_STARS[list_decans()[0]],
    }
    assert decans[-1]["index"] == 35


def test_hermetic_decan_longitude_route_matches_engine_truth() -> None:
    longitude = 60.0
    name = decan_for_longitude(longitude)

    with _client() as client:
        response = client.post("/v1/hermetic-decans/longitude", json={"longitude": longitude})

    assert response.status_code == 200
    body = response.json()
    assert body["longitude"] == longitude
    assert body["normalized_longitude"] == longitude
    assert body["index"] == decan_index(name)
    assert body["name"] == name
    assert body["ruling_star"] == DECAN_RULING_STARS[name]


def test_hermetic_rising_decan_route_matches_engine_truth() -> None:
    payload = {"jd": 2451545.0, "latitude": 51.5, "longitude": -0.1}
    name = decan_at(payload["jd"], payload["latitude"], payload["longitude"])

    with _client() as client:
        response = client.post("/v1/hermetic-decans/rising", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["jd"] == payload["jd"]
    assert body["latitude"] == payload["latitude"]
    assert body["observer_longitude"] == payload["longitude"]
    assert body["index"] == decan_index(name)
    assert body["name"] == name
    assert body["ruling_star"] == DECAN_RULING_STARS[name]


def test_hermetic_night_hours_route_serializes_night_vessel(monkeypatch: pytest.MonkeyPatch) -> None:
    decan_names = list_decans()
    hours = tuple(
        DecanHour(
            hour_number=index + 1,
            decan=decan_names[index],
            ruling_star=DECAN_RULING_STARS[decan_names[index]],
            jd_start=2451545.75 + index / 12.0,
            jd_end=2451545.75 + (index + 1) / 12.0,
        )
        for index in range(12)
    )
    night = DecanHoursNight(
        date_jd=2451545.5,
        latitude=51.5,
        longitude=-0.1,
        sunset_jd=hours[0].jd_start,
        next_sunrise_jd=hours[-1].jd_end,
        hours=hours,
    )
    monkeypatch.setattr(
        decans_router,
        "compute_hermetic_decan_night_hours",
        lambda request: night,
    )

    with _client() as client:
        response = client.post(
            "/v1/hermetic-decans/night-hours",
            json={"jd": 2451545.5, "latitude": 51.5, "longitude": -0.1},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["date_jd"] == night.date_jd
    assert body["sunset_jd"] == night.sunset_jd
    assert body["next_sunrise_jd"] == night.next_sunrise_jd
    assert len(body["hours"]) == 12
    assert body["hours"][0]["hour_number"] == 1
    assert body["hours"][0]["decan"] == decan_names[0]
    assert body["hours"][-1]["jd_end"] == night.next_sunrise_jd


@pytest.mark.parametrize(
    ("path", "payload", "fragment"),
    [
        ("/v1/decanates/chaldean-face", {"longitude": "NaN"}, "longitude"),
        ("/v1/decanates/vedic-drekkana", {"longitude": 10.0, "jd": "NaN"}, "jd"),
        ("/v1/decanates/vedic-drekkana", {"longitude": 10.0, "jd": 2451545.0, "ayanamsa_system": ""}, "ayanamsa_system"),
        ("/v1/hermetic-decans/longitude", {"longitude": "Infinity"}, "longitude"),
        ("/v1/hermetic-decans/rising", {"jd": 2451545.0, "latitude": 90.0, "longitude": 0.0}, "less than 90"),
        ("/v1/hermetic-decans/night-hours", {"jd": "NaN", "latitude": 0.0, "longitude": 0.0}, "jd"),
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
    app = create_app(ServerConfig(docs_enabled=False))
    paths = {route.path for route in app.routes}

    assert "/v1/decanates/chaldean-face" in paths
    assert "/v1/decanates/triplicity" in paths
    assert "/v1/decanates/vedic-drekkana" in paths
    assert "/v1/decanates/set" in paths
    assert "/v1/hermetic-decans/catalog" in paths
    assert "/v1/hermetic-decans/longitude" in paths
    assert "/v1/hermetic-decans/rising" in paths
    assert "/v1/hermetic-decans/night-hours" in paths
