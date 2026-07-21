"""Constitutional Phase 9 Uromarisi structural network intelligence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

import moira
import moira._pancha_pakshi_network as network_module
import moira.facade as facade
import moira.pancha_pakshi as pakshi
import moira.vedic as vedic
from moira._pancha_pakshi_aggregate import (
    pancha_pakshi_uromarisi_aggregate_intelligence,
)
from moira._pancha_pakshi_classification import (
    PanchaPakshiHistoricalCellClassification,
    PanchaPakshiHistoricalClassificationPolicy,
    PanchaPakshiHistoricalClassificationPolicyId,
    PanchaPakshiHistoricalDisposition,
    PanchaPakshiHistoricalIdentityConflict,
    PanchaPakshiHistoricalSemanticMarker,
    PanchaPakshiHistoricalTimeClass,
    PanchaPakshiUromarisiPhase2ClassificationCorpus,
)
from moira._pancha_pakshi_condition import (
    pancha_pakshi_uromarisi_local_conditions_under_policy,
)
from moira._pancha_pakshi_network import (
    PanchaPakshiHistoricalNetworkMetricStatus,
    PanchaPakshiHistoricalRelationCandidate,
    pancha_pakshi_uromarisi_network,
)
from moira._pancha_pakshi_relations import (
    PanchaPakshiHistoricalRelationConfidence,
    PanchaPakshiHistoricalRelationPresence,
    PanchaPakshiHistoricalRelationRecord,
    PanchaPakshiHistoricalRelationSurfaceKind,
    PanchaPakshiUromarisiPhase5RelationCorpus,
)
from moira.pancha_pakshi import PanchaPakshiActivity
from moira_server.routers import pancha_pakshi as router_module


_ROOT = Path(__file__).resolve().parents[2]
_DECISION_PATH = _ROOT / "tests" / "fixtures" / (
    "pancha_pakshi_uromarisi_phase9_network_intelligence_2026_07_21.json"
)
_PHASE8_PATH = _ROOT / "tests" / "fixtures" / (
    "pancha_pakshi_uromarisi_phase8_aggregate_intelligence_2026_07_21.json"
)
_PHASE5_PATH = _ROOT / "tests" / "fixtures" / (
    "pancha_pakshi_uromarisi_phase5_relations_2026_07_21.json"
)
_PHASE2_PATH = _ROOT / "tests" / "fixtures" / (
    "pancha_pakshi_uromarisi_phase2_classification_closure_2026_07_21.json"
)
_MANIFEST_PATH = _ROOT / "moira" / "data" / "pancha_pakshi_manifest.json"
_DECISION_SHA256 = "49935df6e96595b5cd365dbea12acabcf862eb81a120c3d9122d29ad4962872b"
_PHASE8_SHA256 = "b193b3ba62d1c5eb57d526777310fa16f29c81fa999e69b813670c680ba2fd13"
_MANIFEST_SHA256 = "584d2b28bd2c7537f8ebb029633ed7bce682ed02ee38bf32402901940887c955"


def _digest(path: Path) -> str:
    canonical = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _decision() -> dict[str, object]:
    return json.loads(_DECISION_PATH.read_text(encoding="utf-8"))


def _classification_corpus() -> PanchaPakshiUromarisiPhase2ClassificationCorpus:
    phase2 = json.loads(_PHASE2_PATH.read_text(encoding="utf-8"))
    boundaries = phase2["prior_truth_boundaries"]
    cells = tuple(
        PanchaPakshiHistoricalCellClassification(
            activity=PanchaPakshiActivity(row["activity"]),
            ordinal=row["ordinal"],
            verse=row["verse"],
            disposition=PanchaPakshiHistoricalDisposition(row["disposition"]),
            time_class=PanchaPakshiHistoricalTimeClass(row["time_class"]),
            semantic_markers=frozenset(
                PanchaPakshiHistoricalSemanticMarker(marker)
                for marker in row["semantic_markers"]
            ),
            uncertainty_count=row["uncertainty_count"],
            source_decision_id=boundaries[row["source_ref"]]["decision_id"],
            source_decision_sha256=boundaries[row["source_ref"]]["sha256"],
        )
        for row in phase2["classified_cells"]
    )
    row = phase2["blocked_conflicts"][0]
    boundary = boundaries[row["source_ref"]]
    conflict = PanchaPakshiHistoricalIdentityConflict(
        verse=row["verse"],
        candidate_ordinal=row["candidate_ordinal"],
        heading_activity=PanchaPakshiActivity(row["heading_activity"]),
        verse_activity=PanchaPakshiActivity(row["verse_activity"]),
        commentary_activity=PanchaPakshiActivity(row["commentary_activity"]),
        source_decision_id=boundary["decision_id"],
        source_decision_sha256=boundary["sha256"],
    )
    return PanchaPakshiUromarisiPhase2ClassificationCorpus(
        witness_id=phase2["governing_object"]["witness_id"],
        cells=cells,
        blocked_conflicts=(conflict,),
    )


def _relation_corpus() -> PanchaPakshiUromarisiPhase5RelationCorpus:
    phase5 = json.loads(_PHASE5_PATH.read_text(encoding="utf-8"))
    boundaries = phase5["source_decision_boundaries"]
    records = tuple(
        PanchaPakshiHistoricalRelationRecord(
            activity=PanchaPakshiActivity(row["activity"]),
            ordinal=row["ordinal"],
            verse=row["verse"],
            presence=PanchaPakshiHistoricalRelationPresence(row["presence"]),
            surface_kind=(
                PanchaPakshiHistoricalRelationSurfaceKind(row["surface_kind"])
                if row["surface_kind"] is not None
                else None
            ),
            confidence=PanchaPakshiHistoricalRelationConfidence(row["confidence"]),
            source_decision_id=boundaries[row["source_ref"]]["decision_id"],
            source_decision_sha256=boundaries[row["source_ref"]]["sha256"],
        )
        for row in phase5["relation_records"]
    )
    return PanchaPakshiUromarisiPhase5RelationCorpus(
        classification_corpus=_classification_corpus(), records=records
    )


def _network():
    policy = PanchaPakshiHistoricalClassificationPolicy(
        policy_id=PanchaPakshiHistoricalClassificationPolicyId.EXPLICIT_ACTIVITY_ORDINAL
    )
    conditions = pancha_pakshi_uromarisi_local_conditions_under_policy(
        _relation_corpus(), policy=policy
    )
    aggregate = pancha_pakshi_uromarisi_aggregate_intelligence(conditions)
    return pancha_pakshi_uromarisi_network(conditions, aggregate=aggregate)


def test_phase9_decision_is_hash_exact_and_chains_phase8() -> None:
    decision = _decision()
    assert _digest(_DECISION_PATH) == _DECISION_SHA256
    assert _digest(_PHASE8_PATH) == _PHASE8_SHA256
    assert _digest(_MANIFEST_PATH) == _MANIFEST_SHA256
    assert decision["prior_boundary"]["phase8_decision_sha256"] == _PHASE8_SHA256
    assert decision["constitutional_phase"] == 9
    assert decision["authorization"]["explicit_user_transition"] is True
    assert set(decision["admission_decision"].values()) == {False}


def test_network_projects_exact_nodes_candidates_and_no_edges() -> None:
    network = _network()
    contract = _decision()["network_contract"]

    assert len(network.nodes) == contract["node_count"]
    assert list(network.node_ids) == contract["node_ids"]
    assert len(network.relation_candidates) == contract["relation_candidate_count"]
    assert len(network.admitted_edges) == contract["admitted_edge_count"]
    assert len(network.scored_edges) == contract["scored_edge_count"]
    assert list(network.blocked_verses) == contract["blocked_verses"]
    assert network.metric_status.value == contract["metric_status"]
    assert network.topology_status == contract["topology_status"]
    assert all(candidate.endpoint_status == "not_established" for candidate in network.relation_candidates)
    assert all(candidate.direction_status == "not_established" for candidate in network.relation_candidates)


def test_network_lookups_preserve_absence_without_repairs() -> None:
    network = _network()
    first = network.node_for(PanchaPakshiActivity.EAT, 1)
    assert first is not None
    assert first.node_id == "eat:1:verse:230"
    assert network.candidate_for_node(first.node_id) is not None
    assert network.node_for(PanchaPakshiActivity.SLEEP, 5) is None
    assert network.candidate_for_node("sleep:2:verse:247") is None
    assert all(node.identity[2] != 250 for node in network.nodes)
    with pytest.raises(TypeError, match="activity"):
        network.node_for("eat", 1)
    with pytest.raises(ValueError, match="ordinal"):
        network.node_for(PanchaPakshiActivity.EAT, 0)
    with pytest.raises(ValueError, match="node_id"):
        network.candidate_for_node("")


def test_network_rejects_drift_inference_and_mutation() -> None:
    network = _network()
    candidate = network.relation_candidates[0]

    with pytest.raises(TypeError, match="condition_corpus"):
        pancha_pakshi_uromarisi_network(object(), aggregate=network.aggregate)
    with pytest.raises(TypeError, match="aggregate"):
        pancha_pakshi_uromarisi_network(network.condition_corpus, aggregate=object())
    with pytest.raises(ValueError, match="canonical"):
        replace(network, nodes=tuple(reversed(network.nodes)))
    with pytest.raises(ValueError, match="detected clause"):
        PanchaPakshiHistoricalRelationCandidate(
            owner_node_id=network.nodes[-1].node_id,
            relation=network.nodes[-1].profile.relation,
        )
    with pytest.raises(ValueError, match="owner"):
        replace(candidate, owner_node_id=network.nodes[1].node_id)
    with pytest.raises(ValueError, match="no admitted or scored"):
        replace(network, admitted_edges=(object(),))
    with pytest.raises(ValueError, match="blocked verses"):
        replace(network, blocked_verses=())
    with pytest.raises(FrozenInstanceError):
        network.admitted_edges = (object(),)
    assert network.metric_status is PanchaPakshiHistoricalNetworkMetricStatus.NOT_EVALUABLE


def test_phase9_remains_private_and_opens_only_phase10() -> None:
    decision = _decision()
    assert network_module.__all__ == ()
    for namespace in (moira, facade, pakshi, vedic, router_module):
        assert not hasattr(namespace, "PanchaPakshiUromarisiPhase9Network")
        assert not hasattr(namespace, "pancha_pakshi_uromarisi_network")
    assert decision["decision_id"] not in _MANIFEST_PATH.read_text(encoding="utf-8")
    closure = decision["phase9_closure"]
    assert closure["status"] == "complete_private_structural_network_boundary"
    assert closure["next_constitutional_phase"] == 10
    assert closure["next_phase_scope"] == "full_subsystem_hardening_only"
