"""
Moira — Ashtakavarga Engine
=============================

Archetype: Engine

Purpose
-------
Computes the Parashari Ashtakavarga (eightfold-point system) for the seven
classical planets.  For each planet, a Bhinnashtakavarga (individual
benefic-point table) is produced by counting rekhas (benefic points)
contributed across all 12 signs by 8 reference positions (the 7 classical
planets + Lagna).  The aggregate across all 7 planets is the
Sarvashtakavarga.

Phase 1 (this implementation):
  - Unreduced Bhinnashtakavarga for all 7 classical planets.
  - Sarvashtakavarga (sum of all 7 Bhinnashtavargas, sign by sign).
  - Transit strength query (rekha count for a given transit sign).

Phase 2 (future):
  - Trikona Shodhana (trine reduction).
  - Ekadhipatya Shodhana (same-ruler reduction).

Rekha tables
------------
The 7 × 8 rekha tables (one per planet assessed, one row per reference
position) are encoded from the authoritative source:

  B.V. Raman, "Ashtakavarga System of Prediction" (1981).

Each table entry is a frozenset of 1-based sign-distances from the
reference position that receive a rekha (benefic point).  The 1-based
distance from reference sign R to sign S is ``(S - R) % 12 + 1`` (range
1–12).  Values not in the frozenset receive no rekha (0 points).

Important: Different editions of BPHS have minor discrepancies in these
tables.  Raman (1981) is used as the single committed source.  All
discrepancies between Raman and other editions are documented in comments
where they arise.

Tradition and sources
---------------------
Parashara, "Brihat Parashara Hora Shastra", Ashtakavarga Adhyaya.
Vaidyanatha Dikshita, "Jataka Parijata" (14th c.).
B.V. Raman, "Ashtakavarga System of Prediction" (1981) — primary table
  source; used as the authoritative encoding reference.

Boundary declaration
--------------------
Owns: Ashtakavarga rekha tables, Bhinnashtakavarga computation,
      Sarvashtakavarga aggregation, transit strength query, and the
      ``BhinnashtakavargaResult`` / ``AshtakavargaResult`` result vessels.
Delegates: sidereal conversion to the caller; this module operates on
           sign indices (0–11) only.

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required.  No database access.  All rekha tables are
compile-time constants.

Constitutional phase
--------------------
Phase 12 — Public API Curation.  All twelve phases complete.

Public surface
--------------
``RekhaTier``                 — strength classification constants for rekha counts.
``AshtakavargaPolicy``        — policy dataclass for Ashtakavarga computation.
``REKHA_TABLES``              — 7 × 8 rekha frozenset lookup tables.
``BhinnashtakavargaResult``   — immutable vessel for one planet's rekha counts.
``AshtakavargaResult``        — immutable vessel for the full chart result.
``SignStrengthProfile``       — integrated condition profile for one sign in one planet's BAV.
``AshtakavargaChartProfile``  — aggregate intelligence profile for a full chart.
``bhinnashtakavarga``         — compute one planet's benefic-point table.
``ashtakavarga``              — compute the full Ashtakavarga for a chart.
``transit_strength``          — rekha count for a transiting planet.
``sign_strength_profile``     — build a SignStrengthProfile for one sign.
``ashtakavarga_chart_profile`` — build an AshtakavargaChartProfile.
``validate_ashtakavarga_output`` — validate structural invariants of an AshtakavargaResult.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    # Phase 2 — Classification
    "RekhaTier",
    # Phase 4 — Policy
    "AshtakavargaPolicy",
    # Tables
    "REKHA_TABLES",
    # Phase 1 — Truth Preservation
    "BhinnashtakavargaResult",
    "AshtakavargaResult",
    # Phase 7 — Integrated Local Condition
    "SignStrengthProfile",
    # Phase 8 — Aggregate Intelligence
    "AshtakavargaChartProfile",
    # Functions
    "bhinnashtakavarga",
    "ashtakavarga",
    "transit_strength",
    "sign_strength_profile",
    "ashtakavarga_chart_profile",
    "validate_ashtakavarga_output",
]

# ---------------------------------------------------------------------------
# Classical planet set and reference order
# ---------------------------------------------------------------------------

_SEVEN_PLANETS: tuple[str, ...] = (
    'Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn',
)
_REFERENCES: tuple[str, ...] = _SEVEN_PLANETS + ('Lagna',)


# ---------------------------------------------------------------------------
# Phase 2 — Classification constants
# ---------------------------------------------------------------------------

class RekhaTier:
    """Rekha count strength classification for Ashtakavarga.

    Applies to individual planet Bhinnashtakavarga rekha counts per sign.
    The traditional threshold for transit strength is ≥ 4 rekhas.
    """
    STRONG = 'strong'   # rekha count ≥ 4 (strong for transit / muhurta)
    WEAK   = 'weak'     # rekha count < 4


# ---------------------------------------------------------------------------
# Rekha tables
#
# Source: B.V. Raman, "Ashtakavarga System of Prediction" (1981).
#
# REKHA_TABLES[planet_P][reference] = frozenset of 1-based sign-distances
# from the reference position that contribute a rekha to the assessed planet.
#
# 1-based distance: (sign_i - reference_sign) % 12 + 1  → values 1–12.
# ---------------------------------------------------------------------------

REKHA_TABLES: dict[str, dict[str, frozenset[int]]] = {

    # -----------------------------------------------------------------------
    # Sun's Bhinnashtakavarga
    # Source: Raman (1981) — total 48 benefic points.
    # -----------------------------------------------------------------------
    'Sun': {
        'Sun':     frozenset({1, 2, 4, 7, 8, 9, 10, 11}),
        'Moon':    frozenset({3, 6, 10, 11}),
        'Mars':    frozenset({1, 2, 4, 7, 8, 9, 10, 11}),
        'Mercury': frozenset({3, 5, 6, 9, 10, 11, 12}),
        'Jupiter': frozenset({5, 6, 9, 11}),
        'Venus':   frozenset({6, 7, 12}),
        'Saturn':  frozenset({1, 2, 4, 7, 8, 10, 11}),      # 7 pts — 9 absent (Raman)
        'Lagna':   frozenset({1, 2, 4, 7, 8, 10, 11}),      # 7 pts — 9 absent (Raman)
    },

    # -----------------------------------------------------------------------
    # Moon's Bhinnashtakavarga
    # -----------------------------------------------------------------------
    'Moon': {
        'Sun':     frozenset({3, 6, 7, 8, 10, 11}),
        'Moon':    frozenset({1, 3, 6, 7, 10, 11}),
        'Mars':    frozenset({2, 3, 5, 6, 9, 10, 11}),
        'Mercury': frozenset({1, 3, 4, 5, 7, 8, 10, 11}),
        'Jupiter': frozenset({1, 4, 7, 8, 10, 11, 12}),
        'Venus':   frozenset({3, 4, 5, 7, 9, 10, 11}),
        'Saturn':  frozenset({3, 5, 6, 11}),
        'Lagna':   frozenset({3, 6, 10, 11}),
    },

    # -----------------------------------------------------------------------
    # Mars's Bhinnashtakavarga
    # Source: Raman (1981) — total 39 benefic points.
    # -----------------------------------------------------------------------
    'Mars': {
        'Sun':     frozenset({3, 6, 10, 11}),                  # 4 pts — 5 absent (Raman)
        'Moon':    frozenset({3, 6, 11}),
        'Mars':    frozenset({1, 2, 4, 7, 8, 10, 11}),
        'Mercury': frozenset({3, 5, 6, 11}),
        'Jupiter': frozenset({6, 10, 11, 12}),
        'Venus':   frozenset({6, 8, 11, 12}),
        'Saturn':  frozenset({1, 4, 7, 8, 10, 11}),          # 6 pts — 9 absent (Raman)
        'Lagna':   frozenset({1, 2, 4, 7, 8, 10, 11}),
    },

    # -----------------------------------------------------------------------
    # Mercury's Bhinnashtakavarga
    # -----------------------------------------------------------------------
    'Mercury': {
        'Sun':     frozenset({5, 6, 9, 11, 12}),
        'Moon':    frozenset({2, 4, 6, 8, 10, 11}),
        'Mars':    frozenset({1, 2, 4, 7, 8, 9, 10, 11}),
        'Mercury': frozenset({1, 3, 5, 6, 9, 10, 11, 12}),
        'Jupiter': frozenset({6, 8, 11, 12}),
        'Venus':   frozenset({1, 2, 3, 4, 5, 8, 9, 11}),
        'Saturn':  frozenset({1, 2, 4, 7, 8, 9, 10, 11}),
        'Lagna':   frozenset({1, 2, 4, 6, 8, 10, 11}),
    },

    # -----------------------------------------------------------------------
    # Jupiter's Bhinnashtakavarga
    # -----------------------------------------------------------------------
    'Jupiter': {
        'Sun':     frozenset({1, 2, 3, 4, 7, 8, 9, 10, 11}),
        'Moon':    frozenset({2, 5, 7, 9, 11}),
        'Mars':    frozenset({1, 2, 4, 7, 8, 10, 11}),
        'Mercury': frozenset({1, 2, 4, 5, 6, 9, 10, 11}),
        'Jupiter': frozenset({1, 2, 3, 4, 7, 8, 10, 11}),
        'Venus':   frozenset({2, 5, 6, 9, 10, 11}),
        'Saturn':  frozenset({3, 5, 6, 12}),
        'Lagna':   frozenset({1, 2, 4, 5, 6, 7, 9, 10, 11}),
    },

    # -----------------------------------------------------------------------
    # Venus's Bhinnashtakavarga
    # -----------------------------------------------------------------------
    'Venus': {
        'Sun':     frozenset({8, 11, 12}),
        'Moon':    frozenset({1, 2, 3, 4, 5, 8, 9, 11, 12}),
        'Mars':    frozenset({3, 4, 6, 9, 11, 12}),
        'Mercury': frozenset({3, 5, 6, 9, 11}),
        'Jupiter': frozenset({5, 8, 9, 10, 11}),
        'Venus':   frozenset({1, 2, 3, 4, 5, 8, 9, 10, 11}),
        'Saturn':  frozenset({3, 4, 5, 8, 9, 10, 11}),
        'Lagna':   frozenset({1, 2, 3, 4, 5, 8, 9, 11}),
    },

    # -----------------------------------------------------------------------
    # Saturn's Bhinnashtakavarga
    # -----------------------------------------------------------------------
    'Saturn': {
        'Sun':     frozenset({1, 2, 4, 7, 8, 10, 11}),
        'Moon':    frozenset({3, 6, 11}),
        'Mars':    frozenset({3, 5, 6, 10, 11, 12}),
        'Mercury': frozenset({6, 8, 9, 10, 11, 12}),
        'Jupiter': frozenset({5, 6, 11, 12}),
        'Venus':   frozenset({6, 11, 12}),
        'Saturn':  frozenset({3, 5, 6, 11}),
        'Lagna':   frozenset({1, 3, 4, 6, 10, 11}),
    },
}


# ---------------------------------------------------------------------------
# Result vessels
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class BhinnashtakavargaResult:
    """
    Immutable vessel for one planet's Bhinnashtakavarga (individual
    benefic-point table across all 12 signs).

    Attributes
    ----------
    planet : str
        The planet whose Bhinnashtakavarga was computed.
    rekhas : tuple[int, ...]
        12-element tuple of rekha counts, one per sign.
        Index 0 = Aries, index 11 = Pisces.  Each value is in [0, 8].
    total_rekhas : int
        Sum of all 12 rekha counts.  The theoretical maximum is 56
        (8 references × 7 planets), though practice yields 35–45 for most
        planets.
    """

    planet: str
    rekhas: tuple[int, ...]
    total_rekhas: int

    def __post_init__(self) -> None:
        if self.planet not in _SEVEN_PLANETS:
            raise ValueError(
                f"BhinnashtakavargaResult.planet must be one of "
                f"{_SEVEN_PLANETS}, got {self.planet!r}"
            )
        if len(self.rekhas) != 12:
            raise ValueError(
                f"rekhas must have 12 entries, got {len(self.rekhas)}"
            )
        for i, r in enumerate(self.rekhas):
            if not (0 <= r <= 8):
                raise ValueError(
                    f"rekhas[{i}] must be in [0, 8], got {r}"
                )
        if self.total_rekhas != sum(self.rekhas):
            raise ValueError(
                f"total_rekhas ({self.total_rekhas}) != sum(rekhas) "
                f"({sum(self.rekhas)})"
            )

    # --- Phase 3 — Inspectability ------------------------------------------

    def for_sign(self, sign_idx: int) -> int:
        """Return the rekha count for the given sign index (0–11)."""
        if not (0 <= sign_idx <= 11):
            raise ValueError(
                f"sign_idx must be in [0, 11], got {sign_idx}"
            )
        return self.rekhas[sign_idx]

    def strong_signs(self, threshold: int = 4) -> list[int]:
        """Return list of sign indices with rekha count ≥ ``threshold``."""
        return [i for i, r in enumerate(self.rekhas) if r >= threshold]


@dataclass(frozen=True, slots=True)
class AshtakavargaResult:
    """
    Immutable vessel for the full Ashtakavarga computation for a chart.

    Attributes
    ----------
    ayanamsa_system : str
        The ayanamsa system used for sidereal conversion (informational;
        this module receives sign indices, not longitudes).
    bhinnashtakavarga : dict[str, BhinnashtakavargaResult]
        Mapping of planet name → its Bhinnashtakavarga result.
    sarvashtakavarga : tuple[int, ...]
        12-element tuple of aggregate rekha counts (sum of all 7
        Bhinnashtavargas, sign by sign).  Maximum per sign = 56 (7 × 8).
        A sign with ≥ 28 rekhas is considered strong for transit.
    """

    ayanamsa_system: str
    bhinnashtakavarga: dict[str, BhinnashtakavargaResult]
    sarvashtakavarga: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.ayanamsa_system:
            raise ValueError("AshtakavargaResult.ayanamsa_system must be non-empty")
        if len(self.sarvashtakavarga) != 12:
            raise ValueError(
                f"sarvashtakavarga must have 12 entries, "
                f"got {len(self.sarvashtakavarga)}"
            )
        if set(self.bhinnashtakavarga) != set(_SEVEN_PLANETS):
            raise ValueError(
                f"bhinnashtakavarga must have exactly the 7 classical planets, "
                f"got {sorted(self.bhinnashtakavarga)}"
            )

    # --- Phase 3 — Inspectability ------------------------------------------

    def for_planet(self, planet: str) -> BhinnashtakavargaResult:
        """Return the ``BhinnashtakavargaResult`` for the given planet.

        Raises ``KeyError`` if ``planet`` is not in the result.
        """
        return self.bhinnashtakavarga[planet]


# ---------------------------------------------------------------------------
# Phase 4 — Policy
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AshtakavargaPolicy:
    """Policy surface for Ashtakavarga computation.

    Attributes
    ----------
    ayanamsa_system : str
        Ayanamsa system name.  Informational only; this module receives
        pre-converted sign indices.  Defaults to Lahiri.
    strong_threshold : int
        Rekha count threshold (inclusive) for classifying a sign as strong.
        Traditional default is 4 (applies to Bhinnashtakavarga transit
        strength).  Must be in [1, 8].
    """
    ayanamsa_system: str = 'Lahiri'
    strong_threshold: int = 4

    def __post_init__(self) -> None:
        if not self.ayanamsa_system:
            raise ValueError(
                "AshtakavargaPolicy.ayanamsa_system must be non-empty"
            )
        if not (1 <= self.strong_threshold <= 8):
            raise ValueError(
                f"AshtakavargaPolicy.strong_threshold must be in [1, 8], "
                f"got {self.strong_threshold}"
            )


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def bhinnashtakavarga(
    planet: str,
    sign_indices: dict[str, int],
) -> BhinnashtakavargaResult:
    """
    Compute the Bhinnashtakavarga for one planet.

    For each of the 12 zodiac signs, counts how many of the 8 reference
    positions (Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn, Lagna)
    contribute a rekha (benefic point) to that sign as seen from the
    assessed planet.

    Parameters
    ----------
    planet : str
        The planet being assessed.  Must be one of the seven classical
        planets: ``'Sun'``, ``'Moon'``, ``'Mars'``, ``'Mercury'``,
        ``'Jupiter'``, ``'Venus'``, ``'Saturn'``.
    sign_indices : dict[str, int]
        Mapping of planet/lagna name → sidereal sign index (0–11).
        Must contain keys for all 8 references: the 7 classical planets
        plus ``'Lagna'``.

    Returns
    -------
    BhinnashtakavargaResult

    Raises
    ------
    ValueError
        If ``planet`` is not one of the seven classical planets.
    KeyError
        If a required reference key is missing from ``sign_indices``.

    Examples
    --------
    >>> indices = {'Sun':0,'Moon':1,'Mars':2,'Mercury':3,
    ...            'Jupiter':4,'Venus':5,'Saturn':6,'Lagna':7}
    >>> result = bhinnashtakavarga('Sun', indices)
    >>> len(result.rekhas)
    12
    """
    if planet not in _SEVEN_PLANETS:
        raise ValueError(
            f"planet must be one of {_SEVEN_PLANETS}, got {planet!r}"
        )

    table = REKHA_TABLES[planet]
    rekhas: list[int] = []

    for sign_i in range(12):
        count = 0
        for ref in _REFERENCES:
            ref_sign = sign_indices[ref]
            distance = (sign_i - ref_sign) % 12 + 1   # 1–12
            if distance in table[ref]:
                count += 1
        rekhas.append(count)

    rekha_tuple = tuple(rekhas)
    return BhinnashtakavargaResult(
        planet=planet,
        rekhas=rekha_tuple,
        total_rekhas=sum(rekha_tuple),
    )


def ashtakavarga(
    sidereal_longitudes: dict[str, float],
    ayanamsa_system: str = 'Lahiri',
    policy: AshtakavargaPolicy | None = None,
) -> AshtakavargaResult:
    """
    Compute the full Ashtakavarga for a chart.

    Parameters
    ----------
    sidereal_longitudes : dict[str, float]
        Mapping of body name → sidereal longitude in degrees.  Must contain
        the 7 classical planets and ``'Lagna'``.  Extra keys are ignored.
        Caller is responsible for tropical-to-sidereal conversion before
        calling this function.
    ayanamsa_system : str
        Recorded in the result for reference.  This function does not
        perform ayanamsa conversion.  Ignored when ``policy`` is supplied.
    policy : AshtakavargaPolicy or None
        Optional policy vessel.  When provided,
        ``policy.ayanamsa_system`` overrides ``ayanamsa_system``.

    Returns
    -------
    AshtakavargaResult

    Raises
    ------
    KeyError
        If a required body is missing from ``sidereal_longitudes``.

    Examples
    --------
    >>> lons = {'Sun':10.,'Moon':40.,'Mars':70.,'Mercury':100.,
    ...         'Jupiter':130.,'Venus':160.,'Saturn':190.,'Lagna':220.}
    >>> result = ashtakavarga(lons)
    >>> len(result.sarvashtakavarga)
    12
    """
    if policy is not None:
        ayanamsa_system = policy.ayanamsa_system
    # Compute sign indices from sidereal longitudes
    sign_indices: dict[str, int] = {
        body: int(sidereal_longitudes[body] % 360.0 // 30)
        for body in list(_REFERENCES)
    }

    bhinna: dict[str, BhinnashtakavargaResult] = {
        planet: bhinnashtakavarga(planet, sign_indices)
        for planet in _SEVEN_PLANETS
    }

    sarva = tuple(
        sum(bhinna[p].rekhas[i] for p in _SEVEN_PLANETS)
        for i in range(12)
    )

    return AshtakavargaResult(
        ayanamsa_system=ayanamsa_system,
        bhinnashtakavarga=bhinna,
        sarvashtakavarga=sarva,
    )


def transit_strength(
    planet: str,
    transit_sign_index: int,
    bhinna: BhinnashtakavargaResult,
) -> int:
    """
    Return the rekha count for a planet transiting a given sign.

    This is the direct reading of the Bhinnashtakavarga for the transiting
    planet's current sign.  A count of ≥ 4 is traditionally considered
    strong for transit purposes.

    Parameters
    ----------
    planet : str
        The transiting planet name.  Must match ``bhinna.planet``.
    transit_sign_index : int
        Sidereal sign index of the transit position (0=Aries … 11=Pisces).
    bhinna : BhinnashtakavargaResult
        The planet's pre-computed Bhinnashtakavarga.

    Returns
    -------
    int
        Rekha count in [0, 8].

    Raises
    ------
    ValueError
        If ``transit_sign_index`` is not in [0, 11].
        If ``planet`` does not match ``bhinna.planet``.
    """
    if not (0 <= transit_sign_index <= 11):
        raise ValueError(
            f"transit_sign_index must be in [0, 11], got {transit_sign_index}"
        )
    if planet != bhinna.planet:
        raise ValueError(
            f"planet {planet!r} does not match bhinna.planet {bhinna.planet!r}"
        )
    return bhinna.rekhas[transit_sign_index]


# ---------------------------------------------------------------------------
# Phase 7 — Integrated Local Condition
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SignStrengthProfile:
    """Integrated condition profile for one sign in one planet's
    Bhinnashtakavarga.

    Built via :func:`sign_strength_profile`.

    Attributes
    ----------
    planet : str
        The planet whose Bhinnashtakavarga is being profiled.
    sign_idx : int
        0-based sign index (0=Aries … 11=Pisces).
    rekha_count : int
        Number of rekhas in this sign (0–8).
    tier : str
        ``RekhaTier.STRONG`` or ``RekhaTier.WEAK`` relative to the
        threshold in the policy (default 4).
    """

    planet: str
    sign_idx: int
    rekha_count: int
    tier: str


# ---------------------------------------------------------------------------
# Phase 8 — Aggregate Intelligence
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AshtakavargaChartProfile:
    """Aggregate intelligence profile for a full Ashtakavarga chart.

    Derived from an :class:`AshtakavargaResult` via
    :func:`ashtakavarga_chart_profile`.

    Attributes
    ----------
    sarva_total : int
        Sum of all 12 Sarvashtakavarga rekha counts.
    sarva_max : int
        Highest Sarvashtakavarga count across the 12 signs.
    sarva_max_sign_idx : int
        Sign index (0–11) with the highest Sarvashtakavarga count.
    sarva_min : int
        Lowest Sarvashtakavarga count.
    sarva_min_sign_idx : int
        Sign index with the lowest Sarvashtakavarga count.
    strong_planet_sign_counts : dict[str, int]
        Mapping of planet name → number of signs with rekha count ≥
        ``strong_threshold`` in that planet's Bhinnashtakavarga.
    ayanamsa_system : str
        Ayanamsa system used for the underlying computation.
    """

    sarva_total: int
    sarva_max: int
    sarva_max_sign_idx: int
    sarva_min: int
    sarva_min_sign_idx: int
    strong_planet_sign_counts: dict[str, int]
    ayanamsa_system: str


# ---------------------------------------------------------------------------
# Phase 7 — Condition profile function
# ---------------------------------------------------------------------------

def sign_strength_profile(
    bhinna: BhinnashtakavargaResult,
    sign_idx: int,
    policy: AshtakavargaPolicy | None = None,
) -> SignStrengthProfile:
    """Build a :class:`SignStrengthProfile` for one sign in a
    :class:`BhinnashtakavargaResult`.

    Parameters
    ----------
    bhinna : BhinnashtakavargaResult
    sign_idx : int
        0-based sign index (0–11).
    policy : AshtakavargaPolicy or None
        Optional policy for the strong_threshold.  Defaults to 4.

    Returns
    -------
    SignStrengthProfile
    """
    if not (0 <= sign_idx <= 11):
        raise ValueError(f"sign_idx must be in [0, 11], got {sign_idx}")
    threshold = policy.strong_threshold if policy is not None else 4
    count = bhinna.rekhas[sign_idx]
    tier = RekhaTier.STRONG if count >= threshold else RekhaTier.WEAK
    return SignStrengthProfile(
        planet=bhinna.planet,
        sign_idx=sign_idx,
        rekha_count=count,
        tier=tier,
    )


# ---------------------------------------------------------------------------
# Phase 8 — Aggregate function
# ---------------------------------------------------------------------------

def ashtakavarga_chart_profile(
    result: AshtakavargaResult,
    policy: AshtakavargaPolicy | None = None,
) -> AshtakavargaChartProfile:
    """Build an :class:`AshtakavargaChartProfile` from an
    :class:`AshtakavargaResult`.

    Parameters
    ----------
    result : AshtakavargaResult
    policy : AshtakavargaPolicy or None
        Optional policy.  Controls the strong_threshold (default 4).

    Returns
    -------
    AshtakavargaChartProfile
    """
    threshold = policy.strong_threshold if policy is not None else 4
    sarva = result.sarvashtakavarga
    sarva_total = sum(sarva)
    sarva_max = max(sarva)
    sarva_max_sign_idx = sarva.index(sarva_max)
    sarva_min = min(sarva)
    sarva_min_sign_idx = sarva.index(sarva_min)
    strong_counts: dict[str, int] = {
        planet: len(result.bhinnashtakavarga[planet].strong_signs(threshold))
        for planet in _SEVEN_PLANETS
    }
    return AshtakavargaChartProfile(
        sarva_total=sarva_total,
        sarva_max=sarva_max,
        sarva_max_sign_idx=sarva_max_sign_idx,
        sarva_min=sarva_min,
        sarva_min_sign_idx=sarva_min_sign_idx,
        strong_planet_sign_counts=strong_counts,
        ayanamsa_system=result.ayanamsa_system,
    )


# ---------------------------------------------------------------------------
# Phase 10 — Full-subsystem hardening
# ---------------------------------------------------------------------------

def validate_ashtakavarga_output(result: AshtakavargaResult) -> None:
    """Validate structural invariants of an :class:`AshtakavargaResult`.

    Raises ``ValueError`` if any invariant is violated.

    Invariants checked
    ------------------
    - ``ayanamsa_system`` is non-empty.
    - ``sarvashtakavarga`` has 12 entries.
    - Each ``sarvashtakavarga[i]`` equals the sum of all 7 planet rekha
      counts for that sign.
    - ``bhinnashtakavarga`` contains exactly the 7 classical planets.
    - Each planet's ``total_rekhas`` equals ``sum(rekhas)``.

    Parameters
    ----------
    result : AshtakavargaResult

    Raises
    ------
    ValueError
        On any invariant violation.
    """
    if not result.ayanamsa_system:
        raise ValueError("ayanamsa_system must be non-empty")
    if len(result.sarvashtakavarga) != 12:
        raise ValueError(
            f"sarvashtakavarga must have 12 entries, got {len(result.sarvashtakavarga)}"
        )
    if set(result.bhinnashtakavarga) != set(_SEVEN_PLANETS):
        raise ValueError(
            f"bhinnashtakavarga must contain exactly the 7 classical planets, "
            f"got {sorted(result.bhinnashtakavarga)}"
        )
    for i in range(12):
        expected_sarva = sum(
            result.bhinnashtakavarga[p].rekhas[i] for p in _SEVEN_PLANETS
        )
        if result.sarvashtakavarga[i] != expected_sarva:
            raise ValueError(
                f"sarvashtakavarga[{i}] = {result.sarvashtakavarga[i]}, "
                f"expected {expected_sarva} (sum of planet rekhas)"
            )
    for planet, bhinna in result.bhinnashtakavarga.items():
        if bhinna.total_rekhas != sum(bhinna.rekhas):
            raise ValueError(
                f"{planet} total_rekhas ({bhinna.total_rekhas}) != "
                f"sum(rekhas) ({sum(bhinna.rekhas)})"
            )
