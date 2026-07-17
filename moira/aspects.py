"""
Moira — Aspect Engine
======================

Archetype: Engine

Purpose
-------
Governs ecliptic-longitude and whole-sign aspects.  First-class parallel and
contra-parallel doctrine is governed by ``moira.declination_aspects`` and
re-exported here to preserve the historical public import surface.

Architecture layers
-------------------
This module has thirteen distinct concerns, kept intentionally separate:

1. **Core aspect detection** — ``find_aspects``, ``aspects_between``,
   ``aspects_to_point``, and ``find_out_of_bounds``.
   Pure geometric computations: given positions, return every angular
   relationship that falls within a qualifying orb, and detect bodies
   whose declination exceeds the solar maximum.  Detection semantics
   are stable and must not be silently changed.

2. **Relational truth preservation** — the ``AspectData`` result vessel.
   Each admitted aspect records not only *what* was found but *why* it
   qualified: actual angular separation, target angle, orb deviation,
   and applied orb ceiling.  A caller can fully reconstruct the admission
   test from the vessel alone.  Degree-based aspects preserve
   ``abs(separation - angle) == orb`` and ``orb <= allowed_orb``;
   categorical whole-sign aspects explicitly carry a zero-width orb context.

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
   A frozen dataclass that bundles longitude-aspect doctrine inputs and keeps
   ``declination_orb`` as a compatibility adapter. Pass one ``policy`` argument instead of
   four scattered keyword arguments.  When ``policy`` is supplied it takes
   precedence; existing individual parameters remain for backward
   compatibility.

7. **Geometric strength** — ``AspectStrength``, ``aspect_strength``.
   A pure arithmetic derivation of how close to exact an admitted aspect
   is, expressed as four named components: raw ``orb``, ``allowed_orb``,
   ``surplus`` (headroom), and ``exactness`` (1.0 = exact, 0.0 = at
   boundary).  Categorical whole-sign aspects report exactness 1.0 without
   inventing an orb window.  No interpretation or new input is introduced.

8. **Temporal state** — ``MotionState``, ``aspect_motion_state``.
   Formalises the motion-aware truth already implicit in the vessel's
   ``applying`` and ``stationary`` fields into a single, explicit,
   named enum value.  Covers every possible field combination without
   ambiguity: APPLYING, EXACT, SEPARATING, STATIONARY, INDETERMINATE (speeds
   absent), NONE (``DeclinationAspect`` — no motion data at all).

9. **First-class signed motion** — ``AspectMotionWitness``,
   ``AspectMotionState``, and ``aspect_motion_witness``.
   Preserves one caller-selected instantaneous aspect branch, its signed
   error and relative rate, explicit exact/station/ambiguity policy, canonical
   orb admission, and caller-declared frame/timescale provenance.  It does not
   search for a future perfection or station.

10. **Canonical configuration** — ``CANONICAL_ASPECTS``.
   The complete, explicitly declared set of all 24 aspect types recognised
   and detectable by this engine: 22 zodiacal aspects (5 major, 6
   common-minor, 11 extended-minor) plus 2 declination aspects (Parallel,
   Contra-Parallel).  ``CANONICAL_ASPECTS`` makes the full set inspectable
   at import time without requiring knowledge of ``moira.constants``.

11. **Multi-body pattern layer** — ``AspectPatternKind``, ``AspectPattern``,
    ``find_patterns``.
    Detects structural configurations formed by three or more bodies whose
    pairwise aspects (already admitted by the detection layer) satisfy a
    named topological template: Stellium, T-Square, Grand Trine, Grand Cross,
    and Yod.  Pattern detection is a pure function over a ``list[AspectData]``
    — it does not re-run position arithmetic, does not introduce new doctrine
    inputs, and does not mutate the supplied pairwise vessels.

12. **Relational graph / network layer** — ``AspectGraphNode``, ``AspectGraph``,
    ``build_aspect_graph``.
    Expresses the chart as a deterministic relational network built from
    already-admitted pairwise aspects.  Bodies become nodes; each admitted
    aspect becomes an edge.  The graph layer exposes node degree, per-node
    aspect-name counts, connected components, isolated bodies, and hub
    detection.  It is a pure function over ``list[AspectData]`` — it does not
    re-run position arithmetic, does not alter any vessel, and does not
    introduce new doctrine inputs.  An optional ``bodies`` parameter allows
    degree-0 (isolated) nodes to be declared explicitly.

13. **Harmonic / family intelligence layer** — ``AspectFamilyProfile``,
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
Owns: longitude and whole-sign aspect detection, orb arithmetic,
      applying/separating determination, stationary detection,
      ``AspectData``, and the longitude signed-motion witness.
Delegates: aspect definition tables and tier lists to ``moira.constants``,
           angular distance arithmetic to ``moira.coordinates``, and
           declination relationships to ``moira.declination_aspects``.

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required. No database access. Pure computation over
position and speed dicts.

Public surface
--------------
``AspectDomain``             — enum: ZODIACAL, DECLINATION, or WHOLE_SIGN.
``AspectDirection``          — enum: SINISTER or DEXTER (Hellenistic).
``AspectTier``               — enum: MAJOR, COMMON_MINOR, EXTENDED_MINOR.
``AspectFamily``             — enum: harmonic family (conjunction, trine, …).
``AspectClassification``     — frozen dataclass bundling domain + tier + family.
``AspectPolicy``             — frozen dataclass bundling all doctrine inputs.
``DEFAULT_POLICY``           — default policy matching current parameter defaults.
``TRADITIONAL_MOIETY_ORBS`` — Lilly 1647 orb table for moiety mode.
``AspectStrength``           — frozen dataclass: orb, allowed_orb, surplus, exactness.
``aspect_strength``          — derive AspectStrength from any admitted vessel.
``MotionState``              — enum: APPLYING, EXACT, SEPARATING, STATIONARY, INDETERMINATE, NONE.
``aspect_motion_state``      — derive MotionState from any admitted vessel.
``AspectMotionBranch``       — selected positive, negative, conjunction, or ambiguous branch.
``AspectMotionOrbPolicy``    — explicit orb policy used by the signed witness.
``AspectMotionState``        — enum: APPLYING, EXACT, SEPARATING, STATIONARY, INDETERMINATE.
``AspectMotionStationaryReason`` — typed body-station or relative-standstill reason.
``AspectMotionWitness``      — immutable instantaneous signed-error/rate witness.
``aspect_motion_witness``    — build the witness from caller-supplied longitudes and speeds.
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
``AspectData``               — vessel for a longitude or whole-sign aspect.
``DeclinationAspect``        — vessel for a parallel or contra-parallel aspect.
``DeclinationAspectAnalysis`` — immutable caller-supplied declination analysis.
``OutOfBoundsBody``          — vessel for a body whose declination exceeds solar max.
``find_aspects``             — find all aspects in a position dict.
``aspects_between``          — find aspects between two specific bodies.
``aspects_to_point``         — find aspects from a body set to a single point.
``find_declination_aspects`` — find parallels and contra-parallels.
``declination_aspects_from_declinations`` — deterministic first-class declination analysis.
``find_out_of_bounds``       — detect bodies beyond maximum solar declination.
``find_whole_sign_aspects``  — find non-orb aspects by sign boundaries.
``overcoming``               — determine Hellenistic overcoming (dominance) between bodies.

Convenience properties (read-only, derived only)
-------------------------------------------------
``AspectData.is_major``          — True when tier is MAJOR.
``AspectData.is_minor``          — True when tier is not MAJOR.
``AspectData.is_zodiacal``       — True when domain is ZODIACAL.
``AspectData.is_applying``       — True when applying is True (not None or False).
``AspectData.is_separating``     — True when applying is False (not None or True).
``AspectData.orb_surplus``       — allowed_orb minus orb (remaining headroom).
``AspectData.is_partile``        — True when a major aspect has both bodies at the same degree-of-sign; False for non-major.
``AspectData.is_platic``         — True when a major aspect is admitted but not partile; False for non-major.
``DeclinationAspect.is_parallel``         — True when aspect is "Parallel".
``DeclinationAspect.is_contra_parallel``  — True when aspect is "Contra-Parallel".
``DeclinationAspect.orb_surplus``         — allowed_orb minus orb.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from itertools import combinations, permutations
import math
from types import MappingProxyType
from typing import Collection, Callable, Mapping

from ._aspect_types import (
    AspectClassification,
    AspectDomain,
    AspectFamily,
    AspectTier,
)
from .constants import Aspect, AspectDefinition, ASPECT_TIERS, DEFAULT_ORBS, TRADITIONAL_MOIETY_ORBS, Body
from .coordinates import angular_distance
from .declination_aspects import (
    DeclinationAspect,
    DeclinationAspectAnalysis,
    DeclinationAspectKind,
    DeclinationAspectMotionWitness,
    DeclinationAspectPolicy,
    DeclinationEquatorPolicy,
    DeclinationHemispherePolicy,
    DeclinationMotionState,
    _CONTRA_PARALLEL_CLASSIFICATION,
    _PARALLEL_CLASSIFICATION,
    declination_aspect_motion_witness,
    declination_aspects_from_declinations as _declination_analysis,
    find_declination_aspects as _find_declination_aspects,
)

__all__ = [
    # Constants
    "CANONICAL_ASPECTS",
    "DEFAULT_POLICY",
    "TRADITIONAL_MOIETY_ORBS",
    # Enums
    "AspectDirection",
    "AspectDomain",
    "AspectFamily",
    "AspectMotionBranch",
    "AspectMotionOrbPolicy",
    "AspectPatternKind",
    "AspectMotionStationaryReason",
    "AspectTier",
    "AspectMotionState",
    "MotionState",
    "DeclinationAspectKind",
    "DeclinationEquatorPolicy",
    "DeclinationHemispherePolicy",
    "DeclinationMotionState",
    # Dataclasses
    "AspectClassification",
    "AspectData",
    "DeclinationAspectAnalysis",
    "AspectFamilyProfile",
    "AspectGraph",
    "AspectGraphNode",
    "AspectHarmonicProfile",
    "AspectMotionWitness",
    "LongitudeAspectAnalysis",
    "AspectPattern",
    "AspectPolicy",
    "AspectStrength",
    "DeclinationAspect",
    "DeclinationAspectMotionWitness",
    "DeclinationAspectPolicy",
    # Entry points
    "aspect_harmonic_profile",
    "aspect_motion_witness",
    "aspect_motion_state",
    "aspect_strength",
    "aspects_between",
    "declination_aspects_from_declinations",
    "declination_aspect_motion_witness",
    "aspects_to_point",
    "build_aspect_graph",
    "find_aspects",
    "aspects_from_longitudes",
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

class AspectDirection(str, Enum):
    """Vessel: Registry of zodiacal aspect directions."""
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

def _finite_number(name: str, value: object) -> float:
    """Return *value* as a finite float or raise a field-specific error."""
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number")
    try:
        parsed = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{name} must be a finite number")
    return parsed


def _normalized_named_values(
    values: Mapping[str, float],
    *,
    quantity: str,
    minimum: float | None = None,
    maximum: float | None = None,
) -> dict[str, float]:
    """Validate a named numerical mapping while preserving caller order."""
    if not isinstance(values, Mapping):
        raise ValueError(f"{quantity}s must be a mapping of point names to degrees")
    normalized: dict[str, float] = {}
    for name, value in values.items():
        if not isinstance(name, str) or not name or name != name.strip():
            raise ValueError(f"{quantity} point names must be non-empty trimmed strings")
        parsed = _finite_number(f"{quantity} for {name!r}", value)
        if minimum is not None and parsed < minimum:
            raise ValueError(
                f"{quantity} for {name!r} must be >= {minimum}, got {parsed!r}"
            )
        if maximum is not None and parsed > maximum:
            raise ValueError(
                f"{quantity} for {name!r} must be <= {maximum}, got {parsed!r}"
            )
        normalized[name] = parsed
    return normalized


# ---------------------------------------------------------------------------
# Policy surface
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AspectPolicy:
    """Vessel: Policy definition for aspect detection doctrine."""
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
                      Ignored when ``orb_mode="moiety"``.
    orb_factor      : multiplier applied to all default orbs (e.g. 0.5 = tight
                      windows).  Ignored when ``orbs`` is provided or when
                      ``orb_mode="moiety"``.
    declination_orb : orb ceiling for Parallel and Contra-Parallel detection.
    orb_mode        : orb doctrine to apply.

                      ``"fixed"`` (default) — per-aspect-angle orb window,
                      sourced from ``orbs`` or scaled ``default_orb`` values.
                      This is the modern / default behaviour.

                      ``"moiety"`` — per-body-pair orb window computed as the
                      sum of the two bodies' moieties (half their traditional
                      full orbs).  ``orbs`` and ``orb_factor`` are ignored.
                      Uses ``moiety_orbs`` when supplied; falls back to
                      ``TRADITIONAL_MOIETY_ORBS`` (Lilly 1647) otherwise.
                      Bodies not in the table receive a default full orb of
                      5° (moiety 2.5°).  Detection is **restricted to the five
                      Ptolemaic major aspects** (Conjunction, Sextile, Square,
                      Trine, Opposition) regardless of ``tier`` or
                      ``include_minor``; moiety doctrine has no historical basis
                      for minor or harmonic aspects.

    moiety_orbs     : custom per-body full-orb table ``{body_name: full_orb}``.
                      Used only when ``orb_mode="moiety"``.  When ``None``,
                      ``TRADITIONAL_MOIETY_ORBS`` is used.  Moiety of each
                      body = ``full_orb / 2``; combined allowed orb for a pair
                      = ``moiety(A) + moiety(B)``.

    All fields are optional; the defaults reproduce the historical default
    behaviour of all four detection functions.

    Raises
    ------
    ValueError
        If ``tier`` is not 0, 1, 2, or ``None``.
        If ``include_minor`` is not a boolean.
        If any numeric policy input is non-finite.
        If ``orb_factor <= 0``.
        If ``declination_orb < 0``.
        If ``orb_mode`` is not ``"fixed"`` or ``"moiety"``.
        If any custom orb or moiety value is not positive.
    """
    tier:            int | None                = None
    include_minor:   bool                      = True
    orbs:            Mapping[float, float] | None = None
    orb_factor:      float                     = 1.0
    declination_orb: float                     = 1.0
    orb_mode:        str                       = "fixed"
    moiety_orbs:     Mapping[str, float] | None = None

    def __post_init__(self) -> None:
        if self.tier is not None and (
            isinstance(self.tier, bool)
            or not isinstance(self.tier, int)
            or self.tier not in ASPECT_TIERS
        ):
            raise ValueError(
                f"AspectPolicy: tier must be 0, 1, 2, or None, got {self.tier!r}."
            )
        if not isinstance(self.include_minor, bool):
            raise ValueError(
                "AspectPolicy: include_minor must be a boolean, "
                f"got {self.include_minor!r}."
            )

        orb_factor = _finite_number("AspectPolicy.orb_factor", self.orb_factor)
        if orb_factor <= 0:
            raise ValueError(
                f"AspectPolicy: orb_factor must be > 0, got {orb_factor!r}. "
                "A zero or negative multiplier produces meaningless orb windows."
            )
        object.__setattr__(self, "orb_factor", orb_factor)

        declination_orb = _finite_number(
            "AspectPolicy.declination_orb", self.declination_orb
        )
        if declination_orb < 0:
            raise ValueError(
                "AspectPolicy: declination_orb must be >= 0, "
                f"got {declination_orb!r}."
            )
        object.__setattr__(self, "declination_orb", declination_orb)

        if self.orb_mode not in ("fixed", "moiety"):
            raise ValueError(
                f"AspectPolicy: orb_mode must be 'fixed' or 'moiety', got {self.orb_mode!r}."
            )

        if self.orbs is not None:
            if not isinstance(self.orbs, Mapping):
                raise ValueError("AspectPolicy: orbs must be a mapping")
            normalized_orbs: dict[float, float] = {}
            for raw_angle, raw_orb in self.orbs.items():
                angle = _finite_number("AspectPolicy.orbs angle", raw_angle)
                allowed = _finite_number(
                    f"AspectPolicy.orbs[{angle!r}]", raw_orb
                )
                if not 0.0 <= angle <= 180.0:
                    raise ValueError(
                        "AspectPolicy: orb-table angles must be in [0, 180], "
                        f"got {angle!r}."
                    )
                if allowed <= 0.0:
                    raise ValueError(
                        "AspectPolicy: orbs values must be > 0; "
                        f"got {allowed!r} for angle {angle!r}."
                    )
                normalized_orbs[angle] = allowed
            object.__setattr__(
                self, "orbs", MappingProxyType(normalized_orbs)
            )

        if self.moiety_orbs is not None:
            if not isinstance(self.moiety_orbs, Mapping):
                raise ValueError("AspectPolicy: moiety_orbs must be a mapping")
            normalized_moieties: dict[str, float] = {}
            for body, raw_orb in self.moiety_orbs.items():
                if not isinstance(body, str) or not body or body != body.strip():
                    raise ValueError(
                        "AspectPolicy: moiety_orbs keys must be non-empty "
                        "trimmed body names"
                    )
                full_orb = _finite_number(
                    f"AspectPolicy.moiety_orbs[{body!r}]", raw_orb
                )
                if full_orb <= 0.0:
                    raise ValueError(
                        "AspectPolicy: moiety_orbs values must be > 0; "
                        f"got {full_orb!r} for {body!r}."
                    )
                normalized_moieties[body] = full_orb
            object.__setattr__(
                self, "moiety_orbs", MappingProxyType(normalized_moieties)
            )


DEFAULT_POLICY: AspectPolicy = AspectPolicy()


# ---------------------------------------------------------------------------
# Geometric strength layer
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AspectStrength:
    """Vessel: Geometric strength of an admitted aspect."""
    """
    Pure geometric strength of an admitted aspect, derived entirely from
    the admission context already stored on the result vessel.

    No interpretation, no dignity weighting, no configuration.  For an
    orb-admitted aspect every field is a direct arithmetic consequence of
    ``orb`` and ``allowed_orb``.  A whole-sign aspect is categorical and
    therefore carries ``orb=allowed_orb=surplus=0`` and ``exactness=1``.

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

    Orb-admitted invariants
    -----------------------
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

    Whole-sign aspects use the categorical identity
    ``orb = allowed_orb = surplus = 0`` and ``exactness = 1`` instead.

    Raises
    ------
    ValueError
        If ``orb`` or ``allowed_orb`` is non-finite, or ``orb < 0``.
        If ``allowed_orb <= 0`` (division by zero / meaningless window).
        If ``orb > allowed_orb`` (vessel violates the admission invariant).
    """
    orb         = aspect.orb
    allowed_orb = aspect.allowed_orb
    if (
        isinstance(aspect, AspectData)
        and aspect.classification is not None
        and aspect.classification.domain is AspectDomain.WHOLE_SIGN
    ):
        if orb != 0.0 or allowed_orb != 0.0:
            raise ValueError(
                "aspect_strength: whole-sign vessels must carry orb=0 and "
                "allowed_orb=0 because their strength is categorical"
            )
        return AspectStrength(
            orb=0.0,
            allowed_orb=0.0,
            surplus=0.0,
            exactness=1.0,
        )
    if not math.isfinite(orb) or orb < 0.0:
        raise ValueError(
            f"aspect_strength: orb must be finite and >= 0, got {orb!r}."
        )
    if not math.isfinite(allowed_orb):
        raise ValueError(
            "aspect_strength: allowed_orb must be finite, "
            f"got {allowed_orb!r}."
        )
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
    """Vessel: Registry of temporal motion states for aspects."""
    """
    Explicit temporal-motion state of an admitted aspect, derived from the
    ``applying`` and ``stationary`` fields already preserved on the vessel.

    Covers the complete decision space with no ambiguity:

    APPLYING      — both bodies are in motion and the aspect is closing
                    (``applying is True``, ``stationary is False``).
    EXACT         — the aspect is exact within 1e-9 degrees.  Exactness takes
                    precedence over stationary and applying/separating state.
    SEPARATING    — both bodies are in motion and the aspect is widening
                    (``applying is False``, ``stationary is False``).
    STATIONARY    — at least one body's daily motion is below the stationary
                    threshold (``stationary is True``).  The applying/separating
                    distinction is not meaningful in this condition.
    INDETERMINATE — the vessel was produced without speed data, so the
                    direction of motion cannot be resolved
                    (``applying is None``, ``stationary is False``).
    NONE          — the vessel type carries no longitude-motion information
                    (``DeclinationAspect`` or categorical whole-sign data).
    """
    APPLYING      = "applying"
    EXACT         = "exact"
    SEPARATING    = "separating"
    STATIONARY    = "stationary"
    INDETERMINATE = "indeterminate"
    NONE          = "none"


class AspectMotionState(str, Enum):
    """Instantaneous phase of one selected longitude-aspect branch."""

    APPLYING = "applying"
    EXACT = "exact"
    SEPARATING = "separating"
    STATIONARY = "stationary"
    INDETERMINATE = "indeterminate"


class AspectMotionBranch(str, Enum):
    """Selected signed exact-aspect branch."""

    UNDIRECTED_CONJUNCTION = "undirected_conjunction"
    POSITIVE = "positive"
    NEGATIVE = "negative"
    AMBIGUOUS_AT_ZERO_SEPARATION = "ambiguous_at_zero_separation"


class AspectMotionOrbPolicy(str, Enum):
    """Orb policy used by the instantaneous motion witness."""

    CANONICAL_DEFAULT_SCALED = "canonical_default_scaled"


class AspectMotionStationaryReason(str, Enum):
    """Explicit reason that instantaneous aspect motion is stationary."""

    BODY1_BELOW_THRESHOLD = "body1_below_stationary_threshold"
    BODY2_BELOW_THRESHOLD = "body2_below_stationary_threshold"
    RELATIVE_RATE_WITHIN_TOLERANCE = "relative_rate_within_tolerance"


def aspect_motion_state(aspect: AspectData | DeclinationAspect) -> MotionState:
    """
    Derive the explicit temporal-motion state of an admitted aspect vessel.

    Reads only the ``orb``, ``applying``, and ``stationary`` fields already
    stored on the vessel.  No new information is required.  The mapping is
    deterministic and covers every possible field combination:

    Decision table
    --------------
    ==================  ===========  =========  ==================
    vessel type         orb          stationary   applying   → MotionState
    ==================  ===========  ===========  =========  ==================
    DeclinationAspect   any          —            —          NONE
    WHOLE_SIGN data     any          —            —          NONE
    ZODIACAL data       <= 1e-9      any          any        EXACT
    ZODIACAL data       > 1e-9       True         any        STATIONARY
    ZODIACAL data       > 1e-9       False        True       APPLYING
    ZODIACAL data       > 1e-9       False        False      SEPARATING
    ZODIACAL data       > 1e-9       False        None       INDETERMINATE
    ==================  ===========  ===========  =========  ==================

    Parameters
    ----------
    aspect : an ``AspectData`` or ``DeclinationAspect`` instance.

    Returns
    -------
    A ``MotionState`` enum member.
    """
    if isinstance(aspect, DeclinationAspect):
        return MotionState.NONE
    if (
        aspect.classification is not None
        and aspect.classification.domain is AspectDomain.WHOLE_SIGN
    ):
        return MotionState.NONE
    if aspect.orb <= 1e-9:
        return MotionState.EXACT
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
    """Vessel: Registry of multi-body aspect pattern kinds."""
    """
    Kind of multi-body aspect pattern.

    Implemented (detectable by ``find_patterns``)
    ----------------------------------------------
    STELLIUM         — three or more bodies within mutual Conjunction orbs.
    T_SQUARE         — three bodies: one Opposition and two Squares forming a
                       right-angle cross (the apex body squares both poles).
    GRAND_TRINE      — three bodies each separated by a Trine (120°), forming
                       an equilateral triangle in the chart.
    GRAND_CROSS      — four bodies: two Oppositions and four Squares forming a
                       square cross.
    YOD              — three bodies: two Quincunxes (150°) sharing an apex and
                       a Sextile (60°) connecting the base pair.
    KITE             — four bodies: a Grand Trine and a fourth body opposing the apex
                       and forming sextiles to the other two.
    MYSTIC_RECTANGLE — four bodies: two Oppositions, two Trines, and two Sextiles.
    CRADLE           — four bodies: one Opposition, three Sextiles, and two Trines.
    WEDGE            — three bodies: one Opposition, one Trine, and one Sextile.
    BUTTERFLY        — four bodies: two Wedges sharing the same Opposition axis.
    GRAND_SEXTILE    — six bodies forming a closed loop of six Sextiles.
    GOLDEN_YOD       — three bodies: two Biquintiles (144°) and a Quintile (72°).
    THORS_HAMMER     — three bodies: two Sesquiquadrates (135°) and a Square (90°).
    FINGER_OF_WORLD  — three bodies: two Semisquares (45°) and a Square (90°).
    GRAND_QUINTILE   — five bodies: five Quintiles forming a closed pentagon.
    GRAND_SEPTILE    — seven bodies: seven Septiles forming a closed heptagon.
    GRAND_NOVILE     — nine bodies: nine Noviles forming a closed nonagon.
    ENVELOPE         — five bodies: a Mystic Rectangle connected to a fifth body.
    YOD_OF_DESTINY   — four bodies: three Quincunxes sharing an apex and two Sextiles.
    """
    STELLIUM         = "stellium"
    T_SQUARE         = "t_square"
    GRAND_TRINE      = "grand_trine"
    GRAND_CROSS      = "grand_cross"
    YOD              = "yod"
    KITE             = "kite"
    MYSTIC_RECTANGLE = "mystic_rectangle"
    CRADLE           = "cradle"
    WEDGE            = "wedge"
    BUTTERFLY        = "butterfly"
    GRAND_SEXTILE    = "grand_sextile"
    GOLDEN_YOD       = "golden_yod"
    THORS_HAMMER     = "thors_hammer"
    FINGER_OF_WORLD  = "finger_of_world"
    GRAND_QUINTILE   = "grand_quintile"
    GRAND_SEPTILE    = "grand_septile"
    GRAND_NOVILE     = "grand_novile"
    ENVELOPE         = "envelope"
    YOD_OF_DESTINY   = "yod_of_destiny"


@dataclass(frozen=True, slots=True)
class AspectPattern:
    """Vessel: Result vessel for a detected multi-body aspect pattern."""
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


@dataclass(frozen=True, slots=True)
class _PatternTemplate:
    """Edge-constraint template describing one detectable aspect pattern shape."""

    kind: AspectPatternKind
    num_bodies: int
    edges: list[tuple[int, int, frozenset[str]]]
    filter_fn: Callable[[tuple[str, ...], list[AspectData]], bool] | None = None


_PATTERN_TEMPLATES: list[_PatternTemplate] = [
    # 1. T-Square
    _PatternTemplate(
        kind=AspectPatternKind.T_SQUARE,
        num_bodies=3,
        edges=[
            (1, 2, frozenset({"Opposition"})),
            (0, 1, frozenset({"Square"})),
            (0, 2, frozenset({"Square"})),
        ],
    ),
    # 2. Grand Trine
    _PatternTemplate(
        kind=AspectPatternKind.GRAND_TRINE,
        num_bodies=3,
        edges=[
            (0, 1, frozenset({"Trine"})),
            (1, 2, frozenset({"Trine"})),
            (0, 2, frozenset({"Trine"})),
        ],
    ),
    # 3. Grand Cross
    _PatternTemplate(
        kind=AspectPatternKind.GRAND_CROSS,
        num_bodies=4,
        edges=[
            (0, 2, frozenset({"Opposition"})),
            (1, 3, frozenset({"Opposition"})),
            (0, 1, frozenset({"Square"})),
            (1, 2, frozenset({"Square"})),
            (2, 3, frozenset({"Square"})),
            (3, 0, frozenset({"Square"})),
        ],
    ),
    # 4. Yod
    _PatternTemplate(
        kind=AspectPatternKind.YOD,
        num_bodies=3,
        edges=[
            (1, 2, frozenset({"Sextile"})),
            (0, 1, frozenset({"Quincunx"})),
            (0, 2, frozenset({"Quincunx"})),
        ],
    ),
    # 5. Kite
    _PatternTemplate(
        kind=AspectPatternKind.KITE,
        num_bodies=4,
        edges=[
            (0, 1, frozenset({"Trine"})),
            (0, 2, frozenset({"Trine"})),
            (1, 2, frozenset({"Trine"})),
            (0, 3, frozenset({"Opposition"})),
            (1, 3, frozenset({"Sextile"})),
            (2, 3, frozenset({"Sextile"})),
        ],
    ),
    # 6. Mystic Rectangle
    _PatternTemplate(
        kind=AspectPatternKind.MYSTIC_RECTANGLE,
        num_bodies=4,
        edges=[
            (0, 3, frozenset({"Opposition"})),
            (1, 2, frozenset({"Opposition"})),
            (0, 1, frozenset({"Trine"})),
            (2, 3, frozenset({"Trine"})),
            (0, 2, frozenset({"Sextile"})),
            (1, 3, frozenset({"Sextile"})),
        ],
    ),
    # 7. Cradle
    _PatternTemplate(
        kind=AspectPatternKind.CRADLE,
        num_bodies=4,
        edges=[
            (0, 3, frozenset({"Opposition"})),
            (0, 1, frozenset({"Sextile"})),
            (1, 2, frozenset({"Sextile"})),
            (2, 3, frozenset({"Sextile"})),
            (0, 2, frozenset({"Trine"})),
            (1, 3, frozenset({"Trine"})),
        ],
    ),
    # 8. Wedge
    _PatternTemplate(
        kind=AspectPatternKind.WEDGE,
        num_bodies=3,
        edges=[
            (1, 2, frozenset({"Opposition"})),
            (0, 1, frozenset({"Trine", "Sextile"})),
            (0, 2, frozenset({"Trine", "Sextile"})),
        ],
        filter_fn=lambda bodies, aspects: {a.aspect for a in aspects} == {"Opposition", "Trine", "Sextile"},
    ),
    # 9. Butterfly
    _PatternTemplate(
        kind=AspectPatternKind.BUTTERFLY,
        num_bodies=4,
        edges=[
            (0, 1, frozenset({"Opposition"})),
            (0, 2, frozenset({"Trine", "Sextile"})),
            (1, 2, frozenset({"Trine", "Sextile"})),
            (0, 3, frozenset({"Trine", "Sextile"})),
            (1, 3, frozenset({"Trine", "Sextile"})),
        ],
        filter_fn=lambda bodies, aspects: (
            len(aspects) == 5
            and sum(1 for a in aspects if a.aspect == "Opposition") == 1
            and sum(1 for a in aspects if a.aspect == "Trine") == 2
            and sum(1 for a in aspects if a.aspect == "Sextile") == 2
            and {a.aspect for a in aspects if frozenset((a.body1, a.body2)) == frozenset((bodies[0], bodies[2])) or frozenset((a.body1, a.body2)) == frozenset((bodies[1], bodies[2]))} == {"Trine", "Sextile"}
            and {a.aspect for a in aspects if frozenset((a.body1, a.body2)) == frozenset((bodies[0], bodies[3])) or frozenset((a.body1, a.body2)) == frozenset((bodies[1], bodies[3]))} == {"Trine", "Sextile"}
        ),
    ),
    # 10. Grand Sextile
    _PatternTemplate(
        kind=AspectPatternKind.GRAND_SEXTILE,
        num_bodies=6,
        edges=[
            (0, 3, frozenset({"Opposition"})),
            (1, 4, frozenset({"Opposition"})),
            (2, 5, frozenset({"Opposition"})),
            (0, 2, frozenset({"Trine"})),
            (2, 4, frozenset({"Trine"})),
            (4, 0, frozenset({"Trine"})),
            (1, 3, frozenset({"Trine"})),
            (3, 5, frozenset({"Trine"})),
            (5, 1, frozenset({"Trine"})),
            (0, 1, frozenset({"Sextile"})),
            (1, 2, frozenset({"Sextile"})),
            (2, 3, frozenset({"Sextile"})),
            (3, 4, frozenset({"Sextile"})),
            (4, 5, frozenset({"Sextile"})),
            (5, 0, frozenset({"Sextile"})),
        ],
    ),
    # 11. Golden Yod
    _PatternTemplate(
        kind=AspectPatternKind.GOLDEN_YOD,
        num_bodies=3,
        edges=[
            (1, 2, frozenset({"Quintile"})),
            (0, 1, frozenset({"Biquintile"})),
            (0, 2, frozenset({"Biquintile"})),
        ],
    ),
    # 12. Thor's Hammer
    _PatternTemplate(
        kind=AspectPatternKind.THORS_HAMMER,
        num_bodies=3,
        edges=[
            (1, 2, frozenset({"Square"})),
            (0, 1, frozenset({"Sesquiquadrate"})),
            (0, 2, frozenset({"Sesquiquadrate"})),
        ],
    ),
    # 13. Finger of the World
    _PatternTemplate(
        kind=AspectPatternKind.FINGER_OF_WORLD,
        num_bodies=3,
        edges=[
            (1, 2, frozenset({"Square"})),
            (0, 1, frozenset({"Semisquare"})),
            (0, 2, frozenset({"Semisquare"})),
        ],
    ),
    # 14. Grand Quintile
    _PatternTemplate(
        kind=AspectPatternKind.GRAND_QUINTILE,
        num_bodies=5,
        edges=[
            (0, 1, frozenset({"Quintile"})),
            (1, 2, frozenset({"Quintile"})),
            (2, 3, frozenset({"Quintile"})),
            (3, 4, frozenset({"Quintile"})),
            (4, 0, frozenset({"Quintile"})),
        ],
    ),
    # 15. Grand Septile
    _PatternTemplate(
        kind=AspectPatternKind.GRAND_SEPTILE,
        num_bodies=7,
        edges=[
            (0, 1, frozenset({"Septile"})),
            (1, 2, frozenset({"Septile"})),
            (2, 3, frozenset({"Septile"})),
            (3, 4, frozenset({"Septile"})),
            (4, 5, frozenset({"Septile"})),
            (5, 6, frozenset({"Septile"})),
            (6, 0, frozenset({"Septile"})),
        ],
    ),
    # 16. Grand Novile
    _PatternTemplate(
        kind=AspectPatternKind.GRAND_NOVILE,
        num_bodies=9,
        edges=[
            (0, 1, frozenset({"Novile"})),
            (1, 2, frozenset({"Novile"})),
            (2, 3, frozenset({"Novile"})),
            (3, 4, frozenset({"Novile"})),
            (4, 5, frozenset({"Novile"})),
            (5, 6, frozenset({"Novile"})),
            (6, 7, frozenset({"Novile"})),
            (7, 8, frozenset({"Novile"})),
            (8, 0, frozenset({"Novile"})),
        ],
    ),
    # 17. Envelope
    _PatternTemplate(
        kind=AspectPatternKind.ENVELOPE,
        num_bodies=5,
        edges=[
            (0, 3, frozenset({"Opposition"})),
            (1, 2, frozenset({"Opposition"})),
            (0, 1, frozenset({"Trine"})),
            (2, 3, frozenset({"Trine"})),
            (0, 2, frozenset({"Sextile"})),
            (1, 3, frozenset({"Sextile"})),
            (0, 4, frozenset({"Conjunction", "Sextile", "Square", "Trine", "Opposition"})),
            (1, 4, frozenset({"Conjunction", "Sextile", "Square", "Trine", "Opposition"})),
            (2, 4, frozenset({"Conjunction", "Sextile", "Square", "Trine", "Opposition"})),
            (3, 4, frozenset({"Conjunction", "Sextile", "Square", "Trine", "Opposition"})),
        ],
    ),
    # 18. Yod of Destiny
    _PatternTemplate(
        kind=AspectPatternKind.YOD_OF_DESTINY,
        num_bodies=4,
        edges=[
            (0, 1, frozenset({"Quincunx"})),
            (0, 2, frozenset({"Quincunx"})),
            (0, 3, frozenset({"Quincunx"})),
            (1, 2, frozenset({"Sextile"})),
            (2, 3, frozenset({"Sextile"})),
        ],
    ),
]


def _match_pattern_template(
    template: _PatternTemplate,
    adjacency: dict[str, dict[str, list[AspectData]]],
    all_bodies: list[str],
) -> list[AspectPattern]:
    num_vertices = template.num_bodies
    constraints = [[] for _ in range(num_vertices)]
    for u, v, allowed in template.edges:
        u, v = min(u, v), max(u, v)
        constraints[v].append((u, allowed))

    results: list[AspectPattern] = []
    seen_sets: set[frozenset[str]] = set()

    current = [None] * num_vertices
    used = set()

    def backtrack(idx: int) -> None:
        if idx == num_vertices:
            bodies_tuple = tuple(current)
            bodies_set = frozenset(bodies_tuple)
            if bodies_set in seen_sets:
                return

            match_aspects: list[AspectData] = []
            for u, v, allowed in template.edges:
                b_u, b_v = bodies_tuple[u], bodies_tuple[v]
                aspect_candidates = adjacency[b_u][b_v]
                match_aspects.append(next(a for a in aspect_candidates if a.aspect in allowed))

            if template.filter_fn is not None:
                if not template.filter_fn(bodies_tuple, match_aspects):
                    return

            seen_sets.add(bodies_set)
            results.append(AspectPattern(
                kind=template.kind,
                bodies=bodies_set,
                aspects=tuple(sorted(match_aspects, key=lambda a: (a.body1, a.body2, a.aspect))),
            ))
            return

        candidates = None
        for u, allowed in constraints[idx]:
            b_u = current[u]
            neighbors = set()
            for b_neighbor, aspect_list in adjacency.get(b_u, {}).items():
                if any(a.aspect in allowed for a in aspect_list):
                    neighbors.add(b_neighbor)
            if candidates is None:
                candidates = neighbors
            else:
                candidates &= neighbors
            if not candidates:
                return

        iter_candidates = all_bodies if candidates is None else candidates

        for b in iter_candidates:
            if b not in used:
                current[idx] = b
                used.add(b)
                backtrack(idx + 1)
                used.remove(b)
                current[idx] = None

    backtrack(0)
    return results


def find_patterns(aspects: list[AspectData]) -> list[AspectPattern]:
    """
    Detect multi-body aspect patterns from a list of admitted pairwise aspects.

    Pattern detection operates entirely on the supplied ``AspectData`` list.
    No positions, speeds, or external inputs are used.  Pairwise detection
    semantics are not changed.

    Implemented patterns (see ``AspectPatternKind`` for full doctrine)
    ------------------------------------------------------------------
    STELLIUM         — ≥3 bodies in mutual Conjunction.
    T_SQUARE         — 3 bodies: one Opposition + two Squares.
    GRAND_TRINE      — 3 bodies: three mutual Trines.
    GRAND_CROSS      — 4 bodies: two Oppositions + four Squares.
    YOD              — 3 bodies: Sextile base + two Quincunxes meeting at apex.
    KITE             — 4 bodies: Grand Trine + Opposition apex-focus + two Sextiles.
    MYSTIC_RECTANGLE — 4 bodies: two Oppositions + two Trines + two Sextiles.
    CRADLE           — 4 bodies: one Opposition + three Sextiles + two Trines.
    WEDGE            — 3 bodies: one Opposition + one Trine + one Sextile.
    BUTTERFLY        — 4 bodies: two Wedges sharing an Opposition axis.
    GRAND_SEXTILE    — 6 bodies: six consecutive Sextiles forming a loop.
    GOLDEN_YOD       — 3 bodies: two Biquintiles + one Quintile.
    THORS_HAMMER     — 3 bodies: two Sesquiquadrates + one Square.
    FINGER_OF_WORLD  — 3 bodies: two Semisquares + one Square.
    GRAND_QUINTILE   — 5 bodies: five Quintiles forming a closed pentagon.
    GRAND_SEPTILE    — 7 bodies: seven Septiles forming a closed heptagon.
    GRAND_NOVILE     — 9 bodies: nine Noviles forming a closed nonagon.
    ENVELOPE         — 5 bodies: a Mystic Rectangle connected to a fifth body.
    YOD_OF_DESTINY   — 4 bodies: three Quincunxes sharing apex + two Sextiles.

    Each detected pattern is reported at most once per unique body set.
    Sub-patterns contained within a larger Stellium are suppressed; all
    other pattern types are independent.

    Determinism contract
    --------------------
    The output is fully determined by the *logical content* of the input
    list, not by its ordering.  Specifically:

    - ``bodies`` is a ``frozenset`` — order-independent.
    - ``aspects`` inside each pattern is sorted by ``(body1, body2, aspect)``
      — identical for any permutation of the input list.
    - Patterns are emitted in the order of `AspectPatternKind` enum declaration.
      Within each kind, they are sorted by lexicographically ordered body names.

    Parameters
    ----------
    aspects : list of ``AspectData`` as returned by ``find_aspects``.

    Returns
    -------
    List of ``AspectPattern``, empty list when no pattern is found.
    """
    if not aspects:
        return []

    idx = _aspect_index(aspects)
    all_names: set[str] = {a.body1 for a in aspects} | {a.body2 for a in aspects}
    all_bodies = sorted(all_names)

    # Build adjacency mapping for templates matcher
    adjacency: dict[str, dict[str, list[AspectData]]] = {}
    for a in aspects:
        adjacency.setdefault(a.body1, {}).setdefault(a.body2, []).append(a)
        adjacency.setdefault(a.body2, {}).setdefault(a.body1, []).append(a)

    results = []
    # 1. Stellia
    results.extend(_find_stellia(aspects, idx))

    # 2. Declarative patterns
    for template in _PATTERN_TEMPLATES:
        matched = _match_pattern_template(template, adjacency, all_bodies)
        matched.sort(key=lambda p: sorted(p.bodies))
        results.extend(matched)

    return results


# ---------------------------------------------------------------------------
# Relational graph / network layer
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AspectGraphNode:
    """Vessel: Node in a relational aspect graph representing a body."""
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
    """Vessel: Relational graph of admitted pairwise aspects."""
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
    """Vessel: Statistical profile of aspect harmonic families."""
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
    """Vessel: Comprehensive profile of harmonic distributions."""
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
    3. ``AspectFamily.DECLINATION`` for the two canonical declination names.
    4. ``AspectFamily.UNKNOWN`` for an unclassified custom name.  Unknown
       zodiacal data is never silently relabelled as declination data.
    """
    raw: dict[AspectFamily, int] = {}
    for a in aspects:
        if a.classification is not None:
            fam = a.classification.family
        elif a.aspect in {"Parallel", "Contra-Parallel"}:
            fam = AspectFamily.DECLINATION
        else:
            fam = _FAMILY_BY_NAME.get(a.aspect, AspectFamily.UNKNOWN)
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

@dataclass(frozen=True, slots=True)
class AspectData:
    """Vessel: Result vessel for a detected longitude or whole-sign aspect."""
    """
    RITE: The Aspect Vessel — a detected angular relationship between two bodies.

    THEOREM: Holds the two body names, aspect name and symbol, target angle,
    actual angular separation, orb deviation, applied orb ceiling,
    applying/separating flag, stationary flag, and explicit classification
    for a single detected degree-based or whole-sign aspect.

    RITE OF PURPOSE:
        Serves the Aspect Engine as the canonical result vessel for all
        longitude and whole-sign detections.  The vessel preserves full admission
        context (Phase 1) and carries an explicit classification (Phase 2)
        so that a caller can determine not only *why* the aspect qualified
        but *what kind* of aspect it is, without reconstructing that
        knowledge from the name string.

    LAW OF OPERATION:
        Responsibilities:
            - Store both body names, aspect name, Unicode symbol, target
              angle, actual angular separation, non-negative orb deviation,
              allowed orb ceiling, applying/separating flag,
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
            - For ZODIACAL results, ``orb`` equals
              ``abs(separation - angle)`` and ``orb <= allowed_orb``.
            - For WHOLE_SIGN results, ``orb == allowed_orb == 0`` because
              the relationship is categorical rather than orb-admitted.
            - ``orb_surplus == allowed_orb - orb >= 0``.
            - ``separation`` is the raw angular distance (0–180°) between
              the two bodies as computed by ``angular_distance``.
            - ``allowed_orb`` is the orb ceiling actually applied (post
              orb_factor, post custom-orbs override).
            - ``classification.domain`` is ``AspectDomain.ZODIACAL`` or
              ``AspectDomain.WHOLE_SIGN`` for detector-produced vessels.
            - ``applying`` is ``None`` when the aspect is exact, either body
              is stationary, speeds are unavailable, or the result is categorical.
            - ``stationary`` is ``True`` when either body's speed is below
              0.01 deg/day.
            - ``is_applying`` and ``is_separating`` are mutually exclusive
              and both are ``False`` when ``applying`` is ``None``.
        Succession stance: terminal — not designed for subclassing.

    Degree-based admission identity (verifiable from vessel fields)::

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
                "applying", "stationary", "classification",
                "direction", "sign_degree1", "sign_degree2"
            ],
            "public_properties": [
                "is_major", "is_minor", "is_zodiacal",
                "is_applying", "is_separating", "orb_surplus", "is_partile",
                "is_platic"
            ]
        },
        "state": {
            "mutable": false,
            "fields": [
                "body1", "body2", "aspect", "symbol",
                "angle", "separation", "orb", "allowed_orb",
                "applying", "stationary", "classification",
                "direction", "sign_degree1", "sign_degree2"
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
    sign_degree1:   int | None = None    # 0-29 degree number within body1's sign
    sign_degree2:   int | None = None    # 0-29 degree number within body2's sign

    # ------------------------------------------------------------------
    # Inspectability — read-only, derived-only convenience properties
    # ------------------------------------------------------------------

    @property
    def is_major(self) -> bool:
        """True when this aspect belongs to the five Ptolemaic major aspects."""
        if self.classification is not None:
            return self.classification.tier is AspectTier.MAJOR
        return self.aspect in ("Conjunction", "Sextile", "Square", "Trine", "Opposition")

    @property
    def is_minor(self) -> bool:
        """True when this aspect is not a Ptolemaic major aspect."""
        if self.classification is not None:
            return self.classification.tier is not AspectTier.MAJOR
        return not self.is_major

    @property
    def is_zodiacal(self) -> bool:
        """True when this aspect is measured by degree along the ecliptic."""
        return (
            self.classification is None
            or self.classification.domain is AspectDomain.ZODIACAL
        )

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

    @property
    def is_partile(self) -> bool:
        """
        True when this is a Ptolemaic major aspect and both bodies share the
        same integer degree-of-sign.

        Returns ``False`` for non-major (non-Ptolemaic) aspects; sign-degree
        coincidence carries no doctrinal weight outside the five major aspects.
        """
        return (
            self.is_major
            and self.sign_degree1 is not None
            and self.sign_degree2 is not None
            and self.sign_degree1 == self.sign_degree2
        )

    @property
    def is_platic(self) -> bool:
        """
        True when a Ptolemaic major aspect is admitted but not partile.
        """
        return self.is_major and not self.is_partile

    def __repr__(self) -> str:
        app = " applying" if self.applying else " separating" if self.applying is False else ""
        sta = " [stationary]" if self.stationary else ""
        return f"{self.body1} {self.symbol} {self.body2}  (orb {self.orb:+.2f}°){app}{sta}"


@dataclass(frozen=True, slots=True)
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


@dataclass(frozen=True, slots=True)
class LongitudeAspectAnalysis:
    """First-class aspect analysis of caller-supplied ecliptic longitudes.

    The positions are synthetic or already-derived inputs, not an astronomical
    chart reduction.  Without speeds, applying/separating and stationary truth
    cannot be inferred; each returned ``AspectData`` therefore preserves the
    existing position-only motion semantics.
    """

    positions: tuple[tuple[str, float], ...]
    aspects: tuple[AspectData, ...]
    tier: int
    orb_factor: float
    include_nodes: bool
    excluded_node_names: tuple[str, ...]
    motion_semantics: str = "not_computed_without_speeds"

    @property
    def longitudes(self) -> dict[str, float]:
        """Return the normalized, deterministically ordered input positions."""

        return dict(self.positions)

    @property
    def point_count(self) -> int:
        return len(self.positions)

    @property
    def aspect_count(self) -> int:
        return len(self.aspects)


@dataclass(frozen=True, slots=True)
class AspectMotionWitness:
    """Inspectable instantaneous motion witness for one longitude aspect.

    ``directed_error_deg`` is measured on the selected signed aspect branch:
    the shortest directed longitude from ``body1`` to ``body2`` minus the
    same-sign exact aspect target.  Its time derivative is the caller-supplied
    relative longitude speed ``speed2 - speed1``.  Applying and separating
    therefore follow directly from whether that signed error is closing or
    opening; no future perfection or station search is implied.  When a
    non-conjunction target has equally near positive and negative branches at
    zero separation, the target and error remain undefined and the motion
    state is indeterminate.
    """

    body1: str
    body2: str
    longitude1_deg: float
    longitude2_deg: float
    speed1_deg_per_day: float | None
    speed2_deg_per_day: float | None
    aspect: str
    symbol: str
    angle_deg: float
    branch_selection: AspectMotionBranch
    target_directed_separation_deg: float | None
    directed_separation_deg: float
    directed_error_deg: float | None
    separation_deg: float
    orb_deg: float
    allowed_orb_deg: float
    within_orb: bool
    orb_policy: AspectMotionOrbPolicy
    orb_factor: float
    relative_speed_deg_per_day: float | None
    orb_rate_deg_per_day: float | None
    state: AspectMotionState
    exact_tolerance_deg: float
    rate_tolerance_deg_per_day: float
    body1_stationary_threshold_deg_per_day: float
    body2_stationary_threshold_deg_per_day: float
    body1_stationary: bool | None
    body2_stationary: bool | None
    relative_motion_stalled: bool | None
    stationary_reasons: tuple[AspectMotionStationaryReason, ...]
    reference_frame: str
    timescale: str
    provenance: str = "caller_supplied_longitudes_and_speeds"
    evaluation_scope: str = "instantaneous_no_event_search"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _resolve_aspects(
    tier: int | None,
    include_minor: bool,
) -> list[AspectDefinition]:
    """Return the aspect list for the given tier / include_minor flag."""
    if tier is not None:
        if (
            isinstance(tier, bool)
            or not isinstance(tier, int)
            or tier not in ASPECT_TIERS
        ):
            raise ValueError(f"aspect tier must be 0, 1, or 2, got {tier!r}")
        return ASPECT_TIERS[tier]
    if not isinstance(include_minor, bool):
        raise ValueError("include_minor must be a boolean")
    return Aspect.MAJOR + Aspect.COMMON_MINOR if include_minor else Aspect.MAJOR


# ---------------------------------------------------------------------------
# Moiety orb resolution
# ---------------------------------------------------------------------------

_MOIETY_DEFAULT_FULL_ORB = 5.0  # used for bodies absent from the moiety table


def _moiety_allowed_orb(
    b1: str,
    b2: str,
    table: Mapping[str, float],
) -> float:
    """
    Combined allowed orb for a pair of bodies under the moiety doctrine.

    Each body contributes its moiety (half its full orb).  Bodies absent
    from the table receive ``_MOIETY_DEFAULT_FULL_ORB`` (5°, moiety 2.5°).

    Parameters
    ----------
    b1, b2 : body names (``Body.*`` string constants).
    table  : per-body full-orb table (full orb; moiety = half).

    Returns
    -------
    float — combined moiety in degrees.
    """
    m1 = table.get(b1, _MOIETY_DEFAULT_FULL_ORB) / 2.0
    m2 = table.get(b2, _MOIETY_DEFAULT_FULL_ORB) / 2.0
    return m1 + m2


def _sign_degree_number(longitude: float) -> int:
    """
    Return the integer degree number within the sign for a longitude.

    0.0 Aries through 0.999... Aries yields 0; 29.0 through (30 - 1e-11)
    yields 29.  Values within 1e-11° of a 30°-boundary are snapped to
    degree 0 of the following sign to absorb floating-point rounding noise
    from upstream ephemeris calculations.
    """
    within_sign = longitude % 30.0
    if within_sign > 30.0 - 1e-11:
        return 0
    return int(within_sign)


_STATIONARY_THRESHOLDS: dict[str, float] = {
    Body.MERCURY: 0.060,
    Body.VENUS:   0.050,
    Body.MARS:    0.015,
    Body.JUPITER: 0.008,
    Body.SATURN:  0.004,
    Body.URANUS:  0.0015,
    Body.NEPTUNE: 0.0008,
    Body.PLUTO:   0.0005,
}


def _is_stationary(b1: str, b2: str, speeds: dict[str, float]) -> bool:
    """Return True when either body's speed is below its specific stationary threshold."""
    t1 = _STATIONARY_THRESHOLDS.get(b1, 0.005)
    t2 = _STATIONARY_THRESHOLDS.get(b2, 0.005)
    return (abs(speeds.get(b1, 1.0)) < t1
            or abs(speeds.get(b2, 1.0)) < t2)


def _applying(
    b1: str, lon1: float,
    b2: str, lon2: float,
    speeds: dict[str, float],
    angle: float,
) -> bool | None:
    """
    True = applying, False = separating, None = unknown or stationary.

    Returns None when the aspect is exact within 1e-9 degrees or either body's
    daily speed is below its specific stationary threshold.  Exactness takes
    precedence because the absolute orb has a cusp at perfection; applying
    versus separating requires a side-of-event statement there.

    The signed shortest-arc difference ``diff = (lon2 - lon1 + 180) % 360 - 180``
    gives the rate of change of the angular separation:

        d(sep)/dt = speed_b2 - speed_b1   when diff >= 0
        d(sep)/dt = speed_b1 - speed_b2   when diff <  0

    The orb ``|sep - angle|`` is decreasing (applying) when:
        sep >= angle  →  d(sep)/dt < 0
        sep <  angle  →  d(sep)/dt > 0
    """
    if b1 not in speeds or b2 not in speeds:
        return None
    if _is_stationary(b1, b2, speeds):
        return None
    diff = (lon2 - lon1 + 180.0) % 360.0 - 180.0
    sep = abs(diff)
    if abs(sep - angle) <= 1e-9:
        return None
    dsep_dt = (speeds[b2] - speeds[b1]) if diff >= 0 else (speeds[b1] - speeds[b2])
    return dsep_dt < 0 if sep >= angle else dsep_dt > 0


def aspect_motion_witness(
    body1: str,
    longitude1_deg: float,
    body2: str,
    longitude2_deg: float,
    aspect: str,
    *,
    speed1_deg_per_day: float | None = None,
    speed2_deg_per_day: float | None = None,
    orb_factor: float = 1.0,
    exact_tolerance_deg: float = 1e-9,
    rate_tolerance_deg_per_day: float = 1e-12,
    reference_frame: str,
    timescale: str,
) -> AspectMotionWitness:
    """Return an immutable signed motion witness for one selected aspect.

    The computation is kernel-free and instantaneous.  Longitudes and daily
    speeds are caller-owned inputs; ``reference_frame`` and ``timescale`` are
    therefore required provenance rather than inferred defaults.  The aspect
    target and default orb come from :class:`moira.constants.Aspect`.

    Exactness takes precedence over motion classification.  Away from exact,
    missing speeds produce ``indeterminate``; a body below Moira's existing
    body-specific stationary threshold or a relative rate within the supplied
    rate tolerance produces ``stationary``.  Otherwise the signed branch error
    and relative speed determine applying versus separating.
    """

    for field_name, value in (("body1", body1), ("body2", body2)):
        if not isinstance(value, str) or not value or value != value.strip():
            raise ValueError(f"{field_name} must be a non-empty trimmed string")
    if body1 == body2:
        raise ValueError("body1 and body2 must identify distinct points")
    if not isinstance(aspect, str):
        raise ValueError("aspect must name one canonical longitude aspect")
    definition = next((item for item in Aspect.ALL if item.name == aspect), None)
    if definition is None:
        raise ValueError(f"unknown canonical longitude aspect {aspect!r}")

    def finite_number(name: str, value: float) -> float:
        if isinstance(value, bool):
            raise ValueError(f"{name} must be finite")
        try:
            parsed = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{name} must be finite") from exc
        if not math.isfinite(parsed):
            raise ValueError(f"{name} must be finite")
        return parsed

    longitude1 = finite_number("longitude1_deg", longitude1_deg) % 360.0
    longitude2 = finite_number("longitude2_deg", longitude2_deg) % 360.0
    speed1 = (
        None
        if speed1_deg_per_day is None
        else finite_number("speed1_deg_per_day", speed1_deg_per_day)
    )
    speed2 = (
        None
        if speed2_deg_per_day is None
        else finite_number("speed2_deg_per_day", speed2_deg_per_day)
    )
    resolved_orb_factor = finite_number("orb_factor", orb_factor)
    exact_tolerance = finite_number("exact_tolerance_deg", exact_tolerance_deg)
    rate_tolerance = finite_number(
        "rate_tolerance_deg_per_day", rate_tolerance_deg_per_day
    )
    if resolved_orb_factor <= 0.0:
        raise ValueError("orb_factor must be positive")
    if exact_tolerance < 0.0:
        raise ValueError("exact_tolerance_deg must be non-negative")
    if rate_tolerance < 0.0:
        raise ValueError("rate_tolerance_deg_per_day must be non-negative")
    for field_name, value in (
        ("reference_frame", reference_frame),
        ("timescale", timescale),
    ):
        if not isinstance(value, str) or not value or value != value.strip():
            raise ValueError(f"{field_name} must be a non-empty trimmed string")

    directed_separation = (
        (longitude2 - longitude1 + 180.0) % 360.0
    ) - 180.0
    if definition.angle == 0.0:
        branch_selection = AspectMotionBranch.UNDIRECTED_CONJUNCTION
        target_directed_separation = 0.0
    elif directed_separation == 0.0:
        branch_selection = AspectMotionBranch.AMBIGUOUS_AT_ZERO_SEPARATION
        target_directed_separation = None
    elif directed_separation > 0.0:
        branch_selection = AspectMotionBranch.POSITIVE
        target_directed_separation = definition.angle
    else:
        branch_selection = AspectMotionBranch.NEGATIVE
        target_directed_separation = -definition.angle
    directed_error = (
        None
        if target_directed_separation is None
        else directed_separation - target_directed_separation
    )
    separation = abs(directed_separation)
    orb = abs(separation - definition.angle)
    allowed_orb = definition.default_orb * resolved_orb_factor

    threshold1 = _STATIONARY_THRESHOLDS.get(body1, 0.005)
    threshold2 = _STATIONARY_THRESHOLDS.get(body2, 0.005)
    body1_stationary = None if speed1 is None else abs(speed1) < threshold1
    body2_stationary = None if speed2 is None else abs(speed2) < threshold2
    relative_speed = None if speed1 is None or speed2 is None else speed2 - speed1
    relative_motion_stalled = (
        None
        if relative_speed is None
        else abs(relative_speed) <= rate_tolerance
    )

    stationary_reasons: list[AspectMotionStationaryReason] = []
    if body1_stationary:
        stationary_reasons.append(AspectMotionStationaryReason.BODY1_BELOW_THRESHOLD)
    if body2_stationary:
        stationary_reasons.append(AspectMotionStationaryReason.BODY2_BELOW_THRESHOLD)
    if relative_motion_stalled:
        stationary_reasons.append(
            AspectMotionStationaryReason.RELATIVE_RATE_WITHIN_TOLERANCE
        )

    is_exact = orb <= exact_tolerance
    orb_rate = (
        None
        if relative_speed is None or is_exact or directed_error is None
        else math.copysign(1.0, directed_error) * relative_speed
    )
    if is_exact:
        state = AspectMotionState.EXACT
    elif relative_speed is None or directed_error is None:
        state = AspectMotionState.INDETERMINATE
    elif stationary_reasons:
        state = AspectMotionState.STATIONARY
    elif orb_rate is not None and orb_rate < 0.0:
        state = AspectMotionState.APPLYING
    else:
        state = AspectMotionState.SEPARATING

    return AspectMotionWitness(
        body1=body1,
        body2=body2,
        longitude1_deg=longitude1,
        longitude2_deg=longitude2,
        speed1_deg_per_day=speed1,
        speed2_deg_per_day=speed2,
        aspect=definition.name,
        symbol=definition.symbol,
        angle_deg=definition.angle,
        branch_selection=branch_selection,
        target_directed_separation_deg=target_directed_separation,
        directed_separation_deg=directed_separation,
        directed_error_deg=directed_error,
        separation_deg=separation,
        orb_deg=orb,
        allowed_orb_deg=allowed_orb,
        within_orb=orb <= allowed_orb,
        orb_policy=AspectMotionOrbPolicy.CANONICAL_DEFAULT_SCALED,
        orb_factor=resolved_orb_factor,
        relative_speed_deg_per_day=relative_speed,
        orb_rate_deg_per_day=orb_rate,
        state=state,
        exact_tolerance_deg=exact_tolerance,
        rate_tolerance_deg_per_day=rate_tolerance,
        body1_stationary_threshold_deg_per_day=threshold1,
        body2_stationary_threshold_deg_per_day=threshold2,
        body1_stationary=body1_stationary,
        body2_stationary=body2_stationary,
        relative_motion_stalled=relative_motion_stalled,
        stationary_reasons=tuple(stationary_reasons),
        reference_frame=reference_frame,
        timescale=timescale,
    )


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
    sign1 = int((lon1 % 360.0 + 1e-11) // 30) % 12
    sign2 = int((lon2 % 360.0 + 1e-11) // 30) % 12
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

    When ``policy.orb_mode="moiety"``, detection is restricted to the five
    Ptolemaic major aspects regardless of ``tier`` or ``include_minor``.

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
    resolved_policy = policy or AspectPolicy(
        tier=tier,
        include_minor=include_minor,
        orbs=orbs,
        orb_factor=orb_factor,
    )
    tier = resolved_policy.tier
    include_minor = resolved_policy.include_minor
    orbs = resolved_policy.orbs
    orb_factor = resolved_policy.orb_factor
    _use_moiety = resolved_policy.orb_mode == "moiety"
    _moiety_table = (
        resolved_policy.moiety_orbs
        if resolved_policy.moiety_orbs is not None
        else TRADITIONAL_MOIETY_ORBS
    )
    positions = _normalized_named_values(positions, quantity="longitude")
    if speeds is not None:
        speeds = _normalized_named_values(speeds, quantity="speed")
    aspect_list = Aspect.MAJOR if _use_moiety else _resolve_aspects(tier, include_minor)
    bodies = list(positions.keys())
    results: list[AspectData] = []

    for i in range(len(bodies)):
        for j in range(i + 1, len(bodies)):
            b1, b2 = bodies[i], bodies[j]
            lon1, lon2 = positions[b1], positions[b2]
            sep = angular_distance(lon1, lon2)
            pair_allowed = _moiety_allowed_orb(b1, b2, _moiety_table) if _use_moiety else None

            for adef in aspect_list:
                if _use_moiety:
                    allowed = pair_allowed
                elif orbs is not None:
                    allowed = orbs.get(adef.angle, adef.default_orb)
                else:
                    allowed = adef.default_orb * orb_factor
                orb = abs(sep - adef.angle)
                if orb <= allowed:
                    app = _applying(b1, lon1, b2, lon2, speeds, adef.angle) if speeds else None
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
                        sign_degree1=_sign_degree_number(lon1),
                        sign_degree2=_sign_degree_number(lon2),
                    ))

    results.sort(key=lambda a: a.orb)
    return results


_DERIVED_CHART_NODE_NAMES = frozenset(
    {Body.TRUE_NODE, Body.MEAN_NODE, Body.LILITH, Body.TRUE_LILITH}
)


def aspects_from_longitudes(
    longitudes: Mapping[str, float],
    *,
    tier: int = 1,
    orb_factor: float = 1.0,
    include_nodes: bool = True,
) -> LongitudeAspectAnalysis:
    """Analyze supplied ecliptic longitudes under canonical aspect doctrine.

    This is the position-only entry point for composite, harmonic, progressed,
    and other derived charts that do not represent an ephemeris moment.  It
    normalizes longitudes, establishes deterministic point ordering, applies
    the caller-declared tier and orb multiplier, and delegates detection to
    :func:`find_aspects`.  It never fabricates speeds or temporal motion state.
    """

    if isinstance(tier, bool) or tier not in {0, 1, 2}:
        raise ValueError("aspect tier must be 0, 1, or 2")
    if isinstance(orb_factor, bool):
        raise ValueError("aspect orb_factor must be positive and finite")
    try:
        resolved_orb_factor = float(orb_factor)
    except (TypeError, ValueError) as exc:
        raise ValueError("aspect orb_factor must be positive and finite") from exc
    if not math.isfinite(resolved_orb_factor) or resolved_orb_factor <= 0.0:
        raise ValueError("aspect orb_factor must be positive and finite")
    if not isinstance(include_nodes, bool):
        raise ValueError("aspect include_nodes must be boolean")
    if not isinstance(longitudes, Mapping):
        raise ValueError("longitudes must be a mapping of point names to degrees")

    normalized: dict[str, float] = {}
    excluded: list[str] = []
    for name, value in longitudes.items():
        if not isinstance(name, str) or not name or name != name.strip():
            raise ValueError("longitude point names must be non-empty trimmed strings")
        if isinstance(value, bool):
            raise ValueError(f"longitude for {name!r} must be finite")
        try:
            longitude = float(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"longitude for {name!r} must be finite") from exc
        if not math.isfinite(longitude):
            raise ValueError(f"longitude for {name!r} must be finite")
        if not include_nodes and name in _DERIVED_CHART_NODE_NAMES:
            excluded.append(name)
            continue
        normalized[name] = longitude % 360.0

    if len(normalized) < 2:
        raise ValueError("at least two included longitude points are required")

    ordered = dict(sorted(normalized.items()))
    aspects = find_aspects(
        ordered,
        tier=tier,
        orb_factor=resolved_orb_factor,
    )
    return LongitudeAspectAnalysis(
        positions=tuple(ordered.items()),
        aspects=tuple(aspects),
        tier=tier,
        orb_factor=resolved_orb_factor,
        include_nodes=include_nodes,
        excluded_node_names=tuple(sorted(excluded)),
    )


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

    When ``policy.orb_mode="moiety"``, detection is restricted to the five
    Ptolemaic major aspects regardless of ``tier`` or ``include_minor``.

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
    resolved_policy = policy or AspectPolicy(
        tier=tier,
        orbs=orbs,
        orb_factor=orb_factor,
    )
    _use_moiety = resolved_policy.orb_mode == "moiety"
    _moiety_table = (
        resolved_policy.moiety_orbs
        if resolved_policy.moiety_orbs is not None
        else TRADITIONAL_MOIETY_ORBS
    )
    orbs = resolved_policy.orbs
    orb_factor = resolved_policy.orb_factor
    if _use_moiety:
        aspect_list = Aspect.MAJOR
    elif resolved_policy.tier is not None:
        aspect_list = _resolve_aspects(resolved_policy.tier, True)
    else:
        aspect_list = _resolve_aspects(None, resolved_policy.include_minor)
    for field_name, value in (("body_a", body_a), ("body_b", body_b)):
        if not isinstance(value, str) or not value or value != value.strip():
            raise ValueError(f"{field_name} must be a non-empty trimmed string")
    lon_a = _finite_number("lon_a", lon_a)
    lon_b = _finite_number("lon_b", lon_b)
    if speed_a is not None:
        speed_a = _finite_number("speed_a", speed_a)
    if speed_b is not None:
        speed_b = _finite_number("speed_b", speed_b)
    sep = angular_distance(lon_a, lon_b)
    pair_allowed = _moiety_allowed_orb(body_a, body_b, _moiety_table) if _use_moiety else None
    results: list[AspectData] = []

    speeds = {}
    if speed_a is not None:
        speeds[body_a] = speed_a
    if speed_b is not None:
        speeds[body_b] = speed_b

    for adef in aspect_list:
        if _use_moiety:
            allowed = pair_allowed
        elif orbs is not None:
            allowed = orbs.get(adef.angle, adef.default_orb)
        else:
            allowed = adef.default_orb * orb_factor
        orb = abs(sep - adef.angle)
        if orb <= allowed:
            app = _applying(body_a, lon_a, body_b, lon_b, speeds, adef.angle) if speeds else None
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
                sign_degree1=_sign_degree_number(lon_a),
                sign_degree2=_sign_degree_number(lon_b),
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

    When ``policy.orb_mode="moiety"``, detection is restricted to the five
    Ptolemaic major aspects regardless of ``tier`` or ``include_minor``.

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
    resolved_policy = policy or AspectPolicy(
        tier=tier,
        include_minor=include_minor,
        orbs=orbs,
        orb_factor=orb_factor,
    )
    _use_moiety = resolved_policy.orb_mode == "moiety"
    _moiety_table = (
        resolved_policy.moiety_orbs
        if resolved_policy.moiety_orbs is not None
        else TRADITIONAL_MOIETY_ORBS
    )
    tier = resolved_policy.tier
    include_minor = resolved_policy.include_minor
    orbs = resolved_policy.orbs
    orb_factor = resolved_policy.orb_factor
    point_longitude = _finite_number("point_longitude", point_longitude)
    if (
        not isinstance(point_name, str)
        or not point_name
        or point_name != point_name.strip()
    ):
        raise ValueError("point_name must be a non-empty trimmed string")
    positions = _normalized_named_values(positions, quantity="longitude")
    aspect_list = Aspect.MAJOR if _use_moiety else _resolve_aspects(tier, include_minor)
    results: list[AspectData] = []

    for body, lon in positions.items():
        sep = angular_distance(lon, point_longitude)
        pair_allowed = _moiety_allowed_orb(body, point_name, _moiety_table) if _use_moiety else None
        for adef in aspect_list:
            if _use_moiety:
                allowed = pair_allowed
            elif orbs is not None:
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
                    sign_degree1=_sign_degree_number(lon),
                    sign_degree2=_sign_degree_number(point_longitude),
                ))

    results.sort(key=lambda a: a.orb)
    return results


# ---------------------------------------------------------------------------
# Declination aspects: parallels and contra-parallels
# ---------------------------------------------------------------------------

def find_declination_aspects(
    declinations: Mapping[str, float],
    orb: float = 1.0,
    policy: AspectPolicy | None = None,
) -> list[DeclinationAspect]:
    """Compatibility entrypoint for the first-class declination engine.

    New declination-only callers may import the governing function from
    moira.declination_aspects and use DeclinationAspectPolicy directly. The
    historical AspectPolicy parameter remains supported here.
    """

    resolved_orb = policy.declination_orb if policy is not None else orb
    return _find_declination_aspects(
        declinations,
        policy=DeclinationAspectPolicy(orb=resolved_orb),
    )


def declination_aspects_from_declinations(
    declinations: Mapping[str, float],
    *,
    reference_frame: str,
    timescale: str,
    orb: float = 1.0,
    policy: AspectPolicy | None = None,
) -> DeclinationAspectAnalysis:
    """Compatibility entrypoint for first-class declination analysis."""

    resolved_orb = policy.declination_orb if policy is not None else orb
    return _declination_analysis(
        declinations,
        reference_frame=reference_frame,
        timescale=timescale,
        policy=DeclinationAspectPolicy(orb=resolved_orb),
    )


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
    declinations = _normalized_named_values(
        declinations,
        quantity="declination",
        minimum=-90.0,
        maximum=90.0,
    )
    obliquity = _finite_number("obliquity", obliquity)
    if not 0.0 < obliquity <= 90.0:
        raise ValueError("obliquity must be in (0, 90]")
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
    positions = _normalized_named_values(positions, quantity="longitude")
    bodies = list(positions.keys())
    results: list[AspectData] = []

    for i in range(len(bodies)):
        for j in range(i + 1, len(bodies)):
            b1, b2 = bodies[i], bodies[j]
            lon1, lon2 = positions[b1], positions[b2]

            sign1 = int((lon1 % 360.0 + 1e-11) // 30) % 12
            sign2 = int((lon2 % 360.0 + 1e-11) // 30) % 12
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
                sign_degree1=_sign_degree_number(lon1),
                sign_degree2=_sign_degree_number(lon2),
            ))

    return results
