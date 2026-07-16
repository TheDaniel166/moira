"""Phase 8 composition-law tests independent of ephemeris resources."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import moira
import moira.facade as facade
import moira.western_electional as western
from moira.classical_perfection import (
    ClassicalPerfectionState,
    LillyPerfectionKind,
)


def _enum(value: str):
    return SimpleNamespace(value=value)


def _moon(status: str = "clear_of_profile_impediments", rules=()):
    return SimpleNamespace(
        profile_id="sahl_moon_condition_v1",
        status=_enum(status),
        rules=tuple(rules),
    )


def _matter(
    *,
    status: str = "clear_of_explicit_profile_gates",
    moon=None,
    clauses=(),
):
    moon = _moon() if moon is None else moon
    return SimpleNamespace(
        jd_ut=2451545.0,
        profile_id=_enum("sahl_sale_v1"),
        status=_enum(status),
        moon_condition=moon,
        clauses=tuple(clauses),
        authorities=("Sahl source fixture",),
        reader_provenance="synthetic-reader",
    )


def _perfection(*, present=(), indeterminate=()):
    witnesses = tuple(
        SimpleNamespace(
            kind=kind,
            state=ClassicalPerfectionState.INDETERMINATE,
            explanation=f"{kind.value} remains indeterminate",
            source_reference="Lilly source fixture",
        )
        for kind in indeterminate
    )
    return SimpleNamespace(
        jd_start=2451545.0,
        jd_end=2451552.0,
        profile_id="lilly_1647_perfection_v1",
        present_kinds=tuple(present),
        indeterminate_kinds=tuple(indeterminate),
        witnesses=witnesses,
        authorities=("Lilly source fixture",),
        reader_provenance="synthetic-reader",
    )


def _selection():
    return western.WesternElectionalJudgementSelection(
        doctrine=western.WesternElectionalJudgementDoctrine.SAHL,
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


def _assemble(matter, perfection):
    return western.assemble_western_electional_judgement(
        latitude=51.5,
        longitude=-0.1,
        requested_house_system="R",
        selection=_selection(),
        matter_profile=matter,
        perfection_path=perfection,
    )


def test_phase8_surface_is_public_at_every_library_layer() -> None:
    names = {
        "WesternElectionalJudgementDoctrine",
        "WesternElectionalJudgementState",
        "WesternElectionalComponentState",
        "WesternElectionalRequirementState",
        "WesternElectionalJudgementPolicy",
        "WesternElectionalJudgementSelection",
        "WesternElectionalComponentSummary",
        "WesternElectionalRequirementWitness",
        "WesternElectionalJudgementEvaluation",
        "WESTERN_ELECTIONAL_JUDGEMENT_V1",
        "assemble_western_electional_judgement",
        "western_electional_judgement_at",
    }
    for name in names:
        assert hasattr(western, name)
        assert hasattr(facade, name)
        assert hasattr(moira, name)
    assert hasattr(moira.Moira, "western_electional_judgement_at")


def test_complete_requires_clear_components_and_constructive_perfection() -> None:
    result = _assemble(
        _matter(),
        _perfection(present=(LillyPerfectionKind.DIRECT,)),
    )
    assert result.state is western.WesternElectionalJudgementState.COMPLETE
    assert result.complete_electional_judgement is True
    assert result.rooted_context is None
    assert result.components[1].state is western.WesternElectionalComponentState.NOT_APPLICABLE
    assert not result.unresolved_requirements
    assert {item.requirement_id for item in result.excluded_requirements} >= {
        "dorothean_rooted_context",
        "scoring",
        "advice_or_recommendation",
    }


def test_explicit_impediment_precedes_unresolved_evidence() -> None:
    unresolved_rule = SimpleNamespace(
        rule_id="source_open_rule",
        state=_enum("not_evaluable"),
        source_reference="Sahl open source fixture",
    )
    result = _assemble(
        _matter(
            status="one_or_more_explicit_profile_gates",
            moon=_moon(status="indeterminate", rules=(unresolved_rule,)),
        ),
        _perfection(indeterminate=(LillyPerfectionKind.DIRECT,)),
    )
    assert result.state is western.WesternElectionalJudgementState.IMPEDED
    assert {item.requirement_id for item in result.unresolved_requirements} == {
        "moon_condition:source_open_rule",
        "perfection_path:direct_perfection",
        "perfection_path:no_constructive_perfection",
    }


def test_absent_constructive_perfection_propagates_indeterminacy() -> None:
    result = _assemble(_matter(), _perfection())
    assert result.state is western.WesternElectionalJudgementState.INDETERMINATE
    assert result.components[3].state is western.WesternElectionalComponentState.INDETERMINATE
    assert result.unresolved_requirements[-1].requirement_id == (
        "perfection_path:no_constructive_perfection"
    )


def test_policy_and_selection_reject_hidden_substitution() -> None:
    with pytest.raises(ValueError, match="fixed"):
        western.WesternElectionalJudgementPolicy(scoring="weighted")
    with pytest.raises(ValueError, match="match the selected doctrine"):
        western.WesternElectionalJudgementSelection(
            doctrine=western.WesternElectionalJudgementDoctrine.SAHL,
            matter_profile_id="dorotheus_leasing_v1",
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
            sahl_burnt_path_variant="variant",
            sahl_eighth_rule_variant="variant",
        )


def test_reader_provenance_cannot_diverge_between_components() -> None:
    perfection = _perfection(present=(LillyPerfectionKind.DIRECT,))
    perfection.reader_provenance = "other-reader"
    with pytest.raises(ValueError, match="share one reader provenance"):
        _assemble(_matter(), perfection)
