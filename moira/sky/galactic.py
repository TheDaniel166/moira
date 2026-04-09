"""
moira.sky.galactic — Galactic Coordinate System
================================================
Strict astronomy API for galactic frame transforms and reference point
catalog.

Rotation matrix authority
--------------------------
Liu, Zhu & Zhang (2011, A&A 526, A16) — ICRS-to-galactic rotation
constants derived from the IAU 1958 galactic pole definition realigned to
the ICRS.  The matrix is exact; no approximation is applied in the
equatorial-to-galactic path.

Coordinate conventions
-----------------------
Galactic longitude  l   0° toward GC, increasing eastward
Galactic latitude   b   +90° at NGP, −90° at SGP
Frame               IAU 1958 galactic system, rigorously tied to ICRS/J2000

Reference points (J2000 equatorial)
-------------------------------------
GC   Galactic Center (IAU definition point, closely matches Sgr A*)
     RA 266.4051°  Dec −28.9362°
NGP  North Galactic Pole  (in Coma Berenices)
     RA 192.8595°  Dec +27.1283°
GAC  Galactic Anti-Center  (in Gemini / Auriga)
     RA  86.4051°  Dec +28.9362°
SGP  South Galactic Pole
     RA  12.8595°  Dec −27.1283°
SGC  Super-Galactic Center  (Virgo / M87)
     RA 187.7059°  Dec +12.3911°

Ecliptic coordinates of these reference points at any epoch are computed
by ``galactic_reference_points(obliquity, jd_tt)``.

Transforms
-----------
equatorial_to_galactic   RA/Dec → (l, b)   — J2000, no epoch conversion
galactic_to_equatorial   (l, b) → RA/Dec   — J2000
ecliptic_to_galactic     ecliptic lon/lat → (l, b)  — bridges via RA/Dec
galactic_to_ecliptic     (l, b) → ecliptic lon/lat  — bridges via RA/Dec

Both ecliptic functions require ``obliquity`` (degrees) and ``jd_tt`` for
the precession + nutation bridge through the equatorial frame.

Position vessel
---------------
GalacticPosition
    body, lon (l), lat (b), ecliptic_lon, ecliptic_lat.
    Computed properties:
      near_galactic_plane          True if |b| < threshold
      galactic_hemisphere          'north' or 'south'
      angular_distance_to_gc       great-circle separation from GC in degrees
      angular_distance_to_anticenter

Batch and single-body helpers
------------------------------
galactic_position_of     compute GalacticPosition for one body
all_galactic_positions   compute a list[GalacticPosition] for a chart

Reference point table
---------------------
galactic_reference_points(obliquity, jd_tt)
    Returns dict[str, tuple[float, float]] mapping each of the five named
    points (GC, NGP, GAC, SGP, SGC) to (ecliptic_lon, ecliptic_lat) at the
    given epoch.
"""

from __future__ import annotations

from moira.galactic import (
    GalacticPosition,
    all_galactic_positions,
    ecliptic_to_galactic,
    equatorial_to_galactic,
    galactic_position_of,
    galactic_reference_points,
    galactic_to_ecliptic,
    galactic_to_equatorial,
)

__all__ = [
    # Transforms
    "equatorial_to_galactic",
    "galactic_to_equatorial",
    "ecliptic_to_galactic",
    "galactic_to_ecliptic",
    # Reference points
    "galactic_reference_points",
    # Result vessel
    "GalacticPosition",
    # Helpers
    "galactic_position_of",
    "all_galactic_positions",
]
