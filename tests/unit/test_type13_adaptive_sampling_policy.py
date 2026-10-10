"""Shared asteroid/comet Type-13 adaptive sampling policy."""

from __future__ import annotations

import math

import pytest

from moira import moira_native
from scripts import type13_adaptive_sampling as adaptive


def _quadratic_states(epochs: list[float]) -> list[list[float]]:
    center = 2451560.25
    x: list[float] = []
    vx: list[float] = []
    for epoch in epochs:
        offset = epoch - center
        x.append(100_000_000.0 + 1000.0 * offset * offset)
        vx.append(2000.0 * offset / adaptive.SECONDS_PER_DAY)
    count = len(epochs)
    return [x, [0.0] * count, [0.0] * count, vx, [0.0] * count, [0.0] * count]


def _exact_fetch(
    epochs: list[float],
    query_kind: str,
) -> tuple[list[float], list[list[float]], list[dict[str, object]]]:
    return epochs, _quadratic_states(epochs), [{"query_kind": query_kind}]


def test_uniform_cadence_rejects_wrong_horizons_step() -> None:
    with pytest.raises(RuntimeError, match="cadence mismatch"):
        adaptive.validate_uniform_cadence(
            [2451545.0, 2451545.0 + 1.0 / 24.0],
            expected_step_days=3.0,
        )


def test_request_chunking_never_splits_a_dense_refinement_interval() -> None:
    epochs = [0.0, 0.5, 1.0, 1.5, 10.0, 10.5, 11.0, 11.5]

    chunks = adaptive.refinement_request_chunks(
        epochs,
        max_count=5,
        max_span_days=100.0,
    )

    assert chunks == [epochs[:4], epochs[4:]]


def test_shared_policy_certifies_exact_quadratic_extremum() -> None:
    base_epochs = [2451545.0 + 10.0 * index for index in range(4)]
    epochs, states, certificate, receipts = adaptive.build_certified_adaptive_series(
        base_epochs,
        _quadratic_states(base_epochs),
        _exact_fetch,
    )

    assert certificate["passed"] is True
    assert certificate["accepted_refinement_step_days"] == 1.0
    assert certificate["base_extremum_brackets"] == 1
    assert certificate["levels"][0]["worst_event_time_error_seconds"] < 1.0e-3
    assert certificate["levels"][0]["worst_event_distance_error_km"] < 1.0e-6
    assert certificate["levels"][0]["evaluated_event_count"] == 1
    assert certificate["levels"][0]["event_type_counts"] == {
        "PERICENTER": 1,
        "APOCENTER": 0,
    }
    assert "events" not in certificate["levels"][0]
    assert len(epochs) > len(base_epochs)
    assert len(states) == 6
    assert receipts == [{"query_kind": "adaptive_level_1d"}]


def test_failed_level_halves_cadence_before_admission(monkeypatch) -> None:
    base_epochs = [2451545.0 + 10.0 * index for index in range(4)]
    seen_steps: list[float] = []

    def fake_certificate(**kwargs):
        step = kwargs["refinement_step_days"]
        seen_steps.append(step)
        return {
            "refinement_step_days": step,
            "passed": math.isclose(step, 0.5),
        }

    monkeypatch.setattr(adaptive, "_level_certificate", fake_certificate)

    _epochs, _states, certificate, receipts = adaptive.build_certified_adaptive_series(
        base_epochs,
        _quadratic_states(base_epochs),
        _exact_fetch,
    )

    assert seen_steps == [1.0, 0.5]
    assert certificate["accepted_refinement_step_days"] == 0.5
    assert [receipt["query_kind"] for receipt in receipts] == [
        "adaptive_level_1d",
        "adaptive_level_0.5d",
    ]


def test_caller_can_select_a_deeper_dyadic_refinement_floor(monkeypatch) -> None:
    base_epochs = [2451545.0 + 10.0 * index for index in range(4)]
    seen_steps: list[float] = []

    def fake_certificate(**kwargs):
        step = kwargs["refinement_step_days"]
        seen_steps.append(step)
        return {
            "refinement_step_days": step,
            "passed": math.isclose(step, 1.0 / 64.0),
        }

    monkeypatch.setattr(adaptive, "_level_certificate", fake_certificate)

    _epochs, _states, certificate, _receipts = (
        adaptive.build_certified_adaptive_series(
            base_epochs,
            _quadratic_states(base_epochs),
            _exact_fetch,
            minimum_refinement_step_days=1.0 / 64.0,
        )
    )

    assert seen_steps == [1.0, 0.5, 0.25, 0.125, 0.0625, 0.03125, 0.015625]
    assert certificate["accepted_refinement_step_days"] == 1.0 / 64.0


@pytest.mark.parametrize("step_days", [0.0, -0.5, 0.1, 2.0, math.inf])
def test_refinement_floor_must_be_a_positive_reachable_halving(step_days) -> None:
    with pytest.raises(ValueError, match="minimum_refinement_step_days"):
        adaptive.sampling_policy(minimum_refinement_step_days=step_days)


def test_policy_is_shared_and_gate_visible() -> None:
    policy = adaptive.sampling_policy()

    assert policy["policy_version"] == (
        "moira-small-body-type13-apsidal-adaptive-v4"
    )
    assert policy["base_step_days"] == 10.0
    assert policy["window_size"] == 7
    assert policy["integration_coherence"] == (
        "every_exact_request_includes_coverage_endpoints"
    )
    assert policy["certification"] == {
        "witness_step_ratio": 0.5,
        "distance_absolute_km": 0.1495978707,
        "event_time_absolute_seconds": 8.64,
        "failure_action": "halve_refinement_step_or_reject_body",
    }


def test_local_evaluator_matches_full_native_window_selection() -> None:
    epochs = [2451545.0 + 0.5 * index for index in range(100)]
    states = _quadratic_states(epochs)
    epoch = 2451563.375

    expected = moira_native.spk_type13_record(epochs, states, 7, epoch)
    actual = adaptive._evaluate(epochs, states, 7, epoch)

    assert actual == pytest.approx(expected, abs=0.0)


def test_certificate_keeps_only_worst_event_receipts() -> None:
    base_epochs = [2451545.0 + 10.0 * index for index in range(10)]

    _epochs, _states, certificate, _receipts = (
        adaptive.build_certified_adaptive_series(
            base_epochs,
            _quadratic_states(base_epochs),
            _exact_fetch,
        )
    )

    level = certificate["levels"][0]
    assert level["evaluated_event_count"] == level["authority_extrema_detected"]
    assert set(level["worst_event_time_case"]) == {
        "kind",
        "authority_epoch_jd_tdb",
        "time_error_seconds",
        "distance_error_km",
    }
    assert set(level["worst_event_distance_case"]) == set(
        level["worst_event_time_case"]
    )
    assert "events" not in level
