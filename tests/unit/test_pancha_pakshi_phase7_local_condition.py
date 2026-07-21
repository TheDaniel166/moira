"""Constitutional Phase 7 Uromarisi integrated local condition."""

from __future__ import annotations

import hashlib
import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

import moira
import moira._pancha_pakshi_condition as condition_module
import moira.facade as facade
import moira.pancha_pakshi as pakshi
import moira.vedic as vedic
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
    PanchaPakshiHistoricalLocalConditionProfile,
    PanchaPakshiUromarisiPhase7LocalConditionCorpus,
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
_PHASE4_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_uromarisi_phase4_policy_2026_07_21.json"
)
_PHASE2_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_uromarisi_phase2_classification_closure_2026_07_21.json"
)
_MANIFEST_PATH = _ROOT / "moira" / "data" / "pancha_pakshi_manifest.json"
_DECISION_SHA256 = (
    "401c90b7d7c15663427e034a527f983054800f948019cf12b404a0086b3203be"
)
_PHASE6_SHA256 = (
    "b175bcd1e537fb551cd26b18d6e6caa37f7a574b7e0a96b336d6fbb97eff9b12"
)
_PHASE5_SHA256 = (
    "e8e189f75418cc96bc6930e2e93d2cfcebc849cb4080001ee4b4b07b158908d1"
)
_PHASE4_SHA256 = (
    "4a444c91bab9a4949664e6bca4e64ad0ee341b439019db831429e4548bd2c4f9"
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


def _policy() -> PanchaPakshiHistoricalClassificationPolicy:
    return PanchaPakshiHistoricalClassificationPolicy(
        policy_id=(
            PanchaPakshiHistoricalClassificationPolicyId.EXPLICIT_ACTIVITY_ORDINAL
        )
    )


def _condition_corpus() -> PanchaPakshiUromarisiPhase7LocalConditionCorpus:
    return pancha_pakshi_uromarisi_local_conditions_under_policy(
        _relation_corpus(), policy=_policy()
    )


def test_phase7_decision_is_hash_exact_and_chains_phase6() -> None:
    decision = _decision()
    prior = decision["prior_boundary"]

    assert _digest(_DECISION_PATH) == _DECISION_SHA256
    assert _digest(_PHASE6_PATH) == _PHASE6_SHA256
    assert _digest(_PHASE5_PATH) == _PHASE5_SHA256
    assert _digest(_PHASE4_PATH) == _PHASE4_SHA256
    assert _digest(_MANIFEST_PATH) == _MANIFEST_SHA256
    assert prior["phase6_decision_sha256"] == _PHASE6_SHA256
    assert prior["phase5_decision_sha256"] == _PHASE5_SHA256
    assert prior["phase4_decision_sha256"] == _PHASE4_SHA256
    assert prior["manifest_sha256"] == _MANIFEST_SHA256
    assert decision["constitutional_phase"] == 7
    assert decision["admission_status"] == "research_only"
    assert set(decision["admission_decision"].values()) == {False}


def test_all_profiles_integrate_exact_classification_relation_and_policy() -> None:
    corpus = _condition_corpus()

    assert len(corpus.profiles) == 24
    for profile, classification, relation in zip(
        corpus.profiles,
        corpus.relation_corpus.classification_corpus.cells,
        corpus.relation_corpus.records,
        strict=True,
    ):
        assert profile.classification is classification
        assert profile.relation is relation
        assert profile.policy is corpus.policy
        assert profile.identity == (
            classification.activity,
            classification.ordinal,
            classification.verse,
        )
        assert profile.source_binding == classification.source_binding
        assert profile.evaluation_status is (
            PanchaPakshiHistoricalLocalConditionEvaluationStatus.NOT_EVALUABLE
        )
        assert profile.favorability_status == "not_assigned"
        assert profile.condition_score is None
        assert profile.prognosis_status == "not_performed"
        assert profile.medical_use_status == "forbidden"
        assert profile.admission_status == "research_only"
        assert profile.relation_is_detected is relation.is_detected
        assert profile.relation_is_admitted is False
        assert profile.relation_is_scored is False


def test_condition_lookups_preserve_exact_identity_absence_and_conflict() -> None:
    corpus = _condition_corpus()

    for lookup in _decision()["lookup_contract"]:
        if lookup["lookup"] == "condition_at":
            result = corpus.condition_at(
                PanchaPakshiActivity(lookup["activity"]), lookup["ordinal"]
            )
        else:
            result = corpus.condition_for_verse(lookup["verse"])
        if lookup.get("expected_result", object()) is None:
            assert result is None
            continue
        assert result is not None
        assert result.classification.verse == lookup["expected_verse"]
        assert result.relation_is_detected is lookup["expected_relation_detected"]
        assert result.evaluation_status.value == lookup["expected_evaluation_status"]

    with pytest.raises(TypeError, match="activity"):
        corpus.condition_at("eat", 1)
    for invalid_ordinal in (True, 0, 6):
        with pytest.raises(ValueError, match="ordinal"):
            corpus.condition_at(PanchaPakshiActivity.EAT, invalid_ordinal)
    for invalid_verse in (True, 0, -1):
        with pytest.raises(ValueError, match="verse"):
            corpus.condition_for_verse(invalid_verse)


def test_phase7_vessels_reject_cross_layer_drift_and_evaluation_invention() -> None:
    relation_corpus = _relation_corpus()
    policy = _policy()
    classification = relation_corpus.classification_corpus.cells[0]
    relation = relation_corpus.records[0]

    with pytest.raises(TypeError, match="relation_corpus"):
        pancha_pakshi_uromarisi_local_conditions_under_policy(
            object(), policy=policy
        )
    with pytest.raises(TypeError, match="policy"):
        pancha_pakshi_uromarisi_local_conditions_under_policy(
            relation_corpus, policy="explicit"
        )
    with pytest.raises(ValueError, match="identities"):
        PanchaPakshiHistoricalLocalConditionProfile(
            classification=classification,
            relation=relation_corpus.records[1],
            policy=policy,
        )
    with pytest.raises(ValueError, match="source bindings"):
        PanchaPakshiHistoricalLocalConditionProfile(
            classification=classification,
            relation=replace(relation, source_decision_sha256="0" * 64),
            policy=policy,
        )

    admitted_relation = replace(relation)
    object.__setattr__(admitted_relation, "runtime_semantics_status", "admitted")
    with pytest.raises(ValueError, match="no admitted relation"):
        PanchaPakshiHistoricalLocalConditionProfile(
            classification=classification,
            relation=admitted_relation,
            policy=policy,
        )
    scored_relation = replace(relation)
    object.__setattr__(scored_relation, "scoring_status", "performed")
    with pytest.raises(ValueError, match="no scored relation"):
        PanchaPakshiHistoricalLocalConditionProfile(
            classification=classification,
            relation=scored_relation,
            policy=policy,
        )

    corpus = _condition_corpus()
    with pytest.raises(TypeError, match="must contain"):
        replace(corpus, profiles=(object(),) + corpus.profiles[1:])
    with pytest.raises(ValueError, match="canonical classifications"):
        replace(corpus, profiles=tuple(reversed(corpus.profiles)))
    with pytest.raises(FrozenInstanceError):
        corpus.profiles[0].condition_score = 1


def test_phase7_remains_private_and_opens_only_phase8_aggregation() -> None:
    decision = _decision()

    assert condition_module.__all__ == ()
    for namespace in (moira, facade, pakshi, vedic, router_module):
        assert not hasattr(namespace, "PanchaPakshiHistoricalLocalConditionProfile")
        assert not hasattr(
            namespace, "PanchaPakshiUromarisiPhase7LocalConditionCorpus"
        )
    assert decision["decision_id"] not in _MANIFEST_PATH.read_text(encoding="utf-8")
    assert decision["phase7_closure"]["status"] == (
        "complete_private_research_boundary"
    )
    assert decision["phase7_closure"]["next_constitutional_phase"] == 8
    assert decision["phase7_closure"]["next_phase_scope"] == (
        "aggregate_structural_intelligence_only"
    )
