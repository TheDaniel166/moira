"""
Midpoint Engine — moira/midpoints.py

Archetype: Engine
Purpose: Computes shorter-arc midpoints between all pairs of chart bodies,
         supports midpoint-tree searches on both the 360° wheel and the
         Hamburg 90° dial, and provides the Midpoint and MidpointsService
         types.

Boundary declaration:
    Owns: the shorter-arc midpoint formula, the 90° dial projection, the
          midpoint-tree search, and the Midpoint and MidpointsService types.
    Delegates: sign derivation to moira.constants.sign_of.

Import-time side effects: None

External dependency assumptions:
    - moira.constants.sign_of(longitude) returns (sign_name, symbol, degree).

Public surface / exports:
    Midpoint              — result dataclass for a single midpoint
    MidpointsService      — service class for computing midpoints
    CLASSIC_7 / MODERN_3 / MODERN_10 / EXTENDED — planet set constants
    calculate_midpoints() — module-level convenience wrapper
    midpoints_to_point()  — find midpoints within orb of a target longitude
    to_dial_90()          — project longitude onto the 90° dial
    dial_90_midpoints()   — midpoints sorted by 90° dial position
    midpoint_tree()       — midpoints equidistant from a focus on chosen dial
"""

from dataclasses import dataclass, field
from itertools import combinations

from .constants import sign_of

__all__ = [
    "Midpoint",
    "MidpointsService",
    "CLASSIC_7",
    "MODERN_3",
    "MODERN_10",
    "EXTENDED",
    "calculate_midpoints",
    "midpoints_to_point",
    "to_dial_90",
    "dial_90_midpoints",
    "midpoint_tree",
]

# ---------------------------------------------------------------------------
# Planet sets
# ---------------------------------------------------------------------------

CLASSIC_7: set[str] = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"}
MODERN_3:  set[str] = {"Uranus", "Neptune", "Pluto"}
MODERN_10: set[str] = CLASSIC_7 | MODERN_3
EXTENDED:  set[str] = MODERN_10 | {"True Node", "North Node", "Chiron", "Asc", "MC"}


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class Midpoint:
    """
    RITE: The Hidden Axis — the invisible point equidistant between two
          planets, where their combined energies converge in the zodiac.

    THEOREM: Immutable record of the shorter-arc midpoint between two chart
             bodies, storing both planet names, the midpoint longitude, and
             the derived sign/degree fields.

    RITE OF PURPOSE:
        Midpoint is the result vessel of MidpointsService.  It labels the
        midpoint longitude with the names of both contributing bodies so
        that callers can identify which pair produced each point without
        maintaining a parallel index.  Without this vessel, midpoint results
        would be bare floats with no association to their source planets.

    LAW OF OPERATION:
        Responsibilities:
            - Store planet_a, planet_b, and longitude.
            - Derive sign, sign_symbol, and sign_degree via __post_init__.
            - Render a compact repr showing the pair and sign position.
        Non-responsibilities:
            - Does not compute the midpoint; that is MidpointsService's role.
            - Does not validate that planet_a != planet_b.
            - Does not perform any I/O or kernel access.
        Dependencies:
            - moira.constants.sign_of for sign derivation.
        Structural invariants:
            - longitude is in [0, 360).
            - sign, sign_symbol, sign_degree are consistent with longitude.

    Canon: Reinhold Ebertin, The Combination of Stellar Influences (1940)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.midpoints.Midpoint",
        "risk": "low",
        "api": {"frozen": ["planet_a", "planet_b", "longitude"], "internal": ["sign", "sign_symbol", "sign_degree"]},
        "state": {"mutable": false, "owners": []},
        "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
        "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
        "failures": {"policy": "none"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    planet_a:    str
    planet_b:    str
    longitude:   float
    sign:        str   = field(init=False)
    sign_symbol: str   = field(init=False)
    sign_degree: float = field(init=False)

    def __post_init__(self) -> None:
        self.sign, self.sign_symbol, self.sign_degree = sign_of(self.longitude)

    def __repr__(self) -> str:
        return (f"{self.planet_a}/{self.planet_b}: "
                f"{self.longitude:.4f}  {self.sign} {self.sign_degree:.2f}")


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------

class MidpointsService:
    """
    RITE: The Axis Weaver — the Engine that enumerates every pair of chart
          bodies, computes their shorter-arc midpoint, and serves the full
          midpoint table or targeted searches on any dial.

    THEOREM: Governs the computation of all shorter-arc midpoints for a
             chosen planet set, and provides midpoint-to-point proximity
             searches on both the 360° wheel and the Hamburg 90° dial.

    RITE OF PURPOSE:
        MidpointsService is the computational core of the Midpoint Engine.
        It accepts a dict of natal longitudes, filters to the requested
        planet set, enumerates all pairs via itertools.combinations, and
        returns a sorted list of Midpoint records.  Without this Engine,
        callers would need to re-implement the shorter-arc formula and
        pair enumeration at every call site.

    LAW OF OPERATION:
        Responsibilities:
            - Filter planet_longitudes to the requested planet set.
            - Compute shorter-arc midpoints for all pairs.
            - Return results sorted by longitude.
            - Provide midpoints_to_point() for proximity searches.
        Non-responsibilities:
            - Does not validate that planet names are known bodies.
            - Does not perform any I/O or kernel access.
        Dependencies:
            - moira.constants.sign_of for sign derivation in Midpoint.
        Failure behavior:
            - Unknown planet_set strings default to CLASSIC_7 silently.

    Canon: Reinhold Ebertin, The Combination of Stellar Influences (1940);
           Alfred Witte, Rules for Planetary Pictures (Hamburg School)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.midpoints.MidpointsService",
        "risk": "low",
        "api": {"frozen": ["calculate_midpoints", "midpoints_to_point"], "internal": []},
        "state": {"mutable": false, "owners": []},
        "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
        "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
        "failures": {"policy": "silent_default"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    def calculate_midpoints(
        self,
        planet_longitudes: dict[str, float],
        planet_set: str = "classic",
    ) -> list[Midpoint]:
        """
        Calculate midpoints between all pairs in the chosen set.

        Parameters
        ----------
        planet_longitudes : dict of body name → longitude (degrees)
        planet_set        : 'classic' (7), 'modern' (10), or 'extended'

        Returns
        -------
        List of Midpoint sorted by longitude
        """
        allowed = {"classic": CLASSIC_7, "modern": MODERN_10,
                   "extended": EXTENDED}.get(planet_set, CLASSIC_7)

        # Normalise to title case and filter
        available: dict[str, float] = {}
        for name, lon in planet_longitudes.items():
            n = name.strip().title()
            if n in allowed:
                available[n] = lon

        midpoints = [
            Midpoint(
                planet_a=a,
                planet_b=b,
                longitude=_midpoint(lon_a, lon_b),
            )
            for (a, lon_a), (b, lon_b) in combinations(available.items(), 2)
        ]
        midpoints.sort(key=lambda m: m.longitude)
        return midpoints

    def midpoints_to_point(
        self,
        target: float,
        planet_longitudes: dict[str, float],
        orb: float = 1.5,
        planet_set: str = "classic",
    ) -> list[tuple[Midpoint, float]]:
        """
        Find midpoints that conjoin a target longitude within an orb.

        Returns
        -------
        List of (Midpoint, orb_value) tuples sorted by |orb|
        """
        all_mps = self.calculate_midpoints(planet_longitudes, planet_set)
        hits: list[tuple[Midpoint, float]] = []
        for mp in all_mps:
            diff = abs((mp.longitude - target + 180) % 360 - 180)
            if diff <= orb:
                hits.append((mp, diff))
        hits.sort(key=lambda x: x[1])
        return hits


# ---------------------------------------------------------------------------
# Helpers and module-level interface
# ---------------------------------------------------------------------------

def _midpoint(lon_a: float, lon_b: float) -> float:
    """Shorter-arc midpoint."""
    a, b = lon_a % 360, lon_b % 360
    diff = abs(a - b)
    if diff <= 180:
        return (a + b) / 2 % 360
    return ((a + b) / 2 + 180) % 360


_service = MidpointsService()


def calculate_midpoints(
    planet_longitudes: dict[str, float],
    planet_set: str = "classic",
) -> list[Midpoint]:
    """
    Compute all midpoints for the given planet set.

    Parameters
    ----------
    planet_longitudes : dict of body name → longitude (degrees)
    planet_set        : 'classic', 'modern', or 'extended'
    """
    return _service.calculate_midpoints(planet_longitudes, planet_set)


def midpoints_to_point(
    target: float,
    planet_longitudes: dict[str, float],
    orb: float = 1.5,
    planet_set: str = "classic",
) -> list[tuple[Midpoint, float]]:
    """Find midpoints within orb of a target longitude."""
    return _service.midpoints_to_point(target, planet_longitudes, orb, planet_set)


# ---------------------------------------------------------------------------
# Hamburg School: 90° dial
# ---------------------------------------------------------------------------

def to_dial_90(longitude: float) -> float:
    """
    Project a 360° ecliptic longitude onto the 90° dial.

    The 90° dial (Hamburg / Uranian School) compresses the zodiac by a factor
    of 4, folding Aries, Cancer, Libra, and Capricorn onto the same 0° point.
    This causes midpoints that are invisible on a 360° wheel to cluster
    visibly on the dial.

    Formula: dial_position = (longitude * 4) mod 90
    """
    return (longitude * 4.0) % 90.0


def dial_90_midpoints(
    planet_longitudes: dict[str, float],
    planet_set: str = "classic",
) -> list[Midpoint]:
    """
    Return all midpoints sorted by their position on the 90° dial.

    Identical to calculate_midpoints() in content, but sorted by
    ``to_dial_90(midpoint.longitude)`` rather than raw longitude.
    This makes it easy to scan for tight clusters on the Hamburg dial.

    Parameters
    ----------
    planet_longitudes : dict of body name → longitude (degrees)
    planet_set        : 'classic', 'modern', or 'extended'

    Returns
    -------
    List of Midpoint sorted by 90° dial position (0–90°)
    """
    mps = calculate_midpoints(planet_longitudes, planet_set)
    mps.sort(key=lambda m: to_dial_90(m.longitude))
    return mps


def midpoint_tree(
    focus: float,
    planet_longitudes: dict[str, float],
    orb: float = 2.0,
    planet_set: str = "classic",
    dial: int = 360,
) -> list[tuple[Midpoint, float]]:
    """
    Find all midpoints equidistant from a focus point on the chosen dial.

    A "midpoint tree" (or "midpoint direct/indirect") lists every planetary
    midpoint that falls within *orb* of the focus on the specified dial.
    On the 90° dial this exposes harmonic midpoints that are exact multiples
    of 90° away on the full wheel.

    Parameters
    ----------
    focus  : target longitude (degrees, 360° wheel coordinates)
    planet_longitudes : dict of body name → longitude (degrees)
    orb    : maximum orb in degrees, measured on the chosen dial
    planet_set : 'classic', 'modern', or 'extended'
    dial   : 360 (standard wheel) or 90 (Hamburg dial)

    Returns
    -------
    List of (Midpoint, orb_value) sorted by absolute orb (tightest first)

    Notes
    -----
    On the 90° dial both the focus and each midpoint longitude are projected
    via ``to_dial_90()`` before the orb is measured.  The orb itself is the
    shortest arc on the 90° circle (i.e. min(d, 90-d) where d is the raw
    dial difference).
    """
    if dial not in (360, 90):
        raise ValueError(f"dial must be 360 or 90, got {dial!r}")

    all_mps = calculate_midpoints(planet_longitudes, planet_set)
    hits: list[tuple[Midpoint, float]] = []

    if dial == 360:
        # Standard: shortest arc on the 360° wheel
        focus_pos = focus % 360.0
        for mp in all_mps:
            diff = abs((mp.longitude - focus_pos + 180.0) % 360.0 - 180.0)
            if diff <= orb:
                hits.append((mp, diff))
    else:
        # 90° dial: project both focus and midpoint, then measure shortest arc
        # on the 90° circle (wrap at 90°, so max arc = 45°)
        focus_dial = to_dial_90(focus)
        for mp in all_mps:
            mp_dial = to_dial_90(mp.longitude)
            raw_diff = abs(mp_dial - focus_dial)
            diff = min(raw_diff, 90.0 - raw_diff)
            if diff <= orb:
                hits.append((mp, diff))

    hits.sort(key=lambda x: x[1])
    return hits
