"""Coverage and evidence-class gates for the Light Box assurance matrix."""

from __future__ import annotations

import importlib.util
import json
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
    assert matrix["summary"]["canonical_surfaces"] == 1210
    assert matrix["summary"]["surfaces_with_contracts"] == 15
    assert matrix["summary"]["surfaces_without_contracts"] == 1195
    assert matrix["summary"]["contracts"] == 9
    assert matrix["summary"]["contracts_failed"] == 0
    for row in matrix["surfaces"]:
        assert set(row["evidence"]) == set(generator.EVIDENCE_CLASSES)


def test_matrix_does_not_promote_local_receipts_to_release_evidence() -> None:
    generator = _module()
    matrix = generator.build_matrix(
        generator._load(generator.CONTRACTS_PATH),
        generator._load(generator.RECEIPTS_PATH),
        generator._load(generator.MANIFEST_PATH),
    )
    assert matrix["receipt_artifact_status"] == "local_unreleased_worktree"
    assert matrix["summary"]["evidence_classes"]["release"]["passed_local"] == 15
    assert matrix["summary"]["evidence_classes"]["release"]["passed_exact_source"] == 0
    assert matrix["summary"]["evidence_classes"]["release"]["not_run"] == 1195


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
