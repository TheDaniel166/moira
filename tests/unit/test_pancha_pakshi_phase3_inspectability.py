"""Constitutional Phase 3 derived-only Pancha Pakshi inspectability."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

import moira
import moira._pancha_pakshi_classification as classification_module
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
from moira.pancha_pakshi import PanchaPakshiActivity
from moira_server.routers import pancha_pakshi as router_module


_ROOT = Path(__file__).resolve().parents[2]
_DECISION_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_uromarisi_phase3_inspectability_2026_07_21.json"
)
_PHASE2_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_uromarisi_phase2_classification_closure_2026_07_21.json"
)
_MANIFEST_PATH = _ROOT / "moira" / "data" / "pancha_pakshi_manifest.json"
_DECISION_SHA256 = (
    "2fd93585f8d2d439882ee77cdeb28e5509e916cd752357d60caaa003cc9fb2ca"
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


def _phase2() -> dict[str, object]:
    return json.loads(_PHASE2_PATH.read_text(encoding="utf-8"))


def _corpus() -> PanchaPakshiUromarisiPhase2ClassificationCorpus:
    phase2 = _phase2()
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


def test_phase3_decision_is_hash_exact_and_chains_phase2() -> None:
    decision = _decision()
    prior = decision["prior_boundary"]

    assert _digest(_DECISION_PATH) == _DECISION_SHA256
    assert _digest(_PHASE2_PATH) == _PHASE2_SHA256
    assert _digest(_MANIFEST_PATH) == _MANIFEST_SHA256
    assert prior["phase2_closure_sha256"] == _PHASE2_SHA256
    assert prior["manifest_sha256"] == _MANIFEST_SHA256
    assert decision["constitutional_phase"] == 3
    assert decision["admission_status"] == "research_only"
    assert set(decision["admission_decision"].values()) == {False}


def test_cell_inspectability_is_exactly_derived_from_stored_fields() -> None:
    corpus = _corpus()
    decision = _decision()
    expected = decision["verified_derived_views"]

    assert tuple(cell.identity for cell in corpus.cells) == tuple(
        (cell.activity, cell.ordinal) for cell in corpus.cells
    )
    assert all(
        cell.source_binding
        == (cell.source_decision_id, cell.source_decision_sha256)
        for cell in corpus.cells
    )
    assert all(
        cell.semantic_marker_names
        == tuple(sorted(marker.value for marker in cell.semantic_markers))
        for cell in corpus.cells
    )
    assert [cell.verse for cell in corpus.mortality_language_cells] == expected[
        "mortality_language_verses"
    ]
    assert [cell.verse for cell in corpus.unstated_time_cells] == expected[
        "unstated_time_verses"
    ]
    assert [cell.verse for cell in corpus.cells if cell.has_conditional_time] == expected[
        "conditional_time_verses"
    ]
    assert [
        cell.verse for cell in corpus.cells if cell.has_unreconciled_time_markers
    ] == expected["unreconciled_time_marker_verses"]


def test_conflict_inspectability_preserves_layers_and_lookup_absence() -> None:
    corpus = _corpus()
    conflict = corpus.blocked_conflicts[0]

    assert conflict.activity_by_layer == (
        ("heading", PanchaPakshiActivity.DIE),
        ("verse", PanchaPakshiActivity.DIE),
        ("commentary", PanchaPakshiActivity.SLEEP),
    )
    assert conflict.distinct_activities == frozenset(
        {PanchaPakshiActivity.DIE, PanchaPakshiActivity.SLEEP}
    )
    assert conflict.heading_and_verse_agree is True
    assert conflict.source_binding == next(
        cell.source_binding
        for cell in corpus.cells
        if cell.activity is PanchaPakshiActivity.SLEEP
    )
    assert corpus.classification_at(PanchaPakshiActivity.SLEEP, 5) is None
    assert corpus.classification_for_verse(250) is None
    assert corpus.conflict_for_verse(250) is conflict


def test_corpus_views_and_lookups_are_deterministic_and_typed() -> None:
    corpus = _corpus()
    expected = _decision()["verified_derived_views"]

    assert len(corpus.classified_verses) == expected["classified_verse_count"]
    assert corpus.blocked_verses == tuple(expected["blocked_verses"])
    assert dict((activity.value, count) for activity, count in corpus.activity_counts) == (
        expected["activity_counts"]
    )
    assert len(corpus.source_bindings) == expected["source_binding_count"]
    assert tuple(
        cell.verse for cell in corpus.cells_for_activity(PanchaPakshiActivity.RULE)
    ) == tuple(range(241, 246))
    assert corpus.classification_at(PanchaPakshiActivity.EAT, 1).verse == 230
    assert corpus.classification_for_verse(255).identity == (
        PanchaPakshiActivity.DIE,
        5,
    )
    assert corpus.conflict_for_verse(249) is None

    with pytest.raises(TypeError, match="activity must be"):
        corpus.cells_for_activity("rule")
    with pytest.raises(ValueError, match="ordinal must be"):
        corpus.classification_at(PanchaPakshiActivity.RULE, 0)
    with pytest.raises(ValueError, match="verse must be"):
        corpus.classification_for_verse(0)


def test_phase3_hardening_rejects_inconsistent_vessels_without_new_doctrine() -> None:
    corpus = _corpus()
    first = corpus.cells[0]

    with pytest.raises(TypeError, match="cells must be an immutable tuple"):
        replace(corpus, cells=list(corpus.cells))
    with pytest.raises(ValueError, match="activity verses do not match"):
        replace(corpus, cells=(replace(first, verse=999), *corpus.cells[1:]))
    with pytest.raises(ValueError, match="time class is not admitted"):
        replace(first, time_class=PanchaPakshiHistoricalTimeClass.NOT_STATED)
    with pytest.raises(ValueError, match="one activity must retain one source"):
        replace(
            corpus,
            cells=(
                replace(first, source_decision_sha256="0" * 64),
                *corpus.cells[1:],
            ),
        )
    with pytest.raises(ValueError, match="SLEEP-source binding"):
        replace(
            corpus,
            blocked_conflicts=(
                replace(
                    corpus.blocked_conflicts[0],
                    source_decision_sha256="0" * 64,
                ),
            ),
        )

    decision = _decision()
    assert decision["governing_object"]["new_source_semantics"] is False
    assert decision["governing_object"]["new_doctrine"] is False
    assert decision["phase3_closure"]["status"] == (
        "complete_at_private_research_boundary"
    )
    assert decision["phase3_closure"]["automatic_phase4_policy_selection"] is False
    assert decision["phase3_closure"]["automatic_public_admission"] is False
    assert classification_module.__all__ == ()

    phase12_governance_names = {
        "PanchaPakshiUromarisiConstitutionStatus",
        "pancha_pakshi_uromarisi_constitution_status",
    }
    for surface in (moira, pakshi, vedic, facade.Moira):
        assert not [
            name
            for name in dir(surface)
            if "uromarisi" in name.lower()
            and name not in phase12_governance_names
        ]
    assert {
        route.path
        for route in router_module.router.routes
        if "uromarisi" in route.path.lower()
    } == {"/v1/pancha-pakshi/constitution/uromarisi"}
