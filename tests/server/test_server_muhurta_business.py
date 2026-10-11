"""Commerce HTTP parity and role/anchor admission without a kernel."""
from copy import deepcopy
import pytest
from fastapi.testclient import TestClient
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira.muhurta_business import compare_business_elections
from moira.muhurta_election import ElectionEvidence,ElectionPlanet
from moira_server.models.muhurta_business import BusinessComparisonResponse
from moira_server.serializers.muhurta_election import election_values

pytestmark=pytest.mark.loopback
DIRECT={'evidence':{'jd_ut1':2460000.,'planets':[{'planet':'Moon','sidereal_longitude':5.}]},
        'policy':{'purpose':'purchase'},'context':{'actor_id':'a','actor_role':'buyer','anchor':'acceptance_exchange'}}


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr('moira_server.app.create_engine',lambda config:object())
    with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as client:
        yield client


def test_discovery_direct_and_two_party_comparison(client):
    r=client.get('/v1/muhurta/business/catalogue')
    assert r.status_code==200,r.text
    assert r.json()['purposes']==['purchase','sale','first_opening_for_trade']
    r=client.post('/v1/muhurta/business/direct',json=DIRECT)
    assert r.status_code==200,r.text
    assert r.json()['astronomical']['status']=='passes_selected_profile'
    r=client.post('/v1/muhurta/business/compare',json={'evidence':DIRECT['evidence'],'buyer_id':'a','seller_id':'b'})
    assert r.status_code==200,r.text
    expected=compare_business_elections(ElectionEvidence(2460000.,(ElectionPlanet('Moon',5.),)),buyer_id='a',seller_id='b')
    assert r.json()==BusinessComparisonResponse(**election_values(expected)).model_dump(mode='json')


@pytest.mark.parametrize('owner,name,value',[
    ('policy','purpose','incorporation'),('policy','profile','universal_business'),('policy','solver_tolerance_seconds',True),
    ('context','actor_role','seller'),('context','anchor','payment_settlement'),('context','actor_id',' '),
    ('context','counterparty_id','a'),('context','participant',{'participant_id':'a'}),
    ('evidence','jd_ut1',True),('evidence','source_receipt','certified'),
])
def test_hostile_role_anchor_and_evidence_rejected(client,owner,name,value):
    body=deepcopy(DIRECT)
    body[owner][name]=value
    assert client.post('/v1/muhurta/business/direct',json=body).status_code==422


def test_two_roles_cannot_be_the_same_actor(client):
    assert client.post('/v1/muhurta/business/compare',json={'evidence':DIRECT['evidence'],'buyer_id':'a','seller_id':'a'}).status_code==422
