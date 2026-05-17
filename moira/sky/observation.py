"""
moira.sky.observation — Observational Quantities and Phenomena
==============================================================
Strict astronomy API for the visual appearance of solar system bodies and
discrete orbital phenomena.

Phase quantities  (moira.phase)
--------------------------------
phase_angle(body, jd_ut)
    Sun–Planet–Earth angle in degrees.
    0° = full illumination (superior conjunction / opposition side).
    180° = new (inferior conjunction side, fully dark toward observer).

illuminated_fraction(phase_angle)
    Fraction of disk illuminated (0.0–1.0) derived from phase angle.

elongation(body, jd_ut)
    Angular separation from the Sun in degrees (0°–180°).

synodic_phase_angle(body1, body2, jd_ut)
    Ecliptic phase angle between any two bodies (0°–360°).

synodic_phase_state(angle_deg)
    Coarse phase state label — e.g. "waxing", "full", "waning" — for a
    synodic phase angle.

angular_diameter(body, jd_ut)
    Apparent angular diameter in arcseconds, computed from the body's
    physical radius and geocentric distance.

apparent_magnitude(body, jd_ut)
    Apparent visual magnitude (V band), using a simplified IAU-style model.

Orbital phenomena  (moira.phenomena)
--------------------------------------
Result vessels
..............
PhenomenonEvent
    A single phenomenon: body name, kind label, epoch (JD_UT), and the
    key geometric value (elongation, distance, etc.) at that epoch.

OrbitalResonance
    Harmonic ratio between two orbital periods in the form P/Q with a
    precision measure.

PlanetPhenomena
    Snapshot of all phenomena for one planet at a given epoch: phase angle,
    illuminated fraction, elongation, next and previous apsides.

Moon phase constant table
.........................
MOON_PHASE_ANGLES
    dict mapping phase name → target elongation in degrees.
    Keys: "new_moon", "first_quarter", "full_moon", "last_quarter",
          "waxing_crescent", "waxing_gibbous", "waning_gibbous",
          "waning_crescent".

Search functions
................
greatest_elongation(body, jd_start)
    Next greatest elongation (east or west) of Mercury or Venus.

perihelion(body, jd_start)
    Next perihelion passage of a planet.

aphelion(body, jd_start)
    Next aphelion passage of a planet.

next_moon_phase(phase_name, jd_start)
    Next occurrence of a named Moon phase after jd_start.

moon_phases_in_range(jd_start, jd_end)
    All eight Moon phases in a date range.

next_conjunction(body1, body2, jd_start)
    Next geocentric conjunction between two named bodies.

conjunctions_in_range(body1, body2, jd_start, jd_end)
    All geocentric conjunctions in a date range.

resonance(body1, body2)
    Best harmonic ratio P/Q between the sidereal periods of two bodies.

planet_phenomena_at(body, jd_ut)
    Full PlanetPhenomena snapshot for a body at an epoch.
"""

from __future__ import annotations

from moira.phase import (
    angular_diameter,
    apparent_magnitude,
    elongation,
    illuminated_fraction,
    phase_angle,
    synodic_phase_angle,
    synodic_phase_state,
)
from moira.phenomena import (
    MOON_PHASE_ANGLES,
    OrbitalResonance,
    PhenomenonEvent,
    PlanetPhenomena,
    aphelion,
    conjunctions_in_range,
    greatest_elongation,
    moon_phases_in_range,
    next_conjunction,
    next_moon_phase,
    perihelion,
    planet_phenomena_at,
    resonance,
)

__all__ = [
    # Phase quantities
    "phase_angle",
    "illuminated_fraction",
    "elongation",
    "synodic_phase_angle",
    "synodic_phase_state",
    "angular_diameter",
    "apparent_magnitude",
    # Phenomena — result vessels
    "PhenomenonEvent",
    "OrbitalResonance",
    "PlanetPhenomena",
    # Phenomena — constants
    "MOON_PHASE_ANGLES",
    # Phenomena — search functions
    "greatest_elongation",
    "perihelion",
    "aphelion",
    "next_moon_phase",
    "moon_phases_in_range",
    "next_conjunction",
    "conjunctions_in_range",
    "resonance",
    "planet_phenomena_at",
]
