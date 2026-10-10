"""Real-reader event roots, off-midpoint states, lifecycle, and HTTP parity."""
from contextvars import Context
from dataclasses import asdict
from datetime import date

from fastapi.testclient import TestClient
import pytest

from moira import (
    MuhurtaDoshaPolicy, detect_muhurta_doshas, muhurta_doshas_for_date,
    HouseSystem,
)
from moira.houses import calculate_houses
from moira.muhurta_dosha import KP_EXEMPT, MC_NECESSARY, MC_ABHIJIT
from moira.planets import planet_at
from moira.rise_set import _altitude
from moira.sidereal import tropical_to_sidereal
from moira.spk_reader import SpkReader, get_active_reader, use_reader_override
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.serializers.muhurta_dosha import serialize_dosha_day

pytestmark=[pytest.mark.integration,pytest.mark.requires_ephemeris,pytest.mark.loopback]


@pytest.mark.parametrize('day,lat,lon,zone,table,clock,gandanta',[
    (date(2026,10,9),28.6139,77.209,'Asia/Kolkata','mc_vivaha_49_51.v1','mc_avasthi_scaled_start_fixed_width.v1','mc_vivaha_43_fixed_ghati.v1'),
    (date(2026,10,10),28.6139,77.209,'Asia/Kolkata','kp_185_dual_mula.v1','normalized_nakshatra_sixtieths.v1','bphs_santhanam_92_fixed_ghati.v1'),
    (date(2026,3,8),40.73,-73.92,'America/New_York','mc_vivaha_49_51.v1','normalized_nakshatra_sixtieths.v1','mc_vivaha_43_fixed_ghati.v1'),
    (date(2026,11,1),40.73,-73.92,'America/New_York','kp_185_single_mula.v1','mc_avasthi_scaled_start_fixed_width.v1','bphs_santhanam_92_fixed_ghati.v1'),
    (date(2000,1,2),0,0,'UTC','mc_vivaha_49_51.v1','mc_avasthi_scaled_start_fixed_width.v1','mc_vivaha_43_fixed_ghati.v1'),
    (date(2026,9,22),65.99,25,'Europe/Helsinki','mc_vivaha_49_51.v1','normalized_nakshatra_sixtieths.v1','mc_vivaha_43_fixed_ghati.v1'),
])
def test_roots_and_dense_states(moira_engine,day,lat,lon,zone,table,clock,gandanta):
    previous=get_active_reader()
    policy=MuhurtaDoshaPolicy(vishanadi_profile=table,vishanadi_clock=clock,gandanta_profile=gandanta,
                              parihara_profiles=(KP_EXEMPT,MC_NECESSARY,MC_ABHIJIT))
    result=moira_engine.muhurta_doshas_for_date(day,lat,lon,timezone=zone,necessary_activity=True,policy=policy)
    assert result.status=='available' and not result.unavailable_reasons
    assert result.kernel_label=='DE-0441LE-0441' and result.reader_binding=='caller_owned_reader'
    assert get_active_reader() is previous

    def longitudes(jd):
        return tuple(tropical_to_sidereal(planet_at(n,jd,reader=moira_engine._reader).longitude,jd,policy.ayanamsa_system) for n in ('Sun','Moon'))

    def asc(jd):
        return tropical_to_sidereal(calculate_houses(jd,lat,lon,HouseSystem.WHOLE_SIGN).asc,jd,policy.ayanamsa_system)

    def truth(a):
        return tuple((f.rule_id,f.state,f.detected,f.neutralized) for f in a.findings)

    with use_reader_override(moira_engine._reader):
        for b,direction in ((result.sunrise,1),(result.sunset,-1),(result.next_sunrise,1)):
            h=policy.sunrise_definition.altitude_degrees
            assert direction*(_altitude(b.lower_jd_ut1,lat,lon,'Sun')-h)<=0
            assert direction*(_altitude(b.upper_jd_ut1,lat,lon,'Sun')-h)>=0
        lo,hi=result.sunrise.jd_ut1,result.next_sunrise.jd_ut1
        probes=[lo+(hi-lo)*(i+.5)/48 for i in range(48)]
        probes += [c.interval.start.upper_jd_ut1+f*(c.interval.end.lower_jd_ut1-c.interval.start.upper_jd_ut1)
                   for c in result.cells for f in (.11,.89)]
        for jd in probes:
            stored=result.at(jd)
            if stored is None:
                continue
            snapshot=detect_muhurta_doshas(*longitudes(jd),jd_ut1=jd,weekday=(day.weekday()+1)%7,
                lagna_sidereal_longitude=asc(jd),phase_spans=stored.inputs.phase_spans,
                sunrise_day=stored.inputs.sunrise_day,sunset=stored.inputs.sunset,
                necessary_activity=True,policy=policy)
            assert truth(snapshot)==truth(stored),(jd,truth(snapshot),truth(stored))
        # Independently evaluate the astronomical phase on both sides of every
        # full parent root, including parent events outside the owned sunrise day.
        seen=set()
        for c in result.cells:
            for event in c.assessment.inputs.phase_spans:
                for b in (event.interval.start,event.interval.end):
                    key=(event.kind,b.jd_ut1)
                    if key in seen:
                        continue
                    seen.add(key)
                    assert (b.upper_jd_ut1-b.lower_jd_ut1)*86400<=policy.solver_tolerance_seconds
                    def residual(jd):
                        sun,moon=longitudes(jd)
                        value=moon if event.kind=='nakshatra' else (moon-sun)%360 if event.kind=='tithi' else asc(jd)
                        divisions={'nakshatra':27,'tithi':30,'lagna':12}[event.kind]
                        return (value*divisions/360+.5)%1-.5
                    assert residual(b.lower_jd_ut1)<=0<=residual(b.upper_jd_ut1)
    for b in result.transition_bands:
        if b.lower_jd_ut1<b.upper_jd_ut1:
            assert result.at(b.jd_ut1) is None
    assert result.at(lo-1) is None and result.at(hi+1) is None
    assert any(f.state=='neutralized' for c in result.cells for f in c.assessment.findings)


@pytest.mark.parametrize('day',[date(2026,6,21),date(2026,12,21)])
def test_polar_no_solar_day(moira_engine,day):
    r=moira_engine.muhurta_doshas_for_date(day,69.6492,18.9553,timezone='Europe/Oslo')
    assert r.status=='unavailable' and not r.cells and r.unavailable_reasons


def test_polar_lagna_component_is_explicitly_unavailable(moira_engine):
    r=moira_engine.muhurta_doshas_for_date(date(2026,3,20),69.6492,18.9553,timezone='Europe/Oslo')
    assert r.status=='partial' and r.cells
    assert r.unavailable_reasons==('lagna_timing_at_or_above_ecliptic_polar_circle',)
    assert all(c.assessment.findings[-1].detected is None for c in r.cells)
    assert any(c.assessment.findings[2].detected is True for c in r.cells)


def test_caller_reader_survives_and_active_context_matches(planetary_kernel_path):
    before=get_active_reader()
    with SpkReader(planetary_kernel_path) as reader:
        explicit=muhurta_doshas_for_date(date(2000,1,2),0,0,timezone='UTC',reader=reader)
        with use_reader_override(reader):
            implicit=muhurta_doshas_for_date(date(2000,1,2),0,0,timezone='UTC')
            assert get_active_reader() is reader
        assert explicit.cells==implicit.cells and not reader._closed
    assert reader._closed and get_active_reader() is before


@pytest.mark.parametrize('configured',[False,True])
def test_serving_reader_canonical_http_parity(planetary_kernel_path,configured):
    config=ServerConfig(kernel_path=str(planetary_kernel_path) if configured else None,
                        prewarm_enabled=False,require_kernel_ready=True)
    def run():
        with TestClient(create_app(config)) as client:
            engine=client.app.state.engine
            try:
                body={'local_date':'2026-10-09','latitude':28.6139,'longitude':77.209,
                      'timezone':'Asia/Kolkata','necessary_activity':True,
                      'policy':{'parihara_profiles':[MC_NECESSARY,MC_ABHIJIT]}}
                r=client.post('/v1/muhurta/doshas/day',json=body)
                assert r.status_code==200,r.text
                expected=engine.muhurta_doshas_for_date(date(2026,10,9),28.6139,77.209,timezone='Asia/Kolkata',
                    necessary_activity=True,policy=MuhurtaDoshaPolicy(parihara_profiles=(MC_NECESSARY,MC_ABHIJIT)))
                assert r.json()==serialize_dosha_day(expected).model_dump(mode='json')
                assert asdict(expected)['activity_suitability']=='not_evaluated'
                assert not engine._reader_obj._closed
            finally:
                engine._reader_obj.close()
    Context().run(run)
