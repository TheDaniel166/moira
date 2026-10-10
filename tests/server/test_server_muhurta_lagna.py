"""Kernel-free strict admission, OpenAPI contracts, partials and error transport."""
import json
from dataclasses import asdict
from datetime import datetime
from zoneinfo import ZoneInfo
import pytest
from fastapi.testclient import TestClient
from moira import Moira, evaluate_muhurta_lagna_strength, muhurta_lagna_for_datetime
from moira.muhurta_search import MuhurtaResourceError, MuhurtaCoverageError
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.serializers.muhurta_lagna import serialize_lagna_assessment
from tests.unit.test_muhurta_lagna import POSITIONS, strength

pytestmark=pytest.mark.loopback
DIRECT={'sidereal_longitudes':POSITIONS,'jd_ut1':2451545.,'lagna_sidereal_longitude':5.}
DATED={'dt':'2026-10-09T12:00:00Z','latitude':28.6,'longitude':77.2}


@pytest.fixture
def surface(monkeypatch):
    class Engine:
        def muhurta_lagna_for_datetime(self, **kwargs):
            raise AssertionError('unexpected resource access')
    engine=Engine()
    monkeypatch.setattr('moira_server.app.create_engine',lambda config:engine)
    with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as client:
        yield client,engine


def test_catalogue_direct_and_partial_lossless(surface):
    client,_=surface
    catalogue=client.get('/v1/muhurta/lagna/catalogue')
    assert catalogue.status_code==200 and len(catalogue.json()['purpose_profiles'])==2
    for payload in (DIRECT,{'sidereal_longitudes':{},'jd_ut1':2451545.}):
        r=client.post('/v1/muhurta/lagna/direct',json=payload)
        assert r.status_code==200,r.text
        expected=evaluate_muhurta_lagna_strength(**payload)
        assert r.json()==serialize_lagna_assessment(expected).model_dump(mode='json')
        assert r.json()['activity_suitability']=='not_evaluated'


@pytest.mark.parametrize('field,value',[
 ('jd_ut1',True),('jd_ut1','2451545'),('jd_ut1',float('nan')),('jd_ut1',float('inf')),
 ('jd_ut1',10**1000),('lagna_sidereal_longitude',360),('lagna_sidereal_longitude',-1),
 ('lagna_sidereal_longitude','12'),('lagna_sidereal_longitude',False),
 ('sidereal_longitudes',{'Earth':12}),('sidereal_longitudes',{'Moon':'12'}),
 ('sidereal_longitudes',{'Moon':True}),('sidereal_longitudes',{'Moon':360}),
 ('sidereal_longitudes',{'Rahu':10,'Ketu':10}),
 ('natal_moon_sidereal_longitude',-1),('natal_lagna_sidereal_longitude',360),
 ('shadbala_result',{}),('policy',{'purpose_profile':'universal'}),
 ('policy',{'aspect_profile':'rasi_drishti'}),('policy',{'ayanamsa_system':'invented'}),
 ('policy',{'purpose_profile':'mc_nakshatra_44.v1','parihara_profile':'mc_vivaha_88_natural_avasthas_orb.v1'}),
 ('extra',123),
])
def test_invalid_direct_422(surface,field,value):
    client,_=surface
    r=client.post('/v1/muhurta/lagna/direct',content=json.dumps(DIRECT|{field:value}),headers={'Content-Type':'application/json'})
    assert r.status_code==422,r.text


@pytest.mark.parametrize('field,value',[
 ('dt',123456789),('dt','123456789'),('dt','2026-10-09'),('dt','2026-10-09T12:00:00'),
 ('latitude',91),('latitude',True),('longitude',181),('include_shadbala','true'),
 ('include_shadbala',1),('hora_lord','Venus'),('hora_lord','Rahu'),('extra',1),
])
def test_invalid_datetime_422_without_resources(surface,field,value):
    client,_=surface
    r=client.post('/v1/muhurta/lagna/datetime',json=DATED|{field:value})
    assert r.status_code==422,r.text


def test_full_strength_input_and_stale_rejection(surface):
    client,_=surface
    body=DIRECT|{'shadbala_result':asdict(strength())}
    r=client.post('/v1/muhurta/lagna/direct',json=body)
    assert r.status_code==200,r.text
    assert len(r.json()['shadbala'])==7
    body['shadbala_result']['jd']+=1
    assert client.post('/v1/muhurta/lagna/direct',json=body).status_code==422


@pytest.mark.parametrize('error,status',[(MuhurtaResourceError('missing'),503),(MuhurtaCoverageError('outside'),422)])
def test_resource_and_coverage_envelopes(surface,error,status):
    client,engine=surface
    def fail(**kwargs):raise error
    engine.muhurta_lagna_for_datetime=fail
    r=client.post('/v1/muhurta/lagna/datetime',json=DATED)
    assert r.status_code==status,r.text


def test_openapi_explicit_models_and_no_untyped_responses(surface):
    client,_=surface
    schema=client.get('/openapi.json').json()
    for name,method in [('catalogue','get'),('direct','post'),('datetime','post')]:
        op=schema['paths']['/v1/muhurta/lagna/'+name][method]
        assert '$ref' in op['responses']['200']['content']['application/json']['schema']
    assert schema['components']['schemas']['LagnaDirectRequest']['additionalProperties'] is False
    assert schema['components']['schemas']['LagnaPolicyRequest']['additionalProperties'] is False


def test_python_date_validation_precedes_resource_access():
    for dt in (datetime(2026,1,1),datetime(2026,3,8,2,30,tzinfo=ZoneInfo('America/New_York'))):
        with pytest.raises(ValueError):muhurta_lagna_for_datetime(dt,0,0,reader=object())


def test_facade_preserves_reader(monkeypatch):
    seen=[]
    monkeypatch.setattr('moira.muhurta_lagna_dated.muhurta_lagna_for_datetime',lambda *args,**kwargs:seen.append(kwargs))
    class Owner:_reader=object()
    owner=Owner()
    Moira.muhurta_lagna_for_datetime.__wrapped__(owner,datetime(2026,1,1),0,0) if hasattr(Moira.muhurta_lagna_for_datetime,'__wrapped__') else Moira.muhurta_lagna_for_datetime(owner,datetime(2026,1,1),0,0)
    assert seen[0]['reader'] is owner._reader
