"""
Moira — Decanates Engine
=========================

Archetype: Engine

Purpose
-------
Governs the three classical planetary decanate systems, mapping a tropical
or sidereal ecliptic longitude onto a 10° decan and its ruling planet.

Each system divides every zodiac sign into three equal 10° segments.  The
three systems differ in how they assign planetary rulership and which
zodiacal frame they operate in:

  Chaldean Face      — 36 planetary faces cycling through the 7 classical
                       planets in Chaldean order, starting with Mars at
                       Aries 0°.  Operates on tropical longitude.
                       (Also called "faces" or "planetary faces".)

  Triplicity Decan   — Each decan is ruled by the same-element sign in
                       natural zodiacal order (1st: own sign; 2nd: +4 signs;
                       3rd: +8 signs).  Operates on tropical longitude.
                       (Also called "triplicity decans" or "elemental decans".)

  Vedic Drekkana     — The same +4 / +8 elemental-triplicity arithmetic
                       applied to sidereal longitude (Parashari D3).
                       Requires a Julian date for ayanamsha correction.
                       Uses traditional 7-planet Vedic rulerships (no outer
                       planets).  (Also called "drekkana" or "D3".)

Tradition and sources
---------------------
Chaldean Faces:
    Agrippa, "Three Books of Occult Philosophy" (1531), Book II, Ch. 37.
    Picatrix (Ghāyat al-Ḥakīm, ~11th c.), Book I, Ch. 4.
    The 7-planet cycle (Mars → Sun → Venus → Mercury → Moon → Saturn →
    Jupiter) begins at Aries 0° and repeats every 7 decans across the 36.

Triplicity Decan:
    Dorotheus of Sidon, "Carmen Astrologicum" (~1st c. CE).
    Vettius Valens, "Anthology" (~2nd c. CE).
    Each sign's three decans are ruled by the signs of the same triplicity
    in natural zodiacal order, starting from the sign itself.

Vedic Drekkana (D3):
    Parashara, "Brihat Parashara Hora Shastra", Drekkana Adhyaya.
    Standard Parashari D3: 1st decan = same sign, 2nd = 5th sign from it
    (counting inclusively; same element, next zodiacal occurrence), 3rd =
    9th sign.  In zero-index arithmetic this is the same +4 / +8 progression
    used by the Western triplicity decan — the geometry is identical; the
    distinction lies in the sidereal zodiac frame and Vedic 7-planet
    rulerships.

Boundary declaration
--------------------
Owns: the Chaldean face cycle table, triplicity decan rulership arithmetic,
      Vedic drekkana computation (including ayanamsha delegation), and
      the ``DecanatePosition`` result vessel.
Delegates: tropical-to-sidereal conversion to ``moira.sidereal``,
           sign name and symbol lookup to ``moira.constants``.

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required.  No database access.  Vedic drekkana
computation requires a valid Julian date for ayanamsha correction.

Public surface
--------------
``DecanatePosition``  — immutable result vessel for a decanate computation.
``chaldean_face``     — map a tropical longitude to its Chaldean face.
``triplicity_decan``  — map a tropical longitude to its triplicity decan.
``vedic_drekkana``    — map a longitude to its Vedic drekkana, D3 (sidereal).
"""

import math
from dataclasses import dataclass

from .constants import SIGNS, SIGN_SYMBOLS

__all__ = [
    "DecanatePosition",
    "chaldean_face",
    "triplicity_decan",
    "vedic_drekkana",
]

# ---------------------------------------------------------------------------
# Chaldean face cycle
#
# 36 faces across 360°, each spanning 10°.  The 7 classical planets cycle
# starting from Mars at Aries 0°.  The sequence follows the order used in
# Agrippa and Picatrix: Mars, Sun, Venus, Mercury, Moon, Saturn, Jupiter.
#
# Verification:
#   face 0  (Aries   0–10°) → Mars        face 6  (Gemini  0–10°) → Jupiter
#   face 1  (Aries  10–20°) → Sun         face 7  (Gemini 10–20°) → Mars
#   face 2  (Aries  20–30°) → Venus       face 12 (Leo     0–10°) → Saturn
#   face 3  (Taurus  0–10°) → Mercury     face 33 (Pisces  0–10°) → Saturn
#   face 4  (Taurus 10–20°) → Moon        face 34 (Pisces 10–20°) → Jupiter
#   face 5  (Taurus 20–30°) → Saturn      face 35 (Pisces 20–30°) → Mars
# ---------------------------------------------------------------------------

_CHALDEAN_CYCLE: tuple[str, ...] = (
    'Mars', 'Sun', 'Venus', 'Mercury', 'Moon', 'Saturn', 'Jupiter',
)

# ---------------------------------------------------------------------------
# Traditional 7-planet sign rulerships
#
# Used by both Triplicity Decans (tropical) and Vedic Drekkanas (sidereal).
# Outer planets are excluded by doctrine: Scorpio = Mars, Aquarius = Saturn,
# Pisces = Jupiter.
# ---------------------------------------------------------------------------

_TRADITIONAL_RULERS: tuple[str, ...] = (
    'Mars',    # 0  Aries
    'Venus',   # 1  Taurus
    'Mercury', # 2  Gemini
    'Moon',    # 3  Cancer
    'Sun',     # 4  Leo
    'Mercury', # 5  Virgo
    'Venus',   # 6  Libra
    'Mars',    # 7  Scorpio
    'Jupiter', # 8  Sagittarius
    'Saturn',  # 9  Capricorn
    'Saturn',  # 10 Aquarius
    'Jupiter', # 11 Pisces
)


# ---------------------------------------------------------------------------
# Result vessel
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class DecanatePosition:
    """
    Immutable result vessel for a single decanate computation.

    All three decanate systems return this type.

    Attributes
    ----------
    system : str
        Which system produced this result.  One of ``'chaldean_face'``,
        ``'triplicity'``, or ``'vedic_drekkana'``.
    decan_number : int
        Position within the sign: 1 (0–10°), 2 (10–20°), or 3 (20–30°).
    ruling_planet : str
        The classical planet assigned to this decan under the given system.
        Always one of the 7 traditional planets (Moon, Mercury, Venus, Sun,
        Mars, Jupiter, Saturn).
    ruling_sign : str or None
        The zodiac sign whose ruler governs this decan.  ``None`` for the
        Chaldean face system, which assigns planets directly without a sign
        intermediary.  For triplicity and Vedic drekkana this is the same-
        element sign (own sign for decan 1, +4 signs for decan 2, +8 for
        decan 3).
    sign : str
        The zodiac sign the body occupies.
    sign_symbol : str
        Glyph symbol of the occupied sign.
    degree_in_decan : float
        Degrees elapsed within the current 10° decan span, in [0, 10).
    longitude_used : float
        The ecliptic longitude that was used for the computation, in
        [0, 360).  Tropical for Chaldean and triplicity; sidereal for
        Vedic drekkana.
    """

    system: str
    decan_number: int
    ruling_planet: str
    ruling_sign: str | None
    sign: str
    sign_symbol: str
    degree_in_decan: float
    longitude_used: float

    def __post_init__(self) -> None:
        if self.system not in {"chaldean_face", "triplicity", "vedic_drekkana"}:
            raise ValueError(f"DecanatePosition.system is invalid: {self.system!r}")
        if self.decan_number not in {1, 2, 3}:
            raise ValueError(
                f"DecanatePosition.decan_number must be in {{1, 2, 3}}, got {self.decan_number}"
            )
        if self.ruling_planet not in _CHALDEAN_CYCLE:
            raise ValueError(
                f"DecanatePosition.ruling_planet must be a traditional planet, got {self.ruling_planet!r}"
            )
        if self.ruling_sign is not None and self.ruling_sign not in SIGNS:
            raise ValueError(
                f"DecanatePosition.ruling_sign must be None or a zodiac sign, got {self.ruling_sign!r}"
            )
        if self.sign not in SIGNS:
            raise ValueError(f"DecanatePosition.sign must be a zodiac sign, got {self.sign!r}")
        if self.sign_symbol not in SIGN_SYMBOLS:
            raise ValueError(
                f"DecanatePosition.sign_symbol must be a zodiac symbol, got {self.sign_symbol!r}"
            )
        if not (0.0 <= self.degree_in_decan < 10.0):
            raise ValueError(
                "DecanatePosition.degree_in_decan must be in [0, 10), "
                f"got {self.degree_in_decan}"
            )
        if not math.isfinite(self.longitude_used) or not (0.0 <= self.longitude_used < 360.0):
            raise ValueError(
                "DecanatePosition.longitude_used must be finite and in [0, 360), "
                f"got {self.longitude_used}"
            )
        if self.system == "chaldean_face" and self.ruling_sign is not None:
            raise ValueError("Chaldean face results must have ruling_sign=None")
        if self.system != "chaldean_face" and self.ruling_sign is None:
            raise ValueError("Triplicity and Vedic drekkana results must include ruling_sign")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sign_components(longitude: float) -> tuple[int, str, str, int, float]:
    """
    Return (sign_index, sign_name, sign_symbol, decan_number, degree_in_decan)
    for a longitude in [0, 360).
    """
    lon = longitude % 360.0
    sign_idx = int(lon // 30)
    deg_in_sign = lon - sign_idx * 30.0
    decan_number = int(deg_in_sign // 10) + 1
    degree_in_decan = deg_in_sign - (decan_number - 1) * 10.0
    return sign_idx, SIGNS[sign_idx], SIGN_SYMBOLS[sign_idx], decan_number, degree_in_decan


def _triplicity_ruler(sign_idx: int, decan_number: int) -> tuple[str, str]:
    """
    Return (ruling_sign, ruling_planet) for a triplicity decan or Vedic drekkana.

    The ruling sign for decan k (1, 2, 3) is the sign reached by advancing
    (k-1)*4 positions forward from sign_idx in the zodiac, keeping within
    the same elemental triplicity.
    """
    ruling_sign_idx = (sign_idx + (decan_number - 1) * 4) % 12
    return SIGNS[ruling_sign_idx], _TRADITIONAL_RULERS[ruling_sign_idx]


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def chaldean_face(longitude: float) -> DecanatePosition:
    """
    Map a tropical ecliptic longitude to its Chaldean planetary face.

    The 36 faces are numbered 0–35 from Aries 0° and the 7 classical
    planets cycle (Mars, Sun, Venus, Mercury, Moon, Saturn, Jupiter)
    repeating across all 36.

    Parameters
    ----------
    longitude : float
        Tropical ecliptic longitude in degrees.  Any value is accepted;
        it is reduced to [0, 360) internally.

    Returns
    -------
    DecanatePosition
        ``ruling_sign`` is ``None`` — the face system assigns planets
        directly, not through sign rulership.

    Examples
    --------
    >>> pos = chaldean_face(0.0)     # Aries 0° — first face
    >>> pos.ruling_planet
    'Mars'
    >>> pos.decan_number
    1
    >>> chaldean_face(95.0).ruling_planet   # Leo ~5° — zero-based face index 9
    'Venus'
    """
    if not math.isfinite(longitude):
        raise ValueError(f"longitude must be finite, got {longitude!r}")
    lon = longitude % 360.0
    sign_idx, sign_name, sign_sym, decan_number, deg_in_decan = _sign_components(lon)
    face_idx = int(lon // 10)  # 0–35
    planet = _CHALDEAN_CYCLE[face_idx % 7]
    return DecanatePosition(
        system='chaldean_face',
        decan_number=decan_number,
        ruling_planet=planet,
        ruling_sign=None,
        sign=sign_name,
        sign_symbol=sign_sym,
        degree_in_decan=deg_in_decan,
        longitude_used=lon,
    )


def triplicity_decan(longitude: float) -> DecanatePosition:
    """
    Map a tropical ecliptic longitude to its triplicity decanate.

    Each sign's three decans are ruled by the signs of the same elemental
    triplicity in natural zodiacal order: the sign itself for decan 1,
    the sign 4 positions ahead for decan 2, and 8 positions ahead for
    decan 3.  The ruling planet is the traditional 7-planet ruler of that
    sign.

    Parameters
    ----------
    longitude : float
        Tropical ecliptic longitude in degrees.

    Returns
    -------
    DecanatePosition

    Examples
    --------
    >>> pos = triplicity_decan(0.0)   # Aries 0° — own sign rules
    >>> pos.ruling_planet, pos.ruling_sign
    ('Mars', 'Aries')
    >>> pos = triplicity_decan(15.0)  # Aries 15° — Leo rules
    >>> pos.ruling_planet, pos.ruling_sign
    ('Sun', 'Leo')
    """
    if not math.isfinite(longitude):
        raise ValueError(f"longitude must be finite, got {longitude!r}")
    lon = longitude % 360.0
    sign_idx, sign_name, sign_sym, decan_number, deg_in_decan = _sign_components(lon)
    ruling_sign, ruling_planet = _triplicity_ruler(sign_idx, decan_number)
    return DecanatePosition(
        system='triplicity',
        decan_number=decan_number,
        ruling_planet=ruling_planet,
        ruling_sign=ruling_sign,
        sign=sign_name,
        sign_symbol=sign_sym,
        degree_in_decan=deg_in_decan,
        longitude_used=lon,
    )


def vedic_drekkana(
    longitude: float,
    jd: float,
    ayanamsa_system: str = 'Lahiri',
) -> DecanatePosition:
    """
    Map a tropical ecliptic longitude to its Vedic drekkana (D3 division).

    The longitude is first converted to sidereal using the given ayanamsha
    system and Julian date, then the same triplicity arithmetic is applied.
    Rulerships use the traditional 7-planet Vedic scheme (no outer planets:
    Scorpio = Mars, Aquarius = Saturn, Pisces = Jupiter).

    Parameters
    ----------
    longitude : float
        Tropical ecliptic longitude in degrees.
    jd : float
        Julian date (UT) of the chart moment, used for ayanamsha correction.
    ayanamsa_system : str
        Ayanamsha system name.  Accepts any name from ``Ayanamsa`` or a
        ``UserDefinedAyanamsa`` instance.  Defaults to Lahiri (Indian
        national standard).

    Returns
    -------
    DecanatePosition
        ``longitude_used`` holds the sidereal longitude after ayanamsha
        correction.

    Examples
    --------
    >>> from moira.julian import julian_day
    >>> jd = julian_day(2000, 1, 1, 12.0)
    >>> pos = vedic_drekkana(0.0, jd)
    >>> pos.system
    'vedic_drekkana'
    """
    if not math.isfinite(longitude):
        raise ValueError(f"longitude must be finite, got {longitude!r}")
    from .sidereal import tropical_to_sidereal
    sid_lon = tropical_to_sidereal(longitude, jd, system=ayanamsa_system)
    sign_idx, sign_name, sign_sym, decan_number, deg_in_decan = _sign_components(sid_lon)
    ruling_sign, ruling_planet = _triplicity_ruler(sign_idx, decan_number)
    return DecanatePosition(
        system='vedic_drekkana',
        decan_number=decan_number,
        ruling_planet=ruling_planet,
        ruling_sign=ruling_sign,
        sign=sign_name,
        sign_symbol=sign_sym,
        degree_in_decan=deg_in_decan,
        longitude_used=sid_lon,
    )
