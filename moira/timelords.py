"""
Moira — Timelords Engine
Governs the timelord Engine surfaces for Firdaria and Zodiacal Releasing: sequence construction, hierarchical grouping, active-period lookup, condition profiles, and aggregate profiles.

Boundary: owns Firdaria sequence arithmetic and sub-period allocation, Zodiacal Releasing recursion and angularity classification, timelord policy vessels, result vessels, and relational vessels. Delegates domicile ruler lookup to moira.profections.

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
    CHALDEAN_ORDER, MINOR_YEARS, FirdarSequenceKind, ZRAngularityClass,
    FirdarYearPolicy, ZRYearPolicy, TimelordComputationPolicy,
    DEFAULT_TIMELORD_POLICY, FirdarPeriod, ReleasingPeriod, FirdarMajorGroup,
    ZRPeriodGroup, FirdarConditionProfile, ZRConditionProfile,
    FirdarSequenceProfile, ZRSequenceProfile, FirdarActivePair, ZRLevelPair,
    firdaria, current_firdaria, zodiacal_releasing, current_releasing,
    group_firdaria, group_releasing, firdar_condition_profile,
    zr_condition_profile, firdar_sequence_profile, zr_sequence_profile,
    firdar_active_pair, zr_level_pair, validate_firdaria_output,
    validate_releasing_output
"""

from dataclasses import dataclass, field
from datetime import datetime
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
    "ZRAngularityClass",
    # Policy surfaces
    "FirdarYearPolicy",
    "ZRYearPolicy",
    "TimelordComputationPolicy",
    "DEFAULT_TIMELORD_POLICY",
    # Truth-preservation vessels
    "FirdarPeriod",
    "ReleasingPeriod",
    # Relational vessels
    "FirdarMajorGroup",
    "ZRPeriodGroup",
    # Condition vessels
    "FirdarConditionProfile",
    "ZRConditionProfile",
    # Aggregate vessels
    "FirdarSequenceProfile",
    "ZRSequenceProfile",
    # Network vessels
    "FirdarActivePair",
    "ZRLevelPair",
    # Computational functions
    "firdaria",
    "current_firdaria",
    "zodiacal_releasing",
    "current_releasing",
    "group_firdaria",
    "group_releasing",
    "firdar_condition_profile",
    "zr_condition_profile",
    "firdar_sequence_profile",
    "zr_sequence_profile",
    "firdar_active_pair",
    "zr_level_pair",
    "validate_firdaria_output",
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


def _firdar_sequence_kind(is_day_chart: bool, variant: str) -> str:
    """Return the FirdarSequenceKind string for a (sect, variant) pair."""
    if is_day_chart:
        return FirdarSequenceKind.DIURNAL
    if variant == "bonatti":
        return FirdarSequenceKind.NOCTURNAL_BONATTI
    return FirdarSequenceKind.NOCTURNAL_STANDARD


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
_ZR_LONG_SIGNS = {sign for sign, years in MINOR_YEARS.items() if years > 17}


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


@dataclass(frozen=True, slots=True)
class TimelordComputationPolicy:
    """
    Lean doctrine surface for the Timelord subsystem.

    The default policy preserves current behavior exactly. Override
    sub-policies to govern year-length constants without altering
    per-chart inputs (is_day_chart, variant, lot_longitude, etc.).

    firdaria_year  — governs the Julian-year constant for Firdaria
    zr_year        — governs the symbolic-year constant for Zodiacal Releasing
    """
    firdaria_year: FirdarYearPolicy = field(default_factory=FirdarYearPolicy)
    zr_year:       ZRYearPolicy     = field(default_factory=ZRYearPolicy)


DEFAULT_TIMELORD_POLICY = TimelordComputationPolicy()


def _validate_timelord_policy(
    policy: TimelordComputationPolicy,
) -> TimelordComputationPolicy:
    if not isinstance(policy.firdaria_year, FirdarYearPolicy):
        raise TypeError("policy.firdaria_year must be a FirdarYearPolicy")
    if not isinstance(policy.zr_year, ZRYearPolicy):
        raise TypeError("policy.zr_year must be a ZRYearPolicy")
    if policy.firdaria_year.year_days <= 0:
        raise ValueError("policy.firdaria_year.year_days must be positive")
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
        Behavioral invariants:
            - All consumers treat ReleasingPeriod fields as read-only after construction

    Canon: Vettius Valens, Anthology II; Chris Brennan, "Hellenistic Astrology" Ch.10

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.timelords.ReleasingPeriod",
      "risk": "high",
      "api": {
        "frozen": ["level", "sign", "ruler", "start_jd", "end_jd", "years"],
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
    angularity_class: str | None = None  # ZRAngularityClass constant, or None if non-peak

    def __post_init__(self) -> None:
        if self.level not in (1, 2, 3, 4):
            raise ValueError(f"ReleasingPeriod.level must be 1–4, got {self.level}")
        if self.sign not in SIGNS:
            raise ValueError(f"ReleasingPeriod.sign must be a valid zodiac sign, got '{self.sign}'")
        if not math.isfinite(self.start_jd) or not math.isfinite(self.end_jd):
            raise ValueError("ReleasingPeriod start_jd and end_jd must be finite")
        if self.end_jd <= self.start_jd:
            raise ValueError("ReleasingPeriod end_jd must be greater than start_jd")

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
            - Angular-class counts match the supplied profiles and sum to `peak_period_count`.
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
        if self.angular_count + self.succedent_count + self.cadent_count \
                != self.peak_period_count:
            raise ValueError(
                "ZRSequenceProfile angular + succedent + cadent must equal peak_period_count"
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
    return {
        0: 1,
        3: 4,
        6: 7,
        9: 10,
    }.get(offset)


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
        angularity_from_fortune = _fortune_angularity(current_sign, fortune_sign)

        rp = ReleasingPeriod(
            level=level,
            sign=current_sign,
            ruler=DOMICILE_RULERS[current_sign],
            start_jd=cursor_jd,
            end_jd=effective_end,
            years=effective_years,
            lot_name=lot_name,
            is_loosing_of_bond=next_is_loosing_of_bond,
            is_peak_period=angularity_from_fortune is not None,
            angularity_from_fortune=angularity_from_fortune,
            use_loosing_of_bond=use_loosing_of_bond,
            angularity_class=_zr_angularity_class(angularity_from_fortune),
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
        If current_jd is before natal_jd or beyond one full primary releasing circuit.
    """
    pol = _resolve_timelord_policy(policy)
    _eff_cap_days = _TOTAL_MINOR_YEARS * pol.zr_year.year_days

    if not math.isfinite(current_jd):
        raise ValueError("current_jd must be finite")
    if current_jd < natal_jd:
        raise ValueError("current_jd must not be earlier than natal_jd.")

    if current_jd > natal_jd + _eff_cap_days:
        raise ValueError("current_jd is beyond the full Zodiacal Releasing circuit cap.")

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
