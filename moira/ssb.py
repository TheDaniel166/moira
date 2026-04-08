"""
Moira — ssb.py: Solar System Barycenter Chart Engine
=====================================================

Archetype: Engine

Purpose
-------
Governs computation of ecliptic positions expressed relative to the Solar
System Barycenter (SSB), the true inertial center-of-mass of the solar
system.

In all other Moira position engines, coordinates are expressed relative to
a named body (Earth for geocentric, the Sun for heliocentric, or an
arbitrary planet for planetocentric).  The SSB chart uses the BCRS
(Barycentric Celestial Reference System) origin directly — the same
inertial frame that the DE441 kernel uses natively.

The Sun is *not* at the SSB; it wanders up to ~2.2 solar radii (~0.010 AU)
from the barycenter, driven mainly by Jupiter's mass.  This displacement is
small but real and directly accessible here without any approximation.

Frame
-----
Positions are given in the true-of-date geocentric ecliptic frame
(precession + nutation applied), consistent with all other Moira position
products.  The frame rotations are applied to the raw ICRF barycentric
vectors before ecliptic projection.

Boundary declaration
--------------------
Owns: SSBPosition vessel, ``SSB_BODIES``, ``ssb_position_at``,
      ``all_ssb_positions_at``.
Delegates: barycentric state vectors to the private helpers in
           ``moira.planets``, frame rotation to ``moira.coordinates``,
           ecliptic projection to ``moira.coordinates``,
           obliquity to ``moira.obliquity``.

Import-time side effects: None

External dependency assumptions
--------------------------------
Requires the DE441 kernel to be initialised (same requirement as
``moira.planets.planet_at``).

Public surface
--------------
``SSBPosition``        — vessel for a single SSB-relative position.
``SSB_BODIES``         — frozenset of body names for which SSB positions
                         can be computed.
``ssb_position_at``    — SSB-relative position of one body.
``all_ssb_positions_at`` — SSB-relative positions of all supported bodies.
"""

from dataclasses import dataclass, field

from .constants import Body, NAIF_ROUTES, KM_PER_AU, sign_of
from .coordinates import (
    icrf_to_ecliptic,
    mat_vec_mul,
    vec_norm,
    precession_matrix_equatorial,
    nutation_matrix_equatorial,
)
from .julian import ut_to_tt, decimal_year
from .obliquity import true_obliquity

__all__ = [
    "SSBPosition",
    "SSB_BODIES",
    "ssb_position_at",
    "all_ssb_positions_at",
]

# ---------------------------------------------------------------------------
# Valid body set
# ---------------------------------------------------------------------------

#: Bodies for which a well-defined barycentric state exists in the DE441 kernel.
#: Earth is included explicitly because it requires the SSB→EMB→Earth chain
#: rather than a direct NAIF_ROUTES entry.
SSB_BODIES: frozenset[str] = frozenset(NAIF_ROUTES.keys()) | {Body.EARTH}


# ---------------------------------------------------------------------------
# Data vessel
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class SSBPosition:
    """
    RITE: The Solar System Barycenter Position Vessel.

    THEOREM: Holds the ecliptic position of a body as measured from the Solar
    System Barycenter (SSB), expressed in the true-of-date ecliptic frame.

    Unlike ``PlanetData`` (which is always geocentric) or ``PlanetocentricData``
    (which references an arbitrary planet observer), ``SSBPosition`` uses the
    BCRS inertial origin.  The Sun itself has a non-zero position here,
    displaced from the SSB by the gravitational pull of the giant planets.

    Structural invariants
    ---------------------
    - ``longitude`` is in [0°, 360°).
    - ``sign``, ``sign_symbol``, ``sign_degree`` are always consistent with
      ``longitude`` after ``__post_init__`` completes.
    - ``retrograde`` is always True iff ``speed < 0``.
    - ``distance`` is always ≥ 0 (the SSB itself is the origin).
    """

    name:       str    # Body name (Body.* constant)
    longitude:  float  # Ecliptic longitude in degrees, [0°, 360°)
    latitude:   float  # Ecliptic latitude in degrees, (−90°, +90°)
    distance:   float  # Distance from SSB in km
    speed:      float  # Longitudinal speed in degrees/day
    retrograde: bool   # True when speed < 0

    # Derived zodiac fields — populated by __post_init__
    sign:        str   = field(init=False)
    sign_symbol: str   = field(init=False)
    sign_degree: float = field(init=False)

    def __post_init__(self) -> None:
        self.sign, self.sign_symbol, self.sign_degree = sign_of(self.longitude)

    @property
    def distance_au(self) -> float:
        """Distance from the Solar System Barycenter in Astronomical Units."""
        return self.distance / KM_PER_AU

    def __repr__(self) -> str:
        return (
            f"SSBPosition("
            f"name={self.name!r}, "
            f"lon={self.longitude:.4f}°, "
            f"lat={self.latitude:.4f}°, "
            f"dist={self.distance_au:.6f} AU)"
        )


# ---------------------------------------------------------------------------
# Internal: unified barycentric state resolver (same pattern as planetocentric)
# ---------------------------------------------------------------------------

def _body_barycentric_state(body: str, jd_tt: float, reader):
    """
    Return the SSB-relative position and velocity of a body (km, km/day, ICRF).

    Handles Earth explicitly (SSB→EMB→Earth route not in NAIF_ROUTES) and
    delegates all other bodies to ``planets._barycentric_state``.
    """
    from .planets import _barycentric_state, _earth_barycentric_state

    if body == Body.EARTH:
        return _earth_barycentric_state(jd_tt, reader)
    return _barycentric_state(body, jd_tt, reader)


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def ssb_position_at(
    body:   str,
    jd_ut:  float,
    reader=None,
) -> SSBPosition:
    """
    Compute the ecliptic position of ``body`` relative to the Solar System
    Barycenter (SSB) at the given Julian Date.

    The position vector is the raw barycentric state of the body, taken
    directly from the DE441 kernel without subtracting any observer.  Frame
    rotations (precession + nutation) are applied to bring the ICRF vector
    into the true-of-date ecliptic frame used by all Moira position products.

    Parameters
    ----------
    body   : Body name (``Body.*`` constant).  Must be in ``SSB_BODIES``.
    jd_ut  : Julian Day Number in Universal Time (UT1).
    reader : An open ``SpkReader`` instance.  If ``None``, the module-level
             singleton from ``moira.planets.get_reader()`` is used.

    Returns
    -------
    SSBPosition — ecliptic position relative to the SSB, speed, sign data.

    Raises
    ------
    ValueError
        If ``body`` is not in ``SSB_BODIES``.

    Notes
    -----
    Light-travel time is not corrected.  The SSB chart is a geometric
    (astrometric) product — it shows where bodies physically are relative
    to the inertial center of the solar system, not where they appear to be
    from Earth.
    """
    if body not in SSB_BODIES:
        raise ValueError(
            f"ssb_position_at: {body!r} is not in SSB_BODIES. "
            f"Choose from: {sorted(SSB_BODIES)}"
        )

    from .planets import get_reader, approx_year as _approx_year, _longitude_rate

    if reader is None:
        reader = get_reader()

    year, month, *_ = _approx_year(jd_ut)
    jd_tt = ut_to_tt(jd_ut, decimal_year(year, month))

    # -----------------------------------------------------------------------
    # Barycentric position and velocity (ICRF, km / km·day⁻¹)
    # -----------------------------------------------------------------------
    pos, vel = _body_barycentric_state(body, jd_tt, reader)

    # -----------------------------------------------------------------------
    # Rotate to true-of-date equatorial frame (precession + nutation)
    # -----------------------------------------------------------------------
    prec_mat = precession_matrix_equatorial(jd_tt)
    nut_mat  = nutation_matrix_equatorial(jd_tt)
    pos_tod  = mat_vec_mul(nut_mat, mat_vec_mul(prec_mat, pos))
    vel_tod  = mat_vec_mul(nut_mat, mat_vec_mul(prec_mat, vel))

    # -----------------------------------------------------------------------
    # Project to ecliptic, derive speed and distance
    # -----------------------------------------------------------------------
    obliquity = true_obliquity(jd_tt)
    lon, lat, dist = icrf_to_ecliptic(pos_tod, obliquity)
    speed = _longitude_rate(pos_tod, vel_tod, obliquity)

    return SSBPosition(
        name       = body,
        longitude  = lon,
        latitude   = lat,
        distance   = dist,
        speed      = speed,
        retrograde = (speed < 0.0),
    )


def all_ssb_positions_at(
    jd_ut:  float,
    bodies: list[str] | None = None,
    reader=None,
) -> dict[str, SSBPosition]:
    """
    Compute SSB-relative positions for multiple bodies at once.

    Parameters
    ----------
    jd_ut  : Julian Day Number in Universal Time (UT1).
    bodies : List of body names to compute.  Defaults to all members of
             ``SSB_BODIES``.
    reader : An open ``SpkReader`` instance.  If ``None``, the module-level
             singleton is used.

    Returns
    -------
    dict mapping body name (``str``) to ``SSBPosition``.

    Raises
    ------
    ValueError
        If any entry in ``bodies`` is not in ``SSB_BODIES``.
    """
    if bodies is None:
        bodies = sorted(SSB_BODIES)

    from .planets import get_reader
    if reader is None:
        reader = get_reader()

    return {body: ssb_position_at(body, jd_ut, reader=reader) for body in bodies}
