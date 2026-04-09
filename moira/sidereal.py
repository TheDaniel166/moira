"""
Moira — Sidereal Engine
========================

Archetype: Engine

Purpose
-------
Governs ayanamsa computation for sidereal (Vedic) astrology, providing
tropical-to-sidereal and sidereal-to-tropical longitude conversion across
30 named ayanamsa systems, and nakshatra position computation for the
27 Vedic lunar mansions.

Boundary declaration
--------------------
Owns: ayanamsa system name constants, J2000 reference values, drift terms,
      star-anchored ayanamsa resolution, tropical/sidereal conversion,
      nakshatra span arithmetic, and the ``Ayanamsa`` and
      ``NakshatraPosition`` vessels.
Delegates: general precession to ``moira.precession``,
           nutation to ``moira.obliquity``,
           fixed star positions to ``moira.stars``,
           Julian century arithmetic to ``moira.julian``.

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required. No database access. Star-anchored ayanamsas
require the fixed star catalog (``moira/data/star_registry.csv``) to be accessible; falls
back to polynomial approximation if the catalog is absent.

Public surface
--------------
``Ayanamsa``               — Warden of ayanamsa system name constants.
``NakshatraPosition``      — vessel for a body's nakshatra position.
``ayanamsa``               — compute ayanamsa value for a JD and system.
``tropical_to_sidereal``   — convert tropical longitude to sidereal.
``sidereal_to_tropical``   — convert sidereal longitude to tropical.
``list_ayanamsa_systems``  — return all systems with their J2000 values.
``nakshatra_of``           — compute nakshatra position for a longitude.
``all_nakshatras_at``      — compute nakshatras for a full position dict.
"""

import math
from dataclasses import dataclass
from .constants import J2000, JULIAN_CENTURY
from .julian import centuries_from_j2000, ut_to_tt
from .precession import general_precession_in_longitude
from .obliquity import nutation

__all__ = [
    "Ayanamsa",
    "UserDefinedAyanamsa",
    "NakshatraPosition",
    "ayanamsa",
    "tropical_to_sidereal",
    "sidereal_to_tropical",
    "list_ayanamsa_systems",
    "nakshatra_of",
    "all_nakshatras_at",
]

# ---------------------------------------------------------------------------
# User-defined ayanamsa  (Phase 3 — Defer.Doctrine; ayanamsa expansion)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class UserDefinedAyanamsa:
    """
    A caller-supplied ayanamsa specified by its J2000.0 reference value.

    Replaces Swiss Ephemeris ``swe_set_sid_mode(SE_SIDM_USER, ...)`` global
    state mutation with a typed, immutable, first-class value.  Pass an
    instance anywhere a system-name string is accepted.

    Doctrine:
        The ayanamsa at any Julian Day is computed as::

            ayan(jd) = reference_value_j2000
                       + general_precession_in_longitude(jd)
                       + drift_per_century * T
                       [+ Δψ if mode='true']

        where ``T`` is centuries from J2000.0.  This is identical to the
        polynomial path used for all named systems; the only difference is
        that the reference value is caller-supplied rather than drawn from
        the built-in table.

    Acceptance criteria for future built-in ayanamsa additions
    (documented here as the doctrinal standard for all ``SIDM_*`` candidates):
        1. Must have a published, peer-reviewed epoch reference value.
        2. Must name the anchor star or epoch date explicitly.
        3. Must differ from all existing systems by > 1 arcminute at J2000.
        4. Must have a demonstrated user community (not hypothetical).
        5. Star-anchored systems additionally require a named star present
           in the Moira fixed-star catalog.
        Candidates not meeting all five criteria remain as
        ``UserDefinedAyanamsa`` use-cases, not new ``Ayanamsa.*`` constants.

    Args:
        reference_value_j2000: Ayanamsa value at J2000.0 (degrees).
        drift_per_century: Additional linear drift term in degrees per
            Julian century beyond the standard general precession.
            Defaults to 0.0 (pure precession-only tracking).

    Example::

        kp_ayanamsa = UserDefinedAyanamsa(reference_value_j2000=23.8576389)
        lon_sid = tropical_to_sidereal(mars.longitude, jd, system=kp_ayanamsa)
    """
    reference_value_j2000: float
    drift_per_century:     float = 0.0


# ---------------------------------------------------------------------------
# Ayanamsa system identifiers
# ---------------------------------------------------------------------------

class Ayanamsa:
    """
    RITE: The Warden of Zodiacs — the canonical namespace for ayanamsa systems.

    THEOREM: Provides string constants for all 34 supported ayanamsa system
    names and an ``ALL`` list for iteration.

    RITE OF PURPOSE:
        Serves the Sidereal Engine as the authoritative name registry for
        ayanamsa systems. Without this Warden, callers would use ad-hoc
        string literals that diverge across the codebase, breaking lookup
        against ``_AYANAMSA_AT_J2000`` and causing silent wrong-system errors.

    LAW OF OPERATION:
        Responsibilities:
            - Declare one class-level string constant per ayanamsa system.
            - Expose ``ALL`` as an ordered list of all 30 system name strings.
        Non-responsibilities:
            - Does not compute ayanamsa values.
            - Does not validate that a name is present in the reference table.
        Dependencies:
            - None. Pure namespace class with no runtime dependencies.
        Structural invariants:
            - ``ALL`` contains exactly 34 entries in canonical order.
        Succession stance: terminal — not designed for subclassing.

    Canon: Lahiri Commission (1955); Swiss Ephemeris documentation;
           Fagan & Bradley, "Primer of Sidereal Astrology" (1967).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.sidereal.Ayanamsa",
        "risk": "low",
        "api": {
            "public_methods": [],
            "public_attributes": ["LAHIRI", "FAGAN_BRADLEY", "KRISHNAMURTI", "ALL"]
        },
        "state": {
            "mutable": false,
            "fields": []
        },
        "effects": {
            "io": [],
            "signals_emitted": [],
            "db_writes": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": [],
            "policy": "no runtime failures — pure constants"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]
    """
    LAHIRI          = "Lahiri"           # Indian national standard
    FAGAN_BRADLEY   = "Fagan-Bradley"    # Western sidereal standard
    KRISHNAMURTI    = "Krishnamurti"     # KP system
    RAMAN           = "Raman"
    YUKTESHWAR      = "Yukteshwar"
    DJWHAL_KHUL     = "Djwhal Khul"      # Theosophical
    TRUE_CHITRAPAKSHA = "True Chitrapaksha"  # Chitra star-based
    DE_LUCE         = "De Luce"
    USHA_SHASHI     = "Usha-Shashi"
    SASSANIAN       = "Sassanian"
    BHASIN          = "Bhasin"
    KUGLER_1        = "Babylonian (Kugler 1)"
    KUGLER_2        = "Babylonian (Kugler 2)"
    KUGLER_3        = "Babylonian (Kugler 3)"
    HUBER           = "Babylonian (Huber)"
    ETA_PISCIUM     = "Babylonian (Eta Piscium)"
    ALDEBARAN_15_TAU = "Aldebaran (15 Tau)"
    GALACTIC_0_SAG  = "Galactic Center (0 Sag)"
    GALACTIC_5_SAG  = "Galactic Center (5 Sag)"
    HIPPARCHOS      = "Hipparchos"
    SURYASIDDHANTA  = "Suryasiddhanta"
    SURYASIDDHANTA_MSUN = "Suryasiddhanta (Mean Sun)"
    ARYABHATA       = "Aryabhata"
    ARYABHATA_MSUN  = "Aryabhata (Mean Sun)"
    SS_REVATI       = "SS Revati"
    SS_CITRA        = "SS Citra"
    TRUE_REVATI     = "True Revati"
    TRUE_PUSHYA     = "True Pushya"
    GALCENT_RG_BRAND = "Galactic Center (RGB)"
    GALCENT_COCHRANE = "Galactic Center (Cochrane)"
    ARYABHATA_522    = "Aryabhata 522"          # 522 CE epoch; Aryabhatiya lineage
    BABYL_BRITTON    = "Babylonian (Britton)"   # Britton; peer-reviewed Babylonian tablets
    TRUE_MULA        = "True Mula"              # Star-anchored: Shaula (λ Sco) at 240°
    GALEQU_IAU1958   = "Galactic Equator (IAU 1958)"  # Blaauw et al. 1960, BAN 11 414

    ALL = [
        LAHIRI, FAGAN_BRADLEY, KRISHNAMURTI, RAMAN,
        YUKTESHWAR, DJWHAL_KHUL, TRUE_CHITRAPAKSHA,
        DE_LUCE, USHA_SHASHI, SASSANIAN, BHASIN,
        KUGLER_1, KUGLER_2, KUGLER_3, HUBER,
        ETA_PISCIUM, ALDEBARAN_15_TAU,
        GALACTIC_0_SAG, GALACTIC_5_SAG,
        HIPPARCHOS, SURYASIDDHANTA, SURYASIDDHANTA_MSUN,
        ARYABHATA, ARYABHATA_MSUN, SS_REVATI, SS_CITRA,
        TRUE_REVATI, TRUE_PUSHYA, GALCENT_RG_BRAND,
        GALCENT_COCHRANE, ARYABHATA_522, BABYL_BRITTON,
        TRUE_MULA, GALEQU_IAU1958,
    ]


# ---------------------------------------------------------------------------
# Ayanamsa values at J2000.0 (degrees) — standard reference values
# Annual precession ≈ 50.2388″/year = 0.013955°/year
# Each system defines its own epoch offset.
# ---------------------------------------------------------------------------

# Reference: Astro-Databank, Swiss Ephemeris documentation, Lahiri Commission
_AYANAMSA_AT_J2000: dict[str, float] = {
    # Swiss-compatible J2000 anchors back-solved from Astro.com swetest output
    # at 2000-01-01 00:00 UT with -nonut, while retaining Moira's precession model.
    Ayanamsa.LAHIRI:            23.857092317461543,
    Ayanamsa.FAGAN_BRADLEY:     24.740299956350434,
    Ayanamsa.KRISHNAMURTI:      23.76024001190599,
    Ayanamsa.RAMAN:             22.410791011905985,
    Ayanamsa.YUKTESHWAR:        22.478803011905985,
    Ayanamsa.DJWHAL_KHUL:       28.359678595239323,
    Ayanamsa.TRUE_CHITRAPAKSHA: 23.83996870635043,
    Ayanamsa.DE_LUCE:           27.815752761905987,
    Ayanamsa.USHA_SHASHI:       20.057541011905986,
    Ayanamsa.SASSANIAN:         19.9929593730171,
    Ayanamsa.BHASIN:            22.76213701190599,
    Ayanamsa.KUGLER_1:          23.5336398730171,
    Ayanamsa.KUGLER_2:          24.9336398730171,
    Ayanamsa.KUGLER_3:          25.7836398730171,
    Ayanamsa.HUBER:             24.7336398730171,
    Ayanamsa.ETA_PISCIUM:       24.522527928572654,
    Ayanamsa.ALDEBARAN_15_TAU:  24.7589238730171,
    Ayanamsa.GALACTIC_0_SAG:    26.846036011905987,
    Ayanamsa.GALACTIC_5_SAG:    31.846036011905987,
    Ayanamsa.HIPPARCHOS:        20.247788095239322,
    Ayanamsa.SURYASIDDHANTA:    20.89505884523932,
    Ayanamsa.SURYASIDDHANTA_MSUN: 20.680424900794875,
    Ayanamsa.ARYABHATA:         20.89505973412821,
    Ayanamsa.ARYABHATA_MSUN:    20.65742734523932,
    Ayanamsa.SS_REVATI:         20.1033883730171,
    Ayanamsa.SS_CITRA:          23.005763289683763,
    Ayanamsa.TRUE_REVATI:       20.0452116230171,
    Ayanamsa.TRUE_PUSHYA:       22.727067234128207,
    Ayanamsa.GALCENT_RG_BRAND:  22.46909498412821,
    Ayanamsa.GALCENT_COCHRANE:  356.846036011906,
    # --- Added after individual doctrinal audit (2026-04) ---
    # Epoch: AD 522 CE; Aryabhatiya lineage. Cited in Pingree & Plofker.
    Ayanamsa.ARYABHATA_522:     20.575827873,
    # Epoch: Babylonian tablets, Britton derivation. Peer-reviewed in Centaurus,
    # AHES, and JHA.
    Ayanamsa.BABYL_BRITTON:     24.615733680,
    # Star-anchored fallback: Shaula (λ Sco) at 240° sidereal (Chandra Hari).
    # Live star position is preferred at compute time; this polynomial is the
    # fallback if Shaula is absent from the fixed-star catalog.
    Ayanamsa.TRUE_MULA:         24.579939992,
    # Epoch: IAU 1958 galactic coordinate standard (Blaauw et al. 1960,
    # Bull. Astron. Inst. Netherlands 11, 414). Carries a non-standard drift
    # term for the galactic nodal intersection with the ecliptic.
    Ayanamsa.GALEQU_IAU1958:    30.023153273,
}

# Small Swiss-compatibility drift terms for systems whose historical motion
# is not reproduced closely enough by the generic longitude precession alone.
# Units: degrees per Julian century from J2000.0.
_AYANAMSA_DRIFT_PER_CENTURY: dict[str, float] = {
    Ayanamsa.GALACTIC_0_SAG:    -0.0017343906255857713,
    Ayanamsa.GALACTIC_5_SAG:    -0.0017343906255857713,
    Ayanamsa.GALCENT_COCHRANE:  -0.001734390625587667,
    Ayanamsa.GALCENT_RG_BRAND:  -0.0017343906255857713,
    Ayanamsa.TRUE_CHITRAPAKSHA: -0.0030344397134131097,
    Ayanamsa.TRUE_PUSHYA:        0.0015419877388162119,
    Ayanamsa.TRUE_REVATI:        0.0048149641721038725,
    # TRUE_MULA polynomial fallback drift (live Shaula anchor is primary path)
    Ayanamsa.TRUE_MULA:         -0.000290,
    # Galactic nodal drift above standard ecliptic precession (empirically measured
    # against pyswisseph; consistent with the IAU 1958 galactic pole definition)
    Ayanamsa.GALEQU_IAU1958:     0.007460,
}

# ---------------------------------------------------------------------------
# Star-anchored ayanamsas
# Each entry: ayanamsa_name → (star_catalog_name, target_sidereal_longitude)
# The ayanamsa is computed as:  star_tropical_lon - target_sidereal_lon
# ---------------------------------------------------------------------------

_STAR_ANCHORED: dict[str, tuple[str, float]] = {
    # Chitrapaksha / True Lahiri: Spica (α Virginis / Chitra) at 180° sidereal
    Ayanamsa.TRUE_CHITRAPAKSHA: ("Spica",     180.0),
    # Revati: ζ Piscium at 29°50' Pisces sidereal (359°50' = 359.8333…°)
    # Swiss sid_mode=28 uses 359°50'; the prior 0° was a rounding error that
    # shifted the ayanamsa by ~10 arcminutes.
    Ayanamsa.TRUE_REVATI:       ("Revati",      359.0 + 50.0 / 60.0),
    # Aldebaran at 15° Taurus sidereal (45°)
    Ayanamsa.ALDEBARAN_15_TAU:  ("Aldebaran",  45.0),
    # Pushya-paksha: δ Cancri (Asellus Australis) at 16°00' Cancer sidereal (106°)
    # Swiss sid_mode=29 uses 106°; the prior 106.667° (16°40') was incorrect.
    Ayanamsa.TRUE_PUSHYA:       ("Asellus Australis", 106.0),
    # Mula-paksha (Chandra Hari): λ Scorpii (Shaula) at 0° Mula sidereal (240°)
    Ayanamsa.TRUE_MULA:         ("Shaula",    240.0),
}


def _star_anchored_ayanamsa(system: str, jd: float) -> float:
    """
    Compute a star-anchored ayanamsa from the actual apparent tropical
    longitude of the anchor star.

    ayanamsa = star_tropical_longitude − target_sidereal_longitude

    Falls back to the polynomial approximation only when the anchor star
    cannot be found in the fixed-star catalog (``LookupError`` or
    ``FileNotFoundError``), which occurs when ``moira/data/star_registry.csv``
    is absent or does not contain the anchor star.

    All other failures (kernel errors, numerical exceptions, etc.) propagate
    to the caller rather than being silently swallowed.
    """
    from .stars import star_at
    from .julian import ut_to_tt, decimal_year
    from .planets import approx_year as _approx_year

    star_name, target_sid = _STAR_ANCHORED[system]

    try:
        # star_at expects JD in TT; difference from UT is ~1 min, negligible
        # for proper motion but we compute it correctly anyway
        year, month, *_ = _approx_year(jd)
        jd_tt = ut_to_tt(jd, decimal_year(year, month))
        star = star_at(star_name, jd_tt)
        return (star.longitude - target_sid) % 360.0
    except (LookupError, FileNotFoundError):
        # Star not in catalog or registry absent — fall back to polynomial
        base = _AYANAMSA_AT_J2000[system]
        jd_tt = ut_to_tt(jd)
        dpsi_deg, _ = nutation(jd_tt)
        return base + general_precession_in_longitude(jd_tt) + dpsi_deg


def ayanamsa(
    jd: float,
    system: 'str | UserDefinedAyanamsa' = Ayanamsa.LAHIRI,
    mode: str = "true",
) -> float:
    """
    Compute the ayanamsa for a given Julian Day.

    The caller should pass a JD in UT. The sidereal engine converts that UT
    epoch to TT internally before invoking TT-based precession and nutation
    helpers, including the star-anchored fallback path. Passing a JD already
    in TT will introduce a duplicate UT→TT shift.

    Parameters
    ----------
    jd     : Julian Day Number
    system : one of the Ayanamsa.* constants, or a :class:`UserDefinedAyanamsa`
             instance for a caller-supplied reference value.
    mode   : "mean" (precession only; polynomial for all systems) or
             "true" (live star-anchored for systems in ``_STAR_ANCHORED``;
             precession + nutation Δψ for all other polynomial systems).
             Ignored for ``UserDefinedAyanamsa`` in ``mode='true'`` (Δψ still
             applied) — star-anchored resolution is never attempted.

    Returns
    -------
    Ayanamsa value in degrees

    Notes
    -----
    Systems listed in ``_STAR_ANCHORED`` (TRUE_CHITRAPAKSHA, TRUE_REVATI,
    ALDEBARAN_15_TAU, TRUE_PUSHYA) use the actual apparent tropical longitude
    of their anchor star at ``jd`` to derive the ayanamsa, matching the
    behaviour of Swiss Ephemeris SE_SIDM_TRUE_CITRA etc.  The polynomial
    path (``_AYANAMSA_AT_J2000`` + precession + optional nutation) is used
    for all other systems and as a fallback when the star catalog is absent.

    Ayanamsa.LAHIRI is epoch-anchored (23°15′00.658″ at 21 Mar 1956), not
    star-anchored, matching SE_SIDM_LAHIRI in SwissEph.
    """
    if mode not in ("mean", "true"):
        raise ValueError(f"mode must be 'mean' or 'true', got {mode!r}")

    jd_tt = ut_to_tt(jd)

    # --- UserDefinedAyanamsa branch -----------------------------------------
    if isinstance(system, UserDefinedAyanamsa):
        precession = general_precession_in_longitude(jd_tt)
        T = centuries_from_j2000(jd_tt)
        base = system.reference_value_j2000 + precession + system.drift_per_century * T
        if mode == "true":
            dpsi_deg, _ = nutation(jd_tt)
            return base + dpsi_deg
        return base

    # --- Named system branch ------------------------------------------------
    if system not in _AYANAMSA_AT_J2000:
        raise ValueError(
            f"Unknown ayanamsa system '{system}'. "
            f"Choose from: {list(_AYANAMSA_AT_J2000)}"
        )

    if mode == "true" and system in _STAR_ANCHORED:
        return _star_anchored_ayanamsa(system, jd)

    base = _AYANAMSA_AT_J2000[system]
    precession = general_precession_in_longitude(jd_tt)
    extra_drift = _AYANAMSA_DRIFT_PER_CENTURY.get(system, 0.0) * centuries_from_j2000(jd_tt)

    if mode == "mean":
        return base + precession + extra_drift
    else:  # "true", polynomial systems
        dpsi_deg, _ = nutation(jd_tt)
        return base + precession + extra_drift + dpsi_deg


def tropical_to_sidereal(
    tropical_longitude: float,
    jd: float,
    system: str = Ayanamsa.LAHIRI,
    mode: str = "true",
) -> float:
    """
    Convert a tropical ecliptic longitude to sidereal.

    Returns
    -------
    Sidereal longitude in degrees [0, 360)
    """
    ayan = ayanamsa(jd, system, mode)
    return (tropical_longitude - ayan) % 360.0


def sidereal_to_tropical(
    sidereal_longitude: float,
    jd: float,
    system: str = Ayanamsa.LAHIRI,
    mode: str = "true",
) -> float:
    """
    Convert a sidereal ecliptic longitude to tropical.

    Returns
    -------
    Tropical longitude in degrees [0, 360)
    """
    ayan = ayanamsa(jd, system, mode)
    return (sidereal_longitude + ayan) % 360.0


def list_ayanamsa_systems() -> dict[str, float]:
    """
    Return all available ayanamsa systems with their J2000 values.

    Returns
    -------
    Dict mapping system name → ayanamsa at J2000.0 (degrees)
    """
    return dict(_AYANAMSA_AT_J2000)


# ---------------------------------------------------------------------------
# Nakshatras — 27 Lunar Mansions
# ---------------------------------------------------------------------------

NAKSHATRA_SPAN = 360.0 / 27  # 13.3333...°

NAKSHATRA_NAMES: list[str] = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni",
    "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha",
    "Anuradha", "Jyeshtha", "Mula", "Purva Ashadha", "Uttara Ashadha",
    "Shravana", "Dhanishtha", "Shatabhisha", "Purva Bhadrapada",
    "Uttara Bhadrapada", "Revati",
]

# Lord of each nakshatra (in order) — used for Vimshottari dasha start
NAKSHATRA_LORDS: list[str] = [
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu",
    "Jupiter", "Saturn", "Mercury",  # 1–9 (then repeats)
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu",
    "Jupiter", "Saturn", "Mercury",
    "Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu",
    "Jupiter", "Saturn", "Mercury",
]

# 4 padas (quarters) per nakshatra, each = 3°20' = 3.3333°
PADA_SPAN = NAKSHATRA_SPAN / 4


@dataclass(slots=True)
class NakshatraPosition:
    """
    RITE: The Nakshatra Vessel — a body's place in the lunar mansion of the sky.

    THEOREM: Holds the nakshatra name, index, planetary lord, pada, degrees
    elapsed within the nakshatra, and full sidereal longitude for a single
    body's nakshatra position result.

    RITE OF PURPOSE:
        Serves the Sidereal Engine as the canonical result vessel for nakshatra
        computations. Without this vessel, callers would receive raw nakshatra
        indices with no lord, pada, or degree-within-nakshatra context, making
        Vimshottari dasha calculation and Jyotish chart display impossible.

    LAW OF OPERATION:
        Responsibilities:
            - Store nakshatra name, 0-based index, planetary lord, pada (1-4),
              degrees elapsed within the nakshatra, and full sidereal longitude.
        Non-responsibilities:
            - Does not compute the nakshatra (delegated to ``nakshatra_of``).
            - Does not compute the ayanamsa (delegated to ``ayanamsa``).
        Dependencies:
            - Populated by ``nakshatra_of()`` or ``all_nakshatras_at()``.
        Structural invariants:
            - ``nakshatra_index`` is always in [0, 26].
            - ``pada`` is always in [1, 4].
            - ``degrees_in`` is always in [0, NAKSHATRA_SPAN).
        Succession stance: terminal — not designed for subclassing.

    Canon: Parashara, "Brihat Parashara Hora Shastra" (classical Jyotish
           foundational text).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.sidereal.NakshatraPosition",
        "risk": "medium",
        "api": {
            "public_methods": ["__repr__"],
            "public_attributes": [
                "nakshatra", "nakshatra_index", "nakshatra_lord",
                "pada", "degrees_in", "sidereal_lon"
            ]
        },
        "state": {
            "mutable": false,
            "fields": [
                "nakshatra", "nakshatra_index", "nakshatra_lord",
                "pada", "degrees_in", "sidereal_lon"
            ]
        },
        "effects": {
            "io": [],
            "signals_emitted": [],
            "db_writes": []
        },
        "concurrency": {
            "thread": "pure_computation",
            "cross_thread_calls": "safe_read_only"
        },
        "failures": {
            "raises": [],
            "policy": "caller ensures finite tropical longitude before construction"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]
    """
    nakshatra:       str    # e.g. "Ashwini"
    nakshatra_index: int    # 0–26
    nakshatra_lord:  str    # planetary lord (e.g. "Ketu")
    pada:            int    # 1–4
    degrees_in:      float  # degrees elapsed within the nakshatra (0–13.333)
    sidereal_lon:    float  # full sidereal longitude (degrees)

    def __repr__(self) -> str:
        return (f"{self.nakshatra} (lord: {self.nakshatra_lord}) "
                f"pada {self.pada}  {self.degrees_in:.4f}° in  "
                f"[sidereal {self.sidereal_lon:.4f}°]")


def nakshatra_of(
    tropical_longitude: float,
    jd: float,
    ayanamsa_system: str = Ayanamsa.LAHIRI,
) -> NakshatraPosition:
    """
    Return the nakshatra position for a tropical ecliptic longitude.

    Parameters
    ----------
    tropical_longitude : tropical ecliptic longitude in degrees
    jd                 : Julian Day (for ayanamsa computation)
    ayanamsa_system    : ayanamsa system (default: Lahiri)

    Returns
    -------
    NakshatraPosition dataclass
    """
    sid_lon = tropical_to_sidereal(tropical_longitude, jd, system=ayanamsa_system)
    idx = int(sid_lon / NAKSHATRA_SPAN) % 27
    degrees_in = sid_lon - idx * NAKSHATRA_SPAN
    pada = int(degrees_in / PADA_SPAN) + 1
    # Clamp pada to [1, 4] — floating-point safety at the very boundary
    pada = min(pada, 4)
    return NakshatraPosition(
        nakshatra=NAKSHATRA_NAMES[idx],
        nakshatra_index=idx,
        nakshatra_lord=NAKSHATRA_LORDS[idx],
        pada=pada,
        degrees_in=degrees_in,
        sidereal_lon=sid_lon,
    )


def all_nakshatras_at(
    positions: dict[str, float],
    jd: float,
    ayanamsa_system: str = Ayanamsa.LAHIRI,
) -> dict[str, NakshatraPosition]:
    """
    Compute nakshatra positions for all bodies in a positions dict.

    Parameters
    ----------
    positions       : dict of body name → tropical longitude
    jd              : Julian Day
    ayanamsa_system : ayanamsa system

    Returns
    -------
    Dict of body name → NakshatraPosition
    """
    return {
        name: nakshatra_of(lon, jd, ayanamsa_system)
        for name, lon in positions.items()
    }

