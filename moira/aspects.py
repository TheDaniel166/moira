"""
Moira — Aspect Engine
======================

Archetype: Engine

Purpose
-------
Governs detection of ecliptic aspects and declination aspects between
planetary positions, producing structured result vessels with full
qualification context and explicit aspect classification.

Architecture layers
-------------------
This module has twelve distinct concerns, kept intentionally separate:

1. **Core aspect detection** — ``find_aspects``, ``aspects_between``,
   ``aspects_to_point``, ``find_declination_aspects``,
   ``find_out_of_bounds``.
   Pure geometric computations: given positions, return every angular
   relationship that falls within a qualifying orb, and detect bodies
   whose declination exceeds the solar maximum.  Detection semantics
   are stable and must not be silently changed.

2. **Relational truth preservation** — ``AspectData`` and
   ``DeclinationAspect`` result vessels.
   Each admitted aspect records not only *what* was found but *why* it
   qualified: actual angular separation, target angle, orb deviation,
   and applied orb ceiling.  A caller can fully reconstruct the admission
   test from the vessel alone:
   ``abs(separation - angle) == orb`` and ``orb <= allowed_orb``.

3. **Classification** — ``AspectClassification``, ``AspectDomain``,
   ``AspectTier``, ``AspectFamily``.
   Every admitted aspect carries an explicit, deterministic type
   description: the measurement dimension (zodiacal or declination), the
   tier within the canonical aspect set (major, common-minor,
   extended-minor), and the harmonic family (conjunction series,
   trine series, quintile series, etc.).
   Classification is descriptive — it describes what was detected, not
   how it should be interpreted.

4. **Inspectability** — convenience read-only properties on
   ``AspectData`` and ``DeclinationAspect``.
   Pure single-expression derivations of already-stored fields.  No new
   storage, no logic, no policy.  They make common query patterns legible
   without navigating two attribute levels or importing enum constants::

       a.is_major          # tier shorthand
       a.is_zodiacal       # domain shorthand
       a.is_applying       # motion shorthand (True only when applying is True)
       a.is_separating     # motion shorthand (True only when applying is False)
       a.orb_surplus       # allowed_orb - orb  (remaining headroom)

5. **Doctrine inputs** — ``tier``, ``include_minor``, ``orbs``,
   ``orb_factor``, ``declination_orb``.
   Caller-supplied policy knobs that affect which aspects are considered
   and how wide the orb windows are.  They are resolved at detection time
   and are not stored on the vessel.

6. **Policy surface** — ``AspectPolicy``, ``DEFAULT_POLICY``.
   A single frozen dataclass that bundles all doctrine inputs for ecliptic
   and declination detection.  Pass one ``policy`` argument instead of
   four scattered keyword arguments.  When ``policy`` is supplied it takes
   precedence; existing individual parameters remain for backward
   compatibility.

7. **Geometric strength** — ``AspectStrength``, ``aspect_strength``.
   A pure arithmetic derivation of how close to exact an admitted aspect
   is, expressed as four named components: raw ``orb``, ``allowed_orb``,
   ``surplus`` (headroom), and ``exactness`` (1.0 = exact, 0.0 = at
   boundary).  No interpretation, no configuration, no new inputs beyond
   what is already on the vessel.

8. **Temporal state** — ``MotionState``, ``aspect_motion_state``.
   Formalises the motion-aware truth already implicit in the vessel's
   ``applying`` and ``stationary`` fields into a single, explicit,
   named enum value.  Covers every possible field combination without
   ambiguity: APPLYING, SEPARATING, STATIONARY, INDETERMINATE (speeds
   absent), NONE (``DeclinationAspect`` — no motion data at all).

9. **Canonical configuration** — ``CANONICAL_ASPECTS``.
   The complete, explicitly declared set of all 24 aspect types recognised
   and detectable by this engine: 22 zodiacal aspects (5 major, 6
   common-minor, 11 extended-minor) plus 2 declination aspects (Parallel,
   Contra-Parallel).  ``CANONICAL_ASPECTS`` makes the full set inspectable
   at import time without requiring knowledge of ``moira.constants``.

10. **Multi-body pattern layer** — ``AspectPatternKind``, ``AspectPattern``,
    ``find_patterns``.
    Detects structural configurations formed by three or more bodies whose
    pairwise aspects (already admitted by the detection layer) satisfy a
    named topological template: Stellium, T-Square, Grand Trine, Grand Cross,
    and Yod.  Pattern detection is a pure function over a ``list[AspectData]``
    — it does not re-run position arithmetic, does not introduce new doctrine
    inputs, and does not mutate the supplied pairwise vessels.

11. **Relational graph / network layer** — ``AspectGraphNode``, ``AspectGraph``,
    ``build_aspect_graph``.
    Expresses the chart as a deterministic relational network built from
    already-admitted pairwise aspects.  Bodies become nodes; each admitted
    aspect becomes an edge.  The graph layer exposes node degree, per-node
    aspect-name counts, connected components, isolated bodies, and hub
    detection.  It is a pure function over ``list[AspectData]`` — it does not
    re-run position arithmetic, does not alter any vessel, and does not
    introduce new doctrine inputs.  An optional ``bodies`` parameter allows
    degree-0 (isolated) nodes to be declared explicitly.

12. **Harmonic / family intelligence layer** — ``AspectFamilyProfile``,
    ``AspectHarmonicProfile``, ``aspect_harmonic_profile``.
    Derives the harmonic-family distribution of admitted aspects at both the
    chart level and per body.  Reports counts, proportions, and dominant
    families.  The layer is a pure function over ``list[AspectData]`` — it
    does not re-run detection, does not introduce doctrine inputs, and does
    not mutate any vessel.

Future layers (not current scope)
----------------------------------
- Kite, Mystic Rectangle, Grand Quintile, and other oriented or 5-body patterns
- Dignity weighting, reception scoring, or body-specific strength modifiers
- Configurable doctrine tables (e.g. body-specific orb weights)
- Sinister/dexter distinction, antiscion contacts
- Cross-chart (synastry) relational policies
- State-machine tracking for aspect perfection / separation arcs

Boundary declaration
--------------------
Owns: aspect detection logic, orb arithmetic, applying/separating
      determination, stationary detection, the ``AspectData`` and
      ``DeclinationAspect`` result vessels, and the classification layer.
Delegates: aspect definition tables and tier lists to ``moira.constants``,
           angular distance arithmetic to ``moira.coordinates``.

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required. No database access. Pure computation over
position and speed dicts.

Public surface
--------------
``AspectDomain``             — enum: ZODIACAL or DECLINATION.
``AspectTier``               — enum: MAJOR, COMMON_MINOR, EXTENDED_MINOR.
``AspectFamily``             — enum: harmonic family (conjunction, trine, …).
``AspectClassification``     — frozen dataclass bundling domain + tier + family.
``AspectPolicy``             — frozen dataclass bundling all doctrine inputs.
``DEFAULT_POLICY``           — default policy matching current parameter defaults.
``AspectStrength``           — frozen dataclass: orb, allowed_orb, surplus, exactness.
``aspect_strength``          — derive AspectStrength from any admitted vessel.
``MotionState``              — enum: APPLYING, SEPARATING, STATIONARY, INDETERMINATE, NONE.
``aspect_motion_state``      — derive MotionState from any admitted vessel.
``CANONICAL_ASPECTS``        — tuple of all 24 canonical aspect names (22 zodiacal + 2 declination).
``AspectPatternKind``        — enum: STELLIUM, T_SQUARE, GRAND_TRINE, GRAND_CROSS, YOD.
``AspectPattern``            — frozen dataclass: kind, bodies (frozenset), aspects (tuple).
``find_patterns``            — detect multi-body patterns from a list of admitted AspectData.
``AspectGraphNode``          — frozen dataclass: name, degree, edges, family_counts.
``AspectGraph``              — frozen dataclass: nodes, edges, components; hubs/isolated properties.
``build_aspect_graph``       — build a relational aspect graph from a list of admitted AspectData.
``AspectFamilyProfile``      — frozen dataclass: counts, total, proportions, dominant.
``AspectHarmonicProfile``    — frozen dataclass: chart-level profile + per-body profiles.
``aspect_harmonic_profile``  — derive harmonic/family profile from a list of admitted AspectData.
``AspectData``               — vessel for a detected ecliptic aspect.
``DeclinationAspect``        — vessel for a parallel or contra-parallel aspect.
``find_aspects``             — find all aspects in a position dict.
``aspects_between``          — find aspects between two specific bodies.
``aspects_to_point``         — find aspects from a body set to a single point.
``find_declination_aspects`` — find parallels and contra-parallels.

Convenience properties (read-only, derived only)
-------------------------------------------------
``AspectData.is_major``          — True when tier is MAJOR.
``AspectData.is_minor``          — True when tier is not MAJOR.
``AspectData.is_zodiacal``       — True when domain is ZODIACAL.
``AspectData.is_applying``       — True when applying is True (not None or False).
``AspectData.is_separating``     — True when applying is False (not None or True).
``AspectData.orb_surplus``       — allowed_orb minus orb (remaining headroom).
``DeclinationAspect.is_parallel``         — True when aspect is "Parallel".
``DeclinationAspect.is_contra_parallel``  — True when aspect is "Contra-Parallel".
``DeclinationAspect.orb_surplus``         — allowed_orb minus orb.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from itertools import combinations, permutations
from typing import Collection

from .constants import Aspect, AspectDefinition, ASPECT_TIERS, DEFAULT_ORBS
from .coordinates import angular_distance

__all__ = [
    # Constants
    "CANONICAL_ASPECTS",
    "DEFAULT_POLICY",
    # Enums
    "AspectDirection",
    "AspectDomain",
    "AspectFamily",
    "AspectPatternKind",
    "AspectTier",
    "MotionState",
    # Dataclasses
    "AspectClassification",
    "AspectData",
    "AspectFamilyProfile",
    "AspectGraph",
    "AspectGraphNode",
    "AspectHarmonicProfile",
    "AspectPattern",
    "AspectPolicy",
    "AspectStrength",
    "DeclinationAspect",
    # Entry points
    "aspect_harmonic_profile",
    "aspect_motion_state",
    "aspect_strength",
    "aspects_between",
    "aspects_to_point",
    "build_aspect_graph",
    "find_aspects",
    "find_declination_aspects",
    "find_out_of_bounds",
    "find_patterns",
    "find_whole_sign_aspects",
    "OutOfBoundsBody",
    "overcoming",
]


# ---------------------------------------------------------------------------
# Classification layer
# ---------------------------------------------------------------------------

class AspectDomain(str, Enum):
    """
    Measurement dimension of an aspect.

    ZODIACAL    — measured along the ecliptic (longitude separation).
    DECLINATION — measured in celestial latitude (parallel/contra-parallel).
    WHOLE_SIGN  — measured by sign-count (no orb).
    """
    ZODIACAL    = "zodiacal"
    DECLINATION = "declination"
    WHOLE_SIGN  = "whole_sign"


class AspectDirection(str, Enum):
    """
    Zodiacal casting direction of an aspect ray.

    SINISTER — the aspect ray goes forward in zodiacal order (e.g. from
               Aries toward Leo for a trine).
    DEXTER   — the aspect ray goes backward in zodiacal order (e.g. from
               Leo toward Aries for a trine).

    Canon: Ptolemy, Tetrabiblos I.13; Brennan, Hellenistic Astrology, Ch. 11.
    """
    SINISTER = "sinister"
    DEXTER   = "dexter"


class AspectTier(str, Enum):
    """
    Canonical tier within the aspect set, taken directly from
    ``AspectDefinition.is_major`` and membership in ``Aspect.EXTENDED_MINOR``.

    MAJOR          — the five Ptolemaic aspects (0°, 60°, 90°, 120°, 180°).
    COMMON_MINOR   — widely-used minor aspects (30°, 45°, 72°, 135°, 144°, 150°).
    EXTENDED_MINOR — harmonic-series aspects beyond the common minor set.
    """
    MAJOR          = "major"
    COMMON_MINOR   = "common_minor"
    EXTENDED_MINOR = "extended_minor"


class AspectFamily(str, Enum):
    """
    Harmonic family of an ecliptic aspect, derived from the integer divisor
    of 360° that produces the aspect angle.

    Each member groups the fundamental and its multiples::

        CONJUNCTION   — 0° (1st harmonic; union)
        OPPOSITION    — 180° (2nd harmonic; polarity)
        SQUARE        — 90°, 270° (4th harmonic; tension)
        TRINE         — 120°, 240° (3rd harmonic; flow)
        SEXTILE       — 60°, 300° (6th harmonic; opportunity)
        SEMISEXTILE   — 30° (12th harmonic)
        SEMISQUARE    — 45° (8th harmonic)
        SESQUIQUADRATE — 135° (8th harmonic, upper)
        QUINCUNX      — 150° (12th harmonic, upper)
        QUINTILE      — 72°, 144° (5th harmonic; creativity)
        SEPTILE       — 360/7°, 720/7°, 1080/7° (7th harmonic; fate)
        NOVILE        — 40°, 80°, 160° (9th harmonic; integration)
        DECILE        — 36°, 108° (10th harmonic)
        UNDECILE      — 360/11° (11th harmonic)
        QUINDECILE    — 24° (15th harmonic)
        VIGINTILE     — 18° (20th harmonic)
        DECLINATION   — parallel / contra-parallel (out-of-plane dimension)
    """
    CONJUNCTION    = "conjunction"
    OPPOSITION     = "opposition"
    SQUARE         = "square"
    TRINE          = "trine"
    SEXTILE        = "sextile"
    SEMISEXTILE    = "semisextile"
    SEMISQUARE     = "semisquare"
    SESQUIQUADRATE = "sesquiquadrate"
    QUINCUNX       = "quincunx"
    QUINTILE       = "quintile"
    SEPTILE        = "septile"
    NOVILE         = "novile"
    DECILE         = "decile"
    UNDECILE       = "undecile"
    QUINDECILE     = "quindecile"
    VIGINTILE      = "vigintile"
    DECLINATION    = "declination"


@dataclass(frozen=True, slots=True)
class AspectClassification:
    """
    Lean, explicit type description for an admitted aspect.

    Populated once at detection time from the ``AspectDefinition`` record
    used to admit the aspect.  Immutable and deterministic: the same
    aspect name always produces the same classification.

    Fields
    ------
    domain  : measurement dimension (zodiacal or declination).
    tier    : canonical tier (major, common_minor, extended_minor).
    family  : harmonic family grouping.

    Classification is descriptive — it describes what was detected, not
    how it should be interpreted.  Strength, dignity weighting, and
    reception scoring belong to a later policy layer.
    """
    domain: AspectDomain
    tier:   AspectTier
    family: AspectFamily


# ---------------------------------------------------------------------------
# Module-level classification lookup (built once from Aspect.ALL)
# ---------------------------------------------------------------------------

_FAMILY_BY_NAME: dict[str, AspectFamily] = {
    "Conjunction":     AspectFamily.CONJUNCTION,
    "Opposition":      AspectFamily.OPPOSITION,
    "Square":          AspectFamily.SQUARE,
    "Trine":           AspectFamily.TRINE,
    "Sextile":         AspectFamily.SEXTILE,
    "Semisextile":     AspectFamily.SEMISEXTILE,
    "Semisquare":      AspectFamily.SEMISQUARE,
    "Sesquiquadrate":  AspectFamily.SESQUIQUADRATE,
    "Quincunx":        AspectFamily.QUINCUNX,
    "Quintile":        AspectFamily.QUINTILE,
    "Biquintile":      AspectFamily.QUINTILE,
    "Septile":         AspectFamily.SEPTILE,
    "Biseptile":       AspectFamily.SEPTILE,
    "Triseptile":      AspectFamily.SEPTILE,
    "Novile":          AspectFamily.NOVILE,
    "Binovile":        AspectFamily.NOVILE,
    "Quadnovile":      AspectFamily.NOVILE,
    "Decile":          AspectFamily.DECILE,
    "Tredecile":       AspectFamily.DECILE,
    "Undecile":        AspectFamily.UNDECILE,
    "Quindecile":      AspectFamily.QUINDECILE,
    "Vigintile":       AspectFamily.VIGINTILE,
}

_EXTENDED_MINOR_NAMES: frozenset[str] = frozenset(
    adef.name for adef in Aspect.EXTENDED_MINOR
)
_COMMON_MINOR_NAMES: frozenset[str] = frozenset(
    adef.name for adef in Aspect.COMMON_MINOR
)


def _tier_for(adef: AspectDefinition) -> AspectTier:
    if adef.is_major:
        return AspectTier.MAJOR
    if adef.name in _EXTENDED_MINOR_NAMES:
        return AspectTier.EXTENDED_MINOR
    return AspectTier.COMMON_MINOR


_ASPECT_CLASSIFICATION: dict[str, AspectClassification] = {
    adef.name: AspectClassification(
        domain=AspectDomain.ZODIACAL,
        tier=_tier_for(adef),
        family=_FAMILY_BY_NAME[adef.name],
    )
    for adef in Aspect.ALL
}

_PARALLEL_CLASSIFICATION = AspectClassification(
    domain=AspectDomain.DECLINATION,
    tier=AspectTier.MAJOR,
    family=AspectFamily.DECLINATION,
)

_CONTRA_PARALLEL_CLASSIFICATION = AspectClassification(
    domain=AspectDomain.DECLINATION,
    tier=AspectTier.MAJOR,
    family=AspectFamily.DECLINATION,
)


# ---------------------------------------------------------------------------
# Policy surface
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AspectPolicy:
    """
    Doctrine inputs for aspect detection, bundled into a single immutable value.

    Encapsulates all caller-supplied policy knobs so that detection functions
    can accept one structured argument instead of four or five scattered
    keyword parameters.  When a ``policy`` is passed to a detection function
    it takes full precedence over any corresponding individual parameters;
    individual parameters remain available for backward compatibility.

    Fields
    ------
    tier            : aspect tier filter (0=Major, 1=Major+Common Minor,
                      2=All minor, None=use ``include_minor``).
                      Overrides ``include_minor`` when set.
    include_minor   : include common minor aspects when ``tier`` is None.
    orbs            : custom orb table ``{angle: max_orb}``.  When provided,
                      overrides both default orbs and ``orb_factor``.
    orb_factor      : multiplier applied to all default orbs (e.g. 0.5 = tight
                      windows).  Ignored when ``orbs`` is provided.
    declination_orb : orb ceiling for Parallel and Contra-Parallel detection.

    All fields are optional; the defaults reproduce the historical default
    behaviour of all four detection functions.

    Raises
    ------
    ValueError
        If ``orb_factor <= 0``.
        If ``declination_orb < 0``.
    """
    tier:            int | None              = None
    include_minor:   bool                    = True
    orbs:            dict[float, float] | None = None
    orb_factor:      float                   = 1.0
    declination_orb: float                   = 1.0

    def __post_init__(self) -> None:
        if self.orb_factor <= 0:
            raise ValueError(
                f"AspectPolicy: orb_factor must be > 0, got {self.orb_factor!r}. "
                "A zero or negative multiplier produces meaningless orb windows."
            )
        if self.declination_orb < 0:
            raise ValueError(
                f"AspectPolicy: declination_orb must be >= 0, got {self.declination_orb!r}."
            )


DEFAULT_POLICY: AspectPolicy = AspectPolicy()


# ---------------------------------------------------------------------------
# Geometric strength layer
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AspectStrength:
    """
    Pure geometric strength of an admitted aspect, derived entirely from
    the admission context already stored on the result vessel.

    No interpretation, no dignity weighting, no configuration.  Every field
    is a direct arithmetic consequence of ``orb`` and ``allowed_orb``.

    Fields
    ------
    orb         : raw angular deviation from the target angle (degrees).
                  Always non-negative.  Copied directly from the vessel.
    allowed_orb : orb ceiling that was applied at admission.
                  Copied directly from the vessel.
    surplus     : ``allowed_orb - orb``.  Remaining headroom in the window.
                  Always non-negative (admission gate guarantees ``orb <= allowed_orb``).
    exactness   : ``1.0 - orb / allowed_orb``.  Normalised closeness to the
                  target angle within the admitted window.
                  1.0 = exact conjunction with the target angle (orb == 0).
                  0.0 = admitted at the boundary (orb == allowed_orb).
                  Strictly monotonic: smaller orb → higher exactness for any
                  fixed ``allowed_orb``.

    Invariants
    ----------
    - ``0.0 <= orb <= allowed_orb``        (admission gate)
    - ``surplus == allowed_orb - orb``     (arithmetic identity)
    - ``0.0 <= exactness <= 1.0``          (normalised range)
    - ``exactness == 1.0 - orb / allowed_orb``  (derivation identity)

    Comparison: AspectStrength is frozen, so equality and hashing work by
    field value.  Sorting by ``exactness`` descending gives tightest-first
    ordering within a uniform admission context.
    """
    orb:         float
    allowed_orb: float
    surplus:     float
    exactness:   float


def aspect_strength(aspect: AspectData | DeclinationAspect) -> AspectStrength:
    """
    Compute the geometric strength of an admitted aspect vessel.

    Derives all four strength components from the vessel's existing
    ``orb`` and ``allowed_orb`` fields.  No new information is introduced;
    no detection re-computation occurs.

    Parameters
    ----------
    aspect : an ``AspectData`` or ``DeclinationAspect`` instance produced
             by any of the four detection functions.

    Returns
    -------
    ``AspectStrength`` with ``orb``, ``allowed_orb``, ``surplus``, and
    ``exactness`` populated.

    Formula
    -------
    ::

        surplus   = allowed_orb - orb
        exactness = 1.0 - orb / allowed_orb

    Raises
    ------
    ValueError
        If ``allowed_orb <= 0`` (division by zero / meaningless window).
        If ``orb > allowed_orb`` (vessel violates the admission invariant).
    """
    orb         = aspect.orb
    allowed_orb = aspect.allowed_orb
    if allowed_orb <= 0:
        raise ValueError(
            f"aspect_strength: allowed_orb must be > 0, got {allowed_orb!r}. "
            "An orb window of zero or negative width is not a valid admission context."
        )
    if orb > allowed_orb:
        raise ValueError(
            f"aspect_strength: orb ({orb!r}) exceeds allowed_orb ({allowed_orb!r}). "
            "The vessel violates the admission invariant orb <= allowed_orb."
        )
    return AspectStrength(
        orb=orb,
        allowed_orb=allowed_orb,
        surplus=allowed_orb - orb,
        exactness=1.0 - orb / allowed_orb,
    )


# ---------------------------------------------------------------------------
# Temporal-state layer
# ---------------------------------------------------------------------------

class MotionState(str, Enum):
    """
    Explicit temporal-motion state of an admitted aspect, derived from the
    ``applying`` and ``stationary`` fields already preserved on the vessel.

    Covers the complete decision space with no ambiguity:

    APPLYING      — both bodies are in motion and the aspect is closing
                    (``applying is True``, ``stationary is False``).
    SEPARATING    — both bodies are in motion and the aspect is widening
                    (``applying is False``, ``stationary is False``).
    STATIONARY    — at least one body's daily motion is below the stationary
                    threshold (``stationary is True``).  The applying/separating
                    distinction is not meaningful in this condition.
    INDETERMINATE — the vessel was produced without speed data, so the
                    direction of motion cannot be resolved
                    (``applying is None``, ``stationary is False``).
    NONE          — the vessel type carries no motion information at all
                    (``DeclinationAspect``; declination detection never
                    receives speed inputs).
    """
    APPLYING      = "applying"
    SEPARATING    = "separating"
    STATIONARY    = "stationary"
    INDETERMINATE = "indeterminate"
    NONE          = "none"


def aspect_motion_state(aspect: AspectData | DeclinationAspect) -> MotionState:
    """
    Derive the explicit temporal-motion state of an admitted aspect vessel.

    Reads only the ``applying`` and ``stationary`` fields already stored on
    the vessel.  No new information is required.  The mapping is
    deterministic and covers every possible field combination:

    Decision table
    --------------
    ==================  ===========  =========  ==================
    vessel type         stationary   applying   → MotionState
    ==================  ===========  =========  ==================
    DeclinationAspect   —            —          NONE
    AspectData          True         any        STATIONARY
    AspectData          False        True        APPLYING
    AspectData          False        False       SEPARATING
    AspectData          False        None        INDETERMINATE
    ==================  ===========  =========  ==================

    Parameters
    ----------
    aspect : an ``AspectData`` or ``DeclinationAspect`` instance.

    Returns
    -------
    A ``MotionState`` enum member.
    """
    if isinstance(aspect, DeclinationAspect):
        return MotionState.NONE
    if aspect.stationary:
        return MotionState.STATIONARY
    if aspect.applying is True:
        return MotionState.APPLYING
    if aspect.applying is False:
        return MotionState.SEPARATING
    return MotionState.INDETERMINATE


# ---------------------------------------------------------------------------
# Canonical configuration
# ---------------------------------------------------------------------------

CANONICAL_ASPECTS: tuple[str, ...] = (
    # Major (5) — the five Ptolemaic aspects
    "Conjunction",
    "Sextile",
    "Square",
    "Trine",
    "Opposition",
    # Common Minor (6) — widely-used non-Ptolemaic aspects
    "Semisextile",
    "Semisquare",
    "Sesquiquadrate",
    "Quincunx",
    "Quintile",
    "Biquintile",
    # Extended Minor (11) — harmonic-series aspects
    "Septile",
    "Biseptile",
    "Triseptile",
    "Novile",
    "Binovile",
    "Quadnovile",
    "Decile",
    "Tredecile",
    "Undecile",
    "Quindecile",
    "Vigintile",
    # Declination (2) — out-of-plane dimension
    "Parallel",
    "Contra-Parallel",
)
"""
The complete set of 24 aspect names recognised and detectable by this engine.

Composition
-----------
- 5 major (Ptolemaic): Conjunction, Sextile, Square, Trine, Opposition
- 6 common-minor: Semisextile, Semisquare, Sesquiquadrate, Quincunx,
  Quintile, Biquintile
- 11 extended-minor: Septile series (3), Novile series (3), Decile
  series (2), Undecile, Quindecile, Vigintile
- 2 declination: Parallel, Contra-Parallel

The 22 zodiacal names correspond 1-to-1 with entries in ``Aspect.ALL``
from ``moira.constants``.  The 2 declination names are produced exclusively
by ``find_declination_aspects``.

This tuple is declaration-only; it carries no detection logic.
"""


# ---------------------------------------------------------------------------
# Multi-body pattern layer
# ---------------------------------------------------------------------------

class AspectPatternKind(str, Enum):
    """
    Kind of multi-body aspect pattern.

    Implemented (detectable by ``find_patterns``)
    ----------------------------------------------
    STELLIUM    — three or more bodies within mutual Conjunction orbs.
                  Minimum size: 3 bodies; no maximum imposed.
    T_SQUARE    — three bodies: one Opposition and two Squares forming a
                  right-angle cross (the apex body squares both poles).
    GRAND_TRINE — three bodies each separated by a Trine (120°), forming
                  an equilateral triangle in the chart.
    GRAND_CROSS — four bodies: two Oppositions and four Squares forming a
                  square cross (each body squares its two neighbours and
                  opposes the one across).
    YOD         — three bodies: two Quincunxes (150°) sharing an apex and
                  a Sextile (60°) connecting the base pair.  Also called
                  the Finger of God.

    Deferred (not yet implemented)
    ------------------------------
    Kite, Mystic Rectangle, Grand Quintile, and other oriented or 5-body
    patterns require topology reasoning not yet in scope.
    """
    STELLIUM    = "stellium"
    T_SQUARE    = "t_square"
    GRAND_TRINE = "grand_trine"
    GRAND_CROSS = "grand_cross"
    YOD         = "yod"


@dataclass(frozen=True, slots=True)
class AspectPattern:
    """
    A detected multi-body aspect pattern, derived entirely from
    already-admitted pairwise ``AspectData`` results.

    Pattern detection consumes a ``list[AspectData]`` produced by
    ``find_aspects`` or ``aspects_between``; it does not re-run position
    arithmetic or change pairwise semantics.

    Fields
    ------
    kind    : the ``AspectPatternKind`` identifying the structural type.
    bodies  : frozenset of body names that participate in the pattern.
    aspects : tuple of the contributing ``AspectData`` instances, sorted
              by ``(body1, body2, aspect)`` for deterministic ordering
              independent of the input list ordering.

    Structural invariants
    ---------------------
    - ``len(bodies) >= 3`` for all implemented patterns
      (STELLIUM may have 3+; T_SQUARE, GRAND_TRINE, YOD have exactly 3;
       GRAND_CROSS has exactly 4).
    - ``len(aspects) >= 3`` for all implemented patterns
      (STELLIUM: 3 for 3-body, 6 for 4-body; T_SQUARE: 3;
       GRAND_TRINE: 3; GRAND_CROSS: 6; YOD: 3).
    - Every body named in ``bodies`` appears in at least one aspect in
      ``aspects``.
    - ``aspects`` is sorted by ``(body1, body2, aspect)``; this ordering
      is stable and independent of the order in which pairwise aspects
      were supplied to ``find_patterns``.
    - The vessel is immutable; detection does not store new state.
    """
    kind:    AspectPatternKind
    bodies:  frozenset[str]
    aspects: tuple[AspectData, ...]


# ---------------------------------------------------------------------------
# Pattern detection helpers (internal)
# ---------------------------------------------------------------------------

def _aspect_index(
    aspects: list[AspectData],
) -> dict[frozenset[str], list[AspectData]]:
    """Build a pair→aspects index for fast structural queries."""
    idx: dict[frozenset[str], list[AspectData]] = {}
    for a in aspects:
        key = frozenset((a.body1, a.body2))
        idx.setdefault(key, []).append(a)
    return idx


def _aspects_of_kind(
    idx: dict[frozenset[str], list[AspectData]],
    b1: str,
    b2: str,
    *names: str,
) -> list[AspectData]:
    """Return aspects between b1/b2 whose name is in ``names``."""
    return [a for a in idx.get(frozenset((b1, b2)), [])
            if a.aspect in names]


def _find_stellia(
    aspects: list[AspectData],
    idx: dict[frozenset[str], list[AspectData]],
) -> list[AspectPattern]:
    """
    Detect Stellia: groups of ≥3 bodies in mutual Conjunction.

    Two bodies are 'conjoined' when at least one Conjunction aspect between
    them is present in the admitted list.  A stellium is a maximal clique
    of ≥3 mutually-conjoined bodies.

    Maximality: a smaller subset is not reported if it is fully contained
    within an already-reported larger stellium.
    """
    all_bodies: set[str] = {a.body1 for a in aspects} | {a.body2 for a in aspects}

    conjoined: dict[str, set[str]] = {b: set() for b in all_bodies}
    for a in aspects:
        if a.aspect == "Conjunction":
            conjoined[a.body1].add(a.body2)
            conjoined[a.body2].add(a.body1)

    cliques: list[frozenset[str]] = []
    bodies_list = sorted(all_bodies)

    def _extend(current: frozenset[str], candidates: list[str]) -> None:
        is_maximal = True
        for c in candidates:
            if current.issubset(conjoined[c] | {c}):
                _extend(current | {c}, [x for x in candidates if x > c])
                is_maximal = False
        if is_maximal and len(current) >= 3:
            cliques.append(current)

    for i, b in enumerate(bodies_list):
        _extend(frozenset({b}), [x for x in bodies_list if x > b])

    results: list[AspectPattern] = []
    seen: set[frozenset[str]] = set()
    for clique in cliques:
        if any(clique <= s for s in seen):
            continue
        seen.add(clique)
        clique_aspects: list[AspectData] = []
        bl = sorted(clique)
        for i in range(len(bl)):
            for j in range(i + 1, len(bl)):
                clique_aspects.extend(_aspects_of_kind(idx, bl[i], bl[j], "Conjunction"))
        results.append(AspectPattern(
            kind=AspectPatternKind.STELLIUM,
            bodies=clique,
            aspects=tuple(sorted(clique_aspects, key=lambda a: (a.body1, a.body2, a.aspect))),
        ))
    return results


def _find_t_squares(
    idx: dict[frozenset[str], list[AspectData]],
    all_bodies: set[str],
) -> list[AspectPattern]:
    """
    Detect T-Squares: A opposes B, C squares both A and B.

    C is the apex; A–B is the opposition axis.  All three permutations of
    apex are checked.
    """
    results: list[AspectPattern] = []
    seen: set[frozenset[str]] = set()
    bl = sorted(all_bodies)
    for i, a in enumerate(bl):
        for j in range(i + 1, len(bl)):
            b = bl[j]
            opp = _aspects_of_kind(idx, a, b, "Opposition")
            if not opp:
                continue
            for k in range(len(bl)):
                c = bl[k]
                if c == a or c == b:
                    continue
                sq_ac = _aspects_of_kind(idx, a, c, "Square")
                sq_bc = _aspects_of_kind(idx, b, c, "Square")
                if sq_ac and sq_bc:
                    key = frozenset((a, b, c))
                    if key not in seen:
                        seen.add(key)
                        contrib = opp[:1] + sq_ac[:1] + sq_bc[:1]
                        results.append(AspectPattern(
                            kind=AspectPatternKind.T_SQUARE,
                            bodies=key,
                            aspects=tuple(sorted(contrib, key=lambda x: (x.body1, x.body2, x.aspect))),
                        ))
    return results


def _find_grand_trines(
    idx: dict[frozenset[str], list[AspectData]],
    all_bodies: set[str],
) -> list[AspectPattern]:
    """
    Detect Grand Trines: A trines B, B trines C, A trines C.
    """
    results: list[AspectPattern] = []
    seen: set[frozenset[str]] = set()
    bl = sorted(all_bodies)
    for i, a in enumerate(bl):
        for j in range(i + 1, len(bl)):
            b = bl[j]
            tr_ab = _aspects_of_kind(idx, a, b, "Trine")
            if not tr_ab:
                continue
            for k in range(j + 1, len(bl)):
                c = bl[k]
                tr_bc = _aspects_of_kind(idx, b, c, "Trine")
                tr_ac = _aspects_of_kind(idx, a, c, "Trine")
                if tr_bc and tr_ac:
                    key = frozenset((a, b, c))
                    if key not in seen:
                        seen.add(key)
                        contrib = tr_ab[:1] + tr_bc[:1] + tr_ac[:1]
                        results.append(AspectPattern(
                            kind=AspectPatternKind.GRAND_TRINE,
                            bodies=key,
                            aspects=tuple(sorted(contrib, key=lambda x: (x.body1, x.body2, x.aspect))),
                        ))
    return results


def _find_grand_crosses(
    idx: dict[frozenset[str], list[AspectData]],
    all_bodies: set[str],
) -> list[AspectPattern]:
    """
    Detect Grand Crosses: four bodies forming two opposition axes with
    each body squaring its two neighbours.

    Required edges: A–B opp, C–D opp, A–C sq, A–D sq, B–C sq, B–D sq.
    All valid labellings of the four bodies are checked.
    """
    results: list[AspectPattern] = []
    seen: set[frozenset[str]] = set()

    for quad in combinations(sorted(all_bodies), 4):
        key = frozenset(quad)
        if key in seen:
            continue
        for a, b, c, d in permutations(quad):
            opp_ab = _aspects_of_kind(idx, a, b, "Opposition")
            opp_cd = _aspects_of_kind(idx, c, d, "Opposition")
            sq_ac  = _aspects_of_kind(idx, a, c, "Square")
            sq_ad  = _aspects_of_kind(idx, a, d, "Square")
            sq_bc  = _aspects_of_kind(idx, b, c, "Square")
            sq_bd  = _aspects_of_kind(idx, b, d, "Square")
            if opp_ab and opp_cd and sq_ac and sq_ad and sq_bc and sq_bd:
                seen.add(key)
                contrib = (
                    opp_ab[:1] + opp_cd[:1] +
                    sq_ac[:1] + sq_ad[:1] + sq_bc[:1] + sq_bd[:1]
                )
                results.append(AspectPattern(
                    kind=AspectPatternKind.GRAND_CROSS,
                    bodies=key,
                    aspects=tuple(sorted(contrib, key=lambda x: (x.body1, x.body2, x.aspect))),
                ))
                break
    return results


def _find_yods(
    idx: dict[frozenset[str], list[AspectData]],
    all_bodies: set[str],
) -> list[AspectPattern]:
    """
    Detect Yods (Finger of God): apex A is quincunx both B and C,
    and B and C are sextile each other.

    All three permutations of apex are checked.
    """
    results: list[AspectPattern] = []
    seen: set[frozenset[str]] = set()
    bl = sorted(all_bodies)
    for i, b in enumerate(bl):
        for j in range(i + 1, len(bl)):
            c = bl[j]
            sext = _aspects_of_kind(idx, b, c, "Sextile")
            if not sext:
                continue
            for a in bl:
                if a == b or a == c:
                    continue
                q_ab = _aspects_of_kind(idx, a, b, "Quincunx")
                q_ac = _aspects_of_kind(idx, a, c, "Quincunx")
                if q_ab and q_ac:
                    key = frozenset((a, b, c))
                    if key not in seen:
                        seen.add(key)
                        contrib = sext[:1] + q_ab[:1] + q_ac[:1]
                        results.append(AspectPattern(
                            kind=AspectPatternKind.YOD,
                            bodies=key,
                            aspects=tuple(sorted(contrib, key=lambda x: (x.body1, x.body2, x.aspect))),
                        ))
    return results


def find_patterns(aspects: list[AspectData]) -> list[AspectPattern]:
    """
    Detect multi-body aspect patterns from a list of admitted pairwise aspects.

    Pattern detection operates entirely on the supplied ``AspectData`` list.
    No positions, speeds, or external inputs are used.  Pairwise detection
    semantics are not changed.

    Implemented patterns (see ``AspectPatternKind`` for full doctrine)
    ------------------------------------------------------------------
    STELLIUM    — ≥3 bodies in mutual Conjunction.
    T_SQUARE    — 3 bodies: one Opposition + two Squares (apex squares both poles).
    GRAND_TRINE — 3 bodies: three mutual Trines.
    GRAND_CROSS — 4 bodies: two Oppositions + four Squares forming a closed cross.
    YOD         — 3 bodies: Sextile base + two Quincunxes meeting at an apex.

    Each detected pattern is reported at most once per unique body set.
    Sub-patterns contained within a larger Stellium are suppressed; all
    other pattern types are independent (a Grand Cross may also contain
    T-Squares; both are reported).

    Determinism contract
    --------------------
    The output is fully determined by the *logical content* of the input
    list, not by its ordering.  Specifically:

    - ``bodies`` is a ``frozenset`` — order-independent.
    - ``aspects`` inside each pattern is sorted by ``(body1, body2, aspect)``
      — identical for any permutation of the input list that contains the
      same logical pairwise aspects.
    - Patterns of the same kind are emitted in the order determined by
      sorted body-name iteration (the outer loops in each helper always
      iterate over ``sorted(all_bodies)``).

    Parameters
    ----------
    aspects : list of ``AspectData`` as returned by ``find_aspects``,
              ``aspects_between``, or any combination.

    Returns
    -------
    List of ``AspectPattern``, in the order: Stellia, T-Squares, Grand
    Trines, Grand Crosses, Yods.  Empty list when no pattern is found.
    """
    if not aspects:
        return []

    idx       = _aspect_index(aspects)
    all_b: set[str] = {a.body1 for a in aspects} | {a.body2 for a in aspects}

    return (
        _find_stellia(aspects, idx)
        + _find_t_squares(idx, all_b)
        + _find_grand_trines(idx, all_b)
        + _find_grand_crosses(idx, all_b)
        + _find_yods(idx, all_b)
    )


# ---------------------------------------------------------------------------
# Relational graph / network layer
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AspectGraphNode:
    """
    A node in the aspect graph, representing one celestial body.

    Fields
    ------
    name         : body name, matching ``AspectData.body1`` / ``body2``.
    degree       : number of pairwise aspects incident to this node.
    edges        : tuple of all ``AspectData`` instances in which this body
                   participates, sorted by ``(body1, body2, aspect)``.
    family_counts: mapping of aspect name → count of admitted aspects of
                   that name incident to this node.  Keys are ``AspectData.aspect``
                   strings (e.g. ``"Trine"``, ``"Conjunction"``).  Empty dict
                   when ``degree == 0``.

    Invariants
    ----------
    - ``degree == len(edges)``
    - ``sum(family_counts.values()) == degree``
    - Every entry in ``edges`` has ``body1 == name`` or ``body2 == name``.
    - ``edges`` is sorted by ``(body1, body2, aspect)`` — deterministic and
      independent of input list ordering.
    """
    name:          str
    degree:        int
    edges:         tuple[AspectData, ...]
    family_counts: dict[str, int]


@dataclass(frozen=True, slots=True)
class AspectGraph:
    """
    A relational graph built from a list of admitted pairwise ``AspectData``
    results, exposing the chart as a deterministic aspect network.

    The graph is a pure structural view — it does not re-run position
    arithmetic, does not introduce new doctrine inputs, and does not mutate
    any supplied aspect vessel.

    Fields
    ------
    nodes      : tuple of ``AspectGraphNode``, one per body, sorted by name.
                 Includes any body supplied in ``bodies`` to
                 ``build_aspect_graph`` that has no admitted aspects (degree 0).
    edges      : tuple of all input ``AspectData``, sorted by
                 ``(body1, body2, aspect)``.
    components : tuple of connected components, each a ``frozenset[str]`` of
                 body names.  Sorted by ``(min(component), len(component))``
                 ascending — deterministic regardless of input ordering.

    Derived read-only properties
    ----------------------------
    ``hubs``          — ``tuple[AspectGraphNode, ...]`` of node(s) with the
                        highest degree.  Empty tuple when all nodes are isolated.
    ``isolated``      — ``tuple[AspectGraphNode, ...]`` of nodes with degree 0,
                        sorted by name.

    Determinism contract
    --------------------
    - ``nodes`` is sorted by name.
    - ``edges`` is sorted by ``(body1, body2, aspect)``.
    - ``components`` is sorted by ``(min(component), len(component))``.
    - ``hubs`` and ``isolated`` are derived solely from ``nodes`` and are
      therefore equally deterministic.
    - The output is fully determined by the logical content of the input; any
      permutation of the input list produces identical output.
    """
    nodes:      tuple[AspectGraphNode, ...]
    edges:      tuple[AspectData, ...]
    components: tuple[frozenset[str], ...]

    @property
    def hubs(self) -> tuple[AspectGraphNode, ...]:
        """Node(s) with the highest degree.  Empty tuple when no edges exist."""
        if not self.nodes:
            return ()
        max_deg = max(n.degree for n in self.nodes)
        if max_deg == 0:
            return ()
        return tuple(n for n in self.nodes if n.degree == max_deg)

    @property
    def isolated(self) -> tuple[AspectGraphNode, ...]:
        """Nodes with degree 0, sorted by name."""
        return tuple(n for n in self.nodes if n.degree == 0)


def build_aspect_graph(
    aspects: list[AspectData],
    bodies: Collection[str] | None = None,
) -> AspectGraph:
    """
    Build a relational aspect graph from a list of admitted pairwise aspects.

    The graph layer is a pure function over already-admitted ``AspectData``
    results.  It does not re-run position arithmetic and does not alter any
    supplied vessel.

    Parameters
    ----------
    aspects : list of ``AspectData`` as returned by ``find_aspects``,
              ``aspects_between``, or any combination.
    bodies  : optional collection of body names that must appear as nodes
              even if they form no admitted aspect (degree-0 / isolated nodes).
              Names already present via ``aspects`` are not duplicated.

    Returns
    -------
    ``AspectGraph`` with deterministic node, edge, component, hub, and
    isolated-node views.  An empty ``aspects`` list with no ``bodies`` returns
    a graph with no nodes, no edges, and no components.

    Determinism contract
    --------------------
    The output is fully determined by the logical content of ``aspects`` and
    ``bodies``, not by input ordering.  Any permutation of ``aspects`` and any
    ordering of ``bodies`` produces identical output.
    """
    all_names: set[str] = set()
    for a in aspects:
        all_names.add(a.body1)
        all_names.add(a.body2)
    if bodies is not None:
        all_names.update(bodies)

    adjacency: dict[str, list[AspectData]] = {n: [] for n in all_names}
    for a in aspects:
        adjacency[a.body1].append(a)
        adjacency[a.body2].append(a)

    nodes: list[AspectGraphNode] = []
    for name in sorted(all_names):
        incident = sorted(adjacency[name], key=lambda x: (x.body1, x.body2, x.aspect))
        fc: dict[str, int] = {}
        for a in incident:
            fc[a.aspect] = fc.get(a.aspect, 0) + 1
        nodes.append(AspectGraphNode(
            name=name,
            degree=len(incident),
            edges=tuple(incident),
            family_counts=fc,
        ))

    sorted_edges = tuple(
        sorted(aspects, key=lambda a: (a.body1, a.body2, a.aspect))
    )

    components = tuple(
        sorted(
            _connected_components(all_names, aspects),
            key=lambda c: (min(c), len(c)),
        )
    )

    return AspectGraph(
        nodes=tuple(nodes),
        edges=sorted_edges,
        components=components,
    )


def _connected_components(
    all_names: set[str],
    aspects: list[AspectData],
) -> list[frozenset[str]]:
    """
    Compute connected components of the aspect graph via union-find.

    Bodies linked by at least one aspect are in the same component.
    Bodies with no aspects (isolated) form singleton components.
    """
    parent: dict[str, str] = {n: n for n in all_names}

    def _find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def _union(x: str, y: str) -> None:
        rx, ry = _find(x), _find(y)
        if rx != ry:
            parent[rx] = ry

    for a in aspects:
        _union(a.body1, a.body2)

    groups: dict[str, set[str]] = {}
    for n in all_names:
        root = _find(n)
        groups.setdefault(root, set()).add(n)

    return [frozenset(g) for g in groups.values()]


# ---------------------------------------------------------------------------
# Harmonic / family intelligence layer
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AspectFamilyProfile:
    """
    Family-level distribution for a set of admitted aspects.

    A single instance covers either the full chart (all admitted aspects)
    or one body's incident aspects within a chart.  The vessel is immutable
    and fully derived from the input; it carries no doctrine inputs and
    performs no interpretation.

    Fields
    ------
    counts      : mapping of ``AspectFamily`` → count of admitted aspects in
                  that family.  Only families with at least one aspect present
                  are included.  Keys follow ``AspectFamily`` declaration order.
    total       : total number of admitted aspects covered by this profile.
                  Equal to ``sum(counts.values())``.
    proportions : mapping of ``AspectFamily`` → ``count / total``.  Same key
                  set as ``counts``.  Empty dict when ``total == 0``.
    dominant    : tuple of ``AspectFamily`` values tied at the highest count,
                  sorted by ``AspectFamily.value`` (alphabetical) for
                  determinism.  Empty tuple when ``total == 0``.

    Invariants
    ----------
    - ``sum(counts.values()) == total``
    - ``len(proportions) == len(counts)``
    - ``abs(sum(proportions.values()) - 1.0) < 1e-9`` when ``total > 0``
    - Every member of ``dominant`` is a key in ``counts``
    - All proportions are in ``[0.0, 1.0]``
    """
    counts:      dict[AspectFamily, int]
    total:       int
    proportions: dict[AspectFamily, float]
    dominant:    tuple[AspectFamily, ...]


@dataclass(frozen=True, slots=True)
class AspectHarmonicProfile:
    """
    Chart-level harmonic analysis derived from all admitted aspects.

    Built by ``aspect_harmonic_profile``; consumes a ``list[AspectData]``
    without re-running position arithmetic or altering any vessel.

    Fields
    ------
    chart   : ``AspectFamilyProfile`` aggregating all admitted aspects.
    by_body : mapping of body name → ``AspectFamilyProfile`` for that body's
              incident aspects.  Every body that appears in at least one
              admitted aspect has an entry.  Sorted by body name (dict
              preserves insertion order in Python 3.7+).

    Determinism contract
    --------------------
    The output is fully determined by the logical content of the input list.
    Any permutation of the input produces identical ``chart`` and ``by_body``
    values.  ``by_body`` keys are inserted in sorted body-name order.
    """
    chart:   AspectFamilyProfile
    by_body: dict[str, AspectFamilyProfile]


def _build_family_profile(aspects: list[AspectData]) -> AspectFamilyProfile:
    """
    Build an ``AspectFamilyProfile`` from a flat list of ``AspectData``.

    Family resolution order
    -----------------------
    1. ``a.classification.family`` when ``classification`` is not ``None``
       (the normal case for vessels produced by detection functions).
    2. ``_FAMILY_BY_NAME[a.aspect]`` when ``classification`` is ``None``
       and the aspect name is a known zodiacal name.
    3. ``AspectFamily.DECLINATION`` as the fallback for any unrecognised
       name (covers "Parallel", "Contra-Parallel", or custom names).
    """
    raw: dict[AspectFamily, int] = {}
    for a in aspects:
        if a.classification is not None:
            fam = a.classification.family
        else:
            fam = _FAMILY_BY_NAME.get(a.aspect, AspectFamily.DECLINATION)
        raw[fam] = raw.get(fam, 0) + 1

    total = len(aspects)
    counts: dict[AspectFamily, int] = {
        fam: raw[fam]
        for fam in AspectFamily
        if fam in raw
    }

    if total == 0:
        return AspectFamilyProfile(
            counts={}, total=0, proportions={}, dominant=()
        )

    proportions: dict[AspectFamily, float] = {
        fam: cnt / total
        for fam, cnt in counts.items()
    }

    max_count = max(counts.values())
    dominant = tuple(
        sorted(
            (fam for fam, cnt in counts.items() if cnt == max_count),
            key=lambda f: f.value,
        )
    )

    return AspectFamilyProfile(
        counts=counts,
        total=total,
        proportions=proportions,
        dominant=dominant,
    )


def aspect_harmonic_profile(aspects: list[AspectData]) -> AspectHarmonicProfile:
    """
    Derive a chart-level harmonic / family profile from admitted pairwise aspects.

    The harmonic layer is a pure function over an already-admitted
    ``list[AspectData]``.  It does not re-run position arithmetic, does not
    introduce new doctrine inputs, and does not mutate any supplied vessel.

    Parameters
    ----------
    aspects : list of ``AspectData`` as returned by ``find_aspects``,
              ``aspects_between``, or any combination.

    Returns
    -------
    ``AspectHarmonicProfile`` with:

    - ``chart``   — aggregate ``AspectFamilyProfile`` over all aspects.
    - ``by_body`` — per-body ``AspectFamilyProfile`` for each body that
                    appears in at least one admitted aspect.

    An empty input list returns a profile with zero counts and empty
    ``dominant`` / ``by_body``.

    Determinism contract
    --------------------
    The output is fully determined by the logical content of ``aspects``.
    Any permutation of the input list produces identical output.
    ``by_body`` keys are in sorted body-name order.
    """
    chart = _build_family_profile(aspects)

    adjacency: dict[str, list[AspectData]] = {}
    for a in aspects:
        adjacency.setdefault(a.body1, []).append(a)
        adjacency.setdefault(a.body2, []).append(a)

    by_body: dict[str, AspectFamilyProfile] = {
        name: _build_family_profile(adjacency[name])
        for name in sorted(adjacency)
    }

    return AspectHarmonicProfile(chart=chart, by_body=by_body)


# ---------------------------------------------------------------------------
# Result vessels
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class AspectData:
    """
    RITE: The Aspect Vessel — a detected angular relationship between two bodies.

    THEOREM: Holds the two body names, aspect name and symbol, target angle,
    actual angular separation, orb deviation, applied orb ceiling,
    applying/separating flag, stationary flag, and explicit classification
    for a single detected ecliptic aspect.

    RITE OF PURPOSE:
        Serves the Aspect Engine as the canonical result vessel for all
        ecliptic aspect detections.  The vessel preserves full admission
        context (Phase 1) and carries an explicit classification (Phase 2)
        so that a caller can determine not only *why* the aspect qualified
        but *what kind* of aspect it is, without reconstructing that
        knowledge from the name string.

    LAW OF OPERATION:
        Responsibilities:
            - Store both body names, aspect name, Unicode symbol, target
              angle, actual angular separation, orb deviation (always
              positive), allowed orb ceiling, applying/separating flag,
              stationary flag, and ``AspectClassification``.
            - Expose read-only convenience properties that are pure
              single-expression derivations of already-stored fields.
        Non-responsibilities:
            - Does not detect aspects (delegated to ``find_aspects`` and
              related functions).
            - Does not compute angular distances.
            - Does not assign strength, dignity weighting, or interpretation.
        Dependencies:
            - Populated by ``find_aspects()``, ``aspects_between()``, or
              ``aspects_to_point()``.
        Structural invariants:
            - ``orb`` is always non-negative and equals
              ``abs(separation - angle)`` to floating-point precision.
            - ``orb <= allowed_orb`` is always true for any stored vessel.
            - ``orb_surplus == allowed_orb - orb >= 0``.
            - ``separation`` is the raw angular distance (0–180°) between
              the two bodies as computed by ``angular_distance``.
            - ``allowed_orb`` is the orb ceiling actually applied (post
              orb_factor, post custom-orbs override).
            - ``classification.domain`` is always ``AspectDomain.ZODIACAL``
              for this vessel.
            - ``applying`` is ``None`` when either body is stationary or
              speeds are unavailable.
            - ``stationary`` is ``True`` when either body's speed is below
              0.01 deg/day.
            - ``is_applying`` and ``is_separating`` are mutually exclusive
              and both are ``False`` when ``applying`` is ``None``.
        Succession stance: terminal — not designed for subclassing.

    Admission identity (verifiable from vessel fields)::

        orb        == abs(separation - angle)          # geometric deviation
        orb        <= allowed_orb                      # admission gate
        separation  = angular_distance(lon1, lon2)     # raw input

    Canon: Ptolemy, "Tetrabiblos" I; Lilly, "Christian Astrology" (1647).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.aspects.AspectData",
        "risk": "high",
        "api": {
            "public_methods": ["__repr__"],
            "public_attributes": [
                "body1", "body2", "aspect", "symbol",
                "angle", "separation", "orb", "allowed_orb",
                "applying", "stationary", "classification"
            ],
            "public_properties": [
                "is_major", "is_minor", "is_zodiacal",
                "is_applying", "is_separating", "orb_surplus"
            ]
        },
        "state": {
            "mutable": false,
            "fields": [
                "body1", "body2", "aspect", "symbol",
                "angle", "separation", "orb", "allowed_orb",
                "applying", "stationary", "classification"
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
            "policy": "caller ensures valid positions before construction"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]
    """
    body1:          str                  # name of first body
    body2:          str                  # name of second body
    aspect:         str                  # aspect name e.g. "Trine"
    symbol:         str                  # Unicode glyph e.g. "△"
    angle:          float                # target aspect angle (e.g. 120.0°)
    separation:     float                # actual angular distance between body1 and body2
    orb:            float                # |separation - angle| (always non-negative)
    allowed_orb:    float                # orb ceiling used for admission (post orb_factor / custom-orbs)
    applying:       bool | None = None   # True=applying, False=separating, None=unknown/stationary
    stationary:     bool        = False  # True when either body's speed is < 0.01°/day
    classification: AspectClassification | None = None  # explicit type description
    direction:      AspectDirection | None = None  # sinister/dexter from body1's perspective

    # ------------------------------------------------------------------
    # Inspectability — read-only, derived-only convenience properties
    # ------------------------------------------------------------------

    @property
    def is_major(self) -> bool:
        """True when this aspect belongs to the five Ptolemaic major aspects."""
        return (self.classification is not None
                and self.classification.tier is AspectTier.MAJOR)

    @property
    def is_minor(self) -> bool:
        """True when this aspect is not a Ptolemaic major aspect."""
        return (self.classification is not None
                and self.classification.tier is not AspectTier.MAJOR)

    @property
    def is_zodiacal(self) -> bool:
        """True when this aspect is measured along the ecliptic (always True for AspectData)."""
        return (self.classification is not None
                and self.classification.domain is AspectDomain.ZODIACAL)

    @property
    def is_applying(self) -> bool:
        """True only when ``applying`` is exactly ``True`` (not ``None``)."""
        return self.applying is True

    @property
    def is_separating(self) -> bool:
        """True only when ``applying`` is exactly ``False`` (not ``None``)."""
        return self.applying is False

    @property
    def orb_surplus(self) -> float:
        """Remaining headroom in the orb window: ``allowed_orb - orb``.  Always >= 0."""
        return self.allowed_orb - self.orb

    def __repr__(self) -> str:
        app = " applying" if self.applying else " separating" if self.applying is False else ""
        sta = " [stationary]" if self.stationary else ""
        return f"{self.body1} {self.symbol} {self.body2}  (orb {self.orb:+.2f}°){app}{sta}"


@dataclass(slots=True)
class DeclinationAspect:
    """
    RITE: The Declination Vessel — a parallel or contra-parallel between two bodies.

    THEOREM: Holds the two body names, aspect type, individual signed
    declinations, orb deviation, allowed orb ceiling, and explicit
    classification for a single detected parallel or contra-parallel.

    RITE OF PURPOSE:
        Serves the Aspect Engine as the canonical result vessel for declination
        aspect detections.  The vessel preserves full admission context
        (Phase 1) and carries an explicit classification (Phase 2) so that a
        caller can interrogate the measurement dimension and family without
        inspecting the ``aspect`` string.

    LAW OF OPERATION:
        Responsibilities:
            - Store both body names, aspect type ("Parallel" or
              "Contra-Parallel"), individual signed declinations, orb
              deviation, allowed orb ceiling, and ``AspectClassification``.
            - Expose read-only convenience properties that are pure
              single-expression derivations of already-stored fields.
        Non-responsibilities:
            - Does not detect declination aspects (delegated to
              ``find_declination_aspects``).
            - Does not compute declinations from ecliptic coordinates.
            - Does not assign strength or interpretation.
        Dependencies:
            - Populated exclusively by ``find_declination_aspects()``.
        Structural invariants:
            - ``aspect`` is always "Parallel" or "Contra-Parallel".
            - ``orb`` is always non-negative.
            - For a Parallel: ``orb == abs(dec1 - dec2)``.
            - For a Contra-Parallel: ``orb == abs(dec1 + dec2)``.
            - ``orb <= allowed_orb`` is always true for any stored vessel.
            - ``orb_surplus == allowed_orb - orb >= 0``.
            - ``dec1`` and ``dec2`` are always in [-90, +90].
            - ``classification.domain`` is always ``AspectDomain.DECLINATION``
              for this vessel.
            - ``classification.family`` is always ``AspectFamily.DECLINATION``.
            - ``is_parallel`` and ``is_contra_parallel`` are mutually exclusive.
        Succession stance: terminal — not designed for subclassing.

    Canon: Ptolemy, "Tetrabiblos" I; Lilly, "Christian Astrology" (1647).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.aspects.DeclinationAspect",
        "risk": "high",
        "api": {
            "public_methods": ["__repr__"],
            "public_attributes": [
                "body1", "body2", "aspect", "dec1", "dec2",
                "orb", "allowed_orb", "classification"
            ],
            "public_properties": [
                "is_parallel", "is_contra_parallel", "orb_surplus"
            ]
        },
        "state": {
            "mutable": false,
            "fields": [
                "body1", "body2", "aspect", "dec1", "dec2",
                "orb", "allowed_orb", "classification"
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
            "policy": "caller ensures valid declinations before construction"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]
    """
    body1:          str
    body2:          str
    aspect:         str    # "Parallel" or "Contra-Parallel"
    dec1:           float  # declination of body1 (degrees, signed, ±90)
    dec2:           float  # declination of body2 (degrees, signed, ±90)
    orb:            float  # |difference| in degrees (always non-negative)
    allowed_orb:    float  # orb ceiling used for admission
    classification: AspectClassification | None = None  # always DECLINATION domain

    # ------------------------------------------------------------------
    # Inspectability — read-only, derived-only convenience properties
    # ------------------------------------------------------------------

    @property
    def is_parallel(self) -> bool:
        """True when both bodies are on the same side of the equator (Parallel)."""
        return self.aspect == "Parallel"

    @property
    def is_contra_parallel(self) -> bool:
        """True when the bodies are on opposite sides of the equator (Contra-Parallel)."""
        return self.aspect == "Contra-Parallel"

    @property
    def orb_surplus(self) -> float:
        """Remaining headroom in the orb window: ``allowed_orb - orb``.  Always >= 0."""
        return self.allowed_orb - self.orb

    def __repr__(self) -> str:
        return f"{self.body1} ∥ {self.body2}  (orb {self.orb:+.2f}°) [{self.aspect}]"


@dataclass(slots=True)
class OutOfBoundsBody:
    """
    RITE: The Out-of-Bounds Vessel — a body whose declination exceeds the solar maximum.

    THEOREM: Holds the body name, its signed declination, the true obliquity
    threshold, and the excess beyond that threshold.

    RITE OF PURPOSE:
        Serves the Aspect Engine as the canonical result vessel for out-of-bounds
        detections.  A body is out-of-bounds when ``|declination| > obliquity``
        of the ecliptic — i.e., it has moved beyond the Sun's maximum possible
        declination.  The vessel preserves full context so the caller can
        reconstruct the admission test from the vessel alone:
        ``excess == abs(declination) - obliquity > 0``.

    LAW OF OPERATION:
        Responsibilities:
            - Store the body name, signed declination, obliquity threshold, and
              positive excess beyond that threshold.
            - Expose read-only convenience properties that are pure
              single-expression derivations of already-stored fields.
        Non-responsibilities:
            - Does not detect OOB bodies (delegated to ``find_out_of_bounds``).
            - Does not compute declinations from ecliptic coordinates.
            - Does not compute obliquity (caller supplies via
              ``moira.obliquity.true_obliquity``).
        Dependencies:
            - Populated exclusively by ``find_out_of_bounds()``.
        Structural invariants:
            - ``excess`` is always strictly positive.
            - ``excess == abs(declination) - obliquity``.
            - ``declination`` is in [-90, +90].
            - ``is_north`` and ``is_south`` are mutually exclusive; both False
              only when ``declination == 0.0`` (degenerate, in practice impossible).
        Succession stance: terminal — not designed for subclassing.

    Canon: Kt Boehrer, "Declination: The Other Dimension" (1994);
           modern practice (post-1990).

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.aspects.OutOfBoundsBody",
        "risk": "low",
        "api": {
            "public_methods": ["__repr__"],
            "public_attributes": ["body", "declination", "obliquity", "excess"],
            "public_properties": ["is_north", "is_south"]
        },
        "state": {
            "mutable": false,
            "fields": ["body", "declination", "obliquity", "excess"]
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
            "policy": "caller ensures excess > 0 before construction"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]
    """
    body:        str
    declination: float  # signed declination in degrees (±90)
    obliquity:   float  # true obliquity used as threshold (degrees)
    excess:      float  # abs(declination) - obliquity (always > 0)

    # ------------------------------------------------------------------
    # Inspectability — read-only, derived-only convenience properties
    # ------------------------------------------------------------------

    @property
    def is_north(self) -> bool:
        """True when the body has positive (north) declination."""
        return self.declination > 0.0

    @property
    def is_south(self) -> bool:
        """True when the body has negative (south) declination."""
        return self.declination < 0.0

    def __repr__(self) -> str:
        direction = "N" if self.is_north else "S"
        return (
            f"OutOfBoundsBody({self.body!r}, "
            f"dec={abs(self.declination):.4f}°{direction}, "
            f"excess={self.excess:.4f}°)"
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_aspects(
    tier: int | None,
    include_minor: bool,
) -> list[AspectDefinition]:
    """Return the aspect list for the given tier / include_minor flag."""
    if tier is not None:
        return ASPECT_TIERS.get(tier, Aspect.MAJOR)
    return Aspect.MAJOR + Aspect.COMMON_MINOR if include_minor else Aspect.MAJOR


_STATIONARY_THRESHOLD = 0.005  # degrees/day — below this a planet is considered stationary


def _applying(
    b1: str, lon1: float,
    b2: str, lon2: float,
    speeds: dict[str, float],
) -> bool | None:
    """
    True = applying, False = separating, None = unknown or stationary.

    Returns None when either body's daily speed is below the stationary
    threshold (< 0.005°/day), because the applying/separating distinction
    is not meaningful for a body that is effectively motionless.
    """
    if b1 not in speeds or b2 not in speeds:
        return None
    if abs(speeds.get(b1, 1.0)) < _STATIONARY_THRESHOLD or abs(speeds.get(b2, 1.0)) < _STATIONARY_THRESHOLD:
        return None
    relative_speed = speeds[b1] - speeds[b2]
    diff = (lon2 - lon1 + 180.0) % 360.0 - 180.0
    return relative_speed > 0 if diff > 0 else relative_speed < 0


def _is_stationary(b1: str, b2: str, speeds: dict[str, float]) -> bool:
    """Return True when either body's speed is below 0.01°/day."""
    _STAT_BROAD = 0.01
    return (abs(speeds.get(b1, 1.0)) < _STAT_BROAD
            or abs(speeds.get(b2, 1.0)) < _STAT_BROAD)


def _aspect_direction(lon1: float, lon2: float, angle: float) -> AspectDirection | None:
    """
    Determine the sinister/dexter direction of an aspect from body1's perspective.

    A sinister aspect is cast forward in zodiacal order (body2 is ahead of body1).
    A dexter aspect is cast backward (body2 is behind body1).
    Conjunctions and oppositions have no directional polarity; return None.
    """
    if angle == 0.0 or angle == 180.0:
        return None
    forward = (lon2 - lon1) % 360.0
    if forward <= 180.0:
        return AspectDirection.SINISTER
    return AspectDirection.DEXTER


def overcoming(lon1: float, lon2: float) -> bool:
    """
    Return True if the body at lon1 overcomes the body at lon2.

    Overcoming (katarchein) occurs when a planet is in the 10th-sign position
    relative to another — i.e., it casts a dexter square onto the other planet.
    The body in the superior (10th-sign) position dominates.

    Canon: Vettius Valens; Brennan, Hellenistic Astrology, Ch. 11.
    """
    sign1 = int(lon1 % 360.0 // 30)
    sign2 = int(lon2 % 360.0 // 30)
    diff = (sign1 - sign2) % 12
    return diff == 3  # body1 is 3 signs ahead = 10th-sign from body2


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def find_aspects(
    positions: dict[str, float],
    orbs: dict[float, float] | None = None,
    include_minor: bool = True,
    speeds: dict[str, float] | None = None,
    tier: int | None = None,
    orb_factor: float = 1.0,
    policy: AspectPolicy | None = None,
) -> list[AspectData]:
    """
    Find all aspects between a set of planetary longitudes.

    Core aspect detection
    ---------------------
    For every unique pair of bodies, computes the angular separation and
    tests each aspect definition in the resolved aspect list.  An aspect
    is admitted when ``abs(separation - angle) <= allowed_orb``.

    Relational truth preserved
    --------------------------
    Each result carries ``separation`` and ``allowed_orb`` so the admission
    test is verifiable from the vessel alone.

    Classification
    --------------
    Each result carries an ``AspectClassification`` with ``domain``
    (always ``ZODIACAL``), ``tier``, and ``family``.

    Policy surface
    --------------
    Pass an ``AspectPolicy`` instance via ``policy`` to supply all doctrine
    inputs in one argument.  When ``policy`` is provided it takes precedence
    over the individual ``tier``, ``include_minor``, ``orbs``, and
    ``orb_factor`` parameters.

    Doctrine inputs (current policy knobs)
    ---------------------------------------
    orbs         : custom orb table {angle: max_orb}.  When provided,
                   overrides both tier defaults and orb_factor.
    include_minor: include common minor aspects (ignored when tier is set).
    tier         : 0=Major, 1=Major+Common Minor, 2=All minor.
                   Overrides include_minor when set.
    orb_factor   : multiplier applied to all default orbs (e.g. 0.5 = tight).
                   Ignored when custom orbs dict is provided.

    Parameters
    ----------
    positions    : dict mapping body name → ecliptic longitude (degrees)
    orbs         : custom orb table {angle: max_orb}
    include_minor: include common minor aspects (ignored when tier is set)
    speeds       : dict mapping body name → daily speed (degrees/day).
                   Required for accurate applying/separating detection.
    tier         : 0/1/2 aspect tier; overrides include_minor when set
    orb_factor   : multiplier for default orbs; ignored when orbs is provided
    policy       : when supplied, overrides tier/include_minor/orbs/orb_factor

    Returns
    -------
    List of AspectData sorted by orb (tightest first).
    """
    if policy is not None:
        tier          = policy.tier
        include_minor = policy.include_minor
        orbs          = policy.orbs
        orb_factor    = policy.orb_factor
    aspect_list = _resolve_aspects(tier, include_minor)
    bodies = list(positions.keys())
    results: list[AspectData] = []

    for i in range(len(bodies)):
        for j in range(i + 1, len(bodies)):
            b1, b2 = bodies[i], bodies[j]
            lon1, lon2 = positions[b1], positions[b2]
            sep = angular_distance(lon1, lon2)

            for adef in aspect_list:
                if orbs is not None:
                    allowed = orbs.get(adef.angle, adef.default_orb)
                else:
                    allowed = adef.default_orb * orb_factor
                orb = abs(sep - adef.angle)
                if orb <= allowed:
                    app = _applying(b1, lon1, b2, lon2, speeds) if speeds else None
                    sta = _is_stationary(b1, b2, speeds) if speeds else False
                    results.append(AspectData(
                        body1=b1, body2=b2,
                        aspect=adef.name, symbol=adef.symbol,
                        angle=adef.angle,
                        separation=sep,
                        orb=orb,
                        allowed_orb=allowed,
                        applying=app,
                        stationary=sta,
                        classification=_ASPECT_CLASSIFICATION[adef.name],
                        direction=_aspect_direction(lon1, lon2, adef.angle),
                    ))

    results.sort(key=lambda a: a.orb)
    return results


def aspects_between(
    body_a: str,
    lon_a: float,
    body_b: str,
    lon_b: float,
    tier: int = 2,
    orbs: dict[float, float] | None = None,
    orb_factor: float = 1.0,
    speed_a: float | None = None,
    speed_b: float | None = None,
    policy: AspectPolicy | None = None,
) -> list[AspectData]:
    """
    Find all aspects between two specific bodies.

    Core aspect detection
    ---------------------
    Computes the angular separation between the two bodies and tests each
    aspect definition in the resolved tier.  An aspect is admitted when
    ``abs(separation - angle) <= allowed_orb``.

    Relational truth preserved
    --------------------------
    Each result carries ``separation`` and ``allowed_orb`` so the admission
    test is verifiable from the vessel alone.

    Classification
    --------------
    Each result carries an ``AspectClassification`` with ``domain``
    (always ``ZODIACAL``), ``tier``, and ``family``.

    Policy surface
    --------------
    Pass an ``AspectPolicy`` instance via ``policy`` to supply all doctrine
    inputs in one argument.  When ``policy`` is provided it takes precedence
    over the individual ``tier``, ``orbs``, and ``orb_factor`` parameters.
    Note: ``policy.tier=None`` resolves via ``policy.include_minor``; it does
    not fall back to this function's default ``tier=2``.

    Doctrine inputs (current policy knobs)
    ---------------------------------------
    tier       : aspect set (default 2 = all aspects)
    orbs       : custom orb table {angle: max_orb}
    orb_factor : multiplier for default orbs; ignored when orbs is provided

    Parameters
    ----------
    body_a / lon_a    : first body name and longitude
    body_b / lon_b    : second body name and longitude
    tier              : aspect set (default 2 = all aspects)
    orbs              : custom orb table
    orb_factor        : multiplier for default orbs
    speed_a / speed_b : daily motion (for applying/separating)
    policy            : when supplied, overrides tier/orbs/orb_factor

    Returns
    -------
    List of AspectData sorted by orb.
    """
    if policy is not None:
        orbs       = policy.orbs
        orb_factor = policy.orb_factor
        if policy.tier is not None:
            aspect_list = ASPECT_TIERS.get(policy.tier, Aspect.ALL)
        else:
            aspect_list = _resolve_aspects(None, policy.include_minor)
    else:
        aspect_list = ASPECT_TIERS.get(tier, Aspect.ALL)
    sep = angular_distance(lon_a, lon_b)
    results: list[AspectData] = []

    speeds = {}
    if speed_a is not None:
        speeds[body_a] = speed_a
    if speed_b is not None:
        speeds[body_b] = speed_b

    for adef in aspect_list:
        if orbs is not None:
            allowed = orbs.get(adef.angle, adef.default_orb)
        else:
            allowed = adef.default_orb * orb_factor
        orb = abs(sep - adef.angle)
        if orb <= allowed:
            app = _applying(body_a, lon_a, body_b, lon_b, speeds) if speeds else None
            sta = _is_stationary(body_a, body_b, speeds) if speeds else False
            results.append(AspectData(
                body1=body_a, body2=body_b,
                aspect=adef.name, symbol=adef.symbol,
                angle=adef.angle,
                separation=sep,
                orb=orb,
                allowed_orb=allowed,
                applying=app,
                stationary=sta,
                classification=_ASPECT_CLASSIFICATION[adef.name],
                direction=_aspect_direction(lon_a, lon_b, adef.angle),
            ))

    results.sort(key=lambda a: a.orb)
    return results


def aspects_to_point(
    point_longitude: float,
    positions: dict[str, float],
    point_name: str = "Point",
    orbs: dict[float, float] | None = None,
    include_minor: bool = True,
    tier: int | None = None,
    orb_factor: float = 1.0,
    policy: AspectPolicy | None = None,
) -> list[AspectData]:
    """
    Find all aspects from a set of planets to a single point longitude.

    Useful for transits, progressions, and fixed star contacts.

    Core aspect detection
    ---------------------
    For each body in ``positions``, computes the angular separation to
    ``point_longitude`` and tests each aspect definition.  An aspect is
    admitted when ``abs(separation - angle) <= allowed_orb``.
    No motion data is available for a static point, so ``applying`` is
    always ``None`` for results from this function.

    Relational truth preserved
    --------------------------
    Each result carries ``separation`` and ``allowed_orb`` so the admission
    test is verifiable from the vessel alone.

    Classification
    --------------
    Each result carries an ``AspectClassification`` with ``domain``
    (always ``ZODIACAL``), ``tier``, and ``family``.

    Policy surface
    --------------
    Pass an ``AspectPolicy`` instance via ``policy`` to supply all doctrine
    inputs in one argument.  When ``policy`` is provided it takes precedence
    over the individual ``tier``, ``include_minor``, ``orbs``, and
    ``orb_factor`` parameters.

    Doctrine inputs (current policy knobs)
    ---------------------------------------
    orbs         : custom orb table {angle: max_orb}
    include_minor: include common minor aspects (ignored when tier is set)
    tier         : 0/1/2 aspect tier; overrides include_minor when set
    orb_factor   : multiplier for default orbs; ignored when orbs is provided

    Parameters
    ----------
    point_longitude : target ecliptic longitude (degrees)
    positions       : dict of body name → longitude
    point_name      : label for the target point in AspectData.body2
    orbs            : custom orb table
    include_minor   : include common minor aspects (ignored when tier is set)
    tier            : 0/1/2 aspect tier
    orb_factor      : multiplier for default orbs
    policy          : when supplied, overrides tier/include_minor/orbs/orb_factor

    Returns
    -------
    List of AspectData sorted by orb.
    """
    if policy is not None:
        tier          = policy.tier
        include_minor = policy.include_minor
        orbs          = policy.orbs
        orb_factor    = policy.orb_factor
    aspect_list = _resolve_aspects(tier, include_minor)
    results: list[AspectData] = []

    for body, lon in positions.items():
        sep = angular_distance(lon, point_longitude)
        for adef in aspect_list:
            if orbs is not None:
                allowed = orbs.get(adef.angle, adef.default_orb)
            else:
                allowed = adef.default_orb * orb_factor
            orb = abs(sep - adef.angle)
            if orb <= allowed:
                results.append(AspectData(
                    body1=body, body2=point_name,
                    aspect=adef.name, symbol=adef.symbol,
                    angle=adef.angle,
                    separation=sep,
                    orb=orb,
                    allowed_orb=allowed,
                    applying=None,
                    classification=_ASPECT_CLASSIFICATION[adef.name],
                    direction=_aspect_direction(lon, point_longitude, adef.angle),
                ))

    results.sort(key=lambda a: a.orb)
    return results


# ---------------------------------------------------------------------------
# Declination aspects: parallels and contra-parallels
# ---------------------------------------------------------------------------

def find_declination_aspects(
    declinations: dict[str, float],
    orb: float = 1.0,
    policy: AspectPolicy | None = None,
) -> list[DeclinationAspect]:
    """
    Find parallel and contra-parallel aspects from a dict of declinations.

    Core aspect detection
    ---------------------
    Parallel:        ``|dec_A − dec_B| <= orb``  (bodies on the same side of
                     the celestial equator, within *orb* degrees of each other)
    Contra-Parallel: ``|dec_A + dec_B| <= orb``  (bodies on opposite sides,
                     their absolute declinations within *orb* degrees of each
                     other)

    Relational truth preserved
    --------------------------
    Each result stores ``allowed_orb`` (the ``orb`` argument as resolved at
    call time) so the admission test ``orb <= allowed_orb`` is verifiable
    from the vessel alone.

    Classification
    --------------
    Each result carries an ``AspectClassification`` with:
    - ``domain  = AspectDomain.DECLINATION``
    - ``tier    = AspectTier.MAJOR``
    - ``family  = AspectFamily.DECLINATION``

    Both Parallel and Contra-Parallel share this classification since they
    differ only in sign direction, not in harmonic family.

    Policy surface
    --------------
    Pass an ``AspectPolicy`` instance via ``policy`` to supply doctrine inputs
    in one argument.  When ``policy`` is provided, ``policy.declination_orb``
    takes precedence over the individual ``orb`` parameter.

    Doctrine inputs (current policy knobs)
    ---------------------------------------
    orb : single global ceiling for both aspect types (default 1.0°)

    Parameters
    ----------
    declinations : dict mapping body name → signed declination in degrees (±90)
    orb          : maximum orb in degrees (default 1.0°)
    policy       : when supplied, policy.declination_orb overrides orb

    Returns
    -------
    List of DeclinationAspect sorted by orb (tightest first).
    """
    if policy is not None:
        orb = policy.declination_orb
    bodies = list(declinations.keys())
    results: list[DeclinationAspect] = []

    for i in range(len(bodies)):
        for j in range(i + 1, len(bodies)):
            b1, b2 = bodies[i], bodies[j]
            d1, d2 = declinations[b1], declinations[b2]

            parallel_diff = abs(d1 - d2)
            if parallel_diff <= orb:
                results.append(DeclinationAspect(
                    body1=b1, body2=b2,
                    aspect="Parallel",
                    dec1=d1, dec2=d2,
                    orb=parallel_diff,
                    allowed_orb=orb,
                    classification=_PARALLEL_CLASSIFICATION,
                ))

            contra_diff = abs(d1 + d2)
            if contra_diff <= orb:
                results.append(DeclinationAspect(
                    body1=b1, body2=b2,
                    aspect="Contra-Parallel",
                    dec1=d1, dec2=d2,
                    orb=contra_diff,
                    allowed_orb=orb,
                    classification=_CONTRA_PARALLEL_CLASSIFICATION,
                ))

    results.sort(key=lambda a: a.orb)
    return results


def find_out_of_bounds(
    declinations: dict[str, float],
    obliquity: float,
) -> list[OutOfBoundsBody]:
    """
    Find bodies whose declination exceeds the obliquity of the ecliptic.

    A body is out-of-bounds (OOB) when ``|declination| > obliquity``.
    The Sun's maximum possible declination equals the true obliquity (~23°26').
    Any body beyond this threshold has moved outside the Sun's reach — a
    condition associated in modern practice with unconventional or
    boundary-breaking expression.

    Core detection
    --------------
    OOB admission test: ``abs(declination) > obliquity``
    Excess:             ``abs(declination) - obliquity  (always > 0 for OOB bodies)``

    Relational truth preserved
    --------------------------
    Each result stores ``obliquity`` and ``excess`` so the admission test is
    verifiable from the vessel alone without re-running the computation.

    Parameters
    ----------
    declinations : dict mapping body name → signed declination in degrees (±90)
    obliquity    : true obliquity of the ecliptic in degrees.  Use
                   ``moira.obliquity.true_obliquity(jd_tt)`` to obtain the
                   epoch-correct value for the chart's Julian Date.

    Returns
    -------
    List of OutOfBoundsBody sorted by excess descending (most OOB first).
    """
    results: list[OutOfBoundsBody] = []
    for body, dec in declinations.items():
        excess = abs(dec) - obliquity
        if excess > 0.0:
            results.append(OutOfBoundsBody(
                body=body,
                declination=dec,
                obliquity=obliquity,
                excess=excess,
            ))
    results.sort(key=lambda o: o.excess, reverse=True)
    return results


# ---------------------------------------------------------------------------
# Whole-sign aspects (Phase 4 — Hellenistic completion)
# ---------------------------------------------------------------------------

# Sign-count → (aspect_name, symbol, angle) for the five Ptolemaic aspects
_WHOLE_SIGN_MAP: dict[int, tuple[str, str, float]] = {
    0:  ("Conjunction", "☌",   0.0),
    2:  ("Sextile",    "⚹",  60.0),
    3:  ("Square",     "□",  90.0),
    4:  ("Trine",      "△", 120.0),
    6:  ("Opposition", "☍", 180.0),
    # Mirror side (e.g. 10 signs = sextile, 9 = square, 8 = trine)
    10: ("Sextile",    "⚹",  60.0),
    9:  ("Square",     "□",  90.0),
    8:  ("Trine",      "△", 120.0),
}

_WHOLE_SIGN_CLASSIFICATION: dict[str, AspectClassification] = {
    name: AspectClassification(
        domain=AspectDomain.WHOLE_SIGN,
        tier=AspectTier.MAJOR,
        family=_FAMILY_BY_NAME[name],
    )
    for name in ("Conjunction", "Sextile", "Square", "Trine", "Opposition")
}


def find_whole_sign_aspects(
    positions: dict[str, float],
) -> list[AspectData]:
    """
    Detect whole-sign (sign-based) aspects among a set of bodies.

    Whole-sign aspects use sign-count separation rather than degree-based
    orbs.  Two bodies form a Ptolemaic aspect when the number of signs
    between their sign positions matches a classical pattern:

        0 signs  → Conjunction
        2 or 10  → Sextile
        3 or  9  → Square
        4 or  8  → Trine
        6        → Opposition

    Aversion (1, 5, 7, 11 signs apart) yields no Ptolemaic aspect.

    Whole-sign aspects carry no orb (``orb = 0.0``) and exactness is
    always ``1.0``.  ``applying`` is always ``None`` since the aspect is
    categorical, not orbital.

    The ``direction`` field (sinister/dexter) is computed from the actual
    longitudes, following the same logic as degree-based aspects.

    Parameters
    ----------
    positions : dict mapping body name → ecliptic longitude (degrees)

    Returns
    -------
    List of AspectData with ``classification.domain == WHOLE_SIGN``.
    """
    bodies = list(positions.keys())
    results: list[AspectData] = []

    for i in range(len(bodies)):
        for j in range(i + 1, len(bodies)):
            b1, b2 = bodies[i], bodies[j]
            lon1, lon2 = positions[b1], positions[b2]

            sign1 = int(lon1 % 360.0 // 30)
            sign2 = int(lon2 % 360.0 // 30)
            sign_diff = (sign1 - sign2) % 12

            mapping = _WHOLE_SIGN_MAP.get(sign_diff)
            if mapping is None:
                continue

            aspect_name, symbol, angle = mapping
            sep = angular_distance(lon1, lon2)

            results.append(AspectData(
                body1=b1,
                body2=b2,
                aspect=aspect_name,
                symbol=symbol,
                angle=angle,
                separation=sep,
                orb=0.0,
                allowed_orb=0.0,
                applying=None,
                classification=_WHOLE_SIGN_CLASSIFICATION[aspect_name],
                direction=_aspect_direction(lon1, lon2, angle),
            ))

    return results
