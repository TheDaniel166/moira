"""Engine/facade/REST parity, strict admission and exact public failure schemas."""
from datetime import datetime, timezone
from importlib import import_module
import json
from fastapi.testclient import TestClient
import pytest

from moira import Moira
from moira.gochara import GocharaPolicy, GocharaVedhaMode, GOCHARA_PLANETS
from moira.gochara_dated import GocharaDatePolicy, GocharaBirthLocation, GocharaNatalBavMode, GocharaResourceError, GocharaCoverageError
from moira.gochara_windows import GocharaWindowUnresolvedError, window_json_bytes
from moira.sidereal import Ayanamsa
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.gochara_windows import GocharaWindowErrorResponse
from tools.gochara_window_cases import install, START, NATAL

pytestmark = pytest.mark.loopback


@pytest.fixture
def surface(monkeypatch):
    calls=install(monkeypatch,{"Moon":(29.9,.2)})
    class Engine:
        _reader=object()
        gochara_windows=Moira.gochara_windows
        gochara_windows_for_datetimes=Moira.gochara_windows_for_datetimes
    engine=Engine()
    monkeypatch.setattr("moira_server.app.create_engine",lambda cfg:engine)
    app=create_app(ServerConfig(docs_enabled=True,prewarm_enabled=False))
    with TestClient(app) as client:
        yield client,engine,calls


def payload():
    return dict(natal_jd_ut1=NATAL,start_jd_ut1=START,end_jd_ut1=START+1)


@pytest.mark.parametrize("system",Ayanamsa.ALL)
@pytest.mark.parametrize("raw",[False,True])
@pytest.mark.parametrize("baseline",[False,True])
def test_all_astronomy_bav_and_vedha_choices_have_lossless_transport(surface,system,raw,baseline):
    client,engine,_=surface
    policy=GocharaDatePolicy(system,GocharaNatalBavMode.COMPUTE_RAW if raw else GocharaNatalBavMode.OMIT,
        GocharaPolicy(vedha_mode=GocharaVedhaMode.BASELINE_ONLY if baseline else GocharaVedhaMode.ORDINARY))
    location=GocharaBirthLocation(28.6,77.2) if raw else None
    body=payload()|{"subjects":["Jupiter"],"policy":{
        "ayanamsa_system":system,"natal_bav_mode":policy.natal_bav_mode.value,
        "gochara_policy":{"vedha_mode":policy.gochara_policy.vedha_mode.value}}}
    if location:
        body["birth_location"]={"latitude":28.6,"longitude":77.2}
    response=client.post("/v1/gochara/windows/from-epochs",json=body)
    assert response.status_code==200,response.text
    result=engine.gochara_windows(NATAL,START,START+1,policy=policy,birth_location=location,subjects=("Jupiter",))
    assert response.json()==result.to_dict()
    assert response.content==window_json_bytes(result)
    assert response.json()["coverage"]["participants"]==list(GOCHARA_PLANETS)


@pytest.mark.parametrize("patch,code",[
    ({"natal_jd_ut1":True},"validation_error"),({"start_jd_ut1":"2460000"},"validation_error"),
    ({"end_jd_ut1":START},"validation_error"),({"end_jd_ut1":START+367},"gochara_window_budget_exceeded"),
    ({"start_jd_ut1":2415020.4},"gochara_window_outside_certified_domain"),
    ({"subjects":["Moon","Moon"]},"validation_error"),({"subjects":["Rahu"]},"validation_error"),
    ({"unknown":1},"validation_error"),({"search_policy":{"require_resolved":"true"}},"validation_error"),
    ({"search_policy":{"limits":{"max_events":True}}},"validation_error"),
    ({"policy":{"natal_bav_mode":"compute_raw"}},"validation_error"),
])
def test_invalid_requests_keep_engine_errors_before_astronomy(surface,patch,code):
    client,_,calls=surface
    response=client.post("/v1/gochara/windows/from-epochs",json=payload()|patch)
    assert response.status_code==422,response.text
    assert response.json()["error_code"]==code
    GocharaWindowErrorResponse.model_validate(response.json())
    assert not calls


@pytest.mark.parametrize("error,status,code",[
    (GocharaResourceError("missing anchor"),503,"gochara_resource_unavailable"),
    (GocharaCoverageError("missing epoch"),422,"gochara_date_outside_coverage"),
    (GocharaWindowUnresolvedError(("count_unproved",),1,2.),422,"gochara_window_unresolved"),
])
def test_domain_failures_preserve_typed_transport(surface,monkeypatch,error,status,code):
    client,engine,_=surface
    def fail(*args,**kwargs):
        raise error
    monkeypatch.setattr(engine,"gochara_windows",fail)
    response=client.post("/v1/gochara/windows/from-epochs",json=payload())
    assert response.status_code==status and response.json()["error_code"]==code
    GocharaWindowErrorResponse.model_validate(response.json())


def test_budget_numeric_details_match_openapi_and_no_partial_200(surface):
    client,_,_=surface
    response=client.post("/v1/gochara/windows/from-epochs",json=payload()|{"search_policy":{"limits":{"max_output_bytes":1}}})
    assert response.status_code==422
    data=response.json()
    assert data["error_code"]=="gochara_window_budget_exceeded"
    assert type(data["details"]["count"]) is int and data["details"]["limit"]==1
    GocharaWindowErrorResponse.model_validate(data)


def test_civil_route_converts_once_and_serializes_same_engine_result(surface,monkeypatch):
    client,engine,_=surface
    calls=[]
    julian=import_module("moira.julian")
    monkeypatch.setattr(julian,"jd_from_datetime",lambda v:v.day)
    def to_ut(v):
        calls.append(v)
        return {1:NATAL,2:START,3:START+1}[v]
    monkeypatch.setattr(julian,"utc_to_ut1",to_ut)
    values=[datetime(2026,1,d,tzinfo=timezone.utc) for d in (1,2,3)]
    response=client.post("/v1/gochara/windows/from-datetimes",json=dict(zip(
        ("natal_dt","start_dt","end_dt"),(v.isoformat() for v in values))))
    assert response.status_code==200,response.text
    assert calls==[1,2,3]
    result=engine.gochara_windows_for_datetimes(*values)
    assert response.content==window_json_bytes(result)


@pytest.mark.parametrize("value",["2026-01-01","2026-01-01T00:00:00",123,False,
    "1700000000","+1700000000"," 1700000000 ","1700000000.0"])
def test_ambiguous_civil_instants_rejected(surface,value):
    client,_,calls=surface
    response=client.post("/v1/gochara/windows/from-datetimes",json={"natal_dt":value,
        "start_dt":"2026-01-02T00:00:00Z","end_dt":"2026-01-03T00:00:00Z"})
    assert response.status_code==422 and not calls


def test_unresolved_bands_survive_http_and_strict_mode(surface,monkeypatch):
    client,_,_=surface
    install(monkeypatch,{"Moon":(29.75,1.,-1.)})
    response=client.post("/v1/gochara/windows/from-epochs",json=payload())
    assert response.status_code==200
    assert response.json()["coverage"]["events_resolved"] is False
    assert any(r["kind"]=="unresolved_band" for r in response.json()["regions"])
    strict=client.post("/v1/gochara/windows/from-epochs",json=payload()|{"search_policy":{"require_resolved":True}})
    assert strict.status_code==422 and strict.json()["error_code"]=="gochara_window_unresolved"


def test_capabilities_openapi_and_curated_models(surface):
    client,_,calls=surface
    response=client.get("/v1/gochara/windows/capabilities")
    assert response.status_code==200 and not calls
    assert response.json()["ayanamsas"]==Ayanamsa.ALL
    spec=client.get("/openapi.json").json()
    for route in ("from-epochs","from-datetimes"):
        operation=spec["paths"]["/v1/gochara/windows/"+route]["post"]
        assert operation["responses"]["422"]["content"]["application/json"]["schema"]["$ref"].endswith("GocharaWindowErrorResponse")
    models=import_module("moira_server.models.gochara_windows")
    curated=import_module("moira_server.models")
    assert all(getattr(curated,n) is getattr(models,n) for n in models.__all__)
    schema=json.dumps(spec["components"]["schemas"]["GocharaWindowRegionResponse"])
    assert "boundary_band" in schema and "unresolved_band" in schema


def test_asgi_worker_requests_keep_independent_receipts(surface):
    from concurrent.futures import ThreadPoolExecutor
    client,_,_=surface
    bodies=[payload()|{"policy":{"ayanamsa_system":s}} for s in ("Lahiri","True Mula")]
    sequential=[client.post("/v1/gochara/windows/from-epochs",json=b).content for b in bodies]
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda b:client.post("/v1/gochara/windows/from-epochs",json=b),bodies))
    assert all(r.status_code==200 for r in results)
    assert [r.content for r in results]==sequential


def test_http_disconnect_leaves_worker_context_and_reader_usable(surface,monkeypatch):
    """A timed-out loopback client cannot poison the synchronous worker."""
    import socket
    import threading
    import time
    import urllib.request
    import uvicorn
    from moira.spk_reader import get_active_reader
    client,engine,_=surface
    original=engine.gochara_windows
    completed=threading.Event()
    clean=[]
    def delayed(*args,**kwargs):
        before=get_active_reader()
        try:
            time.sleep(.2)
            return original(*args,**kwargs)
        finally:
            clean.append(get_active_reader() is before)
            completed.set()
    monkeypatch.setattr(engine,"gochara_windows",delayed)
    sock=socket.socket()
    sock.bind(("127.0.0.1",0))
    port=sock.getsockname()[1]
    config=uvicorn.Config(client.app,host="127.0.0.1",port=port,log_level="critical",lifespan="off",ws="none")
    server=uvicorn.Server(config)
    worker=threading.Thread(target=lambda:server.run(sockets=[sock]),daemon=True)
    worker.start()
    try:
        deadline=time.monotonic()+5
        while not server.started and time.monotonic()<deadline:
            time.sleep(.01)
        assert server.started
        request=urllib.request.Request(f"http://127.0.0.1:{port}/v1/gochara/windows/from-epochs",
            data=json.dumps(payload()).encode(),headers={"Content-Type":"application/json"})
        with pytest.raises(TimeoutError):
            urllib.request.urlopen(request,timeout=.05)
        assert completed.wait(5) and clean==[True]
        with urllib.request.urlopen(request,timeout=5) as response:
            assert json.load(response)["coverage"]["domain_accounted"]
    finally:
        server.should_exit=True
        worker.join(timeout=5)
        sock.close()
    assert not worker.is_alive() and all(clean)
