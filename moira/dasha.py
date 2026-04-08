"""
Moira — dasha.py
The Dasha Engine: governs Vimshottari Dasha period computation for Vedic
predictive astrology.

Boundary: owns Vimshottari sequence arithmetic, nakshatra-based period
initialisation, recursive sub-period generation, active-period lookup,
doctrinal policy surfaces, classification namespacing, integrated condition
profiling, chart-wide sequence aggregation, and lord-pair network projection.
Delegates sidereal longitude conversion and nakshatra lord tables to sidereal.
Delegates Julian Day arithmetic to julian. Does NOT own natal chart construction
or ephemeris state.

Public surface:
    Constants:
        VIMSHOTTARI_YEARS, VIMSHOTTARI_SEQUENCE, VIMSHOTTARI_TOTAL,
        VIMSHOTTARI_YEAR_BASIS, VIMSHOTTARI_LEVEL_NAMES
    Classification:
        DashaLordType
    Policy:
        VimshottariYearPolicy, VimshottariAyanamsaPolicy,
        VimshottariComputationPolicy, DEFAULT_VIMSHOTTARI_POLICY
    Vessels:
        DashaPeriod           — single dasha period with nested sub-periods
        DashaActiveLine       — named chain of active periods across levels
        DashaConditionProfile — integrated per-period condition profile
        DashaSequenceProfile  — chart-wide aggregate over a Mahadasha sequence
        DashaLordPair         — Mahadasha / Antardasha lord network node
    Functions:
        vimshottari            — compute the full Vimshottari sequence from birth
        current_dasha          — active periods at a query Julian Day
        dasha_balance          — birth Mahadasha lord and remaining years
        dasha_active_line      — construct DashaActiveLine from current_dasha output
        dasha_condition_profile — build condition profile for a single period
        dasha_sequence_profile  — aggregate profile for a full sequence
        dasha_lord_pair         — Mahadasha / Antardasha pair from an active line
        validate_vimshottari_output — verify cross-layer invariants on a sequence

Import-time side effects: None

External dependency assumptions:
    - No third-party packages; stdlib only plus internal moira modules.
    - sidereal module must be importable (provides NAKSHATRA_LORDS, NAKSHATRA_SPAN,
      tropical_to_sidereal, Ayanamsa).
"""

import math
from dataclasses import dataclass, field
from datetime import datetime

from .constants import JULIAN_YEAR
from .julian import CalendarDateTime, calendar_datetime_from_jd, datetime_from_jd, decimal_year_from_jd
from .sidereal import tropical_to_sidereal, Ayanamsa, NAKSHATRA_LORDS, NAKSHATRA_SPAN, NAKSHATRA_NAMES


# ---------------------------------------------------------------------------
# Phase 12 — Public API Curation
# ---------------------------------------------------------------------------

__all__ = [
    # Constants
    "VIMSHOTTARI_YEARS",
    "VIMSHOTTARI_SEQUENCE",
    "VIMSHOTTARI_TOTAL",
    "VIMSHOTTARI_YEAR_BASIS",
    "VIMSHOTTARI_LEVEL_NAMES",
    # Classification namespace
    "DashaLordType",
    # Policy surfaces
    "VimshottariYearPolicy",
    "VimshottariAyanamsaPolicy",
    "VimshottariComputationPolicy",
    "DEFAULT_VIMSHOTTARI_POLICY",
    # Truth-preservation vessel
    "DashaPeriod",
    # Relational vessel
    "DashaActiveLine",
    # Condition vessel
    "DashaConditionProfile",
    # Aggregate vessel
    "DashaSequenceProfile",
    # Network vessel
    "DashaLordPair",
    # Computational functions
    "vimshottari",
    "current_dasha",
    "dasha_balance",
    "dasha_active_line",
    "dasha_condition_profile",
    "dasha_sequence_profile",
    "dasha_lord_pair",
    "validate_vimshottari_output",
]


# ---------------------------------------------------------------------------
# Phase 2 — Classification namespace
# ---------------------------------------------------------------------------

class DashaLordType:
    """
    Typed classification of a Vimshottari dasha lord by its Jyotish planetary
    grouping.

    The nine Vimshottari lords themselves are standard across all schools.
    The grouping into LUMINARY, INNER, OUTER, and NODE is an internal
    analytical classification used by this engine; it is derived from the
    planet name alone and does not depend on chart context.

    LUMINARY — Sun, Moon  (the two lights; fastest movers; foundational vitality)
    INNER    — Mercury, Venus  (inner planets; sub-solar orbit)
    OUTER    — Mars, Jupiter, Saturn  (outer planets; supra-solar orbit)
    NODE     — Rahu, Ketu  (lunar nodes; shadow planets; karmic axis)
    """
    LUMINARY = "luminary"
    INNER    = "inner"
    OUTER    = "outer"
    NODE     = "node"


_DASHA_LORD_TYPE: dict[str, str] = {
    "Sun":     DashaLordType.LUMINARY,
    "Moon":    DashaLordType.LUMINARY,
    "Mercury": DashaLordType.INNER,
    "Venus":   DashaLordType.INNER,
    "Mars":    DashaLordType.OUTER,
    "Jupiter": DashaLordType.OUTER,
    "Saturn":  DashaLordType.OUTER,
    "Rahu":    DashaLordType.NODE,
    "Ketu":    DashaLordType.NODE,
}


# ---------------------------------------------------------------------------
# Vimshottari constants
# ---------------------------------------------------------------------------

VIMSHOTTARI_YEARS: dict[str, int] = {
    "Ketu": 7, "Venus": 20, "Sun": 6, "Moon": 10, "Mars": 7,
    "Rahu": 18, "Jupiter": 16, "Saturn": 19, "Mercury": 17,
}

VIMSHOTTARI_SEQUENCE: list[str] = [
    "Ketu", "Venus", "Sun", "Moon", "Mars",
    "Rahu", "Jupiter", "Saturn", "Mercury",
]

VIMSHOTTARI_TOTAL = 120.0  # years

VIMSHOTTARI_YEAR_BASIS: dict[str, float] = {
    "savana_360": 360.0,
    "julian_365.25": JULIAN_YEAR,
}

VIMSHOTTARI_LEVEL_NAMES: dict[int, str] = {
    1: "Mahadasha",
    2: "Antardasha",
    3: "Pratyantardasha",
    4: "Sookshma",
    5: "Prana",
}


# ---------------------------------------------------------------------------
# Phase 4 — Doctrine / Policy Surface
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class VimshottariYearPolicy:
    """
    Doctrine surface for the Vimshottari year-basis doctrine.

    year_basis selects which year length is used to convert period durations
    (in years) to Julian Day boundaries. Must be a key in VIMSHOTTARI_YEAR_BASIS.

    Supported keys:
        "julian_365.25" — standard Julian year (default, most widely used)
        "savana_360"    — Vedic civil/savana year of 360 days
    """
    year_basis: str = "julian_365.25"


@dataclass(frozen=True, slots=True)
class VimshottariAyanamsaPolicy:
    """
    Doctrine surface for Vimshottari nakshatra ayanamsa selection.

    ayanamsa_system governs which ayanamsa is applied when converting the
    Moon's tropical longitude to its sidereal nakshatra position.
    Default: Lahiri (the most widely adopted standard in modern Jyotish).
    """
    ayanamsa_system: str = Ayanamsa.LAHIRI


@dataclass(frozen=True, slots=True)
class VimshottariComputationPolicy:
    """
    Lean doctrine surface for the Vimshottari subsystem.

    The default policy preserves current behavior exactly. Override
    sub-policies to govern year-basis and ayanamsa without altering
    per-chart inputs (moon_tropical_lon, natal_jd, levels).

    year     — governs the year-basis doctrine
    ayanamsa — governs the nakshatra ayanamsa selection
    """
    year:     VimshottariYearPolicy     = field(default_factory=VimshottariYearPolicy)
    ayanamsa: VimshottariAyanamsaPolicy = field(default_factory=VimshottariAyanamsaPolicy)


DEFAULT_VIMSHOTTARI_POLICY = VimshottariComputationPolicy()


def _validate_vimshottari_policy(
    policy: VimshottariComputationPolicy,
) -> VimshottariComputationPolicy:
    if not isinstance(policy.year, VimshottariYearPolicy):
        raise TypeError("policy.year must be a VimshottariYearPolicy")
    if not isinstance(policy.ayanamsa, VimshottariAyanamsaPolicy):
        raise TypeError("policy.ayanamsa must be a VimshottariAyanamsaPolicy")
    if policy.year.year_basis not in VIMSHOTTARI_YEAR_BASIS:
        raise ValueError(
            f"policy.year.year_basis '{policy.year.year_basis}' is not a "
            f"supported Vimshottari doctrine key"
        )
    if not policy.ayanamsa.ayanamsa_system:
        raise ValueError("policy.ayanamsa.ayanamsa_system must be non-empty")
    return policy


def _resolve_vimshottari_policy(
    policy: VimshottariComputationPolicy | None,
) -> VimshottariComputationPolicy:
    return _validate_vimshottari_policy(
        DEFAULT_VIMSHOTTARI_POLICY if policy is None else policy
    )


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class DashaPeriod:
    """
    RITE: The Dasha Period Vessel

    THEOREM: Governs the storage of a single Vimshottari dasha period at any
    hierarchical level, with optional recursive sub-period nesting.

    RITE OF PURPOSE:
        DashaPeriod is the authoritative data vessel for a single Vimshottari dasha
        period produced by the Dasha Engine. It captures the hierarchical level
        (Mahadasha through Sookshma), the ruling planet, the start and end Julian
        Days, and a list of child sub-periods. Without it, callers would receive
        unstructured collections with no field-level guarantees. It exists to give
        every higher-level consumer a single, named, mutable record of each dasha
        period and its nested sub-periods.

    LAW OF OPERATION:
        Responsibilities:
            - Store a single dasha period as named, typed fields
            - Carry nested sub-periods in the sub list (populated by _build_sub_periods)
            - Expose UTC datetime and CalendarDateTime views via read-only properties
            - Expose duration in years via the years property
            - Serve as the return type of vimshottari() and current_dasha()
        Non-responsibilities:
            - Computing period boundaries (delegates to vimshottari / _build_sub_periods)
            - Converting sidereal longitude (delegates to sidereal)
        Dependencies:
            - Populated by vimshottari() and _build_sub_periods()
            - start_dt / end_dt delegate to datetime_from_jd()
            - start_calendar / end_calendar delegate to calendar_datetime_from_jd()
        Structural invariants:
            - level is in [1, 5]
            - end_jd > start_jd
            - sub is empty for leaf periods (level == 5 or levels not requested)
        Behavioral invariants:
            - years property is always (end_jd - start_jd) / year_days

    Canon: B.V. Raman, "A Manual of Hindu Astrology"; K.N. Rao, "Timing Events through Vimshottari Dasha"

    [MACHINE_CONTRACT v1]
    {
      "scope": "class",
      "id": "moira.dasha.DashaPeriod",
      "risk": "high",
      "api": {
        "frozen": ["level", "planet", "start_jd", "end_jd"],
        "internal": ["sub", "start_dt", "start_calendar", "end_dt", "end_calendar", "years"]
      },
      "state": {"mutable": true, "owners": ["vimshottari", "_build_sub_periods"]},
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
    level:     int       # 1=Mahadasha, 2=Antardasha, 3=Pratyantardasha, 4=Sookshma, 5=Prana
    planet:    str
    start_jd:  float
    end_jd:    float
    year_days: float = JULIAN_YEAR
    sub:       list["DashaPeriod"] = field(default_factory=list, repr=False)
    # Phase 1: preserved generative context
    year_basis:         str | None = None   # doctrinal name: "savana_360" or "julian_365.25"
    birth_nakshatra:    str | None = None   # Moon's nakshatra at birth (first Mahadasha only)
    nakshatra_fraction: float | None = None # fraction elapsed through birth nakshatra (first Mahadasha only)
    # Phase 2: typed classification
    lord_type: str | None = None            # DashaLordType constant for this period's planet

    def __post_init__(self) -> None:
        if self.level not in (1, 2, 3, 4, 5):
            raise ValueError(f"DashaPeriod.level must be 1–5, got {self.level}")
        if not math.isfinite(self.start_jd) or not math.isfinite(self.end_jd):
            raise ValueError("DashaPeriod start_jd and end_jd must be finite")
        if self.end_jd <= self.start_jd:
            raise ValueError("DashaPeriod end_jd must be greater than start_jd")
        if self.planet not in VIMSHOTTARI_SEQUENCE:
            raise ValueError(
                f"DashaPeriod.planet must be a Vimshottari lord, got '{self.planet}'"
            )

    # --- Phase 3: inspectability ---

    @property
    def is_node_dasha(self) -> bool:
        """True when this period belongs to a lunar node (Rahu or Ketu)."""
        return self.lord_type == DashaLordType.NODE

    @property
    def is_luminary_dasha(self) -> bool:
        """True when this period belongs to a luminary (Sun or Moon)."""
        return self.lord_type == DashaLordType.LUMINARY

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

    # --- Datetime views and derived properties ---

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
    def years(self) -> float:
        return (self.end_jd - self.start_jd) / self.year_days

    @property
    def level_name(self) -> str:
        return VIMSHOTTARI_LEVEL_NAMES.get(self.level, f"Level {self.level}")

    def __repr__(self) -> str:
        indent = "  " * (self.level - 1)
        return (f"{indent}L{self.level} {self.planet:<10} "
                f"{self.start_calendar.date_string()} → "
                f"{self.end_calendar.date_string()} "
                f"({self.years:.2f}y)")


# ---------------------------------------------------------------------------
# Phase 5 — Relational Formalization
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class DashaActiveLine:
    """
    RITE: The Dasha Active Line Vessel

    Formalizes the chain of currently active Vimshottari dasha periods
    across hierarchical levels.

    The list returned by current_dasha() has implicit ordering (index 0 =
    Mahadasha, index 1 = Antardasha, etc.) with no named access.
    DashaActiveLine makes the active-period chain explicit and named by
    doctrinal level, matching the canonical Jyotish terminology.

    Fields are None when that level was not generated or no active period
    exists at that level for the query date.

    Fields
    ------
    mahadasha       — the active Level 1 (Mahadasha) period
    antardasha      — the active Level 2 (Antardasha) period, or None
    pratyantardasha — the active Level 3 (Pratyantardasha) period, or None
    sookshma        — the active Level 4 (Sookshma) period, or None
    prana           — the active Level 5 (Prana) period, or None
    """
    mahadasha:       DashaPeriod
    antardasha:      DashaPeriod | None = None
    pratyantardasha: DashaPeriod | None = None
    sookshma:        DashaPeriod | None = None
    prana:           DashaPeriod | None = None

    def __post_init__(self) -> None:
        if self.mahadasha.level != 1:
            raise ValueError(
                f"DashaActiveLine.mahadasha must be level 1, got {self.mahadasha.level}"
            )
        _level_checks = [
            (self.antardasha,      2, "antardasha"),
            (self.pratyantardasha, 3, "pratyantardasha"),
            (self.sookshma,        4, "sookshma"),
            (self.prana,           5, "prana"),
        ]
        for period, expected_level, name in _level_checks:
            if period is not None and period.level != expected_level:
                raise ValueError(
                    f"DashaActiveLine.{name} must be level {expected_level}, "
                    f"got {period.level}"
                )
        # Phase 6 hardening — temporal containment of each level within its parent
        _containment_pairs = [
            (self.mahadasha,  self.antardasha,      "antardasha"),
            (self.antardasha, self.pratyantardasha,  "pratyantardasha"),
            (self.pratyantardasha, self.sookshma,    "sookshma"),
            (self.sookshma,   self.prana,            "prana"),
        ]
        for parent, child, name in _containment_pairs:
            if parent is not None and child is not None:
                if child.start_jd < parent.start_jd - 1e-6:
                    raise ValueError(
                        f"DashaActiveLine.{name} starts before its parent period"
                    )
                if child.end_jd > parent.end_jd + 1e-6:
                    raise ValueError(
                        f"DashaActiveLine.{name} ends after its parent period"
                    )

    @property
    def depth(self) -> int:
        """Number of non-None levels in this active chain."""
        return sum(
            1 for p in (
                self.mahadasha, self.antardasha, self.pratyantardasha,
                self.sookshma, self.prana,
            )
            if p is not None
        )

    def as_list(self) -> list[DashaPeriod]:
        """Return active periods in order from Mahadasha to the deepest level."""
        return [
            p for p in (
                self.mahadasha, self.antardasha, self.pratyantardasha,
                self.sookshma, self.prana,
            )
            if p is not None
        ]

    # --- Phase 6: lord-type chain properties ---

    @property
    def lord_types(self) -> tuple[str | None, ...]:
        """Lord-type strings (DashaLordType constants) for each active level,
        in order from Mahadasha to the deepest level."""
        return tuple(p.lord_type for p in self.as_list())

    @property
    def is_node_chain(self) -> bool:
        """True when any active period in the chain is governed by a node lord
        (Rahu or Ketu)."""
        return any(p.lord_type == DashaLordType.NODE for p in self.as_list())

    @property
    def is_complete(self) -> bool:
        """True when all five Vimshottari dasha levels are active (depth == 5)."""
        return self.depth == 5


def dasha_active_line(active_periods: list[DashaPeriod]) -> "DashaActiveLine":
    """
    Construct a DashaActiveLine from the flat list returned by current_dasha().

    Parameters
    ----------
    active_periods : list[DashaPeriod]
        The output of current_dasha() — one period per active level.

    Returns
    -------
    DashaActiveLine
        Named chain of active periods from Mahadasha to the deepest level.

    Raises
    ------
    ValueError
        If active_periods is empty or does not contain a level-1 period.
    """
    if not active_periods:
        raise ValueError("active_periods must not be empty")
    by_level: dict[int, DashaPeriod] = {p.level: p for p in active_periods}
    if 1 not in by_level:
        raise ValueError("active_periods must contain a level-1 (Mahadasha) period")
    return DashaActiveLine(
        mahadasha       = by_level[1],
        antardasha      = by_level.get(2),
        pratyantardasha = by_level.get(3),
        sookshma        = by_level.get(4),
        prana           = by_level.get(5),
    )


# ---------------------------------------------------------------------------
# Phase 7 — Integrated Local Condition
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class DashaConditionProfile:
    """
    Integrated local condition profile for a single Vimshottari dasha period.

    Assembles all preserved, classified, and inspectable truth from
    Phases 1–6 into one coherent per-period vessel. Callers do not need to
    reach across DashaPeriod fields, DashaLordType, and VIMSHOTTARI_LEVEL_NAMES
    to understand the full condition of a dasha period.

    Fields
    ------
    planet              — the ruling planet of this dasha period
    level               — 1 (Mahadasha) through 5 (Prana)
    level_name          — canonical Jyotish name: "Mahadasha" through "Prana"
    lord_type           — DashaLordType constant, or None if unclassified
    years               — duration in dasha years (computed from year_days)
    days                — duration in Julian days
    year_basis          — doctrinal year-length basis: "savana_360" or "julian_365.25"
    is_node_dasha       — True when lord_type == DashaLordType.NODE
    is_luminary_dasha   — True when lord_type == DashaLordType.LUMINARY
    birth_nakshatra     — Moon's nakshatra at birth (first Mahadasha only, else None)
    nakshatra_fraction  — fraction elapsed through birth nakshatra (first Mahadasha only)
    """
    planet:             str
    level:              int
    level_name:         str
    lord_type:          str | None
    years:              float
    days:               float
    year_basis:         str | None
    is_node_dasha:      bool
    is_luminary_dasha:  bool
    birth_nakshatra:    str | None
    nakshatra_fraction: float | None


def dasha_condition_profile(period: DashaPeriod) -> DashaConditionProfile:
    """
    Build a DashaConditionProfile from a DashaPeriod.

    Assembles all Phase 1–6 truth about the period into a single profile.
    This function is deterministic and has no side effects.

    Parameters
    ----------
    period : DashaPeriod
        Any DashaPeriod produced by vimshottari() or current_dasha().

    Returns
    -------
    DashaConditionProfile
    """
    return DashaConditionProfile(
        planet             = period.planet,
        level              = period.level,
        level_name         = period.level_name,
        lord_type          = period.lord_type,
        years              = period.years,
        days               = period.days,
        year_basis         = period.year_basis,
        is_node_dasha      = period.is_node_dasha,
        is_luminary_dasha  = period.is_luminary_dasha,
        birth_nakshatra    = period.birth_nakshatra,
        nakshatra_fraction = period.nakshatra_fraction,
    )


# ---------------------------------------------------------------------------
# Phase 8 — Aggregate Intelligence
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class DashaSequenceProfile:
    """
    Aggregate over a generated Vimshottari Mahadasha sequence.

    Derived from DashaConditionProfile vessels (Phase 7). Summarises the
    structural composition of a 120-year dasha cycle — how many lords of each
    type, the total nominal years, and whether the sequence contains any node
    dashas.

    The profiles tuple contains only level-1 (Mahadasha) profiles in the order
    they appear in the source vimshottari() list.

    Fields
    ------
    profiles        — Mahadasha condition profiles in sequence order
    mahadasha_count — total number of Mahadasha periods
    luminary_count  — Mahadashas whose lord is a luminary (Sun or Moon)
    inner_count     — Mahadashas whose lord is an inner planet (Mercury or Venus)
    outer_count     — Mahadashas whose lord is an outer planet (Mars, Jupiter, Saturn)
    node_count      — Mahadashas whose lord is a node (Rahu or Ketu)
    total_years     — sum of nominal years across all Mahadasha periods
    """
    profiles:        tuple["DashaConditionProfile", ...]
    mahadasha_count: int
    luminary_count:  int
    inner_count:     int
    outer_count:     int
    node_count:      int
    total_years:     float

    def __post_init__(self) -> None:
        if self.mahadasha_count != len(self.profiles):
            raise ValueError("DashaSequenceProfile.mahadasha_count must equal len(profiles)")
        if self.luminary_count != sum(
            1 for p in self.profiles if p.lord_type == DashaLordType.LUMINARY
        ):
            raise ValueError("DashaSequenceProfile.luminary_count does not match profiles")
        if self.inner_count != sum(
            1 for p in self.profiles if p.lord_type == DashaLordType.INNER
        ):
            raise ValueError("DashaSequenceProfile.inner_count does not match profiles")
        if self.outer_count != sum(
            1 for p in self.profiles if p.lord_type == DashaLordType.OUTER
        ):
            raise ValueError("DashaSequenceProfile.outer_count does not match profiles")
        if self.node_count != sum(
            1 for p in self.profiles if p.lord_type == DashaLordType.NODE
        ):
            raise ValueError("DashaSequenceProfile.node_count does not match profiles")
        if self.luminary_count + self.inner_count + self.outer_count + self.node_count \
                != self.mahadasha_count:
            raise ValueError(
                "DashaSequenceProfile lord-type counts must sum to mahadasha_count"
            )

    @property
    def profile_count(self) -> int:
        """Total number of Mahadasha profiles in this aggregate."""
        return len(self.profiles)

    @property
    def has_node_dashas(self) -> bool:
        """True when the sequence contains at least one node Mahadasha."""
        return self.node_count > 0


def dasha_sequence_profile(periods: list[DashaPeriod]) -> DashaSequenceProfile:
    """
    Build a DashaSequenceProfile from a Vimshottari period list.

    Aggregates over level-1 (Mahadasha) periods only. Sub-periods at deeper
    levels are ignored.

    Parameters
    ----------
    periods : list[DashaPeriod]
        The output of vimshottari() — Mahadashas with nested sub-periods.

    Returns
    -------
    DashaSequenceProfile
    """
    maha_profiles = tuple(
        dasha_condition_profile(p) for p in periods if p.level == 1
    )
    luminary = sum(1 for p in maha_profiles if p.lord_type == DashaLordType.LUMINARY)
    inner    = sum(1 for p in maha_profiles if p.lord_type == DashaLordType.INNER)
    outer    = sum(1 for p in maha_profiles if p.lord_type == DashaLordType.OUTER)
    node     = sum(1 for p in maha_profiles if p.lord_type == DashaLordType.NODE)

    return DashaSequenceProfile(
        profiles        = maha_profiles,
        mahadasha_count = len(maha_profiles),
        luminary_count  = luminary,
        inner_count     = inner,
        outer_count     = outer,
        node_count      = node,
        total_years     = sum(p.years for p in maha_profiles),
    )


# ---------------------------------------------------------------------------
# Phase 9 — Network Intelligence
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class DashaLordPair:
    """
    Network node: the structural relationship between the active Mahadasha
    and Antardasha lords.

    Projects the Phase 5 relation layer (DashaActiveLine) and Phase 7
    condition profiles into an explicit structural edge between the two
    most prominent simultaneously active dasha lords. This makes the
    "two lords simultaneously" relationship available as a named,
    inspectable network unit rather than two separate lookups.

    antar_profile is None when the DashaActiveLine was built at levels=1
    (no Antardasha generated), or when no Antardasha is active.

    Fields
    ------
    maha_profile   — condition profile of the active Mahadasha (level 1)
    antar_profile  — condition profile of the active Antardasha (level 2), or None
    """
    maha_profile:  DashaConditionProfile
    antar_profile: DashaConditionProfile | None

    def __post_init__(self) -> None:
        if self.maha_profile.level != 1:
            raise ValueError(
                f"DashaLordPair.maha_profile must be level 1, got {self.maha_profile.level}"
            )
        if self.antar_profile is not None and self.antar_profile.level != 2:
            raise ValueError(
                f"DashaLordPair.antar_profile must be level 2, got {self.antar_profile.level}"
            )

    @property
    def has_antar(self) -> bool:
        """True when an Antardasha is present in this pair."""
        return self.antar_profile is not None

    @property
    def is_same_lord(self) -> bool:
        """True when the Mahadasha and Antardasha lords are the same planet."""
        return (
            self.antar_profile is not None
            and self.maha_profile.planet == self.antar_profile.planet
        )

    @property
    def is_same_lord_type(self) -> bool:
        """True when both lords share the same DashaLordType classification."""
        return (
            self.antar_profile is not None
            and self.maha_profile.lord_type == self.antar_profile.lord_type
        )

    @property
    def involves_node(self) -> bool:
        """True when either the Mahadasha or Antardasha lord is a node (Rahu or Ketu)."""
        if self.maha_profile.is_node_dasha:
            return True
        return self.antar_profile is not None and self.antar_profile.is_node_dasha

    @property
    def both_are_nodes(self) -> bool:
        """True when both the Mahadasha and Antardasha lords are nodes."""
        return (
            self.antar_profile is not None
            and self.maha_profile.is_node_dasha
            and self.antar_profile.is_node_dasha
        )


def dasha_lord_pair(line: "DashaActiveLine") -> DashaLordPair:
    """
    Build a DashaLordPair from a DashaActiveLine.

    Extracts the Mahadasha and Antardasha profiles from the active chain
    and wraps them in a DashaLordPair network node.

    Parameters
    ----------
    line : DashaActiveLine
        An active dasha chain from dasha_active_line().

    Returns
    -------
    DashaLordPair
    """
    return DashaLordPair(
        maha_profile  = dasha_condition_profile(line.mahadasha),
        antar_profile = dasha_condition_profile(line.antardasha)
                        if line.antardasha is not None else None,
    )


# ---------------------------------------------------------------------------
# Phase 10 — Full-Subsystem Hardening
# ---------------------------------------------------------------------------

def _validate_dasha_sub_containment(period: DashaPeriod) -> None:
    """Recursively verify that sub-periods are temporally contained in their parent."""
    for i, sub in enumerate(period.sub):
        if sub.start_jd < period.start_jd - 1e-9:
            raise ValueError(
                f"validate_vimshottari_output: '{sub.planet}' (L{sub.level}) "
                f"starts before its parent '{period.planet}'"
            )
        if sub.end_jd > period.end_jd + 1e-9:
            raise ValueError(
                f"validate_vimshottari_output: '{sub.planet}' (L{sub.level}) "
                f"ends after its parent '{period.planet}'"
            )
        if i > 0 and period.sub[i - 1].end_jd > sub.start_jd + 1e-9:
            raise ValueError(
                f"validate_vimshottari_output: sub-periods of '{period.planet}' "
                f"overlap or are out of order "
                f"('{period.sub[i - 1].planet}' end_jd={period.sub[i - 1].end_jd:.6f} > "
                f"'{sub.planet}' start_jd={sub.start_jd:.6f})"
            )
        _validate_dasha_sub_containment(sub)


def validate_vimshottari_output(periods: list[DashaPeriod]) -> None:
    """
    Verify that a vimshottari() output satisfies all cross-layer invariants.

    Checks the following invariants:
    - Level-1 (Mahadasha) periods are in chronological order with no JD overlaps.
    - Every planet in the list is a recognised Vimshottari lord (enforced
      by DashaPeriod.__post_init__, not re-checked here).
    - Sub-periods at every level are temporally contained within their parent and
      are in chronological order with no overlaps.

    Raises
    ------
    ValueError
        If periods is empty, or on the first invariant violation found.
        Passes silently when all invariants hold.
    """
    if not periods:
        raise ValueError("validate_vimshottari_output: periods list must not be empty")
    level1 = [p for p in periods if p.level == 1]

    # Cross-layer invariant 1: level-1 periods in chronological order, no overlap
    for i in range(len(level1) - 1):
        if level1[i].end_jd > level1[i + 1].start_jd + 1e-9:
            raise ValueError(
                f"validate_vimshottari_output: Mahadasha periods overlap or are out of "
                f"order ('{level1[i].planet}' end_jd={level1[i].end_jd:.6f} > "
                f"'{level1[i + 1].planet}' start_jd={level1[i + 1].start_jd:.6f})"
            )

    # Cross-layer invariant 2: sub-period containment and ordering at all depths
    for maha in level1:
        _validate_dasha_sub_containment(maha)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sequence_from(lord: str) -> list[str]:
    """
    Return the VIMSHOTTARI_SEQUENCE starting from a given lord.

    For example, _sequence_from("Moon") returns:
        ["Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury",
         "Ketu", "Venus", "Sun"]
    """
    if lord not in VIMSHOTTARI_SEQUENCE:
        raise ValueError(
            f"'{lord}' is not a recognised Vimshottari lord. "
            f"Valid lords: {VIMSHOTTARI_SEQUENCE}"
        )
    start_idx = VIMSHOTTARI_SEQUENCE.index(lord)
    return VIMSHOTTARI_SEQUENCE[start_idx:] + VIMSHOTTARI_SEQUENCE[:start_idx]


def _resolve_vimshottari_year_days(year_basis: str) -> float:
    if year_basis not in VIMSHOTTARI_YEAR_BASIS:
        raise ValueError("year_basis must be a supported Vimshottari doctrine key")
    return VIMSHOTTARI_YEAR_BASIS[year_basis]


def _build_sub_periods(
    period: DashaPeriod,
    levels: int,
    year_days: float,
    year_basis: str,
) -> None:
    """
    Recursively populate period.sub with child DashaPeriods.

    Each child is an Antardasha (or deeper level) within *period*.
    Sub-period durations follow:
        sub_years = (VIMSHOTTARI_YEARS[sub_planet] / VIMSHOTTARI_TOTAL)
                    × period.years
    The sequence of sub-planets starts from the period's own lord.

    Parameters
    ----------
    period     : the parent DashaPeriod whose .sub list will be filled
    levels     : how many more levels to generate below this one
                 (0 means stop — do not recurse further)
    year_basis : doctrinal year-basis name, propagated to all child periods
    """
    if levels <= 0:
        return

    sub_sequence = _sequence_from(period.planet)
    current_jd = period.start_jd

    for sub_planet in sub_sequence:
        sub_years = (VIMSHOTTARI_YEARS[sub_planet] / VIMSHOTTARI_TOTAL) * period.years
        sub_end_jd = current_jd + sub_years * year_days

        child = DashaPeriod(
            level=period.level + 1,
            planet=sub_planet,
            start_jd=current_jd,
            end_jd=sub_end_jd,
            year_days=year_days,
            year_basis=year_basis,
            lord_type=_DASHA_LORD_TYPE[sub_planet],
        )

        # Recurse for deeper levels
        _build_sub_periods(child, levels - 1, year_days, year_basis)

        period.sub.append(child)
        current_jd = sub_end_jd


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def vimshottari(
    moon_tropical_lon: float,
    natal_jd: float,
    levels: int = 2,
    ayanamsa_system: str | None = None,
    *,
    year_basis: str | None = None,
    policy: VimshottariComputationPolicy | None = None,
) -> list[DashaPeriod]:
    """
    Compute the full Vimshottari Dasha sequence from birth.

    Parameters
    ----------
    moon_tropical_lon : Moon's tropical ecliptic longitude at birth
    natal_jd          : Julian Day of birth (UT)
    levels            : number of levels to generate (1=Mahadasha only,
                        2=+Antardasha, 3=+Pratyantardasha, 4=+Sookshma,
                        5=+Prana)
    ayanamsa_system   : ayanamsa for Moon's nakshatra; None uses policy default
    year_basis        : year-length doctrine key; None uses policy default
    policy            : VimshottariComputationPolicy governing doctrinal defaults

    Returns
    -------
    List of DashaPeriod at level 1 (each with .sub populated to requested depth)
    """
    pol = _resolve_vimshottari_policy(policy)
    year_basis      = year_basis      if year_basis      is not None else pol.year.year_basis
    ayanamsa_system = ayanamsa_system if ayanamsa_system is not None else pol.ayanamsa.ayanamsa_system

    if not math.isfinite(moon_tropical_lon):
        raise ValueError("moon_tropical_lon must be finite")
    if not math.isfinite(natal_jd):
        raise ValueError("natal_jd must be finite")

    year_days = _resolve_vimshottari_year_days(year_basis)
    levels = max(1, min(levels, 5))

    # 1. Convert Moon's longitude to sidereal
    sid_lon = tropical_to_sidereal(moon_tropical_lon, natal_jd, system=ayanamsa_system)

    # 2. Identify birth nakshatra
    nak_idx = int(sid_lon / NAKSHATRA_SPAN) % 27

    # 3. Compute how far through the nakshatra the Moon has travelled
    degrees_elapsed = sid_lon - nak_idx * NAKSHATRA_SPAN
    fraction_elapsed = degrees_elapsed / NAKSHATRA_SPAN  # 0.0–1.0

    # 4. The first Mahadasha lord is the lord of the birth nakshatra
    starting_lord = NAKSHATRA_LORDS[nak_idx]
    starting_years = VIMSHOTTARI_YEARS[starting_lord]

    # Remaining years left in the first Mahadasha at the moment of birth
    remaining_first = starting_years * (1.0 - fraction_elapsed)

    # 5. Build the ordered sequence of Mahadashas starting from the birth lord
    maha_sequence = _sequence_from(starting_lord)

    # 6. Generate one full rotation of all 9 Mahadasha lords.
    #    The actual span is always less than 120 Vimshottari years because the
    #    first period is truncated to the remaining nakshatra fraction.
    mahadashas: list[DashaPeriod] = []
    current_jd = natal_jd

    for i, lord in enumerate(maha_sequence):
        if i == 0:
            # First period: only the remaining portion is in the future
            duration_years = remaining_first
        else:
            duration_years = float(VIMSHOTTARI_YEARS[lord])

        end_jd = current_jd + duration_years * year_days

        maha = DashaPeriod(
            level=1,
            planet=lord,
            start_jd=current_jd,
            end_jd=end_jd,
            year_days=year_days,
            year_basis=year_basis,
            # Birth nakshatra context is doctrinal truth of the first period only
            birth_nakshatra=NAKSHATRA_NAMES[nak_idx] if i == 0 else None,
            nakshatra_fraction=fraction_elapsed if i == 0 else None,
            lord_type=_DASHA_LORD_TYPE[lord],
        )

        # Populate sub-periods for the requested depth
        _build_sub_periods(maha, levels - 1, year_days, year_basis)

        mahadashas.append(maha)
        current_jd = end_jd

    return mahadashas


def current_dasha(
    moon_tropical_lon: float,
    natal_jd: float,
    current_jd: float,
    ayanamsa_system: str | None = None,
    *,
    year_basis: str | None = None,
    levels: int = 5,
    policy: VimshottariComputationPolicy | None = None,
) -> list[DashaPeriod]:
    """
    Return the active dasha periods at current_jd.

    Returns a list of active periods from Mahadasha down to the deepest
    requested generated level, up to Prana.

    Parameters
    ----------
    moon_tropical_lon : Moon's tropical ecliptic longitude at birth
    natal_jd          : Julian Day of birth (UT)
    current_jd        : Julian Day of the query moment
    ayanamsa_system   : ayanamsa for Moon's nakshatra; None uses policy default
    year_basis        : year-length doctrine key; None uses policy default
    levels            : number of dasha levels to generate (1–5; default 5)
    policy            : VimshottariComputationPolicy governing doctrinal defaults

    Returns
    -------
    List of active DashaPeriod objects, one per active level from Mahadasha
    down to the deepest generated level.

    Raises
    ------
    ValueError
        If current_jd is not finite, is earlier than natal_jd, is beyond the
        Vimshottari cycle cap, or falls outside the generated sequence.
    """
    pol = _resolve_vimshottari_policy(policy)
    year_basis      = year_basis      if year_basis      is not None else pol.year.year_basis
    ayanamsa_system = ayanamsa_system if ayanamsa_system is not None else pol.ayanamsa.ayanamsa_system

    if not math.isfinite(current_jd):
        raise ValueError("current_jd must be finite")
    if current_jd < natal_jd:
        raise ValueError("current_jd must not be earlier than natal_jd")
    year_days = _resolve_vimshottari_year_days(year_basis)
    if current_jd > natal_jd + VIMSHOTTARI_TOTAL * year_days:
        raise ValueError("current_jd is beyond the Vimshottari cycle cap")

    all_periods = vimshottari(
        moon_tropical_lon,
        natal_jd,
        levels=levels,
        ayanamsa_system=ayanamsa_system,
        year_basis=year_basis,
        policy=policy,
    )

    active: list[DashaPeriod] = []

    # Walk down through successive levels, finding the active period at each
    candidates: list[DashaPeriod] = all_periods
    while candidates:
        found: DashaPeriod | None = None
        for period in candidates:
            if period.start_jd <= current_jd < period.end_jd:
                found = period
                break
        if found is None:
            break
        active.append(found)
        candidates = found.sub

    if not active:
        raise ValueError("current_jd falls outside the generated Vimshottari sequence")

    return active


def dasha_balance(
    moon_tropical_lon: float,
    natal_jd: float,
    ayanamsa_system: str | None = None,
    *,
    year_basis: str | None = None,
    policy: VimshottariComputationPolicy | None = None,
) -> tuple[str, float]:
    """
    Return the Mahadasha lord at birth and the remaining years in that period.

    This is the "dasha balance" shown in traditional Jyotish charts — it
    tells how many years remain of the first Mahadasha at the moment of birth.

    Parameters
    ----------
    moon_tropical_lon : Moon's tropical ecliptic longitude at birth
    natal_jd          : Julian Day of birth (UT)
    ayanamsa_system   : ayanamsa for Moon's nakshatra; None uses policy default
    year_basis        : accepted for API symmetry and validated, but does not
                        affect the return value — the balance is always expressed
                        in Vimshottari years (nakshatra-proportional), not
                        calendar days
    policy            : VimshottariComputationPolicy governing doctrinal defaults

    Returns
    -------
    (lord_name, remaining_vimshottari_years_at_birth)
        The balance in Vimshottari years (where the full Mahadasha sum is 120).
        To convert to Julian days, multiply by the year_days for your basis.

    Raises
    ------
    ValueError
        If moon_tropical_lon or natal_jd is not finite, or year_basis is invalid.
    """
    pol = _resolve_vimshottari_policy(policy)
    year_basis      = year_basis      if year_basis      is not None else pol.year.year_basis
    ayanamsa_system = ayanamsa_system if ayanamsa_system is not None else pol.ayanamsa.ayanamsa_system

    if not math.isfinite(moon_tropical_lon):
        raise ValueError("moon_tropical_lon must be finite")
    if not math.isfinite(natal_jd):
        raise ValueError("natal_jd must be finite")
    # Validate year_basis; year_days is not used here because the return value
    # of dasha_balance is in Vimshottari years (nakshatra-proportional), not
    # calendar days.  The check is still necessary to surface invalid policy inputs.
    _ = _resolve_vimshottari_year_days(year_basis)

    sid_lon = tropical_to_sidereal(moon_tropical_lon, natal_jd, system=ayanamsa_system)

    nak_idx = int(sid_lon / NAKSHATRA_SPAN) % 27
    degrees_elapsed = sid_lon - nak_idx * NAKSHATRA_SPAN
    fraction_elapsed = degrees_elapsed / NAKSHATRA_SPAN

    lord = NAKSHATRA_LORDS[nak_idx]
    total_years = float(VIMSHOTTARI_YEARS[lord])
    remaining = total_years * (1.0 - fraction_elapsed)

    return lord, remaining
