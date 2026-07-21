"""Stage 2L independent-witness collation and non-admission guards."""

from __future__ import annotations

import hashlib
import json
from fractions import Fraction
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
    / "pancha_pakshi_independent_witness_stage2l_research_2026_07_21.json"
)
_PRIOR_DECISION_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_bogamuni_2024_sookshma_temporal_selector_2026_07_21.json"
)
_MANIFEST_PATH = _ROOT / "moira" / "data" / "pancha_pakshi_manifest.json"
_DECISION_SHA256 = (
    "5534ddde1c0b87fa5fc3332112d02fd1c48c38e0a79f45f4a75a3e3c728a4c34"
)
_PRIOR_DECISION_SHA256 = (
    "10bcfbd70dda28fd399e5c95b8bfa237b8e48f3b2cb20901fc21e0261a73cf70"
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


def test_stage2l_decision_is_hash_exact_and_preserves_stage2k() -> None:
    decision = _decision()

    assert _digest(_DECISION_PATH) == _DECISION_SHA256
    assert _digest(_PRIOR_DECISION_PATH) == _PRIOR_DECISION_SHA256
    assert _digest(_MANIFEST_PATH) == _MANIFEST_SHA256
    assert decision["admission_status"] == "research_only"
    assert decision["prior_public_state"] == {
        "stage": "2K",
        "manifest_path": "moira/data/pancha_pakshi_manifest.json",
        "manifest_sha256": _MANIFEST_SHA256,
        "decision_path": (
            "tests/fixtures/"
            "pancha_pakshi_bogamuni_2024_sookshma_temporal_selector_"
            "2026_07_21.json"
        ),
        "decision_sha256": _PRIOR_DECISION_SHA256,
        "manifest_changed": False,
    }
    assert set(decision["admission_decision"].values()) == {False}


def test_collation_preserves_agreement_and_material_conflict() -> None:
    decision = _decision()
    collation = decision["collation"]

    first_eat = collation["purva_day_first_eat_bird_weekday_mapping"]
    assert first_eat["agreement"] == "exact_all_seven_cells"
    assert first_eat["cells"] == {
        "sunday": "vulture",
        "monday": "owl",
        "tuesday": "vulture",
        "wednesday": "owl",
        "thursday": "crow",
        "friday": "cock",
        "saturday": "peacock",
    }

    vectors = collation["duration_vectors_nazhigai"]
    parsed = {
        name: {activity: Fraction(value) for activity, value in vector.items()}
        for name, vector in vectors.items()
        if isinstance(vector, dict)
    }
    assert all(sum(vector.values()) == Fraction(6) for vector in parsed.values())
    assert parsed["agastya_1879_all_regimes"] == parsed[
        "sarasvati_2014_and_narasimhan_waxing_day"
    ]
    assert parsed["agastya_1879_all_regimes"] != parsed[
        "sarasvati_2014_and_narasimhan_waxing_night"
    ]
    assert parsed["agastya_1879_all_regimes"] != parsed[
        "sarasvati_2014_and_narasimhan_waning_day"
    ]
    assert parsed["agastya_1879_all_regimes"] != parsed[
        "sarasvati_2014_and_narasimhan_waning_night"
    ]
    assert collation["textual_lineage_determination"] == (
        "not_established_for_any_comparable_witness"
    )
    assert collation["admission_tier_after_collation"] == (
        "source_scoped_public_unchanged"
    )


def test_witness_classification_rejects_false_independence() -> None:
    decision = _decision()
    witnesses = {
        witness["witness_id"]: witness
        for witness in decision["inspected_witnesses"]
    }

    sarasvati = witnesses["tva_bok_0022647_valaiyarul_patinen_siddhargal_2014"]
    assert sarasvati["pdf_sha256"] == (
        "894f88c3381f026aa1963861dd30e1f74039aa32a89fd84015efb3a098dc5366"
    )
    assert sarasvati["pdf_page_count"] == 574
    assert sarasvati["textual_lineage_independence"] == "not_established"
    assert {locator["pdf_page"] for locator in sarasvati["locators"]} == {
        2,
        4,
        30,
        31,
        33,
        37,
        88,
        89,
        136,
        209,
        302,
    }

    narasimhan = witnesses["gr_narasimhan_simplified_pancha_pakshi_2018"]
    assert narasimhan["evidence_class"] == "modern_secondary_table_comparator"
    assert narasimhan["textual_lineage_independence"] == "not_documented"
    assert narasimhan["source_citation_status"] == (
        "no_bibliography_citations_or_primary_text_lineage_found"
    )

    rejected = witnesses["panch_pakshi_guide_canva_2025"]
    assert rejected["evidence_class"] == "rejected_unreliable_modern_guide"
    assert rejected["metadata_ai_generated_content"] is True
    assert len(rejected["rejection_reasons"]) == 4

    ambiguity = decision["ambiguity_policy"]
    assert ambiguity["publication_separation_equals_textual_independence"] is False
    assert ambiguity["matching_rows_override_conflicting_rows"] is False
    assert ambiguity["catalog_record_can_supply_computational_rules"] is False
    assert ambiguity["human_language_reviewer_dependency"] == "none"


def test_stage2l_creates_no_runtime_or_public_surface() -> None:
    decision = _decision()
    manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest_tokens = json.dumps(manifest, sort_keys=True).lower()

    assert decision["gate"]["result"] == "collation_completed_gate_not_cleared"
    assert all(
        entry["admission_status"] == "source_scoped_public"
        for entry in manifest["profiles"]
    )
    assert "corroborated_public" not in manifest_tokens
    for token in ("stage2l", "narasimhan", "valaiyarul", "independent_witness"):
        assert token not in manifest_tokens
        for surface in (moira, pakshi, vedic, facade.Moira):
            assert not [name for name in dir(surface) if token in name.lower()]
        assert all(token not in route.path.lower() for route in router_module.router.routes)
