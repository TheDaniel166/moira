"""REST admission tests for whole-sign aspect direction and overcoming."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira.aspects import find_whole_sign_aspects, overcoming
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


class _FakeEngine:
    pass


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: _FakeEngine())
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as test_client:
        yield test_client


def _assert_validation_envelope(response, *, message_fragment: str) -> None:
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert message_fragment in body["message"]


def test_whole_sign_route_preserves_direction_classification_and_overcoming(
    client: TestClient,
) -> None:
    positions = {"Mars": 5.0, "Saturn": 95.0, "Venus": 245.0}
    direct = find_whole_sign_aspects(positions)

    response = client.post(
        "/v1/aspects/hellenistic/whole-sign",
        json={"positions": positions},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == len(direct)
    assert [item["direction"] for item in body["aspects"]] == [
        item.direction.value if item.direction is not None else None for item in direct
    ]
    assert all(
        item["classification"]["domain"] == "whole_sign"
        for item in body["aspects"]
    )
    for item in body["aspects"]:
        assert item["body1_overcomes_body2"] is overcoming(
            positions[item["body1"]], positions[item["body2"]]
        )
        assert item["body2_overcomes_body1"] is overcoming(
            positions[item["body2"]], positions[item["body1"]]
        )
    assert body["provenance"]["ephemeris"] == "not_used"
    assert body["provenance"]["chart_motion"] == "not_computed"


def test_overcoming_route_is_bidirectional_and_normalizes_longitudes(
    client: TestClient,
) -> None:
    response = client.post(
        "/v1/aspects/hellenistic/overcoming",
        json={
            "body1": "Mars",
            "longitude1": 275.0,
            "body2": "Saturn",
            "longitude2": 5.0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["longitude1"] == pytest.approx(275.0)
    assert body["longitude2"] == pytest.approx(5.0)
    assert body["body1_overcomes_body2"] is True
    assert body["body2_overcomes_body1"] is False
    assert body["overcoming_body"] == "Mars"
    assert body["provenance"]["doctrine"] == "tenth_sign_overcoming"


def test_overcoming_route_returns_no_winner_outside_tenth_sign_relation(
    client: TestClient,
) -> None:
    response = client.post(
        "/v1/aspects/hellenistic/overcoming",
        json={
            "body1": "Sun",
            "longitude1": 10.0,
            "body2": "Moon",
            "longitude2": 130.0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["body1_overcomes_body2"] is False
    assert body["body2_overcomes_body1"] is False
    assert body["overcoming_body"] is None


def test_whole_sign_routes_reject_ambiguous_or_non_finite_inputs(
    client: TestClient,
) -> None:
    too_few = client.post(
        "/v1/aspects/hellenistic/whole-sign",
        json={"positions": {"Sun": 10.0}},
    )
    duplicate = client.post(
        "/v1/aspects/hellenistic/whole-sign",
        json={"positions": {"Sun": 10.0, " Sun ": 20.0}},
    )
    non_finite = client.post(
        "/v1/aspects/hellenistic/overcoming",
        json={
            "body1": "Sun",
            "longitude1": "NaN",
            "body2": "Moon",
            "longitude2": 20.0,
        },
    )

    _assert_validation_envelope(too_few, message_fragment="at least two bodies")
    _assert_validation_envelope(duplicate, message_fragment="unique after trimming")
    _assert_validation_envelope(non_finite, message_fragment="longitudes must be finite")


def test_hellenistic_aspect_routes_are_registered(client: TestClient) -> None:
    paths = {
        route.path
        for route in client.app.routes
        if route.path.startswith("/v1/aspects/hellenistic/")
    }
    assert paths == {
        "/v1/aspects/hellenistic/whole-sign",
        "/v1/aspects/hellenistic/overcoming",
    }
