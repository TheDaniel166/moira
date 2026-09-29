"""Shared adaptive Type-13 sampling for small-body apsidal products.

The catalog builders own network access and artifact publication.  This module
owns the common numerical policy: locate radial-velocity sign crossings on a
coarse base series, add exact local nodes, and certify the resulting Type-13
interpolant against exact half-step Horizons witnesses.  A level is admitted
only when both sampled radial distance and recovered extremum time/distance
meet the existing Stage 2 gates.
"""

from __future__ import annotations

import bisect
from collections.abc import Callable
import math
from typing import Any

from moira import moira_native


POLICY_VERSION = "moira-small-body-type13-apsidal-adaptive-v4"
BASE_STEP_DAYS = 10.0
WINDOW_SIZE = 7
INITIAL_REFINEMENT_STEP_DAYS = 1.0
MIN_REFINEMENT_STEP_DAYS = 1.0 / 16.0
REFINEMENT_PADDING_DAYS = 4.0
DISTANCE_GATE_KM = 0.1495978707
EVENT_TIME_GATE_SECONDS = 8.64
SECONDS_PER_DAY = 86_400.0
_EPOCH_KEY_DIGITS = 12

VectorSeries = tuple[list[float], list[list[float]]]
FetchExact = Callable[[list[float], str], tuple[list[float], list[list[float]], list[dict[str, Any]]]]
LevelProgress = Callable[[dict[str, object]], None]


def sampling_policy(
    *,
    base_step_days: float = BASE_STEP_DAYS,
    window_size: int = WINDOW_SIZE,
) -> dict[str, object]:
    """Return the common, release-visible adaptive sampling policy."""

    return {
        "policy_version": POLICY_VERSION,
        "mode": "certified_adaptive_radial_extrema",
        "base_step_days": base_step_days,
        "initial_refinement_step_days": INITIAL_REFINEMENT_STEP_DAYS,
        "minimum_refinement_step_days": MIN_REFINEMENT_STEP_DAYS,
        "refinement_padding_days": REFINEMENT_PADDING_DAYS,
        "refined_extrema": ["PERICENTER", "APOCENTER"],
        "time_tags": "nonuniform",
        "integration_coherence": "every_exact_request_includes_coverage_endpoints",
        "window_size": window_size,
        "certification": {
            "witness_step_ratio": 0.5,
            "distance_absolute_km": DISTANCE_GATE_KM,
            "event_time_absolute_seconds": EVENT_TIME_GATE_SECONDS,
            "failure_action": "halve_refinement_step_or_reject_body",
        },
    }


def _validate_series(epochs: list[float], states: list[list[float]]) -> None:
    if not epochs:
        raise ValueError("epochs must not be empty")
    if len(states) != 6 or any(len(axis) != len(epochs) for axis in states):
        raise ValueError("states must have shape (6, len(epochs))")
    if any(left >= right for left, right in zip(epochs, epochs[1:])):
        raise ValueError("epochs must be strictly increasing")


def validate_uniform_cadence(
    epochs: list[float],
    *,
    expected_step_days: float,
    tolerance_days: float = 5.0e-9,
) -> None:
    """Reject a Horizons reply whose actual epochs do not match its request."""

    if len(epochs) < 2:
        return
    for left, right in zip(epochs, epochs[1:]):
        if abs((right - left) - expected_step_days) > tolerance_days:
            raise RuntimeError(
                "Horizons response cadence mismatch: "
                f"requested {expected_step_days:g} days, received {right - left:.12g}"
            )


def radial_velocity_km_s(state: list[float] | tuple[float, ...]) -> float:
    x, y, z, vx, vy, vz = state
    radius = math.sqrt(x * x + y * y + z * z)
    if not math.isfinite(radius) or radius <= 0.0:
        raise RuntimeError("invalid zero or non-finite small-body radius")
    return (x * vx + y * vy + z * vz) / radius


def radial_velocity_at(states: list[list[float]], index: int) -> float:
    return radial_velocity_km_s([states[axis][index] for axis in range(6)])


def crosses_radial_extremum(left: float, right: float) -> bool:
    return (
        (left <= 0.0 <= right or left >= 0.0 >= right)
        and not (left == 0.0 and right == 0.0)
    )


def extremum_refinement_intervals(
    epochs: list[float],
    states: list[list[float]],
    *,
    padding_days: float = REFINEMENT_PADDING_DAYS,
) -> tuple[list[tuple[float, float]], int]:
    """Return merged padded intervals around every base-grid radial crossing."""

    _validate_series(epochs, states)
    intervals: list[tuple[float, float]] = []
    bracket_count = 0
    for index in range(len(epochs) - 1):
        if not crosses_radial_extremum(
            radial_velocity_at(states, index),
            radial_velocity_at(states, index + 1),
        ):
            continue
        bracket_count += 1
        intervals.append(
            (
                max(epochs[0], epochs[index] - padding_days),
                min(epochs[-1], epochs[index + 1] + padding_days),
            )
        )

    merged: list[tuple[float, float]] = []
    for start, stop in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], stop))
        else:
            merged.append((start, stop))
    return merged, bracket_count


def epochs_for_intervals(
    intervals: list[tuple[float, float]],
    *,
    step_days: float,
) -> list[float]:
    if not math.isfinite(step_days) or step_days <= 0.0:
        raise ValueError("step_days must be positive and finite")
    epochs: dict[str, float] = {}
    for start, stop in intervals:
        if stop < start:
            raise ValueError("refinement interval stop precedes start")
        count = int(math.floor((stop - start) / step_days + 1.0e-10))
        for offset in range(count + 1):
            epoch = start + offset * step_days
            epochs[f"{epoch:.{_EPOCH_KEY_DIGITS}f}"] = epoch
        last = start + count * step_days
        if stop - last > 5.0e-10:
            epochs[f"{stop:.{_EPOCH_KEY_DIGITS}f}"] = stop
    return sorted(epochs.values())


def refinement_request_chunks(
    epochs: list[float],
    *,
    max_count: int,
    max_span_days: float,
) -> list[list[float]]:
    """Pack complete local-refinement intervals into bounded requests.

    Splitting one dense interval across two Horizons requests can mix slightly
    different numerical propagations inside a single Type-13 window.  The
    interval gaps encoded in ``epochs`` are therefore discovered first, and
    only whole runs are packed into a request.
    """

    if not epochs:
        return []
    if max_count < 1 or max_span_days <= 0.0:
        raise ValueError("request chunk bounds must be positive")
    deltas = [right - left for left, right in zip(epochs, epochs[1:])]
    positive = [delta for delta in deltas if delta > 5.0e-10]
    nominal_step = min(positive, default=math.inf)
    runs: list[list[float]] = []
    current = [epochs[0]]
    for epoch, delta in zip(epochs[1:], deltas):
        if delta > nominal_step * 1.5 + 5.0e-10:
            runs.append(current)
            current = []
        current.append(epoch)
    runs.append(current)

    chunks: list[list[float]] = []
    current = []
    for run in runs:
        if len(run) > max_count:
            raise RuntimeError(
                "one adaptive refinement interval exceeds the Horizons TLIST limit"
            )
        if current and (
            len(current) + len(run) > max_count
            or run[-1] - current[0] > max_span_days
        ):
            chunks.append(current)
            current = []
        current.extend(run)
    if current:
        chunks.append(current)
    return chunks


def merge_vectors(
    base_epochs: list[float],
    base_states: list[list[float]],
    additions: list[VectorSeries],
) -> VectorSeries:
    """Merge exact vector series, with later additions replacing duplicates."""

    _validate_series(base_epochs, base_states)
    by_epoch: dict[str, tuple[float, tuple[float, ...]]] = {}

    def add(epochs: list[float], states: list[list[float]]) -> None:
        _validate_series(epochs, states)
        for index, epoch in enumerate(epochs):
            by_epoch[f"{epoch:.{_EPOCH_KEY_DIGITS}f}"] = (
                epoch,
                tuple(states[axis][index] for axis in range(6)),
            )

    add(base_epochs, base_states)
    for epochs, states in additions:
        if epochs:
            add(epochs, states)
    ordered = sorted(by_epoch.values(), key=lambda item: item[0])
    return (
        [item[0] for item in ordered],
        [[item[1][axis] for item in ordered] for axis in range(6)],
    )


def _series_from_cache(
    epochs: list[float],
    cache: dict[str, tuple[float, ...]],
) -> VectorSeries:
    return (
        epochs,
        [[cache[f"{epoch:.{_EPOCH_KEY_DIGITS}f}"][axis] for epoch in epochs] for axis in range(6)],
    )


def _state_radius_km(state: list[float] | tuple[float, ...]) -> float:
    return math.sqrt(sum(component * component for component in state[:3]))


def _evaluate(
    epochs: list[float],
    states: list[list[float]],
    window_size: int,
    epoch: float,
) -> list[float]:
    index = bisect.bisect_left(epochs, epoch)
    start = max(0, index - window_size // 2)
    start = min(start, len(epochs) - window_size)
    local_epochs = epochs[start : start + window_size]
    local_states = [axis[start : start + window_size] for axis in states]
    return list(
        moira_native.spk_type13_record(
            local_epochs,
            local_states,
            window_size,
            epoch,
        )
    )


def _bisect_radial_root(
    evaluator: Callable[[float], list[float]],
    left: float,
    right: float,
) -> tuple[float, list[float]]:
    left_state = evaluator(left)
    right_state = evaluator(right)
    left_g = radial_velocity_km_s(left_state)
    right_g = radial_velocity_km_s(right_state)
    if not crosses_radial_extremum(left_g, right_g):
        raise RuntimeError("interpolant does not bracket the authority radial root")
    for _ in range(80):
        midpoint = 0.5 * (left + right)
        middle_state = evaluator(midpoint)
        middle_g = radial_velocity_km_s(middle_state)
        if abs(right - left) * SECONDS_PER_DAY <= 1.0e-4:
            return midpoint, middle_state
        if crosses_radial_extremum(left_g, middle_g):
            right = midpoint
            right_g = middle_g
        else:
            left = midpoint
            left_g = middle_g
    midpoint = 0.5 * (left + right)
    return midpoint, evaluator(midpoint)


def _level_certificate(
    *,
    candidate_epochs: list[float],
    candidate_states: list[list[float]],
    authority_epochs: list[float],
    authority_states: list[list[float]],
    node_epochs: set[str],
    base_bracket_count: int,
    refinement_step_days: float,
    window_size: int,
) -> dict[str, object]:
    candidate = lambda epoch: _evaluate(  # noqa: E731 - compact numerical closure
        candidate_epochs, candidate_states, window_size, epoch
    )
    authority = lambda epoch: _evaluate(  # noqa: E731 - compact numerical closure
        authority_epochs, authority_states, window_size, epoch
    )

    crossings: list[tuple[int, float, float]] = []
    for index in range(len(authority_epochs) - 1):
        if crosses_radial_extremum(
            radial_velocity_at(authority_states, index),
            radial_velocity_at(authority_states, index + 1),
        ):
            crossings.append((index, authority_epochs[index], authority_epochs[index + 1]))

    worst_witness_radial = 0.0
    worst_witness_cartesian = 0.0
    worst_event_time = 0.0
    worst_event_distance = 0.0
    evaluated_event_count = 0
    event_type_counts = {"PERICENTER": 0, "APOCENTER": 0}
    worst_time_event: dict[str, object] | None = None
    worst_distance_event: dict[str, object] | None = None
    witness_indices: set[int] = set()
    for index, _left, _right in crossings:
        for candidate_index in range(
            max(0, index - 3),
            min(len(authority_epochs), index + 5),
        ):
            if f"{authority_epochs[candidate_index]:.{_EPOCH_KEY_DIGITS}f}" not in node_epochs:
                witness_indices.add(candidate_index)

    for index in sorted(witness_indices):
        epoch = authority_epochs[index]
        fitted = candidate(epoch)
        exact = [authority_states[axis][index] for axis in range(6)]
        worst_witness_radial = max(
            worst_witness_radial,
            abs(_state_radius_km(fitted) - _state_radius_km(exact)),
        )
        worst_witness_cartesian = max(
            worst_witness_cartesian,
            math.sqrt(sum((fitted[axis] - exact[axis]) ** 2 for axis in range(3))),
        )

    root_failure: str | None = None
    for _index, left, right in crossings:
        try:
            authority_epoch, authority_state = _bisect_radial_root(authority, left, right)
            candidate_epoch, candidate_state = _bisect_radial_root(candidate, left, right)
        except RuntimeError as exc:
            root_failure = str(exc)
            break
        time_error = abs(candidate_epoch - authority_epoch) * SECONDS_PER_DAY
        distance_error = abs(
            _state_radius_km(candidate_state) - _state_radius_km(authority_state)
        )
        kind = (
            "PERICENTER"
            if radial_velocity_at(authority_states, _index) < 0.0
            else "APOCENTER"
        )
        event = {
            "kind": kind,
            "authority_epoch_jd_tdb": authority_epoch,
            "time_error_seconds": time_error,
            "distance_error_km": distance_error,
        }
        evaluated_event_count += 1
        event_type_counts[kind] += 1
        if worst_time_event is None or time_error > worst_event_time:
            worst_time_event = event
        if worst_distance_event is None or distance_error > worst_event_distance:
            worst_distance_event = event
        worst_event_time = max(worst_event_time, time_error)
        worst_event_distance = max(worst_event_distance, distance_error)

    passed = (
        root_failure is None
        and len(crossings) == base_bracket_count
        and worst_witness_radial <= DISTANCE_GATE_KM
        and worst_event_distance <= DISTANCE_GATE_KM
        and worst_event_time <= EVENT_TIME_GATE_SECONDS
    )
    return {
        "refinement_step_days": refinement_step_days,
        "authority_witness_step_days": refinement_step_days / 2.0,
        "base_extremum_brackets": base_bracket_count,
        "authority_extrema_detected": len(crossings),
        "witness_count": len(witness_indices),
        "worst_witness_radial_error_km": worst_witness_radial,
        "worst_witness_cartesian_error_km": worst_witness_cartesian,
        "worst_event_time_error_seconds": worst_event_time,
        "worst_event_distance_error_km": worst_event_distance,
        "evaluated_event_count": evaluated_event_count,
        "event_type_counts": event_type_counts,
        "worst_event_time_case": worst_time_event,
        "worst_event_distance_case": worst_distance_event,
        "root_failure": root_failure,
        "passed": passed,
    }


def build_certified_adaptive_series(
    base_epochs: list[float],
    base_states: list[list[float]],
    fetch_exact: FetchExact,
    *,
    window_size: int = WINDOW_SIZE,
    progress: LevelProgress | None = None,
) -> tuple[list[float], list[list[float]], dict[str, object], list[dict[str, Any]]]:
    """Refine and certify one body's apsidal Type-13 representation.

    ``fetch_exact`` must return exact Horizons vectors for precisely the
    requested epochs.  The function is intentionally resumable at the caller's
    network/cache layer; within one call it also avoids re-fetching epochs that
    were obtained at a coarser level.
    """

    _validate_series(base_epochs, base_states)
    intervals, bracket_count = extremum_refinement_intervals(base_epochs, base_states)
    if bracket_count == 0:
        return (
            base_epochs,
            base_states,
            {
                "status": "no_radial_extrema_in_coverage",
                "base_extremum_brackets": 0,
                "accepted_refinement_step_days": None,
                "levels": [],
                "passed": True,
            },
            [],
        )

    receipts: list[dict[str, Any]] = []
    levels: list[dict[str, object]] = []
    step = INITIAL_REFINEMENT_STEP_DAYS
    while step + 1.0e-15 >= MIN_REFINEMENT_STEP_DAYS:
        witness_epochs = epochs_for_intervals(intervals, step_days=step / 2.0)
        returned_epochs, returned_states, new_receipts = fetch_exact(
            witness_epochs,
            f"adaptive_level_{step:g}d",
        )
        _validate_series(returned_epochs, returned_states)
        if len(returned_epochs) != len(witness_epochs) or any(
            abs(actual - expected) > 5.0e-10
            for actual, expected in zip(returned_epochs, witness_epochs)
        ):
            raise RuntimeError("exact refinement response does not match requested epochs")
        exact_cache = {
            f"{epoch:.{_EPOCH_KEY_DIGITS}f}": tuple(
                returned_states[axis][index] for axis in range(6)
            )
            for index, epoch in enumerate(returned_epochs)
        }
        receipts.extend(new_receipts)

        node_epochs = epochs_for_intervals(intervals, step_days=step)
        node_series = _series_from_cache(node_epochs, exact_cache)
        authority_series = _series_from_cache(witness_epochs, exact_cache)
        candidate_epochs, candidate_states = merge_vectors(
            base_epochs,
            base_states,
            [node_series],
        )
        level = _level_certificate(
            candidate_epochs=candidate_epochs,
            candidate_states=candidate_states,
            authority_epochs=authority_series[0],
            authority_states=authority_series[1],
            node_epochs={f"{epoch:.{_EPOCH_KEY_DIGITS}f}" for epoch in node_epochs},
            base_bracket_count=bracket_count,
            refinement_step_days=step,
            window_size=window_size,
        )
        levels.append(level)
        if progress is not None:
            progress(level)
        if level["passed"]:
            return (
                candidate_epochs,
                candidate_states,
                {
                    "status": "certified",
                    "base_extremum_brackets": bracket_count,
                    "refinement_intervals": len(intervals),
                    "accepted_refinement_step_days": step,
                    "distance_gate_km": DISTANCE_GATE_KM,
                    "event_time_gate_seconds": EVENT_TIME_GATE_SECONDS,
                    "levels": levels,
                    "passed": True,
                },
                receipts,
            )
        step /= 2.0

    raise RuntimeError(
        "adaptive Type-13 sampling failed its apsidal gates at the minimum "
        f"{MIN_REFINEMENT_STEP_DAYS:g}-day cadence; levels={levels!r}"
    )
