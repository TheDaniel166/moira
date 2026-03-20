"""
Moira — Planetary Node Engine
===============================

Archetype: Engine

Purpose
-------
Governs computation of heliocentric ascending nodes, perihelion longitudes,
aphelion longitudes, inclinations, eccentricities, and semi-major axes for
Mercury through Neptune, using low-order polynomial mean orbital elements.

Boundary declaration
--------------------
Owns: mean orbital element table (Meeus/JPL), polynomial evaluation,
      and the ``OrbitalNode`` result vessel.
Delegates: nothing — all computation is self-contained arithmetic over
           the J2000 epoch constant.

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required. No database access. Valid for approximately
2000 BCE to 3000 CE per the Meeus/Simon et al. element sets.

Public surface
--------------
``OrbitalNode``         — vessel for a planet's orbital node and apsides.
``planetary_node``      — compute orbital node data for a single planet.
``all_planetary_nodes`` — compute orbital nodes for all eight planets.
"""

from dataclasses import dataclass

from .constants import J2000, JULIAN_CENTURY


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
                "planet", "ascending_node", "perihelion", "aphelion",
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
