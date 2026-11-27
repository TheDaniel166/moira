"""Choghadiya weekday sequences and sunrise-owned solar schedules."""
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Literal

from .daily_panchanga import (
    PanchangaMoment, PanchangaSunriseDefinition, _SolarCycleMissing, _civil_bounds, _finite_number,
    _moment, _resolve_timezone, _solar_cycle_on, _solar_date, _validate_solar_location,
)
from .spk_reader import get_reader, use_reader_override

__all__ = [
    "ChoghadiyaInterval", "ChoghadiyaSchedule", "ChoghadiyaDay",
    "choghadiya_from_solar_times", "choghadiya_for_date",
]

_CYCLE = ("Udvega", "Amrita", "Roga", "Labha", "Shubha", "Chala", "Kala")



@dataclass(frozen=True, slots=True)
class ChoghadiyaInterval:
    """One numbered half-open eighth of the selected solar arc."""

    period: Literal["day", "night"]
    ordinal: int
    name: str
    start_jd_ut1: float
    end_jd_ut1: float


@dataclass(frozen=True, slots=True)
class ChoghadiyaSchedule:
    """Both sets of solar eighths for a single governing weekday."""

    weekday: int
    sunrise_jd_ut1: float
    sunset_jd_ut1: float
    next_sunrise_jd_ut1: float
    day: tuple[ChoghadiyaInterval, ...]
    night: tuple[ChoghadiyaInterval, ...]
    profile_id: Literal["sirohi_1916"] = field(init=False, default="sirohi_1916")
    source_reference: str = field(
        init=False, default="Samadhishatakam, Sirohi (1916), pp. 232–233 and Sampoorna Panchang Gyan",
    )


@dataclass(frozen=True, slots=True)
class ChoghadiyaDay:
    """Dated schedule or explicit missing solar evidence, with local bounds."""

    local_date: date
    timezone: str
    latitude: float
    longitude: float
    sunrise_definition: PanchangaSunriseDefinition
    reader_binding: Literal["caller_owned_reader", "active_or_default_reader"]
    status: Literal["available", "unavailable"]
    unavailable_reason: _SolarCycleMissing | None
    sunrise: PanchangaMoment | None
    sunset: PanchangaMoment | None
    next_sunrise: PanchangaMoment | None
    schedule: ChoghadiyaSchedule | None
    boundaries: tuple[PanchangaMoment, ...]
    profile_id: Literal["sirohi_1916"] = field(init=False, default="sirohi_1916")


def _eighths(period, start, end, first, stride):
    edges = (start,) + tuple(start + (end - start) * i / 8 for i in range(1, 8)) + (end,)
    if any(left >= right for left, right in zip(edges, edges[1:])):
        raise ValueError("solar anchors need sufficient UT1 resolution for eight intervals")
    return tuple(ChoghadiyaInterval(period, i + 1, _CYCLE[(first + i * stride) % 7], left, right)
                 for i, (left, right) in enumerate(zip(edges, edges[1:])))


def choghadiya_from_solar_times(*, weekday: int, sunrise_jd_ut1: float,
                              sunset_jd_ut1: float, next_sunrise_jd_ut1: float) -> ChoghadiyaSchedule:
    """Build both sequences using the sunrise weekday, Monday=0 through Sunday=6."""
    if type(weekday) is not int or not 0 <= weekday <= 6:
        raise ValueError("weekday must be an integer in [0, 6] (Monday=0)")
    for name, value in (("sunrise_jd_ut1", sunrise_jd_ut1), ("sunset_jd_ut1", sunset_jd_ut1),
                        ("next_sunrise_jd_ut1", next_sunrise_jd_ut1)):
        _finite_number(name, value)
    if not sunrise_jd_ut1 < sunset_jd_ut1 < next_sunrise_jd_ut1:
        raise ValueError("solar anchors must be ordered sunrise, sunset, next sunrise")
    first = (weekday + 1) % 7
    return ChoghadiyaSchedule(
        weekday, sunrise_jd_ut1, sunset_jd_ut1, next_sunrise_jd_ut1,
        _eighths("day", sunrise_jd_ut1, sunset_jd_ut1, first, 5),
        _eighths("night", sunset_jd_ut1, next_sunrise_jd_ut1, first + 4, 4),
    )


def choghadiya_for_date(local_date: date, latitude: float, longitude: float, *,
                       timezone: str,
                       sunrise_definition: PanchangaSunriseDefinition = PanchangaSunriseDefinition.RASHTRIYA_UPPER_LIMB,
                       reader=None) -> ChoghadiyaDay:
    """Resolve the governing cycle and display its UT1 boundaries in the chosen timezone."""
    if type(local_date) is not date or not 2 <= local_date.year <= 9998:
        raise ValueError("local_date must be a date in years [2, 9998]")
    _validate_solar_location(latitude, longitude)
    if not isinstance(sunrise_definition, PanchangaSunriseDefinition):
        raise TypeError("sunrise_definition must be PanchangaSunriseDefinition")
    zone = _resolve_timezone(timezone)
    next_date = local_date + timedelta(days=1)
    _civil_bounds(local_date, zone)
    _civil_bounds(next_date, zone)
    bound = get_reader() if reader is None else reader
    altitude = sunrise_definition.altitude_degrees
    with use_reader_override(bound):
        today = _solar_date(local_date, zone, latitude, longitude, altitude)
        tomorrow = _solar_date(next_date, zone, latitude, longitude, altitude)
    sunrise, sunset, next_sunrise, reason = _solar_cycle_on(today, tomorrow)
    schedule = None
    boundaries = ()
    if reason is None:
        schedule = choghadiya_from_solar_times(
            weekday=local_date.weekday(), sunrise_jd_ut1=sunrise.jd_ut1,
            sunset_jd_ut1=sunset.jd_ut1, next_sunrise_jd_ut1=next_sunrise.jd_ut1,
        )
        boundaries = ((sunrise,) + tuple(_moment(slot.start_jd_ut1, zone) for slot in schedule.day[1:])
                      + (sunset,) + tuple(_moment(slot.start_jd_ut1, zone) for slot in schedule.night[1:])
                      + (next_sunrise,))
    return ChoghadiyaDay(
        local_date, timezone, latitude, longitude, sunrise_definition,
        "active_or_default_reader" if reader is None else "caller_owned_reader",
        "available" if schedule is not None else "unavailable", reason,
        sunrise, sunset, next_sunrise, schedule, boundaries,
    )
