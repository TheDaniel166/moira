"""Strict daily requests, canonical HTTP fidelity and actual reader binding."""
from datetime import date
import json
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from moira.daily_panchanga import (
    DailyPanchangaPolicy, DailyPanchangaResult, DailyPanchangaProvenance,
    PanchangaMoment, PanchangaSolarDate, PanchangaSunriseDefinition,
)
from moira.julian import datetime_from_jd
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.daily_panchanga import DailyPanchangaRequest
from moira_server.services.daily_panchanga import compute_daily_panchanga
from moira_server.serializers.daily_panchanga import serialize_daily_panchanga

pytestmark = pytest.mark.loopback
PAYLOAD = {"local_date": "2026-09-22", "timezone": "UTC+05:30",
           "latitude": 23 + 11 / 60, "longitude": 82.5}


@pytest.fixture(scope="module")
def client():
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("moira_server.app.create_engine", lambda config: object())
        with TestClient(create_app(ServerConfig(docs_enabled=True, prewarm_enabled=False))) as value:
            yield value


@pytest.fixture(scope="module")
def real_client(moira_engine):
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
        with TestClient(create_app(ServerConfig(docs_enabled=False, prewarm_enabled=False))) as value:
            yield value


@pytest.mark.parametrize("field,value", [
    ("latitude", True), ("latitude", "23"), ("latitude", "NaN"),
    ("latitude", 91), ("latitude", None), ("longitude", False),
    ("longitude", "82.5"), ("longitude", 181),
    ("local_date", 0), ("local_date", True), ("local_date", "2026-09-22T00:00:00Z"),
    ("local_date", "2026-9-22"), ("local_date", "2026-02-30"),
    ("timezone", True), ("timezone", ""), ("timezone", "a" * 129),
])
def test_hostile_inputs_fail_without_engine_computation(client, field, value):
    response = client.post("/v1/panchanga/day", json={**PAYLOAD, field: value})
    assert response.status_code == 422, response.text
    body = response.json()
    assert body["error_code"] == "validation_error" and body["category"] == "input_validation"
    assert response.headers["X-Request-ID"] == body["request_id"]


@pytest.mark.parametrize("policy", [
    {"solver_tolerance_seconds": True}, {"solver_tolerance_seconds": "0.1"},
    {"solver_tolerance_seconds": 0}, {"solver_tolerance_seconds": 2},
    {"ayanamsa_system": "fictional"}, {"sunrise_definition": "hindu"},
    {"sunrise_definition": False}, {"terrain_altitude": 1},
])
def test_unsupported_or_coerced_policy_is_rejected(client, policy):
    response = client.post("/v1/panchanga/day", json={**PAYLOAD, "policy": policy})
    assert response.status_code == 422, response.text


def test_extra_fields_and_missing_location_are_rejected(client):
    for body in ({**PAYLOAD, "observer_elev_m": 1000},
                 {key: value for key, value in PAYLOAD.items() if key != "longitude"}):
        assert client.post("/v1/panchanga/day", json=body).status_code == 422


def test_openapi_exposes_bounded_daily_product(client):
    schema = client.get("/openapi.json").json()
    operation = schema["paths"]["/v1/panchanga/day"]["post"]
    assert operation["tags"] == ["panchanga"]
    request = schema["components"]["schemas"]["DailyPanchangaRequest"]
    assert request["additionalProperties"] is False
    assert request["properties"]["latitude"]["minimum"] == -90
    assert request["properties"]["local_date"]["format"] == "date"
    assert "200" in operation["responses"]


def test_service_delegates_selected_policy_and_preserves_unavailable_truth():
    clock = datetime_from_jd(2451545)
    moment = PanchangaMoment(2451545, clock, clock)
    solar = PanchangaSolarDate(date(2000, 1, 1), moment, moment, (), ())
    following = PanchangaSolarDate(date(2000, 1, 2), moment, moment, (), ())
    policy = DailyPanchangaPolicy()
    result = DailyPanchangaResult(date(2000, 1, 1), "UTC", 90, 0, policy,
        DailyPanchangaProvenance("caller_owned_reader"), "unavailable",
        ("sunrise_absent", "next_sunrise_absent"), solar, following, None, ())
    def compute(day, lat, lon, *, timezone, policy):
        assert (day, lat, lon, timezone) == (date(2000, 1, 1), 90, 0, "UTC")
        assert policy == result.policy
        return result
    request = DailyPanchangaRequest(local_date=date(2000, 1, 1), timezone="UTC", latitude=90, longitude=0)
    assert compute_daily_panchanga(SimpleNamespace(daily_panchanga=compute), request) is result
    response = serialize_daily_panchanga(result).model_dump(mode="json")
    assert response["status"] == "unavailable" and response["limbs"] == []
    assert response["at_sunrise"] is None
    assert response["unavailable_reasons"] == ["sunrise_absent", "next_sunrise_absent"]


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("definition", list(PanchangaSunriseDefinition))
def test_http_preserves_complete_canonical_result_for_each_sunrise_policy(real_client, moira_engine, definition):
    body = {**PAYLOAD, "policy": {"sunrise_definition": definition.value}}
    direct = moira_engine.daily_panchanga(date(2026, 9, 22), PAYLOAD["latitude"], PAYLOAD["longitude"],
        timezone=PAYLOAD["timezone"], policy=DailyPanchangaPolicy(sunrise_definition=definition))
    response = real_client.post("/v1/panchanga/day", json=body)
    assert response.status_code == 200, response.text
    assert response.json() == serialize_daily_panchanga(direct).model_dump(mode="json")
    value = response.json()
    assert value["provenance"]["reader_binding"] == "caller_owned_reader"
    assert value["policy"]["sunrise_definition"] == definition.value
    assert value["at_sunrise"]["vara_lord"] == "Mars"


@pytest.mark.requires_ephemeris
def test_default_policy_matches_explicit_policy_and_polar_http_is_unavailable(real_client):
    default = real_client.post("/v1/panchanga/day", json=PAYLOAD)
    explicit = real_client.post("/v1/panchanga/day", json={**PAYLOAD, "policy": {}})
    assert default.status_code == explicit.status_code == 200
    assert default.json() == explicit.json()
    polar = real_client.post("/v1/panchanga/day", json={**PAYLOAD, "local_date": "2026-06-21",
                                                      "latitude": 89, "longitude": 0, "timezone": "UTC"})
    assert polar.status_code == 200
    assert polar.json()["status"] == "unavailable" and polar.json()["at_sunrise"] is None


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("zone", ["Missing/Zone", "UTC+24:00"])
def test_runtime_timezone_validation_has_standard_error_envelope(real_client, zone):
    response = real_client.post("/v1/panchanga/day", json={**PAYLOAD, "timezone": zone})
    assert response.status_code == 422
    assert response.json()["error_code"] == "validation_error"


def test_nonstandard_nan_json_is_rejected_before_engine(client):
    payload = dict(PAYLOAD, latitude=float("nan"))
    response = client.post("/v1/panchanga/day", content=json.dumps(payload),
                           headers={"content-type": "application/json"})
    assert response.status_code == 422
