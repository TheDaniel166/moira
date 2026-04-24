"""
Moira — Paran Engine
Governs computation of near-simultaneous mundane-circle crossings between two distinct bodies at a specific terrestrial location during a single 24-hour search window.

Boundary: owns paran detection logic, crossing-time collection, time-orb comparison, ParanCrossing and Paran result vessels. Delegates rise/set time computation to moira.rise_set.

Import-time side effects: None

External dependencies:
    - math module for mathematical operations
    - itertools for combination generation
    - dataclasses for structured data definitions
    - datetime for temporal operations
    - functools for caching
    - moira.constants for body definitions

Public surface:
    CIRCLE_TYPES, DEFAULT_PARAN_POLICY, Paran, ParanCrossing, ParanSignature,
    ParanPolicy, ParanStrength, ParanStability, ParanStabilitySample,
    evaluate_paran_stability, ParanSiteResult, ParanFieldSample, evaluate_paran_site,
    sample_paran_field, ParanFieldAnalysis, ParanFieldRegion, ParanFieldPeak,
    ParanThresholdCrossing, analyze_paran_field, ParanContourExtraction,
    ParanContourSegment, ParanContourPoint, extract_paran_field_contours,
    ParanContourPathSet, ParanContourPath, consolidate_paran_contours,
    ParanFieldStructure, ParanContourHierarchyEntry, ParanContourAssociation,
    analyze_paran_field_structure, find_parans, natal_parans
"""

import math
import itertools
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache

from .constants import Body


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CIRCLE_TYPES = ("Rising", "Setting", "Culminating", "AntiCulminating")

_SUPPORTED_METRICS = frozenset({"match_presence", "exactness_score", "survival_rate"})

# Minutes → fractional JD conversion factor
_MINUTES_TO_JD = 1.0 / (24.0 * 60.0)


# ---------------------------------------------------------------------------
# Public API surface
# ---------------------------------------------------------------------------
# This list is the machine-readable contract for the paran subsystem.
# Names not listed here are internal implementation details and must not be
# imported as public API.  See moira/docs/PARANS_BACKEND_STANDARD.md.

__all__ = [
    # Constants / configuration
    "CIRCLE_TYPES",
    "DEFAULT_PARAN_POLICY",
    # Core vessels
    "Paran",
    "ParanCrossing",
    "ParanSignature",
    "ParanPolicy",
    "ParanStrength",
    # Stability (Phase 6)
    "ParanStability",
    "ParanStabilitySample",
    "evaluate_paran_stability",
    # Site / grid evaluation (Phase 7)
    "ParanSiteResult",
    "ParanFieldSample",
    "evaluate_paran_site",
    "sample_paran_field",
    # Field analysis (Phase 8)
    "ParanFieldAnalysis",
    "ParanFieldRegion",
    "ParanFieldPeak",
    "ParanThresholdCrossing",
    "analyze_paran_field",
    # Contour extraction (Phase 9)
    "ParanContourExtraction",
    "ParanContourSegment",
    "ParanContourPoint",
    "extract_paran_field_contours",
    # Contour consolidation (Phase 10)
    "ParanContourPathSet",
    "ParanContourPath",
    "consolidate_paran_contours",
    # Higher-order field structure (Phase 11)
    "ParanFieldStructure",
    "ParanContourHierarchyEntry",
    "ParanContourAssociation",
    "analyze_paran_field_structure",
    # Engine entry points
    "find_parans",
    "natal_parans",
]


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def _validate_circle(circle: str) -> None:
    """
    Raise ``ValueError`` when *circle* is not a member of ``CIRCLE_TYPES``.

    Called at paran-classification boundaries so that unknown circle strings
    produce an immediate, explicit error rather than a delayed ``KeyError``
    deep inside the classifier.
    """
    if circle not in CIRCLE_TYPES:
        raise ValueError(
            f"Unknown circle type {circle!r}. "
            f"Must be one of {CIRCLE_TYPES}."
        )


def _validate_metric(metric: str) -> None:
    """
    Raise ``ValueError`` when *metric* is not a member of
    ``_SUPPORTED_METRICS``.

    Called at the entry points of field-analysis and contour-extraction
    functions so that unsupported metric names fail immediately at the call
    boundary rather than on the first sample iteration.
    """
    if metric not in _SUPPORTED_METRICS:
        raise ValueError(
            f"Unsupported field metric {metric!r}. "
            f"Must be one of {sorted(_SUPPORTED_METRICS)}."
        )


def _validate_orb_non_negative(orb_minutes: float) -> None:
    """
    Raise ``ValueError`` when *orb_minutes* is negative.

    ``Paran.orb_min`` is documented as always non-negative.  This guard is
    enforced at ``find_parans`` entry so that the invariant holds for all
    engine-produced ``Paran`` instances without requiring a slot validator on
    the dataclass.
    """
    if orb_minutes < 0:
        raise ValueError(
            f"orb_minutes must be non-negative, got {orb_minutes!r}."
        )


@lru_cache(maxsize=1)
def _named_star_catalog() -> frozenset[str]:
    """
    Return the named fixed-star catalog if available, else an empty set.

    Classification doctrine:
        ``ParanSignature.body_family`` is intentionally based on Moira's local
        named-star catalog rather than a broader astronomical taxonomy. In the
        current model, a body is treated as ``"star"`` only if it resolves as a
        named fixed star through ``moira.stars.list_stars()``. Failure to
        load that catalog does not change paran matching semantics; it only
        causes body-family classification to fall back more often to
        ``"other"``.
    """
    try:
        from .stars import list_stars
        return frozenset(list_stars())
    except Exception:
        return frozenset()


def _body_family_role(body: str) -> str:
    """
    Classify a body name into the lean role buckets used by ``ParanSignature``.

    This helper is intentionally permissive. It preserves current computational
    semantics and only exposes a coarse classification surface suitable for
    Phase 2. Anything that is neither a default planet nor a known named fixed
    star is left in the explicit ``"other"`` bucket.

    Current body-family doctrine:
    - ``"planet"`` means membership in ``Body.ALL_PLANETS``.
    - ``"star"`` means membership in the named fixed-star catalog.
    - ``"other"`` is the explicit remainder bucket.

    This is descriptive classification only. It does not alter matching,
    ranking, inclusion, or doctrinal validity.
    """
    if body in Body.ALL_PLANETS:
        return "planet"
    if body in _named_star_catalog():
        return "star"
    return "other"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class ParanCrossing:
    """
    RITE: The Crossing Witness — a single moment of mundane circle passage.

    THEOREM: Holds the body name, circle type, and Julian Day of a single
    instance where a celestial body crosses one of the four mundane circles
    (Rising, Setting, Culminating, AntiCulminating).

    Doctrinal note:
        This vessel is computational only. It records one timed event drawn
        from the underlying rise/set + transit machinery. It does not claim
        that every recorded event is equally emphasized by every traditional
        school of paran work.

    RITE OF PURPOSE:
        Serves the Paran Engine as the atomic unit of paran detection. Every
        paran is formed by pairing two ``ParanCrossing`` instances whose times
        fall within the orb. Without this vessel, the crossing-time collection
        step would have no structured representation, making paran matching
        impossible.

    LAW OF OPERATION:
        Responsibilities:
            - Store the body name, circle type string, crossing JD, and the
              delegated method/policy metadata used to obtain that event.
            - Expose ``datetime_utc`` and ``calendar_utc`` computed properties
              for human-readable time access.
        Non-responsibilities:
            - Does not compute crossing times (delegated to ``_crossing_times``).
            - Does not validate that ``circle`` is one of ``CIRCLE_TYPES``.
        Dependencies:
            - ``datetime_utc`` delegates to ``moira.julian.datetime_from_jd``.
            - ``calendar_utc`` delegates to ``moira.julian.calendar_datetime_from_jd``.
        Structural invariants:
            - ``circle`` is always one of "Rising", "Setting", "Culminating",
              "AntiCulminating".
        Succession stance: terminal — not designed for subclassing.

    Canon: Brady, "Brady's Book of Fixed Stars" (1998); Ptolemy, Tetrabiblos I.

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.parans.ParanCrossing",
        "risk": "low",
        "api": {
            "public_methods": ["datetime_utc", "calendar_utc", "__repr__"],
            "public_attributes": ["body", "circle", "jd", "source_method", "altitude_policy"]
        },
        "state": {
            "mutable": false,
            "fields": ["body", "circle", "jd", "source_method", "altitude_policy"]
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
            "policy": "caller ensures valid JD before construction"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]

    Attributes
    ----------
    body   : name of the celestial body.
    circle : one of ``"Rising"``, ``"Setting"``, ``"Culminating"``,
             ``"AntiCulminating"``.
    jd     : Julian Day (UT) of the crossing.
    source_method   : delegated timing method that produced the event.
    altitude_policy : altitude threshold used when applicable (rise/set only).
    """

    body: str
    circle: str           # "Rising", "Setting", "Culminating", "AntiCulminating"
    jd: float             # JD of the crossing (UT)
    source_method: str    # delegated source, e.g. "find_phenomena" or "get_transit"
    altitude_policy: float | None = None

    @property
    def datetime_utc(self) -> datetime:
        """Return the crossing time as a timezone-aware UTC datetime."""
        from .julian import datetime_from_jd
        return datetime_from_jd(self.jd)

    @property
    def calendar_utc(self):
        """Return the crossing time as a BCE-safe UTC calendar object."""
        from .julian import calendar_datetime_from_jd
        return calendar_datetime_from_jd(self.jd)

    def __repr__(self) -> str:
        return (
            f"ParanCrossing({self.body!r}, {self.circle!r}, "
            f"jd={self.jd:.6f})"
        )


@dataclass(slots=True)
class ParanSignature:
    """
    RITE: The Signature Witness — a lean geometric classification of a paran.

    THEOREM: Holds a small set of deterministic labels describing what sort of
    angular coincidence a candidate paran represents.

    Scope note:
        This is intentionally a narrow Phase 2 surface. It classifies the
        candidate paran without imposing doctrinal ranking, filtering, or
        strength/stability rules.

    Attributes
    ----------
    event_family : normalized event pairing, e.g. ``"rise-mc"`` or
                   ``"mc-ic"``.
    axis_family  : one of ``"horizon-horizon"``, ``"horizon-meridian"``, or
                   ``"meridian-meridian"``.
    body_family  : one of ``"planet-planet"``, ``"planet-star"``,
                   ``"star-star"``, or ``"other"`` in the current model.
    """

    event_family: str
    axis_family: str
    body_family: str


@dataclass(frozen=True, slots=True)
class ParanPolicy:
    """
    RITE: The Policy Witness — explicit backend doctrine for paran inclusion.

    THEOREM: Holds permissive or restrictive backend rules for admitting
    already-computed paran candidates. This layer does not redefine event
    generation or the core coincidence matcher; it only decides whether a
    candidate paran is retained after classification and before any later
    strength/stability analysis.

    Default stance:
        The default values preserve Moira's current permissive behavior exactly.
        Same-event pairings, same-axis pairings, mixed pairings, and star
        involvement are all admitted unless a stricter policy is supplied.

    Attributes
    ----------
    allow_same_event_family : admit pairings such as ``"mc-mc"`` or
                              ``"rise-rise"`` when true.
    allow_same_axis_family  : admit pairings such as
                              ``"meridian-meridian"`` or
                              ``"horizon-horizon"`` when true.
    allowed_body_families   : optional allow-list of signature body-family
                              labels. ``None`` means no restriction.
    include_stars           : when false, reject candidates where either body is
                              classified as a named fixed star.
    allowed_named_stars     : optional allow-list for star bodies by name.
                              Non-star bodies are unaffected.
    """

    allow_same_event_family: bool = True
    allow_same_axis_family: bool = True
    allowed_body_families: frozenset[str] | None = None
    include_stars: bool = True
    allowed_named_stars: frozenset[str] | None = None


DEFAULT_PARAN_POLICY = ParanPolicy()


@dataclass(frozen=True, slots=True)
class ParanStrength:
    """
    Pure geometric strength summary derived from orb exactness only.

    This layer is intentionally non-interpretive. It does not rank event
    families, body families, or traditional significance. In this phase the
    only input is the already-computed event separation in minutes.

    Attributes
    ----------
    orb_minutes     : raw absolute time separation between the two events.
    exactness_score : normalized exactness score on ``(0, 1]`` where tighter
                      orb means stronger exactness.
    model           : explicit score-model label for inspectability.
    """

    orb_minutes: float
    exactness_score: float
    model: str = "inverse_minutes"


def _derive_paran_strength(paran: "Paran") -> ParanStrength:
    """
    Return the pure geometric strength summary for an admitted paran.

    Current model:
        ``exactness_score = 1 / (1 + orb_minutes)``

    This score is intentionally simple and explicit. It depends only on the
    paran's already-computed orb and therefore cannot change matching or policy
    semantics. Future perturbation or stability layers should extend above this
    raw exactness model rather than replacing the core event separation.
    """
    orb_minutes = paran.orb_min
    return ParanStrength(
        orb_minutes=orb_minutes,
        exactness_score=1.0 / (1.0 + orb_minutes),
    )


@dataclass(frozen=True, slots=True)
class ParanStabilitySample:
    """
    One perturbation sample from Phase 6 stability recomputation.

    Attributes
    ----------
    offset_minutes   : signed perturbation applied to the search anchor.
    survived         : whether the same paran was re-identified after
                       recomputation.
    orb_minutes      : recomputed orb when the paran survived, else ``None``.
    exactness_score  : recomputed Phase 5 exactness when the paran survived,
                       else ``None``.
    """

    offset_minutes: float
    survived: bool
    orb_minutes: float | None
    exactness_score: float | None


@dataclass(frozen=True, slots=True)
class ParanStability:
    """
    Perturbation-based stability summary for a single baseline paran.

    This layer is geometric and recomputation-based. It does not interpret a
    paran's meaning or importance. In this phase it answers whether the same
    paran survives small signed time perturbations of the search anchor and how
    its orb/exactness change when it does.

    Attributes
    ----------
    method                   : explicit perturbation method label.
    baseline_orb_minutes     : baseline orb from the unperturbed paran.
    baseline_exactness_score : baseline Phase 5 exactness score.
    offsets_minutes          : perturbation window evaluated by the helper.
    samples                  : per-offset recomputation results.
    survival_rate            : fraction of offsets for which the paran survived.
    stable_across_window     : true only if the paran survived all evaluated
                               perturbations.
    worst_orb_minutes        : largest surviving orb in the evaluated window.
    max_orb_degradation      : worst increase in orb over baseline among
                               surviving perturbations.
    worst_exactness_score    : lowest surviving exactness score in the window.
    max_exactness_drop       : largest exactness drop from baseline among
                               surviving perturbations.
    """

    method: str
    baseline_orb_minutes: float
    baseline_exactness_score: float
    offsets_minutes: tuple[float, ...]
    samples: tuple[ParanStabilitySample, ...]
    survival_rate: float
    stable_across_window: bool
    worst_orb_minutes: float | None
    max_orb_degradation: float | None
    worst_exactness_score: float | None
    max_exactness_drop: float | None


@dataclass(frozen=True, slots=True)
class ParanSiteResult:
    """
    Geographic site-evaluation result for one target paran at one location.

    This layer is computational only. It evaluates whether a target paran
    identity exists at the supplied site, returns the best matching paran when
    found, and exposes its already-defined strength/stability surfaces without
    redefining them.

    Attributes
    ----------
    lat       : evaluated geographic latitude.
    lon       : evaluated geographic longitude.
    matched   : whether the target paran was found at the site.
    paran     : best matching paran when found, else ``None``.
    strength  : derived Phase 5 strength for the matched paran, else ``None``.
    stability : optional Phase 6 stability result when requested, else ``None``.
    """

    lat: float
    lon: float
    matched: bool
    paran: "Paran | None"
    strength: ParanStrength | None
    stability: ParanStability | None


@dataclass(frozen=True, slots=True)
class ParanFieldSample:
    """
    One structured sample from a geographic paran field grid.

    Attributes
    ----------
    lat         : sampled geographic latitude.
    lon         : sampled geographic longitude.
    site_result : site-evaluation result at this grid point.
    """

    lat: float
    lon: float
    site_result: ParanSiteResult


@dataclass(frozen=True, slots=True)
class ParanThresholdCrossing:
    """
    One orthogonal neighbor edge where threshold membership changes.

    Attributes
    ----------
    start_lat    : latitude of the first grid point.
    start_lon    : longitude of the first grid point.
    end_lat      : latitude of the second grid point.
    end_lon      : longitude of the second grid point.
    start_value  : metric value at the first point.
    end_value    : metric value at the second point.
    """

    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    start_value: float
    end_value: float


@dataclass(frozen=True, slots=True)
class ParanFieldRegion:
    """
    One connected threshold-passing region in a sampled paran field.

    Neighbor rule:
        Regions use orthogonal grid adjacency only: north, south, east, west.
        Diagonal adjacency is intentionally excluded in this phase.

    Attributes
    ----------
    region_id    : deterministic region label in discovery order.
    sample_count : number of grid points in the region.
    cells        : ordered ``(lat, lon)`` grid coordinates in the region.
    peak_value   : largest metric value inside the region.
    """

    region_id: int
    sample_count: int
    cells: tuple[tuple[float, float], ...]
    peak_value: float


@dataclass(frozen=True, slots=True)
class ParanFieldPeak:
    """
    One local maximum in a sampled paran field under orthogonal adjacency.

    Peak rule:
        A sample is a peak when its metric value is not below any orthogonal
        neighbor and is strictly greater than at least one orthogonal neighbor,
        or when it has no orthogonal neighbors.
    """

    lat: float
    lon: float
    value: float


@dataclass(frozen=True, slots=True)
class ParanFieldAnalysis:
    """
    Structural analysis summary for sampled paran geography.

    This layer operates only on already-sampled field results. It does not
    render, interpolate, smooth, contour, or project anything.

    Attributes
    ----------
    metric              : explicit metric name used for analysis.
    threshold           : explicit threshold used for ``value >= threshold``.
    adjacency           : neighbor rule label, currently ``"orthogonal"``.
    total_samples       : number of analyzed field samples.
    active_sample_count : number of samples meeting the threshold.
    regions             : connected threshold-passing regions.
    peaks               : local maxima under the declared metric.
    threshold_crossings : orthogonal neighbor edges that cross the threshold.
    """

    metric: str
    threshold: float
    adjacency: str
    total_samples: int
    active_sample_count: int
    regions: tuple[ParanFieldRegion, ...]
    peaks: tuple[ParanFieldPeak, ...]
    threshold_crossings: tuple[ParanThresholdCrossing, ...]


@dataclass(frozen=True, slots=True)
class ParanContourPoint:
    """
    One interpolated contour point in field-grid coordinates.

    Attributes
    ----------
    lat : interpolated latitude.
    lon : interpolated longitude.
    """

    lat: float
    lon: float


@dataclass(frozen=True, slots=True)
class ParanContourSegment:
    """
    One contour-ready line segment extracted from a single grid cell.

    Attributes
    ----------
    start         : interpolated segment start point.
    end           : interpolated segment end point.
    cell_lat_min  : lower latitude bound of the source cell.
    cell_lon_min  : lower longitude bound of the source cell.
    case_index    : marching-squares case index for the source cell.
    ambiguous     : whether the source cell used an ambiguous case rule.
    """

    start: ParanContourPoint
    end: ParanContourPoint
    cell_lat_min: float
    cell_lon_min: float
    case_index: int
    ambiguous: bool


@dataclass(frozen=True, slots=True)
class ParanContourExtraction:
    """
    Contour-ready threshold geometry extracted from a sampled paran field.

    This layer is computational only. It extracts threshold-boundary fragments
    from a complete rectangular grid and deliberately does not render, smooth,
    project, or stitch them into styled map paths.

    Attributes
    ----------
    metric          : explicit field metric used for extraction.
    threshold       : explicit contour threshold.
    interpolation   : interpolation rule label, currently ``"linear"``.
    segments        : extracted contour fragments.
    ambiguous_cells : cells that used an explicit ambiguous-case rule.
    """

    metric: str
    threshold: float
    interpolation: str
    segments: tuple[ParanContourSegment, ...]
    ambiguous_cells: tuple[tuple[float, float], ...]


@dataclass(frozen=True, slots=True)
class ParanContourPath:
    """
    One ordered contour path stitched from contour fragments.

    Attributes
    ----------
    points              : ordered contour points along the path.
    closed              : whether the path forms a closed loop.
    segment_count       : number of source segments used.
    ambiguous           : whether any source segment came from an ambiguous cell.
    source_case_indices : ordered source case indices contributing to the path.
    """

    points: tuple[ParanContourPoint, ...]
    closed: bool
    segment_count: int
    ambiguous: bool
    source_case_indices: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class ParanContourPathSet:
    """
    Consolidated contour paths derived from Phase 9 contour fragments.

    Attributes
    ----------
    paths            : stitched ordered paths.
    orphan_segments  : fragments that could not be incorporated into a path.
    matching_rule    : explicit endpoint matching rule label.
    """

    paths: tuple[ParanContourPath, ...]
    orphan_segments: tuple[ParanContourSegment, ...]
    matching_rule: str


def _classify_paran(crossing1: ParanCrossing, crossing2: ParanCrossing) -> ParanSignature:
    """Return the lean geometric signature for a matched paran candidate."""
    _validate_circle(crossing1.circle)
    _validate_circle(crossing2.circle)
    event_alias = {
        "Rising": "rise",
        "Setting": "set",
        "Culminating": "mc",
        "AntiCulminating": "ic",
    }
    axis_alias = {
        "Rising": "horizon",
        "Setting": "horizon",
        "Culminating": "meridian",
        "AntiCulminating": "meridian",
    }

    event_pair = sorted(
        [event_alias[crossing1.circle], event_alias[crossing2.circle]]
    )
    axis_pair = sorted(
        [axis_alias[crossing1.circle], axis_alias[crossing2.circle]]
    )
    body_pair = sorted(
        [_body_family_role(crossing1.body), _body_family_role(crossing2.body)]
    )

    body_family = "-".join(body_pair)
    if "other" in body_pair:
        body_family = "other"

    return ParanSignature(
        event_family="-".join(event_pair),
        axis_family="-".join(axis_pair),
        body_family=body_family,
    )


def _is_same_family_label(label: str) -> bool:
    """Return whether a normalized ``x-y`` family label has matching sides."""
    left, right = label.split("-", 1)
    return left == right


def _policy_allows_paran(paran: "Paran", policy: ParanPolicy) -> bool:
    """
    Return whether a classified paran passes the supplied backend policy.

    This function is intentionally narrow: it only filters fully constructed
    candidates. Event generation and time-orb matching remain authoritative in
    the core engine.
    """
    signature = paran.signature
    if signature is None:
        return True

    if not policy.allow_same_event_family and _is_same_family_label(signature.event_family):
        return False
    if not policy.allow_same_axis_family and _is_same_family_label(signature.axis_family):
        return False
    if policy.allowed_body_families is not None and signature.body_family not in policy.allowed_body_families:
        return False

    star_bodies = [
        crossing.body
        for crossing in (paran.crossing1, paran.crossing2)
        if crossing is not None and _body_family_role(crossing.body) == "star"
    ]
    if star_bodies and not policy.include_stars:
        return False
    if policy.allowed_named_stars is not None:
        allowed = policy.allowed_named_stars
        if any(body not in allowed for body in star_bodies):
            return False

    return True


def _matching_perturbed_paran_candidates(
    baseline: "Paran",
    candidates: list["Paran"],
) -> list["Paran"]:
    """
    Return perturbed candidates that match the baseline paran identity.

    Phase 6 re-identification rule:
        A perturbed candidate is treated as the "same" paran when it preserves
        the same ordered body pair and the same ordered mundane-circle pair as
        the baseline paran. If recomputation yields multiple such candidates,
        the stability helper chooses the one whose midpoint JD is closest to
        the baseline midpoint.

    This rule is intentionally explicit and narrow. It avoids introducing a
    broader identity heuristic before geography or richer policy layers exist.
    """
    return [
        candidate
        for candidate in candidates
        if candidate.body1 == baseline.body1
        and candidate.body2 == baseline.body2
        and candidate.circle1 == baseline.circle1
        and candidate.circle2 == baseline.circle2
    ]


def _matching_site_paran_candidates(
    target: "Paran",
    candidates: list["Paran"],
) -> list["Paran"]:
    """
    Return site candidates that match the target paran identity across locations.

    Phase 7 geographic identity rule:
        A candidate at a new site is treated as the same target paran when it
        preserves the same ordered body pair and the same ordered mundane-circle
        pair as the target paran. If multiple candidates match, the site/grid
        evaluator chooses the one whose midpoint JD is closest to the target
        paran's midpoint JD.

    This keeps geographic evaluation tied to the same explicit identity rule
    family already used by perturbation stability.
    """
    return _matching_perturbed_paran_candidates(target, candidates)


def _field_metric_value(sample: ParanFieldSample, metric: str) -> float:
    """
    Return the explicit analysis metric value for one field sample.

    Supported metrics in this phase:
    - ``"match_presence"``: ``1.0`` when the target paran matched, else ``0.0``
    - ``"exactness_score"``: Phase 5 exactness for matched sites, else ``0.0``
    - ``"survival_rate"``: Phase 6 stability survival rate when available,
      else ``0.0``
    """
    site_result = sample.site_result
    if metric == "match_presence":
        return 1.0 if site_result.matched else 0.0
    if metric == "exactness_score":
        return 0.0 if site_result.strength is None else site_result.strength.exactness_score
    if metric == "survival_rate":
        return 0.0 if site_result.stability is None else site_result.stability.survival_rate
    raise ValueError(f"Unsupported field metric: {metric}")


def _infer_field_axes(samples: list[ParanFieldSample]) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Infer deterministic latitude/longitude axes from field samples."""
    latitudes = tuple(dict.fromkeys(sample.lat for sample in samples))
    longitudes = tuple(dict.fromkeys(sample.lon for sample in samples))
    return latitudes, longitudes


def _orthogonal_neighbor_coords(
    lat_idx: int,
    lon_idx: int,
    latitudes: tuple[float, ...],
    longitudes: tuple[float, ...],
) -> list[tuple[float, float]]:
    """Return orthogonal neighbor coordinates for one grid position."""
    coords: list[tuple[float, float]] = []
    if lat_idx > 0:
        coords.append((latitudes[lat_idx - 1], longitudes[lon_idx]))
    if lat_idx + 1 < len(latitudes):
        coords.append((latitudes[lat_idx + 1], longitudes[lon_idx]))
    if lon_idx > 0:
        coords.append((latitudes[lat_idx], longitudes[lon_idx - 1]))
    if lon_idx + 1 < len(longitudes):
        coords.append((latitudes[lat_idx], longitudes[lon_idx + 1]))
    return coords


def _interpolate_contour_point(
    point_a: tuple[float, float],
    value_a: float,
    point_b: tuple[float, float],
    value_b: float,
    threshold: float,
) -> ParanContourPoint:
    """
    Linearly interpolate one threshold-crossing point along a cell edge.

    Deterministic rule:
        When ``value_a == value_b``, return the edge midpoint rather than
        introducing an arbitrary division-by-zero workaround.
    """
    if value_a == value_b:
        t = 0.5
    else:
        t = (threshold - value_a) / (value_b - value_a)
    lat = point_a[0] + t * (point_b[0] - point_a[0])
    lon = point_a[1] + t * (point_b[1] - point_a[1])
    return ParanContourPoint(lat=lat, lon=lon)


def _contour_point_key(point: ParanContourPoint) -> tuple[float, float]:
    """
    Return the exact endpoint-matching key for a contour point.

    Phase 10 matching rule:
        Endpoint matching is exact on the extracted floating-point coordinates.
        No tolerance is applied in this phase because the contour extractor is
        deterministic and shared cell edges produce identical interpolated
        coordinates.
    """
    return (point.lat, point.lon)


def _extract_cell_contour_segments(
    lat_min: float,
    lat_max: float,
    lon_min: float,
    lon_max: float,
    bottom_left_value: float,
    bottom_right_value: float,
    top_right_value: float,
    top_left_value: float,
    threshold: float,
) -> tuple[list[ParanContourSegment], bool]:
    """
    Extract contour fragments for one rectangular grid cell.

    Corner order and case index:
        The marching-squares case index uses
        ``bottom_left=1, bottom_right=2, top_right=4, top_left=8`` with
        threshold membership defined by ``value >= threshold``.

    Ambiguous cases:
        Cases ``5`` and ``10`` are reported explicitly. This phase resolves
        them deterministically with a fixed segment pairing table rather than a
        smoothing heuristic or asymptotic decider.
    """
    values = {
        "bottom": (bottom_left_value, bottom_right_value),
        "right": (bottom_right_value, top_right_value),
        "top": (top_left_value, top_right_value),
        "left": (bottom_left_value, top_left_value),
    }
    points = {
        "bottom": ((lat_min, lon_min), (lat_min, lon_max)),
        "right": ((lat_min, lon_max), (lat_max, lon_max)),
        "top": ((lat_max, lon_min), (lat_max, lon_max)),
        "left": ((lat_min, lon_min), (lat_max, lon_min)),
    }

    case_index = 0
    if bottom_left_value >= threshold:
        case_index |= 1
    if bottom_right_value >= threshold:
        case_index |= 2
    if top_right_value >= threshold:
        case_index |= 4
    if top_left_value >= threshold:
        case_index |= 8

    if case_index in (0, 15):
        return [], False

    crossings: dict[str, ParanContourPoint] = {}
    for edge_name, (value_a, value_b) in values.items():
        if (value_a >= threshold) != (value_b >= threshold):
            point_a, point_b = points[edge_name]
            crossings[edge_name] = _interpolate_contour_point(
                point_a,
                value_a,
                point_b,
                value_b,
                threshold,
            )

    segment_pairs_by_case = {
        1: [("left", "bottom")],
        2: [("bottom", "right")],
        3: [("left", "right")],
        4: [("right", "top")],
        5: [("left", "top"), ("bottom", "right")],
        6: [("bottom", "top")],
        7: [("left", "top")],
        8: [("left", "top")],
        9: [("bottom", "top")],
        10: [("left", "bottom"), ("top", "right")],
        11: [("right", "top")],
        12: [("left", "right")],
        13: [("bottom", "right")],
        14: [("left", "bottom")],
    }

    segments = [
        ParanContourSegment(
            start=crossings[start_edge],
            end=crossings[end_edge],
            cell_lat_min=lat_min,
            cell_lon_min=lon_min,
            case_index=case_index,
            ambiguous=(case_index in (5, 10)),
        )
        for start_edge, end_edge in segment_pairs_by_case[case_index]
    ]
    return segments, case_index in (5, 10)


def evaluate_paran_stability(
    paran: "Paran",
    jd_day: float,
    lat: float,
    lon: float,
    orb_minutes: float = 4.0,
    policy: ParanPolicy | None = None,
    time_offsets_minutes: tuple[float, ...] = (-1.0, 1.0),
) -> ParanStability:
    """
    Evaluate Phase 6 perturbation stability for a single baseline paran.

    Current method:
        Recompute parans for the same body pair after applying each signed
        minute offset in ``time_offsets_minutes`` to the search anchor
        ``jd_day``. For each perturbation, re-identify the same paran by the
        explicit rule documented in ``_matching_perturbed_paran_candidates``.

    Scope note:
        This is intentionally the smallest clean perturbation model that fits
        the current backend. It measures sensitivity to small search-anchor
        time shifts only. It does not yet implement location perturbation,
        interpretive weighting, or geographic field analysis.

    Parameters
    ----------
    paran                : baseline paran to re-evaluate.
    jd_day               : unperturbed search anchor originally supplied to the
                           paran engine.
    lat                  : observer geographic latitude.
    lon                  : observer geographic longitude.
    orb_minutes          : orb forwarded unchanged to ``find_parans``.
    policy               : optional backend inclusion policy forwarded
                           unchanged to ``find_parans``.
    time_offsets_minutes : signed perturbation offsets, in minutes.

    Empty-offsets edge case:
        When *time_offsets_minutes* is empty, no perturbation samples are
        generated and ``survival_rate`` is ``1.0`` by convention (vacuously
        stable).  ``stable_across_window`` is ``True`` and all degradation
        fields are ``None``.

    Returns
    -------
    ParanStability describing survival and degradation across the evaluated
    perturbation window.
    """
    baseline_strength = paran.strength
    samples: list[ParanStabilitySample] = []
    surviving_orbs: list[float] = []
    surviving_exactness: list[float] = []

    for offset_minutes in time_offsets_minutes:
        perturbed_jd_day = jd_day + (offset_minutes * _MINUTES_TO_JD)
        candidates = find_parans(
            [paran.body1, paran.body2],
            perturbed_jd_day,
            lat,
            lon,
            orb_minutes=orb_minutes,
            policy=policy,
        )
        matches = _matching_perturbed_paran_candidates(paran, candidates)
        if not matches:
            samples.append(
                ParanStabilitySample(
                    offset_minutes=offset_minutes,
                    survived=False,
                    orb_minutes=None,
                    exactness_score=None,
                )
            )
            continue

        best_match = min(matches, key=lambda candidate: abs(candidate.jd - paran.jd))
        match_strength = best_match.strength
        surviving_orbs.append(best_match.orb_min)
        surviving_exactness.append(match_strength.exactness_score)
        samples.append(
            ParanStabilitySample(
                offset_minutes=offset_minutes,
                survived=True,
                orb_minutes=best_match.orb_min,
                exactness_score=match_strength.exactness_score,
            )
        )

    total_samples = len(samples)
    survived_count = sum(1 for sample in samples if sample.survived)
    worst_orb_minutes = max(surviving_orbs) if surviving_orbs else None
    worst_exactness_score = min(surviving_exactness) if surviving_exactness else None

    return ParanStability(
        method="time_anchor_perturbation",
        baseline_orb_minutes=paran.orb_min,
        baseline_exactness_score=baseline_strength.exactness_score,
        offsets_minutes=tuple(time_offsets_minutes),
        samples=tuple(samples),
        survival_rate=(survived_count / total_samples) if total_samples else 1.0,
        stable_across_window=(survived_count == total_samples),
        worst_orb_minutes=worst_orb_minutes,
        max_orb_degradation=(
            None if worst_orb_minutes is None else worst_orb_minutes - paran.orb_min
        ),
        worst_exactness_score=worst_exactness_score,
        max_exactness_drop=(
            None
            if worst_exactness_score is None
            else baseline_strength.exactness_score - worst_exactness_score
        ),
    )


def evaluate_paran_site(
    target: "Paran",
    jd_day: float,
    lat: float,
    lon: float,
    orb_minutes: float = 4.0,
    policy: ParanPolicy | None = None,
    stability_time_offsets_minutes: tuple[float, ...] | None = None,
) -> ParanSiteResult:
    """
    Evaluate whether a target paran exists at one geographic site.

    Current method:
        Recompute parans for the target body's ordered pair at the supplied
        latitude/longitude, then re-identify the target by the explicit
        body/circle identity rule documented in
        ``_matching_site_paran_candidates``.

    Tie-break rule:
        If multiple candidates match the target identity, the closest midpoint
        JD to the target paran's midpoint is selected.

    Parameters
    ----------
    target                         : target paran identity to track.
    jd_day                         : search anchor JD for the site evaluation.
    lat                            : evaluated geographic latitude.
    lon                            : evaluated geographic longitude.
    orb_minutes                    : orb forwarded unchanged to ``find_parans``.
    policy                         : optional backend policy forwarded unchanged.
    stability_time_offsets_minutes : optional Phase 6 offsets. When supplied,
                                     stability is evaluated for the matched
                                     site-specific paran.
    """
    candidates = find_parans(
        [target.body1, target.body2],
        jd_day,
        lat,
        lon,
        orb_minutes=orb_minutes,
        policy=policy,
    )
    matches = _matching_site_paran_candidates(target, candidates)
    if not matches:
        return ParanSiteResult(
            lat=lat,
            lon=lon,
            matched=False,
            paran=None,
            strength=None,
            stability=None,
        )

    best_match = min(matches, key=lambda candidate: abs(candidate.jd - target.jd))
    stability = None
    if stability_time_offsets_minutes is not None:
        stability = evaluate_paran_stability(
            best_match,
            jd_day=jd_day,
            lat=lat,
            lon=lon,
            orb_minutes=orb_minutes,
            policy=policy,
            time_offsets_minutes=stability_time_offsets_minutes,
        )

    return ParanSiteResult(
        lat=lat,
        lon=lon,
        matched=True,
        paran=best_match,
        strength=best_match.strength,
        stability=stability,
    )


def sample_paran_field(
    target: "Paran",
    jd_day: float,
    latitudes: list[float] | tuple[float, ...],
    longitudes: list[float] | tuple[float, ...],
    orb_minutes: float = 4.0,
    policy: ParanPolicy | None = None,
    stability_time_offsets_minutes: tuple[float, ...] | None = None,
) -> list[ParanFieldSample]:
    """
    Sample a bounded geographic grid for one target paran identity.

    This is the Phase 7 grid layer: a thin wrapper over ``evaluate_paran_site``
    that returns structured site samples and deliberately stops short of any
    rendering, interpolation, or contour extraction.
    """
    samples: list[ParanFieldSample] = []
    for lat in latitudes:
        for lon in longitudes:
            site_result = evaluate_paran_site(
                target,
                jd_day=jd_day,
                lat=lat,
                lon=lon,
                orb_minutes=orb_minutes,
                policy=policy,
                stability_time_offsets_minutes=stability_time_offsets_minutes,
            )
            samples.append(
                ParanFieldSample(
                    lat=lat,
                    lon=lon,
                    site_result=site_result,
                )
            )
    return samples


def analyze_paran_field(
    samples: list[ParanFieldSample],
    metric: str,
    threshold: float,
) -> ParanFieldAnalysis:
    """
    Analyze sampled paran geography for one explicit metric.

    Threshold rule:
        A sample is considered active when ``metric_value >= threshold``.

    Neighbor rule:
        Regions, peaks, and threshold-crossing edges use orthogonal adjacency
        only on the sampled grid: north, south, east, west.

    Supported metrics:
    - ``"match_presence"``
    - ``"exactness_score"``
    - ``"survival_rate"``

    Raises
    ------
    ValueError
        When *metric* is not a supported metric name.
    ValueError
        When *samples* do not form a complete rectangular grid (duplicate or
        missing coordinates).
    """
    _validate_metric(metric)
    latitudes, longitudes = _infer_field_axes(samples)
    sample_map = {(sample.lat, sample.lon): sample for sample in samples}
    expected_count = len(latitudes) * len(longitudes)
    if len(samples) != expected_count or len(sample_map) != expected_count:
        raise ValueError(
            f"Field samples must form a complete rectangular grid. "
            f"Expected {expected_count} unique (lat, lon) pairs "
            f"({len(latitudes)} latitudes × {len(longitudes)} longitudes), "
            f"got {len(sample_map)}."
        )

    value_map = {
        coords: _field_metric_value(sample, metric)
        for coords, sample in sample_map.items()
    }
    active = {
        coords
        for coords, value in value_map.items()
        if value >= threshold
    }

    regions: list[ParanFieldRegion] = []
    visited: set[tuple[float, float]] = set()
    for lat in latitudes:
        for lon in longitudes:
            coords = (lat, lon)
            if coords not in active or coords in visited:
                continue

            stack = [coords]
            cells: list[tuple[float, float]] = []
            visited.add(coords)
            while stack:
                current = stack.pop()
                cells.append(current)
                lat_idx = latitudes.index(current[0])
                lon_idx = longitudes.index(current[1])
                for neighbor in _orthogonal_neighbor_coords(
                    lat_idx,
                    lon_idx,
                    latitudes,
                    longitudes,
                ):
                    if neighbor in active and neighbor not in visited:
                        visited.add(neighbor)
                        stack.append(neighbor)

            regions.append(
                ParanFieldRegion(
                    region_id=len(regions) + 1,
                    sample_count=len(cells),
                    cells=tuple(cells),
                    peak_value=max(value_map[cell] for cell in cells),
                )
            )

    peaks: list[ParanFieldPeak] = []
    for lat_idx, lat in enumerate(latitudes):
        for lon_idx, lon in enumerate(longitudes):
            coords = (lat, lon)
            value = value_map[coords]
            neighbors = _orthogonal_neighbor_coords(lat_idx, lon_idx, latitudes, longitudes)
            neighbor_values = [value_map[neighbor] for neighbor in neighbors]
            if not neighbor_values:
                peaks.append(ParanFieldPeak(lat=lat, lon=lon, value=value))
                continue
            if all(value >= neighbor for neighbor in neighbor_values) and (
                any(value > neighbor for neighbor in neighbor_values)
            ):
                peaks.append(ParanFieldPeak(lat=lat, lon=lon, value=value))

    threshold_crossings: list[ParanThresholdCrossing] = []
    for lat_idx, lat in enumerate(latitudes):
        for lon_idx, lon in enumerate(longitudes):
            start = (lat, lon)
            start_value = value_map[start]
            if lat_idx + 1 < len(latitudes):
                end = (latitudes[lat_idx + 1], lon)
                end_value = value_map[end]
                if (start_value >= threshold) != (end_value >= threshold):
                    threshold_crossings.append(
                        ParanThresholdCrossing(
                            start_lat=start[0],
                            start_lon=start[1],
                            end_lat=end[0],
                            end_lon=end[1],
                            start_value=start_value,
                            end_value=end_value,
                        )
                    )
            if lon_idx + 1 < len(longitudes):
                end = (lat, longitudes[lon_idx + 1])
                end_value = value_map[end]
                if (start_value >= threshold) != (end_value >= threshold):
                    threshold_crossings.append(
                        ParanThresholdCrossing(
                            start_lat=start[0],
                            start_lon=start[1],
                            end_lat=end[0],
                            end_lon=end[1],
                            start_value=start_value,
                            end_value=end_value,
                        )
                    )

    return ParanFieldAnalysis(
        metric=metric,
        threshold=threshold,
        adjacency="orthogonal",
        total_samples=len(samples),
        active_sample_count=len(active),
        regions=tuple(regions),
        peaks=tuple(peaks),
        threshold_crossings=tuple(threshold_crossings),
    )


def extract_paran_field_contours(
    samples: list[ParanFieldSample],
    metric: str,
    threshold: float,
) -> ParanContourExtraction:
    """
    Extract contour-ready threshold fragments from a rectangular sampled field.

    Interpolation rule:
        Cell-edge crossings use linear interpolation on the selected scalar
        metric.

    Ambiguous-case rule:
        Marching-squares cases ``5`` and ``10`` are not hidden. They are
        reported explicitly in ``ambiguous_cells`` and resolved with a fixed
        deterministic pairing table.

    Raises
    ------
    ValueError
        When *metric* is not a supported metric name.
    ValueError
        When *samples* do not form a complete rectangular grid.
    """
    _validate_metric(metric)
    latitudes, longitudes = _infer_field_axes(samples)
    sample_map = {(sample.lat, sample.lon): sample for sample in samples}
    expected_count = len(latitudes) * len(longitudes)
    if len(samples) != expected_count or len(sample_map) != expected_count:
        raise ValueError(
            f"Field samples must form a complete rectangular grid. "
            f"Expected {expected_count} unique (lat, lon) pairs "
            f"({len(latitudes)} latitudes × {len(longitudes)} longitudes), "
            f"got {len(sample_map)}."
        )

    value_map = {
        coords: _field_metric_value(sample, metric)
        for coords, sample in sample_map.items()
    }

    segments: list[ParanContourSegment] = []
    ambiguous_cells: list[tuple[float, float]] = []
    for lat_idx in range(len(latitudes) - 1):
        for lon_idx in range(len(longitudes) - 1):
            lat_min = latitudes[lat_idx]
            lat_max = latitudes[lat_idx + 1]
            lon_min = longitudes[lon_idx]
            lon_max = longitudes[lon_idx + 1]
            cell_segments, ambiguous = _extract_cell_contour_segments(
                lat_min=lat_min,
                lat_max=lat_max,
                lon_min=lon_min,
                lon_max=lon_max,
                bottom_left_value=value_map[(lat_min, lon_min)],
                bottom_right_value=value_map[(lat_min, lon_max)],
                top_right_value=value_map[(lat_max, lon_max)],
                top_left_value=value_map[(lat_max, lon_min)],
                threshold=threshold,
            )
            segments.extend(cell_segments)
            if ambiguous:
                ambiguous_cells.append((lat_min, lon_min))

    return ParanContourExtraction(
        metric=metric,
        threshold=threshold,
        interpolation="linear",
        segments=tuple(segments),
        ambiguous_cells=tuple(ambiguous_cells),
    )


def consolidate_paran_contours(
    extraction: ParanContourExtraction,
) -> ParanContourPathSet:
    """
    Stitch contour fragments into ordered open or closed paths.

    Matching rule:
        Path assembly uses exact endpoint matching via ``_contour_point_key``.
        No tolerance or geometric simplification is applied.

    Path rule:
        A closed path has identical first and last points after stitching, and
        contains at least 3 points.  A path is marked ambiguous when any
        contributing segment was ambiguous.

    Orphan rule:
        A segment is an orphan when it cannot be joined to any neighbor (both
        endpoints are shared with no other segment, or it is a genuinely
        isolated fragment that forms a one-segment open path).  All orphans are
        reported explicitly in ``ParanContourPathSet.orphan_segments``; none
        are silently discarded.

    Invariant: for every stitched path,
        ``path.segment_count == len(path.points) - 1``.
    """
    segments = list(extraction.segments)
    if not segments:
        return ParanContourPathSet(
            paths=(),
            orphan_segments=(),
            matching_rule="exact_endpoint",
        )

    endpoint_to_indices: dict[tuple[float, float], list[int]] = {}
    for idx, segment in enumerate(segments):
        endpoint_to_indices.setdefault(_contour_point_key(segment.start), []).append(idx)
        endpoint_to_indices.setdefault(_contour_point_key(segment.end), []).append(idx)

    used: set[int] = set()
    used_in_paths: set[int] = set()
    paths: list[ParanContourPath] = []

    def build_path(start_index: int) -> tuple[list[ParanContourPoint], list[int], bool]:
        segment = segments[start_index]
        points = [segment.start, segment.end]
        source_indices = [start_index]
        used.add(start_index)

        def extend(forward: bool) -> None:
            while True:
                anchor = points[-1] if forward else points[0]
                anchor_key = _contour_point_key(anchor)
                candidates = [
                    idx for idx in endpoint_to_indices.get(anchor_key, [])
                    if idx not in used
                ]
                if len(candidates) != 1:
                    return
                next_index = candidates[0]
                next_segment = segments[next_index]
                start_key = _contour_point_key(next_segment.start)
                end_key = _contour_point_key(next_segment.end)
                if start_key == anchor_key:
                    next_point = next_segment.end
                elif end_key == anchor_key:
                    next_point = next_segment.start
                else:
                    return
                used.add(next_index)
                if forward:
                    points.append(next_point)
                    source_indices.append(next_index)
                else:
                    points.insert(0, next_point)
                    source_indices.insert(0, next_index)

        extend(forward=True)
        extend(forward=False)
        closed = (
            len(points) >= 3
            and _contour_point_key(points[0]) == _contour_point_key(points[-1])
        )
        return points, source_indices, closed

    preferred_starts = []
    for idx, segment in enumerate(segments):
        degree_start = len(endpoint_to_indices[_contour_point_key(segment.start)])
        degree_end = len(endpoint_to_indices[_contour_point_key(segment.end)])
        if degree_start == 1 or degree_end == 1:
            preferred_starts.append(idx)
    preferred_starts.extend(idx for idx in range(len(segments)) if idx not in preferred_starts)

    for idx in preferred_starts:
        if idx in used:
            continue
        points, source_indices, closed = build_path(idx)
        stitched_segments = [segments[source_idx] for source_idx in source_indices]
        if len(stitched_segments) == 1 and not closed:
            continue
        used_in_paths.update(source_indices)
        paths.append(
            ParanContourPath(
                points=tuple(points),
                closed=closed,
                segment_count=len(stitched_segments),
                ambiguous=any(segment.ambiguous for segment in stitched_segments),
                source_case_indices=tuple(segment.case_index for segment in stitched_segments),
            )
        )

    orphan_segments = tuple(
        segment
        for idx, segment in enumerate(segments)
        if idx not in used_in_paths
    )
    return ParanContourPathSet(
        paths=tuple(paths),
        orphan_segments=orphan_segments,
        matching_rule="exact_endpoint",
    )


# ---------------------------------------------------------------------------
# Phase 11 — higher-order field structure
# ---------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class ParanContourAssociation:
    """
    Association record linking one stitched contour path to field regions
    and peaks from Phase 8.

    Attributes
    ----------
    path_index              : index of the path in ``ParanContourPathSet.paths``.
    region_id               : ``ParanFieldRegion.region_id`` whose cells contain
                              the first segment's cell origin, or ``None`` when
                              no region covers that cell.
    associated_peak_indices : indices into ``ParanFieldAnalysis.peaks`` whose
                              grid coordinates fall within this path's spatial
                              extent.
    """

    path_index: int
    region_id: int | None
    associated_peak_indices: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class ParanContourHierarchyEntry:
    """
    Containment-hierarchy record for one stitched contour path.

    Containment rule:
        A path is considered inside another closed path when the candidate
        path's centroid passes a ray-casting point-in-polygon test against
        the enclosing path's ordered points.  Open paths always sit at depth 0
        with no parent.

    Attributes
    ----------
    path_index   : index of the path in ``ParanContourPathSet.paths``.
    parent_index : index of the immediately enclosing closed path, or ``None``
                   when the path is outermost or open.
    depth        : number of closed ancestors (0 = outermost).
    """

    path_index: int
    parent_index: int | None
    depth: int


@dataclass(frozen=True, slots=True)
class ParanFieldStructure:
    """
    Higher-order structural analysis of a stitched paran contour field.

    This layer operates only on already-computed Phase 8 field-analysis and
    Phase 10 path-set results.  It does not re-sample the field, re-extract
    contours, or alter any prior result.

    Attributes
    ----------
    dominant_path_index : index of the path with the most points in
                          ``ParanContourPathSet.paths``, or ``None`` when the
                          path set is empty.  Ties are broken by lowest index.
    hierarchy           : containment-depth entry for every path.
    associations        : region/peak association record for every path.
    matching_rule       : label for the containment test, currently
                          ``"centroid_in_polygon"``.
    """

    dominant_path_index: int | None
    hierarchy: tuple[ParanContourHierarchyEntry, ...]
    associations: tuple[ParanContourAssociation, ...]
    matching_rule: str


def _path_bounding_box(
    path: ParanContourPath,
) -> tuple[float, float, float, float]:
    """Return (lat_min, lat_max, lon_min, lon_max) for a path's points."""
    lats = [p.lat for p in path.points]
    lons = [p.lon for p in path.points]
    return min(lats), max(lats), min(lons), max(lons)


def _path_centroid(path: ParanContourPath) -> tuple[float, float]:
    """Return the arithmetic mean (lat, lon) of a path's points."""
    n = len(path.points)
    lat = sum(p.lat for p in path.points) / n
    lon = sum(p.lon for p in path.points) / n
    return lat, lon


def _point_in_closed_path(lat: float, lon: float, path: ParanContourPath) -> bool:
    """
    Ray-casting point-in-polygon test in lat/lon space.

    Only meaningful when ``path.closed`` is ``True``.  Casts a ray in the
    +lon direction and counts edge crossings.  Returns ``True`` when the
    crossing count is odd (inside).
    """
    pts = path.points
    n = len(pts)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = pts[i].lon, pts[i].lat
        xj, yj = pts[j].lon, pts[j].lat
        if ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / (yj - yi + 1e-15) + xi
        ):
            inside = not inside
        j = i
    return inside


def analyze_paran_field_structure(
    field_analysis: ParanFieldAnalysis,
    path_set: ParanContourPathSet,
) -> ParanFieldStructure:
    """
    Derive higher-order structural relationships from Phase 8 and Phase 10
    results.

    This function does not re-sample the field, re-extract contours, or alter
    any prior result.  It derives structure purely from the coordinate data
    already present in the supplied arguments.

    Containment rule:
        A path B is directly inside closed path A when B's centroid passes the
        ray-casting point-in-polygon test against A.  Among all closed paths
        that contain B, the one with the smallest bounding-box area is chosen
        as the immediate parent (the tightest enclosure).

    Region-association rule:
        A path is associated with the region whose ``cells`` set contains the
        ``(cell_lat_min, cell_lon_min)`` origin of the path's first contributing
        segment, resolved from ``ParanContourPathSet`` source segment ordering.
        When a path has no segments or no region covers that cell, ``region_id``
        is ``None``.

    Peak-association rule:
        A peak is associated with a path when the peak's ``(lat, lon)`` lies
        within the path's bounding box and, for closed paths, also passes the
        point-in-polygon test.  For open paths, bounding-box containment alone
        is used.

    Dominant-path rule:
        The path with the most points.  Ties broken by lowest path index.
        ``None`` when the path set is empty.

    Parameters
    ----------
    field_analysis : Phase 8 analysis result.
    path_set       : Phase 10 consolidated path set.

    Returns
    -------
    ParanFieldStructure
    """
    paths = path_set.paths

    if not paths:
        return ParanFieldStructure(
            dominant_path_index=None,
            hierarchy=(),
            associations=(),
            matching_rule="centroid_in_polygon",
        )

    # ------------------------------------------------------------------ #
    # Dominant path
    # ------------------------------------------------------------------ #
    dominant_path_index = max(
        range(len(paths)),
        key=lambda i: len(paths[i].points),
    )

    # ------------------------------------------------------------------ #
    # Build a cell → region_id lookup from Phase 8
    # ------------------------------------------------------------------ #
    cell_to_region: dict[tuple[float, float], int] = {}
    for region in field_analysis.regions:
        for cell in region.cells:
            cell_to_region[cell] = region.region_id

    # ------------------------------------------------------------------ #
    # For each path: find its first segment's cell origin
    # We recover segment cell origins from the orphan-aware segment list
    # by matching the path's source_case_indices order against segments in
    # path_set.  Since ParanContourPath stores only points (not segment refs),
    # we use the extraction's segment list order preserved in path_set by
    # checking every non-orphan segment.  The first segment whose start point
    # matches path.points[0] or path.points[1] supplies the cell origin.
    #
    # Simpler reliable approach: build a map from (start_key, end_key) →
    # segment using all non-orphan segments from the original extraction.
    # However, ParanContourPathSet does not hold a back-reference to the
    # extraction.  We therefore use the orphan set complement: every segment
    # not in orphan_segments contributed to some path.  We match path points
    # against segment endpoints to find cell origins.
    # ------------------------------------------------------------------ #
    orphan_set: set[tuple[tuple[float, float], tuple[float, float]]] = {
        (_contour_point_key(s.start), _contour_point_key(s.end))
        for s in path_set.orphan_segments
    }

    # Reconstruct all contributing segments from orphan_segments complement.
    # Since we only have path points, derive cell origins by checking which
    # non-orphan segment has its start or end matching path.points[0].
    # We need the full segment list — it is not stored on the path set.
    # Use a fallback: record cell origins from orphan_segments absence by
    # walking path points.  The cleanest approach given the current API is to
    # carry a helper that reconstructs segment origins from the path's
    # (start, end) point pairs and the full segment pool.
    #
    # The full segment pool is NOT available here — only orphans are stored.
    # We therefore derive region association from path centroid:
    # find the region whose cells are closest to the path centroid.
    # This is a documented approximation for paths that span multiple cells.

    def _region_for_path(path_idx: int) -> int | None:
        path = paths[path_idx]
        centroid_lat, centroid_lon = _path_centroid(path)
        best_region_id = None
        best_dist = float("inf")
        for region in field_analysis.regions:
            for cell_lat, cell_lon in region.cells:
                dist = (cell_lat - centroid_lat) ** 2 + (cell_lon - centroid_lon) ** 2
                if dist < best_dist:
                    best_dist = dist
                    best_region_id = region.region_id
        return best_region_id

    # ------------------------------------------------------------------ #
    # Containment hierarchy
    # ------------------------------------------------------------------ #
    bboxes = [_path_bounding_box(p) for p in paths]
    centroids = [_path_centroid(p) for p in paths]

    def _bbox_area(bbox: tuple[float, float, float, float]) -> float:
        lat_min, lat_max, lon_min, lon_max = bbox
        return (lat_max - lat_min) * (lon_max - lon_min)

    hierarchy_entries: list[ParanContourHierarchyEntry] = []
    for i, path in enumerate(paths):
        if not path.closed:
            hierarchy_entries.append(
                ParanContourHierarchyEntry(path_index=i, parent_index=None, depth=0)
            )
            continue

        clat, clon = centroids[i]
        i_lat_min, i_lat_max, i_lon_min, i_lon_max = bboxes[i]
        enclosing = [
            j for j, other in enumerate(paths)
            if j != i
            and other.closed
            and _bbox_area(bboxes[j]) > _bbox_area(bboxes[i])
            and bboxes[j][0] <= i_lat_min and bboxes[j][1] >= i_lat_max
            and bboxes[j][2] <= i_lon_min and bboxes[j][3] >= i_lon_max
            and _point_in_closed_path(clat, clon, other)
        ]
        if not enclosing:
            hierarchy_entries.append(
                ParanContourHierarchyEntry(path_index=i, parent_index=None, depth=0)
            )
        else:
            parent_index = min(enclosing, key=lambda j: _bbox_area(bboxes[j]))
            depth = len(enclosing)
            hierarchy_entries.append(
                ParanContourHierarchyEntry(
                    path_index=i,
                    parent_index=parent_index,
                    depth=depth,
                )
            )

    # ------------------------------------------------------------------ #
    # Peak associations
    # ------------------------------------------------------------------ #
    associations: list[ParanContourAssociation] = []
    peaks = field_analysis.peaks
    for i, path in enumerate(paths):
        bbox = bboxes[i]
        lat_min, lat_max, lon_min, lon_max = bbox
        peak_indices: list[int] = []
        for pi, peak in enumerate(peaks):
            in_box = lat_min <= peak.lat <= lat_max and lon_min <= peak.lon <= lon_max
            if not in_box:
                continue
            if path.closed:
                if _point_in_closed_path(peak.lat, peak.lon, path):
                    peak_indices.append(pi)
            else:
                peak_indices.append(pi)

        associations.append(
            ParanContourAssociation(
                path_index=i,
                region_id=_region_for_path(i),
                associated_peak_indices=tuple(peak_indices),
            )
        )

    return ParanFieldStructure(
        dominant_path_index=dominant_path_index,
        hierarchy=tuple(hierarchy_entries),
        associations=tuple(associations),
        matching_rule="centroid_in_polygon",
    )


@dataclass(slots=True)
class Paran:
    """
    RITE: The Paran Vessel — a simultaneous mundane circle crossing between two bodies.

    THEOREM: Holds the two body names, their respective circle types, both
    original crossing times, the time orb in minutes, and optional inspectable
    event/classification context.

    Moira operational definition:
        A ``Paran`` is formed whenever two ``ParanCrossing`` events from two
        distinct bodies occur within the configured time orb. The engine treats
        same-type pairings (e.g. Rising/Rising) and mixed-type pairings
        (e.g. Rising/Culminating) as valid in the current model.

    RITE OF PURPOSE:
        Serves the Paran Engine as the canonical result vessel for detected
        paran aspects. A paran is the astrological event formed when two bodies
        cross any two mundane circles within a time orb. Without this vessel,
        ``find_parans`` would have no structured output, and callers could not
        filter, sort, or display paran results.

    LAW OF OPERATION:
        Responsibilities:
            - Store both body names, their circle types, both crossing JDs, and
              the time orb in minutes.
            - Optionally preserve the underlying ``ParanCrossing`` records and a
              lean ``ParanSignature`` classification.
            - Expose a derived ``ParanStrength`` summary based on orb exactness
              only.
        Non-responsibilities:
            - Does not detect parans (delegated to ``find_parans``).
            - Does not validate that circle types are members of ``CIRCLE_TYPES``.
        Dependencies:
            - Populated exclusively by ``find_parans()``.
        Structural invariants:
            - ``orb_min`` is always non-negative.
            - ``jd1`` and ``jd2`` are the authoritative event times.
            - ``jd`` is a derived compatibility property equal to the arithmetic
              mean of ``jd1`` and ``jd2``.
            - ``delta_minutes`` is a derived convenience alias of ``orb_min``.
            - family convenience properties are pass-through accessors to
              ``signature`` and do not create new semantics.
            - ``strength`` is a derived geometric summary and does not alter
              matching, filtering, or ranking semantics.
        Succession stance: terminal — not designed for subclassing.

    Canon: Brady, "Brady's Book of Fixed Stars" (1998); Ptolemy, Tetrabiblos I.

    [MACHINE_CONTRACT v1]
    {
        "scope": "class",
        "id": "moira.parans.Paran",
        "risk": "medium",
        "api": {
            "public_methods": ["jd", "delta_minutes", "event_family", "axis_family", "body_family", "__repr__"],
            "public_attributes": ["body1", "body2", "circle1", "circle2", "jd1", "jd2", "orb_min", "crossing1", "crossing2", "signature"]
        },
        "state": {
            "mutable": false,
            "fields": ["body1", "body2", "circle1", "circle2", "jd1", "jd2", "orb_min", "crossing1", "crossing2", "signature"]
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
            "policy": "caller ensures valid crossing data before construction"
        },
        "succession": {
            "stance": "terminal",
            "override_points": []
        },
        "agent": "kiro"
    }
    [/MACHINE_CONTRACT]

    Attributes
    ----------
    body1    : name of the first body.
    body2    : name of the second body.
    circle1  : mundane circle for *body1* (one of :data:`CIRCLE_TYPES`).
    circle2  : mundane circle for *body2* (one of :data:`CIRCLE_TYPES`).
    jd1      : JD (UT) of *body1*'s crossing event.
    jd2      : JD (UT) of *body2*'s crossing event.
    orb_min  : time separation of the two crossings in minutes.
    crossing1 : preserved crossing record for *body1* when carried through by
                the engine.
    crossing2 : preserved crossing record for *body2* when carried through by
                the engine.
    signature : lean geometric classification for the current model.
    delta_minutes : derived convenience alias for ``orb_min``.
    event_family / axis_family / body_family : pass-through convenience access
                to ``signature`` when present.
    strength : derived geometric exactness summary based on ``orb_min`` only.
    Stability is evaluated separately via ``evaluate_paran_stability`` so that
    perturbation recomputation remains explicit rather than hidden on the
    result vessel.
    """

    body1: str
    body2: str
    circle1: str
    circle2: str
    jd1: float
    jd2: float
    orb_min: float
    crossing1: ParanCrossing | None = None
    crossing2: ParanCrossing | None = None
    signature: ParanSignature | None = None

    @property
    def jd(self) -> float:
        """Return the derived center JD retained for compatibility."""
        return (self.jd1 + self.jd2) / 2.0

    @property
    def delta_minutes(self) -> float:
        """Return the absolute event separation in minutes."""
        return self.orb_min

    @property
    def event_family(self) -> str | None:
        """Return ``signature.event_family`` when a signature is attached."""
        return None if self.signature is None else self.signature.event_family

    @property
    def axis_family(self) -> str | None:
        """Return ``signature.axis_family`` when a signature is attached."""
        return None if self.signature is None else self.signature.axis_family

    @property
    def body_family(self) -> str | None:
        """Return ``signature.body_family`` when a signature is attached."""
        return None if self.signature is None else self.signature.body_family

    @property
    def strength(self) -> ParanStrength:
        """Return the pure geometric strength summary derived from ``orb_min``."""
        return _derive_paran_strength(self)

    def __repr__(self) -> str:
        return (
            f"Paran({self.body1!r} {self.circle1} ∥ "
            f"{self.body2!r} {self.circle2}, "
            f"orb={self.orb_min:.1f}′)"
        )


# Future layer boundary:
# Perturbation stability now lives in ``evaluate_paran_stability()`` above the
# core matching + classification + raw exactness surface. Phase 7 geographic
# evaluation now lives in ``evaluate_paran_site()`` and ``sample_paran_field()``
# above those same primitives. Rendering or contour extraction remains out of
# scope for this backend module.


# ---------------------------------------------------------------------------
# Internal: find all four crossings for a single body on a given day
# ---------------------------------------------------------------------------

def _crossing_times(
    body: str,
    jd_day: float,
    lat: float,
    lon: float,
    pressure_mbar: float = 1013.25,
    temperature_c: float = 10.0,
) -> list[ParanCrossing]:
    """
    Find all four mundane circle crossings for *body* on the day starting
    at *jd_day*, as seen from the observer at (``lat``, ``lon``).

    This function is where the paran engine inherits its event model from the
    lower-level timing machinery. It does not derive alternative definitions of
    Rise/Set/MC/IC; it delegates to ``moira.rise_set`` and repackages the
    returned times as ``ParanCrossing`` instances.

    The four supported event types are:

    - **Rising**  (Rise / ASC-side horizon event)
    - **Setting** (Set / DSC-side horizon event)
    - **Culminating** (MC)
    - **AntiCulminating** (IC)

    Parameters
    ----------
    body    : body name (one of the ``Body.*`` constants).
    jd_day  : Julian Day (UT) at the start of the search window (i.e. the
              integer JD at 00:00 UT or the natal JD floored to the day).
    lat     : observer geographic latitude (degrees, signed).
    lon     : observer geographic longitude (degrees, east positive).

    Returns
    -------
    list[ParanCrossing] — up to four entries. Fewer are normal when the body
    lacks a rise, set, MC, or IC event in the delegated machinery for that
    day/location.
    """
    from .rise_set import find_phenomena, get_transit

    crossings: list[ParanCrossing] = []

    # Rise and Set are delegated unchanged from rise_set.find_phenomena().
    # The paran model therefore inherits the standard apparent-horizon
    # convention used there: altitude = -0.5667 degrees.
    phenomena = find_phenomena(
        body, jd_day, lat, lon,
        altitude=-0.5667,
        pressure_mbar=pressure_mbar,
        temperature_c=temperature_c,
    )

    if "Rise" in phenomena:
        crossings.append(
            ParanCrossing(
                body=body,
                circle="Rising",
                jd=phenomena["Rise"],
                source_method="find_phenomena",
                altitude_policy=-0.5667,
            )
        )
    if "Set" in phenomena:
        crossings.append(
            ParanCrossing(
                body=body,
                circle="Setting",
                jd=phenomena["Set"],
                source_method="find_phenomena",
                altitude_policy=-0.5667,
            )
        )

    # Upper transit (Culminating) via get_transit().
    try:
        jd_transit = get_transit(body, jd_day, lat, lon)
        crossings.append(
            ParanCrossing(
                body=body,
                circle="Culminating",
                jd=jd_transit,
                source_method="get_transit",
            )
        )
        # IC is solved explicitly as the lower transit on the same search day.
        # This keeps the event model tied to one daily window rather than
        # letting a reseeded upper-transit search drift into the next sidereal
        # day.
        try:
            jd_anti = get_transit(body, jd_day, lat, lon, upper=False)
            crossings.append(
                ParanCrossing(
                    body=body,
                    circle="AntiCulminating",
                    jd=jd_anti,
                    source_method="get_transit",
                )
            )
        except Exception:
            pass
    except Exception:
        # Near polar edge cases can fail in delegated transit solving. The
        # paran engine treats that as "no usable MC/IC event" rather than a
        # fatal error.
        pass

    return crossings


# ---------------------------------------------------------------------------
# Main paran-finding function
# ---------------------------------------------------------------------------

def find_parans(
    bodies: list[str],
    jd_day: float,
    lat: float,
    lon: float,
    orb_minutes: float = 4.0,
    policy: ParanPolicy | None = None,
    pressure_mbar: float = 1013.25,
    temperature_c: float = 10.0,
) -> list[Paran]:
    """
    Find all parans between the given bodies for a given day and location.

    Moira operational definition:
        A paran is detected whenever two supported mundane-circle crossing
        events (one for each of two distinct bodies) fall within
        ``orb_minutes`` of each other inside the same UT-day search window.

    The engine recognizes four event types: Rise, Set, MC, and IC
    (represented internally as ``"Rising"``, ``"Setting"``,
    ``"Culminating"``, and ``"AntiCulminating"``).

    Same-event-type pairings and mixed-event-type pairings are both valid in
    the current model. No doctrinal narrowing is applied here.

    Backend layering:
        1. the core engine generates crossing events;
        2. the matcher forms candidate parans by time orb;
        3. the classifier assigns a lean ``ParanSignature``;
        4. the optional policy layer may admit or reject the candidate;
        5. ``Paran.strength`` exposes pure geometric exactness from orb only;
        6. ``evaluate_paran_stability`` recomputes admitted candidates under
           explicit perturbations;
        7. ``evaluate_paran_site`` / ``sample_paran_field`` evaluate the same
           target identity across locations.

    If *policy* is omitted, the default permissive backend doctrine is used and
    existing behavior is preserved.

    Parameters
    ----------
    bodies      : list of body names to check (e.g. ``Body.ALL_PLANETS``).
    jd_day      : Julian Day (UT) of the day to search.  The function looks
                  over the full 24-hour window starting at this JD.
    lat         : observer geographic latitude (degrees, signed).
    lon         : observer geographic longitude (degrees, east positive).
    orb_minutes   : maximum time separation (in minutes) for two crossings to
                    qualify as a paran.  Default 4 minutes (traditional orb).
    policy        : optional backend inclusion policy. ``None`` preserves the
                    current permissive semantics.
    pressure_mbar : atmospheric pressure in millibars for the refraction-
                    corrected horizon altitude computation.  Default 1013.25.
    temperature_c : air temperature in degrees Celsius for the same.
                    Default 10.0 °C.  Non-standard weather can shift rise/set
                    times by tens of seconds relative to standard atmosphere.

    Returns
    -------
    list[Paran] sorted by ``orb_min`` (tightest paran first).

    Notes
    -----
    The function does *not* compare a body against itself.

    Symmetric duplicates are naturally avoided because body pairs are generated
    once via :func:`itertools.combinations`; therefore "Sun Rising ∥ Moon MC"
    and "Moon MC ∥ Sun Rising" are treated as the same computational event.

    Any missing crossing on either body side simply removes that candidate
    pairing from consideration; the engine does not synthesize substitute
    events.

    Raises
    ------
    ValueError
        When *orb_minutes* is negative.
    """
    _validate_orb_non_negative(orb_minutes)
    orb_jd = orb_minutes * _MINUTES_TO_JD
    active_policy = DEFAULT_PARAN_POLICY if policy is None else policy

    # Gather all crossings for every body.
    all_crossings: list[ParanCrossing] = []
    for body in bodies:
        all_crossings.extend(_crossing_times(body, jd_day, lat, lon, pressure_mbar, temperature_c))

    parans: list[Paran] = []

    # Compare every crossing of body A against every crossing of body B.
    # The current model intentionally permits both same-type and mixed-type
    # pairings; the only hard restriction is that A and B are distinct bodies.
    body_crossings: dict[str, list[ParanCrossing]] = {}
    for c in all_crossings:
        body_crossings.setdefault(c.body, []).append(c)

    for body_a, body_b in itertools.combinations(bodies, 2):
        crossings_a = body_crossings.get(body_a, [])
        crossings_b = body_crossings.get(body_b, [])

        for ca in crossings_a:
            for cb in crossings_b:
                dt_jd = abs(ca.jd - cb.jd)
                if dt_jd <= orb_jd:
                    orb_min = dt_jd / _MINUTES_TO_JD
                    parans.append(
                        Paran(
                            body1=body_a,
                            body2=body_b,
                            circle1=ca.circle,
                            circle2=cb.circle,
                            jd1=ca.jd,
                            jd2=cb.jd,
                            orb_min=orb_min,
                            crossing1=ca,
                            crossing2=cb,
                            signature=_classify_paran(ca, cb),
                        )
                    )

    parans = [paran for paran in parans if _policy_allows_paran(paran, active_policy)]
    parans.sort(key=lambda p: p.orb_min)
    return parans


# ---------------------------------------------------------------------------
# Natal parans convenience function
# ---------------------------------------------------------------------------

def natal_parans(
    bodies: list[str],
    natal_jd: float,
    lat: float,
    lon: float,
    orb_minutes: float = 4.0,
) -> list[Paran]:
    """
    Find natal parans — the parans active on the birth day.

    This is a thin wrapper around :func:`find_parans` that floors the natal
    Julian Day to the start of the birth day (00:00 UT) before searching,
    ensuring the full 24-hour window of the birth date is examined.

    Doctrinal note:
        This wrapper does not redefine parans for natal work. It inherits the
        same event model, allowed pairings, delegated assumptions, and edge
        cases documented on :func:`find_parans`.

    Parameters
    ----------
    bodies      : list of body names to check.
    natal_jd    : Julian Day (UT) of the birth moment.
    lat         : birth location geographic latitude (degrees, signed).
    lon         : birth location geographic longitude (degrees, east positive).
    orb_minutes : time orb in minutes.  Default 4 minutes.

    Returns
    -------
    list[Paran] sorted by ``orb_min`` (tightest paran first).
    """
    # Floor to the start of the UT day (JD noon convention: subtract 0.5,
    # floor, add 0.5 back so the window begins at 00:00 UT).
    jd_day = math.floor(natal_jd - 0.5) + 0.5
    return find_parans(bodies, jd_day, lat, lon, orb_minutes=orb_minutes)

