from __future__ import annotations

"""
Moira — lord_of_the_orb.py
The Lord of the Orb Engine: governs computation of Abu Ma'shar's Lord of the
Orb annual time-lord technique.

The Lord of the Orb is determined by the planetary hour at the moment of birth.
That planet becomes the Lord of the Orb for year 1 of life, governing the
significations of the 1st house. Each subsequent year the next planet in the
Chaldean order becomes Lord of the Orb for the next house, producing two
independent cycles: the 7-planet Chaldean sequence and the 12-house sequence.

Boundary declaration
--------------------
Owns: the Lord of the Orb catalogue, Chaldean sequence arithmetic, cycle-
      variant logic (CONTINUOUS_LOOP and SINGLE_CYCLE), house signification
      mapping, result vessels, condition profiling, and aggregate intelligence.
Delegates: birth planetary hour determination to moira.planetary_hours.
           Does NOT compute the natal chart, solar return chart, or the birth
           planetary hour. The caller supplies birth_planet (the planet ruling
           the birth hour) as a plain string matching Body constants.

Doctrine basis
--------------
Abu Ma'shar, Kitāb taḥāwil sinī al-mawālīd; Diego de Torres, Opus
Astrologicum (Salamanca, late 1480s–1490s). Confirmed cycle variants from:
Benjamin N. Dykes, Persian Nativities IV (Cazimi Press, 2019), pages 126–128
(Abu Ma'shar — ambiguous); Anthony Louis blog, 2021 (Torres — continuous loop
confirmed with Venus worked example).

Default: CONTINUOUS_LOOP (Torres, Giuntini; the better-attested variant).
SINGLE_CYCLE is admitted as an alternative reading of Abu Ma'shar.

Ranking in Abu Ma'shar's annual hierarchy: 6th of 8 annual indicators.

Import-time side effects: None

External dependency assumptions
--------------------------------
- No third-party packages; stdlib only.
- birth_planet must be one of the seven Chaldean planets (Saturn, Jupiter,
  Mars, Sun, Venus, Mercury, Moon). Caller derives this from
  moira.planetary_hours.PlanetaryHour.ruler for the birth JD.

Public surface
--------------
CHALDEAN_ORDER              — ordered tuple of 7 classical planet names
HOUSE_SIGNIFICATIONS        — dict mapping house number (1–12) to a brief
                              traditional signification string
LordOfOrbCycleKind          — CONTINUOUS_LOOP or SINGLE_CYCLE
LordOfOrbPolicy             — doctrinal configuration surface
DEFAULT_LORD_OF_ORB_POLICY
LordOfOrbPeriod             — primary result vessel (year, planet, house)
LordOfOrbSequence           — ordered sequence of periods as a relational group
LordOfOrbConditionProfile   — per-period condition integrating position and
                              house signification
LordOfOrbAggregate          — chart-wide aggregate intelligence
lord_of_orb()               — main computation engine
current_lord_of_orb()       — active period for a given year of life
validate_lord_of_orb_output() — validation entry point
"""

from dataclasses import dataclass, field
from enum import StrEnum


# ---------------------------------------------------------------------------
# Phase 12 — Public API Curation
# ---------------------------------------------------------------------------

__all__ = [
    # Constants
    "CHALDEAN_ORDER",
    "HOUSE_SIGNIFICATIONS",
    # Classification
    "LordOfOrbCycleKind",
    # Policy
    "LordOfOrbPolicy",
    "DEFAULT_LORD_OF_ORB_POLICY",
    # Truth-preservation vessel
    "LordOfOrbPeriod",
    # Relational vessel
    "LordOfOrbSequence",
    # Condition vessel
    "LordOfOrbConditionProfile",
    # Aggregate vessel
    "LordOfOrbAggregate",
    # Computation functions
    "lord_of_orb",
    "current_lord_of_orb",
    # Validation
    "validate_lord_of_orb_output",
]


# ---------------------------------------------------------------------------
# Internal constants
# ---------------------------------------------------------------------------

#: Chaldean order of the seven classical planets, slowest to fastest.
#: Index 0 = Saturn, Index 6 = Moon. Matches planetary_hours._CHALDEAN.
CHALDEAN_ORDER: tuple[str, ...] = (
    "Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon",
)

_CHALDEAN_INDEX: dict[str, int] = {p: i for i, p in enumerate(CHALDEAN_ORDER)}

#: Traditional house significations used for Lord of the Orb domain labelling.
#: Abbreviated to the core domain each house governs in this annual context.
HOUSE_SIGNIFICATIONS: dict[int, str] = {
    1:  "Life, body, disposition",
    2:  "Wealth, substance, livelihood",
    3:  "Siblings, communications, short travel",
    4:  "Parents, home, foundations, end of matter",
    5:  "Children, pleasures, creativity",
    6:  "Health, illness, service, subordinates",
    7:  "Marriage, partnerships, open enemies",
    8:  "Death, transformation, others' resources",
    9:  "Religion, long travel, philosophy, dreams",
    10: "Career, reputation, authority, public life",
    11: "Friends, hopes, benefactors",
    12: "Hidden enemies, imprisonment, sorrow, self-undoing",
}

_VALID_PLANETS: frozenset[str] = frozenset(CHALDEAN_ORDER)


# ---------------------------------------------------------------------------
# Phase 2 — Classification namespaces
# ---------------------------------------------------------------------------

class LordOfOrbCycleKind(StrEnum):
    """
    Governs how the Chaldean planetary sequence and the 12-house cycle relate
    across the native's lifetime.

    CONTINUOUS_LOOP
        The 7-planet Chaldean sequence and the 12-house cycle are independent
        modular counters. The house cycle resets every 12 years; the Chaldean
        sequence advances independently every 7 years. The full combined
        pattern repeats at LCM(7, 12) = 84 years.

        This is the better-attested variant, confirmed in Diego de Torres's
        worked example (Venus as birth planet → years 1, 8, 15, 22, 29, 36
        all governed by Venus) and in Giuntini's tables to age 60.

    SINGLE_CYCLE
        Both the Chaldean sequence and the house cycle reset together every
        12 years. The planet for Year 1 and Year 13 are always identical.
        This is a defensible reading of Abu Ma'shar's Arabic text but is not
        confirmed in any worked example.

    Default: CONTINUOUS_LOOP.
    """
    CONTINUOUS_LOOP = "continuous_loop"
    SINGLE_CYCLE    = "single_cycle"


# ---------------------------------------------------------------------------
# Phase 4 — Doctrine / Policy Surface
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class LordOfOrbPolicy:
    """
    Doctrinal configuration surface for the Lord of the Orb engine.

    All fields are immutable once constructed.

    cycle_kind
        Which cycle variant to apply. Default: CONTINUOUS_LOOP.
        SINGLE_CYCLE is also admitted as an alternative reading of Abu
        Ma'shar.
    """
    cycle_kind: LordOfOrbCycleKind = LordOfOrbCycleKind.CONTINUOUS_LOOP


DEFAULT_LORD_OF_ORB_POLICY: LordOfOrbPolicy = LordOfOrbPolicy()


# ---------------------------------------------------------------------------
# Phase 1 — Truth Preservation
# ---------------------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class LordOfOrbPeriod:
    """
    RITE: The Orb Vessel — the planet governing a single year of life as Lord
    of the Orb, carrying its year number, house assignment, Chaldean index,
    and cycle kind.

    THEOREM: Primary result vessel for the Lord of the Orb engine. Preserves
    all computational truth (Phase 1) and provides typed classification and
    inspectability properties (Phases 2–3).

    RITE OF PURPOSE:
        LordOfOrbPeriod is the atomic output unit of lord_of_orb(). Without
        it, callers would receive bare (year, planet, house) tuples with no
        inspectability, no cycle context, and no house signification. It
        exists to give every consumer a complete, named record for each year.

    LAW OF OPERATION:
        Responsibilities:
            - Store year, planet, house, chaldean_index, cycle_kind, and
              house_signification.
        Non-responsibilities:
            - Does not compute the period (delegated to lord_of_orb()).
            - Does not look up the planet's natal or solar return condition.
            - Does not determine the birth planetary hour.
        Dependencies:
            - Populated by lord_of_orb().
        Structural invariants:
            - year >= 1.
            - house is in [1, 12].
            - chaldean_index is in [0, 6].
            - planet is one of the seven Chaldean planet strings.

    Canon: Abu Ma'shar, Kitāb taḥāwil sinī al-mawālīd; Diego de Torres,
           Opus Astrologicum (Salamanca, late 1480s–1490s).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.lord_of_the_orb.LordOfOrbPeriod",
        "risk": "low",
        "api": {
            "frozen": [
                "year", "planet", "house", "chaldean_index",
                "cycle_kind", "house_signification"
            ],
            "internal": []
        },
        "state": {"mutable": false},
        "effects": {"io": [], "signals_emitted": [], "mutation": "none"},
        "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
        "failures": {"policy": "caller ensures valid birth_planet and year >= 1"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    year:               int
    planet:             str
    house:              int
    chaldean_index:     int
    cycle_kind:         LordOfOrbCycleKind
    house_signification: str

    def __post_init__(self) -> None:
        if self.year < 1:
            raise ValueError(
                f"LordOfOrbPeriod invariant: year must be >= 1, got {self.year}"
            )
        if self.house not in range(1, 13):
            raise ValueError(
                f"LordOfOrbPeriod invariant: house must be in [1, 12], got {self.house}"
            )
        if self.chaldean_index not in range(7):
            raise ValueError(
                f"LordOfOrbPeriod invariant: chaldean_index must be in [0, 6], "
                f"got {self.chaldean_index}"
            )
        if self.planet not in _VALID_PLANETS:
            raise ValueError(
                f"LordOfOrbPeriod invariant: planet must be one of the seven "
                f"Chaldean planets, got {self.planet!r}"
            )
        if CHALDEAN_ORDER[self.chaldean_index] != self.planet:
            raise ValueError(
                f"LordOfOrbPeriod invariant: chaldean_index {self.chaldean_index} "
                f"maps to {CHALDEAN_ORDER[self.chaldean_index]!r}, not {self.planet!r}"
            )

    # -----------------------------------------------------------------------
    # Phase 3 — Inspectability
    # -----------------------------------------------------------------------

    @property
    def house_zero_indexed(self) -> int:
        """House number as a 0-based index (0–11)."""
        return self.house - 1

    @property
    def is_year_one_planet(self) -> bool:
        """
        True when this period's Chaldean index position modulo 7 matches
        year 1. This is always True for year 1 itself and recurs every 7
        years in CONTINUOUS_LOOP.
        """
        return (self.year - 1) % 7 == 0

    @property
    def is_house_cycle_start(self) -> bool:
        """True when this period governs house 1 (start of a 12-year house cycle)."""
        return self.house == 1

    @property
    def years_until_next_same_planet(self) -> int:
        """Years until this planet next appears as Lord of the Orb (always 7)."""
        return 7

    def __repr__(self) -> str:
        return (
            f"LordOfOrbPeriod(year={self.year}, planet={self.planet!r}, "
            f"house={self.house}, cycle={self.cycle_kind.value})"
        )


# ---------------------------------------------------------------------------
# Phase 5 — Relational Formalization
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class LordOfOrbSequence:
    """
    RITE: The Orb Sequence — the complete sequence of Lord of the Orb periods
    for a native's life, carrying the ordered periods, birth-hour planet,
    cycle kind, and relational inspectability over the full sequence.

    THEOREM: Relational vessel grouping multiple LordOfOrbPeriod results with
    their shared birth context. Provides inspectability over the full sequence
    as a structured whole.

    Structural invariants:
        - periods is non-empty and sorted by year ascending.
        - all periods share the same cycle_kind.
        - all periods share the same birth_planet as year 1's planet.
        - year values are consecutive starting from 1.
    """
    birth_planet: str
    periods:      list[LordOfOrbPeriod]
    cycle_kind:   LordOfOrbCycleKind

    def __post_init__(self) -> None:
        if not self.periods:
            raise ValueError("LordOfOrbSequence invariant: periods must be non-empty")
        if self.birth_planet not in _VALID_PLANETS:
            raise ValueError(
                f"LordOfOrbSequence invariant: birth_planet must be a Chaldean "
                f"planet, got {self.birth_planet!r}"
            )
        if self.periods[0].planet != self.birth_planet:
            raise ValueError(
                f"LordOfOrbSequence invariant: year 1 planet must equal "
                f"birth_planet {self.birth_planet!r}, got {self.periods[0].planet!r}"
            )
        for i, period in enumerate(self.periods):
            if period.year != i + 1:
                raise ValueError(
                    f"LordOfOrbSequence invariant: periods must be consecutive "
                    f"from year 1; expected year {i + 1}, got {period.year}"
                )
            if period.cycle_kind is not self.cycle_kind:
                raise ValueError(
                    f"LordOfOrbSequence invariant: all periods must share "
                    f"cycle_kind {self.cycle_kind!r}"
                )

    # -----------------------------------------------------------------------
    # Phase 6 — Relational Hardening / Inspectability
    # -----------------------------------------------------------------------

    def get(self, year: int) -> LordOfOrbPeriod:
        """
        Return the period for the given year of life.

        Raises KeyError if year is not in the sequence.
        """
        if year < 1 or year > len(self.periods):
            raise KeyError(
                f"Year {year} not in sequence (covers years 1–{len(self.periods)})"
            )
        return self.periods[year - 1]

    def years_for_planet(self, planet: str) -> list[int]:
        """Return the years of life in which the given planet is Lord of the Orb."""
        if planet not in _VALID_PLANETS:
            raise ValueError(f"Not a Chaldean planet: {planet!r}")
        return [p.year for p in self.periods if p.planet == planet]

    def years_for_house(self, house: int) -> list[int]:
        """Return the years of life governed by the given house."""
        if house not in range(1, 13):
            raise ValueError(f"house must be in [1, 12], got {house}")
        return [p.year for p in self.periods if p.house == house]

    @property
    def span(self) -> int:
        """Number of years in the sequence."""
        return len(self.periods)

    @property
    def planets_in_sequence(self) -> list[str]:
        """All planets that appear in the sequence, in order of first appearance."""
        seen: list[str] = []
        for p in self.periods:
            if p.planet not in seen:
                seen.append(p.planet)
        return seen

    @property
    def is_full_84_year_cycle(self) -> bool:
        """True when the sequence covers exactly 84 years (one complete combined cycle)."""
        return self.span == 84

    def __repr__(self) -> str:
        return (
            f"LordOfOrbSequence(birth_planet={self.birth_planet!r}, "
            f"span={self.span}, cycle={self.cycle_kind.value})"
        )


# ---------------------------------------------------------------------------
# Phase 7 — Integrated Local Condition
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class LordOfOrbConditionProfile:
    """
    Integrated per-period condition profile for a single Lord of the Orb year.

    Combines the period's planet and house with the house signification,
    the Abu Ma'shar annual hierarchy position, and cycle position context.

    period
        The LordOfOrbPeriod this profile describes.
    house_signification
        Traditional domain of the house governing this year.
    hierarchy_rank
        Rank of the Lord of the Orb in Abu Ma'shar's eight-indicator annual
        hierarchy. Always 6 in the Abu Ma'shar system.
    house_cycle_number
        Which 12-year house cycle this year falls in (1-based).
    planet_cycle_number
        Which 7-year Chaldean cycle this year falls in (1-based).
        In CONTINUOUS_LOOP these two cycles are independent.
    """
    period:              LordOfOrbPeriod
    house_signification: str
    hierarchy_rank:      int
    house_cycle_number:  int
    planet_cycle_number: int

    def __post_init__(self) -> None:
        if self.hierarchy_rank != 6:
            raise ValueError(
                f"LordOfOrbConditionProfile invariant: hierarchy_rank must be 6 "
                f"(Abu Ma'shar), got {self.hierarchy_rank}"
            )
        expected_house_cycle = ((self.period.year - 1) // 12) + 1
        if self.house_cycle_number != expected_house_cycle:
            raise ValueError(
                f"LordOfOrbConditionProfile invariant: house_cycle_number must be "
                f"{expected_house_cycle}, got {self.house_cycle_number}"
            )
        expected_planet_cycle = ((self.period.year - 1) // 7) + 1
        if self.planet_cycle_number != expected_planet_cycle:
            raise ValueError(
                f"LordOfOrbConditionProfile invariant: planet_cycle_number must be "
                f"{expected_planet_cycle}, got {self.planet_cycle_number}"
            )

    @property
    def is_cycle_coincidence(self) -> bool:
        """
        True when a house cycle and a planet cycle both start in this year
        (years 1, 85, 169, …). In CONTINUOUS_LOOP these coincidences occur
        every 84 years (LCM of 7 and 12).
        """
        return self.period.house == 1 and (self.period.year - 1) % 7 == 0

    @property
    def is_benefic_planet(self) -> bool:
        """True for Jupiter and Venus (the two benefics in classical doctrine)."""
        return self.period.planet in {"Jupiter", "Venus"}

    @property
    def is_malefic_planet(self) -> bool:
        """True for Saturn and Mars (the two malefics in classical doctrine)."""
        return self.period.planet in {"Saturn", "Mars"}


# ---------------------------------------------------------------------------
# Phase 8 — Aggregate Intelligence
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class LordOfOrbAggregate:
    """
    Chart-wide aggregate intelligence built from the Lord of the Orb sequence
    and its per-period condition profiles.

    sequence
        The complete LordOfOrbSequence for the chart.
    condition_profiles
        Per-period condition profiles, one per year, in year order.
    policy
        The doctrinal policy used for this computation.

    Properties provide cross-period intelligence: which years are governed by
    benefics or malefics, how many times each planet appears, etc.
    """
    sequence:           LordOfOrbSequence
    condition_profiles: list[LordOfOrbConditionProfile]
    policy:             LordOfOrbPolicy

    def __post_init__(self) -> None:
        if len(self.condition_profiles) != len(self.sequence.periods):
            raise ValueError(
                f"LordOfOrbAggregate invariant: condition_profiles count "
                f"({len(self.condition_profiles)}) must match periods count "
                f"({len(self.sequence.periods)})"
            )

    def get_profile(self, year: int) -> LordOfOrbConditionProfile:
        """Return the condition profile for the given year of life."""
        if year < 1 or year > len(self.condition_profiles):
            raise KeyError(
                f"Year {year} not in aggregate (covers years 1–"
                f"{len(self.condition_profiles)})"
            )
        return self.condition_profiles[year - 1]

    @property
    def benefic_years(self) -> list[int]:
        """Years governed by Jupiter or Venus."""
        return [cp.period.year for cp in self.condition_profiles if cp.is_benefic_planet]

    @property
    def malefic_years(self) -> list[int]:
        """Years governed by Saturn or Mars."""
        return [cp.period.year for cp in self.condition_profiles if cp.is_malefic_planet]

    @property
    def planet_year_counts(self) -> dict[str, int]:
        """Number of years each planet governs in the sequence, in Chaldean order."""
        counts: dict[str, int] = {p: 0 for p in CHALDEAN_ORDER}
        for cp in self.condition_profiles:
            counts[cp.period.planet] += 1
        return counts

    @property
    def cycle_coincidence_years(self) -> list[int]:
        """Years where a house cycle and a Chaldean cycle both begin (every 84 years)."""
        return [cp.period.year for cp in self.condition_profiles if cp.is_cycle_coincidence]

    def __repr__(self) -> str:
        return (
            f"LordOfOrbAggregate(birth_planet={self.sequence.birth_planet!r}, "
            f"span={self.sequence.span}, cycle={self.policy.cycle_kind.value})"
        )


# ---------------------------------------------------------------------------
# Phase 1 / Engine — Core Computation
# ---------------------------------------------------------------------------

def lord_of_orb(
    birth_planet: str,
    years: int,
    policy: LordOfOrbPolicy = DEFAULT_LORD_OF_ORB_POLICY,
) -> LordOfOrbAggregate:
    """
    Compute the Lord of the Orb for a native's life up to the given number
    of years.

    Parameters
    ----------
    birth_planet : str
        The planet ruling the birth planetary hour. Must be one of the seven
        Chaldean planets: 'Saturn', 'Jupiter', 'Mars', 'Sun', 'Venus',
        'Mercury', 'Moon'. Derive from moira.planetary_hours.PlanetaryHour.ruler
        for the birth JD.
    years : int
        Number of years of life to compute. Must be >= 1. To cover one full
        combined cycle, pass 84.
    policy : LordOfOrbPolicy
        Doctrinal configuration. Defaults to DEFAULT_LORD_OF_ORB_POLICY
        (CONTINUOUS_LOOP).

    Returns
    -------
    LordOfOrbAggregate
        Complete result with all periods, condition profiles, and aggregate
        intelligence.

    Raises
    ------
    ValueError
        If birth_planet is not a Chaldean planet, or years < 1.

    Notes
    -----
    Cycle arithmetic:

    CONTINUOUS_LOOP (default, Torres/Giuntini):
        planet_index = (birth_index + year - 1) % 7
        house        = ((year - 1) % 12) + 1
        Full pattern repeats at year 85 (LCM(7,12) + 1).

    SINGLE_CYCLE (Abu Ma'shar ambiguous reading):
        cycle_position = (year - 1) % 12
        planet_index   = (birth_index + cycle_position) % 7
        house          = cycle_position + 1
        Planet resets with house cycle every 12 years.

    Torres's verification: with Venus as birth planet (CONTINUOUS_LOOP),
    years 1, 8, 15, 22, 29, 36, 43, 50, 57, 64, 71, 78 all return Venus.
    """
    _validate_lord_of_orb_inputs(birth_planet, years)

    birth_index = _CHALDEAN_INDEX[birth_planet]
    cycle_kind  = policy.cycle_kind
    periods: list[LordOfOrbPeriod] = []

    for year in range(1, years + 1):
        if cycle_kind is LordOfOrbCycleKind.CONTINUOUS_LOOP:
            planet_index   = (birth_index + year - 1) % 7
            house          = ((year - 1) % 12) + 1
        else:  # SINGLE_CYCLE
            cycle_position = (year - 1) % 12
            planet_index   = (birth_index + cycle_position) % 7
            house          = cycle_position + 1

        planet = CHALDEAN_ORDER[planet_index]

        periods.append(LordOfOrbPeriod(
            year                = year,
            planet              = planet,
            house               = house,
            chaldean_index      = planet_index,
            cycle_kind          = cycle_kind,
            house_signification = HOUSE_SIGNIFICATIONS[house],
        ))

    sequence = LordOfOrbSequence(
        birth_planet = birth_planet,
        periods      = periods,
        cycle_kind   = cycle_kind,
    )

    profiles: list[LordOfOrbConditionProfile] = []
    for period in periods:
        profiles.append(LordOfOrbConditionProfile(
            period              = period,
            house_signification = HOUSE_SIGNIFICATIONS[period.house],
            hierarchy_rank      = 6,
            house_cycle_number  = ((period.year - 1) // 12) + 1,
            planet_cycle_number = ((period.year - 1) // 7) + 1,
        ))

    return LordOfOrbAggregate(
        sequence           = sequence,
        condition_profiles = profiles,
        policy             = policy,
    )


def current_lord_of_orb(
    birth_planet: str,
    age: int,
    policy: LordOfOrbPolicy = DEFAULT_LORD_OF_ORB_POLICY,
) -> LordOfOrbPeriod:
    """
    Return the Lord of the Orb period for a native of the given age.

    Parameters
    ----------
    birth_planet : str
        The planet ruling the birth planetary hour.
    age : int
        The native's current age in completed years (0 = first year of life,
        treated as year 1).
    policy : LordOfOrbPolicy
        Doctrinal configuration.

    Returns
    -------
    LordOfOrbPeriod
        The active Lord of the Orb period for the given age.

    Notes
    -----
    Age 0 (first year of life) maps to year 1. Age N maps to year N + 1.
    """
    year = max(1, age + 1)
    aggregate = lord_of_orb(birth_planet, year, policy)
    return aggregate.sequence.get(year)


# ---------------------------------------------------------------------------
# Phase 10 — Full-Subsystem Hardening
# ---------------------------------------------------------------------------

def validate_lord_of_orb_output(aggregate: LordOfOrbAggregate) -> list[str]:
    """
    Validate the internal consistency of a LordOfOrbAggregate result.

    Returns a list of failure strings. An empty list confirms full consistency.

    Checks:
    1. Year 1 planet matches birth_planet.
    2. All years are consecutive from 1.
    3. All cycle_kind fields match the aggregate cycle_kind.
    4. All houses are in [1, 12].
    5. All chaldean_index values are in [0, 6].
    6. All chaldean_index values match the planet name.
    7. CONTINUOUS_LOOP: planet recurs every 7 years.
    8. CONTINUOUS_LOOP: house recurs every 12 years.
    9. SINGLE_CYCLE: planet for year N equals planet for year N+12.
    10. Condition profile count matches period count.
    11. All hierarchy_rank values are 6.
    12. Torres verification (CONTINUOUS_LOOP only): if birth_planet is Venus
        and span >= 36, years 1, 8, 15, 22, 29, 36 must all be Venus.
    """
    failures: list[str] = []
    periods  = aggregate.sequence.periods
    cycle    = aggregate.policy.cycle_kind

    # Check 1 — year 1 planet
    if periods and periods[0].planet != aggregate.sequence.birth_planet:
        failures.append(
            f"Year 1 planet {periods[0].planet!r} does not match "
            f"birth_planet {aggregate.sequence.birth_planet!r}"
        )

    # Check 2 — consecutive years
    for i, p in enumerate(periods):
        if p.year != i + 1:
            failures.append(f"Period {i}: expected year {i + 1}, got {p.year}")

    # Check 3 — cycle_kind consistency
    for p in periods:
        if p.cycle_kind is not cycle:
            failures.append(
                f"Year {p.year}: cycle_kind {p.cycle_kind!r} != {cycle!r}"
            )

    # Checks 4 & 5 — house and index ranges
    for p in periods:
        if p.house not in range(1, 13):
            failures.append(f"Year {p.year}: house {p.house} not in [1, 12]")
        if p.chaldean_index not in range(7):
            failures.append(
                f"Year {p.year}: chaldean_index {p.chaldean_index} not in [0, 6]"
            )

    # Check 6 — index/planet consistency
    for p in periods:
        if p.chaldean_index in range(7):
            expected = CHALDEAN_ORDER[p.chaldean_index]
            if p.planet != expected:
                failures.append(
                    f"Year {p.year}: chaldean_index {p.chaldean_index} maps to "
                    f"{expected!r} but planet is {p.planet!r}"
                )

    if cycle is LordOfOrbCycleKind.CONTINUOUS_LOOP:
        # Check 7 — planet recurs every 7 years
        for p in periods:
            seven_ahead = p.year + 7
            if seven_ahead <= len(periods):
                p7 = periods[seven_ahead - 1]
                if p.planet != p7.planet:
                    failures.append(
                        f"CONTINUOUS_LOOP: year {p.year} planet {p.planet!r} "
                        f"!= year {seven_ahead} planet {p7.planet!r} (should repeat every 7)"
                    )

        # Check 8 — house recurs every 12 years
        for p in periods:
            twelve_ahead = p.year + 12
            if twelve_ahead <= len(periods):
                p12 = periods[twelve_ahead - 1]
                if p.house != p12.house:
                    failures.append(
                        f"CONTINUOUS_LOOP: year {p.year} house {p.house} "
                        f"!= year {twelve_ahead} house {p12.house} (should repeat every 12)"
                    )

    if cycle is LordOfOrbCycleKind.SINGLE_CYCLE:
        # Check 9 — planet for year N equals planet for year N+12
        for p in periods:
            twelve_ahead = p.year + 12
            if twelve_ahead <= len(periods):
                p12 = periods[twelve_ahead - 1]
                if p.planet != p12.planet:
                    failures.append(
                        f"SINGLE_CYCLE: year {p.year} planet {p.planet!r} "
                        f"!= year {twelve_ahead} planet {p12.planet!r} (should repeat every 12)"
                    )

    # Check 10 — profile count
    if len(aggregate.condition_profiles) != len(periods):
        failures.append(
            f"condition_profiles count {len(aggregate.condition_profiles)} "
            f"!= periods count {len(periods)}"
        )

    # Check 11 — hierarchy rank
    for cp in aggregate.condition_profiles:
        if cp.hierarchy_rank != 6:
            failures.append(
                f"Year {cp.period.year}: hierarchy_rank must be 6, "
                f"got {cp.hierarchy_rank}"
            )

    # Check 12 — Torres verification
    if (
        cycle is LordOfOrbCycleKind.CONTINUOUS_LOOP
        and aggregate.sequence.birth_planet == "Venus"
        and aggregate.sequence.span >= 36
    ):
        for expected_year in (1, 8, 15, 22, 29, 36):
            p = periods[expected_year - 1]
            if p.planet != "Venus":
                failures.append(
                    f"Torres verification: year {expected_year} should be Venus "
                    f"(birth planet = Venus, CONTINUOUS_LOOP), got {p.planet!r}"
                )

    return failures


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _validate_lord_of_orb_inputs(birth_planet: str, years: int) -> None:
    """Raise ValueError for malformed inputs at the system boundary."""
    if birth_planet not in _VALID_PLANETS:
        raise ValueError(
            f"birth_planet must be one of {list(CHALDEAN_ORDER)!r}, "
            f"got {birth_planet!r}"
        )
    if years < 1:
        raise ValueError(f"years must be >= 1, got {years}")
