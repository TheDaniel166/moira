"""
Moira — Timelords Engine
Governs the timelord Engine surfaces for Firdaria, Zodiacal Releasing, and the
constitutional Decennials subsystem: sequence construction, hierarchical
grouping, active-period lookup, condition profiles, aggregate profiles, and
network surfaces.

Boundary: owns Firdaria sequence arithmetic and sub-period allocation,
Decennials major/sub-period allocation, Zodiacal Releasing recursion and
angularity classification, timelord policy vessels, result vessels, and
relational vessels. Delegates domicile ruler lookup to moira.profections.

Import-time side effects: None

External dependencies:
    - dataclasses for structured data definitions
    - datetime for temporal operations
    - math module for mathematical operations
    - moira.constants for sign definitions
    - moira.julian for calendar conversion
    - moira.profections for domicile rulers

Public surface:
    FIRDARIA_DIURNAL, FIRDARIA_NOCTURNAL, FIRDARIA_NOCTURNAL_BONATTI,
    CHALDEAN_ORDER, MINOR_YEARS, FirdarSequenceKind,
    TimelordEvaluationStatus, DecennialSequenceKind, DecennialTimeBasis,
    DecennialSequenceBodyTruth, DecennialSequenceAssemblyTruth,
    ZRAngularityClass, ZRFortuneAngularityTruth,
    FirdarYearPolicy, DecennialPolicy, ZRYearPolicy, TimelordComputationPolicy,
    DEFAULT_TIMELORD_POLICY, FirdarPeriod, DecennialPeriod, ReleasingPeriod,
    FirdarMajorGroup, DecennialMajorGroup, DecennialPeriodGroup, ZRPeriodGroup,
    FirdarConditionProfile, DecennialConditionProfile, ZRConditionProfile,
    FirdarSequenceProfile, DecennialSequenceProfile, ZRSequenceProfile,
    FirdarActivePair, DecennialActivePair, DecennialActivePath, ZRLevelPair,
    firdaria, current_firdaria, decennial_sequence_truth, decennials,
    current_decennials, zr_fortune_angularity_truth, zodiacal_releasing,
    current_releasing, group_firdaria, group_decennials, group_releasing,
    firdar_condition_profile, decennial_condition_profile, zr_condition_profile,
    firdar_sequence_profile, decennial_sequence_profile, zr_sequence_profile,
    firdar_active_pair, decennial_active_pair, decennial_active_path, zr_level_pair,
    validate_firdaria_output, validate_decennials_output,
    validate_releasing_output
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
import math

from .constants import SIGNS, sign_of
from .julian import CalendarDateTime, calendar_datetime_from_jd, datetime_from_jd
from .profections import DOMICILE_RULERS

# ---------------------------------------------------------------------------
# Phase 12 — Public API Curation
# ---------------------------------------------------------------------------

__all__ = [
    # Sequence constants
    "FIRDARIA_DIURNAL",
    "FIRDARIA_NOCTURNAL",
    "FIRDARIA_NOCTURNAL_BONATTI",
    "CHALDEAN_ORDER",
    "MINOR_YEARS",
    # Classification namespaces
    "FirdarSequenceKind",
    "TimelordEvaluationStatus",
    "DecennialSequenceKind",
    "DecennialTimeBasis",
    "DecennialSequenceBodyTruth",
    "DecennialSequenceAssemblyTruth",
    "ZRAngularityClass",
    "ZRFortuneAngularityTruth",
    # Policy surfaces
    "FirdarYearPolicy",
    "DecennialPolicy",
    "ZRYearPolicy",
    "TimelordComputationPolicy",
    "DEFAULT_TIMELORD_POLICY",
    # Truth-preservation vessels
    "FirdarPeriod",
    "DecennialPeriod",
    "ReleasingPeriod",
    # Relational vessels
    "FirdarMajorGroup",
    "DecennialMajorGroup",
    "DecennialPeriodGroup",
    "ZRPeriodGroup",
    # Condition vessels
    "FirdarConditionProfile",
    "DecennialConditionProfile",
    "ZRConditionProfile",
    # Aggregate vessels
    "FirdarSequenceProfile",
    "DecennialSequenceProfile",
    "ZRSequenceProfile",
    # Network vessels
    "FirdarActivePair",
    "DecennialActivePair",
    "DecennialActivePath",
    "ZRLevelPair",
    # Computational functions
    "firdaria",
    "current_firdaria",
    "decennials",
    "decennial_sequence_truth",
    "current_decennials",
    "zodiacal_releasing",
    "zr_fortune_angularity_truth",
    "current_releasing",
    "group_firdaria",
    "group_decennials",
    "group_releasing",
    "firdar_condition_profile",
    "decennial_condition_profile",
    "zr_condition_profile",
    "firdar_sequence_profile",
    "decennial_sequence_profile",
    "zr_sequence_profile",
    "firdar_active_pair",
    "decennial_active_pair",
    "decennial_active_path",
    "zr_level_pair",
    "validate_firdaria_output",
    "validate_decennials_output",
    "validate_releasing_output",
]


# ---------------------------------------------------------------------------
# Phase 2 — Classification namespaces
# ---------------------------------------------------------------------------

class FirdarSequenceKind:
    """
    RITE: Classification namespace for Firdaria sequence lineage.

    THEOREM: FirdarSequenceKind provides the canonical string constants that identify which admitted Firdaria sequence generated a period.

    RITE OF PURPOSE:
        This namespace collapses the older `(is_day_chart, variant)` pair into
        one public classification surface so later layers can carry one named
        doctrine token instead of re-deriving sequence lineage from multiple
        fields.

    LAW OF OPERATION:
        Responsibilities:
            - Name the admitted Firdaria sequence families.
            - Provide stable public constants for vessel classification.
        Non-responsibilities:
            - Computing Firdaria periods.
            - Enforcing sequence validity at runtime.
        Dependencies:
            - Consumed by `_firdar_sequence_kind()` and downstream vessels.
        Structural invariants:
            - All public attributes are stable string constants.

    Canon: Demetra George, "Ancient Astrology in Theory and Practice" Vol.II

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.timelords.FirdarSequenceKind",
      "risk": "low",
      "api": {
        "frozen": ["DIURNAL", "NOCTURNAL_STANDARD", "NOCTURNAL_BONATTI"],
        "internal": []
      },
      "state": {"mutable": false, "owners": []},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "n/a"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    DIURNAL            = "diurnal"
    NOCTURNAL_STANDARD = "nocturnal_standard"
    NOCTURNAL_BONATTI  = "nocturnal_bonatti"


class TimelordEvaluationStatus(StrEnum):
    """Whether one atomic timelord truth was evaluable."""

    EVALUATED = "evaluated"
    NOT_EVALUABLE = "not_evaluable"


class DecennialSequenceKind:
    """
    Classification namespace for Decennials sequence lineage.

    This names the admitted sect-light-based Decennials sequence families so
    downstream layers can consume one stable doctrinal token rather than
    re-deriving classification from `is_day_chart` and `sect_light`.
    """

    DIURNAL_SOLAR = "diurnal_solar"
    NOCTURNAL_LUNAR = "nocturnal_lunar"


class DecennialTimeBasis:
    """Frozen provenance tokens for admitted Decennials time arithmetic."""

    VALENS_LIVED_DAYS_TO_360_DAY_DISTRIBUTION = (
        "valens_lived_days_to_360_day_distribution"
    )
    ELAPSED_JULIAN_DAYS_FROM_NATAL_JD = "elapsed_julian_days_from_natal_jd"


class ZRAngularityClass:
    """
    RITE: Classification namespace for Fortune-relative angularity in Zodiacal Releasing.

    THEOREM: ZRAngularityClass provides the canonical three-fold angularity labels for a Zodiacal Releasing period's house position from Fortune.

    RITE OF PURPOSE:
        This namespace turns raw Fortune-relative house counts into one stable
        symbolic vocabulary so downstream condition profiles and aggregate
        surfaces do not have to repeatedly translate numeric houses into
        angular, succedent, or cadent doctrine.

    LAW OF OPERATION:
        Responsibilities:
            - Name the admitted angularity classes.
            - Provide stable public constants for profile and vessel surfaces.
        Non-responsibilities:
            - Computing Fortune-relative houses.
            - Deciding angularity from astronomical positions.
        Dependencies:
            - Consumed by `_zr_angularity_class()` and downstream ZR vessels.
        Structural invariants:
            - All public attributes are stable string constants.

    Canon: Vettius Valens, *Anthologies* (Zodiacal Releasing doctrine lineage)

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.timelords.ZRAngularityClass",
      "risk": "low",
      "api": {
        "frozen": ["ANGULAR", "SUCCEDENT", "CADENT"],
        "internal": []
      },
      "state": {"mutable": false, "owners": []},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "n/a"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    ANGULAR   = "angular"
    SUCCEDENT = "succedent"
    CADENT    = "cadent"


_ANGULAR_HOUSES:   frozenset[int] = frozenset({1, 4, 7, 10})
_SUCCEDENT_HOUSES: frozenset[int] = frozenset({2, 5, 8, 11})


def _zr_angularity_class(angularity: int | None) -> str | None:
    """Return the ZRAngularityClass string for a given house number, or None."""
    if angularity is None:
        return None
    if angularity in _ANGULAR_HOUSES:
        return ZRAngularityClass.ANGULAR
    if angularity in _SUCCEDENT_HOUSES:
        return ZRAngularityClass.SUCCEDENT
    return ZRAngularityClass.CADENT


@dataclass(frozen=True, slots=True)
class ZRFortuneAngularityTruth:
    """Typed Fortune dependency and angular-place receipt for one ZR sign."""

    status: TimelordEvaluationStatus
    period_sign: str
    fortune_sign: str | None
    angularity_from_fortune: int | None
    angularity_class: str | None
    is_peak_period: bool | None
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, TimelordEvaluationStatus):
            raise ValueError(
                "ZRFortuneAngularityTruth status must be a "
                "TimelordEvaluationStatus"
            )
        if self.period_sign not in SIGNS:
            raise ValueError(
                "ZRFortuneAngularityTruth period_sign must be a zodiac sign"
            )
        if self.status is TimelordEvaluationStatus.EVALUATED:
            if self.fortune_sign not in SIGNS:
                raise ValueError(
                    "ZRFortuneAngularityTruth evaluated results require "
                    "a Fortune sign"
                )
            expected_angularity = (
                (
                    _sign_index(self.period_sign)
                    - _sign_index(self.fortune_sign)
                )
                % 12
            ) + 1
            if (
                self.angularity_from_fortune not in range(1, 13)
                or self.angularity_from_fortune != expected_angularity
                or self.angularity_class
                != _zr_angularity_class(self.angularity_from_fortune)
                or not isinstance(self.is_peak_period, bool)
                or self.reason is not None
            ):
                raise ValueError(
                    "ZRFortuneAngularityTruth evaluated results require "
                    "Fortune sign, place, class, peak boolean, and no reason"
                )
            expected_peak = (
                self.angularity_from_fortune in _ANGULAR_HOUSES
            )
            if self.is_peak_period is not expected_peak:
                raise ValueError(
                    "ZRFortuneAngularityTruth peak truth must match the "
                    "Fortune-relative angular place"
                )
        elif (
            self.fortune_sign is not None
            or self.angularity_from_fortune is not None
            or self.angularity_class is not None
            or self.is_peak_period is not None
            or self.reason != "fortune_not_supplied"
        ):
            raise ValueError(
                "ZRFortuneAngularityTruth not_evaluable results require "
                "no fabricated Fortune fields and reason='fortune_not_supplied'"
            )


def zr_fortune_angularity_truth(
    period_sign: str,
    fortune_sign: str | None,
) -> ZRFortuneAngularityTruth:
    """Evaluate one ZR sign's place from Fortune without false defaults."""

    if period_sign not in SIGNS:
        raise ValueError("period_sign must be a zodiac sign")
    if fortune_sign is None:
        return ZRFortuneAngularityTruth(
            status=TimelordEvaluationStatus.NOT_EVALUABLE,
            period_sign=period_sign,
            fortune_sign=None,
            angularity_from_fortune=None,
            angularity_class=None,
            is_peak_period=None,
            reason="fortune_not_supplied",
        )
    if fortune_sign not in SIGNS:
        raise ValueError("fortune_sign must be a zodiac sign or None")

    angularity = _fortune_angularity(period_sign, fortune_sign)
    if angularity is None:
        raise ValueError(
            "supplied Fortune sign must produce an angularity place"
        )
    angularity_class = _zr_angularity_class(angularity)
    if angularity_class is None:
        raise ValueError(
            "evaluated Fortune angularity must produce a class"
        )
    return ZRFortuneAngularityTruth(
        status=TimelordEvaluationStatus.EVALUATED,
        period_sign=period_sign,
        fortune_sign=fortune_sign,
        angularity_from_fortune=angularity,
        angularity_class=angularity_class,
        is_peak_period=angularity in _ANGULAR_HOUSES,
    )


def _firdar_sequence_kind(is_day_chart: bool, variant: str) -> str:
    """Return the FirdarSequenceKind string for a (sect, variant) pair."""
    if is_day_chart:
        return FirdarSequenceKind.DIURNAL
    if variant == "bonatti":
        return FirdarSequenceKind.NOCTURNAL_BONATTI
    return FirdarSequenceKind.NOCTURNAL_STANDARD


def _decennial_sequence_kind(is_day_chart: bool) -> str:
    """Return the DecennialSequenceKind for a sect-light Decennials sequence."""

    if is_day_chart:
        return DecennialSequenceKind.DIURNAL_SOLAR
    return DecennialSequenceKind.NOCTURNAL_LUNAR


# ---------------------------------------------------------------------------
# Firdaria — sequence tables
# ---------------------------------------------------------------------------

#: Diurnal (day-chart) major firdaria: (planet, years)
FIRDARIA_DIURNAL: list[tuple[str, int]] = [
    ("Sun",        10),
    ("Venus",       8),
    ("Mercury",    13),
    ("Moon",        9),
    ("Saturn",     11),
    ("Jupiter",    12),
    ("Mars",        7),
    ("North Node",  3),
    ("South Node",  2),
]

#: Nocturnal (night-chart) major firdaria: (planet, years)
FIRDARIA_NOCTURNAL: list[tuple[str, int]] = [
    ("Moon",        9),
    ("Saturn",     11),
    ("Jupiter",    12),
    ("Mars",        7),
    ("Sun",        10),
    ("Venus",       8),
    ("Mercury",    13),
    ("North Node",  3),
    ("South Node",  2),
]

#: Alternate nocturnal sequence frequently attributed to Bonatti-style usage.
FIRDARIA_NOCTURNAL_BONATTI: list[tuple[str, int]] = [
    ("Moon",        9),
    ("Saturn",     11),
    ("Jupiter",    12),
    ("Mars",        7),
    ("North Node",  3),
    ("South Node",  2),
    ("Sun",        10),
    ("Venus",       8),
    ("Mercury",    13),
]

#: Chaldean order used for sub-period rulers
CHALDEAN_ORDER: list[str] = [
    "Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon",
]

#: Days per Julian year (used for all JD arithmetic)
_JULIAN_YEAR = 365.25


# ---------------------------------------------------------------------------
# Firdaria dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class FirdarPeriod:
    """
    RITE: The Firdar Period Vessel

    THEOREM: Governs the storage of a single major or sub-period in the Firdaria
    time-lord system.

    RITE OF PURPOSE:
        FirdarPeriod is the authoritative data vessel for a single Firdaria period
        produced by the Timelord Engine. It captures the hierarchical level (major
        or sub), the ruling planet, the start and end Julian Days, and the duration
        in years. Without it, callers would receive unstructured tuples with no
        field-level guarantees. It exists to give every higher-level consumer a
        single, named, mutable record of each Firdaria period.

    LAW OF OPERATION:
        Responsibilities:
            - Store a single Firdaria period as named, typed fields
            - Expose UTC datetime and CalendarDateTime views via read-only properties
            - Serve as the return type of firdaria() and current_firdaria()
        Non-responsibilities:
            - Computing period boundaries (delegates to firdaria)
            - Resolving natal positions from ephemeris (delegates to planets)
        Dependencies:
            - Populated by firdaria()
            - start_dt / end_dt delegate to datetime_from_jd()
            - start_calendar / end_calendar delegate to calendar_datetime_from_jd()
        Structural invariants:
            - level is 1 (major) or 2 (sub-period)
            - end_jd > start_jd
        Behavioral invariants:
            - All consumers treat FirdarPeriod fields as read-only after construction

    Canon: Demetra George, "Ancient Astrology in Theory and Practice" Vol.II

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.timelords.FirdarPeriod",
      "risk": "high",
      "api": {
        "frozen": ["level", "planet", "start_jd", "end_jd", "years"],
        "internal": ["start_dt", "start_calendar", "end_dt", "end_calendar"]
      },
      "state": {"mutable": true, "owners": ["firdaria"]},
      "effects": {
        "signals_emitted": [],
        "io": []
      },
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    level:        int           # 1 = major period, 2 = sub-period
    planet:       str
    start_jd:     float
    end_jd:       float
    years:        float
    # Phase 1: preserved generative context
    major_planet: str | None = None   # for level=2: the level-1 lord this sub-period belongs to
    is_day_chart: bool | None = None  # diurnal (True) or nocturnal (False) chart sect
    variant:      str | None = None   # "standard" or "bonatti" sequence variant
    # Phase 2: typed classification
    sequence_kind:  str | None = None  # FirdarSequenceKind constant
    is_node_period: bool = False        # True when planet is North Node or South Node

    def __post_init__(self) -> None:
        if self.level not in (1, 2):
            raise ValueError(f"FirdarPeriod.level must be 1 or 2, got {self.level}")
        if not math.isfinite(self.start_jd) or not math.isfinite(self.end_jd):
            raise ValueError("FirdarPeriod start_jd and end_jd must be finite")
        if self.end_jd <= self.start_jd:
            raise ValueError("FirdarPeriod end_jd must be greater than start_jd")
        if self.years <= 0:
            raise ValueError("FirdarPeriod years must be positive")

    # --- Phase 3: inspectability ---

    @property
    def is_major(self) -> bool:
        """True when this is a level-1 (major) Firdaria period."""
        return self.level == 1

    @property
    def is_sub(self) -> bool:
        """True when this is a level-2 (sub-period) Firdaria period."""
        return self.level == 2

    @property
    def level_name(self) -> str:
        """Human-readable level label: 'Major' or 'Sub-period'."""
        return "Major" if self.level == 1 else "Sub-period"

    def is_active_at(self, jd: float) -> bool:
        """
        Return True if *jd* falls within this period.

        The interval is half-open: [start_jd, end_jd).
        This is the canonical boundary convention used throughout the engine.
        """
        return self.start_jd <= jd < self.end_jd

    # --- Datetime views ---

    @property
    def start_dt(self) -> datetime:
        """UTC datetime of the period start."""
        return datetime_from_jd(self.start_jd)

    @property
    def start_calendar(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(self.start_jd)

    @property
    def end_dt(self) -> datetime:
        """UTC datetime of the period end."""
        return datetime_from_jd(self.end_jd)

    @property
    def end_calendar(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(self.end_jd)

    @property
    def days(self) -> float:
        """Duration of this period in Julian days."""
        return self.end_jd - self.start_jd

    def __repr__(self) -> str:
        lvl = "Major" if self.level == 1 else "Sub  "
        return (
            f"FirdarPeriod(L{self.level} {lvl} | {self.planet:<11} "
            f"{self.years:.2f} yrs | "
            f"{self.start_calendar.date_string()} → "
            f"{self.end_calendar.date_string()})"
        )


# ---------------------------------------------------------------------------
# Phase 5 — Relational Formalization: Firdaria
# Phase 6 — Relational Hardening / Inspectability: Firdaria
# ---------------------------------------------------------------------------

# Planet-classification sets for Firdaria sub-period subset properties.
_FIRDARIA_LUMINARIES: frozenset[str] = frozenset({"Sun", "Moon"})
_FIRDARIA_NODES:      frozenset[str] = frozenset({"North Node", "South Node"})


@dataclass(slots=True)
class FirdarMajorGroup:
    """
    RITE: The Firdar Major Group Vessel

    THEOREM: FirdarMajorGroup binds one major Firdaria period to the sub-periods it governs.

    RITE OF PURPOSE:
        This vessel makes Firdaria containment explicit. Without it, callers
        would have to reconstruct the relation between level-1 and level-2
        periods by filtering a flat list and trusting contextual fields and JD
        overlap. It preserves that relation as a first-class public object.

    LAW OF OPERATION:
        Responsibilities:
            - Carry one level-1 major period and its level-2 sub-periods.
            - Enforce level correctness and chronological ordering.
            - Provide an inspectable relational surface for Firdaria groups.
        Non-responsibilities:
            - Computing major or sub-period boundaries.
            - Resolving active periods from a query JD.
        Dependencies:
            - Populated by `group_firdaria()`.
            - Consumes `FirdarPeriod` vessels produced by `firdaria()`.
        Structural invariants:
            - `major.level == 1`
            - every member of `subs` has `level == 2`
            - `subs` are in chronological order
        Failure behavior:
            - Raises `ValueError` when level or ordering invariants are broken.

    Canon: Demetra George, "Ancient Astrology in Theory and Practice" Vol.II

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.timelords.FirdarMajorGroup",
      "risk": "medium",
      "api": {
        "frozen": ["major", "subs"],
        "internal": ["__post_init__"]
      },
      "state": {"mutable": true, "owners": ["group_firdaria"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    major: FirdarPeriod
    subs:  list[FirdarPeriod]

    def __post_init__(self) -> None:
        if self.major.level != 1:
            raise ValueError(
                f"FirdarMajorGroup.major must be a level-1 period, got level {self.major.level}"
            )
        for sub in self.subs:
            if sub.level != 2:
                raise ValueError(
                    f"FirdarMajorGroup.subs must contain only level-2 periods, got level {sub.level}"
                )
        # Phase 6 hardening — chronological ordering
        for i in range(len(self.subs) - 1):
            if self.subs[i].start_jd >= self.subs[i + 1].start_jd:
                raise ValueError(
                    "FirdarMajorGroup.subs must be in chronological order"
                )

    @property
    def sub_count(self) -> int:
        """Number of sub-periods in this major group."""
        return len(self.subs)

    @property
    def has_subs(self) -> bool:
        """True when this major period has sub-periods."""
        return bool(self.subs)

    # --- Phase 6: subset distinction ---

    @property
    def luminary_subs(self) -> list[FirdarPeriod]:
        """Sub-periods whose lord is a luminary (Sun or Moon)."""
        return [s for s in self.subs if s.planet in _FIRDARIA_LUMINARIES]

    @property
    def node_subs(self) -> list[FirdarPeriod]:
        """Sub-periods whose lord is a node (North Node or South Node)."""
        return [s for s in self.subs if s.is_node_period]

    @property
    def planet_subs(self) -> list[FirdarPeriod]:
        """Sub-periods whose lord is one of the five traditional planets
        (Mercury, Venus, Mars, Jupiter, Saturn) — neither luminary nor node."""
        return [
            s for s in self.subs
            if s.planet not in _FIRDARIA_LUMINARIES and not s.is_node_period
        ]

    @property
    def is_complete(self) -> bool:
        """True when this group carries the expected number of sub-periods.

        Non-node majors expect exactly 7 sub-periods.
        Node majors may have 0 (not subdivided) or 7 (subdivided) — both admitted.
        """
        if self.major.is_node_period:
            return self.sub_count in (0, 7)
        return self.sub_count == 7

    def active_sub_at(self, jd: float) -> FirdarPeriod | None:
        """Return the sub-period active at *jd*, or None if none applies."""
        for sub in self.subs:
            if sub.is_active_at(jd):
                return sub
        return None


def group_firdaria(periods: list[FirdarPeriod]) -> list[FirdarMajorGroup]:
    """
    Group a flat Firdaria period list into FirdarMajorGroup vessels.

    The input must be the output of firdaria(). Each major period is
    paired with the sub-periods that belong to it (matched by major_planet
    and JD containment). Node periods with no sub-periods produce a group
    with an empty subs list.

    Returns
    -------
    list[FirdarMajorGroup]
        One group per major period, in sequence order.
    """
    major_periods = [p for p in periods if p.level == 1]
    sub_periods   = [p for p in periods if p.level == 2]

    groups: list[FirdarMajorGroup] = []
    for major in major_periods:
        # Match by major_planet alone: each planet appears exactly once as a
        # major lord in a Firdaria sequence, so major_planet is a unique key.
        # JD-range filtering is intentionally omitted — floating-point
        # accumulation can push the last sub-period's end_jd fractionally
        # past the major's end_jd, causing a false exclusion.
        subs = [s for s in sub_periods if s.major_planet == major.planet]
        groups.append(FirdarMajorGroup(major=major, subs=subs))
    return groups


# ---------------------------------------------------------------------------
# Firdaria calculation
# ---------------------------------------------------------------------------

def _resolve_firdaria_sequence(
    is_day_chart: bool,
    variant: str,
) -> list[tuple[str, int]]:
    if variant not in {"standard", "bonatti"}:
        raise ValueError("firdaria variant must be 'standard' or 'bonatti'")
    if is_day_chart:
        return FIRDARIA_DIURNAL
    if variant == "bonatti":
        return FIRDARIA_NOCTURNAL_BONATTI
    return FIRDARIA_NOCTURNAL


def _should_subdivide_firdaria_major(planet: str, include_node_subperiods: bool) -> bool:
    if planet in {"North Node", "South Node"}:
        return include_node_subperiods
    return True


def firdaria(
    natal_jd: float,
    is_day_chart: bool,
    *,
    variant: str = "standard",
    include_node_subperiods: bool = False,
    policy: "TimelordComputationPolicy | None" = None,
) -> list[FirdarPeriod]:
    """
    Generate all Firdaria major and sub-periods for a complete life cycle.

    The full sequence (diurnal or nocturnal) sums to 75 years.  Each major
    period is further divided into 7 sub-periods in Chaldean order, beginning
    with the major-period planet itself rotating to the appropriate position.

    Parameters
    ----------
    natal_jd : float
        Julian Day (UT) of the birth moment.
    is_day_chart : bool
        True for a diurnal (day) chart; False for a nocturnal (night) chart.
    variant : str
        Firdaria sequence variant: ``"standard"`` (default) or ``"bonatti"``.
        Only affects nocturnal charts; diurnal charts always use FIRDARIA_DIURNAL.
    include_node_subperiods : bool
        When True, North Node and South Node major periods are also subdivided
        into 7 sub-periods. Default False (nodes produce no sub-periods).
    policy : TimelordComputationPolicy | None
        Computation policy governing the Julian year constant. Uses
        DEFAULT_TIMELORD_POLICY when None.

    Returns
    -------
    list[FirdarPeriod]
        All major periods, each immediately followed by their 7 sub-periods,
        in chronological order.

    Raises
    ------
    ValueError
        If natal_jd is not finite.
        If variant is not ``"standard"`` or ``"bonatti"``.
    """
    if not math.isfinite(natal_jd):
        raise ValueError(f"firdaria: natal_jd must be finite, got {natal_jd!r}")
    pol = _resolve_timelord_policy(policy)
    sequence = _resolve_firdaria_sequence(is_day_chart, variant)
    periods:  list[FirdarPeriod] = []
    cursor_jd = natal_jd
    _year_days = pol.firdaria_year.year_days
    _seq_kind  = _firdar_sequence_kind(is_day_chart, variant)

    for major_planet, major_years in sequence:
        major_start = cursor_jd
        major_end   = cursor_jd + major_years * _year_days

        _is_node  = major_planet in {"North Node", "South Node"}

        periods.append(FirdarPeriod(
            level=1,
            planet=major_planet,
            start_jd=major_start,
            end_jd=major_end,
            years=float(major_years),
            is_day_chart=is_day_chart,
            variant=variant,
            sequence_kind=_seq_kind,
            is_node_period=_is_node,
        ))

        if _should_subdivide_firdaria_major(major_planet, include_node_subperiods):
            # Sub-periods: 7 planets in Chaldean order, each lasting major_years/7.
            # The sub-period sequence starts at the major planet's Chaldean position.
            if major_planet in CHALDEAN_ORDER:
                start_idx = CHALDEAN_ORDER.index(major_planet)
            else:
                # Nodes use the same starting index as Mars when explicitly subdivided.
                start_idx = CHALDEAN_ORDER.index("Mars")

            sub_years = major_years / 7.0
            sub_cursor = major_start

            for i in range(7):
                sub_planet = CHALDEAN_ORDER[(start_idx + i) % 7]
                sub_end    = sub_cursor + sub_years * _year_days
                periods.append(FirdarPeriod(
                    level=2,
                    planet=sub_planet,
                    start_jd=sub_cursor,
                    end_jd=sub_end,
                    years=sub_years,
                    major_planet=major_planet,
                    is_day_chart=is_day_chart,
                    variant=variant,
                    sequence_kind=_seq_kind,
                    is_node_period=sub_planet in {"North Node", "South Node"},
                ))
                sub_cursor = sub_end

        cursor_jd = major_end

    return periods


def current_firdaria(
    natal_jd: float,
    current_jd: float,
    is_day_chart: bool,
    *,
    variant: str = "standard",
    include_node_subperiods: bool = False,
    policy: "TimelordComputationPolicy | None" = None,
) -> tuple[FirdarPeriod, FirdarPeriod]:
    """
    Find the Firdaria major and sub-period active at a given date.

    Parameters
    ----------
    natal_jd : float
        Julian Day (UT) of birth.
    current_jd : float
        Julian Day (UT) of the date to evaluate.
    is_day_chart : bool
        True for a diurnal chart; False for a nocturnal chart.

    Returns
    -------
    tuple[FirdarPeriod, FirdarPeriod]
        (major_period, sub_period) active at current_jd.

    Raises
    ------
    ValueError
        If current_jd falls outside the 75-year Firdaria cycle.
    """
    if not math.isfinite(natal_jd):
        raise ValueError(f"current_firdaria: natal_jd must be finite, got {natal_jd!r}")
    if not math.isfinite(current_jd):
        raise ValueError(f"current_firdaria: current_jd must be finite, got {current_jd!r}")
    all_periods = firdaria(
        natal_jd,
        is_day_chart,
        variant=variant,
        include_node_subperiods=include_node_subperiods,
        policy=policy,
    )
    major_periods = [p for p in all_periods if p.level == 1]
    sub_periods   = [p for p in all_periods if p.level == 2]

    active_major: FirdarPeriod | None = None
    for p in major_periods:
        if p.start_jd <= current_jd < p.end_jd:
            active_major = p
            break

    if active_major is None:
        raise ValueError(
            f"current_jd {current_jd} falls outside the 75-year Firdaria cycle "
            f"starting at natal_jd {natal_jd}."
        )

    active_sub: FirdarPeriod | None = None
    for p in sub_periods:
        if p.start_jd <= current_jd < p.end_jd:
            active_sub = p
            break

    if active_sub is None:
        if not _should_subdivide_firdaria_major(active_major.planet, include_node_subperiods):
            return active_major, active_major
        for p in sub_periods:
            if p.start_jd == active_major.start_jd:
                active_sub = p
                break

    if active_sub is None:
        raise ValueError("Could not determine active Firdaria sub-period.")

    return active_major, active_sub


# ---------------------------------------------------------------------------
# Decennials — minimum admitted engine
# ---------------------------------------------------------------------------

_DECENNIAL_PLANETS: tuple[str, ...] = (
    "Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn",
)
_DECENNIAL_MONTHS: dict[str, int] = {
    "Saturn": 30,
    "Jupiter": 12,
    "Mars": 15,
    "Sun": 19,
    "Venus": 8,
    "Mercury": 20,
    "Moon": 25,
}
_DECENNIAL_MAJOR_MONTHS = sum(_DECENNIAL_MONTHS.values())
_DECENNIAL_MONTH_DAYS = 30.0
_DECENNIAL_LUMINARIES: frozenset[str] = frozenset({"Sun", "Moon"})
_DECENNIAL_PLANETARIES: frozenset[str] = frozenset({"Mercury", "Venus", "Mars", "Jupiter", "Saturn"})
_DECENNIAL_MAX_LEVEL = 2
_DECENNIAL_SEQUENCE_BOUNDARY_TOLERANCE_DEG = 1e-12


def _decennial_ambiguous_groups(
    body_truths: tuple["DecennialSequenceBodyTruth", ...],
) -> tuple[tuple[str, ...], ...]:
    """Return every tied non-sect arc group in deterministic order."""

    non_sect = sorted(
        (item for item in body_truths if not item.is_sect_light),
        key=lambda item: item.forward_arc_from_sect_light_deg,
    )
    groups: list[tuple[str, ...]] = []
    index = 0
    while index < len(non_sect):
        anchor = non_sect[index]
        group = [anchor.planet]
        cursor = index + 1
        while cursor < len(non_sect) and math.isclose(
            non_sect[cursor].forward_arc_from_sect_light_deg,
            anchor.forward_arc_from_sect_light_deg,
            rel_tol=0.0,
            abs_tol=_DECENNIAL_SEQUENCE_BOUNDARY_TOLERANCE_DEG,
        ):
            group.append(non_sect[cursor].planet)
            cursor += 1
        if len(group) > 1:
            groups.append(tuple(group))
        index = cursor
    return tuple(groups)


@dataclass(frozen=True, slots=True)
class DecennialSequenceBodyTruth:
    """One classical body's zodiacal arc from the sect light."""

    planet: str
    longitude: float
    forward_arc_from_sect_light_deg: float
    is_sect_light: bool

    def __post_init__(self) -> None:
        if self.planet not in _DECENNIAL_PLANETS:
            raise ValueError(
                "DecennialSequenceBodyTruth planet must be classical"
            )
        if not math.isfinite(self.longitude) or not (
            0.0 <= self.longitude < 360.0
        ):
            raise ValueError(
                "DecennialSequenceBodyTruth longitude must be in [0, 360)"
            )
        if not math.isfinite(self.forward_arc_from_sect_light_deg) or not (
            0.0 <= self.forward_arc_from_sect_light_deg < 360.0
        ):
            raise ValueError(
                "DecennialSequenceBodyTruth forward arc must be in [0, 360)"
            )
        if not isinstance(self.is_sect_light, bool):
            raise ValueError(
                "DecennialSequenceBodyTruth is_sect_light must be a boolean"
            )


@dataclass(frozen=True, slots=True)
class DecennialSequenceAssemblyTruth:
    """Typed sect-light origin and zodiacal ordering receipt."""

    status: TimelordEvaluationStatus
    is_day_chart: bool
    sect_light: str
    sequence_kind: str
    sect_light_longitude: float
    body_truths: tuple[DecennialSequenceBodyTruth, ...]
    sequence: tuple[str, ...] | None
    ambiguous_groups: tuple[tuple[str, ...], ...] = ()
    reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.status, TimelordEvaluationStatus):
            raise ValueError(
                "DecennialSequenceAssemblyTruth status must be a "
                "TimelordEvaluationStatus"
            )
        if not isinstance(self.is_day_chart, bool):
            raise ValueError(
                "DecennialSequenceAssemblyTruth is_day_chart must be a boolean"
            )
        expected_light = "Sun" if self.is_day_chart else "Moon"
        expected_kind = _decennial_sequence_kind(self.is_day_chart)
        if self.sect_light != expected_light:
            raise ValueError(
                "DecennialSequenceAssemblyTruth sect_light must match chart sect"
            )
        if self.sequence_kind != expected_kind:
            raise ValueError(
                "DecennialSequenceAssemblyTruth sequence_kind must match chart sect"
            )
        if not math.isfinite(self.sect_light_longitude) or not (
            0.0 <= self.sect_light_longitude < 360.0
        ):
            raise ValueError(
                "DecennialSequenceAssemblyTruth sect-light longitude must "
                "be in [0, 360)"
            )
        if any(
            not isinstance(item, DecennialSequenceBodyTruth)
            for item in self.body_truths
        ):
            raise ValueError(
                "DecennialSequenceAssemblyTruth body_truths must contain "
                "DecennialSequenceBodyTruth values"
            )
        if tuple(item.planet for item in self.body_truths) != _DECENNIAL_PLANETS:
            raise ValueError(
                "DecennialSequenceAssemblyTruth body_truths must contain the "
                "Classic 7 in canonical dependency order"
            )
        for item in self.body_truths:
            expected_arc = (
                item.longitude - self.sect_light_longitude
            ) % 360.0
            if not math.isclose(
                item.forward_arc_from_sect_light_deg,
                expected_arc,
                rel_tol=0.0,
                abs_tol=_DECENNIAL_SEQUENCE_BOUNDARY_TOLERANCE_DEG,
            ):
                raise ValueError(
                    "DecennialSequenceAssemblyTruth body arcs must be measured "
                    "from the sect light"
                )
            if item.is_sect_light is not (item.planet == self.sect_light):
                raise ValueError(
                    "DecennialSequenceAssemblyTruth sect-light marker must "
                    "identify only the sect light"
                )
        if len(self.ambiguous_groups) != len(set(self.ambiguous_groups)):
            raise ValueError(
                "DecennialSequenceAssemblyTruth ambiguous groups must be unique"
            )
        body_by_name = {item.planet: item for item in self.body_truths}
        seen_ambiguous: set[str] = set()
        for group in self.ambiguous_groups:
            if len(group) < 2 or len(group) != len(set(group)):
                raise ValueError(
                    "DecennialSequenceAssemblyTruth ambiguous groups require "
                    "at least two unique planets"
                )
            if self.sect_light in group or any(
                planet not in body_by_name for planet in group
            ):
                raise ValueError(
                    "DecennialSequenceAssemblyTruth ambiguity applies only "
                    "to known non-sect bodies"
                )
            if seen_ambiguous.intersection(group):
                raise ValueError(
                    "DecennialSequenceAssemblyTruth ambiguous groups cannot overlap"
                )
            seen_ambiguous.update(group)
            anchor_arc = body_by_name[group[0]].forward_arc_from_sect_light_deg
            if any(
                not math.isclose(
                    body_by_name[planet].forward_arc_from_sect_light_deg,
                    anchor_arc,
                    rel_tol=0.0,
                    abs_tol=_DECENNIAL_SEQUENCE_BOUNDARY_TOLERANCE_DEG,
                )
                for planet in group[1:]
            ):
                raise ValueError(
                    "DecennialSequenceAssemblyTruth ambiguous groups must "
                    "share one zodiacal arc"
                )
        expected_ambiguous_groups = _decennial_ambiguous_groups(
            self.body_truths
        )
        if self.ambiguous_groups != expected_ambiguous_groups:
            raise ValueError(
                "DecennialSequenceAssemblyTruth ambiguous groups must "
                "exhaustively match tied non-sect arcs"
            )
        if self.status is TimelordEvaluationStatus.EVALUATED:
            if (
                self.sequence is None
                or len(self.sequence) != len(_DECENNIAL_PLANETS)
                or set(self.sequence) != set(_DECENNIAL_PLANETS)
                or self.sequence[0] != self.sect_light
                or self.ambiguous_groups
                or self.reason is not None
            ):
                raise ValueError(
                    "DecennialSequenceAssemblyTruth evaluated results require "
                    "one unambiguous sect-light-led sequence"
                )
            expected_sequence = tuple(
                item.planet
                for item in sorted(
                    self.body_truths,
                    key=lambda item: (
                        item.forward_arc_from_sect_light_deg,
                        0 if item.is_sect_light else 1,
                    ),
                )
            )
            if self.sequence != expected_sequence:
                raise ValueError(
                    "DecennialSequenceAssemblyTruth sequence must follow "
                    "zodiacal arcs from the sect light"
                )
        elif (
            self.sequence is not None
            or not self.ambiguous_groups
            or self.reason != "non_sect_longitude_tie"
        ):
            raise ValueError(
                "DecennialSequenceAssemblyTruth not_evaluable results require "
                "ambiguity groups, no sequence, and "
                "reason='non_sect_longitude_tie'"
            )


@dataclass(slots=True)
class DecennialPeriod:
    """One period with symbolic distribution and calendar-projection truth."""

    level: int
    planet: str
    start_jd: float
    end_jd: float
    years: float
    months: float
    sequence_origin_jd: float
    time_basis: str = DecennialTimeBasis.VALENS_LIVED_DAYS_TO_360_DAY_DISTRIBUTION
    calendar_projection_basis: str = DecennialTimeBasis.ELAPSED_JULIAN_DAYS_FROM_NATAL_JD
    major_planet: str | None = None
    parent_planet: str | None = None
    parent_level: int | None = None
    is_day_chart: bool | None = None
    sect_light: str | None = None
    sequence_kind: str | None = None
    deep_subdivision_method: None = None
    sequence: tuple[str, ...] = field(default_factory=tuple)
    ancestor_planets: tuple[str, ...] = field(default_factory=tuple)
    major_index: int = 0
    sub_index: int | None = None
    major_month_total: float = float(_DECENNIAL_MAJOR_MONTHS)
    month_basis_days: float = _DECENNIAL_MONTH_DAYS
    sequence_truth: DecennialSequenceAssemblyTruth | None = None

    def __post_init__(self) -> None:
        if self.level not in (1, 2):
            raise ValueError(
                "DecennialPeriod.level must be 1 or 2; deeper levels are "
                f"not admitted, got {self.level}"
            )
        if self.planet not in _DECENNIAL_PLANETS:
            raise ValueError(f"DecennialPeriod.planet must be a classical planet, got {self.planet!r}")
        if not math.isfinite(self.start_jd) or not math.isfinite(self.end_jd):
            raise ValueError("DecennialPeriod start_jd and end_jd must be finite")
        if not math.isfinite(self.sequence_origin_jd):
            raise ValueError("DecennialPeriod sequence_origin_jd must be finite")
        if self.end_jd <= self.start_jd:
            raise ValueError("DecennialPeriod end_jd must be greater than start_jd")
        if self.start_jd < self.sequence_origin_jd:
            raise ValueError(
                "DecennialPeriod start_jd must not precede sequence_origin_jd"
            )
        if (
            self.time_basis
            != DecennialTimeBasis.VALENS_LIVED_DAYS_TO_360_DAY_DISTRIBUTION
        ):
            raise ValueError(
                "DecennialPeriod time_basis must preserve the admitted "
                "Valens lived-day to 360-day distribution basis"
            )
        if (
            self.calendar_projection_basis
            != DecennialTimeBasis.ELAPSED_JULIAN_DAYS_FROM_NATAL_JD
        ):
            raise ValueError(
                "DecennialPeriod calendar_projection_basis must preserve "
                "elapsed Julian days from natal_jd"
            )
        if self.years <= 0:
            raise ValueError("DecennialPeriod years must be positive")
        if self.months <= 0:
            raise ValueError("DecennialPeriod months must be positive")
        if self.sect_light is not None and self.sect_light not in {"Sun", "Moon"}:
            raise ValueError("DecennialPeriod sect_light must be Sun, Moon, or None")
        if self.sequence_kind is not None and self.sequence_kind not in {
            DecennialSequenceKind.DIURNAL_SOLAR,
            DecennialSequenceKind.NOCTURNAL_LUNAR,
        }:
            raise ValueError("DecennialPeriod sequence_kind must be a supported DecennialSequenceKind")
        if self.parent_planet is not None and self.parent_planet not in _DECENNIAL_PLANETS:
            raise ValueError("DecennialPeriod parent_planet must be a classical planet or None")
        if self.parent_level is not None and self.parent_level != 1:
            raise ValueError(
                "DecennialPeriod parent_level must be 1 or None"
            )
        if self.deep_subdivision_method is not None:
            raise ValueError(
                "DecennialPeriod deep_subdivision_method is not admitted"
            )
        if self.sequence and set(self.sequence) != set(_DECENNIAL_PLANETS):
            raise ValueError("DecennialPeriod sequence must contain the seven classical planets exactly once")
        if self.major_index < 0:
            raise ValueError("DecennialPeriod major_index must be non-negative")
        if self.sub_index is not None and self.sub_index < 0:
            raise ValueError("DecennialPeriod sub_index must be non-negative when set")
        if self.major_month_total <= 0:
            raise ValueError("DecennialPeriod major_month_total must be positive")
        if self.month_basis_days <= 0:
            raise ValueError("DecennialPeriod month_basis_days must be positive")
        if self.level == 1 and self.major_planet is not None:
            raise ValueError("DecennialPeriod level-1 periods must not set major_planet")
        if self.level == 1 and self.parent_planet is not None:
            raise ValueError("DecennialPeriod level-1 periods must not set parent_planet")
        if self.level == 1 and self.parent_level is not None:
            raise ValueError("DecennialPeriod level-1 periods must not set parent_level")
        if self.level == 1 and self.sub_index is not None:
            raise ValueError("DecennialPeriod level-1 periods must not set sub_index")
        if self.level == 1 and self.ancestor_planets:
            raise ValueError("DecennialPeriod level-1 periods must not set ancestor_planets")
        if self.level >= 2 and not self.major_planet:
            if self.level == 2:
                raise ValueError("DecennialPeriod level-2 periods must preserve major_planet")
            raise ValueError("DecennialPeriod subordinate periods must preserve major_planet")
        if self.level >= 2 and self.sub_index is None:
            if self.level == 2:
                raise ValueError("DecennialPeriod level-2 periods must preserve sub_index")
            raise ValueError("DecennialPeriod subordinate periods must preserve sub_index")
        if self.level >= 2 and not self.parent_planet:
            raise ValueError("DecennialPeriod subordinate periods must preserve parent_planet")
        if self.level >= 2 and self.parent_level != self.level - 1:
            raise ValueError("DecennialPeriod parent_level must equal level - 1 for subordinate periods")
        if len(self.ancestor_planets) != max(0, self.level - 1):
            raise ValueError("DecennialPeriod ancestor_planets must preserve one ancestor per prior level")
        if self.level >= 2 and self.ancestor_planets[0] != self.major_planet:
            raise ValueError("DecennialPeriod ancestor_planets must begin with major_planet")
        if self.level >= 2 and self.ancestor_planets[-1] != self.parent_planet:
            raise ValueError("DecennialPeriod ancestor_planets must end with parent_planet")
        if self.sequence:
            if self.major_index >= len(self.sequence):
                raise ValueError("DecennialPeriod major_index must lie inside preserved sequence")
            if self.level == 1 and self.sequence[self.major_index] != self.planet:
                raise ValueError("DecennialPeriod major planet must match preserved sequence at major_index")
            if self.level >= 2:
                assert self.sub_index is not None
                assert self.parent_planet is not None
                try:
                    anchor_index = self.sequence.index(self.parent_planet)
                except ValueError as exc:
                    raise ValueError("DecennialPeriod parent_planet must exist inside preserved sequence") from exc
                rotated = self.sequence[anchor_index:] + self.sequence[:anchor_index]
                if self.sub_index >= len(rotated):
                    raise ValueError("DecennialPeriod sub_index must lie inside rotated sequence")
                if rotated[self.sub_index] != self.planet:
                    raise ValueError("DecennialPeriod sub planet must match rotated sequence at sub_index")
                if self.major_planet != self.sequence[self.major_index]:
                    raise ValueError("DecennialPeriod level-2 major_planet must match preserved major sequence planet")
        if self.sequence_truth is not None:
            truth = self.sequence_truth
            if truth.status is not TimelordEvaluationStatus.EVALUATED:
                raise ValueError(
                    "DecennialPeriod cannot assemble from not_evaluable "
                    "sequence truth"
                )
            if (
                truth.sequence != self.sequence
                or truth.is_day_chart is not self.is_day_chart
                or truth.sect_light != self.sect_light
                or truth.sequence_kind != self.sequence_kind
            ):
                raise ValueError(
                    "DecennialPeriod sequence fields must match sequence_truth"
                )

    @property
    def is_major(self) -> bool:
        return self.level == 1

    @property
    def is_sub(self) -> bool:
        return self.level >= 2

    @property
    def level_name(self) -> str:
        if self.level == 1:
            return "Major"
        return "Sub-period"

    @property
    def is_diurnal_solar(self) -> bool:
        return self.sequence_kind == DecennialSequenceKind.DIURNAL_SOLAR

    @property
    def is_nocturnal_lunar(self) -> bool:
        return self.sequence_kind == DecennialSequenceKind.NOCTURNAL_LUNAR

    @property
    def effective_major_planet(self) -> str:
        """Return the active major lord for this period."""

        return self.planet if self.level == 1 else self.major_planet  # type: ignore[return-value]

    @property
    def rotated_sequence(self) -> tuple[str, ...]:
        """Return the major-relative sequence order when preserved sequence truth exists."""

        if not self.sequence:
            return tuple()
        if self.level == 1:
            anchor_index = self.major_index
        else:
            assert self.parent_planet is not None
            anchor_index = self.sequence.index(self.parent_planet)
        return self.sequence[anchor_index:] + self.sequence[:anchor_index]

    @property
    def sequence_position(self) -> int:
        """Return the 1-based position of this period within its relevant sequence."""

        if self.level == 1:
            return self.major_index + 1
        assert self.sub_index is not None
        return self.sub_index + 1

    def is_active_at(self, jd: float) -> bool:
        return self.start_jd <= jd < self.end_jd

    def is_active_distribution_day(self, distribution_day: float) -> bool:
        """Return whether an elapsed lived-day coordinate falls in this period."""

        return (
            self.start_distribution_day
            <= distribution_day
            < self.end_distribution_day
        )

    @property
    def start_dt(self) -> datetime:
        return datetime_from_jd(self.start_jd)

    @property
    def start_calendar(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(self.start_jd)

    @property
    def end_dt(self) -> datetime:
        return datetime_from_jd(self.end_jd)

    @property
    def end_calendar(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(self.end_jd)

    @property
    def days(self) -> float:
        return self.end_jd - self.start_jd

    @property
    def start_distribution_day(self) -> float:
        """Elapsed lived days from the natal sequence origin."""

        return self.start_jd - self.sequence_origin_jd

    @property
    def end_distribution_day(self) -> float:
        """Elapsed lived days from the natal sequence origin."""

        return self.end_jd - self.sequence_origin_jd

    @property
    def distribution_years(self) -> float:
        """Nominal 360-day distribution years represented by this period."""

        return self.days / (12.0 * self.month_basis_days)


@dataclass(slots=True)
class DecennialPeriodGroup:
    """Recursive relation vessel for one non-major Decennials period and its children."""

    period: DecennialPeriod
    sub_groups: list["DecennialPeriodGroup"]

    def __post_init__(self) -> None:
        if self.period.level != 2:
            raise ValueError(
                "DecennialPeriodGroup.period must be an admitted level-2 "
                f"period, got level {self.period.level}"
            )
        if self.sub_groups:
            raise ValueError(
                "DecennialPeriodGroup level-2 groups must be leaves; "
                "Decennial L3/L4 is not admitted"
            )

    @property
    def level(self) -> int:
        return self.period.level

    @property
    def has_sub_groups(self) -> bool:
        return bool(self.sub_groups)

    @property
    def is_leaf(self) -> bool:
        return not self.sub_groups

    def all_periods_flat(self) -> list[DecennialPeriod]:
        result: list[DecennialPeriod] = [self.period]
        for sub_group in self.sub_groups:
            result.extend(sub_group.all_periods_flat())
        return result

    def active_sub_at(self, jd: float) -> "DecennialPeriodGroup | None":
        for sub_group in self.sub_groups:
            if sub_group.period.is_active_at(jd):
                return sub_group
        return None


@dataclass(slots=True)
class DecennialMajorGroup:
    """Relational vessel binding one Decennials major period to its sub-periods."""

    major: DecennialPeriod
    subs: list[DecennialPeriod]
    sub_groups: list[DecennialPeriodGroup] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.major.level != 1:
            raise ValueError(
                f"DecennialMajorGroup.major must be a level-1 period, got level {self.major.level}"
            )
        for sub in self.subs:
            if sub.level != 2:
                raise ValueError(
                    f"DecennialMajorGroup.subs must contain only level-2 periods, got level {sub.level}"
                )
            if sub.major_planet != self.major.planet:
                raise ValueError(
                    f"DecennialMajorGroup.sub-period '{sub.planet}' must preserve major_planet '{self.major.planet}'"
                )
            if sub.major_index != self.major.major_index:
                raise ValueError(
                    f"DecennialMajorGroup.sub-period '{sub.planet}' must preserve major_index {self.major.major_index}"
                )
        for i in range(len(self.subs) - 1):
            if self.subs[i].start_jd >= self.subs[i + 1].start_jd:
                raise ValueError("DecennialMajorGroup.subs must be in chronological order")
        if not self.sub_groups and self.subs:
            self.sub_groups = [DecennialPeriodGroup(period=sub, sub_groups=[]) for sub in self.subs]
        if len(self.sub_groups) != len(self.subs):
            raise ValueError("DecennialMajorGroup.sub_groups must provide one recursive group per immediate sub-period")
        for sub_group, sub_period in zip(self.sub_groups, self.subs):
            if sub_group.period is not sub_period:
                raise ValueError("DecennialMajorGroup.sub_groups must align to subs in chronological order")

    @property
    def sub_count(self) -> int:
        return len(self.subs)

    @property
    def has_subs(self) -> bool:
        return bool(self.subs)

    @property
    def luminary_subs(self) -> list[DecennialPeriod]:
        return [sub for sub in self.subs if sub.planet in _DECENNIAL_LUMINARIES]

    @property
    def planetary_subs(self) -> list[DecennialPeriod]:
        return [sub for sub in self.subs if sub.planet in _DECENNIAL_PLANETARIES]

    @property
    def is_complete(self) -> bool:
        return self.sub_count in (0, 7)

    @property
    def has_sub_groups(self) -> bool:
        return bool(self.sub_groups)

    def all_periods_flat(self) -> list[DecennialPeriod]:
        result: list[DecennialPeriod] = [self.major]
        for sub_group in self.sub_groups:
            result.extend(sub_group.all_periods_flat())
        return result

    def active_sub_at(self, jd: float) -> DecennialPeriod | None:
        for sub in self.subs:
            if sub.is_active_at(jd):
                return sub
        return None

    def active_sub_group_at(self, jd: float) -> DecennialPeriodGroup | None:
        for sub_group in self.sub_groups:
            if sub_group.period.is_active_at(jd):
                return sub_group
        return None


def _normalize_lon(lon: float) -> float:
    return lon % 360.0


def _require_admitted_decennial_periods(
    periods: list[DecennialPeriod],
    *,
    caller: str,
) -> None:
    if any(period.level > _DECENNIAL_MAX_LEVEL for period in periods):
        raise ValueError(f"{caller}: Decennial levels 3–4 are not admitted")
    if any(period.deep_subdivision_method is not None for period in periods):
        raise ValueError(
            f"{caller}: Decennial deep_subdivision_method is not admitted"
        )
    if periods:
        first = periods[0]
        if (
            first.time_basis
            != DecennialTimeBasis.VALENS_LIVED_DAYS_TO_360_DAY_DISTRIBUTION
        ):
            raise ValueError(f"{caller}: Decennial time_basis is not admitted")
        if (
            first.calendar_projection_basis
            != DecennialTimeBasis.ELAPSED_JULIAN_DAYS_FROM_NATAL_JD
        ):
            raise ValueError(
                f"{caller}: Decennial calendar_projection_basis is not admitted"
            )
        if not math.isfinite(first.sequence_origin_jd):
            raise ValueError(
                f"{caller}: Decennial sequence_origin_jd must be finite"
            )
        if any(
            period.time_basis != first.time_basis
            or period.calendar_projection_basis != first.calendar_projection_basis
            or period.sequence_origin_jd != first.sequence_origin_jd
            for period in periods[1:]
        ):
            raise ValueError(
                f"{caller}: Decennial periods must preserve one time-basis "
                "and sequence-origin receipt"
            )
        sequence_truths = [
            period.sequence_truth
            for period in periods
            if period.sequence_truth is not None
        ]
        if sequence_truths:
            first_truth = sequence_truths[0]
            if (
                len(sequence_truths) != len(periods)
                or first_truth.status
                is not TimelordEvaluationStatus.EVALUATED
                or any(
                    truth != first_truth
                    for truth in sequence_truths[1:]
                )
            ):
                raise ValueError(
                    f"{caller}: Decennial periods must preserve one "
                    "evaluated sequence-assembly truth"
                )


def _validate_decennial_positions(natal_positions: dict[str, float]) -> None:
    if not isinstance(natal_positions, dict):
        raise TypeError("natal_positions must be a dict of classical planet longitudes")
    missing = [planet for planet in _DECENNIAL_PLANETS if planet not in natal_positions]
    if missing:
        raise ValueError(f"decennials: natal_positions missing required planets: {missing}")
    for planet in _DECENNIAL_PLANETS:
        lon = natal_positions[planet]
        if not math.isfinite(lon):
            raise ValueError(f"decennials: natal_positions[{planet!r}] must be finite")


def decennial_sequence_truth(
    natal_positions: dict[str, float],
    is_day_chart: bool,
) -> DecennialSequenceAssemblyTruth:
    """Return typed sect-light sequence truth without private tie-breaking."""

    if not isinstance(is_day_chart, bool):
        raise ValueError("is_day_chart must be a boolean")
    _validate_decennial_positions(natal_positions)
    sect_light = "Sun" if is_day_chart else "Moon"
    start_lon = _normalize_lon(natal_positions[sect_light])
    body_truths = tuple(
        DecennialSequenceBodyTruth(
            planet=planet,
            longitude=_normalize_lon(natal_positions[planet]),
            forward_arc_from_sect_light_deg=(
                _normalize_lon(natal_positions[planet]) - start_lon
            )
            % 360.0,
            is_sect_light=planet == sect_light,
        )
        for planet in _DECENNIAL_PLANETS
    )
    ambiguous_groups = _decennial_ambiguous_groups(body_truths)

    sequence_kind = _decennial_sequence_kind(is_day_chart)
    if ambiguous_groups:
        return DecennialSequenceAssemblyTruth(
            status=TimelordEvaluationStatus.NOT_EVALUABLE,
            is_day_chart=is_day_chart,
            sect_light=sect_light,
            sequence_kind=sequence_kind,
            sect_light_longitude=start_lon,
            body_truths=body_truths,
            sequence=None,
            ambiguous_groups=ambiguous_groups,
            reason="non_sect_longitude_tie",
        )

    sequence = tuple(
        item.planet
        for item in sorted(
            body_truths,
            key=lambda item: (
                item.forward_arc_from_sect_light_deg,
                0 if item.is_sect_light else 1,
            ),
        )
    )
    return DecennialSequenceAssemblyTruth(
        status=TimelordEvaluationStatus.EVALUATED,
        is_day_chart=is_day_chart,
        sect_light=sect_light,
        sequence_kind=sequence_kind,
        sect_light_longitude=start_lon,
        body_truths=body_truths,
        sequence=sequence,
    )


def _append_decennial_children(
    parent: DecennialPeriod,
    *,
    sequence: tuple[str, ...],
    target_level: int,
    periods: list[DecennialPeriod],
) -> None:
    if target_level > _DECENNIAL_MAX_LEVEL:
        raise ValueError(
            "_append_decennial_children: Decennial levels 3–4 are not admitted"
        )
    if parent.level >= target_level:
        return

    next_level = parent.level + 1
    try:
        anchor_index = sequence.index(parent.planet)
    except ValueError as exc:
        raise ValueError(f"_append_decennial_children: parent planet {parent.planet!r} not found in preserved sequence") from exc
    rotated = sequence[anchor_index:] + sequence[:anchor_index]
    child_cursor = parent.start_jd
    total_days = parent.days
    total_months = parent.months
    denominator = float(_DECENNIAL_MAJOR_MONTHS)

    for child_index, child_planet in enumerate(rotated):
        share = float(_DECENNIAL_MONTHS[child_planet]) / denominator
        child_days = total_days * share
        child_months = total_months * share
        child_end = child_cursor + child_days
        child = DecennialPeriod(
            level=next_level,
            planet=child_planet,
            start_jd=child_cursor,
            end_jd=child_end,
            years=child_months / 12.0,
            months=child_months,
            sequence_origin_jd=parent.sequence_origin_jd,
            time_basis=parent.time_basis,
            calendar_projection_basis=parent.calendar_projection_basis,
            major_planet=parent.planet if parent.level == 1 else parent.major_planet,
            parent_planet=parent.planet,
            parent_level=parent.level,
            is_day_chart=parent.is_day_chart,
            sect_light=parent.sect_light,
            sequence_kind=parent.sequence_kind,
            deep_subdivision_method=None,
            sequence=sequence,
            ancestor_planets=parent.ancestor_planets + (parent.planet,),
            major_index=parent.major_index,
            sub_index=child_index,
            major_month_total=parent.major_month_total,
            month_basis_days=parent.month_basis_days,
            sequence_truth=parent.sequence_truth,
        )
        periods.append(child)
        _append_decennial_children(
            child,
            sequence=sequence,
            target_level=target_level,
            periods=periods,
        )
        child_cursor = child_end


def decennials(
    natal_jd: float,
    natal_positions: dict[str, float],
    is_day_chart: bool,
    *,
    levels: int = 2,
    policy: "TimelordComputationPolicy | None" = None,
) -> list[DecennialPeriod]:
    """
    Generate admitted Decennials major periods and Level-2 sub-periods.

    The minimum admitted Moira engine starts from the sect light, orders the
    seven classical planets by zodiacal succession from that point, assigns
    129 months to each major period, and subdivides each major by the
    transmitted unequal month-allotments of the seven classical planets.
    Its 30-day months are schematic distribution units. ``start_jd`` and
    ``end_jd`` project the resulting elapsed-day offsets from ``natal_jd``;
    they are not civil-calendar month arithmetic.
    Levels 3–4 are outside the closed admitted contract. A future expansion
    would require a new source-admission project and independent validation.
    """
    if not math.isfinite(natal_jd):
        raise ValueError(f"decennials: natal_jd must be finite, got {natal_jd!r}")
    if not (1 <= levels <= _DECENNIAL_MAX_LEVEL):
        raise ValueError(f"decennials: levels must be 1–{_DECENNIAL_MAX_LEVEL}")
    _validate_decennial_positions(natal_positions)
    pol = _resolve_timelord_policy(policy)

    sequence_truth = decennial_sequence_truth(
        natal_positions,
        is_day_chart,
    )
    if (
        sequence_truth.status
        is not TimelordEvaluationStatus.EVALUATED
        or sequence_truth.sequence is None
    ):
        groups = ", ".join(
            "/".join(group)
            for group in sequence_truth.ambiguous_groups
        )
        raise ValueError(
            "decennials: sequence is not evaluable because non-sect "
            f"longitudes are tied ({groups})"
        )
    sequence = list(sequence_truth.sequence)
    sect_light = "Sun" if is_day_chart else "Moon"
    sequence_kind = _decennial_sequence_kind(is_day_chart)
    major_months = float(pol.decennials.major_months)
    month_basis_days = float(pol.decennials.month_basis_days)
    major_days = major_months * month_basis_days
    periods: list[DecennialPeriod] = []
    cursor_jd = natal_jd

    for major_index, major_planet in enumerate(sequence):
        major_start = cursor_jd
        major_end = major_start + major_days
        periods.append(
            DecennialPeriod(
                level=1,
                planet=major_planet,
                start_jd=major_start,
                end_jd=major_end,
                years=major_months / 12.0,
                months=major_months,
                sequence_origin_jd=natal_jd,
                time_basis=pol.decennials.time_basis,
                calendar_projection_basis=pol.decennials.calendar_projection_basis,
                is_day_chart=is_day_chart,
                sect_light=sect_light,
                sequence_kind=sequence_kind,
                sequence=tuple(sequence),
                ancestor_planets=tuple(),
                major_index=major_index,
                major_month_total=major_months,
                month_basis_days=month_basis_days,
                sequence_truth=sequence_truth,
            )
        )

        if levels >= 2:
            _append_decennial_children(
                periods[-1],
                sequence=tuple(sequence),
                target_level=levels,
                periods=periods,
            )

        cursor_jd = major_end

    return periods


def current_decennials(
    natal_jd: float,
    natal_positions: dict[str, float],
    is_day_chart: bool,
    current_jd: float,
    *,
    levels: int = 2,
    policy: "TimelordComputationPolicy | None" = None,
) -> tuple[DecennialPeriod, DecennialPeriod]:
    """Return the active periods at an elapsed lived-day coordinate."""
    if not math.isfinite(current_jd):
        raise ValueError(f"current_decennials: current_jd must be finite, got {current_jd!r}")
    if current_jd < natal_jd:
        raise ValueError("current_decennials: current_jd must not be earlier than natal_jd")

    periods = decennials(natal_jd, natal_positions, is_day_chart, levels=levels, policy=policy)
    major_periods = [period for period in periods if period.level == 1]
    current_distribution_day = current_jd - natal_jd

    active_major = next(
        (
            period
            for period in major_periods
            if period.is_active_distribution_day(current_distribution_day)
        ),
        None,
    )
    if active_major is None:
        raise ValueError(
            f"current_jd {current_jd} falls outside the Decennials cycle starting at natal_jd {natal_jd}."
        )

    if levels == 1:
        return active_major, active_major

    active_leaf = max(
        (
            period
            for period in periods
            if period.level >= 2
            and period.is_active_distribution_day(current_distribution_day)
        ),
        key=lambda period: period.level,
        default=None,
    )
    if active_leaf is None:
        raise ValueError(
            f"current_decennials: no active sub-period found at jd {current_jd} inside major {active_major.planet}"
        )
    return active_major, active_leaf


def validate_decennials_output(periods: list[DecennialPeriod]) -> None:
    """Verify that a decennials() output satisfies ordering and containment invariants."""
    _require_admitted_decennial_periods(
        periods,
        caller="validate_decennials_output",
    )
    by_level: dict[int, list[DecennialPeriod]] = {
        level: [period for period in periods if period.level == level]
        for level in range(1, _DECENNIAL_MAX_LEVEL + 1)
    }
    level1 = by_level[1]

    for index in range(len(level1) - 1):
        if level1[index].end_jd > level1[index + 1].start_jd + 1e-9:
            raise ValueError(
                f"validate_decennials_output: level-1 periods overlap or are out of order "
                f"('{level1[index].planet}' end_jd={level1[index].end_jd:.6f} > "
                f"'{level1[index + 1].planet}' start_jd={level1[index + 1].start_jd:.6f})"
            )

    path_map: dict[tuple[int, tuple[str, ...]], DecennialPeriod] = {}
    child_groups: dict[tuple[int, tuple[str, ...]], list[DecennialPeriod]] = {}

    for period in periods:
        path = period.ancestor_planets + (period.planet,)
        key = (period.level, path)
        if key in path_map:
            raise ValueError(
                f"validate_decennials_output: duplicate Decennials lineage path {path} at level {period.level}"
            )
        path_map[key] = period
        if period.level >= 2:
            if period.parent_level != period.level - 1:
                raise ValueError(
                    f"validate_decennials_output: period '{period.planet}' (L{period.level}) must preserve parent_level={period.level - 1}"
                )
            if len(period.ancestor_planets) != period.level - 1:
                raise ValueError(
                    f"validate_decennials_output: period '{period.planet}' (L{period.level}) has ancestor path length {len(period.ancestor_planets)}, expected {period.level - 1}"
                )
            parent_path = period.ancestor_planets
            child_groups.setdefault((period.level - 1, parent_path), []).append(period)

    for major in level1:
        if major.sequence_kind != _decennial_sequence_kind(bool(major.is_day_chart)):
            raise ValueError(
                f"validate_decennials_output: major '{major.planet}' has inconsistent sequence_kind truth"
            )
        if major.sequence and major.sequence[major.major_index % len(major.sequence)] != major.planet:
            raise ValueError(
                f"validate_decennials_output: major '{major.planet}' has inconsistent preserved sequence position"
            )

    for level in range(2, _DECENNIAL_MAX_LEVEL + 1):
        for period in by_level[level]:
            parent_key = (level - 1, period.ancestor_planets)
            parent = path_map.get(parent_key)
            if parent is None:
                raise ValueError(
                    f"validate_decennials_output: level-{level} period '{period.planet}' references unknown parent path {period.ancestor_planets}"
                )
            if period.start_jd < parent.start_jd - 1e-9 or period.end_jd > parent.end_jd + 1e-9:
                raise ValueError(
                    f"validate_decennials_output: period '{period.planet}' (L{level}) escapes parent '{parent.planet}' (L{level - 1})"
                )
            if period.sequence != parent.sequence:
                raise ValueError(
                    f"validate_decennials_output: period '{period.planet}' (L{level}) must preserve sequence truth of parent '{parent.planet}'"
                )
            if period.sequence_kind != parent.sequence_kind:
                raise ValueError(
                    f"validate_decennials_output: period '{period.planet}' (L{level}) must preserve sequence_kind of parent '{parent.planet}'"
                )
            if period.major_index != parent.major_index:
                raise ValueError(
                    f"validate_decennials_output: period '{period.planet}' (L{level}) must preserve major_index of parent '{parent.planet}'"
                )
            if period.major_planet != parent.major_planet and not (parent.level == 1 and period.major_planet == parent.planet):
                raise ValueError(
                    f"validate_decennials_output: period '{period.planet}' (L{level}) must preserve major_planet truth"
                )
            if period.parent_planet != parent.planet:
                raise ValueError(
                    f"validate_decennials_output: period '{period.planet}' (L{level}) must preserve immediate parent planet '{parent.planet}'"
                )

    for parent_key, children in child_groups.items():
        parent = path_map[parent_key]
        children.sort(key=lambda period: period.start_jd)
        for index in range(len(children) - 1):
            if children[index].end_jd > children[index + 1].start_jd + 1e-9:
                raise ValueError(
                    f"validate_decennials_output: children of '{parent.planet}' (L{parent.level}) overlap or are out of order"
                )
        total_days = 0.0
        total_months = 0.0
        for expected_sub_index, child in enumerate(children):
            if child.sub_index != expected_sub_index:
                raise ValueError(
                    f"validate_decennials_output: child '{child.planet}' of '{parent.planet}' has sub_index={child.sub_index}, expected {expected_sub_index}"
                )
            total_days += child.days
            total_months += child.months
        if abs(total_days - parent.days) > 1e-6:
            raise ValueError(
                f"validate_decennials_output: child day spans of '{parent.planet}' sum to {total_days}, expected {parent.days}"
            )
        if abs(total_months - parent.months) > 1e-6:
            raise ValueError(
                f"validate_decennials_output: child month spans of '{parent.planet}' sum to {total_months}, expected {parent.months}"
            )


def group_decennials(periods: list[DecennialPeriod]) -> list[DecennialMajorGroup]:
    """Group a flat Decennials output into major-period relation vessels."""
    _require_admitted_decennial_periods(periods, caller="group_decennials")

    def _build_decennial_sub_groups(parent: DecennialPeriod) -> list[DecennialPeriodGroup]:
        children = [
            period for period in periods
            if period.parent_level == parent.level
            and period.parent_planet == parent.planet
            and period.major_index == parent.major_index
            and period.ancestor_planets == parent.ancestor_planets + (parent.planet,)
        ]
        children.sort(key=lambda period: period.start_jd)
        return [
            DecennialPeriodGroup(
                period=child,
                sub_groups=_build_decennial_sub_groups(child),
            )
            for child in children
        ]

    major_periods = [period for period in periods if period.level == 1]

    groups: list[DecennialMajorGroup] = []
    for major in major_periods:
        sub_groups = _build_decennial_sub_groups(major)
        subs = [sub_group.period for sub_group in sub_groups]
        groups.append(DecennialMajorGroup(major=major, subs=subs, sub_groups=sub_groups))
    return groups


# ---------------------------------------------------------------------------
# Zodiacal Releasing — tables
# ---------------------------------------------------------------------------

#: Ptolemy's Minor Years — duration (in years) for each sign's releasing period
MINOR_YEARS: dict[str, int] = {
    "Aries":       15,
    "Taurus":       8,
    "Gemini":      20,
    "Cancer":      25,
    "Leo":         19,
    "Virgo":       20,
    "Libra":        8,
    "Scorpio":     15,
    "Sagittarius": 12,
    "Capricorn":   27,
    "Aquarius":    30,
    "Pisces":      12,
}

#: Total of all Minor Years — one full zodiacal releasing circuit = 211 years
_TOTAL_MINOR_YEARS: int = sum(MINOR_YEARS.values())

_ZR_YEAR_DAYS = 360.0
_ZR_MONTH_DAYS = 30.0
_ZR_LEVEL_DAYS: dict[int, float] = {
    1: _ZR_YEAR_DAYS,
    2: _ZR_MONTH_DAYS,
    3: _ZR_MONTH_DAYS / 12.0,
    4: (_ZR_MONTH_DAYS / 12.0) / 12.0,
}
_ZR_MAX_LEVEL = 4
_ZR_CAP_DAYS = _TOTAL_MINOR_YEARS * _ZR_YEAR_DAYS
# Valens IV.4 defines the complete circuit as 17 years 7 months, or
# 211 symbolic months. A starting sign whose allotment exceeds that circuit
# transfers the remaining time to its opposite after the circuit completes.
_ZR_COMPLETE_CIRCUIT_MONTHS = 211
_ZR_LONG_SIGNS = {
    sign
    for sign, years in MINOR_YEARS.items()
    if years * 12 > _ZR_COMPLETE_CIRCUIT_MONTHS
}


# ---------------------------------------------------------------------------
# Phase 4 — Doctrine / Policy Surface
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class FirdarYearPolicy:
    """
    Doctrine surface for the Firdaria year-length constant.

    year_days governs the conversion of Firdaria major-period lengths (in
    years) to Julian Day boundaries. Default: 365.25 (Julian year).
    Changing this value scales all Firdaria period boundaries uniformly
    without altering the sequence order or sub-period proportions.
    """
    year_days: float = _JULIAN_YEAR

    def __post_init__(self) -> None:
        if not math.isfinite(self.year_days) or self.year_days <= 0.0:
            raise ValueError(
                "FirdarYearPolicy.year_days must be finite and positive"
            )


@dataclass(frozen=True, slots=True)
class DecennialPolicy:
    """
    Doctrine surface for the admitted minimum Decennials engine.

    This policy freezes the currently admitted doctrine explicitly, including
    the Valens lived-day/360-day distribution basis and its elapsed-JD
    projection. Historical variants are outside this fixed contract and are
    not selectable.
    """

    start_lord_basis: str = "sect_light"
    sequence_mode: str = "zodiacal_from_sect_light"
    subperiod_mode: str = "rotated_minor_months"
    major_months: float = float(_DECENNIAL_MAJOR_MONTHS)
    month_basis_days: float = _DECENNIAL_MONTH_DAYS
    time_basis: str = DecennialTimeBasis.VALENS_LIVED_DAYS_TO_360_DAY_DISTRIBUTION
    calendar_projection_basis: str = DecennialTimeBasis.ELAPSED_JULIAN_DAYS_FROM_NATAL_JD
    deep_subdivision_method: None = None

    def __post_init__(self) -> None:
        if self.start_lord_basis != "sect_light":
            raise ValueError(
                "DecennialPolicy.start_lord_basis must remain 'sect_light'"
            )
        if self.sequence_mode != "zodiacal_from_sect_light":
            raise ValueError(
                "DecennialPolicy.sequence_mode must remain "
                "'zodiacal_from_sect_light'"
            )
        if self.subperiod_mode != "rotated_minor_months":
            raise ValueError(
                "DecennialPolicy.subperiod_mode must remain "
                "'rotated_minor_months'"
            )
        if (
            not math.isfinite(self.major_months)
            or not math.isclose(
                self.major_months,
                float(_DECENNIAL_MAJOR_MONTHS),
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        ):
            raise ValueError(
                "DecennialPolicy.major_months must preserve the admitted "
                f"{_DECENNIAL_MAJOR_MONTHS}-month major period"
            )
        if (
            not math.isfinite(self.month_basis_days)
            or not math.isclose(
                self.month_basis_days,
                _DECENNIAL_MONTH_DAYS,
                rel_tol=0.0,
                abs_tol=1e-12,
            )
        ):
            raise ValueError(
                "DecennialPolicy.month_basis_days must preserve the admitted "
                f"{_DECENNIAL_MONTH_DAYS}-day symbolic month"
            )
        if (
            self.time_basis
            != DecennialTimeBasis.VALENS_LIVED_DAYS_TO_360_DAY_DISTRIBUTION
        ):
            raise ValueError(
                "DecennialPolicy.time_basis must preserve the admitted "
                "Valens lived-day distribution"
            )
        if (
            self.calendar_projection_basis
            != DecennialTimeBasis.ELAPSED_JULIAN_DAYS_FROM_NATAL_JD
        ):
            raise ValueError(
                "DecennialPolicy.calendar_projection_basis must preserve "
                "elapsed Julian days from natal_jd"
            )
        if self.deep_subdivision_method is not None:
            raise ValueError(
                "DecennialPolicy deep_subdivision_method is not admitted; "
                "the public contract ends at L2"
            )


@dataclass(frozen=True, slots=True)
class ZRYearPolicy:
    """
    Doctrine surface for the Zodiacal Releasing symbolic-year constant.

    year_days is the number of Julian days per symbolic year at Level 1.
    Level 2–4 unit scaling is derived as year_days÷12, year_days÷144,
    year_days÷1728. Default: 360.0 (Hellenistic symbolic year).
    Changing this value scales all ZR period boundaries uniformly without
    altering sign sequence, LB doctrine, or peak detection.
    """
    year_days: float = _ZR_YEAR_DAYS

    def __post_init__(self) -> None:
        if not math.isfinite(self.year_days) or self.year_days <= 0.0:
            raise ValueError(
                "ZRYearPolicy.year_days must be finite and positive"
            )


@dataclass(frozen=True, slots=True)
class TimelordComputationPolicy:
    """
    Lean doctrine surface for the Timelord subsystem.

    The default policy preserves current behavior exactly. Override
    sub-policies to govern year-length constants without altering
    per-chart inputs (is_day_chart, variant, lot_longitude, etc.).

    firdaria_year  — governs the Julian-year constant for Firdaria
    decennials     — freezes the admitted Decennials doctrine
    zr_year        — governs the symbolic-year constant for Zodiacal Releasing
    """
    firdaria_year: FirdarYearPolicy = field(default_factory=FirdarYearPolicy)
    decennials:    DecennialPolicy  = field(default_factory=DecennialPolicy)
    zr_year:       ZRYearPolicy     = field(default_factory=ZRYearPolicy)


DEFAULT_TIMELORD_POLICY = TimelordComputationPolicy()


def _validate_timelord_policy(
    policy: TimelordComputationPolicy,
) -> TimelordComputationPolicy:
    if not isinstance(policy.firdaria_year, FirdarYearPolicy):
        raise TypeError("policy.firdaria_year must be a FirdarYearPolicy")
    if not isinstance(policy.decennials, DecennialPolicy):
        raise TypeError("policy.decennials must be a DecennialPolicy")
    if not isinstance(policy.zr_year, ZRYearPolicy):
        raise TypeError("policy.zr_year must be a ZRYearPolicy")
    if policy.firdaria_year.year_days <= 0:
        raise ValueError("policy.firdaria_year.year_days must be positive")
    if policy.decennials.start_lord_basis != "sect_light":
        raise ValueError("policy.decennials.start_lord_basis must remain 'sect_light' for the admitted doctrine")
    if policy.decennials.sequence_mode != "zodiacal_from_sect_light":
        raise ValueError("policy.decennials.sequence_mode must remain 'zodiacal_from_sect_light'")
    if policy.decennials.subperiod_mode != "rotated_minor_months":
        raise ValueError("policy.decennials.subperiod_mode must remain 'rotated_minor_months'")
    if abs(policy.decennials.major_months - float(_DECENNIAL_MAJOR_MONTHS)) > 1e-12:
        raise ValueError(f"policy.decennials.major_months must remain {_DECENNIAL_MAJOR_MONTHS}")
    if abs(policy.decennials.month_basis_days - _DECENNIAL_MONTH_DAYS) > 1e-12:
        raise ValueError(f"policy.decennials.month_basis_days must remain {_DECENNIAL_MONTH_DAYS}")
    if (
        policy.decennials.time_basis
        != DecennialTimeBasis.VALENS_LIVED_DAYS_TO_360_DAY_DISTRIBUTION
    ):
        raise ValueError(
            "policy.decennials.time_basis must preserve the admitted Valens "
            "lived-day to 360-day distribution basis"
        )
    if (
        policy.decennials.calendar_projection_basis
        != DecennialTimeBasis.ELAPSED_JULIAN_DAYS_FROM_NATAL_JD
    ):
        raise ValueError(
            "policy.decennials.calendar_projection_basis must preserve "
            "elapsed Julian days from natal_jd"
        )
    if policy.decennials.deep_subdivision_method is not None:
        raise ValueError(
            "policy.decennials.deep_subdivision_method is not admitted; "
            "the closed Decennial contract supports L1/L2 only"
        )
    if policy.zr_year.year_days <= 0:
        raise ValueError("policy.zr_year.year_days must be positive")
    return policy


def _resolve_timelord_policy(
    policy: "TimelordComputationPolicy | None",
) -> "TimelordComputationPolicy":
    return _validate_timelord_policy(
        DEFAULT_TIMELORD_POLICY if policy is None else policy
    )


# ---------------------------------------------------------------------------
# Zodiacal Releasing dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ReleasingPeriod:
    """
    RITE: The Releasing Period Vessel

    THEOREM: Governs the storage of a single period in the Zodiacal Releasing
    time-lord system.

    RITE OF PURPOSE:
        ReleasingPeriod is the authoritative data vessel for a single Zodiacal
        Releasing period produced by the Timelord Engine. It captures the
        hierarchical level (1–4), the sign, the classical domicile ruler, the start
        and end Julian Days, and the duration in years. Without it, callers would
        receive unstructured tuples with no field-level guarantees. It exists to
        give every higher-level consumer a single, named, mutable record of each
        Zodiacal Releasing period.

    LAW OF OPERATION:
        Responsibilities:
            - Store a single Zodiacal Releasing period as named, typed fields
            - Preserve Fortune angularity raw truth and its compatibility fields
            - Expose UTC datetime and CalendarDateTime views via read-only properties
            - Serve as the return type of zodiacal_releasing() and current_releasing()
        Non-responsibilities:
            - Computing period boundaries (delegates to zodiacal_releasing / _generate_releasing)
            - Resolving natal positions from ephemeris (delegates to planets)
        Dependencies:
            - Populated by _generate_releasing()
            - start_dt / end_dt delegate to datetime_from_jd()
            - start_calendar / end_calendar delegate to calendar_datetime_from_jd()
        Structural invariants:
            - level is in [1, 4]
            - sign is a valid member of SIGNS
            - end_jd > start_jd
            - Fortune compatibility fields agree with fortune_angularity_truth
              when raw truth is present
        Behavioral invariants:
            - All consumers treat ReleasingPeriod fields as read-only after construction

    Canon: Vettius Valens, Anthology II; Chris Brennan, "Hellenistic Astrology" Ch.10

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.timelords.ReleasingPeriod",
      "risk": "high",
      "api": {
        "frozen": ["level", "sign", "ruler", "start_jd", "end_jd", "years", "lot_name", "is_loosing_of_bond", "is_peak_period", "angularity_from_fortune", "use_loosing_of_bond", "angularity_class", "fortune_angularity_truth"],
        "internal": ["start_dt", "start_calendar", "end_dt", "end_calendar"]
      },
      "state": {"mutable": true, "owners": ["_generate_releasing"]},
      "effects": {
        "signals_emitted": [],
        "io": []
      },
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    level:    int    # 1 = Level 1 (outermost), 2/3/4 = inner levels
    sign:     str
    ruler:    str    # classical domicile ruler
    start_jd: float
    end_jd:   float
    years:    float
    lot_name: str = "Spirit"
    is_loosing_of_bond: bool = False
    is_peak_period: bool = False
    angularity_from_fortune: int | None = None
    # Phase 1: preserved generative context
    use_loosing_of_bond: bool = True  # whether LB doctrine was active during generation
    # Phase 2: typed classification
    angularity_class: str | None = None  # ZRAngularityClass constant, or None when Fortune is unavailable
    fortune_angularity_truth: ZRFortuneAngularityTruth | None = None

    def __post_init__(self) -> None:
        if self.level not in (1, 2, 3, 4):
            raise ValueError(f"ReleasingPeriod.level must be 1–4, got {self.level}")
        if self.sign not in SIGNS:
            raise ValueError(f"ReleasingPeriod.sign must be a valid zodiac sign, got '{self.sign}'")
        if not math.isfinite(self.start_jd) or not math.isfinite(self.end_jd):
            raise ValueError("ReleasingPeriod start_jd and end_jd must be finite")
        if self.end_jd <= self.start_jd:
            raise ValueError("ReleasingPeriod end_jd must be greater than start_jd")
        if self.angularity_from_fortune is not None:
            if self.angularity_from_fortune not in range(1, 13):
                raise ValueError(
                    "ReleasingPeriod.angularity_from_fortune must be 1–12 or None"
                )
            expected_class = _zr_angularity_class(self.angularity_from_fortune)
            if self.angularity_class != expected_class:
                raise ValueError(
                    "ReleasingPeriod.angularity_class must match angularity_from_fortune"
                )
            expected_peak = self.angularity_from_fortune in _ANGULAR_HOUSES
            if self.is_peak_period != expected_peak:
                raise ValueError(
                    "ReleasingPeriod.is_peak_period must identify angular places from Fortune"
                )
        elif self.angularity_class is not None or self.is_peak_period:
            raise ValueError(
                "ReleasingPeriod Fortune angularity fields require angularity_from_fortune"
            )
        if self.fortune_angularity_truth is not None:
            truth = self.fortune_angularity_truth
            if truth.period_sign != self.sign:
                raise ValueError(
                    "ReleasingPeriod Fortune truth must describe its period sign"
                )
            if truth.status is TimelordEvaluationStatus.EVALUATED:
                if (
                    truth.angularity_from_fortune
                    != self.angularity_from_fortune
                    or truth.angularity_class != self.angularity_class
                    or truth.is_peak_period is not self.is_peak_period
                ):
                    raise ValueError(
                        "ReleasingPeriod compatibility angularity fields must "
                        "match evaluated Fortune truth"
                    )
            elif (
                self.angularity_from_fortune is not None
                or self.angularity_class is not None
                or self.is_peak_period
            ):
                raise ValueError(
                    "ReleasingPeriod not_evaluable Fortune truth cannot "
                    "assemble angularity or peak compatibility fields"
                )
    # --- Phase 3: inspectability ---

    @property
    def level_name(self) -> str:
        """Human-readable level label: 'Level 1' through 'Level 4'."""
        return f"Level {self.level}"

    @property
    def days(self) -> float:
        """Duration of this period in Julian days."""
        return self.end_jd - self.start_jd

    def is_active_at(self, jd: float) -> bool:
        """
        Return True if *jd* falls within this period.

        The interval is half-open: [start_jd, end_jd).
        This is the canonical boundary convention used throughout the engine.
        """
        return self.start_jd <= jd < self.end_jd

    # --- Datetime views ---

    @property
    def start_dt(self) -> datetime:
        """UTC datetime of the period start."""
        return datetime_from_jd(self.start_jd)

    @property
    def start_calendar(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(self.start_jd)

    @property
    def end_dt(self) -> datetime:
        """UTC datetime of the period end."""
        return datetime_from_jd(self.end_jd)

    @property
    def end_calendar(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(self.end_jd)

    def __repr__(self) -> str:
        flags: list[str] = []
        if self.is_loosing_of_bond:
            flags.append("LB")
        if self.is_peak_period:
            flags.append("Peak")
        flag_text = f" [{' / '.join(flags)}]" if flags else ""
        return (
            f"ReleasingPeriod(L{self.level} {self.sign:<13} "
            f"({self.ruler:<8}) {self.years:.3f} yrs | "
            f"{self.start_calendar.date_string()} → "
            f"{self.end_calendar.date_string()}){flag_text}"
        )


# ---------------------------------------------------------------------------
# Phase 5 — Relational Formalization: Zodiacal Releasing
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ZRPeriodGroup:
    """
    RITE: The Zodiacal Releasing Period Group Vessel

    Formalizes the containment relation between a Zodiacal Releasing period
    and the deeper-level periods it contains.

    Previously this relation was implicit — callers received a flat list from
    zodiacal_releasing() and had to infer containment by JD overlap.
    ZRPeriodGroup makes the level-by-level nesting explicit and navigable.

    Fields
    ------
    period      — the period at this level (any level 1–4)
    sub_groups  — ZRPeriodGroup vessels for the next level within this period,
                  in chronological order (empty at the deepest generated level)
    """
    period:     ReleasingPeriod
    sub_groups: list["ZRPeriodGroup"]

    def __post_init__(self) -> None:
        # Phase 6 hardening — temporal containment of each immediate sub-group
        for sg in self.sub_groups:
            if sg.period.start_jd < self.period.start_jd - 1e-6:
                raise ValueError(
                    f"ZRPeriodGroup sub-group '{sg.period.sign}' (L{sg.period.level}) "
                    f"starts before its parent period"
                )
            if sg.period.end_jd > self.period.end_jd + 1e-6:
                raise ValueError(
                    f"ZRPeriodGroup sub-group '{sg.period.sign}' (L{sg.period.level}) "
                    f"ends after its parent period"
                )

    @property
    def level(self) -> int:
        """Level of the contained period (1–4)."""
        return self.period.level

    @property
    def has_sub_groups(self) -> bool:
        """True when deeper-level groups exist within this period."""
        return bool(self.sub_groups)

    # --- Phase 6: inspectability ---

    @property
    def is_leaf(self) -> bool:
        """True when this group has no deeper sub-groups (deepest generated level)."""
        return not self.sub_groups

    @property
    def angularity_class(self) -> str | None:
        """ZRAngularityClass string for this period, or None if not a peak period."""
        return self.period.angularity_class

    def all_periods_flat(self) -> list[ReleasingPeriod]:
        """Return all periods in this group and its sub-groups in depth-first order."""
        result: list[ReleasingPeriod] = [self.period]
        for sg in self.sub_groups:
            result.extend(sg.all_periods_flat())
        return result

    def active_sub_at(self, jd: float) -> "ZRPeriodGroup | None":
        """Return the sub-group active at *jd*, or None if none applies."""
        for sg in self.sub_groups:
            if sg.period.is_active_at(jd):
                return sg
        return None


def _group_releasing_level(
    all_periods: list[ReleasingPeriod],
    level: int,
    start_jd: float,
    end_jd: float,
) -> list[ZRPeriodGroup]:
    this_level = [
        p for p in all_periods
        if p.level == level
        and p.start_jd >= start_jd - 1e-9
        and p.end_jd   <= end_jd   + 1e-9
    ]
    return [
        ZRPeriodGroup(
            period=p,
            sub_groups=_group_releasing_level(all_periods, level + 1, p.start_jd, p.end_jd),
        )
        for p in this_level
    ]


def group_releasing(periods: list[ReleasingPeriod]) -> list[ZRPeriodGroup]:
    """
    Group a flat Zodiacal Releasing period list into ZRPeriodGroup vessels.

    The input must be the output of zodiacal_releasing(). Level 1 periods
    form the outermost groups; each is recursively populated with the Level 2
    periods it contains, which are in turn populated with their Level 3
    children, and so on.

    Returns
    -------
    list[ZRPeriodGroup]
        One top-level group per Level 1 period, in chronological order.
    """
    if not periods:
        return []
    return _group_releasing_level(periods, level=1, start_jd=-math.inf, end_jd=math.inf)


# ---------------------------------------------------------------------------
# Phase 7 — Integrated Local Condition
# ---------------------------------------------------------------------------

def _firdaria_lord_type(planet: str, is_node_period: bool) -> str:
    """Return the lord-type label for a Firdaria planet.

    Returns one of: ``"luminary"``, ``"planet"``, ``"node"``.
    """
    if is_node_period:
        return "node"
    if planet in _FIRDARIA_LUMINARIES:
        return "luminary"
    return "planet"


def _decennial_lord_type(planet: str) -> str:
    """Return the lord-type label for a Decennials planet."""

    if planet in _DECENNIAL_LUMINARIES:
        return "luminary"
    return "planet"


@dataclass(slots=True)
class FirdarConditionProfile:
    """
    Integrated local condition profile for a single Firdaria period.

    Assembles all preserved, classified, and inspectable truth from
    Phases 1–6 into one coherent per-period vessel. This is the
    authoritative structural summary of a FirdarPeriod — callers do not
    need to inspect multiple fields across the period and relation layers
    to understand what kind of period they are looking at.

    Fields
    ------
    planet          — the ruling planet of this period
    level           — 1 (major) or 2 (sub-period)
    level_name      — human-readable level: "Major" or "Sub-period"
    is_major        — True when level == 1
    is_node_period  — True when the ruling planet is North Node or South Node
    lord_type       — "luminary" | "planet" | "node"
    sequence_kind   — FirdarSequenceKind constant, or None if not set
    major_planet    — the level-1 lord this sub-period belongs to (None for majors)
    is_day_chart    — True for diurnal chart; False for nocturnal; None if not set
    years           — nominal duration in Firdaria years
    days            — duration in Julian days
    """
    planet:         str
    level:          int
    level_name:     str
    is_major:       bool
    is_node_period: bool
    lord_type:      str
    sequence_kind:  str | None
    major_planet:   str | None
    is_day_chart:   bool | None
    years:          float
    days:           float


def firdar_condition_profile(period: FirdarPeriod) -> FirdarConditionProfile:
    """
    Build a FirdarConditionProfile from a FirdarPeriod.

    Assembles all Phase 1–6 truth about the period into a single profile.
    This function is deterministic and has no side effects.

    Parameters
    ----------
    period : FirdarPeriod
        Any FirdarPeriod produced by firdaria() or current_firdaria().

    Returns
    -------
    FirdarConditionProfile
    """
    return FirdarConditionProfile(
        planet         = period.planet,
        level          = period.level,
        level_name     = period.level_name,
        is_major       = period.is_major,
        is_node_period = period.is_node_period,
        lord_type      = _firdaria_lord_type(period.planet, period.is_node_period),
        sequence_kind  = period.sequence_kind,
        major_planet   = period.major_planet,
        is_day_chart   = period.is_day_chart,
        years          = period.years,
        days           = period.days,
    )


@dataclass(slots=True)
class DecennialConditionProfile:
    """Integrated local condition profile for one Decennials period."""

    planet:                str
    level:                 int
    level_name:            str
    is_major:              bool
    lord_type:             str
    sequence_kind:         str | None
    major_planet:          str | None
    parent_planet:         str | None
    parent_level:          int | None
    ancestor_planets:      tuple[str, ...]
    effective_major_planet:str
    is_day_chart:          bool | None
    sect_light:            str | None
    major_index:           int
    sub_index:             int | None
    sequence_position:     int
    deep_subdivision_method: None
    years:                 float
    months:                float
    days:                  float
    month_basis_days:      float
    time_basis:            str
    calendar_projection_basis: str
    sequence_origin_jd:    float
    start_distribution_day: float
    end_distribution_day:  float
    distribution_years:    float

    def __post_init__(self) -> None:
        if self.level not in (1, 2):
            raise ValueError(
                "DecennialConditionProfile level must be 1 or 2"
            )
        if self.is_major is not (self.level == 1):
            raise ValueError(
                "DecennialConditionProfile is_major must match level"
            )
        expected_name = "Major" if self.level == 1 else "Sub-period"
        if self.level_name != expected_name:
            raise ValueError(
                "DecennialConditionProfile level_name must match level"
            )
        if self.deep_subdivision_method is not None:
            raise ValueError(
                "DecennialConditionProfile deep_subdivision_method is not "
                "admitted"
            )
        if self.level == 1 and (
            self.major_planet is not None
            or self.parent_planet is not None
            or self.parent_level is not None
            or self.sub_index is not None
            or self.ancestor_planets
        ):
            raise ValueError(
                "DecennialConditionProfile major periods cannot carry "
                "sub-period lineage"
            )
        if self.level == 2 and (
            self.major_planet is None
            or self.parent_planet is None
            or self.parent_level != 1
            or self.sub_index is None
            or len(self.ancestor_planets) != 1
        ):
            raise ValueError(
                "DecennialConditionProfile level-2 periods must preserve "
                "their major-period lineage"
            )

def decennial_condition_profile(period: DecennialPeriod) -> DecennialConditionProfile:
    """Build a DecennialConditionProfile from a DecennialPeriod.

    The profile preserves admitted structural Decennials truth only. Candidate
    Valens distributions/delineations are deliberately not attached here.
    """

    _require_admitted_decennial_periods(
        [period],
        caller="decennial_condition_profile",
    )
    return DecennialConditionProfile(
        planet=period.planet,
        level=period.level,
        level_name=period.level_name,
        is_major=period.is_major,
        lord_type=_decennial_lord_type(period.planet),
        sequence_kind=period.sequence_kind,
        major_planet=period.major_planet,
        parent_planet=period.parent_planet,
        parent_level=period.parent_level,
        ancestor_planets=period.ancestor_planets,
        effective_major_planet=period.effective_major_planet,
        is_day_chart=period.is_day_chart,
        sect_light=period.sect_light,
        major_index=period.major_index,
        sub_index=period.sub_index,
        sequence_position=period.sequence_position,
        deep_subdivision_method=period.deep_subdivision_method,
        years=period.years,
        months=period.months,
        days=period.days,
        month_basis_days=period.month_basis_days,
        time_basis=period.time_basis,
        calendar_projection_basis=period.calendar_projection_basis,
        sequence_origin_jd=period.sequence_origin_jd,
        start_distribution_day=period.start_distribution_day,
        end_distribution_day=period.end_distribution_day,
        distribution_years=period.distribution_years,
    )


@dataclass(slots=True)
class ZRConditionProfile:
    """
    RITE: The Zodiacal Releasing Condition Profile Vessel

    THEOREM: Governs the integrated doctrinal profile for one Zodiacal Releasing period.

    RITE OF PURPOSE:
        ZRConditionProfile is the public vessel that gathers the preserved context,
        classification truth, and inspectable condition flags of one releasing
        period into a single record. It exists so callers can inspect the local
        doctrinal state of a period without stitching fields together from the
        raw `ReleasingPeriod` vessel and the classification layer by hand.

    LAW OF OPERATION:
        Responsibilities:
            - Carry the sign, ruler, level, duration, and lot identity of one releasing period.
            - Carry the Loosing of the Bond and peak-period classifications admitted by this Pillar.
            - Serve as the per-period witness used by aggregate sequence and relation vessels.
        Non-responsibilities:
            - Computing releasing boundaries or sign transitions.
            - Deciding angularity classes independently of the originating period truth.
        Dependencies:
            - Built from `ReleasingPeriod` by `zr_condition_profile()`.
            - Depends on `ZRAngularityClass` semantics for peak-period classification.
        Structural invariants:
            - `level` is a Zodiacal Releasing level admitted by this Pillar.
            - `angularity_class` is either `None` or a `ZRAngularityClass` value.
        Behavioral invariants:
            - The vessel preserves the originating period truth without reinterpretation.

    Canon: Vettius Valens, Anthology IV; Chris Brennan, *Hellenistic Astrology* Ch.10

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.timelords.ZRConditionProfile",
      "risk": "medium",
      "api": {
        "frozen": [
          "sign",
          "ruler",
          "level",
          "level_name",
          "lot_name",
          "years",
          "days",
          "is_loosing_of_bond",
          "is_peak_period",
          "angularity_from_fortune",
          "angularity_class",
          "use_loosing_of_bond"
        ],
        "internal": []
      },
      "state": {"mutable": true, "owners": ["zr_condition_profile"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise_by_constructor_if_added"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    sign:                    str
    ruler:                   str
    level:                   int
    level_name:              str
    lot_name:                str
    years:                   float
    days:                    float
    is_loosing_of_bond:      bool
    is_peak_period:          bool
    angularity_from_fortune: int | None
    angularity_class:        str | None
    use_loosing_of_bond:     bool

def zr_condition_profile(period: ReleasingPeriod) -> ZRConditionProfile:
    """
    Build a ZRConditionProfile from a ReleasingPeriod.

    Assembles all Phase 1–6 truth about the period into a single profile.
    This function is deterministic and has no side effects.

    Candidate Valens distributions/delineations are deliberately not attached
    to the admitted structural Zodiacal Releasing profile.

    Parameters
    ----------
    period : ReleasingPeriod
        Any ReleasingPeriod produced by zodiacal_releasing() or current_releasing().

    Returns
    -------
    ZRConditionProfile
    """
    return ZRConditionProfile(
        sign                    = period.sign,
        ruler                   = period.ruler,
        level                   = period.level,
        level_name              = period.level_name,
        lot_name                = period.lot_name,
        years                   = period.years,
        days                    = period.days,
        is_loosing_of_bond      = period.is_loosing_of_bond,
        is_peak_period          = period.is_peak_period,
        angularity_from_fortune = period.angularity_from_fortune,
        angularity_class        = period.angularity_class,
        use_loosing_of_bond     = period.use_loosing_of_bond,
    )


# ---------------------------------------------------------------------------
# Phase 8 — Aggregate Intelligence
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class FirdarSequenceProfile:
    """
    RITE: The Firdaria Sequence Profile Vessel

    THEOREM: Governs the aggregate structural profile of a complete Firdaria major-period sequence.

    RITE OF PURPOSE:
        FirdarSequenceProfile is the public aggregate vessel for chart-wide
        Firdaria sequence truth. It exists so callers can inspect the major-period
        composition of an entire cycle, including lord-type counts and total years,
        without recomputing those summaries from the flat period list each time.

    LAW OF OPERATION:
        Responsibilities:
            - Carry the ordered major-period condition profiles of one Firdaria cycle.
            - Carry aggregate counts by lord type and total major years.
            - Preserve the shared sequence-kind classification of the underlying series.
        Non-responsibilities:
            - Generating the underlying Firdaria periods.
            - Interpreting aggregate counts beyond the exposed structural summary.
        Dependencies:
            - Built from `FirdarConditionProfile` witnesses by `firdar_sequence_profile()`.
            - Depends on `FirdarSequenceKind` doctrine admitted by this Pillar.
        Structural invariants:
            - `major_count` equals `len(profiles)`.
            - Lord-type counts match the supplied profile tuple and sum to `major_count`.
        Failure behavior:
            - Raises `ValueError` when aggregate counts do not match the supplied profiles.

    Canon: Abu Ma'shar, *The Abbreviation of the Introduction to Astrology*; Guido Bonatti, *Liber Astronomiae*

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.timelords.FirdarSequenceProfile",
      "risk": "medium",
      "api": {
        "frozen": [
          "profiles",
          "major_count",
          "luminary_major_count",
          "planet_major_count",
          "node_major_count",
          "total_major_years",
          "sequence_kind"
        ],
        "internal": ["profile_count", "has_node_majors"]
      },
      "state": {"mutable": true, "owners": ["firdar_sequence_profile"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    profiles:             tuple["FirdarConditionProfile", ...]
    major_count:          int
    luminary_major_count: int
    planet_major_count:   int
    node_major_count:     int
    total_major_years:    float
    sequence_kind:        str | None

    def __post_init__(self) -> None:
        if self.major_count != len(self.profiles):
            raise ValueError("FirdarSequenceProfile.major_count must equal len(profiles)")
        if self.luminary_major_count != sum(
            1 for p in self.profiles if p.lord_type == "luminary"
        ):
            raise ValueError("FirdarSequenceProfile.luminary_major_count does not match profiles")
        if self.planet_major_count != sum(
            1 for p in self.profiles if p.lord_type == "planet"
        ):
            raise ValueError("FirdarSequenceProfile.planet_major_count does not match profiles")
        if self.node_major_count != sum(
            1 for p in self.profiles if p.lord_type == "node"
        ):
            raise ValueError("FirdarSequenceProfile.node_major_count does not match profiles")
        if self.luminary_major_count + self.planet_major_count + self.node_major_count \
                != self.major_count:
            raise ValueError(
                "FirdarSequenceProfile lord-type counts must sum to major_count"
            )

    @property
    def profile_count(self) -> int:
        """Total number of major-period profiles in this aggregate."""
        return len(self.profiles)

    @property
    def has_node_majors(self) -> bool:
        """True when the sequence contains at least one node major period."""
        return self.node_major_count > 0


def firdar_sequence_profile(periods: list[FirdarPeriod]) -> FirdarSequenceProfile:
    """
    Build a FirdarSequenceProfile from a flat Firdaria period list.

    Aggregates over the major (level-1) periods only. Sub-periods are not
    included in the profile tuple but contribute to the count totals
    indirectly through the major periods they belong to.

    Parameters
    ----------
    periods : list[FirdarPeriod]
        The output of firdaria() — major and sub-periods mixed.

    Returns
    -------
    FirdarSequenceProfile
    """
    major_profiles = tuple(
        firdar_condition_profile(p) for p in periods if p.level == 1
    )
    luminary_count = sum(1 for p in major_profiles if p.lord_type == "luminary")
    planet_count   = sum(1 for p in major_profiles if p.lord_type == "planet")
    node_count     = sum(1 for p in major_profiles if p.lord_type == "node")
    total_years    = sum(p.years for p in major_profiles)
    kind: str | None = major_profiles[0].sequence_kind if major_profiles else None

    return FirdarSequenceProfile(
        profiles             = major_profiles,
        major_count          = len(major_profiles),
        luminary_major_count = luminary_count,
        planet_major_count   = planet_count,
        node_major_count     = node_count,
        total_major_years    = total_years,
        sequence_kind        = kind,
    )


@dataclass(slots=True)
class DecennialSequenceProfile:
    """Aggregate structural profile of a complete Decennials major-period sequence."""

    profiles: tuple["DecennialConditionProfile", ...]
    major_count: int
    luminary_major_count: int
    planetary_major_count: int
    total_major_years: float
    total_major_months: float
    sequence_kind: str | None
    sect_light: str | None
    time_basis: str
    calendar_projection_basis: str
    sequence_origin_jd: float
    level_count_map: dict[int, int] = field(default_factory=dict)
    deepest_level: int = 1
    deep_subdivision_method: None = None

    def __post_init__(self) -> None:
        if self.deepest_level > _DECENNIAL_MAX_LEVEL:
            raise ValueError(
                "DecennialSequenceProfile Decennial levels 3–4 are not admitted"
            )
        if self.deep_subdivision_method is not None or any(
            profile.deep_subdivision_method is not None for profile in self.profiles
        ):
            raise ValueError(
                "DecennialSequenceProfile deep_subdivision_method is not admitted"
            )
        if (
            self.time_basis
            != DecennialTimeBasis.VALENS_LIVED_DAYS_TO_360_DAY_DISTRIBUTION
        ):
            raise ValueError("DecennialSequenceProfile time_basis is not admitted")
        if (
            self.calendar_projection_basis
            != DecennialTimeBasis.ELAPSED_JULIAN_DAYS_FROM_NATAL_JD
        ):
            raise ValueError(
                "DecennialSequenceProfile calendar_projection_basis is not admitted"
            )
        if not math.isfinite(self.sequence_origin_jd):
            raise ValueError(
                "DecennialSequenceProfile sequence_origin_jd must be finite"
            )
        if any(
            profile.time_basis != self.time_basis
            or profile.calendar_projection_basis != self.calendar_projection_basis
            or profile.sequence_origin_jd != self.sequence_origin_jd
            for profile in self.profiles
        ):
            raise ValueError(
                "DecennialSequenceProfile profiles must share the aggregate "
                "time-basis receipt"
            )
        major_profiles = tuple(profile for profile in self.profiles if profile.level == 1)
        if self.major_count != len(major_profiles):
            raise ValueError("DecennialSequenceProfile.major_count must equal the number of level-1 profiles")
        if self.luminary_major_count != sum(1 for p in major_profiles if p.lord_type == "luminary"):
            raise ValueError("DecennialSequenceProfile.luminary_major_count does not match major profiles")
        if self.planetary_major_count != sum(1 for p in major_profiles if p.lord_type == "planet"):
            raise ValueError("DecennialSequenceProfile.planetary_major_count does not match major profiles")
        if self.luminary_major_count + self.planetary_major_count != self.major_count:
            raise ValueError("DecennialSequenceProfile lord-type counts must sum to major_count")
        if self.profile_count != sum(self.level_count_map.values()):
            raise ValueError("DecennialSequenceProfile.level_count_map must sum to profile_count")
        if self.level_count_map.get(1, 0) != self.major_count:
            raise ValueError("DecennialSequenceProfile.level_count_map[1] must equal major_count")
        if self.deepest_level != max(self.level_count_map, default=1):
            raise ValueError("DecennialSequenceProfile.deepest_level must match the deepest level present in level_count_map")

    @property
    def profile_count(self) -> int:
        return len(self.profiles)


def decennial_sequence_profile(periods: list[DecennialPeriod]) -> DecennialSequenceProfile:
    """Build a DecennialSequenceProfile from a flat Decennials period list."""

    if not periods:
        raise ValueError("decennial_sequence_profile: periods must not be empty")
    _require_admitted_decennial_periods(
        periods,
        caller="decennial_sequence_profile",
    )
    profiles = tuple(decennial_condition_profile(period) for period in periods)
    major_profiles = tuple(profile for profile in profiles if profile.level == 1)
    luminary_count = sum(1 for profile in major_profiles if profile.lord_type == "luminary")
    planetary_count = sum(1 for profile in major_profiles if profile.lord_type == "planet")
    total_years = sum(profile.years for profile in major_profiles)
    total_months = sum(profile.months for profile in major_profiles)
    sequence_kind = major_profiles[0].sequence_kind if major_profiles else None
    sect_light = major_profiles[0].sect_light if major_profiles else None
    level_count_map: dict[int, int] = {}
    deepest_level = 1
    for profile in profiles:
        level_count_map[profile.level] = level_count_map.get(profile.level, 0) + 1
        deepest_level = max(deepest_level, profile.level)

    return DecennialSequenceProfile(
        profiles=profiles,
        major_count=len(major_profiles),
        luminary_major_count=luminary_count,
        planetary_major_count=planetary_count,
        total_major_years=total_years,
        total_major_months=total_months,
        sequence_kind=sequence_kind,
        sect_light=sect_light,
        time_basis=periods[0].time_basis,
        calendar_projection_basis=periods[0].calendar_projection_basis,
        sequence_origin_jd=periods[0].sequence_origin_jd,
        level_count_map=level_count_map,
        deepest_level=deepest_level,
        deep_subdivision_method=None,
    )


@dataclass(slots=True)
class ZRSequenceProfile:
    """
    RITE: The Zodiacal Releasing Sequence Profile Vessel

    THEOREM: Governs the aggregate structural profile of a Zodiacal Releasing sequence at one level.

    RITE OF PURPOSE:
        ZRSequenceProfile is the chart-wide aggregate vessel for the doctrinal
        composition of releasing periods at a chosen level. It exists so callers
        can inspect peak-period frequency, Loosing of the Bond incidence, and
        angular-class distribution without re-scanning the flat releasing list.

    LAW OF OPERATION:
        Responsibilities:
            - Carry the ordered condition profiles for one releasing level.
            - Carry aggregate counts for peak periods, bond releases, and angular classes.
            - Carry the total nominal years represented by the aggregated profiles.
        Non-responsibilities:
            - Generating the underlying releasing periods.
            - Reclassifying periods beyond the supplied profile truth.
        Dependencies:
            - Built from `ZRConditionProfile` witnesses by `zr_sequence_profile()`.
            - Depends on `ZRAngularityClass` semantics admitted by this Pillar.
        Structural invariants:
            - `period_count` equals `len(profiles)`.
            - Angular-class counts match the supplied profiles and sum to the
              number of profiles classified relative to Fortune.
            - `angular_count` equals `peak_period_count`.
        Failure behavior:
            - Raises `ValueError` when aggregate counts do not match the supplied profiles.

    Canon: Vettius Valens, Anthology IV; Chris Brennan, *Hellenistic Astrology* Ch.10

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.timelords.ZRSequenceProfile",
      "risk": "medium",
      "api": {
        "frozen": [
          "profiles",
          "period_count",
          "peak_period_count",
          "loosing_of_bond_count",
          "angular_count",
          "succedent_count",
          "cadent_count",
          "total_years"
        ],
        "internal": ["profile_count", "non_peak_count"]
      },
      "state": {"mutable": true, "owners": ["zr_sequence_profile"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    profiles:              tuple["ZRConditionProfile", ...]
    period_count:          int
    peak_period_count:     int
    loosing_of_bond_count: int
    angular_count:         int
    succedent_count:       int
    cadent_count:          int
    total_years:           float

    def __post_init__(self) -> None:
        if self.period_count != len(self.profiles):
            raise ValueError("ZRSequenceProfile.period_count must equal len(profiles)")
        if self.peak_period_count != sum(
            1 for p in self.profiles if p.is_peak_period
        ):
            raise ValueError("ZRSequenceProfile.peak_period_count does not match profiles")
        if self.loosing_of_bond_count != sum(
            1 for p in self.profiles if p.is_loosing_of_bond
        ):
            raise ValueError("ZRSequenceProfile.loosing_of_bond_count does not match profiles")
        if self.angular_count != sum(
            1 for p in self.profiles if p.angularity_class == ZRAngularityClass.ANGULAR
        ):
            raise ValueError("ZRSequenceProfile.angular_count does not match profiles")
        if self.succedent_count != sum(
            1 for p in self.profiles if p.angularity_class == ZRAngularityClass.SUCCEDENT
        ):
            raise ValueError("ZRSequenceProfile.succedent_count does not match profiles")
        if self.cadent_count != sum(
            1 for p in self.profiles if p.angularity_class == ZRAngularityClass.CADENT
        ):
            raise ValueError("ZRSequenceProfile.cadent_count does not match profiles")
        classified_count = sum(
            1 for p in self.profiles if p.angularity_class is not None
        )
        if self.angular_count + self.succedent_count + self.cadent_count \
                != classified_count:
            raise ValueError(
                "ZRSequenceProfile angular + succedent + cadent must equal classified profiles"
            )
        if self.angular_count != self.peak_period_count:
            raise ValueError(
                "ZRSequenceProfile angular_count must equal peak_period_count"
            )

    @property
    def profile_count(self) -> int:
        """Total number of profiles in this aggregate."""
        return len(self.profiles)

    @property
    def non_peak_count(self) -> int:
        """Number of periods that are not peak periods."""
        return self.period_count - self.peak_period_count

def zr_sequence_profile(
    periods: list[ReleasingPeriod],
    level: int = 1,
) -> ZRSequenceProfile:
    """
    Build a ZRSequenceProfile from a flat Zodiacal Releasing period list.

    Aggregates over periods at the given level (default Level 1). Periods
    at other levels are ignored.

    Parameters
    ----------
    periods : list[ReleasingPeriod]
        The output of zodiacal_releasing() — all levels mixed.
    level : int
        The level to aggregate over (1–4). Default 1.

    Returns
    -------
    ZRSequenceProfile
    """
    if not 1 <= level <= _ZR_MAX_LEVEL:
        raise ValueError(f"zr_sequence_profile: level must be 1–{_ZR_MAX_LEVEL}")
    if not periods:
        raise ValueError("zr_sequence_profile: periods must not be empty")
    available_levels = {period.level for period in periods}
    if level not in available_levels:
        raise ValueError(
            f"zr_sequence_profile: level {level} is not present in periods; "
            f"available levels are {sorted(available_levels)}"
        )
    level_profiles = tuple(
        zr_condition_profile(p) for p in periods if p.level == level
    )
    peak_count  = sum(1 for p in level_profiles if p.is_peak_period)
    lb_count    = sum(1 for p in level_profiles if p.is_loosing_of_bond)
    ang_count   = sum(1 for p in level_profiles if p.angularity_class == ZRAngularityClass.ANGULAR)
    succ_count  = sum(1 for p in level_profiles if p.angularity_class == ZRAngularityClass.SUCCEDENT)
    cad_count   = sum(1 for p in level_profiles if p.angularity_class == ZRAngularityClass.CADENT)
    total_years = sum(p.years for p in level_profiles)

    return ZRSequenceProfile(
        profiles              = level_profiles,
        period_count          = len(level_profiles),
        peak_period_count     = peak_count,
        loosing_of_bond_count = lb_count,
        angular_count         = ang_count,
        succedent_count       = succ_count,
        cadent_count          = cad_count,
        total_years           = total_years,
    )


# ---------------------------------------------------------------------------
# Phase 9 — Network Intelligence
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class FirdarActivePair:
    """
    RITE: The Active Firdaria Pair Vessel

    THEOREM: Governs the simultaneously active major and sub-period Firdaria profiles at one Julian Day.

    RITE OF PURPOSE:
        FirdarActivePair is the explicit relation vessel for the two-lord state
        that Firdaria can produce at a given instant. It exists so callers can
        inspect the active major and optional sub-period together as one public
        object rather than running separate searches and reconstructing the pair.

    LAW OF OPERATION:
        Responsibilities:
            - Carry the active major-period profile.
            - Carry the active sub-period profile when subdivision exists.
            - Expose simple relation predicates such as same-lord and node involvement.
        Non-responsibilities:
            - Locating the active periods in a period list.
            - Interpreting the pair beyond the exposed relation predicates.
        Dependencies:
            - Built from `FirdarConditionProfile` witnesses by `firdar_active_pair()`.
        Structural invariants:
            - `major_profile` is always a major profile.
            - `sub_profile` is `None` or a sub-period profile.
        Failure behavior:
            - Raises `ValueError` when supplied profiles violate the major/sub hierarchy.

    Canon: Abu Ma'shar, *The Abbreviation of the Introduction to Astrology*; Guido Bonatti, *Liber Astronomiae*

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.timelords.FirdarActivePair",
      "risk": "medium",
      "api": {
        "frozen": ["major_profile", "sub_profile"],
        "internal": ["has_sub", "is_same_lord", "is_same_lord_type", "involves_node"]
      },
      "state": {"mutable": true, "owners": ["firdar_active_pair"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    major_profile: FirdarConditionProfile
    sub_profile:   FirdarConditionProfile | None

    def __post_init__(self) -> None:
        if not self.major_profile.is_major:
            raise ValueError(
                "FirdarActivePair.major_profile must be a major (level-1) profile"
            )
        if self.sub_profile is not None and self.sub_profile.is_major:
            raise ValueError(
                "FirdarActivePair.sub_profile must be a sub-period (level-2) profile"
            )

    @property
    def has_sub(self) -> bool:
        """True when a sub-period is active alongside the major."""
        return self.sub_profile is not None

    @property
    def is_same_lord(self) -> bool:
        """True when the major and sub lords are the same planet."""
        return (
            self.sub_profile is not None
            and self.major_profile.planet == self.sub_profile.planet
        )

    @property
    def is_same_lord_type(self) -> bool:
        """True when the major and sub lords share the same lord-type classification."""
        return (
            self.sub_profile is not None
            and self.major_profile.lord_type == self.sub_profile.lord_type
        )

    @property
    def involves_node(self) -> bool:
        """True when either the major or sub lord is a node."""
        if self.major_profile.lord_type == "node":
            return True
        return self.sub_profile is not None and self.sub_profile.lord_type == "node"


def firdar_active_pair(
    periods: list[FirdarPeriod],
    jd: float,
) -> FirdarActivePair | None:
    """
    Return the FirdarActivePair active at *jd*, or None if no major is active.

    Scans the flat firdaria() period list for the active major and (if present)
    the active sub-period at the given Julian Day, then wraps them in a
    FirdarActivePair network node.

    Parameters
    ----------
    periods : list[FirdarPeriod]
        The output of firdaria().
    jd : float
        The Julian Day to query.

    Returns
    -------
    FirdarActivePair | None
        None when *jd* falls outside the entire Firdaria sequence.
    """
    if not math.isfinite(jd):
        raise ValueError(f"firdar_active_pair: jd must be finite, got {jd!r}")
    active_major = next(
        (p for p in periods if p.level == 1 and p.is_active_at(jd)), None
    )
    if active_major is None:
        return None
    active_sub = next(
        (p for p in periods if p.level == 2 and p.is_active_at(jd)), None
    )
    return FirdarActivePair(
        major_profile = firdar_condition_profile(active_major),
        sub_profile   = firdar_condition_profile(active_sub) if active_sub else None,
    )


@dataclass(slots=True)
class DecennialActivePair:
    """The simultaneously active Decennials major and sub-period profiles at one Julian Day."""

    major_profile: DecennialConditionProfile
    sub_profile: DecennialConditionProfile | None

    def __post_init__(self) -> None:
        if not self.major_profile.is_major:
            raise ValueError(
                "DecennialActivePair.major_profile must be a major (level-1) profile"
            )
        if self.sub_profile is not None and self.sub_profile.is_major:
            raise ValueError(
                "DecennialActivePair.sub_profile must be a sub-period (level-2) profile"
            )

    @property
    def has_sub(self) -> bool:
        return self.sub_profile is not None

    @property
    def is_same_lord(self) -> bool:
        return (
            self.sub_profile is not None
            and self.major_profile.planet == self.sub_profile.planet
        )

    @property
    def is_same_lord_type(self) -> bool:
        return (
            self.sub_profile is not None
            and self.major_profile.lord_type == self.sub_profile.lord_type
        )

    @property
    def shares_sect_light(self) -> bool:
        return (
            self.sub_profile is not None
            and self.major_profile.sect_light == self.sub_profile.sect_light
        )


@dataclass(slots=True)
class DecennialActivePath:
    """The full active Decennials lineage at one Julian Day."""

    profiles: tuple[DecennialConditionProfile, ...]

    def __post_init__(self) -> None:
        if not self.profiles:
            raise ValueError("DecennialActivePath.profiles must not be empty")
        if self.profiles[0].level != 1:
            raise ValueError("DecennialActivePath must begin with a level-1 profile")
        if any(
            profile.level not in (1, 2)
            or profile.deep_subdivision_method is not None
            for profile in self.profiles
        ):
            raise ValueError(
                "DecennialActivePath supports admitted L1/L2 profiles only"
            )
        for index in range(len(self.profiles) - 1):
            if self.profiles[index + 1].level != self.profiles[index].level + 1:
                raise ValueError("DecennialActivePath profiles must advance one level at a time")

    @property
    def deepest_profile(self) -> DecennialConditionProfile:
        return self.profiles[-1]

    @property
    def deepest_level(self) -> int:
        return self.deepest_profile.level

    @property
    def major_profile(self) -> DecennialConditionProfile:
        return self.profiles[0]

    @property
    def has_deep_subdivision(self) -> bool:
        return False


def decennial_active_pair(
    periods: list[DecennialPeriod],
    jd: float,
) -> DecennialActivePair | None:
    """
    Return the DecennialActivePair active at *jd*, or None if no major is active.
    """
    if not math.isfinite(jd):
        raise ValueError(f"decennial_active_pair: jd must be finite, got {jd!r}")
    _require_admitted_decennial_periods(
        periods,
        caller="decennial_active_pair",
    )
    active_major = next(
        (period for period in periods if period.level == 1 and period.is_active_at(jd)),
        None,
    )
    if active_major is None:
        return None
    active_sub = next(
        (period for period in periods if period.level == 2 and period.is_active_at(jd)),
        None,
    )
    return DecennialActivePair(
        major_profile=decennial_condition_profile(active_major),
        sub_profile=decennial_condition_profile(active_sub) if active_sub else None,
    )


def decennial_active_path(
    periods: list[DecennialPeriod],
    jd: float,
) -> DecennialActivePath | None:
    """Return the full active Decennials lineage at *jd*, or None if no major is active."""
    if not math.isfinite(jd):
        raise ValueError(f"decennial_active_path: jd must be finite, got {jd!r}")
    _require_admitted_decennial_periods(
        periods,
        caller="decennial_active_path",
    )
    active_profiles = tuple(
        decennial_condition_profile(period)
        for period in sorted(
            (period for period in periods if period.is_active_at(jd)),
            key=lambda period: period.level,
        )
    )
    if not active_profiles:
        return None
    return DecennialActivePath(profiles=active_profiles)


@dataclass(slots=True)
class ZRLevelPair:
    """
    RITE: The Zodiacal Releasing Level Pair Vessel

    THEOREM: Governs the structural relation between two simultaneously active Zodiacal Releasing levels.

    RITE OF PURPOSE:
        ZRLevelPair is the explicit relation vessel for the multi-level state of
        Zodiacal Releasing. It exists so callers can inspect outer and inner
        releasing levels together, including their sign-distance relation, without
        reconstructing that geometry from two separate condition profiles.

    LAW OF OPERATION:
        Responsibilities:
            - Carry the outer and inner condition profiles active at the same instant.
            - Carry the zodiacal house distance from the upper sign to the lower sign.
            - Expose simple relation predicates such as adjacency and shared peak status.
        Non-responsibilities:
            - Locating active periods in a releasing list.
            - Recomputing house distance from raw longitude rather than supplied sign truth.
        Dependencies:
            - Built from `ZRConditionProfile` witnesses by `zr_level_pair()`.
            - Depends on the sign-ordering and house-counting doctrine admitted by this Pillar.
        Structural invariants:
            - `upper_profile.level` is lower than `lower_profile.level`.
            - `house_distance` is an integer in the inclusive range 1..12.
            - `signs_are_identical` matches the two supplied signs.
        Failure behavior:
            - Raises `ValueError` when the hierarchy, distance, or identical-sign flag is inconsistent.

    Canon: Vettius Valens, Anthology IV; Chris Brennan, *Hellenistic Astrology* Ch.10

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.timelords.ZRLevelPair",
      "risk": "medium",
      "api": {
        "frozen": ["upper_profile", "lower_profile", "house_distance", "signs_are_identical"],
        "internal": ["is_adjacent_levels", "is_angular_distance", "is_peak_pair"]
      },
      "state": {"mutable": true, "owners": ["zr_level_pair"]},
      "effects": {"signals_emitted": [], "io": []},
      "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
      "failures": {"policy": "raise"},
      "succession": {"stance": "terminal"},
      "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    upper_profile:       ZRConditionProfile  # outer period — lower level number (e.g. Level 1)
    lower_profile:       ZRConditionProfile  # inner period — higher level number (e.g. Level 2)
    house_distance:      int
    signs_are_identical: bool

    def __post_init__(self) -> None:
        if self.upper_profile.level >= self.lower_profile.level:
            raise ValueError(
                "ZRLevelPair.upper_profile must be at a lower level number "
                "than lower_profile (e.g. Level 1 upper, Level 2 lower)"
            )
        if not (1 <= self.house_distance <= 12):
            raise ValueError(
                f"ZRLevelPair.house_distance must be 1–12, got {self.house_distance}"
            )
        expected_identical = (self.upper_profile.sign == self.lower_profile.sign)
        if self.signs_are_identical != expected_identical:
            raise ValueError(
                "ZRLevelPair.signs_are_identical does not match the sign fields"
            )

    @property
    def is_adjacent_levels(self) -> bool:
        """True when the two profiles are at directly adjacent levels (e.g. 1 and 2)."""
        return self.lower_profile.level == self.upper_profile.level + 1

    @property
    def is_angular_distance(self) -> bool:
        """True when house_distance is one of the four angular houses (1, 4, 7, 10)."""
        return self.house_distance in _ANGULAR_HOUSES

    @property
    def is_peak_pair(self) -> bool:
        """True when both levels are peak periods (both angular from Fortune)."""
        return self.upper_profile.is_peak_period and self.lower_profile.is_peak_period


def zr_level_pair(
    upper: ReleasingPeriod,
    lower: ReleasingPeriod,
) -> ZRLevelPair:
    """
    Build a ZRLevelPair from two ReleasingPeriods at different levels.

    The *upper* period must be at a lower level number (outer level) and
    the *lower* period at a higher level number (inner level). For example,
    upper=Level 1, lower=Level 2.

    Parameters
    ----------
    upper : ReleasingPeriod
        The outer (lower level number, e.g. Level 1) releasing period.
    lower : ReleasingPeriod
        The inner (higher level number, e.g. Level 2) releasing period.

    Returns
    -------
    ZRLevelPair
    """
    upper_idx = SIGNS.index(upper.sign)
    lower_idx = SIGNS.index(lower.sign)
    distance  = (lower_idx - upper_idx) % 12 + 1  # 1 = same sign, 12 = prior sign

    return ZRLevelPair(
        upper_profile       = zr_condition_profile(upper),
        lower_profile       = zr_condition_profile(lower),
        house_distance      = distance,
        signs_are_identical = upper.sign == lower.sign,
    )


# ---------------------------------------------------------------------------
# Phase 10 — Full-Subsystem Hardening
# ---------------------------------------------------------------------------

def validate_firdaria_output(periods: list[FirdarPeriod]) -> None:
    """
    Verify that a firdaria() output satisfies all cross-layer invariants.

    Checks the following invariants:
    - Level-1 periods are in chronological order with no JD overlaps.
    - Every level-2 period's major_planet references a known level-1 planet.
    - Level-2 periods within each major are in chronological order with no overlaps.

    Raises
    ------
    ValueError
        On the first invariant violation found. Passes silently when all
        invariants hold.
    """
    level1 = [p for p in periods if p.level == 1]
    level2 = [p for p in periods if p.level == 2]

    # Cross-layer invariant 1: level-1 periods in chronological order, no overlap
    for i in range(len(level1) - 1):
        if level1[i].end_jd > level1[i + 1].start_jd + 1e-9:
            raise ValueError(
                f"validate_firdaria_output: level-1 periods overlap or are out of order "
                f"('{level1[i].planet}' end_jd={level1[i].end_jd:.6f} > "
                f"'{level1[i + 1].planet}' start_jd={level1[i + 1].start_jd:.6f})"
            )

    # Cross-layer invariant 2: every sub-period's major_planet is a known level-1 planet
    level1_planets = {p.planet for p in level1}
    for sub in level2:
        if sub.major_planet not in level1_planets:
            raise ValueError(
                f"validate_firdaria_output: sub-period '{sub.planet}' references "
                f"unknown major_planet '{sub.major_planet}'"
            )

    # Cross-layer invariant 3: level-2 periods within each major are ordered, no overlap
    for major in level1:
        subs = sorted(
            (s for s in level2 if s.major_planet == major.planet),
            key=lambda s: s.start_jd,
        )
        for i in range(len(subs) - 1):
            if subs[i].end_jd > subs[i + 1].start_jd + 1e-9:
                raise ValueError(
                    f"validate_firdaria_output: sub-periods of '{major.planet}' overlap "
                    f"or are out of order ('{subs[i].planet}' end_jd={subs[i].end_jd:.6f} > "
                    f"'{subs[i + 1].planet}' start_jd={subs[i + 1].start_jd:.6f})"
                )


def validate_releasing_output(periods: list[ReleasingPeriod]) -> None:
    """
    Verify that a zodiacal_releasing() output satisfies all cross-layer invariants.

    Checks the following invariants:
    - Periods at each level are in chronological order with no JD overlaps.
    - Level 2+ periods are temporally contained within a level above them.

    Raises
    ------
    ValueError
        On the first invariant violation found. Passes silently when all
        invariants hold.
    """
    fortune_truths = [
        period.fortune_angularity_truth
        for period in periods
        if period.fortune_angularity_truth is not None
    ]
    if fortune_truths:
        if len(fortune_truths) != len(periods):
            raise ValueError(
                "validate_releasing_output: all periods must preserve "
                "Fortune angularity truth when any period does"
            )
        first_dependency = (
            fortune_truths[0].status,
            fortune_truths[0].fortune_sign,
            fortune_truths[0].reason,
        )
        if any(
            (
                truth.status,
                truth.fortune_sign,
                truth.reason,
            )
            != first_dependency
            for truth in fortune_truths[1:]
        ):
            raise ValueError(
                "validate_releasing_output: periods must preserve one "
                "Fortune dependency context"
            )

    for period in periods:
        truth = period.fortune_angularity_truth
        if truth is None:
            continue
        if truth.period_sign != period.sign:
            raise ValueError(
                "validate_releasing_output: Fortune angularity truth must "
                "match its releasing sign"
            )
        if truth.status is TimelordEvaluationStatus.EVALUATED:
            if (
                truth.angularity_from_fortune
                != period.angularity_from_fortune
                or truth.angularity_class != period.angularity_class
                or truth.is_peak_period is not period.is_peak_period
            ):
                raise ValueError(
                    "validate_releasing_output: compatibility Fortune fields "
                    "must match evaluated truth"
                )
        elif (
            period.angularity_from_fortune is not None
            or period.angularity_class is not None
            or period.is_peak_period
        ):
            raise ValueError(
                "validate_releasing_output: not_evaluable Fortune truth "
                "cannot assemble compatibility fields"
            )

    # Cross-layer invariant 1: chronological ordering and no overlap at each level
    for level in range(1, 5):
        this_level = [p for p in periods if p.level == level]
        for i in range(len(this_level) - 1):
            if this_level[i].end_jd > this_level[i + 1].start_jd + 1e-9:
                raise ValueError(
                    f"validate_releasing_output: Level {level} periods overlap or are "
                    f"out of order ('{this_level[i].sign}' end_jd={this_level[i].end_jd:.6f} > "
                    f"'{this_level[i + 1].sign}' start_jd={this_level[i + 1].start_jd:.6f})"
                )

    # Cross-layer invariant 2: each level N+1 period is contained within a level N period
    for child_level in range(2, 5):
        children  = [p for p in periods if p.level == child_level]
        parents   = [p for p in periods if p.level == child_level - 1]
        for child in children:
            contained = any(
                par.start_jd <= child.start_jd + 1e-9
                and par.end_jd >= child.end_jd - 1e-9
                for par in parents
            )
            if not contained:
                raise ValueError(
                    f"validate_releasing_output: Level-{child_level} period "
                    f"'{child.sign}' (start={child.start_jd:.6f}) is not temporally "
                    f"contained within any Level-{child_level - 1} period"
                )


# ---------------------------------------------------------------------------
# Zodiacal Releasing helpers
# ---------------------------------------------------------------------------

def _sign_index(sign: str) -> int:
    """Return the 0-based index of a sign in SIGNS (Aries=0 … Pisces=11)."""
    return SIGNS.index(sign)


def _sign_at_index(idx: int) -> str:
    """Return the sign name at a 0-based zodiacal index (wraps at 12)."""
    return SIGNS[idx % 12]


def _opposite_sign(sign: str) -> str:
    return _sign_at_index(_sign_index(sign) + 6)


def _zr_duration_days(sign: str, level: int, level_days: dict[int, float]) -> float:
    return float(MINOR_YEARS[sign]) * level_days[level]


def _fortune_angularity(sign: str, fortune_sign: str | None) -> int | None:
    if fortune_sign is None:
        return None
    offset = (_sign_index(sign) - _sign_index(fortune_sign)) % 12
    return offset + 1


def _resolve_releasing_start_sign(
    lot_longitude: float,
    lot_name: str,
    fortune_longitude: float | None,
) -> str:
    sign_name, _, _ = sign_of(lot_longitude)
    if lot_name == "Spirit" and fortune_longitude is not None:
        fortune_sign, _, _ = sign_of(fortune_longitude)
        if fortune_sign == sign_name:
            return _sign_at_index(_sign_index(sign_name) + 1)
    return sign_name


def _generate_releasing(
    start_sign: str,
    start_jd: float,
    level: int,
    max_level: int,
    max_jd: float,
    lot_name: str,
    fortune_sign: str | None,
    use_loosing_of_bond: bool,
    level_days: dict[int, float],
    year_days: float,
) -> list[ReleasingPeriod]:
    """
    Recursively generate Zodiacal Releasing periods.

    Periods advance sign by sign from *start_sign*, each lasting
    MINOR_YEARS[sign] years.  Sub-periods (level+1) are generated inside
    each period, starting from *that period's own sign*.

    Parameters
    ----------
    start_sign : str
        The sign from which this level's releasing begins.
    start_jd : float
        Julian Day at which this releasing starts.
    level : int
        Current depth (1 = outermost Level 1).
    max_level : int
        Maximum depth to generate (typically 4).
    max_jd : float
        Hard upper boundary — no period beyond this JD is generated.

    Returns
    -------
    list[ReleasingPeriod]
        All periods at this level (and deeper levels interleaved) within bounds.
    """
    results: list[ReleasingPeriod] = []
    current_sign = start_sign
    cursor_jd = start_jd
    cycle_start_sign = start_sign
    next_is_loosing_of_bond = False
    _unit_days = level_days[level]

    while cursor_jd < max_jd:
        period_jd_len = float(MINOR_YEARS[current_sign]) * _unit_days
        period_end = cursor_jd + period_jd_len

        # Clamp to the hard boundary
        effective_end = min(period_end, max_jd)

        # Compute the actual duration for this (possibly clamped) period
        effective_years = (effective_end - cursor_jd) / year_days
        fortune_angularity_truth = zr_fortune_angularity_truth(
            current_sign,
            fortune_sign,
        )

        rp = ReleasingPeriod(
            level=level,
            sign=current_sign,
            ruler=DOMICILE_RULERS[current_sign],
            start_jd=cursor_jd,
            end_jd=effective_end,
            years=effective_years,
            lot_name=lot_name,
            is_loosing_of_bond=next_is_loosing_of_bond,
            is_peak_period=fortune_angularity_truth.is_peak_period is True,
            angularity_from_fortune=(
                fortune_angularity_truth.angularity_from_fortune
            ),
            use_loosing_of_bond=use_loosing_of_bond,
            angularity_class=fortune_angularity_truth.angularity_class,
            fortune_angularity_truth=fortune_angularity_truth,
        )
        results.append(rp)
        next_is_loosing_of_bond = False

        # Recurse into deeper levels if requested
        if level < max_level and cursor_jd < max_jd:
            sub = _generate_releasing(
                start_sign=current_sign,   # Level 2 starts at the same sign
                start_jd=cursor_jd,
                level=level + 1,
                max_level=max_level,
                max_jd=effective_end,
                lot_name=lot_name,
                fortune_sign=fortune_sign,
                use_loosing_of_bond=use_loosing_of_bond,
                level_days=level_days,
                year_days=year_days,
            )
            results.extend(sub)

        cursor_jd = period_end
        next_sign = _sign_at_index(_sign_index(current_sign) + 1)
        if (
            use_loosing_of_bond
            and next_sign == cycle_start_sign
            and cycle_start_sign in _ZR_LONG_SIGNS
        ):
            current_sign = _opposite_sign(cycle_start_sign)
            cycle_start_sign = current_sign
            next_is_loosing_of_bond = True
        else:
            current_sign = next_sign

    return results


# ---------------------------------------------------------------------------
# Zodiacal Releasing public API
# ---------------------------------------------------------------------------

def zodiacal_releasing(
    lot_longitude: float,
    natal_jd: float,
    levels: int = 4,
    *,
    lot_name: str = "Spirit",
    fortune_longitude: float | None = None,
    use_loosing_of_bond: bool = True,
    policy: "TimelordComputationPolicy | None" = None,
) -> list[ReleasingPeriod]:
    """
    Generate Zodiacal Releasing periods from a Lot (Fortune, Spirit, etc.).

    Level 1 periods advance through the zodiac from the Lot's natal sign.
    Deeper levels are sub-periods within each Level 1 (and subsequent) period,
    starting from the same sign as their containing period.

    The output spans one full primary releasing circuit from the starting sign.

    Parameters
    ----------
    lot_longitude : float
        Ecliptic longitude of the Lot in the natal chart (degrees, 0–360).
    natal_jd : float
        Julian Day (UT) of birth.
    levels : int
        Number of releasing levels to generate (1–4, default 4).
    lot_name : str
        Name of the releasing Lot: ``"Spirit"``, ``"Fortune"``, ``"Eros"``, or
        ``"Necessity"``. Default ``"Spirit"``. Governs the Spirit/Fortune
        start-sign adjustment rule and the lot_name field on each period.
    fortune_longitude : float | None
        Ecliptic longitude of the Lot of Fortune in the natal chart (degrees).
        Required for angularity classification (peak periods) and for the
        Spirit start-sign adjustment rule. Pass None to disable both.
    use_loosing_of_bond : bool
        When True (default), applies the Loosing of the Bond doctrine:
        releasing skips to the opposite sign when a long sign completes a
        full circuit back to the starting sign.
    policy : TimelordComputationPolicy | None
        Computation policy governing the symbolic year-length constant.
        Uses DEFAULT_TIMELORD_POLICY when None (360-day year).

    Returns
    -------
    list[ReleasingPeriod]
        All releasing periods across the requested levels, in chronological
        order (Level 1, then interleaved deeper levels inside each L1 period).

    Raises
    ------
    ValueError
        If lot_longitude or natal_jd is not finite.
        If fortune_longitude is provided but not finite.
        If lot_name is not one of the four recognised lot names.
        If levels is not in the range 1–4.
    """
    if not math.isfinite(lot_longitude):
        raise ValueError("lot_longitude must be finite")
    if not math.isfinite(natal_jd):
        raise ValueError("natal_jd must be finite")
    if not (1 <= levels <= _ZR_MAX_LEVEL):
        raise ValueError(
            f"zodiacal_releasing: levels must be 1–{_ZR_MAX_LEVEL}, got {levels!r}"
        )
    if lot_name not in {"Spirit", "Fortune", "Eros", "Necessity"}:
        raise ValueError("lot_name must be Spirit, Fortune, Eros, or Necessity")
    if fortune_longitude is not None and not math.isfinite(fortune_longitude):
        raise ValueError("fortune_longitude must be finite when provided")

    pol = _resolve_timelord_policy(policy)
    _eff_year_days  = pol.zr_year.year_days
    _eff_month_days = _eff_year_days / 12.0
    _eff_level_days: dict[int, float] = {
        1: _eff_year_days,
        2: _eff_month_days,
        3: _eff_month_days / 12.0,
        4: (_eff_month_days / 12.0) / 12.0,
    }

    start_sign = _resolve_releasing_start_sign(
        lot_longitude,
        lot_name,
        fortune_longitude,
    )
    fortune_sign = None if fortune_longitude is None else sign_of(fortune_longitude)[0]
    max_jd = natal_jd + _TOTAL_MINOR_YEARS * _eff_year_days

    return _generate_releasing(
        start_sign=start_sign,
        start_jd=natal_jd,
        level=1,
        max_level=levels,
        max_jd=max_jd,
        lot_name=lot_name,
        fortune_sign=fortune_sign,
        use_loosing_of_bond=use_loosing_of_bond,
        level_days=_eff_level_days,
        year_days=_eff_year_days,
    )


def current_releasing(
    lot_longitude: float,
    natal_jd: float,
    current_jd: float,
    *,
    lot_name: str = "Spirit",
    fortune_longitude: float | None = None,
    use_loosing_of_bond: bool = True,
    policy: "TimelordComputationPolicy | None" = None,
) -> list[ReleasingPeriod]:
    """
    Find the four Zodiacal Releasing periods (one per level) active at a date.

    Parameters
    ----------
    lot_longitude : float
        Ecliptic longitude of the Lot in the natal chart (degrees, 0–360).
    natal_jd : float
        Julian Day (UT) of birth.
    current_jd : float
        Julian Day (UT) of the date to evaluate.
    lot_name : str
        Name of the releasing Lot. Passed through to zodiacal_releasing().
        Default ``"Spirit"``.
    fortune_longitude : float | None
        Ecliptic longitude of the Lot of Fortune. Passed through to
        zodiacal_releasing(). Pass None to disable angularity classification.
    use_loosing_of_bond : bool
        Whether to apply the Loosing of the Bond doctrine. Default True.
    policy : TimelordComputationPolicy | None
        Computation policy governing the symbolic year-length constant.
        Uses DEFAULT_TIMELORD_POLICY when None.

    Returns
    -------
    list[ReleasingPeriod]
        List of up to 4 ReleasingPeriod objects (Levels 1–4) active at current_jd.
        If a level cannot be determined, the last valid period for that level
        is returned.

    Raises
    ------
    ValueError
        If current_jd is not finite.
        If current_jd is before natal_jd or at or beyond one full primary
        releasing circuit.
    """
    pol = _resolve_timelord_policy(policy)
    _eff_cap_days = _TOTAL_MINOR_YEARS * pol.zr_year.year_days

    if not math.isfinite(current_jd):
        raise ValueError("current_jd must be finite")
    if current_jd < natal_jd:
        raise ValueError("current_jd must not be earlier than natal_jd.")

    if current_jd >= natal_jd + _eff_cap_days:
        raise ValueError(
            "current_jd is at or beyond the full Zodiacal Releasing circuit cap."
        )

    all_periods = zodiacal_releasing(
        lot_longitude,
        natal_jd,
        levels=4,
        lot_name=lot_name,
        fortune_longitude=fortune_longitude,
        use_loosing_of_bond=use_loosing_of_bond,
        policy=policy,
    )

    active: list[ReleasingPeriod] = []
    for target_level in (1, 2, 3, 4):
        level_periods = [p for p in all_periods if p.level == target_level]
        found: ReleasingPeriod | None = None
        for p in level_periods:
            if p.start_jd <= current_jd < p.end_jd:
                found = p
                break
        if found is None and level_periods:
            # Edge case: exactly at a boundary — use the last period whose
            # start is ≤ current_jd
            candidates = [p for p in level_periods if p.start_jd <= current_jd]
            if candidates:
                found = candidates[-1]
        if found is not None:
            active.append(found)

    return active

# (end of file — duplicate old Valens P6+ stubs removed during full constitutional phases pass.
# The canonical, up-to-date Valens Distributions layer implementation (P1–P12) lives in the
# dedicated block after ZRSequenceProfile, including P7 dignities bridges and current wiring.)

