"""Strict input, complete typed evidence and reader-bound HTTP parity."""
from types import SimpleNamespace
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
import pytest

from moira.lunar_month import LunarMonthPolicy, LunarMonthSystem
from moira import MissingEphemerisKernelError
from moira.julian import jd_from_datetime, utc_to_ut1
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.lunar_month import LunarMonthRequest
from moira_server.services.lunar_month import compute_lunar_month
from moira_server.serializers.lunar_month import serialize_lunar_month

pytestmark = pytest.mark.loopback
PATH = "/v1/panchanga/lunar-month"


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
        with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as value:
            yield value


@pytest.mark.parametrize("body", [
    {}, {"jd_ut1": True}, {"jd_ut1": "2461305.5"}, {"jd_ut1": "NaN"},
    {"jd_ut1": None}, {"jd_ut1": 10_000_001}, {"jd_ut1": -10_000_001},
    {"jd_ut1": 2461305.5, "month": "Vaisakha"},
    *[{"jd_ut1": 2461305.5, "policy": p} for p in (
        {"system": "hindu"}, {"system": True}, {"ayanamsa_system": "fictional"},
        {"ayanamsa_system": True}, {"solver_tolerance_seconds": True},
        {"solver_tolerance_seconds": "0.1"}, {"solver_tolerance_seconds": 0},
        {"solver_tolerance_seconds": 2}, {"festival": "Diwali"},
    )],
])
def test_invalid_or_unsupported_policy_fails_before_compute(client, body):
    response = client.post(PATH, json=body)
    assert response.status_code == 422, response.text
    assert response.json()["error_code"] == "validation_error"


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_nonstandard_nonfinite_json_rejected(client, value):
    response = client.post(PATH, content='{"jd_ut1":'+value+'}',
                           headers={"Content-Type": "application/json"})
    assert response.status_code == 422


def test_openapi_exposes_scope_and_named_policy(client):
    schema = client.get("/openapi.json").json()
    assert schema["paths"][PATH]["post"]["tags"] == ["panchanga"]
    request = schema["components"]["schemas"]["LunarMonthRequest"]
    assert request["additionalProperties"] is False
    assert request["properties"]["jd_ut1"]["maximum"] == 10_000_000
    statuses = schema["components"]["schemas"]["LunarMonthResponse"]["properties"]["status"]["enum"]
    assert "unsupported_intercalation" in statuses and "boundary_ambiguous" in statuses


def test_service_is_exact_public_facade_delegation():
    result = object()
    def call(jd, *, policy):
        assert jd == 2461305 and policy == LunarMonthPolicy(system=LunarMonthSystem.PURNIMANTA)
        return result
    req = LunarMonthRequest(jd_ut1=2461305, policy={"system": "purnimanta"})
    assert compute_lunar_month(SimpleNamespace(lunar_month_at=call), req) is result


def test_missing_resource_remains_http_503_not_domain_unavailability(monkeypatch):
    def fail(jd, *, policy):
        raise MissingEphemerisKernelError("required planetary kernel unavailable")
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: SimpleNamespace(lunar_month_at=fail))
    with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as http:
        response = http.post(PATH, json={"jd_ut1": 2461305.5})
    assert response.status_code == 503
    body = response.json()
    assert body["error_code"] == "kernel_not_ready" and body["category"] == "kernel_readiness"
    assert response.headers["X-Request-ID"] == body["request_id"]


@pytest.mark.requires_ephemeris
@pytest.mark.parametrize("jd,system", [
    (2461305.5, LunarMonthSystem.AMANTA),
    (2461305.5, LunarMonthSystem.PURNIMANTA),
    (2461180.5, LunarMonthSystem.PURNIMANTA),
])
def test_http_preserves_all_canonical_available_and_unavailable_evidence(real_client, moira_engine, jd, system):
    direct = moira_engine.lunar_month_at(jd, policy=LunarMonthPolicy(system=system))
    response = real_client.post(PATH, json={"jd_ut1": jd, "policy": {"system": system.value}})
    assert response.status_code == 200, response.text
    assert response.json() == serialize_lunar_month(direct).model_dump(mode="json")
    value = response.json()
    assert value["provenance"]["reader_binding"] == "caller_owned_reader"
    for key in ("previous_lunation", "amanta_lunation", "next_lunation"):
        assert "lower_jd_ut1" in value[key]["start"]
        assert "uncertain_ingresses" in value[key]
    if direct.status != "available":
        assert value["label"] is None and value["unavailable_reasons"]


@pytest.mark.requires_ephemeris
def test_http_mithuna_ingress_passes_original_pac_minute_gate(real_client):
    # PAC 1948 SE printed 158 / PDF 178: 15 June 2026, 12:53 IST.
    # This failed by 64.4768 seconds before the shared precession correction.
    ist = timezone(timedelta(hours=5, minutes=30))
    jd = utc_to_ut1(jd_from_datetime(datetime(2026, 6, 15, 12, 53, tzinfo=ist)))
    response = real_client.post(PATH, json={"jd_ut1": jd})
    assert response.status_code == 200, response.text
    value = response.json()
    assert value["policy"]["ayanamsa_system"] == "Lahiri"
    assert value["provenance"]["sidereal_mode"] == "true"
    event, = [event for key in ("previous_lunation", "amanta_lunation", "next_lunation")
        for event in value[key]["ingresses"]
        if event["target_degrees"] == 60 and abs(event["upper_jd_ut1"]-jd) < 0.5]
    assert abs(event["upper_jd_ut1"]-jd)*86400 <= 60
    assert (event["upper_jd_ut1"]-event["lower_jd_ut1"])*86400 <= 0.1
