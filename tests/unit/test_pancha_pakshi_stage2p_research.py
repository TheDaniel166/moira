"""Stage 2P illness-grid locator recovery and non-admission guards."""

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
    / "pancha_pakshi_uromarisi_illness_grid_stage2p_research_2026_07_21.json"
)
_STAGE2J_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_uromarisi_vinadi_stage2j_research_2026_07_21.json"
)
_STAGE2O_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_civil_time_sookshma_selection_stage2o_2026_07_21.json"
)
_MANIFEST_PATH = _ROOT / "moira" / "data" / "pancha_pakshi_manifest.json"
_DECISION_SHA256 = (
    "449efb11b81741e1ac591d6a93033023f67892ac835cbcb178103606eb729dd2"
)
_STAGE2J_SHA256 = (
    "d04ed0f3716fe605dc5d8172114dc759b30c4e87be968eebc36e35a23d789243"
)
_STAGE2O_SHA256 = (
    "2ea686e774ba4468c0515f621771b8a142c79f04d89b69839f482e05c37b40df"
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


def test_stage2p_decision_is_hash_exact_and_chains_existing_boundaries() -> None:
    decision = _decision()
    prior = decision["prior_boundaries"]

    assert _digest(_DECISION_PATH) == _DECISION_SHA256
    assert _digest(_STAGE2J_PATH) == _STAGE2J_SHA256
    assert _digest(_STAGE2O_PATH) == _STAGE2O_SHA256
    assert _digest(_MANIFEST_PATH) == _MANIFEST_SHA256
    assert decision["stage"] == "2P"
    assert decision["admission_status"] == "research_only"
    assert prior["stage2j_decision_sha256"] == _STAGE2J_SHA256
    assert prior["stage2o_decision_sha256"] == _STAGE2O_SHA256
    assert prior["manifest_sha256"] == _MANIFEST_SHA256
    assert set(decision["admission_decision"].values()) == {False}


def test_illness_grid_is_exactly_five_activities_by_five_ordinals() -> None:
    decision = _decision()
    recovered = decision["recovered_computational_object"]
    grid = decision["illness_grid"]

    assert recovered["context_family"] == "illness"
    assert recovered["cell_count"] == 25
    assert [row["parent_activity"] for row in grid] == [
        "eat",
        "walk",
        "rule",
        "sleep",
        "die",
    ]
    cells = []
    for row in grid:
        assert [cell["ordinal"] for cell in row["cells"]] == [1, 2, 3, 4, 5]
        cells.extend(
            (row["parent_activity"], cell["ordinal"])
            for cell in row["cells"]
        )
    assert len(cells) == 25
    assert len(set(cells)) == 25


def test_verse_and_page_locators_cover_the_grid_without_absorbing_transitions() -> None:
    decision = _decision()
    cells = [
        cell
        for row in decision["illness_grid"]
        for cell in row["cells"]
    ]
    verses = [cell["verse"] for cell in cells]

    assert verses == [
        *range(230, 240),
        *range(241, 256),
    ]
    assert 240 not in verses
    assert all(
        116 <= page <= 126
        for cell in cells
        for page in cell["pdf_pages"]
    )
    assert all(
        printed == pdf - 2
        for cell in cells
        for pdf, printed in zip(cell["pdf_pages"], cell["printed_pages"])
    )
    assert decision["structural_notes"]["verse_240_status"] == (
        "intervening_transition_verse_not_an_illness_grid_cell_heading"
    )
    assert decision["structural_notes"]["post_grid_material"] == (
        "verse_256_begins_a_separate_illness_duration_section_after_the_"
        "twenty_five_cell_grid"
    )


def test_stage2p_preserves_semantic_and_runtime_fail_closed_boundaries() -> None:
    decision = _decision()
    recovered = decision["recovered_computational_object"]
    ambiguity = decision["ambiguity_policy"]

    assert recovered["outcome_semantic_normalization_status"] == "not_performed"
    assert recovered["translation_status"] == "not_admitted"
    assert recovered["prognostic_interpretation_status"] == "not_admitted"
    assert ambiguity["automatic_stage2o_to_uromarisi_binding"] == "forbidden"
    assert ambiguity["weighted_selector_binding"] == "not_attested"
    assert ambiguity["equal_fifths_selector_binding"] == "not_attested"
    assert ambiguity["default_selector"] is None
    assert ambiguity["outcome_label_inference"] == "forbidden"
    assert ambiguity["condition_or_score_mapping"] == "forbidden"
    assert ambiguity["human_language_reviewer_dependency"] == "none"

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
            or "illness_grid" in name.lower()
        ]
    assert all(
        "uromarisi" not in route.path.lower()
        and "illness-grid" not in route.path.lower()
        for route in router_module.router.routes
    )
