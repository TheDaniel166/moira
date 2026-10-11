"""Real serving evidence for the VED-011 carryover repair; no saved oracle."""
import json
import os
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from moira.muhurta_marriage import MarriageElectionEvidence, MarriageElectionPolicy, MarriagePlanet, assess_marriage_election
from moira.muhurta_marriage_dated import _Context
from moira._muhurta_marriage_search import WorkMeter, MarriageSearchLimits, borrow_marriage_reader
from moira._muhurta_marriage_tradition_sources import KP
from moira._muhurta_marriage_windows import _derived_boundaries
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.serializers.muhurta_marriage import serialize_marriage_windows
from moira_server.models.muhurta_marriage import MarriageEvidenceModel

pytestmark=[pytest.mark.integration,pytest.mark.requires_ephemeris,pytest.mark.loopback]


def test_real_phase_context_retains_both_missed_tithi_intervals(moira_engine):
    # These epochs identify the review reproductions. Recompute the parents
    # and all sidereal longitudes with the current serving reader.
    policy=MarriageElectionPolicy('vows','all_regions',profile=KP)
    meter=WorkMeter(MarriageSearchLimits())
    with borrow_marriage_reader(moira_engine._reader,meter) as reader:
        ctx=_Context(reader,meter,28.6,77.2,ZoneInfo('Asia/Kolkata'),'Asia/Kolkata',policy)
        for jd in (2461091.900740734,2461121.322320754):
            spans,*_=ctx.phase_context(jd)
            previous=next(s for s in spans if s.kind=='tithi' and s.index==2)
            assert previous.interval.end.upper_jd_ut1<jd
            assert previous.interval.start.upper_jd_ut1+55/60<jd<previous.interval.start.lower_jd_ut1+59/60
            planets=tuple(MarriagePlanet(p,ctx.longitude_at(p,jd),ctx.body(p,jd).speed) for p in ('Sun','Moon'))
            evidence=MarriageElectionEvidence(jd,planets,ctx.lagna(jd),phase_spans=spans)
            result=assess_marriage_election(evidence,policy=policy)
            f=next(f for f in result.astronomical_findings if f.rule_id=='kp.tithi_thyajyam')
            assert f.detected is True and f.coverage_complete
            assert any(b.kind.startswith('kp.tithi_thyajyam') and b.jd_ut1>jd for b in _derived_boundaries(result))
        assert not ctx.reasons


@pytest.mark.slow
def test_real_kp_http_window_preserves_carryover_release(planetary_kernel_path,monkeypatch):
    config=ServerConfig(kernel_path=str(planetary_kernel_path),prewarm_enabled=False,require_kernel_ready=True)
    with TestClient(create_app(config)) as client:
        engine=client.app.state.engine
        captured=[]
        original=engine.marriage_election_windows
        def capture(*args,**kwargs):
            value=original(*args,**kwargs)
            captured.append(value)
            return value
        monkeypatch.setattr(engine,'marriage_election_windows',capture)
        body={'start':'2026-02-20T09:07:00Z','end':'2026-02-20T10:07:00Z',
              'latitude':28.6,'longitude':77.2,'timezone':'Asia/Kolkata',
              'policy':{'ritual_anchor':'vows','regional_tradition':'all_regions','profile':KP},
              'limits':{'max_history_days':4096,'max_output_bytes':32000000}}
        response=client.post('/v1/muhurta/marriage/windows',json=body)
        assert response.status_code==200,response.text
        result=captured[-1]
        assert response.json()==serialize_marriage_windows(result).model_dump(mode='json')
        assert result.search_receipt.crossing_completeness=='complete_under_declared_arithmetic_model'
        assert all(cell.constancy_certified for cell in result.cells)
        releases=[b for b in result.transition_bands if 'kp.tithi_thyajyam' in b.kind]
        assert releases
        assert all(result.at(b.jd_ut1) is None for b in releases)
        states=[]
        meter=WorkMeter(MarriageSearchLimits())
        with borrow_marriage_reader(engine._reader,meter) as reader:
            ctx=_Context(reader,meter,28.6,77.2,ZoneInfo('Asia/Kolkata'),'Asia/Kolkata',result.policy)
            for i,cell in enumerate(result.cells):
                assessment=result.assessment(i)
                f=next(f for f in assessment.astronomical_findings if f.rule_id=='kp.tithi_thyajyam')
                assert f.coverage_complete
                states.append(f.detected)
                # Independently recompute the phase evidence at two interior
                # epochs; constancy cannot be inferred from midpoint parity.
                for fraction in (.1,.9):
                    jd=cell.interval.start.upper_jd_ut1+(cell.interval.end.lower_jd_ut1-cell.interval.start.upper_jd_ut1)*fraction
                    spans,*_=ctx.phase_context(jd)
                    planets=tuple(MarriagePlanet(p,ctx.longitude_at(p,jd),ctx.body(p,jd).speed) for p in ('Sun','Moon'))
                    raw=MarriageElectionEvidence(jd,planets,ctx.lagna(jd),phase_spans=spans)
                    instant=assess_marriage_election(raw,policy=result.policy)
                    instant_f=next(f for f in instant.astronomical_findings if f.rule_id=='kp.tithi_thyajyam')
                    assert instant_f.detected is f.detected and instant_f.coverage_complete
            assert not ctx.reasons
        assert True in states and False in states
        # Resolve a full retained witness into the actual public direct route.
        assessment=result.assessment(states.index(True))
        from moira_server.serializers.muhurta_marriage import serialize_marriage_assessment
        raw=serialize_marriage_assessment(assessment).model_dump(mode='json')['evidence']
        direct=client.post('/v1/muhurta/marriage/direct',json={'policy':body['policy'],
            'evidence':{key:raw[key] for key in MarriageEvidenceModel.model_fields}})
        assert direct.status_code==200,direct.text
        direct_f=next(f for f in direct.json()['astronomical_findings'] if f['rule_id']=='kp.tithi_thyajyam')
        assert direct_f['detected'] is True and direct_f['coverage_complete'] is True
        folder=os.environ.get('MOIRA_MARRIAGE_RECEIPT_DIR')
        if folder:
            path=Path(folder)
            path.mkdir(parents=True,exist_ok=True)
            (path/'kp-carryover-windows.json').write_text(json.dumps(response.json(),indent=2),encoding='utf-8')
            (path/'kp-carryover-direct.json').write_text(json.dumps(direct.json(),indent=2),encoding='utf-8')
