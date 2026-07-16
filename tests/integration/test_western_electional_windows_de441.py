"""DE441 integration evidence for Phase 10 judgement windows."""

from __future__ import annotations

import pytest

from moira import (
    DorotheusMatterProfileId,
    DorotheusSignNatureVariant,
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

    travel = engine.western_electional_judgement_windows(
        2451545.0,
        2451545.25,
        51.5074,
        -0.1278,
        house_system="R",
        matter_profile_id=DorotheusMatterProfileId.TRAVEL,
        perfection_significator_a="Moon",
        perfection_significator_b="Jupiter",
        perfection_interval_days=7.0,
        scan_policy=WesternElectionalJudgementWindowPolicy(step_days=0.25),
    )
    assert travel.initial_sample_count == travel.total_evaluation_count == 2
    assert all(
        item.representative_judgement.selection.matter_profile_id
        == "dorotheus_travel_v1"
        for item in travel.windows
    )

    ship_acquisition = engine.western_electional_judgement_windows(
        2451545.0,
        2451545.25,
        51.5074,
        -0.1278,
        house_system="R",
        matter_profile_id=DorotheusMatterProfileId.SHIP_ACQUISITION,
        perfection_significator_a="Moon",
        perfection_significator_b="Jupiter",
        perfection_interval_days=7.0,
        scan_policy=WesternElectionalJudgementWindowPolicy(step_days=0.25),
    )
    assert ship_acquisition.initial_sample_count == ship_acquisition.total_evaluation_count == 2
    assert all(
        item.representative_judgement.selection.matter_profile_id
        == "dorotheus_ship_acquisition_v1"
        for item in ship_acquisition.windows
    )
    sea_travel = engine.western_electional_judgement_windows(
        2451545.0,
        2451545.25,
        51.5074,
        -0.1278,
        house_system="R",
        matter_profile_id=DorotheusMatterProfileId.SEA_TRAVEL,
        perfection_significator_a="Moon",
        perfection_significator_b="Jupiter",
        perfection_interval_days=7.0,
        dorotheus_sign_nature_variant=(
            DorotheusSignNatureVariant.SOURCE_TEXT_UNRESOLVED
        ),
        scan_policy=WesternElectionalJudgementWindowPolicy(step_days=0.25),
    )
    assert sea_travel.initial_sample_count == sea_travel.total_evaluation_count == 2
    assert all(
        item.representative_judgement.selection.dorotheus_sign_nature_variant
        == "source_text_unresolved_no_dry_sign_table"
        for item in sea_travel.windows
    )
    newly_admitted = (
        DorotheusMatterProfileId.SHIP_CONSTRUCTION,
        DorotheusMatterProfileId.SHIP_LAUNCH,
        DorotheusMatterProfileId.PARTNERSHIP,
        DorotheusMatterProfileId.DEBT_AND_PAYMENT,
        DorotheusMatterProfileId.WRITING_A_WILL,
        SahlMatterProfileId.BUSINESS_PARTNERSHIP,
    )
    scans = tuple(
        engine.western_electional_judgement_windows(
            2451545.0,
            2451545.25,
            51.5074,
            -0.1278,
            house_system="R",
            matter_profile_id=profile_id,
            perfection_significator_a="Moon",
            perfection_significator_b="Venus" if profile_id.value.startswith("sahl_") else "Jupiter",
            perfection_interval_days=7.0,
            scan_policy=WesternElectionalJudgementWindowPolicy(step_days=0.25),
            **(
                {
                    "sahl_burnt_path_variant": SahlBurntPathVariant.SAHL_TEXT_INDETERMINATE,
                    "sahl_eighth_rule_variant": SahlEighthRuleVariant.ARABIC_AL_RIJAL_TWELFTH_PART,
                }
                if profile_id.value.startswith("sahl_")
                else {}
            ),
        )
        for profile_id in newly_admitted
    )
    assert all(
        all(
            item.representative_judgement.selection.matter_profile_id == profile_id.value
            for item in scan.windows
        )
        for profile_id, scan in zip(newly_admitted, scans)
    )
