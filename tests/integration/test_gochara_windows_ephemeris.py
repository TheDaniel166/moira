"""Real serving-DE441 enclosure, dated reconstruction and resource contracts."""
import math
import pytest

from moira.gochara import GOCHARA_PLANETS
from moira.gochara_dated import GocharaDatePolicy, gochara_at
from moira.gochara_windows import (
    gochara_windows, GocharaWindowSearchPolicy, GocharaWindowSearchLimits,
    GocharaWindowBudgetError, GocharaWindowDomainError,
)
from moira.sidereal import Ayanamsa
from moira._gochara_window_astronomy import GocharaWindowAstronomy
from moira._event_search.budgets import WorkMeter
from moira._event_search.resources import borrow_reader
from moira._event_search.intervals import EnclosureUnavailable
from moira.spk_reader import use_reader_override

pytestmark=[pytest.mark.integration,pytest.mark.requires_ephemeris]


def meter():
    return WorkMeter(GocharaWindowSearchLimits(),budget_error=GocharaWindowBudgetError,
                     kinds=("evaluations","reader_calls"))


@pytest.mark.parametrize("system",Ayanamsa.ALL)
@pytest.mark.parametrize("jd",[2415022.5,2451545.,2460967.,2488432.5])
def test_all_twelve_enclose_serving_point_longitudes(moira_engine,system,jd):
    policy=GocharaDatePolicy(ayanamsa_system=system)
    with borrow_reader(moira_engine._reader,meter()) as reader,use_reader_override(reader):
        astro=GocharaWindowAstronomy(reader,meter(),policy,jd-.02,jd+.02)
        points=[gochara_at(2451545.,t,reader=reader,policy=policy).transit for t in (jd-.02,jd,jd+.02)]
        for i,p in enumerate(GOCHARA_PLANETS):
            def enclosures(a,b):
                try:
                    return [(a,b,astro.longitude(p,a,b))]
                except EnclosureUnavailable as exc:
                    # Serving record boundaries disable centered bounds. The
                    # interval owner explicitly requests subdivision; verify
                    # the resulting cover instead of assuming one wide box.
                    assert "subdivision" in str(exc) and b-a>1e-7
                    mid=(a+b)/2
                    return enclosures(a,mid)+enclosures(mid,b)
            cover=enclosures(jd-.02,jd+.02)
            for point in points:
                containing=[jet for a,b,jet in cover if a<=point.jd_ut1<=b]
                assert containing
                lon=point.positions[i].position.sidereal_longitude
                for jet in containing:
                    lift=lon+360*math.floor(((jet.value.lo+jet.value.hi)/2-lon)/360+.5)
                    assert jet.value.lo<=lift<=jet.value.hi,(system,jd,p,jet.value,lon)
        astro.assert_resources()


@pytest.mark.parametrize("jd,direction",[(2460967.,1),(2461014.5,-1),(2461193.,1)])
def test_real_jupiter_direct_retrograde_reentry(moira_engine,jd,direction):
    result=moira_engine.gochara_windows(2451545.,jd,jd+1,
        search_policy=GocharaWindowSearchPolicy(require_resolved=True))
    events=[e for e in result.events if e.planet=="Jupiter"]
    assert len(events)==1 and events[0].direction==direction
    assert events[0].boundary_degrees==90
    for sample in result.samples:
        expected=gochara_at(2451545.,sample.epoch.jd_ut1,reader=moira_engine._reader)
        assert result.resolve_sample(sample.id)==expected


@pytest.mark.parametrize("bound",[2415020.5,2488434.4999])
def test_tt_intersection_edges_are_explicit(moira_engine,bound):
    if bound<2451545:
        a,b=bound,bound+.01
    else:
        a,b=bound-.01,bound
    with pytest.raises(GocharaWindowDomainError):
        gochara_windows(2451545.,a,b,reader=moira_engine._reader)


def test_reader_budget_does_not_close_borrowed_reader(moira_engine):
    with pytest.raises(GocharaWindowBudgetError) as caught:
        moira_engine.gochara_windows(2451545.,2460967.,2460968.,search_policy=GocharaWindowSearchPolicy(
            limits=GocharaWindowSearchLimits(max_reader_calls=1)))
    assert caught.value.limit_kind=="reader_calls"
    assert moira_engine.gochara_at(2451545.,2460967.).transit.positions


def test_split_queries_agree_away_from_boundary_bands(moira_engine):
    whole=moira_engine.gochara_windows(2451545.,2460967.,2460969.)
    parts=(moira_engine.gochara_windows(2451545.,2460967.,2460968.),
           moira_engine.gochara_windows(2451545.,2460968.,2460969.))
    for part in parts:
        for sample in part.samples:
            regions=[r for r in whole.regions if r.kind=="certain" and r.start_jd_ut1<sample.epoch.jd_ut1<r.end_jd_ut1]
            if regions:
                assert part.states[sample.state_id].signs==whole.states[regions[0].state_id].signs


def test_request_caches_can_be_disabled_without_changing_scientific_results(moira_engine,monkeypatch):
    import importlib
    import functools
    cached=moira_engine.gochara_windows(2451545.,2460967.,2460968.)
    from moira._bounded_memo import bounded_memo
    def no_memo(function,*,key,maxsize):
        return bounded_memo(function,key=key,maxsize=0)
    for module in ("moira._event_search.astronomy","moira._event_search.frames","moira._gochara_window_astronomy"):
        monkeypatch.setattr(importlib.import_module(module),"bounded_memo",no_memo)
    for module in ("moira._event_search.astronomy","moira._event_search.clocks","moira._event_search.intervals","moira._gochara_window_astronomy"):
        monkeypatch.setattr(importlib.import_module(module),"lru_cache",lambda maxsize:functools.lru_cache(maxsize=0))
    uncached=moira_engine.gochara_windows(2451545.,2460967.,2460968.)
    for name in ("natal","states","samples","events","regions","exclusions","coverage"):
        assert getattr(cached,name)==getattr(uncached,name)
    assert dict(uncached.work)["reader_calls"]>=dict(cached.work)["reader_calls"]


def test_concurrent_requests_keep_readers_and_counters_isolated(moira_engine):
    from concurrent.futures import ThreadPoolExecutor
    from moira.spk_reader import get_active_reader
    def run(system):
        before=get_active_reader()
        result=moira_engine.gochara_windows(2451545.,2460967.,2460968.,policy=GocharaDatePolicy(ayanamsa_system=system))
        assert get_active_reader() is before
        return result
    systems=("Lahiri","True Chitrapaksha")
    sequential=[run(system) for system in systems]
    with ThreadPoolExecutor(max_workers=2) as executor:
        concurrent=list(executor.map(run,systems))
    for a,b in zip(sequential,concurrent):
        assert a.to_dict()==b.to_dict()


def test_serving_reader_cap_below_at_and_above_measured_work(moira_engine):
    # Warm the serving owner first; the borrowed request must still own all
    # cached planetary contexts and charge their reads to its own meter.
    moira_engine.gochara_at(2451545.,2460967.)
    count=dict(moira_engine.gochara_windows(2451545.,2460967.,2460967.1).work)["reader_calls"]
    for cap in (count,count+1):
        result=moira_engine.gochara_windows(2451545.,2460967.,2460967.1,
            search_policy=GocharaWindowSearchPolicy(limits=GocharaWindowSearchLimits(max_reader_calls=cap)))
        assert dict(result.work)["reader_calls"]==count
    with pytest.raises(GocharaWindowBudgetError):
        moira_engine.gochara_windows(2451545.,2460967.,2460967.1,
            search_policy=GocharaWindowSearchPolicy(limits=GocharaWindowSearchLimits(max_reader_calls=count-1)))


def test_live_anchor_missing_and_mutating_resources_fail_explicitly(moira_engine,monkeypatch):
    from moira import stars
    from moira.gochara_dated import GocharaResourceError
    policy=GocharaDatePolicy(ayanamsa_system="True Chitrapaksha")
    with borrow_reader(moira_engine._reader,meter()) as reader,use_reader_override(reader):
        astro=GocharaWindowAstronomy(reader,meter(),policy,2460967.,2460968.)
        with monkeypatch.context() as patch:
            patch.setattr(astro,"_clock_signature",lambda:"changed")
            with pytest.raises(GocharaResourceError,match="clock/EOP"):
                astro.assert_resources()
        original=stars._resolve_star_record
        with monkeypatch.context() as patch:
            patch.setattr(stars,"_resolve_star_record",lambda *a,**k:(object(),))
            with pytest.raises(GocharaResourceError,match="anchor changed"):
                astro.assert_resources()
        assert stars._resolve_star_record is original
    def missing(*args,**kwargs):
        raise LookupError("test missing live anchor")
    monkeypatch.setattr(stars,"_resolve_star_record",missing)
    with pytest.raises(GocharaResourceError):
        moira_engine.gochara_windows(2451545.,2460967.,2460968.,policy=policy)


@pytest.mark.loopback
def test_real_synchronous_rest_workers_match_engine_and_keep_reader(moira_engine,monkeypatch,record_property):
    from concurrent.futures import ThreadPoolExecutor
    from time import perf_counter
    from fastapi.testclient import TestClient
    from moira_server.app import create_app
    from moira_server.config import ServerConfig
    from moira.gochara_windows import window_json_bytes
    monkeypatch.setattr("moira_server.app.create_engine",lambda cfg:moira_engine)
    systems=("Lahiri","True Chitrapaksha")
    bodies=[dict(natal_jd_ut1=2451545.,start_jd_ut1=2460967.,end_jd_ut1=2460968.,
                 policy={"ayanamsa_system":system}) for system in systems]
    expected=[window_json_bytes(moira_engine.gochara_windows(2451545.,2460967.,2460968.,
                policy=GocharaDatePolicy(ayanamsa_system=system))) for system in systems]
    with TestClient(create_app(ServerConfig(prewarm_enabled=False))) as client:
        start=perf_counter()
        sequential=[client.post("/v1/gochara/windows/from-epochs",json=b) for b in bodies]
        record_property("two_one_day_rest_sequential_seconds",perf_counter()-start)
        start=perf_counter()
        with ThreadPoolExecutor(max_workers=2) as executor:
            concurrent=list(executor.map(lambda b:client.post("/v1/gochara/windows/from-epochs",json=b),bodies))
        record_property("two_one_day_rest_concurrent_seconds",perf_counter()-start)
    assert all(r.status_code==200 for r in (*sequential,*concurrent))
    assert [r.content for r in sequential]==expected==[r.content for r in concurrent]
    assert moira_engine.gochara_at(2451545.,2460967.).transit.positions
