"""
moira.sky.time — Time Systems and ΔT
======================================
Strict astronomy API for time representation, conversion between time
scales, Earth rotation quantities, and source-bounded ΔT policy.

Time scales
-----------
UT   — Universal Time (UT1), rotationally tied to Earth orientation.
       Note: Moira resolves UTC to UT1/TT via historical leap second tables.
TT   — Terrestrial Time, uniform atomic-second scale
TDB  — Barycentric Dynamical Time, relativistic correction to TT
ERA  — Earth Rotation Angle, precise UT1-based orientation
GMST — Greenwich Mean Sidereal Time
GAST — Greenwich Apparent Sidereal Time (equation of the equinoxes applied)
LAST — Local Apparent Sidereal Time

Julian Day and calendar
-----------------------
julian_day              JD from calendar date and hour
calendar_from_jd        calendar tuple from JD
calendar_datetime_from_jd  CalendarDateTime from JD
jd_from_datetime        JD from Python datetime
decimal_year            decimal year from calendar
decimal_year_from_jd    decimal year from JD
centuries_from_j2000    Julian centuries from J2000.0

ΔT — source-priority lookup
---------------------------
delta_t          canonical historical/annual lookup plus future scenario
delta_t_from_jd  EOP-derived when a UT1 JD is covered; year-model fallback
DeltaTPolicy     controls which ΔT model is used downstream

Source-bounded ΔT attribution  (delta_t_physical)
---------------------------------------------------
secular_trend    declared tidal + GIA curvature baseline
core_delta_t     reserved zero-valued compatibility field
cryo_delta_t     reserved zero-valued compatibility field
fluid_lowfreq    reserved zero-valued compatibility field
DeltaTBreakdown  additive source/forecast reconciliation vessel
DeltaTDistribution  conditional convenience distribution and uncertainty scale
delta_t_breakdown  compute DeltaTBreakdown for a given year
delta_t_distribution  compute DeltaTDistribution for a given year
"""

from __future__ import annotations

from moira.delta_t_physical import (
    DeltaTBreakdown,
    DeltaTDistribution,
    core_delta_t,
    cryo_delta_t,
    delta_t_breakdown,
    delta_t_distribution,
    fluid_lowfreq,
    secular_trend,
)
from moira.julian import (
    CalendarDateTime,
    DeltaTPolicy,
    apparent_sidereal_time,
    apparent_sidereal_time_at,
    calendar_datetime_from_jd,
    calendar_from_jd,
    centuries_from_j2000,
    decimal_year,
    decimal_year_from_jd,
    delta_t,
    delta_t_from_jd,
    earth_rotation_angle,
    greenwich_mean_sidereal_time,
    jd_from_datetime,
    julian_day,
    local_sidereal_time,
    tt_to_tdb,
    tt_to_ut,
    ut_to_tt,
    utc_to_tt,
    utc_to_ut1,
)

__all__ = [
    # Calendar and Julian Day
    "CalendarDateTime",
    "julian_day",
    "calendar_from_jd",
    "calendar_datetime_from_jd",
    "jd_from_datetime",
    "decimal_year",
    "decimal_year_from_jd",
    "centuries_from_j2000",
    # Time scale conversions
    "utc_to_tt",
    "utc_to_ut1",
    "ut_to_tt",
    "tt_to_ut",
    "tt_to_tdb",
    # Earth rotation and sidereal time
    "earth_rotation_angle",
    "greenwich_mean_sidereal_time",
    "apparent_sidereal_time",
    "apparent_sidereal_time_at",
    "local_sidereal_time",
    # ΔT — standard
    "DeltaTPolicy",
    "delta_t",
    "delta_t_from_jd",
    # ΔT — source-bounded accounting and scenario policy
    "DeltaTBreakdown",
    "DeltaTDistribution",
    "delta_t_breakdown",
    "delta_t_distribution",
    "secular_trend",
    "core_delta_t",
    "cryo_delta_t",
    "fluid_lowfreq",
]
