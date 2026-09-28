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
    SECT / PREFERRED_HEMISPHERE / PREFERRED_GENDER — Halb/Hayz doctrine tables
    is_in_sect()          — sect membership test
    halb_required_hemisphere() — sect-relative Halb hemisphere
    is_in_hayz()          — Hayz test (Halb plus planetary sign gender)
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
from .decanates import chaldean_face
from .dignities_types import (
    CLASSIC_7,
    MODERN_OUTER_3,
    _MODERN_PLANET_ORDER,
    _PLANET_ORDER,
    _normalize_dispositorship_subject_name,
)
from .dignities_types import *  # noqa: F401, F403 — re-export full public surface
from .egyptian_bounds import EgyptianBoundsPolicy, bound_ruler
from .triplicity import (
    ParticipatingRulerPolicy as _ParticipatingRulerPolicy,
    triplicity_assignment_for,
    triplicity_score,
)

__all__ = [
    # Tables
    "DOMICILE", "MODERN_DOMICILE", "EXALTATION", "DETRIMENT", "MODERN_DETRIMENT", "FALL",
    "SECT", "PREFERRED_HEMISPHERE", "PREFERRED_GENDER",
    "PLANETARY_JOYS",
    # Enums
    "TruthEvaluationStatus",
    "HorizonHemisphere",
    "HorizonComputationMethod",
    "SectComponentKind",
    "ConditionPolarity",
    "PlanetarySolarPhaseKind",
    "EssentialDignityKind",
    "AccidentalConditionKind",
    "SectStateKind",
    "SolarConditionKind",
    "SolarProximityBand",
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
    "DignityScoringMode",
    "DignityNodeDoctrine",
    "EgyptianBoundsDoctrine",
    "TriplicityDoctrine",
    "ParticipatingRulerPolicy",
    "HalbHayzDoctrine",
    "MercurySectModel",
    # Policy dataclasses
    "EssentialDignityPolicy",
    "DignityScoringPolicy",
    "SolarConditionPolicy",
    "MutualReceptionPolicy",
    "SectHayzPolicy",
    "AccidentalDignityPolicy",
    "DignityComputationPolicy",
    "DignityHorizonFrame",
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
    "EssentialDignityComponentTruth",
    "PlanetarySolarPhaseTruth",
    "SolarProximityTruth",
    "BesiegingDependencyCompletenessTruth",
    "BesiegingTruth",
    "MercuryPhaseTruth",
    "HorizonTruth",
    "SectComponentTruth",
    "EssentialDignityTruth",
    "AccidentalDignityCondition",
    "AccidentalDignityEvaluationTruth",
    "SolarConditionTruth",
    "MutualReceptionTruth",
    "SectTruth",
    "AccidentalDignityTruth",
    "PlanetaryDignity",
    # Service
    "DignitiesService",
    # Module-level functions
    "is_in_sect",
    "halb_required_hemisphere",
    "is_in_hayz",
    "is_in_halb",
    "is_in_joy",
    "solar_proximity_truth",
    "planetary_solar_phase_truth",
    "oriental_occidental",
    "besieging_truth",
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
    "almuten_of_degree",
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

MODERN_DOMICILE: dict[str, list[str]] = {
    **DOMICILE,
    "Uranus":  ["Aquarius"],
    "Neptune": ["Pisces"],
    "Pluto":   ["Scorpio"],
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

MODERN_DETRIMENT: dict[str, list[str]] = {
    **DETRIMENT,
    "Uranus":  ["Leo"],
    "Neptune": ["Virgo"],
    "Pluto":   ["Taurus"],
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

SCORE_DOMICILE = 5
SCORE_EXALTATION = 4
SCORE_TRIPLICITY = 3
SCORE_BOUND = 2
SCORE_FACE = 1
SCORE_DETRIMENT = -5
SCORE_FALL = -4
SCORE_PEREGRINE = -5

SCORE_HOUSE = {
    1: 5, 10: 5,
    4: 4, 7: 4, 11: 4,
    2: 3, 5: 3,
    9: 2,
    3: 1,
    6: -2, 8: -2,
    12: -5,
}
SCORE_DIRECT = 4
SCORE_RETROGRADE = -5
SCORE_SWIFT = 2
SCORE_SLOW = -2
SCORE_CAZIMI     =  5   # within 17' of Sun
SCORE_COMBUST    = -5   # beyond cazimi through 8 degrees 30 minutes
SCORE_SUNBEAMS   = -4   # beyond combustion through 17 degrees
SCORE_FREE_FROM_BEAMS = 5
SCORE_MR_DOMICILE   = 5
SCORE_MR_EXALTATION = 4
SCORE_JOY        =  0   # tracked condition; not in Lilly's ready table
SCORE_HALB       =  0   # tracked condition; not in Lilly's ready table
SCORE_ORIENTAL   =  2   # oriental planet (favourable phase)
SCORE_OCCIDENTAL = -2   # occidental planet (unfavourable phase)
SCORE_BESIEGED   = -5   # enclosed between two malefics

SCORE_MOON_WAXING = 2
SCORE_MOON_WANING = -2
SCORE_BENEFIC_CONJUNCTION = 5
SCORE_BENEFIC_TRINE = 4
SCORE_BENEFIC_SEXTILE = 3
SCORE_MALEFIC_CONJUNCTION = -5
SCORE_MALEFIC_OPPOSITION = -4
SCORE_MALEFIC_SQUARE = -3
SCORE_NORTH_NODE_CONJUNCTION = 4
SCORE_SOUTH_NODE_CONJUNCTION = -4
SCORE_REGULUS_CONJUNCTION = 6
SCORE_SPICA_CONJUNCTION = 5
SCORE_ALGOL_CONJUNCTION = -5

# Lilly, Christian Astrology (1647), pp. 60-84: mean daily motions used by
# the ready table's swift/slow testimony. Values are decimal degrees/day.
LILLY_MEAN_DAILY_MOTION = {
    "Saturn": (2 + 1 / 60) / 60,
    "Jupiter": (4 + 59 / 60) / 60,
    "Mars": (31 + 27 / 60) / 60,
    "Sun": (59 + 8 / 60) / 60,
    "Venus": (59 + 8 / 60) / 60,
    "Mercury": (59 + 8 / 60) / 60,
    "Moon": 13 + 10 / 60 + 36 / 3600,
}

_PARTILE_ORB_DEG = 1.0
_FIXED_STAR_ORBS_DEG = {"Regulus": 6.0, "Spica": 5.0, "Algol": 5.0}

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

# Sect-relative Halb hemisphere: diurnal planets are above by day and below
# by night; nocturnal planets reverse that relation.
PREFERRED_HEMISPHERE: dict[str, dict[str, str]] = {
    "diurnal": {"day": "above", "night": "below"},
    "nocturnal": {"day": "below", "night": "above"},
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
    "Mercury": "neutral",
}


# ---------------------------------------------------------------------------
# Hayz / Sect standalone functions
# ---------------------------------------------------------------------------

def is_in_sect(
    planet: str,
    is_day_chart: bool,
    mercury_rises_before_sun: bool | None = None,
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
    if mercury_rises_before_sun is None:
        raise ValueError(
            "Mercury sect requires an explicit mercury_rises_before_sun phase."
        )
    # Mercury ("sect_light"): diurnal when rising before Sun, else nocturnal
    mercury_sect = "diurnal" if mercury_rises_before_sun else "nocturnal"
    return mercury_sect == ("diurnal" if is_day_chart else "nocturnal")


def halb_required_hemisphere(
    planet: str,
    is_day_chart: bool,
    mercury_rises_before_sun: bool | None = None,
) -> str | None:
    """
    Return the sect-relative hemisphere required for Halb.

    Under the admitted al-Biruni section 496 doctrine, diurnal planets belong
    above the horizon by day and below it by night; nocturnal planets reverse
    that relation. Mercury's effective sect must therefore be supplied through
    its explicit phase when Mercury is queried.
    """
    planet_sect = SECT.get(planet)
    if planet_sect is None:
        return None
    if planet_sect == "sect_light":
        if mercury_rises_before_sun is None:
            raise ValueError(
                "Mercury Halb requires an explicit mercury_rises_before_sun phase."
            )
        planet_sect = "diurnal" if mercury_rises_before_sun else "nocturnal"
    chart_key = "day" if is_day_chart else "night"
    return PREFERRED_HEMISPHERE[planet_sect][chart_key]


def is_in_hayz(
    planet: str,
    sign: str,
    house: int,
    is_day_chart: bool,
    mercury_rises_before_sun: bool | None = None,
) -> bool:
    """
    Return True if the planet is in Hayz under the admitted doctrine.

    Hayz is Halb (the correct sect-relative hemisphere) plus placement in a
    sign of the planet's own gender. Mercury is neutral in the admitted source
    and no gender-assignment rule is admitted, so Mercury never receives an
    invented Hayz judgment.

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

    if not is_in_halb(
        planet,
        sign,
        house,
        is_day_chart,
        mercury_rises_before_sun,
    ):
        return False

    preferred_gender = PREFERRED_GENDER.get(planet)
    if preferred_gender == "masculine":
        return sign in MASCULINE_SIGNS
    if preferred_gender == "feminine":
        return sign in FEMININE_SIGNS
    return False


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
    mercury_rises_before_sun: bool | None = None,
) -> bool:
    """
    Return True if the planet occupies its sect-relative Halb hemisphere.

    The ``sign`` parameter remains in the public signature for compatibility;
    sign gender belongs to Hayz, not Halb, and is deliberately not consulted.
    """
    if planet not in SECT:
        return False

    if not 1 <= house <= 12:
        raise ValueError(f"house must be in 1–12, got {house!r}")
    required = halb_required_hemisphere(
        planet,
        is_day_chart,
        mercury_rises_before_sun,
    )
    actual = "above" if 7 <= house <= 12 else "below"
    return required is not None and actual == required


# -- Superior / inferior planet classification for oriental/occidental ------

_SUPERIOR_PLANETS = {"Mars", "Jupiter", "Saturn"}
_INFERIOR_PLANETS = {"Mercury", "Venus"}
_PLANETARY_SOLAR_PHASE_BODIES = _SUPERIOR_PLANETS | _INFERIOR_PLANETS
_PLANETARY_SOLAR_PHASE_BOUNDARY_TOLERANCE_DEG = 1e-12
_SOLAR_CAZIMI_LIMIT_DEG = 17.0 / 60.0
_SOLAR_COMBUST_LIMIT_DEG = 8.5
_SOLAR_BEAMS_LIMIT_DEG = 17.0
_SOLAR_BAND_BOUNDARY_TOLERANCE_DEG = 1e-12


def _within_solar_band_limit(distance: float, limit: float) -> bool:
    """Apply one inclusive solar-band boundary with arithmetic tolerance."""

    return distance < limit or math.isclose(
        distance,
        limit,
        rel_tol=0.0,
        abs_tol=_SOLAR_BAND_BOUNDARY_TOLERANCE_DEG,
    )


def solar_proximity_truth(
    planet: str,
    planet_lon: float,
    sun_lon: float,
) -> SolarProximityTruth:
    """Return the raw exclusive solar-distance band before policy assembly."""

    if not math.isfinite(planet_lon) or not math.isfinite(sun_lon):
        raise ValueError("planet_lon and sun_lon must be finite")

    separation = abs((planet_lon % 360.0) - (sun_lon % 360.0))
    distance = min(separation, 360.0 - separation)
    if planet == "Sun":
        return SolarProximityTruth(
            status=TruthEvaluationStatus.NOT_EVALUABLE,
            band=None,
            distance_from_sun_deg=distance,
            reason="solar_proximity_not_applicable_to_sun",
        )

    if _within_solar_band_limit(distance, _SOLAR_CAZIMI_LIMIT_DEG):
        band = SolarProximityBand.CAZIMI
    elif _within_solar_band_limit(distance, _SOLAR_COMBUST_LIMIT_DEG):
        band = SolarProximityBand.COMBUST
    elif _within_solar_band_limit(distance, _SOLAR_BEAMS_LIMIT_DEG):
        band = SolarProximityBand.UNDER_SUNBEAMS
    else:
        band = SolarProximityBand.CLEAR
    return SolarProximityTruth(
        status=TruthEvaluationStatus.EVALUATED,
        band=band,
        distance_from_sun_deg=distance,
    )


def planetary_solar_phase_truth(
    planet: str,
    planet_lon: float,
    sun_lon: float,
) -> PlanetarySolarPhaseTruth:
    """Return typed oriental/occidental truth without forcing boundary cases."""

    if not math.isfinite(planet_lon) or not math.isfinite(sun_lon):
        raise ValueError("planet_lon and sun_lon must be finite")

    forward_to_sun = (sun_lon - planet_lon) % 360.0
    if planet not in _PLANETARY_SOLAR_PHASE_BODIES:
        return PlanetarySolarPhaseTruth(
            status=TruthEvaluationStatus.NOT_EVALUABLE,
            phase=None,
            forward_distance_to_sun_deg=forward_to_sun,
            reason="planetary_solar_phase_not_admitted_for_body",
        )
    if math.isclose(
        forward_to_sun,
        0.0,
        rel_tol=0.0,
        abs_tol=_PLANETARY_SOLAR_PHASE_BOUNDARY_TOLERANCE_DEG,
    ):
        return PlanetarySolarPhaseTruth(
            status=TruthEvaluationStatus.NOT_EVALUABLE,
            phase=None,
            forward_distance_to_sun_deg=forward_to_sun,
            reason="planet_conjunct_sun",
        )
    if math.isclose(
        forward_to_sun,
        180.0,
        rel_tol=0.0,
        abs_tol=_PLANETARY_SOLAR_PHASE_BOUNDARY_TOLERANCE_DEG,
    ):
        return PlanetarySolarPhaseTruth(
            status=TruthEvaluationStatus.NOT_EVALUABLE,
            phase=None,
            forward_distance_to_sun_deg=forward_to_sun,
            reason="planet_opposite_sun",
        )

    phase = (
        PlanetarySolarPhaseKind.ORIENTAL
        if forward_to_sun < 180.0
        else PlanetarySolarPhaseKind.OCCIDENTAL
    )
    return PlanetarySolarPhaseTruth(
        status=TruthEvaluationStatus.EVALUATED,
        phase=phase,
        forward_distance_to_sun_deg=forward_to_sun,
    )


def oriental_occidental(
    planet: str,
    planet_lon: float,
    sun_lon: float,
) -> str | None:
    """
    Classify a planet as oriental or occidental relative to the Sun.

    Classical longitude-phase definition: a planet is **oriental** when it
    precedes and rises before the Sun, and **occidental** when it follows and
    sets after the Sun. Superior and inferior planets use the same geometric
    classification; their favourable scoring polarity differs.
      - Luminaries (Sun, Moon) have no oriental/occidental classification;
        returns None.

    The geometric test: if the forward distance from the planet to the Sun
    (going in the zodiacal direction) is less than 180 degrees, the planet is
    west of / preceding the Sun and therefore oriental. Otherwise it is east
    of / following the Sun and therefore occidental.

    Parameters
    ----------
    planet     : planet name
    planet_lon : ecliptic longitude of the planet (degrees)
    sun_lon    : ecliptic longitude of the Sun (degrees)

    Returns
    -------
    ``"oriental"``, ``"occidental"``, or ``None`` when the classification is
    not applicable or lies exactly on the conjunction/opposition boundary.
    """
    truth = planetary_solar_phase_truth(planet, planet_lon, sun_lon)
    return None if truth.phase is None else truth.phase.value


_BESIEGING_GEOMETRY_TOLERANCE_DEG = 1e-12


def besieging_truth(
    planet_lon: float,
    chart_positions: dict[str, float],
    planet_name: str | None = None,
    orb: float = 12.0,
) -> BesiegingTruth:
    """Return typed nearest-neighbor malefic enclosure truth."""

    if not math.isfinite(planet_lon):
        raise ValueError("planet_lon must be finite")
    if not math.isfinite(orb) or not (0.0 < orb <= 180.0):
        raise ValueError("orb must be finite and in (0, 180]")
    if not isinstance(chart_positions, dict):
        raise TypeError("chart_positions must be a dict of body longitudes")

    target = planet_lon % 360.0

    def circular_distance(left: float, right: float) -> float:
        separation = abs((left % 360.0) - (right % 360.0))
        return min(separation, 360.0 - separation)

    relevant_names = tuple(
        dict.fromkeys(
            (
                *_PLANET_ORDER,
                *(() if not planet_name else (planet_name,)),
            )
        )
    )
    for name in relevant_names:
        if name not in chart_positions:
            continue
        longitude = chart_positions[name]
        if not math.isfinite(longitude):
            raise ValueError(
                f"chart_positions[{name!r}] must be finite"
            )

    resolved_target = planet_name if planet_name else None
    target_reason: str | None = None
    target_candidates: tuple[str, ...] = ()
    if resolved_target is None:
        target_candidates = tuple(
            name
            for name in _PLANET_ORDER
            if (
                name in chart_positions
                and circular_distance(chart_positions[name], target)
                <= _BESIEGING_GEOMETRY_TOLERANCE_DEG
            )
        )
        if len(target_candidates) == 1:
            resolved_target = target_candidates[0]
        elif target_candidates:
            target_reason = "target_identity_ambiguous"
        else:
            target_reason = "target_identity_not_supplied"

    required_bodies = tuple(
        dict.fromkeys(
            (
                *_PLANET_ORDER,
                *(() if resolved_target is None else (resolved_target,)),
            )
        )
    )
    supplied_bodies = tuple(
        name for name in required_bodies if name in chart_positions
    )
    missing_bodies = tuple(
        name for name in required_bodies if name not in supplied_bodies
    )

    if target_reason is not None:
        dependency_truth = BesiegingDependencyCompletenessTruth(
            status=TruthEvaluationStatus.NOT_EVALUABLE,
            required_bodies=required_bodies,
            supplied_bodies=supplied_bodies,
            missing_bodies=missing_bodies,
            reason=target_reason,
        )
        return BesiegingTruth(
            status=TruthEvaluationStatus.NOT_EVALUABLE,
            dependency_truth=dependency_truth,
            target_planet=None,
            target_longitude=target,
            orb_deg=orb,
            besieged=None,
            ambiguous_bodies=target_candidates,
            reason=target_reason,
        )

    if missing_bodies:
        dependency_truth = BesiegingDependencyCompletenessTruth(
            status=TruthEvaluationStatus.NOT_EVALUABLE,
            required_bodies=required_bodies,
            supplied_bodies=supplied_bodies,
            missing_bodies=missing_bodies,
            reason="missing_required_chart_bodies",
        )
        return BesiegingTruth(
            status=TruthEvaluationStatus.NOT_EVALUABLE,
            dependency_truth=dependency_truth,
            target_planet=resolved_target,
            target_longitude=target,
            orb_deg=orb,
            besieged=None,
            reason="missing_required_chart_bodies",
        )

    dependency_truth = BesiegingDependencyCompletenessTruth(
        status=TruthEvaluationStatus.EVALUATED,
        required_bodies=required_bodies,
        supplied_bodies=supplied_bodies,
        missing_bodies=(),
    )
    if circular_distance(chart_positions[resolved_target], target) > (
        _BESIEGING_GEOMETRY_TOLERANCE_DEG
    ):
        raise ValueError(
            "planet_lon must match chart_positions[planet_name]"
        )

    candidates = tuple(
        (name, chart_positions[name] % 360.0)
        for name in _PLANET_ORDER
        if name != resolved_target
    )
    conjunct_bodies = tuple(
        name
        for name, longitude in candidates
        if circular_distance(longitude, target)
        <= _BESIEGING_GEOMETRY_TOLERANCE_DEG
    )
    if conjunct_bodies:
        return BesiegingTruth(
            status=TruthEvaluationStatus.NOT_EVALUABLE,
            dependency_truth=dependency_truth,
            target_planet=resolved_target,
            target_longitude=target,
            orb_deg=orb,
            besieged=None,
            ambiguous_bodies=conjunct_bodies,
            reason="one_or_more_bodies_conjunct_target",
        )

    directional = tuple(
        (
            name,
            (longitude - target) % 360.0,
            (target - longitude) % 360.0,
        )
        for name, longitude in candidates
    )
    minimum_forward = min(item[1] for item in directional)
    minimum_backward = min(item[2] for item in directional)
    forward_ties = tuple(
        name
        for name, distance, _ in directional
        if math.isclose(
            distance,
            minimum_forward,
            rel_tol=0.0,
            abs_tol=_BESIEGING_GEOMETRY_TOLERANCE_DEG,
        )
    )
    backward_ties = tuple(
        name
        for name, _, distance in directional
        if math.isclose(
            distance,
            minimum_backward,
            rel_tol=0.0,
            abs_tol=_BESIEGING_GEOMETRY_TOLERANCE_DEG,
        )
    )
    if len(forward_ties) != 1 or len(backward_ties) != 1:
        ambiguous_candidates = {
            *(() if len(forward_ties) == 1 else forward_ties),
            *(() if len(backward_ties) == 1 else backward_ties),
        }
        tied_bodies = tuple(
            name
            for name in _PLANET_ORDER
            if name in ambiguous_candidates
        )
        return BesiegingTruth(
            status=TruthEvaluationStatus.NOT_EVALUABLE,
            dependency_truth=dependency_truth,
            target_planet=resolved_target,
            target_longitude=target,
            orb_deg=orb,
            besieged=None,
            ambiguous_bodies=tied_bodies,
            reason="nearest_neighbor_tie",
        )

    forward_name = forward_ties[0]
    backward_name = backward_ties[0]
    if forward_name == backward_name:
        return BesiegingTruth(
            status=TruthEvaluationStatus.NOT_EVALUABLE,
            dependency_truth=dependency_truth,
            target_planet=resolved_target,
            target_longitude=target,
            orb_deg=orb,
            besieged=None,
            ambiguous_bodies=(forward_name,),
            reason="nearest_neighbor_side_boundary",
        )

    malefics = {"Mars", "Saturn"}
    besieged = (
        {backward_name, forward_name} == malefics
        and minimum_backward <= orb
        and minimum_forward <= orb
    )
    return BesiegingTruth(
        status=TruthEvaluationStatus.EVALUATED,
        dependency_truth=dependency_truth,
        target_planet=resolved_target,
        target_longitude=target,
        orb_deg=orb,
        besieged=besieged,
        backward_neighbor=backward_name,
        forward_neighbor=forward_name,
        backward_distance_deg=minimum_backward,
        forward_distance_deg=minimum_forward,
    )


def is_besieged(
    planet_lon: float,
    chart_positions: dict[str, float],
    planet_name: str | None = None,
    orb: float = 12.0,
) -> tuple[str, str] | None:
    """
    Compatibility projection of typed nearest-neighbor besieging truth.

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
    Tuple of (backward_malefic, forward_malefic) names when evaluated and
    besieged, otherwise None. Use :func:`besieging_truth` to distinguish an
    evaluated absence from missing dependencies or ambiguous geometry.
    """
    return besieging_truth(
        planet_lon,
        chart_positions,
        planet_name=planet_name,
        orb=orb,
    ).pair


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
        reception / condition network under explicit policy. Without this
        Engine, the dignity tables would be inert
        data with no path to a scored result.

    LAW OF OPERATION:
        Responsibilities:
            - Accept planet_positions and house_positions as plain dicts.
            - Resolve sign, house, essential dignity, and all accidental
              conditions for every planet admitted by the selected doctrine.
            - Preserve enough structured doctrinal/computational truth that
              later layers do not need to reconstruct hidden logic from the
              flattened labels.
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
            - An explicit Sun position is required for sect and solar truth.
            - Other missing planets are skipped without fabricating phase truth.
            - Malformed or incomplete house input raises instead of defaulting.

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
        "failures": {"policy": "raise"},
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
        *,
        horizon_frame: DignityHorizonFrame | None = None,
        node_positions: dict[str, float] | None = None,
        fixed_star_positions: dict[str, float] | None = None,
    ) -> list[PlanetaryDignity]:
        """
        Calculate dignities for all planets admitted by the active doctrine.

        Parameters
        ----------
        planet_positions : list of dicts with keys:
            - name: str
            - degree: float (tropical ecliptic longitude 0–360)
            - is_retrograde: bool (optional; unknown when omitted)
            - speed: float in degrees/day (optional)
        house_positions : list of dicts with keys:
            - number: int (1–12)
            - degree: float (cusp longitude)
        horizon_frame : optional exact Ascendant/Midheaven frame
            When supplied, chart sect and per-body horizon truth are derived
            from the actual angles and are independent of the selected house
            system. The legacy house-number fallback remains available only
            for callers that have not yet migrated.

        Returns
        -------
        List of PlanetaryDignity, sorted in traditional planet order.

        Semantics note
        --------------
        The result preserves every evaluated testimony. Whether a matched
        testimony contributes points is controlled independently by policy.
        """
        policy = DignityComputationPolicy() if policy is None else policy
        self._validate_policy(policy)

        normalized_planets = self._normalize_planet_positions(planet_positions)
        house_cusps = self._build_house_cusps(house_positions)

        planet_lons:  dict[str, float] = {}
        planet_signs: dict[str, str]   = {}
        planet_retro: dict[str, bool | None] = {}
        planet_speeds: dict[str, float | None] = {}

        for pos in normalized_planets:
            name = pos["name"]
            degree = pos["degree"]
            retro = pos["is_retrograde"]
            planet_lons[name] = degree
            planet_signs[name] = SIGNS[int(degree // 30) % 12]
            planet_retro[name] = retro
            planet_speeds[name] = pos["speed"]

        normalized_nodes = self._normalize_named_longitudes(
            node_positions,
            field_name="node_positions",
        )
        normalized_stars = self._normalize_named_longitudes(
            fixed_star_positions,
            field_name="fixed_star_positions",
        )

        if "Sun" not in planet_lons:
            raise ValueError(
                "calculate_dignities requires an explicit Sun position to determine "
                "sect and solar conditions."
            )
        sun_lon = planet_lons["Sun"]
        all_receptions_by_planet = self._find_receptions(
            planet_signs,
            bases=(ReceptionBasis.DOMICILE, ReceptionBasis.EXALTATION),
            policy=policy,
        )
        receptions_by_planet = self._find_receptions(
            planet_signs,
            bases=self._policy_reception_bases(policy),
            policy=policy,
        )

        if horizon_frame is not None:
            sun_horizon_truth = self._build_horizon_truth(sun_lon, horizon_frame)
            if sun_horizon_truth.status is TruthEvaluationStatus.NOT_EVALUABLE:
                raise ValueError(
                    "Chart sect is not evaluable because the Sun is on the "
                    "Ascendant/Descendant horizon boundary."
                )
            is_day_chart = sun_horizon_truth.hemisphere is HorizonHemisphere.ABOVE
        else:
            # Compatibility path for raw callers that only supply numbered
            # cusps. Facade and REST chart calls provide an exact horizon frame.
            sun_house = self._get_house(sun_lon, house_cusps) if house_cusps else 1
            is_day_chart = sun_house >= 7

        mercury_lon = planet_lons.get("Mercury")
        mercury_phase_truth = (
            self._build_mercury_phase_truth(
                mercury_lon=mercury_lon,
                sun_lon=sun_lon,
                policy=policy,
            )
            if mercury_lon is not None
            else None
        )
        mercury_rises_before_sun = (
            None if mercury_phase_truth is None else mercury_phase_truth.rises_before_sun
        )

        results: list[PlanetaryDignity] = []

        for planet in self._dignity_planet_order(policy):
            if planet not in planet_lons:
                continue

            degree = planet_lons[planet]
            sign   = planet_signs[planet]
            retro  = planet_retro.get(planet)
            speed = planet_speeds.get(planet)
            house  = self._get_house(degree, house_cusps)
            horizon_truth = (
                self._build_horizon_truth(degree, horizon_frame)
                if horizon_frame is not None
                else None
            )

            mutual_reception_truth = self._build_mutual_reception_truths(
                receptions_by_planet.get(planet, []),
                policy,
            )
            essential_truth = self._get_essential_dignity_truth(
                planet,
                sign,
                policy,
                is_day_chart,
                longitude=degree,
                receptions=mutual_reception_truth,
            )

            acc_list, acc_score, accidental_truth, sect_truth = self._get_accidental_dignities(
                planet=planet,
                house=house,
                is_retrograde=retro,
                planet_speed=speed,
                planet_lon=degree,
                sun_lon=sun_lon,
                mutual_receptions=mutual_reception_truth,
                sign=sign,
                is_day_chart=is_day_chart,
                mercury_rises_before_sun=mercury_rises_before_sun,
                mercury_phase_truth=mercury_phase_truth,
                horizon_truth=horizon_truth,
                policy=policy,
                chart_positions=planet_lons,
                node_positions=normalized_nodes,
                fixed_star_positions=normalized_stars,
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
                mutual_reception_truth=list(mutual_reception_truth),
                essential_classification=self._classify_essential_truth(essential_truth),
                accidental_classification=self._classify_accidental_truth(accidental_truth),
                sect_classification=self._classify_sect_truth(sect_truth),
                solar_classification=self._classify_solar_truth(accidental_truth.solar_condition),
                reception_classification=self._classify_reception_truths(mutual_reception_truth),
                condition_profile=self._build_condition_profile(
                    planet=planet,
                    essential_truth=essential_truth,
                    accidental_truth=accidental_truth,
                    sect_truth=sect_truth,
                    solar_truth=accidental_truth.solar_condition,
                    all_receptions=list(all_receptions_by_planet.get(planet, [])),
                    admitted_receptions=list(receptions_by_planet.get(planet, [])),
                    mutual_reception_truth=list(mutual_reception_truth),
                ),
            ))

        dignity_order = self._dignity_planet_order(policy)
        results.sort(key=lambda d: dignity_order.index(d.planet)
                     if d.planet in dignity_order else 99)
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
            if name in self._dignity_planet_order(policy):
                planet_signs[name] = SIGNS[int(degree // 30) % 12]

        receptions = self._find_receptions(
            planet_signs,
            bases=self._policy_reception_bases(policy),
            policy=policy,
        )
        ordered: list[PlanetaryReception] = []
        for planet in self._dignity_planet_order(policy):
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
        *,
        horizon_frame: DignityHorizonFrame | None = None,
        node_positions: dict[str, float] | None = None,
        fixed_star_positions: dict[str, float] | None = None,
    ) -> list[PlanetaryConditionProfile]:
        """Calculate integrated per-planet condition profiles."""

        dignities = self.calculate_dignities(
            planet_positions,
            house_positions,
            policy=policy,
            horizon_frame=horizon_frame,
            node_positions=node_positions,
            fixed_star_positions=fixed_star_positions,
        )
        return [dignity.condition_profile for dignity in dignities if dignity.condition_profile is not None]

    def calculate_chart_condition_profile(
        self,
        planet_positions: list[dict],
        house_positions: list[dict],
        policy: DignityComputationPolicy | None = None,
        *,
        horizon_frame: DignityHorizonFrame | None = None,
        node_positions: dict[str, float] | None = None,
        fixed_star_positions: dict[str, float] | None = None,
    ) -> ChartConditionProfile:
        """Calculate the chart-wide condition profile derived from planet profiles."""

        profiles = self.calculate_condition_profiles(
            planet_positions,
            house_positions,
            policy=policy,
            horizon_frame=horizon_frame,
            node_positions=node_positions,
            fixed_star_positions=fixed_star_positions,
        )
        return self._build_chart_condition_profile(profiles)

    def calculate_condition_network_profile(
        self,
        planet_positions: list[dict],
        house_positions: list[dict],
        policy: DignityComputationPolicy | None = None,
        *,
        horizon_frame: DignityHorizonFrame | None = None,
        node_positions: dict[str, float] | None = None,
        fixed_star_positions: dict[str, float] | None = None,
    ) -> ConditionNetworkProfile:
        """Calculate the reception / condition network profile."""

        chart_profile = self.calculate_chart_condition_profile(
            planet_positions,
            house_positions,
            policy=policy,
            horizon_frame=horizon_frame,
            node_positions=node_positions,
            fixed_star_positions=fixed_star_positions,
        )
        return self._build_condition_network_profile(chart_profile)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _dignity_planet_order(policy: DignityComputationPolicy) -> list[str]:
        if policy.essential.doctrine is EssentialDignityDoctrine.MODERN_CO_RULERS:
            return list(_MODERN_PLANET_ORDER)
        return list(_PLANET_ORDER)

    @staticmethod
    def _domicile_table(policy: DignityComputationPolicy) -> dict[str, list[str]]:
        if policy.essential.doctrine is EssentialDignityDoctrine.MODERN_CO_RULERS:
            return MODERN_DOMICILE
        return DOMICILE

    @staticmethod
    def _detriment_table(policy: DignityComputationPolicy) -> dict[str, list[str]]:
        if policy.essential.doctrine is EssentialDignityDoctrine.MODERN_CO_RULERS:
            return MODERN_DETRIMENT
        return DETRIMENT

    @staticmethod
    def _get_essential_dignity_truth(
        planet: str,
        sign: str,
        policy: DignityComputationPolicy,
        is_day_chart: bool = True,
        *,
        longitude: float | None = None,
        receptions: list[MutualReceptionTruth] | None = None,
    ) -> EssentialDignityTruth:
        DignitiesService._validate_policy(policy)
        domicile = DignitiesService._domicile_table(policy)
        detriment = DignitiesService._detriment_table(policy)
        assignment = triplicity_assignment_for(
            sign,
            is_day_chart=is_day_chart,
            doctrine=policy.essential.triplicity_doctrine,
        )
        triplicity_weight = triplicity_score(
            planet,
            sign,
            is_day_chart=is_day_chart,
            doctrine=policy.essential.triplicity_doctrine,
            participating_policy=policy.essential.participating_ruler_policy,
            primary_score=SCORE_TRIPLICITY,
            participating_score=SCORE_FACE,
        )
        domicile_signs = tuple(domicile.get(planet, ()))
        exaltation_signs = tuple(EXALTATION.get(planet, ()))
        detriment_signs = tuple(detriment.get(planet, ()))
        fall_signs = tuple(FALL.get(planet, ()))

        should_score = policy.scoring.mode is not DignityScoringMode.UNSCORED

        def component(
            kind: EssentialDignityKind,
            matched: bool,
            weight: int,
            *,
            matching_signs: tuple[str, ...] = (),
            ruler: str | None = None,
        ) -> EssentialDignityComponentTruth:
            return EssentialDignityComponentTruth(
                kind=kind,
                status=TruthEvaluationStatus.EVALUATED,
                matched=matched,
                matching_signs=matching_signs,
                ruler=ruler,
                weight=weight,
                score=weight if matched and should_score else 0,
            )

        components: list[EssentialDignityComponentTruth] = [
            component(
                EssentialDignityKind.DOMICILE,
                sign in domicile_signs,
                SCORE_DOMICILE,
                matching_signs=domicile_signs,
            ),
            component(
                EssentialDignityKind.EXALTATION,
                sign in exaltation_signs,
                SCORE_EXALTATION,
                matching_signs=exaltation_signs,
            ),
            component(
                EssentialDignityKind.TRIPLICITY,
                triplicity_weight != 0,
                triplicity_weight or SCORE_TRIPLICITY,
                matching_signs=assignment.signs,
                ruler=(
                    assignment.participating_ruler
                    if planet == assignment.participating_ruler and triplicity_weight
                    else assignment.active_ruler
                ),
            ),
        ]

        if longitude is None:
            components.extend(
                [
                    EssentialDignityComponentTruth(
                        kind=EssentialDignityKind.BOUND,
                        status=TruthEvaluationStatus.NOT_EVALUABLE,
                        matched=None,
                        weight=SCORE_BOUND,
                        reason="longitude_required_for_bound",
                    ),
                    EssentialDignityComponentTruth(
                        kind=EssentialDignityKind.FACE,
                        status=TruthEvaluationStatus.NOT_EVALUABLE,
                        matched=None,
                        weight=SCORE_FACE,
                        reason="longitude_required_for_face",
                    ),
                ]
            )
        else:
            bound_host = bound_ruler(
                longitude,
                policy=EgyptianBoundsPolicy(policy.essential.bounds_doctrine),
            )
            face_host = chaldean_face(longitude).ruling_planet
            components.extend(
                [
                    component(
                        EssentialDignityKind.BOUND,
                        planet == bound_host,
                        SCORE_BOUND,
                        ruler=bound_host,
                    ),
                    component(
                        EssentialDignityKind.FACE,
                        planet == face_host,
                        SCORE_FACE,
                        ruler=face_host,
                    ),
                ]
            )

        components.extend(
            [
                component(
                    EssentialDignityKind.DETRIMENT,
                    sign in detriment_signs,
                    SCORE_DETRIMENT,
                    matching_signs=detriment_signs,
                ),
                component(
                    EssentialDignityKind.FALL,
                    sign in fall_signs,
                    SCORE_FALL,
                    matching_signs=fall_signs,
                ),
            ]
        )

        positive_kinds = {
            EssentialDignityKind.DOMICILE,
            EssentialDignityKind.EXALTATION,
            EssentialDignityKind.TRIPLICITY,
            EssentialDignityKind.BOUND,
            EssentialDignityKind.FACE,
        }
        positive_components = [
            component for component in components if component.kind in positive_kinds
        ]
        if any(component.matched is True for component in positive_components):
            peregrine = EssentialDignityComponentTruth(
                kind=EssentialDignityKind.PEREGRINE,
                status=TruthEvaluationStatus.EVALUATED,
                matched=False,
                weight=SCORE_PEREGRINE,
            )
        elif any(
            component.status is TruthEvaluationStatus.NOT_EVALUABLE
            for component in positive_components
        ):
            peregrine = EssentialDignityComponentTruth(
                kind=EssentialDignityKind.PEREGRINE,
                status=TruthEvaluationStatus.NOT_EVALUABLE,
                matched=None,
                weight=SCORE_PEREGRINE,
                reason="one_or_more_positive_dignity_components_not_evaluable",
            )
        else:
            peregrine = component(
                EssentialDignityKind.PEREGRINE,
                True,
                SCORE_PEREGRINE,
            )
        components.append(peregrine)

        label_by_kind = {
            EssentialDignityKind.DOMICILE: "Domicile",
            EssentialDignityKind.EXALTATION: "Exaltation",
            EssentialDignityKind.TRIPLICITY: "Triplicity",
            EssentialDignityKind.BOUND: "Bound",
            EssentialDignityKind.FACE: "Face",
            EssentialDignityKind.DETRIMENT: "Detriment",
            EssentialDignityKind.FALL: "Fall",
            EssentialDignityKind.PEREGRINE: "Peregrine",
        }
        matched_components = [item for item in components if item.matched is True]
        primary = matched_components[0] if matched_components else peregrine
        scored_receptions = tuple(receptions or ())
        return EssentialDignityTruth(
            category="essential",
            label=label_by_kind[primary.kind],
            score=(
                sum(item.score for item in components)
                + sum(reception.score for reception in scored_receptions)
            ),
            sign=sign,
            matching_signs=primary.matching_signs,
            matched=bool(matched_components or scored_receptions),
            components=tuple(components),
            receptions=scored_receptions,
            scoring_mode=policy.scoring.mode,
            bounds_doctrine=policy.essential.bounds_doctrine,
            triplicity_doctrine=policy.essential.triplicity_doctrine,
        )

    @staticmethod
    def _get_essential_dignity(planet: str, sign: str) -> tuple[str, int]:
        truth = DignitiesService._get_essential_dignity_truth(planet, sign, DignityComputationPolicy())
        return truth.label, truth.score

    @staticmethod
    def _get_accidental_dignities(
        planet: str,
        house: int,
        is_retrograde: bool | None,
        planet_speed: float | None,
        planet_lon: float,
        sun_lon: float,
        mutual_receptions: list[MutualReceptionTruth],
        sign: str = "",
        is_day_chart: bool = True,
        mercury_rises_before_sun: bool | None = None,
        mercury_phase_truth: MercuryPhaseTruth | None = None,
        horizon_truth: HorizonTruth | None = None,
        policy: DignityComputationPolicy | None = None,
        chart_positions: dict[str, float] | None = None,
        node_positions: dict[str, float] | None = None,
        fixed_star_positions: dict[str, float] | None = None,
    ) -> tuple[list[str], int, AccidentalDignityTruth, SectTruth]:
        policy = DignityComputationPolicy() if policy is None else policy
        dignities: list[str] = []
        score = 0
        conditions: list[AccidentalDignityCondition] = []
        evaluations: list[AccidentalDignityEvaluationTruth] = []
        full_scoring = policy.scoring.mode is DignityScoringMode.WILLIAM_LILLY_1647

        def make_condition(
            category: str,
            code: str,
            label: str,
            weight: int,
            *,
            source: str = "william_lilly_1647",
            scored: bool | None = None,
        ) -> AccidentalDignityCondition:
            applies = full_scoring if scored is None else scored
            return AccidentalDignityCondition(
                category=category,
                code=code,
                label=label,
                score=weight if applies else 0,
                weight=weight,
                scored=applies,
                source=source,
            )

        def add_condition(condition: AccidentalDignityCondition) -> None:
            nonlocal score
            dignities.append(condition.label)
            conditions.append(condition)
            score += condition.score
            evaluations.append(
                AccidentalDignityEvaluationTruth(
                    category=condition.category,
                    code=condition.code,
                    label=condition.label,
                    status=TruthEvaluationStatus.EVALUATED,
                    matched=True,
                    weight=condition.weight or 0,
                    score=condition.score,
                    source=condition.source,
                )
            )

        def unavailable(
            category: str,
            code: str,
            label: str,
            weight: int,
            reason: str,
            *,
            source: str = "william_lilly_1647",
        ) -> None:
            evaluations.append(
                AccidentalDignityEvaluationTruth(
                    category=category,
                    code=code,
                    label=label,
                    status=TruthEvaluationStatus.NOT_EVALUABLE,
                    matched=None,
                    weight=weight,
                    score=0,
                    source=source,
                    reason=reason,
                )
            )

        def absent(
            category: str,
            code: str,
            label: str,
            weight: int,
            *,
            source: str = "william_lilly_1647",
        ) -> None:
            evaluations.append(
                AccidentalDignityEvaluationTruth(
                    category=category,
                    code=code,
                    label=label,
                    status=TruthEvaluationStatus.EVALUATED,
                    matched=False,
                    weight=weight,
                    score=0,
                    source=source,
                )
            )

        house_condition: AccidentalDignityCondition | None = None
        if policy.accidental.include_house_strength:
            house_code = (
                "angular" if house in ANGULAR_HOUSES
                else "succedent" if house in SUCCEDENT_HOUSES
                else "cadent"
            )
            house_condition = make_condition(
                "house",
                house_code,
                f"{house_code.title()} (H{house})",
                SCORE_HOUSE[house],
            )

        if house_condition is not None:
            add_condition(house_condition)

        motion_condition: AccidentalDignityCondition | None = None
        if policy.accidental.include_motion:
            if planet in {"Sun", "Moon"}:
                unavailable("motion", "direct_retrograde", "Direct / Retrograde", 0, "not_applicable_to_luminary")
            elif planet_speed is not None and math.isclose(
                planet_speed,
                0.0,
                rel_tol=0.0,
                abs_tol=1e-12,
            ):
                motion_condition = make_condition(
                    "motion",
                    "stationary",
                    "Stationary",
                    0,
                    scored=False,
                )
            elif is_retrograde is None:
                unavailable("motion", "direct_retrograde", "Direct / Retrograde", 0, "retrograde_state_not_supplied")
            elif is_retrograde:
                motion_condition = make_condition("motion", "retrograde", "Retrograde", SCORE_RETROGRADE)
            else:
                motion_condition = make_condition("motion", "direct", "Direct", SCORE_DIRECT)

            if motion_condition is not None:
                add_condition(motion_condition)

        if policy.accidental.include_speed:
            if planet_speed is None:
                unavailable("speed", "swift_slow", "Swift / Slow", 0, "daily_motion_not_supplied")
            elif planet not in LILLY_MEAN_DAILY_MOTION:
                unavailable("speed", "swift_slow", "Swift / Slow", 0, "no_admitted_lilly_mean_motion")
            else:
                mean_motion = LILLY_MEAN_DAILY_MOTION[planet]
                actual_motion = abs(planet_speed)
                if math.isclose(actual_motion, mean_motion, abs_tol=1e-12):
                    evaluations.append(
                        AccidentalDignityEvaluationTruth(
                            category="speed", code="mean_motion", label="At Mean Motion",
                            status=TruthEvaluationStatus.EVALUATED, matched=False,
                            weight=0, score=0, source="william_lilly_1647",
                        )
                    )
                elif actual_motion > mean_motion:
                    add_condition(make_condition("speed", "swift", "Swift in Motion", SCORE_SWIFT))
                else:
                    add_condition(make_condition("speed", "slow", "Slow in Motion", SCORE_SLOW))

        proximity_truth = solar_proximity_truth(
            planet,
            planet_lon,
            sun_lon,
        )
        solar_truth = SolarConditionTruth(False)
        solar_policy = policy.accidental.solar
        solar_applicable = (
            proximity_truth.status is TruthEvaluationStatus.EVALUATED
            and (planet != "Moon" or solar_policy.include_for_moon)
        )
        if solar_applicable:
            dist = proximity_truth.distance_from_sun_deg
            if dist is None:
                raise ValueError(
                    "evaluated solar proximity truth requires a distance"
                )
            if proximity_truth.band is SolarProximityBand.CAZIMI and solar_policy.include_cazimi:
                solar_truth = SolarConditionTruth(True, "cazimi", "Cazimi", SCORE_CAZIMI, dist)
            elif proximity_truth.band is SolarProximityBand.COMBUST and solar_policy.include_combust:
                solar_truth = SolarConditionTruth(True, "combust", "Combust", SCORE_COMBUST, dist)
            elif proximity_truth.band is SolarProximityBand.UNDER_SUNBEAMS and solar_policy.include_under_sunbeams:
                solar_truth = SolarConditionTruth(True, "under_sunbeams", "Under Sunbeams", SCORE_SUNBEAMS, dist)
            elif proximity_truth.band is SolarProximityBand.CLEAR and solar_policy.include_free_from_beams:
                solar_truth = SolarConditionTruth(
                    True, "free_from_beams", "Free from Combustion and Beams",
                    SCORE_FREE_FROM_BEAMS if full_scoring else 0, dist,
                    SCORE_FREE_FROM_BEAMS, full_scoring,
                )
            else:
                solar_truth = SolarConditionTruth(False, None, None, 0, dist)

            if solar_truth.present and solar_truth.condition != "free_from_beams":
                solar_truth.weight = solar_truth.score
                solar_truth.scored = full_scoring
                if not full_scoring:
                    solar_truth.score = 0

        if solar_truth.present and solar_truth.label is not None:
            solar_condition = make_condition(
                "solar",
                solar_truth.condition or "solar_condition",
                solar_truth.label,
                solar_truth.weight,
            )
            add_condition(solar_condition)

        sect_truth = DignitiesService._build_sect_truth(
            planet=planet,
            sign=sign,
            house=house,
            planet_lon=planet_lon,
            is_day_chart=is_day_chart,
            mercury_rises_before_sun=mercury_rises_before_sun,
            mercury_phase_truth=mercury_phase_truth,
            horizon_truth=horizon_truth,
            doctrine=policy.accidental.sect.doctrine,
        )

        hayz_condition: AccidentalDignityCondition | None = None
        if policy.accidental.sect.include_hayz and sign and sect_truth.in_hayz:
            hayz_condition = make_condition(
                "sect", "hayz", "In Hayz", 0,
                source="al_biruni_1030_section_496", scored=False,
            )
            add_condition(hayz_condition)
        elif policy.accidental.sect.include_hayz and sect_truth.in_hayz is False:
            absent("sect", "hayz", "In Hayz", 0, source="al_biruni_1030_section_496")

        halb_condition: AccidentalDignityCondition | None = None
        if (
            policy.accidental.sect.include_halb
            and hayz_condition is None
            and sect_truth.in_halb
        ):
            halb_condition = make_condition(
                "sect", "halb", "In Halb", SCORE_HALB,
                source="al_biruni_1030_section_496", scored=False,
            )
            add_condition(halb_condition)
        elif policy.accidental.sect.include_halb and sect_truth.in_halb is False:
            absent("sect", "halb", "In Halb", 0, source="al_biruni_1030_section_496")

        joy_condition: AccidentalDignityCondition | None = None
        if policy.accidental.include_joy and is_in_joy(planet, house):
            joy_condition = make_condition(
                "joy", "joy", f"In Joy (H{house})", SCORE_JOY,
                source="planetary_joys", scored=False,
            )
            add_condition(joy_condition)
        elif policy.accidental.include_joy:
            absent("joy", "joy", f"In Joy (H{house})", 0, source="planetary_joys")

        if policy.accidental.include_lunar_phase and planet == "Moon":
            elongation = (planet_lon - sun_lon) % 360.0
            if math.isclose(elongation, 0.0, abs_tol=1e-12) or math.isclose(elongation, 180.0, abs_tol=1e-12):
                unavailable("lunar_phase", "waxing_waning", "Waxing / Waning Moon", 0, "phase_boundary")
            elif elongation < 180.0:
                add_condition(make_condition("lunar_phase", "waxing", "Moon Waxing", SCORE_MOON_WAXING))
            else:
                add_condition(make_condition("lunar_phase", "waning", "Moon Waning", SCORE_MOON_WANING))

        # -- Oriental / Occidental --
        # For superior planets (Mars/Jupiter/Saturn): oriental is beneficial (+2),
        # occidental is debilitating (-2).  For inferior planets (Mercury/Venus):
        # the reverse — occidental is beneficial, oriental is debilitating.
        oriental_condition: AccidentalDignityCondition | None = None
        planetary_phase_truth = planetary_solar_phase_truth(
            planet,
            planet_lon,
            sun_lon,
        )
        phase = (
            planetary_phase_truth.phase
            if (
                policy.accidental.include_oriental_occidental
                and planetary_phase_truth.status is TruthEvaluationStatus.EVALUATED
            )
            else None
        )
        if phase is not None:
            is_superior = planet in _SUPERIOR_PLANETS
            if phase is PlanetarySolarPhaseKind.ORIENTAL:
                phase_score = SCORE_ORIENTAL if is_superior else SCORE_OCCIDENTAL
                oriental_condition = make_condition(
                    "phase", "oriental", "Oriental", phase_score,
                )
            else:
                phase_score = SCORE_OCCIDENTAL if is_superior else SCORE_ORIENTAL
                oriental_condition = make_condition(
                    "phase", "occidental", "Occidental", phase_score,
                )
            add_condition(oriental_condition)
        elif (
            policy.accidental.include_oriental_occidental
            and planetary_phase_truth.status is TruthEvaluationStatus.NOT_EVALUABLE
        ):
            unavailable(
                "phase", "oriental_occidental", "Oriental / Occidental", 0,
                planetary_phase_truth.reason or "phase_not_evaluable",
            )

        def circular_separation(left: float, right: float) -> float:
            difference = abs((left - right) % 360.0)
            return min(difference, 360.0 - difference)

        def partile_aspect(left: float, right: float, exact_angle: float) -> bool:
            return abs(circular_separation(left, right) - exact_angle) < _PARTILE_ORB_DEG

        if policy.accidental.include_planetary_aspects:
            positions = {} if chart_positions is None else chart_positions
            aspect_rules = (
                ("Jupiter", ((0.0, "conjunction", SCORE_BENEFIC_CONJUNCTION), (120.0, "trine", SCORE_BENEFIC_TRINE), (60.0, "sextile", SCORE_BENEFIC_SEXTILE)), "benefic_aspect"),
                ("Venus", ((0.0, "conjunction", SCORE_BENEFIC_CONJUNCTION), (120.0, "trine", SCORE_BENEFIC_TRINE), (60.0, "sextile", SCORE_BENEFIC_SEXTILE)), "benefic_aspect"),
                ("Saturn", ((0.0, "conjunction", SCORE_MALEFIC_CONJUNCTION), (180.0, "opposition", SCORE_MALEFIC_OPPOSITION), (90.0, "square", SCORE_MALEFIC_SQUARE)), "malefic_aspect"),
                ("Mars", ((0.0, "conjunction", SCORE_MALEFIC_CONJUNCTION), (180.0, "opposition", SCORE_MALEFIC_OPPOSITION), (90.0, "square", SCORE_MALEFIC_SQUARE)), "malefic_aspect"),
            )
            for witness, rules, category in aspect_rules:
                if witness == planet:
                    continue
                witness_lon = positions.get(witness)
                if witness_lon is None:
                    unavailable(category, f"{witness.lower()}_aspect", f"Partile aspect with {witness}", 0, f"{witness.lower()}_position_not_supplied")
                    continue
                for angle, aspect_name, aspect_weight in rules:
                    if partile_aspect(planet_lon, witness_lon, angle):
                        add_condition(make_condition(
                            category,
                            f"{witness.lower()}_{aspect_name}",
                            f"Partile {aspect_name.title()} {witness}",
                            aspect_weight,
                        ))
                    else:
                        absent(
                            category,
                            f"{witness.lower()}_{aspect_name}",
                            f"Partile {aspect_name.title()} {witness}",
                            aspect_weight,
                        )

        if policy.accidental.include_node_contacts:
            nodes = {} if node_positions is None else node_positions
            north_key = "Mean Node" if policy.scoring.node_doctrine is DignityNodeDoctrine.MEAN_NODE else "True Node"
            north_lon = nodes.get(north_key)
            if north_lon is None:
                unavailable("node", "north_node_conjunction", "Conjunct North Node", SCORE_NORTH_NODE_CONJUNCTION, f"{north_key.lower().replace(' ', '_')}_not_supplied")
            else:
                if partile_aspect(planet_lon, north_lon, 0.0):
                    add_condition(make_condition("node", "north_node_conjunction", "Conjunct North Node", SCORE_NORTH_NODE_CONJUNCTION))
                else:
                    absent("node", "north_node_conjunction", "Conjunct North Node", SCORE_NORTH_NODE_CONJUNCTION)
                south_lon = (north_lon + 180.0) % 360.0
                if partile_aspect(planet_lon, south_lon, 0.0):
                    add_condition(make_condition("node", "south_node_conjunction", "Conjunct South Node", SCORE_SOUTH_NODE_CONJUNCTION))
                else:
                    absent("node", "south_node_conjunction", "Conjunct South Node", SCORE_SOUTH_NODE_CONJUNCTION)

        if policy.accidental.include_fixed_star_contacts:
            stars = {} if fixed_star_positions is None else fixed_star_positions
            star_rules = {
                "Regulus": SCORE_REGULUS_CONJUNCTION,
                "Spica": SCORE_SPICA_CONJUNCTION,
                "Algol": SCORE_ALGOL_CONJUNCTION,
            }
            for star, star_weight in star_rules.items():
                star_lon = stars.get(star)
                if star_lon is None:
                    unavailable("fixed_star", f"{star.lower()}_conjunction", f"Conjunct {star}", star_weight, f"{star.lower()}_position_not_supplied")
                elif circular_separation(planet_lon, star_lon) <= _FIXED_STAR_ORBS_DEG[star]:
                    add_condition(make_condition("fixed_star", f"{star.lower()}_conjunction", f"Conjunct {star}", star_weight))
                else:
                    absent("fixed_star", f"{star.lower()}_conjunction", f"Conjunct {star}", star_weight)

        # -- Besieging --
        besieged_condition: AccidentalDignityCondition | None = None
        enclosure_truth = besieging_truth(
            planet_lon,
            {} if chart_positions is None else chart_positions,
            planet_name=planet,
        )
        if (
            policy.accidental.include_besieging
            and
            enclosure_truth.status is TruthEvaluationStatus.EVALUATED
            and enclosure_truth.besieged
        ):
            pair = enclosure_truth.pair
            if pair is None:
                raise ValueError(
                    "evaluated besieging truth requires an enclosing pair"
                )
            left, right = pair
            besieged_condition = make_condition(
                "besieging", "besieged",
                f"Besieged ({left}/{right})", SCORE_BESIEGED,
            )
            add_condition(besieged_condition)
        elif policy.accidental.include_besieging:
            if enclosure_truth.status is TruthEvaluationStatus.EVALUATED:
                absent("besieging", "besieged", "Besieged by Mars and Saturn", SCORE_BESIEGED)
            else:
                unavailable(
                    "besieging", "besieged", "Besieged by Mars and Saturn",
                    SCORE_BESIEGED,
                    enclosure_truth.reason or "besieging_not_evaluable",
                )

        accidental_truth = AccidentalDignityTruth(
            conditions=conditions,
            evaluations=tuple(evaluations),
            house_condition=house_condition,
            motion_condition=motion_condition,
            solar_condition=solar_truth,
            solar_proximity_truth=proximity_truth,
            besieging_truth=enclosure_truth,
            mutual_receptions=list(mutual_receptions),
            hayz_condition=hayz_condition,
            halb_condition=halb_condition,
            joy_condition=joy_condition,
            planetary_solar_phase_truth=planetary_phase_truth,
            oriental_condition=oriental_condition,
            besieged_condition=besieged_condition,
        )

        return dignities, score, accidental_truth, sect_truth

    @staticmethod
    def _build_sect_truth(
        planet: str,
        sign: str,
        house: int,
        planet_lon: float,
        is_day_chart: bool,
        mercury_rises_before_sun: bool | None,
        mercury_phase_truth: MercuryPhaseTruth | None,
        horizon_truth: HorizonTruth | None,
        doctrine: HalbHayzDoctrine,
    ) -> SectTruth:
        if horizon_truth is None:
            actual_hemisphere = "above" if 7 <= house <= 12 else "below"
            horizon_truth = HorizonTruth(
                status=TruthEvaluationStatus.EVALUATED,
                method=HorizonComputationMethod.LEGACY_HOUSE_NUMBER,
                longitude=planet_lon % 360.0,
                hemisphere=HorizonHemisphere(actual_hemisphere),
            )
        else:
            actual_hemisphere = (
                None
                if horizon_truth.hemisphere is None
                else horizon_truth.hemisphere.value
            )
        actual_gender = "masculine" if sign in MASCULINE_SIGNS else "feminine"
        preferred_gender = PREFERRED_GENDER.get(planet)
        planet_sect = SECT.get(planet)
        if planet_sect == "sect_light":
            if mercury_rises_before_sun is None:
                planet_sect = None
                preferred_hemisphere = None
                in_sect = None
                sect_component = SectComponentTruth(
                    kind=SectComponentKind.SECT_MEMBERSHIP,
                    status=TruthEvaluationStatus.NOT_EVALUABLE,
                    matched=None,
                    reason="mercury_phase_not_evaluable",
                )
            else:
                planet_sect = "diurnal" if mercury_rises_before_sun else "nocturnal"
                preferred_hemisphere = halb_required_hemisphere(
                    planet,
                    is_day_chart,
                    mercury_rises_before_sun,
                )
                in_sect = is_in_sect(
                    planet,
                    is_day_chart,
                    mercury_rises_before_sun,
                )
                sect_component = SectComponentTruth(
                    kind=SectComponentKind.SECT_MEMBERSHIP,
                    status=TruthEvaluationStatus.EVALUATED,
                    matched=in_sect,
                )
        else:
            preferred_hemisphere = halb_required_hemisphere(
                planet,
                is_day_chart,
                mercury_rises_before_sun,
            )
            in_sect = is_in_sect(
                planet,
                is_day_chart,
                mercury_rises_before_sun,
            )
            sect_component = SectComponentTruth(
                kind=SectComponentKind.SECT_MEMBERSHIP,
                status=TruthEvaluationStatus.EVALUATED,
                matched=in_sect,
            )

        hemisphere_matches = (
            None
            if preferred_hemisphere is None or actual_hemisphere is None
            else preferred_hemisphere == actual_hemisphere
        )
        gender_matches = (
            preferred_gender == actual_gender
            if preferred_gender in {"masculine", "feminine"}
            else None
        )

        if in_sect is None:
            in_halb = None
            halb_component = SectComponentTruth(
                kind=SectComponentKind.HALB,
                status=TruthEvaluationStatus.NOT_EVALUABLE,
                matched=None,
                reason="sect_membership_not_evaluable",
            )
        elif horizon_truth.status is TruthEvaluationStatus.NOT_EVALUABLE:
            in_halb = None
            halb_component = SectComponentTruth(
                kind=SectComponentKind.HALB,
                status=TruthEvaluationStatus.NOT_EVALUABLE,
                matched=None,
                reason="body_on_horizon",
            )
        else:
            # Halb is the sect-relative hemisphere judgment itself. It does
            # not additionally require the planet to agree with chart sect;
            # the required hemisphere already changes with chart sect.
            in_halb = bool(hemisphere_matches)
            halb_component = SectComponentTruth(
                kind=SectComponentKind.HALB,
                status=TruthEvaluationStatus.EVALUATED,
                matched=in_halb,
            )

        if in_halb is None:
            in_hayz = None
            hayz_reason = (
                "halb_not_evaluable"
                if gender_matches is not None
                else "halb_and_gender_not_evaluable"
            )
            hayz_component = SectComponentTruth(
                kind=SectComponentKind.HAYZ,
                status=TruthEvaluationStatus.NOT_EVALUABLE,
                matched=None,
                reason=hayz_reason,
            )
        elif gender_matches is None:
            in_hayz = None
            hayz_component = SectComponentTruth(
                kind=SectComponentKind.HAYZ,
                status=TruthEvaluationStatus.NOT_EVALUABLE,
                matched=None,
                reason="planetary_gender_preference_not_defined",
            )
        else:
            in_hayz = bool(in_halb and gender_matches)
            hayz_component = SectComponentTruth(
                kind=SectComponentKind.HAYZ,
                status=TruthEvaluationStatus.EVALUATED,
                matched=in_hayz,
            )
        hayz_evaluable = hayz_component.status is TruthEvaluationStatus.EVALUATED

        return SectTruth(
            doctrine=doctrine,
            is_day_chart=is_day_chart,
            sect_light="Sun" if is_day_chart else "Moon",
            planet_sect=planet_sect,
            mercury_rises_before_sun=mercury_rises_before_sun,
            in_sect=in_sect,
            in_halb=in_halb,
            in_hayz=in_hayz,
            preferred_hemisphere=preferred_hemisphere,
            actual_hemisphere=actual_hemisphere,
            hemisphere_matches=hemisphere_matches,
            preferred_gender=preferred_gender,
            actual_gender=actual_gender,
            gender_matches=gender_matches,
            hayz_evaluable=hayz_evaluable,
            mercury_phase_truth=mercury_phase_truth,
            horizon_truth=horizon_truth,
            components=(sect_component, halb_component, hayz_component),
        )

    @staticmethod
    def _build_horizon_truth(
        longitude: float,
        frame: DignityHorizonFrame,
    ) -> HorizonTruth:
        """Classify one longitude using exact Asc/MC horizon geometry."""

        lon = longitude % 360.0
        asc = frame.asc_longitude
        dsc = (asc + 180.0) % 360.0

        def circular_distance(left: float, right: float) -> float:
            delta = abs((left - right) % 360.0)
            return min(delta, 360.0 - delta)

        boundary_distance = min(
            circular_distance(lon, asc),
            circular_distance(lon, dsc),
        )
        if boundary_distance <= frame.boundary_tolerance_deg:
            return HorizonTruth(
                status=TruthEvaluationStatus.NOT_EVALUABLE,
                method=HorizonComputationMethod.ZODIACAL_ANGLES,
                longitude=lon,
                hemisphere=None,
                asc_longitude=asc,
                mc_longitude=frame.mc_longitude,
                boundary_distance_deg=boundary_distance,
                reason="body_on_ascendant_or_descendant",
            )

        mc_on_asc_arc = 0.0 < (frame.mc_longitude - asc) % 360.0 < 180.0
        body_on_asc_arc = 0.0 < (lon - asc) % 360.0 < 180.0
        hemisphere = (
            HorizonHemisphere.ABOVE
            if body_on_asc_arc == mc_on_asc_arc
            else HorizonHemisphere.BELOW
        )
        return HorizonTruth(
            status=TruthEvaluationStatus.EVALUATED,
            method=HorizonComputationMethod.ZODIACAL_ANGLES,
            longitude=lon,
            hemisphere=hemisphere,
            asc_longitude=asc,
            mc_longitude=frame.mc_longitude,
            boundary_distance_deg=boundary_distance,
        )

    @staticmethod
    def _validate_policy(policy: DignityComputationPolicy) -> None:
        if policy.essential.doctrine not in (
            EssentialDignityDoctrine.TRADITIONAL_CLASSIC_7,
            EssentialDignityDoctrine.MODERN_CO_RULERS,
        ):
            raise ValueError(f"Unsupported essential dignity doctrine: {policy.essential.doctrine}")
        if policy.accidental.sect.mercury_sect_model is not MercurySectModel.LONGITUDE_HEURISTIC:
            raise ValueError(f"Unsupported Mercury sect model: {policy.accidental.sect.mercury_sect_model}")
        if (
            policy.accidental.sect.doctrine
            is not HalbHayzDoctrine.AL_BIRUNI_1030_SECTION_496
        ):
            raise ValueError(
                f"Unsupported Halb/Hayz doctrine: {policy.accidental.sect.doctrine}"
            )
        if not isinstance(policy.essential.bounds_doctrine, EgyptianBoundsDoctrine):
            raise ValueError(
                f"Unsupported bounds doctrine: {policy.essential.bounds_doctrine}"
            )
        if policy.essential.triplicity_doctrine is not TriplicityDoctrine.DOROTHEAN_PINGREE_1976:
            raise ValueError(
                f"Unsupported triplicity doctrine: {policy.essential.triplicity_doctrine}"
            )
        if not isinstance(policy.essential.participating_ruler_policy, _ParticipatingRulerPolicy):
            raise ValueError(
                "Unsupported participating-ruler policy: "
                f"{policy.essential.participating_ruler_policy}"
            )
        if not isinstance(policy.scoring.mode, DignityScoringMode):
            raise ValueError(f"Unsupported dignity scoring mode: {policy.scoring.mode}")
        if not isinstance(policy.scoring.node_doctrine, DignityNodeDoctrine):
            raise ValueError(f"Unsupported node doctrine: {policy.scoring.node_doctrine}")
        if policy.scoring.mode is DignityScoringMode.WILLIAM_LILLY_1647:
            if policy.essential.doctrine is not EssentialDignityDoctrine.TRADITIONAL_CLASSIC_7:
                raise ValueError(
                    "william_lilly_1647 scoring requires traditional_classic_7 rulers"
                )
            if policy.essential.bounds_doctrine is not EgyptianBoundsDoctrine.PTOLEMAIC:
                raise ValueError(
                    "william_lilly_1647 scoring requires ptolemaic bounds"
                )
            if (
                policy.essential.participating_ruler_policy
                is not _ParticipatingRulerPolicy.IGNORE
            ):
                raise ValueError(
                    "william_lilly_1647 scoring does not award a participating triplicity ruler"
                )

    @staticmethod
    def _mercury_rises_before_sun(
        mercury_lon: float,
        sun_lon: float,
        policy: DignityComputationPolicy,
    ) -> bool | None:
        """Compatibility projection of the typed Mercury phase truth."""

        return DignitiesService._build_mercury_phase_truth(
            mercury_lon=mercury_lon,
            sun_lon=sun_lon,
            policy=policy,
        ).rises_before_sun

    @staticmethod
    def _build_mercury_phase_truth(
        mercury_lon: float,
        sun_lon: float,
        policy: DignityComputationPolicy,
    ) -> MercuryPhaseTruth:
        if policy.accidental.sect.mercury_sect_model is not MercurySectModel.LONGITUDE_HEURISTIC:
            raise ValueError(f"Unsupported Mercury sect model: {policy.accidental.sect.mercury_sect_model}")
        mercury_diff = (mercury_lon - sun_lon + 360.0) % 360.0
        if min(mercury_diff, 360.0 - mercury_diff) <= 1e-7:
            return MercuryPhaseTruth(
                model=policy.accidental.sect.mercury_sect_model,
                status=TruthEvaluationStatus.NOT_EVALUABLE,
                rises_before_sun=None,
                longitudinal_separation_deg=mercury_diff,
                reason="mercury_conjunct_sun",
            )
        return MercuryPhaseTruth(
            model=policy.accidental.sect.mercury_sect_model,
            status=TruthEvaluationStatus.EVALUATED,
            rises_before_sun=mercury_diff > 180.0,
            longitudinal_separation_deg=mercury_diff,
        )

    @staticmethod
    def _score_polarity(score: int) -> ConditionPolarity:
        if score > 0:
            return ConditionPolarity.STRENGTHENING
        if score < 0:
            return ConditionPolarity.WEAKENING
        return ConditionPolarity.NEUTRAL

    @staticmethod
    def _classify_essential_truth(truth: EssentialDignityTruth) -> EssentialDignityClassification:
        kinds = tuple(component.kind for component in truth.matched_components)
        primary_kind = kinds[0] if kinds else EssentialDignityKind.PEREGRINE
        return EssentialDignityClassification(
            kind=primary_kind,
            kinds=kinds,
            polarity=DignitiesService._score_polarity(truth.weight_total),
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
            ("motion", "stationary"): AccidentalConditionKind.STATIONARY,
            ("speed", "swift"): AccidentalConditionKind.SWIFT,
            ("speed", "slow"): AccidentalConditionKind.SLOW,
            ("solar", "cazimi"): AccidentalConditionKind.CAZIMI,
            ("solar", "combust"): AccidentalConditionKind.COMBUST,
            ("solar", "under_sunbeams"): AccidentalConditionKind.UNDER_SUNBEAMS,
            ("solar", "free_from_beams"): AccidentalConditionKind.FREE_FROM_BEAMS,
            ("mutual_reception", "domicile"): AccidentalConditionKind.MUTUAL_RECEPTION,
            ("mutual_reception", "exaltation"): AccidentalConditionKind.MUTUAL_EXALTATION,
            ("sect", "hayz"): AccidentalConditionKind.HAYZ,
            ("sect", "halb"): AccidentalConditionKind.HALB,
            ("joy", "joy"): AccidentalConditionKind.JOY,
            ("phase", "oriental"): AccidentalConditionKind.ORIENTAL,
            ("phase", "occidental"): AccidentalConditionKind.OCCIDENTAL,
            ("lunar_phase", "waxing"): AccidentalConditionKind.MOON_WAXING,
            ("lunar_phase", "waning"): AccidentalConditionKind.MOON_WANING,
            ("node", "north_node_conjunction"): AccidentalConditionKind.NORTH_NODE_CONTACT,
            ("node", "south_node_conjunction"): AccidentalConditionKind.SOUTH_NODE_CONTACT,
            ("besieging", "besieged"): AccidentalConditionKind.BESIEGED,
            # P7 timelord / valens distributions (both polarities map to the same kind; polarity derived from score)
            ("timelord", "valens_benefic"): AccidentalConditionKind.TIMELORD_DISTRIBUTION,
            ("timelord", "valens_malefic"): AccidentalConditionKind.TIMELORD_DISTRIBUTION,
        }
        key = (condition.category, condition.code)
        if condition.category == "benefic_aspect":
            kind = AccidentalConditionKind.BENEFIC_ASPECT
        elif condition.category == "malefic_aspect":
            kind = AccidentalConditionKind.MALEFIC_ASPECT
        elif condition.category == "fixed_star":
            kind = AccidentalConditionKind.FIXED_STAR_CONTACT
        else:
            kind = kind_map[key]
        return AccidentalConditionClassification(
            kind=kind,
            category=condition.category,
            polarity=DignitiesService._score_polarity(condition.weight or 0),
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
        if truth.in_hayz is True:
            state = SectStateKind.IN_HAYZ
        elif truth.in_halb is True:
            state = SectStateKind.IN_HALB
        elif truth.in_sect is True:
            state = SectStateKind.IN_SECT
        elif truth.in_sect is None:
            state = SectStateKind.NOT_EVALUABLE
        else:
            state = SectStateKind.OUT_OF_SECT
        return SectClassification(
            state=state,
            in_sect=truth.in_sect,
            in_halb=truth.in_halb,
            in_hayz=truth.in_hayz,
            components=truth.components,
        )

    @staticmethod
    def _classify_solar_truth(truth: SolarConditionTruth) -> SolarConditionClassification:
        kind_map = {
            None: SolarConditionKind.NONE,
            "cazimi": SolarConditionKind.CAZIMI,
            "combust": SolarConditionKind.COMBUST,
            "under_sunbeams": SolarConditionKind.UNDER_SUNBEAMS,
            "free_from_beams": SolarConditionKind.FREE_FROM_BEAMS,
        }
        return SolarConditionClassification(
            kind=kind_map[truth.condition],
            polarity=DignitiesService._score_polarity(truth.weight),
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
                polarity=DignitiesService._score_polarity(truth.weight or 0),
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
        mutual_relations = [
            reception for reception in admitted_receptions
            if reception.mode is ReceptionMode.MUTUAL
        ]
        scored_receptions = [
            reception
            for reception, truth in zip(mutual_relations, mutual_reception_truth)
            if truth.scored
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
        policy: DignityComputationPolicy | None = None,
    ) -> dict[str, list[PlanetaryReception]]:
        policy = DignityComputationPolicy() if policy is None else policy
        receptions: dict[str, list[PlanetaryReception]] = {}
        planet_order = DignitiesService._dignity_planet_order(policy)
        planets = [planet for planet in planet_order if planet in planet_signs]

        basis_maps = {
            ReceptionBasis.DOMICILE: DignitiesService._domicile_table(policy),
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
                    planet_order.index(reception.host_planet)
                    if reception.host_planet in planet_order else 99,
                )
            )
        return receptions

    @staticmethod
    def _policy_reception_bases(policy: DignityComputationPolicy) -> tuple[ReceptionBasis, ...]:
        bases: list[ReceptionBasis] = []
        if policy.reception.include_domicile:
            bases.append(ReceptionBasis.DOMICILE)
        if policy.reception.include_exaltation:
            bases.append(ReceptionBasis.EXALTATION)
        return tuple(bases)

    @staticmethod
    def _build_mutual_reception_truths(
        receptions: list[PlanetaryReception],
        policy: DignityComputationPolicy,
    ) -> list[MutualReceptionTruth]:
        should_score = policy.scoring.mode is not DignityScoringMode.UNSCORED
        truths: list[MutualReceptionTruth] = []
        for relation in receptions:
            if relation.mode is not ReceptionMode.MUTUAL:
                continue
            if relation.basis is ReceptionBasis.DOMICILE:
                reception_type = "domicile"
                label = f"Mutual Reception ({relation.host_planet})"
                weight = SCORE_MR_DOMICILE
            elif relation.basis is ReceptionBasis.EXALTATION:
                reception_type = "exaltation"
                label = f"Mutual Exaltation ({relation.host_planet})"
                weight = SCORE_MR_EXALTATION
            else:
                continue
            truths.append(
                MutualReceptionTruth(
                    other_planet=relation.host_planet,
                    reception_type=reception_type,
                    label=label,
                    score=weight if should_score else 0,
                    weight=weight,
                    scored=should_score,
                )
            )
        return truths

    @staticmethod
    def _normalize_planet_positions(planet_positions: list[dict]) -> list[dict[str, object]]:
        if not isinstance(planet_positions, list):
            raise ValueError("planet_positions must be a list of dictionaries")

        normalized: list[dict[str, object]] = []
        seen_supported: set[str] = set()
        duplicate_guard = CLASSIC_7 | MODERN_OUTER_3
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

            retro_value = pos.get("is_retrograde")
            if retro_value is not None and not isinstance(retro_value, bool):
                raise ValueError(f"planet_positions[{index}].is_retrograde must be a bool when provided")

            speed_value = pos.get("speed")
            if speed_value is None:
                speed = None
            else:
                try:
                    speed = float(speed_value)
                except (TypeError, ValueError):
                    raise ValueError(f"planet_positions[{index}].speed must be a real number") from None
                if not math.isfinite(speed):
                    raise ValueError(f"planet_positions[{index}].speed must be finite")
                speed_retrograde = speed < 0.0
                if retro_value is not None and retro_value != speed_retrograde:
                    raise ValueError(
                        f"planet_positions[{index}] has contradictory speed and is_retrograde"
                    )
                if retro_value is None:
                    retro_value = speed_retrograde

            if normalized_name in duplicate_guard:
                if normalized_name in seen_supported:
                    if normalized_name in CLASSIC_7:
                        raise ValueError(f"planet_positions contains duplicate entry for classic planet {normalized_name!r}")
                    raise ValueError(f"planet_positions contains duplicate entry for modern dignity planet {normalized_name!r}")
                seen_supported.add(normalized_name)

            normalized.append(
                {
                    "name": normalized_name,
                    "degree": degree,
                    "is_retrograde": retro_value,
                    "speed": speed,
                }
            )
        return normalized

    @staticmethod
    def _normalize_named_longitudes(
        positions: dict[str, float] | None,
        *,
        field_name: str,
    ) -> dict[str, float]:
        if positions is None:
            return {}
        if not isinstance(positions, dict):
            raise ValueError(f"{field_name} must be a dictionary")
        normalized: dict[str, float] = {}
        for name, value in positions.items():
            if not isinstance(name, str) or not name.strip():
                raise ValueError(f"{field_name} names must be non-empty strings")
            try:
                longitude = float(value)
            except (TypeError, ValueError):
                raise ValueError(f"{field_name}[{name!r}] must be a real number") from None
            if not math.isfinite(longitude):
                raise ValueError(f"{field_name}[{name!r}] must be finite")
            normalized[name.strip()] = longitude % 360.0
        return normalized

    @staticmethod
    def _find_mutual_receptions(
        planet_signs: dict[str, str]
    ) -> dict[str, list[tuple[str, str]]]:
        receptions = DignitiesService._find_receptions(
            planet_signs,
            bases=DignitiesService._policy_reception_bases(DignityComputationPolicy()),
            policy=DignityComputationPolicy(),
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
    *,
    horizon_frame: DignityHorizonFrame | None = None,
    node_positions: dict[str, float] | None = None,
    fixed_star_positions: dict[str, float] | None = None,
) -> list[PlanetaryDignity]:
    """
    Calculate essential and accidental dignities.

    Parameters
    ----------
    planet_positions : list of {'name': str, 'degree': float, 'is_retrograde': bool, 'speed': float}
    house_positions  : list of {'number': int, 'degree': float}
    policy           : optional DignityComputationPolicy
    horizon_frame    : optional exact Ascendant/Midheaven geometry
    """
    return _service.calculate_dignities(
        planet_positions,
        house_positions,
        policy=policy,
        horizon_frame=horizon_frame,
        node_positions=node_positions,
        fixed_star_positions=fixed_star_positions,
    )


def calculate_receptions(
    planet_positions: list[dict],
    policy: DignityComputationPolicy | None = None,
) -> list[PlanetaryReception]:
    """Calculate formal reception relations for planets admitted by policy."""

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
    *,
    horizon_frame: DignityHorizonFrame | None = None,
    node_positions: dict[str, float] | None = None,
    fixed_star_positions: dict[str, float] | None = None,
) -> list[PlanetaryConditionProfile]:
    """Calculate integrated per-planet condition profiles."""

    return _service.calculate_condition_profiles(
        planet_positions,
        house_positions,
        policy=policy,
        horizon_frame=horizon_frame,
        node_positions=node_positions,
        fixed_star_positions=fixed_star_positions,
    )


def calculate_chart_condition_profile(
    planet_positions: list[dict],
    house_positions: list[dict],
    policy: DignityComputationPolicy | None = None,
    *,
    horizon_frame: DignityHorizonFrame | None = None,
    node_positions: dict[str, float] | None = None,
    fixed_star_positions: dict[str, float] | None = None,
) -> ChartConditionProfile:
    """Calculate the chart-wide condition profile."""

    return _service.calculate_chart_condition_profile(
        planet_positions,
        house_positions,
        policy=policy,
        horizon_frame=horizon_frame,
        node_positions=node_positions,
        fixed_star_positions=fixed_star_positions,
    )


def calculate_condition_network_profile(
    planet_positions: list[dict],
    house_positions: list[dict],
    policy: DignityComputationPolicy | None = None,
    *,
    horizon_frame: DignityHorizonFrame | None = None,
    node_positions: dict[str, float] | None = None,
    fixed_star_positions: dict[str, float] | None = None,
) -> ConditionNetworkProfile:
    """Calculate the reception / condition network profile."""

    return _service.calculate_condition_network_profile(
        planet_positions,
        house_positions,
        policy=policy,
        horizon_frame=horizon_frame,
        node_positions=node_positions,
        fixed_star_positions=fixed_star_positions,
    )


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
# Almuten Figuris & Compound Rulerships
# ---------------------------------------------------------------------------

ALMUTEN_HOUSE_SCORES: dict[int, int] = {
    1: 12,
    10: 11,
    7: 10,
    4: 9,
    11: 8,
    5: 7,
    9: 6,
    3: 5,
    2: 4,
    8: 3,
    6: 2,
    12: 1,
}


def almuten_of_degree(longitude: float, is_day: bool) -> str:
    """
    Find the Almuten of a specific ecliptic longitude (degree) based on
    essential dignity scores: domicile (5), exaltation (4), triplicity (3),
    bound/term (2), and face/decan (1).

    Parameters
    ----------
    longitude : float
        Ecliptic longitude in degrees.
    is_day : bool
        True if the chart is diurnal (affects triplicity).

    Returns
    -------
    str
        The name of the planet (Classic 7) with the highest score.
    """
    if not isinstance(longitude, (int, float)):
        raise TypeError(f"longitude must be float or int, got {type(longitude).__name__}")
    if math.isnan(longitude) or math.isinf(longitude):
        raise ValueError("longitude cannot be NaN or infinite")
    if not isinstance(is_day, bool):
        raise TypeError(f"is_day must be a boolean, got {type(is_day).__name__}")

    from .longevity import dignity_score_at, EGYPTIAN_BOUNDS, FACE_RULERS, _sign_and_deg
    from .triplicity import triplicity_score as _triplicity_score

    scores: dict[str, int] = {}
    for planet in _PLANET_ORDER:
        scores[planet] = dignity_score_at(planet, longitude, is_day)

    sign, deg_in_sign = _sign_and_deg(longitude)

    def get_highest_rank(planet: str) -> int:
        if sign in DOMICILE.get(planet, []):
            return 5
        if sign in EXALTATION.get(planet, []):
            return 4
        tri_score = _triplicity_score(
            planet, sign,
            is_day_chart=is_day,
            participating_policy=_ParticipatingRulerPolicy.AWARD_REDUCED,
        )
        if tri_score > 0:
            return 3
        bounds = EGYPTIAN_BOUNDS.get(sign, [])
        for ruler, start, end in bounds:
            if start <= deg_in_sign < end and ruler == planet:
                return 2
        lon_norm = longitude % 360.0
        decan_idx = int(lon_norm // 10) % 36
        face_ruler = FACE_RULERS[decan_idx]
        if face_ruler == planet:
            return 1
        return 0

    best_planet = max(
        _PLANET_ORDER,
        key=lambda p: (scores[p], get_highest_rank(p), -_PLANET_ORDER.index(p))
    )
    return best_planet


def almuten_figuris(
    planet_positions: dict[str, float],
    cusps: list[float] | dict[int, float] | float,
    is_day: bool,
    *,
    prenatal_syzygy_lon: float | None = None,
    day_ruler: str | None = None,
    hour_ruler: str | None = None,
) -> str:
    """
    Find the Almuten Figuris — the planet with the most essential and accidental
    dignities across the key aphetic points.

    If `cusps` is a float/int (representing the Ascendant longitude), we fall
    back to the old simplified calculation scoring only Sun, Moon, and Ascendant
    for essential dignities.

    Otherwise, we perform the full traditional calculation scoring:
    - Essential dignities at Sun, Moon, Ascendant, Lot of Fortune, and prenatal Syzygy.
    - Accidental dignities based on house placement of each planet.
    - Planetary day (+7) and hour (+6) rulers.

    Parameters
    ----------
    planet_positions : dict of body → longitude (must include "Sun", "Moon")
    cusps            : list of 12 cusps, dict of 1..12 cusps, or float (ASC longitude for fallback)
    is_day           : True for day chart (affects triplicity)
    prenatal_syzygy_lon : optional prenatal syzygy longitude
    day_ruler        : optional day ruler planet name
    hour_ruler       : optional hour ruler planet name

    Returns
    -------
    Planet name (string)
    """
    if not isinstance(planet_positions, dict):
        raise TypeError(f"planet_positions must be a dictionary, got {type(planet_positions).__name__}")
    for k, v in planet_positions.items():
        if not isinstance(k, str):
            raise TypeError(f"planet_positions keys must be strings, got {type(k).__name__}")
        if not isinstance(v, (int, float)):
            raise TypeError(f"planet_positions value for '{k}' must be float or int, got {type(v).__name__}")
        if math.isnan(v) or math.isinf(v):
            raise ValueError(f"planet position for '{k}' cannot be NaN or infinite")

    if "Sun" not in planet_positions:
        raise ValueError("planet_positions must contain 'Sun'")
    if "Moon" not in planet_positions:
        raise ValueError("planet_positions must contain 'Moon'")

    if not isinstance(is_day, bool):
        raise TypeError(f"is_day must be a boolean, got {type(is_day).__name__}")

    if prenatal_syzygy_lon is not None:
        if not isinstance(prenatal_syzygy_lon, (int, float)):
            raise TypeError(f"prenatal_syzygy_lon must be float or int, got {type(prenatal_syzygy_lon).__name__}")
        if math.isnan(prenatal_syzygy_lon) or math.isinf(prenatal_syzygy_lon):
            raise ValueError("prenatal_syzygy_lon cannot be NaN or infinite")

    if day_ruler is not None:
        if not isinstance(day_ruler, str):
            raise TypeError(f"day_ruler must be a string, got {type(day_ruler).__name__}")
        if day_ruler not in CLASSIC_7:
            raise ValueError(f"day_ruler must be one of the Classic 7 planets {CLASSIC_7}, got '{day_ruler}'")

    if hour_ruler is not None:
        if not isinstance(hour_ruler, str):
            raise TypeError(f"hour_ruler must be a string, got {type(hour_ruler).__name__}")
        if hour_ruler not in CLASSIC_7:
            raise ValueError(f"hour_ruler must be one of the Classic 7 planets {CLASSIC_7}, got '{hour_ruler}'")

    from .longevity import dignity_score_at, _get_house

    # 1. Fallback to old simplified calculation if cusps is a single float
    if isinstance(cusps, (int, float)):
        if math.isnan(cusps) or math.isinf(cusps):
            raise ValueError("cusps as a float/int cannot be NaN or infinite")
        asc_longitude = float(cusps)
        key_points = [
            planet_positions.get("Sun", 0.0),
            planet_positions.get("Moon", 0.0),
            asc_longitude,
        ]
        scores: dict[str, int] = {}
        for planet in _PLANET_ORDER:
            total = sum(dignity_score_at(planet, lon, is_day) for lon in key_points)
            scores[planet] = total
        return max(_PLANET_ORDER, key=lambda p: scores[p])

    # Validate cusps sequence or dictionary
    if isinstance(cusps, dict):
        for i in range(1, 13):
            if i not in cusps:
                raise ValueError(f"cusps dictionary is missing key for house {i}")
            val = cusps[i]
            if not isinstance(val, (int, float)):
                raise TypeError(f"cusps value for house {i} must be float or int, got {type(val).__name__}")
            if math.isnan(val) or math.isinf(val):
                raise ValueError(f"cusps value for house {i} cannot be NaN or infinite")
        asc_longitude = cusps[1]
    elif isinstance(cusps, (list, tuple)):
        if len(cusps) < 12:
            raise ValueError(f"cusps sequence must contain at least 12 elements, got {len(cusps)}")
        for i in range(12):
            val = cusps[i]
            if not isinstance(val, (int, float)):
                raise TypeError(f"cusps value at index {i} must be float or int, got {type(val).__name__}")
            if math.isnan(val) or math.isinf(val):
                raise ValueError(f"cusps value at index {i} cannot be NaN or infinite")
        asc_longitude = cusps[0]
    else:
        raise TypeError(f"cusps must be float, list, or dict, got {type(cusps).__name__}")

    sun_longitude = planet_positions.get("Sun", 0.0)
    moon_longitude = planet_positions.get("Moon", 0.0)

    # Calculate Lot of Fortune
    if is_day:
        fortune_longitude = (asc_longitude + moon_longitude - sun_longitude) % 360.0
    else:
        fortune_longitude = (asc_longitude + sun_longitude - moon_longitude) % 360.0

    # Resolve prenatal syzygy degree
    syzygy_longitude = prenatal_syzygy_lon
    if syzygy_longitude is None:
        syzygy_longitude = planet_positions.get("Syzygy")

    # Determine key points to score essential dignities at
    key_points = [sun_longitude, moon_longitude, asc_longitude, fortune_longitude]
    if syzygy_longitude is not None:
        key_points.append(syzygy_longitude)

    scores = {}
    for planet in _PLANET_ORDER:
        # Sum essential dignities across key points
        essential_total = sum(dignity_score_at(planet, lon, is_day) for lon in key_points)

        # Accidental dignity: house placement of the planet itself
        planet_lon = planet_positions.get(planet)
        house_points = 0
        if planet_lon is not None:
            house_num = _get_house(planet_lon, cusps)
            house_points = ALMUTEN_HOUSE_SCORES.get(house_num, 0)

        # Accidental dignity: day and hour rulers
        ruler_points = 0
        if day_ruler is not None and day_ruler == planet:
            ruler_points += 7
        if hour_ruler is not None and hour_ruler == planet:
            ruler_points += 6

        scores[planet] = essential_total + house_points + ruler_points

    return max(_PLANET_ORDER, key=lambda p: scores[p])


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
