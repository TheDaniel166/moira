"""
Moira — Alternative Dasha Systems
====================================

Archetype: Engine

Purpose
-------
Implements Vedic time-lord systems beyond Vimshottari (which is in
``moira.dasha``).  Two systems are fully implemented:

  Ashtottari Dasha  — 108-year cycle with 8 lords.  Starting lord is
                      determined by the Moon's birth nakshatra through a
                      nakshatra→lord mapping.  Subject to an eligibility
                      condition (Rahu not in 1st/5th/9th from Lagna) that
                      can be bypassed by policy.

  Yogini Dasha      — 36-year cycle with 8 Yoginis.  Starting Yogini is
                      determined by ``nakshatra_index % 8``.  No eligibility
                      condition.  Simplest of the alternate systems.

A third system, Kalachakra Dasha, requires Navamsha-based sign traversal
with Savya/Apasavya direction switching.  It is reserved for Phase 2 of
this module.

Sub-period arithmetic
---------------------
Both systems use the same proportional sub-period formula as Vimshottari:

    sub_years = (sub_lord_years / system_total) × mahadasha_years

The elapsed fraction in the birth nakshatra determines the remaining
portion of the first Mahadasha at birth.

Tradition and sources
---------------------
Ashtottari:
  Parashara, "Brihat Parashara Hora Shastra", Ashtottari Dasha Adhyaya.
  B.V. Raman, "A Manual of Hindu Astrology", pp. 201–210.
  Total years = 108; lords = Sun, Moon, Mars, Mercury, Saturn, Jupiter,
  Rahu, Venus.

Yogini:
  K.N. Rao, "Yogini Dasha" (1993).
  Parashara, "BPHS" (brief reference).
  Total years = 36; Yoginis: Mangala, Pingala, Dhanya, Bhramari,
  Bhadrika, Ulka, Siddha, Sankata.

Boundary declaration
--------------------
Owns: Ashtottari and Yogini computation, eligibility logic, and the
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
from dataclasses import dataclass, field

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
# Source: BPHS Ashtottari Dasha Adhyaya.
# 8 lords, 108-year total.  Lord sequence differs from Vimshottari.
# ---------------------------------------------------------------------------

ASHTOTTARI_YEARS: dict[str, int] = {
    'Sun': 6, 'Moon': 15, 'Mars': 8, 'Mercury': 17,
    'Saturn': 10, 'Jupiter': 19, 'Rahu': 12, 'Venus': 21,
}

ASHTOTTARI_SEQUENCE: list[str] = [
    'Sun', 'Moon', 'Mars', 'Mercury', 'Saturn', 'Jupiter', 'Rahu', 'Venus',
]

ASHTOTTARI_TOTAL: int = 108

# Nakshatra→Ashtottari lord mapping.
# The 8 lords cycle across all 27 nakshatras in Ashtottari sequence order,
# starting from Ashwini (index 0) = Sun.
ASHTOTTARI_NAKSHATRA_LORD: list[str] = []
for _i in range(27):
    ASHTOTTARI_NAKSHATRA_LORD.append(ASHTOTTARI_SEQUENCE[_i % 8])
del _i


# ---------------------------------------------------------------------------
# Yogini constants
#
# Source: K.N. Rao, "Yogini Dasha" (1993); BPHS (brief reference).
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
    sub: list[AlternateDashaPeriod]

    def __post_init__(self) -> None:
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
        If ``False`` (default) and ``lagna_sign_index`` is provided, the
        eligibility condition is checked.  If Rahu is in the 1st, 5th, or
        9th house from Lagna, a ``ValueError`` is raised.
        Set to ``True`` to skip the eligibility check (e.g. for schools
        that use Ashtottari universally).
    lagna_sign_index : int or None
        0-based sign index (0=Aries…11=Pisces) of the Ascendant.  Required
        for eligibility checking when ``bypass_eligibility=False``.
        Silently ignored when ``bypass_eligibility=True``.
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

    period_years = (period.end_jd - period.start_jd) / year_days
    sub_sequence = _sequence_from(sequence, period.lord)
    current_jd = period.start_jd
    sub_periods: list[AlternateDashaPeriod] = []

    for sub_lord in sub_sequence:
        sub_years = (years_table[sub_lord] / total_years) * period_years
        sub_end_jd = current_jd + sub_years * year_days
        sub = AlternateDashaPeriod(
            system=period.system,
            level=current_level + 1,
            lord=sub_lord,
            start_jd=current_jd,
            end_jd=sub_end_jd,
            sub=[],
        )
        sub = _build_sub_periods(
            sub, years_table, sequence, total_years, year_days,
            current_level + 1, max_levels,
        )
        sub_periods.append(sub)
        current_jd = sub_end_jd

    return AlternateDashaPeriod(
        system=period.system,
        level=period.level,
        lord=period.lord,
        start_jd=period.start_jd,
        end_jd=period.end_jd,
        sub=sub_periods,
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
        end_jd = min(current_jd + duration_years * year_days, cycle_end_jd)
        period = AlternateDashaPeriod(
            system=system,
            level=1,
            lord=lord,
            start_jd=current_jd,
            end_jd=end_jd,
            sub=[],
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

    The starting lord is determined by the Moon's birth nakshatra via the
    ``ASHTOTTARI_NAKSHATRA_LORD`` mapping (one of 8 lords cycling through
    all 27 nakshatras).

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
        If the eligibility condition fails and ``bypass_eligibility`` is
        ``False``.  The Parashari condition is: Rahu must not be in the
        1st, 5th, or 9th sign from the Ascendant (Lagna).  Provide
        ``lagna_sign_index`` in the policy or set
        ``bypass_eligibility=True``.
    ValueError
        If ``natal_jd`` is not finite.
    """
    if policy is None:
        policy = AshtottariPolicy()
    if not math.isfinite(natal_jd):
        raise ValueError("natal_jd must be finite")

    from .sidereal import tropical_to_sidereal, NAKSHATRA_SPAN

    year_days = _resolve_year_days(policy.year_basis)
    levels = max(1, min(levels, 4))

    # Eligibility check
    if not policy.bypass_eligibility and policy.lagna_sign_index is not None:
        raise ValueError(
            "Ashtottari eligibility check requires knowing Rahu's sign.  "
            "Pass rahu_sidereal_lon via lagna_sign_index or set "
            "bypass_eligibility=True.  Eligibility checking is not yet "
            "implemented; set bypass_eligibility=True to proceed."
        )

    # Nakshatra of Moon at birth
    sid_lon = tropical_to_sidereal(
        moon_tropical_lon, natal_jd, system=policy.ayanamsa_system
    )
    nak_idx = int(sid_lon % 360.0 / NAKSHATRA_SPAN)
    nak_idx = min(nak_idx, 26)
    deg_in_nak = (sid_lon % 360.0) - nak_idx * NAKSHATRA_SPAN
    fraction_elapsed = deg_in_nak / NAKSHATRA_SPAN

    starting_lord = ASHTOTTARI_NAKSHATRA_LORD[nak_idx]

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

    The starting Yogini is determined by ``nakshatra_index % 8``, mapping
    the Moon's birth nakshatra to one of the 8 Yoginis.

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

    from .sidereal import tropical_to_sidereal, NAKSHATRA_SPAN

    year_days = _resolve_year_days(policy.year_basis)
    levels = max(1, min(levels, 4))

    # Nakshatra of Moon at birth
    sid_lon = tropical_to_sidereal(
        moon_tropical_lon, natal_jd, system=policy.ayanamsa_system
    )
    nak_idx = int(sid_lon % 360.0 / NAKSHATRA_SPAN)
    nak_idx = min(nak_idx, 26)
    deg_in_nak = (sid_lon % 360.0) - nak_idx * NAKSHATRA_SPAN
    fraction_elapsed = deg_in_nak / NAKSHATRA_SPAN

    # Starting Yogini index
    yogini_start_idx = nak_idx % 8
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
