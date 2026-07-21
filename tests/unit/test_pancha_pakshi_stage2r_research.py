"""Stage 2R WALK-cell semantic-atom extension and non-admission guards."""

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
    / "pancha_pakshi_uromarisi_walk_semantics_stage2r_research_2026_07_21.json"
)
_STAGE2Q_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_uromarisi_eat_semantics_stage2q_research_2026_07_21.json"
)
_MANIFEST_PATH = _ROOT / "moira" / "data" / "pancha_pakshi_manifest.json"
_DECISION_SHA256 = (
    "361a0a334a73623cb0b2c1b0e73489db2c20d3c259e04540a303510113f0e0d6"
)
_STAGE2Q_SHA256 = (
    "7b4311912ece7f49b30773604c91537ca5fa2a9e02b75baeebfb5bdc2575bcd9"
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


def test_stage2r_decision_is_hash_exact_and_chains_stage2q() -> None:
    decision = _decision()
    prior = decision["prior_boundaries"]

    assert _digest(_DECISION_PATH) == _DECISION_SHA256
    assert _digest(_STAGE2Q_PATH) == _STAGE2Q_SHA256
    assert _digest(_MANIFEST_PATH) == _MANIFEST_SHA256
    assert decision["stage"] == "2R"
    assert decision["admission_status"] == "research_only"
    assert prior["stage2q_decision_sha256"] == _STAGE2Q_SHA256
    assert prior["manifest_sha256"] == _MANIFEST_SHA256
    assert set(decision["admission_decision"].values()) == {False}


def test_walk_cells_have_exact_locators_dispositions_and_time_expressions() -> None:
    cells = _decision()["walk_cells"]

    assert [cell["ordinal"] for cell in cells] == [1, 2, 3, 4, 5]
    assert [cell["verse"] for cell in cells] == [235, 236, 237, 238, 239]
    assert [cell["pdf_pages"] for cell in cells] == [
        [118],
        [118, 119],
        [119],
        [119],
        [119, 120],
    ]
    assert [cell["disposition_statement"] for cell in cells] == [
        {"value": "stated_to_resolve", "confidence": "high"},
        {"value": "stated_to_abate", "confidence": "medium"},
        {"value": "stated_to_abate", "confidence": "high"},
        {"value": "stated_to_resolve", "confidence": "high"},
        {
            "value": "timed_progression_without_explicit_resolution",
            "confidence": "high",
        },
    ]
    assert [cell["stated_time_expression"] for cell in cells] == [
        {"kind": "exact_days", "values": [10], "confidence": "high"},
        {"kind": "exact_days", "values": [15], "confidence": "high"},
        {"kind": "upper_bound_days", "values": [20], "confidence": "high"},
        {"kind": "exact_days", "values": [25], "confidence": "high"},
        {"kind": "upper_bound_months", "values": [1], "confidence": "high"},
    ]


def test_stage2r_preserves_distinct_titles_responses_and_clause_roles() -> None:
    cells = _decision()["walk_cells"]

    assert [
        [reference["source_title"] for reference in cell["deity_reference"]]
        for cell in cells
    ] == [["vadivelar"], ["kumaraguru"], ["shanmuga"], ["shanmuga"], ["velavar"]]
    assert [
        [
            (response["category"], response["relation"])
            for response in cell["response_or_mediation"]
        ]
        for cell in cells
    ] == [
        [("vadivelar_worship", "prescribed")],
        [],
        [],
        [
            ("physician_treatment_reference", "stated_mediation"),
            ("shanti_rite", "stated_mediation"),
        ],
        [("velavar_abhisheka", "prescribed")],
    ]
    assert [cell["water_reference"]["role"] for cell in cells] == [
        None,
        "antagonistic_relation",
        "affliction_attribution",
        "constituent_attribution",
        "transformation_clause_semantics_unresolved",
    ]
    assert [cell["medicine_or_physician_reference"]["status"] for cell in cells] == [
        "not_recorded",
        "not_recorded",
        "not_recorded",
        "present",
        "not_recorded",
    ]
    assert [cell["navagraha_dosha_reference"]["status"] for cell in cells] == [
        "not_recorded",
        "not_recorded",
        "not_recorded",
        "present",
        "not_recorded",
    ]
    assert all(cell["unresolved_relation_clause"]["semantics"] is None for cell in cells)
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
    assert ambiguity["resolution_inference_from_abatement_or_progression"] == "forbidden"
    assert ambiguity["day_conversion_from_month_expression"] == "forbidden"
    assert ambiguity["deity_title_collapsing"] == "forbidden"
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
