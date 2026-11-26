"""
Moira — Planetocentric Position Engine
=======================================

Archetype: Engine

Purpose
-------
Governs computation of planetocentric ecliptic positions — the geometric
positions of celestial bodies measured from the ephemeris state selected for
an observer body.

Every body in the DE441 kernel can serve as an observer.  The resulting
ecliptic longitude, latitude, distance, and longitudinal speed are expressed
with SSB-origin vectors differenced into the requested observer-origin vector
and then rotated into the true-of-date ecliptic orientation (precession +
nutation applied), making the output directly comparable in orientation to
Moira's geocentric and heliocentric position products.

Heliocentric (observer = Sun) and geocentric (observer = Earth) are both
degenerate cases of this engine, though dedicated implementations already
exist for each in ``moira.planets``.

Boundary declaration
--------------------
Owns: PlanetocentricData, its reduction receipt, and the single and batch
      planetocentric position surfaces.
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
``all_planetocentric_at_with_truth`` — batch positions with per-result reduction truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .constants import Body, EARTH_ROUTE, NAIF_ROUTES, KM_PER_AU, sign_of
from .coordinates import icrf_to_ecliptic, vec_sub
from ._ephemeris_time import _BoundEphemerisDeltaT, _ephemeris_delta_t
from .julian import _tt_to_tdb_with_receipt

__all__ = [
    "PlanetocentricData",
    "PlanetocentricFrameTruth",
    "PlanetocentricRateSampling",
    "PlanetocentricReductionTruth",
    "PlanetocentricTimeBinding",
    "PlanetocentricWithTruth",
    "VALID_OBSERVER_BODIES",
    "planetocentric_at",
    "all_planetocentric_at",
    "all_planetocentric_at_with_truth",
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

@dataclass(frozen=True, slots=True)
class PlanetocentricData:
    """
    RITE: The Observer-Planet Position Vessel.

    THEOREM: Holds the geometric ecliptic position of a target body measured
    from the center of a specified observer planet, expressed in the
    true-of-date ecliptic orientation.

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
        sign, symbol, degree = sign_of(self.longitude)
        object.__setattr__(self, "sign", sign)
        object.__setattr__(self, "sign_symbol", symbol)
        object.__setattr__(self, "sign_degree", degree)

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


@dataclass(frozen=True, slots=True)
class PlanetocentricTimeBinding:
    """Epochs and the effective Delta-T policy used by the state reduction."""

    jd_ut1: float
    jd_tt: float
    jd_tdb: float
    delta_t_seconds: float
    delta_t_source_product: str
    delta_t_retarget_mode: str
    delta_t_correction_seconds: float
    delta_t_kernel_identity: str | None
    tdb_minus_tt_seconds: float


@dataclass(frozen=True, slots=True)
class PlanetocentricRateSampling:
    """One state epoch per body and two rotation epochs for its frame derivative."""

    frame_derivative_half_span_days: float
    frame_derivative_jd_tt: tuple[float, float]
    method: Literal["instantaneous_state_vector"] = "instantaneous_state_vector"
    ephemeris_state_samples_per_body: Literal[1] = 1
    ephemeris_state_timescale: Literal["TDB"] = "TDB"
    frame_derivative_method: Literal["centered_finite_difference"] = "centered_finite_difference"
    frame_derivative_timescale: Literal["TT"] = "TT"


@dataclass(frozen=True, slots=True)
class PlanetocentricFrameTruth:
    """Frame orientation and correction policy of the geometric state product."""

    source_vector_frame: Literal["ICRF_barycentric"] = "ICRF_barycentric"
    result_frame: Literal["true_ecliptic_and_equinox_of_date"] = "true_ecliptic_and_equinox_of_date"
    precession_model: Literal["IAU_2006_bias_inclusive"] = "IAU_2006_bias_inclusive"
    nutation_model: Literal["IAU_2000A"] = "IAU_2000A"
    position_mode: Literal["geometric"] = "geometric"
    light_time_applied: Literal[False] = False
    aberration_applied: Literal[False] = False
    gravitational_deflection_applied: Literal[False] = False
    topocentric_applied: Literal[False] = False


_StateEndpointKind = Literal["body_center", "planetary_system_barycenter"]


@dataclass(frozen=True, slots=True)
class PlanetocentricReductionTruth:
    """Observer and target state centers, epoch binding, rate sampling and frame."""

    center_body: str
    target_body: str
    center_naif_id: int
    target_naif_id: int
    center_kind: _StateEndpointKind
    target_kind: _StateEndpointKind
    time_binding: PlanetocentricTimeBinding
    rate_sampling: PlanetocentricRateSampling
    frame: PlanetocentricFrameTruth


@dataclass(frozen=True, slots=True)
class PlanetocentricWithTruth:
    """A planetocentric position and the receipt from the same reduction."""

    result: PlanetocentricData
    truth: PlanetocentricReductionTruth


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
    Compute the geometric ecliptic position of ``target`` measured from
    the center of ``observer``.

    Positions are expressed in the requested observer-origin frame and rotated
    into the true-of-date ecliptic orientation (precession and nutation
    applied), consistent in orientation with Moira's geocentric and
    heliocentric position products.

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

    Both vectors receive the full time-dependent transformation into the true
    ecliptic frame of date, including the rotation derivative required for the
    returned longitudinal speed.

    Light-travel time is not corrected.  For precise work (eclipses, occultations
    from another planet's perspective) the caller should apply a light-time
    iteration on top of this function.
    """
    result, _, _ = _reduce_planetocentric(observer, target, jd_ut, reader)
    return result


def _reduce_planetocentric(
    observer: str, target: str, jd_ut: float, reader,
) -> tuple[PlanetocentricData, float, _BoundEphemerisDeltaT]:
    """Reduce one geometric state and retain the clock used for both endpoints."""

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

    from .planets import (
        get_reader,
        _true_of_date_ecliptic_state,
    )

    if reader is None:
        reader = get_reader()

    delta_t = _ephemeris_delta_t(jd_ut, reader)
    jd_tt = jd_ut + delta_t.seconds / 86400.0

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
    xyz_ecl, vel_ecl = _true_of_date_ecliptic_state(xyz, vel, jd_tt)
    lon, lat, dist = icrf_to_ecliptic(xyz_ecl, 0.0)
    speed = _longitude_rate_ecl(xyz_ecl, vel_ecl, 0.0)

    result = PlanetocentricData(
        observer   = observer,
        name       = target,
        longitude  = lon,
        latitude   = lat,
        distance   = dist,
        speed      = speed,
        retrograde = (speed < 0.0),
    )
    return result, jd_tt, delta_t


def _state_endpoint(body: str) -> tuple[int, _StateEndpointKind]:
    """Describe the terminal NAIF state used for a body in the canonical routes."""

    route = EARTH_ROUTE if body == Body.EARTH else NAIF_ROUTES[body]
    naif_id = route[-1][1]
    return naif_id, "planetary_system_barycenter" if 1 <= naif_id <= 9 else "body_center"


def _planetocentric_targets(observer: str, bodies: list[str] | None) -> list[str]:
    """Resolve the batch target order and omit the observer itself."""

    if observer not in VALID_OBSERVER_BODIES:
        raise ValueError(
            f"all_planetocentric_at: {observer!r} is not a valid observer. "
            f"Choose from VALID_OBSERVER_BODIES."
        )
    if bodies is None:
        return sorted(VALID_OBSERVER_BODIES - {observer})
    return [target for target in bodies if target != observer]


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
    from .planets import get_reader

    targets = _planetocentric_targets(observer, bodies)
    if reader is None:
        reader = get_reader()

    return {target: planetocentric_at(observer, target, jd_ut, reader=reader) for target in targets}


def all_planetocentric_at_with_truth(
    observer: str,
    jd_ut: float,
    bodies: list[str] | None = None,
    reader=None,
) -> dict[str, PlanetocentricWithTruth]:
    """Return the planetocentric batch with the reduction used for each target.

    The endpoints share a geometric state epoch. The longitude rate uses the
    state velocity with the rotation derivative sampled around the frame's TT.
    The Delta-T kernel identity is present when the time policy used that
    identity to bind a declared historical tidal basis.
    """
    from .planets import _FRAME_STATE_DERIVATIVE_STEP_DAYS, get_reader

    targets = _planetocentric_targets(observer, bodies)
    if reader is None:
        reader = get_reader()
    center_naif_id, center_kind = _state_endpoint(observer)
    step = _FRAME_STATE_DERIVATIVE_STEP_DAYS

    results: dict[str, PlanetocentricWithTruth] = {}
    for target in targets:
        result, jd_tt, delta_t = _reduce_planetocentric(observer, target, jd_ut, reader)
        tdb = _tt_to_tdb_with_receipt(jd_tt)
        target_naif_id, target_kind = _state_endpoint(target)
        results[target] = PlanetocentricWithTruth(
            result=result,
            truth=PlanetocentricReductionTruth(
                center_body=result.observer,
                target_body=result.name,
                center_naif_id=center_naif_id,
                target_naif_id=target_naif_id,
                center_kind=center_kind,
                target_kind=target_kind,
                time_binding=PlanetocentricTimeBinding(
                    jd_ut1=jd_ut,
                    jd_tt=jd_tt,
                    jd_tdb=tdb.epoch_tdb,
                    delta_t_seconds=delta_t.seconds,
                    delta_t_source_product=delta_t.raw.source_product,
                    delta_t_retarget_mode=delta_t.raw.retarget_mode,
                    delta_t_correction_seconds=delta_t.correction_seconds,
                    delta_t_kernel_identity=delta_t.identity.summary_label if delta_t.identity is not None else None,
                    tdb_minus_tt_seconds=tdb.tdb_minus_tt_seconds,
                ),
                rate_sampling=PlanetocentricRateSampling(
                    frame_derivative_half_span_days=step,
                    frame_derivative_jd_tt=(jd_tt - step, jd_tt + step),
                ),
                frame=PlanetocentricFrameTruth(),
            ),
        )
    return results

