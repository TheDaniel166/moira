"""Constitutional Phase 6 Uromarisi relation hardening and inspectability."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

import moira
import moira._pancha_pakshi_relations as relations_module
import moira.facade as facade
import moira.pancha_pakshi as pakshi
import moira.vedic as vedic
from moira._pancha_pakshi_classification import (
    PanchaPakshiHistoricalCellClassification,
    PanchaPakshiHistoricalDisposition,
    PanchaPakshiHistoricalIdentityConflict,
    PanchaPakshiHistoricalSemanticMarker,
    PanchaPakshiHistoricalTimeClass,
    PanchaPakshiUromarisiPhase2ClassificationCorpus,
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


def test_phase6_decision_is_hash_exact_and_chains_phase5() -> None:
    decision = _decision()
    prior = decision["prior_boundary"]

    assert _digest(_DECISION_PATH) == _DECISION_SHA256
    assert _digest(_PHASE5_PATH) == _PHASE5_SHA256
    assert _digest(_PHASE4_PATH) == _PHASE4_SHA256
    assert _digest(_MANIFEST_PATH) == _MANIFEST_SHA256
    assert prior["phase5_decision_sha256"] == _PHASE5_SHA256
    assert prior["phase4_decision_sha256"] == _PHASE4_SHA256
    assert prior["manifest_sha256"] == _MANIFEST_SHA256
    assert decision["constitutional_phase"] == 6
    assert decision["admission_status"] == "research_only"
    assert set(decision["admission_decision"].values()) == {False}


def test_record_inspectability_is_derived_without_semantic_admission() -> None:
    corpus = _relation_corpus()

    for record in corpus.records:
        assert record.identity == (record.activity, record.ordinal, record.verse)
        assert record.is_detected == (
            record.presence is PanchaPakshiHistoricalRelationPresence.PRESENT
        )
        assert record.is_admitted is False
        assert record.is_scored is False
        assert record.has_unresolved_clause == (
            record.surface_kind
            is PanchaPakshiHistoricalRelationSurfaceKind.UNRESOLVED_CLAUSE
        )
        assert record.has_named_surface_category == (
            record.surface_kind
            not in {
                None,
                PanchaPakshiHistoricalRelationSurfaceKind.UNRESOLVED_CLAUSE,
            }
        )


def test_corpus_views_keep_detected_admitted_and_scored_subsets_distinct() -> None:
    corpus = _relation_corpus()

    assert corpus.record_identities == tuple(
        (cell.activity, cell.ordinal, cell.verse)
        for cell in corpus.classification_corpus.cells
    )
    assert corpus.source_bindings == corpus.classification_corpus.source_bindings
    assert corpus.presence_counts == (
        (PanchaPakshiHistoricalRelationPresence.PRESENT, 17),
        (PanchaPakshiHistoricalRelationPresence.NOT_RECORDED, 7),
    )
    assert len(corpus.detected_records) == 17
    assert len(corpus.not_recorded_records) == 7
    assert len(corpus.unresolved_records) == 10
    assert len(corpus.named_surface_records) == 7
    assert corpus.admitted_records == ()
    assert corpus.scored_records == ()
    assert set(corpus.detected_records).isdisjoint(corpus.not_recorded_records)
    assert all(record.is_detected for record in corpus.detected_records)
    assert all(not record.is_detected for record in corpus.not_recorded_records)

    assert tuple(
        len(corpus.records_for_activity(activity))
        for activity in PanchaPakshiActivity
    ) == (5, 5, 5, 4, 5)


def test_exact_lookups_preserve_absence_and_conflict_without_fallback() -> None:
    corpus = _relation_corpus()

    for lookup in _decision()["lookup_contract"]:
        if lookup["lookup"] == "relation_at":
            result = corpus.relation_at(
                PanchaPakshiActivity(lookup["activity"]), lookup["ordinal"]
            )
        else:
            result = corpus.relation_for_verse(lookup["verse"])
        if lookup.get("expected_result", object()) is None:
            assert result is None
            continue
        assert result is not None
        assert result.verse == lookup["expected_verse"]
        assert result.presence.value == lookup["expected_presence"]
        assert (
            result.surface_kind.value if result.surface_kind is not None else None
        ) == lookup["expected_surface_kind"]

    with pytest.raises(TypeError, match="activity"):
        corpus.records_for_activity("eat")
    with pytest.raises(TypeError, match="activity"):
        corpus.relation_at("eat", 1)
    for invalid_ordinal in (True, 0, 6):
        with pytest.raises(ValueError, match="ordinal"):
            corpus.relation_at(PanchaPakshiActivity.EAT, invalid_ordinal)
    for invalid_verse in (True, 0, -1):
        with pytest.raises(ValueError, match="verse"):
            corpus.relation_for_verse(invalid_verse)


def test_phase6_hardening_is_private_and_opens_only_phase7_condition_work() -> None:
    corpus = _relation_corpus()
    decision = _decision()

    with pytest.raises(TypeError, match="must contain"):
        replace(corpus, records=(object(),) + corpus.records[1:])

    assert relations_module.__all__ == ()
    for namespace in (moira, facade, pakshi, vedic, router_module):
        assert not hasattr(namespace, "PanchaPakshiHistoricalRelationRecord")
        assert not hasattr(namespace, "PanchaPakshiUromarisiPhase5RelationCorpus")
    assert decision["decision_id"] not in _MANIFEST_PATH.read_text(encoding="utf-8")
    assert decision["phase6_closure"]["status"] == (
        "complete_private_research_boundary"
    )
    assert decision["phase6_closure"]["next_constitutional_phase"] == 7
    assert decision["phase6_closure"]["next_phase_scope"] == (
        "integrated_local_condition_only"
    )
