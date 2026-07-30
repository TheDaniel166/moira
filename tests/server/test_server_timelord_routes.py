from __future__ import annotations

from datetime import datetime, timezone

from fastapi.testclient import TestClient
import pytest

from moira.profections import annual_profection, monthly_profection, profection_schedule
from moira_server.app import create_app
from moira_server.config import ServerConfig


pytestmark = pytest.mark.loopback


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
        "activation_orb": 0.25,
    }


@pytest.mark.requires_ephemeris
def test_profection_routes_match_engine_truth(client_with_engine: TestClient, moira_engine) -> None:
    natal = _natal_payload()
    natal_dt = datetime(2000, 1, 1, 12, 0, tzinfo=timezone.utc)
    current_dt = datetime(2024, 6, 1, 0, 0, tzinfo=timezone.utc)
    chart = moira_engine.chart(natal_dt, include_nodes=False)
    houses = moira_engine.houses(natal_dt, natal["latitude"], natal["longitude"])  # type: ignore[index]
    natal_positions = chart.longitudes(include_nodes=False)

    direct_annual = annual_profection(
        houses.asc,
        24,
        natal_positions=natal_positions,
        activation_orb=0.25,
    )
    direct_monthly = monthly_profection(houses.asc, 24, 3)
    direct_schedule = profection_schedule(
        houses.asc,
        natal_dt,
        current_dt,
        natal_positions=natal_positions,
        civil_timezone="America/New_York",
        ambiguous_time_policy="earlier_occurrence",
        activation_orb=0.25,
    )

    annual_response = client_with_engine.post("/v1/profections/annual", json={"natal": natal, "age_years": 24})
    monthly_response = client_with_engine.post(
        "/v1/profections/monthly",
        json={"natal": natal, "age_years": 24, "month_index": 3},
    )
    schedule_response = client_with_engine.post(
        "/v1/profections/schedule",
        json={
            "natal": natal,
            "current_dt": current_dt.isoformat().replace("+00:00", "Z"),
            "civil_timezone": "America/New_York",
            "ambiguous_time_policy": "earlier_occurrence",
            "interval_policy": "equal_twelfths_of_civil_anniversary_year",
        },
    )

    assert annual_response.status_code == 200
    assert annual_response.json()["profected_house"] == direct_annual.profected_house
    assert annual_response.json()["lord_of_year"] == direct_annual.lord_of_year
    assert annual_response.json()["activated_planets"] == direct_annual.activated_planets
    assert annual_response.json()["chronology"] is None
    annual_truth = annual_response.json()["activation_truth"]
    assert annual_truth["activation_orb_deg"] == 0.25
    assert annual_truth["status"] == direct_annual.activation_truth.status.value
    assert [item["body"] for item in annual_truth["body_truths"]] == [
        item.body for item in direct_annual.activation_truth.body_truths
    ]

    assert monthly_response.status_code == 200
    assert monthly_response.json()["profected_longitude"] == pytest.approx(direct_monthly[0])
    assert monthly_response.json()["sign"] == direct_monthly[1]
    assert monthly_response.json()["lord_of_month"] == direct_monthly[2]

    assert schedule_response.status_code == 200
    assert schedule_response.json()["age_basis"] == "civil_anniversary"
    assert schedule_response.json()["profected_house"] == direct_schedule.profected_house
    assert schedule_response.json()["lord_of_year"] == direct_schedule.lord_of_year
    schedule_truth = schedule_response.json()["activation_truth"]
    assert schedule_truth["activation_orb_deg"] == 0.25
    assert schedule_truth["status"] == direct_schedule.activation_truth.status.value
    assert schedule_response.json()["activated_planets"] == list(
        direct_schedule.activation_truth.activated_planets
    )
    chronology = schedule_response.json()["chronology"]
    assert chronology["civil_timezone"] == "America/New_York"
    assert chronology["timezone_data_source"] == "stdlib_zoneinfo"
    assert chronology["timezone_data_version"] is None
    assert chronology["method"] == "computational_projection"
    assert chronology["ambiguous_time_policy"] == "earlier_occurrence"
    assert chronology["ambiguous_time_resolution_applied"] is False
    assert chronology["interval_policy"] == (
        "equal_twelfths_of_civil_anniversary_year"
    )
    assert chronology["boundary_semantics"] == (
        "start_inclusive_end_exclusive"
    )
    assert len(chronology["intervals"]) == 12
    assert sum(item["active"] for item in chronology["intervals"]) == 1
    assert datetime.fromisoformat(
        chronology["intervals"][0]["start_utc"].replace("Z", "+00:00")
    ) == (
        direct_schedule.chronology.intervals[0].start_utc
    )
    assert datetime.fromisoformat(
        chronology["intervals"][-1]["end_utc"].replace("Z", "+00:00")
    ) == (
        direct_schedule.chronology.intervals[-1].end_utc
    )


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
    untrimmed_timezone = client_with_engine.post(
        "/v1/profections/schedule",
        json={
            "natal": natal,
            "current_dt": "2024-06-01T00:00:00Z",
            "civil_timezone": " America/New_York",
        },
    )

    assert negative_age.status_code == 422
    assert invalid_month.status_code == 422
    assert invalid_body.status_code == 422
    assert untrimmed_timezone.status_code == 422
