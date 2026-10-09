"""Real-reader clocks, position parity, immutable evidence and HTTP lifecycle."""
from dataclasses import asdict
from datetime import datetime, timezone
from contextvars import Context
import pytest
from fastapi.testclient import TestClient
from moira import MuhurtaLagnaPolicy, muhurta_lagna_for_datetime, evaluate_muhurta_lagna_strength
from moira.spk_reader import use_reader_override, get_active_reader
from moira.planets import planet_at
from moira.houses import calculate_houses
from moira.sidereal import tropical_to_sidereal
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.serializers.muhurta_lagna import serialize_lagna_snapshot

pytestmark=[pytest.mark.integration,pytest.mark.requires_ephemeris,pytest.mark.loopback]
DT=datetime(2026,10,9,12,tzinfo=timezone.utc)


@pytest.mark.parametrize('lat,lon,system,include',[(28.6,77.2,'Lahiri',True),(40.7,-74.,'Raman',False),(-33.9,151.2,'Lahiri',True),(90.,0.,'Lahiri',True)])
def test_real_epoch_geometry_and_context(moira_engine,lat,lon,system,include):
    prior=get_active_reader()
    r=moira_engine.muhurta_lagna_for_datetime(DT,lat,lon,policy=MuhurtaLagnaPolicy(ayanamsa_system=system),include_shadbala=include)
    assert get_active_reader() is prior
    assert r.epoch.kernel_label=='DE-0441LE-0441'
    assert len(r.assessment.planets)==9
    with use_reader_override(moira_engine._reader):
        for p in r.assessment.planets[:7]:
            tropical=planet_at(p.planet,r.epoch.jd_ut1,reader=moira_engine._reader,jd_tt=r.epoch.jd_tt).longitude
            assert p.sidereal_longitude==pytest.approx(tropical_to_sidereal(tropical,r.epoch.jd_ut1,system),abs=1e-10)
        if abs(lat)<90:
            h=calculate_houses(r.epoch.jd_ut1,lat,lon,'W')
            assert r.assessment.lagna_sidereal_longitude==pytest.approx(tropical_to_sidereal(h.asc,r.epoch.jd_ut1,system),abs=1e-10)
            if include:assert len(r.assessment.shadbala)==7
        else:
            assert r.assessment.lagna_navamsa is None and r.shadbala_basis=='unavailable_lagna_geometry'
    payload=serialize_lagna_snapshot(r).model_dump(mode='json')
    assert payload['assessment']['activity_suitability']=='not_evaluated'
    direct=evaluate_muhurta_lagna_strength({p.planet:p.sidereal_longitude for p in r.assessment.planets},
        jd_ut1=r.epoch.jd_ut1, lagna_sidereal_longitude=r.assessment.lagna_sidereal_longitude,policy=r.assessment.policy)
    assert direct.rules==r.assessment.rules and direct.restrictions==r.assessment.restrictions


@pytest.mark.parametrize('configured',[False,True])
def test_http_and_active_reader_parity(planetary_kernel_path,configured):
    def run():
        config=ServerConfig(kernel_path=str(planetary_kernel_path) if configured else None,prewarm_enabled=False,require_kernel_ready=True)
        with TestClient(create_app(config)) as client:
            engine=client.app.state.engine
            try:
                body={'dt':DT.isoformat(),'latitude':28.6,'longitude':77.2,'include_shadbala':True,'hora_lord':'Venus'}
                response=client.post('/v1/muhurta/lagna/datetime',json=body)
                assert response.status_code==200,response.text
                expected=engine.muhurta_lagna_for_datetime(DT,28.6,77.2,include_shadbala=True,hora_lord='Venus')
                assert response.json()==serialize_lagna_snapshot(expected).model_dump(mode='json')
                assert not engine._reader_obj._closed
                direct={'sidereal_longitudes':{p.planet:p.sidereal_longitude for p in expected.assessment.planets},
                        'lagna_sidereal_longitude':expected.assessment.lagna_sidereal_longitude,'jd_ut1':expected.epoch.jd_ut1,
                        'shadbala_result':{'jd':expected.epoch.jd_ut1,'ayanamsa_system':'Lahiri',
                          'planets':{p.planet:asdict(p) for p in expected.assessment.shadbala}}}
                transport=client.post('/v1/muhurta/lagna/direct',json=direct)
                assert transport.status_code==200,transport.text
                dated_assessment=response.json()['assessment']
                assert dated_assessment['input_basis']=='serving_reader_derived_sidereal_same_epoch'
                assert transport.json()==dated_assessment | {'input_basis':'caller_supplied_sidereal_same_epoch'}
            finally:engine._reader_obj.close()
    Context().run(run)


def test_borrowed_and_discovered_reader_restore(moira_engine):
    before=get_active_reader()
    with use_reader_override(moira_engine._reader):
        implicit=muhurta_lagna_for_datetime(DT,0.,0.)
        explicit=muhurta_lagna_for_datetime(DT,0.,0.,reader=moira_engine._reader)
        assert implicit.assessment==explicit.assessment and implicit.epoch==explicit.epoch
        assert implicit.reader_binding=='discovered_reader'
    assert get_active_reader() is before
