"""Rao discovery, actual HTTP parity, strict admission and profile isolation."""
from fractions import Fraction as F
from types import SimpleNamespace
import math
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError
from moira.kalachakra import (
    KalachakraSeed,KalachakraEpoch,KalachakraProjection,kalachakra_sequence,
    current_kalachakra_periods,
)
from moira.kalachakra_policy import PROFILE_ID,RAO_PROFILE_ID
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.kalachakra import KalachakraSequenceResponse
from moira_server.serializers.kalachakra import serialize_sequence,serialize_current
from tests.server.test_server_kalachakra import client as _client_fixture
from tests.unit.test_kalachakra_astronomy import fake_astronomy as _astronomy_fixture
from tests.unit.test_kalachakra_rao_sources import DATA,SIGNS,GATI_CONTEXTS

client = _client_fixture
fake_astronomy = _astronomy_fixture
pytestmark = pytest.mark.loopback
BASE = '/v1/dasha/kalachakra'


def payload(lon=45.8,projected=False):
    body = {'profile_id':RAO_PROFILE_ID,'seed':{'basis':'sidereal','moon_sidereal_lon':lon}}
    if projected:
        body.update(birth_epoch={'kind':'jd_utc','value':2451545},projection={'year_basis':'savana_360'})
    return body


@pytest.mark.parametrize('case',DATA['balances'],ids=lambda c:c['id'])
@pytest.mark.parametrize('levels',[1,2])
def test_source_example_http_parity(client,case,levels):
    d,m,s = case['dms']
    lon = float(F(d)+F(m,60)+F(s,3600))
    response = client.post(BASE+'/sequence',json={**payload(lon),'levels':levels})
    assert response.status_code==200,response.text
    expected = kalachakra_sequence(KalachakraSeed('sidereal',lon),profile_id=RAO_PROFILE_ID,levels=levels)
    body = response.json()
    assert body == serialize_sequence(expected).model_dump(mode='json')
    assert [SIGNS[p['sign_index']] for p in body['periods']] == case['sequence'].split()
    assert body['birth']['deha_jeeva_reference']=='birth_nine_md_window'
    assert body['generated_node_count']==(9 if levels==1 else 90)


@pytest.mark.parametrize('endpoint',['/sequence','/chart/sequence','/current','/chart/current'])
def test_all_calculation_routes_keep_rao_identity(client,fake_astronomy,endpoint):
    if endpoint.startswith('/chart/'):
        request = {'profile_id':RAO_PROFILE_ID,'birth_datetime':'2000-01-01T12:00:00Z',
                   'ayanamsa_system':'Lahiri','projection':{'year_basis':'savana_360'}}
    else:
        request = {**payload(projected=True),
            'seed':{'basis':'tropical','moon_tropical_lon':57.5,'ayanamsa_system':'Lahiri'}}
    if endpoint.endswith('/current'):
        request['query_epoch']={'kind':'jd_utc','value':2451545}
    response = client.post(BASE+endpoint,json=request)
    assert response.status_code==200,response.text
    body=response.json()
    assert body['profile_id']==RAO_PROFILE_ID and body['profile_version']=='ved014.rao2000.1'
    assert body['birth']['row_id'].startswith('R2000/')
    assert body['birth']['deha_jeeva_reference']=='birth_nine_md_window'
    assert fake_astronomy['binding']==fake_astronomy['ayanamsa']==1
    assert fake_astronomy['moon']==int(endpoint.startswith('/chart/'))


def test_current_coverage_and_shared_boundary_http(client):
    req=payload(projected=True)
    schedule=kalachakra_sequence(KalachakraSeed('sidereal',45.8),profile_id=RAO_PROFILE_ID,
        birth_epoch=KalachakraEpoch('jd_utc',2451545),projection=KalachakraProjection('savana_360'))
    for q in (2451544,2451545,schedule.periods[0].visible_dates.end_jd_utc,schedule.coverage_dates.end_jd_utc):
        response=client.post(BASE+'/current',json={**req,'query_epoch':{'kind':'jd_utc','value':q}})
        assert response.status_code==200,response.text
        expected=current_kalachakra_periods(schedule,KalachakraEpoch('jd_utc',q))
        assert response.json()==serialize_current(expected).model_dump(mode='json')


@pytest.mark.parametrize('patch',[
    {'profile_id':'candidate_rao_2000_continuous'},{'profile_id':'rao_2018'},
    {'levels':True},{'levels':3},{'cycles':2},{'continuation':'natal_row_cycle'},
    {'denominator':97},{'eligibility_bypass':True},{'source_ids':['L02']},
    {'seed':{'basis':'sidereal','moon_sidereal_lon':True}},
])
def test_reject_hybrid_or_unsupported_requests_before_astronomy(client,fake_astronomy,patch):
    response=client.post(BASE+'/sequence',json={**payload(),**patch})
    assert response.status_code==422 and response.json()['error_code']=='validation_error'
    assert sum(fake_astronomy.values())==0


@pytest.mark.parametrize('endpoint',['/sequence','/current'])
def test_mixed_profile_engine_result_is_sanitized_500(client,monkeypatch,endpoint):
    r=kalachakra_sequence(KalachakraSeed('sidereal',45.8),profile_id=RAO_PROFILE_ID,
        birth_epoch=KalachakraEpoch('jd_utc',2451545),projection=KalachakraProjection('savana_360'))
    req=payload(projected=True)
    target='compute_sequence'
    if endpoint=='/current':
        r=current_kalachakra_periods(r,KalachakraEpoch('jd_utc',2451545))
        req['query_epoch']={'kind':'jd_utc','value':2451545}
        target='compute_current'
    object.__setattr__(r,'profile_id',PROFILE_ID)
    monkeypatch.setattr('moira_server.routers.kalachakra.'+target,lambda *a,**kw:r)
    response=client.post(BASE+endpoint,json=req)
    assert response.status_code==500,response.text
    assert response.json()['error_code']=='kalachakra_internal_invariant'
    assert response.json()['request_id']==response.headers['X-Request-ID']


def test_strict_response_identity_and_denominator_domain(client):
    body=client.post(BASE+'/sequence',json=payload()).json()
    with pytest.raises(ValidationError):
        KalachakraSequenceResponse.model_validate({**body,'profile_id':PROFILE_ID})
    body['periods'][0]['children'][0]['denominator']=2
    with pytest.raises(ValidationError):
        KalachakraSequenceResponse.model_validate(body)


def test_projection_precision_remains_explicit_422(client):
    lon=math.nextafter(float(F(7,30)),-math.inf)
    assert client.post(BASE+'/sequence',json=payload(lon)).status_code==200
    r=client.post(BASE+'/sequence',json=payload(lon,True))
    assert r.status_code==422 and r.json()['error_code']=='kalachakra_projection_unrepresentable'


def test_catalogue_and_openapi_share_profile_contract(client):
    catalogue=client.get(BASE+'/profiles').json()
    profiles={p['profile_id']:p for p in catalogue['profiles'] if p['selectable']}
    assert set(profiles)=={PROFILE_ID,RAO_PROFILE_ID}
    r=profiles[RAO_PROFILE_ID]
    assert r['continuation']=='continuous_family_rows' and r['row_namespace']=='R2000/'
    assert r['deha_jeeva_reference']=='birth_nine_md_window'
    assert 'R2000_AD' in r['rule_ids'] and 'R2000-01' in r['conflict_ids']
    schema=client.get('/openapi.json').json()['components']['schemas']
    assert set(schema['KalachakraSequenceRequest']['properties']['profile_id']['enum'])==set(profiles)
    assert 97 in schema['PeriodResponse']['properties']['denominator']['enum']
    assert set(schema['BirthResponse']['properties']['deha_jeeva_reference']['enum'])=={'natal_row','birth_nine_md_window'}
    assert schema['KalachakraSequenceResponse']['properties']['generated_node_count']['enum']==[9,90]


@pytest.mark.parametrize('case',GATI_CONTEXTS,ids=lambda c:c['id'])
@pytest.mark.parametrize('levels',[1,2])
@pytest.mark.parametrize('endpoint',['/sequence','/chart/sequence'])
def test_markati_requires_source_context_over_http(client,fake_astronomy,monkeypatch,case,levels,endpoint):
    lon = case['moon_sidereal_lon']
    if endpoint == '/chart/sequence':
        # Keep the real composition owner with controlled Moon/clock inputs.
        monkeypatch.setattr('moira._kalachakra_astronomy.planet_at',
            lambda *a,**kw:SimpleNamespace(longitude=lon+23.8))
        request = {'profile_id':RAO_PROFILE_ID,'birth_datetime':'2000-01-01T12:00:00Z',
            'ayanamsa_system':'Lahiri','projection':{'year_basis':'savana_360'},'levels':levels}
    else:
        request = {**payload(lon,projected=True),'levels':levels}
    response = client.post(BASE+endpoint,json=request)
    assert response.status_code==200,response.text
    ordinal = case['md_source_ordinal']
    paths = [[ordinal]] + ([[0,ordinal]] if levels==2 else [])
    for path in paths:
        edge = next(e for e in response.json()['transitions'] if e['source_path']==path)
        assert [SIGNS[edge['source_sign_index']],SIGNS[edge['destination_sign_index']]] == case['context'].split()[1:3]
        assert edge['rule_id']=='R2000_GATI'
        assert edge['classification']==case['classification']
        assert edge['classification_status']==('classified' if case['classification'] else 'not_classified_by_profile')


def test_forged_ordinary_markati_is_sanitized_500(client,monkeypatch):
    result = kalachakra_sequence(KalachakraSeed('sidereal',0),profile_id=RAO_PROFILE_ID)
    edge = next(e for e in result.transitions if e.source_path==(3,))
    object.__setattr__(edge,'classification','markati')
    object.__setattr__(edge,'classification_status','classified')
    monkeypatch.setattr('moira_server.routers.kalachakra.compute_sequence',lambda *a,**kw:result)
    response = client.post(BASE+'/sequence',json=payload(0))
    assert response.status_code==500,f'unexpected HTTP {response.status_code}'
    assert response.json()['error_code']=='kalachakra_internal_invariant'
    assert response.json()['request_id']==response.headers['X-Request-ID']


@pytest.mark.requires_ephemeris
def test_real_reader_chart_direct_http_parity(monkeypatch,moira_engine):
    monkeypatch.setattr('moira_server.app.create_engine',lambda config:moira_engine)
    with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as c:
        request={'profile_id':RAO_PROFILE_ID,'birth_datetime':'2000-01-01T12:00:00Z',
                 'ayanamsa_system':'Lahiri','projection':{'year_basis':'julian_365.25'}}
        response=c.post(BASE+'/chart/sequence',json=request)
        assert response.status_code==200,response.text
        body=response.json()
        direct={**payload(body['provenance']['moon_sidereal_lon'],True),
                'projection':{'year_basis':'julian_365.25'}}
        supplied=c.post(BASE+'/sequence',json=direct)
        assert supplied.status_code==200 and supplied.json()['periods']==body['periods']
        request['query_epoch']={'kind':'jd_utc','value':2451545}
        current=c.post(BASE+'/chart/current',json=request)
        assert current.status_code==200,current.text
        assert current.json()['status']=='active' and len(current.json()['active_line'])==2
