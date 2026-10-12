"""Actual HTTP parity, strict admission, exact transport and error contracts."""
from datetime import datetime,timezone
from fractions import Fraction as F
import json
import math
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from moira import Moira
from moira.kalachakra import (
    KalachakraSeed, KalachakraEpoch, KalachakraProjection, KalachakraResourceError,
    KalachakraCoverageError, KalachakraInvariantError, kalachakra_sequence,
    current_kalachakra_periods,
)
from moira.kalachakra_policy import PROFILE_ID
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.serializers.kalachakra import serialize_sequence, serialize_current
from tests.unit.test_kalachakra_sources import DATA
from tests.unit.test_kalachakra_astronomy import fake_astronomy as _fake_astronomy_fixture

fake_astronomy = _fake_astronomy_fixture

pytestmark = pytest.mark.loopback
BASE = '/v1/dasha/kalachakra'


@pytest.fixture
def client(monkeypatch):
    stub = SimpleNamespace(_reader=object())
    stub.kalachakra_sequence = lambda *a,**k: Moira.kalachakra_sequence(stub,*a,**k)
    stub.kalachakra_for_datetime = lambda *a,**k: Moira.kalachakra_for_datetime(stub,*a,**k)
    monkeypatch.setattr('moira_server.app.create_engine',lambda config:stub)
    with TestClient(create_app(ServerConfig(prewarm_enabled=False)),raise_server_exceptions=False) as c:
        yield c


def payload(lon=45.8,projected=False):
    result = {'profile_id':PROFILE_ID,'seed':{'basis':'sidereal','moon_sidereal_lon':lon}}
    if projected:
        result.update(birth_epoch={'kind':'jd_utc','value':2451545},projection={'year_basis':'savana_360'})
    return result


@pytest.mark.parametrize('case',DATA['balances'],ids=lambda c:c['id'])
def test_source_fixture_direct_http_parity(client,case):
    d,m,s = case['dms']
    lon = float(F(d)+F(m,60)+F(s,3600))
    expected = kalachakra_sequence(KalachakraSeed('sidereal',lon),profile_id=PROFILE_ID)
    response = client.post(BASE+'/sequence',json=payload(lon))
    assert response.status_code==200,response.text
    body = response.json()
    assert body == serialize_sequence(expected).model_dump(mode='json')
    assert body['birth']['birth_row_position']==case['position']
    r = body['birth']['birth_md_remaining_years']
    assert F(int(r['numerator']),int(r['denominator']))==expected.birth.birth_md_remaining_years
    assert body['projection_status']=='not_requested'
    assert body['eligibility_status']=='not_evaluated'


def test_projection_and_current_endpoint_states(client):
    request = payload(projected=True)
    response = client.post(BASE+'/sequence',json=request)
    assert response.status_code==200,response.text
    schedule = response.json()
    seed = KalachakraSeed('sidereal',45.8)
    expected = kalachakra_sequence(seed,profile_id=PROFILE_ID,birth_epoch=KalachakraEpoch('jd_utc',2451545),projection=KalachakraProjection('savana_360'))
    for query in (2451544,2451545,schedule['periods'][0]['visible_dates']['end_jd_utc'],schedule['coverage_dates']['end_jd_utc']):
        result = client.post(BASE+'/current',json={**request,'query_epoch':{'kind':'jd_utc','value':query}})
        assert result.status_code==200,result.text
        wanted = current_kalachakra_periods(expected,KalachakraEpoch('jd_utc',query))
        assert result.json()==serialize_current(wanted).model_dump(mode='json')


@pytest.mark.parametrize('bad',[True,False,'34.5',None,-1,360,float('nan'),float('inf')])
def test_bad_angles(client,bad):
    r = client.post(BASE+'/sequence',content=json.dumps(payload(bad)),headers={'Content-Type':'application/json'})
    assert r.status_code==422
    assert r.json()['error_code']=='validation_error'


@pytest.mark.parametrize('patch',[
    {'levels':True},{'levels':'2'},{'levels':3},{'levels':0},{'levels':2.0},
    {'profile_id':'candidate_rao_2000_continuous'}, {'profile_id':None},
    {'cycles':2},{'eligibility_bypass':True},{'periods':[]},{'observer_lat':0},
    {'projection':{'year_basis':'tropical_365.2422'}},{'projection':{'year_basis':'savana_360'}},
    {'birth_epoch':{'kind':'jd_utc','value':2451545}},
    {'seed':{'basis':'sidereal','moon_sidereal_lon':12,'ayanamsa_system':'Lahiri'}},
    {'seed':{'basis':'tropical','moon_tropical_lon':12,'ayanamsa_system':'Lahiri'}},
    {'seed':{'basis':'tropical','moon_tropical_lon':12,'ayanamsa_system':'unknown'}},
])
def test_bad_combinations_before_resource_work(client,patch,fake_astronomy):
    r = client.post(BASE+'/sequence',json={**payload(),**patch})
    assert r.status_code==422,r.text
    assert r.json()['error_code']=='validation_error'
    assert sum(fake_astronomy.values())==0


@pytest.mark.parametrize('value',[0,True,'946728000','2000-01-01','2000-01-01T12:00:00',None])
def test_chart_rejects_non_civil_or_naive_timestamps(client,value,fake_astronomy):
    r = client.post(BASE+'/chart/sequence',json={'profile_id':PROFILE_ID,'birth_datetime':value,'ayanamsa_system':'Lahiri'})
    assert r.status_code==422 and sum(fake_astronomy.values())==0


def test_chart_current_derives_once_and_preserves_provenance(client,fake_astronomy):
    request = {'profile_id':PROFILE_ID,'birth_datetime':'2000-01-01T12:00:00Z','ayanamsa_system':'Lahiri',
               'projection':{'year_basis':'savana_360'},'query_epoch':{'kind':'jd_utc','value':2451545}}
    r = client.post(BASE+'/chart/current',json=request)
    assert r.status_code==200,r.text
    assert r.json()['status']=='active' and len(r.json()['active_line'])==2
    assert r.json()['provenance']['input_origin']=='derived_moon'
    assert fake_astronomy=={'binding':1,'moon':1,'ayanamsa':1,'star':0}
    tropical = {'profile_id':PROFILE_ID,'seed':{'basis':'tropical','moon_tropical_lon':57.5,'ayanamsa_system':'Lahiri'},
        'birth_epoch':{'kind':'datetime','value':'2000-01-01T12:00:00Z'}}
    t = client.post(BASE+'/sequence',json=tropical)
    assert t.status_code==200,t.text
    assert t.json()['provenance']['input_origin']=='supplied_tropical'
    assert fake_astronomy['moon']==1 and fake_astronomy['ayanamsa']==2


def test_current_requires_projection_before_astronomy(client,fake_astronomy):
    r = client.post(BASE+'/chart/current',json={'profile_id':PROFILE_ID,
        'birth_datetime':'2000-01-01T12:00:00Z','ayanamsa_system':'Lahiri',
        'query_epoch':{'kind':'jd_utc','value':2451545}})
    assert r.status_code==422 and sum(fake_astronomy.values())==0


@pytest.mark.parametrize('error,status,code',[
    (KalachakraResourceError,503,'kalachakra_resource_unavailable'),
    (KalachakraCoverageError,422,'kalachakra_epoch_out_of_coverage'),
    (KalachakraInvariantError,500,'kalachakra_internal_invariant'),
])
def test_structured_failure_contracts(client,monkeypatch,error,status,code):
    def failure(*args,**kwargs):
        raise error('secret internal path')
    monkeypatch.setattr('moira_server.routers.kalachakra.compute_sequence',failure)
    r = client.post(BASE+'/sequence',json=payload())
    assert r.status_code==status,r.text
    body = r.json()
    assert body['error_code']==code and body['request_id']==r.headers['X-Request-ID']
    assert 'secret' not in r.text


def test_projection_precision_422_keeps_source_valid(client):
    lon = math.nextafter(float(F(7,30)),-math.inf)
    assert client.post(BASE+'/sequence',json=payload(lon)).status_code==200
    r = client.post(BASE+'/sequence',json=payload(lon,True))
    assert r.status_code==422
    assert r.json()['error_code']=='kalachakra_projection_unrepresentable'


def test_corrupt_engine_result_is_internal_not_caller_error(client,monkeypatch):
    result = kalachakra_sequence(KalachakraSeed('sidereal',45.8),profile_id=PROFILE_ID)
    object.__setattr__(result.periods[0],'ruler','Rahu')
    monkeypatch.setattr('moira_server.routers.kalachakra.compute_sequence',lambda *args:result)
    r = client.post(BASE+'/sequence',json=payload())
    assert r.status_code==500 and r.json()['error_code']=='kalachakra_internal_invariant'


def test_invalid_generated_moon_is_internal_failure(client,fake_astronomy,monkeypatch):
    monkeypatch.setattr('moira._kalachakra_astronomy.planet_at',lambda *a,**k:SimpleNamespace(longitude=float('nan')))
    r = client.post(BASE+'/chart/sequence',json={'profile_id':PROFILE_ID,
        'birth_datetime':'2000-01-01T12:00:00Z','ayanamsa_system':'Lahiri'})
    assert r.status_code==500 and r.json()['error_code']=='kalachakra_internal_invariant'


def test_generated_index_failure_is_internal_not_resource_unavailable(client,fake_astronomy,monkeypatch):
    def corrupt(*args,**kwargs):
        raise IndexError('private internal position buffer')
    monkeypatch.setattr('moira._kalachakra_astronomy.planet_at',corrupt)
    r = client.post(BASE+'/chart/sequence',json={'profile_id':PROFILE_ID,
        'birth_datetime':'2000-01-01T12:00:00Z','ayanamsa_system':'Lahiri'})
    assert r.status_code==500 and r.json()['error_code']=='kalachakra_internal_invariant'
    assert 'private' not in r.text


@pytest.mark.requires_ephemeris
def test_real_kernel_chart_direct_http_parity(monkeypatch,moira_engine):
    monkeypatch.setattr('moira_server.app.create_engine',lambda config:moira_engine)
    with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as c:
        request = {'profile_id':PROFILE_ID,'birth_datetime':'2000-01-01T12:00:00Z','ayanamsa_system':'Lahiri',
                   'projection':{'year_basis':'julian_365.25'}}
        r = c.post(BASE+'/chart/sequence',json=request)
        assert r.status_code==200,r.text
        expected = moira_engine.kalachakra_for_datetime(datetime(2000,1,1,12,tzinfo=timezone.utc),
            profile_id=PROFILE_ID,ayanamsa_system='Lahiri',projection=KalachakraProjection('julian_365.25'))
        assert r.json()==serialize_sequence(expected).model_dump(mode='json')
        p = r.json()['provenance']
        direct = payload(p['moon_sidereal_lon'],True)
        direct['projection']['year_basis']='julian_365.25'
        a = c.post(BASE+'/sequence',json=direct)
        assert a.status_code==200,a.text
        assert a.json()['periods']==r.json()['periods']
        request['birth_datetime']='2000-01-01T07:00:00-05:00'
        assert c.post(BASE+'/chart/sequence',json=request).json()==r.json()
