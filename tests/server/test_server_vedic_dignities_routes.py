"""P9-08 Vedic Dignities route tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira.vedic_dignities import (
    chart_dignity_profile,
    dignity_condition_profile,
    planetary_relationships,
    vedic_dignity,
)
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


_ALL_LONS = {
    "Sun": 10.0,
    "Moon": 33.0,
    "Mars": 280.0,
    "Mercury": 155.0,
    "Jupiter": 130.0,
    "Venus": 357.0,
    "Saturn": 200.0,
}


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


@pytest.mark.parametrize(
    ("planet", "longitude", "rank"),
    [
        ("Sun", 10.0, "exaltation"),
        ("Sun", 190.0, "debilitation"),
        ("Sun", 4 * 30.0 + 5.0, "mulatrikona"),
        ("Sun", 4 * 30.0 + 25.0, "own_sign"),
        ("Sun", 7 * 30.0 + 15.0, "friend_sign"),
        ("Sun", 2 * 30.0 + 15.0, "neutral_sign"),
        ("Sun", 1 * 30.0 + 15.0, "enemy_sign"),
    ],
)
def test_vedic_dignity_route_preserves_rank_examples(
    planet: str,
    longitude: float,
    rank: str,
) -> None:
    direct = vedic_dignity(planet, longitude)

    with _client() as client:
        response = client.post(
            "/v1/vedic-dignities/dignity",
            json={"planet": planet, "sidereal_longitude": longitude},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["planet"] == direct.planet
    assert body["sidereal_longitude"] == direct.sidereal_longitude
    assert body["sign_index"] == direct.sign_index
    assert body["sign"] == direct.sign
    assert body["dignity_rank"] == direct.dignity_rank == rank
    assert body["is_exalted"] == direct.is_exalted
    assert body["is_debilitated"] == direct.is_debilitated
    assert body["is_mulatrikona"] == direct.is_mulatrikona
    assert body["is_own_sign"] == direct.is_own_sign
    assert body["is_strong"] == direct.is_strong
    assert body["is_weak"] == direct.is_weak
    assert body["exaltation_score"] == direct.exaltation_score
    assert body["ayanamsa_system"] == "Lahiri"


def test_vedic_dignity_route_preserves_policy_provenance_label() -> None:
    with _client() as client:
        response = client.post(
            "/v1/vedic-dignities/dignity",
            json={
                "planet": "Sun",
                "sidereal_longitude": 10.0,
                "policy": {"ayanamsa_system": "Krishnamurti"},
            },
        )

    assert response.status_code == 200
    assert response.json()["ayanamsa_system"] == "Krishnamurti"


def test_vedic_dignity_route_preserves_mercury_overlap_as_exaltation() -> None:
    with _client() as client:
        response = client.post(
            "/v1/vedic-dignities/dignity",
            json={"planet": "Mercury", "sidereal_longitude": 165.0},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["dignity_rank"] == "exaltation"
    assert body["is_exalted"] is True
    assert body["is_mulatrikona"] is False


def test_vedic_dignity_route_preserves_longitude_wrapping() -> None:
    direct = vedic_dignity("Sun", 370.0)

    with _client() as client:
        response = client.post(
            "/v1/vedic-dignities/dignity",
            json={"planet": "Sun", "sidereal_longitude": 370.0},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["sidereal_longitude"] == direct.sidereal_longitude == 10.0
    assert body["dignity_rank"] == "exaltation"


def test_vedic_dignity_relationships_route_preserves_directional_truth() -> None:
    direct = planetary_relationships(_ALL_LONS)

    with _client() as client:
        response = client.post(
            "/v1/vedic-dignities/relationships",
            json={"sidereal_longitudes": _ALL_LONS},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["ayanamsa_system"] == "Lahiri"
    assert len(body["relationships"]) == len(direct) == 42
    first = body["relationships"][0]
    assert first["from_planet"] == direct[0].from_planet == "Sun"
    assert first["to_planet"] == direct[0].to_planet == "Moon"
    assert first["natural"] == direct[0].natural
    assert first["temporary"] == direct[0].temporary
    assert first["compound"] == direct[0].compound
    assert first["is_friendly"] == direct[0].is_friendly
    assert first["is_hostile"] == direct[0].is_hostile


def test_vedic_dignity_relationships_route_preserves_engine_unknown_key_behavior() -> None:
    with _client() as client:
        response = client.post(
            "/v1/vedic-dignities/relationships",
            json={"sidereal_longitudes": {"Sun": 10.0, "Pluto": 50.0}},
        )

    assert response.status_code == 200
    assert response.json()["relationships"] == []


def test_vedic_dignity_condition_route_matches_engine_profile() -> None:
    result = vedic_dignity("Sun", 190.0)
    direct = dignity_condition_profile(result)

    with _client() as client:
        response = client.post(
            "/v1/vedic-dignities/condition",
            json={"planet": "Sun", "sidereal_longitude": 190.0},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["planet"] == direct.planet
    assert body["dignity_rank"] == direct.dignity_rank == "debilitation"
    assert body["tier"] == direct.tier == "weak"
    assert body["result"]["dignity_rank"] == "debilitation"
    assert body["ayanamsa_system"] == "Lahiri"


def test_vedic_chart_profile_route_matches_engine_profile() -> None:
    results = {planet: vedic_dignity(planet, lon) for planet, lon in _ALL_LONS.items()}
    direct = chart_dignity_profile(results)

    with _client() as client:
        response = client.post(
            "/v1/vedic-dignities/chart-profile",
            json={"sidereal_longitudes": _ALL_LONS},
        )

    assert response.status_code == 200
    body = response.json()
    assert set(body["results"]) == set(results)
    assert body["strong_count"] == direct.strong_count
    assert body["neutral_count"] == direct.neutral_count
    assert body["weak_count"] == direct.weak_count
    assert body["strongest_planet"] == direct.strongest_planet
    assert body["weakest_planet"] == direct.weakest_planet
    assert body["planet_tiers"] == direct.planet_tiers
    assert body["exaltation_scores"] == direct.exaltation_scores


def test_vedic_dignity_route_rejects_invalid_planet() -> None:
    with _client() as client:
        response = client.post(
            "/v1/vedic-dignities/dignity",
            json={"planet": "Rahu", "sidereal_longitude": 100.0},
        )

    _assert_validation_envelope(response, message_fragment="planet must be one of")


def test_vedic_dignity_route_rejects_malformed_longitude() -> None:
    with _client() as client:
        response = client.post(
            "/v1/vedic-dignities/dignity",
            json={"planet": "Sun", "sidereal_longitude": "not-a-number"},
        )

    _assert_validation_envelope(response)


def test_vedic_chart_profile_route_rejects_empty_map() -> None:
    with _client() as client:
        response = client.post(
            "/v1/vedic-dignities/chart-profile",
            json={"sidereal_longitudes": {}},
        )

    _assert_validation_envelope(response)


def test_vedic_chart_profile_route_rejects_invalid_planet() -> None:
    with _client() as client:
        response = client.post(
            "/v1/vedic-dignities/chart-profile",
            json={"sidereal_longitudes": {"Sun": 10.0, "Pluto": 50.0}},
        )

    _assert_validation_envelope(response, message_fragment="planet must be one of")


def test_vedic_dignity_route_rejects_empty_ayanamsa_label() -> None:
    with _client() as client:
        response = client.post(
            "/v1/vedic-dignities/dignity",
            json={
                "planet": "Sun",
                "sidereal_longitude": 10.0,
                "policy": {"ayanamsa_system": ""},
            },
        )

    _assert_validation_envelope(response, message_fragment="ayanamsa_system")


def test_vedic_dignity_routes_are_registered() -> None:
    app = create_app(ServerConfig(docs_enabled=False))
    paths = {route.path for route in app.routes}

    assert "/v1/vedic-dignities/dignity" in paths
    assert "/v1/vedic-dignities/relationships" in paths
    assert "/v1/vedic-dignities/condition" in paths
    assert "/v1/vedic-dignities/chart-profile" in paths
