"""
Moira - varshaphal.py
Tajika / Varshaphal doctrine layer above the sidereal solar-return substrate.

Boundary: owns Muntha progression, Saham computation, and the structured
Varshaphal annual-chart vessel. Delegates solar-return timing to
moira.transits.varshaphal(), chart assembly to moira.chart/create_chart,
sidereal conversion to moira.sidereal, and house membership to moira.houses.

Doctrinal basis used here:
    - Muntha: progressed Ascendant advanced one sign per completed year, with
      the natal Ascendant degree preserved.
    - Sahams: formulae summarized from B.V. Raman's Varshaphala exposition via
      verified secondary technical summaries. The layer preserves the 30-degree
      correction rule and the default day/night operand reversal doctrine.

This module implements the first Tajika aspect and yoga layer, a primary-
source panchavargi strength scaffold, an initial annual judgement vessel, and
the Gauri mudda dasha schedule from the natal lunar asterism.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from .aspects import AspectData, aspects_between, aspects_to_point
from .chart import ChartContext, create_chart
from .constants import Body, HouseSystem, SIGNS, sign_of
from .coordinates import angular_distance
from .houses import HouseCusps, HousePolicy, house_of, calculate_houses
from .julian import calendar_datetime_from_jd
from .profections import DOMICILE_RULERS
from .planets import all_planets_at
from .rise_set import twilight_times
from .shadbala import MEAN_DAILY_MOTION, NAISARGIKA_BALA
from .sidereal import Ayanamsa, UserDefinedAyanamsa, ayanamsa, nakshatra_of, tropical_to_sidereal
from .spk_reader import SpkReader
from .transits import TransitComputationPolicy, varshaphal as _varshaphal_jd, varshaphal_chart as _varshaphal_chart
from .varga import navamsa
from .vedic_dignities import (
    EXALTATION_SIGN,
    VedicDignityRank,
    DignityConditionProfile as VedicDignityConditionProfile,
    VedicDignityResult,
    DignityTier,
    dignity_condition_profile as vedic_dignity_condition_profile,
    vedic_dignity,
)

__all__ = [
    "VarshaphalSahamDefinition",
    "VarshaphalSaham",
    "TajikaPanchavargiStrength",
    "TajikaKalaBala",
    "TajikaChestaBala",
    "TajikaDrigBala",
    "TajikaShadbalaProfile",
    "VarshaphalActorJudgement",
    "VarshaphalSahamJudgement",
    "VarshaphalSahamPriority",
    "VarsheshaCandidate",
    "VarsheshaResult",
    "VarshaphalJudgementProfile",
    "VarshaphalYearJudgement",
    "VarshaphalTopicJudgement",
    "TajikaAspectPolicy",
    "TajikaAspect",
    "TajikaYoga",
    "MunthaConditionProfile",
    "MuddaDashaPeriod",
    "MuddaDasha",
    "MuddaDashaActivation",
    "TasiraPeriod",
    "TasiraDasha",
    "MuddaPeriodJudgement",
    "MuddaPeriodResultProfile",
    "VarshaphalChart",
    "VarshaphalTopicWindow",
    "VarshaphalYearSummary",
    "muntha",
    "mudda_dasha",
    "active_mudda_dasha",
    "tasira_periods",
    "active_tasira_period",
    "mudda_period_judgement",
    "tajika_panchavargi_strength",
    "tajika_shadbala_profile",
    "tajika_aspects",
    "tajika_yogas",
    "varshesha",
    "varshaphal_judgement_profile",
    "varshaphal_year_judgement",
    "varshaphal_topic_judgements",
    "varshaphal_topic_windows",
    "varshaphal_year_summary",
    "muntha_condition_profile",
    "varshaphal_sahams",
    "build_varshaphal_chart",
]


@dataclass(frozen=True, slots=True)
class VarshaphalSahamDefinition:
    """Definition of one Tajika Saham formula."""

    name: str
    minuend: str
    subtrahend: str
    addend: str
    reverse_at_night: bool = True


@dataclass(frozen=True, slots=True)
class VarshaphalSaham:
    """Computed Saham with audit-friendly formula metadata."""

    name: str
    longitude: float
    house: int
    ruler: str
    minuend: str
    subtrahend: str
    addend: str
    reversed_for_night: bool
    correction_applied: bool


@dataclass(frozen=True, slots=True)
class TajikaPanchavargiStrength:
    """Primary-source Tajika five-dignity strength on the 20-point scale."""

    planet: str
    longitude: float
    sign: str
    domicile_lord: str
    domicile_relationship: str
    domicile_score: float
    exaltation_basis_planet: str | None
    exaltation_relationship: str
    exaltation_score: float
    hadda_lord: str
    hadda_relationship: str
    hadda_score: float
    decan_lord: str
    decan_relationship: str
    decan_score: float
    musallaha_lord: str
    musallaha_relationship: str
    musallaha_score: float
    total_score: float
    category: str


@dataclass(frozen=True, slots=True)
class TajikaKalaBala:
    """Primary-source Tajika temporal strength breakdown."""

    planet: str
    sect_strength: float
    luminary_elongation_strength: float
    venus_elongation_strength: float
    night_watch_strength: float
    total_score: float


@dataclass(frozen=True, slots=True)
class TajikaChestaBala:
    """Primary-source Tajika motion strength breakdown."""

    planet: str
    motion_mode_strength: float
    benefic_contact_strength: float
    solar_synodic_strength: float
    blocked_by_malefic_contact: bool
    total_score: float


@dataclass(frozen=True, slots=True)
class TajikaDrigBala:
    """Primary-source Tajika aspect strength breakdown."""

    planet: str
    ascendant_aspect_strength: float
    benefic_support_strength: float
    blocked_by_malefic_square: bool
    total_score: float


@dataclass(frozen=True, slots=True)
class TajikaShadbalaProfile:
    """Primary-source Tajika sixfold strength profile for one annual planet."""

    planet: str
    panchavargi_strength: TajikaPanchavargiStrength
    directional_strength: float
    temporal_strength: TajikaKalaBala
    natural_strength: float
    motion_strength: TajikaChestaBala
    aspect_strength: TajikaDrigBala
    total_score: float


@dataclass(frozen=True, slots=True)
class VarshaphalActorJudgement:
    """Ranked annual testimony for one governing actor in the return chart."""

    actor: str
    planet: str
    house: int
    supportive_yoga_count: int
    obstructive_yoga_count: int
    panchavargi_strength: TajikaPanchavargiStrength
    shadbala: TajikaShadbalaProfile
    authority_score: float
    authority: str


@dataclass(frozen=True, slots=True)
class VarshaphalSahamJudgement:
    """Ranked annual testimony for one Saham through its place and ruler."""

    saham_name: str
    house: int
    ruler: str
    ruler_house: int
    ruler_strength: TajikaShadbalaProfile
    relevance_score: float
    authority: str


@dataclass(frozen=True, slots=True)
class VarshaphalSahamPriority:
    """Source-owned gate for whether a Saham should weigh in the annual verdict."""

    saham_name: str
    annual_judgement: VarshaphalSahamJudgement
    natal_judgement: VarshaphalSahamJudgement
    priority: str
    is_considered: bool
    doctrine: str


@dataclass(frozen=True, slots=True)
class TajikaAspectPolicy:
    """
    Policy surface for Tajika annual aspect admission.

    ``classical_12_degree`` follows the common 12-degree effectiveness rule
    preserved in Hayanaratna. ``deeptamsa_half_sum`` uses the half-sum of the
    two planets' Deeptamsa values as the pair orb.
    """

    orb_mode: str = "classical_12_degree"
    include_conjunctions: bool = True


@dataclass(frozen=True, slots=True)
class TajikaAspect:
    """Structured Tajika annual aspect built from one admitted zodiacal aspect."""

    body1: str
    body2: str
    aspect: AspectData
    relation: str
    relation_strength: float
    effect: str
    is_benefic_relation: bool
    perfects_in_future: bool | None
    within_effective_orb: bool


@dataclass(frozen=True, slots=True)
class TajikaYoga:
    """Structured Tajika yoga result over an admitted annual aspect."""

    name: str
    body1: str
    body2: str
    aspect: TajikaAspect | None
    favorable: bool
    doctrine: str
    mediator: str | None = None
    supporting_aspects: tuple[TajikaAspect, ...] = ()


@dataclass(frozen=True, slots=True)
class VarsheshaCandidate:
    """One primary-source candidate for rulership of the year."""

    planet: str
    roles: tuple[str, ...]
    role_count: int
    longitude: float
    aspects_year_asc: bool
    asc_aspect: AspectData | None
    panchavargi_strength: TajikaPanchavargiStrength


@dataclass(frozen=True, slots=True)
class VarsheshaResult:
    """Result vessel for the selected ruler of the year."""

    planet: str
    roles: tuple[str, ...]
    selection_basis: str
    candidates: tuple[VarsheshaCandidate, ...]
    asc_aspect: AspectData | None
    triplicity_contenders: tuple[str, str]


@dataclass(frozen=True, slots=True)
class VarshaphalJudgementProfile:
    """First annual judgement scaffold built around the ruler of the year."""

    varshesha: VarsheshaResult
    supportive_yogas: tuple[str, ...]
    obstructive_yogas: tuple[str, ...]
    varshesha_house: int
    varshesha_dignity: VedicDignityResult
    varshesha_strength: TajikaPanchavargiStrength
    varshesha_shadbala: TajikaShadbalaProfile
    muntha_lord_shadbala: TajikaShadbalaProfile
    year_lagna_lord: str
    year_lagna_lord_strong: bool
    actor_rankings: tuple[VarshaphalActorJudgement, ...]
    key_saham_rankings: tuple[VarshaphalSahamJudgement, ...]
    mudda_period: "MuddaPeriodJudgement | None"
    strongest_testimonies: tuple[str, ...]
    yearly_strength_balance: str
    ascendant_authority_indication: str


@dataclass(frozen=True, slots=True)
class VarshaphalYearJudgement:
    """Consolidated annual verdict surface over the Varshaphal doctrine layers."""

    profile: VarshaphalJudgementProfile
    dominant_governor: VarshaphalActorJudgement | None
    supporting_governors: tuple[VarshaphalActorJudgement, ...]
    strained_governors: tuple[VarshaphalActorJudgement, ...]
    topics: tuple["VarshaphalTopicJudgement", ...]
    foreground_topics: tuple["VarshaphalTopicJudgement", ...]
    obstructed_topics: tuple["VarshaphalTopicJudgement", ...]
    background_topics: tuple["VarshaphalTopicJudgement", ...]
    prioritized_sahams: tuple[VarshaphalSahamPriority, ...]
    disregarded_sahams: tuple[VarshaphalSahamPriority, ...]
    key_sahams: tuple[VarshaphalSahamJudgement, ...]
    timed_period: "MuddaPeriodJudgement | None"
    supportive_yogas: tuple[str, ...]
    obstructive_yogas: tuple[str, ...]
    decisive_testimonies: tuple[str, ...]
    final_verdict: str
    conflict_resolution: str
    verdict_basis: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class VarshaphalTopicJudgement:
    """Named annual result channel built from source-owned Sahama and house testimonies."""

    topic: str
    saham_name: str
    polarity: str
    saham_priority: VarshaphalSahamPriority | None
    house_numbers: tuple[int, ...]
    house_rulers: tuple[str, ...]
    supportive_relation_to_varshesha: bool
    obstructive_relation_to_varshesha: bool
    timed_activation: str
    emphasis_score: float
    judgement: str
    basis: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class VarshaphalTopicWindow:
    """Timed activation window for one annual topic within the Mudda or Tāsīra sequence."""

    topic: str
    start_jd: float
    end_jd: float
    source: str
    major_lord: str
    sub_lord: str
    activation_kind: str
    basis: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class VarshaphalYearSummary:
    """Structured summary/report surface for a Varshaphal year."""

    yearly_tone: str
    dominant_governor: str | None
    foreground_topics: tuple[str, ...]
    obstructed_topics: tuple[str, ...]
    background_topics: tuple[str, ...]
    timed_highlights: tuple[str, ...]
    strongest_testimonies: tuple[str, ...]
    narrative_basis: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class MunthaConditionProfile:
    """Structural annual-chart condition profile for Muntha and its lord."""

    muntha_longitude: float
    muntha_house: int
    muntha_sign: str
    muntha_lord: str
    muntha_lord_longitude: float
    muntha_lord_house: int
    muntha_lord_sign: str
    muntha_lord_dignity: VedicDignityResult
    muntha_lord_dignity_profile: VedicDignityConditionProfile
    muntha_lord_house_from_muntha: int
    lord_in_kendra: bool
    lord_in_trikona: bool
    lord_in_dusthana: bool
    lord_in_upachaya: bool
    lord_is_strong: bool
    lord_is_weak: bool


@dataclass(frozen=True, slots=True)
class MuddaDashaPeriod:
    """One mudda dasha period with nominal 360-day and mapped JD bounds."""

    level: int
    lord: str
    start_day: float
    end_day: float
    duration_days: float
    start_jd: float
    end_jd: float
    source_fraction: str
    sub: tuple["MuddaDashaPeriod", ...] = ()


@dataclass(frozen=True, slots=True)
class MuddaDasha:
    """Structured annual Gauri mudda schedule with nested antardashas."""

    school: str
    natal_nakshatra: str
    natal_nakshatra_index: int
    natal_nakshatra_lord: str
    birth_elapsed_ghatis: float
    birth_remaining_ghatis: float
    year_ruler: str
    year_start_jd: float
    year_end_jd: float
    periods: tuple[MuddaDashaPeriod, ...]


@dataclass(frozen=True, slots=True)
class MuddaDashaActivation:
    """Active mudda major and subperiod for one JD within the annual year."""

    jd_ut: float
    major_period: MuddaDashaPeriod
    sub_period: MuddaDashaPeriod


@dataclass(frozen=True, slots=True)
class TasiraPeriod:
    """One annual planetary Tāsīra period derived from aspect to the ascendant."""

    lord: str
    aspect_angle: float
    aspect_points: float
    nominal_days: float
    start_day: float
    end_day: float
    start_jd: float
    end_jd: float


@dataclass(frozen=True, slots=True)
class TasiraDasha:
    """Structured annual planetary Tāsīra sequence for one Varshaphal year."""

    year_start_jd: float
    year_end_jd: float
    periods: tuple[TasiraPeriod, ...]


@dataclass(frozen=True, slots=True)
class MuddaPeriodJudgement:
    """Timed annual testimony for the active mudda major and subperiod."""

    activation: MuddaDashaActivation
    major_house: int | None
    sub_house: int | None
    major_actor_judgement: VarshaphalActorJudgement | None
    sub_actor_judgement: VarshaphalActorJudgement | None
    major_supportive_yoga_count: int
    major_obstructive_yoga_count: int
    sub_supportive_yoga_count: int
    sub_obstructive_yoga_count: int
    major_authority: str | None
    sub_authority: str | None
    major_result: "MuddaPeriodResultProfile"
    sub_result: "MuddaPeriodResultProfile"


@dataclass(frozen=True, slots=True)
class MuddaPeriodResultProfile:
    """Primary-source period-result classification for one operative mudda lord."""

    period_lord: str
    governing_year_lord: str
    relation_to_varshesha: str
    relation_to_year_lagna_lord: str
    strength_quality: str
    manifestation: str
    result_fullness: str
    doctrine: str


@dataclass(frozen=True, slots=True)
class VarshaphalChart:
    """Structured annual return doctrine vessel for Tajika / Varshaphal work."""

    birth_jd: float
    return_year: int
    years_elapsed: int
    jd_ut: float
    ayanamsa_system: str | UserDefinedAyanamsa
    chart: ChartContext
    natal_chart: ChartContext
    sidereal_houses: HouseCusps
    sidereal_planets: dict[str, float]
    natal_sidereal_houses: HouseCusps
    natal_sidereal_planets: dict[str, float]
    natal_sidereal_asc: float
    muntha_longitude: float
    muntha_house: int
    muntha_lord: str
    muntha_profile: MunthaConditionProfile
    varshesha: VarsheshaResult
    judgement: VarshaphalJudgementProfile | None
    year_judgement: VarshaphalYearJudgement | None
    tajika_aspects: tuple[TajikaAspect, ...]
    tajika_yogas: tuple[TajikaYoga, ...]
    sahams: tuple[VarshaphalSaham, ...]
    natal_sahams: tuple[VarshaphalSaham, ...]
    mudda_dasha: MuddaDasha
    tasira_dasha: TasiraDasha

    def __post_init__(self) -> None:
        object.__setattr__(self, "sidereal_planets", MappingProxyType(dict(self.sidereal_planets)))
        object.__setattr__(self, "natal_sidereal_planets", MappingProxyType(dict(self.natal_sidereal_planets)))

    @property
    def muntha_sign(self) -> str:
        """Return the sidereal sign occupied by Muntha."""

        return sign_of(self.muntha_longitude)[0]

    def saham(self, name: str) -> VarshaphalSaham:
        """Return one Saham by name."""

        for saham in self.sahams:
            if saham.name == name:
                return saham
        raise KeyError(f"Unknown Varshaphal Saham: {name}")


_SAHAM_DEFINITIONS: tuple[VarshaphalSahamDefinition, ...] = (
    VarshaphalSahamDefinition("Punya", "Moon", "Sun", "Asc"),
    VarshaphalSahamDefinition("Vidya", "Sun", "Moon", "Asc"),
    VarshaphalSahamDefinition("Yasa", "Jupiter", "Punya", "Asc"),
    VarshaphalSahamDefinition("Mitra", "Jupiter", "Punya", "Venus"),
    VarshaphalSahamDefinition("Mahatmya", "Punya", "Mars", "Asc"),
    VarshaphalSahamDefinition("Asha", "Saturn", "Mars", "Asc"),
    VarshaphalSahamDefinition("Samartha", "Mars", "Asc Lord", "Asc"),
    VarshaphalSahamDefinition("Bhratru", "Jupiter", "Saturn", "Asc", reverse_at_night=False),
    VarshaphalSahamDefinition("Gaurava", "Jupiter", "Moon", "Sun"),
    VarshaphalSahamDefinition("Pitru", "Saturn", "Sun", "Asc"),
    VarshaphalSahamDefinition("Raja", "Saturn", "Sun", "Asc"),
    VarshaphalSahamDefinition("Matru", "Moon", "Venus", "Asc"),
    VarshaphalSahamDefinition("Putra", "Jupiter", "Moon", "Asc"),
    VarshaphalSahamDefinition("Jeeva", "Saturn", "Jupiter", "Asc"),
    VarshaphalSahamDefinition("Karma", "Mars", "Mercury", "Asc"),
    VarshaphalSahamDefinition("Roga", "Asc", "Moon", "Asc"),
    VarshaphalSahamDefinition("Kali", "Jupiter", "Mars", "Asc"),
    VarshaphalSahamDefinition("Sastra", "Jupiter", "Saturn", "Mercury"),
    VarshaphalSahamDefinition("Bandhu", "Mercury", "Moon", "Asc"),
    VarshaphalSahamDefinition("Mrityu", "8th House Cusp", "Moon", "Asc"),
    VarshaphalSahamDefinition("Paradesa", "9th House Cusp", "9th Lord", "Asc"),
    VarshaphalSahamDefinition("Artha", "2nd House Cusp", "2nd Lord", "Asc"),
    VarshaphalSahamDefinition("Paradara", "Venus", "Sun", "Asc"),
    VarshaphalSahamDefinition("Vanik", "Moon", "Mercury", "Asc"),
    VarshaphalSahamDefinition("Karyasiddhi", "Saturn", "Sun", "Sun-sign Lord"),
    VarshaphalSahamDefinition("Vivaha", "Venus", "Saturn", "Asc"),
    VarshaphalSahamDefinition("Santapa", "Saturn", "Moon", "6th House Cusp"),
    VarshaphalSahamDefinition("Sraddha", "Venus", "Mars", "Asc"),
    VarshaphalSahamDefinition("Preeti", "Sastra", "Punya", "Asc"),
    VarshaphalSahamDefinition("Jadya", "Mars", "Saturn", "Mercury"),
    VarshaphalSahamDefinition("Vyapara", "Mars", "Saturn", "Asc", reverse_at_night=False),
    VarshaphalSahamDefinition("Satru", "Mars", "Saturn", "Asc"),
    VarshaphalSahamDefinition("Jalapathana", "15 Cancer", "Saturn", "Asc"),
    VarshaphalSahamDefinition("Bandhana", "Punya", "Saturn", "Asc"),
    VarshaphalSahamDefinition("Apamrityu", "8th House Cusp", "Mars", "Asc"),
)

_TAJIKA_DEEPTAMSA: dict[str, float] = {
    "Sun": 15.0,
    "Moon": 12.0,
    "Mars": 8.0,
    "Mercury": 7.0,
    "Jupiter": 9.0,
    "Venus": 7.0,
    "Saturn": 9.0,
}

_MUDDA_LORD_SEQUENCE: tuple[str, ...] = (
    "Sun",
    "Moon",
    "Mars",
    "Rahu",
    "Jupiter",
    "Saturn",
    "Mercury",
    "Ketu",
    "Venus",
)

_MUDDA_PERIOD_DAYS: dict[str, float] = {
    "Sun": 18.0,
    "Moon": 30.0,
    "Mars": 21.0,
    "Rahu": 54.0,
    "Jupiter": 48.0,
    "Saturn": 57.0,
    "Mercury": 51.0,
    "Ketu": 21.0,
    "Venus": 60.0,
}

_MUDDA_SUBPERIOD_MULTIPLIERS: dict[str, float] = {
    "Sun": 4.0,
    "Moon": 8.0,
    "Mars": 5.0,
    "Rahu": 7.0,
    "Jupiter": 10.0,
    "Saturn": 6.0,
    "Mercury": 9.0,
    "Ketu": 5.0,
    "Venus": 6.0,
}

_MUDDA_GAURI_START_NAKSHATRA_INDEX = 2  # Krittika from Ashvini-zero indexing

_VARSHA_TOPIC_MAP: dict[str, tuple[str, tuple[int, ...], str]] = {
    "wealth": ("Artha", (2, 11), "constructive"),
    "marriage": ("Vivaha", (7,), "constructive"),
    "illness": ("Roga", (6, 8), "adverse"),
    "children": ("Putra", (5,), "constructive"),
    "career": ("Karyasiddhi", (10, 11), "constructive"),
    "travel": ("Paradesa", (9, 12), "mixed"),
    "authority": ("Raja", (10, 11), "constructive"),
}

_TAJIKA_RELATIONS: dict[float, tuple[str, float, str, bool]] = {
    0.0: ("same_sign", 1.0, "same-sign conjunction", False),
    60.0: ("secret_friend", 0.25, "perfects the matter sought quietly", True),
    90.0: ("secret_enemy", 0.5, "obstructs the matter with hidden enmity", False),
    120.0: ("open_friend", 0.75, "openly supports and unites the matter", True),
    180.0: ("open_enemy", 1.0, "openly opposes the matter", False),
}

_TAJIKA_MAJORS: tuple[float, ...] = (0.0, 60.0, 90.0, 120.0, 180.0)
_TAJIKA_SPEED_ORDER: dict[str, int] = {
    "Moon": 0,
    "Mercury": 1,
    "Venus": 2,
    "Sun": 3,
    "Mars": 4,
    "Jupiter": 5,
    "Saturn": 6,
}
_TAJIKA_BRIDGING_SLOW_PLANETS: frozenset[str] = frozenset({"Jupiter", "Saturn"})
_NATURAL_STRENGTH_RANK: dict[str, int] = {
    "Saturn": 1,
    "Mars": 2,
    "Mercury": 3,
    "Jupiter": 4,
    "Venus": 5,
    "Moon": 6,
    "Sun": 7,
}
_TAJIKA_FRIENDSHIP_FRACTIONS: dict[str, float] = {
    "own": 1.0,
    "great_friend": 0.75,
    "friend": 0.5,
    "neutral": 0.25,
    "enemy": 0.125,
    "great_enemy": 0.0625,
}
_TAJIKA_PANCHAVARGI_MAXIMA: dict[str, float] = {
    "domicile": 30.0,
    "exaltation": 20.0,
    "hadda": 15.0,
    "decan": 10.0,
    "musallaha": 5.0,
}
_TAJIKA_HADDA_TABLE: dict[str, tuple[tuple[str, float], ...]] = {
    "Aries": (("Jupiter", 6.0), ("Venus", 6.0), ("Mercury", 8.0), ("Mars", 5.0), ("Saturn", 5.0)),
    "Taurus": (("Venus", 8.0), ("Mercury", 6.0), ("Jupiter", 8.0), ("Saturn", 5.0), ("Mars", 3.0)),
    "Gemini": (("Mercury", 6.0), ("Venus", 6.0), ("Jupiter", 5.0), ("Mars", 7.0), ("Saturn", 6.0)),
    "Cancer": (("Mars", 7.0), ("Venus", 6.0), ("Mercury", 6.0), ("Jupiter", 7.0), ("Saturn", 4.0)),
    "Leo": (("Jupiter", 6.0), ("Venus", 5.0), ("Saturn", 7.0), ("Mercury", 6.0), ("Mars", 6.0)),
    "Virgo": (("Mercury", 7.0), ("Venus", 10.0), ("Jupiter", 4.0), ("Mars", 7.0), ("Saturn", 2.0)),
    "Libra": (("Saturn", 6.0), ("Mercury", 8.0), ("Jupiter", 7.0), ("Venus", 7.0), ("Mars", 2.0)),
    "Scorpio": (("Mars", 7.0), ("Venus", 4.0), ("Mercury", 8.0), ("Jupiter", 5.0), ("Saturn", 6.0)),
    "Sagittarius": (("Jupiter", 12.0), ("Venus", 5.0), ("Mercury", 4.0), ("Mars", 5.0), ("Saturn", 4.0)),
    "Capricorn": (("Mercury", 7.0), ("Jupiter", 7.0), ("Venus", 8.0), ("Saturn", 4.0), ("Mars", 4.0)),
    "Aquarius": (("Mercury", 7.0), ("Venus", 6.0), ("Jupiter", 7.0), ("Mars", 5.0), ("Saturn", 5.0)),
    "Pisces": (("Venus", 12.0), ("Jupiter", 4.0), ("Mercury", 3.0), ("Mars", 9.0), ("Saturn", 2.0)),
}
_TAJIKA_DECAN_RULERS: dict[str, tuple[str, str, str]] = {
    "Aries": ("Mars", "Sun", "Venus"),
    "Taurus": ("Mercury", "Moon", "Saturn"),
    "Gemini": ("Jupiter", "Mars", "Sun"),
    "Cancer": ("Venus", "Mercury", "Moon"),
    "Leo": ("Saturn", "Jupiter", "Mars"),
    "Virgo": ("Sun", "Venus", "Mercury"),
    "Libra": ("Moon", "Saturn", "Jupiter"),
    "Scorpio": ("Mars", "Sun", "Venus"),
    "Sagittarius": ("Mercury", "Moon", "Saturn"),
    "Capricorn": ("Jupiter", "Mars", "Sun"),
    "Aquarius": ("Venus", "Mercury", "Moon"),
    "Pisces": ("Saturn", "Jupiter", "Mars"),
}
_TAJIKA_MALE_PLANETS: frozenset[str] = frozenset({"Sun", "Mars", "Jupiter", "Saturn"})
_TAJIKA_FEMALE_PLANETS: frozenset[str] = frozenset({"Moon", "Venus", "Mercury"})
_TAJIKA_BENEFIC_SUPPORTERS: frozenset[str] = frozenset({"Moon", "Mercury", "Jupiter", "Venus"})
_TAJIKA_MALEFIC_BLOCKERS: frozenset[str] = frozenset({"Mars", "Saturn"})
_TAJIKA_DIG_BALA_HOUSES: dict[str, int] = {
    "Sun": 9,
    "Moon": 3,
    "Mars": 6,
    "Mercury": 1,
    "Jupiter": 11,
    "Venus": 5,
    "Saturn": 12,
}
_EXALTATION_SIGN_OWNER: dict[str, str] = {
    sign_name: planet
    for planet, sign_idx in EXALTATION_SIGN.items()
    for sign_name in (SIGNS[sign_idx],)
}


def _normalize(longitude: float) -> float:
    return longitude % 360.0


def _arc_contains(start: float, end: float, point: float) -> bool:
    """Return whether *point* lies on the direct zodiacal arc from start to end."""

    span = (end - start) % 360.0
    dist = (point - start) % 360.0
    return dist <= span


def _sign_lord(longitude: float) -> str:
    return DOMICILE_RULERS[sign_of(longitude)[0]]


def _mudda_sequence_from(start_lord: str) -> tuple[str, ...]:
    if start_lord not in _MUDDA_LORD_SEQUENCE:
        raise KeyError(f"Unsupported mudda lord: {start_lord!r}")
    start_idx = _MUDDA_LORD_SEQUENCE.index(start_lord)
    return tuple(
        _MUDDA_LORD_SEQUENCE[(start_idx + offset) % len(_MUDDA_LORD_SEQUENCE)]
        for offset in range(len(_MUDDA_LORD_SEQUENCE))
    )


def _mudda_year_ruler_from_nakshatra(nakshatra_index: int, years_elapsed: int) -> str:
    base_index = (nakshatra_index - _MUDDA_GAURI_START_NAKSHATRA_INDEX) % len(_MUDDA_LORD_SEQUENCE)
    return _MUDDA_LORD_SEQUENCE[(base_index + years_elapsed) % len(_MUDDA_LORD_SEQUENCE)]


def _mudda_jd_for_nominal_day(
    nominal_day: float,
    year_start_jd: float,
    year_end_jd: float,
) -> float:
    return year_start_jd + ((year_end_jd - year_start_jd) * (nominal_day / 360.0))


def _sign_distance(from_longitude: float, to_longitude: float) -> int:
    return ((int(_normalize(to_longitude) // 30) - int(_normalize(from_longitude) // 30)) % 12) + 1


def _tajika_friendship_category(
    planet: str,
    ruler: str,
    sidereal_planets: dict[str, float],
) -> str:
    if ruler == planet:
        return "own"
    distance = _sign_distance(sidereal_planets[planet], sidereal_planets[ruler])
    if distance in {5, 9}:
        return "great_friend"
    if distance in {3, 11}:
        return "friend"
    if distance in {2, 6, 8, 12}:
        return "neutral"
    if distance in {4, 10}:
        return "enemy"
    return "great_enemy"


def _tajika_weighted_score(kind: str, relationship: str) -> float:
    return (_TAJIKA_PANCHAVARGI_MAXIMA[kind] * _TAJIKA_FRIENDSHIP_FRACTIONS[relationship]) / 4.0


def _tajika_hadda_lord(longitude: float) -> str:
    sign_name, _, deg_in_sign = sign_of(longitude)
    traversed = 0.0
    for ruler, span in _TAJIKA_HADDA_TABLE[sign_name]:
        upper = traversed + span
        if deg_in_sign < upper or abs(deg_in_sign - upper) < 1e-12:
            return ruler
        traversed = upper
    return _TAJIKA_HADDA_TABLE[sign_name][-1][0]


def _tajika_decan_lord(longitude: float) -> str:
    sign_name, _, deg_in_sign = sign_of(longitude)
    decan_idx = min(int(deg_in_sign // 10.0), 2)
    return _TAJIKA_DECAN_RULERS[sign_name][decan_idx]


def _tajika_musallaha_lord(longitude: float) -> str:
    return DOMICILE_RULERS[navamsa(longitude).sign]


def _tajika_exaltation_basis(
    planet: str,
    longitude: float,
    sidereal_planets: dict[str, float],
) -> tuple[str | None, str, float]:
    sign_name = sign_of(longitude)[0]
    basis_planet = _EXALTATION_SIGN_OWNER.get(sign_name)
    if basis_planet is None:
        return None, "own", _TAJIKA_PANCHAVARGI_MAXIMA["exaltation"] / 4.0
    relationship = _tajika_friendship_category(planet, basis_planet, sidereal_planets)
    return basis_planet, relationship, _tajika_weighted_score("exaltation", relationship)


def _arc_midpoint(start: float, end: float) -> float:
    return _normalize(start + ((end - start) % 360.0) / 2.0)


def _arc_length(start: float, end: float) -> float:
    return (end - start) % 360.0


def _tajika_house_result(longitude: float, house_cusps: HouseCusps) -> float:
    house = house_of(longitude, house_cusps)
    cusp = house_cusps.cusps[house - 1]
    prev_cusp = house_cusps.cusps[house - 2]
    next_cusp = house_cusps.cusps[house % 12]
    opening_junction = _arc_midpoint(prev_cusp, cusp)
    closing_junction = _arc_midpoint(cusp, next_cusp)
    rise_span = _arc_length(opening_junction, cusp)
    fall_span = _arc_length(cusp, closing_junction)
    if rise_span == 0.0 or fall_span == 0.0:
        return 0.0
    if _arc_contains(opening_junction, cusp, longitude):
        return 60.0 * _arc_length(opening_junction, longitude) / rise_span
    return 60.0 * _arc_length(longitude, closing_junction) / fall_span


def _tajika_night_window(
    jd_ut: float,
    latitude: float,
    longitude: float,
) -> tuple[float, float] | None:
    jd_day = float(int(jd_ut - 0.5) + 0.5)
    today = twilight_times(jd_day, latitude, longitude)
    tomorrow = twilight_times(jd_day + 1.0, latitude, longitude)
    yesterday = twilight_times(jd_day - 1.0, latitude, longitude)
    if today.sunrise is not None and jd_ut < today.sunrise and yesterday.sunset is not None:
        return yesterday.sunset, today.sunrise
    if today.sunset is not None and jd_ut >= today.sunset and tomorrow.sunrise is not None:
        return today.sunset, tomorrow.sunrise
    return None


def _tajika_sect_strength(
    planet: str,
    ascendant: float,
    sun_longitude: float,
) -> float:
    arc = (ascendant - sun_longitude) % 360.0
    if planet in _TAJIKA_MALE_PLANETS:
        if arc >= 180.0:
            return 0.0
        branch = arc if arc <= 90.0 else 180.0 - arc
        return max(0.0, min(60.0, branch * (60.0 / 90.0)))
    if planet in _TAJIKA_FEMALE_PLANETS:
        if arc <= 180.0:
            return 0.0
        branch = arc - 180.0
        branch = branch if branch <= 90.0 else 180.0 - branch
        return max(0.0, min(60.0, branch * (60.0 / 90.0)))
    return 0.0


def _tajika_kala_bala(
    planet: str,
    longitude: float,
    ascendant: float,
    sun_longitude: float,
    *,
    jd_ut: float | None = None,
    latitude: float | None = None,
    longitude_geo: float | None = None,
) -> TajikaKalaBala:
    sect_strength = _tajika_sect_strength(planet, ascendant, sun_longitude)
    luminary_elongation_strength = 0.0
    if planet in {"Moon", "Mars"}:
        luminary_elongation_strength = angular_distance(longitude, sun_longitude) / 3.0
    venus_elongation_strength = 0.0
    if planet == "Venus":
        venus_elongation_strength = min(angular_distance(longitude, sun_longitude), 50.0) * (6.0 / 5.0)
    night_watch_strength = 0.0
    if planet in {"Jupiter", "Saturn"} and jd_ut is not None and latitude is not None and longitude_geo is not None:
        night_window = _tajika_night_window(jd_ut, latitude, longitude_geo)
        if night_window is not None:
            sunset_jd, sunrise_jd = night_window
            night_len = sunrise_jd - sunset_jd
            if night_len > 0.0:
                midnight_jd = sunset_jd + night_len / 2.0
                third_watch_end = sunset_jd + (3.0 * night_len / 4.0)
                if midnight_jd <= jd_ut <= third_watch_end:
                    night_watch_strength = 60.0 * (jd_ut - midnight_jd) / (third_watch_end - midnight_jd)
                elif third_watch_end < jd_ut <= sunrise_jd:
                    night_watch_strength = 60.0 * (sunrise_jd - jd_ut) / (sunrise_jd - third_watch_end)
    total_score = max(sect_strength, luminary_elongation_strength, venus_elongation_strength, night_watch_strength)
    return TajikaKalaBala(
        planet=planet,
        sect_strength=sect_strength,
        luminary_elongation_strength=luminary_elongation_strength,
        venus_elongation_strength=venus_elongation_strength,
        night_watch_strength=night_watch_strength,
        total_score=total_score,
    )


def _tajika_chesta_bala(
    planet: str,
    longitude: float,
    sidereal_planets: dict[str, float],
    *,
    planet_speeds: dict[str, float] | None = None,
) -> TajikaChestaBala:
    speed = None if planet_speeds is None else planet_speeds.get(planet)
    mean = MEAN_DAILY_MOTION.get(planet)
    motion_mode_strength = 0.0
    if speed is not None and mean is not None and speed >= 0.0 and speed <= mean:
        motion_mode_strength = 60.0

    blocked_by_malefic_contact = any(
        blocker != planet
        and blocker in sidereal_planets
        and angular_distance(longitude, sidereal_planets[blocker]) <= 30.0
        for blocker in _TAJIKA_MALEFIC_BLOCKERS
    )
    benefic_contact_strength = 0.0
    if not blocked_by_malefic_contact:
        for benefic in _TAJIKA_BENEFIC_SUPPORTERS:
            if benefic == planet or benefic not in sidereal_planets:
                continue
            benefic_contact_strength = max(
                benefic_contact_strength,
                max(0.0, 2.0 * (30.0 - angular_distance(longitude, sidereal_planets[benefic]))),
            )

    solar_synodic_strength = 0.0
    sun_longitude = sidereal_planets.get("Sun")
    if sun_longitude is not None:
        same_sign = sign_of(longitude)[0] == sign_of(sun_longitude)[0]
        same_navamsa = navamsa(longitude).sign == navamsa(sun_longitude).sign
        if same_sign and same_navamsa:
            solar_synodic_strength = max(0.0, 60.0 - 2.0 * abs((longitude % 30.0) - (sun_longitude % 30.0)))

    total_score = max(motion_mode_strength, benefic_contact_strength, solar_synodic_strength)
    return TajikaChestaBala(
        planet=planet,
        motion_mode_strength=motion_mode_strength,
        benefic_contact_strength=benefic_contact_strength,
        solar_synodic_strength=solar_synodic_strength,
        blocked_by_malefic_contact=blocked_by_malefic_contact,
        total_score=total_score,
    )


def _tajika_drig_bala(
    planet: str,
    longitude: float,
    year_asc: float,
    sidereal_planets: dict[str, float],
) -> TajikaDrigBala:
    asc_aspect = _candidate_asc_aspect(planet, longitude, year_asc, TajikaAspectPolicy())
    ascendant_aspect_strength = 0.0 if asc_aspect is None else _TAJIKA_RELATIONS[asc_aspect.angle][1] * 60.0
    annual_aspects = tajika_aspects(sidereal_planets)
    blocked_by_malefic_square = any(
        aspect.aspect.angle == 90.0
        and planet in {aspect.body1, aspect.body2}
        and ({aspect.body1, aspect.body2} - {planet}).pop() in _TAJIKA_MALEFIC_BLOCKERS
        for aspect in annual_aspects
    )
    benefic_support_strength = 0.0
    if not blocked_by_malefic_square:
        for aspect in annual_aspects:
            if planet not in {aspect.body1, aspect.body2}:
                continue
            other = aspect.body2 if aspect.body1 == planet else aspect.body1
            if other not in _TAJIKA_BENEFIC_SUPPORTERS:
                continue
            benefic_support_strength = max(
                benefic_support_strength,
                aspect.relation_strength * 45.0,
            )
    return TajikaDrigBala(
        planet=planet,
        ascendant_aspect_strength=ascendant_aspect_strength,
        benefic_support_strength=benefic_support_strength,
        blocked_by_malefic_square=blocked_by_malefic_square,
        total_score=ascendant_aspect_strength + benefic_support_strength,
    )


def tajika_panchavargi_strength(
    planet: str,
    longitude: float,
    sidereal_planets: dict[str, float],
) -> TajikaPanchavargiStrength:
    """
    Compute Tajika five-dignity strength on the classical 20-point scale.

    Source basis admitted here:
    - Hayanaratna chapter 4: the fivefold friendship scheme used for
      particular strength.
    - Hayanaratna chapter 5: twenty-point panchavargi strength from domicile,
      exaltation, hadda, decan, and musallaha.

    The domicile, hadda, decan, and musallaha components are scored through
    their local rulers and the fivefold friendship table. The exaltation
    component now also preserves the primary-source distinction between a
    planet's own exaltation and the exaltation of a great friend and so on,
    while still using proportional distance from deepest exaltation to deepest
    debilitation for the actual score.
    """

    if planet not in sidereal_planets:
        raise KeyError(f"Planet {planet!r} not present in sidereal_planets")

    sign_name = sign_of(longitude)[0]
    domicile_lord = _sign_lord(longitude)
    domicile_relationship = _tajika_friendship_category(planet, domicile_lord, sidereal_planets)
    domicile_score = _tajika_weighted_score("domicile", domicile_relationship)

    dignity = vedic_dignity(planet, longitude)
    exaltation_basis_planet, exaltation_relationship, exaltation_max = _tajika_exaltation_basis(
        planet,
        longitude,
        sidereal_planets,
    )
    exaltation_score = exaltation_max * dignity.exaltation_score

    hadda_lord = _tajika_hadda_lord(longitude)
    hadda_relationship = _tajika_friendship_category(planet, hadda_lord, sidereal_planets)
    hadda_score = _tajika_weighted_score("hadda", hadda_relationship)

    decan_lord = _tajika_decan_lord(longitude)
    decan_relationship = _tajika_friendship_category(planet, decan_lord, sidereal_planets)
    decan_score = _tajika_weighted_score("decan", decan_relationship)

    musallaha_lord = _tajika_musallaha_lord(longitude)
    musallaha_relationship = _tajika_friendship_category(planet, musallaha_lord, sidereal_planets)
    musallaha_score = _tajika_weighted_score("musallaha", musallaha_relationship)

    total_score = domicile_score + exaltation_score + hadda_score + decan_score + musallaha_score
    if total_score <= 5.0:
        category = "powerless"
    elif total_score <= 10.0:
        category = "middling"
    elif total_score <= 15.0:
        category = "excellent"
    else:
        category = "full"

    return TajikaPanchavargiStrength(
        planet=planet,
        longitude=_normalize(longitude),
        sign=sign_name,
        domicile_lord=domicile_lord,
        domicile_relationship=domicile_relationship,
        domicile_score=domicile_score,
        exaltation_basis_planet=exaltation_basis_planet,
        exaltation_relationship=exaltation_relationship,
        exaltation_score=exaltation_score,
        hadda_lord=hadda_lord,
        hadda_relationship=hadda_relationship,
        hadda_score=hadda_score,
        decan_lord=decan_lord,
        decan_relationship=decan_relationship,
        decan_score=decan_score,
        musallaha_lord=musallaha_lord,
        musallaha_relationship=musallaha_relationship,
        musallaha_score=musallaha_score,
        total_score=total_score,
        category=category,
    )


def tajika_shadbala_profile(
    planet: str,
    *,
    sidereal_planets: dict[str, float],
    sidereal_houses: HouseCusps,
    year_asc: float,
    jd_ut: float | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    planet_speeds: dict[str, float] | None = None,
) -> TajikaShadbalaProfile:
    """
    Compute the currently admitted Tajika sixfold strength profile.

    This profile combines the chapter-5 panchavargi layer with the remaining
    chapter-6 non-panchavargi strengths that can be computed directly from the
    annual chart and its return moment.
    """

    if planet not in sidereal_planets:
        raise KeyError(f"Planet {planet!r} not present in sidereal_planets")

    longitude_planet = sidereal_planets[planet]
    panchavargi = tajika_panchavargi_strength(planet, longitude_planet, sidereal_planets)
    directional_strength = (
        _tajika_house_result(longitude_planet, sidereal_houses)
        if house_of(longitude_planet, sidereal_houses) == _TAJIKA_DIG_BALA_HOUSES[planet]
        else 0.0
    )
    temporal_strength = _tajika_kala_bala(
        planet,
        longitude_planet,
        year_asc,
        sidereal_planets["Sun"],
        jd_ut=jd_ut,
        latitude=latitude,
        longitude_geo=longitude,
    )
    natural_strength = NAISARGIKA_BALA[planet]
    motion_strength = _tajika_chesta_bala(
        planet,
        longitude_planet,
        sidereal_planets,
        planet_speeds=planet_speeds,
    )
    aspect_strength = _tajika_drig_bala(
        planet,
        longitude_planet,
        year_asc,
        sidereal_planets,
    )
    total_score = (
        panchavargi.total_score
        + directional_strength
        + temporal_strength.total_score
        + natural_strength
        + motion_strength.total_score
        + aspect_strength.total_score
    )
    return TajikaShadbalaProfile(
        planet=planet,
        panchavargi_strength=panchavargi,
        directional_strength=directional_strength,
        temporal_strength=temporal_strength,
        natural_strength=natural_strength,
        motion_strength=motion_strength,
        aspect_strength=aspect_strength,
        total_score=total_score,
    )


def _is_strong_dignity(dignity: VedicDignityResult) -> bool:
    return dignity.dignity_rank in {
        VedicDignityRank.EXALTATION,
        VedicDignityRank.MULATRIKONA,
        VedicDignityRank.OWN_SIGN,
    }


def _is_weak_dignity(dignity: VedicDignityResult) -> bool:
    return dignity.dignity_rank in {
        VedicDignityRank.ENEMY_SIGN,
        VedicDignityRank.DEBILITATION,
    }


def _classify_authority(score: float) -> str:
    if score >= 180.0:
        return "strong"
    if score >= 120.0:
        return "supportive"
    if score >= 80.0:
        return "mixed"
    return "strained"


def _authority_to_period_quality(authority: str | None) -> str:
    if authority == "strong":
        return "excellent"
    if authority in {"supportive", "mixed"}:
        return "middling"
    if authority == "strained":
        return "poor"
    return "ungraded"


def _actor_house_bonus(house: int) -> float:
    if house in {1, 4, 7, 10}:
        return 18.0
    if house in {1, 5, 9}:
        return 14.0
    if house in {3, 6, 10, 11}:
        return 10.0
    if house in {6, 8, 12}:
        return -14.0
    return 4.0


def _saham_house_bonus(house: int) -> float:
    if house in {1, 4, 7, 10}:
        return 16.0
    if house in {1, 5, 9, 11}:
        return 12.0
    if house in {6, 8, 12}:
        return -12.0
    return 3.0


def _actor_yoga_balance(
    planet: str,
    yogas: tuple[TajikaYoga, ...],
) -> tuple[int, int]:
    supportive = 0
    obstructive = 0
    for yoga in yogas:
        if planet not in {getattr(yoga, "body1", None), getattr(yoga, "body2", None), getattr(yoga, "mediator", None)}:
            continue
        if getattr(yoga, "favorable", False):
            supportive += 1
        else:
            obstructive += 1
    return supportive, obstructive


def _build_actor_judgement(
    *,
    actor: str,
    planet: str,
    sidereal_planets: dict[str, float],
    sidereal_houses: HouseCusps,
    year_asc: float,
    jd_ut: float | None,
    latitude: float | None,
    longitude: float | None,
    planet_speeds: dict[str, float] | None,
    yogas: tuple[TajikaYoga, ...],
) -> VarshaphalActorJudgement:
    longitude_planet = sidereal_planets[planet]
    house = house_of(longitude_planet, sidereal_houses)
    panchavargi = tajika_panchavargi_strength(planet, longitude_planet, sidereal_planets)
    shadbala = tajika_shadbala_profile(
        planet,
        sidereal_planets=sidereal_planets,
        sidereal_houses=sidereal_houses,
        year_asc=year_asc,
        jd_ut=jd_ut,
        latitude=latitude,
        longitude=longitude,
        planet_speeds=planet_speeds,
    )
    supportive_yoga_count, obstructive_yoga_count = _actor_yoga_balance(planet, yogas)
    authority_score = (
        shadbala.total_score
        + (supportive_yoga_count * 12.0)
        - (obstructive_yoga_count * 10.0)
        + _actor_house_bonus(house)
    )
    return VarshaphalActorJudgement(
        actor=actor,
        planet=planet,
        house=house,
        supportive_yoga_count=supportive_yoga_count,
        obstructive_yoga_count=obstructive_yoga_count,
        panchavargi_strength=panchavargi,
        shadbala=shadbala,
        authority_score=authority_score,
        authority=_classify_authority(authority_score),
    )


def _build_saham_judgement(
    *,
    saham: VarshaphalSaham,
    sidereal_planets: dict[str, float],
    sidereal_houses: HouseCusps,
    year_asc: float,
    jd_ut: float | None,
    latitude: float | None,
    longitude: float | None,
    planet_speeds: dict[str, float] | None,
) -> VarshaphalSahamJudgement:
    ruler_house = house_of(sidereal_planets[saham.ruler], sidereal_houses)
    ruler_strength = tajika_shadbala_profile(
        saham.ruler,
        sidereal_planets=sidereal_planets,
        sidereal_houses=sidereal_houses,
        year_asc=year_asc,
        jd_ut=jd_ut,
        latitude=latitude,
        longitude=longitude,
        planet_speeds=planet_speeds,
    )
    relevance_score = (
        ruler_strength.total_score
        + _saham_house_bonus(saham.house)
        + _actor_house_bonus(ruler_house) / 2.0
    )
    return VarshaphalSahamJudgement(
        saham_name=saham.name,
        house=saham.house,
        ruler=saham.ruler,
        ruler_house=ruler_house,
        ruler_strength=ruler_strength,
        relevance_score=relevance_score,
        authority=_classify_authority(relevance_score),
    )


def _fallback_saham_judgement(
    saham: VarshaphalSaham,
    sidereal_houses: HouseCusps,
    sidereal_planets: dict[str, float],
) -> VarshaphalSahamJudgement:
    ruler_house = (
        house_of(sidereal_planets[saham.ruler], sidereal_houses)
        if saham.ruler in sidereal_planets
        else saham.house
    )
    relevance_score = _saham_house_bonus(saham.house) + (_actor_house_bonus(ruler_house) / 2.0)
    return VarshaphalSahamJudgement(
        saham_name=saham.name,
        house=saham.house,
        ruler=saham.ruler,
        ruler_house=ruler_house,
        ruler_strength=TajikaShadbalaProfile(
            planet=saham.ruler,
            panchavargi_strength=TajikaPanchavargiStrength(
                planet=saham.ruler,
                longitude=sidereal_planets.get(saham.ruler, 0.0),
                sign=sign_of(sidereal_planets.get(saham.ruler, 0.0))[0],
                domicile_lord=saham.ruler,
                domicile_relationship="own",
                domicile_score=0.0,
                exaltation_basis_planet=None,
                exaltation_relationship="own",
                exaltation_score=0.0,
                hadda_lord=saham.ruler,
                hadda_relationship="own",
                hadda_score=0.0,
                decan_lord=saham.ruler,
                decan_relationship="own",
                decan_score=0.0,
                musallaha_lord=saham.ruler,
                musallaha_relationship="own",
                musallaha_score=0.0,
                total_score=0.0,
                category="none",
            ),
            directional_strength=0.0,
            temporal_strength=TajikaKalaBala(saham.ruler, 0.0, 0.0, 0.0, 0.0, 0.0),
            natural_strength=0.0,
            motion_strength=TajikaChestaBala(saham.ruler, 0.0, 0.0, 0.0, False, 0.0),
            aspect_strength=TajikaDrigBala(saham.ruler, 0.0, 0.0, False, 0.0),
            total_score=0.0,
        ),
        relevance_score=relevance_score,
        authority=_classify_authority(relevance_score),
    )


def _saham_priority(
    *,
    annual_judgement: VarshaphalSahamJudgement,
    natal_judgement: VarshaphalSahamJudgement,
) -> VarshaphalSahamPriority:
    if annual_judgement.authority == "strained" and natal_judgement.authority == "strained":
        return VarshaphalSahamPriority(
            saham_name=annual_judgement.saham_name,
            annual_judgement=annual_judgement,
            natal_judgement=natal_judgement,
            priority="disregarded",
            is_considered=False,
            doctrine=(
                "Sahamas found weak by every method in both nativity and year "
                "should not be considered in the annual judgement."
            ),
        )
    if annual_judgement.authority in {"strong", "supportive"} and natal_judgement.authority in {"strong", "supportive"}:
        return VarshaphalSahamPriority(
            saham_name=annual_judgement.saham_name,
            annual_judgement=annual_judgement,
            natal_judgement=natal_judgement,
            priority="high",
            is_considered=True,
            doctrine=(
                "Sahamas supported in both nativity and year, together with "
                "their rulers, are to be considered in the annual judgement."
            ),
        )
    return VarshaphalSahamPriority(
        saham_name=annual_judgement.saham_name,
        annual_judgement=annual_judgement,
        natal_judgement=natal_judgement,
        priority="secondary",
        is_considered=True,
        doctrine=(
            "Mixed Sahama testimony is retained but carries less authority than "
            "Sahamas supported in both nativity and year."
        ),
    )


def _topic_house_rulers(
    house_numbers: tuple[int, ...],
    sidereal_houses: HouseCusps,
) -> tuple[str, ...]:
    rulers: list[str] = []
    for house in house_numbers:
        ruler = _sign_lord(sidereal_houses.cusps[house - 1])
        if ruler not in rulers:
            rulers.append(ruler)
    return tuple(rulers)


def _supports_topic_from_varshesha(
    *,
    varshesha_planet: str,
    rulers: tuple[str, ...],
    yogas: tuple[TajikaYoga, ...],
) -> tuple[bool, bool]:
    supportive = False
    obstructive = False
    for ruler in rulers:
        relation = _mudda_relation(varshesha_planet, ruler, yogas)
        if relation == "ithasala":
            supportive = True
        elif relation == "isarpha":
            obstructive = True
    return supportive, obstructive


def _topic_emphasis_score(
    *,
    saham_priority: VarshaphalSahamPriority | None,
    supportive: bool,
    obstructive: bool,
    timed_activation: str,
) -> float:
    score = 0.0
    if saham_priority is not None:
        if saham_priority.priority == "high":
            score += 40.0
        elif saham_priority.priority == "secondary":
            score += 22.0
        elif saham_priority.priority == "disregarded":
            score -= 30.0
    if supportive:
        score += 16.0
    if obstructive:
        score += 12.0
    if timed_activation == "active":
        score += 18.0
    elif timed_activation == "blocked":
        score += 10.0
    return score


def _topic_rulebook_adjustment(
    *,
    topic: str,
    chart: VarshaphalChart,
    profile: VarshaphalJudgementProfile,
    saham_priority: VarshaphalSahamPriority | None,
    house_rulers: tuple[str, ...],
    house_numbers: tuple[int, ...],
    yogas: tuple[TajikaYoga, ...],
    timed_activation: str,
) -> tuple[tuple[str, ...], float, bool, bool, bool]:
    """Apply topic-owned annual doctrine from the primary house chapters."""

    basis: list[str] = []
    bonus = 0.0
    constructive = False
    adverse = False
    mitigated = False
    year_lagna_lord = getattr(profile, "year_lagna_lord", None)
    sidereal_planets = getattr(chart, "sidereal_planets", {})
    chart_planets = getattr(getattr(chart, "chart", None), "planets", {})
    planet_speeds = {
        name: body.speed
        for name, body in chart_planets.items()
        if hasattr(body, "speed")
    }
    saham_authority = None if saham_priority is None else getattr(saham_priority.annual_judgement, "authority", None)
    ruler_houses = tuple(
        house_of(sidereal_planets[ruler], chart.sidereal_houses)
        for ruler in house_rulers
        if ruler in sidereal_planets
    )

    if topic == "wealth":
        if year_lagna_lord is not None:
            for ruler in house_rulers:
                relation = _mudda_relation(ruler, year_lagna_lord, yogas)
                if relation == "ithasala":
                    basis.append("wealth_easy_gain:lagna_second_ithasala")
                    constructive = True
                    bonus += 14.0
                    break
                if relation == "isarpha":
                    basis.append("wealth_loss:lagna_second_isarpha")
                    adverse = True
                    bonus += 14.0
                    break
        if saham_authority in {"strong", "supportive"}:
            basis.append("wealth_supported:artha_ruler_strong")
            constructive = True
            bonus += 12.0
        elif saham_authority == "strained":
            basis.append("wealth_weakened:artha_ruler_strained")
            adverse = True
            bonus += 10.0

    elif topic == "marriage":
        if year_lagna_lord is not None:
            relation = _mudda_relation(house_rulers[0], year_lagna_lord, yogas)
            if relation == "ithasala":
                basis.append("marriage_testimony:lagna_seventh_ithasala")
                constructive = True
                bonus += 16.0
            elif relation == "isarpha":
                basis.append("marriage_blocked:lagna_seventh_isarpha")
                adverse = True
                bonus += 14.0
        if saham_authority in {"strong", "supportive"}:
            basis.append("marriage_supported:vivaha_ruler_strong")
            constructive = True
            bonus += 12.0
        elif saham_authority == "strained":
            basis.append("marriage_weakened:vivaha_ruler_strained")
            adverse = True
            bonus += 10.0
        if "Venus" in sidereal_planets and house_of(sidereal_planets["Venus"], chart.sidereal_houses) == 7:
            basis.append("marriage_venus_in_seventh")
            constructive = True
            bonus += 8.0

    elif topic == "illness":
        if any(house in {6, 8} for house in ruler_houses):
            basis.append("illness_active:ruler_in_disease_house")
            adverse = True
            bonus += 12.0
        saturn_house = (
            house_of(sidereal_planets["Saturn"], chart.sidereal_houses)
            if "Saturn" in sidereal_planets
            else None
        )
        if (
            chart.varshesha.planet == "Saturn"
            and saturn_house == 6
            and planet_speeds.get("Saturn", 0.0) < 0.0
        ):
            basis.append("illness_compounded:saturn_retrograde_in_sixth")
            adverse = True
            bonus += 18.0
        if timed_activation == "active":
            basis.append("illness_period_active")
            adverse = True
            bonus += 8.0
        if any(
            yoga.name == "Kamboola"
            and any(ruler in {yoga.body1, yoga.body2, yoga.mediator} for ruler in house_rulers)
            for yoga in yogas
        ):
            basis.append("illness_mitigated:kamboola")
            mitigated = True
            bonus -= 6.0

    elif topic == "children":
        jupiter_house = (
            house_of(sidereal_planets["Jupiter"], chart.sidereal_houses)
            if "Jupiter" in sidereal_planets
            else None
        )
        if chart.varshesha.planet == "Jupiter" and jupiter_house in {5, 11}:
            basis.append("children_happiness:jupiter_year_ruler_in_fifth_or_eleventh")
            constructive = True
            bonus += 16.0
        if year_lagna_lord is not None:
            relation = _mudda_relation(house_rulers[0], year_lagna_lord, yogas)
            if relation == "ithasala":
                basis.append("children_supported:fifth_lord_ithasala_with_lagna")
                constructive = True
                bonus += 10.0
            elif relation == "isarpha":
                basis.append("children_unhappiness:fifth_lord_isarpha_with_lagna")
                adverse = True
                bonus += 12.0
        if saham_authority in {"strong", "supportive"}:
            basis.append("children_supported:putra_ruler_strong")
            constructive = True
            bonus += 12.0
        elif saham_authority == "strained":
            basis.append("children_weakened:putra_ruler_strained")
            adverse = True
            bonus += 10.0

    elif topic == "career":
        if year_lagna_lord is not None:
            for ruler in house_rulers:
                relation = _mudda_relation(ruler, year_lagna_lord, yogas)
                if relation == "ithasala":
                    basis.append("career_supported:tenth_lord_ithasala_with_lagna")
                    constructive = True
                    bonus += 14.0
                    break
                if relation == "isarpha":
                    basis.append("career_blocked:tenth_lord_isarpha_with_lagna")
                    adverse = True
                    bonus += 14.0
                    break
        if any(house in {6, 8, 12} for house in ruler_houses):
            basis.append("career_failure:tenth_lord_in_bad_house")
            adverse = True
            bonus += 14.0
        if "Sun" in sidereal_planets and house_of(sidereal_planets["Sun"], chart.sidereal_houses) == 10:
            basis.append("career_visibility:sun_in_tenth")
            constructive = True
            bonus += 8.0
        if saham_authority in {"strong", "supportive"}:
            basis.append("career_supported:karyasiddhi_ruler_strong")
            constructive = True
            bonus += 12.0
        elif saham_authority == "strained":
            basis.append("career_weakened:karyasiddhi_ruler_strained")
            adverse = True
            bonus += 10.0

    elif topic == "travel":
        if year_lagna_lord is not None:
            relation = _mudda_relation(house_rulers[0], year_lagna_lord, yogas)
            if relation == "ithasala":
                basis.append("travel_planned:ninth_lord_ithasala_with_lagna")
                constructive = True
                bonus += 14.0
            elif relation == "isarpha":
                basis.append("travel_hindered:ninth_lord_isarpha_with_lagna")
                adverse = True
                bonus += 12.0
        if any(house in {3, 9} for house in ruler_houses):
            basis.append("travel_signified:ninth_lord_in_third_or_ninth")
            constructive = True
            bonus += 10.0
        if any(
            yoga.name == "Kamboola"
            and any(ruler in {yoga.body1, yoga.body2, yoga.mediator} for ruler in house_rulers)
            for yoga in yogas
        ):
            basis.append("travel_happy:ninth_lord_kamboola")
            constructive = True
            bonus += 10.0
        if chart.varshesha.planet in sidereal_planets:
            varshesha_house = house_of(sidereal_planets[chart.varshesha.planet], chart.sidereal_houses)
            if varshesha_house in {3, 9}:
                if getattr(profile, "yearly_strength_balance", "mixed") == "supportive":
                    basis.append("travel_happy:year_ruler_strong_in_third_or_ninth")
                    constructive = True
                    bonus += 12.0
                elif getattr(profile, "yearly_strength_balance", "mixed") == "adverse":
                    basis.append("travel_suffers:year_ruler_weak_in_third_or_ninth")
                    adverse = True
                    bonus += 10.0
        if timed_activation == "active":
            basis.append("travel_period_active")
            constructive = True
            bonus += 6.0

    elif topic == "authority":
        if year_lagna_lord is not None:
            for ruler in house_rulers:
                relation = _mudda_relation(ruler, year_lagna_lord, yogas)
                if relation == "ithasala":
                    basis.append("authority_supported:tenth_lord_ithasala_with_lagna")
                    constructive = True
                    bonus += 14.0
                    break
                if relation == "isarpha":
                    basis.append("authority_falls:tenth_lord_isarpha_with_lagna")
                    adverse = True
                    bonus += 14.0
                    break
        if "Sun" in sidereal_planets and house_of(sidereal_planets["Sun"], chart.sidereal_houses) == 10:
            basis.append("authority_rank:sun_in_tenth")
            constructive = True
            bonus += 12.0
        if saham_priority is not None and getattr(saham_priority.annual_judgement, "house", None) == 10:
            basis.append("authority_flourishes:raja_saham_in_tenth")
            constructive = True
            bonus += 14.0
        if saham_authority in {"strong", "supportive"}:
            basis.append("authority_supported:raja_ruler_strong")
            constructive = True
            bonus += 12.0
        elif saham_authority == "strained":
            basis.append("authority_weakened:raja_ruler_strained")
            adverse = True
            bonus += 10.0
        if any(house in {6, 8, 12} for house in ruler_houses):
            basis.append("authority_unstable:tenth_lord_in_bad_house")
            adverse = True
            bonus += 12.0

    return tuple(basis), bonus, constructive, adverse, mitigated


def _append_yoga_unique(results: list[TajikaYoga], yoga: TajikaYoga) -> None:
    signature = (
        yoga.name,
        frozenset((yoga.body1, yoga.body2)),
        yoga.mediator,
        None if yoga.aspect is None else (
            yoga.aspect.body1,
            yoga.aspect.body2,
            yoga.aspect.aspect.aspect,
            yoga.aspect.aspect.angle,
        ),
        tuple(
            (
                support.body1,
                support.body2,
                support.aspect.aspect,
                support.aspect.angle,
            )
            for support in yoga.supporting_aspects
        ),
    )
    for existing in results:
        existing_signature = (
            existing.name,
            frozenset((existing.body1, existing.body2)),
            existing.mediator,
            None if existing.aspect is None else (
                existing.aspect.body1,
                existing.aspect.body2,
                existing.aspect.aspect.aspect,
                existing.aspect.aspect.angle,
            ),
            tuple(
                (
                    support.body1,
                    support.body2,
                    support.aspect.aspect,
                    support.aspect.angle,
                )
                for support in existing.supporting_aspects
            ),
        )
        if existing_signature == signature:
            return
    results.append(yoga)


_TAJIKA_TRIPLICITY_DAY: dict[str, str] = {
    "Aries": "Sun",
    "Taurus": "Venus",
    "Gemini": "Saturn",
    "Cancer": "Venus",
    "Leo": "Sun",
    "Virgo": "Venus",
    "Libra": "Saturn",
    "Scorpio": "Venus",
    "Sagittarius": "Sun",
    "Capricorn": "Venus",
    "Aquarius": "Saturn",
    "Pisces": "Venus",
}

_TAJIKA_TRIPLICITY_NIGHT: dict[str, str] = {
    "Aries": "Jupiter",
    "Taurus": "Moon",
    "Gemini": "Mercury",
    "Cancer": "Mars",
    "Leo": "Jupiter",
    "Virgo": "Moon",
    "Libra": "Mercury",
    "Scorpio": "Mars",
    "Sagittarius": "Jupiter",
    "Capricorn": "Moon",
    "Aquarius": "Mercury",
    "Pisces": "Mars",
}

_TAJIKA_TRIPLICITY_CONSTANT: dict[str, str] = {
    "Aries": "Saturn",
    "Taurus": "Mars",
    "Gemini": "Jupiter",
    "Cancer": "Moon",
    "Leo": "Saturn",
    "Virgo": "Mars",
    "Libra": "Jupiter",
    "Scorpio": "Moon",
    "Sagittarius": "Saturn",
    "Capricorn": "Mars",
    "Aquarius": "Jupiter",
    "Pisces": "Moon",
}


def muntha(natal_sidereal_asc: float, years_elapsed: int) -> float:
    """Compute Muntha from the natal sidereal Ascendant and completed years."""

    if years_elapsed < 0:
        raise ValueError(f"years_elapsed must be >= 0, got {years_elapsed}")
    return _normalize(natal_sidereal_asc + years_elapsed * 30.0)


def mudda_dasha(
    birth_jd: float,
    year: int,
    *,
    ayanamsa_system: str | UserDefinedAyanamsa = Ayanamsa.LAHIRI,
    school: str = "gauri",
    reader: SpkReader | None = None,
    return_policy: TransitComputationPolicy | None = None,
) -> MuddaDasha:
    """
    Build the annual Gauri mudda dasha schedule from the natal lunar asterism.

    Primary-source basis:
        - Hayanaratna 7.9 / Tajikamuktavali 82-86 for the nine annual mudda
          rulers, their 360-day period allotments, and the split of the
          current year's first period by the elapsed and remaining portion of
          the natal lunar asterism.
        - Hayanaratna 7.9 for the easy antardasha multipliers summing to 60.

    The doctrinal year is preserved as 360 nominal days and also mapped onto
    the actual interval between consecutive varshaphal returns.
    """

    if school.casefold() != "gauri":
        raise NotImplementedError(
            "Mudda Dasha currently implements only the Gauri school verified "
            "directly from Hayanaratna 7.9."
        )

    birth_year = calendar_datetime_from_jd(birth_jd).year
    years_elapsed = year - birth_year
    if years_elapsed < 0:
        raise ValueError(f"Mudda year {year} precedes birth year for JD {birth_jd}")

    natal_moon = all_planets_at(birth_jd, bodies=["Moon"], reader=reader)["Moon"]
    natal_nakshatra = nakshatra_of(
        natal_moon.longitude,
        birth_jd,
        ayanamsa_system=ayanamsa_system,
    )
    elapsed_fraction = natal_nakshatra.degrees_in / (360.0 / 27.0)
    elapsed_ghatis = elapsed_fraction * 60.0
    remaining_ghatis = 60.0 - elapsed_ghatis

    year_ruler = _mudda_year_ruler_from_nakshatra(
        natal_nakshatra.nakshatra_index,
        years_elapsed,
    )
    year_start_jd = _varshaphal_jd(
        birth_jd,
        year,
        ayanamsa_system=ayanamsa_system,
        reader=reader,
        policy=return_policy,
    )
    year_end_jd = _varshaphal_jd(
        birth_jd,
        year + 1,
        ayanamsa_system=ayanamsa_system,
        reader=reader,
        policy=return_policy,
    )
    sequence = _mudda_sequence_from(year_ruler)
    first_lord_full_days = _MUDDA_PERIOD_DAYS[year_ruler]
    first_remaining_days = first_lord_full_days * (remaining_ghatis / 60.0)
    final_elapsed_days = first_lord_full_days * (elapsed_ghatis / 60.0)

    periods: list[MuddaDashaPeriod] = []
    start_day = 0.0
    for index, lord in enumerate(sequence):
        if index == 0:
            duration_days = first_remaining_days
            source_fraction = "birth_nakshatra_remaining"
        else:
            duration_days = _MUDDA_PERIOD_DAYS[lord]
            source_fraction = "full_period"
        end_day = start_day + duration_days
        start_jd = _mudda_jd_for_nominal_day(start_day, year_start_jd, year_end_jd)
        end_jd = _mudda_jd_for_nominal_day(end_day, year_start_jd, year_end_jd)
        subperiods: list[MuddaDashaPeriod] = []
        sub_start_day = start_day
        for sub_lord in _mudda_sequence_from(lord):
            sub_duration = duration_days * (_MUDDA_SUBPERIOD_MULTIPLIERS[sub_lord] / 60.0)
            sub_end_day = sub_start_day + sub_duration
            subperiods.append(
                MuddaDashaPeriod(
                    level=2,
                    lord=sub_lord,
                    start_day=sub_start_day,
                    end_day=sub_end_day,
                    duration_days=sub_duration,
                    start_jd=_mudda_jd_for_nominal_day(sub_start_day, year_start_jd, year_end_jd),
                    end_jd=_mudda_jd_for_nominal_day(sub_end_day, year_start_jd, year_end_jd),
                    source_fraction="multiplier_subperiod",
                )
            )
            sub_start_day = sub_end_day
        periods.append(
            MuddaDashaPeriod(
                level=1,
                lord=lord,
                start_day=start_day,
                end_day=end_day,
                duration_days=duration_days,
                start_jd=start_jd,
                end_jd=end_jd,
                source_fraction=source_fraction,
                sub=tuple(subperiods),
            )
        )
        start_day = end_day

    periods.append(
        MuddaDashaPeriod(
            level=1,
            lord=year_ruler,
            start_day=start_day,
            end_day=360.0,
            duration_days=final_elapsed_days,
            start_jd=_mudda_jd_for_nominal_day(start_day, year_start_jd, year_end_jd),
            end_jd=year_end_jd,
            source_fraction="birth_nakshatra_elapsed",
            sub=tuple(
                MuddaDashaPeriod(
                    level=2,
                    lord=sub_lord,
                    start_day=sub_start,
                    end_day=sub_end,
                    duration_days=sub_duration,
                    start_jd=_mudda_jd_for_nominal_day(sub_start, year_start_jd, year_end_jd),
                    end_jd=_mudda_jd_for_nominal_day(sub_end, year_start_jd, year_end_jd),
                    source_fraction="multiplier_subperiod",
                )
                for sub_lord, sub_start, sub_end, sub_duration in _final_mudda_subperiods(
                    year_ruler,
                    start_day,
                    final_elapsed_days,
                )
            ),
        )
    )

    return MuddaDasha(
        school="gauri",
        natal_nakshatra=natal_nakshatra.nakshatra,
        natal_nakshatra_index=natal_nakshatra.nakshatra_index,
        natal_nakshatra_lord=natal_nakshatra.nakshatra_lord,
        birth_elapsed_ghatis=elapsed_ghatis,
        birth_remaining_ghatis=remaining_ghatis,
        year_ruler=year_ruler,
        year_start_jd=year_start_jd,
        year_end_jd=year_end_jd,
        periods=tuple(periods),
    )


def _final_mudda_subperiods(
    lord: str,
    start_day: float,
    duration_days: float,
) -> tuple[tuple[str, float, float, float], ...]:
    subperiods: list[tuple[str, float, float, float]] = []
    sub_start_day = start_day
    for sub_lord in _mudda_sequence_from(lord):
        sub_duration = duration_days * (_MUDDA_SUBPERIOD_MULTIPLIERS[sub_lord] / 60.0)
        sub_end_day = sub_start_day + sub_duration
        subperiods.append((sub_lord, sub_start_day, sub_end_day, sub_duration))
        sub_start_day = sub_end_day
    return tuple(subperiods)


def active_mudda_dasha(
    mudda: MuddaDasha,
    jd_ut: float,
) -> MuddaDashaActivation:
    """Return the active mudda major and subperiod for one JD in the annual year."""

    if jd_ut < mudda.year_start_jd or jd_ut > mudda.year_end_jd:
        raise ValueError(
            f"jd_ut {jd_ut} is outside mudda year [{mudda.year_start_jd}, {mudda.year_end_jd}]"
        )
    major_period = mudda.periods[-1]
    for period in mudda.periods:
        if jd_ut < period.end_jd or abs(jd_ut - period.end_jd) < 1e-12:
            major_period = period
            break
    sub_period = major_period.sub[-1]
    for period in major_period.sub:
        if jd_ut < period.end_jd or abs(jd_ut - period.end_jd) < 1e-12:
            sub_period = period
            break
    return MuddaDashaActivation(
        jd_ut=jd_ut,
        major_period=major_period,
        sub_period=sub_period,
    )


def tasira_periods(
    chart: VarshaphalChart,
    *,
    policy: TajikaAspectPolicy | None = None,
) -> TasiraDasha:
    """
    Compute the annual planetary Tāsīra periods from planets aspecting the year ascendant.

    Source basis admitted here:
    - Hayanaratna 7.3: only planets aspecting the ascendant receive Tāsīra periods.
    - The periods are ordered by strongest aspect first.
    - Nominal annual days are assigned proportionally from a 360-day year.
    - The nominal periods are then mapped onto the actual return-to-return JD span.
    """

    active_policy = TajikaAspectPolicy() if policy is None else policy
    asc = chart.sidereal_houses.asc
    year_start_jd = chart.mudda_dasha.year_start_jd
    year_end_jd = chart.mudda_dasha.year_end_jd
    span_jd = year_end_jd - year_start_jd
    aspect_entries: list[tuple[str, AspectData, float]] = []
    for planet, longitude in chart.sidereal_planets.items():
        candidate = _candidate_asc_aspect(planet, longitude, asc, active_policy)
        if candidate is None:
            continue
        points = _TAJIKA_RELATIONS[candidate.angle][1] * 60.0
        if points <= 0.0:
            continue
        aspect_entries.append((planet, candidate, points))
    if not aspect_entries:
        return TasiraDasha(
            year_start_jd=year_start_jd,
            year_end_jd=year_end_jd,
            periods=(),
        )

    aspect_entries.sort(key=lambda item: (-item[2], item[1].orb, item[0]))
    total_points = sum(points for _planet, _aspect, points in aspect_entries)
    consumed_nominal = 0.0
    consumed_jd = year_start_jd
    periods: list[TasiraPeriod] = []
    for index, (planet, aspect, points) in enumerate(aspect_entries):
        nominal_days = 360.0 * points / total_points
        start_day = consumed_nominal
        end_day = 360.0 if index == len(aspect_entries) - 1 else consumed_nominal + nominal_days
        start_jd = consumed_jd
        if index == len(aspect_entries) - 1:
            end_jd = year_end_jd
        else:
            end_jd = year_start_jd + (end_day / 360.0) * span_jd
        periods.append(
            TasiraPeriod(
                lord=planet,
                aspect_angle=aspect.angle,
                aspect_points=points,
                nominal_days=nominal_days,
                start_day=start_day,
                end_day=end_day,
                start_jd=start_jd,
                end_jd=end_jd,
            )
        )
        consumed_nominal = end_day
        consumed_jd = end_jd
    return TasiraDasha(
        year_start_jd=year_start_jd,
        year_end_jd=year_end_jd,
        periods=tuple(periods),
    )


def active_tasira_period(
    tasira: TasiraDasha,
    jd_ut: float,
) -> TasiraPeriod:
    """Return the active annual Tāsīra period for one JD."""

    if not tasira.periods:
        raise ValueError("tasira.periods is empty")
    if jd_ut < tasira.year_start_jd or jd_ut > tasira.year_end_jd:
        raise ValueError(
            f"jd_ut {jd_ut} is outside tasira year [{tasira.year_start_jd}, {tasira.year_end_jd}]"
        )
    active = tasira.periods[-1]
    for period in tasira.periods:
        if jd_ut < period.end_jd or abs(jd_ut - period.end_jd) < 1e-12:
            active = period
            break
    return active


def _mudda_longitudes(chart: VarshaphalChart) -> dict[str, float]:
    longitudes = dict(chart.sidereal_planets)
    if "Rahu" not in longitudes or "Ketu" not in longitudes:
        node_state = getattr(chart.chart, "nodes", {}).get(Body.TRUE_NODE)
        if node_state is not None:
            rahu = tropical_to_sidereal(
                node_state.longitude,
                chart.jd_ut,
                system=chart.ayanamsa_system,
            )
            longitudes.setdefault("Rahu", rahu)
            longitudes.setdefault("Ketu", _normalize(rahu + 180.0))
    return longitudes


def _mudda_lord_judgement(
    *,
    chart: VarshaphalChart,
    lord: str,
    sidereal_points: dict[str, float],
    year_asc: float,
    jd_ut: float,
    latitude: float | None,
    longitude: float | None,
    planet_speeds: dict[str, float] | None,
) -> tuple[int | None, VarshaphalActorJudgement | None, int, int, str | None]:
    if lord in chart.sidereal_planets:
        actor = _build_actor_judgement(
            actor="mudda_period_lord",
            planet=lord,
            sidereal_planets=chart.sidereal_planets,
            sidereal_houses=chart.sidereal_houses,
            year_asc=year_asc,
            jd_ut=jd_ut,
            latitude=latitude,
            longitude=longitude,
            planet_speeds=planet_speeds,
            yogas=chart.tajika_yogas,
        )
        return (
            actor.house,
            actor,
            actor.supportive_yoga_count,
            actor.obstructive_yoga_count,
            actor.authority,
        )
    if lord in sidereal_points:
        house = house_of(sidereal_points[lord], chart.sidereal_houses)
        supportive, obstructive = _actor_yoga_balance(lord, chart.tajika_yogas)
        return house, None, supportive, obstructive, None
    return None, None, 0, 0, None


def _mudda_relation(
    lord: str,
    counterpart: str,
    yogas: tuple[TajikaYoga, ...],
) -> str:
    for yoga in yogas:
        if {getattr(yoga, "body1", None), getattr(yoga, "body2", None)} != {lord, counterpart}:
            continue
        if yoga.name == "Ithasala":
            return "ithasala"
        if yoga.name == "Isarpha":
            return "isarpha"
    return "none"


def _mudda_result_profile(
    *,
    lord: str,
    governing_year_lord: str,
    year_lagna_lord: str,
    authority: str | None,
    yogas: tuple[TajikaYoga, ...],
) -> MuddaPeriodResultProfile:
    relation_to_varshesha = _mudda_relation(lord, governing_year_lord, yogas)
    relation_to_year_lagna = _mudda_relation(lord, year_lagna_lord, yogas)
    quality = _authority_to_period_quality(authority)
    if lord == governing_year_lord:
        manifestation = "governs_year"
        result_fullness = "governing"
        doctrine = (
            "The ruler of the year is ruler of the period of that year; its "
            "strength therefore governs the major annual result."
        )
    elif relation_to_varshesha == "isarpha" or relation_to_year_lagna == "isarpha":
        manifestation = "blocked"
        result_fullness = "withheld"
        doctrine = (
            "A planet able to give its result does not manifest it in the year "
            "when it forms Isarpha with the ruler of the year or year ascendant."
        )
    elif relation_to_varshesha == "ithasala":
        manifestation = "manifest"
        result_fullness = "full"
        doctrine = (
            "Only the results of a planet forming Ithasala with the ruler of "
            "the year are to be understood as full."
        )
    elif relation_to_year_lagna == "ithasala":
        manifestation = "manifest"
        result_fullness = "supported"
        doctrine = (
            "Results are to be predicted in the opposite of obstruction, and an "
            "Ithasala with the ruler of the year ascendant supports manifestation."
        )
    elif relation_to_varshesha == "none" and relation_to_year_lagna == "none":
        manifestation = "natal_dependent"
        result_fullness = "reduced"
        doctrine = (
            "When there is neither Ithasala nor Isarpha with the operative "
            "annual governors, the result depends chiefly on natal promise."
        )
    else:
        manifestation = "manifest"
        result_fullness = "reduced"
        doctrine = (
            "Period results outside full perfection are present but less than "
            "those perfected by Ithasala with the ruler of the year."
        )
    return MuddaPeriodResultProfile(
        period_lord=lord,
        governing_year_lord=governing_year_lord,
        relation_to_varshesha=relation_to_varshesha,
        relation_to_year_lagna_lord=relation_to_year_lagna,
        strength_quality=quality,
        manifestation=manifestation,
        result_fullness=result_fullness,
        doctrine=doctrine,
    )


def mudda_period_judgement(
    chart: VarshaphalChart,
    jd_ut: float | None = None,
) -> MuddaPeriodJudgement:
    """
    Build the timed annual testimony for the active mudda major and subperiod.

    Primary-source framing:
        Hayanaratna 7.7 states that annual results belong to the ruler of the
        year, while the results of the other planets manifest during the days
        of their respective periods within that year. This layer therefore
        identifies the currently operative mudda rulers and reuses the annual
        strength and yoga surfaces where those rulers are planets.
    """

    focus_jd = chart.jd_ut if jd_ut is None else jd_ut
    activation = active_mudda_dasha(chart.mudda_dasha, focus_jd)
    chart_context = getattr(chart, "chart", None)
    chart_planets = {} if chart_context is None else getattr(chart_context, "planets", {})
    planet_speeds = {
        body: body_state.speed
        for body, body_state in chart_planets.items()
        if hasattr(body_state, "speed")
    }
    sidereal_points = _mudda_longitudes(chart)
    latitude = None if chart_context is None else getattr(chart_context, "latitude", None)
    longitude = None if chart_context is None else getattr(chart_context, "longitude", None)
    year_lagna_lord = _sign_lord(chart.sidereal_houses.asc)
    governing_year_lord = getattr(
        getattr(chart, "varshesha", None),
        "planet",
        chart.mudda_dasha.year_ruler,
    )
    major_house, major_actor, major_supportive, major_obstructive, major_authority = _mudda_lord_judgement(
        chart=chart,
        lord=activation.major_period.lord,
        sidereal_points=sidereal_points,
        year_asc=chart.sidereal_houses.asc,
        jd_ut=focus_jd,
        latitude=latitude,
        longitude=longitude,
        planet_speeds=planet_speeds,
    )
    major_result = _mudda_result_profile(
        lord=activation.major_period.lord,
        governing_year_lord=governing_year_lord,
        year_lagna_lord=year_lagna_lord,
        authority=major_authority,
        yogas=chart.tajika_yogas,
    )
    sub_house, sub_actor, sub_supportive, sub_obstructive, sub_authority = _mudda_lord_judgement(
        chart=chart,
        lord=activation.sub_period.lord,
        sidereal_points=sidereal_points,
        year_asc=chart.sidereal_houses.asc,
        jd_ut=focus_jd,
        latitude=latitude,
        longitude=longitude,
        planet_speeds=planet_speeds,
    )
    sub_result = _mudda_result_profile(
        lord=activation.sub_period.lord,
        governing_year_lord=governing_year_lord,
        year_lagna_lord=year_lagna_lord,
        authority=sub_authority,
        yogas=chart.tajika_yogas,
    )
    return MuddaPeriodJudgement(
        activation=activation,
        major_house=major_house,
        sub_house=sub_house,
        major_actor_judgement=major_actor,
        sub_actor_judgement=sub_actor,
        major_supportive_yoga_count=major_supportive,
        major_obstructive_yoga_count=major_obstructive,
        sub_supportive_yoga_count=sub_supportive,
        sub_obstructive_yoga_count=sub_obstructive,
        major_authority=major_authority,
        sub_authority=sub_authority,
        major_result=major_result,
        sub_result=sub_result,
    )


def _tajika_allowed_orb(
    body1: str,
    body2: str,
    policy: TajikaAspectPolicy,
) -> float:
    if policy.orb_mode == "classical_12_degree":
        return 12.0
    if policy.orb_mode == "deeptamsa_half_sum":
        return (_TAJIKA_DEEPTAMSA[body1] + _TAJIKA_DEEPTAMSA[body2]) / 2.0
    raise ValueError(f"Unsupported Tajika orb_mode: {policy.orb_mode}")


def _tajika_triplicity_contenders(sign_name: str, is_day: bool) -> tuple[str, str]:
    active = _TAJIKA_TRIPLICITY_DAY[sign_name] if is_day else _TAJIKA_TRIPLICITY_NIGHT[sign_name]
    constant = _TAJIKA_TRIPLICITY_CONSTANT[sign_name]
    return active, constant


def _tajika_triplicity_ruler(
    sign_name: str,
    is_day: bool,
    sidereal_planets: dict[str, float],
) -> tuple[str, tuple[str, str]]:
    active, constant = _tajika_triplicity_contenders(sign_name, is_day)
    active_strength = tajika_panchavargi_strength(active, sidereal_planets[active], sidereal_planets)
    constant_strength = tajika_panchavargi_strength(constant, sidereal_planets[constant], sidereal_planets)
    if active_strength.total_score > constant_strength.total_score:
        return active, (active, constant)
    if constant_strength.total_score > active_strength.total_score:
        return constant, (active, constant)
    if _NATURAL_STRENGTH_RANK[active] >= _NATURAL_STRENGTH_RANK[constant]:
        return active, (active, constant)
    return constant, (active, constant)


def _candidate_asc_aspect(
    planet: str,
    longitude: float,
    ascendant: float,
    policy: TajikaAspectPolicy,
) -> AspectData | None:
    allowed = 12.0 if policy.orb_mode == "classical_12_degree" else _TAJIKA_DEEPTAMSA[planet]
    aspects = aspects_to_point(
        ascendant,
        {planet: longitude},
        point_name="Year Asc",
        orbs={angle: allowed for angle in _TAJIKA_MAJORS},
        include_minor=False,
    )
    if not aspects:
        return None
    return min(aspects, key=lambda item: (item.orb, item.angle))


def tajika_aspects(
    planets: dict[str, float],
    planet_speeds: dict[str, float] | None = None,
    policy: TajikaAspectPolicy | None = None,
) -> tuple[TajikaAspect, ...]:
    """
    Compute Tajika annual aspects for the seven classical planets.

    Source basis:
    - Hayanaratna preserves the benefic/malefic sign-aspect classes
      (3/11, 4/10, 5/9, 7, and same-sign conjunction).
    - This implementation formalizes them through degree-based admission on the
      corresponding angular families so near-boundary cases within the admitted
      orb are preserved.
    """

    active_policy = TajikaAspectPolicy() if policy is None else policy
    classical = [
        body for body in ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn")
        if body in planets
    ]
    results: list[TajikaAspect] = []
    for idx, body1 in enumerate(classical):
        for body2 in classical[idx + 1:]:
            allowed = _tajika_allowed_orb(body1, body2, active_policy)
            pair_aspects = aspects_between(
                body1,
                planets[body1],
                body2,
                planets[body2],
                orbs={angle: allowed for angle in _TAJIKA_MAJORS},
                speed_a=None if planet_speeds is None else planet_speeds.get(body1),
                speed_b=None if planet_speeds is None else planet_speeds.get(body2),
            )
            for aspect in pair_aspects:
                if aspect.angle not in _TAJIKA_RELATIONS:
                    continue
                if aspect.angle == 0.0 and not active_policy.include_conjunctions:
                    continue
                relation, strength, effect, benefic = _TAJIKA_RELATIONS[aspect.angle]
                results.append(
                    TajikaAspect(
                        body1=body1,
                        body2=body2,
                        aspect=aspect,
                        relation=relation,
                        relation_strength=strength,
                        effect=effect,
                        is_benefic_relation=benefic,
                        perfects_in_future=aspect.applying,
                        within_effective_orb=aspect.orb <= aspect.allowed_orb,
                    )
                )
    results.sort(key=lambda item: (item.aspect.orb, item.body1, item.body2, item.aspect.angle))
    return tuple(results)


def tajika_yogas(
    aspects: tuple[TajikaAspect, ...] | list[TajikaAspect],
    planets: dict[str, float] | None = None,
    planet_speeds: dict[str, float] | None = None,
    lagna_lord: str | None = None,
    significator: str | None = None,
    sidereal_houses: HouseCusps | None = None,
) -> tuple[TajikaYoga, ...]:
    """
    Classify the currently admitted Tajika yogas over annual aspects.

    The layer now covers the core pair yogas and the first bridge,
    obstruction, rescue, and strengthening yogas built so far.
    """

    results: list[TajikaYoga] = []
    if planets is not None and sidereal_houses is not None:
        occupied_houses = {
            house_of(longitude, sidereal_houses)
            for longitude in planets.values()
        }
        if occupied_houses and occupied_houses.issubset({1, 2, 4, 5, 7, 8, 10, 11}):
            results.append(TajikaYoga(
                name="Ikkavala",
                body1="Year",
                body2="Chart",
                aspect=None,
                favorable=True,
                doctrine="If all the planets are in an angle or a succedent house, that is Ikkavala, causing attainment of dominion and happiness.",
            ))
        if occupied_houses and occupied_houses.issubset({3, 6, 9, 12}):
            results.append(TajikaYoga(
                name="Induvara",
                body1="Year",
                body2="Chart",
                aspect=None,
                favorable=False,
                doctrine="If the planets are in cadent houses, that is Induvara, not praised as good in Tajika.",
            ))
    by_pair: dict[frozenset[str], list[TajikaAspect]] = {}
    for aspect in aspects:
        by_pair.setdefault(frozenset((aspect.body1, aspect.body2)), []).append(aspect)

    for aspect in aspects:
        if aspect.aspect.angle == 0.0:
            continue
        if aspect.aspect.applying is True:
            _append_yoga_unique(results, TajikaYoga(
                name="Ithasala",
                body1=aspect.body1,
                body2=aspect.body2,
                aspect=aspect,
                mediator=None,
                supporting_aspects=(aspect,),
                favorable=True,
                doctrine="Applying Tajika aspect within effective orb; matter moves toward perfection.",
            ))
        elif aspect.aspect.applying is False:
            _append_yoga_unique(results, TajikaYoga(
                name="Isarpha",
                body1=aspect.body1,
                body2=aspect.body2,
                aspect=aspect,
                mediator=None,
                supporting_aspects=(aspect,),
                favorable=False,
                doctrine="Separating Tajika aspect within effective orb; the perfection has passed away.",
            ))

    moon_bridges: dict[frozenset[str], list[TajikaAspect]] = {}
    for candidate in aspects:
        if "Moon" not in {candidate.body1, candidate.body2}:
            continue
        other = candidate.body2 if candidate.body1 == "Moon" else candidate.body1
        for yoga in results:
            if yoga.name != "Ithasala":
                continue
            pair = frozenset((yoga.body1, yoga.body2))
            if other not in pair:
                continue
            moon_bridges.setdefault(pair, []).append(candidate)

    ithasala_pairs = {
        frozenset((yoga.body1, yoga.body2)): yoga
        for yoga in results
        if yoga.name == "Ithasala"
    }

    if planets is not None:
        for pair, yoga in ithasala_pairs.items():
            members = tuple(pair)
            faster = min(members, key=lambda body: _TAJIKA_SPEED_ORDER[body])
            faster_longitude = planets.get(faster)
            if faster_longitude is None:
                continue
            for blocker in ("Mars", "Saturn"):
                if blocker in pair:
                    continue
                blocker_longitude = planets.get(blocker)
                if blocker_longitude is None:
                    continue
                if angular_distance(faster_longitude, blocker_longitude) <= _TAJIKA_DEEPTAMSA[faster]:
                    _append_yoga_unique(results, TajikaYoga(
                        name="Manahoo",
                        body1=yoga.body1,
                        body2=yoga.body2,
                        aspect=yoga.aspect,
                        favorable=False,
                        doctrine="An Ithasala is obstructed because Mars or Saturn falls within the faster planet's Deeptamsa.",
                        mediator=blocker,
                        supporting_aspects=(yoga.aspect,),
                    ))
                    break

        sun_longitude = planets.get("Sun")
        for pair, yoga in ithasala_pairs.items():
            members = tuple(pair)
            for body in members:
                if body == "Sun":
                    continue
                longitude = planets.get(body)
                if longitude is None:
                    continue
                retrograde = (
                    planet_speeds is not None
                    and body in planet_speeds
                    and planet_speeds[body] < 0.0
                )
                solar_orb_contact = (
                    sun_longitude is not None
                    and angular_distance(longitude, sun_longitude) <= _TAJIKA_DEEPTAMSA["Sun"]
                )
                if retrograde or solar_orb_contact:
                    _append_yoga_unique(results, TajikaYoga(
                        name="Radda",
                        body1=yoga.body1,
                        body2=yoga.body2,
                        aspect=yoga.aspect,
                        favorable=False,
                        doctrine="An Ithasala is troubled because one of its planets is retrograde or within the Sun's effective orb.",
                        mediator=body,
                        supporting_aspects=(yoga.aspect,),
                    ))
                    break

        for pair, yoga in ithasala_pairs.items():
            members = tuple(pair)
            faster = min(members, key=lambda body: _TAJIKA_SPEED_ORDER[body])
            slower = max(members, key=lambda body: _TAJIKA_SPEED_ORDER[body])
            slower_longitude = planets.get(slower)
            faster_longitude = planets.get(faster)
            if slower_longitude is None or faster_longitude is None:
                continue
            slower_dignity = vedic_dignity(slower, slower_longitude)
            faster_dignity = vedic_dignity(faster, faster_longitude)
            slower_is_strong = _is_strong_dignity(slower_dignity)
            faster_is_strong = _is_strong_dignity(faster_dignity)
            faster_retrograde = (
                planet_speeds is not None
                and faster in planet_speeds
                and planet_speeds[faster] < 0.0
            )
            faster_solar_orb_contact = (
                sun_longitude is not None
                and faster != "Sun"
                and angular_distance(faster_longitude, sun_longitude) <= _TAJIKA_DEEPTAMSA["Sun"]
            )
            if slower_is_strong and not faster_is_strong and not faster_retrograde and not faster_solar_orb_contact:
                _append_yoga_unique(results, TajikaYoga(
                    name="Dupparikutha",
                    body1=yoga.body1,
                    body2=yoga.body2,
                    aspect=yoga.aspect,
                    favorable=True,
                    doctrine="A strong slow planet forms Ithasala with a weaker fast planet and carries the matter to fulfillment.",
                    mediator=slower,
                    supporting_aspects=(yoga.aspect,),
                ))

        if lagna_lord is not None and significator is not None:
            if lagna_lord in planets and significator in planets and lagna_lord != significator:
                lagna_dignity = vedic_dignity(lagna_lord, planets[lagna_lord])
                significator_dignity = vedic_dignity(significator, planets[significator])
                if _is_weak_dignity(lagna_dignity) and _is_weak_dignity(significator_dignity):
                    for pair, yoga in ithasala_pairs.items():
                        if lagna_lord not in pair and significator not in pair:
                            continue
                        rescue = yoga.body2 if yoga.body1 in {lagna_lord, significator} else yoga.body1
                        if rescue in {lagna_lord, significator}:
                            continue
                        rescue_longitude = planets.get(rescue)
                        if rescue_longitude is None:
                            continue
                        rescue_dignity = vedic_dignity(rescue, rescue_longitude)
                        if not _is_strong_dignity(rescue_dignity):
                            continue
                        _append_yoga_unique(results, TajikaYoga(
                            name="Duttota",
                            body1=lagna_lord,
                            body2=significator,
                            aspect=None,
                            favorable=True,
                            doctrine="Weak lagna lord and significator are rescued because one of them forms Ithasala with a strong third planet.",
                            mediator=rescue,
                            supporting_aspects=(yoga.aspect,),
                        ))
                        break

        for candidate in aspects:
            if candidate.aspect.applying is not True:
                continue
            faster = min((candidate.body1, candidate.body2), key=lambda body: _TAJIKA_SPEED_ORDER[body])
            slower = max((candidate.body1, candidate.body2), key=lambda body: _TAJIKA_SPEED_ORDER[body])
            faster_longitude = planets.get(faster)
            slower_longitude = planets.get(slower)
            if faster_longitude is None or slower_longitude is None:
                continue
            faster_dignity = vedic_dignity(faster, faster_longitude)
            faster_degree = faster_longitude % 30.0
            faster_sign_index = int((faster_longitude % 360.0) // 30.0)
            slower_sign_index = int((slower_longitude % 360.0) // 30.0)
            if (
                _is_strong_dignity(faster_dignity)
                and faster_degree >= 25.0
                and ((faster_sign_index + 1) % 12) == slower_sign_index
            ):
                _append_yoga_unique(results, TajikaYoga(
                    name="Thambira",
                    body1=candidate.body1,
                    body2=candidate.body2,
                    aspect=candidate,
                    favorable=True,
                    doctrine="A strong fast planet near the end of its sign is about to cross into the next sign to complete the applying annual aspect with the slower planet there.",
                    mediator=faster,
                    supporting_aspects=(candidate,),
                ))

    for pair, yoga in ithasala_pairs.items():
        moon_support = tuple(sorted(
            moon_bridges.get(pair, []),
            key=lambda item: (item.aspect.orb, item.body1, item.body2),
        ))
        if moon_support:
            _append_yoga_unique(results, TajikaYoga(
                name="Kamboola",
                body1=yoga.body1,
                body2=yoga.body2,
                aspect=yoga.aspect,
                favorable=True,
                doctrine="An Ithasala is strengthened because the Moon joins it by aspecting one or both planets involved.",
                mediator="Moon",
                supporting_aspects=(yoga.aspect, *moon_support),
            ))

    names = sorted({
        aspect.body1 for aspect in aspects
    } | {
        aspect.body2 for aspect in aspects
    })

    for idx, body1 in enumerate(names):
        for body2 in names[idx + 1:]:
            if frozenset((body1, body2)) in by_pair:
                continue

            moon_aspects = [
                bridge
                for bridge in by_pair.get(frozenset((body1, "Moon")), [])
                + by_pair.get(frozenset((body2, "Moon")), [])
                if bridge.body1 == "Moon" or bridge.body2 == "Moon"
            ]
            if len(moon_aspects) == 2:
                _append_yoga_unique(results, TajikaYoga(
                    name="Nakta",
                    body1=body1,
                    body2=body2,
                    aspect=None,
                    mediator="Moon",
                    supporting_aspects=tuple(sorted(moon_aspects, key=lambda item: (item.aspect.orb, item.body1, item.body2))),
                    favorable=True,
                    doctrine="Two planets lack direct aspect, but the Moon bridges them by aspecting both.",
                ))

            for mediator in sorted(_TAJIKA_BRIDGING_SLOW_PLANETS):
                bridge_a = [
                    candidate for candidate in by_pair.get(frozenset((body1, mediator)), [])
                    if candidate.aspect.applying is True
                ]
                bridge_b = [
                    candidate for candidate in by_pair.get(frozenset((body2, mediator)), [])
                    if candidate.aspect.applying is True
                ]
                if not bridge_a or not bridge_b:
                    continue
                if _TAJIKA_SPEED_ORDER.get(mediator, -1) <= _TAJIKA_SPEED_ORDER.get(body1, -1):
                    continue
                if _TAJIKA_SPEED_ORDER.get(mediator, -1) <= _TAJIKA_SPEED_ORDER.get(body2, -1):
                    continue
                _append_yoga_unique(results, TajikaYoga(
                    name="Yamaya",
                    body1=body1,
                    body2=body2,
                    aspect=None,
                    mediator=mediator,
                    supporting_aspects=(bridge_a[0], bridge_b[0]),
                    favorable=True,
                    doctrine="Two planets lack direct aspect, but both form Ithasala with a slow intermediary.",
                ))
                break
    return tuple(results)


def varshesha(
    *,
    natal_sidereal_asc: float,
    year_asc: float,
    muntha_longitude: float,
    sidereal_planets: dict[str, float],
    is_day: bool,
    policy: TajikaAspectPolicy | None = None,
    annual_yogas: tuple[TajikaYoga, ...] | None = None,
) -> VarsheshaResult:
    """
    Select the ruler of the year from primary-source candidate offices.

    Primary-source candidate offices:
    - ruler of the muntha
    - ruler of the year ascendant
    - triplicity ruler of the year ascendant
    - ruler of the sign occupied by the Sun (day) or Moon (night)
    - ruler of the natal ascendant

    Selection law admitted here:
    - candidates aspecting the year ascendant outrank non-aspecting candidates
    - among aspecting candidates, more candidate claims outrank fewer
    - ties then resolve by tighter aspect to the year ascendant
    - remaining ties use primary-source panchavargi strength
    - exact residual ties fall back to the natural strength order preserved in
      Hayanaratna
    """

    active_policy = TajikaAspectPolicy() if policy is None else policy
    year_sign = sign_of(year_asc)[0]
    luminary = "Sun" if is_day else "Moon"
    triplicity_ruler, triplicity_contenders = _tajika_triplicity_ruler(year_sign, is_day, sidereal_planets)

    role_map: dict[str, list[str]] = {}

    def _claim(planet: str, role: str) -> None:
        role_map.setdefault(planet, []).append(role)

    _claim(_sign_lord(muntha_longitude), "muntha_lord")
    _claim(_sign_lord(year_asc), "year_asc_lord")
    _claim(triplicity_ruler, "year_asc_triplicity_ruler")
    _claim(_sign_lord(sidereal_planets[luminary]), f"{luminary.lower()}_sign_lord")
    _claim(_sign_lord(natal_sidereal_asc), "natal_asc_lord")

    def _make_candidate(planet: str, roles: tuple[str, ...]) -> VarsheshaCandidate:
        longitude = sidereal_planets[planet]
        asc_aspect = _candidate_asc_aspect(planet, longitude, year_asc, active_policy)
        strength = tajika_panchavargi_strength(planet, longitude, sidereal_planets)
        return VarsheshaCandidate(
            planet=planet,
            roles=roles,
            role_count=len(roles),
            longitude=longitude,
            aspects_year_asc=asc_aspect is not None,
            asc_aspect=asc_aspect,
            panchavargi_strength=strength,
        )

    candidates: list[VarsheshaCandidate] = []
    for planet, roles in role_map.items():
        candidates.append(_make_candidate(planet, tuple(sorted(roles))))

    candidates.sort(
        key=lambda item: (
            not item.aspects_year_asc,
            -item.role_count,
            999.0 if item.asc_aspect is None else item.asc_aspect.orb,
            -item.panchavargi_strength.total_score,
            -_NATURAL_STRENGTH_RANK[item.planet],
            item.planet,
        )
    )
    winner = candidates[0]
    selection_basis = "aspect_claims_tajika_strength"

    if winner.planet == "Moon":
        moon_pair = None if annual_yogas is None else next(
            (
                yoga for yoga in annual_yogas
                if yoga.name == "Ithasala" and "Moon" in {yoga.body1, yoga.body2}
            ),
            None,
        )
        if "year_asc_triplicity_ruler" not in winner.roles and moon_pair is not None and moon_pair.aspect is not None:
            counterparty = moon_pair.body2 if moon_pair.body1 == "Moon" else moon_pair.body1
            winner = next(
                (candidate for candidate in candidates if candidate.planet == counterparty),
                _make_candidate(counterparty, ("moon_transfer",)),
            )
            selection_basis = "moon_ithasala_transfer"
        elif "year_asc_triplicity_ruler" not in winner.roles:
            moon_sign_lord = _sign_lord(sidereal_planets["Moon"])
            winner = next(
                (candidate for candidate in candidates if candidate.planet == moon_sign_lord),
                _make_candidate(moon_sign_lord, ("moon_sign_lord_fallback",)),
            )
            selection_basis = "moon_sign_lord_fallback"

    return VarsheshaResult(
        planet=winner.planet,
        roles=winner.roles,
        selection_basis=selection_basis,
        candidates=tuple(candidates),
        asc_aspect=winner.asc_aspect,
        triplicity_contenders=triplicity_contenders,
    )


def varshaphal_judgement_profile(
    chart: VarshaphalChart,
    focus_jd: float | None = None,
) -> VarshaphalJudgementProfile:
    """
    Build the first annual judgement scaffold around the ruler of the year.

    This layer does not attempt a full report. It preserves the primary
    governing testimonies that later interpretation can synthesize.
    """

    supportive = tuple(sorted({yoga.name for yoga in chart.tajika_yogas if yoga.favorable}))
    obstructive = tuple(sorted({yoga.name for yoga in chart.tajika_yogas if not yoga.favorable}))
    varshesha_longitude = chart.sidereal_planets[chart.varshesha.planet]
    varshesha_house = house_of(varshesha_longitude, chart.sidereal_houses)
    varshesha_dignity = vedic_dignity(chart.varshesha.planet, varshesha_longitude)
    chart_context = getattr(chart, "chart", None)
    timed_mudda = None
    if hasattr(chart, "mudda_dasha"):
        timed_mudda = mudda_period_judgement(
            chart,
            jd_ut=chart.jd_ut if focus_jd is None else focus_jd,
        )
    chart_planets = {} if chart_context is None else getattr(chart_context, "planets", {})
    planet_speeds = {
        body: body_state.speed
        for body, body_state in chart_planets.items()
        if hasattr(body_state, "speed")
    }
    year_lagna_lord = _sign_lord(chart.sidereal_houses.asc)
    muntha_lord = getattr(
        chart,
        "muntha_lord",
        getattr(getattr(chart, "muntha_profile", None), "muntha_lord", year_lagna_lord),
    )
    lagna_lord_longitude = chart.sidereal_planets[year_lagna_lord]
    lagna_lord_dignity = vedic_dignity(year_lagna_lord, lagna_lord_longitude)
    year_lagna_lord_strong = _is_strong_dignity(lagna_lord_dignity)
    varshesha_strength = tajika_panchavargi_strength(
        chart.varshesha.planet,
        varshesha_longitude,
        chart.sidereal_planets,
    )
    varshesha_shadbala = tajika_shadbala_profile(
        chart.varshesha.planet,
        sidereal_planets=chart.sidereal_planets,
        sidereal_houses=chart.sidereal_houses,
        year_asc=chart.sidereal_houses.asc,
        jd_ut=getattr(chart, "jd_ut", None),
        latitude=None if chart_context is None else getattr(chart_context, "latitude", None),
        longitude=None if chart_context is None else getattr(chart_context, "longitude", None),
        planet_speeds=planet_speeds,
    )
    muntha_lord_shadbala = tajika_shadbala_profile(
        muntha_lord,
        sidereal_planets=chart.sidereal_planets,
        sidereal_houses=chart.sidereal_houses,
        year_asc=chart.sidereal_houses.asc,
        jd_ut=getattr(chart, "jd_ut", None),
        latitude=None if chart_context is None else getattr(chart_context, "latitude", None),
        longitude=None if chart_context is None else getattr(chart_context, "longitude", None),
        planet_speeds=planet_speeds,
    )
    actor_entries: list[VarshaphalActorJudgement] = []
    for actor_name, planet in (
        ("varshesha", chart.varshesha.planet),
        ("muntha_lord", muntha_lord),
        ("year_lagna_lord", year_lagna_lord),
        ("moon", "Moon"),
    ):
        if planet not in chart.sidereal_planets:
            continue
        actor_entries.append(_build_actor_judgement(
            actor=actor_name,
            planet=planet,
            sidereal_planets=chart.sidereal_planets,
            sidereal_houses=chart.sidereal_houses,
            year_asc=chart.sidereal_houses.asc,
            jd_ut=getattr(chart, "jd_ut", None),
            latitude=None if chart_context is None else getattr(chart_context, "latitude", None),
            longitude=None if chart_context is None else getattr(chart_context, "longitude", None),
            planet_speeds=planet_speeds,
            yogas=chart.tajika_yogas,
        ))
    actor_rankings = tuple(sorted(actor_entries, key=lambda item: (-item.authority_score, item.actor, item.planet)))
    sahams = tuple(getattr(chart, "sahams", ()))
    key_saham_rankings = tuple(sorted(
        (
            _build_saham_judgement(
                saham=saham,
                sidereal_planets=chart.sidereal_planets,
                sidereal_houses=chart.sidereal_houses,
                year_asc=chart.sidereal_houses.asc,
                jd_ut=getattr(chart, "jd_ut", None),
                latitude=None if chart_context is None else getattr(chart_context, "latitude", None),
                longitude=None if chart_context is None else getattr(chart_context, "longitude", None),
                planet_speeds=planet_speeds,
            )
            for saham in sahams
        ),
        key=lambda item: (-item.relevance_score, item.saham_name),
    )[:5])

    relation = next(
        (
            yoga.name for yoga in chart.tajika_yogas
            if {yoga.body1, yoga.body2} == {chart.varshesha.planet, year_lagna_lord}
            and yoga.name in {"Ithasala", "Isarpha"}
        ),
        None,
    )
    if relation == "Ithasala" or year_lagna_lord_strong:
        authority = "supportive"
    elif relation == "Isarpha" or _is_weak_dignity(lagna_lord_dignity):
        authority = "adverse"
    else:
        authority = "mixed"
    timed_testimony: list[str] = []
    if timed_mudda is not None:
        timed_testimony.append(
            f"mudda_major:{timed_mudda.activation.major_period.lord}:{timed_mudda.major_result.result_fullness}"
        )
        timed_testimony.append(
            f"mudda_sub:{timed_mudda.activation.sub_period.lord}:{timed_mudda.sub_result.result_fullness}"
        )

    strongest_testimonies = tuple(
        [f"{actor.actor}:{actor.planet}" for actor in actor_rankings[:3]]
        + [f"saham:{saham.saham_name}" for saham in key_saham_rankings[:2]]
        + timed_testimony
    )
    positive_total = sum(actor.authority_score for actor in actor_rankings if actor.authority in {"strong", "supportive"})
    strained_total = sum(actor.authority_score for actor in actor_rankings if actor.authority == "strained")
    if positive_total > strained_total + 80.0:
        yearly_strength_balance = "supportive"
    elif strained_total > positive_total:
        yearly_strength_balance = "adverse"
    else:
        yearly_strength_balance = "mixed"

    return VarshaphalJudgementProfile(
        varshesha=chart.varshesha,
        supportive_yogas=supportive,
        obstructive_yogas=obstructive,
        varshesha_house=varshesha_house,
        varshesha_dignity=varshesha_dignity,
        varshesha_strength=varshesha_strength,
        varshesha_shadbala=varshesha_shadbala,
        muntha_lord_shadbala=muntha_lord_shadbala,
        year_lagna_lord=year_lagna_lord,
        year_lagna_lord_strong=year_lagna_lord_strong,
        actor_rankings=actor_rankings,
        key_saham_rankings=key_saham_rankings,
        mudda_period=timed_mudda,
        strongest_testimonies=strongest_testimonies,
        yearly_strength_balance=yearly_strength_balance,
        ascendant_authority_indication=authority,
    )


def varshaphal_topic_judgements(
    chart: VarshaphalChart,
    profile: VarshaphalJudgementProfile | None = None,
    saham_priorities: tuple[VarshaphalSahamPriority, ...] | None = None,
    disregarded_sahams: tuple[VarshaphalSahamPriority, ...] | None = None,
) -> tuple[VarshaphalTopicJudgement, ...]:
    """
    Build the first named annual result channels for major life topics.

    Primary-source basis admitted here:
        - Sahama-specific annual relevance from chapter 4.
        - Strong ruler-of-house testimony manifests when it has itthaśāla with
          the ruler of the year or ascendant of the year.
        - Blockage by īsarāpha and period obstruction remains adverse.
    """

    active_profile = chart.judgement if profile is None and getattr(chart, "judgement", None) is not None else (
        varshaphal_judgement_profile(chart) if profile is None else profile
    )
    existing_priorities = (
        () if saham_priorities is None else saham_priorities
    ) + (
        () if disregarded_sahams is None else disregarded_sahams
    )
    saham_priority_map = {item.saham_name: item for item in existing_priorities}
    if not saham_priority_map:
        temp_year = varshaphal_year_judgement(chart)
        saham_priority_map = {
            item.saham_name: item
            for item in temp_year.prioritized_sahams + temp_year.disregarded_sahams
        }

    timed_period = active_profile.mudda_period
    yogas = getattr(chart, "tajika_yogas", ())
    topic_results: list[VarshaphalTopicJudgement] = []
    for topic, (saham_name, house_numbers, polarity) in _VARSHA_TOPIC_MAP.items():
        saham_priority = saham_priority_map.get(saham_name)
        house_rulers = _topic_house_rulers(house_numbers, chart.sidereal_houses)
        supportive, obstructive = _supports_topic_from_varshesha(
            varshesha_planet=chart.varshesha.planet,
            rulers=house_rulers,
            yogas=yogas,
        )
        timed_activation = "neutral"
        if timed_period is not None and (
            timed_period.activation.major_period.lord in house_rulers
            or timed_period.activation.sub_period.lord in house_rulers
            or (saham_priority is not None and timed_period.activation.major_period.lord == saham_priority.annual_judgement.ruler)
            or (saham_priority is not None and timed_period.activation.sub_period.lord == saham_priority.annual_judgement.ruler)
        ):
            timed_activation = "active"
        if timed_period is not None and timed_period.major_result.manifestation == "blocked":
            timed_activation = "blocked"
        emphasis_score = _topic_emphasis_score(
            saham_priority=saham_priority,
            supportive=supportive,
            obstructive=obstructive,
            timed_activation=timed_activation,
        )
        doctrine_basis, doctrine_bonus, constructive_doctrine, adverse_doctrine, mitigated = _topic_rulebook_adjustment(
            topic=topic,
            chart=chart,
            profile=active_profile,
            saham_priority=saham_priority,
            house_rulers=house_rulers,
            house_numbers=house_numbers,
            yogas=yogas,
            timed_activation=timed_activation,
        )
        emphasis_score += doctrine_bonus

        basis = [
            f"saham:{saham_name}",
            f"polarity:{polarity}",
            f"houses:{','.join(str(n) for n in house_numbers)}",
            f"house_rulers:{','.join(house_rulers)}",
            f"varshesha_support:{supportive}",
            f"varshesha_obstruction:{obstructive}",
            f"timed_activation:{timed_activation}",
            f"emphasis_score:{emphasis_score}",
        ]
        if saham_priority is not None:
            basis.append(f"saham_priority:{saham_priority.priority}")
        basis.extend(doctrine_basis)

        if saham_priority is not None and not saham_priority.is_considered:
            judgement = "background"
        else:
            if polarity == "adverse":
                if mitigated and not adverse_doctrine and timed_activation != "active":
                    judgement = "conditional"
                elif adverse_doctrine or obstructive or timed_activation in {"active", "blocked"}:
                    judgement = "foreground"
                elif saham_priority is not None and saham_priority.priority == "high":
                    judgement = "activated"
                else:
                    judgement = "conditional"
            elif obstructive or adverse_doctrine or timed_activation == "blocked":
                judgement = "obstructed"
            elif (supportive or constructive_doctrine) and (saham_priority is None or saham_priority.priority == "high"):
                judgement = "foreground"
            elif saham_priority is not None and saham_priority.priority == "high":
                judgement = "activated"
            else:
                judgement = "conditional"

        topic_results.append(
            VarshaphalTopicJudgement(
                topic=topic,
                saham_name=saham_name,
                polarity=polarity,
                saham_priority=saham_priority,
                house_numbers=house_numbers,
                house_rulers=house_rulers,
                supportive_relation_to_varshesha=supportive,
                obstructive_relation_to_varshesha=obstructive,
                timed_activation=timed_activation,
                emphasis_score=emphasis_score,
                judgement=judgement,
                basis=tuple(basis),
            )
        )
    return tuple(sorted(topic_results, key=lambda item: (-item.emphasis_score, item.topic)))


def varshaphal_year_judgement(
    chart: VarshaphalChart,
    focus_jd: float | None = None,
) -> VarshaphalYearJudgement:
    """
    Build the first consolidated annual verdict surface for one Varshaphal year.

    This groups the already-derived annual governors, key sahams, Mudda timing,
    and yoga balance into one stable object for downstream interpretation.
    """

    profile = (
        chart.judgement
        if focus_jd is None and getattr(chart, "judgement", None) is not None
        else varshaphal_judgement_profile(chart, focus_jd=focus_jd)
    )
    actor_rankings = profile.actor_rankings
    dominant_governor = actor_rankings[0] if actor_rankings else None
    supporting_governors = tuple(
        actor for actor in actor_rankings
        if actor.authority in {"strong", "supportive"}
    )
    strained_governors = tuple(
        actor for actor in actor_rankings
        if actor.authority == "strained"
    )
    natal_chart_context = getattr(chart, "natal_chart", None)
    natal_planet_speeds = {
        body: body_state.speed
        for body, body_state in getattr(natal_chart_context, "planets", {}).items()
        if hasattr(body_state, "speed")
    }
    natal_jd = getattr(chart, "birth_jd", getattr(chart, "jd_ut", None))
    natal_saham_lookup = {saham.name: saham for saham in getattr(chart, "natal_sahams", ())}
    saham_priorities = tuple(sorted(
        (
            _saham_priority(
                annual_judgement=annual,
                natal_judgement=_build_saham_judgement(
                    saham=natal_saham_lookup[annual.saham_name],
                    sidereal_planets=chart.natal_sidereal_planets,
                    sidereal_houses=chart.natal_sidereal_houses,
                    year_asc=chart.natal_sidereal_houses.asc,
                    jd_ut=natal_jd,
                    latitude=None if natal_chart_context is None else getattr(natal_chart_context, "latitude", None),
                    longitude=None if natal_chart_context is None else getattr(natal_chart_context, "longitude", None),
                    planet_speeds=natal_planet_speeds,
                ) if len(chart.natal_sidereal_planets) >= 7 else _fallback_saham_judgement(
                    natal_saham_lookup[annual.saham_name],
                    chart.natal_sidereal_houses,
                    chart.natal_sidereal_planets,
                ),
            )
            for annual in profile.key_saham_rankings
            if annual.saham_name in natal_saham_lookup
        ),
        key=lambda item: (
            item.priority != "high",
            item.priority == "disregarded",
            -item.annual_judgement.relevance_score,
            item.saham_name,
        ),
    ))
    prioritized_sahams = tuple(item for item in saham_priorities if item.is_considered)
    disregarded_sahams = tuple(item for item in saham_priorities if not item.is_considered)
    topic_judgements = varshaphal_topic_judgements(
        chart,
        profile=profile,
        saham_priorities=prioritized_sahams,
        disregarded_sahams=disregarded_sahams,
    )
    foreground_topics = tuple(
        topic for topic in topic_judgements
        if topic.judgement in {"foreground", "activated"}
    )
    obstructed_topics = tuple(
        topic for topic in topic_judgements
        if topic.judgement == "obstructed"
    )
    background_topics = tuple(
        topic for topic in topic_judgements
        if topic.judgement == "background"
    )
    timed_period = profile.mudda_period
    decisive_testimonies = list(profile.strongest_testimonies)
    verdict_basis: list[str] = [
        f"strength_balance:{profile.yearly_strength_balance}",
        f"ascendant_authority:{profile.ascendant_authority_indication}",
    ]
    if dominant_governor is not None:
        verdict_basis.append(
            f"dominant_governor:{dominant_governor.actor}:{dominant_governor.planet}:{dominant_governor.authority}"
        )
    if timed_period is not None:
        verdict_basis.append(
            f"mudda_major:{timed_period.activation.major_period.lord}:{timed_period.major_result.result_fullness}"
        )
        verdict_basis.append(
            f"mudda_sub:{timed_period.activation.sub_period.lord}:{timed_period.sub_result.result_fullness}"
        )
        if timed_period.major_result.manifestation == "blocked" or timed_period.sub_result.manifestation == "blocked":
            decisive_testimonies.append("mudda_blockage")
    if profile.obstructive_yogas:
        verdict_basis.append(f"obstructive_yogas:{','.join(profile.obstructive_yogas)}")
    if profile.supportive_yogas:
        verdict_basis.append(f"supportive_yogas:{','.join(profile.supportive_yogas)}")
    if prioritized_sahams:
        verdict_basis.append(
            "prioritized_sahams:" + ",".join(
                f"{item.saham_name}:{item.priority}" for item in prioritized_sahams[:3]
            )
        )
    if disregarded_sahams:
        verdict_basis.append(
            "disregarded_sahams:" + ",".join(item.saham_name for item in disregarded_sahams[:3])
        )
    verdict_basis.append(
        "topics:" + ",".join(f"{item.topic}:{item.judgement}" for item in topic_judgements)
    )

    varshesha_natal_longitude = chart.natal_sidereal_planets.get(chart.varshesha.planet)
    varshesha_natal_house = None if varshesha_natal_longitude is None else house_of(
        varshesha_natal_longitude,
        chart.natal_sidereal_houses,
    )
    varshesha_dual_affliction = (
        dominant_governor is not None
        and dominant_governor.authority == "strained"
        and varshesha_natal_house in {6, 8, 12}
        and profile.varshesha_house in {6, 8, 12}
    )

    if varshesha_dual_affliction:
        final_verdict = "adverse"
        conflict_resolution = "afflicted_year_ruler_overrides_support"
    elif (
        timed_period is not None
        and timed_period.major_result.manifestation == "blocked"
        and dominant_governor is not None
        and dominant_governor.authority not in {"strong", "supportive"}
    ):
        final_verdict = "adverse"
        conflict_resolution = "blocked_mudda_major_overrides_mixed_governance"
    elif (
        timed_period is not None
        and timed_period.major_result.manifestation == "blocked"
        and prioritized_sahams
    ):
        final_verdict = "mixed"
        conflict_resolution = "strong_sahams_temper_blocked_mudda_major"
    elif (
        profile.yearly_strength_balance == "supportive"
        and profile.ascendant_authority_indication == "supportive"
        and (timed_period is None or timed_period.major_result.manifestation != "blocked")
    ):
        final_verdict = "supportive"
        conflict_resolution = "governors_and_timing_agree"
    elif (
        profile.yearly_strength_balance == "adverse"
        or profile.ascendant_authority_indication == "adverse"
        or (timed_period is not None and timed_period.major_result.manifestation == "blocked")
    ):
        final_verdict = "adverse"
        conflict_resolution = "obstruction_outweighs_support"
    else:
        final_verdict = "mixed"
        conflict_resolution = "mixed_testimonies_preserved"

    return VarshaphalYearJudgement(
        profile=profile,
        dominant_governor=dominant_governor,
        supporting_governors=supporting_governors,
        strained_governors=strained_governors,
        topics=topic_judgements,
        foreground_topics=foreground_topics,
        obstructed_topics=obstructed_topics,
        background_topics=background_topics,
        prioritized_sahams=prioritized_sahams,
        disregarded_sahams=disregarded_sahams,
        key_sahams=profile.key_saham_rankings,
        timed_period=timed_period,
        supportive_yogas=profile.supportive_yogas,
        obstructive_yogas=profile.obstructive_yogas,
        decisive_testimonies=tuple(decisive_testimonies),
        final_verdict=final_verdict,
        conflict_resolution=conflict_resolution,
        verdict_basis=tuple(verdict_basis),
    )


def varshaphal_topic_windows(
    chart: VarshaphalChart,
    topic: str,
) -> tuple[VarshaphalTopicWindow, ...]:
    """Return timed Mudda and Tāsīra activation windows for one named annual topic."""

    if topic not in _VARSHA_TOPIC_MAP:
        raise KeyError(f"Unknown Varshaphal topic: {topic}")
    saham_name, house_numbers, _polarity = _VARSHA_TOPIC_MAP[topic]
    house_rulers = _topic_house_rulers(house_numbers, chart.sidereal_houses)
    annual_saham_lookup = {saham.name: saham for saham in chart.sahams}
    saham_ruler = annual_saham_lookup[saham_name].ruler if saham_name in annual_saham_lookup else None
    windows: list[VarshaphalTopicWindow] = []
    for major in chart.mudda_dasha.periods:
        for sub in major.sub:
            activation_kind = "background"
            if major.lord in house_rulers or sub.lord in house_rulers:
                activation_kind = "house_ruler"
            if saham_ruler is not None and (major.lord == saham_ruler or sub.lord == saham_ruler):
                activation_kind = "saham_ruler"
            windows.append(VarshaphalTopicWindow(
                topic=topic,
                start_jd=sub.start_jd,
                end_jd=sub.end_jd,
                source="mudda",
                major_lord=major.lord,
                sub_lord=sub.lord,
                activation_kind=activation_kind,
                basis=(
                    f"saham:{saham_name}",
                    f"major:{major.lord}",
                    f"sub:{sub.lord}",
                ),
            ))
    if hasattr(chart, "tasira_dasha"):
        for period in chart.tasira_dasha.periods:
            activation_kind = "background"
            if period.lord in house_rulers:
                activation_kind = "tasira_house_ruler"
            if saham_ruler is not None and period.lord == saham_ruler:
                activation_kind = "tasira_saham_ruler"
            windows.append(VarshaphalTopicWindow(
                topic=topic,
                start_jd=period.start_jd,
                end_jd=period.end_jd,
                source="tasira",
                major_lord=period.lord,
                sub_lord=period.lord,
                activation_kind=activation_kind,
                basis=(
                    f"saham:{saham_name}",
                    f"tasira:{period.lord}",
                    f"aspect_points:{period.aspect_points}",
                ),
            ))
    return tuple(window for window in windows if window.activation_kind != "background")


def varshaphal_year_summary(
    chart: VarshaphalChart,
    year_judgement: VarshaphalYearJudgement | None = None,
) -> VarshaphalYearSummary:
    """Build the first structured annual summary/report surface."""

    active_year = chart.year_judgement if year_judgement is None and getattr(chart, "year_judgement", None) is not None else (
        varshaphal_year_judgement(chart) if year_judgement is None else year_judgement
    )
    timed_highlights: list[str] = []
    for topic in active_year.foreground_topics[:4]:
        windows = varshaphal_topic_windows(chart, topic.topic)
        if not windows:
            continue
        first = windows[0]
        timed_highlights.append(
            f"{topic.topic}:{first.source}:{first.major_lord}/{first.sub_lord}:{first.activation_kind}"
        )
    dominant_governor = None if active_year.dominant_governor is None else f"{active_year.dominant_governor.actor}:{active_year.dominant_governor.planet}"
    return VarshaphalYearSummary(
        yearly_tone=active_year.final_verdict,
        dominant_governor=dominant_governor,
        foreground_topics=tuple(topic.topic for topic in active_year.foreground_topics),
        obstructed_topics=tuple(topic.topic for topic in active_year.obstructed_topics),
        background_topics=tuple(topic.topic for topic in active_year.background_topics),
        timed_highlights=tuple(timed_highlights),
        strongest_testimonies=active_year.decisive_testimonies,
        narrative_basis=active_year.verdict_basis,
    )


def muntha_condition_profile(
    muntha_longitude: float,
    muntha_house: int,
    muntha_lord: str,
    sidereal_planets: dict[str, float],
    sidereal_houses: HouseCusps,
) -> MunthaConditionProfile:
    """Build a structural condition profile for Muntha and its lord."""

    if muntha_lord not in sidereal_planets:
        raise KeyError(f"Muntha lord {muntha_lord!r} not present in sidereal_planets")
    lord_longitude = sidereal_planets[muntha_lord]
    lord_house = house_of(lord_longitude, sidereal_houses)
    relative_house = ((lord_house - muntha_house) % 12) + 1
    dignity = vedic_dignity(muntha_lord, lord_longitude)
    dignity_profile = vedic_dignity_condition_profile(dignity)
    return MunthaConditionProfile(
        muntha_longitude=muntha_longitude,
        muntha_house=muntha_house,
        muntha_sign=sign_of(muntha_longitude)[0],
        muntha_lord=muntha_lord,
        muntha_lord_longitude=lord_longitude,
        muntha_lord_house=lord_house,
        muntha_lord_sign=sign_of(lord_longitude)[0],
        muntha_lord_dignity=dignity,
        muntha_lord_dignity_profile=dignity_profile,
        muntha_lord_house_from_muntha=relative_house,
        lord_in_kendra=lord_house in {1, 4, 7, 10},
        lord_in_trikona=lord_house in {1, 5, 9},
        lord_in_dusthana=lord_house in {6, 8, 12},
        lord_in_upachaya=lord_house in {3, 6, 10, 11},
        lord_is_strong=dignity_profile.tier == DignityTier.STRONG,
        lord_is_weak=dignity_profile.tier == DignityTier.WEAK,
    )


def _resolve_saham_operand(
    operand: str,
    *,
    ascendant: float,
    planets: dict[str, float],
    house_cusps: HouseCusps,
    derived: dict[str, VarshaphalSaham],
) -> float:
    if operand == "Asc":
        return ascendant
    if operand == "Asc Lord":
        return planets[_sign_lord(ascendant)]
    if operand == "2nd House Cusp":
        return house_cusps.cusps[1]
    if operand == "6th House Cusp":
        return house_cusps.cusps[5]
    if operand == "8th House Cusp":
        return house_cusps.cusps[7]
    if operand == "9th House Cusp":
        return house_cusps.cusps[8]
    if operand == "2nd Lord":
        return planets[_sign_lord(house_cusps.cusps[1])]
    if operand == "9th Lord":
        return planets[_sign_lord(house_cusps.cusps[8])]
    if operand == "Sun-sign Lord":
        return planets[_sign_lord(planets["Sun"])]
    if operand == "15 Cancer":
        return 105.0
    if operand in derived:
        return derived[operand].longitude
    if operand in planets:
        return planets[operand]
    raise KeyError(f"Unsupported Varshaphal Saham operand: {operand}")


def _compute_saham(
    definition: VarshaphalSahamDefinition,
    *,
    ascendant: float,
    planets: dict[str, float],
    house_cusps: HouseCusps,
    is_day: bool,
    derived: dict[str, VarshaphalSaham],
) -> VarshaphalSaham:
    minuend_name = definition.minuend
    subtrahend_name = definition.subtrahend
    reversed_for_night = False
    if not is_day and definition.reverse_at_night:
        minuend_name, subtrahend_name = subtrahend_name, minuend_name
        reversed_for_night = True

    minuend = _resolve_saham_operand(
        minuend_name,
        ascendant=ascendant,
        planets=planets,
        house_cusps=house_cusps,
        derived=derived,
    )
    subtrahend = _resolve_saham_operand(
        subtrahend_name,
        ascendant=ascendant,
        planets=planets,
        house_cusps=house_cusps,
        derived=derived,
    )
    addend = _resolve_saham_operand(
        definition.addend,
        ascendant=ascendant,
        planets=planets,
        house_cusps=house_cusps,
        derived=derived,
    )
    longitude = _normalize(minuend - subtrahend + addend)
    correction_applied = not _arc_contains(subtrahend, minuend, ascendant)
    if correction_applied:
        longitude = _normalize(longitude + 30.0)

    house = house_of(longitude, house_cusps)
    ruler = _sign_lord(longitude)
    return VarshaphalSaham(
        name=definition.name,
        longitude=longitude,
        house=house,
        ruler=ruler,
        minuend=minuend_name,
        subtrahend=subtrahend_name,
        addend=definition.addend,
        reversed_for_night=reversed_for_night,
        correction_applied=correction_applied,
    )


def varshaphal_sahams(
    ascendant: float,
    planets: dict[str, float],
    house_cusps: HouseCusps,
    is_day: bool,
) -> tuple[VarshaphalSaham, ...]:
    """Compute the documented Varshaphal Saham set for one annual chart."""

    derived: dict[str, VarshaphalSaham] = {}
    for definition in _SAHAM_DEFINITIONS:
        saham = _compute_saham(
            definition,
            ascendant=ascendant,
            planets=planets,
            house_cusps=house_cusps,
            is_day=is_day,
            derived=derived,
        )
        derived[saham.name] = saham
    return tuple(derived[name] for name in derived)


def build_varshaphal_chart(
    birth_jd: float,
    natal_latitude: float,
    natal_longitude: float,
    year: int,
    latitude: float,
    longitude: float,
    ayanamsa_system: str | UserDefinedAyanamsa = Ayanamsa.LAHIRI,
    house_system: str = HouseSystem.PLACIDUS,
    bodies: list[str] | None = None,
    reader: SpkReader | None = None,
    return_policy: TransitComputationPolicy | None = None,
    house_policy: HousePolicy | None = None,
) -> VarshaphalChart:
    """
    Build a structured Varshaphal annual-return vessel with Muntha, Sahams,
    and Gauri mudda dasha.

    The low-level annual chart remains available through
    ``moira.transits.varshaphal_chart()``. This higher layer adds Tajika
    annual-return doctrine objects including Muntha, Sahams, and the current
    annual aspect/yoga layer.
    """
    years_elapsed = year - calendar_datetime_from_jd(birth_jd).year
    if years_elapsed < 0:
        raise ValueError(
            f"Varshaphal year {year} precedes birth year for JD {birth_jd}"
        )

    jd_return = _varshaphal_jd(
        birth_jd,
        year,
        ayanamsa_system=ayanamsa_system,
        reader=reader,
        policy=return_policy,
    )
    chart = _varshaphal_chart(
        birth_jd,
        year,
        latitude,
        longitude,
        ayanamsa_system=ayanamsa_system,
        house_system=house_system,
        bodies=bodies,
        reader=reader,
        return_policy=return_policy,
        house_policy=house_policy,
    )

    return_ayan = ayanamsa(jd_return, ayanamsa_system)
    sidereal_houses = calculate_houses(
        jd_return,
        latitude,
        longitude,
        house_system,
        policy=house_policy,
        ayanamsa_offset=return_ayan,
    )
    sidereal_planets = {
        name: tropical_to_sidereal(planet.longitude, jd_return, system=ayanamsa_system)
        for name, planet in chart.planets.items()
    }

    natal_chart = create_chart(
        birth_jd,
        natal_latitude,
        natal_longitude,
        house_system=house_system,
        bodies=bodies,
        reader=reader,
        policy=house_policy,
    )
    natal_ayan = ayanamsa(birth_jd, ayanamsa_system)
    natal_sidereal_houses = calculate_houses(
        birth_jd,
        natal_latitude,
        natal_longitude,
        house_system,
        policy=house_policy,
        ayanamsa_offset=natal_ayan,
    )
    natal_sidereal_planets = {
        name: tropical_to_sidereal(planet.longitude, birth_jd, system=ayanamsa_system)
        for name, planet in natal_chart.planets.items()
    }
    natal_sidereal_asc = natal_sidereal_houses.asc
    natal_sahams = varshaphal_sahams(
        natal_sidereal_houses.asc,
        natal_sidereal_planets,
        natal_sidereal_houses,
        natal_chart.is_day,
    )
    muntha_longitude = muntha(natal_sidereal_asc, years_elapsed)
    muntha_house = house_of(muntha_longitude, sidereal_houses)
    muntha_lord = _sign_lord(muntha_longitude)
    muntha_profile = muntha_condition_profile(
        muntha_longitude,
        muntha_house,
        muntha_lord,
        sidereal_planets,
        sidereal_houses,
    )
    sahams = varshaphal_sahams(
        sidereal_houses.asc,
        sidereal_planets,
        sidereal_houses,
        chart.is_day,
    )
    planet_speeds = {name: planet.speed for name, planet in chart.planets.items()}
    annual_aspects = tajika_aspects(sidereal_planets, planet_speeds=planet_speeds)
    annual_yogas = tajika_yogas(
        annual_aspects,
        sidereal_planets,
        planet_speeds,
        sidereal_houses=sidereal_houses,
    )
    annual_varshesha = varshesha(
        natal_sidereal_asc=natal_sidereal_asc,
        year_asc=sidereal_houses.asc,
        muntha_longitude=muntha_longitude,
        sidereal_planets=sidereal_planets,
        is_day=chart.is_day,
        annual_yogas=annual_yogas,
    )
    annual_mudda_dasha = mudda_dasha(
        birth_jd,
        year,
        ayanamsa_system=ayanamsa_system,
        reader=reader,
        return_policy=return_policy,
    )
    result = VarshaphalChart(
        birth_jd=birth_jd,
        return_year=year,
        years_elapsed=years_elapsed,
        jd_ut=jd_return,
        ayanamsa_system=ayanamsa_system,
        chart=chart,
        natal_chart=natal_chart,
        sidereal_houses=sidereal_houses,
        sidereal_planets=sidereal_planets,
        natal_sidereal_houses=natal_sidereal_houses,
        natal_sidereal_planets=natal_sidereal_planets,
        natal_sidereal_asc=natal_sidereal_asc,
        muntha_longitude=muntha_longitude,
        muntha_house=muntha_house,
        muntha_lord=muntha_lord,
        muntha_profile=muntha_profile,
        varshesha=annual_varshesha,
        judgement=None,
        year_judgement=None,
        tajika_aspects=annual_aspects,
        tajika_yogas=annual_yogas,
        sahams=sahams,
        natal_sahams=natal_sahams,
        mudda_dasha=annual_mudda_dasha,
        tasira_dasha=TasiraDasha(
            year_start_jd=annual_mudda_dasha.year_start_jd,
            year_end_jd=annual_mudda_dasha.year_end_jd,
            periods=(),
        ),
    )
    object.__setattr__(result, "tasira_dasha", tasira_periods(result))
    object.__setattr__(result, "judgement", varshaphal_judgement_profile(result))
    object.__setattr__(result, "year_judgement", varshaphal_year_judgement(result))
    return result
