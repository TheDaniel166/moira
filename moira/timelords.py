"""
Moira — timelords.py
The Timelord Engine: governs Firdaria and Zodiacal Releasing time-lord
period computation.

Boundary: owns Firdaria sequence arithmetic, Chaldean sub-period generation,
Zodiacal Releasing period recursion, and active-period lookup. Delegates
domicile ruler lookup to profections. Delegates Julian Day arithmetic to julian.
Does NOT own natal chart construction or ephemeris state.

Public surface:
    FIRDARIA_DIURNAL, FIRDARIA_NOCTURNAL, CHALDEAN_ORDER,
    MINOR_YEARS,
    FirdarPeriod, ReleasingPeriod,
    firdaria, current_firdaria,
    zodiacal_releasing, current_releasing

Import-time side effects: None

External dependency assumptions:
    - No third-party packages; stdlib only plus internal moira modules.
"""

from dataclasses import dataclass
from datetime import datetime

from .constants import SIGNS, sign_of
from .julian import CalendarDateTime, calendar_datetime_from_jd, datetime_from_jd
from .profections import DOMICILE_RULERS


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
    level:    int    # 1 = major period, 2 = sub-period
    planet:   str
    start_jd: float
    end_jd:   float
    years:    float

    @property
    def start_dt(self) -> datetime:
        """UTC datetime of the period start."""
        return datetime_from_jd(self.start_jd)

    @property
    def start_calendar(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(self.start_jd)

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
    def end_calendar(self) -> CalendarDateTime:
        return calendar_datetime_from_jd(self.end_jd)

    def __repr__(self) -> str:
        lvl = "Major" if self.level == 1 else "Sub  "
        return (
            f"FirdarPeriod(L{self.level} {lvl} | {self.planet:<11} "
            f"{self.years:.2f} yrs | "
            f"{self.start_calendar.date_string()} → "
            f"{self.end_calendar.date_string()})"
        )


# ---------------------------------------------------------------------------
# Firdaria calculation
# ---------------------------------------------------------------------------

def firdaria(natal_jd: float, is_day_chart: bool) -> list[FirdarPeriod]:
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

    Returns
    -------
    list[FirdarPeriod]
        All major periods, each immediately followed by their 7 sub-periods,
        in chronological order.
    """
    sequence = FIRDARIA_DIURNAL if is_day_chart else FIRDARIA_NOCTURNAL
    periods:  list[FirdarPeriod] = []
    cursor_jd = natal_jd

    for major_planet, major_years in sequence:
        major_start = cursor_jd
        major_end   = cursor_jd + major_years * _JULIAN_YEAR

        periods.append(FirdarPeriod(
            level=1,
            planet=major_planet,
            start_jd=major_start,
            end_jd=major_end,
            years=float(major_years),
        ))

        # Sub-periods: 7 planets in Chaldean order, each lasting major_years/7.
        # The sub-period sequence starts at the major planet's Chaldean position.
        if major_planet in CHALDEAN_ORDER:
            start_idx = CHALDEAN_ORDER.index(major_planet)
        else:
            # Nodes use the same starting index as Mars (traditional default)
            start_idx = CHALDEAN_ORDER.index("Mars")

        sub_years = major_years / 7.0
        sub_cursor = major_start

        for i in range(7):
            sub_planet = CHALDEAN_ORDER[(start_idx + i) % 7]
            sub_end    = sub_cursor + sub_years * _JULIAN_YEAR
            periods.append(FirdarPeriod(
                level=2,
                planet=sub_planet,
                start_jd=sub_cursor,
                end_jd=sub_end,
                years=sub_years,
            ))
            sub_cursor = sub_end

        cursor_jd = major_end

    return periods


def current_firdaria(
    natal_jd: float,
    current_jd: float,
    is_day_chart: bool,
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
    all_periods = firdaria(natal_jd, is_day_chart)
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
        # Edge case: exactly at major-period boundary — use first sub-period
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

#: Total of all Minor Years — one full zodiacal cycle = 129 years
_TOTAL_MINOR_YEARS: int = sum(MINOR_YEARS.values())  # 129


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
        return (
            f"ReleasingPeriod(L{self.level} {self.sign:<13} "
            f"({self.ruler:<8}) {self.years:.3f} yrs | "
            f"{self.start_calendar.date_string()} → "
            f"{self.end_calendar.date_string()})"
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


def _generate_releasing(
    start_sign: str,
    start_jd: float,
    level: int,
    max_level: int,
    max_jd: float,
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
    start_idx = _sign_index(start_sign)
    cursor_jd = start_jd
    sign_offset = 0

    # Cycle until we exceed the time cap
    while cursor_jd < max_jd:
        current_sign  = _sign_at_index(start_idx + sign_offset)
        period_years  = float(MINOR_YEARS[current_sign])
        period_jd_len = period_years * _JULIAN_YEAR
        period_end    = cursor_jd + period_jd_len

        # Clamp to the hard boundary
        effective_end = min(period_end, max_jd)

        # Compute the actual duration for this (possibly clamped) period
        effective_years = (effective_end - cursor_jd) / _JULIAN_YEAR

        rp = ReleasingPeriod(
            level=level,
            sign=current_sign,
            ruler=DOMICILE_RULERS[current_sign],
            start_jd=cursor_jd,
            end_jd=effective_end,
            years=effective_years,
        )
        results.append(rp)

        # Recurse into deeper levels if requested
        if level < max_level and cursor_jd < max_jd:
            sub = _generate_releasing(
                start_sign=current_sign,   # Level 2 starts at the same sign
                start_jd=cursor_jd,
                level=level + 1,
                max_level=max_level,
                max_jd=effective_end,
            )
            results.extend(sub)

        cursor_jd = period_end  # advance by full (unclamped) length to stay on schedule
        sign_offset += 1

    return results


# ---------------------------------------------------------------------------
# Zodiacal Releasing public API
# ---------------------------------------------------------------------------

def zodiacal_releasing(
    lot_longitude: float,
    natal_jd: float,
    levels: int = 4,
) -> list[ReleasingPeriod]:
    """
    Generate Zodiacal Releasing periods from a Lot (Fortune, Spirit, etc.).

    Level 1 periods advance through the zodiac from the Lot's natal sign.
    Deeper levels are sub-periods within each Level 1 (and subsequent) period,
    starting from the same sign as their containing period.

    The output is capped at 120 years of elapsed time from birth.

    Parameters
    ----------
    lot_longitude : float
        Ecliptic longitude of the Lot in the natal chart (degrees, 0–360).
    natal_jd : float
        Julian Day (UT) of birth.
    levels : int
        Number of releasing levels to generate (1–4, default 4).

    Returns
    -------
    list[ReleasingPeriod]
        All releasing periods across the requested levels, in chronological
        order (Level 1, then interleaved deeper levels inside each L1 period).
    """
    start_sign, _, _ = sign_of(lot_longitude)
    max_jd = natal_jd + 120.0 * _JULIAN_YEAR

    return _generate_releasing(
        start_sign=start_sign,
        start_jd=natal_jd,
        level=1,
        max_level=max(1, min(levels, 4)),
        max_jd=max_jd,
    )


def current_releasing(
    lot_longitude: float,
    natal_jd: float,
    current_jd: float,
) -> list[ReleasingPeriod]:
    """
    Find the four Zodiacal Releasing periods (one per level) active at a date.

    Parameters
    ----------
    lot_longitude : float
        Ecliptic longitude of the Lot in the natal chart.
    natal_jd : float
        Julian Day (UT) of birth.
    current_jd : float
        Julian Day (UT) of the date to evaluate.

    Returns
    -------
    list[ReleasingPeriod]
        List of 4 ReleasingPeriod objects (Levels 1–4) active at current_jd.
        If a level cannot be determined, the last valid period for that level
        is returned.

    Raises
    ------
    ValueError
        If current_jd is before natal_jd or beyond the 120-year cap.
    """
    if current_jd < natal_jd:
        raise ValueError("current_jd must not be earlier than natal_jd.")

    if current_jd > natal_jd + 120.0 * _JULIAN_YEAR:
        raise ValueError("current_jd is beyond the 120-year Zodiacal Releasing cap.")

    all_periods = zodiacal_releasing(lot_longitude, natal_jd, levels=4)

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
