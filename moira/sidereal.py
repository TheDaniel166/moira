"""
Moira — Sidereal Engine
========================

Archetype: Engine

Purpose
-------
Governs ayanamsa computation for sidereal (Vedic) astrology, providing
tropical-to-sidereal and sidereal-to-tropical longitude conversion across
an independently sourced default set of ayanamsa systems, and nakshatra position computation for the
27 Vedic lunar mansions.

Additional or niche systems are supported through ``UserDefinedAyanamsa``
by supplying a source-backed J2000 reference value and optional drift term.

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
The established scalar/result APIs remain unchanged.  Additive ``*_with_truth``
entry points disclose clock binding, ayanamsa resolution, conversion, and
nakshatra-sector evidence without changing those legacy return types.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from .julian import centuries_from_j2000, ut_to_tt
from .precession import general_precession_in_longitude
from .obliquity import nutation

__all__ = [
    "Ayanamsa",
    "UserDefinedAyanamsa",
    "AyanamsaComputationTruth",
    "SiderealLongitudeConversionTruth",
    "NakshatraPosition",
    "NakshatraComputationTruth",
    "NakshatraWithTruth",
    "NakshatraCollectionWithTruth",
    "ayanamsa",
    "ayanamsa_with_truth",
    "tropical_to_sidereal",
    "tropical_to_sidereal_with_truth",
    "sidereal_to_tropical",
    "sidereal_to_tropical_with_truth",
    "list_ayanamsa_systems",
    "nakshatra_of",
    "nakshatra_of_with_truth",
    "all_nakshatras_at",
    "all_nakshatras_at_with_truth",
]


def _require_finite(name: str, value: float) -> float:
    """Return one finite numeric input or fail at the owning boundary."""

    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be numeric and finite") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return result

# ---------------------------------------------------------------------------
# User-defined ayanamsa  (Phase 3 — Defer.Doctrine; ayanamsa expansion)
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class UserDefinedAyanamsa:
    """
    A caller-supplied ayanamsa specified by its J2000.0 reference value.

    Replaces legacy global sidereal-mode mutation patterns
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

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "reference_value_j2000",
            _require_finite("reference_value_j2000", self.reference_value_j2000),
        )
        object.__setattr__(
            self,
            "drift_per_century",
            _require_finite("drift_per_century", self.drift_per_century),
        )


@dataclass(frozen=True, slots=True)
class AyanamsaComputationTruth:
    """Inspectable clock, model, component, anchor, and fallback identity."""

    jd_ut: float | None
    jd_tt: float
    ayanamsa_system: str
    system_kind: str
    requested_mode: str
    effective_path: str
    ayanamsa_unwrapped_deg: float
    ayanamsa_deg: float
    reference_value_j2000_deg: float | None
    precession_longitude_deg: float | None
    drift_correction_deg: float | None
    nutation_longitude_deg: float | None
    anchor_star: str | None
    anchor_target_sidereal_longitude_deg: float | None
    anchor_tropical_longitude_deg: float | None
    anchor_source_mode: str | None
    fallback_applied: bool
    fallback_reason: str | None
    input_timescale: str = "UT"
    computation_timescale: str = "TT"
    output_normalization: str = "degrees_modulo_360"


@dataclass(frozen=True, slots=True)
class SiderealLongitudeConversionTruth:
    """One longitude conversion bound to exactly one ayanamsa resolution."""

    direction: str
    input_longitude_deg: float
    normalized_input_longitude_deg: float
    output_longitude_deg: float
    source_frame: str
    target_frame: str
    ayanamsa: AyanamsaComputationTruth


# ---------------------------------------------------------------------------
# Ayanamsa system identifiers
# ---------------------------------------------------------------------------

class Ayanamsa:
    """
    RITE: The Warden of Zodiacs — the canonical namespace for ayanamsa systems.

    THEOREM: Provides string constants for the default independently
    sourceable ayanamsa set and an ``ALL`` list for iteration.

    RITE OF PURPOSE:
        Serves the Sidereal Engine as the authoritative name registry for
        ayanamsa systems. Without this Warden, callers would use ad-hoc
        string literals that diverge across the codebase, breaking lookup
        against ``_AYANAMSA_AT_J2000`` and causing silent wrong-system errors.

    LAW OF OPERATION:
        Responsibilities:
            - Declare one class-level string constant per ayanamsa system.
            - Expose ``ALL`` as an ordered list of the default system names.
        Non-responsibilities:
            - Does not compute ayanamsa values.
            - Does not validate that a name is present in the reference table.
        Dependencies:
            - None. Pure namespace class with no runtime dependencies.
        Structural invariants:
            - ``ALL`` contains exactly 12 entries in canonical order.
        Succession stance: terminal — not designed for subclassing.

    Canon: Lahiri Commission (1955); historical sidereal literature;
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
    ALDEBARAN_15_TAU = "Aldebaran (15 Tau)"
    TRUE_REVATI     = "True Revati"
    TRUE_PUSHYA     = "True Pushya"
    TRUE_MULA        = "True Mula"              # Star-anchored: Shaula (λ Sco) at 240°

    ALL = [
        LAHIRI, FAGAN_BRADLEY, KRISHNAMURTI, RAMAN,
        YUKTESHWAR, DJWHAL_KHUL, TRUE_CHITRAPAKSHA,
        DE_LUCE, ALDEBARAN_15_TAU,
        TRUE_REVATI, TRUE_PUSHYA,
        TRUE_MULA,
    ]


# ---------------------------------------------------------------------------
# Ayanamsa values at J2000.0 (degrees) — standard reference values
# Annual precession ≈ 50.2388″/year = 0.013955°/year
# Each system defines its own epoch offset.
# ---------------------------------------------------------------------------

# Reference table policy:
# - Default set contains only systems with independently sourceable literature
#   outside any single-engine implementation lineage.
# - Values are J2000 anchors used by Moira's existing computation path.
_AYANAMSA_AT_J2000: dict[str, float] = {
    # Lahiri Commission report (Government of India Calendar Reform, 1955).
    Ayanamsa.LAHIRI:            23.857092317461543,
    # Fagan & Bradley, Primer of Sidereal Astrology (1967).
    Ayanamsa.FAGAN_BRADLEY:     24.740299956350434,
    # K.S. Krishnamurti, KP ayanamsa tables/publications.
    Ayanamsa.KRISHNAMURTI:      23.76024001190599,
    # B.V. Raman, sidereal ephemeris/tables.
    Ayanamsa.RAMAN:             22.410791011905985,
    # Sri Yukteswar, The Holy Science (1894) lineage.
    Ayanamsa.YUKTESHWAR:        22.478803011905985,
    # Alice A. Bailey / Djwhal Khul theosophical sidereal tradition.
    Ayanamsa.DJWHAL_KHUL:       28.359678595239323,
    # Chitrapaksha true-star anchor: Spica fixed at 180° sidereal.
    Ayanamsa.TRUE_CHITRAPAKSHA: 23.83996870635043,
    # Cyril Fagan, Zodiacs Old and New (1951), De Luce variant lineage.
    Ayanamsa.DE_LUCE:           27.815752761905987,
    # Aldebaran anchor convention: α Tau at 15° Taurus sidereal.
    Ayanamsa.ALDEBARAN_15_TAU:  24.7589238730171,
    # Revati true-star anchor: ζ Piscium fixed at 359°50'.
    Ayanamsa.TRUE_REVATI:       20.0452116230171,
    # Pushya true-star anchor: δ Cancri fixed at 106°.
    Ayanamsa.TRUE_PUSHYA:       22.727067234128207,
    # Star-anchored fallback: Shaula (λ Sco) at 240° sidereal (Chandra Hari).
    # Live star position is preferred at compute time; this polynomial is the
    # fallback if Shaula is absent from the fixed-star catalog.
    Ayanamsa.TRUE_MULA:         24.579939992,
}

# Small compatibility drift terms for systems whose historical motion
# is not reproduced closely enough by the generic longitude precession alone.
# Units: degrees per Julian century from J2000.0.
_AYANAMSA_DRIFT_PER_CENTURY: dict[str, float] = {
    # Empirical compatibility drifts for true-star anchored variants.
    Ayanamsa.TRUE_CHITRAPAKSHA: -0.0030344397134131097,
    Ayanamsa.TRUE_PUSHYA:        0.0015419877388162119,
    Ayanamsa.TRUE_REVATI:        0.0048149641721038725,
    # TRUE_MULA polynomial fallback drift (live Shaula anchor is primary path)
    Ayanamsa.TRUE_MULA:         -0.000290,
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
    # Use 359°50'; the prior 0° was a rounding error that
    # shifted the ayanamsa by ~10 arcminutes.
    Ayanamsa.TRUE_REVATI:       ("Revati",      359.0 + 50.0 / 60.0),
    # Aldebaran at 15° Taurus sidereal (45°)
    Ayanamsa.ALDEBARAN_15_TAU:  ("Aldebaran",  45.0),
    # Pushya-paksha: δ Cancri (Asellus Australis) at 16°00' Cancer sidereal (106°)
    # Use 106°; the prior 106.667° (16°40') was incorrect.
    Ayanamsa.TRUE_PUSHYA:       ("Asellus Australis", 106.0),
    # Mula-paksha (Chandra Hari): λ Scorpii (Shaula) at 0° Mula sidereal (240°)
    Ayanamsa.TRUE_MULA:         ("Shaula",    240.0),
}


def _star_anchored_ayanamsa_at_tt(system: str, jd_tt: float) -> float:
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
    return _ayanamsa_truth_at_tt(
        jd_tt,
        system,
        "true",
    ).ayanamsa_unwrapped_deg


def _ayanamsa_truth_at_tt(
    jd_tt: float,
    system: 'str | UserDefinedAyanamsa' = Ayanamsa.LAHIRI,
    mode: str = "true",
    *,
    jd_ut: float | None = None,
) -> AyanamsaComputationTruth:
    """Resolve one ayanamsa at TT and retain every effective model term."""

    jd_tt = _require_finite("jd_tt", jd_tt)
    if jd_ut is not None:
        jd_ut = _require_finite("jd_ut", jd_ut)
    if mode not in ("mean", "true"):
        raise ValueError(f"mode must be 'mean' or 'true', got {mode!r}")

    if isinstance(system, UserDefinedAyanamsa):
        system_name = "UserDefinedAyanamsa"
        reference = system.reference_value_j2000
        precession = general_precession_in_longitude(jd_tt)
        drift = system.drift_per_century * centuries_from_j2000(jd_tt)
        nutation_longitude = None
        if mode == "true":
            nutation_longitude, _ = nutation(jd_tt)
        value = reference + precession + drift + (nutation_longitude or 0.0)
        return AyanamsaComputationTruth(
            jd_ut=jd_ut,
            jd_tt=jd_tt,
            ayanamsa_system=system_name,
            system_kind="user_defined",
            requested_mode=mode,
            effective_path=(
                "user_defined_reference_plus_precession_plus_drift_plus_nutation"
                if mode == "true"
                else "user_defined_reference_plus_precession_plus_drift"
            ),
            ayanamsa_unwrapped_deg=value,
            ayanamsa_deg=value % 360.0,
            reference_value_j2000_deg=reference,
            precession_longitude_deg=precession,
            drift_correction_deg=drift,
            nutation_longitude_deg=nutation_longitude,
            anchor_star=None,
            anchor_target_sidereal_longitude_deg=None,
            anchor_tropical_longitude_deg=None,
            anchor_source_mode=None,
            fallback_applied=False,
            fallback_reason=None,
        )

    if system not in _AYANAMSA_AT_J2000:
        raise ValueError(
            f"Unknown ayanamsa system '{system}'. "
            f"Choose from: {list(_AYANAMSA_AT_J2000)}"
        )

    anchor = _STAR_ANCHORED.get(system)
    if mode == "true" and anchor is not None:
        from .stars import star_at

        star_name, target_sidereal = anchor
        try:
            # Ayanamsa anchors use the astrometric star (FIXED_STARS_BACKEND_STANDARD.md,
            # Section 5): the Gochara interval enclosure encloses that same product, and
            # an apparent anchor would add a yearly aberration swing to the ayanamsa.
            star = star_at(star_name, jd_tt, product="astrometric")
        except LookupError:
            fallback_reason = "anchor_star_not_found"
        except FileNotFoundError:
            fallback_reason = "star_registry_unavailable"
        else:
            value = (star.longitude - target_sidereal) % 360.0
            star_truth = star.computation_truth
            return AyanamsaComputationTruth(
                jd_ut=jd_ut,
                jd_tt=jd_tt,
                ayanamsa_system=system,
                system_kind="built_in_star_anchored",
                requested_mode=mode,
                effective_path="live_star_anchor",
                ayanamsa_unwrapped_deg=value,
                ayanamsa_deg=value,
                reference_value_j2000_deg=None,
                precession_longitude_deg=None,
                drift_correction_deg=None,
                nutation_longitude_deg=None,
                anchor_star=star_name,
                anchor_target_sidereal_longitude_deg=target_sidereal,
                anchor_tropical_longitude_deg=star.longitude,
                anchor_source_mode=(
                    star_truth.source_mode if star_truth is not None else star.source
                ),
                fallback_applied=False,
                fallback_reason=None,
            )
    else:
        fallback_reason = None

    reference = _AYANAMSA_AT_J2000[system]
    precession = general_precession_in_longitude(jd_tt)
    drift = (
        _AYANAMSA_DRIFT_PER_CENTURY.get(system, 0.0)
        * centuries_from_j2000(jd_tt)
    )
    nutation_longitude = None
    if mode == "true":
        nutation_longitude, _ = nutation(jd_tt)
    value = reference + precession + drift + (nutation_longitude or 0.0)
    fallback_applied = fallback_reason is not None
    star_name, target_sidereal = anchor if anchor is not None else (None, None)
    return AyanamsaComputationTruth(
        jd_ut=jd_ut,
        jd_tt=jd_tt,
        ayanamsa_system=system,
        system_kind=(
            "built_in_star_anchored" if anchor is not None else "built_in_polynomial"
        ),
        requested_mode=mode,
        effective_path=(
            "polynomial_fallback_reference_plus_precession_plus_drift_plus_nutation"
            if fallback_applied
            else (
                "polynomial_reference_plus_precession_plus_drift_plus_nutation"
                if mode == "true"
                else "polynomial_reference_plus_precession_plus_drift"
            )
        ),
        ayanamsa_unwrapped_deg=value,
        ayanamsa_deg=value % 360.0,
        reference_value_j2000_deg=reference,
        precession_longitude_deg=precession,
        drift_correction_deg=drift,
        nutation_longitude_deg=nutation_longitude,
        anchor_star=star_name,
        anchor_target_sidereal_longitude_deg=target_sidereal,
        anchor_tropical_longitude_deg=None,
        anchor_source_mode=None,
        fallback_applied=fallback_applied,
        fallback_reason=fallback_reason,
    )


def _ayanamsa_at_tt(
    jd_tt: float,
    system: 'str | UserDefinedAyanamsa' = Ayanamsa.LAHIRI,
    mode: str = "true",
) -> float:
    """Compute an ayanamsa from an epoch already expressed in TT.

    This private boundary exists for readers that have already composed their
    kernel-specific UT1-to-TT clock path. It never performs another clock
    conversion. Public callers continue to use :func:`ayanamsa`, whose input
    contract remains UT.
    """
    return _ayanamsa_truth_at_tt(
        jd_tt,
        system,
        mode,
    ).ayanamsa_unwrapped_deg


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
    behaviour of star-anchored true sidereal systems.  The polynomial
    path (``_AYANAMSA_AT_J2000`` + precession + optional nutation) is used
    for all other systems and as a fallback when the star catalog is absent.

    Ayanamsa.LAHIRI uses the stored J2000 mean reference value propagated by
    IAU 2006 general precession p_A, with Δψ added in true mode. Its historical
    origin is the March 1956 Lahiri convention; this implementation does not
    impose an exact 1956 apparent-star longitude at every evaluation.
    """
    return ayanamsa_with_truth(jd, system, mode).ayanamsa_unwrapped_deg


def ayanamsa_with_truth(
    jd: float,
    system: 'str | UserDefinedAyanamsa' = Ayanamsa.LAHIRI,
    mode: str = "true",
) -> AyanamsaComputationTruth:
    """Compute one ayanamsa and expose the effective clock/model branch."""

    if mode not in ("mean", "true"):
        raise ValueError(f"mode must be 'mean' or 'true', got {mode!r}")
    jd_ut = _require_finite("jd", jd)
    jd_tt = ut_to_tt(jd_ut)
    return _ayanamsa_truth_at_tt(jd_tt, system, mode, jd_ut=jd_ut)


def _tropical_to_sidereal_at_tt(
    tropical_longitude: float,
    jd_tt: float,
    system: 'str | UserDefinedAyanamsa' = Ayanamsa.LAHIRI,
    mode: str = "true",
) -> float:
    """Convert a tropical longitude using an epoch already expressed in TT."""
    tropical_longitude = _require_finite("tropical_longitude", tropical_longitude)
    jd_tt = _require_finite("jd_tt", jd_tt)
    ayan = _ayanamsa_at_tt(jd_tt, system, mode)
    return (tropical_longitude - ayan) % 360.0


def tropical_to_sidereal(
    tropical_longitude: float,
    jd: float,
    system: 'str | UserDefinedAyanamsa' = Ayanamsa.LAHIRI,
    mode: str = "true",
) -> float:
    """
    Convert a tropical ecliptic longitude to sidereal.

    Returns
    -------
    Sidereal longitude in degrees [0, 360)
    """
    return tropical_to_sidereal_with_truth(
        tropical_longitude,
        jd,
        system,
        mode,
    ).output_longitude_deg


def tropical_to_sidereal_with_truth(
    tropical_longitude: float,
    jd: float,
    system: 'str | UserDefinedAyanamsa' = Ayanamsa.LAHIRI,
    mode: str = "true",
) -> SiderealLongitudeConversionTruth:
    """Convert tropical longitude with one inspectable ayanamsa resolution."""

    longitude = _require_finite("tropical_longitude", tropical_longitude)
    ayanamsa_truth = ayanamsa_with_truth(jd, system, mode)
    normalized_input = longitude % 360.0
    # Preserve the established scalar operation order exactly; the normalized
    # terms are disclosed separately rather than substituted into arithmetic.
    output = (longitude - ayanamsa_truth.ayanamsa_unwrapped_deg) % 360.0
    return SiderealLongitudeConversionTruth(
        direction="tropical_to_sidereal",
        input_longitude_deg=longitude,
        normalized_input_longitude_deg=normalized_input,
        output_longitude_deg=output,
        source_frame="tropical_ecliptic_longitude",
        target_frame="sidereal_ecliptic_longitude",
        ayanamsa=ayanamsa_truth,
    )


def sidereal_to_tropical(
    sidereal_longitude: float,
    jd: float,
    system: 'str | UserDefinedAyanamsa' = Ayanamsa.LAHIRI,
    mode: str = "true",
) -> float:
    """
    Convert a sidereal ecliptic longitude to tropical.

    Returns
    -------
    Tropical longitude in degrees [0, 360)
    """
    return sidereal_to_tropical_with_truth(
        sidereal_longitude,
        jd,
        system,
        mode,
    ).output_longitude_deg


def sidereal_to_tropical_with_truth(
    sidereal_longitude: float,
    jd: float,
    system: 'str | UserDefinedAyanamsa' = Ayanamsa.LAHIRI,
    mode: str = "true",
) -> SiderealLongitudeConversionTruth:
    """Convert sidereal longitude with one inspectable ayanamsa resolution."""

    longitude = _require_finite("sidereal_longitude", sidereal_longitude)
    ayanamsa_truth = ayanamsa_with_truth(jd, system, mode)
    normalized_input = longitude % 360.0
    output = (longitude + ayanamsa_truth.ayanamsa_unwrapped_deg) % 360.0
    return SiderealLongitudeConversionTruth(
        direction="sidereal_to_tropical",
        input_longitude_deg=longitude,
        normalized_input_longitude_deg=normalized_input,
        output_longitude_deg=output,
        source_frame="sidereal_ecliptic_longitude",
        target_frame="tropical_ecliptic_longitude",
        ayanamsa=ayanamsa_truth,
    )


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


def _nakshatra_sector(sidereal_longitude: float) -> tuple[float, int, float]:
    """Classify a longitude in the 27 equal half-open sidereal sectors.

    Internal boundaries are the rational angles ``k * 40/3`` degrees. A
    value equal to the closest binary float for such a boundary, or exactly
    its first predecessor float, belongs to the following nakshatra. The
    recovery is deliberately bounded: the second predecessor remains in the
    preceding sector, and the predecessor of 360 degrees is never moved
    across the zodiac seam.

    Returns ``(normalized_longitude, zero_based_index, degrees_in_sector)``.
    """
    sidereal_longitude = _require_finite(
        "sidereal_longitude",
        sidereal_longitude,
    )
    sid_lon = sidereal_longitude % 360.0

    # A negative value infinitesimally below zero can round its positive
    # remainder to 360.0. Preserve its lawful place in Revati rather than
    # turning it into the 0-degree seam.
    if sid_lon == 360.0:
        sid_lon = math.nextafter(360.0, -math.inf)

    scaled = sid_lon * 3.0 / 40.0
    candidate = int(round(scaled))
    if 1 <= candidate < 27:
        boundary = candidate * 40.0 / 3.0
        if sid_lon == boundary or sid_lon == math.nextafter(boundary, -math.inf):
            return boundary, candidate, 0.0

    idx = min(int(math.floor(scaled)), 26)
    left_boundary = idx * 40.0 / 3.0
    return sid_lon, idx, sid_lon - left_boundary


@dataclass(frozen=True, slots=True)
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


@dataclass(frozen=True, slots=True)
class NakshatraComputationTruth:
    """Inspectable longitude conversion and half-open sector assignment."""

    tropical_longitude_deg: float
    normalized_tropical_longitude_deg: float
    sidereal_longitude_deg: float
    nakshatra_index: int
    sector_start_longitude_deg: float
    sector_end_longitude_deg: float
    pada: int
    ayanamsa: AyanamsaComputationTruth
    taxonomy: str = "twenty_seven_equal_nakshatras"
    sector_boundary_policy: str = "half_open_with_one_predecessor_ulp_recovery"
    interpretation: str = "none_mechanical_position_only"


@dataclass(frozen=True, slots=True)
class NakshatraWithTruth:
    """Backward-compatible nakshatra vessel paired with computation truth."""

    result: NakshatraPosition
    truth: NakshatraComputationTruth


@dataclass(frozen=True, slots=True)
class NakshatraCollectionWithTruth:
    """A bounded position map sharing one ayanamsa resolution."""

    results: dict[str, NakshatraPosition]
    truths: dict[str, NakshatraComputationTruth]
    ayanamsa: AyanamsaComputationTruth


def _nakshatra_position_from_sidereal(
    sidereal_longitude: float,
) -> NakshatraPosition:
    """Build the canonical nakshatra vessel from a sidereal longitude."""
    sid_lon, idx, degrees_in = _nakshatra_sector(sidereal_longitude)
    pada = min(int(degrees_in / PADA_SPAN) + 1, 4)
    return NakshatraPosition(
        nakshatra=NAKSHATRA_NAMES[idx],
        nakshatra_index=idx,
        nakshatra_lord=NAKSHATRA_LORDS[idx],
        pada=pada,
        degrees_in=degrees_in,
        sidereal_lon=sid_lon,
    )


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
    return nakshatra_of_with_truth(
        tropical_longitude,
        jd,
        ayanamsa_system,
    ).result


def _nakshatra_truth_from_conversion(
    tropical_longitude: float,
    conversion: SiderealLongitudeConversionTruth,
) -> NakshatraWithTruth:
    position = _nakshatra_position_from_sidereal(conversion.output_longitude_deg)
    sector_start = position.nakshatra_index * NAKSHATRA_SPAN
    return NakshatraWithTruth(
        result=position,
        truth=NakshatraComputationTruth(
            tropical_longitude_deg=tropical_longitude,
            normalized_tropical_longitude_deg=(tropical_longitude % 360.0),
            sidereal_longitude_deg=position.sidereal_lon,
            nakshatra_index=position.nakshatra_index,
            sector_start_longitude_deg=sector_start,
            sector_end_longitude_deg=sector_start + NAKSHATRA_SPAN,
            pada=position.pada,
            ayanamsa=conversion.ayanamsa,
        ),
    )


def nakshatra_of_with_truth(
    tropical_longitude: float,
    jd: float,
    ayanamsa_system: 'str | UserDefinedAyanamsa' = Ayanamsa.LAHIRI,
) -> NakshatraWithTruth:
    """Return a nakshatra position with its effective sidereal reduction."""

    longitude = _require_finite("tropical_longitude", tropical_longitude)
    conversion = tropical_to_sidereal_with_truth(
        longitude,
        jd,
        system=ayanamsa_system,
        mode="true",
    )
    return _nakshatra_truth_from_conversion(longitude, conversion)


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
    return all_nakshatras_at_with_truth(
        positions,
        jd,
        ayanamsa_system,
    ).results


def all_nakshatras_at_with_truth(
    positions: dict[str, float],
    jd: float,
    ayanamsa_system: 'str | UserDefinedAyanamsa' = Ayanamsa.LAHIRI,
) -> NakshatraCollectionWithTruth:
    """Compute a position map while resolving its ayanamsa exactly once."""

    ayanamsa_truth = ayanamsa_with_truth(jd, ayanamsa_system, "true")
    results: dict[str, NakshatraPosition] = {}
    truths: dict[str, NakshatraComputationTruth] = {}
    for name, raw_longitude in positions.items():
        longitude = _require_finite(f"positions[{name!r}]", raw_longitude)
        normalized_input = longitude % 360.0
        sidereal_longitude = (
            longitude - ayanamsa_truth.ayanamsa_unwrapped_deg
        ) % 360.0
        conversion = SiderealLongitudeConversionTruth(
            direction="tropical_to_sidereal",
            input_longitude_deg=longitude,
            normalized_input_longitude_deg=normalized_input,
            output_longitude_deg=sidereal_longitude,
            source_frame="tropical_ecliptic_longitude",
            target_frame="sidereal_ecliptic_longitude",
            ayanamsa=ayanamsa_truth,
        )
        resolved = _nakshatra_truth_from_conversion(longitude, conversion)
        results[name] = resolved.result
        truths[name] = resolved.truth
    return NakshatraCollectionWithTruth(
        results=results,
        truths=truths,
        ayanamsa=ayanamsa_truth,
    )

