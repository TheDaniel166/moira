"""Strict REST admission, typed evidence, and canonical engine projection."""
from datetime import date
from dataclasses import asdict, replace
import json

from fastapi.testclient import TestClient
import pytest

from moira import Moira, MuhurtaDoshaPolicy, detect_muhurta_doshas, muhurta_dosha_catalogue
from moira.muhurta_dosha import KP_EXEMPT, MC_NECESSARY, MC_ABHIJIT
from moira.muhurta_search import MuhurtaCoverageError, MuhurtaResourceError
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.serializers.muhurta_dosha import serialize_dosha_assessment, serialize_dosha_catalogue, serialize_dosha_day
from tests.muhurta_dosha_support import install_dosha_sky

pytestmark=pytest.mark.loopback
DIRECT={'sun_sidereal_longitude':0,'moon_sidereal_longitude':45,'jd_ut1':2451545.,'weekday':5}
DAY={'local_date':'2026-10-09','latitude':20,'longitude':80,'timezone':'Asia/Kolkata'}


@pytest.fixture
def surface(monkeypatch):
    owner,reader,calls,state=install_dosha_sky(monkeypatch)
    class Engine:
        _reader=reader
        muhurta_doshas_for_date=Moira.muhurta_doshas_for_date
    engine=Engine()
    monkeypatch.setattr('moira_server.app.create_engine',lambda config:engine)
    with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as client:
        yield client,engine,owner,calls,state


def test_catalogue_and_direct_are_kernel_free(surface):
    client,_,_,calls,_=surface
    result=client.get('/v1/muhurta/doshas/catalogue')
    assert result.status_code==200
    assert result.json()==serialize_dosha_catalogue(muhurta_dosha_catalogue()).model_dump(mode='json')
    result=client.post('/v1/muhurta/doshas/direct',json=DIRECT)
    assert result.status_code==200,result.text
    assert result.json()==serialize_dosha_assessment(detect_muhurta_doshas(**DIRECT)).model_dump(mode='json')
    assert not calls


@pytest.mark.parametrize('table',['mc_vivaha_49_51.v1','kp_185_single_mula.v1','kp_185_dual_mula.v1'])
@pytest.mark.parametrize('clock',['mc_avasthi_scaled_start_fixed_width.v1','normalized_nakshatra_sixtieths.v1'])
def test_day_and_every_direct_cell_have_lossless_parity(surface,table,clock):
    client,engine,_,_,_=surface
    profiles=[KP_EXEMPT,MC_NECESSARY,MC_ABHIJIT]
    body=DAY|{'necessary_activity':True,'policy':{'vishanadi_profile':table,'vishanadi_clock':clock,'parihara_profiles':profiles}}
    response=client.post('/v1/muhurta/doshas/day',json=body)
    assert response.status_code==200,response.text
    expected=engine.muhurta_doshas_for_date(date(2026,10,9),20,80,timezone='Asia/Kolkata',necessary_activity=True,
        policy=MuhurtaDoshaPolicy(vishanadi_profile=table,vishanadi_clock=clock,parihara_profiles=tuple(profiles)))
    assert response.json()==serialize_dosha_day(expected).model_dump(mode='json')
    assert expected.status=='available' and len(expected.cells)>20
    for cell in response.json()['cells']:
        a=cell['assessment']
        result=client.post('/v1/muhurta/doshas/direct',json=a['inputs']|{'policy':body['policy']})
        assert result.status_code==200,result.text
        assert result.json()['findings']==a['findings']
    assert any(f['state']=='neutralized' for c in response.json()['cells'] for f in c['assessment']['findings'])


@pytest.mark.parametrize('kind,bad',[
    ('direct',{'jd_ut1':True}),('direct',{'jd_ut1':'2451545'}),
    ('direct',{'jd_ut1':float('inf')}),('direct',{'moon_sidereal_longitude':float('nan')}),
    ('direct',{'sun_sidereal_longitude':10**1000}),('direct',{'moon_sidereal_longitude':360}),
    ('direct',{'weekday':True}),('direct',{'weekday':1.0}),('direct',{'weekday':'1'}),
    ('direct',{'weekday':7}),('direct',{'necessary_activity':1}),('direct',{'necessary_activity':'true'}),
    ('direct',{'policy':{'vishanadi_profile':'combined'}}),('direct',{'policy':{'gandanta_profile':'angular'}}),
    ('direct',{'policy':{'parihara_profiles':[MC_ABHIJIT,MC_ABHIJIT]}}),
    ('direct',{'policy':{'ghati_seconds':1200}}),('direct',{'policy':{'ayanamsa_system':'unknown'}}),
    ('direct',{'policy':{'solver_tolerance_seconds':True}}),('direct',{'unexpected':1}),
    ('day',{'local_date':0}),('day',{'local_date':'20261009'}),
    ('day',{'local_date':'2026-10-09T00:00:00'}),('day',{'latitude':90}),('day',{'latitude':True}),
    ('day',{'longitude':'80'}),('day',{'timezone':'Mars/Unknown'}),
    ('day',{'local_date':'2011-12-30','timezone':'Pacific/Apia'}),
])
def test_rejection_precedes_astronomy(surface,kind,bad):
    client,_,_,calls,_=surface
    response=client.post('/v1/muhurta/doshas/'+kind,content=json.dumps((DIRECT if kind=='direct' else DAY)|bad),headers={'Content-Type':'application/json'})
    assert response.status_code==422,response.text
    assert response.json()['error_code']=='validation_error' and not calls
    assert response.json()['request_id']==response.headers['X-Request-ID']


@pytest.mark.parametrize('flag,status',[('omit_rises','unavailable'),('omit_sets','partial')])
def test_absent_solar_evidence_has_typed_status(surface,flag,status):
    client,_,_,_,state=surface
    setattr(state,flag,True)
    r=client.post('/v1/muhurta/doshas/day',json=DAY)
    assert r.status_code==200,r.text
    assert r.json()['status']==status and r.json()['unavailable_reasons']


def test_unknown_necessity_and_polar_lagna_stay_unknown(surface):
    client,*_=surface
    r=client.post('/v1/muhurta/doshas/day',json=DAY|{'latitude':70,'policy':{'parihara_profiles':[MC_NECESSARY]}})
    assert r.status_code==200,r.text
    assert r.json()['status']=='partial'
    assert len(r.json()['unavailable_reasons'])==2
    assert all(c['assessment']['findings'][-1]['detected'] is None for c in r.json()['cells'])
    assert any(f['detected'] is True and f['neutralized'] is None for c in r.json()['cells'] for f in c['assessment']['findings'] if f['rule_id']=='yamaghanta_kala')


@pytest.mark.parametrize('exc,status,code',[
    (MuhurtaCoverageError('coverage'),422,'muhurta_date_outside_coverage'),
    (MuhurtaResourceError('reader'),503,'muhurta_resource_unavailable'),
])
def test_resource_and_coverage_envelopes(surface,monkeypatch,exc,status,code):
    client,engine,*_=surface
    def fail(*args,**kwargs):
        raise exc
    monkeypatch.setattr(engine,'muhurta_doshas_for_date',fail)
    r=client.post('/v1/muhurta/doshas/day',json=DAY)
    assert r.status_code==status and r.json()['error_code']==code


def test_solar_root_bracket_must_belong_to_next_civil_date(surface,monkeypatch):
    from moira.daily_panchanga import _civil_bounds,_resolve_timezone
    from types import SimpleNamespace
    client,_,owner,*_=surface
    midnight=_civil_bounds(date(2026,10,10),_resolve_timezone('Asia/Kolkata'))[0]
    monkeypatch.setattr(owner,'_refine',lambda *a:SimpleNamespace(kind='sunrise',jd_ut1=midnight,
        lower_jd_ut1=midnight-.01/86400,upper_jd_ut1=midnight+.01/86400))
    r=client.post('/v1/muhurta/doshas/day',json=DAY)
    assert r.status_code==200 and r.json()['status']=='unavailable'
    assert r.json()['next_sunrise'] is None


def test_exact_solar_roots_remain_available(surface,monkeypatch):
    client,_,owner,*_=surface
    original=owner._convert
    def exact(anchor,kind=None):
        b=original(anchor,kind)
        return None if b is None else replace(b,lower_jd_ut1=b.jd_ut1,upper_jd_ut1=b.jd_ut1)
    monkeypatch.setattr(owner,'_convert',exact)
    r=client.post('/v1/muhurta/doshas/day',json=DAY)
    assert r.status_code==200 and r.json()['status']=='available'


def test_nested_phase_input_is_strict(surface):
    from tests.unit.test_muhurta_dosha import event
    client,_,_,calls,_=surface
    span=asdict(event('nakshatra',3,2451544.5,2451545.5))
    for field,value in [('index',True),('index',27),('kind','yoga')]:
        r=client.post('/v1/muhurta/doshas/direct',json=DIRECT|{'phase_spans':[span|{field:value}]})
        assert r.status_code==422 and not calls


def test_openapi_admits_only_named_profiles_and_typed_results(surface):
    client,*_=surface
    schemas=client.get('/openapi.json').json()['components']['schemas']
    for name in ('DoshaPolicyRequest','DoshaDirectRequest','DoshaDayRequest','DoshaAssessmentResponse','DoshaDayResponse','DoshaPhaseSpanModel'):
        assert schemas[name]['additionalProperties'] is False
    assert len(schemas['DoshaPolicyRequest']['properties']['vishanadi_profile']['enum'])==3
    assert len(schemas['DoshaPolicyRequest']['properties']['gandanta_profile']['enum'])==2
