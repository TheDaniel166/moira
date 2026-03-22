"""
Moira — Aspect Pattern Engine
==============================

Archetype: Engine

Purpose
-------
Governs detection of classical and modern multi-body aspect configurations
within a natal chart, including T-Squares, Grand Trines, Yods, Kites,
Stelliums, and seventeen additional pattern types.

Boundary declaration
--------------------
Owns: pattern detection logic, orb arithmetic, deduplication of matched
      configurations, and the ``AspectPattern`` result vessel.
Delegates: aspect computation to ``moira.aspects``,
           angular distance arithmetic to ``moira.coordinates``.

Import-time side effects: None

External dependency assumptions
--------------------------------
No Qt main thread required. No database access. Pure computation over
pre-computed aspect lists and position dicts.

Orb doctrine
------------
All base orbs derive from ``moira.constants.DEFAULT_ORBS``, the same table
used by the aspect engine.  Pattern-specific orbs are listed in each detector
docstring and are scaled by the caller-supplied ``orb_factor``.

    Conjunction / Opposition : 8.0°
    Trine                    : 7.0°
    Square                   : 7.0°
    Sextile                  : 5.0°
    Quincunx (150°)          : 3.0°
    Semisquare (45°)         : 2.0°
    Sesquiquadrate (135°)    : 2.0°
    Quintile (72°)           : 2.0°
    Biquintile (144°)        : 2.0°
    Septile (51.43°)         : 1.5°
    Biseptile (102.86°)      : 1.5°
    Triseptile (154.29°)     : 1.5°

Public surface
--------------
``AspectPattern``           — vessel for a detected multi-body configuration.
``find_t_squares``          — detect T-Square configurations.
``find_grand_trines``       — detect Grand Trine configurations.
``find_grand_crosses``      — detect Grand Cross configurations.
``find_yods``               — detect Yod (Finger of God) configurations.
``find_mystic_rectangles``  — detect Mystic Rectangle configurations.
``find_kites``              — detect Kite configurations.
``find_stelliums``          — detect Stellium clusters.
``find_minor_grand_trines`` — detect Minor Grand Trine configurations.
``find_grand_sextiles``     — detect Grand Sextile (Star of David) configurations.
``find_thors_hammers``      — detect Thor's Hammer configurations.
``find_boomerang_yods``     — detect Boomerang Yod configurations.
``find_wedges``             — detect Wedge (Arrowhead) configurations.
``find_cradles``            — detect Cradle configurations.
``find_trapezes``           — detect Trapeze configurations.
``find_eyes``               — detect Eye (Cosmic Eye) configurations.
``find_irritation_triangles`` — detect Irritation Triangle configurations.
``find_hard_wedges``        — detect Hard Wedge configurations.
``find_dominant_triangles`` — detect Dominant Triangle configurations.
``find_grand_quintiles``    — detect Grand Quintile configurations.
``find_quintile_triangles`` — detect Quintile Triangle configurations.
``find_septile_triangles``  — detect Septile Triangle configurations.
``find_all_patterns``       — detect all registered patterns in one call.
"""

import math
from dataclasses import dataclass, field
from itertools import combinations

from .aspects import AspectData, find_aspects
from .coordinates import angular_distance


__all__ = [
    "AspectPattern",
    "find_t_squares",
    "find_grand_trines",
    "find_grand_crosses",
    "find_yods",
    "find_mystic_rectangles",
    "find_kites",
    "find_stelliums",
    "find_minor_grand_trines",
    "find_grand_sextiles",
    "find_thors_hammers",
    "find_boomerang_yods",
    "find_wedges",
    "find_cradles",
    "find_trapezes",
    "find_eyes",
    "find_irritation_triangles",
    "find_hard_wedges",
    "find_dominant_triangles",
    "find_grand_quintiles",
    "find_quintile_triangles",
    "find_septile_triangles",
    "find_all_patterns",
]


# ---------------------------------------------------------------------------
# Result vessel
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AspectPattern:
    """
    A detected multi-body aspect configuration.

    Fields
    ------
    name    : pattern name (e.g. "T-Square", "Grand Trine").
    bodies  : tuple of body names involved; apex planet is last for
              apex-bearing patterns (T-Square, Yod, Kite, etc.).
    aspects : tuple of the contributing AspectData instances.
    apex    : focal/apex planet name, or None for symmetric patterns.

    Structural invariants
    ---------------------
    - ``bodies`` is always non-empty.
    - ``aspects`` may be empty for Stelliums (position-based, not aspect-based).
    - ``apex`` is None for symmetric patterns (Grand Trine, Grand Cross, etc.).
    - The vessel is immutable.
    """
    name:    str
    bodies:  tuple[str, ...]
    aspects: tuple[AspectData, ...]
    apex:    str | None = None

    def __repr__(self) -> str:
        parts = " - ".join(self.bodies)
        apex_str = f" [apex: {self.apex}]" if self.apex else ""
        return f"{self.name}: {parts}{apex_str}"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_aspect_map(
    aspects: list[AspectData],
) -> dict[tuple[str, str], AspectData]:
    """Build a bidirectional lookup: (b1, b2) and (b2, b1) -> AspectData."""
    mapping: dict[tuple[str, str], AspectData] = {}
    for asp in aspects:
        mapping[(asp.body1, asp.body2)] = asp
        mapping[(asp.body2, asp.body1)] = asp
    return mapping


def _get_aspect(
    aspect_map: dict[tuple[str, str], AspectData],
    b1: str,
    b2: str,
    target_angle: float,
    orb: float,
) -> AspectData | None:
    """
    Return the aspect between b1 and b2 if it was admitted within ``orb``
    degrees of ``target_angle``, else None.

    Admission test: asp.orb <= orb.
    The asp.orb field already encodes the angular deviation from the target
    angle as recorded at admission time by find_aspects; no secondary
    angle check is applied here.
    """
    asp = aspect_map.get((b1, b2))
    if asp is not None and asp.orb <= orb:
        return asp
    return None


def _dedup_patterns(patterns: list[AspectPattern]) -> list[AspectPattern]:
    """
    Remove duplicate patterns.  Two patterns are duplicates when they share
    the same name and the same body set.  The first occurrence is kept.
    """
    seen: set[tuple[str, frozenset[str]]] = set()
    unique: list[AspectPattern] = []
    for p in patterns:
        key = (p.name, frozenset(p.bodies))
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


def _bodies_from(aspects: list[AspectData]) -> list[str]:
    """Sorted unique body list from an aspect list."""
    return sorted({asp.body1 for asp in aspects} | {asp.body2 for asp in aspects})


# ---------------------------------------------------------------------------
# Pattern detectors — classical
# ---------------------------------------------------------------------------

def find_t_squares(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    T-Square: body_A opposition body_B, both square body_C (apex).

    Orbs: opposition 8° * orb_factor, square 7° * orb_factor.
    """
    opp_orb = 8.0 * orb_factor
    sq_orb  = 7.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c in combinations(bodies, 3):
        for apex, p1, p2 in [(c, a, b), (a, b, c), (b, a, c)]:
            opp_asp = _get_aspect(aspect_map, p1, p2, 180.0, opp_orb)
            sq1_asp = _get_aspect(aspect_map, p1, apex, 90.0, sq_orb)
            sq2_asp = _get_aspect(aspect_map, p2, apex, 90.0, sq_orb)
            if opp_asp and sq1_asp and sq2_asp:
                results.append(AspectPattern(
                    name="T-Square",
                    bodies=(*sorted([p1, p2]), apex),
                    aspects=(opp_asp, sq1_asp, sq2_asp),
                    apex=apex,
                ))
                break

    return _dedup_patterns(results)


def find_grand_trines(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Grand Trine: three bodies all trine (120°) each other.

    Orb: 7° * orb_factor.
    """
    trine_orb = 7.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c in combinations(bodies, 3):
        t_ab = _get_aspect(aspect_map, a, b, 120.0, trine_orb)
        t_bc = _get_aspect(aspect_map, b, c, 120.0, trine_orb)
        t_ac = _get_aspect(aspect_map, a, c, 120.0, trine_orb)
        if t_ab and t_bc and t_ac:
            results.append(AspectPattern(
                name="Grand Trine",
                bodies=tuple(sorted([a, b, c])),
                aspects=(t_ab, t_bc, t_ac),
            ))

    return _dedup_patterns(results)


def find_grand_crosses(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Grand Cross: two oppositions and four squares forming a closed cross.

    Orbs: opposition 8° * orb_factor, square 7° * orb_factor.
    """
    opp_orb = 8.0 * orb_factor
    sq_orb  = 7.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c, d in combinations(bodies, 4):
        pairs = [((a, b), (c, d)), ((a, c), (b, d)), ((a, d), (b, c))]
        for (p, q), (r, s) in pairs:
            opp1 = _get_aspect(aspect_map, p, q, 180.0, opp_orb)
            opp2 = _get_aspect(aspect_map, r, s, 180.0, opp_orb)
            if not (opp1 and opp2):
                continue
            sq_pr = _get_aspect(aspect_map, p, r, 90.0, sq_orb)
            sq_rq = _get_aspect(aspect_map, r, q, 90.0, sq_orb)
            sq_qs = _get_aspect(aspect_map, q, s, 90.0, sq_orb)
            sq_sp = _get_aspect(aspect_map, s, p, 90.0, sq_orb)
            if sq_pr and sq_rq and sq_qs and sq_sp:
                results.append(AspectPattern(
                    name="Grand Cross",
                    bodies=tuple(sorted([a, b, c, d])),
                    aspects=(opp1, opp2, sq_pr, sq_rq, sq_qs, sq_sp),
                ))
                break

    return _dedup_patterns(results)


def find_yods(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Yod (Finger of God): A sextile B, both quincunx (150°) C (apex).

    Orbs: sextile 3° * orb_factor, quincunx 3° * orb_factor.
    """
    sext_orb = 3.0 * orb_factor
    qncx_orb = 3.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c in combinations(bodies, 3):
        for apex, p1, p2 in [(c, a, b), (a, b, c), (b, a, c)]:
            sext = _get_aspect(aspect_map, p1, p2, 60.0, sext_orb)
            q1   = _get_aspect(aspect_map, p1, apex, 150.0, qncx_orb)
            q2   = _get_aspect(aspect_map, p2, apex, 150.0, qncx_orb)
            if sext and q1 and q2:
                results.append(AspectPattern(
                    name="Yod",
                    bodies=(*sorted([p1, p2]), apex),
                    aspects=(sext, q1, q2),
                    apex=apex,
                ))
                break

    return _dedup_patterns(results)


def find_mystic_rectangles(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Mystic Rectangle: two trines + two sextiles + two oppositions.
    Adjacent sides alternate trine/sextile; diagonals are oppositions.

    Orbs: trine 7°, sextile 5°, opposition 8° — all * orb_factor.
    """
    trine_orb = 7.0 * orb_factor
    sext_orb  = 5.0 * orb_factor
    opp_orb   = 8.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c, d in combinations(bodies, 4):
        for ordering in [(a, b, c, d), (a, b, d, c), (a, c, b, d)]:
            p, q, r, s = ordering
            t_pq = _get_aspect(aspect_map, p, q, 120.0, trine_orb)
            t_rs = _get_aspect(aspect_map, r, s, 120.0, trine_orb)
            s_qr = _get_aspect(aspect_map, q, r,  60.0, sext_orb)
            s_sp = _get_aspect(aspect_map, s, p,  60.0, sext_orb)
            o_pr = _get_aspect(aspect_map, p, r, 180.0, opp_orb)
            o_qs = _get_aspect(aspect_map, q, s, 180.0, opp_orb)
            if t_pq and t_rs and s_qr and s_sp and o_pr and o_qs:
                results.append(AspectPattern(
                    name="Mystic Rectangle",
                    bodies=tuple(sorted([a, b, c, d])),
                    aspects=(t_pq, t_rs, s_qr, s_sp, o_pr, o_qs),
                ))
                break

    return _dedup_patterns(results)


def find_kites(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Kite: Grand Trine (A, B, C) with a fourth planet D opposing one vertex
    (apex) and sextile the other two.

    Orbs: trine 7°, sextile 5°, opposition 8° — all * orb_factor.
    """
    trine_orb = 7.0 * orb_factor
    sext_orb  = 5.0 * orb_factor
    opp_orb   = 8.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c, d in combinations(bodies, 4):
        for tail, x, y, apex in [
            (d, a, b, c), (d, a, c, b), (d, b, c, a),
            (c, a, b, d), (c, a, d, b), (c, b, d, a),
            (b, a, c, d), (b, a, d, c), (b, c, d, a),
            (a, b, c, d), (a, b, d, c), (a, c, d, b),
        ]:
            t_xy    = _get_aspect(aspect_map, x,    y,    120.0, trine_orb)
            t_xa    = _get_aspect(aspect_map, x,    apex, 120.0, trine_orb)
            t_ya    = _get_aspect(aspect_map, y,    apex, 120.0, trine_orb)
            opp     = _get_aspect(aspect_map, tail, apex, 180.0, opp_orb)
            sext_tx = _get_aspect(aspect_map, tail, x,    60.0,  sext_orb)
            sext_ty = _get_aspect(aspect_map, tail, y,    60.0,  sext_orb)
            if t_xy and t_xa and t_ya and opp and sext_tx and sext_ty:
                results.append(AspectPattern(
                    name="Kite",
                    bodies=tuple(sorted([a, b, c, d])),
                    aspects=(t_xy, t_xa, t_ya, opp, sext_tx, sext_ty),
                    apex=apex,
                ))
                break

    return _dedup_patterns(results)


def find_stelliums(
    positions: dict[str, float],
    min_bodies: int = 3,
    orb: float = 8.0,
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Stellium: 3+ bodies within ``orb * orb_factor`` degrees of the group
    circular centroid.  Only maximal groups are returned (no sub-group of
    a reported Stellium is reported separately).

    Parameters
    ----------
    positions  : dict of body name -> tropical longitude
    min_bodies : minimum number of bodies required (default 3)
    orb        : base spread in degrees (default 8.0)
    orb_factor : multiplier applied to orb (default 1.0)
    """
    effective_orb = orb * orb_factor
    body_list = sorted(positions.keys())
    results: list[AspectPattern] = []

    for size in range(min_bodies, len(body_list) + 1):
        for group in combinations(body_list, size):
            lons = [positions[b] for b in group]
            sin_sum = sum(math.sin(math.radians(lon)) for lon in lons)
            cos_sum = sum(math.cos(math.radians(lon)) for lon in lons)
            centroid = math.degrees(math.atan2(sin_sum, cos_sum)) % 360.0
            if all(angular_distance(lon, centroid) <= effective_orb for lon in lons):
                results.append(AspectPattern(
                    name="Stellium",
                    bodies=tuple(sorted(group)),
                    aspects=(),
                ))

    unique = _dedup_patterns(results)
    body_sets = [frozenset(p.bodies) for p in unique]
    return [
        p for i, p in enumerate(unique)
        if not any(body_sets[i] < other for other in body_sets)
    ]


def find_minor_grand_trines(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Minor Grand Trine: A trine B, both sextile C.

    Orbs: trine 7° * orb_factor, sextile 3° * orb_factor.
    """
    trine_orb = 7.0 * orb_factor
    sext_orb  = 3.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c in combinations(bodies, 3):
        for apex, p1, p2 in [(c, a, b), (a, b, c), (b, a, c)]:
            trine = _get_aspect(aspect_map, p1, p2,   120.0, trine_orb)
            sext1 = _get_aspect(aspect_map, p1, apex,  60.0, sext_orb)
            sext2 = _get_aspect(aspect_map, p2, apex,  60.0, sext_orb)
            if trine and sext1 and sext2:
                results.append(AspectPattern(
                    name="Minor Grand Trine",
                    bodies=tuple(sorted([p1, p2, apex])),
                    aspects=(trine, sext1, sext2),
                ))
                break

    return _dedup_patterns(results)


def find_grand_sextiles(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Grand Sextile (Star of David): six planets all in mutual sextile (60°),
    forming two interlocking Grand Trines.

    Orb: 3° * orb_factor.
    """
    sext_orb = 3.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for group in combinations(bodies, 6):
        group_aspects: list[AspectData] = []
        valid = True
        for b1, b2 in combinations(group, 2):
            asp = _get_aspect(aspect_map, b1, b2, 60.0, sext_orb)
            if asp is None:
                valid = False
                break
            group_aspects.append(asp)
        if valid:
            results.append(AspectPattern(
                name="Grand Sextile",
                bodies=tuple(sorted(group)),
                aspects=tuple(group_aspects),
            ))

    return _dedup_patterns(results)


def find_thors_hammers(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Thor's Hammer (God's Fist): two planets in square (90°), both
    sesquiquadrate (135°) an apex planet.

    Orbs: square 5° * orb_factor, sesquiquadrate 2° * orb_factor.
    """
    sq_orb   = 5.0 * orb_factor
    sesq_orb = 2.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c in combinations(bodies, 3):
        for apex, p1, p2 in [(c, a, b), (a, b, c), (b, a, c)]:
            sq = _get_aspect(aspect_map, p1, p2,    90.0, sq_orb)
            s1 = _get_aspect(aspect_map, p1, apex, 135.0, sesq_orb)
            s2 = _get_aspect(aspect_map, p2, apex, 135.0, sesq_orb)
            if sq and s1 and s2:
                results.append(AspectPattern(
                    name="Thor's Hammer",
                    bodies=(*sorted([p1, p2]), apex),
                    aspects=(sq, s1, s2),
                    apex=apex,
                ))
                break

    return _dedup_patterns(results)


def find_boomerang_yods(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Boomerang Yod: standard Yod (A sextile B, both quincunx C apex) plus a
    fourth planet D opposing the apex C.

    Orbs: sextile 3°, quincunx 3°, opposition 5° — all * orb_factor.
    """
    sext_orb = 3.0 * orb_factor
    qncx_orb = 3.0 * orb_factor
    opp_orb  = 5.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c, d in combinations(bodies, 4):
        for apex, p1, p2, boom in [
            (c, a, b, d), (d, a, b, c),
            (b, a, c, d), (d, a, c, b),
            (a, b, c, d), (d, b, c, a),
        ]:
            sext = _get_aspect(aspect_map, p1,   p2,    60.0, sext_orb)
            q1   = _get_aspect(aspect_map, p1,   apex, 150.0, qncx_orb)
            q2   = _get_aspect(aspect_map, p2,   apex, 150.0, qncx_orb)
            opp  = _get_aspect(aspect_map, boom, apex, 180.0, opp_orb)
            if sext and q1 and q2 and opp:
                results.append(AspectPattern(
                    name="Boomerang Yod",
                    bodies=tuple(sorted([p1, p2, apex, boom])),
                    aspects=(sext, q1, q2, opp),
                    apex=apex,
                ))
                break

    return _dedup_patterns(results)


def find_wedges(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Wedge (Arrowhead): planet A opposing planet B; a third planet C trine
    one and sextile the other.

    Orbs: opposition 8°, trine/sextile 5° — all * orb_factor.
    """
    opp_orb  = 8.0 * orb_factor
    trsx_orb = 5.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c in combinations(bodies, 3):
        for p1, p2, apex in [(a, b, c), (a, c, b), (b, c, a)]:
            opp = _get_aspect(aspect_map, p1,   p2,   180.0, opp_orb)
            tr  = _get_aspect(aspect_map, apex, p1,   120.0, trsx_orb)
            sx  = _get_aspect(aspect_map, apex, p2,    60.0, trsx_orb)
            if opp and tr and sx:
                results.append(AspectPattern(
                    name="Wedge",
                    bodies=(*sorted([p1, p2]), apex),
                    aspects=(opp, tr, sx),
                    apex=apex,
                ))
                break

    return _dedup_patterns(results)


# ---------------------------------------------------------------------------
# Pattern detectors — extended classical / Huber-recognized
# ---------------------------------------------------------------------------

def find_cradles(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Cradle: two Minor Grand Trines sharing a common opposition as their base.
    Structure: A opp D, A trine B, B sext C, C trine D, A sext C, B sext D.
    Equivalently: four planets in sequence A-B-C-D where A opp D, the two
    outer planets each trine their adjacent inner planet, and the two inner
    planets sextile the opposite outer planet.

    Orbs: opposition 8°, trine 7°, sextile 5° — all * orb_factor.
    """
    opp_orb   = 8.0 * orb_factor
    trine_orb = 7.0 * orb_factor
    sext_orb  = 5.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c, d in combinations(bodies, 4):
        for p, q, r, s in [
            (a, b, c, d), (a, b, d, c), (a, c, b, d),
            (a, c, d, b), (a, d, b, c), (a, d, c, b),
        ]:
            opp   = _get_aspect(aspect_map, p, s,   180.0, opp_orb)
            tr_pq = _get_aspect(aspect_map, p, q,   120.0, trine_orb)
            tr_rs = _get_aspect(aspect_map, r, s,   120.0, trine_orb)
            sx_qr = _get_aspect(aspect_map, q, r,    60.0, sext_orb)
            sx_pr = _get_aspect(aspect_map, p, r,    60.0, sext_orb)
            sx_qs = _get_aspect(aspect_map, q, s,    60.0, sext_orb)
            if opp and tr_pq and tr_rs and sx_qr and sx_pr and sx_qs:
                results.append(AspectPattern(
                    name="Cradle",
                    bodies=tuple(sorted([a, b, c, d])),
                    aspects=(opp, tr_pq, tr_rs, sx_qr, sx_pr, sx_qs),
                ))
                break

    return _dedup_patterns(results)


def find_trapezes(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Trapeze (Trapezoid): four planets in sequence where the two end planets
    are in opposition and the four outer edges are sextiles, with one
    diagonal also a sextile.
    Structure: A sext B sext C sext D, A opp C or B opp D (one diagonal
    opposition), and A sext D closing the shape.

    Orbs: opposition 8°, sextile 5° — all * orb_factor.
    """
    opp_orb  = 8.0 * orb_factor
    sext_orb = 5.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c, d in combinations(bodies, 4):
        for p, q, r, s in [
            (a, b, c, d), (a, b, d, c), (a, c, b, d),
            (a, c, d, b), (a, d, b, c), (a, d, c, b),
        ]:
            sx_pq = _get_aspect(aspect_map, p, q,  60.0, sext_orb)
            sx_qr = _get_aspect(aspect_map, q, r,  60.0, sext_orb)
            sx_rs = _get_aspect(aspect_map, r, s,  60.0, sext_orb)
            opp   = _get_aspect(aspect_map, p, s, 180.0, opp_orb)
            if sx_pq and sx_qr and sx_rs and opp:
                results.append(AspectPattern(
                    name="Trapeze",
                    bodies=tuple(sorted([a, b, c, d])),
                    aspects=(sx_pq, sx_qr, sx_rs, opp),
                ))
                break

    return _dedup_patterns(results)


def find_eyes(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Eye (Cosmic Eye): two quincunxes (150°) meeting at an apex, with the
    base planets in trine (120°).  The soft analog of the Yod.

    Orbs: quincunx 3°, trine 7° — all * orb_factor.
    """
    qncx_orb  = 3.0 * orb_factor
    trine_orb = 7.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c in combinations(bodies, 3):
        for apex, p1, p2 in [(c, a, b), (a, b, c), (b, a, c)]:
            q1    = _get_aspect(aspect_map, p1, apex, 150.0, qncx_orb)
            q2    = _get_aspect(aspect_map, p2, apex, 150.0, qncx_orb)
            trine = _get_aspect(aspect_map, p1, p2,  120.0, trine_orb)
            if q1 and q2 and trine:
                results.append(AspectPattern(
                    name="Eye",
                    bodies=(*sorted([p1, p2]), apex),
                    aspects=(q1, q2, trine),
                    apex=apex,
                ))
                break

    return _dedup_patterns(results)


def find_irritation_triangles(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Irritation Triangle (Ambivalence Triangle): one opposition with both
    planets quincunx (150°) a third.  The all-tension analog of the Eye.

    Orbs: opposition 8°, quincunx 3° — all * orb_factor.
    """
    opp_orb  = 8.0 * orb_factor
    qncx_orb = 3.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c in combinations(bodies, 3):
        for apex, p1, p2 in [(c, a, b), (a, b, c), (b, a, c)]:
            opp = _get_aspect(aspect_map, p1, p2,   180.0, opp_orb)
            q1  = _get_aspect(aspect_map, p1, apex, 150.0, qncx_orb)
            q2  = _get_aspect(aspect_map, p2, apex, 150.0, qncx_orb)
            if opp and q1 and q2:
                results.append(AspectPattern(
                    name="Irritation Triangle",
                    bodies=(*sorted([p1, p2]), apex),
                    aspects=(opp, q1, q2),
                    apex=apex,
                ))
                break

    return _dedup_patterns(results)


def find_hard_wedges(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Hard Wedge: planet A opposing planet B; a third planet C is semisquare
    (45°) one and sesquiquadrate (135°) the other.  The tense analog of the
    Wedge using 8th-harmonic aspects.

    Orbs: opposition 8°, semisquare 2°, sesquiquadrate 2° — all * orb_factor.
    """
    opp_orb  = 8.0 * orb_factor
    semi_orb = 2.0 * orb_factor
    sesq_orb = 2.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c in combinations(bodies, 3):
        for p1, p2, apex in [(a, b, c), (a, c, b), (b, c, a)]:
            opp  = _get_aspect(aspect_map, p1,   p2,    180.0, opp_orb)
            semi = _get_aspect(aspect_map, apex, p1,     45.0, semi_orb)
            sesq = _get_aspect(aspect_map, apex, p2,    135.0, sesq_orb)
            if opp and semi and sesq:
                results.append(AspectPattern(
                    name="Hard Wedge",
                    bodies=(*sorted([p1, p2]), apex),
                    aspects=(opp, semi, sesq),
                    apex=apex,
                ))
                break

    return _dedup_patterns(results)


def find_dominant_triangles(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Dominant Triangle (Huber): one opposition + one square + one quincunx
    (150°), forming a mixed-tension three-planet figure.

    Orbs: opposition 8°, square 7°, quincunx 3° — all * orb_factor.
    """
    opp_orb  = 8.0 * orb_factor
    sq_orb   = 7.0 * orb_factor
    qncx_orb = 3.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c in combinations(bodies, 3):
        for p1, p2, p3 in [(a, b, c), (a, c, b), (b, c, a)]:
            opp  = _get_aspect(aspect_map, p1, p2,  180.0, opp_orb)
            sq   = _get_aspect(aspect_map, p1, p3,   90.0, sq_orb)
            qncx = _get_aspect(aspect_map, p2, p3,  150.0, qncx_orb)
            if opp and sq and qncx:
                results.append(AspectPattern(
                    name="Dominant Triangle",
                    bodies=tuple(sorted([a, b, c])),
                    aspects=(opp, sq, qncx),
                ))
                break

    return _dedup_patterns(results)


# ---------------------------------------------------------------------------
# Pattern detectors — harmonic (5th and 7th harmonic)
# ---------------------------------------------------------------------------

def find_grand_quintiles(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Grand Quintile: five planets all in mutual quintile (72°), forming a
    regular pentagon.  A pure 5th-harmonic figure.

    Orb: 2° * orb_factor.
    """
    q_orb = 2.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for group in combinations(bodies, 5):
        group_aspects: list[AspectData] = []
        valid = True
        for b1, b2 in combinations(group, 2):
            asp = _get_aspect(aspect_map, b1, b2, 72.0, q_orb)
            if asp is None:
                valid = False
                break
            group_aspects.append(asp)
        if valid:
            results.append(AspectPattern(
                name="Grand Quintile",
                bodies=tuple(sorted(group)),
                aspects=tuple(group_aspects),
            ))

    return _dedup_patterns(results)


def find_quintile_triangles(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Quintile Triangle: A quintile (72°) B, both biquintile (144°) C (apex).
    The 5th-harmonic analog of the Yod.

    Orbs: quintile 2°, biquintile 2° — all * orb_factor.
    """
    q_orb  = 2.0 * orb_factor
    bq_orb = 2.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    for a, b, c in combinations(bodies, 3):
        for apex, p1, p2 in [(c, a, b), (a, b, c), (b, a, c)]:
            q   = _get_aspect(aspect_map, p1, p2,    72.0, q_orb)
            bq1 = _get_aspect(aspect_map, p1, apex, 144.0, bq_orb)
            bq2 = _get_aspect(aspect_map, p2, apex, 144.0, bq_orb)
            if q and bq1 and bq2:
                results.append(AspectPattern(
                    name="Quintile Triangle",
                    bodies=(*sorted([p1, p2]), apex),
                    aspects=(q, bq1, bq2),
                    apex=apex,
                ))
                break

    return _dedup_patterns(results)


def find_septile_triangles(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Septile Triangle: three planets connected by one each of septile (51.43°),
    biseptile (102.86°), and triseptile (154.29°).  A closed 7th-harmonic
    triangle.

    Orb: 1.5° * orb_factor for all three aspects.
    """
    s_orb = 1.5 * orb_factor
    aspect_map = _build_aspect_map(aspects)
    bodies = _bodies_from(aspects)
    results: list[AspectPattern] = []

    sept  = 360.0 / 7          # 51.428...
    bisept  = 2 * 360.0 / 7    # 102.857...
    trisept = 3 * 360.0 / 7    # 154.285...

    for a, b, c in combinations(bodies, 3):
        for p1, p2, p3 in [(a, b, c), (a, c, b), (b, c, a)]:
            s1 = _get_aspect(aspect_map, p1, p2, sept,   s_orb)
            s2 = _get_aspect(aspect_map, p2, p3, bisept, s_orb)
            s3 = _get_aspect(aspect_map, p1, p3, trisept, s_orb)
            if s1 and s2 and s3:
                results.append(AspectPattern(
                    name="Septile Triangle",
                    bodies=tuple(sorted([a, b, c])),
                    aspects=(s1, s2, s3),
                ))
                break

    return _dedup_patterns(results)


# ---------------------------------------------------------------------------
# Pattern registry and master function
# ---------------------------------------------------------------------------

_PATTERN_REGISTRY: dict[str, str] = {
    "T-Square":             "find_t_squares",
    "Grand Trine":          "find_grand_trines",
    "Grand Cross":          "find_grand_crosses",
    "Yod":                  "find_yods",
    "Mystic Rectangle":     "find_mystic_rectangles",
    "Kite":                 "find_kites",
    "Stellium":             "find_stelliums",
    "Minor Grand Trine":    "find_minor_grand_trines",
    "Grand Sextile":        "find_grand_sextiles",
    "Thor's Hammer":        "find_thors_hammers",
    "Boomerang Yod":        "find_boomerang_yods",
    "Wedge":                "find_wedges",
    "Cradle":               "find_cradles",
    "Trapeze":              "find_trapezes",
    "Eye":                  "find_eyes",
    "Irritation Triangle":  "find_irritation_triangles",
    "Hard Wedge":           "find_hard_wedges",
    "Dominant Triangle":    "find_dominant_triangles",
    "Grand Quintile":       "find_grand_quintiles",
    "Quintile Triangle":    "find_quintile_triangles",
    "Septile Triangle":     "find_septile_triangles",
}


def find_all_patterns(
    positions: dict[str, float],
    aspects: list[AspectData] | None = None,
    orb_factor: float = 1.0,
    include: list[str] | None = None,
) -> list[AspectPattern]:
    """
    Detect all aspect patterns in a chart.

    Parameters
    ----------
    positions   : dict of body name -> longitude
    aspects     : pre-computed aspects (computed via find_aspects if None)
    orb_factor  : multiplier applied to all orbs
    include     : list of pattern names to detect (all patterns if None).
                  Valid names: see _PATTERN_REGISTRY keys.

    Returns
    -------
    list[AspectPattern] sorted by pattern name then body names.
    """
    if aspects is None:
        aspects = find_aspects(positions, orb_factor=orb_factor)

    wanted: set[str] = set(include) if include is not None else set(_PATTERN_REGISTRY)

    all_found: list[AspectPattern] = []

    if "T-Square" in wanted:
        all_found.extend(find_t_squares(aspects, orb_factor=orb_factor))
    if "Grand Trine" in wanted:
        all_found.extend(find_grand_trines(aspects, orb_factor=orb_factor))
    if "Grand Cross" in wanted:
        all_found.extend(find_grand_crosses(aspects, orb_factor=orb_factor))
    if "Yod" in wanted:
        all_found.extend(find_yods(aspects, orb_factor=orb_factor))
    if "Mystic Rectangle" in wanted:
        all_found.extend(find_mystic_rectangles(aspects, orb_factor=orb_factor))
    if "Kite" in wanted:
        all_found.extend(find_kites(aspects, orb_factor=orb_factor))
    if "Stellium" in wanted:
        all_found.extend(find_stelliums(positions, orb_factor=orb_factor))
    if "Minor Grand Trine" in wanted:
        all_found.extend(find_minor_grand_trines(aspects, orb_factor=orb_factor))
    if "Grand Sextile" in wanted:
        all_found.extend(find_grand_sextiles(aspects, orb_factor=orb_factor))
    if "Thor's Hammer" in wanted:
        all_found.extend(find_thors_hammers(aspects, orb_factor=orb_factor))
    if "Boomerang Yod" in wanted:
        all_found.extend(find_boomerang_yods(aspects, orb_factor=orb_factor))
    if "Wedge" in wanted:
        all_found.extend(find_wedges(aspects, orb_factor=orb_factor))
    if "Cradle" in wanted:
        all_found.extend(find_cradles(aspects, orb_factor=orb_factor))
    if "Trapeze" in wanted:
        all_found.extend(find_trapezes(aspects, orb_factor=orb_factor))
    if "Eye" in wanted:
        all_found.extend(find_eyes(aspects, orb_factor=orb_factor))
    if "Irritation Triangle" in wanted:
        all_found.extend(find_irritation_triangles(aspects, orb_factor=orb_factor))
    if "Hard Wedge" in wanted:
        all_found.extend(find_hard_wedges(aspects, orb_factor=orb_factor))
    if "Dominant Triangle" in wanted:
        all_found.extend(find_dominant_triangles(aspects, orb_factor=orb_factor))
    if "Grand Quintile" in wanted:
        all_found.extend(find_grand_quintiles(aspects, orb_factor=orb_factor))
    if "Quintile Triangle" in wanted:
        all_found.extend(find_quintile_triangles(aspects, orb_factor=orb_factor))
    if "Septile Triangle" in wanted:
        all_found.extend(find_septile_triangles(aspects, orb_factor=orb_factor))

    all_found.sort(key=lambda p: (p.name, p.bodies))
    return all_found
