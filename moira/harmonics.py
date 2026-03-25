"""
Harmonic Engine — moira/harmonics.py

Archetype: Engine
Purpose: Computes harmonic chart positions by multiplying natal ecliptic
         longitudes by a harmonic number and reducing modulo 360°, with
         a preset catalogue of astrologically named harmonics, dynamic
         age-harmonic timing, conjunction detection, pattern scoring,
         series sweeps, natal aspect identification, composite resonance
         analysis, and full vibrational fingerprinting.

Boundary declaration:
    Owns: the harmonic formula (lon × H mod 360°), the HARMONIC_PRESETS
          catalogue, age harmonic derivation, inter-harmonic conjunction
          detection, Cochrane-style pattern scoring, harmonic series
          sweeps, natal aspect decoding, composite/synastry harmonic
          comparison, and vibrational fingerprint synthesis.
    Delegates: sign derivation to moira.constants.sign_of.

Import-time side effects: None

External dependency assumptions:
    - moira.constants.sign_of(longitude) returns (sign_name, symbol, degree).

Public surface / exports:
    # Result types
    HarmonicPosition      — one body's harmonic chart position
    HarmonicConjunction   — two bodies conjunct on a harmonic chart
    HarmonicPatternScore  — pattern density score for a single harmonic
    HarmonicSweepEntry    — one harmonic's score in a series sweep
    HarmonicAspect        — natal pair decoded as an Hth-harmonic conjunction
    VibrationFingerprint  — full vibrational profile across H1..Hmax

    # Service class
    HarmonicsService      — OOP facade over all harmonic computations

    # Constants
    HARMONIC_PRESETS      — dict of harmonic number → (name, description)

    # Core computation
    calculate_harmonic()     — project all bodies onto harmonic H
    age_harmonic()           — derive H from person's age at a given date

    # Analysis
    harmonic_conjunctions()  — bodies conjunct on harmonic chart
    harmonic_pattern_score() — Cochrane-style pattern density for one H
    harmonic_sweep()         — sweep H1..Hmax, rank by pattern score
    harmonic_aspects()       — decode natal aspects as harmonic conjunctions
    composite_harmonic()     — cross-chart harmonic conjunctions (synastry)
    vibrational_fingerprint() — synthesised vibrational profile
"""

from dataclasses import dataclass, field

from .constants import sign_of

__all__ = [
    # Result types
    "HarmonicPosition",
    "HarmonicConjunction",
    "HarmonicPatternScore",
    "HarmonicSweepEntry",
    "HarmonicAspect",
    "VibrationFingerprint",
    # Service class
    "HarmonicsService",
    # Constants
    "HARMONIC_PRESETS",
    # Core computation
    "calculate_harmonic",
    "age_harmonic",
    # Analysis
    "harmonic_conjunctions",
    "harmonic_pattern_score",
    "harmonic_sweep",
    "harmonic_aspects",
    "composite_harmonic",
    "vibrational_fingerprint",
]

# ---------------------------------------------------------------------------
# Internal constants
# ---------------------------------------------------------------------------

_TROPICAL_YEAR: float = 365.24219  # mean tropical year in days (IAU)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _circ_dist_360(a: float, b: float) -> float:
    """Unsigned circular distance between two longitudes on a 360° circle."""
    d = abs(a - b) % 360.0
    return d if d <= 180.0 else 360.0 - d


def _circ_mean_360(a: float, b: float) -> float:
    """Circular midpoint of two longitudes, handling the 0°/360° wrap."""
    diff = b - a
    if diff > 180.0:
        diff -= 360.0
    elif diff < -180.0:
        diff += 360.0
    return (a + diff / 2.0) % 360.0


def _h_label(h: float) -> str:
    """Format a harmonic number compactly: integer-valued floats drop the decimal."""
    return f"H{int(h)}" if h == int(h) else f"H{h:.4f}"


# ---------------------------------------------------------------------------
# Preset harmonics with astrological meanings
# ---------------------------------------------------------------------------

HARMONIC_PRESETS: dict[int, tuple[str, str]] = {
    1:  ("Natal",        "Base chart — no transformation"),
    2:  ("Opposition",   "Polarity, opposition, awareness"),
    3:  ("Trine",        "Ease, flow, integration"),
    4:  ("Square",       "Tension, challenges, action"),
    5:  ("Quintile",     "Creativity, talent, gifts"),
    7:  ("Septile",      "Destiny, fate, karma"),
    8:  ("Octile",       "Stress, power, material"),
    9:  ("Novile",       "Spiritual gifts, gestation"),
    11: ("Undecile",     "Rhythm, pattern, timing"),
    12: ("Semi-sextile", "Integration, adjustment"),
}


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class HarmonicPosition:
    """
    RITE: The Resonant Echo — a planet's natal longitude transformed into
          the frequency of a chosen harmonic, revealing hidden patterns
          that are invisible on the natal wheel.

    THEOREM: Immutable record of a single body's harmonic chart position,
             storing the natal longitude, the harmonic number, the computed
             harmonic longitude, and the derived sign/degree fields.

    RITE OF PURPOSE:
        HarmonicPosition is the result vessel of HarmonicsService.  It
        pairs the natal longitude with its harmonic transformation so that
        callers can compare both values and read the sign position of the
        harmonic point without performing the multiplication themselves.

    LAW OF OPERATION:
        Responsibilities:
            - Store planet, natal_longitude, harmonic_longitude, and harmonic.
            - Derive sign, sign_symbol, and sign_degree via __post_init__.
            - Render a compact repr showing both natal and harmonic positions.
        Non-responsibilities:
            - Does not compute the harmonic; that is HarmonicsService's role.
            - Does not validate that harmonic >= 1.
        Structural invariants:
            - harmonic_longitude == (natal_longitude * harmonic) % 360.
            - sign, sign_symbol, sign_degree are consistent with
              harmonic_longitude.

    Canon: John Addey, Harmonics in Astrology (1976)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.harmonics.HarmonicPosition",
        "risk": "low",
        "api": {"frozen": ["planet", "natal_longitude", "harmonic_longitude", "harmonic"], "internal": ["sign", "sign_symbol", "sign_degree"]},
        "state": {"mutable": false, "owners": []},
        "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
        "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
        "failures": {"policy": "none"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    planet:              str
    natal_longitude:     float
    harmonic_longitude:  float
    harmonic:            float   # float to support age harmonics (non-integer H)
    sign:                str   = field(init=False)
    sign_symbol:         str   = field(init=False)
    sign_degree:         float = field(init=False)

    def __post_init__(self) -> None:
        self.sign, self.sign_symbol, self.sign_degree = sign_of(self.harmonic_longitude)

    def __repr__(self) -> str:
        hl = _h_label(self.harmonic)
        return (f"{hl} {self.planet:<10}: "
                f"natal={self.natal_longitude:>8.4f}  "
                f"{hl}={self.harmonic_longitude:>8.4f}  "
                f"{self.sign} {self.sign_degree:.2f}")


@dataclass(slots=True, frozen=True)
class HarmonicConjunction:
    """
    RITE: The Resonant Pair — two bodies vibrating at the same harmonic
          frequency, their echoes arriving at the same point on the wheel.

    THEOREM: Immutable record of two planets whose projected positions on
             a harmonic chart fall within the requested orb, capturing
             which harmonic joined them and how tightly.

    RITE OF PURPOSE:
        HarmonicConjunction is the primary analytical output of
        harmonic_conjunctions() and composite_harmonic().  It names the
        two bodies, the harmonic, the circular distance between their
        projected positions (orb), and the circular midpoint of their
        harmonic positions (longitude).  Without this vessel, callers
        would receive bare pairs of floats with no provenance.

    LAW OF OPERATION:
        Responsibilities:
            - Store planet_a, planet_b, harmonic, orb, longitude.
        Non-responsibilities:
            - Does not validate that planet_a != planet_b.
            - Does not compute any projection; that is the engine's role.
        Structural invariants:
            - orb >= 0.
            - longitude in [0, 360).

    Canon: David Hamblin, Harmonic Charts (1983);
           David Cochrane, The First 32 Harmonics (2002).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.harmonics.HarmonicConjunction",
        "risk": "low",
        "api": {"frozen": ["planet_a", "planet_b", "harmonic", "orb", "longitude"], "internal": []},
        "state": {"mutable": false, "owners": []},
        "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
        "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
        "failures": {"policy": "none"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    planet_a:  str
    planet_b:  str
    harmonic:  float
    orb:       float   # circular distance on 360° harmonic chart (degrees)
    longitude: float   # circular midpoint of the two harmonic positions


@dataclass(slots=True, frozen=True)
class HarmonicPatternScore:
    """
    RITE: The Resonance Census — a harmonic's power measured by the density
          of multi-planet conjunctions it produces in the chart.

    THEOREM: Aggregates all planetary conjunctions at harmonic H into
             connected clusters and scores the harmonic by the total
             number of conjunct pairs across all clusters: each cluster
             of n planets contributes n×(n−1)/2 to the score.

    RITE OF PURPOSE:
        HarmonicPatternScore quantifies how "strongly activated" a given
        harmonic is for a natal chart.  A chart with a tight 4-planet
        cluster at H5 scores 6 (C(4,2)=6), signalling a profound
        quintile/creative signature.  Without this scoring, harmonic
        analysis reduces to list-browsing with no quantitative ranking.

    LAW OF OPERATION:
        Responsibilities:
            - Store harmonic, all conjunctions, cluster sizes, and score.
        Non-responsibilities:
            - Does not interpret astrological meaning; that is the caller's role.
        Structural invariants:
            - score == sum(n*(n-1)//2 for n in cluster_sizes).
            - cluster_sizes is sorted descending.

    Canon: David Cochrane, The First 32 Harmonics (2002) — 4-planet
           cluster criterion; scoring formula adapted for continuous use.

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.harmonics.HarmonicPatternScore",
        "risk": "low",
        "api": {"frozen": ["harmonic", "conjunctions", "cluster_sizes", "score"], "internal": []},
        "state": {"mutable": false, "owners": []},
        "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
        "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
        "failures": {"policy": "none"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    harmonic:      int
    conjunctions:  tuple  # tuple[HarmonicConjunction, ...]
    cluster_sizes: tuple  # tuple[int, ...] sorted descending — one entry per cluster
    score:         float  # sum of n*(n-1)//2 per cluster


@dataclass(slots=True, frozen=True)
class HarmonicSweepEntry:
    """
    RITE: The Frequency Snapshot — a single harmonic's vital statistics
          within a series sweep, ready for ranking.

    THEOREM: Carries the harmonic number, its Cochrane pattern score,
             the total number of conjunctions, and the size of the
             largest cluster for one harmonic in a H1..Hmax sweep.

    RITE OF PURPOSE:
        HarmonicSweepEntry is the output element of harmonic_sweep().
        Ranking entries by score across H1..H32 identifies which
        frequencies the chart most strongly activates — the vibrational
        backbone of the nativity.  Without this vessel the sweep would
        return raw dicts with no type guarantees.

    LAW OF OPERATION:
        Responsibilities:
            - Store harmonic, score, n_conjunctions, largest_cluster.
        Non-responsibilities:
            - Does not store the full conjunction list; use
              harmonic_pattern_score() for that level of detail.
        Structural invariants:
            - score >= 0, n_conjunctions >= 0, largest_cluster >= 0.

    Canon: David Cochrane, The First 32 Harmonics (2002).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.harmonics.HarmonicSweepEntry",
        "risk": "low",
        "api": {"frozen": ["harmonic", "score", "n_conjunctions", "largest_cluster"], "internal": []},
        "state": {"mutable": false, "owners": []},
        "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
        "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
        "failures": {"policy": "none"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    harmonic:        int
    score:           float
    n_conjunctions:  int
    largest_cluster: int


@dataclass(slots=True, frozen=True)
class HarmonicAspect:
    """
    RITE: The Hidden Interval — a natal planetary separation decoded as
          a conjunction on the Hth harmonic chart, unmasking the harmonic
          family to which the aspect truly belongs.

    THEOREM: Records that the natal angular separation between planet_a
             and planet_b projects to a near-conjunction (within orb) on
             the Hth harmonic chart, identifying the harmonic number H
             that explains the aspect.

    RITE OF PURPOSE:
        HarmonicAspect implements John Addey's central thesis: every
        astrological aspect is a harmonic of the circle.  A 72° aspect
        (quintile) is an H5 conjunction; a 51.4° aspect is an H7
        (septile) conjunction.  harmonic_aspects() finds ALL such
        encodings for every pair in the chart, across H1..Hmax, making
        the full harmonic structure of a nativity visible at once.

    LAW OF OPERATION:
        Responsibilities:
            - Store planet_a, planet_b, harmonic, orb, separation.
        Non-responsibilities:
            - Does not assign aspect names; use HARMONIC_PRESETS for
              named harmonics.
        Structural invariants:
            - orb >= 0 and orb <= requested orb at call time.
            - separation is the shorter arc (0 ≤ separation ≤ 180).

    Canon: John Addey, Harmonics in Astrology (1976), Ch. 2.

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.harmonics.HarmonicAspect",
        "risk": "low",
        "api": {"frozen": ["planet_a", "planet_b", "harmonic", "orb", "separation"], "internal": []},
        "state": {"mutable": false, "owners": []},
        "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
        "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
        "failures": {"policy": "none"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    planet_a:   str
    planet_b:   str
    harmonic:   int
    orb:        float   # circular distance on harmonic chart (degrees)
    separation: float   # shorter natal arc between the two planets (degrees)


@dataclass(slots=True, frozen=True)
class VibrationFingerprint:
    """
    RITE: The Vibrational Signature — the complete harmonic character of
          a nativity, distilled from a full H1..Hmax sweep into a ranked
          frequency profile.

    THEOREM: Synthesises the output of harmonic_sweep() into a compact
             profile naming the dominant harmonics (those with score > 0,
             ranked by score), the peak harmonic, and the total activation
             energy across all frequencies tested.

    RITE OF PURPOSE:
        VibrationFingerprint is the top-level answer to "what is the
        vibrational character of this chart?"  It replaces the need to
        manually scan a sweep result, surfacing the dominant harmonics
        immediately and providing the full sweep for detailed inspection.
        A chart whose peak harmonic is H7 with a large gap to H5 has a
        very different vibrational signature than one where H3, H5, and
        H9 all score equally.

    LAW OF OPERATION:
        Responsibilities:
            - Store sweep (H1..Hmax entries, sorted by harmonic number),
              dominant (score > 0, sorted by score descending),
              total_score, peak_harmonic, peak_score.
        Non-responsibilities:
            - Does not interpret the meaning of harmonics; that is the
              caller's role using HARMONIC_PRESETS.
        Structural invariants:
            - sweep is sorted ascending by harmonic.
            - dominant contains only harmonics where score > 0.
            - peak_harmonic == dominant[0] if dominant else 0.
            - total_score == sum(e.score for e in sweep).

    Canon: David Cochrane, Vibrational Astrology: The Essentials (2020);
           David Hamblin, Harmonic Astrology in Practice (2019).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.harmonics.VibrationFingerprint",
        "risk": "low",
        "api": {"frozen": ["sweep", "dominant", "total_score", "peak_harmonic", "peak_score"], "internal": []},
        "state": {"mutable": false, "owners": []},
        "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
        "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
        "failures": {"policy": "none"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """
    sweep:         tuple  # tuple[HarmonicSweepEntry, ...] sorted by harmonic ASC
    dominant:      tuple  # tuple[int, ...] harmonics with score > 0, score-DESC
    total_score:   float
    peak_harmonic: int    # harmonic with highest score; 0 if none activated
    peak_score:    float


# ---------------------------------------------------------------------------
# Service class
# ---------------------------------------------------------------------------

class HarmonicsService:
    """
    RITE: The Frequency Tuner — the Engine that multiplies every natal
          longitude by the chosen harmonic number and returns the full
          transformed chart.

    THEOREM: Governs all harmonic chart computations: basic projection,
             age-harmonic timing, conjunction detection, pattern scoring,
             series sweeps, natal aspect identification, composite
             resonance, and vibrational fingerprinting.

    RITE OF PURPOSE:
        HarmonicsService is the OOP facade of the Harmonic Engine.
        It collects all harmonic operations under one class for callers
        who prefer object-oriented composition.  Module-level functions
        (calculate_harmonic, age_harmonic, etc.) delegate to this class.

    LAW OF OPERATION:
        Responsibilities:
            - Accept planet_longitudes dicts and harmonic parameters.
            - Delegate to the module-level implementation functions.
            - Provide get_preset_info() for harmonic name/description lookup.
        Non-responsibilities:
            - Does not perform any I/O or kernel access.

    Canon: John Addey, Harmonics in Astrology (1976);
           David Hamblin, Harmonic Charts (1983);
           David Cochrane, The First 32 Harmonics (2002).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.harmonics.HarmonicsService",
        "risk": "low",
        "api": {"frozen": ["calculate_harmonic", "get_preset_info", "age_harmonic", "harmonic_conjunctions", "harmonic_pattern_score", "harmonic_sweep", "harmonic_aspects", "composite_harmonic", "vibrational_fingerprint"], "internal": []},
        "state": {"mutable": false, "owners": []},
        "effects": {"signals_emitted": [], "io": [], "mutation": "none"},
        "concurrency": {"thread": "pure_computation", "cross_thread_calls": "safe_read_only"},
        "failures": {"policy": "raise"},
        "succession": {"stance": "terminal", "override_points": []},
        "agent": {"autofix": "allowed", "requires_human_for": ["api_change"]}
    }
    [/MACHINE_CONTRACT]
    """

    @staticmethod
    def calculate_harmonic(
        planet_longitudes: dict[str, float],
        harmonic: int,
    ) -> list[HarmonicPosition]:
        """
        Calculate harmonic positions for all bodies.

        Parameters
        ----------
        planet_longitudes : dict of body name → natal longitude (degrees)
        harmonic          : harmonic number (1 = natal, 4 = square harmonic, etc.)

        Returns
        -------
        List of HarmonicPosition sorted by harmonic longitude.
        """
        h = max(1.0, float(int(harmonic)))
        results = [
            HarmonicPosition(
                planet=name.strip().title(),
                natal_longitude=lon,
                harmonic_longitude=(lon * h) % 360.0,
                harmonic=h,
            )
            for name, lon in planet_longitudes.items()
        ]
        results.sort(key=lambda p: p.harmonic_longitude)
        return results

    @staticmethod
    def get_preset_info(harmonic: int) -> tuple[str, str]:
        """Return (name, description) for a harmonic number."""
        return HARMONIC_PRESETS.get(harmonic, (f"H{harmonic}", "Custom harmonic"))

    @staticmethod
    def age_harmonic(
        planet_longitudes: dict[str, float],
        jd_birth: float,
        jd_now: float,
    ) -> list[HarmonicPosition]:
        """Delegate to module-level age_harmonic()."""
        return age_harmonic(planet_longitudes, jd_birth, jd_now)

    @staticmethod
    def harmonic_conjunctions(
        planet_longitudes: dict[str, float],
        harmonic: int,
        orb: float = 1.0,
    ) -> list[HarmonicConjunction]:
        """Delegate to module-level harmonic_conjunctions()."""
        return harmonic_conjunctions(planet_longitudes, harmonic, orb)

    @staticmethod
    def harmonic_pattern_score(
        planet_longitudes: dict[str, float],
        harmonic: int,
        orb: float = 1.0,
    ) -> HarmonicPatternScore:
        """Delegate to module-level harmonic_pattern_score()."""
        return harmonic_pattern_score(planet_longitudes, harmonic, orb)

    @staticmethod
    def harmonic_sweep(
        planet_longitudes: dict[str, float],
        max_harmonic: int = 32,
        orb: float = 1.0,
    ) -> list[HarmonicSweepEntry]:
        """Delegate to module-level harmonic_sweep()."""
        return harmonic_sweep(planet_longitudes, max_harmonic, orb)

    @staticmethod
    def harmonic_aspects(
        planet_longitudes: dict[str, float],
        orb: float = 1.0,
        max_harmonic: int = 32,
    ) -> list[HarmonicAspect]:
        """Delegate to module-level harmonic_aspects()."""
        return harmonic_aspects(planet_longitudes, orb, max_harmonic)

    @staticmethod
    def composite_harmonic(
        lons_a: dict[str, float],
        lons_b: dict[str, float],
        harmonic: int,
        orb: float = 1.0,
        label_a: str = "A",
        label_b: str = "B",
    ) -> list[HarmonicConjunction]:
        """Delegate to module-level composite_harmonic()."""
        return composite_harmonic(lons_a, lons_b, harmonic, orb, label_a, label_b)

    @staticmethod
    def vibrational_fingerprint(
        planet_longitudes: dict[str, float],
        max_harmonic: int = 32,
        orb: float = 1.0,
    ) -> VibrationFingerprint:
        """Delegate to module-level vibrational_fingerprint()."""
        return vibrational_fingerprint(planet_longitudes, max_harmonic, orb)


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------

_service = HarmonicsService()


# ---------------------------------------------------------------------------
# Core computation
# ---------------------------------------------------------------------------

def calculate_harmonic(
    planet_longitudes: dict[str, float],
    harmonic: int,
) -> list[HarmonicPosition]:
    """
    Compute harmonic chart positions by projecting each natal longitude
    through the formula (lon × H) mod 360°.

    Parameters
    ----------
    planet_longitudes : dict of body name → longitude (degrees)
    harmonic          : harmonic number (integer >= 1)

    Returns
    -------
    List of HarmonicPosition sorted by harmonic longitude.
    """
    return _service.calculate_harmonic(planet_longitudes, harmonic)


def age_harmonic(
    planet_longitudes: dict[str, float],
    jd_birth: float,
    jd_now: float,
) -> list[HarmonicPosition]:
    """
    Compute an Age Harmonic chart using the person's exact decimal age as H.

    The harmonic number is derived from the elapsed time since birth:
        H = (jd_now − jd_birth) / _TROPICAL_YEAR

    This is one of the most powerful timing techniques in modern harmonic
    astrology (Brose / Addey): the chart responds to the precise vibrational
    frequency corresponding to the current age, pinpointing life events to
    within days.

    Parameters
    ----------
    planet_longitudes : dict of body name → natal longitude (degrees)
    jd_birth          : Julian Day of birth (UT)
    jd_now            : Julian Day of the target date (UT)

    Returns
    -------
    List of HarmonicPosition (harmonic field = decimal age) sorted by
    harmonic longitude.

    Raises
    ------
    ValueError
        If jd_now < jd_birth (negative age).
    """
    if jd_now < jd_birth:
        raise ValueError(
            f"jd_now ({jd_now:.4f}) precedes jd_birth ({jd_birth:.4f}) — "
            "age harmonic requires a non-negative age."
        )
    h = max(1e-6, (jd_now - jd_birth) / _TROPICAL_YEAR)
    results = [
        HarmonicPosition(
            planet=name.strip().title(),
            natal_longitude=lon,
            harmonic_longitude=(lon * h) % 360.0,
            harmonic=h,
        )
        for name, lon in planet_longitudes.items()
    ]
    results.sort(key=lambda p: p.harmonic_longitude)
    return results


# ---------------------------------------------------------------------------
# Analysis functions
# ---------------------------------------------------------------------------

def harmonic_conjunctions(
    planet_longitudes: dict[str, float],
    harmonic: int,
    orb: float = 1.0,
) -> list[HarmonicConjunction]:
    """
    Find all planet pairs that are conjunct on the Hth harmonic chart.

    After projecting every natal longitude to the harmonic chart via
    (lon × H) mod 360°, any two bodies whose projected positions fall
    within *orb* degrees of each other on that circle are in conjunction.
    These conjunctions are the primary analytical signal of harmonic
    astrology: a conjunction at H5 means the pair shares a quintile
    resonance; at H7, a septile resonance; and so on.

    Parameters
    ----------
    planet_longitudes : dict of body name → natal longitude (degrees)
    harmonic          : harmonic number (integer >= 1)
    orb               : maximum circular distance on the harmonic chart
                        to qualify as a conjunction (degrees, default 1.0)

    Returns
    -------
    List of HarmonicConjunction sorted by orb (tightest first).
    """
    h = max(1, int(harmonic))
    positions: dict[str, float] = {
        name.strip().title(): (lon * h) % 360.0
        for name, lon in planet_longitudes.items()
    }
    names = list(positions.keys())
    result: list[HarmonicConjunction] = []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            ha, hb = positions[a], positions[b]
            d = _circ_dist_360(ha, hb)
            if d <= orb:
                result.append(HarmonicConjunction(
                    planet_a=a,
                    planet_b=b,
                    harmonic=float(h),
                    orb=d,
                    longitude=_circ_mean_360(ha, hb),
                ))
    result.sort(key=lambda c: c.orb)
    return result


def harmonic_pattern_score(
    planet_longitudes: dict[str, float],
    harmonic: int,
    orb: float = 1.0,
) -> HarmonicPatternScore:
    """
    Score the pattern density of a single harmonic for the given chart.

    Builds all planetary conjunctions at harmonic H (via harmonic_conjunctions),
    groups them into connected clusters using Union-Find, and computes the
    Cochrane-style score: each cluster of n planets contributes n×(n−1)/2
    (the number of conjunct pairs within the cluster).

    A cluster of 2 = 1 point; a cluster of 3 = 3 points; a cluster of 4 = 6
    points.  High scores indicate a densely activated harmonic.

    Parameters
    ----------
    planet_longitudes : dict of body name → natal longitude (degrees)
    harmonic          : harmonic number (integer >= 1)
    orb               : conjunction orb on the harmonic chart (degrees)

    Returns
    -------
    HarmonicPatternScore with conjunctions, cluster_sizes, and score.
    """
    h = max(1, int(harmonic))
    conjs = harmonic_conjunctions(planet_longitudes, h, orb)

    if not conjs:
        return HarmonicPatternScore(
            harmonic=h,
            conjunctions=(),
            cluster_sizes=(),
            score=0.0,
        )

    # Union-Find over all planets that appear in at least one conjunction
    involved: list[str] = sorted({p for c in conjs for p in (c.planet_a, c.planet_b)})
    idx: dict[str, int] = {n: i for i, n in enumerate(involved)}
    parent = list(range(len(involved)))

    def _find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def _union(x: int, y: int) -> None:
        parent[_find(x)] = _find(y)

    for c in conjs:
        _union(idx[c.planet_a], idx[c.planet_b])

    # Count cluster sizes
    root_counts: dict[int, int] = {}
    for i in range(len(involved)):
        r = _find(i)
        root_counts[r] = root_counts.get(r, 0) + 1

    cluster_sizes = tuple(sorted(root_counts.values(), reverse=True))
    score = float(sum(n * (n - 1) // 2 for n in cluster_sizes))

    return HarmonicPatternScore(
        harmonic=h,
        conjunctions=tuple(conjs),
        cluster_sizes=cluster_sizes,
        score=score,
    )


def harmonic_sweep(
    planet_longitudes: dict[str, float],
    max_harmonic: int = 32,
    orb: float = 1.0,
) -> list[HarmonicSweepEntry]:
    """
    Sweep harmonics H1 through Hmax and rank each by its pattern score.

    For each harmonic H in [1, max_harmonic], calls harmonic_pattern_score()
    and records the score, conjunction count, and largest cluster size in a
    HarmonicSweepEntry.  The result is sorted by score descending (ties broken
    by harmonic number ascending) to surface the most activated frequencies
    first.

    This is the quantitative core of Cochrane's Vibrational Astrology: by
    sweeping H1–H32 and ranking by score, the dominant vibrational signature
    of the chart emerges.

    Parameters
    ----------
    planet_longitudes : dict of body name → natal longitude (degrees)
    max_harmonic      : highest harmonic to include in the sweep (default 32)
    orb               : conjunction orb on each harmonic chart (degrees)

    Returns
    -------
    List of HarmonicSweepEntry sorted by score descending, then harmonic ascending.
    """
    n = max(1, int(max_harmonic))
    entries: list[HarmonicSweepEntry] = []
    for h in range(1, n + 1):
        ps = harmonic_pattern_score(planet_longitudes, h, orb)
        entries.append(HarmonicSweepEntry(
            harmonic=h,
            score=ps.score,
            n_conjunctions=len(ps.conjunctions),
            largest_cluster=ps.cluster_sizes[0] if ps.cluster_sizes else 0,
        ))
    entries.sort(key=lambda e: (-e.score, e.harmonic))
    return entries


def harmonic_aspects(
    planet_longitudes: dict[str, float],
    orb: float = 1.0,
    max_harmonic: int = 32,
) -> list[HarmonicAspect]:
    """
    Decode every natal planet pair as a harmonic conjunction.

    For each pair of planets and each harmonic H in [1, max_harmonic],
    projects both natal longitudes to the Hth harmonic chart and checks
    whether they fall within *orb* degrees of each other.  If so, their
    natal separation is "explained" as an Hth-harmonic aspect (a multiple
    of 360°/H degrees).

    This implements John Addey's central thesis: every aspect is a harmonic
    of the circle.  A 72° natal separation appears as an H5 conjunction; a
    51.43° separation as an H7 conjunction.  The result makes the full
    harmonic vocabulary of a chart visible at once.

    Parameters
    ----------
    planet_longitudes : dict of body name → natal longitude (degrees)
    orb               : maximum circular distance on the harmonic chart
                        to qualify (degrees, default 1.0)
    max_harmonic      : highest harmonic to test (default 32)

    Returns
    -------
    List of HarmonicAspect sorted by (harmonic, orb) — i.e. lower harmonics
    first, then tightest orb within each harmonic.
    """
    names_lons: dict[str, float] = {
        n.strip().title(): lon for n, lon in planet_longitudes.items()
    }
    names = list(names_lons.keys())
    n = max(1, int(max_harmonic))
    result: list[HarmonicAspect] = []

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = names[i], names[j]
            lon_a, lon_b = names_lons[a], names_lons[b]
            sep = abs(lon_a - lon_b) % 360.0
            if sep > 180.0:
                sep = 360.0 - sep
            for h in range(1, n + 1):
                ha = (lon_a * h) % 360.0
                hb = (lon_b * h) % 360.0
                d = _circ_dist_360(ha, hb)
                if d <= orb:
                    result.append(HarmonicAspect(
                        planet_a=a,
                        planet_b=b,
                        harmonic=h,
                        orb=d,
                        separation=sep,
                    ))

    result.sort(key=lambda x: (x.harmonic, x.orb))
    return result


def composite_harmonic(
    lons_a: dict[str, float],
    lons_b: dict[str, float],
    harmonic: int,
    orb: float = 1.0,
    label_a: str = "A",
    label_b: str = "B",
) -> list[HarmonicConjunction]:
    """
    Find cross-chart harmonic conjunctions between two natal charts.

    Projects each chart independently onto the Hth harmonic wheel, then
    checks every planet from chart A against every planet from chart B for
    proximity within *orb* degrees.  A conjunction means the two people
    resonate at harmonic H through those two planetary principles.

    Planet names are prefixed with label_a / label_b (default "A:" / "B:")
    to prevent name collisions when both charts contain the same bodies.

    Parameters
    ----------
    lons_a     : dict of body name → natal longitude for person A (degrees)
    lons_b     : dict of body name → natal longitude for person B (degrees)
    harmonic   : harmonic number (integer >= 1)
    orb        : maximum circular distance to qualify (degrees, default 1.0)
    label_a    : prefix for chart A planet names (default "A")
    label_b    : prefix for chart B planet names (default "B")

    Returns
    -------
    List of HarmonicConjunction (cross-chart only) sorted by orb tightest first.
    """
    h = max(1, int(harmonic))
    ha: dict[str, float] = {
        f"{label_a}:{n.strip().title()}": (lon * h) % 360.0
        for n, lon in lons_a.items()
    }
    hb: dict[str, float] = {
        f"{label_b}:{n.strip().title()}": (lon * h) % 360.0
        for n, lon in lons_b.items()
    }
    result: list[HarmonicConjunction] = []
    for na, la in ha.items():
        for nb, lb in hb.items():
            d = _circ_dist_360(la, lb)
            if d <= orb:
                result.append(HarmonicConjunction(
                    planet_a=na,
                    planet_b=nb,
                    harmonic=float(h),
                    orb=d,
                    longitude=_circ_mean_360(la, lb),
                ))
    result.sort(key=lambda c: c.orb)
    return result


def vibrational_fingerprint(
    planet_longitudes: dict[str, float],
    max_harmonic: int = 32,
    orb: float = 1.0,
) -> VibrationFingerprint:
    """
    Synthesise the full vibrational character of a chart across H1..Hmax.

    Runs a complete harmonic_sweep(), identifies all activated harmonics
    (score > 0), and packages the result into a VibrationFingerprint that
    names the dominant frequencies, the peak harmonic, and the total
    activation energy of the chart.

    Parameters
    ----------
    planet_longitudes : dict of body name → natal longitude (degrees)
    max_harmonic      : highest harmonic to include (default 32)
    orb               : conjunction orb on each harmonic chart (degrees)

    Returns
    -------
    VibrationFingerprint with sweep (H-ascending), dominant (score-descending),
    total_score, peak_harmonic, and peak_score.
    """
    sweep_ranked = harmonic_sweep(planet_longitudes, max_harmonic=max_harmonic, orb=orb)

    # Store sweep sorted by harmonic number for stable indexing
    sweep_by_h = tuple(sorted(sweep_ranked, key=lambda e: e.harmonic))

    # Dominant = all harmonics with score > 0, already in score-descending order
    dominant = tuple(e.harmonic for e in sweep_ranked if e.score > 0.0)

    total = sum(e.score for e in sweep_ranked)
    peak = sweep_ranked[0] if sweep_ranked else None

    return VibrationFingerprint(
        sweep=sweep_by_h,
        dominant=dominant,
        total_score=total,
        peak_harmonic=peak.harmonic if (peak and peak.score > 0.0) else 0,
        peak_score=peak.score if peak else 0.0,
    )
