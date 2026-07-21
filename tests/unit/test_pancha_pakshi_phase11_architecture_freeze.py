"""Constitutional Phase 11 architecture freeze and validation codex."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[2]
_DECISION_PATH = _ROOT / "tests" / "fixtures" / (
    "pancha_pakshi_uromarisi_phase11_architecture_freeze_2026_07_21.json"
)
_PHASE10_PATH = _ROOT / "tests" / "fixtures" / (
    "pancha_pakshi_uromarisi_phase10_full_subsystem_hardening_2026_07_21.json"
)
_STANDARD_PATH = _ROOT / "wiki" / "02_standards" / (
    "PANCHA_PAKSHI_UROMARISI_BACKEND_STANDARD.md"
)
_DECISION_SHA256 = "697eecaf22cf4e8d42ca9b7044633e6407ca8d5577dd4407180029cfc00055c0"
_PHASE10_SHA256 = "9ef977585ad1dc9dc517316eb864a8de26f462fb852977bfef936d8756ef64a0"
_STANDARD_SHA256 = "c71860b482458230ac0b78a2f593286e40294cd51bbc0767bfe3e2c5e2de9b72"


def _digest(path: Path) -> str:
    canonical = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _decision() -> dict[str, object]:
    return json.loads(_DECISION_PATH.read_text(encoding="utf-8"))


def test_phase11_decision_and_standard_are_hash_exact() -> None:
    decision = _decision()
    assert _digest(_DECISION_PATH) == _DECISION_SHA256
    assert _digest(_PHASE10_PATH) == _PHASE10_SHA256
    assert _digest(_STANDARD_PATH) == _STANDARD_SHA256
    assert decision["prior_boundary"]["phase10_decision_sha256"] == _PHASE10_SHA256
    assert decision["architecture_freeze"]["standard_sha256"] == _STANDARD_SHA256
    assert decision["constitutional_phase"] == 11


def test_backend_standard_contains_the_frozen_architecture_and_validation_codex() -> None:
    standard = _STANDARD_PATH.read_text(encoding="utf-8")
    for heading in (
        "## 1. Governing Object",
        "## 2. Constitutional Layers",
        "## 3. Stable Identity and Ordering",
        "## 5. Relation Doctrine",
        "## 7. Network Doctrine",
        "## 8. Hardening Doctrine",
        "## 9. Failure Doctrine",
        "## 10. Public and Private Boundaries",
        "## 11. Validation Codex",
        "## 12. Constitutional Nonclaims",
    ):
        assert heading in standard
    assert "2133ad1c72ea5209facbb83ff8f40cfd09c1efea5340df7943fe08ff599cface" in standard
    assert "not_evaluable_no_admitted_condition_doctrine" in standard
    assert "not evaluable" in standard
    assert "medical use is forbidden" in standard


def test_phase11_freezes_only_the_lawful_phase12_candidate() -> None:
    decision = _decision()
    eligible = decision["phase12_eligible_surface"]
    assert eligible == {
        "product": "immutable_constitutional_status_only",
        "package_export_eligible": True,
        "facade_method_eligible": True,
        "manifest_profile_eligible": False,
        "rest_route_eligible": False,
        "historical_data_eligible": False,
        "network_data_eligible": False,
        "evaluation_or_medical_data_eligible": False,
    }
    assert set(_decision()["admission_decision"].values()) == {False}
    closure = decision["phase11_closure"]
    assert closure["status"] == "complete_architecture_freeze_and_validation_codex"
    assert closure["next_constitutional_phase"] == 12
