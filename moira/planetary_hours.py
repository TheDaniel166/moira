"""
Moira — planetary_hours.py
The Planetary Hour Engine: governs traditional planetary hour computation
for any geographic location and input instant, resolved onto the enclosing
sunrise-based local day.

Boundary: owns Chaldean hour sequence arithmetic, daytime/nighttime hour
division, and planetary hour lookup. Delegates the enclosing sunrise-based
window to _local_solar_day, solar event geometry to _solar through that shared
boundary, and Julian Day arithmetic to julian. Does NOT own ephemeris state or
geographic coordinate conversion.

Public surface:
    PlanetaryHour, PlanetaryHoursDay,
    planetary_hours

Import-time side effects: None

External dependency assumptions:
    - No third-party packages; stdlib only plus internal moira modules.
    - If ``reader`` is omitted, the module-level SPK reader must already be
      initialised; callers may also pass an explicit ``SpkReader``.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from ._local_solar_day import (
    LocalSolarDay,
    _local_solar_day_from_utc,
    _local_solar_day_from_ut1,
    _resolve_local_solar_day,
)
from .constants import Body
from .julian import (
    CalendarDateTime,
    _ut1_to_utc,
    calendar_datetime_from_jd,
    datetime_from_jd,
    format_jd_utc,
)
from .spk_reader import SpkReader


# ---------------------------------------------------------------------------
# Chaldean order (standard planetary hour sequence)
# ---------------------------------------------------------------------------

_CHALDEAN: list[str] = [
    Body.SATURN, Body.JUPITER, Body.MARS,
    Body.SUN, Body.VENUS, Body.MERCURY, Body.MOON,
]

# Day-of-week → index into _CHALDEAN for hour 1 of that day
# (Sunday=0 through Saturday=6)
_DAY_RULER_IDX: dict[int, int] = {
    0: 3,   # Sunday   → Sun  (index 3)
    1: 6,   # Monday   → Moon (index 6)
    2: 2,   # Tuesday  → Mars (index 2)
    3: 5,   # Wednesday → Mercury (index 5)
    4: 1,   # Thursday  → Jupiter (index 1)
    5: 4,   # Friday    → Venus (index 4)
    6: 0,   # Saturday  → Saturn (index 0)
}


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PlanetaryHour:
    """
    RITE: The Planetary Hour Vessel

    THEOREM: Governs the storage of a single planetary hour with its ruling planet,
    time boundaries, and daytime/nighttime flag.

    RITE OF PURPOSE:
        PlanetaryHour is the authoritative data vessel for a single planetary hour
        produced by the Planetary Hour Engine. It captures the hour number (1–24),
        the ruling planet in Chaldean order, the start and end Julian Days, and
        whether the hour falls in the daytime or nighttime division. Without it,
        callers would receive unstructured tuples with no field-level guarantees. It
        exists to give every higher-level consumer a single, named, immutable record
        of each planetary hour.

    LAW OF OPERATION:
        Responsibilities:
            - Store a single planetary hour as named, typed fields
            - Expose UTC datetime and CalendarDateTime views via read-only properties
            - Serve as a value inside PlanetaryHoursDay.hours
        Non-responsibilities:
            - Computing hour boundaries (delegates to planetary_hours)
            - Resolving the local solar day (delegates to _local_solar_day)
        Dependencies:
            - Populated by planetary_hours()
        Structural invariants:
            - hour_number is in [1, 24]
            - ruler is a valid Body.* constant from _CHALDEAN
            - jd_end > jd_start
        Behavioral invariants:
            - All consumers treat PlanetaryHour fields as read-only after construction

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.planetary_hours.PlanetaryHour",
      "risk": "high",
      "api": {
        "frozen": ["hour_number", "ruler", "jd_start", "jd_end", "is_daytime"],
        "internal": ["start_utc", "start_calendar_utc", "end_utc", "end_calendar_utc"]
      },
      "state": {"mutable": false, "owners": ["planetary_hours"]},
      "effects": {
        "signals_emitted": [],
        "io": []
      },
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    hour_number: int     # 1–24 (1–12 day, 13–24 night)
    ruler:       str     # Body.* constant
    jd_start:    float
    jd_end:      float
    is_daytime:  bool

    @property
    def start_utc(self) -> datetime:
        return datetime_from_jd(_ut1_to_utc(self.jd_start))

    @property
    def start_calendar_utc(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(_ut1_to_utc(self.jd_start))

    @property
    def end_utc(self) -> datetime:
        return datetime_from_jd(_ut1_to_utc(self.jd_end))

    @property
    def end_calendar_utc(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(_ut1_to_utc(self.jd_end))

    def __repr__(self) -> str:
        label = "Day" if self.is_daytime else "Night"
        return (f"Hour {self.hour_number:2d} ({label}) — {self.ruler:<8}  "
                f"{format_jd_utc(_ut1_to_utc(self.jd_start))}–{self.end_calendar_utc.time_string()} UTC")


@dataclass(frozen=True, slots=True)
class PlanetaryHoursDay:
    """
    RITE: The Planetary Hours Day Vessel

    THEOREM: Governs the storage of all 24 planetary hours for one
    sunrise-based local day window at a geographic location, with sunrise and
    sunset boundaries.

    RITE OF PURPOSE:
        PlanetaryHoursDay is the authoritative data vessel for a complete
        sunrise-to-sunrise planetary-hours window produced by the Planetary Hour
        Engine. It captures the reference Julian Day used to select the window,
        the observer's latitude and longitude, the sunrise and sunset Julian
        Days, and the full list of 24 PlanetaryHour instances. Without it,
        callers would receive unstructured collections with no field-level
        guarantees. It exists to give every higher-level consumer a single,
        named, immutable record of a complete planetary-hours day.

    LAW OF OPERATION:
        Responsibilities:
            - Store a complete sunrise-based planetary hours day as named, typed fields
            - Expose sunrise and sunset as UTC datetime and CalendarDateTime views
            - Provide hour_at() and lord_of_hour() lookup methods
            - Serve as the return type of planetary_hours()
        Non-responsibilities:
            - Computing hour boundaries (delegates to planetary_hours)
            - Resolving the local solar day (delegates to _local_solar_day)
        Dependencies:
            - Populated by planetary_hours()
            - sunrise_utc / sunset_utc delegate to datetime_from_jd()
        Structural invariants:
            - hours has exactly 24 PlanetaryHour instances
            - hours[0:12] are daytime, hours[12:24] are nighttime
        Behavioral invariants:
            - hour_at() returns None if jd falls outside all 24 hours
            - lord_of_hour() returns None if jd falls outside all 24 hours

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.planetary_hours.PlanetaryHoursDay",
      "risk": "high",
      "api": {
        "frozen": ["date_jd", "latitude", "longitude", "sunrise_jd", "sunset_jd", "hours"],
        "internal": ["sunrise_utc", "sunrise_calendar_utc", "sunset_utc", "sunset_calendar_utc", "hour_at", "lord_of_hour"]
      },
      "state": {"mutable": false, "owners": ["planetary_hours"]},
      "effects": {
        "signals_emitted": [],
        "io": []
      },
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    date_jd:    float
    latitude:   float
    longitude:  float
    sunrise_jd: float
    sunset_jd:  float
    hours:      tuple[PlanetaryHour, ...]

    @property
    def sunrise_utc(self) -> datetime:
        return datetime_from_jd(_ut1_to_utc(self.sunrise_jd))

    @property
    def sunrise_calendar_utc(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(_ut1_to_utc(self.sunrise_jd))

    @property
    def sunset_utc(self) -> datetime:
        return datetime_from_jd(_ut1_to_utc(self.sunset_jd))

    @property
    def sunset_calendar_utc(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(_ut1_to_utc(self.sunset_jd))

    def hour_at(self, jd: float) -> PlanetaryHour | None:
        """Return the planetary hour that contains the given JD."""
        for h in self.hours:
            if h.jd_start <= jd < h.jd_end:
                return h
        return None

    def lord_of_hour(self, jd: float) -> str | None:
        """Return the ruling planet for the planetary hour containing jd."""
        h = self.hour_at(jd)
        return h.ruler if h else None


# ---------------------------------------------------------------------------
# Public: calculate planetary hours for a day
# ---------------------------------------------------------------------------

def _planetary_hours_resolved(
    jd: float,
    latitude: float,
    longitude: float,
    reader: SpkReader,
    *,
    previous_noon_ut1: float,
    current_noon_ut1: float,
    next_noon_ut1: float,
) -> PlanetaryHoursDay:
    """
    Calculate all 24 planetary hours for the sunrise-based local day that
    contains *jd*.

    Parameters
    ----------
    jd        : Julian Day (UT) — the instant whose enclosing planetary-hours
                day should be resolved
    latitude  : geographic latitude (degrees, N positive)
    longitude : geographic longitude (degrees, E positive)
    reader    : SpkReader instance

    Returns
    -------
    PlanetaryHoursDay with the sunrise, sunset, and 24 planetary hours for the
    sunrise-to-sunrise local window containing *jd*.
    """
    solar_day = _resolve_local_solar_day(
        jd,
        latitude,
        longitude,
        reader,
        previous_noon_ut1=previous_noon_ut1,
        current_noon_ut1=current_noon_ut1,
        next_noon_ut1=next_noon_ut1,
        bounds_owner="planetary-hours",
    )
    return _planetary_hours_for_solar_day(solar_day)


def _planetary_hours_for_solar_day(solar_day: LocalSolarDay) -> PlanetaryHoursDay:
    """Apply Chaldean hour arithmetic to one resolved local solar day."""
    jd = solar_day.jd
    latitude = solar_day.latitude
    longitude = solar_day.longitude
    jd_sunrise = solar_day.sunrise_jd
    jd_sunset = solar_day.sunset_jd
    jd_next_sunrise = solar_day.next_sunrise_jd
    day_ruler_idx = _DAY_RULER_IDX[solar_day.weekday]

    # Day hours: 12 equal hours from sunrise to sunset
    day_duration = jd_sunset - jd_sunrise
    day_hour_len = day_duration / 12.0

    # Night hours: 12 equal hours from sunset to next sunrise
    night_duration = jd_next_sunrise - jd_sunset
    night_hour_len = night_duration / 12.0

    hours: list[PlanetaryHour] = []

    # Hours 1–12 (daytime)
    for i in range(12):
        ruler_idx = (day_ruler_idx + i) % 7
        jd_h_start = jd_sunrise + i * day_hour_len
        jd_h_end = jd_sunrise + (i + 1) * day_hour_len
        hours.append(PlanetaryHour(
            hour_number=i + 1,
            ruler=_CHALDEAN[ruler_idx],
            jd_start=jd_h_start,
            jd_end=jd_h_end,
            is_daytime=True,
        ))

    # Hours 13–24 (nighttime)
    night_start_idx = (day_ruler_idx + 12) % 7
    for i in range(12):
        ruler_idx  = (night_start_idx + i) % 7
        jd_h_start = jd_sunset + i * night_hour_len
        jd_h_end = jd_sunset + (i + 1) * night_hour_len
        hours.append(PlanetaryHour(
            hour_number=i + 13,
            ruler=_CHALDEAN[ruler_idx],
            jd_start=jd_h_start,
            jd_end=jd_h_end,
            is_daytime=False,
        ))

    return PlanetaryHoursDay(
        date_jd=jd,
        latitude=latitude,
        longitude=longitude,
        sunrise_jd=jd_sunrise,
        sunset_jd=jd_sunset,
        hours=tuple(hours),
    )


def _planetary_hours_from_utc(
    jd_utc: float,
    latitude: float,
    longitude: float,
    reader: SpkReader | None = None,
) -> PlanetaryHoursDay:
    """Resolve a facade UTC instant without losing its civil-day anchor."""
    solar_day = _local_solar_day_from_utc(
        jd_utc,
        latitude,
        longitude,
        reader,
        bounds_owner="planetary-hours",
    )
    return _planetary_hours_for_solar_day(solar_day)


def planetary_hours(
    jd: float,
    latitude: float,
    longitude: float,
    reader: SpkReader | None = None,
) -> PlanetaryHoursDay:
    """
    Calculate all 24 planetary hours for the sunrise-based local day that
    contains *jd*.

    ``jd`` is a UT1 Julian Day. Datetime-facing facade callers use the private
    UTC adapter above so their civil UTC day is selected before the instant and
    the three required solar-noon anchors are converted to UT1.

    Parameters
    ----------
    jd : float
        Julian Day in Universal Time (UT1).
    latitude, longitude : float
        Geographic coordinates in degrees, north/east positive.
    reader : SpkReader or None
        Explicit kernel reader, or the active reader when omitted.
    """
    solar_day = _local_solar_day_from_ut1(
        jd,
        latitude,
        longitude,
        reader,
        bounds_owner="planetary-hours",
    )
    return _planetary_hours_for_solar_day(solar_day)
