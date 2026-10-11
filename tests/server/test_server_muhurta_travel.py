"""Travel component discovery and strict context contracts."""
from copy import deepcopy
import pytest
from fastapi.testclient import TestClient
from moira_server.app import create_app
from moira_server.config import ServerConfig

pytestmark=pytest.mark.loopback
DIRECT={'evidence':{'jd_ut1':2460000.},'policy':{'profile':'kp_1917_weekday_direction_release.v1'},
        'context':{'traveller_id':'a','anchor':'leave_residence','direction':'east'}}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr('moira_server.app.create_engine',lambda config:object())
    with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as client:
        yield client


def test_component_scope_and_unavailable_are_visible(client):
    r=client.get('/v1/muhurta/travel/catalogue')
    assert r.status_code==200,r.text
    assert all(scope=='named_component' for p,scope in r.json()['profile_scopes'] if p.startswith('kp_'))
    assert ['mc_maniprabha_1948_ordinary_land.v1','ordinary_land_departure'] in r.json()['profile_scopes']
    r=client.post('/v1/muhurta/travel/direct',json=DIRECT)
    assert r.status_code==200,r.text
    assert r.json()['policy']['scope']=='named_component'
    assert r.json()['astronomical']['status']=='indeterminate'


@pytest.mark.parametrize('owner,name,value',[
    ('policy','profile','complete_kp_travel'),('policy','tithi_ordinal','zero_based'),('policy','remedies',['cancel_all']),
    ('context','direction',None),('context','direction','northeast'),('context','anchor','booking_time'),
    ('context','traveller_id',' '),('context','leg','arrival'),('context','prior_departure','yesterday'),
    ('context','participant',{'participant_id':'a','natal_moon_sidereal_longitude':30.}),
    ('evidence','jd_ut1',True),
])
def test_component_rejects_unsupported_context(client,owner,name,value):
    body=deepcopy(DIRECT)
    body[owner][name]=value
    assert client.post('/v1/muhurta/travel/direct',json=body).status_code==422


def test_mc_profile_discovery_and_conditional_direct(client):
    body=deepcopy(DIRECT)
    body['policy']['profile']='mc_maniprabha_1948_ordinary_land.v1'
    body['context'].update(direction='northeast',participant={'participant_id':'a'},
                           prior_departure_jd_ut1=2450000.,completed_stop_nights=5)
    r=client.post('/v1/muhurta/travel/direct',json=body)
    assert r.status_code==200,r.text
    assert r.json()['policy']['scope']=='ordinary_land_departure'
    assert not r.json()['personal_decision']['coverage_complete']
    assert any(f['family_id']=='travel.mc_import.vishanadi' for f in r.json()['astronomical_findings'])
    body['policy']['tithi_ordinal']='paksha_1_to_15'
    assert client.post('/v1/muhurta/travel/direct',json=body).status_code==422
