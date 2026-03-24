"""
Moira — orbits.py
Orbital Elements Public Layer

Archetype: Design vessel module (Phase 3 — Defer.Design)

Purpose
-------
Provides the typed vessel surfaces for Keplerian orbital elements and
distance extremes (perihelion/aphelion).  This module is a design vessel —
the types are defined and exported, but no computation is present yet.

Phase 3 mandate
---------------
The orbital-elements domain is deferred because:

1. It requires a dedicated typed subsystem design.  Swiss ``swe_get_orbital_elements``
   returns a raw 50-element float array indexed by undocumented integer offsets.
   Moira must first decide the correct vessel shape, the coordinate frame
   (osculating vs mean elements, heliocentric vs barycentric), and the epoch
   convention before any public function is added.

2. The subsystem spans multiple physical domains:
   - Keplerian elements (a, e, i, Ω, ω, M) — orbital shape and orientation
   - Distance extremes (perihelion/aphelion distance and date)
   - Orbital period
   These should be one coherent subsystem, not scattered helpers.

3. Validation requires comparison against published ephemeris tables
   (Meeus Appendix I, JPL HORIZONS) for at least the eight major planets.

Doctrinal decisions (recorded here before implementation)
---------------------------------------------------------
Decision 1: Coordinate frame
    Heliocentric osculating elements in the J2000.0 ecliptic frame.
    Rationale: osculating elements are meaningful for astrological
    distance-extremes computation; barycentric elements are more accurate
    for long-term dynamics but less intuitive for astrological use.
    The frame choice must be documented on the vessel and in every
    function that produces one.

Decision 2: Module location
    ``moira.orbits`` exists as a public module.
    Rationale: orbital elements are a distinct computational layer, not a
    helper function on planets.py.  They deserve their own module with
    its own validation story and own SCP entry point.

Decision 3: No raw float arrays
    All results are ``KeplerianElements`` or ``DistanceExtremes`` instances.
    Swiss-style array-indexed returns are explicitly rejected.

Validation plan (must exist before ``status=implemented``)
----------------------------------------------------------
- Compare ``OrbitalElements`` for all eight planets against Meeus Table 31.a
  (J2000.0 values) — tolerance 0.01° for angles, 0.001 AU for semi-major axis.
- Compare ``DistanceExtremes`` against JPL HORIZONS for at least three
  consecutive perihelion/aphelion events per planet — tolerance ±1 day, ±0.001 AU.

Public surface
--------------
    KeplerianElements — typed vessel for Keplerian orbital elements
    DistanceExtremes  — typed vessel for perihelion/aphelion distances and dates

Import-time side effects: None
"""

from __future__ import annotations

from dataclasses import dataclass


__all__ = [
    "KeplerianElements",
    "DistanceExtremes",
]


# ---------------------------------------------------------------------------
# KeplerianElements
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class KeplerianElements:
    """
    Keplerian osculating orbital elements for a solar system body.

    Equivalent to the output of Swiss Ephemeris ``swe_get_orbital_elements``,
    expressed as a typed, named vessel rather than a raw float array.

    Coordinate frame: heliocentric, J2000.0 ecliptic and equinox.
    Element type: osculating (instantaneous, valid at ``epoch_jd``).

    Fields
    ------
    name : str
        Body name (one of the ``Body.*`` constants).
    epoch_jd : float
        Julian Day (TT) at which the elements were computed.
    semi_major_axis_au : float
        Semi-major axis in Astronomical Units (AU).
    eccentricity : float
        Orbital eccentricity [0, 1) for elliptical orbits.
    inclination_deg : float
        Orbital inclination to the J2000.0 ecliptic (degrees).
    lon_ascending_node_deg : float
        Longitude of the ascending node, measured from the J2000.0
        vernal equinox (degrees, [0, 360)).
    arg_perihelion_deg : float
        Argument of perihelion, measured from the ascending node
        in the orbital plane (degrees, [0, 360)).
    mean_anomaly_deg : float
        Mean anomaly at epoch (degrees, [0, 360)).
    mean_motion_deg_per_day : float
        Mean daily motion in longitude (degrees/day).
    orbital_period_days : float
        Sidereal orbital period in days.
    """
    name:                   str
    epoch_jd:               float
    semi_major_axis_au:     float
    eccentricity:           float
    inclination_deg:        float
    lon_ascending_node_deg: float
    arg_perihelion_deg:     float
    mean_anomaly_deg:       float
    mean_motion_deg_per_day: float
    orbital_period_days:    float

    @property
    def perihelion_distance_au(self) -> float:
        """Perihelion distance: a(1 − e)."""
        return self.semi_major_axis_au * (1.0 - self.eccentricity)

    @property
    def aphelion_distance_au(self) -> float:
        """Aphelion distance: a(1 + e)."""
        return self.semi_major_axis_au * (1.0 + self.eccentricity)


# ---------------------------------------------------------------------------
# DistanceExtremes
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class DistanceExtremes:
    """
    Perihelion and aphelion distances and dates for a solar system body.

    Equivalent to Swiss Ephemeris ``swe_orbit_max_min_true_distance``,
    expressed as a typed vessel.

    This vessel records the body's next (or most recent) perihelion and
    aphelion passage, together with the heliocentric distance at each.

    Fields
    ------
    name : str
        Body name (one of the ``Body.*`` constants).
    perihelion_jd : float
        Julian Day (TT) of the perihelion passage.
    perihelion_distance_au : float
        Heliocentric distance at perihelion (AU).
    aphelion_jd : float
        Julian Day (TT) of the aphelion passage.
    aphelion_distance_au : float
        Heliocentric distance at aphelion (AU).

    Doctrine note: both passages are recorded for the same orbit (one
    perihelion and one aphelion per vessel).  For inner planets the
    aphelion often precedes the perihelion in the search window; the
    vessel records them as observed, with no forced temporal ordering.
    """
    name:                    str
    perihelion_jd:           float
    perihelion_distance_au:  float
    aphelion_jd:             float
    aphelion_distance_au:    float
