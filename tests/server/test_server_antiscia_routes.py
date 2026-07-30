"""P12-04 ordinary antiscia route admission tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira.antiscia import antiscion, antiscia_to_point, contra_antiscion, find_antiscia
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
    assert body["request_id"]
    assert response.headers["X-Request-ID"] == body["request_id"]
    assert message_fragment in body["message"]


def test_reflect_route_preserves_direct_antiscion(client: TestClient) -> None:
    response = client.post(
        "/v1/antiscia/reflect",
        json={"longitude": 10.0, "kind": "antiscion"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["longitude"] == pytest.approx(10.0)
    assert body["antiscion"] == pytest.approx(170.0)
    assert "contra_antiscion" not in body
    assert body["normalized_range"] == [0.0, 360.0]
    assert body["provenance"]["engine_entrypoint"] == "antiscion"
    assert body["provenance"]["primary_direction_boundary"] == "not_primary_direction_antiscia"
    assert body["provenance"]["chart_motion"] == "not_computed"
    assert body["provenance"]["ephemeris"] == "not_used"


def test_reflect_route_preserves_direct_contra_antiscion(client: TestClient) -> None:
    response = client.post(
        "/v1/antiscia/reflect",
        json={"longitude": 10.0, "kind": "contra_antiscion"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "antiscion" not in body
    assert body["contra_antiscion"] == pytest.approx(350.0)
    assert body["provenance"]["engine_entrypoint"] == "contra_antiscion"


@pytest.mark.parametrize("longitude", [0.0, 90.0, 180.0, 270.0, 359.999, -10.0, 725.5])
def test_reflect_route_preserves_both_outputs_and_involution(
    client: TestClient,
    longitude: float,
) -> None:
    response = client.post("/v1/antiscia/reflect", json={"longitude": longitude})

    assert response.status_code == 200
    body = response.json()
    assert body["antiscion"] == pytest.approx(antiscion(longitude))
    assert body["contra_antiscion"] == pytest.approx(contra_antiscion(longitude))
    assert antiscion(body["antiscion"]) == pytest.approx(longitude % 360.0)
    assert contra_antiscion(body["contra_antiscion"]) == pytest.approx(longitude % 360.0)
    assert body["provenance"]["engine_entrypoint"] == "antiscion+contra_antiscion"


def test_contacts_route_preserves_engine_contact_vessel_and_ordering(
    client: TestClient,
) -> None:
    positions = {
        "Sun": 10.0,
        "Moon": 170.2,
        "Mercury": 30.0,
        "Venus": 329.9,
        "Mars": 88.0,
    }
    direct = find_antiscia(positions, orb=0.5)

    response = client.post(
        "/v1/antiscia/contacts",
        json={"positions": positions, "orb": 0.5},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == len(direct)
    assert body["orb"] == pytest.approx(0.5)
    assert body["contacts"] == [
        {
            "body1": contact.body1,
            "body2": contact.body2,
            "aspect": contact.aspect,
            "lon1": pytest.approx(contact.lon1),
            "lon2": pytest.approx(contact.lon2),
            "shadow": pytest.approx(contact.shadow),
            "orb": pytest.approx(contact.orb),
        }
        for contact in direct
    ]
    assert [contact["orb"] for contact in body["contacts"]] == sorted(
        contact["orb"] for contact in body["contacts"]
    )
    assert {contact["aspect"] for contact in body["contacts"]} == {
        "Antiscion",
        "Contra-Antiscion",
    }
    assert body["provenance"]["engine_entrypoint"] == "find_antiscia"
    assert body["provenance"]["result_ordering"] == "increasing_orb"


def test_to_point_route_preserves_point_name_and_engine_ordering(
    client: TestClient,
) -> None:
    positions = {"Sun": 10.0, "Moon": 190.1, "Mars": 43.0}
    direct = antiscia_to_point(170.0, positions, point_name="Asc", orb=0.5)

    response = client.post(
        "/v1/antiscia/to-point",
        json={
            "point_longitude": 170.0,
            "point_name": "Asc",
            "positions": positions,
            "orb": 0.5,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["count"] == len(direct)
    assert [contact["body2"] for contact in body["contacts"]] == ["Asc"] * len(direct)
    assert body["contacts"] == [
        {
            "body1": contact.body1,
            "body2": contact.body2,
            "aspect": contact.aspect,
            "lon1": pytest.approx(contact.lon1),
            "lon2": pytest.approx(contact.lon2),
            "shadow": pytest.approx(contact.shadow),
            "orb": pytest.approx(contact.orb),
        }
        for contact in direct
    ]
    assert body["provenance"]["engine_entrypoint"] == "antiscia_to_point"
    assert body["provenance"]["result_ordering"] == "increasing_orb"


def test_antiscia_routes_reject_invalid_reflection_inputs(client: TestClient) -> None:
    non_finite = client.post(
        "/v1/antiscia/reflect",
        json={"longitude": "NaN"},
    )
    invalid_kind = client.post(
        "/v1/antiscia/reflect",
        json={"longitude": 10.0, "kind": "primary_direction"},
    )

    _assert_validation_envelope(non_finite, message_fragment="longitude must be finite")
    _assert_validation_envelope(invalid_kind, message_fragment="Input should be")


def test_antiscia_routes_reject_invalid_position_maps(client: TestClient) -> None:
    empty = client.post(
        "/v1/antiscia/contacts",
        json={"positions": {}},
    )
    empty_name = client.post(
        "/v1/antiscia/contacts",
        json={"positions": {" ": 10.0}},
    )
    duplicate_after_trim = client.post(
        "/v1/antiscia/contacts",
        json={"positions": {"Sun": 10.0, " Sun ": 20.0}},
    )
    non_finite = client.post(
        "/v1/antiscia/contacts",
        json={"positions": {"Sun": "NaN"}},
    )
    oversized = client.post(
        "/v1/antiscia/contacts",
        json={"positions": {f"Body{i}": float(i) for i in range(65)}},
    )

    _assert_validation_envelope(empty, message_fragment="at least one body")
    _assert_validation_envelope(empty_name, message_fragment="body names must be non-empty")
    _assert_validation_envelope(duplicate_after_trim, message_fragment="unique after trimming")
    _assert_validation_envelope(non_finite, message_fragment="position longitudes must be finite")
    _assert_validation_envelope(oversized, message_fragment="at most 64 bodies")


def test_antiscia_routes_reject_invalid_orb_and_point_inputs(client: TestClient) -> None:
    negative_orb = client.post(
        "/v1/antiscia/contacts",
        json={"positions": {"Sun": 10.0}, "orb": -0.1},
    )
    oversized_orb = client.post(
        "/v1/antiscia/contacts",
        json={"positions": {"Sun": 10.0}, "orb": 30.1},
    )
    non_finite_orb = client.post(
        "/v1/antiscia/contacts",
        json={"positions": {"Sun": 10.0}, "orb": "NaN"},
    )
    non_finite_point = client.post(
        "/v1/antiscia/to-point",
        json={"point_longitude": "NaN", "positions": {"Sun": 10.0}},
    )
    empty_point_name = client.post(
        "/v1/antiscia/to-point",
        json={"point_longitude": 170.0, "point_name": " ", "positions": {"Sun": 10.0}},
    )

    _assert_validation_envelope(negative_orb, message_fragment="greater than or equal to 0")
    _assert_validation_envelope(oversized_orb, message_fragment="less than or equal to 30")
    _assert_validation_envelope(non_finite_orb, message_fragment="orb must be finite")
    _assert_validation_envelope(non_finite_point, message_fragment="point_longitude must be finite")
    _assert_validation_envelope(empty_point_name, message_fragment="point_name must be non-empty")


def test_antiscia_routes_are_registered_and_separate_from_primary_directions(
    client: TestClient,
) -> None:
    paths = {
        route.path
        for route in client.app.routes
        if route.path.startswith("/v1/antiscia/")
    }

    assert paths == {
        "/v1/antiscia/reflect",
        "/v1/antiscia/contacts",
        "/v1/antiscia/to-point",
    }

    response = client.post("/v1/antiscia/reflect", json={"longitude": 10.0})
    assert response.status_code == 200
    provenance = response.json()["provenance"]
    assert provenance["doctrine"] == "ordinary_antiscia"
    assert provenance["primary_direction_boundary"] == "not_primary_direction_antiscia"
    assert "primary_direction" not in provenance["stage_sequence"]
