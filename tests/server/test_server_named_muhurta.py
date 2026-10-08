"""Strict admission and lossless HTTP projection of canonical named intervals."""
from datetime import date
import json

from fastapi.testclient import TestClient
import pytest

from moira import Moira, NamedMuhurtaPolicy
from moira.muhurta_search import MuhurtaCoverageError, MuhurtaResourceError
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.serializers.named_muhurta import serialize_named_muhurta, serialize_named_muhurta_day
from tests.named_muhurta_support import install_analytic_solar

pytestmark = pytest.mark.loopback


@pytest.fixture
def surface(monkeypatch):
    owner, reader, calls, state = install_analytic_solar(monkeypatch)
    class Engine:
        _reader = reader
        named_muhurta_for_date = Moira.named_muhurta_for_date
        named_muhurta_from_solar_times = Moira.named_muhurta_from_solar_times
    engine = Engine()
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as client:
        yield client, engine, owner, calls, state


def direct_payload():
    return {"sunrise_jd_ut1": 2451545., "sunset_jd_ut1": 2451545.6,
            "previous_sunset_jd_ut1": 2451544.6, "weekday": 2}


def day_payload():
    return {"local_date": "2026-10-08", "latitude": 20, "longitude": 80, "timezone": "Asia/Kolkata"}


@pytest.mark.parametrize("basis", ["arunadatta_fixed_ghati", "legacy_proportional_night_14"])
@pytest.mark.parametrize("rule", ["chintamani_wednesday_exclusion", "geometry_only"])
def test_supplied_anchor_route_is_lossless_and_never_touches_reader(surface, basis, rule):
    client, engine, _, calls, _ = surface
    body = direct_payload() | {"policy": {"brahma_basis": basis, "abhijit_weekday_rule": rule}}
    response = client.post("/v1/muhurta/named/direct", json=body)
    assert response.status_code == 200, response.text
    expected = engine.named_muhurta_from_solar_times(**direct_payload(), policy=NamedMuhurtaPolicy(**body["policy"]))
    assert response.json() == serialize_named_muhurta(expected).model_dump(mode="json")
    assert response.json()["solar_policy_applied"] is False and calls == []


@pytest.mark.parametrize("basis", ["arunadatta_fixed_ghati", "legacy_proportional_night_14"])
def test_date_route_uses_facade_reader_and_preserves_every_receipt(surface, basis):
    client, engine, _, calls, _ = surface
    body = day_payload() | {"policy": {"brahma_basis": basis}}
    response = client.post("/v1/muhurta/named/day", json=body)
    assert response.status_code == 200, response.text
    assert len([c for c in calls if c[0] == "solar"]) == 3
    expected = engine.named_muhurta_for_date(date(2026, 10, 8), 20, 80, timezone="Asia/Kolkata",
                                            policy=NamedMuhurtaPolicy(brahma_basis=basis))
    assert response.json() == serialize_named_muhurta_day(expected).model_dump(mode="json")
    assert response.json()["reader_binding"] == "caller_owned_reader"


@pytest.mark.parametrize("kind,bad", [
    ("direct", {"sunrise_jd_ut1": True}), ("direct", {"sunrise_jd_ut1": "2451545"}),
    ("direct", {"sunrise_jd_ut1": float("nan")}), ("direct", {"sunrise_jd_ut1": float("inf")}),
    ("direct", {"sunrise_jd_ut1": 10**400}), ("direct", {"sunset_jd_ut1": 2451545}),
    ("direct", {"weekday": True}), ("direct", {"weekday": 2.0}), ("direct", {"weekday": 7}),
    ("direct", {"previous_sunset_jd_ut1": 2451546}),
    ("direct", {"policy": {"brahma_basis": "all_traditions"}}),
    ("direct", {"policy": {"endpoint_convention": "closed"}}),
    ("direct", {"policy": {"solver_tolerance_seconds": True}}),
    ("direct", {"policy": {"solver_tolerance_seconds": .001}}),
    ("direct", {"unknown": 1}),
    ("day", {"local_date": "2026-10-08T00:00:00Z"}), ("day", {"local_date": 0}),
    ("day", {"local_date": "20261008"}), ("day", {"local_date": "0001-01-01"}),
    ("day", {"local_date": "2011-12-30", "timezone": "Pacific/Apia"}),
    ("day", {"timezone": "Mars/Olympus"}), ("day", {"timezone": True}),
    ("day", {"latitude": True}), ("day", {"latitude": "20"}), ("day", {"latitude": 90}),
    ("day", {"longitude": float("inf")}), ("day", {"policy": {"sunrise_definition": "custom"}}),
])
def test_hostile_requests_fail_before_astronomy_with_request_id(surface, kind, bad):
    client, _, _, calls, _ = surface
    body = (direct_payload() if kind == "direct" else day_payload()) | bad
    response = client.post("/v1/muhurta/named/"+kind, content=json.dumps(body),
                           headers={"Content-Type": "application/json"})
    assert response.status_code == 422, response.text
    error = response.json()
    assert error["error_code"] == "validation_error"
    assert error["request_id"] == response.headers["X-Request-ID"]
    assert calls == []


@pytest.mark.parametrize("flag,status", [("omit_rises", "unavailable"), ("omit_sets", "partial")])
def test_missing_events_are_typed_success_with_null_endpoints(surface, flag, status):
    client, _, _, _, state = surface
    setattr(state, flag, True)
    response = client.post("/v1/muhurta/named/day", json=day_payload())
    assert response.status_code == 200, response.text
    result = response.json()["result"]
    assert result["status"] == status
    absent = result["intervals"][0]
    assert absent["start"] is absent["end"] is absent["start_jd_ut1"] is None
    assert absent["unavailable_reasons"]


@pytest.mark.parametrize("exception,status,code", [
    (MuhurtaCoverageError("outside coverage"), 422, "muhurta_date_outside_coverage"),
    (MuhurtaResourceError("no kernel"), 503, "muhurta_resource_unavailable"),
])
def test_existing_resource_envelopes_are_preserved(surface, monkeypatch, exception, status, code):
    client, engine, _, _, _ = surface
    def fail(*args, **kwargs):
        raise exception
    monkeypatch.setattr(engine, "named_muhurta_for_date", fail)
    response = client.post("/v1/muhurta/named/day", json=day_payload())
    assert response.status_code == status, response.text
    assert response.json()["error_code"] == code
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


def test_openapi_names_profiles_and_canonical_responses(surface):
    client, _, _, _, _ = surface
    schema = client.get("/openapi.json").json()
    for suffix, model in (("direct", "NamedMuhurtaResponse"), ("day", "NamedMuhurtaDayResponse")):
        response = schema["paths"]["/v1/muhurta/named/"+suffix]["post"]["responses"]["200"]
        assert response["content"]["application/json"]["schema"]["$ref"].endswith("/"+model)
    policy = schema["components"]["schemas"]["NamedMuhurtaPolicyRequest"]["properties"]
    assert policy["brahma_basis"]["enum"] == ["arunadatta_fixed_ghati", "legacy_proportional_night_14"]
    assert policy["abhijit_weekday_rule"]["default"] == "chintamani_wednesday_exclusion"
