from pathlib import Path

import pytest

from moira import (
    DorotheusMatterProfileId,
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
    assert Path(str(kernel)).name == "de441.bsp"
    assert sahl.complete_electional_judgement is True
    assert dorotheus.complete_electional_judgement is True
    assert dorotheus_flow.complete_electional_judgement is True
    assert sahl.scoring == dorotheus.scoring == "not_provided"
