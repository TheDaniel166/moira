"""Required real DE441 HTTP evidence and transition certification."""
import json
import os
from pathlib import Path
from fastapi.testclient import TestClient
import pytest

from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.models.muhurta_vastu import VastuSnapshotResponse, VastuWindowsResponse
from moira_server.serializers.muhurta_election import election_values

pytestmark = [pytest.mark.integration,pytest.mark.requires_ephemeris,pytest.mark.loopback]


def save(name, value):
    destination = os.environ.get('MOIRA_PURPOSE_RECEIPT_DIR')
    if destination:
        directory = Path(destination)
        directory.mkdir(parents=True,exist_ok=True)
        (directory/(name+'.json')).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')


def test_real_housing_http_instant_and_transition_window(planetary_kernel_path, monkeypatch):
    config = ServerConfig(kernel_path=str(planetary_kernel_path),prewarm_enabled=False,require_kernel_ready=True)
    with TestClient(create_app(config)) as client:
        engine = client.app.state.engine
        captured = []
        for method in ('vastu_election_for_datetime','vastu_election_windows'):
            original = getattr(engine,method)
            def capture(*args,_original=original,**kwargs):
                value = _original(*args,**kwargs)
                captured.append(value)
                return value
            monkeypatch.setattr(engine,method,capture)
        common = dict(latitude=28.6,longitude=77.2,timezone='Asia/Kolkata',
            policy={'purpose':'foundation'},context={'facing':'north','excavation_corner':'southwest'})
        instant = client.post('/v1/muhurta/vastu/datetime',json=dict(common,dt='2026-10-10T00:00:00Z'))
        assert instant.status_code == 200,instant.text
        assert instant.json() == VastuSnapshotResponse(**election_values(captured[-1])).model_dump(mode='json')
        assert instant.json()['search_receipt']['crossing_completeness'] == 'complete_under_declared_arithmetic_model'
        save('housing-instant',instant.json())
        response = client.post('/v1/muhurta/vastu/windows',json=dict(common,start='2026-10-10T00:00:00Z',end='2026-10-10T06:00:00Z'))
        assert response.status_code == 200,response.text
        result = captured[-1]
        assert response.json() == VastuWindowsResponse(**election_values(result)).model_dump(mode='json')
        assert result.search_receipt.crossing_completeness == 'complete_under_declared_arithmetic_model'
        assert len(result.cells) >= 3
        assert any('lagna' in b.kind for b in result.transition_bands)
        assert all(c.constancy_certified for c in result.cells)
        for band in result.transition_bands[1:-1]:
            assert result.at(band.jd_ut1) is None
        for cell in result.cells:
            assert result.at(cell.assessment.evidence.jd_ut1) == cell.assessment
        assert not any('apparition' in h[0] or 'star_history' in h[0] for h in result.search_receipt.history_extents)
        save('housing-window',response.json())


def test_real_business_http_role_specific_work_and_windows(planetary_kernel_path,monkeypatch):
    from moira_server.models.muhurta_business import BusinessSnapshotResponse,BusinessWindowsResponse
    config=ServerConfig(kernel_path=str(planetary_kernel_path),prewarm_enabled=False,require_kernel_ready=True)
    with TestClient(create_app(config)) as client:
        engine=client.app.state.engine
        captured=[]
        for method in ('business_election_for_datetime','business_election_windows'):
            original=getattr(engine,method)
            def capture(*args,_original=original,**kwargs):
                value=_original(*args,**kwargs)
                captured.append(value)
                return value
            monkeypatch.setattr(engine,method,capture)
        common=dict(latitude=28.6,longitude=77.2,timezone='Asia/Kolkata',policy={'purpose':'purchase'},
            context={'actor_id':'buyer','actor_role':'buyer','anchor':'acceptance_exchange'})
        r=client.post('/v1/muhurta/business/datetime',json=dict(common,dt='2026-10-10T00:00:00Z'))
        assert r.status_code==200,r.text
        assert r.json()==BusinessSnapshotResponse(**election_values(captured[-1])).model_dump(mode='json')
        assert r.json()['search_receipt']['crossing_completeness']=='complete_under_declared_arithmetic_model'
        assert [p['planet'] for p in r.json()['assessment']['evidence']['planets']]==['Moon']
        assert r.json()['assessment']['evidence']['solar'] is None
        save('business-purchase-instant',r.json())
        r=client.post('/v1/muhurta/business/windows',json=dict(common,start='2026-10-10T00:00:00Z',end='2026-10-12T00:00:00Z'))
        assert r.status_code==200,r.text
        result=captured[-1]
        assert r.json()==BusinessWindowsResponse(**election_values(result)).model_dump(mode='json')
        assert result.search_receipt.crossing_completeness=='complete_under_declared_arithmetic_model'
        assert len(result.cells)>=2
        assert all(c.constancy_certified for c in result.cells)
        assert not result.search_receipt.history_extents
        save('business-purchase-window',r.json())
        common.update(policy={'purpose':'first_opening_for_trade'},
            context={'actor_id':'operator','actor_role':'trading_operator','anchor':'first_opening_for_trade'})
        r=client.post('/v1/muhurta/business/windows',json=dict(common,start='2026-10-10T00:00:00Z',end='2026-10-10T03:00:00Z'))
        assert r.status_code==200,r.text
        assert r.json()['search_receipt']['crossing_completeness']=='complete_under_declared_arithmetic_model'
        assert len(r.json()['cells'])>=2
        assert not any('apparition' in h[0] for h in r.json()['search_receipt']['history_extents'])
        save('business-opening-window',r.json())


@pytest.mark.slow
def test_real_first_entry_calendar_visibility_and_polar_unavailability(planetary_kernel_path):
    config=ServerConfig(kernel_path=str(planetary_kernel_path),prewarm_enabled=False,require_kernel_ready=True)
    with TestClient(create_app(config)) as client:
        common=dict(latitude=28.6,longitude=77.2,timezone='Asia/Kolkata',policy={'purpose':'first_entry'},context={'facing':'east'})
        r=client.post('/v1/muhurta/vastu/windows',json=dict(common,start='2026-10-10T00:00:00Z',end='2026-10-10T03:00:00Z'))
        assert r.status_code==200,r.text
        value=r.json()
        assert value['search_receipt']['crossing_completeness']=='complete_under_declared_arithmetic_model'
        assert len(value['cells'])>=2
        for cell in value['cells']:
            evidence=cell['assessment']['evidence']
            assert evidence['lunar_month']['policy']['system']=='purnimanta'
            assert evidence['jupiter_apparition'] is not None and evidence['venus_apparition'] is not None
            assert cell['constancy_certified']
        save('housing-first-entry-window',value)
        r=client.post('/v1/muhurta/vastu/datetime',json=dict(latitude=70.,longitude=20.,timezone='Europe/Oslo',
            policy={'purpose':'foundation'},context={'facing':'east'},dt='2026-06-21T12:00:00Z'))
        assert r.status_code==200,r.text
        value=r.json()
        assert value['search_receipt']['crossing_completeness']=='not_certified'
        assert value['assessment']['evidence']['solar'] is None
        assert not value['assessment']['astronomical']['coverage_complete']
        save('housing-polar-unavailable',value)


@pytest.mark.parametrize('limits,kind', [({'max_evaluations':1},'evaluations'),({'max_output_bytes':1000},'output_bytes')])
def test_real_purpose_budget_failure_preserves_reader(planetary_kernel_path,limits,kind):
    from moira.spk_reader import get_active_reader
    config=ServerConfig(kernel_path=str(planetary_kernel_path),prewarm_enabled=False,require_kernel_ready=True)
    with TestClient(create_app(config)) as client:
        before=get_active_reader()
        r=client.post('/v1/muhurta/business/datetime',json=dict(latitude=28.6,longitude=77.2,timezone='Asia/Kolkata',
            dt='2026-10-10T00:00:00Z',policy={'purpose':'purchase'},
            context={'actor_id':'a','actor_role':'buyer','anchor':'acceptance_exchange'},limits=limits))
        assert r.status_code==422,r.text
        assert r.json()['error_code']=='election_search_budget'
        assert r.json()['details']['limit_kind']==kind
        assert get_active_reader() is before


def test_real_travel_component_http_release_and_star_transition(planetary_kernel_path,monkeypatch):
    from moira_server.models.muhurta_travel import TravelSnapshotResponse,TravelWindowsResponse
    config=ServerConfig(kernel_path=str(planetary_kernel_path),prewarm_enabled=False,require_kernel_ready=True)
    with TestClient(create_app(config)) as client:
        engine=client.app.state.engine
        captured=[]
        for method in ('travel_election_for_datetime','travel_election_windows'):
            original=getattr(engine,method)
            def capture(*args,_original=original,**kwargs):
                value=_original(*args,**kwargs)
                captured.append(value)
                return value
            monkeypatch.setattr(engine,method,capture)
        common=dict(latitude=28.6,longitude=77.2,timezone='Asia/Kolkata',
            policy={'profile':'kp_1917_weekday_direction_release.v1'},
            context={'traveller_id':'a','anchor':'leave_residence','direction':'east'})
        # Saturday, with the eastward8-ghati release between these times.
        r=client.post('/v1/muhurta/travel/windows',json=dict(common,start='2026-10-10T02:00:00Z',end='2026-10-10T06:00:00Z'))
        assert r.status_code==200,r.text
        result=captured[-1]
        assert r.json()==TravelWindowsResponse(**election_values(result)).model_dump(mode='json')
        assert result.search_receipt.crossing_completeness=='complete_under_declared_arithmetic_model'
        assert [c.assessment.astronomical.status for c in result.cells]==['restricted','passes_selected_profile']
        assert any(b.kind=='kp_weekday_release' for b in result.transition_bands)
        assert result.at(result.transition_bands[1].jd_ut1) is None
        save('travel-kp-weekday-release',r.json())
        common['policy']={'profile':'kp_1917_travel_modular_tests.v1'}
        r=client.post('/v1/muhurta/travel/datetime',json=dict(common,dt='2026-10-10T02:00:00Z'))
        assert r.status_code==200,r.text
        assert r.json()==TravelSnapshotResponse(**election_values(captured[-1])).model_dump(mode='json')
        save('travel-kp-modular-instant',r.json())
        r=client.post('/v1/muhurta/travel/windows',json=dict(common,start='2026-10-10T00:00:00Z',end='2026-10-11T12:00:00Z'))
        assert r.status_code==200,r.text
        result=captured[-1]
        assert result.search_receipt.crossing_completeness=='complete_under_declared_arithmetic_model'
        assert any('Moon_election' in b.kind for b in result.transition_bands)
        assert all(c.constancy_certified for c in result.cells)
        save('travel-kp-modular-window',r.json())


@pytest.mark.slow
def test_real_mc_travel_http_instant_window_and_profile_parity(planetary_kernel_path,monkeypatch):
    from moira_server.models.muhurta_travel import TravelSnapshotResponse,TravelWindowsResponse
    config=ServerConfig(kernel_path=str(planetary_kernel_path),prewarm_enabled=False,require_kernel_ready=True)
    with TestClient(create_app(config)) as client:
        engine=client.app.state.engine
        captured=[]
        for method in ('travel_election_for_datetime','travel_election_windows'):
            original=getattr(engine,method)
            def capture(*args,_original=original,**kwargs):
                result=_original(*args,**kwargs)
                captured.append(result)
                return result
            monkeypatch.setattr(engine,method,capture)
        common=dict(latitude=28.6,longitude=77.2,timezone='Asia/Kolkata',
            policy={'profile':'mc_maniprabha_1948_ordinary_land.v1'},
            context={'traveller_id':'a','anchor':'leave_residence','direction':'north','leg':'return',
                'prior_departure_jd_ut1':2461200.,'completed_stop_nights':5,
                'participant':{'participant_id':'a','natal_moon_sidereal_longitude':33.,'natal_lagna_sidereal_longitude':175.}})
        r=client.post('/v1/muhurta/travel/datetime',json=dict(common,dt='2026-10-10T02:00:00Z'))
        assert r.status_code==200,r.text
        assert r.json()==TravelSnapshotResponse(**election_values(captured[-1])).model_dump(mode='json')
        assert r.json()['search_receipt']['crossing_completeness']=='complete_under_declared_arithmetic_model'
        assert r.json()['assessment']['evidence']['lunar_month'] is None
        assert r.json()['assessment']['evidence']['jupiter_apparition'] is None
        assert r.json()['assessment']['evidence']['venus_apparition'] is not None
        save('travel-mc-instant',r.json())
        r=client.post('/v1/muhurta/travel/windows',json=dict(common,start='2026-10-10T02:00:00Z',end='2026-10-10T02:30:00Z'))
        assert r.status_code==200,r.text
        result=captured[-1]
        assert r.json()==TravelWindowsResponse(**election_values(result)).model_dump(mode='json')
        assert result.search_receipt.crossing_completeness=='complete_under_declared_arithmetic_model'
        assert len(result.cells)>=2
        assert all(c.constancy_certified for c in result.cells)
        assert any('lagna_discrete' in b.kind for b in result.transition_bands)
        for cell in result.cells:
            assert result.at(cell.assessment.evidence.jd_ut1)==cell.assessment
            raw=election_values(cell.assessment)
            request=dict(evidence=raw['evidence'],policy=common['policy'],context=common['context'])
            # Remove evidence fields that are response-owned rather than inputs.
            from moira_server.models.muhurta_election import ElectionEvidenceResponse,ElectionEvidenceModel
            response=ElectionEvidenceResponse(**raw['evidence'])
            request['evidence']=ElectionEvidenceModel(**{k:getattr(response,k) for k in ElectionEvidenceModel.model_fields}).model_dump(mode='json')
            direct=client.post('/v1/muhurta/travel/direct',json=request)
            assert direct.status_code==200,direct.text
            from moira_server.models.muhurta_travel import TravelAssessmentResponse
            expected=TravelAssessmentResponse(**raw).model_dump(mode='json')
            assert direct.json()['astronomical_findings']==expected['astronomical_findings']
            assert direct.json()['personal_findings']==expected['personal_findings']
        save('travel-mc-window',r.json())
