"""Phase 9 ranking-law tests independent of ephemeris resources."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

import moira
import moira.facade as facade
import moira.western_electional as western

from moira._western_electional_judgement import (
    WesternElectionalJudgementDoctrine,
    WesternElectionalJudgementSelection,
    assemble_western_electional_judgement,
)
from moira._western_electional_ranking import (
    ElectionalRankingPolicy,
    WesternElectionalRankingCandidateState,
    WesternElectionalRankingContributionId,
    WesternElectionalRankingWeight,
    assemble_western_electional_ranking,
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
    perfection: LillyPerfectionKind | None,
    moon_status: str = "clear_of_profile_impediments",
):
    moon = SimpleNamespace(
        profile_id="sahl_moon_condition_v1",
        status=_enum(moon_status),
        rules=(),
    )
    matter = SimpleNamespace(
        jd_ut=jd_ut,
        profile_id=_enum("sahl_sale_v1"),
        status=_enum("clear_of_explicit_profile_gates"),
        moon_condition=moon,
        clauses=(),
        authorities=("Sahl synthetic fixture",),
        reader_provenance="synthetic-reader",
    )
    perfection_path = SimpleNamespace(
        jd_start=jd_ut,
        jd_end=jd_ut + 7.0,
        profile_id="lilly_1647_perfection_v1",
        present_kinds=(() if perfection is None else (perfection,)),
        indeterminate_kinds=(),
        witnesses=(),
        authorities=("Lilly synthetic fixture",),
        reader_provenance="synthetic-reader",
    )
    return assemble_western_electional_judgement(
        latitude=51.5,
        longitude=-0.1,
        requested_house_system="R",
        selection=_selection(),
        matter_profile=matter,
        perfection_path=perfection_path,
    )


def _weights():
    return (
        WesternElectionalRankingWeight(
            WesternElectionalRankingContributionId.DIRECT_PERFECTION_PRESENT,
            2.0,
        ),
        WesternElectionalRankingWeight(
            WesternElectionalRankingContributionId.TRANSLATION_OF_LIGHT_PRESENT,
            1.0,
        ),
    )


def test_ranking_is_caller_weighted_visible_and_deterministic() -> None:
    result = assemble_western_electional_ranking(
        (
            _judgement(2451546.0, perfection=LillyPerfectionKind.TRANSLATION),
            _judgement(2451547.0, perfection=LillyPerfectionKind.DIRECT),
            _judgement(
                2451548.0,
                perfection=LillyPerfectionKind.DIRECT,
                moon_status="one_or_more_impediments",
            ),
        ),
        _weights(),
    )

    assert [item.input_index for item in result.ranked_candidates] == [1, 0]
    assert [item.rank for item in result.ranked_candidates] == [1, 2]
    assert result.ranked_candidates[0].score == pytest.approx(2.0 / 3.0)
    assert result.ranked_candidates[1].score == pytest.approx(1.0 / 3.0)
    assert result.ranked_candidates[0].normalization_divisor == 3.0
    assert [item.weighted_value for item in result.ranked_candidates[0].contributions] == [
        2.0,
        0.0,
    ]
    assert result.excluded_candidates[0].state is (
        WesternElectionalRankingCandidateState.EXCLUDED_IMPEDED
    )
    assert result.excluded_candidates[0].judgement.jd_ut == 2451548.0
    assert result.advice_language == result.recommendation_language == "not_admitted"


def test_indeterminate_candidate_is_partitioned_not_scored_as_zero() -> None:
    result = assemble_western_electional_ranking(
        (
            _judgement(2451545.0, perfection=None),
            _judgement(2451546.0, perfection=LillyPerfectionKind.DIRECT),
        ),
        _weights(),
    )
    assert len(result.ranked_candidates) == 1
    assert len(result.excluded_candidates) == 1
    excluded = result.excluded_candidates[0]
    assert excluded.state is WesternElectionalRankingCandidateState.EXCLUDED_INDETERMINATE
    assert "cannot be converted to numeric zero" in excluded.reason


def test_ties_use_jd_then_input_index_without_hidden_preference() -> None:
    result = assemble_western_electional_ranking(
        (
            _judgement(2451547.0, perfection=LillyPerfectionKind.DIRECT),
            _judgement(2451546.0, perfection=LillyPerfectionKind.DIRECT),
        ),
        _weights(),
    )
    assert [item.input_index for item in result.ranked_candidates] == [1, 0]
    assert [item.jd_ut for item in result.ranked_candidates] == [2451546.0, 2451547.0]


def test_weights_and_candidate_contract_reject_ambiguity() -> None:
    with pytest.raises(ValueError, match="nonzero"):
        WesternElectionalRankingWeight(
            WesternElectionalRankingContributionId.DIRECT_PERFECTION_PRESENT,
            0.0,
        )
    duplicate = _weights()[:1] * 2
    with pytest.raises(ValueError, match="unique"):
        assemble_western_electional_ranking(
            (
                _judgement(2451545.0, perfection=LillyPerfectionKind.DIRECT),
                _judgement(2451546.0, perfection=LillyPerfectionKind.DIRECT),
            ),
            duplicate,
        )
    different_selection = replace(
        _judgement(2451546.0, perfection=LillyPerfectionKind.DIRECT),
        selection=replace(_selection(), perfection_interval_days=8.0),
    )
    with pytest.raises(ValueError, match="must share coordinates"):
        assemble_western_electional_ranking(
            (
                _judgement(2451545.0, perfection=LillyPerfectionKind.DIRECT),
                different_selection,
            ),
            _weights(),
        )


def test_policy_has_no_named_weights_or_advice_escape_hatch() -> None:
    with pytest.raises(ValueError, match="fixed"):
        ElectionalRankingPolicy(advice_language="generated")


def test_phase9_surface_is_public_at_every_library_layer() -> None:
    names = {
        "WesternElectionalRankingContributionId",
        "WesternElectionalRankingCandidateState",
        "ElectionalRankingPolicy",
        "WesternElectionalRankingWeight",
        "WesternElectionalRankingContribution",
        "WesternElectionalRankedCandidate",
        "WesternElectionalExcludedCandidate",
        "WesternElectionalRankingEvaluation",
        "WESTERN_ELECTIONAL_RANKING_V1",
        "assemble_western_electional_ranking",
        "western_electional_ranking_at",
    }
    for name in names:
        assert hasattr(western, name)
        assert hasattr(facade, name)
        assert hasattr(moira, name)
    assert hasattr(moira.Moira, "western_electional_ranking_at")
