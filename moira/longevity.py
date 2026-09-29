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
``find_hyleg``           — legacy Moira hyleg rule (house set not sourced; see its docstring).
``calculate_longevity``  — full Hyleg/Alcocoden longevity calculation (legacy rule).
``find_hyleg_lilly_1647`` — Hyleg per Lilly, Christian Astrology (1647) III ch. CIV
                           (luminary step; fails closed where the source step
                           is not admitted).
``HylegDoctrine``, ``HylegStatus``, ``HylegiacalPlaceTruth``,
``HylegDetermination``   — typed vessels for ``find_hyleg_lilly_1647``.
``find_alcocoden_lilly_1647`` — Alcocoden per Lilly III ch. CIV: the planet with
                           most essential dignity in the hyleg's place among
                           those that behold it (``AlcocodenDetermination``).
"""

from __future__ import annotations


import math
from dataclasses import dataclass

from ._strenum import StrEnum
from .constants import SIGNS
from .egyptian_bounds import EGYPTIAN_BOUNDS
from .dignities import (
    DOMICILE, EXALTATION,
    ANGULAR_HOUSES, SUCCEDENT_HOUSES, CLASSIC_7,
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
    "HylegDoctrine",
    "HylegStatus",
    "HylegiacalPlaceTruth",
    "HylegDetermination",
    "HylegDominionCount",
    "find_hyleg_lilly_1647",
    "LILLY_1647_PLANET_ORBS",
    "AlcocodenStatus",
    "AlcocodenCandidate",
    "AlcocodenDetermination",
    "find_alcocoden_lilly_1647",
]

# ---------------------------------------------------------------------------
# Ptolemaic Planetary Years
# ---------------------------------------------------------------------------

# The least, mean and greater years of the planets, as Lilly prints them in
# each planet's chapter of Christian Astrology (1647), Book I chs. VIII-XIV
# (pp. 57-83; Lilly points back to "pag. 57. to 83." in III ch. CIV, p. 530):
#   Saturn  (ch. VIII,  p. 60)  greater 57, mean 43 and a half, least 30
#   Jupiter (ch. IX)            greater 79, mean 45, least 12
#   Mars    (ch. X)             greater 66, mean 40, least 15
#   Sun     (ch. XI)            greater 120, mean 69, least 19
#   Venus   (ch. XII)           greater 82, mean 45, least 8
#   Mercury (ch. XIII)          greater 76, mean 48, least 20
#   Moon    (ch. XIV)           greater 108, mean 66, least 25
# Read from three independent witnesses: the 1647 OCR, the Mithras93
# transcription of vol. 1, and the Astrology Classics edition. Lilly prints
# whole mean years for Jupiter, Mars, Sun and Moon (not the half-years that
# the arithmetic mean of greater and least would give); Saturn alone has
# "43 and a half". Before Moira 6.9.9 Saturn was (30, 57, 90) and the other
# four means carried an unprinted half-year. The name PTOLEMAIC_YEARS is
# historical; Ptolemy does not give these tables.
PTOLEMAIC_YEARS: dict[str, tuple[float, float, float]] = {
    # planet: (minor, mean, major)
    "Sun":     (19.0,  69.0, 120.0),
    "Moon":    (25.0,  66.0, 108.0),
    "Mercury": (20.0,  48.0,  76.0),
    "Venus":   ( 8.0,  45.0,  82.0),
    "Mars":    (15.0,  40.0,  66.0),
    "Jupiter": (12.0,  45.0,  79.0),
    "Saturn":  (30.0,  43.5,  57.0),
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
    Legacy Moira hyleg rule (kept for compatibility; not a sourced doctrine).

    Rule as implemented: the sect light if it is in an angular or succedent
    house (1, 2, 4, 5, 7, 8, 10, 11); else the other luminary in such a house;
    else "Ascendant" whenever cusps are supplied. This house set is not
    traced to Bonatti or any located source, and it contradicts Lilly
    (Christian Astrology, 1647, III ch. CIV), who admits only houses 1, 10,
    11, 7 and 9, rejects the 8th and 12th, and rejects places under the earth
    beyond 25° of the Ascendant. Use ``find_hyleg_lilly_1647`` for a sourced
    determination.

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

    Canon: none verified. The hyleg step is the legacy ``find_hyleg`` rule
           (not sourced); the alcocoden is the highest ``dignity_score_at``
           scorer at the hyleg degree with no aspect condition (Lilly III ch.
           CIV requires the alcocoden to behold the hyleg); planetary years
           per PTOLEMAIC_YEARS (Lilly 1647, Book I).

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
    Legacy Moira Hyleg / Alcocoden longevity calculation (kept for
    compatibility; not a sourced doctrine).

    The hyleg is the legacy ``find_hyleg`` rule; the alcocoden is the highest
    ``dignity_score_at`` scorer at the hyleg degree (Egyptian bounds,
    Dorothean triplicity with a 1-point participating ruler) with NO aspect
    condition, although Lilly (Christian Astrology 1647, III ch. CIV, p. 530)
    requires the alcocoden to behold the hyleg; and the granted years follow
    an angular/succedent/cadent rule that Lilly does not give. Use
    ``find_alcocoden_lilly_1647`` for the sourced determination. The year
    values themselves are Lilly's (``PTOLEMAIC_YEARS``).

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
    1. Determine the Hyleg (legacy ``find_hyleg`` rule; house set unsourced).
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


# ---------------------------------------------------------------------------
# Hyleg — William Lilly, Christian Astrology (1647), Book III ch. CIV
# ---------------------------------------------------------------------------
#
# Source: Lilly, *Christian Astrology* (London, 1647), Book III ch. CIV "Of
# the Prorogator of Life, called Hylech, or Hyleg, or Apheta", pp. 527–529.
#
#   "in a Diurnall geniture, take the Sun; in a Nocturnall, the Moon; and if
#   either of them be in convenient Hylegiacall places, they shall be Hylech:
#   ... when they be either in the first, tenth, eleventh, seventh or ninth
#   houses, or within the Orbs of the houses; what space of the Æquator is
#   under the earth is rejected, unlesse within five and twenty degrees of the
#   ascendant ... the eighth house and twelfth are in this judgment rejected."
#   "If the Sun, by reason of his ill position, is not capable of being Hyleg,
#   then see if the Moon may be admitted; which if not, then ..." the planet
#   with most dignities in the places of the luminary, the preceding
#   syzygy, and the Ascendant, if it is in an hylegiacal house; else the
#   Ascendant.
#
# The dominion step (pp. 528-529): "consider if the geniture be diurnall,
# and whether a new [Moon] did precede the Nativity; but in a nocturnall,
# observe the full [Moon] going before the Birth: see also ... what Planet
# hath most dignities, at least three essentiall fortitudes, in the place of
# the [Sun], in the [conjunction] or [opposition] preceding ... examine which
# of the Planets hath most dignities in these three places, and is also
# constituted in an Hylegiacall house; I say, that Planet may well be
# appointed Hyleg; but if the Planet who hath most dignities in the places
# aforesaid, be not in an apt house, then simply ... let the Horoscope be
# Hyleg." "Besides, observe in diurnall genitures that you must ever regard
# the degree of the Ecliptick wherein the new [Moon] was before the Birth,
# though a full [Moon] intervened". "In nocturnall genitures, take that
# Planet who hath power by his essentiall dignities in these three places,
# viz. Place of the [Moon] at Birth. Place of the [opposition] preceding.
# Place of [the Part of Fortune] at the Birth. For if such a Planet be in an
# Apheticall place, he shall be Prorogator; but if not so, then, if a new
# [Moon] preceded, take the ascendant; if an [opposition], take the
# [Part of Fortune], if it be in an Apheticall place, else take the
# ascendant."
#
# Admitted here (explicit ambiguity policy):
#   * House orb: Lilly, CA Book I ch. IV (pp. 31-32): a planet "within five
#     degrees of the Cusp of any house, his vertue shall be assigned to that
#     house". A luminary within 5° of ecliptic longitude before a cusp is
#     counted in that house.
#   * Under the earth: in a quadrant house figure the points of houses 1–6
#     are below the horizon. Such a luminary qualifies only in the 1st house
#     and only if the arc of the equator between the Ascendant and the
#     luminary's ecliptic degree, measured in oblique ascension at the
#     birthplace latitude, is at most 25°. The luminary's ecliptic latitude
#     is ignored (its zodiacal degree is used).
#   * Luminaries: the sect light if hylegiacal, else the other luminary if
#     hylegiacal. By night the Sun is admitted after the Moon: Lilly's own
#     nocturnal example prefers the Sun in the ascendant to the Moon
#     ("in the nocturnall genitures, let the [Moon] be in the ninth or
#     seventh, but the [Sun] in the ascendant, then the [Sun] is preferred",
#     p. 529), and Ptolemy III.10, which this chapter follows, orders "by
#     night ... the moon first, next the sun".
#   * When both luminaries are hylegiacal, the sect light is taken, as in
#     Lilly's opening rule; the preference "of greater vertue" that Lilly
#     reports from the Ancients is not mechanised and is flagged instead.
#   * Dominion places: by day the Sun, the preceding new Moon (always the new
#     Moon, "though a full [Moon] intervened") and the Ascendant; by night the
#     Moon, the preceding full Moon and the Part of Fortune (Lilly's own list
#     of "these three places"; Fortune is Asc + Moon - Sun by day and night,
#     Book I p. 143). A parenthesis on p. 529 names the night places as the
#     opposition, the Moon and the ascendant; the explicit list is followed.
#   * "Most dignities, at least three essentiall fortitudes": each planet's
#     essential dignities in the three places by Lilly's table (p. 104) and
#     scale (p. 115). A planet qualifies with at least three essential
#     dignities counted over the three places; the qualifying planet with the
#     most points is taken. A tie in points is NOT_EVALUABLE
#     (``dominion_tie``); Lilly gives no tie-break here.
#   * "Constituted in an Hylegiacall house" / "in an Apheticall place": the
#     same place test as for the luminaries.
#   * If no planet qualifies, or the top planet is not in a hylegiacal place:
#     by day the Ascendant; by night the Ascendant after a new Moon, the Part
#     of Fortune after a full Moon if it is in a hylegiacal place, else the
#     Ascendant.
#   * Inputs: the five planets, the preceding new Moon (day) or full Moon
#     (night) longitude, and by night which syzygy came last, are needed only
#     when the dominion step is reached; if missing then the result is
#     NOT_EVALUABLE with a ``*_required`` reason.

HYLEG_LILLY_HYLEGIACAL_HOUSES: frozenset[int] = frozenset({1, 7, 9, 10, 11})
HYLEG_LILLY_CUSP_ORB_DEG: float = 5.0
HYLEG_LILLY_UNDER_EARTH_LIMIT_DEG: float = 25.0


class HylegDoctrine(StrEnum):
    """Named hyleg doctrines admitted by the engine."""

    WILLIAM_LILLY_1647 = "william_lilly_1647"


class HylegStatus(StrEnum):
    """Outcome of a hyleg determination."""

    SELECTED = "selected"
    NOT_EVALUABLE = "not_evaluable"


@dataclass(frozen=True, slots=True)
class HylegiacalPlaceTruth:
    """Whether one luminary stands in a hylegiacal place, and why."""

    body: str
    longitude: float
    strict_house: int
    orb_house: int
    above_horizon: bool
    oblique_ascension_below_ascendant_deg: float | None
    is_hylegiacal: bool
    reason: str


@dataclass(frozen=True, slots=True)
class HylegDominionCount:
    """One planet's essential dignities in the three dominion places (Lilly)."""

    planet: str
    dignities_by_place: tuple[tuple[str, tuple[str, ...]], ...]
    dignity_count: int
    points: int
    qualifies: bool


@dataclass(frozen=True, slots=True)
class HylegDetermination:
    """Hyleg under a named doctrine; ``hyleg`` is None when not evaluable.

    ``hyleg`` names a luminary, a planet, "Ascendant" or "Part of Fortune";
    ``selection_step`` says which of Lilly's steps chose it.
    """

    doctrine: HylegDoctrine
    status: HylegStatus
    hyleg: str | None
    is_day_chart: bool
    candidates: tuple[HylegiacalPlaceTruth, ...]
    both_luminaries_hylegiacal: bool
    reason: str | None
    selection_step: str | None = None
    hyleg_longitude: float | None = None
    dominion_places: tuple[tuple[str, float], ...] = ()
    dominion_counts: tuple[HylegDominionCount, ...] = ()
    dominion_planet: str | None = None
    dominion_planet_place: HylegiacalPlaceTruth | None = None
    part_of_fortune_place: HylegiacalPlaceTruth | None = None

    def __post_init__(self) -> None:
        if self.status is HylegStatus.SELECTED and self.hyleg is None:
            raise ValueError("selected HylegDetermination must name a hyleg")
        if self.status is HylegStatus.NOT_EVALUABLE and (
            self.hyleg is not None or not self.reason
        ):
            raise ValueError("not_evaluable HylegDetermination needs a reason and no hyleg")


def _oblique_ascension(longitude: float, obliquity: float, latitude: float) -> float:
    """Oblique ascension (degrees) of an ecliptic point at geographic latitude.

    Right ascension α and declination δ of the ecliptic point λ (β = 0) under
    obliquity ε, then OA = α − AD with the ascensional difference
    AD = asin(tan φ · tan δ).
    """
    lam = math.radians(longitude)
    eps = math.radians(obliquity)
    phi = math.radians(latitude)
    ra = math.degrees(math.atan2(math.sin(lam) * math.cos(eps), math.cos(lam))) % 360.0
    dec = math.asin(math.sin(eps) * math.sin(lam))
    arg = math.tan(phi) * math.tan(dec)
    if not -1.0 <= arg <= 1.0:
        raise ValueError(
            "ecliptic degree is circumpolar at this latitude; oblique ascension undefined"
        )
    return (ra - math.degrees(math.asin(arg))) % 360.0


def _lilly_place_truth(
    body: str,
    longitude: float,
    house_cusps: list[float],
    *,
    armc: float | None,
    obliquity: float | None,
    geographic_latitude: float | None,
) -> HylegiacalPlaceTruth:
    lon = longitude % 360.0
    strict_house = _get_house(lon, house_cusps)
    next_cusp = house_cusps[strict_house % 12]
    distance_to_next = (next_cusp - lon) % 360.0
    orb_house = (
        (strict_house % 12) + 1
        if distance_to_next <= HYLEG_LILLY_CUSP_ORB_DEG
        else strict_house
    )
    above = strict_house >= 7

    def truth(is_hyl: bool, reason: str, oa_below: float | None = None) -> HylegiacalPlaceTruth:
        return HylegiacalPlaceTruth(
            body=body,
            longitude=lon,
            strict_house=strict_house,
            orb_house=orb_house,
            above_horizon=above,
            oblique_ascension_below_ascendant_deg=oa_below,
            is_hylegiacal=is_hyl,
            reason=reason,
        )

    if orb_house not in HYLEG_LILLY_HYLEGIACAL_HOUSES:
        return truth(False, f"house_{orb_house}_not_hylegiacal")
    if above:
        return truth(True, f"house_{orb_house}_above_horizon")
    if orb_house != 1:
        return truth(False, "under_the_earth")
    if armc is None or obliquity is None or geographic_latitude is None:
        raise ValueError(
            f"{body} is under the earth in the 1st house: armc, obliquity and "
            "geographic_latitude are required for Lilly's 25-degree equatorial limit"
        )
    asc_oa = (armc + 90.0) % 360.0
    body_oa = _oblique_ascension(lon, obliquity, geographic_latitude)
    below = (body_oa - asc_oa) % 360.0
    if below <= HYLEG_LILLY_UNDER_EARTH_LIMIT_DEG:
        return truth(True, "first_house_within_25_equatorial_degrees_of_ascendant", below)
    return truth(False, "first_house_beyond_25_equatorial_degrees_of_ascendant", below)


_HYLEG_DOMINION_PLANETS: tuple[str, ...] = (
    "Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn",
)
_HYLEG_DOMINION_MIN_DIGNITIES = 3


def find_hyleg_lilly_1647(
    sun_longitude: float,
    moon_longitude: float,
    house_cusps: list[float],
    is_day_chart: bool,
    *,
    armc: float | None = None,
    obliquity: float | None = None,
    geographic_latitude: float | None = None,
    planet_positions: dict[str, float] | None = None,
    prenatal_new_moon_longitude: float | None = None,
    prenatal_full_moon_longitude: float | None = None,
    latest_prenatal_syzygy: str | None = None,
) -> HylegDetermination:
    """
    Hyleg by Lilly, *Christian Astrology* (1647) III ch. CIV, pp. 527-529.

    See the doctrine note above ``HYLEG_LILLY_HYLEGIACAL_HOUSES`` for the
    admitted rules, including the dominion step and the Ascendant / Part of
    Fortune final resort.

    ``house_cusps`` are 12 quadrant cusps (cusps[0] = Ascendant); Lilly
    erected his figures in Regiomontanus houses. ``armc``, ``obliquity``
    (degrees) and ``geographic_latitude`` are needed only when a body or the
    Part of Fortune is under the earth in the 1st house; if they are missing
    then, ValueError is raised rather than guessing. ``planet_positions``
    (Mercury, Venus, Mars, Jupiter, Saturn), the preceding new Moon (day) or
    full Moon (night), and by night ``latest_prenatal_syzygy`` ("new_moon" or
    "full_moon") are needed only when no luminary is hylegiacal.
    """
    from .dignities import lilly_1647_essential_dignities_at

    if not isinstance(is_day_chart, bool):
        raise TypeError("is_day_chart must be a bool")
    if not isinstance(house_cusps, (list, tuple)) or len(house_cusps) != 12:
        raise ValueError("house_cusps must be a sequence of 12 cusp longitudes")
    values = [sun_longitude, moon_longitude, *house_cusps]
    values += [
        v for v in (
            armc, obliquity, geographic_latitude,
            prenatal_new_moon_longitude, prenatal_full_moon_longitude,
        )
        if v is not None
    ]
    if planet_positions is not None:
        if not isinstance(planet_positions, dict):
            raise TypeError("planet_positions must be a dict of planet longitudes")
        values += list(planet_positions.values())
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("hyleg inputs must be finite numbers")
    if latest_prenatal_syzygy not in (None, "new_moon", "full_moon"):
        raise ValueError("latest_prenatal_syzygy must be 'new_moon' or 'full_moon'")
    cusps = [float(c) % 360.0 for c in house_cusps]

    kwargs = dict(armc=armc, obliquity=obliquity, geographic_latitude=geographic_latitude)
    sun = _lilly_place_truth("Sun", sun_longitude, cusps, **kwargs)
    moon = _lilly_place_truth("Moon", moon_longitude, cusps, **kwargs)
    both = sun.is_hylegiacal and moon.is_hylegiacal

    def determination(**fields) -> HylegDetermination:
        base = dict(
            doctrine=HylegDoctrine.WILLIAM_LILLY_1647,
            is_day_chart=is_day_chart,
            candidates=(sun, moon),
            both_luminaries_hylegiacal=both,
        )
        base.update(fields)
        if base.get("hyleg") is None:
            base.setdefault("status", HylegStatus.NOT_EVALUABLE)
        else:
            base.setdefault("status", HylegStatus.SELECTED)
            base.setdefault("reason", None)
        return HylegDetermination(**base)

    order = (sun, moon) if is_day_chart else (moon, sun)
    for rank, candidate in enumerate(order):
        if candidate.is_hylegiacal:
            return determination(
                hyleg=candidate.body,
                hyleg_longitude=candidate.longitude,
                selection_step=(
                    "sect_light_hylegiacal" if rank == 0 else "other_luminary_hylegiacal"
                ),
            )

    # Dominion step.
    positions = {} if planet_positions is None else dict(planet_positions)
    positions["Sun"] = float(sun_longitude)
    positions["Moon"] = float(moon_longitude)
    missing = [p for p in _HYLEG_DOMINION_PLANETS if p not in positions]
    if missing:
        return determination(
            hyleg=None,
            reason="planet_positions_required_for_dominion_step:" + ",".join(missing),
        )
    asc = cusps[0]
    fortune = (asc + float(moon_longitude) - float(sun_longitude)) % 360.0
    if is_day_chart:
        if prenatal_new_moon_longitude is None:
            return determination(hyleg=None, reason="prenatal_new_moon_longitude_required")
        places = (
            ("Sun", float(sun_longitude) % 360.0),
            ("preceding_new_moon", float(prenatal_new_moon_longitude) % 360.0),
            ("Ascendant", asc),
        )
    else:
        if prenatal_full_moon_longitude is None:
            return determination(hyleg=None, reason="prenatal_full_moon_longitude_required")
        places = (
            ("Moon", float(moon_longitude) % 360.0),
            ("preceding_full_moon", float(prenatal_full_moon_longitude) % 360.0),
            ("Part of Fortune", fortune),
        )

    counts: list[HylegDominionCount] = []
    for planet in _HYLEG_DOMINION_PLANETS:
        by_place = tuple(
            (
                name,
                tuple(kind for kind, _ in lilly_1647_essential_dignities_at(planet, lon, is_day_chart)),
            )
            for name, lon in places
        )
        points = sum(
            points
            for _, lon in places
            for _, points in lilly_1647_essential_dignities_at(planet, lon, is_day_chart)
        )
        dignity_count = sum(len(kinds) for _, kinds in by_place)
        counts.append(
            HylegDominionCount(
                planet=planet,
                dignities_by_place=by_place,
                dignity_count=dignity_count,
                points=points,
                qualifies=dignity_count >= _HYLEG_DOMINION_MIN_DIGNITIES,
            )
        )
    count_tuple = tuple(counts)
    common = dict(dominion_places=places, dominion_counts=count_tuple)

    qualified = [c for c in counts if c.qualifies]
    top_planet: str | None = None
    top_place: HylegiacalPlaceTruth | None = None
    if qualified:
        best = max(c.points for c in qualified)
        tied = [c.planet for c in qualified if c.points == best]
        if len(tied) > 1:
            return determination(hyleg=None, reason="dominion_tie:" + ",".join(tied), **common)
        top_planet = tied[0]
        top_place = _lilly_place_truth(top_planet, positions[top_planet], cusps, **kwargs)
        if top_place.is_hylegiacal:
            return determination(
                hyleg=top_planet,
                hyleg_longitude=top_place.longitude,
                selection_step="dominion_planet_in_hylegiacal_place",
                dominion_planet=top_planet,
                dominion_planet_place=top_place,
                **common,
            )
    common.update(dominion_planet=top_planet, dominion_planet_place=top_place)

    if is_day_chart:
        return determination(
            hyleg="Ascendant", hyleg_longitude=asc, selection_step="ascendant_final", **common,
        )
    if latest_prenatal_syzygy is None:
        return determination(hyleg=None, reason="latest_prenatal_syzygy_required", **common)
    if latest_prenatal_syzygy == "new_moon":
        return determination(
            hyleg="Ascendant", hyleg_longitude=asc,
            selection_step="ascendant_final_after_new_moon", **common,
        )
    fortune_place = _lilly_place_truth("Part of Fortune", fortune, cusps, **kwargs)
    if fortune_place.is_hylegiacal:
        return determination(
            hyleg="Part of Fortune", hyleg_longitude=fortune,
            selection_step="part_of_fortune_after_full_moon",
            part_of_fortune_place=fortune_place, **common,
        )
    return determination(
        hyleg="Ascendant", hyleg_longitude=asc,
        selection_step="ascendant_final_fortune_not_hylegiacal",
        part_of_fortune_place=fortune_place, **common,
    )


# ---------------------------------------------------------------------------
# Alcocoden — William Lilly, Christian Astrology (1647), Book III ch. CIV
# ---------------------------------------------------------------------------
#
# Source: Lilly, CA III ch. CIV, pp. 530-531 (reporting "the Arabians"):
#
#   "what Planet had most essentiall dignity in the place of the Hyleg, and
#   with some aspect did behold that place, this Planet they called
#   Alcochodon, or giver of yeers; and they were of opinion, that the Native
#   might live the great, greater or lesser yeers, which this Planet did
#   signifie" (p. 530; the years "from pag. 57. to 83. of the first part").
#   "if either of the Luminaries be Hyleg, and in exaltation or house, that
#   Light may be Hyleg and Alcochodon." (p. 530)
#   "If many Planets seem, upon an equality of testimonies, to contend for
#   pre-eminency, he that hath aspect to the Hyleg is preferred before he that
#   hath none ... Where observe, in the day time an Oriental Planet is
#   preferred before one Occidental, viz. the Planet who is neerer the
#   ascendant then he that is next or neer unto the West angle: now if it
#   happen the Alcochodon to be angular, strong and fortunate, especially in
#   the first or tenth, he may possibly give his greater yeers." (p. 531)
#
# Admitted here (explicit ambiguity policy):
#   * Hyleg: ``find_hyleg_lilly_1647`` (luminaries, then the dominion step,
#     then the Ascendant or Part of Fortune). When it is not evaluable,
#     neither is the alcocoden.
#   * Step 1: a luminary hyleg in its own domicile or exaltation is the
#     alcocoden (Sun in Leo or Aries, Moon in Cancer or Taurus).
#   * Step 2: otherwise the alcocoden is the planet with the most essential
#     dignity in the hyleg's degree (Lilly's table and scale,
#     ``moira.dignities.lilly_1647_essential_dignities_at``) among the planets
#     that behold that degree. The hyleg body itself is not a step-2
#     candidate (it cannot aspect its own place).
#   * "Behold": conjunction, sextile, square, trine or opposition to the
#     hyleg's degree within the planet's own orb as Lilly gives it in each
#     planet's chapter, Book I chs. VIII-XIV ("his orb is nine degrees before
#     and after", etc.): LILLY_1647_PLANET_ORBS. Lilly calls the conjunction
#     an aspect only "very improperly" (Book I ch. XIX); it is admitted here
#     as beholding.
#   * Ties: among beholding planets with equal points, by day the planet
#     nearer the Ascendant than the Descendant (eastern) is preferred; any
#     remaining tie is NOT_EVALUABLE.
#   * No dignified planet beholds the hyleg: NOT_EVALUABLE. Lilly's clause
#     "if none aspect the Hyleg, then he that excels the rest in essentiall
#     fortitudes" (p. 531) is read as a rule for planets contending "upon an
#     equality of testimonies"; it is not used to admit a planet that does not
#     behold the hyleg.
#   * Reported, not mechanised: Lilly's further report that when a luminary
#     hyleg is not in its house or exaltation "that Planet shall be reputed
#     Alcochodon who ruleth the Signe wherein Hyleg is" (pp. 530-531) conflicts
#     with the definition above; the sign ruler is returned for inspection as
#     ``sign_ruler_of_hyleg``.
#   * Years: the least, mean and greater years of the alcocoden
#     (PTOLEMAIC_YEARS, Lilly Book I). Lilly gives no mechanical rule for
#     which of them is granted; ``angular_in_first_or_tenth`` records his one
#     condition for the greater years, and no single "granted" figure is
#     returned.

LILLY_1647_PLANET_ORBS: dict[str, float] = {
    "Saturn": 9.0,   # Book I ch. VIII, p. 60
    "Jupiter": 9.0,  # ch. IX
    "Mars": 7.0,     # ch. X
    "Sun": 15.0,     # ch. XI
    "Venus": 7.0,    # ch. XII
    "Mercury": 7.0,  # ch. XIII
    "Moon": 12.0,    # ch. XIV
}

_LILLY_ASPECTS: tuple[tuple[str, float], ...] = (
    ("conjunction", 0.0),
    ("sextile", 60.0),
    ("square", 90.0),
    ("trine", 120.0),
    ("opposition", 180.0),
)

_ALCOCODEN_PLANET_ORDER: tuple[str, ...] = (
    "Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn",
)

_LUMINARY_OWN_SIGNS: dict[str, frozenset[str]] = {
    "Sun": frozenset({"Leo", "Aries"}),
    "Moon": frozenset({"Cancer", "Taurus"}),
}


class AlcocodenStatus(StrEnum):
    """Outcome of an alcocoden determination."""

    SELECTED = "selected"
    NOT_EVALUABLE = "not_evaluable"


@dataclass(frozen=True, slots=True)
class AlcocodenCandidate:
    """One planet's claim on the hyleg's degree."""

    planet: str
    longitude: float
    essential_points: int
    dignities: tuple[str, ...]
    aspect_to_hyleg: str | None
    aspect_distance_deg: float | None
    orb_deg: float
    beholds_hyleg: bool
    eastern: bool


@dataclass(frozen=True, slots=True)
class AlcocodenDetermination:
    """Alcocoden under a named doctrine; ``alcocoden`` is None when not evaluable."""

    doctrine: HylegDoctrine
    status: AlcocodenStatus
    hyleg: HylegDetermination
    hyleg_longitude: float | None
    alcocoden: str | None
    selection_basis: str | None
    candidates: tuple[AlcocodenCandidate, ...]
    sign_ruler_of_hyleg: str | None
    alcocoden_house: int | None
    years_least: float | None
    years_mean: float | None
    years_greater: float | None
    angular_in_first_or_tenth: bool | None
    reason: str | None

    def __post_init__(self) -> None:
        if self.status is AlcocodenStatus.SELECTED:
            if self.alcocoden is None or self.selection_basis is None:
                raise ValueError("selected AlcocodenDetermination must name an alcocoden and basis")
        elif self.alcocoden is not None or not self.reason:
            raise ValueError("not_evaluable AlcocodenDetermination needs a reason and no alcocoden")


def _lilly_aspect(planet: str, planet_lon: float, place_lon: float) -> tuple[str | None, float | None]:
    separation = abs(((planet_lon - place_lon + 180.0) % 360.0) - 180.0)
    orb = LILLY_1647_PLANET_ORBS[planet]
    best: tuple[str, float] | None = None
    for name, angle in _LILLY_ASPECTS:
        distance = abs(separation - angle)
        if distance <= orb and (best is None or distance < best[1]):
            best = (name, distance)
    return (best[0], best[1]) if best is not None else (None, None)


def _is_eastern(longitude: float, asc_longitude: float) -> bool:
    to_asc = abs(((longitude - asc_longitude + 180.0) % 360.0) - 180.0)
    return to_asc < 90.0


def find_alcocoden_lilly_1647(
    planet_positions: dict[str, float],
    house_cusps: list[float],
    is_day_chart: bool,
    *,
    armc: float | None = None,
    obliquity: float | None = None,
    geographic_latitude: float | None = None,
    prenatal_new_moon_longitude: float | None = None,
    prenatal_full_moon_longitude: float | None = None,
    latest_prenatal_syzygy: str | None = None,
) -> AlcocodenDetermination:
    """
    Alcocoden by Lilly, *Christian Astrology* (1647) III ch. CIV.

    ``planet_positions`` must give all seven planets. The hyleg is found by
    ``find_hyleg_lilly_1647`` (same cusp, equatorial and syzygy inputs; the
    hyleg may be a luminary, a planet, the Ascendant or the Part of Fortune).
    See the doctrine note above ``LILLY_1647_PLANET_ORBS`` for the admitted
    rules.
    """
    from .dignities import lilly_1647_essential_dignities_at

    if not isinstance(planet_positions, dict):
        raise TypeError("planet_positions must be a dict of planet longitudes")
    missing = [p for p in _ALCOCODEN_PLANET_ORDER if p not in planet_positions]
    if missing:
        raise ValueError(f"planet_positions missing: {', '.join(missing)}")
    for name in _ALCOCODEN_PLANET_ORDER:
        value = planet_positions[name]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError(f"planet_positions[{name}] must be a finite number")

    hyleg = find_hyleg_lilly_1647(
        planet_positions["Sun"],
        planet_positions["Moon"],
        house_cusps,
        is_day_chart,
        armc=armc,
        obliquity=obliquity,
        geographic_latitude=geographic_latitude,
        planet_positions={
            name: planet_positions[name]
            for name in _ALCOCODEN_PLANET_ORDER
            if name not in ("Sun", "Moon")
        },
        prenatal_new_moon_longitude=prenatal_new_moon_longitude,
        prenatal_full_moon_longitude=prenatal_full_moon_longitude,
        latest_prenatal_syzygy=latest_prenatal_syzygy,
    )

    def not_evaluable(
        reason: str,
        *,
        hyleg_lon: float | None = None,
        candidates: tuple[AlcocodenCandidate, ...] = (),
        sign_ruler: str | None = None,
    ) -> AlcocodenDetermination:
        return AlcocodenDetermination(
            doctrine=HylegDoctrine.WILLIAM_LILLY_1647,
            status=AlcocodenStatus.NOT_EVALUABLE,
            hyleg=hyleg,
            hyleg_longitude=hyleg_lon,
            alcocoden=None,
            selection_basis=None,
            candidates=candidates,
            sign_ruler_of_hyleg=sign_ruler,
            alcocoden_house=None,
            years_least=None,
            years_mean=None,
            years_greater=None,
            angular_in_first_or_tenth=None,
            reason=reason,
        )

    if hyleg.status is not HylegStatus.SELECTED or hyleg.hyleg is None:
        return not_evaluable(f"hyleg_not_evaluable:{hyleg.reason}")

    hyleg_body = hyleg.hyleg
    if hyleg.hyleg_longitude is None:
        raise AssertionError("a selected hyleg carries its longitude")
    hyleg_lon = float(hyleg.hyleg_longitude) % 360.0
    hyleg_sign, _ = _sign_and_deg(hyleg_lon)
    sign_ruler = next(p for p, signs in DOMICILE.items() if hyleg_sign in signs)
    cusps = [float(c) % 360.0 for c in house_cusps]
    asc = cusps[0]

    candidates: list[AlcocodenCandidate] = []
    for planet in _ALCOCODEN_PLANET_ORDER:
        lon = float(planet_positions[planet]) % 360.0
        held = lilly_1647_essential_dignities_at(planet, hyleg_lon, is_day_chart)
        if planet == hyleg_body:
            aspect, distance = None, None
        else:
            aspect, distance = _lilly_aspect(planet, lon, hyleg_lon)
        candidates.append(
            AlcocodenCandidate(
                planet=planet,
                longitude=lon,
                essential_points=sum(points for _, points in held),
                dignities=tuple(kind for kind, _ in held),
                aspect_to_hyleg=aspect,
                aspect_distance_deg=distance,
                orb_deg=LILLY_1647_PLANET_ORBS[planet],
                beholds_hyleg=aspect is not None,
                eastern=_is_eastern(lon, asc),
            )
        )
    candidate_tuple = tuple(candidates)

    if hyleg_sign in _LUMINARY_OWN_SIGNS.get(hyleg_body, frozenset()):
        chosen, basis = hyleg_body, "luminary_hyleg_in_own_domicile_or_exaltation"
    else:
        contenders = [c for c in candidates if c.beholds_hyleg and c.essential_points > 0]
        if not contenders:
            return not_evaluable(
                "no_dignified_planet_beholds_hyleg",
                hyleg_lon=hyleg_lon,
                candidates=candidate_tuple,
                sign_ruler=sign_ruler,
            )
        top = max(c.essential_points for c in contenders)
        tied = [c for c in contenders if c.essential_points == top]
        basis = "most_essential_dignity_in_hyleg_place_beholding_it"
        if len(tied) > 1 and is_day_chart:
            eastern = [c for c in tied if c.eastern]
            if len(eastern) == 1:
                tied = eastern
                basis = "tie_resolved_by_day_oriental_preference"
        if len(tied) > 1:
            return not_evaluable(
                "alcocoden_tie_unresolved:" + ",".join(c.planet for c in tied),
                hyleg_lon=hyleg_lon,
                candidates=candidate_tuple,
                sign_ruler=sign_ruler,
            )
        chosen = tied[0].planet

    least, mean, greater = PTOLEMAIC_YEARS[chosen]
    house = _get_house(float(planet_positions[chosen]), cusps)
    return AlcocodenDetermination(
        doctrine=HylegDoctrine.WILLIAM_LILLY_1647,
        status=AlcocodenStatus.SELECTED,
        hyleg=hyleg,
        hyleg_longitude=hyleg_lon,
        alcocoden=chosen,
        selection_basis=basis,
        candidates=candidate_tuple,
        sign_ruler_of_hyleg=sign_ruler,
        alcocoden_house=house,
        years_least=least,
        years_mean=mean,
        years_greater=greater,
        angular_in_first_or_tenth=house in (1, 10),
        reason=None,
    )
