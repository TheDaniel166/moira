from pathlib import Path

import pytest

from moira import (
    DorotheusMatterProfileId,
    DorotheusSignNatureVariant,
    Moira,
    MoonConnectionFlowPolicy,
    MoonPreviousEventWindowPolicy,
    SahlBurntPathVariant,
    SahlEighthRuleVariant,
    SahlMatterProfileId,
    WesternElectionalComponentState,
    WesternElectionalJudgementState,
)
from moira._kernel_paths import find_planetary_kernel


@pytest.mark.requires_ephemeris
def test_j2000_phase8_composes_sahl_and_dorotheus_through_one_de441_facade() -> None:
    kernel = find_planetary_kernel()
    assert kernel is not None and kernel.name == "de441.bsp"
    engine = Moira(str(kernel))

    sahl = engine.western_electional_judgement_at(
        2451545.0,
        51.5074,
        -0.1278,
        house_system="R",
        matter_profile_id=SahlMatterProfileId.SALE,
        perfection_significator_a="Moon",
        perfection_significator_b="Venus",
        perfection_interval_days=7.0,
        sahl_burnt_path_variant=(
            SahlBurntPathVariant.SAHL_TEXT_INDETERMINATE
        ),
        sahl_eighth_rule_variant=(
            SahlEighthRuleVariant.ARABIC_AL_RIJAL_TWELFTH_PART
        ),
    )
    dorotheus = engine.western_electional_judgement_at(
        2451545.0,
        51.5074,
        -0.1278,
        house_system="R",
        matter_profile_id=DorotheusMatterProfileId.LAND_PURCHASE,
        perfection_significator_a="Moon",
        perfection_significator_b="Saturn",
        perfection_interval_days=7.0,
    )
    dorotheus_flow = engine.western_electional_judgement_at(
        2451545.0,
        51.5074,
        -0.1278,
        house_system="R",
        matter_profile_id=DorotheusMatterProfileId.BUYING_AND_SELLING,
        perfection_significator_a="Moon",
        perfection_significator_b="Mercury",
        perfection_interval_days=7.0,
        moon_flow_policy=MoonConnectionFlowPolicy(
            MoonPreviousEventWindowPolicy.CURRENT_SIGN,
            modern=False,
        ),
    )
    travel = engine.western_electional_judgement_at(
        2451545.0,
        51.5074,
        -0.1278,
        house_system="R",
        matter_profile_id=DorotheusMatterProfileId.TRAVEL,
        perfection_significator_a="Moon",
        perfection_significator_b="Jupiter",
        perfection_interval_days=7.0,
    )
    ship_acquisition = engine.western_electional_judgement_at(
        2451545.0,
        51.5074,
        -0.1278,
        house_system="R",
        matter_profile_id=DorotheusMatterProfileId.SHIP_ACQUISITION,
        perfection_significator_a="Moon",
        perfection_significator_b="Jupiter",
        perfection_interval_days=7.0,
    )

    assert sahl.profile_id == dorotheus.profile_id == "western_electional_judgement_v1"
    assert sahl.state in {
        WesternElectionalJudgementState.IMPEDED,
        WesternElectionalJudgementState.INDETERMINATE,
    }
    assert dorotheus.state in {
        WesternElectionalJudgementState.IMPEDED,
        WesternElectionalJudgementState.INDETERMINATE,
    }
    assert sahl.rooted_context is None
    assert sahl.components[1].state is WesternElectionalComponentState.NOT_APPLICABLE
    assert dorotheus.rooted_context is dorotheus.matter_profile.rooted_context
    assert dorotheus.components[1].profile_id == "dorotheus_rooted_context_v1"
    assert sahl.perfection_path.is_day_chart is dorotheus.perfection_path.is_day_chart
    assert sahl.reader_provenance == sahl.perfection_path.reader_provenance
    assert dorotheus.reader_provenance == dorotheus.perfection_path.reader_provenance
    assert dorotheus_flow.reader_provenance == (
        dorotheus_flow.perfection_path.reader_provenance
    )
    assert dorotheus_flow.matter_profile.moon_connection_flow is not None
    assert dorotheus_flow.selection.moon_flow_previous_window == "current_sign"
    assert dorotheus_flow.selection.moon_flow_previous_lookback_days is None
    assert dorotheus_flow.selection.moon_flow_modern is False
    assert travel.rooted_context is None
    assert travel.matter_profile.rooted_context is None
    assert travel.components[1].state is WesternElectionalComponentState.NOT_APPLICABLE
    assert any(
        item.requirement_id == "dorotheus_v31_rooted_context"
        for item in travel.excluded_requirements
    )
    assert ship_acquisition.rooted_context is None
    assert ship_acquisition.matter_profile.rooted_context is None
    assert ship_acquisition.components[1].state is WesternElectionalComponentState.NOT_APPLICABLE
    assert any(
        item.requirement_id == "dorotheus_v31_rooted_context"
        for item in ship_acquisition.excluded_requirements
    )
    land_travel = engine.western_electional_judgement_at(
        2451545.0,
        51.5074,
        -0.1278,
        house_system="R",
        matter_profile_id=DorotheusMatterProfileId.LAND_TRAVEL,
        perfection_significator_a="Moon",
        perfection_significator_b="Jupiter",
        perfection_interval_days=7.0,
        dorotheus_sign_nature_variant=(
            DorotheusSignNatureVariant.LILLY_1647_ELEMENTAL_QUALITIES
        ),
    )
    sea_travel = engine.western_electional_judgement_at(
        2451545.0,
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
    )
    assert land_travel.selection.dorotheus_sign_nature_variant == (
        "lilly_1647_elemental_qualities"
    )
    assert sea_travel.selection.dorotheus_sign_nature_variant == (
        "source_text_unresolved_no_dry_sign_table"
    )
    assert land_travel.rooted_context is sea_travel.rooted_context is None
    newly_admitted = (
        DorotheusMatterProfileId.SHIP_CONSTRUCTION,
        DorotheusMatterProfileId.SHIP_LAUNCH,
        DorotheusMatterProfileId.PARTNERSHIP,
        DorotheusMatterProfileId.DEBT_AND_PAYMENT,
        DorotheusMatterProfileId.WRITING_A_WILL,
        SahlMatterProfileId.BUSINESS_PARTNERSHIP,
    )
    composed = tuple(
        engine.western_electional_judgement_at(
            2451545.0,
            51.5074,
            -0.1278,
            house_system="R",
            matter_profile_id=profile_id,
            perfection_significator_a="Moon",
            perfection_significator_b="Venus" if profile_id.value.startswith("sahl_") else "Jupiter",
            perfection_interval_days=7.0,
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
    assert tuple(item.selection.matter_profile_id for item in composed) == tuple(
        item.value for item in newly_admitted
    )
    assert all(item.complete_electional_judgement for item in composed)
    assert all(item.matter_profile.complete_matter_profile for item in composed)
    assert Path(str(kernel)).name == "de441.bsp"
    assert sahl.complete_electional_judgement is True
    assert dorotheus.complete_electional_judgement is True
    assert dorotheus_flow.complete_electional_judgement is True
    assert travel.complete_electional_judgement is True
    assert sahl.scoring == dorotheus.scoring == travel.scoring == "not_provided"
