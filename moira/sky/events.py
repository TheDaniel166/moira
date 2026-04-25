"""
moira.sky.events — Astronomical Events with Timing
====================================================
Strict astronomy API for discrete events that require an observer location
or a time-domain search: rise, set, transit, twilight, and planetary stations.

Note on scope
-------------
Discrete orbital phenomena that do not depend on observer location are in
``moira.sky.observation``: Moon phases, apsides, elongations, apsides,
and conjunctions.  The division here is:

  moira.sky.events      rise / set / transit / twilight / stations
  moira.sky.observation phase / magnitude / elongation / Moon phases /
                        planetary apsides / conjunctions / resonances

Rise, set, transit, and twilight  (moira.rise_set)
----------------------------------------------------
RiseSetPolicy
    Typed doctrine object controlling how rise and set events are defined.

    Standard attributes:
      horizon_deg        geometric horizon altitude (default 0°; negative = dip)
      refraction         True = apply atmospheric refraction
      disc_edge          True = use limb rather than center (Sun/Moon)
      geometric_center   True = use geometric center (ignores disc_edge)

    Use the fields explicitly; do not rely on unnamed keyword arguments.

TwilightTimes
    Result dataclass for all twilight events on a calendar day at an observer
    location.  Fields:
      civil_dusk, civil_dawn        Sun at −6°
      nautical_dusk, nautical_dawn  Sun at −12°
      astro_dusk, astro_dawn        Sun at −18°
      sunset, sunrise               limb at horizon
      solar_noon                    upper transit

find_phenomena(body, jd_day, lat, lon, policy)
    Rise, set, and transit dict for a body over a 24-hour UT window.
    Returns a dict with keys "rise", "set", "transit" mapped to JD_UT
    or None when the event does not occur that day.

get_transit(body, jd_day, lat, lon, upper=True)
    Precise JD_UT of the upper (or lower) meridian transit.

twilight_times(jd_day, lat, lon)
    Full TwilightTimes table for a day and observer location.

Stations — retrograde and direct  (moira.stations)
----------------------------------------------------
StationEvent
    Result vessel for a single station: body name, kind ("SR" = stationary
    retrograde, "SD" = stationary direct), epoch (JD_UT and CalendarDateTime),
    and ecliptic longitude at the station.

find_stations(body, jd_start, jd_end)
    All SR/SD station events for a body in a date range.

next_station(body, jd_start)
    First station (SR or SD) after a given JD_UT.

is_retrograde(body, jd_ut)
    Return True if the body is in retrograde motion at the given epoch.

retrograde_periods(body, jd_start, jd_end)
    List of (jd_SR, jd_SD) pairs — begin and end of each retrograde arc.
"""

from moira.rise_set import (
    RiseSetPolicy,
    TwilightTimes,
    find_phenomena,
    get_transit,
    twilight_times,
)
from moira.stations import (
    StationEvent,
    find_stations,
    is_retrograde,
    next_station,
    retrograde_periods,
)

__all__ = [
    # Rise / set / transit / twilight
    "RiseSetPolicy",
    "TwilightTimes",
    "find_phenomena",
    "get_transit",
    "twilight_times",
    # Stations
    "StationEvent",
    "find_stations",
    "next_station",
    "is_retrograde",
    "retrograde_periods",
]
