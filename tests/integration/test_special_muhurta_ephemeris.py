"""DE441 geometry/phase and transport tests; no paired external oracle claim."""
from contextvars import Context
from datetime import date, datetime, timedelta, timezone
from fractions import Fraction

from fastapi.testclient import TestClient
import pytest

from moira import SpecialMuhurtaPolicy, special_muhurta_for_date, muhurta_yogas_from_longitudes
from moira.planets import planet_at
from moira.rise_set import _altitude
from moira.sidereal import tropical_to_sidereal
from moira.spk_reader import SpkReader, get_active_reader, use_reader_override
from moira_server.app import create_app
from moira_server.config import ServerConfig
from moira_server.serializers.special_muhurta import serialize_special_muhurta_day

pytestmark=[pytest.mark.integration,pytest.mark.requires_ephemeris,pytest.mark.loopback]


@pytest.mark.parametrize("day,lat,lon,zone,amrita,horizon",[
    (date(2026,9,22),23+11/60,82.5,"UTC+05:30","sadhana_amrita_siddhi","standard_refraction_34_arcmin"),
    (date(2026,10,8),28.6139,77.209,"Asia/Kolkata","kalaprakasika_amirtha","standard_refraction_34_arcmin"),
    (date(2026,10,10),28.6139,77.209,"Asia/Kolkata","sadhana_amrita_siddhi","geometric_disc"),
    (date(2026,3,8),40.73,-73.92,"America/New_York","kalaprakasika_amirtha","geometric_disc"),
    (date(2026,11,1),40.73,-73.92,"America/New_York","sadhana_amrita_siddhi","standard_refraction_34_arcmin"),
])
def test_real_seven_family_day(moira_engine,day,lat,lon,zone,amrita,horizon):
    before=get_active_reader()
    policy=SpecialMuhurtaPolicy(amrita_basis=amrita,godhuli_horizon=horizon)
    result=moira_engine.special_muhurta_for_date(day,lat,lon,timezone=zone,policy=policy)
    assert get_active_reader() is before and result.status=="available"
    assert result.named.kernel_label=="DE-0441LE-0441"
    assert len(result.results)==5 and len(result.named.result.intervals)==2
    anchors={a.kind:a for a in result.anchors}
    half,full=anchors["half_set"],anchors["upper_limb_sunset"]
    assert half.upper_jd_ut1 < full.lower_jd_ut1
    offset=34/60 if horizon=="standard_refraction_34_arcmin" else 0
    with use_reader_override(moira_engine._reader):
        for anchor,height in ((half,-offset),(full,-offset-16/60)):
            assert _altitude(anchor.lower_jd_ut1,lat,lon,"Sun") >= height
            assert _altitude(anchor.upper_jd_ut1,lat,lon,"Sun") <= height
            assert (anchor.upper_jd_ut1-anchor.lower_jd_ut1)*86400<=.1
    vijaya,godhuli=result.results[:2]
    rise,setting=(Fraction.from_float(anchors[k].jd_ut1) for k in ("sunrise","sunset"))
    assert vijaya.windows[0].start.jd_ut1==float((5*rise+10*setting)/15)
    assert abs((godhuli.windows[-1].end.jd_ut1-godhuli.windows[0].start.jd_ut1)*86400-1440)<.0001
    start,end=anchors["sunrise"].jd_ut1,anchors["next_sunrise"].jd_ut1
    # Independent dense probes plus each solved cell midpoint: presence must
    # agree with canonical instantaneous longitudes outside root bands.
    probes=[start+(end-start)*(i+.5)/48 for i in range(48)]
    probes += [(w.start.upper_jd_ut1+w.end.lower_jd_ut1)/2 for r in result.results[2:] for w in r.windows]
    for jd in probes:
        longitudes=[tropical_to_sidereal(planet_at(body,jd,reader=moira_engine._reader).longitude,jd,policy.ayanamsa_system) for body in ("Sun","Moon")]
        snapshot=muhurta_yogas_from_longitudes(*longitudes,weekday=day.weekday(),policy=policy)
        for row in snapshot.results:
            observed=result.contains_yoga(row.name,jd)
            if observed is not None:
                assert observed==row.present
    for band in result.transition_bands:
        for row in result.results[2:]:
            assert result.contains_yoga(row.name,band.jd_ut1) is None
    if day.month==9:
        # Existing PAC source component: sunrise, not a five-window oracle.
        expected=datetime(2026,9,22,5,49,tzinfo=timezone(timedelta(hours=5,minutes=30)))
        assert abs((anchors["sunrise"].moment.local-expected).total_seconds())<=60


@pytest.mark.parametrize("day",[date(2026,6,21),date(2026,12,21)])
def test_real_polar_absence(moira_engine,day):
    result=moira_engine.special_muhurta_for_date(day,69.6492,18.9553,timezone="Europe/Oslo")
    assert result.status=="unavailable"
    assert all(r.status=="unavailable" and not r.windows for r in result.results)


def test_explicit_and_active_reader_paths_leave_reader_open(planetary_kernel_path):
    with SpkReader(planetary_kernel_path) as reader:
        explicit=special_muhurta_for_date(date(2000,1,2),0,0,timezone="UTC",reader=reader)
        with use_reader_override(reader):
            implicit=special_muhurta_for_date(date(2000,1,2),0,0,timezone="UTC")
            assert get_active_reader() is reader
        assert explicit.results==implicit.results and reader._closed is False
    assert reader._closed is True


@pytest.mark.parametrize("configured",[False,True])
def test_real_startup_http_projection(planetary_kernel_path,configured):
    config=ServerConfig(kernel_path=str(planetary_kernel_path) if configured else None,prewarm_enabled=False,require_kernel_ready=True)
    def run():
        with TestClient(create_app(config)) as client:
            engine=client.app.state.engine
            try:
                body={"local_date":"2026-10-10","latitude":28.6139,"longitude":77.209,"timezone":"Asia/Kolkata",
                      "policy":{"amrita_basis":"kalaprakasika_amirtha","godhuli_horizon":"geometric_disc"}}
                response=client.post("/v1/muhurta/special/day",json=body)
                assert response.status_code==200,response.text
                result=engine.special_muhurta_for_date(date(2026,10,10),28.6139,77.209,timezone="Asia/Kolkata",policy=SpecialMuhurtaPolicy(**body["policy"]))
                assert response.json()==serialize_special_muhurta_day(result).model_dump(mode="json")
                assert engine._reader_obj._closed is False
            finally:
                engine._reader_obj.close()
    Context().run(run)
