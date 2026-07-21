"""Stage 2M Ramadevar candidate identity, access, and non-admission guards."""

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
    / "pancha_pakshi_ramadevar_candidate_stage2m_research_2026_07_21.json"
)
_PRIOR_DECISION_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_independent_witness_stage2l_research_2026_07_21.json"
)
_MANIFEST_PATH = _ROOT / "moira" / "data" / "pancha_pakshi_manifest.json"
_DECISION_SHA256 = (
    "921e604bcd81298aa6eb903acc967e68cfcf6e743c7d1379788ff9996212c6db"
)
_PRIOR_DECISION_SHA256 = (
    "5534ddde1c0b87fa5fc3332112d02fd1c48c38e0a79f45f4a75a3e3c728a4c34"
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


def test_stage2m_decision_is_hash_exact_and_preserves_stage2l() -> None:
    decision = _decision()

    assert _digest(_DECISION_PATH) == _DECISION_SHA256
    assert _digest(_PRIOR_DECISION_PATH) == _PRIOR_DECISION_SHA256
    assert _digest(_MANIFEST_PATH) == _MANIFEST_SHA256
    assert decision["admission_status"] == "research_only"
    assert decision["prior_public_state"] == {
        "stage": "2L",
        "manifest_path": "moira/data/pancha_pakshi_manifest.json",
        "manifest_sha256": _MANIFEST_SHA256,
        "decision_path": (
            "tests/fixtures/"
            "pancha_pakshi_independent_witness_stage2l_research_2026_07_21.json"
        ),
        "decision_sha256": _PRIOR_DECISION_SHA256,
        "manifest_changed": False,
    }
    assert set(decision["admission_decision"].values()) == {False}


def test_A5_target_remains_title_only_and_not_assessable() -> None:
    target = _decision()["target_candidate"]

    assert target["catalog_pdf_sha256"] == (
        "8bf4541aa46e3526d3218b1c35ae7bf174298ff6e29e86d9e10e7389dd5b5e4b"
    )
    assert target["catalog_pdf_page_count"] == 63
    assert target["catalog_fields_present"] == {
        "serial_number": "859",
        "manuscript_number": "A5",
        "title": "Ramadevar Panchapakshi",
    }
    assert {locator["pdf_page"] for locator in target["locators"]} == {1, 2, 52}
    assert target["content_access_status"] == "catalog_title_only"
    assert target["textual_lineage_independence"] == "not_assessable"
    assert target["product_comparability"] == "not_assessable"
    assert len(target["required_fields_absent"]) == 11


def test_patchani_false_cognates_cannot_clear_panchapakshi_gate() -> None:
    decision = _decision()
    witnesses = {
        witness["witness_id"]: witness
        for witness in decision["disambiguated_false_cognates"]
    }

    goml = witnesses["goml_r8978_ramadevar_patchini"]
    assert goml["catalog_pdf_sha256"] == (
        "4ff7f72891c6d53c3eaac502f1f1217a0cb950b60611524bfaff854d38b03ec4"
    )
    assert goml["catalog_facts"]["shelfmark"] == "R.8978"
    assert goml["catalog_facts"]["content_class"] == "gnana_breath_and_yoga"
    assert goml["same_product_as_target"] is False

    eap = witnesses["british_library_eap1217_1_2851_ramadevar_patchani"]
    assert eap["date_range"] == "18th_century"
    assert eap["original_institution_reference"] == "TU_TAMIL_2058-01_2661"
    assert eap["same_product_as_target"] is False

    composite = witnesses["commissionerate_manuscript_27_ramadevar_patchani_108"]
    assert composite["locator"] == {
        "pdf_page": 4,
        "serial_number": "27",
        "manuscript_number": "27",
    }
    assert composite["same_record_as_target"] is False

    publication = witnesses[
        "sarasvati_mahal_ramadevar_sutiram_ashtanga_patchini_1991"
    ]
    assert publication["pdf_sha256"] == (
        "238987ee86aba6b17c963031616fc58598fa308df0c8ffec2a6314ed89156021"
    )
    assert publication["same_product_as_target"] is False

    identity = decision["identity_policy"]
    assert identity["patchani_equals_panchapakshi"] is False
    assert identity["shared_ramadevar_attribution_establishes_same_work"] is False
    assert identity["shared_108_poem_count_establishes_same_work"] is False
    assert identity["catalog_title_establishes_computational_content"] is False


def test_stage2m_creates_no_runtime_or_public_surface() -> None:
    decision = _decision()
    manifest = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest_tokens = json.dumps(manifest, sort_keys=True).lower()

    assert decision["gate"]["result"] == (
        "candidate_identified_but_content_and_copying_history_unavailable"
    )
    assert decision["copying_history_determination"] == {
        "target_A5": "unavailable",
        "false_cognates": (
            "irrelevant_to_target_independence_because_they_are_different_products"
        ),
        "independence_gate": "not_cleared",
    }
    assert "ramadevar" not in manifest_tokens
    assert not any(name.startswith("ramadevar") for name in dir(pakshi))
    assert not any(name.startswith("ramadevar") for name in dir(moira))
    assert not any(name.startswith("ramadevar") for name in dir(vedic))
    assert not any(name.startswith("ramadevar") for name in dir(facade.Moira))
    route_paths = {route.path.lower() for route in router_module.router.routes}
    assert not any("ramadevar" in path for path in route_paths)
