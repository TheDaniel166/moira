"""Constitutional Phase 8 Uromarisi aggregate structural intelligence."""

from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

import moira
import moira._pancha_pakshi_aggregate as aggregate_module
import moira.facade as facade
import moira.pancha_pakshi as pakshi
import moira.vedic as vedic
from moira._pancha_pakshi_aggregate import (
    PanchaPakshiUromarisiPhase8AggregateIntelligence,
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
    PanchaPakshiHistoricalLocalConditionEvaluationStatus,
    pancha_pakshi_uromarisi_local_conditions_under_policy,
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
_DECISION_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_uromarisi_phase8_aggregate_intelligence_2026_07_21.json"
)
_PHASE7_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_uromarisi_phase7_local_condition_2026_07_21.json"
)
_PHASE6_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_uromarisi_phase6_relation_inspectability_2026_07_21.json"
)
_PHASE5_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_uromarisi_phase5_relations_2026_07_21.json"
)
_PHASE2_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_uromarisi_phase2_classification_closure_2026_07_21.json"
)
_MANIFEST_PATH = _ROOT / "moira" / "data" / "pancha_pakshi_manifest.json"
_DECISION_SHA256 = (
    "b193b3ba62d1c5eb57d526777310fa16f29c81fa999e69b813670c680ba2fd13"
)
_PHASE7_SHA256 = (
    "401c90b7d7c15663427e034a527f983054800f948019cf12b404a0086b3203be"
)
_PHASE6_SHA256 = (
    "b175bcd1e537fb551cd26b18d6e6caa37f7a574b7e0a96b336d6fbb97eff9b12"
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
        classification_corpus=_classification_corpus(),
        records=records,
    )


def _condition_corpus():
    policy = PanchaPakshiHistoricalClassificationPolicy(
        policy_id=(
            PanchaPakshiHistoricalClassificationPolicyId.EXPLICIT_ACTIVITY_ORDINAL
        )
    )
    return pancha_pakshi_uromarisi_local_conditions_under_policy(
        _relation_corpus(), policy=policy
    )


def _aggregate() -> PanchaPakshiUromarisiPhase8AggregateIntelligence:
    return pancha_pakshi_uromarisi_aggregate_intelligence(_condition_corpus())


def test_phase8_decision_is_hash_exact_and_chains_phase7() -> None:
    decision = _decision()
    prior = decision["prior_boundary"]

    assert _digest(_DECISION_PATH) == _DECISION_SHA256
    assert _digest(_PHASE7_PATH) == _PHASE7_SHA256
    assert _digest(_PHASE6_PATH) == _PHASE6_SHA256
    assert _digest(_MANIFEST_PATH) == _MANIFEST_SHA256
    assert prior["phase7_decision_sha256"] == _PHASE7_SHA256
    assert prior["phase6_decision_sha256"] == _PHASE6_SHA256
    assert prior["manifest_sha256"] == _MANIFEST_SHA256
    assert decision["constitutional_phase"] == 8
    assert decision["admission_status"] == "research_only"
    assert set(decision["admission_decision"].values()) == {False}


def test_aggregate_matches_the_exact_phase7_structural_counts() -> None:
    aggregate = _aggregate()
    contract = _decision()["aggregate_contract"]

    assert aggregate.policy_id.value == contract["policy_id"]
    assert aggregate.profile_count == contract["profile_count"]
    assert [
        [activity.value, count] for activity, count in aggregate.activity_counts
    ] == contract["activity_counts"]
    assert [
        [status.value, count]
        for status, count in aggregate.evaluation_status_counts
    ] == contract["evaluation_status_counts"]
    for field_name in (
        "relation_detected_count",
        "relation_not_recorded_count",
        "relation_unresolved_count",
        "relation_named_surface_count",
        "relation_admitted_count",
        "relation_scored_count",
    ):
        assert getattr(aggregate, field_name) == contract[field_name]
    assert list(aggregate.blocked_verses) == contract["blocked_verses"]
    assert aggregate.aggregation_status == contract["aggregation_status"]
    assert aggregate.ranking_status == contract["ranking_status"]
    assert aggregate.weighting_status == contract["weighting_status"]
    assert aggregate.favorability_status == contract["favorability_status"]
    assert aggregate.condition_score is contract["condition_score"]
    assert aggregate.prognosis_status == contract["prognosis_status"]
    assert aggregate.admission_status == contract["admission_status"]


def test_aggregate_is_repeatable_immutable_and_contains_no_judgment() -> None:
    first = _aggregate()
    second = _aggregate()

    assert first == second
    assert first.activity_counts == (
        (PanchaPakshiActivity.EAT, 5),
        (PanchaPakshiActivity.WALK, 5),
        (PanchaPakshiActivity.RULE, 5),
        (PanchaPakshiActivity.SLEEP, 4),
        (PanchaPakshiActivity.DIE, 5),
    )
    assert first.evaluation_status_counts == (
        (
            PanchaPakshiHistoricalLocalConditionEvaluationStatus.NOT_EVALUABLE,
            24,
        ),
    )
    assert first.relation_admitted_count == 0
    assert first.relation_scored_count == 0
    with pytest.raises(FrozenInstanceError):
        first.condition_score = 1


def test_phase8_vessel_rejects_inconsistent_or_evaluative_aggregates() -> None:
    aggregate = _aggregate()

    with pytest.raises(TypeError, match="condition_corpus"):
        pancha_pakshi_uromarisi_aggregate_intelligence(object())
    with pytest.raises(ValueError, match="profile_count"):
        replace(aggregate, profile_count=23)
    with pytest.raises(ValueError, match="canonical activity order"):
        replace(aggregate, activity_counts=tuple(reversed(aggregate.activity_counts)))
    with pytest.raises(ValueError, match="not evaluable"):
        replace(aggregate, evaluation_status_counts=())
    with pytest.raises(ValueError, match="cover all profiles"):
        replace(aggregate, relation_detected_count=16)
    with pytest.raises(ValueError, match="cover detected relations"):
        replace(aggregate, relation_unresolved_count=9)
    with pytest.raises(ValueError, match="no admitted or scored"):
        replace(aggregate, relation_admitted_count=1)
    with pytest.raises(ValueError, match="blocked verse 250"):
        replace(aggregate, blocked_verses=())


def test_phase8_closes_the_private_eight_phase_sequence_without_public_admission() -> None:
    decision = _decision()
    closure = decision["eight_phase_closure"]

    assert aggregate_module.__all__ == ()
    for namespace in (moira, facade, pakshi, vedic, router_module):
        assert not hasattr(
            namespace, "PanchaPakshiUromarisiPhase8AggregateIntelligence"
        )
    assert decision["decision_id"] not in _MANIFEST_PATH.read_text(encoding="utf-8")
    assert closure["status"] == "complete_private_research_sequence"
    assert closure["completed_phases"] == list(range(1, 9))
    assert closure["next_phase"] is None
    assert closure["automatic_phase9_transition"] is False
    assert closure["admission_review_status"] == "not_started"
    assert closure["public_exposure_status"] == "not_authorized"
