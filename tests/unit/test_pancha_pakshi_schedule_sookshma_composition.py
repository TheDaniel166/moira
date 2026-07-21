"""Stage 2N explicit schedule-to-Sookshma composition contracts."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from fractions import Fraction
import hashlib
import inspect
import json
from pathlib import Path

import pytest

import moira
import moira.facade as facade
import moira.pancha_pakshi as pakshi
import moira.vedic as vedic


_SCHEDULE_PROFILE_ID = "agastya_madras_1879_akshara_fixed_clock"
_SELECTOR_PROFILE_ID = "bogamuni_chennai_2024_sookshma_temporal_selector"
_ROOT = Path(__file__).resolve().parents[2]
_DECISION_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_schedule_sookshma_composition_stage2n_2026_07_21.json"
)
_DECISION_SHA256 = (
    "084190606dc358abce7cc1879aa898a0071bce421b1eda8845b113520a7c36a9"
)


def _digest(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()


def _compose(
    *,
    policy=pakshi.PanchaPakshiSookshmaSelectorPolicyId.WEIGHTED_SOOKSHMA,
    samam_index=1,
    subject_bird=pakshi.PanchaPakshiBird.VULTURE,
    elapsed=Fraction(),
):
    return pakshi.pancha_pakshi_schedule_sookshma_temporal_selection(
        _SCHEDULE_PROFILE_ID,
        _SELECTOR_PROFILE_ID,
        profile_paksha=pakshi.PanchaPakshiPaksha.PURVA,
        half=pakshi.PanchaPakshiHalf.DAY,
        weekday=pakshi.PanchaPakshiWeekday.SUNDAY,
        samam_index=samam_index,
        subject_bird=subject_bird,
        selector_policy_id=policy,
        elapsed_nazhigai=elapsed,
    )


def test_stage2n_decision_binds_both_profiles_without_manifest_drift() -> None:
    decision = json.loads(_DECISION_PATH.read_text(encoding="utf-8"))

    assert _digest(_DECISION_PATH) == _DECISION_SHA256
    assert decision["stage"] == "2N"
    assert decision["bound_public_products"]["manifest_sha256"] == (
        "584d2b28bd2c7537f8ebb029633ed7bce682ed02ee38bf32402901940887c955"
    )
    assert decision["bound_public_products"]["manifest_changed"] is False
    assert (
        decision["bound_public_products"]["schedule_profile"]["profile_id"]
        == _SCHEDULE_PROFILE_ID
    )
    assert (
        decision["bound_public_products"]["selector_profile"]["profile_id"]
        == _SELECTOR_PROFILE_ID
    )
    assert decision["ambiguity_policy"]["default_selector_policy"] is None
    assert decision["computational_object"]["clock_or_civil_time_routing"] == (
        "not_performed"
    )
    assert decision["computational_object"]["uromarisi_outcome_binding"] == (
        "not_performed"
    )


def test_composition_derives_the_unique_subject_parent_activity() -> None:
    result = _compose(
        samam_index=1,
        subject_bird=pakshi.PanchaPakshiBird.CROW,
        elapsed=Fraction(2),
    )

    assert result.parent_schedule_cell.samam_index == 1
    assert result.parent_schedule_cell.bird is pakshi.PanchaPakshiBird.CROW
    assert result.parent_schedule_cell.activity is pakshi.PanchaPakshiActivity.RULE
    assert result.sookshma_selection.parent_activity is (
        pakshi.PanchaPakshiActivity.RULE
    )
    assert result.sookshma_selection.intervals[0].activity is (
        pakshi.PanchaPakshiActivity.RULE
    )
    assert result.sookshma_selection.selected_ordinal == 2
    assert result.composition_policy.composition_status == (
        "modern_moira_policy_not_source_claim"
    )
    assert result.composition_policy.clock_or_civil_time_routing_status == (
        "not_performed"
    )
    assert result.composition_policy.uromarisi_outcome_binding_status == (
        "not_performed"
    )


def test_all_schedule_samams_have_one_parent_cell_per_subject_bird() -> None:
    for paksha_value in pakshi.PanchaPakshiPaksha:
        for half in pakshi.PanchaPakshiHalf:
            for weekday in pakshi.PanchaPakshiWeekday:
                schedule = pakshi.pancha_pakshi_schedule(
                    _SCHEDULE_PROFILE_ID,
                    paksha=paksha_value,
                    half=half,
                    weekday=weekday,
                )
                for samam_index in range(1, 6):
                    for subject_bird in pakshi.PanchaPakshiBird:
                        result = (
                            pakshi
                            .pancha_pakshi_schedule_sookshma_temporal_selection(
                                _SCHEDULE_PROFILE_ID,
                                _SELECTOR_PROFILE_ID,
                                profile_paksha=paksha_value,
                                half=half,
                                weekday=weekday,
                                samam_index=samam_index,
                                subject_bird=subject_bird,
                                selector_policy_id=(
                                    pakshi
                                    .PanchaPakshiSookshmaSelectorPolicyId
                                    .WEIGHTED_SOOKSHMA
                                ),
                                elapsed_nazhigai=Fraction(),
                            )
                        )
                        matches = tuple(
                            cell
                            for cell in schedule.cells
                            if cell.samam_index == samam_index
                            and cell.bird is subject_bird
                        )
                        assert len(matches) == 1
                        assert result.parent_schedule_cell == matches[0]
                        assert result.sookshma_selection.parent_activity is (
                            matches[0].activity
                        )


def test_equal_fifths_composes_without_inventing_subactivities() -> None:
    result = _compose(
        policy=(
            pakshi.PanchaPakshiSookshmaSelectorPolicyId
            .EKA_SOOKSHMA_EQUAL_FIFTHS
        ),
        subject_bird=pakshi.PanchaPakshiBird.PEACOCK,
        elapsed=Fraction(24, 5),
    )

    assert result.sookshma_selection.selected_ordinal == 5
    assert all(
        interval.activity is None
        for interval in result.sookshma_selection.intervals
    )


def test_every_composition_choice_is_explicit_and_clock_free() -> None:
    signature = inspect.signature(
        pakshi.pancha_pakshi_schedule_sookshma_temporal_selection
    )
    assert set(signature.parameters) == {
        "schedule_profile_id",
        "selector_profile_id",
        "profile_paksha",
        "half",
        "weekday",
        "samam_index",
        "subject_bird",
        "selector_policy_id",
        "elapsed_nazhigai",
    }
    assert all(
        signature.parameters[name].default is inspect.Parameter.empty
        for name in signature.parameters
    )
    assert "datetime" not in str(signature)
    assert "reader" not in signature.parameters
    assert "location" not in signature.parameters


def test_composition_fails_closed_on_wrong_profiles_and_input_types() -> None:
    with pytest.raises(ValueError, match="does not admit.*nominal_schedule"):
        pakshi.pancha_pakshi_schedule_sookshma_temporal_selection(
            _SELECTOR_PROFILE_ID,
            _SELECTOR_PROFILE_ID,
            profile_paksha=pakshi.PanchaPakshiPaksha.PURVA,
            half=pakshi.PanchaPakshiHalf.DAY,
            weekday=pakshi.PanchaPakshiWeekday.SUNDAY,
            samam_index=1,
            subject_bird=pakshi.PanchaPakshiBird.VULTURE,
            selector_policy_id=(
                pakshi.PanchaPakshiSookshmaSelectorPolicyId.WEIGHTED_SOOKSHMA
            ),
            elapsed_nazhigai=Fraction(),
        )
    with pytest.raises(TypeError, match="there is no default"):
        pakshi.pancha_pakshi_schedule_sookshma_temporal_selection(
            _SCHEDULE_PROFILE_ID,
            _SELECTOR_PROFILE_ID,
            profile_paksha=pakshi.PanchaPakshiPaksha.PURVA,
            half=pakshi.PanchaPakshiHalf.DAY,
            weekday=pakshi.PanchaPakshiWeekday.SUNDAY,
            samam_index=1,
            subject_bird=pakshi.PanchaPakshiBird.VULTURE,
            selector_policy_id="weighted",
            elapsed_nazhigai=Fraction(),
        )
    with pytest.raises(ValueError, match=r"\[1, 5\]"):
        _compose(samam_index=0)
    with pytest.raises(TypeError, match="exact Fraction"):
        _compose(elapsed=0.5)


def test_composition_vessel_is_immutable_and_revalidates_both_profiles() -> None:
    result = _compose()
    with pytest.raises(FrozenInstanceError):
        result.samam_index = 2
    with pytest.raises(ValueError, match="unique subject-bird cell"):
        replace(result, parent_schedule_cell=result.schedule.cells[1])
    with pytest.raises(ValueError, match="elapsed offset"):
        replace(result, elapsed_nazhigai=Fraction(1))


def test_composition_is_exported_consistently_and_facade_delegates() -> None:
    names = (
        "PanchaPakshiScheduleSookshmaCompositionPolicy",
        "PanchaPakshiScheduleSookshmaSelection",
        "pancha_pakshi_schedule_sookshma_temporal_selection",
    )
    for name in names:
        expected = getattr(pakshi, name)
        for surface in (moira, facade, vedic):
            assert name in surface.__all__
            assert getattr(surface, name) is expected

    engine = object.__new__(facade.Moira)
    engine._reader_obj = None
    result = engine.pancha_pakshi_schedule_sookshma_temporal_selection(
        _SCHEDULE_PROFILE_ID,
        _SELECTOR_PROFILE_ID,
        profile_paksha=pakshi.PanchaPakshiPaksha.PURVA,
        half=pakshi.PanchaPakshiHalf.DAY,
        weekday=pakshi.PanchaPakshiWeekday.SUNDAY,
        samam_index=1,
        subject_bird=pakshi.PanchaPakshiBird.VULTURE,
        selector_policy_id=(
            pakshi.PanchaPakshiSookshmaSelectorPolicyId.WEIGHTED_SOOKSHMA
        ),
        elapsed_nazhigai=Fraction(),
    )
    assert result.parent_schedule_cell.activity is pakshi.PanchaPakshiActivity.EAT
