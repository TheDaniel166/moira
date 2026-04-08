"""
Moira — Shadbala Engine
========================

Archetype: Engine

Purpose
-------
Computes the six-fold planetary strength (Shadbala) for the seven classical
planets as defined by Parashara.  Shadbala is measured in Shashtiamsas
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

Required minimum Rupas (Parashara):
  Sun:6.5, Moon:6.0, Mars:5.0, Mercury:7.0, Jupiter:6.5, Venus:5.5, Saturn:5.0

Tradition and sources
---------------------
Parashara, "Brihat Parashara Hora Shastra" (BPHS), Shadbala Adhyaya.
B.V. Raman, "Graha and Bhava Balas" (1959) — the primary engineering
  reference; contains a fully worked example chart verifiable to 2 decimal
  places in Rupas.  All sub-component formulas and constants are cross-
  checked against this source.

Boundary declaration
--------------------
Owns: all six Shadbala sub-component computations, the ``SthanaBala``,
      ``KalaBala``, ``PlanetShadbala``, and ``ShadbalaResult`` vessels.
Delegates: Vedic dignity rank to ``moira.vedic_dignities``,
           varga sign indices to ``moira.varga``,
           panchanga elements (Vara, Paksha) to ``moira.panchanga``,
           sunrise/sunset to ``moira.rise_set``.

Import-time side effects: None

Implementation note — Kala Bala completeness
--------------------------------------------
Nathonnatha, Paksha, Tribhaga, and Ayana Bala are fully implemented.
Abda/Masa/Vara/Hora Bala are fully implemented per Raman Ch. 4.  Abda
(15 Sha) and Masa (30 Sha) are located by bisection on the Sun's actual
apparent sidereal longitude from the kernel (``moira.planets.planet_at``),
pinning the Sankranti JD to 1-second precision.  Vara (45 Sha) uses the
supplied ``vara_lord`` parameter.  Hora (60 Sha) is included when
``kala_bala()`` receives a non-None ``hora_lord`` argument; compute it via
``hora_lord_at(birth_jd, sunrise_jd)``.

Chesta Bala — Sun and Moon use the Raman Ch. 9 apogee-distance method:
arc(planet_lon, mandoccha) / 3 Sha (0 Sha at apogee, 60 Sha at perigee).
Sun's mandoccha is derived from Earth's osculating heliocentric perihelion
longitude (``moira.orbits.orbital_elements_at(Body.EARTH, ...)``).  Moon's
mandoccha from the geocentric state vector via kernel pairs (3, 301) and
(3, 399).  The five non-luminaries retain the speed-ratio approximation
(Raman Ch. 9 reserves the apogee-distance method for the luminaries only).

Yuddha Bala (planetary war) is fully implemented via ``_detect_wars()``.
The five non-luminaries are checked for conjunction within 1° of longitude.
Victor is the planet with greater geocentric latitude (Raman Ch. 9); greater
sidereal longitude is used as a fallback when ``planet_latitudes`` is not
supplied to ``shadbala()``.

Drig Bala uses sign-based Vedic aspect doctrine (not degree-based).

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
P3  -- Inspectability: PlanetShadbala.strength_ratio.
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

from __future__ import annotations

import math
from dataclasses import dataclass

__all__ = [
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
    "sthana_bala",
    "dig_bala",
    "kala_bala",
    "chesta_bala",
    "drig_bala",
    "shadbala",
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

    Two non-luminaries are at war when their sidereal longitudes are within
    1° of each other.  The victor is determined by greater geocentric latitude
    (Raman Ch. 9, “Graha and Bhava Balas”).  When latitude is unavailable,
    the planet with greater sidereal longitude is treated as victor.

    Attributes
    ----------
    victor : str
        Name of the victorious planet.
    loser : str
        Name of the defeated planet.
    separation_deg : float
        Angular separation in degrees at the moment of war (0 < value ≤ 1.0).
    """

    victor:         str
    loser:          str
    separation_deg: float

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
        if not (0.0 < self.separation_deg <= 1.0):
            raise ValueError(
                f"GrahaYuddha.separation_deg must be in (0, 1], "
                f"got {self.separation_deg}"
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
# Required minimum Rupas (Parashara)
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
# Source: Raman "Graha and Bhava Balas" Ch. 9; standard classical values.
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
# Saptavargaja Bala — dignity Shashtiamsa values
#
# Source: Raman "Graha and Bhava Balas" Ch. 6.
# ---------------------------------------------------------------------------

_SAPTAVARGAJA_SHA: dict[str, float] = {
    'exaltation':   20.0,
    'own_sign':     15.0,
    'adhi_mitra':   10.0,    # Great friend's sign
    'mitra':         7.5,    # Friend's sign
    'sama':          5.0,    # Neutral's sign
    'shatru':        2.5,    # Enemy's sign
    'adhi_shatru':   1.25,   # Great enemy's sign
    'debilitation':  0.0,
}

# Map VedicDignityRank values to Saptavargaja keys
_DIGNITY_TO_SAPTAVARGAJA: dict[str, str] = {
    'exaltation':   'exaltation',
    'mulatrikona':  'own_sign',      # Mulatrikona counts as own sign in Saptavargaja
    'own_sign':     'own_sign',
    'friend_sign':  'mitra',
    'neutral_sign': 'sama',
    'enemy_sign':   'shatru',
    'debilitation': 'debilitation',
}

# The 7 vargas used in Saptavargaja Bala: D1, D2, D3, D7, D9, D12, D30
_SAPTAVARGA_DIVISIONS: tuple[int, ...] = (1, 2, 3, 7, 9, 12, 30)

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
        if self.total_shashtiamsas < 0.0:
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

    def __post_init__(self) -> None:
        if not self.ayanamsa_system:
            raise ValueError(
                "ShadbalaResult.ayanamsa_system must be non-empty"
            )
        if not math.isfinite(self.jd):
            raise ValueError(
                f"ShadbalaResult.jd must be a finite number, got {self.jd}"
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


def _sun_mandoccha_lon(jd: float, ayanamsa_system: str) -> float:
    """
    Tropical longitude of the Sun's geocentric apogee (mandoccha) at ``jd``.

    The Sun's geocentric apogee lies 180° from Earth's heliocentric perihelion:

        mandoccha_trop = (Ω_Earth + ω_Earth + 180°) mod 360°

    Derived from DE441 osculating elements via ``moira.orbits``; tracks the
    true apsidal precession (~1.7°/century) rather than a static classical
    constant.

    Source: Raman, "Graha and Bhava Balas" (1959), Ch. 9.
    """
    from .orbits import orbital_elements_at
    from .spk_reader import get_reader
    from .constants import Body
    reader = get_reader()
    earth = orbital_elements_at(Body.EARTH, jd, reader)
    lon_peri = (earth.lon_ascending_node_deg + earth.arg_perihelion_deg) % 360.0
    return (lon_peri + 180.0) % 360.0


def _moon_mandoccha_lon(jd: float, ayanamsa_system: str) -> float:
    """
    Tropical longitude of the Moon's geocentric apogee (mandoccha) at ``jd``.

    Derived from the Moon's instantaneous geocentric osculating elements:

        mandoccha_trop = (Ω_Moon + ω_Moon) mod 360°

    Uses DE441 kernel pairs (3, 301) EMB → Moon and (3, 399) EMB → Earth to
    form the geocentric state vector, then applies the same
    ``_keplerian_from_state`` routine used by ``moira.orbits``.

    Source: Raman, "Graha and Bhava Balas" (1959), Ch. 9.
    """
    from .orbits import _keplerian_from_state, _rot_eq_to_ecl
    from .spk_reader import get_reader
    from .julian import ut_to_tt
    from .obliquity import true_obliquity as _true_obliquity
    _GM_EARTH_KM3_DAY2 = 3.986004418e5 * 86400.0 ** 2
    reader = get_reader()
    jd_tt = ut_to_tt(jd)
    moon_pos, moon_vel   = reader.position_and_velocity(3, 301, jd_tt)
    earth_pos, earth_vel = reader.position_and_velocity(3, 399, jd_tt)
    geo_pos = (
        moon_pos[0] - earth_pos[0],
        moon_pos[1] - earth_pos[1],
        moon_pos[2] - earth_pos[2],
    )
    geo_vel = (
        moon_vel[0] - earth_vel[0],
        moon_vel[1] - earth_vel[1],
        moon_vel[2] - earth_vel[2],
    )
    eps = math.radians(_true_obliquity(jd_tt))
    pos_ecl = _rot_eq_to_ecl(*geo_pos, eps)
    vel_ecl = _rot_eq_to_ecl(*geo_vel, eps)
    elems = _keplerian_from_state(pos_ecl, vel_ecl, _GM_EARTH_KM3_DAY2, 'Moon', jd)
    return (elems.lon_ascending_node_deg + elems.arg_perihelion_deg) % 360.0


def _detect_wars(
    sidereal_longitudes: dict[str, float],
    planet_latitudes: dict[str, float] | None,
) -> tuple['GrahaYuddha', ...]:
    """
    Detect Graha Yuddha (planetary wars) and return one GrahaYuddha per pair.

    Only the five non-luminaries (Mars, Mercury, Jupiter, Venus, Saturn)
    participate.  Two planets are at war when their sidereal longitudes are
    within 1° of each other.

    Victor determination (Raman Ch. 9):
        The planet with greater geocentric latitude wins.  When
        ``planet_latitudes`` is ``None``, the planet with greater sidereal
        longitude wins (fallback approximation).

    Returns
    -------
    tuple[GrahaYuddha, ...]
        One record per war pair.  Empty when no wars are detected.
    """
    wars: list[GrahaYuddha] = []
    candidates = sorted(p for p in _WAR_PLANETS if p in sidereal_longitudes)
    for i, p1 in enumerate(candidates):
        for p2 in candidates[i + 1:]:
            lon1 = sidereal_longitudes[p1] % 360.0
            lon2 = sidereal_longitudes[p2] % 360.0
            diff = abs(lon1 - lon2)
            if diff > 180.0:
                diff = 360.0 - diff
            if diff > 1.0:
                continue
            if planet_latitudes is not None:
                lat1 = planet_latitudes.get(p1, 0.0)
                lat2 = planet_latitudes.get(p2, 0.0)
                victor = p1 if lat1 >= lat2 else p2
            else:
                victor = p1 if lon1 >= lon2 else p2
            loser = p2 if victor == p1 else p1
            wars.append(GrahaYuddha(victor=victor, loser=loser, separation_deg=diff))
    return tuple(wars)


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
    function locates the crossing using a bisection search on the Sun's actual
    apparent sidereal longitude, not a mean-motion approximation.

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
    Search strategy mirrors the bisection used in ``moira.phenomena``
    for Moon-phase crossings.  Sidereal conversion: ``moira.sidereal``.
    """
    from .planets import planet_at
    from .sidereal import tropical_to_sidereal
    from .spk_reader import get_reader

    reader = get_reader()
    target = target_sidereal_lon % 360.0

    def _sun_sid(jd: float) -> float:
        sun = planet_at('Sun', jd, reader=reader)
        return tropical_to_sidereal(sun.longitude, jd, system=ayanamsa_system)

    # Forward residual: fraction of the Sun's circle traveled past the target.
    # Returns a value in [0, 360): approaches 360 just before the crossing,
    # then drops to near 0 just after.  The most recent Sankranti is found by
    # scanning backward in time and detecting the step where this value jumps
    # from ~0 (just after crossing) to ~360 (just before crossing).
    def _fwd(jd: float) -> float:
        return (_sun_sid(jd) - target) % 360.0

    # Coarse scan: step backward through the window in ~3-day increments.
    # The Sun travels ~1°/day so a 3-day step cannot skip an entire 360° cycle;
    # at most one Sankranti can exist in the relevant window.
    #
    # We scan forward in the window (i.e., from early → before_jd) to detect
    # where _fwd drops sharply (crosses zero from below 360 to near 0), which
    # marks the forward crossing of the target.
    scan_step = 3.0
    n_steps = int(window_days / scan_step) + 2
    jd_points = [before_jd - (n_steps - 1 - i) * scan_step for i in range(n_steps)]
    # Clip the leftmost point to the window start
    jd_points[0] = max(jd_points[0], before_jd - window_days)

    fwd_vals = [_fwd(jd_i) for jd_i in jd_points]

    sub_a = sub_b = None
    for i in range(len(fwd_vals) - 1):
        # Sign of forward crossing: fwd drops (prev >> 300, next << 60)
        if fwd_vals[i] > 300.0 and fwd_vals[i + 1] < 60.0:
            sub_a, sub_b = jd_points[i], jd_points[i + 1]
            break

    if sub_a is None:
        raise ValueError(
            f"No Sankranti at {target:.1f}° found in the {window_days:.0f}-day "
            f"window before JD {before_jd}."
        )

    # Bisect on the signed residual (well-behaved in the narrow sub-bracket).
    def _residual(jd: float) -> float:
        lon = _sun_sid(jd)
        return (lon - target + 180.0) % 360.0 - 180.0

    # 1-second tolerance in Julian days
    return _bisection_root(_residual, sub_a, sub_b, tol=1.1574e-5, max_iter=64)


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
    from .vedic_dignities import vedic_dignity, VedicDignityRank
    from .varga import (
        hora, chaturthamsha, saptamsa, navamsa,
        dwadashamsa, trimshamsa,
    )
    from .sidereal import tropical_to_sidereal

    lon = sidereal_lon % 360.0

    # --- (a) Uchcha Bala ---
    dig_result = vedic_dignity(planet, lon)
    uchcha_sha = dig_result.exaltation_score * 60.0

    # --- (b) Saptavargaja Bala ---
    # For each of 7 vargas, compute the planet's dignity in that varga sign.
    # D1: sidereal sign (already known)
    # D2–D30: use varga wrappers (accept sidereal longitude)
    varga_fns = {
        1:  lambda l: int(l % 360.0 // 30),   # D1 sign index directly
        2:  lambda l: hora(l).varga_number,    # will use sign_index below
        3:  lambda l: None,
        7:  lambda l: None,
        9:  lambda l: None,
        12: lambda l: None,
        30: lambda l: None,
    }
    # Use the actual varga wrappers to get sign indices
    from .varga import hora as _hora, saptamsa as _saptamsa, navamsa as _navamsa
    from .varga import dwadashamsa as _dwad, trimshamsa as _trim

    def _varga_sign(n: int, l: float) -> int:
        if n == 1:
            return int(l % 360.0 // 30)
        vp_map = {
            2:  _hora(l),
            7:  _saptamsa(l),
            9:  _navamsa(l),
            12: _dwad(l),
            30: _trim(l),
        }
        if n in vp_map:
            vp = vp_map[n]
            from .constants import SIGNS
            return SIGNS.index(vp.sign)
        # D3: Parashari drekkana formula
        sign_idx = int(l % 360.0 // 30)
        seg = int((l % 30.0) / 10.0)
        return (sign_idx + seg * 4) % 12

    saptavargaja_sha = 0.0
    for n in _SAPTAVARGA_DIVISIONS:
        v_sign = _varga_sign(n, lon)
        # Probe at 1° within the varga sign.  vedic_dignity() checks exaltation,
        # debilitation, and own-sign by sign index only (not by degree), so the
        # probe point is adequate for those ranks.  The mulatrikona check is
        # degree-sensitive: if the mulatrikona range does not include 1°, the
        # rank falls through to own_sign.  This is a known approximation for
        # Saptavargaja; degree-precise mulatrikona detection within each varga
        # would require computing the planet's exact longitude within the varga.
        v_dig = vedic_dignity(planet, v_sign * 30.0 + 1.0)
        rank_key = _DIGNITY_TO_SAPTAVARGAJA.get(v_dig.dignity_rank, 'sama')
        saptavargaja_sha += _SAPTAVARGAJA_SHA[rank_key]

    # --- (c) Ojayugmarasyamsa Bala ---
    # Odd-sign planets (Sun, Mars, Jupiter, Saturn): 15 Sha in odd D1 and D9 signs
    # Even-sign planets (Moon, Venus): 15 Sha in even D1 and D9 signs
    # Mercury: neutral — not listed; Raman gives Mercury in both
    d1_sign  = int(lon // 30)
    d9_sign  = _navamsa(lon)
    d9_idx   = int(lon // (30.0 / 9)) % 12  # Navamsa sign index (0 = Aries)
    odd_planets   = {'Sun', 'Mars', 'Jupiter', 'Saturn'}
    even_planets  = {'Moon', 'Venus'}
    ojayugma_sha  = 0.0
    if planet in odd_planets:
        if d1_sign % 2 == 0:    # 0-based: Aries=0 is 1st (odd)
            ojayugma_sha += 15.0
        if d9_idx % 2 == 0:
            ojayugma_sha += 15.0
    elif planet in even_planets:
        if d1_sign % 2 == 1:    # Taurus=1 is 2nd (even)
            ojayugma_sha += 15.0
        if d9_idx % 2 == 1:
            ojayugma_sha += 15.0
    else:
        # Mercury: 15 Sha in odd D1 and 15 Sha in even D1 (i.e. always 15 for D1)
        ojayugma_sha = 15.0

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

    # --- (e) Drekkana Bala ---
    decan_no = int((lon % 30.0) / 10.0) + 1   # 1, 2, or 3
    male_planets      = {'Sun', 'Mars', 'Jupiter'}
    hermaphrodite_pla = {'Mercury', 'Saturn'}
    female_planets    = {'Moon', 'Venus'}
    drekkana_sha = 0.0
    if planet in male_planets and decan_no == 1:
        drekkana_sha = 15.0
    elif planet in hermaphrodite_pla and decan_no == 2:
        drekkana_sha = 15.0
    elif planet in female_planets and decan_no == 3:
        drekkana_sha = 15.0

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
) -> KalaBala:
    """
    Compute Kala Bala (Temporal Strength) for one planet.

    Parameters
    ----------
    planet : str
    sidereal_lon : float
        Sidereal longitude of the planet.
    sun_sidereal_lon : float
        Sidereal longitude of the Sun (for Ayana Bala).
    jd : float
        Julian date (UT); used for Abda/Masa Sankranti bisection and as
        fallback for time-of-day fraction when ``local_day_frac`` is None.
    tithi_number : int
        Current Tithi (1–30) from Panchanga.
    is_day : bool
        ``True`` if birth is during daytime (between sunrise and sunset).
    vara_lord : str
        Planetary lord of the current Vedic weekday.
    planet_speeds : dict[str, float]
        Daily motion (°/day, signed) for each planet.  Negative = retrograde.
    hora_lord : str or None, optional
        Planetary lord of the birth hora.  When provided, contributes 60 Sha
        to the matching planet.  Compute via ``hora_lord_at(birth_jd,
        sunrise_jd)``; defaults to ``None`` (Hora Bala omitted).
    ayanamsa_system : str
        Ayanamsa system used for the Abda and Masa Sankranti bisections.
        Must match the system used for all other sidereal coordinates in
        the chart.  Defaults to ``'Lahiri'``.
    local_day_frac : float or None, optional
        Fractional position within the local solar day, in [0.0, 1.0).
        0.0 corresponds to local solar midnight; 0.5 to local solar noon.
        Used for Nathonnatha and Tribhaga Bala. When ``None`` (default),
        the fraction is approximated from ``jd % 1.0``, which is UTC-anchored
        and will be wrong for observers outside UTC.  Callers should pass
        ``(jd + observer_longitude_deg / 360.0) % 1.0`` for a mean solar
        approximation, or derive it from sunrise/sunset JDs for true solar time.

    Returns
    -------
    KalaBala
    """
    # --- (a) Nathonnatha Bala ---
    day_planets   = {'Sun', 'Jupiter', 'Venus'}
    night_planets = {'Moon', 'Mars', 'Saturn'}
    # Mercury is equally strong day and night
    # time_frac: fractional position in local solar day [0, 1).
    # JD epoch is noon UT, so jd % 1.0 == 0.0 at UT noon — not local noon
    # for non-UTC observers.  Callers should pass local_day_frac for accuracy.
    if local_day_frac is not None:
        time_frac = float(local_day_frac) % 1.0
    else:
        time_frac = (jd % 1.0)
    if planet == 'Mercury':
        nathonnatha = 60.0
    elif planet in day_planets:
        # Peaks at midday (time_frac ≈ 0.5 for mean solar noon)
        nathonnatha = abs(math.sin(math.pi * time_frac)) * 60.0 if is_day else 30.0
    else:
        # Night planets: peak at midnight
        nathonnatha = abs(math.sin(math.pi * time_frac)) * 60.0 if not is_day else 30.0

    # --- (b) Paksha Bala ---
    # Tithi 1–15 = Shukla (waxing); 16–30 = Krishna (waning)
    shukla = tithi_number if tithi_number <= 15 else 30 - tithi_number  # 0–15
    benefic_planets = {'Jupiter', 'Venus', 'Moon', 'Mercury'}
    if planet in benefic_planets:
        paksha = float(shukla) * 4.0   # 0–60 Sha
    else:
        paksha = float(15 - shukla) * 4.0

    # --- (c) Tribhaga Bala ---
    # Day: Jupiter (1st third), Sun (2nd third), Saturn (3rd third)
    # Night: Moon (1st third), Venus (2nd third), Mars (3rd third)
    # Mercury: always strong
    # Uses the same time_frac as Nathonnatha (see local_day_frac note above).
    tribhaga = 0.0
    if planet == 'Mercury':
        tribhaga = 60.0
    else:
        if is_day:
            third = int(time_frac * 3)   # 0, 1, or 2
            tribhaga_day_lords = ['Jupiter', 'Sun', 'Saturn']
            if third < len(tribhaga_day_lords) and planet == tribhaga_day_lords[third]:
                tribhaga = 60.0
        else:
            third = int(time_frac * 3)
            tribhaga_night_lords = ['Moon', 'Venus', 'Mars']
            if third < len(tribhaga_night_lords) and planet == tribhaga_night_lords[third]:
                tribhaga = 60.0

    # --- (d) Abda/Masa/Vara/Hora Bala ---
    # Per Raman "Graha and Bhava Balas" Ch. 4: Abda=15, Masa=30, Vara=45, Hora=60 Sha.
    #
    # Abda lord (year lord): weekday lord of the most recent Mesha Sankranti
    #   (Sun's sidereal longitude = 0°, i.e. entry into Aries).
    # Masa lord (month lord): weekday lord of the most recent Rashi Sankranti
    #   (Sun's sidereal longitude = floor(sun_sid/30)*30°).
    # Both are located by bisection on the Sun's actual apparent sidereal
    # longitude via moira.planets.planet_at + moira.sidereal.tropical_to_sidereal.
    # The Masa target is derived from the kernel-queried real Sun position at jd
    # (not from the passed sun_sidereal_lon) to keep Sankranti calculations
    # fully self-consistent with the bisection.
    # Source: BPHS Shadbala Adhyaya; Raman "Graha and Bhava Balas" Ch. 4.
    from .planets import planet_at as _planet_at
    from .sidereal import tropical_to_sidereal as _t2s
    from .spk_reader import get_reader as _get_reader
    _reader = _get_reader()
    _sun_real = _planet_at('Sun', jd, reader=_reader)
    _sun_sid_real = _t2s(_sun_real.longitude, jd, system=ayanamsa_system)
    _abda_target = 0.0
    _masa_target = float(int(_sun_sid_real // 30) * 30)
    abda_planet = _weekday_lord(_sankranti_jd(_abda_target, jd, ayanamsa_system, window_days=370.0))
    masa_planet = _weekday_lord(_sankranti_jd(_masa_target, jd, ayanamsa_system, window_days=32.0))
    amvh_sha    = 0.0
    if planet == abda_planet:
        amvh_sha += 15.0
    if planet == masa_planet:
        amvh_sha += 30.0
    if planet == vara_lord:
        amvh_sha += 45.0
    if hora_lord is not None and planet == hora_lord:
        amvh_sha += 60.0

    # --- (e) Ayana Bala ---
    # Sun's declination proxy: sin(dec) ≈ sin(obliquity) × sin(sun_lon)
    from .obliquity import true_obliquity as _true_obliquity_kala
    from .julian import ut_to_tt as _ut_to_tt_kala
    obliquity_rad = math.radians(_true_obliquity_kala(_ut_to_tt_kala(jd)))
    sun_lon_rad   = math.radians(sun_sidereal_lon % 360.0)
    sin_dec       = math.sin(obliquity_rad) * math.sin(sun_lon_rad)
    dec_deg       = math.degrees(math.asin(max(-1.0, min(1.0, sin_dec))))
    ayana_sha     = 24.0 * abs(sin_dec)   # 0–24 Sha (approximately)

    # Benefics gain in Uttara Ayana (Capricorn→Gemini, i.e. dec > 0 or sun_lon in [270,360)∪[0,90))
    # Raman simplifies: all planets get ayana_sha; sign depends on planet type vs ayana.
    # We use the absolute value per Raman's formula.

    # --- (f) Yuddha Bala ---
    # Set to 0 here; shadbala() rebuilds KalaBala for war participants after
    # a first-pass loop via _detect_wars().  Victor gets the loser's raw
    # Chesta Bala added to this field; loser's chesta_bala is set to 0.
    yuddha = 0.0

    total = nathonnatha + paksha + tribhaga + amvh_sha + ayana_sha + yuddha
    return KalaBala(
        nathonnatha=nathonnatha,
        paksha=paksha,
        tribhaga=tribhaga,
        abda_masa_vara_hora=amvh_sha,
        ayana=ayana_sha,
        yuddha=yuddha,
        total=total,
    )


def chesta_bala(
    planet: str,
    speed: float,
    planet_sidereal_lon: float | None = None,
    mandoccha_sidereal_lon: float | None = None,
) -> float:
    """
    Compute Chesta Bala (Motional Strength) for one planet.

    For the Sun and Moon, uses the Raman Ch. 9 apogee-distance method:
    ``arc(planet_lon, mandoccha_lon) / 3`` Sha.  The arc is in [0°, 180°],
    giving 0 Sha at apogee (slowest) and 60 Sha at perigee (fastest).
    Activate this path by supplying both ``planet_sidereal_lon`` and
    ``mandoccha_sidereal_lon``.  Pre-compute mandoccha via
    ``_sun_mandoccha_lon`` / ``_moon_mandoccha_lon`` and convert to sidereal
    with ``tropical_to_sidereal`` before passing here.

    For the five non-luminaries, uses a speed-ratio approach: strength is
    proportional to actual daily motion vs. the classical mean motion.
    Retrograde planets receive maximum Chesta Bala (60 Sha).

    Parameters
    ----------
    planet : str
    speed : float
        Actual daily motion in °/day.  Negative = retrograde.
        Used for the speed-ratio path (five non-luminaries) and as fallback
        when ``mandoccha_sidereal_lon`` is not provided.
    planet_sidereal_lon : float or None, optional
        Sidereal longitude of the planet.  Required for the
        apogee-distance path (Sun and Moon).
    mandoccha_sidereal_lon : float or None, optional
        Sidereal longitude of the planet's apogee (mandoccha).
        When provided together with ``planet_sidereal_lon``, activates
        the Raman Ch. 9 apogee-distance formula.

    Returns
    -------
    float
        Chesta Bala in Shashtiamsas, in [0.0, 60.0].

    Source
    ------
    Raman, "Graha and Bhava Balas" (1959), Ch. 9.
    """
    # Raman Ch. 9: apogee-distance method (Sun and Moon)
    if mandoccha_sidereal_lon is not None and planet_sidereal_lon is not None:
        dist = abs((planet_sidereal_lon - mandoccha_sidereal_lon + 180.0) % 360.0 - 180.0)
        return (180.0 - dist) / 3.0

    # Speed-ratio fallback (five non-luminaries)
    if speed < 0:
        return 60.0   # Retrograde = maximum Chesta Bala

    mean = MEAN_DAILY_MOTION.get(planet, 1.0)
    if mean <= 0:
        return 0.0

    ratio = abs(speed) / mean
    # Clamp to [0, 2] — beyond 2× mean speed still caps at 60 Sha
    ratio = min(ratio, 2.0)
    return ratio * 30.0   # 0 at standstill, 60 at 2× mean motion


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
        if asp_planet == planet:
            continue
        asp_sign = int(asp_lon % 360.0 // 30)
        # 1-based sign-distance from asp_planet to planet being assessed
        dist = (planet_sign - asp_sign) % 12 + 1   # 1–12

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
    planet_latitudes : dict[str, float] or None, optional
        Geocentric latitudes (degrees, signed) for the five non-luminaries.
        Used by ``_detect_wars()`` to identify Yuddha Bala victors: the
        planet with greater latitude (north wins) is the victor per Raman
        Ch. 9.  When ``None``, victors are determined by greater sidereal
        longitude (fallback approximation).

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
    if not (1 <= tithi_number <= 30):
        raise ValueError(f"tithi_number must be in [1, 30], got {tithi_number}")

    sun_sid = sidereal_longitudes.get('Sun', 0.0)

    # Raman Ch. 9: pre-compute sidereal mandoccha for the luminaries.
    from .sidereal import tropical_to_sidereal as _t2s
    _sun_mand_sid  = _t2s(_sun_mandoccha_lon(jd, ayanamsa_system),  jd, system=ayanamsa_system)
    _moon_mand_sid = _t2s(_moon_mandoccha_lon(jd, ayanamsa_system), jd, system=ayanamsa_system)

    # --- First pass: raw balas for all planets (yuddha = 0 initially) ---
    _raw: dict[str, tuple] = {}
    for planet in _SEVEN_PLANETS:
        p_lon   = sidereal_longitudes[planet]
        p_speed = planet_speeds[planet]

        s_bala  = sthana_bala(planet, p_lon, houses, jd, ayanamsa_system)
        d_bala  = dig_bala(planet, p_lon, houses, jd, ayanamsa_system)
        k_bala  = kala_bala(
            planet, p_lon, sun_sid, jd, tithi_number,
            is_day, vara_lord, planet_speeds,
            hora_lord=hora_lord,
            ayanamsa_system=ayanamsa_system,
        )
        _mand = (
            _sun_mand_sid  if planet == 'Sun'  else
            _moon_mand_sid if planet == 'Moon' else
            None
        )
        c_bala  = chesta_bala(
            planet, p_speed,
            planet_sidereal_lon=p_lon,
            mandoccha_sidereal_lon=_mand,
        )
        n_bala  = NAISARGIKA_BALA[planet]
        dr_bala = drig_bala(planet, sidereal_longitudes)
        _raw[planet] = (s_bala, d_bala, k_bala, c_bala, n_bala, dr_bala)

    # --- Yuddha Bala: detect wars and apply winner/loser adjustments ---
    # Source: Raman "Graha and Bhava Balas" (1959), Ch. 9.
    # Victor gains the loser's raw Chesta Bala in KalaBala.yuddha.
    # Loser's Chesta Bala is reduced to 0.
    _wars = _detect_wars(sidereal_longitudes, planet_latitudes)
    _adj_c: dict[str, float]    = {p: _raw[p][3] for p in _SEVEN_PLANETS}
    _adj_k: dict[str, KalaBala] = {p: _raw[p][2] for p in _SEVEN_PLANETS}
    for war in _wars:
        loser_c = _raw[war.loser][3]
        old_k   = _adj_k[war.victor]
        _adj_k[war.victor] = KalaBala(
            nathonnatha=old_k.nathonnatha,
            paksha=old_k.paksha,
            tribhaga=old_k.tribhaga,
            abda_masa_vara_hora=old_k.abda_masa_vara_hora,
            ayana=old_k.ayana,
            yuddha=loser_c,
            total=old_k.total + loser_c,
        )
        _adj_c[war.loser] = 0.0

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

    return ShadbalaResult(
        jd=jd,
        ayanamsa_system=ayanamsa_system,
        planets=result,
    )


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

    def __post_init__(self) -> None:
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
    if not result.ayanamsa_system:
        raise ValueError(
            "validate_shadbala_output: ayanamsa_system must be non-empty"
        )
    for planet, ps in result.planets.items():
        if planet != ps.planet:
            raise ValueError(
                f"validate_shadbala_output: key {planet!r} does not match "
                f"PlanetShadbala.planet {ps.planet!r}"
            )
        expected_rupas = ps.total_shashtiamsas / 60.0
        if abs(ps.total_rupas - expected_rupas) > 1e-6:
            raise ValueError(
                f"validate_shadbala_output: {planet} total_rupas "
                f"{ps.total_rupas} != total_shashtiamsas/60 "
                f"({expected_rupas:.6f})"
            )
        expected_sufficient = (ps.total_rupas >= ps.required_rupas)
        if ps.is_sufficient != expected_sufficient:
            raise ValueError(
                f"validate_shadbala_output: {planet} is_sufficient "
                f"{ps.is_sufficient} inconsistent with rupas "
                f"{ps.total_rupas} vs required {ps.required_rupas}"
            )


# ---------------------------------------------------------------------------
# P5/P6 -- graha_yuddha_pairs (public war detection surface)
# ---------------------------------------------------------------------------

def graha_yuddha_pairs(
    sidereal_longitudes: dict[str, float],
    planet_latitudes: dict[str, float] | None = None,
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
    planet_latitudes : dict[str, float] or None, optional
        Geocentric latitudes (signed degrees) for the same planets.  The
        planet with greater latitude (north wins) is the victor per Raman
        Ch. 9.  When ``None``, the planet with greater sidereal longitude
        is used as victor (fallback approximation).

    Returns
    -------
    tuple[GrahaYuddha, ...]
        One record per war pair.  Empty when no wars are detected.
    """
    return _detect_wars(sidereal_longitudes, planet_latitudes)


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
