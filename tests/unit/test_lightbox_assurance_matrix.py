"""Coverage and evidence-class gates for the Light Box assurance matrix."""

from __future__ import annotations

import importlib.util
import json
from copy import deepcopy
from pathlib import Path
import sys


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


def test_matrix_does_not_promote_local_receipts_to_release_evidence() -> None:
    generator = _module()
    receipts = deepcopy(generator._load(generator.RECEIPTS_PATH))
    receipts["artifact_status"] = "local_unreleased_worktree"
    for receipt in receipts["receipts"]:
        receipt["artifact_status"] = "local_unreleased_worktree"
    matrix = generator.build_matrix(
        generator._load(generator.CONTRACTS_PATH),
        receipts,
        generator._load(generator.MANIFEST_PATH),
    )
    covered = matrix["summary"]["surfaces_with_contracts"]
    uncovered = matrix["summary"]["surfaces_without_contracts"]
    assert matrix["receipt_artifact_status"] == "local_unreleased_worktree"
    assert matrix["summary"]["evidence_classes"]["release"]["passed_local"] == covered
    assert matrix["summary"]["evidence_classes"]["release"]["passed_exact_source"] == 0
    assert matrix["summary"]["evidence_classes"]["release"]["not_run"] == uncovered


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
