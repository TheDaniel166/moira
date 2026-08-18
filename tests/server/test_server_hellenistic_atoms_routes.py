"""REST admission tests for twelfth-parts and assemble-condition."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira.hellenistic_relations import assemble_hellenistic_condition
from moira.twelfth_parts import twelfth_part_of
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback


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


def test_twelfth_parts_route_preserves_engine_projection(client: TestClient) -> None:
    positions = {"Moon": 287.0}
    direct = twelfth_part_of(287.0)

    response = client.post(
        "/v1/hellenistic/twelfth-parts",
        json={"positions": positions},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == 1
    part = body["parts"][0]
    assert part["body"] == "Moon"
    assert part["twelfth_part_sign"] == direct.twelfth_part_sign
    assert part["projected_longitude"] == pytest.approx(direct.projected_longitude)
    assert part["slice_index"] == direct.slice_index
    assert body["provenance"]["engine_entrypoint"] == "twelfth_part_of"
    assert body["provenance"]["ephemeris"] == "not_used"
    assert "score" not in body


def test_condition_route_preserves_named_receipts_and_stays_score_free(
    client: TestClient,
) -> None:
    positions = {
        "Sun": 10.0,
        "Moon": 12.0,
        "Mercury": 80.0,
        "Venus": 125.0,
        "Mars": 170.0,
        "Jupiter": 190.0,
        "Saturn": 300.0,
    }
    speeds = {
        "Sun": 2.0,
        "Moon": 1.0,
        "Mercury": 1.2,
        "Venus": 1.0,
        "Mars": 0.5,
        "Jupiter": -0.1,
        "Saturn": 0.05,
    }
    direct = assemble_hellenistic_condition("Sun", positions, speeds)

    response = client.post(
        "/v1/hellenistic/condition",
        json={
            "subject": "Sun",
            "positions": positions,
            "speeds": speeds,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["subject"] == "Sun"
    assert body["testimony"]["status"] == direct.testimony.status.value
    assert {item["body"] for item in body["testimony"]["witnesses"]} == {
        item.body for item in direct.testimony.witnesses
    }
    assert body["overcoming"]["overcame_by"] == list(direct.overcoming.overcame_by)
    assert body["adherence"]["adhered"] is True
    assert body["adherence"]["partner"] == "Moon"
    assert body["ray"]["reason"] == "doctrine_not_admitted"
    assert body["enclosure"]["status"] == direct.enclosure.status.value
    assert "score" not in body
    assert body["provenance"]["doctrine"] == "score_free_assemble_condition"


def test_hellenistic_atom_routes_reject_ambiguous_or_extra_inputs(
    client: TestClient,
) -> None:
    empty = client.post("/v1/hellenistic/twelfth-parts", json={"positions": {}})
    extra = client.post(
        "/v1/hellenistic/condition",
        json={
            "subject": "Sun",
            "positions": {"Sun": 10.0, "Moon": 45.0},
            "score": 12,
        },
    )
    non_finite = client.post(
        "/v1/hellenistic/twelfth-parts",
        json={"positions": {"Sun": "NaN"}},
    )

    _assert_validation_envelope(empty, message_fragment="at least 1")
    _assert_validation_envelope(extra, message_fragment="Extra inputs are not permitted")
    _assert_validation_envelope(non_finite, message_fragment="finite")


def test_hellenistic_atom_routes_are_registered(client: TestClient) -> None:
    paths = {
        route.path
        for route in client.app.routes
        if route.path.startswith("/v1/hellenistic/")
    }
    assert {
        "/v1/hellenistic/chart-profile",
        "/v1/hellenistic/twelfth-parts",
        "/v1/hellenistic/condition",
    } <= paths
