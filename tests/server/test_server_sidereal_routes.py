from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from moira.constants import J2000
from moira.sidereal import (
    Ayanamsa,
    NAKSHATRA_SPAN,
    all_nakshatras_at,
    ayanamsa,
    list_ayanamsa_systems,
    nakshatra_of,
    sidereal_to_tropical,
    tropical_to_sidereal,
)
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.sidereal import SIDEREAL_NAKSHATRA_MAX_BULK_POSITIONS


pytestmark = pytest.mark.loopback


class _FakeEngine:
    pass


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: _FakeEngine())
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as test_client:
        yield test_client


def _assert_validation_envelope(response, *, message_fragment: str | None = None) -> None:
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert body["request_id"]
    assert response.headers["X-Request-ID"] == body["request_id"]
    if message_fragment is not None:
        assert message_fragment in body["message"]


def test_ayanamsa_systems_route_matches_engine_registry(client: TestClient) -> None:
    response = client.get("/v1/sidereal/ayanamsa-systems")

    assert response.status_code == 200
    body = response.json()
    reference = list_ayanamsa_systems()
    assert body["total"] == len(Ayanamsa.ALL)
    assert [entry["system"] for entry in body["systems"]] == list(Ayanamsa.ALL)
    assert body["systems"][0]["reference_value_j2000_deg"] == pytest.approx(
        reference[Ayanamsa.LAHIRI]
    )
    assert body["systems"][0]["supported_modes"] == ["true", "mean"]
    assert body["provenance"]["registry_owner"] == "moira.sidereal.Ayanamsa"
    assert body["provenance"]["user_defined_ayanamsa"] == "not_admitted"


def test_ayanamsa_value_route_matches_engine(client: TestClient) -> None:
    payload = {
        "jd_ut": J2000,
        "ayanamsa_system": Ayanamsa.LAHIRI,
        "mode": "mean",
    }

    response = client.post("/v1/sidereal/ayanamsa", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["jd_ut"] == J2000
    assert body["ayanamsa_system"] == Ayanamsa.LAHIRI
    assert body["mode"] == "mean"
    assert body["ayanamsa_deg"] == pytest.approx(ayanamsa(J2000, Ayanamsa.LAHIRI, "mean"))
    assert body["value_range"] == [0.0, "360_exclusive"]
    assert body["provenance"]["engine_entrypoint"] == "ayanamsa"
    assert body["provenance"]["star_anchor_policy"] == "engine_owned_for_true_star_anchored_systems"


@pytest.mark.parametrize(
    ("direction", "input_longitude"),
    [
        ("tropical_to_sidereal", 123.456),
        ("sidereal_to_tropical", 99.123),
    ],
)
def test_sidereal_conversion_route_matches_engine(
    client: TestClient,
    direction: str,
    input_longitude: float,
) -> None:
    payload = {
        "longitude_deg": input_longitude,
        "jd_ut": J2000,
        "direction": direction,
        "ayanamsa_system": Ayanamsa.LAHIRI,
        "mode": "true",
    }

    response = client.post("/v1/sidereal/convert", json=payload)

    assert response.status_code == 200
    body = response.json()
    if direction == "tropical_to_sidereal":
        expected = tropical_to_sidereal(input_longitude, J2000, Ayanamsa.LAHIRI, "true")
        expected_entrypoint = "tropical_to_sidereal"
    else:
        expected = sidereal_to_tropical(input_longitude, J2000, Ayanamsa.LAHIRI, "true")
        expected_entrypoint = "sidereal_to_tropical"
    assert body["output_longitude_deg"] == pytest.approx(expected)
    assert body["ayanamsa_deg"] == pytest.approx(ayanamsa(J2000, Ayanamsa.LAHIRI, "true"))
    assert body["longitude_range"] == [0.0, "360_exclusive"]
    assert body["provenance"]["engine_entrypoint"] == expected_entrypoint
    assert body["provenance"]["conversion_direction"] == direction


def test_sidereal_conversion_round_trip(client: TestClient) -> None:
    tropical = 280.25
    first = client.post(
        "/v1/sidereal/convert",
        json={
            "longitude_deg": tropical,
            "jd_ut": J2000,
            "direction": "tropical_to_sidereal",
            "ayanamsa_system": Ayanamsa.LAHIRI,
            "mode": "mean",
        },
    )
    assert first.status_code == 200

    second = client.post(
        "/v1/sidereal/convert",
        json={
            "longitude_deg": first.json()["output_longitude_deg"],
            "jd_ut": J2000,
            "direction": "sidereal_to_tropical",
            "ayanamsa_system": Ayanamsa.LAHIRI,
            "mode": "mean",
        },
    )

    assert second.status_code == 200
    assert second.json()["output_longitude_deg"] == pytest.approx(tropical)


def test_nakshatra_position_route_matches_engine(client: TestClient) -> None:
    tropical_longitude = 37.5
    expected = nakshatra_of(tropical_longitude, J2000, Ayanamsa.LAHIRI)

    response = client.post(
        "/v1/nakshatra/position",
        json={
            "tropical_longitude_deg": tropical_longitude,
            "jd_ut": J2000,
            "ayanamsa_system": Ayanamsa.LAHIRI,
        },
    )

    assert response.status_code == 200
    body = response.json()
    position = body["position"]
    assert position["nakshatra"] == expected.nakshatra
    assert position["nakshatra_index"] == expected.nakshatra_index
    assert position["nakshatra_number"] == expected.nakshatra_index + 1
    assert position["nakshatra_lord"] == expected.nakshatra_lord
    assert position["pada"] == expected.pada
    assert position["degrees_in"] == pytest.approx(expected.degrees_in)
    assert position["degrees_remaining"] == pytest.approx(NAKSHATRA_SPAN - expected.degrees_in)
    assert position["sidereal_longitude_deg"] == pytest.approx(expected.sidereal_lon)
    assert body["provenance"]["taxonomy"] == "twenty_seven_equal_nakshatras"
    assert body["provenance"]["panchanga_judgement"] == "not_returned"


def test_nakshatra_bulk_route_matches_engine(client: TestClient) -> None:
    positions = {"Moon": 37.5, "Mars": 91.25}
    expected = all_nakshatras_at(positions, J2000, Ayanamsa.LAHIRI)

    response = client.post(
        "/v1/nakshatra/bulk",
        json={
            "positions": positions,
            "jd_ut": J2000,
            "ayanamsa_system": Ayanamsa.LAHIRI,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    by_name = {entry["name"]: entry for entry in body["positions"]}
    assert by_name["Moon"]["nakshatra"] == expected["Moon"].nakshatra
    assert by_name["Moon"]["degrees_in"] == pytest.approx(expected["Moon"].degrees_in)
    assert by_name["Mars"]["nakshatra_lord"] == expected["Mars"].nakshatra_lord
    assert body["provenance"]["engine_entrypoint"] == "all_nakshatras_at"


def test_nakshatra_route_preserves_boundary_assignment(client: TestClient) -> None:
    before_boundary = sidereal_to_tropical(
        NAKSHATRA_SPAN - 1e-9,
        J2000,
        Ayanamsa.LAHIRI,
    )
    at_boundary = sidereal_to_tropical(
        NAKSHATRA_SPAN,
        J2000,
        Ayanamsa.LAHIRI,
    )

    before = client.post(
        "/v1/nakshatra/position",
        json={
            "tropical_longitude_deg": before_boundary,
            "jd_ut": J2000,
            "ayanamsa_system": Ayanamsa.LAHIRI,
        },
    )
    at = client.post(
        "/v1/nakshatra/position",
        json={
            "tropical_longitude_deg": at_boundary,
            "jd_ut": J2000,
            "ayanamsa_system": Ayanamsa.LAHIRI,
        },
    )

    assert before.status_code == 200
    assert at.status_code == 200
    assert before.json()["position"]["nakshatra_index"] == 0
    assert at.json()["position"]["nakshatra_index"] == 1


@pytest.mark.parametrize(
    ("route", "payload", "message_fragment"),
    [
        (
            "/v1/sidereal/ayanamsa",
            {"jd_ut": J2000, "ayanamsa_system": "NotARealAyanamsa"},
            "ayanamsa_system",
        ),
        (
            "/v1/sidereal/ayanamsa",
            {"jd_ut": J2000, "mode": "apparent"},
            "mode",
        ),
        (
            "/v1/sidereal/ayanamsa",
            {"jd_ut": "NaN"},
            "jd_ut must be finite",
        ),
        (
            "/v1/sidereal/convert",
            {"longitude_deg": 1.0, "jd_ut": J2000, "direction": "unknown"},
            "direction",
        ),
        (
            "/v1/sidereal/convert",
            {
                "longitude_deg": "NaN",
                "jd_ut": J2000,
                "direction": "tropical_to_sidereal",
            },
            "longitude_deg must be finite",
        ),
        (
            "/v1/nakshatra/position",
            {"tropical_longitude_deg": 1.0, "jd_ut": "NaN"},
            "jd_ut must be finite",
        ),
        (
            "/v1/nakshatra/bulk",
            {"positions": {}, "jd_ut": J2000},
            "positions",
        ),
        (
            "/v1/nakshatra/bulk",
            {"positions": {" ": 10.0}, "jd_ut": J2000},
            "position names must be non-empty",
        ),
    ],
)
def test_sidereal_routes_reject_invalid_inputs(
    client: TestClient,
    route: str,
    payload: dict[str, object],
    message_fragment: str,
) -> None:
    response = client.post(route, json=payload)

    _assert_validation_envelope(response, message_fragment=message_fragment)


def test_nakshatra_bulk_route_rejects_oversized_map(client: TestClient) -> None:
    response = client.post(
        "/v1/nakshatra/bulk",
        json={
            "positions": {
                f"Body {index}": float(index)
                for index in range(SIDEREAL_NAKSHATRA_MAX_BULK_POSITIONS + 1)
            },
            "jd_ut": J2000,
        },
    )

    _assert_validation_envelope(response, message_fragment="positions")


def test_sidereal_routes_reject_extra_fields(client: TestClient) -> None:
    response = client.post(
        "/v1/sidereal/ayanamsa",
        json={"jd_ut": J2000, "frame": "sidereal"},
    )

    _assert_validation_envelope(response)


def test_sidereal_route_methods_are_bounded(client: TestClient) -> None:
    assert client.post("/v1/sidereal/ayanamsa-systems").status_code == 405
    assert client.get("/v1/sidereal/ayanamsa").status_code == 405
    assert client.get("/v1/sidereal/convert").status_code == 405
    assert client.get("/v1/nakshatra/position").status_code == 405
    assert client.get("/v1/nakshatra/bulk").status_code == 405
