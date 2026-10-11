"""Residential HTTP parity, strict preflight and source discovery."""
from copy import deepcopy
import json
import pytest
from fastapi.testclient import TestClient
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira.muhurta_vastu import assess_vastu_election, VastuElectionPolicy, VastuElectionContext
from moira.muhurta_election import ElectionEvidence
from moira_server.models.muhurta_vastu import VastuAssessmentResponse
from moira_server.serializers.muhurta_election import election_values

pytestmark = pytest.mark.loopback
DIRECT = {'evidence':{'jd_ut1':2460000.},'policy':{'purpose':'foundation'},'context':{'facing':'east'}}
DATED = {'dt':'2026-10-10T12:00:00Z','latitude':28.6,'longitude':77.2,'timezone':'Asia/Kolkata',
         'policy':{'purpose':'foundation'},'context':{'facing':'east'}}


@pytest.fixture
def client(monkeypatch):
    class Engine:
        def vastu_election_for_datetime(self,*args,**kwargs):
            raise AssertionError('invalid request touched reader')
    monkeypatch.setattr('moira_server.app.create_engine', lambda config: Engine())
    with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as client:
        yield client


def test_catalogue_and_direct_are_lossless_without_kernel(client):
    r = client.get('/v1/muhurta/vastu/catalogue')
    assert r.status_code == 200, r.text
    assert r.json()['profiles'] == ['mc_maniprabha_1948_residential.v1']
    assert len(r.json()['rules']) == 16
    r = client.post('/v1/muhurta/vastu/direct',json=DIRECT)
    assert r.status_code == 200, r.text
    engine = assess_vastu_election(ElectionEvidence(2460000.), policy=VastuElectionPolicy('foundation'), context=VastuElectionContext('east'))
    assert r.json() == VastuAssessmentResponse(**election_values(engine)).model_dump(mode='json')


@pytest.mark.parametrize('owner,field,value',[
    ('evidence','jd_ut1',True),('evidence','jd_ut1','2460000'),('evidence','jd_ut1',float('nan')),
    ('evidence','longitude_frame','heliocentric'),('evidence','source_receipt','verified'),
    ('evidence','planets',[{'planet':'Sun','sidereal_longitude':1},{'planet':'Sun','sidereal_longitude':2}]),
    ('policy','purpose','structural_safety'),('policy','solver_tolerance_seconds',True),
    ('policy','month_system','amanta'),('policy','profile','universal'),('policy','godhuli',True),
    ('context','facing',None),('context','facing','northeast'),('context','extraordinary_reason','fire'),
    ('context','participant',{'participant_id':'a','natal_moon_sidereal_longitude':False}),
    ('context','unexpected',1),
])
def test_hostile_direct_rejected(client,owner,field,value):
    payload = deepcopy(DIRECT)
    payload[owner][field] = value
    r = client.post('/v1/muhurta/vastu/direct',content=json.dumps(payload),headers={'Content-Type':'application/json'})
    assert r.status_code == 422,r.text


@pytest.mark.parametrize('field,value',[
    ('dt','2026-10-10T12:00:00'),('dt',1234),('latitude',True),('latitude',90),
    ('timezone','Mars/Olympus'),('limits',{'max_history_days':1}),('limits',{'max_cells':100000}),
])
def test_datetime_preflight(client,field,value):
    payload = deepcopy(DATED)
    payload[field] = value
    assert client.post('/v1/muhurta/vastu/datetime',json=payload).status_code == 422


def test_closed_openapi_family_surfaces(client):
    schema = client.get('/openapi.json').json()
    for operation in ('catalogue','direct','datetime','windows'):
        assert '/v1/muhurta/vastu/'+operation in schema['paths']
    assert schema['components']['schemas']['VastuPolicyRequest']['properties']['purpose']['enum'] == [
        'foundation','first_entry','return_entry','old_house_entry','extraordinary_entry']


def test_preflight_budget_has_purpose_election_error_identity(client):
    body=deepcopy(DATED)
    body['policy']['purpose']='first_entry'
    body['limits']={'max_history_days':4}
    r=client.post('/v1/muhurta/vastu/datetime',json=body)
    assert r.status_code==422,r.text
    assert r.json()['error_code']=='election_search_budget'
