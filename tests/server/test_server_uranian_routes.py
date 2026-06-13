"""P12-01 Uranian / Hamburg School route admission tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira.uranian import all_uranian_at, list_uranian, uranian_at
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
    assert body["request_id"]
    assert response.headers["X-Request-ID"] == body["request_id"]
    assert message_fragment in body["message"]


def test_uranian_catalog_route_preserves_nine_name_hypothetical_catalog(
    client: TestClient,
) -> None:
    response = client.get("/v1/uranian/catalog")

    assert response.status_code == 200
    body = response.json()
    assert body["names"] == list_uranian()
    assert body["count"] == 9
    assert body["names"][-1] == "Transpluto"
    assert body["model"] == "linear_mean_motion_table"
    assert body["frame"] == "tropical_ecliptic_longitude"
    assert body["epoch"] == "J2000"
    assert body["provenance"] == {
        "source_module": "moira.uranian",
        "engine_entrypoint": "list_uranian",
        "body_kind": "hypothetical_body",
        "school": "Hamburg_Uranian",
        "model": "linear_mean_motion_table",
        "formula_basis": "longitude = longitude_at_J2000 + daily_motion * (jd_ut - J2000)",
        "frame": "tropical_ecliptic_longitude",
        "epoch": "J2000",
        "physical_ephemeris": "none",
        "spk_kernel_used": False,
        "current_name_count": 9,
        "note": (
            "Uranian positions are Hamburg School hypothetical mean points, "
            "not JPL/NAIF physical-body states or discovered TNO positions."
        ),
        "stage_sequence": [
            "catalog_name_table_read",
            "hypothetical_body_provenance_assignment",
            "uranian_catalog_response_serialization",
        ],
    }


@pytest.mark.parametrize("name", list_uranian())
def test_uranian_position_route_matches_engine_for_each_admitted_name(
    client: TestClient,
    name: str,
) -> None:
    jd_ut = 2451545.0
    direct = uranian_at(name, jd_ut)

    response = client.post(
        "/v1/uranian/position",
        json={"name": name, "jd_ut": jd_ut},
    )

    assert response.status_code == 200
    body = response.json()
    position = body["position"]
    assert position["name"] == direct.name
    assert position["longitude"] == pytest.approx(direct.longitude)
    assert position["sign"] == direct.sign
    assert position["sign_symbol"] == direct.sign_symbol
    assert position["sign_degree"] == pytest.approx(direct.sign_degree)
    assert position["speed"] == pytest.approx(direct.speed)
    assert position["body_kind"] == "hypothetical_body"
    provenance = body["provenance"]
    assert provenance["engine_entrypoint"] == "uranian_at"
    assert provenance["body_kind"] == "hypothetical_body"
    assert provenance["physical_ephemeris"] == "none"
    assert provenance["spk_kernel_used"] is False
    assert provenance["stage_sequence"] == [
        "jd_ut_validation",
        "case_sensitive_name_lookup",
        "linear_mean_position_computation",
        "sign_derivation",
        "uranian_position_response_serialization",
    ]


def test_uranian_bulk_route_defaults_to_all_nine_bodies(client: TestClient) -> None:
    jd_ut = 2451545.0
    direct = all_uranian_at(jd_ut)

    response = client.post("/v1/uranian/bulk", json={"jd_ut": jd_ut})

    assert response.status_code == 200
    body = response.json()
    assert body["requested_names"] == list(direct)
    assert list(body["positions"]) == list(direct)
    assert body["count"] == 9
    assert body["positions"]["Transpluto"]["longitude"] == pytest.approx(
        direct["Transpluto"].longitude
    )
    assert body["provenance"]["engine_entrypoint"] == "all_uranian_at"
    assert body["provenance"]["stage_sequence"] == [
        "jd_ut_validation",
        "case_sensitive_name_list_resolution",
        "linear_mean_position_computation",
        "sign_derivation",
        "uranian_bulk_response_serialization",
    ]


def test_uranian_bulk_route_preserves_requested_subset_order(client: TestClient) -> None:
    response = client.post(
        "/v1/uranian/bulk",
        json={"jd_ut": 2451545.0, "names": ["Poseidon", "Cupido"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["requested_names"] == ["Poseidon", "Cupido"]
    assert list(body["positions"]) == ["Poseidon", "Cupido"]
    assert body["count"] == 2
    assert body["provenance"]["engine_entrypoint"] == "uranian_at"


def test_uranian_routes_reject_unknown_or_case_mismatched_names(
    client: TestClient,
) -> None:
    unknown = client.post(
        "/v1/uranian/position",
        json={"name": "NotAPlanet", "jd_ut": 2451545.0},
    )
    case_mismatch = client.post(
        "/v1/uranian/position",
        json={"name": "cupido", "jd_ut": 2451545.0},
    )

    _assert_validation_envelope(unknown, message_fragment="Unknown Uranian body")
    _assert_validation_envelope(case_mismatch, message_fragment="Unknown Uranian body")


def test_uranian_routes_reject_empty_names_and_non_finite_jd(client: TestClient) -> None:
    empty_name = client.post(
        "/v1/uranian/position",
        json={"name": " ", "jd_ut": 2451545.0},
    )
    non_finite = client.post(
        "/v1/uranian/position",
        json={"name": "Cupido", "jd_ut": "NaN"},
    )
    empty_bulk_entry = client.post(
        "/v1/uranian/bulk",
        json={"jd_ut": 2451545.0, "names": ["Cupido", " "]},
    )

    _assert_validation_envelope(empty_name, message_fragment="name must be non-empty")
    _assert_validation_envelope(non_finite, message_fragment="jd_ut must be finite")
    _assert_validation_envelope(
        empty_bulk_entry,
        message_fragment="names entries must be non-empty",
    )


def test_uranian_bulk_route_rejects_duplicate_and_oversized_name_lists(
    client: TestClient,
) -> None:
    duplicate = client.post(
        "/v1/uranian/bulk",
        json={"jd_ut": 2451545.0, "names": ["Cupido", "Cupido"]},
    )
    oversized = client.post(
        "/v1/uranian/bulk",
        json={"jd_ut": 2451545.0, "names": [f"Body{i}" for i in range(10)]},
    )

    _assert_validation_envelope(duplicate, message_fragment="names entries must be unique")
    _assert_validation_envelope(oversized, message_fragment="at most 9 items")
