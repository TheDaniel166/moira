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
            - ``sector`` is always in [1, n] where n is the requested resolution.
            - ``zone`` is "Plus Zone" or "Neutral Zone" when sectors=36 (the
              canonical Gauquelin system); ``None`` for custom resolutions where
              no empirical plus-zone definition exists.
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
    zone:             str | None   # None when sectors != 36 (no canonical plus-zone definition)
    diurnal_position: float

    def __repr__(self) -> str:
        zone_str = self.zone if self.zone is not None else "N/A"
        return (
            f"GauquelinPosition({self.body!r}, sector={self.sector}, "
            f"zone={zone_str!r}, diurnal={self.diurnal_position:.2f}°)"
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
    horizon_altitude: float = -0.5667,
    sectors: int = 36,
) -> GauquelinPosition:
    """
    Compute the Gauquelin sector for a single body.

    Algorithm
    ---------
    1. Compute hour angle: HA = LST − RA
    2. Compute diurnal semi-arc: DSA = arccos(t), where
       t = (sin h₀ − sin φ · sin δ) / (cos φ · cos δ)
       and h₀ is the effective horizon altitude (default −0.5667°,
       matching the standard refraction + stellar semi-diameter correction
       used throughout the library).
    3. Normalise the body's position within its diurnal arc to 0–360°
    4. Sector = ceil(diurnal_position / 10°), clamped to 1–36

    Parameters
    ----------
    body_ra          : apparent right ascension of the body (degrees)
    body_dec         : apparent declination (degrees)
    lat              : geographic latitude of observer (degrees)
    lst              : Local Sidereal Time (degrees)
    body             : optional name label for the returned GauquelinPosition
    horizon_altitude : effective horizon altitude in degrees (default −0.5667°).
                       The geometric horizon is 0°; the standard apparent
                       horizon used in rise/set timing accounts for mean
                       refraction (~34′) and gives −0.5667° for stars and
                       −0.8333° for the Sun/Moon.  Using the apparent horizon
                       here ensures that a planet classified as "just risen"
                       (sector 28) has actually cleared the visible horizon,
                       consistent with Gauquelin's observed-rising methodology.
    sectors          : number of equal divisions of the diurnal circle
                       (default 36, the canonical Gauquelin system).  Must be
                       a positive integer and a divisor of 360 for whole-degree
                       bins, though non-divisors are accepted.  At sectors=36
                       the ``zone`` field carries the canonical Plus Zone
                       classification; at any other value ``zone`` is ``None``
                       because no empirical plus-zone definition exists for
                       custom resolutions.
    """
    # Step 1: Hour angle (positive westward, degrees)
    ha = (lst - body_ra) % 360.0

    # Step 2: Diurnal semi-arc (DSA)
    # General formula for arbitrary horizon altitude h₀:
    #   cos(DSA) = (sin h₀ − sin φ · sin δ) / (cos φ · cos δ)
    # Reduces to the classic −tan φ · tan δ when h₀ = 0.
    phi   = lat      * DEG2RAD
    delta = body_dec * DEG2RAD
    sin_h0    = math.sin(horizon_altitude * DEG2RAD)
    cos_phi   = math.cos(phi)
    sin_phi   = math.sin(phi)
    cos_delta = math.cos(delta)
    sin_delta = math.sin(delta)
    denom = cos_phi * cos_delta
    if abs(denom) < 1e-10:
        t = -1.0 if sin_delta * sin_phi >= 0.0 else 1.0
    else:
        t = (sin_h0 - sin_phi * sin_delta) / denom
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

    # Step 4: sector (1–N), where sector 1 starts just after the Ascendant.
    # Shift diurnal_position so that 270° (ASC) becomes 0° for numbering.
    deg_per_sector = 360.0 / sectors
    shifted    = (diurnal - 270.0) % 360.0
    raw_sector = math.ceil(shifted / deg_per_sector)
    if raw_sector == 0:
        raw_sector = 1
    sector = max(1, min(sectors, raw_sector))

    zone: str | None = (
        ("Plus Zone" if sector in _PLUS_ZONE_SECTORS else "Neutral Zone")
        if sectors == 36 else None
    )

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
    horizon_altitude: float = -0.5667,
    sectors: int = 36,
) -> list[GauquelinPosition]:
    """
    Compute Gauquelin sectors for all bodies in the dict.

    Parameters
    ----------
    planet_ra_dec    : mapping of body name → (right_ascension, declination) in degrees
    lat              : geographic latitude of observer (degrees)
    lst              : Local Sidereal Time (degrees)
    horizon_altitude : effective horizon altitude in degrees (default −0.5667°).
                       Forwarded to :func:`gauquelin_sector`; see its docstring
                       for the physical rationale.
    sectors          : number of diurnal divisions (default 36).  Forwarded to
                       :func:`gauquelin_sector`; ``zone`` is ``None`` for any
                       value other than 36.

    Returns
    -------
    List of GauquelinPosition, one per body, in input order.
    """
    results: list[GauquelinPosition] = []
    for body_name, (ra, dec) in planet_ra_dec.items():
        gp = gauquelin_sector(ra, dec, lat, lst, body=body_name,
                              horizon_altitude=horizon_altitude,
                              sectors=sectors)
        results.append(gp)
    return results
