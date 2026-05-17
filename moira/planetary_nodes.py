"""
Moira — Planetary Node Engine
===============================

Archetype: Engine

Purpose
-------
Governs computation of heliocentric ascending nodes, perihelion longitudes,
aphelion longitudes, inclinations, eccentricities, and semi-major axes for
any body present in the loaded SPK kernel.

Two computational paths are provided:

``planetary_node`` / ``all_planetary_nodes``
    Mean orbital elements from Meeus/Simon et al. polynomial table.
    Fast, kernel-free, Mercury–Neptune only.  Gives the slowly-drifting
    mean node; accurate to a few arcminutes over millennia.

``geometric_node``
    Osculating node derived from DE441 state vectors via the
    eccentricity-vector / angular-momentum method.  Generalises to any
    body present in the loaded SPK kernel (classical planets, Chiron,
    asteroids, TNOs).  Requires a kernel.

Boundary declaration
--------------------
Owns: mean orbital element table (Meeus/JPL), polynomial evaluation,
      geometric node computation from DE441 state vectors, and the
      ``OrbitalNode`` result vessel.
Delegates: kernel I/O to moira.spk_reader; time conversion to
           moira.julian; precession/nutation matrices to
           moira.coordinates; obliquity to moira.obliquity;
           barycentric state vectors to moira.planets._barycentric_state.

Import-time side effects: None

External dependency assumptions
--------------------------------
``geometric_node`` requires an SPK kernel configured via
``moira.spk_reader``.  ``planetary_node`` / ``all_planetary_nodes``
are kernel-free.  Valid for approximately 2000 BCE to 3000 CE per
the Meeus/Simon et al. element sets.

Public surface
--------------
``OrbitalNode``         — vessel for a planet's orbital node and apsides.
``planetary_node``      — mean-element node for a named planet.
``all_planetary_nodes`` — mean-element nodes for all eight planets.
``geometric_node``      — osculating node from DE441, any SPK body.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .constants import J2000, JULIAN_CENTURY, DEG2RAD, RAD2DEG, Body
from .julian import ut_to_tt, decimal_year
from .obliquity import mean_obliquity, nutation
from .coordinates import (
    vec_sub, mat_vec_mul,
    precession_matrix_equatorial, nutation_matrix_equatorial,
)
from .planets import _barycentric_state, approx_year as _approx_year
from .spk_reader import get_reader, SpkReader

__all__ = [
    "OrbitalNode",
    "planetary_node",
    "all_planetary_nodes",
    "geometric_node",
]

# ---------------------------------------------------------------------------
# Physical constants
# ---------------------------------------------------------------------------

_GM_SUN    = 132_712_440_018.0   # km³/s²  — DE441 / TDB-compatible
_KM_PER_AU = 149_597_870.7       # km per AU (IAU 2012)

# ---------------------------------------------------------------------------
# Mean orbital elements
# ---------------------------------------------------------------------------

# Mean orbital elements: (L0, L1, a0, a1, e0, e1, i0, i1, Ω0, Ω1, ω0, ω1)
# L = mean longitude (degrees), a = semi-major axis (AU),
# e = eccentricity, i = inclination (degrees),
# Ω = longitude of ascending node (degrees),
# ω = argument of perihelion (degrees), all at J2000.0
# Rates are per Julian century (T).

_ELEMENTS: dict[str, dict[str, tuple[float, float]]] = {
    "Mercury": {"L": (252.25032350,  149472.67411175), "a": (0.38709927, 0.00000037),
                "e": (0.20563593,  0.00001906), "i": (7.00497902, -0.00594749),
                "Omega": (48.33076593, -0.12534081), "omega": (77.45779628, 0.16047689)},
    "Venus":   {"L": (181.97909950,   58517.81538729), "a": (0.72333566, 0.00000390),
                "e": (0.00677672, -0.00004107), "i": (3.39467605, -0.00078890),
                "Omega": (76.67984255, -0.27769418), "omega": (131.60246718, 0.00268329)},
    "Earth":   {"L": (100.46457166,   35999.37244981), "a": (1.00000261, 0.00000562),
                "e": (0.01671123, -0.00004392), "i": (-0.00001531, -0.01294668),
                "Omega": (0.0, 0.0), "omega": (102.93768193, 0.32327364)},
    "Mars":    {"L": (355.44656122,   19140.30268499), "a": (1.52371034, 0.00001847),
                "e": (0.09339410,  0.00007882), "i": (1.84969142, -0.00813131),
                "Omega": (49.55953891, -0.29257343), "omega": (336.05637041, 0.44441088)},
    "Jupiter": {"L": (34.39644051,    3034.74612775), "a": (5.20288700,-0.00011607),
                "e": (0.04838624, -0.00013253), "i": (1.30439695, -0.00183714),
                "Omega": (100.47390909,  0.20469106), "omega": (14.72847983, 0.21252668)},
    "Saturn":  {"L": (49.95424423,    1222.49362201), "a": (9.53667594,-0.00125060),
                "e": (0.05386179, -0.00050991), "i": (2.48599187,  0.00193609),
                "Omega": (113.66242448, -0.28867794), "omega": (92.59887831, -0.41897216)},
    "Uranus":  {"L": (313.23810451,    428.48202785), "a": (19.18916464,-0.00196176),
                "e": (0.04725744, -0.00004397), "i": (0.77263783, -0.00242939),
                "Omega": (74.01692503,  0.04240589), "omega": (170.95427630, 0.40805281)},
    "Neptune": {"L": (304.87997031,    218.45945325), "a": (30.06992276, 0.00026291),
                "e": (0.00859048,  0.00005105), "i": (1.77004347,  0.00035372),
                "Omega": (131.78422574, -0.00508664), "omega": (44.96476227, -0.32241464)},
}


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class OrbitalNode:
    """
    RITE: The Orbital Vessel — a planet's node, apsides, and orbital elements.

    THEOREM: Holds the heliocentric ascending node longitude, perihelion
    longitude, aphelion longitude, inclination, eccentricity, and semi-major
    axis for a single planet at a given Julian Day.

    RITE OF PURPOSE:
        Serves the Planetary Node Engine as the canonical result vessel for
        orbital element computations. Without this vessel, callers would
        receive scattered floats with no structural link between the node,
        apsides, and orbital shape parameters, making traditional astrology
        node work and orbital mechanics queries impossible.

    LAW OF OPERATION:
        Responsibilities:
            - Store planet name, ascending node longitude, perihelion and
              aphelion longitudes, inclination, eccentricity, and semi-major
              axis.
        Non-responsibilities:
            - Does not compute orbital elements (delegated to
              ``planetary_node``).
            - Does not apply perturbations beyond the polynomial mean elements.
        Dependencies:
            - Populated exclusively by ``planetary_node()``.
        Structural invariants:
            - ``ascending_node``, ``perihelion``, ``aphelion`` are always
              in [0, 360).
            - ``descending_node`` (property) is ``(ascending_node + 180) % 360``.
            - ``aphelion`` is always ``(perihelion + 180) % 360``.
        Succession stance: terminal — not designed for subclassing.

    Canon: Meeus, "Astronomical Algorithms" Ch. 31, Table 31.a;
           Simon et al. (1994), secular orbital elements.

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.planetary_nodes.OrbitalNode",
        "risk": "medium",
        "api": {
            "public_methods": ["__repr__"],
            "public_attributes": [
                "planet", "ascending_node", "descending_node", "perihelion", "aphelion",
                "inclination", "eccentricity", "semi_major_axis"
            ]
        },
        "state": {
            "mutable": false,
            "fields": [
                "planet", "ascending_node", "perihelion", "aphelion",
                "inclination", "eccentricity", "semi_major_axis"
            ]
        },
        "effects": {
            "io": [],
            "signals_emitted": [],
            "db_writes": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": [],
            "policy": "caller ensures valid planet name and finite JD"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]
    """
    planet:             str
    ascending_node:     float   # ecliptic longitude of ascending node (degrees)
    perihelion:         float   # ecliptic longitude of perihelion = Ω + ω (degrees)
    aphelion:           float   # perihelion + 180° (degrees)
    inclination:        float   # orbital inclination (degrees)
    eccentricity:       float   # orbital eccentricity
    semi_major_axis:    float   # AU

    @property
    def descending_node(self) -> float:
        """Ecliptic longitude of the descending node: ☊ + 180°, degrees [0, 360)."""
        return (self.ascending_node + 180.0) % 360.0

    def __repr__(self) -> str:
        return (
            f"OrbitalNode({self.planet!r}  ☊={self.ascending_node:.4f}°  "
            f"♇={self.perihelion:.4f}°  i={self.inclination:.4f}°  "
            f"e={self.eccentricity:.6f}  a={self.semi_major_axis:.6f} AU)"
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def planetary_node(planet: str, jd: float) -> OrbitalNode:
    """
    Compute the orbital node and apsides of a planet for a given JD.

    Parameters
    ----------
    planet : planet name (Mercury through Neptune, or Earth)
    jd     : Julian Day (TT or UT — difference negligible for these slow quantities)

    Returns
    -------
    OrbitalNode
    """
    # Handle case-insensitive lookup
    matched = None
    for k in _ELEMENTS:
        if k.lower() == planet.lower():
            matched = k
            break
    if matched is None:
        raise ValueError(
            f"Unknown planet {planet!r}. "
            f"Valid names: {list(_ELEMENTS.keys())}"
        )

    elems = _ELEMENTS[matched]
    T = (jd - J2000) / JULIAN_CENTURY

    def _eval(key: str) -> float:
        c0, c1 = elems[key]
        return c0 + c1 * T

    ascending_node  = _eval("Omega") % 360.0
    # longitude of perihelion = longitude of ascending node + argument of perihelion
    # In Meeus Table 31.a, omega IS already the longitude of perihelion (Ω + ω combined)
    perihelion_lon  = _eval("omega") % 360.0
    aphelion_lon    = (perihelion_lon + 180.0) % 360.0
    inclination     = _eval("i")
    eccentricity    = _eval("e")
    semi_major_axis = _eval("a")

    return OrbitalNode(
        planet=matched,
        ascending_node=ascending_node,
        perihelion=perihelion_lon,
        aphelion=aphelion_lon,
        inclination=inclination,
        eccentricity=eccentricity,
        semi_major_axis=semi_major_axis,
    )


def all_planetary_nodes(jd: float) -> dict[str, OrbitalNode]:
    """Compute orbital nodes for all planets."""
    return {planet: planetary_node(planet, jd) for planet in _ELEMENTS}


# ---------------------------------------------------------------------------
# Geometric (osculating) node — DE441 state-vector method
# ---------------------------------------------------------------------------

def geometric_node(
    body: str,
    jd_ut: float,
    reader: SpkReader | None = None,
) -> OrbitalNode:
    """
    Compute the osculating heliocentric ascending node and orbital elements
    of *body* at *jd_ut* from DE441 state vectors.

    Method: derives the instantaneous orbital plane from the heliocentric
    angular momentum vector h = r × v, then intersects it with the ecliptic
    to obtain the ascending node direction.  The eccentricity vector
    e = (v × h)/μ − r̂ gives perihelion longitude and eccentricity.
    Inclination follows from the angle between h and the ecliptic pole.
    Semi-major axis is computed from the vis-viva specific orbital energy.

    This is the same eccentricity-vector geometry used by true_lilith() for
    the Moon's apogee, applied heliocentrically with μ = GM_Sun.

    Generalises to any body present in the loaded SPK kernel: classical
    planets, Pluto, Chiron (with an appropriate kernel), asteroids, TNOs.
    For the classical 8 planets, planetary_node() gives the mean node
    without requiring a kernel; use this function when the osculating node
    is required or for bodies outside the mean-element table.

    Parameters
    ----------
    body : Body.* constant or any body name present in NAIF_ROUTES.
        Body.SUN and Body.MOON are rejected (no meaningful heliocentric
        node in this frame).
    jd_ut : Julian Day in Universal Time (UT1).
    reader : open SpkReader; uses the module-level singleton if None.

    Returns
    -------
    OrbitalNode
        ascending_node, perihelion, aphelion : tropical ecliptic longitudes
            in degrees [0, 360).
        inclination, eccentricity, semi_major_axis : osculating orbital
            elements at epoch.

    Raises
    ------
    ValueError
        If body is Body.SUN or Body.MOON.
    KeyError
        If body is not present in NAIF_ROUTES (e.g. Body.CHIRON without
        a loaded Chiron kernel).
    FileNotFoundError
        If no planetary kernel is configured and reader is None.
    """
    if body in (Body.SUN, Body.MOON):
        raise ValueError(
            f"geometric_node: {body!r} does not have a meaningful "
            "heliocentric node in this frame."
        )
    if reader is None:
        reader = get_reader()

    year, month, *_ = _approx_year(jd_ut)
    jd_tt = ut_to_tt(jd_ut, decimal_year(year, month))

    # True obliquity for tropical frame conversion
    _, deps_deg = nutation(jd_tt)
    eps = (mean_obliquity(jd_tt) + deps_deg) * DEG2RAD

    # Heliocentric state vectors in ICRF (km, km/day)
    body_pos, body_vel_d = _barycentric_state(body, jd_tt, reader)
    sun_pos,  sun_vel_d  = reader.position_and_velocity(0, 10, jd_tt)
    r = vec_sub(body_pos, sun_pos)
    v_d = vec_sub(body_vel_d, sun_vel_d)
    v = (v_d[0] / 86400.0, v_d[1] / 86400.0, v_d[2] / 86400.0)  # km/s

    # Specific angular momentum h = r × v
    hx = r[1]*v[2] - r[2]*v[1]
    hy = r[2]*v[0] - r[0]*v[2]
    hz = r[0]*v[1] - r[1]*v[0]
    h_mag = math.sqrt(hx*hx + hy*hy + hz*hz)

    # Ascending node direction: N = ecliptic_z × h
    # ecliptic_z in ICRF ≈ (0, −sin ε, cos ε)
    # Cross product components:
    #   nx = (−sin ε)(hz) − (cos ε)(hy)
    #   ny = (cos ε)(hx)
    #   nz = (sin ε)(hx)
    sin_eps = math.sin(eps)
    cos_eps = math.cos(eps)
    nx = -sin_eps * hz - cos_eps * hy
    ny =  cos_eps * hx
    nz =  sin_eps * hx

    # Rotate ascending-node vector through P then N (J2000 → true-of-date)
    P = precession_matrix_equatorial(jd_tt)
    N_mat = nutation_matrix_equatorial(jd_tt)
    n_prec = mat_vec_mul(P, (nx, ny, nz))
    n_true = mat_vec_mul(N_mat, n_prec)

    # Extract tropical ecliptic longitude of ascending node
    aye = n_true[1] * cos_eps + n_true[2] * sin_eps
    axe = n_true[0]
    ascending_node_lon = math.atan2(aye, axe) * RAD2DEG % 360.0

    # Eccentricity vector e = (v × h)/μ − r̂  (points to perihelion)
    r_mag = math.sqrt(r[0]*r[0] + r[1]*r[1] + r[2]*r[2])
    vhx = v[1]*hz - v[2]*hy
    vhy = v[2]*hx - v[0]*hz
    vhz = v[0]*hy - v[1]*hx
    ex = vhx / _GM_SUN - r[0] / r_mag
    ey = vhy / _GM_SUN - r[1] / r_mag
    ez = vhz / _GM_SUN - r[2] / r_mag
    eccentricity = math.sqrt(ex*ex + ey*ey + ez*ez)

    # Rotate eccentricity vector → tropical longitude of perihelion
    e_prec = mat_vec_mul(P, (ex, ey, ez))
    e_true = mat_vec_mul(N_mat, e_prec)
    peri_y = e_true[1] * cos_eps + e_true[2] * sin_eps
    peri_x = e_true[0]
    perihelion_lon = math.atan2(peri_y, peri_x) * RAD2DEG % 360.0
    aphelion_lon   = (perihelion_lon + 180.0) % 360.0

    # Inclination: angle between h and ecliptic pole
    h_z_ecl = -hy * sin_eps + hz * cos_eps
    inclination = math.acos(max(-1.0, min(1.0, h_z_ecl / h_mag))) * RAD2DEG

    # Semi-major axis from specific orbital energy: a = −μ / (2ε)
    v_sq  = v[0]*v[0] + v[1]*v[1] + v[2]*v[2]
    energy = v_sq / 2.0 - _GM_SUN / r_mag
    semi_major_axis = (-_GM_SUN / (2.0 * energy)) / _KM_PER_AU

    return OrbitalNode(
        planet=body,
        ascending_node=ascending_node_lon,
        perihelion=perihelion_lon,
        aphelion=aphelion_lon,
        inclination=inclination,
        eccentricity=eccentricity,
        semi_major_axis=semi_major_axis,
    )
