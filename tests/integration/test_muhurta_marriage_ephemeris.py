"""Required real serving-reader marriage composition and HTTP acceptance.

The full profile intentionally searches supporting history outside the short
request. One HTTP calculation is captured and reused for projection/source
checks; that reuse is not reported as additional independent ephemeris runs.
"""
from dataclasses import asdict,replace
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import time
import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from moira.muhurta_marriage import MarriagePersonalContext,MarriageParticipant,MarriagePlanet,assess_marriage_election
from moira.muhurta_marriage_dated import marriage_election_for_datetime,_Context
from moira._muhurta_marriage_search import MarriageSearchLimits,MarriageSearchBudgetError,WorkMeter,borrow_marriage_reader
from moira.spk_reader import get_active_reader,use_reader_override
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.muhurta_marriage import MarriageEvidenceModel,MarriageEvidenceResponse
from moira_server.serializers.muhurta_marriage import serialize_marriage_windows,serialize_marriage_assessment,serialize_marriage_snapshot

pytestmark=[pytest.mark.integration,pytest.mark.requires_ephemeris,pytest.mark.loopback,pytest.mark.slow]


def _save_worked_case(name,payload):
    """Opt-in raw validation receipt, never a generated oracle expectation."""
    destination=os.environ.get('MOIRA_MARRIAGE_RECEIPT_DIR')
    if destination:
        directory=Path(destination)
        directory.mkdir(parents=True,exist_ok=True)
        (directory/(name+'.json')).write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')


def test_real_http_windows_full_profile_witnesses_and_reader_lifetime(planetary_kernel_path,monkeypatch,record_property):
    config=ServerConfig(kernel_path=str(planetary_kernel_path),prewarm_enabled=False,require_kernel_ready=True)
    with TestClient(create_app(config)) as client:
        engine=client.app.state.engine
        original=engine.marriage_election_windows
        captured=[]
        def observe(*args,**kwargs):
            result=original(*args,**kwargs)
            captured.append(result)
            return result
        monkeypatch.setattr(engine,'marriage_election_windows',observe)
        prior=get_active_reader()
        body={'start':'2026-10-10T12:00:00Z','end':'2026-10-10T18:00:00Z',
              'latitude':28.6,'longitude':77.2,'timezone':'Asia/Kolkata',
              'policy':{'ritual_anchor':'vows','regional_tradition':'kalinga_vanga','godhuli':True},
              'limits':{'max_history_days':4096}}
        start=time.perf_counter()
        try:
            response=client.post('/v1/muhurta/marriage/windows',json=body)
            _save_worked_case('real-http-windows',{'request':body,'status_code':response.status_code,
                'elapsed_seconds':time.perf_counter()-start,'response':response.json(),
                'evidence_class':'real serving-reader composition; not an independent full-profile oracle'})
            assert response.status_code==200,response.text
            assert len(captured)==1
            result=captured[0]
            assert response.json()==serialize_marriage_windows(result).model_dump(mode='json')
            assert result.search_receipt.crossing_completeness=='complete_under_declared_arithmetic_model',result.search_receipt.unavailable_reasons
            assert result.search_receipt.kernel_source_sha256
            assert result.cells and all(cell.constancy_certified for cell in result.cells)
            assert result.kernel_label=='DE-0441LE-0441'
            assert not engine._reader_obj._closed
            assert get_active_reader() is prior
            for index,cell in enumerate(result.cells):
                rebuilt=result.assessment(index)
                direct=assess_marriage_election(rebuilt.evidence,policy=result.policy)
                assert direct.astronomical_findings==rebuilt.astronomical_findings
                assert direct.composition_findings==rebuilt.composition_findings
                assert direct.requested_composition==cell.requested_composition
                assert result.at(cell.witness.jd_ut1)==rebuilt
                assert not any(f.rule_id=='numerical_search_completeness' for f in rebuilt.astronomical_findings)
            for band in result.transition_bands:
                if band.lower_jd_ut1<band.upper_jd_ut1:
                    assert result.at(band.jd_ut1) is None
            # Additional direct interior probes can expose a missing
            # transition family, but are not substituted for the certificate.
            def states(assessment):
                return tuple((f.rule_id,f.applicable,f.detected,f.effective_restriction,f.coverage_complete,
                              tuple((e.exception_id,e.satisfied) for e in f.exceptions))
                             for f in assessment.composition_findings)
            meter=WorkMeter(MarriageSearchLimits())
            with borrow_marriage_reader(engine._reader,meter) as borrowed,use_reader_override(borrowed):
                context=_Context(borrowed,meter,28.6,77.2,ZoneInfo('Asia/Kolkata'),'Asia/Kolkata',result.policy)
                for index,cell in enumerate(result.cells):
                    expected=result.assessment(index)
                    a,b=cell.interval.start.upper_jd_ut1,cell.interval.end.lower_jd_ut1
                    for fraction in (.25,.75):
                        jd=a+(b-a)*fraction
                        positions=tuple(MarriagePlanet(p.planet,context.longitude_at(p.planet,jd),context.body(p.planet,jd).speed)
                                        for p in expected.evidence.planets)
                        source=replace(expected.evidence,jd_ut1=jd,planets=positions,
                            lagna_sidereal_longitude=context.lagna(jd),
                            lunar_month=replace(expected.evidence.lunar_month,jd_ut1=jd))
                        assert states(assess_marriage_election(source,policy=result.policy))==states(expected)
            evidence=result.assessment(0).evidence
            transported=MarriageEvidenceResponse.model_validate(asdict(evidence))
            assert transported.to_engine()==evidence
            ordinary=replace(result.policy,godhuli=False)
            personal=MarriagePersonalContext((MarriageParticipant('one','bride',first_born=None),
                                              MarriageParticipant('two','groom',first_born=False)))
            assessment=assess_marriage_election(evidence,policy=ordinary,personal=personal)
            request={'evidence':transported.model_dump(mode='json',include=set(MarriageEvidenceModel.model_fields)),
                     'policy':body['policy']|{'godhuli':False},'personal':asdict(personal)}
            reply=client.post('/v1/muhurta/marriage/direct',json=request)
            _save_worked_case('real-http-personal-direct',{'request':request,'status_code':reply.status_code,
                'response':reply.json(),'evidence_class':'same-evidence direct transport and personal composition'})
            assert reply.status_code==200,reply.text
            assert reply.json()==serialize_marriage_assessment(assessment).model_dump(mode='json')
            assert not assessment.personal_decision.coverage_complete
            record_property('marriage_elapsed_seconds',time.perf_counter()-start)
            for key,value in asdict(result.search_receipt).items():
                if key in ('evaluations','reader_calls','transitions','cells','output_bytes','root_iterations','historical_cells'):
                    record_property('marriage_'+key,value)
        finally:
            engine._reader_obj.close()


def test_real_http_high_latitude_snapshot_retains_unavailable_rules(planetary_kernel_path,monkeypatch,record_property):
    config=ServerConfig(kernel_path=str(planetary_kernel_path),prewarm_enabled=False,require_kernel_ready=True)
    with TestClient(create_app(config)) as client:
        engine=client.app.state.engine
        original=engine.marriage_election_for_datetime
        captured=[]
        def observe(*args,**kwargs):
            result=original(*args,**kwargs)
            captured.append(result)
            return result
        monkeypatch.setattr(engine,'marriage_election_for_datetime',observe)
        prior=get_active_reader()
        request={'dt':'2026-10-10T12:00:00Z','latitude':70.,'longitude':19.,'timezone':'Europe/Oslo',
                 'policy':{'ritual_anchor':'vows','regional_tradition':'all_regions'}}
        start=time.perf_counter()
        try:
            response=client.post('/v1/muhurta/marriage/datetime',json=request)
            _save_worked_case('real-http-high-latitude-snapshot',{'request':request,'status_code':response.status_code,
                'elapsed_seconds':time.perf_counter()-start,'response':response.json(),
                'evidence_class':'real serving-reader unavailable composition; not a full-profile oracle'})
            assert response.status_code==200,response.text
            result=captured[0]
            assert response.json()==serialize_marriage_snapshot(result).model_dump(mode='json')
            assert result.assessment.evidence.lagna_sidereal_longitude is None
            assert result.assessment.evidence.jupiter_apparition is None
            assert result.assessment.evidence.venus_apparition is None
            assert all(planet+':required_apparition_history_has_undefined_horizon' in
                       result.search_receipt.unavailable_reasons for planet in ('Jupiter','Venus'))
            assert not result.assessment.astronomical.coverage_complete
            assert result.assessment.requested_composition.status!='passes_selected_profile'
            assert get_active_reader() is prior and not engine._reader_obj._closed
            direct=assess_marriage_election(result.assessment.evidence,policy=result.assessment.policy)
            actual=tuple(f for f in result.assessment.astronomical_findings if f.rule_id!='numerical_search_completeness')
            assert actual==direct.astronomical_findings
            record_property('marriage_elapsed_seconds',time.perf_counter()-start)
            for key,value in asdict(result.search_receipt).items():
                if key in ('evaluations','reader_calls','transitions','cells','output_bytes','root_iterations','historical_cells'):
                    record_property('marriage_'+key,value)
        finally:
            engine._reader_obj.close()


@pytest.mark.parametrize('latitude,history',[(28.6,2048),(70.,2048),(0.,4096)])
def test_real_resource_budget_failure_is_deterministic_and_restores_reader(moira_engine,latitude,history):
    from moira.muhurta_marriage import MarriageElectionPolicy
    prior=get_active_reader()
    with pytest.raises(MarriageSearchBudgetError) as failure:
        marriage_election_for_datetime(datetime(2026,10,10,12,tzinfo=timezone.utc),latitude,0.,timezone='UTC',
            policy=MarriageElectionPolicy('vows','all_regions'),
            limits=MarriageSearchLimits(max_evaluations=2,max_history_days=history),reader=moira_engine._reader)
    assert failure.value.limit_kind=='evaluations' and failure.value.count==3
    assert get_active_reader() is prior
    assert not moira_engine._reader_obj._closed
