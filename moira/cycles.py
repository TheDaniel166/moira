"""
moira/cycles.py — Planetary Cycles Engine

Purpose
-------
This Pillar provides cyclical timing Engines grounded in astronomical
periodicity and classical temporal doctrine: return series, synodic-cycle
position, Jupiter-Saturn great conjunction structure, planetary ages, a
streamlined Firdar family, and Chaldean planetary day/hour sequences.

Boundary
--------
Owns:
    - Cyclical result vessels and classification enums for the public cycles surface.
    - Return-series aggregation and cyclical profile surfaces.
    - Great-conjunction and mutation-period grouping logic.
    - Planetary-age and Chaldean day/hour doctrine surfaces.
Delegates:
    - Exact return solving to `moira.transits`.
    - Synodic geometry inputs to the astronomical Pillars it calls.
    - Kernel access to `moira.spk_reader` where astronomical state is needed.
Does not own:
    - Natal chart construction.
    - General transit condition profiling.
    - The more elaborate timelord relational surfaces housed in `moira.timelords`.

Import-time side effects
------------------------
None.

External dependency assumptions
-------------------------------
- A compatible planetary kernel must be discoverable for the astronomical
  surfaces that require live planetary positions.
- Callers supply Julian Days and natal longitudes in the expected domains.
- Historical/doctrinal layer choices are explicit in the exposed surfaces; this
  Pillar does not silently promote one doctrine family into another.

Public surface / exports
------------------------
`SynodicPhase`, `GreatMutationElement`, `PlanetaryAgeName`, `ReturnEvent`,
`ReturnSeries`, `return_series`, `half_return_series`, `lifetime_returns`,
`SynodicCyclePosition`, `synodic_cycle_position`, `GreatConjunction`,
`GreatConjunctionSeries`, `MutationPeriod`, `great_conjunctions`,
`mutation_period_at`, `PlanetaryAgePeriod`, `PlanetaryAgeProfile`,
`planetary_age_at`, `planetary_age_profile`, `FirdarSubPeriod`,
`FirdarPeriod`, `FirdarSeries`, `firdar_series`, `firdar_at`,
`PlanetaryDayInfo`, `PlanetaryHour`, `PlanetaryHoursProfile`,
`planetary_day_ruler`, `planetary_hours_for_day`
"""

import math
from dataclasses import dataclass
from enum import Enum

from .constants import Body, sign_of
from .spk_reader import KernelReader, SpkReader, get_reader


# ===========================================================================
# PUBLIC API
# ===========================================================================

__all__ = [
    # Enums
    "SynodicPhase",
    "GreatMutationElement",
    "PlanetaryAgeName",
    # Return series
    "ReturnEvent",
    "ReturnSeries",
    "return_series",
    "half_return_series",
    "lifetime_returns",
    # Synodic cycles
    "SynodicCyclePosition",
    "synodic_cycle_position",
    # Great conjunctions
    "GreatConjunction",
    "GreatConjunctionSeries",
    "MutationPeriod",
    "great_conjunctions",
    "mutation_period_at",
    # Planetary ages
    "PlanetaryAgePeriod",
    "PlanetaryAgeProfile",
    "planetary_age_at",
    "planetary_age_profile",
    # Firdar
    "FirdarPeriod",
    "FirdarSubPeriod",
    "FirdarSeries",
    "firdar_series",
    "firdar_at",
    # Planetary days and hours
    "PlanetaryDayInfo",
    "PlanetaryHour",
    "PlanetaryHoursProfile",
    "planetary_day_ruler",
    "planetary_hours_for_day",
]


# ===========================================================================
# CONSTANTS
# ===========================================================================

# The Chaldean order: descending geocentric orbital period.
# This sequence governs planetary hours and the weekday ruler derivation.
CHALDEAN_ORDER: tuple[str, ...] = (
    Body.SATURN, Body.JUPITER, Body.MARS, Body.SUN,
    Body.VENUS, Body.MERCURY, Body.MOON,
)

_CHALDEAN_INDEX: dict[str, int] = {p: i for i, p in enumerate(CHALDEAN_ORDER)}

# Julian year in days — the firdar and age computation standard.
_JULIAN_YEAR: float = 365.25


# ===========================================================================
# SECTION 1 — ENUMS
# ===========================================================================

class SynodicPhase(str, Enum):
    """
    RITE: The Phase Oracle — eight-fold synodic phase classification archetype.

    THEOREM: Classifies synodic phase angles (0–360°) into eight traditional
    lunar-style phases based on angular separation between two celestial bodies.

    RITE OF PURPOSE:
        SynodicPhase serves the Cycles Engine as the canonical classifier for
        synodic relationships between any two bodies. Without it, synodic cycle
        analysis would lack the traditional eight-fold phase structure that
        connects modern astrological practice to ancient lunar phase doctrine.
        It bridges raw angular measurements to meaningful cyclical archetypes.

    LAW OF OPERATION:
        Responsibilities:
            - Classify phase angles (0–360°) into eight named phases
            - Provide the from_angle() static method for angle-to-phase conversion
            - Maintain the traditional 45° phase boundaries with ±22.5° bands
            - Preserve the Rudhyar-derived eight-fold classification system
        Non-responsibilities:
            - Does not compute synodic angles (delegates to calling functions)
            - Does not interpret phase meanings or provide astrological advice
            - Does not handle multi-body or complex cyclical relationships
        Dependencies:
            - None (pure enumeration with static classification logic)
        Structural invariants:
            - Eight phases cover the complete 360° cycle without gaps or overlaps
            - Phase boundaries are fixed at 22.5° intervals
            - NEW phase handles both 0° vicinity and 360° wraparound
        Behavioral invariants:
            - from_angle() always returns a valid SynodicPhase for any input
            - Phase classification is deterministic and stable

    Canon: Dane Rudhyar, "The Lunation Cycle" (1967); traditional lunar phase doctrine.

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.cycles.SynodicPhase",
        "risk": "low",
        "api": {
            "public_methods": ["from_angle"],
            "public_attributes": [
                "NEW", "WAXING_CRESCENT", "FIRST_QUARTER", "WAXING_GIBBOUS",
                "FULL", "WANING_GIBBOUS", "LAST_QUARTER", "WANING_CRESCENT"
            ]
        },
        "state": {
            "mutable": false,
            "fields": ["value"]
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
            "policy": "pure classification never fails"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]
    """

    NEW               = "new"                # 0° ± 22.5°
    WAXING_CRESCENT   = "waxing_crescent"    # 22.5° – 67.5°
    FIRST_QUARTER     = "first_quarter"      # 67.5° – 112.5°
    WAXING_GIBBOUS    = "waxing_gibbous"     # 112.5° – 157.5°
    FULL              = "full"               # 157.5° – 202.5°
    WANING_GIBBOUS    = "waning_gibbous"     # 202.5° – 247.5°
    LAST_QUARTER      = "last_quarter"       # 247.5° – 292.5°
    WANING_CRESCENT   = "waning_crescent"    # 292.5° – 337.5°
    # Closes back to NEW at 337.5°

    @staticmethod
    def from_angle(angle_deg: float) -> "SynodicPhase":
        """Classify a synodic phase angle (0–360°) into one of eight phases."""
        a = angle_deg % 360.0
        if a < 22.5 or a >= 337.5:
            return SynodicPhase.NEW
        if a < 67.5:
            return SynodicPhase.WAXING_CRESCENT
        if a < 112.5:
            return SynodicPhase.FIRST_QUARTER
        if a < 157.5:
            return SynodicPhase.WAXING_GIBBOUS
        if a < 202.5:
            return SynodicPhase.FULL
        if a < 247.5:
            return SynodicPhase.WANING_GIBBOUS
        if a < 292.5:
            return SynodicPhase.LAST_QUARTER
        return SynodicPhase.WANING_CRESCENT


class GreatMutationElement(str, Enum):
    """
    RITE: The Elemental Trigon Oracle — four-fold elemental classification for great conjunctions.

    THEOREM: Classifies zodiacal signs into their traditional elemental trigons
    for Jupiter-Saturn great conjunction cycle analysis.

    RITE OF PURPOSE:
        GreatMutationElement serves the Cycles Engine as the elemental classifier
        for the ~800-year great mutation cycle. Without it, great conjunction
        analysis would lack the traditional elemental framework that connects
        individual conjunctions to their broader historical and mundane context.
        It bridges zodiacal positions to elemental doctrine.

    LAW OF OPERATION:
        Responsibilities:
            - Classify zodiacal signs into four elemental trigons
            - Provide the traditional Fire/Earth/Air/Water groupings
            - Support great conjunction elemental sequence analysis
        Non-responsibilities:
            - Does not compute conjunction positions or timing
            - Does not interpret elemental meanings or provide predictions
            - Does not handle sign-to-element conversion (delegates to calling code)
        Dependencies:
            - None (pure enumeration of traditional elemental doctrine)
        Structural invariants:
            - Four elements cover all twelve zodiacal signs in trigon groups
            - Each element contains exactly three signs (120° apart)
            - Traditional elemental assignments are preserved
        Behavioral invariants:
            - Enumeration values are stable and deterministic

    Canon: Traditional elemental doctrine; Ptolemy, "Tetrabiblos" I.

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.cycles.GreatMutationElement",
        "risk": "low",
        "api": {
            "public_attributes": ["FIRE", "EARTH", "AIR", "WATER"]
        },
        "state": {
            "mutable": false,
            "fields": ["value"]
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
            "policy": "pure enumeration never fails"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]
    """

    FIRE  = "fire"    # Aries, Leo, Sagittarius
    EARTH = "earth"   # Taurus, Virgo, Capricorn
    AIR   = "air"     # Gemini, Libra, Aquarius
    WATER = "water"   # Cancer, Scorpio, Pisces


class PlanetaryAgeName(str, Enum):
    """
    The seven planetary ages of human life (Ptolemy, Tetrabiblos I.10).

    Each planet governs a stage of development corresponding to its
    astronomical nature.  The Moon governs infancy (rapid change), Mercury
    governs childhood (learning), and so on through Saturn's governance
    of old age (contraction and cold).
    """

    MOON    = "Moon"
    MERCURY = "Mercury"
    VENUS   = "Venus"
    SUN     = "Sun"
    MARS    = "Mars"
    JUPITER = "Jupiter"
    SATURN  = "Saturn"


# ===========================================================================
# SECTION 2 — RESULT VESSELS
# ===========================================================================

# ---- Return Series ----

@dataclass(frozen=True, slots=True)
class ReturnEvent:
    """
    RITE: Witness vessel of one return occurrence.

    THEOREM: ReturnEvent stores one exact return or half-return event for a body at a specific Julian Day.

    RITE OF PURPOSE:
        This vessel gives the return-series surface a stable event object rather
        than anonymous tuples. It preserves both the numerical instant and the
        doctrinal classification of whether the event is a direct return or a
        half-return to the opposition point.

    LAW OF OPERATION:
        Responsibilities:
            - Carry one return event and its ordinal number.
            - Preserve the natal longitude target and half-return flag.
        Non-responsibilities:
            - Solving the return instant.
            - Grouping events into a series.
        Dependencies:
            - Produced by the return-series functions in this Pillar.
        Structural invariants:
            - `return_number >= 1`

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.cycles.ReturnEvent",
      "risk": "medium",
      "api": {
        "frozen": ["body", "return_number", "jd_ut", "longitude", "is_half"],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["return_series", "half_return_series", "lifetime_returns"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise_by_constructor_if_added"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    body:          str
    return_number: int
    jd_ut:         float
    longitude:     float
    is_half:       bool = False


@dataclass(frozen=True, slots=True)
class ReturnSeries:
    """
    RITE: Aggregate witness vessel for a body's return cycle.

    THEOREM: ReturnSeries stores all return events found for one body over a requested search window.

    RITE OF PURPOSE:
        This vessel preserves return-series truth as one inspectable object:
        search range, natal longitude, ordered events, and event count. Without
        it, callers would need to manage parallel arrays or infer context from a
        bare tuple of events.

    LAW OF OPERATION:
        Responsibilities:
            - Carry the search window and natal-longitude target.
            - Carry the chronologically ordered tuple of `ReturnEvent` objects.
            - Carry the event count as an explicit public field.
        Non-responsibilities:
            - Solving exact return instants.
            - Deciding broader transit doctrine outside return recurrence.
        Dependencies:
            - Produced by return-series functions in this Pillar.
        Structural invariants:
            - `count == len(returns)` is the intended public contract.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.cycles.ReturnSeries",
      "risk": "medium",
      "api": {
        "frozen": ["body", "natal_longitude", "jd_start", "jd_end", "returns", "count"],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["return_series", "half_return_series", "lifetime_returns"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise_by_constructor_if_added"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    body:             str
    natal_longitude:  float
    jd_start:         float
    jd_end:           float
    returns:          tuple[ReturnEvent, ...]
    count:            int


# ---- Synodic Cycle ----

@dataclass(frozen=True, slots=True)
class SynodicCyclePosition:
    """
    RITE: Synodic witness vessel for a two-body cycle state.

    THEOREM: SynodicCyclePosition stores the evaluated phase geometry and classification of two bodies at one Julian Day.

    RITE OF PURPOSE:
        This vessel binds raw longitudes, phase angle, waxing state, and
        eight-fold phase classification into one public object. It exists so
        synodic state can be inspected directly instead of reconstructed from
        multiple loose return values.

    LAW OF OPERATION:
        Responsibilities:
            - Carry the two bodies and the evaluation moment.
            - Carry the raw phase geometry and the derived phase classification.
            - Preserve the waxing or waning state as an explicit boolean.
        Non-responsibilities:
            - Solving conjunctions or other exact synodic roots.
            - Inferring broader doctrinal meaning beyond the exposed fields.
        Dependencies:
            - Produced by `synodic_cycle_position()`.
        Structural invariants:
            - `phase_angle` is intended to live in the normalized `0 <= angle < 360` domain.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.cycles.SynodicCyclePosition",
      "risk": "medium",
      "api": {
        "frozen": ["body1", "body2", "jd_ut", "phase_angle", "phase", "is_waxing", "lon1", "lon2"],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["synodic_cycle_position"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise_by_constructor_if_added"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    body1:       str
    body2:       str
    jd_ut:       float
    phase_angle: float
    phase:       SynodicPhase
    is_waxing:   bool
    lon1:        float
    lon2:        float


# ---- Great Conjunctions ----

@dataclass(frozen=True, slots=True)
class GreatConjunction:
    """
    RITE: Witness vessel of one Jupiter-Saturn conjunction.

    THEOREM: GreatConjunction stores one exact Jupiter-Saturn conjunction together with its zodiacal and elemental classification.

    RITE OF PURPOSE:
        This vessel preserves both the astronomical instant and the doctrinal
        sign-element interpretation used by the great-mutation surface. Without
        it, callers would have to reconstruct sign and element meaning from a
        bare longitude.

    LAW OF OPERATION:
        Responsibilities:
            - Carry one conjunction instant and longitude.
            - Carry sign, sign symbol, degree-in-sign, and elemental trigon classification.
        Non-responsibilities:
            - Solving the conjunction instant.
            - Grouping conjunctions into broader mutation periods.
        Dependencies:
            - Produced by `great_conjunctions()`.

    Canon: Abu Ma'shar, *On the Great Conjunctions*

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.cycles.GreatConjunction",
      "risk": "medium",
      "api": {
        "frozen": ["jd_ut", "longitude", "sign", "sign_symbol", "degree_in_sign", "element"],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["great_conjunctions"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise_by_constructor_if_added"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    jd_ut:          float
    longitude:      float
    sign:           str
    sign_symbol:    str
    degree_in_sign: float
    element:        GreatMutationElement


@dataclass(frozen=True, slots=True)
class GreatConjunctionSeries:
    """
    RITE: Aggregate witness vessel of a great-conjunction search.

    THEOREM: GreatConjunctionSeries stores all Jupiter-Saturn conjunctions found over one requested search window.

    RITE OF PURPOSE:
        This vessel keeps the conjunction search range, ordered conjunction
        witnesses, and observed elemental spread together as one stable public
        object.

    LAW OF OPERATION:
        Responsibilities:
            - Carry the search window.
            - Carry the ordered tuple of `GreatConjunction` witnesses.
            - Carry the explicit count and represented elements.
        Non-responsibilities:
            - Solving conjunction instants.
            - Defining broader historical interpretation beyond the exposed fields.
        Dependencies:
            - Produced by `great_conjunctions()`.

    Canon: Abu Ma'shar, *On the Great Conjunctions*

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.cycles.GreatConjunctionSeries",
      "risk": "medium",
      "api": {
        "frozen": ["jd_start", "jd_end", "conjunctions", "count", "elements_represented"],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["great_conjunctions"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise_by_constructor_if_added"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    jd_start:              float
    jd_end:                float
    conjunctions:          tuple[GreatConjunction, ...]
    count:                 int
    elements_represented:  tuple[GreatMutationElement, ...]


@dataclass(frozen=True, slots=True)
class MutationPeriod:
    """
    RITE: Grouping vessel for one elemental mutation era.

    THEOREM: MutationPeriod stores one dominant-element span within the great-conjunction cycle.

    RITE OF PURPOSE:
        This vessel binds the dominant element and its inaugurating and terminal
        conjunction witnesses into one inspectable period object so callers can
        reason about mutation epochs rather than isolated conjunction events.

    LAW OF OPERATION:
        Responsibilities:
            - Carry the dominant element of one mutation era.
            - Carry the inaugurating conjunction and optional terminal conjunction.
            - Carry the conjunction count within the era.
        Non-responsibilities:
            - Solving conjunction instants.
            - Performing historical interpretation beyond the exposed grouping.
        Dependencies:
            - Built from `GreatConjunction` witnesses in this Pillar.

    Canon: Abu Ma'shar, *On the Great Conjunctions*

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.cycles.MutationPeriod",
      "risk": "medium",
      "api": {
        "frozen": ["element", "start_conjunction", "end_conjunction", "conjunction_count"],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["great_conjunctions", "mutation_period_at"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise_by_constructor_if_added"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    element:              GreatMutationElement
    start_conjunction:    GreatConjunction
    end_conjunction:      GreatConjunction | None
    conjunction_count:    int


# ---- Planetary Ages ----

@dataclass(frozen=True, slots=True)
class PlanetaryAgePeriod:
    """
    RITE: One life-stage vessel in Ptolemy's seven-age model.

    THEOREM: PlanetaryAgePeriod stores one ruled age band in the seven-stage planetary life sequence.

    RITE OF PURPOSE:
        This vessel makes each age band explicit: ruler, age bounds, and label.
        It exists so the seven-age doctrine can be inspected as structured data
        instead of being re-encoded from prose every time it is queried.

    LAW OF OPERATION:
        Responsibilities:
            - Carry one age ruler and its age bounds.
            - Carry the public label for the age band.
        Non-responsibilities:
            - Choosing the current age for a query.
            - Interpreting the age beyond the exposed doctrinal banding.
        Dependencies:
            - Used by `planetary_age_profile()` and `planetary_age_at()`.

    Canon: Ptolemy, *Tetrabiblos* I.10

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.cycles.PlanetaryAgePeriod",
      "risk": "low",
      "api": {
        "frozen": ["ruler", "start_age", "end_age", "label"],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["planetary_age_profile", "planetary_age_at"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise_by_constructor_if_added"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    ruler:      PlanetaryAgeName
    start_age:  float
    end_age:    float | None    # None for Saturn (open-ended)
    label:      str


@dataclass(frozen=True, slots=True)
class PlanetaryAgeProfile:
    """
    RITE: Aggregate vessel of the full seven-age life model.

    THEOREM: PlanetaryAgeProfile stores the seven planetary age periods and the optional period selected for a queried age.

    RITE OF PURPOSE:
        This vessel keeps the entire seven-age structure and the query result in
        one public object so callers can inspect both the full doctrine and the
        selected current band without issuing separate calls.

    LAW OF OPERATION:
        Responsibilities:
            - Carry all seven age periods in order.
            - Carry the current age period for an optional queried age.
            - Carry the queried age itself when one was supplied.
        Non-responsibilities:
            - Defining the seven-age doctrine.
            - Extending the doctrine beyond the admitted planetary-age model.
        Dependencies:
            - Built from `PlanetaryAgePeriod` vessels in this Pillar.

    Canon: Ptolemy, *Tetrabiblos* I.10

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.cycles.PlanetaryAgeProfile",
      "risk": "low",
      "api": {
        "frozen": ["periods", "current", "queried_age"],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["planetary_age_profile", "planetary_age_at"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise_by_constructor_if_added"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    periods:      tuple[PlanetaryAgePeriod, ...]
    current:      PlanetaryAgePeriod | None = None
    queried_age:  float | None = None


# ---- Firdar ----

@dataclass(frozen=True, slots=True)
class FirdarSubPeriod:
    """
    RITE: One subordinate vessel within a major Firdar.

    THEOREM: FirdarSubPeriod stores one subdivided planetary segment inside a major Firdar period.

    RITE OF PURPOSE:
        This vessel makes the internal sevenfold subdivision of a major Firdar
        explicit and inspectable. It exists so callers can work with the admitted
        sub-period structure as public data rather than recomputing the Chaldean
        sequence and proportional durations from the enclosing major period.

    LAW OF OPERATION:
        Responsibilities:
            - Carry the sub-ruler and Julian Day bounds of one sub-period.
            - Carry the nominal duration in Julian years.
        Non-responsibilities:
            - Determining whether a major period is subdivided.
            - Computing the Chaldean order or proportional split on demand.
        Dependencies:
            - Built by `firdar_series()` from the Firdaria doctrine admitted by this Pillar.

    Canon: Abu Ma'shar; Guido Bonatti

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.cycles.FirdarSubPeriod",
      "risk": "low",
      "api": {
        "frozen": ["sub_ruler", "start_jd", "end_jd", "duration_years"],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["firdar_series"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise_by_constructor_if_added"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    sub_ruler:      str
    start_jd:       float
    end_jd:         float
    duration_years: float


@dataclass(frozen=True, slots=True)
class FirdarPeriod:
    """
    RITE: One major Firdar vessel in the seventy-five-year sequence.

    THEOREM: FirdarPeriod stores one major Firdar period, including its optional subordinate planetary divisions.

    RITE OF PURPOSE:
        This vessel makes one governing Firdar explicit: ruler, bounds, ordinal
        place in the sequence, and optional sub-periods. It exists so the full
        diurnal or nocturnal seventy-five-year order can be exposed as public
        structured data rather than being preserved only in sequence tables.

    LAW OF OPERATION:
        Responsibilities:
            - Carry one major ruler and its Julian Day bounds.
            - Carry the sequence ordinal and nominal duration.
            - Carry the subordinate sevenfold divisions when this authority admits them.
        Non-responsibilities:
            - Choosing the diurnal versus nocturnal sequence.
            - Computing sub-period durations from scratch once instantiated.
        Dependencies:
            - Built by `firdar_series()` from the Firdaria doctrine admitted by this Pillar.
            - Uses `FirdarSubPeriod` for subordinate divisions.

    Canon: Abu Ma'shar; Guido Bonatti

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.cycles.FirdarPeriod",
      "risk": "low",
      "api": {
        "frozen": ["ruler", "start_jd", "end_jd", "duration_years", "ordinal", "sub_periods"],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["firdar_series"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise_by_constructor_if_added"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    ruler:           str
    start_jd:        float
    end_jd:          float
    duration_years:  float
    ordinal:         int
    sub_periods:     tuple[FirdarSubPeriod, ...] | None


@dataclass(frozen=True, slots=True)
class FirdarSeries:
    """
    RITE: The full Firdaria sequence vessel.

    THEOREM: FirdarSeries stores the complete seventy-five-year Firdaria sequence for one nativity.

    RITE OF PURPOSE:
        This vessel preserves the entire major-period order of the nativity's
        Firdaria system in one public object. It exists so callers can inspect the
        full sequence, its birth context, and its total duration without carrying
        loose tuples or recomputing aggregate sequence truth.

    LAW OF OPERATION:
        Responsibilities:
            - Carry the birth Julian Day and day-chart classification used for the sequence.
            - Carry all major Firdar periods in order.
            - Carry the summed nominal duration of the series.
        Non-responsibilities:
            - Deriving the birth chart sect.
            - Locating the currently active period for a query instant.
        Dependencies:
            - Built by `firdar_series()` from `FirdarPeriod` vessels in this Pillar.

    Canon: Abu Ma'shar; Guido Bonatti

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.cycles.FirdarSeries",
      "risk": "low",
      "api": {
        "frozen": ["birth_jd", "is_day_birth", "periods", "total_years"],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["firdar_series"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise_by_constructor_if_added"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    birth_jd:     float
    is_day_birth: bool
    periods:      tuple[FirdarPeriod, ...]
    total_years:  float


# ---- Planetary Days and Hours ----

@dataclass(frozen=True, slots=True)
class PlanetaryDayInfo:
    """
    RITE: The planetary day witness.

    THEOREM: PlanetaryDayInfo stores the weekday identity and planetary ruler of one calendar day.

    RITE OF PURPOSE:
        This vessel exposes the admitted day-ruler doctrine as structured data.
        It exists so planetary-day computations can return the ruler, weekday
        name, and weekday number together instead of scattering those values
        across unrelated return positions.

    LAW OF OPERATION:
        Responsibilities:
            - Carry the day's planetary ruler.
            - Carry the weekday name and ISO weekday number.
        Non-responsibilities:
            - Computing sunrise or planetary hours.
            - Interpreting day rulership beyond the exposed weekday mapping.
        Dependencies:
            - Built by `planetary_day()` from weekday truth admitted by this Pillar.

    Canon: Vettius Valens; medieval planetary weekday doctrine

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.cycles.PlanetaryDayInfo",
      "risk": "low",
      "api": {
        "frozen": ["ruler", "weekday_name", "weekday_number"],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["planetary_day", "planetary_hours_profile"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise_by_constructor_if_added"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    ruler:          str
    weekday_name:   str
    weekday_number: int


@dataclass(frozen=True, slots=True)
class PlanetaryHour:
    """
    RITE: The planetary hour witness.

    THEOREM: PlanetaryHour stores one of the twenty-four unequal planetary hours of a civil day.

    RITE OF PURPOSE:
        This vessel makes each day or night hour explicit: ordinal, ruler, bounds,
        and diurnal classification. It exists so planetary-hour computations can
        return inspectable hour witnesses instead of forcing callers to reconstruct
        hour spans from bulk tables.

    LAW OF OPERATION:
        Responsibilities:
            - Carry the hour number, ruler, and Julian Day bounds.
            - Carry whether the hour belongs to the daytime or nighttime arc.
        Non-responsibilities:
            - Solving sunrise and sunset instants.
            - Choosing the day ruler independently of the surrounding profile.
        Dependencies:
            - Built by `planetary_hours_profile()` from sunrise and sunset truth.

    Canon: Vettius Valens; medieval planetary hours doctrine

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.cycles.PlanetaryHour",
      "risk": "low",
      "api": {
        "frozen": ["hour_number", "ruler", "start_jd", "end_jd", "is_day_hour"],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["planetary_hours_profile"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise_by_constructor_if_added"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    hour_number: int
    ruler:       str
    start_jd:    float
    end_jd:      float
    is_day_hour: bool


@dataclass(frozen=True, slots=True)
class PlanetaryHoursProfile:
    """
    RITE: The full planetary hours profile vessel.

    THEOREM: PlanetaryHoursProfile stores the day ruler, solar bounds, and twenty-four planetary hours for one date.

    RITE OF PURPOSE:
        This vessel exposes the full planetary-hours product as one structured
        result: day rulership, sunrise and sunset boundaries, all twenty-four
        unequal hours, and the daytime and nighttime hour lengths. It exists so
        callers can inspect the complete daily profile without recomputing spans
        or coordinating multiple helper returns.

    LAW OF OPERATION:
        Responsibilities:
            - Carry the planetary day witness and solar boundary Julian Days.
            - Carry all twenty-four planetary hour witnesses in order.
            - Carry the derived daytime and nighttime hour lengths.
        Non-responsibilities:
            - Solving solar altitude or sunrise/sunset events on its own.
            - Interpreting the hours beyond the exposed daily structure.
        Dependencies:
            - Built by `planetary_hours_profile()` from `PlanetaryDayInfo` and `PlanetaryHour` vessels.
            - Depends on sunrise, sunset, and next-sunrise truth admitted by this Pillar.

    Canon: Vettius Valens; medieval planetary hours doctrine

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.cycles.PlanetaryHoursProfile",
      "risk": "low",
      "api": {
        "frozen": [
          "day_info",
          "sunrise_jd",
          "sunset_jd",
          "next_sunrise_jd",
          "hours",
          "day_hour_length",
          "night_hour_length"
        ],
        "internal": []
      },
      "state": {"mutable": false, "owners": ["planetary_hours_profile"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise_by_constructor_if_added"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    day_info:          PlanetaryDayInfo
    sunrise_jd:        float
    sunset_jd:         float
    next_sunrise_jd:   float
    hours:             tuple[PlanetaryHour, ...]
    day_hour_length:   float
    night_hour_length: float


# ===========================================================================
# SECTION 3 — RETURN SERIES
# ===========================================================================

def return_series(
    body: str,
    natal_lon: float,
    jd_start: float,
    jd_end: float,
    reader: KernelReader | None = None,
) -> ReturnSeries:
    """
    Find all returns of *body* to *natal_lon* within a date range.

    Iterates forward from *jd_start*, calling the ephemeris solver for
    each successive return until *jd_end* is exceeded.

    Parameters
    ----------
    body       : body name constant (e.g. Body.SATURN)
    natal_lon  : natal ecliptic longitude to return to (degrees)
    jd_start   : search window start (JD UT)
    jd_end     : search window end (JD UT)
    reader     : optional SpkReader

    Returns
    -------
    ReturnSeries with all returns found.
    """
    from .transits import planet_return

    if reader is None:
        reader = get_reader()

    events: list[ReturnEvent] = []
    jd = jd_start
    n = 0

    # When planet_return fails (search window exhausted), advance by
    # a fraction of the search window to avoid skipping over any return.
    # planet_return's window is _RETURN_SEARCH_DAYS which is ~450 for Saturn.
    # We advance by half that, ensuring overlap so no return is missed.
    from .transits import _RETURN_SEARCH_DAYS
    _advance = _RETURN_SEARCH_DAYS.get(body, 400.0) * 0.5

    while jd < jd_end:
        try:
            jd_ret = planet_return(body, natal_lon, jd, reader=reader)
        except RuntimeError:
            # Search window exhausted without finding a return.
            # Advance by half the search window and retry.
            jd += _advance
            continue
        except Exception:
            break
        if jd_ret > jd_end:
            break
        n += 1
        events.append(ReturnEvent(
            body=body,
            return_number=n,
            jd_ut=jd_ret,
            longitude=natal_lon,
        ))
        # Advance past this return by a safe margin.
        jd = jd_ret + 5.0

    return ReturnSeries(
        body=body,
        natal_longitude=natal_lon,
        jd_start=jd_start,
        jd_end=jd_end,
        returns=tuple(events),
        count=len(events),
    )


def half_return_series(
    body: str,
    natal_lon: float,
    jd_start: float,
    jd_end: float,
    reader: KernelReader | None = None,
) -> ReturnSeries:
    """
    Find all half-returns (oppositions to natal longitude) within a date range.

    A half-return occurs when the body reaches natal_lon + 180°.

    Parameters
    ----------
    body       : body name constant
    natal_lon  : natal longitude (degrees)
    jd_start   : search window start (JD UT)
    jd_end     : search window end (JD UT)
    reader     : optional SpkReader

    Returns
    -------
    ReturnSeries with is_half=True on every event.
    """
    from .transits import planet_return

    if reader is None:
        reader = get_reader()

    opp_lon = (natal_lon + 180.0) % 360.0
    events: list[ReturnEvent] = []
    jd = jd_start
    n = 0

    from .transits import _RETURN_SEARCH_DAYS
    _advance = _RETURN_SEARCH_DAYS.get(body, 400.0) * 0.5

    while jd < jd_end:
        try:
            jd_ret = planet_return(body, opp_lon, jd, reader=reader)
        except RuntimeError:
            jd += _advance
            continue
        except Exception:
            break
        if jd_ret > jd_end:
            break
        n += 1
        events.append(ReturnEvent(
            body=body,
            return_number=n,
            jd_ut=jd_ret,
            longitude=natal_lon,
            is_half=True,
        ))
        jd = jd_ret + 5.0

    return ReturnSeries(
        body=body,
        natal_longitude=natal_lon,
        jd_start=jd_start,
        jd_end=jd_end,
        returns=tuple(events),
        count=len(events),
    )


def lifetime_returns(
    body: str,
    natal_lon: float,
    birth_jd: float,
    years: float = 90.0,
    reader: KernelReader | None = None,
) -> ReturnSeries:
    """
    Convenience wrapper: all returns of *body* over a human lifetime.

    Parameters
    ----------
    body       : body name constant
    natal_lon  : natal longitude (degrees)
    birth_jd   : birth Julian Day (UT)
    years      : lifespan to cover (default 90 years)
    reader     : optional SpkReader

    Returns
    -------
    ReturnSeries covering birth_jd to birth_jd + years.
    """
    jd_end = birth_jd + years * _JULIAN_YEAR
    return return_series(body, natal_lon, birth_jd, jd_end, reader=reader)


# ===========================================================================
# SECTION 4 — SYNODIC CYCLE ANALYSIS
# ===========================================================================

def synodic_cycle_position(
    body1: str,
    body2: str,
    jd_ut: float,
    reader: KernelReader | None = None,
) -> SynodicCyclePosition:
    """
    Evaluate where two bodies stand in their synodic cycle at a given moment.

    Parameters
    ----------
    body1, body2 : body names
    jd_ut        : moment of evaluation (JD UT)
    reader       : optional SpkReader

    Returns
    -------
    SynodicCyclePosition with phase angle, 8-fold phase, waxing flag,
    and the longitudes of both bodies.
    """
    from .planets import planet_at

    if reader is None:
        reader = get_reader()

    p1 = planet_at(body1, jd_ut, reader=reader, apparent=True)
    p2 = planet_at(body2, jd_ut, reader=reader, apparent=True)
    angle = (p2.longitude - p1.longitude) % 360.0
    phase = SynodicPhase.from_angle(angle)

    return SynodicCyclePosition(
        body1=body1,
        body2=body2,
        jd_ut=jd_ut,
        phase_angle=angle,
        phase=phase,
        is_waxing=(0.0 < angle < 180.0),
        lon1=p1.longitude,
        lon2=p2.longitude,
    )


# ===========================================================================
# SECTION 5 — GREAT CONJUNCTIONS (Jupiter–Saturn)
# ===========================================================================

# Sign-to-element mapping. Indices 0–11 map to Aries through Pisces.
_SIGN_ELEMENT: tuple[GreatMutationElement, ...] = (
    GreatMutationElement.FIRE,    # Aries
    GreatMutationElement.EARTH,   # Taurus
    GreatMutationElement.AIR,     # Gemini
    GreatMutationElement.WATER,   # Cancer
    GreatMutationElement.FIRE,    # Leo
    GreatMutationElement.EARTH,   # Virgo
    GreatMutationElement.AIR,     # Libra
    GreatMutationElement.WATER,   # Scorpio
    GreatMutationElement.FIRE,    # Sagittarius
    GreatMutationElement.EARTH,   # Capricorn
    GreatMutationElement.AIR,     # Aquarius
    GreatMutationElement.WATER,   # Pisces
)


def mutation_period_at(longitude: float) -> GreatMutationElement:
    """
    Return the elemental trigon for a given ecliptic longitude.

    This answers: "A great conjunction at this longitude falls in which
    elemental trigon?"
    """
    idx = int(longitude % 360.0 // 30.0)
    return _SIGN_ELEMENT[idx]


def great_conjunctions(
    jd_start: float,
    jd_end: float,
    reader: KernelReader | None = None,
) -> GreatConjunctionSeries:
    """
    Find all Jupiter–Saturn conjunctions in a date range.

    Each conjunction is classified by zodiac sign and elemental trigon.
    The ~20-year Jupiter–Saturn cycle is the foundation of mundane astrology's
    great conjunction doctrine (Abu Ma'shar, Kepler).

    Approximate periodicity:
        Synodic period     ~19.86 years
        Trigon shift       ~10 conjunctions (~200 years) per element
        Full mutation      ~4 elements × ~200 years = ~800 years

    Parameters
    ----------
    jd_start : search window start (JD UT)
    jd_end   : search window end (JD UT)
    reader   : optional SpkReader

    Returns
    -------
    GreatConjunctionSeries
    """
    from .phenomena import conjunctions_in_range as _conj_range

    if reader is None:
        reader = get_reader()

    raw = _conj_range(Body.JUPITER, Body.SATURN, jd_start, jd_end, reader=reader)

    conjs: list[GreatConjunction] = []
    seen_elements: list[GreatMutationElement] = []

    for ev in raw:
        sign_name, sign_sym, deg_in_sign = sign_of(ev.value)
        element = mutation_period_at(ev.value)

        conjs.append(GreatConjunction(
            jd_ut=ev.jd_ut,
            longitude=ev.value,
            sign=sign_name,
            sign_symbol=sign_sym,
            degree_in_sign=deg_in_sign,
            element=element,
        ))
        if element not in seen_elements:
            seen_elements.append(element)

    return GreatConjunctionSeries(
        jd_start=jd_start,
        jd_end=jd_end,
        conjunctions=tuple(conjs),
        count=len(conjs),
        elements_represented=tuple(seen_elements),
    )


# ===========================================================================
# SECTION 6 — PLANETARY AGES (Ptolemy, Tetrabiblos I.10)
# ===========================================================================
#
# Ptolemy assigns each planet governance over an age of life, following
# the Chaldean order from fastest (Moon) to slowest (Saturn):
#
#   Moon     0–4     infancy, nourishment, rapid physical change
#   Mercury  4–14    childhood, learning, speech, rational faculty
#   Venus   14–22    adolescence, desire, erotic impulse
#   Sun     22–41    prime of life, authority, ambition, action
#   Mars    41–56    maturity, severity, toil, the beginning of decline
#   Jupiter 56–68    elder years, withdrawal, dignity, philosophy
#   Saturn  68+      old age, cooling, lessening, contraction
#
# The boundaries are Ptolemy's; the interpretive tone is his.
# ===========================================================================

_PTOLEMAIC_AGES: tuple[tuple[PlanetaryAgeName, float, float | None, str], ...] = (
    (PlanetaryAgeName.MOON,    0.0,  4.0,  "Infancy: nourishment, rapid growth"),
    (PlanetaryAgeName.MERCURY, 4.0,  14.0, "Childhood: learning, reason, speech"),
    (PlanetaryAgeName.VENUS,   14.0, 22.0, "Adolescence: desire, beauty, erotic impulse"),
    (PlanetaryAgeName.SUN,     22.0, 41.0, "Prime: authority, ambition, mastery"),
    (PlanetaryAgeName.MARS,    41.0, 56.0, "Maturity: severity, toil, discontent"),
    (PlanetaryAgeName.JUPITER, 56.0, 68.0, "Elder years: retreat, dignity, foresight"),
    (PlanetaryAgeName.SATURN,  68.0, None, "Old age: cooling, contraction, decay"),
)


def _build_age_period(row: tuple[PlanetaryAgeName, float, float | None, str]) -> PlanetaryAgePeriod:
    return PlanetaryAgePeriod(ruler=row[0], start_age=row[1], end_age=row[2], label=row[3])


def planetary_age_at(age_years: float) -> PlanetaryAgePeriod:
    """
    Return the Ptolemaic planetary age period for a given age in years.

    Parameters
    ----------
    age_years : age in years (may be fractional)

    Returns
    -------
    PlanetaryAgePeriod for the applicable stage of life.

    Raises
    ------
    ValueError if age_years is non-finite (nan, inf).
    ValueError if age_years is negative.
    """
    if not math.isfinite(age_years):
        raise ValueError(f"age_years must be finite, got {age_years!r}")
    if age_years < 0:
        raise ValueError(f"age must be non-negative, got {age_years}")
    for row in _PTOLEMAIC_AGES:
        if row[2] is None or age_years < row[2]:
            return _build_age_period(row)
    # Should not reach here; Saturn is open-ended.
    return _build_age_period(_PTOLEMAIC_AGES[-1])


def planetary_age_profile(age_years: float | None = None) -> PlanetaryAgeProfile:
    """
    Return the complete seven-age model.

    Parameters
    ----------
    age_years : optional age to identify the current period.

    Returns
    -------
    PlanetaryAgeProfile with all 7 periods and optionally the current one.
    """
    periods = tuple(_build_age_period(row) for row in _PTOLEMAIC_AGES)
    current = planetary_age_at(age_years) if age_years is not None else None
    return PlanetaryAgeProfile(
        periods=periods,
        current=current,
        queried_age=age_years,
    )


# ===========================================================================
# SECTION 7 — FIRDAR (Abu Ma'shar, Bonatti)
# ===========================================================================
#
# The firdar (firdāriyyāt, from Greek periodos) divides a 75-year life
# cycle into 9 major periods, each ruled by a planet or node.
#
# Two sequences exist — one for day births, one for night births —
# differing only in the planetary starting ruler.  The final two
# periods (North Node, South Node) are shared.
#
# Each planetary firdar (the first 7) is subdivided into 7 sub-periods,
# each ruled by one of the 7 classical planets in Chaldean order,
# beginning from the major ruler.  The nodal firdars (last 2) are
# traditionally left undivided by most authorities.
# ===========================================================================

# (ruler_name, duration_in_years)
_FIRDAR_DIURNAL: tuple[tuple[str, float], ...] = (
    (Body.SUN,     10.0),
    (Body.VENUS,    8.0),
    (Body.MERCURY, 13.0),
    (Body.MOON,     9.0),
    (Body.SATURN,  11.0),
    (Body.JUPITER, 12.0),
    (Body.MARS,     7.0),
    ("North Node",  3.0),
    ("South Node",  2.0),
)

_FIRDAR_NOCTURNAL: tuple[tuple[str, float], ...] = (
    (Body.MOON,     9.0),
    (Body.SATURN,  11.0),
    (Body.JUPITER, 12.0),
    (Body.MARS,     7.0),
    (Body.SUN,     10.0),
    (Body.VENUS,    8.0),
    (Body.MERCURY, 13.0),
    ("North Node",  3.0),
    ("South Node",  2.0),
)

_NODE_RULERS = frozenset({"North Node", "South Node"})


def _firdar_sub_periods(
    ruler: str,
    start_jd: float,
    duration_years: float,
) -> tuple[FirdarSubPeriod, ...]:
    """
    Generate the 7 sub-periods for a planetary firdar.

    Each sub-period is proportional: duration = major_duration / 7.
    Sub-rulers follow the Chaldean order starting from the major ruler.
    """
    sub_dur_years = duration_years / 7.0
    sub_dur_days = sub_dur_years * _JULIAN_YEAR

    # Find starting index in the Chaldean order.
    start_idx = _CHALDEAN_INDEX.get(ruler, 0)

    subs: list[FirdarSubPeriod] = []
    jd = start_jd
    for i in range(7):
        sub_ruler = CHALDEAN_ORDER[(start_idx + i) % 7]
        subs.append(FirdarSubPeriod(
            sub_ruler=sub_ruler,
            start_jd=jd,
            end_jd=jd + sub_dur_days,
            duration_years=sub_dur_years,
        ))
        jd += sub_dur_days

    return tuple(subs)


def firdar_series(birth_jd: float, is_day_birth: bool) -> FirdarSeries:
    """
    Compute the complete 75-year firdar sequence for a nativity.

    Parameters
    ----------
    birth_jd     : birth Julian Day (UT)
    is_day_birth : True for diurnal chart, False for nocturnal

    Returns
    -------
    FirdarSeries with all 9 major periods and their sub-periods.
    """
    sequence = _FIRDAR_DIURNAL if is_day_birth else _FIRDAR_NOCTURNAL
    periods: list[FirdarPeriod] = []
    jd = birth_jd
    total = 0.0

    for ordinal, (ruler, dur_years) in enumerate(sequence, start=1):
        dur_days = dur_years * _JULIAN_YEAR
        is_node = ruler in _NODE_RULERS

        subs = None if is_node else _firdar_sub_periods(ruler, jd, dur_years)

        periods.append(FirdarPeriod(
            ruler=ruler,
            start_jd=jd,
            end_jd=jd + dur_days,
            duration_years=dur_years,
            ordinal=ordinal,
            sub_periods=subs,
        ))
        jd += dur_days
        total += dur_years

    return FirdarSeries(
        birth_jd=birth_jd,
        is_day_birth=is_day_birth,
        periods=tuple(periods),
        total_years=total,
    )


def firdar_at(
    birth_jd: float,
    target_jd: float,
    is_day_birth: bool,
) -> FirdarPeriod:
    """
    Find the active firdar at a specific moment.

    Parameters
    ----------
    birth_jd     : birth Julian Day (UT)
    target_jd    : moment to query (JD UT)
    is_day_birth : True for diurnal chart

    Returns
    -------
    The FirdarPeriod active at target_jd.

    Raises
    ------
    ValueError if target_jd is before birth or beyond the 75-year cycle.
    """
    if target_jd < birth_jd:
        raise ValueError(
            f"firdar_at: target_jd ({target_jd}) precedes birth_jd ({birth_jd})"
        )

    series = firdar_series(birth_jd, is_day_birth)
    for period in series.periods:
        if period.start_jd <= target_jd < period.end_jd:
            return period

    raise ValueError(
        f"target_jd {target_jd} is beyond the 75-year firdar cycle "
        f"(ends at {series.periods[-1].end_jd})"
    )


# ===========================================================================
# SECTION 8 — PLANETARY DAYS AND HOURS
# ===========================================================================
#
# The planetary weekday scheme assigns each day to a planet based on the
# Chaldean order.  The first "hour" of each day (starting at sunrise) is
# ruled by that day's planet; subsequent hours follow the Chaldean sequence.
#
# Day/night are divided into 12 temporal hours each (unequal hours that
# vary by season and latitude).
#
# Day-ruler table:
#   Monday     Moon        Friday     Venus
#   Tuesday    Mars        Saturday   Saturn
#   Wednesday  Mercury     Sunday     Sun
#   Thursday   Jupiter
#
# The system is self-consistent: the 25th hour (= first hour of the
# next day) falls on the next day's ruler in the Chaldean sequence.
# ===========================================================================

_WEEKDAY_NAMES: tuple[str, ...] = (
    "Monday", "Tuesday", "Wednesday", "Thursday",
    "Friday", "Saturday", "Sunday",
)

# Maps ISO weekday index (0=Mon … 6=Sun) to the day ruler.
_DAY_RULERS: tuple[str, ...] = (
    Body.MOON,     # Monday
    Body.MARS,     # Tuesday
    Body.MERCURY,  # Wednesday
    Body.JUPITER,  # Thursday
    Body.VENUS,    # Friday
    Body.SATURN,   # Saturday
    Body.SUN,      # Sunday
)


def _jd_to_weekday(jd: float) -> int:
    """
    Return the ISO weekday index (0 = Monday, 6 = Sunday) for a Julian Day.

    The Julian Day count starts at noon; JD 0.0 = Monday noon,
    January 1, 4713 BC (proleptic Julian).
    """
    return int(jd + 0.5) % 7


def planetary_day_ruler(jd: float) -> PlanetaryDayInfo:
    """
    Return the planetary day ruler for a given Julian Day.

    The "astrological day" begins at sunrise, but for this function we use
    the calendar day (midnight to midnight ≈ noon JD convention) since
    sunrise requires geographic coordinates.  For sunrise-accurate day rulers,
    compare jd to the sunrise_jd of the location.

    Parameters
    ----------
    jd : Julian Day (UT)

    Returns
    -------
    PlanetaryDayInfo with ruler, weekday name, and ISO weekday number.
    """
    wd = _jd_to_weekday(jd)
    return PlanetaryDayInfo(
        ruler=_DAY_RULERS[wd],
        weekday_name=_WEEKDAY_NAMES[wd],
        weekday_number=wd + 1,  # ISO 1–7
    )


def planetary_hours_for_day(
    sunrise_jd: float,
    sunset_jd: float,
    next_sunrise_jd: float | None = None,
) -> PlanetaryHoursProfile:
    """
    Compute the 24 planetary hours for a single day.

    The astrological day begins at sunrise.  Daytime (sunrise → sunset) is
    divided into 12 equal temporal hours; nighttime (sunset → next sunrise)
    into another 12.  Each hour is ruled by a planet following the Chaldean
    sequence from the day ruler.

    Parameters
    ----------
    sunrise_jd      : Julian Day of sunrise
    sunset_jd       : Julian Day of sunset
    next_sunrise_jd : Julian Day of next sunrise.  If None, estimated as
                      sunrise_jd + 1.0 (approximate).

    Returns
    -------
    PlanetaryHoursProfile with all 24 hours and their rulers.

    Raises
    ------
    ValueError if sunset_jd <= sunrise_jd.
    ValueError if next_sunrise_jd <= sunset_jd.
    """
    if next_sunrise_jd is None:
        next_sunrise_jd = sunrise_jd + 1.0

    if sunset_jd <= sunrise_jd:
        raise ValueError(
            f"planetary_hours_for_day: sunset_jd ({sunset_jd}) must be after "
            f"sunrise_jd ({sunrise_jd})"
        )
    if next_sunrise_jd <= sunset_jd:
        raise ValueError(
            f"planetary_hours_for_day: next_sunrise_jd ({next_sunrise_jd}) must be "
            f"after sunset_jd ({sunset_jd})"
        )

    day_length = sunset_jd - sunrise_jd
    night_length = next_sunrise_jd - sunset_jd
    day_hour = day_length / 12.0
    night_hour = night_length / 12.0

    # The day ruler is determined by the weekday at sunrise.
    day_info = planetary_day_ruler(sunrise_jd)
    start_chaldean_idx = _CHALDEAN_INDEX[day_info.ruler]

    hours: list[PlanetaryHour] = []

    for h in range(24):
        ruler = CHALDEAN_ORDER[(start_chaldean_idx + h) % 7]
        if h < 12:
            # Day hours
            h_start = sunrise_jd + h * day_hour
            h_end = sunrise_jd + (h + 1) * day_hour
            is_day = True
        else:
            # Night hours
            n = h - 12
            h_start = sunset_jd + n * night_hour
            h_end = sunset_jd + (n + 1) * night_hour
            is_day = False

        hours.append(PlanetaryHour(
            hour_number=h + 1,
            ruler=ruler,
            start_jd=h_start,
            end_jd=h_end,
            is_day_hour=is_day,
        ))

    return PlanetaryHoursProfile(
        day_info=day_info,
        sunrise_jd=sunrise_jd,
        sunset_jd=sunset_jd,
        next_sunrise_jd=next_sunrise_jd,
        hours=tuple(hours),
        day_hour_length=day_hour,
        night_hour_length=night_hour,
    )
