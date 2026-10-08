"""Typed HTTP, strict preflight and reader-bound canonical parity."""
from datetime import date
import json

from fastapi.testclient import TestClient
import pytest

from moira import Moira, SpecialMuhurtaPolicy
from moira.muhurta_search import MuhurtaCoverageError, MuhurtaResourceError
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.serializers.special_muhurta import (
    serialize_special_muhurta_solar, serialize_muhurta_yogas, serialize_special_muhurta_day,
)
from tests.special_muhurta_support import install_special_sky

pytestmark = pytest.mark.loopback


@pytest.fixture
def surface(monkeypatch):
    owner, reader, calls, state = install_special_sky(monkeypatch)
    class Engine:
        _reader = reader
        special_muhurta_for_date = Moira.special_muhurta_for_date
        special_muhurta_from_solar_times = Moira.special_muhurta_from_solar_times
        muhurta_yogas_from_longitudes = Moira.muhurta_yogas_from_longitudes
    engine = Engine()
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: engine)
    with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as client:
        yield client, engine, owner, calls, state


def payload(kind):
    return {
        "solar": {"weekday":3,"sunrise_jd_ut1":2451545.,"sunset_jd_ut1":2451545.5,
                  "half_set_jd_ut1":2451545.498,"upper_limb_sunset_jd_ut1":2451545.5},
        "yogas": {"weekday":3,"sun_sidereal_longitude":0,"moon_sidereal_longitude":100},
        "day": {"local_date":"2026-10-08","latitude":20,"longitude":80,"timezone":"Asia/Kolkata"},
    }[kind]


@pytest.mark.parametrize("kind", ["solar", "yogas"])
@pytest.mark.parametrize("alternate", [False,True])
def test_direct_routes_are_lossless_and_do_not_use_reader(surface,kind,alternate):
    client,engine,_,calls,_ = surface
    policy={"amrita_basis":"kalaprakasika_amirtha" if alternate else "sadhana_amrita_siddhi"}
    response=client.post("/v1/muhurta/special/"+kind,json=payload(kind)|{"policy":policy})
    assert response.status_code==200,response.text
    func,serialize=(engine.special_muhurta_from_solar_times,serialize_special_muhurta_solar) if kind=="solar" else (engine.muhurta_yogas_from_longitudes,serialize_muhurta_yogas)
    expected=func(**payload(kind),policy=SpecialMuhurtaPolicy(**policy))
    assert response.json()==serialize(expected).model_dump(mode="json") and calls==[]


@pytest.mark.parametrize("horizon",["standard_refraction_34_arcmin","geometric_disc"])
@pytest.mark.parametrize("amrita",["sadhana_amrita_siddhi","kalaprakasika_amirtha"])
def test_day_route_preserves_all_canonical_fields(surface,horizon,amrita):
    client,engine,_,_,_=surface
    policy={"godhuli_horizon":horizon,"amrita_basis":amrita}
    response=client.post("/v1/muhurta/special/day",json=payload("day")|{"policy":policy})
    assert response.status_code==200,response.text
    result=engine.special_muhurta_for_date(date(2026,10,8),20,80,timezone="Asia/Kolkata",policy=SpecialMuhurtaPolicy(**policy))
    assert response.json()==serialize_special_muhurta_day(result).model_dump(mode="json")
    assert response.json()["named"]["reader_binding"]=="caller_owned_reader"
    assert len(response.json()["results"])==5


@pytest.mark.parametrize("kind,bad",[
    ("solar",{"weekday":True}),("solar",{"weekday":1.0}),("solar",{"weekday":"1"}),
    ("solar",{"weekday":7}),("solar",{"sunrise_jd_ut1":True}),("solar",{"sunrise_jd_ut1":"2451545"}),
    ("solar",{"sunset_jd_ut1":2451544.}),("solar",{"half_set_jd_ut1":2451545.6}),
    ("solar",{"upper_limb_sunset_jd_ut1":float("nan")}),("solar",{"sunrise_jd_ut1":10**1000}),
    ("solar",{"policy":{"godhuli_weekday_rule":"none"}}),("solar",{"policy":{"godhuli_horizon":"sunset"}}),
    ("yogas",{"moon_sidereal_longitude":360}),("yogas",{"sun_sidereal_longitude":-1}),
    ("yogas",{"moon_sidereal_longitude":True}),("yogas",{"sun_sidereal_longitude":"10"}),
    ("yogas",{"moon_sidereal_longitude":float("inf")}),("yogas",{"unknown":1}),
    ("yogas",{"policy":{"amrita_basis":"amrita"}}),("yogas",{"policy":{"ayanamsa_system":"unknown"}}),
    ("yogas",{"policy":{"ayanamsa_system":True}}),("yogas",{"policy":{"solar_policy":{"solver_tolerance_seconds":True}}}),
    ("day",{"local_date":"20261008"}),("day",{"local_date":"2026-10-08T00:00:00Z"}),
    ("day",{"local_date":0}),("day",{"local_date":"0001-01-01"}),
    ("day",{"local_date":"2011-12-30","timezone":"Pacific/Apia"}),
    ("day",{"timezone":"Mars/Olympus"}),("day",{"latitude":90}),("day",{"longitude":"20"}),
    ("day",{"policy":{"solar_policy":{"sunrise_definition":"custom"}}}),
])
def test_bad_requests_reject_before_astronomy(surface,kind,bad):
    client,_,_,calls,_=surface
    response=client.post("/v1/muhurta/special/"+kind,content=json.dumps(payload(kind)|bad),headers={"Content-Type":"application/json"})
    assert response.status_code==422,response.text
    assert response.json()["error_code"]=="validation_error"
    assert response.json()["request_id"]==response.headers["X-Request-ID"] and calls==[]


@pytest.mark.parametrize("flag",["omit_rises","omit_sets"])
def test_missing_data_is_a_typed_success(surface,flag):
    client,_,_,_,state=surface
    setattr(state,flag,True)
    response=client.post("/v1/muhurta/special/day",json=payload("day"))
    assert response.status_code==200,response.text
    assert response.json()["status"]==("unavailable" if flag=="omit_rises" else "partial")
    assert all(not r["windows"] for r in response.json()["results"] if r["status"]=="unavailable")


@pytest.mark.parametrize("exc,status,code",[(MuhurtaCoverageError("coverage"),422,"muhurta_date_outside_coverage"),
    (MuhurtaResourceError("reader"),503,"muhurta_resource_unavailable")])
def test_resource_failure_envelopes(surface,monkeypatch,exc,status,code):
    client,engine,_,_,_=surface
    def fail(*args,**kwargs):
        raise exc
    monkeypatch.setattr(engine,"special_muhurta_for_date",fail)
    response=client.post("/v1/muhurta/special/day",json=payload("day"))
    assert response.status_code==status and response.json()["error_code"]==code
    assert response.json()["request_id"]==response.headers["X-Request-ID"]


def test_openapi_carries_named_policies_and_typed_results(surface):
    client,*_=surface
    schema=client.get("/openapi.json").json()
    for route in ("solar","yogas","day"):
        operation=schema["paths"]["/v1/muhurta/special/"+route]["post"]
        assert "$ref" in operation["responses"]["200"]["content"]["application/json"]["schema"]
    policy=schema["components"]["schemas"]["SpecialMuhurtaPolicyRequest"]
    assert policy["additionalProperties"] is False
    assert policy["properties"]["amrita_basis"]["enum"]==["sadhana_amrita_siddhi","kalaprakasika_amirtha"]
