"""
Moira — Longevity Engine
=========================

Archetype: Engine

Purpose
-------
Governs traditional Hyleg and Alcocoden longevity calculation, determining
the Giver of Life (Hyleg) and Giver of Years (Alcocoden) from a natal chart
and computing the Ptolemaic years granted based on house placement.

Boundary declaration
--------------------
Owns: Ptolemaic year tables, triplicity ruler table, face ruler sequence,
      dignity scoring, Hyleg determination, Alcocoden identification, and
      the ``HylegResult`` result vessel.
Delegates: sign/house constants to ``moira.constants``,
           domicile/exaltation/house-type constants to ``moira.dignities``,
           Egyptian bounds doctrine to ``moira.egyptian_bounds``.

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required. No database access. Pure computation over
planet position dicts and house cusp lists.

Public surface
--------------
``HylegResult``          — vessel for the full Hyleg/Alcocoden result.
``PTOLEMAIC_YEARS``      — dict of planet to (minor, mean, major) year tuples.
``EGYPTIAN_BOUNDS``      — re-export of the Egyptian bound table.
``FACE_RULERS``          — list of 36 face rulers in Chaldean order.
``dignity_score_at``     — compute total dignity score of a planet at a degree.
``find_hyleg``           — determine the Hyleg using Bonatti's priority order.
``calculate_longevity``  — full Hyleg/Alcocoden longevity calculation.
"""


from dataclasses import dataclass

from .constants import SIGNS
from .egyptian_bounds import EGYPTIAN_BOUNDS
from .dignities import (
    DOMICILE, EXALTATION,
    ANGULAR_HOUSES, SUCCEDENT_HOUSES, CADENT_HOUSES,
    CLASSIC_7,
    SCORE_DOMICILE, SCORE_EXALTATION,
    SCORE_BOUND, SCORE_FACE,
)
from .triplicity import triplicity_score as _triplicity_score, ParticipatingRulerPolicy as _ParticipatingRulerPolicy

__all__ = [
    "HylegResult",
    "PTOLEMAIC_YEARS",
    "EGYPTIAN_BOUNDS",
    "FACE_RULERS",
    "dignity_score_at",
    "find_hyleg",
    "calculate_longevity",
]

# ---------------------------------------------------------------------------
# Ptolemaic Planetary Years
# ---------------------------------------------------------------------------

PTOLEMAIC_YEARS: dict[str, tuple[float, float, float]] = {
    # planet: (minor, mean, major)
    "Sun":     (19.0,  69.5, 120.0),
    "Moon":    (25.0,  66.5, 108.0),
    "Mercury": (20.0,  48.0,  76.0),
    "Venus":   ( 8.0,  45.0,  82.0),
    "Mars":    (15.0,  40.5,  66.0),
    "Jupiter": (12.0,  45.5,  79.0),
    "Saturn":  (30.0,  57.0,  90.0),
}

# ---------------------------------------------------------------------------
# Faces / Decans — Chaldean order starting from Aries 0°
# Each decan is 10°; 36 decans total, repeating the Chaldean sequence:
#   Mars, Sun, Venus, Mercury, Moon, Saturn, Jupiter
# ---------------------------------------------------------------------------

FACE_RULERS: list[str] = (
    [["Mars", "Sun", "Venus", "Mercury", "Moon", "Saturn", "Jupiter"][i % 7] for i in range(36)]
)


# ---------------------------------------------------------------------------
# Helpers: sign & degree-within-sign from ecliptic longitude
# ---------------------------------------------------------------------------

def _sign_and_deg(longitude: float) -> tuple[str, float]:
    """Return (sign_name, degree_within_sign) for a longitude in [0, 360)."""
    lon = longitude % 360.0
    idx = int(lon // 30)
    return SIGNS[idx], lon - idx * 30.0


def _get_house(degree: float, cusps: list[float]) -> int:
    """Return 1-based house number for an ecliptic longitude given 12 cusp longitudes."""
    deg = degree % 360.0
    for i in range(12):
        start = cusps[i]
        end   = cusps[(i + 1) % 12]
        if start <= end:
            if start <= deg < end:
                return i + 1
        else:
            if deg >= start or deg < end:
                return i + 1
    return 1


# ---------------------------------------------------------------------------
# Dignity scoring at a specific degree
# ---------------------------------------------------------------------------

def dignity_score_at(
    planet: str,
    longitude: float,
    is_day_chart: bool,
) -> int:
    """
    Compute the total dignity score of a planet at a given ecliptic longitude.
    Checks: domicile (5), exaltation (4), triplicity (3), bound (2), face (1).

    Parameters
    ----------
    planet       : planet name (Classic 7)
    longitude    : ecliptic longitude to test (degrees)
    is_day_chart : True for diurnal chart (affects triplicity rulership)

    Returns
    -------
    Integer dignity score (0–15 maximum)
    """
    sign, deg_in_sign = _sign_and_deg(longitude)
    score = 0

    # Domicile
    if sign in DOMICILE.get(planet, []):
        score += SCORE_DOMICILE

    # Exaltation
    if sign in EXALTATION.get(planet, []):
        score += SCORE_EXALTATION

    # Triplicity
    score += _triplicity_score(
        planet, sign,
        is_day_chart=is_day_chart,
        participating_policy=_ParticipatingRulerPolicy.AWARD_REDUCED,
    )

    # Egyptian Bound
    bounds = EGYPTIAN_BOUNDS.get(sign, [])
    for ruler, start, end in bounds:
        if start <= deg_in_sign < end and ruler == planet:
            score += SCORE_BOUND
            break

    # Face / Decan
    # Decan index: 0-35 across the zodiac
    lon_norm = longitude % 360.0
    decan_idx = int(lon_norm // 10) % 36
    face_ruler = FACE_RULERS[decan_idx]
    if face_ruler == planet:
        score += SCORE_FACE

    return score


# ---------------------------------------------------------------------------
# Hyleg determination
# ---------------------------------------------------------------------------

def find_hyleg(
    planet_positions: dict[str, float],
    house_cusps: list[float],
    is_day_chart: bool,
) -> str:
    """
    Determine the Hyleg using Bonatti's priority order.

    Priority:
      1. Sun  — in a day chart, if Sun is in the hyleg-eligible zone
                (houses 1, 7–12, or within 5° of the Ascendant/MC)
      2. Moon — in a night chart, or if Sun is ineligible
      3. Ascendant — if neither luminary qualifies
      4. Lot of Fortune — fallback

    Parameters
    ----------
    planet_positions : dict mapping body name → ecliptic longitude (degrees)
    house_cusps      : list of 12 cusp longitudes (0-indexed, cusp[0] = Asc)
    is_day_chart     : True if Sun is above horizon (houses 7–12)

    Returns
    -------
    Hyleg name: "Sun", "Moon", "Ascendant", or "Lot of Fortune"
    """
    sun_lon  = planet_positions.get("Sun",  0.0)
    moon_lon = planet_positions.get("Moon", 0.0)

    sun_house  = _get_house(sun_lon,  house_cusps)
    moon_house = _get_house(moon_lon, house_cusps)

    # Hyleg-eligible houses: angular or succedent (not cadent)
    # Bonatti: Sun must be in an angular or succedent house to be hyleg
    ELIGIBLE_HOUSES = ANGULAR_HOUSES | SUCCEDENT_HOUSES  # {1,2,4,5,7,8,10,11}

    if is_day_chart and sun_house in ELIGIBLE_HOUSES:
        return "Sun"

    if not is_day_chart and moon_house in ELIGIBLE_HOUSES:
        return "Moon"

    # If neither luminary is eligible, try the other luminary regardless of sect
    if moon_house in ELIGIBLE_HOUSES:
        return "Moon"
    if sun_house in ELIGIBLE_HOUSES:
        return "Sun"

    # Ascendant as third choice
    if house_cusps:
        return "Ascendant"

    # Lot of Fortune as ultimate fallback
    return "Lot of Fortune"


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class HylegResult:
    """
    RITE: The Longevity Vessel — the verdict of life's appointed guardians.

    THEOREM: Holds the identified Hyleg point, Alcocoden planet, dignity score,
    Ptolemaic year set, house placement, and the granted years for a single
    Hyleg/Alcocoden longevity calculation.

    RITE OF PURPOSE:
        Serves the Longevity Engine as the canonical result vessel for the
        full Hyleg/Alcocoden calculation. Without this vessel, callers would
        receive scattered floats with no context linking the Hyleg point to
        its Alcocoden, dignity score, and granted years, making traditional
        longevity interpretation impossible.

    LAW OF OPERATION:
        Responsibilities:
            - Store the Hyleg name and longitude, Alcocoden name and dignity
              score, all three Ptolemaic year values, the Alcocoden's house,
              and the granted years based on house placement.
        Non-responsibilities:
            - Does not perform the calculation (delegated to
              ``calculate_longevity``).
            - Does not validate that ``granted_years`` matches the house type.
        Dependencies:
            - Populated exclusively by ``calculate_longevity()``.
        Structural invariants:
            - ``granted_years`` is always one of ``years_minor``,
              ``years_mean``, or ``years_major``.
            - ``house`` is always in [1, 12].
        Succession stance: terminal — not designed for subclassing.

    Canon: Bonatti, "Book of Astronomy" Treatise 5;
           al-Qabisi, "Introduction to Astrology";
           Abu Ma'shar, "Great Introduction".

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.longevity.HylegResult",
        "risk": "medium",
        "api": {
            "public_methods": ["__repr__"],
            "public_attributes": [
                "hyleg", "hyleg_lon", "alcocoden", "alcocoden_score",
                "years_minor", "years_mean", "years_major",
                "house", "granted_years"
            ]
        },
        "state": {
            "mutable": false,
            "fields": [
                "hyleg", "hyleg_lon", "alcocoden", "alcocoden_score",
                "years_minor", "years_mean", "years_major",
                "house", "granted_years"
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
            "policy": "caller ensures valid planet positions and house cusps"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]
    """

    hyleg:             str    # "Sun", "Moon", "Ascendant", "Lot of Fortune"
    hyleg_lon:         float  # ecliptic longitude of the hyleg point
    alcocoden:         str    # planet name
    alcocoden_score:   int    # dignity score at hyleg degree
    years_minor:       float
    years_mean:        float
    years_major:       float
    house:             int    # alcocoden's house
    granted_years:     float  # years granted based on house placement

    def __repr__(self) -> str:
        return (
            f"HylegResult("
            f"hyleg={self.hyleg!r} ({self.hyleg_lon:.2f}°), "
            f"alcocoden={self.alcocoden!r} [score={self.alcocoden_score}] "
            f"H{self.house}, "
            f"years=(minor={self.years_minor}, mean={self.years_mean}, "
            f"major={self.years_major}), "
            f"granted={self.granted_years})"
        )


# ---------------------------------------------------------------------------
# Main calculation
# ---------------------------------------------------------------------------

def calculate_longevity(
    planet_positions: dict[str, float],
    house_cusps: list[float],
    is_day_chart: bool,
) -> HylegResult:
    """
    Full Hyleg / Alcocoden longevity calculation.

    Parameters
    ----------
    planet_positions : dict mapping body name → ecliptic longitude (degrees).
                       Should include at minimum the Classic 7 planets plus
                       "Ascendant" and optionally "Lot of Fortune".
    house_cusps      : list of 12 cusp longitudes (0-indexed; cusps[0] = Asc)
    is_day_chart     : True when the Sun is above the horizon (houses 7–12)

    Returns
    -------
    HylegResult with hyleg, alcocoden, Ptolemaic years, and granted years.

    Algorithm
    ---------
    1. Determine the Hyleg (Bonatti priority order).
    2. Resolve the hyleg's longitude.
       - If "Ascendant", use house_cusps[0].
       - If "Lot of Fortune", use planet_positions.get("Lot of Fortune", cusps[0]).
    3. For each Classic 7 planet, compute its dignity score at the hyleg degree.
    4. The planet with the highest score is the Alcocoden.
    5. Look up the Alcocoden's house and the corresponding Ptolemaic years
       (minor for cadent, mean for succedent, major for angular).
    """
    # --- Step 1: Find the Hyleg ---
    hyleg_name = find_hyleg(planet_positions, house_cusps, is_day_chart)

    # --- Step 2: Resolve hyleg longitude ---
    if hyleg_name == "Ascendant":
        hyleg_lon = house_cusps[0] if house_cusps else 0.0
    elif hyleg_name == "Lot of Fortune":
        hyleg_lon = planet_positions.get("Lot of Fortune",
                                         house_cusps[0] if house_cusps else 0.0)
    else:
        hyleg_lon = planet_positions.get(hyleg_name, 0.0)

    # --- Step 3: Score every Classic 7 planet at the hyleg degree ---
    scores: dict[str, int] = {}
    for planet in CLASSIC_7:
        if planet in planet_positions:
            scores[planet] = dignity_score_at(planet, hyleg_lon, is_day_chart)

    # --- Step 4: Identify the Alcocoden (highest scorer) ---
    if not scores:
        # Fallback: use the sign ruler of the hyleg degree
        sign, _ = _sign_and_deg(hyleg_lon)
        alcocoden = next(
            (p for p, signs in DOMICILE.items() if sign in signs),
            "Sun"
        )
        alcocoden_score = 0
    else:
        # Tiebreak by classical planet order: Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn
        _ORDER = ["Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"]
        alcocoden = max(
            scores,
            key=lambda p: (scores[p], -(_ORDER.index(p) if p in _ORDER else 99)),
        )
        alcocoden_score = scores[alcocoden]

    # --- Step 5: Look up Ptolemaic years ---
    minor, mean, major = PTOLEMAIC_YEARS.get(alcocoden, (0.0, 0.0, 0.0))

    # --- Step 6: Determine Alcocoden's house and granted years ---
    alcocoden_lon = planet_positions.get(alcocoden, 0.0)
    alcocoden_house = _get_house(alcocoden_lon, house_cusps) if house_cusps else 1

    if alcocoden_house in ANGULAR_HOUSES:
        granted = major
    elif alcocoden_house in SUCCEDENT_HOUSES:
        granted = mean
    else:  # cadent
        granted = minor

    return HylegResult(
        hyleg=hyleg_name,
        hyleg_lon=hyleg_lon,
        alcocoden=alcocoden,
        alcocoden_score=alcocoden_score,
        years_minor=minor,
        years_mean=mean,
        years_major=major,
        house=alcocoden_house,
        granted_years=granted,
    )
