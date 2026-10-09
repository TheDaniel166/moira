"""Independent source tables, rational clocks, uncertainty and exception scope."""
from dataclasses import replace
from fractions import Fraction
import json
from pathlib import Path

import pytest

from moira.muhurta_dosha import (
    MuhurtaDoshaPolicy, DoshaPhaseSpan, detect_muhurta_doshas,
    muhurta_dosha_catalogue, MC_TABLE, KP_TABLE, KP_DUAL_TABLE,
    FIXED_WIDTH, SCALED_WIDTH, MC_GANDANTA, BP_GANDANTA,
    KP_EXEMPT, MC_NECESSARY, MC_ABHIJIT,
)
from moira.panchanga_shuddhi import ShuddhiBoundary, ShuddhiInterval

SOURCE = json.loads((Path(__file__).parents[1]/"fixtures/muhurta_dosha_sources.json").read_text())


def point(t, uncertainty=0):
    return ShuddhiBoundary("test", float(t), float(t)-uncertainty, float(t)+uncertainty)


def interval(a, b, uncertainty=0):
    return ShuddhiInterval(point(a, uncertainty), point(b, uncertainty))


def event(kind, index, a=0., b=1., uncertainty=0):
    return DoshaPhaseSpan(kind, index, interval(a, b, uncertainty))


def assess(star, jd, *, spans=None, policy=None, **kwargs):
    return detect_muhurta_doshas(0., (star+.5)*360/27, jd_ut1=jd,
        phase_spans=(event("nakshatra", star),) if spans is None else spans,
        policy=policy, **kwargs)


def finding(result, name):
    return next(f for f in result.findings if f.rule_id == name)


@pytest.mark.parametrize("table", [MC_TABLE, KP_TABLE, KP_DUAL_TABLE])
@pytest.mark.parametrize("clock", [FIXED_WIDTH, SCALED_WIDTH])
@pytest.mark.parametrize("duration", [Fraction(3,4), Fraction(1), Fraction(5,4)])
def test_all_vishanadi_source_rows_and_clocks(table, clock, duration):
    offsets = SOURCE["mc_star_offsets" if table == MC_TABLE else "kp_star_offsets"]
    for star, offset in enumerate(offsets):
        policy = MuhurtaDoshaPolicy(vishanadi_profile=table, vishanadi_clock=clock)
        spans = (event("nakshatra", (star-1)%27, -float(duration), 0), event("nakshatra", star, 0, float(duration)))
        result = finding(assess(star, float(duration)/2, spans=spans, policy=policy), "vishanadi")
        windows = [w.window for w in result.witnesses if w.parent_index == star]
        expected = SOURCE["kp_alternative_mula_offsets"] if table == KP_DUAL_TABLE and star == 18 else [offset]
        assert len(windows) == len(expected)
        for window, start in zip(windows, expected):
            a = duration*Fraction(start,60)
            b = a + (Fraction(4,60) if clock == FIXED_WIDTH else duration*Fraction(4,60))
            assert window.start.jd_ut1 == pytest.approx(float(a), abs=1e-14)
            assert window.end.jd_ut1 == pytest.approx(float(b), abs=1e-14)


def test_rohini_commentary_worked_example_and_width_disagreement():
    example = SOURCE["rohini_example"]
    duration = Fraction(example["duration_ghatis"]*60+example["duration_palas"],3600)
    offset = Fraction(example["offset_ghatis"]*60+example["offset_palas"],3600)
    for clock in (FIXED_WIDTH, SCALED_WIDTH):
        f = finding(assess(3, .7, spans=(event("nakshatra",3,0,float(duration)),),
                    policy=MuhurtaDoshaPolicy(vishanadi_clock=clock)), "vishanadi")
        w = f.witnesses[0].window
        assert w.start.jd_ut1 == pytest.approx(float(offset), abs=1e-14)
        width = Fraction(4,60) if clock == FIXED_WIDTH else duration/15
        assert w.end.jd_ut1-w.start.jd_ut1 == pytest.approx(float(width), abs=1e-14)


def test_fixed_width_carryover_is_not_lost_at_next_star():
    spans = (event("nakshatra",18,0,.75), event("nakshatra",19,.75,1.5))
    r = assess(19, .755, spans=spans)
    f = finding(r,"vishanadi")
    assert f.detected is True and f.neutralized is False
    assert any(w.parent_index == 18 and w.detected is True and w.window.end.jd_ut1 > .75 for w in f.witnesses)
    missing = finding(assess(19,.755,spans=spans[1:]),"vishanadi")
    assert missing.detected is None and "carryover" in missing.unavailable_reasons[0]
    normalized = finding(assess(19,.755,spans=spans,policy=MuhurtaDoshaPolicy(vishanadi_clock=SCALED_WIDTH)),"vishanadi")
    assert normalized.detected is False


@pytest.mark.parametrize("weekday",range(7))
def test_both_yamaghantas_against_independent_weekday_tables(weekday):
    for star in range(27):
        r = assess(star,.5,weekday=weekday,sunrise_day=interval(0,1),sunset=point(.5))
        assert finding(r,"yamaghanta_yoga").detected == (star+1 == SOURCE["yamaghanta_stars_one_based_sunday_first"][weekday])
        w = finding(r,"yamaghanta_kala").witnesses[0].window
        n = SOURCE["yamaghanta_daylight_sixteenths_one_based_sunday_first"][weekday]
        assert w.start.jd_ut1 == (n-1)/32
        assert w.end.jd_ut1 == n/32


@pytest.mark.parametrize("weekday",range(7))
def test_yamaghanta_exact_half_open_boundaries_and_necessary_exception(weekday):
    n = SOURCE["yamaghanta_daylight_sixteenths_one_based_sunday_first"][weekday]
    a,b=(n-1)/32,n/32
    p=MuhurtaDoshaPolicy(parihara_profiles=(MC_NECESSARY,))
    for jd,present,neutral in [(a-1e-8,False,False),(a,True,True),((a+b)/2-1e-8,True,True),((a+b)/2,True,False),(b-1e-8,True,False),(b,False,False)]:
        r=assess(3,jd,weekday=weekday,sunrise_day=interval(0,1),sunset=point(.5),necessary_activity=True,policy=p)
        f=finding(r,"yamaghanta_kala")
        assert (f.detected,f.neutralized)==(present,neutral)
    for necessary,expected in [(False,False),(None,None)]:
        f=finding(assess(3,a,weekday=weekday,sunrise_day=interval(0,1),sunset=point(.5),necessary_activity=necessary,policy=p),"yamaghanta_kala")
        assert f.detected is True and f.neutralized is expected


@pytest.mark.parametrize("profile,fixture",[(MC_GANDANTA,"mc_half_width_ghatis"),(BP_GANDANTA,"bp_half_width_ghatis")])
@pytest.mark.parametrize("kind,count",[("nakshatra",27),("tithi",30),("lagna",12)])
def test_every_gandanta_parent_and_exact_edges(profile,fixture,kind,count):
    data=SOURCE["gandanta"]
    first=set(range(0,30,5)) if kind=="tithi" else set(data[kind+"_first_zero_based"])
    last=set(range(4,30,5)) if kind=="tithi" else set(data[kind+"_last_zero_based"])
    width=data[fixture][kind]/60
    for index in range(count):
        for jd in [width-1e-8,width,width+1e-8,1-width-1e-8,1-width,1-width+1e-8]:
            moon=(index+.5)*360/count if kind in ("nakshatra","tithi") else 45.
            r=detect_muhurta_doshas(0.,moon,jd_ut1=jd,
                lagna_sidereal_longitude=(index+.5)*30 if kind=="lagna" else None,
                phase_spans=(event(kind,index),),policy=MuhurtaDoshaPolicy(gandanta_profile=profile))
            f=finding(r,kind+"_gandanta")
            assert f.detected == ((index in first and jd < width) or (index in last and jd >= 1-width))


def test_temporal_lagna_width_is_not_fixed_degrees_and_short_parent_is_clipped():
    r=detect_muhurta_doshas(0.,45.,jd_ut1=.002,lagna_sidereal_longitude=15.,phase_spans=(event("lagna",0,0,.004),))
    f=finding(r,"lagna_gandanta")
    assert f.detected is True
    w=f.witnesses[0]
    assert w.window.end.jd_ut1==.004
    assert w.unclipped_window.end.jd_ut1==.5/60


@pytest.mark.parametrize("table",[MC_TABLE,KP_TABLE,KP_DUAL_TABLE])
def test_seven_star_exemption_is_optional_and_source_scoped(table):
    offsets=SOURCE["mc_star_offsets" if table==MC_TABLE else "kp_star_offsets"]
    exempt=set(SOURCE["kp_exempt_stars_one_based"])
    for star,offset in enumerate(offsets):
        p=MuhurtaDoshaPolicy(vishanadi_profile=table,parihara_profiles=(KP_EXEMPT,))
        f=finding(assess(star,(offset+2)/60,policy=p),"vishanadi")
        assert f.detected is True
        assert f.neutralized == (table!=MC_TABLE and star+1 in exempt)
        assert f.witnesses[0].window is not None
    ordinary=finding(assess(3,42/60,policy=MuhurtaDoshaPolicy(vishanadi_profile=KP_TABLE)),"vishanadi")
    assert ordinary.detected is True and ordinary.neutralized is False


@pytest.mark.parametrize("profile",[MC_GANDANTA,BP_GANDANTA])
def test_commentarial_abhijit_exception_keeps_gandanta_evidence(profile):
    # Wednesday is deliberately not suppressed: this exception's geometry does
    # not overwrite the separate named-Abhijit Wednesday eligibility rule.
    p=MuhurtaDoshaPolicy(gandanta_profile=profile,parihara_profiles=(MC_ABHIJIT,))
    r=assess(9,.5,spans=(event("nakshatra",9,.49,1.49),),weekday=3,
        sunrise_day=interval(0,1.1),sunset=point(1),policy=p)
    f=finding(r,"nakshatra_gandanta")
    assert f.detected is True and f.neutralized == (profile==MC_GANDANTA)
    assert f.witnesses[0].detected is True
    assert f.parihara[0].state == ("applied" if profile==MC_GANDANTA else "excluded")
    missing=replace(r.inputs,sunset=None)
    r2=detect_muhurta_doshas(**{name:getattr(missing,name) for name in missing.__dataclass_fields__},policy=p)
    assert finding(r2,"nakshatra_gandanta").neutralized is (None if profile==MC_GANDANTA else False)


def test_uncertain_brackets_never_become_affirmative_cancellation():
    p=MuhurtaDoshaPolicy(parihara_profiles=(MC_NECESSARY,))
    r=assess(3,9/32,weekday=0,sunrise_day=interval(0,1,1e-5),sunset=point(.5,1e-5),policy=p,necessary_activity=True)
    f=finding(r,"yamaghanta_kala")
    assert f.detected is None and f.neutralized is None
    assert f.state=="uncertain"
    assert all(e.state!="applied" for e in f.parihara)


@pytest.mark.parametrize('necessary,expected', [(True, 'uncertain'), (None, 'unavailable'), (False, 'not_satisfied')])
def test_parihara_distinguishes_uncertain_half_boundary_from_missing_prerequisite(necessary, expected):
    p = MuhurtaDoshaPolicy(parihara_profiles=(MC_NECESSARY,))
    # Sunday daytime fault is [9/32,10/32); its midpoint is uncertain,
    # while presence of the raw fault is unambiguous.
    r = assess(3, 9.5/32, weekday=0, sunrise_day=interval(0, 1, 1e-5),
               sunset=point(.5, 1e-5), policy=p, necessary_activity=necessary)
    f = finding(r, 'yamaghanta_kala')
    assert f.detected is True
    assert f.parihara[0].state == expected
    assert f.neutralized is (False if necessary is False else None)


@pytest.mark.parametrize("kwargs",[
    {"weekday":True},{"weekday":"1"},{"weekday":7},{"necessary_activity":1},
    {"necessary_activity":"true"},{"lagna_sidereal_longitude":360},
    {"phase_spans":[]},{"sunset":point(.5)},
    {"phase_spans":(event("nakshatra",2),)},
    {"phase_spans":(event("nakshatra",2,-1,0),event("nakshatra",3,.1,1))},
    {"phase_spans":(event("nakshatra",2,-1,0),event("nakshatra",4,0,1))},
    {"sunrise_day":interval(0,1),"sunset":point(1)},
])
def test_strict_direct_admission(kwargs):
    with pytest.raises(ValueError):
        detect_muhurta_doshas(0.,45.,jd_ut1=.5,**kwargs)


@pytest.mark.parametrize("kwargs",[
    {"vishanadi_profile":"all"},{"vishanadi_clock":"arc"},
    {"gandanta_profile":"degrees"},{"parihara_profiles":[KP_EXEMPT]},
    {"parihara_profiles":(KP_EXEMPT,KP_EXEMPT)},
    {"parihara_profiles":("any_benefic",)},{"solver_tolerance_seconds":True},
    {"ayanamsa_system":"unknown"},
])
def test_strict_policy(kwargs):
    with pytest.raises((ValueError,TypeError)):
        MuhurtaDoshaPolicy(**kwargs)


@pytest.mark.parametrize("value",[True,"0",float("nan"),float("inf"),-1,360])
def test_bad_longitudes(value):
    with pytest.raises(ValueError):
        detect_muhurta_doshas(0.,value,jd_ut1=.5)


def test_catalogue_declares_profiles_and_exclusions():
    c=muhurta_dosha_catalogue()
    assert len(c.profiles)==12 and len(c.rules)==6
    assert len({p.profile for p in c.profiles})==12
    assert all(p.citations for p in c.profiles)
    assert "strength_aspect_navamsa_parihara" in c.excluded_rules
