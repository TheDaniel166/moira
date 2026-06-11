"""P9-11 Varga route tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira.varga import (
    calculate_varga,
    navamsa,
)
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.services.varga import VARGA_FUNCTIONS


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


def test_varga_generic_route_matches_engine_truth() -> None:
    direct = calculate_varga(45.5, 9, "Custom D9")

    with _client() as client:
        response = client.post(
            "/v1/varga/generic",
            json={
                "sidereal_longitude": 45.5,
                "divisor": 9,
                "name": "Custom D9",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["varga_name"] == direct.varga_name
    assert body["varga_number"] == direct.varga_number
    assert body["longitude"] == direct.longitude
    assert body["varga_longitude"] == direct.varga_longitude
    assert body["sign"] == direct.sign
    assert body["sign_symbol"] == direct.sign_symbol
    assert body["sign_degree"] == direct.sign_degree


@pytest.mark.parametrize("selector", sorted(VARGA_FUNCTIONS))
def test_varga_named_route_matches_each_named_wrapper(selector: str) -> None:
    direct = VARGA_FUNCTIONS[selector](123.456)

    with _client() as client:
        response = client.post(
            "/v1/varga/named",
            json={"sidereal_longitude": 123.456, "varga": selector},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["varga_name"] == direct.varga_name
    assert body["varga_number"] == direct.varga_number
    assert body["varga_longitude"] == direct.varga_longitude
    assert body["sign"] == direct.sign
    assert body["sign_degree"] == direct.sign_degree


def test_varga_shodashvarga_route_returns_all_named_selectors() -> None:
    with _client() as client:
        response = client.post(
            "/v1/varga/shodashvarga",
            json={"sidereal_longitude": 123.456},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["sidereal_longitude"] == 123.456
    assert set(body["vargas"]) == set(VARGA_FUNCTIONS)
    assert body["vargas"]["navamsa"]["sign"] == navamsa(123.456).sign


def test_varga_named_batch_route_preserves_keys_and_truth() -> None:
    payload = {
        "Sun": 10.0,
        "Moon": 40.0,
        "Lot of Fortune": 125.0,
    }

    with _client() as client:
        response = client.post(
            "/v1/varga/named/batch",
            json={"varga": "navamsa", "longitudes": payload},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["varga"] == "navamsa"
    assert set(body["results"]) == set(payload)
    assert body["results"]["Lot of Fortune"]["sign"] == navamsa(125.0).sign


def test_varga_shodashvarga_batch_route_preserves_nested_truth() -> None:
    payload = {"Sun": 10.0, "Moon": 40.0}

    with _client() as client:
        response = client.post(
            "/v1/varga/shodashvarga/batch",
            json={"longitudes": payload},
        )

    assert response.status_code == 200
    body = response.json()
    assert set(body["results"]) == set(payload)
    assert set(body["results"]["Sun"]) == set(VARGA_FUNCTIONS)
    assert body["results"]["Moon"]["hora"]["sign"] == VARGA_FUNCTIONS["hora"](40.0).sign


def test_varga_route_rejects_non_finite_longitude() -> None:
    with _client() as client:
        response = client.post(
            "/v1/varga/named",
            json={"sidereal_longitude": "NaN", "varga": "navamsa"},
        )

    _assert_validation_envelope(response, message_fragment="sidereal_longitude")


def test_varga_generic_route_rejects_invalid_divisor() -> None:
    with _client() as client:
        response = client.post(
            "/v1/varga/generic",
            json={"sidereal_longitude": 10.0, "divisor": 0},
        )

    _assert_validation_envelope(response, message_fragment="greater than or equal to 1")


def test_varga_named_route_rejects_unknown_selector() -> None:
    with _client() as client:
        response = client.post(
            "/v1/varga/named",
            json={"sidereal_longitude": 10.0, "varga": "not_a_varga"},
        )

    _assert_validation_envelope(response, message_fragment="Input should be")


def test_varga_batch_route_rejects_empty_map() -> None:
    with _client() as client:
        response = client.post(
            "/v1/varga/named/batch",
            json={"varga": "navamsa", "longitudes": {}},
        )

    _assert_validation_envelope(response)


def test_varga_batch_route_rejects_empty_key() -> None:
    with _client() as client:
        response = client.post(
            "/v1/varga/named/batch",
            json={"varga": "navamsa", "longitudes": {"": 10.0}},
        )

    _assert_validation_envelope(response, message_fragment="keys must be non-empty")


def test_varga_routes_are_registered() -> None:
    app = create_app(ServerConfig(docs_enabled=False))
    paths = {route.path for route in app.routes}

    assert "/v1/varga/generic" in paths
    assert "/v1/varga/named" in paths
    assert "/v1/varga/shodashvarga" in paths
    assert "/v1/varga/named/batch" in paths
    assert "/v1/varga/shodashvarga/batch" in paths
