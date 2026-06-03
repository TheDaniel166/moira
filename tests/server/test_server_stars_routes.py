from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest

from moira.julian import jd_from_datetime, ut_to_tt
from moira.stars import star_at
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


@pytest.fixture
def client_with_engine(
    moira_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client


def test_server_startup_includes_stars_router(
    moira_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)

    app = create_app(ServerConfig(docs_enabled=True))
    with TestClient(app) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/v1/stars/position" in paths
    assert "/v1/stars/bulk" in paths
    assert "/v1/stars/list" in paths


@pytest.mark.requires_ephemeris
def test_star_position_route_converts_transport_datetime_to_jd_tt(
    client_with_engine: TestClient,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    jd_tt = ut_to_tt(jd_from_datetime(dt))
    direct = star_at("Sirius", jd_tt)

    response = client_with_engine.post(
        "/v1/stars/position",
        json={
            "dt": dt.isoformat(),
            "star": "Sirius",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == direct.name
    assert body["longitude"] == pytest.approx(direct.longitude)
    assert body["latitude"] == pytest.approx(direct.latitude)
    assert body["magnitude"] == pytest.approx(direct.magnitude)


@pytest.mark.requires_ephemeris
def test_stars_bulk_route_preserves_valid_results_and_collects_missing_names(
    client_with_engine: TestClient,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    jd_tt = ut_to_tt(jd_from_datetime(dt))
    direct = star_at("Sirius", jd_tt)

    response = client_with_engine.post(
        "/v1/stars/bulk",
        json={
            "dt": dt.isoformat(),
            "stars": ["Sirius", "DefinitelyNotAStar"],
            "skip_missing": True,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert "Sirius" in body["results"]
    assert body["results"]["Sirius"]["longitude"] == pytest.approx(direct.longitude)
    assert body["missing"] == ["DefinitelyNotAStar"]
