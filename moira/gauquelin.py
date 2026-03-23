"""
Moira — Gauquelin Engine
=========================

Archetype: Engine

Purpose
-------
Governs computation of Gauquelin sector positions for celestial bodies,
dividing the diurnal arc into 36 sectors based on the four mundane angles
(Rising, MC, Setting, IC) as defined in Michel Gauquelin's statistical
research tradition.

Boundary declaration
--------------------
Owns: sector computation algorithm, plus-zone classification, and the
      ``GauquelinPosition`` result vessel.
Delegates: no sub-module delegation — all computation is self-contained
           using standard spherical astronomy (hour angle, diurnal semi-arc).

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required. No database access. Requires caller to supply
apparent right ascension, declination, geographic latitude, and Local
Sidereal Time.

Public surface
--------------
``GauquelinPosition``      — vessel for a body's Gauquelin sector result.
``gauquelin_sector``       — compute sector for a single body.
``all_gauquelin_sectors``  — compute sectors for all bodies in a dict.
"""

import math
from dataclasses import dataclass

from .constants import DEG2RAD, RAD2DEG

__all__ = [
    "GauquelinPosition",
    "gauquelin_sector",
    "all_gauquelin_sectors",
]

# ---------------------------------------------------------------------------
# Sector classification
# ---------------------------------------------------------------------------

# The "plus zones" are the three sectors immediately following each of the
# four angles (ASC, MC, DSC, IC) — sectors 1–3, 10–12, 19–21, 28–30.
_PLUS_ZONE_SECTORS: frozenset[int] = frozenset(
    list(range(1, 4)) + list(range(10, 13)) + list(range(19, 22)) + list(range(28, 31))
)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class GauquelinPosition:
    """
    RITE: The Sector Vessel — a body's place in the diurnal wheel of influence.

    THEOREM: Holds the computed Gauquelin sector number (1–36), zone
    classification, and normalised diurnal position for a single celestial body.

    RITE OF PURPOSE:
        Serves the Gauquelin Engine as the canonical result vessel for sector
        computations. Without this vessel, callers would receive raw sector
        integers with no zone context, making statistical analysis and display
        impossible. It is the structured output of ``gauquelin_sector``.

    LAW OF OPERATION:
        Responsibilities:
            - Store the body name, sector number (1–36), zone label, and
              normalised diurnal position (0–360°).
        Non-responsibilities:
            - Does not compute the sector (delegated to ``gauquelin_sector``).
            - Does not validate that sector is in [1, 36].
        Dependencies:
            - Populated exclusively by ``gauquelin_sector()``.
        Structural invariants:
            - ``sector`` is always in [1, 36].
            - ``zone`` is always "Plus Zone" or "Neutral Zone".
            - ``diurnal_position`` is always in [0, 360).
        Succession stance: terminal — not designed for subclassing.

    Canon: Gauquelin, "The Cosmic Clocks" (1967);
           Ertel & Irving, "The Tenacious Mars Effect" (1996).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.gauquelin.GauquelinPosition",
        "risk": "medium",
        "api": {
            "public_methods": ["__repr__"],
            "public_attributes": ["body", "sector", "zone", "diurnal_position"]
        },
        "state": {
            "mutable": false,
            "fields": ["body", "sector", "zone", "diurnal_position"]
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
            "policy": "caller ensures valid RA/Dec/lat/LST before construction"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]
    """

    body:             str
    sector:           int
    zone:             str
    diurnal_position: float

    def __repr__(self) -> str:
        return (
            f"GauquelinPosition({self.body!r}, sector={self.sector}, "
            f"zone={self.zone!r}, diurnal={self.diurnal_position:.2f}°)"
        )


# ---------------------------------------------------------------------------
# Public API: single body
# ---------------------------------------------------------------------------

def gauquelin_sector(
    body_ra: float,
    body_dec: float,
    lat: float,
    lst: float,
    body: str = "",
) -> GauquelinPosition:
    """
    Compute the Gauquelin sector for a single body.

    Algorithm
    ---------
    1. Compute hour angle: HA = LST − RA
    2. Compute diurnal semi-arc: DSA = arccos(−tan φ · tan δ)
    3. Normalise the body's position within its diurnal arc to 0–360°
    4. Sector = ceil(diurnal_position / 10°), clamped to 1–36

    Parameters
    ----------
    body_ra  : apparent right ascension of the body (degrees)
    body_dec : apparent declination (degrees)
    lat      : geographic latitude of observer (degrees)
    lst      : Local Sidereal Time (degrees)
    body     : optional name label for the returned GauquelinPosition
    """
    # Step 1: Hour angle (positive westward, degrees)
    ha = (lst - body_ra) % 360.0

    # Step 2: Diurnal semi-arc (DSA)
    # DSA = arccos(-tan φ · tan δ), clamped to circumpolar / sub-horizon cases.
    phi = lat * DEG2RAD
    delta = body_dec * DEG2RAD
    t = -math.tan(phi) * math.tan(delta)
    if t <= -1.0:
        # Body is circumpolar — always above the horizon; use full 180° above
        dsa = 180.0
    elif t >= 1.0:
        # Body never rises — always below horizon; use 180° below
        dsa = 0.0
    else:
        dsa = math.acos(t) * RAD2DEG   # degrees, range (0, 180)

    # Step 3: Normalise position within the diurnal arc to 0–360°
    # Gauquelin's mapping (Ertel & Irving convention):
    #   HA = 0  → body at MC (upper transit) → diurnal position = 0° → sector 36
    #   HA = DSA (setting)  → sector boundary between 9 and 10
    #   HA = 180° (IC)      → diurnal position = 180° → sector 18/19 boundary
    #   HA = 360°-DSA (rising) → sector boundary between 27 and 28
    #
    # Sector 1 begins just PAST the Ascendant (body just risen, moving toward MC).
    # The diurnal arc is divided into four quadrants, each of 9 sectors:
    #   Above-horizon east  (MC to ASC): HA 0 → DSA      => sectors 36,1,2,...,9
    #   Above-horizon west  (ASC to MC going west not applicable)
    #
    # Standard algorithm: map HA to a 0–360° "diurnal position" such that
    #   sector = ceil(diurnal_position / 10), where:
    #   - HA=0   (MC)  → diurnal_position = 0   → sector 36 (wrap)
    #   - HA=DSA (DSC) → diurnal_position = 90
    #   - HA=180 (IC)  → diurnal_position = 180
    #   - HA=360-DSA (ASC) → diurnal_position = 270
    #
    # We use a piecewise linear mapping through the four quadrant boundaries.
    if dsa <= 0.0:
        dsa = 1e-6   # guard against pathological cases

    ha = ha % 360.0

    # Quadrant boundaries (in HA space)
    q1 = dsa            # setting point (DSC)
    q2 = 180.0          # IC (lower culmination)
    q3 = 360.0 - dsa    # rising point (ASC)
    q4 = 360.0          # MC again

    if ha <= q1:
        # Above horizon, east side (just past MC toward setting)
        diurnal = (ha / q1) * 90.0
    elif ha <= q2:
        # Below horizon, setting to IC
        diurnal = 90.0 + ((ha - q1) / (q2 - q1)) * 90.0
    elif ha <= q3:
        # Below horizon, IC to rising
        diurnal = 180.0 + ((ha - q2) / (q3 - q2)) * 90.0
    else:
        # Above horizon, rising toward MC
        diurnal = 270.0 + ((ha - q3) / (q4 - q3)) * 90.0

    # Step 4: sector (1–36), where sector 1 starts just after the Ascendant
    # Map diurnal_position 270° → sector 1 start, going toward 360°/0°
    # Shift so that 270° becomes 0° for the sector numbering
    shifted = (diurnal - 270.0) % 360.0
    raw_sector = math.ceil(shifted / 10.0)
    if raw_sector == 0:
        raw_sector = 1
    sector = max(1, min(36, raw_sector))

    zone = "Plus Zone" if sector in _PLUS_ZONE_SECTORS else "Neutral Zone"

    return GauquelinPosition(
        body=body,
        sector=sector,
        zone=zone,
        diurnal_position=diurnal,
    )


# ---------------------------------------------------------------------------
# Public API: all bodies
# ---------------------------------------------------------------------------

def all_gauquelin_sectors(
    planet_ra_dec: dict[str, tuple[float, float]],
    lat: float,
    lst: float,
) -> list[GauquelinPosition]:
    """
    Compute Gauquelin sectors for all bodies in the dict.

    Parameters
    ----------
    planet_ra_dec : mapping of body name → (right_ascension, declination) in degrees
    lat           : geographic latitude of observer (degrees)
    lst           : Local Sidereal Time (degrees)

    Returns
    -------
    List of GauquelinPosition, one per body, in input order.
    """
    results: list[GauquelinPosition] = []
    for body_name, (ra, dec) in planet_ra_dec.items():
        gp = gauquelin_sector(ra, dec, lat, lst, body=body_name)
        results.append(gp)
    return results
