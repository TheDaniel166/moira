"""
Moira — Uranian Engine
=======================

Archetype: Engine

Purpose
-------
Governs position computation for the eight Hamburg School hypothetical
planets (Cupido, Hades, Zeus, Kronos, Apollon, Admetos, Vulkanus, Poseidon)
and Transpluto, using linear mean-motion ephemerides.

Boundary declaration
--------------------
Owns: Uranian body name constants, mean orbital element table, linear
      position computation, and the ``UranianPosition`` result vessel.
Delegates: sign classification to ``moira.constants.sign_of``.

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required. No database access. Pure polynomial computation
from the J2000 epoch constant.

Public surface
--------------
``UranianBody``      — string constants for all nine hypothetical body names.
``UranianPosition``  — vessel for a computed Uranian body position.
``uranian_at``       — compute position of a single Uranian body.
``all_uranian_at``   — compute positions for all nine bodies.
``list_uranian``     — list available body names.
"""


from dataclasses import dataclass, field

from .constants import J2000, sign_of


# ---------------------------------------------------------------------------
# Named constants for Uranian body identifiers
# ---------------------------------------------------------------------------

class UranianBody:
    """
    RITE: The Warden of Names — the canonical namespace for hypothetical bodies.

    THEOREM: Provides string constants for all nine Uranian and hypothetical
    body names used throughout the Uranian Engine.

    RITE OF PURPOSE:
        Serves the Uranian Engine as the authoritative name registry for
        Hamburg School hypothetical planets and Transpluto. Without this
        Warden, callers would use ad-hoc string literals that diverge across
        the codebase, breaking lookup against ``_URANIAN_ELEMENTS``.

    LAW OF OPERATION:
        Responsibilities:
            - Declare one class-level string constant per hypothetical body.
            - Expose ``ALL`` as an ordered list of all nine body name strings.
        Non-responsibilities:
            - Does not compute positions.
            - Does not validate that a name is present in the element table.
        Dependencies:
            - None. Pure namespace class with no runtime dependencies.
        Structural invariants:
            - ``ALL`` contains exactly nine entries in canonical order.
        Succession stance: terminal — not designed for subclassing.

    Canon: Witte, "Regelwerk fur Planetenbilder" (1928);
           Udo Rudolph, "ABC of Uranian Astrology" (2005).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.uranian.UranianBody",
        "risk": "low",
        "api": {
            "public_methods": [],
            "public_attributes": [
                "CUPIDO", "HADES", "ZEUS", "KRONOS", "APOLLON",
                "ADMETOS", "VULKANUS", "POSEIDON", "TRANSPLUTO", "ALL"
            ]
        },
        "state": {
            "mutable": false,
            "fields": []
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
            "policy": "no runtime failures — pure constants"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]
    """
    CUPIDO     = "Cupido"
    HADES      = "Hades"
    ZEUS       = "Zeus"
    KRONOS     = "Kronos"
    APOLLON    = "Apollon"
    ADMETOS    = "Admetos"
    VULKANUS   = "Vulkanus"
    POSEIDON   = "Poseidon"
    TRANSPLUTO = "Transpluto"
    ALL: list[str] = [
        "Cupido", "Hades", "Zeus", "Kronos", "Apollon",
        "Admetos", "Vulkanus", "Poseidon", "Transpluto",
    ]


# ---------------------------------------------------------------------------
# Orbital elements
# ---------------------------------------------------------------------------

# (longitude_at_J2000, daily_motion_degrees_per_day)
# These are mean positions in the tropical zodiac
_URANIAN_ELEMENTS: dict[str, tuple[float, float]] = {
    "Cupido":     (  4.3333,  0.04570556),   # ~8.58 yr period
    "Hades":      (163.4125,  0.02059444),   # ~19.05 yr period
    "Zeus":       ( 20.3583,  0.03269444),   # ~12.00 yr period — same period as Jupiter
    "Kronos":     (193.4792,  0.02333056),   # ~16.80 yr period
    "Apollon":    (188.2708,  0.01930556),   # ~20.30 yr period
    "Admetos":    (  1.8542,  0.01738889),   # ~22.55 yr period
    "Vulkanus":   ( 19.8917,  0.01528611),   # ~25.67 yr period
    "Poseidon":   (  3.6875,  0.01431667),   # ~27.38 yr period
    "Transpluto": (176.9500,  0.00604167),   # ~164 yr period (Landscheidt)
}


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class UranianPosition:
    """
    RITE: The Hypothetical Vessel — position of a body beyond the visible sky.

    THEOREM: Holds the computed tropical ecliptic longitude, sign data, and
    mean daily motion for a single Uranian or hypothetical body at a given JD.

    RITE OF PURPOSE:
        Serves the Uranian Engine as the canonical result vessel for all
        hypothetical body position computations. Without this vessel, callers
        would receive raw floats with no sign context or speed information,
        making downstream display and aspect work impossible.

    LAW OF OPERATION:
        Responsibilities:
            - Store the body name, tropical longitude, and mean daily speed.
            - Derive and store sign name, sign symbol, and degree within sign
              via ``__post_init__`` using ``sign_of``.
        Non-responsibilities:
            - Does not compute the position (delegated to ``uranian_at``).
            - Does not apply corrections for nutation or aberration.
        Dependencies:
            - ``sign_of`` from ``moira.constants`` called in ``__post_init__``.
        Structural invariants:
            - ``longitude`` is always in [0, 360).
            - ``sign``, ``sign_symbol``, and ``sign_degree`` are always set
              after construction.
        Succession stance: terminal — not designed for subclassing.

    Canon: Witte, "Regelwerk fur Planetenbilder" (1928).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.uranian.UranianPosition",
        "risk": "medium",
        "api": {
            "public_methods": ["__repr__"],
            "public_attributes": [
                "name", "longitude", "sign", "sign_symbol", "sign_degree", "speed"
            ]
        },
        "state": {
            "mutable": false,
            "fields": ["name", "longitude", "sign", "sign_symbol", "sign_degree", "speed"]
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
            "policy": "caller ensures longitude is finite before construction"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]
    """
    name:        str
    longitude:   float          # tropical ecliptic longitude [0, 360)
    sign:        str  = field(init=False)
    sign_symbol: str  = field(init=False)
    sign_degree: float = field(init=False)
    speed:       float = 0.0    # daily motion (degrees/day)

    def __post_init__(self) -> None:
        self.sign, self.sign_symbol, self.sign_degree = sign_of(self.longitude)

    def __repr__(self) -> str:
        deg = int(self.sign_degree)
        mins = int((self.sign_degree - deg) * 60)
        return (
            f"{self.name}: {self.sign_symbol}{self.sign} "
            f"{deg:02d}°{mins:02d}'  (lon {self.longitude:.4f}°, "
            f"speed {self.speed:+.5f}°/day)"
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def uranian_at(name: str, jd_ut: float) -> UranianPosition:
    """
    Compute the position of a Uranian hypothetical body.

    Uses a simple linear ephemeris: L(t) = L0 + n * (JD − J2000)
    where L0 is the longitude at J2000.0 and n is the mean daily motion.

    Parameters
    ----------
    name   : one of "Cupido", "Hades", "Zeus", "Kronos", "Apollon",
             "Admetos", "Vulkanus", "Poseidon", "Transpluto"
    jd_ut  : Julian Day (UT)

    Returns
    -------
    UranianPosition

    Raises
    ------
    KeyError
        If *name* is not a recognised Uranian body.
    """
    try:
        l0, n = _URANIAN_ELEMENTS[name]
    except KeyError:
        valid = ", ".join(_URANIAN_ELEMENTS)
        raise KeyError(
            f"Unknown Uranian body {name!r}. "
            f"Valid names: {valid}"
        ) from None

    dt = jd_ut - J2000
    longitude = (l0 + n * dt) % 360.0
    return UranianPosition(name=name, longitude=longitude, speed=n)


def all_uranian_at(jd_ut: float) -> dict[str, UranianPosition]:
    """Compute positions for all 9 Uranian/hypothetical bodies.

    Parameters
    ----------
    jd_ut : Julian Day (UT)

    Returns
    -------
    dict mapping body name → UranianPosition, in canonical order.
    """
    return {name: uranian_at(name, jd_ut) for name in _URANIAN_ELEMENTS}


def list_uranian() -> list[str]:
    """Return names of all available Uranian hypothetical bodies."""
    return list(_URANIAN_ELEMENTS.keys())
