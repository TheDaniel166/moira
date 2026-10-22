"""Bounded-work diagnostics for nonlinear Geodetic input uncertainty.

Owns deterministic sampling and circular sample summaries. The Geodetic core
owns the analytic domain and branch-intersection tests. No confidence levels
or guaranteed envelopes are inferred from finite sampling.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass

from .geodetic import (
    GeodeticChart, GeodeticGeometryWitness, GeodeticInputUncertainty, GeodeticSensitivityResult,
    _ascendant_local_derivatives, _circular_delta, _normalize_angle, _uncertainty_domain_reasons,
    geodetic_asc, geodetic_chart_sensitivity, geodetic_geometry,
)

__all__ = [
    "GeodeticDiagnosticPolicy", "GeodeticCircularArc",
    "GeodeticNonlinearityResult", "diagnose_geodetic_uncertainty",
]


@dataclass(frozen=True, slots=True)
class GeodeticDiagnosticPolicy:
    """Caller-selected angular residual tolerance and finite sampling budget."""

    residual_tolerance_deg: float
    max_evaluations: int = 4096
    max_depth: int = 4

    def __post_init__(self):
        if not math.isfinite(self.residual_tolerance_deg) or self.residual_tolerance_deg <= 0:
            raise ValueError("residual_tolerance_deg must be finite and positive")
        if isinstance(self.max_evaluations, bool) or not isinstance(self.max_evaluations, int) or self.max_evaluations < 1:
            raise ValueError("max_evaluations must be a positive integer")
        if isinstance(self.max_depth, bool) or not isinstance(self.max_depth, int) or not 0 <= self.max_depth <= 12:
            raise ValueError("max_depth must be an integer in [0, 12]")


@dataclass(frozen=True, slots=True)
class GeodeticCircularArc:
    """Shortest circular arc covering the sampled values, not all possible values."""

    start_deg: float
    sweep_deg: float


@dataclass(frozen=True, slots=True)
class GeodeticNonlinearityResult:
    """Analytic domain findings, base conditioning and sampled ASC nonlinearity.

    Sampled maxima/arcs describe ASC. MC retains its direct longitude mapping
    and the local estimate's explicit MC derivative/radius, when representable.
    """

    base_chart: GeodeticChart
    uncertainty: GeodeticInputUncertainty
    policy: GeodeticDiagnosticPolicy
    base_geometry: GeodeticGeometryWitness
    status: str
    reasons: tuple[str, ...]
    linear_estimate: GeodeticSensitivityResult | None
    sampled_max_deviation_deg: float | None
    sampled_max_residual_deg: float | None
    sampled_arc: GeodeticCircularArc | None
    evaluations: int
    sampling_complete: bool
    interpretation: str = "deterministic_samples_not_an_error_bound"
    sampling_scheme: str = "box_center_faces_edges_corners_critical_meridians_adaptive_v1"


def _covering_arc(values):
    angles = sorted(set(_normalize_angle(value) for value in values))
    if len(angles) == 1:
        return GeodeticCircularArc(angles[0], 0.0)
    gaps = [(angles[(i + 1) % len(angles)] - value) % 360.0 for i, value in enumerate(angles)]
    largest = max(range(len(gaps)), key=lambda i: gaps[i])
    return GeodeticCircularArc(angles[(largest + 1) % len(angles)], 360.0 - gaps[largest])


def diagnose_geodetic_uncertainty(chart, uncertainty, *, policy):
    """Inspect the entire input box analytically, then sample valid geometry.

    Residuals use the shortest circular branch. A half-turn local prediction
    is marked nonlinear because its signed interpretation is ambiguous.
    """
    if not isinstance(chart, GeodeticChart):
        raise TypeError("chart must be GeodeticChart")
    if not isinstance(uncertainty, GeodeticInputUncertainty):
        raise TypeError("uncertainty must be GeodeticInputUncertainty")
    if not isinstance(policy, GeodeticDiagnosticPolicy):
        raise TypeError("policy must be GeodeticDiagnosticPolicy")
    reasons = _uncertainty_domain_reasons(chart, uncertainty)
    base_geometry = geodetic_geometry(chart.geo_longitude, chart.geo_latitude, chart.obliquity)
    if reasons:
        return GeodeticNonlinearityResult(
            chart, uncertainty, policy, base_geometry, "domain_intersection", reasons, None,
            None, None, None, 0, True,
        )
    local = _ascendant_local_derivatives(chart.geo_longitude, chart.geo_latitude, chart.obliquity)
    try:
        linear = geodetic_chart_sensitivity(chart, uncertainty)
    except (ValueError, OverflowError):
        # A finite input box may have an unrepresentable linear radius. It
        # still has valid sampled circular geometry; do not invent a bound.
        linear = None
    derivatives = (
        local.geo_longitude_deg, local.geo_latitude_deg, local.obliquity_deg,
    )
    radii = (uncertainty.longitude_deg, uncertainty.latitude_deg, uncertainty.obliquity_deg)
    cache = {}
    incomplete = False
    half_turn = False

    def evaluate(offset):
        nonlocal incomplete, half_turn
        if offset in cache:
            return cache[offset]
        if len(cache) >= policy.max_evaluations:
            incomplete = True
            return None
        value = geodetic_asc(
            chart.geo_longitude + offset[0], chart.geo_latitude + offset[1],
            chart.obliquity + offset[2], chart.ayanamsa_deg,
        )
        prediction = sum(d * v for d, v in zip(derivatives, offset))
        half_turn |= not math.isfinite(prediction) or abs(prediction) >= 180.0
        residual = abs(_circular_delta(value, chart.asc + prediction)) if math.isfinite(prediction) else 180.0
        cache[offset] = (value, residual, abs(_circular_delta(value, chart.asc)))
        return cache[offset]

    # Add relevant interior critical meridians without enumerating periods
    # of a huge longitude interval. Analytic interval tests already examined
    # the entire box; these slices improve sampled residual diagnostics.
    critical = [0.0]
    for phase in (0.0, 90.0, 180.0, 270.0):
        delta = _circular_delta(phase, chart.geo_longitude)
        if abs(delta) <= radii[0]:
            critical.append(delta)
    for offset in itertools.product(sorted(set(critical)), (-radii[1], 0.0, radii[1]), (-radii[2], 0.0, radii[2])):
        if evaluate(offset) is None:
            break
    pending = [((tuple(-r for r in radii)), radii, 0)]
    while pending and not incomplete:
        low, high, depth = pending.pop()
        coordinates = [
            (lo,) if lo == hi else (lo, lo / 2.0 + hi / 2.0, hi)
            for lo, hi in zip(low, high)
        ]
        residual = 0.0
        for offset in itertools.product(*coordinates):
            sample = evaluate(offset)
            if sample is None:
                break
            residual = max(residual, sample[1])
        if residual > policy.residual_tolerance_deg and depth < policy.max_depth and not incomplete:
            splits = [
                ((lo, hi),) if lo == hi else ((lo, lo / 2.0 + hi / 2.0), (lo / 2.0 + hi / 2.0, hi))
                for lo, hi in zip(low, high)
            ]
            for cell in itertools.product(*splits):
                pending.append((tuple(v[0] for v in cell), tuple(v[1] for v in cell), depth + 1))
    values = tuple(cache.values())
    max_residual = max(v[1] for v in values)
    found_nonlinear = max_residual > policy.residual_tolerance_deg or half_turn
    status = "sampling_incomplete" if incomplete else "nonlinear" if found_nonlinear else "sampled_consistent"
    detail = []
    if found_nonlinear:
        detail.append("sampled_linearization_residual" if not half_turn else "circular_linearization_ambiguous")
    if incomplete:
        detail.append("evaluation_budget_exhausted")
    return GeodeticNonlinearityResult(
        chart, uncertainty, policy, base_geometry, status, tuple(detail), linear,
        max(v[2] for v in values), max_residual,
        _covering_arc(v[0] for v in values), len(cache), not incomplete,
    )
