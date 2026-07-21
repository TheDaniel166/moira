"""Constitutional Phase 10 Uromarisi full-subsystem hardening."""

from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

import moira
import moira._pancha_pakshi_hardening as hardening_module
import moira.facade as facade
import moira.pancha_pakshi as pakshi
import moira.vedic as vedic
from moira._pancha_pakshi_condition import (
    PanchaPakshiHistoricalLocalConditionProfile,
)
from moira._pancha_pakshi_hardening import (
    pancha_pakshi_uromarisi_hardening_receipt,
)
from moira_server.routers import pancha_pakshi as router_module
from tests.unit.test_pancha_pakshi_phase9_network_intelligence import _network


_ROOT = Path(__file__).resolve().parents[2]
_DECISION_PATH = _ROOT / "tests" / "fixtures" / (
    "pancha_pakshi_uromarisi_phase10_full_subsystem_hardening_2026_07_21.json"
)
_PHASE9_PATH = _ROOT / "tests" / "fixtures" / (
    "pancha_pakshi_uromarisi_phase9_network_intelligence_2026_07_21.json"
)
_DECISION_SHA256 = "9ef977585ad1dc9dc517316eb864a8de26f462fb852977bfef936d8756ef64a0"
_PHASE9_SHA256 = "49935df6e96595b5cd365dbea12acabcf862eb81a120c3d9122d29ad4962872b"


def _digest(path: Path) -> str:
    canonical = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _decision() -> dict[str, object]:
    return json.loads(_DECISION_PATH.read_text(encoding="utf-8"))


def test_phase10_decision_is_hash_exact_and_chains_phase9() -> None:
    decision = _decision()
    assert _digest(_DECISION_PATH) == _DECISION_SHA256
    assert _digest(_PHASE9_PATH) == _PHASE9_SHA256
    assert decision["prior_boundary"]["phase9_decision_sha256"] == _PHASE9_SHA256
    assert decision["constitutional_phase"] == 10
    assert set(decision["admission_decision"].values()) == {False}


def test_hardening_receipt_matches_exact_cross_layer_contract() -> None:
    receipt = pancha_pakshi_uromarisi_hardening_receipt(_network())
    contract = _decision()["hardening_contract"]

    assert list(receipt.layer_sequence) == contract["layer_sequence"]
    assert receipt.profile_count == contract["profile_count"]
    assert receipt.relation_candidate_count == contract["relation_candidate_count"]
    assert receipt.admitted_edge_count == contract["admitted_edge_count"]
    assert receipt.scored_edge_count == contract["scored_edge_count"]
    assert list(receipt.blocked_verses) == contract["blocked_verses"]
    assert len(receipt.source_bindings) == contract["source_binding_count"]
    assert receipt.structural_sha256 == contract["structural_sha256"]
    assert receipt.invariant_status == contract["invariant_status"]
    assert receipt.ordering_status == contract["ordering_status"]
    assert receipt.inference_policy == contract["inference_policy"]


def test_hardening_is_repeatable_and_immutable() -> None:
    first = pancha_pakshi_uromarisi_hardening_receipt(_network())
    second = pancha_pakshi_uromarisi_hardening_receipt(_network())
    assert first == second
    assert first.failure_policy == "fail_closed"
    assert len(first.node_ids) == len(set(first.node_ids)) == 24
    with pytest.raises(FrozenInstanceError):
        first.structural_sha256 = "0" * 64


def test_cross_layer_adversarial_drift_fails_closed() -> None:
    network = _network()
    first_profile = network.nodes[0].profile
    forged_relation = replace(
        first_profile.relation, source_decision_sha256="0" * 64
    )

    with pytest.raises(TypeError, match="network"):
        pancha_pakshi_uromarisi_hardening_receipt(object())
    with pytest.raises(ValueError, match="canonical"):
        replace(network, nodes=tuple(reversed(network.nodes)))
    with pytest.raises(ValueError, match="canonical"):
        replace(network, nodes=(network.nodes[0],) + network.nodes[:-1])
    with pytest.raises(ValueError, match="source bindings"):
        PanchaPakshiHistoricalLocalConditionProfile(
            classification=first_profile.classification,
            relation=forged_relation,
            policy=first_profile.policy,
        )
    with pytest.raises(ValueError, match="no admitted or scored"):
        replace(network, admitted_edges=(("invented", "edge"),))
    receipt = pancha_pakshi_uromarisi_hardening_receipt(network)
    with pytest.raises(ValueError, match="24 unique"):
        replace(receipt, node_ids=receipt.node_ids[:-1])
    with pytest.raises(ValueError, match="invented"):
        replace(receipt, admitted_edge_count=1)
    with pytest.raises(ValueError, match="blocked verse 250"):
        replace(receipt, blocked_verses=())


def test_phase10_remains_private_and_opens_only_phase11() -> None:
    decision = _decision()
    assert hardening_module.__all__ == ()
    for namespace in (moira, facade, pakshi, vedic, router_module):
        assert not hasattr(
            namespace, "PanchaPakshiUromarisiPhase10HardeningReceipt"
        )
        assert not hasattr(
            namespace, "pancha_pakshi_uromarisi_hardening_receipt"
        )
    closure = decision["phase10_closure"]
    assert closure["status"] == "complete_private_full_subsystem_hardening"
    assert closure["next_constitutional_phase"] == 11
    assert closure["architecture_document_may_now_follow_executable_truth"] is True
