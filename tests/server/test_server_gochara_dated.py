"""Loopback transport exercises the actual dated compositor with analytic astronomy."""
from datetime import datetime
import importlib
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from moira import Moira
from moira.gochara import GOCHARA_PLANETS
from moira.spk_reader import get_active_reader
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.serializers.gochara import serialize_gochara_date
from moira_server.models.gochara_dated import GocharaDateResponse

dated = importlib.import_module("moira.gochara_dated")
pytestmark = pytest.mark.loopback


@pytest.fixture
def surface(monkeypatch):
    reader, calls = object(), []
    class Engine:
        _reader = reader
        gochara_at = Moira.gochara_at
        gochara_for_datetimes = Moira.gochara_for_datetimes
    engine = Engine()
    identity = SimpleNamespace(summary_label="DE-0441LE-0441", planetary_ephemeris="DE441",
        lunar_ephemeris="LE441", lunar_tidal_acceleration_arcsec_per_cy2=-25.936)
    def clock(jd, bound):
        assert bound is reader and get_active_reader() is reader
        return SimpleNamespace(epoch_tt=jd+70/86400, epoch_tdb=jd+70/86400,
            delta_t_seconds=70, delta_t_correction_seconds=0, tdb_minus_tt_seconds=0,
            raw_delta_t=SimpleNamespace(source_product="analytic_clock"), identity=identity)
    def planet(body, jd, **kw):
        assert kw["reader"] is reader and get_active_reader() is reader
        calls.append((body, jd))
        return SimpleNamespace(longitude=(GOCHARA_PLANETS.index(body)*40+jd*0.01) % 360)
    monkeypatch.setattr(dated, "_bind_ephemeris_time", clock)
    monkeypatch.setattr(dated, "_ayanamsa_at_tt", lambda *args: 25)
    monkeypatch.setattr(dated, "planet_at", planet)
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    app = create_app(ServerConfig(docs_enabled=True, prewarm_enabled=False))
    with TestClient(app) as client:
        yield client, engine, calls


def payload():
    return {"natal_jd_ut1": 2447892.5, "transit_jd_ut1": 2461319.5,
        "birth_location": {"latitude": 28.6139, "longitude": 77.209},
        "policy": {"natal_bav_mode": "compute_raw", "gochara_policy": {"bav_mode": "require_all_raw"}}}


def test_dated_route_is_lossless_facade_parity(surface):
    client, engine, calls = surface
    body = payload()
    response = client.post("/v1/gochara/from-epochs", json=body)
    assert response.status_code == 200, response.text
    assert len(calls) == 14
    expected = engine.gochara_at(body["natal_jd_ut1"], body["transit_jd_ut1"],
        birth_location=dated.GocharaBirthLocation(**body["birth_location"]),
        policy=dated.GocharaDatePolicy(natal_bav_mode=dated.GocharaNatalBavMode.COMPUTE_RAW,
            gochara_policy=dated.GocharaPolicy(bav_mode=dated.GocharaBavMode.REQUIRE_ALL_RAW)))
    assert response.json() == serialize_gochara_date(expected).model_dump(mode="json")
    data = response.json()
    assert len(data["natal_sign_indices"]) == 8
    assert data["profile"]["snapshot"]["missing_planets"] == []
    assert data["bav_source"] and data["policy"]["longitude_frame"] == "true_ecliptic_of_date"


def test_datetime_route_normalizes_offsets_and_agrees_with_engine(surface):
    client, engine, _ = surface
    body = {"natal_dt": "1990-01-01T05:30:00+05:30", "transit_dt": "2026-10-06T00:00:00Z"}
    result = client.post("/v1/gochara/from-datetimes", json=body)
    assert result.status_code == 200, result.text
    expected = engine.gochara_for_datetimes(datetime.fromisoformat(body["natal_dt"]),
                                           datetime.fromisoformat(body["transit_dt"].replace("Z", "+00:00")))
    assert result.json() == serialize_gochara_date(expected).model_dump(mode="json")
    body["natal_dt"] = "1990-01-01T00:00:00Z"
    assert result.json() == client.post("/v1/gochara/from-datetimes", json=body).json()


@pytest.mark.parametrize("patch", [
    {"natal_jd_ut1": True}, {"natal_jd_ut1": "2447892.5"}, {"transit_jd_ut1": 10_000_001},
    {"transit_jd_ut1": "Infinity"}, {"transit_jd_ut1": None}, {"raw_bav": {}},
    {"transit_sidereal_longitudes": {"Sun": 0}}, {"nodes": True},
    {"birth_location": {"latitude": 90, "longitude": 0}},
    {"birth_location": {"latitude": "28", "longitude": 0}},
    {"birth_location": {"latitude": 28}}, {"birth_location": None},
    {"policy": {"ayanamsa_system": "unknown"}},
    {"policy": {"ayanamsa_mode": "mean"}},
    {"policy": {"natal_bav_mode": "shodhana"}},
    {"policy": {"natal_bav_mode": "compute_raw", "gochara_policy": {"bav_mode": "omit"}}},
])
def test_bad_inputs_never_reach_astronomy(surface, patch):
    client, _, calls = surface
    response = client.post("/v1/gochara/from-epochs", json=payload() | patch)
    assert response.status_code == 422, response.text
    assert response.json()["error_code"] == "validation_error"
    assert calls == []


@pytest.mark.parametrize("instant", ["1990-01-01", "1990-01-01T00:00:00", 631152000, True, None])
def test_datetime_route_rejects_ambiguous_and_numeric_instants(surface, instant):
    client, _, calls = surface
    response = client.post("/v1/gochara/from-datetimes", json={
        "natal_dt": instant, "transit_dt": "2026-10-06T00:00:00Z"})
    assert response.status_code == 422 and calls == []


@pytest.mark.parametrize("error,status,code", [
    (dated.GocharaResourceError("required natal resource unavailable"), 503, "gochara_resource_unavailable"),
    (dated.GocharaCoverageError("transit epoch outside coverage"), 422, "gochara_date_outside_coverage"),
])
def test_resource_outcomes_have_specific_error_envelopes(surface, monkeypatch, error, status, code):
    client, engine, _ = surface
    monkeypatch.setattr(engine, "gochara_at", lambda *a, **kw: (_ for _ in ()).throw(error))
    response = client.post("/v1/gochara/from-epochs", json=payload())
    assert response.status_code == status
    assert response.json()["error_code"] == code and response.json()["request_id"]


def test_contracts_are_discoverable_and_models_curated(surface):
    import moira_server.models as public
    client, _, _ = surface
    assert public.GocharaDateResponse is GocharaDateResponse
    schema = client.get("/openapi.json").json()
    for route in ("/from-epochs", "/from-datetimes"):
        operation = schema["paths"]["/v1/gochara"+route]["post"]
        assert operation["tags"] == ["gochara"]
        assert operation["responses"]["503"]["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorEnvelope")
    assert schema["components"]["schemas"]["GocharaDatePolicyRequest"]["properties"]["ayanamsa_system"]["enum"] == dated.Ayanamsa.ALL
    for name in ("GocharaDatePolicyRequest", "GocharaEpochRequest", "GocharaDatetimeRequest",
                 "GocharaBirthLocationRequest", "GocharaDateResponse", "GocharaEpochResponse"):
        assert schema["components"]["schemas"][name]["additionalProperties"] is False
    routes = client.get("/v1/meta/routes?tag=gochara").json()
    assert routes["count"] == 5
    assert all(route["family"] == "classical-vedic" for route in routes["routes"])
    catalogue = client.get("/v1/gochara/doctrine-options?topic=astronomy").json()["options"]
    assert {o["id"] for o in catalogue} == {"astronomy.caller_sidereal", "astronomy.reader_epochs"}
