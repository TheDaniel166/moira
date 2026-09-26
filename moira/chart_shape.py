"""
Moira — Chart Shape Engine
==========================

Archetype: Engine
Primary source authority: Marc Edmund Jones, *Essentials of Astrological
                          Analysis* (1960), chapter 1 (aspect orbs) and
                          chapter 2 (Temperament Type), including the 2025
                          Sabian Publishing Society authorized online text:
                          https://sabianpublishingsociety.org/books/essentials_2.html

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
Owns    : chart-shape classification logic, Jones body-set eligibility, gap
          analysis, cluster detection, leading/handle planet derivation, and
          the ChartShape result vessel.
Delegates: canonical body names to moira.constants and longitude
           normalisation to moira.coordinates.
Does not own: general aspect detection or house assignment.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ARCHITECTURE FREEZE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The design below is frozen.  No threshold, detection-order change, or new
shape may be added without explicit revision of this docstring, the
VALIDATION CODEX section below, and the corresponding test class in
tests/unit/test_chart_shape.py.

Planet set doctrine
-------------------
Jones explicitly defines the technique over the ten planets from Sun through
Pluto.  The public function therefore requires exactly those ten bodies and
rejects nodes, angles, asteroids, omitted planets, or extra bodies.

Gap measurement doctrine
------------------------
All gaps are measured as **forward arcs** between consecutive planet
longitudes after sorting.  The occupied arc is ``360.0 - largest_gap``.

Jones does not present the seven types as rigid numerical bins.  He says that
many charts plausibly fit more than one type and that classification is a
matter of continual approximation.  Moira therefore distinguishes source
doctrine from the deterministic rules needed by an engine:

- Bundle and Bowl use Jones's explicit trine (120 degrees) and hemisphere
  (180 degrees) spans.
- A group-separating empty space is either bounded by a sextile within Jones's
  own major-aspect orb, or exceeds 70 degrees, following his explicit Seesaw
  rule.  The same partition rule operationalizes the "distinct groups" of
  Splay and the wheel-like distribution of Splash.
- Jones's aspect orbs are 17 degrees when the Sun participates, 12 degrees
  30 minutes when the Moon but not the Sun participates, and 10 degrees for
  all other planet pairs.
- The residual Splash choice is an engine tie-break for borderline cases, not
  a claim that Jones supplied a universal fallback threshold.

Detection order (Jones / Sabian school priority — frozen)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    1. Bundle     occupied_arc <= 120
    2. Bowl       occupied_arc <= 180, no handle in gap arc
    3. Bucket     one planet opposite a nine-planet Bowl core
    4. Seesaw     exactly two Jones-separated groups, each with 2+ planets
    5. Splay      exactly three Jones-separated groups; singleton reins allowed
    6. Locomotive one Jones-separated gap delimited by a functioning trine
    7. Splash     wheel-like residual / documented borderline tie-break

Rationale for ordering
~~~~~~~~~~~~~~~~~~~~~~
- Bundle before Bowl: a 120-degree arc satisfies both; Bundle is more
  specific and takes priority.
- Bowl before Bucket: _detect_bowl claims every chart whose full-chart
  occupied arc is <= 180 via its arc guard, so only charts whose full-chart
  occupied arc exceeds 180 reach _detect_bucket.  A Bucket's handle lies in
  the wide empty arc outside the bowl core; removing it leaves a Bowl-like
  core whose arc is <= 180.  _detect_bucket therefore reports the bowl-core
  arc and gap (handle removed) -- a distinct measurement from the full-chart
  occupied arc that separated the chart from Bowl.
- Bowl/Bucket before Locomotive: a chart with occupied_arc <= 180 also has
  largest_gap >= 180 >= 120, so Locomotive would fire without the
  ``occupied_arc <= _BOWL_MAX_ARC`` guard inside _detect_locomotive.
- Seesaw and Splay before Locomotive: two- and three-group structures must not
  be swallowed merely because one of their empty spaces is trine-sized.
- Splay permits Jones's explicit one-planet reins grouping; it is not rejected
  merely because one of its three groups is a singleton.
- Splash remains the required seventh result for the source's acknowledged
  borderline cases after the defined one-, two-, and three-group forms decline.

Leading planet doctrine (frozen)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    Bowl / Locomotive : ``gap_from`` — the last planet encountered going
        clockwise before entering the largest gap.
    Bucket            : the single handle planet name.
    Bundle / Seesaw / Splay / Splash : leading_planet is None.

Bucket doctrine
~~~~~~~~~~~~~~~
Jones defines a one-nine division: removing the handle leaves a Bowl, and the
handle must lie in the opposite zodiacal hemisphere.  He supplies no 60-degree
rim-distance test and does not define a conjunction pair as a Bucket handle.
When multiple removals could produce a Bowl, the candidate closest to the
ideal position opposite the Bowl midpoint is selected, following his stated
rule for handle choice.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VALIDATION CODEX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Every rule below must be provable by an existing test in
tests/unit/test_chart_shape.py.  Adding a rule requires adding a test.
Removing a test requires removing or revising the corresponding rule.

RULE-01  Classification completeness
    classify_chart_shape returns a ChartShape for exactly the canonical ten
    Jones bodies and rejects every other body set.
    Tests: TestPlanetSetDoctrine.

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
    For Bucket, handle_planet names one planet and clusters has two entries.
    handle_bodies is the one-member authoritative handle identity, is a subset
    of clusters[1], and is disjoint from clusters[0].  Non-Bucket shapes carry
    an empty handle_bodies.
    Enforced by __post_init__ (handle_planet non-None + cluster count +
    handle_bodies non-empty/subset-of-clusters[1]/disjoint-from-clusters[0];
    empty handle_bodies required off-Bucket).
    Tests: TestBucketDetection::test_bucket_handle_is_pluto,
           TestBucketDetection::test_bucket_handle_in_second_cluster,
           TestBucketDetection::test_bucket_handle_bodies_singleton,
           TestBucketDetection::test_conjunction_pair_is_not_a_jones_bucket,
           TestChartShapeInvariants::test_bucket_without_handle_raises,
           TestChartShapeInvariants::test_bucket_without_handle_bodies_raises,
           TestChartShapeInvariants::test_bucket_with_two_handle_bodies_raises,
           TestChartShapeInvariants::test_bucket_handle_bodies_not_in_second_cluster_raises,
           TestChartShapeInvariants::test_bucket_handle_bodies_in_first_cluster_raises,
           TestChartShapeInvariants::test_non_bucket_with_handle_bodies_raises.

RULE-11  Bucket hemisphere and handle-choice doctrine
    The handle lies opposite the midpoint of the nine-body Bowl core by at
    least 90 degrees.  No rim-distance threshold is imposed.  If more than one
    removal yields a Bowl core, the least-leaning handle wins.
    Tests: TestBucketDetection::test_bucket_handle_at_60_from_rim_is_bucket,
           TestBucketDetection::test_bowl_interior_planet_does_not_trigger_bucket.

RULE-12  Locomotive / Seesaw disambiguation
    A Locomotive has one Jones-separated gap delimited by a trine within
    Jones's body-dependent aspect orb.  Two groups take Seesaw precedence.
    Tests: TestLocomotiveDetection::test_locomotive_does_not_fire_on_seesaw,
           TestLocomotiveDetection::test_functioning_trine_orb_can_delimit_locomotive,
           TestLocomotiveDetection::test_gap_outside_trine_orb_is_not_locomotive,
           TestJonesGapDoctrine.

RULE-13  Seesaw cluster integrity
    A Seesaw has exactly two Jones-separated groups, each containing at least
    two planets.  A 30-degree intra-group gap is not a disqualifier.
    Tests: TestSeesawDetection::test_seesaw_clusters_each_have_multiple_planets,
           TestSeesawDetection::test_seesaw_allows_30_degree_internal_gap.

RULE-14  Splay cluster integrity
    A Splay has exactly three Jones-separated groups.  A one-planet reins
    group is valid under Jones's explicit examples.
    Tests: TestSplayDetection::test_splay_has_exactly_three_groups,
           TestSplayDetection::test_splay_allows_singleton_reins_group.

RULE-15  Splash is the documented borderline residual
    Splash represents the source's wheel-like distribution and is the engine
    tie-break only after canonical-body validation and all defined one-, two-,
    and three-group forms decline.
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

RULE-20  Seesaw partitioning is seam-safe
    A chart whose planets form two clean opposing clusters, one of which
    crosses the 0/360 longitude seam, is classified as Seesaw and is not
    demoted to Splash.  Clusters are built in circular walk order.
    Test: TestSeesawDetection::test_seesaw_cluster_crossing_zero_is_seesaw.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Public surface
--------------
``ChartShapeType``       — enum of the seven Jones pattern names.
``ChartShape``           — frozen result vessel.
``classify_chart_shape`` — single entry point; positions -> ChartShape.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from .constants import Body
from .coordinates import normalize_degrees, angular_distance


__all__ = [
    "ChartShapeType",
    "ChartShape",
    "classify_chart_shape",
]


# ---------------------------------------------------------------------------
# Jones 1960 aspect and span policy
# ---------------------------------------------------------------------------

_BUNDLE_MAX_ARC = 120.0
_BOWL_MAX_ARC = 180.0
_SEXTILE_DEGREES = 60.0
_TRINE_DEGREES = 120.0
_UNASPECTED_EMPTY_SPACE_MIN = 70.0

# Jones, Essentials ch. 1: 17 degrees when the Sun participates, 12 degrees
# 30 minutes when the Moon (but not the Sun) participates, and 10 degrees for
# the other planets.  These are deliberately Jones's aspect orbs rather than
# Moira's general aspect-search policy.
_SUN_ASPECT_ORB = 17.0
_MOON_ASPECT_ORB = 12.5
_PLANET_ASPECT_ORB = 10.0

_JONES_BODIES = frozenset(Body.ALL_PLANETS)


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
        Nine planets form a Bowl and one planet stands in the opposite
        hemisphere as the handle.  The handle is the dominant focal channel.

    LOCOMOTIVE
        All planets within a 240-degree arc, leaving one continuous
        empty arc of at least 120 degrees.  The leading planet (at the
        clockwise edge of the occupied arc) drives the life forward.

    SEESAW
        Two distinct planet clusters on opposing sides of the wheel,
        separated on both sides by a sextile-qualified or greater-than-70
        degree empty space.  Characteristic oppositions between the clusters;
        life lived between two poles.

    SPLAY
        Three distinct groups in a tripod arrangement.  One group may be a
        singleton reins planet.  Does not conform to the neat bipolarity of
        the Bowl or Seesaw.

    SPLASH
        Planets approach an equally spaced, wheel-like distribution.  It also
        supplies the documented engine tie-break for Jones's borderline cases.
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
        The arc in degrees spanned by the classified planet set (360 minus
        the largest gap).  Always in [0, 360].
        Bucket exception: for Bucket these metrics describe the bowl *core* --
        the arc and gap of the remaining planets after the handle is removed --
        not the full chart including the handle.  This is intentional and is
        asserted by the frozen Bucket tests.

    largest_gap
        The largest continuous empty arc in degrees between any two
        consecutive planets (travelling clockwise).  Always in [0, 360].
        For Bucket this is the bowl-core gap (handle removed); see occupied_arc.

    leading_planet
        For Bowl and Locomotive: the planet at the clockwise-leading edge
        of the occupied arc — the last planet encountered going clockwise
        before entering the largest gap.
        For Bucket: the handle planet name.
        None for all other shapes.

    handle_planet
        For Bucket: the singleton handle planet's name.  This is a display
        string; use handle_bodies for membership tests.
        None for all other shapes.

    handle_bodies
        For Bucket: the frozenset of the actual body names forming the handle
        (exactly one name).  This is the authoritative handle identity: it is
        always a non-empty subset of
        clusters[1] and never intersects clusters[0].
        Empty frozenset for all other shapes.

    clusters
        Tuple of frozensets, each containing the body names in one
        detected cluster.  The clusters are ordered clockwise starting
        from the cluster immediately after the first partitioning gap
        encountered clockwise from 0 degrees (for Splay or Seesaw, the first
        Jones-qualifying group separation).  This is not necessarily the
        single largest gap.
        For Bundle, Bowl, Bucket, Locomotive: one cluster (plus the
        handle as a separate singleton for Bucket).
        For Seesaw: two clusters.
        For Splay: exactly three clusters.
        For Splash: one cluster containing all bodies (no sub-grouping).

    Structural invariants
    ---------------------
    - ``occupied_arc + largest_gap == 360.0`` (within floating-point precision).
    - For Bucket: ``handle_planet`` is set (display label); ``handle_bodies``
      contains exactly one name, is a subset of ``clusters[1]``, and is
      disjoint from ``clusters[0]``.
    - For non-Bucket shapes: ``handle_bodies`` is empty.
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
    handle_bodies:   frozenset[str] = frozenset()

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
            if not self.handle_bodies:
                raise ValueError(
                    "ChartShape invariant violated: Bucket requires handle_bodies to be non-empty"
                )
            if len(self.handle_bodies) != 1:
                raise ValueError(
                    "ChartShape invariant violated: Jones Bucket requires exactly one handle body"
                )
            if not self.handle_bodies <= self.clusters[1]:
                raise ValueError(
                    f"ChartShape invariant violated: handle_bodies {set(self.handle_bodies)!r} "
                    f"must be a subset of clusters[1]"
                )
            if self.handle_bodies & self.clusters[0]:
                raise ValueError(
                    f"ChartShape invariant violated: handle_bodies {set(self.handle_bodies)!r} "
                    f"must not intersect clusters[0]"
                )
        elif self.handle_bodies:
            raise ValueError(
                f"ChartShape invariant violated: {self.shape.value} must carry empty "
                f"handle_bodies (got {set(self.handle_bodies)!r})"
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


def _jones_aspect_orb(body1: str, body2: str) -> float:
    """Return Jones's major-aspect orb for the two delimiting bodies."""
    names = {body1, body2}
    if "Sun" in names:
        return _SUN_ASPECT_ORB
    if "Moon" in names:
        return _MOON_ASPECT_ORB
    return _PLANET_ASPECT_ORB


def _is_group_separating_gap(
    gap: tuple[float, int, int],
    sorted_lons: list[tuple[float, str]],
) -> bool:
    """Apply Jones's explicit Seesaw empty-space criterion.

    Essentials ch. 2 requires an empty span delimited by a functioning
    sextile, or more than 70 degrees when no sextile is formed.  The same
    criterion is used here to turn the source's qualitative "distinct groups"
    into a deterministic partition for Seesaw, Splay, and Splash.
    """
    gap_degrees, from_index, to_index = gap
    body1 = sorted_lons[from_index][1]
    body2 = sorted_lons[to_index][1]
    orb = _jones_aspect_orb(body1, body2)
    return (
        abs(gap_degrees - _SEXTILE_DEGREES) <= orb
        or gap_degrees > _UNASPECTED_EMPTY_SPACE_MIN
    )


def _group_separating_gaps(
    sorted_lons: list[tuple[float, str]],
    gaps: list[tuple[float, int, int]],
) -> list[tuple[float, int, int]]:
    return [gap for gap in gaps if _is_group_separating_gap(gap, sorted_lons)]


def _split_at_gaps(
    sorted_lons: list[tuple[float, str]],
    split_gaps: list[tuple[float, int, int]],
) -> list[frozenset[str]]:
    """Partition the wheel immediately after the supplied circular gaps."""
    if not split_gaps:
        return [frozenset(name for _, name in sorted_lons)]

    n = len(sorted_lons)
    split_after = [from_index for _, from_index, _ in split_gaps]
    split_set = set(split_after)
    start = (split_after[0] + 1) % n
    clusters: list[frozenset[str]] = []
    current: list[str] = []

    for step in range(n):
        index = (start + step) % n
        current.append(sorted_lons[index][1])
        if index in split_set:
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
    """Bowl: all ten planets lie within one zodiacal hemisphere."""
    if occupied_arc > _BOWL_MAX_ARC:
        return None

    _, gap_from, _ = max(gaps, key=lambda g: g[0])
    leading_rim = sorted_lons[gap_from][1]

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
    """Bucket: a one-nine division with the nine forming a Bowl.

    Jones does not impose a 60-degree distance from both rim planets.  He does
    require the handle to be in the zodiacal hemisphere opposite the other
    nine and says that, when more than one handle choice is possible, the
    planet closest to the ideal position opposite the Bowl midpoint is chosen.
    """
    n = len(sorted_lons)
    candidates: list[tuple[float, float, str, float, frozenset[str]]] = []

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

        _, _, bowl_gap_to = max(rem_gaps, key=lambda g: g[0])
        core_start_lon = remaining[bowl_gap_to][0]
        core_midpoint = normalize_degrees(core_start_lon + rem_arc / 2.0)
        midpoint_distance = angular_distance(handle_lon, core_midpoint)

        # A handle in the same hemisphere as the Bowl core is explicitly
        # rejected by Jones's 1960 refinement.  The ideal handle is 180
        # degrees from the core midpoint; lower lean wins if several removals
        # produce a Bowl-like core.
        if midpoint_distance < 90.0:
            continue

        lean = 180.0 - midpoint_distance
        candidates.append(
            (
                lean,
                rem_arc,
                handle_name,
                rem_largest_gap,
                frozenset(name for _, name in remaining),
            )
        )

    if candidates:
        _, rem_arc, handle_name, rem_largest_gap, bowl_bodies = min(
            candidates,
            key=lambda candidate: (candidate[0], candidate[1], candidate[2]),
        )
        handle_set = frozenset({handle_name})
        return ChartShape(
            shape=ChartShapeType.BUCKET,
            occupied_arc=rem_arc,
            largest_gap=rem_largest_gap,
            leading_planet=handle_name,
            handle_planet=handle_name,
            clusters=(bowl_bodies, handle_set),
            handle_bodies=handle_set,
        )

    return None


def _detect_locomotive(
    sorted_lons: list[tuple[float, str]],
    gaps: list[tuple[float, int, int]],
    separating_gaps: list[tuple[float, int, int]],
    largest_gap: float,
    occupied_arc: float,
) -> ChartShape | None:
    if occupied_arc <= _BUNDLE_MAX_ARC:
        return None  # Bundle takes priority
    if occupied_arc <= _BOWL_MAX_ARC:
        return None  # Bowl takes priority

    # Jones requires a single empty region delimited by a functioning trine.
    # The gap may be either under or over 120 degrees only while its boundary
    # planets remain within Jones's admitted major-aspect orb.
    if len(separating_gaps) != 1:
        return None
    gap_val, gap_from, gap_to = separating_gaps[0]
    boundary_orb = _jones_aspect_orb(
        sorted_lons[gap_from][1], sorted_lons[gap_to][1]
    )
    if abs(gap_val - _TRINE_DEGREES) > boundary_orb:
        return None

    # Leading planet: immediately before (clockwise) the largest gap.
    _, gap_from, _ = max(gaps, key=lambda g: g[0])
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


def _detect_seesaw(
    sorted_lons: list[tuple[float, str]],
    separating_gaps: list[tuple[float, int, int]],
    largest_gap: float,
    occupied_arc: float,
) -> ChartShape | None:
    # Jones defines exactly two distinct aggregates of two or more planets.
    # He does not impose a 30-degree maximum gap inside either aggregate.
    if len(separating_gaps) != 2:
        return None

    clusters = _split_at_gaps(sorted_lons, separating_gaps)
    if len(clusters) != 2 or any(len(cluster) < 2 for cluster in clusters):
        return None

    return ChartShape(
        shape=ChartShapeType.SEESAW,
        occupied_arc=occupied_arc,
        largest_gap=largest_gap,
        leading_planet=None,
        handle_planet=None,
        clusters=tuple(clusters),
    )


def _detect_splay(
    sorted_lons: list[tuple[float, str]],
    separating_gaps: list[tuple[float, int, int]],
    largest_gap: float,
) -> ChartShape | None:
    # Jones's Splay is a threefold or tripod arrangement.  His Franklin D.
    # Roosevelt and Houdini examples explicitly admit a one-planet "reins"
    # grouping, so singleton clusters are valid here.
    if len(separating_gaps) != 3:
        return None
    clusters = _split_at_gaps(sorted_lons, separating_gaps)
    if len(clusters) != 3:
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
    largest_gap: float,
) -> ChartShape:
    # Jones describes an approximately wheel-like distribution.  With the
    # canonical ten bodies enforced at the public boundary, this is the
    # deterministic residual after the one-, two-, and three-group structures
    # have been tested.  Borderline charts necessarily remain a judgment call
    # in the primary source; this fallback is Moira policy, not a Jones quote.
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
    positions : mapping of the ten Jones bodies (Sun through Pluto) to
                ecliptic longitude in degrees.  Nodes, angles, asteroids, and
                omitted planets are outside the source method and are rejected.

    Returns
    -------
    ChartShape — the classified pattern and its derived metrics.

    Detection order
    ---------------
    1. Bundle     (occupied arc <= 120)
    2. Bowl       (occupied arc <= 180, no isolated handle)
    3. Bucket     (one planet in the opposite hemisphere; other nine in a Bowl)
    4. Seesaw     (two Jones-separated groups, each containing 2+ planets)
    5. Splay      (three Jones-separated groups; a singleton reins group allowed)
    6. Locomotive (one Jones-separated empty region delimited by a trine)
    7. Splash     (wheel-like residual / borderline fallback)

    Raises
    ------
    ValueError if positions is not exactly the canonical Jones body set.
    """
    supplied_bodies = frozenset(positions)
    if supplied_bodies != _JONES_BODIES:
        missing = sorted(_JONES_BODIES - supplied_bodies)
        extra = sorted(supplied_bodies - _JONES_BODIES)
        raise ValueError(
            "classify_chart_shape requires exactly the ten Jones bodies "
            f"(Sun through Pluto); missing={missing!r}, extra={extra!r}"
        )

    sorted_lons = _sorted_longitudes(positions)

    gaps          = _compute_gaps(sorted_lons)
    largest_gap   = max(g for g, _, _ in gaps)
    occupied_arc  = 360.0 - largest_gap
    separating_gaps = _group_separating_gaps(sorted_lons, gaps)

    result = _detect_bundle(sorted_lons, largest_gap, occupied_arc)
    if result:
        return result

    result = _detect_bowl(sorted_lons, gaps, largest_gap, occupied_arc)
    if result:
        return result

    result = _detect_bucket(sorted_lons)
    if result:
        return result

    result = _detect_seesaw(
        sorted_lons,
        separating_gaps,
        largest_gap,
        occupied_arc,
    )
    if result:
        return result

    result = _detect_splay(sorted_lons, separating_gaps, largest_gap)
    if result:
        return result

    result = _detect_locomotive(
        sorted_lons,
        gaps,
        separating_gaps,
        largest_gap,
        occupied_arc,
    )
    if result:
        return result

    return _detect_splash(sorted_lons, largest_gap)
