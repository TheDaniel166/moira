"""Constitutional Phase 5 Uromarisi relation formalization."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import FrozenInstanceError, replace
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
    "e8e189f75418cc96bc6930e2e93d2cfcebc849cb4080001ee4b4b07b158908d1"
)
_PHASE4_SHA256 = (
    "4a444c91bab9a4949664e6bca4e64ad0ee341b439019db831429e4548bd2c4f9"
)
_PHASE2_SHA256 = (
    "a5cd64696d4c040554f2c235056dfd28477fd0796fc82306f44ae43473d434e2"
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


def _relation_records() -> tuple[PanchaPakshiHistoricalRelationRecord, ...]:
    decision = _decision()
    boundaries = decision["source_decision_boundaries"]
    return tuple(
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
        for row in decision["relation_records"]
    )


def _relation_corpus() -> PanchaPakshiUromarisiPhase5RelationCorpus:
    return PanchaPakshiUromarisiPhase5RelationCorpus(
        classification_corpus=_classification_corpus(),
        records=_relation_records(),
    )


def test_phase5_decision_is_hash_exact_and_chains_closed_boundaries() -> None:
    decision = _decision()
    prior = decision["prior_boundary"]

    assert _digest(_DECISION_PATH) == _DECISION_SHA256
    assert _digest(_PHASE4_PATH) == _PHASE4_SHA256
    assert _digest(_PHASE2_PATH) == _PHASE2_SHA256
    assert _digest(_MANIFEST_PATH) == _MANIFEST_SHA256
    assert prior["phase4_decision_sha256"] == _PHASE4_SHA256
    assert prior["phase2_closure_sha256"] == _PHASE2_SHA256
    assert prior["manifest_sha256"] == _MANIFEST_SHA256
    assert decision["constitutional_phase"] == 5
    assert decision["admission_status"] == "research_only"
    assert set(decision["admission_decision"].values()) == {False}

    for boundary in decision["source_decision_boundaries"].values():
        assert _digest(_ROOT / boundary["path"]) == boundary["sha256"]


def test_relation_records_are_exact_phase1_and_phase2_projections() -> None:
    decision = _decision()
    phase2 = json.loads(_PHASE2_PATH.read_text(encoding="utf-8"))
    phase2_by_key = {
        (row["activity"], row["ordinal"], row["verse"]): row
        for row in phase2["classified_cells"]
    }

    for relation in decision["relation_records"]:
        key = (relation["activity"], relation["ordinal"], relation["verse"])
        classification = phase2_by_key[key]
        boundary = decision["source_decision_boundaries"][relation["source_ref"]]
        source = json.loads((_ROOT / boundary["path"]).read_text(encoding="utf-8"))
        atom = next(
            cell
            for cell in source[boundary["cell_key"]]
            if cell["ordinal"] == relation["ordinal"]
            and cell["verse"] == relation["verse"]
        )
        clause = atom[boundary["relation_key"]]

        assert (
            "activity_relation_clause" in classification["semantic_markers"]
        ) == (relation["presence"] == "present")
        assert relation["presence"] == clause["status"]
        if boundary["relation_key"] == "unresolved_relation_clause":
            assert clause["semantics"] is None
            assert relation["surface_kind"] == "unresolved_clause"
            assert relation["confidence"] == clause["confidence"]
        else:
            assert clause["runtime_semantics"] is None
            assert relation["surface_kind"] == clause["surface_statement"]
            assert relation["confidence"] == "not_stated"


def test_phase5_corpus_is_typed_complete_and_semantically_unbound() -> None:
    corpus = _relation_corpus()

    assert len(corpus.records) == 24
    assert Counter(record.presence for record in corpus.records) == Counter(
        {
            PanchaPakshiHistoricalRelationPresence.PRESENT: 17,
            PanchaPakshiHistoricalRelationPresence.NOT_RECORDED: 7,
        }
    )
    assert sum(
        record.surface_kind
        is PanchaPakshiHistoricalRelationSurfaceKind.UNRESOLVED_CLAUSE
        for record in corpus.records
    ) == 10
    assert sum(
        record.surface_kind not in {
            None,
            PanchaPakshiHistoricalRelationSurfaceKind.UNRESOLVED_CLAUSE,
        }
        for record in corpus.records
    ) == 7
    assert all(record.endpoint_status == "not_established" for record in corpus.records)
    assert all(record.direction_status == "not_established" for record in corpus.records)
    assert all(record.runtime_semantics_status == "not_admitted" for record in corpus.records)
    assert all(record.scoring_status == "not_performed" for record in corpus.records)
    assert all(record.admission_status == "research_only" for record in corpus.records)
    assert 250 not in {record.verse for record in corpus.records}


def test_phase5_vessels_reject_inference_drift_and_inconsistent_corpora() -> None:
    corpus = _relation_corpus()
    present = corpus.records[0]
    absent = next(
        record
        for record in corpus.records
        if record.presence is PanchaPakshiHistoricalRelationPresence.NOT_RECORDED
    )

    with pytest.raises(TypeError, match="activity"):
        replace(present, activity="eat")
    with pytest.raises(ValueError, match="surface kind"):
        replace(present, surface_kind=None)
    with pytest.raises(ValueError, match="high or medium"):
        replace(
            present,
            confidence=PanchaPakshiHistoricalRelationConfidence.NOT_STATED,
        )
    with pytest.raises(ValueError, match="cannot have a surface kind"):
        replace(
            absent,
            surface_kind=PanchaPakshiHistoricalRelationSurfaceKind.NO_ENMITY,
        )
    named = next(
        record
        for record in corpus.records
        if record.surface_kind is PanchaPakshiHistoricalRelationSurfaceKind.NO_ENMITY
    )
    with pytest.raises(ValueError, match="must not invent source confidence"):
        replace(named, confidence=PanchaPakshiHistoricalRelationConfidence.HIGH)
    with pytest.raises(FrozenInstanceError):
        present.presence = PanchaPakshiHistoricalRelationPresence.NOT_RECORDED

    with pytest.raises(ValueError, match="canonical order"):
        PanchaPakshiUromarisiPhase5RelationCorpus(
            classification_corpus=corpus.classification_corpus,
            records=tuple(reversed(corpus.records)),
        )
    with pytest.raises(ValueError, match="source bindings"):
        PanchaPakshiUromarisiPhase5RelationCorpus(
            classification_corpus=corpus.classification_corpus,
            records=(replace(present, source_decision_sha256="0" * 64),)
            + corpus.records[1:],
        )
    repaired_absence = replace(
        absent,
        presence=PanchaPakshiHistoricalRelationPresence.PRESENT,
        surface_kind=PanchaPakshiHistoricalRelationSurfaceKind.NO_ENMITY,
    )
    absent_index = corpus.records.index(absent)
    repaired_records = (
        corpus.records[:absent_index]
        + (repaired_absence,)
        + corpus.records[absent_index + 1 :]
    )
    with pytest.raises(ValueError, match="Phase 2 semantic marker"):
        PanchaPakshiUromarisiPhase5RelationCorpus(
            classification_corpus=corpus.classification_corpus,
            records=repaired_records,
        )


def test_phase5_remains_private_and_opens_only_phase6_hardening() -> None:
    decision = _decision()
    decision_id = decision["decision_id"]

    assert relations_module.__all__ == ()
    for namespace in (moira, facade, pakshi, vedic, router_module):
        assert not hasattr(namespace, "PanchaPakshiHistoricalRelationRecord")
        assert not hasattr(namespace, "PanchaPakshiUromarisiPhase5RelationCorpus")
    assert decision_id not in _MANIFEST_PATH.read_text(encoding="utf-8")
    assert decision["phase5_closure"] == {
        "status": "complete_private_research_boundary",
        "next_constitutional_phase": 6,
        "next_phase_scope": "relational_hardening_and_inspectability_only",
        "phase6_may_not_assume": [
            "resolved_unresolved_clause_meaning",
            "relation_endpoints_or_direction",
            "favorable_or_unfavorable_relation",
            "condition_or_numeric_score",
            "temporal_selector_or_runtime_binding",
            "verse250_identity_resolution",
        ],
    }
