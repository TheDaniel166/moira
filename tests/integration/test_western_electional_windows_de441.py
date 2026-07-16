"""DE441 integration evidence for Phase 10 judgement windows."""

from __future__ import annotations

import pytest

from moira import (
    Moira,
    SahlBurntPathVariant,
    SahlEighthRuleVariant,
    SahlMatterProfileId,
    WesternElectionalJudgementWindowPolicy,
    WesternElectionalWindowScanMode,
)
from moira._kernel_paths import find_planetary_kernel


@pytest.mark.requires_ephemeris
def test_phase10_scans_complete_judgements_through_one_de441_facade() -> None:
    kernel = find_planetary_kernel()
    assert kernel is not None and kernel.name == "de441.bsp"
    engine = Moira(str(kernel))
    result = engine.western_electional_judgement_windows(
        2451545.0,
        2451545.25,
        51.5074,
        -0.1278,
        house_system="R",
        matter_profile_id=SahlMatterProfileId.SALE,
        perfection_significator_a="Moon",
        perfection_significator_b="Venus",
        perfection_interval_days=7.0,
        sahl_burnt_path_variant=SahlBurntPathVariant.SAHL_TEXT_INDETERMINATE,
        sahl_eighth_rule_variant=(
            SahlEighthRuleVariant.ARABIC_AL_RIJAL_TWELFTH_PART
        ),
        scan_policy=WesternElectionalJudgementWindowPolicy(step_days=0.25),
    )

    assert result.initial_sample_count == result.total_evaluation_count == 2
    assert result.windows
    assert all(
        item.exactness is WesternElectionalWindowScanMode.SAMPLED
        for item in result.windows
    )
    assert all(
        item.representative_judgement.complete_electional_judgement
        for item in result.windows
    )
    assert all(
        item.representative_judgement.reader_provenance == result.reader_provenance
        for item in result.windows
    )
    assert result.boundary_inventory_complete is False
    assert result.exact_boundary_claimed is False
    assert result.continuous_truth_claimed is False
    assert result.candidate_events == ()
    assert result.event_seed_count == 0
    assert result.ranking_integration == "separate_phase9_endpoint_not_applied"
