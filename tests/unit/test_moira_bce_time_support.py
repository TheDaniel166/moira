from __future__ import annotations

from datetime import datetime, timezone

import pytest

from moira import Chart, Moira, calendar_datetime_from_jd, datetime_from_jd, julian_day
from moira.dasha import DashaPeriod
from moira.occultations import CloseApproach, LunarOccultation
from moira.phenomena import PhenomenonEvent
from moira.progressions import ProgressedChart
from moira.stations import StationEvent
from moira.timelords import FirdarPeriod, ReleasingPeriod
from moira.transits import IngressEvent, TransitEvent


def test_datetime_from_jd_still_rejects_bce_for_python_datetime() -> None:
    with pytest.raises(ValueError, match="calendar_datetime_from_jd"):
        datetime_from_jd(julian_day(-1321, 7, 20, 0.0))


def test_moira_calendar_from_jd_exposes_bce_safe_top_level_api() -> None:
    jd = julian_day(-1321, 7, 20, 0.0)

    engine = Moira()
    cal = engine.calendar_from_jd(jd)

    assert cal == calendar_datetime_from_jd(jd)
    assert cal.year == -1321


def test_bce_chart_and_progressed_chart_expose_calendar_properties() -> None:
    jd = julian_day(-1321, 7, 20, 0.0)

    chart = Chart(jd_ut=jd, planets={}, nodes={}, obliquity=23.4, delta_t=0.0)
    progressed = ProgressedChart(
        chart_type="Secondary Progression",
        natal_jd_ut=jd,
        progressed_jd_ut=jd,
        target_date=datetime(2000, 1, 1, tzinfo=timezone.utc),
        solar_arc_deg=0.0,
        positions={},
    )

    assert chart.calendar_utc.year == -1321
    assert progressed.calendar_utc.year == -1321


def test_bce_event_objects_render_without_crashing() -> None:
    jd = julian_day(-1321, 7, 20, 6.5)

    transit = TransitEvent("Venus", 120.0, jd, "direct")
    ingress = IngressEvent("Venus", "Leo", jd, "direct")
    station = StationEvent("Mercury", "retrograde", jd, 100.0)
    phenomenon = PhenomenonEvent("Moon", "Full Moon", jd, 180.0)
    close = CloseApproach("Moon", "Regulus", jd, 0.1, False)
    occultation = LunarOccultation("Regulus", jd, jd + 0.01, jd + 0.005, 0.01, True)

    assert transit.calendar_utc.year == -1321
    assert ingress.calendar_utc.year == -1321
    assert station.calendar_utc.year == -1321
    assert phenomenon.calendar_utc.year == -1321
    assert close.calendar_utc.year == -1321
    assert occultation.calendar_ingress.year == -1321
    assert occultation.calendar_egress.year == -1321

    assert "-1321-" in repr(transit)
    assert "-1321-" in repr(ingress)
    assert "-1321-" in repr(station)
    assert "-1321-" in repr(phenomenon)
    assert "-1321-" in repr(close)
    assert "-1321-" in repr(occultation)


def test_bce_time_lord_objects_render_without_crashing() -> None:
    jd = julian_day(-1321, 7, 20, 0.0)

    firdar = FirdarPeriod(level=1, planet="Sun", start_jd=jd, end_jd=jd + 365.25, years=1.0)
    releasing = ReleasingPeriod(
        level=1,
        sign="Leo",
        ruler="Sun",
        start_jd=jd,
        end_jd=jd + 365.25,
        years=1.0,
    )
    dasha = DashaPeriod(level=1, planet="Sun", start_jd=jd, end_jd=jd + 365.25)

    assert firdar.start_calendar.year == -1321
    assert releasing.start_calendar.year == -1321
    assert dasha.start_calendar.year == -1321

    assert "-1321-" in repr(firdar)
    assert "-1321-" in repr(releasing)
    assert "-1321-" in repr(dasha)
