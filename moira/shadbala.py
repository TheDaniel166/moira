"""
Moira — Shadbala Engine
========================

Archetype: Engine

Purpose
-------
Computes the six-fold planetary strength (Shadbala) for the seven classical
planets under explicitly identified component conventions.  Shadbala is measured in Shashtiamsas
(Sha); 60 Sha = 1 Rupa.

The six Balas (strengths) and their sub-components:

  1. Sthana Bala    — Positional Strength (5 sub-components)
       a. Uchcha Bala        — exaltation proximity score
       b. Saptavargaja Bala  — dignity across 7 vargas (D1, D2, D3, D7, D9, D12, D30)
       c. Ojayugmarasyamsa   — odd/even sign bonus
       d. Kendradi Bala      — angular/succedent/cadent house position
       e. Drekkana Bala      — decan gender alignment
  2. Dig Bala       — Directional Strength (distance from strong directional house)
  3. Kala Bala      — Temporal Strength (6 sub-components)
       a. Nathonnatha        — day/night benefic/malefic strength
       b. Paksha Bala        — lunar phase strength
       c. Tribhaga Bala      — third-of-day/night strength
       d. Abda/Masa/Vara/Hora — year/month/weekday/hour lord bonus
       e. Ayana Bala         — solstice position strength
       f. Yuddha Bala        — planetary war victor bonus
  4. Chesta Bala    — Motional Strength (speed relative to mean motion)
  5. Naisargika Bala — Natural Fixed Strength (constant, never changes)
  6. Drig Bala      — Aspectual Strength (benefic minus malefic aspect weight)

Retained minimum Rupas (Moira convention):
  Sun:6.5, Moon:6.0, Mars:5.0, Mercury:7.0, Jupiter:6.5, Venus:5.5, Saturn:5.0

Bhava Bala (house strength, Raman Part II) is also computed here, three-fold:
  1. Bhavadhipati Bala  — house lord's total Shadbala piṇḍa
  2. Bhava Digbala      — madhya rasi locomotion class vs. house position
  3. Bhava Drishti Bala — sign-based aspect strength on the bhava madhya

Tradition and sources
---------------------
Raman, Bhava and Graha Balas (1996), articles 25/30, 47-57, 75-77:
selected relationship, Saptavargaja, Kala and pairwise-war rules. BPHS,
Santhanam I 27.2-4 supplies an alternative Saptavargaja scale only.
Independent arithmetic witnesses cover these selected components; this
module does not claim agreement with an entire published worked chart.
Required Rupas, ingress-based Abda/Masa, osculating Chesta and sign-based
Drig remain separately identified Moira conventions. A Saptavargaja profile
selection does not attribute those methods to that book.

Boundary declaration
--------------------
Owns: all six Shadbala sub-component computations, the ``SthanaBala``,
      ``KalaBala``, ``PlanetShadbala``, and ``ShadbalaResult`` vessels.
Delegates: Vedic dignity rank to ``moira.vedic_dignities``,
           varga sign indices to ``moira.varga``,
           panchanga elements (Vara, Paksha) to ``moira.panchanga``,
           sunrise/sunset to ``moira.rise_set``.

Import-time side effects: None

Calculation context and war policy
----------------------------------
Full results require a same-epoch ShadbalaContext. Dated callers derive
apparent geocentric positions, true equatorial declinations and actual
solar events through the serving reader. Synthetic callers supply context;
missing polar events produce typed unavailability, not a full ranking.
Nathonnatha uses apparent solar hour angle; Paksha uses continuous phase;
Tribhaga uses actual day/night thirds; Ayana uses the signed 24-degree
linear rule with planet-specific signs and Sun doubling. See the context
receipt for the explicitly selected Moon/Mercury nature convention.
Raman war detection uses separation strictly below one degree and the
lesser normalized longitude as victor. Pair amounts use pre-war Sthana +
Dig + Kala through Hora, divided by the fixed source disc-diameter
difference. Chesta is unchanged. Simultaneous pair accumulation and exact
ties with zero adjustment are named Moira conventions, not classical
multi-way attribution. The canonical ledger retains signed debits.

Public surface
--------------
``NAISARGIKA_BALA``       -- fixed natural strength constants (Sha).
``REQUIRED_RUPAS``        -- minimum Rupa threshold per planet.
``MEAN_DAILY_MOTION``     -- classical mean daily motions (deg/day).
``ShadbalaTier``          -- P2 classification: SUFFICIENT, INSUFFICIENT.
``SthanaBala``            -- immutable vessel for positional strength breakdown.
``KalaBala``              -- immutable vessel for temporal strength breakdown.
``PlanetShadbala``        -- immutable vessel for one planet's full Shadbala.
``ShadbalaResult``        -- immutable vessel for the full chart computation.
``ShadbalaPolicy``        -- P4 policy vessel.
``ShadbalaConditionProfile`` -- P7 local condition profile for one planet.
``ShadbalaChartProfile``  -- P8 aggregate chart profile.
``sthana_bala``           -- compute Sthana Bala for one planet.
``dig_bala``              -- compute Dig Bala for one planet.
``kala_bala``             -- compute Kala Bala for one planet.
``chesta_bala``           -- compute Chesta Bala for one planet.
``drig_bala``             -- compute Drig Bala for one planet.
``shadbala``              -- compute full Shadbala for all 7 planets.
``BhavaBala``             -- immutable vessel for one house's Bhava Bala.
``BhavaBalaResult``       -- immutable vessel for the 12-house computation.
``bhava_bala``            -- compute Bhava Bala for all 12 houses (Raman Part II).
``bhava_dig_bala``        -- compute Bhava Digbala for one house.
``bhava_drishti_bala``    -- compute Bhava Drishti Bala for one bhava madhya.
``hora_lord_at``          -- compute the planetary hora lord at a birth moment.
``shadbala_condition_profile`` -- P7 local condition profile builder.
``shadbala_chart_profile``     -- P8 aggregate chart profile builder.
``validate_shadbala_output``   -- P10 output validator.
``GrahaYuddha``               -- P5 war-pair vessel.
``graha_yuddha_pairs``        -- P5/P6 public war detection.
``ShadbalaNetworkProfile``    -- P9 strength-network profile.
``shadbala_network_profile``  -- P9 network profile builder.

Constitutional phases applied
-----------------------------
P1  -- Truth preservation: SthanaBala, KalaBala, PlanetShadbala, ShadbalaResult.
P2  -- Classification: ShadbalaTier.
P3  -- Inspectability: PlanetShadbala.strength_ratio,
      PlanetShadbala.ishta_phala / .kashta_phala (BPHS Ch. 27).
P4  -- Policy vessel: ShadbalaPolicy.
P5  -- Relational formalization: GrahaYuddha, graha_yuddha_pairs().
P6  -- Relational hardening: GrahaYuddha.__post_init__ invariants.
P7  -- Local condition profile: ShadbalaConditionProfile,
      shadbala_condition_profile().
P8  -- Aggregate chart profile: ShadbalaChartProfile,
      shadbala_chart_profile().
P9  -- Network profile: ShadbalaNetworkProfile, shadbala_network_profile().
P10 -- Hardening: PlanetShadbala.__post_init__, ShadbalaResult.__post_init__,
      validate_shadbala_output().
P11 -- Architecture freeze: wiki/02_standards/SHADBALA_BACKEND_STANDARD.md.
P12 -- Public API curation: __all__, docstring.
"""

import math
from dataclasses import dataclass, replace
from .shadbala_context import ShadbalaContext, ShadbalaContextError, derive_shadbala_context
from ._shadbala_components import (
    SaptavargajaEntry, saptavargaja_breakdown, kala_components, positional_components,
)

__all__ = [
    "ShadbalaContext", "ShadbalaContextError", "derive_shadbala_context",
    "SaptavargajaEntry", "saptavargaja_breakdown", "WarResolution",
    "NAISARGIKA_BALA",
    "REQUIRED_RUPAS",
    "MEAN_DAILY_MOTION",
    "ShadbalaTier",
    "SthanaBala",
    "KalaBala",
    "PlanetShadbala",
    "ShadbalaResult",
    "ShadbalaPolicy",
    "ShadbalaConditionProfile",
    "ShadbalaChartProfile",
    "BhavaBala",
    "BhavaBalaResult",
    "sthana_bala",
    "dig_bala",
    "kala_bala",
    "chesta_bala",
    "drig_bala",
    "shadbala",
    "bhava_bala",
    "bhava_dig_bala",
    "bhava_drishti_bala",
    "hora_lord_at",
    "shadbala_condition_profile",
    "shadbala_chart_profile",
    "validate_shadbala_output",
    "GrahaYuddha",
    "graha_yuddha_pairs",
    "ShadbalaNetworkProfile",
    "shadbala_network_profile",
]

# ---------------------------------------------------------------------------
# Seven classical planets
# ---------------------------------------------------------------------------

_SEVEN_PLANETS: tuple[str, ...] = (
    'Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn',
)

# Five planets eligible for Graha Yuddha (planetary war).  Sun and Moon
# never participate.  Source: Raman "Graha and Bhava Balas" (1959), Ch. 9.
_WAR_PLANETS: frozenset[str] = frozenset({'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn'})

# ---------------------------------------------------------------------------
# P5/P6 -- GrahaYuddha (planetary war vessel)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class GrahaYuddha:
    """
    P5 vessel for a Graha Yuddha (planetary war) between two non-luminaries.

    Detection uses separation strictly below one degree and lesser normalized
    longitude. Exact ties retain a lexical label and zero adjustment.
    ``adjustment_shashtiamsas`` is the actual Kala adjustment from the ledger;
    detection alone leaves it None. Deprecated ``chesta_transferred`` remains
    a legacy construction field; current computation never populates it.
    """

    victor:         str
    loser:          str
    separation_deg: float
    chesta_transferred: float | None = None
    adjustment_shashtiamsas: float | None = None
    tied: bool = False
    rule: str = "raman_1996_lesser_longitude"

    def __post_init__(self) -> None:
        if self.victor not in _WAR_PLANETS:
            raise ValueError(
                f"GrahaYuddha.victor must be one of {sorted(_WAR_PLANETS)}, "
                f"got {self.victor!r}"
            )
        if self.loser not in _WAR_PLANETS:
            raise ValueError(
                f"GrahaYuddha.loser must be one of {sorted(_WAR_PLANETS)}, "
                f"got {self.loser!r}"
            )
        if self.victor == self.loser:
            raise ValueError(
                "GrahaYuddha.victor and .loser must be different planets, "
                f"both are {self.victor!r}"
            )
        if not (0.0 <= self.separation_deg <= 1.0):
            raise ValueError(
                f"GrahaYuddha.separation_deg must be in (0, 1], "
                f"got {self.separation_deg}"
            )
        if self.adjustment_shashtiamsas is not None and (not math.isfinite(self.adjustment_shashtiamsas) or self.adjustment_shashtiamsas < 0):
            raise ValueError('war adjustment must be finite and nonnegative')
        if self.chesta_transferred is not None and not (
            0.0 <= self.chesta_transferred <= 60.0
        ):
            raise ValueError(
                f"GrahaYuddha.chesta_transferred must be in [0, 60] when "
                f"present, got {self.chesta_transferred}"
            )


# ---------------------------------------------------------------------------
# Naisargika Bala (Natural Fixed Strength — constant for all charts)
#
# Source: BPHS Shadbala Adhyaya; Raman "Graha and Bhava Balas" Ch. 5.
# Values in Shashtiamsas.
# ---------------------------------------------------------------------------

NAISARGIKA_BALA: dict[str, float] = {
    'Sun':     60.00,
    'Moon':    51.43,
    'Venus':   42.85,
    'Jupiter': 34.28,
    'Mercury': 25.70,
    'Mars':    17.14,
    'Saturn':   8.57,
}

# ---------------------------------------------------------------------------
# Retained minimum Rupas (separate from source-component profiles)
# ---------------------------------------------------------------------------

REQUIRED_RUPAS: dict[str, float] = {
    'Sun':     6.5,
    'Moon':    6.0,
    'Mars':    5.0,
    'Mercury': 7.0,
    'Jupiter': 6.5,
    'Venus':   5.5,
    'Saturn':  5.0,
}

# ---------------------------------------------------------------------------
# Mean daily motions (°/day) — used for Chesta Bala speed comparison.
#
# Source: Raman "Graha and Bhava Balas" Ch. 6; standard classical values.
# ---------------------------------------------------------------------------

MEAN_DAILY_MOTION: dict[str, float] = {
    'Sun':      0.9856,
    'Moon':    13.1764,
    'Mars':     0.5240,
    'Mercury':  1.3833,
    'Jupiter':  0.0831,
    'Venus':    1.2000,
    'Saturn':   0.0335,
}

# ---------------------------------------------------------------------------
# P2 -- ShadbalaTier classification
# ---------------------------------------------------------------------------

class ShadbalaTier:
    """
    P2 classification tier for a planet's Shadbala adequacy.

    SUFFICIENT   : total_rupas >= required_rupas (Parashara threshold met).
    INSUFFICIENT : total_rupas < required_rupas.
    """
    SUFFICIENT   = 'sufficient'
    INSUFFICIENT = 'insufficient'

# ---------------------------------------------------------------------------
# Directional strength houses (strong house cusp for each planet)
#
# Source: BPHS Dig Bala section; Raman "Graha and Bhava Balas" Ch. 7.
# ---------------------------------------------------------------------------

_DIG_STRONG_HOUSE: dict[str, int] = {
    'Sun':     9,    # 10th house (0-based: cusp index 9)
    'Mars':    9,
    'Jupiter': 0,    # 1st house (Ascendant)
    'Mercury': 0,
    'Moon':    3,    # 4th house
    'Venus':   3,
    'Saturn':  6,    # 7th house
}

# ---------------------------------------------------------------------------
# Bhava Bala — rasi locomotion classes and strong houses
#
# Governing object: Raman "Graha and Bhava Balas" (1959), Part II.  Every
# rasi (with half-sign splits in Sagittarius and Capricorn) belongs to one
# of four locomotion classes; each class attains full Bhava Digbala (60 Sha)
# when its bhava occupies one specific kendra, decreasing by 10 Sha per
# house of shortest circular distance (0 Sha at the opposite house).
#
#   Nara (human)          — Gemini, Virgo, Libra, Aquarius, Sagittarius 1st half → strong in H1
#   Jalachara (aquatic)   — Cancer, Pisces, Capricorn 2nd half                   → strong in H4
#   Keeta (insect)        — Scorpio                                              → strong in H7
#   Chatushpada (quadruped) — Aries, Taurus, Leo, Sagittarius 2nd half,
#                             Capricorn 1st half                                 → strong in H10
# ---------------------------------------------------------------------------

_BHAVA_CLASS_STRONG_HOUSE: dict[str, int] = {
    'nara':        1,
    'jalachara':   4,
    'keeta':       7,
    'chatushpada': 10,
}

# Whole-sign class by 0-based rasi index; None marks the two half-split rasis
# (Sagittarius = 8, Capricorn = 9) resolved degree-wise in _bhava_rasi_class.
_BHAVA_WHOLE_SIGN_CLASS: tuple[str | None, ...] = (
    'chatushpada',  # 0  Aries
    'chatushpada',  # 1  Taurus
    'nara',         # 2  Gemini
    'jalachara',    # 3  Cancer
    'chatushpada',  # 4  Leo
    'nara',         # 5  Virgo
    'nara',         # 6  Libra
    'keeta',        # 7  Scorpio
    None,           # 8  Sagittarius: 1st half nara, 2nd half chatushpada
    None,           # 9  Capricorn:   1st half chatushpada, 2nd half jalachara
    'nara',         # 10 Aquarius
    'jalachara',    # 11 Pisces
)

# Classical rasi lords by 0-based sign index (no nodal lordships in Shadbala).
# Source: BPHS; Raman "Graha and Bhava Balas" Part II (Bhavadhipathi Bala).
_RASI_LORDS: tuple[str, ...] = (
    'Mars', 'Venus', 'Mercury', 'Moon', 'Sun', 'Mercury',
    'Venus', 'Mars', 'Jupiter', 'Saturn', 'Saturn', 'Jupiter',
)

# ---------------------------------------------------------------------------
# Kala Bala — weekday and hora helpers
# ---------------------------------------------------------------------------

# Weekday-to-planet mapping.  Index = floor(jd + 1.5) % 7.
# 0 = Sunday = Sun, 1 = Monday = Moon, 2 = Tuesday = Mars,
# 3 = Wednesday = Mercury, 4 = Thursday = Jupiter,
# 5 = Friday = Venus, 6 = Saturday = Saturn.
_WEEKDAY_PLANET: tuple[str, ...] = (
    'Sun', 'Moon', 'Mars', 'Mercury', 'Jupiter', 'Venus', 'Saturn',
)

# Chaldean hora sequence (descending orbital-period order).
# Sunday's first hora is Sun; each successive hora advances one step.
# Source: BPHS Hora Bala Adhyaya; Raman "Graha and Bhava Balas" Ch. 4.
_HORA_SEQUENCE: tuple[str, ...] = (
    'Sun', 'Venus', 'Mercury', 'Moon', 'Saturn', 'Jupiter', 'Mars',
)


# ---------------------------------------------------------------------------
# Result vessels
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class SthanaBala:
    """
    Positional Strength breakdown (all values in Shashtiamsas).

    Attributes
    ----------
    uchcha : float
        Exaltation proximity score.  Max 60 Sha (at deepest exaltation);
        0 Sha at deepest debilitation.
    saptavargaja : float
        Dignity-based strength across D1, D2, D3, D7, D9, D12, D30.
        Max 140 Sha (7 × 20).
    ojayugma : float
        Odd/even sign bonus.  15 Sha if planet is in a favoured sign parity.
    kendradi : float
        Angular house bonus.  Kendra=60, Panapara=30, Apoklima=15 Sha.
    drekkana : float
        Decan gender alignment.  15 Sha if correct gender for decan.
    total : float
        Sum of all five sub-components.
    """

    uchcha:       float
    saptavargaja: float
    ojayugma:     float
    kendradi:     float
    drekkana:     float
    total:        float


@dataclass(frozen=True, slots=True)
class KalaBala:
    """
    Temporal Strength breakdown (all values in Shashtiamsas).

    Attributes
    ----------
    nathonnatha : float
        Day/night strength.  Max 60 Sha.
    paksha : float
        Lunar phase strength.  Max 60 Sha.
    tribhaga : float
        Third-of-day/night strength.  60 Sha if in strong period, else 0.
    abda_masa_vara_hora : float
        Year/month/weekday/hour lord bonus.  Abda=15 Sha, Masa=30 Sha, and
        Vara=45 Sha are always computed.  Hora=60 Sha is added when
        ``kala_bala()`` receives a non-None ``hora_lord`` argument.
        Source: Raman "Graha and Bhava Balas" Ch. 4.
    ayana : float
        Solstice position strength.  Derived from Sun's declination proxy.
    yuddha : float
        Planetary war victory bonus.  0 if no war, else loser's Chesta Bala.
    total : float
        Sum of all six sub-components.
    """

    nathonnatha:       float
    paksha:            float
    tribhaga:          float
    abda_masa_vara_hora: float
    ayana:             float
    yuddha:            float
    total:             float


@dataclass(frozen=True, slots=True)
class PlanetShadbala:
    """
    Full Shadbala result for one planet.

    Attributes
    ----------
    planet : str
        Planet name.
    sthana_bala : SthanaBala
        Positional Strength breakdown.
    dig_bala : float
        Directional Strength in Shashtiamsas.
    kala_bala : KalaBala
        Temporal Strength breakdown.
    chesta_bala : float
        Motional Strength in Shashtiamsas.
    naisargika_bala : float
        Natural Fixed Strength in Shashtiamsas (constant).
    drig_bala : float
        Aspectual Strength in Shashtiamsas.
    total_shashtiamsas : float
        Grand total of all six Balas in Shashtiamsas.
    total_rupas : float
        Grand total in Rupas (= total_shashtiamsas / 60).
    required_rupas : float
        Minimum strength threshold for this planet (Parashara).
    is_sufficient : bool
        ``True`` if ``total_rupas >= required_rupas``.
    """

    planet:             str
    sthana_bala:        SthanaBala
    dig_bala:           float
    kala_bala:          KalaBala
    chesta_bala:        float
    naisargika_bala:    float
    drig_bala:          float
    total_shashtiamsas: float
    total_rupas:        float
    required_rupas:     float
    is_sufficient:      bool

    def __post_init__(self) -> None:
        if self.planet not in _SEVEN_PLANETS:
            raise ValueError(
                f"PlanetShadbala.planet must be one of {_SEVEN_PLANETS}, "
                f"got {self.planet!r}"
            )
        if self.total_shashtiamsas < 0.0 and self.kala_bala.yuddha >= 0:
            raise ValueError(
                f"PlanetShadbala.total_shashtiamsas must be >= 0, "
                f"got {self.total_shashtiamsas}"
            )
        if self.required_rupas <= 0.0:
            raise ValueError(
                f"PlanetShadbala.required_rupas must be > 0, "
                f"got {self.required_rupas}"
            )

    @property
    def strength_ratio(self) -> float:
        """P3 -- total_rupas / required_rupas.  >= 1.0 means sufficient."""
        return self.total_rupas / self.required_rupas

    @property
    def ishta_phala(self) -> float:
        """P3 -- Iṣṭa Phala (benefic potential) in Shashtiamsas [0, 60].

        ``√(Uchcha Bala × Chesta Bala)`` per BPHS Ch. 27 (Ishta-Kashta
        Adhyaya); Raman, "Graha and Bhava Balas", Part on predicting
        results.  Uses this vessel's displayed Chesta Bala, so the Sun and
        Moon consume the retained motion convention shown in the breakdown.
        Canonical war adjustments leave Chesta unchanged.
        """
        u = min(max(self.sthana_bala.uchcha, 0.0), 60.0)
        c = min(max(self.chesta_bala, 0.0), 60.0)
        return math.sqrt(u * c)

    @property
    def kashta_phala(self) -> float:
        """P3 -- Kaṣṭa Phala (malefic potential) in Shashtiamsas [0, 60].

        ``√((60 − Uchcha Bala) × (60 − Chesta Bala))`` — the complement of
        Iṣṭa Phala.  Same BPHS Ch. 27 source and same displayed-Chesta
        policy as ``ishta_phala``.
        """
        u = min(max(self.sthana_bala.uchcha, 0.0), 60.0)
        c = min(max(self.chesta_bala, 0.0), 60.0)
        return math.sqrt((60.0 - u) * (60.0 - c))


@dataclass(frozen=True, slots=True)
class ShadbalaResult:
    """
    Full Shadbala computation for all seven classical planets.

    Attributes
    ----------
    jd : float
        Julian date (UT) of the natal chart.
    ayanamsa_system : str
        Ayanamsa system used for sidereal conversion.
    planets : dict[str, PlanetShadbala]
        Mapping of planet name → full Shadbala result for all 7 planets.
    """

    jd: float
    ayanamsa_system: str
    planets: dict[str, PlanetShadbala]

    war_resolution: 'WarResolution | None' = None
    context: ShadbalaContext | None = None
    saptavargaja_profile: str | None = None
    saptavargaja_evidence: tuple[tuple[str, tuple[SaptavargajaEntry, ...]], ...] = ()

    def __post_init__(self) -> None:
        if not self.ayanamsa_system:
            raise ValueError(
                "ShadbalaResult.ayanamsa_system must be non-empty"
            )
        if not math.isfinite(self.jd):
            raise ValueError(
                f"ShadbalaResult.jd must be a finite number, got {self.jd}"
            )


@dataclass(frozen=True, slots=True)
class BhavaBala:
    """
    Bhava Bala (house strength) result for one house.

    Source: Raman, "Graha and Bhava Balas" (1959), Part II.

    Attributes
    ----------
    house : int
        House number (1–12).
    madhya_sidereal_lon : float
        Sidereal longitude of the bhava madhya in degrees [0, 360).
    rasi_index : int
        0-based rasi index (0 = Aries) of the bhava madhya.
    rasi_class : str
        Locomotion class of the madhya rasi: ``'nara'``, ``'jalachara'``,
        ``'keeta'``, or ``'chatushpada'``.
    lord : str
        Classical lord of the madhya rasi.
    bhavadhipati_bala : float
        House lord's total Shadbala piṇḍa in Shashtiamsas.
    bhava_dig_bala : float
        Directional strength of the house in Shashtiamsas [0, 60].
    bhava_drishti_bala : float
        Aspectual strength on the bhava madhya in Shashtiamsas (signed:
        net malefic aspect yields a negative value).
    total_shashtiamsas : float
        Sum of the three components in Shashtiamsas.
    total_rupas : float
        Total in Rupas (= total_shashtiamsas / 60).
    rank : int
        Strength rank within the chart (1 = strongest of the 12 houses).
    """

    house:               int
    madhya_sidereal_lon: float
    rasi_index:          int
    rasi_class:          str
    lord:                str
    bhavadhipati_bala:   float
    bhava_dig_bala:      float
    bhava_drishti_bala:  float
    total_shashtiamsas:  float
    total_rupas:         float
    rank:                int

    def __post_init__(self) -> None:
        if not (1 <= self.house <= 12):
            raise ValueError(
                f"BhavaBala.house must be in [1, 12], got {self.house}"
            )
        if not (0 <= self.rasi_index <= 11):
            raise ValueError(
                f"BhavaBala.rasi_index must be in [0, 11], got {self.rasi_index}"
            )
        if self.rasi_class not in _BHAVA_CLASS_STRONG_HOUSE:
            raise ValueError(
                f"BhavaBala.rasi_class must be one of "
                f"{sorted(_BHAVA_CLASS_STRONG_HOUSE)}, got {self.rasi_class!r}"
            )
        if self.lord not in _SEVEN_PLANETS:
            raise ValueError(
                f"BhavaBala.lord must be one of {_SEVEN_PLANETS}, "
                f"got {self.lord!r}"
            )
        if not (0.0 <= self.bhava_dig_bala <= 60.0):
            raise ValueError(
                f"BhavaBala.bhava_dig_bala must be in [0, 60], "
                f"got {self.bhava_dig_bala}"
            )
        if not (1 <= self.rank <= 12):
            raise ValueError(
                f"BhavaBala.rank must be in [1, 12], got {self.rank}"
            )


@dataclass(frozen=True, slots=True)
class BhavaBalaResult:
    """
    Full Bhava Bala computation for all twelve houses.

    Attributes
    ----------
    jd : float
        Julian date (UT) of the natal chart.
    ayanamsa_system : str
        Ayanamsa system used for sidereal conversion.
    houses : dict[int, BhavaBala]
        Mapping of house number (1–12) → BhavaBala.
    strongest_house : int
        House number holding rank 1.
    weakest_house : int
        House number holding rank 12.
    """

    jd: float
    ayanamsa_system: str
    houses: dict[int, BhavaBala]
    strongest_house: int
    weakest_house: int

    def __post_init__(self) -> None:
        if not self.ayanamsa_system:
            raise ValueError(
                "BhavaBalaResult.ayanamsa_system must be non-empty"
            )
        if not math.isfinite(self.jd):
            raise ValueError(
                f"BhavaBalaResult.jd must be a finite number, got {self.jd}"
            )
        if set(self.houses.keys()) != set(range(1, 13)):
            raise ValueError(
                "BhavaBalaResult.houses must contain exactly houses 1-12, "
                f"got {sorted(self.houses.keys())}"
            )
        ranks = sorted(b.rank for b in self.houses.values())
        if ranks != list(range(1, 13)):
            raise ValueError(
                f"BhavaBalaResult ranks must be a permutation of 1-12, got {ranks}"
            )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _house_number(
    planet_sign: int,
    asc_sign: int,
) -> int:
    """Return 1-based house number (1–12) for a planet given the Ascendant sign."""
    return (planet_sign - asc_sign) % 12 + 1


def _arc_distance(lon_a: float, lon_b: float) -> float:
    """Minimum angular distance between two longitudes in [0, 180]."""
    diff = abs(lon_a - lon_b) % 360.0
    return diff if diff <= 180.0 else 360.0 - diff


def _bisection_root(f, a: float, b: float, tol: float = 1e-6, max_iter: int = 64) -> float:
    """Bisection root finder on a bracket [a, b]."""
    fa = f(a)
    fb = f(b)
    if fa == 0.0:
        return a
    if fb == 0.0:
        return b
    if fa * fb > 0.0:
        raise ValueError("Root is not bracketed")
    left, right = a, b
    for _ in range(max_iter):
        mid = 0.5 * (left + right)
        fm = f(mid)
        if abs(right - left) <= tol or fm == 0.0:
            return mid
        if fa * fm <= 0.0:
            right = mid
            fb = fm
        else:
            left = mid
            fa = fm
    return 0.5 * (left + right)


def _weekday_lord(jd: float) -> str:
    """Return the planetary lord of the weekday for the given Julian Day."""
    return _WEEKDAY_PLANET[int(jd + 1.5) % 7]




def _detect_wars(sidereal_longitudes, planet_latitudes=None, planet_speeds=None):
    """Raman 1996 art.76: separation <1 degree, lesser normalized longitude wins.

    Exact ties have a stable lexical label and zero adjustment under the
    explicit Moira composition rule. Latitudes/speeds are compatibility
    inputs, not evidence of a transfer. Actual amounts require the raw ledger.
    """
    from .varga import _normalize_longitude
    wars = []
    candidates = sorted(p for p in _WAR_PLANETS if p in sidereal_longitudes)
    for i,p1 in enumerate(candidates):
        for p2 in candidates[i+1:]:
            lon1 = _normalize_longitude(sidereal_longitudes[p1])
            lon2 = _normalize_longitude(sidereal_longitudes[p2])
            diff = _arc_distance(lon1, lon2)
            if diff >= 1:
                continue
            victor = p1 if lon1 <= lon2 else p2
            loser = p2 if victor == p1 else p1
            wars.append(GrahaYuddha(victor, loser, diff, tied=(diff == 0)))
    return tuple(wars)


@dataclass(frozen=True, slots=True)
class WarResolution:
    """Canonical simultaneous raw-pair ledger, a named Moira composition.

    Each Raman pair amount is evaluated once against immutable pre-war
    aggregates (Sthana + Dig + Kala through Hora, excluding Ayana). Every
    debit has an equal credit. Chesta remains unchanged; no finite Chesta
    pool is repeatedly spent. Signed Kala and signed net totals are retained.
    """
    pairs: tuple[GrahaYuddha, ...]
    raw_aggregates: tuple[tuple[str, float], ...]
    raw_totals: tuple[tuple[str, float], ...]
    raw_chesta: tuple[tuple[str, float], ...]
    credits: tuple[tuple[str, float], ...]
    debits: tuple[tuple[str, float], ...]
    adjustments: tuple[tuple[str, float], ...]
    policy: str = 'moira_simultaneous_raman_raw_pairs_v1'
    source: str = 'Raman1996:76-77:printed60-61'


def _resolve_wars(raw, positions):
    diameters = {'Mars':9.4, 'Mercury':6.6, 'Jupiter':190.4, 'Venus':16.6, 'Saturn':158.0}
    aggregates = {p: s.total + d + k.total - k.ayana for p,(s,d,k,c,n,dr) in raw.items()}
    totals = {p: s.total + d + k.total + c + n + dr for p,(s,d,k,c,n,dr) in raw.items()}
    credits = {p: [] for p in _SEVEN_PLANETS}
    debits = {p: [] for p in _SEVEN_PLANETS}
    resolved = []
    for war in _detect_wars(positions):
        amount = 0. if war.tied else abs(aggregates[war.victor]-aggregates[war.loser]) / abs(diameters[war.victor]-diameters[war.loser])
        resolved.append(replace(war, adjustment_shashtiamsas=amount))
        credits[war.victor].append(amount)
        debits[war.loser].append(amount)
    credit = {p: math.fsum(credits[p]) for p in _SEVEN_PLANETS}
    debit = {p: math.fsum(debits[p]) for p in _SEVEN_PLANETS}
    return WarResolution(tuple(resolved), tuple((p,aggregates[p]) for p in _SEVEN_PLANETS),
        tuple((p,totals[p]) for p in _SEVEN_PLANETS), tuple((p,raw[p][3]) for p in _SEVEN_PLANETS),
        tuple(credit.items()), tuple(debit.items()), tuple((p,credit[p]-debit[p]) for p in _SEVEN_PLANETS))


def _sankranti_jd(
    target_sidereal_lon: float,
    before_jd: float,
    ayanamsa_system: str,
    window_days: float = 32.0,
) -> float:
    """
    Find the Julian Day of the most recent Sankranti before ``before_jd``.

    A Sankranti is the moment at which the Sun's sidereal longitude equals
    an exact multiple of 30° (Rashi Sankranti) or 0° (Mesha Sankranti).  This
    function delegates to ``moira.panchanga.sankranti_at()``, which locates
    crossings using the Sun's actual apparent sidereal longitude rather than a
    mean-motion approximation.

    The bracket is ``[before_jd - window_days, before_jd]``.  Use
    ``window_days=32`` (default) for a Rashi / Masa Sankranti (at most one
    full solar month preceding the chart).  Use ``window_days=370`` for a
    Mesha / Abda Sankranti (at most one full solar year preceding the chart).
    Bisection converges to 1-second precision (tol ≈ 1.1574e-5 days).

    Parameters
    ----------
    target_sidereal_lon : float
        The sidereal longitude the Sun crossed most recently (degrees).
        For Mesha Sankranti: 0.0.  For Rashi Sankrantis: ``sun_sidereal_lon // 30 * 30``.
    before_jd : float
        The chart birth Julian Day; search window ends here.
    ayanamsa_system : str
        Ayanamsa system to use when converting tropical → sidereal.
    window_days : float
        Width of the backward search window in days.  Default 32.

    Returns
    -------
    float
        Julian Day (UT) of the Sankranti crossing.

    Source
    ------
    Delegates to ``moira.panchanga.sankranti_at``.
    """
    target = target_sidereal_lon % 360.0
    target_rashi_index = int(round(target / 30.0)) % 12
    from .panchanga import sankranti_at

    events = sankranti_at(
        before_jd - window_days,
        before_jd,
        ayanamsa_system=ayanamsa_system,
    )
    for event in reversed(events):
        if event.rashi_index == target_rashi_index:
            return event.jd

    raise ValueError(
        f"No Sankranti at {target:.1f}° found in the {window_days:.0f}-day "
        f"window before JD {before_jd}."
    )


def hora_lord_at(birth_jd: float, sunrise_jd: float) -> str:
    """
    Compute the planetary hora lord at birth.

    Uses equal 60-minute horas (Parashari system).  The first hora of each
    day begins at sunrise and is ruled by the weekday lord of that day.
    Subsequent horas follow the Chaldean sequence::

        Sun → Venus → Mercury → Moon → Saturn → Jupiter → Mars → (repeat)

    Parameters
    ----------
    birth_jd : float
        Julian date (UT) of the birth moment.
    sunrise_jd : float
        Julian date (UT) of sunrise on the birth day.  Compute with
        ``moira.rise_set`` for location-accurate results.

    Returns
    -------
    str
        Planet name of the ruling hora lord.

    Source
    ------
    Raman, "Graha and Bhava Balas" (1959), Ch. 4; BPHS Hora Bala Adhyaya.
    """
    vara = _weekday_lord(sunrise_jd)
    start = _HORA_SEQUENCE.index(vara)
    hora_num = int((birth_jd - sunrise_jd) * 24)
    return _HORA_SEQUENCE[(start + hora_num) % 7]


# ---------------------------------------------------------------------------
# Sub-component functions
# ---------------------------------------------------------------------------

def sthana_bala(
    planet: str,
    sidereal_lon: float,
    houses: object,
    jd: float,
    ayanamsa_system: str = 'Lahiri',
    *,
    sidereal_longitudes: dict[str, float] | None = None,
    saptavargaja_profile: str = 'raman_1996',
) -> SthanaBala:
    """
    Compute Sthana Bala (Positional Strength) for one planet.

    Parameters
    ----------
    planet : str
        One of the seven classical planets.
    sidereal_lon : float
        Sidereal longitude of the planet in degrees.
    houses : HouseCusps
        Chart house cusps.  Used for Kendradi Bala (house number).
        ``houses.asc`` is the tropical Ascendant longitude.
    jd : float
        Julian date; used for Saptavargaja varga computations.
    ayanamsa_system : str
        Ayanamsa system.

    Returns
    -------
    SthanaBala
    """
    from .sidereal import tropical_to_sidereal
    from .varga import _normalize_longitude

    lon = _normalize_longitude(sidereal_lon)

    uchcha_sha, ojayugma_sha, drekkana_sha = positional_components(planet, lon)

    entries = saptavargaja_breakdown(planet, lon, sidereal_longitudes, saptavargaja_profile)
    saptavargaja_sha = sum(e.shashtiamsas for e in entries)

    d1_sign  = int(lon // 30)

    # --- (d) Kendradi Bala ---
    asc_trop = float(getattr(houses, 'asc', 0.0))
    asc_sid  = tropical_to_sidereal(asc_trop, jd, system=ayanamsa_system)
    asc_sign = int(asc_sid % 360.0 // 30)
    house_no = _house_number(d1_sign, asc_sign)
    if house_no in {1, 4, 7, 10}:
        kendradi_sha = 60.0
    elif house_no in {2, 5, 8, 11}:
        kendradi_sha = 30.0
    else:
        kendradi_sha = 15.0

    total = uchcha_sha + saptavargaja_sha + ojayugma_sha + kendradi_sha + drekkana_sha
    return SthanaBala(
        uchcha=uchcha_sha,
        saptavargaja=saptavargaja_sha,
        ojayugma=ojayugma_sha,
        kendradi=kendradi_sha,
        drekkana=drekkana_sha,
        total=total,
    )


def dig_bala(
    planet: str,
    sidereal_lon: float,
    houses: object,
    jd: float,
    ayanamsa_system: str = 'Lahiri',
) -> float:
    """
    Compute Dig Bala (Directional Strength) for one planet.

    Each planet has a "strong direction" (a house cusp where it reaches
    maximum Dig Bala of 60 Sha).  Strength decreases linearly with angular
    distance from that cusp, reaching 0 Sha at the opposite cusp.

    Parameters
    ----------
    planet : str
    sidereal_lon : float
        Sidereal longitude of the planet.
    houses : HouseCusps
        Chart house cusps; must expose a ``cusps`` attribute (tuple/list of
        12 tropical longitudes, 0-based, cusp[0] = Ascendant).
    jd : float
    ayanamsa_system : str

    Returns
    -------
    float
        Dig Bala in Shashtiamsas, in [0.0, 60.0].
    """
    from .sidereal import tropical_to_sidereal

    strong_house_idx = _DIG_STRONG_HOUSE.get(planet)
    if strong_house_idx is None:
        return 0.0

    cusps_trop = getattr(houses, 'cusps', None)
    if cusps_trop is None:
        # Fallback: use equal house from Ascendant
        asc_trop  = float(getattr(houses, 'asc', 0.0))
        asc_sid   = tropical_to_sidereal(asc_trop, jd, system=ayanamsa_system)
        strong_lon = (asc_sid + strong_house_idx * 30.0) % 360.0
    else:
        strong_trop = float(cusps_trop[strong_house_idx])
        strong_lon  = tropical_to_sidereal(strong_trop, jd, system=ayanamsa_system)

    lon = sidereal_lon % 360.0
    dist = _arc_distance(lon, strong_lon)   # 0–180°
    return (180.0 - dist) / 3.0            # max 60 Sha


def kala_bala(
    planet: str,
    sidereal_lon: float,
    sun_sidereal_lon: float,
    jd: float,
    tithi_number: int,
    is_day: bool,
    vara_lord: str,
    planet_speeds: dict[str, float],
    hora_lord: str | None = None,
    ayanamsa_system: str = 'Lahiri',
    local_day_frac: float | None = None,
    *,
    context: ShadbalaContext | None = None,
) -> KalaBala:
    """Compute source-defined temporal strength from explicit context.

    ``jd`` is UT; positions and ayanamsa must match the context. Declinations
    are tropical true-equatorial degrees. Day/vara/hora and any supplied
    apparent solar fraction must agree with that context. Tithi and speeds
    are retained compatibility inputs; continuous phase governs Paksha.
    Missing solar events raise ShadbalaContextError without ephemeris fallback.
    """
    if not isinstance(context, ShadbalaContext):
        raise ShadbalaContextError('Kala Bala requires explicit same-epoch solar and declination context')
    context.check_positions(jd, ayanamsa_system, {planet: sidereal_lon, 'Sun': sun_sidereal_lon})
    if local_day_frac is not None and local_day_frac != context.local_apparent_day_fraction:
        raise ShadbalaContextError('local solar time disagrees with context')
    if is_day != context.is_day or vara_lord != context.vara_lord or hora_lord != context.hora_lord:
        raise ShadbalaContextError('day/vara/hora inputs disagree with context')
    values = kala_components(planet, context)
    return KalaBala(*values, 0., sum(values))


def chesta_bala(
    planet: str,
    speed: float | None = None,
    *,
    planet_sidereal_lon: float | None = None,
    sun_sidereal_lon: float | None = None,
    mean_longitude: float | None = None,
    seeghrochcha: float | None = None,
    chesta_kendra: float | None = None,
    planet_tropical_lon: float | None = None,
    jd: float | None = None,
    ayanamsa_system: str = "Lahiri",
    reader: object | None = None,
) -> float:
    """
    Compute Chesta Bala (Motional Strength) for one planet.

    Primary-Source Formulations:
    B. V. Raman, "Graha and Bhava Balas" (13th edition, 1992):

    1. The Five Non-Luminaries (Mars, Mercury, Jupiter, Venus, Saturn):
       Chapter VI ("Chesta Bala or Motional Strength", pp. 64–79).
       Governed by Chesta Kendra, derived from the apex of fast motion
       (Seeghrochcha), the mean longitude, and the true longitude:

           Chesta Kendra = (Seeghrochcha - (mean_lon + true_lon) / 2) mod 360°
           Reduced Kendra = 360° - Kendra if Kendra > 180° else Kendra
           Chesta Bala = Reduced Kendra / 3  ∈ [0, 60] Shashtiamsas (Virupas)

       - For superior planets (Mars, Jupiter, Saturn): Seeghrochcha is the Sun;
         mean longitude is the planet's mean heliocentric longitude.
       - For inferior planets (Mercury, Venus): Seeghrochcha is the planet's
         heliocentric longitude; mean longitude is the Sun.

    2. The Sun:
       Chapter X (§136, pp. 101–103).
       Derived from its Sayana (tropical) longitude + 90°:

           Arc = (lon_sayana + 90°) mod 360°
           Reduced Arc = 360° - Arc if Arc > 180° else Arc
           Chesta Bala = Reduced Arc / 3  ∈ [0, 60] Shashtiamsas

       (Motional/Ayana proxy: 60 Sha at northern solstice/Cancer ingress,
       0 Sha at southern solstice/Capricorn ingress, 30 Sha at equinoxes).

    3. The Moon:
       Chapter X (§137, pp. 101–103).
       Derived from its elongation (angular distance from the Sun):

           Elongation = |lon_Moon - lon_Sun| mod 360°
           Reduced Elongation = 360° - Elongation if Elongation > 180° else Elongation
           Chesta Bala = Reduced Elongation / 3  ∈ [0, 60] Shashtiamsas

       (Motional/Paksha proxy: 0 Sha at New Moon/conjunction, 60 Sha at
       Full Moon/opposition, 30 Sha at quarters).

    Parameters
    ----------
    planet : str
        Name of the planet (one of the classical 7 planets).
    speed : float or None, optional
        Daily motion in °/day. Retained as a fallback for callers without
        coordinates or ephemeris access.
    planet_sidereal_lon : float or None, optional
        Sidereal longitude of the planet.
    sun_sidereal_lon : float or None, optional
        Sidereal longitude of the Sun (required for Moon, and for non-luminaries
        when deriving from the orbital core).
    mean_longitude : float or None, optional
        Mean longitude of the planet (or Sun for inferior planets).
    seeghrochcha : float or None, optional
        Apex of fast motion (Seeghrochcha) in sidereal degrees.
    chesta_kendra : float or None, optional
        Pre-computed Chesta Kendra arc in degrees [0, 360).
    planet_tropical_lon : float or None, optional
        Tropical (Sayana) longitude of the planet (primarily for Sun).
    jd : float or None, optional
        Julian date UT1 for orbital element evaluation.
    ayanamsa_system : str
        Ayanamsa system name (defaults to 'Lahiri').
    reader : KernelReader or None, optional
        Active SPK kernel reader. When omitted, uses the active reader context.

    Returns
    -------
    float
        Chesta Bala in Shashtiamsas, strictly in [0.0, 60.0].

    Source
    ------
    B. V. Raman, "Graha and Bhava Balas" (13th edition, 1992), Ch. VI & X.
    """
    if planet not in _SEVEN_PLANETS:
        raise ValueError(
            f"chesta_bala: planet must be one of {list(_SEVEN_PLANETS)}, "
            f"got {planet!r}"
        )

    # 1. Direct Chesta Kendra path
    if chesta_kendra is not None:
        kendra = chesta_kendra % 360.0
        red = 360.0 - kendra if kendra > 180.0 else kendra
        return max(0.0, min(60.0, red / 3.0))

    # 2. Sun (Raman Ch. X §136)
    if planet == "Sun":
        trop_lon = planet_tropical_lon
        if trop_lon is None and planet_sidereal_lon is not None and jd is not None:
            from .sidereal import sidereal_to_tropical
            trop_lon = sidereal_to_tropical(planet_sidereal_lon, jd, system=ayanamsa_system)
        if trop_lon is not None:
            arc = (trop_lon + 90.0) % 360.0
            red = 360.0 - arc if arc > 180.0 else arc
            return max(0.0, min(60.0, red / 3.0))
        if speed is not None:
            mean = MEAN_DAILY_MOTION.get("Sun", 0.9856)
            ratio = min(abs(speed) / mean, 2.0)
            return max(0.0, min(60.0, ratio * 30.0))
        raise ValueError("chesta_bala for Sun requires planet_tropical_lon, (planet_sidereal_lon, jd), or speed")

    # 3. Moon (Raman Ch. X §137)
    if planet == "Moon":
        m_lon = planet_sidereal_lon
        s_lon = sun_sidereal_lon
        if m_lon is not None and s_lon is not None:
            elong = abs(m_lon - s_lon) % 360.0
            red = 360.0 - elong if elong > 180.0 else elong
            return max(0.0, min(60.0, red / 3.0))
        if planet_tropical_lon is not None and s_lon is not None and jd is not None:
            from .sidereal import sidereal_to_tropical
            s_trop = sidereal_to_tropical(s_lon, jd, system=ayanamsa_system)
            elong = abs(planet_tropical_lon - s_trop) % 360.0
            red = 360.0 - elong if elong > 180.0 else elong
            return max(0.0, min(60.0, red / 3.0))
        if speed is not None:
            mean = MEAN_DAILY_MOTION.get("Moon", 13.1764)
            ratio = min(abs(speed) / mean, 2.0)
            return max(0.0, min(60.0, ratio * 30.0))
        raise ValueError("chesta_bala for Moon requires planet_sidereal_lon and sun_sidereal_lon, or speed")

    # 4. Five Non-Luminaries (Raman Ch. VI)
    if seeghrochcha is not None and mean_longitude is not None and planet_sidereal_lon is not None:
        kendra = (seeghrochcha - (mean_longitude + planet_sidereal_lon) / 2.0) % 360.0
        red = 360.0 - kendra if kendra > 180.0 else kendra
        return max(0.0, min(60.0, red / 3.0))

    if jd is not None and planet_sidereal_lon is not None and sun_sidereal_lon is not None:
        from .orbits import osculating_elements, OrbitalCenter, OrbitalFrame
        from .sidereal import tropical_to_sidereal
        from .spk_reader import get_reader as _get_reader
        r = reader if reader is not None else _get_reader()
        el = osculating_elements(
            planet,
            jd,
            center=OrbitalCenter.SUN,
            frame=OrbitalFrame.TRUE_ECLIPTIC_OF_DATE,
            reader=r,
        )
        if planet in ("Mars", "Jupiter", "Saturn"):
            s_lon = sun_sidereal_lon
            mean_deg = el.mean_longitude_deg if el.mean_longitude_deg is not None else el.true_longitude_deg
            m_lon = tropical_to_sidereal(mean_deg, jd, system=ayanamsa_system)
        else:  # Mercury, Venus
            s_lon = tropical_to_sidereal(el.true_longitude_deg, jd, system=ayanamsa_system)
            m_lon = sun_sidereal_lon

        kendra = (s_lon - (m_lon + planet_sidereal_lon) / 2.0) % 360.0
        red = 360.0 - kendra if kendra > 180.0 else kendra
        return max(0.0, min(60.0, red / 3.0))

    # 5. Speed-ratio fallback (when coordinates / ephemeris are absent)
    if speed is not None:
        if speed < 0:
            return 60.0  # Retrograde = maximum Chesta Bala
        mean = MEAN_DAILY_MOTION.get(planet, 1.0)
        if mean <= 0:
            return 0.0
        ratio = min(abs(speed) / mean, 2.0)
        return max(0.0, min(60.0, ratio * 30.0))

    raise ValueError(
        f"chesta_bala for {planet} requires seeghrochcha and mean_longitude, "
        f"or (planet_sidereal_lon, sun_sidereal_lon, jd), or speed"
    )


def drig_bala(
    planet: str,
    sidereal_longitudes: dict[str, float],
) -> float:
    """
    Compute Drig Bala (Aspectual Strength) for one planet.

    Uses sign-based Vedic aspect doctrine.  Benefics (Jupiter, Venus,
    waxing-Moon proxy, Mercury) contribute positive aspects; malefics
    (Sun, Mars, Saturn) contribute negative.

    Aspect weights (Raman):
      Full aspect (7th sign):                    1.0
      Three-quarter aspect (Mars 4th/8th,
        Jupiter 5th/9th, Saturn 3rd/10th):       0.75
      Half aspect (5th/9th for others):          0.5
      Quarter aspect (3rd/10th for others):      0.25

    Parameters
    ----------
    planet : str
        The planet receiving aspects.
    sidereal_longitudes : dict[str, float]
        Sidereal longitudes of all participating planets (7 classical).

    Returns
    -------
    float
        Drig Bala in Shashtiamsas.  Positive values indicate net benefic
        influence; negative indicate net malefic (possible in theory).
    """
    if planet not in sidereal_longitudes:
        return 0.0

    planet_sign = int(sidereal_longitudes[planet] % 360.0 // 30)
    return _sign_aspect_drig_sha(planet_sign, sidereal_longitudes, exclude=planet)


def _sign_aspect_drig_sha(
    target_sign: int,
    sidereal_longitudes: dict[str, float],
    exclude: str | None = None,
) -> float:
    """
    Net benefic-minus-malefic sign-based aspect strength on *target_sign*.

    Shared aspect core for Graha Drig Bala (target = the aspected planet's
    sign, with the planet itself excluded) and Bhava Drishti Bala (target =
    the bhava madhya's sign, with all seven planets aspecting).  Weights per
    Raman: full (7th) 1.0; special three-quarter (Mars 4/8, Jupiter 5/9,
    Saturn 3/10) 0.75; half (5/9) 0.5; quarter (3/10) 0.25.
    """
    benefics  = {'Jupiter', 'Venus', 'Moon', 'Mercury'}
    malefics  = {'Sun', 'Mars', 'Saturn'}

    # Special aspects beyond 7th (in addition to default 7th)
    special_aspects: dict[str, set[int]] = {
        'Mars':    {4, 8},
        'Jupiter': {5, 9},
        'Saturn':  {3, 10},
    }

    drig_sha = 0.0
    for asp_planet, asp_lon in sidereal_longitudes.items():
        if asp_planet == exclude:
            continue
        asp_sign = int(asp_lon % 360.0 // 30)
        # 1-based sign-distance from asp_planet to the aspected sign
        dist = (target_sign - asp_sign) % 12 + 1   # 1–12

        weight = 0.0
        if dist == 7:
            weight = 1.0
        elif asp_planet in special_aspects and dist in special_aspects[asp_planet]:
            weight = 0.75
        elif dist in {5, 9}:
            weight = 0.5
        elif dist in {3, 10}:
            weight = 0.25

        if weight > 0:
            if asp_planet in benefics:
                drig_sha += weight * 60.0
            elif asp_planet in malefics:
                drig_sha -= weight * 60.0

    return drig_sha


# ---------------------------------------------------------------------------
# Bhava Bala — house strength (Raman Part II)
# ---------------------------------------------------------------------------

def _bhava_rasi_class(sidereal_lon: float) -> str:
    """
    Return the locomotion class of the rasi holding *sidereal_lon*.

    Whole-sign for ten rasis; degree-resolved for the two half-split rasis
    (Sagittarius: 1st half nara, 2nd half chatushpada; Capricorn: 1st half
    chatushpada, 2nd half jalachara).  Source: Raman Part II, Bhava Digbala.
    """
    lon = sidereal_lon % 360.0
    sign = int(lon // 30)
    cls = _BHAVA_WHOLE_SIGN_CLASS[sign]
    if cls is not None:
        return cls
    first_half = (lon % 30.0) < 15.0
    if sign == 8:    # Sagittarius
        return 'nara' if first_half else 'chatushpada'
    # sign == 9 — Capricorn
    return 'chatushpada' if first_half else 'jalachara'


def _bhava_madhya_sidereal(
    houses: object,
    jd: float,
    ayanamsa_system: str,
) -> list[float]:
    """
    Return the twelve bhava madhya sidereal longitudes, houses 1–12 in order.

    Policy (explicit): the chart's house cusps are taken as the bhava
    madhya reference points, mirroring the module-wide house doctrine used
    by ``dig_bala`` (``houses.cusps`` are 12 tropical longitudes, 0-based,
    ``cusps[0]`` = Ascendant).  When ``cusps`` is unavailable, equal houses
    from the Ascendant are used, with the Ascendant as madhya of house 1.
    """
    from .sidereal import tropical_to_sidereal

    cusps_trop = getattr(houses, 'cusps', None)
    if cusps_trop is None:
        asc_trop = float(getattr(houses, 'asc', 0.0))
        asc_sid  = tropical_to_sidereal(asc_trop, jd, system=ayanamsa_system)
        return [(asc_sid + i * 30.0) % 360.0 for i in range(12)]
    return [
        tropical_to_sidereal(float(cusps_trop[i]), jd, system=ayanamsa_system) % 360.0
        for i in range(12)
    ]


def bhava_dig_bala(house: int, madhya_sidereal_lon: float) -> float:
    """
    Compute Bhava Digbala (house directional strength) for one house.

    The madhya's rasi class fixes the strong house (nara → 1, jalachara → 4,
    keeta → 7, chatushpada → 10); strength is 60 Sha there, decreasing by
    10 Sha per house of shortest circular distance, 0 Sha opposite.

    Source: Raman, "Graha and Bhava Balas" (1959), Part II.

    Parameters
    ----------
    house : int
        House number (1–12).
    madhya_sidereal_lon : float
        Sidereal longitude of the bhava madhya.

    Returns
    -------
    float
        Bhava Digbala in Shashtiamsas, in [0.0, 60.0].
    """
    strong = _BHAVA_CLASS_STRONG_HOUSE[_bhava_rasi_class(madhya_sidereal_lon)]
    dist = min((house - strong) % 12, (strong - house) % 12)   # 0–6
    return 60.0 - 10.0 * dist


def bhava_drishti_bala(
    madhya_sidereal_lon: float,
    sidereal_longitudes: dict[str, float],
) -> float:
    """
    Compute Bhava Drishti Bala (aspect strength on the bhava madhya).

    The bhava madhya is treated as the aspected point ("taking the mid cusp
    of the Bhava as the aspected planet" — Raman Part II), with all seven
    classical planets aspecting.  Uses the module's declared sign-based
    Vedic aspect doctrine, identical to ``drig_bala``.

    Returns
    -------
    float
        Bhava Drishti Bala in Shashtiamsas (signed; net malefic aspect
        yields a negative value).
    """
    target_sign = int(madhya_sidereal_lon % 360.0 // 30)
    return _sign_aspect_drig_sha(target_sign, sidereal_longitudes)


def bhava_bala(
    shadbala_result: ShadbalaResult,
    sidereal_longitudes: dict[str, float],
    houses: object,
) -> BhavaBalaResult:
    """
    Compute Bhava Bala (house strength) for all twelve houses.

    Bhava Bala is three-fold (Raman, "Graha and Bhava Balas", Part II):

      1. Bhavadhipati Bala — the total Shadbala piṇḍa of the house lord
         (classical lord of the rasi holding the bhava madhya).
      2. Bhava Digbala     — directional strength from the madhya rasi's
         locomotion class (see ``bhava_dig_bala``).
      3. Bhava Drishti Bala — sign-based aspect strength on the madhya
         (see ``bhava_drishti_bala``).

    Houses are ranked by total strength (rank 1 = strongest; ties broken
    by lower house number).  The birth moment and ayanamsa are taken from
    *shadbala_result* so the two computations cannot disagree.

    Parameters
    ----------
    shadbala_result : ShadbalaResult
        Output of ``shadbala()`` for the same chart; supplies each house
        lord's total piṇḍa plus the chart's jd and ayanamsa system.
    sidereal_longitudes : dict[str, float]
        Sidereal longitudes for all 7 classical planets (same input that
        produced *shadbala_result*).
    houses : HouseCusps
        Chart house cusps (same object passed to ``shadbala()``).

    Returns
    -------
    BhavaBalaResult
    """
    if shadbala_result.context is not None:
        validate_shadbala_output(shadbala_result)
        shadbala_result.context.check_positions(
            shadbala_result.jd, shadbala_result.ayanamsa_system, sidereal_longitudes)
        canonical = dict(shadbala_result.context.sidereal_longitudes)
        sidereal_longitudes = {p: canonical[p] for p in sidereal_longitudes}
    madhyas = _bhava_madhya_sidereal(
        houses, shadbala_result.jd, shadbala_result.ayanamsa_system,
    )

    records: list[dict] = []
    for house in range(1, 13):
        madhya = madhyas[house - 1]
        rasi_index = int(madhya // 30)
        lord = _RASI_LORDS[rasi_index]
        adhipati = shadbala_result.planets[lord].total_shashtiamsas
        dig = bhava_dig_bala(house, madhya)
        drishti = bhava_drishti_bala(madhya, sidereal_longitudes)
        records.append({
            'house': house,
            'madhya': madhya,
            'rasi_index': rasi_index,
            'rasi_class': _bhava_rasi_class(madhya),
            'lord': lord,
            'adhipati': adhipati,
            'dig': dig,
            'drishti': drishti,
            'total': adhipati + dig + drishti,
        })

    # Rank 1 = strongest; ties broken by lower house number.
    by_strength = sorted(records, key=lambda r: (-r['total'], r['house']))
    ranks = {r['house']: i + 1 for i, r in enumerate(by_strength)}

    result: dict[int, BhavaBala] = {}
    for r in records:
        result[r['house']] = BhavaBala(
            house=r['house'],
            madhya_sidereal_lon=r['madhya'],
            rasi_index=r['rasi_index'],
            rasi_class=r['rasi_class'],
            lord=r['lord'],
            bhavadhipati_bala=r['adhipati'],
            bhava_dig_bala=r['dig'],
            bhava_drishti_bala=r['drishti'],
            total_shashtiamsas=r['total'],
            total_rupas=r['total'] / 60.0,
            rank=ranks[r['house']],
        )

    return BhavaBalaResult(
        jd=shadbala_result.jd,
        ayanamsa_system=shadbala_result.ayanamsa_system,
        houses=result,
        strongest_house=by_strength[0]['house'],
        weakest_house=by_strength[-1]['house'],
    )


# ---------------------------------------------------------------------------
# Public top-level function
# ---------------------------------------------------------------------------

def shadbala(
    sidereal_longitudes: dict[str, float],
    planet_speeds: dict[str, float],
    houses: object,
    jd: float,
    tithi_number: int,
    vara_lord: str,
    is_day: bool,
    ayanamsa_system: str = 'Lahiri',
    hora_lord: str | None = None,
    planet_latitudes: dict[str, float] | None = None,
    *,
    context: ShadbalaContext | None = None,
    policy: 'ShadbalaPolicy | None' = None,
) -> ShadbalaResult:
    """
    Compute full Shadbala for all seven classical planets.

    Parameters
    ----------
    sidereal_longitudes : dict[str, float]
        Sidereal longitudes for all 7 classical planets.  Caller is
        responsible for tropical-to-sidereal conversion.
    planet_speeds : dict[str, float]
        Daily motion (°/day, signed) for all 7 planets.
    houses : HouseCusps
        Chart house cusps from ``moira.houses.calculate_houses``.
        Must expose ``.asc`` (tropical Ascendant longitude) and optionally
        ``.cusps`` (12-element tuple of tropical house cusp longitudes).
    jd : float
        Julian date (UT) of the birth moment.
    tithi_number : int
        Current Tithi (1–30) from ``moira.panchanga.panchanga_at``.
    vara_lord : str
        Weekday planetary lord from ``moira.panchanga.panchanga_at``.
    is_day : bool
        ``True`` if birth is during daytime.  Obtainable from
        ``ChartContext.is_day`` or via ``moira.rise_set``.
    ayanamsa_system : str
        Ayanamsa system.  Defaults to ``'Lahiri'``.
    hora_lord : str or None, optional
        Planetary lord of the birth hora.  Forwarded to ``kala_bala()``.
        Compute via ``hora_lord_at(birth_jd, sunrise_jd)``.
    planet_latitudes : dict or None
        Retained compatibility input; the selected Raman war rule uses longitude.
    context : ShadbalaContext
        Required same-epoch geometry, continuous phase and motion evidence.
    policy : ShadbalaPolicy or None
        Named Saptavargaja scale; defaults to Raman 1996. Other component
        conventions retain their separate attribution.

    Returns
    -------
    ShadbalaResult

    Raises
    ------
    ValueError
        If ``tithi_number`` is not in [1, 30].
    KeyError
        If a required planet is absent from ``sidereal_longitudes`` or
        ``planet_speeds``.
    """
    if type(tithi_number) is not int or not (1 <= tithi_number <= 30):
        raise ValueError(f"tithi_number must be in [1, 30], got {tithi_number}")

    active = ShadbalaPolicy(ayanamsa_system) if policy is None else policy
    if set(sidereal_longitudes) != set(_SEVEN_PLANETS):
        raise ShadbalaContextError('full Shadbala requires exactly seven classical positions')
    for planet in _SEVEN_PLANETS:
        speed = planet_speeds[planet]
        if isinstance(speed,bool) or not isinstance(speed,(int,float)) or not math.isfinite(speed):
            raise ValueError('planet speeds must be finite numbers')
    if active.ayanamsa_system != ayanamsa_system:
        raise ShadbalaContextError('policy ayanamsa must match input frame')
    if not isinstance(context, ShadbalaContext):
        raise ShadbalaContextError('Full Shadbala requires explicit context; dated callers use derive_shadbala_context')
    context.check_positions(jd, ayanamsa_system, sidereal_longitudes)
    context.require_complete()
    # The receipt is authoritative after same-frame comparison (1e-9 degrees).
    # Use its normalized values consistently at discrete Varga boundaries.
    sidereal_longitudes = dict(context.sidereal_longitudes)
    sun_sid = sidereal_longitudes['Sun']

    # --- First pass: raw balas for all planets (yuddha = 0 initially) ---
    _raw: dict[str, tuple] = {}
    for planet in _SEVEN_PLANETS:
        p_lon   = sidereal_longitudes[planet]
        _ = planet_speeds[planet]

        s_bala  = sthana_bala(planet, p_lon, houses, jd, ayanamsa_system,
            sidereal_longitudes=sidereal_longitudes, saptavargaja_profile=active.saptavargaja_profile)
        d_bala  = dig_bala(planet, p_lon, houses, jd, ayanamsa_system)
        k_bala = kala_bala(planet, p_lon, sun_sid, jd, tithi_number,
            is_day, vara_lord, planet_speeds, hora_lord=hora_lord,
            ayanamsa_system=ayanamsa_system, context=context)
        c_bala = dict(context.chesta_values)[planet]
        n_bala  = NAISARGIKA_BALA[planet]
        dr_bala = drig_bala(planet, sidereal_longitudes)
        _raw[planet] = (s_bala, d_bala, k_bala, c_bala, n_bala, dr_bala)

    resolution = _resolve_wars(_raw, sidereal_longitudes)
    _adj_c = dict(resolution.raw_chesta)
    changes = dict(resolution.adjustments)
    _adj_k = {p: replace(_raw[p][2], yuddha=changes[p],
                        total=_raw[p][2].total + changes[p]) for p in _SEVEN_PLANETS}

    # --- Second pass: assemble result vessels ---
    result: dict[str, PlanetShadbala] = {}
    for planet in _SEVEN_PLANETS:
        s_bala, d_bala, _, _, n_bala, dr_bala = _raw[planet]
        k_bala = _adj_k[planet]
        c_bala = _adj_c[planet]
        total_sha = (
            s_bala.total + d_bala + k_bala.total + c_bala + n_bala + dr_bala
        )
        total_rup = total_sha / 60.0
        req_rup   = REQUIRED_RUPAS[planet]

        result[planet] = PlanetShadbala(
            planet=planet,
            sthana_bala=s_bala,
            dig_bala=d_bala,
            kala_bala=k_bala,
            chesta_bala=c_bala,
            naisargika_bala=n_bala,
            drig_bala=dr_bala,
            total_shashtiamsas=total_sha,
            total_rupas=total_rup,
            required_rupas=req_rup,
            is_sufficient=(total_rup >= req_rup),
        )

    output = ShadbalaResult(
        jd=jd,
        ayanamsa_system=ayanamsa_system,
        planets=result,
        war_resolution=resolution,
        context=context,
        saptavargaja_profile=active.saptavargaja_profile,
        saptavargaja_evidence=tuple((p, saptavargaja_breakdown(p, sidereal_longitudes[p],
            sidereal_longitudes, active.saptavargaja_profile)) for p in _SEVEN_PLANETS),
    )
    try:
        validate_shadbala_output(output)
    except ValueError as exc:
        raise RuntimeError('internally inconsistent Shadbala result') from exc
    return output


# ---------------------------------------------------------------------------
# P4 -- ShadbalaPolicy
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ShadbalaPolicy:
    """
    P4 policy vessel for Shadbala computation.

    Attributes
    ----------
    ayanamsa_system : str
        Ayanamsa system for sidereal conversion.  Must be non-empty.
        Default 'Lahiri'.
    """

    ayanamsa_system: str = 'Lahiri'

    saptavargaja_profile: str = 'raman_1996'

    def __post_init__(self) -> None:
        if self.saptavargaja_profile not in ('raman_1996', 'bphs_santhanam_27'):
            raise ValueError('unsupported Saptavargaja profile')
        if not self.ayanamsa_system:
            raise ValueError(
                "ShadbalaPolicy.ayanamsa_system must be non-empty"
            )


# ---------------------------------------------------------------------------
# P7 -- ShadbalaConditionProfile (local condition for one planet)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ShadbalaConditionProfile:
    """
    P7 local condition profile for a single planet's Shadbala state.

    Attributes
    ----------
    planet : str
        Planet name.
    tier : str
        ShadbalaTier constant: SUFFICIENT or INSUFFICIENT.
    total_rupas : float
        Grand total in Rupas.
    required_rupas : float
        Parashara minimum threshold in Rupas.
    strength_ratio : float
        total_rupas / required_rupas.  >= 1.0 is sufficient.
    is_sufficient : bool
        True when total_rupas >= required_rupas.
    """

    planet: str
    tier: str
    total_rupas: float
    required_rupas: float
    strength_ratio: float
    is_sufficient: bool


def shadbala_condition_profile(
    planet_result: PlanetShadbala,
) -> ShadbalaConditionProfile:
    """
    Build a P7 ShadbalaConditionProfile from a PlanetShadbala result.

    Parameters
    ----------
    planet_result : PlanetShadbala
        The full Shadbala result for one planet.

    Returns
    -------
    ShadbalaConditionProfile
    """
    tier = (
        ShadbalaTier.SUFFICIENT
        if planet_result.is_sufficient
        else ShadbalaTier.INSUFFICIENT
    )
    return ShadbalaConditionProfile(
        planet=planet_result.planet,
        tier=tier,
        total_rupas=planet_result.total_rupas,
        required_rupas=planet_result.required_rupas,
        strength_ratio=planet_result.strength_ratio,
        is_sufficient=planet_result.is_sufficient,
    )


# ---------------------------------------------------------------------------
# P8 -- ShadbalaChartProfile (aggregate across all planets)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ShadbalaChartProfile:
    """
    P8 aggregate Shadbala profile for a full chart.

    Attributes
    ----------
    sufficient_count : int
        Number of planets with tier SUFFICIENT.
    insufficient_count : int
        Number of planets with tier INSUFFICIENT.
    strongest_planet : str
        Planet with the highest strength_ratio.
    weakest_planet : str
        Planet with the lowest strength_ratio.
    planet_tiers : dict[str, str]
        Mapping of planet name -> ShadbalaTier constant.
    strength_ratios : dict[str, float]
        Mapping of planet name -> strength_ratio.
    ayanamsa_system : str
        Ayanamsa system from the ShadbalaResult.
    """

    sufficient_count: int
    insufficient_count: int
    strongest_planet: str
    weakest_planet: str
    planet_tiers: dict[str, str]
    strength_ratios: dict[str, float]
    ayanamsa_system: str


def shadbala_chart_profile(result: ShadbalaResult) -> ShadbalaChartProfile:
    """
    Build a P8 ShadbalaChartProfile from a ShadbalaResult.

    Parameters
    ----------
    result : ShadbalaResult
        The full chart Shadbala result.

    Returns
    -------
    ShadbalaChartProfile

    Raises
    ------
    ValueError
        If result.planets is empty.
    """
    if not result.planets:
        raise ValueError("shadbala_chart_profile: result.planets must not be empty")

    profiles = {p: shadbala_condition_profile(r) for p, r in result.planets.items()}

    sufficient_count   = sum(1 for pr in profiles.values() if pr.tier == ShadbalaTier.SUFFICIENT)
    insufficient_count = sum(1 for pr in profiles.values() if pr.tier == ShadbalaTier.INSUFFICIENT)

    ratios = {p: pr.strength_ratio for p, pr in profiles.items()}
    strongest = max(ratios, key=ratios.__getitem__)
    weakest   = min(ratios, key=ratios.__getitem__)

    return ShadbalaChartProfile(
        sufficient_count=sufficient_count,
        insufficient_count=insufficient_count,
        strongest_planet=strongest,
        weakest_planet=weakest,
        planet_tiers={p: pr.tier for p, pr in profiles.items()},
        strength_ratios=ratios,
        ayanamsa_system=result.ayanamsa_system,
    )


# ---------------------------------------------------------------------------
# P10 -- validate_shadbala_output
# ---------------------------------------------------------------------------

def validate_shadbala_output(result: ShadbalaResult) -> None:
    """
    P10 validator for a ShadbalaResult.

    Checks planet completeness, is_sufficient consistency, and
    total_shashtiamsas / total_rupas relationship.

    Parameters
    ----------
    result : ShadbalaResult
        The Shadbala result to validate.

    Raises
    ------
    ValueError
        On any inconsistency.
    """
    if not isinstance(result, ShadbalaResult):
        raise ValueError('canonical ShadbalaResult required')
    if isinstance(result.jd, bool) or not math.isfinite(result.jd) or not result.ayanamsa_system:
        raise ValueError('Shadbala epoch and ayanamsa must be valid')
    if set(result.planets) != set(_SEVEN_PLANETS):
        raise ValueError('Shadbala must contain exactly seven classical planets')
    def equal(a,b,label):
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in (a,b)) or abs(a-b) > 1e-6:
            raise ValueError(f'Shadbala {label} is inconsistent')
    for planet, ps in result.planets.items():
        if not isinstance(ps, PlanetShadbala) or planet != ps.planet:
            raise ValueError('Shadbala key does not match planet')
        sb, kb = ps.sthana_bala, ps.kala_bala
        if not isinstance(sb,SthanaBala) or not isinstance(kb,KalaBala):
            raise ValueError('Shadbala components must use canonical vessels')
        if kb.yuddha != 0 and result.war_resolution is None:
            raise ValueError('nonzero Yuddha requires its canonical ledger')
        svals = (sb.uchcha,sb.saptavargaja,sb.ojayugma,sb.kendradi,sb.drekkana)
        kvals = (kb.nathonnatha,kb.paksha,kb.tribhaga,kb.abda_masa_vara_hora,kb.ayana,kb.yuddha)
        positive = svals + kvals[:4] + (ps.dig_bala,ps.chesta_bala,ps.naisargika_bala)
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v < 0 for v in positive):
            raise ValueError('Shadbala component must be finite and nonnegative')
        if kb.ayana < 0 and result.context is None:
            raise ValueError('signed Ayana requires its declination context')
        for v in kvals[4:] + (ps.drig_bala,):
            equal(v,v,'signed component')
        equal(ps.naisargika_bala, NAISARGIKA_BALA[planet], 'Naisargika')
        equal(sb.total, sum(svals), 'subcomponent total')
        equal(kb.total, sum(kvals), 'subcomponent total')
        equal(ps.total_shashtiamsas, sb.total+ps.dig_bala+kb.total+ps.chesta_bala+ps.naisargika_bala+ps.drig_bala, 'total')
        equal(ps.total_rupas, ps.total_shashtiamsas/60, 'total_rupas')
        equal(ps.required_rupas, REQUIRED_RUPAS[planet], 'required_rupas')
        if type(ps.is_sufficient) is not bool or ps.is_sufficient != (ps.total_rupas >= ps.required_rupas):
            raise ValueError('Shadbala is_sufficient inconsistent with rupas threshold')
    if result.context is None and (result.saptavargaja_profile is not None or result.saptavargaja_evidence):
        raise ValueError('source-profile evidence requires its context')
    if result.context is not None:
        if result.war_resolution is None:
            raise ValueError('source-context result requires its canonical war ledger')
        if not isinstance(result.context, ShadbalaContext):
            raise ValueError('canonical Shadbala context required')
        result.context.__post_init__()
        result.context.require_complete()
        if result.jd != result.context.jd or result.ayanamsa_system != result.context.ayanamsa_system:
            raise ValueError('Shadbala context frame/epoch mismatch')
        positions = dict(result.context.sidereal_longitudes)
        if len(result.saptavargaja_evidence) != 7 or {p for p,_ in result.saptavargaja_evidence} != set(_SEVEN_PLANETS):
            raise ValueError('Saptavargaja evidence must cover seven planets')
        for p, ps in result.planets.items():
            sb = ps.sthana_bala
            for name, value in zip(('uchcha', 'ojayugma', 'drekkana'),
                                   positional_components(p, positions[p])):
                equal(getattr(sb, name), value, 'context positional '+name)
            if (not 0 <= sb.uchcha <= 60 or sb.ojayugma not in (0., 15., 30.)
                    or sb.drekkana not in (0., 15.) or sb.kendradi not in (15., 30., 60.)
                    or not 0 <= ps.dig_bala <= 60):
                raise ValueError('Shadbala positional awards outside admitted ranges')
            equal(ps.drig_bala, drig_bala(p, positions), 'context Drig')
            expected_kala = kala_components(p, result.context)
            actual_kala = ps.kala_bala
            for name,value in zip(('nathonnatha','paksha','tribhaga','abda_masa_vara_hora','ayana'), expected_kala):
                equal(getattr(actual_kala,name),value,'context Kala '+name)
            equal(ps.chesta_bala,dict(result.context.chesta_values)[p],'context Chesta')
        for p,entries in result.saptavargaja_evidence:
            if any(not isinstance(e,SaptavargajaEntry) or type(e.division) is not int
                   or type(e.sign_index) is not int or isinstance(e.shashtiamsas,bool) for e in entries):
                raise ValueError('Saptavargaja evidence requires canonical typed entries')
            expected = saptavargaja_breakdown(p, positions[p], positions, result.saptavargaja_profile)
            if entries != expected:
                raise ValueError('Saptavargaja evidence disagrees with context/profile')
            equal(sum(e.shashtiamsas for e in entries), result.planets[p].sthana_bala.saptavargaja, 'Saptavargaja total')
    ledger = result.war_resolution
    if ledger is not None:
        if (not isinstance(ledger, WarResolution) or result.context is None
                or ledger.policy != 'moira_simultaneous_raman_raw_pairs_v1'
                or ledger.source != 'Raman1996:76-77:printed60-61'):
            raise ValueError('war resolution requires canonical policy and context')
        raw = {p: (ps.sthana_bala, ps.dig_bala,
            replace(ps.kala_bala,yuddha=0.,total=ps.kala_bala.total-ps.kala_bala.yuddha),
            ps.chesta_bala, ps.naisargika_bala, ps.drig_bala) for p,ps in result.planets.items()}
        expected = _resolve_wars(raw, dict(result.context.sidereal_longitudes))
        if len(ledger.pairs) != len(expected.pairs):
            raise ValueError('war detection receipt mismatch')
        for a,b in zip(ledger.pairs,expected.pairs):
            if not isinstance(a,GrahaYuddha) or type(a.tied) is not bool or isinstance(a.separation_deg,bool):
                raise ValueError('canonical typed war pair required')
            if (a.victor,a.loser,a.separation_deg,a.tied,a.rule,a.chesta_transferred) != (b.victor,b.loser,b.separation_deg,b.tied,b.rule,None):
                raise ValueError('war pair identity mismatch')
            if a.adjustment_shashtiamsas is None:
                raise ValueError('missing actual war amount')
            equal(a.adjustment_shashtiamsas,b.adjustment_shashtiamsas,'war adjustment')
        for name in ('raw_aggregates','raw_totals','raw_chesta','credits','debits','adjustments'):
            actual, reference = getattr(ledger,name), getattr(expected,name)
            if tuple(p for p,_ in actual) != tuple(p for p,_ in reference):
                raise ValueError('war ledger planet coverage mismatch')
            for (p,a),(_,b) in zip(actual,reference):
                equal(a,b,name)
        for p,amount in ledger.adjustments:
            equal(amount, result.planets[p].kala_bala.yuddha, 'applied war adjustment')
        equal(math.fsum(v for _,v in ledger.adjustments),0.,'war conservation')


# ---------------------------------------------------------------------------
# P5/P6 -- graha_yuddha_pairs (public war detection surface)
# ---------------------------------------------------------------------------

def graha_yuddha_pairs(
    sidereal_longitudes: dict[str, float],
    planet_latitudes: dict[str, float] | None = None,
    planet_speeds: dict[str, float] | None = None,
) -> tuple[GrahaYuddha, ...]:
    """
    Detect Graha Yuddha (planetary wars) from sidereal longitudes.

    Returns one :class:`GrahaYuddha` vessel per war pair detected.  A war
    occurs when two non-luminaries (Mars, Mercury, Jupiter, Venus, Saturn)
    are within 1° of sidereal longitude.

    Parameters
    ----------
    sidereal_longitudes : dict[str, float]
        Sidereal longitudes for any subset of the five war-eligible planets.
    planet_latitudes, planet_speeds : dict or None
        Compatibility inputs; unused by the selected Raman detection rule.
        Actual amounts require raw strength components and are populated
        only by the canonical full-result WarResolution.

    Returns
    -------
    tuple[GrahaYuddha, ...]
        One record per war pair.  Empty when no wars are detected.
    """
    return _detect_wars(sidereal_longitudes, planet_latitudes, planet_speeds)


# ---------------------------------------------------------------------------
# P9 -- ShadbalaNetworkProfile (strength-network intelligence)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ShadbalaNetworkProfile:
    """
    P9 strength-network profile across all seven classical planets.

    Captures the strength ranking of all planets, the dominant and recessive
    planets, and any active Graha Yuddha war pairs supplied by the caller.

    Attributes
    ----------
    ayanamsa_system : str
        Ayanamsa system from the source ShadbalaResult.
    strength_ranking : tuple[str, ...]
        Planet names ordered strongest to weakest by total Rupas.
    dominant_planet : str
        Planet with the highest total Rupas.
    recessive_planet : str
        Planet with the lowest total Rupas.
    active_wars : tuple[GrahaYuddha, ...]
        Active Graha Yuddha pairs supplied by the caller via
        ``graha_yuddha_pairs()``.  Empty if no war information is provided.
    war_victors : frozenset[str]
        Names of planets that won a war.  Empty if no wars are present.
    war_losers : frozenset[str]
        Names of planets that lost a war.  Empty if no wars are present.
    """

    ayanamsa_system:  str
    strength_ranking: tuple[str, ...]
    dominant_planet:  str
    recessive_planet: str
    active_wars:      tuple[GrahaYuddha, ...]
    war_victors:      frozenset[str]
    war_losers:       frozenset[str]


def shadbala_network_profile(
    result: ShadbalaResult,
    wars: tuple[GrahaYuddha, ...] = (),
) -> ShadbalaNetworkProfile:
    """
    Build a P9 ShadbalaNetworkProfile from a ShadbalaResult.

    Parameters
    ----------
    result : ShadbalaResult
        Full chart Shadbala result from ``shadbala()``.
    wars : tuple[GrahaYuddha, ...], optional
        Active war records from ``graha_yuddha_pairs()``.  Defaults to
        empty (no war information supplied).

    Returns
    -------
    ShadbalaNetworkProfile

    Raises
    ------
    ValueError
        If ``result.planets`` is empty.
    """
    if not result.planets:
        raise ValueError(
            "shadbala_network_profile: result.planets must not be empty"
        )
    if result.war_resolution is not None:
        wars = result.war_resolution.pairs
    ranked = sorted(
        result.planets.values(),
        key=lambda ps: ps.total_rupas,
        reverse=True,
    )
    ranking = tuple(ps.planet for ps in ranked)
    return ShadbalaNetworkProfile(
        ayanamsa_system=result.ayanamsa_system,
        strength_ranking=ranking,
        dominant_planet=ranking[0],
        recessive_planet=ranking[-1],
        active_wars=wars,
        war_victors=frozenset(w.victor for w in wars),
        war_losers=frozenset(w.loser for w in wars),
    )
