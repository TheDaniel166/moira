"""P9-06 Triplicity route tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira.constants import SIGNS
from moira.triplicity import (
    ParticipatingRulerPolicy,
    TriplicityDoctrine,
    triplicity_assignment_for,
    triplicity_score,
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


def test_triplicity_table_route_returns_deterministic_sign_order() -> None:
    with _client() as client:
        response = client.get("/v1/triplicity/table")

    assert response.status_code == 200
    body = response.json()
    assert body["doctrine"] == TriplicityDoctrine.DOROTHEAN_PINGREE_1976.value
    assert body["is_day_chart"] is True
    assert [item["sign"] for item in body["assignments"]] == list(SIGNS)
    assert len(body["assignments"]) == 12


def test_triplicity_assignment_route_matches_engine_day_context() -> None:
    direct = triplicity_assignment_for("Cancer", is_day_chart=True)

    with _client() as client:
        response = client.post(
            "/v1/triplicity/assignment",
            json={"sign": "Cancer", "is_day_chart": True},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["sign"] == direct.sign
    assert body["day_ruler"] == direct.day_ruler == "Mars"
    assert body["night_ruler"] == direct.night_ruler == "Venus"
    assert body["participating_ruler"] == direct.participating_ruler == "Moon"
    assert body["active_ruler"] == direct.active_ruler == "Mars"
    assert body["inactive_ruler"] == direct.inactive_ruler == "Venus"
    assert body["element"] == direct.element.value == "water"


def test_triplicity_assignment_route_matches_engine_night_context() -> None:
    direct = triplicity_assignment_for("Aries", is_day_chart=False)

    with _client() as client:
        response = client.post(
            "/v1/triplicity/assignment",
            json={"sign": "Aries", "is_day_chart": False},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["active_ruler"] == direct.active_ruler == "Jupiter"
    assert body["inactive_ruler"] == direct.inactive_ruler == "Sun"
    assert body["signs"] == list(direct.signs)


def test_triplicity_score_route_matches_participating_award_policy() -> None:
    expected = triplicity_score(
        "Saturn",
        "Aries",
        is_day_chart=True,
        participating_policy=ParticipatingRulerPolicy.AWARD_REDUCED,
    )

    with _client() as client:
        response = client.post(
            "/v1/triplicity/score",
            json={
                "planet": "Saturn",
                "sign": "Aries",
                "is_day_chart": True,
                "participating_policy": "award_reduced",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["score"] == expected == 1
    assert body["assignment"]["participating_ruler"] == "Saturn"
    assert body["participating_policy"] == "award_reduced"


def test_triplicity_score_route_matches_participating_ignore_policy() -> None:
    with _client() as client:
        response = client.post(
            "/v1/triplicity/score",
            json={
                "planet": "Saturn",
                "sign": "Aries",
                "is_day_chart": True,
                "participating_policy": "ignore",
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["score"] == 0
    assert body["participating_policy"] == "ignore"


def test_triplicity_score_route_preserves_unknown_sign_zero_behavior() -> None:
    with _client() as client:
        response = client.post(
            "/v1/triplicity/score",
            json={
                "planet": "Sun",
                "sign": "Ophiuchus",
                "is_day_chart": True,
            },
        )

    assert response.status_code == 200
    body = response.json()
    assert body["score"] == 0
    assert body["assignment"] is None


def test_triplicity_assignment_route_rejects_unknown_sign() -> None:
    with _client() as client:
        response = client.post(
            "/v1/triplicity/assignment",
            json={"sign": "Ophiuchus", "is_day_chart": True},
        )

    _assert_validation_envelope(response, message_fragment="no triplicity entry")


def test_triplicity_assignment_route_rejects_non_boolean_sect() -> None:
    with _client() as client:
        response = client.post(
            "/v1/triplicity/assignment",
            json={"sign": "Aries", "is_day_chart": "true"},
        )

    _assert_validation_envelope(response)


def test_triplicity_score_route_rejects_invalid_policy() -> None:
    with _client() as client:
        response = client.post(
            "/v1/triplicity/score",
            json={
                "planet": "Saturn",
                "sign": "Aries",
                "is_day_chart": True,
                "participating_policy": "full",
            },
        )

    _assert_validation_envelope(response)


def test_triplicity_table_route_rejects_invalid_doctrine() -> None:
    with _client() as client:
        response = client.get(
            "/v1/triplicity/table",
            params={"doctrine": "not_a_doctrine"},
        )

    _assert_validation_envelope(response)


def test_triplicity_routes_are_registered() -> None:
    app = create_app(ServerConfig(docs_enabled=False))
    paths = {route.path for route in app.routes}

    assert "/v1/triplicity/table" in paths
    assert "/v1/triplicity/assignment" in paths
    assert "/v1/triplicity/score" in paths
