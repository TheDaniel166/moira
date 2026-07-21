"""Constitutional Phase 2 classification closure for Uromarisi research."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
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
_CLOSURE_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_uromarisi_phase2_classification_closure_2026_07_21.json"
)
_CLOSURE_SHA256 = (
    "a5cd64696d4c040554f2c235056dfd28477fd0796fc82306f44ae43473d434e2"
)


def _digest(path: Path) -> str:
    text = path.read_bytes().decode("utf-8")
    canonical = text.replace("\r\n", "\n").replace("\r", "\n")
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _closure() -> dict[str, object]:
    return json.loads(_CLOSURE_PATH.read_text(encoding="utf-8"))


def _source_documents(
    closure: dict[str, object],
) -> dict[str, tuple[dict[str, object], dict[str, object]]]:
    result = {}
    for source_ref, boundary in closure["prior_truth_boundaries"].items():
        if not source_ref.startswith("stage"):
            continue
        path = _ROOT / boundary["path"]
        document = json.loads(path.read_text(encoding="utf-8"))
        result[source_ref] = (boundary, document)
    return result


def _source_cell(
    row: dict[str, object],
    sources: dict[str, tuple[dict[str, object], dict[str, object]]],
) -> tuple[dict[str, object], dict[str, object]]:
    boundary, document = sources[row["source_ref"]]
    matches = [
        cell
        for cell in document[boundary["cell_key"]]
        if cell["verse"] == row["verse"]
    ]
    assert len(matches) == 1
    return boundary, matches[0]


def _present(value: dict[str, object] | None) -> bool:
    return bool(value and value.get("status") == "present")


def _derived_disposition(
    activity: PanchaPakshiActivity, cell: dict[str, object]
) -> str:
    if activity is PanchaPakshiActivity.EAT:
        return cell["resolution_statement"]
    if activity is PanchaPakshiActivity.DIE:
        return cell["mortality_statement"]["form"]
    return cell["disposition_statement"]["value"]


def _derived_time_class(
    activity: PanchaPakshiActivity, cell: dict[str, object]
) -> str:
    if activity is PanchaPakshiActivity.EAT:
        source_kind = cell["stated_duration_days"]["kind"]
        return {
            "finite_alternative": "finite_alternative_days",
            "exact": "exact_days",
        }[source_kind]
    return cell["stated_time_expression"]["kind"]


def _derived_markers(
    activity: PanchaPakshiActivity, cell: dict[str, object]
) -> frozenset[str]:
    markers: set[str] = set()

    if activity is PanchaPakshiActivity.EAT:
        if cell["prescribed_response"]:
            markers.add("prescribed_response")
        if _present(cell["medicine_reference"]):
            markers.add("treatment_or_mediation_reference")
        if _present(cell["prithivi_reference"]):
            markers.add("elemental_or_dosha_reference")
        if _present(cell["unresolved_relation_clause"]):
            markers.add("activity_relation_clause")

    elif activity is PanchaPakshiActivity.WALK:
        if any(
            response["relation"] == "prescribed"
            for response in cell["response_or_mediation"]
        ):
            markers.add("prescribed_response")
        if _present(cell["medicine_or_physician_reference"]):
            markers.add("treatment_or_mediation_reference")
        if _present(cell["water_reference"]) or _present(
            cell["navagraha_dosha_reference"]
        ):
            markers.add("elemental_or_dosha_reference")
        if cell["deity_reference"]:
            markers.add("deity_or_fate_reference")
        if _present(cell["unresolved_relation_clause"]):
            markers.add("activity_relation_clause")

    elif activity is PanchaPakshiActivity.RULE:
        if cell["response_or_mediation"]:
            markers.add("prescribed_response")
        if _present(cell["fire_reference"]) or _present(
            cell["saturn_dosha_reference"]
        ):
            markers.add("elemental_or_dosha_reference")
        if cell["deity_reference"]:
            markers.add("deity_or_fate_reference")
        if cell["effect_reference"]:
            markers.add("effect_reference")
        if _present(cell["activity_relation_clause"]):
            markers.add("activity_relation_clause")

    elif activity is PanchaPakshiActivity.SLEEP:
        if cell["response_or_mediation"]:
            markers.add("prescribed_response")
        if any(
            response["category"] == "physician_medicine"
            for response in cell["response_or_mediation"]
        ):
            markers.add("treatment_or_mediation_reference")
        if _present(cell["wind_dosha_reference"]):
            markers.add("elemental_or_dosha_reference")
        if cell["deity_reference"]:
            markers.add("deity_or_fate_reference")
        if cell["effect_reference"]:
            markers.add("effect_reference")
        if _present(cell["activity_relation_clause"]):
            markers.add("activity_relation_clause")
        if _present(cell["conditional_mortality_reference"]):
            markers.add("mortality_language")

    elif activity is PanchaPakshiActivity.DIE:
        if cell["space_or_void_reference"]:
            markers.add("elemental_or_dosha_reference")
        if cell["deity_or_fate_reference"]:
            markers.add("deity_or_fate_reference")
        if cell["effect_reference"]:
            markers.add("effect_reference")
        if _present(cell["activity_relation_clause"]):
            markers.add("activity_relation_clause")
        if _present(cell["mortality_statement"]):
            markers.add("mortality_language")
        if cell["source_branch_reference"]:
            markers.add("source_branch_reference")

    return frozenset(markers)


def _classification_from_row(
    row: dict[str, object],
    sources: dict[str, tuple[dict[str, object], dict[str, object]]],
) -> PanchaPakshiHistoricalCellClassification:
    boundary, cell = _source_cell(row, sources)
    activity = PanchaPakshiActivity(row["activity"])

    assert row["disposition"] == _derived_disposition(activity, cell)
    assert row["time_class"] == _derived_time_class(activity, cell)
    assert frozenset(row["semantic_markers"]) == _derived_markers(activity, cell)
    assert row["uncertainty_count"] == len(cell["uncertainty"])

    return PanchaPakshiHistoricalCellClassification(
        activity=activity,
        ordinal=row["ordinal"],
        verse=row["verse"],
        disposition=PanchaPakshiHistoricalDisposition(row["disposition"]),
        time_class=PanchaPakshiHistoricalTimeClass(row["time_class"]),
        semantic_markers=frozenset(
            PanchaPakshiHistoricalSemanticMarker(marker)
            for marker in row["semantic_markers"]
        ),
        uncertainty_count=row["uncertainty_count"],
        source_decision_id=boundary["decision_id"],
        source_decision_sha256=boundary["sha256"],
    )


def _corpus() -> PanchaPakshiUromarisiPhase2ClassificationCorpus:
    closure = _closure()
    sources = _source_documents(closure)
    cells = tuple(
        _classification_from_row(row, sources)
        for row in closure["classified_cells"]
    )
    row = closure["blocked_conflicts"][0]
    boundary = closure["prior_truth_boundaries"][row["source_ref"]]
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
        witness_id=closure["governing_object"]["witness_id"],
        cells=cells,
        blocked_conflicts=(conflict,),
    )


def test_phase2_closure_is_hash_exact_and_chains_all_truth_boundaries() -> None:
    closure = _closure()

    assert _digest(_CLOSURE_PATH) == _CLOSURE_SHA256
    for source_ref, boundary in closure["prior_truth_boundaries"].items():
        if source_ref.startswith("stage"):
            assert _digest(_ROOT / boundary["path"]) == boundary["sha256"]
    manifest_path = _ROOT / closure["prior_truth_boundaries"]["manifest_path"]
    assert _digest(manifest_path) == closure["prior_truth_boundaries"][
        "manifest_sha256"
    ]
    assert closure["constitutional_phase"] == 2
    assert closure["admission_status"] == "research_only"
    assert set(closure["admission_decision"].values()) == {False}


def test_all_24_classifications_are_exact_phase1_truth_projections() -> None:
    closure = _closure()
    corpus = _corpus()

    assert len(corpus.cells) == 24
    assert Counter(cell.activity for cell in corpus.cells) == Counter(
        {
            PanchaPakshiActivity.EAT: 5,
            PanchaPakshiActivity.WALK: 5,
            PanchaPakshiActivity.RULE: 5,
            PanchaPakshiActivity.SLEEP: 4,
            PanchaPakshiActivity.DIE: 5,
        }
    )
    assert sum(
        PanchaPakshiHistoricalSemanticMarker.MORTALITY_LANGUAGE
        in cell.semantic_markers
        for cell in corpus.cells
    ) == 6
    assert closure["classification_derivation"]["inference_beyond_preserved_truth"] == (
        "forbidden"
    )


def test_verse_250_is_unclassifiable_and_has_no_payload() -> None:
    closure = _closure()
    corpus = _corpus()
    row = closure["blocked_conflicts"][0]

    assert row["classification_status"] == (
        "unclassifiable_text_layer_identity_conflict"
    )
    assert row["classification_payload"] is None
    assert all(cell.verse != 250 for cell in corpus.cells)
    assert corpus.blocked_conflicts[0].verse == 250
    assert corpus.blocked_conflicts[0].heading_activity is PanchaPakshiActivity.DIE
    assert corpus.blocked_conflicts[0].verse_activity is PanchaPakshiActivity.DIE
    assert corpus.blocked_conflicts[0].commentary_activity is (
        PanchaPakshiActivity.SLEEP
    )


def test_phase2_vessels_reject_inconsistent_or_lossy_construction() -> None:
    corpus = _corpus()
    first = corpus.cells[0]
    die = next(cell for cell in corpus.cells if cell.activity is PanchaPakshiActivity.DIE)

    with pytest.raises(ValueError, match="not admitted for the activity"):
        replace(
            first,
            disposition=(
                PanchaPakshiHistoricalDisposition.LIFE_DEPARTURE_AND_NO_RETURN_LANGUAGE
            ),
            semantic_markers=(
                first.semantic_markers
                | {PanchaPakshiHistoricalSemanticMarker.MORTALITY_LANGUAGE}
            ),
        )
    with pytest.raises(ValueError, match="mortality marker must agree"):
        replace(
            die,
            semantic_markers=(
                die.semantic_markers
                - {PanchaPakshiHistoricalSemanticMarker.MORTALITY_LANGUAGE}
            ),
        )
    with pytest.raises(ValueError, match="retain uncertainty"):
        replace(first, uncertainty_count=0)
    with pytest.raises(ValueError, match="24 classified cells"):
        replace(corpus, cells=corpus.cells[:-1])
    with pytest.raises(ValueError, match="disagreeing text-layer activities"):
        replace(
            corpus.blocked_conflicts[0],
            commentary_activity=PanchaPakshiActivity.DIE,
        )


def test_phase2_closure_opens_only_private_phase3_inspectability() -> None:
    closure = _closure()
    phase2 = closure["phase2_closure"]
    invariants = closure["classification_invariants"]

    assert phase2["status"] == "complete_at_research_boundary"
    assert phase2["phase3_entry_status"] == "ready_for_private_inspectability_only"
    assert phase2["phase3_permitted_scope"] == [
        "derived_convenience_views_over_existing_classification_fields",
        "vessel_consistency_and_malformed_construction_hardening",
        "no_new_doctrine_or_interpretation",
    ]
    assert phase2["automatic_public_admission"] is False
    assert invariants["generic_good_bad_labels"] == "forbidden"
    assert invariants["numeric_condition_or_score"] == "forbidden"
    assert invariants["prediction_prognosis_diagnosis_or_advice"] == "forbidden"
    assert invariants["temporal_selector_binding"] == "forbidden_in_phase2"
    assert "human_tamil_review" in phase2["phase3_nonrequirements"]
    assert classification_module.__all__ == ()

    phase12_governance_names = {
        "PanchaPakshiUromarisiConstitutionStatus",
        "pancha_pakshi_uromarisi_constitution_status",
    }
    for surface in (moira, pakshi, vedic, facade.Moira):
        assert not [
            name
            for name in dir(surface)
            if "historicalcell" in name.lower()
            or "historical_cell" in name.lower()
            or (
                "uromarisi" in name.lower()
                and name not in phase12_governance_names
            )
        ]
    assert {
        route.path
        for route in router_module.router.routes
        if "uromarisi" in route.path.lower()
    } == {"/v1/pancha-pakshi/constitution/uromarisi"}
