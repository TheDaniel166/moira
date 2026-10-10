"""Text-derived arithmetic, strict admission, and controlled event invariants."""
from dataclasses import replace
from datetime import date, datetime, timezone
from fractions import Fraction
import math

import pytest

from moira import NamedMuhurtaPolicy, named_muhurta_from_solar_times
from moira.daily_panchanga import _civil_bounds, _resolve_timezone
from moira.julian import jd_from_datetime
from moira.muhurta_search import MuhurtaCoverageError, MuhurtaResourceError
from moira.spk_reader import MissingKernelError, OutOfRangeError, get_active_reader, use_reader_override
from tests.named_muhurta_support import install_analytic_solar


def rational_endpoints(result):
    """Independent rational reading: MC eighth fifteenth, Arunadatta 4/2 ghatis."""
    rise = Fraction.from_float(result.sunrise.jd_ut1)
    setting = Fraction.from_float(result.sunset.jd_ut1)
    previous = Fraction.from_float(result.previous_sunset.jd_ut1)
    abhijit = ((8*rise + 7*setting)/15, (7*rise + 8*setting)/15)
    if result.policy.brahma_basis == "arunadatta_fixed_ghati":
        brahma = (rise-Fraction(4, 60), rise-Fraction(2, 60))
    else:
        brahma = ((2*previous+13*rise)/15, (previous+14*rise)/15)
    return tuple(tuple(map(float, pair)) for pair in (abhijit, brahma))


@pytest.mark.parametrize("basis", ["arunadatta_fixed_ghati", "legacy_proportional_night_14"])
@pytest.mark.parametrize("day_hours,night_hours", [(12, 12), (15, 9), (8, 16), (1, 23)])
def test_source_formulas_against_rational_reading(basis, day_hours, night_hours):
    r = named_muhurta_from_solar_times(2451545., 2451545.+day_hours/24,
        2451545.-night_hours/24, weekday=0, policy=NamedMuhurtaPolicy(brahma_basis=basis))
    assert r.status == "available" and r.solar_policy_applied is False
    for interval, expected in zip(r.intervals, rational_endpoints(r)):
        assert (interval.start_jd_ut1, interval.end_jd_ut1) == expected
        assert interval.citations and interval.start is None
        assert interval.contains(interval.start_jd_ut1) is True
        assert interval.contains(math.nextafter(interval.start_jd_ut1, -math.inf)) is False
        assert interval.contains(math.nextafter(interval.end_jd_ut1, -math.inf)) is True
        assert interval.contains(interval.end_jd_ut1) is False


@pytest.mark.parametrize("weekday", range(7))
def test_selected_weekday_exclusion_preserves_geometry(weekday):
    source = named_muhurta_from_solar_times(2451545, 2451545.5, weekday=weekday)
    geometry = named_muhurta_from_solar_times(2451545, 2451545.5, weekday=weekday,
        policy=NamedMuhurtaPolicy(abhijit_weekday_rule="geometry_only"))
    a, b = source.intervals[0], geometry.intervals[0]
    assert a.eligibility == ("excluded" if weekday == 2 else "not_excluded_by_selected_rule")
    assert b.eligibility == "not_evaluated"
    assert a.start_jd_ut1 == b.start_jd_ut1 and a.end_jd_ut1 == b.end_jd_ut1
    assert a.contains(a.start_jd_ut1) is True


def test_raman_transcription_discrepancy_is_not_frozen_as_truth():
    # PDF109 says 06:10-18:45 yet uses midpoint12:25; arithmetic yields12:27:30.
    midnight = jd_from_datetime(datetime(2000, 1, 1, tzinfo=timezone.utc))
    r = named_muhurta_from_solar_times(midnight+370/1440, midnight+1125/1440, weekday=5)
    a = r.intervals[0]
    assert ((a.start_jd_ut1+a.end_jd_ut1)/2-midnight)*86400 == pytest.approx(44850, abs=.0001)
    assert (a.end_jd_ut1-a.start_jd_ut1)*86400 == pytest.approx(3020, abs=.0001)


def test_missing_anchors_are_window_specific():
    r = named_muhurta_from_solar_times(2451545, weekday=0)
    assert r.status == "partial"
    assert r.intervals[0].unavailable_reasons == ("following_sunset_absent",)
    assert r.intervals[0].contains(2451545) is None
    assert r.intervals[1].status == "available"
    r = named_muhurta_from_solar_times(2451545, 2451545.5, weekday=0,
        policy=NamedMuhurtaPolicy(brahma_basis="legacy_proportional_night_14"))
    assert r.status == "partial"
    assert r.intervals[1].unavailable_reasons == ("previous_sunset_absent",)


@pytest.mark.parametrize("changes", [
    {"sunrise_jd_ut1": True}, {"sunrise_jd_ut1": "2451545"}, {"sunrise_jd_ut1": float("nan")},
    {"sunrise_jd_ut1": float("inf")}, {"sunrise_jd_ut1": 10**400}, {"sunrise_jd_ut1": -1e9},
    {"sunset_jd_ut1": 2451545}, {"previous_sunset_jd_ut1": 2451546},
    {"weekday": True}, {"weekday": 2.0}, {"weekday": 7}, {"weekday": -1}, {"policy": {}},
])
def test_direct_rejects_invalid_inputs(changes):
    with pytest.raises((TypeError, ValueError)):
        named_muhurta_from_solar_times(**({"sunrise_jd_ut1": 2451545, "weekday": 0} | changes))


@pytest.mark.parametrize("changes", [
    {"brahma_basis": "universal"}, {"abhijit_weekday_rule": "ignore"},
    {"sunrise_definition": "rashtriya_upper_limb"}, {"solver_tolerance_seconds": True},
    {"solver_tolerance_seconds": .001}, {"solver_tolerance_seconds": 2},
    {"solver_tolerance_seconds": float("nan")},
])
def test_policy_rejects_unadmitted_choices(changes):
    with pytest.raises((TypeError, ValueError)):
        NamedMuhurtaPolicy(**changes)


def test_interval_and_anchor_evidence_cannot_be_forged_into_valid_states():
    r = named_muhurta_from_solar_times(2451545, 2451545.5, weekday=0)
    with pytest.raises(ValueError):
        replace(r.sunrise, lower_jd_ut1=2451546)
    for changes in ({"status": "unavailable"}, {"end_jd_ut1": None},
                    {"unavailable_reasons": ("absent",)}, {"start_upper_jd_ut1": 2451546}):
        with pytest.raises(ValueError):
            replace(r.intervals[0], **changes)
    with pytest.raises(ValueError):
        replace(r, intervals=r.intervals[::-1])


@pytest.mark.parametrize("day,zone,hours", [
    (date(2026, 3, 8), "America/New_York", 23),
    (date(2026, 11, 1), "America/New_York", 25),
    (date(2026, 10, 8), "Asia/Kolkata", 24),
])
def test_date_composition_root_bounds_dst_and_reader_restore(monkeypatch, day, zone, hours):
    owner, reader, calls, _ = install_analytic_solar(monkeypatch)
    outer = object()
    with use_reader_override(outer):
        r = owner.named_muhurta_for_date(day, 20, 80, timezone=zone, reader=reader)
        assert get_active_reader() is outer
    assert len([c for c in calls if c[0] == "solar"]) == 3
    assert r.result.status == "available" and r.result.solar_policy_applied
    assert r.result.weekday == day.weekday()
    assert r.reader_binding == "caller_owned_reader" and r.kernel_label == "analytic solar fixture"
    assert r.clock_jd_tt > r.clock_jd_ut1 and r.delta_t_source == "analytic clock"
    middle = r.solar_dates[1]
    assert (middle.civil_end.jd_ut1-middle.civil_start.jd_ut1)*24 == pytest.approx(hours, abs=1e-7)
    true_rise = jd_from_datetime(datetime.combine(day, datetime.min.time().replace(hour=6), _resolve_timezone(zone)))
    assert r.result.sunrise.lower_jd_ut1 <= true_rise <= r.result.sunrise.upper_jd_ut1
    for interval, expected in zip(r.result.intervals, rational_endpoints(r.result)):
        assert (interval.start_jd_ut1, interval.end_jd_ut1) == expected
        assert interval.start_upper_jd_ut1-interval.start_lower_jd_ut1 <= .101/86400
        assert interval.contains(interval.start_lower_jd_ut1) is None
        assert interval.contains(interval.start_upper_jd_ut1) is True
        assert interval.contains(interval.end_lower_jd_ut1) is None
        assert interval.contains(interval.end_upper_jd_ut1) is False
        assert interval.start.local.tzinfo == _resolve_timezone(zone)


def test_brahma_can_start_on_previous_civil_date(monkeypatch):
    owner, reader, _, _ = install_analytic_solar(monkeypatch, sunrise_hour=1)
    r = owner.named_muhurta_for_date(date(2026, 10, 8), 60, 0, timezone="UTC", reader=reader)
    assert r.result.intervals[1].start.local.date() == date(2026, 10, 7)
    assert r.result.intervals[1].end.local.date() == date(2026, 10, 8)


@pytest.mark.parametrize("flag,reason", [
    ("omit_rises", "sunrise_absent"), ("multiple", "multiple_sunrises_on_requested_date"),
    ("fail_signal", "sunrise_root_bracket_unresolved"),
])
def test_missing_ambiguous_or_unresolved_sunrise_is_unavailable(monkeypatch, flag, reason):
    owner, reader, _, state = install_analytic_solar(monkeypatch)
    setattr(state, flag, True)
    r = owner.named_muhurta_for_date(date(2026, 10, 8), 20, 80, timezone="UTC", reader=reader)
    assert r.result.status == "unavailable"
    for interval in r.result.intervals:
        assert interval.unavailable_reasons == (reason,)
        assert interval.start is interval.end is interval.start_jd_ut1 is None


def test_missing_sets_still_allow_fixed_brahma(monkeypatch):
    owner, reader, _, state = install_analytic_solar(monkeypatch)
    state.omit_sets = True
    fixed = owner.named_muhurta_for_date(date(2026, 10, 8), 20, 80, timezone="UTC", reader=reader)
    legacy = owner.named_muhurta_for_date(date(2026, 10, 8), 20, 80, timezone="UTC", reader=reader,
        policy=NamedMuhurtaPolicy(brahma_basis="legacy_proportional_night_14"))
    assert fixed.result.status == "partial" and fixed.result.intervals[1].status == "available"
    assert legacy.result.status == "unavailable"


def test_sunrise_root_straddling_midnight_has_uncertain_date_ownership(monkeypatch):
    owner, reader, _, _ = install_analytic_solar(monkeypatch)
    original = owner._refine
    def refine(event, kind, lat, lon, zone, policy):
        anchor = original(event, kind, lat, lon, zone, policy)
        if kind == "sunrise":
            low, _ = _civil_bounds(date(2026, 10, 8), zone)
            return replace(anchor, lower_jd_ut1=low-.000001)
        return anchor
    monkeypatch.setattr(owner, "_refine", refine)
    r = owner.named_muhurta_for_date(date(2026, 10, 8), 20, 80, timezone="UTC", reader=reader)
    assert r.result.status == "unavailable"
    assert r.result.intervals[0].unavailable_reasons == ("sunrise_civil_date_ownership_uncertain",)


@pytest.mark.parametrize("changes", [
    {"local_date": datetime(2026, 10, 8)}, {"local_date": date(1, 1, 1)},
    {"local_date": "2026-10-08"}, {"latitude": True}, {"latitude": 90},
    {"longitude": float("inf")}, {"timezone": "Mars/Olympus"},
    {"local_date": date(2011, 12, 30), "timezone": "Pacific/Apia"},
])
def test_invalid_dates_and_locations_fail_before_reader_access(monkeypatch, changes):
    owner, _, calls, _ = install_analytic_solar(monkeypatch)
    monkeypatch.setattr(owner, "get_reader", lambda: pytest.fail("preflight touched reader"))
    with pytest.raises((TypeError, ValueError)):
        owner.named_muhurta_for_date(**({"local_date": date(2026, 10, 8),
            "latitude": 20, "longitude": 80, "timezone": "UTC"} | changes))
    assert calls == []


@pytest.mark.parametrize("error,expected", [
    (MissingKernelError("missing"), MuhurtaResourceError),
    (OutOfRangeError("range", [1.0]), MuhurtaCoverageError),
])
def test_resource_errors_restore_borrowed_reader(monkeypatch, error, expected):
    owner, reader, _, _ = install_analytic_solar(monkeypatch)
    def fail(*args):
        raise error
    monkeypatch.setattr(owner, "_bind_ephemeris_time", fail)
    outer = object()
    with use_reader_override(outer):
        with pytest.raises(expected):
            owner.named_muhurta_for_date(date(2026, 10, 8), 20, 80, timezone="UTC", reader=reader)
        assert get_active_reader() is outer
