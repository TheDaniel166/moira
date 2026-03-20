"""
Moira — Aspect Engine
======================

Archetype: Engine

Purpose
-------
Governs detection of ecliptic aspects and declination aspects between
planetary positions, producing structured result vessels with orb,
applying/separating status, and stationary flags.

Boundary declaration
--------------------
Owns: aspect detection logic, orb arithmetic, applying/separating
      determination, stationary detection, and the ``AspectData`` and
      ``DeclinationAspect`` result vessels.
Delegates: aspect definition tables and tier lists to ``moira.constants``,
           angular distance arithmetic to ``moira.coordinates``.

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required. No database access. Pure computation over
position and speed dicts.

Public surface
--------------
``AspectData``               — vessel for a detected ecliptic aspect.
``DeclinationAspect``        — vessel for a parallel or contra-parallel aspect.
``find_aspects``             — find all aspects in a position dict.
``aspects_between``          — find aspects between two specific bodies.
``aspects_to_point``         — find aspects from a body set to a single point.
``find_declination_aspects`` — find parallels and contra-parallels.
"""

from dataclasses import dataclass, field

from .constants import Aspect, AspectDefinition, ASPECT_TIERS, DEFAULT_ORBS
from .coordinates import angular_distance


@dataclass(slots=True)
class AspectData:
    """
    RITE: The Aspect Vessel — a detected angular relationship between two bodies.

    THEOREM: Holds the two body names, aspect name and symbol, exact angle,
    orb, applying/separating flag, and stationary flag for a single detected
    ecliptic aspect.

    RITE OF PURPOSE:
        Serves the Aspect Engine as the canonical result vessel for all
        ecliptic aspect detections. Without this vessel, callers would receive
        raw orb floats with no aspect name, symbol, or motion context, making
        chart display, aspect filtering, and applying/separating analysis
        impossible.

    LAW OF OPERATION:
        Responsibilities:
            - Store both body names, aspect name, Unicode symbol, exact angle,
              orb (always positive), applying/separating flag, and stationary
              flag.
        Non-responsibilities:
            - Does not detect aspects (delegated to ``find_aspects`` and
              related functions).
            - Does not compute angular distances.
        Dependencies:
            - Populated by ``find_aspects()``, ``aspects_between()``, or
              ``aspects_to_point()``.
        Structural invariants:
            - ``orb`` is always non-negative.
            - ``applying`` is ``None`` when either body is stationary or
              speeds are unavailable.
            - ``stationary`` is ``True`` when either body's speed is below
              0.01 deg/day.
        Succession stance: terminal — not designed for subclassing.

    Canon: Ptolemy, "Tetrabiblos" I; Lilly, "Christian Astrology" (1647).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.aspects.AspectData",
        "risk": "high",
        "api": {
            "public_methods": ["__repr__"],
            "public_attributes": [
                "body1", "body2", "aspect", "symbol",
                "angle", "orb", "applying", "stationary"
            ]
        },
        "state": {
            "mutable": false,
            "fields": [
                "body1", "body2", "aspect", "symbol",
                "angle", "orb", "applying", "stationary"
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
            "policy": "caller ensures valid positions before construction"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]
    """
    body1:      str           # name of first body
    body2:      str           # name of second body
    aspect:     str           # aspect name e.g. "Trine"
    symbol:     str           # Unicode glyph e.g. "△"
    angle:      float         # exact aspect angle (e.g. 120.0)
    orb:        float         # degrees from exact (always positive)
    applying:   bool | None = None   # True=applying, False=separating, None=unknown
    stationary: bool        = False  # True when either body's speed is < 0.01°/day

    def __repr__(self) -> str:
        app = " applying" if self.applying else " separating" if self.applying is False else ""
        sta = " [stationary]" if self.stationary else ""
        return f"{self.body1} {self.symbol} {self.body2}  (orb {self.orb:+.2f}°){app}{sta}"


@dataclass(slots=True)
class DeclinationAspect:
    """
    RITE: The Declination Vessel — a parallel or contra-parallel between two bodies.

    THEOREM: Holds the two body names, aspect type, individual declinations,
    and orb for a single detected parallel or contra-parallel declination aspect.

    RITE OF PURPOSE:
        Serves the Aspect Engine as the canonical result vessel for declination
        aspect detections. Parallels and contra-parallels operate in the
        declination dimension rather than the ecliptic longitude dimension.
        Without this vessel, declination aspects would have no structured
        representation separate from ecliptic aspects.

    LAW OF OPERATION:
        Responsibilities:
            - Store both body names, aspect type ("Parallel" or
              "Contra-Parallel"), individual signed declinations, and orb.
        Non-responsibilities:
            - Does not detect declination aspects (delegated to
              ``find_declination_aspects``).
            - Does not compute declinations from ecliptic coordinates.
        Dependencies:
            - Populated exclusively by ``find_declination_aspects()``.
        Structural invariants:
            - ``aspect`` is always "Parallel" or "Contra-Parallel".
            - ``orb`` is always non-negative.
            - ``dec1`` and ``dec2`` are always in [-90, +90].
        Succession stance: terminal — not designed for subclassing.

    Canon: Ptolemy, "Tetrabiblos" I; Lilly, "Christian Astrology" (1647).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.aspects.DeclinationAspect",
        "risk": "high",
        "api": {
            "public_methods": ["__repr__"],
            "public_attributes": ["body1", "body2", "aspect", "dec1", "dec2", "orb"]
        },
        "state": {
            "mutable": false,
            "fields": ["body1", "body2", "aspect", "dec1", "dec2", "orb"]
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
            "policy": "caller ensures valid declinations before construction"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]
    """
    body1:  str
    body2:  str
    aspect: str    # "Parallel" or "Contra-Parallel"
    dec1:   float  # declination of body1 (degrees, signed, ±90)
    dec2:   float  # declination of body2 (degrees, signed, ±90)
    orb:    float  # |difference| in degrees

    def __repr__(self) -> str:
        return f"{self.body1} ∥ {self.body2}  (orb {self.orb:+.2f}°) [{self.aspect}]"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_aspects(
    tier: int | None,
    include_minor: bool,
) -> list[AspectDefinition]:
    """Return the aspect list for the given tier / include_minor flag."""
    if tier is not None:
        return ASPECT_TIERS.get(tier, Aspect.MAJOR)
    return Aspect.MAJOR + Aspect.COMMON_MINOR if include_minor else Aspect.MAJOR


_STATIONARY_THRESHOLD = 0.005  # degrees/day — below this a planet is considered stationary


def _applying(
    b1: str, lon1: float,
    b2: str, lon2: float,
    speeds: dict[str, float],
) -> bool | None:
    """
    True = applying, False = separating, None = unknown or stationary.

    Returns None when either body's daily speed is below the stationary
    threshold (< 0.005°/day), because the applying/separating distinction
    is not meaningful for a body that is effectively motionless.
    """
    if b1 not in speeds or b2 not in speeds:
        return None
    # Stationary planet: neither applying nor separating in a meaningful sense
    if abs(speeds.get(b1, 1.0)) < _STATIONARY_THRESHOLD or abs(speeds.get(b2, 1.0)) < _STATIONARY_THRESHOLD:
        return None
    relative_speed = speeds[b1] - speeds[b2]
    diff = (lon2 - lon1 + 180.0) % 360.0 - 180.0
    return relative_speed > 0 if diff > 0 else relative_speed < 0


def _is_stationary(b1: str, b2: str, speeds: dict[str, float]) -> bool:
    """Return True when either body's speed is below 0.01°/day."""
    _STAT_BROAD = 0.01
    return (abs(speeds.get(b1, 1.0)) < _STAT_BROAD
            or abs(speeds.get(b2, 1.0)) < _STAT_BROAD)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def find_aspects(
    positions: dict[str, float],
    orbs: dict[float, float] | None = None,
    include_minor: bool = True,
    speeds: dict[str, float] | None = None,
    tier: int | None = None,
    orb_factor: float = 1.0,
) -> list[AspectData]:
    """
    Find all aspects between a set of planetary longitudes.

    Parameters
    ----------
    positions    : dict mapping body name → ecliptic longitude (degrees)
    orbs         : custom orb table {angle: max_orb}. When provided,
                   overrides both tier defaults and orb_factor.
    include_minor: include common minor aspects (ignored when tier is set)
    speeds       : dict mapping body name → daily speed (degrees/day).
                   Required for accurate applying/separating detection.
    tier         : 0=Major, 1=Major+Common Minor, 2=All minor.
                   Overrides include_minor when set.
    orb_factor   : multiplier applied to all default orbs (e.g. 0.5 = tight).
                   Ignored when custom orbs dict is provided.

    Returns
    -------
    List of AspectData sorted by orb (tightest first)
    """
    aspect_list = _resolve_aspects(tier, include_minor)
    bodies = list(positions.keys())
    results: list[AspectData] = []

    for i in range(len(bodies)):
        for j in range(i + 1, len(bodies)):
            b1, b2 = bodies[i], bodies[j]
            lon1, lon2 = positions[b1], positions[b2]
            sep = angular_distance(lon1, lon2)

            for adef in aspect_list:
                if orbs is not None:
                    allowed = orbs.get(adef.angle, adef.default_orb)
                else:
                    allowed = adef.default_orb * orb_factor
                orb = abs(sep - adef.angle)
                if orb <= allowed:
                    app = _applying(b1, lon1, b2, lon2, speeds) if speeds else None
                    sta = _is_stationary(b1, b2, speeds) if speeds else False
                    results.append(AspectData(
                        body1=b1, body2=b2,
                        aspect=adef.name, symbol=adef.symbol,
                        angle=adef.angle, orb=orb,
                        applying=app,
                        stationary=sta,
                    ))

    results.sort(key=lambda a: a.orb)
    return results


def aspects_between(
    body_a: str,
    lon_a: float,
    body_b: str,
    lon_b: float,
    tier: int = 2,
    orbs: dict[float, float] | None = None,
    orb_factor: float = 1.0,
    speed_a: float | None = None,
    speed_b: float | None = None,
) -> list[AspectData]:
    """
    Find all aspects between two specific bodies.

    Parameters
    ----------
    body_a / lon_a : first body name and longitude
    body_b / lon_b : second body name and longitude
    tier           : aspect set (default 2 = all aspects)
    orbs           : custom orb table
    orb_factor     : multiplier for default orbs
    speed_a / speed_b : daily motion (for applying/separating)

    Returns
    -------
    List of AspectData sorted by orb
    """
    aspect_list = ASPECT_TIERS.get(tier, Aspect.ALL)
    sep = angular_distance(lon_a, lon_b)
    results: list[AspectData] = []

    speeds = {}
    if speed_a is not None:
        speeds[body_a] = speed_a
    if speed_b is not None:
        speeds[body_b] = speed_b

    for adef in aspect_list:
        if orbs is not None:
            allowed = orbs.get(adef.angle, adef.default_orb)
        else:
            allowed = adef.default_orb * orb_factor
        orb = abs(sep - adef.angle)
        if orb <= allowed:
            app = _applying(body_a, lon_a, body_b, lon_b, speeds) if speeds else None
            sta = _is_stationary(body_a, body_b, speeds) if speeds else False
            results.append(AspectData(
                body1=body_a, body2=body_b,
                aspect=adef.name, symbol=adef.symbol,
                angle=adef.angle, orb=orb,
                applying=app,
                stationary=sta,
            ))

    results.sort(key=lambda a: a.orb)
    return results


def aspects_to_point(
    point_longitude: float,
    positions: dict[str, float],
    point_name: str = "Point",
    orbs: dict[float, float] | None = None,
    include_minor: bool = True,
    tier: int | None = None,
    orb_factor: float = 1.0,
) -> list[AspectData]:
    """
    Find all aspects from a set of planets to a single point longitude.

    Useful for transits, progressions, and fixed star contacts.

    Parameters
    ----------
    point_longitude : target ecliptic longitude (degrees)
    positions       : dict of body name → longitude
    point_name      : label for the target point in AspectData.body2
    orbs            : custom orb table
    include_minor   : include common minor aspects (ignored when tier is set)
    tier            : 0/1/2 aspect tier
    orb_factor      : multiplier for default orbs
    """
    aspect_list = _resolve_aspects(tier, include_minor)
    results: list[AspectData] = []

    for body, lon in positions.items():
        sep = angular_distance(lon, point_longitude)
        for adef in aspect_list:
            if orbs is not None:
                allowed = orbs.get(adef.angle, adef.default_orb)
            else:
                allowed = adef.default_orb * orb_factor
            orb = abs(sep - adef.angle)
            if orb <= allowed:
                results.append(AspectData(
                    body1=body, body2=point_name,
                    aspect=adef.name, symbol=adef.symbol,
                    angle=adef.angle, orb=orb,
                    applying=None,
                ))

    results.sort(key=lambda a: a.orb)
    return results


# ---------------------------------------------------------------------------
# Declination aspects: parallels and contra-parallels
# ---------------------------------------------------------------------------

def find_declination_aspects(
    declinations: dict[str, float],
    orb: float = 1.0,
) -> list[DeclinationAspect]:
    """
    Find parallel and contra-parallel aspects from a dict of declinations.

    Parallel:        |dec_A − dec_B| <= orb    (both bodies on the same side of
                     the celestial equator, within *orb* degrees of each other)
    Contra-Parallel: |dec_A + dec_B| <= orb    (bodies on opposite sides, their
                     absolute declinations within *orb* degrees of each other)

    Parameters
    ----------
    declinations : dict mapping body name → signed declination in degrees (±90)
    orb          : maximum orb in degrees (default 1.0°)

    Returns
    -------
    List of DeclinationAspect sorted by orb (tightest first)
    """
    bodies = list(declinations.keys())
    results: list[DeclinationAspect] = []

    for i in range(len(bodies)):
        for j in range(i + 1, len(bodies)):
            b1, b2 = bodies[i], bodies[j]
            d1, d2 = declinations[b1], declinations[b2]

            # Parallel: same-sign declinations that are close in value
            parallel_diff = abs(d1 - d2)
            if parallel_diff <= orb:
                results.append(DeclinationAspect(
                    body1=b1, body2=b2,
                    aspect="Parallel",
                    dec1=d1, dec2=d2,
                    orb=parallel_diff,
                ))

            # Contra-Parallel: opposite-sign declinations whose magnitudes are close
            contra_diff = abs(d1 + d2)
            if contra_diff <= orb:
                results.append(DeclinationAspect(
                    body1=b1, body2=b2,
                    aspect="Contra-Parallel",
                    dec1=d1, dec2=d2,
                    orb=contra_diff,
                ))

    results.sort(key=lambda a: a.orb)
    return results
