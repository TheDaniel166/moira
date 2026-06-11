"""P9-07 Egyptian Bounds route tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira.constants import SIGNS
from moira.egyptian_bounds import (
    EgyptianBoundsDoctrine,
    classify_egyptian_bound,
    egyptian_bound_of,
    evaluate_egyptian_bound_condition,
    evaluate_egyptian_bound_relations,
    evaluate_egyptian_bounds_aggregate,
    evaluate_egyptian_bounds_network,
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


def _aggregate_payload() -> dict:
    return {
        "entries": [
            {"planet": "Mercury", "longitude": 62.0},
            {"planet": "Venus", "longitude": 211.0},
            {"planet": "Mars", "longitude": 32.0},
            {"planet": "Moon", "longitude": 180.0},
            {"planet": "Saturn", "longitude": 32.0},
        ]
    }


def test_egyptian_bounds_table_route_returns_deterministic_sign_order() -> None:
    with _client() as client:
        response = client.get("/v1/egyptian-bounds/table")

    assert response.status_code == 200
    body = response.json()
    assert body["doctrine"] == EgyptianBoundsDoctrine.EGYPTIAN.value
    assert [item["sign"] for item in body["signs"]] == list(SIGNS)
    assert all(len(item["segments"]) == 5 for item in body["signs"])
    assert body["signs"][0]["segments"][0]["ruler"] == "Jupiter"


def test_egyptian_bound_route_matches_engine_truth() -> None:
    direct = egyptian_bound_of(219.5)

    with _client() as client:
        response = client.post(
            "/v1/egyptian-bounds/bound",
            json={"longitude": 219.5},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["longitude"] == direct.longitude
    assert body["sign"] == direct.sign == "Scorpio"
    assert body["degree_in_sign"] == direct.degree_in_sign == 9.5
    assert body["ruler"] == direct.ruler == "Venus"
    assert body["segment_range"] == [7.0, 11.0]


def test_egyptian_bound_classification_route_matches_engine() -> None:
    direct = classify_egyptian_bound("Venus", 10.0)

    with _client() as client:
        response = client.post(
            "/v1/egyptian-bounds/classification",
            json={"planet": "Venus", "longitude": 10.0},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["planet"] == direct.planet
    assert body["own_bound"] is True
    assert body["host_nature"] == "benefic"
    assert body["hosted_by_benefic"] is True


def test_egyptian_bound_classification_route_preserves_optional_host_sect() -> None:
    with _client() as client:
        response = client.post(
            "/v1/egyptian-bounds/classification",
            json={
                "planet": "Moon",
                "longitude": 180.0,
                "is_day_chart": True,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["truth"]["ruler"] == "Saturn"
    assert body["host_in_sect"] is True


def test_egyptian_bound_relation_route_preserves_detected_admitted_and_scored() -> None:
    direct = evaluate_egyptian_bound_relations("Venus", 10.0)

    with _client() as client:
        response = client.post(
            "/v1/egyptian-bounds/relation",
            json={"planet": "Venus", "longitude": 10.0},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["detected_relation_kind"] == direct.detected_relation_kind.value
    assert body["admitted_relation_kinds"] == ["self_hosted"]
    assert body["scored_relation_kinds"] == ["self_hosted"]
    assert body["has_scored_relation"] is True


def test_egyptian_bound_condition_route_matches_engine_profile() -> None:
    direct = evaluate_egyptian_bound_condition("Venus", 234.0)

    with _client() as client:
        response = client.post(
            "/v1/egyptian-bounds/condition",
            json={"planet": "Venus", "longitude": 234.0},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == direct.state.value == "constrained"
    assert body["weakening_count"] == direct.weakening_count == 1
    assert body["is_constrained"] is True
    assert body["relation_profile"]["detected_relation"]["host_ruler"] == "Saturn"


def test_egyptian_bounds_aggregate_route_matches_engine_order_and_counts() -> None:
    direct = evaluate_egyptian_bounds_aggregate(
        [
            evaluate_egyptian_bound_condition("Mars", 109.25),
            evaluate_egyptian_bound_condition("Venus", 10.0),
            evaluate_egyptian_bound_condition("Moon", 180.0),
            evaluate_egyptian_bound_condition("Sun", 15.0),
        ]
    )

    with _client() as client:
        response = client.post(
            "/v1/egyptian-bounds/aggregate",
            json={
                "entries": [
                    {"planet": "Mars", "longitude": 109.25},
                    {"planet": "Venus", "longitude": 10.0},
                    {"planet": "Moon", "longitude": 180.0},
                    {"planet": "Sun", "longitude": 15.0},
                ]
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert [profile["planet"] for profile in body["profiles"]] == [
        profile.planet for profile in direct.profiles
    ]
    assert body["self_governed_count"] == direct.self_governed_count == 1
    assert body["supported_count"] == direct.supported_count == 1
    assert body["mediated_count"] == direct.mediated_count == 1
    assert body["constrained_count"] == direct.constrained_count == 1
    assert body["strongest_planets"] == list(direct.strongest_planets)


def test_egyptian_bounds_network_route_matches_engine_projection() -> None:
    aggregate = evaluate_egyptian_bounds_aggregate(
        [
            evaluate_egyptian_bound_condition("Mercury", 62.0),
            evaluate_egyptian_bound_condition("Venus", 211.0),
            evaluate_egyptian_bound_condition("Mars", 32.0),
            evaluate_egyptian_bound_condition("Moon", 180.0),
            evaluate_egyptian_bound_condition("Saturn", 32.0),
        ]
    )
    direct = evaluate_egyptian_bounds_network(aggregate)

    with _client() as client:
        response = client.post(
            "/v1/egyptian-bounds/network",
            json=_aggregate_payload(),
        )

    assert response.status_code == 200
    body = response.json()
    assert body["node_count"] == direct.node_count == 5
    assert body["edge_count"] == direct.edge_count == 4
    assert body["mutual_edge_count"] == direct.mutual_edge_count == 2
    assert body["unilateral_edge_count"] == direct.unilateral_edge_count == 2
    assert body["isolated_planets"] == list(direct.isolated_planets)
    assert body["most_connected_planets"] == list(direct.most_connected_planets)


def test_egyptian_bounds_routes_support_live_doctrine_enum_values() -> None:
    with _client() as client:
        response = client.get(
            "/v1/egyptian-bounds/table",
            params={"doctrine": "chaldean"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["doctrine"] == "chaldean"
    assert body["signs"][0]["segments"][0]["ruler"] == "Mars"


def test_egyptian_bounds_route_rejects_invalid_doctrine() -> None:
    with _client() as client:
        response = client.get(
            "/v1/egyptian-bounds/table",
            params={"doctrine": "not_a_doctrine"},
        )

    _assert_validation_envelope(response)


def test_egyptian_bound_route_rejects_malformed_longitude() -> None:
    with _client() as client:
        response = client.post(
            "/v1/egyptian-bounds/bound",
            json={"longitude": "not-a-number"},
        )

    _assert_validation_envelope(response)


def test_egyptian_bound_route_rejects_non_boolean_sect() -> None:
    with _client() as client:
        response = client.post(
            "/v1/egyptian-bounds/classification",
            json={
                "planet": "Moon",
                "longitude": 180.0,
                "is_day_chart": "true",
            },
        )

    _assert_validation_envelope(response)


def test_egyptian_bounds_aggregate_route_rejects_duplicate_planets() -> None:
    with _client() as client:
        response = client.post(
            "/v1/egyptian-bounds/aggregate",
            json={
                "entries": [
                    {"planet": "Venus", "longitude": 10.0},
                    {"planet": "Venus", "longitude": 20.0},
                ]
            },
        )

    _assert_validation_envelope(response, message_fragment="profiles must be unique")


def test_egyptian_bounds_routes_are_registered() -> None:
    app = create_app(ServerConfig(docs_enabled=False))
    paths = {route.path for route in app.routes}

    assert "/v1/egyptian-bounds/table" in paths
    assert "/v1/egyptian-bounds/bound" in paths
    assert "/v1/egyptian-bounds/classification" in paths
    assert "/v1/egyptian-bounds/relation" in paths
    assert "/v1/egyptian-bounds/condition" in paths
    assert "/v1/egyptian-bounds/aggregate" in paths
    assert "/v1/egyptian-bounds/network" in paths
