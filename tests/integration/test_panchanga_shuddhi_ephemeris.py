"""DE441 numerical/reader/HTTP validation; not a paired external Shuddhi oracle."""
from contextvars import Context
from datetime import date

from fastapi.testclient import TestClient
import pytest

from moira import PanchangaShuddhiPolicy, panchanga_shuddhi_for_date, panchanga_shuddhi_from_longitudes
from moira.houses import calculate_houses, HouseSystem
from moira.planets import planet_at
from moira.rise_set import _altitude
from moira.sidereal import tropical_to_sidereal
from moira.spk_reader import SpkReader, get_active_reader, use_reader_override
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.serializers.panchanga_shuddhi import serialize_shuddhi_day

pytestmark=[pytest.mark.integration,pytest.mark.requires_ephemeris,pytest.mark.loopback]


@pytest.mark.parametrize('day,lat,lon,zone,profile',[
    (date(2026,10,9),28.6139,77.209,'Asia/Kolkata','mc_gochara_13_quarters.v1'),
    (date(2026,10,10),28.6139,77.209,'Asia/Kolkata','ps_sastri_scientific_273_navaka.v1'),
    (date(2026,3,8),40.73,-73.92,'America/New_York','mc_gochara_13_quarters.v1'),
    (date(2026,11,1),40.73,-73.92,'America/New_York','mc_gochara_13_quarters.v1'),
    (date(2000,1,2),0,0,'UTC','mc_gochara_13_quarters.v1'),
    (date(2026,9,22),65.99,25,'Europe/Helsinki','mc_gochara_13_quarters.v1'),
])
def test_real_cells_roots_and_dense_instantaneous_agreement(moira_engine,day,lat,lon,zone,profile):
    before=get_active_reader()
    policy=PanchangaShuddhiPolicy(tara_profile=profile)
    result=moira_engine.panchanga_shuddhi_for_date(day,lat,lon,timezone=zone,natal_nakshatra_index=0,policy=policy)
    assert result.status=='available' and get_active_reader() is before
    assert result.kernel_label=='DE-0441LE-0441' and result.reader_binding=='caller_owned_reader'
    assert len({c.assessment.values.panchaka.lagna_number for c in result.cells})==12
    def longitudes(jd):
        return tuple(tropical_to_sidereal(planet_at(name,jd,reader=moira_engine._reader).longitude,jd,policy.ayanamsa_system) for name in ('Sun','Moon'))
    with use_reader_override(moira_engine._reader):
        for anchor,direction in ((result.sunrise,1),(result.next_sunrise,1),(result.sunset,-1)):
            height=policy.sunrise_definition.altitude_degrees
            assert direction*(_altitude(anchor.lower_jd_ut1,lat,lon,'Sun')-height)<=0
            assert direction*(_altitude(anchor.upper_jd_ut1,lat,lon,'Sun')-height)>=0
        # Independently re-evaluate exact planets/houses at off-midpoint probes.
        start,end=result.sunrise.jd_ut1,result.next_sunrise.jd_ut1
        probes=[start+(end-start)*(i+.5)/48 for i in range(48)]
        probes += [c.interval.start.upper_jd_ut1+.17*(c.interval.end.lower_jd_ut1-c.interval.start.upper_jd_ut1) for c in result.cells]
        for jd in probes:
            stored=result.at(jd)
            if stored is None:
                continue
            sun,moon=longitudes(jd)
            asc=tropical_to_sidereal(calculate_houses(jd,lat,lon,HouseSystem.WHOLE_SIGN).asc,jd,policy.ayanamsa_system)
            snapshot=panchanga_shuddhi_from_longitudes(sun,moon,jd_ut1=jd,
                weekday=(day.weekday()+1)%7,lagna_sidereal_longitude=asc,natal_nakshatra_index=0,
                is_daytime=jd<result.sunset.jd_ut1,policy=policy,
                yoga_span=stored.inputs.yoga_span,tithi_span=stored.inputs.tithi_span,karana_span=stored.inputs.karana_span)
            assert snapshot.values==stored.values
            assert snapshot.findings==stored.findings
        # Parent-event endpoints solve phase zero modulo their subdivision.
        seen=set()
        for cell in result.cells:
            for name,divisions in (('tithi_span',30),('karana_span',60),('yoga_span',27)):
                span=getattr(cell.assessment.inputs,name)
                for boundary in (span.start,span.end):
                    if (name,boundary.jd_ut1) in seen:
                        continue
                    seen.add((name,boundary.jd_ut1))
                    assert (boundary.upper_jd_ut1-boundary.lower_jd_ut1)*86400<=policy.solver_tolerance_seconds
                    pairs=[longitudes(jd) for jd in (boundary.lower_jd_ut1,boundary.upper_jd_ut1)]
                    values=[(sum(p) if name=='yoga_span' else p[1]-p[0])%360 for p in pairs]
                    # Signed distance to the closest theoretical subdivision.
                    residuals=[(v*divisions/360+.5)%1-.5 for v in values]
                    assert residuals[0]<=0<=residuals[1],(name,values,residuals)
    for band in result.transition_bands:
        assert result.at(band.jd_ut1) is None
    assert result.at(start-1) is None and result.at(end+1) is None
    if day==date(2026,10,9):
        assert any(c.assessment.simultaneous_bhadra_claims for c in result.cells)
        assert any(c.assessment.inputs.tithi_span.start.jd_ut1 < start for c in result.cells)


@pytest.mark.parametrize('day',[date(2026,6,21),date(2026,12,21)])
def test_real_polar_solar_absence(moira_engine,day):
    r=moira_engine.panchanga_shuddhi_for_date(day,69.6492,18.9553,timezone='Europe/Oslo',natal_nakshatra_index=0)
    assert r.status=='unavailable' and not r.cells and r.unavailable_reasons


def test_real_polar_lagna_partial(moira_engine):
    r=moira_engine.panchanga_shuddhi_for_date(date(2026,3,20),69.6492,18.9553,timezone='Europe/Oslo',natal_nakshatra_index=0)
    assert r.status=='partial' and r.cells
    assert r.unavailable_reasons==('lagna_timing_at_or_above_ecliptic_polar_circle',)
    assert all(c.assessment.values.panchaka is None for c in r.cells)


def test_reader_lifecycle_and_explicit_active_parity(planetary_kernel_path):
    with SpkReader(planetary_kernel_path) as reader:
        explicit=panchanga_shuddhi_for_date(date(2000,1,2),0,0,timezone='UTC',reader=reader)
        with use_reader_override(reader):
            implicit=panchanga_shuddhi_for_date(date(2000,1,2),0,0,timezone='UTC')
            assert get_active_reader() is reader
        assert explicit.cells==implicit.cells and not reader._closed
    assert reader._closed


@pytest.mark.parametrize('configured',[False,True])
def test_real_startup_http_reader_projection(planetary_kernel_path,configured):
    config=ServerConfig(kernel_path=str(planetary_kernel_path) if configured else None,
                        prewarm_enabled=False,require_kernel_ready=True)
    def run():
        with TestClient(create_app(config)) as client:
            engine=client.app.state.engine
            try:
                body={'local_date':'2026-10-09','latitude':28.6139,'longitude':77.209,
                      'timezone':'Asia/Kolkata','natal_nakshatra_index':0}
                response=client.post('/v1/muhurta/shuddhi/day',json=body)
                assert response.status_code==200,response.text
                result=engine.panchanga_shuddhi_for_date(date(2026,10,9),28.6139,77.209,timezone='Asia/Kolkata',natal_nakshatra_index=0)
                assert response.json()==serialize_shuddhi_day(result).model_dump(mode='json')
                assert not engine._reader_obj._closed
            finally:
                engine._reader_obj.close()
    Context().run(run)
