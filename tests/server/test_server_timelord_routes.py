from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest

from moira.profections import annual_profection, monthly_profection, profection_schedule
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.network


@pytest.fixture
def client_with_engine(moira_engine, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    app = create_app(ServerConfig(docs_enabled=False))
    with TestClient(app) as client:
        yield client


def _natal_payload() -> dict[str, object]:
    return {
        "dt": "2000-01-01T12:00:00Z",
        "latitude": 40.7128,
        "longitude": -74.0060,
        "include_nodes": False,
    }


@pytest.mark.requires_ephemeris
def test_profection_routes_match_engine_truth(client_with_engine: TestClient, moira_engine) -> None:
    natal = _natal_payload()
    natal_dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    current_dt = datetime(2024, 6, 1, 0, 0, tzinfo=timezone.utc)
    chart = moira_engine.chart(natal_dt, include_nodes=False)
    houses = moira_engine.houses(natal_dt, natal["latitude"], natal["longitude"])  # type: ignore[index]
    natal_positions = chart.longitudes(include_nodes=False)

    direct_annual = annual_profection(houses.asc, 24, natal_positions=natal_positions)
    direct_monthly = monthly_profection(houses.asc, 24, 3)
    direct_schedule = profection_schedule(
        houses.asc,
        chart.jd_ut,
        moira_engine.chart(current_dt).jd_ut,
        natal_positions=natal_positions,
    )

    annual_response = client_with_engine.post("/v1/profections/annual", json={"natal": natal, "age_years": 24})
    monthly_response = client_with_engine.post(
        "/v1/profections/monthly",
        json={"natal": natal, "age_years": 24, "month_index": 3},
    )
    schedule_response = client_with_engine.post(
        "/v1/profections/schedule",
        json={"natal": natal, "current_dt": current_dt.isoformat().replace("+00:00", "Z")},
    )

    assert annual_response.status_code == 200
    assert annual_response.json()["profected_house"] == direct_annual.profected_house
    assert annual_response.json()["lord_of_year"] == direct_annual.lord_of_year
    assert annual_response.json()["activated_planets"] == direct_annual.activated_planets

    assert monthly_response.status_code == 200
    assert monthly_response.json()["profected_longitude"] == pytest.approx(direct_monthly[0])
    assert monthly_response.json()["sign"] == direct_monthly[1]
    assert monthly_response.json()["lord_of_month"] == direct_monthly[2]

    assert schedule_response.status_code == 200
    assert schedule_response.json()["profected_house"] == direct_schedule.profected_house
    assert schedule_response.json()["lord_of_year"] == direct_schedule.lord_of_year


def test_profection_routes_reject_invalid_inputs(client_with_engine: TestClient) -> None:
    natal = _natal_payload()

    negative_age = client_with_engine.post("/v1/profections/annual", json={"natal": natal, "age_years": -1})
    invalid_month = client_with_engine.post(
        "/v1/profections/monthly",
        json={"natal": natal, "age_years": 24, "month_index": 12},
    )
    invalid_body = client_with_engine.post(
        "/v1/profections/annual",
        json={"natal": {**natal, "bodies": ["Pluto", "Bogus"]}, "age_years": 24},
    )

    assert negative_age.status_code == 422
    assert invalid_month.status_code == 422
    assert invalid_body.status_code == 422
