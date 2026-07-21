"""Constitutional Phase 4 explicit Uromarisi research policy."""

from __future__ import annotations

import hashlib
import inspect
import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

import moira
import moira._pancha_pakshi_classification as classification_module
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
    pancha_pakshi_uromarisi_classification_under_policy,
)
from moira.pancha_pakshi import (
    PanchaPakshiActivity,
    PanchaPakshiSookshmaSelectorPolicyId,
)
from moira_server.routers import pancha_pakshi as router_module


_ROOT = Path(__file__).resolve().parents[2]
_DECISION_PATH = (
    _ROOT
    / "tests"
    / "fixtures"
    / "pancha_pakshi_uromarisi_phase4_policy_2026_07_21.json"
)
_PHASE3_PATH = (
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
    "4a444c91bab9a4949664e6bca4e64ad0ee341b439019db831429e4548bd2c4f9"
)
_PHASE3_SHA256 = (
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


def _corpus() -> PanchaPakshiUromarisiPhase2ClassificationCorpus:
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


def _policy() -> PanchaPakshiHistoricalClassificationPolicy:
    return PanchaPakshiHistoricalClassificationPolicy(
        policy_id=(
            PanchaPakshiHistoricalClassificationPolicyId.EXPLICIT_ACTIVITY_ORDINAL
        )
    )


def test_phase4_decision_is_hash_exact_and_chains_prior_boundaries() -> None:
    decision = _decision()
    prior = decision["prior_boundary"]

    assert _digest(_DECISION_PATH) == _DECISION_SHA256
    assert _digest(_PHASE3_PATH) == _PHASE3_SHA256
    assert _digest(_PHASE2_PATH) == _PHASE2_SHA256
    assert _digest(_MANIFEST_PATH) == _MANIFEST_SHA256
    assert prior["phase3_decision_sha256"] == _PHASE3_SHA256
    assert prior["phase2_closure_sha256"] == _PHASE2_SHA256
    assert prior["manifest_sha256"] == _MANIFEST_SHA256
    assert decision["constitutional_phase"] == 4
    assert decision["admission_status"] == "research_only"
    assert set(decision["admission_decision"].values()) == {False}


def test_policy_vessel_is_explicit_typed_immutable_and_has_no_default() -> None:
    policy = _policy()
    contract = _decision()["admitted_private_policy"]

    assert policy.policy_id.value == contract["policy_id"]
    for field_name in (
        "derivation_status",
        "activity_input_status",
        "ordinal_input_status",
        "temporal_selector_binding_status",
        "stage2k_selector_composition_status",
        "outcome_interpretation_status",
        "medical_use_status",
        "admission_status",
    ):
        assert getattr(policy, field_name) == contract[field_name]

    signature = inspect.signature(
        pancha_pakshi_uromarisi_classification_under_policy
    )
    assert signature.parameters["policy"].default is inspect.Parameter.empty
    assert signature.parameters["activity"].default is inspect.Parameter.empty
    assert signature.parameters["ordinal"].default is inspect.Parameter.empty
    assert contract["default_policy"] is None

    with pytest.raises(TypeError, match="policy_id must be"):
        PanchaPakshiHistoricalClassificationPolicy(policy_id=policy.policy_id.value)
    with pytest.raises(FrozenInstanceError):
        policy.policy_id = policy.policy_id


def test_policy_lookup_delegates_exactly_without_temporal_selection_or_fallback() -> None:
    corpus = _corpus()
    policy = _policy()

    for case in _decision()["verified_policy_cases"]:
        result = pancha_pakshi_uromarisi_classification_under_policy(
            corpus,
            policy=policy,
            activity=PanchaPakshiActivity(case["activity"]),
            ordinal=case["ordinal"],
        )
        expected_verse = case["classification_verse"]
        assert (None if result is None else result.verse) == expected_verse
        assert result is corpus.classification_at(
            PanchaPakshiActivity(case["activity"]), case["ordinal"]
        )

    assert pancha_pakshi_uromarisi_classification_under_policy(
        corpus,
        policy=policy,
        activity=PanchaPakshiActivity.SLEEP,
        ordinal=5,
    ) is None
    assert corpus.conflict_for_verse(250) is not None


def test_stage2k_selectors_remain_named_but_unbound_cross_witness_candidates() -> None:
    decision = _decision()
    candidates = decision["unadmitted_cross_witness_selector_candidates"]

    assert [candidate["policy_id"] for candidate in candidates] == [
        PanchaPakshiSookshmaSelectorPolicyId.WEIGHTED_SOOKSHMA.value,
        PanchaPakshiSookshmaSelectorPolicyId.EKA_SOOKSHMA_EQUAL_FIFTHS.value,
    ]
    assert all(
        candidate["uromarisi_binding_status"]
        == "not_source_attested_or_admitted"
        and candidate["automatic_composition"] is False
        for candidate in candidates
    )
    assert decision["policy_invariants"]["stage2k_selector_binding"] == "forbidden"
    assert decision["policy_invariants"]["temporal_inference_from_clock_or_elapsed_time"] == (
        "forbidden"
    )


def test_phase4_failure_and_nonadmission_boundaries_remain_private() -> None:
    corpus = _corpus()
    decision = _decision()

    with pytest.raises(TypeError, match="policy must be"):
        pancha_pakshi_uromarisi_classification_under_policy(
            corpus,
            policy="explicit",
            activity=PanchaPakshiActivity.EAT,
            ordinal=1,
        )
    with pytest.raises(TypeError, match="missing 1 required keyword-only argument"):
        pancha_pakshi_uromarisi_classification_under_policy(
            corpus,
            activity=PanchaPakshiActivity.EAT,
            ordinal=1,
        )

    assert decision["phase4_closure"]["status"] == (
        "complete_at_private_research_boundary"
    )
    assert decision["phase4_closure"]["phase5_entry_status"] == (
        "ready_for_relational_formalization_only"
    )
    assert decision["phase4_closure"]["automatic_public_admission"] is False
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
    assert all("uromarisi" not in route.path.lower() for route in router_module.router.routes)
