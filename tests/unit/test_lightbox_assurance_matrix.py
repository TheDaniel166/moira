"""Coverage and evidence-class gates for the Light Box assurance matrix."""

from __future__ import annotations

import importlib.util
import json
from copy import deepcopy
from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).parents[2]
SCRIPT = REPO_ROOT / "scripts" / "generate_lightbox_assurance_matrix.py"


def _module():
    spec = importlib.util.spec_from_file_location(
        "generate_lightbox_assurance_matrix", SCRIPT
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_matrix_preserves_every_surface_and_every_evidence_class() -> None:
    generator = _module()
    contracts = generator._load(generator.CONTRACTS_PATH)
    receipts = generator._load(generator.RECEIPTS_PATH)
    manifest = generator._load(generator.MANIFEST_PATH)
    matrix = generator.build_matrix(contracts, receipts, manifest)
    assert generator.validate_matrix(matrix, manifest) == []
    canonical_surfaces = sum(
        row["entry_role"] == "canonical" for row in manifest["entries"]
    )
    contracted_surfaces = {
        surface_id
        for contract in contracts["contracts"]
        for surface_id in contract["surface_ids"]
    }
    assert matrix["summary"]["canonical_surfaces"] == canonical_surfaces
    assert matrix["summary"]["surfaces_with_contracts"] == len(contracted_surfaces)
    assert matrix["summary"]["surfaces_without_contracts"] == (
        canonical_surfaces - len(contracted_surfaces)
    )
    assert matrix["summary"]["contracts"] == len(contracts["contracts"])
    assert matrix["summary"]["contracts_failed"] == 0
    for row in matrix["surfaces"]:
        assert set(row["evidence"]) == set(generator.EVIDENCE_CLASSES)


def _synthetic_inputs(generator, artifact_status):
    """Create checksummed test records without rewriting historical execution evidence."""
    fingerprint = "a" * 64
    contract = {
        "claim_id": "LB-TEST-ASSURANCE",
        "surface_ids": ["python:test.covered"],
        "evidence_classes": ["release", "regression"],
        "claim_scope": "Synthetic assurance classification test only.",
        "exclusions": ["Not an execution receipt or release attestation."],
    }
    contracts = {
        "schema_version": "moira.lightbox-evidence-contracts/v1",
        "contracts": [contract],
    }
    receipt = {
        "claim_id": contract["claim_id"],
        "contract_sha256": generator._sha(contract),
        "inventory_fingerprint_sha256": fingerprint,
        "artifact_status": artifact_status,
        "status": "passed",
        "passed_tests": 1,
    }
    receipt["receipt_id"] = generator._sha(receipt)
    receipts = {
        "schema_version": "moira.lightbox-evidence-receipts/v2",
        "source_revision": "1" * 40,
        "artifact_status": artifact_status,
        "inventory_fingerprint_sha256": fingerprint,
        "contracts_sha256": generator._sha(contracts),
        "receipts": [receipt],
    }
    manifest = {
        "schema_version": "moira.lightbox-conformance-manifest/v2",
        "engine_version": "test-only",
        "inventory_fingerprint_sha256": fingerprint,
        "entries": [
            {"surface_id": surface, "entry_role": "canonical", "conformance_status": "test-only"}
            for surface in ("python:test.covered", "python:test.uncovered")
        ],
    }
    return contracts, receipts, manifest


@pytest.mark.parametrize("artifact_status,expected,excluded", [
    ("local_unreleased_worktree", "passed_local", "passed_exact_source"),
    ("exact_source_revision", "passed_exact_source", "passed_local"),
])
def test_matrix_does_not_promote_local_receipts_to_release_evidence(
    artifact_status, expected, excluded,
) -> None:
    generator = _module()
    inputs = _synthetic_inputs(generator, artifact_status)
    unchanged = deepcopy(inputs)
    matrix = generator.build_matrix(*inputs)
    assert inputs == unchanged
    assert generator.validate_matrix(matrix, inputs[2]) == []
    assert matrix["receipt_artifact_status"] == artifact_status
    release = matrix["summary"]["evidence_classes"]["release"]
    assert release == {expected: 1, excluded: 0, "failed": 0, "not_run": 1}
    assert matrix["surfaces"][0]["evidence"]["release"]["status"] == expected
    assert matrix["surfaces"][1]["evidence"]["release"]["status"] == "not_run"


@pytest.mark.parametrize("artifact_status", ["local_unreleased_worktree", "exact_source_revision"])
def test_matrix_rejects_receipt_status_changes_without_a_new_digest(artifact_status) -> None:
    generator = _module()
    contracts, receipts, manifest = _synthetic_inputs(generator, artifact_status)
    # Reproduce the broken fixture: changing checksummed content invalidates its ID.
    receipts["receipts"][0]["artifact_status"] = (
        "exact_source_revision" if artifact_status == "local_unreleased_worktree"
        else "local_unreleased_worktree"
    )
    with pytest.raises(generator.AssuranceMatrixError, match="individual receipt digest mismatch"):
        generator.build_matrix(contracts, receipts, manifest)


def test_generated_matrix_is_current_and_deterministic() -> None:
    generator = _module()
    contracts = generator._load(generator.CONTRACTS_PATH)
    receipts = generator._load(generator.RECEIPTS_PATH)
    manifest = generator._load(generator.MANIFEST_PATH)
    matrix = generator.build_matrix(contracts, receipts, manifest)
    assert generator.JSON_PATH.read_text(encoding="utf-8") == generator.render_json(
        matrix
    )
    assert generator.MARKDOWN_PATH.read_text(
        encoding="utf-8"
    ) == generator.render_markdown(matrix)
    assert json.loads(generator.render_json(matrix)) == matrix
