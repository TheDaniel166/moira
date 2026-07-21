"""Constitutional Phase 12 public API curation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError, asdict
from pathlib import Path

import pytest

import moira
import moira.facade as facade
import moira.pancha_pakshi as pakshi
import moira.vedic as vedic
from moira.pancha_pakshi import (
    PanchaPakshiAdmissionStatus,
    PanchaPakshiUromarisiConstitutionStatus,
    pancha_pakshi_uromarisi_constitution_status,
)
from moira_server.routers import pancha_pakshi as router_module


_ROOT = Path(__file__).resolve().parents[2]
_DECISION_PATH = _ROOT / "tests" / "fixtures" / (
    "pancha_pakshi_uromarisi_phase12_public_api_curation_2026_07_21.json"
)
_PHASE11_PATH = _ROOT / "tests" / "fixtures" / (
    "pancha_pakshi_uromarisi_phase11_architecture_freeze_2026_07_21.json"
)
_STANDARD_PATH = _ROOT / "wiki" / "02_standards" / (
    "PANCHA_PAKSHI_UROMARISI_BACKEND_STANDARD.md"
)
_MANIFEST_PATH = _ROOT / "moira" / "data" / "pancha_pakshi_manifest.json"
_DECISION_SHA256 = "581c137bbbd0fdfe11f61dbb43bfb6cc6e1dafd420f52dd80c2413a4a59ada03"
_PHASE11_SHA256 = "697eecaf22cf4e8d42ca9b7044633e6407ca8d5577dd4407180029cfc00055c0"
_STANDARD_SHA256 = "c71860b482458230ac0b78a2f593286e40294cd51bbc0767bfe3e2c5e2de9b72"


def _digest(path: Path) -> str:
    canonical = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _decision() -> dict[str, object]:
    return json.loads(_DECISION_PATH.read_text(encoding="utf-8"))


def test_phase12_decision_is_hash_exact_and_chains_phase11() -> None:
    decision = _decision()
    assert _digest(_DECISION_PATH) == _DECISION_SHA256
    assert _digest(_PHASE11_PATH) == _PHASE11_SHA256
    assert _digest(_STANDARD_PATH) == _STANDARD_SHA256
    assert decision["prior_boundary"]["phase11_decision_sha256"] == _PHASE11_SHA256
    assert decision["constitutional_phase"] == 12


def test_public_status_matches_the_exact_curated_contract() -> None:
    status = pancha_pakshi_uromarisi_constitution_status()
    contract = _decision()["public_contract"]
    payload = asdict(status)
    payload["completed_phases"] = list(payload["completed_phases"])
    payload["admission_status"] = payload["admission_status"].value
    assert payload == contract
    assert status.admission_status is PanchaPakshiAdmissionStatus.RESEARCH_ONLY
    assert not hasattr(status, "nodes")
    assert not hasattr(status, "relations")
    assert not hasattr(status, "condition_score")
    assert not hasattr(status, "source_text")


def test_public_status_is_immutable_kernel_free_and_has_no_caller_policy() -> None:
    first = pancha_pakshi_uromarisi_constitution_status()
    second = pancha_pakshi_uromarisi_constitution_status()
    assert first == second == PanchaPakshiUromarisiConstitutionStatus()
    with pytest.raises(TypeError):
        PanchaPakshiUromarisiConstitutionStatus(completed_phases=(1,))
    with pytest.raises(FrozenInstanceError):
        first.medical_use_status = "allowed"


def test_public_exports_and_facade_share_one_curated_identity() -> None:
    names = (
        "PanchaPakshiUromarisiConstitutionStatus",
        "pancha_pakshi_uromarisi_constitution_status",
    )
    for name in names:
        expected = getattr(pakshi, name)
        for namespace in (moira, facade, vedic):
            assert name in namespace.__all__
            assert getattr(namespace, name) is expected
    engine = object.__new__(facade.Moira)
    engine._reader_obj = None
    assert engine.pancha_pakshi_uromarisi_constitution_status() == (
        pancha_pakshi_uromarisi_constitution_status()
    )


def test_phase12_does_not_admit_private_data_manifest_or_rest() -> None:
    decision = _decision()
    manifest = _MANIFEST_PATH.read_text(encoding="utf-8")
    assert decision["decision_id"] not in manifest
    assert "uromarisi" not in manifest.lower()
    route_paths = tuple(route.path for route in router_module.router.routes)
    assert all("constitution" not in path for path in route_paths)
    for namespace in (moira, facade, pakshi, vedic, router_module):
        assert not hasattr(namespace, "PanchaPakshiUromarisiPhase9Network")
        assert not hasattr(
            namespace, "PanchaPakshiUromarisiPhase10HardeningReceipt"
        )
    closure = decision["phase12_closure"]
    assert closure["status"] == "complete_public_api_curation"
    assert closure["completed_constitutional_phases"] == list(range(1, 13))
    assert closure["next_constitutional_phase"] is None
    assert closure["historical_research_boundary_remains_private"] is True
