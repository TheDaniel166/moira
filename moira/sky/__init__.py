"""
moira.sky — Strict Astronomy API
=================================
A sovereign astronomical computation surface built on Moira's substrate.

This is not a wrapper around an external black box.  Every quantity here
is derived from Moira's own verified computational pipeline.

Subsystems
----------
moira.sky.time
    UT / TT / TDB / ERA / GMST / GAST / LAST conversions,
    physics-based ΔT decomposition with uncertainty.

moira.sky.position
    Five-stage astrometric correction pipeline: light-time, relativistic
    aberration, gravitational deflection, IAU 2006 frame bias,
    WGS-84 topocentric parallax.  Atmospheric refraction models.

moira.sky.frames
    Reference frame transforms: ICRF, ecliptic (mean and true),
    equatorial, horizontal.  Precession and nutation rotation matrices.
    Equatorial-to-horizon projection.  Equation of time.

moira.sky.visibility
    Observational visibility doctrine: Yallop 1997 lunar crescent,
    Khalid-Sultana 1991 moonlight, arcus visionis, heliacal event search
    for planets, Moon, and stars.

moira.sky.bodies        [stub]
    Planetary positions, Moon, Sun, asteroids, lunar nodes / apsides.

moira.sky.observation   [stub]
    Phase angle, illuminated fraction, angular diameter, apparent
    magnitude, elongation.

moira.sky.galactic      [stub]
    Galactic coordinate transforms, reference points.

moira.sky.events        [stub]
    Stations, conjunctions, apsides, Moon phases, solstices/equinoxes.

moira.sky.eclipse       [stub]
    Solar and lunar eclipse prediction, contacts, geographic paths,
    Saros and Metonic identification, local circumstances.

moira.sky.occultation   [stub]
    Lunar and stellar occultations, close approaches, geographic paths.

Design contract
---------------
- Every symbol surfaces Moira's internal computation directly.
- application-layer coupling (e.g. local_space_from_chart) is excluded.
- No silent fallbacks, no hidden defaults.
- Stubs are documented but raise NotImplementedError — they do not pretend.
"""

from __future__ import annotations

from moira.sky import (  # noqa: F401  (ensure submodules are importable)
    bodies,
    eclipse,
    events,
    frames,
    galactic,
    observation,
    occultation,
    position,
    time,
    visibility,
)

__all__ = [
    "bodies",
    "eclipse",
    "events",
    "frames",
    "galactic",
    "observation",
    "occultation",
    "position",
    "time",
    "visibility",
]
