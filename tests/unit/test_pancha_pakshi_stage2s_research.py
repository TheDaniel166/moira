"""Stage 2S RULE-cell semantic-atom extension and non-admission guards."""

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
    / "pancha_pakshi_uromarisi_rule_semantics_stage2s_research_2026_07_21.json"
)
_STAGE2R_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_uromarisi_walk_semantics_stage2r_research_2026_07_21.json"
)
_MANIFEST_PATH = _ROOT / "moira" / "data" / "pancha_pakshi_manifest.json"
_DECISION_SHA256 = (
    "85142480188a00ddec3de6f192a36025f282ca0eefa4643a6f1d74da4cec811d"
)
_STAGE2R_SHA256 = (
    "361a0a334a73623cb0b2c1b0e73489db2c20d3c259e04540a303510113f0e0d6"
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


def test_stage2s_decision_is_hash_exact_and_chains_stage2r() -> None:
    decision = _decision()
    prior = decision["prior_boundaries"]

    assert _digest(_DECISION_PATH) == _DECISION_SHA256
    assert _digest(_STAGE2R_PATH) == _STAGE2R_SHA256
    assert _digest(_MANIFEST_PATH) == _MANIFEST_SHA256
    assert decision["stage"] == "2S"
    assert decision["admission_status"] == "research_only"
    assert prior["stage2r_decision_sha256"] == _STAGE2R_SHA256
    assert prior["manifest_sha256"] == _MANIFEST_SHA256
    assert set(decision["admission_decision"].values()) == {False}


def test_rule_cells_have_exact_locators_dispositions_and_time_expressions() -> None:
    cells = _decision()["rule_cells"]

    assert [cell["ordinal"] for cell in cells] == [1, 2, 3, 4, 5]
    assert [cell["verse"] for cell in cells] == [241, 242, 243, 244, 245]
    assert [cell["pdf_pages"] for cell in cells] == [
        [120, 121],
        [121],
        [121],
        [121, 122],
        [122],
    ]
    assert {cell["disposition_statement"]["value"] for cell in cells} == {
        "stated_to_resolve"
    }
    assert [cell["stated_time_expression"] for cell in cells] == [
        {"kind": "exact_days", "values": [3], "confidence": "high"},
        {"kind": "exact_days", "values": [5], "confidence": "high"},
        {"kind": "upper_bound_days", "values": [8], "confidence": "high"},
        {"kind": "exact_days", "values": [10], "confidence": "high"},
        {"kind": "exact_days", "values": [12], "confidence": "high"},
    ]


def test_stage2s_preserves_titles_actions_fire_dosha_and_effect_roles() -> None:
    cells = _decision()["rule_cells"]

    assert [
        [reference["source_title"] for reference in cell["deity_reference"]]
        for cell in cells
    ] == [
        ["shiva"],
        ["shiva"],
        ["shiva"],
        ["shiva", "lakshmi"],
        ["parameshvara", "uma_parvati"],
    ]
    assert [
        [
            (response["category"], response["relation"])
            for response in cell["response_or_mediation"]
        ]
        for cell in cells
    ] == [
        [
            ("shiva_abhisheka", "prescribed"),
            ("shiva_circumambulation", "prescribed"),
        ],
        [],
        [("shiva_abhisheka", "prescribed")],
        [("shiva_abhisheka", "prescribed")],
        [],
    ]
    assert [cell["fire_reference"]["role"] for cell in cells] == [
        "heat_attribution",
        "non_harm_clause_semantics_unresolved",
        "dosha_attribution",
        None,
        "heat_attribution",
    ]
    assert [cell["saturn_dosha_reference"]["status"] for cell in cells] == [
        "not_recorded",
        "present",
        "not_recorded",
        "present",
        "not_recorded",
    ]
    assert [cell["activity_relation_clause"]["surface_statement"] for cell in cells] == [
        None,
        None,
        None,
        "no_enmity",
        None,
    ]
    assert [
        [effect["category"] for effect in cell["effect_reference"]]
        for cell in cells
    ] == [
        ["body_heat_and_melting_simile"],
        ["minimal_harm_or_strength_statement"],
        [],
        [],
        ["strength_reduction", "absence_of_joy"],
    ]
    assert all(cell["uncertainty"] for cell in cells)


def test_repeatability_and_runtime_boundaries_fail_closed() -> None:
    decision = _decision()
    repeatability = decision["repeatability_contract"]
    ambiguity = decision["ambiguity_policy"]

    assert repeatability["source_check"] == (
        "rendered_page_controls_semantics_and_archive_ocr_only_aligns_navigation"
    )
    assert repeatability["verbatim_transcription_required_for_this_extension"] is False
    assert repeatability["human_language_reviewer_dependency"] == "none"
    assert ambiguity["exact_day_inference_from_upper_bound"] == "forbidden"
    assert ambiguity["deity_title_collapsing"] == "forbidden"
    assert ambiguity["fire_or_dosha_as_medical_cause"] == "forbidden"
    assert ambiguity["effect_reference_as_symptom_or_score"] == "forbidden"
    assert ambiguity["activity_relation_runtime_binding"] == "forbidden"
    assert ambiguity["generic_favorable_unfavorable_label"] == "forbidden"
    assert ambiguity["condition_or_numeric_score"] == "forbidden"
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
