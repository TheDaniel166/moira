"""Bounded PAC 1948 SE comparisons and independent real-event witnesses.

Retrieved 2026-10-06 from the institution's English archive:
https://packolkata.imd.gov.in/download/EnglishRP2627.zip
PDF RP 1948 SE Final.pdf SHA256:
a8816abe4fae7fc0f0e4349a3d91eef00cfc0044a5f050b1b3bfe826847f9eaa
Printed xii-xiii: month identities; printed 15,23,30 (PDF 35,43,50):
conjunction endings; printed 158 (PDF 178): all 13 solar ingresses.
Conjunction and solar-ingress timing comparisons retain the original
60-second bound; labels are exact. This is not an admission
of exceptional Purnimanta remapping or a complete historical calendar.
"""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path

import pytest

from moira.julian import jd_from_datetime, utc_to_ut1
from moira.lunar_month import lunar_month_at, LunarMonthPolicy, LunarMonthSystem
from moira.planets import planet_at
from moira.sidereal import tropical_to_sidereal
from moira.panchanga import sankranti_at
from moira.spk_reader import use_reader_override

pytestmark = [pytest.mark.integration, pytest.mark.requires_ephemeris]
IST = timezone(timedelta(hours=5, minutes=30))
PAC_INGRESSES = json.loads((Path(__file__).resolve().parents[1] /
    "fixtures/pac_1948_solar_ingresses.json").read_text(encoding="utf-8"))


def instant(text):
    return utc_to_ut1(jd_from_datetime(datetime.fromisoformat(text).replace(tzinfo=IST)))


@pytest.mark.parametrize("day,name,qualifier,paksha", [
    ("2026-04-19", "Vaisakha", "ordinary", "Shukla"),
    ("2026-05-17", "Jyaishtha", "adhika", "Shukla"),
    ("2026-06-02", "Jyaishtha", "adhika", "Krishna"),
    ("2026-06-15", "Jyaishtha", "ordinary", "Shukla"),
    ("2026-07-16", "Ashadha", "ordinary", "Shukla"),
    ("2026-08-31", "Sravana", "ordinary", "Krishna"),
    ("2026-09-22", "Bhadrapada", "ordinary", "Shukla"),
    ("2026-09-28", "Bhadrapada", "ordinary", "Krishna"),
    ("2026-10-12", "Asvina", "ordinary", "Shukla"),
])
def test_published_amanta_identities_at_noon(moira_engine, day, name, qualifier, paksha):
    result = moira_engine.lunar_month_at(instant(day + "T12:00:00"))
    assert result.status == "available"
    assert (result.label.name, result.label.qualifier, result.paksha) == (name, qualifier, paksha)


@pytest.mark.parametrize("day,name", [
    ("2026-08-31", "Bhadrapada"), ("2026-09-22", "Bhadrapada"),
    ("2026-09-28", "Asvina"), ("2026-10-12", "Asvina"),
])
def test_published_ordinary_gauna_labels(moira_engine, day, name):
    r = moira_engine.lunar_month_at(instant(day + "T12:00:00"),
        policy=LunarMonthPolicy(system=LunarMonthSystem.PURNIMANTA))
    assert r.status == "available" and r.label.name == name
    assert r.month_start.kind == "full_moon" and r.month_end.kind == "full_moon"


@pytest.fixture(scope="module")
def adhika(moira_engine):
    return moira_engine.lunar_month_at(instant("2026-05-20T12:00:00"))


@pytest.mark.parametrize("boundary,expected", [
    ("start", "2026-05-17T01:31:00"), ("end", "2026-06-15T08:24:00"),
])
def test_published_intercalary_conjunction_times(adhika, boundary, expected):
    event = getattr(adhika.amanta_lunation, boundary)
    assert abs(event.jd_ut1 - instant(expected))*86400 <= 60


def test_published_following_conjunction(adhika):
    following = adhika.next_lunation
    assert abs(following.end.jd_ut1 - instant("2026-07-14T15:14:00"))*86400 <= 60


def test_published_mithuna_ingress_in_adjacent_lunation(adhika):
    # The original 60-second gate failed by 64.4768 seconds before the shared
    # general-precession scalar was corrected from FW psib to IAU 2006 p_A.
    # This is restored authority validation, not a frozen residual or a fit.
    event, = adhika.next_lunation.ingresses
    assert event.target_degrees == 60
    residual = (event.jd_ut1 - instant("2026-06-15T12:53:00"))*86400
    assert abs(residual) <= 60


@pytest.mark.parametrize("case", PAC_INGRESSES["cases"],
    ids=[f'{case["ist"][:10]}-{case["name"]}' for case in PAC_INGRESSES["cases"]])
def test_all_published_solar_ingresses(moira_engine, case):
    jd = instant(case["ist"])
    result = moira_engine.lunar_month_at(jd)
    events = [event for context in (result.previous_lunation,
        result.amanta_lunation, result.next_lunation) for event in context.ingresses
        if event.target_degrees == case["target_degrees"] and abs(event.jd_ut1-jd) < 0.5]
    event, = events
    assert abs(event.jd_ut1-jd)*86400 <= PAC_INGRESSES["source"]["acceptance_seconds"]
    # Independently assembled existing public Sankranti path must inherit the
    # same corrected scalar. Its angular solver and the lunar time bracket
    # together allow 0.2 seconds here; this is an internal consistency check.
    with use_reader_override(moira_engine._reader):
        sankranti, = sankranti_at(jd-0.5, jd+0.5)
    assert sankranti.rashi_index == int(case["target_degrees"]//30)
    assert abs(sankranti.jd-jd)*86400 <= PAC_INGRESSES["source"]["acceptance_seconds"]
    assert abs(sankranti.jd-event.jd_ut1)*86400 <= 0.2


def test_real_phase_and_solar_roots_have_entered_side_witnesses(adhika, moira_engine):
    for context in (adhika.previous_lunation, adhika.amanta_lunation, adhika.next_lunation):
        for event in (context.start, context.end, *context.ingresses):
            assert (event.jd_ut1 - event.lower_jd_ut1)*86400 <= 0.1
            values = []
            for offset in (-1, 1):
                jd = event.jd_ut1 + offset/86400
                sun = planet_at("Sun", jd, reader=moira_engine._reader).longitude
                if event.kind == "new_moon":
                    moon = planet_at("Moon", jd, reader=moira_engine._reader).longitude
                    values.append((moon-sun) % 360)
                else:
                    values.append(tropical_to_sidereal(sun, jd, "Lahiri"))
            if event.kind == "new_moon":
                assert values[0] > 359.99 and values[1] < 0.01
            else:
                assert int(values[0]//30) == (int(event.target_degrees/30)-1) % 12
                assert int(values[1]//30) == int(event.target_degrees/30)


@pytest.mark.parametrize("day", ["2026-05-03", "2026-05-20", "2026-06-20"])
def test_real_purnimanta_intercalary_neighbourhood_is_not_fabricated(moira_engine, day):
    r = moira_engine.lunar_month_at(instant(day + "T12:00:00"),
        policy=LunarMonthPolicy(system=LunarMonthSystem.PURNIMANTA))
    assert r.status == "unsupported_intercalation"
    assert r.label is None and r.month_start is None and r.month_end is None
    assert any(x.label.qualifier == "adhika" for x in (
        r.previous_lunation, r.amanta_lunation, r.next_lunation))


def test_real_two_ingress_lunation_retains_evidence(moira_engine):
    # Historical numerical invariant, not external authority for regional naming.
    r = moira_engine.lunar_month_at(instant("1983-01-20T12:00:00"))
    assert r.label.qualifier == "ksaya_context"
    assert len(r.amanta_lunation.ingresses) == 2
    assert len(r.amanta_lunation.omitted_months) == 1
    p = moira_engine.lunar_month_at(r.jd_ut1,
        policy=LunarMonthPolicy(system=LunarMonthSystem.PURNIMANTA))
    assert p.status == "unsupported_intercalation"


def test_selected_ayanamsa_is_preserved_and_does_not_move_conjunctions(moira_engine):
    jd = instant("2026-09-22T12:00:00")
    a = lunar_month_at(jd, reader=moira_engine._reader)
    b = lunar_month_at(jd, reader=moira_engine._reader,
        policy=LunarMonthPolicy(ayanamsa_system="Raman"))
    assert b.policy.ayanamsa_system == "Raman"
    assert a.amanta_lunation.start == b.amanta_lunation.start
    assert a.amanta_lunation.end == b.amanta_lunation.end
    assert a.amanta_lunation.ingresses != b.amanta_lunation.ingresses
