"""
Moira — Chart Shape Engine
==========================

Archetype: Engine
Source authority: Marc Edmund Jones, *The Guide to Horoscope Interpretation*
                  (1941); *Essentials of Astrological Analysis* (1960).
                  Supplementary: Penny Leigh Sebring, *The Jones Patterns*.

Purpose
-------
Classifies the whole-chart distribution of planetary bodies into one of the
seven Jones temperament types.  Jones patterns describe the **topological
shape** of the entire planet set around the wheel.  They are categorically
distinct from aspect patterns (moira.patterns), which detect geometric
relationships between subsets of planets.  No aspect computation is performed
here; only the set of planetary longitudes is used.

Boundary declaration
--------------------
Owns    : chart-shape classification logic, gap analysis, cluster detection,
          leading/handle planet derivation, and the ChartShape result vessel.
Delegates: longitude normalisation to moira.coordinates.
Does not own: aspect detection, house assignment, body selection policy.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ARCHITECTURE FREEZE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The design below is frozen.  No threshold, detection-order change, or new
shape may be added without explicit revision of this docstring, the
VALIDATION CODEX section below, and the corresponding test class in
tests/unit/test_chart_shape.py.

Planet set doctrine
-------------------
The caller supplies the positions mapping.  This module does not filter, add,
or remove bodies.  Jones' original method uses the 10 traditional bodies (Sun
through Pluto); callers wishing strict Jones compliance should supply exactly
those 10.  The algorithm is correct for any non-empty mapping.

Gap measurement doctrine
------------------------
All gaps are measured as **forward (clockwise) arcs** between consecutive
planet longitudes after sorting.  The occupied arc is defined as
``360.0 - largest_gap``.  All thresholds follow Jones' primary-source
definitions exactly.  No orb tolerances are applied to gap boundaries.

Gap thresholds (frozen constants — do not adjust without source justification)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    _BUNDLE_MAX_ARC     = 120.0   occupied arc <= 120 → Bundle
    _BOWL_MAX_ARC       = 180.0   occupied arc <= 180 → Bowl candidate
    _BUCKET_MIN_HANDLE  =  60.0   handle > 60 from each rim (strict)
    _LOCOMOTIVE_MIN_GAP = 120.0   single largest gap >= 120 → Locomotive
    _SEESAW_MIN_GAP     =  60.0   two opposing gaps each >= 60 → Seesaw
    _SPLAY_MIN_GAP      =  30.0   inter-cluster gap >= 30; min 3 clusters

Detection order (Jones / Sabian school priority — frozen)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    1. Bundle     occupied_arc <= 120
    2. Bowl       occupied_arc <= 180, no handle in gap arc
    3. Bucket     9 planets arc <= 180, 1 planet in gap arc >= 60 from rims
    4. Locomotive largest_gap >= 120, occupied_arc > 180, exactly one such gap
    5. Seesaw     two qualifying gaps, each cluster >= 2 internally-tight planets
    6. Splay      >= 3 clusters by _SPLAY_MIN_GAP, each cluster >= 2 planets
    7. Splash     unconditional fallback

Rationale for ordering
~~~~~~~~~~~~~~~~~~~~~~
- Bundle before Bowl: a 120-degree arc satisfies both; Bundle is more
  specific and takes priority.
- Bowl before Bucket: Bucket's occupied arc always exceeds 180 degrees
  (removing the handle from a <= 180-degree bowl leaves a remainder that
  must span > 180 to put the handle in the opposite hemisphere).  Therefore
  Bowl and Bucket are mutually exclusive by arc arithmetic, but the Bowl
  detector's explicit handle-in-gap check is the authoritative guard.
- Bowl/Bucket before Locomotive: a chart with occupied_arc <= 180 also has
  largest_gap >= 180 >= 120, so Locomotive would fire without the
  ``occupied_arc <= _BOWL_MAX_ARC`` guard inside _detect_locomotive.
- Locomotive before Seesaw: the Locomotive guard ``len(qualifying_gaps) > 1``
  rejects any chart with two gaps >= 120, passing it down to Seesaw.
- Seesaw before Splay: a two-cluster chart whose intra-cluster gaps are all
  < _SPLAY_MIN_GAP is unambiguously Seesaw; _has_cluster_internal_split
  ensures this.  If a cluster has an internal gap >= 30, Seesaw rejects it
  and Splay catches it.
- Splay before Splash: Splay requires >= 3 clusters each with >= 2 planets.
  A chart with >= 3 singleton clusters (e.g. evenly-spaced planets) does not
  qualify for Splay and falls through to Splash.

Leading planet doctrine (frozen)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Bowl / Locomotive : ``gap_from`` — the last planet encountered going
        clockwise before entering the largest gap.
    Bucket            : the handle planet name.  For a tight conjunction
        pair handle (<= 8 degrees), a slash-joined string "name1/name2".
    Bundle / Seesaw / Splay / Splash : leading_planet is None.

Handle-in-gap doctrine (directional check, not distance-only)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
A planet qualifies as a Bucket handle only when all three conditions hold:
    1. in_gap  : its forward arc from the trailing rim < gap_size
                 (it lies within the empty arc, not the occupied arc).
    2. dist_from_trailing > _BUCKET_MIN_HANDLE  (strict greater-than)
    3. dist_to_leading    > _BUCKET_MIN_HANDLE  (strict greater-than)
Condition (1) is mandatory.  Distance alone (conditions 2–3) is insufficient
because interior bowl planets can be > 60 degrees from both rims while
sitting inside the occupied arc.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VALIDATION CODEX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Every rule below must be provable by an existing test in
tests/unit/test_chart_shape.py.  Adding a rule requires adding a test.
Removing a test requires removing or revising the corresponding rule.

RULE-01  Classification completeness
    classify_chart_shape always returns a ChartShape.  It never raises
    (unless positions is empty) and never returns None.
    Tests: TestEdgeCases::test_empty_positions_raises,
           TestEdgeCases::test_single_planet_returns_splash.

RULE-02  Seven-shape coverage
    Each of the seven ChartShapeType values is reachable by a synthetic
    10-planet positions dict whose membership is unambiguous.
    Tests: TestBundleDetection::test_bundle_detected,
           TestBowlDetection::test_bowl_detected,
           TestBucketDetection::test_bucket_detected,
           TestLocomotiveDetection::test_locomotive_detected,
           TestSeesawDetection::test_seesaw_detected,
           TestSplayDetection::test_splay_detected,
           TestSplashDetection::test_splash_detected.

RULE-03  arc + gap = 360
    For every result, occupied_arc + largest_gap == 360.0 within 1e-9.
    Enforced at construction by ChartShape.__post_init__.
    Tests: TestChartShapeVessel::test_arc_plus_gap_equals_360,
           TestChartShapeInvariants::test_arc_gap_sum_violation_raises.

RULE-04  Immutability
    ChartShape is a frozen dataclass.  Mutation attempts raise.
    Test: TestChartShapeVessel::test_frozen.

RULE-05  Cluster type contract
    clusters is a tuple of frozensets; never a list, set, or other type.
    Test: TestChartShapeVessel::test_clusters_is_tuple_of_frozensets.

RULE-06  Cluster non-emptiness
    clusters is never an empty tuple.
    Enforced by ChartShape.__post_init__.
    Test: TestChartShapeInvariants::test_empty_clusters_raises.

RULE-07  Body coverage
    For Seesaw, Splay: the union of all cluster frozensets equals the
    full body set supplied to classify_chart_shape.
    Tests: TestSeesawDetection::test_seesaw_all_bodies_covered,
           TestSplayDetection::test_splay_all_bodies_covered.

RULE-08  Leading planet — Bowl
    For Bowl, leading_planet is the body at gap_from (last body clockwise
    before the largest gap).  It must be non-None and present in clusters[0].
    Enforced by __post_init__ (non-None + membership).
    Tests: TestLeadingPlanetSemantics::test_bowl_leading_planet_is_last_before_gap,
           TestLeadingPlanetSemantics::test_bowl_leading_planet_in_clusters,
           TestChartShapeInvariants::test_bowl_without_leading_planet_raises,
           TestChartShapeInvariants::test_bowl_leading_planet_not_in_cluster_raises.

RULE-09  Leading planet — Locomotive
    For Locomotive, leading_planet is the body at gap_from.  Same contract
    as Bowl; both detectors use gap_from.
    Tests: TestLeadingPlanetSemantics::test_locomotive_leading_planet_is_last_before_gap,
           TestLeadingPlanetSemantics::test_locomotive_leading_planet_in_clusters.

RULE-10  Handle planet — Bucket
    For Bucket, handle_planet is set; clusters has >= 2 entries; the handle
    is in clusters[1], not clusters[0].
    Enforced by __post_init__ (handle_planet non-None + cluster count).
    Tests: TestBucketDetection::test_bucket_handle_is_pluto,
           TestBucketDetection::test_bucket_handle_in_second_cluster,
           TestChartShapeInvariants::test_bucket_without_handle_raises.

RULE-11  Handle-in-gap directional check
    A planet at exactly _BUCKET_MIN_HANDLE (60 degrees) from a rim is not
    a valid handle (strict greater-than).  An interior bowl planet with
    angular_distance > 60 from both rims does not qualify as a handle
    because it fails the in_gap directional check.
    Tests: TestBucketDetection::test_bucket_handle_exactly_60_from_rim_not_bucket,
           TestBucketDetection::test_bowl_interior_planet_does_not_trigger_bucket.

RULE-12  Locomotive / Seesaw disambiguation
    A chart with two or more gaps >= _LOCOMOTIVE_MIN_GAP (120 degrees) is
    not a Locomotive; it is passed to Seesaw.
    Test: TestLocomotiveDetection::test_locomotive_does_not_fire_on_seesaw.

RULE-13  Seesaw cluster integrity
    Each Seesaw cluster must contain >= 2 planets.  A single-planet cluster
    on one side is a Bucket, not a Seesaw (Penny Leigh doctrine).
    Seesaw clusters must be internally contiguous: no intra-cluster gap
    >= _SPLAY_MIN_GAP; such a chart is Splay, not Seesaw.
    Tests: TestSeesawDetection::test_seesaw_clusters_each_have_multiple_planets.

RULE-14  Splay cluster integrity
    Each Splay cluster must contain >= 2 planets.  A chart whose 30-degree
    split produces singleton clusters (e.g. evenly-spaced planets) is Splash.
    Tests: TestSplayDetection::test_splay_each_cluster_has_at_least_two_planets,
           TestSplashDetection::test_splash_detected.

RULE-15  Splash is unconditional fallback
    Splash carries no threshold enforcement.  If all preceding detectors
    reject, Splash is returned regardless of gap magnitude or body count.
    No _SPLASH_MAX_GAP constant exists; the threshold is not enforced.
    Tests: TestSplashDetection::test_splash_detected.

RULE-16  Longitude normalisation
    Longitudes outside [0, 360) are normalised before any computation.
    A positions dict with all longitudes shifted by +360 produces the same
    shape as the original.
    Test: TestEdgeCases::test_longitudes_outside_0_360_are_normalised.

RULE-17  Bundle boundary inclusivity
    occupied_arc == 120.0 qualifies as Bundle (<=, not <).
    Test: TestEdgeCases::test_bundle_at_exact_120_boundary.

RULE-18  Public surface sealed
    moira.chart_shape.__all__ exposes exactly
    {ChartShapeType, ChartShape, classify_chart_shape}.
    No internal name (_detect_*, _compute_*, threshold constants) appears
    in __all__.  These three names are intentionally NOT re-exported into
    moira.__all__; moira.__init__ is kept thin and callers access this
    module via ``from moira.chart_shape import ...`` or through
    ``moira.facade``.
    Tests: TestPublicAPIResolution::test_all_names_on_moira_package,
           TestPublicAPIResolution::test_module_all_exists_and_matches,
           TestPublicAPIResolution::test_internals_absent_from_all.

RULE-19  moira.__all__ exclusion is enforced
    ChartShapeType, ChartShape, and classify_chart_shape must not appear
    in moira.__all__.  The top-level package namespace is intentionally
    kept thin; this module is accessible as a submodule import.
    Test: TestPublicAPIResolution::test_all_names_on_moira_package.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Public surface
--------------
``ChartShapeType``       — enum of the seven Jones pattern names.
``ChartShape``           — frozen result vessel.
``classify_chart_shape`` — single entry point; positions -> ChartShape.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from .coordinates import normalize_degrees, angular_distance


__all__ = [
    "ChartShapeType",
    "ChartShape",
    "classify_chart_shape",
]


# ---------------------------------------------------------------------------
# Gap thresholds (Jones primary-source definitions, no orb buffers)
# ---------------------------------------------------------------------------

_BUNDLE_MAX_ARC      = 120.0   # all planets within this arc
_LOCOMOTIVE_MIN_GAP  = 120.0   # single largest gap must be at least this
_BOWL_MAX_ARC        = 180.0   # all planets within this arc
_BUCKET_MIN_HANDLE   =  60.0   # handle must be >= this from each rim planet
_SEESAW_MIN_GAP      =  60.0   # each of the two opposing gaps must be >= this
_SPLAY_MIN_GAP       =  30.0   # gap between each adjacent cluster >= this


# ---------------------------------------------------------------------------
# ChartShapeType enum
# ---------------------------------------------------------------------------

class ChartShapeType(str, Enum):
    """
    The seven Jones whole-chart temperament types.

    BUNDLE
        All planets within a 120-degree arc.  The most concentrated
        pattern; intense specialisation and focus.

    BOWL
        All planets within a 180-degree arc (one hemisphere).  The
        occupied half drives the life; the empty half is the horizon
        of unfulfilled potential.

    BUCKET
        Bowl with one planet (the handle) isolated in the opposing
        hemisphere by at least 60 degrees from each rim planet.  The
        handle is the dominant focal channel for the entire chart.

    LOCOMOTIVE
        All planets within a 240-degree arc, leaving one continuous
        empty arc of at least 120 degrees.  The leading planet (at the
        clockwise edge of the occupied arc) drives the life forward.

    SEESAW
        Two distinct planet clusters on opposing sides of the wheel,
        separated by two opposing empty arcs each at least 60 degrees
        wide.  Characteristic oppositions between the clusters; life
        lived between two poles.

    SPLAY
        Three or more irregular clusters spread across the wheel, each
        separated by a gap of at least 30 degrees.  Does not conform to
        the neat bipolarity of the Bowl or Seesaw.

    SPLASH
        Unconditional fallback when no other pattern applies.  Planets are
        broadly distributed around the wheel without forming a recognisable
        Jones shape.  Wide interests; diffuse energy.
    """
    BUNDLE     = "Bundle"
    BOWL       = "Bowl"
    BUCKET     = "Bucket"
    LOCOMOTIVE = "Locomotive"
    SEESAW     = "Seesaw"
    SPLAY      = "Splay"
    SPLASH     = "Splash"


# ---------------------------------------------------------------------------
# ChartShape result vessel
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ChartShape:
    """
    Whole-chart Jones temperament classification result.

    Fields
    ------
    shape
        The detected ChartShapeType.

    occupied_arc
        The arc in degrees spanned by all planets (360 minus the largest
        gap).  Always in [0, 360].

    largest_gap
        The largest continuous empty arc in degrees between any two
        consecutive planets (travelling clockwise).  Always in [0, 360].

    leading_planet
        For Bowl and Locomotive: the planet at the clockwise-leading edge
        of the occupied arc — the last planet encountered going clockwise
        before entering the largest gap.
        For Bucket: the handle planet name (or "name1/name2" for a
        tight conjunction pair handle).
        None for all other shapes.

    handle_planet
        For Bucket: the name of the singleton handle planet.
        None for all other shapes.

    clusters
        Tuple of frozensets, each containing the body names in one
        detected cluster.  The clusters are ordered clockwise starting
        from the cluster immediately after the largest gap.
        For Bundle, Bowl, Bucket, Locomotive: one cluster (plus the
        handle as a separate singleton for Bucket).
        For Seesaw: two clusters.
        For Splay: three or more clusters.
        For Splash: one cluster containing all bodies (no sub-grouping).

    Structural invariants
    ---------------------
    - ``occupied_arc + largest_gap == 360.0`` (within floating-point precision).
    - For Bucket: ``handle_planet`` is set and is not in ``clusters[0]``.
    - For Bowl / Locomotive: ``leading_planet`` is set and is in ``clusters[0]``.
    - ``clusters`` is never empty.
    - The vessel is immutable.
    """
    shape:           ChartShapeType
    occupied_arc:    float
    largest_gap:     float
    leading_planet:  str | None
    handle_planet:   str | None
    clusters:        tuple[frozenset[str], ...]

    def __post_init__(self) -> None:
        if abs(self.occupied_arc + self.largest_gap - 360.0) > 1e-9:
            raise ValueError(
                f"ChartShape invariant violated: "
                f"occupied_arc ({self.occupied_arc}) + largest_gap ({self.largest_gap}) "
                f"!= 360.0"
            )
        if not self.clusters:
            raise ValueError("ChartShape invariant violated: clusters must not be empty")
        if self.shape in (ChartShapeType.BOWL, ChartShapeType.LOCOMOTIVE):
            if self.leading_planet is None:
                raise ValueError(
                    f"ChartShape invariant violated: "
                    f"{self.shape.value} requires leading_planet to be set"
                )
            if self.leading_planet not in self.clusters[0]:
                raise ValueError(
                    f"ChartShape invariant violated: "
                    f"leading_planet {self.leading_planet!r} not in clusters[0]"
                )
        if self.shape is ChartShapeType.BUCKET:
            if self.handle_planet is None:
                raise ValueError(
                    "ChartShape invariant violated: Bucket requires handle_planet to be set"
                )
            if len(self.clusters) < 2:
                raise ValueError(
                    "ChartShape invariant violated: Bucket requires at least two clusters"
                )

    def __repr__(self) -> str:
        lp = f", leading={self.leading_planet!r}" if self.leading_planet else ""
        hp = f", handle={self.handle_planet!r}"   if self.handle_planet  else ""
        return (
            f"ChartShape({self.shape.value}, "
            f"arc={self.occupied_arc:.1f}, "
            f"gap={self.largest_gap:.1f}"
            f"{lp}{hp})"
        )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _sorted_longitudes(positions: dict[str, float]) -> list[tuple[float, str]]:
    """
    Return (longitude, name) pairs sorted by normalised longitude ascending
    (i.e., clockwise from 0 degrees).
    """
    return sorted(
        ((normalize_degrees(lon), name) for name, lon in positions.items()),
        key=lambda x: x[0],
    )


def _compute_gaps(sorted_lons: list[tuple[float, str]]) -> list[tuple[float, int, int]]:
    """
    Compute the forward (clockwise) arc from each planet to the next.

    Returns a list of (gap_degrees, from_index, to_index) tuples, including
    the wrap-around gap from the last planet back to the first.  Indexed
    into sorted_lons.
    """
    n = len(sorted_lons)
    gaps: list[tuple[float, int, int]] = []
    for i in range(n):
        j = (i + 1) % n
        gap = (sorted_lons[j][0] - sorted_lons[i][0]) % 360.0
        gaps.append((gap, i, j))
    return gaps


def _split_into_clusters(
    sorted_lons: list[tuple[float, str]],
    min_gap: float,
) -> list[frozenset[str]]:
    """
    Partition sorted_lons into clusters separated by gaps >= min_gap.
    Returns clusters ordered clockwise, starting immediately after the
    first gap >= min_gap found going clockwise from longitude 0.
    """
    n = len(sorted_lons)
    gaps = _compute_gaps(sorted_lons)

    # Find split points: indices where the gap to the next planet >= min_gap
    split_after: list[int] = [i for gap, i, j in gaps if gap >= min_gap]

    if not split_after:
        return [frozenset(name for _, name in sorted_lons)]

    clusters: list[frozenset[str]] = []
    # Start cluster immediately after the first split point (clockwise order)
    start = (split_after[0] + 1) % n
    split_set = set(split_after)
    current: list[str] = []

    for step in range(n):
        idx = (start + step) % n
        current.append(sorted_lons[idx][1])
        if idx in split_set:
            clusters.append(frozenset(current))
            current = []

    if current:
        clusters.append(frozenset(current))

    return clusters


# ---------------------------------------------------------------------------
# Shape detectors (internal, called in priority order)
# ---------------------------------------------------------------------------

def _detect_bundle(
    sorted_lons: list[tuple[float, str]],
    largest_gap: float,
    occupied_arc: float,
) -> ChartShape | None:
    if occupied_arc > _BUNDLE_MAX_ARC:
        return None
    all_bodies = frozenset(name for _, name in sorted_lons)
    return ChartShape(
        shape=ChartShapeType.BUNDLE,
        occupied_arc=occupied_arc,
        largest_gap=largest_gap,
        leading_planet=None,
        handle_planet=None,
        clusters=(all_bodies,),
    )


def _detect_bowl(
    sorted_lons: list[tuple[float, str]],
    gaps: list[tuple[float, int, int]],
    largest_gap: float,
    occupied_arc: float,
) -> ChartShape | None:
    """
    Bowl: all planets within <= 180 degrees, no planet isolated >= 60 from
    both rim planets (that would be a Bucket).
    """
    if occupied_arc > _BOWL_MAX_ARC:
        return None

    gap_val, gap_from, gap_to = max(gaps, key=lambda g: g[0])
    leading_rim      = sorted_lons[gap_from][1]
    trailing_rim_lon = sorted_lons[gap_from][0]
    leading_rim_lon  = sorted_lons[gap_to][0]

    gap_size = (leading_rim_lon - trailing_rim_lon) % 360.0
    for lon, name in sorted_lons:
        forward_from_trailing = (lon - trailing_rim_lon) % 360.0
        in_gap = forward_from_trailing < gap_size
        dist_from_trailing = angular_distance(lon, trailing_rim_lon)
        dist_to_leading    = angular_distance(lon, leading_rim_lon)
        if in_gap and dist_from_trailing > _BUCKET_MIN_HANDLE and dist_to_leading > _BUCKET_MIN_HANDLE:
            return None  # handle present -> Bucket, not Bowl

    all_bodies = frozenset(name for _, name in sorted_lons)
    return ChartShape(
        shape=ChartShapeType.BOWL,
        occupied_arc=occupied_arc,
        largest_gap=largest_gap,
        leading_planet=leading_rim,
        handle_planet=None,
        clusters=(all_bodies,),
    )


def _detect_bucket(
    sorted_lons: list[tuple[float, str]],
) -> ChartShape | None:
    """
    Bucket: exactly one planet (or a tight conjunction pair <= 8 degrees)
    isolated by >= 60 degrees from each rim planet, where the remaining
    planets form a contiguous arc of <= 180 degrees.
    """
    n = len(sorted_lons)

    for h_idx in range(n):
        handle_lon  = sorted_lons[h_idx][0]
        handle_name = sorted_lons[h_idx][1]

        remaining = [sorted_lons[i] for i in range(n) if i != h_idx]
        if not remaining:
            continue

        rem_gaps = _compute_gaps(remaining)
        rem_largest_gap = max(g for g, _, _ in rem_gaps)
        rem_arc = 360.0 - rem_largest_gap

        if rem_arc > _BOWL_MAX_ARC:
            continue

        _, bowl_gap_from, bowl_gap_to = max(rem_gaps, key=lambda g: g[0])
        trailing_rim_lon = remaining[bowl_gap_from][0]
        leading_rim_lon  = remaining[bowl_gap_to][0]

        gap_size               = (leading_rim_lon - trailing_rim_lon) % 360.0
        forward_from_trailing  = (handle_lon - trailing_rim_lon) % 360.0
        in_gap                 = forward_from_trailing < gap_size
        dist_from_trailing     = angular_distance(handle_lon, trailing_rim_lon)
        dist_to_leading        = angular_distance(handle_lon, leading_rim_lon)

        if in_gap and dist_from_trailing > _BUCKET_MIN_HANDLE and dist_to_leading > _BUCKET_MIN_HANDLE:
            bowl_bodies = frozenset(name for _, name in remaining)
            return ChartShape(
                shape=ChartShapeType.BUCKET,
                occupied_arc=rem_arc,
                largest_gap=rem_largest_gap,
                leading_planet=handle_name,
                handle_planet=handle_name,
                clusters=(bowl_bodies, frozenset({handle_name})),
            )

    for h1 in range(n):
        for h2 in range(h1 + 1, n):
            lon1, name1 = sorted_lons[h1]
            lon2, name2 = sorted_lons[h2]
            pair_gap = min((lon2 - lon1) % 360.0, (lon1 - lon2) % 360.0)
            if pair_gap > 8.0:
                continue

            remaining = [sorted_lons[i] for i in range(n) if i not in (h1, h2)]
            if not remaining:
                continue

            rem_gaps = _compute_gaps(remaining)
            rem_largest_gap = max(g for g, _, _ in rem_gaps)
            rem_arc = 360.0 - rem_largest_gap

            if rem_arc > _BOWL_MAX_ARC:
                continue

            _, bowl_gap_from, bowl_gap_to = max(rem_gaps, key=lambda g: g[0])
            trailing_rim_lon = remaining[bowl_gap_from][0]
            leading_rim_lon  = remaining[bowl_gap_to][0]

            gap_size = (leading_rim_lon - trailing_rim_lon) % 360.0
            valid = True
            for hlon in (lon1, lon2):
                forward = (hlon - trailing_rim_lon) % 360.0
                if not (
                    forward < gap_size
                    and angular_distance(hlon, trailing_rim_lon) > _BUCKET_MIN_HANDLE
                    and angular_distance(hlon, leading_rim_lon)  > _BUCKET_MIN_HANDLE
                ):
                    valid = False
                    break

            if valid:
                bowl_bodies  = frozenset(name for _, name in remaining)
                handle_set   = frozenset({name1, name2})
                handle_label = f"{name1}/{name2}"
                return ChartShape(
                    shape=ChartShapeType.BUCKET,
                    occupied_arc=rem_arc,
                    largest_gap=rem_largest_gap,
                    leading_planet=handle_label,
                    handle_planet=handle_label,
                    clusters=(bowl_bodies, handle_set),
                )

    return None


def _detect_locomotive(
    sorted_lons: list[tuple[float, str]],
    gaps: list[tuple[float, int, int]],
    largest_gap: float,
    occupied_arc: float,
) -> ChartShape | None:
    if largest_gap < _LOCOMOTIVE_MIN_GAP:
        return None
    if occupied_arc <= _BUNDLE_MAX_ARC:
        return None  # Bundle takes priority
    if occupied_arc <= _BOWL_MAX_ARC:
        return None  # Bowl takes priority
    # A Seesaw has two large opposing gaps; Locomotive has exactly one.
    # If more than one gap qualifies, this is not a Locomotive.
    qualifying_gaps = [g for g, _, _ in gaps if g >= _LOCOMOTIVE_MIN_GAP]
    if len(qualifying_gaps) > 1:
        return None

    # Leading planet: immediately before (clockwise) the largest gap.
    gap_val, gap_from, gap_to = max(gaps, key=lambda g: g[0])
    leading = sorted_lons[gap_from][1]

    all_bodies = frozenset(name for _, name in sorted_lons)
    return ChartShape(
        shape=ChartShapeType.LOCOMOTIVE,
        occupied_arc=occupied_arc,
        largest_gap=largest_gap,
        leading_planet=leading,
        handle_planet=None,
        clusters=(all_bodies,),
    )


def _has_cluster_internal_split(
    cluster_names: list[str],
    sorted_lons: list[tuple[float, str]],
) -> bool:
    """
    Return True if any consecutive pair within cluster_names (in sorted
    longitude order) is separated by a forward arc >= _SPLAY_MIN_GAP.
    Used by _detect_seesaw to reject charts whose apparent two-gap split
    conceals a third intra-cluster gap (those are Splay, not Seesaw).
    """
    name_set = set(cluster_names)
    idxs = [i for i, (_, nm) in enumerate(sorted_lons) if nm in name_set]
    for k in range(len(idxs) - 1):
        fwd = (sorted_lons[idxs[k + 1]][0] - sorted_lons[idxs[k]][0]) % 360.0
        if fwd >= _SPLAY_MIN_GAP:
            return True
    return False


def _detect_seesaw(
    sorted_lons: list[tuple[float, str]],
    gaps: list[tuple[float, int, int]],
    largest_gap: float,
    occupied_arc: float,
) -> ChartShape | None:
    # Two opposing gaps each >= _SEESAW_MIN_GAP (60 degrees).
    qualifying: list[tuple[float, int, int]] = [
        (g, i, j) for g, i, j in gaps if g >= _SEESAW_MIN_GAP
    ]
    if len(qualifying) < 2:
        return None

    n = len(sorted_lons)

    # Check each pair of qualifying gaps.  A Seesaw requires exactly two
    # clusters, each with >= 2 internally-contiguous planets.
    for idx_a in range(len(qualifying)):
        for idx_b in range(idx_a + 1, len(qualifying)):
            ga, ia, ja = qualifying[idx_a]
            gb, ib, jb = qualifying[idx_b]

            # Build the two clusters by walking clockwise between gap endpoints.
            # ja != jb is guaranteed: _compute_gaps assigns each j uniquely.
            c1: list[str] = []
            c2: list[str] = []

            step = ja
            while step != jb:
                c1.append(sorted_lons[step][1])
                step = (step + 1) % n

            while step != ja:
                c2.append(sorted_lons[step][1])
                step = (step + 1) % n

            if len(c1) < 2 or len(c2) < 2:
                continue

            if _has_cluster_internal_split(c1, sorted_lons):
                continue
            if _has_cluster_internal_split(c2, sorted_lons):
                continue

            # Use the pre-computed authoritative largest_gap / occupied_arc
            # values rather than max(ga, gb), which may differ when a third
            # gap dominates.
            return ChartShape(
                shape=ChartShapeType.SEESAW,
                occupied_arc=occupied_arc,
                largest_gap=largest_gap,
                leading_planet=None,
                handle_planet=None,
                clusters=(frozenset(c1), frozenset(c2)),
            )

    return None


def _detect_splay(
    sorted_lons: list[tuple[float, str]],
    largest_gap: float,
) -> ChartShape | None:
    # Three or more clusters each separated by >= _SPLAY_MIN_GAP (30 degrees).
    # Each cluster must contain >= 2 planets; atomised single-planet "clusters"
    # indicate an evenly-spread Splash, not an irregular Splay.
    clusters = _split_into_clusters(sorted_lons, _SPLAY_MIN_GAP)
    if len(clusters) < 3:
        return None
    if any(len(c) < 2 for c in clusters):
        return None

    occupied_arc = 360.0 - largest_gap
    return ChartShape(
        shape=ChartShapeType.SPLAY,
        occupied_arc=occupied_arc,
        largest_gap=largest_gap,
        leading_planet=None,
        handle_planet=None,
        clusters=tuple(clusters),
    )


def _detect_splash(
    sorted_lons: list[tuple[float, str]],
    gaps: list[tuple[float, int, int]],
    largest_gap: float,
) -> ChartShape:
    # Fallback: at least 7 distinct bodies, no gap > 60 degrees.
    # If neither condition is met, still return Splash (caller's choice of
    # planet set may be smaller than Jones' canonical 10).
    occupied_arc = 360.0 - largest_gap
    all_bodies = frozenset(name for _, name in sorted_lons)
    return ChartShape(
        shape=ChartShapeType.SPLASH,
        occupied_arc=occupied_arc,
        largest_gap=largest_gap,
        leading_planet=None,
        handle_planet=None,
        clusters=(all_bodies,),
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def classify_chart_shape(positions: Mapping[str, float]) -> ChartShape:
    """
    Classify the whole-chart Jones temperament type for the given planet set.

    Parameters
    ----------
    positions : dict mapping body name to ecliptic longitude (degrees).
                Jones' original method uses the 10 traditional bodies
                (Sun through Pluto).  Any non-empty dict is accepted.

    Returns
    -------
    ChartShape — the classified pattern and its derived metrics.

    Detection order
    ---------------
    1. Bundle     (occupied arc <= 120)
    2. Bowl       (occupied arc <= 180, no isolated handle)
    3. Bucket     (9 planets in contiguous arc <= 180 + 1 isolated handle)
    4. Locomotive (largest gap >= 120, occupied arc > 180, not a Bucket)
    5. Seesaw     (two opposing gaps each >= 60)
    6. Splay      (three or more clusters, each gap >= 30)
    7. Splash     (fallback)

    Raises
    ------
    ValueError if positions is empty.
    """
    if not positions:
        raise ValueError("classify_chart_shape: positions must not be empty")

    sorted_lons = _sorted_longitudes(positions)

    if len(sorted_lons) == 1:
        lon, name = sorted_lons[0]
        return ChartShape(
            shape=ChartShapeType.SPLASH,
            occupied_arc=0.0,
            largest_gap=360.0,
            leading_planet=None,
            handle_planet=None,
            clusters=(frozenset({name}),),
        )

    gaps          = _compute_gaps(sorted_lons)
    largest_gap   = max(g for g, _, _ in gaps)
    occupied_arc  = 360.0 - largest_gap

    result = _detect_bundle(sorted_lons, largest_gap, occupied_arc)
    if result:
        return result

    result = _detect_bowl(sorted_lons, gaps, largest_gap, occupied_arc)
    if result:
        return result

    result = _detect_bucket(sorted_lons)
    if result:
        return result

    result = _detect_locomotive(sorted_lons, gaps, largest_gap, occupied_arc)
    if result:
        return result

    result = _detect_seesaw(sorted_lons, gaps, largest_gap, occupied_arc)
    if result:
        return result

    result = _detect_splay(sorted_lons, largest_gap)
    if result:
        return result

    return _detect_splash(sorted_lons, gaps, largest_gap)
