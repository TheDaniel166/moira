"""Stage 2O explicit civil-time routing into Stage 2N."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
from fractions import Fraction
import hashlib
import inspect
import json
from pathlib import Path

import pytest

import moira
import moira._ephemeris_time as ephemeris_time
import moira._local_solar_day as local_solar_day
import moira.facade as facade
import moira.pancha_pakshi as pakshi
import moira.vedic as vedic
from moira._local_solar_day import LocalSolarDay


_SCHEDULE = "agastya_madras_1879_akshara_fixed_clock"
_SELECTOR = "bogamuni_chennai_2024_sookshma_temporal_selector"
_SUNRISE = 2_460_000.0
_TT_OFFSET = 100.0 / 86_400.0
_READER = object()
_DECISION = (
    Path(__file__).parents[1]
    / "fixtures"
    / "pancha_pakshi_civil_time_sookshma_selection_stage2o_2026_07_21.json"
)


def _bind_clock_and_day(
    monkeypatch: pytest.MonkeyPatch,
    *,
    requested_jd_ut1: float,
    solar_half_hours: float,
) -> None:
    solar_day = LocalSolarDay(
        jd=requested_jd_ut1,
        latitude=13.0827,
        longitude=80.2707,
        sunrise_jd=_SUNRISE,
        sunset_jd=_SUNRISE + solar_half_hours / 24.0,
        next_sunrise_jd=_SUNRISE + 1.0,
        weekday=0,
    )
    monkeypatch.setattr(
        ephemeris_time,
        "_ut1_to_ephemeris_tt",
        lambda jd, reader: jd + _TT_OFFSET,
    )
    monkeypatch.setattr(
        ephemeris_time,
        "_ephemeris_tt_to_ut1",
        lambda jd, reader: jd - _TT_OFFSET,
    )
    monkeypatch.setattr(
        local_solar_day,
        "_local_solar_day_from_ut1",
        lambda *args, **kwargs: solar_day,
    )


def _select(
    timing_policy_id: pakshi.PanchaPakshiSookshmaTimingPolicyId,
):
    return pakshi.pancha_pakshi_civil_time_sookshma_selection_at(
        _SCHEDULE,
        _SELECTOR,
        _SUNRISE,
        13.0827,
        80.2707,
        profile_paksha=pakshi.PanchaPakshiPaksha.PURVA,
        subject_bird=pakshi.PanchaPakshiBird.CROW,
        timing_policy_id=timing_policy_id,
        selector_policy_id=(
            pakshi.PanchaPakshiSookshmaSelectorPolicyId.WEIGHTED_SOOKSHMA
        ),
        reader=_READER,  # type: ignore[arg-type]
    )


def test_stage2o_policy_and_result_are_explicit_and_immutable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _bind_clock_and_day(
        monkeypatch,
        requested_jd_ut1=_SUNRISE,
        solar_half_hours=12.0,
    )
    result = _select(pakshi.PanchaPakshiSookshmaTimingPolicyId.FIXED_CLOCK)

    assert tuple(item.name for item in fields(result.routing_policy)) == (
        "policy_id",
        "composition_status",
        "timing_policy_selection",
        "selector_policy_selection",
        "selection_time_scale",
        "samam_derivation",
        "elapsed_derivation",
        "interval_ownership",
        "fixed_tail_policy",
        "automatic_timing_fallback",
        "astronomical_paksha_inference_status",
        "uromarisi_outcome_binding_status",
        "outcome_interpretation_status",
    )
    assert result.routing_policy.timing_policy_selection == (
        "caller_named_no_default"
    )
    assert result.routing_policy.automatic_timing_fallback == "forbidden"
    assert result.subject_bird is pakshi.PanchaPakshiBird.CROW
    assert result.samam_index == 1
    assert result.elapsed_nazhigai == Fraction()
    assert result.composition is not None
    assert result.composition.subject_bird is pakshi.PanchaPakshiBird.CROW
    assert result.composition.sookshma_selection.selected_ordinal == 1

    with pytest.raises(FrozenInstanceError):
        result.samam_index = 2  # type: ignore[misc]


@pytest.mark.parametrize(
    "timing_policy_id",
    tuple(pakshi.PanchaPakshiSookshmaTimingPolicyId),
)
def test_both_timing_policies_route_the_same_twelve_hour_anchor(
    monkeypatch: pytest.MonkeyPatch,
    timing_policy_id: pakshi.PanchaPakshiSookshmaTimingPolicyId,
) -> None:
    _bind_clock_and_day(
        monkeypatch,
        requested_jd_ut1=_SUNRISE,
        solar_half_hours=12.0,
    )
    result = _select(timing_policy_id)
    assert result.timing_policy_id is timing_policy_id
    assert result.current_cell_selection.materialization.policy.policy_id == (
        timing_policy_id.value
    )
    assert result.samam_index == 1
    assert result.elapsed_nazhigai == Fraction()


def test_exact_samam_boundary_belongs_to_following_samam(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _bind_clock_and_day(
        monkeypatch,
        requested_jd_ut1=_SUNRISE,
        solar_half_hours=12.0,
    )
    anchor = _select(pakshi.PanchaPakshiSookshmaTimingPolicyId.FIXED_CLOCK)
    boundary_ut1 = anchor.current_cell_selection.materialization.cells[5].start_jd_ut1
    _bind_clock_and_day(
        monkeypatch,
        requested_jd_ut1=boundary_ut1,
        solar_half_hours=12.0,
    )
    result = pakshi.pancha_pakshi_civil_time_sookshma_selection_at(
        _SCHEDULE,
        _SELECTOR,
        boundary_ut1,
        13.0827,
        80.2707,
        profile_paksha=pakshi.PanchaPakshiPaksha.PURVA,
        subject_bird=pakshi.PanchaPakshiBird.CROW,
        timing_policy_id=pakshi.PanchaPakshiSookshmaTimingPolicyId.FIXED_CLOCK,
        selector_policy_id=(
            pakshi.PanchaPakshiSookshmaSelectorPolicyId.EKA_SOOKSHMA_EQUAL_FIFTHS
        ),
        reader=_READER,  # type: ignore[arg-type]
    )
    assert result.samam_index == 2
    assert result.elapsed_nazhigai == Fraction()
    assert result.composition is not None
    assert result.composition.sookshma_selection.selected_ordinal == 1


def test_fixed_long_half_tail_stays_explicit_without_fallback_or_composition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    requested = _SUNRISE + 13.0 / 24.0
    _bind_clock_and_day(
        monkeypatch,
        requested_jd_ut1=requested,
        solar_half_hours=14.0,
    )
    fixed = pakshi.pancha_pakshi_civil_time_sookshma_selection_at(
        _SCHEDULE,
        _SELECTOR,
        requested,
        13.0827,
        80.2707,
        profile_paksha=pakshi.PanchaPakshiPaksha.PURVA,
        subject_bird=pakshi.PanchaPakshiBird.VULTURE,
        timing_policy_id=pakshi.PanchaPakshiSookshmaTimingPolicyId.FIXED_CLOCK,
        selector_policy_id=(
            pakshi.PanchaPakshiSookshmaSelectorPolicyId.WEIGHTED_SOOKSHMA
        ),
        reader=_READER,  # type: ignore[arg-type]
    )
    assert fixed.selection_status is (
        pakshi.PanchaPakshiCurrentCellSelectionStatus
        .UNMATERIALIZED_SOLAR_HALF_TAIL
    )
    assert fixed.subject_bird is pakshi.PanchaPakshiBird.VULTURE
    assert fixed.samam_index is None
    assert fixed.elapsed_nazhigai is None
    assert fixed.composition is None

    proportional = pakshi.pancha_pakshi_civil_time_sookshma_selection_at(
        _SCHEDULE,
        _SELECTOR,
        requested,
        13.0827,
        80.2707,
        profile_paksha=pakshi.PanchaPakshiPaksha.PURVA,
        subject_bird=pakshi.PanchaPakshiBird.VULTURE,
        timing_policy_id=(
            pakshi.PanchaPakshiSookshmaTimingPolicyId.SOLAR_PROPORTIONAL
        ),
        selector_policy_id=(
            pakshi.PanchaPakshiSookshmaSelectorPolicyId.WEIGHTED_SOOKSHMA
        ),
        reader=_READER,  # type: ignore[arg-type]
    )
    assert proportional.selection_status is (
        pakshi.PanchaPakshiCurrentCellSelectionStatus.SELECTED
    )
    assert proportional.composition is not None


def test_public_signature_exports_and_facade_keep_both_policies_required() -> None:
    signature = inspect.signature(
        pakshi.pancha_pakshi_civil_time_sookshma_selection_at
    )
    assert signature.parameters["timing_policy_id"].default is inspect.Parameter.empty
    assert signature.parameters["selector_policy_id"].default is inspect.Parameter.empty
    for surface in (moira, facade, vedic):
        assert surface.PanchaPakshiCivilTimeSookshmaSelection is (
            pakshi.PanchaPakshiCivilTimeSookshmaSelection
        )
        assert surface.PanchaPakshiSookshmaTimingPolicyId is (
            pakshi.PanchaPakshiSookshmaTimingPolicyId
        )
        assert surface.pancha_pakshi_civil_time_sookshma_selection_at is (
            pakshi.pancha_pakshi_civil_time_sookshma_selection_at
        )
    facade_signature = inspect.signature(
        facade.Moira.pancha_pakshi_civil_time_sookshma_selection
    )
    assert facade_signature.parameters["timing_policy_id"].default is (
        inspect.Parameter.empty
    )
    assert facade_signature.parameters["selector_policy_id"].default is (
        inspect.Parameter.empty
    )


def test_stage2o_decision_binds_unchanged_profiles_and_explicit_policies() -> None:
    raw = _DECISION.read_bytes()
    decision = json.loads(raw)
    canonical = raw.decode("utf-8").replace("\r\n", "\n").replace("\r", "\n")
    assert hashlib.sha256(canonical.encode("utf-8")).hexdigest() == (
        "2ea686e774ba4468c0515f621771b8a142c79f04d89b69839f482e05c37b40df"
    )
    assert decision["stage"] == "2O"
    assert decision["prior_implementation_boundary"]["fixture_sha256"] == (
        "084190606dc358abce7cc1879aa898a0071bce421b1eda8845b113520a7c36a9"
    )
    bound = decision["bound_public_products"]
    assert bound["manifest_sha256"] == (
        "584d2b28bd2c7537f8ebb029633ed7bce682ed02ee38bf32402901940887c955"
    )
    assert bound["manifest_changed"] is False
    assert bound["profile_count_changed"] is False
    assert bound["profile_capabilities_changed"] is False
    assert decision["ambiguity_policy"]["default_timing_policy"] is None
    assert decision["ambiguity_policy"]["default_selector_policy"] is None
    assert decision["computational_object"]["automatic_timing_fallback"] == (
        "forbidden"
    )
