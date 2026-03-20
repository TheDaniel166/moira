"""
Moira — dasha.py
The Dasha Engine: governs Vimshottari Dasha period computation for Vedic
predictive astrology.

Boundary: owns Vimshottari sequence arithmetic, nakshatra-based period
initialisation, recursive sub-period generation, and active-period lookup.
Delegates sidereal longitude conversion and nakshatra lord tables to sidereal.
Delegates Julian Day arithmetic to julian. Does NOT own natal chart construction
or ephemeris state.

Public surface:
    VIMSHOTTARI_YEARS, VIMSHOTTARI_SEQUENCE, VIMSHOTTARI_TOTAL,
    DashaPeriod,
    vimshottari, current_dasha, dasha_balance

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
            - level is in [1, 4]
            - end_jd > start_jd
            - sub is empty for leaf periods (level == 4 or levels not requested)
        Behavioral invariants:
            - years property is always (end_jd - start_jd) / JULIAN_YEAR

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
    level:     int       # 1=Mahadasha, 2=Antardasha, 3=Pratyantardasha, 4=Sookshma
    planet:    str
    start_jd:  float
    end_jd:    float
    sub:       list["DashaPeriod"] = field(default_factory=list, repr=False)

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
        return (self.end_jd - self.start_jd) / JULIAN_YEAR

    def __repr__(self) -> str:
        indent = "  " * (self.level - 1)
        return (f"{indent}L{self.level} {self.planet:<10} "
                f"{self.start_calendar.date_string()} → "
                f"{self.end_calendar.date_string()} "
                f"({self.years:.2f}y)")


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
    start_idx = VIMSHOTTARI_SEQUENCE.index(lord)
    return VIMSHOTTARI_SEQUENCE[start_idx:] + VIMSHOTTARI_SEQUENCE[:start_idx]


def _build_sub_periods(
    period: DashaPeriod,
    levels: int,
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
    period : the parent DashaPeriod whose .sub list will be filled
    levels : how many more levels to generate below this one
             (0 means stop — do not recurse further)
    """
    if levels <= 0:
        return

    sub_sequence = _sequence_from(period.planet)
    current_jd = period.start_jd

    for sub_planet in sub_sequence:
        sub_years = (VIMSHOTTARI_YEARS[sub_planet] / VIMSHOTTARI_TOTAL) * period.years
        sub_end_jd = current_jd + sub_years * JULIAN_YEAR

        child = DashaPeriod(
            level=period.level + 1,
            planet=sub_planet,
            start_jd=current_jd,
            end_jd=sub_end_jd,
        )

        # Recurse for deeper levels
        _build_sub_periods(child, levels - 1)

        period.sub.append(child)
        current_jd = sub_end_jd


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def vimshottari(
    moon_tropical_lon: float,
    natal_jd: float,
    levels: int = 2,
    ayanamsa_system: str = Ayanamsa.LAHIRI,
) -> list[DashaPeriod]:
    """
    Compute the full Vimshottari Dasha sequence from birth.

    Parameters
    ----------
    moon_tropical_lon : Moon's tropical ecliptic longitude at birth
    natal_jd          : Julian Day of birth (UT)
    levels            : number of levels to generate (1=Mahadasha only,
                        2=+Antardasha, 3=+Pratyantardasha, 4=+Sookshma)
    ayanamsa_system   : ayanamsa for Moon's nakshatra (default: Lahiri)

    Returns
    -------
    List of DashaPeriod at level 1 (each with .sub populated to requested depth)
    """
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

    # 6. Generate all Mahadashas covering the full 120-year cycle
    #    (The sequence naturally runs one full cycle of all 9 planets, but in
    #    practice charts may be truncated; we generate the complete 120-year span.)
    mahadashas: list[DashaPeriod] = []
    current_jd = natal_jd

    for i, lord in enumerate(maha_sequence):
        if i == 0:
            # First period: only the remaining portion is in the future
            duration_years = remaining_first
        else:
            duration_years = float(VIMSHOTTARI_YEARS[lord])

        end_jd = current_jd + duration_years * JULIAN_YEAR

        maha = DashaPeriod(
            level=1,
            planet=lord,
            start_jd=current_jd,
            end_jd=end_jd,
        )

        # Populate sub-periods for the requested depth
        _build_sub_periods(maha, levels - 1)

        mahadashas.append(maha)
        current_jd = end_jd

    return mahadashas


def current_dasha(
    moon_tropical_lon: float,
    natal_jd: float,
    current_jd: float,
    ayanamsa_system: str = Ayanamsa.LAHIRI,
) -> list[DashaPeriod]:
    """
    Return the active dasha periods at current_jd.

    Returns a list of [Mahadasha, Antardasha, Pratyantardasha, Sookshma]
    — up to 4 levels — each being the active period at current_jd.

    Parameters
    ----------
    moon_tropical_lon : Moon's tropical ecliptic longitude at birth
    natal_jd          : Julian Day of birth (UT)
    current_jd        : Julian Day of the query moment
    ayanamsa_system   : ayanamsa for Moon's nakshatra (default: Lahiri)

    Returns
    -------
    List of up to 4 DashaPeriod objects (one per active level).
    """
    all_periods = vimshottari(
        moon_tropical_lon,
        natal_jd,
        levels=4,
        ayanamsa_system=ayanamsa_system,
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

    return active


def dasha_balance(
    moon_tropical_lon: float,
    natal_jd: float,
    ayanamsa_system: str = Ayanamsa.LAHIRI,
) -> tuple[str, float]:
    """
    Return the Mahadasha lord at birth and the remaining years in that period.

    This is the "dasha balance" shown in traditional Jyotish charts — it
    tells how many years remain of the first Mahadasha at the moment of birth.

    Parameters
    ----------
    moon_tropical_lon : Moon's tropical ecliptic longitude at birth
    natal_jd          : Julian Day of birth (UT)
    ayanamsa_system   : ayanamsa for Moon's nakshatra (default: Lahiri)

    Returns
    -------
    (lord_name, remaining_years_at_birth)
    """
    sid_lon = tropical_to_sidereal(moon_tropical_lon, natal_jd, system=ayanamsa_system)

    nak_idx = int(sid_lon / NAKSHATRA_SPAN) % 27
    degrees_elapsed = sid_lon - nak_idx * NAKSHATRA_SPAN
    fraction_elapsed = degrees_elapsed / NAKSHATRA_SPAN

    lord = NAKSHATRA_LORDS[nak_idx]
    total_years = float(VIMSHOTTARI_YEARS[lord])
    remaining = total_years * (1.0 - fraction_elapsed)

    return lord, remaining
