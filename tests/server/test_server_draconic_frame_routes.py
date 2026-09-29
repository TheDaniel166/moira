"""Draconic chart route: honest origin label and rotated houses (real engine).

Einstein, 1879-03-14 10:50:02 UT, Ulm (48.40 N, 9.9833 E), Placidus.
The draconic rotation is the module's own normalize(source - anchor); the
checks below are invariants of that rotation against the engine's own natal
houses, not a secondary-engine comparison.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest

from moira_server.app import create_app
from moira_server.config import ServerConfig

pytestmark = [pytest.mark.loopback, pytest.mark.requires_ephemeris]

_DT = "1879-03-14T10:50:02Z"
_LAT, _LON = 48.40, 9.9833


@pytest.fixture(scope="module")
def client():
    with TestClient(create_app(ServerConfig(docs_enabled=False))) as test_client:
        yield test_client


def _norm(x: float) -> float:
    return x % 360.0


def test_geocentric_chart_is_labelled_geocentric(client: TestClient) -> None:
    body = client.post("/v1/draconic/chart", json={"dt": _DT, "node_mode": "true"}).json()
    assert body["origin"] == "geocentric"
    assert body["houses"] is None and body["angles"] is None and body["house_system"] is None


def test_observer_chart_is_labelled_topocentric(client: TestClient) -> None:
    body = client.post(
        "/v1/draconic/chart",
        json={"dt": _DT, "node_mode": "true", "observer_lat": _LAT, "observer_lon": _LON},
    ).json()
    assert body["origin"] == "topocentric"


def test_place_gives_the_natal_houses_rotated_by_the_node(client, moira_engine) -> None:
    body = client.post(
        "/v1/draconic/chart",
        json={"dt": _DT, "node_mode": "true", "latitude": _LAT, "longitude": _LON, "house_system": "P"},
    ).json()
    anchor = body["anchor"]["longitude"]
    natal = moira_engine.houses(datetime(1879, 3, 14, 10, 50, 2, tzinfo=timezone.utc), _LAT, _LON, "P")

    assert body["origin"] == "geocentric"  # a place for the houses does not move the planets
    assert body["house_system"] == natal.effective_system
    assert len(body["houses"]) == len(natal.cusps)
    for drac, nat in zip(body["houses"], natal.cusps):
        assert drac == pytest.approx(_norm(nat - anchor), abs=1e-9)
    assert body["angles"]["asc"] == pytest.approx(_norm(natal.asc - anchor), abs=1e-9)
    assert body["angles"]["mc"] == pytest.approx(_norm(natal.mc - anchor), abs=1e-9)
    # Einstein: natal Asc 11°38' Cancer, True Node 2°44' Aquarius -> draconic Asc 8°55' Virgo.
    assert 158.9 < body["angles"]["asc"] < 158.92


def test_place_requires_both_coordinates(client: TestClient) -> None:
    response = client.post("/v1/draconic/chart", json={"dt": _DT, "node_mode": "true", "latitude": _LAT})
    assert response.status_code == 422
