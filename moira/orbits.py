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
    KeplerianElements    — typed vessel for Keplerian orbital elements
    DistanceExtremes     — typed vessel for perihelion/aphelion distances and dates
    orbital_elements_at  — compute heliocentric Keplerian elements for a body at a JD
    distance_extremes_at — find nearest perihelion and aphelion from a given JD

Import-time side effects: None
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .constants import Body
from .spk_reader import SpkReader


__all__ = [
    "KeplerianElements",
    "DistanceExtremes",
    "orbital_elements_at",
    "distance_extremes_at",
]


# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------

# GM_sun from JPL: 1.32712440018e20 m³/s², converted to km³/day²
_GM_SUN_KM3_DAY2: float = 1.32712440018e11 * 86400.0 ** 2

# IAU 2012 definition: 1 AU = 149597870.700 km exactly
_KM_PER_AU: float = 149597870.700

# IAU J2000.0 ecliptic obliquity (Seidelmann 1992 value used in DE441 frame)
_J2000_OBLIQUITY_RAD: float = math.radians(23.439291111)


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


# ===========================================================================
# Private helpers — coordinate transforms and element extraction
# ===========================================================================

def _rot_eq_to_ecl(
    x: float, y: float, z: float, eps: float
) -> tuple[float, float, float]:
    """Rotate an ICRF equatorial vector to the J2000 ecliptic frame.

    The rotation is about the x-axis by the obliquity angle ε:
        x_ecl =  x
        y_ecl =  y cos ε + z sin ε
        z_ecl = −y sin ε + z cos ε
    """
    cos_e = math.cos(eps)
    sin_e = math.sin(eps)
    return x, y * cos_e + z * sin_e, -y * sin_e + z * cos_e


def _cross3(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> tuple[float, float, float]:
    ax, ay, az = a
    bx, by, bz = b
    return (ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx)


def _dot3(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _mag3(a: tuple[float, float, float]) -> float:
    return math.sqrt(_dot3(a, a))


def _keplerian_from_state(
    r: tuple[float, float, float],
    v: tuple[float, float, float],
    gm: float,
    name: str,
    epoch_jd: float,
) -> KeplerianElements:
    """Extract Keplerian osculating elements from a heliocentric state vector.

    Parameters
    ----------
    r : heliocentric position (km, J2000 ecliptic)
    v : heliocentric velocity (km/day, J2000 ecliptic)
    gm : gravitational parameter of the central body (km³/day²)
    name : body name (stored verbatim in the result)
    epoch_jd : Julian Day at which the state was evaluated

    Returns
    -------
    KeplerianElements with all angular fields in degrees [0, 360).
    """
    rx, ry, rz = r
    r_mag = _mag3(r)
    v_mag = _mag3(v)

    # Angular momentum h = r × v
    h = _cross3(r, v)
    h_mag = _mag3(h)

    # Inclination i = arccos(h_z / |h|)
    incl_rad = math.acos(max(-1.0, min(1.0, h[2] / h_mag)))

    # Ascending-node vector N = k̂ × h = (−h_y, h_x, 0)
    nx, ny = -h[1], h[0]
    n_mag = math.sqrt(nx * nx + ny * ny)

    # Longitude of ascending node Ω
    if n_mag < 1e-10:
        omega = 0.0                            # equatorial orbit: node undefined
    else:
        omega = math.degrees(math.acos(max(-1.0, min(1.0, nx / n_mag))))
        if ny < 0.0:
            omega = 360.0 - omega

    # Eccentricity vector e = (v × h) / GM − r̂
    vxh = _cross3(v, h)
    ex = vxh[0] / gm - rx / r_mag
    ey = vxh[1] / gm - ry / r_mag
    ez = vxh[2] / gm - rz / r_mag
    ecc = math.sqrt(ex * ex + ey * ey + ez * ez)

    # Argument of perihelion ω
    if n_mag < 1e-10 or ecc < 1e-10:
        arg_peri = 0.0
    else:
        e_dot_n = ex * nx + ey * ny          # e·N  (nz = ez_proj = 0 for N)
        arg_peri = math.degrees(math.acos(max(-1.0, min(1.0, e_dot_n / (ecc * n_mag)))))
        if ez < 0.0:
            arg_peri = 360.0 - arg_peri

    # True anomaly ν
    if ecc < 1e-10:
        true_anom = 0.0                        # circular: ν undefined, use 0
    else:
        e_dot_r = ex * rx + ey * ry + ez * rz
        true_anom = math.degrees(math.acos(max(-1.0, min(1.0, e_dot_r / (ecc * r_mag)))))
        if _dot3(r, v) < 0.0:
            true_anom = 360.0 - true_anom

    # Semi-major axis from vis-viva: a = −GM / (2 · ε_orb)
    energy = 0.5 * v_mag ** 2 - gm / r_mag
    if abs(energy) < 1e-30:
        raise ValueError(
            f"Body {name!r} is on a parabolic trajectory; "
            "semi-major axis is undefined"
        )
    sma_km = -gm / (2.0 * energy)

    # Mean anomaly M from eccentric anomaly E (elliptical only)
    if ecc < 1.0:
        half_nu = math.radians(true_anom) / 2.0
        ea = 2.0 * math.atan2(
            math.sqrt(max(0.0, 1.0 - ecc)) * math.sin(half_nu),
            math.sqrt(max(0.0, 1.0 + ecc)) * math.cos(half_nu),
        )
        mean_anom = math.degrees(ea - ecc * math.sin(ea)) % 360.0
    else:
        mean_anom = 0.0                        # hyperbolic: M not defined

    # Mean motion n = √(GM / a³) and period T = 2π / n
    if sma_km > 0.0:
        mean_motion = math.degrees(math.sqrt(gm / sma_km ** 3))   # deg/day
        period      = 360.0 / mean_motion                          # days
    else:
        mean_motion = 0.0
        period      = float("inf")

    return KeplerianElements(
        name=name,
        epoch_jd=epoch_jd,
        semi_major_axis_au=sma_km / _KM_PER_AU,
        eccentricity=ecc,
        inclination_deg=math.degrees(incl_rad) % 360.0,
        lon_ascending_node_deg=omega % 360.0,
        arg_perihelion_deg=arg_peri % 360.0,
        mean_anomaly_deg=mean_anom % 360.0,
        mean_motion_deg_per_day=mean_motion,
        orbital_period_days=period,
    )


# ===========================================================================
# Public entry point
# ===========================================================================

def orbital_elements_at(
    body: str,
    jd_ut: float,
    reader: SpkReader,
) -> KeplerianElements:
    """
    Compute heliocentric osculating Keplerian orbital elements for a body.

    The elements are instantaneous (osculating) at ``jd_ut``, expressed in the
    heliocentric J2000.0 ecliptic frame.

    Parameters
    ----------
    body : str
        Body name — one of the ``Body.*`` constants (e.g. ``Body.EARTH``).
        ``Body.SUN`` and ``Body.MOON`` raise ``ValueError``.
    jd_ut : float
        Julian Date in Universal Time (UT1).
    reader : SpkReader
        An open DE441 kernel reader (e.g. from ``moira.spk_reader.get_reader()``).

    Returns
    -------
    KeplerianElements
        Heliocentric J2000.0 osculating elements at ``jd_ut``.

    Raises
    ------
    ValueError
        If ``body`` is ``Body.SUN`` (the reference center) or ``Body.MOON``
        (whose heliocentric elements are not physically meaningful in the
        osculating Keplerian sense).

    Notes
    -----
    Method
        1. Evaluate the body's and the Sun's Solar-System Barycentric (SSB)
           position and velocity from DE441 at ``jd_tt = jd_ut + ΔT/86400``.
        2. Subtract to form the heliocentric state in ICRF (equatorial J2000).
        3. Rotate to the J2000.0 ecliptic frame via the fixed obliquity
           ε₀ = 23.439291111° (IAU J2000.0 value).
        4. Apply classical Keplerian element extraction (Bate, Mueller & White
           §2.4 algorithm) using GM_sun = 1.32712440018×10²⁰ m³/s².

    Validation
        Compare against Meeus *Astronomical Algorithms* Table 31.a (J2000.0
        elements) for the eight major planets.  Tolerance: ≤ 0.01° for angular
        elements, ≤ 0.001 AU for semi-major axis.
    """
    if body == Body.SUN:
        raise ValueError(
            "Cannot compute heliocentric elements for Body.SUN — "
            "it is the reference center"
        )
    if body == Body.MOON:
        raise ValueError(
            "Heliocentric Keplerian elements are not meaningful for "
            "Body.MOON in the osculating sense; use geocentric elements instead"
        )

    from .julian import ut_to_tt as _ut_to_tt
    from .planets import _barycentric_state, _earth_barycentric_state

    jd_tt = _ut_to_tt(jd_ut)

    # Body barycentric state (km, km/day, ICRF)
    if body == Body.EARTH:
        body_pos, body_vel = _earth_barycentric_state(jd_tt, reader)
    else:
        body_pos, body_vel = _barycentric_state(body, jd_tt, reader)

    # Sun barycentric state (km, km/day, ICRF): SSB → Sun (NAIF 10)
    sun_pos, sun_vel = reader.position_and_velocity(0, 10, jd_tt)

    # Heliocentric state in ICRF
    r_icrf = (
        body_pos[0] - sun_pos[0],
        body_pos[1] - sun_pos[1],
        body_pos[2] - sun_pos[2],
    )
    v_icrf = (
        body_vel[0] - sun_vel[0],
        body_vel[1] - sun_vel[1],
        body_vel[2] - sun_vel[2],
    )

    # Rotate to J2000.0 ecliptic frame
    eps = _J2000_OBLIQUITY_RAD
    r_ecl = _rot_eq_to_ecl(*r_icrf, eps)
    v_ecl = _rot_eq_to_ecl(*v_icrf, eps)

    return _keplerian_from_state(r_ecl, v_ecl, _GM_SUN_KM3_DAY2, body, jd_ut)


def distance_extremes_at(
    body: str,
    jd_ut: float,
    reader: SpkReader,
) -> DistanceExtremes:
    """
    Find the nearest perihelion and aphelion for a body from a given JD.

    Delegates to :func:`moira.phenomena.perihelion` and
    :func:`moira.phenomena.aphelion`, which use golden-section minimisation /
    maximisation of the heliocentric distance derived from DE441.

    Parameters
    ----------
    body : str
        Body name — one of the ``Body.*`` constants.  ``Body.SUN`` raises
        ``ValueError``; ``Body.MOON`` is not meaningful for this surface
        and also raises.
    jd_ut : float
        Search start in Julian Date (UT1).  The function finds the *next*
        perihelion and *next* aphelion after this date.
    reader : SpkReader
        An open DE441 kernel reader.

    Returns
    -------
    DistanceExtremes
        Perihelion and aphelion JDs (UT1) and heliocentric distances (AU).
        The two passages are the nearest ones forward from ``jd_ut``;
        they may come in either order (inner planets often reach aphelion
        before perihelion within the same half-orbit).

    Raises
    ------
    ValueError
        If ``body`` is ``Body.SUN`` or ``Body.MOON``, or if no perihelion or
        aphelion is found within 1.5 × the body's orbital period.

    Notes
    -----
    The search window is 1.5 × the orbital period, consistent with
    :func:`moira.phenomena.perihelion` and :func:`moira.phenomena.aphelion`.
    For outer planets (Saturn, Uranus, Neptune) this can take a few tens of
    milliseconds; for inner planets it is sub-millisecond.
    """
    if body == Body.SUN:
        raise ValueError("Body.SUN has no heliocentric perihelion or aphelion")
    if body == Body.MOON:
        raise ValueError(
            "Heliocentric distance extremes are not meaningful for Body.MOON"
        )

    from .phenomena import perihelion as _peri, aphelion as _aphe

    peri_event = _peri(body, jd_ut, reader)
    aphe_event = _aphe(body, jd_ut, reader)

    if peri_event is None:
        raise ValueError(
            f"No perihelion found for {body!r} within 1.5 orbital periods "
            f"of JD {jd_ut:.1f}"
        )
    if aphe_event is None:
        raise ValueError(
            f"No aphelion found for {body!r} within 1.5 orbital periods "
            f"of JD {jd_ut:.1f}"
        )

    return DistanceExtremes(
        name=body,
        perihelion_jd=peri_event.jd_ut,
        perihelion_distance_au=peri_event.value,
        aphelion_jd=aphe_event.jd_ut,
        aphelion_distance_au=aphe_event.value,
    )
