"""
Moira — houses.py
The House Engine: governs ecliptic house cusp computation for all supported
house systems using ARMC, obliquity, and geographic coordinates.

Boundary: owns the full pipeline from raw Julian date and observer coordinates
to a populated HouseCusps result vessel. Delegates time conversion to julian,
obliquity and nutation to obliquity, local sidereal time to julian, and
coordinate normalisation to coordinates. Does not own planet positions, aspect
detection, chart assembly, or any display formatting.

Layers present in this file:
    CORE COMPUTATION
        calculate_houses() — the main engine.  Produces all cusp values.
        _whole_sign, _equal_house, _porphyry, _placidus, _koch, … — one
        private function per system; pure mathematics, no policy.

    TRUTH PRESERVATION  (Phase 1)
        HouseCusps.system           — requested system code, never modified.
        HouseCusps.effective_system — system code actually used for cusps.
        HouseCusps.fallback         — True iff effective != requested.
        HouseCusps.fallback_reason  — human-readable fallback cause or None.

    CLASSIFICATION  (Phase 2)
        HouseSystemFamily    — doctrinal family enum (EQUAL, QUADRANT, …).
        HouseSystemCuspBasis — cusp-projection basis enum (ECLIPTIC, SEMI_ARC, …).
        HouseSystemClassification — frozen dataclass: family, cusp_basis,
            latitude_sensitive, polar_capable.
        classify_house_system() — maps a system code → classification.
        HouseCusps.classification — classification of the effective system.

    INSPECTABILITY  (Phase 3)
        HouseCusps.__post_init__        — structural invariant guard raised at
            construction time; catches inconsistent results before callers see them.
        HouseCusps.is_quadrant_system   — True iff effective system is QUADRANT family.
        HouseCusps.is_latitude_sensitive — True iff effective system's cusps vary
            with observer latitude.
        _POLAR_SYSTEMS / _KNOWN_SYSTEMS — module-level frozensets (moved from
            calculate_houses() locals) for explicit, auditable scope.

    DOCTRINE / POLICY  (Phase 4)
        UnknownSystemPolicy — enum: FALLBACK_TO_PLACIDUS (default) or RAISE.
        PolarFallbackPolicy — enum: FALLBACK_TO_PORPHYRY (default), RAISE,
            or EXPERIMENTAL_SEARCH.
        HousePolicy         — frozen dataclass: unknown_system + polar_fallback.
            HousePolicy.default() returns the canonical default (current behavior).
        calculate_houses(..., policy=HousePolicy.default()) — accepts an optional
            policy argument; default is backward-compatible with all prior callers.
        HouseCusps.policy   — the HousePolicy that governed this result.
        Critical-latitude doctrine (explicit):
            The fallback threshold is 90° − obliquity, computed from the chart's
            actual obliquity at call time.  At J2000 this is ≈ 66.56°.  This is
            the geometric Arctic Circle: above it, some ecliptic degrees become
            circumpolar, making semi-arc iteration undefined.  The affected systems
            (Placidus, Koch, Pullen SD) clamp the acos() domain error but return
            astronomically invalid cusp orderings for a large fraction of ARMC
            values above this threshold.  The old fixed 75.0° threshold was wrong:
            it silently passed garbage results from ≈66.6° to 74.9°.
            Pullen SR uses a different formula and remains geometrically valid to
            90°; it is not in _POLAR_SYSTEMS.

    POINT-TO-HOUSE MEMBERSHIP  (Phase 5)
        HousePlacement — frozen result vessel: house number, placed longitude,
            the HouseCusps that determined membership, exact-on-cusp flag, and
            the opening cusp longitude.
        assign_house() — maps an ecliptic longitude to a house (1–12) under
            explicit boundary doctrine using an existing HouseCusps result.
        Boundary doctrine (explicit):
            - Interval rule: house n owns [cusps[n-1], cusps[n % 12]).
              Inclusive on the opening cusp, exclusive on the next.
            - Wraparound: spans are measured as forward arcs on the circle.
              (end − start) % 360° — correct even when cusps cross 0°/360°.
            - Exact-on-cusp: if longitude == cusps[n-1] within 1e-9°,
              exact_on_cusp is True; point is still assigned to that house.
            - Membership law is identical for all system families (EQUAL,
              QUADRANT, WHOLE_SIGN, SOLAR); only the cusp positions differ.

    CUSP PROXIMITY / BOUNDARY SENSITIVITY  (Phase 6)
        HouseBoundaryProfile — frozen result vessel: opening/closing cusp
            longitudes, forward distances to each, house span, nearest cusp,
            nearest cusp distance, declared near-cusp threshold, is_near_cusp.
        describe_boundary() — derives boundary context from an existing
            HousePlacement without re-performing house assignment.
        Distance doctrine (explicit):
            - dist_to_opening: forward arc (longitude − opening_cusp) % 360°.
              Always ≥ 0; equals 0 when exact_on_cusp is True.
            - dist_to_closing: forward arc (closing_cusp − longitude) % 360°.
              Always > 0 within the assigned house (closing cusp excluded by
              Phase 5 interval rule, so it is never reached).
            - house_span: dist_to_opening + dist_to_closing == full house arc.
            - nearest_cusp_distance: min(dist_to_opening, dist_to_closing).
              This is the within-house minimal distance; always ≤ span / 2.
            - is_near_cusp: nearest_cusp_distance < near_cusp_threshold.
              Threshold is caller-declared; default 3.0° is conventional and
              explicit, not silently imposed doctrine.

    ANGULARITY / HOUSE-POWER STRUCTURE  (Phase 7)
        HouseAngularity  — enum: ANGULAR, SUCCEDENT, CADENT.
        HouseAngularityProfile — frozen result vessel: placement, category,
            house (convenience copy).
        describe_angularity() — maps an existing HousePlacement to its
            structural angularity category using a pure house-number lookup.
        Doctrine (explicit):
            ANGULAR   — houses 1, 4, 7, 10  (the four angular cusps).
            SUCCEDENT — houses 2, 5, 8, 11  (follow the angles).
            CADENT    — houses 3, 6, 9, 12  (precede the angles).
            This is purely house-number-based at this phase; no cusp proximity,
            no orb, and no system-family sensitivity are applied.

    SYSTEM COMPARISON  (Phase 8)
        HouseSystemComparison — frozen result vessel for cusp-level comparison
            of two HouseCusps results: cusp_deltas (signed circular difference
            per house), systems_agree, fallback_differs, families_differ.
        HousePlacementComparison — frozen result vessel for point-placement
            comparison across two or more systems: longitude, per-system
            HousePlacement tuple, house-number tuple, all_agree, angularity_agrees.
        compare_systems(left, right) — cusp-level diff of two HouseCusps.
        compare_placements(longitude, *house_cusps_seq) — places one longitude
            under each system and compares the resulting house assignments.
        Comparison doctrine (explicit):
            - Cusp delta: signed circular difference (right − left) in (−180, 180].
              Positive means right cusp is ahead (counter-clockwise) of left.
            - systems_agree: left.effective_system == right.effective_system.
              Uses effective system (what actually ran), not requested system.
            - fallback_differs: left.fallback != right.fallback.
            - families_differ: classification families of the two effective systems differ.
            - all_agree: all placements land in the same house number.
            - angularity_agrees: all placements share the same HouseAngularity category.
            - Requested-system truth is preserved on each HouseCusps.system field;
              it is never collapsed into effective_system.

    CHART-WIDE HOUSE DISTRIBUTION INTELLIGENCE  (Phase 9)
        HouseOccupancy — frozen per-house record: house number, occupant count,
            occupant longitudes tuple (input order), placements tuple, is_empty.
        HouseDistributionProfile — frozen chart-wide result vessel: the source
            HouseCusps, total point count, 12-entry occupancies tuple, convenience
            counts tuple, empty_houses frozenset, dominant_houses tuple,
            angular/succedent/cadent counts.
        distribute_points(longitudes, house_cusps) — places every longitude in
            the sequence via assign_house() and assembles the distribution profile.
        Distribution doctrine (explicit):
            - Each longitude normalised to [0, 360) before placement.
            - Each longitude placed independently via assign_house(); no new
              membership logic is introduced.
            - occupancies is always 12 entries, indexed house 1–12 in order.
            - dominant_houses: houses with count == max(counts) and max > 0;
              sorted ascending; empty tuple if no points placed.
            - empty_houses: frozenset of house numbers with count == 0.
            - Angularity counts derive from _ANGULARITY_MAP (Phase 7 doctrine).
            - Occupant order within each HouseOccupancy mirrors input order.

    FUTURE LAYERS (not yet present)
        - Hemisphere / quadrant totals (above/below horizon, eastern/western)
        - Harmonic overlays
        - Cross-system chart-distribution comparison
Public surface:
    HouseSystemFamily, HouseSystemCuspBasis,
    HouseSystemClassification, classify_house_system,
    UnknownSystemPolicy, PolarFallbackPolicy, HousePolicy,
    HouseCusps, calculate_houses,
    HousePlacement, assign_house,
    HouseBoundaryProfile, describe_boundary,
    HouseAngularity, HouseAngularityProfile, describe_angularity,
    HouseSystemComparison, HousePlacementComparison,
    compare_systems, compare_placements,
    HouseOccupancy, HouseDistributionProfile, distribute_points

Import-time side effects: None

External dependency assumptions:
    - moira.julian must be importable (ut_to_tt, local_sidereal_time,
      greenwich_mean_sidereal_time).
    - moira.obliquity must be importable (true_obliquity, nutation).
    - moira.coordinates must be importable (normalize_degrees).
    - moira.constants must be importable (DEG2RAD, RAD2DEG, HouseSystem, sign_of).
    - moira.planets is imported lazily inside calculate_houses only when
      HouseSystem.SUNSHINE is requested.
"""

import math
from dataclasses import dataclass, field
from enum import Enum

from .constants import DEG2RAD, RAD2DEG, HouseSystem, sign_of
from .coordinates import normalize_degrees
from .julian import local_sidereal_time, ut_to_tt, greenwich_mean_sidereal_time
from .obliquity import true_obliquity, nutation
from .planets import approx_year as _approx_year

__all__ = [
    # Enums / doctrine
    "HouseSystemFamily",
    "HouseSystemCuspBasis",
    "UnknownSystemPolicy",
    "PolarFallbackPolicy",
    # Classification / policy
    "HouseSystemClassification",
    "classify_house_system",
    "HousePolicy",
    # Result vessels
    "HouseCusps",
    "HousePlacement",
    "HouseBoundaryProfile",
    "HouseAngularity",
    "HouseAngularityProfile",
    "HouseSystemComparison",
    "HousePlacementComparison",
    "HouseOccupancy",
    "HouseDistributionProfile",
    # Public entry points
    "calculate_houses",
    "houses_from_armc",
    "assign_house",
    "body_house_position",
    "describe_boundary",
    "describe_angularity",
    "compare_systems",
    "compare_placements",
    "distribute_points",
    # Phase 3 — house dynamics
    "CuspSpeed",
    "HouseDynamics",
    "cusp_speeds_at",
    "house_dynamics_from_armc",
    # Phase 4 — Rudhyar quadrant emphasis
    "Quadrant",
    "QuadrantEmphasisProfile",
    "quadrant_of",
    "quadrant_emphasis",
    # Phase 5 — diurnal quadrants
    "DiurnalQuadrant",
    "DiurnalPosition",
    "DiurnalEmphasisProfile",
    "diurnal_position",
    "diurnal_emphasis",
  ]


# ===========================================================================
# CLASSIFICATION LAYER
# ===========================================================================

class HouseSystemFamily(str, Enum):
    """
    Doctrinal family of a house system.

    EQUAL
        All twelve houses span exactly 30° of the relevant reference frame
        (ecliptic or equator). Cusps are spaced uniformly; no quadrant
        trisection is involved.  Includes: EQUAL, WHOLE_SIGN, VEHLOW,
        MORINUS, MERIDIAN.

    QUADRANT
        The four angular cusps (ASC, IC, DSC, MC) are derived from ARMC and
        obliquity; the eight intermediate cusps are found by some form of
        trisection or projection within each quadrant.  Includes: PLACIDUS,
        KOCH, PORPHYRY, CAMPANUS, REGIOMONTANUS, ALCABITIUS, TOPOCENTRIC,
        AZIMUTHAL, CARTER, PULLEN_SD, PULLEN_SR, KRUSINSKI, APC.

    WHOLE_SIGN
        The first house is the entire sign rising; all houses are complete
        30° sign divisions regardless of ASC degree within the sign.

    SOLAR
        The Sun's ecliptic position replaces the ASC as the basis for house
        division.  Includes: SUNSHINE.
    """
    EQUAL      = "equal"
    QUADRANT   = "quadrant"
    WHOLE_SIGN = "whole_sign"
    SOLAR      = "solar"


class HouseSystemCuspBasis(str, Enum):
    """
    The projection or division method used to derive intermediate cusp positions.

    ECLIPTIC
        Cusps are placed at equal intervals directly on the ecliptic (or at
        sign boundaries).  No projection from another frame is needed.
        Systems: WHOLE_SIGN, EQUAL, VEHLOW.

    EQUATORIAL
        Equal 30° divisions of the celestial equator are projected onto the
        ecliptic.  Systems: MORINUS, MERIDIAN, CARTER.

    SEMI_ARC
        Intermediate cusps are found via the diurnal or nocturnal semi-arc
        of the Ascendant or of each cusp degree itself (self-referential
        iteration).  Systems: PLACIDUS, ALCABITIUS.

    OBLIQUE_ASCENSION
        Cusps are placed using the oblique ascension of the MC degree,
        projected back to the ecliptic.  Systems: KOCH.

    QUADRANT_TRISECTION
        Each of the four unequal quadrants is trisected directly in ecliptic
        longitude.  Systems: PORPHYRY.

    PRIME_VERTICAL
        Great circles through the prime vertical are projected onto the
        ecliptic.  Systems: CAMPANUS.

    HORIZON
        Great circles through the Zenith (horizon-based) are projected onto
        the ecliptic.  Systems: AZIMUTHAL.

    POLAR_PROJECTION
        Each cusp uses a graduated polar height derived from the observer
        latitude, projected onto the equator then to the ecliptic.
        Systems: REGIOMONTANUS, TOPOCENTRIC.

    SINUSOIDAL
        Intermediate cusps are placed at sinusoidal offsets from the cardinal
        cusps, derived from the quadrant size.  Systems: PULLEN_SD, PULLEN_SR.

    GREAT_CIRCLE
        Great circles through the Ascendant and Zenith divide the sphere;
        cusps are intersections with the ecliptic.  Systems: KRUSINSKI.

    APC_FORMULA
        Uses the APC formula (Boehrer / Polich) which positions cusps via a
        composite ascension angle incorporating latitude and obliquity.
        Systems: APC.

    SOLAR_POSITION
        The Sun's ecliptic longitude is the basis; cusps are equal 30°
        intervals starting from the Sun.  Systems: SUNSHINE.
    """
    ECLIPTIC             = "ecliptic"
    EQUATORIAL           = "equatorial"
    SEMI_ARC             = "semi_arc"
    OBLIQUE_ASCENSION    = "oblique_ascension"
    QUADRANT_TRISECTION  = "quadrant_trisection"
    PRIME_VERTICAL       = "prime_vertical"
    HORIZON              = "horizon"
    POLAR_PROJECTION     = "polar_projection"
    SINUSOIDAL           = "sinusoidal"
    GREAT_CIRCLE         = "great_circle"
    APC_FORMULA          = "apc_formula"
    SOLAR_POSITION       = "solar_position"


@dataclass(frozen=True, slots=True)
class HouseSystemClassification:
    """
    CLASSIFICATION: Doctrinal and computational character of a house system.

    Describes the algorithm that produced a set of cusps — not the cusps
    themselves.  All fields are derivable from the system code alone; none
    depend on computed cusp values, observer latitude, or Julian date.

    Fields:
        family
            The doctrinal family of the system.  See HouseSystemFamily.

        cusp_basis
            The projection or division method used for intermediate cusps.
            See HouseSystemCuspBasis.

        latitude_sensitive
            True if the cusp positions change with the observer's geographic
            latitude (i.e. the system has a meaningful geographic pole).
            False for systems where all observers at the same moment share
            the same cusps regardless of latitude:
            WHOLE_SIGN, EQUAL, VEHLOW, MORINUS, MERIDIAN.

        polar_capable
            True if the system can produce numerically stable results at
            |latitude| >= 75° without falling back to another system.
            Systems that cannot (PLACIDUS, KOCH, PULLEN_SD, PULLEN_SR) have
            polar_capable = False; all others are True.

    This dataclass is frozen (immutable) and carries no computation logic.
    It is a pure doctrinal label attached to an already-computed HouseCusps.

    Future layers that are NOT the responsibility of this class:
        - Cusp-zone or angularity scoring
        - House membership analysis
        - Boundary sensitivity
        - System comparison or policy selection
    """
    family:              HouseSystemFamily
    cusp_basis:          HouseSystemCuspBasis
    latitude_sensitive:  bool
    polar_capable:       bool


# ---------------------------------------------------------------------------
# Classification table: system code → HouseSystemClassification
# ---------------------------------------------------------------------------

_F  = HouseSystemFamily
_CB = HouseSystemCuspBasis

_CLASSIFICATIONS: dict[str, HouseSystemClassification] = {
    HouseSystem.WHOLE_SIGN:    HouseSystemClassification(_F.WHOLE_SIGN, _CB.ECLIPTIC,            False, True),
    HouseSystem.EQUAL:         HouseSystemClassification(_F.EQUAL,      _CB.ECLIPTIC,            False, True),
    HouseSystem.VEHLOW:        HouseSystemClassification(_F.EQUAL,      _CB.ECLIPTIC,            False, True),
    HouseSystem.MORINUS:       HouseSystemClassification(_F.EQUAL,      _CB.EQUATORIAL,          False, True),
    HouseSystem.MERIDIAN:      HouseSystemClassification(_F.EQUAL,      _CB.EQUATORIAL,          False, True),
    HouseSystem.CARTER:        HouseSystemClassification(_F.QUADRANT,   _CB.EQUATORIAL,          True,  True),
    HouseSystem.PORPHYRY:      HouseSystemClassification(_F.QUADRANT,   _CB.QUADRANT_TRISECTION, True,  True),
    HouseSystem.PLACIDUS:      HouseSystemClassification(_F.QUADRANT,   _CB.SEMI_ARC,            True,  False),
    HouseSystem.ALCABITIUS:    HouseSystemClassification(_F.QUADRANT,   _CB.SEMI_ARC,            True,  True),
    HouseSystem.KOCH:          HouseSystemClassification(_F.QUADRANT,   _CB.OBLIQUE_ASCENSION,   True,  False),
    HouseSystem.CAMPANUS:      HouseSystemClassification(_F.QUADRANT,   _CB.PRIME_VERTICAL,      True,  True),
    HouseSystem.AZIMUTHAL:     HouseSystemClassification(_F.QUADRANT,   _CB.HORIZON,             True,  True),
    HouseSystem.REGIOMONTANUS: HouseSystemClassification(_F.QUADRANT,   _CB.POLAR_PROJECTION,    True,  True),
    HouseSystem.TOPOCENTRIC:   HouseSystemClassification(_F.QUADRANT,   _CB.POLAR_PROJECTION,    True,  True),
    HouseSystem.PULLEN_SD:     HouseSystemClassification(_F.QUADRANT,   _CB.SINUSOIDAL,          True,  False),
    HouseSystem.PULLEN_SR:     HouseSystemClassification(_F.QUADRANT,   _CB.SINUSOIDAL,          True,  True),
    HouseSystem.KRUSINSKI:     HouseSystemClassification(_F.QUADRANT,   _CB.GREAT_CIRCLE,        True,  True),
    HouseSystem.APC:           HouseSystemClassification(_F.QUADRANT,   _CB.APC_FORMULA,         True,  True),
    HouseSystem.SUNSHINE:      HouseSystemClassification(_F.SOLAR,      _CB.SOLAR_POSITION,      False, True),
}

def classify_house_system(code: str) -> HouseSystemClassification:
    """
    Return the HouseSystemClassification for the given HouseSystem code.

    The classification describes the algorithm associated with that code —
    its doctrinal family, cusp-projection basis, latitude sensitivity, and
    polar capability.  It is derived entirely from the code string; no
    chart data or observer coordinates are needed.

    When `code` is not a recognised HouseSystem constant, raises ValueError.
    Classification is a property of a declared, known system code, not of a
    downstream fallback policy.

    Args:
        code: A HouseSystem constant string (e.g. HouseSystem.PLACIDUS).

    Returns:
        A frozen HouseSystemClassification for that code.

    Raises:
        ValueError: If ``code`` is not a recognised HouseSystem constant.
    """
    if code not in _CLASSIFICATIONS:
        raise ValueError(f"unknown house system code {code!r}")
    return _CLASSIFICATIONS[code]


# ---------------------------------------------------------------------------
# Module-scope policy sets used by calculate_houses() and __post_init__
# ---------------------------------------------------------------------------

# Systems that produce geometrically disordered cusps above the critical latitude.
# The real breakdown threshold is 90° − obliquity (≈ 66.56° at J2000), not 75°.
# Placidus and Koch: cusp ordering fails above ~66.6° for some ARMC values.
# Pullen SD:         cusp ordering fails above ~64.0° for some ARMC values.
# Pullen SR:         remains geometrically ordered up to 90°; excluded.
_POLAR_SYSTEMS: frozenset[str] = frozenset({
    HouseSystem.PLACIDUS, HouseSystem.KOCH, HouseSystem.PULLEN_SD,
})

# The full set of recognised HouseSystem codes.
_KNOWN_SYSTEMS: frozenset[str] = frozenset({
    HouseSystem.WHOLE_SIGN, HouseSystem.EQUAL, HouseSystem.PORPHYRY,
    HouseSystem.PLACIDUS, HouseSystem.KOCH, HouseSystem.CAMPANUS,
    HouseSystem.REGIOMONTANUS, HouseSystem.ALCABITIUS, HouseSystem.MORINUS,
    HouseSystem.TOPOCENTRIC, HouseSystem.MERIDIAN, HouseSystem.VEHLOW,
    HouseSystem.SUNSHINE, HouseSystem.AZIMUTHAL, HouseSystem.CARTER,
    HouseSystem.PULLEN_SD, HouseSystem.PULLEN_SR, HouseSystem.KRUSINSKI,
    HouseSystem.APC,
})


# ===========================================================================
# DOCTRINE / POLICY LAYER
# ===========================================================================

class UnknownSystemPolicy(str, Enum):
    """
    Doctrine governing what happens when calculate_houses() receives a system
    code that is not present in _KNOWN_SYSTEMS.

    FALLBACK_TO_PLACIDUS (default)
        Silently substitute Placidus and record the substitution in
        HouseCusps.fallback / HouseCusps.fallback_reason.  This is the
        behavior present in all prior phases.

    RAISE
        Raise ValueError immediately instead of substituting.  Use this when
        the caller considers an unknown code a programming error rather than
        an acceptable fallback condition.
    """
    FALLBACK_TO_PLACIDUS = "fallback_to_placidus"
    RAISE                = "raise"


class PolarFallbackPolicy(str, Enum):
    """
    Doctrine governing what happens when calculate_houses() is called above the
    critical latitude (90° − obliquity, ≈ 66.56° at J2000) with a system in
    _POLAR_SYSTEMS.

    FALLBACK_TO_PORPHYRY (default)
        Silently substitute Porphyry and record the substitution in
        HouseCusps.fallback / HouseCusps.fallback_reason.  This is the
        behavior present in all prior phases.

    RAISE
        Raise ValueError immediately instead of substituting.  Use this when
        the caller considers a request for an incapable system above the
        critical latitude a programming error rather than an acceptable
        fallback condition.

    EXPERIMENTAL_SEARCH
        Opt-in research mode. For HouseSystem.PLACIDUS only, attempt a
        branch-aware high-latitude Placidus solve using
        ``moira.experimental_placidus``. If exactly one ordered cusp cycle is
        found, return Placidus directly with no fallback. If no ordered cycle
        is found, or more than one ordered cycle exists, raise ValueError.
        Other polar-incapable systems remain unsupported in this mode.
    """
    FALLBACK_TO_PORPHYRY = "fallback_to_porphyry"
    RAISE                = "raise"
    EXPERIMENTAL_SEARCH  = "experimental_search"


@dataclass(frozen=True, slots=True)
class HousePolicy:
    """
    DOCTRINE: Governing policy for a single house computation.

    Encapsulates the two doctrinal decisions that calculate_houses() must
    make when the requested system cannot be served exactly as requested:

        unknown_system:   what to do when the system code is unrecognised.
        polar_fallback:   what to do when the system is incapable at the
                          requested polar latitude.

    Both fields default to the permissive, silent-substitution behavior that
    was present in all prior phases.  Callers that want strict, no-fallback
    semantics can pass a stricter policy.

    The policy is a pure doctrinal specification — it carries no computation
    logic itself.  It is evaluated by calculate_houses() before any cusp
    mathematics run.

    HousePolicy.default() returns the canonical default policy, which exactly
    replicates all prior behavior.

    Future layers that are NOT the responsibility of this class:
        - System selection or comparison logic
        - Any cusp or angular computation
        - Doctrinal ranking among systems
    """
    unknown_system: UnknownSystemPolicy = UnknownSystemPolicy.FALLBACK_TO_PLACIDUS
    polar_fallback: PolarFallbackPolicy = PolarFallbackPolicy.FALLBACK_TO_PORPHYRY

    @classmethod
    def default(cls) -> "HousePolicy":
        """Return the canonical default policy (silent fallback on both axes)."""
        return cls(
            unknown_system=UnknownSystemPolicy.FALLBACK_TO_PLACIDUS,
            polar_fallback=PolarFallbackPolicy.FALLBACK_TO_PORPHYRY,
        )

    @classmethod
    def strict(cls) -> "HousePolicy":
        """Return a strict policy that raises ValueError on any fallback condition."""
        return cls(
            unknown_system=UnknownSystemPolicy.RAISE,
            polar_fallback=PolarFallbackPolicy.RAISE,
        )

    @classmethod
    def experimental(cls) -> "HousePolicy":
        """Return an explicit policy that enables high-latitude Placidus search."""
        return cls(
            unknown_system=UnknownSystemPolicy.FALLBACK_TO_PLACIDUS,
            polar_fallback=PolarFallbackPolicy.EXPERIMENTAL_SEARCH,
        )


def _experimental_polar_placidus_cusps(
    armc: float,
    obliquity: float,
    latitude: float,
    asc: float,
    mc: float,
) -> list[float]:
    """Search for a unique ordered high-latitude Placidus branch or raise."""
    from .experimental_placidus import ExperimentalPlacidusStatus, search_experimental_placidus

    result = search_experimental_placidus(
        armc,
        obliquity,
        latitude,
        asc,
        mc,
    )
    if result.status == ExperimentalPlacidusStatus.UNIQUE_ORDERED_SOLUTION and result.cusps is not None:
        return list(result.cusps)
    raise ValueError(f"experimental Placidus search failed: {result.diagnostic_summary}")


@dataclass(slots=True)
class HouseCusps:
    """
    RESULT VESSEL: The complete output of one calculate_houses() call.

    Carries twelve ecliptic house cusp longitudes, the four angular points
    (ASC, MC, DSC, IC), ARMC, Vertex, and Anti-Vertex for a single chart
    moment and observer location, together with the full computation trail
    that produced them.

    Cusps are indexed 0–11; house n has its opening cusp at cusps[n-1].

    TRUTH PRESERVATION (Phase 1):
        system:           the house system code *requested* by the caller —
                          never modified, even when fallback occurs.
        effective_system: the system code that was *actually used* for cusps —
                          equals system unless a fallback was triggered.
        fallback:         True iff effective_system != system.
        fallback_reason:  human-readable reason when fallback is True; None
                          otherwise.

    CLASSIFICATION (Phase 2):
        classification: HouseSystemClassification for the effective system —
                        family, cusp_basis, latitude_sensitive, polar_capable.
                        Always reflects the system that ran, not the one requested.

    INSPECTABILITY (Phase 3):
        __post_init__ enforces at construction time:
            - len(cusps) == 12
            - For QUADRANT family (cusp_basis ≠ HORIZON): cusps[0] == asc
              within 1e-9°.  HORIZON (Azimuthal) and all non-quadrant systems
              legitimately place H1 ≠ geographic ASC.
            - fallback == (system != effective_system)
            - fallback_reason is None iff fallback is False
            - classification is not None when effective_system is set
        is_quadrant_system: True iff effective system is QUADRANT family.
        is_latitude_sensitive: True iff effective system's cusps vary with
            observer geographic latitude.

    DOCTRINE / POLICY (Phase 4):
        policy: the HousePolicy that governed fallback resolution —
                readable from the result for full auditability.

    Non-responsibilities (delegated to dedicated layers):
        - Cusp computation (calculate_houses)
        - House membership analysis (assign_house / HousePlacement)
        - Angularity scoring and cusp-zone classification (Phase 7)
        - Boundary sensitivity (Phase 6)
        - System comparison (Phase 8)
        - Policy enforcement (calculate_houses)
    """
    system:           str
    cusps:            list[float]          # 12 ecliptic longitudes, degrees [0,360)
    asc:              float                # Ascendant
    mc:               float                # Midheaven
    armc:             float                # ARMC (Right Ascension of MC)
    vertex:           float | None = None  # Vertex (western prime-vertical / ecliptic intersection)
    anti_vertex:      float | None = None  # Anti-Vertex (opposite Vertex)
    effective_system: str                          = ""      # House system code actually used for computation
    fallback:         bool                         = False   # True iff effective_system != system
    fallback_reason:  str | None                   = None    # Why fallback occurred; None when fallback is False
    classification:   HouseSystemClassification | None = None  # Doctrinal classification of effective_system
    policy:           HousePolicy | None                = None  # Policy that governed fallback resolution

    @property
    def dsc(self) -> float:
        return (self.asc + 180.0) % 360.0

    @property
    def ic(self) -> float:
        return (self.mc + 180.0) % 360.0

    @property
    def is_quadrant_system(self) -> bool:
        """True iff the effective house system belongs to the QUADRANT family.

        Derived from classification.family.  Equivalent to:
            classification.family == HouseSystemFamily.QUADRANT
        """
        return (
            self.classification is not None
            and self.classification.family == HouseSystemFamily.QUADRANT
        )

    @property
    def is_latitude_sensitive(self) -> bool:
        """True iff the effective house system's cusps vary with observer latitude.

        Derived from classification.latitude_sensitive.  False for systems
        such as Whole Sign, Equal, Vehlow, Morinus, Meridian, and Sunshine,
        where all observers at the same moment share the same cusp longitudes.
        """
        return self.classification is not None and self.classification.latitude_sensitive

    def __post_init__(self) -> None:
        """Structural invariant guard.

        Raises AssertionError if the object is in an internally inconsistent
        state.  This fires at construction time, before any caller can observe
        a malformed result.

        Invariants checked:
            1. len(cusps) == 12
            2. For quadrant-family systems (excluding HORIZON cusp_basis):
               cusps[0] == asc within 1e-9°.
               HORIZON systems (Azimuthal) compute a horizon-based H1 cusp
               that legitimately differs from the geographic Ascendant.
               Non-quadrant systems (Whole Sign, Vehlow, Morinus, Meridian,
               Sunshine) also legitimately place H1 ≠ ASC.
            3. fallback == (system != effective_system) when effective_system is set
            4. fallback_reason is None iff fallback is False
            5. classification is not None when effective_system is set and non-empty
        """
        assert len(self.cusps) == 12, (
            f"HouseCusps invariant violated: len(cusps)={len(self.cusps)}, expected 12"
        )
        if (
            self.cusps
            and self.classification is not None
            and self.classification.family == HouseSystemFamily.QUADRANT
            and self.classification.cusp_basis != HouseSystemCuspBasis.HORIZON
        ):
            diff = abs(self.cusps[0] - self.asc) % 360.0
            assert diff < 1e-9 or abs(diff - 360.0) < 1e-9, (
                f"HouseCusps invariant violated: quadrant system "
                f"cusps[0]={self.cusps[0]:.9f} != asc={self.asc:.9f}"
            )
        if self.effective_system:
            assert self.fallback == (self.system != self.effective_system), (
                f"HouseCusps invariant violated: fallback={self.fallback} but "
                f"system={self.system!r}, effective_system={self.effective_system!r}"
            )
        assert (self.fallback_reason is None) == (not self.fallback), (
            f"HouseCusps invariant violated: fallback={self.fallback} but "
            f"fallback_reason={self.fallback_reason!r}"
        )
        if self.effective_system:
            assert self.classification is not None, (
                f"HouseCusps invariant violated: effective_system={self.effective_system!r} "
                f"is set but classification is None"
            )

    def sign_of_cusp(self, house: int) -> tuple[str, str, float]:
        """Return (sign, symbol, degree_within_sign) for house 1–12."""
        return sign_of(self.cusps[house - 1])


# ---------------------------------------------------------------------------
# ARMC and MC
# ---------------------------------------------------------------------------

def _armc(jd_ut: float, longitude: float, jd_tt: float, dpsi: float, obliquity: float) -> float:
    """Local Sidereal Time = ARMC (degrees)."""
    return local_sidereal_time(jd_ut, longitude, dpsi, obliquity)


def _mc_from_armc(armc: float, obliquity: float, lat: float = 0.0) -> float:
    """
    Midheaven (MC) from ARMC, obliquity, and geographic latitude.

    The MC is the ecliptic longitude whose right ascension equals ARMC.
    Using atan2(sin(ARMC), cos(ARMC)×cos(ε)) preserves the correct quadrant
    for all four quadrants of ARMC.

    Reference: Meeus "Astronomical Algorithms" §24; Swiss Ephemeris swehouse.c.
    """
    armc_r = armc * DEG2RAD
    eps_r  = obliquity * DEG2RAD
    return math.atan2(math.sin(armc_r), math.cos(armc_r) * math.cos(eps_r)) * RAD2DEG % 360.0


def _mc_above_horizon(mc: float, obliquity: float, lat: float) -> float:
    """
    At extreme latitudes, the standard MC (HA=0 point) may be below the horizon.
    Swiss Ephemeris swaps MC↔IC for quadrant-based systems that require the MC
    to be geometrically accessible (Campanus, Regiomontanus, etc.).

    Porphyry and simple systems keep the traditional HA=0 MC regardless.
    """
    eps_r = obliquity * DEG2RAD
    dec = math.degrees(math.asin(
        max(-1.0, min(1.0, math.sin(eps_r) * math.sin(mc * DEG2RAD)))
    ))
    sin_alt = (math.sin(lat * DEG2RAD) * math.sin(dec * DEG2RAD)
               + math.cos(lat * DEG2RAD) * math.cos(dec * DEG2RAD))
    return (mc + 180.0) % 360.0 if sin_alt < 0.0 else mc


def _asc_from_armc(armc: float, obliquity: float, lat: float) -> float:
    """
    Ascendant from ARMC, obliquity, and geographic latitude.

    atan2 yields two candidate solutions 180° apart; the Ascendant is the
    one whose ecliptic longitude falls in the same 180° semicircle as
    ARMC + 90° (the approximate RA of the eastern horizon).
    """
    armc_r = armc * DEG2RAD
    eps_r  = obliquity * DEG2RAD
    lat_r  = lat * DEG2RAD

    y   = -math.cos(armc_r)
    x   =  math.sin(armc_r) * math.cos(eps_r) + math.tan(lat_r) * math.sin(eps_r)
    raw = math.atan2(y, x) * RAD2DEG % 360.0

    # Pick the candidate closest to the eastern horizon direction (ARMC + 90°)
    expected = (armc + 90.0) % 360.0
    alt      = (raw + 180.0) % 360.0

    def _adist(a: float, b: float) -> float:
        d = abs(a - b) % 360.0
        return d if d <= 180.0 else 360.0 - d

    return alt if _adist(alt, expected) < _adist(raw, expected) else raw


# ---------------------------------------------------------------------------
# Helper: ecliptic to equatorial
# ---------------------------------------------------------------------------

def _ecl_to_eq(lon: float, lat: float, obliquity: float) -> tuple[float, float]:
    """Ecliptic → equatorial (RA, Dec) in degrees."""
    eps = obliquity * DEG2RAD
    l   = lon * DEG2RAD
    b   = lat * DEG2RAD
    sin_dec = math.sin(b)*math.cos(eps) + math.cos(b)*math.sin(eps)*math.sin(l)
    dec = math.asin(max(-1.0, min(1.0, sin_dec))) * RAD2DEG
    y = math.sin(l)*math.cos(eps) - math.tan(b)*math.sin(eps)
    x = math.cos(l)
    ra = math.atan2(y, x) * RAD2DEG % 360.0
    return ra, dec


# ---------------------------------------------------------------------------
# Whole Sign
# ---------------------------------------------------------------------------

def _whole_sign(asc: float) -> list[float]:
    sign_start = int(asc / 30.0) * 30.0
    return [(sign_start + i * 30.0) % 360.0 for i in range(12)]


# ---------------------------------------------------------------------------
# Equal House
# ---------------------------------------------------------------------------

def _equal_house(asc: float) -> list[float]:
    return [(asc + i * 30.0) % 360.0 for i in range(12)]


# ---------------------------------------------------------------------------
# Porphyry
# ---------------------------------------------------------------------------

def _porphyry(asc: float, mc: float) -> list[float]:
    """
    Porphyry houses: trisect each of the four unequal quadrants.

    Quadrant order (counterclockwise, increasing ecliptic longitude):
      Q1: ASC → IC   → houses 2, 3
      Q2: IC  → DSC  → houses 5, 6
      Q3: DSC → MC   → houses 8, 9
      Q4: MC  → ASC  → houses 11, 12

    Cardinal cusps: H1=ASC, H4=IC=MC+180°, H7=DSC=ASC+180°, H10=MC.
    """
    ic  = (mc  + 180.0) % 360.0
    dsc = (asc + 180.0) % 360.0

    cusps = [0.0] * 12
    cusps[0] = asc   # H1
    cusps[3] = ic    # H4
    cusps[6] = dsc   # H7
    cusps[9] = mc    # H10

    def _trisect(start: float, end: float) -> tuple[float, float]:
        span = (end - start) % 360.0
        return (start + span / 3.0) % 360.0, (start + 2.0 * span / 3.0) % 360.0

    cusps[1],  cusps[2]  = _trisect(asc, ic)   # H2, H3
    cusps[4],  cusps[5]  = _trisect(ic,  dsc)  # H5, H6
    cusps[7],  cusps[8]  = _trisect(dsc, mc)   # H8, H9
    cusps[10], cusps[11] = _trisect(mc,  asc)  # H11, H12

    return cusps


# ---------------------------------------------------------------------------
# Placidus (iterative)
# ---------------------------------------------------------------------------

def _placidus(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    Placidus house cusps via self-referential semi-arc iteration.

    Each intermediate cusp λ satisfies a condition on its own DSA or NSA:
      H11: RA(λ) = ARMC + (1/3) * DSA(λ)
      H12: RA(λ) = ARMC + (2/3) * DSA(λ)
      H3:  RA(λ) = IC_RA - (1/3) * NSA(λ)   (IC_RA = ARMC + 180°)
      H2:  RA(λ) = IC_RA - (2/3) * NSA(λ)

    Converges in < 10 iterations for all latitudes |φ| < 66°.
    """
    eps    = obliquity * DEG2RAD
    phi    = lat       * DEG2RAD
    armc_r = armc      * DEG2RAD
    ic_r   = armc_r    + math.pi

    mc  = _mc_from_armc(armc, obliquity, lat)
    asc = _asc_from_armc(armc, obliquity, lat)

    def _ra_to_lam(ra: float) -> float:
        """RA (radians) → ecliptic longitude (radians) on the ecliptic (β = 0)."""
        return math.atan2(math.sin(ra), math.cos(eps) * math.cos(ra))

    def _upper(frac: float) -> float:
        """H11/H12: RA = ARMC + frac * DSA(λ). Iterate to convergence."""
        ra = armc_r + frac * (math.pi / 2)          # initial guess (DSA ≈ 90°)
        for _ in range(50):
            lam     = _ra_to_lam(ra)
            sin_dec = max(-1.0, min(1.0, math.sin(eps) * math.sin(lam)))
            dec     = math.asin(sin_dec)
            cos_dsa = max(-1.0, min(1.0, -math.tan(phi) * math.tan(dec)))
            dsa     = math.acos(cos_dsa)
            new_ra  = armc_r + frac * dsa
            if abs(new_ra - ra) < 1e-12:
                break
            ra = new_ra
        return math.degrees(_ra_to_lam(ra)) % 360.0

    def _lower(frac: float) -> float:
        """H2/H3: RA = IC_RA - frac * NSA(λ). Iterate to convergence."""
        ra = ic_r - frac * (math.pi / 2)            # initial guess (NSA ≈ 90°)
        for _ in range(50):
            lam     = _ra_to_lam(ra)
            sin_dec = max(-1.0, min(1.0, math.sin(eps) * math.sin(lam)))
            dec     = math.asin(sin_dec)
            cos_dsa = max(-1.0, min(1.0, -math.tan(phi) * math.tan(dec)))
            dsa     = math.acos(cos_dsa)
            nsa     = math.pi - dsa
            new_ra  = ic_r - frac * nsa
            if abs(new_ra - ra) < 1e-12:
                break
            ra = new_ra
        return math.degrees(_ra_to_lam(ra)) % 360.0

    cusps = [0.0] * 12
    cusps[0]  = asc
    cusps[3]  = (mc  + 180.0) % 360.0
    cusps[6]  = (asc + 180.0) % 360.0
    cusps[9]  = mc

    cusps[10] = _upper(1/3)    # H11: 1/3 DSA from MC toward ASC
    cusps[11] = _upper(2/3)    # H12: 2/3 DSA from MC toward ASC
    cusps[2]  = _lower(1/3)    # H3:  1/3 NSA from IC toward ASC
    cusps[1]  = _lower(2/3)    # H2:  2/3 NSA from IC toward ASC

    cusps[4]  = (cusps[10] + 180.0) % 360.0   # H5
    cusps[5]  = (cusps[11] + 180.0) % 360.0   # H6
    cusps[7]  = (cusps[1]  + 180.0) % 360.0   # H8
    cusps[8]  = (cusps[2]  + 180.0) % 360.0   # H9

    return cusps


# ---------------------------------------------------------------------------
# Koch
# ---------------------------------------------------------------------------

def _koch(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    Koch (Birthplace) house system.

    Each intermediate cusp is found by projecting an Oblique Ascension (OA)
    back to the ecliptic.  The OA values trisect the MC degree's semi-arcs:

      OA_MC  = ARMC - AD_MC            (OA of MC; AD = ascensional difference)
      OA_IC  = (ARMC+180°) + AD_MC     (OA of IC; AD_IC = -AD_MC by symmetry)
      DSA_MC = diurnal semi-arc of the MC degree (= NSA_IC by symmetry)

      H11 OA = OA_MC + DSA_MC / 3
      H12 OA = OA_MC + 2 * DSA_MC / 3
      H3  OA = OA_IC - DSA_MC / 3
      H2  OA = OA_IC - 2 * DSA_MC / 3

    Projection: tan(λ) = sin(OA) / (cos(OA)*cos(ε) - tan(φ)*sin(ε))

    Reference: Walter Koch (1971); Holden "The Elements of House Division".
    """
    eps = obliquity * DEG2RAD
    phi = lat       * DEG2RAD

    mc  = _mc_from_armc(armc, obliquity, lat)
    asc = _asc_from_armc(armc, obliquity, lat)

    # Declination and DSA of the MC degree
    mc_r       = mc * DEG2RAD
    sin_dec_mc = max(-1.0, min(1.0, math.sin(eps) * math.sin(mc_r)))
    dec_mc     = math.asin(sin_dec_mc)
    cos_dsa    = max(-1.0, min(1.0, -math.tan(phi) * math.tan(dec_mc)))
    dsa_deg    = math.degrees(math.acos(cos_dsa))

    # Ascensional difference of MC degree: AD = arcsin(tan(dec) * tan(φ))
    sin_ad = max(-1.0, min(1.0, math.tan(dec_mc) * math.tan(phi)))
    ad_mc  = math.degrees(math.asin(sin_ad))

    # Oblique Ascensions of MC and IC
    oa_mc = armc - ad_mc                   # OA(MC) = RA(MC) − AD_MC
    oa_ic = (armc + 180.0) + ad_mc        # OA(IC) = RA(IC) − AD_IC = (ARMC+180°) + AD_MC

    def _project(oa: float) -> float:
        """Oblique Ascension → ecliptic longitude at observer's latitude φ."""
        oa_r = oa * DEG2RAD
        y    = math.sin(oa_r)
        x    = math.cos(oa_r) * math.cos(eps) - math.tan(phi) * math.sin(eps)
        return math.atan2(y, x) * RAD2DEG % 360.0

    cusps = [0.0] * 12
    cusps[0] = asc
    cusps[9] = mc
    cusps[3] = (mc  + 180.0) % 360.0
    cusps[6] = (asc + 180.0) % 360.0

    cusps[10] = _project(oa_mc + dsa_deg / 3.0)          # H11
    cusps[11] = _project(oa_mc + 2.0 * dsa_deg / 3.0)    # H12
    cusps[2]  = _project(oa_ic - dsa_deg / 3.0)           # H3
    cusps[1]  = _project(oa_ic - 2.0 * dsa_deg / 3.0)    # H2

    cusps[4] = (cusps[10] + 180.0) % 360.0
    cusps[5] = (cusps[11] + 180.0) % 360.0
    cusps[7] = (cusps[1]  + 180.0) % 360.0
    cusps[8] = (cusps[2]  + 180.0) % 360.0
    return cusps


# ---------------------------------------------------------------------------
# Alcabitius
# ---------------------------------------------------------------------------

def _alcabitius(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    Alcabitius (Semi-Arc) House System.

    Divides the diurnal and nocturnal semi-arcs of the Ascendant degree into thirds.
    Projection uses pole height = 0 (along declination circles), identical to the
    Morinus/Meridian projection.

    RA values (th = ARMC, sda = diurnal semi-arc, sna = 180 − sda):
      H11: th + sda/3          H12: th + 2·sda/3
      H2:  th + 180 − 2·sna/3  H3:  th + 180 − sna/3

    Reference: Swiss Ephemeris swehouse.c (Astrodienst), Alcabitius block.
    """
    eps    = obliquity * DEG2RAD
    phi    = lat       * DEG2RAD
    armc_r = armc      * DEG2RAD

    mc  = _mc_from_armc(armc, obliquity, lat)
    asc = _asc_from_armc(armc, obliquity, lat)

    # Declination of the Ascendant degree
    sin_dek = max(-1.0, min(1.0, math.sin(asc * DEG2RAD) * math.sin(eps)))
    dek_r   = math.asin(sin_dek)

    # Diurnal semi-arc of Ascendant (measured on equator)
    r   = max(-1.0, min(1.0, -math.tan(phi) * math.tan(dek_r)))
    sda = math.acos(r)          # radians
    sna = math.pi - sda

    def _project(ra_r: float) -> float:
        """RA (radians) → ecliptic longitude, pole height = 0."""
        return math.atan2(math.sin(ra_r), math.cos(eps) * math.cos(ra_r)) * RAD2DEG % 360.0

    cusps = [0.0] * 12
    cusps[0]  = asc
    cusps[9]  = mc
    cusps[3]  = (mc  + 180.0) % 360.0
    cusps[6]  = (asc + 180.0) % 360.0

    cusps[10] = _project(armc_r + sda / 3.0)              # H11
    cusps[11] = _project(armc_r + 2.0 * sda / 3.0)        # H12
    cusps[1]  = _project(armc_r + math.pi - 2.0 * sna / 3.0)  # H2
    cusps[2]  = _project(armc_r + math.pi - sna / 3.0)    # H3

    cusps[4]  = (cusps[10] + 180.0) % 360.0   # H5
    cusps[5]  = (cusps[11] + 180.0) % 360.0   # H6
    cusps[7]  = (cusps[1]  + 180.0) % 360.0   # H8
    cusps[8]  = (cusps[2]  + 180.0) % 360.0   # H9

    return cusps


# ---------------------------------------------------------------------------
# Morinus
# ---------------------------------------------------------------------------

def _morinus(armc: float, obliquity: float) -> list[float]:
    """
    Morinus House System.
    Equal 30° divisions of the equator projected onto the ecliptic, starting
    from the East point (ARMC + 90°).

    The Morinus position formula maps ecliptic longitude λ → "Morinus RA":
        tan(m) = tan(λ) / cos(ε)
    The inverse (Morinus RA → ecliptic longitude for cusp computation) is:
        tan(λ) = tan(m) × cos(ε)  →  λ = atan(tan(m) × cos(ε))
    with the quadrant correction: add 180° when m ∈ (90°, 270°].

    NOTE: this differs from the Meridian (Axial Rotation) projection which
    uses atan2(sin(RA), cos(RA)×cos(ε)) — a genuinely different mapping.

    Reference: Swiss Ephemeris swehouse.c, swe_house_pos() Morinus case.
    """
    cose = math.cos(obliquity * DEG2RAD)
    _EPS = 1e-10
    cusps = [0.0] * 12

    for i in range(12):
        ra = (armc + 90.0 + i * 30.0) % 360.0
        if abs(ra - 90.0) < _EPS:
            lon = 90.0
        elif abs(ra - 270.0) < _EPS:
            lon = 270.0
        else:
            ra_r = ra * DEG2RAD
            lon = math.degrees(math.atan(math.tan(ra_r) * cose))
            if 90.0 < ra <= 270.0:
                lon += 180.0
        cusps[i] = lon % 360.0

    return cusps


# ---------------------------------------------------------------------------
# Campanus
# ---------------------------------------------------------------------------

def _campanus(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    Campanus houses: prime vertical trisection projected onto the ecliptic.

    Direct translation of Swiss Ephemeris swehouse.c (Astrodienst).

    Step 1 — Auxiliary pole heights (prime vertical arcs 30° and 60°):
      fh1 = arcsin(sin(φ) * sin(30°)) = arcsin(sin(φ) / 2)
      fh2 = arcsin(sin(φ) * sin(60°)) = arcsin(sin(φ) * √3/2)

    Step 2 — Equatorial arc offsets:
      xh1 = arctan(√3 / cos(φ))
      xh2 = arctan(1 / (√3 * cos(φ)))

    Step 3 — Intermediate cusps via Asc1/Asc2 quadrant-aware projection:
      cusp[11] = Asc1(ARMC + 90 − xh1, fh1)
      cusp[12] = Asc1(ARMC + 90 − xh2, fh2)
      cusp[2]  = Asc1(ARMC + 90 + xh2, fh2)
      cusp[3]  = Asc1(ARMC + 90 + xh1, fh1)

    Reference: github.com/aloistr/swisseph/blob/master/swehouse.c
    """
    sine = math.sin(obliquity * DEG2RAD)
    cose = math.cos(obliquity * DEG2RAD)

    mc  = _mc_above_horizon(_mc_from_armc(armc, obliquity, lat), obliquity, lat)
    asc = _asc_from_armc(armc, obliquity, lat)

    _EPS = 1e-10

    def _asc2(x: float, f: float) -> float:
        """Core ecliptic projection; x and f both in degrees. Returns [0°,180°)."""
        sinx = math.sin(x * DEG2RAD)
        ass  = -math.tan(f * DEG2RAD) * sine + cose * math.cos(x * DEG2RAD)
        if abs(ass) < _EPS:
            return -90.0 if sinx < 0.0 else 90.0
        result = math.degrees(math.atan(sinx / ass))
        if result < 0.0:
            result += 180.0
        return result

    def _asc1(x1: float, f: float) -> float:
        """Quadrant dispatcher; x1 in degrees; returns ecliptic longitude [0°,360°)."""
        if abs(90.0 - f) < _EPS:
            return 180.0
        if abs(90.0 + f) < _EPS:
            return 0.0
        x1 = x1 % 360.0
        n  = int(x1 / 90.0) + 1
        if   n == 1:
            result =         _asc2(x1,          f)
        elif n == 2:
            result = 180.0 - _asc2(180.0 - x1, -f)
        elif n == 3:
            result = 180.0 + _asc2(x1 - 180.0, -f)
        else:
            result = 360.0 - _asc2(360.0 - x1,  f)
        return result % 360.0

    # Auxiliary pole heights
    fh1 = math.degrees(math.asin(max(-1.0, min(1.0, math.sin(lat * DEG2RAD) / 2.0))))
    fh2 = math.degrees(math.asin(max(-1.0, min(1.0, math.sin(lat * DEG2RAD) * math.sqrt(3.0) / 2.0))))

    # Equatorial arc offsets
    cosfi = math.cos(lat * DEG2RAD)
    if abs(cosfi) < _EPS:
        xh1 = xh2 = 90.0 if lat > 0.0 else 270.0
    else:
        xh1 = math.degrees(math.atan(math.sqrt(3.0) / cosfi))
        xh2 = math.degrees(math.atan(1.0 / (math.sqrt(3.0) * cosfi)))

    # Detect if _mc_above_horizon swapped MC (polar correction)
    mc_raw    = _mc_from_armc(armc, obliquity, lat)
    mc_swapped = abs((mc - mc_raw + 180.0) % 360.0 - 180.0) > 90.0

    # Intermediate cusps
    th = armc  # ARMC in degrees
    cusps = [0.0] * 12
    cusps[0]  = asc
    cusps[9]  = mc
    cusps[10] = _asc1(th + 90.0 - xh1, fh1)   # H11
    cusps[11] = _asc1(th + 90.0 - xh2, fh2)   # H12
    cusps[1]  = _asc1(th + 90.0 + xh2, fh2)   # H2
    cusps[2]  = _asc1(th + 90.0 + xh1, fh1)   # H3
    cusps[3]  = (mc  + 180.0) % 360.0
    cusps[6]  = (asc + 180.0) % 360.0
    cusps[4]  = (cusps[10] + 180.0) % 360.0
    cusps[5]  = (cusps[11] + 180.0) % 360.0
    cusps[7]  = (cusps[1]  + 180.0) % 360.0
    cusps[8]  = (cusps[2]  + 180.0) % 360.0

    # When MC was swapped at polar latitudes, all intermediate cusps are 180° off
    if mc_swapped:
        for i in (1, 2, 4, 5, 7, 8, 10, 11):
            cusps[i] = (cusps[i] + 180.0) % 360.0

    return cusps


# ---------------------------------------------------------------------------
# Regiomontanus
# ---------------------------------------------------------------------------

def _regiomontanus(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    Regiomontanus: trisect the celestial equator from MC to IC (eastward).

    Equatorial RA positions going counterclockwise from MC:
      H11: ARMC + 30°    H12: ARMC + 60°
      H2:  ARMC + 120°   H3:  ARMC + 150°   (NOT negative offsets)

    Polar height at each position:
      phi_h = atan(tan(φ) × sin(n × 30°))
      H11/H3 share phi_h at n=1 (sin 30°), H12/H2 at n=2 (sin 60°).

    Projection: tan(λ) = sin(RA) / (cos(RA)*cos(ε) − tan(phi_h)*sin(ε))
    """
    eps = obliquity * DEG2RAD
    phi = lat       * DEG2RAD

    mc  = _mc_above_horizon(_mc_from_armc(armc, obliquity, lat), obliquity, lat)
    asc = _asc_from_armc(armc, obliquity, lat)

    def _cusp(ra_deg: float, phi_h: float) -> float:
        ra_r = ra_deg * DEG2RAD
        y    = math.sin(ra_r)
        x    = math.cos(ra_r) * math.cos(eps) - math.tan(phi_h) * math.sin(eps)
        return math.atan2(y, x) * RAD2DEG % 360.0

    phi_h1 = math.atan(math.tan(phi) * math.sin(30.0 * DEG2RAD))  # H11 & H3
    phi_h2 = math.atan(math.tan(phi) * math.sin(60.0 * DEG2RAD))  # H12 & H2

    cusps = [0.0] * 12
    cusps[0]  = asc
    cusps[9]  = mc
    cusps[3]  = (mc  + 180.0) % 360.0
    cusps[6]  = (asc + 180.0) % 360.0

    cusps[10] = _cusp(armc + 30.0,  phi_h1)   # H11
    cusps[11] = _cusp(armc + 60.0,  phi_h2)   # H12
    cusps[1]  = _cusp(armc + 120.0, phi_h2)   # H2
    cusps[2]  = _cusp(armc + 150.0, phi_h1)   # H3

    cusps[4]  = (cusps[10] + 180.0) % 360.0
    cusps[5]  = (cusps[11] + 180.0) % 360.0
    cusps[7]  = (cusps[1]  + 180.0) % 360.0
    cusps[8]  = (cusps[2]  + 180.0) % 360.0

    # When MC was swapped at polar latitudes, all intermediate cusps are 180° off
    mc_raw = _mc_from_armc(armc, obliquity, lat)
    mc_swapped = abs((mc - mc_raw + 180.0) % 360.0 - 180.0) > 90.0
    if mc_swapped:
        for i in (1, 2, 4, 5, 7, 8, 10, 11):
            cusps[i] = (cusps[i] + 180.0) % 360.0

    return cusps


# ---------------------------------------------------------------------------
# Meridian (Axial Rotation)
# ---------------------------------------------------------------------------

def _meridian(armc: float, obliquity: float) -> list[float]:
    """Meridian system: equal 30° divisions of the celestial equator from MC."""
    eps = obliquity * DEG2RAD
    cusps = [0.0] * 12

    for i in range(12):
        ra_r = (armc + i * 30.0) * DEG2RAD
        lon = math.atan2(math.sin(ra_r), math.cos(ra_r) * math.cos(eps)) * RAD2DEG % 360.0
        cusps[i] = lon

    # Align H10 with MC (index 9)
    # Cusp[0] in 'cusps' is at ARMC (the MC). 
    # We need to shift it so House 10 is the MC.
    # ARMC is the start. House 10 = index 0. House 11 = index 1.
    # So H1 is index 3 (90 degrees later).
    rotated = [0.0] * 12
    for i in range(12):
        # Index i -> House (i + 10) % 12
        rotated[(i + 9) % 12] = cusps[i]
    return rotated


# ---------------------------------------------------------------------------
# Vehlow Equal Houses
# ---------------------------------------------------------------------------

def _vehlow(asc: float) -> list[float]:
    """
    Vehlow Equal Houses.
    Same as equal houses but the Ascendant falls at the MIDDLE of the 1st house,
    not the cusp.  All cusps shift back by 15°.

    Formula: cusp_1 = (ASC − 15°) mod 360°, then +30° each house.
    """
    start = (asc - 15.0) % 360.0
    return [(start + i * 30.0) % 360.0 for i in range(12)]


# ---------------------------------------------------------------------------
# Sunshine Houses (Makransky)
# ---------------------------------------------------------------------------

def _sunshine(sun_lon: float, lat: float, obliquity: float) -> list[float]:
    """
    Sunshine house system (Robert Makransky, 1988).
    Uses the Sun's position instead of the Ascendant as the basis.
    The Sun is always placed at the cusp of the 12th house.

    Formula: cusp_12 = Sun longitude, then +30° each house proceeding
    through 12, 1, 2, ..., 11.
    (House 12 = Sun, house 1 = Sun+30°, ..., house 11 = Sun+330°)
    """
    cusps = [0.0] * 12
    cusps[11] = sun_lon % 360.0   # 12th house cusp = Sun
    for i in range(11):
        cusps[i] = (sun_lon + (i + 1) * 30.0) % 360.0
    return cusps


# ---------------------------------------------------------------------------
# Azimuthal (Horizontal) Houses
# ---------------------------------------------------------------------------

def _azimuthal(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    Horizontal / Azimuthal house system (Swiss Ephemeris 'H').

    Similar to Campanus but uses the Zenith-Nadir axis as the primary axis
    instead of the prime vertical.  Technically: great circles through the
    Zenith divide the sphere into 12 equal 30° sectors; cusps are where those
    circles intersect the ecliptic.

    Implementation: same Asc1/Asc2 machinery as Campanus, with coordinates
    transformed so the Zenith replaces the Celestial Pole:
        fi  = 90° − lat   (complement of geographic latitude)
        th  = ARMC + 180° (ARMC rotated 180°)

    Reference: Swiss Ephemeris swehouse.c case 'H' (Astrodienst).
    """
    sine = math.sin(obliquity * DEG2RAD)
    cose = math.cos(obliquity * DEG2RAD)

    mc  = _mc_from_armc(armc, obliquity, lat)
    asc_standard = _asc_from_armc(armc, obliquity, lat)

    # Coordinate transformation
    fi = (90.0 - lat) if lat > 0.0 else (-90.0 - lat)
    _EPS = 1e-10
    # Clamp fi away from exactly ±90°
    if abs(abs(fi) - 90.0) < _EPS:
        fi = math.copysign(90.0 - _EPS, fi)
    th = (armc + 180.0) % 360.0

    def _asc2(x: float, f: float) -> float:
        sinx = math.sin(x * DEG2RAD)
        ass  = -math.tan(f * DEG2RAD) * sine + cose * math.cos(x * DEG2RAD)
        if abs(ass) < _EPS:
            return -90.0 if sinx < 0.0 else 90.0
        result = math.degrees(math.atan(sinx / ass))
        if result < 0.0:
            result += 180.0
        return result

    def _asc1(x1: float, f: float) -> float:
        if abs(90.0 - f) < _EPS:  return 180.0
        if abs(90.0 + f) < _EPS:  return 0.0
        x1 = x1 % 360.0
        n  = int(x1 / 90.0) + 1
        if   n == 1: result =         _asc2(x1,          f)
        elif n == 2: result = 180.0 - _asc2(180.0 - x1, -f)
        elif n == 3: result = 180.0 + _asc2(x1 - 180.0, -f)
        else:        result = 360.0 - _asc2(360.0 - x1,  f)
        return result % 360.0

    fh1 = math.degrees(math.asin(max(-1.0, min(1.0, math.sin(fi * DEG2RAD) / 2.0))))
    fh2 = math.degrees(math.asin(max(-1.0, min(1.0, math.sin(fi * DEG2RAD) * math.sqrt(3.0) / 2.0))))
    cosfi = math.cos(fi * DEG2RAD)
    if abs(cosfi) < _EPS:
        # In the transformed equatorial singularity (fi = -90° for lat = 0°),
        # Swiss orients the azimuthal sectors using the 90° branch rather than
        # the southern 270° branch. That keeps house numbering consistent.
        xh1 = xh2 = 90.0
    else:
        xh1 = math.degrees(math.atan(math.sqrt(3.0) / cosfi))
        xh2 = math.degrees(math.atan(1.0 / (math.sqrt(3.0) * cosfi)))

    asc = (_asc1(th + 90.0, fi) + 180.0) % 360.0

    cusps = [0.0] * 12
    cusps[0]  = asc
    cusps[9]  = mc
    cusps[3]  = (mc  + 180.0) % 360.0
    cusps[6]  = (asc + 180.0) % 360.0
    cusps[10] = (_asc1(th + 90.0 - xh1, fh1) + 180.0) % 360.0   # H11
    cusps[11] = (_asc1(th + 90.0 - xh2, fh2) + 180.0) % 360.0   # H12
    cusps[1]  = (_asc1(th + 90.0 + xh2, fh2) + 180.0) % 360.0   # H2
    cusps[2]  = (_asc1(th + 90.0 + xh1, fh1) + 180.0) % 360.0   # H3
    cusps[4]  = (cusps[10] + 180.0) % 360.0    # H5
    cusps[5]  = (cusps[11] + 180.0) % 360.0    # H6
    cusps[7]  = (cusps[1]  + 180.0) % 360.0    # H8
    cusps[8]  = (cusps[2]  + 180.0) % 360.0    # H9

    return cusps


# ---------------------------------------------------------------------------
# Carter Poly-Ptolemaic
# ---------------------------------------------------------------------------

def _carter(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    Carter Poli-Equatorial house system (SWE letter 'F').

    Divides the equator into 12 equal 30° segments starting from the RA of
    the Ascendant, then projects each back to the ecliptic using:
        cusp = atan(tan(RA) / cos(ε))
    with quadrant correction (add 180° when RA ∈ (90°, 270°]).

    This is the same projection as Morinus but anchored to RA(ASC) rather
    than ARMC + 90°.

    Reference: Swiss Ephemeris swehouse.c case 'F'.
    """
    cose  = math.cos(obliquity * DEG2RAD)
    mc    = _mc_from_armc(armc, obliquity, lat)
    asc   = _asc_from_armc(armc, obliquity, lat)

    # Polar correction: if ASC is on wrong side of MC, swap to DSC
    acmc = ((asc - mc + 180.0) % 360.0) - 180.0
    if acmc < 0.0:
        asc = (asc + 180.0) % 360.0

    # RA of Ascendant: ecliptic (lat=0) → equatorial
    asc_r  = asc * DEG2RAD
    eps_r  = obliquity * DEG2RAD
    ra_asc = math.atan2(math.sin(asc_r) * math.cos(eps_r), math.cos(asc_r)) * RAD2DEG % 360.0

    _EPS  = 1e-10
    cusps = [0.0] * 12
    cusps[0] = asc
    cusps[9] = mc
    cusps[3] = (mc  + 180.0) % 360.0
    cusps[6] = (asc + 180.0) % 360.0

    for i in range(2, 13):   # H2 … H12
        if i <= 3 or i >= 10:
            ra = (ra_asc + (i - 1) * 30.0) % 360.0
            if abs(ra - 90.0) <= _EPS:
                lon = 90.0
            elif abs(ra - 270.0) <= _EPS:
                lon = 270.0
            else:
                ra_r = ra * DEG2RAD
                lon  = math.degrees(math.atan(math.tan(ra_r) / cose))
                if 90.0 < ra <= 270.0:
                    lon += 180.0
            cusps[i - 1] = lon % 360.0

    cusps[4] = (cusps[10] + 180.0) % 360.0
    cusps[5] = (cusps[11] + 180.0) % 360.0
    cusps[7] = (cusps[1]  + 180.0) % 360.0
    cusps[8] = (cusps[2]  + 180.0) % 360.0
    return cusps


# ---------------------------------------------------------------------------
# Pullen Sinusoidal Delta
# ---------------------------------------------------------------------------

def _pullen_sd(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    Pullen Sinusoidal Delta house system (SWE letter 'L').

    Cusps are placed at offsets from MC and ASC based on the actual quadrant
    size. For a quadrant of arc q (MC→ASC in ecliptic degrees):
        d = (q − 90) / 4
        H11 = MC + 30 + d
        H12 = MC + 60 + 3d
    Symmetric formula applies for the ASC quadrant (q1 = 180 − q).
    Degenerate case: if q ≤ 30°, H11 = H12 = MC + q/2.

    Reference: Swiss Ephemeris swehouse.c case 'L'.
    """
    mc  = _mc_from_armc(armc, obliquity, lat)
    asc = _asc_from_armc(armc, obliquity, lat)

    acmc = ((asc - mc + 180.0) % 360.0) - 180.0   # swe_difdeg2n(asc, mc)
    if acmc < 0.0:
        asc  = (asc + 180.0) % 360.0
        acmc = ((asc - mc + 180.0) % 360.0) - 180.0

    q1 = 180.0 - acmc   # complementary quadrant (ASC → next MC)

    # Upper quadrant: MC → ASC
    d = (acmc - 90.0) / 4.0
    if acmc <= 30.0:
        h11 = h12 = (mc + acmc / 2.0) % 360.0
    else:
        h11 = (mc + 30.0 + d) % 360.0
        h12 = (mc + 60.0 + 3.0 * d) % 360.0

    # Lower quadrant: ASC → next MC
    d1 = (q1 - 90.0) / 4.0
    if q1 <= 30.0:
        h2 = h3 = (asc + q1 / 2.0) % 360.0
    else:
        h2 = (asc + 30.0 + d1) % 360.0
        h3 = (asc + 60.0 + 3.0 * d1) % 360.0

    cusps = [0.0] * 12
    cusps[0]  = asc;   cusps[9]  = mc
    cusps[3]  = (mc  + 180.0) % 360.0
    cusps[6]  = (asc + 180.0) % 360.0
    cusps[10] = h11;   cusps[11] = h12
    cusps[1]  = h2;    cusps[2]  = h3
    cusps[4]  = (h11 + 180.0) % 360.0
    cusps[5]  = (h12 + 180.0) % 360.0
    cusps[7]  = (h2  + 180.0) % 360.0
    cusps[8]  = (h3  + 180.0) % 360.0
    return cusps


# ---------------------------------------------------------------------------
# Pullen Sinusoidal Ratio
# ---------------------------------------------------------------------------

def _pullen_sr(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    Pullen Sinusoidal Ratio house system (SWE letter 'Q').

    Uses a ratio r derived from the quadrant size q via a cube-root formula:
        c  = (180 − q) / q
        r  = 0.5*√(2^(2/3)·∛(c²−c)+1) + 0.5*√(…) − 0.5
        x  = q / (2r + 1)
    When acmc > 90°: H11=MC+xr³, H12=H11+xr⁴, H2=ASC+xr,  H3=H2+x
    When acmc ≤ 90°: H11=MC+xr,  H12=H11+x,   H2=ASC+xr³, H3=H2+xr⁴

    Reference: Swiss Ephemeris swehouse.c case 'Q'.
    """
    mc  = _mc_from_armc(armc, obliquity, lat)
    asc = _asc_from_armc(armc, obliquity, lat)

    acmc = ((asc - mc + 180.0) % 360.0) - 180.0
    if acmc < 0.0:
        asc  = (asc + 180.0) % 360.0
        acmc = ((asc - mc + 180.0) % 360.0) - 180.0

    q     = acmc if acmc <= 90.0 else 180.0 - acmc
    third = 1.0 / 3.0
    two23 = 2.0 ** (2.0 * third)   # 2^(2/3)

    if q < 1e-30:
        x = xr = xr3 = 0.0
        xr4 = 180.0
    else:
        c   = (180.0 - q) / q
        ccr = (c * c - c) ** third               # ∛(c²−c) — always ≥ 0 for q ≤ 90
        cqx = math.sqrt(two23 * ccr + 1.0)
        r1  = 0.5 * cqx
        r2  = 0.5 * math.sqrt(max(0.0, -2.0 * (1.0 - 2.0 * c) / cqx - two23 * ccr + 2.0))
        r   = r1 + r2 - 0.5
        x   = q / (2.0 * r + 1.0)
        xr  = r * x
        xr3 = xr * r * r
        xr4 = xr3 * r

    if acmc > 90.0:
        h11 = (mc  + xr3) % 360.0
        h12 = (h11 + xr4) % 360.0
        h2  = (asc + xr)  % 360.0
        h3  = (h2  + x)   % 360.0
    else:
        h11 = (mc  + xr)  % 360.0
        h12 = (h11 + x)   % 360.0
        h2  = (asc + xr3) % 360.0
        h3  = (h2  + xr4) % 360.0

    cusps = [0.0] * 12
    cusps[0]  = asc;   cusps[9]  = mc
    cusps[3]  = (mc  + 180.0) % 360.0
    cusps[6]  = (asc + 180.0) % 360.0
    cusps[10] = h11;   cusps[11] = h12
    cusps[1]  = h2;    cusps[2]  = h3
    cusps[4]  = (h11 + 180.0) % 360.0
    cusps[5]  = (h12 + 180.0) % 360.0
    cusps[7]  = (h2  + 180.0) % 360.0
    cusps[8]  = (h3  + 180.0) % 360.0
    return cusps


# ---------------------------------------------------------------------------
# Topocentric (Polich-Page)
# ---------------------------------------------------------------------------

def _topocentric(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    Topocentric House System (Polich-Page).

    Divides the equatorial circle at 30°/60°/120°/150° from ARMC (like Regiomontanus)
    but applies a graduated polar height for each cusp:
      phi_n = atan(n/3 * tan(lat))
    where n = 1 for cusps closest to ASC/MC (11 & 3), n = 2 for cusps 12 & 2.

    The polar height is symmetric about the 90° (ASC) point:
      RA+30°  (H11) → phi_1   RA+60°  (H12) → phi_2
      RA+120° (H2)  → phi_2   RA+150° (H3)  → phi_1

    Reference: Polich & Page (1955); confirmed against Swiss Ephemeris.
    """
    eps = obliquity * DEG2RAD
    phi = lat       * DEG2RAD

    mc  = _mc_above_horizon(_mc_from_armc(armc, obliquity, lat), obliquity, lat)
    asc = _asc_from_armc(armc, obliquity, lat)

    phi_1 = math.atan(1.0/3.0 * math.tan(phi))
    phi_2 = math.atan(2.0/3.0 * math.tan(phi))

    def _project(ra_deg: float, phi_h: float) -> float:
        ra_r = ra_deg * DEG2RAD
        y = math.sin(ra_r)
        x = math.cos(ra_r) * math.cos(eps) - math.tan(phi_h) * math.sin(eps)
        return math.atan2(y, x) * RAD2DEG % 360.0

    cusps = [0.0] * 12
    cusps[0]  = asc
    cusps[9]  = mc
    cusps[10] = _project(armc + 30.0,  phi_1)   # H11: RA+30°,  pole = phi_1
    cusps[11] = _project(armc + 60.0,  phi_2)   # H12: RA+60°,  pole = phi_2
    cusps[1]  = _project(armc + 120.0, phi_2)   # H2:  RA+120°, pole = phi_2
    cusps[2]  = _project(armc + 150.0, phi_1)   # H3:  RA+150°, pole = phi_1

    # Opposition
    cusps[4] = (cusps[10] + 180.0) % 360.0
    cusps[5] = (cusps[11] + 180.0) % 360.0
    cusps[7] = (cusps[1]  + 180.0) % 360.0
    cusps[8] = (cusps[2]  + 180.0) % 360.0
    cusps[3] = (mc  + 180.0) % 360.0
    cusps[6] = (asc + 180.0) % 360.0

    # When MC was swapped at polar latitudes, all intermediate cusps are 180° off
    mc_raw = _mc_from_armc(armc, obliquity, lat)
    mc_swapped = abs((mc - mc_raw + 180.0) % 360.0 - 180.0) > 90.0
    if mc_swapped:
        for i in (1, 2, 4, 5, 7, 8, 10, 11):
            cusps[i] = (cusps[i] + 180.0) % 360.0

    return cusps


# ---------------------------------------------------------------------------
# Coordinate rotation helper (mirrors SWE swe_cotrans)
# ---------------------------------------------------------------------------

def _cotrans(lon: float, lat: float, eps: float) -> tuple[float, float]:
    """
    Rotate spherical coordinates by angle eps (degrees) around the x-axis.

    Mirrors SWE's swe_cotrans():
        lon_new = atan2(cos(e)*sin(lon)*cos(lat) − sin(e)*sin(lat), cos(lon)*cos(lat))
        lat_new = asin( sin(e)*cos(lat)*sin(lon) + cos(e)*sin(lat) )

    Used for ecliptic ↔ equatorial ↔ horizontal frame conversions.
    """
    e  = eps * DEG2RAD
    l  = lon * DEG2RAD
    b  = lat * DEG2RAD
    lon_new = math.atan2(
        math.cos(e) * math.sin(l) * math.cos(b) - math.sin(e) * math.sin(b),
        math.cos(l) * math.cos(b),
    ) * RAD2DEG % 360.0
    lat_new = math.asin(max(-1.0, min(1.0,
        math.sin(e) * math.cos(b) * math.sin(l) + math.cos(e) * math.sin(b),
    ))) * RAD2DEG
    return lon_new, lat_new


# ---------------------------------------------------------------------------
# Krusinski-Pisa (SWE 'U')
# ---------------------------------------------------------------------------

def _krusinski(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    Krusinski-Pisa house system (SWE letter 'U').

    Great circle through the Ascendant and Zenith is divided into 12 equal 30°
    segments; cusps are where meridian circles through those points cut the ecliptic.

    Algorithm (Bogdan Krusinski, 2006):
      Forward: ASC (ecl) → equatorial → rotate by -(ARMC−90°) → horizontal
               → save krHorizonLon → rotate to 0 → house circle
      Backward for each house i (0..5):
               (30i°, 0°) on house circle → horizontal → +krHorizonLon
               → equatorial → +ARMC−90° → RA → ecliptic longitude

    Reference: Swiss Ephemeris swehouse.c case 'U'.
    """
    mc  = _mc_from_armc(armc, obliquity, lat)
    asc = _asc_from_armc(armc, obliquity, lat)

    acmc = ((asc - mc + 180.0) % 360.0) - 180.0
    if acmc < 0.0:
        asc = (asc + 180.0) % 360.0

    ekl = obliquity
    fi  = lat
    th  = armc

    # A1: ecliptic → equatorial
    x0, x1 = _cotrans(asc, 0.0, -ekl)
    # A2: rotate by -(th − 90)
    x0 = (x0 - (th - 90.0)) % 360.0
    # A3: equatorial → horizontal
    x0, x1 = _cotrans(x0, x1, -(90.0 - fi))
    kr_horizon_lon = x0

    cose  = math.cos(ekl * DEG2RAD)
    _EPS  = 1e-10
    cusps = [0.0] * 12

    for i in range(6):
        bx0, bx1 = float(30 * i), 0.0
        # B1: house circle → horizontal
        bx0, bx1 = _cotrans(bx0, bx1, 90.0)
        # B2: rotate back
        bx0 = (bx0 + kr_horizon_lon) % 360.0
        # B3: horizontal → equatorial
        bx0, bx1 = _cotrans(bx0, bx1, 90.0 - fi)
        # B4: rotate back → RA of cusp
        bx0 = (bx0 + (th - 90.0)) % 360.0
        # B5: RA → ecliptic longitude (Morinus-style projection)
        if abs(bx0 - 90.0) <= _EPS:
            lon = 90.0
        elif abs(bx0 - 270.0) <= _EPS:
            lon = 270.0
        else:
            bx0_r = bx0 * DEG2RAD
            lon = math.degrees(math.atan(math.tan(bx0_r) / cose))
            if 90.0 < bx0 <= 270.0:
                lon += 180.0
        cusps[i]     = lon % 360.0
        cusps[i + 6] = (lon + 180.0) % 360.0

    return cusps


# ---------------------------------------------------------------------------
# APC Houses (SWE 'Y')
# ---------------------------------------------------------------------------

def _apc_sector(n: int, ph: float, e: float, az: float) -> float:
    """
    Single APC house cusp (translation of SWE's apc_sector()).

    Parameters: n = house number 1–12, ph = lat (rad), e = obliquity (rad),
    az = ARMC (rad).
    """
    _VS = 1e-6   # VERY_SMALL in SWE
    ph_deg = abs(ph * RAD2DEG)

    if ph_deg > 90.0 - _VS:
        kv = dasc = 0.0
    else:
        kv = math.atan(math.tan(ph) * math.tan(e) * math.cos(az)
                       / (1.0 + math.tan(ph) * math.tan(e) * math.sin(az)))
        if ph_deg < _VS:
            dasc = (90.0 - _VS) * DEG2RAD
            if ph < 0.0:
                dasc = -dasc
        else:
            dasc = math.atan(math.sin(kv) / math.tan(ph))

    if n < 8:
        k = n - 1
        a = kv + az + math.pi / 2.0 + k * (math.pi / 2.0 - kv) / 3.0
    else:
        k = n - 13
        a = kv + az + math.pi / 2.0 + k * (math.pi / 2.0 + kv) / 3.0

    a %= (2.0 * math.pi)

    dret = math.atan2(
        math.tan(dasc) * math.tan(ph) * math.sin(az) + math.sin(a),
        math.cos(e) * (math.tan(dasc) * math.tan(ph) * math.cos(az) + math.cos(a))
        + math.sin(e) * math.tan(ph) * math.sin(az - a),
    )
    return dret * RAD2DEG % 360.0


def _apc(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    APC house system (SWE letter 'Y').

    Reference: Swiss Ephemeris swehouse.c case 'Y', apc_sector().
    """
    mc  = _mc_from_armc(armc, obliquity, lat)
    asc = _asc_from_armc(armc, obliquity, lat)

    ph = lat       * DEG2RAD
    e  = obliquity * DEG2RAD
    az = armc      * DEG2RAD

    cusps = [_apc_sector(i, ph, e, az) for i in range(1, 13)]

    # SWE overrides H10 with standard MC and H4 with IC
    cusps[9] = mc
    cusps[3] = (mc + 180.0) % 360.0

    # Polar correction. When the APC cusp set lands in the opposite hemisphere
    # from the standard ascendant, Swiss rotates the full figure by 180°.
    ac_diff = abs(((cusps[0] - asc + 180.0) % 360.0) - 180.0)
    if abs(lat) >= 90.0 - obliquity and ac_diff > 90.0:
        cusps = [(c + 180.0) % 360.0 for c in cusps]

    return cusps


# ---------------------------------------------------------------------------
# Main public function
# ---------------------------------------------------------------------------

def calculate_houses(
    jd_ut:     float,
    latitude:  float,
    longitude: float,
    system:    str = HouseSystem.PLACIDUS,
    *,
    policy:          HousePolicy | None = None,
    ayanamsa_offset: float | None = None,
) -> HouseCusps:
    """
    Calculate house cusps for a given Universal Time and observer location.

    CORE COMPUTATION:
        Derives ARMC and obliquity from the Julian date, selects the appropriate
        house algorithm, computes all twelve cusp longitudes, and returns a
        populated HouseCusps vessel.

    SYSTEM DOCTRINE:
        The `system` argument is the *requested* system. It is always preserved
        unchanged in HouseCusps.system. The *effective* system — the one whose
        algorithm actually produced the cusps — is stored in
        HouseCusps.effective_system.

    FALLBACK BEHAVIOUR:
        Two conditions can redirect computation away from the requested system.
        What happens in each case is governed by the `policy` argument:

                1. Polar latitude:
                     When |latitude| >= 90° − obliquity, the systems PLACIDUS, KOCH,
                     and PULLEN_SD are not supported by default.
           - Default policy (PolarFallbackPolicy.FALLBACK_TO_PORPHYRY): silently
             substitute Porphyry; record in HouseCusps.fallback / fallback_reason.
           - Strict policy (PolarFallbackPolicy.RAISE): raise ValueError.
                     - Experimental policy (PolarFallbackPolicy.EXPERIMENTAL_SEARCH): for
                         Placidus only, attempt a branch-aware high-latitude solve and use
                         it only when exactly one ordered cusp cycle exists.

        2. Unknown system code:
           If `system` is not a recognised HouseSystem constant:
           - Default policy (UnknownSystemPolicy.FALLBACK_TO_PLACIDUS): silently
             substitute Placidus; record in HouseCusps.fallback / fallback_reason.
           - Strict policy (UnknownSystemPolicy.RAISE): raise ValueError.

        In all normal cases (known system, non-polar latitude) fallback is False
        and fallback_reason is None.

    POLICY:
        `policy` defaults to HousePolicy.default(), which exactly replicates
        all behavior from prior phases.  Pass HousePolicy.strict() or a custom
        HousePolicy to change fallback doctrine.  The active policy is preserved
        in HouseCusps.policy so it is always recoverable from the result.

    FUTURE LAYERS:
        This function intentionally does not:
            - classify cusps by angularity or strength
            - analyse planet-in-house membership
            - compare systems or select among them by doctrine
            - perform any cusp-zone or boundary-sensitivity analysis
        Those capabilities belong in dedicated layers above this function.

    Args:
        jd_ut: Julian date in Universal Time (UT1).
        latitude: Geographic latitude of the observer in decimal degrees,
            positive north, range [-90, 90].
        longitude: Geographic longitude of the observer in decimal degrees,
            positive east, range [-180, 180].
        system: House system identifier; one of the HouseSystem constants.
            Defaults to HouseSystem.PLACIDUS.
        policy: HousePolicy governing fallback doctrine.  Keyword-only.
            Defaults to HousePolicy.default() (silent fallback, current behavior).

    Returns:
        A HouseCusps vessel containing the twelve cusp longitudes (degrees
        [0, 360)), ASC, MC, ARMC, Vertex, Anti-Vertex, the requested system,
        the effective system, the fallback flag, the fallback reason, the
        HouseSystemClassification of the effective system, and the active policy.

    Raises:
        ValueError: When policy requires strict behavior and a fallback condition
            is encountered (unknown system code or polar latitude for an incapable
            system).  Also propagated from subordinate engines if input values are
            outside computable ranges.

    Side effects:
        - Lazily imports moira.planets.sun_longitude when system is
          HouseSystem.SUNSHINE; no other import-time side effects.
    """
    active_policy = policy if policy is not None else HousePolicy.default()
    jd_tt    = ut_to_tt(jd_ut)
    obliquity = true_obliquity(jd_tt)
    dpsi, _ = nutation(jd_tt)
    
    armc    = _armc(jd_ut, longitude, jd_tt, dpsi, obliquity)
    mc      = _mc_from_armc(armc, obliquity, latitude)
    asc     = _asc_from_armc(armc, obliquity, latitude)

    # Vertex: western intersection of the prime vertical with the ecliptic.
    # Formula from Meeus §24: treat ARMC+90° as a new ARMC and negate latitude.
    vertex      = _asc_from_armc((armc + 90.0) % 360.0, obliquity, -latitude)
    anti_vertex = (vertex + 180.0) % 360.0

    # --- Fallback resolution: determine effective system and reason ----------
    #
    # Rule 1 — Critical latitude safety valve:
    #   The semi-arc and oblique-ascension systems (Placidus, Koch, Pullen SD)
    #   produce geometrically disordered cusps above the critical latitude
    #   90° − obliquity (≈ 66.56° at J2000).  At that latitude, the solar
    #   solstice declination equals the co-latitude, so some ecliptic degrees
    #   become circumpolar.  The underlying acos() domain error is silently
    #   clamped, but the resulting cusp sequence is astronomically invalid
    #   (houses swap, spans exceed 180°) for a significant fraction of ARMC
    #   values above that threshold.  We fall back to Porphyry, which uses
    #   only ecliptic trisection and remains valid at all latitudes.
    #   Behavior is governed by active_policy.polar_fallback.
    #
    # Rule 2 — Unknown system code:
    #   Any system code not in _KNOWN_SYSTEMS cannot be dispatched.
    #   Behavior is governed by active_policy.unknown_system.
    #
    critical_lat = 90.0 - obliquity
    polar = abs(latitude) >= critical_lat and system in _POLAR_SYSTEMS
    effective_system = system
    fallback = False
    fallback_reason: str | None = None
    experimental_cusps: list[float] | None = None

    if polar:
        if active_policy.polar_fallback == PolarFallbackPolicy.RAISE:
            raise ValueError(
                f"latitude |{latitude:.4f}°| >= critical latitude {critical_lat:.4f}° "
                f"(= 90° − obliquity {obliquity:.4f}°); "
                f"system {system!r} produces geometrically invalid cusps above this threshold "
                f"and policy is RAISE"
            )
        if active_policy.polar_fallback == PolarFallbackPolicy.EXPERIMENTAL_SEARCH:
            if system != HouseSystem.PLACIDUS:
                raise ValueError(
                    f"experimental polar search is only implemented for {HouseSystem.PLACIDUS!r}; "
                    f"got {system!r}"
                )
            experimental_cusps = _experimental_polar_placidus_cusps(
                armc,
                obliquity,
                latitude,
                asc,
                mc,
            )
        else:
            effective_system = HouseSystem.PORPHYRY
            fallback = True
            fallback_reason = (
                f"|lat| {abs(latitude):.4f}° >= critical latitude {critical_lat:.4f}° "
                f"(90° − obliquity); {system!r} produces invalid cusps above this threshold; "
                f"fell back to Porphyry"
            )
    elif system not in _KNOWN_SYSTEMS:
        if active_policy.unknown_system == UnknownSystemPolicy.RAISE:
            raise ValueError(
                f"unknown house system code {system!r} and policy is RAISE"
            )
        effective_system = HouseSystem.PLACIDUS
        fallback = True
        fallback_reason = (
            f"unknown system code {system!r}; fell back to Placidus"
        )

    # --- Cusp computation: dispatch to the effective system ------------------
    if experimental_cusps is not None:
        cusps = experimental_cusps
    elif effective_system == HouseSystem.WHOLE_SIGN:
        cusps = _whole_sign(asc)
    elif effective_system == HouseSystem.EQUAL:
        cusps = _equal_house(asc)
    elif effective_system == HouseSystem.PORPHYRY:
        cusps = _porphyry(asc, mc)
    elif effective_system == HouseSystem.PLACIDUS:
        cusps = _placidus(armc, obliquity, latitude)
    elif effective_system == HouseSystem.KOCH:
        cusps = _koch(armc, obliquity, latitude)
    elif effective_system == HouseSystem.CAMPANUS:
        cusps = _campanus(armc, obliquity, latitude)
    elif effective_system == HouseSystem.REGIOMONTANUS:
        cusps = _regiomontanus(armc, obliquity, latitude)
    elif effective_system == HouseSystem.ALCABITIUS:
        cusps = _alcabitius(armc, obliquity, latitude)
    elif effective_system == HouseSystem.MORINUS:
        cusps = _morinus(armc, obliquity)
    elif effective_system == HouseSystem.TOPOCENTRIC:
        cusps = _topocentric(armc, obliquity, latitude)
    elif effective_system == HouseSystem.MERIDIAN:
        cusps = _meridian(armc, obliquity)
    elif effective_system == HouseSystem.VEHLOW:
        cusps = _vehlow(asc)
    elif effective_system == HouseSystem.SUNSHINE:
        from .planets import sun_longitude
        sun_lon = sun_longitude(jd_ut)
        cusps = _sunshine(sun_lon, latitude, obliquity)
    elif effective_system == HouseSystem.AZIMUTHAL:
        cusps = _azimuthal(armc, obliquity, latitude)
    elif effective_system == HouseSystem.CARTER:
        cusps = _carter(armc, obliquity, latitude)
    elif effective_system == HouseSystem.PULLEN_SD:
        cusps = _pullen_sd(armc, obliquity, latitude)
    elif effective_system == HouseSystem.PULLEN_SR:
        cusps = _pullen_sr(armc, obliquity, latitude)
    elif effective_system == HouseSystem.KRUSINSKI:
        cusps = _krusinski(armc, obliquity, latitude)
    elif effective_system == HouseSystem.APC:
        cusps = _apc(armc, obliquity, latitude)
    else:
        cusps = _placidus(armc, obliquity, latitude)

    _shift = ayanamsa_offset if ayanamsa_offset is not None else 0.0
    return HouseCusps(
        system=system,
        cusps=[normalize_degrees(c - _shift) for c in cusps],
        asc=normalize_degrees(asc - _shift),
        mc=normalize_degrees(mc - _shift),
        armc=normalize_degrees(armc),
        vertex=normalize_degrees(vertex - _shift),
        anti_vertex=normalize_degrees(anti_vertex - _shift),
        effective_system=effective_system,
        fallback=fallback,
        fallback_reason=fallback_reason,
        classification=classify_house_system(effective_system),
        policy=active_policy,
    )


# ===========================================================================
# POINT-TO-HOUSE MEMBERSHIP LAYER  (Phase 5)
# ===========================================================================

_MEMBERSHIP_CUSP_TOLERANCE: float = 1e-9
"""
Tolerance (degrees) used by assign_house() to decide whether a point falls
exactly on a cusp.  Two longitudes separated by less than this value are
considered coincident for cusp-detection purposes.  This has no effect on
which house the point is assigned to — it only sets exact_on_cusp.
"""


@dataclass(frozen=True, slots=True)
class HousePlacement:
    """
    POINT-TO-HOUSE MEMBERSHIP: Result vessel for a single house assignment.

    Records the outcome of assigning one ecliptic longitude to a house under
    the boundary doctrine encoded in assign_house().  All fields needed to
    audit or reproduce the result are present.

    Fields:
        house
            The house number (1–12) to which `longitude` was assigned.
            Derived from the cusp intervals in `house_cusps`.

        longitude
            The ecliptic longitude (degrees, [0, 360)) that was placed.
            This is the value passed to assign_house(); it is stored verbatim
            so the caller can always confirm what was placed.

        house_cusps
            The HouseCusps vessel that determined the placement.  Carries the
            full truth trail: requested/effective system, fallback, fallback
            reason, classification, and policy.

        exact_on_cusp
            True iff `longitude` coincides with the opening cusp of `house`
            within _MEMBERSHIP_CUSP_TOLERANCE degrees.  The point is still
            assigned to that house (the opening cusp belongs to the house it
            opens).  False in all other cases.

        cusp_longitude
            The ecliptic longitude of the cusp that opens `house`.
            Convenience copy of house_cusps.cusps[house - 1].

    Boundary doctrine (mirrored from assign_house()):
        - House n occupies the half-open interval [cusps[n-1], cusps[n % 12]).
        - Spans are forward arcs on the circle: (end − start) % 360°.
        - The opening cusp is included; the next cusp is excluded.
        - Exact-on-cusp detection uses _MEMBERSHIP_CUSP_TOLERANCE.
        - The membership rule is identical for all system families.

    This dataclass is frozen (immutable) and carries no computation logic.

    Future layers that are NOT the responsibility of this class:
        - Angularity scoring or cusp-zone analysis
        - System comparison or ranked placement
        Cusp proximity and boundary sensitivity live in Phase 6
        (HouseBoundaryProfile / describe_boundary()), which consumes this vessel.
    """
    house:         int
    longitude:     float
    house_cusps:   HouseCusps
    exact_on_cusp: bool
    cusp_longitude: float

    def __post_init__(self) -> None:
        assert 1 <= self.house <= 12, (
            f"HousePlacement invariant violated: house={self.house!r} not in [1, 12]"
        )
        assert 0.0 <= self.longitude < 360.0, (
            f"HousePlacement invariant violated: longitude={self.longitude!r} not in [0, 360)"
        )
        assert 0.0 <= self.cusp_longitude < 360.0, (
            f"HousePlacement invariant violated: cusp_longitude={self.cusp_longitude!r} not in [0, 360)"
        )
        expected_cusp = self.house_cusps.cusps[self.house - 1]
        assert abs(self.cusp_longitude - expected_cusp) < 1e-9, (
            f"HousePlacement invariant violated: cusp_longitude={self.cusp_longitude!r} "
            f"does not match house_cusps.cusps[{self.house - 1}]={expected_cusp!r}"
        )


def assign_house(longitude: float, house_cusps: HouseCusps) -> HousePlacement:
    """
    Assign an ecliptic longitude to a house (1–12) using an existing HouseCusps.

    POINT-TO-HOUSE MEMBERSHIP:
        Implements the canonical interval rule under explicit boundary doctrine.
        The result is a HousePlacement vessel that records the house number,
        the placed longitude, the cusp vessel used, the exact-on-cusp flag,
        and the opening cusp longitude.

    BOUNDARY DOCTRINE:
        Interval rule:
            House n occupies the half-open interval [cusps[n-1], cusps[n % 12]).
            The opening cusp is included in the house it opens.
            The closing cusp (= opening cusp of the next house) is excluded.

        Wraparound:
            Cusp positions are ecliptic longitudes in [0, 360).  They need not
            increase monotonically; the span of a house is always the *forward*
            arc on the circle:
                span = (next_cusp − this_cusp) % 360°
            A point at `longitude` falls in house n when:
                (longitude − cusps[n-1]) % 360° < span_n
            (Strictly less than, so the next cusp is excluded.)

        Exact-on-cusp:
            When (longitude − cusps[n-1]) % 360° < _MEMBERSHIP_CUSP_TOLERANCE,
            exact_on_cusp is True.  The point is still unambiguously assigned
            to house n (not split between houses).

        System-family independence:
            The membership rule is identical for EQUAL, QUADRANT, WHOLE_SIGN,
            and SOLAR families.  The cusp positions differ by system; the rule
            does not.

    GUARANTEES:
        - Always returns a house in [1, 12].
        - Exactly one house claims any given longitude (no gaps, no overlaps).
        - The opening cusp of a house belongs to that house.
        - A longitude numerically equal to two consecutive cusps (degenerate
          zero-width house) is assigned to the house that opens at that cusp.

    Args:
        longitude: Ecliptic longitude of the point, in degrees.
            Will be normalised to [0, 360) before placement.
        house_cusps: A HouseCusps result from calculate_houses().

    Returns:
        A frozen HousePlacement describing which house the point occupies.

    Raises:
        ValueError: If house_cusps.cusps does not contain exactly 12 values.
    """
    if len(house_cusps.cusps) != 12:
        raise ValueError(
            f"assign_house requires exactly 12 cusps; got {len(house_cusps.cusps)}"
        )

    lon = longitude % 360.0

    for i in range(12):
        cusp_open  = house_cusps.cusps[i]
        cusp_close = house_cusps.cusps[(i + 1) % 12]
        span       = (cusp_close - cusp_open) % 360.0
        dist       = (lon - cusp_open) % 360.0

        if dist < span:
            house         = i + 1
            exact_on_cusp = dist < _MEMBERSHIP_CUSP_TOLERANCE
            return HousePlacement(
                house=house,
                longitude=lon,
                house_cusps=house_cusps,
                exact_on_cusp=exact_on_cusp,
                cusp_longitude=cusp_open,
            )

    # Fallback: assign to the house whose cusp is angularly closest.
    # This can only be reached in pathological cusp sets (e.g. duplicate cusps
    # leaving a zero-width gap not covered above), and is deterministic.
    min_dist = 361.0
    best     = 0
    for i in range(12):
        d = (lon - house_cusps.cusps[i]) % 360.0
        if d < min_dist:
            min_dist = d
            best     = i
    house         = best + 1
    exact_on_cusp = min_dist < _MEMBERSHIP_CUSP_TOLERANCE
    return HousePlacement(
        house=house,
        longitude=lon,
        house_cusps=house_cusps,
        exact_on_cusp=exact_on_cusp,
        cusp_longitude=house_cusps.cusps[best],
    )


# ===========================================================================
# CUSP PROXIMITY / BOUNDARY SENSITIVITY LAYER  (Phase 6)
# ===========================================================================

_NEAR_CUSP_DEFAULT_THRESHOLD: float = 3.0
"""
Default near-cusp threshold in degrees used by describe_boundary().

3.0° is a conventional orb widely used in traditional and modern astrology
for cusp sensitivity.  It is the default, not an imposed doctrine; callers
must pass a different value to declare a different threshold explicitly.
"""


@dataclass(frozen=True, slots=True)
class HouseBoundaryProfile:
    """
    CUSP PROXIMITY / BOUNDARY SENSITIVITY: Boundary context for a placement.

    Enriches an existing HousePlacement with the distances from the placed
    longitude to the cusps that bracket its house, and a near-cusp flag
    evaluated against an explicit threshold.

    This vessel does NOT re-perform house assignment.  All placement truth
    (house number, longitude, house_cusps, exact_on_cusp) is inherited from
    the source HousePlacement via the `placement` field.

    Fields:
        placement
            The HousePlacement that was profiled.  Authoritative source of
            house number, longitude, and the HouseCusps that computed the
            cusps.  Boundary profiling reads from this; it never modifies or
            overrides it.

        opening_cusp
            Ecliptic longitude of the cusp that opens the assigned house.
            Equal to placement.house_cusps.cusps[placement.house - 1].
            Identical to placement.cusp_longitude.

        closing_cusp
            Ecliptic longitude of the cusp that closes the assigned house
            (= opening cusp of the next house).
            Equal to placement.house_cusps.cusps[placement.house % 12].

        dist_to_opening
            Forward arc (degrees) from the opening cusp to the placed
            longitude: (longitude − opening_cusp) % 360°.
            Always ≥ 0.  Equals 0.0 when placement.exact_on_cusp is True.
            Equals dist from H-cusp to the point, measured inside the house.

        dist_to_closing
            Forward arc (degrees) from the placed longitude to the closing
            cusp: (closing_cusp − longitude) % 360°.
            Always > 0 for any placement inside the house (the closing cusp
            is excluded by the Phase 5 interval rule, so the point never
            coincides with it).  Equals house_span when exact_on_cusp is True.

        house_span
            Total arc of the assigned house in degrees.
            Invariant: dist_to_opening + dist_to_closing == house_span.

        nearest_cusp
            Longitude of whichever cusp (opening or closing) is angularly
            closer to the placed longitude under the within-house minimal
            distance.  When both distances are equal (midpoint of the house),
            the opening cusp is preferred.

        nearest_cusp_distance
            min(dist_to_opening, dist_to_closing).
            Always ≤ house_span / 2.
            Equals 0.0 when exact_on_cusp is True (opening cusp is nearest,
            dist_to_opening is 0).

        near_cusp_threshold
            The threshold (degrees) declared by the caller and used to compute
            is_near_cusp.  Stored so the result is fully self-describing.

        is_near_cusp
            True iff nearest_cusp_distance < near_cusp_threshold.
            When exact_on_cusp is True, nearest_cusp_distance is 0; is_near_cusp
            is True for any positive threshold.

    Distance doctrine:
        All distances are **forward arcs** on the ecliptic circle:
            dist_to_opening  = (longitude − opening_cusp) % 360°
            dist_to_closing  = (closing_cusp − longitude) % 360°
        This preserves the Phase 5 interval direction.  Both are non-negative
        and their sum is always house_span (up to floating-point precision).
        nearest_cusp_distance is the minimum of the two — a within-house
        measure, not the global minimal arc to any cusp on the zodiac.

    Relationship with exact_on_cusp (Phase 5):
        When placement.exact_on_cusp is True:
            dist_to_opening  == 0.0  (within 1e-9°)
            nearest_cusp     == opening_cusp
            nearest_cusp_distance == 0.0 (or < 1e-9°)
            is_near_cusp     == True  (for any positive threshold)
        No special-casing is applied; the arithmetic is naturally consistent.

    This dataclass is frozen (immutable) and carries no computation logic.

    Future layers that are NOT the responsibility of this class:
        - Angularity classification (Phase 7: HouseAngularityProfile)
        - System comparison
    """
    placement:             HousePlacement
    opening_cusp:          float
    closing_cusp:          float
    dist_to_opening:       float
    dist_to_closing:       float
    house_span:            float
    nearest_cusp:          float
    nearest_cusp_distance: float
    near_cusp_threshold:   float
    is_near_cusp:          bool

    def __post_init__(self) -> None:
        assert 0.0 <= self.opening_cusp < 360.0, (
            f"HouseBoundaryProfile: opening_cusp={self.opening_cusp!r} not in [0, 360)"
        )
        assert 0.0 <= self.closing_cusp < 360.0, (
            f"HouseBoundaryProfile: closing_cusp={self.closing_cusp!r} not in [0, 360)"
        )
        assert self.dist_to_opening >= 0.0, (
            f"HouseBoundaryProfile: dist_to_opening={self.dist_to_opening!r} < 0"
        )
        assert self.dist_to_closing > 0.0, (
            f"HouseBoundaryProfile: dist_to_closing={self.dist_to_closing!r} <= 0"
        )
        assert abs(self.dist_to_opening + self.dist_to_closing - self.house_span) < 1e-9, (
            f"HouseBoundaryProfile: dist_to_opening + dist_to_closing "
            f"({self.dist_to_opening + self.dist_to_closing}) != house_span ({self.house_span})"
        )
        assert self.house_span > 0.0, (
            f"HouseBoundaryProfile: house_span={self.house_span!r} <= 0"
        )
        assert self.near_cusp_threshold > 0.0, (
            f"HouseBoundaryProfile: near_cusp_threshold={self.near_cusp_threshold!r} <= 0"
        )
        assert self.nearest_cusp_distance >= 0.0, (
            f"HouseBoundaryProfile: nearest_cusp_distance={self.nearest_cusp_distance!r} < 0"
        )
        assert self.is_near_cusp == (self.nearest_cusp_distance < self.near_cusp_threshold), (
            f"HouseBoundaryProfile: is_near_cusp inconsistent with "
            f"nearest_cusp_distance={self.nearest_cusp_distance!r} and "
            f"near_cusp_threshold={self.near_cusp_threshold!r}"
        )


def describe_boundary(
    placement: HousePlacement,
    *,
    near_cusp_threshold: float = _NEAR_CUSP_DEFAULT_THRESHOLD,
) -> HouseBoundaryProfile:
    """
    Derive boundary context for an existing HousePlacement.

    CUSP PROXIMITY / BOUNDARY SENSITIVITY:
        Computes how far the placed longitude sits from the cusps that bracket
        its assigned house, and whether it is considered near-cusp under the
        declared threshold.  House assignment is NOT re-performed; the
        placement's house number and longitude are authoritative.

    DISTANCE DOCTRINE:
        dist_to_opening:
            Forward arc from the opening cusp to the placed longitude.
            (longitude − opening_cusp) % 360°.
            Equals 0 when placement.exact_on_cusp is True.

        dist_to_closing:
            Forward arc from the placed longitude to the closing cusp.
            (closing_cusp − longitude) % 360°.
            Always positive: Phase 5 assigns the closing cusp to the next
            house, so a point can never land exactly on the closing cusp.

        house_span:
            Total forward arc of the house.
            Invariant: dist_to_opening + dist_to_closing == house_span.

        nearest_cusp / nearest_cusp_distance:
            The cusp that is closer (min of the two forward distances).
            Tie-break: opening cusp preferred.
            nearest_cusp_distance is always ≤ house_span / 2.

        is_near_cusp:
            True iff nearest_cusp_distance < near_cusp_threshold.

    NEAR-CUSP THRESHOLD:
        The `near_cusp_threshold` argument is keyword-only and defaults to
        _NEAR_CUSP_DEFAULT_THRESHOLD (3.0°).  It is a caller-declared doctrine
        value, not an internal constant; any positive float is accepted.  The
        chosen threshold is stored verbatim in the result for auditability.

    Args:
        placement: A HousePlacement returned by assign_house().
        near_cusp_threshold: Forward-arc threshold in degrees below which a
            placement is considered near-cusp.  Keyword-only.
            Must be > 0.  Defaults to 3.0°.

    Returns:
        A frozen HouseBoundaryProfile enriching the placement with boundary
        context.

    Raises:
        ValueError: If near_cusp_threshold is not positive.
    """
    if near_cusp_threshold <= 0.0:
        raise ValueError(
            f"near_cusp_threshold must be positive; got {near_cusp_threshold!r}"
        )

    cusps        = placement.house_cusps.cusps
    house_idx    = placement.house - 1
    opening_cusp = cusps[house_idx]
    closing_cusp = cusps[placement.house % 12]
    lon          = placement.longitude

    house_span       = (closing_cusp - opening_cusp) % 360.0
    dist_to_opening  = (lon - opening_cusp) % 360.0
    dist_to_closing  = (closing_cusp - lon) % 360.0

    if dist_to_opening <= dist_to_closing:
        nearest_cusp          = opening_cusp
        nearest_cusp_distance = dist_to_opening
    else:
        nearest_cusp          = closing_cusp
        nearest_cusp_distance = dist_to_closing

    is_near_cusp = nearest_cusp_distance < near_cusp_threshold

    return HouseBoundaryProfile(
        placement=placement,
        opening_cusp=opening_cusp,
        closing_cusp=closing_cusp,
        dist_to_opening=dist_to_opening,
        dist_to_closing=dist_to_closing,
        house_span=house_span,
        nearest_cusp=nearest_cusp,
        nearest_cusp_distance=nearest_cusp_distance,
        near_cusp_threshold=near_cusp_threshold,
        is_near_cusp=is_near_cusp,
    )


# ===========================================================================
# ANGULARITY / HOUSE-POWER STRUCTURE LAYER  (Phase 7)
# ===========================================================================

class HouseAngularity(str, Enum):
    """
    Structural angularity category of a house.

    The traditional three-tier house-power doctrine assigns every house to
    one of three categories based on its position relative to the four
    angular cusps (ASC, IC, DSC, MC):

    ANGULAR
        Houses 1, 4, 7, 10.
        These houses open at the four primary angles of the chart.  A planet
        in an angular house is considered to act with the greatest immediacy
        and directness in traditional doctrine.

    SUCCEDENT
        Houses 2, 5, 8, 11.
        These houses follow immediately after the angular houses.  A planet
        here is considered to act with moderate directness; its energy is
        building toward the angle rather than already at it.

    CADENT
        Houses 3, 6, 9, 12.
        These houses precede the angular houses (they "fall away" toward the
        next angle).  A planet here is considered less directly operative in
        traditional doctrine.

    Doctrine scope at this phase:
        This classification is purely house-number-based.  No cusp proximity,
        no orb, no near-cusp sensitivity, and no system-family adjustments are
        applied.  The mapping is universal across all 19 supported house systems
        because it is derived from the assigned house number alone.

    Future phases that are NOT the responsibility of this enum:
        - Weighting or scoring the three categories
        - Combining angularity with cusp proximity for a compound strength value
        - System-comparison ranking
    """
    ANGULAR   = "angular"
    SUCCEDENT = "succedent"
    CADENT    = "cadent"


_ANGULARITY_MAP: dict[int, HouseAngularity] = {
    1:  HouseAngularity.ANGULAR,
    2:  HouseAngularity.SUCCEDENT,
    3:  HouseAngularity.CADENT,
    4:  HouseAngularity.ANGULAR,
    5:  HouseAngularity.SUCCEDENT,
    6:  HouseAngularity.CADENT,
    7:  HouseAngularity.ANGULAR,
    8:  HouseAngularity.SUCCEDENT,
    9:  HouseAngularity.CADENT,
    10: HouseAngularity.ANGULAR,
    11: HouseAngularity.SUCCEDENT,
    12: HouseAngularity.CADENT,
}


@dataclass(frozen=True, slots=True)
class HouseAngularityProfile:
    """
    ANGULARITY / HOUSE-POWER STRUCTURE: Structural positional status of a placement.

    Enriches an existing HousePlacement with its traditional angularity
    category (ANGULAR, SUCCEDENT, or CADENT), derived from the assigned
    house number alone.

    This vessel does NOT re-perform house assignment.  The placement's house
    number is authoritative; angularity is read from it via the static
    _ANGULARITY_MAP lookup.

    Fields:
        placement
            The HousePlacement that was profiled.  Authoritative source of
            the house number and all prior truth (longitude, house_cusps,
            exact_on_cusp, cusp_longitude).  This layer reads from placement;
            it never modifies or overrides it.

        category
            The HouseAngularity value for the assigned house.
            Derived from placement.house via _ANGULARITY_MAP.
            Always one of ANGULAR, SUCCEDENT, CADENT.

        house
            Convenience copy of placement.house (1–12).
            Redundant with placement.house; present so callers can read
            both category and house number from a single vessel without
            traversing the placement chain.

    Angularity doctrine:
        ANGULAR   — house in {1, 4, 7, 10}
        SUCCEDENT — house in {2, 5, 8, 11}
        CADENT    — house in {3, 6, 9, 12}
        The mapping is identical for all house systems and all latitudes.
        No cusp proximity, orb, or boundary context influences the category
        at this phase.

    Relationship with Phase 6 (HouseBoundaryProfile):
        describe_boundary() and describe_angularity() are independent
        enrichment functions that both consume a HousePlacement.  They can
        be called in any order or independently; neither depends on the other.

    This dataclass is frozen (immutable) and carries no computation logic.

    Future layers that are NOT the responsibility of this class:
        - Compound strength scores combining angularity and cusp proximity
        - System comparison or chart-wide power distribution
        - Harmonic overlays
    """
    placement: HousePlacement
    category:  HouseAngularity
    house:     int

    def __post_init__(self) -> None:
        assert 1 <= self.house <= 12, (
            f"HouseAngularityProfile invariant violated: house={self.house!r} not in [1, 12]"
        )
        assert self.house == self.placement.house, (
            f"HouseAngularityProfile invariant violated: house={self.house!r} "
            f"does not match placement.house={self.placement.house!r}"
        )
        assert self.category == _ANGULARITY_MAP[self.house], (
            f"HouseAngularityProfile invariant violated: category={self.category!r} "
            f"does not match _ANGULARITY_MAP[{self.house}]={_ANGULARITY_MAP[self.house]!r}"
        )


def describe_angularity(placement: HousePlacement) -> HouseAngularityProfile:
    """
    Derive the angularity / house-power profile for an existing HousePlacement.

    ANGULARITY / HOUSE-POWER STRUCTURE:
        Maps the assigned house number to its traditional structural category
        (ANGULAR, SUCCEDENT, or CADENT) using a static lookup table.
        House assignment is NOT re-performed; placement.house is authoritative.

    DOCTRINE:
        ANGULAR   — houses 1, 4, 7, 10  (the four cardinal angles).
        SUCCEDENT — houses 2, 5, 8, 11  (follow the angles).
        CADENT    — houses 3, 6, 9, 12  (precede the angles).

        The mapping is purely house-number-based.  No cusp proximity, no orb,
        no latitude sensitivity, and no system-family differences are applied
        at this phase.  The doctrine is identical for all 19 supported house
        systems because it derives from the assigned house number alone.

    RELATIONSHIP WITH OTHER LAYERS:
        describe_angularity() and describe_boundary() are independent; neither
        depends on the other.  Both consume a HousePlacement and can be called
        in any order.

    Args:
        placement: A HousePlacement returned by assign_house().

    Returns:
        A frozen HouseAngularityProfile with category and house number.
    """
    house    = placement.house
    category = _ANGULARITY_MAP[house]
    return HouseAngularityProfile(
        placement=placement,
        category=category,
        house=house,
    )


# ===========================================================================
# SYSTEM COMPARISON LAYER  (Phase 8)
# ===========================================================================

def _circular_diff(a: float, b: float) -> float:
    """Signed circular difference (b − a) in the range (−180, 180]."""
    d = (b - a) % 360.0
    return d - 360.0 if d > 180.0 else d


@dataclass(frozen=True, slots=True)
class HouseSystemComparison:
    """
    SYSTEM COMPARISON: Cusp-level diff of two HouseCusps results.

    Compares two independently-computed HouseCusps objects that were produced
    for the same moment and location under (potentially) different house
    systems.  The comparison is structural and factual; it carries no
    interpretation of which system is "better".

    This vessel does NOT recompute any cusps.  All cusp values are taken
    verbatim from the source HouseCusps objects.

    Fields:
        left
            The first HouseCusps (the reference).

        right
            The second HouseCusps (compared against left).

        cusp_deltas
            Tuple of 12 signed circular differences, one per house:
                cusp_deltas[i] = circular_diff(left.cusps[i], right.cusps[i])
            Each value is in the range (−180°, 180°].
            Positive means right cusp is ahead (counter-clockwise) of left.
            Negative means right cusp is behind left.
            Zero means the cusps coincide within floating-point precision.

        systems_agree
            True iff left.effective_system == right.effective_system.
            Uses the *effective* system (the code that actually produced the
            cusps), not the requested system.  Two calls that requested
            different systems but both fell back to Porphyry will agree.

        fallback_differs
            True iff left.fallback != right.fallback.
            Surfaces the case where one call fell back and the other did not,
            which may indicate an asymmetric policy or latitude condition.

        families_differ
            True iff the doctrinal families of the two effective systems differ.
            Derived from left.classification.family and right.classification.family.
            None-safe: if either classification is None, families_differ is True.

    Comparison doctrine:
        - Cusp delta uses the signed circular difference (right − left),
          preserving ecliptic direction.  The result is always in (−180, 180].
        - systems_agree, fallback_differs, and families_differ all compare
          effective-system properties, not requested-system properties.
        - Requested-system truth is never discarded; it is readable via
          left.system and right.system from the stored HouseCusps objects.

    This dataclass is frozen (immutable) and carries no computation logic.
    """
    left:             HouseCusps
    right:            HouseCusps
    cusp_deltas:      tuple[float, ...]
    systems_agree:    bool
    fallback_differs: bool
    families_differ:  bool

    def __post_init__(self) -> None:
        assert len(self.cusp_deltas) == 12, (
            f"HouseSystemComparison: cusp_deltas must have 12 entries; "
            f"got {len(self.cusp_deltas)}"
        )
        assert all(-180.0 < d <= 180.0 for d in self.cusp_deltas), (
            f"HouseSystemComparison: cusp_deltas contains value outside (-180, 180]: "
            f"{self.cusp_deltas!r}"
        )
        assert self.systems_agree == (
            self.left.effective_system == self.right.effective_system
        ), (
            "HouseSystemComparison: systems_agree inconsistent with effective_system fields"
        )
        assert self.fallback_differs == (self.left.fallback != self.right.fallback), (
            "HouseSystemComparison: fallback_differs inconsistent with fallback fields"
        )


@dataclass(frozen=True, slots=True)
class HousePlacementComparison:
    """
    SYSTEM COMPARISON: Point-placement comparison across two or more systems.

    Records where a single ecliptic longitude lands under each of two or more
    independently-computed HouseCusps, and whether all systems agree on the
    house assignment.

    This vessel does NOT recompute any house assignments.  The placements
    tuple contains one HousePlacement per system, produced by assign_house()
    for the same longitude under each system.

    Fields:
        longitude
            The ecliptic longitude that was placed (degrees, normalised to
            [0, 360)).  Same value used for every placement in this comparison.

        placements
            Tuple of HousePlacement objects, one per input HouseCusps, in the
            same order as the systems were supplied to compare_placements().
            Each carries the full truth trail: requested/effective system,
            fallback, classification, policy.

        houses
            Tuple of house numbers (1–12), one per placement, in the same
            order as placements.  Convenience copy; equivalent to reading
            placement.house from each element of placements.

        all_agree
            True iff all house numbers in `houses` are identical.
            A True value means every compared system places the longitude in
            the same house.

        angularity_agrees
            True iff all placements share the same HouseAngularity category.
            Derived via describe_angularity() at construction time.
            Two systems may disagree on house number but agree on angularity
            (e.g. both assign an angular house, just different ones).

    Comparison doctrine:
        - longitude is normalised to [0, 360) before placement.
        - all_agree compares house numbers exactly; no tolerance is applied.
        - angularity_agrees compares HouseAngularity category values.
        - Requested-system truth is preserved on each placement's house_cusps.
        - Requires at least 2 placements; compare_placements() enforces this.

    This dataclass is frozen (immutable) and carries no computation logic.
    """
    longitude:         float
    placements:        tuple[HousePlacement, ...]
    houses:            tuple[int, ...]
    all_agree:         bool
    angularity_agrees: bool

    def __post_init__(self) -> None:
        assert 0.0 <= self.longitude < 360.0, (
            f"HousePlacementComparison: longitude={self.longitude!r} not in [0, 360)"
        )
        assert len(self.placements) >= 2, (
            f"HousePlacementComparison: requires at least 2 placements; "
            f"got {len(self.placements)}"
        )
        assert len(self.houses) == len(self.placements), (
            f"HousePlacementComparison: houses length {len(self.houses)} != "
            f"placements length {len(self.placements)}"
        )
        assert all(h == pl.house for h, pl in zip(self.houses, self.placements)), (
            "HousePlacementComparison: houses tuple does not match placement.house values"
        )
        assert self.all_agree == (len(set(self.houses)) == 1), (
            "HousePlacementComparison: all_agree inconsistent with houses tuple"
        )
        for pl in self.placements:
            assert pl.longitude == self.longitude, (
                f"HousePlacementComparison: placement.longitude={pl.longitude!r} "
                f"!= longitude={self.longitude!r}"
            )


def compare_systems(left: HouseCusps, right: HouseCusps) -> HouseSystemComparison:
    """
    Produce a cusp-level comparison of two HouseCusps results.

    SYSTEM COMPARISON:
        Computes per-house signed circular cusp deltas and derives agreement
        flags from the two HouseCusps objects.  No cusps are recomputed.

    CUSP DELTA DOCTRINE:
        For each house i (0–11):
            cusp_deltas[i] = (right.cusps[i] − left.cusps[i]) mod ±180°
        The signed circular difference preserves ecliptic direction:
            Positive  → right cusp is counter-clockwise ahead of left.
            Negative  → right cusp is behind left.
            Near-zero → cusps coincide.
        Range: (−180°, 180°].

    AGREEMENT FLAGS:
        systems_agree:    left.effective_system == right.effective_system.
        fallback_differs: left.fallback != right.fallback.
        families_differ:  classification families of the effective systems differ.

    Args:
        left:  First (reference) HouseCusps.
        right: Second HouseCusps to compare against left.

    Returns:
        A frozen HouseSystemComparison.
    """
    deltas = tuple(
        _circular_diff(left.cusps[i], right.cusps[i]) for i in range(12)
    )

    left_family  = left.classification.family  if left.classification  is not None else None
    right_family = right.classification.family if right.classification is not None else None
    families_differ = (left_family is None or right_family is None or left_family != right_family)

    return HouseSystemComparison(
        left=left,
        right=right,
        cusp_deltas=deltas,
        systems_agree=(left.effective_system == right.effective_system),
        fallback_differs=(left.fallback != right.fallback),
        families_differ=families_differ,
    )


def compare_placements(
    longitude: float,
    *house_cusps_seq: HouseCusps,
) -> HousePlacementComparison:
    """
    Place one longitude under each of two or more systems and compare results.

    SYSTEM COMPARISON:
        Calls assign_house(longitude, hc) for each HouseCusps in house_cusps_seq,
        then collects the resulting HousePlacement objects and derives agreement
        flags.  No house assignments are re-performed beyond what assign_house()
        computes independently for each system.

    DOCTRINE:
        - longitude is normalised to [0, 360) before any placement.
        - all_agree is True iff all systems assign the same house number.
        - angularity_agrees is True iff all placements share the same
          HouseAngularity category (derived via describe_angularity()).
        - Requested-system truth is preserved on each placement's house_cusps.

    Args:
        longitude: Ecliptic longitude to place, in degrees.
            Normalised to [0, 360) before placement.
        *house_cusps_seq: Two or more HouseCusps objects to compare.
            Must supply at least two.

    Returns:
        A frozen HousePlacementComparison.

    Raises:
        ValueError: If fewer than two HouseCusps are supplied.
    """
    if len(house_cusps_seq) < 2:
        raise ValueError(
            f"compare_placements requires at least 2 HouseCusps; "
            f"got {len(house_cusps_seq)}"
        )

    lon        = longitude % 360.0
    placements = tuple(assign_house(lon, hc) for hc in house_cusps_seq)
    houses     = tuple(pl.house for pl in placements)
    all_agree  = len(set(houses)) == 1

    categories        = tuple(describe_angularity(pl).category for pl in placements)
    angularity_agrees = len(set(categories)) == 1

    return HousePlacementComparison(
        longitude=lon,
        placements=placements,
        houses=houses,
        all_agree=all_agree,
        angularity_agrees=angularity_agrees,
    )


# ===========================================================================
# CHART-WIDE HOUSE DISTRIBUTION INTELLIGENCE  (Phase 9)
# ===========================================================================

@dataclass(frozen=True, slots=True)
class HouseOccupancy:
    """
    CHART-WIDE DISTRIBUTION: Per-house occupancy record.

    One HouseOccupancy exists for every house (1–12) inside a
    HouseDistributionProfile.  It records which points from the input
    sequence were assigned to this house.

    This vessel does NOT perform house assignment.  All placements are
    produced upstream by distribute_points() via assign_house() and
    stored here verbatim.

    Fields:
        house
            House number (1–12) this record describes.

        count
            Number of points assigned to this house.  Equals len(longitudes).

        longitudes
            Tuple of normalised ecliptic longitudes (degrees, [0, 360)) of
            the points assigned to this house, in the same order they
            appeared in the input sequence supplied to distribute_points().

        placements
            Tuple of HousePlacement objects for each occupant, in the same
            input order as longitudes.  Each carries the full truth trail
            (house_cusps, effective_system, fallback, classification, policy).

        is_empty
            True iff count == 0.  Convenience flag; equivalent to count == 0.

    Invariants:
        count == len(longitudes) == len(placements)
        is_empty == (count == 0)
        All placements have placement.house == house.
    """
    house:      int
    count:      int
    longitudes: tuple[float, ...]
    placements: tuple[HousePlacement, ...]
    is_empty:   bool

    def __post_init__(self) -> None:
        assert 1 <= self.house <= 12, (
            f"HouseOccupancy: house={self.house!r} not in [1, 12]"
        )
        assert self.count == len(self.longitudes), (
            f"HouseOccupancy: count={self.count} != len(longitudes)={len(self.longitudes)}"
        )
        assert self.count == len(self.placements), (
            f"HouseOccupancy: count={self.count} != len(placements)={len(self.placements)}"
        )
        assert self.is_empty == (self.count == 0), (
            f"HouseOccupancy: is_empty={self.is_empty} inconsistent with count={self.count}"
        )
        for pl in self.placements:
            assert pl.house == self.house, (
                f"HouseOccupancy: placement.house={pl.house} != house={self.house}"
            )


@dataclass(frozen=True, slots=True)
class HouseDistributionProfile:
    """
    CHART-WIDE DISTRIBUTION: Chart-wide house distribution analysis.

    Summarises how a set of point longitudes distributes across the twelve
    houses of one house system, including per-house occupancy, empty-house
    detection, dominant-house identification, and angularity-category totals.

    This vessel does NOT perform house assignment.  All placements are
    produced by distribute_points() via assign_house() and stored in the
    occupancies.

    Fields:
        house_cusps
            The HouseCusps used for all placements in this profile.  Carries
            full truth: requested/effective system, fallback, classification,
            policy.

        point_count
            Total number of point longitudes that were placed.
            Equals sum(occ.count for occ in occupancies).

        occupancies
            Tuple of 12 HouseOccupancy objects, one per house, ordered
            house 1 → 12.  Always exactly 12 entries, even for empty houses.

        counts
            Tuple of 12 integers (convenience copy):
                counts[i] == occupancies[i].count, for i in 0..11
            counts[i] is the occupant count for house i+1.

        empty_houses
            Frozenset of house numbers (1–12) with zero occupants.

        dominant_houses
            Tuple of house numbers (1–12) whose occupant count equals
            max(counts), sorted ascending.  Empty tuple if point_count == 0
            (all counts are zero; no house is dominant).

        angular_count
            Total points assigned to houses 1, 4, 7, 10 (ANGULAR).

        succedent_count
            Total points assigned to houses 2, 5, 8, 11 (SUCCEDENT).

        cadent_count
            Total points assigned to houses 3, 6, 9, 12 (CADENT).

    Distribution doctrine:
        - Each input longitude is normalised to [0, 360) before placement.
        - Each longitude is placed independently via assign_house().
        - occupancies is always exactly 12 entries, houses 1–12 in order.
        - dominant_houses lists all houses tied for the maximum count.
          If point_count == 0, dominant_houses is an empty tuple.
        - Angularity counts use _ANGULARITY_MAP from Phase 7; no new doctrine.
        - Occupant order within each HouseOccupancy follows input order.

    Invariants:
        len(occupancies) == 12
        len(counts) == 12
        point_count == sum(counts)
        angular_count + succedent_count + cadent_count == point_count
        len(dominant_houses) >= 1 when point_count > 0
        all h in dominant_houses: counts[h-1] == max(counts)

    This dataclass is frozen (immutable) and carries no computation logic.
    """
    house_cusps:      HouseCusps
    point_count:      int
    occupancies:      tuple[HouseOccupancy, ...]
    counts:           tuple[int, ...]
    empty_houses:     frozenset[int]
    dominant_houses:  tuple[int, ...]
    angular_count:    int
    succedent_count:  int
    cadent_count:     int

    def __post_init__(self) -> None:
        assert len(self.occupancies) == 12, (
            f"HouseDistributionProfile: len(occupancies)={len(self.occupancies)}, expected 12"
        )
        assert len(self.counts) == 12, (
            f"HouseDistributionProfile: len(counts)={len(self.counts)}, expected 12"
        )
        assert self.point_count == sum(self.counts), (
            f"HouseDistributionProfile: point_count={self.point_count} != sum(counts)={sum(self.counts)}"
        )
        assert self.angular_count + self.succedent_count + self.cadent_count == self.point_count, (
            f"HouseDistributionProfile: angularity counts sum "
            f"({self.angular_count}+{self.succedent_count}+{self.cadent_count}) "
            f"!= point_count={self.point_count}"
        )
        for i, occ in enumerate(self.occupancies):
            assert occ.house == i + 1, (
                f"HouseDistributionProfile: occupancies[{i}].house={occ.house}, expected {i+1}"
            )
            assert self.counts[i] == occ.count, (
                f"HouseDistributionProfile: counts[{i}]={self.counts[i]} != occupancy.count={occ.count}"
            )
        if self.point_count == 0:
            assert self.dominant_houses == (), (
                f"HouseDistributionProfile: dominant_houses must be () when point_count==0"
            )
        else:
            max_count = max(self.counts)
            for h in self.dominant_houses:
                assert self.counts[h - 1] == max_count, (
                    f"HouseDistributionProfile: dominant house {h} count "
                    f"{self.counts[h-1]} != max {max_count}"
                )


def distribute_points(
    longitudes: "list[float] | tuple[float, ...]",
    house_cusps: HouseCusps,
) -> HouseDistributionProfile:
    """
    Place a sequence of longitudes against one HouseCusps and return a
    chart-wide distribution profile.

    CHART-WIDE DISTRIBUTION:
        Places each longitude via assign_house() and accumulates per-house
        occupancy records.  Derives empty-house set, dominant-house list, and
        angularity-category totals from the resulting placements.  No new
        house-membership logic is introduced; assign_house() is authoritative.

    DISTRIBUTION DOCTRINE:
        - Each longitude is normalised to [0, 360) before placement.
        - Placements are accumulated per house in input order.
        - occupancies contains exactly 12 HouseOccupancy entries, house 1–12.
        - dominant_houses: all houses tied for max(counts); sorted ascending.
          Empty tuple when no points are provided.
        - empty_houses: frozenset of house numbers with count == 0.
        - Angularity counts use _ANGULARITY_MAP (Phase 7 doctrine).

    Args:
        longitudes: Sequence of ecliptic longitudes to place (degrees).
            May be empty; an empty sequence produces a zero-count profile.
        house_cusps: The HouseCusps to place all points against.

    Returns:
        A frozen HouseDistributionProfile.
    """
    buckets: dict[int, list[tuple[float, HousePlacement]]] = {
        h: [] for h in range(1, 13)
    }

    for raw_lon in longitudes:
        pl = assign_house(raw_lon, house_cusps)
        buckets[pl.house].append((pl.longitude, pl))

    occupancies = tuple(
        HouseOccupancy(
            house=h,
            count=len(buckets[h]),
            longitudes=tuple(lon for lon, _ in buckets[h]),
            placements=tuple(pl for _, pl in buckets[h]),
            is_empty=(len(buckets[h]) == 0),
        )
        for h in range(1, 13)
    )

    counts      = tuple(occ.count for occ in occupancies)
    point_count = sum(counts)

    empty_houses = frozenset(h for h in range(1, 13) if counts[h - 1] == 0)

    if point_count == 0:
        dominant_houses: tuple[int, ...] = ()
    else:
        max_count = max(counts)
        dominant_houses = tuple(h for h in range(1, 13) if counts[h - 1] == max_count)

    angular_count   = sum(counts[h - 1] for h in (1, 4, 7, 10))
    succedent_count = sum(counts[h - 1] for h in (2, 5, 8, 11))
    cadent_count    = sum(counts[h - 1] for h in (3, 6, 9, 12))

    return HouseDistributionProfile(
        house_cusps=house_cusps,
        point_count=point_count,
        occupancies=occupancies,
        counts=counts,
        empty_houses=empty_houses,
        dominant_houses=dominant_houses,
        angular_count=angular_count,
        succedent_count=succedent_count,
        cadent_count=cadent_count,
    )


# ===========================================================================
# ARMC-DIRECT HOUSE COMPUTATION  (Phase 2 — Swiss houses_armc analogue)
# ===========================================================================

def houses_from_armc(
    armc: float,
    obliquity: float,
    lat: float,
    system: str = HouseSystem.PLACIDUS,
    *,
    policy: HousePolicy | None = None,
    sun_longitude: float | None = None,
    ayanamsa_offset: float | None = None,
) -> HouseCusps:
    """
    Compute house cusps directly from a pre-computed ARMC and obliquity.

    Equivalent to Swiss Ephemeris ``swe_houses_armc``.  Use this when the
    ARMC is already known (e.g. from a relocated chart, a synastry engine, or
    an external source) and you do not want Moira to re-derive it from a
    Julian date and geographic longitude.

    Args:
        armc: Apparent Right Ascension of the Medium Coeli (degrees, [0, 360)).
            This is the Local Sidereal Time expressed as an ecliptic degree.
        obliquity: True obliquity of the ecliptic (degrees) at the chart epoch.
        lat: Geographic latitude of the observer (degrees, north positive).
        system: House system identifier; one of the ``HouseSystem`` constants.
            Defaults to ``HouseSystem.PLACIDUS``.
        policy: :class:`HousePolicy` governing fallback doctrine.  Keyword-only.
            Defaults to ``HousePolicy.default()`` (silent fallback).
        sun_longitude: Geocentric ecliptic longitude of the Sun (degrees).
            Required only when ``system == HouseSystem.SUNSHINE``; ignored
            for all other systems.

    Returns:
        A :class:`HouseCusps` vessel populated identically to
        :func:`calculate_houses`, with the same fallback and classification
        fields.

    Raises:
        ValueError: If ``system == HouseSystem.SUNSHINE`` and ``sun_longitude``
            is ``None``.
        ValueError: When policy requires strict behaviour and a fallback
            condition is encountered.
    """
    active_policy = policy if policy is not None else HousePolicy.default()
    mc          = _mc_from_armc(armc, obliquity, lat)
    asc         = _asc_from_armc(armc, obliquity, lat)
    vertex      = _asc_from_armc((armc + 90.0) % 360.0, obliquity, -lat)
    anti_vertex = (vertex + 180.0) % 360.0
    critical_lat = 90.0 - obliquity
    polar = abs(lat) >= critical_lat and system in _POLAR_SYSTEMS
    effective_system = system
    fallback = False
    fallback_reason: str | None = None
    experimental_cusps: list[float] | None = None

    if polar:
        if active_policy.polar_fallback == PolarFallbackPolicy.RAISE:
            raise ValueError(
                f"latitude |{lat:.4f}°| >= critical latitude {critical_lat:.4f}° "
                f"(= 90° − obliquity {obliquity:.4f}°); "
                f"system {system!r} produces geometrically invalid cusps above this "
                f"threshold and policy is RAISE"
            )
        if active_policy.polar_fallback == PolarFallbackPolicy.EXPERIMENTAL_SEARCH:
            if system != HouseSystem.PLACIDUS:
                raise ValueError(
                    f"experimental polar search is only implemented for {HouseSystem.PLACIDUS!r}; "
                    f"got {system!r}"
                )
            experimental_cusps = _experimental_polar_placidus_cusps(
                armc,
                obliquity,
                lat,
                asc,
                mc,
            )
        else:
            effective_system = HouseSystem.PORPHYRY
            fallback = True
            fallback_reason = (
                f"|lat| {abs(lat):.4f}° >= critical latitude {critical_lat:.4f}° "
                f"(90° − obliquity); {system!r} produces invalid cusps above this "
                f"threshold; fell back to Porphyry"
            )
    elif system not in _KNOWN_SYSTEMS:
        if active_policy.unknown_system == UnknownSystemPolicy.RAISE:
            raise ValueError(
                f"unknown house system code {system!r} and policy is RAISE"
            )
        effective_system = HouseSystem.PLACIDUS
        fallback = True
        fallback_reason = f"unknown system code {system!r}; fell back to Placidus"

    if experimental_cusps is not None:
        cusps = experimental_cusps
    elif effective_system == HouseSystem.WHOLE_SIGN:
        cusps = _whole_sign(asc)
    elif effective_system == HouseSystem.EQUAL:
        cusps = _equal_house(asc)
    elif effective_system == HouseSystem.PORPHYRY:
        cusps = _porphyry(asc, mc)
    elif effective_system == HouseSystem.PLACIDUS:
        cusps = _placidus(armc, obliquity, lat)
    elif effective_system == HouseSystem.KOCH:
        cusps = _koch(armc, obliquity, lat)
    elif effective_system == HouseSystem.CAMPANUS:
        cusps = _campanus(armc, obliquity, lat)
    elif effective_system == HouseSystem.REGIOMONTANUS:
        cusps = _regiomontanus(armc, obliquity, lat)
    elif effective_system == HouseSystem.ALCABITIUS:
        cusps = _alcabitius(armc, obliquity, lat)
    elif effective_system == HouseSystem.MORINUS:
        cusps = _morinus(armc, obliquity)
    elif effective_system == HouseSystem.TOPOCENTRIC:
        cusps = _topocentric(armc, obliquity, lat)
    elif effective_system == HouseSystem.MERIDIAN:
        cusps = _meridian(armc, obliquity)
    elif effective_system == HouseSystem.VEHLOW:
        cusps = _vehlow(asc)
    elif effective_system == HouseSystem.SUNSHINE:
        if sun_longitude is None:
            raise ValueError(
                "houses_from_armc: sun_longitude is required for HouseSystem.SUNSHINE"
            )
        cusps = _sunshine(sun_longitude, lat, obliquity)
    elif effective_system == HouseSystem.AZIMUTHAL:
        cusps = _azimuthal(armc, obliquity, lat)
    elif effective_system == HouseSystem.CARTER:
        cusps = _carter(armc, obliquity, lat)
    elif effective_system == HouseSystem.PULLEN_SD:
        cusps = _pullen_sd(armc, obliquity, lat)
    elif effective_system == HouseSystem.PULLEN_SR:
        cusps = _pullen_sr(armc, obliquity, lat)
    elif effective_system == HouseSystem.KRUSINSKI:
        cusps = _krusinski(armc, obliquity, lat)
    elif effective_system == HouseSystem.APC:
        cusps = _apc(armc, obliquity, lat)
    else:
        cusps = _placidus(armc, obliquity, lat)

    _shift = ayanamsa_offset if ayanamsa_offset is not None else 0.0
    return HouseCusps(
        system=system,
        cusps=[normalize_degrees(c - _shift) for c in cusps],
        asc=normalize_degrees(asc - _shift),
        mc=normalize_degrees(mc - _shift),
        armc=normalize_degrees(armc),
        vertex=normalize_degrees(vertex - _shift),
        anti_vertex=normalize_degrees(anti_vertex - _shift),
        effective_system=effective_system,
        fallback=fallback,
        fallback_reason=fallback_reason,
        classification=classify_house_system(effective_system),
        policy=active_policy,
    )


# ===========================================================================
# INTRA-HOUSE FRACTIONAL POSITION  (Phase 2 — Swiss house_pos analogue)
# ===========================================================================

def body_house_position(longitude: float, house_cusps: HouseCusps) -> float:
    """
    Return the fractional house position of an ecliptic longitude.

    Equivalent to Swiss Ephemeris ``swe_house_pos``.  The return value is a
    float H where ``int(H)`` is the house number (1–12) and ``H - int(H)``
    is how far through that house the longitude falls (0.0 at the opening
    cusp, approaching 1.0 at the closing cusp).

    Examples::

        3.0   → exactly on the 3rd-house cusp
        3.5   → midpoint of the 3rd house
        12.99 → just before the 12th house closes (near the Ascendant)

    Args:
        longitude: Ecliptic longitude in degrees (need not be in [0, 360);
            it is normalised internally).
        house_cusps: A :class:`HouseCusps` result from
            :func:`calculate_houses` or :func:`houses_from_armc`.

    Returns:
        A float in the range ``[1.0, 13.0)`` representing the fractional
        house position.

    Raises:
        No exceptions under normal operation.  A degenerate house with zero
        span returns ``float(house_number)``.
    """
    lon = longitude % 360.0
    placement = assign_house(lon, house_cusps)
    n = placement.house
    opening = house_cusps.cusps[n - 1]
    closing = house_cusps.cusps[n % 12]
    span = (closing - opening) % 360.0
    if span < 1e-12:
        return float(n)
    dist = (lon - opening) % 360.0
    return n + dist / span


# ===========================================================================
# HOUSE DYNAMICS DESIGN VESSELS  (Phase 3 — Defer.Doctrine + Defer.Validation)
# ===========================================================================

@dataclass(frozen=True, slots=True)
class CuspSpeed:
    """
    The instantaneous rate of change of a single house cusp.

    Design vessel — Phase 3.  Computation is deferred until the doctrinal
    and validation preconditions are met.

    Doctrine for cusp speed in Moira
    ---------------------------------
    This doctrinal record is written before any implementation so that the
    final surface is never shaped by implementation convenience:

    **What cusp speed means:**
        The rate of change of a cusp's tropical ecliptic longitude with
        respect to Universal Time, in degrees per day.  For quadrant-based
        systems, cusps move because the ARMC moves (sidereal day ≈ 23h56m)
        and because the obliquity changes slowly.  For equal-house systems,
        the ASC speed propagates uniformly.

    **Why this is doctrinally tricky:**
        - Cusp speed is observer-location-dependent: the same sidereal-day
          rotation produces different cusp speeds at different latitudes.
        - At polar latitudes, some systems produce ill-conditioned cusp speeds
          (same instability that triggers the polar-fallback in
          :func:`calculate_houses`).
        - The MC moves at a rate close to 1°/day (the solar day), not 1°/sidereal-day,
          because it is defined by the Sun's right ascension, not by Earth rotation.
          Conflating ARMC-rate with MC-rate is a common error.

    **Validation preconditions:**
        A public cusp-speed surface must be validated against Swiss Ephemeris
        ``swe_houses_ex2`` (which returns cusp speeds in its extended output)
        for ≥5 house systems, ≥3 latitudes, ≥3 epochs.  Tolerance: 0.001°/day.

    Fields
    ------
    house : int
        House number (1–12).
    cusp_longitude : float
        Cusp ecliptic longitude at the instant of measurement (degrees).
    speed_deg_per_day : float
        Rate of change of cusp longitude (degrees/day).
        Positive = cusp moving in the direction of increasing longitude.
    """
    house:              int
    cusp_longitude:     float
    speed_deg_per_day:  float


@dataclass(frozen=True, slots=True)
class HouseDynamics:
    """
    The full set of cusp speeds for a chart, plus angle speeds.

    Design vessel — Phase 3.  Accompanies :class:`CuspSpeed`.

    Doctrine: angle speeds and cusp speeds belong together
    -------------------------------------------------------
    Decision (recorded here before implementation):
        :class:`HouseDynamics` carries both the 12 cusp speeds and the
        four angle speeds (ASC, MC, Vertex, Anti-Vertex).  The rationale
        is that callers who need cusp speeds almost always also need angle
        speeds, and separating them would require two queries for one chart.

        Cusp speeds for houses 1, 4, 7, 10 are redundant with angle speeds
        (ASC = cusp 1, IC = cusp 4, DSC = cusp 7, MC = cusp 10) — they are
        included for uniformity.

    Fields
    ------
    house_cusps : HouseCusps
        The parent house cusps at the instant of measurement.
    cusp_speeds : tuple of CuspSpeed
        Speeds for all 12 cusps, in house order (1–12).
    asc_speed_deg_per_day : float
        Ascendant speed (degrees/day).
    mc_speed_deg_per_day : float
        Midheaven speed (degrees/day).
    vertex_speed_deg_per_day : float
        Vertex speed (degrees/day).
    anti_vertex_speed_deg_per_day : float
        Anti-Vertex speed (degrees/day).
    """
    house_cusps:                    'HouseCusps'
    cusp_speeds:                    tuple
    asc_speed_deg_per_day:          float
    mc_speed_deg_per_day:           float
    vertex_speed_deg_per_day:       float
    anti_vertex_speed_deg_per_day:  float


# ===========================================================================
# HOUSE DYNAMICS COMPUTATION
# ===========================================================================

_SIDEREAL_ROTATION_DEG_PER_DAY = 360.98564736629


def _wrapped_longitude_speed(lon_m: float, lon_p: float, step: float) -> float:
    raw = (lon_p - lon_m) % 360.0
    if raw > 180.0:
        raw -= 360.0
    return raw / (2.0 * step)

def cusp_speeds_at(
    jd_ut:    float,
    latitude: float,
    longitude: float,
    system:   str = HouseSystem.PLACIDUS,
    *,
    policy: HousePolicy | None = None,
    dt:     float = 1.0 / 1440.0,
) -> HouseDynamics:
    """
    Compute instantaneous house cusp speeds and angle speeds.

    Method: centred finite difference over ±dt on :func:`calculate_houses`.
    The derivative is estimated as::

        speed = (longitude(t+dt) − longitude(t−dt)) / (2·dt)

    with a wraparound-safe subtraction (result in (−180, 180]).

    This approach is consistent with how Swiss Ephemeris ``swe_houses_ex2``
    derives cusp speeds internally (finite difference over a small time step).

    Args:
        jd_ut: Julian date in Universal Time (UT1).
        latitude: Geographic latitude of the observer (decimal degrees,
            positive north, range [−90, 90]).
        longitude: Geographic longitude of the observer (decimal degrees,
            positive east, range [−180, 180]).
        system: House system identifier; one of the HouseSystem constants.
            Defaults to HouseSystem.PLACIDUS.
        policy: HousePolicy governing fallback doctrine.  Keyword-only.
            Defaults to HousePolicy.default().
        dt: Half-step in Julian Days for the finite difference.  Keyword-only.
            Default is 1/1440 day (exactly 1 minute).  Values smaller than
            1e-6 may introduce floating-point noise; values larger than 0.01
            reduce accuracy for fast-moving angles.

    Returns:
        A :class:`HouseDynamics` instance containing the house cusps at
        ``jd_ut``, the 12 :class:`CuspSpeed` records, and the four angle
        speeds (ASC, MC, Vertex, Anti-Vertex), all in degrees/day.

    Notes:
        - At polar latitudes the same fallback doctrine as
          :func:`calculate_houses` applies to all three evaluations
          (t−dt, t, t+dt).  If policy raises on polar fallback, all three
          evaluations will raise.
        - SUNSHINE houses require no special handling here; :func:`calculate_houses`
          imports and calls ``sun_longitude`` internally for all three evaluations.
        - The cusp-speed for house 1 is numerically equal to
          ``asc_speed_deg_per_day`` (both derive from the same longitude);
          house 4 speed equals −mc_speed_deg_per_day for most quadrant systems.
          These redundancies are intentional for uniformity.
    """
    h_m = calculate_houses(jd_ut - dt, latitude, longitude, system, policy=policy)
    h0  = calculate_houses(jd_ut,      latitude, longitude, system, policy=policy)
    h_p = calculate_houses(jd_ut + dt, latitude, longitude, system, policy=policy)

    cusp_speeds = tuple(
        CuspSpeed(
            house=n + 1,
            cusp_longitude=h0.cusps[n],
            speed_deg_per_day=_wrapped_longitude_speed(h_m.cusps[n], h_p.cusps[n], dt),
        )
        for n in range(12)
    )

    return HouseDynamics(
        house_cusps=h0,
        cusp_speeds=cusp_speeds,
        asc_speed_deg_per_day=_wrapped_longitude_speed(h_m.asc, h_p.asc, dt),
        mc_speed_deg_per_day=_wrapped_longitude_speed(h_m.mc, h_p.mc, dt),
        vertex_speed_deg_per_day=_wrapped_longitude_speed(h_m.vertex, h_p.vertex, dt),
        anti_vertex_speed_deg_per_day=_wrapped_longitude_speed(h_m.anti_vertex, h_p.anti_vertex, dt),
    )


def house_dynamics_from_armc(
    armc: float,
    obliquity: float,
    lat: float,
    system: str = HouseSystem.PLACIDUS,
    *,
    policy: HousePolicy | None = None,
    sun_longitude: float | None = None,
    darmc_deg: float = _SIDEREAL_ROTATION_DEG_PER_DAY / 1440.0,
) -> HouseDynamics:
    """
    Compute cusp and angle speeds directly from ARMC and obliquity.

    This is the ARMC-native companion to :func:`cusp_speeds_at`. It exists for
    specialist workflows that already operate in ARMC space, such as primary
    directions or externally prepared house frames.

    Method:
        A centred finite difference is applied over ``ARMC ± darmc_deg`` using
        :func:`houses_from_armc`, with obliquity held fixed. The resulting
        derivative in degrees per degree-of-ARMC is converted to degrees/day
        using the mean sidereal rotation rate of Earth.

    Important limitation:
        Unlike :func:`cusp_speeds_at`, this surface does not know the chart
        epoch, so it cannot model the very small day-scale drift of obliquity.
        It is therefore an ARMC-native dynamical approximation, not an
        epoch-complete time derivative.

    Args:
        armc: Apparent Right Ascension of the Midheaven in degrees.
        obliquity: True obliquity of the ecliptic in degrees.
        lat: Geographic latitude in degrees.
        system: House system identifier.
        policy: House fallback doctrine.
        sun_longitude: Required when ``system == HouseSystem.SUNSHINE``.
        darmc_deg: Half-step in ARMC degrees for the finite difference.
            The default corresponds to one sidereal minute of Earth rotation.

    Returns:
        A :class:`HouseDynamics` vessel with cusp and angle speeds in degrees/day.

    Raises:
        ValueError: If ``darmc_deg <= 0``.
        ValueError: If the requested system/policy combination raises inside
            :func:`houses_from_armc`.
    """
    if darmc_deg <= 0.0:
        raise ValueError("darmc_deg must be positive")

    h_m = houses_from_armc(
        armc - darmc_deg,
        obliquity,
        lat,
        system,
        policy=policy,
        sun_longitude=sun_longitude,
    )
    h0 = houses_from_armc(
        armc,
        obliquity,
        lat,
        system,
        policy=policy,
        sun_longitude=sun_longitude,
    )
    h_p = houses_from_armc(
        armc + darmc_deg,
        obliquity,
        lat,
        system,
        policy=policy,
        sun_longitude=sun_longitude,
    )

    def _speed_from_armc(lon_m: float, lon_p: float) -> float:
        return (
            _wrapped_longitude_speed(lon_m, lon_p, darmc_deg)
            * _SIDEREAL_ROTATION_DEG_PER_DAY
        )

    cusp_speeds = tuple(
        CuspSpeed(
            house=n + 1,
            cusp_longitude=h0.cusps[n],
            speed_deg_per_day=_speed_from_armc(h_m.cusps[n], h_p.cusps[n]),
        )
        for n in range(12)
    )

    return HouseDynamics(
        house_cusps=h0,
        cusp_speeds=cusp_speeds,
        asc_speed_deg_per_day=_speed_from_armc(h_m.asc, h_p.asc),
        mc_speed_deg_per_day=_speed_from_armc(h_m.mc, h_p.mc),
        vertex_speed_deg_per_day=_speed_from_armc(h_m.vertex, h_p.vertex),
        anti_vertex_speed_deg_per_day=_speed_from_armc(h_m.anti_vertex, h_p.anti_vertex),
    )


# ===========================================================================
# RUDHYAR QUADRANT EMPHASIS  (Phase 4)
# ===========================================================================
#
# Dane Rudhyar — *The Astrology of Personality* (1936),
#                *The Astrological Houses* (1972)
#
# The chart is divided into four quadrants by the ASC–DSC and MC–IC axes:
#
#   Q1 (Spring)  houses 1–3   ASC → IC      personal / instinctive
#   Q2 (Summer)  houses 4–6   IC  → DSC     personal / subjective
#   Q3 (Autumn)  houses 7–9   DSC → MC      social / relational
#   Q4 (Winter)  houses 10–12 MC  → ASC     social / universal
#
# The analytical product is a quadrant emphasis profile: how many planets
# (or other chart points) occupy each quadrant.
# ===========================================================================

class Quadrant(str, Enum):
    """Rudhyar's four developmental quadrants."""

    Q1 = "Q1"  # houses 1–3   personal / instinctive
    Q2 = "Q2"  # houses 4–6   personal / subjective
    Q3 = "Q3"  # houses 7–9   social / relational
    Q4 = "Q4"  # houses 10–12 social / universal


_HOUSE_TO_QUADRANT: dict[int, Quadrant] = {
    1: Quadrant.Q1,  2: Quadrant.Q1,  3: Quadrant.Q1,
    4: Quadrant.Q2,  5: Quadrant.Q2,  6: Quadrant.Q2,
    7: Quadrant.Q3,  8: Quadrant.Q3,  9: Quadrant.Q3,
    10: Quadrant.Q4, 11: Quadrant.Q4, 12: Quadrant.Q4,
}


def quadrant_of(house: int) -> Quadrant:
    """Return the Rudhyar quadrant for a house number (1–12)."""
    if house < 1 or house > 12:
        raise ValueError(f"house must be 1–12, got {house}")
    return _HOUSE_TO_QUADRANT[house]


@dataclass(frozen=True, slots=True)
class QuadrantEmphasisProfile:
    """
    Rudhyar quadrant emphasis analysis over a set of chart points.

    Fields
    ------
    house_cusps : HouseCusps
        The house frame used for placement.
    point_count : int
        Total number of points placed.
    q1_count, q2_count, q3_count, q4_count : int
        Number of points in each quadrant.
    q1_points, q2_points, q3_points, q4_points : tuple[str, ...]
        Names of points in each quadrant, preserving input order.
    dominant_quadrant : tuple[Quadrant, ...]
        Quadrant(s) with the highest count (ties included).
        Empty tuple when point_count == 0.
    eastern_count : int
        Points in the eastern hemisphere (Q1 + Q4, houses 10–3).
    western_count : int
        Points in the western hemisphere (Q2 + Q3, houses 4–9).
    northern_count : int
        Points in the northern hemisphere (Q1 + Q2, houses 1–6).
    southern_count : int
        Points in the southern hemisphere (Q3 + Q4, houses 7–12).
    """

    house_cusps:        HouseCusps
    point_count:        int
    q1_count:           int
    q2_count:           int
    q3_count:           int
    q4_count:           int
    q1_points:          tuple[str, ...]
    q2_points:          tuple[str, ...]
    q3_points:          tuple[str, ...]
    q4_points:          tuple[str, ...]
    dominant_quadrant:  tuple[Quadrant, ...]
    eastern_count:      int
    western_count:      int
    northern_count:     int
    southern_count:     int

    def __post_init__(self) -> None:
        total = self.q1_count + self.q2_count + self.q3_count + self.q4_count
        if total != self.point_count:
            raise ValueError("quadrant counts must sum to point_count")
        if self.eastern_count + self.western_count != self.point_count:
            raise ValueError("hemisphere counts must sum to point_count")
        if self.northern_count + self.southern_count != self.point_count:
            raise ValueError("hemisphere counts must sum to point_count")


def quadrant_emphasis(
    points: dict[str, float],
    house_cusps: HouseCusps,
) -> QuadrantEmphasisProfile:
    """
    Compute the Rudhyar quadrant emphasis profile for a set of named points.

    Parameters
    ----------
    points : dict[str, float]
        Mapping of point name to ecliptic longitude (degrees).
        Example: {"Sun": 120.5, "Moon": 245.3, "Mars": 15.0}
    house_cusps : HouseCusps
        The house frame to use for placement.

    Returns
    -------
    QuadrantEmphasisProfile
    """
    buckets: dict[Quadrant, list[str]] = {
        Quadrant.Q1: [], Quadrant.Q2: [], Quadrant.Q3: [], Quadrant.Q4: [],
    }

    for name, lon in points.items():
        placement = assign_house(lon, house_cusps)
        q = quadrant_of(placement.house)
        buckets[q].append(name)

    q1 = tuple(buckets[Quadrant.Q1])
    q2 = tuple(buckets[Quadrant.Q2])
    q3 = tuple(buckets[Quadrant.Q3])
    q4 = tuple(buckets[Quadrant.Q4])

    counts = {
        Quadrant.Q1: len(q1),
        Quadrant.Q2: len(q2),
        Quadrant.Q3: len(q3),
        Quadrant.Q4: len(q4),
    }
    point_count = sum(counts.values())

    if point_count == 0:
        dominant: tuple[Quadrant, ...] = ()
    else:
        max_count = max(counts.values())
        dominant = tuple(q for q in Quadrant if counts[q] == max_count)

    return QuadrantEmphasisProfile(
        house_cusps=house_cusps,
        point_count=point_count,
        q1_count=counts[Quadrant.Q1],
        q2_count=counts[Quadrant.Q2],
        q3_count=counts[Quadrant.Q3],
        q4_count=counts[Quadrant.Q4],
        q1_points=q1,
        q2_points=q2,
        q3_points=q3,
        q4_points=q4,
        dominant_quadrant=dominant,
        eastern_count=counts[Quadrant.Q1] + counts[Quadrant.Q4],
        western_count=counts[Quadrant.Q2] + counts[Quadrant.Q3],
        northern_count=counts[Quadrant.Q1] + counts[Quadrant.Q2],
        southern_count=counts[Quadrant.Q3] + counts[Quadrant.Q4],
    )


# ===========================================================================
# DIURNAL QUADRANTS  (Phase 5)
# ===========================================================================
#
# The diurnal quadrant system divides the sky by the actual daily rotation
# of each body through the four angles (ASC, MC, DSC, IC).
#
#   DQ1  ASC → MC   eastern sky, above horizon, rising toward culmination
#   DQ2  MC  → DSC  western sky, above horizon, descending toward setting
#   DQ3  DSC → IC   western sky, below horizon, descending toward nadir
#   DQ4  IC  → ASC  eastern sky, below horizon, ascending toward rising
#
# The boundaries are defined by the body's own semi-diurnal arc (SDA):
#
#   cos(SDA) = −tan(δ) · tan(φ)
#
# where δ is the body's declination and φ is the geographic latitude.
# SDA gives the hour-angle at rising/setting.
#
# Hour angle (HA) = ARMC − RA, measured 0–360° westward from the MC.
#
# This is the framework underlying Gauquelin sectors, classical angularity,
# hayz above/below-horizon tests, and mundane aspects.
# ===========================================================================

class DiurnalQuadrant(str, Enum):
    """
    The four diurnal quadrants defined by the angular frame
    and the body's semi-diurnal arc.
    """

    DQ1 = "DQ1"  # ASC → MC   (eastern, above horizon)
    DQ2 = "DQ2"  # MC  → DSC  (western, above horizon)
    DQ3 = "DQ3"  # DSC → IC   (western, below horizon)
    DQ4 = "DQ4"  # IC  → ASC  (eastern, below horizon)


def _semi_diurnal_arc(dec: float, geo_lat: float) -> float:
    """
    Compute the semi-diurnal arc (SDA) in degrees.

    Returns:
        SDA in degrees [0, 180].
        180 if circumpolar (never sets).
        0 if body never rises.
    """
    tan_dec = math.tan(dec * DEG2RAD)
    tan_lat = math.tan(geo_lat * DEG2RAD)
    cos_sda = -(tan_dec * tan_lat)
    if cos_sda <= -1.0:
        return 180.0   # circumpolar — always above horizon
    if cos_sda >= 1.0:
        return 0.0     # never rises — always below horizon
    return math.acos(cos_sda) * RAD2DEG


@dataclass(frozen=True, slots=True)
class DiurnalPosition:
    """
    A body's position within the diurnal quadrant framework.

    Fields
    ------
    quadrant : DiurnalQuadrant
        Which diurnal quadrant the body occupies.
    hour_angle : float
        Hour angle in degrees [0, 360), measured westward from MC.
        0° = on MC, SDA = on DSC, 180° = on IC, 360−SDA = on ASC.
    semi_diurnal_arc : float
        The body's half-arc above the horizon (degrees, 0–180).
        180° for circumpolar bodies, 0° for never-rising bodies.
    semi_nocturnal_arc : float
        The body's half-arc below the horizon (degrees, 0–180).
        = 180° − semi_diurnal_arc.
    fraction : float
        Proportional position within the current quadrant, 0.0 at the
        entry angle and 1.0 at the exit angle.
    is_above_horizon : bool
        True if the body is above the horizon (DQ1 or DQ2).
    is_eastern : bool
        True if the body is in the eastern sky (DQ1 or DQ4).
    is_circumpolar : bool
        True if the body never sets at this latitude/declination.
    is_never_rises : bool
        True if the body never rises at this latitude/declination.
    ra : float
        Right ascension used in computation (degrees, 0–360).
    dec : float
        Declination used in computation (degrees).
    """

    quadrant:           DiurnalQuadrant
    hour_angle:         float
    semi_diurnal_arc:   float
    semi_nocturnal_arc: float
    fraction:           float
    is_above_horizon:   bool
    is_eastern:         bool
    is_circumpolar:     bool
    is_never_rises:     bool
    ra:                 float
    dec:                float


def diurnal_position(
    ecl_lon: float,
    ecl_lat: float,
    armc: float,
    obliquity: float,
    geo_lat: float,
) -> DiurnalPosition:
    """
    Compute a body's diurnal quadrant position.

    Parameters
    ----------
    ecl_lon : float
        Ecliptic longitude (degrees).
    ecl_lat : float
        Ecliptic latitude (degrees).  ~0 for most planets, nonzero for Moon.
    armc : float
        Local sidereal time as right ascension of the midheaven (degrees).
    obliquity : float
        Obliquity of the ecliptic (degrees).
    geo_lat : float
        Geographic latitude of the observer (degrees, north positive).

    Returns
    -------
    DiurnalPosition
    """
    ra, dec = _ecl_to_eq(ecl_lon, ecl_lat, obliquity)
    sda = _semi_diurnal_arc(dec, geo_lat)
    sna = 180.0 - sda

    ha = (armc - ra) % 360.0

    circumpolar  = (sda >= 180.0)
    never_rises  = (sda <= 0.0)

    # Determine quadrant and proportional fraction.
    # HA measured 0–360 westward from MC:
    #   [0, SDA)          → DQ2  (MC → DSC)
    #   [SDA, 180)        → DQ3  (DSC → IC)
    #   [180, 360−SDA)    → DQ4  (IC → ASC)
    #   [360−SDA, 360)    → DQ1  (ASC → MC)
    #
    # Circumpolar (SDA=180): only DQ1 and DQ2 exist.
    # Never-rises (SDA=0): only DQ3 and DQ4 exist.

    if circumpolar:
        # Always above horizon; split at HA=180 conceptually,
        # but true quadrant boundary is MC: DQ1 for HA > 180, DQ2 for HA ≤ 180.
        if ha <= 180.0:
            quadrant = DiurnalQuadrant.DQ2
            fraction = ha / 180.0 if sda > 0 else 0.0
        else:
            quadrant = DiurnalQuadrant.DQ1
            fraction = (ha - 180.0) / 180.0
    elif never_rises:
        # Always below horizon; split at IC (HA=180).
        if ha < 180.0:
            quadrant = DiurnalQuadrant.DQ3
            fraction = ha / 180.0
        else:
            quadrant = DiurnalQuadrant.DQ4
            fraction = (ha - 180.0) / 180.0
    else:
        asc_ha = 360.0 - sda  # hour angle at ASC
        if ha < sda:
            # DQ2: MC → DSC
            quadrant = DiurnalQuadrant.DQ2
            fraction = ha / sda
        elif ha < 180.0:
            # DQ3: DSC → IC
            quadrant = DiurnalQuadrant.DQ3
            fraction = (ha - sda) / sna if sna > 0 else 0.0
        elif ha < asc_ha:
            # DQ4: IC → ASC
            quadrant = DiurnalQuadrant.DQ4
            fraction = (ha - 180.0) / sna if sna > 0 else 0.0
        else:
            # DQ1: ASC → MC
            quadrant = DiurnalQuadrant.DQ1
            fraction = (ha - asc_ha) / sda

    above = quadrant in (DiurnalQuadrant.DQ1, DiurnalQuadrant.DQ2)
    eastern = quadrant in (DiurnalQuadrant.DQ1, DiurnalQuadrant.DQ4)

    return DiurnalPosition(
        quadrant=quadrant,
        hour_angle=ha,
        semi_diurnal_arc=sda,
        semi_nocturnal_arc=sna,
        fraction=max(0.0, min(1.0, fraction)),
        is_above_horizon=above,
        is_eastern=eastern,
        is_circumpolar=circumpolar,
        is_never_rises=never_rises,
        ra=ra,
        dec=dec,
    )


@dataclass(frozen=True, slots=True)
class DiurnalEmphasisProfile:
    """
    Chart-wide diurnal quadrant distribution.

    Fields
    ------
    point_count : int
        Total number of points placed.
    dq1_count, dq2_count, dq3_count, dq4_count : int
        Number of points in each diurnal quadrant.
    dq1_points, dq2_points, dq3_points, dq4_points : tuple[str, ...]
        Names of points in each diurnal quadrant.
    positions : dict[str, DiurnalPosition]
        Per-point DiurnalPosition, keyed by name.
    dominant_quadrant : tuple[DiurnalQuadrant, ...]
        Quadrant(s) with the highest count (ties included).
    above_horizon_count : int
        Points in DQ1 + DQ2.
    below_horizon_count : int
        Points in DQ3 + DQ4.
    eastern_count : int
        Points in DQ1 + DQ4.
    western_count : int
        Points in DQ2 + DQ3.
    """

    point_count:          int
    dq1_count:            int
    dq2_count:            int
    dq3_count:            int
    dq4_count:            int
    dq1_points:           tuple[str, ...]
    dq2_points:           tuple[str, ...]
    dq3_points:           tuple[str, ...]
    dq4_points:           tuple[str, ...]
    positions:            dict[str, DiurnalPosition]
    dominant_quadrant:    tuple[DiurnalQuadrant, ...]
    above_horizon_count:  int
    below_horizon_count:  int
    eastern_count:        int
    western_count:        int

    def __post_init__(self) -> None:
        total = self.dq1_count + self.dq2_count + self.dq3_count + self.dq4_count
        if total != self.point_count:
            raise ValueError("diurnal quadrant counts must sum to point_count")


def diurnal_emphasis(
    points: dict[str, tuple[float, float]],
    armc: float,
    obliquity: float,
    geo_lat: float,
) -> DiurnalEmphasisProfile:
    """
    Compute the diurnal quadrant emphasis for a set of named bodies.

    Parameters
    ----------
    points : dict[str, tuple[float, float]]
        Mapping of point name to (ecliptic_longitude, ecliptic_latitude).
        Example: {"Sun": (280.5, 0.0), "Moon": (120.3, 5.1)}
    armc : float
        Right ascension of the midheaven (degrees).
    obliquity : float
        Obliquity of the ecliptic (degrees).
    geo_lat : float
        Geographic latitude (degrees, north positive).

    Returns
    -------
    DiurnalEmphasisProfile
    """
    buckets: dict[DiurnalQuadrant, list[str]] = {
        DiurnalQuadrant.DQ1: [], DiurnalQuadrant.DQ2: [],
        DiurnalQuadrant.DQ3: [], DiurnalQuadrant.DQ4: [],
    }
    positions: dict[str, DiurnalPosition] = {}

    for name, (lon, lat) in points.items():
        pos = diurnal_position(lon, lat, armc, obliquity, geo_lat)
        positions[name] = pos
        buckets[pos.quadrant].append(name)

    dq1 = tuple(buckets[DiurnalQuadrant.DQ1])
    dq2 = tuple(buckets[DiurnalQuadrant.DQ2])
    dq3 = tuple(buckets[DiurnalQuadrant.DQ3])
    dq4 = tuple(buckets[DiurnalQuadrant.DQ4])

    counts = {
        DiurnalQuadrant.DQ1: len(dq1), DiurnalQuadrant.DQ2: len(dq2),
        DiurnalQuadrant.DQ3: len(dq3), DiurnalQuadrant.DQ4: len(dq4),
    }
    point_count = sum(counts.values())

    if point_count == 0:
        dominant: tuple[DiurnalQuadrant, ...] = ()
    else:
        max_count = max(counts.values())
        dominant = tuple(dq for dq in DiurnalQuadrant if counts[dq] == max_count)

    return DiurnalEmphasisProfile(
        point_count=point_count,
        dq1_count=counts[DiurnalQuadrant.DQ1],
        dq2_count=counts[DiurnalQuadrant.DQ2],
        dq3_count=counts[DiurnalQuadrant.DQ3],
        dq4_count=counts[DiurnalQuadrant.DQ4],
        dq1_points=dq1,
        dq2_points=dq2,
        dq3_points=dq3,
        dq4_points=dq4,
        positions=positions,
        dominant_quadrant=dominant,
        above_horizon_count=counts[DiurnalQuadrant.DQ1] + counts[DiurnalQuadrant.DQ2],
        below_horizon_count=counts[DiurnalQuadrant.DQ3] + counts[DiurnalQuadrant.DQ4],
        eastern_count=counts[DiurnalQuadrant.DQ1] + counts[DiurnalQuadrant.DQ4],
        western_count=counts[DiurnalQuadrant.DQ2] + counts[DiurnalQuadrant.DQ3],
    )
