"""DE441 integration evidence for Phase 9 explicit-candidate ranking."""

from __future__ import annotations

import pytest

from moira import (
    Moira,
    SahlBurntPathVariant,
    SahlEighthRuleVariant,
    SahlMatterProfileId,
    WesternElectionalRankingContributionId,
    WesternElectionalRankingWeight,
)
from moira._kernel_paths import find_planetary_kernel


@pytest.mark.requires_ephemeris
def test_phase9_evaluates_every_candidate_through_one_de441_facade() -> None:
    kernel = find_planetary_kernel()
    assert kernel is not None and kernel.name == "de441.bsp"
    engine = Moira(str(kernel))
    result = engine.western_electional_ranking_at(
        (2451545.0, 2451546.0),
        51.5074,
        -0.1278,
        house_system="R",
        matter_profile_id=SahlMatterProfileId.SALE,
        perfection_significator_a="Moon",
        perfection_significator_b="Venus",
        perfection_interval_days=7.0,
        weights=(
            WesternElectionalRankingWeight(
                WesternElectionalRankingContributionId.DIRECT_PERFECTION_PRESENT,
                2.0,
            ),
            WesternElectionalRankingWeight(
                WesternElectionalRankingContributionId.TRANSLATION_OF_LIGHT_PRESENT,
                1.0,
            ),
        ),
        sahl_burnt_path_variant=SahlBurntPathVariant.SAHL_TEXT_INDETERMINATE,
        sahl_eighth_rule_variant=(
            SahlEighthRuleVariant.ARABIC_AL_RIJAL_TWELFTH_PART
        ),
    )

    candidates = (*result.ranked_candidates, *result.excluded_candidates)
    assert len(candidates) == 2
    assert {item.input_index for item in candidates} == {0, 1}
    assert all(item.judgement.complete_electional_judgement for item in candidates)
    assert all(item.judgement.selection == candidates[0].judgement.selection for item in candidates)
    assert all(item.judgement.reader_provenance == result.reader_provenance for item in candidates)
    assert result.policy.eligibility_policy == "complete_under_profile_only"
    assert result.ranking_is_decision_support is True
    assert result.advice_language == result.recommendation_language == "not_admitted"
