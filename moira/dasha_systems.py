"""
Moira — Alternative Dasha Systems
====================================

Archetype: Engine

Purpose
-------
Implements Vedic time-lord systems beyond Vimshottari (which is in
``moira.dasha``).  Two systems are fully implemented:

  Ashtottari Dasha  — 108-year cycle with 8 lords.  Starting lord and
                      balance follow BPHS chapter 46's alternating groups
                      of four and three nakshatras, beginning with Ardra.
                      The 28-place count includes Abhijit.

  Yogini Dasha      — 36-year cycle with 8 Yoginis.  Starting Yogini is
                      determined by adding three to the one-based birth-
                      nakshatra number and reducing to a one-through-eight
                      remainder.  No eligibility condition.

A third system, Kalachakra Dasha, requires Navamsha-based sign traversal
with Savya/Apasavya direction switching.  It is reserved for Phase 2 of
this module.

Sub-period arithmetic
---------------------
Both systems use the same proportional sub-period formula as Vimshottari:

    sub_years = (sub_lord_years / system_total) × mahadasha_years

For Yogini, the elapsed fraction in the birth nakshatra determines the
remaining portion of the first Mahadasha.  For Ashtottari, the elapsed
fraction is measured through the current lord's three- or four-nakshatra
allocation before the remaining Mahadasha balance is derived.

Tradition and sources
---------------------
Ashtottari:
  Parashara, "Brihat Parashara Hora Shastra", chapter 46, verses 17–22.
  The exact Abhijit span is a separately identified later convention; BPHS
  supplies the 28-place allocation but not those longitude boundaries.
  Total years = 108; lords = Sun, Moon, Mars, Mercury, Saturn, Jupiter,
  Rahu, Venus.

Yogini:
  Parashara, "Brihat Parashara Hora Shastra", chapter 46, verses 195–200.
  Total years = 36; Yoginis: Mangala, Pingala, Dhanya, Bhramari,
  Bhadrika, Ulka, Siddha, Sankata.

Boundary declaration
--------------------
Owns: Ashtottari and Yogini computation, eligibility-policy boundary, and the
      ``AlternateDashaPeriod``, ``AshtottariPolicy``, ``YoginiPolicy``
      result and policy vessels.
Delegates: nakshatra computation to ``moira.sidereal``, Julian year
           arithmetic to ``moira.constants``.

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required.  No database access.  ``moira.sidereal`` is
imported at call time.

Constitutional phase
--------------------
Phase 12 — Public API Curation.  All twelve phases complete.

Public surface
--------------
``AlternateDashaSystem``        — string constants for the two supported systems.
``ASHTOTTARI_YEARS``            — lord → years in the 108-year cycle.
``ASHTOTTARI_SEQUENCE``         — ordered lord sequence.
``YOGINI_YEARS``                — yogini → years in the 36-year cycle.
``YOGINI_SEQUENCE``             — ordered yogini sequence.
``YOGINI_PLANETS``              — yogini → planetary lord.
``AlternateDashaPeriod``        — immutable period vessel.
``AshtottariPolicy``            — policy dataclass for Ashtottari computation.
``YoginiPolicy``                — policy dataclass for Yogini computation.
``AlternatePeriodProfile``      — integrated condition profile for one period.
``AlternateDashaSequenceProfile`` — aggregate intelligence for a full Mahadasha sequence.
``ashtottari``                  — compute Ashtottari Mahadashas for a natal chart.
``yogini_dasha``                — compute Yogini Mahadashas for a natal chart.
``alternate_period_profile``    — build an AlternatePeriodProfile from one period.
``alternate_sequence_profile``  — build an AlternateDashaSequenceProfile.
``validate_alternate_dasha_output`` — validate structural invariants of a Mahadasha list.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .constants import JULIAN_YEAR

__all__ = [
    # Phase 2 — Classification
    "AlternateDashaSystem",
    # Constants
    "ASHTOTTARI_YEARS",
    "ASHTOTTARI_SEQUENCE",
    "ASHTOTTARI_NAKSHATRA_LORD",
    "ASHTOTTARI_TOTAL",
    "YOGINI_YEARS",
    "YOGINI_SEQUENCE",
    "YOGINI_PLANETS",
    "YOGINI_TOTAL",
    # Phase 1 — Truth Preservation
    "AlternateDashaPeriod",
    # Phase 4 — Policy
    "AshtottariPolicy",
    "YoginiPolicy",
    # Phase 7 — Integrated Local Condition
    "AlternatePeriodProfile",
    # Phase 8 — Aggregate Intelligence
    "AlternateDashaSequenceProfile",
    # Functions
    "ashtottari",
    "yogini_dasha",
    "alternate_period_profile",
    "alternate_sequence_profile",
    "validate_alternate_dasha_output",
]

# ---------------------------------------------------------------------------
# Ashtottari constants
#
# Primary source: BPHS chapter 46, verses 17–22.
# 8 lords, 108-year total.  Four- and three-nakshatra groups begin at Ardra.
# ---------------------------------------------------------------------------

ASHTOTTARI_YEARS: dict[str, int] = {
    'Sun': 6, 'Moon': 15, 'Mars': 8, 'Mercury': 17,
    'Saturn': 10, 'Jupiter': 19, 'Rahu': 12, 'Venus': 21,
}

ASHTOTTARI_SEQUENCE: list[str] = [
    'Sun', 'Moon', 'Mars', 'Mercury', 'Saturn', 'Jupiter', 'Rahu', 'Venus',
]

ASHTOTTARI_TOTAL: int = 108

# BPHS 46.18 alternates four-nakshatra malefic groups and three-nakshatra
# benefic groups.  Verse 17 begins the allocation at Ardra.  The resulting
# count has 28 places because Saturn's group includes Abhijit.
_ASHTOTTARI_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ('Sun', ('Ardra', 'Punarvasu', 'Pushya', 'Ashlesha')),
    ('Moon', ('Magha', 'Purva Phalguni', 'Uttara Phalguni')),
    ('Mars', ('Hasta', 'Chitra', 'Swati', 'Vishakha')),
    ('Mercury', ('Anuradha', 'Jyeshtha', 'Mula')),
    ('Saturn', ('Purva Ashadha', 'Uttara Ashadha', 'Abhijit', 'Shravana')),
    ('Jupiter', ('Dhanishtha', 'Shatabhisha', 'Purva Bhadrapada')),
    ('Rahu', ('Uttara Bhadrapada', 'Revati', 'Ashwini', 'Bharani')),
    ('Venus', ('Krittika', 'Rohini', 'Mrigashira')),
)

_ASHTOTTARI_SEGMENT_RULE: dict[str, tuple[str, int, int]] = {
    nakshatra: (lord, ordinal, len(nakshatras))
    for lord, nakshatras in _ASHTOTTARI_GROUPS
    for ordinal, nakshatra in enumerate(nakshatras)
}

_STANDARD_NAKSHATRA_NAMES: tuple[str, ...] = (
    'Ashwini', 'Bharani', 'Krittika', 'Rohini', 'Mrigashira', 'Ardra',
    'Punarvasu', 'Pushya', 'Ashlesha', 'Magha', 'Purva Phalguni',
    'Uttara Phalguni', 'Hasta', 'Chitra', 'Swati', 'Vishakha',
    'Anuradha', 'Jyeshtha', 'Mula', 'Purva Ashadha', 'Uttara Ashadha',
    'Shravana', 'Dhanishtha', 'Shatabhisha', 'Purva Bhadrapada',
    'Uttara Bhadrapada', 'Revati',
)

# Public 27-nakshatra projection retained for callers using the ordinary
# nakshatra index.  The computation itself uses the 28-place rule above so it
# can distinguish the intercalated Abhijit segment and its balance.
ASHTOTTARI_NAKSHATRA_LORD: list[str] = [
    _ASHTOTTARI_SEGMENT_RULE[name][0] for name in _STANDARD_NAKSHATRA_NAMES
]

# BPHS requires Abhijit as a counting place but does not state its longitude
# span in verses 17–22.  Moira therefore names the later traditional boundary
# explicitly: 6°40'–10°53'20" sidereal Capricorn, the last quarter of Uttara
# Ashadha plus the first fifteenth of Shravana.
_ASHTOTTARI_ABHIJIT_START = 270.0 + 6.0 + 40.0 / 60.0
_ASHTOTTARI_ABHIJIT_END = 270.0 + 10.0 + 53.0 / 60.0 + 20.0 / 3600.0


# ---------------------------------------------------------------------------
# Yogini constants
#
# Primary source: BPHS chapter 46, verses 195–200.
# 8 Yoginis, 36-year total.
# ---------------------------------------------------------------------------

YOGINI_YEARS: dict[str, int] = {
    'Mangala': 1, 'Pingala': 2, 'Dhanya': 3, 'Bhramari': 4,
    'Bhadrika': 5, 'Ulka': 6, 'Siddha': 7, 'Sankata': 8,
}

YOGINI_SEQUENCE: list[str] = [
    'Mangala', 'Pingala', 'Dhanya', 'Bhramari',
    'Bhadrika', 'Ulka', 'Siddha', 'Sankata',
]

YOGINI_PLANETS: dict[str, str] = {
    'Mangala': 'Moon',
    'Pingala': 'Sun',
    'Dhanya':  'Jupiter',
    'Bhramari': 'Mars',
    'Bhadrika': 'Mercury',
    'Ulka':    'Saturn',
    'Siddha':  'Venus',
    'Sankata': 'Rahu',
}

YOGINI_TOTAL: int = 36


# ---------------------------------------------------------------------------
# Supported year bases (mirrors dasha.py)
# ---------------------------------------------------------------------------

_YEAR_BASIS: dict[str, float] = {
    'julian_365.25': JULIAN_YEAR,
    'savana_360':    360.0,
    'tropical_365.2422': 365.2422,
    'sidereal_365.2564': 365.2564,
}


# ---------------------------------------------------------------------------
# Phase 2 — Classification constants
# ---------------------------------------------------------------------------

class AlternateDashaSystem:
    """String constants for the supported alternative Dasha systems.

    Use these instead of bare string literals to reference a system.
    The values match the ``system`` field on ``AlternateDashaPeriod``.
    """
    ASHTOTTARI = 'ashtottari'
    YOGINI     = 'yogini'


# ---------------------------------------------------------------------------
# Result vessel
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AlternateDashaPeriod:
    """
    Immutable vessel for one period in an alternative dasha system.

    Attributes
    ----------
    system : str
        System identifier: ``'ashtottari'`` or ``'yogini'``.
    level : int
        Hierarchy level: 1 = Mahadasha, 2 = Antardasha, 3 = Pratyantar, etc.
    lord : str
        For Ashtottari: the planetary lord (e.g. ``'Sun'``).
        For Yogini: the Yogini name (e.g. ``'Mangala'``).
    start_jd : float
        Julian date (UT) when this period begins.
    end_jd : float
        Julian date (UT) when this period ends.
    sub : list[AlternateDashaPeriod]
        Sub-periods (Antardashas etc.) if ``levels > 1`` was requested.
        Empty list for terminal-level periods.
    """

    system: str
    level: int
    lord: str
    start_jd: float
    end_jd: float
    sub: list["AlternateDashaPeriod"]
    full_start_jd: float | None = None
    full_end_jd: float | None = None
    year_days: float | None = None
    year_basis: str | None = None

    def __post_init__(self) -> None:
        from ._dasha_intervals import validate_interval
        validate_interval(self.start_jd, self.end_jd, self.full_start_jd, self.full_end_jd)
        if (self.year_days is None) != (self.year_basis is None):
            raise ValueError("year_days and year_basis must be supplied together")
        if self.year_basis is not None and _YEAR_BASIS.get(self.year_basis) != self.year_days:
            raise ValueError("year_days must match the declared year_basis")
        if self.system not in ('ashtottari', 'yogini'):
            raise ValueError(
                f"AlternateDashaPeriod.system must be 'ashtottari' or 'yogini', "
                f"got {self.system!r}"
            )
        if self.level < 1:
            raise ValueError(
                f"AlternateDashaPeriod.level must be >= 1, got {self.level}"
            )
        if not self.lord:
            raise ValueError("AlternateDashaPeriod.lord must be a non-empty string")
        if not math.isfinite(self.start_jd) or not math.isfinite(self.end_jd):
            raise ValueError("start_jd and end_jd must be finite")
        if self.start_jd >= self.end_jd:
            raise ValueError(
                f"start_jd ({self.start_jd}) must be < end_jd ({self.end_jd})"
            )

    # --- Phase 3 — Inspectability ------------------------------------------

    @property
    def years(self) -> float:
        """Duration of this period in Julian years (365.25 days)."""
        return (self.end_jd - self.start_jd) / JULIAN_YEAR

    @property
    def is_terminal(self) -> bool:
        """``True`` when this period has no computed sub-periods."""
        return len(self.sub) == 0


# ---------------------------------------------------------------------------
# Policy dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AshtottariPolicy:
    """
    Policy surface for Ashtottari Dasha computation.

    Attributes
    ----------
    year_basis : str
        Year-length doctrine.  One of ``'julian_365.25'``,
        ``'savana_360'``, ``'tropical_365.2422'``,
        ``'sidereal_365.2564'``.  Defaults to ``'julian_365.25'``.
    ayanamsa_system : str
        Ayanamsa system for nakshatra conversion.  Defaults to
        ``'Lahiri'``.
    bypass_eligibility : bool
        If ``True``, the caller explicitly elects to compute Ashtottari
        without an engine eligibility determination.  The current policy
        vessel does not carry enough information to evaluate BPHS 46.17 and
        46.23, so ``False`` must not be read as a positive eligibility proof.
    lagna_sign_index : int or None
        Legacy 0-based Ascendant sign input.  This value alone cannot
        establish the BPHS conditions; supplying it without bypassing the
        check raises rather than fabricating a determination.
    """

    year_basis: str = 'julian_365.25'
    ayanamsa_system: str = 'Lahiri'
    bypass_eligibility: bool = False
    lagna_sign_index: int | None = None

    def __post_init__(self) -> None:
        if self.year_basis not in _YEAR_BASIS:
            raise ValueError(
                f"AshtottariPolicy.year_basis must be one of "
                f"{list(_YEAR_BASIS)}, got {self.year_basis!r}"
            )
        if not self.ayanamsa_system:
            raise ValueError(
                "AshtottariPolicy.ayanamsa_system must be a non-empty string"
            )


@dataclass(frozen=True, slots=True)
class YoginiPolicy:
    """
    Policy surface for Yogini Dasha computation.

    Attributes
    ----------
    year_basis : str
        Year-length doctrine.  Defaults to ``'julian_365.25'``.
    ayanamsa_system : str
        Ayanamsa system.  Defaults to ``'Lahiri'``.
    """

    year_basis: str = 'julian_365.25'
    ayanamsa_system: str = 'Lahiri'

    def __post_init__(self) -> None:
        if self.year_basis not in _YEAR_BASIS:
            raise ValueError(
                f"YoginiPolicy.year_basis must be one of "
                f"{list(_YEAR_BASIS)}, got {self.year_basis!r}"
            )
        if not self.ayanamsa_system:
            raise ValueError(
                "YoginiPolicy.ayanamsa_system must be a non-empty string"
            )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_year_days(year_basis: str) -> float:
    """Return the number of days in one year for the given year_basis."""
    if year_basis not in _YEAR_BASIS:
        raise ValueError(
            f"year_basis must be one of {list(_YEAR_BASIS)}, got {year_basis!r}"
        )
    return _YEAR_BASIS[year_basis]


def _sequence_from(sequence: list[str], starting_lord: str) -> list[str]:
    """
    Return the dasha sequence starting from ``starting_lord``.

    Raises
    ------
    ValueError
        If ``starting_lord`` is not in ``sequence``.
    """
    if starting_lord not in sequence:
        raise ValueError(
            f"{starting_lord!r} is not in the dasha sequence {sequence}"
        )
    idx = sequence.index(starting_lord)
    return sequence[idx:] + sequence[:idx]


def _snap_to_following_segment(value: float, boundary: float) -> float:
    """Give an exact boundary and its first predecessor to the next segment."""
    if value == boundary or value == math.nextafter(boundary, -math.inf):
        return boundary
    return value


def _ashtottari_entry(
    sidereal_longitude: float,
    nakshatra_index: int,
    degrees_in_nakshatra: float,
    nakshatra_span: float,
) -> tuple[str, float]:
    """Return the BPHS starting lord and elapsed fraction of its Mahadasha.

    BPHS 46.17–22 assigns either three or four consecutive counting places to
    each lord.  The first-period balance must therefore include complete
    places already traversed within that lord's group, not merely the elapsed
    fraction of the Moon's ordinary 27-fold nakshatra.

    The text requires Abhijit as one of four Saturn-group places but does not
    define its arc there.  Classification uses Moira's named traditional
    Abhijit boundary constants above.
    """
    segment_name = _STANDARD_NAKSHATRA_NAMES[nakshatra_index]
    segment_fraction = degrees_in_nakshatra / nakshatra_span

    longitude = _snap_to_following_segment(
        sidereal_longitude,
        _ASHTOTTARI_ABHIJIT_START,
    )
    longitude = _snap_to_following_segment(
        longitude,
        _ASHTOTTARI_ABHIJIT_END,
    )

    if segment_name == 'Uttara Ashadha':
        uttara_ashadha_start = nakshatra_index * nakshatra_span
        if longitude >= _ASHTOTTARI_ABHIJIT_START:
            segment_name = 'Abhijit'
            segment_fraction = (
                (longitude - _ASHTOTTARI_ABHIJIT_START)
                / (_ASHTOTTARI_ABHIJIT_END - _ASHTOTTARI_ABHIJIT_START)
            )
        else:
            segment_fraction = (
                (longitude - uttara_ashadha_start)
                / (_ASHTOTTARI_ABHIJIT_START - uttara_ashadha_start)
            )
    elif segment_name == 'Shravana':
        shravana_end = (nakshatra_index + 1) * nakshatra_span
        if longitude < _ASHTOTTARI_ABHIJIT_END:
            segment_name = 'Abhijit'
            segment_fraction = (
                (longitude - _ASHTOTTARI_ABHIJIT_START)
                / (_ASHTOTTARI_ABHIJIT_END - _ASHTOTTARI_ABHIJIT_START)
            )
        else:
            segment_fraction = (
                (longitude - _ASHTOTTARI_ABHIJIT_END)
                / (shravana_end - _ASHTOTTARI_ABHIJIT_END)
            )

    lord, segment_ordinal, group_size = _ASHTOTTARI_SEGMENT_RULE[segment_name]
    fraction_elapsed = (segment_ordinal + segment_fraction) / group_size
    return lord, fraction_elapsed


def _build_sub_periods(
    period: AlternateDashaPeriod,
    years_table: dict[str, int],
    sequence: list[str],
    total_years: int,
    year_days: float,
    current_level: int,
    max_levels: int,
) -> AlternateDashaPeriod:
    """
    Recursively attach sub-periods to a dasha period.

    Sub-period durations are proportional: sub_years = (sub_lord_years /
    total_years) × period_years.
    """
    if current_level >= max_levels:
        return period

    sub_sequence = _sequence_from(sequence, period.lord)
    sub_periods: list[AlternateDashaPeriod] = []
    from ._dasha_intervals import subdivisions
    for index, start, end, full_start, full_end in subdivisions(
        period.start_jd, period.end_jd, period.full_start_jd, period.full_end_jd,
        [years_table[lord] for lord in sub_sequence],
    ):
        sub_lord = sub_sequence[index]
        sub = AlternateDashaPeriod(
            system=period.system,
            level=current_level + 1,
            lord=sub_lord,
            start_jd=start,
            end_jd=end,
            full_start_jd=full_start,
            full_end_jd=full_end,
            year_days=period.year_days,
            year_basis=period.year_basis,
            sub=[],
        )
        sub = _build_sub_periods(
            sub, years_table, sequence, total_years, year_days,
            current_level + 1, max_levels,
        )
        sub_periods.append(sub)

    return AlternateDashaPeriod(
        system=period.system,
        level=period.level,
        lord=period.lord,
        start_jd=period.start_jd,
        end_jd=period.end_jd,
        sub=sub_periods,
        full_start_jd=period.full_start_jd,
        full_end_jd=period.full_end_jd,
        year_days=period.year_days,
        year_basis=period.year_basis,
    )


def _compute_dashas(
    starting_lord: str,
    fraction_elapsed_in_first: float,
    natal_jd: float,
    years_table: dict[str, int],
    sequence: list[str],
    total_years: int,
    year_days: float,
    system: str,
    levels: int,
) -> list[AlternateDashaPeriod]:
    """
    Core dasha computation shared by Ashtottari and Yogini.

    Parameters
    ----------
    fraction_elapsed_in_first : float
        Fraction of the first Mahadasha already elapsed at birth (0.0–1.0).
    """
    ordered = _sequence_from(sequence, starting_lord)
    cycle_end_jd = natal_jd + total_years * year_days
    result: list[AlternateDashaPeriod] = []
    current_jd = natal_jd

    for i, lord in enumerate(ordered * 2):  # two full cycles covers any chart
        if current_jd >= cycle_end_jd:
            break
        base_years = float(years_table[lord])
        if i == 0:
            duration_years = base_years * (1.0 - fraction_elapsed_in_first)
        else:
            duration_years = base_years
        full_end_jd = current_jd + duration_years * year_days
        full_start_jd = full_end_jd - base_years * year_days if i == 0 else current_jd
        end_jd = min(full_end_jd, cycle_end_jd)
        period = AlternateDashaPeriod(
            system=system,
            level=1,
            lord=lord,
            start_jd=current_jd,
            end_jd=end_jd,
            sub=[],
            full_start_jd=full_start_jd,
            full_end_jd=full_end_jd,
            year_days=year_days,
            year_basis=next(key for key, days in _YEAR_BASIS.items() if days == year_days),
        )
        if levels > 1:
            period = _build_sub_periods(
                period, years_table, sequence, total_years, year_days, 1, levels
            )
        result.append(period)
        current_jd = end_jd

    return result


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def ashtottari(
    moon_tropical_lon: float,
    natal_jd: float,
    levels: int = 2,
    policy: AshtottariPolicy | None = None,
) -> list[AlternateDashaPeriod]:
    """
    Compute Ashtottari Mahadashas (and optionally Antardashas) for a chart.

    The starting lord and first-period balance follow BPHS chapter 46,
    verses 17–22: alternating groups of four and three nakshatras begin at
    Ardra, and the 28-place count includes Abhijit.  Each place receives one
    quarter or one third of its lord's Mahadasha respectively.

    Parameters
    ----------
    moon_tropical_lon : float
        Tropical ecliptic longitude of the Moon at birth.
    natal_jd : float
        Julian date (UT) of the birth moment.
    levels : int
        Number of hierarchy levels to compute (1 = Mahadasha only,
        2 = Mahadasha + Antardasha, etc.).  Clamped to [1, 4].
    policy : AshtottariPolicy or None
        Computation policy.  Defaults to ``AshtottariPolicy()`` if ``None``.

    Returns
    -------
    list[AlternateDashaPeriod]
        One entry per Mahadasha spanning the 108-year cycle.

    Raises
    ------
    ValueError
        If the legacy ``lagna_sign_index`` is supplied while eligibility is
        not bypassed.  That input alone cannot evaluate the BPHS 46.17 and
        46.23 applicability conditions.
    ValueError
        If ``natal_jd`` is not finite.
    """
    if policy is None:
        policy = AshtottariPolicy()
    if not math.isfinite(natal_jd):
        raise ValueError("natal_jd must be finite")

    from .sidereal import NAKSHATRA_SPAN, _nakshatra_sector, tropical_to_sidereal

    year_days = _resolve_year_days(policy.year_basis)
    levels = max(1, min(levels, 4))

    # Eligibility check
    if not policy.bypass_eligibility and policy.lagna_sign_index is not None:
        raise ValueError(
            "Ashtottari eligibility check cannot be derived from "
            "lagna_sign_index alone. BPHS 46.17 and 46.23 require additional "
            "Rahu, Lagna-lord, paksha, and day/night context; set "
            "bypass_eligibility=True to proceed without that determination."
        )

    # Nakshatra of Moon at birth
    sid_lon = tropical_to_sidereal(
        moon_tropical_lon, natal_jd, system=policy.ayanamsa_system
    )
    sid_lon, nak_idx, deg_in_nak = _nakshatra_sector(sid_lon)
    starting_lord, fraction_elapsed = _ashtottari_entry(
        sidereal_longitude=sid_lon,
        nakshatra_index=nak_idx,
        degrees_in_nakshatra=deg_in_nak,
        nakshatra_span=NAKSHATRA_SPAN,
    )

    return _compute_dashas(
        starting_lord=starting_lord,
        fraction_elapsed_in_first=fraction_elapsed,
        natal_jd=natal_jd,
        years_table=ASHTOTTARI_YEARS,
        sequence=ASHTOTTARI_SEQUENCE,
        total_years=ASHTOTTARI_TOTAL,
        year_days=year_days,
        system='ashtottari',
        levels=levels,
    )


def yogini_dasha(
    moon_tropical_lon: float,
    natal_jd: float,
    levels: int = 2,
    policy: YoginiPolicy | None = None,
) -> list[AlternateDashaPeriod]:
    """
    Compute Yogini Mahadashas (and optionally Antardashas) for a chart.

    BPHS chapter 46, verse 199 determines the starting Yogini by adding three
    to the one-based birth-nakshatra number and reducing it to a
    one-through-eight remainder.  In zero-based indexing this is
    ``(nakshatra_index + 3) % 8``.

    Parameters
    ----------
    moon_tropical_lon : float
        Tropical ecliptic longitude of the Moon at birth.
    natal_jd : float
        Julian date (UT) of the birth moment.
    levels : int
        Number of hierarchy levels (1–4).
    policy : YoginiPolicy or None
        Computation policy.  Defaults to ``YoginiPolicy()`` if ``None``.

    Returns
    -------
    list[AlternateDashaPeriod]
        One entry per Yogini Mahadasha spanning the 36-year cycle.

    Raises
    ------
    ValueError
        If ``natal_jd`` is not finite.
    """
    if policy is None:
        policy = YoginiPolicy()
    if not math.isfinite(natal_jd):
        raise ValueError("natal_jd must be finite")

    from .sidereal import NAKSHATRA_SPAN, _nakshatra_sector, tropical_to_sidereal

    year_days = _resolve_year_days(policy.year_basis)
    levels = max(1, min(levels, 4))

    # Nakshatra of Moon at birth
    sid_lon = tropical_to_sidereal(
        moon_tropical_lon, natal_jd, system=policy.ayanamsa_system
    )
    _, nak_idx, deg_in_nak = _nakshatra_sector(sid_lon)
    fraction_elapsed = deg_in_nak / NAKSHATRA_SPAN

    # Starting Yogini index
    yogini_start_idx = (nak_idx + 3) % 8
    starting_yogini = YOGINI_SEQUENCE[yogini_start_idx]

    return _compute_dashas(
        starting_lord=starting_yogini,
        fraction_elapsed_in_first=fraction_elapsed,
        natal_jd=natal_jd,
        years_table=YOGINI_YEARS,
        sequence=YOGINI_SEQUENCE,
        total_years=YOGINI_TOTAL,
        year_days=year_days,
        system='yogini',
        levels=levels,
    )


# ---------------------------------------------------------------------------
# Private classification helpers
# ---------------------------------------------------------------------------

# Ashtottari planetary lords and Yogini-mapped planets that are nodes
_NODE_PLANETS: frozenset[str] = frozenset({'Rahu'})
_LUMINARY_PLANETS: frozenset[str] = frozenset({'Sun', 'Moon'})


def _planet_for_lord(lord: str, system: str) -> str:
    """Return the underlying planet name for a dasha lord.

    For Ashtottari, the lord IS the planet.
    For Yogini, the lord is a Yogini name; look up via ``YOGINI_PLANETS``.
    """
    if system == 'yogini':
        return YOGINI_PLANETS[lord]
    return lord


# ---------------------------------------------------------------------------
# Phase 7 — Integrated Local Condition
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AlternatePeriodProfile:
    """Integrated condition profile for one :class:`AlternateDashaPeriod`.

    Enriches the raw period with doctrinal classification (node /
    luminary flags, underlying planet for Yogini lords).  Built via
    :func:`alternate_period_profile`.

    Attributes
    ----------
    system : str
        ``'ashtottari'`` or ``'yogini'``.
    level : int
        Hierarchy level (1 = Mahadasha).
    lord : str
        The lord name (planet for Ashtottari; Yogini name for Yogini).
    planet : str
        The underlying planet (``lord`` for Ashtottari; derived via
        ``YOGINI_PLANETS`` for Yogini).
    years : float
        Duration in Julian years.
    is_node_lord : bool
        ``True`` when the underlying planet is Rahu.
    is_luminary_lord : bool
        ``True`` when the underlying planet is Sun or Moon.
    """

    system: str
    level: int
    lord: str
    planet: str
    years: float
    is_node_lord: bool
    is_luminary_lord: bool


# ---------------------------------------------------------------------------
# Phase 8 — Aggregate Intelligence
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AlternateDashaSequenceProfile:
    """Aggregate intelligence profile for a complete Mahadasha sequence.

    Derived from a list of level-1 :class:`AlternateDashaPeriod` records
    via :func:`alternate_sequence_profile`.

    Attributes
    ----------
    system : str
        ``'ashtottari'`` or ``'yogini'``.
    total_years : int
        Canonical cycle length (108 for Ashtottari, 36 for Yogini).
    mahadasha_count : int
        Number of Mahadasha periods in the list (always equals the number
        of lords in the sequence for a full cycle).
    profiles : list[AlternatePeriodProfile]
        One profile per Mahadasha in chronological order.
    """

    system: str
    total_years: int
    mahadasha_count: int
    profiles: list[AlternatePeriodProfile]

    def __post_init__(self) -> None:
        if self.system not in ('ashtottari', 'yogini'):
            raise ValueError(
                f"AlternateDashaSequenceProfile.system must be 'ashtottari' or "
                f"'yogini', got {self.system!r}"
            )
        if self.mahadasha_count != len(self.profiles):
            raise ValueError(
                f"mahadasha_count ({self.mahadasha_count}) != "
                f"len(profiles) ({len(self.profiles)})"
            )


# ---------------------------------------------------------------------------
# Phase 7 — Condition profile function
# ---------------------------------------------------------------------------

def alternate_period_profile(
    period: AlternateDashaPeriod,
) -> AlternatePeriodProfile:
    """Build an :class:`AlternatePeriodProfile` from one
    :class:`AlternateDashaPeriod`.

    Parameters
    ----------
    period : AlternateDashaPeriod

    Returns
    -------
    AlternatePeriodProfile
    """
    planet = _planet_for_lord(period.lord, period.system)
    return AlternatePeriodProfile(
        system=period.system,
        level=period.level,
        lord=period.lord,
        planet=planet,
        years=period.years,
        is_node_lord=(planet in _NODE_PLANETS),
        is_luminary_lord=(planet in _LUMINARY_PLANETS),
    )


# ---------------------------------------------------------------------------
# Phase 8 — Aggregate function
# ---------------------------------------------------------------------------

def alternate_sequence_profile(
    periods: list[AlternateDashaPeriod],
) -> AlternateDashaSequenceProfile:
    """Build an :class:`AlternateDashaSequenceProfile` from a list of
    level-1 :class:`AlternateDashaPeriod` records.

    Parameters
    ----------
    periods : list[AlternateDashaPeriod]
        All Mahadasha-level periods for one chart (as returned by
        ``ashtottari()`` or ``yogini_dasha()``).

    Returns
    -------
    AlternateDashaSequenceProfile

    Raises
    ------
    ValueError
        If ``periods`` is empty.
    """
    if not periods:
        raise ValueError("periods must not be empty")
    system = periods[0].system
    total_years = ASHTOTTARI_TOTAL if system == 'ashtottari' else YOGINI_TOTAL
    profiles = [alternate_period_profile(p) for p in periods]
    return AlternateDashaSequenceProfile(
        system=system,
        total_years=total_years,
        mahadasha_count=len(periods),
        profiles=profiles,
    )


# ---------------------------------------------------------------------------
# Phase 10 — Full-subsystem hardening
# ---------------------------------------------------------------------------

def validate_alternate_dasha_output(
    periods: list[AlternateDashaPeriod],
) -> None:
    """Validate structural invariants of an alternate dasha Mahadasha list.

    Raises ``ValueError`` with a descriptive message if any invariant is
    violated.

    Invariants checked
    ------------------
    - ``periods`` is non-empty.
    - All periods have the same ``system``.
    - All periods have ``level == 1``.
    - ``start_jd < end_jd`` for each period.
    - Periods are chronologically ordered without gaps between adjacent
      entries (``periods[i].end_jd == periods[i+1].start_jd`` within
      ±1e-6 tolerance).
    - Each lord is a recognised lord for the declared system.

    Parameters
    ----------
    periods : list[AlternateDashaPeriod]

    Raises
    ------
    ValueError
        On any invariant violation.
    """
    if not periods:
        raise ValueError("periods must not be empty")
    system = periods[0].system
    if system == 'ashtottari':
        valid_lords: frozenset[str] = frozenset(ASHTOTTARI_SEQUENCE)
    else:
        valid_lords = frozenset(YOGINI_SEQUENCE)
    for i, p in enumerate(periods):
        _validate_alternate_children(p)
        if p.system != system:
            raise ValueError(
                f"periods[{i}].system = {p.system!r} differs from "
                f"periods[0].system = {system!r}"
            )
        if p.level != 1:
            raise ValueError(
                f"periods[{i}].level = {p.level}, expected 1 (Mahadasha)"
            )
        if p.lord not in valid_lords:
            raise ValueError(
                f"periods[{i}].lord = {p.lord!r} is not a recognised lord "
                f"for system {system!r}"
            )
        if i > 0:
            gap = abs(periods[i].start_jd - periods[i - 1].end_jd)
            if gap > 1e-6:
                raise ValueError(
                    f"Gap or overlap between periods[{i - 1}] and "
                    f"periods[{i}]: Δ = {gap:.8f} JD"
                )


def _validate_alternate_children(
    period: AlternateDashaPeriod, *, require_complete: bool = True,
) -> None:
    """Check identity, chronology and provenance, with explicit coverage mode.

    Generated outputs require complete visible coverage. Supplied REST period
    profiles may select a partial child list; gaps do not waive containment,
    order, full-interval intersection, or uniform year metadata.
    """
    from ._dasha_intervals import validate_child_interval

    period.__post_init__()
    if require_complete and period.sub and (abs(period.sub[0].start_jd - period.start_jd) > 1e-6
                       or abs(period.sub[-1].end_jd - period.end_jd) > 1e-6):
        raise ValueError("Alternate Dasha children must cover their visible parent")
    previous = period.start_jd
    valid = ASHTOTTARI_SEQUENCE if period.system == 'ashtottari' else YOGINI_SEQUENCE
    for child in period.sub:
        if (child.level != period.level + 1 or child.system != period.system
                or child.lord not in valid or child.year_basis != period.year_basis
                or child.year_days != period.year_days):
            raise ValueError("Invalid alternate Dasha child identity, level or year basis")
        if (child.start_jd < previous - 1e-6 or child.end_jd > period.end_jd + 1e-6
                or (require_complete and abs(child.start_jd - previous) > 1e-6)):
            raise ValueError("Alternate Dasha children must be ordered and contained; complete trees must be adjacent")
        validate_child_interval(period, child, tolerance=1e-6)
        _validate_alternate_children(child, require_complete=require_complete)
        previous = child.end_jd
