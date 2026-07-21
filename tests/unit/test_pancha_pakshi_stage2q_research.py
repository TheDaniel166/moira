"""Stage 2Q EAT-cell semantic-atom pilot and non-admission guards."""

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
    / "pancha_pakshi_uromarisi_eat_semantics_stage2q_research_2026_07_21.json"
)
_STAGE2P_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_uromarisi_illness_grid_stage2p_research_2026_07_21.json"
)
_MANIFEST_PATH = _ROOT / "moira" / "data" / "pancha_pakshi_manifest.json"
_DECISION_SHA256 = (
    "7b4311912ece7f49b30773604c91537ca5fa2a9e02b75baeebfb5bdc2575bcd9"
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


def test_stage2q_decision_is_hash_exact_and_chains_stage2p() -> None:
    decision = _decision()
    prior = decision["prior_boundaries"]

    assert _digest(_DECISION_PATH) == _DECISION_SHA256
    assert _digest(_STAGE2P_PATH) == _STAGE2P_SHA256
    assert _digest(_MANIFEST_PATH) == _MANIFEST_SHA256
    assert decision["stage"] == "2Q"
    assert decision["admission_status"] == "research_only"
    assert prior["stage2p_decision_sha256"] == _STAGE2P_SHA256
    assert prior["manifest_sha256"] == _MANIFEST_SHA256
    assert set(decision["admission_decision"].values()) == {False}


def test_eat_cells_have_exact_locators_and_source_stated_durations() -> None:
    cells = _decision()["eat_cells"]

    assert [cell["ordinal"] for cell in cells] == [1, 2, 3, 4, 5]
    assert [cell["verse"] for cell in cells] == [230, 231, 232, 233, 234]
    assert [cell["pdf_pages"] for cell in cells] == [
        [116],
        [116, 117],
        [117],
        [117],
        [117, 118],
    ]
    assert [cell["stated_duration_days"] for cell in cells] == [
        {"kind": "finite_alternative", "values": [4, 5], "confidence": "high"},
        {"kind": "exact", "values": [7], "confidence": "high"},
        {"kind": "exact", "values": [9], "confidence": "high"},
        {"kind": "exact", "values": [13], "confidence": "high"},
        {"kind": "exact", "values": [15], "confidence": "high"},
    ]
    assert {cell["resolution_statement"] for cell in cells} == {
        "stated_to_resolve"
    }


def test_semantic_atoms_preserve_distinct_responses_and_uncertainty() -> None:
    decision = _decision()
    cells = decision["eat_cells"]
    response_categories = [
        [response["category"] for response in cell["prescribed_response"]]
        for cell in cells
    ]

    assert response_categories == [
        ["vinayaka_abhisheka"],
        ["vinayaka_archana_and_prostration"],
        ["vinayaka_puja"],
        ["vinayaka_named_food_offerings", "brahmin_hospitality"],
        ["vinayaka_abhisheka", "brahmin_food_donation"],
    ]
    assert [cell["medicine_reference"]["status"] for cell in cells] == [
        "present",
        "not_recorded",
        "not_recorded",
        "not_recorded",
        "not_recorded",
    ]
    assert [cell["prithivi_reference"]["status"] for cell in cells] == [
        "not_recorded",
        "present",
        "not_recorded",
        "present",
        "present",
    ]
    assert all(
        cell["unresolved_relation_clause"] == {
            "status": "present",
            "confidence": "high",
            "semantics": None,
        }
        for cell in cells
    )
    assert all(cell["uncertainty"] for cell in cells)
    assert decision["ambiguity_policy"]["generic_favorable_unfavorable_label"] == (
        "forbidden"
    )
    assert decision["ambiguity_policy"]["condition_or_numeric_score"] == "forbidden"


def test_repeatability_contract_and_runtime_boundaries_fail_closed() -> None:
    decision = _decision()
    repeatability = decision["repeatability_contract"]
    ambiguity = decision["ambiguity_policy"]

    assert repeatability["source_check"] == (
        "rendered_page_controls_semantics_and_archive_ocr_only_aligns_navigation"
    )
    assert repeatability["verbatim_transcription_required_for_this_pilot"] is False
    assert repeatability["human_language_reviewer_dependency"] == "none"
    assert ambiguity["unresolved_term_inference"] == "forbidden"
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
