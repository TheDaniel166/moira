from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest

from moira.obliquity import nutation
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback


@pytest.fixture
def client_with_engine(
    moira_engine,
    monkeypatch: pytest.MonkeyPatch,
) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client


def test_website_location_search_returns_bounded_seeded_city(
    client_with_engine: TestClient,
) -> None:
    response = client_with_engine.get("/v1/locations/search", params={"query": "new york"})

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "new york"
    assert body["matches"][0]["name"] == "New York"
    assert body["matches"][0]["timezone"] == "America/New_York"
    assert body["matches"][0]["source"] == "moira_server.website_seed_gazetteer.v1"


def test_website_timezone_validation_uses_iana_database(
    client_with_engine: TestClient,
) -> None:
    valid = client_with_engine.post(
        "/v1/locations/timezone/validate",
        json={"timezone": "America/New_York"},
    )
    invalid = client_with_engine.post(
        "/v1/locations/timezone/validate",
        json={"timezone": "Not/AZone"},
    )

    assert valid.status_code == 200
    assert valid.json() == {"timezone": "America/New_York", "valid": True}
    assert invalid.status_code == 200
    assert invalid.json() == {"timezone": "Not/AZone", "valid": False}


@pytest.mark.requires_ephemeris
def test_website_pipeline_planet_route_matches_existing_reduction_surface(
    client_with_engine: TestClient,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    payload = {
        "dt": dt.isoformat(),
        "body": "Moon",
        "observer_lat": 40.7128,
        "observer_lon": -74.0060,
        "observer_elev_m": 10.0,
    }

    website = client_with_engine.post("/v1/pipeline/positions/planet", json=payload)
    canonical = client_with_engine.post("/v1/positions/planet/reduction", json=payload)

    assert website.status_code == 200
    assert canonical.status_code == 200
    assert website.json() == canonical.json()

    reduction = website.json()["reduction"]
    stages = reduction["stages"]
    assert [stage["num"] for stage in stages] == list(range(9))
    assert [stage["name"] for stage in stages] == [
        "Geometric geocentric",
        "Light-time iteration",
        "Gravitational deflection",
        "Annual aberration",
        "IAU 2006 frame bias",
        "IAU 2006 precession",
        "IAU 2000A nutation",
        "Topocentric parallax",
        "Topocentric diurnal aberration",
    ]
    assert stages[0]["delta"] is None
    assert stages[0]["ref_pos"] is not None
    assert stages[1]["enabled"] is True
    assert abs(stages[1]["delta"]) > 0.0
    assert stages[2]["enabled"] is False  # Sun/Moon self-deflection is not applied.
    dpsi_deg, _deps_deg = nutation(reduction["jd_tt"])
    assert stages[6]["delta"] == pytest.approx(round(dpsi_deg * 3600.0, 6))
    assert stages[7]["enabled"] is True
    assert stages[8]["enabled"] is True

    enabled_total = round(
        sum(
            stage["delta"]
            for stage in stages
            if stage["delta"] is not None and stage["enabled"]
        ),
        6,
    )
    assert reduction["total_delta_arcsec"] == pytest.approx(enabled_total)
    assert reduction["stage_longitudes"]["light_time"] != 0.0
    assert reduction["stage_longitudes"]["geocentric"] == pytest.approx(
        reduction["geocentric_longitude"]
    )


@pytest.mark.requires_ephemeris
def test_website_pipeline_sky_route_matches_existing_reduction_surface(
    client_with_engine: TestClient,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    payload = {
        "dt": dt.isoformat(),
        "body": "Venus",
        "latitude": 51.5,
        "longitude": -0.1,
    }

    website = client_with_engine.post("/v1/pipeline/positions/sky", json=payload)
    canonical = client_with_engine.post("/v1/positions/sky/reduction", json=payload)

    assert website.status_code == 200
    assert canonical.status_code == 200
    assert website.json() == canonical.json()


@pytest.mark.requires_ephemeris
def test_website_pipeline_chart_route_exposes_existing_reduction_truth(
    client_with_engine: TestClient,
) -> None:
    dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    response = client_with_engine.post(
        "/v1/pipeline/chart",
        json={"dt": dt.isoformat(), "bodies": ["Sun"], "include_nodes": False},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["reduction"]["engine_surface"] == "Moira.chart"
    assert body["reduction"]["source_vessel"] == "Chart"
    assert body["reduction"]["requested_bodies"] == ["Sun"]
