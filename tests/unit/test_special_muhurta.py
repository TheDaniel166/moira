"""Primary-text tables, independent rational geometry and boundary contracts."""
from datetime import date
from fractions import Fraction
import importlib
import math

import pytest

from moira import (
    SpecialMuhurtaPolicy, SpecialMuhurtaBoundary, SpecialMuhurtaWindow,
    special_muhurta_from_solar_times, muhurta_yogas_from_longitudes,
)
from moira.spk_reader import get_active_reader
from tests.special_muhurta_support import install_special_sky

# Transcribed by NAME from reviewed primary leaves; intentionally independent
# of implementation indices/tables. Sunday-first source order is preserved.
STARS = "Ashwini|Bharani|Krittika|Rohini|Mrigashira|Ardra|Punarvasu|Pushya|Ashlesha|Magha|Purva Phalguni|Uttara Phalguni|Hasta|Chitra|Swati|Vishakha|Anuradha|Jyeshtha|Mula|Purva Ashadha|Uttara Ashadha|Shravana|Dhanishtha|Shatabhisha|Purva Bhadrapada|Uttara Bhadrapada|Revati".split("|")
SARVARTHA = (
    "Hasta|Mula|Uttara Phalguni|Uttara Ashadha|Uttara Bhadrapada|Pushya|Ashwini",
    "Shravana|Rohini|Mrigashira|Pushya|Anuradha",
    "Ashwini|Uttara Bhadrapada|Krittika|Ashlesha",
    "Rohini|Anuradha|Hasta|Krittika|Mrigashira",
    "Revati|Anuradha|Ashwini|Punarvasu|Pushya",
    "Revati|Anuradha|Ashwini|Punarvasu|Shravana", "Shravana|Rohini|Swati",
)
AMRITA = ("Hasta", "Mrigashira", "Ashwini", "Anuradha", "Pushya", "Revati", "Rohini")
AMIRTHA = (
    "", "Rohini|Mrigashira|Swati|Shravana|Punarvasu",
    "Punarvasu|Pushya|Ashlesha|Magha|Purva Phalguni|Mrigashira|Hasta|Chitra|Swati",
    "Ardra|Punarvasu|Pushya|Ashlesha|Magha|Hasta|Chitra|Swati|Vishakha|Shravana",
    "Ashwini|Punarvasu|Pushya|Magha|Swati", "Ashwini|Bharani|Purva Phalguni|Revati",
    "Krittika|Rohini|Shatabhisha|Swati",
)


@pytest.mark.parametrize("source_day", range(7))
@pytest.mark.parametrize("alternate", [False, True])
def test_complete_source_weekday_tables(source_day, alternate):
    policy = SpecialMuhurtaPolicy(amrita_basis="kalaprakasika_amirtha" if alternate else "sadhana_amrita_siddhi")
    for i, name in enumerate(STARS):
        result = muhurta_yogas_from_longitudes(0, (i+.5)*360/27, weekday=(source_day-1) % 7, policy=policy)
        assert result.moon_nakshatra == name and result.moon_nakshatra_index == i
        amrita, _, sarvartha = result.results
        assert amrita.present == (name in (AMIRTHA if alternate else AMRITA)[source_day].split("|"))
        assert amrita.name == ("Amirtha" if alternate else "Amrita Siddhi")
        assert sarvartha.present == (name in SARVARTHA[source_day].split("|"))
        assert all(r.activity_suitability == "not_evaluated" and r.citations for r in result.results)


def test_every_ravi_pair_inclusive_count_and_wrap():
    for sun in range(27):
        for moon in range(27):
            sequence = list(range(sun, 27)) + list(range(sun))
            count = sequence.index(moon)+1
            result = muhurta_yogas_from_longitudes((sun+.5)*360/27, (moon+.5)*360/27, weekday=0)
            assert result.inclusive_sun_moon_count == count
            assert result.results[1].present == (count in [4, 9, 6, 10, 13, 20])


@pytest.mark.parametrize("i", range(1, 27))
def test_nakshatra_half_open_binary64_edges(i):
    boundary = i*(360/27)
    for x, expected in ((math.nextafter(boundary, -math.inf), i-1), (boundary, i), (math.nextafter(boundary, math.inf), i)):
        r = muhurta_yogas_from_longitudes(x, x, weekday=0)
        assert r.sun_nakshatra_index == r.moon_nakshatra_index == expected


@pytest.mark.parametrize("weekday", range(7))
@pytest.mark.parametrize("daylight", [.25, .5, .73])
def test_rational_vijaya_and_godhuli_visibility_partition(weekday, daylight):
    rise, setting = 2451545., 2451545.+daylight
    half, full = setting-.002, setting
    r = special_muhurta_from_solar_times(weekday=weekday, sunrise_jd_ut1=rise,
        sunset_jd_ut1=setting, half_set_jd_ut1=half, upper_limb_sunset_jd_ut1=full)
    vijaya, godhuli = r.results
    a, b = Fraction.from_float(rise), Fraction.from_float(setting)
    v = vijaya.windows[0]
    assert (v.start.jd_ut1, v.end.jd_ut1) == (float((5*a+10*b)/15), float((4*a+11*b)/15))
    assert v.contains(v.start.jd_ut1) is True and v.contains(v.end.jd_ut1) is False
    h = Fraction.from_float(half)
    assert godhuli.windows[0].start.jd_ut1 == float(h-Fraction(1,120))
    assert godhuli.windows[-1].end.jd_ut1 == float(h+Fraction(1,120))
    if weekday in (3,5):
        assert len(godhuli.windows) == 2
        assert godhuli.windows[0].end.jd_ut1 == full != half
        assert [w.eligibility for w in godhuli.windows] == (["excluded", "not_excluded_by_selected_rule"] if weekday == 3
                                                        else ["not_excluded_by_selected_rule", "excluded"])
    else:
        assert len(godhuli.windows) == 1
    assert r.status == "available"


def test_missing_anchors_remain_independent_and_geometry_only_is_explicit():
    r = special_muhurta_from_solar_times(weekday=3, half_set_jd_ut1=2451545.)
    assert r.status == "partial" and r.results[0].status == "unavailable"
    assert r.results[1].status == "partial" and r.results[1].windows[0].eligibility == "not_evaluated"
    r = special_muhurta_from_solar_times(weekday=3, half_set_jd_ut1=2451545.,
        policy=SpecialMuhurtaPolicy(godhuli_weekday_rule="geometry_only"))
    assert r.results[1].status == "available"
    assert special_muhurta_from_solar_times(weekday=0).status == "unavailable"


@pytest.mark.parametrize("offset", [.002, .02])
def test_godhuli_partition_can_be_inside_or_after_window(offset):
    r = special_muhurta_from_solar_times(weekday=5, half_set_jd_ut1=2451545., upper_limb_sunset_jd_ut1=2451545.+offset)
    assert len(r.results[1].windows) == (2 if offset == .002 else 1)


@pytest.mark.parametrize("bad", [True, "12", float("nan"), float("inf"), -1, 360, 10**1000])
def test_bad_longitudes_reject(bad):
    with pytest.raises((ValueError, TypeError)):
        muhurta_yogas_from_longitudes(bad, 0, weekday=0)


@pytest.mark.parametrize("bad", [True, "1", 1.0, -1, 7, None])
def test_bad_weekday_rejects(bad):
    with pytest.raises((ValueError, TypeError)):
        muhurta_yogas_from_longitudes(0, 0, weekday=bad)


@pytest.mark.parametrize("bad", [{"amrita_basis":"amrita"}, {"godhuli_horizon":"sunset"},
    {"godhuli_weekday_rule":"all_good"}, {"ayanamsa_system":"unknown"}, {"solar_policy":{}}, {"ayanamsa_system":True}])
def test_policy_rejects_conflated_or_untyped_choices(bad):
    with pytest.raises((ValueError, TypeError)):
        SpecialMuhurtaPolicy(**bad)


def test_contradictory_solar_anchors_and_boundary_vessels_reject():
    with pytest.raises(ValueError):
        special_muhurta_from_solar_times(weekday=0, sunrise_jd_ut1=2451545., sunset_jd_ut1=2451544.)
    with pytest.raises(ValueError):
        special_muhurta_from_solar_times(weekday=0, half_set_jd_ut1=2451545., upper_limb_sunset_jd_ut1=2451545.)
    with pytest.raises(ValueError):
        SpecialMuhurtaBoundary("bad", 2451545., 2451546., 2451544.)
    with pytest.raises(ValueError):
        SpecialMuhurtaWindow(SpecialMuhurtaBoundary("a", 2451545., 2451544.9, 2451545.1),
                             SpecialMuhurtaBoundary("b", 2451545.1, 2451545., 2451545.2))


def test_window_membership_preserves_root_uncertainty():
    a = SpecialMuhurtaBoundary("a",2451545.,2451544.9,2451545.1)
    b = SpecialMuhurtaBoundary("b",2451546.,2451545.9,2451546.1)
    w = SpecialMuhurtaWindow(a,b)
    for t, expected in ((2451544.,False),(2451545.,None),(2451545.5,True),(2451546.,None),(2451547.,False)):
        assert w.contains(t) is expected


@pytest.mark.parametrize("day,zone", [(date(2026,3,8),"America/New_York"), (date(2026,11,1),"America/New_York"),
                                     (date(2026,10,8),"Asia/Kolkata")])
def test_analytic_date_composition_and_reader_restore(monkeypatch, day, zone):
    owner, reader, calls, _ = install_special_sky(monkeypatch)
    before = get_active_reader()
    result = owner.special_muhurta_for_date(day, 20, 80, timezone=zone, reader=reader)
    assert get_active_reader() is before
    assert result.status == "available" and len(result.results) == 5
    assert len(result.named.result.intervals) == 2
    assert len({c[1] for c in calls if c[0] == "solar"}) == 3
    for anchor in result.anchors:
        assert (anchor.upper_jd_ut1-anchor.lower_jd_ut1)*86400 <= .1
    half, full = result.anchors[2:4]
    assert half.upper_jd_ut1 < full.lower_jd_ut1
    assert all(w.start.moment and w.end.moment for r in result.results for w in r.windows)


@pytest.mark.parametrize("flag", ["omit_rises", "omit_sets", "multiple", "fail_signal"])
def test_missing_or_unresolved_solar_events_are_typed(monkeypatch, flag):
    owner, reader, _, state = install_special_sky(monkeypatch)
    setattr(state, flag, True)
    result = owner.special_muhurta_for_date(date(2026,10,8), 20,80,timezone="UTC",reader=reader)
    assert result.status in ("partial", "unavailable")
    if flag == "omit_sets":
        assert all(r.status == "available" for r in result.results[2:])
    else:
        assert all(r.status == "unavailable" for r in result.results[2:])


@pytest.mark.parametrize("separation", [0, .0000003, .02])
def test_sun_and_moon_transition_cells_with_overlapping_brackets(separation):
    owner = importlib.import_module("moira.special_muhurta")
    start, end = owner._point("sunrise",2451545.), owner._point("next_sunrise",2451546.)
    def phases(jd):
        # Sun crosses Ashwini->Bharani at .5; Moon crosses Rohini->Mrigashira
        # near it. Ravi holds before and after; any short intervening state
        # inside merged uncertainty is expressly unresolved.
        return ((360/27 + jd-start.jd_ut1-.5) % 360,
                (4*360/27+13*(jd-start.jd_ut1-.5-separation)) % 360)
    results,bands = owner._yoga_cells(start,end,phases,0,SpecialMuhurtaPolicy(),owner._resolve_timezone("UTC"))
    assert len(bands) == (1 if separation < .001 else 2)
    if separation < .001:
        assert "Sun" in bands[0].kind and "Moon" in bands[0].kind
    for r in results:
        for w in r.windows:
            t=(w.start.upper_jd_ut1+w.end.lower_jd_ut1)/2
            match=next(m for m in muhurta_yogas_from_longitudes(*phases(t),weekday=0).results if m.name==r.name)
            assert match.present


def test_sun_only_ingress_changes_ravi_and_wrap_has_one_root():
    owner=importlib.import_module("moira.special_muhurta")
    roots=owner._star_roots(0,lambda jd: ((359.5+jd-2451545.)%360,40+.01*(jd-2451545.)),2451545.,2451546.,.1)
    assert len(roots)==1 and roots[0].lower_jd_ut1 <=2451545.5<=roots[0].upper_jd_ut1
    start,end=owner._point("sunrise",2451545.),owner._point("next_sunrise",2451546.)
    def phases(jd):
        return (360/27+jd-2451545.5,45+.01*(jd-2451545.))
    rows,bands=owner._yoga_cells(start,end,phases,0,SpecialMuhurtaPolicy(),owner._resolve_timezone("UTC"))
    ravi=rows[1]
    assert len(ravi.windows)==1 and ravi.windows[0].end.kind=="Sun_nakshatra"
    assert len(bands)==1


def test_all_public_exports_have_owning_identity():
    import moira
    import moira.facade as facade
    import moira.vedic as vedic
    owner=importlib.import_module("moira.special_muhurta")
    for name in owner.__all__:
        assert getattr(moira,name) is getattr(facade,name) is getattr(vedic,name) is getattr(owner,name)


def test_missing_next_sunrise_preserves_current_evening(monkeypatch):
    from dataclasses import replace
    owner,reader,_,_=install_special_sky(monkeypatch)
    named=importlib.import_module("moira.named_muhurta")
    original=owner._solar_date
    def solar(day,*args):
        r=original(day,*args)
        return replace(r,sunrises=()) if day==date(2026,10,9) else r
    monkeypatch.setattr(owner,"_solar_date",solar)
    monkeypatch.setattr(named,"_solar_date",solar)
    result=owner.special_muhurta_for_date(date(2026,10,8),20,80,timezone="UTC",reader=reader)
    assert result.status=="partial"
    assert all(r.status=="available" for r in result.results[:2])
    assert all(r.unavailable_reasons==("next_sunrise_unavailable",) for r in result.results[2:])


def test_no_ingress_full_day_and_uncertainty_membership(monkeypatch):
    owner,reader,_,_=install_special_sky(monkeypatch)
    result=owner.special_muhurta_for_date(date(2026,10,8),20,80,timezone="UTC",reader=reader)
    for band in result.transition_bands:
        for row in result.results[2:]:
            assert result.contains_yoga(row.name,band.jd_ut1) is None
    with pytest.raises(ValueError):
        result.contains_yoga("Nitya Yoga",2451545.)
    start,end=owner._point("sunrise",2451545.),owner._point("next_sunrise",2451546.)
    rows,bands=owner._yoga_cells(start,end,lambda jd:(1+.1*(jd-2451545.),60+.1*(jd-2451545.)),
                               0,SpecialMuhurtaPolicy(),owner._resolve_timezone("UTC"))
    assert not bands
    assert rows[0].name=="Amrita Siddhi" and len(rows[0].windows)==1
    assert rows[0].windows[0].start==start and rows[0].windows[0].end==end


def test_reader_restore_when_new_position_composition_fails(monkeypatch):
    from moira.muhurta_search import MuhurtaCoverageError
    from moira.spk_reader import OutOfRangeError
    owner,reader,_,_=install_special_sky(monkeypatch)
    before=get_active_reader()
    def fail(*args,**kwargs):
        raise OutOfRangeError("outside", ())
    monkeypatch.setattr(owner,"planet_at",fail)
    with pytest.raises(MuhurtaCoverageError):
        owner.special_muhurta_for_date(date(2026,10,8),20,80,timezone="UTC",reader=reader)
    assert get_active_reader() is before


@pytest.mark.parametrize("phase", [lambda jd:(10,20),lambda jd:((10-jd)%360,20),lambda jd:(float("nan"),20)])
def test_invalid_phase_motion_fails_visibly(phase):
    owner=importlib.import_module("moira.special_muhurta")
    with pytest.raises(RuntimeError,match="forward phase bound"):
        owner._star_roots(0,phase,2451545.,2451546.,.1)
