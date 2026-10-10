"""Typed loopback parity and preflight; synthetic sunrise/position inputs."""
import json
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from moira import Moira
from moira.avasthas import AvasthaPolicy
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.sayanadi import SayanadiResponse
from moira_server.serializers.avasthas import serialize_avastha_birth, serialize_avastha_chart
from sayanadi_support import install_analytic_birth

pytestmark = pytest.mark.loopback
SEVEN = {p: 37.2 for p in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")}


def context():
    return {"clock": {"kind": "ordinal", "ordinal": 31}, "name": {"sound": "स"}}


def standalone():
    return {"planet": "Sun", "sidereal_longitudes": {"Sun": 37.2, "Moon": 37.2},
            "lagna_sidereal_lon": 225, "context": context()}


def birth_payload():
    return {"birth": "2000-01-02T12:00:00Z", "latitude": 0, "longitude": 0, "name": {"sound": "स"}}


@pytest.fixture
def surface(monkeypatch):
    dated, reader, calls = install_analytic_birth(monkeypatch)
    class Engine:
        _reader = reader
        avasthas_for_datetime = Moira.avasthas_for_datetime
        evaluate_avasthas = Moira.evaluate_avasthas
        sayanadi_avastha = Moira.sayanadi_avastha
    engine = Engine()
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    app = create_app(ServerConfig(docs_enabled=True, prewarm_enabled=False))
    with TestClient(app) as client:
        yield client, engine, dated, calls


def test_standalone_is_canonical_engine_trace_and_source_parity(surface):
    client, engine, _, _ = surface
    body = standalone()
    response = client.post("/v1/avasthas/sayanadi", json=body)
    assert response.status_code == 200, response.text
    from moira_server.models.sayanadi import SayanadiRequest
    model = SayanadiRequest(**body)
    expected = engine.sayanadi_avastha(body["planet"], body["sidereal_longitudes"], 225,
                                       context=model.context.to_engine())
    assert response.json() == SayanadiResponse.model_validate(expected).model_dump(mode="json")
    data = response.json()
    assert (data["trace"]["total"], data["trace"]["stage1_remainder"], data["trace"]["stage2_remainder"]) == (51, 1, 0)
    assert data["effect_provenance"]["conditions_evaluated"] is False


@pytest.mark.parametrize("clock,ordinal", [
    ({"kind": "ordinal", "ordinal": 31}, 31),
    ({"kind": "ghati_vighati", "whole_ghatis": 30, "vighatis": 33}, 31),
    ({"kind": "elapsed_seconds", "elapsed_seconds": 61200}, 43),
    ({"kind": "elapsed_seconds", "elapsed_seconds": 86401}, 61),
])
def test_direct_clock_forms_and_source_rounding_survive_json(surface, clock, ordinal):
    client, _, _, _ = surface
    body = standalone()
    body["context"]["clock"] = clock
    r = client.post("/v1/avasthas/sayanadi", json=body)
    assert r.status_code == 200, r.text
    assert r.json()["trace"]["context"]["ghati"]["ordinal"] == ordinal


@pytest.mark.parametrize("body", ["Rahu", "Ketu", "Moon"])
def test_source_defined_node_subjects_do_not_require_a_chart_pair(surface, body):
    client, _, _, _ = surface
    request = standalone()
    request["planet"] = body
    request["sidereal_longitudes"] = {"Moon": 37.2, body: 50}
    assert client.post("/v1/avasthas/sayanadi", json=request).status_code == 200


def test_existing_chart_omission_and_evaluated_node_pair(surface):
    client, engine, _, _ = surface
    body = {"sidereal_longitudes": SEVEN, "lagna_sidereal_lon": 225}
    omitted = client.post("/v1/avasthas/evaluate", json=body)
    assert omitted.status_code == 200 and omitted.json()["sayanadi_status"] == "omitted"
    assert all(pa["sayanadi"] is None for pa in omitted.json()["planets"].values())
    body["sayanadi_context"] = context() | {"evaluate_nodes": True}
    assert client.post("/v1/avasthas/evaluate", json=body).status_code == 422
    body["node_longitudes"] = {"Rahu": 20, "Ketu": 200}
    r = client.post("/v1/avasthas/evaluate", json=body)
    assert r.status_code == 200, r.text
    from moira_server.models.sayanadi import SayanadiContextRequest
    expected = engine.evaluate_avasthas(SEVEN, 225, AvasthaPolicy(), body["node_longitudes"],
                                       SayanadiContextRequest(**body["sayanadi_context"]).to_engine())
    assert r.json() == serialize_avastha_chart(expected).model_dump(mode="json")
    assert set(r.json()["sayanadi_nodes"]) == {"Rahu", "Ketu"}


@pytest.mark.parametrize("path,bad", [
    (("planet",), "Pluto"), (("sidereal_longitudes", "Sun"), True),
    (("sidereal_longitudes", "Moon"), "37.2"), (("lagna_sidereal_lon",), "225"),
    (("lagna_sidereal_lon",), float("inf")), (("sidereal_longitudes",), {"Sun": 37.2}),
    (("sidereal_longitudes",), {"Sun": 37.2, "Moon": 37.2, "Pluto": 0}),
    (("sidereal_longitudes",), {"Sun": 37.2, "Moon": 37.2, "sun": 0}),
    (("context", "clock", "ordinal"), True), (("context", "clock", "ordinal"), 31.0),
    (("context", "clock", "ordinal"), "31"), (("context", "clock", "ordinal"), 0),
    (("context", "clock", "ordinal"), -1), (("context", "clock", "kind"), "hours_since_midnight"),
    (("context", "clock"), {"kind": "elapsed_seconds", "elapsed_seconds": True}),
    (("context", "clock"), {"kind": "elapsed_seconds", "elapsed_seconds": -1}),
    (("context", "clock"), {"kind": "elapsed_seconds", "elapsed_seconds": float("nan")}),
    (("context", "clock"), {"kind": "ordinal", "ordinal": 31, "elapsed_seconds": 30}),
    (("context", "clock"), {"kind": "ghati_vighati", "whole_ghatis": 30, "vighatis": 60}),
    (("context", "name"), {"value": 4, "sound": "स"}),
    (("context", "name"), {"value": True}), (("context", "name"), {"value": 4.0}),
    (("context", "name"), {"value": 0}), (("context", "name"), {"value": 6}),
    (("context", "name"), {}), (("context", "name"), {"sound": "Sa"}),
    (("context", "name"), {"sound": "शा"}), (("context", "policy"), {"formulation": "degree_based"}),
    (("context", "policy"), {"source_profile": "invented"}), (("context", "evaluate_nodes"), 1),
    (("context", "evaluate_nodes"), True), (("context",), {}), (("context",), None),
])
def test_standalone_hostile_preflight(surface, path, bad):
    client, _, _, calls = surface
    request = standalone()
    target = request
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = bad
    r = client.post("/v1/avasthas/sayanadi", content=json.dumps(request), headers={"Content-Type": "application/json"})
    assert r.status_code == 422, r.text
    assert r.json()["error_code"] == "validation_error"
    assert calls == []


def test_birth_http_is_lossless_and_reader_bound(surface):
    client, engine, _, calls = surface
    request = birth_payload() | {"policy": {"evaluate_nodes": True}}
    r = client.post("/v1/avasthas/from-datetime", json=request)
    assert r.status_code == 200, r.text
    from moira_server.models.sayanadi import AvasthaBirthRequest
    model = AvasthaBirthRequest(**request)
    expected = engine.avasthas_for_datetime(model.birth, 0, 0, name=model.name.to_engine(), policy=model.policy.to_engine())
    assert r.json() == serialize_avastha_birth(expected).model_dump(mode="json")
    assert r.json()["policy"]["evaluate_nodes"] is True
    assert r.json()["policy"]["lajjitadi_nodes"] is False
    assert r.json()["reader_binding"] == "caller_owned_reader"
    assert len([c for c in calls if c[0] == "epoch"]) == 2


@pytest.mark.parametrize("patch", [
    {"birth": 123456}, {"birth": "123456"}, {"birth": True}, {"birth": "2000-01-02T12:00:00"},
    {"latitude": True}, {"latitude": 90}, {"longitude": 181}, {"longitude": "0"},
    {"name": {"sound": "Sa"}}, {"clock": {"ordinal": 31}}, {"timezone_name": "not/a/zone"},
    {"policy": {"ayanamsa_system": "unknown"}}, {"policy": {"node_mode": "mean"}},
    {"policy": {"evaluate_nodes": "true"}}, {"policy": {"solver_tolerance_seconds": 0}},
    {"policy": {"sayanadi": {"formulation": "degree_based"}}},
    {"avastha_policy": {"deeptadi_source": "mixed"}},
])
def test_birth_preflight_never_calls_astronomy(surface, patch):
    client, _, _, calls = surface
    r = client.post("/v1/avasthas/from-datetime", json=birth_payload() | patch)
    assert r.status_code == 422, r.text
    assert r.json()["error_code"] == "validation_error" and calls == []


def test_birth_unavailable_is_typed_with_no_fabricated_chart(surface, monkeypatch):
    client, _, dated, _ = surface
    monkeypatch.setattr(dated, "_solar_date", lambda *a: SimpleNamespace(sunrises=()))
    r = client.post("/v1/avasthas/from-datetime", json=birth_payload())
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "unavailable" and r.json()["unavailable_reasons"]
    assert r.json()["chart"] is None and r.json()["epoch"] is None


@pytest.mark.parametrize("error,status,code", [
    ("resource", 503, "sayanadi_resource_unavailable"),
    ("coverage", 422, "sayanadi_date_outside_coverage"),
])
def test_resources_and_coverage_keep_distinct_error_envelopes(surface, monkeypatch, error, status, code):
    client, _, dated, _ = surface
    def fail(*args):
        if error == "coverage":
            raise dated.OutOfRangeError("synthetic coverage failure", [])
        raise dated.GocharaResourceError("synthetic reader identity unavailable")
    monkeypatch.setattr(dated, "_epoch", fail)
    r = client.post("/v1/avasthas/from-datetime", json=birth_payload())
    assert r.status_code == status, r.text
    assert r.json()["error_code"] == code and r.json()["request_id"]


def test_openapi_has_discriminated_clocks_nullable_trace_and_birth_status(surface):
    client, _, _, _ = surface
    schemas = client.app.openapi()["components"]["schemas"]
    assert schemas["SayanadiContextRequest"]["properties"]["clock"]["discriminator"]["propertyName"] == "kind"
    assert "anyOf" in schemas["SayanadiResponse"]["properties"]["trace"]
    assert schemas["AvasthaBirthResponse"]["properties"]["status"]["enum"] == ["evaluated", "unavailable"]
    assert set(schemas["AvasthaChartResponse"]["properties"]) >= {"sayanadi_context", "sayanadi_status", "sayanadi_nodes"}
