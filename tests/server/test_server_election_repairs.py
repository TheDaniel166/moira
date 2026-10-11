"""Hostile and boundary HTTP inputs for the four VED-011 repair findings."""
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira._muhurta_marriage_tradition_sources import KP, VV

pytestmark=pytest.mark.loopback


@pytest.fixture
def client(monkeypatch):
    class Engine:
        def marriage_election_for_datetime(self,*args,**kwargs):
            pytest.fail('invalid request reached dated engine')
        def marriage_election_windows(self,*args,**kwargs):
            pytest.fail('invalid request reached window engine')
    monkeypatch.setattr('moira_server.app.create_engine',lambda config:Engine())
    with TestClient(create_app(ServerConfig(require_kernel_ready=False,prewarm_enabled=False))) as value:
        yield value


def point(jd):
    return dict(kind='parent',jd_ut1=jd,lower_jd_ut1=jd,upper_jd_ut1=jd)


def parent(kind,index,a,b):
    return dict(kind=kind,index=index,interval=dict(start=point(a),end=point(b)))


@pytest.mark.parametrize('kind,jd,sun,moon,indices,boundary',[
    ('tithi',100.,0.,36.5,(1,2,3),99.8),
    ('nakshatra',99.94,10.,14.,(26,0,1),99.925),
])
def test_http_retains_carryover_and_missing_history(client,kind,jd,sun,moon,indices,boundary):
    body={'policy':{'ritual_anchor':'vows','regional_tradition':'all_regions','profile':KP},
          'evidence':{'jd_ut1':jd,'planets':[{'planet':'Sun','sidereal_longitude':sun},
              {'planet':'Moon','sidereal_longitude':moon}],
              'phase_spans':[parent(kind,indices[0],98.,99.05),parent(kind,indices[1],99.05,boundary),
                             parent(kind,indices[2],boundary,100.75)]}}
    response=client.post('/v1/muhurta/marriage/direct',json=body)
    assert response.status_code==200,response.text
    finding=next(f for f in response.json()['astronomical_findings'] if f['rule_id']=='kp.'+kind+'_thyajyam')
    assert finding['detected'] is True and finding['coverage_complete'] is True
    body['evidence']['phase_spans']=body['evidence']['phase_spans'][-1:]
    response=client.post('/v1/muhurta/marriage/direct',json=body)
    assert response.status_code==200,response.text
    finding=next(f for f in response.json()['astronomical_findings'] if f['rule_id']=='kp.'+kind+'_thyajyam')
    assert finding['detected'] is None and finding['coverage_complete'] is False


def angular_context(planet):
    orb=11. if planet=='Jupiter' else 10.
    def event(jd,role):
        before,after=(orb-.1,orb+.1) if role=='appearance' else (orb+.1,orb-.1)
        def sample(time,value):
            return dict(jd_ut1=time,planet=planet,sun_sidereal_longitude=0.,
                        planet_sidereal_longitude=value,longitude_speed=1.)
        return dict(role=role,side='west',boundary=dict(kind='orb',jd_ut1=jd,
            lower_jd_ut1=jd-.001,upper_jd_ut1=jd+.001),
            before=sample(jd-.001,before),after=sample(jd+.001,after))
    return dict(previous_event=event(80.,'appearance'),next_event=event(150.,'disappearance'))


@pytest.mark.parametrize('planet',['Jupiter','Venus'])
@pytest.mark.parametrize('family,policy,context',[
    ('vastu',{'purpose':'first_entry'},{'facing':'east'}),
    ('travel',{'profile':'mc_maniprabha_1948_ordinary_land.v1'},
     {'traveller_id':'a','anchor':'leave_residence','direction':'north'}),
    ('business',{'purpose':'purchase'},{'actor_id':'buyer','actor_role':'buyer','anchor':'acceptance_exchange'}),
])
def test_foreign_apparition_rejected_by_engine_and_http(client,family,policy,context,planet):
    import importlib
    from moira.muhurta_election import ElectionEvidence
    from moira_server.models.muhurta_marriage import LongitudeApparitionModel
    raw=angular_context(planet)
    kwargs={planet.lower()+'_apparition':LongitudeApparitionModel.model_validate(raw).to_engine()}
    owner=importlib.import_module('moira.muhurta_'+family)
    prefix=family.title()
    with pytest.raises(ValueError,match='apparition geometry'):
        getattr(owner,'assess_'+family+'_election')(ElectionEvidence(100.,**kwargs),
            policy=getattr(owner,prefix+'ElectionPolicy')(**policy),
            context=getattr(owner,prefix+'ElectionContext')(**context))
    response=client.post('/v1/muhurta/'+family+'/direct',json=dict(policy=policy,context=context,
        evidence={'jd_ut1':100.,planet.lower()+'_apparition':raw}))
    assert response.status_code==422,response.text
    assert response.json()['error_code']=='validation_error'
    # The same evidence remains legal in its owning KP marriage profile.
    response=client.post('/v1/muhurta/marriage/direct',json=dict(
        policy={'ritual_anchor':'vows','regional_tradition':'all_regions','profile':KP},
        evidence={'jd_ut1':100.,planet.lower()+'_apparition':raw}))
    assert response.status_code==200,response.text


@pytest.mark.parametrize('kind,sun,moon',[
    ('solar',(150000000.,0.,0.),(150000000.,0.,0.)),
    ('solar',(150000000.,0.,0.),(1e308,0.,0.)),
    ('lunar_umbral',(700000.,0.,0.),(-1.3e154,0.,0.)),
])
def test_degenerate_shadow_is_422_instead_of_500(client,kind,sun,moon):
    def sample(jd):
        return dict(jd_ut1=jd,kind=kind,sun_xyz_km=sun,
                    moon_xyz_km=moon,moon_sidereal_longitude=20.)
    def contact(a,b,role):
        return dict(boundary=dict(kind='contact',jd_ut1=(a+b)/2,lower_jd_ut1=a,upper_jd_ut1=b),
                    before=sample(a),after=sample(b),role=role)
    body={'policy':{'ritual_anchor':'vows','regional_tradition':'all_regions','profile':VV},
          'evidence':{'jd_ut1':100.,'star_history':{
              'extent':{'start_jd_ut1':90.,'end_jd_ut1':110.},'planets':[],'passages':[],
              'tradition_profile':VV,'additional_extent':{'start_jd_ut1':95.,'end_jd_ut1':105.},
              'declination_extent':{'start_jd_ut1':97.,'end_jd_ut1':103.},
              'eclipse_intervals':[{'start':contact(99.,99.001,'start'),'end':contact(99.1,99.101,'end')}]}}}
    response=client.post('/v1/muhurta/marriage/direct',json=body)
    assert response.status_code==422,response.text
    assert response.json()['error_code']=='validation_error'


@pytest.mark.parametrize('operation,extra,limits,kind',[
    ('datetime',{'dt':'2026-10-10T12:00:00Z'},{'max_history_days':65},'history_days'),
    ('datetime',{'dt':'2026-10-10T12:00:00Z'},{'max_history_days':72},'history_days'),
    ('windows',{'start':'2026-10-10T12:00:00Z','end':'2026-10-12T12:00:00Z'},
     {'max_history_days':73},'history_days'),
    ('windows',{'start':'2026-10-10T12:00:00Z','end':'2026-10-28T12:00:00Z'},
     {'max_history_days':90,'max_range_days':31},'range_days'),
])
def test_vv_budget_rejected_before_route_engine(client,operation,extra,limits,kind):
    body=dict(latitude=28.6,longitude=77.2,timezone='Asia/Kolkata',limits=limits,
              policy={'ritual_anchor':'vows','regional_tradition':'all_regions','profile':VV},**extra)
    response=client.post('/v1/muhurta/marriage/'+operation,json=body)
    assert response.status_code==422,response.text
    assert response.json()['error_code']=='marriage_search_budget'
    assert response.json()['details']['limit_kind']==kind
    assert response.json()['details']['stage']=='additional_tradition_preflight'


def test_valid_vv_window_budget_is_admitted_without_resources():
    from moira_server.models.muhurta_marriage import MarriageWindowsRequest
    payload=dict(start='2026-10-10T12:00:00Z',end='2026-10-12T12:00:00Z',
        latitude=28.6,longitude=77.2,timezone='Asia/Kolkata',limits={'max_history_days':75},
        policy={'ritual_anchor':'vows','regional_tradition':'all_regions','profile':VV})
    assert MarriageWindowsRequest.model_validate(deepcopy(payload)).limits.max_history_days==75
