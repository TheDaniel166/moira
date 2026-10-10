"""Typed Muhurta policy and sampled-search transport with real DE441 parity."""
from fastapi.testclient import TestClient
import pytest

from moira.muhurta import MuhurtaPolicy, personal_muhurta_score
from moira.muhurta_search import MuhurtaSearchPolicy, MuhurtaResourceError
from moira.panchanga import panchanga_at, PanchangaPolicy
from moira.sidereal import tropical_to_sidereal
from moira_server.app import create_app
from moira_server.config import ServerConfig

pytestmark = pytest.mark.loopback

_DIRECT = {"sun_tropical_lon": 280, "moon_tropical_lon": 70, "jd": 2451545}
_SEARCH = {"start_jd_ut1": 2451545, "end_jd_ut1": 2451545.5,
           "janma_moon_sidereal_lon": 100,
           "policy": {"step_minutes": 360, "min_score": -100}}


@pytest.fixture
def client(moira_engine, monkeypatch):
    monkeypatch.setattr("moira_server.app.create_engine", lambda config: moira_engine)
    with TestClient(create_app(ServerConfig(docs_enabled=False))) as result:
        yield result


def _validation(response):
    assert response.status_code == 422
    body = response.json()
    assert body["error_code"] == "validation_error"
    assert body["category"] == "input_validation"
    assert body["request_id"] == response.headers["X-Request-ID"]


def test_personal_weights_and_complete_selected_policy_are_preserved(client):
    weights = MuhurtaPolicy(weight_tara=2.5, weight_chandra=3.5)
    response = client.post("/v1/muhurta/personal/score", json={**_DIRECT,
        "janma_moon_sidereal_lon": 100, "muhurta_policy": {"weight_tara": 2.5, "weight_chandra": 3.5}})
    assert response.status_code == 200
    body = response.json()
    panchanga = panchanga_at(280, 70, 2451545)
    direct = personal_muhurta_score(panchanga, 100, tropical_to_sidereal(70,2451545), weights)
    assert body["total"] == direct.total
    assert body["breakdown"] == direct.breakdown
    assert body["policy"]["weight_tara"] == 2.5
    assert body["policy"]["weight_chandra"] == 3.5
    assert len(body["policy"]["applied_policy_fields"]) == 7
    assert body["policy"]["omitted_policy_fields"] == ["use_classical_ashubha_yoga"]
    assert body["provenance"]["engine_entrypoint"] == "personal_muhurta_score"


def test_nested_panchanga_policy_owns_the_base_and_overlays(client):
    response = client.post("/v1/muhurta/personal/score", json={**_DIRECT,
        "ayanamsa_system": "Lahiri", "panchanga_policy": {"ayanamsa_system": "Raman"},
        "janma_moon_sidereal_lon": 100})
    assert response.status_code == 200
    body = response.json()
    panchanga = panchanga_at(280,70,2451545,policy=PanchangaPolicy("Raman"))
    moon = tropical_to_sidereal(70,2451545,system="Raman")
    assert body["panchanga"]["ayanamsa_system"] == "Raman"
    assert body["transit_moon_sidereal_lon"] == moon
    assert body["total"] == personal_muhurta_score(panchanga,100,moon).total


@pytest.mark.parametrize("route,applied", [("direct/score",5),("direct/classification",0)])
def test_generic_receipt_identifies_unapplied_natal_weights(client,route,applied):
    response = client.post("/v1/muhurta/"+route,json={**_DIRECT,
        "muhurta_policy":{"weight_tara":9,"weight_chandra":8}})
    assert response.status_code == 200
    policy=response.json()["policy"]
    assert policy["weight_tara"] == 9
    assert policy["weight_chandra"] == 8
    assert len(policy["applied_policy_fields"]) == applied
    assert "activity" not in policy["omitted_policy_fields"]


@pytest.mark.parametrize("route,key",[("/v1/muhurta/personal/score","janma_moon_sidereal_lon"),
    ("/v1/muhurta/direct/score","sun_tropical_lon"),
    ("/v1/muhurta/direct/score","moon_tropical_lon"),
    ("/v1/muhurta/direct/score","jd"),
    ("/v1/panchanga/instant","sun_tropical_lon"),
    ("/v1/panchanga/instant","moon_tropical_lon"),
    ("/v1/panchanga/instant","jd")])
@pytest.mark.parametrize("value",[True,"1"])
def test_moment_numeric_inputs_do_not_coerce(client,route,key,value):
    _validation(client.post(route,json={**_DIRECT,"janma_moon_sidereal_lon":100, key:value}
                           if "personal" in route else {**_DIRECT,key:value}))


@pytest.mark.parametrize("weight",["weight_tithi","weight_vara","weight_nakshatra",
    "weight_yoga","weight_karana","weight_tara","weight_chandra"])
@pytest.mark.parametrize("value",[True,"1",-1])
def test_all_policy_weights_are_strict_and_bounded(client,weight,value):
    _validation(client.post("/v1/muhurta/personal/score",json={**_DIRECT,
        "janma_moon_sidereal_lon":100,"muhurta_policy":{weight:value}}))


@pytest.mark.parametrize("route",["/v1/muhurta/chart/score","/v1/panchanga/chart"])
def test_chart_routes_reject_numeric_timestamp(client,route):
    _validation(client.post(route,json={"dt":946728000}))


def test_search_http_preserves_canonical_inputs_peak_and_counts(client,moira_engine):
    direct=moira_engine.find_muhurta_windows(2451545,2451545.5,
        janma_moon_sidereal_lon=100,policy=MuhurtaSearchPolicy(step_days=.25,min_score=-100))
    response=client.post("/v1/muhurta/search",json=_SEARCH)
    assert response.status_code == 200
    body=response.json()
    assert body["sample_count"] == len(direct.samples) == 3
    assert body["qualifying_sample_count"] == direct.qualifying_sample_count
    assert body["observed_window_count"] == direct.observed_window_count
    assert body["truncated"] == direct.truncated
    assert body["natal_mode"] == "tara_chandra"
    for encoded,window in zip(body["windows"],direct.windows,strict=True):
        assert encoded["qualifying_jds"] == list(window.qualifying_jds)
        assert encoded["peak"]["jd_ut1"] == window.peak.jd_ut1
        assert encoded["peak"]["score"]["total"] == window.peak.score.total
        assert encoded["peak"]["score"]["breakdown"] == window.peak.score.breakdown
        assert encoded["peak"]["jd_tt"] == window.peak.jd_tt
        assert encoded["peak"]["jd_tdb"] == window.peak.jd_tdb
        assert encoded["peak"]["tara"]["tara_number"] == window.peak.score.tara.tara_number
    assert body["policy"]["vara_basis"] == "jd_weekday"
    assert body["provenance"]["exact_transitions"] == "not_evaluated"


@pytest.mark.parametrize("payload",[
    {**_SEARCH,"start_jd_ut1":True}, {**_SEARCH,"end_jd_ut1":"2451546"},
    {**_SEARCH,"end_jd_ut1":2451545}, {**_SEARCH,"end_jd_ut1":2451600},
    {**_SEARCH,"policy":{"step_minutes":0}},
    {**_SEARCH,"policy":{"step_minutes":True}},
    {**_SEARCH,"policy":{"step_minutes":1},"end_jd_ut1":2451550},
    {**_SEARCH,"policy":{"max_results":True}},
    {**_SEARCH,"policy":{"max_results":129}},
    {**_SEARCH,"policy":{"ayanamsa_system":"missing"}},
    {**_SEARCH,"policy":{"ayanamsa_mode":"mean"}},
    {**_SEARCH,"janma_nakshatra":"Ashwini"},
])
def test_search_hostile_scope_is_rejected_before_engine_call(client,moira_engine,monkeypatch,payload):
    monkeypatch.setattr(moira_engine,"find_muhurta_windows",lambda *a,**k: pytest.fail("unexpected engine call"))
    _validation(client.post("/v1/muhurta/search",json=payload))


def test_empty_generic_search_distinguishes_omission_from_failure(client):
    response=client.post("/v1/muhurta/search",json={
        "start_jd_ut1":2451545,"end_jd_ut1":2451545.1,
        "policy":{"min_score":1e6}})
    assert response.status_code == 200
    body=response.json()
    assert body["windows"] == []
    assert body["natal_mode"] == "omitted"
    assert body["janma_moon_sidereal_lon"] is None
    assert body["sample_count"] == 4
    assert body["qualifying_sample_count"] == 0


def test_coverage_failure_has_specific_envelope(client):
    response=client.post("/v1/muhurta/search",json={
        "start_jd_ut1":-9500000,"end_jd_ut1":-9499999.9})
    assert response.status_code == 422
    body=response.json()
    assert body["error_code"] == "muhurta_date_outside_coverage"
    assert body["request_id"] == response.headers["X-Request-ID"]


def test_resource_failure_has_specific_envelope(client,moira_engine,monkeypatch):
    def fail(*a,**k):
        raise MuhurtaResourceError("required resource unavailable")
    monkeypatch.setattr(moira_engine,"find_muhurta_windows",fail)
    response=client.post("/v1/muhurta/search",json=_SEARCH)
    assert response.status_code == 503
    assert response.json()["error_code"] == "muhurta_resource_unavailable"


def test_search_openapi_and_method_boundary(client):
    schema=client.app.openapi()
    assert "/v1/muhurta/search" in schema["paths"]
    props=schema["components"]["schemas"]["MuhurtaSearchPolicyRequest"]["properties"]
    assert props["max_results"]["maximum"] == 128
    assert len(props["ayanamsa_system"]["enum"]) == 12
    assert client.get("/v1/muhurta/search").status_code == 405
