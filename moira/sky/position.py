"""
moira.sky.position — Astrometric Correction Pipeline
=====================================================
Named stages of Moira's five-stage astrometric correction pipeline and
atmospheric refraction models.

The pipeline converts geometric ICRF coordinates (as returned by an
ephemeris) into observable apparent positions, applying corrections in
the order listed below.

Pipeline stages
---------------
1. apply_light_time
   Iterative geometric delay: given an observer position and a body's
   barycentric state, returns the body's ICRF position at the retarded
   epoch when the observed light was emitted.

2. apply_aberration
   Relativistic stellar aberration due to the observer's velocity
   relative to the Solar System Barycentre.  Implements the full
   relativistic formula (not the classical v/c approximation).

3. apply_deflection
   Gravitational light deflection in the GCRS due to the Sun, Jupiter,
   and Saturn.  Significant at the sub-arcsecond level near these limbs.

4. apply_frame_bias
   IAU 2006 FK5/ICRS frame alignment correction.  Removes the ~17 mas
   offset between the FK5 equinox and the ICRS origin.

5. topocentric_correction
   WGS-84 observer parallax shift.  Converts geocentric apparent
   coordinates to the observer's topocentric position.

Atmospheric refraction
----------------------
apply_refraction
    Final apparent position correction using the refraction model
    selected by the computation policy.

atmospheric_refraction
    Bennett (1982) model.  Altitude only.  Fast.

atmospheric_refraction_extended
    Full physical model including temperature, pressure, humidity,
    wavelength, and observer elevation above the horizon.
"""

from __future__ import annotations

from moira.coordinates import (
    atmospheric_refraction,
    atmospheric_refraction_extended,
)
from moira.corrections import (
    apply_aberration,
    apply_deflection,
    apply_frame_bias,
    apply_light_time,
    apply_refraction,
    topocentric_correction,
)

__all__ = [
    # Astrometric pipeline stages (application order)
    "apply_light_time",
    "apply_aberration",
    "apply_deflection",
    "apply_frame_bias",
    "topocentric_correction",
    # Final apparent position
    "apply_refraction",
    # Atmospheric refraction models
    "atmospheric_refraction",
    "atmospheric_refraction_extended",
]
