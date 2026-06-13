"""P12-11 caller-supplied Lord of the Turn route admission tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

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


def test_profile_route_preserves_domicile_only_boundary(client: TestClient) -> None:
    response = client.post(
        "/v1/lord-of-the-turn/profile",
        json={
            "natal_asc": 0,
            "age": 0,
            "sr_chart": {
                "sr_asc": 0,
                "planets": {"Sun": 90, "Mars": 5},
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["lord"] == "Mars"
    assert body["profile"]["condition_mode"] == "domicile_only"
    assert body["result"]["selection_reason"] == "domicile_only"
    assert body["profection"]["profected_sign"] == "Aries"
    assert body["candidates"] == [
        {
            "planet": "Mars",
            "role": "domicile",
            "sr_house": None,
            "is_combust": False,
            "is_retrograde": False,
            "is_well_placed": True,
            "blocker_reasons": [],
            "witnesses_target": True,
            "testimony_count": 2,
        }
    ]
    assert body["validation"] == {"included": True, "passed": True, "failures": []}
    provenance = body["provenance"]
    assert provenance["source_module"] == "moira.lord_of_the_turn"
    assert provenance["sr_chart_owner"] == "caller_supplied"
    assert provenance["solar_return_construction_owner"] == "not_this_route"
    assert provenance["house_calculation_owner"] == "not_this_route"
    assert provenance["sect_owner"] == "caller_supplied_sr_is_night"
    assert provenance["domicile_only_mode"] is True


def test_profile_route_preserves_al_qabisi_condition_assessment(client: TestClient) -> None:
    response = client.post(
        "/v1/lord-of-the-turn/profile",
        json={
            "natal_asc": 0,
            "age": 0,
            "sr_chart": {
                "sr_asc": 0,
                "planets": {"Sun": 90, "Moon": 180, "Mars": 5},
                "house_placements": {"Mars": 1, "Sun": 4},
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["profile"]["lord"] == "Mars"
    assert body["profile"]["condition_mode"] == "solar_return_condition_assessment"
    assert body["profile"]["lord_sr_house"] == 1
    assert body["result"]["selection_reason"] == "domicile_well_placed"
    assert body["result"]["winning_candidate"]["is_well_placed"] is True
    assert body["result"]["blocked_candidates"] == []
    assert body["policy"] == {"method": "al_qabisi", "combust_orb": 8.5}
    assert body["provenance"]["domicile_only_mode"] is False
    assert (
        body["provenance"]["al_qabisi_selection_policy"]
        == "sequential_succession_no_simultaneous_tiebreak"
    )


def test_profile_route_preserves_al_qabisi_fallback_blockers(client: TestClient) -> None:
    response = client.post(
        "/v1/lord-of-the-turn/profile",
        json={
            "natal_asc": 0,
            "age": 0,
            "sr_chart": {
                "sr_asc": 0,
                "planets": {"Sun": 90, "Moon": 180, "Mars": 5},
                "house_placements": {"Mars": 3, "Sun": 1},
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["result"]["lord"] == "Sun"
    assert body["result"]["selection_reason"] == "exaltation_fallback"
    assert body["result"]["is_fallback"] is True
    mars = next(candidate for candidate in body["candidates"] if candidate["planet"] == "Mars")
    assert mars["sr_house"] == 3
    assert mars["blocker_reasons"] == ["cadent_in_sr"]


def test_profile_route_preserves_egyptian_testimony_method(client: TestClient) -> None:
    response = client.post(
        "/v1/lord-of-the-turn/profile",
        json={
            "natal_asc": 0,
            "age": 0,
            "method": "egyptian_al_sijzi",
            "sr_chart": {
                "sr_asc": 0,
                "planets": {
                    "Sun": 0,
                    "Moon": 180,
                    "Mars": 5,
                    "Jupiter": 30,
                    "Venus": 30,
                    "Mercury": 30,
                    "Saturn": 30,
                },
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["result"]["method"] == "egyptian_al_sijzi"
    assert body["result"]["lord"] == "Mars"
    assert body["result"]["selection_reason"] == "testimony_winner_witnessing"
    assert body["policy"] == {"method": "egyptian_al_sijzi", "combust_orb": 8.5}
    assert (
        body["provenance"]["testimony_count_policy"]
        == "binary_dignity_type_count_not_weighted_almuten"
    )


def test_profile_route_can_omit_validation_block(client: TestClient) -> None:
    response = client.post(
        "/v1/lord-of-the-turn/profile",
        json={
            "natal_asc": 0,
            "age": 0,
            "include_validation": False,
            "sr_chart": {
                "sr_asc": 0,
                "planets": {"Sun": 90, "Mars": 5},
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["validation"] == {"included": False, "passed": None, "failures": None}
    assert "engine_validation" not in body["provenance"]["stage_sequence"]


def test_profile_route_rejects_invalid_inputs(client: TestClient) -> None:
    bad_natal_asc = client.post(
        "/v1/lord-of-the-turn/profile",
        json={
            "natal_asc": "NaN",
            "age": 0,
            "sr_chart": {"sr_asc": 0, "planets": {"Sun": 90}},
        },
    )
    bad_age = client.post(
        "/v1/lord-of-the-turn/profile",
        json={
            "natal_asc": 0,
            "age": 2.5,
            "sr_chart": {"sr_asc": 0, "planets": {"Sun": 90}},
        },
    )
    bad_sr_asc = client.post(
        "/v1/lord-of-the-turn/profile",
        json={
            "natal_asc": 0,
            "age": 0,
            "sr_chart": {"sr_asc": "Infinity", "planets": {"Sun": 90}},
        },
    )
    bad_planet = client.post(
        "/v1/lord-of-the-turn/profile",
        json={
            "natal_asc": 0,
            "age": 0,
            "sr_chart": {"sr_asc": 0, "planets": {"Pluto": 90}},
        },
    )
    bad_house = client.post(
        "/v1/lord-of-the-turn/profile",
        json={
            "natal_asc": 0,
            "age": 0,
            "sr_chart": {
                "sr_asc": 0,
                "planets": {"Sun": 90},
                "house_placements": {"Sun": 13},
            },
        },
    )
    missing_house_planet = client.post(
        "/v1/lord-of-the-turn/profile",
        json={
            "natal_asc": 0,
            "age": 0,
            "sr_chart": {
                "sr_asc": 0,
                "planets": {"Sun": 90},
                "house_placements": {"Mars": 1},
            },
        },
    )
    bad_retrograde = client.post(
        "/v1/lord-of-the-turn/profile",
        json={
            "natal_asc": 0,
            "age": 0,
            "sr_chart": {
                "sr_asc": 0,
                "planets": {"Sun": 90},
                "retrograde_planets": ["Mars"],
            },
        },
    )
    bad_combust = client.post(
        "/v1/lord-of-the-turn/profile",
        json={
            "natal_asc": 0,
            "age": 0,
            "combust_orb": 0,
            "sr_chart": {"sr_asc": 0, "planets": {"Sun": 90}},
        },
    )
    bad_include_validation = client.post(
        "/v1/lord-of-the-turn/profile",
        json={
            "natal_asc": 0,
            "age": 0,
            "include_validation": "yes",
            "sr_chart": {"sr_asc": 0, "planets": {"Sun": 90}},
        },
    )

    _assert_validation_envelope(bad_natal_asc, message_fragment="natal_asc must be finite")
    _assert_validation_envelope(bad_age, message_fragment="age must be an integer")
    _assert_validation_envelope(bad_sr_asc, message_fragment="sr_asc must be finite")
    _assert_validation_envelope(bad_planet, message_fragment="planets key must be one of")
    _assert_validation_envelope(bad_house, message_fragment="must be in the range 1..12")
    _assert_validation_envelope(
        missing_house_planet,
        message_fragment="house_placements keys must also be present in planets",
    )
    _assert_validation_envelope(
        bad_retrograde,
        message_fragment="retrograde_planets must also be present in planets",
    )
    _assert_validation_envelope(bad_combust, message_fragment="combust_orb must be positive")
    _assert_validation_envelope(
        bad_include_validation,
        message_fragment="include_validation must be a boolean",
    )


def test_lord_of_the_turn_route_is_registered(client: TestClient) -> None:
    paths = {
        route.path
        for route in client.app.routes
        if route.path.startswith("/v1/lord-of-the-turn/")
    }

    assert paths == {"/v1/lord-of-the-turn/profile"}
