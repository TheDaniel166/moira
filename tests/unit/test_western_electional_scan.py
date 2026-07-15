"""Doctrine and invariant tests for named Western profile scanning."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import moira.western_electional as western
import moira._western_electional_scan as scan_module


class _Reader:
    path = "synthetic-scan-reader.bsp"


def _evaluation(status: str, profile_id: str, *, jd_ut: float = 0.0):
    rule_state = (
        "triggered"
        if status == "one_or_more_profile_impediments"
        else "not_evaluable"
        if status == "indeterminate"
        else "clear"
    )
    return SimpleNamespace(
        jd_ut=jd_ut,
        status=SimpleNamespace(value=status),
        profile_id=profile_id,
        profile_version="1.0.0",
        rules=(SimpleNamespace(rule_id=f"rule_{rule_state}", state=SimpleNamespace(value=rule_state)),),
    )


def test_scan_qualifies_exact_statuses_and_merges_only_sampled_truth(monkeypatch) -> None:
    statuses = {
        0: "clear_of_profile_impediments",
        1: "clear_of_profile_impediments",
        2: "one_or_more_profile_impediments",
        3: "clear_of_profile_impediments",
    }

    def fake_ramesey(chart, **_kwargs):
        index = round((chart.jd_ut - 100.0) / 0.25)
        return _evaluation(
            statuses[index], "ramesey_moon_condition_v1", jd_ut=chart.jd_ut
        )

    monkeypatch.setattr(western, "evaluate_ramesey_moon_condition", fake_ramesey)
    monkeypatch.setattr(
        scan_module,
        "create_chart",
        lambda jd_ut, *_args, **_kwargs: SimpleNamespace(jd_ut=jd_ut),
    )
    monkeypatch.setattr(scan_module, "void_periods_in_range", lambda *_args, **_kwargs: [])
    policy = western.WesternElectionalProfileScanPolicy(
        qualifying_statuses=(western.WesternElectionalQualificationStatus.CLEAR,),
        step_days=0.25,
        merge_gap_days=0.3,
        max_scan_points=4,
    )
    result = western.scan_western_electional_profile(
        100.0,
        100.75,
        40.0,
        -75.0,
        house_system="P",
        profile_id=western.WesternElectionalProfileId.RAMESEY_MOON_CONDITION_V1,
        scan_policy=policy,
        reader=_Reader(),
    )
    assert result.scan_point_count == 4
    assert [item.count for item in result.status_counts] == [3, 1, 0]
    assert [window.qualifying_jds for window in result.windows] == [
        (100.0, 100.25),
        (100.75,),
    ]
    assert result.scoring == "not_provided"
    assert result.continuous_boundary_claim == "not_provided"
    assert [sample.status.value for sample in result.samples] == list(statuses.values())
    assert result.samples[2].triggered_rule_ids == ("rule_triggered",)
    assert [sample.qualifies for sample in result.samples] == [True, True, False, True]


def test_scan_can_select_triggered_and_indeterminate_without_scoring(monkeypatch) -> None:
    sequence = iter(
        ("one_or_more_profile_impediments", "indeterminate", "clear_of_profile_impediments")
    )

    def fake_dorotheus(*_args, **_kwargs):
        status = next(sequence)
        jd_ut = _args[0]
        return _evaluation(status, "dorotheus_moon_condition_v1", jd_ut=jd_ut)

    monkeypatch.setattr(western, "dorotheus_moon_condition_at", fake_dorotheus)
    policy = western.WesternElectionalProfileScanPolicy(
        step_days=0.5,
        max_scan_points=3,
        qualifying_statuses=(
            western.WesternElectionalQualificationStatus.TRIGGERED,
            western.WesternElectionalQualificationStatus.INDETERMINATE,
        ),
    )
    result = western.scan_western_electional_profile(
        10.0,
        11.0,
        0.0,
        0.0,
        house_system="P",
        profile_id="dorotheus_moon_condition_v1",
        scan_policy=policy,
        reader=_Reader(),
    )
    assert result.windows[0].qualifying_jds == (10.0, 10.5)
    assert result.policy.qualifying_statuses == (
        western.WesternElectionalQualificationStatus.TRIGGERED,
        western.WesternElectionalQualificationStatus.INDETERMINATE,
    )


def test_scan_enforces_point_bound_and_profile_owned_parameters(monkeypatch) -> None:
    policy = western.WesternElectionalProfileScanPolicy(
        qualifying_statuses=(western.WesternElectionalQualificationStatus.CLEAR,),
        step_days=0.25,
        max_scan_points=3,
    )
    with pytest.raises(ValueError, match="scan point count 5 exceeds maximum 3"):
        western.scan_western_electional_profile(
            10.0,
            11.0,
            0.0,
            0.0,
            house_system="P",
            profile_id="ramesey_moon_condition_v1",
            scan_policy=policy,
            reader=_Reader(),
        )

    with pytest.raises(ValueError, match="Sahl variants"):
        western.scan_western_electional_profile(
            10.0,
            10.25,
            0.0,
            0.0,
            house_system="P",
            profile_id="ramesey_moon_condition_v1",
            sahl_burnt_path_variant="fall_degrees_19_libra_to_3_scorpio",
            scan_policy=policy,
            reader=_Reader(),
        )


def test_sahl_scan_preserves_resolved_variant_parameters(monkeypatch) -> None:
    def fake_sahl(chart, **_kwargs):
        result = _evaluation(
            "indeterminate", "sahl_moon_condition_v1", jd_ut=chart.jd_ut
        )
        result.burnt_path_variant = SimpleNamespace(
            value="fall_degrees_19_libra_to_3_scorpio"
        )
        result.eighth_rule_variant = SimpleNamespace(
            value="arabic_al_rijal_twelfth_part"
        )
        return result

    monkeypatch.setattr(western, "evaluate_sahl_moon_condition", fake_sahl)
    monkeypatch.setattr(
        scan_module,
        "create_chart",
        lambda jd_ut, *_args, **_kwargs: SimpleNamespace(jd_ut=jd_ut),
    )
    monkeypatch.setattr(scan_module, "void_periods_in_range", lambda *_args, **_kwargs: [])
    result = western.scan_western_electional_profile(
        10.0,
        10.25,
        0.0,
        0.0,
        house_system="P",
        profile_id="sahl_moon_condition_v1",
        scan_policy=western.WesternElectionalProfileScanPolicy(
            step_days=0.25,
            max_scan_points=2,
            qualifying_statuses=(
                western.WesternElectionalQualificationStatus.INDETERMINATE,
            ),
        ),
        reader=_Reader(),
    )
    assert [(item.name, item.value) for item in result.profile_parameters] == [
        ("burnt_path_variant", "fall_degrees_19_libra_to_3_scorpio"),
        ("eighth_rule_variant", "arabic_al_rijal_twelfth_part"),
    ]


def test_scan_policy_rejects_duplicate_or_empty_status_sets() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        western.WesternElectionalProfileScanPolicy(qualifying_statuses=())
    with pytest.raises(ValueError, match="duplicates"):
        western.WesternElectionalProfileScanPolicy(
            qualifying_statuses=(
                western.WesternElectionalQualificationStatus.CLEAR,
                western.WesternElectionalQualificationStatus.CLEAR,
            )
        )
