"""
Moira — planetary_hours.py
The Planetary Hour Engine: governs traditional planetary hour computation
for any geographic location and date.

Boundary: owns Chaldean hour sequence arithmetic, daytime/nighttime hour
division, and planetary hour lookup. Delegates solar position and
sunrise/sunset computation to _solar. Delegates Julian Day arithmetic to
julian. Does NOT own ephemeris state or geographic coordinate conversion.

Public surface:
    PlanetaryHour, PlanetaryHoursDay,
    planetary_hours

Import-time side effects: None

External dependency assumptions:
    - No third-party packages; stdlib only plus internal moira modules.
    - SpkReader must be initialised before planetary_hours() is called.
"""

import math
from dataclasses import dataclass
from datetime import datetime, timezone

from .constants import Body
from .julian import CalendarDateTime, calendar_datetime_from_jd, datetime_from_jd, format_jd_utc, jd_from_datetime
from .planets import planet_at
from .spk_reader import get_reader, SpkReader
from ._solar import _solar_declination_ra, _sunrise_sunset, _refine_sunrise


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

@dataclass(slots=True)
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
        exists to give every higher-level consumer a single, named, mutable record
        of each planetary hour.

    LAW OF OPERATION:
        Responsibilities:
            - Store a single planetary hour as named, typed fields
            - Expose UTC datetime and CalendarDateTime views via read-only properties
            - Serve as a value inside PlanetaryHoursDay.hours
        Non-responsibilities:
            - Computing hour boundaries (delegates to planetary_hours)
            - Computing sunrise/sunset (delegates to _sunrise_sunset / _refine_sunrise)
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
      "state": {"mutable": true, "owners": ["planetary_hours"]},
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
        return datetime_from_jd(self.jd_start)

    @property
    def start_calendar_utc(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(self.jd_start)

    @property
    def end_utc(self) -> datetime:
        return datetime_from_jd(self.jd_end)

    @property
    def end_calendar_utc(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(self.jd_end)

    def __repr__(self) -> str:
        label = "Day" if self.is_daytime else "Night"
        return (f"Hour {self.hour_number:2d} ({label}) — {self.ruler:<8}  "
                f"{format_jd_utc(self.jd_start)}–{self.end_calendar_utc.time_string()} UTC")


@dataclass(slots=True)
class PlanetaryHoursDay:
    """
    RITE: The Planetary Hours Day Vessel

    THEOREM: Governs the storage of all 24 planetary hours for a given calendar
    day and geographic location, with sunrise and sunset boundaries.

    RITE OF PURPOSE:
        PlanetaryHoursDay is the authoritative data vessel for a complete day of
        planetary hours produced by the Planetary Hour Engine. It captures the
        reference Julian Day, the observer's latitude and longitude, the sunrise
        and sunset Julian Days, and the full list of 24 PlanetaryHour instances.
        Without it, callers would receive unstructured collections with no
        field-level guarantees. It exists to give every higher-level consumer a
        single, named, mutable record of a complete planetary hours day.

    LAW OF OPERATION:
        Responsibilities:
            - Store a complete planetary hours day as named, typed fields
            - Expose sunrise and sunset as UTC datetime and CalendarDateTime views
            - Provide hour_at() and lord_of_hour() lookup methods
            - Serve as the return type of planetary_hours()
        Non-responsibilities:
            - Computing hour boundaries (delegates to planetary_hours)
            - Computing sunrise/sunset (delegates to _sunrise_sunset / _refine_sunrise)
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
      "state": {"mutable": true, "owners": ["planetary_hours"]},
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
    hours:      list[PlanetaryHour]

    @property
    def sunrise_utc(self) -> datetime:
        return datetime_from_jd(self.sunrise_jd)

    @property
    def sunrise_calendar_utc(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(self.sunrise_jd)

    @property
    def sunset_utc(self) -> datetime:
        return datetime_from_jd(self.sunset_jd)

    @property
    def sunset_calendar_utc(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(self.sunset_jd)

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

def planetary_hours(
    jd: float,
    latitude: float,
    longitude: float,
    reader: SpkReader | None = None,
) -> PlanetaryHoursDay:
    """
    Calculate all 24 planetary hours for the calendar day of *jd*.

    Parameters
    ----------
    jd        : Julian Day (UT) — any time during the target day
    latitude  : geographic latitude (degrees, N positive)
    longitude : geographic longitude (degrees, E positive)
    reader    : SpkReader instance

    Returns
    -------
    PlanetaryHoursDay with all 24 PlanetaryHour instances
    """
    if reader is None:
        reader = get_reader()

    # Get approximate noon for the day
    jd_noon = math.floor(jd - 0.5) + 0.5 + 0.5  # 12:00 UT for the day

    # Sunrise and sunset with iterative refinement
    jd_sr_approx, jd_ss_approx = _sunrise_sunset(jd_noon, latitude, longitude, reader)
    jd_sunrise = _refine_sunrise(jd_sr_approx, latitude, longitude, reader, is_rise=True)
    jd_sunset  = _refine_sunrise(jd_ss_approx, latitude, longitude, reader, is_rise=False)

    # Next sunrise (for night hours boundary)
    jd_next_noon = jd_noon + 1.0
    jd_nr_approx, _ = _sunrise_sunset(jd_next_noon, latitude, longitude, reader)
    jd_next_sunrise = _refine_sunrise(jd_nr_approx, latitude, longitude, reader, is_rise=True)

    # Day-of-week from sunrise JD (to determine day ruler)
    # Julian Day 0 = Monday (weekday 1 in ISO, 0 in our scheme = Sunday)
    # JD mod 7: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
    dow_jd = int(jd_sunrise + 1.5) % 7   # 0=Sun, 1=Mon, ... 6=Sat
    # Adjust: JD+1.5 makes 0=Mon; we want 0=Sun
    # Actually: JD=2451545.0 = Jan 1.5 2000 = Saturday
    # (2451545 + 1) % 7 = 2451546 % 7 = let's compute
    # 2451545 % 7 = 2451545 / 7 = 350220.71... → 350220*7=2451540 → rem=5
    # So JD 2451545 % 7 = 5 → Saturday → we need +2 to shift: (jd+2)%7 = 0=Mon
    # Let's use a known reference: Jan 1, 2000 was Saturday (dow=6 in 0=Sun)
    # JD 2451545.5 % 7 = ? 2451545 % 7 = 5 (so .5 day doesn't change int)
    # We want: 2451545 → Saturday=6; so offset = 6 - 5 = 1
    # dow_0indexed_sunday = (floor(jd_sunrise) + 1) % 7  gives us...
    # Actually let's just use a direct formula
    # Use: weekday = (floor(jd + 1.5)) % 7, where 0=Sun, 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri, 6=Sat
    jd_int   = int(jd_sunrise + 1.5)
    weekday  = jd_int % 7   # 0=Sun (since JD 0.5 = Jan 1, 4713 BC = Monday → shift)
    # Correction: JD=2451545 → Saturday; (2451545+1)%7=2451546%7
    # 2451546/7=350220.857..., 350220*7=2451540, rem=6 → that gives 6=Saturday ✓ if 0=Sun
    # But above formula: jd_int=2451546, 2451546%7=6 → 6=Sat with 0=Sun ✓
    # Wait: if 0=Sun then: Sun=0,Mon=1,...,Sat=6
    # JD 2451545 = Saturday. int(2451545 + 1.5) = 2451546. 2451546 % 7 = 6 → Sat=6 ✓

    day_ruler_idx = _DAY_RULER_IDX[weekday]

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
        jd_h_end   = jd_h_start + day_hour_len
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
        jd_h_end   = jd_h_start + night_hour_len
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
        hours=hours,
    )
