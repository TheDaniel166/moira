"""Stage 2U DIE semantic atoms, blocked precursor, and non-admission guards."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import moira
import moira.facade as facade
import moira.pancha_pakshi as pakshi
import moira.vedic as vedic
from moira_server.routers import pancha_pakshi as router_module


_ROOT = Path(__file__).resolve().parents[2]
_DECISION_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_uromarisi_die_semantics_stage2u_research_2026_07_21.json"
)
_STAGE2T_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_uromarisi_sleep_semantics_stage2t_research_2026_07_21.json"
)
_STAGE2P_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_uromarisi_illness_grid_stage2p_research_2026_07_21.json"
)
_MANIFEST_PATH = _ROOT / "moira" / "data" / "pancha_pakshi_manifest.json"
_DECISION_SHA256 = (
    "4954c13c33aa755bc0e8c6f47b7825d6ddb8346a2b6df39edf804872e81cbf70"
)
_STAGE2T_SHA256 = (
    "09f7651325cdac058d9816b85b031ef528f514ae91fb8cd9636452b8d7fb302a"
)
_STAGE2P_SHA256 = (
    "449efb11b81741e1ac591d6a93033023f67892ac835cbcb178103606eb729dd2"
)
_MANIFEST_SHA256 = (
    "584d2b28bd2c7537f8ebb029633ed7bce682ed02ee38bf32402901940887c955"
)


def _digest(path: Path) -> str:
    text = path.read_bytes().decode("utf-8")
    canonical = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _decision() -> dict[str, object]:
    return json.loads(_DECISION_PATH.read_text(encoding="utf-8"))


def test_stage2u_decision_is_hash_exact_and_chains_prior_boundaries() -> None:
    decision = _decision()
    prior = decision["prior_boundaries"]

    assert _digest(_DECISION_PATH) == _DECISION_SHA256
    assert _digest(_STAGE2T_PATH) == _STAGE2T_SHA256
    assert _digest(_STAGE2P_PATH) == _STAGE2P_SHA256
    assert _digest(_MANIFEST_PATH) == _MANIFEST_SHA256
    assert decision["stage"] == "2U"
    assert decision["admission_status"] == "research_only"
    assert prior["stage2t_decision_sha256"] == _STAGE2T_SHA256
    assert prior["stage2p_decision_sha256"] == _STAGE2P_SHA256
    assert prior["manifest_sha256"] == _MANIFEST_SHA256
    assert set(decision["admission_decision"].values()) == {False}


def test_die_cells_have_exact_identities_locators_and_time_atoms() -> None:
    decision = _decision()
    cells = decision["die_cells"]

    assert decision["governing_object"]["unconflicted_cell_count"] == 5
    assert [cell["ordinal"] for cell in cells] == [1, 2, 3, 4, 5]
    assert [cell["verse"] for cell in cells] == [251, 252, 253, 254, 255]
    assert [cell["pdf_pages"] for cell in cells] == [
        [124, 125],
        [125],
        [125],
        [125, 126],
        [126],
    ]
    assert [cell["printed_pages"] for cell in cells] == [
        [122, 123],
        [123],
        [123],
        [123, 124],
        [124],
    ]
    assert [cell["stated_time_expression"]["kind"] for cell in cells] == [
        "conditional_multiple_month_markers",
        "unreconciled_multiple_source_markers",
        "not_stated",
        "not_stated",
        "not_stated",
    ]
    assert cells[0]["stated_time_expression"]["branches"] == [
        {
            "condition": "rule_enmity",
            "outcome": "mortality_language",
            "kind": "upper_bound_months",
            "values": [2],
        },
        {
            "condition": "source_tanmai_branch",
            "outcome": "not_safely_normalized",
            "kind": "months",
            "values": [6],
        },
    ]
    assert cells[1]["stated_time_expression"]["markers"] == [
        {"kind": "instantaneous", "values": []},
        {"kind": "within_years", "values": [1]},
    ]
    assert cells[1]["stated_time_expression"]["harmonization"] == "forbidden"


def test_stage2u_preserves_relation_space_void_fate_and_effect_roles() -> None:
    cells = _decision()["die_cells"]

    assert [cell["activity_relation_clause"]["surface_statement"] for cell in cells] == [
        "rule_enmity_branch",
        "rule_enmity_branch",
        "earth_rule_enmity_disallowed",
        "rule_enmity_required",
        None,
    ]
    assert [[ref["category"] for ref in cell["space_or_void_reference"]] for cell in cells] == [
        ["akasha_open_space_dosha"],
        ["suniyam_joined_dosha"],
        ["akasha_open_space_dosha", "suniyam_relation"],
        ["suniyam_join_required"],
        [],
    ]
    assert [[ref["source_title"] for ref in cell["deity_or_fate_reference"]] for cell in cells] == [
        ["kootruvan_or_yama"],
        ["kootruvan_or_yama"],
        ["ganges"],
        [],
        ["brahmadeva", "kalan"],
    ]
    assert all(cell["mortality_statement"]["prediction_status"] == "forbidden" for cell in cells)
    assert all(cell["effect_reference"] for cell in cells)
    assert all(cell["uncertainty"] for cell in cells)


def test_verse_250_remains_blocked_and_verse_256_terminates_scope() -> None:
    decision = _decision()
    carry = decision["stage2t_conflict_carry_forward"]
    termination = decision["scope_termination"]

    assert carry == {
        "verse": 250,
        "prior_candidate_ordinal": 5,
        "identity_status": "blocked_text_layer_identity_conflict",
        "heading_layer_activity": "die",
        "verse_layer_activity": "die",
        "commentary_layer_activity": "sleep",
        "stage2u_treatment": "blocked_precursor_only",
        "is_die_cell": False,
        "is_sixth_die_ordinal": False,
        "semantic_normalization_performed": False,
        "resolution_policy": "preserve_stage2t_conflict_without_assignment_or_repair",
    }
    assert decision["governing_object"]["blocked_precursor_count"] == 1
    assert termination == {
        "next_verse": 256,
        "next_section": "illness_duration",
        "included_in_stage2u": False,
        "policy": "stop_at_end_of_five_explicit_die_ordinals",
    }


def test_repeatability_and_runtime_boundaries_fail_closed() -> None:
    decision = _decision()
    repeatability = decision["repeatability_contract"]
    ambiguity = decision["ambiguity_policy"]

    assert repeatability["source_check"] == (
        "rendered_page_controls_semantics_and_archive_ocr_only_aligns_navigation"
    )
    assert repeatability["verbatim_transcription_required_for_this_extension"] is False
    assert repeatability["human_language_reviewer_dependency"] == "none"
    assert ambiguity["identity_inference_from_verse250"] == "forbidden"
    assert ambiguity["mortality_language_as_prediction_or_medical_prognosis"] == "forbidden"
    assert ambiguity["multiple_time_marker_harmonization"] == "forbidden"
    assert ambiguity["space_or_void_reference_as_medical_cause"] == "forbidden"
    assert ambiguity["fate_language_as_deterministic_runtime_rule"] == "forbidden"
    assert ambiguity["activity_relation_runtime_binding"] == "forbidden"
    assert ambiguity["source_branch_calendar_or_runtime_binding"] == "forbidden"
    assert ambiguity["medical_recommendation_or_advice"] == "forbidden"
    assert ambiguity["automatic_stage2o_to_uromarisi_binding"] == "forbidden"
    assert ambiguity["default_selector"] is None

    phase12_governance_names = {
        "PanchaPakshiUromarisiConstitutionStatus",
        "pancha_pakshi_uromarisi_constitution_status",
    }
    for surface in (moira, pakshi, vedic, facade.Moira):
        assert not [
            name
            for name in dir(surface)
            if (
                "uromarisi" in name.lower()
                and name not in phase12_governance_names
            )
            or "illness_outcome" in name.lower()
        ]
    assert {
        route.path
        for route in router_module.router.routes
        if "uromarisi" in route.path.lower()
    } == {"/v1/pancha-pakshi/constitution/uromarisi"}
    assert all(
        "illness-outcome" not in route.path.lower()
        for route in router_module.router.routes
    )
