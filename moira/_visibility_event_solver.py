"""Deterministic numerical core for physical visibility-event search.

This module owns numerical search objects only.  Public doctrine, policy
selection, typed public failures, and result assembly remain in
``moira.heliacal``.

The governing scalar object is a continuous, evaluable signal over a bounded
UT interval.  The solver samples the complete interval at a declared maximum
step, adaptively refines intervals near a zero or with resolved curvature,
brackets every witnessed sign change, and refines each bracket by bisection.
It also searches local absolute-value minima so a tangent or near-zero contact
cannot be silently mistaken for an ordinary sign-changing root.

No callback failure is interpreted as a negative value.  A non-evaluable
sample creates an explicit gap, and callers must fail closed when that gap
intersects an observation window.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass


__all__ = [
    "ScalarEvaluation",
    "ScalarRoot",
    "ScalarNearZero",
    "ScalarGap",
    "ScalarLipschitzCertificate",
    "ScalarRootEnclosure",
    "ScalarUnresolvedInterval",
    "ScalarSearchPolicy",
    "ScalarIntervalScan",
    "ObservationPhaseRule",
    "ObservationWindow",
    "ObservationWindowConstruction",
    "VisibilityWindowSolution",
    "ObservationDaySolution",
    "PhaseTransitionSelection",
    "scan_scalar_interval",
    "construct_observation_windows",
    "classify_observation_day",
    "select_owned_phase_transition",
]


_NEGATIVE_TO_POSITIVE = "negative_to_positive"
_POSITIVE_TO_NEGATIVE = "positive_to_negative"
_TANGENT = "tangent"


@dataclass(frozen=True, slots=True)
class ScalarEvaluation:
    """One typed scalar evaluation at an exact UT Julian date."""

    jd_ut: float
    value: float | None
    reason: str | None = None

    def __post_init__(self) -> None:
        if (
            isinstance(self.jd_ut, bool)
            or not isinstance(self.jd_ut, (int, float))
            or not math.isfinite(self.jd_ut)
        ):
            raise ValueError("jd_ut must be finite")
        if self.value is None:
            if not isinstance(self.reason, str) or not self.reason:
                raise ValueError(
                    "a non-evaluable scalar sample requires a reason"
                )
            return
        if (
            isinstance(self.value, bool)
            or not isinstance(self.value, (int, float))
            or not math.isfinite(self.value)
        ):
            raise ValueError("scalar value must be finite")
        if self.reason is not None:
            raise ValueError(
                "an evaluable scalar sample must not carry a reason"
            )

    @property
    def evaluable(self) -> bool:
        """Whether this sample contains a finite scalar value."""

        return self.value is not None


ScalarEvaluator = Callable[[float], ScalarEvaluation]


@dataclass(frozen=True, slots=True)
class ScalarRoot:
    """One refined sign-changing or tangent scalar root."""

    jd_ut: float
    direction: str
    kind: str
    residual: float
    bracket_start_jd_ut: float
    bracket_end_jd_ut: float
    iterations: int


@dataclass(frozen=True, slots=True)
class ScalarNearZero:
    """A resolved local minimum near zero that is not a root."""

    jd_ut: float
    absolute_value: float
    interval_start_jd_ut: float
    interval_end_jd_ut: float
    iterations: int


@dataclass(frozen=True, slots=True)
class ScalarGap:
    """A bounded interval whose scalar truth was not fully evaluable."""

    start_jd_ut: float
    end_jd_ut: float
    reasons: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ScalarLipschitzCertificate:
    """Admitted absolute-rate bound for zero-containment certification.

    For every pair of instants in the certified scope, the scalar difference
    must not exceed ``maximum_absolute_rate_per_day`` times their separation.
    The solver never estimates this bound from the samples it is certifying;
    callers must supply a separately admitted bound and source identity.
    """

    certificate_id: str
    maximum_absolute_rate_per_day: float
    source_receipt_sha256: str
    maximum_subdivision_depth: int = 24

    def __post_init__(self) -> None:
        if not isinstance(self.certificate_id, str) or not self.certificate_id:
            raise ValueError("certificate_id must not be empty")
        if (
            isinstance(self.maximum_absolute_rate_per_day, bool)
            or not isinstance(
                self.maximum_absolute_rate_per_day,
                (int, float),
            )
            or not math.isfinite(
                self.maximum_absolute_rate_per_day
            )
            or self.maximum_absolute_rate_per_day <= 0.0
        ):
            raise ValueError(
                "maximum_absolute_rate_per_day must be positive and finite"
            )
        if (
            not isinstance(self.source_receipt_sha256, str)
            or len(self.source_receipt_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in self.source_receipt_sha256
            )
        ):
            raise ValueError(
                "source_receipt_sha256 must be lowercase SHA-256"
            )
        if (
            isinstance(self.maximum_subdivision_depth, bool)
            or not isinstance(self.maximum_subdivision_depth, int)
            or self.maximum_subdivision_depth <= 0
        ):
            raise ValueError(
                "maximum_subdivision_depth must be a positive integer"
            )


@dataclass(frozen=True, slots=True)
class ScalarRootEnclosure:
    """One interval guaranteed to contain every unresolved zero in its span."""

    start_jd_ut: float
    end_jd_ut: float
    endpoint_sign_change: bool


@dataclass(frozen=True, slots=True)
class ScalarUnresolvedInterval:
    """One interval for which the supplied certificate cannot decide zero."""

    start_jd_ut: float
    end_jd_ut: float
    reason: str


@dataclass(frozen=True, slots=True)
class ScalarSearchPolicy:
    """Numerical policy for a complete bounded scalar scan."""

    scan_step_days: float = 5.0 / 1440.0
    adaptive_minimum_step_days: float = 30.0 / 86400.0
    root_time_tolerance_days: float = 0.25 / 86400.0
    root_value_tolerance: float = 1.0e-5
    near_zero_tolerance: float = 2.5e-3
    curvature_tolerance: float = 5.0e-3
    maximum_adaptive_depth: int = 12
    maximum_root_iterations: int = 96

    def __post_init__(self) -> None:
        for name in (
            "scan_step_days",
            "adaptive_minimum_step_days",
            "root_time_tolerance_days",
            "root_value_tolerance",
            "near_zero_tolerance",
            "curvature_tolerance",
        ):
            value = getattr(self, name)
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or value <= 0.0
            ):
                raise ValueError(f"{name} must be positive and finite")
        if self.adaptive_minimum_step_days > self.scan_step_days:
            raise ValueError(
                "adaptive_minimum_step_days must not exceed scan_step_days"
            )
        if (
            self.root_time_tolerance_days
            > self.adaptive_minimum_step_days
        ):
            raise ValueError(
                "root_time_tolerance_days must not exceed "
                "adaptive_minimum_step_days"
            )
        for name in (
            "maximum_adaptive_depth",
            "maximum_root_iterations",
        ):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError(f"{name} must be an integer")
            if value <= 0:
                raise ValueError(f"{name} must be positive")


@dataclass(frozen=True, slots=True)
class ScalarIntervalScan:
    """Complete numerical receipt for one bounded scalar scan."""

    interval_start_jd_ut: float
    interval_end_jd_ut: float
    samples: tuple[ScalarEvaluation, ...]
    roots: tuple[ScalarRoot, ...]
    near_zero_intervals: tuple[ScalarNearZero, ...]
    gaps: tuple[ScalarGap, ...]
    evaluation_count: int
    maximum_sample_gap_days: float
    minimum_sample_gap_days: float
    crossing_completeness_state: str = "not_requested"
    crossing_completeness_reason: str | None = (
        "no_interval_certificate_supplied"
    )
    certificate_id: str | None = None
    certificate_maximum_absolute_rate_per_day: float | None = None
    root_enclosures: tuple[ScalarRootEnclosure, ...] = ()
    unresolved_intervals: tuple[ScalarUnresolvedInterval, ...] = ()


@dataclass(frozen=True, slots=True)
class ObservationPhaseRule:
    """Internal projection of the public four-phase event doctrine."""

    solar_side: str
    target_boundary_role: str
    crossing_direction: str
    day_ownership: str

    def __post_init__(self) -> None:
        if self.solar_side not in {"morning", "evening"}:
            raise ValueError("solar_side must be morning or evening")
        if self.target_boundary_role not in {"rising", "setting"}:
            raise ValueError(
                "target_boundary_role must be rising or setting"
            )
        if self.crossing_direction not in {
            _NEGATIVE_TO_POSITIVE,
            _POSITIVE_TO_NEGATIVE,
        }:
            raise ValueError("unsupported crossing_direction")
        if self.day_ownership not in {"first", "last"}:
            raise ValueError("day_ownership must be first or last")


@dataclass(frozen=True, slots=True)
class ObservationWindow:
    """One target-horizon-connected interval inside the solar domain."""

    observation_day_key: int
    start_jd_ut: float
    end_jd_ut: float
    target_boundary_jd_ut: float
    target_boundary_role: str
    solar_side: str


@dataclass(frozen=True, slots=True)
class ObservationWindowConstruction:
    """Typed result of solar-domain and target-horizon intersection."""

    observation_day_key: int
    windows: tuple[ObservationWindow, ...]
    reason: str | None
    geometry_state: str | None
    solar_horizon_scan: ScalarIntervalScan
    solar_domain_scan: ScalarIntervalScan | None
    target_horizon_scan: ScalarIntervalScan | None
    target_domain_scan: ScalarIntervalScan | None


@dataclass(frozen=True, slots=True)
class VisibilityWindowSolution:
    """Visibility-margin classification for one observation window."""

    status: str
    reason: str | None
    window: ObservationWindow
    event_jd_ut: float | None
    assessment_jd_ut: float | None
    boundary_source: str | None
    crossing_direction: str | None
    root_residual: float | None
    root_bracket_start_jd_ut: float | None
    root_bracket_end_jd_ut: float | None
    root_iterations: int | None
    peak_margin_jd_ut: float | None
    peak_margin: float | None
    margin_scan: ScalarIntervalScan | None


@dataclass(frozen=True, slots=True)
class ObservationDaySolution:
    """Typed classification of one comparable observation day."""

    observation_day_key: int
    status: str
    reason: str | None
    selected_window: VisibilityWindowSolution | None
    window_solutions: tuple[VisibilityWindowSolution, ...]
    construction: ObservationWindowConstruction


@dataclass(frozen=True, slots=True)
class PhaseTransitionSelection:
    """First-day or last-day ownership result over candidate day keys."""

    status: str
    reason: str | None
    selected_day: ObservationDaySolution | None
    comparison_day: ObservationDaySolution | None
    classified_days: tuple[ObservationDaySolution, ...]


def _validate_interval(start_jd_ut: float, end_jd_ut: float) -> None:
    if any(
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        for value in (start_jd_ut, end_jd_ut)
    ):
        raise ValueError("interval endpoints must be finite")
    if end_jd_ut <= start_jd_ut:
        raise ValueError("interval end must be after interval start")


def _evaluate(
    evaluator: ScalarEvaluator,
    jd_ut: float,
    cache: dict[float, ScalarEvaluation],
) -> ScalarEvaluation:
    cached = cache.get(jd_ut)
    if cached is not None:
        return cached
    sample = evaluator(jd_ut)
    if not isinstance(sample, ScalarEvaluation):
        raise TypeError("scalar evaluator must return ScalarEvaluation")
    if not math.isclose(
        sample.jd_ut,
        jd_ut,
        rel_tol=0.0,
        abs_tol=1.0e-12,
    ):
        raise ValueError(
            "scalar evaluator returned a sample for a different instant"
        )
    cache[jd_ut] = sample
    return sample


def _initial_grid(
    start_jd_ut: float,
    end_jd_ut: float,
    step_days: float,
) -> tuple[float, ...]:
    count = max(1, math.ceil((end_jd_ut - start_jd_ut) / step_days))
    width = (end_jd_ut - start_jd_ut) / count
    return tuple(
        start_jd_ut + width * index
        for index in range(count)
    ) + (end_jd_ut,)


def _needs_adaptive_split(
    left: ScalarEvaluation,
    middle: ScalarEvaluation,
    right: ScalarEvaluation,
    policy: ScalarSearchPolicy,
) -> bool:
    if not (left.evaluable and middle.evaluable and right.evaluable):
        return False
    assert left.value is not None
    assert middle.value is not None
    assert right.value is not None
    if (
        left.value * middle.value <= 0.0
        or middle.value * right.value <= 0.0
    ):
        return True
    if min(
        abs(left.value),
        abs(middle.value),
        abs(right.value),
    ) <= policy.near_zero_tolerance * 4.0:
        return True
    linear_middle = (left.value + right.value) * 0.5
    return (
        abs(middle.value - linear_middle)
        > policy.curvature_tolerance
    )


def _adaptive_sample_segment(
    evaluator: ScalarEvaluator,
    left: ScalarEvaluation,
    right: ScalarEvaluation,
    policy: ScalarSearchPolicy,
    cache: dict[float, ScalarEvaluation],
    *,
    depth: int,
) -> None:
    width = right.jd_ut - left.jd_ut
    if width <= policy.adaptive_minimum_step_days:
        return
    middle_jd = (left.jd_ut + right.jd_ut) * 0.5
    middle = _evaluate(evaluator, middle_jd, cache)
    if not _needs_adaptive_split(left, middle, right, policy):
        return
    if depth >= policy.maximum_adaptive_depth:
        return
    _adaptive_sample_segment(
        evaluator,
        left,
        middle,
        policy,
        cache,
        depth=depth + 1,
    )
    _adaptive_sample_segment(
        evaluator,
        middle,
        right,
        policy,
        cache,
        depth=depth + 1,
    )


def _crossing_direction(left_value: float, right_value: float) -> str:
    if left_value < right_value:
        return _NEGATIVE_TO_POSITIVE
    return _POSITIVE_TO_NEGATIVE


def _refine_sign_change(
    evaluator: ScalarEvaluator,
    left: ScalarEvaluation,
    right: ScalarEvaluation,
    policy: ScalarSearchPolicy,
    cache: dict[float, ScalarEvaluation],
) -> ScalarRoot:
    assert left.value is not None
    assert right.value is not None
    if left.value == 0.0:
        return ScalarRoot(
            jd_ut=left.jd_ut,
            direction=_crossing_direction(left.value, right.value),
            kind="crossing",
            residual=0.0,
            bracket_start_jd_ut=left.jd_ut,
            bracket_end_jd_ut=right.jd_ut,
            iterations=0,
        )
    if right.value == 0.0:
        return ScalarRoot(
            jd_ut=right.jd_ut,
            direction=_crossing_direction(left.value, right.value),
            kind="crossing",
            residual=0.0,
            bracket_start_jd_ut=left.jd_ut,
            bracket_end_jd_ut=right.jd_ut,
            iterations=0,
        )
    if left.value * right.value > 0.0:
        raise ValueError("root refinement requires a sign-changing bracket")

    bracket_start = left.jd_ut
    bracket_end = right.jd_ut
    direction = _crossing_direction(left.value, right.value)
    iterations = 0
    best = left if abs(left.value) <= abs(right.value) else right

    while iterations < policy.maximum_root_iterations:
        iterations += 1
        middle_jd = (left.jd_ut + right.jd_ut) * 0.5
        middle = _evaluate(evaluator, middle_jd, cache)
        if not middle.evaluable:
            raise ValueError(
                "scalar became non-evaluable inside a root bracket"
            )
        assert middle.value is not None
        if abs(middle.value) < abs(best.value):  # type: ignore[arg-type]
            best = middle
        if middle.value == 0.0:
            best = middle
            left = middle
            right = middle
            break
        if left.value * middle.value < 0.0:
            right = middle
        else:
            left = middle
        if (
            right.jd_ut - left.jd_ut
            <= policy.root_time_tolerance_days
            and abs(best.value) <= policy.root_value_tolerance
        ):
            break

    assert best.value is not None
    return ScalarRoot(
        jd_ut=best.jd_ut,
        direction=direction,
        kind="crossing",
        residual=abs(best.value),
        bracket_start_jd_ut=bracket_start,
        bracket_end_jd_ut=bracket_end,
        iterations=iterations,
    )


def _refine_absolute_minimum(
    evaluator: ScalarEvaluator,
    start_jd_ut: float,
    end_jd_ut: float,
    policy: ScalarSearchPolicy,
    cache: dict[float, ScalarEvaluation],
) -> tuple[ScalarEvaluation, int] | None:
    left = start_jd_ut
    right = end_jd_ut
    best: ScalarEvaluation | None = None
    iterations = 0
    while (
        right - left > policy.root_time_tolerance_days
        and iterations < policy.maximum_root_iterations
    ):
        iterations += 1
        one_third = left + (right - left) / 3.0
        two_thirds = right - (right - left) / 3.0
        first = _evaluate(evaluator, one_third, cache)
        second = _evaluate(evaluator, two_thirds, cache)
        if not (first.evaluable and second.evaluable):
            return None
        assert first.value is not None
        assert second.value is not None
        for candidate in (first, second):
            if (
                best is None
                or abs(candidate.value) < abs(best.value)  # type: ignore[arg-type]
            ):
                best = candidate
        if abs(first.value) <= abs(second.value):
            right = two_thirds
        else:
            left = one_third
    midpoint = _evaluate(evaluator, (left + right) * 0.5, cache)
    if not midpoint.evaluable:
        return None
    assert midpoint.value is not None
    if (
        best is None
        or abs(midpoint.value) < abs(best.value)  # type: ignore[arg-type]
    ):
        best = midpoint
    return best, iterations


def _deduplicate_roots(
    roots: list[ScalarRoot],
    tolerance_days: float,
) -> tuple[ScalarRoot, ...]:
    ordered = sorted(roots, key=lambda root: root.jd_ut)
    result: list[ScalarRoot] = []
    for root in ordered:
        if (
            result
            and abs(root.jd_ut - result[-1].jd_ut) <= tolerance_days
        ):
            previous = result[-1]
            if root.residual < previous.residual:
                result[-1] = root
            continue
        result.append(root)
    return tuple(result)


def _collect_gaps(
    samples: tuple[ScalarEvaluation, ...],
) -> tuple[ScalarGap, ...]:
    gaps: list[ScalarGap] = []
    start_index: int | None = None
    for index, sample in enumerate(samples):
        if not sample.evaluable and start_index is None:
            start_index = index
        if sample.evaluable and start_index is not None:
            first = max(0, start_index - 1)
            reasons = tuple(
                sorted(
                    {
                        item.reason
                        for item in samples[start_index:index]
                        if item.reason is not None
                    }
                )
            )
            gaps.append(
                ScalarGap(
                    start_jd_ut=samples[first].jd_ut,
                    end_jd_ut=sample.jd_ut,
                    reasons=reasons,
                )
            )
            start_index = None
    if start_index is not None:
        first = max(0, start_index - 1)
        reasons = tuple(
            sorted(
                {
                    item.reason
                    for item in samples[start_index:]
                    if item.reason is not None
                }
            )
        )
        gaps.append(
            ScalarGap(
                start_jd_ut=samples[first].jd_ut,
                end_jd_ut=samples[-1].jd_ut,
                reasons=reasons,
            )
        )
    return tuple(gaps)


def _zero_excluded_by_lipschitz_bound(
    left: ScalarEvaluation,
    right: ScalarEvaluation,
    maximum_absolute_rate_per_day: float,
) -> bool:
    """Whether either endpoint proves a constant nonzero sign throughout."""

    if not (left.evaluable and right.evaluable):
        return False
    assert left.value is not None
    assert right.value is not None
    if left.value == 0.0 or right.value == 0.0:
        return False
    if (left.value > 0.0) != (right.value > 0.0):
        return False
    maximum_change = (
        maximum_absolute_rate_per_day
        * (right.jd_ut - left.jd_ut)
    )
    return max(abs(left.value), abs(right.value)) > maximum_change


def _certify_scalar_segment(
    evaluator: ScalarEvaluator,
    left: ScalarEvaluation,
    right: ScalarEvaluation,
    policy: ScalarSearchPolicy,
    certificate: ScalarLipschitzCertificate,
    cache: dict[float, ScalarEvaluation],
    root_enclosures: list[ScalarRootEnclosure],
    unresolved: list[ScalarUnresolvedInterval],
    *,
    depth: int,
) -> None:
    """Recursively enclose every possible zero under one admitted rate bound."""

    width = right.jd_ut - left.jd_ut
    if not (left.evaluable and right.evaluable):
        unresolved.append(
            ScalarUnresolvedInterval(
                start_jd_ut=left.jd_ut,
                end_jd_ut=right.jd_ut,
                reason="non_evaluable_certificate_endpoint",
            )
        )
        return
    assert left.value is not None
    assert right.value is not None
    if _zero_excluded_by_lipschitz_bound(
        left,
        right,
        certificate.maximum_absolute_rate_per_day,
    ):
        return

    endpoint_sign_change = left.value * right.value < 0.0
    if width <= policy.root_time_tolerance_days:
        root_enclosures.append(
            ScalarRootEnclosure(
                start_jd_ut=left.jd_ut,
                end_jd_ut=right.jd_ut,
                endpoint_sign_change=endpoint_sign_change,
            )
        )
        return

    if depth >= certificate.maximum_subdivision_depth:
        unresolved.append(
            ScalarUnresolvedInterval(
                start_jd_ut=left.jd_ut,
                end_jd_ut=right.jd_ut,
                reason=(
                    "certificate_subdivision_depth_exhausted"
                ),
            )
        )
        return

    middle_jd = (left.jd_ut + right.jd_ut) * 0.5
    middle = _evaluate(evaluator, middle_jd, cache)
    if not middle.evaluable:
        unresolved.append(
            ScalarUnresolvedInterval(
                start_jd_ut=left.jd_ut,
                end_jd_ut=right.jd_ut,
                reason=(
                    middle.reason
                    or "non_evaluable_certificate_midpoint"
                ),
            )
        )
        return
    _certify_scalar_segment(
        evaluator,
        left,
        middle,
        policy,
        certificate,
        cache,
        root_enclosures,
        unresolved,
        depth=depth + 1,
    )
    _certify_scalar_segment(
        evaluator,
        middle,
        right,
        policy,
        certificate,
        cache,
        root_enclosures,
        unresolved,
        depth=depth + 1,
    )


def _merge_root_enclosures(
    values: list[ScalarRootEnclosure],
) -> tuple[ScalarRootEnclosure, ...]:
    ordered = sorted(values, key=lambda value: value.start_jd_ut)
    merged: list[ScalarRootEnclosure] = []
    for value in ordered:
        if (
            merged
            and value.start_jd_ut
            <= merged[-1].end_jd_ut + 1.0e-15
        ):
            previous = merged[-1]
            merged[-1] = ScalarRootEnclosure(
                start_jd_ut=previous.start_jd_ut,
                end_jd_ut=max(
                    previous.end_jd_ut,
                    value.end_jd_ut,
                ),
                endpoint_sign_change=(
                    previous.endpoint_sign_change
                    or value.endpoint_sign_change
                ),
            )
        else:
            merged.append(value)
    return tuple(merged)


def scan_scalar_interval(
    evaluator: ScalarEvaluator,
    start_jd_ut: float,
    end_jd_ut: float,
    *,
    policy: ScalarSearchPolicy | None = None,
    certificate: ScalarLipschitzCertificate | None = None,
) -> ScalarIntervalScan:
    """Scan, bracket, refine, and optionally certify one bounded interval."""

    _validate_interval(start_jd_ut, end_jd_ut)
    if not callable(evaluator):
        raise TypeError("evaluator must be callable")
    resolved = policy if policy is not None else ScalarSearchPolicy()
    if not isinstance(resolved, ScalarSearchPolicy):
        raise TypeError("policy must be a ScalarSearchPolicy")
    if (
        certificate is not None
        and not isinstance(certificate, ScalarLipschitzCertificate)
    ):
        raise TypeError(
            "certificate must be a ScalarLipschitzCertificate"
        )

    cache: dict[float, ScalarEvaluation] = {}
    grid = _initial_grid(
        start_jd_ut,
        end_jd_ut,
        resolved.scan_step_days,
    )
    initial = tuple(
        _evaluate(evaluator, jd_ut, cache)
        for jd_ut in grid
    )
    for left, right in zip(initial, initial[1:]):
        _adaptive_sample_segment(
            evaluator,
            left,
            right,
            resolved,
            cache,
            depth=0,
        )

    root_enclosures: list[ScalarRootEnclosure] = []
    unresolved_intervals: list[ScalarUnresolvedInterval] = []
    if certificate is not None:
        for left, right in zip(initial, initial[1:]):
            _certify_scalar_segment(
                evaluator,
                left,
                right,
                resolved,
                certificate,
                cache,
                root_enclosures,
                unresolved_intervals,
                depth=0,
            )

    samples = tuple(
        sorted(cache.values(), key=lambda sample: sample.jd_ut)
    )
    roots: list[ScalarRoot] = []
    for index, sample in enumerate(samples):
        if not sample.evaluable or sample.value != 0.0:
            continue
        previous = next(
            (
                candidate
                for candidate in reversed(samples[:index])
                if (
                    candidate.evaluable
                    and candidate.value != 0.0
                )
            ),
            None,
        )
        following = next(
            (
                candidate
                for candidate in samples[index + 1 :]
                if (
                    candidate.evaluable
                    and candidate.value != 0.0
                )
            ),
            None,
        )
        if previous is not None and following is not None:
            assert previous.value is not None
            assert following.value is not None
            if previous.value < 0.0 < following.value:
                direction = _NEGATIVE_TO_POSITIVE
                kind = "crossing"
            elif previous.value > 0.0 > following.value:
                direction = _POSITIVE_TO_NEGATIVE
                kind = "crossing"
            else:
                direction = _TANGENT
                kind = "tangent"
        elif previous is not None:
            assert previous.value is not None
            direction = (
                _POSITIVE_TO_NEGATIVE
                if previous.value > 0.0
                else _NEGATIVE_TO_POSITIVE
            )
            kind = "crossing"
        elif following is not None:
            assert following.value is not None
            direction = (
                _NEGATIVE_TO_POSITIVE
                if following.value > 0.0
                else _POSITIVE_TO_NEGATIVE
            )
            kind = "crossing"
        else:
            direction = _TANGENT
            kind = "tangent"
        roots.append(
            ScalarRoot(
                jd_ut=sample.jd_ut,
                direction=direction,
                kind=kind,
                residual=0.0,
                bracket_start_jd_ut=(
                    previous.jd_ut
                    if previous is not None
                    else sample.jd_ut
                ),
                bracket_end_jd_ut=(
                    following.jd_ut
                    if following is not None
                    else sample.jd_ut
                ),
                iterations=0,
            )
        )
    for left, right in zip(samples, samples[1:]):
        if not (left.evaluable and right.evaluable):
            continue
        assert left.value is not None
        assert right.value is not None
        if left.value * right.value < 0.0:
            roots.append(
                _refine_sign_change(
                    evaluator,
                    left,
                    right,
                    resolved,
                    cache,
                )
            )

    near_zero: list[ScalarNearZero] = []
    refreshed_samples = tuple(
        sorted(cache.values(), key=lambda sample: sample.jd_ut)
    )
    for left, middle, right in zip(
        refreshed_samples,
        refreshed_samples[1:],
        refreshed_samples[2:],
    ):
        if not (
            left.evaluable
            and middle.evaluable
            and right.evaluable
        ):
            continue
        assert left.value is not None
        assert middle.value is not None
        assert right.value is not None
        if not (
            abs(middle.value) <= abs(left.value)
            and abs(middle.value) <= abs(right.value)
            and abs(middle.value) <= resolved.near_zero_tolerance
            and left.value * right.value >= 0.0
        ):
            continue
        minimum = _refine_absolute_minimum(
            evaluator,
            left.jd_ut,
            right.jd_ut,
            resolved,
            cache,
        )
        if minimum is None:
            continue
        sample, iterations = minimum
        assert sample.value is not None
        residual = abs(sample.value)
        if residual <= resolved.root_value_tolerance:
            roots.append(
                ScalarRoot(
                    jd_ut=sample.jd_ut,
                    direction=_TANGENT,
                    kind="tangent",
                    residual=residual,
                    bracket_start_jd_ut=left.jd_ut,
                    bracket_end_jd_ut=right.jd_ut,
                    iterations=iterations,
                )
            )
        elif residual <= resolved.near_zero_tolerance:
            near_zero.append(
                ScalarNearZero(
                    jd_ut=sample.jd_ut,
                    absolute_value=residual,
                    interval_start_jd_ut=left.jd_ut,
                    interval_end_jd_ut=right.jd_ut,
                    iterations=iterations,
                )
            )

    final_samples = tuple(
        sorted(cache.values(), key=lambda sample: sample.jd_ut)
    )
    gaps_between = tuple(
        right.jd_ut - left.jd_ut
        for left, right in zip(
            final_samples,
            final_samples[1:],
        )
    )
    final_roots = _deduplicate_roots(
        roots,
        resolved.root_time_tolerance_days,
    )
    admitted_root_enclosures: list[ScalarRootEnclosure] = []
    for enclosure in _merge_root_enclosures(root_enclosures):
        witness_exists = any(
            enclosure.start_jd_ut
            - resolved.root_time_tolerance_days
            <= root.jd_ut
            <= enclosure.end_jd_ut
            + resolved.root_time_tolerance_days
            for root in final_roots
        )
        boundary_contact = (
            enclosure.start_jd_ut
            <= start_jd_ut + resolved.root_time_tolerance_days
            or enclosure.end_jd_ut
            >= end_jd_ut - resolved.root_time_tolerance_days
        )
        if not witness_exists and not boundary_contact:
            unresolved_intervals.append(
                ScalarUnresolvedInterval(
                    start_jd_ut=enclosure.start_jd_ut,
                    end_jd_ut=enclosure.end_jd_ut,
                    reason="possible_zero_without_witnessed_root",
                )
            )
            continue
        if (
            enclosure.end_jd_ut - enclosure.start_jd_ut
            > resolved.scan_step_days * 2.0
        ):
            unresolved_intervals.append(
                ScalarUnresolvedInterval(
                    start_jd_ut=enclosure.start_jd_ut,
                    end_jd_ut=enclosure.end_jd_ut,
                    reason="root_enclosure_exceeds_admitted_width",
                )
            )
            continue
        admitted_root_enclosures.append(enclosure)
    return ScalarIntervalScan(
        interval_start_jd_ut=start_jd_ut,
        interval_end_jd_ut=end_jd_ut,
        samples=final_samples,
        roots=final_roots,
        near_zero_intervals=tuple(
            sorted(near_zero, key=lambda item: item.jd_ut)
        ),
        gaps=_collect_gaps(final_samples),
        evaluation_count=len(final_samples),
        maximum_sample_gap_days=max(gaps_between),
        minimum_sample_gap_days=min(gaps_between),
        crossing_completeness_state=(
            "certified_lipschitz_zero_enclosure"
            if certificate is not None and not unresolved_intervals
            else "not_certified"
            if certificate is not None
            else "not_requested"
        ),
        crossing_completeness_reason=(
            None
            if certificate is not None and not unresolved_intervals
            else "certificate_left_unresolved_intervals"
            if certificate is not None
            else "no_interval_certificate_supplied"
        ),
        certificate_id=(
            certificate.certificate_id
            if certificate is not None
            else None
        ),
        certificate_maximum_absolute_rate_per_day=(
            certificate.maximum_absolute_rate_per_day
            if certificate is not None
            else None
        ),
        root_enclosures=tuple(admitted_root_enclosures),
        unresolved_intervals=tuple(unresolved_intervals),
    )


def _evaluated_value(
    evaluator: ScalarEvaluator,
    jd_ut: float,
) -> float | None:
    sample = evaluator(jd_ut)
    if not isinstance(sample, ScalarEvaluation):
        raise TypeError("scalar evaluator must return ScalarEvaluation")
    return sample.value


def _select_solar_horizon_root(
    scan: ScalarIntervalScan,
    solar_side: str,
) -> ScalarRoot | None:
    direction = (
        _NEGATIVE_TO_POSITIVE
        if solar_side == "morning"
        else _POSITIVE_TO_NEGATIVE
    )
    candidates = tuple(
        root
        for root in scan.roots
        if root.kind == "crossing" and root.direction == direction
    )
    if not candidates:
        return None
    return candidates[-1] if solar_side == "morning" else candidates[0]


def _boundary_availability_state(
    scan: ScalarIntervalScan,
    *,
    prefix: str,
) -> str:
    values = tuple(
        sample.value
        for sample in scan.samples
        if sample.evaluable and sample.value is not None
    )
    if not values:
        return f"{prefix}_not_evaluable"
    if all(value > 0.0 for value in values):
        return f"{prefix}_always_above_horizon"
    if all(value < 0.0 for value in values):
        return f"{prefix}_always_below_horizon"
    if any(root.kind == "tangent" for root in scan.roots):
        return f"{prefix}_grazes_horizon_without_crossing"
    return f"{prefix}_requested_crossing_missing"


def _scan_gap_reason(
    scan: ScalarIntervalScan,
    *,
    fallback: str = "solver_domain_disconnected",
) -> str:
    reasons = {
        reason
        for gap in scan.gaps
        for reason in gap.reasons
    }
    if len(reasons) == 1:
        return next(iter(reasons))
    return fallback


def _solar_domain_interval(
    evaluator: ScalarEvaluator,
    start_jd_ut: float,
    end_jd_ut: float,
    *,
    solar_side: str,
    domain: tuple[float, float],
    policy: ScalarSearchPolicy,
    certificate: ScalarLipschitzCertificate | None = None,
) -> tuple[tuple[float, float] | None, ScalarIntervalScan]:
    valid, scan = _value_domain_intervals(
        evaluator,
        start_jd_ut,
        end_jd_ut,
        domain=domain,
        policy=policy,
        certificate=certificate,
    )
    if not valid:
        return None, scan
    return (
        valid[-1] if solar_side == "morning" else valid[0],
        scan,
    )


def _value_domain_intervals(
    evaluator: ScalarEvaluator,
    start_jd_ut: float,
    end_jd_ut: float,
    *,
    domain: tuple[float, float],
    policy: ScalarSearchPolicy,
    certificate: ScalarLipschitzCertificate | None = None,
) -> tuple[tuple[tuple[float, float], ...], ScalarIntervalScan]:
    lower, upper = domain
    if (
        not math.isfinite(lower)
        or not math.isfinite(upper)
        or upper <= lower
    ):
        raise ValueError("scalar domain must be finite and increasing")

    def domain_signal(jd_ut: float) -> ScalarEvaluation:
        sample = evaluator(jd_ut)
        if not sample.evaluable:
            return sample
        assert sample.value is not None
        return ScalarEvaluation(
            jd_ut=jd_ut,
            value=min(sample.value - lower, upper - sample.value),
        )

    scan = scan_scalar_interval(
        domain_signal,
        start_jd_ut,
        end_jd_ut,
        policy=policy,
        certificate=certificate,
    )
    if scan.gaps:
        return (), scan

    boundaries = [start_jd_ut, end_jd_ut]
    boundaries.extend(
        root.jd_ut
        for root in scan.roots
        if root.kind == "crossing"
    )
    ordered = sorted(set(boundaries))
    valid: list[tuple[float, float]] = []
    for left, right in zip(ordered, ordered[1:]):
        midpoint = (left + right) * 0.5
        value = _evaluated_value(evaluator, midpoint)
        if value is not None and lower <= value <= upper:
            valid.append((left, right))
    return tuple(valid), scan


def _positive_intervals(
    evaluator: ScalarEvaluator,
    scan: ScalarIntervalScan,
) -> tuple[tuple[float, float, ScalarRoot | None, ScalarRoot | None], ...]:
    crossing_roots = tuple(
        root
        for root in scan.roots
        if root.kind == "crossing"
    )
    boundaries = [
        scan.interval_start_jd_ut,
        *(root.jd_ut for root in crossing_roots),
        scan.interval_end_jd_ut,
    ]
    result: list[
        tuple[float, float, ScalarRoot | None, ScalarRoot | None]
    ] = []
    for index, (left, right) in enumerate(
        zip(boundaries, boundaries[1:])
    ):
        value = _evaluated_value(evaluator, (left + right) * 0.5)
        if value is None or value < 0.0:
            continue
        left_root = crossing_roots[index - 1] if index > 0 else None
        right_root = (
            crossing_roots[index]
            if index < len(crossing_roots)
            else None
        )
        result.append((left, right, left_root, right_root))
    return tuple(result)


def construct_observation_windows(
    observation_day_key: int,
    longitude_deg: float,
    phase_rule: ObservationPhaseRule,
    *,
    target_apparent_horizon_signal: ScalarEvaluator,
    target_true_altitude: ScalarEvaluator,
    solar_apparent_horizon_signal: ScalarEvaluator,
    solar_true_altitude: ScalarEvaluator,
    solar_true_altitude_domain_deg: tuple[float, float] = (
        -18.0,
        0.0,
    ),
    target_true_altitude_domain_deg: tuple[float, float] = (
        -1.0,
        45.0,
    ),
    policy: ScalarSearchPolicy | None = None,
    target_horizon_certificate: (
        ScalarLipschitzCertificate | None
    ) = None,
    target_altitude_certificate: (
        ScalarLipschitzCertificate | None
    ) = None,
    solar_horizon_certificate: (
        ScalarLipschitzCertificate | None
    ) = None,
    solar_altitude_certificate: (
        ScalarLipschitzCertificate | None
    ) = None,
) -> ObservationWindowConstruction:
    """Intersect one phase-day's solar domain with target-above-horizon time."""

    if (
        isinstance(observation_day_key, bool)
        or not isinstance(observation_day_key, int)
    ):
        raise ValueError("observation_day_key must be an integer")
    if (
        isinstance(longitude_deg, bool)
        or not isinstance(longitude_deg, (int, float))
        or not math.isfinite(longitude_deg)
        or not -180.0 <= longitude_deg <= 180.0
    ):
        raise ValueError("longitude_deg must be finite and in [-180, 180]")
    if not isinstance(phase_rule, ObservationPhaseRule):
        raise TypeError("phase_rule must be an ObservationPhaseRule")
    resolved = policy if policy is not None else ScalarSearchPolicy()
    if not isinstance(resolved, ScalarSearchPolicy):
        raise TypeError("policy must be a ScalarSearchPolicy")

    day_start = (
        observation_day_key
        - 0.5
        - longitude_deg / 360.0
    )
    local_noon = day_start + 0.5
    day_end = day_start + 1.0
    side_start, side_end = (
        (day_start, local_noon)
        if phase_rule.solar_side == "morning"
        else (local_noon, day_end)
    )

    solar_horizon_scan = scan_scalar_interval(
        solar_apparent_horizon_signal,
        side_start,
        side_end,
        policy=resolved,
        certificate=solar_horizon_certificate,
    )
    solar_missing_reason = (
        "solar_rise_missing"
        if phase_rule.solar_side == "morning"
        else "solar_set_missing"
    )
    if solar_horizon_scan.gaps:
        return ObservationWindowConstruction(
            observation_day_key=observation_day_key,
            windows=(),
            reason=_scan_gap_reason(solar_horizon_scan),
            geometry_state="solar_horizon_signal_not_evaluable",
            solar_horizon_scan=solar_horizon_scan,
            solar_domain_scan=None,
            target_horizon_scan=None,
            target_domain_scan=None,
        )
    if (
        solar_horizon_certificate is not None
        and solar_horizon_scan.crossing_completeness_state
        != "certified_lipschitz_zero_enclosure"
    ):
        return ObservationWindowConstruction(
            observation_day_key=observation_day_key,
            windows=(),
            reason="crossing_completeness_not_certified",
            geometry_state="solar_horizon_crossing_not_certified",
            solar_horizon_scan=solar_horizon_scan,
            solar_domain_scan=None,
            target_horizon_scan=None,
            target_domain_scan=None,
        )
    solar_horizon_root = _select_solar_horizon_root(
        solar_horizon_scan,
        phase_rule.solar_side,
    )
    if solar_horizon_root is None:
        return ObservationWindowConstruction(
            observation_day_key=observation_day_key,
            windows=(),
            reason=solar_missing_reason,
            geometry_state=_boundary_availability_state(
                solar_horizon_scan,
                prefix="solar",
            ),
            solar_horizon_scan=solar_horizon_scan,
            solar_domain_scan=None,
            target_horizon_scan=None,
            target_domain_scan=None,
        )

    preliminary_start, preliminary_end = (
        (side_start, solar_horizon_root.jd_ut)
        if phase_rule.solar_side == "morning"
        else (solar_horizon_root.jd_ut, side_end)
    )
    solar_domain, solar_domain_scan = _solar_domain_interval(
        solar_true_altitude,
        preliminary_start,
        preliminary_end,
        solar_side=phase_rule.solar_side,
        domain=solar_true_altitude_domain_deg,
        policy=resolved,
        certificate=solar_altitude_certificate,
    )
    if (
        solar_altitude_certificate is not None
        and solar_domain_scan.crossing_completeness_state
        != "certified_lipschitz_zero_enclosure"
    ):
        return ObservationWindowConstruction(
            observation_day_key=observation_day_key,
            windows=(),
            reason="crossing_completeness_not_certified",
            geometry_state="solar_domain_crossing_not_certified",
            solar_horizon_scan=solar_horizon_scan,
            solar_domain_scan=solar_domain_scan,
            target_horizon_scan=None,
            target_domain_scan=None,
        )
    if solar_domain is None:
        reason = (
            _scan_gap_reason(solar_domain_scan)
            if solar_domain_scan.gaps
            else "solar_twilight_below_data_pack_domain"
        )
        return ObservationWindowConstruction(
            observation_day_key=observation_day_key,
            windows=(),
            reason=reason,
            geometry_state=(
                "solar_manifest_domain_not_connected"
                if not solar_domain_scan.gaps
                else "solar_domain_signal_not_evaluable"
            ),
            solar_horizon_scan=solar_horizon_scan,
            solar_domain_scan=solar_domain_scan,
            target_horizon_scan=None,
            target_domain_scan=None,
        )

    target_scan = scan_scalar_interval(
        target_apparent_horizon_signal,
        preliminary_start,
        preliminary_end,
        policy=resolved,
        certificate=target_horizon_certificate,
    )
    if target_scan.gaps:
        return ObservationWindowConstruction(
            observation_day_key=observation_day_key,
            windows=(),
            reason=_scan_gap_reason(target_scan),
            geometry_state="target_horizon_signal_not_evaluable",
            solar_horizon_scan=solar_horizon_scan,
            solar_domain_scan=solar_domain_scan,
            target_horizon_scan=target_scan,
            target_domain_scan=None,
        )
    if (
        target_horizon_certificate is not None
        and target_scan.crossing_completeness_state
        != "certified_lipschitz_zero_enclosure"
    ):
        return ObservationWindowConstruction(
            observation_day_key=observation_day_key,
            windows=(),
            reason="crossing_completeness_not_certified",
            geometry_state="target_horizon_crossing_not_certified",
            solar_horizon_scan=solar_horizon_scan,
            solar_domain_scan=solar_domain_scan,
            target_horizon_scan=target_scan,
            target_domain_scan=None,
        )

    target_domain_intervals, target_domain_scan = (
        _value_domain_intervals(
            target_true_altitude,
            solar_domain[0],
            solar_domain[1],
            domain=target_true_altitude_domain_deg,
            policy=resolved,
            certificate=target_altitude_certificate,
        )
    )
    if target_domain_scan.gaps:
        return ObservationWindowConstruction(
            observation_day_key=observation_day_key,
            windows=(),
            reason=_scan_gap_reason(target_domain_scan),
            geometry_state="target_domain_signal_not_evaluable",
            solar_horizon_scan=solar_horizon_scan,
            solar_domain_scan=solar_domain_scan,
            target_horizon_scan=target_scan,
            target_domain_scan=target_domain_scan,
        )
    if (
        target_altitude_certificate is not None
        and target_domain_scan.crossing_completeness_state
        != "certified_lipschitz_zero_enclosure"
    ):
        return ObservationWindowConstruction(
            observation_day_key=observation_day_key,
            windows=(),
            reason="crossing_completeness_not_certified",
            geometry_state="target_domain_crossing_not_certified",
            solar_horizon_scan=solar_horizon_scan,
            solar_domain_scan=solar_domain_scan,
            target_horizon_scan=target_scan,
            target_domain_scan=target_domain_scan,
        )

    windows: list[ObservationWindow] = []
    for start, end, left_root, right_root in _positive_intervals(
        target_apparent_horizon_signal,
        target_scan,
    ):
        if phase_rule.target_boundary_role == "rising":
            if (
                left_root is None
                or left_root.direction != _NEGATIVE_TO_POSITIVE
            ):
                continue
            boundary = left_root
        else:
            if (
                right_root is None
                or right_root.direction != _POSITIVE_TO_NEGATIVE
            ):
                continue
            boundary = right_root
        for domain_start, domain_end in target_domain_intervals:
            clipped_start = max(start, domain_start)
            clipped_end = min(end, domain_end)
            if clipped_end <= clipped_start:
                continue
            windows.append(
                ObservationWindow(
                    observation_day_key=observation_day_key,
                    start_jd_ut=clipped_start,
                    end_jd_ut=clipped_end,
                    target_boundary_jd_ut=boundary.jd_ut,
                    target_boundary_role=(
                        phase_rule.target_boundary_role
                    ),
                    solar_side=phase_rule.solar_side,
                )
            )

    reason = None
    geometry_state = None
    if not windows:
        anchored_intervals = tuple(
            interval
            for interval in _positive_intervals(
                target_apparent_horizon_signal,
                target_scan,
            )
            if (
                (
                    phase_rule.target_boundary_role == "rising"
                    and interval[2] is not None
                    and interval[2].direction
                    == _NEGATIVE_TO_POSITIVE
                )
                or (
                    phase_rule.target_boundary_role == "setting"
                    and interval[3] is not None
                    and interval[3].direction
                    == _POSITIVE_TO_NEGATIVE
                )
            )
        )
        if anchored_intervals:
            reason = "target_altitude_out_of_domain"
            geometry_state = "target_manifest_domain_not_connected"
        else:
            reason = (
                "target_rise_missing"
                if phase_rule.target_boundary_role == "rising"
                else "target_set_missing"
            )
            geometry_state = _boundary_availability_state(
                target_scan,
                prefix="target",
            )
    return ObservationWindowConstruction(
        observation_day_key=observation_day_key,
        windows=tuple(windows),
        reason=reason,
        geometry_state=geometry_state,
        solar_horizon_scan=solar_horizon_scan,
        solar_domain_scan=solar_domain_scan,
        target_horizon_scan=target_scan,
        target_domain_scan=target_domain_scan,
    )


def _window_peak(
    scan: ScalarIntervalScan,
) -> ScalarEvaluation | None:
    evaluated = tuple(
        sample for sample in scan.samples if sample.evaluable
    )
    if not evaluated:
        return None
    return max(
        evaluated,
        key=lambda sample: sample.value,  # type: ignore[arg-type]
    )


def _solve_visibility_window(
    window: ObservationWindow,
    phase_rule: ObservationPhaseRule,
    margin_evaluator: ScalarEvaluator,
    policy: ScalarSearchPolicy,
    margin_certificate: ScalarLipschitzCertificate | None,
) -> VisibilityWindowSolution:
    padding = max(
        policy.root_time_tolerance_days * 2.0,
        1.0e-10,
    )
    scan_start = window.start_jd_ut + padding
    scan_end = window.end_jd_ut - padding
    if scan_end <= scan_start:
        return VisibilityWindowSolution(
            status="does_not_qualify",
            reason="no_valid_observation_window",
            window=window,
            event_jd_ut=None,
            assessment_jd_ut=None,
            boundary_source=None,
            crossing_direction=None,
            root_residual=None,
            root_bracket_start_jd_ut=None,
            root_bracket_end_jd_ut=None,
            root_iterations=None,
            peak_margin_jd_ut=None,
            peak_margin=None,
            margin_scan=None,
        )

    scan = scan_scalar_interval(
        margin_evaluator,
        scan_start,
        scan_end,
        policy=policy,
        certificate=margin_certificate,
    )
    peak = _window_peak(scan)
    if scan.gaps:
        return VisibilityWindowSolution(
            status="not_evaluable",
            reason=_scan_gap_reason(scan),
            window=window,
            event_jd_ut=None,
            assessment_jd_ut=None,
            boundary_source=None,
            crossing_direction=None,
            root_residual=None,
            root_bracket_start_jd_ut=None,
            root_bracket_end_jd_ut=None,
            root_iterations=None,
            peak_margin_jd_ut=(
                peak.jd_ut if peak is not None else None
            ),
            peak_margin=(
                peak.value if peak is not None else None
            ),
            margin_scan=scan,
        )
    if (
        margin_certificate is not None
        and scan.crossing_completeness_state
        != "certified_lipschitz_zero_enclosure"
    ):
        return VisibilityWindowSolution(
            status="not_evaluable",
            reason="crossing_completeness_not_certified",
            window=window,
            event_jd_ut=None,
            assessment_jd_ut=None,
            boundary_source=None,
            crossing_direction=None,
            root_residual=None,
            root_bracket_start_jd_ut=None,
            root_bracket_end_jd_ut=None,
            root_iterations=None,
            peak_margin_jd_ut=(
                peak.jd_ut if peak is not None else None
            ),
            peak_margin=(
                peak.value if peak is not None else None
            ),
            margin_scan=scan,
        )

    boundary_probe_jd = (
        scan_start
        if phase_rule.target_boundary_role == "rising"
        else scan_end
    )
    boundary_probe = margin_evaluator(boundary_probe_jd)
    if not boundary_probe.evaluable:
        return VisibilityWindowSolution(
            status="not_evaluable",
            reason=(
                boundary_probe.reason
                or "solver_domain_disconnected"
            ),
            window=window,
            event_jd_ut=None,
            assessment_jd_ut=None,
            boundary_source=None,
            crossing_direction=None,
            root_residual=None,
            root_bracket_start_jd_ut=None,
            root_bracket_end_jd_ut=None,
            root_iterations=None,
            peak_margin_jd_ut=(
                peak.jd_ut if peak is not None else None
            ),
            peak_margin=(
                peak.value if peak is not None else None
            ),
            margin_scan=scan,
        )
    assert boundary_probe.value is not None
    if boundary_probe.value >= 0.0:
        boundary_is_window_edge = (
            abs(
                (
                    window.start_jd_ut
                    if phase_rule.target_boundary_role == "rising"
                    else window.end_jd_ut
                )
                - window.target_boundary_jd_ut
            )
            <= policy.root_time_tolerance_days * 4.0
        )
        if not boundary_is_window_edge:
            return VisibilityWindowSolution(
                status="not_evaluable",
                reason="target_altitude_out_of_domain",
                window=window,
                event_jd_ut=None,
                assessment_jd_ut=None,
                boundary_source=None,
                crossing_direction=None,
                root_residual=None,
                root_bracket_start_jd_ut=None,
                root_bracket_end_jd_ut=None,
                root_iterations=None,
                peak_margin_jd_ut=(
                    peak.jd_ut if peak is not None else None
                ),
                peak_margin=(
                    peak.value if peak is not None else None
                ),
                margin_scan=scan,
            )
        return VisibilityWindowSolution(
            status="qualifies",
            reason=None,
            window=window,
            event_jd_ut=window.target_boundary_jd_ut,
            assessment_jd_ut=boundary_probe_jd,
            boundary_source="target_horizon",
            crossing_direction=phase_rule.crossing_direction,
            root_residual=None,
            root_bracket_start_jd_ut=None,
            root_bracket_end_jd_ut=None,
            root_iterations=None,
            peak_margin_jd_ut=(
                peak.jd_ut if peak is not None else None
            ),
            peak_margin=(
                peak.value if peak is not None else None
            ),
            margin_scan=scan,
        )

    candidates = tuple(
        root
        for root in scan.roots
        if (
            root.kind == "crossing"
            and root.direction == phase_rule.crossing_direction
        )
    )
    if not candidates:
        return VisibilityWindowSolution(
            status="does_not_qualify",
            reason=None,
            window=window,
            event_jd_ut=None,
            assessment_jd_ut=None,
            boundary_source=None,
            crossing_direction=None,
            root_residual=None,
            root_bracket_start_jd_ut=None,
            root_bracket_end_jd_ut=None,
            root_iterations=None,
            peak_margin_jd_ut=(
                peak.jd_ut if peak is not None else None
            ),
            peak_margin=(
                peak.value if peak is not None else None
            ),
            margin_scan=scan,
        )
    selected = (
        candidates[0]
        if phase_rule.target_boundary_role == "rising"
        else candidates[-1]
    )
    if selected.residual > policy.root_value_tolerance:
        return VisibilityWindowSolution(
            status="not_evaluable",
            reason="solver_domain_disconnected",
            window=window,
            event_jd_ut=None,
            assessment_jd_ut=None,
            boundary_source=None,
            crossing_direction=None,
            root_residual=selected.residual,
            root_bracket_start_jd_ut=(
                selected.bracket_start_jd_ut
            ),
            root_bracket_end_jd_ut=selected.bracket_end_jd_ut,
            root_iterations=selected.iterations,
            peak_margin_jd_ut=(
                peak.jd_ut if peak is not None else None
            ),
            peak_margin=(
                peak.value if peak is not None else None
            ),
            margin_scan=scan,
        )
    return VisibilityWindowSolution(
        status="qualifies",
        reason=None,
        window=window,
        event_jd_ut=selected.jd_ut,
        assessment_jd_ut=selected.jd_ut,
        boundary_source="visibility_margin",
        crossing_direction=selected.direction,
        root_residual=selected.residual,
        root_bracket_start_jd_ut=selected.bracket_start_jd_ut,
        root_bracket_end_jd_ut=selected.bracket_end_jd_ut,
        root_iterations=selected.iterations,
        peak_margin_jd_ut=(
            peak.jd_ut if peak is not None else None
        ),
        peak_margin=peak.value if peak is not None else None,
        margin_scan=scan,
    )


def classify_observation_day(
    construction: ObservationWindowConstruction,
    phase_rule: ObservationPhaseRule,
    margin_evaluator: ScalarEvaluator,
    *,
    policy: ScalarSearchPolicy | None = None,
    margin_certificate: ScalarLipschitzCertificate | None = None,
) -> ObservationDaySolution:
    """Classify one day without treating missing evidence as invisibility."""

    if not isinstance(
        construction,
        ObservationWindowConstruction,
    ):
        raise TypeError(
            "construction must be an ObservationWindowConstruction"
        )
    if not isinstance(phase_rule, ObservationPhaseRule):
        raise TypeError("phase_rule must be an ObservationPhaseRule")
    resolved = policy if policy is not None else ScalarSearchPolicy()
    if not isinstance(resolved, ScalarSearchPolicy):
        raise TypeError("policy must be a ScalarSearchPolicy")

    if construction.reason in {
        "target_rise_missing",
        "target_set_missing",
    } and construction.geometry_state in {
        "target_always_above_horizon",
        "target_always_below_horizon",
        "target_grazes_horizon_without_crossing",
        "target_requested_crossing_missing",
    }:
        return ObservationDaySolution(
            observation_day_key=construction.observation_day_key,
            status="does_not_qualify",
            reason=None,
            selected_window=None,
            window_solutions=(),
            construction=construction,
        )
    if construction.reason is not None:
        return ObservationDaySolution(
            observation_day_key=construction.observation_day_key,
            status="not_evaluable",
            reason=construction.reason,
            selected_window=None,
            window_solutions=(),
            construction=construction,
        )

    solutions = tuple(
        _solve_visibility_window(
            window,
            phase_rule,
            margin_evaluator,
            resolved,
            margin_certificate,
        )
        for window in construction.windows
    )
    if any(solution.status == "not_evaluable" for solution in solutions):
        first = next(
            solution
            for solution in solutions
            if solution.status == "not_evaluable"
        )
        return ObservationDaySolution(
            observation_day_key=construction.observation_day_key,
            status="not_evaluable",
            reason=first.reason,
            selected_window=None,
            window_solutions=solutions,
            construction=construction,
        )

    qualifying = tuple(
        solution
        for solution in solutions
        if solution.status == "qualifies"
    )
    if qualifying:
        selected = (
            qualifying[0]
            if phase_rule.target_boundary_role == "rising"
            else qualifying[-1]
        )
        return ObservationDaySolution(
            observation_day_key=construction.observation_day_key,
            status="qualifies",
            reason=None,
            selected_window=selected,
            window_solutions=solutions,
            construction=construction,
        )
    return ObservationDaySolution(
        observation_day_key=construction.observation_day_key,
        status="does_not_qualify",
        reason=None,
        selected_window=None,
        window_solutions=solutions,
        construction=construction,
    )


def select_owned_phase_transition(
    candidate_day_keys: tuple[int, ...],
    phase_rule: ObservationPhaseRule,
    classifier: Callable[[int], ObservationDaySolution],
) -> PhaseTransitionSelection:
    """Apply Phase 0 first-day or last-day ownership with one guard day."""

    if not candidate_day_keys:
        raise ValueError("candidate_day_keys must not be empty")
    if any(
        isinstance(key, bool) or not isinstance(key, int)
        for key in candidate_day_keys
    ):
        raise ValueError("candidate_day_keys must contain integers")
    if tuple(sorted(set(candidate_day_keys))) != candidate_day_keys:
        raise ValueError(
            "candidate_day_keys must be strictly increasing and unique"
        )
    if not isinstance(phase_rule, ObservationPhaseRule):
        raise TypeError("phase_rule must be an ObservationPhaseRule")
    if not callable(classifier):
        raise TypeError("classifier must be callable")

    cache: dict[int, ObservationDaySolution] = {}

    def resolve(day_key: int) -> ObservationDaySolution:
        result = cache.get(day_key)
        if result is None:
            result = classifier(day_key)
            if not isinstance(result, ObservationDaySolution):
                raise TypeError(
                    "classifier must return ObservationDaySolution"
                )
            if result.observation_day_key != day_key:
                raise ValueError(
                    "classifier returned a different observation day"
                )
            cache[day_key] = result
        return result

    if phase_rule.day_ownership == "first":
        for day_key in candidate_day_keys:
            current = resolve(day_key)
            previous = resolve(day_key - 1)
            if current.status != "qualifies":
                continue
            if previous.status == "does_not_qualify":
                return PhaseTransitionSelection(
                    status="evaluated",
                    reason=None,
                    selected_day=current,
                    comparison_day=previous,
                    classified_days=tuple(
                        cache[key] for key in sorted(cache)
                    ),
                )
            if previous.status == "not_evaluable":
                return PhaseTransitionSelection(
                    status="not_evaluable",
                    reason="phase_ownership_not_evaluable",
                    selected_day=current,
                    comparison_day=previous,
                    classified_days=tuple(
                        cache[key] for key in sorted(cache)
                    ),
                )
    else:
        for day_key in candidate_day_keys:
            current = resolve(day_key)
            following = resolve(day_key + 1)
            if current.status != "qualifies":
                continue
            if following.status == "does_not_qualify":
                return PhaseTransitionSelection(
                    status="evaluated",
                    reason=None,
                    selected_day=current,
                    comparison_day=following,
                    classified_days=tuple(
                        cache[key] for key in sorted(cache)
                    ),
                )
            if following.status == "not_evaluable":
                return PhaseTransitionSelection(
                    status="not_evaluable",
                    reason="phase_ownership_not_evaluable",
                    selected_day=current,
                    comparison_day=following,
                    classified_days=tuple(
                        cache[key] for key in sorted(cache)
                    ),
                )

    classified = tuple(cache[key] for key in sorted(cache))
    if any(day.status == "not_evaluable" for day in classified):
        first_missing = next(
            day for day in classified if day.status == "not_evaluable"
        )
        return PhaseTransitionSelection(
            status="not_evaluable",
            reason=(
                first_missing.reason
                or "phase_ownership_not_evaluable"
            ),
            selected_day=None,
            comparison_day=None,
            classified_days=classified,
        )
    return PhaseTransitionSelection(
        status="not_found",
        reason="no_phase_transition_in_search_window",
        selected_day=None,
        comparison_day=None,
        classified_days=classified,
    )
