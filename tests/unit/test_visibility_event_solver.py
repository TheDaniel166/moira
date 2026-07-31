"""Adversarial tests for the Phase 3 physical event-solver core."""

from __future__ import annotations

import math

import pytest

from moira._visibility_event_solver import (
    ObservationDaySolution,
    ObservationPhaseRule,
    ObservationWindow,
    ObservationWindowConstruction,
    ScalarEvaluation,
    ScalarIntervalScan,
    ScalarLipschitzCertificate,
    ScalarSearchPolicy,
    classify_observation_day,
    construct_observation_windows,
    scan_scalar_interval,
    select_owned_phase_transition,
)


_BASE_JD = 2_450_000.0


def _scalar(function):
    def evaluate(jd_ut: float) -> ScalarEvaluation:
        return ScalarEvaluation(jd_ut=jd_ut, value=function(jd_ut))

    return evaluate


def _policy(*, scan_step_days: float = 0.05) -> ScalarSearchPolicy:
    return ScalarSearchPolicy(
        scan_step_days=scan_step_days,
        adaptive_minimum_step_days=1.0e-4,
        root_time_tolerance_days=1.0e-8,
        root_value_tolerance=1.0e-8,
        near_zero_tolerance=1.0e-3,
        curvature_tolerance=1.0e-4,
    )


def test_multiple_crossings_are_all_bracketed_and_refined() -> None:
    roots = (0.2, 0.4, 0.7)

    def signal(jd_ut: float) -> float:
        offset = jd_ut - _BASE_JD
        return math.prod(offset - root for root in roots)

    scan = scan_scalar_interval(
        _scalar(signal),
        _BASE_JD,
        _BASE_JD + 1.0,
        policy=_policy(),
    )

    crossings = tuple(root for root in scan.roots if root.kind == "crossing")
    assert len(crossings) == 3
    assert tuple(root.direction for root in crossings) == (
        "negative_to_positive",
        "positive_to_negative",
        "negative_to_positive",
    )
    for actual, expected in zip(crossings, roots, strict=True):
        assert actual.jd_ut == pytest.approx(
            _BASE_JD + expected,
            abs=2.0e-7,
        )
        assert actual.residual <= 1.0e-8


def test_lipschitz_certificate_finds_two_crossings_hidden_by_coarse_endpoints(
) -> None:
    """Same-sign coarse samples cannot conceal a valid crossing pair."""

    def signal(jd_ut: float) -> float:
        offset = jd_ut - _BASE_JD
        return (offset - 0.205) * (offset - 0.215)

    scan = scan_scalar_interval(
        _scalar(signal),
        _BASE_JD,
        _BASE_JD + 1.0,
        policy=ScalarSearchPolicy(
            scan_step_days=0.1,
            adaptive_minimum_step_days=0.01,
            root_time_tolerance_days=1.0e-6,
            root_value_tolerance=1.0e-8,
            near_zero_tolerance=1.0e-3,
            curvature_tolerance=1.0e9,
            maximum_adaptive_depth=1,
        ),
        certificate=ScalarLipschitzCertificate(
            certificate_id="test-polynomial-rate-bound",
            maximum_absolute_rate_per_day=2.0,
            source_receipt_sha256="a" * 64,
        ),
    )

    crossings = tuple(
        root for root in scan.roots if root.kind == "crossing"
    )
    assert tuple(root.jd_ut - _BASE_JD for root in crossings) == (
        pytest.approx(0.205, abs=2.0e-6),
        pytest.approx(0.215, abs=2.0e-6),
    )
    assert (
        scan.crossing_completeness_state
        == "certified_lipschitz_zero_enclosure"
    )
    assert scan.unresolved_intervals == ()
    assert len(scan.root_enclosures) == 2


def test_certificate_fails_closed_when_possible_zero_has_no_witness() -> None:
    """A discontinuous callback cannot borrow a continuous rate receipt."""

    def evaluator(jd_ut: float) -> ScalarEvaluation:
        offset = jd_ut - _BASE_JD
        if math.isclose(offset, 0.5, abs_tol=1.0e-12):
            return ScalarEvaluation(
                jd_ut=jd_ut,
                value=None,
                reason="synthetic_discontinuity",
            )
        return ScalarEvaluation(jd_ut=jd_ut, value=1.0)

    scan = scan_scalar_interval(
        evaluator,
        _BASE_JD,
        _BASE_JD + 1.0,
        policy=_policy(scan_step_days=0.1),
        certificate=ScalarLipschitzCertificate(
            certificate_id="test-gap-rate-bound",
            maximum_absolute_rate_per_day=1.0,
            source_receipt_sha256="b" * 64,
        ),
    )

    assert scan.crossing_completeness_state == "not_certified"
    assert scan.unresolved_intervals
    assert scan.gaps


def test_tangent_is_detected_without_fabricating_a_crossing() -> None:
    contact = _BASE_JD + 0.50321
    scan = scan_scalar_interval(
        _scalar(lambda jd_ut: (jd_ut - contact) ** 2),
        _BASE_JD,
        _BASE_JD + 1.0,
        policy=_policy(),
    )

    tangencies = tuple(root for root in scan.roots if root.kind == "tangent")
    assert len(tangencies) == 1
    assert tangencies[0].direction == "tangent"
    assert tangencies[0].jd_ut == pytest.approx(contact, abs=2.0e-5)
    assert tangencies[0].residual <= 1.0e-8
    assert not tuple(
        root for root in scan.roots if root.kind == "crossing"
    )


def test_exact_sampled_tangent_is_not_misclassified_as_crossing() -> None:
    contact = _BASE_JD + 0.5
    scan = scan_scalar_interval(
        _scalar(lambda jd_ut: (jd_ut - contact) ** 2),
        _BASE_JD,
        _BASE_JD + 1.0,
        policy=_policy(scan_step_days=0.1),
    )

    assert len(scan.roots) == 1
    assert scan.roots[0].kind == "tangent"
    assert scan.roots[0].direction == "tangent"
    assert scan.roots[0].jd_ut == contact


def test_near_zero_minimum_remains_diagnostic_not_event_root() -> None:
    contact = _BASE_JD + 0.50321
    scan = scan_scalar_interval(
        _scalar(lambda jd_ut: (jd_ut - contact) ** 2 + 5.0e-4),
        _BASE_JD,
        _BASE_JD + 1.0,
        policy=_policy(),
    )

    assert scan.roots == ()
    assert len(scan.near_zero_intervals) == 1
    assert scan.near_zero_intervals[0].absolute_value == pytest.approx(
        5.0e-4,
        abs=1.0e-8,
    )


def test_non_evaluable_samples_create_a_gap_instead_of_negative_truth() -> None:
    def evaluator(jd_ut: float) -> ScalarEvaluation:
        offset = jd_ut - _BASE_JD
        if 0.4 <= offset <= 0.6:
            return ScalarEvaluation(
                jd_ut=jd_ut,
                value=None,
                reason="test_dependency_missing",
            )
        return ScalarEvaluation(jd_ut=jd_ut, value=offset - 0.5)

    scan = scan_scalar_interval(
        evaluator,
        _BASE_JD,
        _BASE_JD + 1.0,
        policy=_policy(),
    )

    assert scan.roots == ()
    assert scan.gaps
    assert {
        reason
        for gap in scan.gaps
        for reason in gap.reasons
    } == {"test_dependency_missing"}


def test_scan_step_convergence_preserves_crossing_times() -> None:
    signal = _scalar(
        lambda jd_ut: math.sin(
            6.0 * math.pi * (jd_ut - _BASE_JD) + 0.37
        )
    )
    coarse = scan_scalar_interval(
        signal,
        _BASE_JD,
        _BASE_JD + 1.0,
        policy=_policy(scan_step_days=0.04),
    )
    fine = scan_scalar_interval(
        signal,
        _BASE_JD,
        _BASE_JD + 1.0,
        policy=_policy(scan_step_days=0.02),
    )

    coarse_crossings = tuple(
        root for root in coarse.roots if root.kind == "crossing"
    )
    fine_crossings = tuple(
        root for root in fine.roots if root.kind == "crossing"
    )
    assert len(coarse_crossings) == len(fine_crossings) == 6
    assert tuple(root.jd_ut for root in coarse_crossings) == pytest.approx(
        tuple(root.jd_ut for root in fine_crossings),
        abs=2.0e-7,
    )


def test_repeated_execution_is_structurally_deterministic() -> None:
    evaluator = _scalar(
        lambda jd_ut: (jd_ut - _BASE_JD - 0.25)
        * (jd_ut - _BASE_JD - 0.75)
    )
    first = scan_scalar_interval(
        evaluator,
        _BASE_JD,
        _BASE_JD + 1.0,
        policy=_policy(),
    )
    second = scan_scalar_interval(
        evaluator,
        _BASE_JD,
        _BASE_JD + 1.0,
        policy=_policy(),
    )

    assert first == second


def test_morning_rising_window_intersects_solar_domain_and_target_horizon() -> None:
    day_key = 100
    day_start = day_key - 0.5
    sunrise = day_start + 0.30
    target_rise = day_start + 0.16

    construction = construct_observation_windows(
        day_key,
        0.0,
        ObservationPhaseRule(
            solar_side="morning",
            target_boundary_role="rising",
            crossing_direction="negative_to_positive",
            day_ownership="first",
        ),
        target_apparent_horizon_signal=_scalar(
            lambda jd_ut: jd_ut - target_rise
        ),
        target_true_altitude=_scalar(
            lambda jd_ut: jd_ut - target_rise
        ),
        solar_apparent_horizon_signal=_scalar(
            lambda jd_ut: jd_ut - sunrise
        ),
        solar_true_altitude=_scalar(
            lambda jd_ut: (
                (jd_ut - sunrise) * (20.0 / 0.30)
            )
        ),
        policy=_policy(scan_step_days=0.02),
    )

    assert construction.reason is None
    assert len(construction.windows) == 1
    window = construction.windows[0]
    assert window.target_boundary_jd_ut == pytest.approx(
        target_rise,
        abs=2.0e-7,
    )
    assert window.start_jd_ut == pytest.approx(
        target_rise,
        abs=2.0e-7,
    )
    assert window.end_jd_ut == pytest.approx(sunrise, abs=2.0e-7)


def test_evening_setting_window_intersects_solar_domain_and_target_horizon() -> None:
    day_key = 100
    local_noon = day_key
    sunset = local_noon + 0.20
    target_set = local_noon + 0.35

    construction = construct_observation_windows(
        day_key,
        0.0,
        ObservationPhaseRule(
            solar_side="evening",
            target_boundary_role="setting",
            crossing_direction="positive_to_negative",
            day_ownership="last",
        ),
        target_apparent_horizon_signal=_scalar(
            lambda jd_ut: target_set - jd_ut
        ),
        target_true_altitude=_scalar(
            lambda jd_ut: target_set - jd_ut
        ),
        solar_apparent_horizon_signal=_scalar(
            lambda jd_ut: sunset - jd_ut
        ),
        solar_true_altitude=_scalar(
            lambda jd_ut: (
                (sunset - jd_ut) * (20.0 / 0.30)
            )
        ),
        policy=_policy(scan_step_days=0.02),
    )

    assert construction.reason is None
    assert len(construction.windows) == 1
    window = construction.windows[0]
    assert window.start_jd_ut == pytest.approx(sunset, abs=2.0e-7)
    assert window.end_jd_ut == pytest.approx(
        target_set,
        abs=2.0e-7,
    )
    assert window.target_boundary_jd_ut == pytest.approx(
        target_set,
        abs=2.0e-7,
    )


@pytest.mark.parametrize(
    ("solar_signal", "reason", "geometry_state"),
    (
        (
            -5.0,
            "solar_rise_missing",
            "solar_always_below_horizon",
        ),
        (
            5.0,
            "solar_rise_missing",
            "solar_always_above_horizon",
        ),
    ),
)
def test_polar_solar_geometry_returns_typed_missing_boundary(
    solar_signal: float,
    reason: str,
    geometry_state: str,
) -> None:
    construction = construct_observation_windows(
        100,
        0.0,
        ObservationPhaseRule(
            solar_side="morning",
            target_boundary_role="rising",
            crossing_direction="negative_to_positive",
            day_ownership="first",
        ),
        target_apparent_horizon_signal=_scalar(lambda _jd: 1.0),
        target_true_altitude=_scalar(lambda _jd: 1.0),
        solar_apparent_horizon_signal=_scalar(
            lambda _jd: solar_signal
        ),
        solar_true_altitude=_scalar(lambda _jd: -9.0),
        policy=_policy(scan_step_days=0.02),
    )

    assert construction.windows == ()
    assert construction.reason == reason
    assert construction.geometry_state == geometry_state


def test_circumpolar_target_does_not_fabricate_a_rising_boundary() -> None:
    day_key = 100
    day_start = day_key - 0.5
    sunrise = day_start + 0.30
    construction = construct_observation_windows(
        day_key,
        0.0,
        ObservationPhaseRule(
            solar_side="morning",
            target_boundary_role="rising",
            crossing_direction="negative_to_positive",
            day_ownership="first",
        ),
        target_apparent_horizon_signal=_scalar(lambda _jd: 1.0),
        target_true_altitude=_scalar(lambda _jd: 1.0),
        solar_apparent_horizon_signal=_scalar(
            lambda jd_ut: jd_ut - sunrise
        ),
        solar_true_altitude=_scalar(
            lambda jd_ut: (
                (jd_ut - sunrise) * (20.0 / 0.30)
            )
        ),
        policy=_policy(scan_step_days=0.02),
    )

    assert construction.windows == ()
    assert construction.reason == "target_rise_missing"
    assert (
        construction.geometry_state
        == "target_always_above_horizon"
    )


def test_never_rising_target_is_distinct_from_circumpolar_target() -> None:
    day_key = 100
    day_start = day_key - 0.5
    sunrise = day_start + 0.30
    construction = construct_observation_windows(
        day_key,
        0.0,
        _morning_rising_rule(),
        target_apparent_horizon_signal=_scalar(lambda _jd: -1.0),
        target_true_altitude=_scalar(lambda _jd: -1.0),
        solar_apparent_horizon_signal=_scalar(
            lambda jd_ut: jd_ut - sunrise
        ),
        solar_true_altitude=_scalar(
            lambda jd_ut: (
                (jd_ut - sunrise) * (20.0 / 0.30)
            )
        ),
        policy=_policy(scan_step_days=0.02),
    )

    assert construction.reason == "target_rise_missing"
    assert (
        construction.geometry_state
        == "target_always_below_horizon"
    )


@pytest.mark.parametrize(
    ("target_signal", "geometry_state"),
    (
        (1.0, "target_always_above_horizon"),
        (-1.0, "target_always_below_horizon"),
    ),
)
def test_missing_target_set_preserves_above_or_below_geometry_state(
    target_signal: float,
    geometry_state: str,
) -> None:
    day_key = 100
    local_noon = float(day_key)
    sunset = local_noon + 0.20
    construction = construct_observation_windows(
        day_key,
        0.0,
        ObservationPhaseRule(
            solar_side="evening",
            target_boundary_role="setting",
            crossing_direction="positive_to_negative",
            day_ownership="last",
        ),
        target_apparent_horizon_signal=_scalar(
            lambda _jd: target_signal
        ),
        target_true_altitude=_scalar(
            lambda _jd: target_signal
        ),
        solar_apparent_horizon_signal=_scalar(
            lambda jd_ut: sunset - jd_ut
        ),
        solar_true_altitude=_scalar(
            lambda jd_ut: (
                (sunset - jd_ut) * (20.0 / 0.30)
            )
        ),
        policy=_policy(scan_step_days=0.02),
    )

    assert construction.reason == "target_set_missing"
    assert construction.geometry_state == geometry_state


def _empty_scan(start: float, end: float) -> ScalarIntervalScan:
    samples = (
        ScalarEvaluation(jd_ut=start, value=1.0),
        ScalarEvaluation(jd_ut=end, value=1.0),
    )
    return ScalarIntervalScan(
        interval_start_jd_ut=start,
        interval_end_jd_ut=end,
        samples=samples,
        roots=(),
        near_zero_intervals=(),
        gaps=(),
        evaluation_count=2,
        maximum_sample_gap_days=end - start,
        minimum_sample_gap_days=end - start,
    )


def _construction(
    day_key: int,
    *,
    start: float,
    end: float,
    role: str = "rising",
) -> ObservationWindowConstruction:
    scan = _empty_scan(start, end)
    boundary = start if role == "rising" else end
    return ObservationWindowConstruction(
        observation_day_key=day_key,
        windows=(
            ObservationWindow(
                observation_day_key=day_key,
                start_jd_ut=start,
                end_jd_ut=end,
                target_boundary_jd_ut=boundary,
                target_boundary_role=role,
                solar_side="morning",
            ),
        ),
        reason=None,
        geometry_state=None,
        solar_horizon_scan=scan,
        solar_domain_scan=scan,
        target_horizon_scan=scan,
        target_domain_scan=scan,
    )


def _morning_rising_rule() -> ObservationPhaseRule:
    return ObservationPhaseRule(
        solar_side="morning",
        target_boundary_role="rising",
        crossing_direction="negative_to_positive",
        day_ownership="first",
    )


def test_day_classification_uses_margin_root_not_first_visible_sample() -> None:
    start = _BASE_JD + 0.2
    end = _BASE_JD + 0.4
    root = _BASE_JD + 0.31
    result = classify_observation_day(
        _construction(10, start=start, end=end),
        _morning_rising_rule(),
        _scalar(lambda jd_ut: jd_ut - root),
        policy=_policy(scan_step_days=0.01),
    )

    assert result.status == "qualifies"
    assert result.selected_window is not None
    assert result.selected_window.boundary_source == "visibility_margin"
    assert result.selected_window.event_jd_ut == pytest.approx(
        root,
        abs=2.0e-7,
    )
    assert (
        result.selected_window.root_residual is not None
        and result.selected_window.root_residual <= 1.0e-8
    )


def test_day_classification_can_assign_transition_to_target_horizon() -> None:
    start = _BASE_JD + 0.2
    end = _BASE_JD + 0.4
    result = classify_observation_day(
        _construction(10, start=start, end=end),
        _morning_rising_rule(),
        _scalar(lambda _jd_ut: 0.5),
        policy=_policy(scan_step_days=0.01),
    )

    assert result.status == "qualifies"
    assert result.selected_window is not None
    assert result.selected_window.boundary_source == "target_horizon"
    assert result.selected_window.event_jd_ut == start
    assert result.selected_window.root_residual is None


def _day(
    day_key: int,
    status: str,
    *,
    reason: str | None = None,
) -> ObservationDaySolution:
    start = _BASE_JD + day_key
    construction = ObservationWindowConstruction(
        observation_day_key=day_key,
        windows=(),
        reason=reason,
        geometry_state=None,
        solar_horizon_scan=_empty_scan(start, start + 0.1),
        solar_domain_scan=None,
        target_horizon_scan=None,
        target_domain_scan=None,
    )
    return ObservationDaySolution(
        observation_day_key=day_key,
        status=status,
        reason=reason,
        selected_window=None,
        window_solutions=(),
        construction=construction,
    )


def test_first_day_ownership_requires_previous_nonqualifying_day() -> None:
    states = {
        9: _day(9, "does_not_qualify"),
        10: _day(10, "qualifies"),
    }
    result = select_owned_phase_transition(
        (10,),
        _morning_rising_rule(),
        states.__getitem__,
    )

    assert result.status == "evaluated"
    assert result.selected_day == states[10]
    assert result.comparison_day == states[9]


def test_last_day_ownership_requires_following_nonqualifying_day() -> None:
    rule = ObservationPhaseRule(
        solar_side="evening",
        target_boundary_role="setting",
        crossing_direction="positive_to_negative",
        day_ownership="last",
    )
    states = {
        10: _day(10, "qualifies"),
        11: _day(11, "does_not_qualify"),
    }
    result = select_owned_phase_transition(
        (10,),
        rule,
        states.__getitem__,
    )

    assert result.status == "evaluated"
    assert result.selected_day == states[10]
    assert result.comparison_day == states[11]


def test_missing_guard_day_evidence_fails_closed() -> None:
    states = {
        9: _day(
            9,
            "not_evaluable",
            reason="solar_rise_missing",
        ),
        10: _day(10, "qualifies"),
    }
    result = select_owned_phase_transition(
        (10,),
        _morning_rising_rule(),
        states.__getitem__,
    )

    assert result.status == "not_evaluable"
    assert result.reason == "phase_ownership_not_evaluable"


def test_evaluable_search_without_transition_is_explicit_not_found() -> None:
    states = {
        9: _day(9, "does_not_qualify"),
        10: _day(10, "does_not_qualify"),
        11: _day(11, "does_not_qualify"),
    }
    result = select_owned_phase_transition(
        (10, 11),
        _morning_rising_rule(),
        states.__getitem__,
    )

    assert result.status == "not_found"
    assert result.reason == "no_phase_transition_in_search_window"
