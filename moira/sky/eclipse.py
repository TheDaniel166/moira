"""
moira.sky.eclipse — Solar and Lunar Eclipses
=============================================
Strict astronomy API for solar and lunar eclipse prediction, contact
solving, geographic path computation, local circumstances, and Saros /
Metonic cycle identification.

Engine
------
All computation is backed by Moira's DE441 ephemeris.  Correction stages are
product-specific: the native global solar shadow uses Earth-reception
light-time centre states without stellar aberration, while observer-local
products apply their separately declared topocentric geometry.  No rendered
sky direction is silently substituted for the physical shadow axis.

Primary entry point
-------------------
EclipseCalculator
    The complete eclipse engine.  Instantiate once and call as needed.

    calculate(dt)                 geometry snapshot at a UTC datetime
    calculate_jd(jd)              geometry snapshot at a UT Julian Day
    solar_besselian_elements(jd_ut1)
                                  instantaneous fundamental-plane elements
    next_lunar_eclipse(jd_start, kind="any")
    previous_lunar_eclipse(jd_start, kind="any")
    analyze_lunar_eclipse(jd_start, *, kind="any", backward=False,
                           mode="native")
    lunar_local_circumstances(jd_start, latitude, longitude, *,
                              elevation_m=0.0, kind="any", backward=False,
                              mode="native")
    next_solar_eclipse(jd_start, kind="any")
    previous_solar_eclipse(jd_start, kind="any")
    solar_local_circumstances(jd_start, latitude, longitude, *,
                              elevation_m=0.0, kind="any", backward=False)
    solar_eclipse_path(jd_start, *, kind="any", backward=False,
                       sample_count=9)
    solar_eclipse_footprint(jd_start, *, kind="any", backward=False,
                            sample_count=181)
    next_solar_eclipse_at_location(jd_start, latitude, longitude, *,
                                   elevation_m=0.0, kind="any",
                                   max_lunations=360)

Convenience function
--------------------
next_solar_eclipse_at_location(jd_start, latitude, longitude, *,
                               elevation_m=0.0, kind="any",
                               max_lunations=360, reader=None)
    Standalone search equivalent to the EclipseCalculator method.

Solar eclipses
--------------
SolarBesselianElements
    Instantaneous native shadow-axis coordinates and cone dimensions on the
    geocentric Besselian fundamental plane.  This is an engine-only specialist
    surface; it does not search for an eclipse or alter facade / REST results.

EclipseType
    Total / Annular / Hybrid / Partial / None.
    Field on EclipseData.eclipse_type.

SolarEclipsePath
    Central shadow-axis geometry and width for totality / annularity.

SolarEclipseVisibilityFootprint
    Complete zero-elevation WGS-84 mean-limb visibility boundary: north/south
    penumbral limits, sunrise/sunset closures, and P1-P4 contact
    topology. Each admitted penumbral kind has component_id=0; contiguous
    segment_id values preserve any time folds. This is distinct from the
    central path and local circumstances.

SolarEclipseLocalCircumstances
    Observer-specific: contact times, altitude, azimuth, magnitude,
    duration of totality.  One instance per observer location.

SolarBodyCircumstances
    Sun and Moon geometric data at a given moment: distance, angular
    diameter, parallax.

LocalContactCircumstances
    A single contact event at an observer location: event time (JD_UT1 and
    datetime UTC), altitude, azimuth, position angle.

Lunar eclipses
--------------
LunarEclipseAnalysis
    Full analysis bundle: type, magnitude, umbral / penumbral contacts,
    duration of totality and partial phases.

LunarEclipseLocalCircumstances
    Observer-specific local lunar eclipse data.

LunarEclipseContacts  (from eclipse_contacts)
    Precise UT1 contact time set: P1 (1st penumbral), U1 (1st umbral),
    U2 (start of totality), U3 (end of totality), U4 (last umbral),
    P4 (last penumbral), plus the separate greatest-eclipse instant.

find_lunar_contacts(calculator, center_jd, *, window_days=0.2,
                    coarse_step_seconds=60.0)  (from eclipse_contacts)
    Solve for the full contact time set around a candidate JD_UT maximum.

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
    SolarBesselianElements,
    SolarEclipseFootprintBoundaryKind,
    SolarEclipsePenumbralContactKind,
    SolarEclipseFootprintTopology,
    SolarEclipseFootprintPoint,
    SolarEclipsePenumbralContact,
    SolarEclipseFootprintContacts,
    SolarEclipseLimitTrack,
    SolarEclipseVisibilityFootprint,
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
    "SolarBesselianElements",
    "SolarEclipseFootprintBoundaryKind",
    "SolarEclipsePenumbralContactKind",
    "SolarEclipseFootprintTopology",
    "SolarEclipseFootprintPoint",
    "SolarEclipsePenumbralContact",
    "SolarEclipseFootprintContacts",
    "SolarEclipseLimitTrack",
    "SolarEclipseVisibilityFootprint",
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
