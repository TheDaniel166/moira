"""
Moira — constants.py
The Warden of Astronomical Constants: governs all fixed numerical values,
body identifiers, zodiacal definitions, and aspect geometry used across the
Moira ephemeris engine.

Boundary: owns every compile-time constant and enumeration that other modules
consume as read-only data. Delegates all computation to the modules that import
these values. Does not own any calculation logic, file I/O, or mutable state.

Public surface:
    TAU, PI, DEG2RAD, RAD2DEG, ARCSEC2RAD,
    J2000, JD_DELTA, JULIAN_CENTURY, JULIAN_YEAR, TROPICAL_YEAR, SIDEREAL_YEAR,
    NAIF, Body, NAIF_ROUTES, EARTH_ROUTE,
    SIGNS, SIGN_SYMBOLS, sign_of,
    HouseSystem, HOUSE_SYSTEM_NAMES,
    AspectDefinition, Aspect, ASPECT_TIERS, DEFAULT_ORBS

Import-time side effects: None

External dependency assumptions:
    None (stdlib math only)
"""

import math

# ---------------------------------------------------------------------------
# Mathematical constants
# ---------------------------------------------------------------------------
TAU        = math.tau          # 2π
PI         = math.pi
DEG2RAD    = PI / 180.0
RAD2DEG    = 180.0 / PI
ARCSEC2RAD = DEG2RAD / 3600.0

# ---------------------------------------------------------------------------
# Time constants
# ---------------------------------------------------------------------------
J2000      = 2451545.0         # Julian Date of J2000.0 epoch (2000-Jan-1.5 TT)
JD_DELTA   = 0.5               # JD starts at noon; calendar day starts at midnight
JULIAN_CENTURY = 36525.0       # Days per Julian century
JULIAN_YEAR    = 365.25        # Days per Julian year (exact by definition)
TROPICAL_YEAR  = 365.24219     # Mean tropical year in days
SIDEREAL_YEAR  = 365.256363    # Mean sidereal year in days

# ---------------------------------------------------------------------------
# Physical constants — single canonical source for the whole library
# ---------------------------------------------------------------------------
# Speed of light: IAU exact definition (km/s × s/day)
C_KM_PER_DAY: float = 299_792.458 * 86_400.0

# IAU 2012 exact definition of the astronomical unit
KM_PER_AU: float = 149_597_870.700

# WGS-84 / IAU 2015 equatorial Earth radius
EARTH_RADIUS_KM: float = 6_378.137

# Solar geometric equatorial radius used for eclipse shadow geometry and
# apparent angular diameter calculations (JPL standard / Haberreiter et al. 2008).
SUN_RADIUS_KM: float = 696_340.0

# Lunar mean radius (IAU Working Group on Cartographic Coordinates 2015)
MOON_RADIUS_KM: float = 1_737.4

# ---------------------------------------------------------------------------
# NAIF / SPICE body IDs (as used in DE441)
# ---------------------------------------------------------------------------
class NAIF:
    """
    RITE: The Warden of NAIF Body Identifiers.

    THEOREM: Enforces the canonical integer body codes defined by the NAIF/SPICE
    standard as used in the JPL DE441 ephemeris kernel.

    RITE OF PURPOSE:
        Every SPK segment lookup requires an integer body ID that matches the
        NAIF/SPICE convention. This Warden centralises those IDs so that no
        module hard-codes magic integers. Without it, body-ID literals would
        scatter across the codebase, making kernel upgrades error-prone and
        cross-module consistency impossible to enforce.

    LAW OF OPERATION:
        Responsibilities:
            - Serve as the single authoritative source of NAIF integer body IDs
              for all bodies present in the DE441 kernel.
        Non-responsibilities:
            - Does not perform any SPK lookups or kernel I/O.
            - Does not validate that a given ID exists in a loaded kernel.
        Dependencies:
            - None; all values are compile-time integer literals.
        Structural invariants:
            - All attributes are class-level integer constants; no instance state.
        Behavioral invariants:
            - Values are immutable for the lifetime of the interpreter.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.constants.NAIF",
      "risk": "low",
      "api": {
        "frozen": [
          "SOLAR_SYSTEM_BARYCENTER", "MERCURY_BARYCENTER", "VENUS_BARYCENTER",
          "EARTH_MOON_BARYCENTER", "MARS_BARYCENTER", "JUPITER_BARYCENTER",
          "SATURN_BARYCENTER", "URANUS_BARYCENTER", "NEPTUNE_BARYCENTER",
          "PLUTO_BARYCENTER", "SUN", "MOON", "EARTH", "MERCURY", "VENUS"
        ],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["NAIF"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    SOLAR_SYSTEM_BARYCENTER = 0
    MERCURY_BARYCENTER       = 1
    VENUS_BARYCENTER         = 2
    EARTH_MOON_BARYCENTER    = 3
    MARS_BARYCENTER          = 4
    JUPITER_BARYCENTER       = 5
    SATURN_BARYCENTER        = 6
    URANUS_BARYCENTER        = 7
    NEPTUNE_BARYCENTER       = 8
    PLUTO_BARYCENTER         = 9
    SUN                      = 10
    MOON                     = 301
    EARTH                    = 399
    MERCURY                  = 199
    VENUS                    = 299

# ---------------------------------------------------------------------------
# Planet identifiers (Moira's own enum-like constants)
# ---------------------------------------------------------------------------
class Body:
    """
    RITE: The Warden of Celestial Body Identifiers.

    THEOREM: Enforces the canonical string names for all planets, luminaries,
    calculated points, and body collections used throughout the Moira engine.

    RITE OF PURPOSE:
        Moira's computation pipeline passes body names as strings between
        modules — from NAIF route lookup to result vessel construction. This
        Warden provides a single, authoritative namespace for those strings,
        preventing silent mismatches caused by inconsistent spelling or
        capitalisation. It also serves the pre-built collection lists
        ALL_PLANETS and ALL_POINTS, which define the default computation scope
        for chart calculations.

    LAW OF OPERATION:
        Responsibilities:
            - Serve as the single authoritative source of canonical body-name
              strings for all celestial bodies and calculated points.
            - Provide ALL_PLANETS and ALL_POINTS as ordered reference lists.
        Non-responsibilities:
            - Does not perform any astronomical computation.
            - Does not map body names to NAIF IDs (that is NAIF_ROUTES's role).
            - Does not validate that a body is supported by the loaded kernel.
        Dependencies:
            - None; all values are compile-time string literals.
        Structural invariants:
            - All attributes are class-level constants; no instance state.
        Behavioral invariants:
            - String values are immutable for the lifetime of the interpreter.
            - ALL_PLANETS and ALL_POINTS are ordered lists; index positions are
              stable across releases.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.constants.Body",
      "risk": "medium",
      "api": {
        "frozen": [
          "SUN", "MOON", "MERCURY", "VENUS", "EARTH", "MARS", "JUPITER",
          "SATURN", "URANUS", "NEPTUNE", "PLUTO",
          "TRUE_NODE", "MEAN_NODE", "LILITH", "TRUE_LILITH", "CHIRON",
          "ALL_PLANETS", "ALL_POINTS"
        ],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["Body"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    SUN     = "Sun"
    MOON    = "Moon"
    MERCURY = "Mercury"
    VENUS   = "Venus"
    EARTH   = "Earth"
    MARS    = "Mars"
    JUPITER = "Jupiter"
    SATURN  = "Saturn"
    URANUS  = "Uranus"
    NEPTUNE = "Neptune"
    PLUTO   = "Pluto"

    # Calculated points
    TRUE_NODE  = "True Node"
    MEAN_NODE  = "Mean Node"
    LILITH     = "Lilith"          # Mean Black Moon Lilith
    TRUE_LILITH = "True Lilith"    # True Osculating Lilith
    CHIRON     = "Chiron"          # requires separate kernel

    ALL_PLANETS = [
        SUN, MOON, MERCURY, VENUS, MARS,
        JUPITER, SATURN, URANUS, NEPTUNE, PLUTO,
    ]

    ALL_POINTS = [
        SUN, MOON, MERCURY, VENUS, MARS,
        JUPITER, SATURN, URANUS, NEPTUNE, PLUTO,
        TRUE_NODE, MEAN_NODE, LILITH, TRUE_LILITH,
    ]

    # Mean Sidereal Orbital Periods (Earth Days)
    # Source: NASA Planetary Fact Sheets / J2000.0
    SIDEREAL_PERIODS = {
        MERCURY:  87.969257,
        VENUS:   224.700798,
        EARTH:   SIDEREAL_YEAR,
        MARS:    686.979586,
        JUPITER: 4332.589,
        SATURN: 10759.22,
        URANUS: 30685.4,
        NEPTUNE: 60189.0,
        PLUTO:   90560.0,
    }

# ---------------------------------------------------------------------------
# NAIF route: how to compute geocentric position of each body
# Each entry is a list of (center, target) segments to chain.
# Final result = sum of vectors.
# ---------------------------------------------------------------------------
# Earth position relative to SSB:  [0,3] + [3,399]
# Moon position relative to Earth: [0,3] + [3,301] − Earth
NAIF_ROUTES: dict[str, list[tuple[int, int]]] = {
    Body.SUN:     [(0, 10)],                       # SSB→Sun  (then subtract Earth)
    Body.MOON:    [(3, 301)],                       # EMB→Moon (relative to Earth directly)
    Body.MERCURY: [(0, 1),  (1, 199)],             # SSB→MercBary→Mercury
    Body.VENUS:   [(0, 2),  (2, 299)],             # SSB→VenusBary→Venus
    Body.MARS:    [(0, 4)],                         # SSB→MarsBary (no separate Mars body in DE441)
    Body.JUPITER: [(0, 5)],
    Body.SATURN:  [(0, 6)],
    Body.URANUS:  [(0, 7)],
    Body.NEPTUNE: [(0, 8)],
    Body.PLUTO:   [(0, 9)],
}

# Earth's own route (needed to convert barycentric → geocentric)
EARTH_ROUTE: list[tuple[int, int]] = [(0, 3), (3, 399)]

# ---------------------------------------------------------------------------
# Zodiac signs
# ---------------------------------------------------------------------------
SIGNS: list[str] = [
    "Aries", "Taurus", "Gemini", "Cancer",
    "Leo", "Virgo", "Libra", "Scorpio",
    "Sagittarius", "Capricorn", "Aquarius", "Pisces",
]

SIGN_SYMBOLS: list[str] = [
    "♈", "♉", "♊", "♋",
    "♌", "♍", "♎", "♏",
    "♐", "♑", "♒", "♓",
]

def sign_of(longitude: float) -> tuple[str, str, float]:
    """Return (sign_name, symbol, degree_within_sign) for an ecliptic longitude."""
    lon = longitude % 360.0
    idx = int(lon // 30)
    return SIGNS[idx], SIGN_SYMBOLS[idx], lon - idx * 30.0

# ---------------------------------------------------------------------------
# House systems
# ---------------------------------------------------------------------------
class HouseSystem:
    """
    RITE: The Warden of House System Codes.

    THEOREM: Enforces the canonical single-character (or two-character) codes
    that identify each supported astrological house system in external
    ephemeris interfaces.

    RITE OF PURPOSE:
        House calculation interfaces commonly select an algorithm via a
        compact flag. This Warden centralises those flags so that every module
        that requests house calculations uses the correct, stable code.
        Without it, literals would be scattered across the codebase, making it
        impossible to audit which systems are supported or to add new ones
        consistently.

    LAW OF OPERATION:
        Responsibilities:
            - Serve as the single authoritative source of house-system flag
              strings for all supported house systems.
        Non-responsibilities:
            - Does not perform any house cusp calculation.
            - Does not validate that a given code is accepted by the installed
              downstream engine version.
        Dependencies:
            - None; all values are compile-time string literals.
        Structural invariants:
            - All attributes are class-level string constants; no instance state.
        Behavioral invariants:
            - Values are immutable for the lifetime of the interpreter.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.constants.HouseSystem",
      "risk": "low",
      "api": {
        "frozen": [
          "PLACIDUS", "KOCH", "EQUAL", "WHOLE_SIGN", "CAMPANUS",
          "REGIOMONTANUS", "PORPHYRY", "MERIDIAN", "ALCABITIUS", "MORINUS",
          "TOPOCENTRIC", "VEHLOW", "SUNSHINE", "AZIMUTHAL", "CARTER",
          "PULLEN_SD", "PULLEN_SR", "KRUSINSKI", "APC"
        ],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["HouseSystem"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    PLACIDUS       = "P"
    KOCH           = "K"
    EQUAL          = "E"
    WHOLE_SIGN     = "W"
    CAMPANUS       = "C"
    REGIOMONTANUS  = "R"
    PORPHYRY       = "O"
    MERIDIAN       = "X"    # also called Axial Rotation
    ALCABITIUS     = "B"
    MORINUS        = "M"
    TOPOCENTRIC    = "T"
    VEHLOW         = "V"    # Equal from ASC-15° (Vehlow)
    SUNSHINE       = "N"    # Makransky's Sunshine houses
    AZIMUTHAL      = "H"    # Horizontal / Azimuthal houses
    CARTER         = "CT"   # Carter Poli-Equatorial
    PULLEN_SD      = "PS"   # Pullen Sinusoidal Delta
    PULLEN_SR      = "PR"   # Pullen Sinusoidal Ratio
    KRUSINSKI      = "U"    # Krusinski-Pisa-Goeldi
    APC            = "Y"    # APC houses

HOUSE_SYSTEM_NAMES: dict[str, str] = {
    HouseSystem.PLACIDUS:      "Placidus",
    HouseSystem.KOCH:          "Koch",
    HouseSystem.EQUAL:         "Equal",
    HouseSystem.WHOLE_SIGN:    "Whole Sign",
    HouseSystem.CAMPANUS:      "Campanus",
    HouseSystem.REGIOMONTANUS: "Regiomontanus",
    HouseSystem.PORPHYRY:      "Porphyry",
    HouseSystem.MERIDIAN:      "Meridian",
    HouseSystem.ALCABITIUS:    "Alcabitius",
    HouseSystem.MORINUS:       "Morinus",
    HouseSystem.TOPOCENTRIC:    "Topocentric",
    HouseSystem.VEHLOW:         "Vehlow Equal",
    HouseSystem.SUNSHINE:       "Sunshine",
    HouseSystem.AZIMUTHAL:      "Azimuthal",
    HouseSystem.CARTER:         "Carter",
    HouseSystem.PULLEN_SD:      "Pullen Sinusoidal Delta",
    HouseSystem.PULLEN_SR:      "Pullen Sinusoidal Ratio",
    HouseSystem.KRUSINSKI:      "Krusinski-Pisa",
    HouseSystem.APC:            "APC",
}

# ---------------------------------------------------------------------------
# Aspects
# ---------------------------------------------------------------------------

from dataclasses import dataclass as _dataclass

@_dataclass(frozen=True)
class AspectDefinition:
    """
    RITE: The Vessel of Aspect Geometry.

    THEOREM: Governs the immutable geometric specification of a single
    astrological aspect, comprising its exact angle, default orb, display
    symbol, and major/minor classification.

    RITE OF PURPOSE:
        Aspect detection requires a precise, self-contained description of each
        angular relationship: the exact separation, the tolerance window, the
        Unicode glyph for display, and whether the aspect belongs to the major
        or minor tier. This Vessel bundles those four attributes into a single
        frozen record so that every engine that consumes aspect definitions
        receives a consistent, immutable specification. Without it, aspect
        parameters would be duplicated across detection, display, and
        configuration layers.

    LAW OF OPERATION:
        Responsibilities:
            - Hold the four defining attributes of one astrological aspect as
              an immutable, hashable record.
        Non-responsibilities:
            - Does not detect whether two bodies form this aspect.
            - Does not apply orb overrides or user preferences.
            - Does not perform any computation.
        Dependencies:
            - dataclasses.dataclass (frozen=True) from the standard library.
        Structural invariants:
            - All four fields are set at construction time and never mutated.
            - Instances are hashable and safe to use as dict keys or set members.
        Behavioral invariants:
            - Two AspectDefinition instances with identical field values compare
              equal (dataclass default equality).

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.constants.AspectDefinition",
      "risk": "low",
      "api": {
        "frozen": ["name", "angle", "default_orb", "symbol", "is_major"],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["AspectDefinition"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    name:        str
    angle:       float   # exact angular separation (degrees)
    default_orb: float   # default allowed orb (degrees)
    symbol:      str     # Unicode glyph
    is_major:    bool


# Major aspects
_CONJ  = AspectDefinition("Conjunction",    0.0,   8.0, "☌", True)
_SEXT  = AspectDefinition("Sextile",       60.0,   5.0, "⚹", True)
_SQR   = AspectDefinition("Square",        90.0,   7.0, "□", True)
_TRIN  = AspectDefinition("Trine",        120.0,   7.0, "△", True)
_OPP   = AspectDefinition("Opposition",   180.0,   8.0, "☍", True)

# Common minor aspects
_SSXT  = AspectDefinition("Semisextile",   30.0,   2.0, "⚺", False)
_SSQR  = AspectDefinition("Semisquare",    45.0,   2.0, "∠", False)
_SQSQ  = AspectDefinition("Sesquiquadrate",135.0,  2.0, "⚼", False)
_QNCX  = AspectDefinition("Quincunx",     150.0,   3.0, "⚻", False)
_QNTL  = AspectDefinition("Quintile",      72.0,   2.0, "Q",  False)
_BQNTL = AspectDefinition("Biquintile",   144.0,   2.0, "bQ", False)

# Extended minor aspects
_SEPT  = AspectDefinition("Septile",      360/7,   1.5, "S",  False)
_BSEPT = AspectDefinition("Biseptile",    720/7,   1.5, "bS", False)
_TSEPT = AspectDefinition("Triseptile",  1080/7,   1.5, "tS", False)
_NOVL  = AspectDefinition("Novile",       40.0,    1.5, "N",  False)
_BNOVL = AspectDefinition("Binovile",     80.0,    1.5, "bN", False)
_QNOVL = AspectDefinition("Quadnovile",  160.0,    1.5, "qN", False)
_DECL  = AspectDefinition("Decile",       36.0,    1.5, "⊼",  False)
_TRDEC = AspectDefinition("Tredecile",   108.0,    1.5, "Td", False)
_UNDEC = AspectDefinition("Undecile",    360/11,   1.0, "U",  False)
_QNDEC = AspectDefinition("Quindecile",   24.0,    1.0, "Qd", False)
_VGNT  = AspectDefinition("Vigintile",    18.0,    1.0, "V",  False)


class Aspect:
    """
    RITE: The Warden of Aspect Definitions.

    THEOREM: Enforces the canonical set of AspectDefinition records for all
    supported astrological aspects, organised into major, common-minor, and
    extended-minor tiers.

    RITE OF PURPOSE:
        Aspect detection engines and UI layers need a single, authoritative
        registry of every recognised angular relationship — its exact angle,
        default orb, symbol, and tier membership. This Warden provides that
        registry as named class attributes and pre-built tier lists, so that
        no module needs to re-declare aspect geometry. Without it, aspect
        parameters would be duplicated and could diverge between the detection
        engine, the orb table, and the display layer.

    LAW OF OPERATION:
        Responsibilities:
            - Serve as the single authoritative registry of AspectDefinition
              instances for all supported aspects.
            - Provide MAJOR, COMMON_MINOR, EXTENDED_MINOR, and ALL tier lists
              for iteration and filtering.
        Non-responsibilities:
            - Does not detect aspects between bodies.
            - Does not apply user-defined orb overrides.
            - Does not perform any computation.
        Dependencies:
            - AspectDefinition (defined in this module).
        Structural invariants:
            - All attributes are class-level constants; no instance state.
            - ALL == MAJOR + COMMON_MINOR + EXTENDED_MINOR (no duplicates,
              no omissions).
        Behavioral invariants:
            - Values are immutable for the lifetime of the interpreter.
            - MINOR is a stable backward-compatibility alias for COMMON_MINOR.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.constants.Aspect",
      "risk": "medium",
      "api": {
        "frozen": [
          "CONJUNCTION", "SEMISEXTILE", "SEMISQUARE", "SEXTILE", "SQUARE",
          "TRINE", "SESQUIQUADRATE", "QUINCUNX", "OPPOSITION", "QUINTILE",
          "BIQUINTILE", "TREDECILE", "SEPTILE", "BISEPTILE", "TRISEPTILE",
          "NOVILE", "BINOVILE", "QUADNOVILE", "DECILE", "UNDECILE",
          "QUINDECILE", "VIGINTILE",
          "MAJOR", "COMMON_MINOR", "EXTENDED_MINOR", "MINOR", "ALL"
        ],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["Aspect"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    CONJUNCTION    = _CONJ
    SEMISEXTILE    = _SSXT
    SEMISQUARE     = _SSQR
    SEXTILE        = _SEXT
    SQUARE         = _SQR
    TRINE          = _TRIN
    SESQUIQUADRATE = _SQSQ
    QUINCUNX       = _QNCX
    OPPOSITION     = _OPP
    QUINTILE       = _QNTL
    BIQUINTILE     = _BQNTL
    TREDECILE      = _TRDEC
    SEPTILE        = _SEPT
    BISEPTILE      = _BSEPT
    TRISEPTILE     = _TSEPT
    NOVILE         = _NOVL
    BINOVILE       = _BNOVL
    QUADNOVILE     = _QNOVL
    DECILE         = _DECL
    UNDECILE       = _UNDEC
    QUINDECILE     = _QNDEC
    VIGINTILE      = _VGNT

    MAJOR: list[AspectDefinition] = [_CONJ, _SEXT, _SQR, _TRIN, _OPP]

    COMMON_MINOR: list[AspectDefinition] = [
        _SSXT, _SSQR, _SQSQ, _QNCX, _QNTL, _BQNTL,
    ]

    EXTENDED_MINOR: list[AspectDefinition] = [
        _SEPT, _BSEPT, _TSEPT,
        _NOVL, _BNOVL, _QNOVL,
        _DECL, _TRDEC,
        _UNDEC, _QNDEC, _VGNT,
    ]

    # Backward-compat alias
    MINOR = COMMON_MINOR

    ALL: list[AspectDefinition] = MAJOR + COMMON_MINOR + EXTENDED_MINOR


# Tier-based groups for UI (matching old AspectsService tiers)
ASPECT_TIERS: dict[int, list[AspectDefinition]] = {
    0: Aspect.MAJOR,
    1: Aspect.MAJOR + Aspect.COMMON_MINOR,
    2: Aspect.ALL,
}

# Default orb table (angle → orb degrees) — derived from definitions
DEFAULT_ORBS: dict[float, float] = {
    a.angle: a.default_orb for a in Aspect.ALL
}

# Traditional per-body full orbs (moiety = half of each value).
#
# Source: William Lilly, "Christian Astrology" (1647), Book I, Ch. VI.
# These are the full orbs; the moiety of each planet is orb / 2.
# Combined moiety for a pair = moiety(A) + moiety(B).
#
# Bodies not present in this table (Chiron, nodes, asteroids, calculated
# points) fall back to a default full orb of 5° (moiety 2.5°).
TRADITIONAL_MOIETY_ORBS: dict[str, float] = {
    "Sun":     15.0,   # moiety 7.5°
    "Moon":    12.0,   # moiety 6.0°
    "Mercury":  7.0,   # moiety 3.5°
    "Venus":    7.0,   # moiety 3.5°
    "Mars":     7.0,   # moiety 3.5°
    "Jupiter": 12.0,   # moiety 6.0°
    "Saturn":  10.0,   # moiety 5.0°
}
