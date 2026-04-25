"""
Moira — Panchanga Engine
=========================

Archetype: Engine

Purpose
-------
Computes the five classical elements of the Vedic Panchanga (almanac) for
a given Julian date and Sun/Moon tropical longitudes.  The five elements
are:

  Tithi    — lunar day (1–30); each Tithi spans 12° of Moon–Sun elongation.
  Vara     — weekday and its planetary lord (Sunday-origin Vedic convention).
  Nakshatra — Moon's lunar mansion (delegates to ``moira.sidereal``).
  Yoga     — combined Sun+Moon longitude divided into 27 × 13.33° spans.
  Karana   — half-Tithi (6° spans); 11 types, 60 per month.

All five elements return the instant value at the supplied Julian date and
also the degrees elapsed within the current span and the degrees remaining
to the next span boundary, enabling muhurta "time until next X" use.

Tradition and sources
---------------------
Parashara, "Brihat Parashara Hora Shastra" (BPHS), Muhurta Panchanga
chapters.  Varahamihira, "Brihat Samhita", Ch. 98–104 (Muhurta).
Sripati, "Ratnamala".  The formulae and name lists are cross-checked
against Jhora (Jagannatha Hora) and Kala software for known dates.

Limitation — Vara boundary
---------------------------
The Vedic day (Vara) begins at local sunrise, not at midnight.  This
implementation uses the astronomical Julian date directly, so the Vara
may disagree with strict Vedic reckoning near midnight if local sunrise
has not yet occurred.  A sunrise-corrected Vara is a future policy
extension.  The ``vara_lord`` returned here is the astronomically correct
weekday lord at the JD instant supplied by the caller.

Limitation — Yoga precision
----------------------------
Yoga computation uses true (osculating) planetary positions.  With a very
fast Moon, a Yoga window of 13.33° can theoretically be traversed within a
single calendar day, causing one Yoga to be "skipped."  This is physically
correct and consistent with Moira's truth-first mandate.

Boundary declaration
--------------------
Owns: Tithi, Vara, Yoga, Karana arithmetic and name tables, solar
    sidereal Sankranti search, the ``PanchangaElement``,
    ``PanchangaResult``, and ``SankrantiResult`` result vessels.
Delegates: Nakshatra computation to ``moira.sidereal.nakshatra_of``,
         ayanamsa conversion to ``moira.sidereal.tropical_to_sidereal``,
         tropical solar longitude lookup to ``moira.planets.sun_longitude``.

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required.  No database access.  ``moira.sidereal`` is
imported at call time (not at module load).

Constitutional phase
--------------------
Phase 12 — Public API Curation.  All twelve phases complete.

Public surface
--------------
``TithiPaksha``              — string constants for the two Tithi fortnights.
``YogaClass``                — string constants for Yoga auspiciousness category.
``KaranaType``               — string constants for Karana type (movable / fixed).
``VaraLordType``             — structural category constants for Vara lords.
``PanchangaPolicy``          — policy dataclass for Panchanga computation.
``TITHI_NAMES``              — 30 Tithi names (Pratipada … Amavasya).
``YOGA_NAMES``               — 27 Yoga names (Vishkumbha … Vaidhriti).
``KARANA_NAMES``             — 11 Karana names.
``VARA_LORDS``               — 7 weekday planetary lords (Sunday-origin).
``VARA_NAMES``               — 7 Vedic weekday names (Sunday-origin).
``RASHI_NAMES``              — 12 Sanskrit sign names (Mesha … Meena).
``PanchangaElement``         — immutable vessel for one Panchanga element.
``PanchangaResult``          — immutable vessel for the full five-element result.
``SankrantiResult``          — immutable vessel for one solar sidereal ingress.
``TithiConditionProfile``    — integrated condition profile for the Tithi element.
``PanchangaProfile``         — aggregate intelligence profile for a full Panchanga.
``panchanga_at``             — compute all five elements for a JD and planet lons.
``sankranti_at``             — find solar sidereal rashi ingresses in a JD window.
``tithi_condition_profile``  — build a TithiConditionProfile from a PanchangaResult.
``panchanga_profile``        — build a PanchangaProfile from a PanchangaResult.
``validate_panchanga_output`` — validate structural invariants of a PanchangaResult.
"""

import math
from dataclasses import dataclass

__all__ = [
    # Phase 2 — Classification
    "TithiPaksha",
    "YogaClass",
    "KaranaType",
    "VaraLordType",
    # Phase 4 — Policy
    "PanchangaPolicy",
    # Name tables
    "TITHI_NAMES",
    "YOGA_NAMES",
    "KARANA_NAMES",
    "VARA_LORDS",
    "VARA_NAMES",
    "RASHI_NAMES",
    # Phase 1 — Truth Preservation
    "PanchangaElement",
    "PanchangaResult",
    "SankrantiResult",
    # Phase 7 — Integrated Local Condition
    "TithiConditionProfile",
    # Phase 8 — Aggregate Intelligence
    "PanchangaProfile",
    # Functions
    "panchanga_at",
    "sankranti_at",
    "tithi_condition_profile",
    "panchanga_profile",
    "validate_panchanga_output",
]

# ---------------------------------------------------------------------------
# Name tables
# ---------------------------------------------------------------------------

TITHI_NAMES: list[str] = [
    'Pratipada', 'Dvitiya', 'Tritiya', 'Chaturthi', 'Panchami',
    'Shashthi', 'Saptami', 'Ashtami', 'Navami', 'Dashami',
    'Ekadashi', 'Dwadashi', 'Trayodashi', 'Chaturdashi', 'Purnima',
    'Pratipada', 'Dvitiya', 'Tritiya', 'Chaturthi', 'Panchami',
    'Shashthi', 'Saptami', 'Ashtami', 'Navami', 'Dashami',
    'Ekadashi', 'Dwadashi', 'Trayodashi', 'Chaturdashi', 'Amavasya',
]
"""
30 Tithi names.  Indices 1–15 are Shukla Paksha (waxing, bright fortnight);
indices 16–30 are Krishna Paksha (waning, dark fortnight).  Index 15
(Purnima, Full Moon) and index 30 (Amavasya, New Moon) are the fortnight
endpoints.
"""

YOGA_NAMES: list[str] = [
    'Vishkumbha', 'Priti', 'Ayushman', 'Saubhagya', 'Shobhana',
    'Atiganda', 'Sukarma', 'Dhriti', 'Shula', 'Ganda',
    'Vriddhi', 'Dhruva', 'Vyaghata', 'Harshana', 'Vajra',
    'Siddhi', 'Vyatipata', 'Variyan', 'Parigha', 'Shiva',
    'Siddha', 'Sadhya', 'Shubha', 'Shukla', 'Brahma',
    'Indra', 'Vaidhriti',
]
"""
27 Yoga names.  Yogas 6 (Atiganda), 9 (Shula), 10 (Ganda), 17 (Vyatipata),
and 27 (Vaidhriti) are traditionally inauspicious (Ashubha Yoga).
"""

# 11 Karana names — 7 movable, 4 fixed
_MOVABLE_KARANAS: tuple[str, ...] = (
    'Bava', 'Balava', 'Kaulava', 'Taitila', 'Gara', 'Vanija', 'Vishti',
)
_FIXED_KARANAS: tuple[str, ...] = (
    'Kimstughna', 'Shakuni', 'Chatushpada', 'Naga',
)
KARANA_NAMES: list[str] = list(_MOVABLE_KARANAS) + list(_FIXED_KARANAS)
"""
11 Karana names: 7 movable (Bava … Vishti) and 4 fixed (Kimstughna,
Shakuni, Chatushpada, Naga).
"""

# Vedic weekday lords and names — Sunday-origin (index 0 = Sunday)
VARA_LORDS: list[str] = ['Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn']
VARA_NAMES: list[str] = ['Ravivara', 'Somavara', 'Mangalavara', 'Budhavara',
                          'Guruvara', 'Shukravara', 'Shanivara']
RASHI_NAMES: list[str] = [
    'Mesha', 'Vrishabha', 'Mithuna', 'Karka', 'Simha', 'Kanya',
    'Tula', 'Vrischika', 'Dhanu', 'Makara', 'Kumbha', 'Meena',
]

# Yoga span in degrees
_YOGA_SPAN: float = 360.0 / 27   # ≈ 13.3333°
_RASHI_SPAN: float = 30.0
_SANKRANTI_SCAN_STEP_DAYS: float = 1.0


# ---------------------------------------------------------------------------
# Phase 2 — Classification constants
# ---------------------------------------------------------------------------

class TithiPaksha:
    """String constants for the two Tithi fortnights.

    Shukla Paksha (bright / waxing) covers Tithis 1–15 (indices 0–14).
    Krishna Paksha (dark / waning) covers Tithis 16–30 (indices 15–29).
    """
    SHUKLA  = 'shukla'   # waxing / bright fortnight
    KRISHNA = 'krishna'  # waning / dark fortnight


class YogaClass:
    """Auspiciousness classification for Nitya Yoga.

    Five Yogas are traditionally inauspicious (Ashubha Yoga) per Parashari
    canon: Atiganda (6), Shula (9), Ganda (10), Vyatipata (17), and
    Vaidhriti (27), stored in ``_ASHUBHA_YOGA_INDICES`` as 0-based indices.
    All others are classed as auspicious.
    """
    AUSPICIOUS   = 'auspicious'
    INAUSPICIOUS = 'inauspicious'


class KaranaType:
    """Type classification for a Karana.

    Seven Karanas are Movable (Chara): Bava, Balava, Kaulava, Taitila,
    Gara, Vanija, Vishti — cycling through positions 1–56.
    Four are Fixed (Sthira): Kimstughna (position 0), Shakuni (57),
    Chatushpada (58), Naga (59).
    """
    MOVABLE = 'movable'
    FIXED   = 'fixed'


class VaraLordType:
    """Structural category constants for Vara (weekday) lords.

    Mirrors ``DashaLordType`` in ``moira.dasha`` and ``KarakaPlanetType``
    in ``moira.jaimini`` for cross-subsystem consistency.  Ketu is never
    a Vara lord.
    """
    LUMINARY = 'luminary'   # Sun, Moon
    INNER    = 'inner'      # Mercury, Venus, Mars
    OUTER    = 'outer'      # Jupiter, Saturn


# Inauspicious Yoga indices (0-based)
_ASHUBHA_YOGA_INDICES: frozenset[int] = frozenset({5, 8, 9, 16, 26})
# Atiganda(5), Shula(8), Ganda(9), Vyatipata(16), Vaidhriti(26)

# Vara lord type lookup
_VARA_LORD_TYPE: dict[str, str] = {
    'Sun':     VaraLordType.LUMINARY,
    'Moon':    VaraLordType.LUMINARY,
    'Mars':    VaraLordType.INNER,
    'Mercury': VaraLordType.INNER,
    'Venus':   VaraLordType.INNER,
    'Jupiter': VaraLordType.OUTER,
    'Saturn':  VaraLordType.OUTER,
}


# ---------------------------------------------------------------------------
# Result vessels
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PanchangaElement:
    """
    Immutable vessel for one of the five Panchanga elements.

    Attributes
    ----------
    name : str
        The name of the current division within the element (e.g. 'Dvitiya'
        for the second Tithi, 'Vishkumbha' for the first Yoga, 'Bava' for
        the first movable Karana).
    index : int
        0-based index within the element's cycle.
    number : int
        1-based number (``index + 1``), matching traditional Jyotish
        notation.
    degrees_elapsed : float
        Degrees elapsed within the current span at the supplied instant.
    degrees_remaining : float
        Degrees remaining until the next span boundary.
    """

    name: str
    index: int
    number: int
    degrees_elapsed: float
    degrees_remaining: float

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError(
                f"PanchangaElement.index must be >= 0, got {self.index}"
            )
        if self.number != self.index + 1:
            raise ValueError(
                f"PanchangaElement.number must equal index+1 "
                f"({self.index + 1}), got {self.number}"
            )
        if self.degrees_elapsed < 0.0:
            raise ValueError(
                f"PanchangaElement.degrees_elapsed must be >= 0, "
                f"got {self.degrees_elapsed}"
            )
        if self.degrees_remaining < 0.0:
            raise ValueError(
                f"PanchangaElement.degrees_remaining must be >= 0, "
                f"got {self.degrees_remaining}"
            )

    # --- Phase 3 — Inspectability ------------------------------------------

    @property
    def span(self) -> float:
        """Total arc span of this element type: ``degrees_elapsed + degrees_remaining``.

        Returns 0.0 for the Vara element (which has no degree span).
        """
        return self.degrees_elapsed + self.degrees_remaining

    @property
    def fraction_elapsed(self) -> float:
        """Fraction of the current span already elapsed, in [0.0, 1.0].

        Returns 0.0 when the span is zero (e.g. for the Vara element).
        """
        s = self.span
        if s == 0.0:
            return 0.0
        return self.degrees_elapsed / s


@dataclass(frozen=True, slots=True)
class PanchangaResult:
    """
    Immutable result vessel for the complete Panchanga at one instant.

    Attributes
    ----------
    jd : float
        The Julian date (UT) of the computation.
    tithi : PanchangaElement
        Lunar day element (1–30; span = 12°).
    vara : PanchangaElement
        Weekday element.  ``degrees_elapsed`` and ``degrees_remaining`` are
        0.0 — Vara is time-based (sunrise to sunrise), not degree-based.
    vara_lord : str
        Planetary lord of the current Vedic weekday.
    nakshatra : object
        ``NakshatraPosition`` from ``moira.sidereal`` for the Moon.
    yoga : PanchangaElement
        Nitya Yoga element (1–27; span = 360°/27 ≈ 13.33°).
    karana : PanchangaElement
        Half-Tithi element (1–60 across a month; span = 6°).
    ayanamsa_system : str
        The ayanamsa system used for sidereal conversion.
    """

    jd: float
    tithi: PanchangaElement
    vara: PanchangaElement
    vara_lord: str
    nakshatra: object           # NakshatraPosition (avoids circular typing)
    yoga: PanchangaElement
    karana: PanchangaElement
    ayanamsa_system: str

    def __post_init__(self) -> None:
        import math
        if not math.isfinite(self.jd):
            raise ValueError(
                f"PanchangaResult.jd must be finite, got {self.jd!r}"
            )
        if not self.ayanamsa_system:
            raise ValueError("PanchangaResult.ayanamsa_system must be non-empty")
        if not (0 <= self.tithi.index <= 29):
            raise ValueError(
                f"tithi.index must be in [0, 29], got {self.tithi.index}"
            )
        if not (0 <= self.yoga.index <= 26):
            raise ValueError(
                f"yoga.index must be in [0, 26], got {self.yoga.index}"
            )
        if not (0 <= self.karana.index <= 59):
            raise ValueError(
                f"karana.index must be in [0, 59], got {self.karana.index}"
            )
        if not (0 <= self.vara.index <= 6):
            raise ValueError(
                f"vara.index must be in [0, 6], got {self.vara.index}"
            )
        if self.vara_lord not in VARA_LORDS:
            raise ValueError(
                f"vara_lord {self.vara_lord!r} is not a valid Vara lord"
            )

    # --- Phase 3 — Inspectability ------------------------------------------

    @property
    def is_dark_fortnight(self) -> bool:
        """``True`` when the current Tithi is in Krishna Paksha (dark / waning).

        Krishna Paksha covers Tithis 16–30 (``tithi.index`` 15–29).
        """
        return self.tithi.index >= 15

    @property
    def is_purnima(self) -> bool:
        """``True`` when the current Tithi is Purnima (Full Moon, index 14)."""
        return self.tithi.index == 14

    @property
    def is_amavasya(self) -> bool:
        """``True`` when the current Tithi is Amavasya (New Moon, index 29)."""
        return self.tithi.index == 29

    @property
    def is_auspicious_yoga(self) -> bool:
        """``True`` when the current Yoga is not one of the five Ashubha Yogas."""
        return self.yoga.index not in _ASHUBHA_YOGA_INDICES


@dataclass(frozen=True, slots=True)
class SankrantiResult:
    """Immutable witness of one sidereal solar sign ingress."""

    jd: float
    rashi_index: int
    rashi_name: str
    ayanamsa_system: str


# ---------------------------------------------------------------------------
# Phase 4 — Policy
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PanchangaPolicy:
    """Policy surface for Panchanga computation.

    Attributes
    ----------
    ayanamsa_system : str
        Ayanamsa system name passed to ``moira.sidereal``.  Any system
        accepted by ``tropical_to_sidereal`` is valid.  Defaults to Lahiri
        (Indian national standard).
    """
    ayanamsa_system: str = 'Lahiri'

    def __post_init__(self) -> None:
        if not self.ayanamsa_system:
            raise ValueError(
                "PanchangaPolicy.ayanamsa_system must be a non-empty string"
            )


# ---------------------------------------------------------------------------
# Phase 7 — Integrated Local Condition
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class TithiConditionProfile:
    """Integrated condition profile for the Tithi element.

    Enriches the raw Tithi ``PanchangaElement`` with doctrinal
    classification (paksha, special-day flags).  Built from a
    ``PanchangaResult`` via :func:`tithi_condition_profile`.

    Attributes
    ----------
    tithi_name : str
        Name of the current Tithi (e.g. ``'Chaturdashi'``).
    tithi_index : int
        0-based index in [0, 29].
    tithi_number : int
        1-based number in [1, 30].
    paksha : str
        ``TithiPaksha.SHUKLA`` (indices 0\u201314) or
        ``TithiPaksha.KRISHNA`` (indices 15\u201329).
    is_purnima : bool
        ``True`` when ``tithi_index == 14`` (Full Moon).
    is_amavasya : bool
        ``True`` when ``tithi_index == 29`` (New Moon).
    degrees_elapsed : float
        Degrees elapsed within the current Tithi span.
    degrees_remaining : float
        Degrees remaining until the next Tithi boundary.
    """

    tithi_name: str
    tithi_index: int
    tithi_number: int
    paksha: str
    is_purnima: bool
    is_amavasya: bool
    degrees_elapsed: float
    degrees_remaining: float


# ---------------------------------------------------------------------------
# Phase 8 — Aggregate Intelligence
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PanchangaProfile:
    """Aggregate intelligence profile for a complete Panchanga.

    Derived from a ``PanchangaResult`` via :func:`panchanga_profile`.
    Summarises the doctrinal condition of all five elements at a glance.

    Attributes
    ----------
    jd : float
        The Julian date of the computation.
    paksha : str
        ``TithiPaksha`` constant for the current fortnight.
    is_purnima : bool
        ``True`` on the Full Moon Tithi.
    is_amavasya : bool
        ``True`` on the New Moon Tithi.
    yoga_class : str
        ``YogaClass.AUSPICIOUS`` or ``YogaClass.INAUSPICIOUS``.
    karana_type : str
        ``KaranaType.MOVABLE`` or ``KaranaType.FIXED``.
    vara_lord : str
        The Vara lord planet name.
    vara_lord_type : str
        ``VaraLordType`` classification of the Vara lord.
    ayanamsa_system : str
        The ayanamsa system used for this computation.
    """

    jd: float
    paksha: str
    is_purnima: bool
    is_amavasya: bool
    yoga_class: str
    karana_type: str
    vara_lord: str
    vara_lord_type: str
    ayanamsa_system: str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _vedic_weekday(jd: float) -> int:
    """
    Return the Vedic weekday index (0 = Sunday) for a Julian Day.

    The formula ``int(jd + 1.5) % 7 == 0`` corresponds to Sunday in the
    standard Vedic reckoning based on JD integer boundaries.
    """
    return int(jd + 1.5) % 7


def _karana_name(karana_index: int) -> str:
    """
    Return the Karana name for a 0-based position (0–59) within the month.

    Mapping (Parashari):
      0          → Kimstughna  (fixed, 1st half of Pratipada)
      1–56       → movable Karanas cycling Bava … Vishti
      57         → Shakuni     (fixed)
      58         → Chatushpada (fixed)
      59         → Naga        (fixed)
    """
    if karana_index == 0:
        return 'Kimstughna'
    if karana_index == 57:
        return 'Shakuni'
    if karana_index == 58:
        return 'Chatushpada'
    if karana_index == 59:
        return 'Naga'
    return _MOVABLE_KARANAS[(karana_index - 1) % 7]


def _make_element(
    name: str,
    index: int,
    span: float,
    deg_elapsed: float,
) -> PanchangaElement:
    """Construct a PanchangaElement from span arithmetic."""
    return PanchangaElement(
        name=name,
        index=index,
        number=index + 1,
        degrees_elapsed=deg_elapsed,
        degrees_remaining=span - deg_elapsed,
    )


def _normalize_ayanamsa_system_name(ayanamsa_system: str) -> str:
    """Resolve uppercase ayanamsa enum-style names to canonical sidereal labels."""
    from .sidereal import Ayanamsa

    if hasattr(Ayanamsa, ayanamsa_system):
        value = getattr(Ayanamsa, ayanamsa_system)
        if isinstance(value, str):
            return value
    return ayanamsa_system


def _sidereal_solar_longitude(jd: float, ayanamsa_system: str, reader: object) -> float:
    """Return the Sun's apparent geocentric sidereal longitude in degrees."""
    from .planets import sun_longitude
    from .sidereal import tropical_to_sidereal

    sun_tropical_lon = sun_longitude(jd, reader=reader)
    return tropical_to_sidereal(sun_tropical_lon, jd, system=ayanamsa_system)


def _signed_longitude_residual(longitude: float, target: float) -> float:
    """Return the shortest signed angular residual from longitude to target."""
    return (longitude - target + 180.0) % 360.0 - 180.0


def _boundary_rashi_index(longitude: float, tolerance_deg: float) -> int | None:
    """Return the entered rashi index when longitude lies on a sign boundary."""
    remainder = longitude % _RASHI_SPAN
    if remainder <= tolerance_deg or (_RASHI_SPAN - remainder) <= tolerance_deg:
        return int(round(longitude / _RASHI_SPAN)) % len(RASHI_NAMES)
    return None


def _bisect_sankranti(
    left_jd: float,
    right_jd: float,
    target_longitude: float,
    ayanamsa_system: str,
    tolerance_deg: float,
    reader: object,
) -> float:
    """Bisect a bracketed solar sidereal boundary crossing to angular tolerance."""
    target_longitude %= 360.0
    left_residual = _signed_longitude_residual(
        _sidereal_solar_longitude(left_jd, ayanamsa_system, reader),
        target_longitude,
    )
    if abs(left_residual) <= tolerance_deg:
        return left_jd

    right_residual = _signed_longitude_residual(
        _sidereal_solar_longitude(right_jd, ayanamsa_system, reader),
        target_longitude,
    )
    if abs(right_residual) <= tolerance_deg:
        return right_jd
    if left_residual * right_residual > 0.0:
        raise ValueError("sankranti_at requires a bracketing interval")

    for _ in range(64):
        mid_jd = (left_jd + right_jd) / 2.0
        mid_residual = _signed_longitude_residual(
            _sidereal_solar_longitude(mid_jd, ayanamsa_system, reader),
            target_longitude,
        )
        if abs(mid_residual) <= tolerance_deg:
            return mid_jd
        if left_residual * mid_residual <= 0.0:
            right_jd = mid_jd
        else:
            left_jd = mid_jd
            left_residual = mid_residual

    return (left_jd + right_jd) / 2.0


# ---------------------------------------------------------------------------
# Public function
# ---------------------------------------------------------------------------

def panchanga_at(
    sun_tropical_lon: float,
    moon_tropical_lon: float,
    jd: float,
    ayanamsa_system: str = 'Lahiri',
    policy: PanchangaPolicy | None = None,
) -> PanchangaResult:
    """
    Compute the five Panchanga elements at a given Julian date.

    All five elements reflect the instantaneous state at ``jd``.  No
    sunrise correction is applied to the Vara; see the module-level
    limitation note.

    Parameters
    ----------
    sun_tropical_lon : float
        Tropical ecliptic longitude of the Sun in degrees.
    moon_tropical_lon : float
        Tropical ecliptic longitude of the Moon in degrees.
    jd : float
        Julian date (UT) of the observation instant.
    ayanamsa_system : str
        Ayanamsa system name for sidereal conversion.  Any system accepted
        by ``moira.sidereal.tropical_to_sidereal`` is valid.  Defaults to
        Lahiri (Indian national standard).  Ignored when ``policy`` is
        supplied.
    policy : PanchangaPolicy or None
        Optional policy vessel.  When provided,
        ``policy.ayanamsa_system`` overrides the ``ayanamsa_system``
        argument.

    Returns
    -------
    PanchangaResult

    Examples
    --------
    >>> from moira.julian import julian_day
    >>> jd = julian_day(2000, 1, 1, 12.0)
    >>> from moira.planets import planet_longitudes_at  # hypothetical caller usage
    >>> result = panchanga_at(280.5, 35.0, jd)
    >>> result.tithi.name
    'Chaturdashi'
    """
    if policy is not None:
        ayanamsa_system = policy.ayanamsa_system
    from .sidereal import tropical_to_sidereal, nakshatra_of

    sun_sid  = tropical_to_sidereal(sun_tropical_lon,  jd, system=ayanamsa_system)
    moon_sid = tropical_to_sidereal(moon_tropical_lon, jd, system=ayanamsa_system)

    # ------------------------------------------------------------------
    # Tithi  (Moon–Sun elongation / 12°)
    # ------------------------------------------------------------------
    diff_ms = (moon_sid - sun_sid) % 360.0
    tithi_idx = int(diff_ms / 12.0)                # 0–29
    tithi_idx = min(tithi_idx, 29)                 # floating-point safety at 360°
    deg_in_tithi = diff_ms - tithi_idx * 12.0
    tithi = _make_element(TITHI_NAMES[tithi_idx], tithi_idx, 12.0, deg_in_tithi)

    # ------------------------------------------------------------------
    # Vara  (weekday lord, time-based — degrees are not applicable)
    # ------------------------------------------------------------------
    vara_idx  = _vedic_weekday(jd)
    vara_name = VARA_NAMES[vara_idx]
    vara_lord = VARA_LORDS[vara_idx]
    vara = PanchangaElement(
        name=vara_name,
        index=vara_idx,
        number=vara_idx + 1,
        degrees_elapsed=0.0,
        degrees_remaining=0.0,
    )

    # ------------------------------------------------------------------
    # Nakshatra  (delegates entirely to moira.sidereal)
    # ------------------------------------------------------------------
    naks = nakshatra_of(moon_tropical_lon, jd, ayanamsa_system=ayanamsa_system)

    # ------------------------------------------------------------------
    # Yoga  ((Sun + Moon sidereal sum) / (360/27))
    # ------------------------------------------------------------------
    yoga_sum = (sun_sid + moon_sid) % 360.0
    yoga_idx = int(yoga_sum / _YOGA_SPAN)          # 0–26
    yoga_idx = min(yoga_idx, 26)                   # floating-point safety
    deg_in_yoga = yoga_sum - yoga_idx * _YOGA_SPAN
    yoga = _make_element(YOGA_NAMES[yoga_idx], yoga_idx, _YOGA_SPAN, deg_in_yoga)

    # ------------------------------------------------------------------
    # Karana  (Moon–Sun elongation / 6°; 60 per month)
    # ------------------------------------------------------------------
    karana_idx = int(diff_ms / 6.0)                # 0–59
    karana_idx = min(karana_idx, 59)               # floating-point safety
    deg_in_karana = diff_ms - karana_idx * 6.0
    karana = _make_element(_karana_name(karana_idx), karana_idx, 6.0, deg_in_karana)

    return PanchangaResult(
        jd=jd,
        tithi=tithi,
        vara=vara,
        vara_lord=vara_lord,
        nakshatra=naks,
        yoga=yoga,
        karana=karana,
        ayanamsa_system=ayanamsa_system,
    )


def sankranti_at(
    start_jd: float,
    end_jd: float,
    ayanamsa_system: str = 'LAHIRI',
    tolerance_deg: float = 1e-6,
) -> list[SankrantiResult]:
    """Find all solar sidereal rashi ingresses in ``[start_jd, end_jd]``.

    The search samples the Sun's apparent geocentric sidereal longitude in
    roughly one-day steps, detects each 30° sign-boundary crossing in the
    sampled interval, and refines the exact ingress instant by bisection to
    the requested angular tolerance.
    """
    if end_jd < start_jd:
        raise ValueError("end_jd must be greater than or equal to start_jd")
    if tolerance_deg <= 0.0:
        raise ValueError("tolerance_deg must be positive")

    ayanamsa_system = _normalize_ayanamsa_system_name(ayanamsa_system)

    from .spk_reader import get_reader

    reader = get_reader()
    if start_jd == end_jd:
        longitude = _sidereal_solar_longitude(start_jd, ayanamsa_system, reader)
        rashi_index = _boundary_rashi_index(longitude, tolerance_deg)
        if rashi_index is None:
            return []
        return [
            SankrantiResult(
                jd=start_jd,
                rashi_index=rashi_index,
                rashi_name=RASHI_NAMES[rashi_index],
                ayanamsa_system=ayanamsa_system,
            )
        ]

    jd_points: list[float] = [start_jd]
    while jd_points[-1] < end_jd:
        jd_points.append(min(jd_points[-1] + _SANKRANTI_SCAN_STEP_DAYS, end_jd))

    wrapped_longitudes = [
        _sidereal_solar_longitude(jd, ayanamsa_system, reader)
        for jd in jd_points
    ]
    unwrapped_longitudes: list[float] = [wrapped_longitudes[0]]
    for longitude in wrapped_longitudes[1:]:
        while longitude < unwrapped_longitudes[-1]:
            longitude += 360.0
        unwrapped_longitudes.append(longitude)

    events: list[SankrantiResult] = []
    for index in range(len(jd_points) - 1):
        left_jd = jd_points[index]
        right_jd = jd_points[index + 1]
        left_unwrapped = unwrapped_longitudes[index]
        right_unwrapped = unwrapped_longitudes[index + 1]

        if index == 0:
            first_boundary = math.ceil((left_unwrapped - tolerance_deg) / _RASHI_SPAN)
        else:
            first_boundary = math.ceil((left_unwrapped + tolerance_deg) / _RASHI_SPAN)
        last_boundary = math.floor((right_unwrapped + tolerance_deg) / _RASHI_SPAN)

        for boundary_index in range(first_boundary, last_boundary + 1):
            boundary_longitude = boundary_index * _RASHI_SPAN
            target_longitude = boundary_longitude % 360.0

            if abs(left_unwrapped - boundary_longitude) <= tolerance_deg:
                ingress_jd = left_jd
            elif abs(right_unwrapped - boundary_longitude) <= tolerance_deg:
                ingress_jd = right_jd
            else:
                ingress_jd = _bisect_sankranti(
                    left_jd,
                    right_jd,
                    target_longitude,
                    ayanamsa_system,
                    tolerance_deg,
                    reader,
                )

            rashi_index = boundary_index % len(RASHI_NAMES)
            events.append(
                SankrantiResult(
                    jd=ingress_jd,
                    rashi_index=rashi_index,
                    rashi_name=RASHI_NAMES[rashi_index],
                    ayanamsa_system=ayanamsa_system,
                )
            )

    return events


# ---------------------------------------------------------------------------
# Phase 7 — Condition profile
# ---------------------------------------------------------------------------

def tithi_condition_profile(result: PanchangaResult) -> TithiConditionProfile:
    """Build a :class:`TithiConditionProfile` from a :class:`PanchangaResult`.

    Parameters
    ----------
    result : PanchangaResult

    Returns
    -------
    TithiConditionProfile
    """
    idx = result.tithi.index
    paksha = TithiPaksha.KRISHNA if idx >= 15 else TithiPaksha.SHUKLA
    return TithiConditionProfile(
        tithi_name=result.tithi.name,
        tithi_index=idx,
        tithi_number=result.tithi.number,
        paksha=paksha,
        is_purnima=(idx == 14),
        is_amavasya=(idx == 29),
        degrees_elapsed=result.tithi.degrees_elapsed,
        degrees_remaining=result.tithi.degrees_remaining,
    )


# ---------------------------------------------------------------------------
# Phase 8 — Aggregate function
# ---------------------------------------------------------------------------

def panchanga_profile(result: PanchangaResult) -> PanchangaProfile:
    """Build a :class:`PanchangaProfile` from a :class:`PanchangaResult`.

    Parameters
    ----------
    result : PanchangaResult

    Returns
    -------
    PanchangaProfile
    """
    idx = result.tithi.index
    paksha = TithiPaksha.KRISHNA if idx >= 15 else TithiPaksha.SHUKLA
    yoga_cls = (
        YogaClass.INAUSPICIOUS
        if result.yoga.index in _ASHUBHA_YOGA_INDICES
        else YogaClass.AUSPICIOUS
    )
    karana_type = (
        KaranaType.FIXED
        if result.karana.index in (0, 57, 58, 59)
        else KaranaType.MOVABLE
    )
    return PanchangaProfile(
        jd=result.jd,
        paksha=paksha,
        is_purnima=(idx == 14),
        is_amavasya=(idx == 29),
        yoga_class=yoga_cls,
        karana_type=karana_type,
        vara_lord=result.vara_lord,
        vara_lord_type=_VARA_LORD_TYPE[result.vara_lord],
        ayanamsa_system=result.ayanamsa_system,
    )


# ---------------------------------------------------------------------------
# Phase 10 — Full-subsystem hardening
# ---------------------------------------------------------------------------

def validate_panchanga_output(result: PanchangaResult) -> None:
    """Validate the structural invariants of a :class:`PanchangaResult`.

    Raises ``ValueError`` with a descriptive message if any invariant is
    violated.  Intended as a test harness and post-computation guard.

    Invariants checked
    ------------------
    - ``jd`` is finite.
    - ``ayanamsa_system`` is non-empty.
    - ``tithi.index`` ∈ [0, 29].
    - ``yoga.index`` ∈ [0, 26].
    - ``karana.index`` ∈ [0, 59].
    - ``vara.index`` ∈ [0, 6].
    - ``vara_lord`` is in ``VARA_LORDS``.
    - ``tithi.name`` matches ``TITHI_NAMES[tithi.index]``.
    - ``yoga.name`` matches ``YOGA_NAMES[yoga.index]``.
    - ``vara.name`` matches ``VARA_NAMES[vara.index]``.
    - ``karana.number == karana.index + 1``; same for tithi, yoga, vara.

    Parameters
    ----------
    result : PanchangaResult

    Raises
    ------
    ValueError
        On any invariant violation.
    """
    import math
    if not math.isfinite(result.jd):
        raise ValueError(f"jd must be finite, got {result.jd!r}")
    if not result.ayanamsa_system:
        raise ValueError("ayanamsa_system must be non-empty")
    if not (0 <= result.tithi.index <= 29):
        raise ValueError(f"tithi.index must be in [0, 29], got {result.tithi.index}")
    if not (0 <= result.yoga.index <= 26):
        raise ValueError(f"yoga.index must be in [0, 26], got {result.yoga.index}")
    if not (0 <= result.karana.index <= 59):
        raise ValueError(f"karana.index must be in [0, 59], got {result.karana.index}")
    if not (0 <= result.vara.index <= 6):
        raise ValueError(f"vara.index must be in [0, 6], got {result.vara.index}")
    if result.vara_lord not in VARA_LORDS:
        raise ValueError(
            f"vara_lord {result.vara_lord!r} is not in VARA_LORDS"
        )
    if result.tithi.name != TITHI_NAMES[result.tithi.index]:
        raise ValueError(
            f"tithi.name {result.tithi.name!r} does not match "
            f"TITHI_NAMES[{result.tithi.index}] = "
            f"{TITHI_NAMES[result.tithi.index]!r}"
        )
    if result.yoga.name != YOGA_NAMES[result.yoga.index]:
        raise ValueError(
            f"yoga.name {result.yoga.name!r} does not match "
            f"YOGA_NAMES[{result.yoga.index}] = "
            f"{YOGA_NAMES[result.yoga.index]!r}"
        )
    if result.vara.name != VARA_NAMES[result.vara.index]:
        raise ValueError(
            f"vara.name {result.vara.name!r} does not match "
            f"VARA_NAMES[{result.vara.index}] = "
            f"{VARA_NAMES[result.vara.index]!r}"
        )
    for label, element in (
        ('tithi', result.tithi),
        ('yoga', result.yoga),
        ('karana', result.karana),
        ('vara', result.vara),
    ):
        if element.number != element.index + 1:
            raise ValueError(
                f"{label}.number ({element.number}) != "
                f"{label}.index + 1 ({element.index + 1})"
            )
