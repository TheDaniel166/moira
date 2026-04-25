"""
Moira — Planetocentric Position Engine
=======================================

Archetype: Engine

Purpose
-------
Governs computation of planetocentric ecliptic positions — the apparent
positions of celestial bodies as seen from the center of a specific planet
other than Earth.

Every body in the DE441 kernel can serve as an observer.  The resulting
ecliptic longitude, latitude, distance, and longitudinal speed are expressed
in the true-of-date geocentric ecliptic frame (precession + nutation applied),
making the output directly comparable to Moira's geocentric and heliocentric
position products.

Heliocentric (observer = Sun) and geocentric (observer = Earth) are both
degenerate cases of this engine, though dedicated implementations already
exist for each in ``moira.planets``.

Boundary declaration
--------------------
Owns: PlanetocentriData vessel, ``planetocentric_at``, ``all_planetocentric_at``.
Delegates: barycentric state vectors to the private helpers in ``moira.planets``,
           frame rotation to ``moira.coordinates``,
           ecliptic projection to ``moira.coordinates``,
           obliquity to ``moira.obliquity``.

Import-time side effects: None

External dependency assumptions
--------------------------------
Requires the DE441 kernel to be initialised (same requirement as
``moira.planets.planet_at``).  No Qt main thread required.  No database access.

Valid observers
---------------
Any body with a defined barycentric state in the DE441 kernel:

    Body.SUN, Body.MOON,
    Body.MERCURY, Body.VENUS, Body.EARTH, Body.MARS,
    Body.JUPITER, Body.SATURN, Body.URANUS, Body.NEPTUNE, Body.PLUTO

Public surface
--------------
``PlanetocentricData``   — vessel for a single planetocentric position.
``VALID_OBSERVER_BODIES`` — frozenset of body names that may serve as observers.
``planetocentric_at``    — position of one target from one observer.
``all_planetocentric_at`` — positions of all visible bodies from one observer.
"""

from dataclasses import dataclass, field

from .constants import Body, NAIF_ROUTES, KM_PER_AU, sign_of
from .coordinates import (
    icrf_to_ecliptic, mat_vec_mul, vec_sub,
    precession_matrix_equatorial,
    nutation_matrix_equatorial,
)
from .julian import ut_to_tt, decimal_year
from .obliquity import true_obliquity

__all__ = [
    "PlanetocentricData",
    "VALID_OBSERVER_BODIES",
    "planetocentric_at",
    "all_planetocentric_at",
]

# ---------------------------------------------------------------------------
# Valid observer / target set
# ---------------------------------------------------------------------------

#: Bodies that have a well-defined barycentric state in the DE441 kernel and
#: may serve as either observer or target in a planetocentric computation.
#: Earth is included explicitly because it requires a separate kernel route
#: (SSB → EMB → Earth) not present in ``NAIF_ROUTES``.
VALID_OBSERVER_BODIES: frozenset[str] = frozenset(NAIF_ROUTES.keys()) | {Body.EARTH}


# ---------------------------------------------------------------------------
# Data vessel
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class PlanetocentricData:
    """
    RITE: The Observer-Planet Position Vessel.

    THEOREM: Holds the apparent ecliptic position of a target body as seen
    from the center of a specified observer planet, expressed in the
    true-of-date geocentric ecliptic frame.

    RITE OF PURPOSE:
        Serves the Planetocentric Engine as the canonical result vessel.
        Without it, callers would need to interpret raw ICRF vectors
        themselves and manage frame consistency manually.

    LAW OF OPERATION:
        Responsibilities:
            - Store observer name, target name, ecliptic longitude, latitude,
              distance, longitudinal speed, and retrograde flag.
            - Derive and store zodiacal sign data consistent with longitude.
        Non-responsibilities:
            - Does not compute positions (delegated to ``planetocentric_at``).
            - Does not validate that observer ≠ target.
            - Does not perform coordinate transforms or time conversions.
        Structural invariants:
            - ``longitude`` is in [0°, 360°).
            - ``sign``, ``sign_symbol``, ``sign_degree`` are always consistent
              with ``longitude`` after ``__post_init__`` completes.
            - ``retrograde`` is always True iff ``speed < 0``.
        Succession stance: terminal.

    Canon: NAIF/SPICE SPK kernel conventions;
           Meeus, "Astronomical Algorithms" Ch. 26.

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.planetocentric.PlanetocentricData",
        "risk": "low",
        "api": {
            "public_methods": ["__repr__", "distance_au"],
            "public_attributes": [
                "observer", "name", "longitude", "latitude",
                "distance", "speed", "retrograde",
                "sign", "sign_symbol", "sign_degree"
            ]
        },
        "state": {
            "mutable": false,
            "fields": [
                "observer", "name", "longitude", "latitude",
                "distance", "speed", "retrograde",
                "sign", "sign_symbol", "sign_degree"
            ]
        },
        "effects": {"io": [], "signals_emitted": [], "db_writes": []},
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": [],
            "policy": "caller ensures valid observer/target and jd before construction"
        },
        "succession": {"stance": "terminal", "override_points": []},
        "agent": "urania"
    }
    [/MACHINE_CONTRACT]
    """

    observer:    str    # Observer planet (Body.* constant)
    name:        str    # Target body name
    longitude:   float  # Ecliptic longitude in degrees, [0°, 360°)
    latitude:    float  # Ecliptic latitude in degrees, (−90°, +90°)
    distance:    float  # Distance in km
    speed:       float  # Longitudinal speed in degrees/day
    retrograde:  bool   # True when speed < 0

    # Derived zodiac fields — populated by __post_init__
    sign:        str   = field(init=False)
    sign_symbol: str   = field(init=False)
    sign_degree: float = field(init=False)

    def __post_init__(self) -> None:
        self.sign, self.sign_symbol, self.sign_degree = sign_of(self.longitude)

    @property
    def distance_au(self) -> float:
        """Distance in astronomical units."""
        return self.distance / KM_PER_AU

    def __repr__(self) -> str:
        return (
            f"PlanetocentricData("
            f"observer={self.observer!r}, "
            f"name={self.name!r}, "
            f"lon={self.longitude:.4f}°, "
            f"lat={self.latitude:.4f}°, "
            f"dist={self.distance_au:.4f} AU)"
        )


# ---------------------------------------------------------------------------
# Internal: unified barycentric state resolver
# ---------------------------------------------------------------------------

def _body_barycentric_state(
    body: str,
    jd_tt: float,
    reader,
):
    """
    Return the Solar System Barycentric (SSB) position and velocity of a body.

    Handles Earth explicitly (requires SSB→EMB→Earth route not in NAIF_ROUTES)
    and delegates all other bodies to ``planets._barycentric_state``.
    """
    # Import here to keep the module boundary explicit and avoid circular imports.
    from .planets import _barycentric_state, _earth_barycentric_state

    if body == Body.EARTH:
        return _earth_barycentric_state(jd_tt, reader)
    return _barycentric_state(body, jd_tt, reader)


def _longitude_rate_ecl(xyz, vel_xyz, obliquity_deg: float) -> float:
    """
    Longitudinal speed (degrees/day) from ecliptic-projected state vectors.

    Delegates to planets._longitude_rate; reproduced here as a private shim
    to avoid importing a private symbol across module boundaries.
    """
    from .planets import _longitude_rate
    return _longitude_rate(xyz, vel_xyz, obliquity_deg)


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def planetocentric_at(
    observer: str,
    target:   str,
    jd_ut:    float,
    reader=None,
) -> PlanetocentricData:
    """
    Compute the apparent ecliptic position of ``target`` as seen from
    the center of ``observer``.

    Positions are expressed in the true-of-date geocentric ecliptic frame
    (precession and nutation applied), consistent with Moira's geocentric
    and heliocentric position products.

    Parameters
    ----------
    observer : Body name of the observer planet (e.g. ``Body.MARS``).
               Must be a member of ``VALID_OBSERVER_BODIES``.
    target   : Body name of the target body (e.g. ``Body.JUPITER``).
               Must be a member of ``VALID_OBSERVER_BODIES``.
               Must differ from ``observer``.
    jd_ut    : Julian Day Number in Universal Time (UT1).
    reader   : An open ``SpkReader`` instance.  If ``None``, the module-level
               singleton returned by ``moira.planets.get_reader()`` is used.

    Returns
    -------
    PlanetocentricData — ecliptic position, distance, speed, sign data.

    Raises
    ------
    ValueError
        If ``observer`` or ``target`` is not in ``VALID_OBSERVER_BODIES``,
        or if ``observer == target``.

    Notes
    -----
    The computation is:

        xyz = barycentric_pos(target) − barycentric_pos(observer)
        vel = barycentric_vel(target) − barycentric_vel(observer)

    Both vectors are then rotated to the true-of-date equatorial frame
    (precession + nutation) and projected onto the ecliptic.  The
    precession-rate contribution to velocity (~50″/century) is neglected,
    consistent with the heliocentric implementation in ``moira.planets``.

    Light-travel time is not corrected.  For precise work (eclipses, occultations
    from another planet's perspective) the caller should apply a light-time
    iteration on top of this function.
    """
    if observer not in VALID_OBSERVER_BODIES:
        raise ValueError(
            f"planetocentric_at: {observer!r} is not a valid observer. "
            f"Choose from VALID_OBSERVER_BODIES."
        )
    if target not in VALID_OBSERVER_BODIES:
        raise ValueError(
            f"planetocentric_at: {target!r} is not a valid target. "
            f"Choose from VALID_OBSERVER_BODIES."
        )
    if observer == target:
        raise ValueError(
            f"planetocentric_at: observer and target must differ, got {observer!r} for both."
        )

    from .planets import get_reader, approx_year as _approx_year

    if reader is None:
        reader = get_reader()

    year, month, *_ = _approx_year(jd_ut)
    jd_tt = ut_to_tt(jd_ut, decimal_year(year, month))

    # -----------------------------------------------------------------------
    # Barycentric states for observer and target
    # -----------------------------------------------------------------------
    obs_pos, obs_vel = _body_barycentric_state(observer, jd_tt, reader)
    tgt_pos, tgt_vel = _body_barycentric_state(target,   jd_tt, reader)

    # Position and velocity of target relative to observer (ICRF/J2000 approx)
    xyz = vec_sub(tgt_pos, obs_pos)
    vel = vec_sub(tgt_vel, obs_vel)

    # -----------------------------------------------------------------------
    # Rotate to true-of-date equatorial frame (precession + nutation)
    # -----------------------------------------------------------------------
    prec_mat = precession_matrix_equatorial(jd_tt)
    nut_mat  = nutation_matrix_equatorial(jd_tt)
    xyz_tod  = mat_vec_mul(nut_mat, mat_vec_mul(prec_mat, xyz))
    vel_tod  = mat_vec_mul(nut_mat, mat_vec_mul(prec_mat, vel))

    # -----------------------------------------------------------------------
    # Project to ecliptic, derive speed
    # -----------------------------------------------------------------------
    obliquity = true_obliquity(jd_tt)
    lon, lat, dist = icrf_to_ecliptic(xyz_tod, obliquity)
    speed = _longitude_rate_ecl(xyz_tod, vel_tod, obliquity)

    return PlanetocentricData(
        observer   = observer,
        name       = target,
        longitude  = lon,
        latitude   = lat,
        distance   = dist,
        speed      = speed,
        retrograde = (speed < 0.0),
    )


def all_planetocentric_at(
    observer:  str,
    jd_ut:     float,
    bodies:    list[str] | None = None,
    reader=None,
) -> dict[str, PlanetocentricData]:
    """
    Compute planetocentric positions for multiple target bodies at once.

    Parameters
    ----------
    observer : Body name of the observer planet.
               Must be a member of ``VALID_OBSERVER_BODIES``.
    jd_ut    : Julian Day Number in Universal Time (UT1).
    bodies   : Target bodies to compute.  Defaults to all members of
               ``VALID_OBSERVER_BODIES`` except ``observer`` itself.
    reader   : An open ``SpkReader`` instance.  If ``None``, the module-level
               singleton is used.

    Returns
    -------
    dict mapping target body name (``str``) to ``PlanetocentricData``.
    """
    if observer not in VALID_OBSERVER_BODIES:
        raise ValueError(
            f"all_planetocentric_at: {observer!r} is not a valid observer. "
            f"Choose from VALID_OBSERVER_BODIES."
        )

    if bodies is None:
        bodies = sorted(VALID_OBSERVER_BODIES - {observer})

    from .planets import get_reader, approx_year as _approx_year
    if reader is None:
        reader = get_reader()

    results: dict[str, PlanetocentricData] = {}
    for target in bodies:
        if target == observer:
            continue
        results[target] = planetocentric_at(observer, target, jd_ut, reader=reader)
    return results

