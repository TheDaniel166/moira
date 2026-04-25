"""
Moira — Vedic Planetary Dignities Engine
==========================================

Archetype: Engine

Purpose
-------
Governs the classical Parashari planetary dignity scheme for the seven
traditional planets (Sun through Saturn), including:

  Exaltation / Debilitation  — sign and deepest-degree points.
  Mulatrikona                — primary sign range (stronger than own sign).
  Swakshetra                 — own-sign domicile (one or two signs).
  Naisargika Maitri          — fixed natural friendship table (BPHS Ch. 3).
  Tatkalika Maitri           — temporary friendship from chart positions.
  Panchadha Maitri           — compound relationship (natural + temporary).

Rahu and Ketu are outside the scope of this system.  Parashara's dignity
tables apply only to the seven classical planets.

Tradition and sources
---------------------
Parashara, "Brihat Parashara Hora Shastra" (BPHS):
  Ch. 3  — Graha Gunas (planetary characteristics, natural friendships).
  Ch. 26 — Planetary Dignities (Ucha, Neecha, Mulatrikona, Swakshetra).
  Ch. 28 — Temporary and Compound Friendship (Tatkalika, Panchadha Maitri).
Kalyana Varma, "Saravali" (9th c. CE), Chapters 5–6.
B.V. Raman, "A Manual of Hindu Astrology" — consolidated tables and
  worked examples used as the primary verification reference.

Boundary declaration
--------------------
Owns: exaltation/debilitation tables, Mulatrikona ranges, own-sign tables,
      the natural friendship table, temporary and compound relationship
      computation, and the ``VedicDignityResult`` / ``PlanetaryRelationship``
      result vessels.
Delegates: sign name lookup to ``moira.constants``.

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required.  No database access.  All dignity tables are
compile-time constants.

Constitutional phases applied
-----------------------------
P2  — Classification constants: DignityTier.
P3  — Inspectability: VedicDignityResult.is_strong, .is_weak;
      PlanetaryRelationship.is_friendly, .is_hostile.
P4  — Policy vessel: VedicDignityPolicy.
P7  — Local condition profile: DignityConditionProfile,
      dignity_condition_profile().
P8  — Aggregate chart profile: ChartDignityProfile, chart_dignity_profile().
P10 — Hardening: VedicDignityResult.__post_init__, PlanetaryRelationship
      .__post_init__, validate_dignity_output().
P12 — Public API curation: __all__, docstring.

Public surface
--------------
``VedicDignityRank``        — string constants for dignity levels.
``CompoundRelationship``    — string constants for compound relationships.
``DignityTier``             — P2 classification: STRONG, NEUTRAL, WEAK.
``VedicDignityResult``      — immutable result vessel for a single planet.
``PlanetaryRelationship``   — immutable result vessel for a planet pair.
``VedicDignityPolicy``      — P4 policy vessel.
``DignityConditionProfile`` — P7 local condition profile for one planet.
``ChartDignityProfile``     — P8 aggregate chart profile.
``EXALTATION_SIGN``         — planet -> exaltation sign index.
``EXALTATION_DEGREE``       — planet -> deepest exaltation degree within sign.
``DEBILITATION_SIGN``       — planet -> debilitation sign index.
``MULATRIKONA_SIGN``        — planet -> Mulatrikona sign index.
``MULATRIKONA_START``       — planet -> start degree of Mulatrikona range.
``MULATRIKONA_END``         — planet -> end degree of Mulatrikona range.
``OWN_SIGNS``               — planet -> list of own-sign indices.
``NATURAL_FRIENDS``         — Naisargika Maitri: planet -> set of friends.
``NATURAL_NEUTRALS``        — planet -> set of neutrals.
``NATURAL_ENEMIES``         — planet -> set of enemies.
``vedic_dignity``           — map a planet's sidereal longitude to its dignity.
``planetary_relationships`` — compute all pairwise relationships for a chart.
``dignity_condition_profile`` — P7 local condition profile builder.
``chart_dignity_profile``   — P8 aggregate chart profile builder.
``validate_dignity_output`` — P10 output validator.
"""

from dataclasses import dataclass

from .constants import SIGNS

__all__ = [
    # Constants
    "VedicDignityRank",
    "CompoundRelationship",
    "DignityTier",
    "EXALTATION_SIGN",
    "EXALTATION_DEGREE",
    "DEBILITATION_SIGN",
    "MULATRIKONA_SIGN",
    "MULATRIKONA_START",
    "MULATRIKONA_END",
    "OWN_SIGNS",
    "NATURAL_FRIENDS",
    "NATURAL_NEUTRALS",
    "NATURAL_ENEMIES",
    # Result vessels
    "VedicDignityResult",
    "PlanetaryRelationship",
    # Policy
    "VedicDignityPolicy",
    # Profiles
    "DignityConditionProfile",
    "ChartDignityProfile",
    # Functions
    "vedic_dignity",
    "planetary_relationships",
    "dignity_condition_profile",
    "chart_dignity_profile",
    "validate_dignity_output",
]

# ---------------------------------------------------------------------------
# Classical planet set
# ---------------------------------------------------------------------------

_SEVEN_PLANETS: tuple[str, ...] = (
    'Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn',
)


# ---------------------------------------------------------------------------
# Dignity rank constants
# ---------------------------------------------------------------------------

class VedicDignityRank:
    """String constants for the seven Parashari dignity levels."""
    EXALTATION   = 'exaltation'
    MULATRIKONA  = 'mulatrikona'
    OWN_SIGN     = 'own_sign'
    FRIEND_SIGN  = 'friend_sign'
    NEUTRAL_SIGN = 'neutral_sign'
    ENEMY_SIGN   = 'enemy_sign'
    DEBILITATION = 'debilitation'


# ---------------------------------------------------------------------------
# Compound relationship constants
# ---------------------------------------------------------------------------

class CompoundRelationship:
    """String constants for the five Panchadha Maitri compound levels."""
    GREAT_FRIEND = 'adhi_mitra'   # Natural friend + temporary friend
    FRIEND       = 'mitra'        # Natural neutral + temporary friend
    NEUTRAL      = 'sama'         # Mixed (friend+enemy or enemy+friend)
    ENEMY        = 'shatru'       # Natural neutral + temporary enemy
    GREAT_ENEMY  = 'adhi_shatru'  # Natural enemy + temporary enemy


# ---------------------------------------------------------------------------
# P2 — DignityTier classification
# ---------------------------------------------------------------------------

class DignityTier:
    """
    P2 classification tier for a planet's dignified state.

    STRONG : exaltation, mulatrikona, or own sign.
    NEUTRAL: friend sign or neutral sign.
    WEAK   : enemy sign or debilitation.
    """
    STRONG  = 'strong'
    NEUTRAL = 'neutral'
    WEAK    = 'weak'


_STRONG_RANKS: frozenset[str] = frozenset({
    VedicDignityRank.EXALTATION,
    VedicDignityRank.MULATRIKONA,
    VedicDignityRank.OWN_SIGN,
})
_WEAK_RANKS: frozenset[str] = frozenset({
    VedicDignityRank.ENEMY_SIGN,
    VedicDignityRank.DEBILITATION,
})


# ---------------------------------------------------------------------------
# Exaltation and debilitation tables
#
# Source: BPHS Ch. 26.
# Deepest exaltation (Uchcha) degrees within the exaltation sign.
# Debilitation sign (Neecha) is always the sign opposite the exaltation
# sign; deepest debilitation degree is the same degree in that sign.
# ---------------------------------------------------------------------------

EXALTATION_SIGN: dict[str, int] = {
    'Sun':     0,    # Aries
    'Moon':    1,    # Taurus
    'Mars':    9,    # Capricorn
    'Mercury': 5,    # Virgo
    'Jupiter': 3,    # Cancer
    'Venus':   11,   # Pisces
    'Saturn':  6,    # Libra
}

EXALTATION_DEGREE: dict[str, float] = {
    'Sun':     10.0,
    'Moon':     3.0,
    'Mars':    28.0,
    'Mercury': 15.0,
    'Jupiter':  5.0,
    'Venus':   27.0,
    'Saturn':  20.0,
}

DEBILITATION_SIGN: dict[str, int] = {
    planet: (sign + 6) % 12
    for planet, sign in EXALTATION_SIGN.items()
}


# ---------------------------------------------------------------------------
# Mulatrikona ranges
#
# Source: BPHS Ch. 26.
# Moon: Parashara gives 3°–30° Taurus (some commentators give 4°; use 3°
# per the primary source).  Mercury: Mulatrikona overlaps the exaltation
# degree at 15° Virgo — check exaltation first in the rank cascade.
# ---------------------------------------------------------------------------

MULATRIKONA_SIGN: dict[str, int] = {
    'Sun':     4,    # Leo
    'Moon':    1,    # Taurus
    'Mars':    0,    # Aries
    'Mercury': 5,    # Virgo
    'Jupiter': 8,    # Sagittarius
    'Venus':   6,    # Libra
    'Saturn':  10,   # Aquarius
}

MULATRIKONA_START: dict[str, float] = {
    'Sun':      0.0,
    'Moon':     3.0,
    'Mars':     0.0,
    'Mercury': 15.0,
    'Jupiter':  0.0,
    'Venus':    0.0,
    'Saturn':   0.0,
}

MULATRIKONA_END: dict[str, float] = {
    'Sun':     20.0,
    'Moon':    30.0,
    'Mars':    12.0,
    'Mercury': 20.0,
    'Jupiter': 10.0,
    'Venus':   15.0,
    'Saturn':  20.0,
}


# ---------------------------------------------------------------------------
# Own-sign (Swakshetra) tables
#
# Traditional 7-planet domicile rulerships.  No outer planets.
# ---------------------------------------------------------------------------

OWN_SIGNS: dict[str, list[int]] = {
    'Sun':     [4],         # Leo
    'Moon':    [3],         # Cancer
    'Mars':    [0, 7],      # Aries, Scorpio
    'Mercury': [2, 5],      # Gemini, Virgo
    'Jupiter': [8, 11],     # Sagittarius, Pisces
    'Venus':   [1, 6],      # Taurus, Libra
    'Saturn':  [9, 10],     # Capricorn, Aquarius
}

# Reverse map: sign index → ruling planet
_SIGN_RULER: dict[int, str] = {}
for _planet, _signs in OWN_SIGNS.items():
    for _s in _signs:
        _SIGN_RULER[_s] = _planet


# ---------------------------------------------------------------------------
# Natural friendship tables (Naisargika Maitri)
#
# Source: BPHS Ch. 3.
# ---------------------------------------------------------------------------

NATURAL_FRIENDS: dict[str, set[str]] = {
    'Sun':     {'Moon', 'Mars', 'Jupiter'},
    'Moon':    {'Sun', 'Mercury'},
    'Mars':    {'Sun', 'Moon', 'Jupiter'},
    'Mercury': {'Sun', 'Venus'},
    'Jupiter': {'Sun', 'Moon', 'Mars'},
    'Venus':   {'Mercury', 'Saturn'},
    'Saturn':  {'Mercury', 'Venus'},
}

NATURAL_NEUTRALS: dict[str, set[str]] = {
    'Sun':     {'Mercury'},
    'Moon':    {'Mars', 'Jupiter', 'Venus', 'Saturn'},
    'Mars':    {'Venus', 'Saturn'},
    'Mercury': {'Mars', 'Jupiter', 'Saturn'},
    'Jupiter': {'Saturn'},
    'Venus':   {'Mars', 'Jupiter', 'Moon'},
    'Saturn':  {'Jupiter'},
}

NATURAL_ENEMIES: dict[str, set[str]] = {
    'Sun':     {'Venus', 'Saturn'},
    'Moon':    set(),
    'Mars':    {'Mercury'},
    'Mercury': {'Moon'},
    'Jupiter': {'Mercury', 'Venus'},
    'Venus':   {'Sun'},
    'Saturn':  {'Sun', 'Moon', 'Mars'},
}


# ---------------------------------------------------------------------------
# Result vessels
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class VedicDignityResult:
    """
    Immutable result vessel for a single planet's Vedic dignity assessment.

    Attributes
    ----------
    planet : str
        Planet name ('Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus',
        'Saturn').
    sidereal_longitude : float
        The sidereal longitude used for the assessment, in [0, 360).
    sign_index : int
        D1 sign index (0=Aries ... 11=Pisces).
    sign : str
        D1 sign name.
    dignity_rank : str
        One of the ``VedicDignityRank`` constants.  Cascade order:
        exaltation > mulatrikona > own_sign > friend_sign >
        neutral_sign > enemy_sign > debilitation.
    is_exalted : bool
        True when the planet is in its exaltation sign.
    is_debilitated : bool
        True when the planet is in its debilitation sign.
    is_mulatrikona : bool
        True when the planet is within its Mulatrikona degree range.
    is_own_sign : bool
        True when the planet is in one of its own signs (and not
        simultaneously in a higher state).
    exaltation_score : float
        Linear score in [0.0, 1.0] where 1.0 = deepest exaltation point
        and 0.0 = deepest debilitation point.  Used as a precursor for
        Uchcha Bala in Shadbala computation.
    """

    planet: str
    sidereal_longitude: float
    sign_index: int
    sign: str
    dignity_rank: str
    is_exalted: bool
    is_debilitated: bool
    is_mulatrikona: bool
    is_own_sign: bool
    exaltation_score: float

    def __post_init__(self) -> None:
        if self.planet not in _SEVEN_PLANETS:
            raise ValueError(
                f"VedicDignityResult.planet must be one of {_SEVEN_PLANETS}, "
                f"got {self.planet!r}"
            )
        if not (0.0 <= self.sidereal_longitude < 360.0):
            raise ValueError(
                f"VedicDignityResult.sidereal_longitude must be in [0, 360), "
                f"got {self.sidereal_longitude}"
            )
        if not (0 <= self.sign_index <= 11):
            raise ValueError(
                f"VedicDignityResult.sign_index must be in [0, 11], "
                f"got {self.sign_index}"
            )
        if not (0.0 <= self.exaltation_score <= 1.0):
            raise ValueError(
                f"VedicDignityResult.exaltation_score must be in [0.0, 1.0], "
                f"got {self.exaltation_score}"
            )

    @property
    def is_strong(self) -> bool:
        """P3 — True when dignity_rank is exaltation, mulatrikona, or own_sign."""
        return self.dignity_rank in _STRONG_RANKS

    @property
    def is_weak(self) -> bool:
        """P3 — True when dignity_rank is enemy_sign or debilitation."""
        return self.dignity_rank in _WEAK_RANKS


@dataclass(frozen=True, slots=True)
class PlanetaryRelationship:
    """
    Immutable result vessel for the relationship between two planets.

    Attributes
    ----------
    from_planet : str
        The planet whose perspective is being assessed.
    to_planet : str
        The planet being evaluated as friend/enemy from ``from_planet``.
    natural : str
        Naisargika relationship: 'friend', 'neutral', or 'enemy'.
    temporary : str
        Tatkalika relationship based on chart positions: 'friend' or 'enemy'.
    compound : str
        Panchadha Maitri compound relationship -- one of the
        ``CompoundRelationship`` constants.
    """

    from_planet: str
    to_planet: str
    natural: str
    temporary: str
    compound: str

    def __post_init__(self) -> None:
        if self.from_planet not in _SEVEN_PLANETS:
            raise ValueError(
                f"PlanetaryRelationship.from_planet must be one of "
                f"{_SEVEN_PLANETS}, got {self.from_planet!r}"
            )
        if self.to_planet not in _SEVEN_PLANETS:
            raise ValueError(
                f"PlanetaryRelationship.to_planet must be one of "
                f"{_SEVEN_PLANETS}, got {self.to_planet!r}"
            )
        if self.natural not in ('friend', 'neutral', 'enemy'):
            raise ValueError(
                f"PlanetaryRelationship.natural must be 'friend', 'neutral', "
                f"or 'enemy', got {self.natural!r}"
            )
        if self.temporary not in ('friend', 'enemy'):
            raise ValueError(
                f"PlanetaryRelationship.temporary must be 'friend' or 'enemy', "
                f"got {self.temporary!r}"
            )

    @property
    def is_friendly(self) -> bool:
        """P3 — True when compound is GREAT_FRIEND or FRIEND."""
        return self.compound in (
            CompoundRelationship.GREAT_FRIEND,
            CompoundRelationship.FRIEND,
        )

    @property
    def is_hostile(self) -> bool:
        """P3 — True when compound is GREAT_ENEMY or ENEMY."""
        return self.compound in (
            CompoundRelationship.GREAT_ENEMY,
            CompoundRelationship.ENEMY,
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _natural_relationship(from_planet: str, to_planet: str) -> str:
    """Return 'friend', 'neutral', or 'enemy' from Naisargika table."""
    if to_planet in NATURAL_FRIENDS[from_planet]:
        return 'friend'
    if to_planet in NATURAL_ENEMIES[from_planet]:
        return 'enemy'
    return 'neutral'


def _temporary_relationship(sign_a: int, sign_b: int) -> str:
    """
    Return 'friend' or 'enemy' based on Tatkalika (temporary) friendship.

    A planet at sign_b is a temporary friend of the planet at sign_a when
    the 1-based sign-distance from sign_a to sign_b falls in
    {1, 2, 3, 9, 10, 11}.  All other distances are temporary enemies.
    Distance 0 (same sign, i.e. the planet itself) should never be passed
    here — it is excluded at the call site.
    """
    distance = (sign_b - sign_a) % 12 + 1   # 1–12
    if distance in {1, 2, 3, 9, 10, 11}:
        return 'friend'
    return 'enemy'


def _compound_relationship(natural: str, temporary: str) -> str:
    """
    Return the Panchadha Maitri compound relationship.

    Combination table (BPHS Ch. 28):
      Friend  + Friend  → Adhi Mitra (Great Friend)
      Friend  + Enemy   → Sama (Neutral)
      Neutral + Friend  → Mitra (Friend)
      Neutral + Enemy   → Shatru (Enemy)
      Enemy   + Friend  → Sama (Neutral)
      Enemy   + Enemy   → Adhi Shatru (Great Enemy)
    """
    if natural == 'friend':
        return CompoundRelationship.GREAT_FRIEND if temporary == 'friend' else CompoundRelationship.NEUTRAL
    if natural == 'neutral':
        return CompoundRelationship.FRIEND if temporary == 'friend' else CompoundRelationship.ENEMY
    # natural == 'enemy'
    return CompoundRelationship.NEUTRAL if temporary == 'friend' else CompoundRelationship.GREAT_ENEMY


def _exaltation_score(planet: str, sidereal_longitude: float) -> float:
    """
    Linear exaltation score in [0.0, 1.0].

    1.0 at the deepest exaltation point; 0.0 at the deepest debilitation
    point (180° away).  Used as a precursor for Uchcha Bala.
    """
    lon = sidereal_longitude % 360.0
    ucha_lon = (EXALTATION_SIGN[planet] * 30.0 + EXALTATION_DEGREE[planet]) % 360.0
    dist = abs(lon - ucha_lon)
    if dist > 180.0:
        dist = 360.0 - dist
    return (180.0 - dist) / 180.0


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def vedic_dignity(planet: str, sidereal_longitude: float) -> VedicDignityResult:
    """
    Map a planet's sidereal longitude to its Parashari dignity state.

    The dignity rank cascade is applied in this order:
    exaltation → mulatrikona → own_sign → friend_sign →
    neutral_sign → enemy_sign → debilitation.

    A planet at exactly the Mulatrikona degree of Virgo (Mercury) is checked
    for exaltation first, because the exaltation point at 15° falls within
    the Mulatrikona range (15°–20°); exaltation takes precedence.

    Parameters
    ----------
    planet : str
        One of the seven classical planets: 'Sun', 'Moon', 'Mars',
        'Mercury', 'Jupiter', 'Venus', 'Saturn'.
    sidereal_longitude : float
        Sidereal ecliptic longitude in degrees.  Any value is accepted; it
        is reduced to [0, 360) internally.

    Returns
    -------
    VedicDignityResult

    Raises
    ------
    ValueError
        If ``planet`` is not one of the seven classical planets.

    Examples
    --------
    >>> pos = vedic_dignity('Sun', 10.0)   # Sun at Aries 10° — deepest exaltation
    >>> pos.dignity_rank
    'exaltation'
    >>> pos.is_exalted
    True
    >>> pos.exaltation_score
    1.0
    """
    if planet not in _SEVEN_PLANETS:
        raise ValueError(
            f"planet must be one of {_SEVEN_PLANETS}, got {planet!r}"
        )

    lon       = sidereal_longitude % 360.0
    sign_idx  = int(lon // 30)
    deg_in    = lon % 30.0
    sign_name = SIGNS[sign_idx]

    uch_score = _exaltation_score(planet, lon)

    # --- Determine rank (cascade) ---
    is_exalted      = False
    is_debilitated  = False
    is_mulatrikona  = False
    is_own          = False

    if sign_idx == EXALTATION_SIGN[planet]:
        is_exalted = True
        rank = VedicDignityRank.EXALTATION

    elif sign_idx == DEBILITATION_SIGN[planet]:
        is_debilitated = True
        rank = VedicDignityRank.DEBILITATION

    elif (sign_idx == MULATRIKONA_SIGN[planet]
          and MULATRIKONA_START[planet] <= deg_in < MULATRIKONA_END[planet]):
        is_mulatrikona = True
        rank = VedicDignityRank.MULATRIKONA

    elif sign_idx in OWN_SIGNS[planet]:
        is_own = True
        rank = VedicDignityRank.OWN_SIGN

    else:
        # Determine by sign ruler relationship
        sign_ruler = _SIGN_RULER.get(sign_idx)
        if sign_ruler is None:
            # Should not happen with a complete _SIGN_RULER map, but guard anyway
            rank = VedicDignityRank.NEUTRAL_SIGN
        elif sign_ruler in NATURAL_FRIENDS[planet]:
            rank = VedicDignityRank.FRIEND_SIGN
        elif sign_ruler in NATURAL_ENEMIES[planet]:
            rank = VedicDignityRank.ENEMY_SIGN
        else:
            rank = VedicDignityRank.NEUTRAL_SIGN

    return VedicDignityResult(
        planet=planet,
        sidereal_longitude=lon,
        sign_index=sign_idx,
        sign=sign_name,
        dignity_rank=rank,
        is_exalted=is_exalted,
        is_debilitated=is_debilitated,
        is_mulatrikona=is_mulatrikona,
        is_own_sign=is_own,
        exaltation_score=uch_score,
    )


def planetary_relationships(
    sidereal_longitudes: dict[str, float],
) -> list[PlanetaryRelationship]:
    """
    Compute all pairwise Panchadha Maitri relationships for a set of planets.

    Relationships are directional: the relationship of planet A toward planet
    B may differ from B toward A (temporary friendship depends on which sign
    is the reference).

    Parameters
    ----------
    sidereal_longitudes : dict[str, float]
        Mapping of planet name → sidereal longitude.  Must include at least
        the seven classical planets that participate in the computation.
        Unknown keys are silently ignored.

    Returns
    -------
    list[PlanetaryRelationship]
        One entry per ordered pair (A, B) where A ≠ B and both are among
        the seven classical planets present in ``sidereal_longitudes``.
        Length is N*(N-1) for N participating planets.

    Examples
    --------
    >>> lons = {'Sun': 10.0, 'Moon': 40.0, 'Mars': 70.0,
    ...         'Mercury': 100.0, 'Jupiter': 130.0, 'Venus': 160.0,
    ...         'Saturn': 190.0}
    >>> rels = planetary_relationships(lons)
    >>> len(rels)
    42
    """
    present = [p for p in _SEVEN_PLANETS if p in sidereal_longitudes]
    sign_of: dict[str, int] = {
        p: int(sidereal_longitudes[p] % 360.0 // 30)
        for p in present
    }

    result: list[PlanetaryRelationship] = []
    for from_p in present:
        for to_p in present:
            if from_p == to_p:
                continue
            nat  = _natural_relationship(from_p, to_p)
            temp = _temporary_relationship(sign_of[from_p], sign_of[to_p])
            comp = _compound_relationship(nat, temp)
            result.append(PlanetaryRelationship(
                from_planet=from_p,
                to_planet=to_p,
                natural=nat,
                temporary=temp,
                compound=comp,
            ))
    return result


# ---------------------------------------------------------------------------
# P4 -- VedicDignityPolicy
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class VedicDignityPolicy:
    """
    P4 policy vessel for vedic dignity computation.

    Attributes
    ----------
    ayanamsa_system : str
        Ayanamsa system used for sidereal reduction.  Must be non-empty.
        Default 'Lahiri'.
    """

    ayanamsa_system: str = 'Lahiri'

    def __post_init__(self) -> None:
        if not self.ayanamsa_system:
            raise ValueError(
                "VedicDignityPolicy.ayanamsa_system must be non-empty"
            )


# ---------------------------------------------------------------------------
# P7 -- DignityConditionProfile (local condition for one planet)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class DignityConditionProfile:
    """
    P7 local condition profile for a single planet's dignity state.

    Attributes
    ----------
    planet : str
        Planet name.
    dignity_rank : str
        One of the VedicDignityRank constants.
    tier : str
        One of the DignityTier constants (STRONG, NEUTRAL, WEAK).
    exaltation_score : float
        Linear score in [0.0, 1.0].
    sign_index : int
        D1 sign index.
    sign : str
        D1 sign name.
    """

    planet: str
    dignity_rank: str
    tier: str
    exaltation_score: float
    sign_index: int
    sign: str


def dignity_condition_profile(
    result: VedicDignityResult,
) -> DignityConditionProfile:
    """
    Build a P7 DignityConditionProfile from a VedicDignityResult.

    Parameters
    ----------
    result : VedicDignityResult
        The dignity result for one planet.

    Returns
    -------
    DignityConditionProfile
    """
    if result.dignity_rank in _STRONG_RANKS:
        tier = DignityTier.STRONG
    elif result.dignity_rank in _WEAK_RANKS:
        tier = DignityTier.WEAK
    else:
        tier = DignityTier.NEUTRAL

    return DignityConditionProfile(
        planet=result.planet,
        dignity_rank=result.dignity_rank,
        tier=tier,
        exaltation_score=result.exaltation_score,
        sign_index=result.sign_index,
        sign=result.sign,
    )


# ---------------------------------------------------------------------------
# P8 -- ChartDignityProfile (aggregate across all seven planets)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ChartDignityProfile:
    """
    P8 aggregate dignity profile for a full chart.

    Attributes
    ----------
    strong_count : int
        Number of planets with tier STRONG.
    neutral_count : int
        Number of planets with tier NEUTRAL.
    weak_count : int
        Number of planets with tier WEAK.
    strongest_planet : str
        Planet with the highest exaltation_score.
    weakest_planet : str
        Planet with the lowest exaltation_score.
    planet_tiers : dict[str, str]
        Mapping of planet name -> DignityTier constant.
    exaltation_scores : dict[str, float]
        Mapping of planet name -> exaltation_score.
    """

    strong_count: int
    neutral_count: int
    weak_count: int
    strongest_planet: str
    weakest_planet: str
    planet_tiers: dict[str, str]
    exaltation_scores: dict[str, float]


def chart_dignity_profile(
    dignity_results: dict[str, VedicDignityResult],
) -> ChartDignityProfile:
    """
    Build a P8 ChartDignityProfile from per-planet dignity results.

    Parameters
    ----------
    dignity_results : dict[str, VedicDignityResult]
        Mapping of planet name -> VedicDignityResult.  Should contain all
        seven classical planets for a complete profile.

    Returns
    -------
    ChartDignityProfile

    Raises
    ------
    ValueError
        If dignity_results is empty.
    """
    if not dignity_results:
        raise ValueError("chart_dignity_profile: dignity_results must not be empty")

    profiles = {p: dignity_condition_profile(r) for p, r in dignity_results.items()}

    strong_count  = sum(1 for pr in profiles.values() if pr.tier == DignityTier.STRONG)
    neutral_count = sum(1 for pr in profiles.values() if pr.tier == DignityTier.NEUTRAL)
    weak_count    = sum(1 for pr in profiles.values() if pr.tier == DignityTier.WEAK)

    scores = {p: r.exaltation_score for p, r in dignity_results.items()}
    strongest = max(scores, key=scores.__getitem__)
    weakest   = min(scores, key=scores.__getitem__)

    return ChartDignityProfile(
        strong_count=strong_count,
        neutral_count=neutral_count,
        weak_count=weak_count,
        strongest_planet=strongest,
        weakest_planet=weakest,
        planet_tiers={p: pr.tier for p, pr in profiles.items()},
        exaltation_scores=scores,
    )


# ---------------------------------------------------------------------------
# P10 -- validate_dignity_output
# ---------------------------------------------------------------------------

def validate_dignity_output(
    dignity_results: dict[str, VedicDignityResult],
) -> None:
    """
    P10 validator for a set of per-planet dignity results.

    Checks that each result has a valid planet, that sign_index matches
    the expected derivation from sidereal_longitude, and that
    exaltation_score is in [0.0, 1.0].

    Parameters
    ----------
    dignity_results : dict[str, VedicDignityResult]
        Mapping of planet name -> VedicDignityResult.

    Raises
    ------
    ValueError
        On any inconsistency.
    """
    for planet, r in dignity_results.items():
        if planet != r.planet:
            raise ValueError(
                f"validate_dignity_output: key {planet!r} does not match "
                f"result.planet {r.planet!r}"
            )
        expected_sign = int(r.sidereal_longitude // 30)
        if r.sign_index != expected_sign:
            raise ValueError(
                f"validate_dignity_output: {planet} sign_index {r.sign_index} "
                f"does not match longitude {r.sidereal_longitude} "
                f"(expected {expected_sign})"
            )
        if not (0.0 <= r.exaltation_score <= 1.0):
            raise ValueError(
                f"validate_dignity_output: {planet} exaltation_score "
                f"{r.exaltation_score} outside [0.0, 1.0]"
            )
