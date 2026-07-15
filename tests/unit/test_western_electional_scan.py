"""Doctrine and invariant tests for named Western profile scanning."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import moira.western_electional as western


class _Reader:
    path = "synthetic-scan-reader.bsp"


def _evaluation(status: str, profile_id: str):
    return SimpleNamespace(
        status=SimpleNamespace(value=status),
        profile_id=profile_id,
        profile_version="1.0.0",
    )


def test_scan_qualifies_exact_statuses_and_merges_only_sampled_truth(monkeypatch) -> None:
    statuses = {
        0: "clear_of_profile_impediments",
        1: "clear_of_profile_impediments",
        2: "one_or_more_profile_impediments",
        3: "clear_of_profile_impediments",
    }

    def fake_ramesey(jd_ut, *_args, **_kwargs):
        index = round((jd_ut - 100.0) / 0.25)
        return _evaluation(statuses[index], "ramesey_moon_condition_v1")

    monkeypatch.setattr(western, "ramesey_moon_condition_at", fake_ramesey)
    policy = western.WesternElectionalProfileScanPolicy(
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


def test_scan_can_select_triggered_and_indeterminate_without_scoring(monkeypatch) -> None:
    sequence = iter(
        ("one_or_more_profile_impediments", "indeterminate", "clear_of_profile_impediments")
    )

    def fake_dorotheus(*_args, **_kwargs):
        return _evaluation(next(sequence), "dorotheus_moon_condition_v1")

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

    monkeypatch.setattr(
        western,
        "ramesey_moon_condition_at",
        lambda *_args, **_kwargs: _evaluation(
            "clear_of_profile_impediments", "ramesey_moon_condition_v1"
        ),
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
            reader=_Reader(),
        )


def test_sahl_scan_preserves_resolved_variant_parameters(monkeypatch) -> None:
    def fake_sahl(*_args, **_kwargs):
        result = _evaluation("indeterminate", "sahl_moon_condition_v1")
        result.burnt_path_variant = SimpleNamespace(
            value="fall_degrees_19_libra_to_3_scorpio"
        )
        result.eighth_rule_variant = SimpleNamespace(
            value="arabic_al_rijal_twelfth_part"
        )
        return result

    monkeypatch.setattr(western, "sahl_moon_condition_at", fake_sahl)
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
