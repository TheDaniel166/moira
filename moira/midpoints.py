"""
Midpoint Engine — moira/midpoints.py

Archetype: Engine
Purpose: Computes shorter-arc midpoints between all pairs of chart bodies,
         supports midpoint-tree searches on the full Hamburg-school dial
         family (360°, 90°, 45°, 22.5°), antiscia/contra-antiscia
         reflections, planetary picture enumeration, midpoint weighting
         analysis, dynamic activation by transit or direction, and spatial
         cluster detection on any dial.

Boundary declaration:
    Owns: shorter-arc midpoint formula, generalized dial projections
          (harmonic 1–16), antiscia/contra-antiscia reflections, planetary
          picture enumeration, midpoint weighting analysis (MWA), transit
          and solar-arc activation, midpoint cluster detection, and all
          result types.
    Delegates: sign derivation to moira.constants.sign_of.

Import-time side effects: None

External dependency assumptions:
    - moira.constants.sign_of(longitude) returns (sign_name, symbol, degree).

Public surface / exports:
    # Result types
    Midpoint             — result dataclass for a single midpoint
    PlanetaryPicture     — a symmetrical equation A = B/C on a chosen dial
    MidpointWeight       — a planet's activation score in the midpoint web
    MidpointCluster      — a spatial concentration of midpoints on the dial

    # Service class
    MidpointsService     — service class for computing midpoints

    # Planet sets
    CLASSIC_7 / MODERN_3 / MODERN_10 / EXTENDED

    # Core computation
    calculate_midpoints()  — all pairs for a planet set
    midpoints_to_point()   — midpoints within orb of a target longitude

    # Dial projections
    to_dial()              — project longitude onto any harmonic dial
    to_dial_90()           — project onto 90° Hamburg dial (harmonic 4)
    to_dial_45()           — project onto 45° dial (harmonic 8)
    to_dial_22_5()         — project onto 22.5° dial (harmonic 16)
    dial_90_midpoints()    — midpoints sorted by 90° dial position
    dial_45_midpoints()    — midpoints sorted by 45° dial position
    dial_22_5_midpoints()  — midpoints sorted by 22.5° dial position
    midpoint_tree()        — midpoints equidistant from a focus (any dial)

    # Antiscia
    antiscion()            — reflection across the Cancer–Capricorn solstice axis
    contra_antiscion()     — reflection across the Aries–Libra equinox axis

    # Advanced analysis
    planetary_pictures()   — all A=B/C equations within orb on a chosen dial
    midpoint_weighting()   — planet activation scores (Munkasey MWA)
    activated_midpoints()  — natal midpoints activated by a transit or direction
    midpoint_clusters()    — spatial midpoint hotspots on the dial
"""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations

from .constants import sign_of

__all__ = [
    # Result types
    "Midpoint",
    "PlanetaryPicture",
    "MidpointWeight",
    "MidpointCluster",
    # Service class
    "MidpointsService",
    # Planet sets
    "CLASSIC_7",
    "MODERN_3",
    "MODERN_10",
    "EXTENDED",
    # Core computation
    "calculate_midpoints",
    "midpoints_to_point",
    # Dial projections
    "to_dial",
    "to_dial_90",
    "to_dial_45",
    "to_dial_22_5",
    "dial_90_midpoints",
    "dial_45_midpoints",
    "dial_22_5_midpoints",
    "midpoint_tree",
    # Antiscia
    "antiscion",
    "contra_antiscion",
    # Advanced analysis
    "planetary_pictures",
    "midpoint_weighting",
    "activated_midpoints",
    "midpoint_clusters",
]


# ---------------------------------------------------------------------------
# Planet sets
# ---------------------------------------------------------------------------

CLASSIC_7: set[str] = {"Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"}
MODERN_3:  set[str] = {"Uranus", "Neptune", "Pluto"}
MODERN_10: set[str] = CLASSIC_7 | MODERN_3
EXTENDED:  set[str] = MODERN_10 | {"True Node", "North Node", "Chiron", "Asc", "MC"}


# ---------------------------------------------------------------------------
# Dial constants
# ---------------------------------------------------------------------------

# Maps dial size in degrees → harmonic (folding factor).
# 360° wheel  (harmonic  1): all aspects visible — identity projection.
# 90°  dial   (harmonic  4): collapses conjunction, opposition, square.
# 45°  dial   (harmonic  8): + semisquare (45°), sesquiquadrate (135°).
# 22.5° dial  (harmonic 16): + 22.5° and all multiples — finest Hamburg dial.
_VALID_DIALS: dict[float, int] = {360.0: 1, 90.0: 4, 45.0: 8, 22.5: 16}


def _harmonic_from_dial(dial: float) -> int:
    """
    Return the harmonic (folding factor) for a supported dial size.

    Raises ValueError for any value not in {360, 90, 45, 22.5}.
    """
    h = _VALID_DIALS.get(float(dial))
    if h is None:
        raise ValueError(
            f"dial must be one of {sorted(_VALID_DIALS, reverse=True)}, got {dial!r}. "
            f"Use to_dial(longitude, harmonic) directly for arbitrary harmonics."
        )
    return h


# ---------------------------------------------------------------------------
# Result types
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


@dataclass(frozen=True, slots=True)
class PlanetaryPicture:
    """
    RITE: The Symmetrical Equation — the condition A = B/C where a body
          occupies the midpoint of a planetary pair on a chosen dial.

    THEOREM: Frozen record of a single planetary picture equation,
             capturing the focus planet (A), the pair whose midpoint it
             occupies (B, C), the midpoint longitude, the measured orb,
             and the dial on which the picture was detected.

    RITE OF PURPOSE:
        PlanetaryPicture is the result vessel of planetary_pictures().
        It labels each symmetrical equation with all three participants
        so callers can enumerate, filter, and interpret all A=B/C
        configurations in a chart without managing parallel index
        structures.  Without this vessel, planetary picture results
        would require the caller to reconstruct the equation from raw
        midpoint and planet longitude arrays.

    LAW OF OPERATION:
        Responsibilities:
            - Store focus, pair_a, pair_b, midpoint_longitude, orb, dial.
            - Render a compact repr: "focus = pair_a/pair_b (orb° on Xdial)".
        Non-responsibilities:
            - Does not judge whether the picture is "significant".
            - Does not validate that focus ∉ {pair_a, pair_b}.
            - Does not perform any I/O or kernel access.
        Structural invariants:
            - orb >= 0.0.
            - dial ∈ {360.0, 90.0, 45.0, 22.5}.
            - midpoint_longitude is the shorter-arc midpoint of pair_a and
              pair_b, expressed on the 360° wheel.

    Canon: Alfred Witte, Rules for Planetary Pictures (Hamburg School, 1928);
           Reinhold Ebertin, The Combination of Stellar Influences (1940).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.midpoints.PlanetaryPicture",
        "risk": "low",
        "api": {"frozen": ["focus", "pair_a", "pair_b", "midpoint_longitude", "orb", "dial"], "internal": []},
        "state": {"mutable": false, "owners": []},
        "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
        "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
        "failures": {"policy": "none"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    focus:              str    # planet sitting on the midpoint  (A in A = B/C)
    pair_a:             str    # first body of the generating pair (B)
    pair_b:             str    # second body of the generating pair (C)
    midpoint_longitude: float  # shorter-arc midpoint longitude on the 360° wheel
    orb:                float  # angular distance focus→midpoint measured on the dial
    dial:               float  # dial size in degrees: 360, 90, 45, or 22.5

    def __repr__(self) -> str:
        return (
            f"{self.focus} = {self.pair_a}/{self.pair_b}  "
            f"(orb {self.orb:.3f}° on {self.dial}° dial)"
        )


@dataclass(frozen=True, slots=True)
class MidpointWeight:
    """
    RITE: The Activation Score — the record of how deeply a body is embedded
          in the midpoint web of a chart.

    THEOREM: Frozen record pairing a planet with every planetary picture in
             which it is the focus (A = B/C), and the count of those pictures
             as a single activation score.

    RITE OF PURPOSE:
        MidpointWeight is the result vessel of midpoint_weighting().
        It answers "which planet has the most midpoints converging on it?"
        — the Midpoint Weighting Analysis (MWA) pioneered by Michael
        Munkasey.  Without this vessel, callers would need to group and
        count PlanetaryPicture results themselves.

    LAW OF OPERATION:
        Responsibilities:
            - Store planet, score, and all activating pictures.
            - Invariant: score == len(pictures).
            - pictures is sorted by orb, tightest first.
        Non-responsibilities:
            - Does not interpret whether a high score is "positive" or
              "negative" in astrological terms.
            - Does not filter by aspect name or orb beyond what pictures store.
        Structural invariants:
            - score == len(pictures) always.
            - score >= 0.

    Canon: Michael Munkasey, Midpoint Weighting Analysis (1991).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.midpoints.MidpointWeight",
        "risk": "low",
        "api": {"frozen": ["planet", "score", "pictures"], "internal": []},
        "state": {"mutable": false, "owners": []},
        "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
        "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
        "failures": {"policy": "none"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    planet:   str
    score:    int
    pictures: tuple[PlanetaryPicture, ...]

    def __repr__(self) -> str:
        return f"MidpointWeight({self.planet!r}, score={self.score})"


@dataclass(frozen=True, slots=True)
class MidpointCluster:
    """
    RITE: The Focal Hotspot — a spatial concentration of midpoints on a
          harmonic dial, revealing where planetary pair energies converge
          in the chart's hidden geometry.

    THEOREM: Frozen record of a connected group of midpoints whose dial
             positions lie within the cluster orb of each other (via
             union-find on circular proximity), together with the cluster's
             centre position, physical spread, and the dial on which it was
             detected.

    RITE OF PURPOSE:
        MidpointCluster is the result vessel of midpoint_clusters().
        It surfaces the observation that charts with tight midpoint bundles
        at a specific dial degree have a concentrated thematic hotspot at
        that position — highly sensitive to transit, solar arc, and
        rectification work.  Without this vessel, callers would need to
        perform the proximity grouping and circular averaging themselves.

    LAW OF OPERATION:
        Responsibilities:
            - Store dial_position (centre), midpoints, spread, and dial.
            - midpoints is sorted by dial position.
            - spread == max(dial_pos) − min(dial_pos) across all members,
              measured as an unwrapped linear span from the first member.
        Non-responsibilities:
            - Does not interpret the astrological meaning of the cluster.
            - Does not validate that each member's dial position is distinct.
        Structural invariants:
            - len(midpoints) >= 2.
            - spread >= 0.0.
            - dial_position is in [0, dial).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.midpoints.MidpointCluster",
        "risk": "low",
        "api": {"frozen": ["dial_position", "midpoints", "spread", "dial"], "internal": []},
        "state": {"mutable": false, "owners": []},
        "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
        "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
        "failures": {"policy": "none"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    dial_position: float                  # cluster centre on the dial (degrees)
    midpoints:     tuple[Midpoint, ...]   # members sorted by dial position
    spread:        float                  # angular span from first to last member
    dial:          float                  # dial size in degrees: 360, 90, 45, or 22.5

    def __repr__(self) -> str:
        return (
            f"MidpointCluster(dial_position={self.dial_position:.2f}°, "
            f"size={len(self.midpoints)}, spread={self.spread:.3f}°, "
            f"dial={self.dial}°)"
        )


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
    """Shorter-arc midpoint in [0, 360)."""
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
    """Find midpoints within orb of a target longitude on the 360° wheel."""
    return _service.midpoints_to_point(target, planet_longitudes, orb, planet_set)


# ---------------------------------------------------------------------------
# Dial projections
# ---------------------------------------------------------------------------

def to_dial(longitude: float, harmonic: int) -> float:
    """
    Project a 360° ecliptic longitude onto a harmonic dial.

    The dial collapses the zodiac wheel by the harmonic factor so that
    aspects which are multiples of (360° / harmonic) all map to the same
    dial position.  This makes symmetrical midpoint relationships visible
    as conjunctions on the projected circle.

    Formula: ``(longitude × harmonic) mod (360 / harmonic)``

    Parameters
    ----------
    longitude : ecliptic longitude in degrees (any finite value)
    harmonic  : folding factor — 1 for the 360° wheel, 4 for the 90° dial,
                8 for the 45° dial, 16 for the 22.5° dial.
                Any positive integer is accepted.

    Returns
    -------
    float in [0, 360 / harmonic)

    Examples
    --------
    >>> to_dial(270.0, 4)   # 0° Capricorn on the 90° dial → same as 0° Aries
    0.0
    >>> to_dial(225.0, 8)   # 15° Scorpio on the 45° dial
    0.0
    """
    dial_size = 360.0 / harmonic
    return (longitude * harmonic) % dial_size


def to_dial_90(longitude: float) -> float:
    """
    Project a 360° ecliptic longitude onto the 90° dial (harmonic 4).

    The 90° dial (Hamburg / Uranian School) compresses the zodiac by a
    factor of 4, folding 0° Aries, 0° Cancer, 0° Libra, and 0° Capricorn
    onto the same 0° point.  This causes midpoints that are invisible on
    a 360° wheel to cluster visibly on the dial.

    Formula: ``to_dial(longitude, 4)``
    """
    return to_dial(longitude, 4)


def to_dial_45(longitude: float) -> float:
    """
    Project a 360° ecliptic longitude onto the 45° dial (harmonic 8).

    Collapses the wheel by a factor of 8, making semisquares (45°),
    squares (90°), sesquiquadrates (135°), and oppositions (180°) all
    conjunct on the dial.  The 45° dial is the standard complement to the
    90° dial in Uranian practice.

    Formula: ``to_dial(longitude, 8)``
    """
    return to_dial(longitude, 8)


def to_dial_22_5(longitude: float) -> float:
    """
    Project a 360° ecliptic longitude onto the 22.5° dial (harmonic 16).

    The finest standard Hamburg dial — collapses the wheel by a factor of
    16.  Used for the most precise midpoint analysis, particularly in
    rectification and solar arc work where tight orbs (< 0.5°) are required.

    Formula: ``to_dial(longitude, 16)``
    """
    return to_dial(longitude, 16)


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
    mps.sort(key=lambda m: to_dial(m.longitude, 4))
    return mps


def dial_45_midpoints(
    planet_longitudes: dict[str, float],
    planet_set: str = "classic",
) -> list[Midpoint]:
    """
    Return all midpoints sorted by their position on the 45° dial.

    Parameters
    ----------
    planet_longitudes : dict of body name → longitude (degrees)
    planet_set        : 'classic', 'modern', or 'extended'

    Returns
    -------
    List of Midpoint sorted by 45° dial position (0–45°)
    """
    mps = calculate_midpoints(planet_longitudes, planet_set)
    mps.sort(key=lambda m: to_dial(m.longitude, 8))
    return mps


def dial_22_5_midpoints(
    planet_longitudes: dict[str, float],
    planet_set: str = "classic",
) -> list[Midpoint]:
    """
    Return all midpoints sorted by their position on the 22.5° dial.

    Parameters
    ----------
    planet_longitudes : dict of body name → longitude (degrees)
    planet_set        : 'classic', 'modern', or 'extended'

    Returns
    -------
    List of Midpoint sorted by 22.5° dial position (0–22.5°)
    """
    mps = calculate_midpoints(planet_longitudes, planet_set)
    mps.sort(key=lambda m: to_dial(m.longitude, 16))
    return mps


def midpoint_tree(
    focus: float,
    planet_longitudes: dict[str, float],
    orb: float = 2.0,
    planet_set: str = "classic",
    dial: float = 360,
) -> list[tuple[Midpoint, float]]:
    """
    Find all midpoints equidistant from a focus point on the chosen dial.

    A "midpoint tree" (or "midpoint direct/indirect") lists every planetary
    midpoint that falls within *orb* of the focus on the specified dial.
    On the 90° dial this exposes harmonic midpoints that are exact multiples
    of 90° away on the full wheel.  The 45° and 22.5° dials expose
    progressively finer harmonic contacts.

    Parameters
    ----------
    focus  : target longitude (degrees, 360° wheel coordinates)
    planet_longitudes : dict of body name → longitude (degrees)
    orb    : maximum orb in degrees, measured on the chosen dial
    planet_set : 'classic', 'modern', or 'extended'
    dial   : 360, 90, 45, or 22.5

    Returns
    -------
    List of (Midpoint, orb_value) sorted by absolute orb (tightest first)

    Notes
    -----
    On any dial other than 360°, both the focus and each midpoint longitude
    are projected via ``to_dial()`` before the orb is measured.  The orb
    itself is the shortest arc on the dial circle (i.e. min(d, dial−d)).
    """
    harmonic  = _harmonic_from_dial(dial)
    dial_size = 360.0 / harmonic

    all_mps = calculate_midpoints(planet_longitudes, planet_set)
    hits: list[tuple[Midpoint, float]] = []

    if harmonic == 1:
        # 360° wheel: standard shortest-arc distance
        focus_pos = focus % 360.0
        for mp in all_mps:
            diff = abs((mp.longitude - focus_pos + 180.0) % 360.0 - 180.0)
            if diff <= orb:
                hits.append((mp, diff))
    else:
        # Harmonic dial: project both focus and midpoint, then shortest arc
        focus_dial = to_dial(focus, harmonic)
        for mp in all_mps:
            mp_dial  = to_dial(mp.longitude, harmonic)
            raw_diff = abs(mp_dial - focus_dial)
            diff     = min(raw_diff, dial_size - raw_diff)
            if diff <= orb:
                hits.append((mp, diff))

    hits.sort(key=lambda x: x[1])
    return hits


# ---------------------------------------------------------------------------
# Antiscia and contra-antiscia
# ---------------------------------------------------------------------------

def antiscion(longitude: float) -> float:
    """
    Return the antiscion (solstice reflection) of an ecliptic longitude.

    The antiscion is the mirror image of a point across the Cancer–Capricorn
    solstice axis (90°/270°).  Two planets in antiscia relation share equal
    solar declination and behave like a conjunction in traditional and
    Uranian technique alike.

    Formula: ``(180° − longitude) mod 360°``

    Antiscia sign pairs (each sign reflects to its partner across 0° Cancer):
        Aries ↔ Virgo,   Taurus ↔ Leo,   Gemini ↔ Cancer,
        Libra ↔ Pisces,  Scorpio ↔ Aquarius,  Sagittarius ↔ Capricorn.

    Parameters
    ----------
    longitude : ecliptic longitude in degrees (any finite value)

    Returns
    -------
    float in [0, 360)

    Examples
    --------
    >>> antiscion(15.0)    # Aries 15° → Virgo 15°
    165.0
    >>> antiscion(135.0)   # Leo 15° → Taurus 15°
    45.0
    >>> antiscion(255.0)   # Sagittarius 15° → Capricorn 15°
    285.0
    """
    return (180.0 - longitude) % 360.0


def contra_antiscion(longitude: float) -> float:
    """
    Return the contra-antiscion (equinox reflection) of an ecliptic longitude.

    The contra-antiscion is the mirror image of a point across the
    Aries–Libra equinox axis (0°/180°) — exactly 180° opposite the antiscion.
    Two planets in contra-antiscia relation share equal but opposite solar
    declination.

    Formula: ``(−longitude) mod 360°``

    Contra-antiscia sign pairs (reflection across 0° Aries):
        Aries ↔ Pisces,   Taurus ↔ Aquarius,  Gemini ↔ Capricorn,
        Cancer ↔ Sagittarius,  Leo ↔ Scorpio,  Virgo ↔ Libra.

    Parameters
    ----------
    longitude : ecliptic longitude in degrees (any finite value)

    Returns
    -------
    float in [0, 360)

    Examples
    --------
    >>> contra_antiscion(15.0)    # Aries 15° → Pisces 15°
    345.0
    >>> contra_antiscion(135.0)   # Leo 15° → Scorpio 15°
    225.0
    """
    return (-longitude) % 360.0


# ---------------------------------------------------------------------------
# Planetary pictures
# ---------------------------------------------------------------------------

def planetary_pictures(
    planet_longitudes: dict[str, float],
    orb: float = 1.5,
    planet_set: str = "classic",
    dial: float = 360.0,
) -> list[PlanetaryPicture]:
    """
    Enumerate all A = B/C equations where planet A sits on the midpoint of B and C.

    A planetary picture (Witte's "Planetenbilder") is a symmetrical equation
    where a body falls within *orb* of the midpoint of a pair of bodies on
    the chosen dial.  On the 90° dial this exposes hard-aspect midpoint
    contacts that are invisible on the 360° wheel.

    The focus planet (A) is excluded from the generating pair (B, C) — a
    planet cannot form a picture with itself.

    Parameters
    ----------
    planet_longitudes : dict of body name → longitude (degrees)
    orb               : maximum angular distance on the dial in degrees
    planet_set        : 'classic' (7), 'modern' (10), or 'extended'
    dial              : 360, 90, 45, or 22.5

    Returns
    -------
    List of PlanetaryPicture sorted by orb (tightest first)
    """
    harmonic  = _harmonic_from_dial(dial)
    dial_size = 360.0 / harmonic

    allowed = {"classic": CLASSIC_7, "modern": MODERN_10, "extended": EXTENDED}.get(
        planet_set, CLASSIC_7
    )
    available: dict[str, float] = {
        name.strip().title(): lon
        for name, lon in planet_longitudes.items()
        if name.strip().title() in allowed
    }

    # Pre-compute all (pair_a, pair_b, midpoint_longitude) triples
    all_pairs: list[tuple[str, str, float]] = [
        (a, b, _midpoint(lon_a, lon_b))
        for (a, lon_a), (b, lon_b) in combinations(available.items(), 2)
    ]

    pictures: list[PlanetaryPicture] = []
    for focus_name, focus_lon in available.items():
        focus_dial = to_dial(focus_lon, harmonic)
        for pair_a, pair_b, mp_lon in all_pairs:
            if focus_name in (pair_a, pair_b):
                continue  # focus cannot be a member of its own generating pair
            mp_dial  = to_dial(mp_lon, harmonic)
            raw_diff = abs(focus_dial - mp_dial)
            dist     = min(raw_diff, dial_size - raw_diff)
            if dist <= orb:
                pictures.append(PlanetaryPicture(
                    focus=focus_name,
                    pair_a=pair_a,
                    pair_b=pair_b,
                    midpoint_longitude=mp_lon,
                    orb=dist,
                    dial=dial,
                ))

    pictures.sort(key=lambda p: p.orb)
    return pictures


# ---------------------------------------------------------------------------
# Midpoint Weighting Analysis
# ---------------------------------------------------------------------------

def midpoint_weighting(
    planet_longitudes: dict[str, float],
    orb: float = 1.5,
    planet_set: str = "classic",
    dial: float = 360.0,
) -> list[MidpointWeight]:
    """
    Rank each planet by how many planetary pictures it forms (MWA).

    For each body in the planet set, counts how many midpoints of other
    pairs fall within *orb* of that body on the chosen dial.  Returns a
    ranked list (highest score first) showing which planets are most
    "activated" in the midpoint web of the chart.

    A planet with a high score is a structural hub: many planetary pairs
    have chosen it as their axis of expression.

    Method: Midpoint Weighting Analysis (MWA) pioneered by Michael Munkasey.

    Parameters
    ----------
    planet_longitudes : dict of body name → longitude (degrees)
    orb               : maximum angular distance on the dial in degrees
    planet_set        : 'classic', 'modern', or 'extended'
    dial              : 360, 90, 45, or 22.5

    Returns
    -------
    List of MidpointWeight sorted by score descending, then planet name.
    Every planet in the available set is included, even those with score 0.
    """
    all_pictures = planetary_pictures(
        planet_longitudes, orb=orb, planet_set=planet_set, dial=dial
    )

    # Group all pictures by their focus planet
    grouped: dict[str, list[PlanetaryPicture]] = {}
    for pic in all_pictures:
        grouped.setdefault(pic.focus, []).append(pic)

    # Ensure every planet in the set is present, even if score is 0
    allowed = {"classic": CLASSIC_7, "modern": MODERN_10, "extended": EXTENDED}.get(
        planet_set, CLASSIC_7
    )
    for name in planet_longitudes:
        canonical = name.strip().title()
        if canonical in allowed:
            grouped.setdefault(canonical, [])

    weights = [
        MidpointWeight(
            planet=name,
            score=len(pics),
            pictures=tuple(sorted(pics, key=lambda p: p.orb)),
        )
        for name, pics in grouped.items()
    ]
    weights.sort(key=lambda w: (-w.score, w.planet))
    return weights


# ---------------------------------------------------------------------------
# Dynamic activation
# ---------------------------------------------------------------------------

def activated_midpoints(
    transit_longitude: float,
    natal_midpoints: list[Midpoint],
    orb: float = 1.5,
    dial: float = 360.0,
) -> list[tuple[Midpoint, float]]:
    """
    Find natal midpoints activated by a transiting or directed point.

    Given the ecliptic longitude of a transiting planet, solar arc
    direction, or secondary progressed planet, returns all natal midpoints
    whose dial position falls within *orb* of the activating point on the
    chosen dial.

    This is the dynamic complement to the static planetary_pictures()
    analysis: where planetary_pictures() maps the natal web, this function
    identifies which nodes of that web are being triggered at a given moment.

    Parameters
    ----------
    transit_longitude : longitude of the activating point in degrees
                        (transit, solar arc direction, progressed planet, etc.)
    natal_midpoints   : list of Midpoint objects from calculate_midpoints()
    orb               : maximum angular distance on the dial in degrees
    dial              : 360, 90, 45, or 22.5

    Returns
    -------
    List of (Midpoint, orb_value) sorted by orb (tightest first)

    Example
    -------
    To find which natal midpoints a transiting Saturn at 280° activates
    on the 90° dial with a 1° orb::

        natal_mps   = calculate_midpoints(natal_longitudes)
        activations = activated_midpoints(280.0, natal_mps, orb=1.0, dial=90)
    """
    harmonic   = _harmonic_from_dial(dial)
    dial_size  = 360.0 / harmonic
    trans_dial = to_dial(transit_longitude, harmonic)

    hits: list[tuple[Midpoint, float]] = []
    for mp in natal_midpoints:
        mp_dial  = to_dial(mp.longitude, harmonic)
        raw_diff = abs(trans_dial - mp_dial)
        dist     = min(raw_diff, dial_size - raw_diff)
        if dist <= orb:
            hits.append((mp, dist))

    hits.sort(key=lambda x: x[1])
    return hits


# ---------------------------------------------------------------------------
# Cluster analysis
# ---------------------------------------------------------------------------

def midpoint_clusters(
    planet_longitudes: dict[str, float],
    cluster_orb: float = 1.0,
    min_size: int = 3,
    planet_set: str = "classic",
    dial: float = 90.0,
) -> list[MidpointCluster]:
    """
    Find spatial concentrations of midpoints on the dial (hotspot analysis).

    Scans the chosen dial for positions where *min_size* or more midpoints
    cluster within *cluster_orb* degrees of each other.  Grouping is
    determined by circular proximity via union-find: any two midpoints within
    *cluster_orb* of each other on the dial are placed in the same cluster.

    A cluster of 4+ midpoints at the same dial degree is a structural
    hotspot — a sensitive degree simultaneously activated by many planetary
    pairs.  These degrees respond strongly to transits and solar arcs.

    The default dial is 90° (not 360°) because the 90° dial is the
    standard Hamburg tool for finding such concentrations.

    Parameters
    ----------
    planet_longitudes : dict of body name → longitude (degrees)
    cluster_orb       : maximum dial-distance between any two connected members
    min_size          : minimum number of midpoints to constitute a cluster
    planet_set        : 'classic', 'modern', or 'extended'
    dial              : 360, 90, 45, or 22.5  (default 90)

    Returns
    -------
    List of MidpointCluster sorted by size descending, then by dial_position.
    Empty list if no cluster of the required size is found.
    """
    harmonic  = _harmonic_from_dial(dial)
    dial_size = 360.0 / harmonic

    mps = calculate_midpoints(planet_longitudes, planet_set)
    n   = len(mps)
    if n < min_size:
        return []

    positions = [to_dial(m.longitude, harmonic) for m in mps]

    # Union-Find with path compression
    parent = list(range(n))

    def _find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def _union(x: int, y: int) -> None:
        px, py = _find(x), _find(y)
        if px != py:
            parent[px] = py

    # Connect all pairs whose circular dial distance is within cluster_orb
    for i in range(n):
        for j in range(i + 1, n):
            raw  = abs(positions[i] - positions[j])
            dist = min(raw, dial_size - raw)
            if dist <= cluster_orb:
                _union(i, j)

    # Group indices by component root
    components: dict[int, list[int]] = {}
    for i in range(n):
        components.setdefault(_find(i), []).append(i)

    clusters: list[MidpointCluster] = []
    for indices in components.values():
        if len(indices) < min_size:
            continue

        members   = [mps[i] for i in indices]
        pos_list  = [positions[i] for i in indices]

        # Circular mean: unwrap all positions relative to the first member
        # to avoid averaging across the 0/dial_size boundary incorrectly.
        ref       = pos_list[0]
        half      = dial_size / 2.0
        unwrapped = [ref + ((p - ref + half) % dial_size - half) for p in pos_list]
        centre    = (sum(unwrapped) / len(unwrapped)) % dial_size
        spread    = max(unwrapped) - min(unwrapped)

        # Sort members by their dial position for a deterministic tuple order
        members_sorted = [m for _, m in sorted(zip(pos_list, members), key=lambda x: x[0])]

        clusters.append(MidpointCluster(
            dial_position=centre,
            midpoints=tuple(members_sorted),
            spread=spread,
            dial=dial,
        ))

    clusters.sort(key=lambda c: (-len(c.midpoints), c.dial_position))
    return clusters
