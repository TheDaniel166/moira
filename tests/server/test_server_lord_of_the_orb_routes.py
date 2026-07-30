"""P12-10 caller-seeded Lord of the Orb route admission tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira.lord_of_the_orb import LordOfOrbCycleKind, lord_of_orb
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


def test_sequence_route_preserves_continuous_loop_cycle(client: TestClient) -> None:
    response = client.post(
        "/v1/lord-of-the-orb/sequence",
        json={"birth_planet": "Venus", "years": 84},
    )

    assert response.status_code == 200
    body = response.json()
    expected = lord_of_orb("Venus", 84)
    assert body["sequence"] == {
        "birth_planet": "Venus",
        "cycle_kind": "continuous_loop",
        "span": 84,
        "planets_in_sequence": expected.sequence.planets_in_sequence,
        "is_full_84_year_cycle": True,
    }
    assert len(body["periods"]) == 84
    assert len(body["condition_profiles"]) == 84
    assert [body["periods"][year - 1]["planet"] for year in (1, 8, 15, 22, 29, 36)] == [
        "Venus",
        "Venus",
        "Venus",
        "Venus",
        "Venus",
        "Venus",
    ]
    assert body["periods"][0]["house"] == 1
    assert body["periods"][83]["house"] == 12
    assert body["aggregate"]["planet_year_counts"] == expected.planet_year_counts
    assert body["aggregate"]["cycle_coincidence_years"] == [1]
    assert body["validation"] == {"included": True, "passed": True, "failures": []}
    provenance = body["provenance"]
    assert provenance["source_module"] == "moira.lord_of_the_orb"
    assert provenance["engine_entrypoint"] == "lord_of_orb"
    assert provenance["birth_planet_source"] == "caller_supplied_birth_planetary_hour_ruler"
    assert provenance["planetary_hour_derivation_owner"] == "not_this_route"
    assert provenance["distinct_from"] == "moira.lord_of_the_turn"


def test_sequence_route_preserves_single_cycle_variant(client: TestClient) -> None:
    response = client.post(
        "/v1/lord-of-the-orb/sequence",
        json={
            "birth_planet": "Venus",
            "years": 24,
            "cycle_kind": "single_cycle",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["policy"]["cycle_kind"] == "single_cycle"
    assert body["periods"][0]["planet"] == body["periods"][12]["planet"] == "Venus"
    assert body["periods"][1]["planet"] == body["periods"][13]["planet"] == "Mercury"
    assert body["periods"][0]["house"] == body["periods"][12]["house"] == 1
    assert body["validation"]["passed"] is True
    assert body["provenance"]["cycle_kind"] == "single_cycle"


def test_sequence_route_can_omit_validation_block(client: TestClient) -> None:
    response = client.post(
        "/v1/lord-of-the-orb/sequence",
        json={
            "birth_planet": "Sun",
            "years": 12,
            "include_validation": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["validation"] == {
        "included": False,
        "passed": None,
        "failures": None,
    }
    assert "engine_validation" not in body["provenance"]["stage_sequence"]


@pytest.mark.parametrize(
    ("age", "expected_year"),
    [(0, 1), (7, 8)],
)
def test_current_route_maps_age_to_year_of_life(
    client: TestClient,
    age: int,
    expected_year: int,
) -> None:
    response = client.post(
        "/v1/lord-of-the-orb/current",
        json={"birth_planet": "Venus", "age": age},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["age"] == age
    assert body["year_of_life"] == expected_year
    assert body["period"]["year"] == expected_year
    assert body["period"]["planet"] == "Venus"
    assert body["condition_profile"]["period"] == body["period"]
    assert body["condition_profile"]["hierarchy_rank"] == 6
    assert body["validation"]["passed"] is True
    assert body["provenance"]["engine_entrypoint"] == "current_lord_of_orb"
    assert "current_period_lookup" in body["provenance"]["stage_sequence"]


def test_lord_of_the_orb_routes_reject_invalid_inputs(client: TestClient) -> None:
    invalid_planet = client.post(
        "/v1/lord-of-the-orb/sequence",
        json={"birth_planet": "Pluto", "years": 12},
    )
    empty_planet = client.post(
        "/v1/lord-of-the-orb/sequence",
        json={"birth_planet": " ", "years": 12},
    )
    zero_years = client.post(
        "/v1/lord-of-the-orb/sequence",
        json={"birth_planet": "Sun", "years": 0},
    )
    excessive_years = client.post(
        "/v1/lord-of-the-orb/sequence",
        json={"birth_planet": "Sun", "years": 253},
    )
    non_integer_years = client.post(
        "/v1/lord-of-the-orb/sequence",
        json={"birth_planet": "Sun", "years": 12.5},
    )
    bad_cycle = client.post(
        "/v1/lord-of-the-orb/sequence",
        json={"birth_planet": "Sun", "years": 12, "cycle_kind": "hybrid"},
    )
    negative_age = client.post(
        "/v1/lord-of-the-orb/current",
        json={"birth_planet": "Sun", "age": -1},
    )
    excessive_age = client.post(
        "/v1/lord-of-the-orb/current",
        json={"birth_planet": "Sun", "age": 252},
    )
    non_integer_age = client.post(
        "/v1/lord-of-the-orb/current",
        json={"birth_planet": "Sun", "age": 7.2},
    )
    bad_include_validation = client.post(
        "/v1/lord-of-the-orb/current",
        json={"birth_planet": "Sun", "age": 7, "include_validation": "yes"},
    )

    _assert_validation_envelope(invalid_planet, message_fragment="birth_planet must be one of")
    _assert_validation_envelope(empty_planet, message_fragment="birth_planet must be non-empty")
    _assert_validation_envelope(zero_years, message_fragment="greater than or equal to 1")
    _assert_validation_envelope(excessive_years, message_fragment="less than or equal to 252")
    _assert_validation_envelope(non_integer_years, message_fragment="years must be an integer")
    _assert_validation_envelope(bad_cycle, message_fragment="Input should be")
    _assert_validation_envelope(negative_age, message_fragment="greater than or equal to 0")
    _assert_validation_envelope(excessive_age, message_fragment="less than or equal to 251")
    _assert_validation_envelope(non_integer_age, message_fragment="age must be an integer")
    _assert_validation_envelope(
        bad_include_validation,
        message_fragment="include_validation must be a boolean",
    )


def test_lord_of_the_orb_routes_are_registered(client: TestClient) -> None:
    paths = {
        route.path
        for route in client.app.routes
        if route.path.startswith("/v1/lord-of-the-orb/")
    }

    assert paths == {
        "/v1/lord-of-the-orb/sequence",
        "/v1/lord-of-the-orb/current",
    }
