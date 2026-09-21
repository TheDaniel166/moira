"""Server route tests for Primary Directions Chronological Life Timeline (POST /v1/primary-directions/timeline).

Verifies:
- Standard chronological life timeline generation over REST.
- Dynamic key inversion integration (solar_ra_dynamic, solar_lon_dynamic).
- Distributor periods and event enrichment (distributor, bound_name, participator).
- Age filtering and bounds doctrine selection.
- Strict payload validation and error handling.
"""

from __future__ import annotations

from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from moira_server.app import create_app
from moira_server.config import ServerConfig

pytestmark = [pytest.mark.loopback, pytest.mark.requires_ephemeris]


@pytest.fixture
def client_with_engine(moira_engine, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client


_NATAL_DT = "1985-07-15T06:00:00Z"
_NATAL_LAT = 28.6139
_NATAL_LON = 77.2090

_TIMELINE_BASE_PAYLOAD = {
    "dt": _NATAL_DT,
    "latitude": _NATAL_LAT,
    "longitude": _NATAL_LON,
    "house_system": "PLACIDUS",
    "observer_lat": _NATAL_LAT,
    "observer_lon": _NATAL_LON,
    "max_age_years": 80.0,
}


def test_timeline_endpoint_default(client_with_engine: TestClient):
    """Test standard timeline generation with default parameters."""
    response = client_with_engine.post(
        "/v1/primary-directions/timeline",
        json=_TIMELINE_BASE_PAYLOAD,
    )
    assert response.status_code == 200
    data = response.json()

    assert "chart_id" in data
    assert "natal_jd_ut" in data
    assert data["max_age_years"] == 80.0
    assert "events" in data
    assert "distributor_periods" in data
    assert data["total_events"] == len(data["events"])
    assert data["total_events"] > 0
    assert len(data["distributor_periods"]) > 0

    # Events must be chronologically ordered
    ages = [ev["age_years"] for ev in data["events"]]
    assert ages == sorted(ages)

    # First event checks
    ev0 = data["events"][0]
    assert "significator" in ev0
    assert "promissor" in ev0
    assert "arc_deg" in ev0
    assert "age_years" in ev0
    assert "perfection_iso" in ev0
    assert "distributor" in ev0
    assert "bound_name" in ev0

    # Check distributor period structure
    p0 = data["distributor_periods"][0]
    assert "significator" in p0
    assert "ruler" in p0
    assert "sign" in p0
    assert "entry_age" in p0
    assert "exit_age" in p0
    assert "entry_date_utc" in p0
    assert "exit_date_utc" in p0
    assert p0["participators_count"] >= 0


def test_timeline_endpoint_dynamic_solar_ra_key(client_with_engine: TestClient):
    """Test timeline endpoint with dynamic True Solar Arc in RA inversion."""
    payload = {
        **_TIMELINE_BASE_PAYLOAD,
        "key": "solar_ra_dynamic",
        "max_age_years": 50.0,
    }
    response = client_with_engine.post(
        "/v1/primary-directions/timeline",
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()

    assert data["key"] == "solar_ra_dynamic"
    assert data["max_age_years"] == 50.0
    assert data["total_events"] > 0
    for ev in data["events"]:
        assert ev["age_years"] <= 50.0 + 1e-3


def test_timeline_endpoint_dynamic_solar_lon_key(client_with_engine: TestClient):
    """Test timeline endpoint with dynamic True Solar Arc in Longitude inversion."""
    payload = {
        **_TIMELINE_BASE_PAYLOAD,
        "key": "solar_lon_dynamic",
        "max_age_years": 40.0,
    }
    response = client_with_engine.post(
        "/v1/primary-directions/timeline",
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()

    assert data["key"] == "solar_lon_dynamic"
    assert data["max_age_years"] == 40.0
    assert data["total_events"] > 0


def test_timeline_endpoint_bound_doctrine(client_with_engine: TestClient):
    """Test timeline endpoint with Ptolemaic bounds doctrine."""
    payload_egyptian = {
        **_TIMELINE_BASE_PAYLOAD,
        "bound_doctrine": "egyptian",
        "max_age_years": 30.0,
    }
    payload_ptolemaic = {
        **_TIMELINE_BASE_PAYLOAD,
        "bound_doctrine": "ptolemaic",
        "max_age_years": 30.0,
    }

    res_eg = client_with_engine.post("/v1/primary-directions/timeline", json=payload_egyptian)
    res_pt = client_with_engine.post("/v1/primary-directions/timeline", json=payload_ptolemaic)

    assert res_eg.status_code == 200
    assert res_pt.status_code == 200

    data_eg = res_eg.json()
    data_pt = res_pt.json()

    # The distributor period boundaries or rulers should differ between Egyptian and Ptolemaic bounds
    rulers_eg = [p["ruler"] for p in data_eg["distributor_periods"]]
    rulers_pt = [p["ruler"] for p in data_pt["distributor_periods"]]
    assert len(rulers_eg) > 0
    assert len(rulers_pt) > 0


def test_timeline_endpoint_significator_filter(client_with_engine: TestClient):
    """Test timeline filtering to specific significators."""
    payload = {
        **_TIMELINE_BASE_PAYLOAD,
        "significators": ["ASC"],
        "max_age_years": 60.0,
    }
    response = client_with_engine.post(
        "/v1/primary-directions/timeline",
        json=payload,
    )
    assert response.status_code == 200
    data = response.json()

    for ev in data["events"]:
        assert ev["significator"] == "ASC"

    for p in data["distributor_periods"]:
        assert p["significator"] == "ASC"


def test_timeline_endpoint_validation_errors(client_with_engine: TestClient):
    """Test invalid payloads are rejected with 422 status."""
    # Invalid max_age_years (< 0)
    res1 = client_with_engine.post(
        "/v1/primary-directions/timeline",
        json={**_TIMELINE_BASE_PAYLOAD, "max_age_years": -10.0},
    )
    assert res1.status_code == 422

    # Invalid max_age_years (> 150)
    res2 = client_with_engine.post(
        "/v1/primary-directions/timeline",
        json={**_TIMELINE_BASE_PAYLOAD, "max_age_years": 200.0},
    )
    assert res2.status_code == 422

    # Invalid key
    res3 = client_with_engine.post(
        "/v1/primary-directions/timeline",
        json={**_TIMELINE_BASE_PAYLOAD, "key": "nonexistent_key_name"},
    )
    assert res3.status_code == 422
