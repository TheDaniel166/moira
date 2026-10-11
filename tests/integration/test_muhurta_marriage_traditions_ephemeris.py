"""Actual VV/KP serving HTTP admission, including lossless direct projection."""
import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from moira._muhurta_marriage_tradition_sources import VV,KP
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.serializers.muhurta_marriage import serialize_marriage_snapshot,serialize_marriage_windows
from moira_server.models.muhurta_marriage import MarriageEvidenceModel,VivahaVrindavanaEvidenceModel

pytestmark=[pytest.mark.integration,pytest.mark.requires_ephemeris,pytest.mark.loopback,pytest.mark.slow]


def save(name,value):
    folder=os.environ.get('MOIRA_MARRIAGE_RECEIPT_DIR')
    if folder:
        path=Path(folder)
        path.mkdir(parents=True,exist_ok=True)
        (path/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')


@pytest.mark.parametrize('profile',[VV,KP])
def test_real_tradition_http_instant_and_windows(planetary_kernel_path,monkeypatch,profile):
    config=ServerConfig(kernel_path=str(planetary_kernel_path),prewarm_enabled=False,require_kernel_ready=True)
    with TestClient(create_app(config)) as client:
        engine=client.app.state.engine
        captured=[]
        for name in ('marriage_election_for_datetime','marriage_election_windows'):
            original=getattr(engine,name)
            def capture(*a,_original=original,**kw):
                result=_original(*a,**kw)
                captured.append(result)
                return result
            monkeypatch.setattr(engine,name,capture)
        common={'latitude':28.6,'longitude':77.2,'timezone':'Asia/Kolkata',
            'policy':{'ritual_anchor':'declared vows','regional_tradition':'all_regions','profile':profile},
            'limits':{'max_history_days':4096}}
        response=client.post('/v1/muhurta/marriage/datetime',json=dict(common,dt='2026-10-10T12:00:00Z'))
        assert response.status_code==200,response.text
        instant=response.json()
        save(profile+'-instant',instant)
        assert instant==serialize_marriage_snapshot(captured[-1]).model_dump(mode='json')
        assert instant['search_receipt']['crossing_completeness']=='complete_under_declared_arithmetic_model'
        raw=instant['assessment']['evidence']
        cls=VivahaVrindavanaEvidenceModel if profile==VV else MarriageEvidenceModel
        direct_input={key:raw[key] for key in cls.model_fields}
        direct=client.post('/v1/muhurta/marriage/direct',json={'policy':common['policy'],'evidence':direct_input})
        assert direct.status_code==200,direct.text
        for layer in ('astronomical_findings','personal_findings','composition_findings'):
            assert direct.json()[layer]==instant['assessment'][layer]
        response=client.post('/v1/muhurta/marriage/windows',json=dict(common,start='2026-10-10T12:00:00Z',end='2026-10-10T12:30:00Z'))
        assert response.status_code==200,response.text
        result=captured[-1]
        payload=response.json()
        save(profile+'-windows',payload)
        assert payload==serialize_marriage_windows(result).model_dump(mode='json')
        assert result.search_receipt.crossing_completeness=='complete_under_declared_arithmetic_model'
        assert len(result.cells)>1 and all(c.constancy_certified for c in result.cells)
        assert any('lagna_discrete' in b.kind for b in result.transition_bands)
        if profile==VV:
            assert any('vv_bhava_' in b.kind for b in result.transition_bands)
        for i,cell in enumerate(result.cells):
            assert result.at(cell.witness.jd_ut1)==result.assessment(i)
