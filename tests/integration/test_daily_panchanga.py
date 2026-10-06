"""Real DE441 daily invariants and a bounded institutional timing comparison.

Authority: IMD/PAC Rashtriya Panchang 1948 SE (2026-27), 31 Bhadra,
22 September 2026. Retrieved 2026-10-06:
https://packolkata.imd.gov.in/panchang/en
https://packolkata.imd.gov.in/panchang/bn/bhadra (dated duplicate row)
Definitions/central station:
https://packolkata.imd.gov.in/panchang/en/explanation
23deg11min N, 82deg30min E; IST; geocentric nirayana angular limbs;
upper-limb sunrise/sunset with 47 arcminutes center depression.

Seven minute-resolution timings, 60-second acceptance for rounding and the
bounded difference between Moira's apparent/true sidereal and PAC reductions.
This is a single-date institutional comparison, not broad Panchanga parity.
"""
from datetime import date, datetime, timedelta, timezone
import importlib

import pytest

from moira.daily_panchanga import daily_panchanga, DailyPanchangaPolicy, PanchangaSunriseDefinition
from moira.panchanga import panchanga_at
from moira.planets import planet_at

pytestmark = [pytest.mark.integration, pytest.mark.requires_ephemeris]
IST = timezone(timedelta(hours=5, minutes=30))


@pytest.fixture(scope="module")
def published_day(moira_engine):
    return daily_panchanga(date(2026, 9, 22), 23 + 11 / 60, 82.5,
                          timezone="UTC+05:30", reader=moira_engine._reader)


@pytest.mark.parametrize("kind,number,hour,minute", [
    ("sunrise", 0, 5, 49), ("sunset", 0, 17, 56),
    ("tithi", 0, 21, 44), ("nakshatra", 0, 7, 7), ("yoga", 0, 16, 29),
    ("karana", 0, 8, 57), ("karana", 1, 21, 44),
])
def test_pac_published_ending_and_solar_times(published_day, kind, number, hour, minute):
    if kind == "sunrise":
        actual = published_day.sunrise.local
    elif kind == "sunset":
        actual = published_day.solar_date.sunsets[0].local
    else:
        limb = next(item for item in published_day.limbs if item.limb == kind)
        actual = limb.intervals[number].ending.local
    expected = datetime(2026, 9, 22, hour, minute, tzinfo=IST)
    assert abs((actual - expected).total_seconds()) <= 60.0


def test_real_day_boundary_witnesses_and_transportable_provenance(published_day, moira_engine):
    daily = importlib.import_module("moira.daily_panchanga")
    r = published_day
    assert r.status == "available" and r.unavailable_reasons == ()
    assert r.at_sunrise.vara_lord == "Mars"
    assert r.at_sunrise.tithi.number == 11
    assert r.at_sunrise.nakshatra.nakshatra_index == 20
    assert r.at_sunrise.yoga.number == 6
    assert r.at_sunrise.karana.name == "Vanija"
    assert r.provenance.reader_binding == "caller_owned_reader"
    for limb in r.limbs:
        assert limb.intervals[0].coverage_start == r.sunrise
        assert limb.intervals[-1].coverage_end == r.next_sunrise
        for part in limb.intervals:
            for offset, expected in ((-1.0, part.index), (1.0, (part.index + 1) % {
                "tithi": 30, "nakshatra": 27, "yoga": 27, "karana": 60}[limb.limb])):
                jd = part.ending.jd_ut1 + offset / 86400
                sun, moon = (planet_at(body, jd, reader=moira_engine._reader).longitude for body in ("Sun", "Moon"))
                snapshot = panchanga_at(sun, moon, jd)
                assert daily._limb_identity(snapshot, limb.limb)[0] == expected


@pytest.mark.parametrize("day,lat,lon,zone", [
    (date(2026, 3, 8), 40.73, -73.92, "America/New_York"),
    (date(2026, 11, 1), 40.73, -73.92, "America/New_York"),
    (date(2026, 9, 22), -36.85, 174.76, "Pacific/Auckland"),
])
def test_real_local_dates_have_complete_contiguous_limb_coverage(moira_engine, day, lat, lon, zone):
    r = moira_engine.daily_panchanga(day, lat, lon, timezone=zone)
    assert r.status == "available"
    assert r.sunrise.local.date() == day
    assert r.next_sunrise.local.date() == day + timedelta(days=1)
    assert r.at_sunrise.vara.index == (day.weekday() + 1) % 7
    for limb in r.limbs:
        assert limb.intervals[0].coverage_start == r.sunrise
        assert limb.intervals[-1].coverage_end == r.next_sunrise
        for a, b in zip(limb.intervals, limb.intervals[1:]):
            assert a.coverage_end == b.coverage_start
            assert b.index == (a.index + 1) % {"tithi": 30, "nakshatra": 27, "yoga": 27, "karana": 60}[limb.limb]


@pytest.mark.parametrize("day", [date(2026, 6, 21), date(2026, 12, 21)])
def test_polar_day_and_night_do_not_fabricate_sunrise(moira_engine, day):
    r = moira_engine.daily_panchanga(day, 89, 0, timezone="UTC")
    assert r.status == "unavailable"
    assert r.at_sunrise is None and r.limbs == ()
    assert "sunrise_absent" in r.unavailable_reasons


def test_geometric_center_is_explicit_and_later_than_upper_limb(published_day, moira_engine):
    center = moira_engine.daily_panchanga(date(2026, 9, 22), 23 + 11 / 60, 82.5,
        timezone="UTC+05:30", policy=DailyPanchangaPolicy(
            sunrise_definition=PanchangaSunriseDefinition.GEOMETRIC_CENTER))
    assert center.sunrise.jd_ut1 > published_day.sunrise.jd_ut1
    assert center.provenance.sunrise_altitude_degrees == 0.0


def test_whole_day_nakshatra_preserves_next_day_ending(moira_engine):
    r = moira_engine.daily_panchanga(date(2026, 9, 21), 23 + 11 / 60, 82.5, timezone="UTC+05:30")
    nakshatra = r.limbs[1]
    assert nakshatra.repeated_at_next_sunrise
    assert len(nakshatra.intervals) == 1
    assert nakshatra.intervals[0].name == "Uttara Ashadha"
    assert nakshatra.intervals[0].ending.local.date() == date(2026, 9, 22)
