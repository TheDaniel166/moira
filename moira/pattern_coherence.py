"""
Moira — Aspect Pattern Coherence & Qualitative Scoring
======================================================

Archetype: Engine
Policy identifier: moira.pattern_coherence.qualitative.v1-draft

Purpose
-------
Governs qualitative evaluation of geometric coherence and instantaneous motion
state for admitted degree-based aspect patterns under a named, frozen reference
doctrine.

RITE OF PURPOSE:
    Replaces arbitrary composite percentage scoring with an auditable
    two-part qualitative result:
        1. Coherence band: determined by the loosest required aspect relative
           to a fixed reference orb.
        2. Motion qualifier: describes applying, exact, separating,
           station-sensitive, or unavailable motion without altering the
           coherence band.

    "Strength" denotes geometric coherence under this named convention.
    It does not denote psychological dominance, physical power, or outcome
    prediction.

Boundary declaration
--------------------
Owns:
    - Frozen reference orbs table for pattern scoring.
    - Weakest-required-link ratio aggregation and coherence band mapping.
    - Motion qualifier precedence evaluation over required pattern relationships.
    - Result vessels `PatternRequiredAspectLedger` and `PatternCoherenceResult`.
    - `evaluate_pattern_coherence()` pure computation.
Delegates:
    - Aspect motion witnessing to `moira.aspects.aspect_motion_witness`.
    - Pattern detection and template definitions to `moira.patterns`.

Canon & Specifications:
    - `docs/architecture/ASPECT_PATTERN_QUALITATIVE_SCORING_V1_DRAFT.md`
    - Ptolemy, "Tetrabiblos" I; Lilly, "Christian Astrology" (1647).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping, Sequence

from ._strenum import StrEnum
from .aspects import AspectData, AspectDomain, MotionState, aspect_motion_witness


# ---------------------------------------------------------------------------
# Policy Identifiers and Frozen Reference Constants
# ---------------------------------------------------------------------------

POLICY_ID: str = "moira.pattern_coherence.qualitative.v1-draft"

FROZEN_REFERENCE_ORBS: MappingProxyType[str, float] = MappingProxyType({
    "Opposition": 8.0,
    "Square": 7.0,
    "Trine": 7.0,
    "Sextile": 5.0,
    "Quincunx": 3.0,
})

_ADMITTED_PATTERNS: frozenset[str] = frozenset({
    "T-Square",
    "Grand Trine",
    "Grand Cross",
    "Yod",
    "Mystic Rectangle",
    "Kite",
})

_RELATION_PHRASES: MappingProxyType[str, str] = MappingProxyType({
    "Opposition": "opposite",
    "Square": "square",
    "Trine": "trine",
    "Sextile": "sextile",
    "Quincunx": "quincunx",
})


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PatternCoherenceBand(StrEnum):
    """
    Qualitative coherence classification for an aspect pattern.

    Determined strictly by the largest ratio R = (actual_orb / reference_orb)
    among all required aspects of the pattern.
    """

    VERY_STRONG = "Very strong"
    STRONG = "Strong"
    MODERATE = "Moderate"
    LOOSE = "Loose"
    MARGINAL = "Marginal"
    NOT_ASSESSED = "Not assessed"


class PatternMotionQualifier(StrEnum):
    """
    Instantaneous motion qualifier for an aspect pattern.

    Derived from the signed motion state of the pattern's required aspects
    evaluated in a strict precedence order.
    """

    MOTION_UNAVAILABLE = "Motion unavailable"
    PARTIAL_MOTION = "Partial motion"
    STATION_SENSITIVE = "Station-sensitive"
    EXACT = "Exact"
    APPLYING = "Applying"
    SEPARATING = "Separating"
    MIXED_MOTION = "Mixed motion"


# ---------------------------------------------------------------------------
# Result Vessels
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class PatternRequiredAspectLedger:
    """
    Immutable ledger entry for one required aspect in an aspect pattern.

    Preserves full precision angular orb, the fixed scoring reference orb,
    the resulting utilization ratio, and the instantaneous motion state.
    """

    body1: str
    body2: str
    aspect: str
    actual_orb_deg: float
    reference_orb_deg: float
    reference_orb_use: float
    motion_state: str | None = None
    is_limiting: bool = False
    exceeds_reference: bool = False

    def __post_init__(self) -> None:
        if self.body1 == self.body2:
            raise ValueError("PatternRequiredAspectLedger invariant failed: bodies must differ")
        if not math.isfinite(self.actual_orb_deg) or self.actual_orb_deg < 0.0:
            raise ValueError("PatternRequiredAspectLedger invariant failed: actual_orb_deg must be non-negative and finite")
        if not math.isfinite(self.reference_orb_deg) or self.reference_orb_deg <= 0.0:
            raise ValueError("PatternRequiredAspectLedger invariant failed: reference_orb_deg must be positive and finite")
        expected_ratio = self.actual_orb_deg / self.reference_orb_deg
        if abs(self.reference_orb_use - expected_ratio) > 1e-12:
            raise ValueError("PatternRequiredAspectLedger invariant failed: reference_orb_use must equal actual_orb / reference_orb")
        expected_exceeds = self.actual_orb_deg > self.reference_orb_deg
        if self.exceeds_reference != expected_exceeds:
            raise ValueError("PatternRequiredAspectLedger invariant failed: exceeds_reference must match geometry")


@dataclass(frozen=True, slots=True)
class PatternCoherenceResult:
    """
    Complete qualitative scoring result for an aspect pattern.

    Combines the geometric coherence band with the instantaneous motion qualifier,
    the weakest-link ratio R, inspectable ledger entries, and a plain-language summary.
    """

    policy_id: str
    pattern_name: str
    band: PatternCoherenceBand
    motion_qualifier: PatternMotionQualifier | None
    weakest_link_ratio: float | None
    limiting_aspects: tuple[PatternRequiredAspectLedger, ...]
    required_aspects: tuple[PatternRequiredAspectLedger, ...]
    supplemental_aspects: tuple[PatternRequiredAspectLedger, ...] = ()
    motion_counts: Mapping[str, int] = field(default_factory=dict)
    plain_language_summary: str = ""
    assessment_reason: str | None = None

    @property
    def is_assessed(self) -> bool:
        """Return True when the pattern was successfully evaluated."""
        return self.band is not PatternCoherenceBand.NOT_ASSESSED


# ---------------------------------------------------------------------------
# Formatting Helpers
# ---------------------------------------------------------------------------

def _format_angle_dms(degrees: float) -> str:
    """Format angular degree as degree and minute string, e.g. 2°00′ or 0°18′."""
    total_seconds = round(degrees * 3600.0)
    d = int(total_seconds // 3600)
    m = int((total_seconds % 3600) // 60)
    return f"{d}°{m:02d}′"


def _format_summary(
    pattern_name: str,
    band: PatternCoherenceBand,
    qualifier: PatternMotionQualifier | None,
    ledger: Sequence[PatternRequiredAspectLedger],
    counts: Mapping[str, int],
) -> str:
    """Construct plain-language compact presentation matching canonical doctrine."""
    header = (
        f"{pattern_name} — {band.value} · {qualifier.value}"
        if qualifier is not None
        else f"{pattern_name} — {band.value}"
    )

    n_req = len(ledger)
    if band is PatternCoherenceBand.VERY_STRONG:
        band_desc = f"All {n_req} required aspects are within the inner tenth of their fixed reference orbs."
    elif band is PatternCoherenceBand.STRONG:
        band_desc = f"All {n_req} required aspects are within the inner quarter of their fixed reference orbs."
    elif band is PatternCoherenceBand.MODERATE:
        band_desc = "The pattern holds together with noticeable angular spread."
    elif band is PatternCoherenceBand.LOOSE:
        band_desc = "At least one required relationship is broad."
    elif band is PatternCoherenceBand.MARGINAL:
        if any(item.exceeds_reference for item in ledger):
            band_desc = "At least one required relationship exceeds its fixed scoring reference."
        else:
            band_desc = "At least one required relationship is near or beyond its reference limit."
    else:
        band_desc = "Geometric coherence not assessed."

    limiting = [item for item in ledger if item.is_limiting]
    if len(limiting) == 1:
        lim = limiting[0]
        verb = _RELATION_PHRASES.get(lim.aspect, lim.aspect.lower())
        orb_str = _format_angle_dms(lim.actual_orb_deg)
        lim_str = f"Limiting relationship: {lim.body1} {verb} {lim.body2}, orb {orb_str}."
    elif len(limiting) > 1:
        phrases = [
            f"{lim.body1} {_RELATION_PHRASES.get(lim.aspect, lim.aspect.lower())} {lim.body2}, orb {_format_angle_dms(lim.actual_orb_deg)}"
            for lim in limiting
        ]
        lim_str = f"Limiting relationships: {'; '.join(phrases)}."
    else:
        lim_str = ""

    if qualifier is None or qualifier is PatternMotionQualifier.MOTION_UNAVAILABLE:
        mot_str = "Motion: unavailable."
    elif qualifier is PatternMotionQualifier.EXACT:
        mot_str = f"Motion: all {n_req} exact."
    elif qualifier is PatternMotionQualifier.APPLYING:
        mot_str = f"Motion: all {n_req} applying."
    elif qualifier is PatternMotionQualifier.SEPARATING:
        mot_str = f"Motion: all {n_req} separating."
    else:
        parts: list[str] = []
        for key in ("applying", "separating", "exact", "stationary", "indeterminate"):
            c = counts.get(key, 0)
            if c > 0:
                label = "station-sensitive" if key == "stationary" else key
                parts.append(f"{c} {label}")
        mot_str = f"Motion: {' · '.join(parts)}."

    body_text = f"{band_desc} {lim_str}".strip()
    return f"{header}\n\n{body_text}\n{mot_str}"


# ---------------------------------------------------------------------------
# Template Matching & Required Edge Ledger Extraction
# ---------------------------------------------------------------------------

def _extract_template_edges(
    pattern: object,
) -> tuple[tuple[AspectData, ...] | None, tuple[AspectData, ...], str | None]:
    """
    Extract required and supplemental edges for the six admitted pattern templates.

    Returns (required_aspects, supplemental_aspects, failure_reason).
    If the template is unsupported or required aspects are invalid, required_aspects is None.
    """
    name = getattr(pattern, "name", None)
    if not isinstance(name, str) or name not in _ADMITTED_PATTERNS:
        return None, (), f"Unsupported pattern template {name!r}; admitted patterns are {sorted(_ADMITTED_PATTERNS)}"

    raw_aspects: tuple[AspectData, ...] = tuple(getattr(pattern, "aspects", ()))
    bodies: tuple[str, ...] = tuple(getattr(pattern, "bodies", ()))
    apex: str | None = getattr(pattern, "apex", None)

    if not raw_aspects:
        return None, (), f"No aspect links found in pattern {name!r}"
    if not bodies:
        return None, (), f"No bodies found in pattern {name!r}"

    # Validate that aspects are degree-based zodiacal and finite
    for asp in raw_aspects:
        if not isinstance(asp, AspectData):
            return None, (), "Pattern aspects must be instances of AspectData"
        if (
            asp.classification is not None
            and asp.classification.domain is AspectDomain.WHOLE_SIGN
        ):
            return None, (), "Categorical whole-sign aspects are not admitted for geometric coherence"
        if not math.isfinite(asp.orb) or not math.isfinite(asp.angle) or not math.isfinite(asp.separation):
            return None, (), "Non-finite geometric values encountered in pattern aspects"
        if isinstance(asp.orb, bool) or isinstance(asp.angle, bool) or isinstance(asp.separation, bool):
            return None, (), "Boolean values are not valid aspect angles or orbs"

    # Deduplicate edges by (canonical_body_pair, aspect_name)
    edge_map: dict[tuple[frozenset[str], str], AspectData] = {}
    for asp in raw_aspects:
        pair_key = (frozenset({asp.body1, asp.body2}), asp.aspect)
        existing = edge_map.get(pair_key)
        if existing is not None:
            # Check for conflicting duplicates
            if abs(existing.orb - asp.orb) > 1e-9 or abs(existing.angle - asp.angle) > 1e-9:
                return None, (), f"Conflicting aspect definitions for body pair {sorted(pair_key[0])}"
            # Identical duplicate: keep first occurrence
            continue
        edge_map[pair_key] = asp

    deduped_aspects = list(edge_map.values())

    def get_link(b1: str, b2: str, asp_name: str) -> AspectData | None:
        return edge_map.get((frozenset({b1, b2}), asp_name))

    # Pattern-specific template matching
    if name == "T-Square":
        # Requires 3 bodies: 2 base bodies opposing each other, each squaring the apex.
        if len(bodies) != 3:
            return None, (), f"T-Square requires exactly 3 bodies, found {len(bodies)}"
        # Resolve apex
        if apex is not None and apex in bodies:
            base_bodies = [b for b in bodies if b != apex]
        else:
            # Infer apex: unique body in 2 squares and 0 oppositions
            opp_counts = {b: 0 for b in bodies}
            sq_counts = {b: 0 for b in bodies}
            for asp in deduped_aspects:
                if asp.aspect == "Opposition":
                    opp_counts[asp.body1] += 1
                    opp_counts[asp.body2] += 1
                elif asp.aspect == "Square":
                    sq_counts[asp.body1] += 1
                    sq_counts[asp.body2] += 1
            cand_apex = [b for b in bodies if sq_counts[b] == 2 and opp_counts[b] == 0]
            if len(cand_apex) != 1:
                return None, (), "Unable to uniquely resolve apex for T-Square"
            apex = cand_apex[0]
            base_bodies = [b for b in bodies if b != apex]

        p1, p2 = base_bodies
        opp = get_link(p1, p2, "Opposition")
        sq1 = get_link(p1, apex, "Square")
        sq2 = get_link(p2, apex, "Square")
        if not (opp and sq1 and sq2):
            return None, (), "Missing required aspect links for T-Square (1 opposition, 2 squares)"
        required = (opp, sq1, sq2)
        supplemental = tuple(a for a in deduped_aspects if a not in required)
        return required, supplemental, None

    elif name == "Grand Trine":
        if len(bodies) != 3:
            return None, (), f"Grand Trine requires exactly 3 bodies, found {len(bodies)}"
        a, b, c = bodies
        t_ab = get_link(a, b, "Trine")
        t_bc = get_link(b, c, "Trine")
        t_ac = get_link(a, c, "Trine")
        if not (t_ab and t_bc and t_ac):
            return None, (), "Missing required aspect links for Grand Trine (3 trines)"
        required = (t_ab, t_bc, t_ac)
        supplemental = tuple(a for a in deduped_aspects if a not in required)
        return required, supplemental, None

    elif name == "Grand Cross":
        if len(bodies) != 4:
            return None, (), f"Grand Cross requires exactly 4 bodies, found {len(bodies)}"
        # Find 2 disjoint oppositions
        opps = [a for a in deduped_aspects if a.aspect == "Opposition"]
        squares = [a for a in deduped_aspects if a.aspect == "Square"]
        if len(opps) < 2 or len(squares) < 4:
            return None, (), "Missing required aspect links for Grand Cross (2 oppositions, 4 squares)"
        # Match cross topology: two disjoint oppositions (p, q) and (r, s),
        # connected by squares (p, r), (r, q), (q, s), (s, p).
        matched_required: tuple[AspectData, ...] | None = None
        for i in range(len(opps)):
            for j in range(i + 1, len(opps)):
                o1, o2 = opps[i], opps[j]
                p, q = o1.body1, o1.body2
                r, s = o2.body1, o2.body2
                if len({p, q, r, s}) != 4:
                    continue
                sq_pr = get_link(p, r, "Square")
                sq_rq = get_link(r, q, "Square")
                sq_qs = get_link(q, s, "Square")
                sq_sp = get_link(s, p, "Square")
                if sq_pr and sq_rq and sq_qs and sq_sp:
                    matched_required = (o1, o2, sq_pr, sq_rq, sq_qs, sq_sp)
                    break
            if matched_required:
                break
        if not matched_required:
            return None, (), "Aspect links do not form a valid closed Grand Cross topology"
        supplemental = tuple(a for a in deduped_aspects if a not in matched_required)
        return matched_required, supplemental, None

    elif name == "Yod":
        if len(bodies) != 3:
            return None, (), f"Yod requires exactly 3 bodies, found {len(bodies)}"
        if apex is not None and apex in bodies:
            base_bodies = [b for b in bodies if b != apex]
        else:
            qncx_counts = {b: 0 for b in bodies}
            for asp in deduped_aspects:
                if asp.aspect == "Quincunx":
                    qncx_counts[asp.body1] += 1
                    qncx_counts[asp.body2] += 1
            cand_apex = [b for b in bodies if qncx_counts[b] == 2]
            if len(cand_apex) != 1:
                return None, (), "Unable to uniquely resolve apex for Yod"
            apex = cand_apex[0]
            base_bodies = [b for b in bodies if b != apex]

        p1, p2 = base_bodies
        sext = get_link(p1, p2, "Sextile")
        q1 = get_link(p1, apex, "Quincunx")
        q2 = get_link(p2, apex, "Quincunx")
        if not (sext and q1 and q2):
            return None, (), "Missing required aspect links for Yod (1 sextile, 2 quincunxes)"
        required = (sext, q1, q2)
        supplemental = tuple(a for a in deduped_aspects if a not in required)
        return required, supplemental, None

    elif name == "Mystic Rectangle":
        if len(bodies) != 4:
            return None, (), f"Mystic Rectangle requires exactly 4 bodies, found {len(bodies)}"
        opps = [a for a in deduped_aspects if a.aspect == "Opposition"]
        trines = [a for a in deduped_aspects if a.aspect == "Trine"]
        sexts = [a for a in deduped_aspects if a.aspect == "Sextile"]
        if len(opps) < 2 or len(trines) < 2 or len(sexts) < 2:
            return None, (), "Missing required aspect links for Mystic Rectangle (2 opp, 2 trines, 2 sextiles)"

        matched_required = None
        for i in range(len(opps)):
            for j in range(i + 1, len(opps)):
                o1, o2 = opps[i], opps[j]
                p, r = o1.body1, o1.body2
                q, s = o2.body1, o2.body2
                if len({p, q, r, s}) != 4:
                    continue
                for q_cand, s_cand in ((q, s), (s, q)):
                    t1 = get_link(p, q_cand, "Trine")
                    t2 = get_link(r, s_cand, "Trine")
                    s1 = get_link(q_cand, r, "Sextile")
                    s2 = get_link(s_cand, p, "Sextile")
                    if t1 and t2 and s1 and s2:
                        matched_required = (o1, o2, t1, t2, s1, s2)
                        break
                if matched_required:
                    break
            if matched_required:
                break
        if not matched_required:
            return None, (), "Aspect links do not form a valid closed Mystic Rectangle topology"
        supplemental = tuple(a for a in deduped_aspects if a not in matched_required)
        return matched_required, supplemental, None

    elif name == "Kite":
        if len(bodies) != 4:
            return None, (), f"Kite requires exactly 4 bodies, found {len(bodies)}"
        opps = [a for a in deduped_aspects if a.aspect == "Opposition"]
        trines = [a for a in deduped_aspects if a.aspect == "Trine"]
        sexts = [a for a in deduped_aspects if a.aspect == "Sextile"]
        if not opps or len(trines) < 3 or len(sexts) < 2:
            return None, (), "Missing required aspect links for Kite (1 opp, 3 trines, 2 sextiles)"

        matched_required = None
        for opp in opps:
            cand_pairs = [(opp.body1, opp.body2), (opp.body2, opp.body1)]
            for cand_tail, cand_apex in cand_pairs:
                if apex is not None and cand_apex != apex:
                    continue
                support = [b for b in bodies if b not in {cand_tail, cand_apex}]
                if len(support) != 2:
                    continue
                x, y = support
                t_xy = get_link(x, y, "Trine")
                t_xa = get_link(x, cand_apex, "Trine")
                t_ya = get_link(y, cand_apex, "Trine")
                s_tx = get_link(cand_tail, x, "Sextile")
                s_ty = get_link(cand_tail, y, "Sextile")
                if t_xy and t_xa and t_ya and s_tx and s_ty:
                    matched_required = (opp, t_xy, t_xa, t_ya, s_tx, s_ty)
                    break
            if matched_required:
                break
        if not matched_required:
            return None, (), "Aspect links do not form a valid closed Kite topology"
        supplemental = tuple(a for a in deduped_aspects if a not in matched_required)
        return matched_required, supplemental, None

    return None, (), f"Unhandled template {name!r}"


# ---------------------------------------------------------------------------
# Evaluator Function
# ---------------------------------------------------------------------------

def evaluate_pattern_coherence(
    pattern: object,
    *,
    positions: Mapping[str, float] | None = None,
    speeds: Mapping[str, float] | None = None,
    reference_frame: str = "geocentric_ecliptic",
    timescale: str = "UT1",
    exact_tolerance_deg: float = 1e-9,
    rate_tolerance_deg_per_day: float = 1e-12,
) -> PatternCoherenceResult:
    """
    Evaluate geometric coherence and motion qualifier for one detected aspect pattern.

    Consumes an existing detected pattern without modifying detector admission
    logic or widening orbs.

    Parameters
    ----------
    pattern : AspectPattern
        The detected pattern vessel.
    positions : Mapping[str, float] | None
        Optional dictionary of body longitudes (degrees). If provided alongside
        speeds, evaluates signed motion witnesses directly via `aspect_motion_witness`.
    speeds : Mapping[str, float] | None
        Optional dictionary of daily longitude rates (degrees/day).
    reference_frame : str
        Reference frame provenance for motion witness (default: "geocentric_ecliptic").
    timescale : str
        Timescale provenance for motion witness (default: "UT1").
    exact_tolerance_deg : float
        Tolerance under which an orb deviation is considered exact (default: 1e-9).
    rate_tolerance_deg_per_day : float
        Rate tolerance under which relative motion is considered stalled (default: 1e-12).

    Returns
    -------
    PatternCoherenceResult
        The auditable qualitative evaluation.
    """
    pattern_name = getattr(pattern, "name", "Unknown")

    required_aspects, supplemental_aspects, failure_reason = _extract_template_edges(pattern)

    if required_aspects is None or failure_reason is not None:
        # Build unassessed supplemental records if valid aspects were present
        raw_aspects = tuple(getattr(pattern, "aspects", ()))
        unassessed_records: list[PatternRequiredAspectLedger] = []
        for asp in raw_aspects:
            if isinstance(asp, AspectData) and asp.aspect in FROZEN_REFERENCE_ORBS:
                ref = FROZEN_REFERENCE_ORBS[asp.aspect]
                if math.isfinite(asp.orb) and not isinstance(asp.orb, bool):
                    unassessed_records.append(
                        PatternRequiredAspectLedger(
                            body1=asp.body1,
                            body2=asp.body2,
                            aspect=asp.aspect,
                            actual_orb_deg=asp.orb,
                            reference_orb_deg=ref,
                            reference_orb_use=asp.orb / ref,
                            exceeds_reference=asp.orb > ref,
                        )
                    )

        reason = failure_reason or "Pattern could not be assessed"
        return PatternCoherenceResult(
            policy_id=POLICY_ID,
            pattern_name=pattern_name,
            band=PatternCoherenceBand.NOT_ASSESSED,
            motion_qualifier=None,
            weakest_link_ratio=None,
            limiting_aspects=(),
            required_aspects=(),
            supplemental_aspects=tuple(unassessed_records),
            motion_counts={},
            plain_language_summary=f"{pattern_name} — Not assessed ({reason})",
            assessment_reason=reason,
        )

    # -----------------------------------------------------------------------
    # Step 1: Motion evaluation for each required aspect
    # -----------------------------------------------------------------------
    motion_states: list[str] = []
    for asp in required_aspects:
        state_str = "indeterminate"
        if positions is not None and asp.body1 in positions and asp.body2 in positions:
            # Caller supplied explicit positions (and optionally speeds)
            witness = aspect_motion_witness(
                body1=asp.body1,
                longitude1_deg=positions[asp.body1],
                body2=asp.body2,
                longitude2_deg=positions[asp.body2],
                aspect=asp.aspect,
                speed1_deg_per_day=speeds.get(asp.body1) if speeds else None,
                speed2_deg_per_day=speeds.get(asp.body2) if speeds else None,
                reference_frame=reference_frame,
                timescale=timescale,
                exact_tolerance_deg=exact_tolerance_deg,
                rate_tolerance_deg_per_day=rate_tolerance_deg_per_day,
            )
            state_str = witness.state.value  # exact, stationary, applying, separating, indeterminate
        else:
            # Fall back to inspecting aspect.motion_state from AspectData
            ms = asp.motion_state
            if ms is MotionState.EXACT:
                state_str = "exact"
            elif ms is MotionState.STATIONARY:
                state_str = "stationary"
            elif ms is MotionState.APPLYING:
                state_str = "applying"
            elif ms is MotionState.SEPARATING:
                state_str = "separating"
            else:
                state_str = "indeterminate"
        motion_states.append(state_str)

    # Motion counts
    n_req = len(required_aspects)
    counts: dict[str, int] = {
        "indeterminate": sum(1 for s in motion_states if s == "indeterminate"),
        "stationary": sum(1 for s in motion_states if s == "stationary"),
        "exact": sum(1 for s in motion_states if s == "exact"),
        "applying": sum(1 for s in motion_states if s == "applying"),
        "separating": sum(1 for s in motion_states if s == "separating"),
    }

    # Evaluate motion qualifier in strict precedence order
    if counts["indeterminate"] == n_req:
        qualifier = PatternMotionQualifier.MOTION_UNAVAILABLE
    elif counts["indeterminate"] > 0:
        qualifier = PatternMotionQualifier.PARTIAL_MOTION
    elif counts["stationary"] > 0:
        qualifier = PatternMotionQualifier.STATION_SENSITIVE
    elif counts["exact"] == n_req:
        qualifier = PatternMotionQualifier.EXACT
    elif counts["applying"] == n_req:
        qualifier = PatternMotionQualifier.APPLYING
    elif counts["separating"] == n_req:
        qualifier = PatternMotionQualifier.SEPARATING
    else:
        qualifier = PatternMotionQualifier.MIXED_MOTION

    # -----------------------------------------------------------------------
    # Step 2: Geometric Coherence Band (Weakest-link ratio R)
    # -----------------------------------------------------------------------
    raw_ratios: list[float] = []
    for asp in required_aspects:
        ref_orb = FROZEN_REFERENCE_ORBS.get(asp.aspect)
        if ref_orb is None:
            reason = f"Aspect {asp.aspect!r} has no frozen scoring reference orb"
            return PatternCoherenceResult(
                policy_id=POLICY_ID,
                pattern_name=pattern_name,
                band=PatternCoherenceBand.NOT_ASSESSED,
                motion_qualifier=None,
                weakest_link_ratio=None,
                limiting_aspects=(),
                required_aspects=(),
                supplemental_aspects=(),
                motion_counts={},
                plain_language_summary=f"{pattern_name} — Not assessed ({reason})",
                assessment_reason=reason,
            )
        raw_ratios.append(asp.orb / ref_orb)

    weakest_r = max(raw_ratios)

    # Band mapping: unrounded comparison against frozen boundaries
    # 0 through 0.10: Very strong
    # Greater than 0.10 through 0.25: Strong
    # Greater than 0.25 through 0.50: Moderate
    # Greater than 0.50 through 0.75: Loose
    # Greater than 0.75: Marginal
    if weakest_r <= 0.10:
        band = PatternCoherenceBand.VERY_STRONG
    elif weakest_r <= 0.25:
        band = PatternCoherenceBand.STRONG
    elif weakest_r <= 0.50:
        band = PatternCoherenceBand.MODERATE
    elif weakest_r <= 0.75:
        band = PatternCoherenceBand.LOOSE
    else:
        band = PatternCoherenceBand.MARGINAL

    # -----------------------------------------------------------------------
    # Step 3: Build immutable ledger entries
    # -----------------------------------------------------------------------
    required_ledger: list[PatternRequiredAspectLedger] = []
    for asp, ratio, mot in zip(required_aspects, raw_ratios, motion_states):
        ref_orb = FROZEN_REFERENCE_ORBS[asp.aspect]
        is_lim = abs(ratio - weakest_r) <= 1e-12
        exceeds = asp.orb > ref_orb
        required_ledger.append(
            PatternRequiredAspectLedger(
                body1=asp.body1,
                body2=asp.body2,
                aspect=asp.aspect,
                actual_orb_deg=asp.orb,
                reference_orb_deg=ref_orb,
                reference_orb_use=ratio,
                motion_state=mot,
                is_limiting=is_lim,
                exceeds_reference=exceeds,
            )
        )

    limiting_ledger = tuple(item for item in required_ledger if item.is_limiting)

    supplemental_ledger: list[PatternRequiredAspectLedger] = []
    for asp in supplemental_aspects:
        ref_orb = FROZEN_REFERENCE_ORBS.get(asp.aspect, asp.allowed_orb)
        ratio = asp.orb / ref_orb if ref_orb > 0.0 else 0.0
        supplemental_ledger.append(
            PatternRequiredAspectLedger(
                body1=asp.body1,
                body2=asp.body2,
                aspect=asp.aspect,
                actual_orb_deg=asp.orb,
                reference_orb_deg=ref_orb,
                reference_orb_use=ratio,
                motion_state=None,
                is_limiting=False,
                exceeds_reference=asp.orb > ref_orb,
            )
        )

    summary = _format_summary(
        pattern_name=pattern_name,
        band=band,
        qualifier=qualifier,
        ledger=required_ledger,
        counts=counts,
    )

    return PatternCoherenceResult(
        policy_id=POLICY_ID,
        pattern_name=pattern_name,
        band=band,
        motion_qualifier=qualifier,
        weakest_link_ratio=weakest_r,
        limiting_aspects=limiting_ledger,
        required_aspects=tuple(required_ledger),
        supplemental_aspects=tuple(supplemental_ledger),
        motion_counts=counts,
        plain_language_summary=summary,
        assessment_reason=None,
    )


__all__ = [
    "POLICY_ID",
    "FROZEN_REFERENCE_ORBS",
    "PatternCoherenceBand",
    "PatternMotionQualifier",
    "PatternRequiredAspectLedger",
    "PatternCoherenceResult",
    "evaluate_pattern_coherence",
]
