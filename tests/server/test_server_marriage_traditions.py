"""Additional profiles use the same strict HTTP contract and engine decisions."""
from dataclasses import asdict

import pytest
from fastapi.testclient import TestClient

from moira.muhurta_marriage import MarriageElectionPolicy,MarriageElectionEvidence,assess_marriage_election,marriage_election_catalogue
from moira._muhurta_marriage_tradition_sources import VV,KP
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.serializers.muhurta_marriage import serialize_marriage_assessment,serialize_marriage_catalogue

pytestmark=pytest.mark.loopback


@pytest.mark.parametrize('profile',[VV,KP])
def test_additional_direct_and_catalogue_remain_kernel_free(profile):
    policy=MarriageElectionPolicy('vows','all_regions',profile=profile)
    with TestClient(create_app(ServerConfig(require_kernel_ready=False,prewarm_enabled=False))) as client:
        request={'policy':{'ritual_anchor':'vows','regional_tradition':'all_regions','profile':profile},'evidence':{'jd_ut1':100.}}
        response=client.post('/v1/muhurta/marriage/direct',json=request)
        assert response.status_code==200,response.text
        expected=assess_marriage_election(MarriageElectionEvidence(100.),policy=policy)
        assert response.json()==serialize_marriage_assessment(expected).model_dump(mode='json')
        cat=client.get('/v1/muhurta/marriage/catalogue')
        assert cat.status_code==200
        assert cat.json()==serialize_marriage_catalogue(marriage_election_catalogue()).model_dump(mode='json')
        request['policy']['remedies']=['mc68_own_or_exalted_luminaries']
        assert client.post('/v1/muhurta/marriage/direct',json=request).status_code==422


def test_http_rejects_cross_profile_extra_history_and_forged_completion():
    from moira import MarriageTraditionHistory,MarriageExtent
    history=MarriageTraditionHistory(MarriageExtent(90.,110.),(),(),tradition_profile=VV,
        additional_extent=MarriageExtent(95.,105.),declination_extent=MarriageExtent(97.,103.))
    request={'policy':{'ritual_anchor':'vows','regional_tradition':'all_regions','profile':KP},
        'evidence':{'jd_ut1':100.,'star_history':asdict(history)}}
    with TestClient(create_app(ServerConfig(require_kernel_ready=False,prewarm_enabled=False))) as client:
        assert client.post('/v1/muhurta/marriage/direct',json=request).status_code==422
        request['policy']['profile']=VV
        reply=client.post('/v1/muhurta/marriage/direct',json=request)
        assert reply.status_code==200,reply.text
        request['evidence']['star_history']['complete']=True
        assert client.post('/v1/muhurta/marriage/direct',json=request).status_code==422
