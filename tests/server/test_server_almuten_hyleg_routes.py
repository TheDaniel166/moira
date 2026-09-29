"""Almuten (degree, figuris) and hyleg (Lilly 1647) route tests — kernel-free."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira.dignities import almuten_figuris_determination, almuten_of_degree_determination
from moira.longevity import find_alcocoden_lilly_1647, find_hyleg_lilly_1647
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


_POSITIONS = {
    "Sun": 10.0, "Moon": 100.0, "Mercury": 20.0, "Venus": 40.0,
    "Mars": 200.0, "Jupiter": 250.0, "Saturn": 300.0,
}
_CUSPS = [30.0 * i for i in range(12)]
_SPEEDS = {
    "Sun": 1.0, "Moon": 13.0, "Mercury": 1.5, "Venus": -0.3,
    "Mars": 0.6, "Jupiter": 0.1, "Saturn": 0.03,
}
_STARS = {"Regulus": 150.0, "Spica": 204.0, "Algol": 56.0}


def test_almuten_degree_route_matches_engine(client: TestClient) -> None:
    response = client.post("/v1/almuten/degree", json={"longitude": 0.0, "is_day_chart": True})
    assert response.status_code == 200
    body = response.json()
    direct = almuten_of_degree_determination(0.0, True)
    assert body["almuten"] == direct.almuten == "Sun"
    assert body["doctrine"] == "william_lilly_1647_almuten_of_degree"
    assert [t["total"] for t in body["tallies"]] == [t.total for t in direct.tallies]
    assert body["provenance"]["bounds_table"] == "william_lilly_1647"
    assert body["provenance"]["triplicity_table"] == "william_lilly_1647"
    assert body["provenance"]["unsourced_elements"] == []
    assert "p. 104" in body["provenance"]["doctrine_source"]


def test_almuten_degree_route_legacy_by_name_and_lilly_tie(client: TestClient) -> None:
    legacy = client.post(
        "/v1/almuten/degree",
        json={"longitude": 0.0, "is_day_chart": True, "doctrine": "moira_legacy_v1"},
    ).json()
    assert legacy["doctrine"] == "moira_almuten_of_degree_v1"
    assert legacy["provenance"]["bounds_table"] == "egyptian"
    assert legacy["provenance"]["unsourced_elements"] == [
        "participating_triplicity_ruler_awarded_1_point"
    ]
    tie = client.post("/v1/almuten/degree", json={"longitude": 21.0, "is_day_chart": True}).json()
    assert tie["almuten"] is None
    assert tie["tied_planets"] == ["Sun", "Mars"]


def test_almuten_figuris_route_matches_engine(client: TestClient) -> None:
    # Lilly's own whole-figure rule needs daily motions, the node and the stars.
    whole = client.post(
        "/v1/almuten/figuris",
        json={
            "positions": _POSITIONS,
            "house_cusps": _CUSPS,
            "is_day_chart": False,  # Sun at 10 Aries is below the horizon
            "speeds": _SPEEDS,
            "north_node_longitude": 123.0,
            "fixed_star_longitudes": _STARS,
        },
    )
    assert whole.status_code == 200
    whole_body = whole.json()
    direct_whole = almuten_figuris_determination(
        _POSITIONS, _CUSPS, False, speeds=_SPEEDS, north_node_longitude=123.0,
        fixed_star_longitudes=_STARS,
    )
    assert whole_body["doctrine"] == "william_lilly_1647_whole_figure"
    assert whole_body["almuten"] == direct_whole.almuten
    assert [t["accidental_points"] for t in whole_body["tallies"]] == [
        t.accidental_points for t in direct_whole.tallies
    ]
    assert "p. 115" in whole_body["provenance"]["doctrine_source"]
    missing = client.post(
        "/v1/almuten/figuris",
        json={"positions": _POSITIONS, "house_cusps": _CUSPS, "is_day_chart": True},
    )
    assert missing.status_code == 422

    response = client.post(
        "/v1/almuten/figuris",
        json={"positions": _POSITIONS, "house_cusps": _CUSPS, "is_day_chart": True,
              "doctrine": "william_lilly_1647_others_five_places"},
    )
    assert response.status_code == 200
    body = response.json()
    direct = almuten_figuris_determination(
        _POSITIONS, _CUSPS, True, doctrine="william_lilly_1647_others_five_places",
    )
    assert body["almuten"] == direct.almuten
    assert body["doctrine"] == "william_lilly_1647_asc_mc_sun_moon_fortune"
    assert [p["name"] for p in body["scored_points"]] == [
        "Ascendant", "Tenth cusp", "Sun", "Moon", "Part of Fortune",
    ]
    assert body["tied_planets"] == list(direct.tied_planets)
    assert body["provenance"]["unsourced_elements"] == []
    assert body["provenance"]["not_computed"]

    refused = client.post(
        "/v1/almuten/figuris",
        json={"positions": _POSITIONS, "house_cusps": _CUSPS, "is_day_chart": True,
              "day_ruler": "Sun"},
    )
    assert refused.status_code == 422

    legacy = client.post(
        "/v1/almuten/figuris",
        json={
            "positions": _POSITIONS,
            "house_cusps": _CUSPS,
            "is_day_chart": True,
            "doctrine": "moira_legacy_v1",
            "day_ruler": "Sun",
            "hour_ruler": "Mars",
            "prenatal_syzygy_longitude": 355.0,
        },
    ).json()
    direct_legacy = almuten_figuris_determination(
        _POSITIONS, _CUSPS, True, day_ruler="Sun", hour_ruler="Mars", prenatal_syzygy_lon=355.0,
        doctrine="moira_legacy_v1",
    )
    assert legacy["almuten"] == direct_legacy.almuten
    assert legacy["doctrine"] == "moira_almuten_figuris_v1"
    assert [p["name"] for p in legacy["scored_points"]] == [
        "Sun", "Moon", "Ascendant", "Lot of Fortune", "Prenatal Syzygy",
    ]
    assert legacy["provenance"]["unsourced_elements"] == [
        "participating_triplicity_ruler_awarded_1_point",
        "house_points_1st_12_to_12th_1_and_day_ruler_7_hour_ruler_6",
    ]


def test_almuten_routes_reject_bad_inputs(client: TestClient) -> None:
    assert client.post("/v1/almuten/degree", json={"longitude": "NaN", "is_day_chart": True}).status_code == 422
    assert client.post("/v1/almuten/degree", json={"longitude": 1.0, "is_day_chart": 1}).status_code == 422
    no_moon = {k: v for k, v in _POSITIONS.items() if k != "Moon"}
    assert client.post(
        "/v1/almuten/figuris",
        json={"positions": no_moon, "house_cusps": _CUSPS, "is_day_chart": True},
    ).status_code == 422
    assert client.post(
        "/v1/almuten/figuris",
        json={"positions": {**_POSITIONS, "Pluto": 1.0}, "house_cusps": _CUSPS, "is_day_chart": True},
    ).status_code == 422
    assert client.post(
        "/v1/almuten/figuris",
        json={"positions": _POSITIONS, "house_cusps": _CUSPS[:11], "is_day_chart": True},
    ).status_code == 422


def test_hyleg_route_selects_and_matches_engine(client: TestClient) -> None:
    payload = {
        "sun_longitude": 280.0,
        "moon_longitude": 100.0,
        "house_cusps": _CUSPS,
        "is_day_chart": True,
    }
    response = client.post("/v1/hyleg/lilly-1647", json=payload)
    assert response.status_code == 200
    body = response.json()
    direct = find_hyleg_lilly_1647(280.0, 100.0, _CUSPS, True)
    assert body["doctrine"] == "william_lilly_1647"
    assert body["status"] == "selected"
    assert body["hyleg"] == direct.hyleg == "Sun"
    assert "Christian Astrology (1647), Book III ch. CIV" in body["provenance"]["source"]


def test_hyleg_route_fails_closed_when_step_not_admitted(client: TestClient) -> None:
    response = client.post(
        "/v1/hyleg/lilly-1647",
        json={
            "sun_longitude": 220.0,
            "moon_longitude": 340.0,
            "house_cusps": _CUSPS,
            "is_day_chart": True,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "not_evaluable"
    assert body["hyleg"] is None
    assert body["reason"].startswith("planet_positions_required_for_dominion_step")

    dominion = client.post(
        "/v1/hyleg/lilly-1647",
        json={
            "sun_longitude": 220.0,
            "moon_longitude": 340.0,
            "house_cusps": _CUSPS,
            "is_day_chart": True,
            "planets": {"Mercury": 20.0, "Venus": 40.0, "Mars": 200.0,
                        "Jupiter": 250.0, "Saturn": 300.0},
            "prenatal_new_moon_longitude": 200.0,
        },
    ).json()
    assert dominion["hyleg"] == "Mars"
    assert dominion["selection_step"] == "dominion_planet_in_hylegiacal_place"
    assert dominion["dominion_places"] == {
        "Sun": 220.0, "preceding_new_moon": 200.0, "Ascendant": 0.0,
    }


def test_hyleg_route_requires_equatorial_inputs_only_when_needed(client: TestClient) -> None:
    response = client.post(
        "/v1/hyleg/lilly-1647",
        json={
            "sun_longitude": 10.0,
            "moon_longitude": 100.0,
            "house_cusps": _CUSPS,
            "is_day_chart": True,
        },
    )
    assert response.status_code == 422
    assert "armc, obliquity and geographic_latitude" in response.json()["message"]


def test_alcocoden_route_matches_engine(client: TestClient) -> None:
    positions = {**_POSITIONS, "Sun": 280.0}
    response = client.post(
        "/v1/hyleg/lilly-1647/alcocoden",
        json={"positions": positions, "house_cusps": _CUSPS, "is_day_chart": True},
    )
    assert response.status_code == 200
    body = response.json()
    direct = find_alcocoden_lilly_1647(positions, _CUSPS, True)
    assert body["status"] == "selected"
    assert body["alcocoden"] == direct.alcocoden == "Venus"
    assert body["hyleg"]["hyleg"] == "Sun"
    assert body["years_greater"] == 82.0
    assert [c["planet"] for c in body["candidates"]] == [c.planet for c in direct.candidates]
    assert "Book III ch. CIV" in body["provenance"]["source"]

    short = client.post(
        "/v1/hyleg/lilly-1647/alcocoden",
        json={"positions": {"Sun": 280.0}, "house_cusps": _CUSPS, "is_day_chart": True},
    )
    assert short.status_code == 422


def test_almuten_and_hyleg_routes_are_registered(client: TestClient) -> None:
    paths = {route.path for route in client.app.routes}
    assert {
        "/v1/almuten/degree",
        "/v1/almuten/figuris",
        "/v1/hyleg/lilly-1647",
        "/v1/hyleg/lilly-1647/alcocoden",
    } <= paths
