"""Stage 2T SLEEP semantic atoms, identity conflict, and non-admission guards."""

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
    / "pancha_pakshi_uromarisi_sleep_semantics_stage2t_research_2026_07_21.json"
)
_STAGE2S_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_uromarisi_rule_semantics_stage2s_research_2026_07_21.json"
)
_STAGE2P_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_uromarisi_illness_grid_stage2p_research_2026_07_21.json"
)
_MANIFEST_PATH = _ROOT / "moira" / "data" / "pancha_pakshi_manifest.json"
_DECISION_SHA256 = (
    "09f7651325cdac058d9816b85b031ef528f514ae91fb8cd9636452b8d7fb302a"
)
_STAGE2S_SHA256 = (
    "85142480188a00ddec3de6f192a36025f282ca0eefa4643a6f1d74da4cec811d"
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


def test_stage2t_decision_is_hash_exact_and_chains_prior_boundaries() -> None:
    decision = _decision()
    prior = decision["prior_boundaries"]

    assert _digest(_DECISION_PATH) == _DECISION_SHA256
    assert _digest(_STAGE2S_PATH) == _STAGE2S_SHA256
    assert _digest(_STAGE2P_PATH) == _STAGE2P_SHA256
    assert _digest(_MANIFEST_PATH) == _MANIFEST_SHA256
    assert decision["stage"] == "2T"
    assert decision["admission_status"] == "research_only"
    assert prior["stage2s_decision_sha256"] == _STAGE2S_SHA256
    assert prior["stage2p_decision_sha256"] == _STAGE2P_SHA256
    assert prior["manifest_sha256"] == _MANIFEST_SHA256
    assert set(decision["admission_decision"].values()) == {False}


def test_unconflicted_sleep_cells_have_exact_locators_dispositions_and_times() -> None:
    decision = _decision()
    cells = decision["sleep_cells"]

    assert decision["governing_object"]["unconflicted_cell_count"] == 4
    assert [cell["ordinal"] for cell in cells] == [1, 2, 3, 4]
    assert [cell["verse"] for cell in cells] == [246, 247, 248, 249]
    assert [cell["pdf_pages"] for cell in cells] == [
        [122, 123],
        [123],
        [123],
        [123, 124],
    ]
    assert [cell["disposition_statement"]["value"] for cell in cells] == [
        "stated_resolution_with_difficulty",
        "stated_resolution_with_recurrence_warning",
        "stated_to_resolve",
        "conditional_mortality_or_resolution",
    ]
    assert [cell["stated_time_expression"]["kind"] for cell in cells] == [
        "upper_bound_days",
        "upper_bound_days",
        "exact_days",
        "conditional_upper_bound_months",
    ]
    assert cells[0]["stated_time_expression"]["values"] == [8]
    assert cells[1]["stated_time_expression"]["values"] == [15]
    assert cells[2]["stated_time_expression"]["values"] == [20]
    assert cells[3]["stated_time_expression"]["branches"] == [
        {"condition": "rule_enmity", "outcome": "mortality_language", "values": [3]},
        {"condition": "otherwise", "outcome": "stated_to_resolve", "values": [3]},
    ]


def test_stage2t_preserves_actions_wind_effect_and_mortality_roles() -> None:
    cells = _decision()["sleep_cells"]

    assert [
        [reference["source_title"] for reference in cell["deity_reference"]]
        for cell in cells
    ] == [
        ["kali", "anjaneya"],
        ["kali"],
        ["kali", "vairavar"],
        ["kali"],
    ]
    assert [cell["wind_dosha_reference"]["status"] for cell in cells] == [
        "present",
        "not_recorded",
        "present",
        "not_recorded",
    ]
    assert [
        [effect["category"] for effect in cell["effect_reference"]]
        for cell in cells
    ] == [
        [],
        ["mental_distress", "recurrence_warning"],
        ["body_harm_or_pain_language"],
        ["severe_harm_language"],
    ]
    assert cells[3]["conditional_mortality_reference"] == {
        "status": "present",
        "prediction_status": "forbidden",
    }
    assert all(cell["uncertainty"] for cell in cells)


def test_verse_250_is_blocked_by_exact_text_layer_identity_conflict() -> None:
    decision = _decision()
    conflicts = decision["conflicted_candidates"]
    refinement = decision["stage2p_structural_refinement"]

    assert decision["governing_object"]["conflicted_candidate_count"] == 1
    assert conflicts == [
        {
            "candidate_ordinal": 5,
            "verse": 250,
            "pdf_pages": [124],
            "printed_pages": [122],
            "archive_ocr_navigation_lines": [5841, 5859],
            "identity_status": "blocked_text_layer_identity_conflict",
            "heading_layer_activity": "die",
            "verse_layer_activity": "die",
            "commentary_layer_activity": "sleep",
            "payload_markers": {
                "mortality_language_present": True,
                "commentary_upper_bound_days_candidate": 5,
                "semantic_normalization_performed": False,
            },
            "resolution_policy": (
                "preserve_each_text_layer_and_do_not_assign_the_candidate_to_"
                "sleep_or_die_runtime_outcomes"
            ),
            "uncertainty": [
                "parent_activity_identity_conflicts_between_heading_verse_and_commentary",
                "mortality_payload_not_normalized",
                "time_expression_not_admitted_as_a_cell_semantic_atom",
            ],
        }
    ]
    assert refinement["prior_locator_claim"] == "five_sleep_ordinals_including_verse_250"
    assert refinement["prior_fixture_mutated"] is False
    assert refinement["current_truth"] == (
        "four_unconflicted_sleep_cells_plus_one_blocked_identity_conflict"
    )


def test_repeatability_and_runtime_boundaries_fail_closed() -> None:
    decision = _decision()
    repeatability = decision["repeatability_contract"]
    ambiguity = decision["ambiguity_policy"]

    assert repeatability["source_check"] == (
        "rendered_page_controls_semantics_and_archive_ocr_only_aligns_navigation"
    )
    assert repeatability["verbatim_transcription_required_for_this_extension"] is False
    assert repeatability["human_language_reviewer_dependency"] == "none"
    assert ambiguity["identity_inference_across_conflicting_text_layers"] == "forbidden"
    assert ambiguity["mortality_language_as_prediction_or_medical_prognosis"] == (
        "forbidden"
    )
    assert ambiguity["ritual_efficacy_assertion"] == "forbidden"
    assert ambiguity["wind_dosha_as_medical_cause"] == "forbidden"
    assert ambiguity["effect_reference_as_symptom_or_score"] == "forbidden"
    assert ambiguity["activity_relation_runtime_binding"] == "forbidden"
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
    assert all(
        "uromarisi" not in route.path.lower()
        and "illness-outcome" not in route.path.lower()
        for route in router_module.router.routes
    )
