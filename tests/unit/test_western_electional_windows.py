"""Synthetic Phase 10 transition and exactness-law tests."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import moira
import moira.facade as facade
import moira.western_electional as western
import moira._western_electional_windows as windows
from moira._western_electional_judgement import (
    WesternElectionalJudgementDoctrine,
    WesternElectionalJudgementSelection,
    assemble_western_electional_judgement,
)
from moira.classical_perfection import LillyPerfectionKind


def _enum(value: str):
    return SimpleNamespace(value=value)


def _selection() -> WesternElectionalJudgementSelection:
    return WesternElectionalJudgementSelection(
        doctrine=WesternElectionalJudgementDoctrine.SAHL,
        matter_profile_id="sahl_sale_v1",
        perfection_profile_id="lilly_1647_perfection_v1",
        perfection_significator_a="Moon",
        perfection_significator_b="Venus",
        perfection_interval_days=7.0,
        election_class="ephemeral",
        natal_input_provided=False,
        natal_jd_ut=None,
        natal_latitude=None,
        natal_longitude=None,
        natal_house_system=None,
        unavoidable_time_urgency=None,
        moon_flow_previous_window=None,
        moon_flow_previous_lookback_days=None,
        moon_flow_modern=None,
        sahl_burnt_path_variant="sahl_text_indeterminate_no_numeric_endpoints",
        sahl_eighth_rule_variant="arabic_al_rijal_twelfth_part",
    )


def _judgement(
    jd_ut: float,
    *,
    after: bool,
    impeded_after: bool = False,
    events=(),
):
    rule = SimpleNamespace(
        rule_id="synthetic_transition_rule",
        state=_enum("triggered" if after and impeded_after else "clear"),
        source_reference="synthetic transition fixture",
    )
    moon = SimpleNamespace(
        profile_id="sahl_moon_condition_v1",
        status=_enum(
            "one_or_more_profile_impediments"
            if after and impeded_after
            else "clear_of_profile_impediments"
        ),
        rules=(rule,),
    )
    matter = SimpleNamespace(
        jd_ut=jd_ut,
        profile_id=_enum("sahl_sale_v1"),
        status=_enum("clear_of_explicit_profile_gates"),
        moon_condition=moon,
        clauses=(),
        authorities=("Sahl synthetic transition fixture",),
        reader_provenance="synthetic-reader",
    )
    perfection = SimpleNamespace(
        jd_start=jd_ut,
        jd_end=jd_ut + 7.0,
        profile_id="lilly_1647_perfection_v1",
        present_kinds=(
            LillyPerfectionKind.TRANSLATION if after else LillyPerfectionKind.DIRECT,
        ),
        indeterminate_kinds=(),
        events=events,
        witnesses=(),
        authorities=("Lilly synthetic transition fixture",),
        reader_provenance="synthetic-reader",
    )
    return assemble_western_electional_judgement(
        latitude=0.0,
        longitude=0.0,
        requested_house_system="R",
        selection=_selection(),
        matter_profile=matter,
        perfection_path=perfection,
    )


def _scan(monkeypatch, policy, *, impeded_after=False, evaluator=None):
    def default_evaluator(jd_ut, *args, **kwargs):
        return _judgement(jd_ut, after=jd_ut >= 5.0, impeded_after=impeded_after)

    monkeypatch.setattr(
        windows,
        "western_electional_judgement_at",
        default_evaluator if evaluator is None else evaluator,
    )
    return windows.scan_western_electional_judgement_windows(
        0.0,
        10.0,
        0.0,
        0.0,
        house_system="R",
        matter_profile_id="sahl_sale_v1",
        perfection_significator_a="Moon",
        perfection_significator_b="Venus",
        perfection_interval_days=7.0,
        sahl_burnt_path_variant="sahl_text_indeterminate_no_numeric_endpoints",
        sahl_eighth_rule_variant="arabic_al_rijal_twelfth_part",
        reader=object(),
        scan_policy=policy,
    )


def test_sampled_mode_preserves_coarse_transition_bracket(monkeypatch) -> None:
    result = _scan(
        monkeypatch,
        windows.WesternElectionalJudgementWindowPolicy(step_days=4.0),
    )
    assert len(result.windows) == 2
    boundary = result.windows[0].end_boundary
    assert boundary is result.windows[1].start_boundary
    assert boundary.resolution is windows.WesternElectionalBoundaryResolution.SAMPLED_BRACKET
    assert (boundary.bracket_start_jd_ut, boundary.bracket_end_jd_ut) == (4.0, 8.0)
    assert boundary.doctrine_boundary_exact is False
    assert result.total_evaluation_count == result.initial_sample_count == 4
    assert result.exact_boundary_claimed is result.continuous_truth_claimed is False


def test_partial_mode_refines_observed_transition_to_tolerance(monkeypatch) -> None:
    policy = windows.WesternElectionalJudgementWindowPolicy(
        mode=windows.WesternElectionalWindowScanMode.PARTIALLY_EVENT_REFINED,
        step_days=4.0,
        transition_tolerance_seconds=30.0,
        max_refinement_iterations=20,
    )
    result = _scan(monkeypatch, policy)
    boundary = result.windows[0].end_boundary
    assert boundary.resolution is (
        windows.WesternElectionalBoundaryResolution.ADAPTIVELY_REFINED_BRACKET
    )
    assert boundary.bracket_start_jd_ut < 5.0 <= boundary.bracket_end_jd_ut
    assert boundary.bracket_width_seconds <= 30.0
    assert result.total_evaluation_count > result.initial_sample_count
    cause_ids = {item.cause_id for item in boundary.causes}
    assert "perfection_present_kinds:direct_perfection" in cause_ids
    assert "perfection_present_kinds:translation_of_light" in cause_ids


def test_coincident_output_changes_share_one_boundary(monkeypatch) -> None:
    policy = windows.WesternElectionalJudgementWindowPolicy(
        mode="partially_event_refined",
        step_days=4.0,
        transition_tolerance_seconds=60.0,
        max_refinement_iterations=20,
    )
    result = _scan(monkeypatch, policy, impeded_after=True)
    boundary = result.windows[0].end_boundary
    cause_ids = {item.cause_id for item in boundary.causes}
    assert {
        "judgement_state",
        "moon_status",
        "moon_rule_states:synthetic_transition_rule",
        "component_states:general_moon_condition",
    } <= cause_ids


def test_scan_resource_limits_reject_before_evaluation(monkeypatch) -> None:
    calls = 0

    def fake(*args, **kwargs):
        nonlocal calls
        calls += 1
        raise AssertionError("resource-invalid scan evaluated a candidate")

    monkeypatch.setattr(windows, "western_electional_judgement_at", fake)
    policy = windows.WesternElectionalJudgementWindowPolicy(
        step_days=1.0,
        max_initial_samples=3,
        max_evaluations=3,
    )
    with pytest.raises(ValueError, match="initial sample count"):
        windows.scan_western_electional_judgement_windows(
            0.0,
            5.0,
            0.0,
            0.0,
            house_system="R",
            matter_profile_id="sahl_sale_v1",
            perfection_significator_a="Moon",
            perfection_significator_b="Venus",
            perfection_interval_days=7.0,
            reader=object(),
            scan_policy=policy,
        )
    assert calls == 0


def test_policy_rejects_exactness_and_refinement_mismatch() -> None:
    with pytest.raises(ValueError, match="sampled mode"):
        windows.WesternElectionalJudgementWindowPolicy(
            mode="sampled",
            max_refinement_iterations=1,
        )
    with pytest.raises(ValueError, match="fixed"):
        windows.WesternElectionalJudgementWindowPolicy(
            exact_boundary_claimed=True,
        )


def test_partial_mode_uses_visible_event_as_non_causal_boundary_seed(
    monkeypatch,
) -> None:
    event = SimpleNamespace(
        event_id="synthetic_perfection_at_5",
        jd_ut=5.0,
        kind=_enum("direct_perfection"),
    )

    def fake(jd_ut, *args, **kwargs):
        return _judgement(
            jd_ut,
            after=jd_ut >= 5.0,
            events=(event,),
        )

    monkeypatch.setattr(windows, "western_electional_judgement_at", fake)
    result = windows.scan_western_electional_judgement_windows(
        0.0,
        10.0,
        0.0,
        0.0,
        house_system="R",
        matter_profile_id="sahl_sale_v1",
        perfection_significator_a="Moon",
        perfection_significator_b="Venus",
        perfection_interval_days=7.0,
        reader=object(),
        scan_policy=windows.WesternElectionalJudgementWindowPolicy(
            mode="partially_event_refined",
            step_days=4.0,
            max_refinement_iterations=4,
        ),
    )

    assert result.event_seed_count == 1
    assert result.candidate_events == (result.windows[0].end_boundary.candidate_events[0],)
    assert result.candidate_events[0].jd_ut == 5.0
    assert result.candidate_events[0].causal_status == (
        "candidate_boundary_seed_not_asserted_cause"
    )
    assert result.windows[0].end_boundary.doctrine_boundary_exact is False


def test_partial_mode_rejects_event_seed_and_evaluation_resource_overruns(
    monkeypatch,
) -> None:
    def event_rich(jd_ut, *args, **kwargs):
        event = SimpleNamespace(
            event_id=f"event_{jd_ut}",
            jd_ut=jd_ut + 0.1,
            kind=_enum("direct_perfection"),
        )
        return _judgement(jd_ut, after=jd_ut >= 5.0, events=(event,))

    monkeypatch.setattr(windows, "western_electional_judgement_at", event_rich)
    with pytest.raises(ValueError, match="candidate event count"):
        _scan(
            monkeypatch,
            windows.WesternElectionalJudgementWindowPolicy(
                mode="partially_event_refined",
                step_days=4.0,
                max_refinement_iterations=1,
                max_event_seeds=2,
            ),
            evaluator=event_rich,
        )

    def no_events(jd_ut, *args, **kwargs):
        return _judgement(jd_ut, after=jd_ut >= 5.0)

    monkeypatch.setattr(windows, "western_electional_judgement_at", no_events)
    with pytest.raises(ValueError, match="max_evaluations"):
        _scan(
            monkeypatch,
            windows.WesternElectionalJudgementWindowPolicy(
                mode="partially_event_refined",
                step_days=4.0,
                max_refinement_iterations=2,
                max_initial_samples=4,
                max_evaluations=4,
            ),
            evaluator=no_events,
        )


def test_transition_and_window_limits_reject_observed_overruns(monkeypatch) -> None:
    with pytest.raises(ValueError, match="max_transitions"):
        _scan(
            monkeypatch,
            windows.WesternElectionalJudgementWindowPolicy(
                step_days=4.0,
                max_transitions=0,
            ),
        )
    with pytest.raises(ValueError, match="max_windows"):
        _scan(
            monkeypatch,
            windows.WesternElectionalJudgementWindowPolicy(
                step_days=4.0,
                max_windows=1,
            ),
        )


def test_equal_endpoint_signatures_can_conceal_an_interior_transition(
    monkeypatch,
) -> None:
    def hidden(jd_ut, *args, **kwargs):
        interior = 4.5 <= jd_ut < 5.5
        return _judgement(jd_ut, after=interior)

    monkeypatch.setattr(windows, "western_electional_judgement_at", hidden)
    result = windows.scan_western_electional_judgement_windows(
        0.0,
        10.0,
        0.0,
        0.0,
        house_system="R",
        matter_profile_id="sahl_sale_v1",
        perfection_significator_a="Moon",
        perfection_significator_b="Venus",
        perfection_interval_days=7.0,
        reader=object(),
        scan_policy=windows.WesternElectionalJudgementWindowPolicy(
            mode="partially_event_refined",
            step_days=4.0,
            max_refinement_iterations=8,
        ),
    )

    assert len(result.windows) == 1
    assert result.transition_count == 0
    assert result.boundary_inventory_complete is False
    assert result.continuous_truth_claimed is False


def test_phase10_surface_is_public_at_every_library_layer() -> None:
    names = {
        "WesternElectionalWindowScanMode",
        "WesternElectionalBoundaryResolution",
        "WesternElectionalJudgementWindowPolicy",
        "WesternElectionalJudgementSignature",
        "WesternElectionalTransitionCause",
        "WesternElectionalCandidateEvent",
        "WesternElectionalWindowBoundary",
        "WesternElectionalJudgementWindow",
        "WesternElectionalJudgementWindowScan",
        "WESTERN_ELECTIONAL_JUDGEMENT_WINDOWS_V1",
        "scan_western_electional_judgement_windows",
    }
    for name in names:
        assert hasattr(western, name)
        assert hasattr(facade, name)
        assert hasattr(moira, name)
    assert hasattr(moira.Moira, "western_electional_judgement_windows")
