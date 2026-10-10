"""Strict HTTP contracts, canonical projection, missing-data and error semantics."""
from datetime import date
from dataclasses import replace
from types import SimpleNamespace
import json
from fastapi.testclient import TestClient
import pytest
from moira import Moira, PanchangaShuddhiPolicy, panchanga_shuddhi_from_longitudes, panchanga_shuddhi_catalogue
from moira.muhurta_search import MuhurtaCoverageError, MuhurtaResourceError
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.serializers.panchanga_shuddhi import serialize_shuddhi_assessment, serialize_shuddhi_catalogue, serialize_shuddhi_day
from tests.panchanga_shuddhi_support import install_shuddhi_sky

pytestmark=pytest.mark.loopback
DIRECT={'sun_sidereal_longitude':0,'moon_sidereal_longitude':45,'natal_nakshatra_index':0,'weekday':5,'lagna_sidereal_longitude':10}
DAY={'local_date':'2026-10-09','latitude':20,'longitude':80,'timezone':'Asia/Kolkata','natal_nakshatra_index':0}


@pytest.fixture
def surface(monkeypatch):
    owner,reader,calls,state=install_shuddhi_sky(monkeypatch)
    class Engine:
        _reader=reader
        panchanga_shuddhi_for_date=Moira.panchanga_shuddhi_for_date
    engine=Engine()
    monkeypatch.setattr('moira_server.app.create_engine',lambda config:engine)
    with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as client:
        yield client,engine,owner,calls,state


def test_discovery_and_direct_do_not_touch_ephemeris(surface):
    client,_,_,calls,_=surface
    r=client.get('/v1/muhurta/shuddhi/catalogue')
    assert r.status_code==200
    assert r.json()==serialize_shuddhi_catalogue(panchanga_shuddhi_catalogue()).model_dump(mode='json')
    r=client.post('/v1/muhurta/shuddhi/direct',json=DIRECT)
    assert r.status_code==200,r.text
    assert r.json()==serialize_shuddhi_assessment(panchanga_shuddhi_from_longitudes(**DIRECT)).model_dump(mode='json')
    assert calls==[]


@pytest.mark.parametrize('profile',['mc_gochara_13_quarters.v1','ps_sastri_scientific_273_navaka.v1'])
def test_dated_canonical_parity_and_changing_lagna(surface,profile):
    client,engine,_,_,_=surface
    body=DAY|{'policy':{'tara_profile':profile}}
    r=client.post('/v1/muhurta/shuddhi/day',json=body)
    assert r.status_code==200,r.text
    result=engine.panchanga_shuddhi_for_date(date(2026,10,9),20,80,timezone='Asia/Kolkata',
        natal_nakshatra_index=0,policy=PanchangaShuddhiPolicy(tara_profile=profile))
    assert r.json()==serialize_shuddhi_day(result).model_dump(mode='json')
    assert result.status=='available' and len({c.assessment.values.panchaka.lagna_number for c in result.cells})==12
    for band in result.transition_bands:
        assert result.at(band.jd_ut1) is None


@pytest.mark.parametrize('kind,bad',[
    ('direct',{'weekday':True}),('direct',{'weekday':1.0}),('direct',{'weekday':'1'}),
    ('direct',{'moon_sidereal_longitude':True}),('direct',{'moon_sidereal_longitude':float('nan')}),
    ('direct',{'moon_sidereal_longitude':10**1000}),('direct',{'lagna_sidereal_longitude':360}),
    ('direct',{'is_daytime':1}),('direct',{'natal_nakshatra_index':27}),('direct',{'extra':1}),
    ('direct',{'policy':{'tara_profile':'combined'}}),('direct',{'policy':{'bhadra_clock':'fixed'}}),
    ('direct',{'policy':{'ayanamsa_system':'unknown'}}),('direct',{'policy':{'solver_tolerance_seconds':True}}),
    ('day',{'local_date':'20261009'}),('day',{'local_date':0}),('day',{'latitude':90}),
    ('day',{'timezone':'Mars/Unknown'}),('day',{'longitude':'80'}),('day',{'natal_nakshatra_index':True}),
    ('day',{'local_date':'2011-12-30','timezone':'Pacific/Apia'}),
])
def test_preflight_rejects_before_astronomy(surface,kind,bad):
    client,_,_,calls,_=surface
    r=client.post('/v1/muhurta/shuddhi/'+kind,content=json.dumps((DIRECT if kind=='direct' else DAY)|bad),headers={'Content-Type':'application/json'})
    assert r.status_code==422,r.text
    assert r.json()['error_code']=='validation_error' and not calls
    assert r.json()['request_id']==r.headers['X-Request-ID']


@pytest.mark.parametrize('flag,status',[('omit_rises','unavailable'),('omit_sets','partial')])
def test_missing_solar_components(surface,flag,status):
    client,_,_,_,state=surface
    setattr(state,flag,True)
    r=client.post('/v1/muhurta/shuddhi/day',json=DAY)
    assert r.status_code==200,r.text
    assert r.json()['status']==status


def test_partial_natal_and_polar_lagna(surface):
    client,_,_,_,_=surface
    r=client.post('/v1/muhurta/shuddhi/day',json=DAY|{'latitude':70,'natal_nakshatra_index':None})
    assert r.status_code==200,r.text
    assert r.json()['status']=='partial'
    assert len(r.json()['unavailable_reasons'])==2
    assert all(c['assessment']['values']['panchaka'] is None for c in r.json()['cells'])


def test_exact_solar_roots_are_available(surface,monkeypatch):
    client,_,owner,_,_=surface
    original=owner._convert
    def exact(anchor,kind=None):
        b=original(anchor,kind)
        return None if b is None else replace(b,lower_jd_ut1=b.jd_ut1,upper_jd_ut1=b.jd_ut1)
    monkeypatch.setattr(owner,'_convert',exact)
    r=client.post('/v1/muhurta/shuddhi/day',json=DAY)
    assert r.status_code==200,r.text
    assert r.json()['status']=='available'
    assert r.json()['sunset']['lower_jd_ut1']==r.json()['sunset']['upper_jd_ut1']


def test_next_sunrise_band_cannot_cross_civil_ownership(surface,monkeypatch):
    from moira.daily_panchanga import _civil_bounds, _resolve_timezone
    client,_,owner,_,_=surface
    midnight=_civil_bounds(date(2026,10,10),_resolve_timezone('Asia/Kolkata'))[0]
    monkeypatch.setattr(owner,'_refine',lambda *a:SimpleNamespace(kind='sunrise',jd_ut1=midnight,
        lower_jd_ut1=midnight-.01/86400,upper_jd_ut1=midnight+.01/86400))
    r=client.post('/v1/muhurta/shuddhi/day',json=DAY)
    assert r.status_code==200,r.text
    assert r.json()['status']=='unavailable' and r.json()['next_sunrise'] is None


@pytest.mark.parametrize('exc,status,code',[(MuhurtaCoverageError('coverage'),422,'muhurta_date_outside_coverage'),(MuhurtaResourceError('reader'),503,'muhurta_resource_unavailable')])
def test_error_envelopes(surface,monkeypatch,exc,status,code):
    client,engine,_,_,_=surface
    def fail(*args,**kwargs):
        raise exc
    monkeypatch.setattr(engine,'panchanga_shuddhi_for_date',fail)
    r=client.post('/v1/muhurta/shuddhi/day',json=DAY)
    assert r.status_code==status and r.json()['error_code']==code


def test_openapi_strict_typed_contract(surface):
    client,*_=surface
    schema=client.get('/openapi.json').json()
    for name in ('ShuddhiDirectRequest','ShuddhiDayRequest','ShuddhiPolicyRequest','ShuddhiAssessmentResponse','ShuddhiDayResponse'):
        assert schema['components']['schemas'][name]['additionalProperties'] is False
    assert len(schema['components']['schemas']['ShuddhiPolicyRequest']['properties']['tara_profile']['enum'])==2
