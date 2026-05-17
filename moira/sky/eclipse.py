"""
moira.sky.eclipse — Solar and Lunar Eclipses
=============================================
Strict astronomy API for solar and lunar eclipse prediction, contact
solving, geographic path computation, local circumstances, and Saros /
Metonic cycle identification.

Engine
------
All computation is backed by Moira's DE441 ephemeris.  The pipeline runs
light-time, aberration, deflection, and topocentric parallax internally —
no simplified shadow geometry is substituted.

Primary entry point
-------------------
EclipseCalculator
    The complete eclipse engine.  Instantiate once and call as needed.

    calculate(dt)                 geometry snapshot at a datetime
    calculate_jd(jd_ut)           geometry snapshot at a JD
    next_lunar_eclipse()          search forward from current epoch
    previous_lunar_eclipse()      search backward
    analyze_lunar_eclipse(event)  full LunarEclipseAnalysis bundle
    lunar_local_circumstances(event, lat, lon, elev)
    next_solar_eclipse(lat, lon)  search forward from current epoch
    previous_solar_eclipse(lat, lon)
    solar_local_circumstances(event, lat, lon, elev)
    solar_eclipse_path(event)     geographic path of totality / annularity
    next_solar_eclipse_at_location(lat, lon)  combined search + circumstances

Convenience function
--------------------
next_solar_eclipse_at_location(lat, lon, jd_ut)
    Standalone search equivalent to the EclipseCalculator method.

Solar eclipses
--------------
EclipseType
    Total / Annular / Hybrid / Partial / None.
    Field on EclipseData.eclipse_type.

SolarEclipsePath
    Central line geometry: begin, greatest, end, limit of totality /
    annularity, northern and southern limits.

SolarEclipseLocalCircumstances
    Observer-specific: contact times, altitude, azimuth, magnitude,
    duration of totality.  One instance per observer location.

SolarBodyCircumstances
    Sun and Moon geometric data at a given moment: distance, angular
    diameter, parallax.

LocalContactCircumstances
    A single contact event at an observer location: event time (JD_TT and
    datetime UTC), altitude, azimuth, position angle.

Lunar eclipses
--------------
LunarEclipseAnalysis
    Full analysis bundle: type, magnitude, umbral / penumbral contacts,
    duration of totality and partial phases.

LunarEclipseLocalCircumstances
    Observer-specific local lunar eclipse data.

LunarEclipseContacts  (from eclipse_contacts)
    Precise TT contact time set: P1 (1st penumbral), U1 (1st umbral),
    U2 (start of totality), greatest eclipse, U3 (end of totality),
    U4 (last umbral), P4 (last penumbral).

find_lunar_contacts(event, jd_guess)  (from eclipse_contacts)
    Solve for the full contact time set from an eclipse event and an
    approximate JD_UT seed.

Eclipse geometry snapshot
--------------------------
EclipseData
    Complete geometry snapshot at any epoch:
      eclipse_type, eclipse_magnitude, saros_index, metonic_year,
      metonic_is_reset, moon_parallax, solar_diameter, moon_diameter,
      galactic_center_longitude, separation, phase_angle, and more.

EclipseEvent
    Lightweight search result: JD_UT epoch, eclipse type, and a
    computed datetime_utc property.

Saros / Metonic cycle
---------------------
EclipseData.saros_index    position within the 223-synodic-month Saros
                           cycle, in units of synodic months (0–222.x)
EclipseData.metonic_year   position within the 19-year Metonic cycle
"""

from __future__ import annotations

from moira.eclipse import (
    EclipseCalculator,
    EclipseData,
    EclipseEvent,
    EclipseType,
    LocalContactCircumstances,
    LunarEclipseAnalysis,
    LunarEclipseLocalCircumstances,
    SolarBodyCircumstances,
    SolarEclipseLocalCircumstances,
    SolarEclipsePath,
    next_solar_eclipse_at_location,
)
from moira.eclipse_contacts import (
    LunarEclipseContacts,
    find_lunar_contacts,
)

__all__ = [
    # Primary engine
    "EclipseCalculator",
    # Classification
    "EclipseType",
    # Geometry snapshot
    "EclipseData",
    "EclipseEvent",
    # Solar eclipse
    "SolarEclipsePath",
    "SolarEclipseLocalCircumstances",
    "SolarBodyCircumstances",
    "LocalContactCircumstances",
    # Lunar eclipse
    "LunarEclipseAnalysis",
    "LunarEclipseLocalCircumstances",
    "LunarEclipseContacts",
    # Functions
    "next_solar_eclipse_at_location",
    "find_lunar_contacts",
]
