"""VED-017 contracts, source-derived testimony and adversarial event semantics."""
from dataclasses import replace
from datetime import datetime, timezone
import json
from pathlib import Path
from importlib import import_module

import pytest
from moira.gochara import GOCHARA_PLANETS, GocharaPolicy, GocharaVedhaMode, GocharaBavMode
from moira.gochara_dated import GocharaDatePolicy, GocharaBirthLocation, GocharaNatalBavMode
from moira.gochara_windows import (
    gochara_windows, gochara_windows_for_datetimes, gochara_window_capabilities,
    GocharaWindowSearchPolicy, GocharaWindowSearchLimits, GocharaWindowDomainError,
    GocharaWindowBudgetError, GocharaWindowUnresolvedError, window_json_bytes,
)
from tools.gochara_window_cases import install, START, NATAL


def calculate(**kwargs):
    return gochara_windows(NATAL,START,START+1,reader=object(),**kwargs)


@pytest.mark.parametrize("kwargs,exception", [
    ({"natal_jd_ut1":True},TypeError), ({"start_jd_ut1":float("nan")},ValueError),
    ({"end_jd_ut1":START},ValueError), ({"end_jd_ut1":START-1},ValueError),
    ({"start_jd_ut1":2415020.4},GocharaWindowDomainError),
    ({"end_jd_ut1":2488434.5},GocharaWindowDomainError),
    ({"subjects":("Moon","Moon")},ValueError), ({"subjects":("Rahu",)},ValueError),
    ({"subjects":()},ValueError), ({"subjects":"Moon"},ValueError),
    ({"policy":"Lahiri"},TypeError), ({"search_policy":{}},TypeError),
    ({"birth_location":GocharaBirthLocation(0,0)},ValueError),
    ({"end_jd_ut1":START+367},GocharaWindowBudgetError),
])
def test_rejects_before_reader_access(monkeypatch,kwargs,exception):
    search=import_module("moira._gochara_window_search")
    monkeypatch.setattr(search,"get_reader",lambda:pytest.fail("invalid request acquired reader"))
    args=dict(natal_jd_ut1=NATAL,start_jd_ut1=START,end_jd_ut1=START+1)|kwargs
    with pytest.raises(exception):
        gochara_windows(**args)


@pytest.mark.parametrize("value", [False,float("nan"),float("inf"),0.,.001,61.,"1"])
def test_invalid_tolerance(value):
    with pytest.raises((ValueError,TypeError)):
        GocharaWindowSearchPolicy(value)


@pytest.mark.parametrize("name", [f for f in GocharaWindowSearchLimits.__dataclass_fields__])
@pytest.mark.parametrize("value", [True,0,-1,1.5,10**9])
def test_limit_admission(name,value):
    with pytest.raises(ValueError):
        GocharaWindowSearchLimits(**{name:value})


def test_capabilities_are_resource_free_and_all_twelve(monkeypatch):
    from moira.sidereal import Ayanamsa
    monkeypatch.setattr("moira.spk_reader.get_reader",lambda:pytest.fail("reader acquired"))
    caps=gochara_window_capabilities()
    assert caps.ayanamsas==tuple(Ayanamsa.ALL)
    assert caps.participants==GOCHARA_PLANETS
    assert not caps.installed_resources_probed


@pytest.mark.parametrize("coefficients,expected,directions", [
    ((29.9,.2),(.5,),(1,)), ((30.1,-.2),(.5,),(-1,)),
    ((30.16,-1.,1.),(.2,.8),(-1,1)),
    ((29.936,.56,-1.4,1.),(.2,.4,.8),(1,-1,1)),
    ((359.9,.2),(.5,),(1,)),
])
def test_analytic_crossings_cannot_disappear_inside_seed_step(monkeypatch,coefficients,expected,directions):
    install(monkeypatch,{"Moon":coefficients})
    result=calculate(search_policy=GocharaWindowSearchPolicy(require_resolved=True))
    events=tuple(e for e in result.events if e.planet=="Moon")
    assert len(events)==len(expected)
    assert tuple(e.direction for e in events)==directions
    for e,root in zip(events,expected):
        assert e.lower_jd_ut1<=START+root<=e.upper_jd_ut1
        assert (e.upper_jd_ut1-e.lower_jd_ut1)*86400<=1
    assert result.coverage.domain_accounted and result.coverage.events_resolved
    assert result.coverage.certain_duration_days+result.coverage.uncertain_duration_days==1


@pytest.mark.parametrize("coefficients",[(29.75,1.,-1.),(30.25,-1.,1.)])
def test_tangent_contacts_are_retained_without_false_uniqueness(monkeypatch,coefficients):
    install(monkeypatch,{"Moon":coefficients})
    result=calculate()
    assert any(r.start_jd_ut1<=START+.5<=r.end_jd_ut1 for r in result.regions if r.kind=="unresolved_band")
    assert not result.coverage.events_resolved
    with pytest.raises(GocharaWindowUnresolvedError):
        calculate(search_policy=GocharaWindowSearchPolicy(require_resolved=True))


@pytest.mark.parametrize("coefficients",[(30.,.2),(29.8,.2),(360.,-.2)])
def test_request_edge_root_is_retained(monkeypatch,coefficients):
    install(monkeypatch,{"Moon":coefficients})
    result=calculate()
    assert result.events
    assert result.regions[0].include_start and result.regions[-1].include_end


def test_simultaneous_candidates_keep_individual_evidence_and_order_uncertainty(monkeypatch):
    install(monkeypatch,{"Moon":(29.9,.2),"Venus":(89.9,.2)})
    result=calculate()
    bands=[r for r in result.regions if r.kind=="unresolved_band"]
    assert len(result.events)==2 and len(bands)==1
    assert bands[0].event_ids==(0,1)
    assert "event_order_unresolved" in bands[0].reasons


_RULES=json.loads((Path(__file__).parents[1]/"fixtures/gochara_phaladeepika_26.json").read_text())["rules"]
_PAIRS=[(planet,house,blocker) for planet,row in _RULES.items() for house,blocker in row["vedha"]]


@pytest.mark.parametrize("rotation",range(12))
@pytest.mark.parametrize("subject,house,blocking_house",_PAIRS)
def test_every_source_pair_rotation_and_possible_blocker_changes_stationary_subject(monkeypatch,rotation,subject,house,blocking_house):
    sign=(rotation+house-1)%12
    block=(rotation+blocking_house-1)%12
    # Keep all nonparticipants safely away from the blocking sign.
    safe=(block+5)%12
    for blocker in GOCHARA_PLANETS:
        if blocker==subject:
            continue
        curves={p:(safe*30+15.,) for p in GOCHARA_PLANETS}
        curves[subject]=(sign*30+15.,)
        curves[blocker]=(block*30-.1,.2)
        install(monkeypatch,curves,natal_sign=rotation)
        result=calculate(subjects=(subject,))
        assert len(result.subject_views)==1 and result.subject_views[0].planet==subject
        assert all(len(s.planets)==7 for s in result.states)
        before,after=(next(p for p in result.states[r.state_id].planets if p.planet==subject)
                      for r in (result.regions[0],result.regions[-1]))
        assert before.sign_index==after.sign_index==sign
        assert not before.witnesses
        assert len(after.witnesses)==1 and after.witnesses[0].blocker==blocker
        exempt=blocker in _RULES[subject]["exempt"]
        assert after.witnesses[0].exempt is exempt
        assert after.vedha_status==("unobstructed" if exempt else "blocked")


def test_bav_once_and_snapshot_resolution_and_baseline_omission(monkeypatch):
    calls=install(monkeypatch,{"Moon":(29.9,.2)})
    dated=import_module("moira.gochara_dated")
    original=dated.bhinnashtakavarga
    count=[]
    def bav(*args,**kwargs):
        count.append(args[0])
        return original(*args,**kwargs)
    monkeypatch.setattr(dated,"bhinnashtakavarga",bav)
    policy=GocharaDatePolicy(natal_bav_mode=GocharaNatalBavMode.COMPUTE_RAW,
        gochara_policy=GocharaPolicy(vedha_mode=GocharaVedhaMode.BASELINE_ONLY,bav_mode=GocharaBavMode.REQUIRE_ALL_RAW))
    result=calculate(policy=policy,birth_location=GocharaBirthLocation(28.6,77.2))
    assert calls.count(NATAL)==1 and tuple(count)==GOCHARA_PLANETS
    for state in result.states:
        for row in state.planets:
            table=next(t for t in result.natal.raw_bav if t.planet==row.planet)
            assert row.raw_bav_rekhas==table.rekhas[row.sign_index]
            assert row.vedha_status in ("omitted_by_policy","not_applicable")
    for sample in result.samples:
        snap=result.resolve_sample(sample.id)
        assert snap.transit==sample.epoch
        assert snap.natal==result.natal.epoch


def test_integrity_and_exclusion_accounting_cannot_be_forged(monkeypatch):
    install(monkeypatch,{"Moon":(29.9,.2)})
    result=calculate()
    patches=[{"exclusions":()}, {"regions":result.regions[1:]},
        {"states":(replace(result.states[0],id=9),*result.states[1:])},
        {"samples":(replace(result.samples[0],state_id=100),*result.samples[1:])}]
    for patch in patches:
        with pytest.raises((ValueError,TypeError)):
            replace(result,**patch)
    bad=replace(result.events[0],kind="possible_contact",direction=None,count=None,reasons=("unproved",))
    with pytest.raises(ValueError):
        replace(result,events=(bad,))
    object.__setattr__(result.natal,"natal_sign_indices",())
    with pytest.raises(ValueError,match="natal context changed"):
        replace(result)


@pytest.mark.parametrize("kind",["evaluations","root_iterations","subdivisions","events","cells","samples","evidence","output_bytes"])
def test_finite_caps_fail_without_partial_success(monkeypatch,kind):
    install(monkeypatch,{"Moon":(30.16,-1.,1.)})
    with pytest.raises(GocharaWindowBudgetError) as caught:
        calculate(search_policy=GocharaWindowSearchPolicy(limits=GocharaWindowSearchLimits(**{"max_"+kind:1})))
    assert caught.value.limit_kind==kind


def test_nested_event_and_region_integrity_rejects_mutable_and_boolean_references(monkeypatch):
    install(monkeypatch,{"Moon":(29.9,.2)})
    result=calculate()
    event=result.events[0]
    for patch in ({"reasons":[]},{"count":True},{"clipped_start":1},{"continuous_branch":1}):
        with pytest.raises((ValueError,TypeError)):
            replace(event,**patch)
    certain=next(r for r in result.regions if r.kind=="certain")
    for patch in ({"state_id":True},{"sample_id":False},{"event_ids":[]},{"reasons":[]}):
        with pytest.raises((ValueError,TypeError)):
            replace(certain,**patch)
    with pytest.raises(ValueError):
        replace(result,subjects=list(result.subjects))
    with pytest.raises(ValueError):
        replace(result,civil_inputs=["a","b","c"])
    ids=[o.id for o in result.selected_options]
    assert "forecast.dated_events" in ids
    assert "forecast.dated_events" not in [o.id for o in result.natal.policy.selected_options]


def test_metered_reader_owns_point_cache_even_when_serving_reader_is_warm():
    from types import SimpleNamespace
    from threading import local
    from moira.planets import _READER_CACHE_LOCAL_ATTR,_reader_thread_caches
    from moira._event_search.resources import MeteredReader
    owner=SimpleNamespace()
    setattr(owner,_READER_CACHE_LOCAL_ATTR,local())
    warm=_reader_thread_caches(owner)
    a,b=MeteredReader(owner,object()),MeteredReader(owner,object())
    assert _reader_thread_caches(a) is not warm
    assert _reader_thread_caches(a) is not _reader_thread_caches(b)


def test_exact_size_cap_and_reader_context_restored(monkeypatch):
    from moira.spk_reader import get_active_reader,use_reader_override
    install(monkeypatch)
    result=calculate()
    # Limit value itself changes the JSON; solve this tiny decimal-width fixed point.
    size=len(window_json_bytes(result))
    for _ in range(3):
        policy=GocharaWindowSearchPolicy(limits=GocharaWindowSearchLimits(max_output_bytes=size))
        size=len(window_json_bytes(replace(result,search_policy=policy)))
    outer=object()
    with use_reader_override(outer):
        accepted=calculate(search_policy=GocharaWindowSearchPolicy(limits=GocharaWindowSearchLimits(max_output_bytes=size)))
        assert len(window_json_bytes(accepted))==size
        assert get_active_reader() is outer
        with pytest.raises(GocharaWindowBudgetError):
            calculate(search_policy=GocharaWindowSearchPolicy(limits=GocharaWindowSearchLimits(max_output_bytes=size-1)))
        assert get_active_reader() is outer
        above=calculate(search_policy=GocharaWindowSearchPolicy(limits=GocharaWindowSearchLimits(max_output_bytes=size+1)))
        assert len(window_json_bytes(above))<=size+1


def test_civil_times_convert_once_and_reject_naive(monkeypatch):
    install(monkeypatch)
    julian=import_module("moira.julian")
    calls=[]
    monkeypatch.setattr(julian,"jd_from_datetime",lambda v: v.day)
    def to_ut(v):
        calls.append(v)
        return {1:NATAL,2:START,3:START+1}[v]
    monkeypatch.setattr(julian,"utc_to_ut1",to_ut)
    values=tuple(datetime(2026,1,d,tzinfo=timezone.utc) for d in (1,2,3))
    result=gochara_windows_for_datetimes(*values,reader=object())
    assert calls==[1,2,3] and len(result.civil_inputs)==3
    with pytest.raises(ValueError):
        gochara_windows_for_datetimes(datetime(2026,1,1),*values[1:])


def test_coarse_and_precise_angular_lifts_cannot_erase_a_real_root():
    from moira._event_search.isolation import Signal,isolate
    from moira._event_search.intervals import Interval as I
    from moira._event_search.budgets import WorkMeter
    def signal(a,b,coarse):
        lift=180 if coarse else -180
        return Signal(I(a-.5+lift,b-.5+lift),I.point(1.),I.point((a+b)/2-.5+lift))
    meter=WorkMeter(GocharaWindowSearchLimits(),kinds=("evaluations","root_iterations","subdivisions"))
    result=isolate(signal,0.,1.,targets=(180.,),period=360.,tolerance=.1,meter=meter)
    assert len(result.roots)==1
    assert result.roots[0].target==180 and result.roots[0].lower<=.5<=result.roots[0].upper


def test_a_proved_crossing_can_have_an_unacceptable_time_width():
    from moira._gochara_window_search import classify_root
    from moira._event_search.isolation import Signal,PossibleRoot
    from moira._event_search.intervals import Interval as I
    def signal(a,b,coarse):
        return Signal(I(a-.5+30,b-.5+30),I.point(1.),I.point((a+b)/2-.5+30))
    event=classify_root(signal,PossibleRoot(30.,.49,.51),0.,1.,1.,"Sun",0)
    assert event.kind=="crossing" and event.count==1 and event.direction==1
    assert event.reasons==("boundary_width_exceeds_requested_tolerance",)


def test_fresh_point_brackets_cannot_prove_full_interval_branch_existence():
    from moira._gochara_window_search import classify_root
    from moira._event_search.isolation import Signal,PossibleRoot
    from moira._event_search.intervals import Interval as I
    def signal(a,b,coarse):
        center=I.point((a+b)/2-.5+30) if a==b else I(29.,31.)
        return Signal(I(29.,31.),I.point(1.),center)
    event=classify_root(signal,PossibleRoot(30.,.499999,.500001),0.,1.,1.,"Sun",0)
    assert event.kind=="possible_contact" and event.count is None


def test_facade_admission_precedes_missing_reader():
    from moira import Moira
    class NoReader:
        gochara_windows=Moira.gochara_windows
        @property
        def _reader(self):
            pytest.fail("invalid facade request touched reader")
    with pytest.raises(ValueError):
        NoReader().gochara_windows(NATAL,START,START)


def test_mutated_nested_limits_cannot_bypass_admission(monkeypatch):
    install(monkeypatch)
    limits=GocharaWindowSearchLimits()
    object.__setattr__(limits,"max_range_days",10000)
    with pytest.raises(ValueError):
        calculate(search_policy=GocharaWindowSearchPolicy(limits=limits))


def test_scientific_gap_retains_source_seam_reason(monkeypatch):
    from moira._event_search.isolation import isolate
    from moira._event_search.intervals import EnclosureUnavailable
    from moira._event_search.budgets import WorkMeter
    def seam(a,b,coarse):
        raise EnclosureUnavailable("serving_descriptor_seam_requires_split")
    meter=WorkMeter(GocharaWindowSearchLimits(),kinds=("evaluations","root_iterations","subdivisions"))
    result=isolate(seam,0.,.000001,tolerance=1.,meter=meter)
    assert result.unresolved==((0.,.000001,"serving_descriptor_seam_requires_split"),)


@pytest.mark.parametrize("kind",["evaluations","root_iterations","subdivisions","events","cells","samples","evidence"])
def test_each_measured_work_cap_below_at_and_above(monkeypatch,kind):
    install(monkeypatch,{"Moon":(29.936,.56,-1.4,1.)})
    count=dict(calculate().work)[kind]
    assert count>1
    for cap in (count,count+1):
        result=calculate(search_policy=GocharaWindowSearchPolicy(
            limits=GocharaWindowSearchLimits(**{"max_"+kind:cap})))
        assert dict(result.work)[kind]==count
    with pytest.raises(GocharaWindowBudgetError) as caught:
        calculate(search_policy=GocharaWindowSearchPolicy(
            limits=GocharaWindowSearchLimits(**{"max_"+kind:count-1})))
    assert caught.value.limit_kind==kind


@pytest.mark.parametrize("days",[365,366,367])
def test_duration_below_at_and_above_published_maximum(monkeypatch,days):
    install(monkeypatch)
    if days>366:
        with pytest.raises(GocharaWindowBudgetError) as failure:
            gochara_windows(NATAL,START,START+days,reader=object())
        assert failure.value.limit_kind=="range_days"
    else:
        result=gochara_windows(NATAL,START,START+days,reader=object())
        assert result.coverage.domain_accounted and result.end_jd_ut1-result.start_jd_ut1==days


def test_unrepresentable_open_gap_is_retained_and_request_edge_witnesses_are_owned():
    from math import nextafter,inf
    from types import SimpleNamespace
    from moira._gochara_window_partition import partition
    from moira._event_search.budgets import WorkMeter
    def event(index,a,b):
        return SimpleNamespace(id=index,lower_jd_ut1=a,upper_jd_ut1=b,reasons=())
    def run(start,end,events):
        samples=[]
        def state(t):
            samples.append(t)
            return 0,len(samples)-1
        regions=partition(start,end,events,(),state,
            WorkMeter(GocharaWindowSearchLimits(),kinds=("cells",)))
        for region in regions:
            if region.kind=="certain":
                t=samples[region.sample_id]
                assert region.start_jd_ut1<=t<=region.end_jd_ut1
                assert t!=region.start_jd_ut1 or region.include_start
                assert t!=region.end_jd_ut1 or region.include_end
        return regions
    a=START+1
    regions=run(START,START+2,(event(0,START+.2,a),event(1,nextafter(a,inf),START+1.8)))
    assert len(regions)==3 and regions[1].kind=="unresolved_band"
    assert regions[1].reasons==("no_representable_interior_witness",)
    assert regions[1].event_ids==(0,1)
    for start in (START,nextafter(START,inf)):
        end=start+1
        run(start,end,(event(0,nextafter(start,inf),nextafter(end,-inf)),))
