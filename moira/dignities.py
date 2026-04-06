"""
Dignity Engine — moira/dignities.py

Archetype: Engine
Purpose: Computes essential and accidental planetary dignities for the Classic
         7 planets, including domicile, exaltation, detriment, fall, peregrine,
         house placement, motion, solar proximity (cazimi/combust/sunbeams),
         mutual reception, hayz, and the Almuten Figuris.

Boundary declaration:
    Owns: dignity tables (DOMICILE, EXALTATION, DETRIMENT, FALL), scoring
          constants, hayz/sect logic, mutual reception detection, phasis
          detection, Almuten Figuris computation, and DignitiesService.
    Delegates: type definitions (enums, policy dataclasses, result vessels)
               to moira.dignities_types; sign arithmetic to
               moira.constants.SIGNS; longevity dignity scoring to
               moira.longevity.dignity_score_at (lazy import); planetary
               positions for phasis to moira.planets.planet_at (lazy import).

Import-time side effects: None

External dependency assumptions:
    - moira.constants.SIGNS is an ordered list of 12 sign name strings.
    - moira.longevity.dignity_score_at(planet, lon, is_day) is importable
      at call time (lazy import in almuten_figuris).

Public surface / exports:
    PlanetaryDignity      — result dataclass for one planet's dignity state
    DignitiesService      — service class for computing dignities from chart data
    DOMICILE / EXALTATION / DETRIMENT / FALL — essential dignity tables
    SECT / PREFERRED_HEMISPHERE / PREFERRED_GENDER — hayz/sect tables
    is_in_sect()          — sect membership test
    is_in_hayz()          — hayz test (all three sect conditions)
    calculate_dignities() — module-level convenience wrapper
    sect_light()          — determine chart sect light (Sun or Moon)
    is_day_chart()        — boolean day/night test
    almuten_figuris()     — planet with most essential dignities at key points
    mutual_receptions()   — all mutual receptions between Classic 7
    find_phasis()         — phasis (solar beam crossing) events for a planet

    All type definitions (enumerations, policy dataclasses, result vessels)
    are defined in moira.dignities_types and re-exported from here via
    ``from .dignities_types import *``.
"""

from __future__ import annotations

import math

from .constants import SIGNS
from .dignities_types import (
    CLASSIC_7,
    _PLANET_ORDER,
    _normalize_dispositorship_subject_name,
)
from .dignities_types import *  # noqa: F401, F403 — re-export full public surface

__all__ = [
    # Tables
    "DOMICILE", "EXALTATION", "DETRIMENT", "FALL",
    "SECT", "PREFERRED_HEMISPHERE", "PREFERRED_GENDER",
    "PLANETARY_JOYS",
    # Enums
    "ConditionPolarity",
    "EssentialDignityKind",
    "AccidentalConditionKind",
    "SectStateKind",
    "SolarConditionKind",
    "ReceptionKind",
    "ReceptionBasis",
    "ReceptionMode",
    "DispositorshipSubjectSet",
    "DispositorshipRulership",
    "DispositorshipTerminationKind",
    "UnsupportedSubjectHandling",
    "DispositorshipConditionState",
    "PlanetaryConditionState",
    "EssentialDignityDoctrine",
    "MercurySectModel",
    # Policy dataclasses
    "EssentialDignityPolicy",
    "SolarConditionPolicy",
    "MutualReceptionPolicy",
    "SectHayzPolicy",
    "AccidentalDignityPolicy",
    "DignityComputationPolicy",
    "DispositorshipSubjectPolicy",
    "DispositorshipRulershipPolicy",
    "DispositorshipTerminationPolicy",
    "DispositorshipUnsupportedSubjectPolicy",
    "DispositorshipOrderingPolicy",
    "DispositorshipComputationPolicy",
    # Result/truth dataclasses
    "PlanetaryReception",
    "DispositorLink",
    "DispositorshipChain",
    "DispositorshipProfile",
    "DispositorshipConditionProfile",
    "DispositorshipChartConditionProfile",
    "DispositorshipNetworkEdgeMode",
    "DispositorshipNetworkNode",
    "DispositorshipNetworkEdge",
    "DispositorshipNetworkProfile",
    "DispositorshipSubsystemProfile",
    "DispositorshipComparisonItem",
    "DispositorshipComparisonBundle",
    "PlanetaryConditionProfile",
    "ChartConditionProfile",
    "ConditionNetworkNode",
    "ConditionNetworkEdge",
    "ConditionNetworkProfile",
    "EssentialDignityClassification",
    "AccidentalConditionClassification",
    "AccidentalDignityClassification",
    "SectClassification",
    "SolarConditionClassification",
    "ReceptionClassification",
    "EssentialDignityTruth",
    "AccidentalDignityCondition",
    "SolarConditionTruth",
    "MutualReceptionTruth",
    "SectTruth",
    "AccidentalDignityTruth",
    "PlanetaryDignity",
    # Service
    "DignitiesService",
    # Module-level functions
    "is_in_sect",
    "is_in_hayz",
    "is_in_halb",
    "is_in_joy",
    "oriental_occidental",
    "is_besieged",
    "calculate_dignities",
    "calculate_receptions",
    "calculate_dispositorship",
    "calculate_dispositorship_condition_profiles",
    "calculate_dispositorship_chart_condition_profile",
    "calculate_dispositorship_network_profile",
    "calculate_dispositorship_subsystem_profile",
    "compare_dispositorship",
    "calculate_condition_profiles",
    "calculate_chart_condition_profile",
    "calculate_condition_network_profile",
    "sect_light",
    "is_day_chart",
    "almuten_figuris",
    "mutual_receptions",
    "find_phasis",
]


# ---------------------------------------------------------------------------
# Essential dignity tables (classic Hellenistic / traditional)
# ---------------------------------------------------------------------------

DOMICILE: dict[str, list[str]] = {
    "Sun":     ["Leo"],
    "Moon":    ["Cancer"],
    "Mercury": ["Gemini", "Virgo"],
    "Venus":   ["Taurus", "Libra"],
    "Mars":    ["Aries", "Scorpio"],
    "Jupiter": ["Sagittarius", "Pisces"],
    "Saturn":  ["Capricorn", "Aquarius"],
}

EXALTATION: dict[str, list[str]] = {
    "Sun":     ["Aries"],
    "Moon":    ["Taurus"],
    "Mercury": ["Virgo"],
    "Venus":   ["Pisces"],
    "Mars":    ["Capricorn"],
    "Jupiter": ["Cancer"],
    "Saturn":  ["Libra"],
}

DETRIMENT: dict[str, list[str]] = {
    "Sun":     ["Aquarius"],
    "Moon":    ["Capricorn"],
    "Mercury": ["Sagittarius", "Pisces"],
    "Venus":   ["Scorpio", "Aries"],
    "Mars":    ["Libra", "Taurus"],
    "Jupiter": ["Gemini", "Virgo"],
    "Saturn":  ["Cancer", "Leo"],
}

FALL: dict[str, list[str]] = {
    "Sun":     ["Libra"],
    "Moon":    ["Scorpio"],
    "Mercury": ["Pisces"],
    "Venus":   ["Virgo"],
    "Mars":    ["Cancer"],
    "Jupiter": ["Capricorn"],
    "Saturn":  ["Aries"],
}

# ---------------------------------------------------------------------------
# Scoring constants
# ---------------------------------------------------------------------------

SCORE_DOMICILE   =  5;  SCORE_EXALTATION =  4
SCORE_TRIPLICITY =  3;  SCORE_BOUND      =  2;  SCORE_FACE     =  1
SCORE_DETRIMENT  = -5;  SCORE_FALL       = -4
SCORE_PEREGRINE  =  0

SCORE_ANGULAR    =  4;  SCORE_SUCCEDENT  =  2;  SCORE_CADENT   = -2
SCORE_DIRECT     =  2;  SCORE_RETROGRADE = -5
SCORE_CAZIMI     =  5   # within 17' of Sun
SCORE_COMBUST    = -5   # within 8 degrees
SCORE_SUNBEAMS   = -4   # 8 degrees-17 degrees
SCORE_MR_DOMICILE   = 5
SCORE_MR_EXALTATION = 4
SCORE_JOY        =  3   # planet in its joy house
SCORE_HALB       =  1   # partial hayz (two of three sect conditions)
SCORE_ORIENTAL   =  2   # oriental planet (favourable phase)
SCORE_OCCIDENTAL = -2   # occidental planet (unfavourable phase)
SCORE_BESIEGED   = -5   # enclosed between two malefics

ANGULAR_HOUSES   = {1, 4, 7, 10}
SUCCEDENT_HOUSES = {2, 5, 8, 11}
CADENT_HOUSES    = {3, 6, 9, 12}

# ---------------------------------------------------------------------------
# Hayz / Sect tables
# ---------------------------------------------------------------------------

# Primary sect membership: 'diurnal', 'nocturnal', or 'sect_light' (Mercury)
SECT: dict[str, str] = {
    "Sun":     "diurnal",
    "Jupiter": "diurnal",
    "Saturn":  "diurnal",
    "Moon":    "nocturnal",
    "Venus":   "nocturnal",
    "Mars":    "nocturnal",
    "Mercury": "sect_light",  # changes with Sun: diurnal if it rises/sets before Sun
}

# Preferred hemisphere: 'above' (houses 7–12) or 'below' (houses 1–6)
PREFERRED_HEMISPHERE: dict[str, str] = {
    "Sun":     "above",
    "Jupiter": "above",
    "Saturn":  "above",
    "Moon":    "below",
    "Venus":   "below",
    "Mars":    "above",   # Mars prefers above horizon in day chart; simplified
}

# Masculine signs (fire + air): Aries, Gemini, Leo, Libra, Sagittarius, Aquarius
MASCULINE_SIGNS: set[str] = {
    "Aries", "Gemini", "Leo", "Libra", "Sagittarius", "Aquarius"
}
FEMININE_SIGNS: set[str] = {
    "Taurus", "Cancer", "Virgo", "Scorpio", "Capricorn", "Pisces"
}

# Preferred sign gender (masculine or feminine)
PREFERRED_GENDER: dict[str, str] = {
    "Sun":     "masculine",
    "Jupiter": "masculine",
    "Saturn":  "masculine",
    "Moon":    "feminine",
    "Venus":   "feminine",
    "Mars":    "masculine",
    "Mercury": "either",   # Mercury works in either gender
}


# ---------------------------------------------------------------------------
# Hayz / Sect standalone functions
# ---------------------------------------------------------------------------

def is_in_sect(
    planet: str,
    is_day_chart: bool,
    mercury_rises_before_sun: bool = True,
) -> bool:
    """
    Return True if the planet is in its preferred sect.

    Diurnal planets (Sun, Jupiter, Saturn) are in sect during a day chart.
    Nocturnal planets (Moon, Venus, Mars) are in sect during a night chart.
    Mercury switches: diurnal when it rises or sets before the Sun (Cazimi
    or morning star), nocturnal otherwise.

    Parameters
    ----------
    planet                  : planet name (Classic 7)
    is_day_chart            : True when the Sun is above the horizon (H7–H12)
    mercury_rises_before_sun: True if Mercury is a morning star / heliacal rising
    """
    sect = SECT.get(planet)
    if sect is None:
        return False
    if sect == "diurnal":
        return is_day_chart
    if sect == "nocturnal":
        return not is_day_chart
    # Mercury ("sect_light"): diurnal when rising before Sun, else nocturnal
    mercury_sect = "diurnal" if mercury_rises_before_sun else "nocturnal"
    return mercury_sect == ("diurnal" if is_day_chart else "nocturnal")


def is_in_hayz(
    planet: str,
    sign: str,
    house: int,
    is_day_chart: bool,
    mercury_rises_before_sun: bool = True,
) -> bool:
    """
    Return True if the planet is in hayz (fully satisfying all sect conditions).

    Hayz requires all three conditions to be met simultaneously:
      1. Planet is in its preferred sect (diurnal planet in day chart, or
         nocturnal planet in night chart; Mercury follows heliacal phase).
      2. Planet is in its preferred hemisphere (above horizon = houses 7–12;
         below horizon = houses 1–6).
      3. Planet is in a sign of its preferred gender (masculine = fire/air;
         feminine = earth/water).

    Hayz is traditionally considered the highest form of accidental strength.

    Parameters
    ----------
    planet                  : planet name (Classic 7 only)
    sign                    : current zodiac sign name
    house                   : house number 1–12
    is_day_chart            : True if Sun is above the horizon (H7–H12)
    mercury_rises_before_sun: for Mercury — True if it is a morning star
    """
    if planet not in SECT:
        return False

    # Condition 1: correct sect
    if not is_in_sect(planet, is_day_chart, mercury_rises_before_sun):
        return False

    # Condition 2: preferred hemisphere
    preferred_hemi = PREFERRED_HEMISPHERE.get(planet)
    if preferred_hemi == "above":
        # Above horizon = houses 7 through 12
        in_preferred_hemi = (7 <= house <= 12)
    elif preferred_hemi == "below":
        # Below horizon = houses 1 through 6
        in_preferred_hemi = (1 <= house <= 6)
    else:
        in_preferred_hemi = True  # unknown planet — do not penalise

    if not in_preferred_hemi:
        return False

    # Condition 3: preferred sign gender
    preferred_gender = PREFERRED_GENDER.get(planet)
    if preferred_gender == "masculine":
        in_preferred_gender = sign in MASCULINE_SIGNS
    elif preferred_gender == "feminine":
        in_preferred_gender = sign in FEMININE_SIGNS
    else:
        # Mercury ("either") is content in any sign gender
        in_preferred_gender = True

    return in_preferred_gender


# ---------------------------------------------------------------------------
# Planetary Joys
# ---------------------------------------------------------------------------
# The seven classical joy-house assignments: Mercury in 1st, Moon in 3rd,
# Venus in 5th, Mars in 6th, Sun in 9th, Jupiter in 11th, Saturn in 12th.
# Canon: Thrasyllus (1st century CE); Brennan, Hellenistic Astrology, Ch. 5.

PLANETARY_JOYS: dict[str, int] = {
    "Mercury": 1,
    "Moon":    3,
    "Venus":   5,
    "Mars":    6,
    "Sun":     9,
    "Jupiter": 11,
    "Saturn":  12,
}


def is_in_joy(planet: str, house: int) -> bool:
    """Return True if the planet is in its joy house."""
    return PLANETARY_JOYS.get(planet) == house


def is_in_halb(
    planet: str,
    sign: str,
    house: int,
    is_day_chart: bool,
    mercury_rises_before_sun: bool = True,
) -> bool:
    """
    Return True if the planet is in halb (partial hayz).

    Halb requires exactly two of the three hayz conditions to be met:
      1. Planet is in its preferred sect.
      2. Planet is in its preferred hemisphere.
      3. Planet is in a sign of its preferred gender.

    When all three are met the planet is in full hayz, not halb.
    When fewer than two are met the planet is neither in hayz nor halb.
    """
    if planet not in SECT:
        return False

    cond_sect = is_in_sect(planet, is_day_chart, mercury_rises_before_sun)

    preferred_hemi = PREFERRED_HEMISPHERE.get(planet)
    if preferred_hemi == "above":
        cond_hemi = 7 <= house <= 12
    elif preferred_hemi == "below":
        cond_hemi = 1 <= house <= 6
    else:
        cond_hemi = True

    preferred_gender = PREFERRED_GENDER.get(planet)
    if preferred_gender == "masculine":
        cond_gender = sign in MASCULINE_SIGNS
    elif preferred_gender == "feminine":
        cond_gender = sign in FEMININE_SIGNS
    else:
        cond_gender = True

    count = sum((cond_sect, cond_hemi, cond_gender))
    return count == 2


# -- Superior / inferior planet classification for oriental/occidental ------

_SUPERIOR_PLANETS = {"Mars", "Jupiter", "Saturn"}
_INFERIOR_PLANETS = {"Mercury", "Venus"}


def oriental_occidental(
    planet: str,
    planet_lon: float,
    sun_lon: float,
) -> str | None:
    """
    Classify a planet as oriental or occidental relative to the Sun.

    Classical Ptolemaic definition:
      - Superior planets (Mars, Jupiter, Saturn) are **oriental** when they
        rise before the Sun, i.e. their ecliptic longitude is *behind* the
        Sun in zodiacal order (the Sun has passed them).  They are
        **occidental** when they set after the Sun.
      - Inferior planets (Mercury, Venus) follow the reverse rule: oriental
        when they are morning stars (rising before the Sun), occidental when
        evening stars.
      - Luminaries (Sun, Moon) have no oriental/occidental classification;
        returns None.

    The geometric test: if the forward distance from the planet to the Sun
    (going in the zodiacal direction) is less than 180 degrees, the planet
    is east of the Sun (occidental for superiors, oriental for inferiors).
    Otherwise the planet is west of the Sun (oriental for superiors,
    occidental for inferiors).

    Parameters
    ----------
    planet     : planet name
    planet_lon : ecliptic longitude of the planet (degrees)
    sun_lon    : ecliptic longitude of the Sun (degrees)

    Returns
    -------
    ``"oriental"``, ``"occidental"``, or ``None`` (for luminaries).
    """
    if planet in ("Sun", "Moon"):
        return None

    # Forward distance from planet to Sun in zodiacal order
    forward_to_sun = (sun_lon - planet_lon) % 360.0

    if planet in _SUPERIOR_PLANETS:
        # Superior: oriental when west of Sun (forward_to_sun < 180),
        # occidental when east of Sun (forward_to_sun > 180)
        if forward_to_sun <= 180.0:
            return "oriental"
        return "occidental"

    if planet in _INFERIOR_PLANETS:
        # Inferior: oriental when morning star (west of Sun, forward < 180),
        # occidental when evening star (east of Sun, forward > 180)
        if forward_to_sun <= 180.0:
            return "oriental"
        return "occidental"

    return None


def is_besieged(
    planet_lon: float,
    chart_positions: dict[str, float],
    planet_name: str | None = None,
    orb: float = 12.0,
) -> tuple[str, str] | None:
    """
    Determine if a planet is besieged (enclosed) between two malefics.

    A planet is besieged when its nearest ecliptic neighbours on *both*
    sides are malefics (Mars and Saturn) within the specified orb.

    Parameters
    ----------
    planet_lon      : ecliptic longitude of the planet to test
    chart_positions : dict of body name → longitude for the whole chart
    planet_name     : if given, excludes this name from the neighbours
    orb             : maximum distance for a malefic to count as enclosing

    Returns
    -------
    Tuple of (left_malefic, right_malefic) names if besieged, else None.
    """
    _MALEFICS = {"Mars", "Saturn"}

    # Build list of (longitude, name) for all chart bodies except the target
    bodies = []
    for name, lon in chart_positions.items():
        if name == planet_name:
            continue
        if name in ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"):
            bodies.append((lon % 360.0, name))

    if len(bodies) < 2:
        return None

    target = planet_lon % 360.0

    # Find nearest body on each side (forward and backward in zodiacal order)
    nearest_forward: tuple[float, str] | None = None
    nearest_backward: tuple[float, str] | None = None

    for lon, name in bodies:
        fwd_dist = (lon - target) % 360.0
        bwd_dist = (target - lon) % 360.0

        if fwd_dist > 0 and (nearest_forward is None or fwd_dist < nearest_forward[0]):
            nearest_forward = (fwd_dist, name)
        if bwd_dist > 0 and (nearest_backward is None or bwd_dist < nearest_backward[0]):
            nearest_backward = (bwd_dist, name)

    if nearest_forward is None or nearest_backward is None:
        return None

    fwd_dist, fwd_name = nearest_forward
    bwd_dist, bwd_name = nearest_backward

    if fwd_name in _MALEFICS and bwd_name in _MALEFICS:
        if fwd_dist <= orb and bwd_dist <= orb:
            return (bwd_name, fwd_name)

    return None


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------

class DignitiesService:
    """
    RITE: The Herald of Honours — the Engine that surveys every planet's
          position in the chart and pronounces its essential throne and
          accidental dignities according to classical tradition.

    THEOREM: Governs the computation of essential and accidental dignities
             for all Classic 7 planets found in a chart, returning a sorted
             list of PlanetaryDignity records whose public labels preserve
             current semantics while their structured truth preserves the
             underlying doctrinal path.

    RITE OF PURPOSE:
        DignitiesService is the computational core of the Dignity Engine.
        It applies the current classical dignity system — essential tables,
        house placement, motion, solar proximity, mutual reception, and
        hayz — to produce a complete dignity portrait of the chart.
        This phase contains the computational core plus a lean descriptive
        classification layer built from that core. It preserves truth,
        classifies it explicitly, adds a small inspectability surface for
        callers, makes doctrine/policy explicit, and formalises reception as
        first-class relational truth, and integrates per-planet condition
        state, aggregates chart-wide condition intelligence, and projects a
        reception / condition network, but does not yet perform policy
        arbitration. Without this Engine, the dignity tables would be inert
        data with no path to a scored result.

    LAW OF OPERATION:
        Responsibilities:
            - Accept planet_positions and house_positions as plain dicts.
            - Resolve sign, house, essential dignity, and all accidental
              conditions for each Classic 7 planet present.
            - Preserve enough structured doctrinal/computational truth that
              later layers do not need to reconstruct hidden logic from the
              flattened legacy labels.
            - Derive lean explicit classifications from the preserved truth
              without changing the underlying computation.
            - Formalise reception relations from the same doctrinal truth
              and policy used by the dignity engine.
            - Integrate per-planet condition profiles from the already
              computed truth without recomputing doctrine independently.
            - Aggregate chart-wide condition profiles from the integrated
              per-planet profiles without recomputing doctrine.
            - Project a deterministic reception / condition network from the
              admitted relation and condition layers.
            - Return dignity vessels that are self-consistent and directly
              inspectable without reconstructing nested state by hand.
            - Return a list of PlanetaryDignity sorted in traditional
              planet order (Sun through Saturn).
        Non-responsibilities:
            - Does not compute planetary positions; those are supplied by
              the caller.
            - Does not support outer planets (Uranus, Neptune, Pluto) for
              essential dignities.
            - Does not perform any I/O or kernel access.
        Dependencies:
            - moira.constants.SIGNS for sign name lookup.
        Failure behavior:
            - Missing planets in planet_positions are silently skipped.
            - Malformed house_positions entries default to 0.0.

    Canon: William Lilly, Christian Astrology (1647), Book I;
           Vettius Valens, Anthology (hayz)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.dignities.DignitiesService",
        "risk": "medium",
        "api": {"frozen": ["calculate_dignities"], "internal": ["_get_essential_dignity", "_get_essential_dignity_truth", "_get_accidental_dignities", "_build_sect_truth", "_find_mutual_receptions", "_build_house_cusps", "_get_house"]},
        "state": {"mutable": false, "owners": []},
        "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
        "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
        "failures": {"policy": "silent_default"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    def calculate_dignities(
        self,
        planet_positions: list[dict],
        house_positions: list[dict],
        policy: DignityComputationPolicy | None = None,
    ) -> list[PlanetaryDignity]:
        """
        Calculate dignities for all Classic 7 planets found in the chart.

        Parameters
        ----------
        planet_positions : list of dicts with keys:
            - name: str
            - degree: float (tropical ecliptic longitude 0–360)
            - is_retrograde: bool (optional, default False)
        house_positions : list of dicts with keys:
            - number: int (1–12)
            - degree: float (cusp longitude)

        Returns
        -------
        List of PlanetaryDignity, sorted in traditional planet order.

        Semantics note
        --------------
        This method preserves existing dignity-computation semantics. New
        structured truth fields are additive and must remain internally
        consistent with the established labels and scores.
        """
        policy = DignityComputationPolicy() if policy is None else policy
        self._validate_policy(policy)

        normalized_planets = self._normalize_planet_positions(planet_positions)
        house_cusps = self._build_house_cusps(house_positions)

        planet_lons:  dict[str, float] = {}
        planet_signs: dict[str, str]   = {}
        planet_retro: dict[str, bool]  = {}

        for pos in normalized_planets:
            name = pos["name"]
            degree = pos["degree"]
            retro = pos["is_retrograde"]
            planet_lons[name] = degree
            planet_signs[name] = SIGNS[int(degree // 30) % 12]
            planet_retro[name] = retro

        sun_lon = planet_lons.get("Sun", 0.0)
        all_receptions_by_planet = self._find_receptions(
            planet_signs,
            bases=(ReceptionBasis.DOMICILE, ReceptionBasis.EXALTATION),
        )
        receptions_by_planet = self._find_receptions(
            planet_signs,
            bases=self._policy_reception_bases(policy),
        )

        # Determine if this is a day chart: Sun above horizon = houses 7–12
        sun_house = self._get_house(sun_lon, house_cusps) if house_cusps else 1
        is_day_chart = sun_house >= 7

        # Determine Mercury's phase: is it a morning star (rises before Sun)?
        # Use a simple heuristic: Mercury is a morning star when it is behind the Sun
        # (i.e., its longitude is less than the Sun's by up to 90°).
        mercury_lon = planet_lons.get("Mercury", sun_lon)
        mercury_rises_before_sun = self._mercury_rises_before_sun(
            mercury_lon=mercury_lon,
            sun_lon=sun_lon,
            policy=policy,
        )

        results: list[PlanetaryDignity] = []

        for planet in CLASSIC_7:
            if planet not in planet_lons:
                continue

            degree = planet_lons[planet]
            sign   = planet_signs[planet]
            retro  = planet_retro.get(planet, False)
            house  = self._get_house(degree, house_cusps)

            essential_truth = self._get_essential_dignity_truth(planet, sign, policy)

            acc_list, acc_score, accidental_truth, sect_truth = self._get_accidental_dignities(
                planet=planet,
                house=house,
                is_retrograde=retro,
                planet_lon=degree,
                sun_lon=sun_lon,
                receptions=receptions_by_planet.get(planet, []),
                sign=sign,
                is_day_chart=is_day_chart,
                mercury_rises_before_sun=mercury_rises_before_sun,
                policy=policy,
                chart_positions=planet_lons,
            )

            results.append(PlanetaryDignity(
                planet=planet,
                sign=sign,
                degree=degree,
                house=house,
                essential_dignity=essential_truth.label,
                essential_score=essential_truth.score,
                accidental_dignities=acc_list,
                accidental_score=acc_score,
                total_score=essential_truth.score + acc_score,
                is_retrograde=retro,
                essential_truth=essential_truth,
                accidental_truth=accidental_truth,
                sect_truth=sect_truth,
                solar_truth=accidental_truth.solar_condition,
                all_receptions=list(all_receptions_by_planet.get(planet, [])),
                receptions=list(receptions_by_planet.get(planet, [])),
                mutual_reception_truth=list(accidental_truth.mutual_receptions),
                essential_classification=self._classify_essential_truth(essential_truth),
                accidental_classification=self._classify_accidental_truth(accidental_truth),
                sect_classification=self._classify_sect_truth(sect_truth),
                solar_classification=self._classify_solar_truth(accidental_truth.solar_condition),
                reception_classification=self._classify_reception_truths(accidental_truth.mutual_receptions),
                condition_profile=self._build_condition_profile(
                    planet=planet,
                    essential_truth=essential_truth,
                    accidental_truth=accidental_truth,
                    sect_truth=sect_truth,
                    solar_truth=accidental_truth.solar_condition,
                    all_receptions=list(all_receptions_by_planet.get(planet, [])),
                    admitted_receptions=list(receptions_by_planet.get(planet, [])),
                    mutual_reception_truth=list(accidental_truth.mutual_receptions),
                ),
            ))

        results.sort(key=lambda d: _PLANET_ORDER.index(d.planet)
                     if d.planet in _PLANET_ORDER else 99)
        return results

    def calculate_receptions(
        self,
        planet_positions: list[dict],
        policy: DignityComputationPolicy | None = None,
    ) -> list[PlanetaryReception]:
        """
        Calculate formal reception relations for all Classic 7 planets found.

        This is a backend relation layer derived from the same doctrinal
        sign-state and policy used by the dignity engine. It does not add
        any new scoring semantics by itself.
        """
        policy = DignityComputationPolicy() if policy is None else policy
        self._validate_policy(policy)

        planet_signs: dict[str, str] = {}
        for pos in self._normalize_planet_positions(planet_positions):
            name = pos["name"]
            degree = pos["degree"]
            if name in CLASSIC_7:
                planet_signs[name] = SIGNS[int(degree // 30) % 12]

        receptions = self._find_receptions(planet_signs, bases=self._policy_reception_bases(policy))
        ordered: list[PlanetaryReception] = []
        for planet in _PLANET_ORDER:
            ordered.extend(receptions.get(planet, []))
        return ordered

    def calculate_dispositorship(
        self,
        planet_positions: list[dict],
        policy: DispositorshipComputationPolicy | None = None,
    ) -> DispositorshipProfile:
        """Calculate chart dispositorship under explicit Phase 1 policy."""

        policy = DispositorshipComputationPolicy() if policy is None else policy
        self._validate_dispositorship_policy(policy)

        normalized_positions = self._normalize_planet_positions(planet_positions)
        signs_by_name: dict[str, str] = {
            str(pos["name"]): SIGNS[int(float(pos["degree"]) // 30) % 12]
            for pos in normalized_positions
        }
        in_scope_names = self._dispositorship_subjects(signs_by_name, policy)
        unsupported = tuple(
            str(pos["name"]) for pos in normalized_positions if str(pos["name"]) not in in_scope_names
        )

        handling = policy.unsupported_subjects.handling
        if handling is UnsupportedSubjectHandling.REJECT and unsupported:
            raise ValueError(
                "calculate_dispositorship received unsupported subjects under reject policy: "
                + ", ".join(unsupported)
            )

        chains: list[DispositorshipChain] = []
        for name in in_scope_names:
            chains.append(self._build_dispositorship_chain(name, signs_by_name, policy))

        if handling is UnsupportedSubjectHandling.IGNORE:
            for pos in normalized_positions:
                name = str(pos["name"])
                if name in in_scope_names:
                    continue
                chains.append(
                    DispositorshipChain(
                        initial_subject=name,
                        initial_sign=signs_by_name[name],
                        subject_in_scope=False,
                        subject_has_dispositor=False,
                        visited_subjects=(name,),
                        termination_kind=DispositorshipTerminationKind.UNRESOLVED,
                    )
                )
        elif handling is UnsupportedSubjectHandling.SEGREGATE:
            # Unsupported bodies are reported only through unsupported_subjects.
            pass

        final_set = {
            terminal
            for chain in chains
            if chain.termination_kind is DispositorshipTerminationKind.FINAL_DISPOSITOR
            for terminal in chain.terminal_subjects
        }
        if policy.ordering.use_dignity_order:
            final_dispositors = tuple(
                planet for planet in _PLANET_ORDER if planet in final_set
            )
        else:
            final_dispositors = tuple(
                name for name in in_scope_names if name in final_set
            )
        terminal_cycles = self._unique_terminal_cycles(chains)
        return DispositorshipProfile(
            chains=chains,
            final_dispositors=final_dispositors,
            terminal_cycles=terminal_cycles,
            unsupported_subjects=unsupported,
            policy=policy,
        )

    def compare_dispositorship(
        self,
        planet_positions: list[dict],
        doctrine_profiles: list[tuple[str, DispositorshipComputationPolicy | None]],
    ) -> DispositorshipComparisonBundle:
        """Compare multiple named dispositorship profiles side by side."""

        if not doctrine_profiles:
            raise ValueError("compare_dispositorship requires at least one named doctrine profile")

        items: list[DispositorshipComparisonItem] = []
        seen_names: set[str] = set()
        for raw_name, policy in doctrine_profiles:
            if not isinstance(raw_name, str) or not raw_name.strip():
                raise ValueError("compare_dispositorship requires each doctrine profile to have a non-empty name")
            name = raw_name.strip()
            if name in seen_names:
                raise ValueError(f"compare_dispositorship received duplicate doctrine profile name {name!r}")
            seen_names.add(name)
            items.append(
                DispositorshipComparisonItem(
                    name=name,
                    profile=self.calculate_dispositorship(planet_positions, policy=policy),
                )
            )

        shared: set[str] | None = None
        all_finals: set[str] = set()
        for item in items:
            finals = set(item.profile.final_dispositors)
            all_finals.update(finals)
            shared = finals if shared is None else shared & finals

        def _ordered_subjects(members: set[str]) -> tuple[str, ...]:
            ordered: list[str] = []
            for item in items:
                for subject in item.profile.final_dispositors:
                    if subject in members and subject not in ordered:
                        ordered.append(subject)
            return tuple(ordered)

        return DispositorshipComparisonBundle(
            items=items,
            shared_final_dispositors=_ordered_subjects(shared or set()),
            all_final_dispositors=_ordered_subjects(all_finals),
            doctrine_names=tuple(item.name for item in items),
        )

    def calculate_dispositorship_condition_profiles(
        self,
        planet_positions: list[dict],
        policy: DispositorshipComputationPolicy | None = None,
    ) -> list[DispositorshipConditionProfile]:
        """Calculate integrated per-subject dispositorship condition profiles."""

        profile = self.calculate_dispositorship(planet_positions, policy=policy)
        return [
            self._build_dispositorship_condition_profile(chain)
            for chain in profile.chains
        ]

    def calculate_dispositorship_chart_condition_profile(
        self,
        planet_positions: list[dict],
        policy: DispositorshipComputationPolicy | None = None,
    ) -> DispositorshipChartConditionProfile:
        """Calculate the chart-wide dispositorship condition profile."""

        profiles = self.calculate_dispositorship_condition_profiles(
            planet_positions,
            policy=policy,
        )
        return self._build_dispositorship_chart_condition_profile(profiles)

    def calculate_dispositorship_network_profile(
        self,
        planet_positions: list[dict],
        policy: DispositorshipComputationPolicy | None = None,
    ) -> DispositorshipNetworkProfile:
        """Calculate the dispositorship network profile."""

        profile = self.calculate_dispositorship(planet_positions, policy=policy)
        condition_profiles = [
            self._build_dispositorship_condition_profile(chain)
            for chain in profile.chains
        ]
        return self._build_dispositorship_network_profile(condition_profiles, profile.chains)

    def calculate_dispositorship_subsystem_profile(
        self,
        planet_positions: list[dict],
        policy: DispositorshipComputationPolicy | None = None,
    ) -> DispositorshipSubsystemProfile:
        """Calculate the fully hardened dispositorship subsystem profile."""

        profile = self.calculate_dispositorship(planet_positions, policy=policy)
        condition_profiles = [
            self._build_dispositorship_condition_profile(chain)
            for chain in profile.chains
        ]
        chart_condition_profile = self._build_dispositorship_chart_condition_profile(condition_profiles)
        network_profile = self._build_dispositorship_network_profile(condition_profiles, profile.chains)
        return DispositorshipSubsystemProfile(
            profile=profile,
            condition_profiles=condition_profiles,
            chart_condition_profile=chart_condition_profile,
            network_profile=network_profile,
        )

    def calculate_condition_profiles(
        self,
        planet_positions: list[dict],
        house_positions: list[dict],
        policy: DignityComputationPolicy | None = None,
    ) -> list[PlanetaryConditionProfile]:
        """Calculate integrated per-planet condition profiles."""

        dignities = self.calculate_dignities(
            planet_positions,
            house_positions,
            policy=policy,
        )
        return [dignity.condition_profile for dignity in dignities if dignity.condition_profile is not None]

    def calculate_chart_condition_profile(
        self,
        planet_positions: list[dict],
        house_positions: list[dict],
        policy: DignityComputationPolicy | None = None,
    ) -> ChartConditionProfile:
        """Calculate the chart-wide condition profile derived from planet profiles."""

        profiles = self.calculate_condition_profiles(
            planet_positions,
            house_positions,
            policy=policy,
        )
        return self._build_chart_condition_profile(profiles)

    def calculate_condition_network_profile(
        self,
        planet_positions: list[dict],
        house_positions: list[dict],
        policy: DignityComputationPolicy | None = None,
    ) -> ConditionNetworkProfile:
        """Calculate the reception / condition network profile."""

        chart_profile = self.calculate_chart_condition_profile(
            planet_positions,
            house_positions,
            policy=policy,
        )
        return self._build_condition_network_profile(chart_profile)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_essential_dignity_truth(
        planet: str,
        sign: str,
        policy: DignityComputationPolicy,
    ) -> EssentialDignityTruth:
        if policy.essential.doctrine is not EssentialDignityDoctrine.TRADITIONAL_CLASSIC_7:
            raise ValueError(f"Unsupported essential dignity doctrine: {policy.essential.doctrine}")
        if sign in DOMICILE.get(planet, []):
            return EssentialDignityTruth("essential", "Domicile", SCORE_DOMICILE, sign, tuple(DOMICILE.get(planet, ())))
        if sign in EXALTATION.get(planet, []):
            return EssentialDignityTruth("essential", "Exaltation", SCORE_EXALTATION, sign, tuple(EXALTATION.get(planet, ())))
        if sign in DETRIMENT.get(planet, []):
            return EssentialDignityTruth("essential", "Detriment", SCORE_DETRIMENT, sign, tuple(DETRIMENT.get(planet, ())))
        if sign in FALL.get(planet, []):
            return EssentialDignityTruth("essential", "Fall", SCORE_FALL, sign, tuple(FALL.get(planet, ())))
        return EssentialDignityTruth("essential", "Peregrine", SCORE_PEREGRINE, sign, ())

    @staticmethod
    def _get_essential_dignity(planet: str, sign: str) -> tuple[str, int]:
        truth = DignitiesService._get_essential_dignity_truth(planet, sign, DignityComputationPolicy())
        return truth.label, truth.score

    @staticmethod
    def _get_accidental_dignities(
        planet: str,
        house: int,
        is_retrograde: bool,
        planet_lon: float,
        sun_lon: float,
        receptions: list[PlanetaryReception],
        sign: str = "",
        is_day_chart: bool = True,
        mercury_rises_before_sun: bool = True,
        policy: DignityComputationPolicy | None = None,
        chart_positions: dict[str, float] | None = None,
    ) -> tuple[list[str], int, AccidentalDignityTruth, SectTruth]:
        policy = DignityComputationPolicy() if policy is None else policy
        dignities: list[str] = []
        score = 0
        conditions: list[AccidentalDignityCondition] = []

        house_condition: AccidentalDignityCondition | None = None
        if policy.accidental.include_house_strength and house in ANGULAR_HOUSES:
            house_condition = AccidentalDignityCondition("house", "angular", f"Angular (H{house})", SCORE_ANGULAR)
        elif policy.accidental.include_house_strength and house in SUCCEDENT_HOUSES:
            house_condition = AccidentalDignityCondition("house", "succedent", f"Succedent (H{house})", SCORE_SUCCEDENT)
        elif policy.accidental.include_house_strength and house in CADENT_HOUSES:
            house_condition = AccidentalDignityCondition("house", "cadent", f"Cadent (H{house})", SCORE_CADENT)

        if house_condition is not None:
            dignities.append(house_condition.label)
            conditions.append(house_condition)
            score += house_condition.score

        motion_condition: AccidentalDignityCondition | None = None
        if policy.accidental.include_motion:
            if is_retrograde:
                motion_condition = AccidentalDignityCondition("motion", "retrograde", "Retrograde", SCORE_RETROGRADE)
            else:
                motion_condition = AccidentalDignityCondition("motion", "direct", "Direct", SCORE_DIRECT)

            dignities.append(motion_condition.label)
            conditions.append(motion_condition)
            score += motion_condition.score

        solar_truth = SolarConditionTruth(False)
        solar_policy = policy.accidental.solar
        if solar_policy.include_for_luminaries or planet not in ("Sun", "Moon"):
            dist = abs((planet_lon % 360) - (sun_lon % 360))
            dist = min(dist, 360 - dist)
            if solar_policy.include_cazimi and dist <= 0.283:
                solar_truth = SolarConditionTruth(True, "cazimi", "Cazimi", SCORE_CAZIMI, dist)
            elif solar_policy.include_combust and dist <= 8.0:
                solar_truth = SolarConditionTruth(True, "combust", "Combust", SCORE_COMBUST, dist)
            elif solar_policy.include_under_sunbeams and dist <= 17.0:
                solar_truth = SolarConditionTruth(True, "under_sunbeams", "Under Sunbeams", SCORE_SUNBEAMS, dist)
            else:
                solar_truth = SolarConditionTruth(False, None, None, 0, dist)

        if solar_truth.present and solar_truth.label is not None:
            solar_condition = AccidentalDignityCondition(
                "solar",
                solar_truth.condition or "solar_condition",
                solar_truth.label,
                solar_truth.score,
            )
            dignities.append(solar_condition.label)
            conditions.append(solar_condition)
            score += solar_condition.score

        reception_truth: list[MutualReceptionTruth] = []
        for relation in receptions:
            if relation.mode is not ReceptionMode.MUTUAL:
                continue
            if relation.basis is ReceptionBasis.DOMICILE:
                label = f"Mutual Reception ({relation.host_planet})"
                reception = MutualReceptionTruth(relation.host_planet, "domicile", label, SCORE_MR_DOMICILE)
            elif relation.basis is ReceptionBasis.EXALTATION:
                label = f"Mutual Exalt. ({relation.host_planet})"
                reception = MutualReceptionTruth(relation.host_planet, "exaltation", label, SCORE_MR_EXALTATION)
            else:
                continue
            reception_truth.append(reception)
            condition = AccidentalDignityCondition("mutual_reception", reception.reception_type, reception.label, reception.score)
            dignities.append(condition.label)
            conditions.append(condition)
            score += condition.score

        sect_truth = DignitiesService._build_sect_truth(
            planet=planet,
            sign=sign,
            house=house,
            is_day_chart=is_day_chart,
            mercury_rises_before_sun=mercury_rises_before_sun,
        )

        hayz_condition: AccidentalDignityCondition | None = None
        if policy.accidental.sect.include_hayz and sign and sect_truth.in_hayz:
            hayz_condition = AccidentalDignityCondition("sect", "hayz", "In Hayz", 2)
            dignities.append(hayz_condition.label)
            conditions.append(hayz_condition)
            score += hayz_condition.score

        halb_condition: AccidentalDignityCondition | None = None
        if hayz_condition is None and sign and is_in_halb(
            planet, sign, house, is_day_chart, mercury_rises_before_sun
        ):
            halb_condition = AccidentalDignityCondition("sect", "halb", "In Halb", SCORE_HALB)
            dignities.append(halb_condition.label)
            conditions.append(halb_condition)
            score += halb_condition.score

        joy_condition: AccidentalDignityCondition | None = None
        if is_in_joy(planet, house):
            joy_condition = AccidentalDignityCondition("joy", "joy", f"In Joy (H{house})", SCORE_JOY)
            dignities.append(joy_condition.label)
            conditions.append(joy_condition)
            score += joy_condition.score

        # -- Oriental / Occidental --
        # For superior planets (Mars/Jupiter/Saturn): oriental is beneficial (+2),
        # occidental is debilitating (-2).  For inferior planets (Mercury/Venus):
        # the reverse — occidental is beneficial, oriental is debilitating.
        oriental_condition: AccidentalDignityCondition | None = None
        phase = oriental_occidental(planet, planet_lon, sun_lon)
        if phase is not None:
            is_superior = planet in _SUPERIOR_PLANETS
            if phase == "oriental":
                phase_score = SCORE_ORIENTAL if is_superior else SCORE_OCCIDENTAL
                oriental_condition = AccidentalDignityCondition(
                    "phase", "oriental", "Oriental", phase_score,
                )
            else:
                phase_score = SCORE_OCCIDENTAL if is_superior else SCORE_ORIENTAL
                oriental_condition = AccidentalDignityCondition(
                    "phase", "occidental", "Occidental", phase_score,
                )
            dignities.append(oriental_condition.label)
            conditions.append(oriental_condition)
            score += oriental_condition.score

        # -- Besieging --
        besieged_condition: AccidentalDignityCondition | None = None
        if chart_positions is not None:
            besieged = is_besieged(planet_lon, chart_positions, planet_name=planet)
            if besieged is not None:
                left, right = besieged
                besieged_condition = AccidentalDignityCondition(
                    "besieging", "besieged",
                    f"Besieged ({left}/{right})", SCORE_BESIEGED,
                )
                dignities.append(besieged_condition.label)
                conditions.append(besieged_condition)
                score += besieged_condition.score

        accidental_truth = AccidentalDignityTruth(
            conditions=conditions,
            house_condition=house_condition,
            motion_condition=motion_condition,
            solar_condition=solar_truth,
            mutual_receptions=reception_truth,
            hayz_condition=hayz_condition,
            halb_condition=halb_condition,
            joy_condition=joy_condition,
            oriental_condition=oriental_condition,
            besieged_condition=besieged_condition,
        )

        return dignities, score, accidental_truth, sect_truth

    @staticmethod
    def _build_sect_truth(
        planet: str,
        sign: str,
        house: int,
        is_day_chart: bool,
        mercury_rises_before_sun: bool,
    ) -> SectTruth:
        actual_hemisphere = "above" if 7 <= house <= 12 else "below"
        actual_gender = "masculine" if sign in MASCULINE_SIGNS else "feminine"
        preferred_hemisphere = PREFERRED_HEMISPHERE.get(planet)
        preferred_gender = PREFERRED_GENDER.get(planet)
        planet_sect = SECT.get(planet)
        if planet_sect == "sect_light":
            planet_sect = "diurnal" if mercury_rises_before_sun else "nocturnal"

        hemisphere_matches = (
            True if preferred_hemisphere is None else preferred_hemisphere == actual_hemisphere
        )
        gender_matches = (
            True if preferred_gender in (None, "either") else preferred_gender == actual_gender
        )
        in_sect = is_in_sect(planet, is_day_chart, mercury_rises_before_sun)
        in_hayz = sign != "" and is_in_hayz(planet, sign, house, is_day_chart, mercury_rises_before_sun)

        return SectTruth(
            is_day_chart=is_day_chart,
            sect_light="Sun" if is_day_chart else "Moon",
            planet_sect=planet_sect,
            mercury_rises_before_sun=mercury_rises_before_sun,
            in_sect=in_sect,
            in_hayz=in_hayz,
            preferred_hemisphere=preferred_hemisphere,
            actual_hemisphere=actual_hemisphere,
            hemisphere_matches=hemisphere_matches,
            preferred_gender=preferred_gender,
            actual_gender=actual_gender,
            gender_matches=gender_matches,
        )

    @staticmethod
    def _validate_policy(policy: DignityComputationPolicy) -> None:
        if policy.essential.doctrine is not EssentialDignityDoctrine.TRADITIONAL_CLASSIC_7:
            raise ValueError(f"Unsupported essential dignity doctrine: {policy.essential.doctrine}")
        if policy.accidental.sect.mercury_sect_model is not MercurySectModel.LONGITUDE_HEURISTIC:
            raise ValueError(f"Unsupported Mercury sect model: {policy.accidental.sect.mercury_sect_model}")

    @staticmethod
    def _mercury_rises_before_sun(
        mercury_lon: float,
        sun_lon: float,
        policy: DignityComputationPolicy,
    ) -> bool:
        if policy.accidental.sect.mercury_sect_model is not MercurySectModel.LONGITUDE_HEURISTIC:
            raise ValueError(f"Unsupported Mercury sect model: {policy.accidental.sect.mercury_sect_model}")
        mercury_diff = (mercury_lon - sun_lon + 360.0) % 360.0
        return mercury_diff > 180.0

    @staticmethod
    def _score_polarity(score: int) -> ConditionPolarity:
        if score > 0:
            return ConditionPolarity.STRENGTHENING
        if score < 0:
            return ConditionPolarity.WEAKENING
        return ConditionPolarity.NEUTRAL

    @staticmethod
    def _classify_essential_truth(truth: EssentialDignityTruth) -> EssentialDignityClassification:
        kind_map = {
            "Domicile": EssentialDignityKind.DOMICILE,
            "Exaltation": EssentialDignityKind.EXALTATION,
            "Detriment": EssentialDignityKind.DETRIMENT,
            "Fall": EssentialDignityKind.FALL,
            "Peregrine": EssentialDignityKind.PEREGRINE,
        }
        return EssentialDignityClassification(
            kind=kind_map[truth.label],
            polarity=DignitiesService._score_polarity(truth.score),
        )

    @staticmethod
    def _classify_accidental_condition(
        condition: AccidentalDignityCondition,
    ) -> AccidentalConditionClassification:
        kind_map = {
            ("house", "angular"): AccidentalConditionKind.ANGULAR,
            ("house", "succedent"): AccidentalConditionKind.SUCCEDENT,
            ("house", "cadent"): AccidentalConditionKind.CADENT,
            ("motion", "direct"): AccidentalConditionKind.DIRECT,
            ("motion", "retrograde"): AccidentalConditionKind.RETROGRADE,
            ("solar", "cazimi"): AccidentalConditionKind.CAZIMI,
            ("solar", "combust"): AccidentalConditionKind.COMBUST,
            ("solar", "under_sunbeams"): AccidentalConditionKind.UNDER_SUNBEAMS,
            ("mutual_reception", "domicile"): AccidentalConditionKind.MUTUAL_RECEPTION,
            ("mutual_reception", "exaltation"): AccidentalConditionKind.MUTUAL_EXALTATION,
            ("sect", "hayz"): AccidentalConditionKind.HAYZ,
            ("sect", "halb"): AccidentalConditionKind.HALB,
            ("joy", "joy"): AccidentalConditionKind.JOY,
            ("phase", "oriental"): AccidentalConditionKind.ORIENTAL,
            ("phase", "occidental"): AccidentalConditionKind.OCCIDENTAL,
            ("besieging", "besieged"): AccidentalConditionKind.BESIEGED,
        }
        return AccidentalConditionClassification(
            kind=kind_map[(condition.category, condition.code)],
            category=condition.category,
            polarity=DignitiesService._score_polarity(condition.score),
            score=condition.score,
            label=condition.label,
        )

    @staticmethod
    def _classify_accidental_truth(
        truth: AccidentalDignityTruth,
    ) -> AccidentalDignityClassification:
        return AccidentalDignityClassification(
            conditions=[
                DignitiesService._classify_accidental_condition(condition)
                for condition in truth.conditions
            ]
        )

    @staticmethod
    def _classify_sect_truth(truth: SectTruth) -> SectClassification:
        if truth.in_hayz:
            state = SectStateKind.IN_HAYZ
        elif truth.in_sect:
            state = SectStateKind.IN_SECT
        else:
            state = SectStateKind.OUT_OF_SECT
        return SectClassification(state=state, in_sect=truth.in_sect, in_hayz=truth.in_hayz)

    @staticmethod
    def _classify_solar_truth(truth: SolarConditionTruth) -> SolarConditionClassification:
        kind_map = {
            None: SolarConditionKind.NONE,
            "cazimi": SolarConditionKind.CAZIMI,
            "combust": SolarConditionKind.COMBUST,
            "under_sunbeams": SolarConditionKind.UNDER_SUNBEAMS,
        }
        return SolarConditionClassification(
            kind=kind_map[truth.condition],
            polarity=DignitiesService._score_polarity(truth.score),
            present=truth.present,
        )

    @staticmethod
    def _classify_reception_truths(
        truths: list[MutualReceptionTruth],
    ) -> list[ReceptionClassification]:
        kind_map = {
            "domicile": ReceptionKind.DOMICILE,
            "exaltation": ReceptionKind.EXALTATION,
        }
        return [
            ReceptionClassification(
                kind=kind_map[truth.reception_type],
                polarity=DignitiesService._score_polarity(truth.score),
                other_planet=truth.other_planet,
                label=truth.label,
                score=truth.score,
            )
            for truth in truths
        ]

    @staticmethod
    def _derive_condition_state(
        strengthening_count: int,
        weakening_count: int,
    ) -> PlanetaryConditionState:
        if strengthening_count > 0 and weakening_count == 0:
            return PlanetaryConditionState.REINFORCED
        if weakening_count > 0 and strengthening_count == 0:
            return PlanetaryConditionState.WEAKENED
        return PlanetaryConditionState.MIXED

    @staticmethod
    def _build_condition_profile(
        planet: str,
        essential_truth: EssentialDignityTruth | None,
        accidental_truth: AccidentalDignityTruth,
        sect_truth: SectTruth | None,
        solar_truth: SolarConditionTruth,
        all_receptions: list[PlanetaryReception],
        admitted_receptions: list[PlanetaryReception],
        mutual_reception_truth: list[MutualReceptionTruth],
    ) -> PlanetaryConditionProfile:
        essential_classification = (
            None if essential_truth is None else DignitiesService._classify_essential_truth(essential_truth)
        )
        accidental_classification = DignitiesService._classify_accidental_truth(accidental_truth)
        sect_classification = (
            None if sect_truth is None else DignitiesService._classify_sect_truth(sect_truth)
        )
        solar_classification = DignitiesService._classify_solar_truth(solar_truth)
        reception_classification = DignitiesService._classify_reception_truths(mutual_reception_truth)
        scored_receptions = [
            reception for reception in admitted_receptions if reception.mode is ReceptionMode.MUTUAL
        ]

        polarities: list[ConditionPolarity] = []
        if essential_classification is not None:
            polarities.append(essential_classification.polarity)
        polarities.extend(condition.polarity for condition in accidental_classification.conditions)

        strengthening_count = sum(
            1 for polarity in polarities if polarity is ConditionPolarity.STRENGTHENING
        )
        weakening_count = sum(
            1 for polarity in polarities if polarity is ConditionPolarity.WEAKENING
        )
        neutral_count = sum(
            1 for polarity in polarities if polarity is ConditionPolarity.NEUTRAL
        )

        return PlanetaryConditionProfile(
            planet=planet,
            essential_truth=essential_truth,
            essential_classification=essential_classification,
            accidental_truth=accidental_truth,
            accidental_classification=accidental_classification,
            sect_truth=sect_truth,
            sect_classification=sect_classification,
            solar_truth=solar_truth,
            solar_classification=solar_classification,
            all_receptions=all_receptions,
            admitted_receptions=admitted_receptions,
            scored_receptions=scored_receptions,
            mutual_reception_truth=mutual_reception_truth,
            reception_classification=reception_classification,
            strengthening_count=strengthening_count,
            weakening_count=weakening_count,
            neutral_count=neutral_count,
            state=DignitiesService._derive_condition_state(strengthening_count, weakening_count),
        )

    @staticmethod
    def _build_chart_condition_profile(
        profiles: list[PlanetaryConditionProfile],
    ) -> ChartConditionProfile:
        ordered_profiles = sorted(
            profiles,
            key=lambda profile: _PLANET_ORDER.index(profile.planet)
            if profile.planet in _PLANET_ORDER else 99,
        )

        reinforced_count = sum(
            1 for profile in ordered_profiles if profile.state is PlanetaryConditionState.REINFORCED
        )
        mixed_count = sum(
            1 for profile in ordered_profiles if profile.state is PlanetaryConditionState.MIXED
        )
        weakened_count = sum(
            1 for profile in ordered_profiles if profile.state is PlanetaryConditionState.WEAKENED
        )

        strengthening_total = sum(profile.strengthening_count for profile in ordered_profiles)
        weakening_total = sum(profile.weakening_count for profile in ordered_profiles)
        neutral_total = sum(profile.neutral_count for profile in ordered_profiles)

        essential_strengthening_total = sum(
            1
            for profile in ordered_profiles
            if profile.essential_classification is not None
            and profile.essential_classification.polarity is ConditionPolarity.STRENGTHENING
        )
        essential_weakening_total = sum(
            1
            for profile in ordered_profiles
            if profile.essential_classification is not None
            and profile.essential_classification.polarity is ConditionPolarity.WEAKENING
        )
        accidental_strengthening_total = sum(
            sum(
                1 for condition in profile.accidental_classification.conditions
                if condition.polarity is ConditionPolarity.STRENGTHENING
            )
            for profile in ordered_profiles
        )
        accidental_weakening_total = sum(
            sum(
                1 for condition in profile.accidental_classification.conditions
                if condition.polarity is ConditionPolarity.WEAKENING
            )
            for profile in ordered_profiles
        )
        reception_participation_total = sum(len(profile.admitted_receptions) for profile in ordered_profiles)

        def _profile_rank(profile: PlanetaryConditionProfile) -> tuple[int, int, int, int]:
            return (
                profile.strengthening_count - profile.weakening_count,
                profile.strengthening_count,
                -profile.weakening_count,
                -_PLANET_ORDER.index(profile.planet) if profile.planet in _PLANET_ORDER else -99,
            )

        strongest_rank = max((_profile_rank(profile) for profile in ordered_profiles), default=None)
        weakest_rank = min((_profile_rank(profile) for profile in ordered_profiles), default=None)

        strongest_planets = [
            profile.planet for profile in ordered_profiles
            if strongest_rank is not None and _profile_rank(profile) == strongest_rank
        ]
        weakest_planets = [
            profile.planet for profile in ordered_profiles
            if weakest_rank is not None and _profile_rank(profile) == weakest_rank
        ]

        return ChartConditionProfile(
            profiles=ordered_profiles,
            reinforced_count=reinforced_count,
            mixed_count=mixed_count,
            weakened_count=weakened_count,
            strengthening_total=strengthening_total,
            weakening_total=weakening_total,
            neutral_total=neutral_total,
            strongest_planets=strongest_planets,
            weakest_planets=weakest_planets,
            essential_strengthening_total=essential_strengthening_total,
            essential_weakening_total=essential_weakening_total,
            accidental_strengthening_total=accidental_strengthening_total,
            accidental_weakening_total=accidental_weakening_total,
            reception_participation_total=reception_participation_total,
        )

    @staticmethod
    def _build_condition_network_profile(
        chart_profile: ChartConditionProfile,
    ) -> ConditionNetworkProfile:
        ordered_profiles = chart_profile.profiles
        edges: list[ConditionNetworkEdge] = []
        node_map: dict[str, ConditionNetworkNode] = {
            profile.planet: ConditionNetworkNode(planet=profile.planet, profile=profile)
            for profile in ordered_profiles
        }

        for profile in ordered_profiles:
            for reception in profile.admitted_receptions:
                edges.append(
                    ConditionNetworkEdge(
                        source_planet=reception.receiving_planet,
                        target_planet=reception.host_planet,
                        basis=reception.basis,
                        mode=reception.mode,
                    )
                )

        edges.sort(
            key=lambda edge: (
                _PLANET_ORDER.index(edge.source_planet) if edge.source_planet in _PLANET_ORDER else 99,
                _PLANET_ORDER.index(edge.target_planet) if edge.target_planet in _PLANET_ORDER else 99,
                0 if edge.mode is ReceptionMode.MUTUAL else 1,
                0 if edge.basis is ReceptionBasis.DOMICILE else 1,
            )
        )

        for edge in edges:
            node_map[edge.source_planet].outgoing_count += 1
            node_map[edge.target_planet].incoming_count += 1
            if edge.is_mutual:
                node_map[edge.source_planet].mutual_count += 1
            node_map[edge.source_planet].total_degree += 1
            node_map[edge.target_planet].total_degree += 1

        nodes = [
            node_map[planet]
            for planet in _PLANET_ORDER
            if planet in node_map
        ]

        isolated_planets = [node.planet for node in nodes if node.is_isolated]
        max_degree = max((node.total_degree for node in nodes), default=0)
        most_connected_planets = [
            node.planet for node in nodes
            if node.total_degree == max_degree and max_degree > 0
        ]
        mutual_edge_count = sum(1 for edge in edges if edge.is_mutual)
        unilateral_edge_count = sum(1 for edge in edges if not edge.is_mutual)

        return ConditionNetworkProfile(
            nodes=nodes,
            edges=edges,
            isolated_planets=isolated_planets,
            most_connected_planets=most_connected_planets,
            mutual_edge_count=mutual_edge_count,
            unilateral_edge_count=unilateral_edge_count,
        )

    @staticmethod
    def _find_receptions(
        planet_signs: dict[str, str],
        bases: tuple[ReceptionBasis, ...],
    ) -> dict[str, list[PlanetaryReception]]:
        receptions: dict[str, list[PlanetaryReception]] = {}
        planets = [planet for planet in _PLANET_ORDER if planet in planet_signs]

        basis_maps = {
            ReceptionBasis.DOMICILE: DOMICILE,
            ReceptionBasis.EXALTATION: EXALTATION,
        }

        for planet in planets:
            sign = planet_signs[planet]
            for other in planets:
                if other == planet:
                    continue
                other_sign = planet_signs[other]
                for basis in bases:
                    host_matching_signs = tuple(basis_maps[basis].get(other, ()))
                    if sign not in host_matching_signs:
                        continue
                    reverse_matching_signs = tuple(basis_maps[basis].get(planet, ()))
                    mode = (
                        ReceptionMode.MUTUAL
                        if other_sign in reverse_matching_signs
                        else ReceptionMode.UNILATERAL
                    )
                    receptions.setdefault(planet, []).append(
                        PlanetaryReception(
                            receiving_planet=planet,
                            host_planet=other,
                            basis=basis,
                            mode=mode,
                            receiving_sign=sign,
                            host_sign=other_sign,
                            host_matching_signs=host_matching_signs,
                        )
                    )

        basis_order = {ReceptionBasis.DOMICILE: 0, ReceptionBasis.EXALTATION: 1}
        mode_order = {ReceptionMode.MUTUAL: 0, ReceptionMode.UNILATERAL: 1}
        for planet, items in receptions.items():
            items.sort(
                key=lambda reception: (
                    mode_order[reception.mode],
                    basis_order[reception.basis],
                    _PLANET_ORDER.index(reception.host_planet)
                    if reception.host_planet in _PLANET_ORDER else 99,
                )
            )
        return receptions

    @staticmethod
    def _policy_reception_bases(policy: DignityComputationPolicy) -> tuple[ReceptionBasis, ...]:
        bases: list[ReceptionBasis] = []
        if policy.accidental.mutual_reception.include_domicile:
            bases.append(ReceptionBasis.DOMICILE)
        if policy.accidental.mutual_reception.include_exaltation:
            bases.append(ReceptionBasis.EXALTATION)
        return tuple(bases)

    @staticmethod
    def _normalize_planet_positions(planet_positions: list[dict]) -> list[dict[str, object]]:
        if not isinstance(planet_positions, list):
            raise ValueError("planet_positions must be a list of dictionaries")

        normalized: list[dict[str, object]] = []
        seen_classic: set[str] = set()
        for index, pos in enumerate(planet_positions):
            if not isinstance(pos, dict):
                raise ValueError(f"planet_positions[{index}] must be a dictionary")

            name = pos.get("name")
            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"planet_positions[{index}].name must be a non-empty string")
            normalized_name = _normalize_dispositorship_subject_name(name)

            degree_value = pos.get("degree")
            try:
                degree = float(degree_value)
            except (TypeError, ValueError):
                raise ValueError(f"planet_positions[{index}].degree must be a real number") from None
            if not math.isfinite(degree):
                raise ValueError(f"planet_positions[{index}].degree must be finite")

            retro_value = pos.get("is_retrograde", False)
            if not isinstance(retro_value, bool):
                raise ValueError(f"planet_positions[{index}].is_retrograde must be a bool when provided")

            if normalized_name in CLASSIC_7:
                if normalized_name in seen_classic:
                    raise ValueError(f"planet_positions contains duplicate entry for classic planet {normalized_name!r}")
                seen_classic.add(normalized_name)

            normalized.append(
                {
                    "name": normalized_name,
                    "degree": degree,
                    "is_retrograde": retro_value,
                }
            )
        return normalized

    @staticmethod
    def _find_mutual_receptions(
        planet_signs: dict[str, str]
    ) -> dict[str, list[tuple[str, str]]]:
        receptions = DignitiesService._find_receptions(
            planet_signs,
            bases=DignitiesService._policy_reception_bases(DignityComputationPolicy()),
        )
        result: dict[str, list[tuple[str, str]]] = {}
        for planet, relations in receptions.items():
            for relation in relations:
                if relation.mode is ReceptionMode.MUTUAL:
                    result.setdefault(planet, []).append((relation.host_planet, relation.basis.value))
        return result

    @staticmethod
    def _validate_dispositorship_policy(policy: DispositorshipComputationPolicy) -> None:
        if policy.subject.subject_set is not DispositorshipSubjectSet.CLASSIC_7:
            raise ValueError(f"Unsupported dispositorship subject set: {policy.subject.subject_set}")
        if policy.rulership.doctrine is not DispositorshipRulership.TRADITIONAL_DOMICILE:
            raise ValueError(f"Unsupported dispositorship rulership doctrine: {policy.rulership.doctrine}")
        if not policy.termination.final_requires_self_domicile:
            raise ValueError("Unsupported dispositorship termination policy: final dispositors must require self-domicile")
        if not policy.termination.cycles_are_terminal:
            raise ValueError("Unsupported dispositorship termination policy: cycles must remain terminal")

    @staticmethod
    def _dispositorship_subjects(
        signs_by_name: dict[str, str],
        policy: DispositorshipComputationPolicy,
    ) -> list[str]:
        if policy.ordering.use_dignity_order:
            return [planet for planet in _PLANET_ORDER if planet in signs_by_name]
        return [name for name in signs_by_name if name in CLASSIC_7]

    @staticmethod
    def _dispositor_of_sign(
        sign: str,
        policy: DispositorshipComputationPolicy,
    ) -> str:
        if policy.rulership.doctrine is not DispositorshipRulership.TRADITIONAL_DOMICILE:
            raise ValueError(f"Unsupported dispositorship rulership doctrine: {policy.rulership.doctrine}")
        for planet, signs in DOMICILE.items():
            if sign in signs:
                return planet
        raise ValueError(f"No dispositorship ruler found for sign {sign!r}")

    @staticmethod
    def _canonical_cycle(cycle_members: tuple[str, ...]) -> tuple[str, ...]:
        if not cycle_members:
            return ()
        best: tuple[str, ...] | None = None
        members = list(cycle_members)
        count = len(members)
        for index in range(count):
            rotated = tuple(members[index:] + members[:index])
            key = tuple(_PLANET_ORDER.index(name) if name in _PLANET_ORDER else 99 for name in rotated)
            if best is None:
                best = rotated
                best_key = key
                continue
            if key < best_key:
                best = rotated
                best_key = key
        return best if best is not None else ()

    @staticmethod
    def _unique_terminal_cycles(chains: list[DispositorshipChain]) -> tuple[tuple[str, ...], ...]:
        unique: list[tuple[str, ...]] = []
        seen: set[tuple[str, ...]] = set()
        for chain in chains:
            if chain.termination_kind is not DispositorshipTerminationKind.TERMINAL_CYCLE:
                continue
            if chain.cycle_members in seen:
                continue
            seen.add(chain.cycle_members)
            unique.append(chain.cycle_members)
        return tuple(unique)

    @staticmethod
    def _derive_dispositorship_condition_state(
        subject_in_scope: bool,
        termination_kind: DispositorshipTerminationKind,
        initial_subject: str,
        terminal_subjects: tuple[str, ...],
    ) -> DispositorshipConditionState:
        if not subject_in_scope:
            return DispositorshipConditionState.OUT_OF_SCOPE
        if termination_kind is DispositorshipTerminationKind.TERMINAL_CYCLE:
            return DispositorshipConditionState.TERMINAL_CYCLE
        if termination_kind is DispositorshipTerminationKind.UNRESOLVED:
            return DispositorshipConditionState.UNRESOLVED
        if terminal_subjects == (initial_subject,):
            return DispositorshipConditionState.SELF_DISPOSED
        return DispositorshipConditionState.RESOLVED_TO_FINAL

    @staticmethod
    def _build_dispositorship_condition_profile(
        chain: DispositorshipChain,
    ) -> DispositorshipConditionProfile:
        return DispositorshipConditionProfile(
            initial_subject=chain.initial_subject,
            initial_sign=chain.initial_sign,
            subject_in_scope=chain.subject_in_scope,
            subject_has_dispositor=chain.subject_has_dispositor,
            termination_kind=chain.termination_kind,
            terminal_subjects=chain.terminal_subjects,
            cycle_members=chain.cycle_members,
            visited_subjects=chain.visited_subjects,
            chain_length=len(chain.visited_subjects),
            state=DignitiesService._derive_dispositorship_condition_state(
                chain.subject_in_scope,
                chain.termination_kind,
                chain.initial_subject,
                chain.terminal_subjects,
            ),
        )

    @staticmethod
    def _build_dispositorship_chart_condition_profile(
        profiles: list[DispositorshipConditionProfile],
    ) -> DispositorshipChartConditionProfile:
        final_dispositors = {
            terminal
            for profile in profiles
            if profile.termination_kind is DispositorshipTerminationKind.FINAL_DISPOSITOR
            for terminal in profile.terminal_subjects
        }
        cycles = {
            profile.cycle_members
            for profile in profiles
            if profile.termination_kind is DispositorshipTerminationKind.TERMINAL_CYCLE
        }
        has_mixed_terminals = (
            bool(final_dispositors) and bool(cycles)
        ) or (bool(final_dispositors or cycles) and any(
            profile.termination_kind is DispositorshipTerminationKind.UNRESOLVED
            for profile in profiles
        ))
        return DispositorshipChartConditionProfile(
            profiles=profiles,
            self_disposed_count=sum(
                1 for profile in profiles if profile.state is DispositorshipConditionState.SELF_DISPOSED
            ),
            resolved_to_final_count=sum(
                1 for profile in profiles if profile.state is DispositorshipConditionState.RESOLVED_TO_FINAL
            ),
            terminal_cycle_count=sum(
                1 for profile in profiles if profile.state is DispositorshipConditionState.TERMINAL_CYCLE
            ),
            unresolved_count=sum(
                1 for profile in profiles if profile.state is DispositorshipConditionState.UNRESOLVED
            ),
            out_of_scope_count=sum(
                1 for profile in profiles if profile.state is DispositorshipConditionState.OUT_OF_SCOPE
            ),
            final_dispositor_count=len(final_dispositors),
            cycle_count=len(cycles),
            has_mixed_terminals=has_mixed_terminals,
        )

    @staticmethod
    def _build_dispositorship_network_profile(
        profiles: list[DispositorshipConditionProfile],
        chains: list[DispositorshipChain],
    ) -> DispositorshipNetworkProfile:
        profile_map = {
            profile.initial_subject: profile
            for profile in profiles
            if profile.subject_in_scope and profile.initial_subject in _PLANET_ORDER
        }
        direct_relations: set[tuple[str, str]] = set()
        for chain in chains:
            if not chain.subject_in_scope or not chain.links:
                continue
            first = chain.links[0]
            if first.subject == first.dispositor:
                continue
            if first.dispositor not in profile_map:
                continue
            direct_relations.add((first.subject, first.dispositor))

        edges: list[DispositorshipNetworkEdge] = []
        for source, target in sorted(
            direct_relations,
            key=lambda pair: (
                _PLANET_ORDER.index(pair[0]) if pair[0] in _PLANET_ORDER else 99,
                _PLANET_ORDER.index(pair[1]) if pair[1] in _PLANET_ORDER else 99,
            ),
        ):
            reverse_present = (target, source) in direct_relations
            edges.append(
                DispositorshipNetworkEdge(
                    source_subject=source,
                    target_subject=target,
                    mode=(
                        DispositorshipNetworkEdgeMode.RECIPROCAL
                        if reverse_present else DispositorshipNetworkEdgeMode.UNILATERAL
                    ),
                )
            )

        outgoing = {name: 0 for name in profile_map}
        incoming = {name: 0 for name in profile_map}
        reciprocal_counts = {name: 0 for name in profile_map}
        for edge in edges:
            outgoing[edge.source_subject] += 1
            incoming[edge.target_subject] += 1
            if edge.mode is DispositorshipNetworkEdgeMode.RECIPROCAL:
                reciprocal_counts[edge.source_subject] += 1

        nodes = [
            DispositorshipNetworkNode(
                subject=subject,
                profile=profile_map[subject],
                outgoing_count=outgoing[subject],
                incoming_count=incoming[subject],
                reciprocal_count=reciprocal_counts[subject],
            )
            for subject in _PLANET_ORDER
            if subject in profile_map
        ]

        max_degree = max((node.degree_count for node in nodes), default=0)
        return DispositorshipNetworkProfile(
            nodes=nodes,
            edges=edges,
            isolated_subjects=[node.subject for node in nodes if node.is_isolated],
            most_connected_subjects=[
                node.subject for node in nodes if node.degree_count == max_degree and max_degree > 0
            ],
            reciprocal_edge_count=sum(
                1 for edge in edges if edge.mode is DispositorshipNetworkEdgeMode.RECIPROCAL
            ),
            unilateral_edge_count=sum(
                1 for edge in edges if edge.mode is DispositorshipNetworkEdgeMode.UNILATERAL
            ),
        )

    @staticmethod
    def _build_dispositorship_chain(
        initial_subject: str,
        signs_by_name: dict[str, str],
        policy: DispositorshipComputationPolicy,
    ) -> DispositorshipChain:
        initial_sign = signs_by_name[initial_subject]
        links: list[DispositorLink] = []
        visited_order: list[str] = []
        seen_index: dict[str, int] = {}
        current = initial_subject

        while True:
            if current not in seen_index:
                seen_index[current] = len(visited_order)
                visited_order.append(current)

            sign = signs_by_name[current]
            dispositor = DignitiesService._dispositor_of_sign(sign, policy)
            links.append(DispositorLink(subject=current, subject_sign=sign, dispositor=dispositor))

            if dispositor == current:
                return DispositorshipChain(
                    initial_subject=initial_subject,
                    initial_sign=initial_sign,
                    subject_in_scope=True,
                    subject_has_dispositor=True,
                    links=links,
                    visited_subjects=tuple(visited_order),
                    termination_kind=DispositorshipTerminationKind.FINAL_DISPOSITOR,
                    terminal_subjects=(current,),
                )

            if dispositor in seen_index:
                cycle_members = tuple(visited_order[seen_index[dispositor]:])
                canonical_cycle = DignitiesService._canonical_cycle(cycle_members)
                return DispositorshipChain(
                    initial_subject=initial_subject,
                    initial_sign=initial_sign,
                    subject_in_scope=True,
                    subject_has_dispositor=True,
                    links=links,
                    visited_subjects=tuple(visited_order),
                    termination_kind=DispositorshipTerminationKind.TERMINAL_CYCLE,
                    terminal_subjects=canonical_cycle,
                    cycle_members=canonical_cycle,
                )

            if dispositor not in signs_by_name:
                return DispositorshipChain(
                    initial_subject=initial_subject,
                    initial_sign=initial_sign,
                    subject_in_scope=True,
                    subject_has_dispositor=True,
                    links=links,
                    visited_subjects=tuple(visited_order),
                    termination_kind=DispositorshipTerminationKind.UNRESOLVED,
                )

            current = dispositor

    @staticmethod
    def _build_house_cusps(house_positions: list[dict]) -> list[float]:
        if not isinstance(house_positions, list):
            raise ValueError("house_positions must be a list of dictionaries")

        cusps = [0.0] * 12
        seen_numbers: set[int] = set()
        for index, pos in enumerate(house_positions):
            if not isinstance(pos, dict):
                raise ValueError(f"house_positions[{index}] must be a dictionary")

            number = pos.get("number")
            if not isinstance(number, int):
                raise ValueError(f"house_positions[{index}].number must be an int from 1 to 12")
            if not (1 <= number <= 12):
                raise ValueError(f"house_positions[{index}].number must be in the range 1..12")
            if number in seen_numbers:
                raise ValueError(f"house_positions contains duplicate cusp number {number}")
            seen_numbers.add(number)

            degree_value = pos.get("degree")
            try:
                degree = float(degree_value)
            except (TypeError, ValueError):
                raise ValueError(f"house_positions[{index}].degree must be a real number") from None
            if not math.isfinite(degree):
                raise ValueError(f"house_positions[{index}].degree must be finite")

            cusps[number - 1] = degree

        missing = [number for number in range(1, 13) if number not in seen_numbers]
        if missing:
            raise ValueError(f"house_positions must contain exactly one cusp for each house 1..12; missing {missing}")
        return cusps

    @staticmethod
    def _get_house(degree: float, cusps: list[float]) -> int:
        degree = degree % 360
        for i in range(12):
            start = cusps[i]
            end   = cusps[(i + 1) % 12]
            if start <= end:
                if start <= degree < end:
                    return i + 1
            else:
                if degree >= start or degree < end:
                    return i + 1
        return 1


# ---------------------------------------------------------------------------
# Module-level convenience wrapper
# ---------------------------------------------------------------------------

_service = DignitiesService()


def calculate_dignities(
    planet_positions: list[dict],
    house_positions: list[dict],
    policy: DignityComputationPolicy | None = None,
) -> list[PlanetaryDignity]:
    """
    Calculate essential and accidental dignities.

    Parameters
    ----------
    planet_positions : list of {'name': str, 'degree': float, 'is_retrograde': bool}
    house_positions  : list of {'number': int, 'degree': float}
    policy           : optional DignityComputationPolicy
    """
    return _service.calculate_dignities(planet_positions, house_positions, policy=policy)


def calculate_receptions(
    planet_positions: list[dict],
    policy: DignityComputationPolicy | None = None,
) -> list[PlanetaryReception]:
    """Calculate formal reception relations for the Classic 7 planets present."""

    return _service.calculate_receptions(planet_positions, policy=policy)


def calculate_dispositorship(
    planet_positions: list[dict],
    policy: DispositorshipComputationPolicy | None = None,
) -> DispositorshipProfile:
    """Calculate chart dispositorship under explicit Phase 1 policy."""

    return _service.calculate_dispositorship(planet_positions, policy=policy)


def calculate_dispositorship_condition_profiles(
    planet_positions: list[dict],
    policy: DispositorshipComputationPolicy | None = None,
) -> list[DispositorshipConditionProfile]:
    """Calculate integrated per-subject dispositorship condition profiles."""

    return _service.calculate_dispositorship_condition_profiles(planet_positions, policy=policy)


def calculate_dispositorship_chart_condition_profile(
    planet_positions: list[dict],
    policy: DispositorshipComputationPolicy | None = None,
) -> DispositorshipChartConditionProfile:
    """Calculate the chart-wide dispositorship condition profile."""

    return _service.calculate_dispositorship_chart_condition_profile(planet_positions, policy=policy)


def calculate_dispositorship_network_profile(
    planet_positions: list[dict],
    policy: DispositorshipComputationPolicy | None = None,
) -> DispositorshipNetworkProfile:
    """Calculate the dispositorship network profile."""

    return _service.calculate_dispositorship_network_profile(planet_positions, policy=policy)


def calculate_dispositorship_subsystem_profile(
    planet_positions: list[dict],
    policy: DispositorshipComputationPolicy | None = None,
) -> DispositorshipSubsystemProfile:
    """Calculate the fully hardened dispositorship subsystem profile."""

    return _service.calculate_dispositorship_subsystem_profile(planet_positions, policy=policy)


def compare_dispositorship(
    planet_positions: list[dict],
    doctrine_profiles: list[tuple[str, DispositorshipComputationPolicy | None]],
) -> DispositorshipComparisonBundle:
    """Compare multiple named dispositorship profiles side by side."""

    return _service.compare_dispositorship(planet_positions, doctrine_profiles)


def calculate_condition_profiles(
    planet_positions: list[dict],
    house_positions: list[dict],
    policy: DignityComputationPolicy | None = None,
) -> list[PlanetaryConditionProfile]:
    """Calculate integrated per-planet condition profiles."""

    return _service.calculate_condition_profiles(planet_positions, house_positions, policy=policy)


def calculate_chart_condition_profile(
    planet_positions: list[dict],
    house_positions: list[dict],
    policy: DignityComputationPolicy | None = None,
) -> ChartConditionProfile:
    """Calculate the chart-wide condition profile."""

    return _service.calculate_chart_condition_profile(planet_positions, house_positions, policy=policy)


def calculate_condition_network_profile(
    planet_positions: list[dict],
    house_positions: list[dict],
    policy: DignityComputationPolicy | None = None,
) -> ConditionNetworkProfile:
    """Calculate the reception / condition network profile."""

    return _service.calculate_condition_network_profile(planet_positions, house_positions, policy=policy)


# ---------------------------------------------------------------------------
# Sect Light
# ---------------------------------------------------------------------------

def sect_light(
    sun_longitude: float,
    asc_longitude: float,
) -> str:
    """
    Determine the sect light of the chart.

    In a diurnal (day) chart, the Sun is above the horizon (houses 7–12),
    and the Sun is the sect light.
    In a nocturnal (night) chart, the Moon is the sect light.

    Parameters
    ----------
    sun_longitude : Sun's ecliptic longitude
    asc_longitude : Ascendant longitude

    Returns
    -------
    "Sun" (day chart) or "Moon" (night chart)
    """
    # In zodiac-order house reckoning, the Sun is above the horizon when it
    # falls in houses 7–12, which corresponds to the arc from Descendant to
    # Ascendant: diff >= 180.
    above = (sun_longitude - asc_longitude) % 360.0 >= 180.0
    return "Sun" if above else "Moon"


def is_day_chart(sun_longitude: float, asc_longitude: float) -> bool:
    """Return True if this is a diurnal (day) chart."""
    return sect_light(sun_longitude, asc_longitude) == "Sun"


# ---------------------------------------------------------------------------
# Almuten Figuris
# ---------------------------------------------------------------------------

def almuten_figuris(
    planet_positions: dict[str, float],
    asc_longitude: float,
    is_day: bool,
) -> str:
    """
    Find the Almuten Figuris — the planet with the most essential dignities
    across the key chart points (Sun, Moon, Ascendant).

    For each of the Classic 7 planets, sum the dignity score it holds at
    the Sun's degree, Moon's degree, and ASC degree.
    The planet with the highest total score is the Almuten Figuris.

    Parameters
    ----------
    planet_positions : dict of body → longitude (must include "Sun", "Moon")
    asc_longitude    : Ascendant longitude
    is_day           : True for day chart (affects triplicity)

    Returns
    -------
    Planet name (string)
    """
    from .longevity import dignity_score_at

    key_points = [
        planet_positions.get("Sun", 0.0),
        planet_positions.get("Moon", 0.0),
        asc_longitude,
    ]

    scores: dict[str, int] = {}
    for planet in CLASSIC_7:
        total = sum(dignity_score_at(planet, lon, is_day) for lon in key_points)
        scores[planet] = total

    return max(scores, key=lambda p: scores[p])


# ---------------------------------------------------------------------------
# Mutual Reception
# ---------------------------------------------------------------------------

def mutual_receptions(
    planet_positions: dict[str, float],
    by_exaltation: bool = False,
) -> list[tuple[str, str, str]]:
    """
    Find all mutual receptions between the Classic 7 planets.

    A mutual reception by domicile occurs when planet A is in a sign ruled
    by planet B AND planet B is in a sign ruled by planet A.
    E.g., Venus in Aries and Mars in Taurus (Mars rules Aries, Venus rules Taurus).

    Parameters
    ----------
    planet_positions : dict of body → tropical longitude (degrees)
    by_exaltation    : also check mutual receptions by exaltation (default False)

    Returns
    -------
    List of (planet_a, planet_b, reception_type) tuples.
    reception_type is "Domicile", "Exaltation", or "Mixed"
    (Mixed = one by domicile, one by exaltation).
    """
    from .constants import SIGNS

    def _sign_of(lon: float) -> str:
        idx = int(lon % 360.0 / 30.0)
        return SIGNS[min(idx, 11)]

    def _domicile_ruler(sign: str) -> list[str]:
        return [p for p, signs in DOMICILE.items() if sign in signs]

    def _exalt_ruler(sign: str) -> list[str]:
        return [p for p, signs in EXALTATION.items() if sign in signs]

    planets = [p for p in planet_positions if p in CLASSIC_7]
    results: list[tuple[str, str, str]] = []
    seen: set[frozenset] = set()

    for i, pa in enumerate(planets):
        for pb in planets[i + 1:]:
            pair = frozenset([pa, pb])
            if pair in seen:
                continue

            sign_a = _sign_of(planet_positions[pa])
            sign_b = _sign_of(planet_positions[pb])

            dom_a = pa in _domicile_ruler(sign_b)   # pa rules sign_b
            dom_b = pb in _domicile_ruler(sign_a)   # pb rules sign_a

            if dom_a and dom_b:
                results.append((pa, pb, "Domicile"))
                seen.add(pair)
                continue

            if by_exaltation:
                ex_a = pa in _exalt_ruler(sign_b)
                ex_b = pb in _exalt_ruler(sign_a)

                if ex_a and ex_b:
                    results.append((pa, pb, "Exaltation"))
                    seen.add(pair)
                elif (dom_a and ex_b) or (ex_a and dom_b):
                    results.append((pa, pb, "Mixed"))
                    seen.add(pair)

    return results


# ---------------------------------------------------------------------------
# Phasis
# ---------------------------------------------------------------------------

def find_phasis(
    body: str,
    jd_start: float,
    jd_end: float,
    reader=None,
    beam_orb: float = 15.0,
    step_days: float = 1.0,
) -> list[dict]:
    """
    Find phasis events for a planet between jd_start and jd_end.

    A "phasis" occurs when a planet crosses the ±beam_orb threshold relative
    to the Sun — transitioning from invisible to visible (emerging) or
    visible to invisible (submerging).

    Parameters
    ----------
    body       : planet name (not Sun or Moon)
    jd_start   : search start JD
    jd_end     : search end JD
    reader     : SpkReader instance (optional; default reader used if None)
    beam_orb   : solar beam orb in degrees (traditional = 15°; combust = 8°)
    step_days  : step size for scanning

    Returns
    -------
    List of dicts: {"jd": float, "event": "Emerging"|"Submerging",
                    "elongation": float}
    """
    from .planets import planet_at
    from .spk_reader import get_reader as _get_reader
    if reader is None:
        reader = _get_reader()

    events = []
    jd = jd_start
    prev_in_beams: bool | None = None

    while jd <= jd_end:
        p = planet_at(body, jd, reader=reader)
        s = planet_at("Sun", jd, reader=reader)
        elong = abs((p.longitude - s.longitude + 180.0) % 360.0 - 180.0)
        in_beams = elong < beam_orb

        if prev_in_beams is not None and in_beams != prev_in_beams:
            # Refine crossing to within 0.5 days via bisection
            t0, t1 = jd - step_days, jd
            for _ in range(10):
                tm = (t0 + t1) / 2
                pm = planet_at(body, tm, reader=reader)
                sm = planet_at("Sun", tm, reader=reader)
                em = abs((pm.longitude - sm.longitude + 180.0) % 360.0 - 180.0)
                if (em < beam_orb) == prev_in_beams:
                    t0 = tm
                else:
                    t1 = tm
            refined_jd = (t0 + t1) / 2
            pm = planet_at(body, refined_jd, reader=reader)
            sm = planet_at("Sun", refined_jd, reader=reader)
            em = abs((pm.longitude - sm.longitude + 180.0) % 360.0 - 180.0)
            event_type = "Emerging" if prev_in_beams else "Submerging"
            events.append({"jd": refined_jd, "event": event_type, "elongation": em})

        prev_in_beams = in_beams
        jd += step_days

    return events
