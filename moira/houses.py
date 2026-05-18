"""
Moira — houses.py
Purpose:
    This Pillar provides the House Engine: ecliptic house cusp computation for
    all supported house systems using ARMC, obliquity, and geographic
    coordinates.

House system implementations in this file include code derived from swehouse.c from Swiss Ephemeris, used with permission of its authors, Dieter Koch and Alois Treindl.

Boundary:
    Owns the full pipeline from raw Julian date and observer coordinates to a
    populated HouseCusps result vessel. Delegates time conversion to julian,
    obliquity and nutation to obliquity, local sidereal time to julian, and
    coordinate normalisation to coordinates. Does not own planet positions,
    aspect detection, chart assembly, or display formatting.

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
            (Placidus, Koch) clamp the acos() domain error but return
            astronomically invalid cusp orderings for a large fraction of ARMC
            values above this threshold.  The old fixed 75.0° threshold was wrong:
            it silently passed garbage results from ≈66.6° to 74.9°.
            Systems not in _POLAR_SYSTEMS are evaluated on their own geometry.

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
Public surface / exports:
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
    - Solar-anchored house systems may resolve the Sun's longitude through the
      narrow solar-anchor Engine when that longitude is not supplied explicitly.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum

from .constants import DEG2RAD, RAD2DEG, HouseSystem, sign_of
from .coordinates import normalize_degrees
from .julian import local_sidereal_time, ut_to_tt, greenwich_mean_sidereal_time
from .obliquity import true_obliquity, nutation
from ._solar import _solar_longitude

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
    "DerivedHouseCusps",
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
    "derived_houses",
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


def _require(condition: bool, message: str, exc_type: type[Exception] = ValueError) -> None:
    """Raise a concrete runtime exception when an invariant is violated."""

    if not condition:
        raise exc_type(message)


def _finalize_cusps(cusps: list[float], *, context: str) -> list[float]:
    """Validate cusp vector shape and numeric sanity, then normalize to [0, 360)."""
    _require(len(cusps) == 12, f"{context}: expected 12 cusps, got {len(cusps)}")

    out: list[float] = []
    for i, value in enumerate(cusps, start=1):
        _require(math.isfinite(value), f"{context}: cusp {i} is not finite: {value!r}")
        out.append(value % 360.0)
    return out


# ===========================================================================
# CLASSIFICATION LAYER
# ===========================================================================

class HouseSystemFamily(str, Enum):
    """
    RITE: The Family Seal

    THEOREM: This enum records the doctrinal family to which a house system belongs.

    RITE OF PURPOSE:
        This enum exists so broad house-system identity can remain explicit and
        stable across classification, policy, and comparison work. It preserves
        the high-level doctrinal grouping of systems as executable truth rather
        than leaving that identity implicit in comments or call-site logic.

    LAW OF OPERATION:
        Responsibilities:
            - Declare the canonical house-system family labels.
            - Preserve stable doctrinal grouping values for classification work.
        Non-responsibilities:
            - Does not compute cusps.
            - Does not classify specific system codes on its own.
        Dependencies:
            - House classification doctrine in this Pillar.
        Side effects:
            - None
        Failure behavior:
            - None

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "type": "enum",
      "owns_state": false,
      "mutates_external_state": false,
      "requires": [],
      "guarantees": ["stable house-family taxonomy"]
    }
    """
    EQUAL      = "equal"
    QUADRANT   = "quadrant"
    WHOLE_SIGN = "whole_sign"
    SOLAR      = "solar"


class HouseSystemCuspBasis(str, Enum):
    """
    RITE: The Cusp Basis Seal

    THEOREM: This enum records the computational basis used to derive intermediate house cusps.

    RITE OF PURPOSE:
        This enum exists so cusp-generation method can remain explicit in the
        doctrinal surface of the House Pillar. It preserves the underlying
        projection or division basis as stable categorical truth for
        classification and comparison work.

    LAW OF OPERATION:
        Responsibilities:
            - Declare the canonical cusp-basis labels.
            - Preserve stable computational-basis values for classification work.
        Non-responsibilities:
            - Does not compute cusp positions.
            - Does not choose among competing bases.
        Dependencies:
            - House classification doctrine in this Pillar.
        Side effects:
            - None
        Failure behavior:
            - None

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "type": "enum",
      "owns_state": false,
      "mutates_external_state": false,
      "requires": [],
      "guarantees": ["stable cusp-basis taxonomy"]
    }
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
    RITE: The House Doctrine Sigil

    THEOREM: This dataclass records the doctrinal family and computational basis of one declared house system code.

    RITE OF PURPOSE:
        This vessel exists so the House Pillar can attach explicit doctrinal
        identity to a computed house figure without forcing callers to infer
        method from cusp values alone. It preserves family, projection basis,
        latitude sensitivity, and polar capability as first-class truth.
        Without it, fallback auditing and system comparison would be forced to
        reason from code strings or numeric output alone.

    LAW OF OPERATION:
        Responsibilities:
            - Record the doctrinal family of a house system code.
            - Record the cusp-basis doctrine used for intermediate cusps.
            - Record latitude sensitivity and polar capability truth.
        Non-responsibilities:
            - Does not compute cusps.
            - Does not choose fallback policy.
            - Does not compare or rank house systems.
        Dependencies:
            - HouseSystemFamily and HouseSystemCuspBasis enumerations.
            - Classification table declarations in this Pillar.
        Structural invariants:
            - All fields are derivable from the declared system code alone.
            - No field depends on chart time, location, or computed cusp values.
        Side effects:
            - None
        Failure behavior:
            - None at the vessel level; validation occurs where codes are classified.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "type": "classification_vessel",
      "owns_state": true,
      "mutates_external_state": false,
      "requires": ["family", "cusp_basis", "latitude_sensitive", "polar_capable"],
      "guarantees": ["immutable doctrinal record", "code-derived semantics only"]
    }
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
    HouseSystem.KRUSINSKI:     HouseSystemClassification(_F.QUADRANT,   _CB.GREAT_CIRCLE,        True,  True),
    HouseSystem.APC:           HouseSystemClassification(_F.QUADRANT,   _CB.APC_FORMULA,         True,  True),
    HouseSystem.SUNSHINE:      HouseSystemClassification(_F.SOLAR,      _CB.SOLAR_POSITION,      False, True),
    HouseSystem.SOLAR_SIGN:    HouseSystemClassification(_F.SOLAR,      _CB.ECLIPTIC,            False, True),
}

def classify_house_system(code: str) -> HouseSystemClassification:
    """
    Return the HouseSystemClassification for the given HouseSystem code.

    The classification describes the algorithm associated with that code ?
    its doctrinal family, cusp-projection basis, latitude sensitivity, and
    polar capability. It is derived entirely from the code string; no chart
    data or observer coordinates are needed.

    When ``code`` is not a recognised HouseSystem constant, this raises
    ``ValueError``. Classification is a property of a declared, known system
    code, not of a downstream fallback policy.

    Args:
        code: A HouseSystem constant string (for example ``HouseSystem.PLACIDUS``).

    Returns:
        A frozen HouseSystemClassification for that code.

    Raises:
        ValueError: If ``code`` is not a recognised HouseSystem constant.

    Side effects:
        None
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
_POLAR_SYSTEMS: frozenset[str] = frozenset({
    HouseSystem.PLACIDUS, HouseSystem.KOCH,
})

# The full set of recognised HouseSystem codes.
_KNOWN_SYSTEMS: frozenset[str] = frozenset({
    HouseSystem.WHOLE_SIGN, HouseSystem.EQUAL, HouseSystem.PORPHYRY,
    HouseSystem.PLACIDUS, HouseSystem.KOCH, HouseSystem.CAMPANUS,
    HouseSystem.REGIOMONTANUS, HouseSystem.ALCABITIUS, HouseSystem.MORINUS,
    HouseSystem.TOPOCENTRIC, HouseSystem.MERIDIAN, HouseSystem.VEHLOW,
    HouseSystem.SUNSHINE, HouseSystem.SOLAR_SIGN, HouseSystem.AZIMUTHAL, HouseSystem.CARTER,
    HouseSystem.KRUSINSKI,
    HouseSystem.APC,
})


# ===========================================================================
# DOCTRINE / POLICY LAYER
# ===========================================================================

class UnknownSystemPolicy(str, Enum):
    """
    RITE: The Unknown-System Policy Seal

    THEOREM: This enum records the fallback doctrine used when a requested house system code is unknown.

    RITE OF PURPOSE:
        This enum exists so unknown-system behavior is declared as explicit
        policy rather than hidden control flow. It preserves the caller's
        doctrine for unknown codes as a stable categorical choice.

    LAW OF OPERATION:
        Responsibilities:
            - Declare the canonical unknown-system fallback modes.
        Non-responsibilities:
            - Does not perform fallback itself.
            - Does not validate known system codes.
        Dependencies:
            - House policy doctrine in this Pillar.
        Side effects:
            - None
        Failure behavior:
            - None

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "type": "enum",
      "owns_state": false,
      "mutates_external_state": false,
      "requires": [],
      "guarantees": ["stable unknown-system policy taxonomy"]
    }
    """
    FALLBACK_TO_PLACIDUS = "fallback_to_placidus"
    RAISE                = "raise"


class PolarFallbackPolicy(str, Enum):
    """
    RITE: The Polar Policy Seal

    THEOREM: This enum records the fallback doctrine used when a requested house system is polar-incapable at the given latitude.

    RITE OF PURPOSE:
        This enum exists so polar fallback behavior is declared as explicit
        policy rather than buried in control flow. It preserves the caller's
        doctrine for critical-latitude requests as a stable categorical choice.

    LAW OF OPERATION:
        Responsibilities:
            - Declare the canonical polar fallback modes.
        Non-responsibilities:
            - Does not perform cusp computation or fallback itself.
            - Does not determine whether a system is polar-capable.
        Dependencies:
            - House policy doctrine in this Pillar.
        Side effects:
            - None
        Failure behavior:
            - None

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "type": "enum",
      "owns_state": false,
      "mutates_external_state": false,
      "requires": [],
      "guarantees": ["stable polar-fallback policy taxonomy"]
    }
    """
    FALLBACK_TO_PORPHYRY = "fallback_to_porphyry"
    RAISE                = "raise"
    EXPERIMENTAL_SEARCH  = "experimental_search"


@dataclass(frozen=True, slots=True)
class HousePolicy:
    """
    RITE: The House Policy Seal

    THEOREM: This dataclass records the fallback doctrine governing one house computation request.

    RITE OF PURPOSE:
        This vessel exists so fallback behavior is declared before any house
        mathematics run, rather than emerging from hidden defaults or ambient
        control flow. It preserves the caller's unknown-system and polar
        fallback doctrine as auditable input truth.
        Without it, fallback semantics would be implicit and harder to test.

    LAW OF OPERATION:
        Responsibilities:
            - Record unknown-system doctrine.
            - Record polar fallback doctrine.
            - Provide canonical default, strict, and experimental policy constructors.
        Non-responsibilities:
            - Does not compute cusps.
            - Does not classify house systems.
            - Does not decide doctrinal ranking among valid systems.
        Dependencies:
            - UnknownSystemPolicy and PolarFallbackPolicy enumerations.
        Structural invariants:
            - Fields always express doctrine only, never computed state.
        Side effects:
            - None
        Failure behavior:
            - None at the vessel level; enforcement occurs in the House Engine.

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

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "type": "policy_vessel",
      "owns_state": true,
      "mutates_external_state": false,
      "requires": ["unknown_system", "polar_fallback"],
      "guarantees": ["immutable fallback doctrine", "constructor-stable defaults"]
    }
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


def _normalize_house_policy(policy: HousePolicy | None) -> HousePolicy:
    """Return a validated house policy, defaulting when omitted."""

    if policy is None:
        return HousePolicy.default()
    _require(isinstance(policy, HousePolicy), "policy must be a HousePolicy", TypeError)
    return policy


def _experimental_polar_placidus_cusps(
    armc: float,
    obliquity: float,
    latitude: float,
    asc: float,
    mc: float,
) -> list[float]:
    """Search for a unique ordered high-latitude Placidus branch or raise."""
    experimental_placidus = _experimental_placidus_module()

    result = experimental_placidus.search_experimental_placidus(
        armc,
        obliquity,
        latitude,
        asc,
        mc,
    )
    if (
        result.status == experimental_placidus.ExperimentalPlacidusStatus.UNIQUE_ORDERED_SOLUTION
        and result.cusps is not None
    ):
        return list(result.cusps)
    raise ValueError(f"experimental Placidus search failed: {result.diagnostic_summary}")


def _experimental_placidus_module():
    """Return the experimental high-latitude Placidus module on explicit demand."""
    from . import experimental_placidus

    return experimental_placidus


def _solar_house_anchor_longitude(jd_ut: float) -> float:
    """
    Return the solar longitude used to anchor SUNSHINE / SOLAR_SIGN houses.

    Side effects:
        - None in this Pillar; delegates the longitude resolution to the
          internal solar longitude Engine.

    Raises:
        - Propagates any exception raised by the delegated solar longitude Engine.
    """
    return _solar_longitude(jd_ut)


@dataclass(slots=True, frozen=True)
class HouseCusps:
    """
    RITE: The Zodiacal House Vessel

    THEOREM: This dataclass carries one fully computed house figure, its angular anchors, and the fallback doctrine that governed its creation.

    RITE OF PURPOSE:
        This vessel exists so the House Pillar returns a complete truth object
        rather than a loose tuple of angles. It preserves requested versus
        effective system identity, fallback visibility, classification truth,
        and the angular frame needed by downstream astrological technique.
        Without it, callers would lose provenance and invariant enforcement at
        the boundary of the House Engine.

    LAW OF OPERATION:
        Responsibilities:
            - Store the twelve cusp longitudes and angular anchors.
            - Preserve requested-system truth alongside effective-system truth.
            - Preserve classification and policy truth for later audit.
            - Enforce structural invariants at construction time.
        Non-responsibilities:
            - Does not compute cusps.
            - Does not assign points to houses.
            - Does not derive angularity, distribution, or comparison products.
        Dependencies:
            - Valid cusp vectors produced by the House Engine.
            - HouseSystemClassification and HousePolicy inputs.
        Structural invariants:
            - Exactly 12 cusps are present.
            - Quadrant-family systems except HORIZON open house 1 at ASC.
            - Fallback truth matches requested versus effective system truth.
            - Classification is present when effective_system is declared.
        Behavioral invariants:
            - Requested system truth is never collapsed into effective system truth.
        Side effects:
            - None
        Failure behavior:
            - Raises ValueError or TypeError through invariant enforcement when
              the vessel is constructed with inconsistent data.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "type": "result_vessel",
      "owns_state": true,
      "mutates_external_state": false,
      "requires": ["12 cusp longitudes", "asc", "mc", "armc", "system truth", "policy truth"],
      "guarantees": ["construction-time invariants", "requested/effective distinction", "audit-ready fallback metadata"]
    }
    """
    system:           str
    cusps:            tuple[float, ...]    # 12 ecliptic longitudes, degrees [0,360)
    asc:              float                # Ascendant
    mc:               float                # Midheaven
    armc:             float                # ARMC (Right Ascension of MC)
    east_point:       float | None = None  # East Point / Equatorial Ascendant (ARMC+90° projected at 0° latitude)
    vertex:           float | None = None  # Vertex (western prime-vertical / ecliptic intersection)
    anti_vertex:      float | None = None  # Anti-Vertex (opposite Vertex)
    effective_system: str                          = ""      # House system code actually used for computation
    fallback:         bool                         = False   # True iff effective_system != system
    fallback_reason:  str | None                   = None    # Why fallback occurred; None when fallback is False
    classification:   HouseSystemClassification | None = None  # Doctrinal classification of effective_system
    policy:           HousePolicy = field(default_factory=HousePolicy.default)  # Policy that governed fallback resolution

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
        object.__setattr__(self, "cusps", tuple(self.cusps))
        _require(
            len(self.cusps) == 12,
            f"HouseCusps invariant violated: len(cusps)={len(self.cusps)}, expected 12",
        )
        if (
            self.cusps
            and self.classification is not None
            and self.classification.family == HouseSystemFamily.QUADRANT
            and self.classification.cusp_basis != HouseSystemCuspBasis.HORIZON
        ):
            diff = abs(self.cusps[0] - self.asc) % 360.0
            _require(
                diff < 1e-9 or abs(diff - 360.0) < 1e-9,
                f"HouseCusps invariant violated: quadrant system "
                f"cusps[0]={self.cusps[0]:.9f} != asc={self.asc:.9f}",
            )
        if self.effective_system:
            _require(
                self.fallback == (self.system != self.effective_system),
                f"HouseCusps invariant violated: fallback={self.fallback} but "
                f"system={self.system!r}, effective_system={self.effective_system!r}",
            )
        _require(
            (self.fallback_reason is None) == (not self.fallback),
            f"HouseCusps invariant violated: fallback={self.fallback} but "
            f"fallback_reason={self.fallback_reason!r}",
        )
        if self.effective_system:
            _require(
                self.classification is not None,
                f"HouseCusps invariant violated: effective_system={self.effective_system!r} "
                f"is set but classification is None",
            )
        _require(
            isinstance(self.policy, HousePolicy),
            "HouseCusps invariant violated: policy must be a HousePolicy",
            TypeError,
        )

    def sign_of_cusp(self, house: int) -> tuple[str, str, float]:
        """Return (sign, symbol, degree_within_sign) for house 1–12."""
        return sign_of(self.cusps[house - 1])


# ---------------------------------------------------------------------------
# Derived / turned houses
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class DerivedHouseCusps:
    """
    RITE: The Turned Wheel Vessel

    THEOREM: This dataclass records a derived house wheel formed by rotating a natal house figure so a chosen cusp becomes house 1.

    RITE OF PURPOSE:
        This vessel exists so turned-house technique can preserve its pivot
        doctrine and natal provenance without recomputing any astronomy. It
        lets downstream callers work with a stable derived wheel while keeping
        the originating HouseCusps visible. Without it, turned-house logic
        would have to travel as unnamed tuples.

    LAW OF OPERATION:
        Responsibilities:
            - Store the pivot house and rotated cusp sequence.
            - Preserve the originating HouseCusps vessel.
            - Enforce that derived house 1 equals the chosen natal pivot cusp.
        Non-responsibilities:
            - Does not compute new astronomy.
            - Does not alter the underlying natal figure.
        Dependencies:
            - A valid HouseCusps vessel.
        Structural invariants:
            - pivot_house is in 1..12.
            - Exactly 12 cusps are present.
            - cusps[0] equals source.cusps[pivot_house - 1].
        Side effects:
            - None
        Failure behavior:
            - Raises ValueError when pivot or rotated cusp shape is inconsistent.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "type": "derived_result_vessel",
      "owns_state": true,
      "mutates_external_state": false,
      "requires": ["pivot_house", "12 rotated cusps", "origin HouseCusps"],
      "guarantees": ["pivot-cusp alignment", "immutable derived wheel"]
    }
    """

    pivot_house: int
    cusps:       tuple[float, ...]
    source:      HouseCusps

    def __post_init__(self) -> None:
        if not 1 <= self.pivot_house <= 12:
            raise ValueError(
                f"DerivedHouseCusps: pivot_house must be 1–12, got {self.pivot_house}"
            )
        if len(self.cusps) != 12:
            raise ValueError(
                f"DerivedHouseCusps: expected 12 cusps, got {len(self.cusps)}"
            )
        expected = self.source.cusps[self.pivot_house - 1]
        if abs(self.cusps[0] - expected) % 360.0 > 1e-9:
            raise ValueError(
                f"DerivedHouseCusps: cusps[0]={self.cusps[0]:.9f} does not match "
                f"source.cusps[{self.pivot_house - 1}]={expected:.9f}"
            )

    def sign_of_cusp(self, house: int) -> tuple[str, str, float]:
        """Return (sign, symbol, degree_within_sign) for derived house 1–12."""
        return sign_of(self.cusps[house - 1])


def derived_houses(house_cusps: HouseCusps, from_house: int) -> DerivedHouseCusps:
    """
    Rotate the natal house wheel so that ``from_house`` becomes house 1.

    No astronomical computation is performed. The function operates entirely
    on the cusp longitudes already present in ``house_cusps``.

    Args:
        house_cusps: The natal house wheel to rotate.
        from_house: Natal house number (1?12) that becomes the new first house.
            House 1 returns the original wheel unchanged.

    Returns:
        A frozen DerivedHouseCusps vessel whose ``cusps[n-1]`` is the opening
        cusp of derived house ``n`` and whose ``cusps[0]`` equals
        ``house_cusps.cusps[from_house - 1]``.

    Raises:
        ValueError: If ``from_house`` is not in 1?12.

    Side effects:
        None
    """
    if not 1 <= from_house <= 12:
        raise ValueError(f"derived_houses: from_house must be 1–12, got {from_house}")
    offset = from_house - 1
    rotated = tuple(house_cusps.cusps[(offset + i) % 12] for i in range(12))
    return DerivedHouseCusps(pivot_house=from_house, cusps=rotated, source=house_cusps)


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
    Using ``atan2(sin(ARMC), cos(ARMC) * cos(eps))`` preserves the correct
    quadrant for all four quadrants of ARMC.

    Reference: Meeus, *Astronomical Algorithms*, ?24.

    Raises:
        None under normal operation.

    Side effects:
        None
    """
    armc_r = armc * DEG2RAD
    eps_r  = obliquity * DEG2RAD
    return math.atan2(math.sin(armc_r), math.cos(armc_r) * math.cos(eps_r)) * RAD2DEG % 360.0


def _mc_above_horizon(mc: float, obliquity: float, lat: float) -> float:
    """
    Return the visible MC branch when a quadrant system requires it above the horizon.

    At extreme latitudes, the standard HA=0 MC may lie below the horizon.
    Some quadrant systems require the geometrically accessible branch, while
    simpler systems preserve the traditional MC without swapping.

    Raises:
        None under normal operation.

    Side effects:
        None
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

    ``atan2`` yields two candidate solutions 180? apart; the Ascendant is the
    one whose ecliptic longitude falls in the same semicircle as ``ARMC + 90?``,
    the approximate right ascension of the eastern horizon.

    Raises:
        None under normal operation.

    Side effects:
        None
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


def _dot3(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    """3D dot product for internal spherical geometry helpers."""
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross3(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
) -> tuple[float, float, float]:
    """3D cross product for internal spherical geometry helpers."""
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _normalize3(v: tuple[float, float, float]) -> tuple[float, float, float]:
    """Return the unit vector of ``v`` or raise on degeneracy."""
    norm = math.sqrt(_dot3(v, v))
    _require(norm > 0.0, "degenerate vector in house geometry helper")
    return (v[0] / norm, v[1] / norm, v[2] / norm)


def _ecliptic_north_vector(obliquity_deg: float) -> tuple[float, float, float]:
    """
    Unit normal of the ecliptic plane in equatorial coordinates.

    The ecliptic is the equatorial plane rotated about the x-axis by the
    obliquity, so its north pole is ``(0, -sin eps, cos eps)``.

    Raises:
        None under normal operation.

    Side effects:
        None
    """
    eps_r = obliquity_deg * DEG2RAD
    return (0.0, -math.sin(eps_r), math.cos(eps_r))


def _ra_pole_plane_normal(
    ra_deg: float,
    pole_height_deg: float,
) -> tuple[float, float, float]:
    """
    Plane normal for the RA-plus-pole construction in equatorial coordinates.

    The cusp plane satisfies ``-sin(RA) * x + cos(RA) * y - tan(pole) * z = 0``.
    Intersecting this plane with the ecliptic plane yields the projected cusp
    direction used by several house systems.

    Raises:
        ValueError: If the constructed plane normal degenerates.

    Side effects:
        None
    """
    ra_r = ra_deg * DEG2RAD
    pole_r = pole_height_deg * DEG2RAD
    return _normalize3((
        -math.sin(ra_r),
        math.cos(ra_r),
        -math.tan(pole_r),
    ))


def _equatorial_ecliptic_direction(lon_deg: float, obliquity_deg: float) -> tuple[float, float, float]:
    """Unit ecliptic direction at longitude ``lon_deg``, expressed in equatorial axes."""
    lon_r = lon_deg * DEG2RAD
    eps_r = obliquity_deg * DEG2RAD
    sin_lon = math.sin(lon_r)
    return (
        math.cos(lon_r),
        sin_lon * math.cos(eps_r),
        sin_lon * math.sin(eps_r),
    )


def _ecliptic_longitude_from_equatorial_vector(
    v: tuple[float, float, float],
    obliquity_deg: float,
) -> float:
    """
    Recover ecliptic longitude from an equatorial-space vector.

    Rotating the vector by ``-obliquity`` about the x-axis maps it into the
    ecliptic frame, where longitude is recovered by the usual ``atan2(y, x)``.

    Raises:
        ValueError: If ``v`` is degenerate and cannot be normalized.

    Side effects:
        None
    """
    x_eq, y_eq, z_eq = _normalize3(v)
    eps_r = obliquity_deg * DEG2RAD
    y_ecl = y_eq * math.cos(eps_r) + z_eq * math.sin(eps_r)
    return math.atan2(y_ecl, x_eq) * RAD2DEG % 360.0


def _in_forward_arc(lon: float, start: float, end: float) -> bool:
    """Return True iff ``lon`` lies in the forward arc [start, end) on the circle."""
    return (lon - start) % 360.0 < (end - start) % 360.0


def _circular_distance(a: float, b: float) -> float:
    """Unsigned shortest circular distance in degrees."""
    return abs((a - b + 180.0) % 360.0 - 180.0)


def _select_antipodal_branch(lon: float, arc_start: float, arc_end: float) -> float:
    """
    Resolve an antipodal cusp ambiguity against a doctrinal zodiacal arc.

    Polar-capable house systems can produce two ecliptic intersections 180?
    apart. Moira chooses the branch that lies in the intended forward arc
    opened by the visible angles; midpoint proximity is only a deterministic
    tie-breaker for near-boundary numerical cases.

    Raises:
        None under normal operation.

    Side effects:
        None
    """
    lon_alt = (lon + 180.0) % 360.0
    if _in_forward_arc(lon, arc_start, arc_end):
        return lon
    if _in_forward_arc(lon_alt, arc_start, arc_end):
        return lon_alt

    span = (arc_end - arc_start) % 360.0
    target = (arc_start + span / 2.0) % 360.0
    if _circular_distance(lon, target) <= _circular_distance(lon_alt, target):
        return lon
    return lon_alt


def _assemble_antipodal_quadrant_cusps(
    *,
    asc: float,
    mc: float,
    h2: float,
    h3: float,
    h11: float,
    h12: float,
    context: str,
) -> list[float]:
    """
    Build a quadrant-style house figure from its primary cusps.

    Doctrine:
        - Cardinal anchors are ASC, IC, DSC, and MC.
        - Primary intermediates are H11/H12 above the horizon and H2/H3 below.
        - Opposite houses are derived by antipodal symmetry, not recomputed.

    Raises:
        ValueError: If the assembled cusp figure fails final structural checks.

    Side effects:
        None
    """
    ic = (mc + 180.0) % 360.0
    dsc = (asc + 180.0) % 360.0

    cusps = [0.0] * 12
    cusps[0] = asc
    cusps[1] = h2
    cusps[2] = h3
    cusps[3] = ic
    cusps[6] = dsc
    cusps[9] = mc
    cusps[10] = h11
    cusps[11] = h12

    opposite_pairs = (
        (10, 4),  # H11 -> H5
        (11, 5),  # H12 -> H6
        (1, 7),   # H2  -> H8
        (2, 8),   # H3  -> H9
    )
    for source, target in opposite_pairs:
        cusps[target] = (cusps[source] + 180.0) % 360.0

    return _finalize_cusps(cusps, context=context)


def _local_horizon_basis(
    armc_deg: float,
    latitude_deg: float,
) -> tuple[
    tuple[float, float, float],
    tuple[float, float, float],
    tuple[float, float, float],
]:
    """
    Return the local horizon basis vectors in equatorial axes.

    The returned basis is ``(east, north, zenith)`` for the observer defined by
    ``armc_deg`` and ``latitude_deg``.

    Raises:
        None under normal operation.

    Side effects:
        None
    """
    phi = latitude_deg * DEG2RAD
    theta = armc_deg * DEG2RAD
    sin_theta = math.sin(theta)
    cos_theta = math.cos(theta)

    east = (-sin_theta, cos_theta, 0.0)
    north = (
        -math.sin(phi) * cos_theta,
        -math.sin(phi) * sin_theta,
        math.cos(phi),
    )
    zenith = (
        math.cos(phi) * cos_theta,
        math.cos(phi) * sin_theta,
        math.sin(phi),
    )
    return east, north, zenith


def _ecliptic_intersection_candidates(
    plane_normal: tuple[float, float, float],
    obliquity_deg: float,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    """
    Return the antipodal ecliptic-intersection directions of a cusp plane.

    Raises:
        ValueError: If the plane/ecliptic intersection degenerates.

    Side effects:
        None
    """
    primary = _normalize3(_cross3(plane_normal, _ecliptic_north_vector(obliquity_deg)))
    return primary, (-primary[0], -primary[1], -primary[2])


def _select_horizon_branch(
    primary: tuple[float, float, float],
    secondary: tuple[float, float, float],
    *,
    zenith: tuple[float, float, float],
    prefer_above_horizon: bool,
    obliquity_deg: float,
    tie_arc_start: float | None = None,
    tie_arc_end: float | None = None,
) -> float:
    """
    Select the antipodal ecliptic branch by local-horizon hemisphere.

    Campanus-family cusp circles distinguish their upper and lower branches by
    whether the selected intersection lies above or below the horizon. The
    zodiacal arc is used only as a deterministic tie-breaker for horizon-grazing
    numerical cases.

    Raises:
        ValueError: If neither candidate satisfies the requested hemisphere and
            no deterministic tie-break is available.

    Side effects:
        None
    """
    height_primary = _dot3(_normalize3(primary), zenith)
    height_secondary = _dot3(_normalize3(secondary), zenith)
    lon_primary = _ecliptic_longitude_from_equatorial_vector(primary, obliquity_deg)
    lon_secondary = _ecliptic_longitude_from_equatorial_vector(secondary, obliquity_deg)
    eps = 1e-12

    if prefer_above_horizon:
        if height_primary > eps and height_secondary < -eps:
            return lon_primary
        if height_secondary > eps and height_primary < -eps:
            return lon_secondary
    else:
        if height_primary < -eps and height_secondary > eps:
            return lon_primary
        if height_secondary < -eps and height_primary > eps:
            return lon_secondary

    if tie_arc_start is not None and tie_arc_end is not None:
        return _select_antipodal_branch(lon_primary, tie_arc_start, tie_arc_end)

    raise ValueError("local-horizon branch selection degenerated at the horizon")


def _horizon_direction_from_azimuth(
    azimuth_deg: float,
    *,
    east: tuple[float, float, float],
    north: tuple[float, float, float],
) -> tuple[float, float, float]:
    """
    Return the unit horizon direction for a local azimuth.

    Raises:
        None under normal operation.

    Side effects:
        None
    """
    az = azimuth_deg * DEG2RAD
    return _normalize3((
        math.sin(az) * east[0] + math.cos(az) * north[0],
        math.sin(az) * east[1] + math.cos(az) * north[1],
        math.sin(az) * east[2] + math.cos(az) * north[2],
    ))


def _local_azimuth_of_direction(
    direction: tuple[float, float, float],
    *,
    east: tuple[float, float, float],
    north: tuple[float, float, float],
) -> float:
    """
    Return the local horizon azimuth of ``direction`` in degrees.

    Raises:
        ValueError: If ``direction`` is degenerate.

    Side effects:
        None
    """
    unit = _normalize3(direction)
    return math.atan2(_dot3(unit, east), _dot3(unit, north)) * RAD2DEG % 360.0


def _select_azimuth_branch(
    primary: tuple[float, float, float],
    secondary: tuple[float, float, float],
    *,
    azimuth_deg: float,
    east: tuple[float, float, float],
    north: tuple[float, float, float],
    obliquity_deg: float,
) -> float:
    """
    Select the antipodal ecliptic branch whose local azimuth best matches the target.

    Raises:
        None under normal operation.

    Side effects:
        None
    """
    az_primary = _local_azimuth_of_direction(primary, east=east, north=north)
    az_secondary = _local_azimuth_of_direction(secondary, east=east, north=north)
    diff_primary = abs((az_primary - azimuth_deg + 180.0) % 360.0 - 180.0)
    diff_secondary = abs((az_secondary - azimuth_deg + 180.0) % 360.0 - 180.0)
    chosen = primary if diff_primary <= diff_secondary else secondary
    return _ecliptic_longitude_from_equatorial_vector(chosen, obliquity_deg)


def _project_pole_height_cusp(
    *,
    ra_deg: float,
    pole_height_deg: float,
    obliquity_deg: float,
    zenith: tuple[float, float, float],
    prefer_above_horizon: bool,
    tie_arc_start: float,
    tie_arc_end: float,
) -> float:
    """
    Project a pole-height cusp plane and select the visible antipodal branch.

    This is the canonical branch doctrine for the pole-height family:
    construct the equatorial cusp plane, intersect it with the ecliptic, then
    choose the above-horizon or below-horizon branch as required by the house
    figure. The zodiacal arc is used only as a deterministic tie-breaker for
    horizon-grazing numerical cases.

    Raises:
        ValueError: Propagated if the cusp plane degenerates.

    Side effects:
        None
    """
    plane_normal = _ra_pole_plane_normal(ra_deg % 360.0, pole_height_deg)
    primary, secondary = _ecliptic_intersection_candidates(plane_normal, obliquity_deg)
    return _select_horizon_branch(
        primary,
        secondary,
        zenith=zenith,
        prefer_above_horizon=prefer_above_horizon,
        obliquity_deg=obliquity_deg,
        tie_arc_start=tie_arc_start,
        tie_arc_end=tie_arc_end,
    )


def _assemble_pole_height_quadrant_family(
    *,
    armc_deg: float,
    asc: float,
    mc: float,
    obliquity_deg: float,
    latitude_deg: float,
    cusp_specs: dict[int, tuple[float, float]],
    context: str,
) -> list[float]:
    """
    Assemble a quadrant figure from pole-height equatorial cusp specifications.

    ``cusp_specs`` maps house numbers ``{2, 3, 11, 12}`` to
    ``(right_ascension_deg, pole_height_deg)`` pairs.

    Raises:
        ValueError: Propagated if cusp projection or final assembly fails.

    Side effects:
        None
    """
    ic = (mc + 180.0) % 360.0
    _east, _north, zenith = _local_horizon_basis(armc_deg, latitude_deg)

    primaries = {
        2: _project_pole_height_cusp(
            ra_deg=cusp_specs[2][0],
            pole_height_deg=cusp_specs[2][1],
            obliquity_deg=obliquity_deg,
            zenith=zenith,
            prefer_above_horizon=False,
            tie_arc_start=asc,
            tie_arc_end=ic,
        ),
        3: _project_pole_height_cusp(
            ra_deg=cusp_specs[3][0],
            pole_height_deg=cusp_specs[3][1],
            obliquity_deg=obliquity_deg,
            zenith=zenith,
            prefer_above_horizon=False,
            tie_arc_start=asc,
            tie_arc_end=ic,
        ),
        11: _project_pole_height_cusp(
            ra_deg=cusp_specs[11][0],
            pole_height_deg=cusp_specs[11][1],
            obliquity_deg=obliquity_deg,
            zenith=zenith,
            prefer_above_horizon=True,
            tie_arc_start=mc,
            tie_arc_end=asc,
        ),
        12: _project_pole_height_cusp(
            ra_deg=cusp_specs[12][0],
            pole_height_deg=cusp_specs[12][1],
            obliquity_deg=obliquity_deg,
            zenith=zenith,
            prefer_above_horizon=True,
            tie_arc_start=mc,
            tie_arc_end=asc,
        ),
    }

    return _assemble_antipodal_quadrant_cusps(
        asc=asc,
        mc=mc,
        h2=primaries[2],
        h3=primaries[3],
        h11=primaries[11],
        h12=primaries[12],
        context=context,
    )


def _assemble_direct_zero_pole_quadrant_family(
    *,
    asc: float,
    mc: float,
    obliquity_deg: float,
    cusp_ras: dict[int, float],
    context: str,
) -> list[float]:
    """
    Assemble a quadrant figure from direct zero-pole equatorial cusp right ascensions.

    This is the exact zero-pole member of the pole-height family. The cusp
    right ascensions are projected directly to the ecliptic without horizon
    hemisphere branch arbitration, then assembled through antipodal symmetry.

    Raises:
        ValueError: Propagated if cusp projection or final assembly fails.

    Side effects:
        None
    """
    primaries = {
        house_index: _project_ra_with_pole(ra_deg % 360.0, 0.0, obliquity_deg)
        for house_index, ra_deg in cusp_ras.items()
    }
    return _assemble_antipodal_quadrant_cusps(
        asc=asc,
        mc=mc,
        h2=primaries[2],
        h3=primaries[3],
        h11=primaries[11],
        h12=primaries[12],
        context=context,
    )


def _koch_pole_height_specs(
    armc_deg: float,
    mc_deg: float,
    obliquity_deg: float,
    latitude_deg: float,
) -> dict[int, tuple[float, float]]:
    """
    Return Koch pole-height family cusp specifications for houses 2, 3, 11, and 12.

    Governing objects:
        - MC as unit vector in equatorial space, derived from its ecliptic longitude.
          Its z-component is sin(dec_MC); its equatorial magnitude is cos(dec_MC).
        - Observer's zenith as unit vector in equatorial space.
          Its z-component is sin(lat); its equatorial magnitude is cos(lat).

    The diurnal semi-arc of the MC declination circle is derived from the
    horizon constraint dot(v, zenith) = 0 at constant declination, giving
    cos(DSA) = -tan(dec_MC)*tan(lat), expressed here entirely through the
    governing vector components without intermediate angle formulas.

    Each cusp is returned as (right_ascension_deg, pole_height_deg) where
    pole_height_deg = latitude_deg (full observer's latitude for Koch).

    Raises:
        None under normal operation.

    Side effects:
        None
    """
    # Governing object 1: MC as unit vector in equatorial space
    v_mc = _equatorial_ecliptic_direction(mc_deg, obliquity_deg)

    # Governing object 2: Observer's zenith as unit vector in equatorial space
    _, _, zenith = _local_horizon_basis(armc_deg, latitude_deg)

    # Equatorial horizontal magnitudes extracted from the governing vectors
    cos_dec_mc = math.hypot(v_mc[0], v_mc[1])
    cos_lat = math.hypot(zenith[0], zenith[1])

    # Horizon arc product: tan(dec_MC)*tan(lat) from governing vector components.
    # This is the shared scalar that drives both DSA and the ascensional difference:
    #   cos(DSA) = -horizon_product,  sin(AD) = horizon_product.
    if cos_dec_mc > 0.0 and cos_lat > 0.0:
        horizon_product = max(-1.0, min(1.0, (v_mc[2] * zenith[2]) / (cos_dec_mc * cos_lat)))
    else:
        horizon_product = 0.0

    dsa_deg = math.degrees(math.acos(-horizon_product))
    ad_mc = math.degrees(math.asin(horizon_product))

    oa_mc = armc_deg - ad_mc
    oa_ic = (armc_deg + 180.0) + ad_mc
    return {
        2: (oa_ic - 2.0 * dsa_deg / 3.0, latitude_deg),
        3: (oa_ic - dsa_deg / 3.0, latitude_deg),
        11: (oa_mc + dsa_deg / 3.0, latitude_deg),
        12: (oa_mc + 2.0 * dsa_deg / 3.0, latitude_deg),
    }


def _alcabitius_zero_pole_specs(
    armc_deg: float,
    asc_deg: float,
    obliquity_deg: float,
    latitude_deg: float,
) -> dict[int, float]:
    """
    Return Alcabitius zero-pole equatorial cusp right ascensions for the quadrant primaries.

    Governing objects:
        - Ascendant as unit vector in equatorial space, derived from its ecliptic longitude.
          Its z-component is sin(dec_ASC); its equatorial magnitude is cos(dec_ASC).
        - Observer's zenith as unit vector in equatorial space.
          Its z-component is sin(lat); its equatorial magnitude is cos(lat).

    The semi-diurnal arc of the Ascendant declination circle is derived from the
    horizon constraint dot(v, zenith) = 0 at constant declination, giving
    cos(SDA) = -tan(dec_ASC)*tan(lat), expressed here entirely through the
    governing vector components without intermediate angle formulas.

    The returned mapping expresses Alcabitius as direct equatorial sector
    right ascensions with zero pole height, preserving its exact direct
    projection doctrine while making the governing objects explicit.

    Raises:
        None under normal operation.

    Side effects:
        None
    """
    # Governing object 1: Ascendant as unit vector in equatorial space
    v_asc = _equatorial_ecliptic_direction(asc_deg, obliquity_deg)

    # Governing object 2: Observer's zenith as unit vector in equatorial space
    _, _, zenith = _local_horizon_basis(armc_deg, latitude_deg)

    # Equatorial horizontal magnitudes extracted from the governing vectors
    cos_dec_asc = math.hypot(v_asc[0], v_asc[1])
    cos_lat = math.hypot(zenith[0], zenith[1])

    # Horizon arc product: -tan(dec_ASC)*tan(lat) from governing vector components.
    # cos(SDA) = -tan(dec_ASC)*tan(lat) = -(v_asc[2]*zenith[2]) / (cos_dec*cos_lat).
    if cos_dec_asc > 0.0 and cos_lat > 0.0:
        r = max(-1.0, min(1.0, -(v_asc[2] * zenith[2]) / (cos_dec_asc * cos_lat)))
    else:
        r = 0.0

    sda_deg = math.degrees(math.acos(r))
    sna_deg = 180.0 - sda_deg
    return {
        2: armc_deg + 180.0 - 2.0 * sna_deg / 3.0,
        3: armc_deg + 180.0 - sna_deg / 3.0,
        11: armc_deg + sda_deg / 3.0,
        12: armc_deg + 2.0 * sda_deg / 3.0,
    }


def _project_ra_with_pole(ra_deg: float, pole_height_deg: float, obliquity_deg: float) -> float:
    """
    Project equatorial right ascension to ecliptic longitude with an arbitrary pole height.

    Moira owns this as an explicit geometric construction: build the cusp
    plane, intersect it with the ecliptic plane, and convert the resulting
    ecliptic direction back to tropical longitude.

    Raises:
        ValueError: If the cusp-plane or ecliptic intersection degenerates.

    Side effects:
        None
    """
    plane_normal = _ra_pole_plane_normal(ra_deg, pole_height_deg)
    ecliptic_north = _ecliptic_north_vector(obliquity_deg)
    intersection = _cross3(plane_normal, ecliptic_north)
    return _ecliptic_longitude_from_equatorial_vector(intersection, obliquity_deg)


def _quadrant_project_ra(ra_deg: float, pole_height_deg: float, obliquity_deg: float) -> float:
    """
    Quadrant-aware RA?ecliptic projection used by Campanus and Azimuthal surfaces.

    This helper handles polar singularities and keeps the projected longitude
    in the circular range.

    Raises:
        ValueError: Propagated if the delegated projection degenerates.

    Side effects:
        None
    """
    _EPS = 1e-10
    if abs(90.0 - pole_height_deg) < _EPS:
        return 180.0
    if abs(90.0 + pole_height_deg) < _EPS:
        return 0.0
    return _project_ra_with_pole(ra_deg, pole_height_deg, obliquity_deg)


def _project_ra_morinus(ra_deg: float, obliquity_deg: float) -> float:
    """
    Project equatorial right ascension to ecliptic longitude using the Morinus inverse relation.

    The governing identity is ``tan(lambda) = tan(RA) * cos(eps)``.

    Raises:
        None under normal operation.

    Side effects:
        None
    """
    ra_r = ra_deg * DEG2RAD
    eps_r = obliquity_deg * DEG2RAD
    y = math.sin(ra_r) * math.cos(eps_r)
    x = math.cos(ra_r)
    return math.atan2(y, x) * RAD2DEG % 360.0


def _project_ra_equatorial(ra_deg: float, obliquity_deg: float) -> float:
    """
    Project equatorial right ascension to the ecliptic along the equatorial plane.

    This is the pole-height-zero member of the equatorial-division family.

    Raises:
        ValueError: Propagated if the equatorial projection degenerates.

    Side effects:
        None
    """
    return _project_ra_with_pole(ra_deg, 0.0, obliquity_deg)


def _equatorial_division_cycle(
    anchor_ra_deg: float,
    obliquity_deg: float,
    projector,
) -> list[float]:
    """
    Project a full 12-house cycle of equal 30-degree equatorial divisions.

    The returned list is in house order, beginning at the projected longitude
    of ``anchor_ra_deg`` and advancing by equal right-ascension steps.

    Raises:
        ValueError: Propagated if the supplied projector degenerates.

    Side effects:
        None
    """
    return [
        projector((anchor_ra_deg + i * 30.0) % 360.0, obliquity_deg) % 360.0
        for i in range(12)
    ]


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
    """Return whole-sign house cusps anchored to the zodiac sign containing the Ascendant."""
    sign_start = int(asc / 30.0) * 30.0
    cusps = [(sign_start + i * 30.0) % 360.0 for i in range(12)]
    return _finalize_cusps(cusps, context="_whole_sign")


# ---------------------------------------------------------------------------
# Equal House
# ---------------------------------------------------------------------------

def _equal_house(asc: float) -> list[float]:
    """Return equal-house cusps in 30-degree steps measured forward from the Ascendant."""
    cusps = [(asc + i * 30.0) % 360.0 for i in range(12)]
    return _finalize_cusps(cusps, context="_equal_house")


# ---------------------------------------------------------------------------
# Porphyry
# ---------------------------------------------------------------------------

def _porphyry(asc: float, mc: float) -> list[float]:
    """
    Porphyry houses: trisect each of the four unequal quadrants.

    The quadrant spans ASC?IC, IC?DSC, DSC?MC, and MC?ASC are each divided
    into three equal ecliptic arcs, with the cardinal cusps fixed at ASC,
    IC, DSC, and MC.

    Raises:
        ValueError: If final cusp normalization detects an invalid figure.

    Side effects:
        None
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

    return _finalize_cusps(cusps, context="_porphyry")


# ---------------------------------------------------------------------------
# Placidus (iterative)
# ---------------------------------------------------------------------------


def _placidus_semi_arc_event(
    lam_rad: float,
    obliquity_deg: float,
    zenith: tuple[float, float, float],
) -> tuple[float, float]:
    """
    Return (DSA_rad, dDSA/dλ) for ecliptic longitude lam_rad.

    Governing event: the diurnal semi-arc of an ecliptic point is the arc of
    the equator swept from the point's upper culmination to its setting.  It is
    derived from the horizon event condition dot(v, zenith) = 0 at constant
    declination, giving cos(DSA) = -tan(dec)*tan(lat), expressed here entirely
    through the governing vector components of the ecliptic point and the
    local zenith.

    This is the event object that defines every Placidus cusp: the cusp at
    fraction frac is the ecliptic point that has traversed exactly frac of
    this arc from the local meridian.

    Raises:
        None under normal operation.

    Side effects:
        None
    """
    # Governing object 1: ecliptic point as unit vector in equatorial space
    v = _equatorial_ecliptic_direction(math.degrees(lam_rad), obliquity_deg)

    cos_dec = math.hypot(v[0], v[1])
    cos_lat = math.hypot(zenith[0], zenith[1])

    if cos_dec < 1e-12 or cos_lat < 1e-12:
        return math.pi / 2.0, 0.0

    # Horizon arc product: tan(dec)*tan(lat) from the governing vector components.
    # cos(DSA) = -tan(dec)*tan(lat) = -(v[2]*zenith[2]) / (cos_dec*cos_lat).
    horizon_product = max(-1.0, min(1.0, (v[2] * zenith[2]) / (cos_dec * cos_lat)))
    dsa = math.acos(-horizon_product)
    sin_dsa = math.sin(dsa)

    if sin_dsa < 1e-12:
        return dsa, 0.0

    # Derivative dDSA/dλ via chain rule on the horizon event condition:
    #   dv[2]/dλ = cos(λ)*sin(ε)  [z-component derivative of the governing vector]
    #   dδ/dλ   = dv[2]/dλ / cos(δ)
    #   dDSA/dλ = tan(φ)*sec²(δ) * dδ/dλ / sin(DSA)
    # tan(φ) = zenith[2] / cos_lat  [from the governing zenith vector]
    eps_r = obliquity_deg * DEG2RAD
    d_sin_dec_d_lam = math.cos(lam_rad) * math.sin(eps_r)
    d_dec_d_lam = d_sin_dec_d_lam / cos_dec
    tan_phi = zenith[2] / cos_lat
    d_dsa_d_lam = (tan_phi / (cos_dec * cos_dec) * d_dec_d_lam) / sin_dsa

    return dsa, d_dsa_d_lam


def _placidus(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    Placidus house cusps via Newton-Raphson root-finding on the semi-arc event condition.

    Governing event: ecliptic point λ is the cusp at fraction frac if it has
    traversed exactly frac of its diurnal semi-arc (upper cusps) or nocturnal
    semi-arc (lower cusps) from the local meridian:

        Upper: RA(λ) − ARMC  = frac · DSA(λ)
        Lower: IC_RA − RA(λ) = frac · NSA(λ)

    The semi-arc event condition is evaluated by _placidus_semi_arc_event using
    the ecliptic-point vector and the local zenith as governing objects.
    Root-finding is the execution method, not the governing ontology.

    Raises:
        ValueError: Propagated if iterative cusp construction fails structural checks.

    Side effects:
        None
    """
    eps    = obliquity * DEG2RAD
    armc_r = armc      * DEG2RAD
    ic_r   = armc_r + math.pi

    cos_eps = math.cos(eps)

    mc  = _mc_from_armc(armc, obliquity, lat)
    asc = _asc_from_armc(armc, obliquity, lat)

    # Governing object: observer's zenith as unit vector in equatorial space.
    # Passed to _placidus_semi_arc_event as the horizon normal for DSA evaluation.
    _, _, zenith = _local_horizon_basis(armc, lat)

    # Initial guess basis: RA(ASC) − ARMC = DSA(ASC) exactly, because the ASC
    # is on the eastern horizon by definition — it has traversed its full
    # diurnal arc from the MC meridian.  Using DSA(ASC) as the seed estimate
    # is strictly better than the equatorial approximation DSA ≈ π/2.
    _v_asc = _equatorial_ecliptic_direction(asc, obliquity)
    _ra_asc_r = math.atan2(_v_asc[1], _v_asc[0])
    _dsa_asc = (_ra_asc_r - armc_r) % (2.0 * math.pi)
    if _dsa_asc > math.pi:
        _dsa_asc = 2.0 * math.pi - _dsa_asc
    _nsa_asc = math.pi - _dsa_asc

    def _lam_to_ra(lam: float) -> float:
        """Ecliptic longitude λ (rad) → equatorial RA (rad), β = 0.

        Ecliptic Cartesian (cos λ, sin λ, 0) rotated by ε around x-axis:
            x_eq = cos λ,  y_eq = sin λ cos ε
        so RA = atan2(sin λ cos ε, cos λ).
        """
        return math.atan2(math.sin(lam) * cos_eps, math.cos(lam))

    def _ra_to_lam(ra: float) -> float:
        """Equatorial RA (rad) → ecliptic longitude λ (rad), β = 0.

        Inverse of _lam_to_ra: tan RA = tan λ · cos ε  →  tan λ = tan RA / cos ε
        so λ = atan2(sin RA, cos ε · cos RA).
        """
        return math.atan2(math.sin(ra), cos_eps * math.cos(ra))

    def _dra_d_lam(lam: float) -> float:
        """
        dRA/dλ for β = 0.

        RA = atan2(sin λ · cos ε, cos λ)

        By the atan2 chain rule with u = sin λ cos ε, v = cos λ:
          d(RA)/dλ = (v·du/dλ − u·dv/dλ) / (u² + v²)
                   = (cos λ · cos λ cos ε + sin λ cos ε · sin λ) / (sin²λ cos²ε + cos²λ)
                   = cos ε / (cos²λ + sin²λ · cos²ε)
        """
        sin_lam = math.sin(lam)
        cos_lam = math.cos(lam)
        den = cos_lam * cos_lam + sin_lam * sin_lam * cos_eps * cos_eps
        if abs(den) < 1e-15:
            return 1.0   # safe fallback at poles of the formula
        return cos_eps / den

    def _solve_upper(frac: float) -> float:
        """
        Solve the upper semi-arc event condition via Newton-Raphson.

        Event: RA(λ) − ARMC − frac·DSA(λ) = 0
        Returns ecliptic longitude in degrees [0, 360).

        Step clamping: Newton steps are clamped to ±60° to prevent the solver
        from crossing the atan2 branch cut and converging to the antipodal root.
        """
        _MAX_STEP = math.pi / 3.0   # 60°
        lam = _ra_to_lam(armc_r + frac * _dsa_asc)

        for _ in range(30):
            dsa, d_dsa = _placidus_semi_arc_event(lam, obliquity, zenith)
            ra_lam = _lam_to_ra(lam)
            ra_lam = armc_r + ((ra_lam - armc_r + math.pi) % (2.0 * math.pi) - math.pi)
            f  = ra_lam - armc_r - frac * dsa
            df = _dra_d_lam(lam) - frac * d_dsa
            if abs(df) < 1e-15:
                break
            step = max(-_MAX_STEP, min(_MAX_STEP, f / df))
            lam -= step
            if abs(step) < 1e-12:
                break

        return math.degrees(lam) % 360.0

    def _solve_lower(frac: float) -> float:
        """
        Solve the lower semi-arc event condition via Newton-Raphson.

        Event: RA(λ) − IC_RA + frac·NSA(λ) = 0  (NSA = π − DSA)
        Returns ecliptic longitude in degrees [0, 360).

        Step clamping: same branch-cut guard as _solve_upper.
        """
        _MAX_STEP = math.pi / 3.0   # 60°
        lam = _ra_to_lam(ic_r - frac * _nsa_asc)

        for _ in range(30):
            dsa, d_dsa = _placidus_semi_arc_event(lam, obliquity, zenith)
            nsa = math.pi - dsa
            ra_lam = _lam_to_ra(lam)
            ra_lam = ic_r + ((ra_lam - ic_r + math.pi) % (2.0 * math.pi) - math.pi)
            f  = ra_lam - ic_r + frac * nsa
            df = _dra_d_lam(lam) - frac * d_dsa
            if abs(df) < 1e-15:
                break
            step = max(-_MAX_STEP, min(_MAX_STEP, f / df))
            lam -= step
            if abs(step) < 1e-12:
                break

        return math.degrees(lam) % 360.0

    cusps = [0.0] * 12
    cusps[0]  = asc
    cusps[3]  = (mc  + 180.0) % 360.0
    cusps[6]  = (asc + 180.0) % 360.0
    cusps[9]  = mc

    cusps[10] = _solve_upper(1/3)    # H11: 1/3 DSA from MC toward ASC
    cusps[11] = _solve_upper(2/3)    # H12: 2/3 DSA from MC toward ASC
    cusps[2]  = _solve_lower(1/3)    # H3:  1/3 NSA from IC toward ASC
    cusps[1]  = _solve_lower(2/3)    # H2:  2/3 NSA from IC toward ASC

    cusps[4]  = (cusps[10] + 180.0) % 360.0   # H5
    cusps[5]  = (cusps[11] + 180.0) % 360.0   # H6
    cusps[7]  = (cusps[1]  + 180.0) % 360.0   # H8
    cusps[8]  = (cusps[2]  + 180.0) % 360.0   # H9

    return _finalize_cusps(cusps, context="_placidus")


# ---------------------------------------------------------------------------
# Koch
# ---------------------------------------------------------------------------

def _koch(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    Koch house cusps from oblique-ascension doctrine.

    Koch divides the ascensional difference from MC to ASC into equal temporal
    steps on the equator, then projects the resulting right ascensions back to
    the ecliptic.

    Raises:
        ValueError: Propagated if cusp assembly or normalization fails.

    Side effects:
        None
    """
    mc  = _mc_from_armc(armc, obliquity, lat)
    asc = _asc_from_armc(armc, obliquity, lat)
    return _assemble_pole_height_quadrant_family(
        armc_deg=armc,
        asc=asc,
        mc=mc,
        obliquity_deg=obliquity,
        latitude_deg=lat,
        cusp_specs=_koch_pole_height_specs(armc, mc, obliquity, lat),
        context="_koch",
    )


# ---------------------------------------------------------------------------
# Alcabitius
# ---------------------------------------------------------------------------

def _alcabitius(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    Alcabitius house cusps from semi-arc trisection.

    Alcabitius divides the semi-arcs of the Ascendant and Descendant into
    equal temporal parts, then projects the resulting right ascensions to the
    ecliptic.

    Raises:
        ValueError: Propagated if cusp projection or normalization fails.

    Side effects:
        None
    """
    mc  = _mc_from_armc(armc, obliquity, lat)
    asc = _asc_from_armc(armc, obliquity, lat)
    return _assemble_direct_zero_pole_quadrant_family(
        asc=asc,
        mc=mc,
        obliquity_deg=obliquity,
        cusp_ras=_alcabitius_zero_pole_specs(armc, asc, obliquity, lat),
        context="_alcabitius",
    )


# ---------------------------------------------------------------------------
# Morinus
# ---------------------------------------------------------------------------

def _morinus(armc: float, obliquity: float) -> list[float]:
    """
    Morinus houses from equal equatorial 30-degree divisions.

    Morinus steps right ascension uniformly from the ARMC and projects those
    divisions directly back to the ecliptic.

    Raises:
        ValueError: Propagated if final cusp normalization fails.

    Side effects:
        None
    """
    cusps = _equatorial_division_cycle((armc + 90.0) % 360.0, obliquity, _project_ra_morinus)
    return _finalize_cusps(cusps, context="_morinus")


# ---------------------------------------------------------------------------
# Campanus
# ---------------------------------------------------------------------------

def _campanus(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    Campanus houses from prime-vertical sector doctrine.

    Campanus divides the prime vertical into equal sectors and projects those
    vertical circles to the ecliptic through local horizon geometry.

    Raises:
        ValueError: Propagated if projection or cusp normalization fails.

    Side effects:
        None
    """
    mc_geometric = _mc_from_armc(armc, obliquity, lat)
    mc = _mc_above_horizon(mc_geometric, obliquity, lat)
    asc = _asc_from_armc(armc, obliquity, lat)
    ic = (mc + 180.0) % 360.0
    east, _north, zenith = _local_horizon_basis(armc, lat)

    def _campanus_cusp(
        alpha_deg: float,
        *,
        prefer_above_horizon: bool,
        tie_arc_start: float,
        tie_arc_end: float,
    ) -> float:
        alpha = alpha_deg * DEG2RAD
        plane_normal = _normalize3((
            math.cos(alpha) * east[0] + math.sin(alpha) * zenith[0],
            math.cos(alpha) * east[1] + math.sin(alpha) * zenith[1],
            math.cos(alpha) * east[2] + math.sin(alpha) * zenith[2],
        ))
        primary, secondary = _ecliptic_intersection_candidates(plane_normal, obliquity)
        return _select_horizon_branch(
            primary,
            secondary,
            zenith=zenith,
            prefer_above_horizon=prefer_above_horizon,
            obliquity_deg=obliquity,
            tie_arc_start=tie_arc_start,
            tie_arc_end=tie_arc_end,
        )

    return _assemble_antipodal_quadrant_cusps(
        asc=asc,
        mc=mc,
        h2=_campanus_cusp(60.0, prefer_above_horizon=False, tie_arc_start=asc, tie_arc_end=ic),
        h3=_campanus_cusp(30.0, prefer_above_horizon=False, tie_arc_start=asc, tie_arc_end=ic),
        h11=_campanus_cusp(150.0, prefer_above_horizon=True, tie_arc_start=mc, tie_arc_end=asc),
        h12=_campanus_cusp(120.0, prefer_above_horizon=True, tie_arc_start=mc, tie_arc_end=asc),
        context="_campanus",
    )


# ---------------------------------------------------------------------------
# Regiomontanus
# ---------------------------------------------------------------------------

def _regiomontanus(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    Regiomontanus houses from equal equatorial sectors and graduated pole-height projection.

    The celestial equator is divided into equal sectors from the meridian, and
    those sectors are projected to the ecliptic through pole-height doctrine.

    Raises:
        ValueError: Propagated if branch selection or cusp normalization fails.

    Side effects:
        None
    """
    mc_raw = _mc_from_armc(armc, obliquity, lat)
    mc  = _mc_above_horizon(mc_raw, obliquity, lat)
    asc = _asc_from_armc(armc, obliquity, lat)
    phi = lat * DEG2RAD

    phi_h1 = math.atan(math.tan(phi) * math.sin(30.0 * DEG2RAD))  # H11 & H3
    phi_h2 = math.atan(math.tan(phi) * math.sin(60.0 * DEG2RAD))  # H12 & H2

    return _assemble_pole_height_quadrant_family(
        armc_deg=armc,
        asc=asc,
        mc=mc,
        obliquity_deg=obliquity,
        latitude_deg=lat,
        cusp_specs={
            2: (armc + 120.0, phi_h2 * RAD2DEG),
            3: (armc + 150.0, phi_h1 * RAD2DEG),
            11: (armc + 30.0, phi_h1 * RAD2DEG),
            12: (armc + 60.0, phi_h2 * RAD2DEG),
        },
        context="_regiomontanus",
    )


def _meridian(armc: float, obliquity: float) -> list[float]:
    """
    Meridian system from equal equatorial 30-degree divisions anchored to house 1.

    Meridian shares the same equatorial division cycle as Morinus, but uses the
    equatorial-plane projector rather than the Morinus inverse relation.

    Raises:
        ValueError: Propagated if cusp projection or normalization fails.

    Side effects:
        None
    """
    cusps = _equatorial_division_cycle((armc + 90.0) % 360.0, obliquity, _project_ra_equatorial)
    return _finalize_cusps(cusps, context="_meridian")


# ---------------------------------------------------------------------------
# Vehlow Equal Houses
# ---------------------------------------------------------------------------

def _vehlow(asc: float) -> list[float]:
    """
    Vehlow equal houses centered on the Ascendant.

    Vehlow shifts the equal-house frame so the Ascendant lies at the midpoint
    of house 1 instead of on its opening cusp.

    Raises:
        ValueError: Propagated if final cusp normalization fails.

    Side effects:
        None
    """
    start = (asc - 15.0) % 360.0
    cusps = [(start + i * 30.0) % 360.0 for i in range(12)]
    return _finalize_cusps(cusps, context="_vehlow")


# ---------------------------------------------------------------------------
# Sunshine Houses (Makransky)
# ---------------------------------------------------------------------------

def _sunshine(sun_lon: float, lat: float, obliquity: float) -> list[float]:
    """
    Sunshine houses anchored directly to the Sun's exact longitude.

    The frame proceeds in equal 30-degree steps from the solar anchor rather
    than from the Ascendant.

    Raises:
        ValueError: Propagated if final cusp normalization fails.

    Side effects:
        None
    """
    cusps = [0.0] * 12
    cusps[11] = sun_lon % 360.0   # 12th house cusp = Sun
    for i in range(11):
        cusps[i] = (sun_lon + (i + 1) * 30.0) % 360.0
    return _finalize_cusps(cusps, context="_sunshine")


def _solar_sign(sun_lon: float) -> list[float]:
    """
    Traditional solar-sign frame.

    House 1 begins at 0? of the Sun's sign, and the remaining houses proceed
    by 30? sign succession from that sign anchor.

    Raises:
        ValueError: Propagated if final cusp normalization fails.

    Side effects:
        None
    """
    sign_start = math.floor((sun_lon % 360.0) / 30.0) * 30.0
    cusps = [(sign_start + i * 30.0) % 360.0 for i in range(12)]
    return _finalize_cusps(cusps, context="_solar_sign")


# ---------------------------------------------------------------------------
# Azimuthal (Horizontal) Houses
# ---------------------------------------------------------------------------

def _azimuthal(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    Horizontal or Azimuthal houses from explicit local-horizon geometry.

    Vertical great circles through the zenith at doctrinal horizon azimuths
    are intersected with the ecliptic, and the visible branch is selected for
    each cusp.

    Raises:
        ValueError: If local-horizon vectors degenerate or cusp normalization fails.

    Side effects:
        None
    """
    mc = _mc_from_armc(armc, obliquity, lat)
    ic = (mc + 180.0) % 360.0
    east, north, zenith = _local_horizon_basis(armc, lat)

    def _vertical_cusp(azimuth_deg: float) -> float:
        horizon_dir = _horizon_direction_from_azimuth(azimuth_deg, east=east, north=north)
        plane_normal = _normalize3(_cross3(zenith, horizon_dir))
        primary, secondary = _ecliptic_intersection_candidates(plane_normal, obliquity)
        return _select_azimuth_branch(
            primary,
            secondary,
            azimuth_deg=azimuth_deg,
            east=east,
            north=north,
            obliquity_deg=obliquity,
        )

    north_sequence = {
        11: 150.0,
        12: 120.0,
        1: 90.0,
        2: 60.0,
        3: 30.0,
    }
    south_sequence = {
        11: 30.0,
        12: 60.0,
        1: 90.0,
        2: 120.0,
        3: 150.0,
    }
    azimuths = north_sequence if lat > 0.0 else south_sequence
    if abs(lat) < 1e-12 and armc >= 180.0:
        azimuths = {house: (azimuth + 180.0) % 360.0 for house, azimuth in azimuths.items()}

    asc = _vertical_cusp(azimuths[1])
    dsc = (asc + 180.0) % 360.0

    cusps = [0.0] * 12
    cusps[0] = asc
    cusps[9] = mc
    cusps[3] = ic
    cusps[6] = dsc
    cusps[10] = _vertical_cusp(azimuths[11])  # H11
    cusps[11] = _vertical_cusp(azimuths[12])  # H12
    cusps[1] = _vertical_cusp(azimuths[2])    # H2
    cusps[2] = _vertical_cusp(azimuths[3])    # H3
    cusps[4] = (cusps[10] + 180.0) % 360.0
    cusps[5] = (cusps[11] + 180.0) % 360.0
    cusps[7] = (cusps[1] + 180.0) % 360.0
    cusps[8] = (cusps[2] + 180.0) % 360.0

    return _finalize_cusps(cusps, context="_azimuthal")


# ---------------------------------------------------------------------------
# Carter Poly-Ptolemaic
# ---------------------------------------------------------------------------

def _carter(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    Carter Poly-Ptolemaic houses from equatorial 30-degree stepping anchored to RA(ASC).

    The construction steps right ascension uniformly from the Ascendant's
    equatorial longitude and projects each step back to the ecliptic.

    Raises:
        ValueError: Propagated if cusp projection or normalization fails.

    Side effects:
        None
    """
    mc    = _mc_from_armc(armc, obliquity, lat)
    asc   = _asc_from_armc(armc, obliquity, lat)

    # Polar correction: if ASC is on wrong side of MC, swap to DSC
    asc_mc_offset = ((asc - mc + 180.0) % 360.0) - 180.0
    if asc_mc_offset < 0.0:
        asc = (asc + 180.0) % 360.0

    # RA of Ascendant: ecliptic (lat=0) → equatorial
    asc_r  = asc * DEG2RAD
    eps_r  = obliquity * DEG2RAD
    ra_asc = math.atan2(math.sin(asc_r) * math.cos(eps_r), math.cos(asc_r)) * RAD2DEG % 360.0

    cycle = _equatorial_division_cycle(ra_asc, obliquity, _project_ra_equatorial)

    cusps = [0.0] * 12
    cusps[0] = asc
    cusps[1] = cycle[1]
    cusps[2] = cycle[2]
    cusps[3] = (mc  + 180.0) % 360.0
    cusps[6] = (asc + 180.0) % 360.0
    cusps[9] = cycle[9]
    cusps[10] = cycle[10]
    cusps[11] = cycle[11]

    cusps[4] = (cusps[10] + 180.0) % 360.0
    cusps[5] = (cusps[11] + 180.0) % 360.0
    cusps[7] = (cusps[1]  + 180.0) % 360.0
    cusps[8] = (cusps[2]  + 180.0) % 360.0
    return _finalize_cusps(cusps, context="_carter")


# ---------------------------------------------------------------------------
# Topocentric (Polich-Page)
# ---------------------------------------------------------------------------

def _topocentric(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    Topocentric (Polich-Page) houses from graduated equatorial pole-height doctrine.

    Equatorial pole right ascensions are spaced from ARMC, projected with the
    doctrinal pole heights, resolved against the visible arcs, and assembled
    into the quadrant figure.

    Raises:
        ValueError: Propagated if branch selection or cusp normalization fails.

    Side effects:
        None
    """
    phi = lat * DEG2RAD

    mc_geometric = _mc_from_armc(armc, obliquity, lat)
    mc = _mc_above_horizon(mc_geometric, obliquity, lat)
    asc = _asc_from_armc(armc, obliquity, lat)
    phi_1 = math.degrees(math.atan((1.0 / 3.0) * math.tan(phi)))
    phi_2 = math.degrees(math.atan((2.0 / 3.0) * math.tan(phi)))

    ic = (mc + 180.0) % 360.0
    mc_swapped = abs((mc - mc_geometric + 180.0) % 360.0 - 180.0) > 90.0

    cusp_specs = (
        (10, 30.0, phi_1),
        (11, 60.0, phi_2),
        (1, 120.0, phi_2),
        (2, 150.0, phi_1),
    )

    primaries: dict[int, float] = {}
    for index, ra_offset_deg, pole_height_deg in cusp_specs:
        pole_ra = (armc + ra_offset_deg) % 360.0
        raw = _project_ra_with_pole(pole_ra, pole_height_deg, obliquity)
        if mc_swapped:
            primaries[index] = (raw + 180.0) % 360.0
        elif index in (10, 11):
            primaries[index] = _select_antipodal_branch(raw, mc, asc)
        else:
            primaries[index] = _select_antipodal_branch(raw, asc, ic)

    return _assemble_antipodal_quadrant_cusps(
        asc=asc,
        mc=mc,
        h2=primaries[1],
        h3=primaries[2],
        h11=primaries[10],
        h12=primaries[11],
        context="_topocentric",
    )


# ---------------------------------------------------------------------------
# Coordinate rotation helper
# ---------------------------------------------------------------------------

def _rotate_x_axis(lon: float, lat: float, rotation: float) -> tuple[float, float]:
    """
    Rotate spherical coordinates about the x-axis by the requested angle.

    This is the shared spherical-frame rotation used in the ecliptic,
    equatorial, and horizontal transforms within the House Pillar.

    Raises:
        None under normal operation.

    Side effects:
        None
    """
    rot_rad = rotation * DEG2RAD
    lon_rad = lon * DEG2RAD
    lat_rad = lat * DEG2RAD

    cos_lat = math.cos(lat_rad)
    sin_lat = math.sin(lat_rad)
    sin_lon = math.sin(lon_rad)
    cos_lon = math.cos(lon_rad)
    sin_rot = math.sin(rot_rad)
    cos_rot = math.cos(rot_rad)

    # Direct spherical relation for x-axis rotation.
    y_num = cos_lat * sin_lon * cos_rot - sin_lat * sin_rot
    x_num = cos_lat * cos_lon
    z_num = cos_lat * sin_lon * sin_rot + sin_lat * cos_rot

    lon_new = math.atan2(y_num, x_num) * RAD2DEG % 360.0
    lat_new = math.asin(max(-1.0, min(1.0, z_num))) * RAD2DEG
    return lon_new, lat_new


# ---------------------------------------------------------------------------
# Krusinski-Pisa
# ---------------------------------------------------------------------------

def _krusinski(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    Krusinski-Pisa houses from the great circle through the Ascendant and Zenith.

    The governing great circle is divided into equal sectors and the resulting
    meridian circles are projected back to the ecliptic.

    Raises:
        ValueError: Propagated if rotated-frame projection or normalization fails.

    Side effects:
        None
    """
    mc = _mc_from_armc(armc, obliquity, lat)
    asc = _asc_from_armc(armc, obliquity, lat)

    # Keep Asc in the same semicircle convention used across quadrant systems.
    if ((asc - mc + 180.0) % 360.0) - 180.0 < 0.0:
        asc = (asc + 180.0) % 360.0

    def _anchor_on_horizon(asc_lon: float) -> float:
        """Longitude offset of the Asc-Zenith great-circle anchor in horizon frame."""
        eq_lon, eq_lat = _rotate_x_axis(asc_lon, 0.0, -obliquity)
        eq_lon = (eq_lon - (armc - 90.0)) % 360.0
        hor_lon, _ = _rotate_x_axis(eq_lon, eq_lat, -(90.0 - lat))
        return hor_lon % 360.0

    def _house_circle_ra(sector_deg: float, anchor_lon: float) -> float:
        """Map a house-circle sector longitude to equatorial right ascension."""
        hor_lon, hor_lat = _rotate_x_axis(sector_deg, 0.0, 90.0)
        hor_lon = (hor_lon + anchor_lon) % 360.0
        eq_lon, eq_lat = _rotate_x_axis(hor_lon, hor_lat, 90.0 - lat)
        return (eq_lon + (armc - 90.0)) % 360.0

    anchor_lon = _anchor_on_horizon(asc)

    def _sector_longitude(sector_deg: float) -> float:
        ra = _house_circle_ra(sector_deg, anchor_lon)
        return _project_ra_with_pole(ra, 0.0, obliquity) % 360.0

    return _assemble_antipodal_quadrant_cusps(
        asc=asc,
        mc=mc,
        h2=_sector_longitude(30.0),
        h3=_sector_longitude(60.0),
        h11=_sector_longitude(300.0),
        h12=_sector_longitude(330.0),
        context="_krusinski",
    )


# ---------------------------------------------------------------------------
# APC Houses
# ---------------------------------------------------------------------------

def _apc_project(
    cusp_ra_rad: float,
    dsa_asc_rad: float,
    tan_lat: float,
    armc_rad: float,
    obliquity_rad: float,
) -> float:
    """
    Project one APC cusp RA (on the Ascendant's parallel circle) to ecliptic
    longitude.

    GEOMETRIC DERIVATION:
        Let C be a cusp point on the Ascendant's parallel circle of declination δ_asc.
        In equatorial rectangular coordinates, the direction vector is:
            v_eq = [cos(δ_asc)*cos(α), cos(δ_asc)*sin(α), sin(δ_asc)]^T
        where α is the right ascension of the cusp point.
        
        Rotating v_eq by true obliquity ε about the x-axis into ecliptic coordinates:
            v_ecl = R_x(ε) * v_eq
            v_ecl = [
                cos(δ_asc)*cos(α),
                cos(δ_asc)*sin(α)*cos(ε) - sin(δ_asc)*sin(ε),
                cos(δ_asc)*sin(α)*sin(ε) + sin(δ_asc)*cos(ε)
            ]^T
            
        The ecliptic longitude λ is given by:
            λ = atan2(Y_ecl, X_ecl)
            
        To make the projection independent of the specific declination scale cos(δ_asc),
        we divide both components by cos(δ_asc):
            y = Y_ecl / cos(δ_asc) = sin(α)*cos(ε) - tan(δ_asc)*sin(ε)
            x = X_ecl / cos(δ_asc) = cos(α)
            
        From the horizon event condition for the Ascendant:
            cos(DSA_asc) = -tan(δ_asc)*tan(lat)
            
        This defines the parallel circle scale factor, parallel_scale = -cos(DSA_asc),
        which relates the declination to geographic latitude via:
            tan(δ_asc) = parallel_scale / tan(lat)
            
        Substituting this into the divided coordinates yields the de Boer/APC
        longitude projection equations:
            parallel_scale = -cos(DSA_asc)
            y = parallel_scale * sin(ARMC) + sin(α)
            x = cos(ε) * (parallel_scale * cos(ARMC) + cos(α)) + sin(ε) * tan(lat) * sin(ARMC - α)
            
        This projection maps any right ascension α on the parallel circle directly
        to the ecliptic.

    Args:
        cusp_ra_rad:   Right ascension of the cusp point on the parallel circle.
        dsa_asc_rad:   Diurnal semi-arc of the Ascendant (radians); equals π/2 + asc_ad.
        tan_lat:       tan(geographic latitude).
        armc_rad:      ARMC in radians.
        obliquity_rad: True obliquity in radians.

    Returns:
        Ecliptic longitude of the projected cusp, in degrees [0, 360).
    """
    parallel_scale = -math.cos(dsa_asc_rad)
    y = parallel_scale * math.sin(armc_rad) + math.sin(cusp_ra_rad)
    x = (
        math.cos(obliquity_rad) * (parallel_scale * math.cos(armc_rad) + math.cos(cusp_ra_rad))
        + math.sin(obliquity_rad) * tan_lat * math.sin(armc_rad - cusp_ra_rad)
    )
    return (math.atan2(y, x) * RAD2DEG) % 360.0


def _apc(armc: float, obliquity: float, lat: float) -> list[float]:
    """
    APC (Ascendant Parallel Circle) house system.

    GEOMETRIC ONTOLOGY AND DERIVATION:
        The Ascendant (ASC) is a direction vector v_asc on the celestial sphere, defined by
        the intersection of the ecliptic plane and the observer's eastern horizon plane.
        The governing event for the APC system is the horizon-crossing condition of the Ascendant.
        At the instant of rising, the Ascendant's unit direction vector satisfies the horizon
        orthogonal relationship:
            v_asc · Zenith = 0
            
        For an observer at geographic latitude φ and local sidereal time LST (ARMC), the
        Zenith vector in equatorial coordinates is:
            Zenith = [cos(φ)*cos(ARMC), cos(φ)*sin(ARMC), sin(φ)]^T
            
        And the Ascendant vector at its parallel circle of declination δ_asc is:
            v_asc = [cos(δ_asc)*cos(α_asc), cos(δ_asc)*sin(α_asc), sin(δ_asc)]^T
            
        Expanding the dot product v_asc · Zenith = 0:
            cos(δ_asc)*cos(φ)*cos(α_asc - ARMC) + sin(δ_asc)*sin(φ) = 0
            
        Dividing by cos(δ_asc)*cos(φ) yields:
            cos(α_asc - ARMC) = -tan(δ_asc)*tan(φ)
            
        By definition, the Diurnal Semi-Arc of the Ascendant, DSA_asc, is the equatorial
        hour angle difference from the meridian to the horizon crossing, which satisfies:
            cos(DSA_asc) = -tan(δ_asc)*tan(φ)
            
        Using the classical ascensional difference, asc_ad, where DSA_asc = π/2 + asc_ad,
        the horizon-crossing condition maps to the exact classical ascending-terms formula:
            asc_ad = atan(p·cos(ARMC) / (1 + p·sin(ARMC)))
        where:
            p = tan(lat)·tan(obl)
            
        This geometric identity is exact and bridges the spatial vector-orthogonal definition
        of the Ascendant horizon-crossing event to the classical ratio-of-terms formulation.

    COMPLETE ARC DOCTRINE (all 12 cusps):
        The eight intermediate cusps lie on the Ascendant's parallel declination circle
        and are trisected across the diurnal (DSA) and nocturnal (NSA) semi-arcs:
            Upper arc (MC → ASC, DSA_asc wide):
                H11 = RA(ASC) − 2·DSA/3
                H12 = RA(ASC) − 1·DSA/3
            Lower arc (ASC → IC → DSC, NSA_asc = π − DSA_asc per half):
                H2  = RA(ASC) + 1·NSA/3
                H3  = RA(ASC) + 2·NSA/3
                H5  = RA(ASC) + 4·NSA/3
                H6  = RA(ASC) + 5·NSA/3
            Opposite upper arc (DSC → MC):
                H8  = RA(ASC) − 5·DSA/3
                H9  = RA(ASC) − 4·DSA/3
            Cardinal cusps set directly (H1=ASC, H4=IC, H7=DSC, H10=MC).

    BRANCH SELECTION DOCTRINE:
        The projection from equatorial right ascension on the parallel circle to ecliptic
        longitude has two antipodal solutions spaced exactly 180° apart. We resolve this
        ambiguity through two explicit, geometrically-grounded branch selection policies:

        1. Projection-to-Cardinal Frame Realignment (mc_shifted):
           The projection primitive _apc_project is anchored to ARMC, and thus its mathematical
           meridian is the geometric MC (mc_geometric). However, for observer locations where the
           above-horizon MC (mc_visible) is flipped by 180 degrees from mc_geometric, the raw
           projected intermediate cusps will land in the hemisphere opposite to mc_visible.
           We detect this frame mismatch directly by checking if mc_visible and mc_geometric are
           in opposite hemispheres (separated by > 90 degrees). If so, we flip the raw cusps by 180°
           to realign them with the visible MC.

        2. Polar-Cap Branch (polar_flipped):
           At latitudes exceeding the polar circle limit (|latitude| >= 90° − obliquity),
           the Ascendant's parallel circle can become circumpolar or sink completely below
           the horizon, causing a coordinate singularity. Under these conditions, the ecliptic
           projection of the Ascendant's right ascension (ra_asc) can flip to the antipodal
           ecliptic hemisphere (shifted by 180°).
           
           DETECTION DOCTRINE: We evaluate a probe projection at ra_asc. Under correct branch conditions,
           projecting ra_asc through _apc_project must recover the true Ascendant (asc). If the
           angular gap between this probe and the true Ascendant exceeds 90°, the projection is
           flipped. The 90° threshold is a robust boundary because the branch solutions are
           exactly 180° apart, leaving zero ambiguity.
           This check is evaluated as a subordinate branch when mc_shifted is False.

        When either detection doctrine triggers, a unified 180° correction is applied to all
        eight intermediate cusps to align them with the correct ecliptic branch.

    Raises:
        ValueError: Propagated if final cusp normalization fails.

    Side effects:
        None
    """
    mc_geometric = _mc_from_armc(armc, obliquity, lat)
    mc_visible = _mc_above_horizon(mc_geometric, obliquity, lat)
    asc = _asc_from_armc(armc, obliquity, lat)

    lat_r  = lat * DEG2RAD
    obl_r  = obliquity * DEG2RAD
    armc_r = armc * DEG2RAD

    _POLAR_EPS = 1e-6
    abs_lat = abs(lat)
    if abs_lat > 90.0 - _POLAR_EPS:
        asc_ad = 0.0
        tan_lat = 0.0
    else:
        tan_lat = math.tan(lat_r)
        p = tan_lat * math.tan(obl_r)
        denom = 1.0 + p * math.sin(armc_r)
        numer = p * math.cos(armc_r)
        asc_ad = (math.copysign(math.pi / 2.0, numer)
                  if abs(denom) < 1e-12
                  else math.atan(numer / denom))

    dsa = math.pi / 2.0 + asc_ad
    nsa = math.pi / 2.0 - asc_ad
    ra_asc = armc_r + asc_ad + math.pi / 2.0

    proj = _apc_project
    h2_raw  = proj(ra_asc + 1.0 * nsa / 3.0, dsa, tan_lat, armc_r, obl_r)
    h3_raw  = proj(ra_asc + 2.0 * nsa / 3.0, dsa, tan_lat, armc_r, obl_r)
    h5_raw  = proj(ra_asc + 4.0 * nsa / 3.0, dsa, tan_lat, armc_r, obl_r)
    h6_raw  = proj(ra_asc + 5.0 * nsa / 3.0, dsa, tan_lat, armc_r, obl_r)
    h8_raw  = proj(ra_asc - 5.0 * dsa / 3.0, dsa, tan_lat, armc_r, obl_r)
    h9_raw  = proj(ra_asc - 4.0 * dsa / 3.0, dsa, tan_lat, armc_r, obl_r)
    h11_raw = proj(ra_asc - 2.0 * dsa / 3.0, dsa, tan_lat, armc_r, obl_r)
    h12_raw = proj(ra_asc - 1.0 * dsa / 3.0, dsa, tan_lat, armc_r, obl_r)

    # 1. Projection-to-Cardinal Frame Realignment (mc_shifted)
    mc_shifted = abs(((mc_visible - mc_geometric + 180.0) % 360.0) - 180.0) > 90.0

    # 2. Polar-Cap Branch Detection (polar_flipped)
    polar_flipped = False
    if not mc_shifted and (abs_lat >= 90.0 - obliquity):
        probe = proj(ra_asc, dsa, tan_lat, armc_r, obl_r)
        probe_gap = abs(((probe - asc + 180.0) % 360.0) - 180.0)
        polar_flipped = probe_gap > 90.0

    # Apply unified branch correction
    branch_flip_required = mc_shifted or polar_flipped
    if branch_flip_required:
        h2  = (h2_raw  + 180.0) % 360.0
        h3  = (h3_raw  + 180.0) % 360.0
        h5  = (h5_raw  + 180.0) % 360.0
        h6  = (h6_raw  + 180.0) % 360.0
        h8  = (h8_raw  + 180.0) % 360.0
        h9  = (h9_raw  + 180.0) % 360.0
        h11 = (h11_raw + 180.0) % 360.0
        h12 = (h12_raw + 180.0) % 360.0
    else:
        h2, h3, h5, h6, h8, h9, h11, h12 = (
            h2_raw, h3_raw, h5_raw, h6_raw, h8_raw, h9_raw, h11_raw, h12_raw
        )

    ic  = (mc_visible + 180.0) % 360.0
    dsc = (asc       + 180.0) % 360.0
    cusps = [asc, h2, h3, ic, h5, h6, dsc, h8, h9, mc_visible, h11, h12]
    return _finalize_cusps(cusps, context="_apc")


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
    sun_longitude:   float | None = None,
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
                 are not supported by default.
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
        sun_longitude: Optional geocentric tropical solar longitude (degrees).
            If supplied, SUNSHINE and SOLAR_SIGN houses use this value directly
            instead of resolving it from the planetary oracle.

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
        - None beyond subordinate numerical calls. SUNSHINE / SOLAR_SIGN may
          resolve the Sun's longitude through the module-scoped solar resolver
          if ``sun_longitude`` is not supplied explicitly.
    """
    active_policy = _normalize_house_policy(policy)
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

    sun_lon = sun_longitude
    if sun_lon is None and system in {HouseSystem.SUNSHINE, HouseSystem.SOLAR_SIGN}:
        sun_lon = _solar_house_anchor_longitude(jd_ut)

    return houses_from_armc(
        armc,
        obliquity,
        latitude,
        system,
        policy=active_policy,
        sun_longitude=sun_lon,
        ayanamsa_offset=ayanamsa_offset,
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
    RITE: The House Membership Witness

    THEOREM: This dataclass records the assignment of one ecliptic longitude to one house under an existing house figure.

    RITE OF PURPOSE:
        This vessel exists so point-to-house membership can be audited as a
        distinct truth product rather than an ephemeral integer result. It
        preserves the placed longitude, opening cusp, and governing HouseCusps
        figure in one immutable record. Without it, later layers would lose
        the doctrinal context of placement.

    LAW OF OPERATION:
        Responsibilities:
            - Record the assigned house number for one longitude.
            - Preserve the governing HouseCusps vessel.
            - Preserve whether the longitude landed on the opening cusp.
            - Enforce internal consistency between house and cusp_longitude.
        Non-responsibilities:
            - Does not compute house cusps.
            - Does not derive boundary or angularity profiles.
        Dependencies:
            - A valid HouseCusps vessel.
            - Boundary doctrine from assign_house().
        Structural invariants:
            - house is in 1..12.
            - longitude and cusp_longitude live in [0, 360).
            - cusp_longitude equals house_cusps.cusps[house - 1].
        Side effects:
            - None
        Failure behavior:
            - Raises ValueError through invariant enforcement when fields disagree.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "type": "membership_vessel",
      "owns_state": true,
      "mutates_external_state": false,
      "requires": ["house", "longitude", "house_cusps", "exact_on_cusp", "cusp_longitude"],
      "guarantees": ["house/cusp alignment", "immutable placement witness"]
    }
    """
    house:         int
    longitude:     float
    house_cusps:   HouseCusps
    exact_on_cusp: bool
    cusp_longitude: float

    def __post_init__(self) -> None:
        _require(1 <= self.house <= 12, f"HousePlacement invariant violated: house={self.house!r} not in [1, 12]")
        _require(0.0 <= self.longitude < 360.0, f"HousePlacement invariant violated: longitude={self.longitude!r} not in [0, 360)")
        _require(0.0 <= self.cusp_longitude < 360.0, f"HousePlacement invariant violated: cusp_longitude={self.cusp_longitude!r} not in [0, 360)")
        expected_cusp = self.house_cusps.cusps[self.house - 1]
        _require(
            abs(self.cusp_longitude - expected_cusp) < 1e-9,
            f"HousePlacement invariant violated: cusp_longitude={self.cusp_longitude!r} "
            f"does not match house_cusps.cusps[{self.house - 1}]={expected_cusp!r}",
        )


def assign_house(longitude: float, house_cusps: HouseCusps) -> HousePlacement:
    """
    Assign an ecliptic longitude to a house (1?12) using an existing HouseCusps.

    This applies the canonical half-open interval rule under explicit boundary
    doctrine and returns a HousePlacement witness for the resulting house.

    Args:
        longitude: Ecliptic longitude of the point, in degrees.
        house_cusps: A HouseCusps result from house computation.

    Returns:
        A frozen HousePlacement describing which house the point occupies.

    Raises:
        ValueError: If ``house_cusps.cusps`` does not contain exactly 12 values.

    Side effects:
        None
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
    RITE: The Boundary Sensitivity Witness

    THEOREM: This dataclass enriches one house placement with forward-arc cusp distances and an explicit near-cusp judgment.

    RITE OF PURPOSE:
        This vessel exists so cusp proximity can be reasoned about without
        re-performing house assignment or smuggling hidden orb doctrine into
        later interpretation. It preserves the threshold and both bracket
        distances as first-class result truth. Without it, boundary
        sensitivity would be reduced to ad hoc arithmetic.

    LAW OF OPERATION:
        Responsibilities:
            - Record opening and closing cusp longitudes for one placement.
            - Record forward-arc distances within the assigned house.
            - Record the declared near-cusp threshold and resulting judgment.
            - Enforce additive distance invariants.
        Non-responsibilities:
            - Does not assign houses.
            - Does not interpret angularity or chart emphasis.
        Dependencies:
            - A valid HousePlacement vessel.
            - Forward-arc doctrine from describe_boundary().
        Structural invariants:
            - Cusp longitudes remain in [0, 360).
            - dist_to_opening + dist_to_closing equals house_span.
            - is_near_cusp matches the stored threshold test.
        Side effects:
            - None
        Failure behavior:
            - Raises ValueError through invariant enforcement when distances or threshold are inconsistent.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "type": "boundary_profile_vessel",
      "owns_state": true,
      "mutates_external_state": false,
      "requires": ["placement", "opening_cusp", "closing_cusp", "distance fields", "threshold"],
      "guarantees": ["forward-arc consistency", "immutable cusp-boundary profile"]
    }
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
        _require(0.0 <= self.opening_cusp < 360.0, f"HouseBoundaryProfile: opening_cusp={self.opening_cusp!r} not in [0, 360)")
        _require(0.0 <= self.closing_cusp < 360.0, f"HouseBoundaryProfile: closing_cusp={self.closing_cusp!r} not in [0, 360)")
        _require(self.dist_to_opening >= 0.0, f"HouseBoundaryProfile: dist_to_opening={self.dist_to_opening!r} < 0")
        _require(self.dist_to_closing > 0.0, f"HouseBoundaryProfile: dist_to_closing={self.dist_to_closing!r} <= 0")
        _require(
            abs(self.dist_to_opening + self.dist_to_closing - self.house_span) < 1e-9,
            f"HouseBoundaryProfile: dist_to_opening + dist_to_closing "
            f"({self.dist_to_opening + self.dist_to_closing}) != house_span ({self.house_span})",
        )
        _require(self.house_span > 0.0, f"HouseBoundaryProfile: house_span={self.house_span!r} <= 0")
        _require(self.near_cusp_threshold > 0.0, f"HouseBoundaryProfile: near_cusp_threshold={self.near_cusp_threshold!r} <= 0")
        _require(self.nearest_cusp_distance >= 0.0, f"HouseBoundaryProfile: nearest_cusp_distance={self.nearest_cusp_distance!r} < 0")
        _require(
            self.is_near_cusp == (self.nearest_cusp_distance < self.near_cusp_threshold),
            f"HouseBoundaryProfile: is_near_cusp inconsistent with "
            f"nearest_cusp_distance={self.nearest_cusp_distance!r} and "
            f"near_cusp_threshold={self.near_cusp_threshold!r}",
        )


def describe_boundary(
    placement: HousePlacement,
    *,
    near_cusp_threshold: float = _NEAR_CUSP_DEFAULT_THRESHOLD,
) -> HouseBoundaryProfile:
    """
    Derive boundary context for an existing HousePlacement.

    This computes forward-arc distances from the placed longitude to the
    opening and closing cusps of its assigned house without re-performing
    house assignment.

    Args:
        placement: A HousePlacement returned by assign_house().
        near_cusp_threshold: Forward-arc threshold in degrees below which a
            placement is considered near-cusp.

    Returns:
        A frozen HouseBoundaryProfile enriching the placement with boundary context.

    Raises:
        ValueError: If ``near_cusp_threshold`` is not positive.

    Side effects:
        None
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
    RITE: The Angularity Triad

    THEOREM: This enum records the three traditional angularity categories assigned from house number alone.

    RITE OF PURPOSE:
        This enum exists so angular house doctrine is preserved as explicit
        symbolic truth rather than ad hoc string literals. It gives later
        vessels and comparisons a stable categorical surface for structural
        house power. Without it, angularity would be harder to validate and compare.

    LAW OF OPERATION:
        Responsibilities:
            - Declare the ANGULAR, SUCCEDENT, and CADENT categories.
            - Preserve the Phase 7 house-power taxonomy as stable values.
        Non-responsibilities:
            - Does not assign houses.
            - Does not score or weight category strength.
        Dependencies:
            - House-number doctrine encoded in _ANGULARITY_MAP.
        Structural invariants:
            - Values remain the canonical category labels for this Pillar.
        Side effects:
            - None
        Failure behavior:
            - None

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
        applied.  The mapping is universal across all 18 supported house systems
        because it is derived from the assigned house number alone.

    Future phases that are NOT the responsibility of this enum:
        - Weighting or scoring the three categories
        - Combining angularity with cusp proximity for a compound strength value
        - System-comparison ranking

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "type": "enum",
      "owns_state": false,
      "mutates_external_state": false,
      "requires": [],
      "guarantees": ["stable angularity taxonomy"]
    }
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
    RITE: The Angularity Witness

    THEOREM: This dataclass records the angularity category of one existing house placement.

    RITE OF PURPOSE:
        This vessel exists so structural house power can be attached to a
        placement without recomputing membership or smuggling interpretation
        into the lower layers. It preserves the assigned category and its
        originating placement as one immutable witness. Without it, category
        truth would have to be recomputed ad hoc.

    LAW OF OPERATION:
        Responsibilities:
            - Record the angularity category for one placement.
            - Preserve the originating HousePlacement.
            - Enforce house/category consistency against _ANGULARITY_MAP.
        Non-responsibilities:
            - Does not assign houses.
            - Does not compute cusp proximity or chart-wide strength.
        Dependencies:
            - A valid HousePlacement vessel.
            - _ANGULARITY_MAP doctrine.
        Structural invariants:
            - house matches placement.house.
            - category matches _ANGULARITY_MAP[house].
        Side effects:
            - None
        Failure behavior:
            - Raises ValueError through invariant enforcement when house/category truth disagrees.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "type": "angularity_profile_vessel",
      "owns_state": true,
      "mutates_external_state": false,
      "requires": ["placement", "category", "house"],
      "guarantees": ["house/category consistency", "immutable angularity witness"]
    }
    """
    placement: HousePlacement
    category:  HouseAngularity
    house:     int

    def __post_init__(self) -> None:
        _require(1 <= self.house <= 12, f"HouseAngularityProfile invariant violated: house={self.house!r} not in [1, 12]")
        _require(
            self.house == self.placement.house,
            f"HouseAngularityProfile invariant violated: house={self.house!r} "
            f"does not match placement.house={self.placement.house!r}",
        )
        _require(
            self.category == _ANGULARITY_MAP[self.house],
            f"HouseAngularityProfile invariant violated: category={self.category!r} "
            f"does not match _ANGULARITY_MAP[{self.house}]={_ANGULARITY_MAP[self.house]!r}",
        )


def describe_angularity(placement: HousePlacement) -> HouseAngularityProfile:
    """
    Derive the angularity or house-power profile for an existing HousePlacement.

    This maps the assigned house number to its traditional structural category
    using the static angularity doctrine. House assignment is not re-performed;
    ``placement.house`` is authoritative.

    Args:
        placement: A HousePlacement returned by assign_house().

    Returns:
        A frozen HouseAngularityProfile with category and house number.

    Raises:
        None under normal operation.

    Side effects:
        None
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
    RITE: The Cusp Comparison Witness

    THEOREM: This dataclass records a cusp-level comparison between two computed house figures.

    RITE OF PURPOSE:
        This vessel exists so system comparison remains an explicit factual
        product rather than an informal diff performed at the call site. It
        preserves directional cusp deltas together with fallback and family
        agreement truth. Without it, comparison logic would be harder to audit.

    LAW OF OPERATION:
        Responsibilities:
            - Record the left and right HouseCusps being compared.
            - Record 12 signed circular cusp deltas.
            - Record effective-system, fallback, and family agreement flags.
        Non-responsibilities:
            - Does not recompute cusps.
            - Does not rank one system above another.
        Dependencies:
            - Two valid HouseCusps vessels.
            - Signed circular difference doctrine.
        Structural invariants:
            - cusp_deltas has 12 entries in (-180, 180].
            - systems_agree and fallback_differs match the stored source vessels.
        Side effects:
            - None
        Failure behavior:
            - Raises ValueError through invariant enforcement when stored deltas or flags are inconsistent.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "type": "comparison_vessel",
      "owns_state": true,
      "mutates_external_state": false,
      "requires": ["left", "right", "12 cusp deltas", "agreement flags"],
      "guarantees": ["signed cusp-delta truth", "effective-system comparison fidelity"]
    }
    """
    left:             HouseCusps
    right:            HouseCusps
    cusp_deltas:      tuple[float, ...]
    systems_agree:    bool
    fallback_differs: bool
    families_differ:  bool

    def __post_init__(self) -> None:
        _require(len(self.cusp_deltas) == 12, f"HouseSystemComparison: cusp_deltas must have 12 entries; got {len(self.cusp_deltas)}")
        _require(
            all(-180.0 < d <= 180.0 for d in self.cusp_deltas),
            f"HouseSystemComparison: cusp_deltas contains value outside (-180, 180]: {self.cusp_deltas!r}",
        )
        _require(
            self.systems_agree == (self.left.effective_system == self.right.effective_system),
            "HouseSystemComparison: systems_agree inconsistent with effective_system fields",
        )
        _require(
            self.fallback_differs == (self.left.fallback != self.right.fallback),
            "HouseSystemComparison: fallback_differs inconsistent with fallback fields",
        )


@dataclass(frozen=True, slots=True)
class HousePlacementComparison:
    """
    RITE: The Placement Comparison Witness

    THEOREM: This dataclass records how one longitude is placed across two or more house figures.

    RITE OF PURPOSE:
        This vessel exists so cross-system placement truth can be retained as
        a first-class artifact rather than collapsed to a yes/no agreement
        flag. It preserves every placement together with house-number and
        angularity agreement truth. Without it, callers would lose the witness
        chain needed for later audit.

    LAW OF OPERATION:
        Responsibilities:
            - Record the normalized longitude under comparison.
            - Record the placements and house numbers for each compared system.
            - Record house-number and angularity agreement truth.
        Non-responsibilities:
            - Does not recompute placements.
            - Does not rank the compared systems.
        Dependencies:
            - At least two valid HousePlacement vessels.
        Structural invariants:
            - longitude is normalized to [0, 360).
            - houses matches placement.house for every placement.
            - all_agree matches the unique-house count.
        Side effects:
            - None
        Failure behavior:
            - Raises ValueError through invariant enforcement when stored placements disagree with summary fields.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "type": "placement_comparison_vessel",
      "owns_state": true,
      "mutates_external_state": false,
      "requires": ["longitude", "placements", "houses", "agreement flags"],
      "guarantees": ["placement summary fidelity", "immutable cross-system witness"]
    }
    """
    longitude:         float
    placements:        tuple[HousePlacement, ...]
    houses:            tuple[int, ...]
    all_agree:         bool
    angularity_agrees: bool

    def __post_init__(self) -> None:
        _require(0.0 <= self.longitude < 360.0, f"HousePlacementComparison: longitude={self.longitude!r} not in [0, 360)")
        _require(len(self.placements) >= 2, f"HousePlacementComparison: requires at least 2 placements; got {len(self.placements)}")
        _require(
            len(self.houses) == len(self.placements),
            f"HousePlacementComparison: houses length {len(self.houses)} != placements length {len(self.placements)}",
        )
        _require(
            all(h == pl.house for h, pl in zip(self.houses, self.placements)),
            "HousePlacementComparison: houses tuple does not match placement.house values",
        )
        _require(
            self.all_agree == (len(set(self.houses)) == 1),
            "HousePlacementComparison: all_agree inconsistent with houses tuple",
        )
        for pl in self.placements:
            _require(
                pl.longitude == self.longitude,
                f"HousePlacementComparison: placement.longitude={pl.longitude!r} != longitude={self.longitude!r}",
            )


def compare_systems(left: HouseCusps, right: HouseCusps) -> HouseSystemComparison:
    """
    Produce a cusp-level comparison of two HouseCusps results.

    This computes per-house signed circular cusp deltas and derives the
    agreement flags from the two stored HouseCusps vessels. No cusps are
    recomputed.

    Args:
        left: First reference HouseCusps.
        right: Second HouseCusps to compare against ``left``.

    Returns:
        A frozen HouseSystemComparison.

    Raises:
        None under normal operation.

    Side effects:
        None
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

    Side effects:
        None
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
    RITE: The Occupancy Witness

    THEOREM: This dataclass records which placed points occupy one house within a chart-wide distribution profile.

    RITE OF PURPOSE:
        This vessel exists so chart-wide distribution can preserve each house's
        local population as an explicit result rather than anonymous counters.
        It keeps occupant longitudes and placements aligned with the house they
        occupy. Without it, distribution truth would lose local granularity.

    LAW OF OPERATION:
        Responsibilities:
            - Record one house number and its occupant count.
            - Preserve occupant longitudes and placements in input order.
            - Record whether the house is empty.
            - Enforce count and house-alignment invariants.
        Non-responsibilities:
            - Does not assign houses.
            - Does not summarize the entire chart.
        Dependencies:
            - HousePlacement records produced upstream.
        Structural invariants:
            - count equals len(longitudes) and len(placements).
            - every placement belongs to the recorded house.
            - is_empty matches count == 0.
        Side effects:
            - None
        Failure behavior:
            - Raises ValueError through invariant enforcement when count or house alignment is inconsistent.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "type": "occupancy_vessel",
      "owns_state": true,
      "mutates_external_state": false,
      "requires": ["house", "count", "longitudes", "placements", "is_empty"],
      "guarantees": ["count fidelity", "per-house placement alignment"]
    }
    """
    house:      int
    count:      int
    longitudes: tuple[float, ...]
    placements: tuple[HousePlacement, ...]
    is_empty:   bool

    def __post_init__(self) -> None:
        _require(1 <= self.house <= 12, f"HouseOccupancy: house={self.house!r} not in [1, 12]")
        _require(self.count == len(self.longitudes), f"HouseOccupancy: count={self.count} != len(longitudes)={len(self.longitudes)}")
        _require(self.count == len(self.placements), f"HouseOccupancy: count={self.count} != len(placements)={len(self.placements)}")
        _require(self.is_empty == (self.count == 0), f"HouseOccupancy: is_empty={self.is_empty} inconsistent with count={self.count}")
        for pl in self.placements:
            _require(pl.house == self.house, f"HouseOccupancy: placement.house={pl.house} != house={self.house}")


@dataclass(frozen=True, slots=True)
class HouseDistributionProfile:
    """
    RITE: The Chart Distribution Witness

    THEOREM: This dataclass records the chart-wide distribution of a point set across one house figure.

    RITE OF PURPOSE:
        This vessel exists so house distribution is preserved as explicit chart
        structure rather than recomputed summaries scattered across callers. It
        keeps per-house occupancies, dominant-house truth, and angularity
        totals in one immutable record. Without it, higher interpretation
        layers would lose provenance and internal consistency.

    LAW OF OPERATION:
        Responsibilities:
            - Record the source HouseCusps and all per-house occupancies.
            - Record total count, dominant houses, empty houses, and angularity totals.
            - Enforce chart-wide count and occupancy invariants.
        Non-responsibilities:
            - Does not assign houses.
            - Does not rank astrological importance beyond the stored counts.
        Dependencies:
            - One HouseCusps vessel and 12 HouseOccupancy vessels.
        Structural invariants:
            - occupancies and counts always have length 12.
            - point_count equals sum(counts).
            - angular_count + succedent_count + cadent_count equals point_count.
        Side effects:
            - None
        Failure behavior:
            - Raises ValueError through invariant enforcement when summary fields disagree with occupancies.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "type": "distribution_profile_vessel",
      "owns_state": true,
      "mutates_external_state": false,
      "requires": ["house_cusps", "point_count", "occupancies", "counts", "summary sets and totals"],
      "guarantees": ["12-house occupancy integrity", "chart-wide count consistency"]
    }
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
        _require(len(self.occupancies) == 12, f"HouseDistributionProfile: len(occupancies)={len(self.occupancies)}, expected 12")
        _require(len(self.counts) == 12, f"HouseDistributionProfile: len(counts)={len(self.counts)}, expected 12")
        _require(self.point_count == sum(self.counts), f"HouseDistributionProfile: point_count={self.point_count} != sum(counts)={sum(self.counts)}")
        _require(
            self.angular_count + self.succedent_count + self.cadent_count == self.point_count,
            f"HouseDistributionProfile: angularity counts sum "
            f"({self.angular_count}+{self.succedent_count}+{self.cadent_count}) "
            f"!= point_count={self.point_count}",
        )
        for i, occ in enumerate(self.occupancies):
            _require(occ.house == i + 1, f"HouseDistributionProfile: occupancies[{i}].house={occ.house}, expected {i+1}")
            _require(self.counts[i] == occ.count, f"HouseDistributionProfile: counts[{i}]={self.counts[i]} != occupancy.count={occ.count}")
        if self.point_count == 0:
            _require(self.dominant_houses == (), f"HouseDistributionProfile: dominant_houses must be () when point_count==0")
        else:
            max_count = max(self.counts)
            for h in self.dominant_houses:
                _require(
                    self.counts[h - 1] == max_count,
                    f"HouseDistributionProfile: dominant house {h} count {self.counts[h-1]} != max {max_count}",
                )


def distribute_points(
    longitudes: "list[float] | tuple[float, ...]",
    house_cusps: HouseCusps,
) -> HouseDistributionProfile:
    """
    Place a sequence of longitudes against one HouseCusps and return a chart-wide distribution profile.

    Each longitude is placed via ``assign_house()``, then accumulated into the
    per-house occupancy records and chart-wide summary totals.

    Args:
        longitudes: Sequence of ecliptic longitudes to place.
        house_cusps: The HouseCusps to place all points against.

    Returns:
        A frozen HouseDistributionProfile.

    Raises:
        None under normal operation.

    Side effects:
        None
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
# ARMC-DIRECT HOUSE COMPUTATION  (Phase 2)
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
    Compute house cusps from ARMC and obliquity.

    Use this when ARMC is already known (e.g. from a relocated chart,
    a synastry engine, or an external source) and you do not want Moira to
    re-derive it from a Julian date and geographic longitude.

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
        A :class:`HouseCusps` vessel using the same policy, fallback,
        and classification conventions as :func:`calculate_houses`.

    Raises:
        ValueError: If ``system == HouseSystem.SUNSHINE`` and ``sun_longitude``
            is ``None``.
        ValueError: When policy requires strict behaviour and a fallback
            condition is encountered.

    Side effects:
        None
    """
    active_policy = _normalize_house_policy(policy)
    mc          = _mc_from_armc(armc, obliquity, lat)
    asc         = _asc_from_armc(armc, obliquity, lat)
    east_point  = _project_ra_morinus((armc + 90.0) % 360.0, obliquity)
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
    elif effective_system == HouseSystem.SOLAR_SIGN:
        if sun_longitude is None:
            raise ValueError(
                "houses_from_armc: sun_longitude is required for HouseSystem.SOLAR_SIGN"
            )
        cusps = _solar_sign(sun_longitude)
    elif effective_system == HouseSystem.AZIMUTHAL:
        cusps = _azimuthal(armc, obliquity, lat)
    elif effective_system == HouseSystem.CARTER:
        cusps = _carter(armc, obliquity, lat)
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
        east_point=normalize_degrees(east_point - _shift),
        vertex=normalize_degrees(vertex - _shift),
        anti_vertex=normalize_degrees(anti_vertex - _shift),
        effective_system=effective_system,
        fallback=fallback,
        fallback_reason=fallback_reason,
        classification=classify_house_system(effective_system),
        policy=active_policy,
    )


# ===========================================================================
# INTRA-HOUSE FRACTIONAL POSITION  (Phase 2)
# ===========================================================================

def body_house_position(longitude: float, house_cusps: HouseCusps) -> float:
    """
    Return the fractional house position of an ecliptic longitude.

    The return value is a float H where ``int(H)`` is the house number (1–12)
    and ``H - int(H)`` is how far through that house the longitude falls
    (0.0 at the opening cusp, approaching 1.0 at the closing cusp).

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

    Side effects:
        None
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
    RITE: The Cusp Motion Witness

    THEOREM: This dataclass records the instantaneous longitudinal speed of one house cusp.

    RITE OF PURPOSE:
        This vessel exists so cusp-motion work can return a single-house record
        with explicit units and local identity rather than loose numeric tuples.
        It preserves the cusp longitude at the measurement instant together
        with its speed. Without it, later dynamics products would be less legible.

    LAW OF OPERATION:
        Responsibilities:
            - Record one house number.
            - Record the cusp longitude at the measurement instant.
            - Record the instantaneous speed in degrees per day.
        Non-responsibilities:
            - Does not compute the derivative.
            - Does not summarize the whole chart.
        Dependencies:
            - Dynamic measurement surfaces in this Pillar.
        Structural invariants:
            - The stored house identifies the cusp record within a 12-house frame.
        Side effects:
            - None
        Failure behavior:
            - None at the vessel level.

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
        A public cusp-speed surface must be validated against an independent
        oracle that returns cusp speeds in extended output
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

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "type": "dynamics_leaf_vessel",
      "owns_state": true,
      "mutates_external_state": false,
      "requires": ["house", "cusp_longitude", "speed_deg_per_day"],
      "guarantees": ["unit-explicit cusp motion record"]
    }
    """
    house:              int
    cusp_longitude:     float
    speed_deg_per_day:  float


@dataclass(frozen=True, slots=True)
class HouseDynamics:
    """
    RITE: The House Motion Witness

    THEOREM: This dataclass records the instantaneous cusp and angle speeds for one house figure.

    RITE OF PURPOSE:
        This vessel exists so chart dynamics can preserve all cusp and angle
        motion in one immutable result rather than scattered derivatives. It
        keeps the parent HouseCusps together with per-cusp and per-angle
        speeds as one coherent product. Without it, motion truth would be fragmented.

    LAW OF OPERATION:
        Responsibilities:
            - Record the source HouseCusps.
            - Record all 12 cusp speeds.
            - Record ASC, MC, Vertex, and Anti-Vertex speeds.
        Non-responsibilities:
            - Does not derive the finite differences itself.
            - Does not interpret motion astrologically.
        Dependencies:
            - HouseCusps and CuspSpeed vessels.
        Structural invariants:
            - cusp_speeds represents the full 12-house sequence.
        Side effects:
            - None
        Failure behavior:
            - None at the vessel level.

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

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "type": "dynamics_profile_vessel",
      "owns_state": true,
      "mutates_external_state": false,
      "requires": ["house_cusps", "cusp_speeds", "angle speeds"],
      "guarantees": ["single-chart motion profile"]
    }
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
    """Return signed longitude speed across wraparound for a centered finite difference."""
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

    This approach follows the standard finite-difference derivation used by
    reference engines for cusp-speed estimation.

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
          resolves the solar anchor internally when it is not supplied explicitly.
        - The cusp-speed for house 1 is numerically equal to
          ``asc_speed_deg_per_day`` (both derive from the same longitude);
          house 4 speed equals −mc_speed_deg_per_day for most quadrant systems.
        These redundancies are intentional for uniformity.

    Raises:
        ValueError: Propagated if the delegated house computations reject the
            requested inputs or policy.

    Side effects:
        None
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

    Side effects:
        None
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
    """
    RITE: The Rudhyar Quadrant Cross

    THEOREM: This enum records the four developmental quadrants used in the Rudhyar emphasis framework.

    RITE OF PURPOSE:
        This enum exists so quadrant emphasis uses stable symbolic values rather
        than informal labels. It preserves the four-quadrant framework as
        executable doctrine for chart-distribution work.

    LAW OF OPERATION:
        Responsibilities:
            - Declare Q1 through Q4 as the canonical quadrant labels.
        Non-responsibilities:
            - Does not assign houses or points.
        Dependencies:
            - Rudhyar quadrant doctrine.
        Side effects:
            - None
        Failure behavior:
            - None

    Canon: Dane Rudhyar, *The Astrology of Personality* (1936); *The Astrological Houses* (1972)

    [MACHINE_CONTRACT v1]
    {
      "type": "enum",
      "owns_state": false,
      "mutates_external_state": false,
      "requires": [],
      "guarantees": ["stable Rudhyar quadrant taxonomy"]
    }
    """

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
    """
    Return the Rudhyar quadrant for a house number (1–12).

    Raises:
        ValueError: If ``house`` is outside 1..12.

    Side effects:
        None
    """
    if house < 1 or house > 12:
        raise ValueError(f"house must be 1–12, got {house}")
    return _HOUSE_TO_QUADRANT[house]


@dataclass(frozen=True, slots=True)
class QuadrantEmphasisProfile:
    """
    RITE: The Quadrant Emphasis Witness

    THEOREM: This dataclass records how a named point set distributes across Rudhyar's four quadrants within one house figure.

    RITE OF PURPOSE:
        This vessel exists so quadrant emphasis can be preserved as explicit
        chart structure rather than ephemeral counts. It keeps the house frame,
        per-quadrant point names, and hemisphere totals in one immutable
        result. Without it, Rudhyar-style emphasis work would lose provenance.

    LAW OF OPERATION:
        Responsibilities:
            - Record the source HouseCusps and quadrant totals.
            - Record the named points occupying each quadrant.
            - Record dominant quadrant and hemisphere totals.
            - Enforce count consistency across quadrants and hemispheres.
        Non-responsibilities:
            - Does not assign houses.
            - Does not interpret psychological meaning.
        Dependencies:
            - One HouseCusps vessel and named-point placement results.
        Structural invariants:
            - Quadrant counts sum to point_count.
            - Hemisphere totals sum to point_count.
        Side effects:
            - None
        Failure behavior:
            - Raises ValueError when stored counts are inconsistent.

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
    Canon: Dane Rudhyar, *The Astrology of Personality* (1936); *The Astrological Houses* (1972)

    [MACHINE_CONTRACT v1]
    {
      "type": "quadrant_profile_vessel",
      "owns_state": true,
      "mutates_external_state": false,
      "requires": ["house_cusps", "quadrant counts", "quadrant point names", "hemisphere totals"],
      "guarantees": ["quadrant count integrity", "named-point preservation"]
    }
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

    Each named point is placed into the supplied house frame, mapped to one of
    Rudhyar's four quadrants, and accumulated into the quadrant and hemisphere
    totals.

    Parameters
    ----------
    points : dict[str, float]
        Mapping of point name to ecliptic longitude.
    house_cusps : HouseCusps
        The house frame to use for placement.

    Returns
    -------
    QuadrantEmphasisProfile

    Raises:
        None under normal operation.

    Side effects:
        None
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
    RITE: The Diurnal Cross

    THEOREM: This enum records the four diurnal quadrants defined by the angular frame and the body's semi-diurnal arc.

    RITE OF PURPOSE:
        This enum exists so diurnal position work uses stable quadrant labels
        instead of ad hoc strings. It preserves the fourfold daily-rotation
        framework used by the diurnal products in this Pillar.

    LAW OF OPERATION:
        Responsibilities:
            - Declare DQ1 through DQ4 as the canonical diurnal quadrant labels.
        Non-responsibilities:
            - Does not compute hour angle or arcs.
        Dependencies:
            - Diurnal quadrant doctrine.
        Side effects:
            - None
        Failure behavior:
            - None

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "type": "enum",
      "owns_state": false,
      "mutates_external_state": false,
      "requires": [],
      "guarantees": ["stable diurnal quadrant taxonomy"]
    }
    """

    DQ1 = "DQ1"  # ASC → MC   (eastern, above horizon)
    DQ2 = "DQ2"  # MC  → DSC  (western, above horizon)
    DQ3 = "DQ3"  # DSC → IC   (western, below horizon)
    DQ4 = "DQ4"  # IC  → ASC  (eastern, below horizon)


def _semi_diurnal_arc(dec: float, geo_lat: float) -> float:
    """
    Compute the semi-diurnal arc (SDA) in degrees.

    The result is the body's half-arc above the horizon for the given
    declination and geographic latitude.

    Raises:
        None under normal operation.

    Side effects:
        None
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
    RITE: The Diurnal Position Witness

    THEOREM: This dataclass records one body's position within the diurnal quadrant framework at a given house frame.

    RITE OF PURPOSE:
        This vessel exists so diurnal-frame analysis can preserve the body's
        quadrant, hour angle, horizon state, and proportional progress as one
        coherent result. It keeps the body-frame geometry explicit rather than
        collapsing it to one label. Without it, mundane position truth would be thinned.

    LAW OF OPERATION:
        Responsibilities:
            - Record the body's diurnal quadrant and hour angle.
            - Record semi-diurnal and semi-nocturnal arcs.
            - Record horizon/easternness flags and proportional fraction.
            - Preserve the RA and declination actually used.
        Non-responsibilities:
            - Does not compute the chart's house cusps.
            - Does not interpret the position astrologically.
        Dependencies:
            - Diurnal quadrant doctrine and equatorial conversion surfaces.
        Structural invariants:
            - fraction is constrained to the quadrant interval [0, 1].
        Side effects:
            - None
        Failure behavior:
            - None at the vessel level.

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
    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "type": "diurnal_position_vessel",
      "owns_state": true,
      "mutates_external_state": false,
      "requires": ["quadrant", "hour_angle", "arc lengths", "flags", "ra", "dec"],
      "guarantees": ["single-body diurnal witness"]
    }
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
    Compute a body's position within the diurnal quadrant framework.

    The ecliptic position is converted to RA and declination, the body's
    semi-diurnal arc is evaluated for the observer latitude, and the hour-angle
    branch determines the body's quadrant and fractional progress.

    Parameters
    ----------
    ecl_lon : float
        Ecliptic longitude in degrees.
    ecl_lat : float
        Ecliptic latitude in degrees.
    armc : float
        Right ascension of the Midheaven in degrees.
    obliquity : float
        Obliquity of the ecliptic in degrees.
    geo_lat : float
        Geographic latitude in degrees.

    Returns
    -------
    DiurnalPosition

    Raises:
        None under normal operation.

    Side effects:
        None
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
    RITE: The Diurnal Emphasis Witness

    THEOREM: This dataclass records how a named point set distributes across the four diurnal quadrants.

    RITE OF PURPOSE:
        This vessel exists so chart-wide diurnal emphasis can be preserved as a
        first-class result rather than rederived from per-point positions each
        time. It keeps counts, point names, and per-point positions together in
        one immutable record. Without it, diurnal distribution truth would fragment.

    LAW OF OPERATION:
        Responsibilities:
            - Record diurnal quadrant counts and named-point membership.
            - Preserve the per-point DiurnalPosition records.
            - Record dominant quadrant and horizon/east-west totals.
        Non-responsibilities:
            - Does not compute the individual diurnal positions.
            - Does not interpret the emphasis astrologically.
        Dependencies:
            - DiurnalPosition records produced upstream.
        Structural invariants:
            - dq1_count + dq2_count + dq3_count + dq4_count equals point_count.
        Side effects:
            - None
        Failure behavior:
            - Raises ValueError when stored quadrant totals are inconsistent.

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
    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
      "type": "diurnal_profile_vessel",
      "owns_state": true,
      "mutates_external_state": false,
      "requires": ["point_count", "diurnal counts", "point-name buckets", "positions"],
      "guarantees": ["diurnal count integrity", "per-point position preservation"]
    }
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

    Each named body is converted into a DiurnalPosition, grouped by diurnal
    quadrant, and accumulated into the chart-wide diurnal emphasis totals.

    Parameters
    ----------
    points : dict[str, tuple[float, float]]
        Mapping of point name to ``(ecliptic_longitude, ecliptic_latitude)``.
    armc : float
        Right ascension of the Midheaven in degrees.
    obliquity : float
        Obliquity of the ecliptic in degrees.
    geo_lat : float
        Geographic latitude in degrees.

    Returns
    -------
    DiurnalEmphasisProfile

    Raises:
        None under normal operation.

    Side effects:
        None
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
