"""
Moira — Aspect Pattern Engine
==============================

Archetype: Engine

Purpose
-------
Governs detection of classical and modern multi-body aspect configurations
within a natal chart, including T-Squares, Grand Trines, Yods, Kites,
Stelliums, and nine additional pattern types.

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

Public surface
--------------
``AspectPattern``          — vessel for a detected multi-body configuration.
``find_t_squares``         — detect T-Square configurations.
``find_grand_trines``      — detect Grand Trine configurations.
``find_grand_crosses``     — detect Grand Cross configurations.
``find_yods``              — detect Yod (Finger of God) configurations.
``find_mystic_rectangles`` — detect Mystic Rectangle configurations.
``find_kites``             — detect Kite configurations.
``find_stelliums``         — detect Stellium clusters.
``find_minor_grand_trines``— detect Minor Grand Trine configurations.
``find_grand_sextiles``    — detect Grand Sextile (Star of David) configurations.
``find_thors_hammers``     — detect Thor's Hammer configurations.
``find_boomerang_yods``    — detect Boomerang Yod configurations.
``find_wedges``            — detect Wedge (Arrowhead) configurations.
``find_all_patterns``      — detect all registered patterns in one call.
"""


from dataclasses import dataclass, field
from itertools import combinations

from .aspects import AspectData, find_aspects
from .coordinates import angular_distance


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class AspectPattern:
    """
    RITE: The Configuration Vessel — a named multi-body celestial geometry.

    THEOREM: Holds the name, participating bodies, underlying aspects, and
    optional apex planet for a single detected multi-body aspect configuration.

    RITE OF PURPOSE:
        Serves the Aspect Pattern Engine as the canonical result vessel for
        all pattern detectors. Every pattern function returns a list of
        ``AspectPattern`` instances. Without this vessel, pattern results
        would have no uniform structure for downstream display, filtering,
        or further analysis.

    LAW OF OPERATION:
        Responsibilities:
            - Store the pattern name (e.g. "T-Square", "Grand Trine").
            - Store the list of body names involved in the pattern.
            - Store the list of ``AspectData`` instances forming the pattern.
            - Store the optional apex/focal planet name.
        Non-responsibilities:
            - Does not detect patterns (delegated to the finder functions).
            - Does not validate that the aspects are geometrically consistent.
            - Does not compute orbs or angular distances.
        Dependencies:
            - ``aspects`` field contains ``AspectData`` instances from ``moira.aspects``.
        Structural invariants:
            - ``bodies`` is always a non-empty list.
            - ``aspects`` may be empty for stelliums (position-based, not aspect-based).
            - ``apex`` is ``None`` for symmetric patterns (Grand Trine, Grand Cross, etc.).
        Succession stance: terminal — not designed for subclassing.

    Canon: None (No applicable canon)

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.patterns.AspectPattern",
        "risk": "medium",
        "api": {
            "public_methods": ["__repr__"],
            "public_attributes": ["name", "bodies", "aspects", "apex"]
        },
        "state": {
            "mutable": false,
            "fields": ["name", "bodies", "aspects", "apex"]
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
            "policy": "caller ensures valid aspect data before construction"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]
    """
    name:    str               # e.g. "T-Square", "Grand Trine"
    bodies:  list[str]         # planets involved (apex last for T-Square/Yod)
    aspects: list[AspectData]  # the underlying aspects forming the pattern
    apex:    str | None = None # focal/apex planet (T-Square, Yod, Kite)

    def __repr__(self) -> str:
        parts = " – ".join(self.bodies)
        apex_str = f" [apex: {self.apex}]" if self.apex else ""
        return f"{self.name}: {parts}{apex_str}"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _build_aspect_map(
    aspects: list[AspectData],
) -> dict[tuple[str, str], AspectData]:
    """Build a bidirectional lookup: (b1, b2) and (b2, b1) → AspectData."""
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
    """Return the aspect between b1 and b2 if it matches target_angle within orb, else None."""
    asp = aspect_map.get((b1, b2))
    if asp is not None and abs(asp.angle - target_angle) < 0.5 and asp.orb <= orb:
        return asp
    return None


def _dedup_patterns(patterns: list[AspectPattern]) -> list[AspectPattern]:
    """Remove duplicate patterns that involve the same set of bodies."""
    seen: set[frozenset[str]] = set()
    unique: list[AspectPattern] = []
    for p in patterns:
        key = frozenset(p.bodies)
        if key not in seen:
            seen.add(key)
            unique.append(p)
    return unique


# ---------------------------------------------------------------------------
# Pattern detectors
# ---------------------------------------------------------------------------

def find_t_squares(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Detect T-Squares: body_A opposition body_B, both square body_C (apex).
    Opposition orb: 10° * orb_factor.  Square orb: 8° * orb_factor.
    """
    opp_orb = 10.0 * orb_factor
    sq_orb  =  8.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)

    # Collect all bodies
    bodies = sorted({asp.body1 for asp in aspects} | {asp.body2 for asp in aspects})

    results: list[AspectPattern] = []
    for a, b, c in combinations(bodies, 3):
        for apex, p1, p2 in [(c, a, b), (a, b, c), (b, a, c)]:
            opp_asp = _get_aspect(aspect_map, p1, p2, 180.0, opp_orb)
            sq1_asp = _get_aspect(aspect_map, p1, apex, 90.0, sq_orb)
            sq2_asp = _get_aspect(aspect_map, p2, apex, 90.0, sq_orb)
            if opp_asp and sq1_asp and sq2_asp:
                involved = sorted([p1, p2]) + [apex]
                results.append(AspectPattern(
                    name="T-Square",
                    bodies=involved,
                    aspects=[opp_asp, sq1_asp, sq2_asp],
                    apex=apex,
                ))
                break  # found a valid arrangement for this triple

    return _dedup_patterns(results)


def find_grand_trines(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """Three bodies all in trine (120°) to each other.  Orb: 8° * orb_factor."""
    trine_orb  = 8.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)

    bodies = sorted({asp.body1 for asp in aspects} | {asp.body2 for asp in aspects})
    results: list[AspectPattern] = []

    for a, b, c in combinations(bodies, 3):
        t_ab = _get_aspect(aspect_map, a, b, 120.0, trine_orb)
        t_bc = _get_aspect(aspect_map, b, c, 120.0, trine_orb)
        t_ac = _get_aspect(aspect_map, a, c, 120.0, trine_orb)
        if t_ab and t_bc and t_ac:
            results.append(AspectPattern(
                name="Grand Trine",
                bodies=sorted([a, b, c]),
                aspects=[t_ab, t_bc, t_ac],
            ))

    return _dedup_patterns(results)


def find_grand_crosses(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """Two oppositions and four squares forming a Grand Cross.  Orb: 8° * orb_factor."""
    opp_orb = 8.0 * orb_factor
    sq_orb  = 8.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)

    bodies = sorted({asp.body1 for asp in aspects} | {asp.body2 for asp in aspects})
    results: list[AspectPattern] = []

    for a, b, c, d in combinations(bodies, 4):
        # A Grand Cross is: A opp C, B opp D, and A sq B, B sq C, C sq D, D sq A
        # Try all pairings for the two oppositions within the four bodies.
        # The three distinct ways to split four bodies into two pairs:
        pairs = [
            ((a, b), (c, d)),
            ((a, c), (b, d)),
            ((a, d), (b, c)),
        ]
        for (p, q), (r, s) in pairs:
            # p opp q and r opp s
            opp1 = _get_aspect(aspect_map, p, q, 180.0, opp_orb)
            opp2 = _get_aspect(aspect_map, r, s, 180.0, opp_orb)
            if not (opp1 and opp2):
                continue
            # squares: p-r, r-q, q-s, s-p
            sq_pr = _get_aspect(aspect_map, p, r, 90.0, sq_orb)
            sq_rq = _get_aspect(aspect_map, r, q, 90.0, sq_orb)
            sq_qs = _get_aspect(aspect_map, q, s, 90.0, sq_orb)
            sq_sp = _get_aspect(aspect_map, s, p, 90.0, sq_orb)
            if sq_pr and sq_rq and sq_qs and sq_sp:
                results.append(AspectPattern(
                    name="Grand Cross",
                    bodies=sorted([a, b, c, d]),
                    aspects=[opp1, opp2, sq_pr, sq_rq, sq_qs, sq_sp],
                ))
                break

    return _dedup_patterns(results)


def find_yods(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Yod (Finger of God): A sextile B, both quincunx (150°) C (apex).
    Sextile orb: 3° * orb_factor.  Quincunx orb: 3° * orb_factor.
    """
    sext_orb = 3.0 * orb_factor
    qncx_orb = 3.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)

    bodies = sorted({asp.body1 for asp in aspects} | {asp.body2 for asp in aspects})
    results: list[AspectPattern] = []

    for a, b, c in combinations(bodies, 3):
        for apex, p1, p2 in [(c, a, b), (a, b, c), (b, a, c)]:
            sext = _get_aspect(aspect_map, p1, p2, 60.0, sext_orb)
            q1   = _get_aspect(aspect_map, p1, apex, 150.0, qncx_orb)
            q2   = _get_aspect(aspect_map, p2, apex, 150.0, qncx_orb)
            if sext and q1 and q2:
                involved = sorted([p1, p2]) + [apex]
                results.append(AspectPattern(
                    name="Yod",
                    bodies=involved,
                    aspects=[sext, q1, q2],
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
    The four planets form a rectangle where adjacent sides alternate trine/sextile
    and the diagonals are oppositions.  Orb: 8° for trines, 5° for sextiles,
    8° for oppositions — all multiplied by orb_factor.
    """
    trine_orb = 8.0 * orb_factor
    sext_orb  = 5.0 * orb_factor
    opp_orb   = 8.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)

    bodies = sorted({asp.body1 for asp in aspects} | {asp.body2 for asp in aspects})
    results: list[AspectPattern] = []

    for a, b, c, d in combinations(bodies, 4):
        # Layout: A-trine-B-sext-C-trine-D-sext-A, diagonals A opp C, B opp D
        # Try all cyclic orderings of the four bodies.
        for ordering in [
            (a, b, c, d),
            (a, b, d, c),
            (a, c, b, d),
        ]:
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
                    bodies=sorted([a, b, c, d]),
                    aspects=[t_pq, t_rs, s_qr, s_sp, o_pr, o_qs],
                ))
                break

    return _dedup_patterns(results)


def find_kites(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Kite: Grand Trine (A, B, C) with a fourth planet D opposing one vertex (say C)
    and sextile the other two (A and B).  The opposing vertex C is the apex/focal point.
    Orb: 8° for trines, 5° for sextiles, 8° for opposition — multiplied by orb_factor.
    """
    trine_orb = 8.0 * orb_factor
    sext_orb  = 5.0 * orb_factor
    opp_orb   = 8.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)

    bodies = sorted({asp.body1 for asp in aspects} | {asp.body2 for asp in aspects})
    results: list[AspectPattern] = []

    for a, b, c, d in combinations(bodies, 4):
        # Try each body as the "kite tail" (D) and each vertex as the apex
        for tail, x, y, apex in [
            (d, a, b, c),
            (d, a, c, b),
            (d, b, c, a),
            (c, a, b, d),
            (c, a, d, b),
            (c, b, d, a),
            (b, a, c, d),
            (b, a, d, c),
            (b, c, d, a),
            (a, b, c, d),
            (a, b, d, c),
            (a, c, d, b),
        ]:
            t_xy    = _get_aspect(aspect_map, x, y,    120.0, trine_orb)
            t_xa    = _get_aspect(aspect_map, x, apex,  120.0, trine_orb)
            t_ya    = _get_aspect(aspect_map, y, apex,  120.0, trine_orb)
            opp     = _get_aspect(aspect_map, tail, apex, 180.0, opp_orb)
            sext_tx = _get_aspect(aspect_map, tail, x,   60.0, sext_orb)
            sext_ty = _get_aspect(aspect_map, tail, y,   60.0, sext_orb)
            if t_xy and t_xa and t_ya and opp and sext_tx and sext_ty:
                results.append(AspectPattern(
                    name="Kite",
                    bodies=sorted([a, b, c, d]),
                    aspects=[t_xy, t_xa, t_ya, opp, sext_tx, sext_ty],
                    apex=apex,
                ))
                break

    return _dedup_patterns(results)


def find_stelliums(
    positions: dict[str, float],
    min_bodies: int = 3,
    orb: float = 8.0,
) -> list[AspectPattern]:
    """
    Detect stelliums: 3+ bodies within `orb` degrees of each other.

    Uses positions dict directly (not an aspects list).
    A stellium is detected when at least *min_bodies* planets are all within
    *orb* degrees of the group centroid.  All maximal groups satisfying this
    constraint are returned.

    Parameters
    ----------
    positions  : dict of body name → tropical longitude
    min_bodies : minimum number of bodies required (default 3)
    orb        : maximum spread in degrees for the group (default 8.0)
    """
    body_list = sorted(positions.keys())
    results: list[AspectPattern] = []

    # Check every combination of min_bodies or more
    for size in range(min_bodies, len(body_list) + 1):
        for group in combinations(body_list, size):
            lons = [positions[b] for b in group]

            # Compute circular mean longitude for the group
            import math
            sin_sum = sum(math.sin(math.radians(lon)) for lon in lons)
            cos_sum = sum(math.cos(math.radians(lon)) for lon in lons)
            centroid = math.degrees(math.atan2(sin_sum, cos_sum)) % 360.0

            # Check all members are within orb of the centroid
            if all(angular_distance(lon, centroid) <= orb for lon in lons):
                # Avoid duplicates from sub-groups already captured by larger ones
                bodies_sorted = sorted(group)
                results.append(AspectPattern(
                    name="Stellium",
                    bodies=bodies_sorted,
                    aspects=[],   # stelliums are not aspect-based
                ))

    # Deduplicate and keep only maximal groups (no group is a subset of another)
    unique = _dedup_patterns(results)
    body_sets = [frozenset(p.bodies) for p in unique]
    maximal: list[AspectPattern] = []
    for i, p in enumerate(unique):
        key = body_sets[i]
        if not any(key < other for other in body_sets):
            maximal.append(p)

    return maximal


def find_minor_grand_trines(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Minor Grand Trine: A trine B, both sextile C.
    Trine orb: 8° * orb_factor.  Sextile orb: 3° * orb_factor.
    """
    trine_orb = 8.0 * orb_factor
    sext_orb  = 3.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)

    bodies = sorted({asp.body1 for asp in aspects} | {asp.body2 for asp in aspects})
    results: list[AspectPattern] = []

    for a, b, c in combinations(bodies, 3):
        for apex, p1, p2 in [(c, a, b), (a, b, c), (b, a, c)]:
            trine  = _get_aspect(aspect_map, p1, p2, 120.0, trine_orb)
            sext1  = _get_aspect(aspect_map, p1, apex,  60.0, sext_orb)
            sext2  = _get_aspect(aspect_map, p2, apex,  60.0, sext_orb)
            if trine and sext1 and sext2:
                results.append(AspectPattern(
                    name="Minor Grand Trine",
                    bodies=sorted([p1, p2, apex]),
                    aspects=[trine, sext1, sext2],
                ))
                break

    return _dedup_patterns(results)


# ---------------------------------------------------------------------------
# Grand Sextile (Star of David)
# ---------------------------------------------------------------------------

def find_grand_sextiles(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Grand Sextile (Star of David): six planets all in mutual sextile (60°),
    forming two interlocking Grand Trines.  Orb: 3° * orb_factor.
    """
    sext_orb = 3.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)

    bodies = sorted({asp.body1 for asp in aspects} | {asp.body2 for asp in aspects})
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
                bodies=sorted(group),
                aspects=group_aspects,
            ))

    return _dedup_patterns(results)


# ---------------------------------------------------------------------------
# Thor's Hammer (God's Fist)
# ---------------------------------------------------------------------------

def find_thors_hammers(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Thor's Hammer (God's Fist): two planets in square (90°), both
    sesquiquadrate (135°) an apex planet.
    Square orb: 5° * orb_factor.  Sesquiquadrate orb: 3° * orb_factor.
    """
    sq_orb   = 5.0 * orb_factor
    sesq_orb = 3.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)

    bodies = sorted({asp.body1 for asp in aspects} | {asp.body2 for asp in aspects})
    results: list[AspectPattern] = []

    for a, b, c in combinations(bodies, 3):
        for apex, p1, p2 in [(c, a, b), (a, b, c), (b, a, c)]:
            sq   = _get_aspect(aspect_map, p1, p2,    90.0, sq_orb)
            s1   = _get_aspect(aspect_map, p1, apex, 135.0, sesq_orb)
            s2   = _get_aspect(aspect_map, p2, apex, 135.0, sesq_orb)
            if sq and s1 and s2:
                results.append(AspectPattern(
                    name="Thor's Hammer",
                    bodies=sorted([p1, p2]) + [apex],
                    aspects=[sq, s1, s2],
                    apex=apex,
                ))
                break

    return _dedup_patterns(results)


# ---------------------------------------------------------------------------
# Boomerang Yod
# ---------------------------------------------------------------------------

def find_boomerang_yods(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Boomerang Yod: a standard Yod (A sextile B, both quincunx C apex) with
    a fourth planet D opposing the apex C and sextile/trine the base planets.
    Sextile orb: 3°, quincunx orb: 3°, opposition orb: 5° — all * orb_factor.
    """
    sext_orb = 3.0 * orb_factor
    qncx_orb = 3.0 * orb_factor
    opp_orb  = 5.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)

    bodies = sorted({asp.body1 for asp in aspects} | {asp.body2 for asp in aspects})
    results: list[AspectPattern] = []

    for a, b, c, d in combinations(bodies, 4):
        # Try each triple as the Yod base+apex, the remaining body as the boomerang
        for apex, p1, p2, boom in [
            (c, a, b, d), (d, a, b, c),
            (b, a, c, d), (d, a, c, b),
            (a, b, c, d), (d, b, c, a),
        ]:
            sext = _get_aspect(aspect_map, p1, p2,    60.0, sext_orb)
            q1   = _get_aspect(aspect_map, p1, apex, 150.0, qncx_orb)
            q2   = _get_aspect(aspect_map, p2, apex, 150.0, qncx_orb)
            opp  = _get_aspect(aspect_map, boom, apex, 180.0, opp_orb)
            if sext and q1 and q2 and opp:
                results.append(AspectPattern(
                    name="Boomerang Yod",
                    bodies=sorted([p1, p2, apex, boom]),
                    aspects=[sext, q1, q2, opp],
                    apex=apex,
                ))
                break

    return _dedup_patterns(results)


# ---------------------------------------------------------------------------
# Wedge (Arrowhead)
# ---------------------------------------------------------------------------

def find_wedges(
    aspects: list[AspectData],
    orb_factor: float = 1.0,
) -> list[AspectPattern]:
    """
    Wedge (Arrowhead): planet A opposing planet B; a third planet C is trine
    one and sextile the other (the reaction/release point).
    Opposition orb: 8°, trine/sextile orb: 5° — all * orb_factor.
    """
    opp_orb  = 8.0 * orb_factor
    trsx_orb = 5.0 * orb_factor
    aspect_map = _build_aspect_map(aspects)

    bodies = sorted({asp.body1 for asp in aspects} | {asp.body2 for asp in aspects})
    results: list[AspectPattern] = []

    for a, b, c in combinations(bodies, 3):
        for p1, p2, apex in [(a, b, c), (a, c, b), (b, c, a)]:
            opp  = _get_aspect(aspect_map, p1, p2,    180.0, opp_orb)
            tr   = _get_aspect(aspect_map, apex, p1,  120.0, trsx_orb)
            sx   = _get_aspect(aspect_map, apex, p2,   60.0, trsx_orb)
            if opp and tr and sx:
                results.append(AspectPattern(
                    name="Wedge",
                    bodies=sorted([p1, p2]) + [apex],
                    aspects=[opp, tr, sx],
                    apex=apex,
                ))
                break

    return _dedup_patterns(results)


# ---------------------------------------------------------------------------
# Master function
# ---------------------------------------------------------------------------

_PATTERN_REGISTRY: dict[str, str] = {
    "T-Square":          "find_t_squares",
    "Grand Trine":       "find_grand_trines",
    "Grand Cross":       "find_grand_crosses",
    "Yod":               "find_yods",
    "Mystic Rectangle":  "find_mystic_rectangles",
    "Kite":              "find_kites",
    "Stellium":          "find_stelliums",
    "Minor Grand Trine": "find_minor_grand_trines",
    "Grand Sextile":     "find_grand_sextiles",
    "Thor's Hammer":     "find_thors_hammers",
    "Boomerang Yod":     "find_boomerang_yods",
    "Wedge":             "find_wedges",
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
    positions   : dict of body name → longitude
    aspects     : pre-computed aspects (computed via find_aspects if None)
    orb_factor  : multiplier applied to all orbs
    include     : list of pattern names to detect (all patterns if None).
                  Valid names: "T-Square", "Grand Trine", "Grand Cross",
                  "Yod", "Mystic Rectangle", "Kite", "Stellium",
                  "Minor Grand Trine", "Grand Sextile", "Thor's Hammer",
                  "Boomerang Yod", "Wedge".

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
        all_found.extend(find_stelliums(positions))
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

    all_found.sort(key=lambda p: (p.name, p.bodies))
    return all_found
