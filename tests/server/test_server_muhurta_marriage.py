"""HTTP admission, engine parity, error mapping and source-discovery contracts."""
import json
from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from moira import Moira, MarriageElectionEvidence, MarriageElectionPolicy, assess_marriage_election
from moira.muhurta_search import MuhurtaResourceError,MuhurtaCoverageError
from moira.muhurta_marriage_dated import MarriageSearchBudgetError,marriage_election_for_datetime
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.serializers.muhurta_marriage import serialize_marriage_assessment

pytestmark=pytest.mark.loopback
POLICY={'ritual_anchor':'vows','regional_tradition':'all_regions'}
DIRECT={'evidence':{'jd_ut1':2460000.},'policy':POLICY}
DATED={'dt':'2026-10-10T12:00:00Z','latitude':28.6,'longitude':77.2,'timezone':'Asia/Kolkata','policy':POLICY}


@pytest.fixture
def surface(monkeypatch):
    class Engine:
        def marriage_election_for_datetime(self,*args,**kwargs):
            raise AssertionError('unexpected reader access')
    engine=Engine()
    monkeypatch.setattr('moira_server.app.create_engine',lambda config:engine)
    with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as client:
        yield client,engine


def test_direct_and_catalogue_are_kernel_free_and_lossless(surface):
    from moira.muhurta_marriage import marriage_election_catalogue
    from moira_server.serializers.muhurta_marriage import serialize_marriage_catalogue
    from moira_server.models.muhurta_marriage import MarriageLimitsModel
    client,_=surface
    response=client.get('/v1/muhurta/marriage/catalogue')
    assert response.status_code==200,response.text
    assert response.json()['admission_status']=='source_scoped_public'
    assert any(r['rule_id']=='kartari' for r in response.json()['rules'])
    assert response.json()==serialize_marriage_catalogue(marriage_election_catalogue()).model_dump(mode='json')
    assert response.json()['default_limits']==MarriageLimitsModel().model_dump(mode='json')
    for name,value in response.json()['hard_maxima'].items():
        with pytest.raises(ValueError):
            MarriageLimitsModel(**{name:value+1})
    assert response.json()['minimum_parent_history_days']==65
    response=client.post('/v1/muhurta/marriage/direct',json=DIRECT)
    assert response.status_code==200,response.text
    expected=assess_marriage_election(MarriageElectionEvidence(2460000.),policy=MarriageElectionPolicy(**POLICY))
    assert response.json()==serialize_marriage_assessment(expected).model_dump(mode='json')
    assert response.json()['personal_decision']['status']=='not_requested'
    assert response.json()['astronomical']['coverage_complete'] is False


@pytest.mark.parametrize('field,value',[
    ('jd_ut1',True),('jd_ut1','2460000'),('jd_ut1',float('nan')),('jd_ut1',float('inf')),
    ('lagna_sidereal_longitude',360),('lagna_sidereal_longitude',False),
    ('planets',[{'planet':'Earth','sidereal_longitude':10}]),
    ('planets',[{'planet':'Sun','sidereal_longitude':True}]),
    ('planets',[{'planet':'Sun','sidereal_longitude':10},{'planet':'Sun','sidereal_longitude':20}]),
    ('planets',[{'planet':'Rahu','sidereal_longitude':10},{'planet':'Ketu','sidereal_longitude':100}]),
    ('extra',1),('longitude_frame','heliocentric'),
])
def test_invalid_evidence_rejected_without_reader(surface,field,value):
    client,_=surface
    payload=deepcopy(DIRECT)
    payload['evidence'][field]=value
    r=client.post('/v1/muhurta/marriage/direct',content=json.dumps(payload),headers={'Content-Type':'application/json'})
    assert r.status_code==422,r.text


@pytest.mark.parametrize('field,value',[
    ('ritual_anchor',' '),('ritual_anchor',False),('regional_tradition','infer_from_location'),
    ('profile','raman_marriage'),('ayanamsa_system','Fagan-Bradley'),('remedies',['all_doshas']),
    ('godhuli','true'),('godhuli',1),('solver_tolerance_seconds',True),('extra',1),
])
def test_invalid_policy_rejected(surface,field,value):
    client,_=surface
    payload=deepcopy(DIRECT)
    payload['policy'][field]=value
    assert client.post('/v1/muhurta/marriage/direct',json=payload).status_code==422


@pytest.mark.parametrize('field,value',[
    ('dt',1234),('dt','2026-10-10'),('dt','2026-10-10T12:00:00'),('latitude',True),
    ('latitude',90),('timezone','Mars/Olympus'),('limits',{'max_history_days':True}),('extra',1),
])
def test_invalid_datetime_does_not_touch_resources(surface,field,value):
    client,_=surface
    r=client.post('/v1/muhurta/marriage/datetime',json=DATED|{field:value})
    assert r.status_code==422,r.text


@pytest.mark.parametrize('error,status,code',[
    (MuhurtaResourceError('missing'),503,'muhurta_resource_unavailable'),
    (MuhurtaCoverageError('history outside'),422,'muhurta_date_outside_coverage'),
    (MarriageSearchBudgetError('evaluations',10,11,'history'),422,'marriage_search_budget'),
])
def test_typed_errors_are_preserved(surface,error,status,code):
    client,engine=surface
    def fail(*args,**kwargs):raise error
    engine.marriage_election_for_datetime=fail
    r=client.post('/v1/muhurta/marriage/datetime',json=DATED)
    assert r.status_code==status,r.text
    assert r.json()['error_code']==code


@pytest.mark.parametrize('operation,body,kind,stage',[
    ('datetime',DATED|{'limits':{'max_history_days':1}},'history_days','calendar_parent_preflight'),
    ('windows',{k:v for k,v in DATED.items() if k!='dt'}|{
        'start':DATED['dt'],'end':'2026-10-19T12:00:00Z'},'range_days','preflight'),
])
def test_preflight_budget_error_keeps_engine_contract_before_reader(surface,operation,body,kind,stage):
    client,_=surface
    response=client.post('/v1/muhurta/marriage/'+operation,json=body)
    assert response.status_code==422,response.text
    result=response.json()
    assert result['error_code']=='marriage_search_budget'
    assert result['category']=='search_budget'
    assert result['details']['limit_kind']==kind
    assert result['details']['stage']==stage


def test_openapi_has_strict_nested_requests_and_typed_results(surface):
    client,_=surface
    schema=client.get('/openapi.json').json()
    for name,method in (('catalogue','get'),('direct','post'),('datetime','post')):
        op=schema['paths']['/v1/muhurta/marriage/'+name][method]
        assert '$ref' in op['responses']['200']['content']['application/json']['schema']
    for model in ('MarriagePolicyRequest','MarriageEvidenceModel','MarriagePlanetModel','MarriageVisibilitySampleModel'):
        assert schema['components']['schemas'][model]['additionalProperties'] is False


def test_civil_gap_and_duplicate_roles_rejected_before_reader():
    with pytest.raises(ValueError):
        marriage_election_for_datetime(datetime(2026,3,8,2,30,tzinfo=ZoneInfo('America/New_York')),
            0,0,timezone='UTC',policy=MarriageElectionPolicy(**POLICY),reader=object())


def test_facade_passes_exact_owned_reader(monkeypatch):
    seen=[]
    monkeypatch.setattr('moira.muhurta_marriage_dated.marriage_election_for_datetime',lambda *a,**k:seen.append(k))
    class Owner:
        _reader=object()
    owner=Owner()
    function=Moira.marriage_election_for_datetime
    getattr(function,'__wrapped__',function)(owner,datetime(2026,1,1),0,0)
    assert seen[0]['reader'] is owner._reader


def test_windows_transport_preserves_shared_registries_and_uncertainty(surface):
    from tests.unit.test_muhurta_marriage_windows import window_fixture
    from moira_server.serializers.muhurta_marriage import serialize_marriage_windows
    from moira_server.models.muhurta_marriage import MarriageWindowsResponse
    client,engine=surface
    result=window_fixture()
    engine.marriage_election_windows=lambda *a,**k:result
    payload={k:v for k,v in DATED.items() if k!='dt'}|{'start':'2023-02-24T12:00:00Z','end':'2023-02-24T18:00:00Z'}
    response=client.post('/v1/muhurta/marriage/windows',json=payload)
    assert response.status_code==200,response.text
    expected=serialize_marriage_windows(result).model_dump(mode='json')
    assert response.json()==expected
    assert MarriageWindowsResponse.model_validate_json(response.text).model_dump(mode='json')==expected
    assert response.json()['cells'][0]['constancy_certified'] is False
