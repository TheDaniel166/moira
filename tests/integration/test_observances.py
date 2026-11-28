"""Replay independently worked Dharmasindhu dates with the DE441 reader."""

from datetime import date, datetime

import pytest

from moira import ObservanceFastingContext, observance_catalogue
from moira.daily_panchanga import _resolve_timezone, _solar_date
from moira.julian import jd_from_datetime, utc_to_ut1
from moira.observances import _Bracket, _night
from moira.spk_reader import use_reader_override

pytestmark = [pytest.mark.integration, pytest.mark.requires_ephemeris]
RULE_ID = observance_catalogue()[0].rule_id
IST = "UTC+05:30"


def evaluate(engine, day, latitude, longitude, zone):
    return engine.evaluate_observance(RULE_ID, date.fromisoformat(day), latitude, longitude, timezone=zone)


@pytest.mark.parametrize(("day", "lat", "lon", "zone", "other", "coverages", "reason"), [
    ("2026-02-15", 13.4167, 75.2500, IST, "2026-02-16", ("full", "none"), "only_covered_night"),
    ("2027-03-06", 22.5726, 88.3639, IST, "2027-03-07", ("full", "none"), "only_covered_night"),
    ("2018-02-13", 10.4503, 77.5161, IST, "2018-02-14", ("full", "partial"), "full_over_partial"),
    ("2018-02-14", 22.5726, 88.3639, IST, "2018-02-13", ("full", "full"), "later_equal_coverage"),
    ("2025-02-26", 40.752, -73.816, "America/New_York", "2025-02-25", ("none", "none"), "later_no_coverage"),
    ("2025-02-26", 31.778, 35.235, "UTC+02:00", None, None, "only_covered_night"),
    ("2018-02-13", 22.075, -159.5, "UTC-10:00", None, None, "only_covered_night"),
])
def test_source_dates_and_geometry(moira_engine, day, lat, lon, zone, other, coverages, reason):
    result = evaluate(moira_engine, day, lat, lon, zone)
    decision = result.date_result
    assert result.provenance.reader_binding == "caller_owned_reader"
    assert decision.status == "selected", decision
    assert decision.selected_date.isoformat() == day
    assert decision.reason == reason
    assert decision.month.label.name == "Magha"
    assert (decision.month.paksha, decision.month.tithi_number) == ("Krishna", 14)
    nights = decision.nights
    assert len(nights) == 2
    if other:
        assert tuple(n.local_date.isoformat() for n in nights) == tuple(sorted((day, other)))
        assert tuple(n.coverage for n in nights) == tuple((value,) for value in coverages)
    assert result.parana.status in ("unavailable", "unsupported_rule")
    assert result.parana.interval is None

    winner = next(night for night in nights if night.local_date == decision.selected_date)
    assert result.vow.status == "selected"
    assert result.vow.local_date == decision.selected_date
    assert result.vow.timing == "selected_morning_after_daily_rites"
    assert result.vow.sunrise == winner.sunrise
    for boundary in (decision.tithi.start, decision.tithi.end, winner.sunrise, winner.sunset,
                     winner.next_sunrise, winner.nisitha.start, winner.nisitha.end):
        assert boundary.lower_jd_ut1 <= boundary.moment.jd_ut1 <= boundary.upper_jd_ut1
        assert (boundary.upper_jd_ut1 - boundary.lower_jd_ut1) * 86400 <= 0.1001
    start = winner.sunset.moment.jd_ut1
    length = winner.next_sunrise.moment.jd_ut1 - start
    assert abs(winner.nisitha.start.moment.jd_ut1 - (start + 7 * length / 15)) * 86400 < 0.001
    assert abs(winner.nisitha.end.moment.jd_ut1 - (start + 8 * length / 15)) * 86400 < 0.001
    if day == "2026-02-15":
        witnesses = (
            (decision.tithi.start, "2026-02-15T17:05:21+05:30"),
            (decision.tithi.end, "2026-02-16T17:34:34+05:30"),
            (winner.nisitha.start, "2026-02-16T00:18:22+05:30"),
            (winner.nisitha.end, "2026-02-16T01:07:33+05:30"),
        )
        for boundary, expected in witnesses:
            assert abs((boundary.moment.local - datetime.fromisoformat(expected)).total_seconds()) <= 2
        assert winner.nisitha.start.moment.local.date() > winner.local_date
        assert result.vow.sunrise_tithi == "before_caturdashi"
        assert winner.sunrise.upper_jd_ut1 < decision.tithi.start.lower_jd_ut1
    if day == "2018-02-13" and zone == IST:
        assert result.vow.sunrise_tithi == "before_caturdashi"
        assert winner.sunset.upper_jd_ut1 < decision.tithi.start.lower_jd_ut1
    if day == "2018-02-14":
        assert winner.nisitha.end.upper_jd_ut1 < decision.tithi.end.lower_jd_ut1
        assert decision.tithi.end.upper_jd_ut1 < winner.next_sunrise.lower_jd_ut1
        assert result.parana.status == "unsupported_rule"
    if zone == "UTC+02:00":
        assert winner.sunrise.upper_jd_ut1 < decision.tithi.start.lower_jd_ut1
        assert decision.tithi.end.upper_jd_ut1 < winner.next_sunrise.lower_jd_ut1
    if zone == "UTC-10:00":
        assert result.vow.sunrise_tithi == "caturdashi"
        assert decision.tithi.start.upper_jd_ut1 < winner.sunrise.lower_jd_ut1
        assert winner.next_sunrise.upper_jd_ut1 < decision.tithi.end.lower_jd_ut1


def test_neighbor_has_same_evidence_but_is_not_the_selected_date(moira_engine):
    result = evaluate(moira_engine, "2018-02-14", 10.4503, 77.5161, IST)
    assert result.date_result.status == "not_applicable"
    assert result.date_result.selected_date == date(2018, 2, 13)
    assert result.date_result.reason == "full_over_partial"
    assert result.parana.status == "not_applicable"
    assert result.vow.status == "not_applicable" and result.vow.timing is None


def test_recorded_1983_observance_retains_unresolved_omitted_and_paired_month(moira_engine):
    evaluation = evaluate(moira_engine, "1983-02-11", 14.165, 77.811, IST)
    result = evaluation.date_result
    assert (result.status, result.reason) == ("unsupported_rule", "intercalation_rule_unverified")
    assert (result.month.label.name, result.month.label.qualifier) == ("Pausha", "ksaya_context")
    assert result.month.amanta_lunation.omitted_months == ("Magha",)
    assert result.regional_context.paired_month_name == "Magha"
    assert result.selected_date is None and result.tithi and result.nights
    assert evaluation.vow.status == "unsupported_rule"
    paired = result.paired_magha
    day = next(night for night in result.nights if night.local_date == date(1983, 2, 11))
    assert day.coverage == ("full",)
    for boundary, expected in (
        (paired.elapsed_time_midpoint, "1983-02-11T14:23:13+05:30"),
        (paired.elongation_342_crossing, "1983-02-11T14:24:49+05:30"),
    ):
        assert abs((boundary.moment.local - datetime.fromisoformat(expected)).total_seconds()) <= 2
        assert boundary.upper_jd_ut1 < day.nisitha.start.lower_jd_ut1
        assert day.nisitha.end.upper_jd_ut1 < result.tithi.end.lower_jd_ut1


def test_post_kshaya_adhika_phalguna_carries_regional_context_without_a_pair(moira_engine):
    decision = evaluate(moira_engine, "1983-03-13", 14.165, 77.811, IST).date_result
    assert (decision.status, decision.reason) == ("unsupported_rule", "intercalation_rule_unverified")
    assert (decision.month.label.name, decision.month.label.qualifier) == ("Phalguna", "adhika")
    assert decision.regional_context.regional_lunations
    assert decision.regional_context.paired_month_name is None
    assert decision.paired_magha is None


@pytest.mark.parametrize(("ready_at", "darsha", "mode", "reason"), [
    ("2026-02-16T08:00:00+05:30", False, "within_tithi", "preparations_allow_in_tithi_parana"),
    ("2026-02-16T18:00:00+05:30", False, "at_tithi_end", "insufficient_time_after_daily_rites"),
    (None, True, "at_tithi_end", "darsha_shraddha_applies"),
])
def test_parana_conditional_branches_with_sringeri_ending(moira_engine, ready_at, darsha, mode, reason):
    ready = utc_to_ut1(jd_from_datetime(datetime.fromisoformat(ready_at))) if ready_at else None
    result = moira_engine.evaluate_observance(
        RULE_ID, date(2026, 2, 15), 13.4167, 75.2500, timezone=IST,
        fasting_context=ObservanceFastingContext(darsha, ready),
    )
    assert result.date_result.status == "selected"
    parana = result.parana
    assert (parana.status, parana.mode, parana.reason) == ("selected", mode, reason)
    end = result.date_result.tithi.end
    assert parana.tithi_end == end
    assert parana.following_sunrise.upper_jd_ut1 < end.lower_jd_ut1
    if mode == "within_tithi":
        assert parana.interval.start.lower_jd_ut1 == ready
        assert parana.interval.end == end
    else:
        assert parana.interval is None


def test_after_tithi_night_does_not_report_a_parana_before_observance(moira_engine):
    result = moira_engine.evaluate_observance(
        RULE_ID, date(2025, 2, 26), 40.752, -73.816, timezone="America/New_York",
        fasting_context=ObservanceFastingContext(True),
    )
    assert result.date_result.status == "selected"
    assert result.parana.status == "unsupported_rule"
    assert result.parana.reason == "tithi_does_not_span_following_sunrise"
    assert result.parana.mode is None and result.parana.interval is None


def test_absent_solar_context_is_unavailable_for_ordinary_magha(moira_engine):
    result = evaluate(moira_engine, "2026-02-15", -90.0, 0.0, "UTC").date_result
    assert (result.status, result.reason) == ("unavailable", "solar_context_unavailable")
    assert result.selected_date is None
    assert any(n.solar_issue == "sunrise_absent" for n in result.nights)


def test_spring_dst_change_preserves_night_length_in_ut1(moira_engine):
    day = date(2025, 3, 8)
    zone = _resolve_timezone("America/New_York")
    latitude, longitude = 40.752, -73.816
    altitude = observance_catalogue()[0].sunrise_definition.altitude_degrees

    def solar_on(day):
        return _solar_date(day, zone, latitude, longitude, altitude)

    with use_reader_override(moira_engine._reader):
        night = _night(day, zone, solar_on, latitude, longitude,
                       _Bracket(2460743, 2460743), _Bracket(2460744, 2460744))
    sunset, next_rise = night.sunset.moment, night.next_sunrise.moment
    assert sunset.local.utcoffset() != next_rise.local.utcoffset()
    civil_seconds = (next_rise.local - sunset.local).total_seconds()
    night_seconds = (next_rise.jd_ut1 - sunset.jd_ut1) * 86400
    assert civil_seconds - night_seconds == pytest.approx(3600, abs=0.01)
    width_seconds = (night.nisitha.end.moment.jd_ut1 - night.nisitha.start.moment.jd_ut1) * 86400
    assert width_seconds == pytest.approx(night_seconds / 15, abs=0.001)
