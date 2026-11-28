"""Catalogue admission, strict request and reader-bound HTTP equivalence."""

from datetime import date

import pytest
from fastapi.testclient import TestClient

from moira import ObservanceFastingContext, observance_catalogue
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.observances import ObservanceResponse

pytestmark = pytest.mark.loopback
CATALOGUE = "/v1/panchanga/observances/catalogue"
EVALUATE = "/v1/panchanga/observances/evaluate"
BODY = {
    "rule_id": observance_catalogue()[0].rule_id,
    "local_date": "2025-02-26",
    "timezone": "America/New_York",
    "latitude": 40.752,
    "longitude": -73.816,
}


@pytest.fixture(scope="module")
def client():
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("moira_server.app.create_engine", lambda config: object())
        with TestClient(create_app(ServerConfig(docs_enabled=True, prewarm_enabled=False))) as value:
            yield value


def test_catalogue_openapi_and_distinct_admission_states(client):
    response = client.get(CATALOGUE)
    assert response.status_code == 200
    assert len(response.json()) == 1
    profile = response.json()[0]
    assert profile["rule_id"] == BODY["rule_id"]
    assert profile["date_admission"] == "ordinary_month_admitted"
    assert profile["fasting_admission"] == "conditional_ordinary_parana_admitted"
    assert profile["vow_start_rule"] == "selected_morning_after_daily_rites"
    assert profile["vow_source_url"].endswith("/kotirudra/38")
    schema = client.get("/openapi.json").json()
    assert schema["paths"][CATALOGUE]["get"]["tags"] == ["panchanga"]
    assert schema["paths"][EVALUATE]["post"]["tags"] == ["panchanga"]
    request = schema["components"]["schemas"]["ObservanceRequest"]
    assert request["additionalProperties"] is False
    assert request["properties"]["rule_id"]["const"] == BODY["rule_id"]
    statuses = schema["components"]["schemas"]["ObservanceDateResponse"]["properties"]["status"]["enum"]
    assert set(statuses) == {
        "selected", "not_applicable", "ambiguous", "unavailable", "excluded_by_profile", "unsupported_rule",
    }


@pytest.mark.parametrize("override", [
    {"rule_id": "unknown"}, {"local_date": "2025-02-26T00:00:00"}, {"local_date": 20250226},
    {"lat": 40}, {"latitude": "40.75"}, {"latitude": True}, {"longitude": 181},
    {"timezone": ""}, {"policy": {}},
    {"fasting_context": {}}, {"fasting_context": {"darsha_shraddha_applies": "false"}},
    {"fasting_context": {"darsha_shraddha_applies": False, "ready_for_parana_jd_ut1": True}},
])
def test_rejects_malformed_requests_before_calling_engine(client, override):
    response = client.post(EVALUATE, json={**BODY, **override})
    assert response.status_code == 422, response.text
    assert response.json()["error_code"] == "validation_error"


@pytest.mark.parametrize("override", [
    {},
    {"local_date": "1983-02-11", "latitude": 14.165, "longitude": 77.811, "timezone": "UTC+05:30"},
    {"local_date": "2011-12-30", "latitude": -13.83, "longitude": -171.75, "timezone": "Pacific/Apia"},
    {"local_date": "2026-02-15", "latitude": 13.4167, "longitude": 75.25, "timezone": "UTC+05:30",
     "fasting_context": {"darsha_shraddha_applies": True}},
])
def test_http_keeps_same_status_and_evidence_as_python(moira_engine, monkeypatch, override):
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    body = {**BODY, **override}
    args = {**body, "local_date": date.fromisoformat(body["local_date"])}
    if "fasting_context" in body:
        args["fasting_context"] = ObservanceFastingContext(**body["fasting_context"])
    direct = moira_engine.evaluate_observance(**args)
    expected = ObservanceResponse.model_validate(direct, from_attributes=True).model_dump(mode="json")
    with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as client:
        response = client.post(EVALUATE, json=body)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload == expected
    if body["local_date"] == "2026-02-15":
        assert payload["vow"]["timing"] == "selected_morning_after_daily_rites"
        assert payload["vow"]["sunrise_tithi"] == "before_caturdashi"
    elif body["local_date"] == "1983-02-11":
        assert payload["vow"]["status"] == "unsupported_rule"
        assert payload["date_result"]["paired_magha"]["elongation_342_crossing"]
