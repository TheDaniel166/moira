"""Coverage-aware transits to explicitly frozen Geodetic angle references.

Targets are frozen tropical anchors, even when displayed sidereally. Search
epochs are JD UT1. Apparent body longitudes come from the canonical provider;
there is no orbit propagation, extrapolation, or comet-specific approximation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from collections.abc import Sequence

from .constants import Body, EARTH_ROUTE, NAIF_ROUTES, C_KM_PER_DAY
from .geodetic import GeodeticChart, _circular_delta, geodetic_asc, geodetic_mc
from .geodetic_inputs import _body_identity, _ENGINE_FRAME
from ._fixed_aspect_search import _FixedScanPolicy

__all__ = [
    "GeodeticFixedReference", "GeodeticTimingPolicy", "GeodeticTimingResource",
    "GeodeticTransitPass", "GeodeticOrbWindow", "GeodeticTimingResult",
    "find_geodetic_transits",
]


@dataclass(frozen=True, slots=True)
class GeodeticFixedReference:
    """One location, obliquity, zodiac and reference epoch frozen for timing.

    Sidereal degrees are mapped back with this reference's offset, never
    event-time ayanamsa. The optional TT epoch is retained when actually known.
    """

    chart: GeodeticChart
    reference_jd_ut1: float
    reference_jd_tt: float | None = None
    angles: tuple[str, ...] = ("MC", "IC", "ASC", "DSC")
    target_policy: str = "frozen_tropical_anchor"
    source_frame: str = _ENGINE_FRAME

    def __post_init__(self):
        if not isinstance(self.chart, GeodeticChart):
            raise TypeError("chart must be GeodeticChart")
        if not math.isfinite(self.reference_jd_ut1) or (self.reference_jd_tt is not None and not math.isfinite(self.reference_jd_tt)):
            raise ValueError("reference epochs must be finite")
        if self.target_policy != "frozen_tropical_anchor" or self.source_frame != _ENGINE_FRAME:
            raise ValueError("only frozen tropical anchors in the canonical ecliptic frame are supported")
        if not isinstance(self.angles, tuple) or not self.angles or len(set(self.angles)) != len(self.angles) or any(a not in ("MC", "IC", "ASC", "DSC") for a in self.angles):
            raise ValueError("angles must be a nonempty tuple of unique supported angles")
        expected_mc = geodetic_mc(self.chart.geo_longitude, self.chart.ayanamsa_deg)
        expected_asc = geodetic_asc(self.chart.geo_longitude, self.chart.geo_latitude, self.chart.obliquity, self.chart.ayanamsa_deg)
        if abs(_circular_delta(expected_mc, self.chart.mc)) > 1e-9 or abs(_circular_delta(expected_asc, self.chart.asc)) > 1e-9:
            raise ValueError("reference angles disagree with location geometry")
        provenance = self.chart.provenance
        if provenance is not None and provenance.chart_jd_ut is not None:
            if self.reference_jd_ut1 != provenance.chart_jd_ut:
                raise ValueError("reference epoch disagrees with chart-context provenance")
            if self.reference_jd_tt is None:
                object.__setattr__(self, "reference_jd_tt", provenance.chart_jd_tt)
            elif self.reference_jd_tt != provenance.chart_jd_tt:
                raise ValueError("reference TT disagrees with chart-context provenance")

    @property
    def selected_targets(self):
        """Named angle degrees in the reference's display zodiac."""
        values = {"MC": self.chart.mc, "IC": geodetic_mc(self.chart.mc, -180),
                  "ASC": self.chart.asc, "DSC": geodetic_mc(self.chart.asc, -180)}
        return tuple((name, values[name]) for name in self.angles)

    @property
    def tropical_targets(self):
        """Frozen tropical targets using only the reference ayanamsa."""
        return tuple((name, geodetic_mc(value, -self.chart.ayanamsa_deg)) for name, value in self.selected_targets)


@dataclass(frozen=True, slots=True)
class GeodeticTimingPolicy:
    """Finite scan/solver controls and explicit resource/coverage admission.

    Padding reserves the canonical providers' half-day speed samples plus a
    declared maximum light-time. Each evaluated apparent distance is checked
    against that light-time policy. This is not a trajectory enclosure proof.
    """

    step_days: float
    time_tolerance_days: float = 1e-7
    angular_tolerance_deg: float = 1e-6
    curvature_tolerance_deg: float = .1
    max_evaluations: int = 50000
    max_subdivisions: int = 10000
    max_depth: int = 12
    velocity_step_days: float = .001
    stationary_rate_tolerance: float = 1e-6
    maximum_light_time_days: float = 1.0
    coverage_policy: str = "require_full"

    def __post_init__(self):
        for name in ("step_days", "time_tolerance_days", "angular_tolerance_deg", "curvature_tolerance_deg", "velocity_step_days", "stationary_rate_tolerance", "maximum_light_time_days"):
            if not math.isfinite(getattr(self, name)) or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be finite and positive")
        if self.angular_tolerance_deg >= 1 or self.curvature_tolerance_deg >= 45:
            raise ValueError("angular and curvature tolerances must be below 1 and 45 degrees")
        if self.velocity_step_days > self.step_days / 2:
            raise ValueError("velocity step must not exceed half the scan step")
        for name in ("max_evaluations", "max_subdivisions", "max_depth"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise ValueError(f"{name} must be a positive integer")
        if self.max_depth > 24:
            raise ValueError("max_depth must not exceed 24")
        if self.coverage_policy not in ("require_full", "allow_partial"):
            raise ValueError("coverage_policy must be require_full or allow_partial")

    @property
    def resource_padding_days(self):
        """Speed-sample and light-time reserve in the resource TDB clock."""
        return .5 + self.maximum_light_time_days + 1e-5

    def _scan_policy(self):
        return _FixedScanPolicy(self.step_days, self.time_tolerance_days, self.angular_tolerance_deg,
                                self.curvature_tolerance_deg, self.max_evaluations, self.max_subdivisions,
                                self.max_depth, self.velocity_step_days, self.stationary_rate_tolerance)


@dataclass(frozen=True, slots=True)
class GeodeticTimingResource:
    """An installed candidate resource used to establish actual route coverage."""

    center: int
    target: int
    source_label: str
    source_sha256: str
    catalog_id: str | None
    catalog_version: str | None
    manifest_sha256: str | None
    intervals_tdb: tuple[tuple[float, float], ...]
    segment_boundaries_tdb: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class GeodeticTransitPass:
    """An isolated exact contact with motion, directed branch and orb window."""

    body_id: str
    target: str
    aspect_angle_deg: float
    directed_angle_deg: float
    jd_ut1: float
    motion: str
    residual_deg: float
    window_index: int | None


@dataclass(frozen=True, slots=True)
class GeodeticOrbWindow:
    """A connected orb interval that may contain several exact passages."""

    body_id: str
    target: str
    aspect_angle_deg: float
    orb_deg: float
    covered_start_jd_ut1: float
    covered_end_jd_ut1: float
    entry_jd_ut1: float | None
    exit_jd_ut1: float | None
    entry_status: str
    exit_status: str
    pass_indices: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class GeodeticTimingResult:
    """Immutable timing, provenance, coverage and bounded-search completion."""

    reference: GeodeticFixedReference
    requested_mover: str
    body_id: str
    identity: object | None
    policy: GeodeticTimingPolicy
    requested_interval_jd_ut1: tuple[float, float]
    covered_intervals_jd_ut1: tuple[tuple[float, float], ...]
    gaps_jd_ut1: tuple[tuple[float, float], ...]
    resources: tuple[GeodeticTimingResource, ...]
    events: tuple[GeodeticTransitPass, ...]
    windows: tuple[GeodeticOrbWindow, ...]
    evaluations: int
    subdivisions: int
    complete: bool
    status: str
    reasons: tuple[str, ...]
    scanned_intervals_jd_ut1: tuple[tuple[float, float], ...]
    ephemeris_clock: object
    timescale: str = "JD_UT1"
    longitude_frame: str = _ENGINE_FRAME
    correction_regime: str = "canonical_planet_at_apparent_default"
    completeness: str = "declared_finite_scan_not_mathematical_root_enclosure"
    resource_semantics: str = "coverage_candidates_not_per_evaluation_reduction_receipts"


def _merged(intervals):
    result = []
    for a, b in sorted(intervals):
        if result and a <= result[-1][1]:
            result[-1] = (result[-1][0], max(result[-1][1], b))
        else:
            result.append((a, b))
    return tuple(result)


def _gaps(low, high, intervals):
    result, previous = [], low
    for a, b in _merged(intervals):
        if a > previous:
            result.append((previous, a))
        previous = max(previous, b)
    if previous < high:
        result.append((previous, high))
    return tuple(result)


def _coverage_schedule(body_id, identity, reader, low, high, policy):
    """Intersect real route resources in TDB, reserve padding, then bind UT1.

    Uses exact disjoint descriptor coverage and all canonical correction/clock
    routes. Comets honor the first SmallBodyKernel chosen by comet_at, rather
    than treating every installed shard as an interchangeable solution.
    """
    from ._ephemeris_time import _bind_ephemeris_time, _ephemeris_tt_to_ut1, _reader_identity_at
    from .julian import tdb_to_tt
    from .spk_reader import KernelPool, _PLANETARY_CLOCK_ROUTES
    from ._spk_body_kernel import SmallBodyKernel
    pool = reader if isinstance(reader, KernelPool) else KernelPool((reader,))
    beginning = _bind_ephemeris_time(low, reader)
    ending = _bind_ephemeris_time(high, reader)
    if beginning.identity != ending.identity:
        raise ValueError("ephemeris clock identity changes across the requested study")
    padding = policy.resource_padding_days
    tdb_low, tdb_high = beginning.epoch_tdb - padding, ending.epoch_tdb + padding
    required = set(_PLANETARY_CLOCK_ROUTES) | set(EARTH_ROUTE) | {(0, 10)}
    if identity is None:
        required.update(NAIF_ROUTES[body_id])
        if body_id not in (Body.SUN, Body.MOON):
            required.update(NAIF_ROUTES[Body.JUPITER])
            required.update(NAIF_ROUTES[Body.SATURN])
    elif identity.family == "asteroid":
        required.add((0, identity.naif_id))
        required.update(NAIF_ROUTES[Body.JUPITER])
        required.update(NAIF_ROUTES[Body.SATURN])
    else:
        required.add((10, identity.naif_id))
    nodes = {n for pair in required for n in pair}
    resources, points, cells = [], {tdb_low, tdb_high}, []
    with pool._read_lease() as snapshot:
        comet_kernel = None
        if identity is not None and identity.family == "comet":
            comet_kernel = next((r for r in snapshot.readers if isinstance(r, SmallBodyKernel) and r.has_body(identity.naif_id)), None)
            if comet_kernel is None:
                raise ValueError(f"no installed comet kernel for {body_id}")
        for candidate in snapshot.readers:
            source = getattr(candidate, "_source_identity", None)
            if source is None:
                raise ValueError("Geodetic timing requires content-identified resource readers")
            for center, target in candidate._coverage_pairs_tdb():
                if center not in nodes or target not in nodes:
                    continue
                if identity is not None and identity.family == "comet" and target == identity.naif_id and candidate is not comet_kernel:
                    continue
                intervals = candidate.coverage_intervals_tdb(center, target)
                if not any(a <= tdb_high and b >= tdb_low for a, b in intervals):
                    continue
                descriptors = tuple(s for s in candidate._kernel.segments if s.center == center and s.target == target)
                boundaries = tuple(sorted({float(v) for s in descriptors for v in (s.start_jd, s.end_jd)}))
                resources.append(GeodeticTimingResource(center, target, source.label, source.sha256,
                                                       source.catalog_id, source.catalog_version, source.manifest_sha256,
                                                       tuple(intervals), boundaries))
                points.update(v for v in boundaries if tdb_low < v < tdb_high)
        ordered = sorted(points)
        for a, b in zip(ordered, ordered[1:]):
            mid = a / 2 + b / 2
            available = True
            for center, target in required:
                if comet_kernel is not None and target == identity.naif_id:
                    available &= any(x <= mid <= y for x, y in comet_kernel.coverage_intervals_tdb(center, target))
                else:
                    available &= pool._find_route_tdb(snapshot, center, target, mid) is not None
            if available:
                if _reader_identity_at(reader, mid, snapshot=snapshot) != beginning.identity:
                    raise ValueError("ephemeris clock identity changes inside covered study")
                cells.append((a, b))
        union = _merged(cells)
        # Reserve padding at actual gaps/outer edges, not at a continuous
        # descriptor seam. Every seam remains an explicit scan split below.
        admitted = [(a + padding, b - padding) for a, b in union if b - a > 2 * padding]
        schedule = []
        for a, b in admitted:
            cuts = [a] + [p for p in ordered if a < p < b] + [b]
            for start, end in zip(cuts, cuts[1:]):
                start_ut = max(low, _ephemeris_tt_to_ut1(tdb_to_tt(start), reader, snapshot=snapshot))
                end_ut = min(high, _ephemeris_tt_to_ut1(tdb_to_tt(end), reader, snapshot=snapshot))
                if start_ut < end_ut:
                    schedule.append((start_ut, end_ut))
        if pool._generation != snapshot.generation:
            raise RuntimeError("reader pool changed during coverage admission")
    # Floating inversion must not manufacture a sub-millisecond gap where
    # both requested endpoints were covered with the declared padding.
    tolerance = 4 * max(math.ulp(low), math.ulp(high))
    includes_start = any(a <= beginning.epoch_tdb <= b for a, b in admitted)
    includes_end = any(a <= ending.epoch_tdb <= b for a, b in admitted)
    if schedule and includes_start and abs(schedule[0][0] - low) <= tolerance:
        schedule[0] = (low, schedule[0][1])
    if schedule and includes_end and abs(schedule[-1][1] - high) <= tolerance:
        schedule[-1] = (schedule[-1][0], high)
    return tuple(schedule), tuple(resources), beginning


def find_geodetic_transits(
    reference: GeodeticFixedReference, mover: str, jd_start: float, jd_end: float, *,
    aspects: Sequence[tuple[float, float]], policy: GeodeticTimingPolicy, reader=None,
) -> GeodeticTimingResult:
    """Find both branches of explicit undirected aspects to fixed angles.

    ``aspects`` contains unique ``(angle_deg, orb_deg)`` pairs. Conjunction
    and opposition are searched once. Gaps and exhausted budgets are visible;
    missing orb entry/exit values never mean proof that no boundary exists.
    """
    from ._ephemeris_time import _bind_ephemeris_time
    from .planets import planet_at
    from .spk_reader import get_reader
    from .transits import TransitComputationPolicy, _validate_transit_range
    from .transits_aspects import _find_aspect_transits_to_longitudes_core
    if not isinstance(reference, GeodeticFixedReference) or not isinstance(policy, GeodeticTimingPolicy):
        raise TypeError("reference and policy must be Geodetic timing vessels")
    _validate_transit_range(jd_start, jd_end)
    if not math.isfinite(jd_end - jd_start) or max(math.ulp(jd_start), math.ulp(jd_end)) > policy.time_tolerance_days:
        raise ValueError("requested epochs cannot represent the solver time tolerance")
    body_id, identity = _body_identity(mover)
    if identity is None and body_id not in Body.ALL_PLANETS:
        raise ValueError("mover must resolve to a canonical major planet, minor body or comet")
    if not aspects or isinstance(aspects, str):
        raise ValueError("explicit nonempty aspects are required")
    specs, metadata, seen = [], [], set()
    for angle, orb in aspects:
        if not math.isfinite(angle) or not 0 <= angle <= 180 or not math.isfinite(orb) or not 0 <= orb < 90:
            raise ValueError("aspect angles must be in [0, 180], and orbs in [0, 90)")
        if angle in seen:
            raise ValueError("duplicate undirected aspect angles")
        seen.add(angle)
        branches = (angle,) if angle in (0, 180) else (angle, -angle)
        for name, longitude in reference.tropical_targets:
            for branch in branches:
                specs.append((longitude, branch, orb))
                metadata.append((name, angle, orb))
    if reader is None:
        reader = get_reader()
    reader_generation = getattr(reader, "_generation", None)
    covered, resources, clock = _coverage_schedule(body_id, identity, reader, jd_start, jd_end, policy)
    gaps = _gaps(jd_start, jd_end, covered)
    if gaps and policy.coverage_policy == "require_full":
        raise ValueError(f"requested interval is not fully covered with reduction padding: {gaps}")
    union = _merged(covered)
    intervals = []
    for a, b in covered:
        left = "outside_study_span" if a == jd_start else "segment_boundary" if any(x < a <= y for x, y in union) else "coverage_gap" if a > jd_start and covered and a != union[0][0] else "outside_coverage"
        right = "outside_study_span" if b == jd_end else "segment_boundary" if any(x <= b < y for x, y in union) else "coverage_gap" if b < jd_end and covered and b != union[-1][1] else "outside_coverage"
        intervals.append((a, b, left, right))

    def evaluate(jd):
        value = planet_at(body_id, jd, reader=reader)
        if value.distance / C_KM_PER_DAY > policy.maximum_light_time_days:
            raise ValueError("evaluated light-time exceeds declared resource padding policy")
        return value.longitude

    result = _find_aspect_transits_to_longitudes_core(
        body_id, specs, jd_start, jd_end, policy.step_days, reader,
        TransitComputationPolicy(), "forward", evaluator=evaluate, intervals=tuple(intervals),
        scan_policy=policy._scan_policy(), rich=True,
    )
    # Merge only the same mover/target/undirected aspect, including windows
    # spanning direct/retrograde repeats or a continuous descriptor seam.
    groups = {}
    for window in result.windows:
        key = metadata[window.target_index]
        groups.setdefault(key, []).append(window)
    assembled = []
    tol = policy.time_tolerance_days
    for key, group in groups.items():
        merged = []
        for window in sorted(group, key=lambda w: w.start):
            if merged and window.start <= merged[-1][1] + tol and not (merged[-1][3] in ("coverage_gap", "outside_coverage") or window.entry_status in ("coverage_gap", "outside_coverage")):
                a, b, entry, exit_ = merged[-1]
                merged[-1] = (a, max(b, window.end), entry, window.exit_status if window.end >= b else exit_)
            else:
                merged.append((window.start, window.end, window.entry_status, window.exit_status))
        for a, b, entry, exit_ in merged:
            assembled.append((key, a, b, entry, exit_))
    assembled.sort(key=lambda w: (w[1], w[0]))
    unresolved_seam = any(entry == "segment_boundary" or exit_ == "segment_boundary" for _, _, _, entry, exit_ in assembled)
    if unresolved_seam:
        clip = "search_budget_exhausted" if "search_budget_exhausted" in result.reasons else "unresolved_boundary"
        assembled = [(key, a, b, clip if entry == "segment_boundary" else entry,
                      clip if exit_ == "segment_boundary" else exit_) for key, a, b, entry, exit_ in assembled]
    hits = []
    for hit in result.passes:
        name, angle, orb = metadata[hit.target_index]
        if any(h.target == name and h.aspect_angle_deg == angle and h.directed_angle_deg == hit.directed_angle_deg and abs(h.jd_ut1 - hit.jd_ut1) <= 4 * tol for h in hits):
            continue
        window_index = next((i for i, (key, a, b, _, _) in enumerate(assembled) if key == (name, angle, orb) and a - tol <= hit.jd_ut1 <= b + tol), None)
        hits.append(GeodeticTransitPass(body_id, name, angle, hit.directed_angle_deg, hit.jd_ut1, hit.motion, hit.residual_deg, window_index))
    windows = tuple(GeodeticOrbWindow(body_id, key[0], key[1], key[2], a, b,
                                     a if entry == "found" else None, b if exit_ == "found" else None,
                                     entry, exit_, tuple(i for i, hit in enumerate(hits) if hit.window_index == wi))
                    for wi, (key, a, b, entry, exit_) in enumerate(assembled))
    reasons = set(result.reasons)
    if gaps:
        reasons.add("partial_coverage")
    if not covered:
        reasons.add("outside_coverage")
    if unresolved_seam:
        reasons.add("unresolved_boundary")
    # Rebind the clock at completion so a mutable reader cannot silently
    # change the scientific identity between coverage and evaluation.
    if _bind_ephemeris_time(jd_start, reader).identity != clock.identity:
        raise RuntimeError("ephemeris clock identity changed during search")
    if getattr(reader, "_generation", None) != reader_generation:
        raise RuntimeError("reader pool changed during search")
    complete = result.complete and not gaps and bool(covered) and not unresolved_seam
    return GeodeticTimingResult(reference, mover, body_id, identity, policy, (jd_start, jd_end), covered, gaps,
                                resources, tuple(hits), windows, result.evaluations, result.subdivisions,
                                complete, "complete_under_scan_policy" if complete else "incomplete", tuple(sorted(reasons)),
                                result.scanned_intervals, clock)
