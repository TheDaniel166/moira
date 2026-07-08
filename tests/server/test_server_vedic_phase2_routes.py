"""Vedic Phase-2 quick-win route tests: vimshopaka, personal muhurta, sade sati."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


_LONS = {
    "Sun": 10.0, "Moon": 35.0, "Mars": 190.0, "Mercury": 160.0,
    "Jupiter": 100.0, "Venus": 185.0, "Saturn": 280.0,
}


@pytest.fixture
def client(moira_engine, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# /v1/varga/vimshopaka
# ---------------------------------------------------------------------------

def test_vimshopaka_route_matches_engine(client: TestClient) -> None:
    from moira.varga import vimshopaka_all, vargottama_planets

    response = client.post(
        "/v1/varga/vimshopaka",
        json={"sidereal_longitudes": _LONS, "group": "shodashavarga"},
    )

    assert response.status_code == 200
    body = response.json()
    direct = vimshopaka_all(_LONS, "shodashavarga")
    assert set(body["planets"]) == set(direct)
    for planet, vb in direct.items():
        planet_body = body["planets"][planet]
        assert planet_body["total"] == pytest.approx(vb.total)
        assert len(planet_body["entries"]) == len(vb.entries)
        for entry_body, entry in zip(planet_body["entries"], vb.entries):
            assert entry_body["division"] == entry.division
            assert entry_body["dignity"] == entry.dignity
            assert entry_body["points"] == pytest.approx(entry.points)
    assert tuple(body["vargottama"]) == tuple(sorted(vargottama_planets(_LONS)))


def test_vimshopaka_route_rejects_missing_planet(client: TestClient) -> None:
    lons = dict(_LONS)
    del lons["Saturn"]
    response = client.post(
        "/v1/varga/vimshopaka",
        json={"sidereal_longitudes": lons},
    )
    assert response.status_code == 422


def test_vimshopaka_route_rejects_unknown_group(client: TestClient) -> None:
    response = client.post(
        "/v1/varga/vimshopaka",
        json={"sidereal_longitudes": _LONS, "group": "panchavarga"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# /v1/muhurta/personal/score
# ---------------------------------------------------------------------------

def test_personal_muhurta_route_matches_engine(client: TestClient) -> None:
    from moira.muhurta import personal_muhurta_score
    from moira.panchanga import panchanga_at
    from moira.sidereal import tropical_to_sidereal

    payload = {
        "sun_tropical_lon": 280.0,
        "moon_tropical_lon": 35.0,
        "jd": 2451545.0,
        "janma_moon_sidereal_lon": 100.0,
    }
    response = client.post("/v1/muhurta/personal/score", json=payload)

    assert response.status_code == 200
    body = response.json()
    panchanga = panchanga_at(280.0, 35.0, 2451545.0)
    transit_sidereal = tropical_to_sidereal(35.0, 2451545.0, system="Lahiri")
    direct = personal_muhurta_score(panchanga, 100.0, transit_sidereal)
    assert body["total"] == pytest.approx(direct.total)
    assert body["breakdown"]["tara"] == pytest.approx(direct.breakdown["tara"])
    assert body["breakdown"]["chandra"] == pytest.approx(direct.breakdown["chandra"])
    assert body["tara"]["tara_name"] == direct.tara.tara_name
    assert body["chandra"]["house_from_moon"] == direct.chandra.house_from_moon
    assert body["chandra"]["is_chandrashtama"] is direct.chandra.is_chandrashtama


def test_personal_muhurta_route_rejects_non_finite_janma(client: TestClient) -> None:
    response = client.post(
        "/v1/muhurta/personal/score",
        json={
            "sun_tropical_lon": 280.0,
            "moon_tropical_lon": 35.0,
            "jd": 2451545.0,
            "janma_moon_sidereal_lon": "NaN",
        },
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# /v1/sade-sati
# ---------------------------------------------------------------------------

def test_sade_sati_status_route_matches_engine(client: TestClient) -> None:
    from moira.sade_sati import sade_sati_status

    response = client.post(
        "/v1/sade-sati/status",
        json={"natal_moon_sidereal_lon": 35.0, "saturn_sidereal_lon": 5.0},
    )

    assert response.status_code == 200
    body = response.json()
    direct = sade_sati_status(35.0, 5.0)
    assert body["phase"] == direct.phase == "rising"
    assert body["house_from_moon"] == direct.house_from_moon
    assert body["in_sade_sati"] is direct.in_sade_sati
    assert body["is_ashtama_shani"] is direct.is_ashtama_shani
    assert body["is_kantaka_shani"] is direct.is_kantaka_shani


@pytest.mark.requires_ephemeris
def test_sade_sati_windows_route_returns_marked_windows(client: TestClient) -> None:
    response = client.post(
        "/v1/sade-sati/windows",
        json={
            "natal_moon_sidereal_lon": 35.0,
            "start_dt": "2000-01-01T00:00:00+00:00",
            "end_dt": "2006-01-01T00:00:00+00:00",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["windows"], "expected windows for a Taurus Moon 2000-2006"
    for window in body["windows"]:
        assert window["phase"] in {"rising", "peak", "setting"}
        assert window["start_jd"] < window["end_jd"]
    ranks = [w["start_jd"] for w in body["windows"]]
    assert ranks == sorted(ranks)


def test_sade_sati_windows_route_rejects_naive_datetime(client: TestClient) -> None:
    response = client.post(
        "/v1/sade-sati/windows",
        json={
            "natal_moon_sidereal_lon": 35.0,
            "start_dt": "2000-01-01T00:00:00",
            "end_dt": "2006-01-01T00:00:00+00:00",
        },
    )
    assert response.status_code == 422
